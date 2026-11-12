"""Fetch report 8510 markdown from platform API and verify sha256.

Usage: python3 scripts/kf_fetch_8510.py
Outputs: runs/wp-8510-01/report_8510.json (raw API payload), runs/wp-8510-01/report_8510.md
"""
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

OUT = pathlib.Path("runs/wp-8510-01")
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
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = _post_json(BASE + path, {"username": user, "password": pwd})
        except Exception as exc:
            last = exc
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def main():
    tok = login()
    if not tok:
        print("ERROR: login failed")
        return 1
    payload = _get_json(BASE + "/tensor/reports/8510", tok)
    if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], dict):
        payload = payload["data"]
    if not isinstance(payload, dict):
        payload = {"raw": payload}
    (OUT / "report_8510.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    md = payload.get("markdown") or ""
    if not md:
        print("ERROR: markdown field empty; keys=", list(payload))
        return 1
    (OUT / "report_8510.md").write_text(md)
    h = hashlib.sha256(md.encode()).hexdigest()
    print("report_id:", payload.get("id"))
    print("title:", payload.get("title"))
    print("chars(markdown):", len(md))
    print("chars(utf8 bytes):", len(md.encode()))
    print("sha256(markdown):", h)
    expected = "89c40d5daaece7b52882a5d137706680a8132e886aa8922092461a8d15208ad7"
    print("expected:", expected)
    print("MATCH:", h == expected)
    return 0 if h == expected else 2


if __name__ == "__main__":
    sys.exit(main())
