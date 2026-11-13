"""KO Schema v1 ingest 服务契约测试（真 PostgreSQL，非 mock）。

覆盖：
  A. 写入路径：合法对象 → ko_object/ko_evidence 落库，三闸事实成列，E-TR 由库内事实复算
  B. 只增不覆盖：同 knowledge_id 重放（identical）不产生第二行；改内容重发被拒
  C. L3 唯一通道：无票据晋级被数据库拒；Agent 侧票据 gate_level=1 被拒（DDL CHECK）；
     三闸未全绿时即使有 confirmed 票据也被拒；票据+三闸全绿才晋级 L3
  D. CLI 入口：validate 合规/不合规退出码；gatecheck 按 evidence 文件复核
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ke import ko_ingest as KI  # noqa: E402
from scripts import ko_v1 as CLI  # noqa: E402
from scripts import validate_ko_v1 as V  # noqa: E402

sys.path.insert(0, str(REPO / "benchmarks" / "ko_v1_conformance"))
import cases as C  # noqa: E402


def _connect():
    return KI.connect(os.environ.get("KO_DSN") or "dbname=tensorknowledge")


def _pg_ready() -> bool:
    try:
        _connect().close()
        return True
    except Exception:
        return False


PG_OK = _pg_ready()
pg_mark = pytest.mark.skipif(not PG_OK, reason="PostgreSQL (KO_DSN/dbname=tensorknowledge) 不可用")


def _hashed(**over) -> dict:
    doc = C.base_ko(**over)
    doc["provenance"]["content_sha256"] = V.content_sha256(doc)
    return doc


@pytest.fixture()
def schema():
    name = f"ko_v1_ing_{uuid.uuid4().hex[:8]}"
    conn = _connect()
    KI.ensure_schema(conn, name)
    yield conn, name
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA {name} CASCADE")
    conn.close()


@pg_mark
def test_ingest_writes_object_and_evidence_facts(schema):
    conn, name = schema
    doc = _hashed()
    rep = KI.ingest(conn, doc, schema=name, reports=C.REPORTS, repo_roots=[REPO])
    assert rep["inserted"] is True
    assert rep["evidence_rows"] == 1
    assert rep["traceability"]["e_tr"] == 1.0          # 报告+小节+图 三闸全绿
    assert rep["content_sha256"] == doc["provenance"]["content_sha256"]
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {name}, public")
        cur.execute("SELECT verification_status, storage_level FROM ko_object WHERE knowledge_id=%s",
                    (doc["knowledge_id"],))
        assert cur.fetchone() == ("report_claimed", "L1")
        cur.execute("SELECT report_resolved, section_resolved, artifact_resolved "
                    "FROM ko_evidence WHERE knowledge_id=%s", (doc["knowledge_id"],))
        assert cur.fetchone() == (True, True, True)
    # 库内事实复算与写入期解析一致（同一口径，不是第二套算法）
    assert KI.traceability(conn, doc["knowledge_id"], schema=name)["e_tr"] == 1.0


@pg_mark
def test_ingest_is_append_only(schema):
    conn, name = schema
    doc = _hashed()
    KI.ingest(conn, doc, schema=name, reports=C.REPORTS, repo_roots=[REPO])
    replay = KI.ingest(conn, doc, schema=name, reports=C.REPORTS, repo_roots=[REPO],
                       on_conflict="skip")
    assert replay["inserted"] is False and replay["reason"] == "identical_replay"
    changed = _hashed(claim=doc["claim"] + "（改写）")
    with pytest.raises(KI.KoIngestError):
        KI.ingest(conn, changed, schema=name, reports=C.REPORTS, repo_roots=[REPO])


@pg_mark
def test_ingest_rejects_hash_mismatch(schema):
    conn, name = schema
    doc = C.base_ko()
    doc["provenance"]["content_sha256"] = "0" * 64
    with pytest.raises((KI.KoIngestError, V.KOError)):
        KI.ingest(conn, doc, schema=name, reports=C.REPORTS, repo_roots=[REPO])


@pg_mark
def test_l3_requires_ticket(schema):
    conn, name = schema
    doc = _hashed()
    KI.ingest(conn, doc, schema=name, reports=C.REPORTS, repo_roots=[REPO])
    with pytest.raises(Exception) as ei:
        KI.promote(conn, doc["knowledge_id"], schema=name)
    assert "ticket" in str(ei.value).lower()


@pg_mark
def test_l3_rejects_low_gate_level_ticket(schema):
    conn, name = schema
    doc = _hashed()
    KI.ingest(conn, doc, schema=name, reports=C.REPORTS, repo_roots=[REPO])
    with pytest.raises(Exception) as ei:
        KI.add_ticket(conn, doc["knowledge_id"], "mv:low", schema=name, gate_level=1)
    assert "ko_ver_confirmed_shape" in str(ei.value) or "check" in str(ei.value).lower()


@pg_mark
def test_l3_rejects_untraceable_evidence(schema):
    conn, name = schema
    doc = _hashed()
    # 工件闸解析不到（repo_path 不存在）→ 三闸不全绿
    doc["evidence"][0]["artifact_ref"] = {"kind": "repo_path", "ref": "does/not/exist.py"}
    doc["provenance"]["content_sha256"] = V.content_sha256(doc)
    rep = KI.ingest(conn, doc, schema=name, reports=C.REPORTS, repo_roots=[REPO])
    assert rep["traceability"]["e_tr"] == 0.0
    KI.add_ticket(conn, doc["knowledge_id"], "mv:green?no", schema=name, gate_level=3)
    with pytest.raises(Exception) as ei:
        KI.promote(conn, doc["knowledge_id"], schema=name)
    assert "traceable" in str(ei.value).lower() or "evidence" in str(ei.value).lower()


@pg_mark
def test_l3_promotes_with_ticket_and_green_evidence(schema):
    conn, name = schema
    doc = _hashed()
    KI.ingest(conn, doc, schema=name, reports=C.REPORTS, repo_roots=[REPO])
    KI.add_ticket(conn, doc["knowledge_id"], "mv:15858:ok", schema=name, gate_level=3,
                  maturity_verdict_id=286, mission_id=15858)
    rep = KI.promote(conn, doc["knowledge_id"], schema=name)
    assert rep["to"] == "platform_verified" and rep["storage_level"] == "L3"
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {name}, public")
        cur.execute("SELECT from_status, to_status, actor_role, ticket_id FROM ko_state_event "
                    "ORDER BY event_id DESC LIMIT 1")
        assert cur.fetchone() == ("report_claimed", "platform_verified", "platform", "mv:15858:ok")


def test_cli_validate_exit_codes(tmp_path):
    good = tmp_path / "good.json"
    good.write_text(json.dumps(_hashed(), ensure_ascii=False), encoding="utf-8")
    assert CLI.main(["validate", "--doc", str(good)]) == 0
    bad_doc = _hashed()
    bad_doc["verification_status"] = "platform_verified"
    bad_doc["provenance"]["storage_level"] = "L3"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(bad_doc, ensure_ascii=False), encoding="utf-8")
    assert CLI.main(["validate", "--doc", str(bad)]) == 1


def test_gatecheck_mirror_flags_missing_keys():
    lv, why = CLI.gatecheck({"tests": ["t"]}, 4)
    assert lv == 1 and any("impl_files" in r for r in why)