"""只读 SQL 后端（psql 子进程；沙箱内 psycopg2 是桩，不依赖真驱动）。

三条只读护栏，缺一不可：
  1. **静态校验**：SQL 必须以 ``SELECT`` / ``WITH`` 开头，且不含 DML/DDL 关键字、不含多语句分隔符；
  2. **服务端 GUC**：连接以 ``PGOPTIONS='-c default_transaction_read_only=on'`` 启动，
     即便静态校验被绕过，写操作也会被 PG 拒绝；
  3. **无事务副作用**：每条查询独立会话，不留下未提交状态。

计量器不得因为「只想读」就免检——读库脚本是最容易被塞进写操作的地方。
"""
from __future__ import annotations

import os
import re
import subprocess

_ALLOWED_HEAD = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)
_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COPY|VACUUM|"
    r"REFRESH|REINDEX|CLUSTER|COMMENT|MERGE|CALL|DO)\b",
    re.IGNORECASE,
)


class ReadOnlyViolation(Exception):
    """SQL 不是只读查询。"""


class BackendUnavailable(Exception):
    """psql / 数据库不可达（离线节点、CI 无 PG 时走这条）。"""


def validate_readonly(sql: str) -> str:
    if not _ALLOWED_HEAD.match(sql):
        raise ReadOnlyViolation(f"只允许 SELECT/WITH 查询，收到：{sql[:80]!r}")
    if ";" in sql.strip().rstrip(";"):
        raise ReadOnlyViolation(f"只允许单条语句：{sql[:80]!r}")
    m = _FORBIDDEN.search(sql)
    if m:
        raise ReadOnlyViolation(f"查询里出现写/DDL 关键字 {m.group(0)!r}：{sql[:80]!r}")
    return sql


class PsqlBackend:
    """以 psql 子进程执行只读查询，返回文本单元格。"""

    def __init__(self, db: str, user: str | None = None, psql: str | None = None,
                 timeout: float = 60.0):
        self.db = db
        self.user = user or os.environ.get("KPI_PG_USER", "postgres")
        self.psql = psql or os.environ.get("KPI_PG_PSQL", "psql")
        self.timeout = timeout

    # -- 低层 ------------------------------------------------------------
    def run(self, sql: str) -> list[list[str]]:
        validate_readonly(sql)
        env = dict(os.environ)
        env["PGOPTIONS"] = "-c default_transaction_read_only=on"
        cmd = [self.psql, "-U", self.user, "-d", self.db, "-tA", "-F", "\x01",
               "-v", "ON_ERROR_STOP=1", "-c", sql]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, env=env,
                               timeout=self.timeout)
        except FileNotFoundError as exc:  # 离线节点没有 psql
            raise BackendUnavailable(f"{self.psql} 不存在：{exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise BackendUnavailable(f"查询超时 {self.timeout}s：{sql[:80]!r}") from exc
        if r.returncode != 0:
            err = (r.stderr or "").strip().splitlines()
            raise BackendUnavailable(
                f"psql -d {self.db} 失败（{r.returncode}）：{err[-1] if err else 'unknown'}")
        out = []
        for line in r.stdout.split("\n"):
            if line == "":
                continue
            out.append(line.split("\x01"))
        return out

    # -- 语义化取值 ------------------------------------------------------
    def scalar(self, sql: str) -> int:
        rows = self.run(sql)
        if not rows or not rows[0] or rows[0][0] == "":
            return 0
        return int(rows[0][0])

    def text(self, sql: str) -> str:
        rows = self.run(sql)
        return rows[0][0] if rows and rows[0] else ""

    def json(self, sql: str) -> dict:
        import json as _json
        raw = self.text(sql)
        return _json.loads(raw) if raw else {}

    def map(self, sql: str) -> dict[str, int]:
        return {r[0]: int(r[1]) for r in self.run(sql) if len(r) >= 2}

    def row(self, sql: str) -> dict[str, str]:
        rows = self.run(sql)
        return dict(rows[0]) if rows and rows[0] and rows[0][0] != "" else {}

    def rows(self, sql: str) -> list[list[str]]:
        return self.run(sql)

    def available(self) -> bool:
        try:
            self.scalar("SELECT 1")
            return True
        except (BackendUnavailable, ReadOnlyViolation):
            return False