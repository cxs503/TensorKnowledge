"""Fetch report_id=12445 markdown from the platform API and pin its sha256.

Work package: wp-12445-01 (task_type=01-asset-registration).
Only report 12445 is touched; the payload is written under runs/wp-12445-01/.

Usage:  python3 scripts/kf_wp12445_fetch.py
Output: runs/wp-12445-01/report_12445.json   (raw payload, as returned)
        runs/wp-12445-01/report_12445.md     (exact markdown bytes -> utf-8)
        runs/wp-12445-01/fetch_meta.json     (lengths + sha256 of the bytes)

Credentials come from env (TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE);
nothing is hardcoded.
"""
import hashlib
import json
import os
import pathlib
import urllib.request

REPORT_ID = "12445"
OUT = pathlib.Path("runs/wp-12445-01")
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _req(url, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data)
    if payload is not None:
        req.add_header("Content-Type", "application/json")
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
            d = _req(BASE + path, {"username": user, "password": pwd})
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tok = login()
    payload = _req(BASE + "/tensor/reports/" + REPORT_ID, token=tok)
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    if not isinstance(payload, dict):
        payload = {"raw": payload}

    md = payload.get("markdown")
    if not isinstance(md, str) or not md:
        raise SystemExit("FATAL: payload has no non-empty 'markdown' field")

    raw = md.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()

    (OUT / "report_12445.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    (OUT / "report_12445.md").write_bytes(raw)
    meta = {
        "report_id": REPORT_ID,
        "source_uri": "tensor://reports/" + REPORT_ID,
        "source_field": "markdown",
        "chars": len(md),
        "bytes_utf8": len(raw),
        "sha256": digest,
        "sha256_uri": "sha256:" + digest,
        "platform_title": payload.get("title"),
        "platform_summary_chars": len(payload.get("summary") or ""),
        "platform_figures": payload.get("figures"),
        "platform_tags": payload.get("tags"),
        "platform_scenario_key": payload.get("scenario_key"),
        "fetched_via": BASE + "/tensor/reports/" + REPORT_ID,
    }
    (OUT / "fetch_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()