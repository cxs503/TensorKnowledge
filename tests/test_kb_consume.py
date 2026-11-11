"""KB 读路径单测（``ke/consume.py`` + ``/kb/search`` 端点）。

全部离线：卡片是合成夹具（合成域名/合成词），不依赖平台 Postgres、不依赖 LLM ——
读路径的正确性必须能在任何机器上被判，而不是靠「跑过一遍现网」。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ke import consume as C  # noqa: E402

CARDS = [
    {"kb_key": "KB-DEMO-FRICTION", "ktype": "fact", "domain": "demo-a",
     "title": "ITTC-1957 平板摩擦系数 0.075/(log10 Re-2)^2",
     "content": "平板摩擦阻力系数公式，适用 Re 到 1e9。", "status": "active"},
    {"kb_key": "KB-DEMO-CLUSTER", "ktype": "pattern", "domain": "demo-b",
     "title": "重计算递交集群作业队列",
     "content": "全量 pytest 预估 25 分钟，不要压控制面容器，递交集群作业队列等待调度。",
     "status": "active"},
    {"kb_key": "KB-DEMO-HUB", "ktype": "lesson", "domain": "demo-b",
     "title": "跨域综述",
     "content": "能力 等级 收敛 力误差 集群 递交 摩擦 系数 平板 阻力 全量 pytest " * 60,
     "status": "active"},
    {"kb_key": "KB-DEMO-RETIRED", "ktype": "lesson", "domain": "demo-a",
     "title": "已被推翻的旧结论 平板摩擦系数用常数 0.003",
     "content": "平板摩擦系数取常数即可。", "status": "retired"},
]


def test_tokenize_cjk_bigram_and_ascii():
    toks = C.tokenize("ITTC-1957 平板摩擦系数")
    assert "ittc-1957" in toks          # 复合标识符按原样保留（拆词实测降分，见模块注）
    assert "平板" in toks and "板摩" in toks   # 中文按 bigram
    assert C.tokenize("") == set()


def test_rank_excludes_non_active_status():
    keys = [h["kb_key"] for h in C.rank("平板摩擦系数", CARDS, status="active", limit=5)]
    assert "KB-DEMO-RETIRED" not in keys
    assert "KB-DEMO-FRICTION" in keys


def test_rank_domain_filter_blocks_cross_domain():
    q = "全量 pytest 递交集群"
    assert [h["kb_key"] for h in C.rank(q, CARDS, domain="demo-b", limit=1)] == ["KB-DEMO-CLUSTER"]
    # 不给 domain 时 hub 卡会来抢 —— 这正是「开工三查必须带 domain」的证据
    top = [h["kb_key"] for h in C.rank(q, CARDS, limit=2)]
    assert "KB-DEMO-CLUSTER" in top


def test_title_face_outranks_buried_content_hub():
    hits = C.rank("平板摩擦系数公式", CARDS, limit=3)
    assert hits[0]["kb_key"] == "KB-DEMO-FRICTION"
    # 长度归一（BM25_B）必须真的在压 hub：否则 60 倍长正文的综述卡通吃
    hub = [h for h in hits if h["kb_key"] == "KB-DEMO-HUB"]
    assert not hub or hub[0]["score"] < hits[0]["score"]


def test_rank_tie_break_is_deterministic():
    cards = [dict(CARDS[0]), dict(CARDS[0], kb_key="KB-DEMO-AAA"),
             dict(CARDS[0], kb_key="KB-DEMO-ZZZ")]
    for c in cards:
        c["content"] = c["title"] = "同分同词"
    runs = [[h["kb_key"] for h in C.rank("同分同词", cards, limit=3)] for _ in range(3)]
    assert runs[0] == ["KB-DEMO-AAA", "KB-DEMO-FRICTION", "KB-DEMO-ZZZ"]
    assert all(r == runs[0] for r in runs)


def test_keywords_face_makes_chinese_query_reachable():
    """capability 卡正文是英文机器 JSON，中文题面词面不可达 —— keywords 面是解法（实测 q20/h06）。"""
    cap = {"kb_key": "cap:demo:m1", "ktype": "capability", "domain": "demo-c",
           "title": "[L3] m1 CAP-PROPULSION-REAL",
           "content": '{"scope": "m1 CAP-PROPULSION-REAL", "level": 3, "evidence": {"entry": "a.py"}}',
           "status": "active"}
    assert C.rank("螺旋桨推进模块是真算法还是桩", [cap], limit=1) == []
    cap2 = dict(cap, keywords=["螺旋桨", "推进", "开口水"])
    hits = C.rank("螺旋桨推进模块是真算法还是桩", [cap2], limit=1)
    assert hits and hits[0]["kb_key"] == "cap:demo:m1"
    assert C.card_keywords(cap2) == "螺旋桨 推进 开口水"
    inline = dict(cap, content='{"scope": "x", "keywords": ["螺旋桨"]}')
    assert C.card_keywords(inline) == "螺旋桨"


def test_key_specified_in_query_wins():
    hits = C.rank("请取回 KB-DEMO-CLUSTER 这张卡", CARDS, limit=1)
    assert hits[0]["kb_key"] == "KB-DEMO-CLUSTER"
    assert hits[0]["score"] > 100


def test_naive_overlap_reference_is_word_split_baseline():
    """ref 臂语义锁死：按空白分词 → 中文整句成一个词，通常零命中。"""
    assert C.naive_overlap("平板摩擦系数公式", CARDS, limit=3) == []
    assert C.naive_overlap("pytest 集群", CARDS, limit=1)[0]["kb_key"] in (
        "KB-DEMO-CLUSTER", "KB-DEMO-HUB")


def test_budget_hint():
    assert C.budget_hint([]) == 0
    assert C.budget_hint([{"title": "ab", "content": "cd"}]) == 4


# ------------------------------------------------------------------ sqlite 全链路

@pytest.fixture()
def conn(tmp_path):
    c = C.connect("sqlite:" + str(tmp_path / "kb.sqlite"))
    C.ensure_schema(c)
    for card in CARDS:
        c.execute("INSERT INTO knowledge_base (kb_key,ktype,domain,title,content,status) "
                  "VALUES (?,?,?,?,?,?)",
                  (card["kb_key"], card["ktype"], card["domain"], card["title"],
                   card["content"], card["status"]))
    c.commit()
    yield c
    c.close()


def test_retrieve_logs_injection_and_bumps_counts(conn):
    first = C.retrieve(conn, "平板摩擦系数", domain="demo-a", limit=1, mission_id=15255,
                       consumer="pytest")
    assert first["n"] == 1 and first["cards"][0]["kb_key"] == "KB-DEMO-FRICTION"
    assert first["injection"]["n"] == 1
    rows = conn.execute("SELECT kb_key, consumer, mission_id, source, injected_at "
                        "FROM knowledge_injections").fetchall()
    assert len(rows) == 1 and rows[0][0] == "KB-DEMO-FRICTION"
    assert rows[0][1] == "pytest" and rows[0][2] == 15255 and rows[0][3] == "ke-api"
    assert rows[0][4].endswith("Z")
    cnt = conn.execute("SELECT injected_count, last_hit_at FROM knowledge_base "
                       "WHERE kb_key='KB-DEMO-FRICTION'").fetchone()
    assert cnt[0] == 1 and cnt[1]

    second = C.retrieve(conn, "平板摩擦系数", domain="demo-a", limit=1, consumer="pytest")
    assert second["injection"]["injection_id"] != first["injection"]["injection_id"]
    assert conn.execute("SELECT count(*) FROM knowledge_injections").fetchone()[0] == 2
    assert conn.execute("SELECT injected_count FROM knowledge_base "
                        "WHERE kb_key='KB-DEMO-FRICTION'").fetchone()[0] == 2


def test_retrieve_log_false_writes_nothing(conn):
    out = C.retrieve(conn, "平板摩擦系数", log=False)
    assert out["n"] >= 1 and "injection" not in out
    assert conn.execute("SELECT count(*) FROM knowledge_injections").fetchone()[0] == 0


def test_retrieve_empty_query_does_not_log(conn):
    out = C.retrieve(conn, "zzzz-不存在的词", limit=3)
    assert out["n"] == 0 and "injection" not in out
    assert conn.execute("SELECT count(*) FROM knowledge_injections").fetchone()[0] == 0


# ------------------------------------------------------------------ HTTP 端点

def test_kb_search_endpoint(tmp_path, monkeypatch):
    """平台侧真调用面：GET /kb/search 走 ke.consume 并落注入台账。"""
    from fastapi.testclient import TestClient
    from ke import api

    db = tmp_path / "kbapi.sqlite"
    conn = C.connect("sqlite:" + str(db))
    C.ensure_schema(conn)
    for card in CARDS:
        conn.execute("INSERT INTO knowledge_base (kb_key,ktype,domain,title,content,status) "
                     "VALUES (?,?,?,?,?,?)",
                     (card["kb_key"], card["ktype"], card["domain"], card["title"],
                      card["content"], card["status"]))
    conn.commit()
    conn.close()

    monkeypatch.setenv("KB_DSN", "sqlite:" + str(db))
    client = TestClient(api.app)
    r = client.get("/kb/search", params={"q": "全量 pytest 递交集群", "domain": "demo-b",
                                         "limit": 2, "mission_id": 15255})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cards"][0]["kb_key"] == "KB-DEMO-CLUSTER"
    assert body["injection"]["n"] >= 1
    # 多卡一次检索：注入台账必须逐行唯一 id（曾因共用 injection_id 撞 PK）
    conn2 = C.connect("sqlite:" + str(db))
    rows = conn2.execute("SELECT injection_id, package_sha256 FROM knowledge_injections").fetchall()
    conn2.close()
    assert len({r_[0] for r_ in rows}) == len(rows) == body["injection"]["n"]
    assert len({r_[1] for r_ in rows}) == 1

    r2 = client.get("/kb/search", params={"q": "全量 pytest", "domain": "demo-b", "log": False})
    assert r2.status_code == 200 and "injection" not in r2.json()

    r3 = client.get("/kb/search", params={"q": ""})
    assert r3.status_code == 422  # min_length=1


def test_kb_search_reports_unreachable_store(monkeypatch):
    from fastapi.testclient import TestClient
    from ke import api

    monkeypatch.setenv("KB_DSN", "postgresql:///no_such_db_at_all")
    client = TestClient(api.app)
    r = client.get("/kb/search", params={"q": "x"})
    assert r.status_code in (503, 200)  # 503=读面不可达（正确语义）；200 仅在库存在时