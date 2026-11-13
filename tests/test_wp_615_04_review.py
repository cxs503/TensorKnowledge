"""Offline invariants for the wp-615-04 independent review (report 615).

These assertions pin the review's own integrity: the source it judged, the quotes it
used, and the fact that no claim is marked verified by the reviewer.

Run: python3 -m pytest tests/test_wp_615_04_review.py -q
"""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "runs/wp-615-04"


def _load(name):
    return json.loads((OUT / name).read_text())


def test_source_hash_is_pinned_and_matches_local_copy():
    src = (OUT / "report_615.md").read_text()
    assert hashlib.sha256(src.encode()).hexdigest() == (
        "3c1b5f9dc373359c9ca5692b5f822bc1ee8c13b50dc015b9b84c7530e29b7e75")


def test_every_quote_is_verbatim_in_the_source():
    md = (OUT / "report_615.md").read_text()
    quotes = _load("independent_checks.json")["quotes"]
    assert len(quotes) >= 20
    missing = [k for k, v in quotes.items() if v["quote"] not in md]
    assert missing == []


def test_envelope_schema_and_provenance():
    import jsonschema
    kf = _load("kf_result.json")
    jsonschema.validate(kf, json.loads((ROOT / "schemas/kf_result.v1.schema.json").read_text()))
    md = (OUT / "report_615.md").read_text()
    assert kf["provenance"]["source_hash"] == "sha256:" + hashlib.sha256(md.encode()).hexdigest()
    assert kf["report_id"] == "615" and kf["package_id"] == "wp-615-04"


def test_review_event_is_legal_and_requests_changes():
    import jsonschema
    events = _load("review_events.json")
    schema = json.loads((ROOT / "schemas/review-event.schema.json").read_text())
    for ev in events:
        jsonschema.validate(ev, schema)
        assert ev["decision"] == "request-changes"
        assert ev["findings"], "request-changes must carry findings"
    # the ledger must fold legally from in-review
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from ke_state_machine import fold
    state, codes = fold(events, {"id": "wp-615-01", "created_by": "producer-session",
                                "reviewer_id": None}, initial_state="in-review")
    assert state == "draft" and "OK_CHANGES_REQUESTED" in codes


def test_reviewer_does_not_mark_anything_verified():
    rr = _load("review_report.json")
    allowed = {"supported", "partially-supported", "overstated", "unsupported", "unresolved"}
    assert {c["assessment"] for c in rr["claims_assessment"]} <= allowed
    assert "verified" not in json.dumps(rr["claims_assessment"]).lower()
    assert rr["verdict"] in {"pass", "needs-fix", "fail"}


def test_quantitative_findings_hold():
    """The three numbers the verdict rests on, recomputed from the parsed report table."""
    checks = _load("independent_checks.json")["base"]
    rc = checks["recomputed"]
    assert abs(rc["stokes_terminal_velocity_m_s"] - 0.0545) / 0.0545 < 1e-6
    assert abs(rc["relaxation_time_s"] - 0.0611111) / 0.0611111 < 1e-4
    assert abs(rc["diameter_over_cell"] - 0.2) < 1e-9          # dp/dx = 1 mm / 5 mm
    assert 50 < rc["reported_vs_stokes_re_sim"] < 60            # Re far outside Stokes range
    assert rc["sn_terminal_velocity_m_s"] < 0.03                # closure-consistent v_t
    assert rc["stokes_vs_sn_velocity_gap_ratio"] > 0.15         # >15% unacceptable band
    assert rc["reported_over_sn_terminal_velocity"] > 2.0


def test_published_markdown_has_exactly_one_json_block():
    md = (OUT / "report_published.md").read_text()
    assert md.count("```json") == 1
    assert md.startswith("# KF-RESULT wp-615-04")
    body = md.split("```json", 1)[1].rsplit("```", 1)[0]
    kf = json.loads(body)
    assert kf == _load("kf_result.json")