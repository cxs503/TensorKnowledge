"""Regression tests for the wp-5611-04 independent review (report 5611).

Two layers:

1. *Logic* tests — the review helpers (brace expansion, path-token recall,
   offset-vs-quote resolution) are pure functions and are pinned here with
   synthetic inputs, so the review cannot silently lose a check.
2. *Artifact* tests — when the review outputs are present in the worktree
   (``docs/kf/wp-5611-04/``) they are re-validated: envelope schema,
   review-event schema + state-machine fold, and the rule that every ``quote``
   in the report is a verbatim slice of report 5611's markdown.  These skip
   (never silently "pass") when the sourced artefacts are absent, e.g. on a
   clean GitHub checkout without the fetched report.

Repro:
    python3 -m pytest tests/kf/test_wp_5611_04_review.py -q
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
for extra in (REPO / "scripts", REPO):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import kf_review_5611_04 as rv  # noqa: E402

ART = REPO / "docs" / "kf" / "wp-5611-04"
SOURCE = REPO / "work" / "kf-wp-5611" / "source_5611.md"


# --------------------------------------------------------------------------- #
# 1. logic
# --------------------------------------------------------------------------- #
def test_brace_expansion_covers_every_alternative():
    assert rv.expand_braces("tools/pulse/{a,b}.py") == ["tools/pulse/a.py", "tools/pulse/b.py"]
    assert len(rv.expand_braces("x/{a,b,c,d}.py")) == 4
    assert rv.expand_braces("plain.py") == ["plain.py"]


def test_token_scan_reports_real_paths_and_ignores_elision():
    md = ("lead `tools/pulse/{alpha,beta}.py` tail `fig1..3.png` "
          "artifacts/x/run.jsonl and `tests/t.py`")
    concrete, elided = rv.markdown_artifact_tokens(md)
    assert "tools/pulse/alpha.py" in concrete
    assert "tools/pulse/beta.py" in concrete
    assert "artifacts/x/run.jsonl" in concrete
    assert "tests/t.py" in concrete
    assert elided == ["fig1..3.png"]
    assert not any(".." in t for t in concrete)


def test_offset_mismatch_is_detected_even_when_quote_exists():
    """The defect class F-01: quote present, declared span wrong."""
    text = "## heading\n\nbody text here"
    loc = {"quote": "## heading", "char_start": 0, "char_end": 20}
    s, e = rv.offset_keys(loc)
    assert (s, e) == (0, 20)
    assert text.find(loc["quote"]) == 0
    assert text[s:e] != loc["quote"]  # E4 would have to fail
    good = {"quote": "## heading", "start_offset": 0, "end_offset": 10}
    s, e = rv.offset_keys(good)
    assert text[s:e] == good["quote"]


def test_offset_keys_prefers_gate_names():
    loc = {"start_offset": 1, "end_offset": 2, "char_start": 5, "char_end": 9}
    assert rv.offset_keys(loc) == (1, 2)
    assert rv.offset_keys({"quote": "x"}) == (None, None)


def test_sha_and_line_helpers_are_verbatim():
    text = "alpha\nbeta gen_mod.py in brace `{a,gen_mod}.py` line\n"
    assert rv.line_at(text, "tools/gen_mod.py") == \
        "beta gen_mod.py in brace `{a,gen_mod}.py` line"
    assert rv.line_at(text, "absent_token") == ""
    assert rv.sha256("abc").startswith("sha256:")
    assert rv.sha256("abc") == "sha256:" + hashlib.sha256(b"abc").hexdigest()


# --------------------------------------------------------------------------- #
# 2. artefacts
# --------------------------------------------------------------------------- #
def _load(name):
    p = ART / name
    if not p.is_file():
        pytest.skip(f"{p} absent (review not run in this checkout)")
    return json.loads(p.read_text(encoding="utf-8"))


def test_envelope_validates_against_kf_result_schema():
    jsonschema = pytest.importorskip("jsonschema")
    env = _load("kf_result.json")
    schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text())
    jsonschema.validate(env, schema)
    assert env["package_id"] == "wp-5611-04"
    assert env["task_type"] == "04-independent-review"
    assert env["report_id"] == "5611"
    assert env["provenance"]["source_field"] == "markdown"
    assert set(env["outputs"]) == {"review_report.json", "review_events.json"}
    assert env["claims"] == []
    assert "source_hash" in env["provenance"]


def test_review_events_schema_and_state_machine_fold():
    jsonschema = pytest.importorskip("jsonschema")
    from ke_state_machine import fold, submit

    events = _load("review_events.json")
    schema = json.loads((REPO / "schemas" / "review-event.schema.json").read_text())
    for ev in events:
        jsonschema.validate(ev, schema)
    ctx = {"producer_ids": ["agent/m15570"]}
    state = submit(ctx, "draft")
    state, codes = fold(events, ctx, initial_state=state)
    assert state == "draft"                      # request-changes returns to draft
    assert codes == ["OK_CHANGES_REQUESTED"]


def test_review_report_matches_the_machine_checks():
    checks = _load("review_checks.json")
    report = _load("review_report.json")
    assert report["scope_and_checks_performed"]["n_checks"] == checks["n_checks"]
    assert report["scope_and_checks_performed"]["n_pass"] == checks["n_pass"]
    failing = {c["check_id"] for c in checks["checks"] if not c["ok"]}
    finding_ids = {f["finding_id"] for f in report["findings"]}
    # every machine failure must be pleaded by a finding; no orphan finding
    assert failing == {"R07.declared_offsets_byte_exact", "R10.inventory_recall",
                       "R14.referenced_artifacts_existence_probe",
                       "R16.locator_quote_length_floor"}
    assert finding_ids == {"F-01", "F-02", "N-01", "N-02", "N-03"}
    assert report["verdict"]["disposition"] == "request-changes"
    assert report["verdict"]["pass"] is False


def test_every_report_quote_is_a_verbatim_slice_of_the_source():
    if not SOURCE.is_file():
        pytest.skip("source markdown not fetched in this checkout")
    md = SOURCE.read_text(encoding="utf-8")
    report = _load("review_report.json")
    quotes: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "quote" and isinstance(v, str) and v:
                    quotes.append(v)
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(report)
    assert quotes, "review report carries no evidence quotes"
    bad = [q for q in quotes if q not in md]
    assert not bad, f"non-verbatim quotes: {bad}"


def test_review_report_does_not_assert_verification_status():
    """The review axis informs; only the platform gate computes verification."""
    if not SOURCE.is_file():
        pytest.skip("review artefacts absent")
    report = _load("review_report.json")
    banned = {"verified", "verification_status", "verification_level", "is_verified",
              "gate_confirmed"}
    hits: list[str] = []

    def walk(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in banned:
                    hits.append(f"{path}/{k}")
                walk(v, f"{path}/{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(report)
    assert hits == [], f"review report asserts verification state: {hits}"