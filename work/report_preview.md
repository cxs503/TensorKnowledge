## ① 案例介绍

**任务**：TensorKnowledge#152 重开（原 PR 因夹带 `ke/__pycache__/*.pyc` 二进制被 owner 裁定关闭），
按 KF 五工序制的第 1 工序（01-asset-registration）重做 **wp-5577-01**：把平台报告 5577
「BP 示范工程报告：Agent 科研生产闭环端到端实证（IN12-P8 / m4936）」登记成可校验的资产清单。

**源**：`tensor://reports/5577` · scenario_key=`campaign/bp-demo-in12p8` · `markdown`
= **3702 字符 / 5707 UTF-8 字节 / 96 逻辑行**，
sha256 钉子 `60575cfe91ed23757639b1060ce931c746236989cb3ba8734a4a8280582b7de8`。

**源报告的物理内容**（本案只登记、不复算，下表数字由脚本从源 markdown 表格解析注入）：
KRISO **KCS** 集装箱船静水裸船体阻力预报。

| 量（源自报告参数表） | 值 |
|---|---|
| Lpp / B / T | 230.0 / 32.2 / 10.8 |
| ∇ | 52030 |
| Cb / Cm / Cwp | 0.6509 / 0.9849 / 0.7630 |
| 设计航速 / Fn | 24.00 / 0.2600 |

总阻力按 R_T=(1+k)R_F+R_W+R_B+R_TR+R_A+R_APP 分解，兴波阻力取 Holtrop–Mennen(1982) /
Holtrop(1984) 回归（d = −0.9），摩擦项 ITTC-57 + ITTC-1978 粗糙度。源报告结果表内
5 个航速点：12/15/18/21/24 kn → R_T = 335.2/532.7/829.4/1296.4/2011.6 kN。

## ② 怎么做的

1. **取源并证哈希**（先证后做）：`GET /api/v1/tensor/reports/5577` **拉两次**，各自算 UTF-8
   字节 sha256，两次相等才落盘；`source/markdown.sha256` 写钉子。
   平台记录本身不含 markdown 哈希字段（无 `contract_source_hash`），故以「双次拉取稳定 +
   本地重算」替代 —— 状态记为 NOT_APPLICABLE 而非「相符」。
2. **逐资产定位**：每条资产声明一个在源 markdown 中唯一的 needle，脚本膨胀成
   `(start_char, end_char, start_line, end_line, quote)`，`quote` **严格等于**
   `md[start_char:end_char]`；不唯一时向上扩行（到顶后向下）直到唯一；行号由字符偏移反算。
   表格类资产自动扩到整块表。
3. **可达性探测**：图 → `GET /tensor/reports/5577/figures/<name>`；跨仓代码/工件/符号 →
   本工作树存在性探测（一律 `referenced_unresolved`，禁止造同名文件）；文献/数据集/端点 →
   只登记引用、不探测不复制。源报告显式声明不可得的（KCS EFD 表、七维指标生态/商业/经济性
   证据）→ `declared_absent`。
4. **出工件**：`asset_manifest.json`（`schemas/asset_manifest.v1.schema.json`）+
   `kf_result.json`（`schemas/kf_result.v1.schema.json`）+ `acceptance.json`（16 项机器可裁）+
   图 1；构建器 `scripts/wp5577_build_report.py` 一次跑出，报告数字从工件注入（零手抄）。
5. **可复现性**：测试离线重放构建器纯函数，产物必须**逐字段等于**提交的 manifest
   （防手改），并做变异测试（改一个 quote/计数，检验器必须报错）。

## ③ 计算结果

| 指标 | wp-5577-01 | 基线 wp-11621-01（同工序同路由） |
|---|---|---|
| 登记资产 | 23 | 21 |
| `resolved_in_source` | 5 | 7 |
| `referenced_unresolved` | 16 | 14 |
| `declared_absent` | 2 | 0 |
| 图字节可达 | 0/3 | 6/6 |
| 定位器自洽 | 23/23 | 15/15 |
| claims | 0（01 工序无抽取职责） | 0 |

逐条登记（行号为源 markdown 逻辑行，1-based）：

| id | class | 章节 | 行区间 | resolution |
|---|---|---|---|---|
| A01 | report_markdown | 全文 | L1-96 | resolved_in_source |
| A02 | data_table | ① 案例介绍 | L9-15 | resolved_in_source |
| A03 | data_table | ③ 计算结果 | L36-42 | resolved_in_source |
| A04 | data_table | ③ 计算结果 | L44-48 | resolved_in_source |
| A05 | data_table | ⑥ 误差判定 | L77-83 | resolved_in_source |
| A06 | embedded_figure | ④ 结果图 | L59-59 | referenced_unresolved |
| A07 | embedded_figure | ④ 结果图 | L59-59 | referenced_unresolved |
| A08 | embedded_figure | ④ 结果图 | L59-59 | referenced_unresolved |
| A09 | source_code_reference | ② 怎么做的 | L19-19 | referenced_unresolved |
| A10 | source_code_reference | ② 怎么做的 | L30-30 | referenced_unresolved |
| A11 | source_code_reference | ⑤ 注意点 | L68-68 | referenced_unresolved |
| A12 | source_code_reference | ② 怎么做的 | L25-25 | referenced_unresolved |
| A13 | data_artifact_reference | ④ 结果图 | L60-60 | referenced_unresolved |
| A14 | endpoint_reference | ② 怎么做的 | L23-23 | referenced_unresolved |
| A15 | endpoint_reference | ⑤ 注意点 | L64-64 | referenced_unresolved |
| A16 | service_reference | ③ 计算结果 | L48-48 | referenced_unresolved |
| A17 | literature_reference | ① 案例介绍 | L4-4 | referenced_unresolved |
| A18 | literature_reference | ① 案例介绍 | L5-5 | referenced_unresolved |
| A19 | dataset_reference | ① 案例介绍 | L3-3 | referenced_unresolved |
| A20 | literature_reference | ② 怎么做的 | L26-26 | referenced_unresolved |
| A21 | symbol_reference | ⑤ 注意点 | L68-68 | referenced_unresolved |
| A22 | dataset_reference | ⑤ 注意点 | L72-72 | declared_absent |
| A23 | metric_evidence | ⑥ 误差判定 | L96-96 | declared_absent |

验收：**16/16 PASS**（verdict=PASS），
含 AC03/AC04（双 schema 校验）、AC05–AC07（切片自洽/唯一/行号反算）、AC13（包内无 .pyc）、
AC14（跨仓引用未伪造）。

## ④ 结果图

**图 1**（`fig1_asset_resolution.png`，107121 B，sha256
`6bb04a761c25bbbc…`）：资产解析矩阵——横轴=登记条数，
纵轴=asset_class，颜色=解析状态；标题内嵌源哈希前 16 位与 chars/bytes，一张图同时钉住
「资产面覆盖」与「源不漂移」。

**图 2**（`fig2_resolution_vs_baseline.png`）：与基线包的对照——同一工序（KF-01）、同一图端点，
基线 wp-11621-01 图字节 **6/6 可达**，本包 **0/3 可达**。
这条对照排除「路由被改」的解释，把 5577 的 404 归因于**该报告自身缺图字节**。

> 说明：本任务属**文档/登记类工序**，不存在物理场，故无场量云图可画；替代视图 =
> 图 1 的「类别 × 解析状态」矩阵 + 图 2 的基线对照条。

## ⑤ 注意点

- **图字节 404 是结论不是事故**：已用图 2/同路由对照（11621 200 且 71730 B）证明是报告侧缺图，
  并写入 `manifest.limitations` 供后续工序追讨；本包**不代为生成、不代填 sha256**。
- **绝不代造跨仓内容**：`bp_demo/`、`physics/holtrop`、`tests/test_resistance_ittc78.py`、
  `cluster_exec.py`、`artifacts/bp_demo/sha256_index.json` 在本仓不存在 → 全部
  `referenced_unresolved`；AC14 反向校验「本仓不得出现同名文件」，防后人顺手伪造。
- **原 PR#152 的两处教训**：(a) 夹带 `ke/__pycache__/*.pyc` → 本包 AC13 机械禁止包内字节码，
  且提交只 `git add` 本包 10 个文件（仓内既有 tracked pyc 的改动一律不入提交）；
  (b) 一次性堆 9 文件 + 3 二进制的大提交 → 本轮拆成「1 脚本 + 1 测试 + 1 包目录」。
- **locator 扩张单调**：不唯一时向上扩行（到顶后向下），扩到全文必唯一，故必然终止。
- **局限**：本工序不校验源报告数字真伪、不重算阻力、不裁定源报告 V3/V4 的 honest-FAIL ——
  这些属 04 独立审核工序；也不修跨仓内容（`/calculations/resistance` 与 `/resistance/predict`
  两套阻力链并存的问题归船舶平台仓）。

## ⑥ 误差判定

| 项 | 验证内容 | 实测 | 基准 | 偏差 | 是否<3% |
|---|---|---|---|---|---|
| E1 | 源哈希（本地重算 vs 二次拉取） | `60575cfe91ed2375…` | `60575cfe91ed2375…` | 0.000% | 是（逐字节） |
| E2 | 定位器切片 quote vs md[start:end] | 23/23 | 全等 | 0.000% | 是 |
| E3 | 行号反算 vs 登记行号 | 23/23 | 全等 | 0.000% | 是 |
| E4 | counts 三类合计 vs 资产条数 | 23 vs 23 | 相等 | 0.000% | 是 |
| E5 | 图字节可达率 | 0/3 | 3/3 | 缺口 100% | **否（honest-FAIL）** |
| E6 | src 尺寸 chars/bytes | 3702 / 5707 | 文件实测 | 0.000% | 是 |

逐项回答：

- **E1–E4、E6**：偏差 0.000%（逐字节/整数相等）→ 是否<3%：**是**。
- **E5 图字节可达率 0/3**：缺口 100% → 是否<3%：**否**。
  **HONEST-FAIL**：源报告 3 张图字节在平台侧取不到（404），本包不以生成图冒充源图；
  补齐只能由源报告提交方补图表、或平台侧修复图存储后重开本包。
- **物理量对标（阻力是否<3%）不适用本工序**：本工序零物理计算，任何阻力精度结论属 04 工序，
  故不在此声明通过。源报告的 V3（遗留 mock，+243.10%）与 V4（KVLCC2 全尺度，−17.26%）
  是其自报的 honest-FAIL，本包原样登记为证据，不改写、不粉饰。
