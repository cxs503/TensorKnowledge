"""Knowledge Asset Management — version chain, dataset assets, quality ledger,
and ASSET-INDEX compatible export.

Provides:
- KO version lifecycle (draft→in_review→published→deprecated) with supersede chains
- Dataset-level asset registration (sft/eval/triples) with immutability discipline
- Quality ledger aggregation per KO
- ASSET-INDEX compatible JSON export for platform ingestion
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Schema extensions (appended to existing SCHEMA in store.py)
# ---------------------------------------------------------------------------
ASSET_SCHEMA = """
-- KO version chain: each knowledge object can have multiple versions.
-- Physical deletes are forbidden; old versions are superseded.
CREATE TABLE IF NOT EXISTS ko_versions (
    id              TEXT PRIMARY KEY,
    ko_id           TEXT NOT NULL,          -- logical KO identifier (e.g. tko:oss-lbm:pylbm)
    version         TEXT NOT NULL,          -- semver string
    state           TEXT NOT NULL DEFAULT 'draft',  -- draft|in_review|published|deprecated
    title           TEXT,
    object_type     TEXT,
    summary         TEXT,
    content_json    TEXT,
    superseded_by   TEXT,                   -- ko_versions.id of the replacing version
    created_at      TEXT NOT NULL,
    created_by      TEXT,
    source_file     TEXT,
    raw_json        TEXT NOT NULL
);

-- Review events (append-only, mirrors review-event.schema.json)
CREATE TABLE IF NOT EXISTS review_events (
    id              TEXT PRIMARY KEY,
    object_ref      TEXT NOT NULL,
    object_version  TEXT,
    decision        TEXT NOT NULL,          -- approve|request-changes|reject|revoke|deprecate
    reviewer_json   TEXT NOT NULL,
    reviewed_at     TEXT NOT NULL,
    policy_version  TEXT NOT NULL,
    rationale       TEXT,
    findings_json   TEXT,
    supersedes_event TEXT,
    conditions_json TEXT,
    source_file     TEXT,
    raw_json        TEXT NOT NULL
);

-- Dataset-level assets (sft/eval/triples exports from m8810)
CREATE TABLE IF NOT EXISTS dataset_assets (
    id              TEXT PRIMARY KEY,       -- tka:<domain>:<name>:v<semver>
    asset_type      TEXT NOT NULL,          -- sft|eval|triples
    version         TEXT NOT NULL,
    record_count    INTEGER NOT NULL,
    status_dist_json TEXT,                  -- {"train": N, "valid": N, ...}
    sha256          TEXT NOT NULL,
    gen_params_json TEXT,                   -- generation parameters
    upstream_commit TEXT,                   -- git commit that produced this dataset
    created_at      TEXT NOT NULL,
    created_by      TEXT,
    source_file     TEXT,
    raw_json        TEXT NOT NULL
);

-- Quality ledger: aggregated metrics per KO (computed, not stored raw)
-- This is a materialized view table, refreshed on demand.
CREATE TABLE IF NOT EXISTS quality_ledger (
    ko_id           TEXT PRIMARY KEY,
    evidence_count  INTEGER NOT NULL DEFAULT 0,
    citation_count  INTEGER NOT NULL DEFAULT 0,
    falsified_count INTEGER NOT NULL DEFAULT 0,
    last_review_at  TEXT,
    last_review_decision TEXT,
    state           TEXT,
    version         TEXT,
    is_stale        INTEGER NOT NULL DEFAULT 0,  -- 1 if published and >30 days since last review
    computed_at     TEXT NOT NULL
);
"""

# ---------------------------------------------------------------------------
# State machine transitions
# ---------------------------------------------------------------------------
VALID_STATES = {"draft", "in_review", "published", "deprecated"}
STATE_TRANSITIONS = {
    "draft": {"in_review", "deprecated"},
    "in_review": {"published", "draft", "deprecated"},
    "published": {"deprecated", "in_review"},
    "deprecated": set(),  # terminal
}


def _validate_transition(current: str, target: str) -> None:
    allowed = STATE_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValueError(
            f"Invalid state transition: {current!r} → {target!r}. "
            f"Allowed: {sorted(allowed)}"
        )


# ---------------------------------------------------------------------------
# KO version management
# ---------------------------------------------------------------------------
def register_ko_version(
    conn: sqlite3.Connection,
    ko_id: str,
    version: str,
    title: str = "",
    object_type: str = "",
    summary: str = "",
    content: dict | None = None,
    state: str = "draft",
    created_by: str = "",
    source_file: str = "",
    raw_json: str = "",
    superseded_by: str | None = None,
) -> str:
    """Register a new KO version. Returns the version id."""
    vid = f"{ko_id}:v{version}"
    if state not in VALID_STATES:
        raise ValueError(f"Invalid state: {state!r}")

    conn.execute(
        """INSERT INTO ko_versions
           (id, ko_id, version, state, title, object_type, summary,
            content_json, superseded_by, created_at, created_by,
            source_file, raw_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            vid, ko_id, version, state, title, object_type, summary,
            json.dumps(content, ensure_ascii=False, sort_keys=True) if content else None,
            superseded_by,
            datetime.now(timezone.utc).isoformat(),
            created_by, source_file, raw_json,
        ),
    )
    return vid


def supersede_ko(
    conn: sqlite3.Connection,
    old_vid: str,
    new_vid: str,
) -> None:
    """Mark old version as superseded by new version."""
    conn.execute(
        "UPDATE ko_versions SET superseded_by = ? WHERE id = ?",
        (new_vid, old_vid),
    )


def get_ko_lineage(conn: sqlite3.Connection, ko_id: str) -> list[dict]:
    """Return the full version chain for a KO, ordered by creation time."""
    rows = conn.execute(
        """SELECT id, ko_id, version, state, title, object_type, summary,
                  superseded_by, created_at, created_by, source_file
           FROM ko_versions WHERE ko_id = ? ORDER BY created_at""",
        (ko_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_ko_latest(conn: sqlite3.Connection, ko_id: str) -> dict | None:
    """Return the latest (by creation time) version of a KO."""
    row = conn.execute(
        """SELECT id, ko_id, version, state, title, object_type, summary,
                  superseded_by, created_at, created_by, source_file
           FROM ko_versions WHERE ko_id = ? ORDER BY created_at DESC LIMIT 1""",
        (ko_id,),
    ).fetchone()
    return dict(row) if row else None


def transition_ko_state(
    conn: sqlite3.Connection,
    vid: str,
    new_state: str,
) -> None:
    """Transition a KO version to a new state (validates transition rules)."""
    row = conn.execute(
        "SELECT state FROM ko_versions WHERE id = ?", (vid,)
    ).fetchone()
    if row is None:
        raise KeyError(f"Unknown version id: {vid}")
    current = row["state"]
    _validate_transition(current, new_state)
    conn.execute(
        "UPDATE ko_versions SET state = ? WHERE id = ?",
        (new_state, vid),
    )


def deprecate_ko(
    conn: sqlite3.Connection,
    vid: str,
    reviewer: str = "",
    rationale: str = "",
) -> str:
    """Deprecate a KO version and record a review event. Returns event id."""
    transition_ko_state(conn, vid, "deprecated")

    # Record review event
    event_id = f"tkr:asset-ops:deprecate-{vid.split(':')[-1]}"
    reviewer_json = json.dumps({"id": reviewer, "reviewer_type": "agent"}, sort_keys=True)
    conn.execute(
        """INSERT INTO review_events
           (id, object_ref, object_version, decision, reviewer_json,
            reviewed_at, policy_version, rationale, raw_json)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            event_id, vid.split(":v")[0], vid.split(":v")[1],
            "deprecate", reviewer_json,
            datetime.now(timezone.utc).isoformat(),
            "asset-ops-v1", rationale,
            json.dumps({
                "id": event_id, "object_ref": vid.split(":v")[0],
                "decision": "deprecate", "reviewer": {"id": reviewer, "reviewer_type": "agent"},
                "rationale": rationale,
            }, sort_keys=True),
        ),
    )
    return event_id


# ---------------------------------------------------------------------------
# Dataset asset management
# ---------------------------------------------------------------------------
def compute_sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def register_dataset_asset(
    conn: sqlite3.Connection,
    asset_id: str,
    asset_type: str,
    version: str,
    record_count: int,
    status_dist: dict | None = None,
    sha256: str = "",
    gen_params: dict | None = None,
    upstream_commit: str = "",
    created_by: str = "",
    source_file: str = "",
    raw_json: str = "",
) -> str:
    """Register a dataset-level asset. Enforces immutability: if the same
    asset_id+version already exists with a different sha256, raise error."""
    existing = conn.execute(
        "SELECT sha256 FROM dataset_assets WHERE id = ?", (asset_id,)
    ).fetchone()
    if existing:
        if existing["sha256"] != sha256:
            raise ValueError(
                f"Immutability violation: {asset_id} already exists with "
                f"sha256={existing['sha256']}, new sha256={sha256}. "
                f"Bump version to register changed content."
            )
        return asset_id  # idempotent re-registration

    conn.execute(
        """INSERT INTO dataset_assets
           (id, asset_type, version, record_count, status_dist_json,
            sha256, gen_params_json, upstream_commit, created_at, created_by,
            source_file, raw_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            asset_id, asset_type, version, record_count,
            json.dumps(status_dist, sort_keys=True) if status_dist else None,
            sha256,
            json.dumps(gen_params, sort_keys=True) if gen_params else None,
            upstream_commit,
            datetime.now(timezone.utc).isoformat(),
            created_by, source_file, raw_json,
        ),
    )
    return asset_id


def list_dataset_assets(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """SELECT id, asset_type, version, record_count, status_dist_json,
                  sha256, gen_params_json, upstream_commit, created_at, created_by
           FROM dataset_assets ORDER BY id"""
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Quality ledger
# ---------------------------------------------------------------------------
def compute_quality_ledger(conn: sqlite3.Connection, stale_days: int = 30) -> list[dict]:
    """Compute quality metrics for all registered KOs.

    Metrics:
    - evidence_count: number of evidence records linked to this KO
    - citation_count: number of other KOs that reference this KO
    - falsified_count: number of review events with decision='reject' or 'revoke'
    - last_review_at / last_review_decision
    - is_stale: published and >stale_days since last review
    """
    # Get all unique KO ids from ko_versions
    ko_ids = [
        r["ko_id"]
        for r in conn.execute("SELECT DISTINCT ko_id FROM ko_versions ORDER BY ko_id").fetchall()
    ]

    ledger = []
    now = datetime.now(timezone.utc)

    for ko_id in ko_ids:
        # Evidence count: count evidence records whose id starts with the KO's domain
        # (evidence linked via claim_refs or by naming convention)
        evidence_count = conn.execute(
            """SELECT COUNT(*) FROM evidence
               WHERE id LIKE ?""",
            (f"%{ko_id.split(':')[-1]}%",),
        ).fetchone()[0]

        # Citation count: how many other KOs reference this one via relations
        citation_count = conn.execute(
            """SELECT COUNT(*) FROM ko_versions
               WHERE content_json LIKE ? AND ko_id != ?""",
            (f'%"{ko_id}"%', ko_id),
        ).fetchone()[0]

        # Falsified count: review events with reject/revoke for this KO
        falsified_count = conn.execute(
            """SELECT COUNT(*) FROM review_events
               WHERE object_ref = ? AND decision IN ('reject', 'revoke')""",
            (ko_id,),
        ).fetchone()[0]

        # Last review
        last_review = conn.execute(
            """SELECT reviewed_at, decision FROM review_events
               WHERE object_ref = ? ORDER BY reviewed_at DESC LIMIT 1""",
            (ko_id,),
        ).fetchone()

        last_review_at = last_review["reviewed_at"] if last_review else None
        last_review_decision = last_review["decision"] if last_review else None

        # Latest version state
        latest = get_ko_latest(conn, ko_id)
        state = latest["state"] if latest else "draft"
        version = latest["version"] if latest else "0.0.0"

        # Stale check: published and >stale_days since last review
        is_stale = 0
        if state == "published" and last_review_at:
            last_dt = datetime.fromisoformat(last_review_at)
            if (now - last_dt).days > stale_days:
                is_stale = 1
        elif state == "published" and not last_review_at:
            is_stale = 1  # published but never reviewed

        computed_at = now.isoformat()

        conn.execute(
            """INSERT OR REPLACE INTO quality_ledger
               (ko_id, evidence_count, citation_count, falsified_count,
                last_review_at, last_review_decision, state, version,
                is_stale, computed_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                ko_id, evidence_count, citation_count, falsified_count,
                last_review_at, last_review_decision, state, version,
                is_stale, computed_at,
            ),
        )

        ledger.append({
            "ko_id": ko_id,
            "evidence_count": evidence_count,
            "citation_count": citation_count,
            "falsified_count": falsified_count,
            "last_review_at": last_review_at,
            "last_review_decision": last_review_decision,
            "state": state,
            "version": version,
            "is_stale": bool(is_stale),
            "computed_at": computed_at,
        })

    return ledger


def get_quality_report(conn: sqlite3.Connection, stale_days: int = 30) -> dict:
    """Generate the full quality report (health table)."""
    ledger = compute_quality_ledger(conn, stale_days)
    total = len(ledger)
    published = sum(1 for r in ledger if r["state"] == "published")
    stale = sum(1 for r in ledger if r["is_stale"])
    deprecated = sum(1 for r in ledger if r["state"] == "deprecated")

    return {
        "summary": {
            "total_kos": total,
            "published": published,
            "stale": stale,
            "deprecated": deprecated,
            "draft_or_review": total - published - deprecated,
        },
        "ledger": ledger,
    }


# ---------------------------------------------------------------------------
# ASSET-INDEX compatible export
# ---------------------------------------------------------------------------
def export_asset_index(conn: sqlite3.Connection) -> list[dict]:
    """Export all registered assets (KOs + datasets) in ASSET-INDEX compatible format.

    Format aligned with platform asset-index spec:
    - Each entry has: asset_id, asset_type, version, state, sha256, created_at,
      metadata (title, object_type, domains, etc.), lineage (supersede chain)
    - Designed for ledger_line 30min ingestion
    """
    entries = []

    # KO versions as assets
    rows = conn.execute(
        """SELECT id, ko_id, version, state, title, object_type, summary,
                  superseded_by, created_at, created_by, content_json
           FROM ko_versions ORDER BY ko_id, created_at"""
    ).fetchall()

    for row in rows:
        content = json.loads(row["content_json"]) if row["content_json"] else {}
        domains = content.get("domains", []) if isinstance(content, dict) else []

        # Build lineage
        lineage = []
        if row["superseded_by"]:
            lineage.append(row["superseded_by"])

        entry = {
            "asset_id": row["id"],
            "asset_type": "knowledge_object",
            "object_type": row["object_type"] or "",
            "version": row["version"],
            "state": row["state"],
            "title": row["title"] or "",
            "summary": row["summary"] or "",
            "domains": domains,
            "created_at": row["created_at"],
            "created_by": row["created_by"] or "",
            "lineage": lineage,
            "superseded_by": row["superseded_by"],
            "sha256": compute_sha256(row["id"] + row["version"] + json.dumps(content, sort_keys=True)),
            "metadata": {
                "ko_id": row["ko_id"],
                "content_keys": list(content.keys()) if isinstance(content, dict) else [],
            },
        }
        entries.append(entry)

    # Dataset assets
    ds_rows = conn.execute(
        """SELECT id, asset_type, version, record_count, status_dist_json,
                  sha256, gen_params_json, upstream_commit, created_at, created_by
           FROM dataset_assets ORDER BY id"""
    ).fetchall()

    for row in ds_rows:
        entry = {
            "asset_id": row["id"],
            "asset_type": f"dataset_{row['asset_type']}",
            "version": row["version"],
            "state": "published",
            "record_count": row["record_count"],
            "status_dist": json.loads(row["status_dist_json"]) if row["status_dist_json"] else {},
            "sha256": row["sha256"],
            "gen_params": json.loads(row["gen_params_json"]) if row["gen_params_json"] else {},
            "upstream_commit": row["upstream_commit"],
            "created_at": row["created_at"],
            "created_by": row["created_by"] or "",
            "lineage": [],
            "metadata": {
                "source": "m8810_export",
            },
        }
        entries.append(entry)

    return entries


def export_asset_index_json(conn: sqlite3.Connection) -> str:
    """Export as JSON string, ready for ledger_line ingestion."""
    entries = export_asset_index(conn)
    return json.dumps({
        "format": "asset-index-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_entries": len(entries),
        "entries": entries,
    }, ensure_ascii=False, indent=2, sort_keys=True)
