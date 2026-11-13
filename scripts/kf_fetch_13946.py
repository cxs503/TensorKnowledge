"""Fetch report 13946 markdown from platform API and verify sha256 against the work-package contract.

Usage: python3 scripts/kf_fetch_13946.py
Outputs: runs/wp-13946-01/report_13946.json (raw API payload), runs/wp-13946-01/report_13946.md
Never hardcodes credentials: uses env TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE.
Only report_id=13946 is read (hard boundary of wp-13946-01).
"""
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

REPORT_ID = "13946"
PACKAGE_ID = "wp-13946-01"
EXPECTED_HASH = "eb37b6effecdfc9396ded7a80f236173e234f2785fd984a948efba4a9b671072"
OUT = pathlib.Path("runs") / PACKAGE_ID
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


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
    OUT.mkdir(parents=True, exist_ok=True)
    tok = login()
    payload = _get_json(BASE + "/tensor/reports/" + REPORT_ID, tok)
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    if not isinstance(payload, dict):
        payload = {"raw": payload}
    (OUT / "report_13946.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    md = payload.get("markdown") or ""
    if not md:
        print("ERROR: markdown field empty; keys=", list(payload))
        return 1
    (OUT / "report_13946.md").write_text(md)
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