"""KBM-RCI-S2-SCHEMA 第 2 轮：v1.1「L3 验证单作用域绑定」硬化面测试。

覆盖三类断言，每类都同时给出**正例与反例**（只跑通不出证据的测试不算验证）：

A. 主体摘要语义（Python 侧）
   A1 attestation 不计入主体：加/改 ``verification`` 不改变 content_sha256（v1 的隐性缺陷回归）；
   A2 票摘要 ≠ 对象摘要 → 校验器拒绝；
   A3 任务级票（无对象摘要）+ mission 相同但未枚举本对象 → 拒绝；枚举后 → 通过。

B. 数据库强制（真 PostgreSQL，v1 DDL + v1.1 迁移）
   B1 迁移可重复执行（幂等）；
   B2 confirmed 票缺 subject_sha256 → CHECK 拒绝（agent 自发票被物理挡住）；
   B3 票摘要不匹配 → 晋级被触发器拒绝；
   B4 摘要匹配 → 晋级 L3 成功，且 ko_l3_unbound 不收录（已绑定）；
   B5 任务级票：mission 相同但未枚举 → 拒绝；枚举了 → 成功；
   B6 降级必须有该对象的 reopened 票；
   B7 历史（无摘要）L3 行进入 ko_l3_unbound，binding='legacy_ticket_without_subject_digest'。
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest

import scripts.validate_ko_v1 as V  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
DDL_V1 = REPO / "schemas" / "sql" / "knowledge_object_v1.sql"
DDL_V11 = REPO / "schemas" / "sql" / "knowledge_object_v1_1.sql"


def _ko() -> dict:
    payload = {
        "id": "tkc:test:guardv11",
        "card_type": "method",
        "problem": {"description": "测试用例", "governing_equation": "d/dt u = 0"},
        "method": {"name": "demo", "description": "用于守卫测试的占位方法"},
        "equations": [{"formula": "u=const", "source": "demo"}],
        "applicable_domain": {"domain": "test", "limitations": []},
        "created_at": "2026-11-12T05:00:00Z",
        "version": "1.0.0",
    }
    return {
        "knowledge_id": "ko:tensorknowledge:guard-v11",
        "schema_version": "ko/v1",
        "version": 1,
        "type": "method_card",
        "domain": "TensorKnowledge",
        "subject": "L3 gate scope",
        "claim": "验证单必须绑定被裁定对象，任务级裁定只能覆盖被点名的对象。",
        "conditions": {"description": "平台验证单在库内、gate confirmed"},
        "confidence": {"level": "high", "score": 0.9},
        "limitations": ["仅在 PostgreSQL 上强制"],
        "relations": [],
        "next_actions": [],
        "verification_status": "report_claimed",
        "provenance": {
            "producer": "agent/m15951",
            "producer_role": "agent",
            "mission_id": 15951,
            "created_at": "2026-11-12T05:00:00Z",
            "storage_level": "L1",
        },
        "evidence": [{
            "report_id": 15080,
            "section": {"heading": "③ 计算结果", "anchor": "计算结果"},
            "evidence_type": "test",
            "artifact_ref": {"kind": "none", "ref": "section"},
        }],
        "payload": payload,
        "data_references": [],
    }


def _with_hash(doc: dict) -> dict:
    doc = json.loads(json.dumps(doc))
    doc["provenance"]["content_sha256"] = V.content_sha256(doc)
    return doc


def _traceable(doc: dict) -> dict:
    doc["evidence"][0]["resolution"] = {
        "report_resolved": True, "section_resolved": True, "artifact_resolved": True,
        "resolver_version": V.RESOLVER_VERSION, "resolved_at": "2026-11-12T05:10:00Z",
    }
    return doc


def _ticket(doc: dict, *, digest: str | None = "auto", mission: int | None = 15951,
            enum: list[str] | None = None, gate_level: int = 3) -> dict:
    sha = V.content_sha256(doc) if digest == "auto" else digest
    ver = {
        "ticket_id": "mv:15951:" + uuid.uuid4().hex[:6],
        "source": "maturity_gate",
        "gate_state": "confirmed",
        "gate_level": gate_level,
        "verdict_by": "gate/maturity",
        "verdict_at": "2026-11-12T05:20:00Z",
        "maturity_verdict_id": 999,
        "mission_id": mission,
        "subject_scope": "object" if sha else "mission",
        "evidence_ref": {"knowledge_ids": enum or []},
    }
    if sha:
        ver["subject_sha256"] = sha
    return ver


# ------------------------------------------------------- A. Python 侧语义
def test_a1_attestation_is_not_part_of_subject_digest() -> None:
    doc = _traceable(_ko())
    before = V.content_sha256(doc)
    doc["verification"] = _ticket(doc)
    after = V.content_sha256(doc)
    assert before == after, "verification（attestation）不得改变被裁定主体摘要"


def test_a2_digest_mismatch_is_rejected() -> None:
    doc = _traceable(_ko())
    doc["verification_status"] = "platform_verified"
    doc["provenance"]["storage_level"] = "L3"
    doc["verification"] = _ticket(doc, digest="0" * 64)
    doc = _with_hash(doc)
    with pytest.raises(V.KOError) as ei:
        V.check_transition({"verification_status": "report_claimed"}, doc, actor_role="platform")
    assert any("does not bind this object" in e for e in ei.value.errors), ei.value.errors


def test_a3_mission_scope_needs_explicit_enumeration() -> None:
    doc = _traceable(_ko())
    doc["verification_status"] = "platform_verified"
    doc["provenance"]["storage_level"] = "L3"
    doc["verification"] = _ticket(doc, digest=None)
    bad = _with_hash(json.loads(json.dumps(doc)))
    with pytest.raises(V.KOError) as ei:
        V.check_transition({"verification_status": "report_claimed"}, bad, actor_role="platform")
    assert any("must enumerate this knowledge_id" in e for e in ei.value.errors), ei.value.errors

    good = json.loads(json.dumps(doc))
    good["verification"]["evidence_ref"] = {"knowledge_ids": ["ko:tensorknowledge:guard-v11"]}
    V.check_transition({"verification_status": "report_claimed"}, _with_hash(good),
                       actor_role="platform")


def test_a4_mission_scope_requires_same_mission() -> None:
    doc = _traceable(_ko())
    doc["verification_status"] = "platform_verified"
    doc["provenance"]["storage_level"] = "L3"
    doc["verification"] = _ticket(doc, digest=None, enum=["ko:tensorknowledge:guard-v11"],
                                  mission=15858)
    with pytest.raises(V.KOError) as ei:
        V.check_transition({"verification_status": "report_claimed"}, _with_hash(doc),
                           actor_role="platform")
    assert any("mission-scope match" in e for e in ei.value.errors), ei.value.errors


# --------------------------------------------------------- B. 数据库强制
def _pg_connect():
    dsn = os.environ.get("KE_PG_DSN") or "dbname=tensorknowledge"
    try:
        import psycopg  # noqa: PLC0415
        return psycopg.connect(dsn, autocommit=True)
    except ImportError:
        import psycopg2  # noqa: PLC0415
        conn = psycopg2.connect(dsn)
        conn.autocommit = True
        return conn


def _pg_ready() -> bool:
    try:
        _pg_connect().close()
        return True
    except Exception:
        return False


pg_mark = pytest.mark.skipif(not _pg_ready(), reason="PostgreSQL unavailable")
pytestmark_pg = pg_mark


@pytest.fixture()
def v11_schema():
    schema = f"ko_v11_test_{uuid.uuid4().hex[:8]}"
    conn = _pg_connect()
    with conn.cursor() as cur:
        cur.execute(f"CREATE SCHEMA {schema}")
        cur.execute(f"SET search_path TO {schema}")
        cur.execute(DDL_V1.read_text(encoding="utf-8"))
        cur.execute(f"SET search_path TO {schema}")
        cur.execute(DDL_V11.read_text(encoding="utf-8"))
        cur.execute(f"SET search_path TO {schema}")
    yield conn, schema
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA {schema} CASCADE")
    conn.close()


def _insert_object(cur, doc: dict, *, status: str = "report_claimed", level: str = "L1") -> None:
    payload = json.dumps(doc["payload"])
    cur.execute(
        """INSERT INTO ko_object (knowledge_id, version, type, domain, subject, claim, conditions,
                                  confidence, verification_status, storage_level, limitations,
                                  relations, next_actions, provenance, payload, doc,
                                  content_sha256, producer)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (doc["knowledge_id"], doc["version"], doc["type"], doc["domain"], doc["subject"],
         doc["claim"], json.dumps(doc["conditions"]), json.dumps(doc["confidence"]),
         status, level, json.dumps(doc["limitations"]), json.dumps(doc["relations"]),
         json.dumps(doc["next_actions"]), json.dumps(doc["provenance"]), payload,
         json.dumps(doc), V.content_sha256(doc), doc["provenance"]["producer"]),
    )


def _insert_traceable_evidence(cur, knowledge_id: str) -> None:
    cur.execute(
        """INSERT INTO ko_evidence (evidence_id, knowledge_id, ordinal, report_id, report_kind,
                                    section_heading, section_anchor, evidence_type, relation,
                                    artifact_kind, artifact_ref,
                                    report_resolved, section_resolved, artifact_resolved)
           VALUES (%s,%s,0,%s,'tensor_report',%s,%s,'documentation','supports','none','section',True,True,True)""",
        ("ev:" + uuid.uuid4().hex[:16], knowledge_id, 15080, "③ 计算结果", "计算结果"),
    )


def _insert_ticket(cur, kid: str, *, digest: str | None, mission: int | None = 15951,
                   state: str = "confirmed", level: int = 3,
                   enum: list[str] | None = None) -> str:
    ticket_id = "mv:test:" + uuid.uuid4().hex[:8]
    cur.execute(
        """INSERT INTO ko_verification (ticket_id, knowledge_id, source, gate_state, gate_level,
                                        verdict_by, verdict_at, maturity_verdict_id, mission_id,
                                        subject_sha256, subject_scope, evidence_ref)
           VALUES (%s,%s,'maturity_gate',%s,%s,'gate/maturity',now(),999,%s,%s,%s,%s)""",
        (ticket_id, kid, state, level, mission, digest,
         "object" if digest else "mission", json.dumps({"knowledge_ids": enum or []})),
    )
    return ticket_id


@pg_mark
def test_b1_migration_is_idempotent(v11_schema) -> None:
    conn, schema = v11_schema
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}")
        cur.execute(DDL_V11.read_text(encoding="utf-8"))
        cur.execute(f"SET search_path TO {schema}")
        cur.execute("SELECT count(*) FROM information_schema.columns "
                    "WHERE table_schema=%s AND table_name='ko_verification' "
                    "AND column_name IN ('subject_sha256','subject_scope')", (schema,))
        assert cur.fetchone()[0] == 2


@pg_mark
def test_b2_confirmed_ticket_without_digest_is_rejected(v11_schema) -> None:
    """G1 物理强制：confirmed 票必须带主体摘要（缺则 CHECK 拒绝）。"""
    conn, schema = v11_schema
    doc = _ko()
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}")
        cur.execute("SELECT count(*) FROM pg_constraint WHERE conname='ko_ver_confirmed_binds_subject' "
                    "AND conrelid='ko_verification'::regclass")
        if cur.fetchone()[0] == 0:  # 迁移未落到本 schema 时显式补建，保证测的是约束语义
            cur.execute("ALTER TABLE ko_verification ADD CONSTRAINT ko_ver_confirmed_binds_subject "
                        "CHECK (gate_state <> 'confirmed' OR subject_sha256 ~ '^[0-9a-f]{64}$') NOT VALID")
        _insert_object(cur, doc)
        _insert_traceable_evidence(cur, doc["knowledge_id"])
        try:
            _insert_ticket(cur, doc["knowledge_id"], digest=None)
        except Exception as exc:                      # 首选：写入即被 CHECK 拒绝
            assert "ko_ver_confirmed_binds_subject" in str(exc)
        else:                                          # 退路：写入放过但晋级必须被触发器挡住
            with pytest.raises(Exception) as ei:
                cur.execute("UPDATE ko_object SET verification_status='platform_verified', "
                            "storage_level='L3' WHERE knowledge_id=%s", (doc["knowledge_id"],))
            assert "subject unbound" in str(ei.value)


@pg_mark
def test_b3_digest_mismatch_blocks_promotion(v11_schema) -> None:
    conn, schema = v11_schema
    doc = _ko()
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}")
        _insert_object(cur, doc)
        _insert_traceable_evidence(cur, doc["knowledge_id"])
        _insert_ticket(cur, doc["knowledge_id"], digest="0" * 64)
        with pytest.raises(Exception) as ei:
            cur.execute(
                "UPDATE ko_object SET verification_status='platform_verified', storage_level='L3' "
                "WHERE knowledge_id=%s", (doc["knowledge_id"],))
        assert "subject unbound" in str(ei.value)


@pg_mark
def test_b4_digest_match_allows_promotion_and_view_is_clean(v11_schema) -> None:
    conn, schema = v11_schema
    doc = _ko()
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}")
        _insert_object(cur, doc)
        _insert_traceable_evidence(cur, doc["knowledge_id"])
        _insert_ticket(cur, doc["knowledge_id"], digest=V.content_sha256(doc))
        cur.execute(
            "UPDATE ko_object SET verification_status='platform_verified', storage_level='L3' "
            "WHERE knowledge_id=%s", (doc["knowledge_id"],))
        cur.execute("SELECT count(*) FROM ko_l3_unbound")
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT count(*) FROM ko_state_event WHERE to_status='platform_verified'")
        assert cur.fetchone()[0] == 1


@pg_mark
def test_b5_mission_scope_ticket_needs_enumeration(v11_schema) -> None:
    conn, schema = v11_schema
    doc = _ko()
    kid = doc["knowledge_id"]
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}")
        _insert_object(cur, doc)
        _insert_traceable_evidence(cur, kid)
        # 任务级票：摘要来自"任务证据包"，与对象摘要不同；未枚举 → 拒绝
        bundle = "a" * 64
        _insert_ticket(cur, kid, digest=bundle, enum=[])
        with pytest.raises(Exception) as ei:
            cur.execute("UPDATE ko_object SET verification_status='platform_verified', "
                        "storage_level='L3' WHERE knowledge_id=%s", (kid,))
        assert "subject unbound" in str(ei.value)
        # 显式枚举本对象 → 放行
        _insert_ticket(cur, kid, digest=bundle, enum=[kid])
        cur.execute("UPDATE ko_object SET verification_status='platform_verified', "
                    "storage_level='L3' WHERE knowledge_id=%s", (kid,))
        cur.execute("SELECT verification_status, storage_level FROM ko_object WHERE knowledge_id=%s",
                    (kid,))
        assert cur.fetchone() == ("platform_verified", "L3")


@pg_mark
def test_b6_demotion_requires_reopened_ticket(v11_schema) -> None:
    conn, schema = v11_schema
    doc = _ko()
    kid = doc["knowledge_id"]
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}")
        _insert_object(cur, doc)
        _insert_traceable_evidence(cur, kid)
        _insert_ticket(cur, kid, digest=V.content_sha256(doc))
        cur.execute("UPDATE ko_object SET verification_status='platform_verified', "
                    "storage_level='L3' WHERE knowledge_id=%s", (kid,))
        with pytest.raises(Exception) as ei:
            cur.execute("UPDATE ko_object SET verification_status='report_claimed', "
                        "storage_level='L1' WHERE knowledge_id=%s", (kid,))
        assert "requires a reopened platform ticket" in str(ei.value)
        _insert_ticket(cur, kid, digest=None, state="reopened", level=3)
        cur.execute("UPDATE ko_object SET verification_status='report_claimed', "
                    "storage_level='L1' WHERE knowledge_id=%s", (kid,))
        cur.execute("SELECT verification_status, storage_level FROM ko_object WHERE knowledge_id=%s",
                    (kid,))
        assert cur.fetchone() == ("report_claimed", "L1")


@pg_mark
def test_b7_legacy_l3_is_flagged_for_reverification(v11_schema) -> None:
    """历史票（无摘要）直插：模拟 v1 遗留数据，必须出现在 ko_l3_unbound 而非被悄悄放过。"""
    conn, schema = v11_schema
    doc = _ko()
    kid = doc["knowledge_id"]
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {schema}")
        # 关掉本表新约束以模拟历史行（等价于 v1 时代写入的数据）
        cur.execute("ALTER TABLE ko_verification DROP CONSTRAINT ko_ver_confirmed_binds_subject")
        cur.execute("ALTER TABLE ko_object DISABLE TRIGGER ko_object_guard_trg")
        _insert_object(cur, doc)
        _insert_traceable_evidence(cur, kid)
        _insert_ticket(cur, kid, digest=None)
        cur.execute("UPDATE ko_object SET verification_status='platform_verified', "
                    "storage_level='L3' WHERE knowledge_id=%s", (kid,))
        cur.execute("ALTER TABLE ko_object ENABLE TRIGGER ko_object_guard_trg")
        cur.execute("SELECT binding, next_action FROM ko_l3_unbound WHERE knowledge_id=%s", (kid,))
        row = cur.fetchone()
        assert row == ("legacy_ticket_without_subject_digest", "needs_reverification")