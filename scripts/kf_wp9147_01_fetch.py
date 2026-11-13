"""wp-9147-01: fetch report 9147 markdown from the platform API and verify sha256.

Scope guard: touches report_id=9147 only (read-only GET on that single resource).
Credentials come from env (TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE);
nothing is hardcoded.

Outputs (worktree-internal):
  runs/wp-9147-01/report_9147.json   raw API payload
  runs/wp-9147-01/report_9147.md     markdown field, byte-exact
  runs/wp-9147-01/report_9147.meta.json  id/title/scenario/chars/sha256

Exit code 0 = sha256 equals the contract source_hash; 2 = mismatch; 1 = fetch error.
"""
import hashlib
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

REPORT_ID = "9147"
EXPECTED = "754d613193b8da4880f56371095812b6865d4d376bdca5edb8ab4f4ceb6d0ff6"
CONTRACT_TITLE = "P77-N03: EEXI/CII Green Compliance Machine Judgment Gate Maturation"
CONTRACT_SCENARIO = "P77-N03"
CONTRACT_CHARS = 1649

OUT = pathlib.Path("runs/wp-9147-01")
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
    last = None
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = _post_json(BASE + path, {"username": user, "password": pwd})
        except urllib.error.HTTPError as exc:
            last = exc
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    if last:
        print("login failed:", last, file=sys.stderr)
    return None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tok = login()
    try:
        payload = _get_json(BASE + "/tensor/reports/" + REPORT_ID, tok)
    except urllib.error.HTTPError as exc:
        print("ERROR fetching report:", exc, file=sys.stderr)
        return 1
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    (OUT / "report_9147.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    md = payload.get("markdown") or ""
    if not md:
        print("ERROR: markdown empty; keys=", list(payload), file=sys.stderr)
        return 1
    # write bytes exactly as received (no newline translation)
    (OUT / "report_9147.md").write_bytes(md.encode("utf-8"))
    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    meta = {
        "report_id": str(payload.get("id", REPORT_ID)),
        "title": payload.get("title"),
        "scenario_key": payload.get("scenario_key"),
        "chars": len(md),
        "bytes_utf8": len(md.encode("utf-8")),
        "sha256": digest,
        "expected_sha256": EXPECTED,
        "hash_matches_contract": digest == EXPECTED,
        "title_matches_contract": payload.get("title") == CONTRACT_TITLE,
        "scenario_matches_contract": payload.get("scenario_key") == CONTRACT_SCENARIO,
        "chars_matches_contract": len(md) == CONTRACT_CHARS,
        "platform_figures": payload.get("figures"),
        "platform_tags": payload.get("tags"),
        "payload_keys": sorted(payload.keys()),
    }
    (OUT / "report_9147.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    for k in ("report_id", "title", "scenario_key", "chars", "bytes_utf8", "sha256"):
        print(k, "=", meta[k])
    print("hash_matches_contract =", meta["hash_matches_contract"])
    return 0 if meta["hash_matches_contract"] else 2


if __name__ == "__main__":
    sys.exit(main())