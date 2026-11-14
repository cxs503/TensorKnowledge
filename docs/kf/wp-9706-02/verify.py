#!/usr/bin/env python3
"""Independent re-check of work package wp-9706-02.

Deliberately does NOT import build.py or wp9706_data.py: it re-derives everything
from published artefacts only, so a bug in the builder cannot hide here.

Checks
  V1 source identity  — pull report 9706 from the platform API (fallback: local
                        cache) and recompute sha256; compare with the hash in the
                        result JSON *and* in the contract.
  V2 result structure — the KF-RESULT body must contain exactly one ```json block,
                        and it must validate against schemas/kf_result.v1.
  V3 locator search   — every quote must be found verbatim by plain substring
                        search, and its declared [start,end) must equal the found
                        position (offsets are the contract, not decoration).
  V4 id hygiene       — locator / claim / flag ids unique; every claim, flag,
                        grade note and per-signal reference points at a real id.
  V5 no verification  — no claim may claim a verified status (producer cannot).
  V6 hash binding     — content_hash == sha256(quote) for every locator.

Usage: python docs/kf/wp-9706-02/verify.py [--offline]
Exit code 0 = all pass, 1 = any failure.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

PKG = Path(__file__).resolve().parent
REPO = PKG.parents[2]
SOURCE_CACHE = REPO / "docs" / "kf" / "sources" / "9706.md"
EXPECTED = "sha256:7d0e024b8630cd3390f5efc0c3f5abfb467e85a869c78126bbb210a1a2d13534"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def api_token() -> str | None:
    base, user, pw = os.environ.get("TENSOR_API_BASE"), os.environ.get("TENSOR_AGENT_USER"), \
        os.environ.get("TENSOR_AGENT_PASS")
    if not (base and user and pw):
        return None
    req = urllib.request.Request(
        f"{base}/auth/login",
        data=json.dumps({"username": user, "password": pw}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())["access_token"]
    except Exception as exc:  # noqa: BLE001 - offline fallback is legitimate
        print(f"(login failed: {exc}; falling back to local cache)")
        return None


def fetch_source(offline: bool) -> tuple[str, str]:
    """Return (text, provenance_note)."""
    if not offline:
        tok = api_token()
        if tok:
            base = os.environ["TENSOR_API_BASE"]
            req = urllib.request.Request(f"{base}/tensor/reports/9706",
                                         headers={"Authorization": f"Bearer {tok}"})
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    rec = json.loads(r.read())
                return rec["markdown"], "platform API /tensor/reports/9706"
            except Exception as exc:  # noqa: BLE001
                print(f"(report fetch failed: {exc}; falling back to local cache)")
    return SOURCE_CACHE.read_text(encoding="utf-8"), f"local cache {SOURCE_CACHE}"


def main() -> int:
    offline = "--offline" in sys.argv
    text, prov = fetch_source(offline)
    actual = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

    kf = json.loads((PKG / "kf_result.wp-9706-02.json").read_text(encoding="utf-8"))
    contract = json.loads((PKG / "work-package.json").read_text(encoding="utf-8"))
    report = (PKG / "KF-RESULT-wp-9706-02.md").read_text(encoding="utf-8")

    check("V1.source_hash_recomputed", actual == EXPECTED,
          f"{actual} from {prov} ({len(text)} chars)")
    check("V1.hash_in_result", kf["provenance"]["source_hash"] == actual,
          kf["provenance"]["source_hash"])
    check("V1.hash_in_contract", contract["input"]["source_hash"] == actual,
          contract["input"]["source_hash"])

    blocks = re.findall(r"```json\n(.*?)\n```", report, flags=re.S)
    check("V2.single_json_block", len(blocks) == 1, f"{len(blocks)} block(s)")
    embedded = json.loads(blocks[0]) if blocks else {}
    system_schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json")
                              .read_text(encoding="utf-8"))
    import jsonschema
    err = None
    try:
        jsonschema.validate(embedded, system_schema)
    except jsonschema.ValidationError as exc:  # pragma: no cover
        err = exc.message
    check("V2.kf_result_schema", err is None, err or "kf_result.v1 valid")
    check("V2.block_equals_file", embedded == kf, "report JSON block == kf_result file")
    check("V2.package_and_report_ids",
          embedded.get("package_id") == "wp-9706-02"
          and embedded.get("report_id") == "9706"
          and embedded.get("task_type") == "02-classification-parse",
          f"{embedded.get('package_id')}/{embedded.get('task_type')}/{embedded.get('report_id')}")

    cls = kf["outputs"]["classification.json"]
    locators = cls["locators"]
    bad_off, not_found = [], []
    for l in locators:
        pos = text.find(l["quote"])
        if pos < 0:
            not_found.append(l["id"])
        elif (pos, pos + len(l["quote"])) != (l["start_offset"], l["end_offset"]):
            bad_off.append((l["id"], pos, l["start_offset"]))
    check("V3.quotes_found_verbatim", not not_found, f"not found={not_found[:5]}")
    check("V3.offsets_equal_found_position", not bad_off, f"mismatch={bad_off[:5]}")
    check("V3.quote_min_length", all(len(l["quote"]) >= 12 for l in locators),
          f"min={min(len(l['quote']) for l in locators)}")

    loc_ids = [l["id"] for l in locators]
    claim_ids = [c["id"] for c in cls["claims"]]
    flag_ids = [f["id"] for f in cls["consistency_flags"]]
    check("V4.ids_unique",
          len(set(loc_ids)) == len(loc_ids) and len(set(claim_ids)) == len(claim_ids)
          and len(set(flag_ids)) == len(flag_ids),
          f"{len(loc_ids)}/{len(claim_ids)}/{len(flag_ids)}")
    referenced = {i for c in cls["claims"] for i in c["locator_ids"]}
    referenced |= {i for f in cls["consistency_flags"] for i in f["locator_ids"]}
    referenced |= {g["locator_id"] for g in cls["grade_notes_from_source"]}
    for cand in cls["type_candidates"]:
        for sig in cand["signal_judgement"].values():
            referenced |= set(sig["locator_ids"])
    dangling = sorted(referenced - set(loc_ids))
    check("V4.locator_refs_resolve", not dangling, f"dangling={dangling[:5]}")
    check("V4.every_claim_has_locator",
          all(c["locator_ids"] for c in cls["claims"]),
          f"{sum(1 for c in cls['claims'] if c['locator_ids'])}/{len(cls['claims'])}")

    check("V5.no_verified_status",
          all(c.get("epistemic_status") == "draft" and c.get("assessment_status") == "unassessed"
              for c in cls["claims"])
          and "verified" not in json.dumps(cls["claims"], ensure_ascii=False).lower(),
          "claims are draft/unassessed")

    bad_hash = [l["id"] for l in locators
                if l["content_hash"] != "sha256:" + hashlib.sha256(
                    l["quote"].encode("utf-8")).hexdigest()]
    check("V6.content_hash_matches_quote", not bad_hash, f"bad={bad_hash[:5]}")

    check("V6.structure_covers_text",
          cls["structure"]["sections"][0]["start_offset"] == 0
          and cls["structure"]["sections"][-1]["end_offset"] == len(text),
          f"{cls['structure']['section_count']} sections")

    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed"
          + (f"; FAILED: {failed}" if failed else ""))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())