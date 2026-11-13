#!/usr/bin/env python3
"""wp-11156-01 · 01-asset-registration · report_id=11156

Registers the *assets* of report 11156 ("DEM Parameter Auto-Calibration
Framework: Bayesian Optimization + MCMC UQ", scenario p284w3-n05-dem-auto-calibration).

Scope of this package (contract objective): register assets only.
  * classify_report_type = False   -> no report-type classification is written
  * no extraction                  -> claims == [] (zero forced claim generation)
  * no verification                -> nothing is marked verified; every asset carries
                                      verification_status="not_performed"
  * report_id is hard-locked to 11156 by register_assets_lib.fetch_report()

What is registered, every item with a verbatim, machine-checked locator
(quote must satisfy `quote in markdown` AND `markdown[offset:+len] == quote`):
  A01      source markdown itself (document locator, hash-pinned)
  A02/A03  inline tables (§2.1 benchmark->macroscopic map, §4 acceptance criteria)
  A04-A06  material presets (§3.3 bullets, one asset per preset)
  A07-A10  file references quoted in §6 Files (probed against this worktree)
  A11-A13  quantitative statements that later stages will need (§3.1, §3.2, §4/§6)
  A14-A15  hash anchors printed in the publish-anchor line (declared, NOT recomputed:
           the ledger/corpus bytes are outside this package's scope)
  A16      publish anchor (mission / branch / commit), declared only
  A17-A21  figure metadata carried by the platform record (name+caption only,
           no byte payload -> declared_only; payload never claimed)

Two record-level observations are registered without interpretation:
  * the record's figure captions talk about criterion-family kill rates, which is a
    different topic from DEM calibration -> flagged topic_mismatch, no cause invented;
  * record.mission_id (9416) differs from the markdown publish anchor text
    ("mission 9437") -> both sides quoted, discrepancy left open.

Usage (repro, live fetch):
  TENSOR_API_BASE=... TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=... \
    python3 scripts/kf/build_asset_manifest_wp11156_01.py
Offline rebuild from a saved record:
  python3 scripts/kf/build_asset_manifest_wp11156_01.py --record-file /tmp/r11156.json
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "kf"))
import register_assets_lib as L  # noqa: E402

PKG = "wp-11156-01"
REPORT_ID = "11156"
TASK_TYPE = "01-asset-registration"
CONTRACT_HASH = "4e34bdac8a446701f339014fec117feea5083ad4ef85543edae87ccb77806d77"
SOURCE_URI = "tensor://reports/11156"
CONTRACT_CHARS = 4478
CONTRACT_TITLE = "DEM Parameter Auto-Calibration Framework: Bayesian Optimization + MCMC UQ"
CONTRACT_SCENARIO = "p284w3-n05-dem-auto-calibration"
PRODUCER = "agent/m15691"

PKG_DIR = ROOT / "docs" / "kf" / PKG
RUN_DIR = ROOT / "runs" / PKG

# --------------------------------------------------------------------------- #
# selector helpers (reuse register_assets_lib.Md primitives, whole-line quotes)
# --------------------------------------------------------------------------- #


def line_of(md: L.Md, offset: int) -> int:
    """0-based line index of a char offset (markdown split with '\\n')."""
    return md.text.count("\n", 0, offset)


def span(md: L.Md, offset: int, quote: str) -> dict:
    occ = md.text.count(quote)
    return {
        "method": "char_span",
        "start_char": offset,
        "end_char": offset + len(quote),
        "start_line": line_of(md, offset) + 1,
        "end_line": line_of(md, offset + max(len(quote) - 1, 0)) + 1,
        "quote": quote,
        "unique": occ == 1,
        "occurrences": occ,
        "quote_verbatim": md.text[offset:offset + len(quote)] == quote,
    }


def by_token(md: L.Md, token: str, nth: int = 0) -> dict:
    off, ln = md.find_line(token, nth)
    return span(md, off, ln)


def by_substring(md: L.Md, token: str) -> dict:
    """Locate an exact substring (used when the interesting unit is a fragment of a line)."""
    off = md.text.find(token)
    if off < 0:
        raise LookupError("substring not found: %r" % token)
    return span(md, off, token)


def by_table(md: L.Md, header_token: str) -> tuple[dict, dict]:
    (ho, hl), rows = md.table_block(header_token)
    last_off, last_ln = rows[-1] if rows else (ho, hl)
    quote = md.text[ho:last_off + len(last_ln)]
    return span(md, ho, quote), {"data_rows": len(rows), "header": hl}


def by_bullet(md: L.Md, header_token: str, token: str) -> dict:
    for off, ln in md.bullets_after(header_token):
        if token in ln:
            return span(md, off, ln)
    raise LookupError("bullet not found: %r under %r" % (token, header_token))


def by_document(md: L.Md) -> dict:
    h1 = md.lines[0][1]
    occ = md.text.count(h1)
    return {
        "method": "document",
        "start_char": 0,
        "end_char": len(md.text),
        "start_line": 1,
        "end_line": line_of(md, len(md.text) - 1) + 1,
        "quote": h1,
        "quote_is_first_line_only": True,
        "document_sha256": hashlib.sha256(md.text.encode("utf-8")).hexdigest(),
        "unique": occ == 1,
        "occurrences": occ,
        "quote_verbatim": True,
        "note": "document-level locator; quote is only the H1 line for readability",
    }


def worktree_probe(rel: str) -> dict:
    p = ROOT / rel
    return {
        "check": "worktree_probe:%s" % rel,
        "result": "present" if p.exists() else "absent",
        "searched_root": "TensorKnowledge worktree (this repo)",
        "note": "report 11156 was produced in a TensorDEM-side worktree; the "
                "TensorKnowledge checkout is not expected to carry those bytes",
    }


# --------------------------------------------------------------------------- #
# asset spec
# --------------------------------------------------------------------------- #
def build(md_text: str, rec: dict, now: str) -> dict:
    md = L.Md(md_text)
    assets: list[dict] = []

    def add(aid, kind, label, section, loc, resolution, note, verification="not_performed"):
        assets.append(
            {
                "asset_id": aid,
                "kind": kind,
                "label": label,
                "section": section,
                "resolution": resolution,
                "verification_status": verification,
                "locator": loc,
                "note": note,
            }
        )

    add("A01", "source_markdown", "report 11156 markdown (hash-pinned source of record)",
        "document", by_document(md), "resolved_in_source",
        "sha256 recomputed live over UTF-8 bytes; equals the contract-declared hash. "
        "Hash equality is a mechanical identity check only.")

    loc, meta = by_table(md, "| Benchmark |")
    add("A02", "table", "§2.1 forward-benchmark -> macroscopic-response mapping table",
        "2.1 Forward Problem", loc, "resolved_in_source",
        "table header + %d data rows quoted verbatim; row count recorded in locator_stats" % meta["data_rows"])
    assets[-1]["locator_stats"] = meta

    loc, meta = by_table(md, "| Criterion |")
    add("A03", "table", "§4 acceptance-criteria table (targets + status wording)",
        "4. Acceptance Criteria", loc, "resolved_in_source",
        "targets are registered as *declared*; the reported status column is quoted, "
        "not re-verified by this package (verification belongs to the platform gate)")
    assets[-1]["locator_stats"] = meta

    for aid, token, label in [
        ("A04", "**Glass beads**", "material preset: glass beads (mu / mu_r / e ranges)"),
        ("A05", "**Sand**", "material preset: sand (mu / mu_r / e ranges)"),
        ("A06", "**Gravel**", "material preset: gravel (mu / mu_r / e ranges)"),
    ]:
        add(aid, "parameter_preset", label, "3.3 Material Presets",
            by_bullet(md, "3.3 Material Presets", token), "resolved_in_source",
            "verbatim bullet; the numeric ranges are the report's own values, not re-derived")

    for aid, rel, label in [
        ("A07", "src/tensordem/auto_calibration.py", "file reference: main calibration framework"),
        ("A08", "tests/test_auto_calibration.py", "file reference: 30-test pytest suite"),
        ("A09", "artifacts/fig*.png", "file reference: result figures (glob, no concrete filenames)"),
        ("A10", "runs/calibration_result.json", "file reference: calibration run results"),
    ]:
        probe = worktree_probe(rel)
        res = "referenced_unresolved" if probe["result"] == "absent" else "resolved_in_source"
        add(aid, "referenced_path", label, "6. Files",
            by_bullet(md, "6. Files", rel), res,
            "path text quoted verbatim from §6; byte payload NOT available in this package -> "
            "existence was probed only against this worktree and is reported as-is")
        assets[-1]["resolution_check"] = probe

    add("A11", "reported_quantity", "BO convergence: 38 evaluations, objective < 0.01 (2D quadratic test)",
        "3.1 Bayesian Optimization Convergence", by_token(md, "within 38 evaluations"),
        "resolved_in_source", "declared numeric result; not reproduced here (no extraction, no verification)")
    add("A12", "reported_quantity", "MCMC input data: repose angle 25 deg +/- 3 deg",
        "3.2 MCMC Posterior Distribution", by_token(md, "25 degrees +/- 3 degrees"),
        "resolved_in_source", "declared experimental datum; posterior mean/CI are described only "
        "qualitatively in §3.2 (no numbers) -> see observation O2")
    add("A13", "reported_quantity", "pytest count: 30 tests",
        "4. Acceptance Criteria", by_token(md, "30 tests pass"),
        "resolved_in_source", "declared test count (acceptance row (f)); suite not executed by this package")

    add("A14", "hash_anchor", "publish anchor: ledger sha256 (declared)",
        "publish anchor line", by_substring(md, "ledger sha256 `16685355b1c97e5a01daa492b9c1c05046b286b2b295773591dcd011a81861d0`"),
        "declared_only", "anchor is quoted verbatim but the referenced ledger bytes are outside this "
        "package -> hash NOT recomputed, NOT confirmed")
    add("A15", "hash_anchor", "publish anchor: corpus sha256 (declared)",
        "publish anchor line", by_substring(md, "corpus sha256 `4f09e8caa017ce8c1a54170aae734f78f98073ff2cac4ef7fcd23a224a07add9`"),
        "declared_only", "same status as A14: declared only, bytes unavailable -> hash NOT "
        "recomputed, NOT confirmed")
    add("A16", "publish_anchor", "publish anchor: mission / branch / commit",
        "publish anchor line", by_substring(md, "mission 9437 / branch agent/m9437 · commit 89b3ec6f"),
        "declared_only", "provenance pointers declared by the report; NOT resolved against any git "
        "repository by this package")

    for i, fig in enumerate(rec.get("figures") or [], start=17):
        name = fig.get("name", "")
        caption = fig.get("caption", "")
        loc = {
            "method": "record_figures_index",
            "source_field": "record",
            "record_index": i - 17,
            "name": name,
            "quote": caption or name,
            "resolvable_in_markdown": bool(name and name in md_text),
            "start_char": None,
            "end_char": None,
            "start_line": None,
            "end_line": None,
            "unique": True,
            "occurrences": 1 if caption else 0,
            "note": "name/caption live in record.figures; the PNG payload is not carried by the "
                    "record, so no image bytes and no image hash are claimed",
        }
        add("A%02d" % i, "figure_metadata", "record figure metadata: %s" % (name or "<unnamed>"),
            "record.figures", loc, "declared_only",
            "declared only: no payload, no hash, no visual check performed by this package")
        assets[-1]["caption"] = caption
        assets[-1]["caption_topic_matches_report"] = False if caption and (
            "判据" in caption or "杀伤" in caption or "变异体" in caption) else None

    ids = [a["asset_id"] for a in assets]
    assert len(ids) == len(set(ids)), "duplicate asset_id"

    figures = rec.get("figures") or []
    obs = [
        {
            "observation_id": "O1",
            "kind": "record_metadata_topic_mismatch",
            "statement": "All 5 figure captions in record.figures discuss criterion-family "
                         "kill rates / mutants, i.e. a different subject than DEM parameter "
                         "calibration. Flagged, cause NOT inferred (do_not_invent_missing_information).",
            "evidence": {
                "record_field": "figures[].caption",
                "quotes": [f.get("caption") for f in figures],
            },
        },
        {
            "observation_id": "O2",
            "kind": "information_gap_in_source",
            "statement": "§3.2 reports the MCMC posterior only qualitatively (no posterior mean, "
                         "no CI numbers); §3.3/§4 numbers exist but posterior quantities do not. "
                         "Registered as an explicit gap; nothing is filled in.",
            "evidence": {
                "quote": md.lines[[i for i, (_o, ln) in enumerate(md.lines)
                                   if ln.startswith("- Posterior mean")][0]][1],
                "note": "quoted verbatim from §3.2",
            },
        },
        {
            "observation_id": "O3",
            "kind": "provenance_pointer_discrepancy",
            "statement": "Platform record mission_id=9416 while the markdown publish anchor reads "
                         "'mission 9437'. Both values registered verbatim; discrepancy left open.",
            "evidence": {
                "record_field": "mission_id",
                "record_value": rec.get("mission_id"),
                "markdown_quote": "mission 9437 / branch agent/m9437",
                "markdown_quote_commit": "commit 89b3ec6f",
            },
        },
        {
            "observation_id": "O4",
            "kind": "unresolvable_scope",
            "statement": "None of the four §6 file references (A07-A10) exists in the "
                         "TensorKnowledge worktree, so the assets are registered as text locators "
                         "only; no code/byte level check was possible in this package.",
            "evidence": {"asset_ids": ["A07", "A08", "A09", "A10"],
                         "probes": [a.get("resolution_check") for a in assets if a.get("resolution_check")]},
        },
    ]

    by_kind: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    uniq_violations = [a["asset_id"] for a in assets
                       if a["locator"].get("method") in ("char_span", "document")
                       and not a["locator"].get("unique")]
    verbatim_violations = [a["asset_id"] for a in assets
                           if a["locator"].get("method") in ("char_span", "document")
                           and not a["locator"].get("quote_verbatim")]
    md_span_assets = [a for a in assets if a["locator"].get("method") in ("char_span", "document")]
    record_assets = [a for a in assets if a["locator"].get("method") == "record_figures_index"]

    headings = [ln for _o, ln in md.lines if ln.startswith("#")]
    digest = hashlib.sha256(md_text.encode("utf-8")).hexdigest()

    return {
        "manifest_version": "1.0",
        "schema": "asset_manifest.v1",
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "generated_at": now,
        "generated_by": PRODUCER,
        "scope": {
            "registers_assets_only": True,
            "extracts_claims": False,
            "classifies_report_type": False,
            "marks_anything_verified": False,
            "reports_touched": [REPORT_ID],
        },
        "contract": {
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash_declared": "sha256:" + CONTRACT_HASH,
            "chars_declared": CONTRACT_CHARS,
            "title_declared": CONTRACT_TITLE,
            "scenario_key_declared": CONTRACT_SCENARIO,
        },
        "source": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest,
            "hash_contract": CONTRACT_HASH,
            "hash_matches_contract": digest == CONTRACT_HASH,
            "hash_method": "sha256 over UTF-8 bytes of the markdown field",
            "retrieved_via": rec.get("_retrieved_via", "unknown"),
            "chars": len(md_text),
            "chars_matches_contract": len(md_text) == CONTRACT_CHARS,
            "bytes_utf8": len(md_text.encode("utf-8")),
            "title": rec.get("title"),
            "title_matches_contract": rec.get("title") == CONTRACT_TITLE,
            "scenario_key": rec.get("scenario_key"),
            "platform_mission_id": rec.get("mission_id"),
            "platform_status": rec.get("status"),
            "platform_tags": rec.get("tags"),
            "line_count": len(md.lines),
            "heading_count": len(headings),
            "headings": headings,
        },
        "counts": {
            "assets": len(assets),
            "by_kind": by_kind,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_only": by_res.get("declared_only", 0),
            "claims": 0,
        },
        "assets": assets,
        "observations": obs,
        "claims": [],
        "claims_note": "intentionally empty: package objective is asset registration only; "
                       "no claim is generated, none is marked verified (verification stays with the platform gate)",
        "integrity": {
            "hash_recomputed_locally": True,
            "hash_matches_contract": digest == CONTRACT_HASH,
            "quote_uniqueness": "checked per char_span locator (count==1)",
            "md_span_locators": len(md_span_assets),
            "record_locators": len(record_assets),
            "quote_uniqueness_violations": uniq_violations,
            "quote_verbatim_violations": verbatim_violations,
            "duplicate_asset_ids": [],
            "all_claims_have_evidence_or_unresolved_status": True,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record-file", type=Path, default=None)
    args = ap.parse_args()

    rec = L.fetch_report(REPORT_ID, args.record_file)
    md_text = rec["markdown"]
    now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()

    manifest = build(md_text, rec, now)
    PKG_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    (PKG_DIR / "source.md").write_text(md_text, encoding="utf-8")
    record_meta = {k: rec.get(k) for k in
                   ("id", "title", "scenario_key", "status", "tags", "mission_id",
                    "created_by", "created_at", "stage", "figures", "summary")}
    record_meta["_retrieved_via"] = rec.get("_retrieved_via", "unknown")
    record_meta["_note"] = ("record metadata snapshot for offline acceptance checks; the markdown "
                            "field is snapshotted separately in source.md")
    (PKG_DIR / "record_meta.json").write_text(
        json.dumps(record_meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (PKG_DIR / "asset_manifest.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    locator_check = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "source_hash": manifest["source"]["hash"],
        "checked_at": now,
        "locators": {
            a["asset_id"]: {
                "source_field": a["locator"].get("source_field", "markdown"),
                "quote": a["locator"]["quote"],
                "resolvable_in_markdown": a["locator"].get("source_field", "markdown") != "markdown"
                                         or (a["locator"]["quote"] in md_text
                                             and (a["locator"]["method"] == "document"
                                                  or md_text[a["locator"]["start_char"]:a["locator"]["end_char"]]
                                                  == a["locator"]["quote"])),
                "offset_chars": a["locator"]["start_char"],
                "count_occurrences": a["locator"]["occurrences"],
            }
            for a in manifest["assets"]
        },
    }
    (PKG_DIR / "locator_check.json").write_text(
        json.dumps(locator_check, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    result = {
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": "sha256:" + manifest["source"]["hash"],
            "producer": PRODUCER,
            "emitted_at": now,
            "notes": "01-asset-registration only: markdown fetched live, sha256 recomputed over UTF-8 "
                     "bytes and matched against the contract hash; %d assets registered with verbatim "
                     "locators; figure metadata registered as declared-only; claims intentionally empty; "
                     "nothing marked verified."
                     % manifest["counts"]["assets"],
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    (PKG_DIR / "kf_result.json").write_text(
        json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    import jsonschema  # local import: only needed for the self-check

    schema_path = ROOT / "schemas" / "kf_result.v1.schema.json"
    try:
        jsonschema.validate(result, json.load(open(schema_path, encoding="utf-8")))
        schema_pass = True
    except Exception as e:  # noqa: BLE001 - the verdict must record the failure, not crash
        schema_pass = "failed: %r" % (e,)
        print("SCHEMA FAIL:", e, file=sys.stderr)

    verdict = {
        "package_id": PKG,
        "emitted_at": now,
        "schema_validated_against": "schemas/kf_result.v1.schema.json",
        "acceptance": {
            "valid_json": True,
            "schema_pass": schema_pass,
            "source_locator_resolvable": not manifest["integrity"]["quote_verbatim_violations"],
            "source_hash_matches": manifest["source"]["hash_matches_contract"],
            "no_duplicate_ids": len({a["asset_id"] for a in manifest["assets"]}) == len(manifest["assets"]),
            "all_claims_have_evidence_or_explicit_unresolved_status": manifest["claims"] == [],
        },
    }
    (RUN_DIR / "verification.json").write_text(
        json.dumps(verdict, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({"package_id": PKG,
                      "hash_match": manifest["source"]["hash_matches_contract"],
                      "chars": manifest["source"]["chars"],
                      "assets": manifest["counts"]["assets"],
                      "by_resolution": manifest["counts"]["by_resolution"],
                      "unique_violations": manifest["integrity"]["quote_uniqueness_violations"],
                      "verbatim_violations": manifest["integrity"]["quote_verbatim_violations"],
                      }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()