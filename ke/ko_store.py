"""KO v1 存储面 — 把编译/入库产物落进 ``schemas/sql/knowledge_object_v1.sql`` 的库。

设计边界（不另立存储）：

* 表结构**只**来自 ``schemas/sql/knowledge_object_v1.sql``（KBM-RCI-S2-SCHEMA 的
  唯一权威 DDL）：ko_object / ko_evidence / ko_relation / ko_verification /
  ko_state_event。本模块只负责「按 DDL 建 schema + 幂等写入 + 检索」。
* 写入是 **append-only + 幂等**：``ON CONFLICT DO NOTHING``；已存在的对象不改写，
  版本化靠知识对象自身 ``version``/``supersedes`` 边，不靠 UPDATE。
* 隔离：默认写进独立 PG schema（``ko_compiler_v1``），不碰现网 ``ke_service``
  生产表；schema 名可由 ``--schema`` 覆盖。检索用同一连接，因此「入库即可检索」。
* L3 通道：本模块**拒绝**写入 ``verification_status='platform_verified'``
  （DDL 触发器之外再加一道应用层闸，报错而不是静默降级）。

DSN 解析顺序：显式参数 > ``KO_DSN`` > ``KE_PG_DSN`` > ``dbname=ke_service``。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
DDL_PATH = REPO_ROOT / "schemas" / "sql" / "knowledge_object_v1.sql"

DEFAULT_SCHEMA = "ko_compiler_v1"
DEFAULT_DSN = "dbname=ke_service"

#: 允许本模块写入的验证状态上限（L3 只走平台验证单）
WRITABLE_STATUSES = ("unverified", "report_claimed")


class KOWriteError(RuntimeError):
    """违反治理约束的写入尝试（越级 L3 / 非 v1 文档 / 缺证据）。"""


def dsn_from_env(explicit: str | None = None) -> str:
    return explicit or os.environ.get("KO_DSN") or os.environ.get("KE_PG_DSN") or DEFAULT_DSN


def connect(dsn: str | None = None, *, schema: str = DEFAULT_SCHEMA, create: bool = True):
    """打开 PG 连接并把 search_path 指到 ``schema``；``create`` 时按权威 DDL 建表。"""
    import psycopg

    conn = psycopg.connect(dsn_from_env(dsn), autocommit=True)
    cur = conn.cursor()
    cur.execute("CREATE SCHEMA IF NOT EXISTS %s" % _ident(schema))
    cur.execute("SET search_path TO %s, public" % _ident(schema))
    if create:
        cur.execute(DDL_PATH.read_text(encoding="utf-8"))
        cur.execute("SET search_path TO %s, public" % _ident(schema))
    return conn


def _ident(name: str) -> str:
    if not name or not all(c.isalnum() or c == "_" for c in name):
        raise ValueError("unsafe schema name: %r" % name)
    return '"%s"' % name


# ------------------------------------------------------------------ 写入
def ingest_document(conn, doc: Mapping[str, Any]) -> str:
    """写入一条 KO v1 文档（+ 证据行 + 关系边）。返回 inserted / exists。"""
    if doc.get("schema_version") != "ko/v1":
        raise KOWriteError("not a ko/v1 document: %r" % doc.get("schema_version"))
    status = doc.get("verification_status")
    if status not in WRITABLE_STATUSES:
        raise KOWriteError(
            "compiler/ingest may not write verification_status=%r (L3 only via platform ticket)" % status
        )
    prov = doc.get("provenance") or {}
    if not prov.get("producer") or not prov.get("created_at"):
        raise KOWriteError("provenance.producer/created_at required")
    if not doc.get("evidence"):
        raise KOWriteError("knowledge object without evidence cannot be stored above unverified")

    cur = conn.cursor()
    try:
        cur.execute(
        """
        INSERT INTO ko_object (knowledge_id, schema_version, version, type, domain, subject,
                               claim, conditions, confidence, verification_status, storage_level,
                               limitations, relations, next_actions, provenance, payload, doc,
                               content_sha256, producer)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (knowledge_id) DO NOTHING
        """,
        (
            doc["knowledge_id"], doc["schema_version"], int(doc["version"]), doc["type"],
            doc["domain"], doc["subject"], doc["claim"],
            json.dumps(doc["conditions"], ensure_ascii=False),
            json.dumps(doc["confidence"], ensure_ascii=False),
            status, prov.get("storage_level", "L1"),
            json.dumps(doc.get("limitations", []), ensure_ascii=False),
            json.dumps(doc.get("relations", []), ensure_ascii=False),
            json.dumps(doc.get("next_actions", []), ensure_ascii=False),
            json.dumps(prov, ensure_ascii=False),
            _jdump(doc.get("payload")),
            _jdump(doc),
            prov.get("content_sha256") or _content_sha(doc),
            prov["producer"],
        ),
        )
    except Exception as exc:  # ko_object_claim_uniq：同域同主体同断言=同一对象（防手抄）
        if "ko_object_claim_uniq" in str(exc):
            return "duplicate_claim"
        raise
    inserted = cur.rowcount == 1

    for ordinal, ev in enumerate(doc["evidence"]):
        sec = ev["section"]
        span = sec.get("span") or [None, None]
        cur.execute(
            """
            INSERT INTO ko_evidence (evidence_id, knowledge_id, ordinal, report_id, report_kind,
                                     section_heading, section_anchor, section_start, section_end,
                                     section_sha256, excerpt, evidence_type, relation, artifact_kind,
                                     artifact_ref, artifact_sha256, report_resolved,
                                     section_resolved, artifact_resolved, resolver_version, resolved_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (knowledge_id, ordinal) DO NOTHING
            """,
            (
                ev["evidence_id"], doc["knowledge_id"], ordinal, int(ev["report_id"]),
                ev.get("report_kind", "tensor_report"), sec["heading"], sec["anchor"],
                span[0], span[1], sec.get("section_sha256"), sec.get("excerpt"),
                ev.get("evidence_type", "documentation"), ev.get("relation", "supports"),
                ev["artifact_ref"]["kind"], ev["artifact_ref"]["ref"],
                ev["artifact_ref"].get("sha256"),
                bool(ev.get("resolution", {}).get("report_resolved")),
                bool(ev.get("resolution", {}).get("section_resolved")),
                ev.get("resolution", {}).get("artifact_resolved"),
                ev.get("resolution", {}).get("resolver_version"),
            ),
        )

    for rel in doc.get("relations") or []:
        cur.execute(
            """
            INSERT INTO ko_relation (src_id, dst_id, relation, note)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (src_id, dst_id, relation) DO NOTHING
            """,
            (doc["knowledge_id"], rel["target_id"], rel["type"], rel.get("note")),
        )

    if inserted:
        cur.execute(
            """
            INSERT INTO ko_state_event (knowledge_id, from_status, to_status, actor, actor_role, reason)
            VALUES (%s, NULL, %s, %s, %s, %s)
            """,
            (doc["knowledge_id"], status, prov["producer"], "agent",
             "compiled/ingested by knowledge-compiler-v1"),
        )
    return "inserted" if inserted else "exists"


def ingest_documents(conn, docs: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    out = {"inserted": 0, "exists": 0, "rejected": 0, "duplicate_claim": 0}
    for doc in docs:
        try:
            out[ingest_document(conn, doc)] += 1
        except KOWriteError:
            out["rejected"] += 1
    return out


def _jdump(obj: Any) -> str | None:
    """JSONB 列写入：非有限浮点（inf/nan）一律写 null，绝不让库崩。"""
    if obj is None:
        return None
    return json.dumps(_finite(obj), ensure_ascii=False)


def _finite(obj: Any) -> Any:
    import math

    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _finite(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_finite(v) for v in obj]
    return obj


def _content_sha(doc: Mapping[str, Any]) -> str:
    import hashlib

    body = json.loads(json.dumps(doc))
    prov = body.get("provenance")
    if isinstance(prov, dict):
        prov.pop("content_sha256", None)
    canon = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ 检索
def search(conn, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
    """检索面：claim/subject/domain 三列 ILIKE + 证据回链（入库即可查）。"""
    cur = conn.cursor()
    like = "%" + query.replace("%", r"\%") + "%"
    cur.execute(
        """
        SELECT o.knowledge_id, o.type, o.domain, o.subject, o.claim, o.verification_status,
               o.storage_level, e.report_id, e.section_anchor, e.section_heading
        FROM ko_object o
        LEFT JOIN ko_evidence e ON e.knowledge_id = o.knowledge_id AND e.ordinal = 0
        WHERE o.claim ILIKE %s OR o.subject ILIKE %s OR o.domain ILIKE %s
        ORDER BY o.knowledge_id
        LIMIT %s
        """,
        (like, like, like, limit),
    )
    cols = [d.name for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def get(conn, knowledge_id: str) -> dict[str, Any] | None:
    cur = conn.cursor()
    cur.execute("SELECT doc FROM ko_object WHERE knowledge_id = %s", (knowledge_id,))
    row = cur.fetchone()
    return row[0] if row else None


def stats(conn) -> dict[str, Any]:
    cur = conn.cursor()
    out: dict[str, Any] = {}
    for name, sql in (
        ("objects", "SELECT count(*) FROM ko_object"),
        ("evidence", "SELECT count(*) FROM ko_evidence"),
        ("relations", "SELECT count(*) FROM ko_relation"),
        ("state_events", "SELECT count(*) FROM ko_state_event"),
        ("verified_l3", "SELECT count(*) FROM ko_object WHERE verification_status='platform_verified'"),
    ):
        cur.execute(sql)
        out[name] = int(cur.fetchone()[0])
    cur.execute("SELECT verification_status, count(*) FROM ko_object GROUP BY 1 ORDER BY 1")
    out["by_status"] = {k: int(v) for k, v in cur.fetchall()}
    cur.execute("SELECT count(DISTINCT report_id) FROM ko_evidence")
    out["reports_covered"] = int(cur.fetchone()[0])
    return out


def schema_exists(conn, schema: str = DEFAULT_SCHEMA) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema=%s AND table_name='ko_object'",
        (schema,),
    )
    return bool(cur.fetchone()[0])


def iter_docs(conn, *, limit: int | None = None) -> list[dict[str, Any]]:
    cur = conn.cursor()
    sql = "SELECT doc FROM ko_object ORDER BY knowledge_id"
    if limit:
        sql += " LIMIT %d" % int(limit)
    cur.execute(sql)
    return [r[0] for r in cur.fetchall()]


def search_terms_ok(conn, docs: Sequence[Mapping[str, Any]], *, sample: int = 3) -> dict[str, Any]:
    """检索连通性自检：每份文档取 claim 里的一个 token，回查必须命中自身 id。"""
    hit = miss = 0
    misses: list[dict[str, Any]] = []
    for doc in docs:
        claim = doc["claim"]
        token = _probe_token(claim)
        got = {row["knowledge_id"] for row in search(conn, token, limit=200)}
        if doc["knowledge_id"] in got:
            hit += 1
        else:
            miss += 1
            if len(misses) < sample:
                misses.append({"knowledge_id": doc["knowledge_id"], "token": token})
    return {"searched": hit + miss, "hit": hit, "miss": miss, "miss_samples": misses}


def _probe_token(claim: str) -> str:
    """取引文里最有区分度的 token（优先含数字，其次最长拉丁词，最后取前 24 字符）。"""
    import re

    m = re.search(r"\d+(?:\.\d+)?%?", claim)
    if m:
        return m.group(0)
    words = sorted(re.findall(r"[A-Za-z][A-Za-z0-9_]{3,}", claim), key=len, reverse=True)
    if words:
        return words[0]
    return claim[:24]