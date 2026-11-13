#!/usr/bin/env python3
"""Publish the KF-RESULT report for wp-13325-01 to the platform.

Body/payload are rendered by scripts/kf_wp13325_01_report.py into
artifacts/wp-13325-01/report_payload.json (markdown carries the single ```json block
that equals artifacts/wp-13325-01/kf_result.json verbatim). Credentials come from the
environment only; nothing secret is written into the tree.

Run:  python3 scripts/kf_wp13325_01_publish.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request

API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "artifacts", "wp-13325-01")
MISSION_ID = 15758


def call(path: str, body: dict | None = None, tok: str | None = None, timeout: int = 180):
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = "Bearer " + tok
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(API + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(os.path.join(ART, "report_payload.json"), encoding="utf-8") as fh:
        payload = json.load(fh)
    payload["mission_id"] = MISSION_ID
    if args.dry_run:
        print(json.dumps({k: (v if k != "markdown" and k != "figures" else f"<{len(v)}>")
                          for k, v in payload.items()}, ensure_ascii=False)[:800])
        return

    st, body = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                    "password": os.environ["TENSOR_AGENT_PASS"]})
    if st != 200:
        raise SystemExit(f"login failed: {st} {body[:300]}")
    tok = json.loads(body)["access_token"]
    st, body = call("/tensor/reports", payload, tok)
    print(st, body[:600])
    if st not in (200, 201):
        raise SystemExit("publish failed")


if __name__ == "__main__":
    main()