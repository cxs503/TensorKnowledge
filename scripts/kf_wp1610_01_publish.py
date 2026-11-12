#!/usr/bin/env python3
"""wp-1610-01: publish the KF-RESULT report to the platform.

Body = docs/kf_result_wp-1610-01.md verbatim (it already carries the single json block).
Credentials come from the environment; nothing secret is written to the tree.
No figures: this package is asset registration only (declared in §5).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
MD_PATH = "docs/kf_result_wp-1610-01.md"
PACKAGE_ID = "wp-1610-01"


def call(path: str, body: dict | None, tok: str | None = None, timeout: int = 120):
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(API + path, data=data, headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def main() -> None:
    st, body = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                    "password": os.environ["TENSOR_AGENT_PASS"]})
    assert st == 200, (st, body[:400])
    tok = json.loads(body)["access_token"]

    markdown = open(MD_PATH, encoding="utf-8").read()
    payload = {
        "title": f"KF-RESULT {PACKAGE_ID}",
        "summary": (
            f"{PACKAGE_ID} (01-asset-registration, report 1610): report markdown sha256 recomputed "
            "and equal to the contract hash; 3 record figures + 3 declared artifact paths registered; "
            "15/15 quoted excerpts resolve verbatim; no claims extracted (claims=[] by contract)."
        ),
        "scenario_key": "cmaes_literature_verification",
        "mission_id": 15530,
        "tags": ["kf-wp:" + PACKAGE_ID, "01-asset-registration", "report:1610",
                 "lane:C", "draft", "knowledge-factory"],
        "markdown": markdown,
        "figures": [],
    }
    st, resp = call("/tensor/reports", payload, tok)
    print(st, resp[:600])
    if st not in (200, 201):
        raise SystemExit("publish failed")


if __name__ == "__main__":
    main()