#!/usr/bin/env python3
"""Independent verifier for KF work package wp-11624-01 (01-asset-registration).

This script does NOT trust the `checks` / `integrity` block written by the
register script: it re-derives every acceptance item from the raw snapshot and
the emitted manifest. It runs offline (no API call) so a reviewer can re-run it
against the committed worktree.

Acceptance items of the contract and how each is re-derived here
  valid_json                 -> strict json.load of every emitted file
  schema_pass                -> jsonschema.validate(manifest, pinned package schema)
                                + jsonschema.validate(result, schemas/kf_result.v1.schema.json)
  source_locator_resolvable  -> per locator: markdown locators must satisfy
                                md[start_char:end_char] == quote and md.count(quote) == 1
                                (document-scope: span covers the whole markdown);
                                record locators must resolve a JSON pointer into
                                source_record.json with the quote inside its value
  source_hash_matches        -> sha256(UTF-8 bytes of snapshot) == contract hash
                                == manifest.source.hash == provenance.source_hash
  no_duplicate_ids           -> asset_id uniqueness + locator ids cover assets
  all_claims_have_evidence_or_explicit_unresolved_status
                             -> vacuous by contract (claims == []); the verifier proves
                                the stronger property that no claim lacks evidence/status
                                and that nothing is marked `verified`.

Exit 0 iff all checks pass; 1 otherwise (honest failure, printed, never masked).
Usage: python3 scripts/kf_wp_11624_01_verify.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PKG = "wp-11624-01"
REPORT_ID = "11624"
CONTRACT_SOURCE_HASH = (
    "sha256:a5a0885e7f86a7d7e46ba9e66dcd748d1607075c640484785fce58868aaedd33"
)
CONTRACT_CHARS = 4253

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "knowledge" / "kf" / PKG
DOC_DIR = ROOT / "docs" / PKG
SNAPSHOT = OUT_DIR / "source_report_11624.md"
RECORD = OUT_DIR / "source_record.json"
MANIFEST = OUT_DIR / "asset_manifest.json"
RESULT = OUT_DIR / "kf_result.json"
SCHEMA = ROOT / "schemas" / "asset_manifest.v1.wp-11624-01.schema.json"
KF_SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"


def jp_get(doc, pointer: str):
    """Minimal JSON-pointer resolver (RFC 6901 subset used by this package)."""
    cur = doc
    for tok in pointer.lstrip("/").split("/"):
        tok = tok.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, list):
            cur = cur[int(tok)]
        elif isinstance(cur, dict):
            cur = cur[tok]
        else:
            raise KeyError(pointer)
    return cur


def _schema_ok(doc, schema_path: Path) -> tuple[bool, str]:
    try:
        import jsonschema
    except ImportError:
        return False, "jsonschema missing -> NOT_RUN"
    try:
        jsonschema.validate(doc, json.loads(schema_path.read_text(encoding="utf-8")))
        return True, "PASS"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def evaluate(md: str, record: dict, man: dict, res: dict, man_bytes: bytes) -> dict:
    """Re-derive every acceptance check from raw inputs (pure function, testable)."""
    checks: dict[str, object] = {}
    snapshot_hash = hashlib.sha256(md.encode("utf-8")).hexdigest()

    # ---- source_hash_matches ------------------------------------------------
    h_contract = ("sha256:" + snapshot_hash) == CONTRACT_SOURCE_HASH
    h_manifest = man["source"]["hash"] == snapshot_hash
    h_prov = res["provenance"]["source_hash"] == "sha256:" + snapshot_hash
    checks["source_hash_matches"] = {
        "snapshot_sha256": snapshot_hash,
        "contract": CONTRACT_SOURCE_HASH,
        "snapshot_matches_contract": h_contract,
        "manifest_matches_snapshot": h_manifest,
        "provenance_matches_snapshot": h_prov,
        "chars": len(md),
        "chars_match_contract": len(md) == CONTRACT_CHARS,
        "pass": h_contract and h_manifest and h_prov and len(md) == CONTRACT_CHARS,
    }

    # ---- source_locator_resolvable -----------------------------------------
    md_lines = md.split("\n")
    per_asset, bad = [], []
    for a in man["assets"]:
        loc = a["locator"]
        if loc["source_field"] == "markdown" and loc["method"] == "document":
            # document-scope asset: span covers the whole markdown, quote is the H1
            span_ok = md[loc["start_char"]:loc["end_char"]] == md
            first_ok = loc["quote"] == md_lines[0]
            ok = span_ok and first_ok
            per_asset.append({"asset_id": a["asset_id"], "resolved": ok,
                              "document_span_covers_source": span_ok,
                              "quote_is_first_line": first_ok, "chars": len(md)})
            if not ok:
                bad.append(a["asset_id"])
            continue
        if loc["source_field"] == "markdown":
            span_ok = md[loc["start_char"]:loc["end_char"]] == loc["quote"]
            occ = md.count(loc["quote"])
            lines_ok = 1 <= loc["start_line"] <= loc["end_line"] <= len(md_lines)
            ok = span_ok and occ == 1 and lines_ok
            detail = {"char_span_matches": span_ok, "unique": occ == 1,
                      "occurrences": occ, "lines_in_range": lines_ok}
        else:
            try:
                val = jp_get(record, loc["pointer"])
                ok = bool(val) and loc["quote"] in str(val)
                detail = {"pointer": loc["pointer"], "pointer_resolves": True,
                          "quote_in_pointer_value": loc["quote"] in str(val)}
            except Exception as exc:  # noqa: BLE001
                ok, detail = False, {"pointer": loc["pointer"], "error": str(exc)}
        per_asset.append({"asset_id": a["asset_id"], "resolved": ok, **detail})
        if not ok:
            bad.append(a["asset_id"])
    checks["source_locator_resolvable"] = {
        "assets_checked": len(per_asset),
        "assets_resolved": sum(1 for p in per_asset if p["resolved"]),
        "bad": bad,
        "detail": per_asset,
        "pass": not bad and len(per_asset) > 0,
    }

    # ---- no_duplicate_ids ---------------------------------------------------
    ids = [a["asset_id"] for a in man["assets"]]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    loc_ids = [x["id"] for x in man["locators"]]
    checks["no_duplicate_ids"] = {
        "asset_ids": len(ids),
        "duplicates": dupes,
        "locator_ids_cover_assets": sorted(loc_ids) == sorted(ids),
        "pass": not dupes and sorted(loc_ids) == sorted(ids),
    }

    # ---- claims / verified marks -------------------------------------------
    claims = man.get("claims", [])
    claim_violations = [
        c.get("claim_id") for c in claims
        if not c.get("evidence_locator") and not c.get("status") and not c.get("evidence")
    ]
    blob = json.dumps(man["assets"], ensure_ascii=False)
    verified_marks = '"verified"' in blob or "已核验" in blob
    checks["claims_have_evidence_or_unresolved_status"] = {
        "claims": len(claims),
        "vacuous_by_contract": len(claims) == 0,
        "claim_violations": claim_violations,
        "verified_marks_on_assets": verified_marks,
        "provenance_verification_status": res["provenance"].get("verification_status"),
        "pass": not claim_violations and not verified_marks
                and res["provenance"].get("verification_status") != "verified",
    }

    # ---- schema_pass --------------------------------------------------------
    ok_m, msg_m = _schema_ok(man, SCHEMA)
    ok_r, msg_r = _schema_ok(res, KF_SCHEMA)
    checks["schema_pass"] = {"manifest_vs_package_schema": msg_m,
                             "kf_result_vs_platform_schema": msg_r,
                             "pass": ok_m and ok_r}

    # ---- envelope identity --------------------------------------------------
    art_sha = res["outputs"]["asset_manifest.json"]["artifact_sha256"]
    checks["envelope_identity"] = {
        "package_id": res["package_id"], "task_type": res["task_type"],
        "report_id": res["report_id"],
        "outputs_keys": sorted(res["outputs"].keys()),
        "manifest_copy_matches_file": art_sha == hashlib.sha256(man_bytes).hexdigest(),
        "pass": res["package_id"] == PKG and res["task_type"] == "01-asset-registration"
                and res["report_id"] == REPORT_ID
                and sorted(res["outputs"].keys()) == ["asset_manifest.json"]
                and art_sha == hashlib.sha256(man_bytes).hexdigest(),
    }

    # ---- single-report scope ------------------------------------------------
    foreign = []
    for name, txt in (("snapshot", md), ("manifest", json.dumps(man, ensure_ascii=False)),
                      ("result", json.dumps(res, ensure_ascii=False)),
                      ("record", json.dumps(record, ensure_ascii=False))):
        if "tensor://reports/" in txt:
            for tok in txt.split("tensor://reports/")[1:]:
                rid = tok.split("'")[0].split('"')[0].split(")")[0].split()[0].strip(",;`")
                if rid and rid != REPORT_ID:
                    foreign.append((name, rid))
    checks["single_report_scope"] = {"report_id": REPORT_ID,
                                     "foreign_report_refs": foreign, "pass": not foreign}
    return checks


def main() -> int:
    md = SNAPSHOT.read_text(encoding="utf-8")
    man_bytes = MANIFEST.read_bytes()
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    man = json.loads(man_bytes)
    res = json.loads(RESULT.read_text(encoding="utf-8"))

    checks = evaluate(md, record, man, res, man_bytes)

    mirror = []
    for name in ("source_report_11624.md", "source_record.json", "asset_manifest.json",
                 "kf_result.json", "verification_report.json"):
        a, b = OUT_DIR / name, DOC_DIR / name
        if name == "verification_report.json":
            continue  # written by this script; compared on the next run
        ok = a.exists() and b.exists() and a.read_bytes() == b.read_bytes()
        mirror.append({"name": name, "identical": ok})
    checks["durable_mirror"] = {"files": mirror, "pass": all(m["identical"] for m in mirror)}

    all_pass = all(v["pass"] for v in checks.values())
    out = {"package_id": PKG, "report_id": REPORT_ID, "all_checks_pass": all_pass,
           "verifier": "scripts/kf_wp_11624_01_verify.py", "checks": checks}
    blob = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    (OUT_DIR / "verification_report.json").write_text(blob, encoding="utf-8")
    (DOC_DIR / "verification_report.json").write_text(blob, encoding="utf-8")

    for k, v in checks.items():
        print("%-42s %s" % (k, "PASS" if v["pass"] else "FAIL"))
    print("ALL:", "PASS" if all_pass else "FAIL")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())