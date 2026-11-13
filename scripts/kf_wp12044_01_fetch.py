#!/usr/bin/env python3
"""wp-12044-01 (01-asset-registration, report 12044): fetch the source report.

Fetches GET {TENSOR_API_BASE}/tensor/reports/12044 with a bearer token obtained from
/auth/login (credentials from the environment only, never written to disk), stores the
record and the `markdown` field byte-for-byte, and prints the recomputed sha256 so the
contract source_hash can be checked mechanically.

Usage: python3 scripts/kf_wp12044_01_fetch.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "kf" / "wp-12044-01"
REPORT_ID = "12044"
EXPECTED = "74cbbb52b6682ff4bb865490e1b4cce8511d023ed1a48afa19a9f2d22a0220b6"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _get(path: str, token: str) -> dict:
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tok = _post(
        "/auth/login",
        {
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        },
    )
    if isinstance(tok.get("data"), dict):
        tok = tok["data"]
    token = tok.get("access_token") or tok.get("token")
    if not token:
        print("FATAL: no access_token in login response; keys=", list(tok))
        return 1

    payload = _get("/tensor/reports/" + REPORT_ID, token)
    if isinstance(payload.get("data"), dict):
        payload = payload["data"]
    (OUT / "report_12044.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    md = payload.get("markdown") or ""
    if not md:
        print("FATAL: markdown empty; keys=", list(payload))
        return 1
    (OUT / "source.md").write_bytes(md.encode())
    h = hashlib.sha256(md.encode()).hexdigest()
    (OUT / "sha256.txt").write_text(
        "report_id=12044\nfield=markdown\nsha256=%s\nchars=%d\nbytes_utf8=%d\ncontract=%s\nmatch=%s\n"
        % (h, len(md), len(md.encode()), EXPECTED, h == EXPECTED),
        encoding="utf-8",
    )
    print("id:", payload.get("id"))
    print("title:", payload.get("title"))
    print("scenario_key:", payload.get("scenario_key"))
    print("mission_id:", payload.get("mission_id"))
    print("tags:", payload.get("tags"))
    print("figures:", payload.get("figures"))
    print("chars:", len(md), "bytes_utf8:", len(md.encode()))
    print("sha256:", h)
    print("contract:", EXPECTED)
    print("MATCH:", h == EXPECTED)
    print("MARKDOWN_REPR:", repr(md))
    return 0 if h == EXPECTED else 2


if __name__ == "__main__":
    sys.exit(main())