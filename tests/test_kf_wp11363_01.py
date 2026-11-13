"""Invariant tests for KF work package wp-11363-01 (asset registration, report 11363).

These tests are offline: they work on the committed snapshot
runs/wp-11363-01/source_11363.md and the committed deliverables. They assert
*invariants* (hash identity, locator resolvability, id uniqueness, claim policy)
and -- for three of them -- that the check actually fails on a tampered input,
so a green run means the check bites rather than "the code ran".
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = "wp-11363-01"
OUT = ROOT / "docs" / "kf" / PKG
MANIFEST = OUT / "asset_manifest.json"
ENVELOPE = OUT / "kf_result.json"
SELFCHECK = OUT / "report_selfcheck.json"
SNAPSHOT = ROOT / "runs" / PKG / "source_11363.md"
CONTRACT_HASH = "sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23"


def _verify_module():
    spec = importlib.util.spec_from_file_location(
        "kf_wp11363_01_verify", ROOT / "scripts" / "kf_wp11363_01_verify.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def artifacts():
    md = SNAPSHOT.read_text(encoding="utf-8")
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    return md, env, man


def test_snapshot_hash_equals_contract_hash(artifacts):
    md, env, man = artifacts
    digest = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_HASH
    assert env["provenance"]["source_hash"] == CONTRACT_HASH
    assert man["source"]["source_hash"] == CONTRACT_HASH
    assert man["source"]["chars"] == 6902 == len(md)


def test_envelope_matches_manifest_and_declares_one_output(artifacts):
    _, env, man = artifacts
    assert env["package_id"] == man["package_id"] == PKG
    assert env["report_id"] == man["report_id"] == "11363"
    assert env["task_type"] == man["task_type"] == "01-asset-registration"
    assert list(env["outputs"]) == ["asset_manifest.json"]
    assert env["outputs"]["asset_manifest.json"] == man


def test_every_char_span_locator_resolves(artifacts):
    md, _, man = artifacts
    spans = [a for a in man["assets"] if a["locator"]["method"] == "char_span"]
    assert len(spans) == man["counts"]["locators"] == man["locators"]["count"]
    for a in spans:
        loc = a["locator"]
        q = loc["quote"]
        assert q and q in md, a["asset_id"]
        assert md[loc["start_char"]:loc["end_char"]] == q, a["asset_id"]
        assert md.count(q) == loc["count_occurrences"], a["asset_id"]
        assert md[:loc["start_char"]].count("\n") + 1 == loc["line"], a["asset_id"]


def test_asset_ids_unique_and_unique_quotes_flagged(artifacts):
    _, _, man = artifacts
    ids = [a["asset_id"] for a in man["assets"]]
    assert len(ids) == len(set(ids)) == man["id_integrity"]["count"]
    assert man["id_integrity"]["duplicate_ids"] == []
    for a in man["assets"]:
        loc = a["locator"]
        if loc["method"] == "char_span" and loc["count_occurrences"] == 1:
            assert loc["unique"] is True, a["asset_id"]


def test_claims_policy_no_extraction_no_verified_marks(artifacts):
    _, env, man = artifacts
    assert man["claims"] == [] and env["claims"] == []
    assert man["claims_empty_reason"]                       # emptiness is explained
    assert man["counts"]["claims"] == 0
    for c in man["claims"] + env["claims"]:
        assert c.get("status") != "verified"
        assert c.get("verified") is not True


def test_figures_declared_in_record_are_all_registered(artifacts):
    _, _, man = artifacts
    figs = [a for a in man["assets"] if a["kind"] == "embedded_figure"]
    assert len(figs) == man["counts"]["figures_declared_in_record"] == 4
    names = {f["name"] for f in figs}
    assert names == {"fig1_per_device_savings.png", "fig2_combined_vs_sum.png",
                     "fig3_selfprop_coupling.png", "fig4_benchmark.png"}
    for f in figs:
        assert f["locator"]["method"] == "char_span"        # figure is quoted in the body
        # never claim a payload without a hash, nor a hash without a payload
        has_hash = bool(f.get("sha256"))
        assert (f["resolution"]["status"] == "resolved_with_bytes") == has_hash
        if has_hash:
            assert f["bytes"] > 0 and f["sha256"].startswith("sha256:")


def test_bundle_line_is_internally_consistent(artifacts):
    """The report says the artefacts directory holds 10 files; the enumerated
    members must add up to 10 (5 named files + '4 张 png' + manifest.json)."""
    md, _, man = artifacts
    bc = man["bundle_consistency"]
    assert bc["declared_in_manifest_line"] == 10
    assert bc["matches"] is True and bc["member_file_count"] == 10
    assert bc["quote"] in md


def test_selfcheck_committed_and_all_green(artifacts):
    md, env, man = artifacts
    mod = _verify_module()
    checks = mod.run_checks(md, env, man, "committed snapshot")
    failed = {k: v for k, v in checks.items() if not v["pass"]}
    assert not failed, failed
    committed = json.loads(SELFCHECK.read_text(encoding="utf-8"))
    assert committed["summary"]["all_pass"] is True


# --------------------------------------------------------------- mutation tests
def test_tampered_quote_is_caught(artifacts):
    md, env, man = artifacts
    mod = _verify_module()
    bad = copy.deepcopy(man)
    victim = next(a for a in bad["assets"] if a["locator"]["method"] == "char_span")
    victim["locator"]["quote"] = victim["locator"]["quote"] + " (hand-typed addition)"
    checks = mod.run_checks(md, env, bad, "mutation: quote altered")
    assert checks["source_locator_resolvable"]["pass"] is False


def test_shifted_offset_is_caught(artifacts):
    md, env, man = artifacts
    mod = _verify_module()
    bad = copy.deepcopy(man)
    victim = next(a for a in bad["assets"] if a["locator"]["method"] == "char_span")
    victim["locator"]["start_char"] += 3
    victim["locator"]["end_char"] += 3
    checks = mod.run_checks(md, env, bad, "mutation: offsets shifted")
    assert checks["source_locator_resolvable"]["pass"] is False


def test_duplicate_id_is_caught(artifacts):
    md, env, man = artifacts
    mod = _verify_module()
    bad = copy.deepcopy(man)
    bad["assets"][1]["asset_id"] = bad["assets"][0]["asset_id"]
    bad["id_integrity"]["count"] = len(bad["assets"])
    checks = mod.run_checks(md, env, bad, "mutation: duplicate asset id")
    assert checks["no_duplicate_ids"]["pass"] is False


def test_wrong_hash_is_caught(artifacts):
    md, env, man = artifacts
    mod = _verify_module()
    bad_env, bad_man = copy.deepcopy(env), copy.deepcopy(man)
    bad_env["provenance"]["source_hash"] = "sha256:" + "0" * 64
    bad_man["source"]["source_hash"] = "sha256:" + "0" * 64
    checks = mod.run_checks(md, bad_env, bad_man, "mutation: hash replaced")
    assert checks["source_hash_matches"]["pass"] is False


def test_foreign_report_id_is_caught(artifacts):
    md, env, man = artifacts
    mod = _verify_module()
    bad_env = copy.deepcopy(env)
    bad_env["report_id"] = "9999"
    checks = mod.run_checks(md, bad_env, man, "mutation: foreign report_id")
    assert checks["constraint_report_id_scope"]["pass"] is False
    # the generic envelope schema only pins ^[0-9]+$, so cross-artifact consistency
    # is what actually catches a foreign id -- asserted here so the gap stays visible
    assert checks["constraint_envelope_manifest_consistency"]["pass"] is False