"""Gate tests for KF work package wp-12866-01 (01-asset-registration, report_id=12866).

Every acceptance item of the work-package contract is asserted against the committed
artifacts (no network needed). Run: python3 -m pytest tests/test_wp12866_01_asset_registration.py -q
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = "wp-12866-01"
REPORT_ID = "12866"
OUT = ROOT / "docs" / "kf" / PKG
CONTRACT_HASH = "e577eedec941fa1ce25076f7a16b0774d609c1ca6693b056a5b0212ab5483154"
SOURCE_URI = "tensor://reports/12866"
FIGURE_NAMES = [
    "fig1_lamb_coefficients.png",
    "fig2_munk_convergence.png",
    "fig3_depth_keeping.png",
    "fig4_munk_vs_alpha.png",
]


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def kf() -> dict:
    return json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def md() -> str:
    return (OUT / "source_markdown.md").read_text(encoding="utf-8")


def test_valid_json_artifacts():
    """acceptance: valid_json — every emitted artifact parses."""
    for name in ("asset_manifest.json", "kf_result.json", "figure_probe.json", "self_check.json", "report_record.json"):
        json.loads((OUT / name).read_text(encoding="utf-8"))


def test_envelope_schema_pass(kf):
    """acceptance: schema_pass — envelope validates against the platform-pinned schema."""
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(kf, schema)
    assert kf["package_id"] == PKG
    assert kf["task_type"] == "01-asset-registration"
    assert kf["report_id"] == REPORT_ID
    assert kf["provenance"]["source_field"] == "markdown"
    assert kf["provenance"]["source_hash"].startswith("sha256:")


def test_manifest_schema_pass(manifest):
    """acceptance: schema_pass — manifest validates against the package-local schema."""
    schema = json.loads((OUT / "asset_manifest_12866.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)
    assert manifest["objective"] == {"register_assets": True, "classify_report_type": False}
    assert manifest["source"]["uri"] == SOURCE_URI
    assert manifest["source"]["field"] == "markdown"


def test_source_hash_matches_contract(manifest, kf, md):
    """acceptance: source_hash_matches — independent recomputation over utf-8 bytes."""
    recomputed = hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert recomputed == CONTRACT_HASH
    assert manifest["source"]["hash"] == recomputed
    assert manifest["source"]["contract_hash"] == CONTRACT_HASH
    assert manifest["source"]["hash_matches_contract"] is True
    assert kf["provenance"]["source_hash"] == f"sha256:{CONTRACT_HASH}"
    assert kf["provenance"]["source_chars"] == len(md)
    assert kf["provenance"]["source_bytes_utf8"] == len(md.encode("utf-8"))


def test_no_duplicate_ids(manifest, kf):
    """acceptance: no_duplicate_ids — asset ids (and claim ids) are unique."""
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"A[0-9]{2}", i) for i in ids)
    cids = [c["claim_id"] for c in kf.get("claims", [])]
    assert len(cids) == len(set(cids))


def test_source_locator_resolvable(manifest, md):
    """acceptance: source_locator_resolvable — every locator reproduces its quote verbatim, once."""
    for a in manifest["assets"]:
        loc = a["locator"]
        assert md[loc["start_char"] : loc["end_char"]] == loc["quote"], a["asset_id"]
        assert md.count(loc["quote"]) == 1, a["asset_id"]
        assert loc["unique"] is True
        # line numbers must be consistent with the char span
        assert loc["start_line"] == md.count("\n", 0, loc["start_char"]) + 1
        assert 1 <= loc["start_line"] <= loc["end_line"] <= md.count("\n") + 1


def test_all_claims_have_evidence_or_explicit_unresolved_status(kf, manifest):
    """acceptance: no claim may exist without evidence or an explicit unresolved status.

    For 01-asset-registration the contract-permitted complete result carries zero claims.
    """
    assert kf["claims"] == []
    assert manifest["claims"] == []
    assert manifest["counts"]["claims_registered"] == 0


def test_figures_hash_pinned(manifest):
    """Figures are real payloads: endpoint 200, sha256 pinned, local copy reproduces the hash."""
    figs = [a for a in manifest["assets"] if a["asset_class"] == "embedded_figure"]
    assert len(figs) == 4
    seen = set()
    for a in figs:
        pl = a["payload"]
        probe = pl["probe"]
        assert probe["http_status"] == 200
        assert probe["resolvable"] is True
        assert probe["bytes"] > 0
        assert pl["record_figure_name"] in FIGURE_NAMES
        seen.add(pl["record_figure_name"])
        local = ROOT / pl["local_copy"]
        assert local.exists()
        assert hashlib.sha256(local.read_bytes()).hexdigest() == probe["sha256"]
    assert seen == set(FIGURE_NAMES)


def test_platform_figure_metadata_cross_checked(manifest):
    record = json.loads((OUT / "report_record.json").read_text(encoding="utf-8"))
    names = [f["name"] for f in record["figures"]]
    assert names == FIGURE_NAMES
    assert manifest["source"]["mission_id"] == record["mission_id"] == 12371
    assert manifest["source"]["scenario_key"] == record["scenario_key"] == "auv_manoeuvrability_vertical_plane"


def test_cross_repo_references_are_not_claimed_resolved(manifest):
    """Honesty guard: targets outside this package must stay referenced_unresolved."""
    unresolved = {a["locator"]["quote"] for a in manifest["assets"] if a["resolution"] == "referenced_unresolved"}
    for anchor in (
        "backend/methods/manoeuvring/submarine.py",
        "backend/tests/test_auv_manoeuvring_m12371.py",
        "docs/reports/auv_manoeuvrability_w5n06.md",
        "artifacts/auv_manoeuvring_m12371/",
        "agent/m12371",
        "ship-performance-platform",
    ):
        assert anchor in unresolved
    for a in manifest["assets"]:
        if a["resolution"] == "referenced_unresolved":
            assert a["resolution_check"]["result"] == "unresolved"
            assert a["note"].strip()


def test_report_body_contract(manifest, kf):
    rep = (OUT / "REPORT.md").read_text(encoding="utf-8")
    assert rep.splitlines()[0] == f"# KF-RESULT {PKG}"
    assert f"kf-wp:{PKG}" in rep
    for sec in ("①", "②", "③", "④", "⑤", "⑥"):
        assert sec in rep
    blocks = re.findall(r"```json\n(.*?)\n```", rep, flags=re.S)
    assert len(blocks) == 1, "exactly one fenced json block is the single result channel"
    assert json.loads(blocks[0]) == kf
    assert "repro_cmd" in manifest and manifest["repro_cmd"]


def test_single_report_scope():
    """Boundary: no artifact may point at another report_id."""
    for path in OUT.glob("*.json"):
        for other in re.findall(r"tensor://reports/(\d+)", path.read_text(encoding="utf-8")):
            assert other == REPORT_ID, f"{path.name} references report {other}"


def test_outputs_pointer_matches_file(kf):
    entry = kf["outputs"]["asset_manifest.json"]
    data = (ROOT / entry["path"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == entry["sha256"]
    assert len(data) == entry["bytes"]


def test_verify_mode_is_green():
    """The package's own verifier must pass end-to-end (this is the repro_cmd gate)."""
    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "kf" / "build_asset_manifest_12866.py"), "--offline", "--verify"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert out.returncode == 0, out.stdout + out.stderr
    assert "VERIFY OK" in out.stdout

def test_process_figure_and_counts_consistency(manifest):
    """The only self-produced figure must exist and be derived from the manifest counts."""
    fig = OUT / "fig_asset_resolution.png"
    assert fig.exists() and fig.stat().st_size > 5000
    rep = (OUT / "REPORT.md").read_text(encoding="utf-8")
    assert "fig_asset_resolution.png" in rep
    counts = manifest["counts"]
    assert sum(counts["by_class"].values()) == counts["assets"] == len(manifest["assets"])
    assert sum(counts["by_resolution"].values()) == counts["assets"]
    assert counts["resolved_in_source"] + counts["referenced_unresolved"] + counts["declared_absent"] == counts["assets"]
