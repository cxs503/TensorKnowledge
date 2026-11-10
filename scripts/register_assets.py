#!/usr/bin/env python3
"""Register all OSS-LBM knowledge objects into the asset management system.

This script:
1. Scans all oss-lbm claim/evidence/provenance files
2. Registers each claim as a KO version (draft→published)
3. Creates a supersede chain demo (one KO with v1.0.0→v1.1.0→v2.0.0)
4. Registers sample dataset assets (m8810 exports)
5. Computes quality ledger
6. Exports ASSET-INDEX compatible JSON
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent
OSS_LBM_DIR = REPO_ROOT / "knowledge" / "oss-lbm"

sys.path.insert(0, str(REPO_ROOT))

from ke import store, assets as asset_mgr


def compute_content_sha256(content: dict) -> str:
    return hashlib.sha256(
        json.dumps(content, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def register_oss_lbm_kos(conn, deduplicate: bool = True) -> dict:
    """Register all OSS-LBM claims as KO versions.

    When deduplicate=True, claims with the same KO ID are merged (first wins).
    """
    registered = {"kos": [], "supersede_chain": [], "duplicates_skipped": 0}
    seen_ko_ids: set[str] = set()

    # Collect all claim files
    claim_files = list(OSS_LBM_DIR.rglob("claims.json"))

    for cf in sorted(claim_files):
        claims = json.loads(cf.read_text(encoding="utf-8"))
        if not isinstance(claims, list):
            claims = [claims]

        for claim in claims:
            claim_id = claim["id"]
            # Derive KO id from claim id: tkc:oss-lbm:X → tko:oss-lbm:X
            ko_id = claim_id.replace("tkc:", "tko:", 1)

            if deduplicate and ko_id in seen_ko_ids:
                registered["duplicates_skipped"] += 1
                continue
            seen_ko_ids.add(ko_id)

            version = claim.get("version", "1.0.0")

            content = {
                "id": claim_id,
                "statement": claim["statement"],
                "claim_type": claim["claim_type"],
                "scope": claim.get("scope", {}),
                "modality": claim.get("modality", ""),
                "epistemic_status": claim.get("epistemic_status", "not-assessed"),
                "evidence_refs": claim.get("evidence_refs", []),
                "domains": [claim.get("scope", {}).get("domain", "lattice-Boltzmann-method")],
                "notes": claim.get("notes", []),
            }

            vid = asset_mgr.register_ko_version(
                conn,
                ko_id=ko_id,
                version=version,
                title=claim["statement"][:120],
                object_type="claim",
                summary=claim["statement"][:200],
                content=content,
                state="published",
                created_by=claim.get("created_by", "agent-m8635"),
                source_file=str(cf.relative_to(REPO_ROOT)),
                raw_json=json.dumps(claim, ensure_ascii=False, sort_keys=True),
            )
            registered["kos"].append({"ko_id": ko_id, "version_id": vid})

    conn.commit()  # Persist all registrations
    return registered


def create_supersede_demo(conn, ko_id: str = "tko:demo:supersede-chain") -> dict:
    """Create a supersede chain demo: one KO with 3 versions showing evolution.

    Uses a dedicated demo KO ID to avoid conflicts with registered oss-lbm KOs.
    """
    # v1.0.0 - initial (will be superseded)
    v1_content = {
        "id": "tkc:demo:supersede-chain",
        "statement": "pylbm implements symbolic equivalent equation derivation to second order.",
        "claim_type": "descriptive",
        "scope": {"domain": "lattice-Boltzmann-method", "system": "pylbm"},
        "domains": ["lattice-Boltzmann-method"],
    }
    v1_vid = asset_mgr.register_ko_version(
        conn, ko_id=ko_id, version="1.0.0",
        title="pylbm equivalent equation (v1)",
        object_type="claim",
        summary="Initial claim about pylbm equivalent equation derivation.",
        content=v1_content,
        state="published",
        created_by="agent-m8635",
        source_file="knowledge/oss-lbm/claims/claims.json",
        raw_json=json.dumps(v1_content, sort_keys=True),
    )

    # v1.1.0 - refined (supersedes v1.0.0)
    v2_content = {
        "id": "tkc:demo:supersede-chain",
        "statement": "pylbm implements symbolic equivalent equation derivation to second order in the lattice spacing using SymPy, computing coeff_order1 and coeff_order2.",
        "claim_type": "descriptive",
        "scope": {"domain": "lattice-Boltzmann-method", "system": "pylbm", "conditions": ["SymPy-based symbolic computation"]},
        "domains": ["lattice-Boltzmann-method"],
    }
    v2_vid = asset_mgr.register_ko_version(
        conn, ko_id=ko_id, version="1.1.0",
        title="pylbm equivalent equation (v1.1)",
        object_type="claim",
        summary="Refined claim with SymPy computation details.",
        content=v2_content,
        state="published",
        created_by="agent-m8635",
        source_file="knowledge/oss-lbm/claims/claims.json",
        raw_json=json.dumps(v2_content, sort_keys=True),
    )
    asset_mgr.supersede_ko(conn, v1_vid, v2_vid)

    # v2.0.0 - major revision (supersedes v1.1.0)
    v3_content = {
        "id": "tkc:demo:supersede-chain",
        "statement": "pylbm implements symbolic equivalent equation derivation to second order in the lattice spacing using SymPy, computing coeff_order1 (convective fluxes) and coeff_order2 (diffusion tensor B_ij) for arbitrary DdQq schemes.",
        "claim_type": "descriptive",
        "scope": {"domain": "lattice-Boltzmann-method", "system": "pylbm", "conditions": ["SymPy-based symbolic computation", "schemes without conserved_polynomials"]},
        "domains": ["lattice-Boltzmann-method"],
    }
    v3_vid = asset_mgr.register_ko_version(
        conn, ko_id=ko_id, version="2.0.0",
        title="pylbm equivalent equation (v2)",
        object_type="claim",
        summary="Major revision: full statement with DdQq scheme support.",
        content=v3_content,
        state="published",
        created_by="agent-m8811",
        source_file="knowledge/oss-lbm/claims/claims.json",
        raw_json=json.dumps(v3_content, sort_keys=True),
    )
    asset_mgr.supersede_ko(conn, v2_vid, v3_vid)

    # Add review events for the chain
    for vid, rationale in [
        (v1_vid, "superseded by v1.1.0 with refined statement"),
        (v2_vid, "superseded by v2.0.0 with full DdQq support"),
    ]:
        conn.execute(
            """INSERT INTO review_events
               (id, object_ref, object_version, decision, reviewer_json,
                reviewed_at, policy_version, rationale, raw_json)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                f"tkr:asset-ops:review-{vid.split(':')[-1]}",
                ko_id, vid.split(":v")[1],
                "approve",
                json.dumps({"id": "agent-m8811", "reviewer_type": "agent"}, sort_keys=True),
                datetime.now(timezone.utc).isoformat(),
                "asset-ops-v1",
                rationale,
                json.dumps({"decision": "approve", "rationale": rationale}, sort_keys=True),
            ),
        )

    conn.commit()  # Persist demo data
    return {
        "ko_id": ko_id,
        "chain": [v1_vid, v2_vid, v3_vid],
        "latest": v3_vid,
    }


def register_dataset_assets(conn) -> list:
    """Register sample dataset assets (simulating m8810 exports)."""
    registered = []

    # Simulated SFT dataset
    sft_data = json.dumps({"samples": [{"input": "x", "output": "y"}] * 1000}, sort_keys=True)
    sft_sha = hashlib.sha256(sft_data.encode()).hexdigest()
    aid = asset_mgr.register_dataset_asset(
        conn,
        asset_id="tka:oss-lbm:sft-lbm-concepts:v1.0.0",
        asset_type="sft",
        version="1.0.0",
        record_count=1000,
        status_dist={"train": 800, "valid": 100, "test": 100},
        sha256=sft_sha,
        gen_params={"domain": "lattice-Boltzmann-method", "source": "oss-lbm-claims"},
        upstream_commit="abc123def456",
        created_by="agent-m8810",
        raw_json=sft_data,
    )
    registered.append(aid)

    # Simulated eval dataset
    eval_data = json.dumps({"questions": [{"q": "What is LBM?", "a": "..."}] * 200}, sort_keys=True)
    eval_sha = hashlib.sha256(eval_data.encode()).hexdigest()
    aid = asset_mgr.register_dataset_asset(
        conn,
        asset_id="tka:oss-lbm:eval-lbm-concepts:v1.0.0",
        asset_type="eval",
        version="1.0.0",
        record_count=200,
        status_dist={"hard": 50, "medium": 100, "easy": 50},
        sha256=eval_sha,
        gen_params={"domain": "lattice-Boltzmann-method", "difficulty": "mixed"},
        upstream_commit="abc123def456",
        created_by="agent-m8810",
        raw_json=eval_data,
    )
    registered.append(aid)

    # Simulated triples dataset
    triples_data = json.dumps({"triples": [{"s": "LBM", "p": "implements", "o": "Boltzmann"}] * 500}, sort_keys=True)
    triples_sha = hashlib.sha256(triples_data.encode()).hexdigest()
    aid = asset_mgr.register_dataset_asset(
        conn,
        asset_id="tka:oss-lbm:triples-lbm-knowledge:v1.0.0",
        asset_type="triples",
        version="1.0.0",
        record_count=500,
        status_dist={"verified": 400, "pending": 100},
        sha256=triples_sha,
        gen_params={"domain": "lattice-Boltzmann-method", "extraction": "claim-evidence-pairs"},
        upstream_commit="abc123def456",
        created_by="agent-m8810",
        raw_json=triples_data,
    )
    registered.append(aid)

    conn.commit()  # Persist dataset assets
    return registered


def main(db_path: str | None = None) -> dict:
    """Run full registration pipeline."""
    if db_path:
        conn = store.connect(db_path)
    else:
        import tempfile
        db_path = tempfile.mktemp(suffix=".assets.db")
        conn = store.connect(db_path)

    result = {
        "db": db_path,
        "registered_kos": register_oss_lbm_kos(conn),
        "supersede_demo": create_supersede_demo(conn),
        "dataset_assets": register_dataset_assets(conn),
    }

    # Compute quality ledger
    result["quality_report"] = asset_mgr.get_quality_report(conn)

    # Export asset index
    result["asset_index"] = json.loads(asset_mgr.export_asset_index_json(conn))

    conn.close()
    return result


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else None
    result = main(db)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
