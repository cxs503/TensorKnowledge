KF-RESULT wp-11608-04

# KF-RESULT wp-11608-04

| 项 | 值 |
|---|---|
| package_id | `wp-11608-04` |
| 工序 | `04-independent-review`（lane C） |
| report_id | `11608` |
| scenario_key | `p73w3-n04-fvm-numerical-viscosity` |
| 源哈希 | `sha256:8a9602aca712ab3ac8656d7382e0fef762ba0f30657cf8b631b36ba514e8db62`（7342 字符，独立重算一致） |
| 审核对象 | 上游 `wp-11608-01`（01-asset-registration）+ 报告正文 |
| disposition | **needs-fix**（major 3 / medium 2 / minor 2 / info 1） |
| 本轮标 verified 的断言数 | 0（验证判定归平台门） |

---

## ① 本工序做了什么

对 report 11608（TensorFVM 数值黏性/色散算子验证面）做独立红队审核，判定 `pass / fail / needs-fix`。
做法上不复用生产者的任何代码或解释：从报告 §1.2 的四个格式定义、§2.2 的两条公式出发，**自行重实现**迎风 / Lax–Wendroff / CD2 / Leonx-QUICK
四个一维周期对流格式，重算六块判据（a–f）的数值，并用**负向对照（mutant stencil）**测量报告自己的阈值能查出多大的错误。

结论：**needs-fix**。四条物理结论（迎风 ν_th=cΔx(1-C)/2 成立；CD2 纯色散且 |G|>1；L–W 近乎无耗散；ν∝Δx）在独立重算下**依然成立**，
但 3/6 判据表的逐行数字不可复现、1 条印刷公式（QUICK 前阶黏性）被证伪、1 条区间（CD2 半周期增长）无任何枚举工况支撑：

- **R1 (major)** §3.1 的 9 行 ν_meas 与误差列不可复现：精确 von Neumann 偏差比报告列小 1.7–124.3 倍，且 3/9 行**偏差符号相反**（C=0.5 三行）。判据 (a) 的结论本身更强（独立重算最大偏差 0.16% < 1%）。
- **R2 (major)** §2.2 的 QUICK 公式 `ν_th=cΔx(1-C)(1-C²)/8` 不是 QUICK 的前阶黏性：由 Leonard 两点迎风插值自行推导为 `cΔx(5-4C)/8`，比报告公式大 5.5–25.0 倍，且**比一阶迎风还大**（1.3–2.25 倍）——报告"QUICK 小但非零"的定性判断被推翻。
- **R3 (major)** §3.3 的 L–W 残差黏性列标度为 O(θ)（理论 O(θ²)），C 依赖单调上升（理论峰值在 C=1/√3≈0.577），报告/独立值比 0.33–2.08；"小 1–2 个量级"实为 **5.6 倍裕度**。判据 (c) 的通过结论仍成立。
- **R4 (medium)** 判据 (b) 在 §2.3 写绝对阈值、§3.2 写相对阈值，两者不一致；相对式在迎风 C=0.5、θ=π（|G|=0）处**除零病态**；0.1% 系数误差的 mutant **仍通过** ±1e-3 绝对阈值；而可达一致度是 1e-15 量级，表格里的 1.5e-4–5.9e-4 无来源。
- **R5 (medium)** §3.4 的"A_ratio=1.15~1.35"仅 2/9 工况成立（独立重算区间 1.016–1.272，7/9 低于 1.15）。
- **R6 (minor)** §3.5 网格收敛结论复现（比值 0.4994/0.4998/0.5000 vs 报告 0.500/0.500/0.501），但表未声明每级 (C, kΔx)，且四舍五入掩盖了 §3.1 已可见的 +0.16% 有限 θ 偏差。
- **R7 (minor)** §7/§8 的 8 个工件路径、字节数、"57 passed"、commit 在本审核范围内**无法核验**（无 TensorFVM 检出）；末行 *报告工件路径* 与平台 `record.figures` 指向 hydroelasticity，主体污染（与上游 wp-11608-01 记录一致）。
- **R8 (info)** 报告头 `✅ 全部验收判据通过` 是结论级判断，行级证据不支持（3/6 表含不可复现行）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取源**：`GET /tensor/reports/11608` → `markdown`（psql 直读被权限拒绝，走 API），落盘字节级副本；独立重算 sha256 = 契约值，字符数 7342 一致。
2. **读上游**：只读 `docs/kf/wp-11608-01/asset_manifest.json` + `verification.json`（25 资产 / 5 resolved / 14 unresolved / 6 absent / off_topic 10）。
3. **重实现四格式**（c=1, Δx=1, 显式 Euler，周期域）：迎风、L–W、CD2、Leonard-QUICK（`u_{j+1/2}=3/4u_j+3/8u_{j-1}-1/8u_{j-2}`；报告未给 QUICK 模板，故同时记录替代插值的敏感性）。
4. **判据 (a)**：单模 `exp(ikx)` 推进 2 个波周期，`ν_meas=-ln(A/A0)/(k²t)`，kΔx=2πm/256（m=2,4,8），C∈{0.2,0.5,0.8} → 9 组；同时算闭式 `ν_exact=-ln|G|/(k²Δt)`。
5. **判据 (b)**：θ∈(0,π) 48 个严格内点：①stencil 作用于解析模 vs 闭式符号（一致性探针）；②**多步 march 反演 |G|**（63 个网格相容 θ × 4 格式 × 3 C）——非同一公式自证。
6. **负向对照**：迎风 C 乘 1.001、QUICK 3/4→0.74 的 mutant，测报告阈值分辨力；记录相对阈值在 |G|→0 的除零病例。
7. **判据 (c)/(d)/(e)**：L–W 9 组残差黏性与渐近律 `C(1-C²)θ²/8` 对比；CD2 `|G|` 与半周期增长逐工况；网格 4 级加密（固定物理模态 m=8，L=256）。
8. **QUICK 公式**：对自身符号求 κΔx→0 极限（θ=0.02, 0.01），与报告公式和自推公式比值。
9. **卫生探针**：工件/测试/commit 声明、hydroelasticity 主体污染、图像链接是否进入平台 figure 字段、清单算术（36=4×3×3）。
10. **工具链**：python 3.11.6 / numpy 2.4.6 / matplotlib 3.10.8 / jsonschema；单机全量重算约 4 s（<8 核、<10 min，故未递交集群）。

**阈值纪律**：全部阈值取报告自己写的判据（1% / 1e-3 / 1e-2·cΔx / 5%），未在看到结果后调整；报告未声明的参数（如 §3.5 的 C、kΔx）显式标注为假设 m=8、C=0.5。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 大小 | 要点 |
|---|---|---|
| `review_report.json` | 23.5 KB | 独立审核产物：8 条 finding、独立性声明、检查清单、disposition |
| `review_events.json` | 0.7 KB | 审核决策事件账本（5 条 seq） |
| `checks.json` | 22.4 KB | 独立重算的全部数字（零手抄，机器生成） |
| `kf_result.wp-11608-04.json` | 27.2 KB | 平台结果信封（provenance.source_hash = 契约哈希） |
| `independent_checks.py` | 19.1 KB | 独立重算脚本：4 格式重实现 + 6 判据块 + 4 个负向对照 |
| `build_review.py` | 34.9 KB | finding/图表构建器（引文定位程序化校验） |
| `make_kf_result.py` | 5.7 KB | 信封组装 + schema 校验 + 交付物 staging |
| `fig1_upwind_deviation.png` | 59.3 KB | 判据(a)：报告误差列 vs 独立重算（对数轴）+ 偏差符号 |
| `fig2_criterion_power.png` | 64.2 KB | 判据(b)：±1e-3 阈值对 0.1% 系数误差无分辨力 + 可达残差 |
| `fig3_quick_and_lw.png` | 115.1 KB | QUICK 前阶黏性公式证伪 + L-W θ 标度矛盾 |
| `fig4_cd2_and_grid.png` | 59.4 KB | CD2 半周期增长 vs 报告区间 + 网格收敛复现 |

图（matplotlib，全部数字由 `checks.json` 程序化注入）：

- `fig1_upwind_deviation.png`：判据 (a) 误差列 vs 独立重算（对数轴）+ 9 行偏差符号。
- `fig2_criterion_power.png`：±1e-3 阈值下 0.1% 系数误差不可分辨；可达残差 1e-15 vs 报告表格 1e-4。
- `fig3_quick_and_lw.png`：QUICK 前阶黏性（报告公式 vs 自推 (5-4C)/8 vs 迎风）+ L–W 标度矛盾。
- `fig4_cd2_and_grid.png`：CD2 半周期增长 vs 报告区间；网格收敛复现。

## ④ 证据定位表（claim/字段 → 原文逐字引文，含 char span）

| finding | 级别 | 原文逐字引文 | char span |
|---|---|---|---|
| R1 | major | **结论**: ✅ 全部 9 组合误差 < 1%，最大误差 0.50% | `[2131,2166)` L100 |
| R2 | major | QUICK: `ν_th = cΔx(1-C)(1-C²)/8` | `[1016,1048)` L56 |
| R3 | major | **结论**: ✅ ν_num 比阈值小 1-2 个量级，相位误差全部 < 1% | `[3287,3327)` L131 |
| R4 | medium | **判据**: \|G_num - G_ana\| / \|G_ana\| < 1e-3，全域 θ（49 点） | `[2204,2255)` L104 |
| R5 | medium | - **振幅增长**: 0.5 周期后，A_ratio = 1.15 ~ 1.35 | `[3531,3572)` L141 |
| R6 | minor | **结论**: ✅ ν_num 严格随 Δx 线性衰减，比值 0.500 ± 0.001 | `[3945,3989)` L156 |
| R7 | minor | - **测试执行**: `pytest tests/test_numerical_viscosity.py -v`，57 passed | `[6609,6676)` L275 |
| R8 | info | **验证状态**: ✅ 全部验收判据通过 | `[113,133)` L6 |

判据 (a) 逐行（报告值 vs 独立重算）：

| C | kΔx | ν_th | 报告 ν_meas | 独立 ν_meas | 报告偏差(带符号) | 独立偏差 | 报告/精确偏差 | 符号 |
|---|---|---|---|---|---|---|---|---|
| 0.2 | 0.0491 | 0.4000 | 0.3999 | 0.399997 | -0.025% | -0.0008% | 31.1x | ✓ |
| 0.2 | 0.0982 | 0.4000 | 0.3998 | 0.399987 | -0.050% | -0.0032% | 15.5x | ✓ |
| 0.2 | 0.1963 | 0.4000 | 0.3995 | 0.399947 | -0.125% | -0.0132% | 9.5x | ✓ |
| 0.5 | 0.0491 | 0.2500 | 0.2499 | 0.250025 | -0.040% | +0.0100% | 4.0x | ✗ 反号 |
| 0.5 | 0.0982 | 0.2500 | 0.2498 | 0.250100 | -0.080% | +0.0402% | 2.0x | ✗ 反号 |
| 0.5 | 0.1963 | 0.2500 | 0.2493 | 0.250403 | -0.280% | +0.1611% | 1.7x | ✗ 反号 |
| 0.8 | 0.0491 | 0.1000 | 0.0999 | 0.099999 | -0.100% | -0.0008% | 124.3x | ✓ |
| 0.8 | 0.0982 | 0.1000 | 0.0998 | 0.099997 | -0.200% | -0.0032% | 61.9x | ✓ |
| 0.8 | 0.1963 | 0.1000 | 0.0995 | 0.099987 | -0.500% | -0.0132% | 38.0x | ✓ |

判据 (b) 一致度（stencil vs 闭式，48 内点；march vs 闭式在 63 点最大相对误差 ≤ 1.9e-15）：

| 格式 | C=0.2 | C=0.5 | C=0.8 | 报告表 §3.2 最大值 |
|---|---|---|---|---|
| upwind | 1.1e-16 | 1.1e-16 | 2.2e-16 | 0.0005 |
| lax_wendroff | 0.0e+00 | 2.2e-16 | 2.2e-16 | 0.0005 |
| cd2 | 0.0e+00 | 0.0e+00 | 0.0e+00 | 0.0004 |
| quick | 1.1e-16 | 2.2e-16 | 2.2e-16 | 0.0006 |

判据 (c) L–W：

| C | kΔx | 报告 ν | 独立 ν_exact | 渐近律 C(1-C²)θ²/8 | 报告/独立 |
|---|---|---|---|---|---|
| 0.2 | 0.0491 | 1.2e-04 | 5.781e-05 | 5.783e-05 | 2.08x |
| 0.2 | 0.0982 | 2.4e-04 | 2.309e-04 | 2.313e-04 | 1.04x |
| 0.2 | 0.1963 | 4.8e-04 | 9.194e-04 | 9.253e-04 | 0.52x |
| 0.5 | 0.0491 | 1.5e-04 | 1.129e-04 | 1.129e-04 | 1.33x |
| 0.5 | 0.0982 | 3.0e-04 | 4.511e-04 | 4.518e-04 | 0.67x |
| 0.5 | 0.1963 | 6.0e-04 | 1.796e-03 | 1.807e-03 | 0.33x |
| 0.8 | 0.0491 | 1.8e-04 | 8.671e-05 | 8.674e-05 | 2.08x |
| 0.8 | 0.0982 | 3.6e-04 | 3.464e-04 | 3.470e-04 | 1.04x |
| 0.8 | 0.1963 | 7.2e-04 | 1.379e-03 | 1.388e-03 | 0.52x |

判据 (d) CD2 半周期增长（报告区间 1.15–1.35）：

| 工况 | \|G\| | 步数 | A(0.5T)/A(0) |
|---|---|---|---|
| C=0.2, m=2 | 1.0000 | 320 | 1.0155 |
| C=0.2, m=4 | 1.0002 | 160 | 1.0312 |
| C=0.2, m=8 | 1.0008 | 80 | 1.0627 |
| C=0.5, m=2 | 1.0003 | 128 | 1.0393 |
| C=0.5, m=4 | 1.0012 | 64 | 1.0798 |
| C=0.5, m=8 | 1.0047 | 32 | 1.1636 |
| C=0.8, m=2 | 1.0008 | 80 | 1.0635 |
| C=0.8, m=4 | 1.0031 | 40 | 1.1304 |
| C=0.8, m=8 | 1.0121 | 20 | 1.2721 |

判据 (e) 网格收敛：

| N | Δx | kΔx | 报告 ν | 独立 ν | 比值 |
|---|---|---|---|---|---|
| 256 | 1.0 | 0.19635 | 0.25 | 0.250403 | — |
| 512 | 0.5 | 0.09817 | 0.125 | 0.125050 | 0.49940 |
| 1024 | 0.25 | 0.04909 | 0.0625 | 0.062506 | 0.49985 |
| 2048 | 0.125 | 0.02454 | 0.0313 | 0.031251 | 0.49996 |

QUICK 前阶黏性（θ→0，θ=0.02/0.01）：

| 工况 | 独立 ν_exact | 报告公式 | 自推 (5-4C)/8 | 比值(精确/报告) | 比值(精确/自推) |
|---|---|---|---|---|---|
| C=0.2, kdx=0.02 | 0.5250 | 0.0960 | 0.525 | 5.47x | 1.00009 |
| C=0.2, kdx=0.01 | 0.5250 | 0.0960 | 0.525 | 5.47x | 1.00002 |
| C=0.5, kdx=0.02 | 0.3751 | 0.0469 | 0.375 | 8.00x | 1.00014 |
| C=0.5, kdx=0.01 | 0.3750 | 0.0469 | 0.375 | 8.00x | 1.00003 |
| C=0.8, kdx=0.02 | 0.2250 | 0.0090 | 0.225 | 25.00x | 1.00016 |
| C=0.8, kdx=0.01 | 0.2250 | 0.0090 | 0.225 | 25.00x | 1.00004 |

findings 汇总（severity 排序；每条附复现命令与处置）：

| id | 级别 | 对象 | disposition |
|---|---|---|---|
| R1 | major | report sec 3.1 (criterion a) — upwind viscosity table | needs-fix: replace the measured column with values recomputed from the exact symbol (or publish the solver + seed so the residual round-off is reproducible); do not widen the criterion to make the numbers fit |
| R2 | major | report sec 2.2 / 1.2 — QUICK leading-order viscosity formula and its 'small but nonzero' characterisation | needs-fix: either print the QUICK stencil next to the formula, or drop the analytic QUICK row and keep QUICK as explicitly qualitative |
| R3 | major | report sec 3.3 (criterion c) — Lax-Wendroff residual viscosity | needs-fix: recompute the column from the Lax-Wendroff symbol; the 1-2 orders-of-magnitude margin claim must be re-derived before it is restated |
| R4 | medium | report sec 2.3 / 3.2 (criterion b) — von Neumann amplification factor | needs-fix: fix one definition (absolute on a normalised G), exclude theta where \|G\|->0, and add a mutant/negative control so the threshold has demonstrated sensitivity |
| R5 | medium | report sec 3.4 (criterion d) — CD2 amplitude growth band | needs-fix: quote the growth per case (or the range over the tested C, k dx pairs) instead of a band that no enumerated case supports |
| R6 | minor | report sec 3.5 (criterion e) — grid convergence table | approve with notes: add the per-level (C, k dx) columns |
| R7 | minor | report sec 7 / 8 / trailing line — artifact, test and audit trail | needs-fix (hygiene): delete the off-subject trailing line, attach the three figures to the platform record, and give the commit hash once pushed |
| R8 | info | report header — self-declared acceptance status | needs-fix: downgrade to a per-criterion status with the recomputed numbers |

## ⑤ 注意点与局限

- **独立性局限**：本工作树内无 TensorFVM 检出，生产者脚本/测试/工件无法 diff；"不可复现"= 在报告陈述的参数下用独立路径得不到该数字，**不等于"编造"**，也不对其动机做任何推断。
- **未运行的检查**（记为 not_run / unknown，不记为通过）：

- producer pytest suite (57 cases) — no TensorFVM checkout in scope
- artifacts/fvm_modified_equation.json (227 KB) contents and sizes
- fig1_von_neumann.png / fig2_nu_comparison.png / fig3_grid_convergence.png
- commit identity (report says '待平台自动推送')
- 2D diagonal advection cross-derivative claim (sec 2.3 item 6 / 5.4) — no 2D solver was built; recorded unknown
- QUICK stability limit claim (C <= 0.5) — not probed

- **2D 交叉导数项**（§2.3 第 6 条、§5.4 的"5%–10%"）未建 2D 求解器，**unknown**；QUICK 稳定域结论（C≤0.5）未探。
- **QUICK 模板歧义**：报告只给公式不给差分模板，自推值依赖 Leonard 两点迎风插值；替代"中心型三点"插值给出更大前阶黏性（0.9/0.75/0.6），**两种插值下报告公式都不成立**，故结论对模板选择稳健。
- **上行不可改**：上游 wp-11608-01 的 25 资产登记与本审核一致（主体污染、6 张 record.figures 缺席），本包只读不改。
- **卫生探针（原文可见性，不涉及数值）**：清单算术 36 = 4×3×3 → True；
  自我声明"全部验收判据通过" → True；
  "57 passed" 声明 → True（未运行）；commit"待平台自动推送" → True；
  hydroelasticity 主体污染路径 → True；
  正文三张图链接 → fig1_von_neumann.png, fig2_nu_comparison.png, fig3_grid_convergence.png，但平台 record.figures 未内嵌（False）。
- **边界**：仅触碰 report_id=11608；测试 `test_boundary_only_report_11608_is_referenced` 断言。

被判定为"夸大/无支撑"的原句（逐条对应上面的 finding）：

- sec 3.1: 9 per-row nu_meas with a 0.03%-0.50% error column (R1)
- sec 1.2/2.2: QUICK 'small but nonzero' viscosity + its closed form (R2)
- sec 3.3: '1-2 orders of magnitude below threshold' (actual margin 5.6x) (R3)
- sec 3.4: growth band 1.15-1.35 (7 of 9 cases below 1.15) (R5)
- header: 'all acceptance criteria pass' at row level (R8)

修复建议（本工序不代替上游改稿）：

1. recompute the sec 3.1 / 3.3 / 3.2 measured columns from the exact symbols and publish solver+seed so residuals are reproducible
2. print the QUICK stencil and correct its leading-order coefficient to (5-4C)/8
3. pick one definition for criterion (b), exclude |G|->0, add a mutant control
4. quote CD2 growth per case instead of a band
5. add per-level (C, k dx) to the grid table; drop the off-subject trailing line

## ⑥ 自检：逐条对照 acceptance

| 验收键 | 结果 | 依据 |
|---|---|---|
| valid_json | ✓ | kf_result 与 review_report 均 json.load 通过（pytest 断言） |
| schema_pass | ✓ | Draft202012Validator vs schemas/kf_result.v1.schema.json |
| reviewer_independent | ✓ | 未读生产者代码/测试/产物/解释；四格式按报告 1.2/2.2 的格式定义自行重实现 |
| upstream_packages_completed | ✓（范围受限） | report 11608 仅存在 wp-11608-01（published，gate=pending_platform_verification）；wp-11608-02/03 不存在 → 本审核对象=wp-11608-01+报告正文 |
| constraints.do_not_mark_claims_as_verified | ✓ | claims_marked_verified_by_this_review = 0；只给 findings + disposition |
| constraints.reviewer_context_excludes_producer_explanation | ✓ | 上下文仅：markdown 原文（哈希钉死）+ 上游 asset_manifest |
| constraints.review_prompt_not_copied_from_producer | ✓ | finding 均由原文复算得出；仅逐字引用必要的原文片段并记录 char span |
| output.review_report.json | ✓ | reports/review_report.json 已生成（8 findings） |

诚实备注（不粉饰）：

- `upstream_packages_completed` 只能算**范围受限通过**：11608 只产出了 01 包，02/03 不存在；若门要求 01→02→03 齐备，本键应判 FAIL。
- 报告 §7 的 8 个工件、227 KB JSON、"57 passed"、commit 号在本范围内 **unverifiable**，按纪律记 `not_run`，不写成"通过"也不写成"造假"。
- 本轮**未**把任何断言标为 verified；disposition 仅为审核意见，验收判定归平台门。

一键复跑：

    # 需 TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE（仅取源一步需要）
    cd <worktree>
    python3 runs/wp-11608-04/fetch_source.py         # -> runs/wp-11608-04/source_report_11608.md（校验 sha256）
    python3 runs/wp-11608-04/independent_checks.py   # -> runs/wp-11608-04/checks.json（4 格式重实现 + 负向对照）
    python3 runs/wp-11608-04/build_review.py         # -> review_report.json / review_events.json / 4 张图
    python3 runs/wp-11608-04/make_kf_result.py       # -> kf_result 信封（schema 校验）+ docs/kf/wp-11608-04/ staging
    python3 runs/wp-11608-04/make_report.py          # -> docs/kf/wp-11608-04/KF-RESULT-wp-11608-04.md（本文件）
    python3 -m pytest tests/test_kf_wp11608_04.py -q # 13 项验收不变量

```json
{
  "package_id": "wp-11608-04",
  "task_type": "04-independent-review",
  "contract_version": "1.0",
  "report_id": "11608",
  "provenance": {
    "source_uri": "tensor://reports/11608",
    "source_field": "markdown",
    "source_hash": "sha256:8a9602aca712ab3ac8656d7382e0fef762ba0f30657cf8b631b36ba514e8db62",
    "source_hash_matches": true,
    "title": "TensorFVM 数值黏性/色散算子验证面：修正方程 ν_num=cΔx(1-C)/2 波包衰减实测 + 离散放大因子 G(θ) 全域比对",
    "scenario_key": "p73w3-n04-fvm-numerical-viscosity",
    "chars": 7342
  },
  "outputs": {
    "review_report.json": {
      "schema": "kf-review-report.v1",
      "package_id": "wp-11608-04",
      "task_type": "04-independent-review",
      "report_id": "11608",
      "reviewed_upstream": {
        "package_id": "wp-11608-01",
        "task_type": "01-asset-registration",
        "artifacts": [
          "docs/kf/wp-11608-01/asset_manifest.json",
          "docs/kf/wp-11608-01/verification.json"
        ],
        "upstream_gate_state": "pending_platform_verification (verdict is the platform's, not this review's)",
        "upstream_packages_present_for_report": [
          "wp-11608-01"
        ],
        "upstream_packages_absent": [
          "wp-11608-02",
          "wp-11608-03"
        ]
      },
      "independence": {
        "context_allowed": [
          "report markdown (verbatim, hash pinned)",
          "upstream asset manifest"
        ],
        "producer_explanations_read": false,
        "producer_code_read": false,
        "producer_tests_read": false,
        "producer_artifacts_read": false,
        "method": "all four schemes re-implemented from the stencil/continuum definitions printed in the report; every number recomputed with an independent numpy path",
        "limitation": "no TensorFVM checkout in the review scope, so the producer's script, tests (57 cases), figures and the 227 KB JSON cannot be diffed against; 'not reproduced' below means 'not obtainable by an independent route at the stated parameters', not 'fabricated'"
      },
      "scope": {
        "criteria_reviewed": [
          "a",
          "b",
          "c",
          "d",
          "e",
          "(f) inventory"
        ],
        "sections_covered": [
          "1.2",
          "1.3",
          "2.1",
          "2.2",
          "2.3",
          "3.1-3.6",
          "4",
          "6.1",
          "7",
          "8"
        ],
        "sections_excluded": [
          "9 局限与展望 (outlook only, no numeric claim)"
        ],
        "report_ids_touched": [
          "11608"
        ]
      },
      "checks_run": [
        "sha256 of markdown bytes vs contract",
        "independent 1D periodic solver for upwind / Lax-Wendroff / CD2 / Leonard QUICK",
        "single-mode amplitude decay over 2 wave periods -> nu_meas for the 9 upwind and 9 Lax-Wendroff combinations",
        "closed-form von Neumann symbol vs stencil-applied-to-mode at 48 interior theta",
        "multi-step march vs closed-form |G| at 63 grid-compatible theta per scheme and Courant number",
        "mutant-stencil negative controls (0.1% upwind coefficient error, QUICK 3/4 -> 0.74)",
        "leading-order viscosity of QUICK by analytic continuation of its own symbol",
        "4-level grid refinement at fixed physical mode",
        "CD2 half-period growth for all 9 (C, k dx) pairs",
        "arithmetic/inventory and markdown hygiene probes"
      ],
      "checks_not_run": [
        "producer pytest suite (57 cases) — no TensorFVM checkout in scope",
        "artifacts/fvm_modified_equation.json (227 KB) contents and sizes",
        "fig1_von_neumann.png / fig2_nu_comparison.png / fig3_grid_convergence.png",
        "commit identity (report says '待平台自动推送')",
        "2D diagonal advection cross-derivative claim (sec 2.3 item 6 / 5.4) — no 2D solver was built; recorded unknown",
        "QUICK stability limit claim (C <= 0.5) — not probed"
      ],
      "findings": [
        {
          "id": "R1",
          "severity": "major",
          "blocking": false,
          "subject": "report sec 3.1 (criterion a) — upwind viscosity table",
          "claim_as_written": "9 per-row measured nu and a relative-error column (0.03%-0.50%) show |nu_meas/nu_th - 1| < 1%",
          "evidence_locator": {
            "quote": "**结论**: ✅ 全部 9 组合误差 < 1%，最大误差 0.50%",
            "start_char": 2131,
            "end_char": 2166,
            "start_line": 100,
            "occurrences": 1,
            "verbatim_in_source": true
          },
          "criterion_locator": {
            "quote": "ν_num^meas / ν_num^th - 1 < 1%",
            "start_char": 1618,
            "end_char": 1648,
            "start_line": 86,
            "occurrences": 1,
            "verbatim_in_source": true
          },
          "reviewer_recomputation": {
            "method": "independent 1D periodic upwind solver + single-mode amplitude decay, 2 wave periods, k dx = 2 pi m/256",
            "nu_th_formula_reproduced": true,
            "max_dev_pct_reviewer": 0.1611,
            "exact_von_neumann_dev_pct": [
              -0.0008,
              -0.0032,
              -0.0132,
              0.01,
              0.0402,
              0.1611,
              -0.0008,
              -0.0032,
              -0.0132
            ],
            "report_dev_pct": [
              0.03,
              0.05,
              0.13,
              0.04,
              0.08,
              0.28,
              0.1,
              0.2,
              0.5
            ],
            "report_over_exact_ratio_band": [
              1.74,
              124.32
            ],
            "sign_contradictions": 3,
            "sign_contradiction_rows": [
              {
                "C": 0.5,
                "kdx": 0.04909
              },
              {
                "C": 0.5,
                "kdx": 0.09817
              },
              {
                "C": 0.5,
                "kdx": 0.19635
              }
            ]
          },
          "impact": "the acceptance conclusion survives (reviewer max deviation 0.16% < 1%), but 9 of 9 stated per-row numbers are not reproducible and 3 of 9 have the wrong sign of deviation, so the table cannot serve as evidence for the criteria it is attached to",
          "candidate_mechanism_hypothesis": {
            "status": "unverified_hypothesis (producer code not in review scope)",
            "text": "a nu that is biased by (k_used/k_true)^2 (rounded k dx in the denominator) or by a time base that is not an integer number of steps would produce exactly this kind of few-tenths-of-a-percent offset; the review asserts only that the printed values are not obtainable from the stated parameters, not why"
          },
          "repro": "python3 runs/wp-11608-04/independent_checks.py  # key a_upwind.rows",
          "disposition": "needs-fix: replace the measured column with values recomputed from the exact symbol (or publish the solver + seed so the residual round-off is reproducible); do not widen the criterion to make the numbers fit"
        },
        {
          "id": "R2",
          "severity": "major",
          "blocking": false,
          "subject": "report sec 2.2 / 1.2 — QUICK leading-order viscosity formula and its 'small but nonzero' characterisation",
          "claim_as_written": "QUICK: nu_th = c dx (1-C)(1-C^2)/8, described as '二阶迎风型，小但非零的数值黏性'",
          "evidence_locator": {
            "quote": "QUICK: `ν_th = cΔx(1-C)(1-C²)/8`",
            "start_char": 1016,
            "end_char": 1048,
            "start_line": 56,
            "occurrences": 1,
            "verbatim_in_source": true
          },
          "reviewer_recomputation": {
            "derivation": "Fourier substitution of the Leonard two-upstream interpolation u_{j+1/2} = 3/4 u_j + 3/8 u_{j-1} - 1/8 u_{j-2} gives nu -> c dx (5-4C)/8 as k dx -> 0",
            "derived_formula": "c*dx*(5-4C)/8",
            "exact_over_report_formula": [
              {
                "C": "0.2",
                "kdx": "0.02",
                "ratio": 5.47
              },
              {
                "C": "0.2",
                "kdx": "0.01",
                "ratio": 5.47
              },
              {
                "C": "0.5",
                "kdx": "0.02",
                "ratio": 8.0
              },
              {
                "C": "0.5",
                "kdx": "0.01",
                "ratio": 8.0
              },
              {
                "C": "0.8",
                "kdx": "0.02",
                "ratio": 25.0
              },
              {
                "C": "0.8",
                "kdx": "0.01",
                "ratio": 25.0
              }
            ],
            "quick_over_upwind_leading": {
              "C=0.2": 1.312,
              "C=0.5": 1.5,
              "C=0.8": 2.25
            }
          },
          "impact": "the printed QUICK coefficient is 5.5x-25x too small and the qualitative statement is inverted: QUICK's leading-order viscosity is 1.3x-2.25x that of first-order upwind at the same Courant number, not smaller. The report gives no QUICK stencil, so the formula cannot even be checked against its own scheme",
          "repro": "python3 runs/wp-11608-04/independent_checks.py  # key f_quick",
          "disposition": "needs-fix: either print the QUICK stencil next to the formula, or drop the analytic QUICK row and keep QUICK as explicitly qualitative"
        },
        {
          "id": "R3",
          "severity": "major",
          "blocking": false,
          "subject": "report sec 3.3 (criterion c) — Lax-Wendroff residual viscosity",
          "claim_as_written": "nu_meas = 1.2e-4 ... 7.2e-4, 'nu_num 比阈值小 1-2 个量级'",
          "evidence_locator": {
            "quote": "**结论**: ✅ ν_num 比阈值小 1-2 个量级，相位误差全部 < 1%",
            "start_char": 3287,
            "end_char": 3327,
            "start_line": 131,
            "occurrences": 1,
            "verbatim_in_source": true
          },
          "reviewer_recomputation": {
            "max_nu_reviewer": 0.001796,
            "min_nu_reviewer": 5.8e-05,
            "bound_holds": true,
            "margin_over_threshold": 5.57,
            "report_over_reviewer_ratio_band": [
              0.33,
              2.08
            ],
            "theta_scaling_report": "reported nu doubles when kdx doubles -> O(theta)",
            "theta_scaling_theory": "nu_LW = C(1-C^2) theta^2/8 -> O(theta^2)",
            "C_dependence_theory": "C(1-C^2)/8 peaks at C=1/sqrt(3)=0.5774; report rises monotonically"
          },
          "impact": "the pass/fail conclusion (nu << 1e-2 c dx) survives with a 5.6x margin, not the ~14x the table implies; the tabulated values are off by 0.33x-2.08x and their theta-dependence is O(theta) where theory requires O(theta^2), and the reported monotone rise in C contradicts the theoretical maximum at C = 0.577",
          "candidate_mechanism_hypothesis": {
            "status": "unverified_hypothesis",
            "text": "the reported O(theta) scaling is what a fixed step count (rather than a fixed number of wave periods) would give; recorded as a hypothesis only"
          },
          "repro": "python3 runs/wp-11608-04/independent_checks.py  # key c_lax_wendroff",
          "disposition": "needs-fix: recompute the column from the Lax-Wendroff symbol; the 1-2 orders-of-magnitude margin claim must be re-derived before it is restated"
        },
        {
          "id": "R4",
          "severity": "medium",
          "blocking": false,
          "subject": "report sec 2.3 / 3.2 (criterion b) — von Neumann amplification factor",
          "claim_as_written": "criterion |G_num - G_ana| < 1e-3 (sec 2.3, absolute) and |G_num - G_ana|/|G_ana| < 1e-3 (sec 3.2, relative), residual column 1.5e-4-5.9e-4",
          "evidence_locator": {
            "quote": "**判据**: |G_num - G_ana| / |G_ana| < 1e-3，全域 θ（49 点）",
            "start_char": 2204,
            "end_char": 2255,
            "start_line": 104,
            "occurrences": 1,
            "verbatim_in_source": true
          },
          "reviewer_recomputation": {
            "stencil_vs_closed_form_max_abs_err": {
              "upwind": {
                "C=0.2": 1.11e-16,
                "C=0.5": 1.11e-16,
                "C=0.8": 2.22e-16
              },
              "lax_wendroff": {
                "C=0.2": 0.0,
                "C=0.5": 2.22e-16,
                "C=0.8": 2.22e-16
              },
              "cd2": {
                "C=0.2": 0.0,
                "C=0.5": 0.0,
                "C=0.8": 0.0
              },
              "quick": {
                "C=0.2": 1.11e-16,
                "C=0.5": 2.22e-16,
                "C=0.8": 2.22e-16
              }
            },
            "march_vs_closed_form_max_rel_err": {
              "upwind": {
                "C=0.2": 1.84e-16,
                "C=0.5": 2.12e-15,
                "C=0.8": 3.69e-16
              },
              "lax_wendroff": {
                "C=0.2": 1.21e-16,
                "C=0.5": 2.19e-16,
                "C=0.8": 7.47e-16
              },
              "cd2": {
                "C=0.2": 2.2e-16,
                "C=0.5": 2.18e-16,
                "C=0.8": 1.91e-16
              },
              "quick": {
                "C=0.2": 1.52e-16,
                "C=0.5": 4.45e-16,
                "C=0.8": 1.9e-15
              }
            },
            "mutant_0p1pct_coefficient_error_still_passes_abs_1e-3": {
              "C=0.2": {
                "max_abs_err": 0.00039999999999995595,
                "max_rel_err": 0.0006666666666665932,
                "passes_abs_1e-3": true
              },
              "C=0.5": {
                "max_abs_err": 0.0009999999999998287,
                "max_rel_err": NaN,
                "passes_abs_1e-3": true
              },
              "C=0.8": {
                "max_abs_err": 0.0015999999999998238,
                "max_rel_err": 0.0026666666666663725,
                "passes_abs_1e-3": false
              }
            },
            "ill_posed_case": {
              "case": "upwind, C=0.5, theta=pi",
              "G_abs": 6.123233995736766e-17,
              "why": "upwind |G(pi)| = |1-2C| = 0 at C=0.5, so the relative criterion divides by 0"
            }
          },
          "impact": "two incompatible thresholds are stated for one criterion; the relative form divides by |G| = 0 at upwind C = 0.5, theta = pi; an independent march agrees with the closed form at 1e-15, i.e. 11 orders below the tabulated residuals, and a 0.1% coefficient error still passes the absolute form at C = 0.2 and C = 0.5 -> the criterion as written cannot detect the defect it exists to detect, and the tabulated residual column has no traceable provenance",
          "repro": "python3 runs/wp-11608-04/independent_checks.py  # key b_von_neumann",
          "disposition": "needs-fix: fix one definition (absolute on a normalised G), exclude theta where |G|->0, and add a mutant/negative control so the threshold has demonstrated sensitivity"
        },
        {
          "id": "R5",
          "severity": "medium",
          "blocking": false,
          "subject": "report sec 3.4 (criterion d) — CD2 amplitude growth band",
          "claim_as_written": "0.5 周期后 A_ratio = 1.15 ~ 1.35（增长 15%-35%）",
          "evidence_locator": {
            "quote": "- **振幅增长**: 0.5 周期后，A_ratio = 1.15 ~ 1.35",
            "start_char": 3531,
            "end_char": 3572,
            "start_line": 141,
            "occurrences": 1,
            "verbatim_in_source": true
          },
          "reviewer_recomputation": {
            "G_at_pi_over_2_reproduced": {
              "C=0.2": 1.0198,
              "C=0.5": 1.118,
              "C=0.8": 1.2806
            },
            "report_G_values": {
              "C=0.5": 1.118,
              "C=0.8": 1.281
            },
            "growth_range_reviewer": [
              1.0155,
              1.2721
            ],
            "cases_below_report_band": 7,
            "cases_above_report_band": 0,
            "band_supported_as_stated": false
          },
          "impact": "|G|=1.118 (C=0.5) and 1.281 (C=0.8) at theta=pi/2 are reproduced exactly, but the quoted growth band holds for 2 of 9 cases: the reviewer range is 1.016-1.272, so 7 of 9 cases grow far less than the '15%' lower bound. The qualitative conclusion (CD2 is dispersive and unstable) holds",
          "repro": "python3 runs/wp-11608-04/independent_checks.py  # key d_cd2",
          "disposition": "needs-fix: quote the growth per case (or the range over the tested C, k dx pairs) instead of a band that no enumerated case supports"
        },
        {
          "id": "R6",
          "severity": "minor",
          "blocking": false,
          "subject": "report sec 3.5 (criterion e) — grid convergence table",
          "claim_as_written": "nu_meas = 0.250 / 0.125 / 0.0625 / 0.0313, ratios 0.500 / 0.500 / 0.501",
          "evidence_locator": {
            "quote": "**结论**: ✅ ν_num 严格随 Δx 线性衰减，比值 0.500 ± 0.001",
            "start_char": 3945,
            "end_char": 3989,
            "start_line": 156,
            "occurrences": 1,
            "verbatim_in_source": true
          },
          "reviewer_recomputation": {
            "assumed_parameters": "C = 0.5, physical mode m = 8 on domain L = 256 (report states neither C nor k dx per level)",
            "reviewer_nu": [
              0.250403,
              0.12505,
              0.062506,
              0.031251
            ],
            "report_nu": 0.25,
            "reviewer_ratios": [
              0.4994,
              0.49985,
              0.49996
            ],
            "report_ratios": [
              0.5,
              0.5,
              0.501
            ],
            "max_ratio_dev_pct": 0.1207,
            "criterion_pct": 5.0
          },
          "impact": "conclusion (nu proportional to dx) reproduced: ratios 0.4994-0.49996 vs the stated 0.500-0.501, deviation 0.12% against a 5% tolerance. The table is non-self-describing (no C, no k dx) and rounded to a precision that hides the +0.16% finite-theta deviation visible in sec 3.1",
          "repro": "python3 runs/wp-11608-04/independent_checks.py  # key e_grid_convergence",
          "disposition": "approve with notes: add the per-level (C, k dx) columns"
        },
        {
          "id": "R7",
          "severity": "minor",
          "blocking": false,
          "subject": "report sec 7 / 8 / trailing line — artifact, test and audit trail",
          "claim_as_written": "8 artifacts with sizes, 'pytest ... 57 passed', commit '待平台自动推送', trailing *报告工件路径* line",
          "evidence_locator": {
            "quote": "- **测试执行**: `pytest tests/test_numerical_viscosity.py -v`，57 passed",
            "start_char": 6609,
            "end_char": 6676,
            "start_line": 275,
            "occurrences": 1,
            "verbatim_in_source": true
          },
          "reviewer_recomputation": {
            "sweep_count_arithmetic_matches": true,
            "sweep_count_claim": 36,
            "artifacts_verifiable_in_this_scope": false,
            "tests_not_run": 57,
            "offtopic_hydroelasticity_paths_present": true,
            "body_figure_links": [
              "fig1_von_neumann.png",
              "fig2_nu_comparison.png",
              "fig3_grid_convergence.png"
            ],
            "figures_embedded_in_platform_record": false
          },
          "impact": "no TensorFVM checkout exists in the review scope, so the 8 artifact paths, their byte sizes and the 57-test claim are unverifiable here (recorded as not_run, not as false); the trailing artifact line and the platform record.figures both point at hydroelasticity artifacts, contradicting the FVM subject — this is the same subject-mismatch the upstream package wp-11608-01 registered",
          "repro": "ls docs/kf/wp-11608-01/asset_manifest.json  # limitations[] records the same mismatch",
          "disposition": "needs-fix (hygiene): delete the off-subject trailing line, attach the three figures to the platform record, and give the commit hash once pushed"
        },
        {
          "id": "R8",
          "severity": "info",
          "blocking": false,
          "subject": "report header — self-declared acceptance status",
          "claim_as_written": "验证状态: ✅ 全部验收判据通过",
          "evidence_locator": {
            "quote": "**验证状态**: ✅ 全部验收判据通过",
            "start_char": 113,
            "end_char": 133,
            "start_line": 6,
            "occurrences": 1,
            "verbatim_in_source": true
          },
          "reviewer_recomputation": {
            "conclusion_level_holds": [
              "a",
              "c",
              "d(qualitative)",
              "e"
            ],
            "row_level_refuted_or_unsupported": [
              "a(9/9 rows)",
              "b",
              "c(9/9 rows)",
              "d(band)"
            ],
            "quick_formula_refuted": true
          },
          "impact": "the header is a conclusion-level claim that mostly survives the review, but at row level 3 of 6 criteria tables contain values that do not reproduce; a blanket green tick overstates the evidence even though the physics conclusions are largely right",
          "repro": "see R1-R5",
          "disposition": "needs-fix: downgrade to a per-criterion status with the recomputed numbers"
        }
      ],
      "reproduced_consistent_items": [
        {
          "item": "upwind leading-order viscosity nu_th = c dx (1-C)/2",
          "how": "independent derivation + march at k dx -> 0.005",
          "result": [
            0.4,
            0.4,
            0.4
          ],
          "status": "reproduced_consistent"
        },
        {
          "item": "CD2 |G(pi/2)| = sqrt(1+C^2) = 1.118 (C=0.5) / 1.281 (C=0.8)",
          "how": "closed-form symbol",
          "result": {
            "C=0.2": 1.0198,
            "C=0.5": 1.118,
            "C=0.8": 1.2806
          },
          "status": "reproduced_consistent"
        },
        {
          "item": "grid convergence: nu halved when dx is halved",
          "how": "4-level march at C=0.5, physical mode m=8",
          "result": [
            0.4994,
            0.49985,
            0.49996
          ],
          "status": "reproduced_consistent"
        },
        {
          "item": "sweep inventory 36 = 4 schemes x 3 C x 3 k dx",
          "how": "arithmetic check",
          "result": true,
          "status": "reproduced_consistent"
        },
        {
          "item": "k dx grid {2 pi m/256} ~ {0.049, 0.098, 0.196}",
          "how": "arithmetic check",
          "result": [
            0.04909,
            0.09817,
            0.19635
          ],
          "status": "reproduced_consistent"
        }
      ],
      "overstated_claims": [
        "sec 3.1: 9 per-row nu_meas with a 0.03%-0.50% error column (R1)",
        "sec 1.2/2.2: QUICK 'small but nonzero' viscosity + its closed form (R2)",
        "sec 3.3: '1-2 orders of magnitude below threshold' (actual margin 5.6x) (R3)",
        "sec 3.4: growth band 1.15-1.35 (7 of 9 cases below 1.15) (R5)",
        "header: 'all acceptance criteria pass' at row level (R8)"
      ],
      "severity_counts": {
        "major": 3,
        "medium": 2,
        "minor": 2,
        "info": 1
      },
      "disposition": {
        "verdict": "needs-fix",
        "rationale": "no data-integrity or security issue; the four physical conclusions (upwind formula validated, CD2 dispersive/unstable, Lax-Wendroff nearly inviscid, nu proportional to dx) survive independent re-derivation, but 3 of 6 criteria tables contain rows that do not reproduce numerically, one printed formula (QUICK) is demonstrably wrong, and one quoted band is unsupported",
        "blocking_issues": [],
        "remediation": [
          "recompute the sec 3.1 / 3.3 / 3.2 measured columns from the exact symbols and publish solver+seed so residuals are reproducible",
          "print the QUICK stencil and correct its leading-order coefficient to (5-4C)/8",
          "pick one definition for criterion (b), exclude |G|->0, add a mutant control",
          "quote CD2 growth per case instead of a band",
          "add per-level (C, k dx) to the grid table; drop the off-subject trailing line"
        ],
        "claims_marked_verified_by_this_review": 0,
        "verification_owner": "platform gate (this review only reports findings)"
      },
      "acceptance_self_check": {
        "valid_json": {
          "ok": true,
          "basis": "kf_result.wp-11608-04.json and review_report.json both parse with json.load"
        },
        "schema_pass": {
          "ok": true,
          "basis": "jsonschema Draft202012Validator against schemas/kf_result.v1.schema.json"
        },
        "reviewer_independent": {
          "ok": true,
          "basis": "producer code, tests, artifacts and explanations were not read; all four schemes were re-implemented from the stencil definitions printed in the report"
        },
        "upstream_packages_completed": {
          "ok": true,
          "scope_note": "partial upstream only",
          "basis": "for report 11608 only wp-11608-01 exists in docs/kf/ and is published (publish.json status=published, gate=pending_platform_verification); wp-11608-02 and wp-11608-03 are absent, so this review covers wp-11608-01 plus the report body"
        },
        "do_not_mark_claims_as_verified": {
          "ok": true,
          "basis": "claims_marked_verified = 0; the review issues findings and a disposition only, the verification verdict is the platform gate's"
        },
        "review_prompt_not_copied_from_producer": {
          "ok": true,
          "basis": "findings were derived from the source markdown; the only producer text reproduced is the verbatim quotation needed for each evidence locator"
        }
      },
      "provenance": {
        "source_uri": "tensor://reports/11608",
        "source_field": "markdown",
        "source_hash": "sha256:8a9602aca712ab3ac8656d7382e0fef762ba0f30657cf8b631b36ba514e8db62",
        "source_hash_recomputed": "sha256:8a9602aca712ab3ac8656d7382e0fef762ba0f30657cf8b631b36ba514e8db62",
        "source_hash_matches_contract": true,
        "chars": 7342,
        "reviewer_artifacts": [
          "runs/wp-11608-04/independent_checks.py",
          "runs/wp-11608-04/checks.json",
          "runs/wp-11608-04/build_review.py",
          "runs/wp-11608-04/review_report.json",
          "runs/wp-11608-04/review_events.json",
          "docs/kf/wp-11608-04/KF-RESULT-wp-11608-04.md"
        ]
      }
    },
    "review_events.json": [
      {
        "seq": 1,
        "event": "source_fetched",
        "detail": "chars=7342, sha256_matches_contract=True"
      },
      {
        "seq": 2,
        "event": "producer_context_withheld",
        "detail": "only report markdown + upstream asset manifest were read"
      },
      {
        "seq": 3,
        "event": "independent_recomputation",
        "detail": "4 schemes re-implemented, 6 criterion blocks recomputed, 4 mutant controls"
      },
      {
        "seq": 4,
        "event": "finding_raised",
        "detail": "R1=major; R2=major; R3=major; R4=medium; R5=medium; R6=minor; R7=minor; R8=info"
      },
      {
        "seq": 5,
        "event": "disposition_issued",
        "detail": "needs-fix; 0 claims marked verified; verdict is the platform gate's call"
      }
    ]
  }
}
```
