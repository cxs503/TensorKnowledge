"""Claim / evidence specifications for the sediment package of mission 7485.

Every number that reaches a claim statement is interpolated from ``N`` (derived
in ``sediment_m7485_extract.py`` out of the committed machine artefacts), and
every quotation is sliced by ``ev`` out of ``git show <sha>:<path>``.  Nothing
is typed in by hand.
"""

from sediment_spec_m7485 import DOC, POINTS, TESTS, VERDICT

NO_SELF_REVIEW_NOTE = (
    "review_status=draft（fold(空 review-event 账本)，见 knowledge/sediment/m7485/"
    "review-status.json）；生产者不自审，独立评审席位另派"
)
SCHEMA_DEVIATION_NOTE = (
    "epistemic_status 取 schema 合法值 provisional：claim-record.schema.json 的 "
    "epistemic_status enum 无 'draft' 值（draft 属 review-event 账本 fold 的结果，见 "
    "docs/ke/mapping-spec.md MUST-4.5 / D-09）；偏差已在 INDEX.md §偏差 记录"
)
REPRO_PYTEST = (
    "复现（自证）：cd <TensorBEM>@80ad52a && PYTHONPATH=src python -m pytest "
    "tests/test_propeller_open_water.py -q  → 15 passed（本单 m8823 已重跑确认）"
)
REPRO_SWEEP = (
    "复现（扫掠）：cd <TensorBEM>@80ad52a && PYTHONPATH=src python -m "
    "tensorbem.benchmarks.kp505_openwater_bem  → 重生成 "
    "benchmarks/kp505_openwater_bem/{verdict.json,points.csv}"
)
NOT_RERUN = (
    "本单未重跑 KP505 扫掠（成本高）：数值取自该 sha 已提交的 points.csv / verdict.json，"
    "并逐项用 points.csv 复算校验，非手抄"
)


def specs(N, ev):
    """Return the list of claim specs."""

    return [
        {
            "slug": "kp505-kt-design-j-falsified",
            "claim_type": "hypothesis",
            "domain": "ship-propulsion / open-water propeller hydrodynamics",
            "statement": (
                "假设 H1（被否证）：涡格升力面敞水内核（n_radial=16, n_chord=2，几何螺距尾涡，"
                "ITTC-1978 剖面粘性阻力，由公开 6 个主尺度标量重建的 KP505 几何）在锚定设计进速比 "
                "J=0.8 处可达到 |ΔK_T| ≤ 3%。实测 K_T=" + N["kt_bem_08"] + " vs 锚（Iftikhar & Takinaci 2023 "
                "MARINE 2023 Table 2 实验列）" + N["kt_anchor_08"] + "，ΔK_T=" + N["dkt_08"] + "% → 是否 <3%：否"
                "（超标约 10 倍）；配套判据 C2（全 J 域 |Δη_0| ≤ 5%）同样是否：" + N["points_total"]
                + " 个锚点中仅 " + N["points_inside_band"] + " 点落在 5% 带内。故 H1 与 C1/C2 一并被否证，"
                "verdict = FAIL（honest FAIL，未做阈值事后调整）。"
            ),
            "system": (
                "lifting-surface vortex lattice (horseshoe segments, Z-fold rotational symmetry, "
                "geometric-pitch wake, strip-width core regularisation) on reconstructed KP505 "
                "geometry; D=0.25 m, n=10 rev/s, Re_c≈2–4e5"
            ),
            "conditions": [
                "J = 0.1 … 1.0 共 10 个锚点全报（判据③：禁只报达标点）",
                "判据动手前固定：C1 设计 J 处 |ΔK_T| ≤ 3%，C2 全 J 域 |Δη_0| ≤ 5%",
                "设计 J=0.8 由锚表 η_0 = J K_T/(2π K_Q) 程序化取峰值得到，非人为挑选",
            ],
            "exclusions": [
                "不得外推为『面元法精度』的通用结论：几何为重建（弦长/径向螺距分布/NACA66 a=0.8 拱度均缺）",
                "不含桨毂、叶片厚度排挤、空泡、自由面、非定常",
            ],
            "notes": [
                "反证工件：benchmarks/kp505_openwater_bem/verdict.json（criteria C1/C2, passed=false）"
                "与 benchmarks/kp505_openwater_bem/points.csv 第 9 行（J=0.8）",
                "本条数字由本单从 points.csv 复算 100*(K_T,bem-K_T,anchor)/K_T,anchor，未手抄",
                REPRO_PYTEST,
                REPRO_SWEEP,
                NOT_RERUN,
                NO_SELF_REVIEW_NOTE,
                SCHEMA_DEVIATION_NOTE,
            ],
            "evidence": [
                ev("kp505-kt-fail-report", DOC, [8], "refutes",
                   "报告结论先行段：verdict=FAIL、ΔK_T=-29.13%、η_0 最差 786.67%、5% 带内仅 1/10 点"),
                ev("kp505-kt-fail-verdict", VERDICT, [33], "supports",
                   "机器工件侧 C1 的 measured_pct，与报告同值，可 grep 溯源"),
                ev("kp505-kt-fail-points", POINTS, [9], "supports",
                   "原始点位数据 J=0.8 行；Δ 可由该行 K_T 两列复算"),
            ],
        },
        {
            "slug": "kp505-mesh-refinement-not-the-cause",
            "claim_type": "hypothesis",
            "domain": "numerical verification / discretisation-error estimation",
            "statement": (
                "假设 H2（被否证）：H1 失败主因是面元密度不足，继续加密即可进 3% 带。实测（三网格 "
                "n_r=8/16/32，r=2，J=0.4/0.7/0.9）K_T 观测阶 p≈0.96–1.05（径向一阶），"
                "GCI_fine(K_T)=7.14–8.08%，本身已宽于 3% 判据；且取 Richardson 外推到最细网格之外"
                "（J=0.7：K_T=" + N["richardson_kt_07"] + "，锚 " + N["kt_anchor_07"] + "）偏差 "
                + N["dkt_richardson_07"] + "%，比细网格本身的 " + N["dkt_bem_07"] + "% 更大 → 是否 <3%：否。"
                "H2 被否证：失败不能归咎于『网格还不够细』，须先把径向格式从一阶提到二阶。"
            ),
            "system": "same lattice as H1; three-level radial and chordwise ladder, GCI(r=2) + Richardson extrapolation",
            "conditions": ["J = 0.4 / 0.7 / 0.9 三点做 GCI", "径向 n_r = 8/16/32；弦向 n_c = 1/2/4"],
            "exclusions": [
                "GCI 只覆盖离散误差，不含几何缺口与尾涡模型误差（后者无法用网格加密发现）",
            ],
            "notes": [
                "反证工件：docs/m7485_kp505_openwater_bem.md §3.2 表（GCI）与 verdict.json 的 convergence 段",
                "GCI 数值取自报告 §3.2 逐字引句；Richardson 外推点的偏差由本单用 points.csv 锚值复算",
                "3% 判据若要可达，路径是径向格式二阶化（报告 §7 第 3 项），不是无界加密",
                NO_SELF_REVIEW_NOTE,
                SCHEMA_DEVIATION_NOTE,
            ],
            "evidence": [
                ev("kp505-mesh-readout", DOC, [125], "supports",
                   "§3.2 读法：径向一阶、GCI 7.1–8.1% 宽于 3% 判据、Richardson 外推偏差更大"),
                ev("kp505-mesh-gci-kt-j07", DOC, [116], "supports",
                   "K_T @ J=0.7 行：观测阶 1.02、GCI_fine 7.14%、Richardson 0.14927"),
            ],
        },
        {
            "slug": "elliptic-wing-lift-vs-lifting-line",
            "claim_type": "mathematical",
            "domain": "lifting-surface method verification (analytic pinning)",
            "statement": (
                "涡格 + Kutta-Joukowski 升力链在椭圆翼解析判例上的定量精度（先于任何桨数的求解器自证）："
                "AR=8、α=5°、20 径向站 → C_L=0.4392 vs 经典升力线 2πAR/(AR+2)α=0.4386，相对偏差 +0.13%"
                "（是否 <3%：是）；AR=4、α=5°、16 站 → C_L=0.3334 vs 0.3655，相对偏差 −8.8%"
                "（是否 <3%：否，归因该经典公式自身在低 AR 的近似误差；测试容差 0.10 内显式写明，"
                "不计为求解器误差）。可复用结论：自证只钉死核函数与力的符号/量级（+0.13% 级），"
                "不能外推为真实桨几何下的精度。"
            ),
            "system": "vortex lattice with one chordwise panel, Kutta condition + Kutta-Joukowski force, flat elliptic wing",
            "conditions": ["α=5°；AR=8（20 站，容差 6%）与 AR=4（16 站，容差 10%）", "core_ratio=0.02"],
            "exclusions": ["薄翼、无厚度、无粘；不可外推到有厚度/大拱度/失速工况"],
            "notes": [
                "反例价值：AR=4 时与经典公式差 −8.8%，说明『与解析解差 <3%』不是普适判据——"
                "低于经典公式自身精度时应归因基准而非求解器",
                REPRO_PYTEST,
                NO_SELF_REVIEW_NOTE,
                SCHEMA_DEVIATION_NOTE,
            ],
            "evidence": [
                ev("elliptic-wing-report-rows", DOC, [78, 79], "supports",
                   "报告 §2.2 自证表两行：AR=8 +0.13%（<3% 是）、AR=4 −8.8%（<3% 否，归因经典公式）"),
                ev("elliptic-wing-test-tolerance", TESTS, [114], "supports",
                   "测试 docstring 显式声明 AR=4 的 ~9% 属经典公式自身精度、AR=8 闭合到 0.1%"),
            ],
        },
        {
            "slug": "line-vortex-kernel-vs-closed-form",
            "claim_type": "mathematical",
            "domain": "Biot-Savart segment kernel verification",
            "statement": (
                "直线涡段诱导核在长段极限下等于闭式 Γ/(2πh)：段 z=±500、测点 h=0.1、单位环量时横向分量 "
                "v=1/(2π·0.1)=1.5915，测试断言 rel=1e-6，且另两分量为零（|v|<1e-9），环量反号则诱导反号。"
                "→ 相对误差 <1e-6（是否 <3%：是）。可复用结论：段式 Biot-Savart 的符号约定与幅度在极限"
                "情形被钉到 1e-6，是马蹄涡/尾涡模型正确性的下限保障。"
            ),
            "system": "segment_induced_velocity(points, start, end, core_ratio=0.0) — unit circulation, no core regularisation",
            "conditions": ["段长 1000·h（远大于测点距离）", "core_ratio=0.0"],
            "exclusions": ["不覆盖近场（测点距段 < 核半径）行为；近场由 strip-width 核正则化处理，不在本判例内"],
            "notes": [
                "该判例是 H1 失败的排除项：核函数错会给出全局符号/量级错，而实测失败表现为随 J 换号，"
                "与核错误不相容",
                REPRO_PYTEST,
                NO_SELF_REVIEW_NOTE,
                SCHEMA_DEVIATION_NOTE,
            ],
            "evidence": [
                ev("line-vortex-test-assert", TESTS, [54], "supports",
                   "测试断言：速度等于 1/(2π·0.1)，rel=1e-6"),
                ev("line-vortex-report-row", DOC, [77], "supports",
                   "报告自证表行：直线涡诱导幅度与方向，相对误差 <1e-6，反号对消"),
            ],
        },
        {
            "slug": "viscous-section-drag-required-in-kq",
            "claim_type": "causal",
            "domain": "propeller open-water modelling (viscous coupling)",
            "statement": (
                "粘性剖面阻力必须计入 K_Q，否则 η_0 恒高估：J=0.7 去掉粘性后 K_T 略升而 10K_Q 明显下降，"
                "η_0 由 0.670 抬到 0.784（+0.114，相对 +17.0%）。该效应量级（~17%）远大于 3% 判据带宽，"
                "属 3% 级对标的前置建模项而非可忽略修正——本内核据此把 ITTC-1978 剖面阻力耦合进涡格。"
            ),
            "system": "same lattice; viscous vs inviscid section-drag switch (sensitivity study)",
            "conditions": ["J=0.7（其余 J 点同向，见 sensitivity.csv）"],
            "exclusions": [
                "ITTC-1978 剖面阻力律按文献转写、标准原文离线不可得（报告 §5 第 5 条）；其份额约占 K_Q 的 10–25%",
            ],
            "notes": [
                "数值逐字引自报告 §3.4 读法段；本单未重跑 sensitivity 扫掠，该文段与 "
                "benchmarks/kp505_openwater_bem/sensitivity.csv 的 inviscid 行同源",
                "量级判定由本单完成：|Δη_0| ≈ 17% > 3% ⇒ 粘性项不可省",
                NO_SELF_REVIEW_NOTE,
                SCHEMA_DEVIATION_NOTE,
            ],
            "evidence": [
                ev("viscous-readout", DOC, [211], "supports",
                   "§3.4 读法：去粘性后 η_0 0.670→0.784，粘性阻力必须进 K_Q"),
            ],
        },
        {
            "slug": "deviation-sign-change-root-cause",
            "claim_type": "causal",
            "domain": "error attribution / root-cause judgement",
            "statement": (
                "根因判例：ΔK_T、Δ10K_Q 随 J 单调换号。按 points.csv 数据，ΔK_T 在 J=0.5 为 "
                + N["dkt_05"] + "%、J=0.6 已转 " + N["dkt_06"] + "%，故换号区间实为 J∈(" + N["cross_lo"]
                + ", " + N["cross_hi"] + ")；零推力进速比 BEM≈0.95 vs 锚≈1.03。单一物理解释：重建几何"
                "（等平均螺距、平板无拱度、按 Ae/Ao 反推弦长）低 J 给偏大载荷、高 J 零推力 J 偏低，"
                "偏差因此随 J 系统性换号——不是随机噪声，也不是核函数符号错（后者会全局反号）。"
                "该换号模式即后续修法的判据（补 NACA66 a=0.8 拱度 + 真实径向螺距分布）。"
            ),
            "system": "KP505 reconstructed geometry, geometric wake, viscous section drag",
            "conditions": ["10 个锚点全报（J=0.1…1.0）"],
            "exclusions": ["『几何缺口主导』属因果推断：拱度与径向螺距同时缺失，单因素不可分离"],
            "notes": [
                "与源报告的一处出入（本单订正）：报告 §3.1 文字称『ΔK_T、Δ10K_Q 在 J ≤ 0.6 为正、J ≥ 0.7 为负』，"
                "但其表 3.1 与 points.csv 自身给出 ΔK_T(J=0.6)=" + N["dkt_06"] + "%（已为负）→ 换号区间应为 ("
                + N["cross_lo"] + ", " + N["cross_hi"] + ")。本单按机器数据订正，并把该引句 relation 记为 qualifies",
                "订正依据可复算：points.csv 的 dKT_pct 列逐行符号",
                NO_SELF_REVIEW_NOTE,
                SCHEMA_DEVIATION_NOTE,
            ],
            "evidence": [
                ev("sign-change-readout", DOC, [109], "qualifies",
                   "§3.1 根因段（换号→单一物理解释）；其中『J ≤ 0.6 为正』与表内 J=0.6 的 −3.51% 冲突，本单订正"),
                ev("sign-change-points-rows", POINTS, [6, 7], "supports",
                   "points.csv J=0.5（dKT +2.01%）与 J=0.6（dKT −3.51%）两行，给出换号真实区间"),
            ],
        },
        {
            "slug": "unphysical-near-zero-load-gate",
            "claim_type": "normative",
            "domain": "evidence discipline / physical-admissibility gates",
            "statement": (
                "准入闸（规范）：近零载荷段数值必须『按原值报出并标记不可信』，不得剔除。实例：J=1.0 处 "
                "K_T=" + N["kt_bem_10"] + "（<0，负推力）且动量上界被违反（η_0=" + N["eta_bem_10"]
                + " > 动量上界 " + N["eta_bound_10"] + "，points.csv 列 momentum_gate_ok=False），属该涡格在零"
                "升力附近的模型失效；该点 Δη_0=+" + N["deta_10"] + "% 按原值计入 C2 的『全 J 域最差』，"
                "物理域（J≤0.9）最差 " + N["abs_deta_09"] + "%。若剔除该点，C2 失败幅度会被粉饰约 32 倍"
                "（786.67% → 24.38%），故『报出 + 标记』是可复用的证据纪律。"
            ),
            "system": "verdict criteria C2 reporting rule + momentum-bound plausibility gate",
            "conditions": ["J=1.0（K_T<0 的近零载荷段）", "物理域界定为 J ≤ 0.9"],
            "exclusions": ["不主张该点数值有物理意义——恰相反，标 unphysical 后只用于如实计分"],
            "notes": [
                "可机检：points.csv 的 momentum_gate_ok 列在 J=1.0 为 False，其余 9 点为 True",
                "可复用性：任何『全域最差』判据都应禁止对失败点做域外剔除，除非同时报告剔除前后两值",
                NO_SELF_REVIEW_NOTE,
                SCHEMA_DEVIATION_NOTE,
            ],
            "evidence": [
                ev("unphysical-readout", DOC, [226], "supports",
                   "§5 第 4 条：K_T<0 且动量上界被违反，已按原值报出并标 unphysical，未剔除"),
                ev("unphysical-points-row", POINTS, [11], "supports",
                   "points.csv J=1.0 行：K_T 负、η_0 3.7893 > 动量上界 1.0274、momentum_gate_ok=False"),
            ],
        },
        {
            "slug": "modelling-parameters-do-not-explain-gap",
            "claim_type": "hypothesis",
            "domain": "sensitivity analysis / error attribution",
            "statement": (
                "假设 H3（被否证）：15–30% 的对标缺口由可调建模参数造成，调参即可消除。实测敏感度："
                "t/c 0.04↔0.08 与 8↔12 rev/s 影响在 1% 量级，根部弦长形态 0.06↔0.20 影响 2–3%，"
                "径向间距余弦/均匀 <1%，全部叠加仍解释不了 15–30% 缺口 → 是否 <3%：否（缺口比最大单参数"
                "敏感度高一个量级）。H3 被否证：缺口主因须落在几何缺口（真实弦长/径向螺距/拱度）与径向"
                "一阶格式，二者都不是『调参』能解决的。"
            ),
            "system": "sensitivity study over t/c, rev/s, root-chord shape, radial spacing, viscosity switch (J=0.4/0.7/0.9)",
            "conditions": ["baseline: n_r=16, n_c=2, geometric wake, wake_length/D=1.0, n=10 rev/s, t/c=0.06"],
            "exclusions": ["未扫掠的参数（侧斜/纵倾/厚度律）无法评估，故对 H3 的否定限于已扫掠参数集"],
            "notes": [
                "数值逐字引自报告 §3.4 读法段（与 sensitivity.csv 同源）",
                "负知识价值：固化『可调参数不足以解释缺口』，避免后续重复调参",
                NOT_RERUN,
                NO_SELF_REVIEW_NOTE,
                SCHEMA_DEVIATION_NOTE,
            ],
            "evidence": [
                ev("sensitivity-readout", DOC, [211], "supports",
                   "§3.4 读法：各参数敏感度 ≤2–3%，合计仍解释不了 15–30% 缺口"),
            ],
        },
    ]