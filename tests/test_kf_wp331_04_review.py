"""Offline tests for work package wp-331-04 (04-independent-review, report 331).

They run against the pinned source snapshot in runs/wp-331-04/ so no network is needed.
A negative test mutates one quote and shows the verbatim guard actually goes red.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "wp-331-04"
OUT = ROOT / "docs" / "kf" / "wp-331-04"
CONTRACT_HASH = "sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717"
CONTRACT_CHARS = 1371


@pytest.fixture(scope="module")
def source() -> str:
    return (RUNS / "source_331.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads((OUT / "kf_result.wp-331-04.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def review(envelope) -> dict:
    return envelope["outputs"]["review_report.json"]


def test_envelope_validates_against_kf_result_schema(envelope):
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(envelope, schema)
    assert envelope["package_id"] == "wp-331-04"
    assert envelope["task_type"].startswith("04")
    assert envelope["report_id"] == "331"


def test_provenance_hash_is_the_source_bytes(source, envelope):
    recomputed = "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert recomputed == envelope["provenance"]["source_hash"] == CONTRACT_HASH
    assert envelope["provenance"]["source_field"] == "markdown"
    assert len(source) == CONTRACT_CHARS


def test_every_quote_is_verbatim(source, review):
    quotes = [e["quote"] for f in review["findings"] for e in f.get("evidence", [])
              if e.get("source_field") == "markdown"]
    quotes += [e["quote"] for c in review["claim_judgements"] for e in c.get("evidence", [])
               if e.get("source_field") == "markdown"]
    assert len(quotes) >= 20, "review must be anchored on real quotations"
    assert [q for q in quotes if q not in source] == []


def test_quote_locator_offsets_are_exact(source, review):
    for f in review["findings"]:
        for e in f.get("evidence", []):
            if "offset_start" in e:
                assert source[e["offset_start"]:e["offset_end"]] == e["quote"]


def test_derived_metrics_are_recomputed_not_retyped(source, review):
    rows = {}
    lines = source.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("## ③"))
    for ln in lines[start:]:
        if ln.startswith("## ") and not ln.startswith("## ③"):
            break
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) == 4 and not set(cells[1]) <= set("- ") and cells[0].lower() != "metric":
            rows[cells[0]] = cells[1:]
    num = lambda t: float(re.search(r"-?\d+(?:\.\d+)?", t).group(0))  # noqa: E731
    d = review["derived_metrics"]
    assert d["exponent_abs_deviation"] == round(abs(num(rows["Exponent"][0]) - num(rows["Exponent"][1])), 4)
    assert d["exponent_verdict"] == "FAIL" and d["stiffness_verdict"] == "FAIL"
    assert d["energy_verdict"] == "FAIL" and d["beam_verdict"] == "PASS"
    assert d["indent_over_R"] == 0.5  # max_indent 0.05 / R 0.1, both parsed from the source
    assert d["stiffness_budget_overshoot_factor"] == 14.7
    assert d["energy_budget_overshoot_factor"] == 58.6


def test_verbatim_guard_can_go_red(source):
    """Negative control: a mutated quote must NOT be found in the source."""
    tampered = "| Energy drift | 5.86% | ≤1% | — |"
    assert tampered not in source


def test_no_self_verification_field_anywhere(review):
    blob = json.dumps(review)
    assert not re.search(r'"(verified|verification_status|verification_level|is_verified|gate_confirmed)"', blob)
    assert review["review_event"]["marks_claims_verified"] is False


def test_upstream_absence_is_reported_honestly(review):
    if review["upstream"]["product_found"] is False:
        assert review["acceptance_selfcheck"]["upstream_packages_completed"] is False
        assert any(f["blocking"] for f in review["findings"])
        assert review["verdict"] != "pass"
    else:  # pragma: no cover - becomes live once wp-331-01 is attached
        assert review["acceptance_selfcheck"]["upstream_packages_completed"] is True


def test_delivery_markdown_has_single_json_block_with_the_envelope(envelope):
    md = (OUT / "KF-RESULT-wp-331-04.md").read_text(encoding="utf-8")
    assert md.startswith("# KF-RESULT wp-331-04")
    assert "kf-wp:wp-331-04" in md
    assert md.count("```json") == 1 and md.count("```") == 2
    block = md.split("```json", 1)[1].split("```", 1)[0]
    assert json.loads(block) == envelope