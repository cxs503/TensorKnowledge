#!/usr/bin/env python3
"""Fetch report 4537 markdown (+record) read-only, cache under runs/ and verify sha256.

Only report_id=4537 is touched. Credentials come from the environment; nothing is printed.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from pathlib import Path

REPORT_ID = "4537"
EXPECT_HASH = "sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08"
EXPECT_CHARS = 7931
ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "runs" / "m15829_wp4537_04"


def main() -> int:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps(
        {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]}
    ).encode()
    req = urllib.request.Request(
        f"{base}/auth/login", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        token = json.load(resp)["access_token"]
    req = urllib.request.Request(
        f"{base}/tensor/reports/{REPORT_ID}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        record = json.load(resp)
    md = record["markdown"]
    raw = md.encode("utf-8")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / f"source_report_{REPORT_ID}.md").write_text(md, encoding="utf-8")
    (CACHE / f"report_record_{REPORT_ID}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    meta = {
        "report_id": REPORT_ID,
        "sha256": digest,
        "chars": len(md),
        "bytes": len(raw),
        "hash_matches_contract": digest == EXPECT_HASH,
        "chars_match_contract": len(md) == EXPECT_CHARS,
        "record_keys": sorted(record.keys()),
    }
    (CACHE / "fetch_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))
    return 0 if (meta["hash_matches_contract"] and meta["chars_match_contract"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())