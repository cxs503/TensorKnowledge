"""Fetch report 11930 markdown from the TensorPlatform API into docs/kf/wp-11930-01/.

Zero hand-copying: the markdown comes straight from the platform (or, as a
fallback, from the local Postgres DB), is written verbatim to disk, and the
sha256 is recomputed locally so the contract source_hash can be checked.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.request

OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "docs" / "kf" / "wp-11930-01"
REPORT_ID = "11930"


def api_login(base: str) -> str:
    user = os.environ["TENSOR_AGENT_USER"]
    pwd = os.environ["TENSOR_AGENT_PASS"]
    body = json.dumps({"username": user, "password": pwd}).encode()
    req = urllib.request.Request(
        base + "/auth/login",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode())
    for key in ("access_token", "token", "jwt"):
        if isinstance(payload, dict) and payload.get(key):
            return payload[key]
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, dict):
        for key in ("access_token", "token", "jwt"):
            if data.get(key):
                return data[key]
    raise SystemExit("no token in login response: %r" % (list(payload),))


def fetch_report(base: str, token: str) -> dict:
    req = urllib.request.Request(
        base + "/tensor/reports/" + REPORT_ID,
        headers={"Authorization": "Bearer " + token},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode())
    if isinstance(payload, dict) and "data" in payload and "markdown" not in payload:
        payload = payload["data"]
    return payload


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    token = api_login(base)
    rec = fetch_report(base, token)
    md = rec["markdown"]
    raw = md.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()

    (OUT_DIR / "source_11930.md").write_bytes(raw)
    meta = {
        "report_id": REPORT_ID,
        "title": rec.get("title"),
        "scenario_key": rec.get("scenario_key"),
        "chars": len(md),
        "bytes_utf8": len(raw),
        "sha256": digest,
        "fields_present": sorted(k for k in rec.keys()),
        "figures": rec.get("figures"),
        "tags": rec.get("tags"),
    }
    (OUT_DIR / "source_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())