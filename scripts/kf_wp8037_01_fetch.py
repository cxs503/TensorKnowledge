#!/usr/bin/env python3
"""wp-8037-01 step 1: fetch report 8037 from the platform API and pin its bytes.

No credentials are hardcoded: TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS
are read from the environment.

Outputs (under runs/wp-8037-01/):
    report_8037.json  raw API payload (id/title/scenario_key/figures/tags/...)
    report_8037.md    the `markdown` field, written byte-for-byte (utf-8, no newline fixups)
    fetch_meta.json   measured sha256 / chars / bytes + the contract-declared targets

Usage: python3 scripts/kf_wp8037_01_fetch.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ID = "8037"
PACKAGE_ID = "wp-8037-01"
RUN_DIR = ROOT / "runs" / PACKAGE_ID

# contract-declared identity (from the work-package YAML). Comparison targets only.
CONTRACT_SOURCE_HASH = "sha256:1e44804da4c51cf5e17cb6db345e3f414ffa55321b8f3e8b3a29d08e9c69c9b0"
CONTRACT_CHARS = 1223
CONTRACT_TITLE = "DEM Contact Mechanics Dual Verification (P27W3-N06)"
CONTRACT_SCENARIO = "dem_contact_mechanics_verification"


def api_base() -> str:
    base = os.environ.get("TENSOR_API_BASE")
    if not base:
        raise SystemExit("TENSOR_API_BASE not set")
    return base.rstrip("/")


def _req(url: str, body: dict | None = None, token: str | None = None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def login() -> str | None:
    user = os.environ.get("TENSOR_AGENT_USER")
    pwd = os.environ.get("TENSOR_AGENT_PASS")
    if not user or not pwd:
        return None
    last = None
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = _req(api_base() + path, {"username": user, "password": pwd})
        except Exception as exc:  # noqa: BLE001 - try the next endpoint
            last = exc
            continue
        tok = (d.get("access_token") or d.get("token")
               or (d.get("data") or {}).get("access_token"))
        if tok:
            return tok
    raise SystemExit("login failed: %r" % (last,))


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    tok = login()
    payload = _req(api_base() + "/tensor/reports/" + REPORT_ID, token=tok)
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    if not isinstance(payload, dict):
        raise SystemExit("unexpected payload type: %r" % type(payload))
    (RUN_DIR / "report_8037.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md = payload.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("payload has no str markdown field; keys=%s" % sorted(payload))
    raw = md.encode("utf-8")
    (RUN_DIR / "report_8037.md").write_bytes(raw)

    meta = {
        "report_id": REPORT_ID,
        "package_id": PACKAGE_ID,
        "retrieved_via": "GET %s/tensor/reports/%s" % (api_base(), REPORT_ID),
        "measured": {
            "sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
            "chars": len(md),
            "bytes_utf8": len(raw),
            "title": payload.get("title"),
            "scenario_key": payload.get("scenario_key"),
            "figures": len(payload.get("figures") or []),
            "tags": payload.get("tags"),
        },
        "contract_declared": {
            "sha256": CONTRACT_SOURCE_HASH,
            "chars": CONTRACT_CHARS,
            "title": CONTRACT_TITLE,
            "scenario_key": CONTRACT_SCENARIO,
        },
    }
    m, c = meta["measured"], meta["contract_declared"]
    meta["checks"] = {
        "hash_matches_contract": m["sha256"] == c["sha256"],
        "chars_matches_contract": m["chars"] == c["chars"],
        "title_matches_contract": (m["title"] or "").strip() == c["title"].strip(),
        "scenario_key_matches_contract": (m["scenario_key"] or "").strip() == c["scenario_key"].strip(),
    }
    (RUN_DIR / "fetch_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    if not meta["checks"]["hash_matches_contract"]:
        print("FATAL: source hash does not match the contract", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())