"""wp-3076-04 self-checks (independent review of wp-3076-01 / report 3076).

Runs offline: needs only the artefacts already in the worktree
(artifacts/wp-3076-04/*, docs/wp-3076-04/*). No network, no producer code.

T1..T4  structure/JSON/schema of the three emitted files
T5      review ledger is legal under scripts/ke_state_machine.py (+ negative control:
        the producer identity cannot approve; request-changes needs findings)
T6      every quote in the review report is verbatim in the source markdown
        (+ negative control: a tampered quote is caught)
T7      no claim/field is labelled verified
T8      the independent reconstruction reproduces (H1 series, HARD inventory)
T9      delivery md has exactly one json block, byte-equal to the envelope file
T10     boundary: only report_id 3076 is used as the envelope report_id
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "wp-3076-04"
DOC = ROOT / "docs" / "wp-3076-04" / "KF-RESULT-wp-3076-04.md"
SRC = PKG / "source.md"
SCHEMAS = ROOT / "schemas"
EXPECTED_SHA = "9b7bb2427af8a1b4a7f229971492c52fc691737a7742b4b703ce4e41cea464c1"


def _load_json(name: str) -> dict:
    return json.loads((PKG / name).read_text(encoding="utf-8"))


def _load_module(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def src_md() -> str:
    return SRC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def envelope() -> dict:
    return _load_json("kf_result.wp-3076-04.json")


@pytest.fixture(scope="module")
def review() -> dict:
    return _load_json("review_report.json")


@pytest.fixture(scope="module")
def ledger() -> list:
    return _load_json("review_events.json")


# --- T1: JSON parses ------------------------------------------------------
def test_T1_all_outputs_are_valid_json(envelope, review, ledger):
    assert isinstance(envelope, dict) and isinstance(review, dict) and isinstance(ledger, list)
    assert envelope["package_id"] == "wp-3076-04"
    assert envelope["task_type"] == "04-independent-review"
    assert envelope["report_id"] == "3076"


# --- T2: envelope schema --------------------------------------------------
def test_T2_envelope_passes_kf_result_schema(envelope):
    schema = _load_json_schema("kf_result.v1.schema.json")
    jsonschema.validate(envelope, schema)
    assert envelope["provenance"]["source_hash"] == f"sha256:{EXPECTED_SHA}"
    assert set(envelope["outputs"]) >= {"review_report.json"}


def _load_json_schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def test_T2b_envelope_hash_is_the_source_bytes(src_md):
    # provenance.source_hash must equal the sha256 of the report markdown bytes
    assert hashlib.sha256(src_md.encode("utf-8")).hexdigest() == EXPECTED_SHA


# --- T3: review ledger schema + decision vocabulary -----------------------
def test_T3_ledger_passes_review_event_schema(ledger):
    schema = _load_json_schema("review-event.schema.json")
    assert ledger, "ledger must contain the review decision"
    for ev in ledger:
        jsonschema.validate(ev, schema)
    ev = ledger[0]
    assert ev["decision"] == "request-changes"
    assert ev["reviewer"]["role"] == "red-team-reviewer"
    assert ev.get("touches_epistemic_status") is None  # schema forbids the key; A3 holds by absence


# --- T4: review report contract fields -----------------------------------
def test_T4_review_report_shape(review, ledger):
    assert review["decision"] in {"pass", "fail", "needs-fix"}
    assert review["decision"] == "needs-fix"
    assert review["reviewed_package"] == "wp-3076-01"
    sev = [f["severity"] for f in review["findings"]]
    assert set(sev) <= {"blocking", "major", "minor", "informational"}
    assert len(review["findings"]) == len({f["id"] for f in review["findings"]})
    for f in review["findings"]:
        assert f["evidence"], f"{f['id']} has no evidence"
        for e in f["evidence"]:
            assert e["quote"] and isinstance(e["line"], int)
    # claims use review vocabulary only (never "verified")
    assert {c["status"] for c in review["claims_assessment"]} <= {
        "supported", "partially-supported", "unresolved", "refuted"}
    # ledger findings mirror the report findings (same count, same severities)
    assert len(ledger[0]["findings"]) == len(review["findings"])
    assert [f["severity"] for f in ledger[0]["findings"]] == sev


# --- T5: ledger legality under the KE review state machine ----------------
def test_T5_ledger_is_legal_and_producer_cannot_request_changes(ledger):
    sys.path.insert(0, str(ROOT / "scripts"))
    ksm = _load_module(ROOT / "scripts" / "ke_state_machine.py", "kf_ksm_3076_04")
    ctx = {"producer_ids": ["1", "kf-wp3076-01 asset registration (scripts/kf_register_3076.py)"]}
    state = ksm.submit(ctx, "draft")            # draft -> in-review is a system transition
    final, codes = ksm.fold(ledger, ctx, initial_state=state)
    assert final == "draft" and codes == ["OK_CHANGES_REQUESTED"]

    # negative control: dropping findings must be refused
    bad = [{**ledger[0], "findings": []}]
    with pytest.raises(ksm.StateMachineError) as ei:
        ksm.fold(bad, ctx, initial_state="in-review")
    assert ei.value.code == "FINDINGS_REQUIRED"

    # negative control: the producer identity cannot be the one approving
    producer_ev = [{"id": "tkr:x:1", "decision": "approve", "policy_version": ksm.POLICY_VERSION,
                    "reviewer": {"id": "kf-wp3076-01 asset registration", "reviewer_type": "agent"},
                    "reviewed_at": "2026-11-12T02:50:00Z"}]
    with pytest.raises(ksm.StateMachineError) as ei2:
        ksm.fold(producer_ev, ctx, initial_state="in-review")
    assert ei2.value.code == "SELF_APPROVAL_BLOCKED"

    ok, basis = ksm.is_independent(ledger[0]["reviewer"], ksm.producer_identity(ctx))
    assert ok, basis


# --- T6: quotes are verbatim -------------------------------------------
def _all_quotes(obj, out=None):
    if out is None:
        out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "quote" and isinstance(v, str):
                out.append(v)
            else:
                _all_quotes(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _all_quotes(v, out)
    return out


def test_T6_every_quote_is_verbatim_in_source(review, src_md):
    quotes = _all_quotes(review)
    assert len(quotes) >= 15
    missing = [q for q in quotes if q not in src_md]
    assert not missing, f"quotes not found verbatim: {missing}"


def test_T6b_tampered_quote_is_caught(src_md):
    # negative control for T6: a one-character edit must break verbatim matching
    tampered = "HARD 失败 9/11"
    assert tampered not in src_md


# --- T7: nothing is labelled verified ------------------------------------
def test_T7_no_verified_label_anywhere():
    for p in sorted(PKG.glob("*.json")):
        text = p.read_text(encoding="utf-8")
        assert '"verified": true' not in text.replace(" ", ""), p.name
        assert '"status": "verified"' not in text.replace(" ", ""), p.name
        assert "ACCEPTED_VERIFIED" not in text, p.name


# --- T8: independent reconstruction reproduces --------------------------
def test_T8_independent_reconstruction(review):
    mod = _load_module(PKG / "independent_dispersion_check.py", "kf_idc_3076_04")
    md = mod.load_md()
    p = mod.parse_params(md)
    claims = mod.parse_claims(md)

    # H1 deviation series, recomputed with an independent solver
    for T in (4, 6, 8, 10, 12):
        kt = mod.find_roots(p, "tanh", T)[0][0]
        kc = mod.find_roots(p, "coth", T)[0][0]
        dev = abs(kc - kt) / kt * 100.0
        assert abs(dev - claims["dev"][T]) < 0.01, (T, dev, claims["dev"][T])

    # HARD inventory: the report's own table has 10 HARD rows, the summary says /11
    audit = mod.count_hard_rows(md)
    assert audit["n_rows"] == 11 and audit["n_hard"] == 10 and audit["n_soft"] == 1
    assert audit["hard_fail_sealed"] == 8 and audit["hard_fail_control"] == 0
    assert all(c["den"] != audit["n_hard"] for c in claims["hard_fail_claims"])

    # coth no-root boundary: T=14.0 s still has a root, T=14.2 s does not
    assert mod.find_roots(p, "coth", 14.0)
    assert not mod.find_roots(p, "coth", 14.2)
    tc = 2.0 * 3.141592653589793 / (p["g"] / p["h"]) ** 0.5
    assert 14.0 < tc < 14.2


# --- T9: delivery md has exactly one json block --------------------------
def test_T9_single_json_block_matches_envelope(envelope):
    doc = DOC.read_text(encoding="utf-8")
    assert doc.startswith("# KF-RESULT wp-3076-04")
    assert doc.count("```json") == 1
    body = doc.split("```json", 1)[1].split("```", 1)[0]
    assert json.loads(body) == envelope
    assert "kf-wp:wp-3076-04" not in doc  # tags are a platform field, not markdown
    for section in ("## ①", "## ②", "## ③", "## ④", "## ⑤", "## ⑥"):
        assert section in doc, section


# --- T10: report_id boundary -------------------------------------------
def test_T10_report_id_boundary(envelope, review):
    assert envelope["report_id"] == "3076"
    assert review["report_id"] == "3076"
    assert review["reviewed_object"]["source_uri"] == "tensor://reports/3076"
    assert review["reviewed_object"]["chars"] == len(SRC.read_text(encoding="utf-8"))