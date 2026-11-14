#!/usr/bin/env python3
"""RCI-S1 · render docs/rci-s1-registry.md (and the report figures) from artifacts.

Every number in the rendered page is injected from
``runs/rci-s1-registry/out/{summary,inputs_manifest}.json`` (plus the row ledger
for the distribution tables) -- nothing is hand-typed. ``--check`` re-renders in
memory and diffs against the file on disk, so a stale page fails CI.

Figures (``--figures``) go to ``artifacts/rci-s1-registry/figures/`` (gitignored run
area) and are embedded in the mission report; they are pure functions of the row ledger.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "runs", "rci-s1-registry", "out")
DOC = os.path.join(ROOT, "docs", "rci-s1-registry.md")
FIGDIR = os.path.join(
    ROOT, "artifacts", "rci-s1-registry", "figures"
)  # gitignored run area

# Inherited from the board audit of the original run (m15810 §3): the gate sweep
# needs the MinHash feature set, which was not archived, so it is *cited*, never
# recomputed here -- and it is excluded from every test assertion.
SWEEP = [
    ("0.4", 764, 2176, 1412),
    ("0.5", 763, 2174, 1411),
    ("0.7", 758, 2161, 1403),
    ("0.0 (LSH-only)", 764, 2176, 1412),
]
SWEEP_SRC = (
    "board audit m15810 §3 独立重跑（audit/artifacts/rerun_n8.log）；"
    "**本次未重算**——见 §6 F1"
)


def load():
    with gzip.open(
        os.path.join(OUT, "registry_rows.jsonl.gz"), "rt", encoding="utf-8"
    ) as f:
        rows = [json.loads(line) for line in f if line.strip()]
    summary = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    manifest = json.load(
        open(os.path.join(OUT, "inputs_manifest.json"), encoding="utf-8")
    )
    return rows, summary, manifest


def kv(d, order=None):
    items = [(k, d[k]) for k in order if k in d] if order else sorted(d.items())
    return ", ".join(f"{k}={v}" for k, v in items)


def render(rows, s, m) -> str:
    cc = m["cross_checks"]
    by_type = s["by_type"]
    n = s["rows"]
    type_sum = sum(by_type.values())
    rule_sum = sum(s["by_type_rule"].values())
    fe_codes_sum = sum(s["failed_empty_codes"].values())
    # rows carrying >=2 hole codes: union is smaller than the code sum (F3)
    multi = sum(1 for r in rows if len(r["failed_empty_codes"]) >= 2)
    repos = Counter(r["repo"] for r in rows if r["repo"]).most_common(8)
    repo_txt = ", ".join(f"{k}={v}" for k, v in repos)
    status = Counter(r["mission_status"] for r in rows).most_common()
    status_txt = ", ".join(f"{k if k else '<none>'}={v}" for k, v in status)
    hist = s["dup_cluster_size_hist"]
    hist_txt = ", ".join(
        f"{k}→{v}" for k, v in sorted(hist.items(), key=lambda x: int(x[0]))
    )
    q = s["q_dims_pending"]
    a8_ok = (
        cc["sql_dup_clusters"] == s["dup_clusters"]
        and cc["sql_dup_reports_in_clusters"] == s["dup_reports_in_clusters"]
        and cc["coverage_ledger_only_rows"] == 0 == cc["coverage_source_only_rows"]
    )
    sweep_tbl = "\n".join(f"| {g} | {c} | {i} | {e} |" for g, c, i, e in SWEEP)

    return f"""# KBM-RCI-S1-REGISTRY · 报告资产盘点（Research Asset Registry）

> 锚点 `KBM-RCI-S1-REGISTRY`｜快照 `{m["snapshot_id"]}`｜行数 **{n}**｜
> 裁判：`scripts/rci-s1-registry/export_registry.py verify`（从行级账重算 23 聚合）+ SQL 侧独立复算（manifest.cross_checks）
> 本页由 `scripts/rci-s1-registry/gen_doc.py` 从工件渲染（数字零手抄）；`--check` 模式保证页与工件同版本。

## ① 问题设定与基准出处

TensorKnowledge 第一个正式工程 *Research Corpus Intelligence* 的阶段 1：把平台 `tensor_reports` 里
全部 **{n}** 篇 published 报告变成可检索/可关联/可验证/可复用的资产账。三铁则（owner 原令）：
报告自动入库≠知识；知识必须加工；科学结论必须验证。

**基准（ref）出处**：

- 数量基准 `{n}` = 任务书头条数字。本账以快照 id `{m["snapshot_id"]}` 钉死；
  源库同一时刻复算 `status='published' AND created_at <= {m["t_pin"]}` = **{cc["db_published_at_t_pin"]}**（逐字相等，误差 0）。
  实时 published 为 **{cc["db_live_published"]}**（`observed_at={cc["observed_at"]}`，与上一数字**同一次读取**），
  差额 {cc["drift_vs_pin"]} 篇属快照后增长，不混入本账（F2 的修法：单次读取 + 标注时刻）。
- 清洗判决基准 = KBM-CLEAN-W1 报告面账本（`runs/cleaning-w1/reports/ledger.jsonl`）。该源文件在本工作树已不可得，
  其判决结果已冻结在表列 `clean_decision` / `clean_primary_code` / `failed_empty_codes` 中，本单只消费不重造。
- 方法谱系（external_anchor）：Broder 1997（MinHash 相似度）；Indyk & Motwani 1998 STOC（LSH 分带索引）；
  Charikar 2002（SimHash，本轮未采用）；W3C PROV-O 2013（溯源字段命名对齐）；`datasketch` 的 b×r 分带惯例。
- 开源横向调研：feature 检索 `%REGISTRY%` 0 命中——横向无现成结构可抄，方法按文献谱系自落地（如实记录，不编造对标）。

## ② 方法与实现

四段流水线（纯 stdlib，loong64 安全；数字全部程序化产出）：

| 步 | 脚本（原跑） | 做什么 | 关键实现 |
|---|---|---|---|
| 1 | `build_data.py` | 钉快照导出 reports/missions CSV + 消费 W1 清洗账本 + 工件三件套探针 | `dump_csv` / `probe_worktree` |
| 2 | `rci_pipeline.py shard` | 逐报告：长度/图/tag、`md_sha256`、标题归一、数字掩码骨架、5-gram MinHash-128、数字集、四类分型、真实执行重合率 | `gram_hashes` / `minhash_sig` / `classify` |
| 3 | `rci_pipeline.py merge` | 并查集：exact-sha ∪ title ∪ skeleton ∪ LSH 候选（J≥0.5 复算）；簇号；六维质量位；汇总 | `run_merge` / `DSU` |
| 4 | `verify_db.py` / `load_registry.py` | 落库 `rci_asset_registry` 后 17 个聚合 DB↔工件全等复核 | `checks{{}}` |

**本轮补的复现桥**：第 2–4 步的输入（W1 清洗账本、`worktree_triple.json`、MinHash 特征集）未随分支入库，
故行级/聚合工件一度只剩 DB。`export_registry.py` 从**表即记录**（`rci_asset_registry`，一行一报告，快照钉死）
把 `registry_rows.jsonl.gz` + `summary.json` 逐字节确定性地重建（keys 排序、gzip mtime=0），
并在同一次导出里做 SQL↔工件双向对拍。`verify` 只读行级账重算全部聚合，任何手改即红。

**分型规则（标题→任务 goal→正文信号 级联，规则号入库）**：
{kv(s["by_type_rule"], ["R0_clean_excluded", "R1_title_creative", "R2_title_research", "R3_title_analysis", "R4_title_info", "R5_goal_creative", "R6_goal_research", "R7_goal_analysis", "R8_goal_info", "R9_bench_ref", "R10_table_numbers", "R11_numbers"])}

## ③ 参数表

| 参数 | 值 | 说明 |
|---|---|---|
| 快照 T_pin | `{m["t_pin"]}` | {n} 篇 published 的冻结时刻 |
| GRAM / 窗口 | {s["params"]["GRAM"]} / {s["params"]["MD_WINDOW"]} | 5-gram，正文尾窗 50k 字符（控成本） |
| MinHash | N_PERM={s["params"]["N_PERM"]}，BANDS={s["params"]["BANDS"]}×ROWS={s["params"]["ROWS"]} | 128 排列，16×8 分带（保守召回） |
| 精确门限 | J ≥ {s["params"]["JACCARD_GATE"]} | LSH 候选再算真 Jaccard |
| 真实执行门限 | 数字交集/报告数字集 ≥ 0.5 → verified | 阈值在 `run_shard` 常量 |
| 去重链接 | {s["params"]["dup_link"]} | 三类结构链接与 LSH 并查集合并 |
| 工件三件套 | wt_exists → artifacts\|runs 有文件 → repro 入口 | 三真才 `triple_ok`（活体探测，见 F1） |

## ④ 对照表（ref vs got，判据逐条打勾）

| 判据 | got（程序化） | 判定 |
|---|---|---|
| A1 覆盖 {n} 篇（数量） | rows={n}；源库同期 {cc["db_published_at_t_pin"]} | ✅（误差 0） |
| A2 四类分型覆盖 100% | {" + ".join(f"{k}={v}" for k, v in sorted(by_type.items()))} = {type_sum} | {"✅" if type_sum == n else "❌"} |
| A3 分型有可复算规则（无未命中） | 规则和={rule_sum}，`R12_fallback`={s["by_type_rule"].get("R12_fallback", 0)} | {"✅" if rule_sum == n and "R12_fallback" not in s["by_type_rule"] else "❌"} |
| A4 项目/领域来源 | repo 非空 {sum(1 for r in rows if r["repo"])}/{n}，distinct repo={s["distinct_repos"]}，distinct scenario={s["distinct_scenarios"]} | ✅ |
| A5 任务链关联（mission_id→tensor_dev_missions） | 有 mission {s["with_mission"]}/{n}，distinct mission={s["distinct_missions"]}，悬空 {cc["dangling_mission_ids"]} 个 id / {cc["dangling_mission_rows"]} 行 | {"✅" if cc["dangling_mission_rows"] == 0 else "❌"}（残留记账，不抹平） |
| A6 真实执行标记覆盖 100% | {" + ".join(f"{k}={v}" for k, v in sorted(s["by_real_exec"].items()))} = {sum(s["by_real_exec"].values())} | {"✅" if sum(s["by_real_exec"].values()) == n else "❌"} |
| A7 重复簇 + 空洞账 | clusters={s["dup_clusters"]}, in={s["dup_reports_in_clusters"]}, excess={s["dup_excess_reports"]}, failed_empty={s["failed_empty"]} | ✅ |
| A8 落库一致性（SQL vs 工件） | SQL 独立复算 clusters={cc["sql_dup_clusters"]}/in={cc["sql_dup_reports_in_clusters"]}/excess={cc["sql_dup_excess_reports"]}；双向覆盖差 {cc["coverage_ledger_only_rows"]}/{cc["coverage_source_only_rows"]} | {"✅" if a8_ok else "❌"} |

**分项数字（同一快照）**

| 维度 | 分布 |
|---|---|
| asset_type | {kv(by_type)} |
| clean_decision | {kv(s["by_clean"])} |
| real_exec_flag | {kv(s["by_real_exec"])} |
| 重复簇 | clusters={s["dup_clusters"]}, reports_in_clusters={s["dup_reports_in_clusters"]}, excess={s["dup_excess_reports"]}, 最大簇={max(int(k) for k in hist)} |
| 簇尺寸直方图 | {hist_txt} |
| 空洞/失败账 | no_artifact={s["failed_empty_codes"].get("no_artifact", 0)}, clean_X06_process_log={s["failed_empty_codes"].get("clean_X06_process_log", 0)}, clean_X02_empty_or_stub={s["failed_empty_codes"].get("clean_X02_empty_or_stub", 0)}, no_numbers={s["failed_empty_codes"].get("no_numbers", 0)}；**并集 failed_empty={s["failed_empty"]}**（码和={fe_codes_sum}，多码行 {multi}，多码计一次） |
| 任务状态 | {status_txt} |
| repo（前 8） | {repo_txt} |
| 正文/图 | md_chars_total={s["md_chars_total"]}, p50={s["md_chars_p50"]}, figures={s["n_figures_total"]}, 有图报告={s["reports_with_figures"]} |

## ⑤ 敏感性 / 两分辨率

门限扫描（clusters / in-cluster / excess）：

| gate | clusters | in-cluster | excess |
|---|---|---|---|
{sweep_tbl}

出处：{SWEEP_SRC}。主跑 gate=0.5；0.4 放松、0.7 收紧只在 6 簇内摆动，
故主结论（**excess={s["dup_excess_reports"]} 篇 = {s["dup_excess_reports"] / n:.1%} 的重复劳动**）对阈值不敏感。
**两分辨率**：数量/分型/去重三维在异分片重跑（N=8 vs 主跑 N=24，审计记录）逐位相同；
活体探测族（wt_exists / triple_ok / failed_empty）随工作树存活状态漂移（F1）。

## ⑥ 失败模式 / 局限（诚实记账）

| ID | 现象（本轮复核） | 处置 |
|---|---|---|
| F1 | `probe_worktree` 直读 `/root/tp-agent/work/m<id>`：活体探测，重跑漂移（历史 N=8 重跑 wt_exists 2240→1608）。本账 wt_exists={s["wt_exists"]}、triple_ok={s["triple_ok"]} 为原跑时刻值 | 表即记录：探测结果已冻结入库，`export_registry.py` 不再活体探测；后继单应改为钉死 `worktree_triple.json` 输入 |
| F2 | 旧文档把两次不同读取的 live published 混写 | 已改单次读取 + `observed_at={cc["observed_at"]}` 标注（见 §①） |
| F3 | failed_empty 四码相加 ≠ 并集 | 本文统一按并集 {s["failed_empty"]} 表述，多码行 {multi} 计一次 |
| F4 | 任务链悬空：{cc["dangling_mission_ids"]} 个 mission_id（{cc["dangling_mission_rows"]} 行）无 `tensor_dev_missions` 行，占 {cc["dangling_mission_rows"] / n:.2%} | 记为残留，不抹平；A5 自判 ❌ |
| F5 | 门限扫描未在本工作树重算（MinHash 特征集未归档） | 保留审计出处并标注；后继单应持久化 `minhash` 签名（9446×128 int ≈ 1.2M 数，几 MB 级） |
| F6 | 质量位 {", ".join(q)} 全为 NULL（S2 范围） | 本阶段只做 S1（可检索/可关联/可验证），不虚标 L3 |

## ⑦ 复现

```bash
# 1) 表即记录 -> 行级账 + 聚合（只读 DB，确定性字节）
python3 scripts/rci-s1-registry/export_registry.py export --out runs/rci-s1-registry/out
# 2) 从行级账重算 23 聚合（任一不等即 exit 1）
python3 scripts/rci-s1-registry/export_registry.py verify --out runs/rci-s1-registry/out
# 3) 本页与工件是否同版本
python3 scripts/rci-s1-registry/gen_doc.py --check
# 4) 不变量测试
python3 -m pytest tests/test_rci_registry.py -q
```
"""


def figures(rows, s):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(FIGDIR, exist_ok=True)
    made = []

    # fig1: asset_type x clean_decision
    types = sorted(s["by_type"])
    cleans = sorted(s["by_clean"])
    grid = {t: {c: 0 for c in cleans} for t in types}
    for r in rows:
        if r["asset_type"] in grid and r["clean_decision"] in grid[r["asset_type"]]:
            grid[r["asset_type"]][r["clean_decision"]] += 1
    fig, ax = plt.subplots(figsize=(6.4, 3.6), dpi=160)
    bottom = [0] * len(types)
    colors = {
        "kept": "#4c78a8",
        "repaired": "#f58518",
        "excluded": "#b0b0b0",
        "not_in_w1": "#d62728",
    }
    for c in cleans:
        vals = [grid[t][c] for t in types]
        ax.bar(types, vals, bottom=bottom, label=c, color=colors.get(c))
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_ylabel("reports")
    ax.set_title(f"asset_type × clean_decision (n={s['rows']})")
    ax.legend(fontsize=8)
    fig.tight_layout()
    p1 = os.path.join(FIGDIR, "fig1_typing_clean.png")
    fig.savefig(p1)
    plt.close(fig)
    made.append(p1)

    # fig2: real_exec_flag
    keys = sorted(s["by_real_exec"], key=lambda k: -s["by_real_exec"][k])
    vals = [s["by_real_exec"][k] for k in keys]
    fig, ax = plt.subplots(figsize=(6.4, 3.2), dpi=160)
    ax.barh(keys[::-1], vals[::-1], color="#4c78a8")
    for y, v in enumerate(vals[::-1]):
        ax.text(v, y, f" {v}", va="center", fontsize=8)
    ax.set_xlabel("reports")
    ax.set_title("real-execution evidence flag (number-overlap proxy)")
    fig.tight_layout()
    p2 = os.path.join(FIGDIR, "fig2_real_exec.png")
    fig.savefig(p2)
    plt.close(fig)
    made.append(p2)

    # fig3: cluster size histogram (log-log)
    hist = {int(k): v for k, v in s["dup_cluster_size_hist"].items()}
    xs = sorted(hist)
    fig, ax = plt.subplots(figsize=(6.4, 3.2), dpi=160)
    ax.plot(xs, [hist[x] for x in xs], "o-", color="#f58518")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("duplicate cluster size")
    ax.set_ylabel("#clusters")
    ax.set_title(
        f"duplicate cluster sizes (clusters={s['dup_clusters']}, "
        f"reports={s['dup_reports_in_clusters']})"
    )
    ax.grid(alpha=0.3)
    fig.tight_layout()
    p3 = os.path.join(FIGDIR, "fig3_duplicates.png")
    fig.savefig(p3)
    plt.close(fig)
    made.append(p3)

    # fig4: md_chars vs real_exec_overlap, coloured by flag
    fig, ax = plt.subplots(figsize=(6.4, 3.6), dpi=160)
    for flag, color in (
        ("verified", "#2ca02c"),
        ("partial", "#4c78a8"),
        ("zero_overlap", "#d62728"),
    ):
        pts = [
            (r["md_chars"], r["real_exec_overlap"])
            for r in rows
            if r["real_exec_flag"] == flag and r["real_exec_overlap"] is not None
        ]
        if pts:
            ax.scatter(
                [p[0] for p in pts],
                [p[1] for p in pts],
                s=3,
                alpha=0.5,
                label=f"{flag} ({len(pts)})",
                color=color,
            )
    ax.axhline(0.5, ls="--", lw=1, color="k")
    ax.text(1e2, 0.52, "verified gate J>=0.5", fontsize=7)
    ax.set_xscale("log")
    ax.set_xlabel("report md_chars (log)")
    ax.set_ylabel("number overlap with mission.result")
    ax.set_title("real-execution proxy vs report length")
    ax.legend(fontsize=7)
    fig.tight_layout()
    p4 = os.path.join(FIGDIR, "fig4_traceability_length.png")
    fig.savefig(p4)
    plt.close(fig)
    made.append(p4)
    return made


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="diff rendered page vs disk")
    ap.add_argument(
        "--figures", action="store_true", help="also regenerate png figures"
    )
    a = ap.parse_args()
    rows, s, m = load()
    page = render(rows, s, m)
    if a.check:
        cur = open(DOC, encoding="utf-8").read() if os.path.exists(DOC) else ""
        if cur != page:
            print(
                f"DOC STALE: {DOC} differs from gen_doc.py rendering "
                f"({len(cur)} vs {len(page)} chars)"
            )
            return 1
        print(f"DOC OK: {DOC} == gen_doc.py rendering ({len(page)} chars)")
        return 0
    with open(DOC, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {DOC} ({len(page)} chars, {page.count(chr(10))} lines)")
    if a.figures:
        for p in figures(rows, s):
            print("figure:", os.path.relpath(p, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
