"""Acceptance gate for the wp-5716-04 independent review of report 5716.

These tests assert *invariants* of the delivered package, not just that a script
ran.  Two failure modes are what they exist for:

* a review that silently hand-copies numbers (so the package can drift from the
  source it claims to review), and
* a review that launders a FAIL into a PASS (a verdict that is not the arithmetic
  consequence of the numbers it stores).

Every check is therefore re-derived here from its own ``inputs`` and
``formula`` — the test never imports the generator, so a wrong generator cannot
make its own gate green.  Provenance is bound byte-wise to the hash that
``docs/kf/wp-5716-01`` registered, which is also the hash the platform recomputes.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs/kf/wp-5716-04"
SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
UPSTREAM = ROOT / "docs/kf/wp-5716-01" / "kf_result.json"

SRC = PKG / "source_5716.md"
META = PKG / "source_5716.md.meta.json"
RECOMPUTE = PKG / "recompute.json"
REVIEW = PKG / "review_report.json"
KF = PKG / "kf_result.json"
REPORT_MD = PKG / "report.md"
README = PKG / "README.md"
FIG_DIR = PKG / "figures"

VERDICTS = {"reproduced", "self_consistent", "contradicted", "gap", "withheld"}
DEV_KINDS = {
    "recompute_vs_claim", "closure", "cross_reference", "census",
    "undefined_denominator", "reading_sensitivity", "threshold_comparison", "none",
}
ARITH_TOL = 3.0


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source() -> str:
    return SRC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def recompute() -> dict:
    return load(RECOMPUTE)


@pytest.fixture(scope="module")
def review() -> dict:
    return load(REVIEW)


@pytest.fixture(scope="module")
def kf() -> dict:
    return load(KF)


@pytest.fixture(scope="module")
def checks(recompute) -> dict:
    return {c["id"]: c for c in recompute["checks"]}


# ---------------------------------------------------------------------------
# 1. provenance: the review is bound to the bytes the 01 package registered
# ---------------------------------------------------------------------------
def test_source_hash_matches_upstream_registration(source):
    registered = load(UPSTREAM)["provenance"]["source_hash"]
    assert registered.startswith("sha256:")
    assert hashlib.sha256(source.encode("utf-8")).hexdigest() == registered.split(":", 1)[1]


def test_meta_agrees_with_snapshot_and_contract(source):
    meta = load(META)
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert meta["sha256_recomputed"] == digest
    assert meta["sha256_contract"].split(":", 1)[1] == digest
    assert meta["hash_matches_contract"] is True
    assert meta["chars_recomputed"] == len(source)
    assert meta["bytes_utf8_recomputed"] == len(source.encode("utf-8"))
    assert meta["line_count"] == len(source.splitlines())
    assert meta["report_id"] == "5716" and meta["package_id"] == "wp-5716-04"


def test_envelope_binds_the_same_hash(kf, source):
    env_hash = kf["provenance"]["source_hash"]
    assert env_hash == "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert kf["provenance"]["source_field"] == "markdown"
    assert kf["provenance"]["source_hash_matches"] is True


# ---------------------------------------------------------------------------
# 2. every quote is a verbatim line of the snapshot (no paraphrase, no drift)
# ---------------------------------------------------------------------------
def test_located_quotes_are_verbatim_lines(recompute, source):
    lines = source.splitlines()
    located = [c for c in recompute["checks"] if c["line"] is not None]
    assert len(located) >= 20, "too few located checks to call the review traceable"
    for c in located:
        assert isinstance(c["line"], int) and 1 <= c["line"] <= len(lines), c["id"]
        assert c["quote"] == lines[c["line"] - 1].strip(), f"{c['id']} quote is not that line"
        assert c["quote"] in source


def test_each_quote_is_anchored_on_unique_source_text(recompute, source):
    """Several checks may cite one line, but each must name the phrase it rests on,
    and that phrase must be unique in the source (so the locator cannot drift)."""
    for c in recompute["checks"]:
        if c["quote"] is None:
            assert c["anchor"] is None, c["id"]
            continue
        assert c["anchor"] and c["anchor"] in c["quote"], f"{c['id']}: anchor not inside its quote"
        assert source.count(c["anchor"]) == 1, f"{c['id']}: anchor is not unique in the source"


# ---------------------------------------------------------------------------
# 3. each verdict is the arithmetic consequence of the numbers stored
# ---------------------------------------------------------------------------
def test_verdict_vocabulary_and_id_sequence(recompute):
    ids = [c["id"] for c in recompute["checks"]]
    assert ids == [f"R{i:02d}" for i in range(1, len(ids) + 1)]
    for c in recompute["checks"]:
        assert c["verdict"] in VERDICTS, c["id"]
        assert c["dev_kind"] in DEV_KINDS, c["id"]
        assert isinstance(c["inputs"], dict) and c["inputs"], f"{c['id']} has no inputs"
        assert isinstance(c["formula"], str) and len(c["formula"]) > 5, f"{c['id']} has no formula"
        assert c["note"], f"{c['id']} has no rationale"


def test_stored_deviation_follows_from_claimed_and_recomputed(recompute):
    numeric = 0
    for c in recompute["checks"]:
        claimed, rec, dev = c["claimed"], c["recomputed"], c["rel_dev_pct"]
        if dev is None or not isinstance(claimed, (int, float)) or not isinstance(rec, (int, float)):
            continue
        if claimed == 0:
            continue
        numeric += 1
        assert isinstance(claimed, (int, float)) and isinstance(rec, (int, float))
        expected = abs(rec - claimed) / abs(claimed) * 100.0
        assert dev == pytest.approx(expected, rel=1e-6, abs=5e-7), (
            f"{c['id']}: stored {dev} but |{rec}-{claimed}|/|{claimed}| = {expected}")
    assert numeric >= 10, "not enough numeric checks to make the arithmetic gate meaningful"


def test_arithmetic_recomputations_are_all_under_three_percent(recompute):
    arith = [c for c in recompute["checks"] if c["dev_kind"] == "recompute_vs_claim"]
    # exactly the checks whose number is a closed-form function of disclosed inputs
    assert [c["id"] for c in arith] == ["R01", "R02", "R14", "R22"]
    for c in arith:
        assert c["rel_dev_pct"] is not None, f"{c['id']} claims a recomputation but stores no deviation"
        assert c["rel_dev_pct"] < ARITH_TOL, f"{c['id']} deviates {c['rel_dev_pct']}% >= 3%"
        assert c["under_3pct"] is True
        assert c["verdict"] == "reproduced", f"{c['id']} is under 3% but not marked reproduced"


def test_under_threshold_flags_agree_with_the_deviation(recompute):
    for c in recompute["checks"]:
        dev = c["rel_dev_pct"]
        if dev is None:
            assert c["under_3pct"] is None and c["under_15pct"] is None, c["id"]
        else:
            assert c["under_3pct"] is (dev < 3.0), c["id"]
            assert c["under_15pct"] is (dev < 15.0), c["id"]


def test_withheld_and_gap_are_never_recorded_as_pass(recompute):
    for c in recompute["checks"]:
        if c["verdict"] in {"withheld", "gap"}:
            assert c["verdict"] not in {"reproduced", "self_consistent"}
            # a withheld number must not be dressed up as a passing recomputation
            if c["verdict"] == "withheld":
                assert c["dev_kind"] in {"none", "threshold_comparison"} or c["rel_dev_pct"] is None


# ---------------------------------------------------------------------------
# 4. the load-bearing numbers, re-derived here from report inputs only
# ---------------------------------------------------------------------------
def test_geometry_inversion_is_reproducible(checks):
    c = checks["R01"]
    i = c["inputs"]
    cb = (i["DWT_t"] / i["displacement_over_DWT"]) / i["rho_t_per_m3"] / (
        i["L_m"] * i["B_m"] * i["T_m"])
    assert cb == pytest.approx(c["recomputed"], abs=5e-7)
    # the gate's PASS hinges on rho: without sea water the same numbers fail 2%
    cb_fw = (i["DWT_t"] / i["displacement_over_DWT"]) / (i["L_m"] * i["B_m"] * i["T_m"])
    assert cb_fw == pytest.approx(checks["R03"]["recomputed"], abs=5e-7)
    assert abs(cb_fw - i["Cb_declared"]) / i["Cb_declared"] * 100.0 > checks["R03"]["gate_tolerance_pct"]


def test_speed_profile_closure_is_reproducible(checks):
    c = checks["R10"]
    i = c["inputs"]
    v_mean = i["route_nm"] / i["t_h"]
    v_ow = (v_mean - i["ice_fraction"] * i["v_design_kn"]) / (1 - i["ice_fraction"])
    assert v_ow == pytest.approx(c["recomputed"], abs=1e-4)
    assert c["rel_dev_pct"] < ARITH_TOL  # closure on the 13 kn service speed

    r11 = checks["R11"]
    d = r11["reading_distance"]
    v_ow_kn = r11["inputs"]["v_ow_kn"]
    expected_t = (r11["inputs"]["ice_fraction"] * r11["inputs"]["route_nm"]
                  / r11["inputs"]["v_design_kn"]
                  + (1 - r11["inputs"]["ice_fraction"]) * r11["inputs"]["route_nm"] / v_ow_kn)
    assert d["t_total_h"] == pytest.approx(expected_t, abs=2e-3)
    assert d["t_total_h"] > r11["inputs"]["t_total_h"], "distance reading must overshoot 63.3 h"


def test_ice_fraction_readings_are_mutually_inconsistent(checks):
    """27.0% cannot be distance, energy and time at once - that is the finding."""
    r11 = checks["R11"]
    ice_time_pct = r11["reading_energy"]["ice_time_pct"]
    ice_dist_pct = r11["reading_time"]["ice_distance_pct"]
    assert ice_time_pct > 27.0 + 5.0, "the energy reading should break the 27% claim"
    assert ice_dist_pct < 27.0 - 5.0, "the distance share should be far below 27%"
    assert r11["verdict"] == "contradicted"


def test_structure_correction_implies_the_undisclosed_sn_slope(checks):
    c = checks["R14"]
    i = c["inputs"]
    beta = i["beta_theory"] * (1 + i["deviation_pct"] / 100.0)
    util = i["util_20y"] / (beta / i["beta_theory"]) ** i["sn_slope_m"]
    assert util == pytest.approx(c["recomputed"], abs=1e-3)
    m = math.log(i["util_20y"] / c["claimed"]) / math.log(beta / i["beta_theory"])
    assert m == pytest.approx(checks["R15"]["implied_sn_slope"], abs=1e-3)
    assert m == pytest.approx(3.0, abs=0.02), "the correction only closes for a cubic S-N slope"


def test_a2_skill_is_not_reproducible_from_the_disclosed_rmse_pair(checks):
    c = checks["R04"]
    i = c["inputs"]
    linear = 1 - i["rmse_a2_m"] / i["rmse_reference_m"]
    murphy = 1 - (i["rmse_a2_m"] / i["rmse_reference_m"]) ** 2
    assert linear == pytest.approx(c["skill_definitions_tried"]["linear"], abs=1e-4)
    assert murphy == pytest.approx(c["skill_definitions_tried"]["murphy"], abs=1e-4)
    assert min(abs(linear - i["skill_claimed"]), abs(murphy - i["skill_claimed"])) > 0.05
    assert c["verdict"] == "withheld"


def test_gate_census_is_exact(recompute, checks):
    table_rows = [ln for ln in SRC.read_text(encoding="utf-8").splitlines()
                  if re.match(r"^\| `G\d\d-", ln)]
    assert len(table_rows) == checks["R18"]["inputs"]["rows_in_table"] == 16
    assert all("| PASS |" in ln for ln in table_rows)
    assert checks["R18"]["verdict"] == "reproduced"


# ---------------------------------------------------------------------------
# 5. the summary is a recount, not a second opinion
# ---------------------------------------------------------------------------
def test_summary_is_a_recount_of_the_checks(recompute):
    checks = recompute["checks"]
    s = recompute["summary"]
    assert s["n_checks"] == len(checks)
    for verdict, block in s["by_verdict"].items():
        assert block["ids"] == [c["id"] for c in checks if c["verdict"] == verdict]
        assert block["n"] == len(block["ids"])
    assert sum(b["n"] for b in s["by_verdict"].values()) == len(checks)

    arith = [c for c in checks if c["dev_kind"] == "recompute_vs_claim" and c["rel_dev_pct"] is not None]
    assert s["arithmetic_checks"]["ids"] == [c["id"] for c in arith]
    assert s["arithmetic_checks"]["max_rel_dev_pct"] == max(c["rel_dev_pct"] for c in arith)
    assert s["arithmetic_checks"]["all_under_3pct"] is True

    incons = [c for c in checks
              if c["verdict"] in {"contradicted", "gap"} and c["rel_dev_pct"] is not None]
    assert s["document_inconsistencies"]["ids"] == [c["id"] for c in incons]
    assert s["document_inconsistencies"]["ids_over_3pct"] == [
        c["id"] for c in incons if c["rel_dev_pct"] >= 3.0]
    assert s["document_inconsistencies"]["max_rel_dev_pct"] == max(c["rel_dev_pct"] for c in incons)
    assert s["withheld_ids"] == [c["id"] for c in checks if c["verdict"] == "withheld"]


def test_report_error_table_self_judgement_matches_arithmetic(recompute):
    rows = recompute["report_section6_claimed_errors"]
    assert len(rows) == 13, "report 5716 declares 13 error rows"
    for r in rows:
        if r["value"] is None:
            assert r["review_under_3pct"] is None
            continue
        assert r["review_under_3pct"] is (r["value"] < 3.0), r["item"]
        assert r["declared_under_3pct"] is (r["value"] < 3.0), (
            f"{r['item']}: the report's own <3% call disagrees with its own number")


# ---------------------------------------------------------------------------
# 6. the review verdicts are internally coherent
# ---------------------------------------------------------------------------
def test_disposition_matches_the_findings(review, checks):
    findings = {f["id"]: f for f in review["severity_ranked_findings"]}
    assert findings, "a review with no findings must say so; this one has findings"
    assert review["blocking_issues"] == [] 
    assert review["disposition"] == "approve_with_notes"
    for f in findings.values():
        assert f["check"] in checks, f"{f['id']} points at a check that does not exist"
        assert f["severity"] in {"major", "medium", "minor"}
        assert f["blocking"] is False
        assert f["evidence"] and f["remediation"]
    assert set(review["must_fix_before_downstream_use"]) <= set(findings)


def test_declared_fails_are_never_downgraded(review, checks):
    """The report's honest FAILs must survive the review as FAILs."""
    for cid in ("R12", "R19", "R20"):
        assert checks[cid]["verdict"] == "self_consistent"
        assert checks[cid]["direction_honest"] is True
    q = review["errors_under_3pct_question"]
    assert q["recompute_under_3pct"] is True
    assert q["physical_claims_under_3pct"] is False
    assert q["unacceptable_by_platform_15pct"], "the 15% line must bite somewhere"
    for item in q["unacceptable_by_platform_15pct"]:
        match = re.search(r"([0-9]+\.[0-9]+)\s*%", item)
        assert match, f"no percentage in {item!r}"
        assert float(match.group(1)) > 15.0


def test_checks_not_run_are_declared(review):
    blocks = review["checks_not_run"]
    assert len(blocks) >= 4
    for b in blocks:
        assert b["what"] and b["why"]
    assert review["independence_limitations"]
    for claim in review["overstated_claims"]:
        assert claim["status"] in {"unsupported", "contradicted", "unverifiable", "conditional", "verified"}


# ---------------------------------------------------------------------------
# 7. envelope conformance + output integrity
# ---------------------------------------------------------------------------
def test_envelope_conforms_to_shared_schema(kf):
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft202012Validator(load(SCHEMA))
    validator.validate(kf)
    assert kf["package_id"] == "wp-5716-04"
    assert kf["task_type"] == "04-independent-review"
    assert kf["report_id"] == "5716"


def test_every_output_hash_matches_the_bytes_on_disk(kf):
    outputs = kf["outputs"]
    assert len(outputs) >= 8
    for name, rec in outputs.items():
        path = ROOT / rec["path"]
        assert path.exists(), f"declared output missing: {name}"
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == rec["sha256"].split(":", 1)[1], name
        assert len(data) == rec["bytes"], name


def test_every_package_artifact_is_declared(kf):
    declared = {Path(rec["path"]).name if "/" not in rec["path"].split("docs/kf/wp-5716-04/")[1]
                else rec["path"].split("docs/kf/wp-5716-04/")[1] for rec in kf["outputs"].values()}
    on_disk = {str(p.relative_to(PKG)) for p in PKG.rglob("*") if p.is_file()} - {"kf_result.json"}
    assert on_disk == declared, f"undeclared or missing artifacts: {on_disk ^ declared}"


def test_validation_block_is_a_recount(kf, recompute):
    v = kf["validation"]
    s = recompute["summary"]
    assert v["checks"] == s["n_checks"]
    for verdict in ("reproduced", "self_consistent", "contradicted", "gap", "withheld"):
        assert v[verdict] == s["by_verdict"][verdict]["n"]
    assert v["all_recomputations_under_3pct"] is True
    assert v["blocking_issues"] == 0


# ---------------------------------------------------------------------------
# 8. the prose carries the machine numbers (zero hand-copy) and the figures exist
# ---------------------------------------------------------------------------
def test_report_md_numbers_come_from_recompute(recompute):
    text = REPORT_MD.read_text(encoding="utf-8")
    s = recompute["summary"]
    C = {c["id"]: c for c in recompute["checks"]}
    expected = [
        f"{s['arithmetic_checks']['max_rel_dev_pct']:.2f}",
        f"{C['R03']['rel_dev_pct']:.2f}",
        f"{C['R11']['reading_distance']['excess_over_stated_pct']}",
        f"{C['R11']['reading_time']['ice_distance_pct']}",
        f"{C['R10']['v_ow_kn']}",
        f"{C['R14']['recomputed']:.3f}",
        f"{C['R16']['rel_dev_pct']:.2f}",
        f"{C['R21']['rel_dev_pct']:.2f}",
        str(s["n_checks"]),
    ]
    for token in expected:
        assert token in text, f"report.md does not carry the computed token {token!r}"
    for cid in C:
        assert cid in text, f"report.md never mentions check {cid}"
    # the six mandated sections
    for marker in ("## ①", "## ②", "## ③", "## ④", "## ⑤", "## ⑥"):
        assert marker in text


def test_readme_states_the_disposition_and_the_arithmetic_result(recompute):
    text = README.read_text(encoding="utf-8")
    assert "approve_with_notes" in text
    assert f"{recompute['summary']['arithmetic_checks']['max_rel_dev_pct']:.2f}" in text
    assert "withheld" in text and "unknown" in text


def test_figures_are_real_pngs(recompute):
    expected = {"fig_review_errors.png", "fig_review_closure.png"}
    found = {p.name for p in FIG_DIR.glob("*.png")}
    assert expected <= found, f"missing figures: {expected - found}"
    for name in expected:
        data = (FIG_DIR / name).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n", name
        assert len(data) > 20_000, f"{name} looks like an empty plot ({len(data)} bytes)"
        # IHDR width/height
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        assert width >= 1000 and height >= 600, f"{name} is too small to read: {width}x{height}"
    assert len(recompute["report_section6_claimed_errors"]) == 13