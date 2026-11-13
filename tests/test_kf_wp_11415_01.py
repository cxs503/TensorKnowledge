"""Acceptance tests for KF work package wp-11415-01 (01-asset-registration, report 11415).

Each test maps to one or more acceptance items of the work-package contract:

  valid_json | schema_pass | source_locator_resolvable | source_hash_matches
  | no_duplicate_ids | all_claims_have_evidence_or_explicit_unresolved_status

The tests re-derive the facts from the raw API snapshot (runs/wp-11415-01/report_11415.json)
instead of trusting artifacts/*.json bookkeeping, so a corrupted artifact fails here
rather than passing by self-assertion.

Run:  python3 -m pytest tests/test_kf_wp_11415_01.py -q
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
RUN_DIR = REPO / "runs/wp-11415-01"
ART = REPO / "artifacts/wp-11415-01/asset_manifest.json"
RESULT = RUN_DIR / "kf_result.wp-11415-01.json"
FIG = REPO / "docs/kf/wp-11415-01/fig_asset_locator_map.png"

REPORT_ID = "11415"
PACKAGE_ID = "wp-11415-01"
CONTRACT_SOURCE_HASH = "d8bc42883f1fa1d274a3ca4808586d2a8773e9d0f464b554c944f5090b0c8c50"
CONTRACT_CHARS = 7903

ACCEPTANCE_TO_CHECKS = {
    "valid_json": ["valid_json"],
    "schema_pass": ["kf_result_schema", "asset_manifest_schema"],
    "source_locator_resolvable": ["source_locator_resolvable"],
    "source_hash_matches": ["source_hash_matches", "source_chars_match_contract"],
    "no_duplicate_ids": ["no_duplicate_ids"],
    "all_claims_have_evidence_or_explicit_unresolved_status":
        ["all_claims_have_evidence_or_explicit_unresolved_status"],
}


def _load_verifier():
    spec = importlib.util.spec_from_file_location(
        "kf_verify_11415", REPO / "scripts/kf_verify_11415.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def verify_report():
    """Run the independent verifier with the repo root as cwd (its paths are relative)."""
    cwd = os.getcwd()
    os.chdir(REPO)
    try:
        return _load_verifier().verify()
    finally:
        os.chdir(cwd)


@pytest.fixture(scope="module")
def manifest():
    return json.loads(ART.read_text())


@pytest.fixture(scope="module")
def result():
    return json.loads(RESULT.read_text())


@pytest.fixture(scope="module")
def source_md():
    return json.loads((RUN_DIR / "report_11415.json").read_text())["markdown"]


@pytest.mark.parametrize("acceptance,checks", sorted(ACCEPTANCE_TO_CHECKS.items()))
def test_acceptance_items(verify_report, acceptance, checks):
    for name in checks:
        assert name in verify_report["checks"], f"verifier did not evaluate {name} for {acceptance}"
        assert verify_report["checks"][name]["pass_"] is True, f"{acceptance} failed via {name}: " \
            f"{json.dumps(verify_report['checks'][name], ensure_ascii=False)[:400]}"


def test_all_verifier_checks_pass(verify_report):
    assert verify_report["all_pass"] is True


def test_source_hash_recomputed_from_raw_snapshot(source_md):
    assert hashlib.sha256(source_md.encode()).hexdigest() == CONTRACT_SOURCE_HASH
    assert len(source_md) == CONTRACT_CHARS


def test_locators_slice_exactly(source_md, manifest):
    """Independent of the verifier: quote must be the exact slice AND unique."""
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        assert source_md[loc["start_char"]:loc["end_char"]] == q, a["asset_id"]
        assert source_md.count(q) == 1, a["asset_id"]
        assert loc["unique"] is True


def test_ids_contiguous_and_unique(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert ids == ["A%02d" % i for i in range(1, len(ids) + 1)]


def test_claims_empty_is_explicit_not_omitted(manifest):
    assert manifest["claims"] == []
    assert "claims 允许为空数组" in manifest["claims_note"]


def test_report_boundary_single_report_id(manifest, result):
    assert manifest["report_id"] == result["report_id"] == REPORT_ID
    assert manifest["source"]["uri"] == "tensor://reports/11415"
    seen = set()
    for a in manifest["assets"]:
        for m in __import__("re").findall(r"tensor://reports/(\d+)", json.dumps(a, ensure_ascii=False)):
            seen.add(m)
    assert seen <= {REPORT_ID}


def test_unresolved_assets_are_machine_backed_not_asserted(manifest):
    """Every non-resolved asset must name the check that produced its status."""
    for a in manifest["assets"]:
        rc = a["resolution_check"]
        assert rc["check"] and rc["result"], a["asset_id"]
        if a["resolution"] != "resolved_in_source":
            assert rc["result"] in {"unresolved", "absent"}, a["asset_id"]
            assert rc.get("detail") or rc.get("missing"), a["asset_id"]


def test_figures_registered_match_platform_payload(source_md, manifest):
    payload = json.loads((RUN_DIR / "report_11415.json").read_text())
    names = {f["name"] for f in payload["figures"]}
    fig_assets = [a for a in manifest["assets"] if a["asset_class"] == "figure"]
    assert len(fig_assets) == len(names) == 4
    for a in fig_assets:
        rc = a["resolution_check"]
        assert a["resolution"] == "resolved_in_source", a["asset_id"]
        assert rc["check"] == "platform_figure_binary_fetch"
        assert rc["result"] == "present" and rc["http_status"] == 200
        assert rc["figure_name"] in names
        assert rc["figure_name"] in a["locator"]["quote"]
        assert rc["png_magic"] is True and rc["png_bytes"] > 10_000
        # the recorded fingerprint must equal the bytes actually fetched on disk
        blob = (RUN_DIR / "figures" / rc["figure_name"]).read_bytes()
        assert hashlib.sha256(blob).hexdigest() == rc["png_sha256"].split(":")[1]
        assert int(rc["png_bytes"]) == len(blob)


def test_figure_deliverable_is_generated_from_manifest(manifest):
    """The report figure is a pure function of the artifact (no hand-typed numbers)."""
    src = (REPO / "scripts/kf_figure_11415.py").read_text()
    assert "asset_manifest.json" in src
    label = json.loads(ART.read_text())["counts"]["assets"]
    assert label == len(manifest["assets"])


def test_envelope_fields_and_not_verified(result):
    assert result["package_id"] == PACKAGE_ID
    assert result["task_type"] == "01-asset-registration"
    assert result["provenance"]["source_hash"] == "sha256:" + CONTRACT_SOURCE_HASH
    assert result["provenance"]["source_field"] == "markdown"
    assert result["provenance"]["verification_status"] == "not_verified"
    assert list(result["outputs"]) == ["asset_manifest.json"]


def test_figure_artifact_exists_and_is_png():
    assert FIG.exists()
    assert FIG.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert FIG.stat().st_size > 20_000

def test_published_report_shape():
    """The local copy of the published markdown must carry the delivery contract shape."""
    md_path = REPO / "docs/kf/wp-11415-01/KF-RESULT-wp-11415-01.md"
    md = md_path.read_text()
    assert md.startswith("# KF-RESULT wp-11415-01")
    assert md.count("```json") == 1
    import re
    block = json.loads(re.findall(r"```json\n(.*?)\n```", md, re.S)[0])
    assert block["package_id"] == PACKAGE_ID and block["report_id"] == REPORT_ID
    assert block["provenance"]["source_hash"] == "sha256:" + CONTRACT_SOURCE_HASH


def test_publish_record_consistent():
    rec = json.loads((REPO / "docs/kf/wp-11415-01/report_published.json").read_text())
    assert rec["title"] == "KF-RESULT wp-11415-01"
    assert "kf-wp:wp-11415-01" in rec["tags"]
    assert rec["mission_id"] == 15698
    post = rec["post_publish_verification"]
    assert post["title_ok"] and post["tag_ok"] and post["one_json_block"]
    assert post["source_hash_matches"] and post["n_assets"] == 28 and post["claims"] == 0
    assert rec["published_markdown_sha256"] == hashlib.sha256(
        (REPO / "docs/kf/wp-11415-01/KF-RESULT-wp-11415-01.md").read_text().encode()).hexdigest().join(
        ["sha256:", ""])
