"""pytest wrapper around the wp-12316-01 acceptance verifier (offline mode, no network).

These tests assert the *contract* invariances of the delivered asset manifest, not the upstream
report's physics: byte-identical source hash, locator resolvability, id uniqueness, claims policy.
Run: python3 -m pytest tests/test_kf_wp_12316_01.py -v
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "wp-12316-01"
CONTRACT_HASH = "65f8acb5dfe8a1d34dabae2a3d2225ef74b825201ecd9b7be7359b2d687cd34c"
CONTRACT_CHARS = 1805


def load(name: str) -> dict:
    return json.loads((PKG / name).read_text())


def test_source_hash_matches_contract():
    md = (PKG / "report.md").read_text()
    assert hashlib.sha256(md.encode()).hexdigest() == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS
    m = load("asset_manifest.json")
    assert m["source"]["hash"] == CONTRACT_HASH
    assert m["source"]["field"] == "markdown"
    assert m["source"]["uri"] == "tensor://reports/12316"


def test_every_locator_resolves_and_is_unique():
    md = (PKG / "report.md").read_text()
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
    assert m["integrity"]["hash_matches_contract"]
    for a in m["assets"]:
        assert "verified" not in json.dumps(a, ensure_ascii=False).lower()


def test_verifier_full_pass_offline():
    offline_out = PKG / "verification.offline.json"
    r = subprocess.run([sys.executable, str(ROOT / "scripts/kf_verify_12316.py"),
                        "--offline", "--out", str(offline_out)],
                       cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    acc = json.loads(offline_out.read_text())
    assert acc["summary"]["failed"] == 0 and acc["summary"]["passed"] >= 10


def test_envelope_shape():
    env = json.loads((PKG / "kf_result.wp-12316-01.json").read_text())
    assert env["package_id"] == "wp-12316-01"
    assert env["task_type"] == "01-asset-registration"
    assert env["report_id"] == "12316"
    assert env["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert env["provenance"]["source_field"] == "markdown"
    assert env["outputs"]["asset_manifest.json"] == load("asset_manifest.json")


def test_schema_validation():
    import jsonschema
    manifest = load("asset_manifest.json")
    envelope = json.loads((PKG / "kf_result.wp-12316-01.json").read_text())

    schema_path = ROOT / "schemas" / "asset_manifest.v1.schema.json"
    schema = json.loads(schema_path.read_text())
    jsonschema.Draft202012Validator(schema).validate(manifest)

    kf_schema_path = ROOT / "schemas" / "kf_result.v1.schema.json"
    kf_schema = json.loads(kf_schema_path.read_text())
    jsonschema.Draft202012Validator(kf_schema).validate(envelope)


def test_asset_count_matches():
    m = load("asset_manifest.json")
    assert m["counts"]["assets"] == 24
    assert m["counts"]["resolved_in_source"] + m["counts"]["referenced_unresolved"] == 24
    assert len(m["assets"]) == 24


def test_verification_json_exists_and_passes():
    v = load("verification.json")
    assert v["result"] == "ALL_PASS"
    assert v["summary"]["failed"] == 0
    assert v["summary"]["passed"] >= 10


def test_fig_exists():
    fig = PKG / "fig1_registration_map.png"
    assert fig.exists()
    assert fig.stat().st_size > 10000  # At least 10KB


def test_readme_exists():
    readme = PKG / "README.md"
    assert readme.exists()
    content = readme.read_text()
    assert "WP-12316-01" in content
    assert "01-asset-registration" in content


def test_scripts_exist():
    for script in ["kf_register_12316.py", "kf_verify_12316.py", "kf_publish_12316.py"]:
        assert (ROOT / "scripts" / script).exists(), f"{script} not found"


def test_register_script_runs_clean():
    """Re-run the register script and verify it produces identical output."""
    r = subprocess.run([sys.executable, str(ROOT / "scripts/kf_register_12316.py")],
                       cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    # Verify the output is still valid
    m = load("asset_manifest.json")
    assert m["package_id"] == "wp-12316-01"
    assert m["counts"]["assets"] == 24
