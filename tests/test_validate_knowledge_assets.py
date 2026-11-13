"""Tests for the repository gate that runs sediment verifiers.

Regression context (mission 17202): the ``Validate knowledge assets`` CI job was
red on ``main`` because the runner had no ``jsonschema`` installed -- the sediment
verifier died with ``ModuleNotFoundError`` and the gate reported the single line
``verifier ... failed (rc=1)``, indistinguishable from "the asset content is
wrong".  Two properties are pinned here:

* a package's declared python dependencies are probed, so a missing module is
  reported as ``blocked-missing-dependency`` with the install command;
* every non-passing package appears in a failure index with its own status and
  reason, and only a real check failure is reported as ``fail``.

Plus the schema ``version`` rule: a schema that defines ``version`` must pin an
accepted form, and the two legitimate forms (semver string / integer revision
counter) are unit-tested together with the forms that must still be rejected.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_knowledge_assets as validator  # noqa: E402
import validate_sediment_packages as runner  # noqa: E402

RANK = """
import sys
print("PASS  a:ok")
print("{}  b:x")
sys.exit({})
"""


def make_package(tmp_path: Path, *, exit_code: int = 0, status_line: str = "PASS",
                 stdout: str = "", stderr: str = "", requires: list[str] | None = None,
                 entry: Path | None = None) -> Path:
    """Build a synthetic sediment package whose verifier is a tiny script."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    script = entry or (tmp_path / "verifier.py")
    body = stdout or RANK.format(status_line, exit_code)
    if stderr:
        body += f"\nimport sys\nsys.stderr.write({stderr!r})\n"
    script.write_text(body, encoding="utf-8")
    manifest = {
        "package": pkg.name,
        "title": "synthetic fixture package (no domain content)",
        "source": {"sha": "0" * 40, "root_env": "SYNTHETIC_SRC_REPO", "default_root": str(tmp_path / "no-src")},
        "records": {"claims": 0, "evidence": 0, "provenance": 0},
        "entry": {"verifier": str(script)},
        "version": "1.0.0",
    }
    if requires is not None:
        manifest["entry"]["requires"] = requires
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return pkg


# ---------------------------------------------------------------------------
# dependency probe: environment problem != failed asset
# ---------------------------------------------------------------------------
def test_missing_dependency_without_risky_import_blame(tmp_path: Path) -> None:
    pkg = make_package(tmp_path, requires=["no_such_module_for_m17202"])
    res = runner.run_package(pkg)
    assert res["status"] == "blocked-missing-dependency"
    assert res["returncode"] is None
    assert res["missing_requirements"] == ["no_such_module_for_m17202"]
    assert "requirements-validation.txt" in res["reason"]
    assert "no_such_module_for_m17202" in res["reason"]


def test_declared_dependency_present_runs_the_verifier(tmp_path: Path) -> None:
    pkg = make_package(tmp_path, requires=["json"], exit_code=0)
    assert runner.run_package(pkg)["status"] == "pass"


def test_crash_with_module_error_is_attributed_to_the_environment(tmp_path: Path) -> None:
    body = "import no_such_module_for_m17202\n"
    pkg = make_package(tmp_path, entry=tmp_path / "crasher.py", stdout=body)
    res = runner.run_package(pkg)
    assert res["status"] == "blocked-missing-dependency"
    assert res["missing_requirements"] == ["no_such_module_for_m17202"]
    assert "before any check ran" in res["reason"]


# ---------------------------------------------------------------------------
# status classification
# ---------------------------------------------------------------------------
def test_real_check_failure_is_a_failure(tmp_path: Path) -> None:
    pkg = make_package(tmp_path, exit_code=1, status_line="FAIL")
    res = runner.run_package(pkg)
    assert res["status"] == "fail"
    assert res["returncode"] == 1
    assert "1/2 checks failed" in res["reason"]


def test_source_unavailable_is_a_skip_not_a_pass(tmp_path: Path) -> None:
    body = ('print("FAIL  source:available                /x missing; quote/number checks NOT run")\n'
            'raise SystemExit(1)\n')
    pkg = make_package(tmp_path, entry=tmp_path / "skipper.py", stdout=body)
    res = runner.run_package(pkg)
    assert res["status"] == "skipped-source-unavailable"
    assert res["status"] not in runner.FAILING_STATUSES


def test_crash_without_any_check_line_is_reported_as_a_crash(tmp_path: Path) -> None:
    body = 'raise SystemExit("boom: cannot even start")\n'
    pkg = make_package(tmp_path, entry=tmp_path / "silent.py", stdout=body)
    res = runner.run_package(pkg)
    assert res["status"] == "error-verifier-crashed"
    assert "boom: cannot even start" in res["reason"]


def test_gate_stays_red_for_every_non_pass_status() -> None:
    assert set(runner.FAILING_STATUSES) == {
        "fail", "error-verifier-crashed", "blocked-missing-dependency"}
    assert "skipped-source-unavailable" not in runner.FAILING_STATUSES


# ---------------------------------------------------------------------------
# failure index: one red line per asset, never one opaque gate failure
# ---------------------------------------------------------------------------
def test_index_lists_every_failing_asset_with_its_reason(tmp_path: Path) -> None:
    ok = {"package": "good-asset", "status": "pass", "returncode": 0, "reason": "3 checks pass"}
    bad = {"package": "bad-asset", "status": "fail", "returncode": 1, "reason": "1/2 checks failed"}
    blocked = {"package": "blocked-asset", "status": "blocked-missing-dependency",
               "returncode": None, "reason": "missing python module 'jsonschema'"}
    skipped = {"package": "skipped-asset", "status": "skipped-source-unavailable",
               "returncode": 1, "reason": "source absent"}
    results = [ok, bad, blocked, skipped]

    index = runner.render_index(results)
    assert "good-asset" in index and "skipped-asset" in index
    assert "FAILED ASSETS (2):" in index
    assert "  - bad-asset: fail rc=1 :: 1/2 checks failed" in index
    assert "  - blocked-asset: blocked-missing-dependency" in index
    assert "good-asset: pass" not in index.split("FAILED ASSETS", 1)[1]

    summary = runner.summarise(results)
    assert summary["ok"] is False
    assert summary["counts"] == {"pass": 1, "fail": 1,
                                 "blocked-missing-dependency": 1,
                                 "skipped-source-unavailable": 1}
    assert [item["package"] for item in summary["failure_index"]] == ["bad-asset", "blocked-asset"]


def test_gate_is_green_when_every_asset_passes_or_is_source_skipped() -> None:
    results = [{"package": "a", "status": "pass", "returncode": 0, "reason": ""},
               {"package": "b", "status": "skipped-source-unavailable", "returncode": 1, "reason": ""}]
    assert runner.summarise(results)["ok"] is True
    assert "FAILED ASSETS" not in runner.render_index(results)


def test_runner_cli_exit_code_follows_the_failure_index(tmp_path: Path) -> None:
    root = tmp_path / "sediment"
    root.mkdir()
    bad = make_package(tmp_path, exit_code=1, status_line="FAIL")
    (root / "bad").mkdir()
    (root / "bad" / "manifest.json").write_text((bad / "manifest.json").read_text(), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_sediment_packages.py"),
                           "--root", str(root), "--json", str(tmp_path / "index.json")],
                          capture_output=True, text=True, cwd=str(ROOT), timeout=300)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "FAILED ASSETS (1):" in proc.stdout
    payload = json.loads((tmp_path / "index.json").read_text())
    assert payload["summary"]["ok"] is False
    assert payload["summary"]["failure_index"][0]["package"] == "bad"


# ---------------------------------------------------------------------------
# schema version rule
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("version_property", [
    {"type": "string"},
    {"type": "string", "pattern": "^v[0-9]+$"},
    {"type": "string", "pattern": "^[0-9]+\\.[0-9]+$"},
    "1.0.0",
])
def test_loose_version_fields_are_rejected(tmp_path: Path, version_property) -> None:
    errors: list[str] = []
    validator.check_schema_version_rule({"properties": {"version": version_property}},
                                        ROOT / "schemas" / "x.schema.json", errors)
    assert errors, version_property


@pytest.mark.parametrize("version_property", [
    {"type": "string", "pattern": validator.SEMVER_PATTERN},
    {"type": "integer", "minimum": 1},
])
def test_pinned_version_fields_are_accepted(tmp_path: Path, version_property) -> None:
    errors: list[str] = []
    validator.check_schema_version_rule({"properties": {"version": version_property}},
                                        ROOT / "schemas" / "x.schema.json", errors)
    assert errors == []


def test_repository_schemas_satisfy_the_version_rule() -> None:
    """The two dialects in the repo: semver learning assets and RCI revisions."""
    schema_dirs = [ROOT / "schemas", ROOT / "knowledge-map", ROOT / "curriculum"]
    checked = 0
    for directory in schema_dirs:
        for path in sorted(directory.rglob("*.schema.json")):
            errors: list[str] = []
            validator.check_schema_version_rule(json.loads(path.read_text(encoding="utf-8")),
                                                path, errors)
            assert not errors, errors
            checked += 1
    assert checked >= 1


def test_repository_schema_dialects_are_pinned_to_2020_12() -> None:
    for path in sorted((ROOT / "schemas").glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", path.name


# ---------------------------------------------------------------------------
# the sloshing package declares the modules its verifier imports
# ---------------------------------------------------------------------------
def test_sediment_packages_declare_their_verifier_requirements() -> None:
    pkg = ROOT / "knowledge" / "sediment" / "sloshing-impact-lbm"
    manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    requires = manifest["entry"].get("requires", [])
    assert "jsonschema" in requires
    for module in requires:
        assert runner.MODULE_RE.match(module), module
        assert not runner.probe_requirements([module]), f"{module} not importable here"


def test_verify_sediment_reports_a_missing_dependency_as_env_failure(tmp_path: Path) -> None:
    """End-to-end: a verifier whose jsonschema import is blocked says ``env:``.

    ``sediment_lib.SchemaSet`` raises ``DependencyError``; the verifier must turn
    that into an ``env:dependency`` FAIL line (so the runner can label it) rather
    than a bare traceback.
    """
    blocker = tmp_path / "block"
    blocker.mkdir()
    (blocker / "jsonschema.py").write_text(
        "raise ImportError(\"No module named 'jsonschema'\", name='jsonschema')\n", encoding="utf-8")
    env = {"PATH": "/usr/bin:/bin", "PYTHONPATH": str(blocker),
           "SLOSHING_SRC_REPO": str(tmp_path / "no-src")}
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "verify_sediment_sloshing.py"),
                           "--no-write"], capture_output=True, text=True, cwd=str(ROOT),
                          env=env, timeout=600)
    assert proc.returncode == 1
    assert "env:dependency" in proc.stdout
    assert "requirements-validation.txt" in proc.stdout
    assert "traceback" not in proc.stdout.lower()