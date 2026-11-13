#!/usr/bin/env python3
"""wp-12044-01: publish the KF-RESULT report to the platform (single result channel).

Body = docs/kf/wp-12044-01/report_body.md verbatim (it already carries exactly one
```json block). The figure is embedded as png_base64 with its manifest-computed caption.

After creating the report the script re-fetches it and asserts:
  * title == "KF-RESULT wp-12044-01" and the kf-wp tag is present
  * the stored markdown contains exactly one ```json block and it parses to a dict whose
    package_id/report_id/provenance.source_hash match docs/kf/wp-12044-01/kf_result.json
  * source report 12044 is untouched (its markdown sha256 is unchanged)

Usage: python3 scripts/kf_wp12044_01_publish.py [--dry-run]
Credentials: environment only, never written to disk.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-12044-01"
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
PACKAGE_ID = "wp-12044-01"
MISSION_ID = 15737
SRC_REPORT = "12044"
SRC_HASH = "74cbbb52b6682ff4bb865490e1b4cce8511d023ed1a48afa19a9f2d22a0220b6"


def call(path: str, body: dict | None = None, tok: str | None = None, timeout: int = 120):
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = "Bearer " + tok
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(API + path, data=data, headers=headers,
                                method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def main() -> int:
    markdown = (PKG / "report_body.md").read_text(encoding="utf-8")
    result = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
    figs_meta = json.loads((PKG / "figures.json").read_text(encoding="utf-8"))
    manifest = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))

    blocks = re.findall(r"```json\s*\n(.*?)```", markdown, flags=re.S)
    if len(blocks) != 1 or json.loads(blocks[0]) != result:
        raise SystemExit("pre-publish: body does not carry exactly kf_result.json")

    figures = []
    for meta in figs_meta:
        png = (PKG / meta["figure"]).read_bytes()
        if hashlib.sha256(png).hexdigest() != meta["sha256"]:
            raise SystemExit("pre-publish: figure digest drift " + meta["figure"])
        figures.append({"name": meta["figure"], "caption": meta["caption"],
                        "png_base64": base64.b64encode(png).decode()})

    payload = {
        "title": "KF-RESULT " + PACKAGE_ID,
        "summary": (
            "wp-12044-01 (01-asset-registration, report 12044): markdown sha256 recomputed locally and "
            "equal to the contract source_hash; 4 assets registered with character-precise verbatim "
            "locators (source_document / timestamp_token / intent_statement / figure_declaration); "
            "3 resolved_in_source, 1 referenced_unresolved (figure name+caption only, figures endpoint "
            "404); claims=[] by contract (no extraction, no verification marking)."
        ),
        "scenario_key": None,
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:" + PACKAGE_ID, "01-asset-registration", "report:" + SRC_REPORT,
                 "lane:C", "draft", "knowledge-factory"],
        "markdown": markdown,
        "figures": figures,
    }

    if "--dry-run" in sys.argv:
        probe = dict(payload)
        probe["markdown"] = "<%d chars>" % len(markdown)
        probe["figures"] = [{k: v for k, v in f.items() if k != "png_base64"} for f in figures]
        print(json.dumps(probe, ensure_ascii=False, indent=2))
        return 0

    st, body = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                    "password": os.environ["TENSOR_AGENT_PASS"]})
    if st != 200:
        raise SystemExit("login failed: %s %s" % (st, body[:300]))
    tok = json.loads(body)["access_token"]

    st, resp = call("/tensor/reports", payload, tok)
    print("POST /tensor/reports ->", st)
    if st not in (200, 201):
        raise SystemExit("publish failed: " + resp[:600])
    created = json.loads(resp)
    if isinstance(created.get("data"), dict):
        created = created["data"]
    new_id = created.get("id")
    (PKG / "publish_receipt.json").write_text(
        json.dumps({"status": st, "created_report_id": new_id, "title": payload["title"],
                    "tags": payload["tags"], "mission_id": MISSION_ID,
                    "markdown_chars": len(markdown),
                    "figures": [f["name"] for f in figures],
                    "source_report_untouched": SRC_REPORT}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    # ---- post-publication self-check (independent re-fetch) ----------------
    st2, back = call("/tensor/reports/%s" % new_id, None, tok)
    if st2 != 200:
        raise SystemExit("re-fetch of created report failed: %s" % st2)
    rec = json.loads(back)
    if isinstance(rec.get("data"), dict):
        rec = rec["data"]
    md2 = rec.get("markdown") or ""
    b2 = re.findall(r"```json\s*\n(.*?)```", md2, flags=re.S)
    assert rec.get("title") == "KF-RESULT " + PACKAGE_ID, rec.get("title")
    assert any(t.startswith("kf-wp:") for t in (rec.get("tags") or [])), rec.get("tags")
    assert len(b2) == 1, "stored markdown has %d json blocks" % len(b2)
    assert md2 == markdown, "stored markdown differs from the local body (chars %d vs %d)" % (
        len(md2), len(markdown))
    parsed = json.loads(b2[0])
    assert parsed["package_id"] == PACKAGE_ID and parsed["report_id"] == SRC_REPORT
    assert parsed["provenance"]["source_hash"] == "sha256:" + SRC_HASH

    st3, back3 = call("/tensor/reports/" + SRC_REPORT, None, tok)
    src = json.loads(back3)
    if isinstance(src.get("data"), dict):
        src = src["data"]
    src_hash = hashlib.sha256((src.get("markdown") or "").encode()).hexdigest()
    assert src_hash == SRC_HASH, "source report 12044 changed!"

    print("created report id:", new_id)
    print("stored markdown == local body (%d chars), one json block == kf_result.json, title/tags ok"
          % len(md2))
    print("source report 12044 markdown sha256 unchanged:", src_hash)
    print("asset counts:", manifest["counts"]["by_resolution"])
    return 0


if __name__ == "__main__":
    sys.exit(main())