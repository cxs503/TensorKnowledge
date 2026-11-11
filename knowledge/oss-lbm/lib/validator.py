"""
Knowledge Validator - Validates knowledge package integrity.

Checks:
- Schema conformance
- Cross-reference integrity
- Epistemic discipline
- Count constraints
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple


class KnowledgeValidator:
    """Validate knowledge package structure and integrity."""
    
    def __init__(self, package_dir: str):
        self.package_dir = Path(package_dir)
        self.errors = []
        self.warnings = []
        
    def validate_claims(self, claims: List[Dict]) -> bool:
        """Validate claims structure and constraints."""
        valid = True
        
        # Check count
        if len(claims) < 15:
            self.errors.append(f"Expected ≥15 claims, found {len(claims)}")
            valid = False
        
        # Check required fields
        required_fields = ["id", "statement", "claim_type", "epistemic_status", 
                          "created_at", "version", "evidence_refs", "notes"]
        
        for claim in claims:
            for field in required_fields:
                if field not in claim:
                    self.errors.append(f"Claim {claim.get('id', '?')} missing field: {field}")
                    valid = False
            
            # Check epistemic status
            valid_statuses = ["established", "well-supported", "provisional", 
                            "contested", "speculative", "superseded", "not-assessed"]
            if claim.get("epistemic_status") not in valid_statuses:
                self.errors.append(f"Claim {claim['id']} has invalid epistemic_status")
                valid = False
            
            # Check notes (TensorLBM service statement)
            if not claim.get("notes"):
                self.errors.append(f"Claim {claim['id']} missing notes")
                valid = False
        
        return valid
    
    def validate_evidence(self, evidence: List[Dict]) -> bool:
        """Validate evidence structure and constraints."""
        valid = True
        
        required_fields = ["id", "claim_refs", "source", "relation", "locator",
                          "captured_at", "assessment_status", "version"]
        
        for ev in evidence:
            for field in required_fields:
                if field not in ev:
                    self.errors.append(f"Evidence {ev.get('id', '?')} missing field: {field}")
                    valid = False
            
            # Check assessment status
            valid_statuses = ["unassessed", "reviewed-supports", "reviewed-refutes",
                            "reviewed-qualifies", "insufficient", "disputed"]
            if ev.get("assessment_status") not in valid_statuses:
                self.errors.append(f"Evidence {ev['id']} has invalid assessment_status")
                valid = False
            
            # Check locator
            locator = ev.get("locator", {})
            if locator.get("locator_type") != "code-location":
                self.warnings.append(f"Evidence {ev['id']} should use code-location locator")
            
            if not locator.get("quote"):
                self.errors.append(f"Evidence {ev['id']} missing quote")
                valid = False
        
        return valid
    
    def validate_cross_references(self, claims: List[Dict], 
                                 evidence: List[Dict]) -> bool:
        """Validate bidirectional cross-references."""
        valid = True
        
        claim_ids = {c["id"] for c in claims}
        evidence_ids = {e["id"] for e in evidence}
        
        # Claims → Evidence
        for claim in claims:
            for ref in claim.get("evidence_refs", []):
                if ref not in evidence_ids:
                    self.errors.append(f"Claim {claim['id']} references missing evidence {ref}")
                    valid = False
        
        # Evidence → Claims
        for ev in evidence:
            for ref in ev.get("claim_refs", []):
                if ref not in claim_ids:
                    self.errors.append(f"Evidence {ev['id']} references missing claim {ref}")
                    valid = False
        
        return valid
    
    def validate_epistemic_discipline(self, claims: List[Dict], 
                                     evidence: List[Dict]) -> bool:
        """Validate epistemic discipline (no self-approval)."""
        valid = True
        
        # Check that no evidence is self-approved
        for ev in evidence:
            if ev.get("assessment_status") in ["reviewed-supports", "reviewed-refutes"]:
                if ev.get("captured_by") == ev.get("reviewed_by"):
                    self.errors.append(f"Evidence {ev['id']} appears self-approved")
                    valid = False
        
        return valid
    
    def validate_package(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate entire knowledge package."""
        self.errors = []
        self.warnings = []
        
        # Load data
        claims_path = self.package_dir / "claims" / "claims.json"
        evidence_path = self.package_dir / "evidence" / "evidence.json"
        provenance_path = self.package_dir / "provenance" / "provenance.json"
        
        if not claims_path.exists():
            self.errors.append(f"Missing: {claims_path}")
            return False, {"errors": self.errors, "warnings": self.warnings}
        
        if not evidence_path.exists():
            self.errors.append(f"Missing: {evidence_path}")
            return False, {"errors": self.errors, "warnings": self.warnings}
        
        if not provenance_path.exists():
            self.errors.append(f"Missing: {provenance_path}")
            return False, {"errors": self.errors, "warnings": self.warnings}
        
        claims = json.loads(claims_path.read_text())
        evidence = json.loads(evidence_path.read_text())
        provenance = json.loads(provenance_path.read_text())
        
        # Run validations
        valid = True
        valid &= self.validate_claims(claims)
        valid &= self.validate_evidence(evidence)
        valid &= self.validate_cross_references(claims, evidence)
        valid &= self.validate_epistemic_discipline(claims, evidence)
        
        result = {
            "valid": valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "counts": {
                "claims": len(claims),
                "evidence": len(evidence),
                "provenance": len(provenance)
            }
        }
        
        return valid, result
