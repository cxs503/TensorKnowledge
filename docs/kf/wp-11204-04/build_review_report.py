#!/usr/bin/env python3
"""wp-11204-04 · build the independent review payload from the frozen source + checks.

Writes `review_report.json` and `kf_result.json`. Findings carry verbatim anchors that are
re-verified here against `source/report_11204.md` (substring + declared line), so a quote
that drifts out of the report breaks the build instead of rotting silently.

Usage:  python docs/kf/wp-11204-04/build_review_report.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import review_checks as rc

PKG = Path(__file__).resolve().parent
SOURCE = PKG / "source" / "report_11204.md"
UPSTREAM = PKG / "source" / "upstream_wp-11204-01.kf_result.json"
REVIEW_OUT = PKG / "review_report.json"
KF_OUT = PKG / "kf_result.json"

REVIEWER = "agent/m19783"
MIN_QUOTE = 12
RECORD_TITLE = "FEM 弹塑性本构(von Mises J2)与 3D 混合模式 cohesive 单元：CT / 三点弯曲验证"
SCENARIO = "p273w3-n01-fem-elastoplastic-cohesive"

FINDINGS = [
    dict(
        finding_id="F1",
        severity="medium",
        blocking=False,
        category="unverifiable_setup",
        title="弹性 J / SE(B) J 的评估载荷未在报告中给出，两行基准无法独立复算",
        detail=(
            "数据表把 peak load（P_Q = 34725 N）与 J 并排列出，但 CT 弹性 J = 1957.7 J/m² 只有在 "
            "P ≈ 12.0 kN 时才成立：按 ASTM E399 CT 几何因子 f(0.5)=9.659 与 J=K²(1−ν²)/E 反算，"
            "P_Q 下的弹性 J 应为 ≈1.638e4 J/m²（8.4 倍）。SE(B) 同理：136.34 J/m² 对应 P ≈ 2.0 kN，"
            "而 LEFM 峰值载荷为 7782 N。报告另外在图 1 使用 P = 45 kN。三处载荷互不相同，"
            "文中没有任何一处声明 J 是在哪个载荷下取值，故 C2（弹性）与 C2（SE(B)）两行无法被独立复算，"
            "读者也容易把它误读为峰值载荷下的弹性 J。"
        ),
        anchor="| CT 弹性 J [J/m²] | 1957.7 | K²(1−ν²)/E = 1956.1 | +0.081% |",
        impact=(
            "相对误差本身（+0.081% / +3.202%）与载荷无关，只要两列同载荷取值就成立，所以判据结论不受影响；"
            "受影响的是可核验性：审阅者无法从报告文字重建该对照，也无从判断 CT 弹塑性 J 行（隐含载荷更高、"
            "J_pl/J=0.191）与弹性行是否同一算例序列。"
        ),
        recommended_fix=(
            "在载荷/J 对照表增加「评估载荷 [N]」列（或在 §② 判据层声明 J 的取样载荷），"
            "并说明 Fig.3 左图横轴载荷范围；SE(B) 一行同样标注取样载荷。"
        ),
        evidence_check_ids=["C7_elastic_J_load_level", "C4_table_arithmetic"],
    ),
    dict(
        finding_id="F2",
        severity="low",
        blocking=False,
        category="internal_inconsistency",
        title="同一误差在判据总表与数据表中符号相反（C1、C1b），且 C1b 数值差 0.004 pp",
        detail=(
            "判据总表写 C1「+0.104%」、C1b「+1.385%」，而同页数据表与 §⑥ 写「-0.104%」「-1.385%」。"
            "重算 (34689−34725)/34725 = -0.1037%，(7674−7782)/7782 = -1.3888%：数据表与 §⑥ 的符号正确，"
            "判据总表两处符号错误；此外 C1b 的 -1.385% 与重算值 -1.389% 相差 0.004 pp（其余四项 ≤0.003 pp）。"
        ),
        anchor="| C1 CT 峰值载荷误差 | +0.104% | <5% | PASS | P_fem=34689 N vs ASTM P_Q=34725 N |",
        impact=(
            "不影响任何判据的 PASS/FAIL（各项均远离门限），但符号是误差方向的语义载体："
            "+0.104% 会被读成“偏硬”，实际是 FEM 峰值偏低于 ASTM P_Q。"
        ),
        recommended_fix="判据总表 C1/C1b 改为 -0.104% / -1.389%，并统一各处保留位数（3 位小数）。",
        evidence_check_ids=["C8_sign_consistency", "C4_table_arithmetic"],
    ),
    dict(
        finding_id="F3",
        severity="low",
        blocking=False,
        category="evidence_gap",
        title="§⑤ 三个过程性百分比（-50% / -82% / 58%）只出现在散文里，无数据表或工件支撑",
        detail=(
            "「实测 J 偏小 50%（CT）/ 82%（SE(B)）」「初版取 K_n = 1e14 时峰值载荷偏低 58%」是报告"
            "唯一的负控证据，但没有对应的结果表、网格/参数扫描记录或工件文件名，审阅者只能接受断言。"
            "这三点恰是报告最有复用价值的知识（半模型 EDI 陷阱、界面刚度自洽条件），缺证据会削弱其可迁移性。"
        ),
        anchor="实测 J 偏小 50%（CT）/ 82%（SE(B)）",
        impact="不影响主判据；降低 §⑤ 教训条目的证据等级（原文可定位，但不可从已声明工件复算）。",
        recommended_fix=(
            "把三组负控（半模型 vs 完整模型、K_n=1e14 vs 1e16 的载荷）补进 verification.json / acceptance.json "
            "的负控表，并在 §⑤ 引用表号。"
        ),
        evidence_check_ids=["C12_anecdote_evidence"],
    ),
    dict(
        finding_id="F4",
        severity="info",
        blocking=False,
        category="ambiguous_claim",
        title="材料表 SE(B) 列「塑性 同左」，但 SE(B) 的验证路径是弹性 + cohesive，无塑性项",
        detail=(
            "几何/材料表把 σ_y 与硬化 H 以「同左」赋予 SE(B)，然而 SE(B) 的判据（J vs K²(1−ν²)/E、"
            "粘聚区峰值载荷 vs LEFM）全部是线弹性 + 界面损伤口径，正文未说明 SE(B) 算例是否真的带 J2 塑性。"
            "若不带，该列表格项属于冗余；若带，则 J 的对照缺少 J_pl 项说明。"
        ),
        anchor="| 塑性 | sigma_y = 1000 MPa (小范围屈服) / 350 MPa (弹塑性), 线性硬化 H = 20 / 10 GPa | 同左 |",
        impact="读者无法判断 SE(B) 是否为弹塑性算例；对结论无影响（该行对照本身是弹性口径）。",
        recommended_fix="SE(B) 列改为「—（弹性 + cohesive）」或注明塑性参数未被该算例使用。",
        evidence_check_ids=["C3_anchors_verbatim"],
    ),
    dict(
        finding_id="F5",
        severity="info",
        blocking=False,
        category="unverifiable_setup",
        title="平台记录摘要称「pytest 40 项全绿含 5 项负控」，markdown 内无「5 项」出处",
        detail=(
            "报告 markdown 的复现段只写「40 项，含负控」，没有负控计数；「5 项」只出现在平台记录 summary，"
            "而 summary 不在 source_field=markdown 的哈希覆盖范围内，本审核无法从被审字节核验该数字。"
            "同时 40 项测试、scripts/m9422_run_verification.py 与本报告引用的 artifacts/m9422/*.json "
            "都不在本工作树（TensorPhysics 仓）内，未执行。"
        ),
        anchor=None,
        no_report_anchor_reason="该断言位于平台记录 summary 字段，不在被审 markdown 字节内，故无可锚定原文行",
        impact="不构成对报告正文的指控；仅说明该项证据等级为 WITHHELD（未执行/未交付）。",
        recommended_fix="若摘要保留「5 项负控」，在 markdown 复现段写出负控清单（负控名称 + 期望失败模式），使数字可定位。",
        evidence_check_ids=["C2_upstream_pinned"],
    ),
]

CHECKS_NOT_RUN = [
    "执行 tests/test_fem_elastoplastic_cohesive3d.py（40 项）与 scripts/m9422_run_verification.py：TensorPhysics 仓不在本工作树，无法运行",
    "比对 artifacts/m9422/verification.json / acceptance.json 原始数字：报告未随附工件，本工作树亦无该仓检出",
    "图 1–3 的像素/场量核查（σ_yy 云图是否与 P=45 kN、J2 平面应变一致）：figures/m9422/*.png 不在本工作树",
    "核验 §⑤ 三个负控百分比（-50%/-82%/58%）与 58% 所依赖的 K_n=1e14 算例：无工件、无脚本入参记录",
    "核验 J2 一致切线中心差分 <1e-6、δ0≈δf 退化、Newton 失败步折半后 60 步全收敛等实现级断言：需读源码/运行，均未做",
    "核验网格收敛序列的单元数与网格几何（CT n_y 12→40 的 1392→4640 单元）是否与生成的网格一致：需网格文件",
]


def main() -> dict:
    md = SOURCE.read_text(encoding="utf-8")
    lines = md.split("\n")
    upstream = json.loads(UPSTREAM.read_text(encoding="utf-8"))
    checks = rc.run()
    h = checks["source_hash_recomputed"]

    findings = []
    for f in FINDINGS:
        f = dict(f)
        a = f["anchor"]
        if a is None:
            assert f.get("no_report_anchor_reason")
            f["anchor_line"] = None
        else:
            assert len(a) >= MIN_QUOTE, f["finding_id"]
            assert a in md, (f["finding_id"], "anchor not verbatim")
            ln = rc.line_of(md, a)
            assert a in lines[ln - 1], f["finding_id"]
            f["anchor_line"] = ln
        # every non-info finding must rest on a red check
        if f["severity"] != "info":
            red = set(checks["summary"]["failing"])
            assert set(f["evidence_check_ids"]) & red, f["finding_id"]
        assert set(f["evidence_check_ids"]) <= set(checks["checks"]), f["finding_id"]
        findings.append(f)

    blocking = sum(1 for f in findings if f["blocking"])
    review = {
        "review_id": "wp-11204-04",
        "package_id": "wp-11204-04",
        "report_id": "11204",
        "contract_version": "1.0",
        "review_type": "04-independent-review",
        "review_report_version": "1.0.0",
        "reviewed_at": "2026-11-14",
        "report_title": RECORD_TITLE,
        "provenance": {
            "source_uri": "tensor://reports/11204",
            "source_field": "markdown",
            "source_hash": h,
            "source_hash_matches": True,
            "chars": len(md),
            "bytes_utf8": len(SOURCE.read_bytes()),
            "scenario_key": SCENARIO,
            "frozen_copy": "docs/kf/wp-11204-04/source/report_11204.md",
        },
        "reviewer": {
            "identity": REVIEWER,
            "role": "red-team-reviewer",
            "producer_identity": upstream["provenance"]["producer"],
            "upstream_report_branch": "agent/m9422",
            "independence": {
                "independent": True,
                "reviewer_is_producer": False,
                "context_inputs": ["report markdown (byte-frozen)", "upstream wp-11204-01 asset_manifest/kf_result"],
                "context_excludes_producer_explanation": True,
                "producer_explanation_available": False,
                "review_prompt_authored_by_reviewer": True,
                "review_prompt_copied_from_producer": False,
                "note": "审核问题清单由审阅人自拟（哈希一致性、表内算术、BK 律重算、E399 几何因子反算、符号/门限一致性），未采用生产者提供的任何解释或待答清单。",
            },
        },
        "reviewed_package": {
            "package_id": "wp-11204-01",
            "task_type": "01-asset-registration",
            "producer": upstream["provenance"]["producer"],
            "artifacts_used": {
                "source/report_11204.md": h,
                "source/upstream_wp-11204-01.kf_result.json": rc.sha256_text(UPSTREAM.read_text(encoding="utf-8")),
            },
            "upstream_packages_completed": True,
            "upstream_pinned_hash_matches": upstream["provenance"]["source_hash"] == h,
            "note": "report 11204 仅登记了 01（资产登记）；本单审核对象为 wp-11204-01 与报告正文。",
        },
        "scope": {
            "reviewed_artifacts": [
                "report 11204 markdown（5999 chars，sha256 逐字重算）",
                "wp-11204-01 kf_result.json / asset_manifest.json（上游登记产物）",
                "判据总表、载荷/J 对照表、3D 混合模式表、网格收敛表、§⑥ 误差判定表（全部数值重算）",
            ],
            "checks_performed": [f"{c['title']} — {c['detail']}" for c in checks["checks"].values()],
            "checks_not_run": CHECKS_NOT_RUN,
            "out_of_scope": [
                "出题/生产者的运行日志与解释",
                "其余 report_id 的任何内容",
                "verification 级别判定（由平台门计算，本审核不设置）",
            ],
        },
        "checks": [
            {"check_id": cid, "title": c["title"],
             "status": "pass" if c["pass"] else "finding",
             "detail": c["detail"]}
            for cid, c in checks["checks"].items()
        ],
        "checks_summary": {"n_checks": checks["summary"]["n_checks"],
                           "n_pass": checks["summary"]["n_pass"],
                           "n_finding": checks["summary"]["n_finding"]},
        "findings": findings,
        "finding_counts": {"blocking": blocking,
                           "non_blocking": len(findings) - blocking,
                           "by_severity": {s: sum(1 for f in findings if f["severity"] == s)
                                           for s in ("critical", "high", "medium", "low", "info")}},
        "semantic_fidelity": {
            "verdict": "faithful_with_notes",
            "reproduced": {
                "criterion_rows": 6,
                "table_errors_reproduced": "5/5 在 0.003 pp 内",
                "bk_law_rows_reproduced": "7/7 在 0.05 J/m² 内",
                "cohesive_delta_ratio": "0.009 精确复现",
                "section6_lt3pct_verdicts": "6/6 与算术一致（含 2 项 honest-FAIL）",
            },
            "not_reproducible": ["C2 弹性 J / SE(B) J 的评估载荷（见 F1）",
                                 "§⑤ 三个过程性百分比（见 F3）"],
            "honesty_assessment": "§⑥ 显式承认 6.05% 与 3.20% 两项 >3%，且未把它们的美化写进判据门限（门限 <8% 为自定，报告已写明），未发现粉饰。",
        },
        "overstated_claims": [
            {
                "claim": "6 项机器判据全部 PASS",
                "issue": "判据行数与 PASS 判定均与正文一致（重算 6/6），但其中 C2 两行的基准在未声明载荷下取值，PASS 的可核验性弱于其余四项。",
                "correction": "补评估载荷后，该断言才成为完全可复核的机器判据。",
                "anchored": True,
            },
            {
                "claim": "pytest 40 项全绿含 5 项负控（平台记录摘要）",
                "issue": "markdown 仅写「40 项，含负控」，无「5 项」出处；测试未在本工作树执行。",
                "correction": "摘要与正文口径统一，并列出负控清单。",
                "anchored": False,
            },
        ],
        "decision": {
            "verdict": "approve_with_notes",
            "blocking_findings": blocking,
            "rationale": (
                "报告的核心数字在自身表格内可复算（5 项相对误差重算最大差 0.003 pp）、3D 混合模式解析列可由 "
                "扩展 BK（G_Ic=200, G_shear,c=600, η=1.5）逐点复现（≤0.05 J/m²）、粘聚参数自洽（δ0/δf=0.009）、"
                "网格序列单调、6 项判据的 PASS/FAIL 与门限一致，且 §⑥ 诚实标注两项 >3%。"
                "不存在阻断性错误；需修的是可核验性（F1 评估载荷缺失）与两处符号（F2），以及负控证据入表（F3）。"
            ),
            "not_asserted": [
                "不声明本报告的任何结论已被平台验证（verification 由平台门计算，审核不设置该字段）",
                "不声明 pytest 40 项 / 40 项含 5 项负控已通过（未执行）",
                "不声明图 1–3 与场量云图正确（未取到图件）",
            ],
        },
        "remediation": [
            "F1：J 对照表增加「评估载荷 [N]」列，或声明 J 的取样载荷与 Fig.3 横轴范围（阻断复算的唯一项）",
            "F2：判据总表 C1/C1b 误差符号改为负号，C1b 数值改为 -1.389%，三处保留位数统一",
            "F3：§⑤ 三个负控百分比补进 verification.json/acceptance.json 的负控表并在正文引用表号",
            "F4：SE(B) 材料列注明塑性参数未被该算例使用（或注明为弹性算例）",
            "F5：摘要「5 项负控」与正文口径对齐，正文给出负控清单",
        ],
        "independence_limitations": [
            "仅据报告 markdown 与上游 01 产物审核，未读取生产者的解释、日志或对话记录（约束要求的隔离），因此无法判断数字是怎样生成的，只能判断其是否可复算。",
            "TensorPhysics 源码（src/tensorphysics/fem_nonlinear/）与 scripts/m9422_*、artifacts/m9422/*.json 不在本工作树，实现级与运行级断言（一致切线误差、60 步收敛、40 项 pytest）全部未执行，证据等级 WITHHELD。",
            "F1 的判定依赖 ASTM E399 几何因子与 J=K²(1−ν²)/E 的教科书形式；若生产者的 CT/SE(B) 尺寸比或约束条件与 ASTM 标准比例不同，隐含载荷的数值会变，但“报告中未给出评估载荷”这一事实不变。",
            "图件未取到，图 1–3 与正文数字的一致性未核查。",
            "本审核为单审阅人执行，未做交叉复核（sample_rate=1.0，全量而非抽样）。",
        ],
        "acceptance_selfcheck": {
            "valid_json": True,
            "schema_pass": True,
            "reviewer_independent": True,
            "upstream_packages_completed": True,
            "do_not_mark_claims_as_verified": True,
            "notes": "schema 由 tests/test_wp_11204_04_independent_review.py 现场校验；upstream_packages_completed 以 wp-11204-01 kf_result 存在且哈希一致为依据（该报告未派生 02/03 包）。",
        },
        "evidence_summary": {
            "source_hash_recomputed": h,
            "n_anchors_verified": sum(1 for f in findings if f.get("anchor")),
            "n_fabricated_or_misplaced_quotes": 0,
            "n_checks": checks["summary"]["n_checks"],
            "n_checks_failing": checks["summary"]["n_finding"],
            "checks_artifact": "docs/kf/wp-11204-04/checks/independent_checks.json",
        },
        "repro_cmd": (
            "python docs/kf/wp-11204-04/review_checks.py && "
            "python docs/kf/wp-11204-04/build_review_report.py && "
            "python -m pytest tests/test_wp_11204_04_independent_review.py -q"
        ),
    }

    REVIEW_OUT.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    kf = {
        "package_id": "wp-11204-04",
        "task_type": "04-independent-review",
        "contract_version": "1.0",
        "report_id": "11204",
        "provenance": {
            "source_uri": "tensor://reports/11204",
            "source_field": "markdown",
            "source_hash": h,
            "source_hash_matches": True,
            "title": RECORD_TITLE,
            "scenario_key": SCENARIO,
            "chars": len(md),
        },
        "outputs": {"review_report.json": review},
    }
    KF_OUT.write_text(json.dumps(kf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {REVIEW_OUT.relative_to(PKG.parents[2])} and {KF_OUT.relative_to(PKG.parents[2])}")
    print(f"findings={len(findings)} blocking={blocking} verdict={review['decision']['verdict']}")
    return kf


if __name__ == "__main__":
    main()