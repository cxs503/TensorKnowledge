"""Knowledge Object Schema v1 — ingest service (L1 structured record → L2 relation net).

锚点 KBM-RCI-S2-SCHEMA。这是 Schema v1 的**写入侧真实现**，不重新发明规则：

* 文档校验与状态机判定全部复用 :mod:`scripts.validate_ko_v1`（单一真相源）；
* 证据三闸（报告/小节/工件）由 ``resolve_evidence`` 现场解析后**落库为事实列**
  （``report_resolved`` / ``section_resolved`` / ``artifact_resolved``），
  可追溯率因此可被 SQL 复算，而不是写在文档里的自述；
* L3 晋级只走平台验证单：调用方必须先 ``add_ticket`` 写入
  ``ko_verification(gate_state='confirmed', gate_level>=2)``，再由 DDL 触发器复核
  证据三闸全绿；Agent 侧自宣布在数据库层被拒（owner 铁则的机器实现）。

被谁调用（integration）
----------------------
``ke/api.py`` 的 ``POST /ko/v1/ingest`` / ``POST /ko/v1/{knowledge_id}/promote``
端点直接调用本模块（KE 服务=平台侧真调用方）；CLI 入口是 ``scripts/ko_v1.py``。

用法::

    from ke import ko_ingest

    conn = ko_ingest.connect()                       # KO_DSN 或 dbname=tensorknowledge
    ko_ingest.ensure_schema(conn, "ko_v1")           # 幂等应用 schemas/sql/knowledge_object_v1.sql
    rep = ko_ingest.ingest(conn, doc, reports=reports, repo_roots=[REPO])

过程工件（可核）: ``docs/rci/m15858/ingest_run.json``、``docs/rci/m15858/etr_live.json``。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
DDL_PATH = REPO / "schemas" / "sql" / "knowledge_object_v1.sql"

#: 与 DDL 的 CHECK 词表保持一致（写库前先自检，错在 Python 侧就停，别让数据库兜底）
EVIDENCE_TYPES = ("measurement", "simulation", "analytic", "literature",
                  "code", "test", "dataset", "documentation")
ARTIFACT_KINDS = ("tensor_data_artifact", "repo_path", "report_figure",
                  "report_section", "url", "none")
RELATIONS = ("supports", "refines", "contradicts", "supersedes", "depends_on",
             "derived_from", "instance_of", "measured_by", "fails_on", "replicated_by")


class KoIngestError(RuntimeError):
    """写入前置条件不成立（校验失败/重复/票据缺失），不是数据库异常。"""


def validator():
    """惰性导入校验器（``scripts/validate_ko_v1.py``），避免包导入期副作用。"""
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from scripts import validate_ko_v1  # noqa: PLC0415

    return validate_ko_v1


def default_dsn() -> str:
    return os.environ.get("KO_DSN") or "dbname=tensorknowledge"


def connect(dsn: str | None = None):
    """psycopg3 优先（psycopg2 在 loong64 沙箱里是 stub）。autocommit=真。"""
    try:
        import psycopg  # noqa: PLC0415

        return psycopg.connect(dsn or default_dsn(), autocommit=True)
    except ImportError:
        import psycopg2  # noqa: PLC0415

        conn = psycopg2.connect(dsn or default_dsn())
        conn.autocommit = True
        return conn


def ensure_schema(conn, schema: str = "ko_v1", ddl: Path | str | None = None) -> str:
    """幂等建 schema + 应用 DDL（DDL 自带 BEGIN/COMMIT，可在 autocommit 连接上整段执行）。"""
    text = Path(ddl).read_text(encoding="utf-8") if ddl else DDL_PATH.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        cur.execute(f"SET search_path TO {schema}, public")
        cur.execute(text)
    return schema


def evidence_id(knowledge_id: str, ordinal: int) -> str:
    """确定性 id（幂等重放不产生新证据行）。"""
    return "ev:" + hashlib.sha256(f"{knowledge_id}|{ordinal}".encode()).hexdigest()[:16]


def _evidence_row(ev: Mapping[str, Any], knowledge_id: str, ordinal: int) -> tuple:
    section = dict(ev.get("section") or {})
    anchor = str(section.get("anchor") or validator().slugify(str(section.get("heading", ""))))
    span = section.get("span") or [None, None]
    art = dict(ev.get("artifact_ref") or {})
    kind = str(art.get("kind") or "none")
    ref = str(art.get("ref") or ("none" if kind == "none" else ""))
    resolution = dict(ev.get("resolution") or {})
    etype = str(ev.get("evidence_type") or "documentation")
    if etype not in EVIDENCE_TYPES:
        raise KoIngestError(f"evidence_type 不在 DDL 词表: {etype}")
    if kind not in ARTIFACT_KINDS:
        raise KoIngestError(f"artifact_kind 不在 DDL 词表: {kind}")
    return (
        evidence_id(knowledge_id, ordinal), knowledge_id, ordinal, int(ev["report_id"]),
        str(ev.get("report_kind") or "tensor_report"),
        str(section.get("heading") or ""), anchor, span[0], span[1],
        section.get("section_sha256"), ev.get("excerpt"), etype,
        str(ev.get("relation") or "supports"), kind, ref,
        art.get("sha256"), bool(resolution.get("report_resolved")),
        bool(resolution.get("section_resolved")), resolution.get("artifact_resolved"),
        resolution.get("resolver_version"), resolution.get("resolved_at"),
    )


_INSERT_EVIDENCE = """INSERT INTO ko_evidence (
    evidence_id, knowledge_id, ordinal, report_id, report_kind, section_heading,
    section_anchor, section_start, section_end, section_sha256, excerpt, evidence_type,
    relation, artifact_kind, artifact_ref, artifact_sha256, report_resolved,
    section_resolved, artifact_resolved, resolver_version, resolved_at)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""

_INSERT_OBJECT = """INSERT INTO ko_object (
    knowledge_id, version, type, domain, subject, claim, conditions, confidence,
    verification_status, storage_level, limitations, relations, next_actions,
    provenance, payload, doc, content_sha256, producer)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""


def ingest(
    conn,
    doc: Mapping[str, Any],
    *,
    schema: str = "ko_v1",
    reports: Mapping[str, Mapping[str, Any]] | None = None,
    repo_roots: Sequence[Path] | None = None,
    on_conflict: str = "error",
) -> dict[str, Any]:
    """校验 → 证据三闸解析 → L1/L2 结构化落库。返回可审计的过程记录。"""
    V = validator()
    V.validate_document(doc)                                  # 不合规即抛 KoError
    kid = str(doc["knowledge_id"])
    prov = dict(doc["provenance"])
    sha = V.content_sha256(doc)
    declared = prov.get("content_sha256")
    if declared and str(declared) != sha:
        raise KoIngestError(f"content_sha256 不符: declared={declared} actual={sha}")

    resolved = [V.resolve_evidence(ev, reports=reports, repo_roots=repo_roots)
                for ev in doc.get("evidence") or []]
    stats = V.evidence_traceability(resolved)
    level = str(prov.get("storage_level") or "L1")
    relation_list = list(doc.get("relations") or [])

    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}, public")
        cur.execute("SELECT content_sha256, storage_level FROM ko_object WHERE knowledge_id=%s",
                    (kid,))
        prior = cur.fetchone()
        if prior:
            if on_conflict == "skip" and str(prior[0]) == sha:
                return {"knowledge_id": kid, "inserted": False, "reason": "identical_replay",
                        "content_sha256": sha, "traceability": stats}
            raise KoIngestError(f"knowledge_id 已存在（只增不覆盖，纠正请发新版本）: {kid}")
        cur.execute(_INSERT_OBJECT, (
            kid, int(doc["version"]), doc["type"], doc["domain"], doc["subject"],
            doc["claim"], json.dumps(doc["conditions"], ensure_ascii=False),
            json.dumps(doc["confidence"], ensure_ascii=False),
            doc["verification_status"], level,
            json.dumps(doc.get("limitations") or [], ensure_ascii=False),
            json.dumps(relation_list, ensure_ascii=False),
            json.dumps(doc.get("next_actions") or [], ensure_ascii=False),
            json.dumps(prov, ensure_ascii=False),
            json.dumps(doc.get("payload") or {}, ensure_ascii=False),
            json.dumps(doc, ensure_ascii=False, sort_keys=True), sha,
            str(prov.get("producer") or "unknown"),
        ))
        for ordinal, ev in enumerate(resolved):
            cur.execute(_INSERT_EVIDENCE, _evidence_row(ev, kid, ordinal))
        for rel in relation_list:
            rel_type = str(rel.get("type") or rel.get("relation") or "")
            dst = str(rel.get("target") or rel.get("dst_id") or "")
            if rel_type not in RELATIONS or not dst:
                continue
            cur.execute(
                "INSERT INTO ko_relation (src_id, dst_id, relation, note) "
                "VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (kid, dst, rel_type, rel.get("note")))
    return {
        "knowledge_id": kid, "inserted": True, "schema": schema,
        "storage_level": level, "verification_status": doc["verification_status"],
        "content_sha256": sha, "evidence_rows": len(resolved),
        "traceability": stats,
    }


def add_ticket(conn, knowledge_id: str, ticket_id: str, *, schema: str = "ko_v1",
               source: str = "maturity_gate", gate_state: str = "confirmed",
               gate_level: int = 2, verdict_by: str = "gate/maturity",
               maturity_verdict_id: int | None = None, mission_id: int | None = None,
               evidence_ref: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """写入平台验证单（L3 唯一凭据）。confirmed 且 gate_level>=2 才可能是 L3 通道。"""
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}, public")
        cur.execute(
            """INSERT INTO ko_verification (ticket_id, knowledge_id, source, gate_state,
                   gate_level, verdict_by, verdict_at, maturity_verdict_id, mission_id, evidence_ref)
               VALUES (%s,%s,%s,%s,%s,%s, now(), %s, %s, %s)""",
            (ticket_id, knowledge_id, source, gate_state, int(gate_level), verdict_by,
             maturity_verdict_id, mission_id, json.dumps(dict(evidence_ref or {}), ensure_ascii=False)))
    return {"ticket_id": ticket_id, "knowledge_id": knowledge_id, "source": source,
            "gate_state": gate_state, "gate_level": int(gate_level)}


def promote(conn, knowledge_id: str, *, schema: str = "ko_v1") -> dict[str, Any]:
    """report_claimed → platform_verified。合法性（票据 + 三闸全绿）由 DDL 触发器裁决。"""
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}, public")
        cur.execute("SELECT verification_status FROM ko_object WHERE knowledge_id=%s", (knowledge_id,))
        row = cur.fetchone()
        if not row:
            raise KoIngestError(f"未知 knowledge_id: {knowledge_id}")
        cur.execute(
            "UPDATE ko_object SET verification_status='platform_verified', storage_level='L3' "
            "WHERE knowledge_id=%s", (knowledge_id,))
    return {"knowledge_id": knowledge_id, "from": row[0], "to": "platform_verified",
            "storage_level": "L3"}


def traceability(conn, knowledge_id: str, *, schema: str = "ko_v1") -> dict[str, Any]:
    """从库内事实列复算 E-TR（与 validator 同一口径，因而不是第二套算法）。"""
    V = validator()
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}, public")
        cur.execute(
            """SELECT report_id, section_heading, artifact_kind, artifact_ref,
                      report_resolved, section_resolved, artifact_resolved
               FROM ko_evidence WHERE knowledge_id=%s ORDER BY ordinal""", (knowledge_id,))
        rows = cur.fetchall()
    evs = [{"report_id": r[0], "section": {"heading": r[1]}, "artifact_ref": {"kind": r[2], "ref": r[3]},
            "resolution": {"report_resolved": bool(r[4]), "section_resolved": bool(r[5]),
                           "artifact_resolved": r[6]}} for r in rows]
    return V.evidence_traceability(evs)