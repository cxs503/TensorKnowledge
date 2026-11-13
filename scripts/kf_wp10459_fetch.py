"""Fetch report 10459 markdown from the platform API and verify its sha256.

Work package: wp-10459-01 (task_type 01-asset-registration).
Never hardcodes credentials: uses env TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE.

Usage: python3 scripts/kf_wp10459_fetch.py
Outputs:
  runs/wp-10459-01/report_10459.json  (raw API payload)
  runs/wp-10459-01/report_10459.md    (markdown field, byte-identical to what was hashed)
"""
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

REPORT_ID = "10459"
EXPECTED_HASH = "08c1a0cfb3f0db38ad3a473ac2155001589bde91c1f85c21db1d29863ca84f6c"
OUT = pathlib.Path("runs/wp-10459-01")
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _post_json(url, payload):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
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
        sys.exit("unexpected payload type: %r" % type(payload))
    md = payload.get("markdown") or ""
    if not md:
        sys.exit("empty markdown field for report %s" % REPORT_ID)

    (OUT / "report_10459.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "report_10459.md").write_text(md, encoding="utf-8")

    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    print("chars=%d bytes_utf8=%d" % (len(md), len(md.encode("utf-8"))))
    print("sha256=%s" % digest)
    print("contract=%s" % EXPECTED_HASH)
    print("hash_matches_contract=%s" % (digest == EXPECTED_HASH))
    print("title=%r" % payload.get("title"))
    print("scenario_key=%r" % payload.get("scenario_key"))
    if digest != EXPECTED_HASH:
        sys.exit("SHA256 MISMATCH -- refuse to register assets from a different payload")


if __name__ == "__main__":
    main()