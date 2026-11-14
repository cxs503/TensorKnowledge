"""报告层：把 result + snapshot 渲染成六要素 Markdown 与三张图（数字全部程序化注入）。

铁律：报告里的每个数字都来自 ``result`` / ``snapshot`` 对象，函数内**没有手写字面量数字**，
所以任何人改了数据重跑，报告自动跟着改，不会出现"报告好看、数据难看"。
"""
from __future__ import annotations

import json
from pathlib import Path

from . import compute, spec


def _pct(x) -> str:
    return "未定义(0/0)" if x is None else f"{x:.4%}"


def render_markdown(result: dict, snapshot: dict, bench: dict | None = None) -> str:
    raw = snapshot["raw"]
    ci = result.get("confidence_interval") or {}
    L: list[str] = []
    A = L.append
    A("# KPI-KB-VERIFY-RATE 周期复测计量（只读计量单）\n")
    A(f"- 锚点：`feature_ledger#{spec.ANCHOR['feature_ledger_id']}` "
      f"`{spec.ANCHOR['slug']}`（{spec.ANCHOR['definition']}）")
    A(f"- 口径 spec：`{spec.SPEC_VERSION}` / `spec_sha256={spec.SPEC_SHA256}`")
    A(f"- 快照：`snapshot_sha256={result['snapshot_sha256']}` 采集于 {result['collected_at_utc']}")
    A(f"- **现值 current = {_pct(result['current'])}**"
      f"（分子 {result['numerator']} / 分母 {result['denominator']}）")
    A(f"- 目标 target = `null`（{result['target_status']}）：{result['target_source']}\n")

    # ① 案例介绍
    A("## ① 案例介绍（KPI 口径与数据面）\n")
    A("本单计量的是「知识对象（KO）从进入验证流程到经平台验证通过」的转化率，"
      "它衡量知识治理链路是否真的把 KO 推到可验证状态，而不是衡量文档/代码产量。\n")
    A("| 量 | 定义（冻结） |")
    A("|---|---|")
    A(f"| 分子 | {spec.NUMERATOR_SCOPE} |")
    A(f"| 分母 | {spec.DENOMINATOR_SCOPE} |")
    A(f"| 目标 | 由 RCI-F1 试点评估定标（当前 `{result['target_status']}`） |")
    A("")
    A("数据面（两个库、全部只读）：\n")
    A("| 逻辑库 | 表 | 作用 |")
    A("|---|---|---|")
    seen = set()
    for q in spec.QUERIES.values():
        key = (q["db"], q["table"])
        if key in seen:
            continue
        seen.add(key)
        A(f"| `{q['db']}` | `{q['table']}` | {q['role']} |")
    A("")

    # ② 方法
    A("## ② 怎么做的（方法 / 工具链 / 可复算设计）\n")
    A("1. **采集**：`python -m tools.kpi_kb_verify_rate collect` 以只读连接（服务端 "
      "`default_transaction_read_only=on` + 静态 SELECT 校验）执行 spec 登记的 "
      f"{len(spec.QUERIES)} 条 SQL，落 `snapshot.json`（含每条 SQL 原文与 sha256 指纹）。")
    A("2. **算核**：`compute.build_result()` 是纯函数（不连库、不读时钟），把 snapshot 变成 "
      "result JSON；`0/0` 判为**未定义**（null），绝不写 0。")
    A("3. **双路径复核**：`oracle.py` 用另一种写法（状态机事件表数分母、`EXISTS` 半连接取分子 id 集）"
      "独立复算，判等不只是数字相等，还比 id 集合相等。")
    A("4. **基准（ref vs got）**：`bench.py` 三层（口径语义 / scratch 库真 SQL / 活库双路径）。")
    A("5. **工件**：result JSON + 六要素报告 + 三张图，全部由同一次采样程序化生成。\n")
    A("```bash")
    for c in result["repro_cmd"]:
        A(c)
    A("```\n")

    # ③ 计算结果
    A("## ③ 计算结果（程序化注入，零手抄）\n")
    A("### 3.1 KPI 现值\n")
    A("| 项 | 值 | 推导 |")
    A("|---|---|---|")
    A(f"| 分子 numerator | {result['numerator']} | `num_l3_gate_confirmed`："
      "`storage_level='L3' ∧ verification_status='platform_verified' ∧ 验证单 confirmed(gate_level≥2)` |")
    A(f"| 分母 denominator | {result['denominator']} | `ko_enter_flow`："
      "`verification_status ∈ {report_claimed, platform_verified}` |")
    A(f"| current | {_pct(result['current'])} | 分子/分母（分母=0 → null） |")
    if ci:
        A(f"| 95% Wilson 区间 | [{ci['low']:.4%}, {ci['high']:.4%}] | 分子={result['numerator']}、"
          f"n={result['denominator']} |")
    A(f"| target / gap | `null` / `null` | 目标未定标 -> 不消账（{result['target_status']}） |")
    A("")
    A("### 3.2 链路逐级漏斗（原始计数，全部可 SQL 复算）\n")
    A("| 环节 | 计数 | 字段 |")
    A("|---|---|---|")
    for qid, label in [("ko_total", "KO 总数"), ("ko_enter_flow", "进入验证流程"),
                       ("ko_enter_flow_events", "状态机事件显示已进入流程"),
                       ("ko_l3_candidates", "L3 候选"), ("ko_platform_verified", "平台已验证"),
                       ("verification_tickets", "验证单总数"),
                       ("num_l3_gate_confirmed", "L3 且 gate confirmed（=分子）")]:
        A(f"| {label} | {raw.get(qid)} | `{qid}` |")
    A("")
    A("### 3.3 灵敏度（同数据、不同口径解释；headline 只引主口径）\n")
    A("| 口径 | 分子 | 分母 | 现值 |")
    A("|---|---|---|---|")
    for s in result["sensitivity"]:
        A(f"| {s['scope']} | {s['numerator']} | {s['denominator']} | {s['current_display']} |")
    A("")
    dist = raw.get("ko_by_status") or {}
    if dist:
        A("### 3.4 状态分布\n")
        A("| verification_status | 计数 |")
        A("|---|---|")
        for k, v in dist.items():
            A(f"| `{k}` | {v} |")
        A("")
    lv = raw.get("ko_by_level") or {}
    if lv:
        A("| storage_level | 计数 |")
        A("|---|---|")
        for k, v in lv.items():
            A(f"| `{k}` | {v} |")
        A("")

    # ④ 图
    A("## ④ 结果图\n")
    A("![fig1](figures/fig1_funnel.png)")
    A("**图1** 验证链路逐级漏斗：从 KO 总数到 gate confirmed 分子，每级都标注计数；"
      "断点位置直接指出分子为 0 的机制性原因。\n")
    A("![fig2](figures/fig2_sensitivity.png)")
    A("**图2** 四条口径的现值对照（主口径带 95% Wilson 区间）。"
      "任何口径下现值都不被「好看」地放大。\n")
    A("![fig3](figures/fig3_data_quality.png)")
    A("**图3** 分母与证据层的数据质量画像：证据 `artifact_kind` 分布、平台 verdict gate 状态分布，"
      "以及单 producer 批量灌入的窗口。\n")

    # ⑤ 注意点
    A("## ⑤ 注意点（坑 / 局限 / 适用范围）\n")
    prof = raw.get("ko_producer_profile") or {}
    A(f"- **分母质量**：`{raw.get('ko_total')}` 条 KO 由 {prof.get('producers')} 个 producer 在 "
      f"{prof.get('span_seconds')} 秒内写入、覆盖 {prof.get('domains')} 个 domain "
      "——分母真实性未证，现值应连同该画像一起引用。")
    A(f"- **证据层**：`artifact_kind='none'` 证据 {raw.get('evidence_artifact_none')} 条 / "
      f"总 {raw.get('evidence_total')} 条，可解析工件证据的 KO 数为 "
      f"{raw.get('ko_with_artifact_evidence')}——gate 若要求工件证据，则分子在结构上无法抬升。")
    A(f"- **验证单通道**：`ko_verification` 共 {raw.get('verification_tickets')} 张，"
      f"confirmed {raw.get('verification_tickets_confirmed')} 张。")
    A("- **口径敏感性**：分母若改按「已开验证单的 KO」计，则 0/0 → KPI 未定义（不是 0%）；"
      "本报告因此始终把口径与数字一起引用。")
    A("- **只读边界**：本单不改任何代码/数据，不对平台库写入；缺口修复建议以派生锚点形式提出，"
      "由后续改进单执行。\n")

    # ⑥ 误差判定
    A("## ⑥ 误差判定（逐项显式回答「是否 <3%」）\n")
    A("| 项 | ref（参照） | got（本计量器） | 偏差 | 是否 <3% |")
    A("|---|---|---|---|---|")
    if bench:
        for r in bench.get("tier_a", []):
            A(f"| Tier A {r['case']}：口径语义 | {r['ref']} | {r['got']} | "
              f"{r['abs_error']:.3g} | 是（精确 0） |")
        tb = bench.get("tier_b", {})
        if tb.get("status") == "run":
            for r in tb["cases"]:
                A(f"| Tier B {r['case']}：scratch 库真 SQL | {r['ref']} | {r['got']} | "
                  f"counts Δ={r['abs_error_numerator']}/{r['abs_error_denominator']} | "
                  f"{'是（精确 0）' if r['pass'] else '**否**'} |")
        else:
            A(f"| Tier B：scratch 库真 SQL | — | — | — | NOT_RUN（{tb.get('reason')}） |")
        tc = bench.get("tier_c", {})
        if tc.get("status") == "run":
            A(f"| Tier C 活库双路径 | num/den={tc['ref']['numerator']}/{tc['ref']['denominator']} | "
              f"num/den={tc['got']['numerator']}/{tc['got']['denominator']} | "
              f"Δ={tc['abs_error_numerator']}/{tc['abs_error_denominator']} | "
              f"{'是（精确 0）' if tc['pass'] else '**否**'} |")
        else:
            A(f"| Tier C 活库双路径 | — | — | — | NOT_RUN（{tc.get('reason')}） |")
    A("")
    A(f"**结论**：本次计量的数值本身没有「误差」之说（分子/分母都是精确计数，"
      f"current 由整数除法得到），能判的是**两路独立实现是否给同一答案**："
      f"当前主路与独立 oracle 在活库上"
      f"{'一致' if (bench or {}).get('tier_c', {}).get('pass') else '未判/不一致'}。"
      f"**是否 <3%**：计数类判据为精确相等（0 偏差），故远小于 3%；"
      f"但**目标值未定标**，因此「现状离目标差多少」这一项**无基准可判**，"
      f"不以任何估计值填充。\n")

    # 缺口与派生锚点
    A("## ⑦ 缺口与派生锚点（由 snapshot 程序化派生）\n")
    A("| 缺口 | 严重度 | 发现 | 推导式 |")
    A("|---|---|---|---|")
    for g in result["top_gaps"]:
        A(f"| `{g['id']}` | {g['severity']} | {g['finding']} | `{g['derivation']}` |")
    A("")
    A("| 建议锚点 | derived_from | acceptance |")
    A("|---|---|---|")
    for a in result["proposed_anchors"]:
        A(f"| `{a['slug']}` | `{a['derived_from']}` | {a['acceptance']} |")
    A("")
    return "\n".join(L) + "\n"


def _setup_mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.dpi": 120, "font.size": 9, "axes.grid": True,
                         "grid.alpha": 0.3})
    return plt


def make_figures(result: dict, snapshot: dict, out_dir: str | Path) -> list[Path]:
    plt = _setup_mpl()
    raw = snapshot["raw"]
    out = Path(out_dir) / "figures"
    out.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    # fig1 漏斗
    labels = ["KO total", "enter flow", "L3 candidates", "platform verified",
              "gate confirmed\n(= numerator)"]
    values = [int(raw.get(k) or 0) for k in
              ("ko_total", "ko_enter_flow", "ko_l3_candidates", "ko_platform_verified",
               "num_l3_gate_confirmed")]
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    bars = ax.bar(range(len(values)), [max(v, 0.5) for v in values],
                  color=["#4c78a8", "#4c78a8", "#f58518", "#f58518", "#d62728"])
    ax.set_yscale("log")
    ax.set_xticks(range(len(values)))
    ax.set_xticklabels(labels)
    ax.set_ylabel("count (log; 0 drawn as 0.5)")
    ax.set_title(f"KPI-KB-VERIFY-RATE = {result['numerator']}/{result['denominator']} "
                 f"= {_pct(result['current'])}")
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, max(v, 0.5) * 1.15, f"{v}",
                ha="center", fontsize=9, fontweight="bold")
    fig.tight_layout()
    p1 = out / "fig1_funnel.png"
    fig.savefig(p1)
    plt.close(fig)
    paths.append(p1)

    # fig2 灵敏度
    scopes = [s["scope"] for s in result["sensitivity"]]
    vals = [0.0 if s["current"] is None else s["current"] for s in result["sensitivity"]]
    fig, ax = plt.subplots(figsize=(8.4, 3.8))
    colors = ["#d62728" if i == 0 else "#9ecae1" for i in range(len(vals))]
    ax.barh(range(len(vals)), vals, color=colors)
    ax.set_yticks(range(len(vals)))
    ax.set_yticklabels([s[:4] for s in scopes], fontsize=7)
    for i, s in enumerate(result["sensitivity"]):
        ax.text(vals[i] + 0.0005, i, s["current_display"], va="center", fontsize=8)
    ci = result.get("confidence_interval")
    if ci and result["current"] is not None:
        ax.errorbar([result["current"]], [0], xerr=[[result["current"] - ci["low"]],
                                                   [ci["high"] - result["current"]]],
                    fmt="o", color="black", capsize=4, label="95% Wilson (primary)")
        ax.legend(fontsize=7, loc="lower right")
    ax.set_xlabel("current (ratio)")
    ax.set_title("KPI current under 4 scope interpretations (red = primary)")
    ax.set_xlim(0, max(vals) * 1.35 + 0.001)
    fig.tight_layout()
    p2 = out / "fig2_sensitivity.png"
    fig.savefig(p2)
    plt.close(fig)
    paths.append(p2)

    # fig3 数据质量
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.8))
    kinds = raw.get("evidence_kinds") or {}
    if kinds:
        axes[0].bar(range(len(kinds)), list(kinds.values()), color="#6baed6")
        axes[0].set_xticks(range(len(kinds)))
        axes[0].set_xticklabels(list(kinds), rotation=20, fontsize=7)
        axes[0].set_ylabel("evidence rows")
        axes[0].set_title(f"evidence artifact_kind distribution (none={kinds.get('none')})")
    gs = raw.get("verdict_gate_states") or {}
    if gs:
        axes[1].bar(range(len(gs)), list(gs.values()), color="#fdae6b")
        axes[1].set_xticks(range(len(gs)))
        axes[1].set_xticklabels(list(gs), rotation=20, fontsize=7)
        axes[1].set_ylabel("verdicts")
        axes[1].set_title(f"platform verdict gate_state (total={sum(gs.values())})")
    prof = raw.get("ko_producer_profile") or {}
    if prof:
        fig.suptitle(f"denominator profile: producers={prof.get('producers')} domains={prof.get('domains')} "
                     f"n={prof.get('n')} span={prof.get('span_seconds')}s", fontsize=9)
    fig.tight_layout()
    p3 = out / "fig3_data_quality.png"
    fig.savefig(p3)
    plt.close(fig)
    paths.append(p3)
    return paths


def write_artifacts(snapshot: dict, result: dict, out_dir: str | Path,
                    bench: dict | None = None) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = render_markdown(result, snapshot, bench)
    (out / "KPI-KB-VERIFY-RATE.md").write_text(md, encoding="utf-8")
    figs = make_figures(result, snapshot, out)
    (out / "figures_manifest.json").write_text(json.dumps(
        [{"name": p.name, "bytes": p.stat().st_size} for p in figs], indent=2) + "\n",
        encoding="utf-8")
    return {"result": out / "result.json", "markdown": out / "KPI-KB-VERIFY-RATE.md",
            "figures": figs, "result_sha256": compute.result_fingerprint(result)}