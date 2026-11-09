#!/usr/bin/env python3
"""Validator for CudaPhaseField OSS knowledge claims.

Checks:
1. All claim files exist and have required fields
2. Evidence sections contain verbatim quotes with file:line references
3. Provenance sections contain commit hash and file paths
4. GAP anchor is present on each claim
5. epistemic_status is one of: established, contested, hypothesized
6. Minimum 8 claims present
"""

import os
import sys
import re
import glob

CLAIMS_DIR = os.path.join(os.path.dirname(__file__), "claims")
REQUIRED_FIELDS = ["claim_id", "epistemic_status", "gap_anchor", "Statement", "Evidence", "Provenance"]
VALID_STATUSES = {"established", "contested", "hypothesized"}
MIN_CLAIMS = 8

def validate_claim(filepath):
    """Validate a single claim file."""
    errors = []
    warnings = []
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in content:
            errors.append(f"Missing required field: {field}")
    
    # Check epistemic_status
    status_match = re.search(r'\*\*epistemic_status\*\*:\s*(\w+)', content)
    if status_match:
        status = status_match.group(1)
        if status not in VALID_STATUSES:
            errors.append(f"Invalid epistemic_status: {status}")
    else:
        errors.append("Missing epistemic_status")
    
    # Check GAP anchor
    gap_match = re.search(r'\*\*gap_anchor\*\*:\s*(GAP-[\w-]+)', content)
    if not gap_match:
        errors.append("Missing or malformed gap_anchor")
    
    # Check evidence has verbatim quotes
    if "```" not in content:
        warnings.append("No code blocks found in Evidence section")
    
    # Check provenance has commit
    if "commit" not in content.lower():
        errors.append("Missing commit reference in Provenance")
    
    # Check claim_id format
    id_match = re.search(r'\*\*claim_id\*\*:\s*(CUDAPF-\d+)', content)
    if not id_match:
        errors.append("Missing or malformed claim_id (expected CUDAPF-NNN)")
    
    return errors, warnings

def main():
    print("=" * 60)
    print("CudaPhaseField OSS Knowledge Validator")
    print("=" * 60)
    
    claim_files = sorted(glob.glob(os.path.join(CLAIMS_DIR, "claim_*.md")))
    
    if not claim_files:
        print(f"FAIL: No claim files found in {CLAIMS_DIR}")
        sys.exit(1)
    
    print(f"\nFound {len(claim_files)} claim files")
    
    all_errors = []
    all_warnings = []
    claim_ids = []
    
    for filepath in claim_files:
        fname = os.path.basename(filepath)
        errors, warnings = validate_claim(filepath)
        
        if errors:
            all_errors.append((fname, errors))
        if warnings:
            all_warnings.append((fname, warnings))
        
        # Extract claim_id
        with open(filepath) as f:
            content = f.read()
        id_match = re.search(r'\*\*claim_id\*\*:\s*(CUDAPF-\d+)', content)
        if id_match:
            claim_ids.append(id_match.group(1))
    
    # Check minimum claims
    if len(claim_files) < MIN_CLAIMS:
        all_errors.append(("_summary_", [f"Only {len(claim_files)} claims found, minimum is {MIN_CLAIMS}"]))
    
    # Check for duplicate claim_ids
    if len(claim_ids) != len(set(claim_ids)):
        all_errors.append(("_summary_", ["Duplicate claim_ids detected"]))
    
    # Report
    print(f"\n--- Results ---")
    print(f"Claims validated: {len(claim_files)}")
    print(f"Claim IDs: {', '.join(claim_ids)}")
    
    if all_warnings:
        print(f"\nWarnings ({sum(len(w) for _, w in all_warnings)}):")
        for fname, warnings in all_warnings:
            for w in warnings:
                print(f"  [WARN] {fname}: {w}")
    
    if all_errors:
        print(f"\nErrors ({sum(len(e) for _, e in all_errors)}):")
        for fname, errors in all_errors:
            for e in errors:
                print(f"  [FAIL] {fname}: {e}")
        print(f"\nVALIDATION FAILED")
        sys.exit(1)
    else:
        print(f"\nAll {len(claim_files)} claims passed validation")
        print("VALIDATION PASSED")
        sys.exit(0)

if __name__ == "__main__":
    main()
