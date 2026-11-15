"""TensorKnowledge — 训练出口闸门（train_gate）。

锚点 FEAT-SIM-DATAHOUSE（子件4·训练出口闸门）。语义（TK 定位令既定）：

    published / reviewed 才进训练集；review_level = 'none' 的版本对训练侧不可见。

三态（单向流转，撤销需显式审计）：

    none --review--> reviewed --publish--> published
     ^                    |                    |
     +-------- revoke ----+--------------------+

一张 ``train_gate`` 行 = 一个 (dataset_id, version) 的训练出口决定，字段按交付要求：
dataset_id / version / 审级 review_level(none|reviewed|published) / 审定人 reviewer /
证据链 evidence_chain / 入训练集时间 admitted_at。

设计规则
--------
* **证据不可缺**：reviewed / published 行必须同时有 reviewer 与 evidence_chain，
  由 SQL ``CHECK`` 约束强制（不是应用层 if）。
* **自审禁止**：reviewer ≠ producer（四眼原则），两级流转还要求 publish 者 ≠ review 者。
* **直改库即失败**：审级变更只有一条合法路径 —— 在同一事务里先落
  ``train_gate_token`` 令牌再 UPDATE。``trg_tg_update_guard`` 触发器发现无令牌的
  任何 gate 行变更（审级 / 审定人 / 证据链）即 ``RAISE(ABORT)``，所以「拿 sqlite3 客户端直接
  UPDATE train_gate SET review_level='published'」会被数据库拦下。
* **审计只增不改**：``train_gate_audit`` 上的触发器禁止 UPDATE / DELETE；
  已定级的 gate 行也不允许 DELETE（撤审必须走 revoke 留痕）。
* **可对账**：``integrity_alerts()`` 把每行的当前审级与审计表最后一条 to_level
  比对，不一致即告警（防「审计表被清空后直改」这类半截伪造）。

存储复用 ``ke.datasets`` 的 SQLite 连接（同一 DB 文件），不额外引入服务依赖。
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable

LEVELS = ("none", "reviewed", "published")
#: 训练侧可见（可进入训练集）的审级
TRAINING_VISIBLE_LEVELS = ("reviewed", "published")
#: 合法流转（不含撤销；撤销走 revoke()）
TRANSITIONS = {("none", "reviewed"), ("reviewed", "published")}
#: 撤销：定级回落到 none
REVOCABLE_FROM = ("reviewed", "published")
#: 下载端点允许的 include 值（'all' 永不开放给训练侧）
DOWNLOAD_INCLUDES = ("published", "reviewed")

SCHEMA = """
CREATE TABLE IF NOT EXISTS train_gate (
    dataset_id     TEXT NOT NULL,
    version        TEXT NOT NULL,
    review_level   TEXT NOT NULL DEFAULT 'none',
    reviewer       TEXT,
    evidence_chain TEXT,
    producer       TEXT,
    admitted_at    TEXT,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    PRIMARY KEY (dataset_id, version),
    CHECK (review_level IN ('none','reviewed','published')),
    CHECK (length(trim(dataset_id)) > 0 AND length(trim(version)) > 0),
    -- 审级与证据必须一致：定级行缺审定人/证据链 -> 写入失败
    CHECK (
        (review_level = 'none'
             AND reviewer IS NULL AND evidence_chain IS NULL AND admitted_at IS NULL)
        OR
        (review_level <> 'none'
             AND reviewer IS NOT NULL AND length(trim(reviewer)) > 0
             AND evidence_chain IS NOT NULL AND length(trim(evidence_chain)) > 0
             AND admitted_at IS NOT NULL)
    ),
    -- 四眼原则：审定人不得是产出方
    CHECK (producer IS NULL OR reviewer IS NULL OR reviewer <> producer)
);

CREATE TABLE IF NOT EXISTS train_gate_audit (
    audit_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id     TEXT NOT NULL,
    version        TEXT NOT NULL,
    from_level     TEXT,
    to_level       TEXT NOT NULL,
    reviewer       TEXT,
    evidence_chain TEXT,
    actor          TEXT NOT NULL,
    action         TEXT NOT NULL,
    note           TEXT,
    at             TEXT NOT NULL
);

-- 流转令牌：只有 transition()/revoke() 在同一事务里先插令牌，UPDATE 才被放行
CREATE TABLE IF NOT EXISTS train_gate_token (
    dataset_id TEXT NOT NULL,
    version    TEXT NOT NULL,
    to_level   TEXT NOT NULL,
    issued_at  TEXT NOT NULL,
    PRIMARY KEY (dataset_id, version)
);

CREATE TRIGGER IF NOT EXISTS trg_tg_update_guard
BEFORE UPDATE ON train_gate
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM train_gate_token t
        WHERE t.dataset_id = OLD.dataset_id
          AND t.version = OLD.version
          AND t.to_level = NEW.review_level
    ) THEN RAISE(ABORT, 'train_gate: unguarded UPDATE (forged grade/reviewer)') END;
    DELETE FROM train_gate_token
     WHERE dataset_id = OLD.dataset_id AND version = OLD.version;
END;

CREATE TRIGGER IF NOT EXISTS trg_tg_insert_guard
BEFORE INSERT ON train_gate
WHEN NEW.review_level <> 'none' AND NOT EXISTS (
    SELECT 1 FROM train_gate_audit a
     WHERE a.dataset_id = NEW.dataset_id
       AND a.version = NEW.version
       AND a.to_level = NEW.review_level
)
BEGIN
    SELECT RAISE(ABORT, 'train_gate: graded insert without audit row');
END;

CREATE TRIGGER IF NOT EXISTS trg_tg_no_delete_graded
BEFORE DELETE ON train_gate
WHEN OLD.review_level <> 'none'
BEGIN
    SELECT RAISE(ABORT, 'train_gate: graded row cannot be deleted (use revoke)');
END;

CREATE TRIGGER IF NOT EXISTS trg_tg_audit_no_update
BEFORE UPDATE ON train_gate_audit
BEGIN
    SELECT RAISE(ABORT, 'train_gate_audit is append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_tg_audit_no_delete
BEFORE DELETE ON train_gate_audit
BEGIN
    SELECT RAISE(ABORT, 'train_gate_audit is append-only');
END;
"""


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _norm_evidence(evidence_chain: str | Iterable[str] | None) -> str:
    """证据链归一化为非空字符串（列表 -> JSON 数组文本）。"""
    if evidence_chain is None:
        raise ValueError("evidence_chain is required for a graded dataset version")
    if isinstance(evidence_chain, str):
        refs = [evidence_chain.strip()] if evidence_chain.strip() else []
        text = evidence_chain.strip()
    else:
        refs = [str(r).strip() for r in evidence_chain if str(r).strip()]
        text = json.dumps(refs, ensure_ascii=False, sort_keys=True)
    if not refs:
        raise ValueError("evidence_chain must reference at least one evidence record")
    return text


class TrainGateStore:
    """训练出口闸门表 train_gate + 只增审计表 train_gate_audit。"""

    def __init__(
        self,
        db_path: str | Path = ":memory:",
        conn: sqlite3.Connection | None = None,
        strict: bool = False,
    ):
        if conn is not None:
            self.conn = conn
            self._owns_conn = False
        else:
            self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
            self._owns_conn = True
        #: strict=True 时「无 gate 行」= 拒绝（fail-closed）；默认 False 保持旧数据集
        #: （未接入闸门）行为不变，由 datasets.status 自行把关。
        self.strict = strict
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA busy_timeout = 5000")
        self.conn.executescript(SCHEMA)

    # -- internal -----------------------------------------------------------

    def _audit(
        self,
        dataset_id: str,
        version: str,
        from_level: str | None,
        to_level: str,
        reviewer: str | None,
        evidence_chain: str | None,
        actor: str,
        action: str,
        note: str | None,
    ) -> None:
        self.conn.execute(
            "INSERT INTO train_gate_audit (dataset_id, version, from_level, to_level,"
            " reviewer, evidence_chain, actor, action, note, at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (dataset_id, version, from_level, to_level, reviewer, evidence_chain,
             actor, action, note, _now_iso()),
        )

    @staticmethod
    def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row is not None else None

    # -- registration -------------------------------------------------------

    def register(
        self,
        dataset_id: str,
        version: str,
        producer: str | None = None,
        actor: str | None = None,
        note: str = "initial registration",
    ) -> dict[str, Any]:
        """登记一个数据集版本，初始审级 = none（训练侧不可见）。"""
        now = _now_iso()
        actor = actor or producer or "system"
        with self.conn:
            self._audit(dataset_id, version, None, "none", None, None, actor,
                        "register", note)
            self.conn.execute(
                "INSERT INTO train_gate (dataset_id, version, review_level, reviewer,"
                " evidence_chain, producer, admitted_at, created_at, updated_at)"
                " VALUES (?,?,'none',NULL,NULL,?,NULL,?,?)",
                (dataset_id, version, producer, now, now),
            )
        return self.get(dataset_id, version)  # type: ignore[return-value]

    # -- transitions --------------------------------------------------------

    def transition(
        self,
        dataset_id: str,
        version: str,
        to_level: str,
        reviewer: str,
        evidence_chain: str | Iterable[str],
        actor: str,
        note: str = "",
    ) -> dict[str, Any]:
        """推进审级：none → reviewed → published。

        拒绝：跨级跳（none → published）、自审、审级相同、证据链为空、
        同一人既 review 又 publish（四眼）。
        """
        if to_level not in LEVELS:
            raise ValueError(f"invalid level: {to_level!r} (allowed: {LEVELS})")
        cur = self.conn.execute(
            "SELECT * FROM train_gate WHERE dataset_id=? AND version=?",
            (dataset_id, version),
        ).fetchone()
        if cur is None:
            raise KeyError(f"dataset {dataset_id}/{version} is not registered in train_gate")

        from_level = cur["review_level"]
        if (from_level, to_level) not in TRANSITIONS:
            raise ValueError(
                f"illegal transition {from_level} -> {to_level} for {dataset_id}/{version}; "
                f"allowed: {sorted(TRANSITIONS)}"
            )

        reviewer = (reviewer or "").strip()
        if not reviewer:
            raise ValueError("reviewer is required")
        producer = cur["producer"]
        if producer and reviewer == producer:
            raise ValueError(
                f"self-review refused: reviewer {reviewer!r} is the producer of {dataset_id}/{version}"
            )
        if to_level == "published" and reviewer == cur["reviewer"]:
            raise ValueError(
                f"four-eyes refused: {reviewer!r} already reviewed {dataset_id}/{version}; "
                f"publishing needs a different reviewer"
            )
        ev = _norm_evidence(evidence_chain)
        actor = (actor or reviewer).strip()
        now = _now_iso()

        with self.conn:
            # 1) 令牌：声明本次要去的审级（触发器只认这一步）
            self.conn.execute(
                "INSERT OR REPLACE INTO train_gate_token (dataset_id, version, to_level, issued_at)"
                " VALUES (?,?,?,?)",
                (dataset_id, version, to_level, now),
            )
            # 2) 审级/审定人变更（trg_tg_update_guard 在此消费令牌）
            self.conn.execute(
                "UPDATE train_gate SET review_level=?, reviewer=?, evidence_chain=?,"
                " admitted_at=COALESCE(admitted_at, ?), updated_at=?"
                " WHERE dataset_id=? AND version=?",
                (to_level, reviewer, ev, now, now, dataset_id, version),
            )
            # 3) 审计行
            self._audit(dataset_id, version, from_level, to_level, reviewer, ev,
                        actor, "transition", note or None)
        return self.get(dataset_id, version)  # type: ignore[return-value]

    def revoke(
        self,
        dataset_id: str,
        version: str,
        actor: str,
        note: str,
    ) -> dict[str, Any]:
        """撤审：定级回落到 none（训练侧立即不可见），留审计行。"""
        cur = self.conn.execute(
            "SELECT * FROM train_gate WHERE dataset_id=? AND version=?",
            (dataset_id, version),
        ).fetchone()
        if cur is None:
            raise KeyError(f"dataset {dataset_id}/{version} is not registered in train_gate")
        from_level = cur["review_level"]
        if from_level not in REVOCABLE_FROM:
            raise ValueError(f"cannot revoke {dataset_id}/{version}: level is already 'none'")
        if not (note or "").strip():
            raise ValueError("revoke requires a note")
        now = _now_iso()
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO train_gate_token (dataset_id, version, to_level, issued_at)"
                " VALUES (?,?,'none',?)",
                (dataset_id, version, now),
            )
            self.conn.execute(
                "UPDATE train_gate SET review_level='none', reviewer=NULL, evidence_chain=NULL,"
                " admitted_at=NULL, updated_at=? WHERE dataset_id=? AND version=?",
                (now, dataset_id, version),
            )
            self._audit(dataset_id, version, from_level, "none", None, None,
                        (actor or "system").strip(), "revoke", note)
        return self.get(dataset_id, version)  # type: ignore[return-value]

    # -- read side ----------------------------------------------------------

    def get(self, dataset_id: str, version: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM train_gate WHERE dataset_id=? AND version=?",
            (dataset_id, version),
        ).fetchone()
        return self._row_to_dict(row)

    def list_rows(
        self,
        dataset_id: str | None = None,
        level: str | None = None,
        visible_only: bool = False,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM train_gate WHERE 1=1"
        args: list[Any] = []
        if dataset_id:
            sql += " AND dataset_id=?"
            args.append(dataset_id)
        if level:
            if level not in LEVELS:
                raise ValueError(f"invalid level filter: {level!r}")
            sql += " AND review_level=?"
            args.append(level)
        if visible_only:
            sql += " AND review_level IN ('reviewed','published')"
        sql += " ORDER BY dataset_id, version"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def audit(self, dataset_id: str | None = None, version: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM train_gate_audit WHERE 1=1"
        args: list[Any] = []
        if dataset_id:
            sql += " AND dataset_id=?"
            args.append(dataset_id)
        if version:
            sql += " AND version=?"
            args.append(version)
        sql += " ORDER BY audit_id"
        return [dict(r) for r in self.conn.execute(sql, args)]

    def grade_counts(self) -> dict[str, int]:
        counts = {lvl: 0 for lvl in LEVELS}
        for r in self.conn.execute(
            "SELECT review_level, COUNT(*) AS n FROM train_gate GROUP BY review_level"
        ):
            counts[r["review_level"]] = int(r["n"])
        return counts

    def integrity_alerts(self) -> list[dict[str, Any]]:
        """对账：每行当前审级必须等于其审计表最后一条 to_level。"""
        alerts: list[dict[str, Any]] = []
        for row in self.conn.execute("SELECT * FROM train_gate"):
            last = self.conn.execute(
                "SELECT to_level, at FROM train_gate_audit WHERE dataset_id=? AND version=?"
                " ORDER BY audit_id DESC LIMIT 1",
                (row["dataset_id"], row["version"]),
            ).fetchone()
            if last is None:
                alerts.append({
                    "dataset_id": row["dataset_id"], "version": row["version"],
                    "kind": "missing_audit", "review_level": row["review_level"],
                })
            elif last["to_level"] != row["review_level"]:
                alerts.append({
                    "dataset_id": row["dataset_id"], "version": row["version"],
                    "kind": "level_audit_mismatch",
                    "review_level": row["review_level"], "audit_to_level": last["to_level"],
                })
        return alerts

    # -- training-side enforcement -----------------------------------------

    def require_train_visible(self, dataset_id: str, version: str, include: str = "published") -> str:
        """训练侧下载闸门。返回生效审级；不可见抛 PermissionError（HTTP 403）。

        * 无 gate 行 → strict=False 时视为未接入闸门（返回 'ungated'，由数据集自身审级把关）；
  strict=True 时直接拒绝（fail-closed，生产建议开）。
        * review_level='none' → 任何 include 都 403（未过审版本对训练侧不可见）。
        * include='all' → 403（训练侧永不开放）。
        * reviewed → 只允许 include in ('reviewed',)；published → ('published','reviewed')。
        """
        row = self.get(dataset_id, version)
        if row is None:
            if self.strict:
                raise PermissionError(
                    f"dataset {dataset_id}/{version} has no train_gate row; "
                    f"strict mode denies unreviewed-by-default consumers"
                )
            return "ungated"
        level = row["review_level"]
        if level == "none":
            raise PermissionError(
                f"dataset {dataset_id}/{version} has train_gate level 'none'; "
                f"not visible to training (reviewed/published required)"
            )
        if include not in DOWNLOAD_INCLUDES:
            raise PermissionError(
                f"include={include!r} is not exposed to the training side; allowed: {DOWNLOAD_INCLUDES}"
            )
        if level == "published":
            return level
        # level == 'reviewed'
        if include != "reviewed":
            raise PermissionError(
                f"dataset {dataset_id}/{version} is gate level 'reviewed'; "
                f"download requires include=reviewed"
            )
        return level

    def visible_for_training(self, dataset_id: str, version: str) -> bool:
        row = self.get(dataset_id, version)
        return bool(row and row["review_level"] in TRAINING_VISIBLE_LEVELS)

    def close(self) -> None:
        if self._owns_conn:
            self.conn.close()