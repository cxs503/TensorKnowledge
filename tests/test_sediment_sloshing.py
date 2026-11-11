"""Tests for the sloshing-impact sediment package and its re-derivation library.

Two layers:

* **always run** (no source repository needed): recipe unit tests on synthetic
  data, package structure, schema validation, cross-reference/index closure,
  producer discipline, and the claim-literal binding in ``number_checks.json``.
* **source-dependent** (skipped when no ``TensorLBM`` checkout is reachable):
  verbatim quote reproduction, benchmark re-execution, builder determinism.

A skipped test is reported as skipped, never as passed.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import sloshing_reference as REF  # noqa: E402
from sediment_lib import (  # noqa: E402
    Checks,
    SchemaSet,
    check_discipline,
    check_index,
    check_xref,
    load_records,
)

PKG = ROOT / "knowledge" / "sediment" / "sloshing-impact-lbm"
MANIFEST = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))
SOURCE = MANIFEST["source"]
SRC_ROOT = Path(os.environ.get(SOURCE["root_env"], SOURCE["default_root"]))
HAVE_SOURCE = (SRC_ROOT / ".git").exists() or (SRC_ROOT / "HEAD").exists()

needs_source = pytest.mark.skipif(
    not HAVE_SOURCE, reason=f"source repository not available at {SRC_ROOT}"
)


# ---------------------------------------------------------------------------
# recipes (pure numerics, synthetic inputs only)
# ---------------------------------------------------------------------------
def test_omega_exact_matches_classic_formula() -> None:
    value = REF.omega_exact(20.0, 4.0, 9.80665)
    k = math.pi / 20.0
    assert value == pytest.approx(math.sqrt(9.80665 * k * math.tanh(k * 4.0)), rel=0.0, abs=0.0)
    assert value == pytest.approx(0.9262031964108087, rel=1e-14)


def test_swe_ratio_identity_and_monotonicity() -> None:
    for kh in (0.01, 0.1, 0.6283185, 1.0, 5.0):
        assert REF.swe_ratio(kh) == pytest.approx(math.sqrt(kh / math.tanh(kh)), rel=1e-14)
    assert REF.swe_ratio(0.6283185) > REF.swe_ratio(0.5) > REF.swe_ratio(0.1)
    assert REF.swe_ratio(1e-9) == pytest.approx(1.0, rel=1e-6)


def test_kh_for_ratio_inverts_swe_ratio() -> None:
    for target in (1.03, 1.05, 1.10):
        kh = REF.kh_for_ratio(target)
        assert REF.swe_ratio(kh) <= target
        assert REF.swe_ratio(kh * 1.001) > target


def test_bore_reflection_solves_the_shock_condition() -> None:
    depth, g = 4.0, 9.80665
    u_front = REF.u_front(depth, g)
    h_r = REF.bore_reflection_depth(depth, u_front, g)
    # the reflected depth must satisfy the Rankine-Hugoniot condition it was solved for
    assert REF.shock_velocity(depth, h_r, g) == pytest.approx(u_front, rel=1e-10)
    assert h_r / depth == pytest.approx(3.4939592074, rel=1e-9)
    assert REF.bore_reflection_depth(depth, 0.0, g) == depth


def test_bore_reflection_rejects_unreachable_state() -> None:
    with pytest.raises(ValueError):
        REF.bore_reflection_depth(4.0, -1.0)


def test_moving_max_is_a_trailing_average() -> None:
    series = [0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0]
    assert REF.moving_max(series, 2) == pytest.approx(1.0)
    assert REF.moving_max(series, 4) == pytest.approx(0.5)
    with pytest.raises(ValueError):
        REF.moving_max(series, 0)


def test_peak_omega_finds_a_synthetic_sinusoid() -> None:
    omega, dt, n = 1.7, 0.01, 4096
    t = [i * dt for i in range(n)]
    y = [math.sin(omega * t[i]) for i in range(n)]
    found = REF.peak_omega(t, y, (1.2, 2.2))
    assert found["omega"] == pytest.approx(omega, rel=2e-4)


# ---------------------------------------------------------------------------
# package structure / contracts (always run)
# ---------------------------------------------------------------------------
def test_package_files_present() -> None:
    for rel in ("INDEX.md", "manifest.json", "number_checks.json",
                "run/build.json", "run/verification.json", "run/benchmark.json"):
        assert (PKG / rel).is_file(), rel
    assert len(load_records(PKG, "claim")) >= 5
    assert len(load_records(PKG, "evidence")) >= len(load_records(PKG, "claim"))
    assert len(load_records(PKG, "provenance")) == len(load_records(PKG, "claim"))


def test_records_validate_against_schemas() -> None:
    schemas = SchemaSet(ROOT / "schemas")
    for kind in ("claim", "evidence", "provenance"):
        records = load_records(PKG, kind)
        assert records, kind
        errors = [m for m in (schemas.validate(f"{kind}-record.schema.json", r) for r in records) if m]
        assert not errors, errors


def test_cross_references_index_and_discipline() -> None:
    claims, evidences = load_records(PKG, "claim"), load_records(PKG, "evidence")
    checks = Checks()
    check_xref(checks, claims, evidences)
    check_index(checks, PKG, claims, evidences)
    check_discipline(checks, claims, evidences)
    assert checks.ok, checks.failures


def test_every_claim_literal_is_bound_to_a_check() -> None:
    """A number in a claim statement must be bound to a machine-executable check."""
    plan = json.loads((PKG / "number_checks.json").read_text(encoding="utf-8"))
    statements = {c["id"]: c["statement"] for c in load_records(PKG, "claim")}
    assert plan["checks"], "empty plan"
    bound = set()
    for item in plan["checks"]:
        assert item["claim"] in statements, item["claim"]
        for literal in item["literals"]:
            assert literal in statements[item["claim"]], (item["id"], literal, "not in statement")
            bound.add((item["claim"], literal))
    assert len(bound) >= 15
    for item in plan["checks"]:
        # every non-reported-only check must be executable by the verifier
        if not item.get("reported_only"):
            assert item["ref"] or item["recipe"], item["id"]
            assert item["recipe"] in REF.RECIPES, item["id"]


def test_committed_verification_has_no_failures() -> None:
    verification = json.loads((PKG / "run" / "verification.json").read_text(encoding="utf-8"))
    summary = verification["summary"]
    assert summary["n_fail"] == 0, summary["failures"]
    assert summary["n_checks"] == summary["n_pass"]
    assert summary["n_checks"] >= 100
    assert verification["environment"]["partial"] is False


def test_committed_benchmark_is_a_numeric_comparison() -> None:
    bench = json.loads((PKG / "run" / "benchmark.json").read_text(encoding="utf-8"))
    assert bench["n_rederived"] >= 10
    assert bench["n_compared"] >= 10
    assert bench["worst_abs_rel_error"] < 5e-3
    exact = [i for i in bench["items"] if i["rel_error"] is not None and abs(i["rel_error"]) <= 1e-9]
    assert len(exact) >= 10
    for item in bench["items"]:
        if item["verdict"] != "derived-only":
            assert item["ref"] is not None, item["id"]
        if item["rederived"]:
            assert item["got"] is not None, item["id"]
        assert item["verdict"] in ("pass", "reported-only", "derived-only")


# ---------------------------------------------------------------------------
# source-dependent checks
# ---------------------------------------------------------------------------
@needs_source
def test_quotes_reproduce_in_the_pinned_source() -> None:
    from sediment_lib import GitSource, quote_of, quote_sha256

    src = GitSource(SRC_ROOT, SOURCE["sha"])
    for ev in load_records(PKG, "evidence"):
        uri = ev["locator"]["value"]
        path = uri.split(":", 1)[1].rsplit("#", 1)[0]
        span = uri.rsplit("#L", 1)[1]
        first, last = (int(x) for x in span.split("-L"))
        quote = quote_of(src.lines(path), first, last)
        assert quote == ev["locator"]["quote"], ev["id"]
        assert quote_sha256(quote) == ev["locator"]["content_hash"], ev["id"]


@needs_source
def test_verifier_passes_and_builder_is_deterministic(tmp_path: Path) -> None:
    env = dict(os.environ)
    env[SOURCE["root_env"]] = str(SRC_ROOT)
    verify = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_sediment_sloshing.py"), "--no-write"],
        cwd=str(ROOT), capture_output=True, text=True, env=env, timeout=600,
    )
    assert verify.returncode == 0, verify.stdout[-2000:]
    build = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "sediment_sloshing_extract.py"), "--check"],
        cwd=str(ROOT), capture_output=True, text=True, env=env, timeout=600,
    )
    assert build.returncode == 0, build.stderr[-2000:]


@needs_source
def test_package_runner_integrates_the_verifier() -> None:
    import validate_sediment_packages as runner

    before = (PKG / "run" / "verification.json").read_bytes()
    result = runner.run_package(PKG)
    assert result["status"] == "pass", result
    assert result["entry"] == MANIFEST["entry"]["verifier"]
    # a validator must not mutate the committed artefacts
    assert (PKG / "run" / "verification.json").read_bytes() == before