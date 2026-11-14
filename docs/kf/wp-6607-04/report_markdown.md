# wp-6607-04 — 报告 6607 的独立复核（pass-with-notes）

**一句话**：报告的数字全部可由它自己印出的输入重算，没有捏造；但有 3 条 medium 级的表述/口径缺陷（两臂一致性被低估 1.3–3.2 倍、淬火臂 nu 印成扫描上界、判据 c 写出≠执行），均不改变任何 PASS/FAIL 结论 → **approve with notes**。

## 1 复核对象与源钉扎

| 项 | 值 |
|---|---|
| 报告 | `6607` — jamming 体积分数重锁：FIRE/CG 能量极小 + 双周期 + 有限尺寸标度（IN32-N02） |
| 场景键 | `dem-granular-jamming` |
| 源字段 / 哈希 | `markdown` / `sha256:b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1` |
| 字符 / 行 | 7642 / 136 |
| 取回 | GET <TENSOR_API_BASE>/tensor/reports/6607 (auth: platform login)（2026-11-14T21:08:38+00:00） |
| 复核包 | `wp-6607-04`（工序 04-independent-review） |

快照 `source_6607.md` 与取回 markdown 逐字节相等（sha256 同上）。改一个字符，本包所有结论失效、`--offline` 重建立即 `PIN MISMATCH`。

## 2 怎么做的（方法与独立性边界）

1. 只审 markdown 字节：从第 3 节的 4 dp 均值表、phi_J(∞) 汇总行、判据表的 measured JSON、第 6 节误差表**程序化解析**出输入（`parse_phi_table` 与逐行正则），不手抄任何 φ_J。
2. 复算三件事：算术恒等式（差值/百分比/阈值比较）、有限尺寸标度拟合（变量投影 + 一维 ν 扫描）、以及「判据写出的口径 vs 实际可执行的检查」。
3. 判定与复算分离：判定行（`status=fail`）只在**印出的数与自己印出的断言矛盾**时触发；上游执行层缺失一律 `NOT_RUN`/`WITHHELD`，不按「没发现问题」算通过。
4. 负对照：判据 g 的 R²>0.98 一支用 200 组随机漂移假数据检验（R12），判据 b 的负对照用 √2·1e-3 反推（R23）。

## 3 复算台账（42 条）

| id | 种类 | 复算式 | 复算值 | 报告值 | 相对差% | 状态 |
|---|---|---|---|---|---|---|
| `T1_PHI_TABLE_PARSE` | derived | parse the chapter-3 mean±s.e.m. table: 5 N-rows x 4 protocol columns | 5 rows x 4 protocols | — | — | **derived** |
| `R1_GROWTH_MONOTONE` | invariant | all(phi[N_{i+1}] > phi[N_i]) for N=256..4096 | true | 单调 | — | **pass** |
| `R1_DECOMPRESSION_MONOTONE` | invariant | all(phi[N_{i+1}] > phi[N_i]) for N=256..4096 | true | 单调 | — | **pass** |
| `R3_GROWTH_16X` | arithmetic | phi(N=4096) - phi(N=256) | 0.0036 | 0.0036 | -1.76e-12 | **pass** |
| `R3_DECOMPRESSION_16X` | arithmetic | phi(N=4096) - phi(N=256) | 0.0040 | 0.0040 | 8.67e-14 | **pass** |
| `R5_QUASI_GAP_PER_N` | invariant | max_N \|phi_decompression(N) - phi_growth(N)\| | 0.0020 | 0.0015 | 33.3 | **fail** |
| `R6_QUASI_GAP_AT_PHI_INF` | arithmetic | phi_inf(decompression) - phi_inf(growth), both as printed on the phi_J(inf) row | 0.0034 | 0.0015 | 127 | **fail** |
| `R7_QUASI_PLATEAU_SPREAD` | invariant | max over the quasi-static protocols of (max - min) phi for N in {1024,2048,4096} | 0.0016 | 0.0005 | 220 | **fail** |
| `R8_FIT_PHI_INF_GROWTH` | fit | phi(N) = phi_inf - c N^(-1/(2 nu)), variable projection over nu, 5 points | 0.845437 | 0.8454 | 0.0044 | **pass** |
| `R9_FIT_NU_GROWTH` | fit | nu at the SSR minimum of the same fit | 1.1975 | 1.21 | -1.04 | **pass** |
| `R10_NU_PROFILE_WIDTH` | derived | nu range where SSR(nu) <= k*SSR_min, growth column | SSR<=1.05x: nu in [1.03, 1.43] ; SSR<=1.50x: nu in [0.78, 2.42] ; SSR<=4.00x: nu in [0.49, 6.00] | — | — | **derived** |
| `R11_FIT_R2_GROWTH` | fit | R2 = 1 - SSR/SST of the same 5-point fit | 0.987771 | 0.990 | -0.225 | **pass** |
| `R12_R2_ARM_NULL_CONTROL` | negative_control | share of 200 seeded monotone decoys (0.84 + 1e-3*j + 2e-3*U) whose 5-point FSS fit gives R2 > 0.98 | 32/200 monotone decoys, 3/200 pure-noise decoys | — | — | **derived** |
| `R13_FIT_PHI_INF_DECOMP` | fit | same fit on the decompression column | 0.848981 | 0.8488 | 0.0214 | **pass** |
| `R14_CRIT_C_LITERAL_WINDOW` | criterion_execution | criterion c executed literally: fit on N>=2048 only (3 points, 3 parameters => exact interpolation, so phi_inf is defined only once nu is fixed; read off over nu in [0.5, 1.5]) | growth phi_inf in [0.8449, 0.8475]; decompression in [0.8459, 0.8470] | 0.8454 | — | **fail** |
| `R15_CRIT_C_BAND_GROWTH` | criterion_execution | \|phi_inf - 0.84\| <= 0.01 | true | PASS | — | **pass** |
| `R15_CRIT_C_BAND_DECOMPRESSION` | criterion_execution | \|phi_inf - 0.84\| <= 0.01 | true | PASS | — | **pass** |
| `R16_CRIT_E_MAX_MINUS_MIN` | arithmetic | max_p phi_inf(p) - min_p phi_inf(p) over the four protocols | 0.090100 | 0.090096 | 0.0041 | **pass** |
| `R17_CRIT_F_THRESHOLD` | criterion_execution | max_seed_dispersion_percent <= 1 % | 1.2382% | 1 | — | **pass** |
| `R18_CRIT_D_NULL` | criterion_execution | measured phi_inf(mu=0.5) is null => criterion d cannot be PASS | null | FAIL | — | **pass** |
| `R19_CRITERIA_TALLY` | arithmetic | count PASS/FAIL in the nine-row criterion table | 6 PASS / 3 FAIL of 9 | 6 条通过 | — | **pass** |
| `R20_FIRE_REDUCTION` | consistency | eps0/eps and fmax0/fmax vs the printed fmax_reduction; reduction must also be >= 1e6 | 5.666760e+11 | 5.666760e+11 | 0 | **pass** |
| `R21_FIRE_DIMENSIONLESS_IDENTITY` | consistency | r_bar/E0 implied by (eps0, fmax0) must equal the one implied by (eps, fmax) | 0.045855870941923 | 0.045855870941923 | 0 | **pass** |
| `R22_VIRIAL_THRESHOLDS` | criterion_execution | virial_identity_rel < 1e-10 and stress_symmetry_rel < 1e-12 | 1.849870483311284e-11 < 1e-10 and 7.83612936479418e-18 < 1e-12 | PASS | — | **pass** |
| `R23_NEG_CONTROL_SQRT2` | consistency | negative_control_without_image_rel vs 1e-3*sqrt(2) (1e-3\|\|W\|\| broken in two components) | 1.4142135623731e-03 | 0.0014142135579266247 | 3.14e-07 | **pass** |
| `R24_RESIDUAL_LINEARITY` | arithmetic | log10(1.06e-4 / 1.85e-11) / log10(1e-6 / 1e-13)   (1.0 = strictly linear in epsilon) | 0.9654 | 线性 | — | **pass** |
| `R25_QUENCH_NU_IS_SCAN_CAP` | fit | R2(nu) of the FSS form on the two quench columns at nu = 2.51, 4, 6, 8 | rsa_direct R2(2.51)=0.7360 -> R2(8)=0.7798 ; fire_from_rsa R2(2.51)=0.8416 -> R2(8)=0.8779 | 2.51 | — | **fail** |
| `R26_RSA_DIRECT_MONOTONE` | invariant | all(phi[N_{i+1}] < phi[N_i]) on the rsa_direct column | false | 下降 | — | **fail** |
| `R27_1_SEC6_ROW` | arithmetic | 100*(work - base)/base computed from the error-table row itself, then check the printed <3% column | +0.64% | +0.64% | 0.643 | **pass** |
| `R27_2_SEC6_ROW` | arithmetic | 100*(work - base)/base computed from the error-table row itself, then check the printed <3% column | +1.05% | +1.05% | 1.05 | **pass** |
| `R27_3_SEC6_ROW` | arithmetic | 100*(work - base)/base computed from the error-table row itself, then check the printed <3% column | +0.48% | +0.48% | 0.476 | **pass** |
| `R27_4_SEC6_ROW` | arithmetic | 100*(work - base)/base computed from the error-table row itself, then check the printed <3% column | +5.25% | +5.2% | 5.25 | **pass** |
| `R27_5_VIRIAL` | arithmetic | 100*(work - base)/base computed from the error-table row itself, then check the printed <3% column | 1.850e-11 | 绝对值 | — | **pass** |
| `R27_6_SEC6_ROW` | arithmetic | 100*(work - base)/base computed from the error-table row itself, then check the printed <3% column | -5.92% | −5.9% | -5.92 | **pass** |
| `R28_SEC6_HONESTY_TALLY` | invariant | count of error-table rows whose <3% column agrees with \|recomputed error\| < 3% | 6/6 consistent | — | — | **pass** |
| `N1_ACCEPTED_STEP_FRACTION` | not_recomputable | share of accepted FIRE steps that raised max\|F\| (reported 47%) | — | 47 | — | **not_recomputable** |
| `N2_MAX_RELATIVE_INCREASE` | not_recomputable | max_relative_increase of max\|F\| on accepted steps (printed 0.94, called 微小抬升) | — | 0.94 | — | **not_recomputable** |
| `N3_UPSTREAM_ARTIFACTS` | not_recomputable | TensorDEM run artifacts (artifacts/jamming_protocol/jamming_protocol.json, benchmarks/jamming_*.py, src/tensordem/granular2d/minimizer.py) | — | — | — | **not_recomputable** |
| `N4_PYTEST_COUNTS` | not_recomputable | pytest count claimed by criterion i (29 test functions / 5 negative controls) | — | 29 | — | **not_recomputable** |
| `N5_LITERATURE_ANCHOR` | withheld | literature anchor phi_J = 0.84 +- 0.01 (O'Hern, Langer, Liu & Nagel, PRL 91, 075501 (2003)) | — | 0.84 | — | **withheld** |
| `N6_FLOOR_BAND` | not_recomputable | phi_j_floor_band = 0.0017-0.0026 (P(phi) extrapolation floor sensitivity, growth arm) | — | 0.0017 | — | **not_recomputable** |
| `N7_FIGURE_BYTES` | withheld | report figures pressure_vs_phi.png / phi_j_vs_N.png / residual_history.png | — | — | — | **withheld** |

状态口径：`pass` 复算与印出一致；`fail` 印出的断言/参数被自己的数（或口径）否证；`derived` 复核方派生、无对应印刷值；`not_recomputable`/`withheld` 需上游产物或缺文献。

## 4 判据逐项执行核对

| 判据 | 名称 | 报告判定 | 复核入口 | 复核读数 |
|---|---|---|---|---|
| a | fire_convergence | PASS | `R20_FIRE_REDUCTION` | 数值自洽；逐帧执行未重放（N1/N3） |
| b | double_periodic_virial | PASS | `R22_VIRIAL_THRESHOLDS` | 阈值比较与负对照自洽；引擎复算未重放（N3） |
| c | frictionless_phi_j_infinite | PASS | `R14_CRIT_C_LITERAL_WINDOW` | 写出的口径不可识别（F3）；两支外推仍在锚窗内 |
| d | frictional_phi_j | FAIL | `R18_CRIT_D_NULL` | measured=null -> FAIL 自洽；摩擦臂未交付 |
| e | protocol_independence | FAIL | `R16_CRIT_E_MAX_MINUS_MIN` | 0.0901 与印出一致；「只差 0.0015」被 R6 更正（F1） |
| f | seed_sensitivity | FAIL | `R17_CRIT_F_THRESHOLD` | 1.2382% vs 1% 阈值复算一致 |
| g | finite_size_scaling | PASS | `R8_FIT_PHI_INF_GROWTH` | 拟合复现；R2>0.98 一支鉴别力弱（R12 假数据 16%% 也能过），nu 一支有效 |
| h | m5079_comparison | PASS | `N3_UPSTREAM_ARTIFACTS` | 印刷的 m5079 压力列 9 行与 measured.n_rows=9 一致；压力值本身需上游（N3） |
| i | tests_with_negative_controls | PASS | `N4_PYTEST_COUNTS` | 用例数按自述登记；未执行（N4） |

## 5 发现（按 severity）

### F1 · medium · 三处「两臂一致 / 稳定」的印出量都低估了 1.3–3.2 倍，其中 0.0015 被自己的表否证

- 类别：`overstated_claim`；复算：`R5_QUASI_GAP_PER_N`, `R6_QUASI_GAP_AT_PHI_INF`, `R7_QUASI_PLATEAU_SPREAD`
- 原文（第 46 行）：`两条曲线在每个 N 上的差 ≤ 0.0015，种子离散 0.12–0.31%。`
- 观测：同一张表里两条准静态臂的最大逐 N 差是 0.0020（N=2048），外推值差 0.0034，N>=1024 平台段展宽 1.3e-3 / 1.6e-3 —— 相对 0.0015 / 0.0015 / 5e-4 分别是 1.3x / 2.3x / 3.2x
- 应为：三句应改成它们自己的数字：逐 N <= 0.0020、外推差 0.0034、平台段 1.6e-3
- 对判定影响：none（判据 e 的 FAIL、以及「失败定位在淬火臂」这一定性都不变：0.0034 远小于 0.01，更远小于 0.0901）
- 建议修复：把三处改写为可复算的印刷值，或统一改述为「准静态臂分歧 <= 0.0034（判据容差的 34%）」

### F2 · medium · 两条淬火臂的 nu=2.51 是拟合扫描的上界，被当成估计值印出（且未标注该臂不适用 FSS）

- 类别：`parameter_at_boundary`；复算：`R25_QUENCH_NU_IS_SCAN_CAP`
- 原文（第 43 行）：`| **φ_J(∞)** | 0.8454 (ν=1.21, R²=0.990) | 0.8488 (ν=1.65, R²=0.993) | 0.8165 (ν=2.51, R²=0.724) | 0.7587 (ν=2.51, R²=0.834) |`
- 观测：rsa_direct R2(2.51)=0.7360 -> R2(8)=0.7798 ; fire_from_rsa R2(2.51)=0.8416 -> R2(8)=0.8779：两条不同曲线的 R2 在 nu 增大方向仍在上升，且两者印出同一个 nu=2.51
- 应为：若扫描上界是 2.5，应印成 nu >= 2.51（截断）或直接印 n/a：报告第 3 节自己说这两臂未落到能量极小态，FSS 形式对它们没有物理含义
- 对判定影响：none（判据 g 只约束准静态臂的 nu，2.51 不参与任何 PASS/FAIL）
- 建议修复：淬火臂一栏的拟合参数标为 n/a（非能量极小态）或注明扫描上界；判据 g 保持只对 growth/decompression 生效

### F3 · medium · 判据 c 写出的口径（N>=2048）不可识别，实际执行的是 5 点全窗拟合

- 类别：`criterion_not_executed`；复算：`R14_CRIT_C_LITERAL_WINDOW`, `R15_CRIT_C_BAND_GROWTH`, `R15_CRIT_C_BAND_DECOMPRESSION`
- 原文（第 82 行）：`| c_frictionless_phi_j_infinite | phi_J(N->inf) from N>=2048 must lie in 0.84 +- 0.01 |`
- 观测：growth phi_inf in [0.8449, 0.8475]; decompression in [0.8459, 0.8470]（3 点 3 参被精确穿过，phi_inf 随 nu 漂移）
- 应为：报告印出的 0.8454 只能由 N=256..4096 的 5 点拟合得到；写出的口径与实际口径不一致
- 对判定影响：none（两支外推都落在 0.84±0.01 内，且 R14 的整个区间 0.8449–0.8475 仍在内）
- 建议修复：判据 c 改写为「5 点（N=256..4096）FSS 外推落在 0.84±0.01 内」，或对 N>=2048 只做「不外推、直接比较 N=4096 值 0.8440」的检查

### F4 · low · 「phi_J 随 N 下降」对 rsa_direct 不成立（N=512 处微升）

- 类别：`imprecise_statement`；复算：`R26_RSA_DIRECT_MONOTONE`
- 原文（第 47 行）：`两个瞬时淬火臂则相反：φ_J 随 N **下降**（0.8377 → 0.8280 / 0.7995）`
- 观测：rsa_direct: 0.8377, 0.8378, 0.8377, 0.8317, 0.8280 —— 只在 N>=1024 后单调
- 应为：「N>=1024 之后随 N 下降」；fire_from_rsa 才是严格单调
- 对判定影响：none
- 建议修复：把该句限定到 N>=1024 或指明只有 fire_from_rsa 严格单调

### F5 · low · 「最大相对抬升 0.94」被称作「微小抬升」，与字面值 94% 自相矛盾且归一定义缺失

- 类别：`undefined_metric`；复算：`N1_ACCEPTED_STEP_FRACTION`, `N2_MAX_RELATIVE_INCREASE`
- 原文（第 93 行）：`接受步有微小抬升（最大相对抬升 0.94）`
- 观测：max_relative_increase = 0.94（无单位说明）；若为相对量即 94% 的抬升
- 应为：印出该量的定义与归一化（例如 |F| 的增量相对 eps 容差，或相对该步初值）
- 对判定影响：none（判据 a 的 PASS 走的是包络口径，报告已声明逐帧严格口径未达成）
- 建议修复：给出 max_relative_increase 的公式与单位；若确为 94%，删去「微小」

### F6 · low · 泄压臂的锚窗 PASS 只剩 12% 余量，与报告自述的外推地板敏感性同量级，但未传播进判据

- 类别：`sensitivity_not_propagated`；复算：`R15_CRIT_C_BAND_GROWTH`, `R15_CRIT_C_BAND_DECOMPRESSION`, `N6_FLOOR_BAND`
- 原文（第 82 行）：`| c_frictionless_phi_j_infinite | phi_J(N->inf) from N>=2048 must lie in 0.84 +- 0.01 |`
- 观测：growth 偏差 0.0054（容差的 54%），decompression 偏差 0.0088（容差的 88%，余量 0.0012）；而 5.7 自述 P(phi) 外推地板带是 0.0017–0.0026
- 应为：判据 c 的 PASS 应带上「外推方法系统不确定度 0.002 量级」的注记，或给出把地板带传播进来之后的区间结论
- 对判定影响：none（growth 臂余量充足；两臂同向偏高，不改变 PASS 但改变可信度的表述）
- 建议修复：在判据 c 行加一条「±0.002 外推系统项」并说明它不改变判定

## 6 未执行 / 不可复算（不按通过计）

| 检查 | 状态 | 原因 | 影响 |
|---|---|---|---|
| 上游 TensorDEM 执行层（判据 a/b/e/f/h/i 的运行记录） | NOT_RUN | 报告引用的 artifacts/jamming_protocol/jamming_protocol.json、benchmarks/jamming_*.py、src/tensordem/granular2d/minimizer.py 在 TensorKnowledge 仓内不存在（跨仓路径）。 | 16 条断言里凡需要逐帧历史/原始 P(phi) 序列/压力曲线的，都只核对了「印出的数是否自洽」，没有重放执行；判据 a 的 47%、0.94 一律未复算。 |
| pytest 29 个用例 / 5 个负对照（判据 i） | NOT_RUN | tests/test_granular2d_energy_minimization.py 属 TensorDEM 仓。 | 判据 i 的 PASS 按报告自述登记，本包不构成执行证据。 |
| 报告图（pressure_vs_phi / phi_j_vs_N / residual_history）的图内数据 | WITHHELD | 平台报告记录只带图名与图注，无 PNG 字节。 | 图与表是否一致未核；本包只核表。 |
| 文献锚 0.84 ± 0.01（O'Hern et al., PRL 91, 075501 (2003)） | WITHHELD | 本仓库无该文献副本，复核方未独立取数。 | 所有「落在锚窗内」的判定沿用报告的锚值；锚若移动，判据 c 的读数随之移动。 |
| P(phi) 三点外推与地板敏感性（phi_j_floor_band） | NOT_RECONSTRUCTABLE | 只印出结论区间 0.0017–0.0026，未印出 P(phi) 序列与地板取值。 | F6 只能定性指出其量级与判据 c 的余量相当。 |

## 7 误差判定（关键量 vs 基准，是否 <3%）

| 量 | 基准 | 报告值 | 复算误差 | 报告是否 <3% | 复核判定 |
|---|---|---|---|---|---|
| `R27_1_SEC6_ROW` | 0.84（文献锚） | 0.8454 | +0.64% | **是** | pass |
| `R27_2_SEC6_ROW` | 0.84 | 0.8488 | +1.05% | **是** | pass |
| `R27_3_SEC6_ROW` | 0.84 | 0.8440 | +0.48% | **是** | pass |
| `R27_4_SEC6_ROW` | 4.0 | 4.21 | +5.25% | 否（有限尺寸/接触定义差异，见 §3.1） | pass |
| `R27_5_VIRIAL` | 0 | 1.85e-11 | absolute | **是** | pass |
| `R27_6_SEC6_ROW` | 0.84 | 0.7903 | -5.92% | 否（m5079 未通过；本节点正是重锁） | pass |

**显式回答「是否 <3%」**：3 行判「是」（无摩擦 φ_J(∞)（充气） +0.64%、无摩擦 φ_J(∞)（泄压） +1.05%、无摩擦 φ_J（N=4096 直接值） +0.48%）、2 行判「否」（配位数 z（φ=0.85，无摩擦等静定） +5.25%、m5079 的 φ_J（同体系、有壁、阻尼淬火） -5.92%），与复算逐行一致（`R28_SEC6_HONESTY_TALLY` = 6/6 consistent）——报告在误差栏没有粉饰。

## 8 结论与修复建议

- 判定 **pass-with-notes**，disposition **approve with notes**；blocking 发现 0 条；severity 分布 high=0 / medium=3 / low=3。
- 证据支持「数字未捏造」：`R8`/`R13` 复现外推值，`R20`/`R21` 证明 FIRE 四元组同源，`R28` 证明误差栏诚实。
- 建议按 F1–F6 改述后再归档；其中 F1/F2/F3 应在下一次修订中改，F4–F6 属措辞与注记。
- 本包**不自称已发布、不自称已验证**：`published.json` 由平台门在合并时写入，任务态保持 `awaiting_pr_merge` 直到合并（pr-gate 记账）。

## 9 复现

```bash
python3 scripts/kf/review_wp_6607_04.py --offline   # 由已提交快照重建全部工件
pytest -q tests/test_wp_6607_04_review.py          # 不变量 + 负对照
```

来源钉扎：`sha256:b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1`（7642 字符 / 136 行）。
