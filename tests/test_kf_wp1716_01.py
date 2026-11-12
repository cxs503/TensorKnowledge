"""Acceptance tests for KF work package wp-1716-01 (01-asset-registration).

These tests re-derive every acceptance criterion of the package contract from the
committed artifacts, without network access:

  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status

They also pin the two properties that make the registration trustworthy rather
than merely well-formed:
  * byte-stability — regenerating from the snapshot reproduces the manifest byte
    for byte, so a reviewer can replay the registration;
  * honesty — nothing is marked verified, no claim is invented, and every
    unresolved asset carries an explicit reason code instead of being silently
    reported as "present".
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "kf" / "wp-1716-01"
MANIFEST = OUT / "asset_manifest.json"
SNAPSHOT = OUT / "source_report_1716.md"
CHECKS = OUT / "checks.json"
SCRIPT = REPO / "scripts" / "kf_wp1716_01_asset_manifest.py"

CONTRACT_HASH = (
    "sha256:79cd7a448000f110435f121ee33ed9909bc3989cc6ac1046b16c0203e3936a8b"
)
CONTRACT_CHARS = 4159


def _load_script():
    spec = importlib.util.spec_from_file_location("kf_wp1716_01", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def manifest():
    assert MANIFEST.exists(), f"missing deliverable {MANIFEST}"
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def markdown():
    return SNAPSHOT.read_text(encoding="utf-8")


# --------------------------------------------------------------- structure --
def test_manifest_is_valid_json():
    json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_schema_required_fields(manifest):
    for key in ("schema_version", "package_id", "task_type", "report_id",
                "source", "channel_probes", "assets", "claims",
                "verification_policy", "scope_notes"):
        assert key in manifest, f"missing top-level key {key}"
    assert manifest["package_id"] == "wp-1716-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == "1716"


# ---------------------------------------------------------------- identity --
def test_source_hash_matches_contract_and_snapshot(manifest, markdown):
    h = manifest["source"]["hash"]
    assert h["value"] == CONTRACT_HASH
    assert h["contract_value"] == CONTRACT_HASH
    assert h["recomputed_in_run"] is True and h["matches_contract"] is True
    live = "sha256:" + hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    assert live == CONTRACT_HASH == manifest["source"]["snapshot"]["hash"]


def test_source_size(manifest, markdown):
    assert manifest["source"]["size"]["chars"] == CONTRACT_CHARS == len(markdown)
    assert manifest["source"]["size"]["bytes"] == len(markdown.encode("utf-8"))


def test_title_and_scenario_key_match_contract(manifest):
    facts = manifest["source"]["report_facts"]
    assert facts["title_matches_contract"] is True
    assert facts["scenario_key"] == "platform_gsa_sobol_verification"
    assert facts["scenario_key_matches_contract"] is True


# ---------------------------------------------------------------- locators --
def test_every_locator_resolves_verbatim(manifest, markdown):
    for a in manifest["assets"]:
        loc = a["locator"]
        assert loc["field"] == "markdown"
        s, e, q = loc["char_start"], loc["char_end"], loc["quote"]
        assert isinstance(s, int) and isinstance(e, int) and 0 <= s < e <= len(markdown)
        assert markdown[s:e] == q, f"{a['asset_id']} slice != quote"
        assert q in markdown, f"{a['asset_id']} quote not present in source"


def test_every_occurrence_resolves_verbatim(manifest, markdown):
    for a in manifest["assets"]:
        for occ in a.get("occurrences", []) or []:
            assert markdown[occ["char_start"]:occ["char_end"]] == occ["quote"]


def test_no_duplicate_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert len(manifest["assets"]) == manifest["unresolved_summary"]["n_assets"]


def test_assets_cover_the_four_declared_kinds(manifest):
    kinds = {a["kind"] for a in manifest["assets"]}
    assert {"report_markdown", "figure", "referenced_artifact_path",
            "git_ref"} <= kinds
    figs = {a["declared_metadata"]["name"]
            for a in manifest["assets"] if a["kind"] == "figure"}
    assert figs == {"gsa_convergence.png", "gsa_estimates_vs_analytic.png",
                    "gsa_lindqvist_ice.png"}


# ----------------------------------------------------------------- honesty --
def test_claims_have_evidence_or_unresolved_status(manifest):
    claims = manifest["claims"]
    assert isinstance(claims, list)
    for c in claims:
        assert c.get("evidence_locator") or c.get("status") == "unresolved"


def test_no_claims_invented(manifest):
    # contract allows an empty array; registration must not fabricate extraction
    assert manifest["claims"] == []
    assert manifest["verification_policy"]["claims_marked_verified"] == 0


def test_nothing_is_marked_verified(manifest):
    blob = json.dumps(manifest, ensure_ascii=False)
    assert not re.search(r'"status"\s*:\s*"verified"', blob)
    assert "verified_by_platform" not in blob
    assert all(a["status"] in {"registered", "declared_not_fetched"}
               for a in manifest["assets"])


def test_unresolved_assets_carry_reason_codes(manifest):
    for a in manifest["assets"]:
        if a["status"] == "registered":
            assert a["resolution"]["bytes_obtained"] is True
            continue
        assert a["resolution"]["bytes_obtained"] is False
        reason = a["resolution"]["unresolved_reason"]
        assert reason["code"] and reason["detail"]


def test_figure_payloads_are_recorded_as_404_not_as_present(manifest):
    probes = {p["path"]: p["http_status"] for p in manifest["channel_probes"]}
    for a in manifest["assets"]:
        if a["kind"] != "figure":
            continue
        path = f"/tensor/reports/1716/figures/{a['declared_metadata']['name']}"
        assert probes[path] == 404
        assert a["hash"] is None and a["size"] is None


def test_scope_is_single_report(manifest):
    ids = {manifest["report_id"]}
    ids |= {a["declared_uri"].split("#")[0] for a in manifest["assets"]}
    assert ids == {"1716", "tensor://reports/1716"}


# ------------------------------------------------------------ reproducibility --
def test_regeneration_is_byte_stable():
    before = MANIFEST.read_bytes()
    mod = _load_script()
    mod.build(offline=True)
    after = MANIFEST.read_bytes()
    assert before == after, "offline rebuild changed the manifest bytes"


def test_committed_checks_all_pass(manifest, markdown):
    mod = _load_script()
    result = mod.run_checks(manifest, markdown)
    assert result["all_ok"], result["failed"]
    assert CHECKS.exists()
    assert json.loads(CHECKS.read_text(encoding="utf-8"))["all_ok"] is True