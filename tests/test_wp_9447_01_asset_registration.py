"""wp-9447-01 (task type ``01-asset-registration``) — matured mission deliverables.

The contract under test is :mod:`ke.mission_assets`: a finished mission's
deliverables become immutable knowledge objects **only** when they are matured
(``evidence_grade == REAL``, acceptance note stated, bytes hashable and inside
the package directory), and even then they are born ``in_review`` so that
:func:`ke.assets.record_review` — not the producer — publishes them.

Every store-touching test runs on both backends (``sqlite`` and ``pg``) through
the shared :mod:`tests.conftest` factory ``new_conn``, so "the registration
contract is backend-neutral" is machine-checked rather than promised.

Coverage map (one test per acceptance item):

* ``valid_json`` / report shape ................. test_report_shape_and_witness
* ``sha256_matches_bytes`` (no caller trust) .... test_hash_is_recomputed_not_trusted
* ``schema_pass`` (in_review, never self-published) test_versions_born_in_review
* ``no_duplicate_ids`` ......................... test_duplicate_ids_rejected
* ``source_locator_resolvable`` ................ test_missing_file_and_traversal_rejected
* ``maturity_gate`` ............................ test_non_matured_grades_rejected
* ``build_artefact_gate`` ...................... test_bytecode_artefacts_rejected
* ``immutability`` ............................. test_reconfigured_bytes_raise
* ``idempotency`` .............................. test_rerun_is_idempotent
* ``batch_all_or_nothing`` ..................... test_failed_batch_writes_nothing
* ``drift_detection`` .......................... test_verify_detects_drift_and_missing
* ``cli`` ...................................... test_cli_roundtrip
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ke import assets, mission_assets  # noqa: E402

MISSION = "m9447"


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def package(tmp_path) -> Path:
    """A miniature mission package with two matured deliverables."""
    pkg = tmp_path / "pkg"
    (pkg / "docs").mkdir(parents=True)
    (pkg / "artifacts").mkdir()
    (pkg / "docs" / "result.md").write_text("# result\nresistance +2.1%\n", encoding="utf-8")
    (pkg / "artifacts" / "wave.json").write_text('{"amplitude": 0.41}\n', encoding="utf-8")
    return pkg


def _spec(path: str, deliverable_id: str, **over) -> dict:
    spec = {
        "deliverable_id": deliverable_id,
        "title": f"Deliverable {deliverable_id}",
        "path": path,
        "evidence_grade": "REAL",
        "acceptance": "acceptance: pytest green + reference delta < 3%",
    }
    spec.update(over)
    return spec


def _two(package: Path) -> list[dict]:
    return [_spec("docs/result.md", "result"),
            _spec("artifacts/wave.json", "wave")]


def _register(conn, specs, package, **kwargs):
    return mission_assets.register_matured_deliverables(
        conn, MISSION, specs, base_dir=package, **kwargs
    )


# ---------------------------------------------------------------------------
# happy path / report
# ---------------------------------------------------------------------------
def test_report_shape_and_witness(new_conn, package):
    conn = new_conn()
    report = _register(conn, _two(package), package)
    conn.commit()

    assert report["schema"] == "mission-assets-report.v1"
    assert report["mission_id"] == MISSION
    assert report["state"] == "in_review"
    assert report["counts"] == {"deliverables": 2, "registered": 2,
                                "skipped_idempotent": 0}
    assert report["registered"] == ["mission.m9447.result:v1.0.0",
                                    "mission.m9447.wave:v1.0.0"]
    assert json.loads(json.dumps(report)) == report  # JSON-serialisable

    # the witness binds every (ko_id, bytes) pair of the batch
    expected = assets.sha256_json(sorted(
        [[e["ko_id"], e["sha256"]] for e in report["entries"]]
    ))
    assert report["batch_sha256"] == expected
    assert all(len(e["sha256"]) == 64 for e in report["entries"])


def test_hash_is_recomputed_not_trusted(new_conn, package):
    """A caller-supplied digest is ignored; the registry pins real bytes."""
    conn = new_conn()
    bogus = {**_spec("docs/result.md", "result"), "sha256": "0" * 64}
    report = _register(conn, [bogus], package)
    stored = assets.get_ko_version(conn, report["registered"][0])

    real = mission_assets.sha256_file(package / "docs" / "result.md")
    assert stored["content"]["sha256"] == real != "0" * 64
    assert stored["source_file"] == "docs/result.md"
    assert stored["content"]["size"] == (package / "docs" / "result.md").stat().st_size


def test_versions_born_in_review(new_conn, package):
    """Producer registration is not publication: only a review event publishes."""
    conn = new_conn()
    report = _register(conn, _two(package), package)
    for vid in report["registered"]:
        row = assets.get_ko_version(conn, vid)
        assert row["state"] == "in_review"
        assert row["object_type"] == "mission-deliverable"
        assert row["content"]["schema"] == mission_assets.SCHEMA
        assert row["content"]["mission_id"] == MISSION
    # no review event exists yet -> the asset layer cannot report it published
    assert assets.get_review_events(conn) == []

    assets.record_review(conn, report["registered"][0], "approve",
                         reviewer={"kind": "agent", "id": "reviewer-1"},
                         rationale="acceptance verified")
    assert assets.get_ko_version(conn, report["registered"][0])["state"] == "published"


def test_draft_birth_allowed_but_published_forbidden(new_conn, package):
    conn = new_conn()
    report = _register(conn, _two(package), package, state="draft")
    assert assets.get_ko_version(conn, report["registered"][0])["state"] == "draft"
    with pytest.raises(ValueError, match="publishing requires a review decision"):
        _register(conn, _two(package), package, state="published")


# ---------------------------------------------------------------------------
# idempotency + immutability
# ---------------------------------------------------------------------------
def test_rerun_is_idempotent(new_conn, package):
    conn = new_conn()
    first = _register(conn, _two(package), package)
    second = _register(conn, _two(package), package)
    assert second["registered"] == []
    assert second["skipped_idempotent"] == first["registered"]
    assert second["counts"] == {"deliverables": 2, "registered": 0,
                                "skipped_idempotent": 2}
    assert second["batch_sha256"] == first["batch_sha256"]
    assert len(assets.list_ko_versions(conn)) == 2


def test_reconfigured_bytes_raise(new_conn, package):
    conn = new_conn()
    _register(conn, _two(package), package)
    (package / "docs" / "result.md").write_text("# result\nresistance +9.9%\n",
                                               encoding="utf-8")
    with pytest.raises(ValueError, match="immutability violation"):
        _register(conn, _two(package), package)
    # a version bump is the sanctioned path
    bumped = _register(conn, _two(package), package, version="1.0.1")
    assert bumped["registered"] == ["mission.m9447.result:v1.0.1",
                                   "mission.m9447.wave:v1.0.1"]
    lineage = assets.get_ko_lineage(conn, "mission.m9447.result")
    assert [r["version"] for r in lineage] == ["1.0.0", "1.0.1"]


# ---------------------------------------------------------------------------
# maturity gate
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("grade", ["MOCK", "STUB", "WITHHELD", "NOT_SUPPORTED"])
def test_non_matured_grades_rejected(new_conn, package, grade):
    conn = new_conn()
    specs = [_spec("docs/result.md", "result", evidence_grade=grade)]
    with pytest.raises(mission_assets.DeliverableError) as err:
        _register(conn, specs, package)
    assert any("is not a matured grade" in p for p in err.value.problems)
    assert assets.list_ko_versions(conn) == []


def test_unknown_grade_rejected(new_conn, package):
    conn = new_conn()
    with pytest.raises(mission_assets.DeliverableError) as err:
        _register(conn, [_spec("docs/result.md", "result", evidence_grade="GREEN")],
                  package)
    assert any("not in [" in p for p in err.value.problems)


def test_failed_batch_writes_nothing(new_conn, package):
    """One MOCK deliverable poisons the batch: all-or-nothing, no partial rows."""
    conn = new_conn()
    specs = [_spec("docs/result.md", "result"),
             _spec("artifacts/wave.json", "wave", evidence_grade="MOCK")]
    with pytest.raises(mission_assets.DeliverableError):
        _register(conn, specs, package)
    assert assets.list_ko_versions(conn) == []
    assert mission_assets.mission_deliverable_report(conn, MISSION)["count"] == 0


# ---------------------------------------------------------------------------
# structural rejections
# ---------------------------------------------------------------------------
def test_bytecode_artefacts_rejected(new_conn, package):
    """The closed PR#167 shipped ``__pycache__/*.pyc``; they are not deliverables."""
    conn = new_conn()
    cache = package / "ke" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "store.cpython-311.pyc").write_bytes(b"\x00\x01binary")
    with pytest.raises(mission_assets.DeliverableError) as err:
        _register(conn, [_spec("ke/__pycache__/store.cpython-311.pyc", "pyc")], package)
    assert any("build artefact" in p for p in err.value.problems)


def test_missing_file_and_traversal_rejected(new_conn, package, tmp_path):
    conn = new_conn()
    outside = tmp_path / "outside.md"
    outside.write_text("secret\n", encoding="utf-8")
    with pytest.raises(mission_assets.DeliverableError) as err:
        _register(conn, [_spec("docs/nope.md", "nope"),
                        _spec("../outside.md", "escape")], package)
    problems = " ".join(err.value.problems)
    assert "docs/nope.md" in problems and "not a file" in problems
    assert "escapes base_dir" in problems
    assert assets.list_ko_versions(conn) == []


def test_duplicate_ids_rejected(new_conn, package):
    conn = new_conn()
    specs = [_spec("docs/result.md", "result"), _spec("artifacts/wave.json", "result")]
    with pytest.raises(mission_assets.DeliverableError) as err:
        _register(conn, specs, package)
    assert any("duplicated in batch" in p for p in err.value.problems)


def test_acceptance_and_id_required(new_conn, package):
    conn = new_conn()
    with pytest.raises(mission_assets.DeliverableError) as err:
        _register(conn, [
            _spec("docs/result.md", "result", acceptance=""),
            _spec("artifacts/wave.json", "Bad Id"),
            {"title": "no path", "evidence_grade": "REAL", "acceptance": "x"},
        ], package)
    problems = " ".join(err.value.problems)
    assert "acceptance criterion" in problems
    assert "must match" in problems
    assert "path: must be a non-empty relative path" in problems


def test_mission_id_validated(new_conn, package):
    conn = new_conn()
    with pytest.raises(ValueError, match="mission_id"):
        mission_assets.register_matured_deliverables(
            conn, "M 9447", _two(package), base_dir=package)


# ---------------------------------------------------------------------------
# mission index + drift verification
# ---------------------------------------------------------------------------
def test_mission_report_scopes_and_orders(new_conn, package):
    conn = new_conn()
    _register(conn, _two(package), package)
    _register(conn, [_spec("docs/result.md", "result")], package, version="1.1.0")
    mission_assets.register_matured_deliverables(
        conn, "other", [_spec("docs/result.md", "result")], base_dir=package)

    report = mission_assets.mission_deliverable_report(conn, MISSION)
    assert report["count"] == 2  # other mission's KO is not mixed in
    by_id = {e["ko_id"]: e for e in report["deliverables"]}
    assert by_id["mission.m9447.result"]["version"] == "1.1.0"  # newest wins
    assert by_id["mission.m9447.wave"]["version"] == "1.0.0"
    assert report["states"] == {"in_review": 2}


def test_verify_detects_drift_and_missing(new_conn, package):
    conn = new_conn()
    _register(conn, _two(package), package)

    clean = mission_assets.verify_mission_deliverables(conn, MISSION, base_dir=package)
    assert clean["ok"] is True
    assert clean["counts"] == {"ok": 2, "drift": 0, "missing": 0}

    (package / "docs" / "result.md").write_text("edited after registration\n",
                                               encoding="utf-8")
    (package / "artifacts" / "wave.json").unlink()
    dirty = mission_assets.verify_mission_deliverables(conn, MISSION, base_dir=package)
    assert dirty["ok"] is False
    assert dirty["counts"] == {"ok": 0, "drift": 1, "missing": 1}
    status = {e["path"]: e["status"] for e in dirty["entries"]}
    assert status == {"docs/result.md": "drift", "artifacts/wave.json": "missing"}


# ---------------------------------------------------------------------------
# CLI (sqlite, subprocess: the documented operator path)
# ---------------------------------------------------------------------------
def test_cli_roundtrip(package, tmp_path):
    db = tmp_path / "ke.db"
    specs = tmp_path / "deliverables.json"
    specs.write_text(json.dumps(_two(package)), encoding="utf-8")
    base = [sys.executable, "-m", "ke.cli", "assets"]

    def run(*args):
        return subprocess.run([*base, *args, "--db", str(db)], cwd=REPO,
                              capture_output=True, text=True)

    reg = run("register-mission", MISSION, "--deliverables", str(specs),
              "--base-dir", str(package))
    assert reg.returncode == 0, reg.stderr
    payload = json.loads(reg.stdout)
    assert payload["counts"]["registered"] == 2

    rep = run("mission-report", MISSION)
    assert rep.returncode == 0, rep.stderr
    assert json.loads(rep.stdout)["count"] == 2

    ok = run("verify-mission", MISSION, "--base-dir", str(package))
    assert ok.returncode == 0 and json.loads(ok.stdout)["ok"] is True

    (package / "docs" / "result.md").write_text("drifted\n", encoding="utf-8")
    bad = run("verify-mission", MISSION, "--base-dir", str(package))
    assert bad.returncode == 1
    assert json.loads(bad.stdout)["counts"]["drift"] == 1

    mock = tmp_path / "mock.json"
    mock.write_text(json.dumps([_spec("docs/result.md", "m", evidence_grade="MOCK")]),
                    encoding="utf-8")
    refused = run("register-mission", MISSION, "--deliverables", str(mock),
                  "--base-dir", str(package))
    assert refused.returncode == 1
    assert "is not a matured grade" in refused.stderr