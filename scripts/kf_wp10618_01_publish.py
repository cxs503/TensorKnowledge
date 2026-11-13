#!/usr/bin/env python3
"""Publish docs/kf/wp-10618-01/result.md as the single KF-RESULT report for wp-10618-01.

    python3 scripts/kf_wp10618_01_publish.py

Only creates ONE new report (title "KF-RESULT wp-10618-01", tags kf-wp:wp-10618-01).
Report 10618 and every other report_id are read-only for this package.
After publishing, re-fetches the new report and re-verifies byte-identity of the
markdown and of the embedded JSON envelope against the local artefacts.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = "wp-10618-01"
OUT = ROOT / "docs" / "kf" / PKG
RESULT_MD = OUT / "result.md"
ENVELOPE = OUT / "kf_result.json"
FIG = OUT / "figures" / "wp10618_01_asset_map.png"
SOURCE_REPORT = "10618"
SCENARIO = "p485w1-n07-spp-ice-stability"
MISSION_ID = 15687


def _api(path: str) -> str:
    return os.environ["TENSOR_API_BASE"].rstrip("/") + path


def call(path: str, payload=None, tok=None, timeout=120):
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = "Bearer " + tok
    req = urllib.request.Request(_api(path), data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def main() -> None:
    st, body = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                    "password": os.environ["TENSOR_AGENT_PASS"]})
    if st != 200:
        raise SystemExit("login failed: %s %s" % (st, body[:300]))
    tok = json.loads(body)["access_token"]

    md = RESULT_MD.read_text(encoding="utf-8")
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    n_json = len(re.findall(r"```json\n", md))
    if n_json != 1:
        raise SystemExit("result.md must carry exactly one ```json block, found %d" % n_json)
    assets = env["outputs"]["asset_manifest.json"]["counts"]

    fig_b64 = base64.b64encode(FIG.read_bytes()).decode()
    payload = {
        "title": "KF-RESULT %s" % PKG,
        "summary": (
            "%s (01-asset-registration, source report %s): source markdown sha256 recomputed and "
            "equal to the contract hash; %d assets registered (%d resolved in source, %d referenced "
            "but unresolved: 4 figures on dead /tmp paths, 2 cross-repo code refs, 4 test ids, "
            "3 standards); claims=[] by contract (classify_report_type=false); no verified marks. "
            "18/18 locator quotes re-resolved against a second independent fetch."
            % (PKG, SOURCE_REPORT, assets["assets"], assets["resolved_in_source"],
               assets["referenced_unresolved"])
        ),
        "scenario_key": SCENARIO,
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:" + PKG, "kf-result", "01-asset-registration", "report:" + SOURCE_REPORT,
                 "lane:C", "draft", "knowledge-factory"],
        "markdown": md,
        "figures": [{
            "name": "wp10618_01_asset_map.png",
            "caption": "wp-10618-01 asset inventory (left: class x resolution; right: char-span "
                       "locator map over the 7463-char source markdown)",
            "png_base64": fig_b64,
        }],
    }
    st, resp = call("/tensor/reports", payload, tok)
    print("POST /tensor/reports ->", st, resp[:400])
    if st not in (200, 201):
        raise SystemExit("publish failed")
    new_id = json.loads(resp).get("id")

    st2, body2 = call("/tensor/reports/%s" % new_id, tok=tok)
    rec = json.loads(body2)
    got = rec.get("markdown") or ""
    roundtrip = hashlib.sha256(got.encode("utf-8")).hexdigest() == \
        hashlib.sha256(md.encode("utf-8")).hexdigest()
    blocks = re.findall(r"```json\n(.*?)\n```", got, re.S)
    embedded = json.loads(blocks[0]) if blocks else {}
    same_env = embedded == env
    out = {
        "published_report_id": new_id,
        "title": rec.get("title"),
        "tags": rec.get("tags"),
        "scenario_key": rec.get("scenario_key"),
        "mission_id": rec.get("mission_id"),
        "markdown_sha256": "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest(),
        "markdown_roundtrip_identical": roundtrip,
        "embedded_envelope_equals_local_kf_result": same_env,
        "figures_posted": len(rec.get("figures") or []),
        "source_report_untouched": SOURCE_REPORT,
    }
    ledger_path = OUT / "publish.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {}
    pubs = ledger.get("publications", [])
    if not pubs and ledger.get("published_report_id"):
        # legacy single-entry ledger (first publication of this package)
        pubs = [{"published_report_id": ledger["published_report_id"],
                 "markdown_sha256": ledger.get("markdown_sha256"),
                 "markdown_roundtrip_identical": ledger.get("markdown_roundtrip_identical"),
                 "embedded_envelope_equals_local_kf_result":
                     ledger.get("embedded_envelope_equals_local_kf_result"),
                 "figures_posted": ledger.get("figures_posted")}]
    pubs = [p for p in pubs if p.get("published_report_id") != new_id]
    pubs.append({
        "published_report_id": new_id,
        "markdown_sha256": out["markdown_sha256"],
        "markdown_roundtrip_identical": roundtrip,
        "embedded_envelope_equals_local_kf_result": same_env,
        "figures_posted": out["figures_posted"],
    })
    out["publications"] = pubs
    out["authoritative_report_id"] = new_id
    out["supersedes"] = [p["published_report_id"] for p in pubs[:-1]]
    ledger_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if not (roundtrip and same_env):
        raise SystemExit("post-publish round-trip check FAILED")


if __name__ == "__main__":
    main()