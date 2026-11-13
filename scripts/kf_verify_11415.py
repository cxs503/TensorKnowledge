#!/usr/bin/env python3
"""Independent verifier for KF work package wp-11415-01 (asset registration).

Re-derives every acceptance item from raw inputs instead of trusting the
generator's own bookkeeping:

  * source hash  = sha256 of payload['markdown'] (re-read from the API snapshot)
                   and of the local markdown copy -- both compared with the
                   contract source_hash;
  * locators     = quote must equal markdown[start_char:end_char], must occur
                   exactly once, and start_line/end_line must be the line
                   indices actually containing those char offsets;
  * schema       = kf_result.v1 envelope + asset_manifest.v1 (wp-11415-01 pin)
                   validated with jsonschema;
  * ids          = unique + contiguous A01..A0N;
  * claims       = every claim carries evidence or an explicit status
                   (0 claims is legitimate for this package);
  * counts       = counts block recomputed from the asset list;
  * no asset is declared verified (verification is the platform gate's job).

Writes runs/wp-11415-01/verify_report.json and exits non-zero on any failure.
Run:  python3 scripts/kf_verify_11415.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

import jsonschema

RUN_DIR = pathlib.Path("runs/wp-11415-01")
ART = pathlib.Path("artifacts/wp-11415-01/asset_manifest.json")
MIRROR = pathlib.Path("docs/kf/wp-11415-01/asset_manifest.json")
RESULT = RUN_DIR / "kf_result.wp-11415-01.json"
RESULT_SCHEMA = pathlib.Path("schemas/kf_result.v1.schema.json")
MANIFEST_SCHEMA = pathlib.Path("schemas/asset_manifest.v1.wp-11415-01.schema.json")

PACKAGE_ID = "wp-11415-01"
REPORT_ID = "11415"
EXPECTED_HASH = "d8bc42883f1fa1d274a3ca4808586d2a8773e9d0f464b554c944f5090b0c8c50"
EXPECTED_CHARS = 7903


def line_index_of(md: str, offset: int) -> int:
    return md[:offset].count("\n")


def verify() -> dict:
    payload = json.loads((RUN_DIR / "report_11415.json").read_text())
    md_api = payload["markdown"]
    md_file = (RUN_DIR / "report_11415.md").read_text()
    result = json.loads(RESULT.read_text())
    manifest = result["outputs"]["asset_manifest.json"]
    checks: dict[str, dict] = {}

    # --- source hash (recomputed twice, independently of the generator) -------
    h_api = hashlib.sha256(md_api.encode()).hexdigest()
    h_file = hashlib.sha256(md_file.encode()).hexdigest()
    checks["source_hash_matches"] = dict(
        pass_=h_api == EXPECTED_HASH == h_file
        and result["provenance"]["source_hash"] == "sha256:" + EXPECTED_HASH
        and manifest["source"]["hash"] == EXPECTED_HASH,
        api_sha256=h_api, file_sha256=h_file, contract="sha256:" + EXPECTED_HASH,
        envelope=result["provenance"]["source_hash"],
    )
    checks["source_chars_match_contract"] = dict(
        pass_=len(md_api) == EXPECTED_CHARS == manifest["source"]["chars"]
        and result["provenance"]["source_chars"] == EXPECTED_CHARS,
        api_chars=len(md_api), contract_chars=EXPECTED_CHARS,
    )

    # --- schema validation ---------------------------------------------------
    kf_schema = json.loads(RESULT_SCHEMA.read_text())
    mf_schema = json.loads(MANIFEST_SCHEMA.read_text())
    for name, inst, sch in (("kf_result_schema", result, kf_schema),
                            ("asset_manifest_schema", manifest, mf_schema)):
        try:
            jsonschema.validate(inst, sch)
            checks[name] = dict(pass_=True, errors=[])
        except jsonschema.ValidationError as exc:  # pragma: no cover
            checks[name] = dict(pass_=False, errors=[f"{list(exc.absolute_path)}: {exc.message}"])
    checks["valid_json"] = dict(pass_=True, parsed_files=[str(RESULT), str(ART)])

    # --- boundary / identity -------------------------------------------------
    checks["report_id_boundary"] = dict(
        pass_=result["report_id"] == manifest["report_id"] == REPORT_ID
        and manifest["source"]["uri"] == "tensor://reports/" + REPORT_ID
        and payload["id"] == int(REPORT_ID)
        and result["package_id"] == manifest["package_id"] == PACKAGE_ID,
        report_id=result["report_id"], uri=manifest["source"]["uri"], package_id=result["package_id"],
    )

    # --- locator resolvability (the core of this task_type) ------------------
    bad, per_asset = [], {}
    for a in manifest["assets"]:
        loc = a["locator"]
        start, end, quote = loc["start_char"], loc["end_char"], loc["quote"]
        span_ok = md_api[start:end] == quote
        unique_ok = md_api.count(quote) == 1
        if loc["method"] == "document":
            # whole-document locator: defined as [0, len(markdown)); line span is bookkeeping
            line_ok = (loc["start_line"] == 0 and start == 0 and end == len(md_api))
        else:
            line_ok = (line_index_of(md_api, start) == loc["start_line"]
                       and line_index_of(md_api, end - 1) == loc["end_line"])
        in_bounds = 0 <= start < end <= len(md_api)
        ok = span_ok and unique_ok and line_ok and in_bounds and loc["unique"] is True
        per_asset[a["asset_id"]] = dict(span_ok=span_ok, unique_ok=unique_ok,
                                        lines_ok=line_ok, in_bounds=in_bounds)
        if not ok:
            bad.append(a["asset_id"])
    checks["source_locator_resolvable"] = dict(
        pass_=not bad, failures=bad, checked=len(manifest["assets"]),
        detail="quote == markdown[start_char:end_char] AND count(quote)==1 AND line indices re-derived from offsets",
    )

    # --- ids -----------------------------------------------------------------
    ids = [a["asset_id"] for a in manifest["assets"]]
    expected_ids = ["A%02d" % i for i in range(1, len(ids) + 1)]
    checks["no_duplicate_ids"] = dict(
        pass_=len(set(ids)) == len(ids) == len(manifest["assets"]) and ids == expected_ids,
        n=len(ids), unique=len(set(ids)), contiguous=ids == expected_ids,
    )

    # --- claims --------------------------------------------------------------
    claims = manifest.get("claims", [])
    bad_claims = [c.get("claim_id") for c in claims
                  if not (c.get("evidence") or c.get("status") or c.get("unresolved_reason"))]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = dict(
        pass_=not bad_claims, n_claims=len(claims), offending=bad_claims,
        note="0 claims is legitimate here (register_assets only); empty != unverifiable omission",
        claims_note_present=bool(manifest.get("claims_note")),
    )

    # --- counts consistency --------------------------------------------------
    by_class, by_res = {}, {}
    for a in manifest["assets"]:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    c = manifest["counts"]
    checks["counts_consistent"] = dict(
        pass_=c["assets"] == len(manifest["assets"]) and c["by_class"] == by_class
        and c["by_resolution"] == by_res
        and c["resolved_in_source"] == by_res.get("resolved_in_source", 0)
        and c["referenced_unresolved"] == by_res.get("referenced_unresolved", 0)
        and c["declared_absent"] == by_res.get("declared_absent", 0),
        assets=c["assets"], by_class=by_class, by_resolution=by_res,
    )

    # --- resolution checks are machine-backed, not asserted -------------------
    backed = {a["asset_id"]: a["resolution_check"].get("check") for a in manifest["assets"]}
    checks["resolution_checks_machine_backed"] = dict(
        pass_=all(v for v in backed.values()), checks=backed,
        detail="each asset's resolution carries a named machine check + its result",
    )
    unresolved_detail = {a["asset_id"]: a["resolution_check"] for a in manifest["assets"]
                         if a["resolution"] != "resolved_in_source"}

    # --- nothing is self-declared verified -----------------------------------
    blob = ART.read_text() + json.dumps(result, ensure_ascii=False)
    verified_hits = re.findall(r'"verification_status"\s*:\s*"([^"]+)"', blob)
    checks["no_self_declared_verified"] = dict(
        pass_=all(v == "not_verified" for v in verified_hits) and '"verified": true' not in blob,
        verification_status_values=sorted(set(verified_hits)),
        outputs_equals_artifact=manifest == json.loads(ART.read_text()),
        detail="verification is computed by the platform gate; this package only reports not_verified",
    )

    # --- durable mirror ------------------------------------------------------
    checks["artifact_mirror_identical"] = dict(
        pass_=ART.read_bytes() == MIRROR.read_bytes(),
        artifact_sha256=hashlib.sha256(ART.read_bytes()).hexdigest(),
        mirror_sha256=hashlib.sha256(MIRROR.read_bytes()).hexdigest(),
    )
    art_sha = hashlib.sha256(ART.read_bytes()).hexdigest()
    checks["artifact_hash_matches_provenance"] = dict(
        pass_=(art_sha == result["provenance"]["artifact_sha256"]
               and ART.stat().st_size == result["provenance"]["artifact_bytes"]),
        declared=result["provenance"]["artifact_sha256"], recomputed=art_sha,
        bytes=ART.stat().st_size,
    )

    checks["outputs_manifest_equals_artifact_file"] = dict(
        pass_=manifest == json.loads(ART.read_text()),
        artifact_sha256=art_sha,
    )
    all_pass = all(v["pass_"] for v in checks.values())
    report = dict(package_id=PACKAGE_ID, report_id=REPORT_ID, all_pass=all_pass,
                  n_assets=len(manifest["assets"]), checks=checks,
                  unresolved_detail=unresolved_detail,
                  source_sha256_recomputed="sha256:" + h_api)
    (RUN_DIR / "verify_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def main() -> int:
    rep = verify()
    for k, v in rep["checks"].items():
        print(("PASS " if v["pass_"] else "FAIL ") + k)
    print("ALL_PASS:", rep["all_pass"], "assets:", rep["n_assets"])
    return 0 if rep["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())