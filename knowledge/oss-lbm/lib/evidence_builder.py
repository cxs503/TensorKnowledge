"""
Evidence Builder - Constructs evidence records with proper provenance.

Ensures all evidence follows the epistemic discipline:
- Code-location locators with verbatim quotes
- Unassessed status (no self-approval)
- Proper cross-references to claims
"""

from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class EvidenceBuilder:
    """Build evidence records from source code inspection."""
    
    def __init__(self, framework: str, commit: str):
        self.framework = framework
        self.commit = commit
        self.evidence_records = []
    
    def build_code_evidence(self, claim_id: str, file_path: str, 
                           line_start: int, line_end: int,
                           quote: str, relation: str = "supports") -> Dict[str, Any]:
        """Build a code-location evidence record."""
        evidence_id = f"tke:oss-lbm:{self.framework}-{claim_id.split(':')[-1]}-src"
        
        evidence = {
            "id": evidence_id,
            "claim_refs": [claim_id],
            "source": {
                "source_type": "other",
                "citation": f"{self.framework} source code, {file_path}",
                "url": f"https://github.com/{self.framework}",
                "accessed_at": datetime.utcnow().strftime("%Y-%m-%d")
            },
            "relation": relation,
            "locator": {
                "locator_type": "code-location",
                "value": f"{self.framework}@{self.commit} {file_path}:{line_start}-{line_end}",
                "quote": quote
            },
            "extraction_method": "direct-quotation",
            "captured_at": datetime.utcnow().isoformat() + "Z",
            "captured_by": "agent-evidence-builder",
            "assessment_status": "unassessed",
            "version": "1.0.0"
        }
        
        self.evidence_records.append(evidence)
        return evidence
    
    def build_test_evidence(self, claim_id: str, test_file: str,
                           test_name: str, result: str) -> Dict[str, Any]:
        """Build evidence from test execution."""
        evidence_id = f"tke:oss-lbm:{self.framework}-{claim_id.split(':')[-1]}-test"
        
        evidence = {
            "id": evidence_id,
            "claim_refs": [claim_id],
            "source": {
                "source_type": "test-result",
                "citation": f"{self.framework} test suite, {test_file}::{test_name}",
                "url": f"https://github.com/{self.framework}",
                "accessed_at": datetime.utcnow().strftime("%Y-%m-%d")
            },
            "relation": "supports",
            "locator": {
                "locator_type": "test-location",
                "value": f"{test_file}::{test_name}",
                "quote": result
            },
            "extraction_method": "test-execution",
            "captured_at": datetime.utcnow().isoformat() + "Z",
            "captured_by": "agent-evidence-builder",
            "assessment_status": "unassessed",
            "version": "1.0.0"
        }
        
        self.evidence_records.append(evidence)
        return evidence
    
    def get_evidence(self) -> List[Dict[str, Any]]:
        """Get all built evidence records."""
        return self.evidence_records
