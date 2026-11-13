#!/usr/bin/env python3
"""Publish the m15956 board-audit report to the platform report API.

Reads docs/ke/board-audit-m15956.md + docs/ke/figures/fig-m15956-audit.png,
logs in with TENSOR_AGENT_USER/TENSOR_AGENT_PASS, POSTs /tensor/reports.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def post(path: str, payload: dict, token: str | None = None) -> dict:
    req = urllib.request.Request(
        f"{API}{path}", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 **({"Authorization": f"Bearer {token}"} if token else {})},
        method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def main() -> int:
    md = (ROOT / "docs" / "ke" / "board-audit-m15956.md").read_text(encoding="utf-8")
    png = base64.b64encode((ROOT / "docs" / "ke" / "figures" / "fig-m15956-audit.png").read_bytes()).decode()
    token = post("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                 "password": os.environ["TENSOR_AGENT_PASS"]}).get("access_token")
    if not token:
        print("login failed", file=sys.stderr)
        return 2
    payload = {
        "title": "交差审计 m15956 → KBM-TKC-DOC-SYNC：9/9 漂移门复现但 4/9 谓词自指，判 L2",
        "summary": ("取证复核 m15956 三件套：4 条复现命令全跑（doc-sync 9/9、stats digest 一致、"
                    "boundary 61 违规 FAIL、pytest 55 passed）；7 条 headline 数字 6 条吻合、"
                    "A级6处实为 4 个 critical 文件；裁判表 0 行⇒无 L4，CI 无调用⇒无 L3；"
                    "判 L2 并落表 tensor_maturity_verdicts#421。"),
        "scenario_key": "board-audit",
        "mission_id": 15963,
        "tags": ["board-audit", "KBM-TKC-DOC-SYNC", "m15956", "TensorKnowledge",
                 "maturity-gate", "L2"],
        "markdown": md,
        "figures": [{
            "name": "fig-m15956-audit.png",
            "caption": ("左：stats.json 三口径（30443 / 10166 / 0，digest 复现一致）；"
                        "右：doc-sync 9 条声明谓词质量——4 条自指、4 条源码子串、1 条非自指 file_exists。"),
            "png_base64": png,
        }],
    }
    res = post("/tensor/reports", payload, token)
    print(json.dumps(res, ensure_ascii=False)[:400])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())