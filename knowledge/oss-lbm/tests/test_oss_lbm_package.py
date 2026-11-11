"""
Test suite for OSS-LBM knowledge package.

Tests validate:
- Package structure and file existence
- Schema conformance
- Cross-reference integrity
- Epistemic discipline
- Claim extraction utilities
"""

import pytest
import json
from pathlib import Path
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.validator import KnowledgeValidator
from lib.claim_extractor import ClaimExtractor
from lib.evidence_builder import EvidenceBuilder


PACKAGE_DIR = Path(__file__).parent.parent


class TestPackageStructure:
    """Test knowledge package structure."""
    
    def test_claims_file_exists(self):
        """Claims file must exist."""
        claims_path = PACKAGE_DIR / "claims" / "claims.json"
        assert claims_path.exists(), f"Missing {claims_path}"
    
    def test_evidence_file_exists(self):
        """Evidence file must exist."""
        evidence_path = PACKAGE_DIR / "evidence" / "evidence.json"
        assert evidence_path.exists(), f"Missing {evidence_path}"
    
    def test_provenance_file_exists(self):
        """Provenance file must exist."""
        provenance_path = PACKAGE_DIR / "provenance" / "provenance.json"
        assert provenance_path.exists(), f"Missing {provenance_path}"
    
    def test_readme_exists(self):
        """README must exist."""
        readme_path = PACKAGE_DIR / "README.md"
        assert readme_path.exists(), f"Missing {readme_path}"
    
    def test_validator_exists(self):
        """Validator script must exist."""
        validator_path = PACKAGE_DIR / "validate_oss_lbm.py"
        assert validator_path.exists(), f"Missing {validator_path}"


class TestClaimsContent:
    """Test claims content and structure."""
    
    @pytest.fixture
    def claims(self):
        """Load claims from file."""
        claims_path = PACKAGE_DIR / "claims" / "claims.json"
        return json.loads(claims_path.read_text())
    
    def test_minimum_claim_count(self, claims):
        """Must have at least 15 claims."""
        assert len(claims) >= 15, f"Expected ≥15 claims, found {len(claims)}"
    
    def test_claim_ids_unique(self, claims):
        """All claim IDs must be unique."""
        ids = [c["id"] for c in claims]
        assert len(ids) == len(set(ids)), "Duplicate claim IDs found"
    
    def test_claim_id_pattern(self, claims):
        """Claim IDs must match pattern."""
        import re
        pattern = re.compile(r"^tkc:oss-lbm:[a-z0-9-]+$")
        for claim in claims:
            assert pattern.match(claim["id"]), f"Invalid claim ID: {claim['id']}"
    
    def test_claim_required_fields(self, claims):
        """Claims must have all required fields."""
        required = ["id", "statement", "claim_type", "epistemic_status",
                   "created_at", "version", "evidence_refs", "notes"]
        for claim in claims:
            for field in required:
                assert field in claim, f"Claim {claim['id']} missing {field}"
    
    def test_claim_epistemic_status_valid(self, claims):
        """Epistemic status must be from valid set."""
        valid_statuses = {"established", "well-supported", "provisional",
                         "contested", "speculative", "superseded", "not-assessed"}
        for claim in claims:
            assert claim["epistemic_status"] in valid_statuses, \
                f"Claim {claim['id']} has invalid status: {claim['epistemic_status']}"
    
    def test_claim_has_tensorlbm_notes(self, claims):
        """Each claim must have TensorLBM service notes."""
        for claim in claims:
            assert claim.get("notes"), f"Claim {claim['id']} missing notes"
            assert len(claim["notes"]) > 0, f"Claim {claim['id']} has empty notes"


class TestEvidenceContent:
    """Test evidence content and structure."""
    
    @pytest.fixture
    def evidence(self):
        """Load evidence from file."""
        evidence_path = PACKAGE_DIR / "evidence" / "evidence.json"
        return json.loads(evidence_path.read_text())
    
    def test_evidence_ids_unique(self, evidence):
        """All evidence IDs must be unique."""
        ids = [e["id"] for e in evidence]
        assert len(ids) == len(set(ids)), "Duplicate evidence IDs found"
    
    def test_evidence_id_pattern(self, evidence):
        """Evidence IDs must match pattern."""
        import re
        pattern = re.compile(r"^tke:oss-lbm:[a-z0-9-]+$")
        for ev in evidence:
            assert pattern.match(ev["id"]), f"Invalid evidence ID: {ev['id']}"
    
    def test_evidence_required_fields(self, evidence):
        """Evidence must have all required fields."""
        required = ["id", "claim_refs", "source", "relation", "locator",
                   "captured_at", "assessment_status", "version"]
        for ev in evidence:
            for field in required:
                assert field in ev, f"Evidence {ev['id']} missing {field}"
    
    def test_evidence_assessment_status(self, evidence):
        """Assessment status must be from valid set."""
        valid_statuses = {"unassessed", "reviewed-supports", "reviewed-refutes",
                         "reviewed-qualifies", "insufficient", "disputed"}
        for ev in evidence:
            assert ev["assessment_status"] in valid_statuses, \
                f"Evidence {ev['id']} has invalid status: {ev['assessment_status']}"
    
    def test_evidence_has_code_location(self, evidence):
        """Evidence should use code-location locator."""
        for ev in evidence:
            locator = ev.get("locator", {})
            assert locator.get("locator_type") == "code-location", \
                f"Evidence {ev['id']} should use code-location"
    
    def test_evidence_has_quote(self, evidence):
        """Evidence must have verbatim quote."""
        for ev in evidence:
            locator = ev.get("locator", {})
            assert locator.get("quote"), f"Evidence {ev['id']} missing quote"


class TestCrossReferences:
    """Test cross-reference integrity."""
    
    @pytest.fixture
    def claims_and_evidence(self):
        """Load claims and evidence."""
        claims_path = PACKAGE_DIR / "claims" / "claims.json"
        evidence_path = PACKAGE_DIR / "evidence" / "evidence.json"
        claims = json.loads(claims_path.read_text())
        evidence = json.loads(evidence_path.read_text())
        return claims, evidence
    
    def test_claims_reference_valid_evidence(self, claims_and_evidence):
        """All claim evidence_refs must point to existing evidence."""
        claims, evidence = claims_and_evidence
        evidence_ids = {e["id"] for e in evidence}
        
        for claim in claims:
            for ref in claim.get("evidence_refs", []):
                assert ref in evidence_ids, \
                    f"Claim {claim['id']} references missing evidence {ref}"
    
    def test_evidence_references_valid_claims(self, claims_and_evidence):
        """All evidence claim_refs must point to existing claims."""
        claims, evidence = claims_and_evidence
        claim_ids = {c["id"] for c in claims}
        
        for ev in evidence:
            for ref in ev.get("claim_refs", []):
                assert ref in claim_ids, \
                    f"Evidence {ev['id']} references missing claim {ref}"


class TestEpistemicDiscipline:
    """Test epistemic discipline compliance."""
    
    @pytest.fixture
    def claims_and_evidence(self):
        """Load claims and evidence."""
        claims_path = PACKAGE_DIR / "claims" / "claims.json"
        evidence_path = PACKAGE_DIR / "evidence" / "evidence.json"
        claims = json.loads(claims_path.read_text())
        evidence = json.loads(evidence_path.read_text())
        return claims, evidence
    
    def test_no_self_approval(self, claims_and_evidence):
        """Evidence must not be self-approved."""
        claims, evidence = claims_and_evidence
        
        for ev in evidence:
            if ev.get("assessment_status") in ["reviewed-supports", "reviewed-refutes"]:
                captured_by = ev.get("captured_by", "")
                reviewed_by = ev.get("reviewed_by", "")
                assert captured_by != reviewed_by, \
                    f"Evidence {ev['id']} appears self-approved"
    
    def test_all_evidence_unassessed(self, claims_and_evidence):
        """All evidence should be unassessed (draft status)."""
        claims, evidence = claims_and_evidence
        
        # This is a convention for draft packages
        unassessed_count = sum(1 for e in evidence 
                              if e.get("assessment_status") == "unassessed")
        # At least 90% should be unassessed
        ratio = unassessed_count / len(evidence) if evidence else 0
        assert ratio >= 0.9, f"Only {ratio:.1%} evidence is unassessed"


class TestValidator:
    """Test the KnowledgeValidator class."""
    
    def test_validator_initialization(self):
        """Validator should initialize with package directory."""
        validator = KnowledgeValidator(PACKAGE_DIR)
        assert validator.package_dir == PACKAGE_DIR
    
    def test_validator_package_validation(self):
        """Validator should validate the package."""
        validator = KnowledgeValidator(PACKAGE_DIR)
        valid, result = validator.validate_package()
        
        assert isinstance(valid, bool)
        assert "errors" in result
        assert "warnings" in result
        assert "counts" in result


class TestClaimExtractor:
    """Test the ClaimExtractor class."""
    
    def test_extractor_initialization(self):
        """Extractor should initialize with repo path."""
        # Use a mock path for testing
        extractor = ClaimExtractor("/tmp/mock", "test-framework")
        assert extractor.framework_name == "test-framework"
    
    def test_extractor_get_results(self):
        """Extractor should return results dict."""
        extractor = ClaimExtractor("/tmp/mock", "test-framework")
        results = extractor.get_results()
        
        assert "claims" in results
        assert "evidence" in results
        assert isinstance(results["claims"], list)
        assert isinstance(results["evidence"], list)


class TestEvidenceBuilder:
    """Test the EvidenceBuilder class."""
    
    def test_builder_initialization(self):
        """Builder should initialize with framework and commit."""
        builder = EvidenceBuilder("test-framework", "abc1234")
        assert builder.framework == "test-framework"
        assert builder.commit == "abc1234"
    
    def test_builder_get_evidence(self):
        """Builder should return evidence list."""
        builder = EvidenceBuilder("test-framework", "abc1234")
        evidence = builder.get_evidence()
        
        assert isinstance(evidence, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
