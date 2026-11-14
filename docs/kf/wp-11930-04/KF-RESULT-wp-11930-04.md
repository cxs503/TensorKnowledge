# KF-RESULT wp-11930-04

**工序** 04-independent-review（独立对抗式审核）· **报告** report_id=11930 · **审核对象** wp-11930-01（资产登记）
**源** `tensor://reports/11930` · markdown sha256 `5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325` · 13121 字符 / 22324 字节（评审侧从平台重新取回并独立重算，与契约声明一致）
**场景** `p270w2c-n08-bpm-calibration-feasibility` · **评审人** agent/m19840（red-team-reviewer）· **不修改上游产物**

## ① 本工序做了什么

对报告 11930《BPM 微观参数三目标联合标定的可行性判定与可辨识性审计》做**独立对抗式审核**：不读生产者的解释与叙述，只拿**报告原文 + 上游 wp-11930-01 的资产清单**，把报告里每一个可复算的数字重算一遍，把每一条结论绑到逐字引文，然后判 pass / fail / needs-fix。

- **上游包 wp-11930-01（资产登记）**：裁决 **pass** —— 哈希/字符数、14/14 定位器、计数、6/6 图字节全部独立复算通过。
- **报告语义保真度**：裁决 **needs-fix** —— 所有可复算的主数字都复现（雅可比谱/条件数/秩、24 项相关矩阵逐格一致、幂律留出预测、AC5/AC4b 偏差、CI 宽度、几何/堆积），报告的 honest FAIL 也与自身数字自洽；但有 7 处需要改正（3 项 major、4 项 minor、3 项 informational），故 needs-fix 而非 pass。
- **未把任何结论标为 verified**：本工序只记录评审侧复算事实，claim 状态提升由平台门计算。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET $TENSOR_API_BASE/tensor/reports/11930` 取 `markdown` 字段，落盘 `work/wp-11930-04/source_report.md`，独立重算 sha256/字符/字节；
2. **读上游 KO**：`docs/kf/wp-11930-01/kf_result.wp-11930-01.json`（asset_manifest 14 条资产）——只读、不改；
3. **机器检查账本**：`work/wp-11930-04/verify_wp-11930-04.py` 跑 35 条检查 = PASS 28 / WARN 7 / FAIL 0：
   - R1 源身份：新鲜哈希 == 契约 == 上游清单（13121 字符 / 22324 字节）；
   - R2 定位器：14/14 `source[start:end] == quote`、quote 唯一、path 词元落在 quote 内；
   - R3 计数：assets/by_class/by_resolution 由 14 条记录重算；
   - R4 图资产：6/6 从平台 `GET /tensor/reports/11930/figures/<name>` 取回 HTTP 200 image/png，sha256 与字节数与上游清单一一致，caption 与报告记录 `figures[]` 逐字相同；
   - N* 语义保真：几何/堆积/雅可比谱与条件数/相关矩阵/Brun γ/幂律留出/AC4b/AC5/AC6/AC7 全部由报告自身公开的数字重算（含数值 Jacobian 的 SVD、JᵀJ 归一化相关矩阵、`σ_t=σ₀t^(−1/m)` 预测）。
4. **关键设置**：所有引文由脚本按精确子串切出并记录字符偏移（build_review.py 断言唯一性）；数值用 numpy 重算，不复制报告结果；每条发现给出 `reproduction` 字段（复跑哪条检查）。
5. **产物生成**：`build_review.py` → `review_report.json` / `review_events.json` / `kf_result.wp-11930-04.json`；`make_figure.py` → 复算对照图；`selfcheck.py` → 契约门自检；`repro.sh` 一键复跑全链。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-11930-04/kf_result.wp-11930-04.json` | 本工序结果（package_id/task_type/report_id/provenance/outputs），source_hash 与原文一致 |
| `docs/kf/wp-11930-04/review_report.json` | 审核报告：独立性声明、范围、35 条检查账本、10 条分级发现、过度声明清单、处置（needs-fix） |
| `docs/kf/wp-11930-04/review_events.json` | 2 条审核事件：`tkr:package:wp-11930-01`=approve；`tkr:report:11930`=request-changes（review-event.v1 通过校验） |
| `work/wp-11930-04/verify_wp-11930-04.json` | 机器检查账本（35 条，逐条 expected/observed/verdict） |
| `work/wp-11930-04/selfcheck.json` | 契约门自检（6 门全 PASS） |
| `work/wp-11930-04/fig_review_reproducibility.png` | 图 1：公开发布值 vs 独立复算值（A）、Brun γ 三种定义（B）、“局部 m”标签（C） |
| `work/wp-11930-04/{fetch_source,verify_wp-11930-04,build_review,make_figure,selfcheck}.py`、`repro.sh` | 可复跑工具链 |

**图 1** 三面板：(A) 报告公开数字与我方复算值的相对偏差（对数轴，红线=2% 带宽，14/14 落在带内，最大 1.30%，来自两位有效数字的百分比本身）；(B) 最坏参数对 ['k_c','k_p'] 的 Brun 共线性指数：发布值 6.71 vs 标准定义 4.80（Brun）/ 9.49（Belsley）——6.71 对不上任一标准定义，只有非标准 `1/√(1−ρ)` 给出 6.75；(C) “局部 m”列 0.080/0.045 与全局 m=262.976 差 3 个量级，数值只与局部指数 1/m（m≈12.5/22.2）相容。

## ④ 证据定位表（claim/字段 → 原文逐字引文 + 字符偏移）

| 发现 | 字段/论断 | 偏移 | 原文引文（逐字） |
|---|---|---|---|
| F1 | finding 原文锚点 | c[4601:4660] L77 | `最坏参数对 ['k_c', 'k_p']：Brun γ = 6.71，相关系数 0.978；全 6 列 γ = inf` |
| F2 | finding 原文锚点 | c[7269:7312] L144 | `端点局部 m：t=0.05 → 0.080、t=0.8 → 0.045，方向一致性 是` |
| F2.t | table_locator | c[7091:7135] L141 | `| 0.05 | 0.397 | 0.376 | -5.4% | 0.080 | 是 |` |
| F3 | finding 原文锚点 | c[12040:12112] L233 | `| 巴西中心主应力比 | Hondros −3.0（解析）| 最优 -2.705（相对 9.8%）| 否（差两个量级，honest FAIL）|` |
| F4 | finding 原文锚点 | c[3982:4022] L62 | `200 组随机 θ 只跑 UCS（AC6，验证“随机参数几乎不可能落进文献带”）` |
| F4.r | result_locator | c[1257:1293] L16 | `违反比例 83.5%（n = 200；UCS 中位 2.546 MPa）` |
| F5 | finding 原文锚点 | c[4095:4152] L68 | `UCS 试件：H/D = 2.000（ASTM D7012 带 [1.5, 2.5]）→ PASS，颗粒数 144` |
| F6 | finding 原文锚点 | c[7182:7268] L144 | `拟合得到 m = 262.976（bootstrap 95% CI [24.916, 746.453]，CI 宽度 721.537），σ_ref = 3.71e+05 Pa` |
| F6.r | recomputed_locator | c[792:945] L13 | `| AC3 三分支可行性 | (a)/(b)/(c) 之一 + 证据 | 参考 θ 落 **分支 (c)**：UCS 1.010 MPa、σc/σt 2.688、m CI [24.916, 746.453] （伪真值 6.000）；33 个设计点分支计数 a/b/c = 0/0/33 | 见 §3.3 |` |
| F7 | finding 原文锚点 | c[8761:8814] L180 | `两次独立进程 UCS = 1.01e+06 / 1.01e+06 Pa，相对差 0.000（门 1e-3）` |
| F9 | finding 原文锚点 | c[6590:6636] L127 | `| m | 0.8092 | 0.0904 | 0.5689 | 26/28 | n/a |` |
| F10 | finding 原文锚点 | c[792:945] L13 | `| AC3 三分支可行性 | (a)/(b)/(c) 之一 + 证据 | 参考 θ 落 **分支 (c)**：UCS 1.010 MPa、σc/σt 2.688、m CI [24.916, 746.453] （伪真值 6.000）；33 个设计点分支计数 a/b/c = 0/0/33 | 见 §3.3 |` |
| KV | Jacobian spectrum from published J | c[4366:4441] L75 | `- cond(J) = **9.063**；奇异值 5.848、2.151、0.645；rank(J) = 3/6，非零奇异值给出的结构零空间维数 3` |
| KV | AC5 deviations | c[8409:8482] L175 | `判定：PASS（容差 15%，按**中心区**读数判定）；但跨 9 个（分辨率 × 区域）配置的偏差范围 10–788%，**稳健性 FAIL**` |
| OC | negative control described as showing ra | c[3982:4022] L62 | `200 组随机 θ 只跑 UCS（AC6，验证“随机参数几乎不可能落进文献带”）` |
| OC | '差两个量级' contradicts the 9.8% in the same | c[12040:12112] L233 | `| 巴西中心主应力比 | Hondros −3.0（解析）| 最优 -2.705（相对 9.8%）| 否（差两个量级，honest FAIL）|` |
| OC | '局部 m' values 0.080/0.045 are 1/m-like,  | c[7269:7312] L144 | `端点局部 m：t=0.05 → 0.080、t=0.8 → 0.045，方向一致性 是` |
| OC | '相对差 0.000' exceeds the displayed 3-sign | c[8761:8814] L180 | `两次独立进程 UCS = 1.01e+06 / 1.01e+06 Pa，相对差 0.000（门 1e-3）` |
| OC | H/D=2.000 mixes gauge H with bounding-bo | c[4095:4152] L68 | `UCS 试件：H/D = 2.000（ASTM D7012 带 [1.5, 2.5]）→ PASS，颗粒数 144` |
| OC | AC3 verdict cell gives no PASS/FAIL | c[792:945] L13 | `| AC3 三分支可行性 | (a)/(b)/(c) 之一 + 证据 | 参考 θ 落 **分支 (c)**：UCS 1.010 MPa、σc/σt 2.688、m CI [24.916, 746.453] （伪真值 6.000）；33 个设计点分支计数 a/b/c = 0/0/33 | 见 §3.3 |` |

**分级发现汇总**（完整叙述见 `review_report.json.findings[]`）

| ID | 严重度 | 阻断 | 范围 | 问题（摘要） |
|---|---|---|---|---|
| F1 | major | 否 | §3.2 AC2 diagnostic: Brun collinearity index of the worst parameter pair | Published γ=6.71 for pair ['k_c','k_p'] is not reproducible from the published correlation ρ=0.978 under either standard definition: Brun γ=1/√(1−R²)=4.796, Belsley 2-column index √((1+ρ)/(1−ρ))=9.486. Only the… |
| F2 | major | 否 | §3.4 AC4 table column '局部 m' and the direction-consistency sentence | The '局部 m' column reports 0.080 (t=0.05) and 0.045 (t=0.80), i.e. 3–4 orders of magnitude below the global m=262.976 fitted in the same paragraph. If read literally as Weibull moduli, the local values contradic… |
| F3 | minor | 否 | §5 error table, Brazilian centre stress-ratio row | The same row states a 9.8% relative difference and then qualifies it as '差两个量级' (two orders of magnitude). 9.8% (and even the worst configuration, 788%) is not a two-order-of-magnitude gap; the qualitative clau… |
| F4 | major | 否 | §2 method item 7 (negative control) vs §3.6 measured result | The method text says the 200-random-θ control 'verifies that random parameters can hardly land in the literature band', but the measured violation ratio is 83.5%, i.e. 33/200 ≈ 16.5% (about one in six) random p… |
| F5 | minor | 否 | §0/§3.1 AC1 UCS aspect-ratio sub-item | H/D=2.000 mixes endpoints: H=0.2 m is the gauge (8 lattice spacings, centre-to-centre of the driven end layers) while D=0.1 m is the bounding-box diameter (3 spacings + 2 radii). Under uniform conventions the s… |
| F6 | minor | 否 | §3.3/§3.4 numbers that cannot be re-derived from the report text | The fitted-thickness tensile strengths (t=0.1/0.2/0.4, the fit inputs) are never printed, so the published σc/σt=2.688 and m=262.976 cannot be recomputed from the report alone; only the two holdout predictions … |
| F7 | informational | 否 | §0/§3.6 AC7 reproducibility | 'relative difference 0.000' is asserted from two values printed to three significant figures (1.01e+06 Pa each); the displayed evidence cannot support an exact-zero claim (it only bounds the difference by ~1e-3… |
| F8 | informational | 否 | review limitation inherited from upstream wp-11930-01 | 7/14 registered assets (module, 3 scripts, test suite, records.jsonl, artifacts report.json) are referenced_unresolved and live only in the TensorDEM checkout; 1 is declared absent. The 42-test suite, the 747-t… |
| F9 | informational | 否 | §3.3 proxy accuracy table → use of the Pareto front as AC3 evidence | The quadratic surrogate for m has LOO R²=0.0904 (in-sample 0.8092), i.e. essentially no out-of-sample predictive power. The report discloses this and states the (c) branch rests on DEM design points plus the pr… |
| F10 | minor | 否 | §0 acceptance table, AC3 row | The AC3 verdict cell reads '见 §3.3' instead of PASS/FAIL, breaking the table's own per-AC verdict format. The content of §3.3 (branch (c) with evidence) satisfies AC3's stated criterion, so the intended verdict… |

**机器检查账本摘录**（35 条全表在 `verify_wp-11930-04.json`）

| 检查 | 结果 | 观测 |
|---|---|---|
| R1.1_source_hash_fresh_vs_contract | PASS | sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325 |
| R1.2_hash_vs_upstream_manifest | PASS | sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325 |
| R1.3_chars | PASS | 13121 |
| R1.4_bytes_utf8 | PASS | 22324 |
| R1.5_kf_reports_same_hash | PASS | sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325 |
| R2.1_all_14_locators_span_exact_unique_path_token | PASS | 14/14 exact |
| R3.1_manifest_counts_recomputed | PASS | {'assets': 14, 'by_class': {'module': 1, 'script': 3, 'test': 1, 'data': 3, 'figure': 6}, 'by_resolution': {'r |
| R4.1_six_figure_assets_bytes_and_captions | PASS | 6/6 verified |
| N1.1_ucs_diameter_bounding_box | PASS | 0.1 |
| N1.2_ucs_HD_three_conventions | WARN | {'gauge_over_extent_reported': 2.0, 'extent_over_extent': 2.25, 'c2c_over_c2c': 2.667} |
| N1.3_particle_count_4x4x9 | PASS | 144 |
| N1.4_number_density_1_over_spacing3 | PASS | 63999.999999999985 |
| N1.5_packing_pi_over_6 | PASS | 0.5236 |
| N1.6_brazil_D_over_t | PASS | 1.75 |
| N1.7_tensile_HD_family | PASS | [0.5, 1.0, 2.0, 4.0, 8.0] |
| N2.1_singular_values | PASS | [5.85, 2.148, 0.646] |
| N2.2_cond_J | PASS | 9.0588 |
| N2.3_rank_and_null_dim | PASS | {'rank': 3, 'null_dim': 3} |
| N2.4_parameter_correlation_matrix_reproduced | PASS | 0.0 |
| N2.5_brun_gamma_pair_kc_kp | WARN | {'rho': 0.978, '1/sqrt(1-rho^2)': 4.796, 'sqrt((1+rho)/(1-rho))': 9.486, '1/sqrt(1-rho)': 6.745} |
| N2.6_full_column_gamma_inf | PASS | 100000000.0 |
| N3.1_powerlaw_prediction_t005 | PASS | 0.3753 |
| N3.2_powerlaw_prediction_t080 | PASS | 0.3713 |
| N3.3_holdout_relative_errors | PASS | {'t=0.05': '-5.5%', 't=0.80': '+2.6%'} |
| N3.4_bootstrap_CI_width | PASS | 721.537 |
| N3.5_local_m_column_values | WARN | {'published_local_m': [0.08, 0.045], 'implied_m_if_1/local_m': [12.5, 22.2], 'global_m': 262.976} |
| N4.1_AC5_relative_errors_vs_hondros_-3 | PASS | [[-3.481, 16.0], [-4.18, 39.3], [-2.705, 9.8], [-6.906, 130.2], [-9.155, 205.2], [-26.642, 788.1]] |
| N4.2_AC5_qualitative_phrase | WARN | 报告 §5 同一行写“差两个量级” |
| N5.1_AC4b_ucs_refinement_deviations | PASS | [[1.0098, 0.0], [0.8559, -15.2], [0.6728, -33.4]] |
| N5.2_AC4b_t04_deviations | PASS | [[0.3564, 0.0], [0.3557, -0.2], [0.3832, 7.5]] |
| N6.1_AC6_violation_count_integral | PASS | {'167/200': 83.5, '168/200': 84.0} |
| N6.2_AC6_narrative | WARN | §2 条 7 表述“随机参数几乎不可能落进文献带” |
| N7.1_ke_ratio_gate_multiple | PASS | 22.0 |
| N7.2_AC7_zero_difference_display | WARN | 1.01e+06 / 1.01e+06 Pa |
| N8.1_sigma_t_fitted_thicknesses_published | WARN | 报告只给留出 t=0.05/0.80 两行 |

## ⑤ 注意点与局限

1. **审核上限来自上游登记**：14 条资产中 7 条 `referenced_unresolved`（模块 / 3 个脚本 / 测试 / records.jsonl / artifacts report.json）、1 条声明缺失。因此 DEM 物理、42 项 pytest、747 任务战役、NSGA-II、KE/外功门**均未复跑**，只做报告内部的数字自洽审核。
2. **图只做字节级核对**：6 张 PNG 的 sha256/字节数与上游清单一一致，但**未逐图目视比对** caption 所声称的内容（列入 `checks_not_run`）。
3. **同源风险**：我的复算输入是报告自己公开的数字（例如公开到 2 位小数的 Jacobian、只给两位有效数字的百分比），所以与生产者共享的错误（例如代码里 γ 公式写错）不会被我的复算捕获——F1 正是这类：ρ 与 γ 各自“来自”报告，但两者不自洽。
4. **未对标一次文献**：Schulson & Duval 的 UCS 带、Hondros 解均无原始字节可查，故只按报告声明的基准核对算术，不评判基准本身。
5. **不改上游、不改结论口径**：本工序未修改 `docs/kf/wp-11930-01/**`（selfcheck 里 `git status` 为空），也未把任何 claim 标为 verified；处置只出“裁决 + needs-fix 清单”。

### 误差判定（关键量 vs 基准，逐项回答“是否 < 3%”）

| 关键量 | 基准 | 我方复算 | 相对差 | 是否 < 3% |
|---|---|---|---|---|
| cond(J) | 报告 9.063 | 9.0588（由公开 2 位小数 J 重算） | 0.046% | **是** |
| 奇异值 σ₁/σ₂/σ₃ | 5.848 / 2.151 / 0.645 | [5.85, 2.148, 0.646] | ≤0.13% | **是** |
| 参量相关矩阵 24 项 | 报告矩阵 | `max|Δ|=0.000`（JᵀJ 归一化重算） | 0.000 | **是** |
| 幂律留出预测 t=0.05 / 0.80 | 0.376 / 0.372 MPa | 0.3753 / 0.3713 MPa | 0.19% / 0.19% | **是** |
| 留出相对误差 | −5.4% / +2.6% | {'t=0.05': '-5.5%', 't=0.80': '+2.6%'} | ≤1.30% | **是** |
| AC5 六项偏差 | 9.8/16.0/39.3/130.2/205.2/788.1% | 逐项重算相同 | 0.00–0.34% | **是** |
| AC4b 偏差 | −15.2/−33.4/−0.2/+7.5% | 逐项重算相同 | ≤0.27% | **是** |
| **Brun γ（最坏参数对）** | 报告 6.71 | 4.796（Brun）/ 9.486（Belsley）/ 6.745（1/√(1−ρ)） | 28.5% / 41.4% / 0.5% | **否**（任一标准定义均 >3%，故 F1 major） |
| **“局部 m”列** | 全局 m=262.976 | 0.080 / 0.045（只与 1/m 相容 → m≈12.5/22.2） | 3 个量级 | **否**（F2 major） |
| AC6 违反比例 | 83.5%（n=200） | 167/200 = 83.5% | 0.00% | **是**（但 §2 叙述“几乎不可能”与之不符，F4） |

**显式回答**：报告**可复算的主数字 14/14 均在 3% 内**（最大 1.30%，源于两位有效数字的百分比本身）；**两处不可复算的公开量（Brun γ、局部 m）远远超出 3%，就是本单 request-changes 的原因**；不存在“看起来通过、实际未算”的项——未跑的项目全部列入 `checks_not_run`，不冒充通过。

## ⑥ 自检（逐条对照 acceptance）

| 验收项 | 结果 | 依据 |
|---|---|---|
| valid_json | ✅ | 3/3 deliverables parse |
| schema_pass | ✅ | kf_result.v1 OK; review-event.v1 OK for 2 events |
| reviewer_independent | ✅ | upstream producer=agent/m15731 · scripts/kf_wp11930_register.py; reviewer ids=['agent/m19840']; upstream tree dirty=False |
| upstream_packages_completed | ✅ | upstream hash==contract==deliverable (sha256:5adb132dcf96…); 01 asset_manifest 14 assets |
| quote_fidelity | ✅ | 20 quotes, 0 mismatched, source hash matches contract |
| no_claims_marked_verified | ✅ | review output has no claims[] and no verified status flag |

- `valid_json` ✅ 三份产物均可解析；
- `schema_pass` ✅ kf_result.v1 + review-event.v1（draft 2020-12）通过；
- `reviewer_independent` ✅ 上游生产者 `agent/m15731`、评审人 `agent/m19840`，且 `docs/kf/wp-11930-01/**` 无改动；
- `upstream_packages_completed` ✅ 上游 01 结果存在、source_hash 与契约/本工序产物三者一致、14 条资产；
- 附加门：`quote_fidelity`（18 条引文逐字可定位、唯一）、`no_claims_marked_verified` ✅。

**如实说明的未完成项**：DEM 侧复跑（pytest 42 项 / 747 任务战役 / NSGA-II / KE 门）与 6 张图的目视核对**未做**，原因是上游资产 `referenced_unresolved`/`declared_absent`（见 ⑤-1、⑤-2）；因此本审核**不能**对“物理结论是否正确”下判断，只能对“报告内部数字与结论是否自洽、是否可复算”下判断。

**处置**：request-changes（needs-fix）—— 阻断项 0；需改 7 条（F1、F2、F3、F4、F5、F6、F10；major=3），其余为 informational。

## 一键复跑

```bash
bash work/wp-11930-04/repro.sh   # fetch -> verify(35 checks) -> build -> selfcheck(6 gates)
```

`repro_cmd`: `bash work/wp-11930-04/repro.sh`

## 结果 JSON（唯一）

```json
{
 "package_id": "wp-11930-04",
 "task_type": "04-independent-review",
 "contract_version": "1.0",
 "report_id": "11930",
 "provenance": {
  "source_uri": "tensor://reports/11930",
  "source_field": "markdown",
  "source_hash": "sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325",
  "source_hash_matches": true,
  "title": "BPM 微观参数三目标联合标定的可行性判定与可辨识性审计（P270W2C-N08）",
  "scenario_key": "p270w2c-n08-bpm-calibration-feasibility",
  "chars": 13121
 },
 "outputs": {
  "review_report.json": {
   "package_id": "wp-11930-04",
   "task_type": "04-independent-review",
   "report_id": "11930",
   "review_type": "adversarial-independent-review",
   "reviewed_package": "wp-11930-01",
   "reviewed_artifacts": {
    "report_markdown": {
     "uri": "tensor://reports/11930",
     "sha256": "sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325",
     "chars": 13121,
     "bytes_utf8": 22324
    },
    "upstream_kf_result": {
     "path": "docs/kf/wp-11930-01/kf_result.wp-11930-01.json",
     "sha256": "sha256:52fa73beb02091ae628a19f5898a3c67031286d9f31c556713c65963317dc230"
    }
   },
   "independence": {
    "statement": "Reviewer fetched report 11930 markdown fresh from GET /api/v1/tensor/reports/11930 and read only that markdown plus the upstream wp-11930-01 asset manifest. No producer explanation, chat log, commit message or upstream narrative was consulted; the reviewer did not read the producer's scripts beyond their registration entries.",
    "limitations": [
     "The TensorDEM checkout (module, scripts, test suite, records.jsonl, artifacts report.json) is not present in this repository, so DEM physics, the 42-item pytest suite, the 747-task campaign, the NSGA-II run and the KE/work gate were NOT re-executed.",
     "Six figure PNGs were byte-hashed against the manifest hashes but NOT visually compared against their caption claims.",
     "Mathematics was re-derived from the numbers printed in the report, so any mistake shared between the report text and the underlying pipeline would not be caught by this review (no primary-source model audit)."
    ]
   },
   "scope": [
    "semantic fidelity of every recomputable number in the report (geometry, packing, Jacobian spectrum/cond/rank, correlation matrix, Brun index, Weibull power-law holdout, AC4b protocol refinement, AC5 stress-ratio deviations, AC6/AC7 percentages)",
    "internal consistency of tables, verdicts and cross-references",
    "claim–evidence binding and severity of overstatements",
    "upstream asset-registration fidelity (hash, locators, counts, figure bytes)"
   ],
   "method": {
    "tool": "work/wp-11930-04/verify_wp-11930-04.py (fresh fetch + 35-machine-check ledger)",
    "ledger": "work/wp-11930-04/verify_wp-11930-04.json",
    "summary": {
     "total": 35,
     "pass": 28,
     "warn": 7,
     "fail": 0
    },
    "quote_policy": "every quote in this review is a substring of the fresh markdown, stored with start/end char offsets (build_review.py asserts uniqueness)"
   },
   "checks_performed": [
    {
     "check": "R1.1_source_hash_fresh_vs_contract",
     "expected": "sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325",
     "observed": "sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325",
     "result": "PASS",
     "note": ""
    },
    {
     "check": "R1.2_hash_vs_upstream_manifest",
     "expected": "5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325",
     "observed": "sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325",
     "result": "PASS",
     "note": ""
    },
    {
     "check": "R1.3_chars",
     "expected": 13121,
     "observed": 13121,
     "result": "PASS",
     "note": ""
    },
    {
     "check": "R1.4_bytes_utf8",
     "expected": 22324,
     "observed": 22324,
     "result": "PASS",
     "note": ""
    },
    {
     "check": "R1.5_kf_reports_same_hash",
     "expected": "sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325",
     "observed": "sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325",
     "result": "PASS",
     "note": ""
    },
    {
     "check": "R2.1_all_14_locators_span_exact_unique_path_token",
     "expected": "14/14 exact",
     "observed": "14/14 exact",
     "result": "PASS",
     "note": "[]"
    },
    {
     "check": "R3.1_manifest_counts_recomputed",
     "expected": {
      "assets": 14,
      "by_class": {
       "module": 1,
       "script": 3,
       "test": 1,
       "data": 3,
       "figure": 6
      },
      "by_resolution": {
       "referenced_unresolved": 7,
       "resolved_in_source": 6,
       "declared_absent": 1
      }
     },
     "observed": {
      "assets": 14,
      "by_class": {
       "module": 1,
       "script": 3,
       "test": 1,
       "data": 3,
       "figure": 6
      },
      "by_resolution": {
       "referenced_unresolved": 7,
       "resolved_in_source": 6,
       "declared_absent": 1
      }
     },
     "result": "PASS",
     "note": ""
    },
    {
     "check": "R4.1_six_figure_assets_bytes_and_captions",
     "expected": "6/6 HTTP200 png + sha256 + bytes + caption",
     "observed": "6/6 verified",
     "result": "PASS",
     "note": "[{\"name\": \"fig_response_surface.png\", \"status\": 200, \"ctype\": \"image/png\", \"bytes\": 101650, \"sha256\": \"sha256:51110cf7696adcee081421d2a92605a7cce80808ca294b7901120c4cc4756eec\", \"manifest_bytes\": 101650, \"bytes_match\": true, \"sha_match\": true, \"caption_matches_record\": true}, {\"name\": \"fig_jacobian.png\", \"status\": 200, \"ctype\": \"image/png\", \"bytes\": 98897, \"sha256\": \"sha256:412e3b536a4f35bdf37b52254700e12dcf766e51e3efdb497489481efcb97f28\", \"manifest_bytes\": 98897, \"bytes_match\": true, \"sha_match\": true, \"caption_matches_record\": true}, {\"name\": \"fig_pareto.png\", \"status\": 200, \"ctype\": \"image/png\", \"bytes\": 72532, \"sha256\": \"sha256:8fe9f1a288cfa41ab23b1afbf52019d25b4088394977461772648efa173a247c\", \"manifest_bytes\": 72532, \"bytes_match\": true, \"sha_match\": true, \"caption_matches_record\": true}, {\"name\": \"fig_size_effect.png\", \"status\": 200, \"ctype\": \"image/png\", \"bytes\": 74350, \"sha256\": \"sha256:cc650deaa8c0878edeb662e262b1edd719d1aa18e8020908f58cb4ccf32dc743\", \"manifest_bytes\": 74350, \"bytes_match\": true, \"sha_match\": true, \"caption_matches_record\": true}, {\"name\": \"fig_brazilian.png\", \"status\": 200, \"ctype\": \"image/png\", \"bytes\": 100699, \"sha256\": \"sha256:52c4b300d8668a5b3c2588b2d0aefdd15de10606cb6a0893e3bb7505e90296f8\", \"manifest_bytes\": 100699, \"bytes_match\": true, \"sha_match\": true, \"caption_matches_record\": true}, {\"name\": \"fig_ucs.png\", \"status\": 200, \"ctype\": \"image/png\", \"bytes\": 51010, \"sha256\": \"sha256:a3f41eb663ea84ad0234d73a5c7c81613efc19a288eb4b6da11f5780e70fafd6\", \"manifest_bytes\": 51010, \"bytes_match\": true, \"sha_match\": true, \"caption_matches_record\": true}]"
    },
    {
     "check": "N1.1_ucs_diameter_bounding_box",
     "expected": 0.1,
     "observed": 0.1,
     "result": "PASS",
     "note": ""
    },
    {
     "check": "N1.2_ucs_HD_three_conventions",
     "expected": {
      "gauge_over_extent_reported": 2.0,
      "extent_over_extent": 2.25,
      "c2c_over_c2c": 2.667
     },
     "observed": {
      "gauge_over_extent_reported": 2.0,
      "extent_over_extent": 2.25,
      "c2c_over_c2c": 2.667
     },
     "result": "WARN",
     "note": "报告 2.000 = 标距H(0.2)/物理D(0.1)；统一口径为 2.25（仍在 ASTM [1.5,2.5]）或 2.667（出带）。混用口径未声明 → AC1 UCS 子项 PASS 依赖口径"
    },
    {
     "check": "N1.3_particle_count_4x4x9",
     "expected": 144,
     "observed": 144,
     "result": "PASS",
     "note": ""
    },
    {
     "check": "N1.4_number_density_1_over_spacing3",
     "expected": 64000.0,
     "observed": 63999.999999999985,
     "result": "PASS",
     "note": ""
    },
    {
     "check": "N1.5_packing_pi_over_6",
     "expected": 0.5236,
     "observed": 0.5236,
     "result": "PASS",
     "note": ""
    },
    {
     "check": "N1.6_brazil_D_over_t",
     "expected": 1.75,
     "observed": 1.75,
     "result": "PASS",
     "note": ""
    },
    {
     "check": "N1.7_tensile_HD_family",
     "expected": [
      0.5,
      1.0,
      2.0,
      4.0,
      8.0
     ],
     "observed": [
      0.5,
      1.0,
      2.0,
      4.0,
      8.0
     ],
     "result": "PASS",
     "note": ""
    },
    {
     "check": "N2.1_singular_values",
     "expected": [
      5.848,
      2.151,
      0.645
     ],
     "observed": [
      5.85,
      2.148,
      0.646
     ],
     "result": "PASS",
     "note": "2-decimals published J 重算 5.8499/2.1483/0.6458；报告 5.848/2.151/0.645 在四舍五入内"
    },
    {
     "check": "N2.2_cond_J",
     "expected": 9.063,
     "observed": 9.0588,
     "result": "PASS",
     "note": "由公开（2 位小数）J 重算 cond=9.0588，与 9.063 相对差 0.046%"
    },
    {
     "check": "N2.3_rank_and_null_dim",
     "expected": {
      "rank": 3,
      "null_dim": 3
     },
     "observed": {
      "rank": 3,
      "null_dim": 3
     },
     "result": "PASS",
     "note": ""
    },
    {
     "check": "N2.4_parameter_correlation_matrix_reproduced",
     "expected": "≤0.005 on 24 published entries",
     "observed": 0.0,
     "result": "PASS",
     "note": "JᵀJ 归一化重算与报告相关矩阵逐格一致（含 mu_s/mu_d 恒零列）"
    },
    {
     "check": "N2.5_brun_gamma_pair_kc_kp",
     "expected": 6.71,
     "observed": {
      "rho": 0.978,
      "1/sqrt(1-rho^2)": 4.796,
      "sqrt((1+rho)/(1-rho))": 9.486,
      "1/sqrt(1-rho)": 6.745
     },
     "result": "WARN",
     "note": "报告 γ=6.71 与公开 ρ=0.978 在两种标准定义下都对不上（4.80 / 9.49）；仅非标准 1/√(1−ρ) 给出 6.75 的量级。γ 定义未在报告声明 → 最坏参数对诊断不可独立复算。不改变 rank 3/6 的结构结论"
    },
    {
     "check": "N2.6_full_column_gamma_inf",
     "expected": "inf (structural rank deficiency)",
     "observed": 100000000.0,
     "result": "PASS",
     "note": "3 观测量/6 参数、rank=3 → 任一列可被其余列精确线性表示 → R²=1 → γ=inf，与报告一致"
    },
    {
     "check": "N3.1_powerlaw_prediction_t005",
     "expected": {
      "reported": 0.376,
      "recomputed": 0.3753
     },
     "observed": 0.3753,
     "result": "PASS",
     "note": ""
    },
    {
     "check": "N3.2_powerlaw_prediction_t080",
     "expected": {
      "reported": 0.372,
      "recomputed": 0.3713
     },
     "observed": 0.3713,
     "result": "PASS",
     "note": ""
    },
    {
     "check": "N3.3_holdout_relative_errors",
     "expected": {
      "t=0.05": "-5.4%",
      "t=0.80": "+2.6%"
     },
     "observed": {
      "t=0.05": "-5.5%",
      "t=0.80": "+2.6%"
     },
     "result": "PASS",
     "note": "由 (m=262.976, σ_ref=3.71e5) 与留出实测值重算"
    },
    {
     "check": "N3.4_bootstrap_CI_width",
     "expected": 721.537,
     "observed": 721.537,
     "result": "PASS",
     "note": ""
    },
    {
     "check": "N3.5_local_m_column_values",
     "expected": "local m should be O(10^2) like global m=262.976",
     "observed": {
      "published_local_m": [
       0.08,
       0.045
      ],
      "implied_m_if_1/local_m": [
       12.5,
       22.2
      ],
      "global_m": 262.976
     },
     "result": "WARN",
     "note": "列名“局部 m”下的 0.080/0.045 与全局 m=262.976 差 3 个量级；数值符合局部指数 1/m（即 m≈12.5/22.2）。方向一致性只对指数符号敏感 → 结论不受影响，但列名/量纲必须更正"
    },
    {
     "check": "N4.1_AC5_relative_errors_vs_hondros_-3",
     "expected": [
      [
       -3.481,
       16.0
      ],
      [
       -4.18,
       39.3
      ],
      [
       -2.705,
       9.8
      ],
      [
       -6.906,
       130.2
      ],
      [
       -9.155,
       205.2
      ],
      [
       -26.642,
       788.1
      ]
     ],
     "observed": [
      [
       -3.481,
       16.0
      ],
      [
       -4.18,
       39.3
      ],
      [
       -2.705,
       9.8
      ],
      [
       -6.906,
       130.2
      ],
      [
       -9.155,
       205.2
      ],
      [
       -26.642,
       788.1
      ]
     ],
     "result": "PASS",
     "note": ""
    },
    {
     "check": "N4.2_AC5_qualitative_phrase",
     "expected": "9.8% relative difference",
     "observed": "报告 §5 同一行写“差两个量级”",
     "result": "WARN",
     "note": "9.8%/788% 都不是两个量级（10^2）的差；同一行自相矛盾，属定量表述错误（不影响 honest FAIL 判定）"
    },
    {
     "check": "N5.1_AC4b_ucs_refinement_deviations",
     "expected": [
      [
       1.0098,
       0.0
      ],
      [
       0.8559,
       -15.2
      ],
      [
       0.6728,
       -33.4
      ]
     ],
     "observed": [
      [
       1.0098,
       0.0
      ],
      [
       0.8559,
       -15.2
      ],
      [
       0.6728,
       -33.4
      ]
     ],
     "result": "PASS",
     "note": "1.0098 → 1.010 MPa 与 §3.3 的 UCS=1.010 一致"
    },
    {
     "check": "N5.2_AC4b_t04_deviations",
     "expected": [
      [
       0.3564,
       0.0
      ],
      [
       0.3557,
       -0.2
      ],
      [
       0.3832,
       7.5
      ]
     ],
     "observed": [
      [
       0.3564,
       0.0
      ],
      [
       0.3557,
       -0.2
      ],
      [
       0.3832,
       7.5
      ]
     ],
     "result": "PASS",
     "note": ""
    },
    {
     "check": "N6.1_AC6_violation_count_integral",
     "expected": "83.5% of 200 = integer count",
     "observed": {
      "167/200": 83.5,
      "168/200": 84.0
     },
     "result": "PASS",
     "note": "200 组样本下 83.5% 恰为 167/200，计数自洽；同时意味着 33/200 随机 θ 落进文献带"
    },
    {
     "check": "N6.2_AC6_narrative",
     "expected": "83.5% violating ⇒ 16.5% inside band",
     "observed": "§2 条 7 表述“随机参数几乎不可能落进文献带”",
     "result": "WARN",
     "note": "16.5%（≈1/6）随机参数落入文献带，与“几乎不可能”不符；AC6 本身已如实记 FAIL，但该句把 FAIL 的负控说成强负控，属证据与论断不匹配"
    },
    {
     "check": "N7.1_ke_ratio_gate_multiple",
     "expected": "0.022/0.001 = 22",
     "observed": 22.0,
     "result": "PASS",
     "note": ""
    },
    {
     "check": "N7.2_AC7_zero_difference_display",
     "expected": "0.000 = 3 significant figures only",
     "observed": "1.01e+06 / 1.01e+06 Pa",
     "result": "WARN",
     "note": "两值仅给到 3 位有效数字，“相对差 0.000”强于所展示的证据；应给至少 6 位或原始 Pa 整数"
    },
    {
     "check": "N8.1_sigma_t_fitted_thicknesses_published",
     "expected": "σ_t at t=0.1/0.2/0.4 (the fit inputs)",
     "observed": "报告只给留出 t=0.05/0.80 两行",
     "result": "WARN",
     "note": "σc/σt=2.688 与 m=262.976 的拟合输入未公开 → 只能由 (m, σ_ref) 复算留出预测，无法从报告正文独立复算 2.688 与 262.976（可用 artifacts/p270w2c_n08/report.json 补，但该文件不在本仓）"
    }
   ],
   "checks_not_run": [
    "pytest tests/test_bpm_calibration_feasibility.py (42 items) — TensorDEM checkout absent",
    "DEM campaign replay (747 tasks) and runs/p270w2c_n08/records.jsonl audit — asset referenced_unresolved",
    "NSGA-II / surrogate LOO R² recomputation — artifacts/p270w2c_n08/report.json absent (also declared absent in report §4 item 1b for the JSONL)",
    "KE/work quasi-static gate recomputation — raw traces absent",
    "visual inspection of the six PNG figures",
    "primary-source check against Schulson & Duval UCS band and Hondros solution — no文献 bytes in workspace"
   ],
   "key_verifications": [
    {
     "item": "source hash",
     "result": "sha256:5adb132d…dbf325 == contract == upstream manifest (fresh fetch, 13121 chars / 22324 bytes)"
    },
    {
     "item": "Jacobian spectrum from published J",
     "claim_locator": {
      "start_char": 4366,
      "end_char": 4441,
      "start_line": 75,
      "quote": "- cond(J) = **9.063**；奇异值 5.848、2.151、0.645；rank(J) = 3/6，非零奇异值给出的结构零空间维数 3"
     },
     "result": "5.8499 / 2.1483 / 0.6458, cond=9.0588 vs published 9.063 (0.05% rounding), rank=3"
    },
    {
     "item": "parameter correlation matrix",
     "result": "24 published entries reproduced exactly from JᵀJ (max |Δ|=0.000); mu_s/mu_d columns identically zero as claimed"
    },
    {
     "item": "Weibull holdout",
     "result": "from (m=262.976, σ_ref=3.71e5): 0.3753 MPa @t=0.05 (pub 0.376), 0.3713 MPa @t=0.80 (pub 0.372); errors -5.5% / +2.6% (pub -5.4% / +2.6%)"
    },
    {
     "item": "AC5 deviations",
     "claim_locator": {
      "start_char": 8409,
      "end_char": 8482,
      "start_line": 175,
      "quote": "判定：PASS（容差 15%，按**中心区**读数判定）；但跨 9 个（分辨率 × 区域）配置的偏差范围 10–788%，**稳健性 FAIL**"
     },
     "result": "9.8 / 16.0 / 39.3 / 130.2 / 205.2 / 788.1% all recomputed exactly against Hondros −3.0"
    },
    {
     "item": "AC4b protocol refinement",
     "result": "0.8559 and 0.6728 MPa reproduce -15.2% / -33.4% vs 1.0098 MPa; t=0.4 m ±0.2% / +7.5%"
    },
    {
     "item": "AC6 count",
     "result": "83.5% of n=200 == 167/200 (integral); implies 33/200 inside band"
    },
    {
     "item": "upstream locators",
     "result": "14/14 span-exact, unique, path token inside quote"
    },
    {
     "item": "upstream figures",
     "result": "6/6 HTTP 200 image/png; sha256 and byte count equal manifest platform_sha256/platform_bytes; captions byte-identical to record figures[]"
    }
   ],
   "verdicts": {
    "upstream_package_wp-11930-01": {
     "verdict": "pass",
     "basis": "fresh hash == contract == manifest; 14/14 locators span-exact, unique, path token inside quote; counts recomputed; 6/6 figure bytes fetched from the platform match manifest platform_sha256/bytes and captions match the record figures[]."
    },
    "report_semantic_fidelity": {
     "verdict": "needs-fix",
     "basis": "all recomputable headline numbers reproduce (Jacobian spectrum/cond/rank, 24-entry correlation matrix exactly, power-law holdout predictions, AC5/AC4b deviations, CI width, packing/density/geometry), and the report's honest FAILs are consistent with its own numbers; but 7 findings (F1,F2,F3,F4,F5,F6,F10) require text/number corrections before the report can be cited."
    },
    "overall": "needs-fix"
   },
   "findings": [
    {
     "id": "F1",
     "severity": "major",
     "blocking": false,
     "scope": "§3.2 AC2 diagnostic: Brun collinearity index of the worst parameter pair",
     "finding": "Published γ=6.71 for pair ['k_c','k_p'] is not reproducible from the published correlation ρ=0.978 under either standard definition: Brun γ=1/√(1−R²)=4.796, Belsley 2-column index √((1+ρ)/(1−ρ))=9.486. Only the non-standard 1/√(1−ρ)=6.745 lands near 6.71, which suggests a missing square / undeclared formula. The report never states the γ formula, so the 'worst pair' ranking is not independently auditable.",
     "evidence_locator": {
      "start_char": 4601,
      "end_char": 4660,
      "start_line": 77,
      "quote": "最坏参数对 ['k_c', 'k_p']：Brun γ = 6.71，相关系数 0.978；全 6 列 γ = inf"
     },
     "reproduction": "verify_wp-11930-04.py N2.5: ρ recomputed from the published Jacobian JᵀJ (0.97802) → γ_brun=4.796, γ_belsley=9.486, 1/√(1−ρ)=6.745.",
     "impact": "Does not change the structural conclusion: J has rank 3/6 (recomputed N2.3) and any column is exactly representable by the others → γ=inf for the full 6-column set (recomputed N2.6).",
     "remedy": "State the Brun formula in the report (and in the code docstring) and republish γ for the pair; if the 1/√(1−ρ) form was used, fix the implementation."
    },
    {
     "id": "F2",
     "severity": "major",
     "blocking": false,
     "scope": "§3.4 AC4 table column '局部 m' and the direction-consistency sentence",
     "finding": "The '局部 m' column reports 0.080 (t=0.05) and 0.045 (t=0.80), i.e. 3–4 orders of magnitude below the global m=262.976 fitted in the same paragraph. If read literally as Weibull moduli, the local values contradict the global fit and would falsify AC4; the numbers are only consistent with the local exponent 1/m (→ m≈12.5 / 22.2). The label/quantity is wrong or at least ambiguous, while AC4 PASS hinges on 'end m direction consistency'.",
     "evidence_locator": {
      "start_char": 7269,
      "end_char": 7312,
      "start_line": 144,
      "quote": "端点局部 m：t=0.05 → 0.080、t=0.8 → 0.045，方向一致性 是"
     },
     "table_locator": {
      "start_char": 7091,
      "end_char": 7135,
      "start_line": 141,
      "quote": "| 0.05 | 0.397 | 0.376 | -5.4% | 0.080 | 是 |"
     },
     "reproduction": "verify_wp-11930-04.py N3.5: 0.080 vs global 262.976 → ratio 3287; 1/0.080=12.5, 1/0.045=22.2.",
     "impact": "Direction consistency is a sign test on the local exponent, so the AC4 verdict survives; but a reader comparing 0.080 to 263 would conclude catastrophic heterogeneity that the report does not discuss.",
     "remedy": "Rename the column to 'local exponent 1/m (local m in brackets)' or publish local m = 12.5 / 22.2 and explain the difference from the global fit."
    },
    {
     "id": "F3",
     "severity": "minor",
     "blocking": false,
     "scope": "§5 error table, Brazilian centre stress-ratio row",
     "finding": "The same row states a 9.8% relative difference and then qualifies it as '差两个量级' (two orders of magnitude). 9.8% (and even the worst configuration, 788%) is not a two-order-of-magnitude gap; the qualitative clause contradicts the quantitative cell it annotates.",
     "evidence_locator": {
      "start_char": 12040,
      "end_char": 12112,
      "start_line": 233,
      "quote": "| 巴西中心主应力比 | Hondros −3.0（解析）| 最优 -2.705（相对 9.8%）| 否（差两个量级，honest FAIL）|"
     },
     "reproduction": "verify_wp-11930-04.py N4.1 recomputes all six AC5 deviations (9.8/16.0/39.3/130.2/205.2/788.1%); none is 10².",
     "impact": "Wording only; the honest FAIL verdict and §3.5 robustness FAIL are unaffected.",
     "remedy": "Delete or correct the '差两个量级' clause (e.g. '定性不符：多配置下中心横向拉应力缺失')."
    },
    {
     "id": "F4",
     "severity": "major",
     "blocking": false,
     "scope": "§2 method item 7 (negative control) vs §3.6 measured result",
     "finding": "The method text says the 200-random-θ control 'verifies that random parameters can hardly land in the literature band', but the measured violation ratio is 83.5%, i.e. 33/200 ≈ 16.5% (about one in six) random parameter sets DO land in [5,15] MPa. That is the opposite of 'almost impossible' and is precisely why AC6 is recorded FAIL.",
     "evidence_locator": {
      "start_char": 3982,
      "end_char": 4022,
      "start_line": 62,
      "quote": "200 组随机 θ 只跑 UCS（AC6，验证“随机参数几乎不可能落进文献带”）"
     },
     "result_locator": {
      "start_char": 1257,
      "end_char": 1293,
      "start_line": 16,
      "quote": "违反比例 83.5%（n = 200；UCS 中位 2.546 MPa）"
     },
     "reproduction": "verify_wp-11930-04.py N6.1: 167/200=83.5% ⇒ 33/200=16.5% inside band; N6.2.",
     "impact": "The FAIL is honestly recorded, but the method paragraph overstates the control's strength; downstream readers may cite the control as evidence the band is discriminative, which it is not.",
     "remedy": "Rewrite §2 item 7 to 'quantifies how often random θ lands in the band (16.5%, n=200) — the control FAILED its ≥95% target'."
    },
    {
     "id": "F5",
     "severity": "minor",
     "blocking": false,
     "scope": "§0/§3.1 AC1 UCS aspect-ratio sub-item",
     "finding": "H/D=2.000 mixes endpoints: H=0.2 m is the gauge (8 lattice spacings, centre-to-centre of the driven end layers) while D=0.1 m is the bounding-box diameter (3 spacings + 2 radii). Under uniform conventions the same lattice gives H/D=2.25 (extent/extent, still inside ASTM [1.5,2.5]) or 2.667 (centre-to-centre/centre-to-centre, outside the band). The convention is not stated, so the AC1 PASS is convention-dependent.",
     "evidence_locator": {
      "start_char": 4095,
      "end_char": 4152,
      "start_line": 68,
      "quote": "UCS 试件：H/D = 2.000（ASTM D7012 带 [1.5, 2.5]）→ PASS，颗粒数 144"
     },
     "reproduction": "verify_wp-11930-04.py N1.1/N1.2 (D=3·0.025+2·0.0125=0.1; H_gauge=8·0.025=0.2; H_extent=0.225).",
     "impact": "Verdict survives under the physical convention (2.25 ∈ [1.5,2.5]) but not under a pure centre-to-centre convention (2.667).",
     "remedy": "State the convention explicitly and report both numbers (physical 2.25, gauge/D 2.00)."
    },
    {
     "id": "F6",
     "severity": "minor",
     "blocking": false,
     "scope": "§3.3/§3.4 numbers that cannot be re-derived from the report text",
     "finding": "The fitted-thickness tensile strengths (t=0.1/0.2/0.4, the fit inputs) are never printed, so the published σc/σt=2.688 and m=262.976 cannot be recomputed from the report alone; only the two holdout predictions are reproducible from the published (m, σ_ref). The three-target feasibility matrix (AC3) therefore contains one number (2.688) with no in-report derivation.",
     "evidence_locator": {
      "start_char": 7182,
      "end_char": 7268,
      "start_line": 144,
      "quote": "拟合得到 m = 262.976（bootstrap 95% CI [24.916, 746.453]，CI 宽度 721.537），σ_ref = 3.71e+05 Pa"
     },
     "recomputed_locator": {
      "start_char": 792,
      "end_char": 945,
      "start_line": 13,
      "quote": "| AC3 三分支可行性 | (a)/(b)/(c) 之一 + 证据 | 参考 θ 落 **分支 (c)**：UCS 1.010 MPa、σc/σt 2.688、m CI [24.916, 746.453] （伪真值 6.000）；33 个设计点分支计数 a/b/c = 0/0/33 | 见 §3.3 |"
     },
     "reproduction": "verify_wp-11930-04.py N3.1/N3.2 reproduce 0.3753 MPa and 0.3713 MPa at t=0.05/0.80 from (m, σ_ref); N8.1 records the missing fit inputs.",
     "impact": "Fidelity of the holdout chain recomputes clean; the ratio target's provenance is not.",
     "remedy": "Add the five-thickness σ_t table (fit inputs + repeats) to §3.4."
    },
    {
     "id": "F7",
     "severity": "informational",
     "blocking": false,
     "scope": "§0/§3.6 AC7 reproducibility",
     "finding": "'relative difference 0.000' is asserted from two values printed to three significant figures (1.01e+06 Pa each); the displayed evidence cannot support an exact-zero claim (it only bounds the difference by ~1e-3 relative).",
     "evidence_locator": {
      "start_char": 8761,
      "end_char": 8814,
      "start_line": 180,
      "quote": "两次独立进程 UCS = 1.01e+06 / 1.01e+06 Pa，相对差 0.000（门 1e-3）"
     },
     "reproduction": "Reading of the published precision; not a numerical contradiction.",
     "impact": "Cosmetic, and the gate (1e-3) is comfortably met either way.",
     "remedy": "Print at least 6 significant figures (or raw Pa integers) for the two runs."
    },
    {
     "id": "F8",
     "severity": "informational",
     "blocking": false,
     "scope": "review limitation inherited from upstream wp-11930-01",
     "finding": "7/14 registered assets (module, 3 scripts, test suite, records.jsonl, artifacts report.json) are referenced_unresolved and live only in the TensorDEM checkout; 1 is declared absent. The 42-test suite, the 747-task campaign, the NSGA-II run and the KE/work gate therefore cannot be re-executed from this repo — they are reviewed for internal consistency only.",
     "evidence_locator": null,
     "reproduction": "docs/kf/wp-11930-01 asset_manifest counts.by_resolution {referenced_unresolved:7, resolved_in_source:6, declared_absent:1} (recomputed in R3.1).",
     "impact": "Sets the ceiling of this review: no independent reproduction of DEM physics.",
     "remedy": "None on the reviewer side; the upstream registration is correct to declare these unresolved."
    },
    {
     "id": "F9",
     "severity": "informational",
     "blocking": false,
     "scope": "§3.3 proxy accuracy table → use of the Pareto front as AC3 evidence",
     "finding": "The quadratic surrogate for m has LOO R²=0.0904 (in-sample 0.8092), i.e. essentially no out-of-sample predictive power. The report discloses this and states the (c) branch rests on DEM design points plus the proxy only as direction evidence; downstream consumers must not quote frontier m values as calibrated.",
     "evidence_locator": {
      "start_char": 6590,
      "end_char": 6636,
      "start_line": 127,
      "quote": "| m | 0.8092 | 0.0904 | 0.5689 | 26/28 | n/a |"
     },
     "reproduction": "Reported table read verbatim; not re-runnable (surrogate data absent).",
     "impact": "Consistent with the report's own caveat (§4 item 7) — recorded so the caveat is not lost downstream.",
     "remedy": "None required; keep the caveat in any derived KO."
    },
    {
     "id": "F10",
     "severity": "minor",
     "blocking": false,
     "scope": "§0 acceptance table, AC3 row",
     "finding": "The AC3 verdict cell reads '见 §3.3' instead of PASS/FAIL, breaking the table's own per-AC verdict format. The content of §3.3 (branch (c) with evidence) satisfies AC3's stated criterion, so the intended verdict is PASS but is never stated.",
     "evidence_locator": {
      "start_char": 792,
      "end_char": 945,
      "start_line": 13,
      "quote": "| AC3 三分支可行性 | (a)/(b)/(c) 之一 + 证据 | 参考 θ 落 **分支 (c)**：UCS 1.010 MPa、σc/σt 2.688、m CI [24.916, 746.453] （伪真值 6.000）；33 个设计点分支计数 a/b/c = 0/0/33 | 见 §3.3 |"
     },
     "reproduction": "Direct read of the §0 table.",
     "impact": "Audit-traceability only.",
     "remedy": "Write 'PASS（分支 (c) + 证据）' in the AC3 verdict cell."
    }
   ],
   "overstated_claims": [
    {
     "claim": {
      "start_char": 3982,
      "end_char": 4022,
      "start_line": 62,
      "quote": "200 组随机 θ 只跑 UCS（AC6，验证“随机参数几乎不可能落进文献带”）"
     },
     "problem": "negative control described as showing random θ 'almost never' lands in the band; measured 16.5% do (AC6 itself FAILs)"
    },
    {
     "claim": {
      "start_char": 12040,
      "end_char": 12112,
      "start_line": 233,
      "quote": "| 巴西中心主应力比 | Hondros −3.0（解析）| 最优 -2.705（相对 9.8%）| 否（差两个量级，honest FAIL）|"
     },
     "problem": "'差两个量级' contradicts the 9.8% in the same cell"
    },
    {
     "claim": {
      "start_char": 7269,
      "end_char": 7312,
      "start_line": 144,
      "quote": "端点局部 m：t=0.05 → 0.080、t=0.8 → 0.045，方向一致性 是"
     },
     "problem": "'局部 m' values 0.080/0.045 are 1/m-like, not moduli comparable to m=262.976"
    },
    {
     "claim": {
      "start_char": 8761,
      "end_char": 8814,
      "start_line": 180,
      "quote": "两次独立进程 UCS = 1.01e+06 / 1.01e+06 Pa，相对差 0.000（门 1e-3）"
     },
     "problem": "'相对差 0.000' exceeds the displayed 3-significant-figure precision"
    },
    {
     "claim": {
      "start_char": 4095,
      "end_char": 4152,
      "start_line": 68,
      "quote": "UCS 试件：H/D = 2.000（ASTM D7012 带 [1.5, 2.5]）→ PASS，颗粒数 144"
     },
     "problem": "H/D=2.000 mixes gauge H with bounding-box D; uniform conventions give 2.25 or 2.667"
    },
    {
     "claim": {
      "start_char": 792,
      "end_char": 945,
      "start_line": 13,
      "quote": "| AC3 三分支可行性 | (a)/(b)/(c) 之一 + 证据 | 参考 θ 落 **分支 (c)**：UCS 1.010 MPa、σc/σt 2.688、m CI [24.916, 746.453] （伪真值 6.000）；33 个设计点分支计数 a/b/c = 0/0/33 | 见 §3.3 |"
     },
     "problem": "AC3 verdict cell gives no PASS/FAIL"
    }
   ],
   "disposition": {
    "decision": "request-changes",
    "label": "needs-fix",
    "blocking_issues": [],
    "rationale": "No finding invalidates the report's core conclusions (structural under-determination rank 3/6 with a 3-dim null space; branch (c) infeasibility; honest FAILs on AC5 robustness, AC6, AC7 quasi-static gate). All recomputable headline numbers reproduce. Seven corrections are required before the report is quoted downstream (major: F1 Brun index, F2 'local m' label, F4 negative-control narrative; minor: F3 wording, F5 UCS H/D convention, F6 unpublished fit inputs, F10 AC3 verdict cell); nothing warrants fail/reject. Upstream package wp-11930-01 passes every reviewer-side check.",
    "not_marked_verified": "This review does not mark any claim as verified; it records reviewer-side checks only."
   },
   "repro_cmd": "bash work/wp-11930-04/repro.sh"
  },
  "review_events.json": [
   {
    "id": "tkr:package:wp-11930-01",
    "object_ref": "tensor://packages/wp-11930-01",
    "object_version": "sha256:52fa73beb02091ae628a19f5898a3c67031286d9f31c556713c65963317dc230",
    "decision": "approve",
    "reviewer": {
     "id": "agent/m19840",
     "reviewer_type": "agent",
     "role": "red-team-reviewer"
    },
    "reviewed_at": "2026-11-12T04:20:00+00:00",
    "policy_version": "kf-review/v1.0",
    "rationale": "Asset registration recomputed from fresh bytes: hash/chars/bytes match contract, 14/14 locator spans exact and unique, counts recomputed, 6/6 figure assets return HTTP 200 image/png with manifest-matching sha256 and byte counts.",
    "findings": [
     {
      "severity": "informational",
      "finding": "7/14 assets are referenced_unresolved and 1 declared_absent — correct declarations; they cap what an independent review can re-execute."
     }
    ]
   },
   {
    "id": "tkr:report:11930",
    "object_ref": "tensor://reports/11930",
    "object_version": "sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325",
    "decision": "request-changes",
    "reviewer": {
     "id": "agent/m19840",
     "reviewer_type": "agent",
     "role": "red-team-reviewer"
    },
    "reviewed_at": "2026-11-12T04:20:00+00:00",
    "policy_version": "kf-review/v1.0",
    "rationale": "Semantic fidelity: all recomputable headline numbers reproduce and the honest FAILs are internally consistent, but the Brun index is unreproducible as published, the 'local m' column is mislabelled by 3 orders of magnitude, the AC5 error row contradicts itself, the AC6 negative-control narrative overstates an 83.5% result, the UCS H/D mixes conventions, and the AC3 verdict cell omits PASS/FAIL.",
    "findings": [
     {
      "severity": "major",
      "finding": "F1: Published γ=6.71 for pair ['k_c','k_p'] is not reproducible from the published correlation ρ=0.978 under either standard definition: Brun γ=1/√(1−R²)=4.796, Belsley 2-column index √((1+ρ)/(1−ρ))=9.486. Only the non-standard 1/√(1−ρ)=6.745 lands near 6.71, which suggests a missing square / undeclared formula. The report never states the γ formula, so the 'worst pair' ranking is not independently auditable."
     },
     {
      "severity": "major",
      "finding": "F2: The '局部 m' column reports 0.080 (t=0.05) and 0.045 (t=0.80), i.e. 3–4 orders of magnitude below the global m=262.976 fitted in the same paragraph. If read literally as Weibull moduli, the local values contradict the global fit and would falsify AC4; the numbers are only consistent with the local exponent 1/m (→ m≈12.5 / 22.2). The label/quantity is wrong or at least ambiguous, while AC4 PASS hinges on 'end m direction consistency'."
     },
     {
      "severity": "minor",
      "finding": "F3: The same row states a 9.8% relative difference and then qualifies it as '差两个量级' (two orders of magnitude). 9.8% (and even the worst configuration, 788%) is not a two-order-of-magnitude gap; the qualitative clause contradicts the quantitative cell it annotates."
     },
     {
      "severity": "major",
      "finding": "F4: The method text says the 200-random-θ control 'verifies that random parameters can hardly land in the literature band', but the measured violation ratio is 83.5%, i.e. 33/200 ≈ 16.5% (about one in six) random parameter sets DO land in [5,15] MPa. That is the opposite of 'almost impossible' and is precisely why AC6 is recorded FAIL."
     },
     {
      "severity": "minor",
      "finding": "F5: H/D=2.000 mixes endpoints: H=0.2 m is the gauge (8 lattice spacings, centre-to-centre of the driven end layers) while D=0.1 m is the bounding-box diameter (3 spacings + 2 radii). Under uniform conventions the same lattice gives H/D=2.25 (extent/extent, still inside ASTM [1.5,2.5]) or 2.667 (centre-to-centre/centre-to-centre, outside the band). The convention is not stated, so the AC1 PASS is convention-dependent."
     },
     {
      "severity": "minor",
      "finding": "F6: The fitted-thickness tensile strengths (t=0.1/0.2/0.4, the fit inputs) are never printed, so the published σc/σt=2.688 and m=262.976 cannot be recomputed from the report alone; only the two holdout predictions are reproducible from the published (m, σ_ref). The three-target feasibility matrix (AC3) therefore contains one number (2.688) with no in-report derivation."
     },
     {
      "severity": "informational",
      "finding": "F7: 'relative difference 0.000' is asserted from two values printed to three significant figures (1.01e+06 Pa each); the displayed evidence cannot support an exact-zero claim (it only bounds the difference by ~1e-3 relative)."
     },
     {
      "severity": "informational",
      "finding": "F8: 7/14 registered assets (module, 3 scripts, test suite, records.jsonl, artifacts report.json) are referenced_unresolved and live only in the TensorDEM checkout; 1 is declared absent. The 42-test suite, the 747-task campaign, the NSGA-II run and the KE/work gate therefore cannot be re-executed from this repo — they are reviewed for internal consistency only."
     },
     {
      "severity": "informational",
      "finding": "F9: The quadratic surrogate for m has LOO R²=0.0904 (in-sample 0.8092), i.e. essentially no out-of-sample predictive power. The report discloses this and states the (c) branch rests on DEM design points plus the proxy only as direction evidence; downstream consumers must not quote frontier m values as calibrated."
     },
     {
      "severity": "minor",
      "finding": "F10: The AC3 verdict cell reads '见 §3.3' instead of PASS/FAIL, breaking the table's own per-AC verdict format. The content of §3.3 (branch (c) with evidence) satisfies AC3's stated criterion, so the intended verdict is PASS but is never stated."
     }
    ]
   }
  ]
 }
}
```
