# KF-RESULT wp-7216-01

**工作包**: `wp-7216-01` · **task_type**: `01-asset-registration` · **report_id**: `7216` · **lane**: `C` · **delivery**: `TensorKnowledge`（draft）
**源**: `tensor://reports/7216` 字段 `markdown` · **哈希口径**: UTF-8 字节 · `sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b`

## ① 本工序做了什么

对 report 7216《IN31-N12: LBM Rayleigh-Benard discrete linear stability + two-phase lambda/rho decoupling and Hadamard-Rybczynski comparison》执行**资产登记**（工序 01-asset-registration）：只确认源资产身份、清点报告声明的附件/工件/代码指针，**不做抽取、不做报告类型判定、不标 verified**（契约 objective 仅 `register_assets=true`，`classify_report_type=false`）。

1. **源资产身份确认**：`markdown` = 17984 B / 11338 字符 / 210 行；本地重算 sha256 = `sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b`，与工作包契约 `source_hash` **逐字节一致**；字符数 11338 = 契约 `chars` 11338；`title`、`scenario_key`（`lbm_rb_hr_validation`）与契约逐字一致。
2. **登记资产 40 项**：1 项源 markdown（`resolved_in_source`，字节在手）+ 39 项正文声明的引用（图 / 源码 / bench 脚本 / 单测 / 数据工件 / 目录 / 产出分支 / 库符号）。
3. **每条资产带可重解析定位**：字符区间 `[char_start, char_end)` + 1 基行号 + 该行**逐字**引文 + 引文 sha256；40/40 个引文在源内唯一（`unique=true`）。
4. **解析状态如实三分**：`resolved_in_source` **1**（源 markdown 一项，另有本地副本 `runs/wp-7216-01/source_7216.md`）、`referenced_unresolved` **39**、`declared_absent` **0**。**没有任何资产被标成 verified**（`integrity.verified_marks_emitted = 0`）。
5. `claims` 保持**空数组**并写明理由：本工序不产出知识对象；report 7216 自身的数值结论原样留在源 markdown，本工序不改写、不重述、不升级。

资产按类别分布：

| asset_class | 数量 |
|---|---|
| `api_symbol_reference` | 17 |
| `benchmark_script_reference` | 3 |
| `data_artifact_reference` | 6 |
| `directory_reference` | 1 |
| `figure_reference` | 6 |
| `git_branch_reference` | 1 |
| `report_markdown` | 1 |
| `source_code_reference` | 3 |
| `test_reference` | 2 |
| **合计** | **40** |

（`resolved_in_source` 1 / `referenced_unresolved` 39 / `declared_absent` 0）

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`POST /api/v1/auth/login`（`$TENSOR_AGENT_USER`）→ `GET /api/v1/tensor/reports/7216`，取 `markdown` **原字段**，UTF-8 字节落盘 `runs/wp-7216-01/source_7216.md`（`record_7216.json` 同时落盘供复核）。旁路交叉校验尝试：`psql -d $TP_PG_DB -tA -c "select markdown from tensor_reports where id=7216"` → `ERROR:  permission denied for table tensor_reports`，故 **API 是本次唯一可用取源通道**（如实记 `not_run`，不当作 PASS；记录见 `verification.json:extra_checks.db_cross_channel`）。
2. **定身份，不等即中止**：`sha256(UTF-8 bytes)` vs 契约 `source_hash`；`len(markdown)` vs 契约 `chars=11338`；`title` / `scenario_key` vs 契约。任一不符 → `SystemExit`，不产出半成品清单（本次 4 项全等）。
3. **扫描引用（规则确定、零猜测）**：
   - markdown 图片语法 `![alt](path)` → 图引用；
   - 反引号内容中符合**路径字符集** `^[A-Za-z0-9_./*-]+$` 者 → 路径引用；按扩展名归类（`.py`→源码/测试/bench、`.json`→数据工件、`.png`→图、无扩展→目录）；含 `*` 的 glob 单独标 `figure_glob`；`agent/...` → 产出分支引用；
   - 反引号内**含空格的 shell 命令**（如 `pytest -q tests/....py tests/....py`、`python benchmarks/.../run_bench.py --ny N`）按空白切分，只登记带真实工件后缀的参数——这样一处命令里的两个单测文件都被登记，而公式里的 `1/2` 不会被误登记（首版踩到 1 例假阳性后修正，见 ⑤-4）；
   - 反引号内的**点分模块名**、**带参调用**、**snake_case 标识符** → `api_symbol_reference`（声明的库符号/可调用入口）。
4. **解析判定（按类别分别做实测探针，而不是统一标"未解析"）**：
   - 源 markdown → 字节在手，`resolved_in_source`；
   - 图 → `GET /api/v1/tensor/reports/7216/figures/<name>` 逐图探测，结果写进 `resolution_check`；
   - 源码/测试/bench/数据工件 → 只在**交付工作树**（TensorKnowledge）内查找，命中则记字节数 + sha256，未命中记 `unresolved` + 同 basename 命中列表；**不跨仓臆测存在性**；
   - 库符号 / 产出分支 → `declared_only`：本工序的契约范围不含打开产出仓（TensorLBM，报告 §6 署名分支 `agent/m5628`）。
5. **非契约旁证探针**（`ecosystem_presence_probe.json`，**不参与**资产状态判定）：8/14 个声明路径在本地生态检出中被找到；其中内容哈希不唯一者 1 个（`rb_continuum_stability.py` → 2 种内容）；6 个 `artifacts/in31_n12/*.json` 在 0 个检出中出现。该探针只证明"这些文件在本地某些业检出里存在"，**不能**证明产出修订，因此不把任何资产翻转为 `resolved`——这是刻意的保守设定。
6. **信封 + 自校验**：`kf_result.json` 的 `provenance.source_hash` 由**重新拉取的实时字节**重算后写入；`verification.json` 用 `jsonschema` 校验 `schemas/kf_result.v1.schema.json`（Draft 2020-12，平台下发 schema 的仓内副本）与本包的结构 pin `docs/kf/wp-7216-01/asset_manifest.schema.json`（Draft-07，由 wp-448 先例 schema 重新参数化到本包），并**再次**对实时 markdown 重解析全部定位点。
7. **工具链**：纯标准库（urllib / hashlib / json / re / subprocess）+ `jsonschema` 做 schema 门 + matplotlib 出图；脚本幂等，`all` 一条命令重建全部产物。

一键复跑（工作树根执行；需 `TENSOR_API_BASE` / `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS`）：

```bash
python3 scripts/kf_wp721601_register_assets.py all   && python3 scripts/kf_wp721601_render_report.py render
# 复跑校验（acceptance 六项）：见上条命令内 verify 子命令的输出，以及
# docs/kf/wp-7216-01/verification.json:"all_ok"
```

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-7216-01/asset_manifest.json` | 主产物。40 项资产，每项含 class / 定位点（char span + 行号 + 逐字引文 + 引文 sha256 + unique）/ resolution / resolution_check；`claims=[]` 附理由；`integrity` 记录哈希本地重算与契约一致、`verified_marks_emitted=0`。 |
| `docs/kf/wp-7216-01/kf_result.json` | 平台结果信封（即本报告末尾唯一 json 代码块的内容）。`provenance.source_hash` = `sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b`，`outputs["asset_manifest.json"]` 为上述清单全文。 |
| `docs/kf/wp-7216-01/verification.json` | 六项 acceptance 的自校验记录（含每项 detail / 失败列表）+ `extra_checks`（API↔DB 双通道交叉验证尝试；本次 DB 直读被拒 → `not_run`）。`all_ok=true`。 |
| `docs/kf/wp-7216-01/asset_manifest.schema.json` | 本包清单的结构 pin（Draft-07）。wp-448 先例 schema 把 `package_id`/`report_id` 写死成 `wp-448-01`/`448`，无法校验其它包，故重新参数化；平台 schema 若有差异以平台门为准。 |
| `docs/kf/wp-7216-01/ecosystem_presence_probe.json` | 非契约旁证：14 个声明路径在本地生态检出中的存在性/内容哈希分布。**不参与** resolution 判定。 |
| `docs/kf/wp-7216-01/figures/wp721601_source_locator_map.png` | 定位点分布图（行剖面 + 各类资产定位竖线 + 类别计数）。 |
| `docs/reports/kf_wp_7216_01_result.md` | 本报告（含唯一 json 代码块）。 |
| `runs/wp-7216-01/source_7216.md` / `record_7216.json` | 源 markdown 字节副本与报告记录快照（供复核者本地重算哈希）。 |
| `scripts/kf_wp721601_register_assets.py` / `scripts/kf_wp721601_render_report.py` | 登记器与报告渲染器（build / envelope / verify / probe / figure / all）。 |

## ④ 证据定位表（资产 → 原文逐字定位）

引文取自 `asset_manifest.json` 的 `locator.quote`，即 `markdown[char_start:char_end]`；表中按 110 字符截断（长行以 `…` 标记），**逐字全文与字符区间在清单内**，可由 `md[char_start:char_end] == quote` 直接重解析（本次 40/40 通过）。

身份锚点：

| 量 | 值 | 契约 | 一致 |
|---|---|---|---|
| markdown sha256 | `sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b` | `sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b` | 是 |
| markdown chars | 11338 | 11338 | 是 |
| lines / bytes | 210 行 / 17984 B | —（契约未给） | n/a |
| title | `IN31-N12: LBM Rayleigh-Benard discrete linear stability + two-phase lambda/rho decoupling and Hadamard-Rybczynski comparison` | 同 | 是 |
| scenario_key | `lbm_rb_hr_validation` | 同 | 是 |

资产定位表：

| asset_id | class | resolution | 行 | 声明 token（原文形态） | 原文行（逐字，截断 110；反引号显示为 '） |
|---|---|---|---|---|---|
| `A01` | report_markdown | resolved_in_source | L1 | —（整字段） | # IN31-N12 · LBM Rayleigh–Bénard 离散线性稳定性 + 双相黏度比/密度比解耦与 Hadamard–Rybczynski 对拍 |
| `A02` | git_branch_reference | referenced_unresolved | L3 | `agent/m5628` | **节点**: IN31-N12（战役 DAG，物理域） · **仓库**: TensorLBM · **分支**: 'agent/m5628' |
| `A03` | api_symbol_reference | referenced_unresolved | L5 | `tensorlbm.rb_discrete_stability` | **结论速览**: (1) RB 起稳判据升级为**同一格子算子上的离散线性稳定性特征值**：本仓库新增 'tensorlbm.rb_discrete_stability'（矩阵无关 Jacobian + 谱），其主导特… |
| `A04` | directory_reference | referenced_unresolved | L13 | `benchmarks/pending/rayleigh_benard` | 格子与物理参数（与 'benchmarks/pending/rayleigh_benard' 的基准设置一致）：ν=(τ−1/2)/3=0.11833，α=(τ_T−1/2)/3=0.16667，Pr=ν/α=0.710… |
| `A05` | api_symbol_reference | referenced_unresolved | L13 | `thermal.buoyancy_force` | 格子与物理参数（与 'benchmarks/pending/rayleigh_benard' 的基准设置一致）：ν=(τ−1/2)/3=0.11833，α=(τ_T−1/2)/3=0.16667，Pr=ν/α=0.710… |
| `A06` | api_symbol_reference | referenced_unresolved | L13 | `thermal.collide_bgk_force` | 格子与物理参数（与 'benchmarks/pending/rayleigh_benard' 的基准设置一致）：ν=(τ−1/2)/3=0.11833，α=(τ_T−1/2)/3=0.16667，Pr=ν/α=0.710… |
| `A07` | api_symbol_reference | referenced_unresolved | L30 | `tensorlbm.hadamard_rybczynski` | λ→0 给出 Rybczynski 气泡（U=ΔρgR²/3μ_c），λ→∞ 给出 Stokes 固体球（U=2ΔρgR²/9μ_c）。本仓已有 'tensorlbm.hadamard_rybczynski'（解析律 +… |
| `A08` | source_code_reference | referenced_unresolved | L36 | `src/tensorlbm/rb_discrete_stability.py` | ### 2.1 离散线性稳定性求解器（新增 'src/tensorlbm/rb_discrete_stability.py'） |
| `A09` | api_symbol_reference | referenced_unresolved | L40 | `buoyancy_force` | 2. **Jacobian**：步进算子 = 库内原语组合（'temperature_collision'→'temperature_stream'→ABB 壁面→'buoyancy_force'→'collide_bg… |
| `A10` | api_symbol_reference | referenced_unresolved | L40 | `collide_bgk_force` | 2. **Jacobian**：步进算子 = 库内原语组合（'temperature_collision'→'temperature_stream'→ABB 壁面→'buoyancy_force'→'collide_bg… |
| `A11` | api_symbol_reference | referenced_unresolved | L40 | `pre_streaming_bounce_back` | 2. **Jacobian**：步进算子 = 库内原语组合（'temperature_collision'→'temperature_stream'→ABB 壁面→'buoyancy_force'→'collide_bg… |
| `A12` | api_symbol_reference | referenced_unresolved | L40 | `temperature_collision` | 2. **Jacobian**：步进算子 = 库内原语组合（'temperature_collision'→'temperature_stream'→ABB 壁面→'buoyancy_force'→'collide_bg… |
| `A13` | api_symbol_reference | referenced_unresolved | L40 | `temperature_stream` | 2. **Jacobian**：步进算子 = 库内原语组合（'temperature_collision'→'temperature_stream'→ABB 壁面→'buoyancy_force'→'collide_bg… |
| `A14` | source_code_reference | referenced_unresolved | L48 | `src/tensorlbm/rb_continuum_stability.py` | ### 2.2 连续谱参考（新增 'src/tensorlbm/rb_continuum_stability.py'） |
| `A15` | source_code_reference | referenced_unresolved | L62 | `src/tensorlbm/pseudopotential_hr.py` | ### 2.3 伪势双相 λ/ρ 解耦（新增 'src/tensorlbm/pseudopotential_hr.py'） |
| `A16` | api_symbol_reference | referenced_unresolved | L64 | `multiphase3d.collide_sc_two_component_3d` | - 单松弛 BGK 的单元动力黏度 μ=ρ c_s²(τ−1/2)。若两相同 τ，则 λ 被密度比锁死（λ=ρ_d/ρ_c）。双组分核 'multiphase3d.collide_sc_two_component_3d'… |
| `A17` | api_symbol_reference | referenced_unresolved | L67 | `two_phase_viscosity.shear_wave_decay` | - 解耦不是断言而是**测量**：对每个 (λ, ρ_d/ρ_c) 组合，用 'two_phase_viscosity.shear_wave_decay' 在真实 D2Q9 BGK 核上分别测两相的运动黏度，再按 μ=ρ… |
| `A18` | api_symbol_reference | referenced_unresolved | L69 | `collide_sc_two_component_3d` | - 已定位的库层缺口与补丁：'collide_sc_two_component_3d' 只接受**同一个** gz 给两个组分，无法表达"只给液滴加重力"（浮力问题的必需形式）。新增 'collide_two_compo… |
| `A19` | api_symbol_reference | referenced_unresolved | L69 | `collide_two_component_with_gravity(f1,f2,G_12,τ1,τ2,gz1,gz2,u_eq)` | - 已定位的库层缺口与补丁：'collide_sc_two_component_3d' 只接受**同一个** gz 给两个组分，无法表达"只给液滴加重力"（浮力问题的必需形式）。新增 'collide_two_compo… |
| `A20` | benchmark_script_reference | referenced_unresolved | L152 | `benchmarks/rb_discrete_stability/make_figures.py` | 见随报告提交的 PNG（全部由 'benchmarks/rb_discrete_stability/make_figures.py' 从 JSON 程序化生成）： |
| `A21` | figure_reference | referenced_unresolved | L154 | `rb_growth_rate.png` | - 'rb_growth_rate.png'：γ̂(Ra) 格子 vs 连续谱（等 Ra、等 a）；右图为相对差。 |
| `A22` | figure_reference | referenced_unresolved | L155 | `rb_ra_c_convergence.png` | - 'rb_ra_c_convergence.png'：Ra_c^lat 随 ny 的收敛与 (ny/(ny−1))³ 锚。 |
| `A23` | figure_reference | referenced_unresolved | L156 | `rb_eig_vs_sim.png` | - 'rb_eig_vs_sim.png'：特征值 γ 与非线性时间推进 γ 的对角一致性（±1% 带）。 |
| `A24` | figure_reference | referenced_unresolved | L157 | `rb_base_profile.png` | - 'rb_base_profile.png'：实测 H_eff=ny−1 证据。 |
| `A25` | figure_reference | referenced_unresolved | L158 | `hr_decoupling_settling.png` | - 'hr_decoupling_settling.png'：λ 解耦实测（左）与沉降速度 vs HR（右，含 honest FAIL）。 |
| `A26` | data_artifact_reference | referenced_unresolved | L198 | `artifacts/in31_n12/rb_lattice_nyN.json` | \| RB 生产（每分辨率） \| 'python benchmarks/rb_discrete_stability/run_bench.py --ny N' \| 'artifacts/in31_n12/rb_latt… |
| `A27` | benchmark_script_reference | referenced_unresolved | L198 | `benchmarks/rb_discrete_stability/run_bench.py` | \| RB 生产（每分辨率） \| 'python benchmarks/rb_discrete_stability/run_bench.py --ny N' \| 'artifacts/in31_n12/rb_latt… |
| `A28` | data_artifact_reference | referenced_unresolved | L199 | `artifacts/in31_n12/continuum.json` | \| RB 连续谱参考 \| 'critical_rayleigh_continuous(M_list=(50,100,200))' \| 'artifacts/in31_n12/continuum.json' \| |
| `A29` | api_symbol_reference | referenced_unresolved | L199 | `critical_rayleigh_continuous(M_list=(50,100,200))` | \| RB 连续谱参考 \| 'critical_rayleigh_continuous(M_list=(50,100,200))' \| 'artifacts/in31_n12/continuum.json' \| |
| `A30` | data_artifact_reference | referenced_unresolved | L200 | `artifacts/in31_n12/base_profile.json` | \| 基态/等效间隙诊断 \| 'conductive_base_state' 基态温度剖面拟合（见 'make_report' 说明） \| 'artifacts/in31_n12/base_profile.json'… |
| `A31` | api_symbol_reference | referenced_unresolved | L200 | `conductive_base_state` | \| 基态/等效间隙诊断 \| 'conductive_base_state' 基态温度剖面拟合（见 'make_report' 说明） \| 'artifacts/in31_n12/base_profile.json'… |
| `A32` | api_symbol_reference | referenced_unresolved | L200 | `make_report` | \| 基态/等效间隙诊断 \| 'conductive_base_state' 基态温度剖面拟合（见 'make_report' 说明） \| 'artifacts/in31_n12/base_profile.json'… |
| `A33` | data_artifact_reference | referenced_unresolved | L201 | `artifacts/in31_n12/hr_decoupling.json` | \| 双相解耦实测 \| 'python benchmarks/rb_discrete_stability/run_hr_bench.py --mode decoupling' \| 'artifacts/in31_n1… |
| `A34` | benchmark_script_reference | referenced_unresolved | L201 | `benchmarks/rb_discrete_stability/run_hr_bench.py` | \| 双相解耦实测 \| 'python benchmarks/rb_discrete_stability/run_hr_bench.py --mode decoupling' \| 'artifacts/in31_n1… |
| `A35` | data_artifact_reference | referenced_unresolved | L202 | `artifacts/in31_n12/hr_settling.json` | \| 双相沉降对拍 \| '... --mode settling' \| 'artifacts/in31_n12/hr_settling.json' \| |
| `A36` | data_artifact_reference | referenced_unresolved | L203 | `artifacts/in31_n12/criteria.json` | \| 图/判据汇总 \| 'python benchmarks/rb_discrete_stability/make_figures.py' \| 'figures/in31_n12/*.png', 'artifacts… |
| `A37` | figure_reference | referenced_unresolved | L203 | `figures/in31_n12/*.png` | \| 图/判据汇总 \| 'python benchmarks/rb_discrete_stability/make_figures.py' \| 'figures/in31_n12/*.png', 'artifacts… |
| `A38` | test_reference | referenced_unresolved | L204 | `tests/test_pseudopotential_hr.py` | \| 单测 \| 'pytest -q tests/test_rb_discrete_stability.py tests/test_pseudopotential_hr.py' \| – \| |
| `A39` | test_reference | referenced_unresolved | L204 | `tests/test_rb_discrete_stability.py` | \| 单测 \| 'pytest -q tests/test_rb_discrete_stability.py tests/test_pseudopotential_hr.py' \| – \| |
| `A40` | api_symbol_reference | referenced_unresolved | L210 | `tensorlbm.two_phase_viscosity` | - 'tensorlbm.hadamard_rybczynski'（解析律 + 轴对称有限元 Stokes）与 'tensorlbm.two_phase_viscosity'（λ/ρ 解耦映射）已存在且未修改；本节点的增… |

图引用与平台探测结果：

| figure | 平台图端点 | 结论 |
|---|---|---|
| `rb_growth_rate.png` | HTTP 404 | 声明在 `record.figures`，字节未提供（`{"detail":"figure not found"}`） |
| `rb_ra_c_convergence.png` | HTTP 404 | 声明在 `record.figures`，字节未提供（`{"detail":"figure not found"}`） |
| `rb_eig_vs_sim.png` | HTTP 404 | 声明在 `record.figures`，字节未提供（`{"detail":"figure not found"}`） |
| `rb_base_profile.png` | HTTP 404 | 声明在 `record.figures`，字节未提供（`{"detail":"figure not found"}`） |
| `hr_decoupling_settling.png` | HTTP 404 | 声明在 `record.figures`，字节未提供（`{"detail":"figure not found"}`） |
| `figures/in31_n12/*.png` | —（glob，不逐图探测） | glob 引用，无单一文件可哈希 |

## ⑤ 注意点与局限

1. **39/40 项资产未解析，这是结构性的、不是遗漏**：report 7216 的附件几乎全部属于 **TensorLBM** 仓（报告 §6 署名代码路径 `src/tensorlbm/...`、`benchmarks/rb_discrete_stability/...`、`artifacts/in31_n12/...`，分支 `agent/m5628`），而本工作包的交付仓是 **TensorKnowledge**。契约未授权跨仓取字节，因此一律 `referenced_unresolved` 并附上"查了哪里、为什么没命中"。任何把它们标成 `resolved` 的做法都只能是猜测。
2. **图的字节确实拿不到**：`record.figures` 声明了 5 张图，但 `GET /api/v1/tensor/reports/7216/figures/<name>` 全部返回 HTTP 404 `figure not found`。图只登记到"名字 + 声明来源 + 探测结果"，不伪造字节数或哈希。
3. **旁证探针内容漂移**：8/14 个声明路径在本地生态检出中被找到；其中内容哈希不唯一者 1 个（`rb_continuum_stability.py` → 2 种内容）；6 个 `artifacts/in31_n12/*.json` 在 0 个检出中出现。同一路径在不同检出里出现多种内容，说明"文件存在"无法定位到产出修订——这正是我不把它写进 `resolution` 的理由。
4. **扫描规则的假阳性已记录并修正**：首版把含空格的公式 `` `τ_d = 1/2 + λ (ρ_c/ρ_d)(τ_c−1/2)` `` 切出 `1/2` 当作路径登记（1 例）。改为"命令切分后必须带真实工件后缀"后该例消失；同时把 `agent/m5628`（产出分支）从"目录"纠正为 `git_branch_reference`，把 `Jv≈(F(x0+εv)−F(x0))/ε` 之类的表达式排除在路径字符集之外。当前 40 项资产经人工复核无残留假阳性。
5. **符号级引用是 declared-only**：`collide_two_component_with_gravity(f1,f2,G_12,τ1,τ2,gz1,gz2,u_eq)`、`critical_rayleigh_continuous(M_list=(50,100,200))` 等以报告原文形态登记（`symbol_key` 去掉实参供去重），本工序不打开产出仓验证其存在性。
6. **不越界**：未做抽取、未做报告类型判定、未改写上游产物、未触碰其它 `report_id`；`claims=[]` 且 `verified_marks_emitted=0`，是否 verified 由平台门独立计算。
7. **未运行项（如实标注）**：`psql` 直读 `tensor_reports.markdown` 被判 `permission denied for table tensor_reports`，故双通道校验记 `not_run`（不当作 PASS），API 是本次唯一取源通道；平台侧只探测了 figure 端点，artifact/attachment 端点未探测（因此不声称它们的可用性）。

## ⑥ 自检：逐条对照 acceptance

| 结果 | acceptance 项 | 证据 |
|---|---|---|
| ✅ PASS | `valid_json` | asset_manifest.json + kf_result.json parsed by json.loads |
| ✅ PASS | `schema_pass` | kf_result.v1.schema.json (Draft2020-12) errors=0; local asset_manifest.schema.json (Draft-07) errors=0 |
| ✅ PASS | `source_locator_resolvable` | 40/40 locators re-resolved on the live markdown (char span + verbatim + quote sha256) |
| ✅ PASS | `source_hash_matches` | live=sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b manifest=sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b co… |
| ✅ PASS | `no_duplicate_ids` | 40 ids / 40 keys; duplicate ids=[] duplicate keys=[] |
| ✅ PASS | `all_claims_have_evidence_or_explicit_unresolved_status` | 0 claims; every claim with evidence/unresolved: True; empty-claims reason stated: True |

### ⑥.1 误差判定（关键量 vs 基准，逐项回答"是否 <3%"）

| 关键量 | 基准 | 本工作 | 相对误差 | 是否 <3% |
|---|---|---|---|---|
| markdown sha256 | 契约 `source_hash` | 本地重算 | 0（逐字节相同） | **是** |
| markdown 字符数 | 契约 `chars=11338` | 11338 | 0% | **是** |
| 定位点可重解析 | 实时 markdown | 40/40 | 0% | **是** |
| 引文唯一性 | 源内唯一 | 40/40 | —（覆盖度，非误差量） | 不适用 |
| 资产解析率 | 无基线（跨仓字节不可得） | 1/40 | 不可判定 | 不适用（见 ⑤-1） |

**结论**：本工序的可判定量只有"身份一致"，两项（哈希、字符数）均为**逐字节 0 误差，<3% 成立**；资产解析率不存在基准，不做粉饰性判定。

```json
{
  "package_id": "wp-7216-01",
  "task_type": "01-asset-registration",
  "report_id": "7216",
  "provenance": {
    "source_hash": "sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b",
    "source_field": "markdown",
    "producer": "kf-worker/m15594",
    "emitted_at": "2026-11-12T01:30:05.603376+00:00",
    "notes": "hash recomputed locally from the UTF-8 bytes of the `markdown` field of GET /api/v1/tensor/reports/7216; equals the contract value sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "manifest_version": "1.0",
      "package_id": "wp-7216-01",
      "task_type": "01-asset-registration",
      "report_id": "7216",
      "lane": "C",
      "producer": "kf-worker/m15594",
      "generated_at": "2026-11-12T01:30:05.436212+00:00",
      "source": {
        "report_id": "7216",
        "source_uri": "tensor://reports/7216",
        "source_field": "markdown",
        "hash_alg": "sha256",
        "hash": "34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b",
        "source_hash": "sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b",
        "contract_source_hash": "sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b",
        "hash_match": true,
        "chars": 11338,
        "contract_chars": 11338,
        "chars_match_contract": true,
        "bytes_utf8": 17984,
        "lines": 210,
        "has_crlf": false,
        "has_trailing_newline": true,
        "line_counting": "1-based; logical lines = markdown.rstrip(chr(10)).split(chr(10)); char spans index the full markdown string",
        "fetched_via": "GET /api/v1/tensor/reports/7216",
        "title": "IN31-N12: LBM Rayleigh-Benard discrete linear stability + two-phase lambda/rho decoupling and Hadamard-Rybczynski comparison",
        "scenario_key": "lbm_rb_hr_validation",
        "mission_id": 5628,
        "status": "published",
        "created_at": "2026-11-07T16:09:38.005378+00:00",
        "tags": [
          "TensorLBM",
          "Rayleigh-Benard",
          "linear-stability",
          "pseudopotential",
          "Hadamard-Rybczynski",
          "IN31-N12"
        ],
        "contract_title": "IN31-N12: LBM Rayleigh-Benard discrete linear stability + two-phase lambda/rho decoupling and Hadamard-Rybczynski comparison",
        "contract_scenario_key": "lbm_rb_hr_validation",
        "title_matches_contract": true,
        "scenario_matches_contract": true,
        "platform_figures": [
          "hr_decoupling_settling.png",
          "rb_base_profile.png",
          "rb_eig_vs_sim.png",
          "rb_growth_rate.png",
          "rb_ra_c_convergence.png"
        ],
        "platform_tags": [
          "TensorLBM",
          "Rayleigh-Benard",
          "linear-stability",
          "pseudopotential",
          "Hadamard-Rybczynski",
          "IN31-N12"
        ]
      },
      "counts": {
        "assets": 40,
        "by_class": {
          "api_symbol_reference": 17,
          "benchmark_script_reference": 3,
          "data_artifact_reference": 6,
          "directory_reference": 1,
          "figure_reference": 6,
          "git_branch_reference": 1,
          "report_markdown": 1,
          "source_code_reference": 3,
          "test_reference": 2
        },
        "by_resolution": {
          "referenced_unresolved": 39,
          "resolved_in_source": 1
        },
        "resolved_in_source": 1,
        "referenced_unresolved": 39,
        "declared_absent": 0,
        "figure_declarations_in_prose": 6,
        "record_figures": 5
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_key": "report-7216:source-markdown",
          "asset_class": "report_markdown",
          "label": "report-7216-markdown",
          "in_report_section": "# IN31-N12 · LBM Rayleigh–Bénard 离散线性稳定性 + 双相黏度比/密度比解耦与 Hadamard–Rybczynski 对拍",
          "locator": {
            "method": "document",
            "source_field": "markdown",
            "char_start": 0,
            "char_end": 11338,
            "line_start": 1,
            "line_end": 210,
            "quote": "# IN31-N12 · LBM Rayleigh–Bénard 离散线性稳定性 + 双相黏度比/密度比解耦与 Hadamard–Rybczynski 对拍",
            "quote_sha256": "sha256:f69b9107e3ee932ec36cb639a333a713ba1bbd96d1d875a688ded83ac2aae033",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256(UTF-8 bytes) == contract source_hash",
            "result": "resolved"
          },
          "bytes": 17984,
          "chars": 11338,
          "lines": 210,
          "sha256": "sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b",
          "hash_scope": "UTF-8 bytes of the `markdown` field served by GET /api/v1/tensor/reports/7216",
          "local_copy": "runs/wp-7216-01/source_7216.md",
          "note": "source asset; hash recomputed locally and compared to the contract value"
        },
        {
          "asset_id": "A02",
          "asset_key": "report-7216:ref:agent/m5628",
          "asset_class": "git_branch_reference",
          "label": "branch",
          "token": "agent/m5628",
          "symbol_key": null,
          "form": "backticked_path",
          "in_report_section": "(before first ## heading)",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 80,
            "char_end": 152,
            "line_start": 3,
            "line_end": 3,
            "quote": "**节点**: IN31-N12（战役 DAG，物理域） · **仓库**: TensorLBM · **分支**: `agent/m5628`",
            "quote_sha256": "sha256:3d9bfb49ebb5031ebd3270bb59dd0af22e0934c7d70d7952d8b2110ab2644a45",
            "unique": true
          },
          "occurrence_lines": [
            3
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "git_branch_named_in_prose",
            "result": "unresolved",
            "note": "producing branch name only; this工序 does not query the LBM repository refs (out of contract scope)"
          },
          "note": "code/test/benchmark pointer declared in the report; bytes unavailable in this worktree"
        },
        {
          "asset_id": "A03",
          "asset_key": "report-7216:ref:tensorlbm.rb_discrete_stability",
          "asset_class": "api_symbol_reference",
          "label": "dotted_symbol",
          "token": "tensorlbm.rb_discrete_stability",
          "symbol_key": "tensorlbm.rb_discrete_stability",
          "form": "backticked_dotted",
          "in_report_section": "(before first ## heading)",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 154,
            "char_end": 634,
            "line_start": 5,
            "line_end": 5,
            "quote": "**结论速览**: (1) RB 起稳判据升级为**同一格子算子上的离散线性稳定性特征值**：本仓库新增 `tensorlbm.rb_discrete_stability`（矩阵无关 Jacobian + 谱），其主导特征值与真实非线性 LBM 时间推进的增长率在 ny=16/32 上一致到 **0.01% / 0.06%**（判据 <3% 通过）；离散临界 Rayleigh 数在 ny=16/32/64 上分别为 2687.3/2101.0/1883.6（相对 1707.76 上移 +57.36%/+23.03%/+10.30%）。(2) 双相伪势引擎**库层**已实现 λ=μ_d/μ_c 与 ρ_d/ρ_c 解耦（剪切波实测 λ 误差 ≤0.113%；λ 对密度比的斜率 ≈ 0）。(3) **LBM 端 Hadamard–Rybczynski 对拍 honest FAIL**：伪势双相液滴的沉降被界面寄生流（spurious current ~5e-2）完全淹没，与 HR 解析速度相差 3 个量级以上，未达 15% 判据——详见 §5、§6。",
            "quote_sha256": "sha256:ff74f8f8896a76c0e5da8441bca1d03d2471ac8d8a7e23c37763a29dd8daea7b",
            "unique": true
          },
          "occurrence_lines": [
            5
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "symbol_declared_in_markdown_no_byte_asset",
            "result": "unresolved",
            "note": "library symbol named in prose; registration does not open the producing repo (out of contract scope)"
          },
          "note": "declared library symbol / callable; this工序 registers the pointer only and does not read the producing repository"
        },
        {
          "asset_id": "A04",
          "asset_key": "report-7216:ref:benchmarks/pending/rayleigh_benard",
          "asset_class": "directory_reference",
          "label": "directory",
          "token": "benchmarks/pending/rayleigh_benard",
          "symbol_key": null,
          "form": "backticked_path",
          "in_report_section": "### 1.1 Rayleigh–Bénard 起稳（2D，刚–刚等温壁）",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 899,
            "char_end": 1215,
            "line_start": 13,
            "line_end": 13,
            "quote": "格子与物理参数（与 `benchmarks/pending/rayleigh_benard` 的基准设置一致）：ν=(τ−1/2)/3=0.11833，α=(τ_T−1/2)/3=0.16667，Pr=ν/α=0.7100，间隙 H=ny（benchmark 约定），水平周期长度 nx=2ny（单卷，a=2πH/nx=π≈3.1416）。Boussinesq 浮力用 Guo 力格式（`thermal.buoyancy_force` + `thermal.collide_bgk_force`），温度用 D2Q5 + 上下壁 anti-bounce-back（ABB），速度用 D2Q9 + pre-streaming 半程反弹。",
            "quote_sha256": "sha256:6437715523ce4cdd0125f7f9e005d8f3d27a9715f8e87a3d828458a941150863",
            "unique": true
          },
          "occurrence_lines": [
            13
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_delivery_worktree",
            "result": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report 7216 is a TensorLBM asset, repo layering=LBM|research|A)",
            "same_basename_hits": []
          },
          "note": "directory/glob reference; no single file to hash"
        },
        {
          "asset_id": "A05",
          "asset_key": "report-7216:ref:thermal.buoyancy_force",
          "asset_class": "api_symbol_reference",
          "label": "dotted_symbol",
          "token": "thermal.buoyancy_force",
          "symbol_key": "thermal.buoyancy_force",
          "form": "backticked_dotted",
          "in_report_section": "### 1.1 Rayleigh–Bénard 起稳（2D，刚–刚等温壁）",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 899,
            "char_end": 1215,
            "line_start": 13,
            "line_end": 13,
            "quote": "格子与物理参数（与 `benchmarks/pending/rayleigh_benard` 的基准设置一致）：ν=(τ−1/2)/3=0.11833，α=(τ_T−1/2)/3=0.16667，Pr=ν/α=0.7100，间隙 H=ny（benchmark 约定），水平周期长度 nx=2ny（单卷，a=2πH/nx=π≈3.1416）。Boussinesq 浮力用 Guo 力格式（`thermal.buoyancy_force` + `thermal.collide_bgk_force`），温度用 D2Q5 + 上下壁 anti-bounce-back（ABB），速度用 D2Q9 + pre-streaming 半程反弹。",
            "quote_sha256": "sha256:6437715523ce4cdd0125f7f9e005d8f3d27a9715f8e87a3d828458a941150863",
            "unique": true
          },
          "occurrence_lines": [
            13
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "symbol_declared_in_markdown_no_byte_asset",
            "result": "unresolved",
            "note": "library symbol named in prose; registration does not open the producing repo (out of contract scope)"
          },
          "note": "declared library symbol / callable; this工序 registers the pointer only and does not read the producing repository"
        },
        {
          "asset_id": "A06",
          "asset_key": "report-7216:ref:thermal.collide_bgk_force",
          "asset_class": "api_symbol_reference",
          "label": "dotted_symbol",
          "token": "thermal.collide_bgk_force",
          "symbol_key": "thermal.collide_bgk_force",
          "form": "backticked_dotted",
          "in_report_section": "### 1.1 Rayleigh–Bénard 起稳（2D，刚–刚等温壁）",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 899,
            "char_end": 1215,
            "line_start": 13,
            "line_end": 13,
            "quote": "格子与物理参数（与 `benchmarks/pending/rayleigh_benard` 的基准设置一致）：ν=(τ−1/2)/3=0.11833，α=(τ_T−1/2)/3=0.16667，Pr=ν/α=0.7100，间隙 H=ny（benchmark 约定），水平周期长度 nx=2ny（单卷，a=2πH/nx=π≈3.1416）。Boussinesq 浮力用 Guo 力格式（`thermal.buoyancy_force` + `thermal.collide_bgk_force`），温度用 D2Q5 + 上下壁 anti-bounce-back（ABB），速度用 D2Q9 + pre-streaming 半程反弹。",
            "quote_sha256": "sha256:6437715523ce4cdd0125f7f9e005d8f3d27a9715f8e87a3d828458a941150863",
            "unique": true
          },
          "occurrence_lines": [
            13
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "symbol_declared_in_markdown_no_byte_asset",
            "result": "unresolved",
            "note": "library symbol named in prose; registration does not open the producing repo (out of contract scope)"
          },
          "note": "declared library symbol / callable; this工序 registers the pointer only and does not read the producing repository"
        },
        {
          "asset_id": "A07",
          "asset_key": "report-7216:ref:tensorlbm.hadamard_rybczynski",
          "asset_class": "api_symbol_reference",
          "label": "dotted_symbol",
          "token": "tensorlbm.hadamard_rybczynski",
          "symbol_key": "tensorlbm.hadamard_rybczynski",
          "form": "backticked_dotted",
          "in_report_section": "### 1.2 双相液滴沉降（Hadamard–Rybczynski）",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 1635,
            "char_end": 1844,
            "line_start": 30,
            "line_end": 30,
            "quote": "λ→0 给出 Rybczynski 气泡（U=ΔρgR²/3μ_c），λ→∞ 给出 Stokes 固体球（U=2ΔρgR²/9μ_c）。本仓已有 `tensorlbm.hadamard_rybczynski`（解析律 + 轴对称有限元 Stokes 求解器，属**已验收**的解析/有限元验证，本节点不重复）；本节点的对象是**伪势（Shan–Chen）双相 LBM 引擎**能否独立设定 λ 与 ρ 比并按该律沉降。",
            "quote_sha256": "sha256:c261e2b442985caadba19306fa0fd386a071be328d2986ac61a314004575df97",
            "unique": true
          },
          "occurrence_lines": [
            30,
            210
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "symbol_declared_in_markdown_no_byte_asset",
            "result": "unresolved",
            "note": "library symbol named in prose; registration does not open the producing repo (out of contract scope)"
          },
          "note": "declared library symbol / callable; this工序 registers the pointer only and does not read the producing repository"
        },
        {
          "asset_id": "A08",
          "asset_key": "report-7216:ref:src/tensorlbm/rb_discrete_stability.py",
          "asset_class": "source_code_reference",
          "label": "source_module",
          "token": "src/tensorlbm/rb_discrete_stability.py",
          "symbol_key": null,
          "form": "backticked_path",
          "in_report_section": "### 2.1 离散线性稳定性求解器（新增 `src/tensorlbm/rb_discrete_stability.py`）",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 1992,
            "char_end": 2055,
            "line_start": 36,
            "line_end": 36,
            "quote": "### 2.1 离散线性稳定性求解器（新增 `src/tensorlbm/rb_discrete_stability.py`）",
            "quote_sha256": "sha256:65634013618db8ecebf28db038a59da2461d0c44c0bcbab3490d6605bb3e74c0",
            "unique": true
          },
          "occurrence_lines": [
            36,
            206
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_delivery_worktree",
            "result": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report 7216 is a TensorLBM asset, repo layering=LBM|research|A)",
            "same_basename_hits": []
          },
          "note": "code/test/benchmark pointer declared in the report; bytes unavailable in this worktree"
        },
        {
          "asset_id": "A09",
          "asset_key": "report-7216:ref:buoyancy_force",
          "asset_class": "api_symbol_reference",
          "label": "identifier",
          "token": "buoyancy_force",
          "symbol_key": "buoyancy_force",
          "form": "backticked_identifier",
          "in_report_section": "### 2.1 离散线性稳定性求解器（新增 `src/tensorlbm/rb_discrete_stability.py`）",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 2231,
            "char_end": 2499,
            "line_start": 40,
            "line_end": 40,
            "quote": "2. **Jacobian**：步进算子 = 库内原语组合（`temperature_collision`→`temperature_stream`→ABB 壁面→`buoyancy_force`→`collide_bgk_force`(Guo)→`pre_streaming_bounce_back`→`stream`），与 benchmark 主循环逐步同序。Jacobian 用 float64 有限差分 `Jv≈(F(x0+εv)−F(x0))/ε`（ε=1e-6）**矩阵无关**求取，因此不存在\"手推算子与代码脱节\"的风险。",
            "quote_sha256": "sha256:ce10ee0e87f37f24b74ec4593675ef03aedadcf54ed2591bc8009c16abfbeec0",
            "unique": true
          },
          "occurrence_lines": [
            40
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "symbol_declared_in_markdown_no_byte_asset",
            "result": "unresolved",
            "note": "library symbol named in prose; registration does not open the producing repo (out of contract scope)"
          },
          "note": "declared library symbol / callable; this工序 registers the pointer only and does not read the producing repository"
        },
        {
          "asset_id": "A10",
          "asset_key": "report-7216:ref:collide_bgk_force",
          "asset_class": "api_symbol_reference",
          "label": "identifier",
          "token": "collide_bgk_force",
          "symbol_key": "collide_bgk_force",
          "form": "backticked_identifier",
          "in_report_section": "### 2.1 离散线性稳定性求解器（新增 `src/tensorlbm/rb_discrete_stability.py`）",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 2231,
            "char_end": 2499,
            "line_start": 40,
            "line_end": 40,
            "quote": "2. **Jacobian**：步进算子 = 库内原语组合（`temperature_collision`→`temperature_stream`→ABB 壁面→`buoyancy_force`→`collide_bgk_force`(Guo)→`pre_streaming_bounce_back`→`stream`），与 benchmark 主循环逐步同序。Jacobian 用 float64 有限差分 `Jv≈(F(x0+εv)−F(x0))/ε`（ε=1e-6）**矩阵无关**求取，因此不存在\"手推算子与代码脱节\"的风险。",
            "quote_sha256": "sha256:ce10ee0e87f37f24b74ec4593675ef03aedadcf54ed2591bc8009c16abfbeec0",
            "unique": true
          },
          "occurrence_lines": [
            40
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "symbol_declared_in_markdown_no_byte_asset",
            "result": "unresolved",
            "note": "library symbol named in prose; registration does not open the producing repo (out of contract scope)"
          },
          "note": "declared library symbol / callable; this工序 registers the pointer only and does not read the producing repository"
        },
        {
          "asset_id": "A11",
          "asset_key": "report-7216:ref:pre_streaming_bounce_back",
          "asset_class": "api_symbol_reference",
          "label": "identifier",
          "token": "pre_streaming_bounce_back",
          "symbol_key": "pre_streaming_bounce_back",
          "form": "backticked_identifier",
          "in_report_section": "### 2.1 离散线性稳定性求解器（新增 `src/tensorlbm/rb_discrete_stability.py`）",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 2231,
            "char_end": 2499,
            "line_start": 40,
            "line_end": 40,
            "quote": "2. **Jacobian**：步进算子 = 库内原语组合（`temperature_collision`→`temperature_stream`→ABB 壁面→`buoyancy_force`→`collide_bgk_force`(Guo)→`pre_streaming_bounce_back`→`stream`），与 benchmark 主循环逐步同序。Jacobian 用 float64 有限差分 `Jv≈(F(x0+εv)−F(x0))/ε`（ε=1e-6）**矩阵无关**求取，因此不存在\"手推算子与代码脱节\"的风险。",
            "quote_sha256": "sha256:ce10ee0e87f37f24b74ec4593675ef03aedadcf54ed2591bc8009c16abfbeec0",
            "unique": true
          },
          "occurrence_lines": [
            40
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "symbol_declared_in_markdown_no_byte_asset",
            "result": "unresolved",
            "note": "library symbol named in prose; registration does not open the producing repo (out of contract scope)"
          },
          "note": "declared library symbol / callable; this工序 registers the pointer only and does not read the producing repository"
        },
        {
          "asset_id": "A12",
          "asset_key": "report-7216:ref:temperature_collision",
          "asset_class": "api_symbol_reference",
          "label": "identifier",
          "token": "temperature_collision",
          "symbol_key": "temperature_collision",
          "form": "backticked_identifier",
          "in_report_section": "### 2.1 离散线性稳定性求解器（新增 `src/tensorlbm/rb_discrete_stability.py`）",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 2231,
            "char_end": 2499,
            "line_start": 40,
            "line_end": 40,
            "quote": "2. **Jacobian**：步进算子 = 库内原语组合（`temperature_collision`→`temperature_stream`→ABB 壁面→`buoyancy_force`→`collide_bgk_force`(Guo)→`pre_streaming_bounce_back`→`stream`），与 benchmark 主循环逐步同序。Jacobian 用 float64 有限差分 `Jv≈(F(x0+εv)−F(x0))/ε`（ε=1e-6）**矩阵无关**求取，因此不存在\"手推算子与代码脱节\"的风险。",
            "quote_sha256": "sha256:ce10ee0e87f37f24b74ec4593675ef03aedadcf54ed2591bc8009c16abfbeec0",
            "unique": true
          },
          "occurrence_lines": [
            40
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "symbol_declared_in_markdown_no_byte_asset",
            "result": "unresolved",
            "note": "library symbol named in prose; registration does not open the producing repo (out of contract scope)"
          },
          "note": "declared library symbol / callable; this工序 registers the pointer only and does not read the producing repository"
        },
        {
          "asset_id": "A13",
          "asset_key": "report-7216:ref:temperature_stream",
          "asset_class": "api_symbol_reference",
          "label": "identifier",
          "token": "temperature_stream",
          "symbol_key": "temperature_stream",
          "form": "backticked_identifier",
          "in_report_section": "### 2.1 离散线性稳定性求解器（新增 `src/tensorlbm/rb_discrete_stability.py`）",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 2231,
            "char_end": 2499,
            "line_start": 40,
            "line_end": 40,
            "quote": "2. **Jacobian**：步进算子 = 库内原语组合（`temperature_collision`→`temperature_stream`→ABB 壁面→`buoyancy_force`→`collide_bgk_force`(Guo)→`pre_streaming_bounce_back`→`stream`），与 benchmark 主循环逐步同序。Jacobian 用 float64 有限差分 `Jv≈(F(x0+εv)−F(x0))/ε`（ε=1e-6）**矩阵无关**求取，因此不存在\"手推算子与代码脱节\"的风险。",
            "quote_sha256": "sha256:ce10ee0e87f37f24b74ec4593675ef03aedadcf54ed2591bc8009c16abfbeec0",
            "unique": true
          },
          "occurrence_lines": [
            40
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "symbol_declared_in_markdown_no_byte_asset",
            "result": "unresolved",
            "note": "library symbol named in prose; registration does not open the producing repo (out of contract scope)"
          },
          "note": "declared library symbol / callable; this工序 registers the pointer only and does not read the producing repository"
        },
        {
          "asset_id": "A14",
          "asset_key": "report-7216:ref:src/tensorlbm/rb_continuum_stability.py",
          "asset_class": "source_code_reference",
          "label": "source_module",
          "token": "src/tensorlbm/rb_continuum_stability.py",
          "symbol_key": null,
          "form": "backticked_path",
          "in_report_section": "### 2.2 连续谱参考（新增 `src/tensorlbm/rb_continuum_stability.py`）",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 2971,
            "char_end": 3030,
            "line_start": 48,
            "line_end": 48,
            "quote": "### 2.2 连续谱参考（新增 `src/tensorlbm/rb_continuum_stability.py`）",
            "quote_sha256": "sha256:49ef15620aa61fbad59c3a90fbad62129d69995853cb9e616fc095f1bdbfce07",
            "unique": true
          },
          "occurrence_lines": [
            48,
            206
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_delivery_worktree",
            "result": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report 7216 is a TensorLBM asset, repo layering=LBM|research|A)",
            "same_basename_hits": []
          },
          "note": "code/test/benchmark pointer declared in the report; bytes unavailable in this worktree"
        },
        {
          "asset_id": "A15",
          "asset_key": "report-7216:ref:src/tensorlbm/pseudopotential_hr.py",
          "asset_class": "source_code_reference",
          "label": "source_module",
          "token": "src/tensorlbm/pseudopotential_hr.py",
          "symbol_key": null,
          "form": "backticked_path",
          "in_report_section": "### 2.3 伪势双相 λ/ρ 解耦（新增 `src/tensorlbm/pseudopotential_hr.py`）",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 3606,
            "char_end": 3667,
            "line_start": 62,
            "line_end": 62,
            "quote": "### 2.3 伪势双相 λ/ρ 解耦（新增 `src/tensorlbm/pseudopotential_hr.py`）",
            "quote_sha256": "sha256:c07d30edd16a8d078aead1933c17f1bc06741a02591e05db78609dbd06f389f2",
            "unique": true
          },
          "occurrence_lines": [
            62,
            206
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_delivery_worktree",
            "result": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report 7216 is a TensorLBM asset, repo layering=LBM|research|A)",
            "same_basename_hits": []
          },
          "note": "code/test/benchmark pointer declared in the report; bytes unavailable in this worktree"
        },
        {
          "asset_id": "A16",
          "asset_key": "report-7216:ref:multiphase3d.collide_sc_two_component_3d",
          "asset_class": "api_symbol_reference",
          "label": "dotted_symbol",
          "token": "multiphase3d.collide_sc_two_component_3d",
          "symbol_key": "multiphase3d.collide_sc_two_component_3d",
          "form": "backticked_dotted",
          "in_report_section": "### 2.3 伪势双相 λ/ρ 解耦（新增 `src/tensorlbm/pseudopotential_hr.py`）",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 3669,
            "char_end": 3794,
            "line_start": 64,
            "line_end": 64,
            "quote": "- 单松弛 BGK 的单元动力黏度 μ=ρ c_s²(τ−1/2)。若两相同 τ，则 λ 被密度比锁死（λ=ρ_d/ρ_c）。双组分核 `multiphase3d.collide_sc_two_component_3d` 对每个组分独立给 τ，故可由",
            "quote_sha256": "sha256:791aac0ff848facac7673fc3675e3556aab7244d3e2b9f4c3464498a8bc0a506",
            "unique": true
          },
          "occurrence_lines": [
            64
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "symbol_declared_in_markdown_no_byte_asset",
            "result": "unresolved",
            "note": "library symbol named in prose; registration does not open the producing repo (out of contract scope)"
          },
          "note": "declared library symbol / callable; this工序 registers the pointer only and does not read the producing repository"
        },
        {
          "asset_id": "A17",
          "asset_key": "report-7216:ref:two_phase_viscosity.shear_wave_decay",
          "asset_class": "api_symbol_reference",
          "label": "dotted_symbol",
          "token": "two_phase_viscosity.shear_wave_decay",
          "symbol_key": "two_phase_viscosity.shear_wave_decay",
          "form": "backticked_dotted",
          "in_report_section": "### 2.3 伪势双相 λ/ρ 解耦（新增 `src/tensorlbm/pseudopotential_hr.py`）",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 3854,
            "char_end": 3989,
            "line_start": 67,
            "line_end": 67,
            "quote": "- 解耦不是断言而是**测量**：对每个 (λ, ρ_d/ρ_c) 组合，用 `two_phase_viscosity.shear_wave_decay` 在真实 D2Q9 BGK 核上分别测两相的运动黏度，再按 μ=ρν 组成 λ_measured，与给定 λ 比较。",
            "quote_sha256": "sha256:5e805e0a969c761490030b0af226f3a333ef3b607dc71a278aa0e963f789470e",
            "unique": true
          },
          "occurrence_lines": [
            67
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "symbol_declared_in_markdown_no_byte_asset",
            "result": "unresolved",
            "note": "library symbol named in prose; registration does not open the producing repo (out of contract scope)"
          },
          "note": "declared library symbol / callable; this工序 registers the pointer only and does not read the producing repository"
        },
        {
          "asset_id": "A18",
          "asset_key": "report-7216:ref:collide_sc_two_component_3d",
          "asset_class": "api_symbol_reference",
          "label": "identifier",
          "token": "collide_sc_two_component_3d",
          "symbol_key": "collide_sc_two_component_3d",
          "form": "backticked_identifier",
          "in_report_section": "### 2.3 伪势双相 λ/ρ 解耦（新增 `src/tensorlbm/pseudopotential_hr.py`）",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 3991,
            "char_end": 4214,
            "line_start": 69,
            "line_end": 69,
            "quote": "- 已定位的库层缺口与补丁：`collide_sc_two_component_3d` 只接受**同一个** gz 给两个组分，无法表达\"只给液滴加重力\"（浮力问题的必需形式）。新增 `collide_two_component_with_gravity(f1,f2,G_12,τ1,τ2,gz1,gz2,u_eq)` 按库内约定逐组分施力，并用单测证明：当 gz1=gz2 且 τ 相同/不同时它**逐位等于**库内核（max|Δ|=0.0）。",
            "quote_sha256": "sha256:aec3d8638d582e74ffcb5a3403895cc86e07b6fd93a7d1b00d91b9054610850f",
            "unique": true
          },
          "occurrence_lines": [
            69
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "symbol_declared_in_markdown_no_byte_asset",
            "result": "unresolved",
            "note": "library symbol named in prose; registration does not open the producing repo (out of contract scope)"
          },
          "note": "declared library symbol / callable; this工序 registers the pointer only and does not read the producing repository"
        },
        {
          "asset_id": "A19",
          "asset_key": "report-7216:ref:collide_two_component_with_gravity",
          "asset_class": "api_symbol_reference",
          "label": "callable",
          "token": "collide_two_component_with_gravity(f1,f2,G_12,τ1,τ2,gz1,gz2,u_eq)",
          "symbol_key": "collide_two_component_with_gravity",
          "form": "backticked_call",
          "in_report_section": "### 2.3 伪势双相 λ/ρ 解耦（新增 `src/tensorlbm/pseudopotential_hr.py`）",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 3991,
            "char_end": 4214,
            "line_start": 69,
            "line_end": 69,
            "quote": "- 已定位的库层缺口与补丁：`collide_sc_two_component_3d` 只接受**同一个** gz 给两个组分，无法表达\"只给液滴加重力\"（浮力问题的必需形式）。新增 `collide_two_component_with_gravity(f1,f2,G_12,τ1,τ2,gz1,gz2,u_eq)` 按库内约定逐组分施力，并用单测证明：当 gz1=gz2 且 τ 相同/不同时它**逐位等于**库内核（max|Δ|=0.0）。",
            "quote_sha256": "sha256:aec3d8638d582e74ffcb5a3403895cc86e07b6fd93a7d1b00d91b9054610850f",
            "unique": true
          },
          "occurrence_lines": [
            69
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "symbol_declared_in_markdown_no_byte_asset",
            "result": "unresolved",
            "note": "library symbol named in prose; registration does not open the producing repo (out of contract scope)"
          },
          "note": "declared library symbol / callable; this工序 registers the pointer only and does not read the producing repository"
        },
        {
          "asset_id": "A20",
          "asset_key": "report-7216:ref:benchmarks/rb_discrete_stability/make_figures.py",
          "asset_class": "benchmark_script_reference",
          "label": "benchmark_script",
          "token": "benchmarks/rb_discrete_stability/make_figures.py",
          "symbol_key": null,
          "form": "backticked_path",
          "in_report_section": "### 3.6 图",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 7436,
            "char_end": 7517,
            "line_start": 152,
            "line_end": 152,
            "quote": "见随报告提交的 PNG（全部由 `benchmarks/rb_discrete_stability/make_figures.py` 从 JSON 程序化生成）：",
            "quote_sha256": "sha256:df39024ee061317aa25077a72664bdf278ee2507ac2839ca7d0858bfd3f80da8",
            "unique": true
          },
          "occurrence_lines": [
            152,
            203
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_delivery_worktree",
            "result": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report 7216 is a TensorLBM asset, repo layering=LBM|research|A)",
            "same_basename_hits": [
              "demos/ke_eval/make_figures.py"
            ]
          },
          "note": "code/test/benchmark pointer declared in the report; bytes unavailable in this worktree"
        },
        {
          "asset_id": "A21",
          "asset_key": "report-7216:ref:rb_growth_rate.png",
          "asset_class": "figure_reference",
          "label": "figure",
          "token": "rb_growth_rate.png",
          "symbol_key": null,
          "form": "backticked_path",
          "in_report_section": "### 3.6 图",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 7519,
            "char_end": 7576,
            "line_start": 154,
            "line_end": 154,
            "quote": "- `rb_growth_rate.png`：γ̂(Ra) 格子 vs 连续谱（等 Ra、等 a）；右图为相对差。",
            "quote_sha256": "sha256:d7f58acfbd9ce9dd27d0244ed405b80c249b7a88e968c3db411273c080fd26e6",
            "unique": true
          },
          "occurrence_lines": [
            154
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform_figure_endpoint",
            "result": "unresolved",
            "http_status": 404,
            "detail": "{\"detail\":\"figure not found\"}",
            "endpoint": "GET /api/v1/tensor/reports/7216/figures/rb_growth_rate.png",
            "note": "declared in record.figures, bytes not served by the platform"
          },
          "note": "figure bytes are not served by the platform figure endpoint; identity is the record.figures declaration plus the prose reference (probe recorded in resolution_check)"
        },
        {
          "asset_id": "A22",
          "asset_key": "report-7216:ref:rb_ra_c_convergence.png",
          "asset_class": "figure_reference",
          "label": "figure",
          "token": "rb_ra_c_convergence.png",
          "symbol_key": null,
          "form": "backticked_path",
          "in_report_section": "### 3.6 图",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 7577,
            "char_end": 7639,
            "line_start": 155,
            "line_end": 155,
            "quote": "- `rb_ra_c_convergence.png`：Ra_c^lat 随 ny 的收敛与 (ny/(ny−1))³ 锚。",
            "quote_sha256": "sha256:543deeeb578fcd90fa724b172a3cadda0918cde5d2e1d5a483d784339e323ed5",
            "unique": true
          },
          "occurrence_lines": [
            155
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform_figure_endpoint",
            "result": "unresolved",
            "http_status": 404,
            "detail": "{\"detail\":\"figure not found\"}",
            "endpoint": "GET /api/v1/tensor/reports/7216/figures/rb_ra_c_convergence.png",
            "note": "declared in record.figures, bytes not served by the platform"
          },
          "note": "figure bytes are not served by the platform figure endpoint; identity is the record.figures declaration plus the prose reference (probe recorded in resolution_check)"
        },
        {
          "asset_id": "A23",
          "asset_key": "report-7216:ref:rb_eig_vs_sim.png",
          "asset_class": "figure_reference",
          "label": "figure",
          "token": "rb_eig_vs_sim.png",
          "symbol_key": null,
          "form": "backticked_path",
          "in_report_section": "### 3.6 图",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 7640,
            "char_end": 7693,
            "line_start": 156,
            "line_end": 156,
            "quote": "- `rb_eig_vs_sim.png`：特征值 γ 与非线性时间推进 γ 的对角一致性（±1% 带）。",
            "quote_sha256": "sha256:9f090f0ac16bf158456bb1dea3a9f58daa59ba3af8525c9ab2b887bf95b7a044",
            "unique": true
          },
          "occurrence_lines": [
            156
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform_figure_endpoint",
            "result": "unresolved",
            "http_status": 404,
            "detail": "{\"detail\":\"figure not found\"}",
            "endpoint": "GET /api/v1/tensor/reports/7216/figures/rb_eig_vs_sim.png",
            "note": "declared in record.figures, bytes not served by the platform"
          },
          "note": "figure bytes are not served by the platform figure endpoint; identity is the record.figures declaration plus the prose reference (probe recorded in resolution_check)"
        },
        {
          "asset_id": "A24",
          "asset_key": "report-7216:ref:rb_base_profile.png",
          "asset_class": "figure_reference",
          "label": "figure",
          "token": "rb_base_profile.png",
          "symbol_key": null,
          "form": "backticked_path",
          "in_report_section": "### 3.6 图",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 7694,
            "char_end": 7735,
            "line_start": 157,
            "line_end": 157,
            "quote": "- `rb_base_profile.png`：实测 H_eff=ny−1 证据。",
            "quote_sha256": "sha256:d65d8317f6d0a424bbc0a467ef2323542ecaa38e5fb6f0a371cafb60af2e5d19",
            "unique": true
          },
          "occurrence_lines": [
            157
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform_figure_endpoint",
            "result": "unresolved",
            "http_status": 404,
            "detail": "{\"detail\":\"figure not found\"}",
            "endpoint": "GET /api/v1/tensor/reports/7216/figures/rb_base_profile.png",
            "note": "declared in record.figures, bytes not served by the platform"
          },
          "note": "figure bytes are not served by the platform figure endpoint; identity is the record.figures declaration plus the prose reference (probe recorded in resolution_check)"
        },
        {
          "asset_id": "A25",
          "asset_key": "report-7216:ref:hr_decoupling_settling.png",
          "asset_class": "figure_reference",
          "label": "figure",
          "token": "hr_decoupling_settling.png",
          "symbol_key": null,
          "form": "backticked_path",
          "in_report_section": "### 3.6 图",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 7736,
            "char_end": 7805,
            "line_start": 158,
            "line_end": 158,
            "quote": "- `hr_decoupling_settling.png`：λ 解耦实测（左）与沉降速度 vs HR（右，含 honest FAIL）。",
            "quote_sha256": "sha256:68503c5405cd89186afecdfcb6679230e3d53584d6d989bdbaec104c5492cf7b",
            "unique": true
          },
          "occurrence_lines": [
            158,
            192
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform_figure_endpoint",
            "result": "unresolved",
            "http_status": 404,
            "detail": "{\"detail\":\"figure not found\"}",
            "endpoint": "GET /api/v1/tensor/reports/7216/figures/hr_decoupling_settling.png",
            "note": "declared in record.figures, bytes not served by the platform"
          },
          "note": "figure bytes are not served by the platform figure endpoint; identity is the record.figures declaration plus the prose reference (probe recorded in resolution_check)"
        },
        {
          "asset_id": "A26",
          "asset_key": "report-7216:ref:artifacts/in31_n12/rb_lattice_nyN.json",
          "asset_class": "data_artifact_reference",
          "label": "data_artifact",
          "token": "artifacts/in31_n12/rb_lattice_nyN.json",
          "symbol_key": null,
          "form": "backticked_path",
          "in_report_section": "## 6. 审计链与产物路径",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 10165,
            "char_end": 10287,
            "line_start": 198,
            "line_end": 198,
            "quote": "| RB 生产（每分辨率） | `python benchmarks/rb_discrete_stability/run_bench.py --ny N` | `artifacts/in31_n12/rb_lattice_nyN.json` |",
            "quote_sha256": "sha256:6538d3b72dff6b81a546c4404848dc129704ad4cb81ca9c2abe14d191e8d0fd3",
            "unique": true
          },
          "occurrence_lines": [
            198
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_delivery_worktree",
            "result": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report 7216 is a TensorLBM asset, repo layering=LBM|research|A)",
            "same_basename_hits": []
          },
          "note": "artifact produced outside this repository (evidence chain §6 of the report); bytes unavailable in the delivery worktree"
        },
        {
          "asset_id": "A27",
          "asset_key": "report-7216:ref:benchmarks/rb_discrete_stability/run_bench.py",
          "asset_class": "benchmark_script_reference",
          "label": "benchmark_script",
          "token": "benchmarks/rb_discrete_stability/run_bench.py",
          "symbol_key": null,
          "form": "path_in_backticked_command",
          "in_report_section": "## 6. 审计链与产物路径",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 10165,
            "char_end": 10287,
            "line_start": 198,
            "line_end": 198,
            "quote": "| RB 生产（每分辨率） | `python benchmarks/rb_discrete_stability/run_bench.py --ny N` | `artifacts/in31_n12/rb_lattice_nyN.json` |",
            "quote_sha256": "sha256:6538d3b72dff6b81a546c4404848dc129704ad4cb81ca9c2abe14d191e8d0fd3",
            "unique": true
          },
          "occurrence_lines": [
            198
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_delivery_worktree",
            "result": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report 7216 is a TensorLBM asset, repo layering=LBM|research|A)",
            "same_basename_hits": []
          },
          "note": "code/test/benchmark pointer declared in the report; bytes unavailable in this worktree"
        },
        {
          "asset_id": "A28",
          "asset_key": "report-7216:ref:artifacts/in31_n12/continuum.json",
          "asset_class": "data_artifact_reference",
          "label": "data_artifact",
          "token": "artifacts/in31_n12/continuum.json",
          "symbol_key": null,
          "form": "backticked_path",
          "in_report_section": "## 6. 审计链与产物路径",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 10288,
            "char_end": 10392,
            "line_start": 199,
            "line_end": 199,
            "quote": "| RB 连续谱参考 | `critical_rayleigh_continuous(M_list=(50,100,200))` | `artifacts/in31_n12/continuum.json` |",
            "quote_sha256": "sha256:a1dad22171425194d7fc9596d92afbeaad974edac34e7a6e3d46766f262edfee",
            "unique": true
          },
          "occurrence_lines": [
            199
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_delivery_worktree",
            "result": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report 7216 is a TensorLBM asset, repo layering=LBM|research|A)",
            "same_basename_hits": []
          },
          "note": "artifact produced outside this repository (evidence chain §6 of the report); bytes unavailable in the delivery worktree"
        },
        {
          "asset_id": "A29",
          "asset_key": "report-7216:ref:critical_rayleigh_continuous",
          "asset_class": "api_symbol_reference",
          "label": "callable",
          "token": "critical_rayleigh_continuous(M_list=(50,100,200))",
          "symbol_key": "critical_rayleigh_continuous",
          "form": "backticked_call",
          "in_report_section": "## 6. 审计链与产物路径",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 10288,
            "char_end": 10392,
            "line_start": 199,
            "line_end": 199,
            "quote": "| RB 连续谱参考 | `critical_rayleigh_continuous(M_list=(50,100,200))` | `artifacts/in31_n12/continuum.json` |",
            "quote_sha256": "sha256:a1dad22171425194d7fc9596d92afbeaad974edac34e7a6e3d46766f262edfee",
            "unique": true
          },
          "occurrence_lines": [
            199
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "symbol_declared_in_markdown_no_byte_asset",
            "result": "unresolved",
            "note": "library symbol named in prose; registration does not open the producing repo (out of contract scope)"
          },
          "note": "declared library symbol / callable; this工序 registers the pointer only and does not read the producing repository"
        },
        {
          "asset_id": "A30",
          "asset_key": "report-7216:ref:artifacts/in31_n12/base_profile.json",
          "asset_class": "data_artifact_reference",
          "label": "data_artifact",
          "token": "artifacts/in31_n12/base_profile.json",
          "symbol_key": null,
          "form": "backticked_path",
          "in_report_section": "## 6. 审计链与产物路径",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 10393,
            "char_end": 10502,
            "line_start": 200,
            "line_end": 200,
            "quote": "| 基态/等效间隙诊断 | `conductive_base_state` 基态温度剖面拟合（见 `make_report` 说明） | `artifacts/in31_n12/base_profile.json` |",
            "quote_sha256": "sha256:4700d17a16f5054d9e0b7e39248f1c8d2ec83756d17e80d8e353358cec53daf3",
            "unique": true
          },
          "occurrence_lines": [
            200
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_delivery_worktree",
            "result": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report 7216 is a TensorLBM asset, repo layering=LBM|research|A)",
            "same_basename_hits": []
          },
          "note": "artifact produced outside this repository (evidence chain §6 of the report); bytes unavailable in the delivery worktree"
        },
        {
          "asset_id": "A31",
          "asset_key": "report-7216:ref:conductive_base_state",
          "asset_class": "api_symbol_reference",
          "label": "identifier",
          "token": "conductive_base_state",
          "symbol_key": "conductive_base_state",
          "form": "backticked_identifier",
          "in_report_section": "## 6. 审计链与产物路径",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 10393,
            "char_end": 10502,
            "line_start": 200,
            "line_end": 200,
            "quote": "| 基态/等效间隙诊断 | `conductive_base_state` 基态温度剖面拟合（见 `make_report` 说明） | `artifacts/in31_n12/base_profile.json` |",
            "quote_sha256": "sha256:4700d17a16f5054d9e0b7e39248f1c8d2ec83756d17e80d8e353358cec53daf3",
            "unique": true
          },
          "occurrence_lines": [
            200
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "symbol_declared_in_markdown_no_byte_asset",
            "result": "unresolved",
            "note": "library symbol named in prose; registration does not open the producing repo (out of contract scope)"
          },
          "note": "declared library symbol / callable; this工序 registers the pointer only and does not read the producing repository"
        },
        {
          "asset_id": "A32",
          "asset_key": "report-7216:ref:make_report",
          "asset_class": "api_symbol_reference",
          "label": "identifier",
          "token": "make_report",
          "symbol_key": "make_report",
          "form": "backticked_identifier",
          "in_report_section": "## 6. 审计链与产物路径",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 10393,
            "char_end": 10502,
            "line_start": 200,
            "line_end": 200,
            "quote": "| 基态/等效间隙诊断 | `conductive_base_state` 基态温度剖面拟合（见 `make_report` 说明） | `artifacts/in31_n12/base_profile.json` |",
            "quote_sha256": "sha256:4700d17a16f5054d9e0b7e39248f1c8d2ec83756d17e80d8e353358cec53daf3",
            "unique": true
          },
          "occurrence_lines": [
            200
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "symbol_declared_in_markdown_no_byte_asset",
            "result": "unresolved",
            "note": "library symbol named in prose; registration does not open the producing repo (out of contract scope)"
          },
          "note": "declared library symbol / callable; this工序 registers the pointer only and does not read the producing repository"
        },
        {
          "asset_id": "A33",
          "asset_key": "report-7216:ref:artifacts/in31_n12/hr_decoupling.json",
          "asset_class": "data_artifact_reference",
          "label": "data_artifact",
          "token": "artifacts/in31_n12/hr_decoupling.json",
          "symbol_key": null,
          "form": "backticked_path",
          "in_report_section": "## 6. 审计链与产物路径",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 10503,
            "char_end": 10633,
            "line_start": 201,
            "line_end": 201,
            "quote": "| 双相解耦实测 | `python benchmarks/rb_discrete_stability/run_hr_bench.py --mode decoupling` | `artifacts/in31_n12/hr_decoupling.json` |",
            "quote_sha256": "sha256:e4dee3848d337162a6005b7222f6888f7c3d336ea07168f2a880d6434147fc89",
            "unique": true
          },
          "occurrence_lines": [
            201
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_delivery_worktree",
            "result": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report 7216 is a TensorLBM asset, repo layering=LBM|research|A)",
            "same_basename_hits": []
          },
          "note": "artifact produced outside this repository (evidence chain §6 of the report); bytes unavailable in the delivery worktree"
        },
        {
          "asset_id": "A34",
          "asset_key": "report-7216:ref:benchmarks/rb_discrete_stability/run_hr_bench.py",
          "asset_class": "benchmark_script_reference",
          "label": "benchmark_script",
          "token": "benchmarks/rb_discrete_stability/run_hr_bench.py",
          "symbol_key": null,
          "form": "path_in_backticked_command",
          "in_report_section": "## 6. 审计链与产物路径",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 10503,
            "char_end": 10633,
            "line_start": 201,
            "line_end": 201,
            "quote": "| 双相解耦实测 | `python benchmarks/rb_discrete_stability/run_hr_bench.py --mode decoupling` | `artifacts/in31_n12/hr_decoupling.json` |",
            "quote_sha256": "sha256:e4dee3848d337162a6005b7222f6888f7c3d336ea07168f2a880d6434147fc89",
            "unique": true
          },
          "occurrence_lines": [
            201
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_delivery_worktree",
            "result": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report 7216 is a TensorLBM asset, repo layering=LBM|research|A)",
            "same_basename_hits": []
          },
          "note": "code/test/benchmark pointer declared in the report; bytes unavailable in this worktree"
        },
        {
          "asset_id": "A35",
          "asset_key": "report-7216:ref:artifacts/in31_n12/hr_settling.json",
          "asset_class": "data_artifact_reference",
          "label": "data_artifact",
          "token": "artifacts/in31_n12/hr_settling.json",
          "symbol_key": null,
          "form": "backticked_path",
          "in_report_section": "## 6. 审计链与产物路径",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 10634,
            "char_end": 10708,
            "line_start": 202,
            "line_end": 202,
            "quote": "| 双相沉降对拍 | `... --mode settling` | `artifacts/in31_n12/hr_settling.json` |",
            "quote_sha256": "sha256:3c9c4107fd452e8b62bf080463009586c1010d9ecfcccc1f954b3d8d858b8662",
            "unique": true
          },
          "occurrence_lines": [
            202
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_delivery_worktree",
            "result": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report 7216 is a TensorLBM asset, repo layering=LBM|research|A)",
            "same_basename_hits": []
          },
          "note": "artifact produced outside this repository (evidence chain §6 of the report); bytes unavailable in the delivery worktree"
        },
        {
          "asset_id": "A36",
          "asset_key": "report-7216:ref:artifacts/in31_n12/criteria.json",
          "asset_class": "data_artifact_reference",
          "label": "data_artifact",
          "token": "artifacts/in31_n12/criteria.json",
          "symbol_key": null,
          "form": "backticked_path",
          "in_report_section": "## 6. 审计链与产物路径",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 10709,
            "char_end": 10842,
            "line_start": 203,
            "line_end": 203,
            "quote": "| 图/判据汇总 | `python benchmarks/rb_discrete_stability/make_figures.py` | `figures/in31_n12/*.png`, `artifacts/in31_n12/criteria.json` |",
            "quote_sha256": "sha256:4811b0c5781467dd3841db63c1206ce36781929ee2ef23139c90e366b293fd42",
            "unique": true
          },
          "occurrence_lines": [
            203
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_delivery_worktree",
            "result": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report 7216 is a TensorLBM asset, repo layering=LBM|research|A)",
            "same_basename_hits": []
          },
          "note": "artifact produced outside this repository (evidence chain §6 of the report); bytes unavailable in the delivery worktree"
        },
        {
          "asset_id": "A37",
          "asset_key": "report-7216:ref:figures/in31_n12/*.png",
          "asset_class": "figure_reference",
          "label": "figure_glob",
          "token": "figures/in31_n12/*.png",
          "symbol_key": null,
          "form": "backticked_path",
          "in_report_section": "## 6. 审计链与产物路径",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 10709,
            "char_end": 10842,
            "line_start": 203,
            "line_end": 203,
            "quote": "| 图/判据汇总 | `python benchmarks/rb_discrete_stability/make_figures.py` | `figures/in31_n12/*.png`, `artifacts/in31_n12/criteria.json` |",
            "quote_sha256": "sha256:4811b0c5781467dd3841db63c1206ce36781929ee2ef23139c90e366b293fd42",
            "unique": true
          },
          "occurrence_lines": [
            203
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "glob_reference_no_single_file",
            "result": "unresolved",
            "detail": "glob pattern; no single file to hash or fetch"
          },
          "note": "figure bytes are not served by the platform figure endpoint; identity is the record.figures declaration plus the prose reference (probe recorded in resolution_check)"
        },
        {
          "asset_id": "A38",
          "asset_key": "report-7216:ref:tests/test_pseudopotential_hr.py",
          "asset_class": "test_reference",
          "label": "test",
          "token": "tests/test_pseudopotential_hr.py",
          "symbol_key": null,
          "form": "path_in_backticked_command",
          "in_report_section": "## 6. 审计链与产物路径",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 10843,
            "char_end": 10936,
            "line_start": 204,
            "line_end": 204,
            "quote": "| 单测 | `pytest -q tests/test_rb_discrete_stability.py tests/test_pseudopotential_hr.py` | – |",
            "quote_sha256": "sha256:8ef17a43e47067ce799e87c8c0b2756d7123adc51f7bc87897043ba0bf68a3b3",
            "unique": true
          },
          "occurrence_lines": [
            204
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_delivery_worktree",
            "result": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report 7216 is a TensorLBM asset, repo layering=LBM|research|A)",
            "same_basename_hits": []
          },
          "note": "code/test/benchmark pointer declared in the report; bytes unavailable in this worktree"
        },
        {
          "asset_id": "A39",
          "asset_key": "report-7216:ref:tests/test_rb_discrete_stability.py",
          "asset_class": "test_reference",
          "label": "test",
          "token": "tests/test_rb_discrete_stability.py",
          "symbol_key": null,
          "form": "path_in_backticked_command",
          "in_report_section": "## 6. 审计链与产物路径",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 10843,
            "char_end": 10936,
            "line_start": 204,
            "line_end": 204,
            "quote": "| 单测 | `pytest -q tests/test_rb_discrete_stability.py tests/test_pseudopotential_hr.py` | – |",
            "quote_sha256": "sha256:8ef17a43e47067ce799e87c8c0b2756d7123adc51f7bc87897043ba0bf68a3b3",
            "unique": true
          },
          "occurrence_lines": [
            204
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_delivery_worktree",
            "result": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report 7216 is a TensorLBM asset, repo layering=LBM|research|A)",
            "same_basename_hits": []
          },
          "note": "code/test/benchmark pointer declared in the report; bytes unavailable in this worktree"
        },
        {
          "asset_id": "A40",
          "asset_key": "report-7216:ref:tensorlbm.two_phase_viscosity",
          "asset_class": "api_symbol_reference",
          "label": "dotted_symbol",
          "token": "tensorlbm.two_phase_viscosity",
          "symbol_key": "tensorlbm.two_phase_viscosity",
          "form": "backticked_dotted",
          "in_report_section": "### 与既有成果的边界（避免重复 verified/）",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "char_start": 11132,
            "char_end": 11337,
            "line_start": 210,
            "line_end": 210,
            "quote": "- `tensorlbm.hadamard_rybczynski`（解析律 + 轴对称有限元 Stokes）与 `tensorlbm.two_phase_viscosity`（λ/ρ 解耦映射）已存在且未修改；本节点的增量是：RB 离散谱求解器（全新）、仓库内可复现的连续谱参考（替代外部 Chebyshev 数值）、逐组分施力核与 λ 解耦的**实测**验证、以及伪势引擎 HR 对拍的定量 FAIL 诊断。",
            "quote_sha256": "sha256:7c0f9e87c12de45bec2bf6be213dd62504e2707f46abb95f5e3f2e4b6c9e4fef",
            "unique": true
          },
          "occurrence_lines": [
            210
          ],
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "symbol_declared_in_markdown_no_byte_asset",
            "result": "unresolved",
            "note": "library symbol named in prose; registration does not open the producing repo (out of contract scope)"
          },
          "note": "declared library symbol / callable; this工序 registers the pointer only and does not read the producing repository"
        }
      ],
      "claims": [],
      "claims_empty_reason": "objective.classify_report_type=false and this package is registration-only (no extraction): claims are legitimately empty per contract.output.asset_manifest.json + constraints.no_forced_claim_generation. Report 7216's own numeric claims are NOT re-stated here; they stay in the source markdown and are untouched (no verified marks).",
      "integrity": {
        "quote_uniqueness": {
          "locators": 40,
          "unique_quotes": 40,
          "note": "non-unique quotes are still exactly resolvable via their char span; uniqueness is reported, not forced"
        },
        "hash_recomputed_locally": "sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b",
        "hash_matches_contract": true,
        "assets_with_locator": 40,
        "assets_without_locator": 0,
        "verified_marks_emitted": 0
      }
    }
  },
  "claims": []
}
```
