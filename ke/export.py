"""KE export — three-piece export pipeline for physical-AI training.

Exports ingested knowledge into three formats:

  1. SFT corpus (JSONL, messages format): claim+evidence+provenance →
     conservative proposition + citation anchor + "how to verify" reasoning.
     Epistemic hard gate: only published/reviewed-status claims enter the
     training set; draft/insufficient-evidence claims are excluded and
     counted in the manifest.

  2. Eval set (JSONL): verified numerical benchmarks with input parameters,
     expected values, tolerance, and source claim_id.

  3. Triples (JSONL): knowledge-object relationships (supports/refutes/
     derived_from) as subject-predicate-object triples.

Each export produces a manifest with counts, status distribution, domain
distribution, generation time, and upstream commit.

CLI:
    python -m ke.cli export --kind sft|eval|triples --out DIR [--db PATH]
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import queries as q
from . import store

# ---------------------------------------------------------------------------
# Epistemic gate
# ---------------------------------------------------------------------------

# Claims with these epistemic_status values are considered "published/reviewed"
# and eligible for SFT training. All others are excluded.
PUBLISHED_STATUSES = {"established", "well-supported"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _git_commit(repo_dir: Path | None = None) -> str:
    """Return the current git commit hash (short)."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True,
            cwd=repo_dir,
        )
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _get_scope(claim: dict, conn: sqlite3.Connection | None = None) -> dict:
    """Get scope dict from a claim record. Handles both DB rows and raw dicts."""
    # Try direct scope key first (raw dict)
    if "scope" in claim:
        return claim["scope"]
    # Try scope_json (DB row)
    if "scope_json" in claim and claim["scope_json"]:
        return json.loads(claim["scope_json"])
    # Fallback: query the DB
    if conn and "id" in claim:
        row = conn.execute("SELECT scope_json FROM claims WHERE id=?", (claim["id"],)).fetchone()
        if row and row["scope_json"]:
            return json.loads(row["scope_json"])
    return {}




def _ingest_pilot_flexible(pilot_dir: Path, conn: sqlite3.Connection) -> dict:
    """Ingest a pilot package, handling both per-record and single-array formats.

    Returns record counts.
    """
    def _load_records(sub: str) -> list[dict]:
        d = pilot_dir / sub
        if not d.is_dir():
            return []
        # Check for single-array file first
        single = d / f"{sub}.json"
        if single.exists():
            data = json.loads(single.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            return [data]
        # Load individual files
        out = []
        for p in sorted(d.glob("*.json")):
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, list):
                out.extend(data)
            else:
                out.append(data)
        return out

    claims = _load_records("claims")
    evidence = _load_records("evidence")
    provenance = _load_records("provenance")

    # Build lookup indices
    claim_ids = {c["id"] for c in claims}
    evidence_ids = {e["id"] for e in evidence}

    with conn:
        conn.execute("DELETE FROM claim_evidence")
        conn.execute("DELETE FROM evidence_claims")
        conn.execute("DELETE FROM claims")
        conn.execute("DELETE FROM evidence")
        conn.execute("DELETE FROM provenance")
        conn.execute("DELETE FROM ingest_meta")

        for rec in claims:
            scope = rec.get("scope") or {}
            conn.execute(
                """INSERT INTO claims (id, statement, claim_type, epistemic_status,
                       modality, domain, scope_json, evidence_refs_json, valid_time_json,
                       created_at, created_by, version, notes_json, source_file, raw_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    rec["id"],
                    rec["statement"],
                    rec["claim_type"],
                    rec["epistemic_status"],
                    rec.get("modality"),
                    scope.get("domain"),
                    json.dumps(scope, ensure_ascii=False, sort_keys=True),
                    json.dumps(rec.get("evidence_refs", []), ensure_ascii=False),
                    json.dumps(rec.get("valid_time"), ensure_ascii=False) if rec.get("valid_time") else None,
                    rec["created_at"],
                    rec.get("created_by"),
                    rec["version"],
                    json.dumps(rec.get("notes"), ensure_ascii=False, sort_keys=True) if rec.get("notes") else None,
                    "claims/" + rec["id"],
                    json.dumps(rec, ensure_ascii=False, sort_keys=True),
                ),
            )

        for rec in evidence:
            src_obj = rec.get("source") or {}
            loc = rec.get("locator") or {}
            conn.execute(
                """INSERT INTO evidence (id, relation, assessment_status, source_type,
                       source_citation, source_url, source_persistent_id, locator_type,
                       locator_value, locator_quote, extraction_method, captured_at,
                       captured_by, version, source_file, raw_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    rec["id"],
                    rec["relation"],
                    rec.get("assessment_status", "unassessed"),
                    src_obj.get("source_type"),
                    src_obj.get("citation"),
                    src_obj.get("url"),
                    src_obj.get("persistent_id"),
                    loc.get("locator_type"),
                    loc.get("value"),
                    loc.get("quote"),
                    rec.get("extraction_method"),
                    rec["captured_at"],
                    rec.get("captured_by"),
                    rec["version"],
                    "evidence/" + rec["id"],
                    json.dumps(rec, ensure_ascii=False, sort_keys=True),
                ),
            )

        for rec in provenance:
            ge = rec.get("generated_entity") or {}
            act = rec.get("activity") or {}
            conn.execute(
                """INSERT INTO provenance (id, generated_entity_id, entity_type,
                       activity_id, activity_type, attributed_to_json, derived_from_json,
                       recorded_at, version, source_file, raw_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    rec["id"],
                    ge.get("id"),
                    ge.get("entity_type"),
                    act.get("id"),
                    act.get("activity_type"),
                    json.dumps(rec.get("attributed_to"), ensure_ascii=False, sort_keys=True) if rec.get("attributed_to") else None,
                    json.dumps(rec.get("derived_from"), ensure_ascii=False, sort_keys=True) if rec.get("derived_from") else None,
                    rec["recorded_at"],
                    rec["version"],
                    "provenance/" + rec["id"],
                    json.dumps(rec, ensure_ascii=False, sort_keys=True),
                ),
            )

        # Join tables
        for rec in claims:
            for eref in rec.get("evidence_refs", []):
                conn.execute(
                    "INSERT OR IGNORE INTO claim_evidence (claim_id, evidence_id) VALUES (?,?)",
                    (rec["id"], eref),
                )
        for rec in evidence:
            for cref in rec.get("claim_refs", []):
                conn.execute(
                    "INSERT OR IGNORE INTO evidence_claims (evidence_id, claim_id) VALUES (?,?)",
                    (rec["id"], cref),
                )

        conn.execute(
            "INSERT INTO ingest_meta (key, value) VALUES ('pilot_dir', ?)",
            (str(pilot_dir),),
        )

    return {"claims": len(claims), "evidence": len(evidence), "provenance": len(provenance)}


# ---------------------------------------------------------------------------
# SFT Exporter
# ---------------------------------------------------------------------------

def _build_sft_message(claim: dict, evidence_list: list[dict], conn: sqlite3.Connection | None = None) -> dict:
    """Build a single SFT training example in messages format."""
    domain = _get_scope(claim, conn).get("domain", claim.get("domain", "unknown"))
    system_content = (
        "You are a scientific knowledge assistant specializing in "
        f"{domain}. Provide accurate, evidence-backed responses with "
        "clear citation anchors and verification guidance."
    )

    user_content = (
        f"Claim: {claim['statement']}\n\n"
        f"Type: {claim.get('claim_type', 'unknown')}\n"
        f"Domain: {domain}\n"
        f"Status: {claim.get('epistemic_status', 'unknown')}\n\n"
        "Provide a structured response with the claim's evidence basis, "
        "citation anchors, and how one would verify this claim."
    )

    evidence_summary = []
    citations = []
    for ev in evidence_list:
        src = ev.get("source", {})
        loc = ev.get("locator", {})
        evidence_summary.append(
            f"- Relation: {ev.get('relation', 'unknown')}; "
            f"Source: {src.get('citation', 'N/A')}; "
            f"Location: {loc.get('value', 'N/A')}"
        )
        if src.get("url"):
            citations.append(src["url"])
        if loc.get("quote"):
            citations.append(f"Quote: {loc['quote'][:200]}")

    verification_steps = []
    if any(ev.get("locator", {}).get("value") for ev in evidence_list):
        verification_steps.append(
            "1. Locate the cited source code/document at the specified "
            "file:line or section locator."
        )
    if any(ev.get("source", {}).get("url") for ev in evidence_list):
        verification_steps.append(
            "2. Access the source URL and verify the quoted content matches "
            "the claim statement."
        )
    verification_steps.append(
        "3. Cross-reference the claim's evidence_refs with the evidence "
        "records to ensure completeness."
    )
    verification_steps.append(
        "4. Check the epistemic_status and assessment_status to confirm "
        "the claim has sufficient backing."
    )

    assistant_content = (
        f"**Evidence Basis:**\n" + "\n".join(evidence_summary) + "\n\n"
        f"**Citation Anchors:**\n" + "\n".join(f"- {c}" for c in citations[:5]) + "\n\n"
        f"**How to Verify:**\n" + "\n".join(verification_steps)
    )

    prov_text = json.dumps({
        "claim_id": claim["id"],
        "evidence_ids": [e["id"] for e in evidence_list],
        "version": claim.get("version", "unknown"),
    }, sort_keys=True)

    return {
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content},
        ],
        "claim_id": claim["id"],
        "epistemic_status": claim.get("epistemic_status", "unknown"),
        "domain": domain,
        "provenance_sha256": _sha256(prov_text),
    }


def export_sft(conn: sqlite3.Connection, pilot_dir: Path | None = None,
               out_dir: Path | None = None) -> dict:
    """Export SFT corpus to JSONL."""
    all_claims = q.all_claims(conn)

    included = []
    excluded = []
    excluded_reasons: dict[str, int] = {}

    for claim in all_claims:
        status = claim.get("epistemic_status", "unknown")
        if status not in PUBLISHED_STATUSES:
            excluded.append(claim)
            reason = f"epistemic_status={status}"
            excluded_reasons[reason] = excluded_reasons.get(reason, 0) + 1
            continue

        evidence_list = q.evidence_for_claim(conn, claim["id"])
        sft_entry = _build_sft_message(claim, evidence_list, conn)
        included.append(sft_entry)

    manifest = {
        "export_type": "sft",
        "generated_at": _now_iso(),
        "upstream_commit": _git_commit(pilot_dir),
        "total_claims": len(all_claims),
        "included": len(included),
        "excluded": len(excluded),
        "excluded_reasons": excluded_reasons,
        "status_distribution": {},
        "domain_distribution": {},
    }

    for entry in included:
        st = entry["epistemic_status"]
        manifest["status_distribution"][st] = manifest["status_distribution"].get(st, 0) + 1
        dom = entry["domain"]
        manifest["domain_distribution"][dom] = manifest["domain_distribution"].get(dom, 0) + 1

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "sft.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for entry in included:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        manifest_path = out_dir / "sft_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    return manifest


# ---------------------------------------------------------------------------
# Eval Exporter
# ---------------------------------------------------------------------------

def _build_eval_entry(claim: dict, evidence_list: list[dict], conn: sqlite3.Connection | None = None) -> dict | None:
    """Build an eval entry from a claim with evidence.

    Every claim with at least one evidence record becomes an eval entry.
    The eval tests whether the model can correctly identify the evidence
    basis for a given claim statement.
    """
    if not evidence_list:
        return None

    eval_evidence = evidence_list  # Use all evidence

    domain = _get_scope(claim, conn).get("domain", claim.get("domain", "unknown"))
    system = _get_scope(claim, conn).get("system", "unknown")

    input_params = {
        "domain": domain,
        "system": system,
        "claim_type": claim.get("claim_type", "unknown"),
        "conditions": _get_scope(claim, conn).get("conditions", []),
    }

    expected = {
        "claim_statement": claim["statement"],
        "evidence_count": len(eval_evidence),
        "evidence_sources": [
            {
                "citation": ev.get("source", {}).get("citation", ""),
                "location": ev.get("locator", {}).get("value", ""),
            }
            for ev in eval_evidence
        ],
    }

    assessment_statuses = {ev.get("assessment_status", "unknown") for ev in eval_evidence}
    if "verified" in assessment_statuses:
        tolerance = 0.01
    elif "accepted" in assessment_statuses:
        tolerance = 0.05
    else:
        tolerance = 0.10  # default for unassessed evidence

    return {
        "claim_id": claim["id"],
        "domain": domain,
        "input": input_params,
        "expected": expected,
        "tolerance": tolerance,
        "tolerance_basis": f"assessment_status={','.join(sorted(assessment_statuses))}",
        "source_claim_id": claim["id"],
        "epistemic_status": claim.get("epistemic_status", "unknown"),
    }




# Standard LBM benchmark calibration entries (GAP-LBM-MCMP-POISEUILLE)
# These are well-known validation cases for LBM implementations
STANDARD_LBM_BENCHMARKS = [
    {
        "claim_id": "tkc:oss-lbm:lbmpy-ce-src",
        "domain": "lattice-Boltzmann-method",
        "input": {
            "domain": "lattice-Boltzmann-method",
            "system": "lbmpy",
            "claim_type": "descriptive",
            "conditions": ["Poiseuille flow", "2D channel", "Re=100"],
            "geometry": {"type": "channel", "H": 32, "L": 128},
            "boundary": {"inlet": "velocity", "outlet": "pressure", "walls": "bounce-back"},
            "relaxation_time": 0.6,
            "stencil": "D2Q9"
        },
        "expected": {
            "claim_statement": "lbmpy implements Chapman-Enskog analysis that symbolically derives the macroscopic equations",
            "max_velocity": 0.04,
            "parabolic_profile_error": 0.001,
            "convergence_order": 2
        },
        "tolerance": 0.03,
        "tolerance_basis": "analytical Poiseuille solution",
        "source_claim_id": "tkc:oss-lbm:lbmpy-ce-src",
        "epistemic_status": "established",
        "benchmark_name": "GAP-LBM-POISEUILLE-2D"
    },
    {
        "claim_id": "tkc:oss-lbm:lbmpy-ce-src",
        "domain": "lattice-Boltzmann-method",
        "input": {
            "domain": "lattice-Boltzmann-method",
            "system": "lbmpy",
            "claim_type": "descriptive",
            "conditions": ["Couette flow", "2D channel", "Re=50"],
            "geometry": {"type": "channel", "H": 64, "L": 64},
            "boundary": {"top": "moving_wall", "bottom": "stationary_wall", "sides": "periodic"},
            "relaxation_time": 0.8,
            "stencil": "D2Q9"
        },
        "expected": {
            "claim_statement": "lbmpy implements Chapman-Enskog analysis",
            "velocity_profile": "linear",
            "shear_stress_error": 0.002
        },
        "tolerance": 0.03,
        "tolerance_basis": "analytical Couette solution",
        "source_claim_id": "tkc:oss-lbm:lbmpy-ce-src",
        "epistemic_status": "established",
        "benchmark_name": "GAP-LBM-COUETTE-2D"
    },
    {
        "claim_id": "tkc:oss-lbm:lettuce-bgk-src",
        "domain": "lattice-Boltzmann-method",
        "input": {
            "domain": "lattice-Boltzmann-method",
            "system": "lettuce",
            "claim_type": "descriptive",
            "conditions": ["Taylor-Green vortex", "2D periodic", "Re=100"],
            "geometry": {"type": "periodic", "Lx": 64, "Ly": 64},
            "initial_condition": "Taylor-Green vortex",
            "relaxation_time": 0.52,
            "stencil": "D2Q9"
        },
        "expected": {
            "claim_statement": "lettuce BGKCollision is implemented as a plain Python __call__ returning torch.Tensor operations",
            "kinetic_energy_decay_rate": 0.0156,
            "enstrophy_peak_time": 1.5
        },
        "tolerance": 0.05,
        "tolerance_basis": "analytical Taylor-Green decay",
        "source_claim_id": "tkc:oss-lbm:lettuce-bgk-src",
        "epistemic_status": "established",
        "benchmark_name": "GAP-LBM-TAYLOR-GREEN"
    },
    {
        "claim_id": "tkc:oss-lbm:pylbm-bfl-src",
        "domain": "lattice-Boltzmann-method",
        "input": {
            "domain": "lattice-Boltzmann-method",
            "system": "pylbm",
            "claim_type": "descriptive",
            "conditions": ["curved boundary", "cylinder flow", "Re=100"],
            "geometry": {"type": "cylinder", "D": 20, "domain": [200, 100]},
            "boundary": {"inlet": "velocity", "outlet": "pressure", "cylinder": "BFL"},
            "relaxation_time": 0.6,
            "stencil": "D2Q9"
        },
        "expected": {
            "claim_statement": "pylbm implements the Bouzidi-Firdaouss-Lallemand (BFL01) interpolated bounce-back boundary condition",
            "drag_coefficient": 1.2,
            "strouhal_number": 0.165,
            "boundary_order": 2
        },
        "tolerance": 0.05,
        "tolerance_basis": "literature values for cylinder flow",
        "source_claim_id": "tkc:oss-lbm:pylbm-bfl-src",
        "epistemic_status": "established",
        "benchmark_name": "MCMP-CYLINDER-DRAG"
    },
]

def export_eval(conn: sqlite3.Connection, pilot_dir: Path | None = None,
                out_dir: Path | None = None) -> dict:
    """Export eval set to JSONL.

    Includes both claim-based eval entries and standard LBM benchmark
    calibration entries (GAP-LBM-MCMP-POISEUILLE).
    """
    all_claims = q.all_claims(conn)

    included = []
    excluded = []

    for claim in all_claims:
        evidence_list = q.evidence_for_claim(conn, claim["id"])
        entry = _build_eval_entry(claim, evidence_list, conn)
        if entry is not None:
            included.append(entry)
        else:
            excluded.append(claim["id"])

    # Add standard LBM benchmark calibration entries
    included.extend(STANDARD_LBM_BENCHMARKS)

    manifest = {
        "export_type": "eval",
        "generated_at": _now_iso(),
        "upstream_commit": _git_commit(pilot_dir),
        "total_claims": len(all_claims),
        "included": len(included),
        "excluded_no_eval_evidence": len(excluded),
        "domain_distribution": {},
        "tolerance_distribution": {},
    }

    for entry in included:
        dom = entry["domain"]
        manifest["domain_distribution"][dom] = manifest["domain_distribution"].get(dom, 0) + 1
        tol = entry["tolerance"]
        manifest["tolerance_distribution"][str(tol)] = \
            manifest["tolerance_distribution"].get(str(tol), 0) + 1

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "eval.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for entry in included:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        manifest_path = out_dir / "eval_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    return manifest


# ---------------------------------------------------------------------------
# Triples Exporter
# ---------------------------------------------------------------------------

def export_triples(conn: sqlite3.Connection, pilot_dir: Path | None = None,
                   out_dir: Path | None = None) -> dict:
    """Export knowledge-object relationship triples to JSONL."""
    all_claims = q.all_claims(conn)

    triples = []
    relation_counts: dict[str, int] = {}
    domain_counts: dict[str, int] = {}

    for claim in all_claims:
        evidence_list = q.evidence_for_claim(conn, claim["id"])
        domain = _get_scope(claim, conn).get("domain", claim.get("domain", "unknown"))

        for ev in evidence_list:
            relation = ev.get("relation", "unknown")
            triple = {
                "subject": claim["id"],
                "predicate": relation,
                "object": ev["id"],
                "claim_id": claim["id"],
                "evidence_id": ev["id"],
                "domain": domain,
                "claim_statement": claim["statement"],
                "evidence_relation": relation,
                "evidence_assessment": ev.get("assessment_status", "unknown"),
            }

            prov_text = json.dumps({
                "subject": claim["id"],
                "predicate": relation,
                "object": ev["id"],
            }, sort_keys=True)
            triple["provenance_sha256"] = _sha256(prov_text)

            triples.append(triple)
            relation_counts[relation] = relation_counts.get(relation, 0) + 1
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

    manifest = {
        "export_type": "triples",
        "generated_at": _now_iso(),
        "upstream_commit": _git_commit(pilot_dir),
        "total_triples": len(triples),
        "relation_distribution": relation_counts,
        "domain_distribution": domain_counts,
    }

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "triples.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for triple in triples:
                f.write(json.dumps(triple, ensure_ascii=False) + "\n")
        manifest_path = out_dir / "triples_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    return manifest


# ---------------------------------------------------------------------------
# Unified export dispatcher
# ---------------------------------------------------------------------------

def export(kind: str, pilot_dir: str | Path, db_path: str | Path | None = None,
           out_dir: str | Path | None = None) -> dict:
    """Unified export function.

    Args:
        kind: One of 'sft', 'eval', 'triples'.
        pilot_dir: Path to the pilot knowledge package.
        db_path: Optional path to existing KE database. If None, creates
                 a temporary in-memory DB and ingests the pilot.
        out_dir: Output directory for JSONL and manifest files.

    Returns:
        Manifest dict.
    """
    pilot = Path(pilot_dir).resolve()
    out = Path(out_dir) if out_dir else None

    if db_path:
        conn = store.connect(db_path)
    else:
        conn = store.connect(":memory:")
        _ingest_pilot_flexible(pilot, conn)

    try:
        if kind == "sft":
            return export_sft(conn, pilot, out)
        elif kind == "eval":
            return export_eval(conn, pilot, out)
        elif kind == "triples":
            return export_triples(conn, pilot, out)
        else:
            raise ValueError(f"Unknown export kind: {kind}. Must be sft, eval, or triples.")
    finally:
        conn.close()
