"""Fetch report 11478 markdown from the platform API and verify sha256 against the work-package contract.

Usage: python3 scripts/kf_fetch_11478.py
Outputs:
  runs/wp-11478-01/report_11478.json   raw API payload (record fields, no secrets)
  runs/wp-11478-01/report_11478.md     markdown field, byte-exact
  runs/wp-11478-01/fetch_11478.json    fetch metadata (hash, chars, bytes, field, endpoint)

Never hardcodes credentials: uses env TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE.
Exit codes: 0 ok, 2 sha256 mismatch (contract vs live markdown), 3 fetch failure.
"""
import hashlib
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

REPORT_ID = "11478"
OUT = pathlib.Path("runs/wp-11478-01")
EXPECTED_HASH = "b5b856a019926eb922be123bd6e34077d4a1b470775aa311e56761e680057258"
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


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        tok = login()
        payload = _get_json(f"{BASE}/tensor/reports/{REPORT_ID}", tok)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        print(f"FETCH FAILED: {exc}")
        return 3
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    if not isinstance(payload, dict):
        print("FETCH FAILED: unexpected payload shape")
        return 3

    md = payload.get("markdown")
    if not isinstance(md, str) or not md:
        print("FETCH FAILED: no markdown field")
        return 3

    (OUT / "report_11478.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    (OUT / "report_11478.md").write_text(md)

    digest = hashlib.sha256(md.encode()).hexdigest()
    meta = {
        "report_id": REPORT_ID,
        "endpoint": f"/tensor/reports/{REPORT_ID}",
        "source_field": "markdown",
        "chars": len(md),
        "bytes_utf8": len(md.encode()),
        "sha256": digest,
        "contract_source_hash": "sha256:" + EXPECTED_HASH,
        "hash_matches_contract": digest == EXPECTED_HASH,
        "title": payload.get("title"),
        "scenario_key": payload.get("scenario_key"),
        "figures_count": len(payload.get("figures") or []),
        "tags": payload.get("tags"),
        "record_keys": sorted(payload.keys()),
    }
    (OUT / "fetch_11478.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(json.dumps({k: meta[k] for k in ("chars", "bytes_utf8", "sha256", "hash_matches_contract")},
                     ensure_ascii=False))
    if digest != EXPECTED_HASH:
        print("SHA256 MISMATCH: live markdown differs from contract source_hash")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())