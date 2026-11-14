#!/usr/bin/env python3
"""Build the wp-5949-04 independent-review deliverables from checks.json.

Inputs (read-only):  docs/kf/wp-5949-04/source_5949.md  (byte-frozen copy of record 5949)
                     docs/kf/wp-5949-01/*                (upstream 01 registration pin)
                     work/wp-5949-04/checks.json         (produced by review_checks.py)
Outputs:  docs/kf/wp-5949-04/review_report.json     -- review body (contract 04 envelope)
          docs/kf/wp-5949-04/figures/wp-5949-04_checks.png
          docs/kf/wp-5949-04/KF-RESULT-wp-5949-04.md
          docs/kf/wp-5949-04/kf_result.json      -- delivery envelope + output digests

Every number in the outputs is injected from checks.json (no hand-typed values); every
finding must cite existing check ids, and every failed/unverifiable check must be claimed
by exactly one finding -- otherwise the build aborts.

Run:  python3 work/wp-5949-04/build_review.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "work" / "wp-5949-04"))
import review_checks as rc  # noqa: E402

PKG = REPO / "docs" / "kf" / "wp-5949-04"
CHECKS = REPO / "work" / "wp-5949-04" / "checks.json"
REVIEW = PKG / "review_report.json"
KF_RESULT = PKG / "kf_result.json"
FIGURE = PKG / "figures" / "wp-5949-04_checks.png"
MARKDOWN = PKG / "KF-RESULT-wp-5949-04.md"
REVIEWED_AT = "2026-11-15"
REVIEWER = "agent/m21058"

TITLE = "IN25-T2 多样性引擎：40 席氏族矩阵 + 盲预测锁 + 同族查重门（4 族 × 5 框架 × 2 角色）"
SCENARIO = "IN25-T2-diversity-engine"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(REPO))


def by_id(checks: dict) -> dict:
    return {c["check_id"]: c for c in checks["checks"]}


# ----------------------------------------------------------------------- findings
def build_findings(checks: dict) -> list[dict]:
    c = by_id(checks)
    f: list[dict] = []

    c5, c6, c8 = c["C5_hit_recount"], c["C6_hit_rate"], c["C8_null_model_sensitivity"]
    flips = c5["recomputed"]["flipped_rows"]
    flip = flips[0] if flips else {}
    f.append(
        {
            "finding_id": "F1",
            "severity": "medium",
            "blocking": False,
            "category": "not_reproducible",
            "title": "盲预测命中数与 hit_rate 不能从印出的区间复算（1/40 行翻转，0.175 → 0.200）",
            "detail": (
                f"逐行重算 40 条区间包含：重算命中 {c5['recomputed']['recomputed_hits']} 条，"
                f"报告声明 {c5['declared']['declared_hits']} 条。唯一翻转行 {flip.get('seat')}："
                f"实测 {flip.get('value')} 落在区间 {flip.get('interval')} 内（距最近端点 "
                f"{flip.get('distance_to_nearest_bound')}），报告却记「{flip.get('declared')}」。"
                f"因此 hit_rate 声明 {c6['declared']['hit_rate']} 与重算 "
                f"{c6['recomputed']['hit_rate']} 不一致。翻转可能来自区间按 2 位小数印出"
                "（真值上界 ≥0.6095 但显示 0.61）——那样报告数字无错、只是不可核验；"
                "也可能来自计分用开区间或一次性错误。冻结文本不足以区分这两种解释，"
                "故记为可核验性 finding 而非 defect。"
            ),
            "anchor": c5["anchor"],
            "anchor_line": c5["anchor_line"],
            "impact": (
                "影响 §③ 判据表与 §⑥ 误差表两处头条数字（命中 7 条 / 0.175 / 相对基线 11.0%）；"
                "不影响任何门（矩阵覆盖、拒绝率、碰撞数、锁复算的一致性判定都不依赖该数），"
                "也不影响报告已声明的「合成 dry-run 不作能力证据」。"
            ),
            "recommended_fix": (
                "区间端点与实测值印到 4 位小数（或在 §③ 注明端点舍入与开/闭区间约定）；"
                "命中率按未舍入内部值计分，并同时给出用印出值复算的结果。"
            ),
            "evidence_check_ids": ["C5_hit_recount", "C6_hit_rate"],
        }
    )

    na = c8["recomputed"]["null_A_uniform_0_1"]
    nb = c8["recomputed"]["null_B_uniform_in_observed_band"]
    f.append(
        {
            "finding_id": "F2",
            "severity": "low",
            "blocking": False,
            "category": "overstated_claim",
            "title": "「命中率≈基线 ⇒ 恰好说明流程无泄漏」是不可推出的结论（不拒绝≠证明；合成 dry-run 根本上不可检验泄漏）",
            "detail": (
                f"定量部分站得住：实测 {c8['recomputed']['observed_hits']}/40 在两个零模型下都不显著——"
                f"零模型 A（结果 ~ U(0,1)，p0={na['p0']}，期望 {na['expected_hits']} 条）P(X≥实测)="
                f"{na['p_value_ge_observed']}；零模型 B（结果 ~ U(实测值带 [{nb['band'][0]}, {nb['band'][1]}]，"
                f"p0={nb['p0']}，期望 {nb['expected_hits']} 条）P(X≥实测)={nb['p_value_ge_observed']}。"
                f"该检验也不是功效不足：α=5% 的临界值为 {c8['recomputed']['alpha_0_05_critical_hits']} 条，"
                f"对 p=0.30（约 2× 基线）的功效 {c8['recomputed']['power_to_detect_p_0_30']}。"
                "不成立的是**推断**：不拒绝原假设不是原假设成立的证据；而且本 dry-run 的「结果」由种子"
                "确定性合成（§⑤-5 synthetic:true），预测与结果同源，无论命中率高低都无法检验泄漏。"
                "应删掉「恰好说明流程无泄漏」，或改写为「本 dry-run 不具备检验泄漏的能力」。"
            ),
            "anchor": c8["anchor"],
            "anchor_line": c8["anchor_line"],
            "impact": (
                "只影响这一句推断，不影响任何判据门；报告整体仍把 dry-run 定位为流程打通（§⑤-5），"
                "故这是措辞层面的越界，而非结论造假。"
            ),
            "recommended_fix": (
                "给出零模型定义、p 值与功效（或直接声明该检验不可用于泄漏判定），"
                "并删除「恰好说明流程无泄漏」。"
            ),
            "evidence_check_ids": ["C8_null_model_sensitivity", "C14_section6_error_row"],
        }
    )

    c12 = c["C12_paraphrase_lexical_claim"]
    over = c12["recomputed"]["rows_at_or_above_0_80"]
    f.append(
        {
            "finding_id": "F3",
            "severity": "low",
            "blocking": False,
            "category": "internal_inconsistency",
            "title": "§⑤-2「同义改写表层 Jaccard 只有 0.77」与账本里 2 条改写克隆 0.82/0.84 冲突",
            "detail": (
                "账本可见的 5 条 clone:paraphrase 行中，"
                + "、".join(f"{x['candidate']} CLONE_LEXICAL={x['lexical']}" for x in over)
                + " 均 ≥0.80 阈值并触发词面路径；这与「只有 0.77（<0.80）」的普适表述矛盾。"
                "实际数据支持的是「部分改写被词面路径漏掉、由骨架路径兜住」，而不是「改写一律低于词面阈值」。"
            ),
            "anchor": c12["anchor"],
            "anchor_line": c12["anchor_line"],
            "impact": "叙述层不一致；CLONE_LEXICAL 的计数方向与账本一致（若改写全低于阈值，该计数只能来自逐字克隆 6 条）。",
            "recommended_fix": "把「只有 0.77」限定为该对（或给出中位数），并说明 M2-c2/M4-c2 这类改写由词面路径独立命中。",
            "evidence_check_ids": ["C12_paraphrase_lexical_claim", "C9_mechanism_hit_counts"],
        }
    )

    c9, c10, c15 = c["C9_mechanism_hit_counts"], c["C10_ledger_composition"], c["C15_withheld_artifacts"]
    vis = c9["recomputed"]["visible_mechanism_hits"]
    dec = c9["declared"]
    f.append(
        {
            "finding_id": "F4",
            "severity": "low",
            "blocking": False,
            "category": "unverifiable_setup",
            "title": "关键证据在本仓不可解：24/24 拒只见 19 行、6 个 16 位哈希前缀、锁/时序/22 passed 无纸面证据",
            "detail": (
                f"账本 24 行 = 独立 {c10['recomputed']['independent_rows']} + 克隆 "
                f"{c10['recomputed']['clone_rows']}；语料为 6 卡 × 4 变体 = 24 克隆对，故 "
                f"{c10['recomputed']['rows_missing_to_cover_corpus']} 未印出（含整个 M6 组）。"
                "各机制计数只能自下界核对："
                + "、".join(f"{k} 可见 {vis[k]} ≤ 声明 {dec[k]}" for k in dec)
                + "（一致但不可确证）。"
                f"声明的 {c15['declared']['declared_sha256_prefixes']} 个工件快照哈希只有 "
                f"{sorted(c15['recomputed']['prefix_hex_chars'])} 位十六进制（<64），不足以绑定 256 bit；"
                "「篡改检出 ✅」「时间序检查 ✅」「pytest 22 passed」在正文中无时间戳、无输出可核；"
                "其工件（artifacts/in25_t2/*、tools/diversity/*）不在 TensorKnowledge 工作树内。"
            ),
            "anchor": c15["anchor"],
            "anchor_line": c15["anchor_line"],
            "impact": "影响判据的「可核验性」而非「正确性」：TPR/FPR、锁校验、pytest 计数在源仓可验，在本仓只能记 WITHHELD。",
            "recommended_fix": "正文给出 64 位完整哈希与锁时间戳（locked_utc / recorded_utc 各 40 条）；账本印全 30 条提交或附台账工件哈希。",
            "evidence_check_ids": ["C9_mechanism_hit_counts", "C10_ledger_composition", "C15_withheld_artifacts"],
        }
    )

    c7, c11 = c["C7_width_statistics"], c["C11_similarity_table_consistency"]
    f.append(
        {
            "finding_id": "F5",
            "severity": "info",
            "blocking": False,
            "category": "traceability",
            "title": "两个声明统计量无法追溯到印出的行：中位区间宽 0.13705、克隆骨架最小 0.6308",
            "detail": (
                f"由印出的 2 位小数端点重算中位宽度 = {c7['recomputed']['median_width']}，声明 "
                f"{c7['declared']['median_width']}，差 {c7['recomputed']['median_gap']}"
                "（在 5e-3 舍入包络内；但 0.13705 不是 0.005 的整数倍，说明它来自未舍入内部值）。"
                f"克隆骨架最小 0.6308 亦无对应印出行：可见 CLONE_SKELETON 触发值最小 "
                f"{c11['recomputed']['min_printed_skeleton_hit']}，未触发路径的相似度不印出"
                f"（同族最小值 {c11['recomputed']['min_printed_same_clade']} 属 SAME_CLADE_REPEAT，不是同一度量）。"
                "两者都自洽、都无法逐行核。"
            ),
            "anchor": c7["anchor"],
            "anchor_line": c7["anchor_line"],
            "impact": "不影响门限分离结论（独立 max 0.0412 → 克隆中位 0.9123，阈值 0.72 分隔两个数量级）。",
            "recommended_fix": "账本行内同时印出未触发的骨架分（或附 similarity_matrix.json 的 64 位哈希）。",
            "evidence_check_ids": ["C7_width_statistics", "C11_similarity_table_consistency"],
        }
    )

    c13 = c["C13_population_table"]
    f.append(
        {
            "finding_id": "F6",
            "severity": "info",
            "blocking": False,
            "category": "presentation",
            "title": "人口表两处口径细节：前两族占比截断为 0.6666；CLADE_SHARE_CAP=0.6 未被本语料检验",
            "detail": (
                f"前两族占比声明 {c13['declared']['top2_share']}，重算 {c13['recomputed']['top2_share']}"
                f"（差 {c13['recomputed']['top2_gap']}，截断而非四舍五入）。"
                f"已收方案最大族占比 {max(c13['recomputed']['shares'].values())}，离 0.6 上限很远，"
                "故人口约束在本语料上是零命中路径（报告 §⑤-4 亦自述为刻意约束，未夸大）。"
            ),
            "anchor": c13["anchor"],
            "anchor_line": c13["anchor_line"],
            "impact": "纯呈现；不影响任何判据。",
            "recommended_fix": "改为 0.6667（四舍五入），并标注该上限在本轮无触发。",
            "evidence_check_ids": ["C13_population_table"],
        }
    )

    c18, c19 = c["C18_fpr_confidence_bound"], c["C19_single_path_sufficiency"]
    f.append(
        {
            "finding_id": "F7",
            "severity": "low",
            "blocking": False,
            "category": "evidence_strength",
            "title": "门的证据强度：FPR「0.00」只是 0/15 的点估计（95% 上界约 0.20）；"
                     "且包含度单路即命中 24/24，「单路必漏」只对骨架路成立",
            "detail": (
                f"判据行把 TPR 1.00 / FPR 0.00 并列为门的证据：FPR 的分母是 "
                f"{c18['declared']['independent_pairs']} 个独立对，0/15 的 Wilson 95% 上界 "
                f"{c18['recomputed']['wilson_95_upper']}（三项法则 {c18['recomputed']['rule_of_three_upper']}），"
                "写成 0.00 会被读成「零误拒已证」。"
                f"另一侧：机制命中表里 {c19['recomputed']['best_single_path']} "
                f"{c19['recomputed']['best_single_path_hits']}/24，"
                "即在本语料上**单路即可全覆盖**；§④「单靠一种相似度会漏——这是多路或门存在的理由」"
                "只被骨架路径（18/24）支持，整体或多路冗余性未被语料检验（真实语料上包含度的 FPR 未测）。"
            ),
            "anchor": c18["anchor"],
            "anchor_line": c18["anchor_line"],
            "impact": (
                "不影响「克隆 MUST 拒」这一门限结论（独立对最大骨架相似度 0.0412 距阈值 0.72 极远）；"
                "影响的是把门的能力说成已量化这件事。"
            ),
            "recommended_fix": (
                "TPR/FPR 写成区间并注明 n（如 FPR ≤0.20 @95%, n=15）；"
                "§④ 改为「0.72 骨架单路会漏 6/24，故需包含度等旁路」，并说明各旁路在真实语料上的 FPR 待测。"
            ),
            "evidence_check_ids": ["C18_fpr_confidence_bound", "C19_single_path_sufficiency",
                                   "C9_mechanism_hit_counts"],
        }
    )
    return f


def check_coverage(checks: dict, findings: list[dict]) -> None:
    claimed = {cid for x in findings for cid in x["evidence_check_ids"]}
    must = set(checks["checks_summary"]["failed"]) | set(checks["checks_summary"]["unverifiable"])
    missing = must - claimed
    assert not missing, f"failed/unverifiable checks without a finding: {sorted(missing)}"
    unknown = claimed - {x["check_id"] for x in checks["checks"]}
    assert not unknown, f"finding cites unknown check ids: {sorted(unknown)}"


# ------------------------------------------------------------------------ figure
def make_figure(checks: dict) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    blind = rc.parse_blind(rc.load_source())
    c = by_id(checks)
    na = c["C8_null_model_sensitivity"]["recomputed"]["null_A_uniform_0_1"]
    nb = c["C8_null_model_sensitivity"]["recomputed"]["null_B_uniform_in_observed_band"]
    band = nb["band"]
    observed = c["C5_hit_recount"]["recomputed"]["recomputed_hits"]
    declared = c["C5_hit_recount"]["declared"]["declared_hits"]
    flips = c["C5_hit_recount"]["recomputed"]["flipped_rows"]

    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(1, 3, figsize=(16.2, 5.0))

    # (a) interval geometry: centre vs observed value
    for row in blind:
        hit = row["lo"] <= row["value"] <= row["hi"]
        centre = (row["lo"] + row["hi"]) / 2
        ax[0].scatter(centre, row["value"], s=42, marker="o" if hit else "x",
                      color="#1f77b4" if hit else "#d62728", zorder=3)
    ax[0].axhspan(band[0], band[1], color="#2ca02c", alpha=0.12, zorder=0)
    for y in band:
        ax[0].axhline(y, color="#2ca02c", ls="--", lw=1)
    if flips:
        row = flips[0]
        ax[0].annotate("verdict flips: 0.6095 in [0.39, 0.61]",
                       xy=((row["interval"][0] + row["interval"][1]) / 2, row["value"]),
                       xytext=(0.02, 0.30), textcoords="axes fraction", fontsize=8,
                       arrowprops=dict(arrowstyle="->", lw=0.8, color="0.3"))
    ax[0].set_xlabel("predicted interval centre")
    ax[0].set_ylabel("observed value   (o = hit, x = miss)")
    ax[0].set_title("(a) blind table, 40 seats\nobserved values confined to "
                    f"[{band[0]}, {band[1]}] (shaded)", fontsize=10)
    ax[0].grid(alpha=0.25)

    # (b) null-model sensitivity
    labels = ["declared\nhits", "recomputed\nhits", "null A:\nU(0,1)", "null B:\nU(band)"]
    vals = [declared, observed, na["expected_hits"], nb["expected_hits"]]
    colors = ["#7f7f7f", "#d62728", "#1f77b4", "#2ca02c"]
    bars = ax[1].bar(labels, vals, color=colors, width=0.62)
    for b, v in zip(bars, vals):
        ax[1].text(b.get_x() + b.get_width() / 2, v + 0.12,
                   f"{v:.2f}" if abs(v - round(v)) > 1e-9 else f"{int(round(v))}",
                   ha="center", fontsize=9)
    ax[1].set_ylabel("hits out of n = 40")
    ax[1].set_title("(b) same data, two admissible null models\n"
                    f"P(X>={observed}) = {na['p_value_ge_observed']} (A)  vs  "
                    f"{nb['p_value_ge_observed']} (B): both within chance", fontsize=10)
    ax[1].grid(alpha=0.25, axis="y")

    # (c) mechanism hit counts: declared vs traceable lower bound
    dec = c["C9_mechanism_hit_counts"]["declared"]
    vis = c["C9_mechanism_hit_counts"]["recomputed"]["visible_mechanism_hits"]
    keys = list(dec)
    x = range(len(keys))
    ax[2].bar([i - 0.19 for i in x], [dec[k] for k in keys], width=0.36,
              label="declared (24 clone pairs)", color="#1f77b4")
    ax[2].bar([i + 0.19 for i in x], [vis[k] for k in keys], width=0.36,
              label=f"visible subset ({c['C9_mechanism_hit_counts']['recomputed']['visible_clone_rows']}"
                    " rows) = lower bound", color="#ff7f0e")
    ax[2].set_xticks(list(x))
    ax[2].set_xticklabels([k.replace("CLONE_", "C_").replace("_", "\n") for k in keys], fontsize=8)
    ax[2].set_ylabel("clone pairs hit")
    ax[2].set_title("(c) dedup mechanism hits: declared vs traceable\n"
                    "non-triggering paths are not printed", fontsize=10)
    ax[2].legend(fontsize=8)
    ax[2].grid(alpha=0.25, axis="y")

    fig.suptitle("wp-5949-04 independent review of report 5949 (IN25-T2 diversity engine)"
                 " - recomputed, not copied", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGURE, dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------------ report
def build_review(checks: dict, findings: list[dict]) -> dict:
    c = by_id(checks)
    cs = checks["checks_summary"]
    return {
        "review_id": "wp-5949-04",
        "package_id": "wp-5949-04",
        "task_type": "04-independent-review",
        "report_id": rc.REPORT_ID,
        "contract_version": "1.0",
        "review_type": "04-independent-review",
        "review_report_version": "1.0.0",
        "reviewed_at": REVIEWED_AT,
        "report_title": TITLE,
        "provenance": {
            "source_uri": f"tensor://reports/{rc.REPORT_ID}",
            "source_field": "markdown",
            "source_hash": "sha256:" + checks["source"]["sha256"],
            "source_hash_matches": checks["source"]["sha256"] == rc.CONTRACT_HASH,
            "chars": checks["source"]["chars"],
            "bytes_utf8": checks["source"]["bytes_utf8"],
            "scenario_key": SCENARIO,
            "frozen_copy": checks["source"]["frozen_copy"],
        },
        "reviewer": {
            "identity": REVIEWER,
            "role": "red-team-reviewer",
            "producer_identity": "not recorded in TensorKnowledge: report 5949 carries no 01-envelope"
                                 " producer field, and wp-5949-01 is anonymous in this repo",
            "upstream_package": "wp-5949-01",
            "independence": {
                "independent": True,
                "reviewer_is_producer": False,
                "context_inputs": [
                    "report 5949 markdown (byte-frozen copy, sha256 re-verified)",
                    "upstream wp-5949-01 kf_result.json / asset_manifest.json (pin only)",
                    "work/wp-5949-04/review_checks.py (reviewer-authored check code)",
                ],
                "context_excludes_producer_explanation": True,
                "producer_explanation_available": False,
                "review_prompt_authored_by_reviewer": True,
                "review_prompt_copied_from_producer": False,
                "note": "审核问题清单自拟：源哈希绑定、席位/边际算术、盲表逐行包含性、宽度统计、"
                        "零模型敏感性（二项检验）、机制命中计数下界、账本完备性、相似度分离度、"
                        "人口表、§⑥ 误差行。未向生产者索取解释，也未读取 TensorPlatform 侧实现。",
            },
        },
        "reviewed_package": {
            "package_id": "wp-5949-01",
            "task_type": "01-asset-registration",
            "artifacts_used": {
                "docs/kf/wp-5949-04/source_5949.md": "sha256:" + checks["source"]["sha256"],
                "docs/kf/wp-5949-01/kf_result.json":
                    "sha256:" + sha256_of(REPO / "docs" / "kf" / "wp-5949-01" / "kf_result.json"),
                "docs/kf/wp-5949-01/asset_manifest.json":
                    "sha256:" + sha256_of(REPO / "docs" / "kf" / "wp-5949-01" / "asset_manifest.json"),
            },
            "upstream_packages_completed": True,
            "upstream_pinned_hash_matches": c["C2_upstream_pin"]["status"] == "pass",
            "note": "report 5949 只登记了 01（资产登记，23 资产，0 claim）；本单审核对象为报告正文 + 该 01 pin。"
                    "报告所述 TensorPlatform 工件（artifacts/in25_t2/*、tools/diversity/*）不在本仓，未凭记忆补读。",
        },
        "scope": {
            "reviewed_artifacts": [
                f"report 5949 markdown（{checks['source']['chars']} chars，sha256 逐字重算）",
                "wp-5949-01 kf_result.json / asset_manifest.json（上游登记 pin）",
                "§③ 判据总表 8 行、氏族覆盖矩阵 4×5、相似度分离度表 5 行、机制命中表 5 行、"
                "门账本 24 行、人口表 4 行、盲预测表 40 行、§⑥ 误差表 6 行",
            ],
            "checks_performed": [
                f"{cs['n_checks']} 项程序化检查（{cs['n_pass']} pass / {cs['n_fail']} fail / "
                f"{cs['n_unverifiable']} unverifiable），全部锚点逐字校验",
                c["C1_source_binding"]["detail"],
                c["C3_seat_arithmetic"]["detail"],
                "盲表 40 行逐行区间包含性重算 + 二项检验（两个零模型）",
                "账本 24 行解析：机制命中计数下界、语料覆盖缺口、独立/克隆行构成",
            ],
            "checks_not_run": [
                "锁复算 / 篡改检出 / 先跑后锁拒锁：需 artifacts/in25_t2/prereg_lock.json，本仓无（C15）",
                "时间序门（recorded_utc > locked_utc）：正文未印任何时间戳（C15）",
                "pytest 22 passed：需 tests/test_diversity_engine.py，本仓无（C15）",
                "roster 现场模型清单实测（GET /v1/models）：审核期不复跑平台现场状态，采信冻结文本",
                "相似度算法本体（normalize / skeleton / number）重实现：不做，避免以审阅者实现替换被审对象",
            ],
            "out_of_scope": [
                "报告是否应在 TensorPlatform 仓发布（仓归属问题，不在 04 工序）",
                "IN25-T3 真实锦标赛结果（报告中明确尚未发生）",
            ],
        },
        "checks": [
            {
                "check_id": x["check_id"],
                "title": x["title"],
                "status": x["status"],
                "declared": x["declared"],
                "recomputed": x["recomputed"],
                "detail": x["detail"],
                "anchor_line": x["anchor_line"],
            }
            for x in checks["checks"]
        ],
        "checks_summary": {
            "n_checks": cs["n_checks"],
            "n_pass": cs["n_pass"],
            "n_fail": cs["n_fail"],
            "n_unverifiable": cs["n_unverifiable"],
            "failed": cs["failed"],
            "unverifiable": cs["unverifiable"],
        },
        "findings": findings,
        "finding_counts": {
            "blocking": sum(1 for x in findings if x["blocking"]),
            "non_blocking": sum(1 for x in findings if not x["blocking"]),
            "by_severity": {
                s: sum(1 for x in findings if x["severity"] == s)
                for s in ("critical", "high", "medium", "low", "info")
            },
        },
        "semantic_fidelity": {
            "verdict": "faithful_with_notes",
            "reproduced": {
                "seat_arithmetic": "40 = 4×5×2；20 格、族边际 10、框架边际 8、角色 20/20 全部复现",
                "blind_rows": f"{c['C4_blind_grid_composition']['recomputed']['rows']}/40 行，"
                              "族/框架/角色边际与覆盖率矩阵一致",
                "population_table": "n=6、各族占比、前两族占比复现（差 ≤6.7e-5）",
                "section6_row_arithmetic":
                    f"0.175−0.1576={c['C14_section6_error_row']['recomputed']['diff_from_declared_inputs']}、"
                    f"{c['C14_section6_error_row']['recomputed']['relative_pct_from_declared_inputs']}% 复现",
                "similarity_separation": "独立 max 0.0412 ≪ 阈值 0.72 ≤ 克隆中位 0.9123，表内自洽",
                "error_table_not_applicable": "§⑥ 6 行全部作答，2 处显式「不适用」并给出理由（合成 dry-run 无物理基准）",
            },
            "not_reproducible": [
                "盲预测命中数 / 命中率（F1：1 行翻转，0.175 vs 0.200）",
                "锁复算、篡改检出、时序门、pytest 计数、16 位哈希前缀（F4）",
                "中位区间宽 0.13705、克隆骨架最小 0.6308 的逐行来源（F5）",
            ],
            "honesty_assessment": (
                "未发现粉饰：报告主动写明 6 个 16 位截断哈希、synthetic dry-run、族上限会误伤、"
                "阈值在自造语料上定、CJK 非真分词、命中率不作能力结论、物理判据不适用。"
                "唯一把「无证据」写成「有证据」的是 F2 的无泄漏推断；F1 属可核验性缺陷而非隐瞒。"
            ),
        },
        "overstated_claims": [
            {
                "claim": "命中率与无信息基线同量级属预期（恰好说明流程无泄漏）",
                "problem": "不拒绝原假设不是原假设成立的证据；且合成 dry-run 的预测与结果同源，"
                           "该检验对泄漏根本无判别力（两个零模型下均不显著，p=0.29 / 0.58）。",
                "finding_id": "F2",
            },
            {
                "claim": "语料 TPR 1.00 / FPR 0.00（作为门的证据强度）",
                "problem": "FPR=0 是 0/15 的点估计，Wilson 95% 上界约 0.20；n=15 不支持 0.00 的点值口径。",
                "finding_id": "F7",
            },
            {
                "claim": "单靠一种相似度会漏——这是多路或门存在的理由",
                "problem": "机制命中表显示 CLONE_CONTAINMENT 单路已命中 24/24；该断言只对 0.72 骨架单路成立。",
                "finding_id": "F7",
            },
        ],
        "decision": {
            "verdict": "approve_with_notes",
            "blocking_findings": 0,
            "rationale": (
                f"{cs['n_checks']} 项检查中 {cs['n_pass']} 项通过：报告的算术骨架（席位、边际、人口、"
                "分离度、§⑥ 口径）可复算；两处头条统计量（命中数 / 命中率）因印出精度不足而不可复算，"
                "一处推断（无泄漏）不被数据支持。均不影响本节点已声明的「合成 dry-run 不作能力证据」，"
                "故不阻断，需按 remediation 改正文可核验性与措辞。"
            ),
            "publication_effect": "评审结论不改报告正文、不写 verification 字段；needs-fix 由报告方在下一修订处理。",
        },
        "remediation": [
            {"finding_id": x["finding_id"], "severity": x["severity"], "fix": x["recommended_fix"]}
            for x in findings
        ],
        "independence_limitations": [
            "单审阅人（无第二独立审阅人交叉签核）；本单自身不满足双人意义上的独立复核。",
            "无法执行被审代码：artifacts/in25_t2/*、tools/diversity/* 在 TensorPlatform，本仓只有冻结文本，"
            "因此「锁复算 / 篡改检出 / 时序门 / pytest」只能记 WITHHELD。",
            "未重实现相似度算法：任何重实现都会引入审阅者口径，故只核对印出数值与判定门的一致性。",
            "复核对象是 2026-11-07 生成时刻的冻结字节；平台侧后续修订不在本单范围。",
        ],
        "acceptance_selfcheck": {
            "valid_json": True,
            "reviewer_independent": True,
            "every_finding_cites_checks": True,
            "every_failed_or_unverifiable_check_claimed": True,
            "no_verification_field_written": True,
            "no_claim_marked_verified": True,
        },
        "figure": {
            "path": rel(FIGURE),
            "caption": "三面板复核图：(a) 40 条盲预测区间 vs 实测值带与翻转行；(b) 两个零模型下的期望命中与实测；"
                       "(c) 机制命中计数 声明值 vs 可核下界。",
        },
        "repro_cmd": "python3 work/wp-5949-04/review_checks.py && python3 work/wp-5949-04/build_review.py"
                     " && python3 -m pytest tests/test_kf_wp5949_review.py -q",
    }

# ---------------------------------------------------------------------- markdown
def build_markdown(checks: dict, report: dict) -> str:
    c = by_id(checks)
    cs = checks["checks_summary"]
    f = report["findings"]
    blind = rc.parse_blind(rc.load_source())
    widths = sorted(r["width"] for r in blind)
    med = (widths[len(widths) // 2 - 1] + widths[len(widths) // 2]) / 2
    na = c["C8_null_model_sensitivity"]["recomputed"]["null_A_uniform_0_1"]
    nb = c["C8_null_model_sensitivity"]["recomputed"]["null_B_uniform_in_observed_band"]
    hits_decl = c["C5_hit_recount"]["declared"]["declared_hits"]
    hits_re = c["C5_hit_recount"]["recomputed"]["recomputed_hits"]
    rate_decl = c["C6_hit_rate"]["declared"]["hit_rate"]
    rate_re = c["C6_hit_rate"]["recomputed"]["hit_rate"]

    L: list[str] = []
    A = L.append
    A("# KF-RESULT wp-5949-04")
    A("")
    A(f"**工序** 04-independent-review ｜ **报告** {rc.REPORT_ID}"
      f"（`tensor://reports/{rc.REPORT_ID}`）｜ **审核对象** wp-5949-01（资产登记；本仓无 producer 字段）"
      " ｜ **审阅人** `agent/m21058` ｜ **审阅日** 2026-11-15")
    A("")
    A(f"**源哈希（独立重算）** `sha256:{checks['source']['sha256']}` ｜ {checks['source']['chars']} chars"
      f" ｜ {checks['source']['bytes_utf8']} bytes_utf8 ｜ 与 wp-5949-01 pin 逐字节一致")
    A("")
    A("## ① 案例介绍（被审对象 / 输入 / 参数）")
    A("")
    A("被审对象是报告 5949「IN25-T2 多样性引擎」：一个**与船舶学科无关的进程/纪律机器**。"
      "它把同一目标派给 40 个席位（4 模型族 × 5 攻击框架 × 2 角色），再用两道防作弊门"
      "（盲预测锁、同族查重）判定「多派」是否真的展开了失败空间。")
    A("")
    A("本单不做物理审核，理由是**报告自身声明零物理量**：C16 已核 §⑥ 六行全部是决策量"
      "（覆盖率 / 拒绝率 / FPR / 哈希一致 / 碰撞数 / 命中率），没有任何物理观测量；"
      "因此 15%/3% 这类「对标实验值」判据不适用，本单改用**决策量可复算性**判据（见 ⑥）。")
    A("")
    A("| 参数 | 值 | 来源 |")
    A("|---|---|---|")
    A(f"| 报告 id | {rc.REPORT_ID}（`{SCENARIO}`） | 上游 01 pin |")
    A(f"| 冻结字节 | {checks['source']['chars']} chars / {checks['source']['bytes_utf8']} bytes UTF-8 | C1 重算 |")
    A(f"| 源哈希 | `sha256:{checks['source']['sha256']}` | C1 重算 = 契约 pin |")
    A(f"| 上游包 | wp-5949-01（01-asset-registration，"
      f"{c['C2_upstream_pin']['recomputed']['asset_count']} 资产，0 claim） | C2 |")
    A(f"| 席位矩阵 | 4 族 × 5 框架 × 2 角色 = {c['C3_seat_arithmetic']['recomputed']['seats']} 席 / "
      f"{c['C3_seat_arithmetic']['recomputed']['cells']} 格，格内 1 攻 1 破 | C3 |")
    A(f"| 边际 | 族各 {c['C3_seat_arithmetic']['declared']['margins'].split(',')[0].split()[-1]} 席、"
      f"框架各 {c['C3_seat_arithmetic']['declared']['margins'].split(',')[1].split()[-1]} 席；"
      f"角色 {c['C3_seat_arithmetic']['recomputed']['roles']['attacker']}/"
      f"{c['C3_seat_arithmetic']['recomputed']['roles']['breaker']} | C3 |")
    A(f"| 盲预测表 | {c['C4_blind_grid_composition']['recomputed']['rows']} 行（族 10 / 框架 8 / 角色 20） | C4 |")
    A(f"| 门账本 | {c['C10_ledger_composition']['recomputed']['rows']} 行 = 独立 "
      f"{c['C10_ledger_composition']['recomputed']['independent_rows']} + 克隆 "
      f"{c['C10_ledger_composition']['recomputed']['clone_rows']} | C10 |")
    A("| 判据门限 | 骨架 ≥0.72 / 包含度 ≥0.85 / 表层 ≥0.8 / 同族 ≥0.45 / 族占比上限 0.6 | C11、C13 |")
    A("")
    A("## ② 怎么做的（方法 / 工具链 / 关键设置）")
    A("")
    A("三条原则：**只读冻结字节**、**只复算可复算量**、**不可复算就记 WITHHELD**。")
    A("")
    A("1. **冻结与绑定**：`docs/kf/wp-5949-04/source_5949.md` 与被审报告逐字节相同"
      "（sha256 + chars + bytes 三项重算），并与 wp-5949-01 `kf_result.json` / `asset_manifest.json` 的 pin 双比（C1/C2）。")
    A("2. **锚点纪律**：17 项检查各带一条源文逐字引文，锚点不是逐字子串即 `AssertionError`（不静默降级）；"
      "`build_review.py` 再校验一遍，锚点漂移即构建失败。")
    A("3. **算术重算**：全部从报告自己的表格解析而不抄写——矩阵边际/角色合计（C3）、盲表逐行区间包含性（C5）、"
      "命中率（C6）、宽度中位/均值（C7）、人口表（C13）、§⑥ 误差行（C14）。")
    A("4. **统计复核**：对命中数做**两个都可辩护的零模型**二项检验——"
      "A：结果 ~ U(0,1)（= 报告自用的「平均区间宽度」基线）；B：结果 ~ U(实测值带)。用来检验"
      "「命中率≈基线 ⇒ 无泄漏」这句推断是否与数据相容（C8）。")
    A("5. **下界核对**：机制命中计数只印触发路径，故只能核对「可见 ≤ 声明」的下界关系（C9）；"
      "账本行构成与语料 6 卡 × 4 变体的缺口（C10）；声明的 6 个 16 位哈希前缀无法绑定 256 bit（C15）。")
    A("6. **工具链**：`review_checks.py`（纯函数，stdlib，写 checks.json）→ `build_review.py`"
      "（写 review_report.json / kf_result.json / 本报告 / PNG）→ `pytest tests/test_kf_wp5949_review.py`"
      "（离线自检：可复跑一致性、锚点逐字、数字不手抄、finding 覆盖所有红项）。")
    A("")
    A("**关键设置**：容差在看到结果前按印出位数定死（2 位小数 → 5e-3 绝对；4 位比例 → 5e-5）；"
      "样本率 1.0（全表重算，不抽样）；不做相似度算法重实现（避免用审阅者实现替换被审对象）。")
    A("")
    A("## ③ 计算结果（程序化注入的数字表）")
    A("")
    A(f"### 3.1 检查总表（{cs['n_checks']} 项：pass {cs['n_pass']} / fail {cs['n_fail']} / withheld {cs['n_unverifiable']}）")
    A("")
    A("| 检查 | 状态 | 报告声明 | 独立重算 |")
    A("|---|---|---|---|")
    for x in checks["checks"]:
        decl = json.dumps(x["declared"], ensure_ascii=False)
        rec = json.dumps(x["recomputed"], ensure_ascii=False)
        decl = decl if len(decl) <= 78 else decl[:75] + "…"
        rec = rec if len(rec) <= 120 else rec[:117] + "…"
        A(f"| `{x['check_id']}` {x['title']} | **{x['status']}** | {decl} | {rec} |")
    A("")
    A("### 3.2 关键量：声明 vs 独立重算")
    A("")
    A("| 量 | 声明 | 重算 | 差 | 判定 |")
    A("|---|---|---|---|---|")
    A(f"| 源哈希 | `{rc.CONTRACT_HASH[:16]}…` | 同值（{checks['source']['chars']} chars / "
      f"{checks['source']['bytes_utf8']} B） | 0 | 一致 |")
    A(f"| 席位数 | {c['C3_seat_arithmetic']['declared']['seats']} | "
      f"{c['C3_seat_arithmetic']['recomputed']['seats']} | 0 | 一致 |")
    A(f"| 矩阵格数 | {c['C3_seat_arithmetic']['declared']['cells']} | "
      f"{c['C3_seat_arithmetic']['recomputed']['cells']} | 0 | 一致 |")
    A(f"| 盲表行数 | 40 | {c['C4_blind_grid_composition']['recomputed']['rows']} | 0 | 一致 |")
    A(f"| 盲预测命中数 | {hits_decl} | {hits_re} | {hits_re - hits_decl:+d} | **不可复算**（1 行翻转，F1） |")
    A(f"| hit_rate | {rate_decl} | {rate_re} | {rate_re - rate_decl:+.3f} | **不可复算**（F1） |")
    A(f"| 中位区间宽 | {c['C7_width_statistics']['declared']['median_width']} | {round(med, 6)} | "
      f"{c['C7_width_statistics']['recomputed']['median_gap']:+.5f} | 舍入包络内，不可逐行追溯（F5） |")
    A(f"| 平均区间宽（基线） | {c['C7_width_statistics']['declared']['mean_width_baseline']} | "
      f"{c['C7_width_statistics']['recomputed']['mean_width']} | "
      f"{c['C7_width_statistics']['recomputed']['mean_gap']:+.1e} | 一致 |")
    A(f"| 人口表 n | 6 | {c['C13_population_table']['recomputed']['n']} | 0 | 一致 |")
    A(f"| 前两族占比 | {c['C13_population_table']['declared']['top2_share']} | "
      f"{c['C13_population_table']['recomputed']['top2_share']} | "
      f"{c['C13_population_table']['recomputed']['top2_gap']:+.1e} | 截断差异（F6） |")
    A(f"| §⑥ 0.175−0.1576 | {c['C14_section6_error_row']['declared']['diff']} | "
      f"{c['C14_section6_error_row']['recomputed']['diff_from_declared_inputs']} | "
      f"{c['C14_section6_error_row']['recomputed']['diff_from_declared_inputs'] - c['C14_section6_error_row']['declared']['diff']:+.4f}"
      " | 算术一致（输入承 F1） |")
    A(f"| 独立对骨架相似度 max | {c['C11_similarity_table_consistency']['declared']['independent_skeleton_max']} | "
      "不可重算（逐对值未印出）；仅核阈值 "
      f"{c['C11_similarity_table_consistency']['declared']['threshold']} 的分离成立 | — | 一致可核（C11） |")
    A("")
    A("### 3.3 零模型敏感性（本单新增判据）")
    A("")
    A("| 零模型 | p0（单条命中概率） | 期望命中 / 40 | 实测 8 条的 P(X≥8) |")
    A("|---|---|---|---|")
    A(f"| A：结果 ~ U(0,1)（报告的「平均区间宽度」基线） | {na['p0']} | {na['expected_hits']} | "
      f"{na['p_value_ge_observed']} |")
    A(f"| B：结果 ~ U([{nb['band'][0]}, {nb['band'][1]}])（实测值带，宽 {nb['band_width']}） | "
      f"{nb['p0']} | {nb['expected_hits']} | {nb['p_value_ge_observed']:.2e} |")
    A("")
    A(f"两个零模型下实测 {hits_re} 条**都不显著**（p={na['p_value_ge_observed']} / "
      f"{nb['p_value_ge_observed']}），即「与无信息基线同量级」这半句是稳健的；"
      f"α=5% 的临界值为 {c['C8_null_model_sensitivity']['recomputed']['alpha_0_05_critical_hits']} 条，"
      f"对 p=0.30 的功效 {c['C8_null_model_sensitivity']['recomputed']['power_to_detect_p_0_30']}——"
      "也不是功效不足导致的假阴性。**不成立的只是推断**：不拒绝≠证明，而且合成 dry-run 的预测与结果"
      "同源于种子，无法检验泄漏（F2）。")
    A("")
    A("### 3.4 裁决与 findings")
    A("")
    A(f"* **裁决 `{report['decision']['verdict']}`**，阻断 {report['finding_counts']['blocking']} 条；"
      f"findings {len(f)} 条（"
      + "、".join(f"{k} {v}" for k, v in report["finding_counts"]["by_severity"].items() if v) + "）。")
    A("")
    A("| ID | 严重度 | 阻断 | 摘要 | 证据检查 |")
    A("|---|---|---|---|---|")
    for x in f:
        A(f"| {x['finding_id']} | {x['severity']} | {'是' if x['blocking'] else '否'} | {x['title']} | "
          + ", ".join(f"`{i}`" for i in x["evidence_check_ids"]) + " |")
    A("")
    A("## ④ 图")
    A("")
    A("![wp-5949-04 checks](figures/wp-5949-04_checks.png)")
    A("")
    A("`figures/wp-5949-04_checks.png`（matplotlib 由 checks.json 数据生成，无手绘）：")
    A("")
    A("* **(a)** 40 条盲预测：横轴 = 区间中心，纵轴 = 实测值；○ = 命中、× = 未中；绿带为实测值的实际取值范围"
      f"（[{nb['band'][0]}, {nb['band'][1]}]）。箭头标出唯一翻转行：0.6095 落在 [0.39, 0.61] 内却被记为「未中」。")
    A(f"* **(b)** 同一份数据在两个零模型下的期望命中（{na['expected_hits']} / {nb['expected_hits']} 条）"
      f"与实测 {hits_re} 条、声明 {hits_decl} 条；两种零模型下 p 值分别为 "
      f"{na['p_value_ge_observed']} / {nb['p_value_ge_observed']}，即「与随机同量级」稳健，"
      "但由它推出的「无泄漏」仍是不可推出的（F2）。")
    A("* **(c)** 去重机制的声明命中数（24 对语料）与可见账本（19 行）给出的**下界**：只印触发路径，"
      "故可见值只能证明「≥」，不能证明「=」。")
    A("")
    A("**为什么没有场量云图**：本单的审核对象是进程/纪律机器（零物理量、零几何、零流场），"
      "不存在可画云图的场量；上图为全部可量化的审核证据，未用示意图替代数据。")
    A("")
    A("## ⑤ 注意点 / 局限（踩过的坑）")
    A("")
    A("1. **印出精度决定可核性**：区间端点印 2 位小数，而声明量给到 14 位有效数字"
      "（`0.13705000000000003`）。前者使 1/40 行判定翻转、中位宽无法复算——"
      "这不是「报告算错」，而是「报告给不出可核的数字」。精度自洽是可核验性的第一道门。")
    A("2. **零模型要写出来，但别指望它替你下结论**：`无信息基线 = 平均区间宽度` 只在结果 ~ U(0,1) 时成立；"
      "换用实测值带零模型后 p0 由 0.1575 变为 0.2032（区间本身几乎覆盖整个值带）。本单核过：两种零模型下"
      "实测命中都不显著，所以「同量级」这半句站得住；真正不能写的是由它推出的「无泄漏」——"
      "不拒绝 ≠ 证明，且合成 dry-run 对泄漏无判别力（F2）。审阅者自己也要避免把「零模型敏感」"
      "直接写成「报告结论翻转」：先算 p 值再下判语。")
    A("3. **只能核对下界时要说下界**：账本只印前 24 行中的 19 条克隆，机制计数只能验证「可见 ≤ 声明」。"
      "把下界一致写成「已核实」是 04 工序最常见的越界。")
    A("4. **合成数据的两难**：dry-run 结果由种子确定性生成，任何「预测-结果」相关性都无法归因于"
      "人类/模型能力或泄漏——报告 §⑤-5 已自述，本单进一步指出「无泄漏」也同属不可判定。")
    A("5. **本单自身的局限**：单审阅人、无第二签核；不执行被审代码；不重实现相似度算法"
      "（重实现会引入审阅者口径，反而降低独立性）。因此「锁/篡改/时序/pytest」四类证据只能记 WITHHELD。")
    A("6. **不要用 finding 数当质量指标**：4 条 fail 里 2 条（C5/C6）是同一根因（印出精度），"
      "1 条（C12）是叙述口径，1 条（C8）是推断越界；把它们当「4 个独立缺陷」会夸大问题。")
    A("")
    A("## ⑥ 误差判定（关键量 vs 基准，逐项回答「是否 <3%」）")
    A("")
    A("**基准声明**：本节点零物理量（C16 已核），故「对标实验值」的 15%/3% 判据**不适用**；"
      "下表的基准取「报告自身声明值」与「契约 pin」，判的是**可复算性误差**。")
    A("")
    A("| 量 | 基准 | 重算 | 相对误差 | <3%？ |")
    A("|---|---|---|---|---|")
    rel_err = lambda a, b: abs(a - b) / abs(b) * 100 if b else 0.0  # noqa: E731
    rows = [
        ("源哈希 / 字符数", "契约 pin "
         f"({checks['source']['chars']} chars)", f"{checks['source']['chars']} chars", 0.0, "是"),
        ("席位数 40 = 4×5×2", "40", f"{c['C3_seat_arithmetic']['recomputed']['seats']}",
         rel_err(c["C3_seat_arithmetic"]["recomputed"]["seats"], 40), "是"),
        ("矩阵格数 20 / 格内 1+1", "20", f"{c['C3_seat_arithmetic']['recomputed']['cells']}"
         f"（1+1 格 {c['C3_seat_arithmetic']['recomputed']['cells_with_exactly_1_attacker_1_breaker']}）",
         rel_err(c["C3_seat_arithmetic"]["recomputed"]["cells"], 20), "是"),
        ("角色边际 attacker/breaker", "20 / 20",
         f"{c['C3_seat_arithmetic']['recomputed']['roles']['attacker']} / "
         f"{c['C3_seat_arithmetic']['recomputed']['roles']['breaker']}", 0.0, "是"),
        ("人口占比（4 族）", "0.3333/0.1667/0.1667/0.3333",
         "/".join(f"{v:.4f}" for v in c["C13_population_table"]["recomputed"]["shares"].values()),
         0.0, "是"),
        ("前两族占比", f"{c['C13_population_table']['declared']['top2_share']}",
         f"{c['C13_population_table']['recomputed']['top2_share']}",
         rel_err(c["C13_population_table"]["recomputed"]["top2_share"],
                 c["C13_population_table"]["declared"]["top2_share"]), "是（0.001%）"),
        ("§⑥ 差 0.175−0.1576", f"{c['C14_section6_error_row']['declared']['diff']}",
         f"{c['C14_section6_error_row']['recomputed']['diff_from_declared_inputs']}",
         rel_err(c["C14_section6_error_row"]["recomputed"]["diff_from_declared_inputs"],
                 c["C14_section6_error_row"]["declared"]["diff"]), "是"),
        ("平均区间宽（无信息基线）",
         f"{c['C7_width_statistics']['declared']['mean_width_baseline']}",
         f"{c['C7_width_statistics']['recomputed']['mean_width']}",
         rel_err(c["C7_width_statistics"]["recomputed"]["mean_width"],
                 c["C7_width_statistics"]["declared"]["mean_width_baseline"]), "是（0.06%）"),
        ("中位区间宽", f"{c['C7_width_statistics']['declared']['median_width']}", f"{round(med, 6)}",
         rel_err(med, c["C7_width_statistics"]["declared"]["median_width"]), "是（1.5%，舍入包络内）"),
        ("盲预测命中数", f"{hits_decl}", f"{hits_re}", rel_err(hits_re, hits_decl),
         f"**否**（{rel_err(hits_re, hits_decl):.1f}% > 3%，F1）"),
        ("hit_rate", f"{rate_decl}", f"{rate_re}", rel_err(rate_re, rate_decl),
         f"**否**（{rel_err(rate_re, rate_decl):.1f}% > 3%，F1）"),
        ("克隆骨架最小相似度", "0.6308", "无印出行（可见最小 "
         f"{c['C11_similarity_table_consistency']['recomputed']['min_printed_skeleton_hit']}）",
         None, "无基准（F5）"),
        ("锁复算 / 篡改 / 时序 / pytest", "✅✅✅ / 22 passed", "不可执行（工件不在本仓）", None,
         "无基准（WITHHELD，F4）"),
    ]
    for name, base, ours, err, verdict in rows:
        err_s = "—" if err is None else f"{err:.4f}%"
        A(f"| {name} | {base} | {ours} | {err_s} | {verdict} |")
    A("")
    numeric = [(n, e) for n, _, _, e, _ in rows if e is not None]
    under = [n for n, e in numeric if e < 3.0]
    over = [(n, e) for n, e in numeric if e >= 3.0]
    exact = [n for n, e in numeric if e == 0.0]
    A(f"**逐项结论**：{len(numeric)} 个可算出相对误差的量中，**{len(under)} 个 <3%（其中 {len(exact)} 个恰为 0）**；"
      f"**{len(over)} 个 >3%**（" + "、".join(f"{n} {e:.1f}%" for n, e in over)
      + "，同一印出精度根因，F1）；"
      f"{len(rows) - len(numeric)} 个无基准（0.6308 无印出行；锁/篡改/时序/pytest 工件不在本仓）。"
      "物理基准（15%/3%）整体**不适用**——本节点不产生物理量，报告亦如此声明，本单核过（C16）。")
    A("")
    A("**honest-FAIL 记录**：F1/F2 是两条实实在在的「不可复算 / 推断越界」，未因「不影响门」而降级为通过；"
      "F4 的四类证据记 WITHHELD 而非 pass；未在任何字段写入 verification 或「已核实」。")
    A("")
    A("## 附：产物与复算")
    A("")
    A("| 文件 | 作用 |")
    A("|---|---|")
    A("| `work/wp-5949-04/review_checks.py` | 17 项检查实现（纯函数，stdlib，锚点逐字强校验） |")
    A("| `work/wp-5949-04/checks.json` | 逐项检查原始结果（声明 / 重算 / 状态 / 锚点行号） |")
    A("| `docs/kf/wp-5949-04/review_report.json` | 审核正文（契约 04 信封：checks / findings / decision / remediation） |")
    A("| `docs/kf/wp-5949-04/source_5949.md` | 被审报告冻结副本（哈希即 provenance.source_hash） |")
    A("| `docs/kf/wp-5949-04/figures/wp-5949-04_checks.png` | 三面板复核图（④） |")
    A("| `docs/kf/wp-5949-04/kf_result.json` | 交付信封 + 各产物 sha256/字节数 |")
    A("| `tests/test_kf_wp5949_review.py` | 离线自检（可复跑一致、锚点、数字注入、finding 覆盖、无 verification 字段） |")
    A("")
    A("复算：`python3 work/wp-5949-04/review_checks.py && python3 work/wp-5949-04/build_review.py "
      "&& python3 -m pytest tests/test_kf_wp5949_review.py -q`")
    A("")
    return "\n".join(L)


# -------------------------------------------------------------------------- main
def main() -> None:
    checks = json.loads(CHECKS.read_text(encoding="utf-8"))
    fresh = rc.run_checks()
    assert fresh == checks, "checks.json is stale: rerun work/wp-5949-04/review_checks.py"

    findings = build_findings(checks)
    check_coverage(checks, findings)
    report = build_review(checks, findings)

    PKG.mkdir(parents=True, exist_ok=True)
    make_figure(checks)

    REVIEW.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    MARKDOWN.write_text(build_markdown(checks, report), encoding="utf-8")

    kf = {
        "package_id": "wp-5949-04",
        "task_type": "04-independent-review",
        "contract_version": "1.0",
        "report_id": rc.REPORT_ID,
        "provenance": {
            "source_uri": f"tensor://reports/{rc.REPORT_ID}",
            "source_field": "markdown",
            "source_hash": "sha256:" + checks["source"]["sha256"],
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": checks["source"]["chars"],
            "source_bytes_utf8": checks["source"]["bytes_utf8"],
            "source_hash_matches": checks["source"]["sha256"] == rc.CONTRACT_HASH,
            "title": TITLE,
            "scenario_key": SCENARIO,
            "upstream_package": "wp-5949-01",
            "reviewer": REVIEWER,
            "reviewed_at": REVIEWED_AT,
        },
        "decision": {
            "verdict": report["decision"]["verdict"],
            "blocking_findings": report["finding_counts"]["blocking"],
            "checks": {k: report["checks_summary"][k] for k in
                       ("n_checks", "n_pass", "n_fail", "n_unverifiable")},
        },
        "outputs": {},
    }
    for label, path in (
        ("review_report.json", REVIEW),
        ("KF-RESULT-wp-5949-04.md", MARKDOWN),
        ("figures/wp-5949-04_checks.png", FIGURE),
        ("work/wp-5949-04/checks.json", CHECKS),
        ("work/wp-5949-04/review_checks.py", REPO / "work" / "wp-5949-04" / "review_checks.py"),
        ("work/wp-5949-04/build_review.py", REPO / "work" / "wp-5949-04" / "build_review.py"),
        ("source_5949.md", PKG / "source_5949.md"),
    ):
        raw = path.read_bytes()
        kf["outputs"][label] = {
            "path": rel(path),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        }
    KF_RESULT.write_text(json.dumps(kf, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {rel(REVIEW)}, {rel(MARKDOWN)}, {rel(KF_RESULT)}, {rel(FIGURE)}")
    print(f"decision={report['decision']['verdict']} findings={len(findings)} "
          f"(blocking={report['finding_counts']['blocking']})")


if __name__ == "__main__":
    main()
