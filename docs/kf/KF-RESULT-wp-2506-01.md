# KF-RESULT wp-2506-01

> 工序 `01-asset-registration` ｜ report_id=`2506` ｜ lane `C` ｜ package `wp-2506-01`
> source_uri `tensor://reports/2506` ｜ source_field `markdown`
> 归档产物：`artifacts/kf/wp-2506-01/asset_manifest.json`、`kf_result.json`、`checks.json`、`source_snapshot/`
> 交付镜像（artifacts/ 被 .gitignore 忽略，随分支交付的是这一份）：`knowledge/kf/wp-2506-01/`

## ① 本工序做了什么（案例介绍 / Case）

源报告 2506 的记录字段：title `TensorFVM 粘性算子耗散性定因：非正交修正被证伪 + 能量相容(Galerkin)装配 PSD 证书（41 几何扫掠）`，scenario_key `tensorfvm/verification/compatible-viscous-dissipativity`，
mission_id `2488`，status `published`，created_at `2026-11-03T11:27:21.025547+00:00`，
tags `['TensorFVM', 'verification', 'viscous-operator', 'dissipativity', 'PSD', 'sum-by-parts']`；正文 H1 为 `TensorFVM 粘性算子耗散性定因与能量相容装配（native compatible viscous operator）`。
其物理内容属 **TensorFVM 粘性算子耗散性定因**：两单元非正交网格（`two_tetrahedra(skew)`）上
离散粘性算子是否会造动能，以及能量相容（Galerkin）装配的半正定证书——这部分**不是本工序的对象**。

本工序只做一件事：**把这份报告登记成可被下游工序寻址的资产清单**——确认 report_id 与 markdown 的
UTF-8 字节 sha256、枚举可解析的附件/工件、给每条资产一个字符偏移 + 逐字引文定位，把拿不到字节的
工件如实登记为未解析。本工序**不抽取知识**（claims=[]）、**不判定 verified**（裁决权在平台验证门）、
**不重跑上游算例**、**不读写其它 report_id**。

源身份事实（程序化注入）：`source_hash = sha256:c62850b3dacd416bd9d535fec206f6e8427fb10121f439c7b865b2165e5138b0`（与契约 `sha256:c62850b3dacd416bd9d535fec206f6e8427fb10121f439c7b865b2165e5138b0` 逐字节一致
→ hash_match=True），chars=3382（契约 3382，match=True），
bytes(UTF-8)=5171，lines=59；记录 title 与契约 title 一致=True，
scenario_key 与契约一致=True，
**记录 title 是否在 markdown 正文中逐字出现=False**（见 ⑤ 注意点 1）。

## ② 怎么做的（方法 / 工具链 / 关键设置）

1. **取源**：`GET /api/v1/tensor/reports/2506`（Bearer token，`POST /api/v1/auth/login` 取得），只取 `markdown`
   与记录级元数据；脚本硬锁 `report_id=2506`，其它 id 直接 `SystemExit`（互不覆盖前提）。
2. **指纹**：对 `markdown` 的 UTF-8 字节独立重算 sha256，与契约 `source_hash` 对齐；同时核字符数（契约 chars=3382，
   实测 3382）、字节数与行数。
3. **零手抄定位**：引文**不手打**——脚本用选择器（H1 行、`## ①` 后第 n 个非空行、含 token 的行、表格首/首个数据行、
   段内列表项）定位，取**命中的整行原文**作为 quote 并记 `offset_chars`；随后对每条 quote 做
   `quote in markdown` **和** `markdown[offset:offset+len] == quote` 双重回读（任一失败即门失败，不静默跳过）。
4. **结构门**：清单与信封分别用 `schemas/asset_manifest.v1.schema.json`、`schemas/kf_result.v1.schema.json`
   做 jsonschema（Draft 2020-12）校验；ID 唯一性、status-缺口一致性（未解析必须带理由 ≥10 字符）逐条断言。
5. **未解析登记**：图件、pytest 运行日志、代码级绑定三类走端点探针 + 正文检索，拿不到就如实入 `declared_unresolvable`，
   **不重绘、不代上游补图、不反推**。
6. **工具链**：Python 3 / urllib（取源）/ hashlib（指纹）/ jsonschema 4.26（结构门）/ matplotlib 3.10（图件）/ pytest（回归）。
   脚本：`scripts/kf/register_assets_lib.py`（取源+定位库）、`scripts/kf/wp_2506_01_register_assets.py`（本工序主程序）、
   `scripts/kf/plot_wp_2506_01.py`（图件）、`scripts/kf/build_wp_2506_01_report.py`（本文件生成器）；
   测试：`tests/test_kf_wp_2506_01.py`。
7. **离线可重建**：抓取时把完整记录落到 `source_snapshot/report_2506.json`，`--record-file` 可无网/无 token 复跑。

一键复跑（在线，仓库根目录执行，需要 `$TENSOR_API_BASE` / `$TENSOR_AGENT_USER` / `$TENSOR_AGENT_PASS`）：

```
python3 scripts/kf/wp_2506_01_register_assets.py && python3 scripts/kf/plot_wp_2506_01.py && python3 scripts/kf/build_wp_2506_01_report.py && python3 -m pytest tests/test_kf_wp_2506_01.py -q
```

离线复跑（无网无 token；与仓库产物逐字节一致，`generated_at` 除外）：

```
python3 scripts/kf/wp_2506_01_register_assets.py --record-file artifacts/kf/wp-2506-01/source_snapshot/report_2506.json --out /tmp/wp2506_repro
```

## ③ 产出物清单（输出文件名 → 要点）

| 输出文件 | 字节 | 要点 |
|---|---|---|
| `artifacts/kf/wp-2506-01/asset_manifest.json` | 32242 | 工序 01 唯一输出：source 指纹 + 26 条资产 + 4 条未解析缺口 + locator_checks |
| `artifacts/kf/wp-2506-01/kf_result.json` | 35723 | 平台结果信封（package_id/task_type/report_id/provenance/outputs/claims=[]） |
| `artifacts/kf/wp-2506-01/checks.json` | 2966 | 验收自检机读结果（11 项布尔通过项 + 明细, all_pass=True） |
| `artifacts/kf/wp-2506-01/source_snapshot/report_2506.json` | 6348 | 取源时刻完整记录快照（离线重建与审计用） |
| `artifacts/kf/wp-2506-01/figures/wp2506_01_asset_registry.png` | 349306 | 图 1：资产登记图（左=资产/状态/偏移，中=自检，右=源身份事实） |
| `artifacts/kf/wp-2506-01/delivery_verification.json` | 1230 | 交付自验：发布后把报告读回来复核唯一 json 块/tags/mission_id/provenance 哈希 + 图件路由对照 |
| `docs/kf/KF-RESULT-wp-2506-01.md` | — | 本报告正文（含唯一一个 JSON 结果代码块） |
| `knowledge/kf/wp-2506-01/` | — | 交付镜像（清单/信封/自检/图/源快照，与 artifacts 逐字节一致，tests 绑定） |

资产状态分布（程序化统计，共 26 条）：{'resolved': 22, 'declared_unresolvable': 4}。

### 资产登记表（26 条）

| asset_id | kind | status | offset(chars) | quote（逐字，整行原文；表格竖线已转义） |
|---|---|---|---|---|
| `asset-2506-01-report-markdown` | report_markdown | resolved | 0 | # TensorFVM 粘性算子耗散性定因与能量相容装配（native compatible viscous operator） |
| `asset-2506-02-report-record` | report_record_metadata | declared_unresolvable | n/a | （无逐字引文：见 unresolved_reason） |
| `asset-2506-03-section-case-defect` | section_prose | resolved | 76 | 仓库长期挂 `xfail(strict=True)` 开放缺陷 `test_two_cell_skew_viscosity_must_dissipate`：两单元非正交网格上 |
| `asset-2506-04-section-geometry-family` | section_prose | resolved | 164 | 离散粘性算子会**造动能**。几何族 `two_tetrahedra(skew)`：两共享面四面体，5 顶点 / 2 单元 / 7 面， |
| `asset-2506-05-parameter-sweep-grid` | parameter_statement | resolved | 233 | 全部静止 Dirichlet，μ=ρ=1，单元 0 速度规定为 (1,0,0)；skew∈[0,1] 共 41 点（skew>1 面定向非法）。 |
| `asset-2506-06-criterion-statement` | criterion_statement | resolved | 306 | 判据：动能变化率 E = uᵀA u（A 为融合槽位矩阵，E<0 = 耗散），以及对称部分特征值证书。 |
| `asset-2506-07-method-damping-sweep` | method_steps | resolved | 369 | 1. 给 `NativeViscous3D` 增加**逐面非正交修正阻尼** `correction_damping∈[0,1]`（默认 1.0 → 与 HEAD 逐位相同）， |
| `asset-2506-08-equation-galerkin-assembly` | equation | resolved | 587 |    `K = Σ_c 2 μ_c V_c [Σ_i S_iiᵀS_ii + 2Σ_{i<j} S_ijᵀS_ij]`，`S = sym(∇u)`（可去偏）。 |
| `asset-2506-09-method-psd-by-construction` | method_steps | resolved | 667 |    该矩阵是平方和，故对任意网格、任意 u 恒为**对称半正定**，耗散性由构造保证；边界数据经 |
| `asset-2506-10-toolchain-list` | toolchain_list | resolved | 764 | 3. 工具链：`scripts/audit_compatible_viscous_dissipativity.py`（41 点扫掠 → JSON/CSV/表/PNG）+ pytest |
| `asset-2506-11-table-sweep-result` | result_table | resolved | 956 | \| skew \| 最大非正交角° \| legacy E (α=1) \| legacy E (α=0.5) \| legacy E (α=0) \| 相容 E \| legacy λmin(-DAG) \| 相容 λmin(K) \| |
| `asset-2506-12-table-sweep-row0` | result_table_row | resolved | 1102 | \| 0.000 \| 25.24 \| -10.764444 \| -5.862222 \| -0.960000 \| -2.111111 \| +8.906667 \| +0.535005 \| |
| `asset-2506-13-summary-legacy-default` | result_summary_bullet | resolved | 2382 | - legacy 默认装配（α=1）在 **2 个几何**上造能，首个失效 skew=0.975（非正交角 86.22° 起）。 |
| `asset-2506-14-summary-alpha0` | result_summary_bullet | resolved | 2447 | - **α=0（纯两点通量，既有报告称为"延迟修正、恒耗散"）反而在 20 个几何上造能** → 非正交修正不是主因。 |
| `asset-2506-15-summary-compatible-extrema` | result_summary_bullet | resolved | 2507 | - 相容装配：E 的最小值 = -3.935422（41 点全为负），λmin(K) 最小值 = +0.360339 > 0。 |
| `asset-2506-16-figure-dissipativity-sweep` | figure | declared_unresolvable | 2579 | ![sweep](dissipativity-sweep.png)：左=E(skew)（legacy 三条阻尼曲线与相容装配）；右=对称部分最小特征值证书。 |
| `asset-2506-17-limitation-attribution` | limitations_list | resolved | 2671 | - **归因修正**：m2431 把造能归给非正交修正（"延迟修正恒耗散"）。本单用逐面阻尼扫掠证明该结论在其自己的几何族上不成立： |
| `asset-2506-18-limitation-default-path` | limitations_list | resolved | 2819 | - **默认路径未改**：`correction_damping=1.0` 与 HEAD 矩阵逐位相同（有回归用例），仓库唯一 strict xfail 保持红灯（诚实保留欠账）。 |
| `asset-2506-19-limitation-dissipativity-only` | limitations_list | resolved | 2910 | - **只认证耗散性，不认证标度**：native 单元梯度模板未做体积归一（本单实测其仿射场梯度偏离解析值，最大 6.17）， |
| `asset-2506-20-limitation-sparsity` | limitations_list | resolved | 3075 | - K 的模板是两跳（单元梯度用邻居的邻居），引入求解器需评估稀疏度/带宽。 |
| `asset-2506-21-error-basis` | error_judgement | resolved | 3125 | 本单判据是**符号/特征值证书**而非与解析解的相对误差，无文献基准可比，故不适用「<3%」条款（显式声明，不含糊）： |
| `asset-2506-22-error-energy-bound` | error_judgement | resolved | 3185 | - 相容装配 E ≤ 0：41/41 点满足，最坏值 -3.935422（距 0 的余量 100%）。 |
| `asset-2506-23-error-lambda-min` | error_judgement | resolved | 3237 | - 相容装配 λmin(K) > 0：41/41 点满足，最小值 +0.360339。 |
| `asset-2506-24-test-evidence-summary` | test_evidence_summary | resolved | 764 | 3. 工具链：`scripts/audit_compatible_viscous_dissipativity.py`（41 点扫掠 → JSON/CSV/表/PNG）+ pytest |
| `asset-2506-25-run-artifact-pytest-log` | run_artifact | declared_unresolvable | 2819 | - **默认路径未改**：`correction_damping=1.0` 与 HEAD 矩阵逐位相同（有回归用例），仓库唯一 strict xfail 保持红灯（诚实保留欠账）。 |
| `asset-2506-26-codebase-pointer` | codebase_pointer | declared_unresolvable | 764 | 3. 工具链：`scripts/audit_compatible_viscous_dissipativity.py`（41 点扫掠 → JSON/CSV/表/PNG）+ pytest |

### 未解析缺口（4 条）

| asset_id | kind | 理由 |
|---|---|---|
| `asset-2506-02-report-record` | report_record_metadata | 记录 title（=契约 title）未在 markdown 中逐字出现：markdown H1 措辞为「TensorFVM 粘性算子耗散性定因与能量相容装配（native compatible viscous operator）」，与记录 title「…定因：非正交修正被证伪 + 能量相容(Galerkin)装配 PSD 证书（41 几何扫掠）」不同。按零手抄纪律不改写、不强行匹配，登记为记录级元数据不可在正文定位（title_matches_markdown_h1=False）。 |
| `asset-2506-16-figure-dissipativity-sweep` | figure | 记录 figures 仅 name/caption（figure_payload_present=False），图件端点 GET /tensor/reports/2506/figures/dissipativity-sweep(.png) 返回 HTTP 404；本工序不重绘、不代上游补图，保留未解析（正文引用行仍可逐字定位）。 |
| `asset-2506-25-run-artifact-pytest-log` | run_artifact | 报告仅以文字提及「有回归用例」与 pytest 6 条用例，未附原始 pytest 日志/trace/运行记录，工件字节不可得；工序 01 不重跑上游算例，故保留未解析。 |
| `asset-2506-26-codebase-pointer` | codebase_pointer | 正文给出仓库内相对路径（src/tensorfvm/native_compatible_viscous3d.py、scripts/audit_compatible_viscous_dissipativity.py、tests/test_native_compatible_viscous3d.py）但无分支/提交号，字节不可经报告信道取得，亦无法绑定到具体 commit；仅由记录 mission_id=2488 探到 mission 记录 repo=TensorFVM，属记录级间接线索，不认定为工件绑定。 |

**图 1**（`artifacts/kf/wp-2506-01/figures/wp2506_01_asset_registry.png`）：左图为 report 2506 的 26 条资产
（颜色=status，@n=逐字引文在 markdown 中的字符偏移），中图为 11 项机读自检（all_pass=True），
右图为源身份事实（哈希/字符数/行数/契约一致性/图件载荷）。本工序是纯登记工序，不产生任何物理场量，
因此**没有场量云图、也没有与解析解/实验的比较曲线**——这是本单无物理图件的如实理由（上游报告自述的
`dissipativity-sweep.png` 字节不可得，见缺口表）；图中数据全部来自 `asset_manifest.json` / `checks.json` 注入，无手填点。

## ④ 证据定位表（claim/字段 → 原文引文片段）

| 字段/资产 | offset | 原文引文（逐字，整行） |
|---|---|---|
| source_hash / chars | — | `sha256:c62850b3dacd416bd9d535fec206f6e8427fb10121f439c7b865b2165e5138b0`；chars=3382（契约 3382），hash_match=True，chars_match_contract=True |
| `asset-2506-01-report-markdown` / H1 | @0 | # TensorFVM 粘性算子耗散性定因与能量相容装配（native compatible viscous operator） |
| `asset-2506-03-section-case-defect` / ① 案例介绍 / 悬案缺陷 | @76 | 仓库长期挂 `xfail(strict=True)` 开放缺陷 `test_two_cell_skew_viscosity_must_dissipate`：两单元非正交网格上 |
| `asset-2506-04-section-geometry-family` / ① 案例介绍 / 几何族 | @164 | 离散粘性算子会**造动能**。几何族 `two_tetrahedra(skew)`：两共享面四面体，5 顶点 / 2 单元 / 7 面， |
| `asset-2506-05-parameter-sweep-grid` / ① 案例介绍 / 扫掠参数 | @233 | 全部静止 Dirichlet，μ=ρ=1，单元 0 速度规定为 (1,0,0)；skew∈[0,1] 共 41 点（skew>1 面定向非法）。 |
| `asset-2506-06-criterion-statement` / ① 案例介绍 / 判据 | @306 | 判据：动能变化率 E = uᵀA u（A 为融合槽位矩阵，E<0 = 耗散），以及对称部分特征值证书。 |
| `asset-2506-07-method-damping-sweep` / ② 方法 / 步骤1 | @369 | 1. 给 `NativeViscous3D` 增加**逐面非正交修正阻尼** `correction_damping∈[0,1]`（默认 1.0 → 与 HEAD 逐位相同）， |
| `asset-2506-08-equation-galerkin-assembly` / ② 方法 / Galerkin 装配式 | @587 |    `K = Σ_c 2 μ_c V_c [Σ_i S_iiᵀS_ii + 2Σ_{i<j} S_ijᵀS_ij]`，`S = sym(∇u)`（可去偏）。 |
| `asset-2506-09-method-psd-by-construction` / ② 方法 / 半正定由构造保证 | @667 |    该矩阵是平方和，故对任意网格、任意 u 恒为**对称半正定**，耗散性由构造保证；边界数据经 |
| `asset-2506-10-toolchain-list` / ② 方法 / 工具链 | @764 | 3. 工具链：`scripts/audit_compatible_viscous_dissipativity.py`（41 点扫掠 → JSON/CSV/表/PNG）+ pytest |
| `asset-2506-11-table-sweep-result` / ③ 计算结果 / 41 点扫掠表 | @956 | \| skew \| 最大非正交角° \| legacy E (α=1) \| legacy E (α=0.5) \| legacy E (α=0) \| 相容 E \| legacy λmin(-DAG) \| 相容 λmin(K) \| |
| `asset-2506-12-table-sweep-row0` / ③ 计算结果 / 首行数据 | @1102 | \| 0.000 \| 25.24 \| -10.764444 \| -5.862222 \| -0.960000 \| -2.111111 \| +8.906667 \| +0.535005 \| |
| `asset-2506-13-summary-legacy-default` / ③ 扫描汇总 / legacy 默认装配 | @2382 | - legacy 默认装配（α=1）在 **2 个几何**上造能，首个失效 skew=0.975（非正交角 86.22° 起）。 |
| `asset-2506-14-summary-alpha0` / ③ 扫描汇总 / α=0 反证 | @2447 | - **α=0（纯两点通量，既有报告称为"延迟修正、恒耗散"）反而在 20 个几何上造能** → 非正交修正不是主因。 |
| `asset-2506-15-summary-compatible-extrema` / ③ 扫描汇总 / 相容装配极值 | @2507 | - 相容装配：E 的最小值 = -3.935422（41 点全为负），λmin(K) 最小值 = +0.360339 > 0。 |
| `asset-2506-16-figure-dissipativity-sweep` / ④ 图 / dissipativity-sweep.png | @2579 | ![sweep](dissipativity-sweep.png)：左=E(skew)（legacy 三条阻尼曲线与相容装配）；右=对称部分最小特征值证书。 |
| `asset-2506-17-limitation-attribution` / ⑤ 局限 / 归因修正 | @2671 | - **归因修正**：m2431 把造能归给非正交修正（"延迟修正恒耗散"）。本单用逐面阻尼扫掠证明该结论在其自己的几何族上不成立： |
| `asset-2506-18-limitation-default-path` / ⑤ 局限 / 默认路径未改 | @2819 | - **默认路径未改**：`correction_damping=1.0` 与 HEAD 矩阵逐位相同（有回归用例），仓库唯一 strict xfail 保持红灯（诚实保留欠账）。 |
| `asset-2506-19-limitation-dissipativity-only` / ⑤ 局限 / 只认证耗散性 | @2910 | - **只认证耗散性，不认证标度**：native 单元梯度模板未做体积归一（本单实测其仿射场梯度偏离解析值，最大 6.17）， |
| `asset-2506-20-limitation-sparsity` / ⑤ 局限 / 稀疏度 | @3075 | - K 的模板是两跳（单元梯度用邻居的邻居），引入求解器需评估稀疏度/带宽。 |
| `asset-2506-21-error-basis` / ⑥ 误差判定 / 判据性质 | @3125 | 本单判据是**符号/特征值证书**而非与解析解的相对误差，无文献基准可比，故不适用「<3%」条款（显式声明，不含糊）： |
| `asset-2506-22-error-energy-bound` / ⑥ 误差判定 / E 证书 | @3185 | - 相容装配 E ≤ 0：41/41 点满足，最坏值 -3.935422（距 0 的余量 100%）。 |
| `asset-2506-23-error-lambda-min` / ⑥ 误差判定 / λmin 证书 | @3237 | - 相容装配 λmin(K) > 0：41/41 点满足，最小值 +0.360339。 |
| `asset-2506-24-test-evidence-summary` / ② 工具链 / pytest 用例数 | @764 | 3. 工具链：`scripts/audit_compatible_viscous_dissipativity.py`（41 点扫掠 → JSON/CSV/表/PNG）+ pytest |
| `asset-2506-25-run-artifact-pytest-log` / ⑤ 局限 / 回归用例 | @2819 | - **默认路径未改**：`correction_damping=1.0` 与 HEAD 矩阵逐位相同（有回归用例），仓库唯一 strict xfail 保持红灯（诚实保留欠账）。 |
| `asset-2506-26-codebase-pointer` / ② 工具链 / 代码路径 | @764 | 3. 工具链：`scripts/audit_compatible_viscous_dissipativity.py`（41 点扫掠 → JSON/CSV/表/PNG）+ pytest |

上表每条引文的字符偏移与命中次数见 `asset_manifest.json → locator_checks`；
`source_locator_resolvable=True`，`offset_mismatch=[]`。

## ⑤ 注意点与局限

1. **记录 title 与正文 H1 措辞不同**（本工序发现的源侧事实，不掩盖）：记录 title 为
   `TensorFVM 粘性算子耗散性定因：非正交修正被证伪 + 能量相容(Galerkin)装配 PSD 证书（41 几何扫掠）`，markdown H1 为 `TensorFVM 粘性算子耗散性定因与能量相容装配（native compatible viscous operator）`。
   两者不是逐字同形串，因此 `title_matches_markdown_h1=False`；按零手抄纪律**不改写、不强行匹配**，
   该条（`asset-2506-02-report-record`）登记为 `declared_unresolvable`，理由写在清单里。
2. **图件不可得**：记录 `figures` 只有 `name/caption`（figure_payload_present=False），
   端点探针 HTTP 状态 = [404, 404]；
   本工序**不重绘、不代上游补图**，登记为 `declared_unresolvable`。
   **路由形状对照（区别「路由不对」与「载荷不存在」）**：本工序把**自己发布的报告**作对照样本去探同一路由
   `GET /tensor/reports/<id>/figures/<name>.png`，返回 200 且字节数等于本地 png 大小；同一路由对 report 2506 为 404。
   故 `404` 属上游图件载荷在平台侧不存在，而非本工序探针写错路径。核对记录见
   `artifacts/kf/wp-2506-01/delivery_verification.json`（`figure_probes` 字段，含两次探针的状态码与字节数）。
3. **测试证据是自述**：正文只以「有回归用例」「pytest（…，6 条用例）」的文字提及，无原始 pytest 日志/trace；
   本工序只登记该断言可定位，**不把它当通过证据**，也未重跑上游算例（工序 01 不做）。
4. **代码指针只到路径**：正文给出 `src/tensorfvm/native_compatible_viscous3d.py` 等相对路径但无分支/提交号，
   字节不可经报告信道取得，无法绑定 commit；mission 探针（`/tensor/missions/2488` → repo=TensorFVM）
   仅属记录级间接线索，不作工件绑定。
5. **不评价真伪**：本单不含 claims、不标 verified；报告里的 `E`/`λmin` 证书与 α=0 反证等结论的裁决权在平台验证门与下游工序。
6. **互不覆盖**：脚本硬锁 `report_id=2506`；本单未读写其它任何 report_id 的内容。
7. **引文口径**：quote 一律取**整行原文**（含 markdown 表格竖线/LaTeX 反引号），不裁不改；跨行段落取代表行，
   不做字符串拼接（避免二次转录误差）。
8. 清单级局限（原文入档）：图件字节不可得：记录 figures 仅 name/caption（figure_payload_present=False），端点探针 404；未重绘、未代上游补图。；正文给出仓库内相对路径但无分支/提交号，代码级绑定不可解析；仅记录级 mission_id=2488 → repo=TensorFVM 间接线索。

## ⑥ 自检（acceptance 逐条 + 误差判定）

### 关键量 vs 基准（本工序的“基准”=契约与原文）

| 关键量 | 基准 | 实测 | 误差 | < 3%? |
|---|---|---|---|---|
| markdown 字节哈希 | 契约 `sha256:c62850b3dacd416bd9d535fec206f6e8427fb10121f439c7b865b2165e5138b0` | `sha256:c62850b3dacd416bd9d535fec206f6e8427fb10121f439c7b865b2165e5138b0` | 0（逐字节相同） | ✅ YES（0%） |
| 字符数 | 契约 3382 | 3382 | 0 | ✅ YES（0%） |
| 引文可定位性 | 每条 quote 必须逐字命中且偏移回读一致 | 失配 0 条 / 共 25 条 | 0 条 | ✅ YES（0%） |
| ID 唯一性 | 无重复 asset_id | 重复 0 条 | 0 | ✅ YES（0%） |

结论：登记层无物理量误差，误差面是**字节/引文级**，四项全部 0 偏差（<3% 显式成立）。
报告正文的物理数值（如 `E` 最坏值、`λmin` 最小值、失效几何数）属上游报告自述，本工序不复核、不背书，
也未据此生成任何 claim。

### acceptance 逐条自检（机读）

| 验收项 | 结果 |
|---|---|
| source_hash_matches | ✅ |
| chars_match_contract | ✅ |
| report_id_locked | ✅ |
| source_locator_resolvable | ✅ |
| no_duplicate_ids | ✅ |
| unresolved_have_reasons | ✅ |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ |
| title_scenario_match_contract | ✅ |
| no_extraction_no_verification | ✅ |
| schema_pass | ✅ |
| valid_json | ✅ |

明细（`checks.json`）：

| check | 结果 | 明细（截断） |
|---|---|---|
| source_hash_matches | ✅ PASS | {"contract": "sha256:c62850b3dacd416bd9d535fec206f6e8427fb10121f439c7b865b2165e5138b0", "recomputed": "sha256:c62850b3dacd416bd9d535fec206f6e8427fb10121f439c7b865b2165e5138b0"} |
| chars_match_contract | ✅ PASS | {"contract": 3382, "measured": 3382} |
| report_id_locked | ✅ PASS | {"report_id": 2506} |
| source_locator_resolvable | ✅ PASS | {"assets": 25, "bad_quotes": [], "offset_mismatch": []} |
| no_duplicate_ids | ✅ PASS | {"assets": 26, "unique": 26} |
| unresolved_have_reasons | ✅ PASS | [] |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ PASS | {"claims": 0, "unresolved": 4, "note": "claims 为空数组（契约允许）；4 条不可得工件均带 reason"} |
| title_scenario_match_contract | ✅ PASS | {"title_matches": true, "scenario_matches": true} |
| no_extraction_no_verification | ✅ PASS | {"extraction_performed": false, "claims_emitted": 0, "verification_performed": false, "note": "工序 01 只登记资产与指纹：不抽取知识、不判定 verified、不重跑上游算例；claims 允许为空数组，本单为空。"} |
| schema_pass | ✅ PASS | {"manifest_errors": [], "kf_result_errors": [], "schema": ["schemas/asset_manifest.v1.schema.json", "schemas/kf_result.v1.schema.json"], "validator": "jsonschema Draft2020-12"} |
| valid_json | ✅ PASS | {"files": ["asset_manifest.json", "kf_result.json"], "reloaded": true, "reload_errors": []} |

### honest-FAIL / 未完成声明

- `all_pass=True`；失败项=[]。
- 须显式声明三项**未完成/不可得**（不是通过）：图件字节不可得、pytest 原始日志不可得、代码级 commit 绑定不可得；
  另有记录 title 与 H1 措辞不一致一条。四者均已登记在 `unresolved` / `declared_unresolvable` 并带理由，
  下游若需这些字节，应回上游补件，而不是由本工序生成。

## 结果信封（唯一 JSON 代码块，原样提交）

```json
{
  "package_id": "wp-2506-01",
  "task_type": "01-asset-registration",
  "report_id": "2506",
  "provenance": {
    "source_uri": "tensor://reports/2506",
    "source_hash": "sha256:c62850b3dacd416bd9d535fec206f6e8427fb10121f439c7b865b2165e5138b0",
    "source_field": "markdown",
    "producer": "kf-worker/tp-native-1",
    "emitted_at": "2026-11-12T01:01:54+00:00",
    "notes": "asset_manifest.json 见 outputs；引文均由脚本从 markdown 按整行取子串，逐条做 quote in markdown + 偏移回读确认；未抽取 claims，未标 verified。"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-2506-01",
      "task_type": "01-asset-registration",
      "report_id": "2506",
      "lane": "C",
      "generated_at": "2026-11-12T01:01:54+00:00",
      "producer": "kf-worker/tp-native-1",
      "source": {
        "report_id": "2506",
        "source_uri": "tensor://reports/2506",
        "source_field": "markdown",
        "source_hash": "sha256:c62850b3dacd416bd9d535fec206f6e8427fb10121f439c7b865b2165e5138b0",
        "contract_source_hash": "sha256:c62850b3dacd416bd9d535fec206f6e8427fb10121f439c7b865b2165e5138b0",
        "hash_algo": "sha256",
        "hash_scope": "UTF-8 bytes of tensor_reports.markdown",
        "hash_match": true,
        "chars": 3382,
        "contract_chars": 3382,
        "chars_match_contract": true,
        "bytes": 5171,
        "lines": 59,
        "fetched_via": "GET /api/v1/tensor/reports/2506 (Bearer token)",
        "record_fields": {
          "title": "TensorFVM 粘性算子耗散性定因：非正交修正被证伪 + 能量相容(Galerkin)装配 PSD 证书（41 几何扫掠）",
          "scenario_key": "tensorfvm/verification/compatible-viscous-dissipativity",
          "mission_id": 2488,
          "status": "published",
          "created_at": "2026-11-03T11:27:21.025547+00:00",
          "tags": [
            "TensorFVM",
            "verification",
            "viscous-operator",
            "dissipativity",
            "PSD",
            "sum-by-parts"
          ],
          "contract_title": "TensorFVM 粘性算子耗散性定因：非正交修正被证伪 + 能量相容(Galerkin)装配 PSD 证书（41 几何扫掠）",
          "contract_scenario_key": "tensorfvm/verification/compatible-viscous-dissipativity",
          "title_matches_contract": true,
          "scenario_matches_contract": true,
          "title_matches_markdown_h1": false
        }
      },
      "assets": [
        {
          "asset_id": "asset-2506-01-report-markdown",
          "kind": "report_markdown",
          "uri": "tensor://reports/2506#markdown/H1",
          "status": "resolved",
          "chars": 64,
          "locator": {
            "source_field": "markdown",
            "section": "H1",
            "quote": "# TensorFVM 粘性算子耗散性定因与能量相容装配（native compatible viscous operator）",
            "quote_verified": true,
            "offset_chars": 0,
            "count_occurrences": 1,
            "note": "markdown 首行 H1，全文指纹载体"
          }
        },
        {
          "asset_id": "asset-2506-02-report-record",
          "kind": "report_record_metadata",
          "uri": "tensor://reports/2506#markdown/record.title",
          "status": "declared_unresolvable",
          "unresolved_reason": "记录 title（=契约 title）未在 markdown 中逐字出现：markdown H1 措辞为「TensorFVM 粘性算子耗散性定因与能量相容装配（native compatible viscous operator）」，与记录 title「…定因：非正交修正被证伪 + 能量相容(Galerkin)装配 PSD 证书（41 几何扫掠）」不同。按零手抄纪律不改写、不强行匹配，登记为记录级元数据不可在正文定位（title_matches_markdown_h1=False）。",
          "notes": "记录级元数据：title/scenario_key/mission_id 见 source.record_fields；正文无同形串"
        },
        {
          "asset_id": "asset-2506-03-section-case-defect",
          "kind": "section_prose",
          "uri": "tensor://reports/2506#markdown/① 案例介绍 / 悬案缺陷",
          "status": "resolved",
          "chars": 87,
          "locator": {
            "source_field": "markdown",
            "section": "① 案例介绍 / 悬案缺陷",
            "quote": "仓库长期挂 `xfail(strict=True)` 开放缺陷 `test_two_cell_skew_viscosity_must_dissipate`：两单元非正交网格上",
            "quote_verified": true,
            "offset_chars": 76,
            "count_occurrences": 1,
            "note": "§1 首行：strict xfail 开放缺陷"
          }
        },
        {
          "asset_id": "asset-2506-04-section-geometry-family",
          "kind": "section_prose",
          "uri": "tensor://reports/2506#markdown/① 案例介绍 / 几何族",
          "status": "resolved",
          "chars": 68,
          "locator": {
            "source_field": "markdown",
            "section": "① 案例介绍 / 几何族",
            "quote": "离散粘性算子会**造动能**。几何族 `two_tetrahedra(skew)`：两共享面四面体，5 顶点 / 2 单元 / 7 面，",
            "quote_verified": true,
            "offset_chars": 164,
            "count_occurrences": 1,
            "note": "§1 次行：two_tetrahedra(skew) 几何族与规模"
          }
        },
        {
          "asset_id": "asset-2506-05-parameter-sweep-grid",
          "kind": "parameter_statement",
          "uri": "tensor://reports/2506#markdown/① 案例介绍 / 扫掠参数",
          "status": "resolved",
          "chars": 72,
          "locator": {
            "source_field": "markdown",
            "section": "① 案例介绍 / 扫掠参数",
            "quote": "全部静止 Dirichlet，μ=ρ=1，单元 0 速度规定为 (1,0,0)；skew∈[0,1] 共 41 点（skew>1 面定向非法）。",
            "quote_verified": true,
            "offset_chars": 233,
            "count_occurrences": 1,
            "note": "§1 第三行：边界条件、μ=ρ=1、41 点扫掠与合法域上界"
          }
        },
        {
          "asset_id": "asset-2506-06-criterion-statement",
          "kind": "criterion_statement",
          "uri": "tensor://reports/2506#markdown/① 案例介绍 / 判据",
          "status": "resolved",
          "chars": 51,
          "locator": {
            "source_field": "markdown",
            "section": "① 案例介绍 / 判据",
            "quote": "判据：动能变化率 E = uᵀA u（A 为融合槽位矩阵，E<0 = 耗散），以及对称部分特征值证书。",
            "quote_verified": true,
            "offset_chars": 306,
            "count_occurrences": 1,
            "note": "§1 末行：E=uᵀAu 与对称部分特征值判据"
          }
        },
        {
          "asset_id": "asset-2506-07-method-damping-sweep",
          "kind": "method_steps",
          "uri": "tensor://reports/2506#markdown/② 方法 / 步骤1",
          "status": "resolved",
          "chars": 88,
          "locator": {
            "source_field": "markdown",
            "section": "② 方法 / 步骤1",
            "quote": "1. 给 `NativeViscous3D` 增加**逐面非正交修正阻尼** `correction_damping∈[0,1]`（默认 1.0 → 与 HEAD 逐位相同），",
            "quote_verified": true,
            "offset_chars": 369,
            "count_occurrences": 1,
            "note": "§2 步骤1：correction_damping 扫掠用于检验既有归因"
          }
        },
        {
          "asset_id": "asset-2506-08-equation-galerkin-assembly",
          "kind": "equation",
          "uri": "tensor://reports/2506#markdown/② 方法 / Galerkin 装配式",
          "status": "resolved",
          "chars": 79,
          "locator": {
            "source_field": "markdown",
            "section": "② 方法 / Galerkin 装配式",
            "quote": "   `K = Σ_c 2 μ_c V_c [Σ_i S_iiᵀS_ii + 2Σ_{i<j} S_ijᵀS_ij]`，`S = sym(∇u)`（可去偏）。",
            "quote_verified": true,
            "offset_chars": 587,
            "count_occurrences": 1,
            "note": "§2 步骤2：能量（Galerkin）装配的平方和形式"
          }
        },
        {
          "asset_id": "asset-2506-09-method-psd-by-construction",
          "kind": "method_steps",
          "uri": "tensor://reports/2506#markdown/② 方法 / 半正定由构造保证",
          "status": "resolved",
          "chars": 49,
          "locator": {
            "source_field": "markdown",
            "section": "② 方法 / 半正定由构造保证",
            "quote": "   该矩阵是平方和，故对任意网格、任意 u 恒为**对称半正定**，耗散性由构造保证；边界数据经",
            "quote_verified": true,
            "offset_chars": 667,
            "count_occurrences": 1,
            "note": "§2 步骤2：PSD 由平方和构造保证"
          }
        },
        {
          "asset_id": "asset-2506-10-toolchain-list",
          "kind": "toolchain_list",
          "uri": "tensor://reports/2506#markdown/② 方法 / 工具链",
          "status": "resolved",
          "chars": 91,
          "locator": {
            "source_field": "markdown",
            "section": "② 方法 / 工具链",
            "quote": "3. 工具链：`scripts/audit_compatible_viscous_dissipativity.py`（41 点扫掠 → JSON/CSV/表/PNG）+ pytest",
            "quote_verified": true,
            "offset_chars": 764,
            "count_occurrences": 1,
            "note": "§2 步骤3：审计脚本 + pytest + matplotlib 工具链"
          }
        },
        {
          "asset_id": "asset-2506-11-table-sweep-result",
          "kind": "result_table",
          "uri": "tensor://reports/2506#markdown/③ 计算结果 / 41 点扫掠表",
          "status": "resolved",
          "chars": 111,
          "locator": {
            "source_field": "markdown",
            "section": "③ 计算结果 / 41 点扫掠表",
            "quote": "| skew | 最大非正交角° | legacy E (α=1) | legacy E (α=0.5) | legacy E (α=0) | 相容 E | legacy λmin(-DAG) | 相容 λmin(K) |",
            "quote_verified": true,
            "offset_chars": 956,
            "count_occurrences": 1,
            "note": "§3 表头行；数据行数由 stats.data_rows 程序化统计"
          },
          "stats": {
            "data_rows": 14,
            "header_quote": "| skew | 最大非正交角° | legacy E (α=1) | legacy E (α=0.5) | legacy E (α=0) | 相容 E | legacy λmin(-DAG) | 相容 λmin(K) |"
          }
        },
        {
          "asset_id": "asset-2506-12-table-sweep-row0",
          "kind": "result_table_row",
          "uri": "tensor://reports/2506#markdown/③ 计算结果 / 首行数据",
          "status": "resolved",
          "chars": 90,
          "locator": {
            "source_field": "markdown",
            "section": "③ 计算结果 / 首行数据",
            "quote": "| 0.000 | 25.24 | -10.764444 | -5.862222 | -0.960000 | -2.111111 | +8.906667 | +0.535005 |",
            "quote_verified": true,
            "offset_chars": 1102,
            "count_occurrences": 1,
            "note": "§3 表首个数据行（skew=0.000 代表行）"
          },
          "stats": {
            "data_rows": 14
          }
        },
        {
          "asset_id": "asset-2506-13-summary-legacy-default",
          "kind": "result_summary_bullet",
          "uri": "tensor://reports/2506#markdown/③ 扫描汇总 / legacy 默认装配",
          "status": "resolved",
          "chars": 64,
          "locator": {
            "source_field": "markdown",
            "section": "③ 扫描汇总 / legacy 默认装配",
            "quote": "- legacy 默认装配（α=1）在 **2 个几何**上造能，首个失效 skew=0.975（非正交角 86.22° 起）。",
            "quote_verified": true,
            "offset_chars": 2382,
            "count_occurrences": 1,
            "note": "§3 汇总第1条：默认装配造能几何数"
          }
        },
        {
          "asset_id": "asset-2506-14-summary-alpha0",
          "kind": "result_summary_bullet",
          "uri": "tensor://reports/2506#markdown/③ 扫描汇总 / α=0 反证",
          "status": "resolved",
          "chars": 59,
          "locator": {
            "source_field": "markdown",
            "section": "③ 扫描汇总 / α=0 反证",
            "quote": "- **α=0（纯两点通量，既有报告称为\"延迟修正、恒耗散\"）反而在 20 个几何上造能** → 非正交修正不是主因。",
            "quote_verified": true,
            "offset_chars": 2447,
            "count_occurrences": 1,
            "note": "§3 汇总第2条：α=0 反而造能（归因被证伪）"
          }
        },
        {
          "asset_id": "asset-2506-15-summary-compatible-extrema",
          "kind": "result_summary_bullet",
          "uri": "tensor://reports/2506#markdown/③ 扫描汇总 / 相容装配极值",
          "status": "resolved",
          "chars": 63,
          "locator": {
            "source_field": "markdown",
            "section": "③ 扫描汇总 / 相容装配极值",
            "quote": "- 相容装配：E 的最小值 = -3.935422（41 点全为负），λmin(K) 最小值 = +0.360339 > 0。",
            "quote_verified": true,
            "offset_chars": 2507,
            "count_occurrences": 1,
            "note": "§3 汇总第3条：相容装配 E 与 λmin 极值"
          }
        },
        {
          "asset_id": "asset-2506-16-figure-dissipativity-sweep",
          "kind": "figure",
          "uri": "tensor://reports/2506#markdown/④ 图 / dissipativity-sweep.png",
          "status": "declared_unresolvable",
          "chars": 78,
          "locator": {
            "source_field": "markdown",
            "section": "④ 图 / dissipativity-sweep.png",
            "quote": "![sweep](dissipativity-sweep.png)：左=E(skew)（legacy 三条阻尼曲线与相容装配）；右=对称部分最小特征值证书。",
            "quote_verified": true,
            "offset_chars": 2579,
            "count_occurrences": 1,
            "note": "§4 图引用行：正文以 markdown 图片语法指向该 png"
          },
          "unresolved_reason": "记录 figures 仅 name/caption（figure_payload_present=False），图件端点 GET /tensor/reports/2506/figures/dissipativity-sweep(.png) 返回 HTTP 404；本工序不重绘、不代上游补图，保留未解析（正文引用行仍可逐字定位）。"
        },
        {
          "asset_id": "asset-2506-17-limitation-attribution",
          "kind": "limitations_list",
          "uri": "tensor://reports/2506#markdown/⑤ 局限 / 归因修正",
          "status": "resolved",
          "chars": 66,
          "locator": {
            "source_field": "markdown",
            "section": "⑤ 局限 / 归因修正",
            "quote": "- **归因修正**：m2431 把造能归给非正交修正（\"延迟修正恒耗散\"）。本单用逐面阻尼扫掠证明该结论在其自己的几何族上不成立：",
            "quote_verified": true,
            "offset_chars": 2671,
            "count_occurrences": 1,
            "note": "§5 第1条：主因改判为 sum-by-parts 不成立"
          }
        },
        {
          "asset_id": "asset-2506-18-limitation-default-path",
          "kind": "limitations_list",
          "uri": "tensor://reports/2506#markdown/⑤ 局限 / 默认路径未改",
          "status": "resolved",
          "chars": 90,
          "locator": {
            "source_field": "markdown",
            "section": "⑤ 局限 / 默认路径未改",
            "quote": "- **默认路径未改**：`correction_damping=1.0` 与 HEAD 矩阵逐位相同（有回归用例），仓库唯一 strict xfail 保持红灯（诚实保留欠账）。",
            "quote_verified": true,
            "offset_chars": 2819,
            "count_occurrences": 1,
            "note": "§5 第2条：默认路径逐位不变、strict xfail 保留"
          }
        },
        {
          "asset_id": "asset-2506-19-limitation-dissipativity-only",
          "kind": "limitations_list",
          "uri": "tensor://reports/2506#markdown/⑤ 局限 / 只认证耗散性",
          "status": "resolved",
          "chars": 64,
          "locator": {
            "source_field": "markdown",
            "section": "⑤ 局限 / 只认证耗散性",
            "quote": "- **只认证耗散性，不认证标度**：native 单元梯度模板未做体积归一（本单实测其仿射场梯度偏离解析值，最大 6.17），",
            "quote_verified": true,
            "offset_chars": 2910,
            "count_occurrences": 1,
            "note": "§5 第3条：标度/一致性未认证，如实留白"
          }
        },
        {
          "asset_id": "asset-2506-20-limitation-sparsity",
          "kind": "limitations_list",
          "uri": "tensor://reports/2506#markdown/⑤ 局限 / 稀疏度",
          "status": "resolved",
          "chars": 38,
          "locator": {
            "source_field": "markdown",
            "section": "⑤ 局限 / 稀疏度",
            "quote": "- K 的模板是两跳（单元梯度用邻居的邻居），引入求解器需评估稀疏度/带宽。",
            "quote_verified": true,
            "offset_chars": 3075,
            "count_occurrences": 1,
            "note": "§5 第4条：两跳模板的稀疏度/带宽需评估"
          }
        },
        {
          "asset_id": "asset-2506-21-error-basis",
          "kind": "error_judgement",
          "uri": "tensor://reports/2506#markdown/⑥ 误差判定 / 判据性质",
          "status": "resolved",
          "chars": 59,
          "locator": {
            "source_field": "markdown",
            "section": "⑥ 误差判定 / 判据性质",
            "quote": "本单判据是**符号/特征值证书**而非与解析解的相对误差，无文献基准可比，故不适用「<3%」条款（显式声明，不含糊）：",
            "quote_verified": true,
            "offset_chars": 3125,
            "count_occurrences": 1,
            "note": "§6 显式声明不适用 <3% 条款及原因"
          }
        },
        {
          "asset_id": "asset-2506-22-error-energy-bound",
          "kind": "error_judgement",
          "uri": "tensor://reports/2506#markdown/⑥ 误差判定 / E 证书",
          "status": "resolved",
          "chars": 51,
          "locator": {
            "source_field": "markdown",
            "section": "⑥ 误差判定 / E 证书",
            "quote": "- 相容装配 E ≤ 0：41/41 点满足，最坏值 -3.935422（距 0 的余量 100%）。",
            "quote_verified": true,
            "offset_chars": 3185,
            "count_occurrences": 1,
            "note": "§6：41/41 点 E≤0 与最坏值"
          }
        },
        {
          "asset_id": "asset-2506-23-error-lambda-min",
          "kind": "error_judgement",
          "uri": "tensor://reports/2506#markdown/⑥ 误差判定 / λmin 证书",
          "status": "resolved",
          "chars": 43,
          "locator": {
            "source_field": "markdown",
            "section": "⑥ 误差判定 / λmin 证书",
            "quote": "- 相容装配 λmin(K) > 0：41/41 点满足，最小值 +0.360339。",
            "quote_verified": true,
            "offset_chars": 3237,
            "count_occurrences": 1,
            "note": "§6：41/41 点 λmin>0 与最小值"
          }
        },
        {
          "asset_id": "asset-2506-24-test-evidence-summary",
          "kind": "test_evidence_summary",
          "uri": "tensor://reports/2506#markdown/② 工具链 / pytest 用例数",
          "status": "resolved",
          "chars": 91,
          "locator": {
            "source_field": "markdown",
            "section": "② 工具链 / pytest 用例数",
            "quote": "3. 工具链：`scripts/audit_compatible_viscous_dissipativity.py`（41 点扫掠 → JSON/CSV/表/PNG）+ pytest",
            "quote_verified": true,
            "offset_chars": 764,
            "count_occurrences": 1,
            "note": "§2 唯一给出用例数的一行（6 条用例）；与 asset-10 同源行，如实登记为文字自述"
          }
        },
        {
          "asset_id": "asset-2506-25-run-artifact-pytest-log",
          "kind": "run_artifact",
          "uri": "tensor://reports/2506#markdown/⑤ 局限 / 回归用例",
          "status": "declared_unresolvable",
          "chars": 90,
          "locator": {
            "source_field": "markdown",
            "section": "⑤ 局限 / 回归用例",
            "quote": "- **默认路径未改**：`correction_damping=1.0` 与 HEAD 矩阵逐位相同（有回归用例），仓库唯一 strict xfail 保持红灯（诚实保留欠账）。",
            "quote_verified": true,
            "offset_chars": 2819,
            "count_occurrences": 1,
            "note": "§5 第2条同一行（回归用例文字断言）：只登记可定位性，不作通过证据"
          },
          "unresolved_reason": "报告仅以文字提及「有回归用例」与 pytest 6 条用例，未附原始 pytest 日志/trace/运行记录，工件字节不可得；工序 01 不重跑上游算例，故保留未解析。"
        },
        {
          "asset_id": "asset-2506-26-codebase-pointer",
          "kind": "codebase_pointer",
          "uri": "tensor://reports/2506#markdown/② 工具链 / 代码路径",
          "status": "declared_unresolvable",
          "chars": 91,
          "locator": {
            "source_field": "markdown",
            "section": "② 工具链 / 代码路径",
            "quote": "3. 工具链：`scripts/audit_compatible_viscous_dissipativity.py`（41 点扫掠 → JSON/CSV/表/PNG）+ pytest",
            "quote_verified": true,
            "offset_chars": 764,
            "count_occurrences": 1,
            "note": "代码指针：路径文本可定位，字节与 commit 不可得"
          },
          "unresolved_reason": "正文给出仓库内相对路径（src/tensorfvm/native_compatible_viscous3d.py、scripts/audit_compatible_viscous_dissipativity.py、tests/test_native_compatible_viscous3d.py）但无分支/提交号，字节不可经报告信道取得，亦无法绑定到具体 commit；仅由记录 mission_id=2488 探到 mission 记录 repo=TensorFVM，属记录级间接线索，不认定为工件绑定。"
        }
      ],
      "unresolved": [
        {
          "asset_id": "asset-2506-02-report-record",
          "kind": "report_record_metadata",
          "reason": "记录 title（=契约 title）未在 markdown 中逐字出现：markdown H1 措辞为「TensorFVM 粘性算子耗散性定因与能量相容装配（native compatible viscous operator）」，与记录 title「…定因：非正交修正被证伪 + 能量相容(Galerkin)装配 PSD 证书（41 几何扫掠）」不同。按零手抄纪律不改写、不强行匹配，登记为记录级元数据不可在正文定位（title_matches_markdown_h1=False）。"
        },
        {
          "asset_id": "asset-2506-16-figure-dissipativity-sweep",
          "kind": "figure",
          "reason": "记录 figures 仅 name/caption（figure_payload_present=False），图件端点 GET /tensor/reports/2506/figures/dissipativity-sweep(.png) 返回 HTTP 404；本工序不重绘、不代上游补图，保留未解析（正文引用行仍可逐字定位）。"
        },
        {
          "asset_id": "asset-2506-25-run-artifact-pytest-log",
          "kind": "run_artifact",
          "reason": "报告仅以文字提及「有回归用例」与 pytest 6 条用例，未附原始 pytest 日志/trace/运行记录，工件字节不可得；工序 01 不重跑上游算例，故保留未解析。"
        },
        {
          "asset_id": "asset-2506-26-codebase-pointer",
          "kind": "codebase_pointer",
          "reason": "正文给出仓库内相对路径（src/tensorfvm/native_compatible_viscous3d.py、scripts/audit_compatible_viscous_dissipativity.py、tests/test_native_compatible_viscous3d.py）但无分支/提交号，字节不可经报告信道取得，亦无法绑定到具体 commit；仅由记录 mission_id=2488 探到 mission 记录 repo=TensorFVM，属记录级间接线索，不认定为工件绑定。"
        }
      ],
      "locator_checks": {
        "asset-2506-01-report-markdown": {
          "quote": "# TensorFVM 粘性算子耗散性定因与能量相容装配（native compatible viscous operator）",
          "resolvable_in_markdown": true,
          "offset_chars": 0,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-03-section-case-defect": {
          "quote": "仓库长期挂 `xfail(strict=True)` 开放缺陷 `test_two_cell_skew_viscosity_must_dissipate`：两单元非正交网格上",
          "resolvable_in_markdown": true,
          "offset_chars": 76,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-04-section-geometry-family": {
          "quote": "离散粘性算子会**造动能**。几何族 `two_tetrahedra(skew)`：两共享面四面体，5 顶点 / 2 单元 / 7 面，",
          "resolvable_in_markdown": true,
          "offset_chars": 164,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-05-parameter-sweep-grid": {
          "quote": "全部静止 Dirichlet，μ=ρ=1，单元 0 速度规定为 (1,0,0)；skew∈[0,1] 共 41 点（skew>1 面定向非法）。",
          "resolvable_in_markdown": true,
          "offset_chars": 233,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-06-criterion-statement": {
          "quote": "判据：动能变化率 E = uᵀA u（A 为融合槽位矩阵，E<0 = 耗散），以及对称部分特征值证书。",
          "resolvable_in_markdown": true,
          "offset_chars": 306,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-07-method-damping-sweep": {
          "quote": "1. 给 `NativeViscous3D` 增加**逐面非正交修正阻尼** `correction_damping∈[0,1]`（默认 1.0 → 与 HEAD 逐位相同），",
          "resolvable_in_markdown": true,
          "offset_chars": 369,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-08-equation-galerkin-assembly": {
          "quote": "   `K = Σ_c 2 μ_c V_c [Σ_i S_iiᵀS_ii + 2Σ_{i<j} S_ijᵀS_ij]`，`S = sym(∇u)`（可去偏）。",
          "resolvable_in_markdown": true,
          "offset_chars": 587,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-09-method-psd-by-construction": {
          "quote": "   该矩阵是平方和，故对任意网格、任意 u 恒为**对称半正定**，耗散性由构造保证；边界数据经",
          "resolvable_in_markdown": true,
          "offset_chars": 667,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-10-toolchain-list": {
          "quote": "3. 工具链：`scripts/audit_compatible_viscous_dissipativity.py`（41 点扫掠 → JSON/CSV/表/PNG）+ pytest",
          "resolvable_in_markdown": true,
          "offset_chars": 764,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-11-table-sweep-result": {
          "quote": "| skew | 最大非正交角° | legacy E (α=1) | legacy E (α=0.5) | legacy E (α=0) | 相容 E | legacy λmin(-DAG) | 相容 λmin(K) |",
          "resolvable_in_markdown": true,
          "offset_chars": 956,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-12-table-sweep-row0": {
          "quote": "| 0.000 | 25.24 | -10.764444 | -5.862222 | -0.960000 | -2.111111 | +8.906667 | +0.535005 |",
          "resolvable_in_markdown": true,
          "offset_chars": 1102,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-13-summary-legacy-default": {
          "quote": "- legacy 默认装配（α=1）在 **2 个几何**上造能，首个失效 skew=0.975（非正交角 86.22° 起）。",
          "resolvable_in_markdown": true,
          "offset_chars": 2382,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-14-summary-alpha0": {
          "quote": "- **α=0（纯两点通量，既有报告称为\"延迟修正、恒耗散\"）反而在 20 个几何上造能** → 非正交修正不是主因。",
          "resolvable_in_markdown": true,
          "offset_chars": 2447,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-15-summary-compatible-extrema": {
          "quote": "- 相容装配：E 的最小值 = -3.935422（41 点全为负），λmin(K) 最小值 = +0.360339 > 0。",
          "resolvable_in_markdown": true,
          "offset_chars": 2507,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-16-figure-dissipativity-sweep": {
          "quote": "![sweep](dissipativity-sweep.png)：左=E(skew)（legacy 三条阻尼曲线与相容装配）；右=对称部分最小特征值证书。",
          "resolvable_in_markdown": true,
          "offset_chars": 2579,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-17-limitation-attribution": {
          "quote": "- **归因修正**：m2431 把造能归给非正交修正（\"延迟修正恒耗散\"）。本单用逐面阻尼扫掠证明该结论在其自己的几何族上不成立：",
          "resolvable_in_markdown": true,
          "offset_chars": 2671,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-18-limitation-default-path": {
          "quote": "- **默认路径未改**：`correction_damping=1.0` 与 HEAD 矩阵逐位相同（有回归用例），仓库唯一 strict xfail 保持红灯（诚实保留欠账）。",
          "resolvable_in_markdown": true,
          "offset_chars": 2819,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-19-limitation-dissipativity-only": {
          "quote": "- **只认证耗散性，不认证标度**：native 单元梯度模板未做体积归一（本单实测其仿射场梯度偏离解析值，最大 6.17），",
          "resolvable_in_markdown": true,
          "offset_chars": 2910,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-20-limitation-sparsity": {
          "quote": "- K 的模板是两跳（单元梯度用邻居的邻居），引入求解器需评估稀疏度/带宽。",
          "resolvable_in_markdown": true,
          "offset_chars": 3075,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-21-error-basis": {
          "quote": "本单判据是**符号/特征值证书**而非与解析解的相对误差，无文献基准可比，故不适用「<3%」条款（显式声明，不含糊）：",
          "resolvable_in_markdown": true,
          "offset_chars": 3125,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-22-error-energy-bound": {
          "quote": "- 相容装配 E ≤ 0：41/41 点满足，最坏值 -3.935422（距 0 的余量 100%）。",
          "resolvable_in_markdown": true,
          "offset_chars": 3185,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-23-error-lambda-min": {
          "quote": "- 相容装配 λmin(K) > 0：41/41 点满足，最小值 +0.360339。",
          "resolvable_in_markdown": true,
          "offset_chars": 3237,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-24-test-evidence-summary": {
          "quote": "3. 工具链：`scripts/audit_compatible_viscous_dissipativity.py`（41 点扫掠 → JSON/CSV/表/PNG）+ pytest",
          "resolvable_in_markdown": true,
          "offset_chars": 764,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-25-run-artifact-pytest-log": {
          "quote": "- **默认路径未改**：`correction_damping=1.0` 与 HEAD 矩阵逐位相同（有回归用例），仓库唯一 strict xfail 保持红灯（诚实保留欠账）。",
          "resolvable_in_markdown": true,
          "offset_chars": 2819,
          "back_read_ok": true,
          "count_occurrences": 1
        },
        "asset-2506-26-codebase-pointer": {
          "quote": "3. 工具链：`scripts/audit_compatible_viscous_dissipativity.py`（41 点扫掠 → JSON/CSV/表/PNG）+ pytest",
          "resolvable_in_markdown": true,
          "offset_chars": 764,
          "back_read_ok": true,
          "count_occurrences": 1
        }
      },
      "identity_facts": {
        "markdown_h1": "# TensorFVM 粘性算子耗散性定因与能量相容装配（native compatible viscous operator）",
        "record_title": "TensorFVM 粘性算子耗散性定因：非正交修正被证伪 + 能量相容(Galerkin)装配 PSD 证书（41 几何扫掠）",
        "title_consistent": false,
        "scenario_key": "tensorfvm/verification/compatible-viscous-dissipativity",
        "mission_id": 2488,
        "mission_probe": {
          "endpoint": "/tensor/missions/2488",
          "http_status": 200,
          "mission_repo": "TensorFVM",
          "mission_status": "succeeded",
          "mission_campaign_id": null
        },
        "figures_declared": 1,
        "figure_payload_present": false,
        "figure_endpoint_probes": [
          {
            "endpoint": "/tensor/reports/2506/figures/dissipativity-sweep",
            "http_status": 404,
            "bytes": 0
          },
          {
            "endpoint": "/tensor/reports/2506/figures/dissipativity-sweep.png",
            "http_status": 404,
            "bytes": 0
          }
        ],
        "markdown_sha256": "sha256:c62850b3dacd416bd9d535fec206f6e8427fb10121f439c7b865b2165e5138b0",
        "chars": 3382,
        "bytes_utf8": 5171,
        "lines": 59,
        "asset_count": 26,
        "asset_status_distribution": {
          "resolved": 22,
          "declared_unresolvable": 4
        }
      },
      "scope": {
        "extraction_performed": false,
        "claims_emitted": 0,
        "verification_performed": false,
        "note": "工序 01 只登记资产与指纹：不抽取知识、不判定 verified、不重跑上游算例；claims 允许为空数组，本单为空。"
      },
      "limitations": [
        "图件字节不可得：记录 figures 仅 name/caption（figure_payload_present=False），端点探针 404；未重绘、未代上游补图。",
        "pytest 6 条用例为报告文字自述，无原始日志/trace 工件；本工序不重跑上游，只登记可定位性。",
        "正文给出仓库内相对路径但无分支/提交号，代码级绑定不可解析；仅记录级 mission_id=2488 → repo=TensorFVM 间接线索。",
        "本清单不评价报告结论真伪（含 α=0 反证与 PSD 证书）；数值裁决权在平台验证门与下游工序。",
        "引文口径=整行原文，不裁不改；跨行段落取其中代表行，不做字符串拼接（避免二次转录误差）。"
      ]
    }
  },
  "claims": []
}
```
