"""Fetch report 9763 (markdown + raw JSON payload) for work package wp-9763-01.

No hand transcription: the markdown is written byte-for-byte as returned by the platform.
Usage: python3 scripts/kf_fetch_9763.py
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.request

REPORT_ID = "9763"
OUT = pathlib.Path("runs/wp-9763-01")
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _req(url, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login():
    user = os.environ.get("TENSOR_AGENT_USER")
    pwd = os.environ.get("TENSOR_AGENT_PASS")
    if not user or not pwd:
        return None
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = _req(BASE + path, {"username": user, "password": pwd})
        except Exception:
            continue
        if isinstance(d, dict):
            tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
            if tok:
                return tok
    return None


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tok = login()
    payload = _req(BASE + "/tensor/reports/" + REPORT_ID, token=tok)
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    (OUT / "report_9763.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    md = payload.get("markdown")
    if not isinstance(md, str) or not md:
        print("FATAL: no markdown in payload; keys=%s" % sorted(payload)[:20])
        return 2
    (OUT / "report_9763.md").write_text(md, encoding="utf-8")
    import hashlib
    h = hashlib.sha256(md.encode()).hexdigest()
    print("title:", payload.get("title"))
    print("scenario_key:", payload.get("scenario_key"))
    print("chars:", len(md), "bytes:", len(md.encode()))
    print("sha256:", h)
    print("figures:", len(payload.get("figures") or []))
    print("tags:", payload.get("tags"))
    return 0


if __name__ == "__main__":
    sys.exit(main())