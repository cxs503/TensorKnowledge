#!/usr/bin/env python3
"""wp-9756-01 | publish the KF-RESULT report (title `KF-RESULT wp-9756-01`).

Posts docs/kf/wp-9756-01/report_body.md as the report markdown. The body already
contains exactly one fenced json block (the kf_result.v1 envelope); this script
re-asserts that before sending, so the "single json block" contract cannot regress.

    python3 scripts/kf_wp9756_01_publish.py [--dry-run]

Env: TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PWD = os.environ["TENSOR_AGENT_PASS"]
PKG = "wp-9756-01"
REPORT_ID = "9756"
MISSION_ID = 15666
BODY = f"docs/kf/{PKG}/report_body.md"
PNG = f"docs/kf/{PKG}/figures/asset_manifest_coverage.png"
CONTRACT_HASH = "sha256:66c02e91e7ffcc3d81b24465112b94ac481ebc351584c13d01d978c16be4316b"


def post_json(url: str, payload: dict, token: str | None = None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=120).read())
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"POST {url} -> {exc.code}: {exc.read()[:500]!r}") from exc


def login() -> str:
    body = post_json(f"{BASE}/auth/login", {"username": USER, "password": PWD})
    tok = body.get("access_token") or body.get("token")
    if not tok:
        raise SystemExit("login returned no token")
    return tok


def main() -> None:
    md = open(BODY, encoding="utf-8").read()

    blocks = re.findall(r"```json\n(.*?)\n```", md, flags=re.S)
    assert md.count("```json") == 1, f"expected exactly one json block, found {md.count('```json')}"
    assert len(blocks) == 1, blocks
    env = json.loads(blocks[0])
    assert env["package_id"] == PKG and env["report_id"] == REPORT_ID
    assert env["provenance"]["source_hash"] == CONTRACT_HASH, env["provenance"]["source_hash"]
    assert env["claims"] == []

    payload = {
        "title": f"KF-RESULT {PKG}",
        "summary": ("report_id=9756 资产登记：markdown sha256 与契约逐字节一致（chars 8293 / bytes 12236），"
                    "登记 27 项源资产（1 resolved / 4 metadata_only / 22 referenced_unresolved），"
                    "34 条定位器全部逐字命中且唯一，claims=[]（不做抽取、不标 verified），自检 15 例全绿。"),
        "scenario_key": f"ship_performance/knowledge_factory/{PKG}",
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:wp-9756-01", "kf-result", "01-asset-registration",
                 "report:9756", "EEXI", "CII", "green_compliance", "asset-registration"],
        "markdown": md,
        "figures": [{
            "name": "asset_manifest_coverage.png",
            "caption": ("wp-9756-01 资产解析状态覆盖：resolved_in_source 1 / metadata_only 4 / "
                        "referenced_unresolved 22（共 27 项，数字取自 asset_manifest.json counts.by_resolution）"),
            "png_base64": base64.b64encode(open(PNG, "rb").read()).decode(),
        }],
    }

    if "--dry-run" in sys.argv:
        print(f"dry-run: body {len(md)} chars, json block ok, figure {len(payload['figures'][0]['png_base64'])} b64 chars")
        return

    tok = login()
    resp = post_json(f"{BASE}/tensor/reports", payload, tok)
    new_id = resp.get("id") or (resp.get("report") or {}).get("id")
    print(f"published KF-RESULT {PKG} as report id={new_id} (source report_id={REPORT_ID})")
    print(json.dumps({k: resp.get(k) for k in ("id", "title", "status", "scenario_key")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()