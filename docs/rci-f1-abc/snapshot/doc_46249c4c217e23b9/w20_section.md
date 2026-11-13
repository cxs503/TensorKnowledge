## W20 挖矿更新（2026-11-09；窗口 id>7571 ∧ id≤10436，2236 篇；EVO-1 盲评期剔除 0 篇）

> 本波定位（owner 2026-11-08 顶刊重组令）：从「挖课题」转为「按顶刊证据要求组织科研任务」。窗口自 W16 冻结上界起算（W17 为验证欠账审计波、W18/W19 为执行波，未追加 registry 段）。

### ① 窗口盘点（脚本直读，零手抄）

| 指标 | 值 | 冻结件 |
|---|---|---|
| 窗口报告数 | 2236 | `inventory.json` |
| 窗口内图件数 | 6161 | `digest.json` |
| 窗口内判据行 | 16871 | `digest.json` |
| 含 `<3%` 达标行报告 | 1197 | `digest.json` |
| 判 PASS 报告 | 951 | `digest.json` |
| 判 FAIL 报告 | 550 | `digest.json` |
| 出现 WITHHELD 报告 | 444 | `digest.json` |
| 每报告平均图件 | 2.76 | `digest.json` |
| 平台报告总数 | 6787 | `inventory.json` |

归簇覆盖：`candidates.json` 的 17 个领域簇中 17 个够格（≥3 报告 ∧ 判据行>0 ∧ 有图）；未归簇 1045 篇（绝大多数为平台自治/战役治理类，非船舶域，按纪律不入候选）。

### ② 双轨重标（append-only 增补；既有课题逐条判 external / internal）

判据：**external** ⇔ 存在 ≥1 个外部定量锚（已发表 benchmark 值/模型试验/规范条款值）作对比核心；**internal** ⇔ 平台方法学自审计（ledger/gate/canon/台账/性能基准类），目标产物是 tech report，永不以顶刊框架成稿。既有 9 篇在库稿默认 internal 轨；本波对既有 31 个 registry 课题 + 14 个窗口新候选逐一裁决。

| 课题 | 轨道 | 学科域 | registry | 外部锚（级/可达） | 锚门 | 窗口证据（报告/图/判据行） | 计划 | 下一步 |
|---|---|---|---|---|---|---|---|---|
| `composite-laminate-verification` | external | 结构 | 新候选 | AN-ANALYTIC-NAVIER[A/✓] | closed | 3/12/30 | — | exp-new-plan |
| `damaged-stability-flooding-td` | external | 稳性 | 是 | AN-ISCODE2008[A/✓] | closed | 9/32/82 | 0/1 销项，open=1 | exp-close-gap |
| `formation-ice-channel` | external | 冰区 | 是 | AN-ISO19906[A/✓], AN-LINDQVIST[A/✓] | closed | 4/17/29 | 1/1 销项 | exp-extend |
| `grain-stability-igc` | external | 稳性 | 新候选 | AN-IGC[A/✓] | closed | 11/31/118 | — | exp-new-plan |
| `green-eedi-cii` | external | 绿色航行 | 是 | AN-MEPC353[A/✓] | closed | 92/186/548 | — | exp-new-plan |
| `green-shipping-iso19030` | external | 绿色航行 | 新候选 | AN-ISO19030[A/✓], AN-MEPC353[A/✓] | closed | 16/71/192 | — | exp-new-plan |
| `holtrop-citation-grade-de-mock` | external | 阻力 | 是 | AN-HOLTROP[A/✓], AN-ITTC57[A/✓] | closed | 8/28/49 | — | exp-new-plan |
| `hull-vibration-analytic-kernel` | external | 振动噪声 | 是 | AN-ISO6954[A/✓] | closed | 95/341/880 | 1/1 销项 | exp-extend |
| `ice-coupled-6dof` | external | 冰区 | 是 | AN-ISO19906[A/✓] | closed | 10/40/89 | 1/1 销项 | exp-extend |
| `ice-hull-propeller-threefield` | external | 冰区 | 是 | AN-ISO19906[A/✓], AN-LINDQVIST[A/✓] | closed | 8/19/79 | 1/1 销项 | exp-extend |
| `ice-load-digital-twin` | external | 冰区 | 是 | AN-ISO19906[A/✓] | closed | 4/3/26 | 1/1 销项 | exp-extend |
| `ice-load-statistics` | external | 冰区 | 是 | AN-ISO19906[A/✓] | closed | 0/0/0 | — | exp-new-plan |
| `ice-mechanics-rudder` | external | 冰区 | 是 | AN-ISO19906[A/✓] | closed | 37/162/381 | — | exp-new-plan |
| `ice-nav-operational-chain` | external | 冰区 | 是 | AN-ISO19906[A/✓] | closed | 44/85/232 | 0/1 销项，open=1 | exp-close-gap |
| `ice-resistance-crossimpl` | external | 冰区 | 是 | AN-LINDQVIST[A/✓] | closed | 29/130/244 | 1/1 销项 | exp-extend |
| `ice-ridge-keel-grounding` | external | 冰区 | 是 | AN-ISO19906[A/✓] | closed | 27/115/219 | — | exp-new-plan |
| `ice-wave-mechanics` | external | 冰区 | 是 | AN-ISO19906[A/✓] | closed | 50/96/288 | — | exp-new-plan |
| `lbm-suboff-tau` | external | 阻力 | 是 | AN-SUBOFF[B/✓], AN-ITTC57[A/✓] | closed | 4/7/30 | 3/5 销项，open=2 | exp-close-gap |
| `maneuvering-podded-ice` | external | 操纵 | 是 | AN-MSC137[A/✓], AN-ISO19906[A/✓] | closed | 10/27/56 | 0/1 销项，open=1 | exp-close-gap |
| `mmg-imo-msc137-compliance` | external | 操纵 | 是 | AN-MSC137[A/✓], AN-SIMMAN2008[B/✓] | closed | 56/232/631 | 4/4 销项 | draft-exists |
| `propeller-openwater-bem` | external | 推进 | 是 | AN-KP505[B/✓], AN-ITTC57[A/✓] | closed | 75/235/599 | 3/4 销项，open=1 | exp-close-gap |
| `resistance-efd-applicability` | external | 阻力 | 是 | AN-HOLTROP[A/✓], AN-ITTC78[A/✓] | closed | 12/37/98 | — | exp-new-plan |
| `resistance-ittc-traceable-chain` | external | 阻力 | 新候选 | AN-ITTC57[A/✓], AN-ITTC78[A/✓] | closed | 12/38/221 | — | exp-new-plan |
| `seakeeping-truncation` | external | 耐波 | 是 | AN-ITTC-SEAKEEP[A/✓], AN-WIGLEY[B/✓] | closed | 10/16/71 | 3/3 销项 | draft-ready |
| `ship-hull-girder-structure` | external | 结构 | 新候选 | AN-IACS-CSR[A/✓] | closed | 36/140/487 | — | exp-new-plan |
| `ship-vibration-noise-real-chain` | external | 振动噪声 | 新候选 | AN-ISO6954[A/✓] | closed | 14/62/215 | — | exp-new-plan |
| `stability-is-code-2008` | external | 稳性 | 是 | AN-ISCODE2008[A/✓] | closed | 9/26/145 | 3/3 销项 | draft-exists |
| `stability-large-angle-gz` | external | 稳性 | 是 | AN-ISCODE2008[A/✓] | closed | 2/6/13 | 0/1 销项，open=1 | exp-close-gap |
| `underice-acoustics` | external | 振动噪声 | 是 | AN-PEKERIS[A/✓] | closed | 43/106/224 | — | exp-new-plan |
| `undex-shock-chain` | external | 结构 | 新候选 | AN-COLE[A/✓] | closed | 2/12/46 | — | exp-new-plan |
| `wetted-surface-geometry` | external | 阻力 | 是 | AN-ITTC57[A/✓], AN-SIMMAN2008[B/✓] | closed | 45/126/341 | 3/3 销项 | draft-exists |
| `wind-load-blendermann-weather-criterion` | external | 稳性 | 是 | AN-BLEND[B/✓] | closed | 2/5/7 | 1/2 销项，open=1 | exp-close-gap |
| `wind-load-six-component` | external | 稳性 | 新候选 | AN-OCIMF[B/✓], AN-BLEND[B/✓] | closed | 8/27/99 | — | exp-new-plan |
| `agent-orchestration` | internal | 平台方法学 | 是 | — | no_anchor | 5/7/10 | — | techreport |
| `digital-twin-ekf-consistency` | internal | 平台方法学 | 是 | — | no_anchor | 0/0/0 | — | hold |
| `mock-fingerprint-verdicts` | internal | 平台方法学 | 是 | — | no_anchor | 15/22/121 | — | techreport |
| `multikernel-code-verification` | internal | 平台方法学 | 是 | — | no_anchor | 5/22/68 | — | techreport |
| `numerical-uncertainty-gci` | internal | 平台方法学 | 是 | — | no_anchor | 32/105/334 | — | techreport |
| `optimizer-analytic-benchmarks` | internal | 平台方法学 | 是 | — | no_anchor | 0/0/0 | — | hold |
| `paper-line-machine-gates` | internal | 平台方法学 | 新候选 | — | no_anchor | 28/55/283 | — | techreport |
| `paper-trace-mutation-gate` | internal | 平台方法学 | 是 | — | no_anchor | 15/31/91 | — | techreport |
| `physics-contract-verification` | internal | 平台方法学 | 是 | — | no_anchor | 47/151/657 | — | techreport |
| `platform-evidence-audit` | internal | 平台方法学 | 是 | — | no_anchor | 62/116/635 | — | techreport |
| `resistance-benchmark-canon` | internal | 平台方法学 | 是 | AN-ITTC57[A/✓], AN-HOLTROP[A/✓] | closed | 25/52/273 | — | techreport |
| `tensorlbm-gpu-bench` | internal | 平台方法学 | 是 | — | no_anchor | 9/17/41 | — | techreport |

小计：external 33 / internal 12。internal 轨下一步一律 `techreport` 或 `hold`，不得进顶刊成稿线（本波机检项 G5_track_discipline）。

### ③ 外部锚目录与可达性分级（顶刊门槛①的可执行化）

锚目录 24 条：A 级（闭式规范/解析，离线可逐字实现并数值求值）17、B 级（仓内已转录基准数据/系数表，路径可查）6、C 级（付费墙一手文献，离线不可核销）1；机器可达 23/24。

| 锚 | 级别 | 出处 | 定量陈述 | 机检方式 | 可达 |
|---|---|---|---|---|---|
| ITTC-1957 摩擦线 | A | ITTC Recommended Procedure 7.5-02-03-01.4 (1957 friction line) | C_F = 0.075/(log10 Re - 2)^2 | numeric_eval | ✓ |
| ITTC-78 形因子法阻力外推 | A | ITTC 1978 Performance Prediction Method | C_T = (1+k) C_F + C_A + C_W（模型→实船换算链） | numeric_eval | ✓ |
| Holtrop-Mennen 阻力分解 | A | Holtrop & Mennen, ISP 29(335), 1982; Holtrop, ISP 31(363), 1984 | R_T = R_F(1+k1) + R_APP + R_W + R_B + R_TR + R_A（结构式；各分项多项式系数待锁） | numeric_eval | ✓ |
| IMO IS Code 2008 完整稳性判据 | A | IMO Resolution MSC.267(85), IS Code 2008 Part A §2.2 | A30≥0.055 m·rad, A40≥0.09 m·rad, A(30-40)≥0.03 m·rad, GZmax≥0.20 m@≥25°, ΔGZmax≥0.20 m | numeric_eval | ✓ |
| IMO MSC.137(76) 操纵性判据 | A | IMO Resolution MSC.137(76) (2002) Standards for Ship Manoeuvrability | 进距 ≤ 4.5L；战术直径 ≤ 5L（Z 形首向超调判据按 L/V 条件另列） | numeric_eval | ✓ |
| International Grain Code 谷物稳性 | A | IMO International Grain Code (1991), Part A §3 | 横倾角 ≤ 12°；剩余面积 ≥ 0.075 m·rad | numeric_eval | ✓ |
| IMO CII 计算与评级 | A | IMO Resolution MEPC.353(78) (2022) 2022 Guidelines on CII | attained CII = FC·C_F/(Capacity·distance)；required CII = a·Capacity^(-c)（a,c,dd 表值待锁） | numeric_eval | ✓ |
| ISO 19030 在役航速-功率性能 | A | ISO 19030-2/-3:2016 | ΔV = V_ref - V_meas（风浪流修正后）；功率-航速退化量以参考工况归一 | numeric_eval | ✓ |
| ISO 19906 极区冰载荷面积律 | A | ISO 19906:2010 Petroleum and natural gas industries — Arctic offshore structures | p_G = C_R (A/A_0)^ex（C_R、ex 取规范表；全局压力 ex<0，局部压力口径不同） | numeric_eval | ✓ |
| Lindqvist (1989) 冰阻力闭式 | A | Lindqvist G., J. Ship Research 33(1), 1989 | R_ice = R_c + R_b + R_s（三分量结构式；量纲齐次与线性缩放可机检，C/μ/穿透量为实现级参数） | numeric_eval | ✓ |
| IACS CSR / UR S 船体梁强度衡准 | A | IACS Common Structural Rules for Bulk Carriers and Oil Tankers (2019) Pt.1 Ch.5; IACS UR S7 (2010) Minimum longitudinal strength standard | ULS：γ_s·M_sw + γ_w·M_wv ≤ M_u（利用率 ≤1.0）；屈服：σ = M/Z ≤ σ_y/γ_R （分项安全因子取规范表值，待锁） | numeric_eval | ✓ |
| Cole (1948) 水下爆炸冲击波 | A | Cole R.H., Underwater Explosions, Princeton Univ. Press, 1948 | p_m = K (W^(1/3)/R)^A（K、A 为装药相关实现参数） | numeric_eval | ✓ |
| ISO 6954:2000 船体振动衡准 | A | ISO 6954:2000 Mechanical vibration — Guidelines for the measurement, reporting and evaluation of vibration with regard to habitability | 振动速度 RMS 按舱室类别限值（A/B/C 类频率加权） | numeric_eval | ✓ |
| 层合板 Navier/Levy 解析解 | A | Reddy, Mechanics of Laminated Composite Plates and Shells, 2nd ed. (2004) | 简支层合板 Navier 双三角级数挠度/频率解析值（CLT/FSDT 级数收敛） | numeric_eval | ✓ |
| DTRC SUBOFF AFF-8 阻力基准 | B | Stern et al. (1980) DTRC report; Groves, Huang & Chang (1987); ITTC 7.5-03-02-03 | AFF-8 几何 L=4.356 m, D=0.508 m；Re=1.2e7 下的 C_T 由领域仓转录件承载 | repo_artifact_glob | ✓ |
| KP505 螺旋桨敞水曲线 | B | KRISO KP505 (KCS propeller) open-water test data; SIMMAN 2008 workshop | J=0.1~0.9 的 K_T(J)、K_Q(J)、η0(J) 表；设计点 J=0.70 | repo_artifact_glob | ✓ |
| SIMMAN 2008 KCS/KVLCC2 操纵与阻力基准 | B | SIMMAN 2008 Workshop on Verification and Validation of Ship Manoeuvring Simulation Methods | KCS(Fr=0.26)/KVLCC2(Fr=0.142) 阻力与 PMM/操纵试验基准值（由仓内转录件承载） | repo_artifact_glob | ✓ |
| OCIMF 风载荷系数 | B | OCIMF Prediction of Wind and Current Loads on VLCCs, 2nd ed. (1994) | C_X/C_Y/C_N 随风舷角与吃水的无量纲系数表（VLCC 系列） | repo_artifact_glob | ✓ |
| Wigley 抛物型船模试验阻力/RAO | B | Wigley (1942) 系列模型试验；ITTC 耐波性基准算例 | Wigley 船型（L/B=10, B/T=1.6）阻力与 RAO 试验值 | repo_artifact_glob | ✓ |
| ISO 15016:2015 航速/功率试航修正 | A | ISO 15016:2015 Ships and marine technology — Guidelines for the assessment of speed and power performance by analysis of speed trial data | 风、浪、流、水深、水温修正量的分项计算链（修正后 V_ref/P_ref） | numeric_eval | ✓ |
| Journée (1992) 浅水死水试验 | C | Journée J.M.J., Ships and Maritime Research 36(3), 1992 | 死水（dead water）双峰阻力曲线与内部波速试验值 | documented_blocker | ✗ |
| Blendermann (1994) 风倾侧衡准 | B | Blendermann W., Ship Technology Research 41, 1994 | 风倾侧力矩与横风稳定衡准曲线（含阵风因子） | repo_artifact_glob | ✓ |
| Pekeris 浅海声传播解析解 | A | Pekeris C.L., Geol. Soc. Am. Mem. 27, 1948 | 两层流体浅海简正波（模态）色散关系与传播损失解析解 | numeric_eval | ✓ |
| ITTC 耐波性数值计算推荐规程 | A | ITTC Recommended Procedure 7.5-02-07-02.1 | 耐波性数值计算域截断与消波区设置要求（域长度/波长比、辐射边界条件） | numeric_eval | ✓ |

**A 级锚真数值求值（不是字符串断言）**：

| 锚 | 求值结果（节选） |
|---|---|
| AN-ITTC57 | `{"Cf_Re1e9": 0.001530612244897959, "Cf_Re1e7": 0.003, "monotone_decreasing": true}` |
| AN-ITTC78 | `{"CT_example_k0.15_Ca0": 0.002160204081632653}` |
| AN-ISCODE2008 | `{"A30_mrad": 0.08813912722571365, "A40_mrad": 0.1413716694115407, "A3040_mrad": 0.05323254218582704, "GZmax_m": 0.31, "GZmax_angle_deg": 35.0, "Delta_GZ_max_m": 0.010000000000000009, "pass": false}` |
| AN-MSC137 | `{"advance_over_L": 3.9130434782608696, "DT_over_L": 4.782608695652174, "advance_crit_over_L": 4.5, "DT_crit_over_L": 5.0, "pass": true}` |
| AN-IGC | `{"heel_deg": 12.0, "residual_area_mrad": 0.12629202467430967, "crit_mrad": 0.075, "heel_crit_deg": 12.0, "pass": true}` |
| AN-MEPC353 | `{"attained_CII_gCO2_per_t_nm": 6.228}` |
| AN-ISO19906 | `{"p_G_A1m2_CR0.9": 0.9, "p_G_A10m2_CR0.9": 0.28460498941515416}` |
| AN-COLE | `{"scaled_distance": 0.23207944168063893, "p_m_MPa": 43.18689256989767}` |
| AN-LINDQVIST | `{"components_N": {"R_c_N": 24000000.0, "R_b_N": 2256000.0, "R_s_N": 466171.20000000007, "R_total_N": 26722171.2}, "scaling_check": {"exp_B": 2.0, "exp_h": 2.0, "exp_sigma": 2.0, "homogeneous_linear": true}}` |

> 口径声明：A 级锚中「规范表值」（ISO 19906 的 C_R/指数、MEPC.353 的 a/c/dd 表、MSC.137 的 Z 形条件判据、Cole 的 K/A）在本波只做**结构可求值**证明；具体表值须由对应 exp 单逐字抄录并登记来源，未抄录前不得在正文以锚值自居。这是本波对 W19 技报（#9852：40 单中 20 单「来源不可得」）的机制化回应：把「锚是否在手」变成开机检的分类判据，而不是写作期才发现。

### ④ research_plan 销项账本（历史 27 计划 / 44 任务）

| 指标 | 值 |
|---|---|
| 已立计划课题 | 27 |
| 计划任务总数 | 44 |
| 已销项（≥1 报告） | 36 |
| 未销项（零报告） | 8 |
| 计划形式封口课题 | 20 |
| 未封口课题 | 7 |
| 接触报告总数 | 43 |

**未销项任务清单（本波诊断重试对象）**：

| 课题 | 未销项 task_key | mission | DB 状态 | 诊断 |
|---|---|---|---|---|
| `damaged-stability-flooding-td` | `paper-exp-damaged-stability-flooding-td-1` | 7507 | succeeded | mission 终态 succeeded 但零报告（静默失败） |
| `ice-nav-operational-chain` | `paper-exp-ice-nav-operational-chain-1` | 7506 | succeeded | mission 终态 succeeded 但零报告（静默失败） |
| `lbm-suboff-tau` | `paper-exp-lbm-suboff-tau-3` | 7479 | failed | mission 终态 failed（零报告） |
| `lbm-suboff-tau` | `paper-exp-lbm-suboff-tau-4` | 7480 | succeeded | mission 终态 succeeded 但零报告（静默失败） |
| `maneuvering-podded-ice` | `paper-exp-maneuvering-podded-ice-1` | 7498 | succeeded | mission 终态 succeeded 但零报告（静默失败） |
| `propeller-openwater-bem` | `paper-exp-propeller-openwater-bem-1` | 7484 | succeeded | mission 终态 succeeded 但零报告（静默失败） |
| `stability-large-angle-gz` | `paper-exp-stability-large-angle-gz-1` | 7503 | succeeded | mission 终态 succeeded 但零报告（静默失败） |
| `wind-load-blendermann-weather-criterion` | `paper-exp-wind-load-blendermann-weather-criterion-1` | 7509 | succeeded | mission 终态 succeeded 但零报告（静默失败） |

> 结论（诚实）：**任务状态 ≠ 证据**。8 个未销项任务里，终态 succeeded 却零报告者占多数——这不是写作问题，而是执行单缺「必交工件」硬门。W20 起所有科研任务单正文强制三要素（任务/判据/工件）+ 零报告即失败条款。

### ⑤ W20 新增 research_plan（科研任务先行：任务/判据/工件三要素）

| task_key | 计划项 | 动作 | 仓 | 外部锚 | 判据条数 | 工件数 | mission |
|---|---|---|---|---|---|---|---|
| `paper-exp-composite-laminate-verification-1` | 1 | exp-new-plan | `TensorFEM` | AN-ANALYTIC-NAVIER | 3 | 3 | 9653 |
| `paper-exp-damaged-stability-flooding-td-2` | 2 | exp-close-gap | `ship-performance-platform` | AN-ISCODE2008 | 3 | 3 | 9643 |
| `paper-exp-grain-stability-igc-1` | 1 | exp-new-plan | `ship-performance-platform` | AN-IGC | 3 | 3 | 9650 |
| `paper-exp-green-shipping-iso19030-1` | 1 | exp-new-plan | `ship-performance-platform` | AN-ISO19030, AN-MEPC353 | 3 | 3 | 9651 |
| `paper-exp-hull-vibration-analytic-kernel-2` | 2 | exp-extend | `TensorFEM` | AN-ISO6954 | 3 | 3 | 9649 |
| `paper-exp-ice-nav-operational-chain-2` | 2 | exp-close-gap | `ship-performance-platform` | AN-ISO19906, AN-LINDQVIST | 3 | 3 | 9644 |
| `paper-exp-ice-resistance-crossimpl-2` | 2 | exp-extend | `ship-performance-platform` | AN-LINDQVIST | 3 | 3 | 9648 |
| `paper-exp-lbm-suboff-tau-6` | 6 | exp-close-gap | `TensorLBM` | AN-SUBOFF, AN-ITTC57 | 4 | 3 | 9639 |
| `paper-exp-lbm-suboff-tau-7` | 7 | exp-close-gap | `TensorLBM` | AN-SUBOFF, AN-ITTC57 | 3 | 2 | 9640 |
| `paper-exp-maneuvering-podded-ice-2` | 2 | exp-close-gap | `TensorFEM` | AN-MSC137, AN-ISO19906 | 3 | 3 | 9645 |
| `paper-techreport-paper-line-machine-gates` | — | techreport | `TensorPapers` | — | 3 | 0 | 9654 |
| `paper-techreport-physics-contract-verification` | — | techreport | `TensorPapers` | — | 3 | 0 | 9655 |
| `paper-exp-propeller-openwater-bem-5` | 5 | exp-close-gap | `TensorBEM` | AN-KP505 | 3 | 3 | 9641 |
| `paper-exp-seakeeping-truncation-4` | 4 | anchor-repair | `TensorBEM` | AN-WIGLEY, AN-ITTC-SEAKEEP | 3 | 3 | 9647 |
| `paper-exp-stability-large-angle-gz-2` | 2 | exp-close-gap | `ship-performance-platform` | AN-ISCODE2008 | 3 | 3 | 9646 |
| `paper-exp-undex-shock-chain-1` | 1 | exp-new-plan | `TensorFEM` | AN-COLE | 3 | 3 | 9652 |
| `paper-exp-wind-load-blendermann-weather-criterion-3` | 3 | exp-close-gap | `ship-performance-platform` | AN-BLEND | 3 | 3 | 9642 |

派单回执：本波 POST 2 单（exp 15 / techreport 2），查重跳过 0 单；模型统一 `deepseek-v4-flash`（非 EVO-1 臂席专用模型），runner=native，预算 exp 100 calls/14400 s、techreport 80 calls/14400 s。

**计划项设计原则**（对顶刊审稿人视角的回应）：

- 每个计划项对应一个**可机器的量化判据**（阈值写死在 goal 里，达标或 honest FAIL 均算销项）；
- 每个计划项必交**工件路径**（JSON 结论件 + markdown 报告），零报告即视为任务失败；
- 外部锚在 goal 里逐条列出（名称+出处+级别+可达性），写稿时直接从锚件取值，不再「写作期现找锚」；
- 单例不足以支撑顶刊结论的课题（tasks<3 或接触报告<3）一律走 `exp-extend`（多工况/系综/量纲机检），不允许单例直接成稿。

### ⑥ 成稿单判定（顶刊四门全过才派）

- 本波 `draft-ready` 课题：`seakeeping-truncation`；
- 成稿单实派：0 单。理由：只有 research_plan 全销项的 external 课题才派 paper-draft-<slug>；本波唯一 draft-ready 课题（seakeeping-truncation）因锚核销返工（exp-4）在批，计划回退为未销项 → 本波成稿单 0 个，理由随件登记。
- `seakeeping-truncation`：本波新增计划项 → 计划未全销项（新增计划项 `paper-exp-seakeeping-truncation-4`）

> 本波 0 成稿单是**判据结果，不是空转**：唯一达成形式条件的课题在锚核销返工中（W18 exp#1 自报 Wigley 试验锚「源不可达」，而仓内 `TensorBEM/benchmarks/verified/bem_wigley_*` 有已核验件），按「计划未全销项不得写正文」纪律，先派 exp 返工再议成稿。

### ⑦ 归档

- 数据：`papers/data/w20-2026-11-09/`（inventory / digest / registry_review / candidates / uncovered / mission_ledger / research_plan_ledger / anchors / anchors_check / tracks / research_plan / payloads_exp / payloads_tech / dispatched / figures / number_audit）
- 图件：`papers/figures/w20_dual_track.png`、`papers/figures/w20_anchor_reachability.png`、`papers/figures/w20_plan_closure.png`、`papers/figures/w20_window_composition.png`（脚本 `papers/tools/w20_figures.py`，输入/输出 sha256 见 `figures.json`）
- 工具：`papers/tools/w20_{extract,plan,anchors,tracks,research_plan,dispatch,figures,report}.py` + `gen_w20_section.py` + `test_w20_artifacts.py`
- 报告：平台报告见 `docs/w20-research-report.md` 同源
