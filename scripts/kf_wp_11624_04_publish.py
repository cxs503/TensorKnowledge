#!/usr/bin/env python3
"""Publish the wp-11624-04 progress report to the platform (owner report discipline).

Posts the reviewed markdown body + the two matplotlib figures (base64-inlined) to
POST /api/v1/tensor/reports. Credentials come from the environment only
(TENSOR_AGENT_USER / TENSOR_AGENT_PASS); nothing is written to disk except a receipt.

Reproduce: python3 scripts/kf_wp_11624_04_publish.py [--dry-run]
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "reviews" / "wp-11624-04"
PKG = "wp-11624-04"
MISSION_ID = 19831

body = (OUT / f"KF-RESULT.{PKG}.md").read_text(encoding="utf-8")
review = json.load(open(OUT / "review_report.json", encoding="utf-8"))
nums = json.load(open(OUT / "numbers.json", encoding="utf-8"))

ship_line = "; ".join(
    f"{s['ship']}: EEXI {s['eexi_attained']:.3f}/{s['eexi_required']:.3f} "
    f"({s['eexi_ok'] and 'compliant' or 'non-compliant'}), "
    f"CII/CII_req {s['cii_ratio']:.4f} -> {s['rating']}" for s in nums["ships"]
)

figures = [
    {"name": png.name, "caption": cap,
     "png_base64": base64.b64encode(png.read_bytes()).decode()}
    for png, cap in (
        (OUT / "fig1_eexi_cii_recheck.png",
         "图 1 独立审核重算：报告 §3.1 的 EEXI/CII 数字（脚本从原文解析）与用报告 §2.2 dd 向量机械重判的 A–E 评级"),
        (OUT / "fig2_review_ledger.png",
         "图 2 审核台账：左=27 个上游资产定位点字节级复算；右=19 条检查的 pass/fail/not_run（红=发现缺陷）"),
    )
]

payload = {
    "title": f"KF-RESULT {PKG}：报告 11624 EEXI/CII 验证面的独立红队审核（上游 wp-11624-01）",
    "summary": (
        f"独立审核裁决 {review['verdict'].upper()}：13 项门控检查全通过（27/27 定位点字节级复现，"
        f"源哈希 a5a0885e… 复算一致），5 项非阻塞发现（A07 参数表 2/4 列为空、C4 用例不可追溯到参数表、"
        f"双算法互裁为代数恒等式、信封 schema 越界、§4.2 叙述张力）。{ship_line}。"
        f"表内一致性误差 ≤{max((s.get('rel_diff_table_vs_log') or 0) for s in nums['ships']) * 100:.4f}%（<3%）；"
        "物理基准误差不可给（报告未提供 P_i/SFOC/CF/f 系数，重算欠定）。"
    ),
    "scenario_key": "P187-W1-N06",
    "mission_id": MISSION_ID,
    "tags": ["kf-wp:" + PKG, "report:11624", "lane:C", "task:04-independent-review",
             "EEXI", "CII", "independent-review", "red-team"],
    "markdown": body,
    "figures": figures,
}

if "--dry-run" in sys.argv:
    Path("/tmp/report.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print("dry-run: payload written to /tmp/report.json", len(payload["markdown"]), "chars,",
          len(figures), "figures")
    raise SystemExit(0)

base = os.environ["TENSOR_API_BASE"].rstrip("/")


def post(path: str, payload: dict, token: str | None = None) -> dict:
    req = urllib.request.Request(
        base + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 **({"Authorization": "Bearer " + token} if token else {})},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


tok = post("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                           "password": os.environ["TENSOR_AGENT_PASS"]})["access_token"]
res = post("/tensor/reports", payload, tok)
json.dump(res, open(OUT / "publish_receipt.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({k: res.get(k) for k in ("id", "title", "status", "scenario_key", "mission_id")},
                 ensure_ascii=False, indent=1))
print("figures stored:", len(res.get("figures") or []))