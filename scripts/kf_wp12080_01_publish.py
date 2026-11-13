#!/usr/bin/env python3
"""wp-12080-01: publish the KF-RESULT report to the platform.

Body = docs/wp-12080-01/KF-RESULT-wp-12080-01.md verbatim (it already carries the single
JSON fence with the kf_result.v1 envelope). Credentials come from the environment; nothing
secret is written into the tree. No figures: registration-only package (§5 states why).
"""
from __future__ import annotations

import json
import os
import pathlib
import urllib.error
import urllib.request

PKG = "wp-12080-01"
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
MD_PATH = pathlib.Path("docs") / PKG / ("KF-RESULT-%s.md" % PKG)


def call(path: str, body: dict | None, tok: str | None = None, timeout: int = 120):
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
    st, body = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                    "password": os.environ["TENSOR_AGENT_PASS"]})
    assert st == 200, (st, body[:400])
    tok = json.loads(body)["access_token"]

    markdown = MD_PATH.read_text(encoding="utf-8")
    payload = {
        "title": "KF-RESULT " + PKG,
        "summary": (
            "wp-12080-01 (01-asset-registration, report 12080): markdown sha256 re-computed "
            "= fe235db9…c93e0 and equal to the contract hash (7931 chars); 25 source assets "
            "registered (17 resolved_in_source / 7 referenced_unresolved / 1 declared_absent); "
            "every locator quote is a verbatim, unique md[start:end] slice; no claims extracted "
            "(claims=[] by contract); nothing marked verified."
        ),
        "scenario_key": "dp_time_domain",
        "mission_id": 15741,
        "tags": ["kf-wp:" + PKG, "01-asset-registration", "report:12080",
                 "lane:C", "draft", "knowledge-factory"],
        "markdown": markdown,
        "figures": [],
    }
    st, resp = call("/tensor/reports", payload, tok)
    print(st, resp[:800])
    if st not in (200, 201):
        raise SystemExit("publish failed")
    doc = json.loads(resp)
    rid = doc.get("id") or (doc.get("data") or {}).get("id")
    pathlib.Path("runs", PKG, "published_report.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2))
    print("published report_id =", rid)


if __name__ == "__main__":
    main()