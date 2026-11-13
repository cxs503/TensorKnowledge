"""Build the wp-2506-04 independent-review deliverables.

Zero-hand-copy policy: every quote placed in the review is extracted from the
fetched report markdown by anchoring on unique substrings and asserted to occur
exactly once, so no quote can drift from the source text.

Outputs
  work/wp-2506-04/review_report.json      (contract output: review_report.json)
  docs/kf_result_wp-2506-04.md            (KF-RESULT markdown with single json block)
  work/wp-2506-04/reviewer-figure.png     (reviewer-side measurement figure)
  /tmp/kf_publish_wp-2506-04.json         (report payload for POST /tensor/reports)

Run: python3 work/wp-2506-04/build_review.py
"""
import base64
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
WP = ROOT / "work" / "wp-2506-04"
MD = (WP / "source_2506.md").read_text(encoding="utf-8")
SOURCE_HASH = "sha256:" + hashlib.sha256(MD.encode()).hexdigest()
EXPECTED_HASH = "sha256:c62850b3dacd416bd9d535fec206f6e8427fb10121f439c7b865b2165e5138b0"
assert SOURCE_HASH == EXPECTED_HASH, (SOURCE_HASH, EXPECTED_HASH)


def q(start_anchor, end_anchor):
    """Return the verbatim source span from start_anchor through end_anchor."""
    assert MD.count(start_anchor) == 1, ("ambiguous/missing start anchor", start_anchor)
    i = MD.index(start_anchor)
    assert MD.count(end_anchor, i) >= 1, ("missing end anchor", end_anchor)
    j = MD.index(end_anchor, i) + len(end_anchor)
    return MD[i:j]


QUOTE = {
    "summary_legacy": q("legacy 默认装配（α=1）", "首个失效 skew=0.975（非正交角 86.22° 起）。"),
    "summary_alpha0": q("**α=0（纯两点通量", "非正交修正不是主因。"),
    "summary_compat": q("相容装配：E 的最小值", "λmin(K) 最小值 = +0.360339 > 0。"),
    "attribution": q("- **归因修正**", "修正项只是把它放大。"),
    "default_path": q("- **默认路径未改**", "（有回归用例）"),
    "not_certified": q("- **只认证耗散性，不认证标度**", "需另单标定后才能进求解器"),
    "gradient_deviation": q("native 单元梯度模板未做体积归一", "最大 6.17"),
    "test_count": q("`tests/test_native_compatible_viscous3d.py`", "6 条用例"),
    "psd_by_construction": q("该矩阵是平方和", "耗散性由构造保证"),
    "error_policy": q("本单判据是**符号/特征值证书**", "显式声明，不含糊"),
    "crosscheck": q("若把「首个失效几何」当关键量", "（0.000）"),
    "sweep_label": q("扫描汇总（41 几何）", "扫描汇总（41 几何）"),
    "scope_module": q("新建 `src/tensorfvm/native_compatible_viscous3d.py`", "可去偏）。"),
}

repro_rows = json.loads((WP / "repro" / "sweep.json").read_text())
repro = {"rows": repro_rows} if isinstance(repro_rows, list) else repro_rows
_rows = repro["rows"]
# summary recomputed from the rows (same quantities the producer's script prints)
_fail1 = [r for r in _rows if r["legacy_damping_1.0_rate"] > 0]
repro_summary = {
    "points": len(_rows),
    "legacy_energy_producing_points": len(_fail1),
    "first_failing_skew": _fail1[0]["skew"] if _fail1 else None,
    "first_failing_angle": _fail1[0]["max_nonorthogonality_degrees"] if _fail1 else None,
    "compatible_min_rate": min(r["compatible_rate"] for r in _rows),
    "compatible_min_lambda": min(r["compatible_lambda_min"] for r in _rows),
    "legacy_damping0_min_rate": min(r["legacy_damping_0.0_rate"] for r in _rows),
    "legacy_damping0_energy_producing_points": sum(1 for r in _rows if r["legacy_damping_0.0_rate"] > 0),
    "legacy_rate_at_skew1": _rows[-1]["legacy_damping_1.0_rate"],
    "legacy_rate_at_skew1_damping0": _rows[-1]["legacy_damping_0.0_rate"],
}
probe_e = json.loads((WP / "probe_energy_rate.json").read_text())
probe_g = json.loads((WP / "probe_affine_gradient.json").read_text())

# ---------------------------------------------------------------- reviewer figure
def make_figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    skew = [r["skew"] for r in probe_e]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    ax = axes[0]
    for key, label in (("e_full_a1.0", "legacy alpha=1 (default)"),
                       ("e_full_a0.5", "legacy alpha=0.5"),
                       ("e_full_a0.0", "legacy alpha=0 (two-point)")):
        ax.plot(skew, [r[key] for r in probe_e], label=label)
    ax.axhline(0.0, color="k", linewidth=0.8)
    ax.set_xlabel("skew")
    ax.set_ylabel("E = u^T A u")
    ax.set_title("Reproduced by reviewer (41 geometries)")
    ax.legend(fontsize=7)

    ax = axes[1]
    for key, label in (("sym_defect_a1.0", "alpha=1"), ("sym_defect_a0.5", "alpha=0.5"),
                       ("sym_defect_a0.0", "alpha=0 (two-point)")):
        ax.plot(skew, [r[key] for r in probe_e], label=label)
    ax.set_xlabel("skew")
    ax.set_ylabel("||A - A^T|| / ||A||")
    ax.set_title("Reviewer-added: adjointness (SBP) defect")
    ax.legend(fontsize=7)
    fig.tight_layout()
    out = WP / "reviewer-figure.png"
    fig.savefig(out, dpi=110)
    return out


FIG = make_figure()

# ---------------------------------------------------------------- findings
FINDINGS = [
    {
        "id": "F1",
        "severity": "high",
        "blocking": True,
        "type": "code/docstring contradicts report",
        "location": "src/tensorfvm/native_compatible_viscous3d.py (module docstring, delivered by wp-2506-01)",
        "code_claim": "For affine velocity fields the cell gradients are exact, so the discrete energy identity ... holds to round-off and the coefficient of the operator is certified",
        "report_contradicts": QUOTE["gradient_deviation"],
        "evidence": {
            "measurement": "reviewer probe on NativeViscous3D.gradient_matrices, random affine field",
            "two_tetrahedra_skew0.0": probe_g["two_tetrahedra_skew0.0"]["max_abs_deviation"],
            "two_tetrahedra_skew0.5": probe_g["two_tetrahedra_skew0.5"]["max_abs_deviation"],
            "two_tetrahedra_skew1.0": probe_g["two_tetrahedra_skew1.0"]["max_abs_deviation"],
            "relative_deviation_range": [3.456590099922983, 7.623078781014948],
            "is_exact_to_roundoff": [probe_g[k]["is_exact_to_roundoff"] for k in
                                     ("two_tetrahedra_skew0.0", "two_tetrahedra_skew0.5",
                                      "two_tetrahedra_skew1.0")],
        },
        "impact": "The report is right and the shipped code is wrong. A consumer who trusts the docstring will treat K as a scale-certified discretisation of -div(2 mu S) and can install a dissipative-but-wrong-magnitude viscous term in the solver. This is the exact failure mode report 5 says must not happen.",
        "recommendation": "Replace the two docstring sentences with the report's own scope statement (dissipativity certified; scale/consistency NOT certified pending volume-normalised gradients).",
    },
    {
        "id": "F2",
        "severity": "medium",
        "blocking": True,
        "type": "overstated claim",
        "claim": QUOTE["attribution"],
        "evidence": {
            "energy_producing_points_alpha1": repro_summary.get("legacy_energy_producing_points"),
            "energy_producing_points_alpha0": repro_summary.get("legacy_damping0_energy_producing_points"),
            "interpretation": "alpha=0 fails on 20/41 geometries, alpha=1 on 2/41: switching the non-orthogonal correction ON removes energy production on 18 of 20 geometries, so the correction is not merely an amplifier.",
            "adjointness_defect_alpha1_max": max(r["sym_defect_a1.0"] for r in probe_e),
            "adjointness_defect_alpha0_max": max(r["sym_defect_a0.0"] for r in probe_e),
            "adjointness_defect_at_skew_0.05": [probe_e[2]["sym_defect_a1.0"], probe_e[2]["sym_defect_a0.0"]],
        },
        "impact": "The falsification of the previous attribution (non-orthogonal correction as main cause) stands, but the replacement sentence 'the correction merely amplifies it' is contradicted by the report's own count column. It matters because a reader could conclude the correction term is useless/harmful, which the data do not support.",
        "recommendation": "State both effects explicitly: the correction restores dissipativity over most of the family (20 -> 2 failing geometries) yet raises the magnitude of the residual defect at extreme skew (|E| at skew=1: 0.39 -> 4.83). Drop 'merely amplifies'.",
    },
    {
        "id": "F3",
        "severity": "medium",
        "blocking": False,
        "type": "factual claim vs repository state",
        "claim": QUOTE["default_path"],
        "evidence": {
            "live_strict_xfails_found": [
                "tests/test_native_energy_small.py:20 (the two-cell skew test cited in the report)",
                "tests/test_native_viscous_order3d.py:110 (wall-adjacent divergence O(1), a different open defect)",
            ],
            "count": 2,
            "note": "\"仓库唯一 strict xfail\" is false: at least two live strict xfails exist in tests/.",
        },
        "impact": "The 'single open debt' framing understates the repository's open-defect ledger; downstream bookkeeping (debt accounting) would be wrong.",
        "recommendation": "Say 'the two-cell skew xfail remains red' without the uniqueness claim, or enumerate the ledger.",
    },
    {
        "id": "F4",
        "severity": "medium",
        "blocking": False,
        "type": "cited evidence does not establish the claim",
        "claim": QUOTE["default_path"],
        "evidence": {
            "cited_test": "test_correction_damping_default_keeps_legacy_matrices_bitwise",
            "test_body": "NativeViscous3D(mesh, mask, 1.3) vs NativeViscous3D(mesh, mask, 1.3, correction_damping=1.) -> both use damping 1.0; the assertion is a tautology and cannot show bitwise identity with HEAD.",
            "independent_check": "commit 81a506d8 diff of src/tensorfvm/native_viscous3d.py changes active -> active*damping and active*(...) -> correction_damping*active*(...); multiplication by exactly 1.0 is exact in IEEE-754, so bitwise identity with the pre-change path does hold.",
        },
        "impact": "The claim is TRUE but the cited 'regression case' proves nothing. A future change that alters the default could keep this test green.",
        "recommendation": "Keep the claim only if backed by a golden-matrix fixture captured from the pre-change commit; otherwise mark it as 'by inspection of the diff'.",
    },
    {
        "id": "F5",
        "severity": "low",
        "blocking": False,
        "type": "artifact-count mismatch",
        "claim": QUOTE["test_count"],
        "evidence": {
            "reviewer_run": "PYTHONPATH=src pytest tests/test_native_compatible_viscous3d.py -q -> 5 passed",
            "def_count": 5,
            "tests": ["test_compatible_operator_is_symmetric_positive_semidefinite_across_skew_family",
                      "test_compatible_operator_dissipates_where_the_legacy_assembly_produces_energy",
                      "test_legacy_defect_survives_nonorthogonal_correction_damping",
                      "test_correction_damping_default_keeps_legacy_matrices_bitwise",
                      "test_invalid_arguments_are_rejected"],
        },
        "impact": "Report says 6 cases; the delivered file has 5 (the withdrawn hexa cases were already removed). Minor traceability defect.",
        "recommendation": "Correct the count to 5 (or name the withdrawn case).",
    },
    {
        "id": "F6",
        "severity": "low",
        "blocking": False,
        "type": "evidence presentation",
        "claim": QUOTE["sweep_label"],
        "evidence": {
            "actual_grid": "np.linspace(0, 1, 41) -> step 0.025 (verified in scripts/audit_compatible_viscous_dissipativity.py)",
            "published_table_rows": 14,
            "note": "The published table is a 14-row subsample (0.000-0.900 step 0.1 plus 0.925/0.950/0.975/1.000) of the 41-row sweep and is not labelled as such; the reader cannot tell the sweep grid from it.",
            "reviewer_artifact": "work/wp-2506-04/repro/report-table.md (all 41 rows regenerated)",
        },
        "impact": "Non-blocking transparency gap; no number is wrong.",
        "recommendation": "Label the table as a subsample or publish all 41 rows.",
    },
    {
        "id": "F7",
        "severity": "low",
        "blocking": False,
        "type": "framing / severity calibration",
        "claim": QUOTE["summary_legacy"],
        "evidence": {
            "first_failure_angle_deg": repro_summary.get("first_failing_angle"),
            "family_note": "illegal face orientation begins at skew>1, i.e. the legacy failure is confined to the last 5% of the family at >=86.2 deg non-orthogonality.",
            "still_real": True,
        },
        "impact": "The defect is real but sits at the extreme edge of the admissible family; readers may over-estimate its practical reach on production meshes.",
        "recommendation": "Add one sentence placing the failure at >=86 deg non-orthogonality.",
    },
    {
        "id": "F8",
        "severity": "low",
        "blocking": False,
        "type": "uninformative error metric",
        "claim": QUOTE["error_policy"],
        "evidence": {"text": "'最坏值 -3.935422（距 0 的余量 100%）' — a signed quantity has no '100% margin to zero'; the metric carries no information."},
        "impact": "Section 6 looks quantitative without being so.",
        "recommendation": "Report the certificate margin as min |E| / max |E| or as lambda_min(K) in absolute units.",
    },
]

NOT_RUN = [
    {"check": "cross-report agreement with the earlier attribution report (2468 / m2431)",
     "status": "not_run",
     "reason": "the package boundary forbids reading any report_id other than 2506; the claim '" + QUOTE["crosscheck"] + "' is therefore unverifiable by this reviewer and must be marked WITHHELD, not passed."},
    {"check": "bitwise identity against the pre-change HEAD matrix",
     "status": "partially_run",
     "reason": "verified by diff inspection of commit 81a506d8 (multiplication by exactly 1.0), not by executing a golden-matrix test (none exists)."},
    {"check": "affine consistency / second-order convergence on hexahedral interpolation meshes",
     "status": "not_run",
     "reason": "withdrawn from the producer's test set on the same grounds the reviewer confirms in F1; no reference implementation available for a repair within this package."},
    {"check": "admission of K into a solver (sparsity/bandwidth, iterative convergence)",
     "status": "not_run",
     "reason": "out of scope for a review package and explicitly left open by the report."},
]

POSITIVE = [
    {"claim": QUOTE["summary_alpha0"], "status": "supported",
     "why": "independently reproduced: alpha=0 produces energy on exactly 20 of 41 geometries (reviewer run of the producer's audit)."},
    {"claim": QUOTE["summary_compat"], "status": "supported",
     "why": "reproduced to 6 decimals: min E = -3.935422, min lambda_min(K) = 0.360339."},
    {"claim": QUOTE["psd_by_construction"], "status": "supported",
     "why": "structure checked in code: K = sum w_ij G_ij^T diag(2 mu V) G_ij with mu,V>0 is a sum of Gram matrices, hence PSD for any mesh; the 41/41 sweep is therefore a tautological sanity check, not independent physical validation (noted, not a defect, because the report says so itself)."},
]

REVIEW = {
    "reviewer_role": "red-team-reviewer",
    "reviewed_package": "wp-2506-01",
    "reviewed_report_id": "2506",
    "reviewed_source_hash": SOURCE_HASH,
    "verdict": "needs-fix",
    "judge_semantic_fidelity": True,
    "semantic_fidelity": {
        "outcome": "needs-fix",
        "numbers_fabricated": False,
        "summary": "All headline numbers reproduce exactly from the source repository with the producer's own script, and two reviewer probes confirm the central negative result. However one shipped-code docstring asserts a certification the report itself retracts (F1), one replacement attribution sentence is contradicted by the report's own table (F2), and two bookkeeping claims do not match the repository (F3, F5). No fabrication was found.",
        "severity_counts": {"high": 1, "medium": 3, "low": 4},
    },
    "scope_reviewed": {
        "report_markdown": "3382 chars, sha256 matched contract",
        "upstream_code": "src/tensorfvm/native_viscous3d.py, src/tensorfvm/native_compatible_viscous3d.py, "
                         "scripts/audit_compatible_viscous_dissipativity.py, tests/test_native_compatible_viscous3d.py",
        "reviewed_repo_head": "0f13a8d3 (TensorFVM), producer commit 81a506d8 (m2488)",
        "read_only": True,
    },
    "findings": FINDINGS,
    "supported_claims": POSITIVE,
    "checks_not_run": NOT_RUN,
    "independence_limitations": [
        "The review used the report markdown plus the upstream repository only; no producer explanation, chat or transcript was consulted.",
        "Reading any report_id other than 2506 is forbidden by the package boundary, so the cross-report consistency statement could not be checked.",
        "The local TensorFVM checkout is at 0f13a8d3, later than the producer's 81a506d8; the reviewer re-ran the producer's script there, i.e. numbers were reproduced on a drifted tree (the audit and operator files were unchanged in between, but this was not exhaustively proven).",
        "Reviewer probes measure structure (adjointness defect, affine reproduction), not a reference solution: consistency/scale of K remains unverified, exactly as the report declares.",
        "Reproduction used the producer's own geometry family and driver script; a bug present in three_tetrahedra/two_tetrahedra geometry construction would be reproduced rather than detected.",
    ],
    "reproduction": {
        "harness": "reviewer-side, output written to work/wp-2506-04/repro (source repository untouched)",
        "producer_audit_rerun": repro_summary,
        "checks": "python3 work/wp-2506-04/verify_review.py",
    },
    "disposition": "request changes — fix F1 docstring and F2 wording; F3/F5 are one-line corrections. Numbers and the falsification result are accepted as-is.",
}

ENVELOPE = {
    "package_id": "wp-2506-04",
    "task_type": "04-independent-review",
    "report_id": "2506",
    "provenance": {
        "source_hash": SOURCE_HASH,
        "source_field": "markdown",
        "producer": "wp-2506-04 red-team reviewer",
        "notes": "independent review of wp-2506-01; report 2506 read-only; every quote machine-verified verbatim against the source markdown",
    },
    "outputs": {"review_report.json": REVIEW},
}

(WP / "review_report.json").write_text(json.dumps(ENVELOPE, ensure_ascii=False, indent=1), encoding="utf-8")

# ---------------------------------------------------------------- markdown report
fig_b64 = base64.b64encode(FIG.read_bytes()).decode()
rows = repro["rows"]

def row_md(r):
    return ("| %.3f | %.2f | %.6f | %.6f | %.6f | %.6f | %.6f | %.6f |" % (
        r["skew"], r["max_nonorthogonality_degrees"],
        r["legacy_damping_1.0_rate"], r["legacy_damping_0.5_rate"], r["legacy_damping_0.0_rate"],
        r["compatible_rate"], r["legacy_damping_1.0_lambda_min"], r["compatible_lambda_min"]))

table = ("| skew | 最大非正交角° | legacy E (α=1) | legacy E (α=0.5) | legacy E (α=0) | 相容 E | legacy λmin(-DAG) | 相容 λmin(K) |\n"
         "|---|---|---|---|---|---|---|---|\n" + "\n".join(row_md(r) for r in rows))

body = f"""# KF-RESULT wp-2506-04

**tags**: `kf-wp:wp-2506-04`, `independent-review`, `red-team`, `tensorfvm`, `viscous-dissipativity`

> 审核对象 wp-2506-01（report_id=2506，sha256 `{SOURCE_HASH[7:23]}…`）。
> **判定：needs-fix / request changes**。核心数字全部复现，未发现造假；但交付代码的 docstring 声称了一个报告自己撤回的认证（F1），
> 一处替代归因措辞与报告自身表格矛盾（F2）。

---

## ① 本工序做了什么

对报告 2506《TensorFVM 粘性算子耗散性定因 + 能量相容 PSD 证书（41 几何扫掠）》做**独立红队审核**（工序 04）。边界内只读 report_id=2506 与上游仓库代码，未看生产者任何解释，未改动 TensorFVM 任何文件，未把任何结论标为 verified。

- 逐字校验：报告 markdown 3382 字符，sha256 与契约声明 `sha256:c62850b3…5138b0` **逐位一致**。
- 全量复算：用生产者自己的 `scripts/audit_compatible_viscous_dissipativity.py` 在**评审方输出目录**重跑 41 几何扫掠，逐项比对 headline 数字。
- 新增两项评审方探针（生产者未做的测量）：①能量率 E=uᵀAu 与对称部分二次型是否一致（结论：恒等，无缺陷，**自我否决的一项怀疑**）；②算子自伴缺陷 ‖A−Aᵀ‖/‖A‖（给"sum-by-parts 不成立"补上直接测量）；③仿射场梯度复现误差（判定 F1）。
- 测试与账本核对：pytest 实跑、strict xfail 实际个数、damping 钩子的提交 diff。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文**：`GET $TENSOR_API_BASE/tensor/reports/2506`（`/auth/login` 取 Bearer），落盘 `work/wp-2506-04/source_2506.md`，算 sha256 与契约比对（一致）。
2. **复算**：`PYTHONPATH=<TensorFVM>/src python3 scripts/audit_compatible_viscous_dissipativity.py --out work/wp-2506-04/repro`（**只写我自己的 worktree**，不动上游）。得到 41 行 sweep.json/csv/表/PNG。
3. **评审方探针 1**（`probe_energy_rate.py`）：对 41 几何 × 3 档 α 计算 E_full=uᵀAu 与 E_sym=uᵀsym(A)u 并比对符号。**结果差值恒为 0.0**——因为任意 A 都有 uᵀAu≡uᵀsym(A)u，评审方最初怀疑的"能量率用错矩阵"不成立，如实记录为**已排除的假线索**。顺带测出自伴缺陷 ‖A−Aᵀ‖/‖A‖ 最大 0.572（α=0）/0.397（α=1）。
4. **评审方探针 2**（`probe_affine_gradient.py`）：随机仿射场 u=Ax+b，经 `NativeViscous3D.gradient_matrices` 求单元梯度，与解析 A 比对（skew=0/0.5/1）。
5. **代码与账本核对**：`pytest tests/test_native_compatible_viscous3d.py -q`；`grep xfail(strict=True`；`git show 81a506d8 -- src/tensorfvm/native_viscous3d.py` 看 damping 钩子改动。
6. **零手抄**：所有引文由 `build_review.py` 的内锚点切片从原文提取，并断言"在原文中恰好出现一次"；`verify_review.py` 再独立复核一遍 JSON 里每条引文是否为原文子串。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `work/wp-2506-04/review_report.json` | 契约输出：判定 needs-fix、8 条分级发现（1 高 / 3 中 / 4 低）、支持项、未跑项、独立性局限 |
| `docs/kf_result_wp-2506-04.md` | 本报告（唯一 json 代码块） |
| `work/wp-2506-04/repro/sweep.json|csv|report-table.md|dissipativity-sweep.png` | 评审方独立重跑的 41 行扫掠（含报告只列 14 行的**全表**，修 F6） |
| `work/wp-2506-04/probe_energy_rate.py|.json` | 探针 1：E_full vs E_sym（差值 0.0，排除假线索）+ 自伴缺陷 |
| `work/wp-2506-04/probe_affine_gradient.py|.json` | 探针 2：仿射梯度偏离实测（F1 判据） |
| `work/wp-2506-04/reviewer-figure.png` | 左=E(skew) 复现曲线，右=**评审方新增**自伴缺陷曲线 |
| `work/wp-2506-04/verify_review.py` | 一键复核：hash、引文逐字、数字比对、判定一致性 |

## ④ 证据定位表（claim → 原文引文 / 评审方独立数字）

| 字段 | 原文引文（逐字，机器校验） | 评审方独立结果 |
|---|---|---|
| 复现 legacy 失效 | 「{QUOTE['summary_legacy']}」 | 重跑得 2 点造能、首个失效 skew=0.975/86.219° ✔ |
| 反证 α=0 | 「{QUOTE['summary_alpha0']}」 | 重跑得 **20** 点造能 ✔ |
| 相容装配证书 | 「{QUOTE['summary_compat']}」 | 重跑得 min E=−3.935422、min λmin(K)=0.360339 ✔ |
| PSD 由构造 | 「{QUOTE['psd_by_construction']}」 | 代码核对 K=Σ w Gᵀdiag(2μV)G 为 Gram 和 ✔（同时说明该扫掠是**同义反复**的实装自检） |
| 归因修正措辞 | 「{QUOTE['attribution']}」 | ✘ 与自身表格矛盾：α=0 20/41 vs α=1 2/41，修正**修好了 18 个几何**（F2） |
| 默认路径未改 | 「{QUOTE['default_path']}」 | 结论真（diff：×1.0 精确），但所述"回归用例"是比较 1.0 与 1.0 的**同义反复**（F4）；且"唯一 strict xfail"不实（F3） |
| 标度未认证 | 「{QUOTE['not_certified']}」 | 报告此项真实且重要：「{QUOTE['gradient_deviation']}」 |
| 交付代码 docstring | （代码，非原文）"affine velocity fields the cell gradients are exact … the coefficient of the operator is certified" | ✘ 实测偏离 5.685 / 8.037 / 7.696（相对 3.46–7.62 倍），**docstring 与被审报告自相矛盾**（F1） |
| 用例数 | 「{QUOTE['test_count']}」 | ✘ 实跑 5 passed（F5） |
| 跨报告一致性 | 「{QUOTE['crosscheck']}」 | ⚠ WITHHELD：越界不可读（只许碰 2506），不得判 pass |
| 误差政策 | 「{QUOTE['error_policy']}」 | 判据选择恰当 ✔；但"距 0 的余量 100%"无信息（F8） |

## ⑤ 复现的数字表（评审方重跑，41/41 全表）

{table}

> 全表 41 行与报告 14 行子表在重叠行上**逐位一致**（如 skew=0.300：−9.382056 / −0.386190 / −0.898237 / +8.144633 / +0.362769）。

![reviewer](reviewer-figure.png)

图注：左=评审方在 41 几何上重跑的 E(skew)（legacy α=1/0.5/0 三档，零线与 2 个造能点）；右=**评审方新增**的算子自伴缺陷 ‖A−Aᵀ‖/‖A‖(skew)，用于把「sum-by-parts 不成立」从"由症状推断"变成"直接测量"（最大值 α=0 0.572 / α=1 0.397）。PNG 见 `work/wp-2506-04/reviewer-figure.png`，同时以 `figures[0].png_base64` 随报告发布。

## ⑥ 注意点与局限

- **不能读别的报告**：跨报告一致性（m2431/2468）与"默认路径与 HEAD 逐位相同"的黄金矩阵均**未跑/仅间接**，标 not_run 而非 pass。
- **树有漂移**：本地 TensorFVM 在 `0f13a8d3`，生产者为 `81a506d8`；复跑在漂移树上完成（相关文件期间未变，但未穷证）。
- **只测结构、不比参考解**：评审方探针测的是自伴缺陷与仿射复现误差，K 的绝对标度/一致性仍**未认证**——这与报告自述一致，不是评审方新判据。
- **同源风险**：几何族与驱动脚本用生产者的，若 `two_tetrahedra` 造形本身有错，复跑只会复现它。
- **假线索已排除并记录**：最初怀疑"能量率应取对称部分、报告取了全矩阵"→ 实测两者恒等（差值 0.0），故不作为发现，避免冤枉上游。

## ⑦ 误差判定（是否 <3%）

| 关键量 | 报告值 | 评审方复算 | 相对误差 | <3%？ |
|---|---|---|---|---|
| 造能几何数（α=1） | 2 | 2 | 0 | **是** |
| 首个失效 skew / 角度 | 0.975 / 86.22° | 0.975 / 86.219° | 0 | **是** |
| 造能几何数（α=0） | 20 | 20 | 0 | **是** |
| min E（相容） | −3.935422 | −3.9354221 | 2.2e−8 | **是** |
| min λmin(K) | +0.360339 | +0.3603387 | 8.4e−7 | **是** |
| legacy E @ skew=1（α=1） | +4.832805 | +4.8328045 | 1.0e−7 | **是** |
| 仿射梯度偏离（K 标度正确性） | "最大 6.17" | 5.685–8.037（不同网格/场） | — | **无解析基准**：该量本身即偏差度量，报告已声明标度未认证，故不适用"<3%"，显式留白 |

**结论**：可复算的数字**全部 0 误差复现**（<3% 满足）；不可复算的是"标度一致性"这一**报告自己声明未认证**的项，评审方**维持未认证**，不代其认证。

## ⑧ 自检（逐条对照 acceptance）

- [x] `valid_json`：review_report.json 由 build_review.py 序列化，verify_review.py 再解析校验。
- [x] `schema_pass`：信封顶层仅 package_id/task_type/report_id/provenance/outputs，`task_type` 匹配 `^[0-9]{{2}}(-[a-z0-9-]+)?$`，`package_id` 匹配 `^wp-…-[0-9]{{2}}$`，provenance 含 source_hash/source_field。
- [x] `reviewer_independent`：评审 Prompt 由本包自拟（未复制生产者）；上下文=报告原文+上游 KO，**未看生产者解释**；新增 3 项生产者未做的探针，并**自我否决 1 项假线索**。
- [x] `upstream_packages_completed`：审核对象 wp-2506-01 的产物（报告 2506 + 代码/脚本/测试）在仓库中均可取到并实跑通过（5 passed）。
- [x] `do_not_mark_claims_as_verified`：判定 needs-fix；跨报告项标 WITHHELD；标度项维持未认证。
- [x] 只碰 report_id=2506：未读/未写其它报告；TensorFVM 只读，产物全在本 worktree。
- [ ] **未完成/如实留白**：F1 的 docstring 修复与 F2 的措辞修订属**上游仓库改动**，本单边界内不改——留作 wp-2506-01 的返工项。

## ⑨ 一键复跑

```
bash work/wp-2506-04/repro_cmd.sh
```

等价展开：取原文+校验 hash → 在 `work/wp-2506-04/repro` 重跑生产者扫掠 → 跑两项探针 → `verify_review.py`（引文逐字 + 数字比对 + 判定一致性）。
"""

envelope_block = json.dumps(ENVELOPE, ensure_ascii=False, indent=1)
markdown = body + f"""
## \u2469 结果信封（契约要求的唯一 json 代码块）

```json
{envelope_block}
```
"""

(WP / "kf_result_wp-2506-04.md").write_text(markdown, encoding="utf-8")
(ROOT / "docs" / "kf_result_wp-2506-04.md").write_text(markdown, encoding="utf-8")

payload = {
    "title": "KF-RESULT wp-2506-04",
    "summary": ("独立红队审核 wp-2506-01：41 几何扫掠与 headline 数字 0 误差复现（造能数 2/20、min E −3.935422、min λmin +0.360339 全中），"
                "未发现造假；判 needs-fix——交付代码 docstring 声称仿射梯度精确/系数已认证，而评审方实测偏离 5.69–8.04 且被审报告自述撤回该认证（F1）；"
                "「修正项只是把它放大」被报告自身表格反证（α=0 20/41 vs α=1 2/41，修正修好 18 个几何，F2）；"
                "「唯一 strict xfail」不实（实存 2 个）、「6 条用例」实为 5 条。新增评审方自伴缺陷测量（‖A−Aᵀ‖/‖A‖ 最大 0.572）补上 SBP 归因的直接证据；"
                "并自我否决一项假线索（uᵀAu≡uᵀsym(A)u，差值 0.0）。"),
    "scenario_key": "tensorfvm/verification/compatible-viscous-dissipativity",
    "mission_id": 15825,
    "tags": ["kf-wp:wp-2506-04", "independent-review", "red-team", "TensorFVM", "viscous-dissipativity", "review"],
    "markdown": markdown,
    "figures": [{"name": "reviewer-sweep-and-adjointness.png",
                 "caption": "评审方独立重跑：左=E(skew) 三档阻尼复现曲线；右=评审方新增的算子自伴缺陷 ‖A−Aᵀ‖/‖A‖，直接支撑「sum-by-parts 不成立」归因",
                 "png_base64": fig_b64}],
}
pathlib.Path("/tmp/kf_publish_wp-2506-04.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

print("wrote", WP / "review_report.json")
print("wrote", ROOT / "docs" / "kf_result_wp-2506-04.md")
print("figure bytes", len(FIG.read_bytes()), "b64", len(fig_b64))
print("quotes verified:", len(QUOTE))
print("json blocks in md:", markdown.count("```json"))