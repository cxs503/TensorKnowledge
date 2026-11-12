"""Schema v1 (KBM-RCI-S2-SCHEMA) contract tests.

三组断言：
  A. JSON Schema v1 收紧处：L3 必须带平台验证单（gate_state=confirmed / gate_level>=2）、
     L2 必须有 relations、五类卡 payload 必须过专属 card schema。
  B. 状态机 / L3 唯一通道：越级跳转被拒、Agent 自宣布 L3 被拒、reopen 反向一格合法。
  C. 证据可追溯率口径 E-TR 可计算，且三道单闸可分别定位失败原因；
     并在可用时把 DDL 真跑进 PostgreSQL scratch schema，验证约束不是纸上文字。
"""
from __future__ import annotations

import copy
import json
import os
import sys
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts import validate_ko_v1 as V  # noqa: E402

REPORT_MD = """# 报告

## ① 案例介绍
圆柱绕流，Re=100，D=1，U=1。

## ② 怎么做的
LBM D2Q9，格子 512x256，时间步 20000。

## ③ 计算结果
St = 0.1645（程序化注入）。

## ④ 结果图
![vort](fig1.png)

## ⑤ 注意点
入口段需足够长。

## ⑥ 误差判定
St 相对文献 0.165 误差 0.30%，<3%。
"""

REPORTS = {
    "900001": {
        "markdown": REPORT_MD,
        "figures": [{"name": "fig1.png", "caption": "涡量场"}],
    }
}

CARD = {
    "id": "tkc:tensorkbm:lbm-d2q9",
    "card_type": "method",
    "problem": {"description": "圆柱绕流非定常分离"},
    "method": {"name": "LBM D2Q9 BGK", "description": "单松弛格子玻尔兹曼", "family": "LBM"},
    "equations": [{"formula": "f_i(x+c_i dt, t+dt) = f_i - (f_i-f_i^eq)/tau", "source": "Chen & Doolen 1998"}],
    "applicable_domain": {"domain": "incompressible flow", "limitations": ["低 Mach 数"]},
    "created_at": "2026-11-12T00:00:00Z",
    "version": "1.0.0",
}


def _evidence(**over) -> dict:
    ev = {
        "report_id": 900001,
        "section": {"heading": "③ 计算结果"},
        "evidence_type": "simulation",
        "relation": "quantifies",
        "artifact_ref": {"kind": "report_figure", "ref": "fig1.png"},
    }
    ev.update(over)
    return ev


def _ko(**over) -> dict:
    doc = {
        "schema_version": "ko/v1",
        "knowledge_id": "ko:tensorkbm:lbm-d2q9-strouhal",
        "version": 1,
        "type": "method_card",
        "domain": "tensorkbm",
        "subject": "LBM D2Q9 圆柱绕流",
        "claim": "D2Q9 BGK 在 Re=100 圆柱绕流下给出 St=0.1645，与文献 0.165 相差 0.30%",
        "conditions": {
            "description": "二维不可压，Re=100，格子 512x256",
            "assumptions": ["低 Mach 数近似"],
            "validity_range": {"Re": "50-200"},
        },
        "evidence": [_evidence()],
        "confidence": {"level": "high", "score": 0.9, "basis": "benchmark_tolerance"},
        "verification_status": "report_claimed",
        "limitations": ["未验证三维效应"],
        "relations": [],
        "next_actions": [{"action": "request_platform_verification", "anchor": "KBM-RCI-S2-SCHEMA"}],
        "provenance": {
            "producer": "agent/m15461",
            "producer_role": "agent",
            "mission_id": 15461,
            "created_at": "2026-11-12T00:00:00Z",
            "storage_level": "L1",
        },
        "payload": CARD,
        "data_references": [],
    }
    doc.update(over)
    return doc


def _with_hash(doc: dict) -> dict:
    doc = json.loads(json.dumps(doc))
    doc["provenance"]["content_sha256"] = V.content_sha256(doc)
    return doc


def _l3(doc: dict | None = None, ticket_state: str = "confirmed", gate_level: int = 3) -> dict:
    doc = json.loads(json.dumps(doc or _ko()))
    doc["verification_status"] = "platform_verified"
    doc["provenance"]["storage_level"] = "L3"
    doc["verification"] = {
        "ticket_id": "mv:15461:ko:tensorkbm:lbm-d2q9-strouhal",
        "source": "maturity_gate",
        "gate_state": ticket_state,
        "gate_level": gate_level,
        "verdict_by": "gate/maturity",
        "verdict_at": "2026-11-12T01:00:00Z",
        "maturity_verdict_id": 286,
        "mission_id": 15461,
    }
    # L3 需要三闸全绿证据
    doc["evidence"][0]["resolution"] = {
        "report_resolved": True,
        "section_resolved": True,
        "artifact_resolved": True,
        "resolver_version": V.RESOLVER_VERSION,
        "resolved_at": "2026-11-12T00:30:00Z",
    }
    return _with_hash(doc)


# ---------------------------------------------------------------- A. schema v1
def test_valid_report_claimed_object_passes() -> None:
    V.validate_document(_with_hash(_ko()))


def test_self_declared_l3_without_ticket_is_rejected() -> None:
    doc = _ko()
    doc["verification_status"] = "platform_verified"
    doc["provenance"]["storage_level"] = "L3"
    doc = _with_hash(doc)
    with pytest.raises(V.KOError) as ei:
        V.validate_document(doc)
    assert any("verification" in e for e in ei.value.errors), ei.value.errors


def test_l3_with_reopened_ticket_is_rejected() -> None:
    with pytest.raises(V.KOError) as ei:
        V.validate_document(_with_hash(_l3(ticket_state="reopened")))
    assert any("gate_state" in e for e in ei.value.errors), ei.value.errors


def test_l3_with_gate_level_1_is_rejected() -> None:
    with pytest.raises(V.KOError) as ei:
        V.validate_document(_with_hash(_l3(gate_level=1)))
    assert any("gate_level" in e for e in ei.value.errors), ei.value.errors


def test_confirmed_ticket_object_passes_and_hashes_coherently() -> None:
    doc = _l3()
    V.validate_document(doc)
    assert doc["provenance"]["content_sha256"] == V.content_sha256(doc)


def test_l2_requires_relations() -> None:
    doc = _ko()
    doc["provenance"]["storage_level"] = "L2"
    doc = _with_hash(doc)
    with pytest.raises(V.KOError) as ei:
        V.validate_document(doc)
    assert any("relations" in e for e in ei.value.errors), ei.value.errors


def test_card_payload_must_match_card_schema() -> None:
    doc = _ko(payload={"id": "tkc:x:y", "card_type": "method"})  # 缺 required
    with pytest.raises(V.KOError) as ei:
        V.validate_document(_with_hash(doc))
    assert any(e.startswith("payload(method-card.schema.json)") for e in ei.value.errors)


def test_evidence_requires_section_heading() -> None:
    doc = _ko(evidence=[_evidence(section={"anchor": "results"})])
    with pytest.raises(V.KOError) as ei:
        V.validate_document(_with_hash(doc))
    assert any("section.heading" in e for e in ei.value.errors)


def test_unknown_field_is_rejected_not_ignored() -> None:
    doc = _with_hash(_ko())
    doc["extra_field"] = 1
    with pytest.raises(V.KOError) as ei:
        V.validate_document(doc)
    assert any("extra_field" in e for e in ei.value.errors)


# ------------------------------------------------------- B. state machine / L3
def test_skip_level_transition_rejected() -> None:
    prev = {"verification_status": "unverified", "claim": _ko()["claim"]}
    with pytest.raises(V.KOError) as ei:
        V.check_transition(prev, _l3(), actor_role="platform")
    assert any("illegal transition unverified -> platform_verified" in e for e in ei.value.errors)


def test_agent_cannot_self_declare_l3() -> None:
    prev = {"verification_status": "report_claimed", "claim": _ko()["claim"]}
    with pytest.raises(V.KOError) as ei:
        V.check_transition(prev, _l3(), actor_role="agent")
    assert any("platform-only" in e for e in ei.value.errors)


def test_platform_can_promote_with_confirmed_ticket() -> None:
    prev = {"verification_status": "report_claimed", "claim": _ko()["claim"]}
    V.check_transition(prev, _l3(), actor_role="platform")


def test_reopen_demotion_is_legal_only_for_platform() -> None:
    prev = {"verification_status": "platform_verified", "claim": _ko()["claim"]}
    doc = _ko()
    doc["verification"] = {
        "ticket_id": "mv:reopen:1",
        "source": "maturity_gate",
        "gate_state": "reopened",
        "gate_level": 0,
        "verdict_by": "gate/maturity",
        "verdict_at": "2026-11-12T02:00:00Z",
    }
    with pytest.raises(V.KOError) as ei:
        V.check_transition(prev, doc, actor_role="agent")
    assert any("platform-only" in e for e in ei.value.errors)
    V.check_transition(prev, doc, actor_role="platform")


def test_l3_claim_immutable() -> None:
    prev = _l3()
    doc = _l3()
    doc["claim"] = "改成另一个结论"
    with pytest.raises(V.KOError) as ei:
        V.check_transition(prev, doc, actor_role="platform")
    assert any("immutable" in e for e in ei.value.errors)


# ---------------------------------------------------------- C. traceability
def test_section_anchors_are_derived_from_real_headings() -> None:
    sections = V.iter_sections(REPORT_MD)
    anchors = {s["anchor"] for s in sections}
    assert "案例介绍" in anchors and "计算结果" in anchors
    assert V.slugify("③ 计算结果") == "计算结果"


def test_resolve_evidence_all_gates_green() -> None:
    ev = V.resolve_evidence(_evidence(), reports=REPORTS)
    assert ev["resolution"]["report_resolved"] is True
    assert ev["resolution"]["section_resolved"] is True
    assert ev["resolution"]["artifact_resolved"] is True
    assert ev["section"]["section_sha256"]  # 摄取期回填，抗篡改


def test_wrong_section_fails_section_gate_only() -> None:
    ev = V.resolve_evidence(_evidence(section={"heading": "⑦ 不存在的章节"}), reports=REPORTS)
    assert ev["resolution"]["report_resolved"] is True
    assert ev["resolution"]["section_resolved"] is False
    assert ev["resolution"]["artifact_resolved"] is True


def test_missing_report_fails_report_gate() -> None:
    ev = V.resolve_evidence(_evidence(report_id=424242), reports=REPORTS)
    assert ev["resolution"]["report_resolved"] is False
    assert ev["resolution"]["section_resolved"] is False


def test_e_tr_counts_intersection_not_average() -> None:
    good = V.resolve_evidence(_evidence(), reports=REPORTS)
    bad_section = V.resolve_evidence(_evidence(section={"heading": "⑦ 无此节"}), reports=REPORTS)
    bad_report = V.resolve_evidence(_evidence(report_id=1), reports=REPORTS)
    stats = V.evidence_traceability([good, bad_section, bad_report])
    # 单闸各自 2/3（报告）或 1/3（小节），全绿只有 1/3 —— 口径取交集不是平均值
    # 报告闸挂掉时小节闸必然也挂（没有正文就没有锚点），这是有意的级联口径
    assert stats["evidence_total"] == 3
    assert stats["fully_traceable_n"] == 1
    assert stats["e_tr"] == pytest.approx(0.3333, abs=5e-5)
    assert stats["r1_report_resolvable"] == pytest.approx(0.6667, abs=5e-5)
    assert stats["r2_section_resolvable"] == pytest.approx(0.3333, abs=5e-5)


def test_itemp_none_artifact_is_not_penalised() -> None:
    ev = V.resolve_evidence(
        _evidence(evidence_type="documentation", artifact_ref={"kind": "none", "ref": "section"}),
        reports=REPORTS,
    )
    stats = V.evidence_traceability([ev])
    assert stats["e_tr"] == 1.0


# ------------------------------------------------------------------ C'. DDL
DDL = REPO / "schemas" / "sql" / "knowledge_object_v1.sql"


def _pg_connect():
    """psycopg3 preferred (psycopg2 is a stub on loong64 sandboxes)."""
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


PG_OK = _pg_ready()
pg_mark = pytest.mark.skipif(not PG_OK, reason="PostgreSQL (KE_PG_DSN / tensorknowledge) unavailable")


@pytest.fixture()
def ko_schema():
    schema = f"ko_v1_test_{uuid.uuid4().hex[:8]}"
    conn = _pg_connect()
    with conn.cursor() as cur:
        cur.execute(f"CREATE SCHEMA {schema}")
        cur.execute(f"SET search_path TO {schema}")
        cur.execute(DDL.read_text(encoding="utf-8"))
        cur.execute(f"SET search_path TO {schema}")
    yield conn, schema
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA {schema} CASCADE")
    conn.close()


def _insert_ko(cur, doc: dict) -> None:
    cur.execute(
        """INSERT INTO ko_object (knowledge_id, version, type, domain, subject, claim, conditions,
                                  confidence, verification_status, storage_level, limitations,
                                  relations, next_actions, provenance, payload, doc,
                                  content_sha256, producer)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            doc["knowledge_id"], doc["version"], doc["type"], doc["domain"], doc["subject"],
            doc["claim"], json.dumps(doc["conditions"]), json.dumps(doc["confidence"]),
            doc["verification_status"], doc["provenance"]["storage_level"],
            json.dumps(doc["limitations"]), json.dumps(doc["relations"]),
            json.dumps(doc["next_actions"]), json.dumps(doc["provenance"]),
            json.dumps(doc["payload"]), json.dumps(doc),
            doc["provenance"].get("content_sha256") or V.content_sha256(doc),
            doc["provenance"]["producer"],
        ),
    )


def _insert_evidence(cur, ev: dict, knowledge_id: str, ordinal: int = 0) -> None:
    cur.execute(
        """INSERT INTO ko_evidence (evidence_id, knowledge_id, ordinal, report_id, section_heading,
                                    section_anchor, section_sha256, evidence_type, artifact_kind,
                                    artifact_ref, artifact_sha256, report_resolved, section_resolved,
                                    artifact_resolved)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            f"ev:{uuid.uuid4().hex[:16]}", knowledge_id, ordinal, ev["report_id"],
            ev["section"]["heading"], ev["section"].get("anchor") or V.slugify(ev["section"]["heading"]),
            "0" * 64, ev["evidence_type"], ev["artifact_ref"]["kind"], ev["artifact_ref"]["ref"],
            None, False, False, None,
        ),
    )


@pg_mark
def test_ddl_rejects_l3_without_ticket(ko_schema):
    conn, _ = ko_schema
    with conn.cursor() as cur:
        # (a) 状态机越级：unverified -> platform_verified 直接拒（票据检查都到不了）
        raw = _ko()
        raw["verification_status"] = "unverified"
        _insert_ko(cur, raw)
        _insert_evidence(cur, raw["evidence"][0], raw["knowledge_id"])
        with pytest.raises(Exception) as ei:
            cur.execute(
                "UPDATE ko_object SET verification_status='platform_verified', storage_level='L3'"
                " WHERE knowledge_id=%s", (raw["knowledge_id"],)
            )
        assert "illegal verification transition" in str(ei.value)

        # (b) 合法边 report_claimed -> platform_verified，但没有平台票据 -> 仍拒
        doc = _ko(claim="D2Q9 在 Re=100 圆柱绕流下的 St 由平台基准门复核")
        doc["knowledge_id"] = "ko:tensorkbm:lbm-d2q9-strouhal-b"
        _insert_ko(cur, doc)
        _insert_evidence(cur, doc["evidence"][0], doc["knowledge_id"])
        with pytest.raises(Exception) as ei:
            cur.execute(
                "UPDATE ko_object SET verification_status='platform_verified', storage_level='L3'"
                " WHERE knowledge_id=%s", (doc["knowledge_id"],)
            )
        assert "requires a confirmed platform ticket" in str(ei.value)


@pg_mark
def test_ddl_promotes_l3_with_ticket_and_audits_state(ko_schema):
    conn, _ = ko_schema
    with conn.cursor() as cur:
        doc = _ko()
        _insert_ko(cur, doc)
        _insert_evidence(cur, doc["evidence"][0], doc["knowledge_id"])
        # 三闸全绿 + 平台票据
        cur.execute(
            "UPDATE ko_evidence SET report_resolved=TRUE, section_resolved=TRUE, artifact_resolved=TRUE"
        )
        cur.execute(
            """INSERT INTO ko_verification (ticket_id, knowledge_id, source, gate_state, gate_level,
                                            verdict_by, verdict_at)
               VALUES ('mv:1', %s, 'maturity_gate', 'confirmed', 3, 'gate/maturity', now())""",
            (doc["knowledge_id"],),
        )
        cur.execute(
            "UPDATE ko_object SET verification_status='report_claimed' WHERE knowledge_id=%s",
            (doc["knowledge_id"],),
        )
        cur.execute(
            "UPDATE ko_object SET verification_status='platform_verified', storage_level='L3'"
            " WHERE knowledge_id=%s", (doc["knowledge_id"],)
        )
        cur.execute("SELECT verification_status, storage_level FROM ko_object WHERE knowledge_id=%s",
                    (doc["knowledge_id"],))
        assert cur.fetchone() == ("platform_verified", "L3")
        cur.execute("SELECT from_status, to_status, actor_role, ticket_id FROM ko_state_event ORDER BY event_id")
        rows = cur.fetchall()
        assert rows[-1] == ("report_claimed", "platform_verified", "platform", "mv:1")
        cur.execute("SELECT missing_ticket FROM ko_l3_audit")
        assert cur.fetchone() == (False,)


@pg_mark
def test_ddl_l3_evidence_gate_and_immutability(ko_schema):
    conn, _ = ko_schema
    with conn.cursor() as cur:
        doc = _ko()
        _insert_ko(cur, doc)
        _insert_evidence(cur, doc["evidence"][0], doc["knowledge_id"])  # 三闸未绿
        cur.execute(
            """INSERT INTO ko_verification (ticket_id, knowledge_id, source, gate_state, gate_level,
                                            verdict_by, verdict_at)
               VALUES ('mv:2', %s, 'maturity_gate', 'confirmed', 3, 'gate/maturity', now())""",
            (doc["knowledge_id"],),
        )
        cur.execute("UPDATE ko_object SET verification_status='report_claimed' WHERE knowledge_id=%s",
                    (doc["knowledge_id"],))
        with pytest.raises(Exception) as ei:
            cur.execute(
                "UPDATE ko_object SET verification_status='platform_verified', storage_level='L3'"
                " WHERE knowledge_id=%s", (doc["knowledge_id"],)
            )
        assert "fully traceable evidence" in str(ei.value)

        cur.execute("UPDATE ko_evidence SET report_resolved=TRUE, section_resolved=TRUE, artifact_resolved=TRUE")
        cur.execute("UPDATE ko_object SET verification_status='platform_verified', storage_level='L3'"
                    " WHERE knowledge_id=%s", (doc["knowledge_id"],))
        with pytest.raises(Exception) as ei:
            cur.execute("UPDATE ko_object SET claim='被私自改写的结论' WHERE knowledge_id=%s",
                        (doc["knowledge_id"],))
        assert "immutable" in str(ei.value)
        with pytest.raises(Exception) as ei:
            cur.execute("DELETE FROM ko_evidence")
        assert "append-only" in str(ei.value)
        with pytest.raises(Exception) as ei:
            cur.execute("UPDATE ko_verification SET gate_level=4")
        assert "append-only" in str(ei.value)


@pg_mark
def test_ddl_confirmed_ticket_requires_level_2(ko_schema):
    conn, _ = ko_schema
    with conn.cursor() as cur:
        doc = _ko()
        _insert_ko(cur, doc)
        with pytest.raises(Exception) as ei:
            cur.execute(
                """INSERT INTO ko_verification (ticket_id, knowledge_id, source, gate_state, gate_level,
                                                verdict_by, verdict_at)
                   VALUES ('mv:3', %s, 'maturity_gate', 'confirmed', 1, 'gate/maturity', now())""",
                (doc["knowledge_id"],),
            )
        assert "ko_ver_confirmed_shape" in str(ei.value)


@pg_mark
def test_ddl_traceability_view_matches_python_meter(ko_schema):
    conn, _ = ko_schema
    with conn.cursor() as cur:
        doc = _ko()
        _insert_ko(cur, doc)
        _insert_evidence(cur, doc["evidence"][0], doc["knowledge_id"], ordinal=0)
        _insert_evidence(cur, doc["evidence"][0], doc["knowledge_id"], ordinal=1)
        cur.execute(
            "UPDATE ko_evidence SET report_resolved=TRUE, section_resolved=TRUE, artifact_resolved=TRUE"
            " WHERE ordinal=0"
        )
        cur.execute("UPDATE ko_evidence SET report_resolved=TRUE, section_resolved=FALSE"
                    " WHERE ordinal=1")
        cur.execute("SELECT e_tr_full, evidence_total, fully_traceable_n FROM ko_evidence_traceability_global")
        e_tr, total, full = cur.fetchone()
        assert (total, full) == (2, 1)
        assert float(e_tr) == pytest.approx(0.5)