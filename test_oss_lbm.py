"""Pytest tests for OSS-LBM knowledge packages."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent


def test_validate_oss_lbm():
    """Run the main OSS-LBM validator."""
    validator = HERE / "knowledge" / "oss-lbm" / "validate_oss_lbm.py"
    result = subprocess.run(
        [sys.executable, str(validator)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"Validator failed:\n{result.stdout}\n{result.stderr}"
    assert "PASS" in result.stdout


def test_validate_thermalmulti():
    """Run the ThermalMultiphase validator."""
    validator = HERE / "knowledge" / "oss-lbm" / "thermalmulti" / "validate_thermalmulti.py"
    result = subprocess.run(
        [sys.executable, str(validator)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"Validator failed:\n{result.stdout}\n{result.stderr}"
    assert "PASS" in result.stdout


def test_thermalmulti_claim_count():
    """Verify thermalmulti has ≥8 claims (task minimum)."""
    import json
    claims_path = HERE / "knowledge" / "oss-lbm" / "thermalmulti" / "claims" / "claims.json"
    claims = json.loads(claims_path.read_text())
    assert len(claims) >= 8, f"Expected ≥8 claims, found {len(claims)}"


def test_thermalmulti_gap_anchors():
    """Verify all thermalmulti claims have GAP-LBM-THERMAL-MULTIPHASE anchor."""
    import json
    claims_path = HERE / "knowledge" / "oss-lbm" / "thermalmulti" / "claims" / "claims.json"
    claims = json.loads(claims_path.read_text())
    for claim in claims:
        notes = claim.get("notes", [])
        has_gap = any("GAP" in n and "THERMAL-MULTIPHASE" in n for n in notes)
        assert has_gap, f"Claim {claim['id']} missing GAP-LBM-THERMAL-MULTIPHASE anchor"


def test_thermalmulti_evidence_quotes():
    """Verify all thermalmulti evidence has verbatim quotes."""
    import json
    evidence_path = HERE / "knowledge" / "oss-lbm" / "thermalmulti" / "evidence" / "evidence.json"
    evidence = json.loads(evidence_path.read_text())
    for ev in evidence:
        loc = ev.get("locator", {})
        assert loc.get("quote"), f"Evidence {ev['id']} missing verbatim quote"
        assert loc.get("locator_type") == "code-location", f"Evidence {ev['id']} wrong locator_type"


def test_thermalmulti_provenance():
    """Verify thermalmulti has valid provenance."""
    import json
    prov_path = HERE / "knowledge" / "oss-lbm" / "thermalmulti" / "provenance" / "provenance.json"
    provenance = json.loads(prov_path.read_text())
    assert len(provenance) >= 1, "Expected ≥1 provenance record"
    for prov in provenance:
        assert "ThermalMultiphaseOpenLB" in str(prov), "Provenance should reference ThermalMultiphaseOpenLB"
