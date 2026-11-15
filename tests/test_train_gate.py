"""训练出口闸门（FEAT-SIM-DATAHOUSE）测试：三态流转 / 审计 / 红队 / API。

覆盖：
  * train_gate 表 CHECK：定级行缺审定人或证据链 -> 写入失败
  * 流转合法性：跨级跳、自审、重复流转、publish 同人（四眼）全部拒绝
  * 每次流转留审计行（register/transition/revoke）
  * 红队：拿裸 sqlite3 直改审级 / 偷换审定人 / 篡改审计行 / 删审计行 -> 全部被拦
  * 训练侧可见性：level=none -> PermissionError(403)；reviewed 只认 include=reviewed
  * HTTP：/api/v1/knowledge/train-gate 的 GET/POST（含 401/503 写面保护）
  * 下载端点：未过审版本 curl=403；include=all 永不开放

Run: python -m pytest tests/test_train_gate.py -v
"""
from __future__ import annotations

import json
import sqlite3
import threading
from http.client import HTTPConnection

import pytest

from ke.train_gate import LEVELS, TrainGateStore

DS = "FEAT-SIM-DATAHOUSE"
VER = "v1.0"
PRODUCER = "sim-datahouse-pipeline"
EVIDENCE = ["tkc:review-form-v1.0", "tke:geometry-cb-check-v1.0"]


@pytest.fixture()
def gate():
    g = TrainGateStore(":memory:")
    g.register(DS, VER, producer=PRODUCER)
    return g


# ---------------------------------------------------------------------------
# schema / CHECK
# ---------------------------------------------------------------------------

def test_register_starts_at_none(gate):
    row = gate.get(DS, VER)
    assert row["review_level"] == "none"
    assert row["reviewer"] is None and row["evidence_chain"] is None
    assert row["admitted_at"] is None
    assert gate.visible_for_training(DS, VER) is False


def test_check_constraint_rejects_graded_row_without_evidence(gate):
    with pytest.raises(sqlite3.IntegrityError):
        with gate.conn:
            gate.conn.execute(
                "INSERT INTO train_gate (dataset_id, version, review_level, reviewer,"
                " evidence_chain, admitted_at, created_at, updated_at)"
                " VALUES ('X','v1','reviewed','rev-a',NULL,'t','t','t')"
            )


def test_check_constraint_rejects_self_review(gate):
    """审级 + 审定人齐全，但审定人 == 产出方 -> CHECK 拦下。"""
    with pytest.raises(sqlite3.IntegrityError):
        with gate.conn:
            gate.conn.execute(
                "INSERT INTO train_gate (dataset_id, version, review_level, reviewer,"
                " evidence_chain, producer, admitted_at, created_at, updated_at)"
                " VALUES ('X','v1','reviewed',?,'tkc:x','rev-a','t','t','t')",
                ("rev-a",),
            )


# ---------------------------------------------------------------------------
# transitions
# ---------------------------------------------------------------------------

def test_happy_path_none_reviewed_published(gate):
    r1 = gate.transition(DS, VER, "reviewed", reviewer="rev-zhang",
                         evidence_chain=EVIDENCE, actor="rev-zhang")
    assert r1["review_level"] == "reviewed"
    assert r1["reviewer"] == "rev-zhang"
    assert r1["admitted_at"] is not None  # 入训练集时间在首次可见时打点
    r2 = gate.transition(DS, VER, "published", reviewer="pub-li",
                         evidence_chain=EVIDENCE, actor="pub-li")
    assert r2["review_level"] == "published"
    assert gate.integrity_alerts() == []


def test_skip_level_rejected(gate):
    with pytest.raises(ValueError, match="illegal transition"):
        gate.transition(DS, VER, "published", reviewer="rev", evidence_chain=EVIDENCE,
                        actor="rev")


def test_self_review_rejected(gate):
    with pytest.raises(ValueError, match="self-review"):
        gate.transition(DS, VER, "reviewed", reviewer=PRODUCER, evidence_chain=EVIDENCE,
                        actor=PRODUCER)


def test_publish_requires_different_reviewer(gate):
    gate.transition(DS, VER, "reviewed", reviewer="rev-zhang", evidence_chain=EVIDENCE,
                    actor="rev-zhang")
    with pytest.raises(ValueError, match="four-eyes"):
        gate.transition(DS, VER, "published", reviewer="rev-zhang", evidence_chain=EVIDENCE,
                        actor="rev-zhang")


def test_empty_evidence_rejected(gate):
    with pytest.raises(ValueError, match="evidence_chain"):
        gate.transition(DS, VER, "reviewed", reviewer="rev", evidence_chain=[], actor="rev")


def test_each_transition_writes_audit_row(gate):
    gate.transition(DS, VER, "reviewed", reviewer="rev-zhang", evidence_chain=EVIDENCE,
                    actor="rev-zhang", note="review pass")
    gate.transition(DS, VER, "published", reviewer="pub-li", evidence_chain=EVIDENCE,
                    actor="pub-li")
    audit = gate.audit(DS, VER)
    assert [(a["action"], a["from_level"], a["to_level"]) for a in audit] == [
        ("register", None, "none"),
        ("transition", "none", "reviewed"),
        ("transition", "reviewed", "published"),
    ]


def test_revoke_returns_to_none_and_is_audited(gate):
    gate.transition(DS, VER, "reviewed", reviewer="rev-zhang", evidence_chain=EVIDENCE,
                    actor="rev-zhang")
    row = gate.revoke(DS, VER, actor="admin", note="样本抽检不合格，撤回")
    assert row["review_level"] == "none"
    assert row["admitted_at"] is None
    assert gate.audit(DS, VER)[-1]["action"] == "revoke"
    with pytest.raises(PermissionError):
        gate.require_train_visible(DS, VER, "reviewed")


# ---------------------------------------------------------------------------
# red team: forged grades straight into the DB
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sql", [
    "UPDATE train_gate SET review_level='published' WHERE dataset_id='%s' AND version='%s'",
    "UPDATE train_gate SET review_level='reviewed', reviewer='ghost'"
    " WHERE dataset_id='%s' AND version='%s'",
])
def test_forged_level_update_blocked(gate, sql):
    stmt = sql % (DS, VER)
    with pytest.raises(sqlite3.IntegrityError, match="unguarded UPDATE"):
        with gate.conn:
            gate.conn.execute(stmt)
    assert gate.get(DS, VER)["review_level"] == "none"


def test_forged_reviewer_swap_blocked(gate):
    gate.transition(DS, VER, "reviewed", reviewer="rev-zhang", evidence_chain=EVIDENCE,
                    actor="rev-zhang")
    with pytest.raises(sqlite3.IntegrityError, match="unguarded UPDATE"):
        with gate.conn:
            gate.conn.execute(
                "UPDATE train_gate SET reviewer='someone-else'"
                " WHERE dataset_id=? AND version=?", (DS, VER))
    assert gate.get(DS, VER)["reviewer"] == "rev-zhang"


def test_audit_table_is_append_only(gate):
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        with gate.conn:
            gate.conn.execute("UPDATE train_gate_audit SET to_level='published'")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        with gate.conn:
            gate.conn.execute("DELETE FROM train_gate_audit")


def test_graded_row_cannot_be_deleted(gate):
    gate.transition(DS, VER, "reviewed", reviewer="rev-zhang", evidence_chain=EVIDENCE,
                    actor="rev-zhang")
    with pytest.raises(sqlite3.IntegrityError, match="cannot be deleted"):
        with gate.conn:
            gate.conn.execute("DELETE FROM train_gate WHERE dataset_id=? AND version=?",
                              (DS, VER))


def test_out_of_band_row_raises_audit_alert(gate):
    """绕过 API 直插一行（无审计行）-> 对账告警。"""
    with gate.conn:
        gate.conn.execute(
            "INSERT INTO train_gate (dataset_id, version, review_level, reviewer,"
            " evidence_chain, producer, admitted_at, created_at, updated_at)"
            " VALUES (?,'v9.9','none',NULL,NULL,'rogue',NULL,'t','t')", (DS,))
    alerts = gate.integrity_alerts()
    assert any(a["kind"] == "missing_audit" and a["version"] == "v9.9" for a in alerts)


# ---------------------------------------------------------------------------
# training-side visibility
# ---------------------------------------------------------------------------

def test_none_level_invisible(gate):
    for include in ("published", "reviewed", "all"):
        with pytest.raises(PermissionError, match="level 'none'"):
            gate.require_train_visible(DS, VER, include)


def test_reviewed_level_requires_reviewed_include(gate):
    gate.transition(DS, VER, "reviewed", reviewer="rev-zhang", evidence_chain=EVIDENCE,
                    actor="rev-zhang")
    assert gate.require_train_visible(DS, VER, "reviewed") == "reviewed"
    with pytest.raises(PermissionError):
        gate.require_train_visible(DS, VER, "published")
    with pytest.raises(PermissionError):
        gate.require_train_visible(DS, VER, "all")


def test_published_level_allows_published_include(gate):
    gate.transition(DS, VER, "reviewed", reviewer="rev-zhang", evidence_chain=EVIDENCE,
                    actor="rev-zhang")
    gate.transition(DS, VER, "published", reviewer="pub-li", evidence_chain=EVIDENCE,
                    actor="pub-li")
    assert gate.require_train_visible(DS, VER, "published") == "published"
    assert gate.require_train_visible(DS, VER, "reviewed") == "published"


def test_ungated_dataset_reports_ungated():
    g = TrainGateStore(":memory:")
    assert g.require_train_visible("unknown", "v0") == "ungated"


def test_strict_mode_fails_closed_without_gate_row():
    g = TrainGateStore(":memory:", strict=True)
    g.register(DS, VER, producer=PRODUCER)
    with pytest.raises(PermissionError, match="no train_gate row"):
        g.require_train_visible("another-dataset", "v1.0", "published")


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------

@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("KE_TRAIN_GATE_DB", str(tmp_path / "gate.sqlite"))
    monkeypatch.setenv("KE_API_TOKEN", "test-token")
    from fastapi.testclient import TestClient

    from ke import train_gate_api as A
    from ke.api import app

    A.reset_gate()
    client = TestClient(app)
    yield client, A.get_gate()
    A.reset_gate()


def test_api_get_and_post_roundtrip(api):
    client, store = api
    h = {"Authorization": "Bearer test-token"}
    assert client.get("/api/v1/knowledge/train-gate").json()["count"] == 0

    r = client.post("/api/v1/knowledge/train-gate", headers=h, json={
        "dataset_id": DS, "version": VER, "to_level": "none", "producer": PRODUCER})
    assert r.status_code == 200 and r.json()["item"]["review_level"] == "none"

    r = client.post("/api/v1/knowledge/train-gate", headers=h, json={
        "dataset_id": DS, "version": VER, "to_level": "reviewed",
        "reviewer": "rev-zhang", "evidence_chain": EVIDENCE, "actor": "rev-zhang"})
    assert r.status_code == 200
    item = r.json()["item"]
    assert item["review_level"] == "reviewed" and item["train_visible"] is True
    assert item["admitted_at"]

    listing = client.get(f"/api/v1/knowledge/train-gate?dataset_id={DS}").json()
    assert listing["items"][0]["review_level"] == "reviewed"
    assert listing["counts"]["reviewed"] == 1
    assert listing["alerts"] == []
    assert client.get("/api/v1/knowledge/train-gate/audit").json()["count"] == 2


def test_api_write_requires_token(api):
    client, _ = api
    r = client.post("/api/v1/knowledge/train-gate", json={
        "dataset_id": DS, "version": VER, "to_level": "none"})
    assert r.status_code == 401
    r = client.post("/api/v1/knowledge/train-gate",
                    headers={"Authorization": "Bearer wrong"}, json={
                        "dataset_id": DS, "version": VER, "to_level": "none"})
    assert r.status_code == 401


def test_api_write_disabled_without_token(api, monkeypatch):
    client, _ = api
    monkeypatch.delenv("KE_API_TOKEN")
    r = client.post("/api/v1/knowledge/train-gate", json={
        "dataset_id": DS, "version": VER, "to_level": "none"})
    assert r.status_code == 503


def test_api_rejects_self_review_and_bad_level(api):
    client, _ = api
    h = {"Authorization": "Bearer test-token"}
    client.post("/api/v1/knowledge/train-gate", headers=h, json={
        "dataset_id": DS, "version": VER, "to_level": "none", "producer": PRODUCER})
    r = client.post("/api/v1/knowledge/train-gate", headers=h, json={
        "dataset_id": DS, "version": VER, "to_level": "reviewed",
        "reviewer": PRODUCER, "evidence_chain": EVIDENCE})
    assert r.status_code == 422 and "self-review" in r.json()["detail"]
    r = client.post("/api/v1/knowledge/train-gate", headers=h, json={
        "dataset_id": DS, "version": VER, "to_level": "blessed", "reviewer": "x"})
    assert r.status_code == 422
    assert set(client.get("/api/v1/knowledge/train-gate").json()["levels"]) == set(LEVELS)


def test_api_held_out_endpoint_lists_at_least_15_cases(api):
    client, _ = api
    body = client.get("/api/v1/knowledge/held-out").json()
    assert body["case_count"] >= 15
    assert len(body["cases"]) == body["case_count"]


# ---------------------------------------------------------------------------
# dataset download endpoint: 403 before review
# ---------------------------------------------------------------------------

def _get(port: int, path: str) -> tuple[int, str]:
    conn = HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request("GET", path)
    resp = conn.getresponse()
    body = resp.read().decode("utf-8")
    conn.close()
    return resp.status, body


def _free_port() -> int:
    import socket

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture()
def gated_server(tmp_path):
    from ke.dataset_builder import build_dataset
    from ke.dataset_server import make_server
    from ke.datasets import DatasetStore

    db = tmp_path / "ds.sqlite"
    store = DatasetStore(db)
    gate = TrainGateStore(conn=store.conn)
    store.attach_gate(gate)
    rows = [{"id": "r1", "text": "sample", "case_id": "SIM-RES-KCS-FR020"},
            {"id": "r2", "text": "leak", "case_id": "HO-RES-004"}]
    built = build_dataset(store, DS, VER, rows, status="draft", producer=PRODUCER, gate=gate)
    port = _free_port()
    server = make_server(str(db), port, "127.0.0.1", gate_enabled=True)
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    yield port, store, gate, built
    server.shutdown()
    server.server_close()


def test_download_403_when_level_none(gated_server):
    port, store, gate, _built = gated_server
    status, body = _get(port, f"/datasets/{DS}/{VER}/download")
    assert status == 403 and "level 'none'" in body
    status, _ = _get(port, f"/datasets/{DS}/{VER}/download?include=reviewed")
    assert status == 403
    # ?include=all 旧泄漏口在训练侧永久关闭
    status, body = _get(port, f"/datasets/{DS}/{VER}/download?include=all")
    assert status == 403 and "never exposed" in body


def test_download_200_after_review_with_header(gated_server):
    port, store, gate, _ = gated_server
    gate.transition(DS, VER, "reviewed", reviewer="rev-zhang", evidence_chain=EVIDENCE,
                    actor="rev-zhang")
    store.promote(DS, VER, "reviewed")
    status, body = _get(port, f"/datasets/{DS}/{VER}/download?include=reviewed")
    assert status == 200
    assert "HO-RES-004" not in body  # held-out 行在入库时已排除
    assert json.loads(body.strip().splitlines()[0])["id"] == "r1"


def test_diff_endpoint_is_gated_too(gated_server):
    """增量端点不能成为绕过 download 闸门的旁路。"""
    port, store, gate, _ = gated_server
    status, _ = _get(port, f"/datasets/{DS}/{VER}/diff?since={VER}")
    assert status == 403
    gate.transition(DS, VER, "reviewed", reviewer="rev-zhang", evidence_chain=EVIDENCE,
                    actor="rev-zhang")
    store.promote(DS, VER, "reviewed")
    with pytest.raises(PermissionError):
        store.diff(DS, VER, since=VER, include="published")
    assert store.diff(DS, VER, since=VER, include="reviewed") == []


def test_store_enforces_gate_below_http_layer(gated_server):
    _port, store, _gate, _ = gated_server
    with pytest.raises(PermissionError):
        store.download_rows_jsonl(DS, VER, include="published")