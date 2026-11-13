"""Contract checks for KF work package wp-736-01 (asset registration, report 736).

Two tiers:

* offline: the pinned manifest/result artefacts are internally consistent
  (hash pins, unique ids, locator shape, empty claims, output digest).
* live (skipped without agent credentials): re-fetch the report and replay
  every locator against the fetched markdown.

Run::

    python3 -m pytest tests/test_kf_wp736_01_asset_manifest.py -q
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "kf" / "wp-736-01"
MANIFEST = OUT / "asset_manifest.json"
RESULT = OUT / "kf_result_wp-736-01.json"
SCRIPT = REPO / "scripts" / "kf_wp736_01_asset_manifest.py"

CONTRACT_HASH = "sha256:9726d9bcd05657bd5cf0833a4c47a855d683bc5c5ae19b89f6ca49af4b945ef0"
CONTRACT_CHARS = 8500


def _load(path: Path) -> dict:
    assert path.is_file(), f"missing artefact {path}"
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def manifest() -> dict:
    return _load(MANIFEST)


@pytest.fixture(scope="module")
def result() -> dict:
    return _load(RESULT)


def test_result_contract_fields(result: dict) -> None:
    assert set(result) == {"package_id", "task_type", "report_id", "provenance", "outputs"}
    assert result["package_id"] == "wp-736-01"
    assert result["task_type"] == "01-asset-registration"
    assert result["report_id"] == "736"
    assert result["provenance"]["source_uri"] == "tensor://reports/736"
    assert result["provenance"]["source_field"] == "markdown"


def test_source_hash_pinned(result: dict, manifest: dict) -> None:
    assert result["provenance"]["source_hash"] == CONTRACT_HASH
    assert manifest["source"]["hash"]["value"] == CONTRACT_HASH
    assert manifest["source"]["hash"]["matches_contract"] is True
    assert manifest["source"]["size"]["chars"] == CONTRACT_CHARS


def test_output_digest_matches_file(result: dict, manifest: dict) -> None:
    declared = result["outputs"]["asset_manifest.json"]
    path = REPO / declared["path"]
    actual = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    # the result pins the manifest bytes exactly as delivered: any hand edit to
    # the manifest without regenerating the result is caught here.
    assert actual == declared["sha256"]
    assert declared["assets"] == manifest["asset_count"]
    assert declared["claims"] == 0


def test_no_duplicate_ids(manifest: dict) -> None:
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert manifest["asset_count"] == len(ids)


def test_claims_empty_by_contract(manifest: dict) -> None:
    assert manifest["claims"] == []
    assert manifest["verification"]["marked_verified_claims"] == 0


def test_every_asset_has_locator_and_status(manifest: dict) -> None:
    for asset in manifest["assets"]:
        loc = asset["locator"]
        assert loc["field"] == "markdown"
        assert isinstance(loc["quote"], str) and loc["quote"]
        assert 0 <= loc["char_start"] < loc["char_end"]
        assert loc["char_end"] - loc["char_start"] == len(loc["quote"])
        assert asset["status"] in {"registered", "unresolved", "present_on_host"}
        if asset["status"] == "registered":
            assert asset["hash"]["value"].startswith("sha256:")
        else:
            # unresolved assets must say why (no silent gaps)
            assert asset.get("unresolved_reason") or asset.get("reason")
        assert asset["extraction"]["performed"] is False


def test_no_asset_marked_verified(manifest: dict) -> None:
    assert not [a for a in manifest["assets"] if a.get("status") == "verified"]


def test_figures_registered_as_declared_not_fetched(manifest: dict) -> None:
    figs = [a for a in manifest["assets"] if a["kind"] == "figure"]
    assert len(figs) == 2
    for fig in figs:
        assert fig["payload_status"] == "declared_not_fetched"
        assert fig["caption"]  # caption registered verbatim from report metadata
        assert fig["payload_probe"]["http_status"] == 404  # bytes genuinely unavailable


LIVE = bool(os.environ.get("TENSOR_API_BASE") and os.environ.get("TENSOR_AGENT_USER"))


@pytest.mark.skipif(not LIVE, reason="needs TENSOR_API_BASE + agent credentials")
def test_live_replay_locators() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--verify", "--out", str(OUT)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "locators resolve" in proc.stdout