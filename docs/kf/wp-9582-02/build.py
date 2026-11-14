#!/usr/bin/env python3
"""Build the wp-9582-02 (02-classification-parse) result for report 9582.

Design rules honoured here:
  * zero hand-copy: every quote below is a *candidate string* that is located in
    the fetched markdown; offsets and content hashes are computed, never typed.
  * absence claims are falsifiable: each "absent" signal records the exact search
    terms and their hit counts measured on this markdown.
  * nothing is marked verified: all records carry epistemic_status=draft,
    assessment_status=unassessed; verification belongs to the platform gate.

Usage:  python3 artifacts/wp-9582-02/build.py
Inputs: artifacts/wp-9582-02/source.md (verbatim markdown of tensor_reports id 9582)
Outputs: artifacts/wp-9582-02/classification.json, artifacts/wp-9582-02/kf_result.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE
while not (ROOT / "schemas" / "kf_result.v1.schema.json").is_file():
    if ROOT == ROOT.parent:
        raise SystemExit("repo root (schemas/kf_result.v1.schema.json) not found above this file")
    ROOT = ROOT.parent
SRC = HERE / "source.md"
PKG = "wp-9582-02"
REPORT_ID = "9582"
EXPECTED_HASH = "cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f"

META = HERE / "record_meta.json"
meta = json.loads(META.read_text(encoding="utf-8"))
text = SRC.read_text(encoding="utf-8")
src_bytes = SRC.read_bytes()
src_hash = hashlib.sha256(src_bytes).hexdigest()
if src_hash != EXPECTED_HASH:
    sys.exit(f"source hash mismatch: {src_hash} != {EXPECTED_HASH}")
if meta["markdown_chars"] != len(text) or meta["markdown_sha256"] != "sha256:" + src_hash:
    sys.exit("record_meta.json does not describe this exact markdown — refusing to build")


def sha256(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- evidence bank
# (id, aspect, statement, quote)  -- quote must occur exactly once in the source
EVIDENCE = [
    (
        "ev-9582-02-01",
        "identity.title",
        "报告 H1 自述标题（与记录 title 存在措辞差异，见 limitations.title_drift）",
        "# P82W2-N02 碎冰堆积体动态演化与运动学：孔隙率场、力链网络与 μ(I) 流变标定",
    ),
    (
        "ev-9582-02-02",
        "purpose.problem_class",
        "报告把自身定位为船舶冰阻力/冰载荷连续模型的等效介质来源，属于应用物理量标定类工作",
        "碎冰（rubble）堆积体是船舶冰阻力与冰载荷模型的等效连续介质来源。",
    ),
    (
        "ev-9582-02-03",
        "type.experimental-validation.test_matrix",
        "test matrix 信号命中：工况矩阵显式给出 runs/条件/seed 重复数",
        "| 工况数 | 54 runs，19 个（场景, 固体分数, 速率）条件；剪切/压缩每条件 3 个 seed，航道 2 个 |",
    ),
    (
        "ev-9582-02-04",
        "type.experimental-validation.measurement_uncertainty",
        "measurement uncertainty 信号命中之二：条件均值标准误作为统计噪声量化",
        "| 条件均值 μ 的平均标准误（统计噪声） | 0.0102 |",
    ),
    (
        "ev-9582-02-05",
        "type.experimental-validation.uncertainty_budget",
        "噪声预算专节（残差 vs 统计噪声的可分辨性判据）",
        "### 3.6 判据 (c) 的噪声预算：残差是结构性的还是统计的？",
    ),
    (
        "ev-9582-02-06",
        "type.experimental-validation.signal_vs_noise",
        "信号-噪声对照：条件间标准差作为信号量级",
        "| μ 的条件间标准差（信号） | 0.0281 |",
    ),
    (
        "ev-9582-02-07",
        "type.experimental-validation.validation_case",
        "validation case 信号命中：样本外验证场景显式声明未参与标定",
        "### 3.8 样本外验证（碎冰航道，未参与标定）",
    ),
    (
        "ev-9582-02-08",
        "type.experimental-validation.validation_result",
        "样本外验证给出偏差数值与离散度（含符号），保留为模型形式误差",
        "6 个航道 run 的实测 μ 与单元试验律预测之差 = -0.1698 ± 0.0182（相对误差均值 -2.25），压力 6186–9191 Pa。",
    ),
    (
        "ev-9582-02-09",
        "type.experimental-validation.baseline_comparison",
        "baseline/threshold 对照信号命中：预注册阈值 vs 实测 vs 结论四列表",
        "| 判据 | 阈值 | 实测 | 结论 |",
    ),
    (
        "ev-9582-02-10",
        "type.experimental-validation.honest_fail",
        "主判据被判 FAIL(honest)，报告未把失败改写为通过",
        "| (c) μ(I) 拟合优度（主判据：合并单元试验） | R²≥0.95, σ≤0.05 | R²=0.8035, σ=0.0134 | **FAIL (honest)** |",
    ),
    (
        "ev-9582-02-11",
        "type.experimental-validation.baseline_semantics",
        "对照基准的语义被显式限定为量级窗（不是逐点基准），属保留不确定性的写法",
        "| η(0.1 s⁻¹, 10 kPa) vs 文献窗 | [1e3, 1e5] Pa·s（量级窗，非逐点） | 2.512e+04 | 窗内（不作 % 判定，基准为量级窗） |",
    ),
    (
        "ev-9582-02-12",
        "type.scientific-computation.governing_equation_partial",
        "二次流变律与 I/μ/η 定义被写出（构关系式，非控制方程）",
        "（3）宏观流变点 (I, μ) 与二次流变律 μ(I) = μ₀ + αI + βI²，并给出等效黏度 η = μP/γ̇ 与文献锚点对照。",
    ),
    (
        "ev-9582-02-13",
        "type.scientific-computation.fitted_law",
        "拟合得到的本构律及适用 I 区间（含区间端点）",
        "主判据律：μ(I) = 0.2498 +2.028 I -12.984 I²，覆盖 I ∈ [4.330e-03, 0.0674]。",
    ),
    (
        "ev-9582-02-14",
        "type.scientific-computation.discretisation_partial",
        "仅后处理网格被离散化规定（h=5d50 且给出铺满偏差）——求解器离散/时间积分未描述",
        "| 后处理网格 | h = 5 d₅₀（单元格精确铺满域，h/d₅₀ = 5.0 ± 0.5%） |",
    ),
    (
        "ev-9582-02-15",
        "type.scientific-computation.postprocess_method",
        "后处理方法被逐条编号描述（Voronoi/Delaunay 逐颗粒量）",
        "2. Voronoi/Delaunay：中心点镶嵌（周期像/闭壁镜像）给逐颗粒 φᵢ = 1 − A_disk/A_cell 与 Delaunay 边长/d₅₀。",
    ),
    (
        "ev-9582-02-16",
        "type.scientific-computation.stress_definition",
        "宏观应力的位力定义与 I 的定义式、无量纲化方式被写出",
        "4. 宏观量：Love–Weber 位力 σ = −(1/V)Σf⊗b（压为正），P = trσ/2，τ = (σ₁−σ₂)/2，μ = τ/P；I = γ̇d₅₀/√(P/ρ)，γ̇ 三场景一律取**实测**值：剪切/航道用本体速度剖面斜率，压缩用本体速度梯度 `bulk_deformation_rate` 的 √(2D:D)（本次修正，见 3.5）。",
    ),
    (
        "ev-9582-02-17",
        "type.software-engineering.interface",
        "引擎接口变更被显式声明，并声明默认值保持历史行为（向后兼容）",
        "- 剪切：x 周期、上下粗糙壁**反向滑动**（±v/2，几何不动）。为此给引擎新增逐段壁面速度 `wall_velocity`（默认 None = 历史行为逐位不变）。γ̇ 由本体切片（离壁 ≥3r̄）速度剖面最小二乘斜率给出。",
    ),
    (
        "ev-9582-02-18",
        "type.software-engineering.regression",
        "回归证据以测试项数（含负控）形式给出",
        "- 测试：`tests/test_rubble_postprocess.py`（19 项，含 4 个负控）+ `tests/test_rubble_kinematics.py`（5 项，运动学一致性）",
    ),
    (
        "ev-9582-02-19",
        "type.software-engineering.commit_trailer",
        "全文唯一出现 commit 的位置是尾部注释里的 hemelb commit，与被分类报告的改动无对应关系——不可当作本报告改动提交号",
        "<!-- m8301 / FEAT-OSS-INVENTORY-LBM / hemelb commit 432d3386 -->",
    ),
    (
        "ev-9582-02-20",
        "type.literature-review.citation_density",
        "全文唯一可解析的文献引证为 Guimarães et al. 2022，且被标注为量级窗/逐点 WITHHELD——不构成综述型引证密度",
        "6. **文献锚点为量级窗**：Guimarães et al. 2022 未数字化逐点数据，逐点对比标注 WITHHELD。",
    ),
    (
        "ev-9582-02-21",
        "type.algorithm-implementation.procedure_block",
        "算法的编号步骤块存在（后处理 1–5 步），但没有伪码/复杂度/函数签名",
        "3. 力链：按接触力分位切分强弱链（互补掩码），方向折叠到 [0,π)，结构张量 R = ⟨nn⟩ 给 A_c = 2(λ₁−λ₂)/(λ₁+λ₂)，强子图连通分量与横跨判定（判据 b 双审计：接触数 + 力求和）。",
    ),
    (
        "ev-9582-02-22",
        "type.technical-proposal.absent_plan",
        "报告以「先声明阈值、后扫描」的预注册执行链呈现，而不是提案/路线图",
        "- 预注册：`prereg/rubble_rheology_prereg.json`（阈值先声明；Amendment 1 = 等面积压缩 + 航道改作验证；Amendment 2 = 本次两个运动学修正、被否决的仿射速度重映射、双固体分数设计，均写于生产扫描之前）",
    ),
    (
        "ev-9582-02-23",
        "setup.numerical_cell",
        "实验/数值装置的类型与几何被声明：二维平面应变 + 周期 x，属«数值单元试验»而非物理实验台",
        "| 几何/维度 | 二维平面应变，周期 x（航道场景 x 周期 + 固定船体） |",
    ),
    (
        "ev-9582-02-24",
        "setup.material",
        "材料/颗粒参数被给出（双分散刚性圆盘、d50、密度）",
        "| 颗粒 | 双分散刚性圆盘，d₅₀ = 0.02359 m，密度 ρ = 917 kg/m³ |",
    ),
    (
        "ev-9582-02-25",
        "setup.contact_model",
        "接触模型与摩擦/刚度参数被给出（Hertz–Mindlin + Coulomb + 滚动阻力）",
        "| 接触 | Hertz–Mindlin 法向/切向 + Coulomb 摩擦 μ_p = 0.5 + 滚动阻力 0.05，kn = 3.0e4 N/m，板厚 0.03 m |",
    ),
    (
        "ev-9582-02-26",
        "setup.scenarios",
        "三类场景被显式枚举，决定了 3.1 表的分组结构",
        "| 场景 | 简单剪切（粗糙滑动壁 Couette）/ 等面积平面应变压缩 / 碎冰航道漂移 |",
    ),
    (
        "ev-9582-02-27",
        "measurement.result_table_shear",
        "条件级结果表的列结构（含 seeds 与标准误）——03 抽取的条件/重复单元定义",
        "| 场景 | 名义速率 | seeds | P [Pa] | I | μ | μ 标准误 |",
    ),
    (
        "ev-9582-02-28",
        "measurement.fit_table",
        "拟合结果表的列结构（μ₀/α/β/R²/残差/n）",
        "| 口径 | μ₀ | α | β | R² | 残差标准差 | n |",
    ),
    (
        "ev-9582-02-29",
        "comparison.ablation",
        "消融对照设计存在（legacy/piston/remap × 两个名义速率）",
        "### 3.5 压缩单元试验运动学消融（本次修正的直接证据）",
    ),
    (
        "ev-9582-02-30",
        "limitations.finite_size",
        "有限尺寸涨落被量化为局限（N≈400，seed 间/条件级离散度）",
        "4. **有限尺寸涨落**：N≈400 圆盘，seed 间 μ 标准差 0.01–0.02，条件标准误 0.005–0.010；12 快照平均后的条件均值仍是判据 (c) 的主要噪声源。",
    ),
    (
        "ev-9582-02-31",
        "comparison.honest_conclusion",
        "报告的诚实结论段把数值层误差与物理层 FAIL 分开陈述",
        "**诚实结论**：数值/守恒/拟合器层面误差 ≪3%；物理层面「单一 μ(I) 跨三场景」主判据 honest FAIL（R² = 0.8035 < 0.95，残差 σ = 0.0134）。",
    ),
    (
        "ev-9582-02-32",
        "measurement.figures_declared",
        "报告声明了 6 张图并给出英文图注（图为平台侧 figures 字段，正文仅有说明）",
        "**porosity_fields.png** — Porosity field phi(x,t) of one steady snapshot per scenario on the required grid h = 5 d50.",
    ),
    (
        "ev-9582-02-33",
        "toolchain",
        "工具链与产物路径被列出（扫描/分析脚本、summary.json）",
        "**工具链**：预注册 `prereg/rubble_rheology_prereg.json`（阈值先于生产扫描声明，含 Amendment 1）；扫描 `scripts/run_rubble_rheology.py`（集群 20 并发，60 runs）；拟合/验收/绘图 `scripts/analyse_rubble_rheology.py`；全部数字写入 `summary.json`。",
    ),
    (
        "ev-9582-02-34",
        "comparison.residual_interpretation",
        "残差性质的英文判读句（结构性而非抽样噪声）原文保留，不做改写",
        "解读：the pooled residual (0.0134) is 1.3x the mean per-condition standard error (0.0102), so it is structural (state/path), not sampling noise;",
    ),
    (
        "ev-9582-02-35",
        "figures.section",
        "④ 结果图章节存在（结构切分锚点），且图注为英文并以所需网格 h = 5 d50 表述",
        "## ④ 结果图\n\n**porosity_fields.png** — Porosity field",
    ),
]


def locate(quote: str) -> dict:
    n = text.count(quote)
    if n != 1:
        raise SystemExit(f"quote occurs {n} times (must be 1): {quote[:60]!r}")
    start = text.find(quote)
    end = start + len(quote)
    assert text[start:end] == quote
    return {
        "locator_type": "char_offset",
        "source_field": "markdown",
        "value": quote,
        "start_offset": start,
        "end_offset": end,
        "quote": quote,
        "content_hash": sha256(quote),
    }


evidence = []
for ev_id, aspect, statement, quote in EVIDENCE:
    evidence.append(
        {
            "id": ev_id,
            "aspect": aspect,
            "statement": statement,
            "locator": locate(quote),
            "epistemic_status": "draft",
            "assessment_status": "unassessed",
        }
    )

# --------------------------------------------------------------- absence checks
ABSENCE_TERMS = {
    "convergence study": ["convergence", "收敛", "收敛性研究", "网格收敛", "收敛阶"],
    "mesh refinement": ["mesh refinement", "refinement", "网格加密", "网格无关性"],
    "timing table": ["timing", "wall-clock", "计时", "耗时", "性能表"],
    "governing equations (PDE)": ["governing equation", "控制方程", "Navier", "平衡方程"],
    "facility (physical rig)": ["facility", "实验台", "试验台", "水槽", "冰池", "拖曳水池"],
    "related work": ["related work", "相关工作", "state of the art", "研究现状"],
    "survey": ["survey", "综述"],
    "bibliography": ["bibliography", "参考文献", "References"],
    "pseudocode": ["pseudocode", "伪代码"],
    "complexity": ["complexity", "时间复杂度", "复杂度"],
    "changed files (diff)": ["changed files", "diff --git", "变更文件"],
    "roadmap / proposal": ["roadmap", "proposal", "路线图", "提案"],
    "specification": ["specification", "规格书", "规格说明"],
}


def absence(signal: str) -> dict:
    terms = ABSENCE_TERMS[signal]
    hits = {t: text.count(t) for t in terms}
    return {
        "signal": signal,
        "presence": "absent",
        "basis": "search_terms_measured_on_markdown",
        "search_terms": hits,
        "total_hits": sum(hits.values()),
        "note": "no qualifying occurrence in the 11293-char markdown; absence is a measured claim, "
        "re-runnable via build.py / verify.py",
    }


def absent_with_refs(signal: str, ev_ids: list[str], note: str, terms: list[str]) -> dict:
    """A recorded miss that also cites source text explaining *why* the signal misses."""
    hits = {t: text.count(t) for t in terms}
    return {
        "signal": signal,
        "presence": "absent",
        "evidence_refs": ev_ids,
        "basis": "search_terms_measured_on_markdown + cited text",
        "search_terms": hits,
        "total_hits": sum(hits.values()),
        "note": note,
    }


def present(signal: str, ev_ids: list[str], status: str = "present", note: str = "") -> dict:
    rec = {"signal": signal, "presence": status, "evidence_refs": ev_ids}
    if note:
        rec["note"] = note
    return rec


# citation density (programmatic)
cite_terms = ["et al.", "et al", "Guimarães", "doi", "(20", "（20"]
cite_hits = {t: text.count(t) for t in cite_terms}
citation_density = round(sum(cite_hits.values()) / (len(text) / 1000.0), 4)

signals = {
    "experimental-validation": [
        present("test matrix", ["ev-9582-02-03"]),
        absent_with_refs(
            "facility",
            ["ev-9582-02-23", "ev-9582-02-24", "ev-9582-02-25"],
            note="no physical facility: the device is a 2-D periodic-strain numerical cell, and "
            "ev-9582-02-23/24/25 give the numerical setup instead. Recorded as a real miss of the "
            "signal, not reinterpreted as a hit.",
            terms=["facility", "实验台", "试验台", "水槽", "冰池", "拖曳水池"],
        ),
        present("measurement uncertainty", ["ev-9582-02-04", "ev-9582-02-05", "ev-9582-02-06", "ev-9582-02-30"]),
        present("validation case", ["ev-9582-02-07", "ev-9582-02-08"]),
        present("baseline comparison", ["ev-9582-02-09", "ev-9582-02-10", "ev-9582-02-11"]),
    ],
    "scientific-computation": [
        present(
            "governing equations",
            ["ev-9582-02-12", "ev-9582-02-16"],
            status="partial",
            note="constitutive/definition relations (mu(I), I, eta, Love-Weber virial) are written; "
            "no governing PDE or contact-dynamics evolution equation is stated",
        ),
        present(
            "discretisation",
            ["ev-9582-02-14", "ev-9582-02-15"],
            status="partial",
            note="only the post-processing grid h = 5 d50 is discretisation-specified; solver time integration is not described",
        ),
        absence("convergence study"),
        absence("mesh refinement"),
        absence("timing table"),
    ],
    "software-engineering": [
        present("changed files", ["ev-9582-02-33"], status="partial",
                note="file paths are listed in the audit chain; no diff/hunk is shown"),
        absent_with_refs(
            "commit",
            ["ev-9582-02-19"],
            note="the only 'commit' token is an unrelated hemelb trailer in a footer comment; it cannot "
            "be read as the commit of this report's change, so the signal is a miss (and is a trap worth "
            "recording for downstream extraction)",
            terms=["commit", "提交", "sha", "git "],
        ),
        present("interface", ["ev-9582-02-17"]),
        present("regression", ["ev-9582-02-18"]),
        present("API", ["ev-9582-02-17", "ev-9582-02-16"], status="partial",
                note="API-level identifiers (wall_velocity, bulk_deformation_rate) appear, "
                     "but as method description, not as API documentation"),
    ],
    "algorithm-implementation": [
        present("algorithm block", ["ev-9582-02-21"], status="partial",
                note="a numbered procedure block exists, but it is a data-analysis recipe"),
        absence("pseudocode"),
        absence("complexity"),
        absent_with_refs(
            "function signature", [], "no function signature appears in the markdown (identifiers only: "
            "wall_velocity, bulk_deformation_rate, RubbleNoContactsError)", ["def ", "(", ") ->"]),
    ],
    "literature-review": [
        absence("related work"),
        absence("survey"),
        absence("bibliography"),
        absent_with_refs(
            "citation density >= 5 per 1000 chars",
            ["ev-9582-02-20"],
            f"measured citation-ish token count {sum(cite_hits.values())} over "
            f"{len(text)/1000.0:.2f} kchar -> density {citation_density}; one anchor work only, and it is "
            "flagged WITHHELD for point-wise comparison",
            ["et al.", "Guimarães", "doi", "(20", "（20"],
        ),
    ],
    "technical-proposal": [
        absence("roadmap / proposal"),
        absence("specification"),
        absent_with_refs(
            "design", [], "the text reports executed runs and measured values; it does not propose a design "
            "to be built", ["design", "设计", "方案"]),
    ],
}

# ---------------------------------------------------------------- structure cut
lines = text.splitlines(keepends=True)
offsets = []
acc = 0
for ln in lines:
    offsets.append(acc)
    acc += len(ln)

sections = []
stack: list[tuple[int, str, int, str]] = []
for i, ln in enumerate(lines):
    stripped = ln.strip()
    if stripped.startswith("#"):
        level = len(stripped) - len(stripped.lstrip("#"))
        heading = stripped[level:].strip()
        stack.append((level, heading, offsets[i], stripped))
for idx, (level, heading, start, _) in enumerate(stack):
    end = stack[idx + 1][2] if idx + 1 < len(stack) else len(text)
    sections.append(
        {
            "section_id": f"s{idx + 1:02d}",
            "level": level,
            "heading": heading,
            "start_offset": start,
            "end_offset": end,
            "chars": end - start,
        }
    )

# map target skill sections (xsk-experimental-validation:
# setup / measurement / comparison / uncertainty / validation).
# Mapping is by heading keyword so it cannot silently drift with a shifted id.
SKILL_SECTION_RULES = {
    "setup": ["① 案例介绍", "② 怎么做的"],
    "measurement": ["3.1 各条件的流变点", "3.3 等效黏度", "3.4 孔隙率场与力链微结构"],
    "comparison": ["3.2 μ(I) 拟合", "3.7 机器可算验收判据", "⑥ 误差判定"],
    "uncertainty": ["3.6 判据 (c) 的噪声预算", "⑤ 注意点"],
    "validation": ["3.5 压缩单元试验运动学消融", "3.8 样本外验证"],
}
UNMAPPED_NOTES = {
    "s01": "document title (H1), no skill section",
    "s04": "container heading '③ 计算结果'; its content lives in the 3.x subsections",
    "s13": "figure-caption section; figures live in the platform figures field, not in the body",
    "s16": "audit chain (pre-registration / code / artifact pointers), no skill section",
}
sec_by_id = {s["section_id"]: s for s in sections}
heading_index = {s["heading"]: s["section_id"] for s in sections}
SKILL_SECTION_MAP: dict[str, list[str]] = {}
for skill_sec, keywords in SKILL_SECTION_RULES.items():
    ids = []
    for kw in keywords:
        matched = [sid for h, sid in heading_index.items() if h.startswith(kw)]
        if len(matched) != 1:
            raise SystemExit(f"skill section {skill_sec!r}: keyword {kw!r} matched {matched}")
        sid = matched[0]
        sec_by_id[sid].setdefault("skill_sections", []).append(skill_sec)
        ids.append(sid)
    SKILL_SECTION_MAP[skill_sec] = ids
missing_notes = [s["section_id"] for s in sections
                 if "skill_sections" not in s and s["section_id"] not in UNMAPPED_NOTES]
if missing_notes:
    raise SystemExit(f"unmapped sections without a note: {missing_notes}")

# --------------------------------------------------------------- classification
cls = {
    "schema": "classification.v1",
    "package_id": PKG,
    "task_type": "02-classification-parse",
    "contract_version": "1.0",
    "report_id": REPORT_ID,
    "source": {
        "uri": "tensor://reports/9582",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": src_hash,
        "chars": len(text),
        "bytes_utf8": len(src_bytes),
        "title_record": meta["title"],
        "title_markdown_h1": evidence[0]["locator"]["quote"].lstrip("# "),
        "scenario_key": meta["scenario_key"],
        "mission_id_record": meta["mission_id"],
        "record_status": meta["status"],
        "record_tags": meta["tags"],
        "record_figures": meta["figures"],
        "citation_token_counts": cite_hits,
        "citation_density_per_kchar": citation_density,
    },
    "classification": {
        "report_type": "experimental-validation",
        "report_type_is_hypothesis": True,
        "status": "draft",
        "confidence": "medium-high",
        "confidence_rationale": "4 of 5 experimental-validation signals are present with locators (test matrix, "
        "measurement uncertainty, validation case, baseline comparison); the single miss (physical facility) is a "
        "genuine miss because the work is a numerical element-test campaign. The runner-up software-engineering "
        "type matches 3 of 5 signals, so the decision is a judgement about what the report is *about* (a "
        "calibration/validation study whose code change is instrumental), not a mechanical signal count.",
        "selected_skill_id": "xsk-experimental-validation",
        "skill_version": "0.1.0",
        "skill_lifecycle_state": "template-created",
        "signal_table": signals,
        "alternatives_considered": [
            {
                "report_type": "software-engineering",
                "decision": "rejected_as_primary",
                "rank": 2,
                "signals_matched": 3,
                "reason": "the report does contain an engine-level change (wall velocity with backward-compatible "
                "default) plus regression tests, and one ablation section is devoted to it; but the change "
                "occupies part of section ② and the audit chain, while the deliverable quantity of the report "
                "is the (I, mu) point set, the fit law and the acceptance criteria. Extracting this report as a "
                "software change would miss the measured conditions and their uncertainty.",
                "evidence_refs": ["ev-9582-02-17", "ev-9582-02-18", "ev-9582-02-19", "ev-9582-02-29"],
                "residual_risk": "if工序03 wants change-scope claims, run xsk-software-engineering as a secondary skill",
            },
            {
                "report_type": "scientific-computation",
                "decision": "rejected_as_primary",
                "rank": 3,
                "signals_matched": 0,
                "signals_partial": 2,
                "reason": "the constitutive law and the Love-Weber stress definition are written, and a "
                "post-processing grid is specified, but there is no governing PDE, no discretisation of a "
                "solver, and - measured - zero occurrences of convergence/mesh-refinement/timing terms. "
                "A scientific-computation skill would demand a convergence study this report does not have.",
                "evidence_refs": ["ev-9582-02-12", "ev-9582-02-13", "ev-9582-02-14", "ev-9582-02-16"],
            },
            {
                "report_type": "algorithm-implementation",
                "decision": "rejected_as_primary",
                "rank": 4,
                "signals_matched": 1,
                "reason": "a numbered post-processing recipe exists, but no pseudocode, complexity statement "
                "or function signature; the algorithmic content is a data-analysis recipe, not an algorithm report.",
                "evidence_refs": ["ev-9582-02-15", "ev-9582-02-21"],
            },
            {
                "report_type": "literature-review",
                "decision": "rejected_as_primary",
                "rank": 5,
                "signals_matched": 0,
                "reason": "one literature anchor (Guimarães et al. 2022), explicitly flagged WITHHELD for "
                "point-wise comparison; measured citation-token density far below the >=5 per 1000 chars signal.",
                "evidence_refs": ["ev-9582-02-20"],
            },
            {
                "report_type": "technical-proposal",
                "decision": "rejected_as_primary",
                "rank": 6,
                "signals_matched": 0,
                "reason": "no proposal/roadmap/specification; the text reports already-executed runs under "
                "pre-registered thresholds rather than proposing future work.",
                "evidence_refs": ["ev-9582-02-22"],
            },
        ],
    },
    "topics": {
        "scenario_key": meta["scenario_key"],
        "discipline": "ship_ice_navigation",
        "subdiscipline": "ice_resistance_and_loads",
        "method_family": "discrete_element_method",
        "layers": ["DEM", "ice_rubble_rheology_dem", "l"],
        "tags": [
            "DEM",
            "mu(I)-rheology",
            "ice-rubble",
            "porosity-field",
            "force-chain",
            "equivalent-viscosity",
            "couette-shear",
            "biaxial-compression",
            "ice-channel",
            "uncertainty-budget",
            "model-form-error",
            "honest-FAIL",
            "pre-registration",
        ],
        "topic_scope": "calibration and out-of-sample validation of a mu(I) constitutive law for ice rubble, "
        "plus micro-structural descriptors (porosity field, force-chain network) usable by continuum ice-load models",
    },
    "structure": {
        "section_count": len(sections),
        "sections": sections,
        "skill_section_map": SKILL_SECTION_MAP,
        "unmapped_sections": UNMAPPED_NOTES,
        "notes": "offsets are Python character indices into the markdown field (unicode code points), "
        "computed by build.py from the fetched bytes; section spans run to the next heading.",
    },
    "classification_evidence": evidence,
    "unresolved": [
        {
            "id": "unres-9582-02-01",
            "aspect": "type.facility",
            "status": "unresolved",
            "statement": "experimental-validation signal 'facility' is not satisfied and cannot be resolved from "
            "the text: the work is a numerical element-test campaign, so a physical facility is not merely "
            "omitted but inapplicable. Recorded unresolved rather than re-labelled.",
            "evidence_refs": ["ev-9582-02-23"],
        },
        {
            "id": "unres-9582-02-02",
            "aspect": "identity.title_drift",
            "status": "unresolved",
            "statement": "record title, contract title and markdown H1 differ in wording; the report markdown "
            "H1 also names kinematic descriptors, the record title names 'equivalent viscosity (DEM)'. The "
            "divergence is preserved, not reconciled; downstream must key on report_id.",
            "evidence_refs": ["ev-9582-02-01"],
        },
    ],
    "limitations": [
        {
            "id": "lim-9582-02-01",
            "aspect": "signal_selection_asymmetry",
            "statement": "The experimental-validation signal 'facility' misses because the work is computational; "
            "the scientific-computation signals 'convergence study' / 'mesh refinement' / 'timing table' miss for "
            "the same inapplicability reason. Both are recorded as misses (symmetric treatment). Robustness check: "
            "if inapplicable signals are dropped from the denominator, experimental-validation scores 4/4 and "
            "scientific-computation 2/5 — the ranking does not change, so the primary type does not hinge on this.",
            "evidence_refs": ["ev-9582-02-23", "ev-9582-02-14"],
        },
        {
            "id": "lim-9582-02-02",
            "aspect": "section_mapping_is_a_judgement",
            "statement": "Mapping report sections onto the skill's setup/measurement/comparison/uncertainty/"
            "validation slots is a judgement; several sections could serve two slots (e.g. 3.3 equivalent viscosity "
            "is both a derived measurement and a literature-window comparison; 3.5 ablation is both comparison and "
            "validation). Each section was given its dominant slot only, to keep the downstream extraction "
            "instruction unambiguous. Re-slotting is a legitimate downstream revision.",
            "evidence_refs": ["ev-9582-02-29", "ev-9582-02-11"],
        },
        {
            "id": "lim-9582-02-03",
            "aspect": "absence_is_term_based",
            "statement": "Absence of a signal is measured with an explicit bilingual term list recorded in the "
            "product. A synonymous Chinese phrasing outside that list would be missed; this residual uncertainty is "
            "why confidence is medium-high, not high.",
            "evidence_refs": [],
        },
        {
            "id": "lim-9582-02-04",
            "aspect": "mission_id_not_interpreted",
            "statement": "The record carries mission_id 8301 (also echoed in the report footer as m8301). It is "
            "recorded verbatim and not interpreted; the work-package contract declares mission_id: null.",
            "evidence_refs": ["ev-9582-02-19"],
        },
        {
            "id": "lim-9582-02-05",
            "aspect": "no_semantic_verdict",
            "statement": "This package does not judge whether the report's own scientific statements are true. "
            "Classification correctness is decided by工序04 / the platform gate; every record here is draft and "
            "unassessed.",
            "evidence_refs": [],
        },
    ],
    "scope": {
        "did": ["fetch markdown by id", "recompute sha256", "six-type signal evaluation with locators",
                "section cut with offsets", "select skill_id", "topic tagging", "absence measurement"],
        "did_not": ["extract claims", "register assets", "read or write any other report_id",
                    "mark anything verified", "modify upstream or sibling products"],
        "claims_emitted": 0,
        "claims_note": "task_type 02 does not extract; claims.json is emitted as an empty array by design, "
        "which satisfies the acceptance rule 'all_claims_have_evidence_or_explicit_unresolved_status' vacuously "
        "and explicitly (legitimate zero-claim package).",
    },
}

# ------------------------------------------- upstream (01) consistency, read-only
UPSTREAM = ROOT / "docs" / "kf" / "wp-9582-01" / "asset_manifest.json"
upstream = None
if UPSTREAM.is_file():
    um = json.loads(UPSTREAM.read_text(encoding="utf-8"))
    upstream = {
        "package_id": um.get("package_id"),
        "task_type": um.get("task_type"),
        "source_hash": um["source"]["hash"],
        "source_chars": um["source"].get("chars"),
        "hash_equal_to_this_package": um["source"]["hash"] == src_hash,
        "chars_equal": um["source"].get("chars") == len(text),
        "access": "read-only; not modified by this package",
        "path": str(UPSTREAM.relative_to(ROOT)),
    }
cls["upstream_check"] = upstream or {"status": "absent", "note": "no wp-9582-01 manifest found in this worktree"}

# ------------------------------------------------------------------- kf_result
kf = {
    "package_id": PKG,
    "task_type": "02-classification-parse",
    "contract_version": "1.0",
    "report_id": REPORT_ID,
    "provenance": {
        "source_uri": "tensor://reports/9582",
        "source_field": "markdown",
        "source_hash": "sha256:" + src_hash,
        "source_hash_matches": True,
        "title": cls["source"]["title_record"],
        "scenario_key": meta["scenario_key"],
        "chars": len(text),
    },
    "outputs": {
        "classification.json": cls,
        "claims.json": [],
    },
}

(HERE / "classification.json").write_text(
    json.dumps(cls, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8"
)
(HERE / "kf_result.json").write_text(
    json.dumps(kf, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8"
)
print(f"source: chars={len(text)} bytes={len(src_bytes)} sha256={src_hash}")
print(f"evidence={len(evidence)} sections={len(sections)} unresolved={len(cls['unresolved'])}")
print("wrote classification.json, kf_result.json")