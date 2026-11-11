#!/usr/bin/env python3
"""
Update OSS-LBM knowledge package with verified evidence from actual source code.

This script:
1. Updates pylbm evidence with correct commit hash
2. Adds claims from Maarten-vd-Sande_lbm (lbm-principles-practice companion)
3. Ensures all evidence has proper code-location locators
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib.claim_extractor import ClaimExtractor


def update_pylbm_evidence():
    """Update pylbm evidence with verified commit hash."""
    print("Updating pylbm evidence with verified source code...")
    
    claims_path = Path("claims/claims.json")
    evidence_path = Path("evidence/evidence.json")
    
    claims = json.loads(claims_path.read_text())
    evidence = json.loads(evidence_path.read_text())
    
    # Update commit hash for pylbm evidence
    pylbm_commit = "f9f5d16"
    
    for ev in evidence:
        if "pylbm" in ev["id"]:
            # Update locator with correct commit
            locator = ev.get("locator", {})
            if locator.get("value", "").startswith("pylbm@"):
                old_value = locator["value"]
                # Replace commit hash
                parts = old_value.split(" ", 1)
                if len(parts) == 2:
                    locator["value"] = f"pylbm@{pylbm_commit} {parts[1]}"
                    ev["locator"] = locator
    
    # Save updated evidence
    evidence_path.write_text(json.dumps(evidence, indent=4, ensure_ascii=False))
    print(f"✓ Updated {sum(1 for e in evidence if 'pylbm' in e['id'])} pylbm evidence records")
    
    return claims, evidence


def add_maarten_claims():
    """Add claims from Maarten-vd-Sande_lbm repository."""
    print("\nAdding claims from Maarten-vd-Sande_lbm (lbm-principles-practice companion)...")
    
    repo_path = Path("/root/oss-cache/Maarten-vd-Sande_lbm")
    if not repo_path.exists():
        print(f"✗ Repository not found: {repo_path}")
        return [], []
    
    extractor = ClaimExtractor(repo_path, "lbm-principles-practice", "master")
    
    # Extract claims from key files
    try:
        # Claim 1: D2Q9 lattice structure
        extractor.extract_function_claim(
            "lbm/streamcollide.py",
            "set_equi",
            "lbm-principles-practice implements D2Q9 lattice with standard equilibrium distribution using weights t[n] and velocity vectors v[n], following the textbook formulation from Thuerey's PhD thesis.",
            "TensorLBM 可服务改进点: 可作为教学参考实现，用于验证 D2Q9 格子和平衡态分布的正确性。"
        )
        
        # Claim 2: BGK collision operator
        extractor.extract_function_claim(
            "lbm/streamcollide.py",
            "collide",
            "lbm-principles-practice implements BGK collision operator with single relaxation time omega, including gravitational force coupling through velocity-weighted source terms.",
            "TensorLBM 可服务改进点: BGK 碰撞算子的简洁实现可作为基准参考，用于验证更复杂碰撞模型的正确性。"
        )
        
        # Claim 3: Free-surface interface tracking
        extractor.extract_function_claim(
            "lbm/streamcollide.py",
            "get_epsilon",
            "lbm-principles-practice implements free-surface LBM with mass-based interface tracking, computing cell fill fraction epsilon from mass/density ratio with clipping to [0,1].",
            "TensorLBM 可服务改进点: 自由表面 LBM 的质量交换方法可用于多相流扩展，提供界面追踪的参考实现。"
        )
        
        # Claim 4: Interface normal computation
        extractor.extract_function_claim(
            "lbm/streamcollide.py",
            "get_normal",
            "lbm-principles-practice computes interface normals from fill fraction gradients using central differences, enabling surface tension effects through normal-dependent streaming correction.",
            "TensorLBM 可服务改进点: 界面法向量的有限差分计算可用于表面张力模型的实现参考。"
        )
        
        # Claim 5: Mass exchange for interface cells
        extractor.extract_function_claim(
            "lbm/streamcollide.py",
            "interface_mass_exchange",
            "lbm-principles-practice implements mass exchange between interface and neighboring cells (fluid/interface/gas) with neighbor-type-dependent flux computation, conserving mass across the interface.",
            "TensorLBM 可服务改进点: 界面质量交换算法可用于发展守恒的多相流 LBM 方法。"
        )
        
        # Claim 6: Numba JIT optimization
        extractor.extract_function_claim(
            "lbm/streamcollide.py",
            "update_rho_u",
            "lbm-principles-practice uses Numba @jit decorator for performance-critical kernels (streaming, collision, density/velocity update), demonstrating Python+JIT approach to LBM acceleration.",
            "TensorLBM 可服务改进点: Numba JIT 优化策略可作为 Python 性能优化的参考，平衡开发效率与运行性能。"
        )
        
        # Claim 7: Velocity limiting for stability
        extractor.extract_function_claim(
            "lbm/streamcollide.py",
            "update_rho_u",
            "lbm-principles-practice implements velocity magnitude limiting to sqrt(2/3) (lattice sound speed times sqrt(2)) to maintain low Mach number and numerical stability.",
            "TensorLBM 可服务改进点: 速度限制策略可用于防止高 Mach 数不稳定性，作为稳定性增强机制的参考。"
        )
        
        # Claim 8: Inlet boundary condition
        extractor.extract_function_claim(
            "lbm/streamcollide.py",
            "set_inlet",
            "lbm-principles-practice implements Zou-He style inlet boundary condition, computing density from velocity and incoming distributions for pressure/velocity inlet.",
            "TensorLBM 可服务改进点: Zou-He 边界条件的实现可用于验证 TensorLBM 的边界处理精度。"
        )
        
        # Claim 9: Outlet boundary condition
        extractor.extract_function_claim(
            "lbm/streamcollide.py",
            "set_outlet",
            "lbm-principles-practice implements simple outlet boundary condition by copying distributions from upstream neighbor, providing zero-gradient outflow.",
            "TensorLBM 可服务改进点: 简单出口边界可作为基准测试用例，验证更复杂出口条件的必要性。"
        )
        
        # Claim 10: Time evolution loop
        extractor.extract_function_claim(
            "lbm/time_evolve.py",
            "evolve",
            "lbm-principles-practice organizes time evolution as a separate module with evolve() function, demonstrating clean separation of time stepping from physics kernels.",
            "TensorLBM 可服务改进点: 时间演化的模块化组织可用于 TensorLBM 的求解器架构设计参考。"
        )
        
    except Exception as e:
        print(f"✗ Error extracting claims: {e}")
        import traceback
        traceback.print_exc()
        return [], []
    
    results = extractor.get_results()
    print(f"✓ Extracted {len(results['claims'])} claims from Maarten-vd-Sande_lbm")
    
    return results['claims'], results['evidence']


def merge_claims_and_evidence(existing_claims, existing_evidence, 
                             new_claims, new_evidence):
    """Merge new claims and evidence with existing ones."""
    # Check for duplicates
    existing_claim_ids = {c['id'] for c in existing_claims}
    existing_evidence_ids = {e['id'] for e in existing_evidence}
    
    # Filter out duplicates
    unique_new_claims = [c for c in new_claims if c['id'] not in existing_claim_ids]
    unique_new_evidence = [e for e in new_evidence if e['id'] not in existing_evidence_ids]
    
    # Merge
    merged_claims = existing_claims + unique_new_claims
    merged_evidence = existing_evidence + unique_new_evidence
    
    return merged_claims, merged_evidence


def main():
    """Main update script."""
    print("=" * 60)
    print("OSS-LBM Knowledge Package Update")
    print("=" * 60)
    
    # Load existing data
    claims_path = Path("claims/claims.json")
    evidence_path = Path("evidence/evidence.json")
    
    if not claims_path.exists() or not evidence_path.exists():
        print("✗ Missing claims or evidence files")
        return 1
    
    existing_claims = json.loads(claims_path.read_text())
    existing_evidence = json.loads(evidence_path.read_text())
    
    print(f"Existing: {len(existing_claims)} claims, {len(existing_evidence)} evidence")
    
    # Update pylbm evidence
    updated_claims, updated_evidence = update_pylbm_evidence()
    
    # Add Maarten claims
    new_claims, new_evidence = add_maarten_claims()
    
    # Merge
    final_claims, final_evidence = merge_claims_and_evidence(
        updated_claims, updated_evidence, new_claims, new_evidence
    )
    
    # Save
    claims_path.write_text(json.dumps(final_claims, indent=4, ensure_ascii=False))
    evidence_path.write_text(json.dumps(final_evidence, indent=4, ensure_ascii=False))
    
    print(f"\n{'=' * 60}")
    print(f"Final: {len(final_claims)} claims, {len(final_evidence)} evidence")
    print(f"Added: {len(final_claims) - len(existing_claims)} new claims")
    print(f"{'=' * 60}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
