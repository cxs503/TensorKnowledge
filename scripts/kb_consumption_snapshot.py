#!/usr/bin/env python3
"""kb_consumption_snapshot —— KB 消费计量周期快照（m15181 / KBM-CONSUME-W1 ④）

纯 SQL 零 LLM，可随 chronicle 六源钟同拍：payload schema = kb-consumption/1。
落两处：artifacts/kb_consumption/snapshots.jsonl（append + sha256 自校验）+ 表 kb_consumption_snapshots。

告警语义（写进 payload["alerts"]，机制化不依赖人看）：
  A1 access_ok=false            → 读面不可达，KB 处于设计失效态，cited 统计不可信
  A2 injected_7d==0 且同域任务>10 → 注入回路断
  A3 cited_total==0 且 injected_total>0 → 内容/格式问题（进第 2 轮设计）

用法：
  python3 scripts/kb_consumption_snapshot.py            # 写文件 + 写表 + 打印摘要
  python3 scripts/kb_consumption_snapshot.py --print    # 只打印 payload（chronicle 内联用）
  python3 scripts/kb_consumption_snapshot.py --no-db    # 不写 Postgres（离线可跑）
"""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "kb_consumption"
PSQL = os.environ.get("TP_PG_DSN", "-U postgres -d tensorplatform -h /var/run/postgresql").split()


def psql(sql):
    r = subprocess.run(["psql"] + PSQL + ["-tA", "-F", "\x1f", "-c", sql],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:300])
    return [line.split("\x1f") for line in r.stdout.splitlines()]


def one(sql, default=None):
    try:
        rows = psql(sql)
        return rows[0][0] if rows and rows[0] and rows[0][0] != "" else default
    except Exception:
        return default


def num(sql, default=0):
    v = one(sql)
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def build_payload():
    """六块指标；任何一块查询失败都不抛（降级为 null 并进 alerts/skipped）。"""
    skipped = []
    payload = {"schema": "kb-consumption/1", "taken_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    def guard(name, fn, default=None):
        try:
            return fn()
        except Exception as e:  # 表缺失/权限拒绝都降级
            skipped.append({"block": name, "error": str(e)[:200]})
            return default

    payload["kb_total"] = guard("kb_total", lambda: num("SELECT count(*) FROM knowledge_base"))
    payload["injected_total"] = guard(
        "injected_total", lambda: num("SELECT coalesce(sum(injected_count),0) FROM knowledge_base"))
    payload["cited_total"] = guard(
        "cited_total", lambda: num("SELECT coalesce(sum(cited_count),0) FROM knowledge_base"))
    payload["cited_rows"] = guard("cited_rows", lambda: [
        {"kb_key": r[0], "cited_count": int(r[1]), "last_cited_at": r[2]}
        for r in psql("SELECT kb_key, cited_count, coalesce(last_cited_at,'') "
                      "FROM knowledge_base WHERE cited_count>0 ORDER BY cited_count DESC")], [])
    payload["by_ktype"] = guard("by_ktype", lambda: {
        r[0]: {"n": int(r[1]), "injected": int(r[2]), "cited": int(r[3])}
        for r in psql("SELECT ktype, count(*), coalesce(sum(injected_count),0), "
                      "coalesce(sum(cited_count),0) FROM knowledge_base GROUP BY ktype ORDER BY 1")}, {})
    payload["by_domain"] = guard("by_domain", lambda: {
        r[0]: int(r[1]) for r in psql(
            "SELECT domain, count(*) FROM knowledge_base GROUP BY domain ORDER BY 2 DESC")}, {})

    payload["injection_rows"] = guard(
        "injection_rows",
        lambda: num("SELECT count(*) FROM knowledge_injections"), 0)
    payload["injected_7d"] = guard(
        "injected_7d",
        lambda: num("SELECT count(*) FROM knowledge_injections "
                    "WHERE injected_at::timestamptz > now()-interval '7 days'"), 0)
    payload["injection_missions"] = guard("injection_missions", lambda: [
        r[0] for r in psql("SELECT DISTINCT mission_id::text FROM knowledge_injections "
                           "WHERE mission_id IS NOT NULL")], [])

    # 暴露度分母：卡创建后同域（repo 名 == domain）任务数
    payload["exposure_denominator"] = guard("exposure", lambda: num(
        "SELECT count(*) FROM tensor_dev_missions m JOIN knowledge_base kb ON m.repo = kb.domain "
        "WHERE m.created_at >= kb.created_at"))
    payload["missions_total"] = guard(
        "missions_total", lambda: num("SELECT count(*) FROM tensor_dev_missions"))
    payload["missions_mentioning_cited_kb"] = guard(
        "missions_mentioning", lambda: num(
            "SELECT count(*) FROM tensor_dev_missions WHERE result::text LIKE '%cited_kb%'"))
    # 暴露高但零引用（下一轮该先改哪张卡）
    payload["unretrieved_top"] = guard("unretrieved_top", lambda: [
        {"kb_key": r[0], "ktype": r[1], "domain": r[2], "exposure": int(r[3])}
        for r in psql("SELECT kb.kb_key, kb.ktype, kb.domain, count(m.id) AS e "
                      "FROM knowledge_base kb LEFT JOIN tensor_dev_missions m "
                      "ON m.repo = kb.domain AND m.created_at >= kb.created_at "
                      "WHERE kb.cited_count = 0 GROUP BY 1,2,3 ORDER BY e DESC, 1 LIMIT 5")], [])

    exp = payload.get("exposure_denominator") or 0
    cited = payload.get("cited_total") or 0
    payload["citation_rate"] = round(cited / exp, 4) if exp else None
    payload["access_ok"] = bool(payload.get("kb_total"))
    payload["alerts"] = []
    if not payload["access_ok"]:
        payload["alerts"].append("A1_READ_PATH_UNREACHABLE")
    if payload.get("injected_7d") == 0 and exp > 10:
        payload["alerts"].append("A2_INJECTION_LOOP_DOWN")
    if cited == 0 and (payload.get("injected_total") or 0) > 0:
        payload["alerts"].append("A3_CITED_ZERO_WITH_INJECTIONS")
    payload["skipped"] = skipped
    return payload


def write_db(payload):
    psql("CREATE TABLE IF NOT EXISTS kb_consumption_snapshots ("
         "id bigserial PRIMARY KEY, taken_at timestamptz NOT NULL, "
         "kb_total int, injected_total int, cited_total int, exposure int, "
         "citation_rate real, alerts text[], payload jsonb, payload_sha256 text NOT NULL)")
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    sha = hashlib.sha256(body.encode()).hexdigest()
    alerts = "{" + ",".join('"%s"' % a for a in payload["alerts"]) + "}"
    payload_js = body.replace("'", "''")
    psql("INSERT INTO kb_consumption_snapshots "
         "(taken_at, kb_total, injected_total, cited_total, exposure, citation_rate, alerts, payload, payload_sha256) "
         f"VALUES (now(), {payload.get('kb_total') or 'NULL'}, {payload.get('injected_total') or 0}, "
         f"{payload.get('cited_total') or 0}, {payload.get('exposure_denominator') or 0}, "
         f"{(payload.get('citation_rate') if payload.get('citation_rate') is not None else 'NULL')}, "
         f"'{alerts}', '{payload_js}', '{sha}')")
    return sha


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true", dest="only_print")
    ap.add_argument("--no-db", action="store_true")
    a = ap.parse_args()
    payload = build_payload()
    if a.only_print:
        print(json.dumps(payload, ensure_ascii=False))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    sha = hashlib.sha256(body.encode()).hexdigest()
    payload["payload_sha256"] = sha
    with open(OUT / "snapshots.jsonl", "a") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    if not a.no_db:
        try:
            write_db(payload)
            payload["db_written"] = True
        except Exception as e:
            payload["db_written"] = False
            payload["db_error"] = str(e)[:160]
    print(json.dumps(payload, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()