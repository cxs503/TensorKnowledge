"""Fetch report 13988 markdown from the platform API and verify sha256 against the contract.

Usage: python3 scripts/kf_fetch_13988.py
Outputs:
  runs/wp-13988-01/report_13988.json  (raw API payload: id/title/scenario_key/figures/tags/...)
  runs/wp-13988-01/report_13988.md    (markdown payload, byte-exact)
Never hardcodes credentials: uses env TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE.
"""
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

REPORT_ID = "13988"
PKG = "wp-13988-01"
OUT = pathlib.Path("runs") / PKG
EXPECTED_HASH = "79d795674f0b13f828d8933af64612a1addb30cb8a8b903f7ab136f0508442b9"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _req(url, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data)
    if data is not None:
        req.add_header("Content-Type", "application/json")
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
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tok = login()
    payload = _req("%s/tensor/reports/%s" % (BASE, REPORT_ID), token=tok)
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    (OUT / ("report_%s.json" % REPORT_ID)).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2))
    md = payload["markdown"]
    (OUT / ("report_%s.md" % REPORT_ID)).write_text(md)
    h = hashlib.sha256(md.encode()).hexdigest()
    print("id:", payload.get("id"), "title:", (payload.get("title") or "")[:60])
    print("chars:", len(md), "bytes_utf8:", len(md.encode()))
    print("sha256:", h, "MATCH" if h == EXPECTED_HASH else "MISMATCH vs contract")
    print("figures:", len(payload.get("figures") or []), "tags:", payload.get("tags"))
    return 0 if h == EXPECTED_HASH else 2


if __name__ == "__main__":
    sys.exit(main())