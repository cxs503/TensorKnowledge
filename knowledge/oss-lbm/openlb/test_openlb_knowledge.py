#!/usr/bin/env python3
"""Pytest validator for the openLB OSS knowledge package (knowledge/oss-lbm/openlb/).

Checks
------
1.  File presence and JSON parseability
2.  ID patterns (tkc/tke/tkp:oss-lbm:openlb-*) and uniqueness
3.  Bidirectional claim<->evidence cross-references
4.  Count constraint (>=8 claims)
5.  Epistemic discipline: status enums, all evidence unassessed (no self-approval)
6.  Required fields per record
7.  Every claim carries the GAP-LBM-INDUSTRIAL-ENG anchor in its notes
8.  Every locator is a code-location with a verbatim quote of <=3 lines
9.  Anti-fabrication: each quote line must appear VERBATIM at the cited
    file:line in the openLB source cache (skipped if the cache is absent)

Run:  pytest knowledge/oss-lbm/openlb/test_openlb_knowledge.py -v
"""
import json
import re
from pathlib import Path

import pytest

HERE = Path(__file__).parent
CACHE = Path("/root/openlb")
SHORT_COMMIT = "6c3934d"

CLAIM_PATTERN = re.compile(r"^tkc:oss-lbm:openlb-[a-z0-9-]+$")
EVIDENCE_PATTERN = re.compile(r"^tke:oss-lbm:openlb-[a-z0-9-]+$")
PROVENANCE_PATTERN = re.compile(r"^tkp:oss-lbm:openlb-[a-z0-9-]+$")
LOCATOR_PATTERN = re.compile(
    r"^openlb@" + SHORT_COMMIT + r" (\S+):(\d+)(?:-(\d+))?$"
)

EPISTEMIC_ENUM = {
    "established", "well-supported", "provisional", "contested",
    "speculative", "superseded", "not-assessed",
}
ASSESSMENT_ENUM = {
    "unassessed", "reviewed-supports", "reviewed-refutes",
    "reviewed-qualifies", "insufficient", "disputed",
}
GAP_ANCHOR = "GAP-LBM-INDUSTRIAL-ENG"


def _load(name: str):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def claims():
    return _load("claims/claims.json")


@pytest.fixture(scope="module")
def evidence():
    return _load("evidence/evidence.json")


@pytest.fixture(scope="module")
def provenance():
    return _load("provenance/provenance.json")


# ------------------------------------------------------------- structure ----

def test_files_exist():
    for rel in ("claims/claims.json", "evidence/evidence.json",
                "provenance/provenance.json", "README.md"):
        assert (HERE / rel).is_file(), f"missing {rel}"


def test_counts(claims, evidence, provenance):
    assert len(claims) >= 8, f"need >=8 claims, got {len(claims)}"
    assert len(evidence) == len(claims), "one evidence record per claim expected"
    assert len(provenance) >= 1


def test_id_patterns(claims, evidence, provenance):
    for c in claims:
        assert CLAIM_PATTERN.match(c["id"]), c["id"]
    for e in evidence:
        assert EVIDENCE_PATTERN.match(e["id"]), e["id"]
    for p in provenance:
        assert PROVENANCE_PATTERN.match(p["id"]), p["id"]


def test_unique_ids(claims, evidence, provenance):
    assert len({c["id"] for c in claims}) == len(claims)
    assert len({e["id"] for e in evidence}) == len(evidence)
    assert len({p["id"] for p in provenance}) == len(provenance)


def test_cross_references(claims, evidence):
    claim_ids = {c["id"] for c in claims}
    evidence_ids = {e["id"] for e in evidence}
    for c in claims:
        assert c.get("evidence_refs"), f"{c['id']} has no evidence_refs"
        for ref in c["evidence_refs"]:
            assert ref in evidence_ids, f"{c['id']} -> missing {ref}"
    for e in evidence:
        assert e.get("claim_refs"), f"{e['id']} has no claim_refs"
        for ref in e["claim_refs"]:
            assert ref in claim_ids, f"{e['id']} -> missing {ref}"


# ------------------------------------------------------- epistemic discipline

def test_epistemic_status(claims):
    for c in claims:
        assert c["epistemic_status"] in EPISTEMIC_ENUM, c["id"]
        # conservative rule: 'established' requires validation-surface evidence;
        # this package is source-inspection-only, so 'established' is forbidden
        assert c["epistemic_status"] != "established", (
            f"{c['id']}: 'established' requires validation-surface evidence; "
            "source-inspection claims must stay well-supported/provisional"
        )


def test_no_self_approval(evidence):
    for e in evidence:
        assert e["assessment_status"] == "unassessed", (
            f"{e['id']}: assessment_status must stay 'unassessed' (draft, no self-approval)"
        )


def test_required_fields(claims, evidence, provenance):
    for c in claims:
        for f in ("id", "statement", "claim_type", "epistemic_status",
                  "created_at", "version", "notes"):
            assert f in c, f"{c.get('id', '?')} missing {f}"
        assert c["notes"], f"{c['id']} missing notes"
    for e in evidence:
        for f in ("id", "source", "relation", "locator", "captured_at",
                  "assessment_status", "version"):
            assert f in e, f"{e.get('id', '?')} missing {f}"
    for p in provenance:
        for f in ("id", "generated_entity", "activity", "agents",
                  "recorded_at", "version"):
            assert f in p, f"{p.get('id', '?')} missing {f}"


# ------------------------------------------------------------- schema -------

def test_schema_conformance(claims, evidence, provenance):
    """Per-record conformance against schemas/ (Draft 2020-12).

    The repo convention is per-record validation: the record schemas describe a
    single object, while the package files are lists of records (same as the
    sibling pylbm/lettuce/lbmpy/XLB package).
    """
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        pytest.skip("jsonschema not installed")
    schemas_dir = HERE.parent.parent.parent / "schemas"
    pairs = [
        (claims, "claim-record.schema.json"),
        (evidence, "evidence-record.schema.json"),
        (provenance, "provenance-record.schema.json"),
    ]
    for records, schema_name in pairs:
        schema = json.loads((schemas_dir / schema_name).read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        for rec in records:
            errs = sorted(validator.iter_errors(rec), key=lambda e: list(e.path))
            assert not errs, (
                f"{rec.get('id', '?')} violates {schema_name}: "
                + "; ".join(e.message[:120] for e in errs[:3])
            )


# ------------------------------------------------------------- GAP anchors ---

def test_gap_anchor_on_every_claim(claims):
    for c in claims:
        joined = " ".join(c["notes"])
        assert GAP_ANCHOR in joined, (
            f"{c['id']} missing {GAP_ANCHOR} anchor in notes"
        )


def test_gpl_boundary_explicit(claims):
    """The GPL-2 contagion judgment must be explicit in the license claim."""
    lic = [c for c in claims if c["id"] == "tkc:oss-lbm:openlb-gpl2-reference-only"]
    assert lic, "license claim missing"
    joined = " ".join(lic[0]["notes"]) + " " + lic[0]["statement"]
    assert "reference-only" in joined.lower(), (
        "GPL-2 contagion must be explicitly judged as a reference-only boundary"
    )


# --------------------------------------------------------------- locators ----

def test_locators_and_quotes(claims, evidence):
    for e in evidence:
        loc = e["locator"]
        assert loc["locator_type"] == "code-location", e["id"]
        m = LOCATOR_PATTERN.match(loc["value"])
        assert m, f"{e['id']}: bad locator value {loc['value']!r}"
        quote = loc["quote"]
        assert quote, f"{e['id']}: empty quote"
        lines = quote.split("\n")
        assert len(lines) <= 3, f"{e['id']}: quote has {len(lines)} lines (>3)"
        assert all(ln.strip() for ln in lines), f"{e['id']}: blank line in quote"


def test_quotes_verbatim_in_cache(evidence):
    """Anti-fabrication gate: every quote line must match the cache byte-for-byte."""
    if not CACHE.is_dir():
        pytest.skip(f"openLB cache {CACHE} not present on this host")
    for e in evidence:
        loc = e["locator"]
        m = LOCATOR_PATTERN.match(loc["value"])
        rel, a, b = m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))
        path = CACHE / rel
        assert path.is_file(), f"{e['id']}: {rel} not in cache"
        file_lines = path.read_text(encoding="utf-8").splitlines()
        assert b <= len(file_lines), f"{e['id']}: line {b} out of range in {rel}"
        cited = file_lines[a - 1:b]
        quoted = loc["quote"].split("\n")
        assert quoted == cited, (
            f"{e['id']}: quote does not match {rel}:{a}-{b} verbatim\n"
            f"  cited : {quoted!r}\n  actual: {cited!r}"
        )


def test_provenance_links_full_commit(provenance):
    """Provenance must carry the FULL commit hash plus the cache path."""
    for p in provenance:
        desc = p["activity"]["description"]
        assert "6c3934dea66e4c3cad66049f579e00b93effc256" in desc, (
            "provenance must record the full commit hash"
        )
        assert "/root/openlb" in desc, "provenance must record the cache path"
        assert p["generated_entity"]["id"] == "knowledge/oss-lbm/openlb"
