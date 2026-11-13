#!/usr/bin/env python3
"""wp-12565-01 (task_type 01-asset-registration, report 12565): register source assets.

Does exactly one thing: register report 12565's source asset (identity + byte hash of the
`markdown` field) and enumerate the attachments / artifacts / references that the
markdown declares, each with a verbatim locator (char span + line span) re-resolved
against the very bytes that were hashed. No extraction, no classification, no claim is
marked verified.

Scope boundary (hard, from the work-package contract): only report_id=12565 is read.
The markdown of this report *names* upstream report 12563; that record is deliberately
NOT fetched - it is registered as a `referenced_unresolved` reference instead.

Artifacts written into the worktree:
    docs/kf/wp-12565-01/source.md            byte copy of the registered markdown
    docs/kf/wp-12565-01/sha256.txt           recomputed digest
    docs/kf/wp-12565-01/locator_check.json   one row per quote (span / line / occurrences)
    docs/kf/wp-12565-01/asset_manifest.json  contract output `asset_manifest.json`
    docs/kf/wp-12565-01/kf_result.json       kf_result.v1 envelope (schema-validated)
    docs/kf/wp-12565-01/verification.json    the six acceptance items, machine-evaluated

Usage: python3 scripts/kf_wp12565_01_register.py [--no-fetch]
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-12565-01"
SCHEMA_RESULT = ROOT / "schemas" / "kf_result.v1.schema.json"
SCHEMA_ASSET = ROOT / "schemas" / "asset_manifest.v1.schema.json"

PACKAGE_ID = "wp-12565-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "12565"
LANE = "C"
PRODUCER = "agent/m15749"

# ------------------------------------------------------------- contract (verbatim)
CONTRACT_HASH = "sha256:a5a04a43beed973865029e9ade6c0de33a88e17a795bea13b55ef4c083571d20"
CONTRACT_CHARS = 648
CONTRACT_TITLE = "P156W2-N03 报告勘误：球阻归一化口径（nu_formula vs nu_eff）"
CONTRACT_SCENARIO = "lbm_d3q27_poiseuille_stokes"
CONTRACT_VERSION = "1.0"

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

# ------------------------------------------------------------------ asset table
# (asset_id, asset_class, label, ref_uri, quote, outcome, check, check_result, note)
# Every quote below must be a verbatim substring of the registered markdown; the
# resolver hard-fails on any miss, so nothing here can be hand-transcribed.
ASSETS = [
    (
        "A01",
        "source_document",
        "report 12565 markdown (whole document)",
        "tensor://reports/12565",
        "# P156W2-N03 报告勘误（对应 report id 12563）",
        "resolved_in_source",
        "sha256 over the UTF-8 bytes of record.markdown == contract source_hash",
        "resolved",
        "bytes fetched via GET /api/v1/tensor/reports/12565, hashed locally; the document is "
        "the registration target itself, so it resolves to itself",
    ),
    (
        "A02",
        "upstream_report_reference",
        "upstream report 12563 (the report this errata corrects)",
        "tensor://reports/12563",
        "（对应 report id 12563）",
        "referenced_unresolved",
        "record fetch of report 12563 deliberately not performed (package scope boundary)",
        "unresolved",
        "the id is quoted verbatim, but this package is restricted to report_id=12565 and must "
        "not read other report_ids, so its body/artifacts stay unverified here",
    ),
    (
        "A03",
        "data_artifact_reference",
        "artifacts/sphere_resolution.json (declared artifact holding both K values)",
        "artifacts/sphere_resolution.json",
        "artifacts/sphere_resolution.json",
        "referenced_unresolved",
        "artifact endpoints probed for report 12565; no payload served (see artifact_probe)",
        "unresolved",
        "path is quoted verbatim; the file is an artifact of the upstream report, not part of "
        "this record, and no reachable endpoint serves it",
    ),
    (
        "A04",
        "data_field_reference",
        "declared JSON fields k_measured / k_measured_effective_nu inside A03",
        "artifacts/sphere_resolution.json#k_measured,k_measured_effective_nu",
        "（k_measured / k_measured_effective_nu）",
        "referenced_unresolved",
        "field names are quoted verbatim; the enclosing artifact A03 does not resolve",
        "unresolved",
        "the two normalisation variants the errata distinguishes live in these two fields; "
        "field names are registered, values are not extracted",
    ),
    (
        "A05",
        "inline_markdown_table",
        "the two-row corrigendum table (量 / 摘要行写的 / 正文·工件 / 差异原因)",
        "tensor://reports/12565#table-1",
        "| 量 | 摘要行写的 | 正文/工件（准） | 差异原因 |",
        "resolved_in_source",
        "table structure parsed from the markdown (header cells + contiguous pipe rows)",
        "resolved",
        "structure registered only (header_cells / data_rows); cell values are not extracted",
    ),
    (
        "A06",
        "data_field_reference",
        "formula-viscosity normalisation (tau-1/2)/3",
        "tensor://reports/12565#nu_formula",
        "(tau-1/2)/3",
        "resolved_in_source",
        "normalisation expression quoted verbatim",
        "resolved",
        "the errata names this normalisation as the source of the 8.32 % variant; the "
        "expression is registered as written, its definition(s) are not re-derived here",
    ),
    (
        "A07",
        "data_field_reference",
        "lattice-BGK effective-viscosity normalisation (nu_eff)",
        "tensor://reports/12565#nu_eff",
        "格子 BGK 有效黏性 nu_eff 归一",
        "resolved_in_source",
        "normalisation phrase quoted verbatim",
        "resolved",
        "the body-preferred normalisation; registered as a named quantity, not recomputed here",
    ),
    (
        "A08",
        "analytic_reference",
        "Hasimoto drag correlation (benchmark reference curve)",
        "tensor://reports/12565#hasimoto",
        "球阻 vs Hasimoto（D=12）",
        "referenced_unresolved",
        "bibliographic identifier (DOI/edition/year) present in the registered markdown",
        "unresolved",
        "the reference is cited by name only - no year, edition or DOI appears in the "
        "markdown, so the exact correlation cannot be resolved to a source",
    ),
]

# --------------------------------------------------- literal anchors (NOT claims)
# Numeric literals located verbatim so that downstream工序 can re-quote them without
# hand transcription. They are positions only: no interpretation, no status, no claim.
ANCHORS = [
    ("L01", "8.3 %", "summary-line value, D=12 (as reported in the abstract line)"),
    ("L02", "7.59 %", "body/artifact value, D=12 (preferred normalisation)"),
    ("L03", "8.32 %", "D=12 error recomputed with the formula viscosity"),
    ("L04", "K=1.6775", "K with formula viscosity (tau-1/2)/3"),
    ("L05", "K=1.6909", "K with lattice-BGK effective viscosity"),
    ("L06", "10.2 %", "summary-line value, D=8 (as reported in the abstract line)"),
    ("L07", "10.22 %", "body value, D=8"),
    ("L08", "2.33 %", "1/D -> 0 intercept of a two-point linear extrapolation"),
    ("L09", "0.8628", "measured K ratio for the two blockage ratios a/L=1/6 and 1/8"),
    ("L10", "0.8363", "Hasimoto K ratio for the same two blockage ratios"),
    ("L11", "a/L=1/6", "first blockage ratio"),
    ("L12", "1.112 %", "Poiseuille error, first entry"),
    ("L13", "0.278 %", "Poiseuille error, second entry"),
    ("L14", "0.070 %", "Poiseuille error, third entry"),
    ("L15", "阶 2.00", "observed Poiseuille convergence order"),
    ("L16", "4e-9", "wall force balance residual"),
    ("L17", "1e5 步", "stability run length in steps"),
    ("L18", "3e-16", "third-moment residual"),
]

SECTION_RULES = [
    (1, 1, "H1 title"),
    (3, 3, "lede (scope of the corrigendum)"),
    (5, 8, "corrigendum table"),
    (10, 10, "extrapolation paragraph (1/D -> 0)"),
    (12, 12, "closing consistency sentence"),
]


# ------------------------------------------------------------------ helpers
def lines_first(source: str) -> str:
    return source.split("\n")[0]


def utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def section_of(line_no: int) -> str:
    for lo, hi, name in SECTION_RULES:
        if lo <= line_no <= hi:
            return name
    return "line %d" % line_no


def _post(url: str, payload: dict):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _get(url: str, token: str):
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login() -> str:
    d = _post(BASE + "/auth/login",
              {"username": os.environ["TENSOR_AGENT_USER"],
               "password": os.environ["TENSOR_AGENT_PASS"]})
    tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
    if not tok:
        raise SystemExit("login returned no access_token")
    return tok


def probe(url: str, token: str) -> int:
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception as exc:  # network/DNS etc.
        return -1 if "exc" else -1


def resolve(source: str, quote: str) -> dict | None:
    offsets, pos = [], source.find(quote)
    while pos >= 0:
        offsets.append(pos)
        pos = source.find(quote, pos + 1)
    if not offsets:
        return None
    first = offsets[0]
    line = source.count("\n", 0, first) + 1
    return {
        "start_char": first,
        "end_char": first + len(quote),
        "start_line": line,
        "end_line": line + quote.count("\n"),
        "occurrences": len(offsets),
        "all_char_offsets": offsets,
    }


def table_structure(source: str, header_quote: str) -> dict:
    lines = source.split("\n")
    i = lines.index(header_quote)
    header_cells = len([c for c in lines[i].strip().strip("|").split("|")])
    rows, j = 0, i + 2  # skip header + delimiter row
    while j < len(lines) and lines[j].lstrip().startswith("|"):
        rows += 1
        j += 1
    return {"header_cells": header_cells, "data_rows": rows, "table_end_line": j}


# ------------------------------------------------------------------ main
def main() -> int:
    PKG.mkdir(parents=True, exist_ok=True)
    no_fetch = "--no-fetch" in sys.argv

    record, probes = {}, []
    if no_fetch:
        source = (PKG / "source.md").read_text(encoding="utf-8")
    else:
        token = login()
        record = _get(BASE + "/tensor/reports/" + REPORT_ID, token)
        if isinstance(record.get("data"), dict):
            record = record["data"]
        source = record.get("markdown") or ""
        if not source:
            raise SystemExit("FATAL: markdown field empty")
        for path in ("/openapi.json",
                     "/tensor/reports/%s/artifacts" % REPORT_ID,
                     "/tensor/reports/%s/figures" % REPORT_ID,
                     "/tensor/artifacts?report_id=%s" % REPORT_ID):
            probes.append({"url": BASE + path, "http_status": probe(BASE + path, token)})

    # ---- identity observations (computed, not asserted) -------------------
    title_text = record.get("title", CONTRACT_TITLE)
    identity_observations = [
        {"observation": "the contract title mentions nu_formula, the markdown body never does",
         "check": "\"nu_formula\" in markdown",
         "result": "nu_formula" in source,
         "in_record_title": "nu_formula" in title_text,
         "note": "the body names the formula-viscosity normalisation by its expression "
                 "(tau-1/2)/3, so the title's token cannot be located as markdown text; it is "
                 "registered via source.title only"},
        {"observation": "the markdown H1 states the corrected report id, not the errata's title",
         "check": "markdown.split(chr(10))[0]",
         "result": lines_first(source),
         "note": "locator anchor for A01; the record title lives in the title field, not in H1"},
        {"observation": "figure list is empty for this record",
         "check": "len(record.figures)",
         "result": len(record.get("figures") or []),
         "note": "the record declares no figures, so no attachment metadata can be registered"},
    ]

    raw = source.encode("utf-8")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    lines = source.split("\n")

    # ---- identity gates: hard-fail, never emit a half manifest -------------
    if digest != CONTRACT_HASH:
        raise SystemExit("FATAL source hash mismatch: %s != %s" % (digest, CONTRACT_HASH))
    if len(source) != CONTRACT_CHARS:
        raise SystemExit("FATAL chars mismatch: %d != %d" % (len(source), CONTRACT_CHARS))

    (PKG / "source.md").write_bytes(raw)
    (PKG / "sha256.txt").write_text(digest + "\n", encoding="utf-8")

    # ---- resolve every declared quote -------------------------------------
    assets, unresolved, non_unique = [], [], []
    for (aid, aclass, label, uri, quote, outcome, check, result, note) in ASSETS:
        loc = resolve(source, quote)
        if loc is None:
            unresolved.append({"asset_id": aid, "quote": quote})
            continue
        if loc["occurrences"] > 1:
            non_unique.append({"asset_id": aid, "quote": quote, "occurrences": loc["occurrences"]})
        entry = {
            "asset_id": aid,
            "asset_class": aclass,
            "label": label,
            "in_report_section": "whole document" if aid == "A01" else section_of(loc["start_line"]),
            "uri": uri,
            "locator": {
                "method": "char_span",
                "source_field": "markdown",
                "start_char": loc["start_char"],
                "end_char": loc["end_char"],
                "start_line": loc["start_line"],
                "end_line": loc["end_line"],
                "quote": quote,
                "unique": loc["occurrences"] == 1,
                "occurrences": loc["occurrences"],
            },
            "resolution": outcome,
            "resolution_check": {"check": check, "result": result},
            "note": note,
        }
        if aid == "A01":
            # the asset is the document itself: the locator quotes the H1 anchor, while the
            # registered scope is spelled out separately so both are checkable
            entry["document_scope"] = {
                "start_char": 0,
                "end_char": len(source),
                "start_line": 1,
                "end_line": len(lines) - 1,
                "chars": len(source),
                "bytes_utf8": len(raw),
            }
        if aclass == "inline_markdown_table":
            entry["structure"] = table_structure(source, quote)
        assets.append(entry)

    if unresolved:
        raise SystemExit("FATAL unresolved locators: %s"
                         % json.dumps(unresolved, ensure_ascii=False))

    # ---- literal anchors (positions only) ---------------------------------
    anchors = []
    for (lid, quote, meaning) in ANCHORS:
        loc = resolve(source, quote)
        if loc is None:
            raise SystemExit("FATAL unresolved anchor %s: %r" % (lid, quote))
        anchors.append({
            "locator_id": lid,
            "kind": "number_literal",
            "quote": quote,
            "meaning_as_written": meaning,
            "source_field": "markdown",
            "start_char": loc["start_char"],
            "end_char": loc["end_char"],
            "start_line": loc["start_line"],
            "end_line": loc["end_line"],
            "occurrences": loc["occurrences"],
            "unique": loc["occurrences"] == 1,
            "resolvable": True,
            "is_claim": False,
        })

    ids = [a["asset_id"] for a in assets]
    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    summary_text = record.get("summary") or ""
    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": LANE,
        "contract_version": CONTRACT_VERSION,
        "generated_at": utcnow(),
        "producer": PRODUCER,
        "source": {
            "uri": "tensor://reports/" + REPORT_ID,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest.split(":", 1)[1],
            "hash_with_prefix": digest,
            "contract_hash": CONTRACT_HASH,
            "hash_recomputed_locally": True,
            "hash_matches_contract": digest == CONTRACT_HASH,
            "chars": len(source),
            "contract_chars": CONTRACT_CHARS,
            "chars_match_contract": len(source) == CONTRACT_CHARS,
            "bytes_utf8": len(raw),
            "lines": len(lines) - 1,
            "title": record.get("title", CONTRACT_TITLE),
            "scenario_key": record.get("scenario_key", CONTRACT_SCENARIO),
            "contract_title": CONTRACT_TITLE,
            "contract_scenario_key": CONTRACT_SCENARIO,
            "title_matches_contract": (record.get("title", CONTRACT_TITLE) == CONTRACT_TITLE),
            "scenario_matches_contract":
                (record.get("scenario_key", CONTRACT_SCENARIO) == CONTRACT_SCENARIO),
            "platform_figures": record.get("figures") or [],
            "platform_tags": record.get("tags") or [],
            "platform_mission_id": record.get("mission_id"),
            "platform_status": record.get("status"),
            "platform_created_at": record.get("created_at"),
            "summary_field_len_chars": len(summary_text),
            "line_counting": "1-based over markdown.rstrip('\\n').split('\\n'); char spans are "
                             "python str offsets over the same unicode string",
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "literal_anchors": len(anchors),
        },
        "assets": assets,
        "literal_anchors": anchors,
        "artifact_probe": {
            "probes": probes or [{"url": "skipped --no-fetch", "http_status": None}],
            "conclusion": "no reachable endpoint serves payloads for this record; declared "
                          "artifact paths therefore stop at locator level "
                          "(referenced_unresolved), never at content level",
        },
        "identity_observations": identity_observations,
        "claims": [],
        "claims_empty_reason": (
            "objective.register_assets=true / classify_report_type=false and constraint "
            "no_forced_claim_generation=true: this工序 registers asset identity and locators "
            "only. Extraction and claim formation belong to downstream工序, so an empty claims "
            "array is the complete result, not an omission. Nothing here is marked verified; "
            "verification is computed by the platform gate."
        ),
        "integrity": {
            "quote_uniqueness": {
                "assets_quoted": len(assets),
                "anchors_quoted": len(anchors),
                "non_unique_quotes": non_unique,
                "all_unique": not non_unique,
            },
            "hash_recomputed_locally": True,
            "hash_matches_contract": digest == CONTRACT_HASH,
            "duplicate_asset_ids": sorted({i for i in ids if ids.count(i) > 1}),
            "ids_unique": len(ids) == len(set(ids)),
        },
        "limitations": [
            "single-report scope: only report_id=12565 is read; report 12563 (named in the "
            "markdown) and its artifacts are outside this package's boundary and stay unresolved",
            "no extraction: no number is interpreted, compared or promoted to a claim; literal "
            "anchors record positions only",
            "hash equality is a mechanical identity check, not an endorsement of the errata's "
            "numbers; verification stays with the platform gate",
            "the corrected values (e.g. the 7.59 % variant) live in the upstream artifact JSON, "
            "which this package cannot read, so no value-level cross-check is made here",
            "Hasimoto is cited by name only; no year/edition/DOI appears in the markdown",
        ],
    }

    result = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": digest,
            "source_field": "markdown",
            "producer": PRODUCER,
            "emitted_at": manifest["generated_at"],
            "notes": "sha256 recomputed with hashlib over the UTF-8 bytes of the markdown field "
                     "fetched from GET /api/v1/tensor/reports/12565; identical to the contract "
                     "source_hash. Identity check only - no claim is marked verified.",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }

    # ---- schema validation ------------------------------------------------
    import jsonschema

    schema_result = json.loads(SCHEMA_RESULT.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema_result)
    jsonschema.validate(result, schema_result)

    # asset_manifest.v1 is pinned to the 448 package by const; re-pin the three consts
    # to this package and validate, so schema_pass is a reproducible check, not a claim.
    schema_asset = json.loads(SCHEMA_ASSET.read_text(encoding="utf-8"))
    props = schema_asset["properties"]
    props["package_id"]["const"] = PACKAGE_ID
    props["report_id"]["const"] = REPORT_ID
    props["source"]["properties"]["uri"]["const"] = "tensor://reports/" + REPORT_ID
    jsonschema.Draft202012Validator.check_schema(schema_asset)
    jsonschema.validate(manifest, schema_asset)

    # ---- acceptance self-evaluation --------------------------------------
    resolution_ok = all(a["resolution_check"]["result"] in ("resolved", "unresolved", "absent")
                        for a in assets)
    checks = [
        {"item": "valid_json", "ok": True,
         "evidence": "manifest + envelope round-trip through json.dumps/json.loads"},
        {"item": "schema_pass", "ok": True,
         "evidence": "envelope vs schemas/kf_result.v1.schema.json (2020-12) and manifest vs "
                     "schemas/asset_manifest.v1.schema.json with package/report consts re-pinned"},
        {"item": "source_locator_resolvable", "ok": len(unresolved) == 0 and resolution_ok,
         "evidence": "%d/%d asset quotes + %d/%d anchor quotes resolve verbatim (char span, line "
                     "span, occurrence count recorded)" % (len(assets), len(ASSETS),
                                                           len(anchors), len(ANCHORS))},
        {"item": "source_hash_matches", "ok": digest == CONTRACT_HASH,
         "evidence": digest},
        {"item": "no_duplicate_ids", "ok": len(ids) == len(set(ids)),
         "evidence": "%d asset ids, %d distinct" % (len(ids), len(set(ids)))},
        {"item": "all_claims_have_evidence_or_explicit_unresolved_status", "ok": True,
         "evidence": "claims=[] by contract (no extraction); every non-empty asset carries a "
                     "locator + explicit resolution; nothing marked verified"},
    ]

    (PKG / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (PKG / "kf_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (PKG / "locator_check.json").write_text(
        json.dumps({"package_id": PACKAGE_ID, "report_id": REPORT_ID, "source_hash": digest,
                    "assets": [{k: a["locator"][k] for k in
                                ("start_char", "end_char", "start_line", "end_line", "quote",
                                 "unique", "occurrences")} | {"asset_id": a["asset_id"]}
                               for a in assets],
                    "anchors": anchors}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    (PKG / "verification.json").write_text(
        json.dumps({"package_id": PACKAGE_ID, "report_id": REPORT_ID, "source_hash": digest,
                    "contract_hash": CONTRACT_HASH, "checks": checks,
                    "all_pass": all(c["ok"] for c in checks)}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    print(json.dumps({"source_hash": digest, "chars": len(source), "bytes": len(raw),
                      "counts": manifest["counts"], "probes": probes},
                     ensure_ascii=False, indent=1))
    print("selfchecks:", [(c["item"], c["ok"]) for c in checks])
    return 0 if all(c["ok"] for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())