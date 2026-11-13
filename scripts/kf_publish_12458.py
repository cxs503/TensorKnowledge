#!/usr/bin/env python3
"""wp-12458-01: publish the KF-RESULT report to the platform.

Body = runs/wp-12458-01/report_markdown.md verbatim (it already carries the single json block).
Credentials come from the environment; nothing secret is written to the tree.
No figures: this package is asset registration only (declared in §5).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
MD_PATH = "runs/wp-12458-01/report_markdown.md"
PACKAGE_ID = "wp-12458-01"


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
            f"{PACKAGE_ID} (01-asset-registration, report 12458): report markdown sha256 recomputed "
            "and equal to the contract hash (e82df280…); 3 source assets registered (A01 full doc / "
            "A02 heading / A03 statement), all resolved_in_source; no claims extracted (claims=[] "
            "by contract); result envelope passes kf_result.v1 schema."
        ),
        "scenario_key": "test",
        "mission_id": 15746,
        "tags": ["kf-wp:" + PACKAGE_ID, "01-asset-registration", "report:12458",
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
