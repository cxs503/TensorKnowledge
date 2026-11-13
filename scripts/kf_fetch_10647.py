"""Fetch report 10647 (markdown payload) from the platform API for work package wp-10647-01.

No hand transcription: the markdown is stored verbatim and its sha256 recomputed in-process.
The contract-declared hash, the API-declared record hash (if any) and the local recomputation
are printed side by side; a mismatch aborts with a non-zero exit instead of being papered over.

Outputs
  runs/wp-10647-01/report_10647.json  raw API payload (id/title/scenario_key/figures/tags/...)
  runs/wp-10647-01/report_10647.md    markdown field, byte-for-byte as returned

Usage: python3 scripts/kf_fetch_10647.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.request

REPORT_ID = "10647"
EXPECTED_HASH = "aa10fd7a44acab4a0c877a58dab70f087877e249a28e2684f9a6a7a2d6dfbf31"
EXPECTED_CHARS = 10814
OUT = pathlib.Path("runs/wp-10647-01")
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def login() -> str | None:
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (u and p):
        return None
    for path in ("/auth/login", "/auth/token", "/login"):
        req = urllib.request.Request(
            BASE + path,
            data=json.dumps({"username": u, "password": p}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tok = login()
    req = urllib.request.Request(
        BASE + "/tensor/reports/%s" % REPORT_ID,
        headers={"Authorization": "Bearer " + tok} if tok else {},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.loads(r.read().decode())
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    (OUT / "report_10647.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    md = payload.get("markdown") or ""
    if not md:
        print("ERROR: markdown field empty; keys=", list(payload))
        return 1
    (OUT / "report_10647.md").write_text(md, encoding="utf-8")

    h = hashlib.sha256(md.encode("utf-8")).hexdigest()
    print("report_id        :", payload.get("id"))
    print("title            :", payload.get("title"))
    print("scenario_key     :", payload.get("scenario_key"))
    print("chars            :", len(md))
    print("bytes_utf8       :", len(md.encode("utf-8")))
    print("figures          :", len(payload.get("figures") or []))
    print("tags             :", payload.get("tags"))
    print("sha256(markdown) :", h)
    print("expected         :", EXPECTED_HASH)
    print("MATCH            :", h == EXPECTED_HASH)
    print("chars_match      :", len(md) == EXPECTED_CHARS)
    return 0 if h == EXPECTED_HASH else 2


if __name__ == "__main__":
    sys.exit(main())