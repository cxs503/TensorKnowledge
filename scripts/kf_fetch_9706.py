"""Fetch report 9706 from the platform API and verify its markdown sha256.

Work package wp-9706-01 (task_type 01-asset-registration), report_id 9706 only.
Never hardcodes credentials: uses env TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE.

Usage: python3 scripts/kf_fetch_9706.py
Outputs: runs/wp-9706-01/report_9706.json (raw API payload), runs/wp-9706-01/report_9706.md
"""
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

REPORT_ID = "9706"
PACKAGE_ID = "wp-9706-01"
EXPECTED_HASH = "7d0e024b8630cd3390f5efc0c3f5abfb467e85a869c78126bbb210a1a2d13534"
EXPECTED_CHARS = 12546

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
    (OUT / f"report_{REPORT_ID}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = payload.get("markdown")
    if not isinstance(md, str) or not md:
        print("FATAL: no markdown field in payload keys=%s" % sorted(payload)[:20])
        return 2
    raw = md.encode("utf-8")
    (OUT / f"report_{REPORT_ID}.md").write_bytes(raw)
    got = hashlib.sha256(raw).hexdigest()
    print(f"report_id={REPORT_ID} title={payload.get('title')!r}")
    print(f"scenario_key={payload.get('scenario_key')!r} chars={len(md)} bytes_utf8={len(raw)}")
    print(f"sha256={got}")
    print(f"expected={EXPECTED_HASH} match={got == EXPECTED_HASH}")
    print(f"chars_expected={EXPECTED_CHARS} match={len(md) == EXPECTED_CHARS}")
    return 0 if got == EXPECTED_HASH else 1


if __name__ == "__main__":
    sys.exit(main())