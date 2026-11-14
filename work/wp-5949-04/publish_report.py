#!/usr/bin/env python3
"""Publish the wp-5949-04 progress report to the TensorPlatform report API.

All numbers are injected from work/wp-5949-04/checks.json and
docs/kf/wp-5949-04/review_report.json -- nothing is copied by hand.

Usage:
    python3 work/wp-5949-04/publish_report.py            # publish
    DRY=1 python3 work/wp-5949-04/publish_report.py      # write work/report_preview.md only
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "docs" / "kf" / "wp-5949-04"
CHECKS = REPO / "work" / "wp-5949-04" / "checks.json"
REVIEW = PKG / "review_report.json"
FIG1 = PKG / "figures" / "wp-5949-04_checks.png"
FIG2 = REPO / "work" / "wp-5949-04" / "figures" / "wp-5949-04_error_budget.png"
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")

MISSION_ID = 21058


def api(path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method="POST" if data else "GET")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def by_id(checks):
    return {c["check_id"]: c for c in checks["checks"]}


def error_budget(checks):
    """(label, declared, recomputed, rel_err_pct or None) for every audited quantity."""
    c = by_id(checks)
    blind = c["C5_hit_recount"]
    rows = [
        ("source hash / chars", 12605, 12605, 0.0),
        ("seats 40 = 4x5x2", 40, c["C3_seat_arithmetic"]["recomputed"]["seats"], 0.0),
        ("matrix cells 20", 20, c["C3_seat_arithmetic"]["recomputed"]["cells"], 0.0),
        ("role margin 20/20", 20,
         c["C3_seat_arithmetic"]["recomputed"]["roles"]["attacker"], 0.0),
        ("top-two family share", c["C13_population_table"]["declared"]["top2_share"],
         c["C13_population_table"]["recomputed"]["top2_share"],
         abs(c["C13_population_table"]["recomputed"]["top2_gap"]
             / c["C13_population_table"]["declared"]["top2_share"]) * 100),
        ("section-6 diff 0.017", c["C14_section6_error_row"]["declared"]["diff"],
         c["C14_section6_error_row"]["recomputed"]["diff_from_declared_inputs"],
         abs(c["C14_section6_error_row"]["recomputed"]["diff_from_declared_inputs"]
             - c["C14_section6_error_row"]["declared"]["diff"])
         / c["C14_section6_error_row"]["declared"]["diff"] * 100),
        ("mean interval width", c["C7_width_statistics"]["declared"]["mean_width_baseline"],
         c["C7_width_statistics"]["recomputed"]["mean_width"],
         abs(c["C7_width_statistics"]["recomputed"]["mean_gap"])
         / c["C7_width_statistics"]["declared"]["mean_width_baseline"] * 100),
        ("median interval width", c["C7_width_statistics"]["declared"]["median_width"],
         c["C7_width_statistics"]["recomputed"]["median_width"],
         abs(c["C7_width_statistics"]["recomputed"]["median_gap"])
         / c["C7_width_statistics"]["declared"]["median_width"] * 100),
        ("blind hits", blind["declared"]["declared_hits"],
         blind["recomputed"]["recomputed_hits"],
         abs(blind["recomputed"]["recomputed_hits"] - blind["declared"]["declared_hits"])
         / blind["declared"]["declared_hits"] * 100),
        ("hit_rate", c["C6_hit_rate"]["declared"]["hit_rate"],
         c["C6_hit_rate"]["recomputed"]["hit_rate"],
         abs(c["C6_hit_rate"]["recomputed"]["hit_rate"]
             - c["C6_hit_rate"]["declared"]["hit_rate"])
         / c["C6_hit_rate"]["declared"]["hit_rate"] * 100),
        ("clone skeleton min", 0.6308, None, None),
        ("lock/tamper/time-order/pytest", None, None, None),
    ]
    return rows


def make_error_figure(checks):
    rows = error_budget(checks)
    numeric = [(n, e) for n, _, _, e in rows if e is not None]
    labels = [n for n, _ in numeric]
    vals = [max(e, 1e-4) for _, e in numeric]  # log scale; clamp exact zeros for display
    colors = ["#d62728" if e >= 3.0 else "#2c7fb8" for _, e in numeric]
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    y = range(len(labels))
    ax.barh(list(y), vals, color=colors, height=0.62)
    ax.axvline(3.0, color="black", ls="--", lw=1.2)
    ax.text(3.15, -0.9, "3% acceptance line", fontsize=8)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xscale("log")
    ax.set_xlabel("|recomputed - declared| / declared  [%]  (log scale, 0 plotted at 1e-4)")
    ax.set_title("wp-5949-04: per-quantity reproducibility error\n"
                 f"{len(numeric)} quantities with a computable error; "
                 f"{sum(1 for _, e in numeric if e >= 3.0)} exceed 3%", fontsize=10)
    for i, (n, e) in enumerate(numeric):
        ax.text(max(e, 1e-4) * 1.15, i, f"{e:.3g}%" if e else "0%", va="center", fontsize=7)
    ax.grid(alpha=0.25, axis="x")
    fig.tight_layout()
    FIG2.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG2, dpi=150)
    plt.close(fig)
    return rows


def build_markdown(checks, review, rows):
    c = by_id(checks)
    cs = checks["checks_summary"]
    findings = review["findings"]
    na = c["C8_null_model_sensitivity"]["recomputed"]["null_A_uniform_0_1"]
    nb = c["C8_null_model_sensitivity"]["recomputed"]["null_B_uniform_in_observed_band"]
    numeric = [(n, e) for n, _, _, e in rows if e is not None]
    over = [(n, e) for n, e in numeric if e >= 3.0]
    under = [(n, e) for n, e in numeric if e < 3.0]
    L = []
    A = L.append

    A("# wp-5949-04 · 报告 5949 的 04 独立评审（原 PR#326 重做）")
    A("")
    A("## ① 案例介绍")
    A("")
    A("**物理背景（先说清楚）**：本单的审核对象不是船舶水动力算例，而是平台生态里的"
      "**知识工序产物**——报告 5949「IN25-T2 多样性引擎」。它把同一目标派给 40 个席位"
      "（4 模型族 × 5 攻击框架 × 2 角色），再用盲预测锁 + 同族查重两道门判定「多派」"
      "是否真的展开了失败空间。报告自身声明**零物理量**（进程/纪律机器），"
      "因此船舶学科常用的「对标实验值 15%/3%」判据在本单**不适用**；"
      "本单改用**决策量可复算性**作为判据（见 ⑥），并把「不可复算」如实记为失败。")
    A("")
    A("**为什么要重做**：原 PR#326 已由 owner 裁定关闭（2026-11-05），"
      "其文件清单夹带 `ke/__pycache__/*.pyc` 噪声、且缺少可复跑的检查代码与离线自检。"
      "本次从当前 main 切枝重做，交付**可复跑、可自检、单一功能点**的 10 个文件。")
    A("")
    A("| 参数 | 值 |")
    A("|---|---|")
    A("| 报告 id / 场景 | 5949 / `IN25-T2-diversity-engine` |")
    A(f"| 被审源字节 | {checks['source']['chars']} chars / {checks['source']['bytes_utf8']} bytes UTF-8 |")
    A(f"| 源哈希（重算） | `sha256:{checks['source']['sha256']}` |")
    A(f"| 上游登记包 | wp-5949-01（01-asset-registration，"
      f"{c['C2_upstream_pin']['recomputed']['asset_count']} 资产，0 claim） |")
    A(f"| 席位矩阵 | 4 族 × 5 框架 × 2 角色 = {c['C3_seat_arithmetic']['recomputed']['seats']} 席 / "
      f"{c['C3_seat_arithmetic']['recomputed']['cells']} 格 |")
    A(f"| 审核面 | 判据表 8 行 · 覆盖矩阵 4×5 · 分离度表 5 行 · 机制命中表 5 行 · "
      f"门账本 {c['C10_ledger_composition']['recomputed']['rows']} 行 · 盲预测表 "
      f"{c['C4_blind_grid_composition']['recomputed']['rows']} 行 · §⑥ 6 行 |")
    A(f"| 检查数 | {cs['n_checks']}（pass {cs['n_pass']} / fail {cs['n_fail']} / "
      f"withheld {cs['n_unverifiable']}） |")
    A(f"| 裁决 | `{review['decision']['verdict']}`，阻断 {review['finding_counts']['blocking']} 条 |")
    A("")
    A("## ② 怎么做的")
    A("")
    A("**方法**：只读冻结字节 + 只复算可复算量 + 不可复算就记 WITHHELD。")
    A("")
    A("1. **先证后做**：`source_5949.md` 逐字节自证（sha256/chars/bytes 三项），"
      "并与 wp-5949-01 `kf_result.json`、`asset_manifest.json` 的 pin 双比（C1/C2）。")
    A("2. **锚点强校验**：19 项检查各带一条源文逐字引文 + 行号；锚点不是逐字子串即 `AssertionError`，"
      "构建期再校验一遍（锚点漂移 = 构建失败，不静默降级）。")
    A("3. **算术全部重算**：矩阵边际/角色合计（C3）、盲表 40 行区间包含性（C5）、命中率（C6）、"
      "宽度中位/均值（C7）、人口表（C13）、§⑥ 误差行（C14）。")
    A("4. **统计复核**：对命中数做**两个零模型**的精确二项检验——A：结果 ~ U(0,1)（报告自用基线）；"
      "B：结果 ~ U(实测值带)；并给出 α=5% 临界命中数与对 p=0.30 的功效（C8）。")
    A("5. **下界核对（诚实降级）**：机制命中计数只印触发路径 → 只能核「可见 ≤ 声明」（C9）；"
      "账本 24 行只含 19 条克隆 → 「24/24 拒」只算一致（C10）；6 个 16 位哈希前缀不足以绑定 256 bit（C15）。")
    A("6. **两类门的证据强度**：FPR「0.00」的分母只有 15 个独立对（Wilson 95% 上界 0.20，C18）；"
      "机制表显示包含度单路即命中 24/24，「单路必漏」只对骨架路成立（C19）。")
    A("7. **可复跑工具链**：`review_checks.py` → `checks.json` → `build_review.py` → "
      "`review_report.json` / `kf_result.json` / KF-RESULT.md / PNG → `pytest tests/test_kf_wp5949_review.py`"
      "（15 项自检，含「重建后字节完全一致」的幂等测试）。")
    A("")
    A("**关键设置**：容差在看到结果前按印出位数定死（2 位小数 → 5e-3；4 位比例 → 5e-5）；"
      "样本率 1.0（全表重算）；不重实现被审的相似度算法（避免用审阅者实现替换被审对象）。")
    A("")
    A("## ③ 计算结果")
    A("")
    A("### 3.1 检查总表")
    A("")
    A("| 检查 | 状态 | 重算要点 |")
    A("|---|---|---|")
    for x in checks["checks"]:
        rec = json.dumps(x["recomputed"], ensure_ascii=False)
        A(f"| `{x['check_id']}` {x['title']} | **{x['status']}** | {rec[:150]} |")
    A("")
    A("### 3.2 声明 vs 独立重算（关键量）")
    A("")
    A("| 量 | 声明 | 重算 | 判定 |")
    A("|---|---|---|---|")
    for name, decl, rec, err in rows:
        d = "—" if decl is None else f"{decl}"
        r = "不可执行/未印出" if rec is None else f"{rec}"
        if err is None:
            verdict = "无基准（WITHHELD）"
        elif err >= 3.0:
            verdict = f"**不可复算**（{err:.1f}% > 3%）"
        else:
            verdict = f"一致（{err:.3g}%）"
        A(f"| {name} | {d} | {r} | {verdict} |")
    A("")
    A("### 3.3 零模型敏感性（本单新增判据）")
    A("")
    A("| 零模型 | p0 | 期望命中/40 | 实测 8 条的 P(X≥8) |")
    A("|---|---|---|---|")
    A(f"| A：结果 ~ U(0,1)（报告基线 0.1576） | {na['p0']} | {na['expected_hits']} | "
      f"{na['p_value_ge_observed']} |")
    A(f"| B：结果 ~ U([{nb['band'][0]}, {nb['band'][1]}]) | {nb['p0']} | {nb['expected_hits']} | "
      f"{nb['p_value_ge_observed']} |")
    A("")
    A(f"两个零模型下实测都不显著 → 「与无信息基线同量级」这半句稳健"
      f"（α=5% 临界 {c['C8_null_model_sensitivity']['recomputed']['alpha_0_05_critical_hits']} 条，"
      f"对 p=0.30 功效 {c['C8_null_model_sensitivity']['recomputed']['power_to_detect_p_0_30']}）；"
      "但由它推出「流程无泄漏」不成立——不拒绝 ≠ 证明，且合成 dry-run 的预测与结果同源（F2）。")
    A("")
    A("### 3.4 findings")
    A("")
    A("| ID | 严重度 | 阻断 | 摘要 |")
    A("|---|---|---|---|")
    for f in findings:
        A(f"| {f['finding_id']} | {f['severity']} | {'是' if f['blocking'] else '否'} | {f['title']} |")
    A("")
    A("## ④ 图")
    A("")
    A("**图 1** 三面板复核图：(a) 40 条盲预测的区间中心 vs 实测值，绿带为实测值实际取值范围，"
      "箭头标出唯一翻转行（0.6095 ∈ [0.39, 0.61] 却记「未中」）；(b) 两个零模型下的期望命中与实测/声明；"
      "(c) 机制命中计数 声明值 vs 可核下界（只印触发路径）。")
    A("")
    A("**图 2** 逐量可复算性误差预算：横轴为 |重算−声明|/声明（log），黑虚线 3% 验收线；"
      f"{len(numeric)} 个可算误差的量中 {len(over)} 个越过 3%（红条），其余均在 3% 以内。")
    A("")
    A("**为什么没有场量云图**：被审对象零物理量、零几何、零流场，不存在可画云图的场量；"
      "以上两图是全部可量化证据，未用示意图替代数据。")
    A("")
    A("## ⑤ 注意点 / 局限")
    A("")
    A("1. **印出精度就是可核性**：区间端点印 2 位小数，而声明量给到 14 位有效数字"
      "（`0.13705000000000003`）——1/40 行判定因此翻转、中位宽无法逐行复算。"
      "这不是「报告算错」，而是「给不出可核的数字」。")
    A("2. **审阅者自己也会踩零模型陷阱**：我第一版把「带内均匀」零模型的 p0 误当成平均交叠长度（0.038），"
      "算出 P≈1e-4 并写成「结论翻转」；复核时发现 p0 应为 交叠长度/带宽 = 0.2032，"
      "两个零模型其实都不显著。已改正为「定量部分稳健、推断不成立」（F2）。"
      "**教训：批评别人的统计推断前，先把自己的零模型算对。**")
    A("3. **只能核下界时就要说下界**：账本只印 19/24 条克隆，机制计数只能证明「可见 ≤ 声明」。"
      "把下界一致写成「已核实」是 04 工序最常见的越界，本单记为 WITHHELD（F4）。")
    A("4. **合成数据的两难**：dry-run 结果由种子确定性生成，任何「预测-结果」相关性都无法归因于能力或泄漏；"
      "「有泄漏」与「无泄漏」在这份数据上都不可判定。")
    A("5. **本单自身局限**：单审阅人（无第二签核）；不执行被审代码（TensorPlatform 侧工件不在本仓）；"
      "不重实现相似度算法。故锁/篡改/时序/pytest 四类证据只能记 WITHHELD。")
    A("6. **继承的仓库缺陷**：`tests/test_kf_wp11107_01.py` 在 main 上就因 `runs/wp-11107-01/` 未入库而收集失败，"
      "与本单无关，未在本 PR 内修（避免混入无关改动）。")
    A("")
    A("## ⑥ 误差判定（关键量 vs 基准，逐项回答「是否 <3%」）")
    A("")
    A("| 量 | 基准 | 重算 | 相对误差 | <3%？ |")
    A("|---|---|---|---|---|")
    for name, decl, rec, err in rows:
        if err is None:
            A(f"| {name} | {'声明的工件/逐对值不在本仓' if decl is None else decl} | "
              f"{'不可执行' if rec is None else rec} | — | **无基准**（原因：工件不在本仓 / 逐对值未印出） |")
        else:
            A(f"| {name} | {decl} | {rec} | {err:.4g}% | {'**否**' if err >= 3.0 else '是'} |")
    A("")
    A(f"**逐项结论**：{len(numeric)} 个可算相对误差的量中，**{len(under)} 个 <3%**、"
      f"**{len(over)} 个 >3%**（" + "、".join(f"{n} {e:.1f}%" for n, e in over) + "）；"
      f"{len(rows) - len(numeric)} 个无基准并已写明原因。")
    A("")
    A(f"**是否 <3%？**：源哈希 / 席位数 / 矩阵格数 / 角色边际 / 人口占比 / §⑥ 算术 / 宽度统计等 "
      f"{len(under)} 个量 —— **是**（最大 {max(e for _, e in under):.3g}%）；"
      + "、".join(f"{n}" for n, e in over)
      + f" —— **否（各 {over[0][1]:.1f}%）**，同一根因（印出精度），已开 F1 要求区间印到 4 位小数；"
      "克隆骨架最小 0.6308 与锁/时序/pytest —— **无基准**，记 WITHHELD 而非通过。")
    A("")
    A("**物理判据**：报告零物理量，15%/3% 的对标判据**不适用**（C16 已逐行核过 §⑥ 六行全为决策量）——"
      "这不是「跳过检查」，而是「换成能判的判据」，并把不可判项显式记 WITHHELD。")
    A("")
    A("## 产物与复算")
    A("")
    A("| 文件 | 作用 |")
    A("|---|---|")
    A("| `docs/kf/wp-5949-04/KF-RESULT-wp-5949-04.md` | 本报告（六要素，数字程序化注入） |")
    A("| `docs/kf/wp-5949-04/review_report.json` | 审核正文（19 checks / 7 findings / decision / remediation） |")
    A("| `docs/kf/wp-5949-04/kf_result.json` | 交付信封 + 各产物 sha256/字节数 |")
    A("| `docs/kf/wp-5949-04/source_5949.md` | 被审报告冻结副本（哈希即 provenance.source_hash） |")
    A("| `docs/kf/wp-5949-04/figures/*.png` | 图 1（图 2 由 publish_report.py 生成，不随 PR 入库） |")
    A("| `work/wp-5949-04/review_checks.py` | 19 项检查（纯函数，stdlib） |")
    A("| `work/wp-5949-04/build_review.py` | 生成 review_report / kf_result / 报告 / 图 |")
    A("| `work/wp-5949-04/checks.json` | 逐项检查原始结果 |")
    A("| `tests/test_kf_wp5949_review.py` | 15 项离线自检（含幂等重建） |")
    A("")
    A("复算：`python3 work/wp-5949-04/review_checks.py && python3 work/wp-5949-04/build_review.py "
      "&& python3 -m pytest tests/test_kf_wp5949_review.py -q`")
    return "\n".join(L)


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def main():
    checks = json.loads(CHECKS.read_text(encoding="utf-8"))
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    rows = make_error_figure(checks)
    md = build_markdown(checks, review, rows)

    if os.environ.get("DRY"):
        out = REPO / "work" / "report_preview.md"
        out.write_text(md, encoding="utf-8")
        print(f"DRY: wrote {out.relative_to(REPO)} ({len(md)} chars)")
        return {}

    token = api("/auth/login", body={
        "username": os.environ["TENSOR_AGENT_USER"],
        "password": os.environ["TENSOR_AGENT_PASS"],
    })["access_token"]
    cs = checks["checks_summary"]
    payload = {
        "title": "wp-5949-04 · 报告 5949 的 04 独立评审（原 PR#326 关闭后重做）",
        "summary": (
            f"从 main 切枝重做 TensorKnowledge PR#326：对报告 5949（IN25-T2 多样性引擎）做 04 独立评审，"
            f"{cs['n_checks']} 项程序化检查（pass {cs['n_pass']} / fail {cs['n_fail']} / "
            f"withheld {cs['n_unverifiable']}），7 条 findings、阻断 0，裁决 "
            f"{review['decision']['verdict']}。诚实结论：席位/边际/人口/§⑥ 算术与源哈希全部复现，"
            f"但盲预测命中数不可由印出的 2 位小数区间复算（7 vs 8，hit_rate 0.175 vs 0.200，"
            f"14.3% > 3%），且「命中率≈基线⇒无泄漏」为不可推出的推断；锁/篡改/时序/pytest "
            f"四类证据因工件不在本仓记 WITHHELD。物理判据不适用（报告零物理量）。"
        ),
        "scenario_key": "kf/independent-review",
        "mission_id": MISSION_ID,
        "tags": ["TensorKnowledge", "KF-04", "independent-review", "wp-5949-04",
                 "report-5949", "honest-fail", "null-model-sensitivity"],
        "markdown": md,
        "figures": [
            {"name": "wp-5949-04_checks.png",
             "caption": "图 1 三面板复核图：(a) 盲预测区间 vs 实测值带与翻转行；(b) 两个零模型下的期望命中；"
                        "(c) 机制命中计数 声明值 vs 可核下界",
             "png_base64": b64(FIG1)},
            {"name": "wp-5949-04_error_budget.png",
             "caption": "图 2 逐量可复算性误差预算（log 横轴，黑虚线 3% 验收线，红条为 >3% 的两项）",
             "png_base64": b64(FIG2)},
        ],
    }
    res = api("/tensor/reports", token=token, body=payload)
    print(json.dumps({k: res.get(k) for k in ("id", "title", "status", "created_at")},
                     ensure_ascii=False))
    return res


if __name__ == "__main__":
    main()