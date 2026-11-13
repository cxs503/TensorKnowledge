"""Tests for the KBM knowledge-governance layer (KBM-TKC-GOV-SCALE).

Every test is synthetic (fixtures built in-memory, no network, no DB) except the
opt-in pilot check at the bottom, which validates the *published* artifacts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ke import gov  # noqa: E402

RUN_AT = "2026-11-12T02:30:00Z"


@pytest.fixture(scope="module")
def cfg():
    return gov.load_config()


@pytest.fixture(scope="module")
def registry(cfg):
    return gov.EntityRegistry(cfg)


def _report(rid: int, text: str) -> dict:
    return {"report_id": rid, "title": f"r{rid}", "text": text,
            "sha256": gov.sha256_text(text), "producer": "platform/tensor_reports"}


def _kos(cfg, *reports):
    out = []
    for rep in reports:
        out.extend(gov.build_kos(rep, registry_of(cfg), cfg)["kos"])
    return out


_REGISTRY_CACHE: dict[int, gov.EntityRegistry] = {}


def registry_of(cfg) -> gov.EntityRegistry:
    key = id(cfg)
    if key not in _REGISTRY_CACHE:
        _REGISTRY_CACHE[key] = gov.EntityRegistry(cfg)
    return _REGISTRY_CACHE[key]


# ---------------------------------------------------------------------------
# Entity Resolution v1
# ---------------------------------------------------------------------------
def test_alias_collapse_and_qualifier_split(registry):
    for alias in ("Cd", "CD", "C_D", "drag coefficient", "阻力系数"):
        r = registry.resolve(alias)
        assert r["entity_id"] == "ent:cd" and r["confidence"] == 1.0, alias
    r = registry.resolve("Cd_ref")
    assert r["entity_id"] == "ent:cd" and r["qualifier"] == "ref" and r["confidence"] == 0.9
    assert registry.resolve("Qx_unregistered")["entity_id"] is None


def test_unresolved_candidate_is_discarded_with_reason(cfg):
    built = gov.build_kos(_report(1, "Frobnicator = 12.5 and Cd = 1.0"), registry_of(cfg), cfg)
    reasons = [d["reason"] for d in built["discarded"]]
    assert "entity_unresolved" in reasons
    assert [k["entity"] for k in built["kos"]] == ["Cd"]


def test_operator_expression_is_not_a_measurement(cfg):
    """"Cd = 24/Re" is Stokes' formula, not an observation; it must be dropped."""
    built = gov.build_kos(_report(2, "For creeping flow Cd = 24/Re holds."), registry_of(cfg), cfg)
    assert built["kos"] == []
    assert any(d["reason"] == "value_is_expression" for d in built["discarded"])


# ---------------------------------------------------------------------------
# Zero hand-copying: provenance relocation
# ---------------------------------------------------------------------------
def test_relocation_detects_tampered_source(cfg):
    text = "Results: Cd = 1.234 at Re = 100."
    built = gov.build_kos(_report(3, text), registry_of(cfg), cfg)
    ko = built["kos"][0]
    assert ko["verification"]["relocated"] is True
    span = ko["source"]["span"]
    tampered = text[:span[0]] + "Cd = 9.999" + text[span[1]:]
    check = gov.relocate(tampered, {"span": span, "needle": ko["source"]["needle"],
                                    "value_literal": str(ko["value"]), "value": ko["value"]})
    assert check["relocated"] is False and check["needle_match"] is False


# ---------------------------------------------------------------------------
# Dedup: two layers
# ---------------------------------------------------------------------------
def test_dedup_exact_layer(cfg):
    kos = _kos(cfg, _report(10, "Cd = 1.12198 was obtained."),
               _report(11, "Cd = 1.12198 was obtained."))
    d = gov.dedupe(kos, cfg)
    assert d["n_ko"] == 2 and d["n_clusters"] == 1 and d["duplicate_rate"] == 0.5
    assert d["clusters"][0]["layers"] == ["exact"]
    assert d["clusters"][0]["source_reports"] == [10, 11]


def test_dedup_semantic_layer_catches_reworded_duplicate(cfg):
    """Same claim, reworded (same language) -> merged by the semantic layer."""
    kos = _kos(cfg, _report(12, "error=20.5% was reported for the case."),
               _report(13, "for the case, error = 20.5% was measured"))
    d = gov.dedupe(kos, cfg)
    assert d["n_clusters"] == 1
    assert d["clusters"][0]["layers"] == ["semantic_wording"]


def test_cross_language_rewording_is_a_known_non_merge(cfg):
    """Known limitation (registered as a W2 gap): a translation is not merged.

    The semantic layer compares *surface* wording; it has no translation model,
    so knowledge repeated in another language survives dedupe.  Silence would be
    worse than the gap, hence this explicit test.
    """
    kos = _kos(cfg, _report(12, "error = 20.5% was reported for the case."),
               _report(13, "误差 = 20.5% 为该算例结果。"))
    assert gov.dedupe(kos, cfg)["n_clusters"] == 2


def test_dedup_does_not_merge_different_values(cfg):
    kos = _kos(cfg, _report(14, "Cd = 1.10 was obtained."), _report(15, "Cd = 1.35 was obtained."))
    d = gov.dedupe(kos, cfg)
    assert d["n_clusters"] == 2 and d["duplicate_rate"] == 0.0


def test_dedup_requires_conditions_or_wording_for_unstated_conditions(cfg):
    """Same subject+value with *unrelated* wording and no conditions: not a duplicate."""
    kos = _kos(cfg, _report(16, "Cd = 2.5 for the upstream probe."),
               _report(17, "Altogether different text mentions nothing alike, Cd = 2.5."))
    d = gov.dedupe(kos, cfg)
    assert d["n_clusters"] == 2


# ---------------------------------------------------------------------------
# Cross-validation / contradiction detection
# ---------------------------------------------------------------------------
def test_crossval_supported_needs_numeric_conditions(cfg):
    kos = _kos(cfg, _report(20, "Re = 100, sphere case, Cd = 1.10."),
               _report(21, "Re = 100, sphere case, Cd = 1.12."))
    cv = gov.cross_validate(kos, cfg)
    assert cv["n_pairs"] == 1 and cv["pairs"][0]["verdict"] == "agree"
    assert cv["group_verdicts"]["supported"] == 1


def test_crossval_unstated_conditions_is_insufficient(cfg):
    kos = _kos(cfg, _report(22, "Cd = 1.10 for the case."), _report(23, "Cd = 1.12 for the case."))
    cv = gov.cross_validate(kos, cfg)
    assert cv["pairs"][0]["verdict"] == "agree"
    assert cv["group_verdicts"] == {"supported": 0, "contradicted": 0,
                                    "insufficient-evidence": 1}


def test_contradiction_detected_on_identical_conditions(cfg):
    kos = _kos(cfg, _report(24, "Re = 100, sphere case, Cd = 1.00."),
               _report(25, "Re = 100, sphere case, Cd = 1.60."))
    cv = gov.cross_validate(kos, cfg)
    assert cv["n_contradiction_pairs"] == 1
    c = cv["contradictions"][0]
    assert c["status"] == "contradicted" and c["rel_diff"] > 0.15
    assert sorted(c["reports"]) == [24, 25] and c["next_action"] == "replicate"
    assert cv["group_verdicts"]["contradicted"] == 1


def test_different_conditions_are_incomparable_not_contradicted(cfg):
    kos = _kos(cfg, _report(26, "Re = 100, sphere case, Cd = 1.00."),
               _report(27, "Re = 1000, sphere case, Cd = 1.60."))
    cv = gov.cross_validate(kos, cfg)
    assert cv["pairs"][0]["verdict"] == "incomparable_conditions"
    assert cv["n_contradiction_pairs"] == 0


def test_different_geometry_is_incomparable(cfg):
    kos = _kos(cfg, _report(28, "Re = 100, cylinder case, Cd = 1.35."),
               _report(29, "Re = 100, sphere case, Cd = 0.40."))
    cv = gov.cross_validate(kos, cfg)
    assert cv["pairs"][0]["verdict"] == "incomparable_conditions"


def test_document_local_entity_excluded_from_cross_source(cfg):
    kos = _kos(cfg, _report(30, "error = 1.5% overall."), _report(31, "error = 9.0% overall."))
    cv = gov.cross_validate(kos, cfg)
    assert cv["n_pairs"] == 0 and cv["document_local_subjects"] == ["err||%"]
    assert cv["group_verdicts"]["contradicted"] == 0


def test_intra_report_pairs_are_not_cross_validated(cfg):
    kos = _kos(cfg, _report(32, "Re = 100, sphere case, Cd = 1.00. Later Cd = 1.60."))
    cv = gov.cross_validate(kos, cfg)
    assert cv["n_pairs"] == 0


# ---------------------------------------------------------------------------
# Review pool + state machine write-back
# ---------------------------------------------------------------------------
def _review(cfg, kos, *, mutate=None):
    pool = gov.ReviewPool(cfg)
    consistency = {ko["id"]: {"status": "not_compared"} for ko in kos}
    results = []
    for ko in kos:
        if mutate:
            mutate(ko)
        results.append(pool.review(ko, {"consistency": consistency}, run_at=RUN_AT))
    folded = gov.fold_reviews([r["event"] for r in results],
                              {ko["id"]: ko for ko in kos}, run_at=RUN_AT)
    return pool, results, folded


def test_review_pass_writes_approved_state(cfg):
    kos = _kos(cfg, _report(40, "Re = 100, sphere case, Cd = 1.10."))
    _, results, folded = _review(cfg, kos)
    assert results[0]["verdict"] == "pass"
    assert folded["status"][kos[0]["id"]] == "approved"
    assert folded["writeback"][kos[0]["id"]]["last_code"] == "OK_APPROVED"


def test_review_needs_fix_and_fail_map_to_state_machine(cfg):
    kos = _kos(cfg, _report(41, "Cd_ref = 1.10 for the case."),   # qualifier unverified
               _report(42, "Cd = 1.10 for the case."))
    _, results, folded = _review(cfg, kos)
    verdicts = [r["verdict"] for r in results]
    assert verdicts[0] == "needs-fix" and folded["status"][kos[0]["id"]] == "draft"

    bad = [dict(k) for k in kos[1:2]]
    bad[0]["verification"] = {**bad[0]["verification"], "relocated": False}
    _, _, folded2 = _review(cfg, bad)
    assert folded2["status"][bad[0]["id"]] == "rejected"


def test_no_self_approval_is_refused_and_recorded(cfg):
    kos = _kos(cfg, _report(43, "Re = 100, sphere case, Cd = 1.10."))
    pool = gov.ReviewPool(cfg)
    res = pool.review(kos[0], {"consistency": {kos[0]["id"]: {"status": "not_compared"}}},
                      run_at=RUN_AT)
    reviewer_id = res["event"]["reviewer"]["id"]
    # make the producer identical to the signing reviewer -> approve must fail closed
    kos[0]["producer_ids"] = [reviewer_id]
    folded = gov.fold_reviews([res["event"]], {kos[0]["id"]: kos[0]}, run_at=RUN_AT)
    assert folded["refused"] and folded["refused"][0]["code"] in (
        "SELF_APPROVAL_BLOCKED", "INDEPENDENCE_UNRESOLVABLE")
    assert kos[0]["id"] not in folded["status"]  # no state change without a valid event


def test_pool_capacity_deferral_is_counted(cfg):
    kos = _kos(cfg, _report(44, "Re = 100, sphere case, Cd = 1.10."))
    tight = json.loads(json.dumps(cfg))
    for r in tight["review_pool"]["reviewers"]:
        r["capacity"] = 0
    pool = gov.ReviewPool(tight)
    res = pool.review(kos[0], {"consistency": {kos[0]["id"]: {"status": "not_compared"}}},
                      run_at=RUN_AT)
    assert res["assignment"]["deferred_lanes"] and res["votes"] == []
    assert res["decision"] == "request-changes"


def test_ledger_hash_chain_detects_tampering(cfg):
    kos = _kos(cfg, _report(45, "Re = 100, sphere case, Cd = 1.10."))
    _, results, folded = _review(cfg, kos)
    lines = gov.chain_ledger(folded["events"])
    assert gov.verify_chain(lines)["ok"] is True
    lines[0]["event"]["decision"] = "reject"
    assert gov.verify_chain(lines)["ok"] is False


# ---------------------------------------------------------------------------
# Counting口径
# ---------------------------------------------------------------------------
def test_unknown_bucket_is_rejected():
    c = gov.Counting()
    with pytest.raises(gov.BucketViolation):
        c.metric("dup", 0.1, "B9_made_up", formula="x")


def test_bucket_reconciliation_rejects_inconsistent_counts():
    c = gov.Counting()
    c.set("quantity_statements", 10)
    c.set("discarded", 3)
    c.set("context_candidates", 1)
    c.set("ko_extracted", 5)          # 3 + 1 + 5 = 9 != 10 -> must raise
    c.set("ko_pending_review", 5)
    c.set("review_pass", 3)
    c.set("review_needs_fix", 1)
    c.set("review_fail", 1)
    c.set("dedup_clusters", 4)
    c.set("duplicate_members", 1)
    c.set("governed_objects", 2)
    c.set("pass_duplicate_members", 1)
    with pytest.raises(gov.BucketViolation):
        c.reconcile()


def test_end_to_end_is_deterministic_and_invariants_hold(cfg):
    reports = [
        _report(50, "# Results\nRe = 100, sphere case\nCd = 1.10\nCd = 1.10\n"),
        _report(51, "# Results\nRe = 100, sphere case\nCd = 1.60\n"),
        _report(52, "# Results\nFoobar = 3.5\nCd = 1.10\n"),
    ]
    a = gov.run_governance(reports, cfg, run_at=RUN_AT)
    b = gov.run_governance(reports, cfg, run_at=RUN_AT)
    strip = lambda r: json.dumps({k: v for k, v in r["stats"].items()}, sort_keys=True)
    assert strip(a) == strip(b)
    assert all(a["invariants"].values())
    assert a["stats"]["counts"]["governed_objects"] <= a["stats"]["counts"]["review_pass"]
    # the injected 60% divergence on identical conditions is caught
    assert a["stats"]["metrics"]["contradiction_pairs"]["value"] >= 1


# ---------------------------------------------------------------------------
# Published pilot artifacts (opt-in: generated by scripts/kbm_gov_w1.py run)
# ---------------------------------------------------------------------------
PILOT = REPO / "runs" / "kbm-gov-w1"


@pytest.mark.skipif(not (PILOT / "stats.json").is_file(), reason="pilot artifacts not generated")
def test_pilot_artifacts_reconcile():
    stats = json.loads((PILOT / "stats.json").read_text(encoding="utf-8"))
    c = stats["counts"]
    assert all(stats["invariants"].values())
    assert c["ko_pending_review"] == c["review_pass"] + c["review_needs_fix"] + c["review_fail"]
    assert c["review_pass"] == c["governed_objects"] + c["pass_duplicate_members"]
    for name, m in stats["metrics"].items():
        assert "bucket" in m and "formula" in m, name
    assert stats["metrics"]["duplicate_rate"]["bucket"] == "derived:B1_ko_pending_review"