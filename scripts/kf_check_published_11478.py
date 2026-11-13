#!/usr/bin/env python3
"""wp-11478-01 · verify the published platform report round-trips our deliverables.

Checks (all recomputed from the platform, not from local copies):
  1. the published report's markdown is byte-identical to docs/wp-11478-01/KF-RESULT-<pkg>.md
  2. it contains exactly one ```json block and that block equals runs/.../kf_result.<pkg>.json
  3. provenance.source_hash == the contract source_hash of report 11478
  4. the figure named asset_span_map.png is attached
Output: runs/wp-11478-01/publish_verify_11478.json
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request

API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
PKG = "wp-11478-01"
CONTRACT_HASH = "b5b856a019926eb922be123bd6e34077d4a1b470775aa311e56761e680057258"
RUN_DIR = pathlib.Path("runs") / PKG
DOC_DIR = pathlib.Path("docs") / PKG
DOC = DOC_DIR / f"KF-RESULT-{PKG}.md"
ENVELOPE = DOC_DIR / f"kf_result.{PKG}.json"


def call(path: str, body: dict | None = None, tok: str | None = None):
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    data = None if body is None else json.dumps(body).encode()
    with urllib.request.urlopen(urllib.request.Request(API + path, data=data, headers=headers),
                                timeout=120) as r:
        return json.loads(r.read().decode())


def main() -> int:
    rec = json.loads((RUN_DIR / "publish_11478.json").read_text())
    rid = rec["report_id"]
    tok = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                               "password": os.environ["TENSOR_AGENT_PASS"]})["access_token"]
    payload = call(f"/tensor/reports/{rid}", tok=tok)
    if isinstance(payload.get("data"), dict):
        payload = payload["data"]

    md = payload.get("markdown") or ""
    doc = DOC.read_text()
    blocks = re.findall(r"```json\n(.*?)\n```", md, flags=re.S)
    envelope = json.loads(ENVELOPE.read_text())
    checks = {
        "title_is_kf_result": payload.get("title") == f"KF-RESULT {PKG}",
        "tag_present": f"kf-wp:{PKG}" in (payload.get("tags") or []),
        "markdown_byte_identical": md == doc,
        "one_json_block": len(blocks) == 1,
        "json_block_matches_envelope": len(blocks) == 1 and json.loads(blocks[0]) == envelope,
        "provenance_hash_is_contract": len(blocks) == 1
        and json.loads(blocks[0])["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH,
        "figure_attached": any((f or {}).get("name") == "asset_span_map.png"
                               for f in (payload.get("figures") or [])),
    }
    out = {"report_id": rid, "markdown_sha256": hashlib.sha256(md.encode()).hexdigest(),
           "doc_chars": len(md), "checks": checks, "all_pass": all(checks.values())}
    (RUN_DIR / "publish_verify_11478.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())