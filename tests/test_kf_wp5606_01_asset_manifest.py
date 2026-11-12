"""Acceptance test for KF work package wp-5606-01 (asset registration).

Runs the independent verifier against the delivered artifacts, and a negative
control that tampers with one locator quote to prove the verifier can actually
FAIL (no negative control ⇒ no gate).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PKG = REPO_ROOT / "runs" / "wp-5606-01"
VERIFY = PKG / "verify_wp5606_01.py"
ENVELOPE = PKG / "kf_result.json"
MANIFEST = PKG / "asset_manifest.json"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VERIFY), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def test_artifacts_exist():
    assert VERIFY.is_file() and ENVELOPE.is_file() and MANIFEST.is_file()


def test_envelope_structure():
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    assert set(env) <= {
        "package_id",
        "task_type",
        "report_id",
        "provenance",
        "outputs",
        "claims",
    }
    assert env["package_id"] == "wp-5606-01"
    assert env["report_id"] == "5606"
    assert env["provenance"]["source_field"] == "markdown"
    assert "asset_manifest.json" in env["outputs"]
    assert env["claims"] == []


def test_verifier_passes_on_delivery():
    proc = _run()
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = json.loads(proc.stdout)
    assert out["status"] == "PASS"
    assert out["hash_matches_contract"] is True
    assert out["locators_failed"] == []


def test_negative_control_tampered_quote_fails(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    item = manifest["attachments"]["items"][0]
    item["locator"]["quote"] = "引文被篡改，原文不存在这一行"
    bad = tmp_path / "asset_manifest.json"
    bad.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    proc = _run("--manifest", str(bad))
    assert proc.returncode != 0, "tampered locator must be rejected"
    out = json.loads(proc.stdout)
    assert out["status"] == "FAIL"
    assert any(e.startswith("1 locator") for e in out["errors"])


def test_negative_control_hash_drift_fails(tmp_path):
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    env["provenance"]["source_hash"] = "sha256:" + "0" * 64
    bad = tmp_path / "kf_result.json"
    bad.write_text(json.dumps(env, ensure_ascii=False, indent=2), encoding="utf-8")
    proc = _run("--envelope", str(bad))
    assert proc.returncode != 0, "source-hash drift must be rejected"
    out = json.loads(proc.stdout)
    assert out["hash_matches_provenance"] is False