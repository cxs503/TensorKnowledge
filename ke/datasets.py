"""TensorKnowledge — versioned dataset service (m8813).

Provides immutable, versioned datasets with SHA256 integrity, epistemic
status enforcement (published / reviewed / draft), and incremental diff
support for training continuation.

Design rules
------------
* Version一经发布 manifest 冻结；重导出内容变化必须升版本号。
* 同版本 sha256 不符 → 409 Conflict。
* download 默认 published-only；?include=reviewed 才并入 reviewed；
  draft 永不可下——服务端强制。
* 所有数据集行以 JSONL 格式存储，每行一个训练样本。
* 训练出口闸门（FEAT-SIM-DATAHOUSE）：持有 ``TrainGateStore`` 时，下载端点先问
  ``train_gate`` —— 审级 ``none`` 的版本对训练侧一律 403（含 ``include=all``）。
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterator

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS datasets (
    name        TEXT NOT NULL,
    version     TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('draft','reviewed','published')),
    description TEXT,
    created_at  TEXT NOT NULL,
    sha256      TEXT NOT NULL,
    row_count   INTEGER NOT NULL DEFAULT 0,
    manifest_json TEXT NOT NULL,
    PRIMARY KEY (name, version)
);

CREATE TABLE IF NOT EXISTS dataset_rows (
    name        TEXT NOT NULL,
    version     TEXT NOT NULL,
    row_index   INTEGER NOT NULL,
    row_json    TEXT NOT NULL,
    PRIMARY KEY (name, version, row_index),
    FOREIGN KEY (name, version) REFERENCES datasets(name, version)
);

CREATE TABLE IF NOT EXISTS dataset_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256_of_rows(rows: list[str]) -> str:
    """Compute SHA256 over the concatenation of JSONL rows (with trailing newline)."""
    h = hashlib.sha256()
    for r in rows:
        h.update((r + "\n").encode("utf-8"))
    return h.hexdigest()


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# DatasetStore
# ---------------------------------------------------------------------------

class DatasetStore:
    """SQLite-backed versioned dataset store."""

    def __init__(self, db_path: str | Path = ":memory:", gate: "Any | None" = None):
        # check_same_thread=False allows the connection to be used from
        # multiple threads (e.g. HTTP server handler threads).
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA busy_timeout = 5000")
        self.conn.executescript(SCHEMA)
        #: 训练出口闸门（ke.train_gate.TrainGateStore）；None = 未接入（不为旧调用方强加）
        self.gate = gate

    def attach_gate(self, gate: "Any") -> None:
        """接入训练出口闸门（ke.train_gate.TrainGateStore）。"""
        self.gate = gate

    # -- registration / publishing ------------------------------------------

    def register(
        self,
        name: str,
        version: str,
        rows: list[dict[str, Any]],
        status: str = "draft",
        description: str = "",
        extra_manifest: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Register a new dataset version.

        *rows* is a list of dicts; each dict becomes one JSONL line.
        *status* must be 'draft', 'reviewed', or 'published'.
        *extra_manifest* merges additional manifest keys (e.g. the ``held_out``
        declaration written by :func:`ke.dataset_builder.build_dataset`).
        Returns the manifest dict.
        """
        if status not in ("draft", "reviewed", "published"):
            raise ValueError(f"invalid status: {status!r}")

        # Check immutability: if (name, version) already exists, reject
        existing = self.conn.execute(
            "SELECT sha256 FROM datasets WHERE name=? AND version=?",
            (name, version),
        ).fetchone()
        if existing:
            raise ValueError(
                f"dataset {name}/{version} already exists (immutable); "
                f"use a new version number"
            )

        row_jsons = [json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows]
        sha = _sha256_of_rows(row_jsons)
        created = _now_iso()

        manifest = {
            "name": name,
            "version": version,
            "status": status,
            "description": description,
            "created_at": created,
            "sha256": sha,
            "row_count": len(rows),
        }
        if extra_manifest:
            reserved = set(manifest)
            clash = reserved & set(extra_manifest)
            if clash:
                raise ValueError(f"extra_manifest must not override core keys: {sorted(clash)}")
            manifest.update(extra_manifest)

        with self.conn:
            self.conn.execute(
                """INSERT INTO datasets (name, version, status, description,
                       created_at, sha256, row_count, manifest_json)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    name, version, status, description, created, sha,
                    len(rows), json.dumps(manifest, ensure_ascii=False, sort_keys=True),
                ),
            )
            for idx, rj in enumerate(row_jsons):
                self.conn.execute(
                    "INSERT INTO dataset_rows (name, version, row_index, row_json) VALUES (?,?,?,?)",
                    (name, version, idx, rj),
                )

        return manifest

    # -- listing ------------------------------------------------------------

    def list_datasets(self, name: str | None = None) -> list[dict[str, Any]]:
        """List all dataset versions, optionally filtered by name."""
        if name:
            cur = self.conn.execute(
                "SELECT name, version, status, description, created_at, sha256, row_count "
                "FROM datasets WHERE name=? ORDER BY version",
                (name,),
            )
        else:
            cur = self.conn.execute(
                "SELECT name, version, status, description, created_at, sha256, row_count "
                "FROM datasets ORDER BY name, version"
            )
        return [dict(r) for r in cur]

    # -- manifest -----------------------------------------------------------

    def get_manifest(self, name: str, version: str) -> dict[str, Any] | None:
        """Return the manifest for a specific dataset version, or None.

        Reconstructs manifest from current DB state (not cached JSON) so
        that status changes via promote() are reflected.
        """
        row = self.conn.execute(
            "SELECT name, version, status, description, created_at, sha256, row_count,"
            " manifest_json FROM datasets WHERE name=? AND version=?",
            (name, version),
        ).fetchone()
        if row is None:
            return None
        out = dict(row)
        stored = out.pop("manifest_json", None)
        if stored:
            # 冻结时写入的额外声明（如 held_out）必须保留；
            # 核心字段以库内实时状态为准（promote() 会改 status）。
            try:
                base = json.loads(stored)
            except (TypeError, ValueError):
                base = {}
            if isinstance(base, dict):
                merged = {**base, **out}
                merged.pop("manifest_json", None)
                return merged
        return out

    # -- download -----------------------------------------------------------

    def download_rows(
        self,
        name: str,
        version: str,
        include: str = "published",
    ) -> tuple[Iterator[str], str]:
        """Yield JSONL rows for a dataset version.

        *include* controls epistemic visibility:
          - 'published' (default): only published datasets
          - 'reviewed': published + reviewed
          - 'all': published + reviewed + draft  (NOT exposed via API)

        Returns (row_iterator, sha256).
        Raises PermissionError for draft datasets when include != 'all'.
        Raises KeyError if dataset not found.
        """
        ds = self.conn.execute(
            "SELECT status, sha256 FROM datasets WHERE name=? AND version=?",
            (name, version),
        ).fetchone()
        if ds is None:
            raise KeyError(f"dataset {name}/{version} not found")

        status = ds["status"]
        sha = ds["sha256"]

        # Training-exit gate (FEAT-SIM-DATAHOUSE): 未过审版本对训练侧不可见。
        gate = getattr(self, "gate", None)
        if gate is not None:
            gate.require_train_visible(name, version, include)

        # Epistemic leak prevention
        if include == "published" and status != "published":
            raise PermissionError(
                f"dataset {name}/{version} is '{status}'; "
                f"only 'published' datasets are downloadable by default"
            )
        if include == "reviewed" and status not in ("published", "reviewed"):
            raise PermissionError(
                f"dataset {name}/{version} is '{status}'; "
                f"use ?include=all to access draft (not recommended)"
            )

        cur = self.conn.execute(
            "SELECT row_json FROM dataset_rows WHERE name=? AND version=? ORDER BY row_index",
            (name, version),
        )

        def _iter():
            for r in cur:
                yield r["row_json"]

        return _iter(), sha

    def download_rows_jsonl(
        self,
        name: str,
        version: str,
        include: str = "published",
    ) -> tuple[list[str], str]:
        """Materialize all rows as a list of JSONL strings (for testing)."""
        it, sha = self.download_rows(name, version, include=include)
        return list(it), sha

    # -- diff ---------------------------------------------------------------

    def diff(
        self,
        name: str,
        version: str,
        since: str,
        include: str = "published",
    ) -> list[dict[str, Any]]:
        """Return rows that are new in *version* compared to *since*.

        Uses row_index as the ordering key; returns rows whose index is
        >= the row_count of the *since* version (append-only assumption).
        For more complex diffs, callers should compare SHA256 manifests.
        """
        since_ds = self.conn.execute(
            "SELECT row_count, status FROM datasets WHERE name=? AND version=?",
            (name, since),
        ).fetchone()
        if since_ds is None:
            raise KeyError(f"dataset {name}/{since} not found (since version)")

        # Training-exit gate (FEAT-SIM-DATAHOUSE): 增量端点同样是训练侧出口，
        # 否则未过审版本可以绕过 download 从 /diff 泄漏。
        gate = getattr(self, "gate", None)
        if gate is not None:
            gate.require_train_visible(name, version, include)
            gate.require_train_visible(name, since, include)

        # Check epistemic access for the since version too
        since_status = since_ds["status"]
        if include == "published" and since_status != "published":
            raise PermissionError(
                f"since-version {name}/{since} is '{since_status}'; "
                f"only 'published' datasets are accessible by default"
            )
        if include == "reviewed" and since_status not in ("published", "reviewed"):
            raise PermissionError(
                f"since-version {name}/{since} is '{since_status}'; "
                f"use ?include=all to access draft"
            )

        cur = self.conn.execute(
            "SELECT row_json FROM dataset_rows WHERE name=? AND version=? "
            "AND row_index >= ? ORDER BY row_index",
            (name, version, since_ds["row_count"]),
        )
        return [json.loads(r["row_json"]) for r in cur]

    # -- integrity check ----------------------------------------------------

    def verify_integrity(self, name: str, version: str) -> bool:
        """Verify that stored rows match the recorded SHA256."""
        ds = self.conn.execute(
            "SELECT sha256 FROM datasets WHERE name=? AND version=?",
            (name, version),
        ).fetchone()
        if ds is None:
            return False
        # 完整性校验是服务端内部动作，直读行、不过训练出口闸门
        # （闸门只约束训练侧消费，不能把自己的校验路径也挡住）。
        rows = [r["row_json"] for r in self.conn.execute(
            "SELECT row_json FROM dataset_rows WHERE name=? AND version=? ORDER BY row_index",
            (name, version),
        )]
        computed = _sha256_of_rows(rows)
        return computed == ds["sha256"]

    # -- promote ------------------------------------------------------------

    def promote(self, name: str, version: str, new_status: str) -> dict[str, Any]:
        """Change dataset status (draft → reviewed → published).

        Status can only move forward: draft → reviewed → published.
        """
        allowed = {"draft": "reviewed", "reviewed": "published"}
        ds = self.conn.execute(
            "SELECT status FROM datasets WHERE name=? AND version=?",
            (name, version),
        ).fetchone()
        if ds is None:
            raise KeyError(f"dataset {name}/{version} not found")
        current = ds["status"]
        if allowed.get(current) != new_status:
            raise ValueError(
                f"cannot promote {name}/{version} from '{current}' to '{new_status}'; "
                f"allowed: {current} → {allowed.get(current)}"
            )
        with self.conn:
            self.conn.execute(
                "UPDATE datasets SET status=? WHERE name=? AND version=?",
                (new_status, name, version),
            )
            # Also update manifest_json to reflect new status
            manifest = self.get_manifest(name, version)
            if manifest:
                self.conn.execute(
                    "UPDATE datasets SET manifest_json=? WHERE name=? AND version=?",
                    (json.dumps(manifest, ensure_ascii=False, sort_keys=True), name, version),
                )
        return self.get_manifest(name, version)  # type: ignore[return-value]

    def close(self):
        self.conn.close()
