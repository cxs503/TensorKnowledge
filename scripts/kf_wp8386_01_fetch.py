#!/usr/bin/env python3
"""wp-8386-01 fetch step: pull report 8386 markdown via the platform API and
snapshot it (raw JSON + markdown) under runs/wp-8386-01/.

Zero manual transcription: every number printed here is measured from the
fetched bytes. stdlib only.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ID = "8386"
RUN_DIR = ROOT / "runs" / ("wp-%s-01" % REPORT_ID)
CONTRACT_HASH = "sha256:4104143f4653a88fd9df9c12b93d3d05d42592aca5c835749a34f21ad85761af"
CONTRACT_CHARS = 20879


def api_base() -> str:
    base = os.environ.get("TENSOR_API_BASE")
    if not base:
        raise SystemExit("TENSOR_API_BASE not set")
    return base.rstrip("/")


def login() -> str:
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(api_base() + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        tok = json.load(r).get("access_token")
    if not tok:
        raise SystemExit("login returned no access_token")
    return tok


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    tok = login()
    req = urllib.request.Request(api_base() + "/tensor/reports/" + REPORT_ID,
                                 headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req) as r:
        raw = r.read()
    (RUN_DIR / ("report_%s.json" % REPORT_ID)).write_bytes(raw)
    rec = json.loads(raw)
    md = rec.get("markdown")
    if not md:
        raise SystemExit("report %s has no markdown field" % REPORT_ID)
    (RUN_DIR / ("report_%s.md" % REPORT_ID)).write_text(md, encoding="utf-8")
    digest = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    out = {
        "report_id": REPORT_ID,
        "title": rec.get("title"),
        "scenario_key": rec.get("scenario_key"),
        "chars": len(md),
        "bytes_utf8": len(md.encode("utf-8")),
        "sha256": digest,
        "contract_hash": CONTRACT_HASH,
        "hash_matches_contract": digest == CONTRACT_HASH,
        "contract_chars": CONTRACT_CHARS,
        "chars_match_contract": len(md) == CONTRACT_CHARS,
        "tags": rec.get("tags"),
        "figures": rec.get("figures") or [],
        "record_keys": sorted(rec.keys()),
    }
    (RUN_DIR / "fetch.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                        encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if not out["hash_matches_contract"]:
        raise SystemExit("FATAL: markdown sha256 != contract source_hash")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())