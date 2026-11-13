#!/usr/bin/env python3
"""wp-13612-01: publish the KF-RESULT report to the platform (the only result channel).

Body = docs/kf_result_wp-13612-01.md verbatim (it already carries the single ```json block
holding docs/kf/wp-13612-01/kf_result.json). Credentials come from the environment and
nothing secret is written into the tree. No figures: this package is registration only
(reason stated in section ⑤ of the body).
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
MD_PATH = "docs/kf_result_wp-13612-01.md"
PACKAGE_ID = "wp-13612-01"
REPORT_ID = "13612"
MISSION_ID = 15765


def call(path: str, body: dict | None, tok: str | None = None, timeout: int = 180):
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
    if markdown.count("```json") != 1:
        raise SystemExit(f"body must carry exactly one json block, found {markdown.count('```json')}")

    envelope = json.load(open("docs/kf/wp-13612-01/kf_result.json", encoding="utf-8"))
    man = envelope["outputs"]["asset_manifest.json"]
    counts = man["counts"]
    payload = {
        "title": f"KF-RESULT {PACKAGE_ID}",
        "summary": (
            f"{PACKAGE_ID} (01-asset-registration, source report {REPORT_ID}, lane C): markdown sha256 "
            f"{man['source']['hash']} recomputed and byte-equal to the contract hash ({man['source']['chars']} "
            f"chars); {counts['assets']} assets registered ({counts['resolved_in_source']} resolved in "
            f"source / {counts['referenced_unresolved']} referenced-unresolved / "
            f"{counts['declared_absent']} declared-absent) incl. 5 figures fetched HTTP 200 and bound to "
            "their payload sha256; every quote verbatim + unique; claims=[] by contract (no extraction, "
            "no report classification, nothing marked verified)."
        ),
        "scenario_key": man["source"]["scenario_key"],
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:" + PACKAGE_ID, "01-asset-registration", "report:" + REPORT_ID,
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