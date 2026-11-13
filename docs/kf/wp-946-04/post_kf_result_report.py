#!/usr/bin/env python3
"""Submit the KF-RESULT deliverable itself as the mission's result-channel report.

Title is exactly `KF-RESULT wp-946-04`; tags carry `kf-wp:wp-946-04`; the markdown body is
docs/kf/wp-946-04/report.md verbatim, i.e. it contains exactly one fenced json block = the
kf_result.v1 envelope (docs/kf/wp-946-04/kf_result.json).

Usage: python3 docs/kf/wp-946-04/post_kf_result_report.py
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

PKG = Path(__file__).resolve().parent
BODY = PKG / "report.md"
KF = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))

markdown = BODY.read_text(encoding="utf-8")
blocks = re.findall(r"```json\n(.*?)\n```", markdown, re.S)
assert len(blocks) == 1, f"expected exactly one json block, found {len(blocks)}"
assert json.loads(blocks[0]) == KF, "embedded json block differs from kf_result.json"

payload = {
    "title": "KF-RESULT wp-946-04",
    "summary": (
        f"独立审核 wp-946-01（report 946）判决 {KF['outputs']['review_report.json']['verdict']}："
        f"{len(KF['outputs']['review_report.json']['checks'])} 项检查 0 失败，附 "
        f"{len(KF['outputs']['review_report.json']['non_blocking_notes'])} 条非阻断发现与 "
        f"{len(KF['outputs']['review_report.json']['not_run'])} 项未核；provenance.source_hash 与报告 946 markdown 一致"
    ),
    "scenario_key": "ai-native-infra",
    "mission_id": 15818,
    "tags": ["KF", "KF-RESULT", "kf-wp:wp-946-04", "wp-946-04", "report-946", "independent-review", "ai-native-infra"],
    "markdown": markdown,
    "figures": [],
}


def main() -> None:
    base = os.environ["TENSOR_API_BASE"]
    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps(
            {
                "username": os.environ["TENSOR_AGENT_USER"],
                "password": os.environ["TENSOR_AGENT_PASS"],
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    tok = json.load(urllib.request.urlopen(req))
    tok = tok.get("access_token") or tok.get("token")
    req = urllib.request.Request(
        base + "/tensor/reports",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok},
    )
    try:
        resp = json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as exc:
        print("HTTP", exc.code, exc.read()[:500].decode("utf8", "ignore"))
        raise
    print(
        json.dumps(
            {
                "posted_report_id": resp.get("id"),
                "title": resp.get("title"),
                "mission_id": resp.get("mission_id"),
                "tags": resp.get("tags"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()