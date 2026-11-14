#!/usr/bin/env python3
"""Tests for wp-12028-01 asset manifest (report_id=12028).

Two families:
  * positive: the delivered artifacts satisfy the contract acceptance items;
  * negative controls: each check provably FAILS on a tampered input — an
    acceptance check that cannot fail proves nothing.

Runs fully offline from the single pinned snapshot
work/wp-12028-01/source/report_12028.json (record + markdown + figure fingerprints).
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "kf"))

import kf12028_checks as kc  # noqa: E402

PKG = "wp-12028-01"
REPORT_ID = "12028"
CONTRACT_HASH = "sha256:69846e9d0680b8a1c5db5c607b9a5bf4a0ba2e6103b1d193a6a5d5e83e0ec29f"
CONTRACT_CHARS = 8377

SRC = ROOT / "work/wp-12028-01/source"
ENV_PATH = ROOT / "docs/kf/wp-12028-01/kf_result.json"
MAN_PATH = ROOT / "docs/kf/wp-12028-01/asset_manifest.json"
SCHEMA_PATH = ROOT / "schemas/kf_result.v1.schema.json"


@pytest.fixture(scope="module")
def env() -> dict:
    return json.loads(ENV_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def man() -> dict:
    return json.loads(MAN_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rec() -> dict:
    return json.loads((SRC / "report_12028.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def md(rec) -> str:
    return rec["markdown"]


# --------------------------------------------------------------------------
# positive checks
# --------------------------------------------------------------------------
def test_envelope_validates_against_schema(env):
    jsonschema.validate(env, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def test_envelope_declares_the_contract_scope(env, man):
    assert env["package_id"] == PKG
    assert env["task_type"] == "01-asset-registration"
    assert env["report_id"] == REPORT_ID
    assert "asset_manifest.json" in env["outputs"]
    assert man["scope"]["reports_touched"] == [REPORT_ID]
    assert man["scope"]["extracts_claims"] is False
    assert man["scope"]["classifies_report_type"] is False


def test_source_hash_and_chars_match_contract(md, env, man):
    assert kc.sha256_of_text(md) == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS
    h = kc.hash_report(md, env, man)
    assert h["matches_provenance"] and h["matches_manifest"]
    # the committed snapshot must carry exactly those bytes in its markdown field
    snap = json.loads((SRC / "report_12028.json").read_text(encoding="utf-8"))
    raw = snap["markdown"].encode("utf-8")
    assert "sha256:" + hashlib.sha256(raw).hexdigest() == CONTRACT_HASH


def test_every_locator_and_observation_evidence_resolves(man, md, rec):
    assert kc.locator_failures(man, md, rec) == []


def test_asset_ids_unique_and_patterned(man):
    ids = [a["asset_id"] for a in man["assets"]]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"ast-%s-\d{2}" % REPORT_ID, i) for i in ids)
    assert kc.duplicate_report(man, {"claims": []})["all_unique"]


def test_claims_stay_out_of_the_envelope_and_no_verified_flag(man, env):
    # the current schema forbids extra top-level keys, so the empty-claims contract
    # is recorded in the manifest instead of the envelope
    assert "claims" not in env
    assert "claims.json" not in (env["outputs"] or {})
    assert man["claims_policy"]["claims"] == []
    assert man["claims_policy"]["reason"]
    inv = kc.structural_invariants(man)
    assert kc.all_pass(inv), inv


def test_counts_agree_with_asset_list(man):
    counts = man["asset_counts"]
    assert counts["assets_total"] == len(man["assets"])
    assert counts["resolved"] + counts["unresolved"] == counts["assets_total"]
    assert sum(counts["by_kind"].values()) == counts["assets_total"]


def test_unresolved_assets_are_external_code_artefacts_with_reasons(man):
    unresolved = [a for a in man["assets"] if a["status"] == "unresolved"]
    assert unresolved, "expected the code/test/script artefacts to stay unresolved"
    assert {a["kind"] for a in unresolved} == {"code_module", "test_file", "script_file"}
    assert all(a["unresolved_reason"] for a in unresolved)


def test_figure_payloads_are_registered_with_hashes(man):
    figs = [a for a in man["assets"] if a["kind"] == "figure_reference"]
    assert len(figs) == 4
    for a in figs:
        rb = a["resolved_bytes"]
        assert rb["http_status"] == 200 and rb["bytes"] > 0
        assert rb["content_type"] == "image/png"
        assert re.fullmatch(r"sha256:[0-9a-f]{64}", rb["sha256"])
        assert rb["width_px"] > 0 and rb["height_px"] > 0
        assert a["resolvable"] is True and a["status"] == "resolved"


def test_figure_fingerprints_match_the_snapshot(man, rec):
    """The manifest's figure fingerprints must equal the ones pinned in the snapshot
    (the online runner re-checks them against the live platform store)."""
    assert kc.figure_fingerprint_defects(man, rec["figure_fingerprints"]) == []
    for a in man["assets"]:
        if a["kind"] == "figure_reference":
            assert a["resolved_bytes"]["sha256"].startswith("sha256:")
            assert a["resolved_bytes"]["width_px"] > 0


def test_every_observation_carries_resolvable_evidence(man, md):
    for obs in man["observations"]:
        assert obs["evidence"], obs["id"]
        for loc in obs["evidence"]:
            assert md[loc["char_start"]:loc["char_end"]] == loc["quote"]


# --------------------------------------------------------------------------
# negative controls — each check must be able to fail
# --------------------------------------------------------------------------
def test_negative_tampered_quote_is_detected(man, md, rec):
    bad = copy.deepcopy(man)
    loc = bad["assets"][5]["locators"][0]
    loc["quote"] = loc["quote"] + " (paraphrased)"
    assert kc.locator_failures(bad, md, rec), "tampered quote went undetected"


def test_negative_shifted_offset_is_detected(man, md, rec):
    bad = copy.deepcopy(man)
    bad["assets"][5]["locators"][0]["char_start"] += 1
    assert kc.locator_failures(bad, md, rec)


def test_negative_invented_quote_is_detected(man, md, rec):
    bad = copy.deepcopy(man)
    bad["assets"][5]["locators"][0] = {
        "source_uri": "tensor://reports/12028", "source_field": "markdown",
        "char_start": 0, "char_end": 5, "quote": "flap-jet optimizer",
    }
    assert kc.locator_failures(bad, md, rec)


def test_negative_fabricated_record_value_is_detected(man, md, rec):
    bad = copy.deepcopy(man)
    record_asset = next(a for a in bad["assets"] if a["kind"] == "record_metadata")
    title_loc = next(loc for loc in record_asset["locators"] if loc.get("field") == "title")
    title_loc["value"] = "some other title"
    assert kc.locator_failures(bad, md, rec)


def test_negative_duplicate_asset_id_is_detected(man):
    bad = copy.deepcopy(man)
    bad["assets"][3]["asset_id"] = bad["assets"][2]["asset_id"]
    assert kc.duplicate_report(bad, {"claims": []})["all_unique"] is False


def test_negative_modified_markdown_breaks_hash(md, env, man):
    h = kc.hash_report(md + " ", env, man)
    assert h["matches_provenance"] is False and h["matches_manifest"] is False


def test_negative_claim_without_evidence_is_flagged():
    assert kc.claim_defects([{"claim_id": "c1", "text": "unbacked"}])
    assert kc.claim_defects(
        [{"claim_id": "c2", "text": "t", "status": "supported"}]) == []


def test_negative_worker_set_verified_status_is_rejected():
    defects = kc.claim_defects([{"claim_id": "c1", "text": "t", "status": "verified"}])
    assert any(d["why"].startswith("worker must not") for d in defects)


def test_negative_verified_flag_in_manifest_is_detected(man):
    bad = copy.deepcopy(man)
    bad["assets"][1]["verified"] = True
    inv = kc.structural_invariants(bad)
    assert inv["no_truthy_verified_flag"] is False
    assert kc.all_pass(inv) is False


def test_negative_missing_unresolved_reason_is_detected(man):
    bad = copy.deepcopy(man)
    for a in bad["assets"]:
        if a["status"] == "unresolved":
            a.pop("unresolved_reason", None)
            break
    assert kc.structural_invariants(bad)["unresolved_have_reason"] is False


def test_negative_wrong_count_table_is_detected(man):
    bad = copy.deepcopy(man)
    bad["asset_counts"]["resolved"] += 1
    assert kc.structural_invariants(bad)["resolved_count_matches"] is False


def test_negative_scope_escalation_is_detected(man):
    bad = copy.deepcopy(man)
    bad["scope"]["extracts_claims"] = True
    assert kc.structural_invariants(bad)["scope_no_claim_extraction"] is False

def test_negative_tampered_figure_sha_is_detected(man, rec):
    bad = copy.deepcopy(man)
    fig = next(a for a in bad["assets"] if a["kind"] == "figure_reference")
    fig["resolved_bytes"]["sha256"] = "sha256:" + "0" * 64
    assert kc.figure_fingerprint_defects(bad, rec["figure_fingerprints"]), "tampered figure sha undetected"
