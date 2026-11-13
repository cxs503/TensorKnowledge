#!/usr/bin/env python3
"""wp-10542-01: publish the KF-RESULT report to the platform, then verify the
published record round-trip (single ```json block, embedded envelope hash still
equal to report 10542's markdown sha256).

Body = docs/kf/wp-10542-01/KF-RESULT_wp-10542-01.md verbatim.
Credentials come from the environment; nothing secret is written to the tree.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
PACKAGE_ID = "wp-10542-01"
REPORT_ID = "10542"
MD_PATH = ROOT / "docs" / "kf" / PACKAGE_ID / ("KF-RESULT_%s.md" % PACKAGE_ID)
FIG_PATH = ROOT / "docs" / "kf" / PACKAGE_ID / "figures" / "fig_asset_locator_map.png"
MISSION_ID = 15685


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
    st, body = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                    "password": os.environ["TENSOR_AGENT_PASS"]})
    if st != 200:
        raise SystemExit("login %s %s" % (st, body[:300]))
    tok = json.loads(body)["access_token"]

    markdown = MD_PATH.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", markdown, re.S)
    if len(blocks) != 1:
        raise SystemExit("expected exactly 1 json block, got %d" % len(blocks))
    envelope = json.loads(blocks[0])
    if len(re.findall(r"```json", markdown)) != 1:
        raise SystemExit("more than one ```json fence in body")

    figures = []
    if FIG_PATH.exists():
        figures.append({
            "name": FIG_PATH.name,
            "caption": ("wp-10542-01 资产定位器地图：每个登记资产的逐字引文在原文 markdown 上的 char 跨度"
                        "（上）与按解析状态着色的资产清单（下）"),
            "png_base64": base64.b64encode(FIG_PATH.read_bytes()).decode(),
        })

    payload = {
        "title": "KF-RESULT " + PACKAGE_ID,
        "summary": (
            "wp-10542-01 (01-asset-registration, report 10542 动力定位DP能力评估): markdown sha256 "
            "recomputed = 87ad4490…ce43c matching the contract; 11 assets registered "
            "(1 source document + 2 figures with real PNG bytes pinned by sha256 + 8 declared upstream "
            "paths unresolved in this worktree); 11/11 locators re-resolve to exact bytes incl. "
            "occurrence index; claims=[] by contract (no extraction, no verified marks)."
        ),
        "scenario_key": "ship_dp_capability",
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:" + PACKAGE_ID, "KF-RESULT", "01-asset-registration",
                 "report:" + REPORT_ID, "lane:C", "draft", "knowledge-factory"],
        "markdown": markdown,
        "figures": figures,
    }
    st, resp = call("/tensor/reports", payload, tok)
    print("POST /tensor/reports ->", st, resp[:400])
    if st not in (200, 201):
        raise SystemExit("publish failed")
    new_id = json.loads(resp).get("id")

    # round-trip check on the published record
    st, resp = call("/tensor/reports/%s" % new_id, None, tok)
    if st != 200:
        raise SystemExit("round-trip GET failed: %s %s" % (st, resp[:200]))
    rec = json.loads(resp)
    body_md = rec["markdown"]
    got = re.findall(r"```json\n(.*?)\n```", body_md, re.S)
    rep_env = json.loads(got[0]) if len(got) == 1 else {}
    local_hash = "sha256:" + hashlib.sha256(
        (ROOT / "runs" / PACKAGE_ID / ("source_%s.md" % REPORT_ID)).read_bytes()).hexdigest()
    print(json.dumps({
        "published_report_id": new_id,
        "title": rec.get("title"),
        "tags_ok": ("kf-wp:" + PACKAGE_ID) in (rec.get("tags") or []),
        "json_blocks": len(got),
        "embedded_source_hash": rep_env.get("provenance", {}).get("source_hash"),
        "local_source_hash": local_hash,
        "hash_consistent": rep_env.get("provenance", {}).get("source_hash")
        == envelope["provenance"]["source_hash"] == local_hash,
        "status": rec.get("status"),
        "figures": [f.get("name") for f in (rec.get("figures") or [])],
        "body_bytes": len(body_md.encode("utf-8")),
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()