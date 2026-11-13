"""wp-444-04 independent-review deliverables: reproducibility and consistency tests.

These tests do not re-litigate the domain numbers; they assert that the review
itself is (a) deterministic from the stored fixtures, (b) internally consistent,
(c) schema-valid where a schema exists, and (d) never writes the verification axis.
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "artifacts", "wp-444-04")
DOC = os.path.join(ROOT, "docs", "kf", "wp-444-04")
SRC = os.path.join(ART, "source_markdown.md")
UP_MD = os.path.join(ART, "upstream_report_14623.md")
UP_JSON = os.path.join(ART, "upstream_envelope_wp-444-01.json")
VERIFY = os.path.join(ART, "verification.json")
REPORT = os.path.join(DOC, "review_report.json")
EVENTS = os.path.join(DOC, "review_events.json")

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ke_state_machine as ksm  # noqa: E402


def _load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def verification(tmp_path_factory):
    out = tmp_path_factory.mktemp("replay") / "verification.json"
    subprocess.run(
        [sys.executable, os.path.join(ROOT, "work", "verify_wp444_01.py"),
         "--md", SRC, "--upstream", UP_MD, "--out", str(out)],
        check=True, capture_output=True, text=True,
    )
    return _load(str(out)), _load(VERIFY)


def test_fixtures_present():
    for p in (SRC, UP_MD, UP_JSON, VERIFY, REPORT, EVENTS):
        assert os.path.exists(p), p


def test_source_fixture_hash_is_the_declared_contract_hash(verification):
    import hashlib
    with open(SRC, "rb") as f:
        h = "sha256:" + hashlib.sha256(f.read()).hexdigest()
    assert h == ("sha256:4068f881c6722010ea3cdf78ee673068d8fb56"
                 "fdc12be39db9c7b3f764457af2")
    assert verification[0]["measured"]["markdown_sha256"] == h


def test_offline_replay_reproduces_stored_verification(verification):
    replay, stored = verification
    assert replay["measured"] == stored["measured"]
    assert replay["hard_failures"] == stored["hard_failures"]


def test_structural_counts_match_source(verification):
    m = verification[0]["measured"]
    assert (m["sections"], m["tables"], m["figures"], m["code_references"]) == (7, 4, 1, 0)


def test_upstream_envelope_is_schema_valid():
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json"))
    env = _load(UP_JSON)
    errs = list(jsonschema.Draft202012Validator(schema).iter_errors(env))
    assert not errs, [f"{list(e.path)}: {e.message}" for e in errs]


def test_output_key_differs_from_contract_declaration_is_recorded():
    """F1 must stay a finding while the envelope key still differs from the contract."""
    env = _load(UP_JSON)
    rep = _load(REPORT)
    finding = next(f for f in rep["findings"] if f["id"] == "F1")
    assert "asset_manifest.json" in finding["evidence"]["declared_contract_output_key"]
    assert "asset_manifest" in env["outputs"]
    assert "asset_manifest.json" not in env["outputs"]


def test_non_verbatim_quotes_uniquely_found_in_source():
    """Every quote the review calls non-verbatim must really be absent from the source,
    and every quote it calls verbatim must really be present (no hand-typed list)."""
    src = open(SRC, encoding="utf-8").read()
    rep = _load(REPORT)
    claims = [c for c in rep["checks_performed"] if c["id"] == "H9"][0]["result"]
    assert claims["non_verbatim"], "expected at least one non-verbatim quote"
    for q in claims["non_verbatim"]:
        assert q not in src, q
    stored = _load(VERIFY)["checks"]["H9_locator_verbatim"]
    for item in stored:
        assert (item["quote"] in src) == item["verbatim_in_markdown"]


def test_review_report_shape_and_verdict_binding():
    rep = _load(REPORT)
    for key in ("review_id", "package_id_reviewed", "report_id", "reviewer",
                "checks_performed", "checks_not_run", "findings", "verdict",
                "independence", "repro_cmd"):
        assert key in rep, key
    assert rep["package_id_reviewed"] == "wp-444-01"
    assert rep["report_id"] == "444"
    sev = {f["id"]: f["severity"] for f in rep["findings"]}
    assert sev and set(sev.values()) <= {"blocking", "medium", "low"}
    # a needs-fix verdict requires at least one medium-or-worse finding with reproduction
    if rep["verdict"]["verdict"] == "needs-fix":
        assert any(f["severity"] in ("medium", "blocking") and f.get("reproduction")
                   for f in rep["findings"])


def test_reviewer_is_independent_of_the_producer():
    rep = _load(REPORT)
    ok, basis = ksm.is_independent(rep["reviewer"],
                                   ksm.producer_identity(
                                       {"producer_ids": ["m15508", "agent/m15508"]}))
    assert ok, basis
    ok2, basis2 = ksm.is_independent({"id": "m15508", "reviewer_type": "agent"},
                                     ksm.producer_identity({"producer_ids": ["m15508"]}))
    assert not ok2 and basis2 == "SELF_APPROVAL_BLOCKED"


def test_review_event_ledger_folds_from_draft_to_request_changes():
    events = _load(EVENTS)
    state = ksm.submit({}, "draft")
    assert state == "in-review"
    final, codes = ksm.fold(events, {"producer_ids": ["m15508"]}, initial_state="in-review")
    assert codes == ["OK_CHANGES_REQUESTED"]
    assert final == "draft"


def test_no_verification_axis_written():
    rep = _load(REPORT)
    blob = json.dumps(rep, ensure_ascii=False)
    assert '"verification_status"' not in blob
    assert rep["axes_untouched"]["claims_marked_verified"] is False
    env = _load(UP_JSON)
    assert env["provenance"].get("source_hash_verified") is not None  # self-check only
    assert "verification_status" not in json.dumps(env)


def test_out_of_scope_observations_are_computed_not_asserted():
    obs = _load(os.path.join(ART, "out_of_scope_observations.json"))
    rows = {r["row"]: r for r in obs["rows"]}
    ittc = rows["ITTC-1957 Cf (Re=1e8)"]
    assert ittc["formula_value"] == pytest.approx(0.075 / (8 - 2) ** 2)
    assert ittc["rel_error_vs_formula_pct"] > 0
    assert rows["Blasius Cf (Re_L=1e6)"]["rel_error_vs_formula_pct"] == 0.0
    assert rows["HM 1+k (Cb=0.6)"]["formula"] is None  # not reproducible from the report

def test_deliverable_has_exactly_one_json_block_and_contract_hash():
    import hashlib
    import re
    md = open(os.path.join(DOC, "KF-RESULT-wp-444-04.md"), encoding="utf-8").read()
    blocks = re.findall(r"```json\n(.*?)```", md, re.S)
    assert len(blocks) == 1, f"deliverable must carry exactly one json block, got {len(blocks)}"
    env = json.loads(blocks[0])
    assert env["package_id"] == "wp-444-04"
    assert env["task_type"] == "04-independent-review"
    assert env["report_id"] == "444"
    assert "review_report.json" in env["outputs"]
    with open(SRC, "rb") as f:
        live = "sha256:" + hashlib.sha256(f.read()).hexdigest()
    assert env["provenance"]["source_hash"] == live
    assert md.lstrip().startswith("# KF-RESULT wp-444-04")
