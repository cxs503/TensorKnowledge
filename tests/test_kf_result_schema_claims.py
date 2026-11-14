"""Regression tests for the kf_result.v1 envelope contract (schema drift guard).

Context: envelope producers added optional fields over time — top-level
``claims`` (94 envelopes in-tree), ``provenance.producer`` (105),
``provenance.notes`` (103), ``provenance.emitted_at`` (104) — while
``schemas/kf_result.v1.schema.json`` kept ``additionalProperties: false`` and
still required ``provenance.source_uri``.  Packages were therefore emitted
correctly and still failed the schema gate (wp-459-01 reported
``schema_pass ✅`` in its own report while ``jsonschema`` rejected the file).

These tests pin the *contract* rather than one package instance:

* the envelope accepts the producer fields the corpus actually uses;
* the schema stays strict — unknown fields, unknown claim fields and a
  provenance with no source locator are still rejected;
* every required key that existed before is still required (no loosening of
  traceability: ``source_field`` + ``source_hash`` remain mandatory, and
  ``source_uri`` or ``notes`` must locate the source).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "kf_result.v1.schema.json"

# required keys as of the pre-drift contract; the fix may only *relax* these
# inside provenance (source_uri -> source_uri|notes), never the root set.
BASELINE_ROOT_REQUIRED = {"package_id", "task_type", "report_id", "provenance", "outputs"}
BASELINE_PROVENANCE_REQUIRED = {"source_uri", "source_field", "source_hash"}

SOURCE_HASH = "sha256:" + "0" * 64


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def validator(schema):
    jsonschema = pytest.importorskip("jsonschema")
    return jsonschema.Draft202012Validator(schema)


def envelope(**overrides) -> dict:
    base = {
        "package_id": "wp-0000-01",
        "task_type": "01-asset-registration",
        "report_id": "000",
        "provenance": {
            "source_uri": "tensor://reports/000",
            "source_field": "markdown",
            "source_hash": SOURCE_HASH,
        },
        "outputs": {"asset_manifest.json": {"package_id": "wp-0000-01"}},
    }
    base.update(overrides)
    return base


def errors_of(validator, document) -> list[str]:
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in validator.iter_errors(document)]


# --------------------------------------------------------------------------
# 1. additive producer fields the corpus already uses are accepted
# --------------------------------------------------------------------------
def test_minimal_envelope_is_valid(validator):
    assert errors_of(validator, envelope()) == []


def test_claims_is_optional_and_may_be_empty(validator):
    assert errors_of(validator, envelope(claims=[])) == []


def test_claims_with_locatable_evidence_are_valid(validator):
    doc = envelope(
        claims=[
            {
                "claim_id": "R1-C1-default-flip",
                "text": "默认 force_scheme 由 guo_sp 改为 trt_split。",
                "status": "supported",
                "evidence": [
                    {"quote": "| 1 | `force_scheme` 默认", "source_field": "markdown", "note": "§4 表 1"}
                ],
            }
        ]
    )
    assert errors_of(validator, doc) == []


def test_claim_may_be_explicitly_unresolved_instead_of_evidenced(validator):
    doc = envelope(claims=[{"claim_id": "C2", "text": "载荷缺失的图无法核验。", "unresolved_reason": "figure payload absent"}])
    assert errors_of(validator, doc) == []


def test_provenance_producer_annotations_are_valid(validator):
    """wp-459-01 records producer + notes instead of a canonical source_uri."""
    doc = envelope(
        provenance={
            "source_field": "markdown",
            "source_hash": SOURCE_HASH,
            "producer": "scripts/kf/register_assets.py",
            "notes": "hash recomputed from GET /tensor/reports/459 markdown",
        }
    )
    assert errors_of(validator, doc) == []


def test_provenance_emitted_at_is_valid(validator):
    doc = envelope(provenance={"source_uri": "tensor://reports/000", "source_field": "markdown", "source_hash": SOURCE_HASH, "emitted_at": "2026-11-01T00:00:00Z"})
    assert errors_of(validator, doc) == []


# --------------------------------------------------------------------------
# 2. strictness is preserved (this is a drift fix, not an escape hatch)
# --------------------------------------------------------------------------
def test_unknown_top_level_property_is_still_rejected(validator):
    assert errors_of(validator, envelope(verified=True))


def test_unknown_provenance_property_is_still_rejected(validator):
    doc = envelope(provenance={"source_uri": "tensor://reports/000", "source_field": "markdown", "source_hash": SOURCE_HASH, "trust_me": 1})
    assert errors_of(validator, doc)


def test_provenance_without_any_source_locator_is_rejected(validator):
    assert errors_of(validator, envelope(provenance={"source_field": "markdown", "source_hash": SOURCE_HASH}))


def test_claim_without_evidence_or_reason_is_rejected(validator):
    assert errors_of(validator, envelope(claims=[{"claim_id": "C1", "text": "无证据的主张。"}]))


def test_claim_evidence_requires_a_quote(validator):
    doc = envelope(claims=[{"claim_id": "C1", "text": "x", "evidence": [{"source_field": "markdown"}]}])
    assert errors_of(validator, doc)


def test_empty_claim_id_is_rejected(validator):
    assert errors_of(validator, envelope(claims=[{"claim_id": "", "text": "x", "unresolved_reason": "missing"}]))


def test_required_keys_are_not_loosened(schema):
    assert set(schema["required"]) == BASELINE_ROOT_REQUIRED
    prov = schema["properties"]["provenance"]
    assert set(prov["required"]) <= BASELINE_PROVENANCE_REQUIRED
    assert prov["required"] == ["source_field", "source_hash"]
    # the dropped key must still be enforced through the anyOf locator rule
    locator = [alt for alt in prov["anyOf"] if "source_uri" in alt.get("required", [])]
    assert locator, "source_uri must remain mandatory unless notes carries the route"
    assert [alt for alt in prov["anyOf"] if "notes" in alt.get("required", [])]


def test_additional_properties_stay_closed(schema):
    assert schema["additionalProperties"] is False
    assert schema["properties"]["provenance"]["additionalProperties"] is False
    assert schema["properties"]["outputs"]["additionalProperties"] is False
    assert schema["$defs"]["claim"]["additionalProperties"] is False
    assert schema["$defs"]["claim_evidence"]["additionalProperties"] is False


# --------------------------------------------------------------------------
# 3. the in-tree envelopes that motivated the fix now validate
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "relpath",
    [
        "docs/kf/wp-459-01/kf_result.json",   # 01 工序，claims 合法为空 + producer/notes
        "docs/kf/wp-7473-04/kf_result.json",  # 04 工序，带证据的 claims + emitted_at
    ],
)
def test_in_tree_envelope_validates(validator, relpath):
    document = json.loads((ROOT / relpath).read_text(encoding="utf-8"))
    assert errors_of(validator, document) == []


def test_wp459_01_envelope_declares_its_producer(validator):
    document = json.loads((ROOT / "docs/kf/wp-459-01/kf_result.json").read_text(encoding="utf-8"))
    assert document["claims"] == []
    assert document["provenance"]["producer"] == "scripts/kf/register_assets.py"
    assert document["provenance"]["source_hash"].startswith("sha256:")


# --------------------------------------------------------------------------
# 4. the drift scanner itself (scripts/kf/schema_conformance_scan.py)
# --------------------------------------------------------------------------
def _write(path: Path, payload) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def test_scan_reports_additive_only_migration(tmp_path):
    sys_path = ROOT / "scripts" / "kf"
    import sys

    if str(sys_path) not in sys.path:
        sys.path.insert(0, str(sys_path))
    import schema_conformance_scan as scanmod

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    baseline = json.loads(json.dumps(schema))
    # rebuild the pre-fix strictness: no claims, no producer annotations, source_uri mandatory
    baseline["properties"].pop("claims")
    prov = baseline["properties"]["provenance"]
    prov.pop("anyOf")
    prov["required"] = ["source_uri", "source_field", "source_hash"]
    for key in ("producer", "notes", "emitted_at"):
        prov["properties"].pop(key)

    workspace = tmp_path / "repo"
    _write(workspace / "docs/kf/a/kf_result.json", envelope())  # valid before and after
    _write(workspace / "docs/kf/b/kf_result.json", envelope(
        claims=[{"claim_id": "C1", "text": "x", "unresolved_reason": "missing payload"}],
        provenance={"source_field": "markdown", "source_hash": SOURCE_HASH, "producer": "p", "notes": "GET /tensor/reports/1"},
    ))  # invalid before, valid after
    _write(workspace / "docs/kf/c/asset_manifest.json", {"package_id": "wp-c-01", "assets": []})  # not an envelope

    baseline_path = _write(tmp_path / "baseline.json", baseline)
    schema_path = _write(tmp_path / "current.json", schema)

    before = scanmod.scan(baseline_path, workspace, ["docs/kf"])
    after = scanmod.scan(schema_path, workspace, ["docs/kf"])

    assert before["envelopes_scanned"] == 2
    assert before["envelopes_valid"] == 1
    assert after["envelopes_valid"] == 2
    assert set(before["valid_paths"]) <= set(after["valid_paths"]), "schema change must be additive-only"
    assert after["skipped_not_envelope"] == 1


def test_committed_conformance_artifact_is_consistent_with_schema():
    """The checked-in scan must not claim more valid envelopes than the schema does."""
    jsonschema = pytest.importorskip("jsonschema")
    artifact = ROOT / "docs" / "kf" / "wp-459-01" / "schema_conformance.json"
    report = json.loads(artifact.read_text(encoding="utf-8"))
    assert report["delta"]["additive_only"] is True
    assert report["delta"]["regressions"] == []
    assert report["current"]["envelopes_valid"] >= report["baseline"]["envelopes_valid"]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    document = json.loads((ROOT / "docs/kf/wp-459-01/kf_result.json").read_text(encoding="utf-8"))
    assert list(validator.iter_errors(document)) == []