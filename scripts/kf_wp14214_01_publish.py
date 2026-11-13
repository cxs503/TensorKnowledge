#!/usr/bin/env python3
"""Publish the wp-14214-01 report to the platform (title/tags per work-package rule).

Reads the rendered body from docs/kf/wp-14214-01/report_body.md, embeds the two
figures as base64 PNGs, and POSTs /api/v1/tensor/reports. Credentials come from the
environment only. Prints the created report id (no secrets, no token).

    python3 scripts/kf_wp14214_01_publish.py
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-14214-01"
FIGDIR = ROOT / "docs" / "kf" / "figures" / "wp-14214-01"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
MISSION_ID = 15784
PACKAGE_ID = "wp-14214-01"

FIGURES = [
    ("fig1_asset_landscape.png",
     "图1 wp-14214-01 资产登记全景：24 项资产按 class 与 resolution 分层（"
     "resolved_in_source=正文内可解析结构，referenced_unresolved=仅路径可在正文定位）。"
     "数据直读 asset_manifest.json，scripts/kf_wp14214_01_figures.py 生成。"),
    ("fig2_integrity_observations.png",
     "图2 一致性登记：O1 判词三态合计 382 vs 窗口 430（差 48 未归因，unresolved）；"
     "O2 阻断计数 正文 23 vs 记录 title 22（冲突未裁决）；O3 派单回执 20 行/10 个 task_key、"
     "mission 15092–15101 连续（自洽）。全部为登记事实，非 verified。"),
]


def _post(url, payload, token=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def main() -> int:
    tok = _post(BASE + "/auth/login",
                {"username": os.environ["TENSOR_AGENT_USER"],
                 "password": os.environ["TENSOR_AGENT_PASS"]})
    token = tok.get("access_token") or tok.get("token")
    if not token:
        raise SystemExit("login returned no token")

    body = (PKG / "report_body.md").read_text(encoding="utf-8")
    man = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    figs = []
    for name, caption in FIGURES:
        png = (FIGDIR / name).read_bytes()
        figs.append({"name": name, "caption": caption,
                     "png_base64": base64.b64encode(png).decode()})

    summary = (
        "wp-14214-01 资产登记（report 14214）：markdown sha256 独立重算与契约一致（chars=%d），"
        "登记 %d 项资产（%s），全部引文机器定位且唯一；%d 条算术/跨字段一致性登记"
        "（O1 判词三态 382≠窗口 430、O2 阻断 23 vs 22、O3/O4 自洽、O5 六段齐全、O6 精度口径），"
        "不做抽取、不产 claim、无 verified 标注。"
        % (man["source"]["chars"], man["counts"]["assets"],
           ", ".join("%s=%d" % kv for kv in sorted(man["counts"]["by_class"].items())),
           len(man["integrity_observations"]))
    )

    payload = {
        "title": "KF-RESULT " + PACKAGE_ID,
        "summary": summary,
        "scenario_key": "paper-line-w23",
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:" + PACKAGE_ID, "asset-registration", "report-14214", "lane-B",
                 "TensorKnowledge", "draft"],
        "markdown": body,
        "figures": figs,
    }
    out = _post(BASE + "/tensor/reports", payload, token)
    if isinstance(out.get("data"), dict):
        out = out["data"]
    print(json.dumps({"published_report_id": out.get("id"), "title": out.get("title"),
                      "tags": out.get("tags"), "figures": [f["name"] for f in figs],
                      "markdown_chars": len(body)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
