"""Regression tests for wp-6551-01 (task_type 01-asset-registration).

The tests are offline: they run against the committed artefacts and the stored
source copy under ``runs/wp-6551-01/source_6551.md`` (byte-identical to the
markdown served by GET /api/v1/tensor/reports/6551, sha256 pinned in the contract).
They are written to *falsify* the registration, not merely to execute the script:

* the locator re-resolution test uses the same ``locator_errors`` function the gate
  self-check uses, and a negative control tampers one quote to prove the check
  actually rejects a bad locator (a green suite on a toothless check is worthless);
* the schema tests validate against the repo schemas, so a drifting manifest fails
  here before it reaches the platform gate;
* nothing in the manifest may be marked ``verified`` -- verification is the
  platform gate's decision, never the producer's.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-6551-01"
MANIFEST_PATH = PKG / "asset_manifest.json"
ENVELOPE_PATH = PKG / "kf_result.json"
VERIFICATION_PATH = PKG / "verification.json"
SCHEMA_GENERIC = ROOT / "schemas" / "asset_manifest.v1.generic.schema.json"
SCHEMA_KF = ROOT / "schemas" / "kf_result.v1.schema.json"

CONTRACT_SOURCE_HASH = "sha256:879d4b3cb0112589ae9f58962c23b8d92d07a4de2ea71b950dba6a5d83c47431"
CONTRACT_CHARS = 5491
CONTRACT_TITLE = "IN28-N04 船型阻力闭合：三级证据记账、波阻 GCI 与诚实 FAIL（KCS/5415/Series60）"
CONTRACT_SCENARIO = "IN28-N04-ship-resistance-closure"
RESOLUTIONS = {"resolved_in_source", "referenced_unresolved", "declared_absent"}


def _load_module():
    path = ROOT / "scripts" / "kf_wp6551_register_assets.py"
    spec = importlib.util.spec_from_file_location("kf_wp6551_register_assets", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def reg():
    return _load_module()


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST_PATH.read_text())


@pytest.fixture(scope="module")
def envelope():
    return json.loads(ENVELOPE_PATH.read_text())


@pytest.fixture(scope="module")
def source_md():
    return (ROOT / "runs" / "wp-6551-01" / "source_6551.md").read_text()


# ------------------------------------------------------------------ the source
def test_source_copy_matches_contract(source_md: str) -> None:
    raw = source_md.encode("utf-8")
    assert "sha256:" + hashlib.sha256(raw).hexdigest() == CONTRACT_SOURCE_HASH
    assert len(source_md) == CONTRACT_CHARS


def test_source_copy_is_the_served_markdown(manifest: dict, source_md: str) -> None:
    """The stored copy's bytes are what the manifest hashed (no re-encoding drift)."""
    src = manifest["source"]
    assert "sha256:" + hashlib.sha256(source_md.encode()).hexdigest() == src["source_hash"]
    assert src["bytes_utf8"] == len(source_md.encode()) == len(source_md.encode("utf-8"))
    assert src["hash_match"] and src["chars_match_contract"]


def test_record_identity_matches_contract(manifest: dict) -> None:
    src = manifest["source"]
    assert src["title"] == CONTRACT_TITLE and src["title_matches_contract"]
    assert src["scenario_key"] == CONTRACT_SCENARIO and src["scenario_matches_contract"]


# --------------------------------------------------------------------- schema
def test_manifest_schema_pass(manifest: dict) -> None:
    schema = json.loads(SCHEMA_GENERIC.read_text())
    jsonschema.Draft202012Validator(schema).validate(manifest)


def test_envelope_schema_pass(envelope: dict) -> None:
    schema = json.loads(SCHEMA_KF.read_text())
    jsonschema.Draft202012Validator(schema).validate(envelope)


def test_envelope_outputs_name_the_contract_output(envelope: dict, manifest: dict) -> None:
    assert set(envelope["outputs"]) == {"asset_manifest.json"}
    assert envelope["outputs"]["asset_manifest.json"] == manifest
    assert envelope["provenance"]["source_field"] == "markdown"
    assert envelope["provenance"]["source_hash"] == CONTRACT_SOURCE_HASH
    assert envelope["report_id"] == "6551" and envelope["package_id"] == "wp-6551-01"


# ------------------------------------------------------------------- locators
def test_every_markdown_locator_resolves(reg, manifest: dict, source_md: str) -> None:
    assert reg.locator_errors(source_md, manifest) == []


def test_locator_check_has_teeth(reg, manifest: dict, source_md: str) -> None:
    """Negative control: a one-character change to a quote must be detected."""
    tampered = json.loads(json.dumps(manifest))
    victim = next(a for a in tampered["assets"] if a["locator"]["method"] == "char_span")
    victim["locator"]["quote"] = victim["locator"]["quote"] + "X"
    assert victim["asset_id"] in reg.locator_errors(source_md, tampered)

    tampered2 = json.loads(json.dumps(manifest))
    victim2 = next(a for a in tampered2["assets"] if a["locator"]["method"] == "char_span")
    victim2["locator"]["start_char"] += 1
    assert victim2["asset_id"] in reg.locator_errors(source_md, tampered2)


def test_identity_facts_are_the_document_skeleton(manifest: dict) -> None:
    facts = {f["fact_id"]: f for f in manifest["identity_facts"]}
    assert {f["fact_id"] for f in manifest["identity_facts"]} >= {
        "# title", "## section ①", "## section ⑥", "closing-note"}
    assert facts["## section ⑥"]["quote"].startswith("## ⑥ 误差判定")
    # the closing note is the last non-empty line of the document, i.e. the tail of the
    # final paragraph that opens with **总判**
    lines = (ROOT / "runs" / "wp-6551-01" / "source_6551.md").read_text().rstrip("\n").split("\n")
    assert facts["closing-note"]["locator"]["line"] == max(
        i for i, ln in enumerate(lines, start=1) if ln.strip())
    assert facts["closing-note"]["quote"] == lines[facts["closing-note"]["locator"]["line"] - 1]
    tail = "\n".join(lines[facts["## section ⑥"]["locator"]["line"] - 1:])
    assert "**总判**" in tail


# ------------------------------------------------------------------- manifest
def test_no_duplicate_asset_ids(manifest: dict) -> None:
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert manifest["counts"]["assets"] == len(ids)


def test_resolution_vocabulary_and_counts(manifest: dict) -> None:
    counts = manifest["counts"]
    by_res = {}
    for a in manifest["assets"]:
        assert a["resolution"] in RESOLUTIONS
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    assert counts["by_resolution"] == by_res
    assert counts["resolved_in_source"] == by_res.get("resolved_in_source", 0)
    assert counts["referenced_unresolved"] == by_res.get("referenced_unresolved", 0)
    assert sum(counts["by_class"].values()) == counts["assets"]


def test_every_unresolved_asset_states_why(manifest: dict) -> None:
    for a in manifest["assets"]:
        if a["resolution"] == "referenced_unresolved":
            detail = a["resolution_detail"]
            assert detail.get("reason") or detail.get("http_status") == 404, a["asset_id"]
            assert a["resolution_check"]["result"] == "unresolved"
        else:
            assert a["resolution_check"]["result"] in {"resolved", "present"}


def test_nothing_is_marked_verified(manifest: dict, envelope: dict) -> None:
    """producer must not self-verify: no status/verdict field may say verified."""
    blob = json.dumps({"manifest": manifest, "envelope": envelope}, ensure_ascii=False)
    lowered = blob.lower()
    assert "verified_at_source" not in lowered
    for a in manifest["assets"]:
        assert a.get("status") != "verified"
        assert a.get("verified") is not True
    for c in envelope.get("claims") or []:
        assert c["status"] != "verified"


def test_claims_are_empty_and_explained(manifest: dict, envelope: dict) -> None:
    assert manifest["claims"] == [] and envelope["claims"] == []
    assert len(manifest["claims_empty_reason"]) > 40


def test_single_report_scope(manifest: dict, envelope: dict, source_md: str) -> None:
    """Guard against cross-report bleed: everything registered belongs to 6551."""
    assert manifest["report_id"] == envelope["report_id"] == "6551"
    assert manifest["source"]["uri"] == "tensor://reports/6551"
    others = {r for r in ("6550", "6552", "623", "448", "542") if ("reports/" + r) in source_md}
    assert others == set()
    for a in manifest["assets"]:
        assert "6551" in a["asset_id"]


def test_figures_are_metadata_only(manifest: dict) -> None:
    figs = [a for a in manifest["assets"] if a["asset_class"] == "embedded_figure"]
    assert len(figs) == 4
    assert {f["name"] for f in figs} == set(manifest["source"]["platform_figures"])
    for f in figs:
        assert f["resolution"] == "referenced_unresolved"
        assert f["resolution_detail"]["http_status"] == 404
        assert f["resolution_detail"]["name_resolved_in_markdown"] is True


def test_declared_hash_is_registered_as_truncated(manifest: dict, source_md: str) -> None:
    hashes = [a for a in manifest["assets"] if a["asset_class"] == "declared_hash_reference"]
    assert len(hashes) == 1
    h = hashes[0]
    assert h["resolution_detail"]["algo"] == "sha256"
    assert h["resolution_detail"]["truncated_in_report"] is True
    assert h["resolution_detail"]["declared_hex_chars"] < 64
    assert h["resolution_detail"]["verifiability"] == "unverifiable_truncated_prefix"
    assert h["name"] in source_md


def test_path_references_carry_scope_not_absence(manifest: dict) -> None:
    """Unresolved path references must say *where* they were searched."""
    refs = [a for a in manifest["assets"] if a["asset_id"].startswith("r6551:ref:")]
    assert refs
    for a in refs:
        detail = a["resolution_detail"]
        assert detail["searched_scopes"], a["asset_id"]
        if detail["status"] == "unresolved":
            assert "same_basename_hits_in_worktree" in detail
            assert "not in this worktree" in a["note"] or "TensorLBM" in a["note"]


def test_manifest_identity_fields(manifest: dict) -> None:
    assert manifest["schema"] == "asset_manifest.v1"
    assert manifest["package_id"] == "wp-6551-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["objective"] == {"register_assets": True, "classify_report_type": False,
                                     "extraction_performed": False}


# ---------------------------------------------------------------- self-check
def test_committed_verification_all_ok() -> None:
    v = json.loads(VERIFICATION_PATH.read_text())
    assert v["package_id"] == "wp-6551-01"
    failing = [k for k, c in v["acceptance"].items() if not c["ok"]]
    assert failing == [], failing
    assert set(v["acceptance"]) == {
        "valid_json", "schema_pass", "source_locator_resolvable", "source_hash_matches",
        "no_duplicate_ids", "all_claims_have_evidence_or_explicit_unresolved_status"}
    assert v["not_checked"], "limitations must be stated, not omitted"