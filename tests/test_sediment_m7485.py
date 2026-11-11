"""Guard test for the sediment package ``knowledge/sediment/m7485``.

Runs the *independent* verifier (``scripts/verify_sediment_m7485.py``) against
the written package.  The verifier re-fetches every cited blob by sha out of the
TensorBEM git object store, so the test skips (rather than fails) when that
checkout — or the mission-7485 commit — is not reachable from the machine, e.g.
on a plain GitHub CI runner.

The point of the test: a later edit to the package (rewritten quotation, edited
number, dropped review marker) cannot pass silently; it must either pass the
sha-level re-extraction or fail here.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
VERIFIER = SCRIPTS / "verify_sediment_m7485.py"
PACKAGE = REPO_ROOT / "knowledge" / "sediment" / "m7485"
SOURCE_REPO = Path(os.environ.get("M7485_SRC_REPO", "/root/tp-agent/work/m7485"))
SOURCE_SHA = "80ad52a8236030e2343d5a88131bea3190088c09"


def _source_reachable() -> bool:
    if not (SOURCE_REPO / ".git").exists():
        return False
    proc = subprocess.run(
        ["git", "-C", str(SOURCE_REPO), "cat-file", "-e", f"{SOURCE_SHA}^{{commit}}"],
        capture_output=True,
    )
    return proc.returncode == 0


def _load_verifier():
    spec = importlib.util.spec_from_file_location("verify_sediment_m7485", VERIFIER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_package_exists():
    assert PACKAGE.is_dir(), f"missing sediment package: {PACKAGE}"
    assert list(PACKAGE.glob("claim-*.json")), "no claim records"
    assert list(PACKAGE.glob("evidence-*.json")), "no evidence records"
    assert list(PACKAGE.glob("provenance-*.json")), "no provenance records"
    assert (PACKAGE / "INDEX.md").is_file(), "no INDEX.md"


@pytest.mark.skipif(not _source_reachable(),
                    reason="TensorBEM@80ad52a not reachable (set M7485_SRC_REPO)")
def test_package_verifies_against_source_sha(capsys):
    module = _load_verifier()
    exit_code = module.main()
    out = capsys.readouterr().out
    failed = [ln for ln in out.splitlines() if ln.startswith("FAIL")]
    assert exit_code == 0, "verifier failed:\n" + "\n".join(failed)
    assert "checks passed" in out


def test_no_review_event_and_draft_status():
    """Producer must not have self-reviewed: 0 review events, draft fold only."""
    import json

    assert not list(PACKAGE.glob("review-event*.json"))
    status = json.loads((PACKAGE / "review-status.json").read_text(encoding="utf-8"))
    assert status["review_status"] == "draft"
    assert status["promoted"] is False
    assert status["producer_self_review"] is False
    for path in PACKAGE.glob("evidence-*.json"):
        rec = json.loads(path.read_text(encoding="utf-8"))
        assert rec["assessment_status"] == "unassessed", path.name