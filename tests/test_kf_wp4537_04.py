"""Acceptance tests for KF work package wp-4537-04 (independent review of wp-4537-01).

The tests re-derive every claim of the review package from bytes on disk instead of
trusting the emitted JSON: source hash, quote resolvability, disposition/severity
consistency, review-ledger legality (via the engine's own state machine), reviewer
independence, single-report scope, and reproducibility of the refutation probe.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-4537-04"
SOURCE = ROOT / "runs" / "m15829_wp4537_04" / "source_report_4537.md"
UPSTREAM_SCRIPT = ROOT / "scripts" / "kf" / "register_4537_assets.py"
CONTRACT_HASH = "sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08"

sys.path.insert(0, str(ROOT / "scripts"))


def _load(name: str) -> dict:
    return json.loads((PKG / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return _load("kf_result.json")


@pytest.fixture(scope="module")
def review(envelope: dict) -> dict:
    return envelope["outputs"]["review_report.json"]


@pytest.fixture(scope="module")
def events(envelope: dict) -> list:
    return envelope["outputs"]["review_events.json"]


@pytest.fixture(scope="module")
def markdown() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_result_json_valid_and_schema_conformant(envelope: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(envelope, schema)
    assert envelope["package_id"] == "wp-4537-04"
    assert envelope["task_type"] == "04-independent-review"
    assert envelope["report_id"] == "4537"
    assert envelope["claims"] == []


def test_source_hash_is_independently_recomputable(envelope: dict, markdown: str) -> None:
    computed = "sha256:" + hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    assert computed == CONTRACT_HASH
    assert envelope["provenance"]["source_hash"] == CONTRACT_HASH
    assert envelope["provenance"]["source_field"] == "markdown"


def test_every_finding_quote_resolves_at_its_declared_span(review: dict, markdown: str) -> None:
    n = 0
    for finding in review["findings"]:
        assert finding["evidence"], f"{finding['finding_id']} has no evidence"
        for ev in finding["evidence"]:
            corpus = (ROOT / ev["corpus"]).read_text(encoding="utf-8")
            assert corpus == markdown or ev["corpus"] != "runs/m15829_wp4537_04/source_report_4537.md"
            start, end = ev["span"]
            assert corpus[start:end] == ev["quote"], f"{finding['finding_id']} span mismatch"
            digest = "sha256:" + hashlib.sha256(ev["quote"].encode("utf-8")).hexdigest()
            assert digest == ev["content_hash"]
            assert len(ev["quote"]) >= 12
            n += 1
    assert n >= 4


def test_disposition_is_consistent_with_findings(review: dict) -> None:
    blocking = [f for f in review["findings"] if f["blocking"]]
    expected = "needs-fix" if blocking else "pass"
    assert review["disposition"] == expected
    assert review["disposition"] in ("pass", "fail", "needs-fix")
    for f in review["findings"]:
        assert f["severity"] in ("blocker", "medium", "low", "info")
        assert f["reproduction"] and f["remediation"] and f["impact"]


def test_review_ledger_folds_legally(events: list, envelope: dict) -> None:
    from ke_state_machine import fold, submit

    object_ctx = {"producer_ids": review_producer_ids(envelope)}
    state = submit(object_ctx, "draft")          # system transition into review
    final, codes = fold(events, object_ctx, initial_state=state)
    decisions = [e["decision"] for e in events]
    expected = "draft" if "request-changes" in decisions else "approved"
    assert final == expected
    assert all(not e.get("touches_epistemic_status") for e in events)
    assert codes


def review_producer_ids(envelope: dict) -> list[str]:
    return envelope["outputs"]["review_report.json"]["producer_ids"]


def test_reviewer_is_independent(envelope: dict, review: dict) -> None:
    from ke_state_machine import is_independent, producer_identity

    ok, basis = is_independent(review["reviewer"],
                              producer_identity({"producer_ids": review_producer_ids(envelope)}))
    assert ok, basis
    assert review["independence"]["ok"] is True
    assert review["independence"]["limitations"], "independence limits must be stated"


def test_no_verification_marking_and_single_report_scope(envelope: dict) -> None:
    """No output value may assert verification; meta prose and rule names may mention it."""
    bad: list[str] = []

    def walk(node: object, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("verification_status", "verified", "verification_ticket") and value:
                    bad.append(f"{path}.{key}")
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f"{path}[{i}]")
        elif isinstance(node, str) and node.strip().lower() in ("verified", "true-verified"):
            bad.append(f"{path}={node!r}")

    walk(envelope, "$")
    assert not bad, bad
    blob = json.dumps(envelope, ensure_ascii=False)
    assert set(re.findall(r'"report_id":\s*"(\d+)"', blob)) == {"4537"}
    ids = set(re.findall(r"reports/(\d{3,})", blob))
    assert ids <= {"4537"}


def test_upstream_locator_audit_passed(review: dict) -> None:
    checks = {c["id"]: c for c in review["checks"]}
    assert checks["F1"]["pass"] and checks["F2"]["pass"] and checks["F4"]["pass"]
    # the completeness gap and the unresolved-mirror must stay visible as failures
    assert checks["F9"]["pass"] is False and "tests/test_v1_readiness.py" in checks["F9"]["detail"]
    assert checks["F10"]["pass"] is False


@pytest.mark.skipif(subprocess.run(["which", "ruff"], capture_output=True).returncode != 0,
                    reason="ruff not installed")
def test_refutation_probe_reproduces(review: dict) -> None:
    """FN-4537-04-03 must be reproducible: `ruff format` splits E701/E702 statements."""
    probe = next(p for p in review["reproduction_probes"] if p["probe"].startswith("R1b"))
    assert probe["verdict"] == "refuted"
    d = Path(tempfile.mkdtemp(prefix="wp4537_04_test_"))
    f = d / "m.py"
    f.write_text("x = 1; y = 2\nif True: pass\n", encoding="utf-8")
    subprocess.run(["ruff", "format", "m.py"], cwd=str(d), capture_output=True, check=True)
    text = f.read_text(encoding="utf-8")
    assert "x = 1; y = 2" not in text and "y = 2" in text
    out = subprocess.run(["ruff", "check", "--select", "E701,E702", "m.py"],
                         cwd=str(d), capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


def test_confirmed_probes_stay_confirmed(review: dict) -> None:
    verdicts = {p["probe"]: p["verdict"] for p in review["reproduction_probes"]}
    assert verdicts["R1a-e701-e702-have-no-lint-fix"] == "confirmed"
    assert verdicts["R2-config-select-vs-cli-select"] == "confirmed"
    assert verdicts["R3-unquoted-colon-in-step-name"] == "confirmed"
    assert verdicts["R4-temp-dir-loses-ruff-config"] == "confirmed"
    # checks that could not run must be declared, never silently assumed to pass
    assert review["checks_not_run"]
    assert review["overstated_claims"]