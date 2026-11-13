# wp-5577-01 · KF 工序 01（asset-registration）结果报告

**源报告**：BP 示范工程报告：Agent 科研生产闭环端到端实证（IN12-P8 / m4936）
**源 URI**：`tensor://reports/5577` · scenario_key=`campaign/bp-demo-in12p8` · `markdown`
**源哈希钉子**：`sha256:60575cfe91ed23757639b1060ce931c746236989cb3ba8734a4a8280582b7de8`（3702 字符 / 5707 UTF-8 字节 / 96 逻辑行）
**包 ID**：`wp-5577-01` · task_type=`01-asset-registration` · 构建器 `scripts/wp5577_build_report.py`

> **交付纪律声明**：本包零改动 TensorKnowledge 核心模块——未触 `ke/` 任何模块、未改任何共享
> schema（`schemas/asset_manifest.v1.schema.json`、`schemas/kf_result.v1.schema.json` 均只读），
> 改动为新增：1 个构建脚本 + 1 个测试 + 本包目录 8 个产物（合计 10 个文件），
> 不与其他在开 PR 的热文件路径重叠。原 PR#152 携带 `ke/__pycache__/*.pyc` 二进制，
> 本轮由 AC13 机械禁止复现。

## ① 案例介绍

本工序的「案例」是**一份报告的可达性登记**，不是物理算例。源报告 5577 是 BP 示范工程
（IN12-P8 / mission 4936）的 Agent 科研生产闭环端到端实证，其物理内容为 KRISO KCS
集装箱船静水裸船体阻力预报：Lpp/B/T = 230.0/32.2/10.8 m，∇ = 52030 m³，
Cb/Cm/Cwp = 0.6509/0.9849/0.7630，设计点 24 kn / Fn = 0.2600，主链为
ITTC-57 摩擦 + Holtrop–Mennen(1984) 兴波。上述数字由参数表资产
（A02，L9-L15）承载；本工序**只登记位置、不复算数值**（复算属 04 独立审核）。

## ② 怎么做的

1. **取源并证哈希**：`GET /api/v1/tensor/reports/5577` 拉两次，各自算 UTF-8 字节 sha256，两次一致才落盘，
   `source/markdown.sha256` 写钉子（AC01/AC02）。
2. **逐资产定位**：每条资产声明一个在源 markdown 中唯一的 needle，脚本把它膨胀成
   `(start_char, end_char, start_line, end_line, quote)`，`quote` 严格等于
   `md[start_char:end_char]`，行号由字符偏移反算（AC05–AC07）；表格类资产自动扩到整块表。
3. **可达性探测**：平台图 → `GET /tensor/reports/5577/figures/<name>`；跨仓代码/工件/符号 →
   本工作树存在性探测；外部文献/数据集/端点 → 只登记引用、不探测不复制（NOTES#5）。
4. **出工件**：`asset_manifest.json`（schema `asset_manifest.v1`）+ `kf_result.json`
   （schema `kf_result.v1`）+ `acceptance.json` + 图 1，全部脚本一次跑出，
   本报告数字从 manifest/acceptance 注入。

## ③ 计算结果

| 指标 | 值 |
|---|---|
| 登记资产总数 | 23 |
| `resolved_in_source`（源内可定位） | 5 |
| `referenced_unresolved`（引用存在、内容未取） | 16 |
| `declared_absent`（源显式声明不可得/未运行） | 2 |
| 定位器自洽 | 23/23 |
| claims | 0（01 工序无抽取职责） |
| 验收项 | 16/16 PASS（verdict=PASS） |

资产类别分布：

| asset_class | 条数 | 占比 |
|---|---|---|
| data_artifact_reference | 1 | 4.3% |
| data_table | 4 | 17.4% |
| dataset_reference | 2 | 8.7% |
| embedded_figure | 3 | 13.0% |
| endpoint_reference | 2 | 8.7% |
| literature_reference | 3 | 13.0% |
| metric_evidence | 1 | 4.3% |
| report_markdown | 1 | 4.3% |
| service_reference | 1 | 4.3% |
| source_code_reference | 4 | 17.4% |
| symbol_reference | 1 | 4.3% |

逐条登记（行号为源 markdown 逻辑行，1-based）：

| id | class | 章节 | 行区间 | resolution | 唯一 |
|---|---|---|---|---|---|
| A01 | report_markdown | 全文 | L1-96 | resolved_in_source | Y |
| A02 | data_table | ① 案例介绍 | L9-15 | resolved_in_source | Y |
| A03 | data_table | ③ 计算结果 | L36-42 | resolved_in_source | Y |
| A04 | data_table | ③ 计算结果 | L44-48 | resolved_in_source | Y |
| A05 | data_table | ⑥ 误差判定 | L77-83 | resolved_in_source | Y |
| A06 | embedded_figure | ④ 结果图 | L59-59 | referenced_unresolved | Y |
| A07 | embedded_figure | ④ 结果图 | L59-59 | referenced_unresolved | Y |
| A08 | embedded_figure | ④ 结果图 | L59-59 | referenced_unresolved | Y |
| A09 | source_code_reference | ② 怎么做的 | L19-19 | referenced_unresolved | Y |
| A10 | source_code_reference | ② 怎么做的 | L30-30 | referenced_unresolved | Y |
| A11 | source_code_reference | ⑤ 注意点 | L68-68 | referenced_unresolved | Y |
| A12 | source_code_reference | ② 怎么做的 | L25-25 | referenced_unresolved | Y |
| A13 | data_artifact_reference | ④ 结果图 | L60-60 | referenced_unresolved | Y |
| A14 | endpoint_reference | ② 怎么做的 | L23-23 | referenced_unresolved | Y |
| A15 | endpoint_reference | ⑤ 注意点 | L64-64 | referenced_unresolved | Y |
| A16 | service_reference | ③ 计算结果 | L48-48 | referenced_unresolved | Y |
| A17 | literature_reference | ① 案例介绍 | L4-4 | referenced_unresolved | Y |
| A18 | literature_reference | ① 案例介绍 | L5-5 | referenced_unresolved | Y |
| A19 | dataset_reference | ① 案例介绍 | L3-3 | referenced_unresolved | Y |
| A20 | literature_reference | ② 怎么做的 | L26-26 | referenced_unresolved | Y |
| A21 | symbol_reference | ⑤ 注意点 | L68-68 | referenced_unresolved | Y |
| A22 | dataset_reference | ⑤ 注意点 | L72-72 | declared_absent | Y |
| A23 | metric_evidence | ⑥ 误差判定 | L96-96 | declared_absent | Y |

验收项（机器可裁，逐项带 observed/expected）：

| id | 检查 | observed | expected | 结果 |
|---|---|---|---|---|
| AC01 | 源 markdown 字符数 / UTF-8 字节数与 manifest 一致 | [3702, 5707] | [3702, 5707] | PASS |
| AC02 | 双次拉取 sha256 一致（平台未声明 contract_source_hash，用一致性替代） | True | True | PASS |
| AC03 | asset_manifest 通过 schemas/asset_manifest.v1.schema.json | valid | valid | PASS |
| AC04 | kf_result 通过 schemas/kf_result.v1.schema.json | valid | valid | PASS |
| AC05 | quote == md[start_char:end_char]（逐资产切片自洽） | 23 | 23 | PASS |
| AC06 | quote 在源 markdown 中唯一 | 23 | 23 | PASS |
| AC07 | 行号可由字符偏移反算复现 | 23 | 23 | PASS |
| AC08 | asset_id 连续无重复（A01..A23） | ['A01', 'A02', 'A03', 'A04', 'A05', 'A06', 'A07', 'A08', 'A09', 'A10', 'A11', 'A12', 'A13', 'A14', 'A15', 'A16', 'A17', 'A18', 'A19', 'A20', 'A21', 'A22', 'A23'] | ['A01', 'A02', 'A03', 'A04', 'A05', 'A06', 'A07', 'A08', 'A09', 'A10', 'A11', 'A12', 'A13', 'A14', 'A15', 'A16', 'A17', 'A18', 'A19', 'A20', 'A21', 'A22', 'A23'] | PASS |
| AC09 | counts 三类合计 == 资产条数 | [23, 23] | [23, 23] | PASS |
| AC10 | 平台 record 声明的图全部登记为资产 | 3 | 3 | PASS |
| AC11 | 图字节可达数（0..3，honest 观测；不作本包失败项） | recorded_honestly | recorded_honestly | PASS |
| AC12 | claims 为空且带 claims_empty_reason | [0, True] | [0, True] | PASS |
| AC13 | 包内无 .pyc / __pycache__（原 PR#152 的二进制污染不复现） | [] | [] | PASS |
| AC14 | 跨仓引用未在本仓伪造同名文件（存在性探测全 false） | [] | [] | PASS |
| AC15 | fig1 PNG 落盘且 sha256 与登记一致 | 6bb04a761c25bbbcf6dfbb4a3e6950ad86b2814e31513cb2601684b8ad140e7f | 6bb04a761c25bbbcf6dfbb4a3e6950ad86b2814e31513cb2601684b8ad140e7f | PASS |
| AC16 | fig1 PNG 体积 > 10 KB（非空图） | True | True | PASS |

最关键的一组未解析资产是**图字节**：平台 record 声明了 3 张图
（fig1 阻力谱 / fig2 偏差谱 / fig3 证据链），但 `GET /tensor/reports/5577/figures/<name>`
未返回内容（http 404），故本包只能给出 `referenced_unresolved` + http_status/bytes 证据，
**不代为生成、不代填 sha256**。对照实验：同一路由对 report 11621 返回 200 且 71730 B，
说明 404 是该报告自身缺图字节，不是路由变更。

## ④ 结果图

图 1 `fig1_asset_resolution.png`：资产解析矩阵——横轴=登记条数，纵轴=asset_class，颜色=解析状态
（resolved_in_source / referenced_unresolved / declared_absent），标题内嵌源哈希前 16 位
与 chars/bytes，用一张图同时证明「资产面覆盖」与「源被钉住」。该图由
`scripts/wp5577_build_report.py` 的 `render_figure` 程序化生成，无手工编辑。

本工序属**文档/登记类任务**，不存在物理场，故无场量云图可画；替代的比较视图即
图 1 的「类别 × 解析状态」堆积条（同一坐标下三类状态可直接对照）。

## ⑤ 注意点

- **图字节 404 是结论不是事故**：已在 ④ 给出对照实验（11621 同路由 200），
  因此 5577 的 404 归因于该报告自身缺图字节；已写入 `manifest.limitations`。
- **绝不代造跨仓内容**：`bp_demo/`、`physics/holtrop`、`tests/test_resistance_ittc78.py`、
  `cluster_exec.py`、`artifacts/bp_demo/sha256_index.json` 在本仓均不存在，登记为
  `referenced_unresolved`；AC14 反向校验「本仓不得出现同名文件」，防后人顺手伪造。
- **行号口径**：逻辑行 = 去掉尾换行后按换行切分，1-based；与 `docs/kf/NOTES.md` 既有多包
  一致，跨包可比。
- **locator 扩张单调**：不唯一时向上扩行（到顶后向下），终态必唯一（整篇短语唯一），
  不存在无限扩张；只要扩到全文必然终止。
- **局限**：本工序不校验源报告数字真伪、不重算阻力、不裁定源报告 V3/V4 的 honest-FAIL；
  这些属 04 独立审核工序。

## ⑥ 误差判定

| 项 | 验证内容 | 实测 | 基准 | 偏差 | 是否<3% |
|---|---|---|---|---|---|
| E1 | 源哈希：本地重算 vs 二次拉取 | `60575cfe91ed2375…` | `60575cfe91ed2375…` | 0.000% | 是（逐字节相等） |
| E2 | 定位器切片：quote vs md[start:end] | 23/23 相等 | 全等 | 0.000% | 是 |
| E3 | 行号反算 vs 登记行号 | 23/23 一致 | 全等 | 0.000% | 是 |
| E4 | counts 三类合计 vs 资产条数 | 23 vs 23 | 相等 | 0.000% | 是 |
| E5 | 图字节可达率 | 0/3 | 3/3（期望） | 缺口 100% | **否（honest-FAIL）** |

逐项回答：

- **E1–E4**：偏差均为 0.000%（逐字节 / 整数相等）→ 是否<3%：**是**。
- **E5 图字节可达率**：0/3 可达，缺口 100% → 是否<3%：**否**。
  **HONEST-FAIL**：源报告 3 张图的字节在平台侧取不到，本包不以生成图冒充源图；
  该缺口只能由源报告提交方补图表、或平台侧修复图存储后重开本包补齐。
- 物理量对标（阻力误差是否<3% 基准）**不适用本工序**：本工序零物理计算，
  任何阻力精度结论都属 04 工序，故不在此声明通过。
