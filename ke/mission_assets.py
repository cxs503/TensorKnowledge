"""Mission deliverables -> knowledge assets (wp-9447-01, task type ``01-asset-registration``).

The asset layer (:mod:`ke.assets`) answers *which knowledge objects exist*.  This
module answers the question that used to be answered by hand-edited manifests:
**which finished mission deliverables are allowed to become knowledge objects,
and on what evidence**.

A deliverable is registered only when it is *matured*, i.e. all of the
following hold — every check is executed in code, never by convention:

============  ==================================================================
check         rule
============  ==================================================================
maturity      ``evidence_grade`` must be ``REAL``; ``MOCK`` / ``STUB`` /
              ``WITHHELD`` / ``NOT_SUPPORTED`` are rejected with the reason
              (a stub cannot be laundered into the registry by labelling it a
              deliverable)
acceptance    a non-empty ``acceptance`` note is mandatory — "done" without a
              stated acceptance criterion is not a matured deliverable
bytes         the file must exist inside ``base_dir`` (path traversal is
              rejected) and its ``sha256`` is recomputed here from the bytes,
              never taken from the caller
artefact      build junk is refused: ``__pycache__`` segments and ``*.pyc`` are
              not deliverables (the closed PR#167 shipped exactly those)
batch         duplicate ``deliverable_id`` inside one batch is an error, and
              validation is all-or-nothing: a batch that fails raises before any
              row is written, so a partial registration can never masquerade as
              a complete mission
============  ==================================================================

Registered versions are born ``in_review`` (``draft`` on request): the producer
of a mission is *not* allowed to publish its own deliverable, exactly as
:func:`ke.assets.record_review` demands for every other knowledge object.

Idempotency / immutability follow the asset layer's rules: re-registering the
same ``mission`` + ``deliverable`` + ``version`` with identical bytes is a no-op
(``skipped_idempotent``), while different bytes raise ``ValueError`` — bump the
version instead of silently replacing a published digest.

Identifier scheme (deterministic, so re-runs address the same rows)::

    ko_id = f"mission.{mission_id}.{deliverable_id}"
    vid   = f"{ko_id}:v{version}"
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from . import assets as asset_mgr

SCHEMA = "mission-asset.v1"
REPORT_SCHEMA = "mission-assets-report.v1"

#: Grades the platform uses (REAL .. NOT_SUPPORTED, see the ecosystem evidence
#: ladder).  Only :data:`MATURE_GRADES` may enter the registry.
KNOWN_GRADES = ("REAL", "MOCK", "STUB", "WITHHELD", "NOT_SUPPORTED")
MATURE_GRADES = frozenset({"REAL"})

#: A version born by this module may not be ``published`` — publish is a review
#: decision, not a registration side effect.
ALLOWED_BIRTH_STATES = ("draft", "in_review")

KO_PREFIX = "mission."
MAX_BYTES = 5 * 1024 * 1024  # a knowledge object, not a data lake blob

_SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class DeliverableError(ValueError):
    """A batch of deliverables failed validation (nothing was written)."""

    def __init__(self, problems: list[str]):
        self.problems = list(problems)
        super().__init__(
            "deliverable validation failed:\n  - " + "\n  - ".join(self.problems)
        )


def _slug(value, field: str, problems: list[str]) -> str:
    text = (value or "").strip() if isinstance(value, str) else ""
    if not text:
        problems.append(f"{field}: must be a non-empty string")
        return ""
    if not _SLUG.match(text):
        problems.append(
            f"{field}: {text!r} must match {_SLUG.pattern} (lowercase, no spaces)"
        )
        return ""
    return text


def sha256_file(path: Path) -> str:
    """``sha256`` of the file's bytes (streamed, no caller trust)."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def joint_sha256(ko_id: str, sha256: str) -> str:
    """Digest binding an identifier to its content (batch/lineage witnesses)."""
    return hashlib.sha256(f"{ko_id}:{sha256}".encode("utf-8")).hexdigest()


def _resolve(path_value, base_dir: Path, label: str, problems: list[str]) -> tuple:
    """Resolve ``path_value`` under ``base_dir``; returns (abs_path, rel_posix)."""
    if not isinstance(path_value, str) or not path_value.strip():
        problems.append(f"{label}.path: must be a non-empty relative path")
        return None, ""
    raw = Path(path_value.strip())
    candidate = (raw if raw.is_absolute() else base_dir / raw)
    try:
        resolved = candidate.resolve()
        rel = resolved.relative_to(base_dir.resolve())
    except (ValueError, OSError):
        problems.append(
            f"{label}.path: {path_value!r} escapes base_dir {str(base_dir)!r}"
        )
        return None, ""
    rel_posix = rel.as_posix()
    if "__pycache__" in resolved.parts or resolved.suffix == ".pyc":
        problems.append(
            f"{label}.path: {rel_posix!r} is build artefact (bytecode), not a deliverable"
        )
        return None, ""
    if not resolved.is_file():
        problems.append(f"{label}.path: {rel_posix!r} is not a file")
        return None, ""
    size = resolved.stat().st_size
    if size == 0:
        problems.append(f"{label}.path: {rel_posix!r} is empty")
        return None, ""
    if size > MAX_BYTES:
        problems.append(
            f"{label}.path: {rel_posix!r} is {size} bytes > MAX_BYTES={MAX_BYTES}"
        )
        return None, ""
    return resolved, rel_posix


def normalise_deliverables(deliverables, base_dir) -> list[dict]:
    """Validate and normalise a deliverable batch (no writes).

    Raises :class:`DeliverableError` carrying *every* problem it found, so one
    review round reports the whole list instead of the first failure.
    """
    base = Path(base_dir)
    problems: list[str] = []
    if not deliverables:
        raise DeliverableError(["batch: at least one deliverable is required"])
    if not isinstance(deliverables, (list, tuple)):
        raise DeliverableError(["batch: deliverables must be a list of dicts"])

    seen: set[str] = set()
    out: list[dict] = []
    for index, raw in enumerate(deliverables):
        if not isinstance(raw, dict):
            problems.append(f"#{index}: deliverable must be a mapping")
            continue
        label = f"#{index}"
        deliverable_id = _slug(raw.get("deliverable_id"), f"{label}.deliverable_id", problems)
        if deliverable_id:
            label = deliverable_id
            if deliverable_id in seen:
                problems.append(f"{label}.deliverable_id: duplicated in batch")
            seen.add(deliverable_id)

        title = (raw.get("title") or "").strip() if isinstance(raw.get("title"), str) else ""
        if not title:
            problems.append(f"{label}.title: must be a non-empty string")
        acceptance = (raw.get("acceptance") or "").strip() \
            if isinstance(raw.get("acceptance"), str) else ""
        if not acceptance:
            problems.append(
                f"{label}.acceptance: a matured deliverable must state its "
                f"acceptance criterion"
            )
        grade = (raw.get("evidence_grade") or "").strip().upper() \
            if isinstance(raw.get("evidence_grade"), str) else ""
        if grade not in KNOWN_GRADES:
            problems.append(
                f"{label}.evidence_grade: {raw.get('evidence_grade')!r} not in "
                f"{list(KNOWN_GRADES)}"
            )
        elif grade not in MATURE_GRADES:
            problems.append(
                f"{label}.evidence_grade: {grade} is not a matured grade "
                f"(matured = {sorted(MATURE_GRADES)}); deliverable stays out of "
                f"the registry until its evidence is REAL"
            )

        resolved, rel_posix = _resolve(raw.get("path"), base, label, problems)
        if resolved is None:
            continue
        digest = sha256_file(resolved)
        out.append({
            "deliverable_id": deliverable_id,
            "title": title,
            "acceptance": acceptance,
            "evidence_grade": grade,
            "path": rel_posix,
            "sha256": digest,
            "size": resolved.stat().st_size,
        })
    if problems:
        raise DeliverableError(problems)
    return out


def ko_id_for(mission_id: str, deliverable_id: str) -> str:
    """Deterministic KO identifier for one mission deliverable."""
    return f"{KO_PREFIX}{mission_id}.{deliverable_id}"


def register_matured_deliverables(
    conn,
    mission_id: str,
    deliverables,
    *,
    base_dir,
    version: str = "1.0.0",
    created_by: str = "mission-registrar",
    state: str = "in_review",
    now: datetime | None = None,
) -> dict:
    """Register a matured mission's deliverables as immutable KO versions.

    All-or-nothing: validation happens for the whole batch before the first
    insert, so a rejected batch leaves the registry untouched.

    Returns a JSON-serialisable report (``mission-assets-report.v1``) with the
    registered / skipped ids and a ``batch_sha256`` witness over every
    ``(ko_id, content sha256)`` pair.
    """
    if not isinstance(mission_id, str) or not _SLUG.match(mission_id.strip() or ""):
        raise ValueError(
            f"mission_id: {mission_id!r} must match {_SLUG.pattern}"
        )
    mission_id = mission_id.strip()
    if state not in ALLOWED_BIRTH_STATES:
        raise ValueError(
            f"state: {state!r} not allowed; a mission deliverable is born "
            f"{list(ALLOWED_BIRTH_STATES)} — publishing requires a review "
            f"decision (ke.assets.record_review)"
        )
    if not isinstance(version, str) or not version.strip():
        raise ValueError("version: must be a non-empty string")
    version = version.strip()

    batch = normalise_deliverables(deliverables, base_dir)

    # Immutability check for the whole batch *before* writing anything.
    for item in batch:
        vid = f"{ko_id_for(mission_id, item['deliverable_id'])}:v{version}"
        existing = asset_mgr.get_ko_version(conn, vid)
        if existing is None:
            continue
        stored = (existing.get("content") or {}).get("sha256")
        if stored != item["sha256"]:
            raise ValueError(
                f"immutability violation: {vid!r} registered sha256={stored}, "
                f"current bytes sha256={item['sha256']}; bump --version instead of "
                f"replacing published bytes"
            )

    created_at = datetime.now(timezone.utc) if now is None else now
    registered: list[str] = []
    skipped: list[str] = []
    entries: list[dict] = []
    for item in batch:
        ko_id = ko_id_for(mission_id, item["deliverable_id"])
        vid = f"{ko_id}:v{version}"
        content = {
            "schema": SCHEMA,
            "mission_id": mission_id,
            "deliverable_id": item["deliverable_id"],
            "title": item["title"],
            "acceptance": item["acceptance"],
            "evidence_grade": item["evidence_grade"],
            "path": item["path"],
            "sha256": item["sha256"],
            "size": item["size"],
            "registrar": created_by,
        }
        if asset_mgr.get_ko_version(conn, vid) is not None:
            skipped.append(vid)
        else:
            registered.append(
                asset_mgr.register_ko_version(
                    conn, ko_id, version,
                    title=item["title"],
                    object_type="mission-deliverable",
                    summary=item["acceptance"],
                    content=content,
                    state=state,
                    created_by=created_by,
                    source_file=item["path"],
                    now=created_at,
                )
            )
        entries.append({
            "ko_id": ko_id,
            "version_id": vid,
            "path": item["path"],
            "sha256": item["sha256"],
            "evidence_grade": item["evidence_grade"],
            "status": "skipped_idempotent" if vid in skipped else "registered",
        })

    witness = asset_mgr.sha256_json(
        sorted([[e["ko_id"], e["sha256"]] for e in entries])
    )
    return {
        "schema": REPORT_SCHEMA,
        "mission_id": mission_id,
        "version": version,
        "state": state,
        "created_by": created_by,
        "generated_at": asset_mgr.iso(created_at),
        "registered": registered,
        "skipped_idempotent": skipped,
        "entries": entries,
        "counts": {
            "deliverables": len(batch),
            "registered": len(registered),
            "skipped_idempotent": len(skipped),
        },
        "batch_sha256": witness,
    }


def mission_deliverable_report(conn, mission_id: str) -> dict:
    """Every registered deliverable of a mission, newest version per deliverable.

    Filtering happens in Python over :func:`ke.assets.list_ko_versions` so the
    query is byte-identical on SQLite and PostgreSQL (no dialect-specific
    ``LIKE`` semantics).
    """
    prefix = ko_id_for(mission_id, "")
    latest: dict[str, dict] = {}
    for row in asset_mgr.list_ko_versions(conn):
        if not row["ko_id"].startswith(prefix):
            continue
        keep = latest.get(row["ko_id"])
        if keep is None or asset_mgr.version_key(row["version"]) > \
                asset_mgr.version_key(keep["version"]):
            latest[row["ko_id"]] = row
    entries = []
    for ko_id in sorted(latest):
        row = latest[ko_id]
        content = row.get("content") or {}
        entries.append({
            "ko_id": ko_id,
            "version_id": row["id"],
            "version": row["version"],
            "state": row["state"],
            "evidence_grade": content.get("evidence_grade"),
            "path": content.get("path"),
            "sha256": content.get("sha256"),
        })
    return {
        "schema": "mission-assets-index.v1",
        "mission_id": mission_id,
        "deliverables": entries,
        "count": len(entries),
        "states": {s: sum(1 for e in entries if e["state"] == s)
                   for s in sorted({e["state"] for e in entries})},
    }


def verify_mission_deliverables(conn, mission_id: str, *, base_dir) -> dict:
    """Re-hash the files on disk against what the registry recorded.

    Detects post-registration edits (``drift``) and deleted deliverables
    (``missing``) — the registry is only worth the bytes it pins.
    """
    base = Path(base_dir)
    index = mission_deliverable_report(conn, mission_id)
    entries = []
    for entry in index["deliverables"]:
        rel = entry["path"] or ""
        path = base / rel
        if not rel or not path.is_file():
            status, current = "missing", None
        else:
            current = sha256_file(path)
            status = "ok" if current == entry["sha256"] else "drift"
        entries.append({
            "ko_id": entry["ko_id"],
            "path": rel,
            "registered_sha256": entry["sha256"],
            "current_sha256": current,
            "status": status,
        })
    tally = {s: sum(1 for e in entries if e["status"] == s)
             for s in ("ok", "drift", "missing")}
    return {
        "schema": "mission-assets-verify.v1",
        "mission_id": mission_id,
        "entries": entries,
        "counts": tally,
        "ok": tally["drift"] == 0 and tally["missing"] == 0 and bool(entries),
    }