"""Fetch report 11608 (markdown) from the platform API and pin its byte hash.

Usage: python3 scripts/kf_fetch_11608.py
Inputs : env TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS (credentials
         stay in the environment; never written to disk).
Outputs: runs/wp-11608-01/report_11608.json  (raw API payload)
         runs/wp-11608-01/report_11608.md    (markdown field, UTF-8, bytes verbatim)
Exit   : 0 = fetched and sha256(markdown) equals the work-package contract hash;
         2 = hash mismatch (loud, no silent fallback); 1 = transport/field failure.

The hash is a mechanical identity check on the bytes the platform serves; it is
NOT a verification verdict -- verification is computed by the platform gate.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.request

REPORT_ID = "11608"
EXPECTED_SHA256 = "8a9602aca712ab3ac8656d7382e0fef762ba0f30657cf8b631b36ba514e8db62"
EXPECTED_CHARS = 7342
OUT = pathlib.Path(__file__).resolve().parents[1] / "runs" / "wp-11608-01"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _post_json(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _get_json(url: str, token: str | None) -> dict:
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login() -> str | None:
    user = os.environ.get("TENSOR_AGENT_USER")
    pwd = os.environ.get("TENSOR_AGENT_PASS")
    if not user or not pwd:
        return None
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = _post_json(BASE + path, {"username": user, "password": pwd})
        except Exception:  # endpoint shape differs between deployments
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    token = login()
    try:
        payload = _get_json(BASE + "/tensor/reports/" + REPORT_ID, token)
    except Exception as exc:
        print("ERROR: fetch failed:", exc)
        return 1
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    (OUT / "report_11608.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
    md = payload.get("markdown") or ""
    if not md:
        print("ERROR: markdown field empty; keys=", list(payload))
        return 1
    # write the decoded text with newline handling untouched
    with open(OUT / "report_11608.md", "w", encoding="utf-8", newline="") as fh:
        fh.write(md)
    h = hashlib.sha256(md.encode("utf-8")).hexdigest()
    print("report_id      :", payload.get("id"))
    print("title          :", payload.get("title"))
    print("scenario_key   :", payload.get("scenario_key"))
    print("chars(markdown):", len(md))
    print("bytes(utf-8)   :", len(md.encode("utf-8")))
    print("sha256         :", h)
    print("expected       :", EXPECTED_SHA256)
    print("chars expected :", EXPECTED_CHARS)
    print("HASH MATCH     :", h == EXPECTED_SHA256)
    print("CHARS MATCH    :", len(md) == EXPECTED_CHARS)
    return 0 if h == EXPECTED_SHA256 and len(md) == EXPECTED_CHARS else 2


if __name__ == "__main__":
    sys.exit(main())