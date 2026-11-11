"""Guard the m5054 sediment package (knowledge/sediment/tk-sediment-m5054).

Three things are worth guarding, in increasing order of strength:

1. the committed package is schema-valid, producer-clean and self-consistent;
2. the committed package is exactly what the extractor produces from
   ``TensorSPH@82b72a15`` — byte-identical rebuild, so the JSON cannot drift away
   from the source pin silently;
3. the machinery is load-bearing rather than decorative: a stale quote must make
   the build fail, and the reference values in the benchmark table must come out
   of the source artifacts, not out of the author's memory.

Checks that need the pinned source checkout are skipped (pytest skip, visible in
the report — never a silent pass) when no checkout carrying 82b72a15 is found.
The negative-control and schema tests run everywhere.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from ke.sediment_extract import (GitPin, QuoteNotFound, build_evidence,  # noqa: E402
                                 build_benchmarks, extract_package)
from ke.sediment_verify import verify  # noqa: E402

PKG = REPO / "knowledge" / "sediment" / "tk-sediment-m5054"
SPEC = PKG / "spec.json"
SCHEMAS = REPO / "schemas"
SHA = "82b72a15c044259d1e7c8d638e9273705fa42e7b"

SPEC_DATA = json.loads(SPEC.read_text(encoding="utf-8"))


def _source_repo() -> Path | None:
    """A checkout that actually carries the pinned commit (or None)."""
    candidates = [os.environ.get("TENSORSPH_REPO"),
                  "/root/tp-agent/work/m5054",
                  SPEC_DATA["source"]["default_path"],
                  "/root/tensor-ecosystem/TensorSPH"]
    for cand in candidates:
        if not cand:
            continue
        repo = Path(cand)
        if not (repo / ".git").exists():
            continue
        probe = subprocess.run(["git", "-C", str(repo), "cat-file", "-e", SHA],
                               capture_output=True)
        if probe.returncode == 0:
            return repo
    return None


SOURCE = _source_repo()
needs_source = pytest.mark.skipif(SOURCE is None,
                                 reason=f"no checkout carrying {SHA[:7]} (source checks NOT_RUN)")


def _package_files() -> list[Path]:
    return sorted(p for p in PKG.rglob("*")
                  if p.is_file() and p.name != "validate_m5054.py"
                  and p.parent.name in {"claims", "evidence", "provenance"}
                  or p in (PKG / "benchmarks.json", PKG / "INDEX.md", PKG / "anchors.json"))


# Paths that make the platform/CI side of the integration explicit: the repo's
# test run executes the package entry point and the writer script, so the code
# under knowledge/sediment/m5054 is called, not merely stored.
ENTRY_SCRIPT = "knowledge/sediment/tk-sediment-m5054/validate_m5054.py"
BUILD_SCRIPT = "scripts/sediment_m5054_build.py"


# --------------------------------------------------------------------------- #
# 1. committed package structure (no source needed)
# --------------------------------------------------------------------------- #
def test_package_shape_and_producer_contract():
    claims = sorted((PKG / "claims").glob("*.json"))
    evidence = sorted((PKG / "evidence").glob("*.json"))
    prov = sorted((PKG / "provenance").glob("*.json"))
    assert len(claims) == 6
    assert len(evidence) >= len(claims)
    assert len(prov) == len(claims)
    assert (PKG / "benchmarks.json").is_file()
    assert (PKG / "INDEX.md").is_file()
    assert not list(PKG.rglob("*review*")), "producer must not write review events"
    for path in claims:
        rec = json.loads(path.read_text(encoding="utf-8"))
        assert rec["epistemic_status"] == "draft"
        assert rec["evidence_refs"]
    for path in evidence:
        rec = json.loads(path.read_text(encoding="utf-8"))
        assert rec["assessment_status"] == "unassessed"
        assert len(rec["locator"]["quote"]) >= 20
        assert rec["locator"]["content_hash"]
    for path in prov:
        rec = json.loads(path.read_text(encoding="utf-8"))
        assert any("5054" in item for item in rec["derived_from"])
        assert rec["activity"]["parameters"]["task_key"] == "tk-sediment-m5054"


def test_evidence_bundle_paths_all_exist():
    """The maturity evidence must point at files that exist, not at intentions."""
    bundle = json.loads((REPO / "docs" / "sediment"
                         / "tk-sediment-m5054-evidence.json").read_text(encoding="utf-8"))
    for key in ("impl_files", "run_artifacts"):
        for path in bundle[key]:
            assert Path(path).is_file(), f"{key}: {path}"
    for key in ("entry", "external_anchor", "report", "rework_of"):
        if key == "rework_of":
            continue
        assert Path(bundle[key]).is_file(), f"{key}: {bundle[key]}"
    assert bundle["benchmark"]["rows"] and bundle["repro_cmd"]


def test_committed_validator_report_passes_or_is_honestly_skipped():
    report_path = REPO / "docs" / "sediment" / "tk-sediment-m5054" / "runs" / "validate" / "validate_report.json"
    if not report_path.is_file():
        pytest.skip("validate_report.json not built in this checkout (run validate_m5054.py)")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["failed"] == 0
    assert report["passed"] >= 8
    if SOURCE is None:  # quote/benchmark checks may only have been skipped, not faked
        assert {r["check"] for r in report["checks"] if r["status"] == "SKIP"} <= {
            "V4 quote-at-pin", "V7 benchmark-rederive"}


def test_source_guard_run_artifact_is_recorded():
    """The honest-FAIL claim must be backed by an executed probe, not a sentence."""
    artifact = REPO / "docs" / "sediment" / "tk-sediment-m5054" / "runs" / "source_guard" / "source_guard.json"
    assert artifact.is_file(), "run scripts/sediment_m5054_source_guard.py"
    data = json.loads(artifact.read_text(encoding="utf-8"))
    assert data["source"]["sha"] == SHA
    assert data["pytest"]["failed"] == 2 and data["pytest"]["passed"] == 1, data["pytest"]
    failed = {c["test"].rsplit("::", 1)[-1] for c in data["pytest"]["cases"]
              if c["status"] == "FAILED"}
    assert failed == {"test_shear_report_meets_its_criteria",
                      "test_hydrostatic_report_meets_its_criteria"}, data["pytest"]["cases"]
    assert data["doc_link_check"]["exists"] is False
    assert data["doc_link_check"]["returncode"] == 128
    assert (artifact.parent / "pytest_output.txt").is_file()


# --------------------------------------------------------------------------- #
# 2. the machinery is load-bearing (negative control, no source needed)
# --------------------------------------------------------------------------- #
@needs_source
def test_stale_quote_aborts_the_build(tmp_path):
    """A spec quote that no longer matches the pin must fail loudly."""
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    claim = spec["claims"][0]
    claim["evidence"][0].pop("line_needle")
    claim["evidence"][0]["quote"] = "kernel_integral = 1.0000000000 (edited by hand)"
    broken = tmp_path / "spec.json"
    broken.write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(QuoteNotFound):
        extract_package(broken, str(SOURCE), tmp_path / "pkg", tmp_path / "run")


# --------------------------------------------------------------------------- #
# 4. delivery paths must survive the push gate
# --------------------------------------------------------------------------- #
def _delivery_paths() -> list[Path]:
    """Every file this mission delivers (package, code, tests, docs, run records)."""
    files = [p for p in PKG.rglob("*") if p.is_file()]
    files += [p for p in (REPO / "ke").glob("sediment_*.py")]
    files += [p for p in (REPO / "scripts").glob("sediment_m5054_*.py")]
    files += [REPO / "tests" / "test_sediment_m5054.py"]
    files += [p for p in (REPO / "docs" / "sediment").rglob("*")
              if p.is_file() and ("runs" in p.parts
                                  or p.name.startswith("tk-sediment-m5054-"))]
    return sorted(set(files))


def test_delivery_paths_survive_the_push_gate():
    """Mirror tp_pusher v5.4/v5.6 path filters (the P2 root cause of the sediment line).

    Two filters silently ate every earlier sediment delivery: top-level ``runs/`` and
    ``artifacts/`` are record areas that never reach GitHub, and any path segment
    ``/m<digits>/`` is dropped as *another mission's* artefact — which is exactly
    what a package named after its source mission (``knowledge/sediment/m5054/``)
    looks like. The package therefore lives under ``tk-sediment-m5054`` (its
    task_key) and the run records under ``docs/``; this test keeps it that way.
    """
    record = re.compile(r"^(artifacts?/|runs/|results[-/]|REPORT_GATE)")
    binary = re.compile(r"\.(db|sqlite3?|png|log)$")
    other_mission = re.compile(r"(?:^|/)m(\d{2,})/")
    my_mission = "14526"
    paths = [str(p.relative_to(REPO)) for p in _delivery_paths()]
    assert len(paths) >= 30, f"too few delivery paths discovered: {paths[:5]}"
    problems = []
    for path in paths:
        if record.search(path):
            problems.append(f"{path}: record area, never pushed")
            continue
        if binary.search(path) and not (path.startswith("docs/")
                                        and path.endswith((".png", ".svg"))):
            problems.append(f"{path}: binary/log dropped outside docs/")
            continue
        others = [m for m in other_mission.findall(path) if m != my_mission]
        if others:
            problems.append(f"{path}: looks like mission {others}'s artefact")
    assert not problems, problems


# --------------------------------------------------------------------------- #
# 3. source-pinned checks
# --------------------------------------------------------------------------- #
@needs_source
def test_committed_package_is_byte_identical_to_a_fresh_build(tmp_path):
    summary = extract_package(SPEC, str(SOURCE), tmp_path / "pkg", tmp_path / "run")
    assert summary["source"]["sha"] == SHA
    fresh = {Path(f["path"]).relative_to(tmp_path / "pkg"): f["sha256"]
             for f in summary["files"]}
    committed = {}
    for path in _package_files():
        committed[path.relative_to(PKG)] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert set(fresh) == set(committed), "package file set drifted from the extractor"
    drift = {str(k): (committed[k], fresh[k]) for k in committed if committed[k] != fresh[k]}
    assert not drift, f"committed package is not reproducible: {drift}"


@needs_source
def test_validator_passes_and_all_checks_execute(tmp_path):
    report = tmp_path / "validate.json"
    proc = subprocess.run([sys.executable, "-m", "ke.sediment_verify",
                           "--package", str(PKG), "--spec", str(SPEC),
                           "--schemas", str(SCHEMAS), "--source-repo", str(SOURCE),
                           "--run-dir", str(REPO / "docs" / "sediment" / "tk-sediment-m5054" / "runs" / "extract"),
                           "--report", str(report)],
                          cwd=REPO, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-2000:]
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["failed"] == 0 and data["skipped"] == 0
    assert {"V4 quote-at-pin", "V7 benchmark-rederive"} <= {c["check"] for c in data["checks"]}


@needs_source
def test_every_quote_resolves_once_at_the_pin():
    pin = GitPin(SOURCE, SHA)
    evidence, _ = build_evidence(SPEC_DATA, pin)
    assert len(evidence) == 21
    for ev in evidence:
        text = pin.blob(ev["locator"]["value"].split("#")[0].split(":")[-1])
        quote = ev["locator"]["quote"]
        assert text[ev["locator"]["start_offset"]:ev["locator"]["end_offset"]] == quote
        assert text.count(quote) == 1


@needs_source
def test_benchmark_references_are_recomputed_not_copied():
    pin = GitPin(SOURCE, SHA)
    table = build_benchmarks(SPEC_DATA, pin)
    rows = {row["id"]: row for row in table["rows"]}
    # analytic reference values, independent of the committed artifact
    assert rows["shear-decay-n24"]["ref"] == pytest.approx(2 * 0.05 * (2 * 3.141592653589793) ** 2,
                                                           rel=1e-12)
    assert rows["hydro-bottom-best"]["ref"] == pytest.approx(1000 * 9.81 * (0.16 - 0.01 / 2),
                                                             rel=1e-12)
    assert rows["kernel-integral"]["ref"] == 1.0
    assert rows["kernel-second-moment"]["ref"] == 6.0
    # and the artifact numbers they are compared against
    assert rows["shear-decay-n24"]["rel_error_pct"] == pytest.approx(-2.6775, abs=1e-3)
    assert rows["shear-decay-n12"]["rel_error_pct"] == pytest.approx(-12.620, abs=1e-3)
    assert rows["hydro-bottom-best"]["rel_error_pct"] == pytest.approx(-2.7476, abs=1e-3)
    assert rows["hydro-bottom-tait"]["rel_error_pct"] == pytest.approx(-25.229, abs=1e-2)
    assert rows["lattice-second-moment-K"]["rel_error_pct"] == pytest.approx(17.3427, abs=1e-3)
    assert table["summary"]["rows_outside_tolerance"] == [
        "shear-raw-n20", "shear-renorm-n20", "hydro-bottom-tait",
        "hydro-core-max", "lattice-second-moment-K"]


@needs_source
def test_committed_benchmark_table_matches_recomputation():
    pin = GitPin(SOURCE, SHA)
    fresh = build_benchmarks(SPEC_DATA, pin)
    committed = json.loads((PKG / "benchmarks.json").read_text(encoding="utf-8"))
    assert committed["rows"] == fresh["rows"]
    assert committed["summary"] == fresh["summary"]


@needs_source
def test_build_entry_point_runs_end_to_end(tmp_path):
    """The writer script is a real entry point: run it, then check its artifacts."""
    proc = subprocess.run([sys.executable, BUILD_SCRIPT,
                           "--source-repo", str(SOURCE),
                           "--out", str(tmp_path / "pkg"),
                           "--run-dir", str(tmp_path / "run")],
                          cwd=REPO, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    assert (tmp_path / "run" / "run_manifest.json").is_file()
    assert (tmp_path / "run" / "extract.txt").is_file()
    assert len(list((tmp_path / "pkg" / "claims").glob("*.json"))) == 6
    # and the committed package entry point verifies the fresh copy
    verify_proc = subprocess.run([sys.executable, ENTRY_SCRIPT,
                                  "--package", str(tmp_path / "pkg"),
                                  "--spec", str(SPEC),
                                  "--schemas", str(SCHEMAS),
                                  "--source-repo", str(SOURCE),
                                  "--run-dir", str(tmp_path / "run"),
                                  "--report", str(tmp_path / "validate.json")],
                                 cwd=REPO, capture_output=True, text=True)
    assert verify_proc.returncode == 0, verify_proc.stdout[-2000:]
    assert "checks passed" in verify_proc.stdout


@needs_source
def test_validator_catches_a_tampered_quote(tmp_path):
    """The verifier must fail on a doctored package, otherwise it proves nothing."""
    pkg = tmp_path / "pkg"
    shutil.copytree(PKG, pkg)
    victim = sorted((pkg / "evidence").glob("*.json"))[0]
    rec = json.loads(victim.read_text(encoding="utf-8"))
    rec["locator"]["quote"] = rec["locator"]["quote"].replace("a", "e", 1)
    victim.write_text(json.dumps(rec, indent=2), encoding="utf-8")
    rep = verify(pkg, SPEC, SCHEMAS, str(SOURCE), REPO / "docs" / "sediment"
                 / "tk-sediment-m5054" / "runs" / "extract")
    assert rep.failed, "tampered quote slipped through"
    assert any(c["check"] == "V4 quote-at-pin" for c in rep.failed)


@needs_source
def test_verify_reports_the_package_clean():
    rep = verify(PKG, SPEC, SCHEMAS, str(SOURCE), REPO / "docs" / "sediment" / "tk-sediment-m5054" / "runs" / "extract")
    assert not rep.failed, rep.failed
    assert not rep.skipped, rep.skipped
    assert len(rep.passed) == 10