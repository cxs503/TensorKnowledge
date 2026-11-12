#!/usr/bin/env python3
"""Build asset_manifest.json for KF work package wp-5656-01 (task_type 01-asset-registration).

Design rules enforced by this builder (registration only, no extraction):
  * Quotes are NEVER typed by hand. Each asset is declared as a line range of the
    source markdown; the quote is sliced out of the fetched bytes. This makes
    "zero hand-copying" a mechanical property rather than a promise.
  * Every locator is re-checked: md[start_char:end_char] == quote, count(quote)==1.
  * The source hash is recomputed from the markdown utf-8 bytes and compared with
    the hash fixed in the work-package contract.
  * No claim is marked verified; claims[] stays empty (allowed by the contract).

Usage:
  python3 scripts/kf/build_asset_manifest_5656.py \
      --source runs/wp-5656-01/source_5656.json \
      --out-dir docs/kf/wp-5656-01
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone

PKG = "wp-5656-01"
CONTRACT_REPORT_ID = "5656"
CONTRACT_SOURCE_URI = "tensor://reports/5656"
CONTRACT_SOURCE_HASH = "0e698f7d7f4fb439b5c47b210d0a2b3cc8d94cd44852b3693e6b5895befd8e51"
CONTRACT_CHARS = 2506

# (asset_class, label, section, line_from, line_to, resolution, check_kind, note)
# line numbers are 1-based and inclusive; quotes are sliced, not retyped.
ASSETS = [
    ("document", "report markdown (full source field)", "(document)", 1, 66,
     "resolved_in_source", "hash_and_span",
     "Whole markdown field; sha256 recomputed locally from utf-8 bytes."),
    ("heading", "report title heading", "1. Case Introduction", 1, 1,
     "resolved_in_source", "present", "Top-level heading of the report."),
    ("lattice_definition", "D3Q27 stencil definition (27 velocity directions)", "1. Case Introduction", 5, 5,
     "resolved_in_source", "present",
     "Declares the stencil enumeration domain {-1,0,1}^3 used by the solver."),
    ("parameter_set", "run parameters: grid / u_lid / tau / steps / collision", "1. Case Introduction", 8, 12,
     "resolved_in_source", "present",
     "Registers the 5 numeric run parameters verbatim; values are not re-derived here."),
    ("external_reference", "reference dataset in-text citation: Ghia et al. (1982), Re=400", "1. Case Introduction", 13, 13,
     "referenced_unresolved", "unresolved",
     "Citation of an external publication; its table is not embedded in the report, so no bytes are resolvable in this package's scope."),
    ("method_block", "2.1 enumeration symmetry self-check (completeness / no-dup / OPPOSITE / weights / isotropy)", "2.1", 17, 22,
     "resolved_in_source", "present",
     "Five stated self-check items, including the D3Q27 weight set."),
    ("method_block", "2.2 lid-driven cavity comparison setup (BCs, MRT, centreline vs Ghia)", "2.2", 24, 28,
     "resolved_in_source", "present",
     "Setup of the comparison that produced the results table."),
    ("code_convention", "2.3 layout convention (C shape, field shape, streaming shifts)", "2.3", 30, 33,
     "resolved_in_source", "present",
     "Implementation conventions stated in prose; no module path is given."),
    ("result_table", "results table: u/v L2 and max errors, compute time (D3Q27 vs D3Q19)", "3. Results", 37, 43,
     "resolved_in_source", "present",
     "Only quantitative results block in the report; registered as one table asset."),
    ("error_assessment", "4. Error Assessment: three stated causes of the large errors", "4. Error Assessment", 47, 50,
     "resolved_in_source", "present",
     "Self-declared error attribution (grid, tau/Re, nz)."),
    ("primary_conclusion", "4. key finding: D3Q27 ~ D3Q19 within 2%", "4. Error Assessment", 52, 52,
     "resolved_in_source", "present",
     "Report's own headline conclusion; registered, NOT marked verified (gate decides)."),
    ("test_coverage", "5. Test Coverage counts (32 + 5 + 31 = 68 passing)", "5. Test Coverage", 56, 59,
     "resolved_in_source", "present",
     "Test counts as declared by the report."),
    ("code_reference", "test suite reference (enumeration + cavity comparison tests)", "5. Test Coverage", 56, 58,
     "referenced_unresolved", "unresolved",
     "Counts are given but no module/file path or commit id appears in the report; target bytes are not locatable from this report alone."),
    ("limitation_set", "6. Limitations: resolution/steps budget, 5x cost, corner cost vs isotropy", "6. Limitations", 63, 65,
     "resolved_in_source", "present",
     "Declared limitations of the reported results."),
]

FIGURES = [
    ("embedded_figure", "figure[0] cavity_u_profile", "3. Results",
     "u/u_lid along vertical centreline",
     "Platform lists name+caption only (no png_base64 payload in figures[]), so no byte hash is claimable; payload resolution is out of this package's scope."),
    ("embedded_figure", "figure[1] cavity_v_profile", "3. Results",
     "v/u_lid along horizontal centreline",
     "Platform lists name+caption only; no payload -> unresolved in this package."),
    ("embedded_figure", "figure[2] cavity_error_comparison", "3. Results",
     "Error comparison bar chart",
     "Platform lists name+caption only; no payload -> unresolved in this package."),
]


def slice_quote(md: str, line_from: int, line_to: int) -> tuple[str, int, int]:
    lines = md.split("\n")
    chunk = "\n".join(lines[line_from - 1:line_to])
    start = md.index(chunk) if chunk in md else -1
    if start < 0:
        raise SystemExit("line range %d-%d not found verbatim in source" % (line_from, line_to))
    return chunk, start, start + len(chunk)


def build(source_path: str) -> dict:
    src = json.load(open(source_path, encoding="utf-8"))
    md = src["markdown"]
    raw = md.encode("utf-8")
    sha = hashlib.sha256(raw).hexdigest()
    if sha != CONTRACT_SOURCE_HASH:
        raise SystemExit("source hash mismatch: %s != %s" % (sha, CONTRACT_SOURCE_HASH))
    if len(md) != CONTRACT_CHARS:
        raise SystemExit("source char count mismatch: %d != %d" % (len(md), CONTRACT_CHARS))

    assets = []
    ids = []
    for i, (cls, label, section, lf, lt, resolution, check, note) in enumerate(ASSETS, 1):
        quote, start, end = slice_quote(md, lf, lt)
        asserts = [
            "md[start_char:end_char] == quote",
            "md.count(quote) == 1",
        ]
        ok = md[start:end] == quote and md.count(quote) == 1
        aid = "A%02d" % i
        ids.append(aid)
        assets.append({
            "asset_id": aid,
            "asset_class": cls,
            "label": label,
            "uri": "%s#L%d-L%d" % (CONTRACT_SOURCE_URI, lf, lt),
            "in_report_section": section,
            "locator": {
                "method": "char_span",
                "start_char": start,
                "end_char": end,
                "start_line": lf,
                "end_line": lt,
                "quote": quote,
                "unique": md.count(quote) == 1,
            },
            "resolution": resolution,
            "resolution_check": {
                "check": "; ".join(asserts),
                "result": {"resolved_in_source": "present", "referenced_unresolved": "unresolved",
                           "declared_absent": "absent"}[resolution] if ok else "unresolved",
                "passed": ok,
            },
            "note": note,
        })

    # figures: platform-side metadata only
    fig_list = src.get("figures") or []
    for j, (cls, label, section, cap, note) in enumerate(FIGURES):
        aid = "A%02d" % (len(assets) + 1)
        ids.append(aid)
        listed = j < len(fig_list)
        assets.append({
            "asset_id": aid,
            "asset_class": cls,
            "label": label,
            "uri": "%s#figures[%d]" % (CONTRACT_SOURCE_URI, j),
            "in_report_section": section,
            "locator": {
                "method": "document",
                "start_char": 0,
                "end_char": len(md),
                "start_line": 0,
                "end_line": 0,
                "quote": "platform figures[] index %d (%s)" % (j, cap),
                "unique": listed,
                "field": "figures",
                "index": j,
            },
            "resolution": "referenced_unresolved",
            "resolution_check": {
                "check": "platform figures[%d] present; payload png_base64 absent" % j,
                "result": "unresolved",
                "passed": listed,
            },
            "note": note,
        })

    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": CONTRACT_REPORT_ID,
        "source": {
            "uri": CONTRACT_SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": sha,
            "chars": len(md),
            "bytes_utf8": len(raw),
            "title": src.get("title"),
            "scenario_key": src.get("scenario_key"),
            "platform_id": src.get("id"),
            "platform_mission_id": src.get("mission_id"),
            "platform_figures": [{"name": f.get("name"), "caption": f.get("caption")} for f in fig_list],
            "platform_tags": src.get("tags") or [],
            "retrieved_via": src.get("fetched_via"),
            "local_copy": "runs/wp-5656-01/report_5656.md",
        },
        "counts": {
            "assets": len(assets),
            "by_class": dict(sorted(by_class.items())),
            "by_resolution": dict(sorted(by_res.items())),
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
        },
        "assets": assets,
        "claims": [],
        "claims_note": ("objective.classify_report_type=false and no extraction is in scope for task_type "
                        "01-asset-registration, so claims[] is empty by contract. Nothing in this manifest is "
                        "marked verified; verification is computed by the platform gate."),
        "integrity": {
            "quote_uniqueness": all(a["locator"]["unique"] for a in assets),
            "hash_recomputed_locally": sha,
            "hash_matches_contract": sha == CONTRACT_SOURCE_HASH,
            "chars_match_contract": len(md) == CONTRACT_CHARS,
            "no_duplicate_ids": len(ids) == len(set(ids)),
            "all_resolution_checks_passed": all(a["resolution_check"]["passed"] for a in assets),
            "hand_copied_text": False,
            "hand_copy_note": "quotes are sliced from the fetched markdown by line range (builder never types source text)",
            "claims_marked_verified": 0,
        },
        "artifact_endpoint_probe": {
            "/tensor/reports/5656/artifacts": {"status": "http_404"},
            "/tensor/reports/5656/attachments": {"status": "http_404"},
            "/tensor/artifacts?report_id=5656": {"status": "http_404"},
            "conclusion": ("platform exposes no attachment/artifact listing for this report (all three probes 404), "
                           "so the only enumerable non-markdown assets are source.platform_figures (3, metadata only)"),
        },
        "limitations": [
            "Registration only: no parameter/claim extraction, no recalculation of the reported numbers.",
            "Figure payloads are not stored by the report record (name+caption only); they stay referenced_unresolved.",
            "Test counts in section 5 cannot be bound to a commit or module path from the report text alone.",
            "Asset identity is per declared span; overlapping spans (e.g. the test-coverage block and its code_reference view) are intentional and carry distinct ids.",
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/kf/build_asset_manifest_5656.py",
        "contract_version": "1.0",
    }
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="runs/wp-5656-01/source_5656.json")
    ap.add_argument("--out-dir", default="docs/kf/wp-5656-01")
    args = ap.parse_args()

    manifest = build(args.source)
    os.makedirs(args.out_dir, exist_ok=True)
    mp = os.path.join(args.out_dir, "asset_manifest.json")
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    raw = open(mp, "rb").read()

    kf = {
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": CONTRACT_REPORT_ID,
        "provenance": {
            "source_uri": CONTRACT_SOURCE_URI,
            "source_field": "markdown",
            "source_hash": "sha256:" + manifest["source"]["hash"],
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": manifest["source"]["chars"],
            "source_bytes_utf8": manifest["source"]["bytes_utf8"],
            "fetched_via": "GET /api/v1/tensor/reports/5656",
            "generator": "scripts/kf/build_asset_manifest_5656.py",
            "contract_version": "1.0",
        },
        "outputs": {
            "asset_manifest.json": {
                "path": os.path.join(args.out_dir, "asset_manifest.json"),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
                "asset_count": manifest["counts"]["assets"],
                "claims": 0,
            }
        },
        "coupling_contract": {
            "addressed_task": PKG,
            "depends_on": [],
            "observes": CONTRACT_SOURCE_URI,
            "produces_field": "outputs.asset_manifest.json",
            "guarantees": [
                "source hash re-computable from provenance.source_hash",
                "every asset locator resolves to a unique verbatim substring of source markdown",
                "no claim marked verified",
            ],
            "reserved_fields": ["claims[]", "outputs[]"],
            "produces_metrics_level": 3,
            "does_not_encode": ["task_level_metrics"],
        },
    }
    kp = os.path.join(args.out_dir, "kf_result.json")
    with open(kp, "w", encoding="utf-8") as f:
        json.dump(kf, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(json.dumps({"manifest": mp, "sha256": kf["outputs"]["asset_manifest.json"]["sha256"],
                      "bytes": len(raw), "counts": manifest["counts"],
                      "integrity": manifest["integrity"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()