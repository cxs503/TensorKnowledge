#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wp-5577-04 · 审核证据数据（引文 / 发现 / claim 判定）。

零手抄纪律：QUOTES 里的每一段都必须在本脚本运行时被断言为 report-5577 markdown 的
逐字子串（见 wp5577_review.py: assert_quotes()）。发现与 claim 判定只允许引用 QUOTES 中的字符串，
或引用上游记录的结构化字段（record.summary 等，明确标注为字段而非正文引文）。
"""

# 报告自述的几何/工况（取自 report 5577 的表格与正文）
LPP, B, T = 230.0, 32.2, 10.8
NABLA = 52030.0
CB_TAB, CM_TAB, CWP_TAB = 0.6509, 0.9849, 0.7630
S = 8975.0
G = 9.81
KN = 0.5144444444444445          # 1 kn -> m/s

# 审核假设（报告未声明，反解/惯例值；写成假设而非事实）
RHO_ASSUMED = 1025.0             # kg/m3
DCF_ASSUMED = 4.0e-4             # ITTC-1978 粗糙度补贴

# ③ 主表逐行：(V[kn], Fn, Re, Cf, Cr, Rf[kN], Rw[kN], RT[kN], Ct)
ROWS = [
    (12.00, 0.1300, 1.193e9, 0.00150, 0.00002, 332.6, 2.6, 335.2, 0.00191),
    (15.00, 0.1625, 1.491e9, 0.00146, 0.00009, 508.7, 24.0, 532.7, 0.00194),
    (18.00, 0.1949, 1.790e9, 0.00143, 0.00028, 720.1, 109.4, 829.4, 0.00210),
    (21.00, 0.2274, 2.088e9, 0.00140, 0.00061, 966.2, 330.2, 1296.4, 0.00242),
    (24.00, 0.2600, 2.387e9, 0.00138, 0.00109, 1246.8, 764.8, 2011.6, 0.00287),
]

FIXED_RT = 2011.61
BASE_RT = 2005.99
MOCK_RT = 6882.59
DEPLOYED_RT = 7401.24
MOCK_CR = 0.008036
KVLCC2_RT = 1621.66
KVLCC2_BASE = 1960.0
KVLCC2_CB = 0.8098               # KVLCC2 公开船型参数（仅用于复核 Cwp 回归，见 F/C9）

QUOTES = {
    "q_formula_decomposition": "R_T=(1+k)R_F+R_W+R_B+R_TR+R_A+R_APP",
    "q_rw_formula": "R_W = c1·c2·c5·∇·ρg·exp(m1·Fn^d + m2·cos(λ·Fn^-2))，d = -0.9",
    "q_geom_row": "| 几何先验（Cb 反算偏差） | 0.0617（<1% 通过） | % |",
    "q_mock_cr_formula": "Cr 原为 `Cr = 0.005·C4(Fn)·C1·C2·C3` 分段多项式 mock",
    "q_fix_formula": "Cr = R_W(V)/(½ρV²S)",
    "q_universal_claim": "按 Fn 分段的多项式",
    "q_universal_claim_2": "段产生成倍偏差——本单发现的缺陷即源于此。",
    "q_row_12kn": "| 12.00 | 0.1300 | 1.193e+09 | 8975 | 0.00150 | 0.00002 | 332.6 | 2.6 | 335.2 | 0.00191 |",
    "q_row_24kn": "| 24.00 | 0.2600 | 2.387e+09 | 8975 | 0.00138 | 0.00109 | 1246.8 | 764.8 | 2011.6 | 0.00287 |",
    "q_method_label": "ITTC-57摩擦阻力 + ITTC-1978粗糙度补贴 + Holtrop-Mennen(1984)兴波阻力(physics.holtrop 单一源)",
    "q_calls": "调用 8 次全部按契约行事",
    "q_latency": "延迟 p50 0.004 s；",
    "q_pytest": "回归测试 41 passed, 3 skipped, 1 warning in 1.25s",
    "q_gate": "报告门 8/8；工件索引 20 条，复算命中",
    "q_gate2": "20/20。",
    "q_tbl2_mock": "| 修复前（mock） | 0.008036 | 6882.59 | 243.10 |",
    "q_tbl2_fixed": "| 修复后（工作树临时实例） | 0.001091 | 2011.61 | 0.28 |",
    "q_tbl2_deployed": "| 部署实例 http://127.0.0.1:8002（旧构建） | 0.008036 | 7401.24 | 268.96 |",
    "q_drift": "常驻 8002 是旧构建，同点仍返回 7401.24 kN",
    "q_figures": "见内嵌附图",
    "q_no_form_factor": "端点无 (1+k)/附体通道，与含形因子的全尺度数据对标系统性偏低约",
    "q_no_efd": "未取得 KCS 水池试验原始数据表，单一源对标属同级而非",
    "q_v2_row": "| V2 | KCS 设计点总阻力 Rt（单一物理源对标） | 2011.61 | 2005.99 | kN | 0.280 | 是 |",
    "q_v4_row": "| V4 | KVLCC2 全尺度 Rt vs 文献（含附体/形因子） | 1621.66 | 1960.0 | kN | -17.262 | 否 |",
    "q_honest_fail": "**HONEST-FAIL**：V4（KVLCC2 全尺度，偏差 -17.26%）与 V3",
    "q_cwp_old": "KCS 给 0.913，实船 0.763",
    "q_cwp_new": "Momo/Schneekluth 回归 (1+2Cb)/3",
    "q_cwp_values": "（KCS 0.767、KVLCC2 0.873）",
    "q_holtrop_domain": "Holtrop 适用域 Fn 0.10–0.45",
}

# 上游 wp-5577-01 的 record.summary 片段（字段引文，非 report-5577 正文）
UPSTREAM_SUMMARY_CLAIM = "登记 21 资产（resolved 2 / unresolved 19），27 条 locator 全部逐字回解"
UPSTREAM_SCOPE_CLAIM = "01-asset-registration for report 5577"


def findings(up: dict, rows: list[dict], max_dev: dict, dev: dict, geom: dict, fit: dict,
             probe: dict | None = None) -> list[dict]:
    """严重度排序：blocking > medium > low > info。本单无 blocking 项（见 verdict）。"""
    r12, r24 = rows[0], rows[4]
    return [
        {
            "finding_id": "F1", "severity": "medium", "blocking": False,
            "title": "① 的阻力分解公式与 ③ 的实算口径不一致：实算无 (1+k)，也无 R_B/R_TR/R_A/R_APP",
            "claim_quote": QUOTES["q_formula_decomposition"],
            "evidence": [QUOTES["q_formula_decomposition"], QUOTES["q_no_form_factor"],
                         QUOTES["q_row_24kn"]],
            "analysis": "① 声明 R_T=(1+k)R_F+R_W+R_B+R_TR+R_A+R_APP；③ 主表逐行满足 RT=Rf+Rw"
                        f"（最大残差 {max_dev['RT_dev_kN']} kN，0.1 kN 舍入级），Rf 已含 ΔCf 粗糙度补贴、不含形因子 (1+k)。"
                        "报告在 ⑤ 用『端点无 (1+k)/附体通道』解释 V4 的 -17.3%，但 ③ 未写出实际采用的定义式，"
                        "于是同一份报告里『声明的模型』与『算出的模型』不是同一个；下游 claim 抽取照抄 ① 会得到错误的能力画像。",
            "reproduction": "python3 scripts/wp5577_review.py（C8 明细 numeric_recomputation.rows[*].RT_dev_kN ≤0.1 kN；Rf 需 ΔCf≈4.0e-4 才闭合）",
            "remediation": "③ 表头/⑤ 增一行显式定义式 R_T,impl=(C_f+ΔC_f+C_r)·½ρV²S，注明 R_B=R_TR=R_A=R_APP=0、形因子通道缺失，并给出 ρ/ν/ΔCf 取值与出处。",
        },
        {
            "finding_id": "F2", "severity": "medium", "blocking": False,
            "title": "关键常数（ρ、ν、ΔCf、S）无出处，数字只能反解、不可唯一复现",
            "claim_quote": QUOTES["q_method_label"],
            "evidence": [QUOTES["q_method_label"], QUOTES["q_row_12kn"], QUOTES["q_row_24kn"]],
            "analysis": "报告给出 Cf 与 Rf 两列，二者只差一个未声明的 ΔCf；ρ、ν 同样未给。"
                        f"以 (ρ,ΔCf) 联合反解得 ρ≈{fit['rho_best']}、ΔCf≈{fit['dCf_best']}（跨行相对离散 {fit['max_cross_row_rel_spread']:.1e}），"
                        "说明 5 行数据自洽，但 (ρ,ΔCf) 退化：ρ=1018/ΔCf=4.1e-4 与 ρ=1025/ΔCf=4.0e-4 都落在舍入误差内。"
                        "『零手抄可逐字定位』的可审计性因此在这一列断链——第三方只能反解、不能复算。",
            "reproduction": "python3 scripts/wp5577_review.py（C8 detail.assumptions 与 numeric_recomputation.rho_dcf_fit）",
            "remediation": "③ 增列 ρ[kg/m³]、ν[m²/s]、ΔCf（注明 ITTC-1978 出处），S=8975 m² 附几何来源。",
        },
        {
            "finding_id": "F3", "severity": "medium", "blocking": False,
            "title": "两个『修复前』数字互不相容（6882.59 vs 7401.24），报告仅以『旧构建』带过",
            "claim_quote": QUOTES["q_tbl2_deployed"],
            "evidence": [QUOTES["q_tbl2_mock"], QUOTES["q_tbl2_deployed"], QUOTES["q_drift"],
                         QUOTES["q_mock_cr_formula"]],
            "analysis": f"按 ② 的 mock 式 Cr=0.008036 与同表 Rf，24 kn 应得 RT≈{dev['mock_RT_recomputed_from_Cr']} kN"
                        f"（与报告的 {MOCK_RT} kN 差 {dev['mock_RT_dev_pct']}%，成立）；而部署实例 7401.24 kN 反解 Cr≈"
                        f"{dev['deployed_Cr_implied_by_RT']}（比 mock 高 {(dev['deployed_over_mock_Cr_ratio']-1)*100:.1f}%）。"
                        "两行都标『修复前』却由不同公式/不同缺省所生，报告未给差异机制（⑤ 只说『旧构建』）——"
                        "应显式标 WITHHELD 或给出差异来源（如旧构建的 Cwp 缺省或 Cr 版本）。",
            "reproduction": "python3 scripts/wp5577_review.py（C10: mock_RT_recomputed_from_Cr / deployed_Cr_implied_by_RT）",
            "remediation": "③ 表二第 3 行补旧构建的提交号与所用 Cr 公式版本；否则降级为 WITHHELD（不可复核）。",
        },
        {
            "finding_id": "F4", "severity": "medium", "blocking": False,
            "title": "『见内嵌附图』被字节面探针否证：三个声明图名在该端点 404，而正对照可取回且 sha256 一致",
            "claim_quote": QUOTES["q_figures"],
            "evidence": [QUOTES["q_figures"]],
            "analysis": f"record 里 figures={up['target_figures']} 条、带 png_base64 的 {up['target_figures_with_png']} 条；"
                        "进一步做受控探针（scripts/wp5577_probe_figures.py）：对 `GET /tensor/reports/5577/figures/{name}` 取三个声明图名全部 **404**，"
                        "而对本审核自身投递的报告（同一 POST /tensor/reports 路径写入 figures[].png_base64）取回 70557 字节、"
                        "sha256 与本地 PNG 完全一致。"
                        "结论：平台这条读路径**确实能取回图字节**，所以 5577 的图不是『平台不存』，而是**该报告从未把图字节落库**；"
                        "报告原句『见内嵌附图』因此是不成立的断言（且报告未给出图字节存于何处）。",
            "reproduction": "python3 scripts/wp5577_probe_figures.py --control-report-id 14965（读回 docs/kf/wp-5577-04/source/figure_probe.json；离线审核脚本 C11/C14 消费该结果）",
            "remediation": "把三张图以 figures[].png_base64 随报告投递（平台存字节且可按名取回），或改写为『图 PNG 存于 artifacts/bp_demo/，本记录仅登记 name/caption』并给出可取回的路径。",
        },
        {
            "finding_id": "F5", "severity": "low", "blocking": False,
            "title": "12 kn 行 Cr 与 Rw 在声明精度下不相容（0.00002 vs 反解 0.0000148）",
            "claim_quote": QUOTES["q_row_12kn"],
            "evidence": [QUOTES["q_row_12kn"], QUOTES["q_row_24kn"]],
            "analysis": "12 kn：Cr=0.00002×½ρV²S(=175 262 kN，ρ=1025)=3.5 kN，同表 Rw=2.6 kN；由 Rw 反解 Cr="
                        f"{r12['Cr_recomputed_from_Rw']:.5f}（5 位小数应显示 0.00001，表列 0.00002 偏大 33%）。"
                        f"其余 4 行闭合到舍入级（最大 |Rw_dev| {max(abs(r['Rw_dev_pct']) for r in rows[1:])}%）。"
                        "对 RT 影响 0.3%（0.9 kN / 335 kN），不改结论，但『可逐字定位』的表不应自相矛盾。",
            "reproduction": "python3 scripts/wp5577_review.py（numeric_recomputation.rows[0].Cr_recomputed_from_Rw）",
            "remediation": "Cr 列增至 6 位小数，或注明『Cr 由未舍入 Rw 计算』。",
        },
        {
            "finding_id": "F6", "severity": "low", "blocking": False,
            "title": "过度概括：由单一 mock 实现推出『任何按 Fn 分段的多项式都会成倍偏差』",
            "claim_quote": QUOTES["q_universal_claim"],
            "evidence": [QUOTES["q_universal_claim"], QUOTES["q_universal_claim_2"],
                         QUOTES["q_mock_cr_formula"]],
            "analysis": "被否证的只是 /calculations/resistance 里那一组 C4(Fn) 分段系数（0.008036 vs 0.00109，约 7.4 倍）。"
                        "『任何分段多项式』是全称断言，报告未对该族给出证明，也未对比其它分段实现——结论外推过度，"
                        "按 S 分级不应据此树立方法论结论。",
            "reproduction": "读 ① 第 2 段与 ② 『本轮修复』段即可复现该叙述（无需运行）",
            "remediation": "改为『本实现所用的 C4(Fn) 分段插值在 Fn≈0.26 处把 Cr 抬高约 7.4 倍（0.008036 vs 0.00109）』。",
        },
        {
            "finding_id": "F7", "severity": "low", "blocking": False,
            "title": "V2 的 0.280%<3% 属同级自洽，不是精度验证；⑥ 表『基准』列未标属性",
            "claim_quote": QUOTES["q_v2_row"],
            "evidence": [QUOTES["q_v2_row"], QUOTES["q_no_efd"], QUOTES["q_honest_fail"]],
            "analysis": "基准 2005.99 kN 与被测 2011.61 kN 同出 Holtrop 单一源（⑤ 自述『单一源对标属同级而非实验对标』），"
                        f"复算偏差 {dev['V2_dev_pct_recomputed']}% 与声明一致，但它只证明两条调用路径同源一致，不构成对物理真值的精度证据；"
                        "⑥ 表无『基准类型』列，下游易把 0.280% 误读为实验对标误差。",
            "reproduction": "python3 scripts/wp5577_review.py（C10: V2_dev_pct_recomputed）",
            "remediation": "⑥ 表增『基准类型』列（self-consistency / literature / EFD），V2 标 self-consistency。",
        },
        {
            "finding_id": "F8", "severity": "low", "blocking": False,
            "title": "V4 文献基准 1960.0 kN 无出处、KVLCC2 几何/工况未给 ⇒ -17.26% 不可独立复核",
            "claim_quote": QUOTES["q_v4_row"],
            "evidence": [QUOTES["q_v4_row"], QUOTES["q_no_form_factor"], QUOTES["q_honest_fail"]],
            "analysis": "报告未给 KVLCC2 的 L/B/T/Cb/S/航速，也未给 1960.0 kN 的文献名与表号。"
                        f"本审核只能复核百分比算术（复算 {(KVLCC2_RT-KVLCC2_BASE)/KVLCC2_BASE*100:.3f}% vs 声明 -17.262%，一致），"
                        "不能复核物理量，故该行的『否』无法区分是模型缺陷还是基准不当。",
            "reproduction": "python3 scripts/wp5577_review.py（C10: V4_dev_pct_recomputed）",
            "remediation": "补 KVLCC2 参数表 + 文献引用（作者/年/表号/工况/附体假设），否则该行标 WITHHELD。",
        },
        {
            "finding_id": "F9", "severity": "low", "blocking": False,
            "title": "上游 wp-5577-01 的 summary 计数口径与 manifest 不一致（27 vs 26 locator）",
            "claim_quote": UPSTREAM_SUMMARY_CLAIM,
            "evidence": [UPSTREAM_SUMMARY_CLAIM],
            "analysis": f"manifest 实测 locator {up['locators_total']} 条（markdown {up['locators_markdown']} + record {up['locators_record']}），"
                        "上游 ② 自己也写『17 条 + 9 条』=26、③ 写『26 locator』；summary 的『27 条』疑为把 ast-5577-01 的 "
                        "content_ref 整篇跨度也计作 locator。"
                        "该串取自上游 record.summary 字段（非正文引文），仅计数口径不一致；schema/哈希/locator 回解三项验收结论不受影响。",
            "reproduction": "python3 scripts/wp5577_review.py（C6 明细 locators_total / summary_locator_count_claim）",
            "remediation": "summary 改为『26 条 locator（17 markdown + 9 record）+ 1 条整篇 content_ref』。",
        },
        {
            "finding_id": "F10", "severity": "info", "blocking": False,
            "title": "上游 01 的范围声明准确：19 unresolved = 源记录缺字节副本，非登记遗漏",
            "claim_quote": UPSTREAM_SCOPE_CLAIM,
            "evidence": [UPSTREAM_SCOPE_CLAIM, UPSTREAM_SUMMARY_CLAIM],
            "analysis": "独立复核（均取自上游记录字段，非 report-5577 正文）：21 资产（resolved 2 / unresolved 19）与其 ④ 表 21 行一致；"
                        "17/17 条 markdown locator 在原文对应字符区间逐字命中；claims=[] 与 01 契约（objective=register_assets）一致；"
                        "上游 ⑤.2 明示不对报告数字做正确性背书，本审核确认属实——故其 unresolved/不背书是设计而非缺漏。",
            "reproduction": "python3 scripts/wp5577_review.py（C2–C6）",
            "remediation": "无需修复。",
        },
    ]


def claim_judgements(rows: list[dict], max_dev: dict, dev: dict, geom: dict, up: dict) -> list[dict]:
    r24 = rows[4]
    return [
        {"claim_id": "clm-5577-c1",
         "text": "端点 Cr 已由分段多项式 mock 改为 Cr=R_W(V)/(½ρV²S)，R_W 取 physics.holtrop 单一源",
         "status": "supported",
         "basis": "24 kn 行 Rw=764.8 kN 与 Cr=0.00109 在 Q=½ρV²S(ρ=1025)=701 186 kN 下闭环"
                  f"（Cr 反解 {r24['Cr_recomputed_from_Rw']:.5f}，偏差 {r24['Rw_dev_pct']}%）；"
                  f"5 行 Rw 最大偏差 {max_dev['Rw_dev_pct']}%。",
         "evidence": ["q_fix_formula", "q_row_24kn"]},
        {"claim_id": "clm-5577-c2",
         "text": "KCS 设计点总阻力 Rt 与基准偏差 0.280%<3%",
         "status": "partially-supported",
         "basis": f"百分比算术复核一致（{dev['V2_dev_pct_recomputed']}% vs 0.280%），但基准与被测同源（Holtrop 单一源），"
                  "该偏差是自洽性而非精度证据；见 F7。",
         "evidence": ["q_v2_row", "q_no_efd"]},
        {"claim_id": "clm-5577-c3",
         "text": "修复前 mock 的 KCS Rt=6882.59 kN（偏差 243.10%）",
         "status": "supported",
         "basis": f"用 Cr=0.008036 与同表 Rf=1246.8 kN 复算 RT={dev['mock_RT_recomputed_from_Cr']} kN，"
                  f"与 {MOCK_RT} kN 差 {dev['mock_RT_dev_pct']}%；偏差百分比复算 {dev['V3_dev_pct_recomputed']}%（声明 243.102%）。",
         "evidence": ["q_tbl2_mock", "q_mock_cr_formula"]},
        {"claim_id": "clm-5577-c4",
         "text": "部署实例 8002（旧构建）同点返回 7401.24 kN，偏差 268.96%",
         "status": "unresolved",
         "basis": f"该 RT 反解 Cr≈{dev['deployed_Cr_implied_by_RT']}，与报告 mock Cr=0.008036 不一致，且未给旧构建的公式/构建号；"
                  f"偏差算术本身可复算（{dev['tbl2_row3_dev_vs_base']}%）。见 F3。",
         "evidence": ["q_tbl2_deployed", "q_drift"]},
        {"claim_id": "clm-5577-c5",
         "text": "Cb 反算偏差 0.0617%（<1% 通过）",
         "status": "supported",
         "basis": f"∇/(LBT)=52030/79984.8={geom['Cb_from_nabla']}，与表列 Cb=0.6509 相差 {geom['Cb_dev_pct']}%。",
         "evidence": ["q_geom_row"]},
        {"claim_id": "clm-5577-c6",
         "text": "缺省 Cwp 由 0.75+0.25Cb 改为 Momo/Schneekluth (1+2Cb)/3，KCS 得 0.767、KVLCC2 得 0.873",
         "status": "supported",
         "basis": f"复算：旧式 KCS {geom['Cwp_default_old_KCS']}（报告称 0.913）；新式 KCS {geom['Cwp_default_new_KCS']}（报告 0.767）、"
                  f"KVLCC2(Cb=0.8098) {geom['Cwp_default_new_KVLCC2']}（报告 0.873）。",
         "evidence": ["q_cwp_old", "q_cwp_new", "q_cwp_values"]},
        {"claim_id": "clm-5577-c7",
         "text": "8 次调用 100% 按契约、延迟 p50 0.004 s、41 passed/3 skipped、报告门 8/8、工件索引 20/20",
         "status": "unresolved",
         "basis": "全部为报告自述：运行日志、report_gate 输出、artifacts/bp_demo/sha256_index.json 均未随记录落库，无字节可核（见 checks_not_run）。"
                  "唯一可做的内部一致性检查：5 航速+2 负控+1 复调=8，与『8 次』自洽。",
         "evidence": ["q_calls", "q_latency", "q_pytest", "q_gate"]},
        {"claim_id": "clm-5577-c8",
         "text": "任何按 Fn 分段的多项式近似都会在中等 Fn 段产生成倍偏差",
         "status": "refuted",
         "basis": "证据只覆盖本仓被删的一组 C4(Fn) 系数（0.008036 vs 0.00109，约 7.4 倍），不支持『任何』这一全称量化；属过度外推。见 F6。",
         "evidence": ["q_universal_claim", "q_universal_claim_2"]},
        {"claim_id": "clm-5577-c9",
         "text": "端点无 (1+k)/附体通道，故与含形因子的全尺度数据对标系统性偏低约 17.3%",
         "status": "partially-supported",
         "basis": "C8 证实实算 RT=Rf(含ΔCf)+Rw、无 (1+k)；但 -17.3% 的文献基准 1960.0 kN 无出处，无法判定偏低是否全由缺 (1+k) 造成（见 F8）。",
         "evidence": ["q_no_form_factor", "q_v4_row"]},
        {"claim_id": "clm-5577-c10",
         "text": "三张结果图已随报告内嵌",
         "status": "unresolved",
         "basis": f"record.figures={up['target_figures']} 条仅有 name/caption，带 png_base64 的 "
                  f"{up['target_figures_with_png']} 条；图内容不可审计。见 F4。",
         "evidence": ["q_figures"]},
    ]