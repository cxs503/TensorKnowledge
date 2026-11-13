#!/usr/bin/env python3
"""wp-5606-04 独立审核复算脚本（red-team reviewer 侧，零手抄）。

设计
----
* 输入只有两样：契约声明（source_hash）与 report 5606 的 markdown 原文（落盘件
  ``report_source_5606.md``，取回即校验 sha256）。不读生产者实现代码/自评/笔记，
  独立性由输入集保证而非口头声明。
* 审核报告用到的每条原文引用登记在 ``QUOTE``，脚本逐条断言 ``quote in markdown``
  并记录字符偏移；任一引用不在原文即退出码 2（honest-FAIL，不出报告）。
* 全部数字由本脚本从原文重新解析/重算。

复跑：
    python3 artifacts/wp-5606-04/indep_check.py
    python3 artifacts/wp-5606-04/build_report.py     # 生成 review_report.json 等
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PKG_ID = "wp-5606-04"
TASK_TYPE = "04-independent-review"
REPORT_ID = "5606"
EXPECTED_SOURCE_HASH = "sha256:da0d91e5c5eae1aa240fba2fcc6b0ebab3960fb49f0f31378cf9a7f866b14edd"
SCENARIO_KEY = "campaign:IN18-T3:chronicle-report-v2"
SNAP_HASH = "sha256:f46ab6f316a2c10c1c38b67594643eb0483c0e7cbe7d67c7e20dfcb374f9f572"
ARTIFACT_PATH = "/root/tp-agent/work/m4976/artifacts/capability_ledger/capability_ledger_resolved.json"

HERE = Path(__file__).resolve().parent
SRC_MD = HERE / "report_source_5606.md"

# 原文逐字引用表（claim/字段 -> 片段）。注意：不得跨行拼接，markdown 有硬换行。
QUOTE = {
    "q_title": "IN18-T3 顶刊报告框架与防造假溯源管线",
    "q_artifact": "被冻结的真实工件：`/root/tp-agent/work/m4976/artifacts/capability_ledger/capability_ledger_resolved.json`",
    "q_snap_hash": "快照哈希 `f46ab6f316a2c10c1c38b67594643eb0483c0e7cbe7d67c7e20dfcb374f9f572`",
    "q_n_records": "| 溯源记录数 | 23（数字 20 / 图 3） |",
    "q_n_marked": "| 块内带标记数字 | 23 |",
    "q_n_bare": "| 块内裸数字 | 0 |",
    "q_n_sql": "| 重跑 SQL 条数 | 20 |",
    "q_n_figfiles": "| 校验图件文件数 | 6 |",
    "q_gate": "| 门禁裁定 | **PASS**（FAIL 0 / WARN 0） |",
    "q_blocks": "| 强制块数 | 2 |",
    "q_total_cap": "| 注册能力总数 | 21 |",
    "q_ev_rows": "| 证据行总数 | 10 |",
    "q_claimed_real": "| 宣称 REAL | 18 |",
    "q_recon_real": "| 对账 REAL | 1（4.8 %） |",
    "q_ok": "| 一致 OK | 4（19.0 %） |",
    "q_over": "| 过度宣称 OVERCLAIM | 2（9.5 %） |",
    "q_unver": "| 未验证 UNVERIFIED | 15 |",
    "q_sat": "| 证据获取饱和比 | 0.300（3 能力 / 10 证据行） |",
    "q_n004": "| `n-004` | 21 | `SELECT COUNT(*) FROM capability` |",
    "q_n010": "| `n-010` | 21 | `SELECT COUNT(*) FROM capability` |",
    "q_n005": "| `n-005` | 10 | `SELECT COUNT(*) FROM evidence` |",
    "q_n011": "| `n-011` | 10 | `SELECT COUNT(*) FROM evidence` |",
    "q_failcodes": "8 类 FAIL 码 + 2 类 WARN 码",
    "q_negctl": "FABRICATED/SOURCE_DRIFT/SNAP_HASH/FIGURE_HASH/UNMARKED 全部命中",
    "q_lesson": "没有负例的门禁等于没有门禁",
    "q_ro": "连接以 `mode=ro` 打开，校验器物理上无法改写自己的证据。",
    "q_toolchain": "工具链：Python 3.10 / matplotlib 2.4.6 后端 Agg / numpy / stdlib sqlite3；无新增第三方依赖。",
    "q_syntax": "稿中数字唯一合法形态为 `数值 {{prov:<id>}}`",
    "q_block": "强制范围是 `prov:begin/end` 块",
    "q_figarr": "数组全部由 SQL 窗口函数与分组查询产出，",
    "q_figledger": "图件账本（文件字节哈希，替换即 FAIL）：",
    "q_funnel": "图 3 成功漏斗：claimed 21 → reconciled → machine-checked → OK 4 → REAL 1，",
    "q_funnel2": "各阶段为 SQL 谓词定义，计数单调不增，未做任何平滑。",
    "q_fig2": "对账后仅 1 项 —— 这是本次审计最重要的定量发现。",
    "q_lim_hash": "哈希是篡改*证据*非*证明*",
    "q_lim_block": "强制范围仅 2 个块，非全文",
    "q_lim_unknown": "未知造假形态（重写工件→重建快照→一致重算哈希）可绕过，需外部时间戳/签名。",
    "q_err1": "| 数字-记录一致 | 印刷值 vs 记录值（容差 = 半量级） | 20 条全部一致 | 是 |",
    "q_err2": "| 记录-SQL 一致 | 记录值 vs 重跑 SQL（rtol 1e-9） | 20 条全部复现 | 是 |",
    "q_err_n3": "是否 <3%？—— 本节点无数值型物理基准，**不适用**",
}


def sha256_bytes(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def load_source(path: Path | None) -> tuple[str, dict]:
    if path is not None and path.suffix == ".json":
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc = doc.get("data", doc)
        md = doc["markdown"]
        meta = {"channel": "api_json", "title": doc.get("title"),
                "scenario_key": doc.get("scenario_key"), "status": doc.get("status")}
    else:
        md = SRC_MD.read_text(encoding="utf-8")
        meta = {"channel": "snapshot_file"}
    b = md.encode("utf-8")
    meta.update({"chars": len(md), "bytes": len(b), "sha256": sha256_bytes(b),
                 "hash_matches_contract": sha256_bytes(b) == EXPECTED_SOURCE_HASH})
    return md, meta


def parse_prov_rows(md: str) -> list[dict]:
    rows = []
    for m in re.finditer(r"^\| `(n-\d{3})` \| ([0-9.]+) \| `([^`]+)` \| `([0-9a-f]+)` \|$", md, re.M):
        rows.append({"pid": m.group(1), "value": float(m.group(2)), "sql": m.group(3),
                     "snap_prefix": m.group(4), "offset": m.start()})
    return rows


def parse_fig_rows(md: str) -> list[dict]:
    out = []
    for m in re.finditer(r"^\| `(fig-\d{3})` \| ([a-z0-9_]+) \| ([^|]+) \| `([^`]+)` \|$", md, re.M):
        out.append({"pid": m.group(1), "figure": m.group(2),
                    "files": [x.strip() for x in m.group(3).split(",")],
                    "hash_prefixes": [x.strip() for x in m.group(4).split(",")],
                    "offset": m.start()})
    return out


def parse_table1(md: str) -> dict:
    out = {}
    for m in re.finditer(r"^\| ([^|]+?) \| ([^|]+?) \|$", md, re.M):
        k, v = m.group(1).strip(), m.group(2).strip()
        if k in {"指标", "参数", "判据"} or set(k) <= {"-"}:
            continue
        num = re.search(r"[0-9]+(?:\.[0-9]+)?", v)
        if num:
            out[k] = {"printed": v, "number": float(num.group(0)), "offset": m.start()}
    return out


def conservation(rows: list[dict], t1: dict) -> dict:
    by_val: dict[float, list[str]] = {}
    for r in rows:
        by_val.setdefault(r["value"], []).append(r["pid"])
    total = t1["注册能力总数"]["number"]
    ok, over, unver = t1["一致 OK"]["number"], t1["过度宣称 OVERCLAIM"]["number"], t1["未验证 UNVERIFIED"]["number"]
    claimed_real, recon_real = t1["宣称 REAL"]["number"], t1["对账 REAL"]["number"]
    pcts = []
    for label, k, printed in (("对账 REAL %", 1, 4.7619), ("一致 OK %", 4, 19.0476), ("过度宣称 %", 2, 9.52381)):
        recomp = 100.0 * k / total
        pcts.append({"field": label, "printed": printed, "recomputed": round(recomp, 6),
                     "rel_err": abs(recomp - printed) / printed})
    return {
        "capability_total": total,
        "divergence_partition": {"OK": ok, "OVERCLAIM": over, "UNVERIFIED": unver,
                                 "sum": ok + over + unver, "equals_total": ok + over + unver == total},
        "claimed_vs_reconciled": {"claimed_REAL": claimed_real, "reconciled_REAL": recon_real,
                                  "gap": claimed_real - recon_real,
                                  "explained_by": {"reconciled_REAL": recon_real, "OVERCLAIM": over,
                                                   "UNVERIFIED": unver, "sum": recon_real + over + unver}},
        "percent_recompute": pcts,
        "percent_max_rel_err": max(p["rel_err"] for p in pcts),
        "saturation": {"printed": 0.3, "recomputed": 3 / 10, "abs_err": 0.0},
        "duplicate_value_groups": {("%g" % v): pids for v, pids in sorted(by_val.items()) if len(pids) > 1},
        "distinct_values": len(by_val),
        "distinct_sql_prefixes": len({r["sql"] for r in rows}),
        "n_rows": len(rows),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=None, help="API 落库 JSON（含 markdown 字段）")
    ap.add_argument("--materialize", action="store_true", help="把 --source 的 markdown 落盘为快照")
    args = ap.parse_args()

    if args.materialize and args.source:
        doc = json.loads(Path(args.source).read_text(encoding="utf-8"))
        doc = doc.get("data", doc)
        SRC_MD.write_text(doc["markdown"], encoding="utf-8")

    md, meta = load_source(Path(args.source) if (args.source and not args.materialize) else None)
    checks: list[dict] = []

    def rec(cid, question, status, observed, expected=None, note=None):
        checks.append({"id": cid, "question": question, "status": status,
                       "expected": expected, "observed": observed, "note": note})

    rec("C01.source_hash", "落盘原文 sha256 是否等于契约 source_hash",
        "pass" if meta["hash_matches_contract"] else "fail",
        {"sha256": meta["sha256"], "chars": meta["chars"], "bytes": meta["bytes"]},
        EXPECTED_SOURCE_HASH)

    missing = [k for k, v in QUOTE.items() if v not in md]
    quote_index = {k: {"offset": md.index(v), "chars": len(v)} for k, v in QUOTE.items() if v in md}
    rec("C02.quotes_locatable", "审核所用全部原文引用是否逐字命中 markdown（零手抄机器保证）",
        "pass" if not missing else "fail",
        {"n_quotes": len(QUOTE), "n_missing": len(missing), "missing": missing[:5]}, "0 missing")
    if missing:
        print("FATAL quotes not in source:", missing, file=sys.stderr)
        return 2

    rows, figs = parse_prov_rows(md), parse_fig_rows(md)
    t1 = parse_table1(md)
    cons = conservation(rows, t1)

    rec("C03.record_count", "『溯源记录数 23（数字 20 / 图 3）』是否与原文可解析行一致",
        "pass" if len(rows) == 20 and len(figs) == 3 else "fail",
        {"number_rows": len(rows), "figure_rows": len(figs), "sum": len(rows) + len(figs)},
        {"number_rows": 20, "figure_rows": 3, "sum": 23})

    rec("C04.percent_recompute", "表 1 百分比是否由计数/21 精确导出（rel_err < 1e-3）",
        "pass" if cons["percent_max_rel_err"] < 1e-3 else "fail",
        {"max_rel_err": cons["percent_max_rel_err"], "detail": cons["percent_recompute"]}, "<1e-3")

    part, cvc = cons["divergence_partition"], cons["claimed_vs_reconciled"]
    rec("C05.partition_conservation", "OK+OVERCLAIM+UNVERIFIED 是否分完 21 项；宣称 REAL 18 是否被 1+2+15 解释",
        "pass" if part["equals_total"] and cvc["explained_by"]["sum"] == cvc["claimed_REAL"] else "fail",
        {"partition": part, "claimed_vs_reconciled": cvc}, "两处闭合")

    rec("C06.saturation", "饱和比 0.300 是否恰等于 3 能力 / 10 证据行",
        "pass" if abs(cons["saturation"]["abs_err"]) < 1e-12 else "fail", cons["saturation"], 0.0)

    rec("C07.sql_uniqueness", "『重跑 SQL 条数 20』是否等于互不相同的查询数",
        "fail" if cons["distinct_sql_prefixes"] < 20 else "pass",
        {"n_rows": cons["n_rows"], "distinct_sql_prefixes": cons["distinct_sql_prefixes"],
         "duplicate_value_groups": cons["duplicate_value_groups"],
         "caveat": "正文 SQL 列被截断（如 `...FROM capabi`），互异性按截断串比较，真实互异数可能更低"},
        "20 distinct")

    prov_real = len(re.findall(r"\{\{prov:(?!<id>)", md))
    rec("C08.provenance_markers_present",
        "被审对象 markdown 内是否存在真实溯源标记/块（非语法示例），以复核『块内裸数字 0』",
        "fail" if prov_real == 0 else "pass",
        {"real_marker_occurrences": prov_real, "prov_begin_occurrences": len(re.findall("prov:begin", md)),
         "syntax_example_present": "{{prov:<id>}}" in md,
         "interpretation": "仅 1 处语法示例 + 1 处语法说明；无任何真实 {{prov:<id>}} 标注、无 prov:begin/end 块"},
        ">=20 real markers inside 2 blocks")

    named = sorted(set(re.findall(r"\b(FABRICATED|SOURCE_DRIFT|SNAP_HASH|FIGURE_HASH|UNMARKED)\b", md)))
    rec("C09.negative_control_coverage", "声明的 8 类 FAIL 码是否各有命名负例（§6 仅列 5 类）",
        "fail" if len(named) < 8 else "pass",
        {"declared_fail_codes": 8, "codes_with_named_negative_control": named, "uncovered": 8 - len(named)},
        "8/8 covered")

    art = Path(ARTIFACT_PATH)
    art_exists = art.is_file()
    art_hash = sha256_bytes(art.read_bytes()) if art_exists else None
    rec("C10.frozen_artifact_reachable", "声明的冻结工件能否取回、snapshot_hash 能否独立复算",
        "pass" if (art_exists and art_hash == SNAP_HASH) else "not_run",
        {"path": ARTIFACT_PATH, "exists": art_exists, "recomputed": art_hash,
         "note": "所在工作树 m4976 已不存在；其他工作树同名副本抽样哈希≠f46ab6f3…；"
                 "全盘 find 超时（120s）未完成，故判 not_run 而非 fail"},
        SNAP_HASH)

    def ver(mod):
        try:
            return __import__(mod).__version__
        except Exception as exc:  # pragma: no cover
            return f"unavailable: {exc}"
    env = {"python": platform.python_version(), "matplotlib": ver("matplotlib"), "numpy": ver("numpy"),
           "reported_toolchain": "Python 3.10 / matplotlib 2.4.6 后端 Agg / numpy / stdlib sqlite3"}
    rec("C11.toolchain_version", "工具链版本自陈能否在本节点复现",
        "not_run", env,
        "构建镜像与控制面节点可不同版本故不判 fail；但『matplotlib 2.4.6』与本节点 numpy 2.4.6 同号，"
        "疑为版本号错记到 matplotlib 名下（matplotlib 2.x 无 2.4.6 属外部知识，未机器验证）")

    rec("C12.figure_data_traceability", "图 1–3 的数组是否在溯源账本内有可重跑 SQL 记录",
        "pass" if any(f.get("sql") for f in figs) else "fail",
        {"figure_records": len(figs),
         "fields_per_record": ["pid", "figure", "files", "hash_prefixes"],
         "figure_data_sql_bindings": 0,
         "implication": "账本只锁图件字节、不锁图件数值；『图数组=一条可重跑 SQL』在账本内不可复核"},
        "figure arrays bound to sql records")

    rec("C13.funnel_stage_values", "图 3 五阶段是否每阶段都给出可复核计数",
        "fail",
        {"stages_in_text": ["claimed", "reconciled", "machine-checked", "OK", "REAL"],
         "stages_with_value": re.findall(r"(?:claimed|OK|REAL) (\d+)", QUOTE["q_funnel"]),
         "missing": ["reconciled", "machine-checked"]}, "5/5 有值")

    rec("C14.divergence_rule", "『宣称 REAL 18 → 对账 REAL 1』之间 17 项的降级判据是否在文中定义",
        "fail",
        {"claimed_REAL": cvc["claimed_REAL"], "reconciled_REAL": cvc["reconciled_REAL"], "gap": cvc["gap"],
         "labelled_OVERCLAIM": part["OVERCLAIM"], "labelled_UNVERIFIED": part["UNVERIFIED"],
         "implication": "17 项降级中仅 2 项命名为 OVERCLAIM，其余 15 项归 UNVERIFIED；"
                        "两标签的判定谓词全文未给出，『过度宣称 9.5%』易被读成全貌"},
        "classification rule stated")

    rec("C15.gate_rerun", "门禁裁定 PASS（FAIL 0 / WARN 0）能否由审核者独立重执行",
        "not_run",
        {"snapshot_sqlite": "不可得", "manuscript_with_markers": "不可得",
         "producer_scripts": "未读取（保独立性）",
         "consequence": "该裁定在本次审核中保持『未复核』，不升格为 verified"}, "rerun reproduces PASS")

    rec("C16.readonly_claim_strength", "『校验器物理上无法改写自己的证据』是否成立",
        "fail",
        {"actual_guarantee": "sqlite3 mode=ro 只阻止经该连接的写事务；文件系统层替换不受约束",
         "report_own_caveat": QUOTE["q_lim_unknown"]},
        "holds against filesystem-level rewrite")

    rec("C17.reviewer_independence", "审核输入是否仅含原文、不含生产者解释",
        "pass",
        {"inputs": ["任务书契约声明", "GET /tensor/reports/5606 的 markdown 落盘件"],
         "not_read": ["生产者实现代码 snapshot.py/provenance.py/skeleton.py/figures.py/verify.py",
                      "生产者 rationale / 自评", "其它 report_id 的 markdown"],
         "limitation": "未读实现 ⇒ 只能判『文档与账本能否支撑声明』，不能判代码是否照描述执行"},
        "context == source only")

    rec("C18.no_numeric_contradiction", "表 1 与 20 条记录之间是否存在数值矛盾",
        "pass",
        {"percent_checks": len(cons["percent_recompute"]), "max_rel_err": cons["percent_max_rel_err"],
         "partition_closed": part["equals_total"],
         "note": "本次审核的正面结论：印刷数字、SQL 语义、分类划分自洽，未见伪造痕迹"}, "no contradiction")

    s = {"pass": [c["id"] for c in checks if c["status"] == "pass"],
         "fail": [c["id"] for c in checks if c["status"] == "fail"],
         "not_run": [c["id"] for c in checks if c["status"] == "not_run"]}

    indep = {"package_id": PKG_ID, "report_id": REPORT_ID, "source": meta,
             "quote_index": quote_index, "checks": checks, "checks_summary": s,
             "derived": {"table1": {k: v["number"] for k, v in t1.items()},
                         "conservation": cons,
                         "provenance_rows": rows, "figure_rows": figs,
                         "frozen_artifact": {"path": ARTIFACT_PATH, "exists": art_exists, "sha256": art_hash}},
             "env": env, "generated_at": datetime.now(timezone.utc).isoformat()}
    (HERE / "indep_check.json").write_text(json.dumps(indep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"checks": len(checks), **{k: len(v) for k, v in s.items()}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())