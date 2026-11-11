#!/usr/bin/env python3
"""kb_consume_audit —— KB 消费现状审计（m15181 / 锚点 KBM-CONSUME-W1）

零手抄纪律：本脚本是文档里全部数字的唯一来源。每个输出块都带 SQL 原文与本机实测
探针结果，报告/文档只许引用本脚本产出的 JSON（可 SQL 溯源）。

产出（artifacts/kb_consumption/）：
  inventory.json    knowledge_base 31 行逐条指标（ktype/domain/长度/注入次数/引用次数）
  injections.json   knowledge_injections 注入台账逐条
  citations.json    cited_count>0 的正例 + 任务 result 文本里提及 cited_kb 的负例原文
  exposure.json     暴露度：每条 KB 卡创建后同域任务数（引用率的分母）
  access_probe.json 检索面可达性实测（psql 各角色 + 4 个 HTTP 端点）
  staleness.json    新鲜度：卡 cited 后同域是否有推翻性新证据（verdict/negative 条数）

用法：
  python3 scripts/kb_consume_audit.py [--out artifacts/kb_consumption]
环境：
  TP_PG_DSN   psql 连接参数（默认 -U postgres -d tensorplatform -h /var/run/postgresql）
"""
import argparse
import json
import os
import pathlib
import subprocess
import urllib.error
import urllib.request

PSQL_BASE = os.environ.get(
    "TP_PG_DSN", "-U postgres -d tensorplatform -h /var/run/postgresql"
).split()


def psql(sql, dsn=None):
    """跑一条 SQL，返回 [ [col,...], ... ]；失败抛 RuntimeError（带 stderr）。"""
    cmd = ["psql"] + (dsn or PSQL_BASE) + ["-tA", "-F", "\x1f", "-c", sql]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"psql failed: {r.stderr.strip()[:300]}")
    rows = []
    for line in r.stdout.splitlines():
        rows.append(line.split("\x1f"))
    return rows


def q(sql):
    """带 SQL 溯源的单查询包。"""
    rows = psql(sql)
    return {"sql": sql, "rows": rows, "n": len(rows)}


def inventory():
    sql = ("SELECT id, kb_key, ktype, domain, title, length(content), status, source, "
           "injected_count, cited_count, coalesce(last_cited_at,''), created_at::text "
           "FROM knowledge_base ORDER BY id")
    rows = psql(sql)
    cols = ["id", "kb_key", "ktype", "domain", "title", "content_chars", "status",
            "source", "injected_count", "cited_count", "last_cited_at", "created_at"]
    items = [dict(zip(cols, r)) for r in rows]
    for it in items:
        it["id"] = int(it["id"])
        it["content_chars"] = int(it["content_chars"])
        it["injected_count"] = int(it["injected_count"])
        it["cited_count"] = int(it["cited_count"])
    by_type = {}
    for it in items:
        b = by_type.setdefault(it["ktype"], {"n": 0, "chars": [], "injected": 0, "cited": 0})
        b["n"] += 1
        b["chars"].append(it["content_chars"])
        b["injected"] += it["injected_count"]
        b["cited"] += it["cited_count"]
    for k, b in by_type.items():
        cs = sorted(b["chars"])
        b["chars_min"] = cs[0]
        b["chars_median"] = cs[len(cs) // 2]
        b["chars_max"] = cs[-1]
        del b["chars"]
    domains = {}
    for it in items:
        domains[it["domain"]] = domains.get(it["domain"], 0) + 1
    return {
        "total": len(items),
        "total_injected": sum(i["injected_count"] for i in items),
        "total_cited": sum(i["cited_count"] for i in items),
        "cited_rows": [i["kb_key"] for i in items if i["cited_count"] > 0],
        "injected_rows": [i["kb_key"] for i in items if i["injected_count"] > 0],
        "by_ktype": by_type,
        "by_domain": domains,
        "items": items,
        "sql": sql,
    }


def injections():
    sql = ("SELECT injection_id, coalesce(mission_id::text,''), kb_key, coalesce(kb_domain,''), "
           "coalesce(consumer,''), source, coalesce(match_score::text,''), "
           "coalesce(match_terms,''), injected_at, coalesce(cited_at,''), citation_count, "
           "coalesce(citation_ref,'') FROM knowledge_injections ORDER BY injected_at")
    if not psql("SELECT to_regclass('knowledge_injections') IS NOT NULL")[0][0] == "t":
        return {"sql": sql, "rows": [], "n": 0, "note": "table absent"}
    rows = psql(sql)
    cols = ["injection_id", "mission_id", "kb_key", "kb_domain", "consumer", "source",
            "match_score", "match_terms", "injected_at", "cited_at", "citation_count",
            "citation_ref"]
    items = [dict(zip(cols, r)) for r in rows]
    missions = sorted({i["mission_id"] for i in items if i["mission_id"]})
    terms = [t for i in items for t in json.loads(i["match_terms"] or "[]")]
    return {
        "n": len(items),
        "distinct_missions": missions,
        "distinct_kb_keys": sorted({i["kb_key"] for i in items}),
        "cited": sum(1 for i in items if i["cited_at"]),
        "match_score_range": [min((float(i["match_score"]) for i in items if i["match_score"]), default=None),
                              max((float(i["match_score"]) for i in items if i["match_score"]), default=None)],
        "match_terms": terms,
        "items": items,
        "sql": sql,
    }


def citations():
    """正例（计数器>0）+ 负例（任务 result 文本自报 cited_kb 的原话）。"""
    pos_sql = ("SELECT kb_key, cited_count, coalesce(last_cited_at,'') FROM knowledge_base "
               "WHERE cited_count>0 ORDER BY id")
    neg_sql = ("SELECT id, repo, status, substring(result::text from '.{200}cited_kb.{160}') "
               "FROM tensor_dev_missions WHERE result::text LIKE '%cited_kb%' ORDER BY id")
    mention_sql = "SELECT count(*) FROM tensor_dev_missions WHERE result::text LIKE '%cited_kb%'"
    total_sql = "SELECT count(*) FROM tensor_dev_missions"
    return {
        "positive": {"sql": pos_sql, "rows": psql(pos_sql)},
        "negative_mentions": {"sql": neg_sql, "rows": psql(neg_sql)},
        "mention_missions": int(psql(mention_sql)[0][0]),
        "all_missions": int(psql(total_sql)[0][0]),
        "mention_sql": mention_sql,
        "total_sql": total_sql,
    }


def exposure():
    """暴露度：KB 卡创建后，同域任务数（分母）；同域=repo 名与 card.domain 完全相等。
    另统计『开工三查查询①可达的卡』数量：ktype='capability' AND domain=<repo>。"""
    sql = """
SELECT kb.kb_key, kb.ktype, kb.domain, kb.created_at::date::text,
       (SELECT count(*) FROM tensor_dev_missions m
         WHERE m.repo = kb.domain AND m.created_at >= kb.created_at) AS missions_after,
       (SELECT count(*) FROM tensor_dev_missions m
         WHERE m.repo = kb.domain AND m.created_at >= kb.created_at
           AND m.result::text LIKE '%'||kb.kb_key||'%') AS missions_mentioning
  FROM knowledge_base kb ORDER BY kb.id
"""
    rows = psql(sql)
    cols = ["kb_key", "ktype", "domain", "created", "missions_after", "missions_mentioning"]
    items = [dict(zip(cols, r)) for r in rows]
    for i in items:
        i["missions_after"] = int(i["missions_after"])
        i["missions_mentioning"] = int(i["missions_mentioning"])
    repo_names = [r[0] for r in psql(
        "SELECT DISTINCT repo FROM tensor_dev_missions WHERE repo IS NOT NULL ORDER BY 1")]
    reach_sql = ("SELECT domain, count(*) FROM knowledge_base "
                 "WHERE ktype='capability' AND domain = ANY(%s) GROUP BY domain")
    arr = "{" + ",".join('"%s"' % r for r in repo_names) + "}"
    reach = psql(reach_sql % ("'" + arr + "'"))
    unmapped = sorted({i["domain"] for i in items} - set(repo_names))
    return {
        "items": items,
        "total_missions_after_card": sum(i["missions_after"] for i in items),
        "total_missions_mentioning_key": sum(i["missions_mentioning"] for i in items),
        "domains_not_a_repo": unmapped,
        "n_domains_not_a_repo": len(unmapped),
        "capability_reachable_by_repo_domain": {d: int(n) for d, n in reach},
        "repo_vocabulary": repo_names,
        "sql": sql,
        "reach_sql": reach_sql % "'" + arr + "'",
    }


def _http(path, token=None):
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
    req = urllib.request.Request(base + path)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = json.loads(r.read() or b"{}")
        return {"path": path, "http": 200, "body": body}
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read() or b"{}")
        except Exception:
            body = {}
        return {"path": path, "http": e.code, "body": body}
    except Exception as e:  # 连接拒绝等
        return {"path": path, "http": None, "error": f"{type(e).__name__}: {e}"}


def _login():
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (u and p):
        return None
    body = json.dumps({"username": u, "password": p}).encode()
    req = urllib.request.Request(base + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read())
        return d.get("access_token") or d.get("token")
    except Exception:
        return None


def access_probe():
    """检索面可达性：四个角色 psql 读 knowledge_base + 四个 HTTP 端点实测。"""
    roles = {}
    for role in ("root", "kb", "postgres", "ship", "foundation"):
        dsn = f"-h /var/run/postgresql -U {role} -d tensorplatform".split()
        try:
            rows = psql("SELECT count(*) FROM knowledge_base", dsn=dsn)
            roles[role] = {"ok": True, "count": int(rows[0][0])}
        except Exception as e:
            roles[role] = {"ok": False, "error": str(e)[:160]}
    tok = _login()
    http = [_http(p, tok) for p in (
        "/knowledge/stats",
        "/knowledge/search?q=ITTC",
        "/tensor/knowledge/status",
        "/tensor/knowledge/search?q=ITTC",
        "/tensor/knowledge/assets",
    )]
    return {"psql_roles": roles, "http": http, "auth_ok": bool(tok)}


def staleness():
    """新鲜度面：卡被引用后，同域后续是否出现推翻性证据（负知识/gate 判决）。"""
    sql = """
SELECT kb.kb_key, kb.domain,
       (SELECT count(*) FROM negative_knowledge_ledger n
         WHERE n.registered_at >= kb.created_at
           AND (n.keywords ILIKE '%'||kb.domain||'%' OR n.domain_tags ILIKE '%'||kb.domain||'%'))
  FROM knowledge_base kb ORDER BY kb.id
"""
    neg_total = "SELECT count(*) FROM negative_knowledge_ledger"
    return {"items": psql(sql), "sql": sql, "neg_total": psql(neg_total)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/kb_consumption")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    blocks = {
        "inventory": inventory(),
        "injections": injections(),
        "citations": citations(),
        "exposure": exposure(),
        "access_probe": access_probe(),
        "staleness": staleness(),
    }
    (out / "audit.json").write_text(json.dumps(
        {"schema": "kb-consumption-audit/1", "blocks": blocks},
        ensure_ascii=False, indent=1))
    # 摘要（文档直接引用这一块）
    inv = blocks["inventory"]
    summary = {
        "schema": "kb-consumption-audit/1",
        "kb_total": inv["total"],
        "kb_by_ktype": {k: v["n"] for k, v in inv["by_ktype"].items()},
        "injected_total": inv["total_injected"],
        "cited_total": inv["total_cited"],
        "injection_rows": blocks["injections"]["n"],
        "injection_missions": blocks["injections"]["distinct_missions"],
        "missions_mentioning_cited_kb": blocks["citations"]["mention_missions"],
        "missions_total": blocks["citations"]["all_missions"],
        "embedded_citation_rate": (round(inv["total_cited"] / max(
            blocks["exposure"]["total_missions_after_card"], 1), 4)),
        "exposure_total_missions_after_card": blocks["exposure"]["total_missions_after_card"],
        "domains_not_a_repo": blocks["exposure"]["domains_not_a_repo"],
        "psql_roles_blocked": [r for r, v in blocks["access_probe"]["psql_roles"].items()
                               if not v["ok"]],
        "http_probe": [{"path": h["path"], "http": h.get("http"),
                        "reason": h.get("body", {}).get("reason")}
                       for h in blocks["access_probe"]["http"]],
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()