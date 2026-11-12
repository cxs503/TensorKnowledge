#!/usr/bin/env python3
"""Re-check the already-published wp-3076-01 report (round trip, no duplicate publishing).

Reads the published id from docs/wp-3076-01/publish_roundtrip.json (written by
scripts/kf_publish_3076.py), re-fetches that report, re-extracts the single json block, compares it
with docs/wp-3076-01/kf_result.wp-3076-01.json, re-hashes report 3076 and probes the figure-payload
endpoint (positive control for the 404s recorded on report 3076). Rewrites publish_roundtrip.json.

Use this instead of re-running kf_publish_3076.py when the deliverable already exists — publishing
twice would leave two competing reports for one work package.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

import kf_fetch_3076 as fetch
import kf_publish_3076 as publish
import kf_verify_3076 as verify

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "wp-3076-01"


def main() -> int:
    current = json.loads((DOCS / "publish_roundtrip.json").read_text(encoding="utf-8"))
    report_id = current["published_report_id"]
    token = fetch.login()

    status, record = publish.call(f"/tensor/reports/{report_id}", token=token, method="GET")
    stored_md = record.get("markdown", "")
    block = publish.extract_json_block(stored_md)
    envelope = json.loads((DOCS / "kf_result.wp-3076-01.json").read_text(encoding="utf-8"))
    source, _ = fetch.fetch_markdown()
    fig_name = publish.FIGURES[0][0]
    fig_status, fig_bytes = publish.call_raw(f"/tensor/reports/{report_id}/figures/{fig_name}", token)

    recheck = {
        "published_report_id": report_id,
        "http_status": status,
        "json_block_round_trip_equal": block == envelope,
        "json_blocks_in_markdown": stored_md.count("```json"),
        "provenance_hash_equals_fresh_report_3076_hash": block["provenance"]["source_hash"]
        == "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "report_id_field": block["report_id"],
        "package_id_field": block["package_id"],
        "tags_stored": record.get("tags"),
        "figures_stored": [f.get("name") for f in record.get("figures", [])],
        "figures_have_png": [bool(f.get("png_base64")) for f in record.get("figures", [])],
        "figure_payload_exposed_in_record": any(f.get("png_base64") for f in record.get("figures", [])),
        "figure_endpoint_positive_control": {
            "report_id": report_id,
            "name": fig_name,
            "http_status": fig_status,
            "bytes": len(fig_bytes),
            "sha256": hashlib.sha256(fig_bytes).hexdigest(),
            "delivered_bytes_equal_local": fig_bytes == (DOCS / fig_name).read_bytes(),
            "note": "GET /tensor/reports/<id>/figures/<name> returns 200 here, so the 404 observed for report 3076 is a genuinely absent payload, not a wrong route",
        },
        "markdown_chars_stored": len(stored_md),
        "markdown_sha256_stored": hashlib.sha256(stored_md.encode("utf-8")).hexdigest(),
    }
    (DOCS / "publish_roundtrip.json").write_text(json.dumps(recheck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = (
        recheck["json_block_round_trip_equal"]
        and recheck["json_blocks_in_markdown"] == 1
        and recheck["provenance_hash_equals_fresh_report_3076_hash"]
        and recheck["report_id_field"] == "3076"
        and recheck["package_id_field"] == "wp-3076-01"
        and recheck["figure_endpoint_positive_control"]["http_status"] == 200
        and recheck["figures_stored"] == [n for n, _ in publish.FIGURES]
    )
    print(json.dumps(recheck, ensure_ascii=False, indent=2))
    print("round_trip_ok:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())