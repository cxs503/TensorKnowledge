#!/usr/bin/env python3
"""Sediment → KE assertion relay (m14356 / FEAT-TK-GOV-INFRA).

Bridges the gap between sediment extraction packages (knowledge/sediment/m{id}/)
and the Knowledge Engine SQLite store.  Each sediment package contains
four-contract JSON files (claim-*.json, evidence-*.json, provenance-*.json)
that this relay validates, maps, and upserts into the KE database.

Design
------
* **Idempotent**: re-running on the same sediment directory produces the same
  database state.  Uses task_key (mission id) to track ingestion; existing
  records for the same mission are replaced atomically.
* **Failure-isolated**: a bad record in one mission does not block other
  missions.  Per-mission results are logged; the relay continues.
* **Schema-mapped**: claim/evidence/provenance → ke entity tables with
  scope/anchor preservation.
* **Accumulative**: all valid records from all missions are combined into a
  single pilot directory and ingested in one transaction (since ke.store.ingest_pilot
  replaces all records).

Usage::

    # Relay all sediment packages into a new KE database
    python scripts/sediment_ke_relay.py --db /tmp/ke_sediment.db

    # Relay specific missions only
    python scripts/sediment_ke_relay.py --db /tmp/ke.db --missions m8381 m2591

    # Dry-run: validate only, don't write
    python scripts/sediment_ke_relay.py --db /tmp/ke.db --dry-run

    # Also ingest oss-lbm packages (converted to sediment format on-the-fly)
    python scripts/sediment_ke_relay.py --db /tmp/ke.db --include-oss-lbm
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sqlite3
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure repo root is on path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

from ke import store as ke_store
from ke import queries as ke_queries

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("sediment_ke_relay")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEDIMENT_DIR = REPO_ROOT / "knowledge" / "sediment"
SCHEMAS_DIR = REPO_ROOT / "schemas"
RELAY_META_TABLE = "sediment_relay_meta"

# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def _validate_record_minimal(rec: dict, kind: str) -> list[str]:
    """Minimal structural validation without jsonschema."""
    errors = []
    if kind == "claim":
        for field in ("id", "statement", "claim_type", "epistemic_status", "created_at", "version"):
            if field not in rec:
                errors.append(f"missing required field: {field}")
        if "id" in rec and not rec["id"].startswith("tkc:"):
            errors.append(f"claim id must start with 'tkc:', got {rec['id']!r}")
    elif kind == "evidence":
        for field in ("id", "source", "relation", "locator", "captured_at", "assessment_status", "version"):
            if field not in rec:
                errors.append(f"missing required field: {field}")
        if "id" in rec and not rec["id"].startswith("tke:"):
            errors.append(f"evidence id must start with 'tke:', got {rec['id']!r}")
    elif kind == "provenance":
        for field in ("id", "generated_entity", "activity", "agents", "recorded_at", "version"):
            if field not in rec:
                errors.append(f"missing required field: {field}")
        if "id" in rec and not rec["id"].startswith("tkp:"):
            errors.append(f"provenance id must start with 'tkp:', got {rec['id']!r}")
    return errors


def _try_jsonschema_validate(rec: dict, kind: str) -> list[str]:
    """Full jsonschema validation if available, else minimal."""
    try:
        import jsonschema
    except ImportError:
        return _validate_record_minimal(rec, kind)

    schema_map = {
        "claim": "claim-record.schema.json",
        "evidence": "evidence-record.schema.json",
        "provenance": "provenance-record.schema.json",
    }
    schema_file = SCHEMAS_DIR / schema_map[kind]
    if not schema_file.exists():
        return _validate_record_minimal(rec, kind)

    doc = json.loads(schema_file.read_text(encoding="utf-8"))
    try:
        jsonschema.Draft202012Validator(doc).validate(rec)
        return []
    except jsonschema.ValidationError as e:
        return [str(e.message)[:300]]


# ---------------------------------------------------------------------------
# Sediment package reader
# ---------------------------------------------------------------------------

def read_sediment_package(mission_dir: Path) -> dict[str, list[dict]]:
    """Read a sediment package directory.

    Returns {"claims": [...], "evidence": [...], "provenance": [...]}
    Handles both individual files (claim-*.json) and aggregate files (claims.json).
    """
    result: dict[str, list[dict]] = {"claims": [], "evidence": [], "provenance": []}

    if not mission_dir.is_dir():
        raise FileNotFoundError(f"sediment dir not found: {mission_dir}")

    # Map: (result_key, file_prefix, aggregate_filename)
    specs = [
        ("claims", "claim-", "claims.json"),
        ("evidence", "evidence-", "evidence.json"),
        ("provenance", "provenance-", "provenance.json"),
    ]

    for result_key, prefix, aggregate_name in specs:
        records = []

        # Try individual files first (claim-01.json, evidence-01.json, ...)
        individual_files = sorted(mission_dir.glob(f"{prefix}*.json"))
        if individual_files:
            for f in individual_files:
                try:
                    rec = json.loads(f.read_text(encoding="utf-8"))
                    records.append(rec)
                except (json.JSONDecodeError, OSError) as e:
                    log.warning(f"  bad file {f}: {e}")
        else:
            # Try aggregate file (claims.json, evidence.json, ...)
            agg = mission_dir / aggregate_name
            if agg.exists():
                try:
                    data = json.loads(agg.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        records.extend(data)
                    elif isinstance(data, dict):
                        records.append(data)
                except (json.JSONDecodeError, OSError) as e:
                    log.warning(f"  bad aggregate {agg}: {e}")

            # Try subdirectory layout: claims/*.json, evidence/*.json, provenance/*.json
            subdir_name = result_key  # claims, evidence, provenance
            sub = mission_dir / subdir_name
            if sub.is_dir():
                for f in sorted(sub.glob("*.json")):
                    if f.name == aggregate_name:
                        continue
                    try:
                        rec = json.loads(f.read_text(encoding="utf-8"))
                        records.append(rec)
                    except (json.JSONDecodeError, OSError) as e:
                        log.warning(f"  bad file {f}: {e}")
                # Also try aggregate in subdir if no individual files found
                agg2 = sub / aggregate_name
                if agg2.exists() and not records:
                    try:
                        data = json.loads(agg2.read_text(encoding="utf-8"))
                        if isinstance(data, list):
                            records.extend(data)
                    except (json.JSONDecodeError, OSError):
                        pass

        result[result_key] = records

    return result


def read_oss_lbm_package(pkg_dir: Path) -> dict[str, list[dict]]:
    """Read an oss-lbm knowledge package (aggregate JSON format)."""
    result: dict[str, list[dict]] = {"claims": [], "evidence": [], "provenance": []}

    claims_file = pkg_dir / "claims" / "claims.json"
    if claims_file.exists():
        data = json.loads(claims_file.read_text(encoding="utf-8"))
        result["claims"] = data if isinstance(data, list) else [data]

    evidence_file = pkg_dir / "evidence" / "evidence.json"
    if evidence_file.exists():
        data = json.loads(evidence_file.read_text(encoding="utf-8"))
        result["evidence"] = data if isinstance(data, list) else [data]

    provenance_file = pkg_dir / "provenance" / "provenance.json"
    if provenance_file.exists():
        data = json.loads(provenance_file.read_text(encoding="utf-8"))
        result["provenance"] = data if isinstance(data, list) else [data]

    return result


# ---------------------------------------------------------------------------
# Relay meta table (idempotency tracking)
# ---------------------------------------------------------------------------

RELAY_META_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {RELAY_META_TABLE} (
    mission_id   TEXT PRIMARY KEY,
    task_key     TEXT NOT NULL,
    status       TEXT NOT NULL CHECK (status IN ('succeeded', 'failed', 'partial', 'skipped')),
    claims_count INTEGER NOT NULL DEFAULT 0,
    evidence_count INTEGER NOT NULL DEFAULT 0,
    provenance_count INTEGER NOT NULL DEFAULT 0,
    error_detail TEXT,
    ingested_at  TEXT NOT NULL,
    source_dir   TEXT
);
"""


def init_relay_meta(conn: sqlite3.Connection) -> None:
    conn.execute(RELAY_META_SCHEMA)
    conn.commit()


def set_relay_status(
    conn: sqlite3.Connection,
    mission_id: str,
    task_key: str,
    status: str,
    claims: int,
    evidence: int,
    provenance: int,
    error_detail: str | None,
    source_dir: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        f"""INSERT OR REPLACE INTO {RELAY_META_TABLE}
            (mission_id, task_key, status, claims_count, evidence_count,
             provenance_count, error_detail, ingested_at, source_dir)
            VALUES (?,?,?,?,?,?,?,?,?)""",
        (mission_id, task_key, status, claims, evidence, provenance,
         error_detail, now, source_dir),
    )


# ---------------------------------------------------------------------------
# Core relay: accumulate all packages → single pilot dir → ke ingest
# ---------------------------------------------------------------------------

def _sanitize_id_for_filename(record_id: str) -> str:
    """Convert a record ID to a safe filename."""
    return record_id.replace(":", "_").replace("/", "_")


def relay_all(
    sediment_dir: Path,
    db_path: str,
    missions: list[str] | None = None,
    dry_run: bool = False,
    include_oss_lbm: bool = False,
) -> dict[str, Any]:
    """Relay all (or selected) sediment packages into the KE database.

    Strategy: accumulate all records from all missions into a single temporary
    pilot directory, then call ke.store.ingest_pilot() once. This is necessary
    because ingest_pilot() replaces all existing records.

    Returns summary with per-mission results and aggregate stats.
    """
    summary = {
        "db_path": db_path,
        "sediment_dir": str(sediment_dir),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "missions": [],
        "totals": {"succeeded": 0, "failed": 0, "partial": 0, "skipped": 0},
        "total_claims": 0,
        "total_evidence": 0,
        "total_provenance": 0,
    }

    # Discover missions
    if not sediment_dir.is_dir():
        log.error(f"Sediment directory not found: {sediment_dir}")
        summary["error"] = f"sediment directory not found: {sediment_dir}"
        return summary

    mission_dirs = sorted([
        d for d in sediment_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ])

    if missions:
        mission_dirs = [d for d in mission_dirs if d.name in missions]

    if not mission_dirs and not include_oss_lbm:
        log.warning("No sediment missions found to relay")
        return summary

    log.info(f"Found {len(mission_dirs)} sediment missions to relay")

    # Phase 1: Read and validate all packages, accumulate records
    all_claims: dict[str, dict] = {}  # id -> record (dedup by id)
    all_evidence: dict[str, dict] = {}
    all_provenance: dict[str, dict] = {}
    mission_results: list[dict] = []

    # Process sediment packages
    for mdir in mission_dirs:
        mid = mdir.name
        task_key = f"tk-sediment-{mid}"
        result = {
            "mission_id": mid,
            "task_key": task_key,
            "status": "pending",
            "claims": 0,
            "evidence": 0,
            "provenance": 0,
            "validation_errors": [],
            "error": None,
        }

        try:
            package = read_sediment_package(mdir)
        except FileNotFoundError as e:
            result["status"] = "failed"
            result["error"] = str(e)
            mission_results.append(result)
            summary["totals"]["failed"] += 1
            continue

        claims = package["claims"]
        evidence = package["evidence"]
        provenance = package["provenance"]

        if not claims and not evidence and not provenance:
            result["status"] = "skipped"
            result["error"] = "empty package"
            mission_results.append(result)
            summary["totals"]["skipped"] += 1
            continue

        log.info(f"  {mid}: {len(claims)}c / {len(evidence)}e / {len(provenance)}p")

        # Validate
        errors = []
        for c in claims:
            errs = _try_jsonschema_validate(c, "claim")
            if errs:
                errors.append(f"claim {c.get('id', '?')}: {'; '.join(errs)}")
            else:
                all_claims[c["id"]] = c
        for e in evidence:
            errs = _try_jsonschema_validate(e, "evidence")
            if errs:
                errors.append(f"evidence {e.get('id', '?')}: {'; '.join(errs)}")
            else:
                all_evidence[e["id"]] = e
        for p in provenance:
            errs = _try_jsonschema_validate(p, "provenance")
            if errs:
                errors.append(f"provenance {p.get('id', '?')}: {'; '.join(errs)}")
            else:
                all_provenance[p["id"]] = p

        result["validation_errors"] = errors
        result["claims"] = len(claims)
        result["evidence"] = len(evidence)
        result["provenance"] = len(provenance)
        result["status"] = "partial" if errors else "succeeded"

        if errors:
            log.warning(f"    {len(errors)} validation errors (records still included)")

        mission_results.append(result)
        summary["total_claims"] += len(claims)
        summary["total_evidence"] += len(evidence)
        summary["total_provenance"] += len(provenance)

    # Process oss-lbm packages if requested
    if include_oss_lbm:
        oss_lbm_dir = REPO_ROOT / "knowledge" / "oss-lbm"
        if oss_lbm_dir.is_dir():
            for pkg_dir in sorted(oss_lbm_dir.iterdir()):
                if not pkg_dir.is_dir() or pkg_dir.name.startswith("."):
                    continue
                pkg_name = pkg_dir.name
                mid = f"oss-lbm-{pkg_name}"
                task_key = f"tk-sediment-{mid}"

                # Skip if already processed as sediment
                if any(m["mission_id"] == mid for m in mission_results):
                    continue

                result = {
                    "mission_id": mid,
                    "task_key": task_key,
                    "status": "pending",
                    "claims": 0,
                    "evidence": 0,
                    "provenance": 0,
                    "validation_errors": [],
                    "error": None,
                }

                try:
                    package = read_oss_lbm_package(pkg_dir)
                except Exception as e:
                    result["status"] = "failed"
                    result["error"] = str(e)
                    mission_results.append(result)
                    summary["totals"]["failed"] += 1
                    continue

                claims = package["claims"]
                evidence = package["evidence"]
                provenance = package["provenance"]

                if not claims and not evidence and not provenance:
                    result["status"] = "skipped"
                    result["error"] = "empty package"
                    mission_results.append(result)
                    summary["totals"]["skipped"] += 1
                    continue

                log.info(f"  {mid}: {len(claims)}c / {len(evidence)}e / {len(provenance)}p")

                errors = []
                for c in claims:
                    errs = _try_jsonschema_validate(c, "claim")
                    if errs:
                        errors.append(f"claim {c.get('id', '?')}: {'; '.join(errs)}")
                    else:
                        all_claims[c["id"]] = c
                for e in evidence:
                    errs = _try_jsonschema_validate(e, "evidence")
                    if errs:
                        errors.append(f"evidence {e.get('id', '?')}: {'; '.join(errs)}")
                    else:
                        all_evidence[e["id"]] = e
                for p in provenance:
                    errs = _try_jsonschema_validate(p, "provenance")
                    if errs:
                        errors.append(f"provenance {p.get('id', '?')}: {'; '.join(errs)}")
                    else:
                        all_provenance[p["id"]] = p

                result["validation_errors"] = errors
                result["claims"] = len(claims)
                result["evidence"] = len(evidence)
                result["provenance"] = len(provenance)
                result["status"] = "partial" if errors else "succeeded"

                mission_results.append(result)
                summary["total_claims"] += len(claims)
                summary["total_evidence"] += len(evidence)
                summary["total_provenance"] += len(provenance)

    summary["missions"] = mission_results

    # Phase 2: Write combined pilot directory and ingest
    if dry_run:
        for m in mission_results:
            if m["status"] == "pending":
                m["status"] = "dry-run"
            summary["totals"][m["status"]] = summary["totals"].get(m["status"], 0) + 1
        log.info(f"DRY RUN: {len(all_claims)} claims, {len(all_evidence)} evidence, {len(all_provenance)} provenance")
        return summary

    if not all_claims and not all_evidence and not all_provenance:
        log.warning("No valid records to ingest")
        for m in mission_results:
            summary["totals"].get(m["status"], 0)
        return summary

    log.info(f"Accumulated: {len(all_claims)} claims, {len(all_evidence)} evidence, {len(all_provenance)} provenance")

    # Create temp pilot directory
    pilot_dir = Path(tempfile.mkdtemp(prefix="sediment_relay_"))
    try:
        # Write claims
        claims_dir = pilot_dir / "claims"
        claims_dir.mkdir()
        for cid, rec in all_claims.items():
            fname = _sanitize_id_for_filename(cid) + ".json"
            (claims_dir / fname).write_text(
                json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        # Write evidence
        evidence_dir = pilot_dir / "evidence"
        evidence_dir.mkdir()
        for eid, rec in all_evidence.items():
            fname = _sanitize_id_for_filename(eid) + ".json"
            (evidence_dir / fname).write_text(
                json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        # Write provenance
        provenance_dir = pilot_dir / "provenance"
        provenance_dir.mkdir()
        for pid, rec in all_provenance.items():
            fname = _sanitize_id_for_filename(pid) + ".json"
            (provenance_dir / fname).write_text(
                json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        # Connect and ingest
        conn = ke_store.connect(db_path)
        init_relay_meta(conn)

        counts = ke_store.ingest_pilot(str(pilot_dir), conn)
        log.info(f"Ingested: {counts}")

        # Record relay status for each mission
        for m in mission_results:
            try:
                set_relay_status(
                    conn, m["mission_id"], m["task_key"], m["status"],
                    m["claims"], m["evidence"], m["provenance"],
                    m.get("error"), "",
                )
            except Exception as e:
                log.error(f"  Failed to record meta for {m['mission_id']}: {e}")

        conn.commit()

        # Update totals
        for m in mission_results:
            status = m["status"]
            if status in summary["totals"]:
                summary["totals"][status] += 1

        # Get final database stats
        try:
            db_stats = ke_queries.stats(conn)
            summary["ke_database_stats"] = db_stats
        except Exception:
            pass

    except Exception as e:
        log.error(f"Ingest failed: {e}")
        log.debug(traceback.format_exc())
        summary["error"] = f"ingest failed: {e}"
        for m in mission_results:
            if m["status"] in ("succeeded", "partial"):
                m["status"] = "failed"
                m["error"] = str(e)
    finally:
        shutil.rmtree(pilot_dir, ignore_errors=True)

    summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    return summary


# ---------------------------------------------------------------------------
# Query helper: verify assertions are queryable
# ---------------------------------------------------------------------------

def verify_ke_queryable(db_path: str) -> dict:
    """Verify that assertions in the KE database are queryable via the API."""
    conn = ke_store.connect(db_path)
    result = {
        "total_claims": 0,
        "total_evidence": 0,
        "total_provenance": 0,
        "sample_claims": [],
        "claims_by_status": {},
        "queryable": False,
    }

    try:
        stats = ke_queries.stats(conn)
        result["total_claims"] = stats["claims"]
        result["total_evidence"] = stats["evidence"]
        result["total_provenance"] = stats["provenance"]
        result["claims_by_status"] = stats["claims_by_status"]

        # Get sample claims
        all_c = ke_queries.all_claims(conn)
        result["sample_claims"] = [
            {"id": c["id"], "statement": c["statement"][:80], "status": c["epistemic_status"]}
            for c in all_c[:10]
        ]

        result["queryable"] = stats["claims"] > 0
    except Exception as e:
        result["error"] = str(e)

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="sediment_ke_relay",
        description="Relay sediment extraction packages into the Knowledge Engine",
    )
    ap.add_argument("--db", required=True, help="KE SQLite database path")
    ap.add_argument("--sediment-dir", default=str(SEDIMENT_DIR),
                    help="Sediment packages directory (default: knowledge/sediment)")
    ap.add_argument("--missions", nargs="*", default=None,
                    help="Specific mission IDs to relay (default: all)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Validate only, don't write to database")
    ap.add_argument("--include-oss-lbm", action="store_true",
                    help="Also relay oss-lbm knowledge packages")
    ap.add_argument("--output", default=None,
                    help="Write summary JSON to this path")
    ap.add_argument("--verify", action="store_true",
                    help="After relay, verify assertions are queryable")
    ap.add_argument("--verbose", "-v", action="store_true")

    args = ap.parse_args(argv)
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    summary = relay_all(
        sediment_dir=Path(args.sediment_dir),
        db_path=args.db,
        missions=args.missions,
        dry_run=args.dry_run,
        include_oss_lbm=args.include_oss_lbm,
    )

    # Verify if requested
    if args.verify and not args.dry_run:
        verification = verify_ke_queryable(args.db)
        summary["verification"] = verification
        log.info(f"Verification: {verification['total_claims']} claims queryable")

    # Print summary
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        log.info(f"Summary written to {args.output}")

    # Exit code
    if summary["totals"].get("succeeded", 0) > 0 or summary["totals"].get("partial", 0) > 0:
        return 0
    if summary.get("dry_run"):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
