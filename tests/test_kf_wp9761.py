#!/usr/bin/env python3
"""Regression guard for work package wp-9761-01 (report 9761 asset registration).

Two kinds of assertions:
  A. the acceptance items of the contract hold on the committed artifacts;
  B. negative controls — each verifier check is shown to have teeth by feeding it a
     deliberately corrupted copy and asserting it *fails*.  Without B a green run only
     proves the code executed (see skill: tests must assert invariants).

Run: python3 -m pytest tests/test_kf_wp9761.py -q
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import kf_verify_9761 as V  # noqa: E402  (path-dependent import by design)


def _load(name: str):
    """Load a package artifact, tolerating the repo push gate.

    The push gate drops artifacts/** and runs/**, so a fresh clone only has the durable
    copies under docs/wp-9761-01/ (plus whatever the API can serve). Prefer the working
    artifact, fall back to the durable mirror, and skip with an explicit reason rather
    than failing ambiguously when neither exists.
    """
    primary, fallback = ARTIFACTS[name]
    for p in (primary, fallback):
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    pytest.skip("%s unavailable (looked for %s and %s) — run the repro_cmd first"
                % (name, primary, fallback))


def _load_markdown() -> str:
    for p in ARTIFACTS["markdown"]:
        if p.exists():
            return p.read_text(encoding="utf-8")
    try:
        md, _ = V.fetch_report()
    except Exception as exc:                      # pragma: no cover - offline
        pytest.skip("source markdown unavailable locally and API fetch failed: %s" % exc)
    return md


ARTIFACTS = {
    "manifest": (ROOT / "artifacts/wp-9761-01/asset_manifest.json",
                 ROOT / "docs/wp-9761-01/asset_manifest.json"),
    "result": (ROOT / "runs/wp-9761-01/kf_result.wp-9761-01.json",
               ROOT / "docs/wp-9761-01/kf_result_block.json"),
    "verification": (ROOT / "artifacts/wp-9761-01/verification.json",
                     ROOT / "docs/wp-9761-01/verification.json"),
    "payload": (ROOT / "runs/wp-9761-01/report_9761.json",
                ROOT / "docs/wp-9761-01/report_9761_meta.json"),
    "markdown": (ROOT / "runs/wp-9761-01/report_9761.md",),
}

MANIFEST = _load("manifest")
RESULT = _load("result")
MD = _load_markdown()
PAYLOAD = _load("payload")


# ---------------------------------------------------------------- A. acceptance
def test_source_hash_matches_contract_and_local_copy():
    h = hashlib.sha256(MD.encode()).hexdigest()
    assert h == V.EXPECTED_HASH
    assert MANIFEST["source"]["hash"] == h
    assert RESULT["provenance"]["source_hash"] == "sha256:" + h
    assert len(MD) == 8931
    assert MANIFEST["source"]["chars"] == len(MD)


def test_every_locator_resolves_in_source_markdown():
    assert V.check_locators(MD, MANIFEST) == []


def test_no_duplicate_asset_ids_and_observation_targets_exist():
    assert V.check_duplicate_ids(MANIFEST) == []
    have = {a["asset_id"] for a in MANIFEST["assets"]}
    assert {o["evidence_asset"] for o in MANIFEST["observations"]} <= have


def test_claims_are_empty_and_allowed():
    assert MANIFEST["claims"] == []
    assert RESULT["claims"] == []
    assert V.check_claims([]) == []
    assert MANIFEST["claims_note"]


def test_resolution_vocabulary_is_consistent():
    for a in MANIFEST["assets"]:
        assert a["resolution_check"]["result"] == V.RESOLUTION_TO_CHECK[a["resolution"]]
        assert a["locator"]["unique"] is True
        assert a["locator"]["occurrences"] == 1


def test_no_asset_is_marked_verified():
    blob = json.dumps({"m": MANIFEST, "r": RESULT}, ensure_ascii=False)
    assert '"status": "verified"' not in blob
    assert RESULT["provenance"]["verification_status"] == "not_verified"


def test_counts_are_recomputed_not_asserted():
    by_res = {}
    for a in MANIFEST["assets"]:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    assert MANIFEST["counts"]["assets"] == len(MANIFEST["assets"])
    assert MANIFEST["counts"]["by_resolution"] == by_res
    assert MANIFEST["counts"]["unique_quotes"] == len(MANIFEST["assets"])


def test_report_scope_is_9761_only():
    assert MANIFEST["report_id"] == RESULT["report_id"] == "9761"
    assert RESULT["package_id"] == "wp-9761-01"
    assert RESULT["task_type"] == "01-asset-registration"
    assert MANIFEST["source"]["uri"] == "tensor://reports/9761"


def test_result_envelope_matches_platform_schema():
    import jsonschema
    schema = json.loads((ROOT / "schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(RESULT, schema)
    assert set(RESULT) == {"package_id", "task_type", "report_id", "provenance", "outputs", "claims"}


def test_platform_metadata_agrees_with_report():
    assert PAYLOAD["id"] == 9761
    assert PAYLOAD["scenario_key"] == "rigid_contact_energy_ledger_certification"
    assert len(PAYLOAD["figures"]) == 5
    assert [f["name"] for f in PAYLOAD["figures"]] == [
        "fig1_three_conventions.png", "fig2_force_power_checkpoint.png",
        "fig3_restitution.png", "fig4_m5404_verdict.png", "fig5_newton_cradle.png"]
    # observations must record the title drift instead of silently "fixing" it
    o1 = [o for o in MANIFEST["observations"] if o["id"] == "O1"][0]
    assert o1["detail"]["platform_title"] != o1["detail"]["markdown_heading"]


def test_external_artifacts_are_honestly_unresolved():
    """The TensordDEM-side files must not be claimed as present in this worktree."""
    ext = [a for a in MANIFEST["assets"] if a["resolution"] == "referenced_unresolved"]
    assert {a["asset_id"] for a in ext} == {"A10", "A19", "A25"}
    for a in ext:
        assert a["resolution_check"]["result"] == "unresolved"
        for p in a["resolution_check"].get("worktree_hits", []):
            assert not (ROOT / p).exists()


# ------------------------------------------------------- B. negative controls
def _corrupt_quote(m: dict) -> dict:
    m = copy.deepcopy(m)
    m["assets"][3]["locator"]["quote"] = m["assets"][3]["locator"]["quote"] + "☒"
    return m


def _duplicate_id(m: dict) -> dict:
    m = copy.deepcopy(m)
    m["assets"][5]["asset_id"] = m["assets"][4]["asset_id"]
    return m


def test_negative_control_locator_detects_a_one_character_tamper():
    assert V.check_locators(MD, _corrupt_quote(MANIFEST)) != []


def test_negative_control_duplicate_ids_are_detected():
    assert V.check_duplicate_ids(_duplicate_id(MANIFEST)) != []


def test_negative_control_dangling_observation_target_is_detected():
    m = copy.deepcopy(MANIFEST)
    m["observations"][0]["evidence_asset"] = "A99"
    assert V.check_duplicate_ids(m) == ["A99"]


def test_negative_control_uniqueness_flag_is_load_bearing():
    m = copy.deepcopy(MANIFEST)
    short = MD.index("1e-9")
    m["assets"][0]["locator"] = dict(m["assets"][0]["locator"], start_char=short,
                                     end_char=short + 4, quote="1e-9", unique=False)
    defects = [r for _, r in V.check_locators(MD, m)]
    assert "quote_not_unique:%d" % MD.count("1e-9") in defects
    assert "unique_flag_false" in defects


def test_negative_control_claim_without_evidence_is_flagged():
    assert V.check_claims([{"claim_id": "c1", "text": "no evidence attached"}]) == ["c1"]
    assert V.check_claims([{"claim_id": "c2", "text": "x", "status": "unresolved"}]) == []
    assert V.check_claims([{"claim_id": "c3", "text": "x",
                            "evidence": [{"quote": "q"}]}]) == []


def test_negative_control_wrong_hash_is_rejected():
    tampered = MD.replace("5.111e-07", "5.112e-07", 1)
    assert hashlib.sha256(tampered.encode()).hexdigest() != V.EXPECTED_HASH
    # and the locator set must notice as well (the quote no longer re-resolves)
    assert V.check_locators(tampered, MANIFEST) != []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))