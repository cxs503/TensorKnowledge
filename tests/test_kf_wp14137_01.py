"""pytest wrapper around the wp-14137-01 acceptance verifier (offline mode, no network).

These tests assert the *contract* invariances of the delivered asset manifest, not the upstream
report's physics: byte-identical source hash, locator resolvability, id uniqueness, claims policy.
Run: python3 -m pytest tests/test_kf_wp14137_01.py -q
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/wp-14137-01"
ART = ROOT / "artifacts/wp-14137-01"
CONTRACT_HASH = "6f65040f0d3483ee5ca35f81c0fa4e5af147165e066e6c9c1cdb9a815faa8c30"


def load(name: str) -> dict:
    return json.loads((ART / name).read_text())


def test_source_hash_matches_contract():
    md = (RUN / "report_14137.md").read_text()
    assert hashlib.sha256(md.encode()).hexdigest() == CONTRACT_HASH
    assert len(md) == 7569  # contract input.chars
    m = load("asset_manifest.json")
    assert m["source"]["hash"] == CONTRACT_HASH
    assert m["source"]["field"] == "markdown"
    assert m["source"]["uri"] == "tensor://reports/14137"


def test_every_locator_resolves_and_is_unique():
    md = (RUN / "report_14137.md").read_text()
    for a in load("asset_manifest.json")["assets"]:
        loc = a["locator"]
        assert md[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        assert md.count(loc["quote"]) == 1, a["asset_id"]
        assert md[:loc["start_char"]].count("\n") == loc["start_line"], a["asset_id"]


def test_ids_unique_and_resolution_enum():
    assets = load("asset_manifest.json")["assets"]
    ids = [a["asset_id"] for a in assets]
    assert len(ids) == len(set(ids))
    assert set(a["resolution"] for a in assets) <= {
        "resolved_in_source", "referenced_unresolved", "declared_absent"}


def test_claims_empty_and_not_verified():
    m = load("asset_manifest.json")
    assert m["claims"] == []
    assert m["integrity"]["registered_not_verified"]
    for a in m["assets"]:
        assert "verified" not in json.dumps(a, ensure_ascii=False).lower()


def test_verifier_full_pass_offline():
    offline_out = ART / "acceptance.offline.json"
    r = subprocess.run([sys.executable, str(ROOT / "scripts/kf_verify_14137.py"),
                        "--offline", "--out", str(offline_out)],
                       cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    # NB: the test must not clobber the deliverable acceptance.json (that is the online run's output)
    acc = json.loads(offline_out.read_text())
    assert acc["failed"] == 0 and acc["passed"] >= 15


def test_docs_mirrors_match_artifacts():
    """artifacts/ is gitignored here, so docs/<package>/ holds the committed copy of every deliverable."""
    docs = ROOT / "docs" / "wp-14137-01"
    for name in ("asset_manifest.json", "acceptance.json", "fig_asset_manifest.png"):
        a, d = (ART / name).read_bytes(), (docs / name).read_bytes()
        assert a == d, name


def test_envelope_shape():
    env = json.loads((RUN / "kf_result.wp-14137-01.json").read_text())
    assert env["package_id"] == "wp-14137-01"
    assert env["task_type"] == "01-asset-registration"
    assert env["report_id"] == "14137"
    assert env["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert env["provenance"]["source_field"] == "markdown"
    assert env["outputs"]["asset_manifest.json"] == load("asset_manifest.json")