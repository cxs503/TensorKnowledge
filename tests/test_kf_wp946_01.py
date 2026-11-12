"""Adversarial tests for the wp-946-01 asset-registration deliverable.

The point is not "the validator printed PASS" but "the validator fails when the
deliverable is broken". Each negative case copies the deliverable into tmp_path,
tampers with exactly one property, and asserts the validator exits non-zero
with the expected check flipped to FAIL.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WP_DIR = REPO_ROOT / "docs" / "kf" / "wp-946-01"
SCHEMA = REPO_ROOT / "schemas" / "kf_result.v1.schema.json"
VALIDATOR = WP_DIR / "validate_asset_manifest.py"


def _run(home: Path) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), str(home), str(SCHEMA)],
        capture_output=True,
        text=True,
    )
    sc = json.loads((home / "selfcheck.json").read_text(encoding="utf-8"))
    return proc.returncode, sc


@pytest.fixture()
def workdir(tmp_path: Path) -> Path:
    dst = tmp_path / "wp-946-01"
    shutil.copytree(WP_DIR, dst)
    return dst


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _dump(p: Path, obj) -> None:
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def test_deliverable_passes_all_checks(workdir: Path):
    rc, sc = _run(workdir)
    assert rc == 0, sc["failures"]
    assert sc["pass"] is True
    assert sc["failures"] == []
    # the checks must be substantive, not a single tautology
    assert len(sc["checks"]) >= 10
    assert sc["markdown_locators_verified"] >= 20
    assert sc["record_locators_verified"] >= 10


def test_source_hash_is_the_contract_hash(workdir: Path):
    sc = _run(workdir)[1]
    assert sc["checks"]["source_hash_matches"]["detail"]["recomputed"] == (
        "sha256:3ea029afd6df49a8d3e407e42df035654b58a7555f9678d657f5fdfc1fe35552"
    )


def test_detects_tampered_quote(workdir: Path):
    p = workdir / "asset_manifest.json"
    man = _load(p)
    man["assets"][0]["locators"][0]["quote"] += " (hand edited)"
    _dump(p, man)
    env = _load(workdir / "kf_result.json")
    env["outputs"]["asset_manifest.json"] = man
    _dump(workdir / "kf_result.json", env)
    rc, sc = _run(workdir)
    assert rc == 1
    assert sc["checks"]["source_locator_resolvable"]["pass"] is False


def test_detects_shifted_span(workdir: Path):
    p = workdir / "asset_manifest.json"
    man = _load(p)
    man["assets"][3]["locators"][0]["char_start"] += 1
    _dump(p, man)
    env = _load(workdir / "kf_result.json")
    env["outputs"]["asset_manifest.json"] = man
    _dump(workdir / "kf_result.json", env)
    rc, sc = _run(workdir)
    assert rc == 1
    assert sc["checks"]["source_locator_resolvable"]["pass"] is False


def test_detects_duplicate_ids(workdir: Path):
    p = workdir / "asset_manifest.json"
    man = _load(p)
    man["assets"][1]["asset_id"] = man["assets"][0]["asset_id"]
    _dump(p, man)
    env = _load(workdir / "kf_result.json")
    env["outputs"]["asset_manifest.json"] = man
    _dump(workdir / "kf_result.json", env)
    rc, sc = _run(workdir)
    assert rc == 1
    assert sc["checks"]["no_duplicate_ids"]["pass"] is False


def test_detects_source_mutation(workdir: Path):
    p = workdir / "source" / "report_946.json"
    rec = _load(p)
    rec["markdown"] = rec["markdown"].replace("42", "43", 1)
    _dump(p, rec)
    rc, sc = _run(workdir)
    assert rc == 1
    assert sc["checks"]["source_hash_matches"]["pass"] is False


def test_detects_unresolved_asset_without_reason(workdir: Path):
    p = workdir / "asset_manifest.json"
    man = _load(p)
    victim = next(a for a in man["assets"] if not a["resolvable"])
    victim.pop("unresolved_reason")
    _dump(p, man)
    env = _load(workdir / "kf_result.json")
    env["outputs"]["asset_manifest.json"] = man
    _dump(workdir / "kf_result.json", env)
    rc, sc = _run(workdir)
    assert rc == 1
    assert sc["checks"]["all_unresolved_have_reason"]["pass"] is False


def test_detects_self_verification_mark(workdir: Path):
    p = workdir / "asset_manifest.json"
    man = _load(p)
    man["verification"] = {"performed": True, "reason": "self certified"}
    _dump(p, man)
    env = _load(workdir / "kf_result.json")
    env["outputs"]["asset_manifest.json"] = man
    _dump(workdir / "kf_result.json", env)
    rc, sc = _run(workdir)
    assert rc == 1
    assert sc["checks"]["no_self_verification"]["pass"] is False


def test_detects_claim_without_evidence(workdir: Path):
    p = workdir / "kf_result.json"
    env = _load(p)
    env["claims"] = [{"claim_id": "C-x", "text": "unsupported", "status": "supported"}]
    _dump(p, env)
    rc, sc = _run(workdir)
    assert rc == 1
    assert sc["checks"]["all_claims_have_evidence_or_explicit_unresolved_status"]["pass"] is False


def test_detects_envelope_schema_violation(workdir: Path):
    p = workdir / "kf_result.json"
    env = _load(p)
    env["provenance"]["source_hash"] = "md5:deadbeef"  # violates pattern
    _dump(p, env)
    rc, sc = _run(workdir)
    assert rc == 1
    assert sc["checks"]["schema_pass"]["pass"] is False


def test_report_id_scope_is_single(workdir: Path):
    p = workdir / "asset_manifest.json"
    man = _load(p)
    man["scope"]["reports_touched"].append("941")
    _dump(p, man)
    env = _load(workdir / "kf_result.json")
    env["outputs"]["asset_manifest.json"] = man
    _dump(workdir / "kf_result.json", env)
    rc, sc = _run(workdir)
    assert rc == 1
    assert sc["checks"]["scope_single_report"]["pass"] is False