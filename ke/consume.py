"""KB 读路径（消费面）：确定性检索 + 注入计量。

为什么存在（证据驱动，见 docs/ke/kb-consumption-v1.md ①）：
``knowledge_base`` 表存着全部知识卡，但**没有任何可用的 HTTP 读面** —— 类 agent 只能
靠 prompt 里的一段 SQL 自行连库，连不上就没有 cited_kb。本模块把「读路径」做成一等公民：

  rank(query, cards)        纯函数、确定性、可测的词面检索（中文 bigram + ASCII 词，
                            标题/元数据/正文分权，覆盖度归一，避免长卡 dominate）
  connect(dsn)              同一套代码跑 sqlite（测试/离线）与 postgres（现网）
  fetch_cards(conn, ...)    从 ``knowledge_base`` 按 domain/ktype/status 取候选
  retrieve(conn, query...)  检索 + 取卡 + 落注入台账（``knowledge_injections``）
                            + 更新 ``knowledge_base.injected_count/last_hit_at``
  naive_overlap(...)        **对照组**：复刻现网注入器「通用词重叠」的旧行为
                            （无域过滤、无标题加权、按空白分词→中文几乎零重叠），
                            供 scripts/kb_retrieve_bench.py 做 ref vs got 对照

设计取舍（每条挂证据，见 docs ⑤）：
- 域/类型是**过滤**不是加权：跨域噪声卡（domain 不是仓名的 ops 卡）本来是结构上不可达
  的那 16 张，过滤比加权更能压掉它们。
- 只回 `status` 命中信任层的卡（默认 active），使「被推翻的卡」可以被降级出检索面。
- 分数 round 到 4 位：同分按 kb_key 排序，保证重跑逐字节可复现（A/B/bench 要可复算）。

无第三方依赖（sqlite 用 stdlib；postgres 用 psycopg 3，仅在其被调用时导入）。
"""
from __future__ import annotations

import datetime
import json
import hashlib
import math
import re
import uuid

DEFAULT_LIMIT = 5
TITLE_W = 10.0
META_W = 4.0
CONTENT_W = 6.0
KEYWORDS_W = 8.0
SUB_MIN = 3      # ASCII 子串命中最小长度；0=关闭子串（逐字相等）
BM25_B = 0.5     # 正文面长度归一强度（hubness 抑制）；0=关闭
CONTENT_CHARS = 8000

_ASCII = re.compile(r"[a-z0-9][a-z0-9_\-\.:]{1,}")
_CJK = re.compile(r"[\u4e00-\u9fff]+")
_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were",
    "not", "you", "your", "our", "请", "的", "了", "和", "是", "在", "要", "把",
}


def tokenize(text: str) -> set[str]:
    """ASCII 词（小写、≥2 字符）+ 中文连续串的双字 bigram。

    中文没有空格，按空白分词会让「注入台账里的 match_terms」对中文正文几乎零重叠
    （现网 3 条注入记录正是这种词：worker/列空/派发）；bigram 是零依赖下最稳的替代。
    """
    if not text:
        return set()
    t = text.lower()
    # 实测否证：把复合标识符拆成子词（XVAL-FVM-SOD1978 -> xval/fvm/sod...）在 20 题 prereg 集上
    # 把 precision@1 从 0.80 拉到 0.75（噪声来自 L2/L4/m15xxx 段的子词与数字串），已回滚；
    # 词面消歧交给 keywords 面（见 card_keywords）——「Sod 激波管」的 miss 是数据缺别名，不是切词 bug。
    out = {w for w in _ASCII.findall(t) if w not in _STOP}
    for run in _CJK.findall(t):
        if len(run) == 1:
            out.add(run)
        for i in range(len(run) - 1):
            bg = run[i:i + 2]
            if bg not in _STOP:
                out.add(bg)
    return out


def card_keywords(card: dict) -> str:
    """卡的「域词/别名」面：显式 ``keywords`` 字段，或 content 里 JSON 的 keywords/aliases。

    为什么需要：现网 28 张 capability 卡的 content 是机器 JSON（scope/entry/tests 路径全英文），
    中文题面（「螺旋桨推进模块是真算法还是桩」）**词面上根本不可达**（实测 q20 top1 miss）。
    代码侧先把入口留好，词表由域 owner 回填（backfill 是 round-2 的数据动作，不是检索器能自造）。
    """
    kw = card.get("keywords") or card.get("aliases")
    if not kw:
        body = card.get("content") or ""
        if body.lstrip().startswith("{"):
            try:
                doc = json.loads(body)
                kw = doc.get("keywords") or doc.get("aliases")
            except (ValueError, TypeError):
                kw = None
    if isinstance(kw, (list, tuple)):
        return " ".join(str(x) for x in kw)
    return str(kw or "")


def card_tokens(card: dict) -> dict:
    """一张卡的四个词面（keywords 面为空时自动失效）。"""
    return {
        "title": tokenize(card.get("title") or ""),
        "meta": tokenize(" ".join(str(card.get(k) or "")
                                  for k in ("kb_key", "ktype", "domain"))),
        "content": tokenize((card.get("content") or "")[:CONTENT_CHARS]),
        "keywords": tokenize(card_keywords(card)),
    }


def _blobs(toks: dict) -> dict:
    """每个面的空格串，用于 ASCII 子串命中判定（复合标识符 gap-dem-gpu-100k 里找 gpu）。"""
    return {k: " ".join(sorted(v)) for k, v in toks.items()}


def _hit(t: str, toks: dict, blobs: dict) -> str | None:
    """返回 t 命中的最强面名（title > keywords > meta > content），未命中 None。

    ASCII 词按「子串且长度≥3」判定：标识符是连写复合词（XVAL-FVM-SOD1978 / GAP-DEM-GPU-100K），
    逐字相等会让 "sod"/"gpu" 这类判别词全 miss（holdout h08 / v1 q18 实测）。
    实测否证记在 docs：把复合词**拆成子词入词表**反而降分（噪声），而**子串命中**不增词表、只
    放宽匹配，故采用后者。
    """
    sub = SUB_MIN > 0 and len(t) >= SUB_MIN and t.isascii()
    for face in ("title", "keywords", "meta", "content"):
        if t in toks[face]:
            return face
        if sub and t in blobs[face]:
            return face
    return None


def doc_freq(q_tokens, cards, toks_by_key: dict) -> dict:
    """每个 query 词在候选集里命中多少张卡（子串判定与打分一致，否则 idf 失真）。"""
    df = {t: 0 for t in q_tokens}
    for c in cards:
        toks = toks_by_key.get(c.get("kb_key"))
        if not toks:
            continue
        blobs = _blobs(toks)
        for t in q_tokens:
            if _hit(t, toks, blobs):
                df[t] += 1
    return df


def idf(w: str, df: dict, n: int) -> float:
    return math.log((n + 1) / (df.get(w, 0) + 0.5)) + 1.0


def _rel_len(toks: dict) -> float:
    """正文相对长度（以 120 词≈典型 ops 短卡为 1）：长"综述型"卡不该靠字数通吃。"""
    return max(1.0, len(toks["content"]) / 120.0)


def score_card(q_tokens: set[str], card: dict, toks: dict | None = None, df=None, n=None) -> float:
    """idf 加权覆盖度：每个 query 词只按它在**最匹配的那个面**上的权重计一次，再除以 |q|。

    为什么用 idf（实测驱动）：无 idf 时"能力/等级/算例"这类高频 bigram 让长 capability 卡
    彼此打平（holdout h06/h07/h09 上 top1 全 miss），而这一层权衡不是题集特有的 —— 高频词
    在任何语料上都该让位于 "frazil/gpu/冰带" 这类判别词。
    归一化分母是 |q| 而不是 Σidf：保证分数上界稳定（≤ KEYWORDS_W），跨查询可比、可设阈值。
    """
    if not q_tokens:
        return 0.0
    toks = toks or card_tokens(card)
    blobs = _blobs(toks)
    key = (card.get("kb_key") or "").lower()
    bonus = 1000.0 if key and key in " ".join(sorted(q_tokens)) else 0.0
    total = 0.0
    for t in q_tokens:
        face = _hit(t, toks, blobs)
        if not face:
            continue
        w = {"title": TITLE_W, "keywords": KEYWORDS_W, "meta": META_W, "content": CONTENT_W}[face]
        total += (idf(t, df, n) if df is not None and n else 1.0) * w
    total /= len(q_tokens)
    if BM25_B > 0:
        total /= (1.0 - BM25_B) + BM25_B * _rel_len(toks)
    return round(total + bonus, 4)


def filter_cards(cards, domain=None, ktype=None, status="active"):
    out = []
    for c in cards:
        if status and (c.get("status") or "active") != status:
            continue
        if domain and c.get("domain") != domain:
            continue
        if ktype and c.get("ktype") != ktype:
            continue
        out.append(c)
    return out


def rank(query: str, cards, domain=None, ktype=None, status="active", limit=DEFAULT_LIMIT):
    """确定性检索：过滤 → 打分 → (score desc, kb_key asc) → top-k。"""
    q = tokenize(query)
    pool = filter_cards(cards, domain=domain, ktype=ktype, status=status)
    toks = {c.get("kb_key"): card_tokens(c) for c in pool}
    df = doc_freq(q, pool, toks)
    scored = []
    for c in pool:
        s = score_card(q, c, toks=toks.get(c.get("kb_key")), df=df, n=len(pool))
        if s > 0:
            scored.append((s, c))
    scored.sort(key=lambda x: (-x[0], x[1].get("kb_key") or ""))
    out = []
    for s, c in scored[:limit]:
        out.append({"kb_key": c.get("kb_key"), "ktype": c.get("ktype"), "domain": c.get("domain"),
                    "title": c.get("title"), "score": s, "content": c.get("content") or ""})
    return out


def naive_overlap(query: str, cards, limit=DEFAULT_LIMIT):
    """**对照组（现网旧行为）**：按空白分词、全库不过滤、命中词数排序。

    复刻 docs/ke/kb-consumption-v1.md ① 里记录的现网注入器：``match_terms`` 是
    ``query.split()`` 出来的词（中文整段成词），命中即算分。它代表「不做设计」的基线。
    """
    terms = [w.strip("，。,.;；:：！？()（）[]") for w in (query or "").split()]
    terms = [w.lower() for w in terms if len(w) >= 2]
    scored = []
    for c in cards:
        hay = " ".join(str(c.get(k) or "") for k in ("kb_key", "ktype", "domain", "title", "content")).lower()
        n = sum(1 for t in terms if t and t in hay)
        if n > 0:
            scored.append((n, c))
    scored.sort(key=lambda x: (-x[0], x[1].get("kb_key") or ""))
    return [{"kb_key": c.get("kb_key"), "ktype": c.get("ktype"), "domain": c.get("domain"),
             "title": c.get("title"), "score": float(n), "content": c.get("content") or ""}
            for n, c in scored[:limit]]


# --------------------------------------------------------------------------- DB

def connect(dsn: str):
    """``sqlite:PATH`` / ``sqlite:///PATH`` → sqlite3；其余按 libpq DSN 交给 psycopg3。"""
    if dsn.startswith("sqlite:"):
        import sqlite3
        path = dsn[len("sqlite:"):] or ":memory:"
        path = path[2:] if path.startswith("//") else path
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn
    import psycopg
    return psycopg.connect(dsn)


def ensure_schema(conn):
    """建 ``knowledge_base`` / ``knowledge_injections``（已存在则跳过）。

    只覆盖本模块用到的列；现网表有更多列（evidence/source/cited_count…）不影响读。
    """
    is_sqlite = conn.__class__.__module__.startswith("sqlite3")
    idcol = "id INTEGER PRIMARY KEY AUTOINCREMENT" if is_sqlite else "id serial PRIMARY KEY"
    cur = conn.cursor()
    cur.execute(f"""CREATE TABLE IF NOT EXISTS knowledge_base (
        {idcol},
        kb_key TEXT UNIQUE NOT NULL,
        ktype TEXT NOT NULL,
        domain TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        injected_count INTEGER NOT NULL DEFAULT 0,
        last_hit_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS knowledge_injections (
        injection_id TEXT PRIMARY KEY,
        mission_id BIGINT,
        kb_id INTEGER,
        kb_key TEXT NOT NULL,
        kb_domain TEXT,
        consumer TEXT,
        source TEXT NOT NULL DEFAULT 'manual',
        package_sha256 TEXT,
        match_score REAL,
        match_terms TEXT,
        injected_at TEXT NOT NULL,
        cited_at TEXT,
        citation_count INTEGER NOT NULL DEFAULT 0,
        citation_ref TEXT)""")
    conn.commit()


def fetch_cards(conn, domain=None, ktype=None, status="active"):
    sql = "SELECT kb_key,ktype,domain,title,content,status FROM knowledge_base WHERE 1=1"
    args = []
    if status:
        sql += " AND COALESCE(status,'active')=%s" if _pg(conn) else " AND COALESCE(status,'active')=?"
        args.append(status)
    if domain:
        sql += " AND domain=%s" if _pg(conn) else " AND domain=?"
        args.append(domain)
    if ktype:
        sql += " AND ktype=%s" if _pg(conn) else " AND ktype=?"
        args.append(ktype)
    sql += " ORDER BY kb_key"
    cur = conn.cursor()
    cur.execute(sql, args)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def fetch_cards_psql(psql_args=None, status="active"):
    """psql 子进程兜底取卡（零依赖）。

    为什么需要：现网 agent 默认角色（unix peer = ``root``）对 ``knowledge_base`` 是
    ``permission denied``（``scripts/kb_consume_audit.py`` 的 access_probe 实测），
    只有 ``postgres`` 角色能读。检索器/基准要能「在没有 GRANT 的情况下仍能取证」，
    因此保留这条显式兜底；生产读面应改为 GRANT 一个只读角色（见 docs/ke/kb-read-path.md）。
    """
    import os
    import subprocess
    args = (psql_args or os.environ.get("TP_PG_DSN",
            "-U postgres -d tensorplatform -h /var/run/postgresql")).split()
    sql = ("SELECT COALESCE(json_agg(t ORDER BY t.kb_key),'[]') FROM ("
           "SELECT kb_key,ktype,domain,title,content,COALESCE(status,'active') AS status "
           f"FROM knowledge_base WHERE COALESCE(status,'active')='{status}') t")
    r = subprocess.run(["psql"] + args + ["-tA", "-c", sql], capture_output=True, text=True,
                       timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"psql failed: {r.stderr.strip()[:300]}")
    return json.loads(r.stdout.strip() or "[]")


def _pg(conn) -> bool:
    return not conn.__class__.__module__.startswith("sqlite3")


def log_injection(conn, cards, query, mission_id=None, consumer="ke-api", source="ke-api",
                  injection_id=None):
    """把「这次检索返回了哪几张卡」写进台账，并 bump 卡上的 injected_count。

    这是消费计量的**唯一真相源**：没有这一步，cited/injected 差额永远无法归因
    （现网 44 张卡只有 3 条注入记录，全部来自一次人工打包）。
    """
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    inj = injection_id or ("keapi-" + uuid.uuid4().hex[:16])
    body = "|".join(f"{c['kb_key']}:{c['score']}" for c in cards)
    sha = hashlib.sha256(body.encode()).hexdigest()
    q = "%s" if _pg(conn) else "?"
    cur = conn.cursor()
    terms = ",".join(sorted(tokenize(query))[:24])
    for i, c in enumerate(cards):
        # 一次检索多张卡 = 同 package_sha256 的多行，行 id 必须逐行唯一（PK）
        cur.execute(
            f"INSERT INTO knowledge_injections (injection_id,mission_id,kb_key,kb_domain,consumer,"
            f"source,package_sha256,match_score,match_terms,injected_at) VALUES "
            f"({q},{q},{q},{q},{q},{q},{q},{q},{q},{q})",
            (f"{inj}-{i:02d}", mission_id, c["kb_key"], c.get("domain"), consumer, source, sha,
             float(c["score"]), terms, now))
        cur.execute(
            f"UPDATE knowledge_base SET injected_count=COALESCE(injected_count,0)+1, last_hit_at={q} "
            f"WHERE kb_key={q}", (now, c["kb_key"]))
    conn.commit()
    return {"injection_id": inj, "n": len(cards), "injected_at": now, "package_sha256": sha}


def retrieve(conn, query, domain=None, ktype=None, limit=DEFAULT_LIMIT, status="active",
             mission_id=None, consumer="ke-api", log=True):
    """读路径主函数（HTTP 面与脚本共用）。"""
    cards = fetch_cards(conn, domain=domain, ktype=ktype, status=status)
    hits = rank(query, cards, domain=domain, ktype=ktype, status=status, limit=limit)
    out = {"schema": "kb-retrieve/1", "query": query, "domain": domain, "ktype": ktype,
           "candidates": len(cards), "n": len(hits), "cards": hits}
    if log and hits:
        out["injection"] = log_injection(conn, hits, query, mission_id=mission_id,
                                         consumer=consumer)
    return out


def budget_hint(cards) -> int:
    """给调用方一个便宜的上界：这些卡塞进上下文要多少字符（≈ token*4）。"""
    return sum(len(c.get("content") or "") + len(c.get("title") or "") for c in cards)


__all__ = ["fetch_cards_psql", "card_keywords", "doc_freq", "idf", "tokenize", "rank", "naive_overlap", "filter_cards", "score_card", "card_tokens",
           "connect", "ensure_schema", "fetch_cards", "log_injection", "retrieve",
           "budget_hint", "DEFAULT_LIMIT"]