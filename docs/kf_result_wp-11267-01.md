# KF-RESULT wp-11267-01

**work package** `wp-11267-01` · task_type `01-asset-registration` · lane C · report_id **11267**
**source** `tensor://reports/11267` field `markdown` · sha256 `sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f` · 7482 chars / 11574 bytes UTF-8 / 201 lines
**self-check verdict** `pass` — 6/6 acceptance items, 9/9 checks pass
**claims** `0` (by contract: register-only工序, `classify_report_type=false`)

## 1. 本工序做了什么

只执行契约声明的一件事：**登记 report 11267 的源资产与它声明过的附件/工件**，不做抽取、不做分类、不做 verified 判定。

- **源资产身份**：`tensor://reports/11267` 的 `markdown` 字段，本地重算 sha256 = `sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f`，
  与契约 `source_hash` 比对 `True`；字符数 7482（契约声明
  7482，一致 `True`）；记录侧身份
  title/scenario_key 与 YAML 一致 `True` / `True`。
- **工件清单**：从 markdown 正文文本驱动扫出 **23 个资产**（含源文档自身）：
  `resolved_in_source`=8 ·
  `referenced_unresolved`=8 ·
  `declared_absent`=7；
  按类：`{"cluster_job": 3, "code_module_path": 1, "code_script": 3, "data_artifact": 1, "declared_measurement_gap": 4, "figure_artifact": 7, "run_command": 1, "source_document": 1, "test_suite": 1, "test_symbol": 1}`。
- **payload 哈希**：7 张图不是"声明了但拿不到"，而是从
  `GET /tensor/reports/11267/figures/<name>` 真取到 PNG 字节（校验 PNG magic），
  逐个记录 `payload_sha256`（见 §3 表）。
- **声明缺失项**：报告自己声明未测量/未落地的 7 项
  （C1/C2/C4 判据未测量、MPIComm 后端未本机实测、cj308/cj313/cj314 集群作业排队中）
  登记为 `declared_absent`——登记"报告声明为空"，不是判其真伪。

## 2. 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET http://127.0.0.1:8010/api/v1/tensor/reports/11267`（Bearer token 由
   `POST /auth/login` 取得），只读这一份 report_id；markdown 落地
   `runs/wp-11267-01/source_11267.md`，记录落地 `runs/wp-11267-01/record_11267.json`。
2. **哈希独立重算**：`sha256(markdown.encode("utf-8"))`，与契约常量、manifest、envelope、
   磁盘副本四处对比（任何一处不等即 abort，未走软判定）。
3. **文本驱动发现资产**（不靠记忆、不靠人工列表）：markdown 图片链接正则、
   路径 token 正则（必带目录段 + 已知扩展名）、目录 token 正则（限 `src|scripts|tests|artifacts|figures|docs|data|examples|benchmarks|tools` 根）、
   `python -m <点分模块>`、反引号内的 `test_*` 符号、`cjNNN` 作业号、
   判据表中含 `not measured/未测量` 的行、以及 MPIComm 的"未在本机实测"警示句（该句与后端名
   不在同一行，按前向 6 行窗口匹配）。
4. **去重不丢定位**：同一路径多次出现折叠为一个资产，`all_locators` 保留每一处
   char span（如 `scripts/fem_parallel_report.py` 出现于 L5 与 L200；
   `python -m tensorphysics.fem_parallel.verification` 出现于 L4、L195、L196）。
   图名统一到正文链接形态（`figures/<name>.png`），因为 §4 以裸文件名复述同一批图。
5. **可解性判定**：每个 locator 记录 `start_char/end_char/start_line/quote`，判定口径为
   `quote in markdown` **且** `markdown[start:end] == quote` **且** 由 offset 重算的行号 == 声明行号。
6. **校验**：`jsonschema` draft-07 校验工序内 pinned 的 manifest schema
   （`docs/kf/wp-11267-01/asset_manifest.schema.json`，因其 consts 与 `schemas/asset_manifest.v1.schema.json`
   的 wp-448 绑定不同）+ draft-2020-12 校验 `schemas/kf_result.v1.schema.json`；
   校验前**重新拉取**一次原文，避免"验证自己的构建副本"。

## 3. 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-11267-01/asset_manifest.json` | 主产物：23 资产 / 34 个 locator / claims=[] / source hash |
| `docs/kf/wp-11267-01/kf_result.json` | 结果信封 `outputs["asset_manifest.json"]`，`provenance.source_hash`=sha256:2ca7aed6b4a37… |
| `docs/kf/wp-11267-01/asset_manifest.schema.json` | 本工序 manifest 形状的机器可校验 pin（schema_pass 可复跑） |
| `docs/kf/wp-11267-01/verification.json` | 9 条自检（6 acceptance + 3 integrity）逐条 metric 与 verdict |
| `docs/kf/wp-11267-01/figures/asset_registration_map.png` | 图 A 资产↔源行定位图；图 B 自检条带 |
| `runs/wp-11267-01/source_11267.md`、`record_11267.json` | 原文与记录快照（复算基准） |
| `scripts/kf_wp1126701_register_assets.py`、`scripts/kf_wp1126701_figure_report.py` | 一键复跑脚本 |

### 3.1 资产清单（逐条）

| asset | class | literal declaration (verbatim from markdown) | line | section | resolution | occurrences |
|---|---|---|---|---|---|---|
| A00 | source_document | `# MPI 域分解并行有限元基础设施（p284w3-n04-fem-mpi-parallel）` | 1 | (document root) | resolved_in_source | 1 |
| A01 | code_module_path | `src/tensorphysics/fem_parallel/` | 3 | (document root) | referenced_unresolved | 1 |
| A02 | run_command | `python -m tensorphysics.fem_parallel.verification` | 4 | (document root) | referenced_unresolved | 3 |
| A03 | data_artifact | `artifacts/fem_parallel/verification.json` | 5 | (document root) | referenced_unresolved | 2 |
| A04 | code_script | `scripts/fem_parallel_report.py` | 5 | (document root) | referenced_unresolved | 2 |
| A05 | declared_measurement_gap | `\| C1_strong_efficiency \| not measured \| 0.600000 \| P=16…` | 124 | 判据汇总 | declared_absent | 1 |
| A06 | declared_measurement_gap | `\| C2_weak_ratio \| not measured \| 1.500000 \| P=32 \| FAI…` | 125 | 判据汇总 | declared_absent | 1 |
| A07 | declared_measurement_gap | `\| C4_comm_fraction \| not measured \| 0.300000 \| P=16 \| …` | 126 | 判据汇总 | declared_absent | 1 |
| A08 | figure_artifact | `figures/strong_scaling.png` | 128 | 判据汇总 | resolved_in_source | 2 |
| A09 | figure_artifact | `figures/weak_scaling.png` | 129 | 判据汇总 | resolved_in_source | 2 |
| A10 | figure_artifact | `figures/communication.png` | 130 | 判据汇总 | resolved_in_source | 2 |
| A11 | figure_artifact | `figures/iterations.png` | 131 | 判据汇总 | resolved_in_source | 2 |
| A12 | figure_artifact | `figures/accuracy.png` | 132 | 判据汇总 | resolved_in_source | 2 |
| A13 | figure_artifact | `figures/load_balance.png` | 133 | 判据汇总 | resolved_in_source | 2 |
| A14 | figure_artifact | `figures/fields.png` | 134 | 判据汇总 | resolved_in_source | 2 |
| A15 | declared_measurement_gap | `   自动探测，但**未在本机实测**（如实声明，不作为本节点证据）。` | 162 | ⑤ 注意点（踩过的坑 / 局限） | declared_absent | 1 |
| A16 | cluster_job | `cj308` | 169 | ⑤ 注意点（踩过的坑 / 局限） | declared_absent | 1 |
| A17 | cluster_job | `cj313` | 169 | ⑤ 注意点（踩过的坑 / 局限） | declared_absent | 1 |
| A18 | cluster_job | `cj314` | 169 | ⑤ 注意点（踩过的坑 / 局限） | declared_absent | 1 |
| A19 | code_script | `scripts/fem_parallel_point.py` | 173 | ⑤ 注意点（踩过的坑 / 局限） | referenced_unresolved | 1 |
| A20 | test_symbol | `test_elasticity_patch_test_is_exact` | 186 | ⑥ 误差判定 | referenced_unresolved | 1 |
| A21 | test_suite | `tests/test_fem_parallel_*.py` | 197 | 复现 | referenced_unresolved | 1 |
| A22 | code_script | `scripts/fem_parallel_figures.py` | 198 | 复现 | referenced_unresolved | 1 |

### 3.2 图像 payload 探针

| figure (record caption) | in-body link | payload probe | bytes | payload sha256 | resolution |
|---|---|---|---|---|---|
| strong_scaling.png — 强扩展：S(P)、E(P)（仅求解 / 组装+setup+求解两种口 | yes | HTTP 200, png_magic=True | 96414 | `35630fb51a42dcb95315…` | resolved_in_source |
| weak_scaling.png — 弱扩展：T(P)/T(1) 随 P 变化，理想值 1，验收线 1.5 | yes | HTTP 200, png_magic=True | 59170 | `13b2b9a2c253d91b2f17…` | resolved_in_source |
| communication.png — 通信开销：T_comm/T_solve 随 P 变化，及 T_sol | yes | HTTP 200, png_magic=True | 85255 | `78d5bf9335730f01c4ff…` | resolved_in_source |
| iterations.png — CG / PCG-Jacobi / PCG-ASM 迭代数对比 | yes | HTTP 200, png_magic=True | 35144 | `c4e0136feef7d52c2db6…` | resolved_in_source |
| accuracy.png — Q1 制造解相对 L2 误差随 h 收敛（参考斜率 h²） | yes | HTTP 200, png_magic=True | 44985 | `dd5f74df6ea565252626…` | resolved_in_source |
| load_balance.png — 各秩本地组装/本地矩阵向量积耗时（负载均衡判据数据源） | yes | HTTP 200, png_magic=True | 33102 | `1e2eca93764bb5d37d0e…` | resolved_in_source |
| fields.png — 并行 FE 解场、解析解场与逐点误差云图（制造解算例） | yes | HTTP 200, png_magic=True | 98452 | `67c1e04da83ef640efcd…` | resolved_in_source |

图注（record metadata）：strong_scaling.png = 强扩展：S(P)、E(P)（仅求解 / 组装+setup+求解两种口径，含验收线 E=0.6）; weak_scaling.png = 弱扩展：T(P)/T(1) 随 P 变化，理想值 1，验收线 1.5; communication.png = 通信开销：T_comm/T_solve 随 P 变化，及 T_solve、T_comm 绝对值; iterations.png = CG / PCG-Jacobi / PCG-ASM 迭代数对比; accuracy.png = Q1 制造解相对 L2 误差随 h 收敛（参考斜率 h²）; load_balance.png = 各秩本地组装/本地矩阵向量积耗时（负载均衡判据数据源）; fields.png = 并行 FE 解场、解析解场与逐点误差云图（制造解算例）。

## 4. 证据定位表（claim/字段 → 原文引文）

本节列**全部** 34 个 locator（资产定位，非知识 claim）：`asset | quote | char span | line | 是否唯一 | 重解析结果`。

| asset | locator quote | char span | line | unique | re-resolved |
|---|---|---|---|---|---|
| A00 | `# MPI 域分解并行有限元基础设施（p284w3-n04-fem-mpi-parallel）` | 0–47 | 1 | yes | yes |
| A01 | `src/tensorphysics/fem_parallel/` | 75–106 | 3 | yes | yes |
| A02 | `python -m tensorphysics.fem_parallel.verification` | 133–182 | 4 | repeat | yes |
| A02 | `python -m tensorphysics.fem_parallel.verification` | 6678–6727 | 174 | repeat | yes |
| A02 | `python -m tensorphysics.fem_parallel.verification` | 7190–7239 | 195 | repeat | yes |
| A03 | `artifacts/fem_parallel/verification.json` | 193–233 | 5 | repeat | yes |
| A03 | `artifacts/fem_parallel/verification.json` | 7311–7351 | 196 | repeat | yes |
| A04 | `scripts/fem_parallel_report.py` | 242–272 | 5 | repeat | yes |
| A04 | `scripts/fem_parallel_report.py` | 7447–7477 | 199 | repeat | yes |
| A05 | `\| C1_strong_efficiency \| not measured \| 0.600000 \…` | 4472–4542 | 124 | yes | yes |
| A06 | `\| C2_weak_ratio \| not measured \| 1.500000 \| P=32 …` | 4543–4606 | 125 | yes | yes |
| A07 | `\| C4_comm_fraction \| not measured \| 0.300000 \| P=…` | 4607–4673 | 126 | yes | yes |
| A08 | `figures/strong_scaling.png` | 4682–4708 | 128 | yes | yes |
| A08 | `strong_scaling.png` | 4913–4931 | 138 | yes | yes |
| A09 | `figures/weak_scaling.png` | 4717–4741 | 129 | yes | yes |
| A09 | `weak_scaling.png` | 4978–4994 | 139 | yes | yes |
| A10 | `figures/communication.png` | 4751–4776 | 130 | yes | yes |
| A10 | `communication.png` | 5031–5048 | 140 | yes | yes |
| A11 | `figures/iterations.png` | 4785–4807 | 131 | yes | yes |
| A11 | `iterations.png` | 5096–5110 | 141 | yes | yes |
| A12 | `figures/accuracy.png` | 4815–4835 | 132 | yes | yes |
| A12 | `accuracy.png` | 5146–5158 | 142 | yes | yes |
| A13 | `figures/load_balance.png` | 4845–4869 | 133 | yes | yes |
| A13 | `load_balance.png` | 5195–5211 | 143 | yes | yes |
| A14 | `figures/fields.png` | 4877–4895 | 134 | yes | yes |
| A14 | `fields.png` | 5246–5256 | 144 | yes | yes |
| A15 | `   自动探测，但**未在本机实测**（如实声明，不作为本节点证据）。` | 6086–6121 | 162 | yes | yes |
| A16 | `cj308` | 6405–6410 | 169 | yes | yes |
| A17 | `cj313` | 6416–6421 | 169 | yes | yes |
| A18 | `cj314` | 6430–6435 | 169 | yes | yes |
| A19 | `scripts/fem_parallel_point.py` | 6633–6662 | 173 | yes | yes |
| A20 | `test_elasticity_patch_test_is_exact` | 7016–7051 | 186 | yes | yes |
| A21 | `tests/test_fem_parallel_*.py` | 7369–7397 | 197 | yes | yes |
| A22 | `scripts/fem_parallel_figures.py` | 7408–7439 | 198 | yes | yes |

非 markdown 来源的证据（同样零手抄，均由脚本采集）：

| 字段 | 来源 | 值 |
|---|---|---|
| `source.hash` | http GET + sha256 重算 | `sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f` |
| `source.record_figures[*].payload_probe` | GET /tensor/reports/11267/figures/<name> | 7/7 HTTP 200，PNG magic 全部 True |
| `source.artifact_endpoint_probe` | GET /tensor/reports/11267/artifacts | HTTP 404 `{"detail":"Not Found"}` |
| `source.title / scenario_key` | 记录字段 | `TensorPhysics: MPI 域分解并行 FEM 基础设施与强/弱扩展验证 (p284w3-n04)` / `p284w3-n04-fem-mpi-parallel` |

## 5. 注意点与局限

1. **本工序不判定真伪**：23 个资产里 `declared_absent` 7 项只是"报告自己说没有/没测"，
   `resolution_check=none` 意义上的缺席**没有**被独立核实（例如 cj308 是否真的仍在排队，
   本工序未去调度器查证）；下游若要使用，须自行复核。
2. **`referenced_unresolved` 8 项不是丢件**：`src/tensorphysics/fem_parallel/`、
   `scripts/fem_parallel_*.py`、`artifacts/fem_parallel/verification.json`、
   `tests/test_fem_parallel_*.py`、`test_elasticity_patch_test_is_exact` 等都属交付仓
   TensorPhysics（原文第 3 行明示），不在 TensorKnowledge 工作树内，因此在本工序范围内
   无法取到 payload；已如实标记，未伪造哈希。
3. **图名归一化**是唯一一处"名字改写"：§4 用裸文件名复述 7 张图，若按字面登记会与 §3
   的 `figures/xxx.png` 形成 7 对重复资产；故 name 统一为正文链接形态，**literal quote 仍逐字保留**
   （`all_locators[*].quote` 为各处原文 token）。
4. **资产发现是文本驱动的**，不是 API 清单：平台侧若存在报告未在正文提及的附件，
   本工序看不见（`/artifacts` 端点对 11267 返回 HTTP
   404，即无独立工件索引可对表）。这是本方法的天花板，
   如需穷尽须平台提供工件清单接口。
5. **`claims=[]` 是契约要求，不是漏做**：`objective.classify_report_type=false`、
   `no_forced_claim_generation=true`、notes 明言"claims 允许为空数组"。任何把报告数字搬进
   claims 的做法都会越界成抽取工序。
6. **未做的事**：未读/未写其它 report_id；未改上游产物；未给任何结论打 verified；未对
   报告数值做复算。

## 6. 自检（逐条对照 acceptance）

- [x] `valid_json` — pass (C1_valid_json)
- [x] `schema_pass` — pass (C2_schema_pass)
- [x] `source_locator_resolvable` — pass (C3_source_locator_resolvable)
- [x] `source_hash_matches` — pass (C4_source_hash_matches)
- [x] `no_duplicate_ids` — pass (C5_no_duplicate_ids)
- [x] `all_claims_have_evidence_or_explicit_unresolved_status` — pass (C6_claims_evidence_or_status)

- **X1_contract_identity** PASS、**X2_figure_caption_coverage** PASS、**X3_report_scope** PASS（附加完整性检查，非契约 acceptance 项）

逐条 metric：

| check | acceptance item | status | metric |
|---|---|---|---|
| C1_valid_json | valid_json | **pass** | `{"manifest_bytes": 47009, "envelope_bytes": 50362}` |
| C2_schema_pass | schema_pass | **pass** | `{"manifest_errors": [], "envelope_errors": []}` |
| C3_source_locator_resolvable | source_locator_resolvable | **pass** | `{"locators_checked": 34, "failures": []}` |
| C4_source_hash_matches | source_hash_matches | **pass** | `{"recomputed": "sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f", "contract": "sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f", "manifest": "sha256:2ca7aed6b4a376b61e38…` |
| C5_no_duplicate_ids | no_duplicate_ids | **pass** | `{"assets": 23, "duplicate_ids": [], "duplicate_names": []}` |
| C6_claims_evidence_or_status | all_claims_have_evidence_or_explicit_unresolved_status | **pass** | `{"claims": 0, "claims_without_evidence_or_status": 0, "claims_empty_reason_present": true, "verified_marks_present": false}` |
| X1_contract_identity | extra: source identity matches the work-package YAML | **pass** | `{"record_title": "TensorPhysics: MPI 域分解并行 FEM 基础设施与强/弱扩展验证 (p284w3-n04)", "record_scenario_key": "p284w3-n04-fem-mpi-parallel"}` |
| X2_figure_caption_coverage | extra: every record figure is referenced in body | **pass** | `{"record_figures": 7, "referenced_in_body": 7, "payload_served": 7}` |
| X3_report_scope | extra: single report_id touched | **pass** | `{"manifest_report_id": "11267", "envelope_report_id": "11267", "source_uri": "tensor://reports/11267"}` |

**声明缺失项登记（declared_absent，逐条原文）**：

- `C1_strong_efficiency` (declared_measurement_gap, line 124): `| C1_strong_efficiency | not measured | 0.600000 | P=16 | FAIL (未测量) |`
- `C2_weak_ratio` (declared_measurement_gap, line 125): `| C2_weak_ratio | not measured | 1.500000 | P=32 | FAIL (未测量) |`
- `C4_comm_fraction` (declared_measurement_gap, line 126): `| C4_comm_fraction | not measured | 0.300000 | P=16 | FAIL (未测量) |`
- `MPIComm_local_measurement` (declared_measurement_gap, line 162): `   自动探测，但**未在本机实测**（如实声明，不作为本节点证据）。`
- `cj308` (cluster_job, line 169): `cj308`
- `cj313` (cluster_job, line 169): `cj313`
- `cj314` (cluster_job, line 169): `cj314`

**未解析项清单**（15 条 → 见 `asset_manifest.json.unresolved`）；其中
`referenced_unresolved` 的原因统一为"payload 在工作树之外"，`declared_absent` 为"报告自述缺席"。

**honest 说明**：本工序没有 FAIL 项；但 `all_claims_have_evidence_or_explicit_unresolved_status`
是**空集上的真**（claims=[]），已在 `asset_manifest.json.claims_empty_reason` 与
`verification.json` 的 metric 中显式记录，不是"跑绿了就当做过"。

## 附A. 结果图（图件内嵌）

![asset registration coverage](figures/asset_registration_map.png)

*图 A（左）：把 23 个资产按其首个 locator 的行号投到 201 行源文本轴上，
颜色=resolution（绿=本工序取到 payload/哈希，橙=声明可定位但 payload 在交付仓外，红=报告自述缺席）；
实心大点=首个 locator，半透明小点=同一资产的其余出现位置；虚线=S 段界（宿主机无 CJK 字体，
故用 S1..S7 标注：S1=① 案例介绍(L8); S2=② 方法(L38); S3=③ 计算结果(L57); S4=④ 结果图说明(L136); S5=⑤ 注意点（踩过的坑 / 局限）(L146); S6=⑥ 误差判定(L176); S7=复现(L191)）。
图 B（右）：6 项 acceptance + 3 项 integrity 自检的通过/失败条带，本工序 verdict=`pass`。
本工序为登记类工序，无物理场量/无量纲曲线；平台要求附图，故以"定位覆盖图 + 自检条带"
这一可核对的可视化替代场量云图。*

## 复现

```bash
cd <TensorKnowledge worktree>
export TENSOR_API_BASE=http://127.0.0.1:8010/api/v1
python3 scripts/kf_wp1126701_register_assets.py all   # build + envelope + verify (9/9 pass)
python3 scripts/kf_wp1126701_figure_report.py all     # figure + render + publish
```

```json
{
 "package_id": "wp-11267-01",
 "task_type": "01-asset-registration",
 "report_id": "11267",
 "provenance": {
  "source_hash": "sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f",
  "source_field": "markdown",
  "producer": "kf-worker/m15695",
  "emitted_at": "2026-11-12T01:54:18.481719+00:00",
  "notes": "source_hash recomputed from the live markdown bytes fetched via GET /api/v1/tensor/reports/11267; equals the contract-declared hash"
 },
 "outputs": {
  "asset_manifest.json": {
   "schema": "asset_manifest.v1",
   "manifest_version": "1.0",
   "package_id": "wp-11267-01",
   "task_type": "01-asset-registration",
   "report_id": "11267",
   "lane": "C",
   "generated_at": "2026-11-12T01:54:18.476889+00:00",
   "producer": "kf-worker/m15695",
   "scope": {
    "registers": "source asset identity (report_id + markdown byte hash) and the attachments/artifacts the report declares",
    "does_not": [
     "claim extraction (claims == [])",
     "report-type classification (contract: classify_report_type=false)",
     "verification (the platform gate computes it)",
     "reading or writing any other report_id"
    ]
   },
   "source": {
    "report_id": "11267",
    "uri": "tensor://reports/11267",
    "field": "markdown",
    "hash_alg": "sha256",
    "hash": "sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f",
    "contract_hash": "sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f",
    "hash_matches_contract": true,
    "chars": 7482,
    "contract_chars": 7482,
    "chars_match_contract": true,
    "bytes_utf8": 11574,
    "lines": 201,
    "has_trailing_newline": true,
    "line_counting": "logical lines = markdown.split(chr(10)); 1-based",
    "fetched_via": "GET /api/v1/tensor/reports/11267",
    "local_copy": "runs/wp-11267-01/source_11267.md",
    "title": "TensorPhysics: MPI 域分解并行 FEM 基础设施与强/弱扩展验证 (p284w3-n04)",
    "scenario_key": "p284w3-n04-fem-mpi-parallel",
    "mission_id": 9417,
    "status": "published",
    "created_at": "2026-11-10T12:34:22.323023+00:00",
    "tags": [
     "FEM",
     "MPI",
     "domain-decomposition",
     "PCG",
     "strong-scaling",
     "weak-scaling",
     "communication-overhead",
     "TensorPhysics"
    ],
    "contract_title": "TensorPhysics: MPI 域分解并行 FEM 基础设施与强/弱扩展验证 (p284w3-n04)",
    "contract_scenario_key": "p284w3-n04-fem-mpi-parallel",
    "title_matches_contract": true,
    "scenario_matches_contract": true,
    "record_figures": [
     {
      "index": 0,
      "name": "strong_scaling.png",
      "caption": "强扩展：S(P)、E(P)（仅求解 / 组装+setup+求解两种口径，含验收线 E=0.6）",
      "referenced_in_body": true,
      "api_pointer": "/figures/0",
      "payload_probe": {
       "http_status": 200,
       "bytes": 96414,
       "sha256": "sha256:35630fb51a42dcb95315a484902b023fcc19d068cc8247cb4c398860dfda629f",
       "png_magic": true,
       "looks_like_json_error": false
      }
     },
     {
      "index": 1,
      "name": "weak_scaling.png",
      "caption": "弱扩展：T(P)/T(1) 随 P 变化，理想值 1，验收线 1.5",
      "referenced_in_body": true,
      "api_pointer": "/figures/1",
      "payload_probe": {
       "http_status": 200,
       "bytes": 59170,
       "sha256": "sha256:13b2b9a2c253d91b2f17a5fca299b0518fd5729ad41c45a7a2f6ed37ee926426",
       "png_magic": true,
       "looks_like_json_error": false
      }
     },
     {
      "index": 2,
      "name": "communication.png",
      "caption": "通信开销：T_comm/T_solve 随 P 变化，及 T_solve、T_comm 绝对值",
      "referenced_in_body": true,
      "api_pointer": "/figures/2",
      "payload_probe": {
       "http_status": 200,
       "bytes": 85255,
       "sha256": "sha256:78d5bf9335730f01c4ffbc3365a91e4c149f01af793764de08aa7241d92e5049",
       "png_magic": true,
       "looks_like_json_error": false
      }
     },
     {
      "index": 3,
      "name": "iterations.png",
      "caption": "CG / PCG-Jacobi / PCG-ASM 迭代数对比",
      "referenced_in_body": true,
      "api_pointer": "/figures/3",
      "payload_probe": {
       "http_status": 200,
       "bytes": 35144,
       "sha256": "sha256:c4e0136feef7d52c2db6273846489c4aa9d99c4f1820b6e36e20f3fffa7eeb54",
       "png_magic": true,
       "looks_like_json_error": false
      }
     },
     {
      "index": 4,
      "name": "accuracy.png",
      "caption": "Q1 制造解相对 L2 误差随 h 收敛（参考斜率 h²）",
      "referenced_in_body": true,
      "api_pointer": "/figures/4",
      "payload_probe": {
       "http_status": 200,
       "bytes": 44985,
       "sha256": "sha256:dd5f74df6ea565252626267caa946ad48e95ad96894bbacd61c72f0bbdd6e3a7",
       "png_magic": true,
       "looks_like_json_error": false
      }
     },
     {
      "index": 5,
      "name": "load_balance.png",
      "caption": "各秩本地组装/本地矩阵向量积耗时（负载均衡判据数据源）",
      "referenced_in_body": true,
      "api_pointer": "/figures/5",
      "payload_probe": {
       "http_status": 200,
       "bytes": 33102,
       "sha256": "sha256:1e2eca93764bb5d37d0e36b89a396fd731f6d3cf49176dc1cd5d4951f9aea99d",
       "png_magic": true,
       "looks_like_json_error": false
      }
     },
     {
      "index": 6,
      "name": "fields.png",
      "caption": "并行 FE 解场、解析解场与逐点误差云图（制造解算例）",
      "referenced_in_body": true,
      "api_pointer": "/figures/6",
      "payload_probe": {
       "http_status": 200,
       "bytes": 98452,
       "sha256": "sha256:67c1e04da83ef640efcd349561e0dcfe292f0ce2626fec681a3aaaa7abf6c977",
       "png_magic": true,
       "looks_like_json_error": false
      }
     }
    ],
    "artifact_endpoint_probe": {
     "path": "/tensor/reports/11267/artifacts",
     "http_status": 404,
     "bytes": 22,
     "body_head": "{\"detail\":\"Not Found\"}"
    },
    "figure_endpoint_probes": {
     "strong_scaling.png": {
      "http_status": 200,
      "bytes": 96414,
      "sha256": "sha256:35630fb51a42dcb95315a484902b023fcc19d068cc8247cb4c398860dfda629f",
      "png_magic": true,
      "looks_like_json_error": false
     },
     "weak_scaling.png": {
      "http_status": 200,
      "bytes": 59170,
      "sha256": "sha256:13b2b9a2c253d91b2f17a5fca299b0518fd5729ad41c45a7a2f6ed37ee926426",
      "png_magic": true,
      "looks_like_json_error": false
     },
     "communication.png": {
      "http_status": 200,
      "bytes": 85255,
      "sha256": "sha256:78d5bf9335730f01c4ffbc3365a91e4c149f01af793764de08aa7241d92e5049",
      "png_magic": true,
      "looks_like_json_error": false
     },
     "iterations.png": {
      "http_status": 200,
      "bytes": 35144,
      "sha256": "sha256:c4e0136feef7d52c2db6273846489c4aa9d99c4f1820b6e36e20f3fffa7eeb54",
      "png_magic": true,
      "looks_like_json_error": false
     },
     "accuracy.png": {
      "http_status": 200,
      "bytes": 44985,
      "sha256": "sha256:dd5f74df6ea565252626267caa946ad48e95ad96894bbacd61c72f0bbdd6e3a7",
      "png_magic": true,
      "looks_like_json_error": false
     },
     "load_balance.png": {
      "http_status": 200,
      "bytes": 33102,
      "sha256": "sha256:1e2eca93764bb5d37d0e36b89a396fd731f6d3cf49176dc1cd5d4951f9aea99d",
      "png_magic": true,
      "looks_like_json_error": false
     },
     "fields.png": {
      "http_status": 200,
      "bytes": 98452,
      "sha256": "sha256:67c1e04da83ef640efcd349561e0dcfe292f0ce2626fec681a3aaaa7abf6c977",
      "png_magic": true,
      "looks_like_json_error": false
     }
    }
   },
   "counts": {
    "assets": 23,
    "by_class": {
     "cluster_job": 3,
     "code_module_path": 1,
     "code_script": 3,
     "data_artifact": 1,
     "declared_measurement_gap": 4,
     "figure_artifact": 7,
     "run_command": 1,
     "source_document": 1,
     "test_suite": 1,
     "test_symbol": 1
    },
    "by_resolution": {
     "declared_absent": 7,
     "referenced_unresolved": 8,
     "resolved_in_source": 8
    },
    "resolved_in_source": 8,
    "referenced_unresolved": 8,
    "declared_absent": 7,
    "body_image_links": 7,
    "figure_references_total": 14,
    "distinct_referenced_paths": 15,
    "claims": 0
   },
   "assets": [
    {
     "asset_id": "A00",
     "asset_class": "source_document",
     "label": "report 11267 markdown (H1 title line as identity quote)",
     "name": "tensor://reports/11267#markdown",
     "in_report_section": "(document root)",
     "locator": {
      "method": "document",
      "start_char": 0,
      "end_char": 7482,
      "start_line": 1,
      "end_line": 201,
      "quote": "# MPI 域分解并行有限元基础设施（p284w3-n04-fem-mpi-parallel）",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 1,
       "start_char": 0,
       "end_char": 47,
       "quote": "# MPI 域分解并行有限元基础设施（p284w3-n04-fem-mpi-parallel）",
       "quote_sha256": "sha256:56f3b8c7e71af50d8a7f81781322aaff52464c114802df5da66afc643a9066eb",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "document",
     "occurrence_count": 1,
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "sha256(markdown utf-8 bytes) recomputed locally",
      "result": "resolved",
      "algorithm": "sha256",
      "recomputed": "sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f",
      "contract_declared": "sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f",
      "match": true
     },
     "note": "the registered asset of this工序 is the report markdown itself; the hash is recomputed here, not copied from the contract"
    },
    {
     "asset_id": "A01",
     "asset_class": "code_module_path",
     "label": "src/tensorphysics/fem_parallel/",
     "name": "src/tensorphysics/fem_parallel/",
     "in_report_section": "(document root)",
     "locator": {
      "method": "char_span",
      "start_char": 75,
      "end_char": 106,
      "start_line": 3,
      "end_line": 3,
      "quote": "src/tensorphysics/fem_parallel/",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 3,
       "start_char": 75,
       "end_char": 106,
       "quote": "src/tensorphysics/fem_parallel/",
       "quote_sha256": "sha256:7b9952d5181093612a3c012d1a964b84f676689aee380671814cedd2b701789e",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "directory_token",
     "occurrence_count": 1,
     "resolution": "referenced_unresolved",
     "resolution_check": {
      "check": "path exists in TensorKnowledge worktree: src/tensorphysics/fem_parallel/",
      "result": "unresolved",
      "path": "/root/tp-agent/work/m15695/src/tensorphysics/fem_parallel"
     },
     "note": "declared path belongs to the delivery repo named at line 3 (TensorPhysics, src/tensorphysics/fem_parallel); the payload is outside this工序's worktree -> declared reference, unresolvable here"
    },
    {
     "asset_id": "A02",
     "asset_class": "run_command",
     "label": "tensorphysics.fem_parallel.verification",
     "name": "tensorphysics.fem_parallel.verification",
     "in_report_section": "(document root)",
     "locator": {
      "method": "char_span",
      "start_char": 133,
      "end_char": 182,
      "start_line": 4,
      "end_line": 4,
      "quote": "python -m tensorphysics.fem_parallel.verification",
      "unique": false
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 4,
       "start_char": 133,
       "end_char": 182,
       "quote": "python -m tensorphysics.fem_parallel.verification",
       "quote_sha256": "sha256:36e7c0e95f3d40463423d5d19a542ca0642f5f67f5e0b48c10bc9cc013219932",
       "quote_in_source": true,
       "on_declared_span": true
      },
      {
       "source_field": "markdown",
       "line": 174,
       "start_char": 6678,
       "end_char": 6727,
       "quote": "python -m tensorphysics.fem_parallel.verification",
       "quote_sha256": "sha256:36e7c0e95f3d40463423d5d19a542ca0642f5f67f5e0b48c10bc9cc013219932",
       "quote_in_source": true,
       "on_declared_span": true
      },
      {
       "source_field": "markdown",
       "line": 195,
       "start_char": 7190,
       "end_char": 7239,
       "quote": "python -m tensorphysics.fem_parallel.verification",
       "quote_sha256": "sha256:36e7c0e95f3d40463423d5d19a542ca0642f5f67f5e0b48c10bc9cc013219932",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "module_entrypoint",
     "occurrence_count": 3,
     "resolution": "referenced_unresolved",
     "resolution_check": {
      "check": "path exists in TensorKnowledge worktree: tensorphysics.fem_parallel.verification",
      "result": "unresolved",
      "path": "/root/tp-agent/work/m15695/tensorphysics.fem_parallel.verification"
     },
     "note": "declared path belongs to the delivery repo named at line 3 (TensorPhysics, src/tensorphysics/fem_parallel); the payload is outside this工序's worktree -> declared reference, unresolvable here"
    },
    {
     "asset_id": "A03",
     "asset_class": "data_artifact",
     "label": "artifacts/fem_parallel/verification.json",
     "name": "artifacts/fem_parallel/verification.json",
     "in_report_section": "(document root)",
     "locator": {
      "method": "char_span",
      "start_char": 193,
      "end_char": 233,
      "start_line": 5,
      "end_line": 5,
      "quote": "artifacts/fem_parallel/verification.json",
      "unique": false
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 5,
       "start_char": 193,
       "end_char": 233,
       "quote": "artifacts/fem_parallel/verification.json",
       "quote_sha256": "sha256:a1506063dd8e7716b759af94275d5bb0c4087d6b784e8321afff1c803abe3d97",
       "quote_in_source": true,
       "on_declared_span": true
      },
      {
       "source_field": "markdown",
       "line": 196,
       "start_char": 7311,
       "end_char": 7351,
       "quote": "artifacts/fem_parallel/verification.json",
       "quote_sha256": "sha256:a1506063dd8e7716b759af94275d5bb0c4087d6b784e8321afff1c803abe3d97",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "path_token",
     "occurrence_count": 2,
     "resolution": "referenced_unresolved",
     "resolution_check": {
      "check": "path exists in TensorKnowledge worktree: artifacts/fem_parallel/verification.json",
      "result": "unresolved",
      "path": "/root/tp-agent/work/m15695/artifacts/fem_parallel/verification.json"
     },
     "note": "declared path belongs to the delivery repo named at line 3 (TensorPhysics, src/tensorphysics/fem_parallel); the payload is outside this工序's worktree -> declared reference, unresolvable here"
    },
    {
     "asset_id": "A04",
     "asset_class": "code_script",
     "label": "scripts/fem_parallel_report.py",
     "name": "scripts/fem_parallel_report.py",
     "in_report_section": "(document root)",
     "locator": {
      "method": "char_span",
      "start_char": 242,
      "end_char": 272,
      "start_line": 5,
      "end_line": 5,
      "quote": "scripts/fem_parallel_report.py",
      "unique": false
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 5,
       "start_char": 242,
       "end_char": 272,
       "quote": "scripts/fem_parallel_report.py",
       "quote_sha256": "sha256:706322f34ba02a5557cb30fae8224070e70b5a0926f2754f7d1dd4cb437e9a1b",
       "quote_in_source": true,
       "on_declared_span": true
      },
      {
       "source_field": "markdown",
       "line": 199,
       "start_char": 7447,
       "end_char": 7477,
       "quote": "scripts/fem_parallel_report.py",
       "quote_sha256": "sha256:706322f34ba02a5557cb30fae8224070e70b5a0926f2754f7d1dd4cb437e9a1b",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "path_token",
     "occurrence_count": 2,
     "resolution": "referenced_unresolved",
     "resolution_check": {
      "check": "path exists in TensorKnowledge worktree: scripts/fem_parallel_report.py",
      "result": "unresolved",
      "path": "/root/tp-agent/work/m15695/scripts/fem_parallel_report.py"
     },
     "note": "declared path belongs to the delivery repo named at line 3 (TensorPhysics, src/tensorphysics/fem_parallel); the payload is outside this工序's worktree -> declared reference, unresolvable here"
    },
    {
     "asset_id": "A05",
     "asset_class": "declared_measurement_gap",
     "label": "C1_strong_efficiency",
     "name": "C1_strong_efficiency",
     "in_report_section": "判据汇总",
     "locator": {
      "method": "char_span",
      "start_char": 4472,
      "end_char": 4542,
      "start_line": 124,
      "end_line": 124,
      "quote": "| C1_strong_efficiency | not measured | 0.600000 | P=16 | FAIL (未测量) |",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 124,
       "start_char": 4472,
       "end_char": 4542,
       "quote": "| C1_strong_efficiency | not measured | 0.600000 | P=16 | FAIL (未测量) |",
       "quote_sha256": "sha256:fa4f8a6e086afaff755007cb492af0ec8929f26d0d67cee8679d8ff8e7320bff",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "criteria_table_row",
     "occurrence_count": 1,
     "resolution": "declared_absent",
     "resolution_check": {
      "check": "report itself declares this artefact/measurement absent or unmeasured",
      "result": "absent",
      "worktree_probe": {
       "check": "path exists in TensorKnowledge worktree: C1_strong_efficiency",
       "result": "unresolved",
       "path": "/root/tp-agent/work/m15695/C1_strong_efficiency"
      }
     },
     "note": "the report states the artefact is absent/queued/not measured; registered as declared_absent -- registration of a declared gap, NOT a claim and NOT a verified finding"
    },
    {
     "asset_id": "A06",
     "asset_class": "declared_measurement_gap",
     "label": "C2_weak_ratio",
     "name": "C2_weak_ratio",
     "in_report_section": "判据汇总",
     "locator": {
      "method": "char_span",
      "start_char": 4543,
      "end_char": 4606,
      "start_line": 125,
      "end_line": 125,
      "quote": "| C2_weak_ratio | not measured | 1.500000 | P=32 | FAIL (未测量) |",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 125,
       "start_char": 4543,
       "end_char": 4606,
       "quote": "| C2_weak_ratio | not measured | 1.500000 | P=32 | FAIL (未测量) |",
       "quote_sha256": "sha256:7e18143036db51f40a79765ac05d282b81649202ffa7af68adccfce991451261",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "criteria_table_row",
     "occurrence_count": 1,
     "resolution": "declared_absent",
     "resolution_check": {
      "check": "report itself declares this artefact/measurement absent or unmeasured",
      "result": "absent",
      "worktree_probe": {
       "check": "path exists in TensorKnowledge worktree: C2_weak_ratio",
       "result": "unresolved",
       "path": "/root/tp-agent/work/m15695/C2_weak_ratio"
      }
     },
     "note": "the report states the artefact is absent/queued/not measured; registered as declared_absent -- registration of a declared gap, NOT a claim and NOT a verified finding"
    },
    {
     "asset_id": "A07",
     "asset_class": "declared_measurement_gap",
     "label": "C4_comm_fraction",
     "name": "C4_comm_fraction",
     "in_report_section": "判据汇总",
     "locator": {
      "method": "char_span",
      "start_char": 4607,
      "end_char": 4673,
      "start_line": 126,
      "end_line": 126,
      "quote": "| C4_comm_fraction | not measured | 0.300000 | P=16 | FAIL (未测量) |",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 126,
       "start_char": 4607,
       "end_char": 4673,
       "quote": "| C4_comm_fraction | not measured | 0.300000 | P=16 | FAIL (未测量) |",
       "quote_sha256": "sha256:11e0d978397c3ba23baf380a8abae6aa5f2820179b1f1d4785951a2a9bc97730",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "criteria_table_row",
     "occurrence_count": 1,
     "resolution": "declared_absent",
     "resolution_check": {
      "check": "report itself declares this artefact/measurement absent or unmeasured",
      "result": "absent",
      "worktree_probe": {
       "check": "path exists in TensorKnowledge worktree: C4_comm_fraction",
       "result": "unresolved",
       "path": "/root/tp-agent/work/m15695/C4_comm_fraction"
      }
     },
     "note": "the report states the artefact is absent/queued/not measured; registered as declared_absent -- registration of a declared gap, NOT a claim and NOT a verified finding"
    },
    {
     "asset_id": "A08",
     "asset_class": "figure_artifact",
     "label": "强扩展",
     "name": "figures/strong_scaling.png",
     "in_report_section": "判据汇总",
     "locator": {
      "method": "char_span",
      "start_char": 4682,
      "end_char": 4708,
      "start_line": 128,
      "end_line": 128,
      "quote": "figures/strong_scaling.png",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 128,
       "start_char": 4682,
       "end_char": 4708,
       "quote": "figures/strong_scaling.png",
       "quote_sha256": "sha256:62a144dbbc2f105dbecdd60bf67b8e4a325011bddd0661b3666286b10d18fa0c",
       "quote_in_source": true,
       "on_declared_span": true
      },
      {
       "source_field": "markdown",
       "line": 138,
       "start_char": 4913,
       "end_char": 4931,
       "quote": "strong_scaling.png",
       "quote_sha256": "sha256:08f31f7725986b3ac4f683a581eba0cad99fc83fc73858940a109748c0d203cd",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "markdown_image_link",
     "occurrence_count": 2,
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "GET /tensor/reports/11267/figures/strong_scaling.png",
      "result": "resolved",
      "http_status": 200,
      "bytes": 96414,
      "payload_sha256": "sha256:35630fb51a42dcb95315a484902b023fcc19d068cc8247cb4c398860dfda629f",
      "png_magic": true,
      "worktree_probe": {
       "check": "path exists in TensorKnowledge worktree: figures/strong_scaling.png",
       "result": "unresolved",
       "path": "/root/tp-agent/work/m15695/figures/strong_scaling.png"
      }
     },
     "note": "payload fetched from GET /tensor/reports/11267/figures/<name> (PNG magic checked) -> payload_sha256 is the hash of the bytes actually served; the caption is also declared in the record metadata"
    },
    {
     "asset_id": "A09",
     "asset_class": "figure_artifact",
     "label": "弱扩展",
     "name": "figures/weak_scaling.png",
     "in_report_section": "判据汇总",
     "locator": {
      "method": "char_span",
      "start_char": 4717,
      "end_char": 4741,
      "start_line": 129,
      "end_line": 129,
      "quote": "figures/weak_scaling.png",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 129,
       "start_char": 4717,
       "end_char": 4741,
       "quote": "figures/weak_scaling.png",
       "quote_sha256": "sha256:fdcd0c73c59ab5e99c10974f65036a86597ceae869eeee3ab182cb625ce5baf1",
       "quote_in_source": true,
       "on_declared_span": true
      },
      {
       "source_field": "markdown",
       "line": 139,
       "start_char": 4978,
       "end_char": 4994,
       "quote": "weak_scaling.png",
       "quote_sha256": "sha256:9049582d7d3083be77303c6a098c939370e6b5db41113f7a01e742ca0eadb129",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "markdown_image_link",
     "occurrence_count": 2,
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "GET /tensor/reports/11267/figures/weak_scaling.png",
      "result": "resolved",
      "http_status": 200,
      "bytes": 59170,
      "payload_sha256": "sha256:13b2b9a2c253d91b2f17a5fca299b0518fd5729ad41c45a7a2f6ed37ee926426",
      "png_magic": true,
      "worktree_probe": {
       "check": "path exists in TensorKnowledge worktree: figures/weak_scaling.png",
       "result": "unresolved",
       "path": "/root/tp-agent/work/m15695/figures/weak_scaling.png"
      }
     },
     "note": "payload fetched from GET /tensor/reports/11267/figures/<name> (PNG magic checked) -> payload_sha256 is the hash of the bytes actually served; the caption is also declared in the record metadata"
    },
    {
     "asset_id": "A10",
     "asset_class": "figure_artifact",
     "label": "通信开销",
     "name": "figures/communication.png",
     "in_report_section": "判据汇总",
     "locator": {
      "method": "char_span",
      "start_char": 4751,
      "end_char": 4776,
      "start_line": 130,
      "end_line": 130,
      "quote": "figures/communication.png",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 130,
       "start_char": 4751,
       "end_char": 4776,
       "quote": "figures/communication.png",
       "quote_sha256": "sha256:b0d59a1221a6fe35e2de16c3c2ce98436677eb6a0da72aa841afeafa65c65755",
       "quote_in_source": true,
       "on_declared_span": true
      },
      {
       "source_field": "markdown",
       "line": 140,
       "start_char": 5031,
       "end_char": 5048,
       "quote": "communication.png",
       "quote_sha256": "sha256:d80438e8d18f3e633e973f65b165c3d8253d6b14a08cddeab03119e9ef70dd3a",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "markdown_image_link",
     "occurrence_count": 2,
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "GET /tensor/reports/11267/figures/communication.png",
      "result": "resolved",
      "http_status": 200,
      "bytes": 85255,
      "payload_sha256": "sha256:78d5bf9335730f01c4ffbc3365a91e4c149f01af793764de08aa7241d92e5049",
      "png_magic": true,
      "worktree_probe": {
       "check": "path exists in TensorKnowledge worktree: figures/communication.png",
       "result": "unresolved",
       "path": "/root/tp-agent/work/m15695/figures/communication.png"
      }
     },
     "note": "payload fetched from GET /tensor/reports/11267/figures/<name> (PNG magic checked) -> payload_sha256 is the hash of the bytes actually served; the caption is also declared in the record metadata"
    },
    {
     "asset_id": "A11",
     "asset_class": "figure_artifact",
     "label": "迭代数",
     "name": "figures/iterations.png",
     "in_report_section": "判据汇总",
     "locator": {
      "method": "char_span",
      "start_char": 4785,
      "end_char": 4807,
      "start_line": 131,
      "end_line": 131,
      "quote": "figures/iterations.png",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 131,
       "start_char": 4785,
       "end_char": 4807,
       "quote": "figures/iterations.png",
       "quote_sha256": "sha256:1a502b99d458e60708e38231481284616c356357c4739714cd5ad19ac101b59c",
       "quote_in_source": true,
       "on_declared_span": true
      },
      {
       "source_field": "markdown",
       "line": 141,
       "start_char": 5096,
       "end_char": 5110,
       "quote": "iterations.png",
       "quote_sha256": "sha256:60cb61dda191a28ff0ffcfe0adf0758bb855badcbec913b6c9990eb3c7128eae",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "markdown_image_link",
     "occurrence_count": 2,
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "GET /tensor/reports/11267/figures/iterations.png",
      "result": "resolved",
      "http_status": 200,
      "bytes": 35144,
      "payload_sha256": "sha256:c4e0136feef7d52c2db6273846489c4aa9d99c4f1820b6e36e20f3fffa7eeb54",
      "png_magic": true,
      "worktree_probe": {
       "check": "path exists in TensorKnowledge worktree: figures/iterations.png",
       "result": "unresolved",
       "path": "/root/tp-agent/work/m15695/figures/iterations.png"
      }
     },
     "note": "payload fetched from GET /tensor/reports/11267/figures/<name> (PNG magic checked) -> payload_sha256 is the hash of the bytes actually served; the caption is also declared in the record metadata"
    },
    {
     "asset_id": "A12",
     "asset_class": "figure_artifact",
     "label": "收敛",
     "name": "figures/accuracy.png",
     "in_report_section": "判据汇总",
     "locator": {
      "method": "char_span",
      "start_char": 4815,
      "end_char": 4835,
      "start_line": 132,
      "end_line": 132,
      "quote": "figures/accuracy.png",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 132,
       "start_char": 4815,
       "end_char": 4835,
       "quote": "figures/accuracy.png",
       "quote_sha256": "sha256:f2859e7c6b9429fe023643e7b48a638d4955566b64f18f49aee7e7730b917782",
       "quote_in_source": true,
       "on_declared_span": true
      },
      {
       "source_field": "markdown",
       "line": 142,
       "start_char": 5146,
       "end_char": 5158,
       "quote": "accuracy.png",
       "quote_sha256": "sha256:03e9177b2508cfb08283c879eb60466d21e8702852a46deda33e1e64e7a1eac7",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "markdown_image_link",
     "occurrence_count": 2,
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "GET /tensor/reports/11267/figures/accuracy.png",
      "result": "resolved",
      "http_status": 200,
      "bytes": 44985,
      "payload_sha256": "sha256:dd5f74df6ea565252626267caa946ad48e95ad96894bbacd61c72f0bbdd6e3a7",
      "png_magic": true,
      "worktree_probe": {
       "check": "path exists in TensorKnowledge worktree: figures/accuracy.png",
       "result": "unresolved",
       "path": "/root/tp-agent/work/m15695/figures/accuracy.png"
      }
     },
     "note": "payload fetched from GET /tensor/reports/11267/figures/<name> (PNG magic checked) -> payload_sha256 is the hash of the bytes actually served; the caption is also declared in the record metadata"
    },
    {
     "asset_id": "A13",
     "asset_class": "figure_artifact",
     "label": "负载均衡",
     "name": "figures/load_balance.png",
     "in_report_section": "判据汇总",
     "locator": {
      "method": "char_span",
      "start_char": 4845,
      "end_char": 4869,
      "start_line": 133,
      "end_line": 133,
      "quote": "figures/load_balance.png",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 133,
       "start_char": 4845,
       "end_char": 4869,
       "quote": "figures/load_balance.png",
       "quote_sha256": "sha256:a3afe80f0c808da493b615c83a5d71e41472f92146862fecb92d23629f937494",
       "quote_in_source": true,
       "on_declared_span": true
      },
      {
       "source_field": "markdown",
       "line": 143,
       "start_char": 5195,
       "end_char": 5211,
       "quote": "load_balance.png",
       "quote_sha256": "sha256:e7ca2f8914d32a5ebcc86f3223a0fdfa949d0fc8eb642fd00ae8ec62c1162039",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "markdown_image_link",
     "occurrence_count": 2,
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "GET /tensor/reports/11267/figures/load_balance.png",
      "result": "resolved",
      "http_status": 200,
      "bytes": 33102,
      "payload_sha256": "sha256:1e2eca93764bb5d37d0e36b89a396fd731f6d3cf49176dc1cd5d4951f9aea99d",
      "png_magic": true,
      "worktree_probe": {
       "check": "path exists in TensorKnowledge worktree: figures/load_balance.png",
       "result": "unresolved",
       "path": "/root/tp-agent/work/m15695/figures/load_balance.png"
      }
     },
     "note": "payload fetched from GET /tensor/reports/11267/figures/<name> (PNG magic checked) -> payload_sha256 is the hash of the bytes actually served; the caption is also declared in the record metadata"
    },
    {
     "asset_id": "A14",
     "asset_class": "figure_artifact",
     "label": "场量",
     "name": "figures/fields.png",
     "in_report_section": "判据汇总",
     "locator": {
      "method": "char_span",
      "start_char": 4877,
      "end_char": 4895,
      "start_line": 134,
      "end_line": 134,
      "quote": "figures/fields.png",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 134,
       "start_char": 4877,
       "end_char": 4895,
       "quote": "figures/fields.png",
       "quote_sha256": "sha256:838c33699a6a57cd93d25201aac12c705377600dad80147c08c704e28090f217",
       "quote_in_source": true,
       "on_declared_span": true
      },
      {
       "source_field": "markdown",
       "line": 144,
       "start_char": 5246,
       "end_char": 5256,
       "quote": "fields.png",
       "quote_sha256": "sha256:ac4a46c0b8cd2f8eb556a88e2bc9c01d6b77a167bc6afbc75a88ce7a9637979c",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "markdown_image_link",
     "occurrence_count": 2,
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "GET /tensor/reports/11267/figures/fields.png",
      "result": "resolved",
      "http_status": 200,
      "bytes": 98452,
      "payload_sha256": "sha256:67c1e04da83ef640efcd349561e0dcfe292f0ce2626fec681a3aaaa7abf6c977",
      "png_magic": true,
      "worktree_probe": {
       "check": "path exists in TensorKnowledge worktree: figures/fields.png",
       "result": "unresolved",
       "path": "/root/tp-agent/work/m15695/figures/fields.png"
      }
     },
     "note": "payload fetched from GET /tensor/reports/11267/figures/<name> (PNG magic checked) -> payload_sha256 is the hash of the bytes actually served; the caption is also declared in the record metadata"
    },
    {
     "asset_id": "A15",
     "asset_class": "declared_measurement_gap",
     "label": "MPIComm backend, local measurement",
     "name": "MPIComm_local_measurement",
     "in_report_section": "⑤ 注意点（踩过的坑 / 局限）",
     "locator": {
      "method": "char_span",
      "start_char": 6086,
      "end_char": 6121,
      "start_line": 162,
      "end_line": 162,
      "quote": "   自动探测，但**未在本机实测**（如实声明，不作为本节点证据）。",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 162,
       "start_char": 6086,
       "end_char": 6121,
       "quote": "   自动探测，但**未在本机实测**（如实声明，不作为本节点证据）。",
       "quote_sha256": "sha256:abf107a2848252f4fe2131d02a1f7d1d190c165599f9087aed541f1e887d02cb",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "caveat_sentence",
     "occurrence_count": 1,
     "resolution": "declared_absent",
     "resolution_check": {
      "check": "report itself declares this artefact/measurement absent or unmeasured",
      "result": "absent",
      "worktree_probe": {
       "check": "path exists in TensorKnowledge worktree: MPIComm_local_measurement",
       "result": "unresolved",
       "path": "/root/tp-agent/work/m15695/MPIComm_local_measurement"
      }
     },
     "note": "the report states the artefact is absent/queued/not measured; registered as declared_absent -- registration of a declared gap, NOT a claim and NOT a verified finding"
    },
    {
     "asset_id": "A16",
     "asset_class": "cluster_job",
     "label": "cj308",
     "name": "cj308",
     "in_report_section": "⑤ 注意点（踩过的坑 / 局限）",
     "locator": {
      "method": "char_span",
      "start_char": 6405,
      "end_char": 6410,
      "start_line": 169,
      "end_line": 169,
      "quote": "cj308",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 169,
       "start_char": 6405,
       "end_char": 6410,
       "quote": "cj308",
       "quote_sha256": "sha256:beb1bf71030a1d47791d4db8fc4e539b7048828c66e872ecdaed7a772fb36b82",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "job_id",
     "occurrence_count": 1,
     "resolution": "declared_absent",
     "resolution_check": {
      "check": "report itself declares this artefact/measurement absent or unmeasured",
      "result": "absent",
      "worktree_probe": {
       "check": "path exists in TensorKnowledge worktree: cj308",
       "result": "unresolved",
       "path": "/root/tp-agent/work/m15695/cj308"
      }
     },
     "note": "the report states the artefact is absent/queued/not measured; registered as declared_absent -- registration of a declared gap, NOT a claim and NOT a verified finding"
    },
    {
     "asset_id": "A17",
     "asset_class": "cluster_job",
     "label": "cj313",
     "name": "cj313",
     "in_report_section": "⑤ 注意点（踩过的坑 / 局限）",
     "locator": {
      "method": "char_span",
      "start_char": 6416,
      "end_char": 6421,
      "start_line": 169,
      "end_line": 169,
      "quote": "cj313",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 169,
       "start_char": 6416,
       "end_char": 6421,
       "quote": "cj313",
       "quote_sha256": "sha256:267f68b050d034d806c93ec8f12abf09677180747bce897073577932b926ccb1",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "job_id",
     "occurrence_count": 1,
     "resolution": "declared_absent",
     "resolution_check": {
      "check": "report itself declares this artefact/measurement absent or unmeasured",
      "result": "absent",
      "worktree_probe": {
       "check": "path exists in TensorKnowledge worktree: cj313",
       "result": "unresolved",
       "path": "/root/tp-agent/work/m15695/cj313"
      }
     },
     "note": "the report states the artefact is absent/queued/not measured; registered as declared_absent -- registration of a declared gap, NOT a claim and NOT a verified finding"
    },
    {
     "asset_id": "A18",
     "asset_class": "cluster_job",
     "label": "cj314",
     "name": "cj314",
     "in_report_section": "⑤ 注意点（踩过的坑 / 局限）",
     "locator": {
      "method": "char_span",
      "start_char": 6430,
      "end_char": 6435,
      "start_line": 169,
      "end_line": 169,
      "quote": "cj314",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 169,
       "start_char": 6430,
       "end_char": 6435,
       "quote": "cj314",
       "quote_sha256": "sha256:4926b2fdc4dc1d156e836f52d007cf7c0cc3d03a5bea521b7e83494876ff1773",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "job_id",
     "occurrence_count": 1,
     "resolution": "declared_absent",
     "resolution_check": {
      "check": "report itself declares this artefact/measurement absent or unmeasured",
      "result": "absent",
      "worktree_probe": {
       "check": "path exists in TensorKnowledge worktree: cj314",
       "result": "unresolved",
       "path": "/root/tp-agent/work/m15695/cj314"
      }
     },
     "note": "the report states the artefact is absent/queued/not measured; registered as declared_absent -- registration of a declared gap, NOT a claim and NOT a verified finding"
    },
    {
     "asset_id": "A19",
     "asset_class": "code_script",
     "label": "scripts/fem_parallel_point.py",
     "name": "scripts/fem_parallel_point.py",
     "in_report_section": "⑤ 注意点（踩过的坑 / 局限）",
     "locator": {
      "method": "char_span",
      "start_char": 6633,
      "end_char": 6662,
      "start_line": 173,
      "end_line": 173,
      "quote": "scripts/fem_parallel_point.py",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 173,
       "start_char": 6633,
       "end_char": 6662,
       "quote": "scripts/fem_parallel_point.py",
       "quote_sha256": "sha256:a4d43abfc2e5694852b03daf3e5cf691ec1ad63e424a5761df0ecca8d41de71e",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "path_token",
     "occurrence_count": 1,
     "resolution": "referenced_unresolved",
     "resolution_check": {
      "check": "path exists in TensorKnowledge worktree: scripts/fem_parallel_point.py",
      "result": "unresolved",
      "path": "/root/tp-agent/work/m15695/scripts/fem_parallel_point.py"
     },
     "note": "declared path belongs to the delivery repo named at line 3 (TensorPhysics, src/tensorphysics/fem_parallel); the payload is outside this工序's worktree -> declared reference, unresolvable here"
    },
    {
     "asset_id": "A20",
     "asset_class": "test_symbol",
     "label": "test_elasticity_patch_test_is_exact",
     "name": "test_elasticity_patch_test_is_exact",
     "in_report_section": "⑥ 误差判定",
     "locator": {
      "method": "char_span",
      "start_char": 7016,
      "end_char": 7051,
      "start_line": 186,
      "end_line": 186,
      "quote": "test_elasticity_patch_test_is_exact",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 186,
       "start_char": 7016,
       "end_char": 7051,
       "quote": "test_elasticity_patch_test_is_exact",
       "quote_sha256": "sha256:eee4c365f3b8e41e51a549695bb65b7692551781784ff86714559a4ae92bef89",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "backticked_symbol",
     "occurrence_count": 1,
     "resolution": "referenced_unresolved",
     "resolution_check": {
      "check": "path exists in TensorKnowledge worktree: test_elasticity_patch_test_is_exact",
      "result": "unresolved",
      "path": "/root/tp-agent/work/m15695/test_elasticity_patch_test_is_exact"
     },
     "note": "declared path belongs to the delivery repo named at line 3 (TensorPhysics, src/tensorphysics/fem_parallel); the payload is outside this工序's worktree -> declared reference, unresolvable here"
    },
    {
     "asset_id": "A21",
     "asset_class": "test_suite",
     "label": "tests/test_fem_parallel_*.py",
     "name": "tests/test_fem_parallel_*.py",
     "in_report_section": "复现",
     "locator": {
      "method": "char_span",
      "start_char": 7369,
      "end_char": 7397,
      "start_line": 197,
      "end_line": 197,
      "quote": "tests/test_fem_parallel_*.py",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 197,
       "start_char": 7369,
       "end_char": 7397,
       "quote": "tests/test_fem_parallel_*.py",
       "quote_sha256": "sha256:8bf57aed074f107773bfc61a110fed71029c3427daa71876dd49f62bd8e13ab9",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "path_token",
     "occurrence_count": 1,
     "resolution": "referenced_unresolved",
     "resolution_check": {
      "check": "glob in TensorKnowledge worktree: tests/test_fem_parallel_*.py",
      "result": "unresolved",
      "glob_matches": [],
      "glob_match_count": 0
     },
     "note": "declared path belongs to the delivery repo named at line 3 (TensorPhysics, src/tensorphysics/fem_parallel); the payload is outside this工序's worktree -> declared reference, unresolvable here"
    },
    {
     "asset_id": "A22",
     "asset_class": "code_script",
     "label": "scripts/fem_parallel_figures.py",
     "name": "scripts/fem_parallel_figures.py",
     "in_report_section": "复现",
     "locator": {
      "method": "char_span",
      "start_char": 7408,
      "end_char": 7439,
      "start_line": 198,
      "end_line": 198,
      "quote": "scripts/fem_parallel_figures.py",
      "unique": true
     },
     "all_locators": [
      {
       "source_field": "markdown",
       "line": 198,
       "start_char": 7408,
       "end_char": 7439,
       "quote": "scripts/fem_parallel_figures.py",
       "quote_sha256": "sha256:19782a9bfc66233ad4463447867d98b3d40ce19f5c9cd5f5f81e599da48236b3",
       "quote_in_source": true,
       "on_declared_span": true
      }
     ],
     "reference_form": "path_token",
     "occurrence_count": 1,
     "resolution": "referenced_unresolved",
     "resolution_check": {
      "check": "path exists in TensorKnowledge worktree: scripts/fem_parallel_figures.py",
      "result": "unresolved",
      "path": "/root/tp-agent/work/m15695/scripts/fem_parallel_figures.py"
     },
     "note": "declared path belongs to the delivery repo named at line 3 (TensorPhysics, src/tensorphysics/fem_parallel); the payload is outside this工序's worktree -> declared reference, unresolvable here"
    }
   ],
   "claims": [],
   "claims_empty_reason": "Contract wp-11267-01 sets objective.register_assets=true and objective.classify_report_type=false, output=asset_manifest.json only, notes 'claims 允许为空数组', and constraints forbid no_forced_claim_generation and do_not_mark_claims_as_verified. This工序 registers asset identity only (report_id, markdown byte hash, declared attachments/artifacts); knowledge extraction is a downstream工序, so claims=[] is the complete result of this package.",
   "id_integrity": {
    "ids_checked": 23,
    "duplicate_ids": [],
    "names_checked": 23,
    "duplicate_names": [],
    "unique": true
   },
   "unresolved": [
    {
     "asset_id": "A01",
     "asset_class": "code_module_path",
     "name": "src/tensorphysics/fem_parallel/",
     "resolution": "referenced_unresolved",
     "reason": "path exists in TensorKnowledge worktree: src/tensorphysics/fem_parallel/"
    },
    {
     "asset_id": "A02",
     "asset_class": "run_command",
     "name": "tensorphysics.fem_parallel.verification",
     "resolution": "referenced_unresolved",
     "reason": "path exists in TensorKnowledge worktree: tensorphysics.fem_parallel.verification"
    },
    {
     "asset_id": "A03",
     "asset_class": "data_artifact",
     "name": "artifacts/fem_parallel/verification.json",
     "resolution": "referenced_unresolved",
     "reason": "path exists in TensorKnowledge worktree: artifacts/fem_parallel/verification.json"
    },
    {
     "asset_id": "A04",
     "asset_class": "code_script",
     "name": "scripts/fem_parallel_report.py",
     "resolution": "referenced_unresolved",
     "reason": "path exists in TensorKnowledge worktree: scripts/fem_parallel_report.py"
    },
    {
     "asset_id": "A05",
     "asset_class": "declared_measurement_gap",
     "name": "C1_strong_efficiency",
     "resolution": "declared_absent",
     "reason": "report itself declares this artefact/measurement absent or unmeasured"
    },
    {
     "asset_id": "A06",
     "asset_class": "declared_measurement_gap",
     "name": "C2_weak_ratio",
     "resolution": "declared_absent",
     "reason": "report itself declares this artefact/measurement absent or unmeasured"
    },
    {
     "asset_id": "A07",
     "asset_class": "declared_measurement_gap",
     "name": "C4_comm_fraction",
     "resolution": "declared_absent",
     "reason": "report itself declares this artefact/measurement absent or unmeasured"
    },
    {
     "asset_id": "A15",
     "asset_class": "declared_measurement_gap",
     "name": "MPIComm_local_measurement",
     "resolution": "declared_absent",
     "reason": "report itself declares this artefact/measurement absent or unmeasured"
    },
    {
     "asset_id": "A16",
     "asset_class": "cluster_job",
     "name": "cj308",
     "resolution": "declared_absent",
     "reason": "report itself declares this artefact/measurement absent or unmeasured"
    },
    {
     "asset_id": "A17",
     "asset_class": "cluster_job",
     "name": "cj313",
     "resolution": "declared_absent",
     "reason": "report itself declares this artefact/measurement absent or unmeasured"
    },
    {
     "asset_id": "A18",
     "asset_class": "cluster_job",
     "name": "cj314",
     "resolution": "declared_absent",
     "reason": "report itself declares this artefact/measurement absent or unmeasured"
    },
    {
     "asset_id": "A19",
     "asset_class": "code_script",
     "name": "scripts/fem_parallel_point.py",
     "resolution": "referenced_unresolved",
     "reason": "path exists in TensorKnowledge worktree: scripts/fem_parallel_point.py"
    },
    {
     "asset_id": "A20",
     "asset_class": "test_symbol",
     "name": "test_elasticity_patch_test_is_exact",
     "resolution": "referenced_unresolved",
     "reason": "path exists in TensorKnowledge worktree: test_elasticity_patch_test_is_exact"
    },
    {
     "asset_id": "A21",
     "asset_class": "test_suite",
     "name": "tests/test_fem_parallel_*.py",
     "resolution": "referenced_unresolved",
     "reason": "glob in TensorKnowledge worktree: tests/test_fem_parallel_*.py"
    },
    {
     "asset_id": "A22",
     "asset_class": "code_script",
     "name": "scripts/fem_parallel_figures.py",
     "resolution": "referenced_unresolved",
     "reason": "path exists in TensorKnowledge worktree: scripts/fem_parallel_figures.py"
    }
   ],
   "method_notes": [
    "Asset discovery is text-driven over the markdown: image links, backticked paths / module entrypoints / test symbols, cluster job ids, criteria-table rows stating 'not measured'/'未测量', and the MPIComm caveat sentence.",
    "Repeated references to one path collapse into a single asset whose all_locators lists every char span, so dedup never drops a locator.",
    "resolution=resolved_in_source: payload/hash obtained here; referenced_unresolved: declaration verbatim-locatable but payload outside this工序's worktree; declared_absent: the report itself declares the artefact absent/queued/unmeasured.",
    "Figure names are normalised to the in-body link form (figures/<name>.png): section 4 refers to them bare, and one asset must keep every literal locator span.",
    "A directory token that only prefixes another declared file path (artifacts/fem_parallel/ vs artifacts/fem_parallel/verification.json) is folded into that file asset instead of being counted twice."
   ]
  }
 },
 "claims": []
}
```
