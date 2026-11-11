"""
Claim Extractor - Extracts claims from source code inspection.

This module provides utilities for extracting knowledge claims from
LBM framework source code with proper evidence tracking.
"""

import re
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class ClaimExtractor:
    """Extract knowledge claims from source code repositories."""
    
    def __init__(self, repo_path: str, framework_name: str, commit: str = None):
        self.repo_path = Path(repo_path)
        self.framework_name = framework_name
        self.commit = commit or self._get_commit()
        self.claims = []
        self.evidence = []
        
    def _get_commit(self) -> str:
        """Get current commit hash from repository."""
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip()[:7] if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"
    
    def _sanitize_id(self, name: str) -> str:
        """Sanitize name for use in ID (replace underscores with hyphens)."""
        return name.lower().replace('_', '-')
    
    def extract_class_claim(self, file_path: str, class_name: str, 
                           statement: str, notes: str) -> Dict[str, Any]:
        """Extract a claim about a class implementation."""
        full_path = self.repo_path / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"Source file not found: {full_path}")
        
        content = full_path.read_text(encoding='utf-8', errors='ignore')
        
        # Find class definition
        pattern = rf'class\s+{class_name}\s*[\(:]'
        match = re.search(pattern, content)
        if not match:
            raise ValueError(f"Class {class_name} not found in {file_path}")
        
        # Extract context (50 lines around match)
        lines = content.split('\n')
        line_num = content[:match.start()].count('\n') + 1
        start = max(0, line_num - 5)
        end = min(len(lines), line_num + 45)
        quote = '\n'.join(lines[start:end])
        
        claim_id = f"tkc:oss-lbm:{self.framework_name}-{self._sanitize_id(class_name)}"
        evidence_id = f"tke:oss-lbm:{self.framework_name}-{self._sanitize_id(class_name)}-src"
        
        claim = {
            "id": claim_id,
            "statement": statement,
            "claim_type": "descriptive",
            "scope": {
                "domain": "lattice-Boltzmann-method",
                "system": self.framework_name,
                "conditions": []
            },
            "modality": "asserted",
            "epistemic_status": "established",
            "evidence_refs": [evidence_id],
            "created_at": datetime.utcnow().isoformat() + "Z",
            "created_by": f"agent-extractor",
            "version": "1.0.0",
            "notes": [notes]
        }
        
        evidence = {
            "id": evidence_id,
            "claim_refs": [claim_id],
            "source": {
                "source_type": "other",
                "citation": f"{self.framework_name} source code, {file_path}",
                "url": f"https://github.com/{self.framework_name}",
                "accessed_at": datetime.utcnow().strftime("%Y-%m-%d")
            },
            "relation": "supports",
            "locator": {
                "locator_type": "code-location",
                "value": f"{self.framework_name}@{self.commit} {file_path}:{line_num}",
                "quote": quote[:500]  # Limit quote length
            },
            "extraction_method": "direct-quotation",
            "captured_at": datetime.utcnow().isoformat() + "Z",
            "captured_by": "agent-extractor",
            "assessment_status": "unassessed",
            "version": "1.0.0"
        }
        
        self.claims.append(claim)
        self.evidence.append(evidence)
        
        return {"claim": claim, "evidence": evidence}
    
    def extract_function_claim(self, file_path: str, function_name: str,
                              statement: str, notes: str) -> Dict[str, Any]:
        """Extract a claim about a function implementation."""
        full_path = self.repo_path / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"Source file not found: {full_path}")
        
        content = full_path.read_text(encoding='utf-8', errors='ignore')
        
        # Find function definition
        pattern = rf'def\s+{function_name}\s*\('
        match = re.search(pattern, content)
        if not match:
            raise ValueError(f"Function {function_name} not found in {file_path}")
        
        # Extract context
        lines = content.split('\n')
        line_num = content[:match.start()].count('\n') + 1
        start = max(0, line_num - 3)
        end = min(len(lines), line_num + 20)
        quote = '\n'.join(lines[start:end])
        
        claim_id = f"tkc:oss-lbm:{self.framework_name}-{self._sanitize_id(function_name)}"
        evidence_id = f"tke:oss-lbm:{self.framework_name}-{self._sanitize_id(function_name)}-src"
        
        claim = {
            "id": claim_id,
            "statement": statement,
            "claim_type": "descriptive",
            "scope": {
                "domain": "lattice-Boltzmann-method",
                "system": self.framework_name,
                "conditions": []
            },
            "modality": "asserted",
            "epistemic_status": "established",
            "evidence_refs": [evidence_id],
            "created_at": datetime.utcnow().isoformat() + "Z",
            "created_by": "agent-extractor",
            "version": "1.0.0",
            "notes": [notes]
        }
        
        evidence = {
            "id": evidence_id,
            "claim_refs": [claim_id],
            "source": {
                "source_type": "other",
                "citation": f"{self.framework_name} source code, {file_path}",
                "url": f"https://github.com/{self.framework_name}",
                "accessed_at": datetime.utcnow().strftime("%Y-%m-%d")
            },
            "relation": "supports",
            "locator": {
                "locator_type": "code-location",
                "value": f"{self.framework_name}@{self.commit} {file_path}:{line_num}",
                "quote": quote[:500]
            },
            "extraction_method": "direct-quotation",
            "captured_at": datetime.utcnow().isoformat() + "Z",
            "captured_by": "agent-extractor",
            "assessment_status": "unassessed",
            "version": "1.0.0"
        }
        
        self.claims.append(claim)
        self.evidence.append(evidence)
        
        return {"claim": claim, "evidence": evidence}
    
    def get_results(self) -> Dict[str, List[Dict]]:
        """Get all extracted claims and evidence."""
        return {
            "claims": self.claims,
            "evidence": self.evidence
        }
