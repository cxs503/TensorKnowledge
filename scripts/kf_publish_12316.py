#!/usr/bin/env python3
"""Publish the wp-12316-01 asset registration results to the platform.

Reads the locally produced asset_manifest.json and kf_result envelope, validates them one final
time, then POSTs the result envelope to the platform's KF result endpoint.

Usage: python3 scripts/kf_publish_12316.py [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "wp-12316-01"
PACKAGE_ID = "wp-12316-01"
REPORT_ID = "12316"


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


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def preflight_check() -> list[str]:
    """Run basic sanity checks before publishing."""
    errors: list[str] = []
    manifest_path = OUT / "asset_manifest.json"
    envelope_path = OUT / "kf_result.wp-12316-01.json"
    source_path = OUT / "report.md"

    if not manifest_path.exists():
        errors.append("asset_manifest.json not found")
    if not envelope_path.exists():
        errors.append("kf_result.wp-12316-01.json not found")
    if not source_path.exists():
        errors.append("report.md not found")

    if errors:
        return errors

    manifest = json.loads(manifest_path.read_text())
    envelope = json.loads(envelope_path.read_text())
    source = source_path.read_text()

    # Hash check
    computed = sha256_hex(source)
    if computed != manifest["source"]["hash"]:
        errors.append(f"source hash mismatch: computed={computed}, manifest={manifest['source']['hash']}")

    # Package ID check
    if manifest["package_id"] != PACKAGE_ID:
        errors.append(f"package_id mismatch: {manifest['package_id']} != {PACKAGE_ID}")
    if envelope["package_id"] != PACKAGE_ID:
        errors.append(f"envelope package_id mismatch")

    # Claims must be empty for task_type 01
    if manifest.get("claims"):
        errors.append("claims must be empty for task_type=01")

    return errors


def publish(dry_run: bool = False) -> int:
    errors = preflight_check()
    if errors:
        print("Preflight checks FAILED:")
        for e in errors:
            print(f"  ❌ {e}")
        return 1

    print("Preflight checks PASSED")

    envelope = json.loads((OUT / "kf_result.wp-12316-01.json").read_text())

    if dry_run:
        print(f"[DRY RUN] Would POST envelope to {api_base()}/kf/results")
        print(f"  package_id: {PACKAGE_ID}")
        print(f"  report_id: {REPORT_ID}")
        print(f"  task_type: {envelope['task_type']}")
        print(f"  assets: {len((OUT / 'asset_manifest.json').read_text())} bytes")
        return 0

    try:
        token = login()
        url = api_base() + "/kf/results"
        payload = {
            "package_id": PACKAGE_ID,
            "report_id": REPORT_ID,
            "task_type": envelope["task_type"],
            "envelope": envelope,
        }
        resp = _request(url, "POST", payload, token=token)
        print(f"Published successfully: {resp}")
        return 0
    except Exception as exc:
        print(f"Publish failed: {exc}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish wp-12316-01 results to platform")
    parser.add_argument("--dry-run", action="store_true", help="Validate without posting")
    args = parser.parse_args()
    return publish(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
