"""Fetch report 10602 markdown from the platform API and verify its sha256.

Usage: python3 scripts/kf_fetch_10602.py
Outputs: runs/wp-10602-01/report_10602.json (raw API payload), runs/wp-10602-01/report_10602.md
Never hardcodes credentials: uses env TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE.
"""
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

REPORT_ID = "10602"
OUT = pathlib.Path("runs/wp-10602-01")
OUT.mkdir(parents=True, exist_ok=True)
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
    last = None
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = _post_json(BASE + path, {"username": user, "password": pwd})
        except Exception as exc:  # try next endpoint
            last = exc
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    if last:
        print("login failed:", last, file=sys.stderr)
    return None


def main():
    tok = login()
    payload = _get_json(BASE + "/tensor/reports/" + REPORT_ID, tok)
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    if not isinstance(payload, dict):
        payload = {"raw": payload}
    (OUT / "report_10602.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    md = payload.get("markdown")
    if not isinstance(md, str):
        print("no markdown field in payload; keys=", sorted(payload), file=sys.stderr)
        sys.exit(1)
    raw = md.encode("utf-8")
    (OUT / "report_10602.md").write_bytes(raw)
    print("chars=", len(md), "bytes_utf8=", len(raw))
    print("sha256:", hashlib.sha256(raw).hexdigest())
    print("title:", payload.get("title"))
    print("scenario_key:", payload.get("scenario_key"))


if __name__ == "__main__":
    main()