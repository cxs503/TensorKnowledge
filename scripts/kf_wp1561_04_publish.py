#!/usr/bin/env python3
"""wp-1561-04 · publish the result to the platform report store.

The platform report markdown = docs/kf/wp-1561-04/REPORT.md + exactly one ```json block
carrying the kf_result.v1 envelope (the sole result channel for a work package).
"""
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs/kf/wp-1561-04"
BASE = os.environ["TENSOR_API_BASE"]


def token() -> str:
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=30))["access_token"]


def main() -> int:
    env = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
    body = (PKG / "REPORT.md").read_text(encoding="utf-8")
    md = (body.rstrip() + "\n\n```json\n" + json.dumps(env, ensure_ascii=False, indent=1)
          + "\n```\n")
    assert md.count("```json") == 1, "exactly one json block is allowed"

    png = base64.b64encode((PKG / "fig_review_checks.png").read_bytes()).decode()
    payload = {
        "title": "KF-RESULT wp-1561-04",
        "summary": ("独立红队审核 wp-1561-01（report 1561 资产登记）：30 项检查，26 pass / 3 非阻断 fail / "
                    "1 not_run；字节哈希（契约=快照=实时 API）一致，57 条资产引文逐字可定位，信封过 schema，"
                    "零 claim 合法，台账折叠 approved；7 条发现无阻断项（图 5 件载荷仍 404、record 标题与 H1 "
                    "不一致、2 条资产仅状态无原因、行数 163 vs 162、η_R=1.0 称『保守』方向相反）；"
                    "subject 报告 5 船算术自洽复算通过（最大推力闭合相对差 2.8e-05）。"),
        "scenario_key": "propulsion_closure",
        "mission_id": 15823,
        "tags": ["kf-wp:wp-1561-04", "independent-review", "red-team", "pipeline-04",
                 "report:1561", "review:wp-1561-01", "disposition:approve-with-notes"],
        "markdown": md,
        "figures": [{"name": "fig_review_checks.png",
                     "caption": "wp-1561-04 独立复算面板：A 推力闭合相对差（5 船，对数轴）、"
                                "B 交付功率复算差（±0.5 rpm 区间内）、C I2 需求带 vs 闭合工作点",
                     "png_base64": png}],
    }
    (PKG / "report_payload.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    req = urllib.request.Request(BASE + "/tensor/reports",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + token()})
    out = json.load(urllib.request.urlopen(req, timeout=120))
    print(json.dumps({k: out.get(k) for k in ("id", "title", "status")}, ensure_ascii=False))
    (PKG / "publication.json").write_text(json.dumps(
        {"report_id": out.get("id"), "title": out.get("title"),
         "markdown_sha256": __import__("hashlib").sha256(md.encode()).hexdigest(),
         "markdown_utf8_bytes": len(md.encode()),
         "json_blocks": md.count("```json"),
         "envelope_source_hash": env["provenance"]["source_hash"]},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())