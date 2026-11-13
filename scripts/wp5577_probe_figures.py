#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wp-5577-04 · 图的字节面探针（受控对照实验）。

问题：report-5577 声称「三张图见内嵌附图」，但其记录里 figures 只有 name/caption、没有 png_base64。
    这是「报告没传字节」还是「平台不存字节」？二者结论完全不同，必须用对照实验区分。

设计（动手前先声明判据）
-----------------------
- 处理组：对 report-5577 声明的 3 个图名请求 `GET /tensor/reports/5577/figures/{name}`；
- 正对照：本审核自身此前投递的报告（#CONTROL_REPORT_ID）带有 fig1_closure_residuals.png 的 png_base64，
  用同一端点取回，与本地 PNG 做 sha256 比对；
- 判据：正对照 sha256 一致 ⇒ 该端点确实能取回巨量图字节（平台不吞字节）；
  若处理组全部 404 ⇒ report-5577 的图字节从未随报告落库（生产者侧缺口）而非平台限制；
  若正对照也不一致 ⇒ 探针无效，结论降级为 unknown。

产物：docs/kf/wp-5577-04/source/figure_probe.json（供离线复跑的审核脚本读取）
用法：python3 scripts/wp5577_probe_figures.py [--control-report-id 14965]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "docs", "kf", "wp-5577-04", "source")
TARGET = "5577"
TARGET_FIGURES = ["fig1_resistance_spectrum.png", "fig2_deviation_spectrum.png", "fig3_evidence_chain.png"]
CONTROL_NAME = "fig1_closure_residuals.png"
CONTROL_LOCAL = os.path.join(ROOT, "docs", "kf", "wp-5577-04", CONTROL_NAME)


def api(path: str) -> tuple[int, bytes]:
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
    payload = json.dumps({"username": os.environ.get("TENSOR_AGENT_USER", ""),
                          "password": os.environ.get("TENSOR_AGENT_PASS", "")}).encode()
    req = urllib.request.Request(f"{base}/auth/login", data=payload,
                                 headers={"Content-Type": "application/json"}, method="POST")
    tok = json.loads(urllib.request.urlopen(req, timeout=30).read())["access_token"]
    req = urllib.request.Request(f"{base}/{path}", headers={"Authorization": f"Bearer {tok}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control-report-id", default="14965")
    ap.add_argument("--report-id", default=TARGET)
    a = ap.parse_args()

    figs = []
    for name in TARGET_FIGURES:
        code, body = api(f"tensor/reports/{a.report_id}/figures/{name}")
        figs.append({"name": name, "http_status": code, "bytes": len(body),
                     "sha256": hashlib.sha256(body).hexdigest() if code == 200 else None})

    code, body = api(f"tensor/reports/{a.control_report_id}/figures/{CONTROL_NAME}")
    local = open(CONTROL_LOCAL, "rb").read()
    ctrl = {
        "report_id": a.control_report_id,
        "name": CONTROL_NAME,
        "http_status": code,
        "bytes": len(body),
        "sha256_remote": hashlib.sha256(body).hexdigest() if code == 200 else None,
        "sha256_local": hashlib.sha256(local).hexdigest(),
        "identical": code == 200 and hashlib.sha256(body).digest() == hashlib.sha256(local).digest(),
    }
    out = {
        "experiment": "figure-bytes retrievability（正对照区分『生产者没传』与『平台不存』）",
        "target_report_id": a.report_id,
        "target_figures": figs,
        "all_target_figures_404": all(f["http_status"] == 404 for f in figs),
        "positive_control": ctrl,
        "probe_valid": ctrl["identical"],
        "conclusion": (
            "平台端可取回图字节（正对照 sha256 一致），而 report-5577 三个声明图名全部 404 "
            "⇒ 图字节从未随报告落库（生产者侧缺口），不是平台不存"
            if ctrl["identical"] and all(f["http_status"] == 404 for f in figs)
            else "探针未形成区分力，结论降级为 unknown"
        ),
    }
    os.makedirs(SRC_DIR, exist_ok=True)
    p = os.path.join(SRC_DIR, "figure_probe.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({k: out[k] for k in ("target_figures", "positive_control", "probe_valid", "conclusion")},
                     ensure_ascii=False, indent=2))
    print("wrote", p)


if __name__ == "__main__":
    main()