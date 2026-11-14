#!/usr/bin/env python3
"""Fetch report 11415 markdown (source of truth) for review package wp-11415-04.

Zero-transcription rule: the markdown is written to disk verbatim and its
sha256 is recomputed locally against the contract source_hash.
Run:  python3 scripts/kf_fetch_11415_04.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import urllib.request

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]
OUT = pathlib.Path("runs/wp-11415-04")
EXPECTED = "d8bc42883f1fa1d274a3ca4808586d2a8773e9d0f464b554c944f5090b0c8c50"
EXPECTED_CHARS = 7903


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def get(path: str, token: str) -> dict:
    req = urllib.request.Request(
        BASE + path, headers={"Authorization": "Bearer " + token}, method="GET"
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tok = post("/auth/login", {"username": USER, "password": PASS})
    token = tok.get("access_token") or tok.get("token")
    payload = get("/tensor/reports/11415", token)
    payload = payload.get("data", payload)
    md = payload["markdown"]
    h = hashlib.sha256(md.encode()).hexdigest()
    (OUT / "report_11415.md").write_text(md, encoding="utf-8")
    (OUT / "report_11415.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    meta = {
        "report_id": str(payload.get("id")),
        "title": payload.get("title"),
        "chars": len(md),
        "bytes_utf8": len(md.encode()),
        "sha256": h,
        "sha256_matches_contract": h == EXPECTED,
        "chars_matches_contract": len(md) == EXPECTED_CHARS,
        "status": payload.get("status"),
        "mission_id": payload.get("mission_id"),
        "tags": payload.get("tags"),
        "figures": payload.get("figures"),
        "scenario_key": payload.get("scenario_key"),
    }
    (OUT / "source_identity.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0 if (meta["sha256_matches_contract"] and meta["chars_matches_contract"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())