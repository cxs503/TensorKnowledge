"""Generic KF report fetcher: GET /tensor/reports/<id>, persist markdown + raw payload, verify sha256.

Generalises scripts/kf_fetch_448.py (report-agnostic; nothing else changed in the flow).

Usage:
  python3 scripts/kf_fetch_report.py <report_id> [expected_sha256_hex] [--run-dir DIR]

Outputs (default run dir runs/wp-<id>-01/):
  report_<id>.json  raw API payload (normalised: unwraps {"data": {...}} once)
  report_<id>.md    the markdown field, byte-identical to what the platform hashes
Never hardcodes credentials: env TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE.
Exit codes: 0 = fetched and hash matches (or no hash given), 2 = hash mismatch, 1 = markdown empty.
"""
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _post_json(url, payload, token=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
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
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
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


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    rid = str(argv[1])
    expected = (argv[2].split(":", 1)[-1].strip() if len(argv) > 2 and argv[2] else "")
    run_dir = pathlib.Path("runs/wp-%s-01" % rid)
    if "--run-dir" in argv:
        run_dir = pathlib.Path(argv[argv.index("--run-dir") + 1])
    run_dir.mkdir(parents=True, exist_ok=True)

    tok = login()
    payload = _get_json(BASE + "/tensor/reports/" + rid, tok)
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    if not isinstance(payload, dict):
        payload = {"raw": payload}
    (run_dir / ("report_%s.json" % rid)).write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    md = payload.get("markdown") or ""
    if not md:
        print("ERROR: markdown field empty; keys=", list(payload))
        return 1
    (run_dir / ("report_%s.md" % rid)).write_text(md)
    h = hashlib.sha256(md.encode()).hexdigest()
    print("report_id:", payload.get("id"))
    print("title:", payload.get("title"))
    print("chars(markdown):", len(md))
    print("bytes(utf-8):", len(md.encode()))
    print("sha256(markdown):", h)
    if expected:
        print("expected:", expected)
        print("MATCH:", h == expected)
        return 0 if h == expected else 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))