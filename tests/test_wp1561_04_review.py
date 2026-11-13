"""wp-1561-04 · assertions on the emitted independent-review package.

These tests re-derive facts instead of trusting the emitted artefacts where an
independent derivation is cheap (source hash, upstream quote resolution, ledger fold).

  python3 -m pytest tests/test_wp1561_04_review.py -q
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs/kf/wp-1561-04"
UP = ROOT / "docs/kf/wp-1561-01"
SRC = UP / "source/report_1561.md"
CONTRACT_HASH = "sha256:19203e6ea7f05573f0b06835f9c0e1f08fb54fc5481787ace02487d5ac6d1620"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


def load(name: str):
    return json.loads((PKG / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def md() -> str:
    return SRC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def review() -> dict:
    return load("review_report.json")


@pytest.fixture(scope="module")
def checks() -> dict:
    return load("review_checks.json")


def test_source_snapshot_matches_contract_hash():
    got = "sha256:" + hashlib.sha256(SRC.read_bytes()).hexdigest()
    assert got == CONTRACT_HASH


def test_envelope_is_valid_and_schema_conformant():
    import jsonschema
    env = load("kf_result.json")
    jsonschema.validate(env, json.loads((ROOT / "schemas/kf_result.v1.schema.json").read_text()))
    assert env["package_id"] == "wp-1561-04"
    assert env["task_type"].startswith("04")
    assert env["report_id"] == "1561"
    assert env["provenance"]["source_hash"] == CONTRACT_HASH
    assert env["provenance"]["source_field"] == "markdown"
    assert set(env["outputs"]) == {"review_report.json", "review_events.json"}
    assert env["outputs"]["review_report.json"]["disposition"] in {
        "approve", "approve-with-notes", "request-changes"}


def test_review_report_separates_failures_from_blocking(checks, review):
    fails = [c["id"] for c in checks["checks"] if c["status"] == "fail"]
    allowlisted = {"C5b", "C11", "C12"}   # traceability/wording, no locator or hash impact
    assert set(fails) <= allowlisted, fails
    assert review["blocking_findings"] == []
    assert review["disposition"] == "approve-with-notes"
    assert review["counts"]["fail"] == len(fails)
    assert review["counts"]["checks"] == len(checks["checks"])


def test_every_quote_in_the_review_is_verbatim_in_the_source(md):
    review = load("review_report.json")
    quotes = [e["quote"] for f in review["findings"] for e in f["evidence"] if "quote" in e]
    assert quotes, "the review must bind its findings to raw source text"
    for q in quotes:
        assert q in md, f"quote not found verbatim in report 1561: {q[:80]!r}"
        assert len(q) >= 12


def test_narrative_fragments_are_verbatim_in_the_source(md):
    body = (PKG / "REPORT.md").read_text(encoding="utf-8")
    fragments = [
        "**推力闭合反解（不用钳位）。**",
        "修复后闸门：`cases=5 evaluated=5 verdict_fail=0 froude_fail=0`",
        "1. **Ferry 落在 I3 带边上（η_D=0.516）**。",
        "其中 Aframax 的 Cb·L·B·T 与输入排水量相差 13.7%",
        "η_R 默认 1.0（偏保守：Holtrop 回归值约 0.98）",
        "12→32 站 K_T 差 0.6%、η0 差 0.05%",
    ]
    for f in fragments:
        assert f in md, f"fragment not in source: {f[:60]!r}"
        assert f in body, f"fragment missing from REPORT.md: {f[:60]!r}"


def test_all_upstream_quotes_still_resolve(md):
    man = json.loads((UP / "asset_manifest.json").read_text(encoding="utf-8"))
    bad = [a["asset_id"] for a in man["assets"] if a["quote"] not in md]
    assert bad == []


def test_ledger_folds_to_approved_and_reviewer_is_independent():
    from ke_state_machine import fold, is_independent, producer_identity
    led = load("review_events.json")
    state, codes = fold(led["events"], {"producer_ids": led["producer_ids"]},
                        initial_state="in-review")
    assert state == "approved"
    assert codes == ["OK_APPROVED"]
    ok, basis = is_independent(led["events"][-1]["reviewer"],
                               producer_identity({"producer_ids": led["producer_ids"]}))
    assert ok and basis == "distinct-identity"
    assert led["system_transitions"][0]["to"] == "in-review"


def test_self_approval_is_refused_by_the_same_machine():
    from ke_state_machine import fold
    led = load("review_events.json")
    events = json.loads(json.dumps(led["events"]))
    events[0]["reviewer"] = {"id": led["producer_ids"][0], "reviewer_type": "agent"}
    with pytest.raises(Exception) as exc:
        fold(events, {"producer_ids": led["producer_ids"]}, initial_state="in-review")
    assert "SELF_APPROVAL_BLOCKED" in str(exc.value)


def test_no_verification_marker_in_the_deliverables():
    markers = ("verification_status", "verification_level", "is_verified", "gate_confirmed",
               '"verified"')
    for name in ("review_report.json", "review_events.json", "kf_result.json"):
        raw = (PKG / name).read_text(encoding="utf-8")
        for m in markers:
            assert m not in raw, f"{name} carries {m}"


def test_recomputation_table_covers_five_ships(checks):
    per = {c["id"]: c for c in checks["checks"]}["E1"]["detail"]["per_ship"]
    assert set(per) == {"KCS", "KVLCC2", "Feeder120", "Aframax", "Ferry"}
    for name, d in per.items():
        assert d["T_rel_err"] < 2e-3, name
        assert d["I2_in_band"] and d["P_D_in_band"] and d["I4_contains_1"], name
        assert abs(d["D_over_T"] - 0.70) < 2e-3, name
        assert d["J_in_rpm_interval"] and d["PD_in_rpm_interval"], name


def test_not_run_is_declared_not_silent(checks, review):
    not_run = [c["id"] for c in checks["checks"] if c["status"] == "not_run"]
    assert not_run == ["G1"]
    assert len(review["checks_not_run"]) >= 5


def test_report_body_has_the_six_sections_and_a_figure():
    body = (PKG / "REPORT.md").read_text(encoding="utf-8")
    for head in ("## ①", "## ②", "## ③", "## ④", "## ⑤", "## ⑥"):
        assert head in body
    assert "```json" not in body, "the single json block belongs to the platform report, not REPORT.md"
    assert (PKG / "fig_review_checks.png").stat().st_size > 10_000


def test_prompt_independence_is_measured(checks):
    f2 = {c["id"]: c for c in checks["checks"]}["F2"]
    assert f2["status"] == "pass"
    assert f2["detail"]["jaccard"] < 0.5