#!/usr/bin/env python3
"""wp-8288-01 step 1: fetch report 8288 markdown verbatim and pin its bytes.

Writes docs/kf/wp-8288-01/source.md (byte-exact, utf-8) plus fetch_meta.json.
Refuses to continue if the sha256 of the fetched markdown differs from the
contract-declared source_hash, so no downstream artifact can be built on drift.

Usage: python3 scripts/kf/wp8288_01_fetch.py
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPORT_ID = "8288"
PKG = "wp-8288-01"
EXPECTED_HASH = "2c35fbe3fa027f083b82f15238f3db797f087df0c435a1c536b176280e053f19"
EXPECTED_CHARS = 9660

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "docs" / "kf" / PKG
SRC = OUT_DIR / "source.md"
META = OUT_DIR / "fetch_meta.json"

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASSWORD = os.environ["TENSOR_AGENT_PASS"]


def _req(url, token=None, data=None, ctype="application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def login():
    payload = {"username": USER, "password": PASSWORD}
    try:
        d = _req(BASE + "/auth/login", data=json.dumps(payload).encode())
    except urllib.error.HTTPError:
        d = _req(BASE + "/auth/login", data=urllib.parse.urlencode(payload).encode(),
                 ctype="application/x-www-form-urlencoded")
    tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit("login returned no token: %s" % sorted(d))
    return tok


def fetch(token):
    d = _req(BASE + "/tensor/reports/" + REPORT_ID, token)
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    md = d.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("report %s has no markdown field" % REPORT_ID)
    return d, md


def main():
    token = login()
    meta, md = fetch(token)
    raw = md.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SRC.write_bytes(raw)
    record = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "fetched_via": "GET %s/tensor/reports/%s" % (BASE, REPORT_ID),
        "source_field": "markdown",
        "sha256_recomputed": digest,
        "sha256_contract": EXPECTED_HASH,
        "hash_matches_contract": digest == EXPECTED_HASH,
        "chars": len(md),
        "chars_contract": EXPECTED_CHARS,
        "chars_match_contract": len(md) == EXPECTED_CHARS,
        "bytes_utf8": len(raw),
        "title": meta.get("title"),
        "scenario_key": meta.get("scenario_key"),
        "mission_id": meta.get("mission_id"),
        "tags": meta.get("tags"),
        "created_at": meta.get("created_at"),
        "figures_count": len(meta.get("figures") or []),
        "figure_names": [f.get("name") for f in (meta.get("figures") or [])],
        "record_keys": sorted(meta.keys()),
    }
    META.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: record[k] for k in ("sha256_recomputed", "hash_matches_contract",
                                            "chars", "chars_match_contract", "title")},
                     ensure_ascii=False, indent=2))
    if not record["hash_matches_contract"]:
        raise SystemExit("SOURCE HASH MISMATCH — stop, do not build artifacts")


if __name__ == "__main__":
    main()