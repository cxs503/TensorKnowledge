#!/usr/bin/env python3
"""Fetch report 14478 markdown once and pin it byte-for-byte (KF wp-14478-01, task_type=01-asset-registration).

Reads only report_id=14478 (work-package boundary: no other report_id is read or written).
Auth: TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS from the environment.
Outputs (inside the worktree):
  docs/wp-14478-01/source.md         byte-identical markdown of the report record field "markdown"
  docs/wp-14478-01/source_meta.json  record fields except markdown (title/summary/tags/figures/...)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

REPORT_ID = "14478"
CONTRACT_SOURCE_HASH = "8fbd643e2e79a0fece5f9ae2fbe87a0045f268d61da54927711e260c14b206b0"
CONTRACT_CHARS = 6156

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "wp-14478-01"


def api_base() -> str:
    return os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _request(url: str, method: str = "GET", body: dict | None = None, token: str | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def login() -> str:
    user = os.environ.get("TENSOR_AGENT_USER", "")
    password = os.environ.get("TENSOR_AGENT_PASS", "")
    if not user or not password:
        raise SystemExit("TENSOR_AGENT_USER / TENSOR_AGENT_PASS not set")
    payload = _request(api_base() + "/auth/login", "POST", {"username": user, "password": password})
    token = payload.get("access_token") or (payload.get("data") or {}).get("access_token")
    if not token:
        raise SystemExit("login response carried no access_token")
    return token


def fetch_report(report_id: str = REPORT_ID) -> dict:
    return _request(api_base() + f"/tensor/reports/{report_id}", token=login())


def fetch_markdown(report_id: str = REPORT_ID) -> tuple[str, dict]:
    record = fetch_report(report_id)
    md = record.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("report record has no string field 'markdown'")
    meta = {k: v for k, v in record.items() if k != "markdown"}
    return md, meta


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    md, meta = fetch_markdown()
    digest = sha256_hex(md)
    print(f"report_id={REPORT_ID} chars={len(md)} bytes_utf8={len(md.encode())} sha256={digest}")
    if digest != CONTRACT_SOURCE_HASH:
        print(f"FATAL: contract source_hash {CONTRACT_SOURCE_HASH} != fetched {digest}", file=sys.stderr)
        return 2
    if len(md) != CONTRACT_CHARS:
        print(f"FATAL: contract chars {CONTRACT_CHARS} != fetched {len(md)}", file=sys.stderr)
        return 2
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "source.md").write_text(md, encoding="utf-8", newline="")
    meta_out = {
        "report_id": REPORT_ID,
        "sha256": digest,
        "chars": len(md),
        "bytes_utf8": len(md.encode()),
        "record": meta,
    }
    (OUT_DIR / "source_meta.json").write_text(json.dumps(meta_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT_DIR/'source.md'} and {OUT_DIR/'source_meta.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())