#!/usr/bin/env python3
"""wp-9503-01: publish the KF-RESULT report to the platform (/tensor/reports).

Body = docs/kf/wp-9503-01/KF-RESULT-wp-9503-01.md verbatim (it already carries the single json
block holding the kf_result.v1 envelope). The locator map png is embedded as base64 in `figures`
so the report is self-contained. Credentials come from the environment; nothing secret is written
to the tree. Idempotent: refuses to publish twice for the same package (looks for an existing
report carrying the kf-wp tag).

Usage: python3 scripts/kf_wp9503_01_publish.py [--force]
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ID = "wp-9503-01"
REPORT_ID = "9503"
TASK_MISSION_ID = 15644
MD_PATH = ROOT / "docs" / "kf" / PACKAGE_ID / ("KF-RESULT-%s.md" % PACKAGE_ID)
PNG_PATH = ROOT / "docs" / "kf" / PACKAGE_ID / "figures" / "locator_map.png"
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def call(path: str, body: dict | None = None, tok: str | None = None, timeout: int = 180):
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = "Bearer " + tok
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(API + path, data=data, headers=headers)
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def main() -> None:
    force = "--force" in sys.argv
    st, body = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                    "password": os.environ["TENSOR_AGENT_PASS"]})
    if st != 200:
        raise SystemExit("login failed: %s %s" % (st, body[:300]))
    tok = json.loads(body)["access_token"]

    if not force:
        st, body = call("/tensor/reports?limit=200", tok=tok)
        if st == 200:
            try:
                rows = json.loads(body)
                rows = rows.get("data", rows) if isinstance(rows, dict) else rows
                dup = [r.get("id") for r in rows
                       if isinstance(r, dict) and r.get("title") == "KF-RESULT " + PACKAGE_ID]
                if dup:
                    raise SystemExit("already published as report(s) %s -- use --force" % dup)
            except json.JSONDecodeError:
                pass

    markdown = MD_PATH.read_text(encoding="utf-8")
    png = base64.b64encode(PNG_PATH.read_bytes()).decode("ascii")
    payload = {
        "title": "KF-RESULT " + PACKAGE_ID,
        "summary": (
            "wp-9503-01 (01-asset-registration, report 9503): markdown sha256 195c350d…8b5c "
            "recomputed and bit-identical to the contract hash (chars 8176); 22 assets registered "
            "(13 resolved_in_source / 8 referenced_unresolved / 1 declared_absent) with verbatim "
            "unique locators; 4 record figures have metadata but no bytes (figures/artifacts "
            "routes 404 → no figure hash claimed); claims=[] by contract; nothing marked verified."
        ),
        "scenario_key": "p73w2b-n02-eexi-closed-loop",
        "mission_id": TASK_MISSION_ID,
        "tags": ["kf-wp:" + PACKAGE_ID, "01-asset-registration", "report:9503",
                 "lane:B", "draft", "knowledge-factory", "EEXI"],
        "markdown": markdown,
        "figures": [{
            "name": "wp-9503-01-locator-map",
            "caption": ("report 9503 资产定位图：22 条资产在 152 行原文上的行区间条"
                        "（蓝=resolved_in_source / 橙=referenced_unresolved / 红=declared_absent），"
                        "虚线=章节起点；右面板=完整性预检（contract hash、chars、引文唯一性、"
                        "字符区间回环、图字节可得性计数）"),
            "png_base64": png,
        }],
    }
    st, resp = call("/tensor/reports", payload, tok)
    print("POST /tensor/reports ->", st)
    print(resp[:600])
    if st not in (200, 201):
        raise SystemExit("publish failed")
    md_sha = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    print("published markdown sha256=%s chars=%d" % (md_sha, len(markdown)))


if __name__ == "__main__":
    main()