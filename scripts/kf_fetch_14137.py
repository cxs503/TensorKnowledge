"""Fetch report 14137 markdown from platform API and verify sha256 against the work-package contract.

Usage: python3 scripts/kf_fetch_14137.py
Outputs: runs/wp-14137-01/report_14137.json (raw API payload), runs/wp-14137-01/report_14137.md
Never hardcodes credentials: uses env TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE.
"""
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

OUT = pathlib.Path("runs/wp-14137-01")
OUT.mkdir(parents=True, exist_ok=True)
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
EXPECTED_HASH = "6f65040f0d3483ee5ca35f81c0fa4e5af147165e066e6c9c1cdb9a815faa8c30"


def _post_json(url, payload, token=None):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _get_json(url, token=None):
    req = urllib.request.Request(url)
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
            d = _post_json(BASE + path, {"username": user, "password": pwd})
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def main():
    tok = login()
    payload = _get_json(BASE + "/tensor/reports/14137", tok)
    if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], dict):
        payload = payload["data"]
    if not isinstance(payload, dict):
        payload = {"raw": payload}
    (OUT / "report_14137.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    md = payload.get("markdown") or ""
    if not md:
        print("ERROR: markdown field empty; keys=", list(payload))
        return 1
    (OUT / "report_14137.md").write_text(md)
    h = hashlib.sha256(md.encode()).hexdigest()
    print("report_id:", payload.get("id"))
    print("title:", payload.get("title"))
    print("scenario_key:", payload.get("scenario_key"))
    print("chars(markdown):", len(md))
    print("bytes(utf8):", len(md.encode()))
    print("sha256(markdown):", h)
    print("expected:", EXPECTED_HASH)
    print("MATCH:", h == EXPECTED_HASH)
    return 0 if h == EXPECTED_HASH else 2


if __name__ == "__main__":
    sys.exit(main())