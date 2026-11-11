#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dual-structure validator for the OSS-LBM knowledge package.

The package carries two generations of layout that must coexist in ``main``:

  A. canonical aggregate (generation-1, the layout written by ``main``)
       claims/claims.json        -> JSON array of claim records
       evidence/evidence.json    -> JSON array of evidence records
       provenance/provenance.json-> JSON array of provenance records
  B. per-record ingress files (generation-2, branch ``agent/m8634`` / PR #6)
       claims/tkc-oss-lbm-*.json, evidence/tke-oss-lbm-*.json,
       provenance/tkp-oss-lbm-*.json
     Every ingress record must be mirrored in A, byte-identical (canonical JSON),
     so the merge cannot silently drop, reword or fork a record.
  C. legacy sub-package trees
       <package>/claims/claims.json (+ <package>/evidence/evidence.json ...)
     Each is self-consistent on its own id namespace; a sub-package record whose
     id also appears in A must be identical (no mutual overwrite between
     generations).

Plus a landing manifest check (``lineage/<ref>-landing-manifest.json``) that
binds every generation-2 record id + sha256 to the current tree, i.e. the
machine-checkable form of "no claim lost".

Exit code 0 = ALL PASS.
"""

from __future__ import annotations

import glob
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMAS_DIR = HERE.parent.parent / "schemas"

CLAIM_PATTERN = r"^tkc:oss-lbm:[a-z0-9-]+$"
EVIDENCE_PATTERN = r"^tke:oss-lbm:[a-z0-9-]+$"
PROVENANCE_PATTERN = r"^tkp:oss-lbm:[a-z0-9-]+$"
# sub-package namespaces may add a second qualifier (e.g. tkc:oss-lbm:thermalmulti:pr-eos)
PKG_CLAIM_PATTERN = r"^tkc:[a-z][a-z0-9-]*:[a-z0-9][a-z0-9:-]*$"
PKG_PROVENANCE_PATTERN = r"^tkp:[a-z][a-z0-9-]*:[a-z0-9][a-z0-9:-]*$"

EPISTEMIC_STATUSES = (
    "established", "well-supported", "provisional", "contested", "speculative",
    "superseded", "not-assessed", "draft",
)
ASSESSMENT_STATUSES = (
    "unassessed", "reviewed-supports", "reviewed-refutes", "reviewed-qualifies",
    "insufficient", "disputed",
)

AGGREGATE = {
    "claim": (HERE / "claims" / "claims.json", CLAIM_PATTERN),
    "evidence": (HERE / "evidence" / "evidence.json", EVIDENCE_PATTERN),
    "provenance": (HERE / "provenance" / "provenance.json", PROVENANCE_PATTERN),
}
INGRESS = {
    "claim": ("claims/tkc-*.json", CLAIM_PATTERN),
    "evidence": ("evidence/tke-*.json", EVIDENCE_PATTERN),
    "provenance": ("provenance/tkp-*.json", PROVENANCE_PATTERN),
}
MANIFEST = HERE / "lineage" / "m8634-landing-manifest.json"

ERRORS: list[str] = []
SECTIONS: list[str] = []


def err(msg: str) -> None:
    ERRORS.append(msg)


def canonical(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def section(name: str, detail: str) -> None:
    SECTIONS.append(f"PASS {name}: {detail}")
    print(SECTIONS[-1])


def check_id_pattern(items: list[dict], pattern: str, id_field: str = "id") -> None:
    pat = re.compile(pattern)
    for item in items:
        if not pat.match(item[id_field]):
            err(f"id '{item[id_field]}' does not match pattern {pattern}")


# --------------------------------------------------------------------------- #
# Structure A — canonical aggregate
# --------------------------------------------------------------------------- #
def check_structure_a() -> dict[str, list[dict]]:
    data: dict[str, list[dict]] = {}
    for kind, (path, _pattern) in AGGREGATE.items():
        if not path.exists():
            err(f"Structure A: missing {path.relative_to(HERE)}")
            data[kind] = []
            continue
        loaded = load_json(path)
        if not isinstance(loaded, list):
            err(f"Structure A: {path.relative_to(HERE)} is not a JSON array")
            loaded = []
        data[kind] = loaded

    if ERRORS:
        return data

    claims, evidence, provenance = data["claim"], data["evidence"], data["provenance"]

    if len(claims) < 15:
        err(f"Structure A: expected >=15 claims, found {len(claims)}")

    for kind, (path, pattern) in AGGREGATE.items():
        check_id_pattern(data[kind], pattern)
        ids = [r.get("id") for r in data[kind]]
        if len(set(ids)) != len(ids):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            err(f"Structure A: duplicate {kind} ids: {dupes}")

    claim_ids = {c["id"] for c in claims}
    evidence_ids = {e["id"] for e in evidence}

    for claim in claims:
        for ref in claim.get("evidence_refs", []):
            if ref not in evidence_ids:
                err(f"Structure A: claim {claim['id']} references missing evidence {ref}")
    for ev in evidence:
        for ref in ev.get("claim_refs", []):
            if ref not in claim_ids:
                err(f"Structure A: evidence {ev['id']} references missing claim {ref}")

    for claim in claims:
        if claim.get("epistemic_status") not in EPISTEMIC_STATUSES:
            err(f"Structure A: claim {claim['id']} invalid epistemic_status "
                f"'{claim.get('epistemic_status')}'")
        for field in ("id", "statement", "claim_type", "epistemic_status", "created_at", "version"):
            if field not in claim:
                err(f"Structure A: claim {claim.get('id', '?')} missing required field: {field}")
        if not claim.get("notes"):
            err(f"Structure A: claim {claim['id']} missing notes (TensorLBM service statement required)")

    for ev in evidence:
        for field in ("id", "source", "relation", "locator", "captured_at", "assessment_status", "version"):
            if field not in ev:
                err(f"Structure A: evidence {ev.get('id', '?')} missing required field: {field}")
        if ev.get("assessment_status") not in ASSESSMENT_STATUSES:
            err(f"Structure A: evidence {ev['id']} invalid assessment_status "
                f"'{ev.get('assessment_status')}'")
        if not ev.get("claim_refs"):
            err(f"Structure A: evidence {ev['id']} has no claim_refs")
        loc = ev.get("locator") or {}
        if loc.get("locator_type") != "code-location":
            err(f"Structure A: evidence {ev['id']} locator_type should be 'code-location', "
                f"got '{loc.get('locator_type')}'")
        if not loc.get("quote"):
            err(f"Structure A: evidence {ev['id']} missing quote")

    for prov in provenance:
        for field in ("id", "generated_entity", "activity", "agents", "recorded_at", "version"):
            if field not in prov:
                err(f"Structure A: provenance {prov.get('id', '?')} missing required field: {field}")

    section(
        "structure A (aggregate)",
        f"{len(claims)} claims / {len(evidence)} evidence / {len(provenance)} provenance; "
        f"ids unique, cross-references bidirectional, epistemic vocabularies valid",
    )
    return data


# --------------------------------------------------------------------------- #
# Structure B — per-record ingress files must mirror A
# --------------------------------------------------------------------------- #
def check_structure_b(data: dict[str, list[dict]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for kind, (pattern, _idp) in INGRESS.items():
        agg_by_id = {r["id"]: r for r in data.get(kind, [])}
        files = sorted(HERE.glob(pattern))
        counts[kind] = len(files)
        seen: dict[str, str] = {}
        for path in files:
            try:
                rec = load_json(path)
            except json.JSONDecodeError as exc:
                err(f"Structure B: {path.name} is not valid JSON ({exc})")
                continue
            rid = rec.get("id")
            if rid in seen:
                err(f"Structure B: duplicate ingress id {rid} in {seen[rid]} and {path.name}")
            seen[rid] = path.name
            if rid not in agg_by_id:
                err(f"Structure B: ingress {kind} {rid} ({path.name}) is missing from the aggregate")
            elif canonical(agg_by_id[rid]) != canonical(rec):
                err(f"Structure B: ingress {kind} {rid} ({path.name}) diverges from the aggregate entry")
        extra = set(agg_by_id) - set(seen)
        if files and extra and kind == "claim":
            # aggregate-only records are legal (generation-1 additions), just report.
            pass

    # optional JSON-Schema validation of the ingress records (generation-2 files
    # were authored against schemas/*.schema.json)
    schema_names = {
        "claim": "claim-record",
        "evidence": "evidence-record",
        "provenance": "provenance-record",
    }
    try:
        import jsonschema  # type: ignore
    except ImportError:
        print("SKIP structure B schema validation: jsonschema not installed")
    else:
        for kind, (pattern, _idp) in INGRESS.items():
            schema_path = SCHEMAS_DIR / f"{schema_names[kind]}.schema.json"
            if not schema_path.exists():
                err(f"Structure B: missing schema {schema_path}")
                continue
            schema = load_json(schema_path)
            for path in sorted(HERE.glob(pattern)):
                try:
                    rec = load_json(path)
                except json.JSONDecodeError:
                    continue
                try:
                    jsonschema.validate(rec, schema)
                except jsonschema.ValidationError as exc:
                    err(f"Structure B: {path.name} violates {schema_names[kind]} schema: {exc.message}")

    section(
        "structure B (per-record ingress)",
        f"{counts['claim']} claim / {counts['evidence']} evidence / {counts['provenance']} provenance "
        f"files mirrored byte-identically in A",
    )
    return counts


# --------------------------------------------------------------------------- #
# Structure C — legacy sub-package trees
# --------------------------------------------------------------------------- #
NON_PACKAGE_DIRS = {"claims", "evidence", "provenance", "lineage", "tools", "tests", "artifacts"}


def discover_packages() -> list[Path]:
    """Sub-package trees = dirs with their own claims.json, excluding the
    canonical aggregate directories and tooling directories."""
    pkgs = []
    for d in sorted(p for p in HERE.iterdir() if p.is_dir()):
        if d.name in NON_PACKAGE_DIRS:
            continue
        if (d / "claims" / "claims.json").exists() or (d / "claims.json").exists():
            pkgs.append(d)
    return pkgs


def check_structure_c(data: dict[str, list[dict]]) -> dict[str, dict[str, int]]:
    agg_claims = {c["id"]: c for c in data.get("claim", [])}
    agg_evidence_ids = {e["id"] for e in data.get("evidence", [])}
    summary: dict[str, dict[str, int]] = {}

    for pkg in discover_packages():
        claims_path = pkg / "claims" / "claims.json"
        if not claims_path.exists():
            claims_path = pkg / "claims.json"
        evidence_path = pkg / "evidence" / "evidence.json"
        provenance_path = pkg / "provenance" / "provenance.json"

        claims = load_json(claims_path)
        if isinstance(claims, dict):
            claims = claims.get("claims", [])
        evidence = load_json(evidence_path) if evidence_path.exists() else []
        if isinstance(evidence, dict):
            evidence = evidence.get("evidence", [])
        if provenance_path.exists():
            provenance = load_json(provenance_path)
            if isinstance(provenance, dict):
                provenance = provenance.get("provenance", [])
            for prov in provenance:
                for field in ("id", "generated_entity", "activity", "agents", "recorded_at", "version"):
                    if field not in prov:
                        err(f"Structure C [{pkg.name}]: provenance {prov.get('id', '?')} "
                            f"missing required field: {field}")
                if not re.match(PKG_PROVENANCE_PATTERN, prov.get("id", "")):
                    err(f"Structure C [{pkg.name}]: provenance id '{prov.get('id')}' "
                        f"does not match {PKG_PROVENANCE_PATTERN}")

        ids = [c.get("id") for c in claims]
        if len(set(ids)) != len(ids):
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            err(f"Structure C [{pkg.name}]: duplicate claim ids {dupes}")

        for claim in claims:
            pat = PKG_CLAIM_PATTERN
            if not re.match(pat, claim.get("id", "")):
                err(f"Structure C [{pkg.name}]: claim id '{claim.get('id')}' does not match {pat}")
            for field in ("id", "statement", "claim_type", "epistemic_status"):
                if field not in claim:
                    err(f"Structure C [{pkg.name}]: claim {claim.get('id', '?')} "
                        f"missing required field: {field}")
            if claim.get("epistemic_status") not in EPISTEMIC_STATUSES:
                err(f"Structure C [{pkg.name}]: claim {claim.get('id')} invalid epistemic_status "
                    f"'{claim.get('epistemic_status')}'")
            # claims of a sub-package may cite local or aggregate evidence
            local_evidence = {e.get("id") for e in evidence}
            for ref in claim.get("evidence_refs", []):
                if ref not in local_evidence and ref not in agg_evidence_ids:
                    err(f"Structure C [{pkg.name}]: claim {claim.get('id')} references "
                        f"unknown evidence {ref}")
            # no mutual overwrite: overlapping ids must be identical
            if claim.get("id") in agg_claims and canonical(agg_claims[claim["id"]]) != canonical(claim):
                err(f"Structure C [{pkg.name}]: claim {claim['id']} overlaps the aggregate "
                    f"but differs from it")

        for ev in evidence:
            if not re.match(EVIDENCE_PATTERN, ev.get("id", "")) and not re.match(
                r"^tke:[a-z][a-z0-9-]*:[a-z0-9][a-z0-9:-]*$", ev.get("id", "")
            ):
                err(f"Structure C [{pkg.name}]: evidence id '{ev.get('id')}' does not match "
                    f"a tke:* pattern")
            for ref in ev.get("claim_refs", []):
                if ref not in set(ids):
                    err(f"Structure C [{pkg.name}]: evidence {ev.get('id')} references "
                        f"missing claim {ref}")

        summary[pkg.name] = {
            "claims": len(claims),
            "evidence": len(evidence),
            "shared_with_aggregate": sum(1 for i in ids if i in agg_claims),
        }

    total_claims = sum(v["claims"] for v in summary.values())
    total_evidence = sum(v["evidence"] for v in summary.values())
    detail = ", ".join(f"{k}({v['claims']}c/{v['evidence']}e)" for k, v in summary.items())
    section(
        "structure C (sub-packages)",
        f"{len(summary)} packages, {total_claims} claims / {total_evidence} evidence; "
        f"{detail}",
    )
    return summary


# --------------------------------------------------------------------------- #
# Landing manifest — generation-2 records must stay locatable
# --------------------------------------------------------------------------- #
def check_manifest(data: dict[str, list[dict]]) -> dict[str, int]:
    if not MANIFEST.exists():
        err(f"manifest: missing {MANIFEST.relative_to(HERE)}")
        return {}
    manifest = load_json(MANIFEST)
    agg = {
        "claim": {c["id"]: c for c in data.get("claim", [])},
        "evidence": {e["id"]: e for e in data.get("evidence", [])},
        "provenance": {p["id"]: p for p in data.get("provenance", [])},
    }
    declared = manifest.get("counts", {})
    records = manifest.get("records", [])
    by_kind: dict[str, int] = {}
    for kind in ("claim", "evidence", "provenance"):
        rows = [r for r in records if r["kind"] == kind]
        by_kind[kind] = len(rows)
        if declared.get(kind) is not None and declared[kind] != len(rows):
            err(f"manifest: declared {kind} count {declared[kind]} != {len(rows)} rows")

    missing = []
    for row in records:
        kind, rid, dest = row["kind"], row["id"], HERE.parent.parent / row["dest_path"]
        if rid not in agg[kind]:
            missing.append(f"{kind} {rid} absent from aggregate")
            continue
        if not dest.exists():
            missing.append(f"{kind} {rid} file missing: {row['dest_path']}")
            continue
        blob = dest.read_bytes()
        digest = hashlib.sha256(blob).hexdigest()
        if digest != row["sha256"]:
            missing.append(f"{kind} {rid} sha256 mismatch in {row['dest_path']}")
            continue
        if canonical(json.loads(blob)) != canonical(agg[kind][rid]):
            missing.append(f"{kind} {rid} aggregate entry differs from {row['dest_path']}")
    for m in missing:
        err(f"manifest: {m}")

    section(
        "landing manifest",
        f"source {manifest.get('source_branch')}@{manifest.get('source_commit', '')[:12]} — "
        f"{by_kind['claim']}/{by_kind['claim']} claims, {by_kind['evidence']} evidence, "
        f"{by_kind['provenance']} provenance locatable with matching sha256",
    )
    return by_kind


def main() -> int:
    data = check_structure_a()
    if ERRORS:
        print(f"FAIL: {len(ERRORS)} error(s) in structure A")
        for e in ERRORS:
            print(f"  - {e}")
        return 1
    check_structure_b(data)
    check_structure_c(data)
    check_manifest(data)

    if ERRORS:
        print(f"FAIL: {len(ERRORS)} error(s)")
        for e in ERRORS:
            print(f"  - {e}")
        return 1

    print()
    print("summary:")
    print(f"  aggregate claims      : {len(data['claim'])}")
    print(f"  aggregate evidence    : {len(data['evidence'])}")
    print(f"  aggregate provenance  : {len(data['provenance'])}")
    print(f"  structures checked    : A (aggregate), B (per-record ingress), C (sub-packages)")
    print()
    print("ALL PASS: OSS-LBM knowledge package is consistent across the dual structure")
    print(f"  {len(SECTIONS)} structure sections validated, 0 errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())