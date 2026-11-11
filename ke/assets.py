"""Knowledge asset management — versioned KO registry, review gate, quality ledger.

This is the "asset life-cycle" layer on top of the KE record contract
(:mod:`ke.contract`).  The record contract answers *what is claimed*; this
module answers *which knowledge objects exist, in which version, approved by
whom, and how fresh are they*.

Four tables (all created by :func:`ensure_schema`, which
:func:`ke.store.connect` calls, so both backends always have them):

===============  =====================================================
table            rows
===============  =====================================================
ko_versions      one row per ``(ko_id, version)``; never deleted, only
                 superseded (``superseded_by``) or deprecated
review_events    append-only review decisions (approve / request-changes /
                 reject / revoke / deprecate) with reviewer + policy version
dataset_assets   versioned data artefacts (sft/eval/triples exports) with a
                 content ``sha256`` and the upstream commit that built them
quality_ledger   materialized per-KO quality metrics (evidence count,
                 citation count, falsification count, staleness)
===============  =====================================================

Design rules (each one is enforced in code, not by convention):

1. **Immutability + lineage.** A registered version id is never rewritten.
   Replacement happens through :func:`supersede_ko`, which records the
   successor in ``superseded_by`` and moves the old row to ``deprecated``.
   Physical deletes are not implemented.
2. **One state machine.** ``draft -> in_review -> published -> deprecated``
   (plus ``published -> in_review`` for re-review and ``in_review -> draft``
   for a change request).  Illegal transitions raise ``ValueError``.
3. **Review gate.** A version reaches ``published`` only through an
   ``approve`` review event; reviews carry a ``policy_version`` so the gate
   that took the decision stays auditable.
4. **Dataset immutability.** ``dataset_assets`` re-registration with the same
   id is idempotent *iff* the ``sha256`` matches; otherwise it is a
   ``ValueError`` (bump the version instead of silently replacing bytes).
5. **Backend neutrality.** Only the SQL subset that SQLite and PostgreSQL
   both accept verbatim is used, and everything goes through the
   :class:`ke.store.Store` facade (``?`` placeholders, ``ORDER BY`` pinned to
   :attr:`Store.collate`), so the two backends are byte-comparable.

KO ↔ claim linkage: a KO identifier equals the ``claims.domain`` value of the
claims it governs (that is the contract's own domain dimension), so
``evidence_count`` is computed with a join
(``claims.domain = ko_id -> claim_evidence``) instead of the substring
matching the closed prototype PR used — exact equality, no false positives.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# 1. Schema (portable DDL: TEXT/INTEGER only, no dialect-specific types)
# ---------------------------------------------------------------------------
ASSET_SCHEMA = """
CREATE TABLE IF NOT EXISTS ko_versions (
    id              TEXT PRIMARY KEY,
    ko_id           TEXT NOT NULL,
    version         TEXT NOT NULL,
    state           TEXT NOT NULL,
    title           TEXT,
    object_type     TEXT,
    summary         TEXT,
    content_json    TEXT,
    superseded_by   TEXT,
    created_at      TEXT NOT NULL,
    created_by      TEXT,
    source_file     TEXT,
    raw_json        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS review_events (
    id               TEXT PRIMARY KEY,
    object_ref       TEXT NOT NULL,
    seq              INTEGER NOT NULL,
    object_version   TEXT,
    decision         TEXT NOT NULL,
    reviewer_json    TEXT NOT NULL,
    reviewed_at      TEXT NOT NULL,
    policy_version   TEXT NOT NULL,
    rationale        TEXT,
    findings_json    TEXT,
    supersedes_event TEXT,
    conditions_json  TEXT,
    source_file      TEXT,
    raw_json         TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dataset_assets (
    id               TEXT PRIMARY KEY,
    asset_type       TEXT NOT NULL,
    version          TEXT NOT NULL,
    record_count     INTEGER NOT NULL,
    status_dist_json TEXT,
    sha256           TEXT NOT NULL,
    gen_params_json  TEXT,
    upstream_commit  TEXT,
    created_at       TEXT NOT NULL,
    created_by       TEXT,
    source_file      TEXT,
    raw_json         TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quality_ledger (
    ko_id                TEXT PRIMARY KEY,
    evidence_count       INTEGER NOT NULL,
    citation_count       INTEGER NOT NULL,
    falsified_count      INTEGER NOT NULL,
    last_review_at       TEXT,
    last_review_decision TEXT,
    state                TEXT,
    version              TEXT,
    is_stale             INTEGER NOT NULL,
    computed_at          TEXT NOT NULL
);
"""

ASSET_TABLES = ("ko_versions", "review_events", "dataset_assets", "quality_ledger")

#: decisions that can appear in ``review_events.decision``
DECISIONS = ("approve", "request-changes", "reject", "revoke", "deprecate")

#: decision -> state the reviewed version ends up in
REVIEW_EFFECTS = {
    "approve": "published",
    "request-changes": "in_review",
    "reject": "draft",
    "revoke": "deprecated",
    "deprecate": "deprecated",
}

VALID_STATES = ("draft", "in_review", "published", "deprecated")
STATE_TRANSITIONS = {
    "draft": {"in_review", "deprecated"},
    "in_review": {"published", "draft", "deprecated"},
    "published": {"deprecated", "in_review"},
    "deprecated": set(),  # terminal
}


def ensure_schema(conn) -> None:
    """Create the asset tables if missing (idempotent, both backends)."""
    conn.scripts(ASSET_SCHEMA)


def present_tables(conn) -> list[str]:
    """Asset tables that actually exist in ``conn`` (schema self-check)."""
    found = []
    for table in ASSET_TABLES:
        try:
            conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        except Exception:  # noqa: BLE001 - driver error type differs per backend
            continue
        found.append(table)
    return found


# ---------------------------------------------------------------------------
# 2. Small helpers (time, hashing, semver ordering)
# ---------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    """UTC ISO-8601 second precision with a ``Z`` suffix (sortable as text)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_iso(text: str) -> datetime:
    """Inverse of :func:`iso`; tolerates ``Z`` and explicit offsets."""
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _json(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _from_json(text: str | None, default: Any = None) -> Any:
    if not text:
        return default
    return json.loads(text)


def version_key(version: str) -> tuple:
    """Sort key for dotted versions (``1.10.0`` > ``1.9.2``; odd forms OK)."""
    key: list[tuple[int, int, str]] = []
    for part in version.split("."):
        if part.isdigit():
            key.append((0, int(part), ""))
        else:
            key.append((1, 0, part))
    return tuple(key)


def sha256_json(payload: Any) -> str:
    """Stable content digest of a JSON-serializable payload."""
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _ordered(conn, expr: str) -> str:
    """Byte-ordered expression (locale-independent on both backends)."""
    try:
        return conn.collate(expr)
    except AttributeError:  # pragma: no cover - foreign connection object
        return expr


# ---------------------------------------------------------------------------
# 3. State machine
# ---------------------------------------------------------------------------
def check_transition(current: str, target: str) -> None:
    """Raise ``ValueError`` unless ``current -> target`` is allowed."""
    if current not in VALID_STATES:
        raise ValueError(f"unknown state {current!r}; allowed: {list(VALID_STATES)}")
    if target not in VALID_STATES:
        raise ValueError(f"unknown state {target!r}; allowed: {list(VALID_STATES)}")
    if current == target:
        return
    if target not in STATE_TRANSITIONS[current]:
        raise ValueError(
            f"illegal state transition {current!r} -> {target!r}; "
            f"allowed from {current!r}: {sorted(STATE_TRANSITIONS[current])}"
        )


def _get_version_row(conn, vid: str):
    return conn.execute(
        "SELECT id, ko_id, version, state, superseded_by FROM ko_versions WHERE id = ?",
        (vid,),
    ).fetchone()


def _set_state(conn, vid: str, target: str) -> None:
    row = _get_version_row(conn, vid)
    if row is None:
        raise ValueError(f"no such KO version: {vid!r}")
    check_transition(row["state"], target)
    if row["state"] != target:
        conn.execute("UPDATE ko_versions SET state = ? WHERE id = ?", (target, vid))


# ---------------------------------------------------------------------------
# 4. KO versions
# ---------------------------------------------------------------------------
def register_ko_version(
    conn,
    ko_id: str,
    version: str,
    *,
    title: str = "",
    object_type: str = "",
    summary: str = "",
    content: dict | None = None,
    state: str = "draft",
    created_by: str = "",
    source_file: str = "",
    now: datetime | None = None,
) -> str:
    """Register one immutable KO version; returns its version id.

    Id is ``f"{ko_id}:v{version}"``.  The same ``(ko_id, version)`` may not be
    registered twice (``ValueError``) — knowledge objects are versioned, never
    overwritten.  ``state`` must be one of :data:`VALID_STATES`; a version may
    only be born ``draft``, ``in_review`` or ``published`` (``deprecated`` is
    reachable only by transition, so a brand-new row cannot start dead).
    """
    if not ko_id or not isinstance(ko_id, str):
        raise ValueError("ko_id must be a non-empty string")
    if not version or not isinstance(version, str):
        raise ValueError("version must be a non-empty string")
    if state not in VALID_STATES:
        raise ValueError(f"invalid state {state!r}; allowed: {list(VALID_STATES)}")
    if state == "deprecated":
        raise ValueError("a new KO version cannot be born deprecated")

    vid = f"{ko_id}:v{version}"
    if _get_version_row(conn, vid) is not None:
        raise ValueError(
            f"KO version already registered: {vid!r} (versions are immutable; "
            f"bump the version or use supersede_ko)"
        )
    created_at = iso(now or _now())
    record = {
        "id": vid,
        "ko_id": ko_id,
        "version": version,
        "state": state,
        "title": title,
        "object_type": object_type,
        "summary": summary,
        "content": content or {},
        "created_at": created_at,
        "created_by": created_by,
        "source_file": source_file,
    }
    conn.execute(
        """INSERT INTO ko_versions
           (id, ko_id, version, state, title, object_type, summary,
            content_json, superseded_by, created_at, created_by,
            source_file, raw_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (vid, ko_id, version, state, title, object_type, summary,
         _json(content or {}), None, created_at, created_by, source_file,
         json.dumps(record, ensure_ascii=False, sort_keys=True)),
    )
    return vid


def get_ko_version(conn, vid: str) -> dict | None:
    """One version row (payload JSON decoded) or ``None``."""
    row = conn.execute(
        """SELECT id, ko_id, version, state, title, object_type, summary,
                  content_json, superseded_by, created_at, created_by, source_file
           FROM ko_versions WHERE id = ?""",
        (vid,),
    ).fetchone()
    return _version_dict(row) if row else None


def _version_dict(row) -> dict:
    return {
        "id": row["id"],
        "ko_id": row["ko_id"],
        "version": row["version"],
        "state": row["state"],
        "title": row["title"] or "",
        "object_type": row["object_type"] or "",
        "summary": row["summary"] or "",
        "content": _from_json(row["content_json"], {}) or {},
        "superseded_by": row["superseded_by"],
        "created_at": row["created_at"],
        "created_by": row["created_by"] or "",
        "source_file": row["source_file"] or "",
    }


def list_ko_versions(conn, ko_id: str | None = None) -> list[dict]:
    """Every registered version, byte-ordered by ``(ko_id, created_at, id)``."""
    sql = """SELECT id, ko_id, version, state, title, object_type, summary,
                    content_json, superseded_by, created_at, created_by, source_file
             FROM ko_versions"""
    order = (f" ORDER BY {_ordered(conn, 'ko_id')}, "
             f"{_ordered(conn, 'created_at')}, {_ordered(conn, 'id')}")
    if ko_id is None:
        rows = conn.execute(sql + order).fetchall()
    else:
        rows = conn.execute(sql + " WHERE ko_id = ?" + order, (ko_id,)).fetchall()
    return [_version_dict(r) for r in rows]


def get_ko_lineage(conn, ko_id: str) -> list[dict]:
    """Version chain of one KO, oldest first (semver-then-time ordered)."""
    versions = list_ko_versions(conn, ko_id)
    versions.sort(key=lambda v: (version_key(v["version"]), v["created_at"], v["id"]))
    return versions


def get_ko_latest(conn, ko_id: str) -> dict | None:
    """Newest version of a KO by semver (time/ID as tie-break), or ``None``."""
    lineage = get_ko_lineage(conn, ko_id)
    return lineage[-1] if lineage else None


def supersede_ko(conn, old_vid: str, new_vid: str) -> None:
    """Link ``old_vid`` to its successor and deprecate it.

    Both versions must exist and belong to the same ``ko_id``; a version
    cannot supersede itself and an already-superseded version cannot be
    superseded twice (lineage would fork).
    """
    old = _get_version_row(conn, old_vid)
    new = _get_version_row(conn, new_vid)
    if old is None:
        raise ValueError(f"no such KO version: {old_vid!r}")
    if new is None:
        raise ValueError(f"no such KO version: {new_vid!r}")
    if old_vid == new_vid:
        raise ValueError("a KO version cannot supersede itself")
    if old["ko_id"] != new["ko_id"]:
        raise ValueError(
            f"lineage must stay within one KO: {old['ko_id']!r} != {new['ko_id']!r}"
        )
    if old["superseded_by"] is not None:
        raise ValueError(
            f"{old_vid!r} is already superseded by {old['superseded_by']!r}"
        )
    if version_key(new["version"]) <= version_key(old["version"]):
        raise ValueError(
            f"successor version {new['version']!r} must be greater than "
            f"{old['version']!r}"
        )
    conn.execute("UPDATE ko_versions SET superseded_by = ? WHERE id = ?",
                 (new_vid, old_vid))
    _set_state(conn, old_vid, "deprecated")


# ---------------------------------------------------------------------------
# 5. Review events (append-only gate)
# ---------------------------------------------------------------------------
def record_review(
    conn,
    object_ref: str,
    decision: str,
    *,
    object_version: str = "",
    reviewer: dict | None = None,
    policy_version: str = "review-policy-v1",
    rationale: str = "",
    findings: Iterable[Any] | None = None,
    conditions: Iterable[Any] | None = None,
    supersedes_event: str | None = None,
    source_file: str = "",
    now: datetime | None = None,
) -> str:
    """Append one review decision and apply its state effect; returns event id.

    ``object_ref`` may be a version id (``<ko_id>:v<version>``) or a bare
    ``ko_id`` (then the latest version is reviewed).  The event id is derived
    deterministically from ``(object_ref, reviewed_at, decision, seq)`` where
    ``seq`` counts existing events for that object, so replaying the same
    decision twice produces two distinguishable, ordered events.
    """
    if decision not in DECISIONS:
        raise ValueError(f"unknown decision {decision!r}; allowed: {list(DECISIONS)}")
    target_vid = object_ref
    if _get_version_row(conn, target_vid) is None:
        latest = get_ko_latest(conn, object_ref)
        if latest is None:
            raise ValueError(f"no KO version or KO registered as {object_ref!r}")
        target_vid = latest["id"]
    if supersedes_event is not None:
        found = conn.execute("SELECT id FROM review_events WHERE id = ?",
                             (supersedes_event,)).fetchone()
        if found is None:
            raise ValueError(f"supersedes_event not found: {supersedes_event!r}")

    reviewed_at = iso(now or _now())
    seq = conn.execute("SELECT COUNT(*) FROM review_events WHERE object_ref = ?",
                       (object_ref,)).fetchone()[0]
    event_id = "trev:" + hashlib.sha256(
        f"{object_ref}|{target_vid}|{reviewed_at}|{decision}|{seq}".encode("utf-8")
    ).hexdigest()[:24]
    reviewer = reviewer or {"kind": "human", "id": "unattributed"}
    record = {
        "id": event_id,
        "object_ref": object_ref,
        "seq": seq,
        "object_version": target_vid,
        "decision": decision,
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "policy_version": policy_version,
        "rationale": rationale,
        "findings": list(findings or []),
        "supersedes_event": supersedes_event,
        "conditions": list(conditions or []),
        "source_file": source_file,
    }
    conn.execute(
        """INSERT INTO review_events
           (id, object_ref, seq, object_version, decision, reviewer_json, reviewed_at,
            policy_version, rationale, findings_json, supersedes_event,
            conditions_json, source_file, raw_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (event_id, object_ref, seq, target_vid, decision, _json(reviewer), reviewed_at,
         policy_version, rationale, _json(list(findings or [])), supersedes_event,
         _json(list(conditions or [])), source_file,
         json.dumps(record, ensure_ascii=False, sort_keys=True)),
    )
    _set_state(conn, target_vid, REVIEW_EFFECTS[decision])
    return event_id


def get_review_events(conn, object_ref: str | None = None) -> list[dict]:
    """Review events in byte order (append-only audit trail)."""
    sql = """SELECT id, object_ref, seq, object_version, decision, reviewer_json,
                    reviewed_at, policy_version, rationale, findings_json,
                    supersedes_event, conditions_json, source_file
             FROM review_events"""
    # reviewed_at is second-precision, so events recorded inside the same
    # second must be ordered by their per-object ``seq`` (insertion order);
    # ``id`` only breaks ties between different objects.
    order = (f" ORDER BY {_ordered(conn, 'reviewed_at')}, seq, {_ordered(conn, 'id')}")
    if object_ref is None:
        rows = conn.execute(sql + order).fetchall()
    else:
        # ``object_ref`` may name a version id or a bare ko_id: a bare ko_id
        # must also pull the events recorded against its versions, otherwise
        # the ledger would silently see "published but never reviewed".
        refs = [object_ref] + [r["id"] for r in conn.execute(
            "SELECT id FROM ko_versions WHERE ko_id = ?", (object_ref,)).fetchall()]
        marks = ", ".join("?" for _ in refs)
        where = f" WHERE object_ref IN ({marks}) OR object_version IN ({marks})"
        rows = conn.execute(sql + where + order, refs + refs).fetchall()
    return [
        {
            "id": r["id"],
            "object_ref": r["object_ref"],
            "seq": int(r["seq"]),
            "object_version": r["object_version"] or "",
            "decision": r["decision"],
            "reviewer": _from_json(r["reviewer_json"], {}),
            "reviewed_at": r["reviewed_at"],
            "policy_version": r["policy_version"],
            "rationale": r["rationale"] or "",
            "findings": _from_json(r["findings_json"], []),
            "supersedes_event": r["supersedes_event"],
            "conditions": _from_json(r["conditions_json"], []),
            "source_file": r["source_file"] or "",
        }
        for r in rows
    ]


def deprecate_ko(conn, object_ref: str, *, reviewer: dict | None = None,
                 rationale: str = "deprecated", policy_version: str = "review-policy-v1",
                 now: datetime | None = None) -> str:
    """Deprecate a version through a ``deprecate`` review event (audited)."""
    return record_review(conn, object_ref, "deprecate", reviewer=reviewer,
                         rationale=rationale, policy_version=policy_version, now=now)


# ---------------------------------------------------------------------------
# 6. Dataset assets (versioned, sha256-pinned data artefacts)
# ---------------------------------------------------------------------------
def register_dataset_asset(
    conn,
    asset_id: str,
    asset_type: str,
    version: str,
    record_count: int,
    sha256: str,
    *,
    status_dist: dict | None = None,
    gen_params: dict | None = None,
    upstream_commit: str = "",
    created_by: str = "",
    source_file: str = "",
    now: datetime | None = None,
) -> str:
    """Register a dataset asset; idempotent per ``(id, sha256)``.

    Re-registering the same id with a *different* digest raises ``ValueError``:
    published bytes are immutable, so a content change must bump ``version``.
    """
    if not asset_id or not asset_type or not version:
        raise ValueError("asset_id, asset_type and version must be non-empty")
    if len(sha256) != 64 or any(c not in "0123456789abcdef" for c in sha256.lower()):
        raise ValueError(f"sha256 must be a 64-char hex digest, got {sha256!r}")
    if int(record_count) < 0:
        raise ValueError("record_count must be >= 0")

    existing = conn.execute(
        "SELECT sha256, version FROM dataset_assets WHERE id = ?", (asset_id,)
    ).fetchone()
    if existing is not None:
        if existing["sha256"] != sha256.lower():
            raise ValueError(
                f"immutability violation: {asset_id!r} v{existing['version']} has "
                f"sha256={existing['sha256']}, new content sha256={sha256.lower()}; "
                f"bump the version instead of replacing published bytes"
            )
        return asset_id

    created_at = iso(now or _now())
    record = {
        "id": asset_id,
        "asset_type": asset_type,
        "version": version,
        "record_count": int(record_count),
        "status_dist": status_dist or {},
        "sha256": sha256.lower(),
        "gen_params": gen_params or {},
        "upstream_commit": upstream_commit,
        "created_at": created_at,
        "created_by": created_by,
        "source_file": source_file,
    }
    conn.execute(
        """INSERT INTO dataset_assets
           (id, asset_type, version, record_count, status_dist_json, sha256,
            gen_params_json, upstream_commit, created_at, created_by,
            source_file, raw_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (asset_id, asset_type, version, int(record_count), _json(status_dist or {}),
         sha256.lower(), _json(gen_params or {}), upstream_commit, created_at,
         created_by, source_file,
         json.dumps(record, ensure_ascii=False, sort_keys=True)),
    )
    return asset_id


def list_dataset_assets(conn) -> list[dict]:
    """All dataset assets, byte-ordered by id."""
    rows = conn.execute(
        """SELECT id, asset_type, version, record_count, status_dist_json, sha256,
                  gen_params_json, upstream_commit, created_at, created_by, source_file
           FROM dataset_assets ORDER BY """ + _ordered(conn, "id")
    ).fetchall()
    return [
        {
            "id": r["id"],
            "asset_type": r["asset_type"],
            "version": r["version"],
            "record_count": int(r["record_count"]),
            "status_dist": _from_json(r["status_dist_json"], {}),
            "sha256": r["sha256"],
            "gen_params": _from_json(r["gen_params_json"], {}),
            "upstream_commit": r["upstream_commit"] or "",
            "created_at": r["created_at"],
            "created_by": r["created_by"] or "",
            "source_file": r["source_file"] or "",
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# 7. Quality ledger (computed, materialized per KO)
# ---------------------------------------------------------------------------
def ko_evidence_count(conn, ko_id: str, *, domains=None) -> int:
    """Distinct evidence records reachable from the claims this KO governs.

    Linkage is exact equality on the contract's domain dimension
    (``claims.domain IN (...)``), then ``claim_evidence`` — never a substring
    match, so a KO cannot inherit another KO's evidence.  ``domains`` defaults
    to ``[ko_id]``; a KO whose ``content["domains"]`` declares the claim
    domains it owns (as :mod:`scripts.register_assets` does) passes them here.
    """
    doms = [d for d in (domains or []) if d] or [ko_id]
    marks = ", ".join("?" for _ in doms)
    return conn.execute(
        f"""SELECT COUNT(DISTINCT ce.evidence_id)
            FROM claim_evidence ce JOIN claims c ON c.id = ce.claim_id
            WHERE c.domain IN ({marks})""",
        doms,
    ).fetchone()[0]


def ko_citation_count(conn, ko_id: str) -> int:
    """How many *other* KO versions reference this ``ko_id`` in their content."""
    return conn.execute(
        """SELECT COUNT(*) FROM ko_versions
           WHERE ko_id <> ? AND content_json LIKE ?""",
        (ko_id, f'%"{ko_id}"%'),
    ).fetchone()[0]


def compute_quality_ledger(conn, *, stale_days: int = 30,
                           now: datetime | None = None) -> list[dict]:
    """Recompute ``quality_ledger`` for every registered KO and return it.

    Metrics per KO: evidence count (contract join on the declared claim
    domains), citation count (other KO
    contents referencing it), falsification count (``reject``/``revoke``
    review events), last review, newest version/state, and ``is_stale`` =
    published *and* (never reviewed *or* last review older than
    ``stale_days``).  ``now`` is injectable so staleness is testable.
    """
    now = now or _now()
    if stale_days < 0:
        raise ValueError("stale_days must be >= 0")
    # sorted in Python: ``SELECT DISTINCT ... ORDER BY <expr> COLLATE`` is
    # rejected by PostgreSQL (ORDER BY expression must appear in the select
    # list), and Python's byte order is the backend-independent ordering the
    # rest of the KE relies on anyway.
    ko_ids = sorted({r["ko_id"] for r in conn.execute(
        "SELECT DISTINCT ko_id FROM ko_versions").fetchall()})

    ledger: list[dict] = []
    for ko_id in ko_ids:
        latest = get_ko_latest(conn, ko_id) or {}
        state = latest.get("state", "draft")
        version = latest.get("version", "0.0.0")
        content = latest.get("content") or {}
        declared_domains = content.get("domains") if isinstance(content, dict) else None

        events = get_review_events(conn, ko_id)
        last = events[-1] if events else None
        last_review_at = last["reviewed_at"] if last else None
        last_decision = last["decision"] if last else None
        falsified = sum(1 for e in events if e["decision"] in ("reject", "revoke"))

        is_stale = 0
        if state == "published":
            if last_review_at is None:
                is_stale = 1
            elif now - parse_iso(last_review_at) > timedelta(days=stale_days):
                is_stale = 1

        entry = {
            "ko_id": ko_id,
            "evidence_count": ko_evidence_count(conn, ko_id, domains=declared_domains),
            "citation_count": ko_citation_count(conn, ko_id),
            "falsified_count": falsified,
            "last_review_at": last_review_at,
            "last_review_decision": last_decision,
            "state": state,
            "version": version,
            "is_stale": bool(is_stale),
            "computed_at": iso(now),
        }
        _upsert_ledger(conn, entry)
        ledger.append(entry)
    return ledger


def _upsert_ledger(conn, entry: dict) -> None:
    # ON CONFLICT upsert is accepted verbatim by SQLite (>=3.24) and PostgreSQL
    conn.execute(
        """INSERT INTO quality_ledger
           (ko_id, evidence_count, citation_count, falsified_count, last_review_at,
            last_review_decision, state, version, is_stale, computed_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT (ko_id) DO UPDATE SET
               evidence_count = excluded.evidence_count,
               citation_count = excluded.citation_count,
               falsified_count = excluded.falsified_count,
               last_review_at = excluded.last_review_at,
               last_review_decision = excluded.last_review_decision,
               state = excluded.state,
               version = excluded.version,
               is_stale = excluded.is_stale,
               computed_at = excluded.computed_at""",
        (entry["ko_id"], entry["evidence_count"], entry["citation_count"],
         entry["falsified_count"], entry["last_review_at"],
         entry["last_review_decision"], entry["state"], entry["version"],
         1 if entry["is_stale"] else 0, entry["computed_at"]),
    )


def get_quality_report(conn, *, stale_days: int = 30,
                       now: datetime | None = None) -> dict:
    """Health table: summary counters + the full refreshed ledger."""
    ledger = compute_quality_ledger(conn, stale_days=stale_days, now=now)
    total = len(ledger)
    published = sum(1 for r in ledger if r["state"] == "published")
    deprecated = sum(1 for r in ledger if r["state"] == "deprecated")
    stale = sum(1 for r in ledger if r["is_stale"])
    return {
        "summary": {
            "total_kos": total,
            "published": published,
            "stale": stale,
            "deprecated": deprecated,
            "draft_or_review": total - published - deprecated,
            "evidence_total": sum(r["evidence_count"] for r in ledger),
            "falsified_total": sum(r["falsified_count"] for r in ledger),
            "stale_days": stale_days,
        },
        "ledger": ledger,
    }


# ---------------------------------------------------------------------------
# 8. ASSET-INDEX export (consumable by the platform ledger line)
# ---------------------------------------------------------------------------
def export_asset_index(conn) -> list[dict]:
    """Every asset (KO versions + dataset assets) as ``asset-index-v1`` entries.

    Each entry carries ``asset_id``/``asset_type``/``version``/``state``/
    ``sha256``/``created_at``/``lineage``/``metadata``.  The digest is a pure
    function of the stored row (id + version + content), so an unchanged
    registry exports byte-identical digests across machines and backends.
    """
    entries: list[dict] = []
    for row in list_ko_versions(conn):
        content = row["content"] or {}
        entries.append({
            "asset_id": row["id"],
            "asset_type": "knowledge_object",
            "object_type": row["object_type"],
            "version": row["version"],
            "state": row["state"],
            "title": row["title"],
            "summary": row["summary"],
            "domains": content.get("domains", []) if isinstance(content, dict) else [],
            "created_at": row["created_at"],
            "created_by": row["created_by"],
            "lineage": [row["superseded_by"]] if row["superseded_by"] else [],
            "superseded_by": row["superseded_by"],
            "sha256": sha256_json([row["id"], row["version"], content]),
            "metadata": {
                "ko_id": row["ko_id"],
                "content_keys": sorted(content) if isinstance(content, dict) else [],
                # pinned content digest (e.g. package record digest) so drift
                # detection can compare artefact vs live bytes (see
                # scripts/register_assets.py --verify)
                "content_sha256": content.get("sha256") if isinstance(content, dict) else None,
                # per-kind record counts when the KO describes a package
                "counts": content.get("counts") if isinstance(content, dict) else None,
            },
        })

    for row in list_dataset_assets(conn):
        entries.append({
            "asset_id": row["id"],
            "asset_type": f"dataset_{row['asset_type']}",
            "version": row["version"],
            "state": "published",
            "record_count": row["record_count"],
            "status_dist": row["status_dist"],
            "sha256": row["sha256"],
            "gen_params": row["gen_params"],
            "upstream_commit": row["upstream_commit"],
            "created_at": row["created_at"],
            "created_by": row["created_by"],
            "lineage": [],
            "metadata": {"source_file": row["source_file"]},
        })
    entries.sort(key=lambda e: (e["asset_type"], e["asset_id"]))
    return entries


def export_asset_index_obj(conn, *, generated_at: datetime | None = None) -> dict:
    """``asset-index-v1`` document (entries + manifest digests)."""
    entries = export_asset_index(conn)
    return {
        "format": "asset-index-v1",
        "generated_at": iso(generated_at or _now()),
        "total_entries": len(entries),
        "index_sha256": sha256_json(entries),
        "entries": entries,
    }


def export_asset_index_json(conn, *, generated_at: datetime | None = None) -> str:
    """``asset-index-v1`` document as UTF-8 JSON text."""
    return json.dumps(export_asset_index_obj(conn, generated_at=generated_at),
                      ensure_ascii=False, indent=2, sort_keys=True) + "\n"