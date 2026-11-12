"""Work package wp-5406-01 (01-asset-registration) — invariants of the manifest.

The tests assert *properties*, not that the script ran: every locator must
resolve verbatim against the source bytes of report 5406, no path may be
resolved from a longer path it is a suffix of, a directory reference may never
be reported as a reachable byte, and the record-field locator of the figure must
have teeth (a drifted record must fail the check).

The source record is the in-repo snapshot taken from
``GET /tensor/reports/5406`` (hash pinned both here and in the package
contract), so the suite runs offline.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "wp5406_asset_manifest.py"
SNAPSHOT = REPO_ROOT / "knowledge" / "assets" / "wp-5406-01" / "report_record.json"

CONTRACT_HASH = ("sha256:9c071693614c9bed438bea6aa35956a5f00e1790eb5d48ae48086cc"
                 "2732ede8a")


def _load_script():
    spec = importlib.util.spec_from_file_location("wp5406_asset_manifest", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_script()


@pytest.fixture(scope="module")
def record():
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest(mod, record):
    return mod.build_manifest(record, REPO_ROOT, SNAPSHOT.parent / "source_snapshot.md")


# ---------------------------------------------------------------------------
# source identity
# ---------------------------------------------------------------------------
def test_snapshot_is_report_5406_and_hash_matches_contract(record, manifest):
    assert str(record["id"]) == "5406"
    computed = "sha256:" + hashlib.sha256(record["markdown"].encode("utf-8")).hexdigest()
    assert computed == CONTRACT_HASH
    assert manifest["source"]["computed_source_hash"] == CONTRACT_HASH
    assert manifest["source"]["hash_match"] is True
    assert manifest["source"]["chars"] == 3815
    assert manifest["source"]["record_meta"]["scenario_key"] == "tensordem_ci_clearance"


# ---------------------------------------------------------------------------
# locators
# ---------------------------------------------------------------------------
def test_every_text_locator_resolves_verbatim(manifest, record):
    md = record["markdown"]
    n_text = 0
    for asset in manifest["attachments"]:
        for loc in asset["mentions"]:
            n_text += 1
            assert md[loc["start_offset"]:loc["end_offset"]] == loc["quote"]
            assert loc["content_hash"] == "sha256:" + hashlib.sha256(
                loc["quote"].encode("utf-8")).hexdigest()
            assert loc["line"] == md.count("\n", 0, loc["start_offset"]) + 1
    assert n_text >= 15  # the report cites more than a dozen path tokens


def test_a_longer_path_does_not_resolve_its_own_suffix(mod):
    """`provenance_gate_matrix.png` must not yield a locator for `gate_matrix.png`."""
    md = "产物：`provenance_gate_matrix.png`、`gate_evidence.json`。\n"
    paths = {a["path"] for a in mod.discover_paths(md)}
    assert "provenance_gate_matrix.png" in paths
    assert "gate_evidence.json" in paths
    assert "gate_matrix.png" not in paths
    at = mod._bounded(md, "gate_matrix.png", 0, len(md))
    assert at == -1


def test_figure_is_registered_from_the_record_field_not_from_text(manifest):
    figs = [a for a in manifest["attachments"] if a["kind"] == "report_figure"]
    assert [f["path"] for f in figs] == ["gate_matrix.png"]
    fig = figs[0]
    assert fig["mentions"] == []  # the body never spells the filename
    assert fig["locator"]["locator_type"] == "record_field"
    assert fig["locator"]["field"] == "figures[0].name"
    assert fig["reachability"]["status"] == "declared_metadata_only"
    assert fig["bytes_available"] is False


# ---------------------------------------------------------------------------
# reachability honesty
# ---------------------------------------------------------------------------
def test_directory_reference_is_never_reported_as_a_reachable_byte(manifest):
    by_path = {a["path"]: a for a in manifest["attachments"]}
    for name in ("artifacts", "docs", "src", "artifacts/m4829_ci_gate"):
        assert by_path[name]["directory_reference"] is True
        assert by_path[name]["reachability"]["status"] == "unresolved_referenced_directory"
        assert by_path[name]["bytes_available"] is False


def test_bare_filename_is_bound_to_the_directory_cited_on_the_same_line(manifest):
    by_path = {a["path"]: a for a in manifest["attachments"]}
    for name in ("gate_evidence.json", "provenance_gate_matrix.png",
                 "ledger_regeneration.png"):
        assert by_path[name]["member_of"] == "artifacts/m4829_ci_gate"
        assert by_path[name]["reachability"]["status"] == "unresolved_bare_filename"
    # ...and the report says those three are exactly what the artifacts dir holds
    assert by_path["gate_evidence.json"]["same_asset_as"] == (
        "artifacts/m4829_ci_gate/gate_evidence.json")


def test_no_asset_is_claimed_as_retrieved(manifest):
    assert manifest["counts"]["with_bytes_available"] == 0
    for asset in manifest["attachments"]:
        assert asset["reachability"]["detail"], asset["id"]
        assert asset["reachability"]["checked"], asset["id"]


def test_ids_are_unique_and_namespaced(manifest):
    ids = [a["id"] for a in manifest["attachments"]]
    assert len(ids) == len(set(ids))
    assert all(i.startswith("asset:5406:") for i in ids)


# ---------------------------------------------------------------------------
# the checks have teeth
# ---------------------------------------------------------------------------
def test_checks_pass_on_the_real_record(mod, record, manifest):
    checks = mod.run_checks(manifest, record["markdown"], record)
    failed = [c["name"] for c in checks if not c["pass"]]
    assert failed == []


def test_drifted_record_figure_field_fails_the_locator_check(mod, record, manifest):
    tampered = json.loads(json.dumps(record))
    tampered["figures"][0]["name"] = "gate_matrix_v2.png"
    checks = {c["name"]: c for c in mod.run_checks(manifest, record["markdown"], tampered)}
    assert checks["source_locator_resolvable"]["pass"] is False


def test_drifted_offsets_fail_the_locator_check(mod, record, manifest):
    tampered = json.loads(json.dumps(manifest))
    tampered["attachments"][0]["mentions"][0]["start_offset"] += 1
    checks = {c["name"]: c for c in mod.run_checks(tampered, record["markdown"], record)}
    assert checks["source_locator_resolvable"]["pass"] is False


def test_drifted_hash_fails_the_hash_check(mod, record, manifest):
    tampered = json.loads(json.dumps(manifest))
    tampered["source"]["computed_source_hash"] = "sha256:" + "0" * 64
    tampered["source"]["hash_match"] = False
    checks = {c["name"]: c for c in mod.run_checks(tampered, record["markdown"], record)}
    assert checks["source_hash_matches"]["pass"] is False


# ---------------------------------------------------------------------------
# scope discipline
# ---------------------------------------------------------------------------
def test_no_claims_and_no_self_verification(manifest):
    assert manifest["claims"]["extracted"] == 0
    assert len(manifest["claims"]["reason"]) >= 20
    assert manifest["verification"]["status"] == "not_marked_verified"


def test_refuses_another_report_id(mod, record, tmp_path):
    other = dict(record, id="5407")
    p = tmp_path / "rec.json"
    p.write_text(json.dumps(other), encoding="utf-8")
    assert mod.main(["--offline-from", str(p), "--out", str(tmp_path / "m.json")]) == 5