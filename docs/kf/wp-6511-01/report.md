# KF-RESULT wp-6511-01 —— 报告 6511 源资产登记（01-asset-registration）

**工序**：`wp-6511-01`（task_type `01-asset-registration`，lane C）｜**对象**：report_id=6511
`IN31-L02: TensorLBM Conjugate Heat Transfer (CHT) Validation Ladder`｜**分层**：CHT / IN31-L02 / m
**本单不做抽取**：objective 只开 `register_assets=true` + `classify_report_type=false`，`claims` 按契约允许为空数组。

## ① 案例介绍（本工序的对象与边界）

报告 6511 是 TensorLBM 共轭传热（CHT）验证梯的结题报告：流体对流 + 固体导热 + 界面热流连续，
四个解析锚（1D 复合壁串联热阻、erf 热渗透、Graetz Nu、Churchill-Chu Nu）+ 一组负对照（C6）。
本工序**不评价这些物理结论**，只把它当作"生产线的源资产"来做身份登记：

| 项 | 值（均取自平台，非记忆） |
|---|---|
| report_id | `6511` |
| title | `IN31-L02: TensorLBM Conjugate Heat Transfer (CHT) Validation Ladder` |
| scenario_key | `IN31-L02` |
| status / created_at | `published` / `2026-11-07T13:24:26.514078+00:00` |
| record mission_id | `5486`（与本工作包 mission_id=null 不同，如实记录不调和） |
| markdown sha256 | `sha256:e27b9986b028ac9402f4e90705919fc2aea826da4c47de48224665231fc2d840` |
| chars / bytes / lines | `4405` / `4459` / `112` |
| 资产总数 | 15（resolved 5 / metadata_only 2 / unresolved 7 / absent 1） |
| 声明图 | 正文 §4 声明 4 张，record 声明 2 张，**有字节的 0 张** |
| claims | 0（见 claims_empty_reason） |

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`python3 runs/wp-6511-01/fetch_source.py` —— 登录平台（`$TENSOR_AGENT_USER`）→
   `GET /api/v1/tensor/reports/6511` → 把 `markdown` **逐字节**落盘为 `runs/wp-6511-01/source_6511.md`，
   同时记录 record 字段（title/scenario_key/tags/figures/mission_id…）到 `source_6511_record.json`。
   psql 直读被拒（`permission denied for table tensor_reports`），故 API 是唯一取源通道（已写入 limitations）。
2. **探附件**：`python3 runs/wp-6511-01/probe_figures.py` —— 对 5 条候选图/附件端点做 HTTP 探测，
   结果落 `figure_probe.json`；5 条全 404 ⇒ "有声明、无字节"，而不是"上游图丢了"。
3. **登记**：`python3 runs/wp-6511-01/register_6511.py` —— 结构化读取 markdown（标题/小节/围栏块/表格/路径类 token 扫描），
   逐条资产用 **quote → 唯一行号** 反解定位器；脚本内置断言：契约 source_hash 与 chars 必须匹配、
   每条引文必须是原文的**唯一**子串且落在声明行、id 不得重复；任一断言失败即 `exit 2` 不出产物（宁可失败不可造数）。
   路径类 token 的正则扫描**在脚本内真跑**（结果 0 命中），不是抄旧结论。
4. **自检**：`python3 runs/wp-6511-01/verify_6511.py` —— 6 条 acceptance 各一条断言，其中 source_hash 用
   **重新 GET** 的 markdown 现算（不复用本地副本），并断言 本地副本 == 平台现值。
5. **出图**：`python3 runs/wp-6511-01/make_figure.py` —— 从 manifest 直接读计数绘图，图不会与产物漂移。

**关键设置**：`source_field=markdown`（hash 只覆盖 markdown 字节，不含 summary/record）；行号模型 =
`markdown.rstrip("\n").split("\n")`、1-based、文件无 CRLF。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-6511-01/asset_manifest.json` | 主产物：15 个资产（1 markdown + 2 嵌入表 + 1 参数列表 + 1 公式 + 4 正文图声明 + 2 record 图 + 1 软件引用 + 2 外部相关式 + 1 缺失项），13 个 markdown 定位器全部可解，claims=[] + 理由 |
| `docs/kf/wp-6511-01/kf_result.json` | 平台结果信封（package_id/task_type/report_id/provenance/outputs/claims），即报告 JSON 块的同一份字节 |
| `docs/kf/wp-6511-01/asset_manifest.schema.json` | 本包形状 pin（仓内 `schemas/asset_manifest.v1.schema.json` 把 package_id 写死为 wp-448-01，无法复用） |
| `runs/wp-6511-01/source_6511.md` | 源 markdown 逐字节副本（sha256 与契约一致），一切引文的唯一来源 |
| `runs/wp-6511-01/source_6511_record.json` / `figure_probe.json` | record 元数据快照 / 附件端点探测原始结果 |
| `runs/wp-6511-01/register_6511.py` / `verify_6511.py` / `make_figure.py` / `fetch_source.py` / `probe_figures.py` | 全流程可复跑脚本 |
| `runs/wp-6511-01/verify_out.json` | 6 条 acceptance 的自检结果（all_pass=true） |
| `artifacts/wp-6511-01/asset_inventory.png` | 资产清单图（按 kind / 按 resolution / 沿文档位置） |

## ④ 证据定位表（引文逐字取自 markdown，行号为 1-based）

| 资产 / 字段 | 定位器 | 原文引文片段 | 解析状态 |
|---|---|---|---|
| `r6511:source-markdown` | markdown L1 | `IN31-L02: TensorLBM Conjugate Heat Transfer (CHT) Validation Ladder` | resolved |
| `r6511:software:tensorlbm` | markdown L1 | `IN31-L02: TensorLBM Conjugate Heat Transfer (CHT) Validation Ladder` | unresolved |
| `r6511:params:geometry` | markdown L9 | `- **1D Composite Wall**: Fluid channel (H=20 lu) + Steel plate (t=10 lu, k_ratio=10) + Insulatio` | resolved |
| `r6511:table:parameters` | markdown L16 | `\| Parameter \| Value \| Unit \|` | resolved |
| `r6511:eq:interface-coupling` | markdown L36 | `T_interface = (k_f·T_fluid + k_s·T_solid) / (k_f + k_s)` | resolved |
| `r6511:absent:repro-command` | markdown L40 | `### Algorithm per Time Step` | absent |
| `r6511:external:shah-london` | markdown L61 | `**Result**: Shah-London correlation verified analytically` | unresolved |
| `r6511:external:churchill-chu` | markdown L64 | `### C4: Churchill-Chu Nu` | unresolved |
| `r6511:figure-body:01` | markdown L82 | `1. 1D composite wall analytical solution` | unresolved |
| `r6511:figure-body:02` | markdown L83 | `2. erf heat penetration comparison` | unresolved |
| `r6511:figure-body:03` | markdown L84 | `3. Graetz Nu correlation` | unresolved |
| `r6511:figure-body:04` | markdown L85 | `4. Churchill-Chu correlation` | unresolved |
| `r6511:table:error-assessment` | markdown L103 | `\| Criterion \| Target \| Achieved \| Status \|` | resolved |
| `r6511:figure-record:fig1` | record `figures[0].name` = `cht_fig1` | (record field, not markdown) | metadata_only |
| `r6511:figure-record:fig2` | record `figures[1].name` = `cht_fig2` | (record field, not markdown) | metadata_only |

补充证据（非引文，程序化事实）：
- markdown 共 **112** 行、**6** 个 H2、**14** 个 H3、**1** 个围栏块（该块是公式，不是代码）。
- 路径类 token 扫描（`0` 命中）：本报告**不引用任何文件路径**，故"不可解析附件"不是路径写错，而是根本没给路径。
- 图字节探测：`/tensor/reports/6511/figures`、`/artifacts`、`/figures/cht_fig1`、`/figures/cht_fig1.png`、`/tensor/figures/cht_fig1` 全部 HTTP 404。

## ⑤ 注意点与局限

1. **只登记不抽取**：无 claim、无 verified 标记（verification 由平台门计算，工人不得自标）。
2. **图声明自相矛盾（如实记录、不调和）**：正文 §4「See attached figures for:」下**编号 4 张图（只有描述，无文件名）**，
   record 只声明 **2 张（cht_fig1/cht_fig2，有 name+caption 无字节）**。两组无法从文本一一对应，
   故 4 条正文声明留 `unresolved`、2 条 record 图留 `metadata_only`，**不合并、不猜**。
3. **零手抄**：产物与报告里所有引文都由 manifest 的 locator 生成（builder 从 JSON 读 quote+line 拼表），
   脚本内断言引文是原文唯一子串，杜绝记忆重述。
4. **hash 作用域**：仅 markdown 的 UTF-8 字节；summary/record 变化不会使本 hash 失效，故 record 类结论一律标注 source_field=record。
5. **给下游 03 的观察（本单不升格为 claim）**：§6 误差表把 C1（`<3%` 目标 / `<5%` 达成）、C2（`<5%` / `<15%`）、
   C5（`<5%` / `<20%`）都打了 ✅，而其 Achieved 列**超出** Target 列；这属于 claim 级判定，交抽取/校验道处理。
6. **resolve 作用域有限**：仅 markdown 正文、API 暴露的 record 字段、5 条图字节探测、（与实际产线工作树无关的）路径解析；
   在此之外无法解析的一律报 unresolved，绝不写成"上游产物损坏"。
7. **mission 号差异**：record mission_id=5486，本工作包 mission_id=null，仅记录不调和。

## ⑥ 误差判定（acceptance 逐条 + 是否 <3%）

本工序**不产生物理量**，故不存在"关键量 vs 解析解/文献"的误差比较；按纪律显式声明：
**是否 <3%：N/A（无基准可比）** —— 原因：wp-6511-01 的 objective 只有 register_assets，
产物是资产身份与定位器（字符串/行号），不是数值结果。可度量的误差只有"登记正确性"，逐条如下：

| acceptance | 结果 | 证据 |
|---|---|---|
| valid_json | PASS | parsed 2 files (24146B, 27261B) |
| schema_pass | PASS | asset_manifest OK vs docs/kf/wp-6511-01/asset_manifest.schema.json; kf_result OK vs schemas/kf_result.v1.schema.json |
| source_locator_resolvable | PASS | 13 markdown locators + 2 record locators checked; problems=[] |
| source_hash_matches | PASS | {'live_hash': 'sha256:e27b9986b028ac9402f4e90705919fc2aea826da4c47de48224665231fc2d840', 'contract_hash': 'sha256:e27b9986b028ac9402f4e90705919fc2aea826da4c47de48224665231fc2d840', 'manifest_hash': 'sha256:e27b9986b028ac |
| no_duplicate_ids | PASS | {'asset_ids': 15, 'duplicates': [], 'claim_duplicates': []} |
| all_claims_have_evidence_or_explicit_unresolved_status | PASS | {'claims': 0, 'vacuous_empty_with_reason': True, 'problems': [], 'no_verified_marks': True} |

- 哈希侧硬指标：契约 `sha256:e27b9986…f2d840` **== ** 本地重算 **== ** 重新 GET 现算 **== ** 信封 provenance，字符数 4405 == 契约 4405，误差 **0（<3% 满足，且为精确相等）**。
- 定位器侧：13/13 markdown 定位器引文唯一且落在声明行，2/2 record 定位器可解到 `figures[i].name`，失败 0 条。
- 自检脚本 `verify_6511.py` 退出码 0（`ALL_PASS = True`）；如有任一条失败会以非 0 退出并写 FAIL —— 本单无 FAIL 项。

**未完成 / 留白（honest）**：不抽取知识、不判报告类型、不给 verified；正文 4 张图与 record 2 张图的对应关系、
两套单位制（lu 的 T_hot=1.0 vs SI 的 T_hot=350 K）是否同一算例，均**留待下游工序**，本单不猜。

## 复现（一键）

```bash
cd TensorKnowledge && python3 runs/wp-6511-01/fetch_source.py \
 && python3 runs/wp-6511-01/probe_figures.py \
 && python3 runs/wp-6511-01/register_6511.py \
 && python3 runs/wp-6511-01/verify_6511.py \
 && python3 runs/wp-6511-01/make_figure.py
```

## 结果 JSON（本报告唯一 json 代码块）

```json
{
  "package_id": "wp-6511-01",
  "task_type": "01-asset-registration",
  "report_id": "6511",
  "provenance": {
    "source_hash": "sha256:e27b9986b028ac9402f4e90705919fc2aea826da4c47de48224665231fc2d840",
    "source_field": "markdown",
    "producer": "kf-worker/m15589",
    "emitted_at": "2026-11-12T01:29:04.432629+00:00",
    "notes": "hash recomputed from GET /api/v1/tensor/reports/6511 markdown (UTF-8 bytes); matches contract source_hash sha256:e27b9986b028ac9402f4e90705919fc2aea826da4c47de48224665231fc2d840"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-6511-01",
      "task_type": "01-asset-registration",
      "report_id": "6511",
      "lane": "C",
      "generated_at": "2026-11-12T01:29:04.432629+00:00",
      "producer": "kf-worker/m15589",
      "source": {
        "report_id": "6511",
        "source_uri": "tensor://reports/6511",
        "source_field": "markdown",
        "source_hash": "sha256:e27b9986b028ac9402f4e90705919fc2aea826da4c47de48224665231fc2d840",
        "contract_source_hash": "sha256:e27b9986b028ac9402f4e90705919fc2aea826da4c47de48224665231fc2d840",
        "hash_algo": "sha256",
        "hash_match": true,
        "chars": 4405,
        "contract_chars": 4405,
        "chars_match_contract": true,
        "bytes": 4459,
        "lines": 112,
        "has_crlf": false,
        "has_trailing_newline": true,
        "line_counting": "logical lines = markdown.rstrip(chr(10)).split(chr(10)); 1-based; no CRLF in the file",
        "fetched_via": "GET /api/v1/tensor/reports/6511",
        "record_fields": {
          "title": "IN31-L02: TensorLBM Conjugate Heat Transfer (CHT) Validation Ladder",
          "scenario_key": "IN31-L02",
          "mission_id": 5486,
          "status": "published",
          "created_at": "2026-11-07T13:24:26.514078+00:00",
          "tags": [
            "CHT",
            "conjugate_heat_transfer",
            "validation",
            "LBM",
            "thermal",
            "TensorLBM"
          ],
          "figures": [
            {
              "name": "cht_fig1",
              "caption": "1D composite wall analytical series resistance solution"
            },
            {
              "name": "cht_fig2",
              "caption": "Semi-infinite solid transient conduction (erf solution)"
            }
          ],
          "contract_title": "IN31-L02: TensorLBM Conjugate Heat Transfer (CHT) Validation Ladder",
          "contract_scenario_key": "IN31-L02",
          "title_matches_contract": true,
          "scenario_matches_contract": true
        },
        "figure_byte_probes": {
          "/tensor/reports/6511/figures": {
            "http_status": 404,
            "bytes": 22
          },
          "/tensor/reports/6511/artifacts": {
            "http_status": 404,
            "bytes": 22
          },
          "/tensor/reports/6511/figures/cht_fig1": {
            "http_status": 404,
            "bytes": 29
          },
          "/tensor/reports/6511/figures/cht_fig1.png": {
            "http_status": 404,
            "bytes": 29
          },
          "/tensor/figures/cht_fig1": {
            "http_status": 404,
            "bytes": 22
          }
        }
      },
      "document_structure": {
        "h2_headings": [
          {
            "line": 3,
            "text": "## 1. Case Introduction"
          },
          {
            "line": 26,
            "text": "## 2. Methodology"
          },
          {
            "line": 47,
            "text": "## 3. Results"
          },
          {
            "line": 79,
            "text": "## 4. Figures"
          },
          {
            "line": 87,
            "text": "## 5. Notes & Limitations"
          },
          {
            "line": 101,
            "text": "## 6. Error Assessment"
          }
        ],
        "h3_headings": [
          {
            "line": 5,
            "text": "### Physical Background"
          },
          {
            "line": 8,
            "text": "### Geometry & Parameters"
          },
          {
            "line": 15,
            "text": "### Parameter Table (Programmatic)"
          },
          {
            "line": 28,
            "text": "### Double Distribution Function (DDF) Model"
          },
          {
            "line": 33,
            "text": "### Interface Coupling"
          },
          {
            "line": 40,
            "text": "### Algorithm per Time Step"
          },
          {
            "line": 49,
            "text": "### C1: 1D Composite Wall (Series Thermal Resistance)"
          },
          {
            "line": 54,
            "text": "### C2: erf Heat Penetration"
          },
          {
            "line": 59,
            "text": "### C3: Graetz Nu Number"
          },
          {
            "line": 64,
            "text": "### C4: Churchill-Chu Nu"
          },
          {
            "line": 69,
            "text": "### C5: Interface Heat Flux Closure"
          },
          {
            "line": 74,
            "text": "### C6: Negative Controls"
          },
          {
            "line": 89,
            "text": "### Known Limitations"
          },
          {
            "line": 95,
            "text": "### Applicable Range"
          }
        ],
        "fenced_block_lines": [
          35,
          37
        ],
        "tables": [
          {
            "asset_id": "r6511:table:parameters",
            "lines": [
              16,
              24
            ]
          },
          {
            "asset_id": "r6511:table:error-assessment",
            "lines": [
              103,
              112
            ]
          }
        ]
      },
      "assets": [
        {
          "asset_id": "r6511:source-markdown",
          "kind": "report_markdown",
          "name": "report-6511-markdown",
          "in_report_section": "whole document (H1 at line 1 .. line 112)",
          "locator": {
            "source_field": "markdown",
            "line": 1,
            "quote": "IN31-L02: TensorLBM Conjugate Heat Transfer (CHT) Validation Ladder",
            "quote_sha256": "sha256:3a225cba0d8ad0e25007205bef6daf22f45b11bb8df68e3ba79d418525a76a65",
            "occurrences_in_source": 1
          },
          "source_uri": "tensor://reports/6511",
          "media_type": "text/markdown",
          "chars": 4405,
          "bytes": 4459,
          "lines": 112,
          "sha256": "sha256:e27b9986b028ac9402f4e90705919fc2aea826da4c47de48224665231fc2d840",
          "hash_scope": "UTF-8 bytes of the markdown field served by GET /api/v1/tensor/reports/6511",
          "local_copy": "runs/wp-6511-01/source_6511.md",
          "resolution": {
            "status": "resolved",
            "scope": "platform_api",
            "via": "GET /tensor/reports/6511"
          },
          "hash_matches_contract": true,
          "chars_matches_contract": true
        },
        {
          "asset_id": "r6511:software:tensorlbm",
          "kind": "software_reference",
          "name": "TensorLBM",
          "in_report_section": "H1 title",
          "locator": {
            "source_field": "markdown",
            "line": 1,
            "quote": "IN31-L02: TensorLBM Conjugate Heat Transfer (CHT) Validation Ladder",
            "quote_sha256": "sha256:3a225cba0d8ad0e25007205bef6daf22f45b11bb8df68e3ba79d418525a76a65",
            "occurrences_in_source": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "report_body",
            "reason": "repository name appears only in the title; the markdown names no path, commit, tag or version, so the implementing code cannot be resolved from this report"
          }
        },
        {
          "asset_id": "r6511:params:geometry",
          "kind": "embedded_parameter_list",
          "name": "geometry_and_case_parameters",
          "in_report_section": "1. Case Introduction / Geometry & Parameters",
          "locator": {
            "source_field": "markdown",
            "line": 9,
            "quote": "- **1D Composite Wall**: Fluid channel (H=20 lu) + Steel plate (t=10 lu, k_ratio=10) + Insulation (t=30 lu, k_ratio=0.1)",
            "quote_sha256": "sha256:a9363d5f498da603574200bda461f6000f096cfef0e49e8c7607796d30165d71",
            "occurrences_in_source": 1
          },
          "span": {
            "first_line": 9,
            "last_line": 13,
            "bullet_count": 5
          },
          "resolution": {
            "status": "resolved",
            "scope": "embedded_in_markdown"
          },
          "note": "Five case-defining bullets (composite-wall layers, BCs, semi-infinite solid, Graetz, Churchill-Chu)."
        },
        {
          "asset_id": "r6511:table:parameters",
          "kind": "embedded_table",
          "name": "parameter_table",
          "in_report_section": "1. Case Introduction / Parameter Table (Programmatic)",
          "locator": {
            "source_field": "markdown",
            "line": 16,
            "quote": "| Parameter | Value | Unit |",
            "quote_sha256": "sha256:e8f38c80653d5065d7a5477e055b1d2d4c7138d915aa2b5b344314a93b605aa6",
            "occurrences_in_source": 1
          },
          "span": {
            "first_line": 16,
            "last_line": 24
          },
          "header_row": "| Parameter | Value | Unit |",
          "data_rows": 7,
          "columns": [
            "Parameter",
            "Value",
            "Unit"
          ],
          "resolution": {
            "status": "resolved",
            "scope": "embedded_in_markdown"
          },
          "note": "7 data rows parsed from pipe table (rho_f, mu_f, k_f, k_s, k_i, T_hot, T_cold); values parse as floats."
        },
        {
          "asset_id": "r6511:eq:interface-coupling",
          "kind": "embedded_formula",
          "name": "conductivity_weighted_temperature_averaging",
          "in_report_section": "2. Methodology / Interface Coupling",
          "locator": {
            "source_field": "markdown",
            "line": 36,
            "quote": "T_interface = (k_f·T_fluid + k_s·T_solid) / (k_f + k_s)",
            "quote_sha256": "sha256:709b436bb0d0829d579dc340f9e04e6bed5a9b7298fdd663e55618c77454b1cd",
            "occurrences_in_source": 1
          },
          "fence": {
            "open_line": 35,
            "close_line": 37
          },
          "resolution": {
            "status": "resolved",
            "scope": "embedded_in_markdown"
          },
          "note": "Single fenced block in the document; it is a formula, not executable code."
        },
        {
          "asset_id": "r6511:absent:repro-command",
          "kind": "absent_artifact",
          "name": "repro_command_or_script",
          "in_report_section": "2. Methodology / Algorithm per Time Step",
          "locator": {
            "source_field": "markdown",
            "line": 40,
            "quote": "### Algorithm per Time Step",
            "quote_sha256": "sha256:f761d2159324d73f4df2c858ade53aba594ecd132d25c6b50032adc6c83a97b4",
            "occurrences_in_source": 1
          },
          "resolution": {
            "status": "absent",
            "scope": "report_body",
            "reason": "algorithm is given as 5 prose steps; document contains exactly 1 fenced block(s) and it is a formula, no shell/pytest command, no script path, no input deck and no random seed",
            "evidence": {
              "fenced_blocks": 1,
              "path_like_tokens": 0
            }
          }
        },
        {
          "asset_id": "r6511:external:shah-london",
          "kind": "external_reference",
          "name": "Shah London",
          "in_report_section": "3. Results",
          "locator": {
            "source_field": "markdown",
            "line": 61,
            "quote": "**Result**: Shah-London correlation verified analytically",
            "quote_sha256": "sha256:1fc3f903ea1b7620d6100282b83f1980e04a7eabd8eba10b8813944e703ef1f0",
            "occurrences_in_source": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "external",
            "reason": "named correlation with no citation, edition, table/page or formula given in the report; cannot be resolved inside the report"
          }
        },
        {
          "asset_id": "r6511:external:churchill-chu",
          "kind": "external_reference",
          "name": "Churchill Chu",
          "in_report_section": "3. Results",
          "locator": {
            "source_field": "markdown",
            "line": 64,
            "quote": "### C4: Churchill-Chu Nu",
            "quote_sha256": "sha256:1a05ee4e80877b8aca50181cf088af5c21fbae3a91cbd6fc742a0a4126d4d2c0",
            "occurrences_in_source": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "external",
            "reason": "named correlation with no citation, edition, table/page or formula given in the report; cannot be resolved inside the report"
          }
        },
        {
          "asset_id": "r6511:figure-body:01",
          "kind": "figure_declaration",
          "name": "unnamed_figure_01",
          "caption": "1D composite wall analytical solution",
          "in_report_section": "4. Figures",
          "locator": {
            "source_field": "markdown",
            "line": 82,
            "quote": "1. 1D composite wall analytical solution",
            "quote_sha256": "sha256:0698b6ef4a90d1f32e4dfb4bd73801ece8dd2c1a944e7dd5548f8669ae9b3dbe",
            "occurrences_in_source": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "report_body",
            "reason": "declared as a numbered list item in 'See attached figures for:' but carries no filename, no link, no platform figure name, and no bytes"
          }
        },
        {
          "asset_id": "r6511:figure-body:02",
          "kind": "figure_declaration",
          "name": "unnamed_figure_02",
          "caption": "erf heat penetration comparison",
          "in_report_section": "4. Figures",
          "locator": {
            "source_field": "markdown",
            "line": 83,
            "quote": "2. erf heat penetration comparison",
            "quote_sha256": "sha256:e5fc16753e60618d6ff22cef80996b5a1db59fed36bd30dd3468a2d7d63d42bd",
            "occurrences_in_source": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "report_body",
            "reason": "declared as a numbered list item in 'See attached figures for:' but carries no filename, no link, no platform figure name, and no bytes"
          }
        },
        {
          "asset_id": "r6511:figure-body:03",
          "kind": "figure_declaration",
          "name": "unnamed_figure_03",
          "caption": "Graetz Nu correlation",
          "in_report_section": "4. Figures",
          "locator": {
            "source_field": "markdown",
            "line": 84,
            "quote": "3. Graetz Nu correlation",
            "quote_sha256": "sha256:6c2ad0a2fa6831f5ff5f2c4b1561046d3fd74c94d3a905668200468e256885a0",
            "occurrences_in_source": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "report_body",
            "reason": "declared as a numbered list item in 'See attached figures for:' but carries no filename, no link, no platform figure name, and no bytes"
          }
        },
        {
          "asset_id": "r6511:figure-body:04",
          "kind": "figure_declaration",
          "name": "unnamed_figure_04",
          "caption": "Churchill-Chu correlation",
          "in_report_section": "4. Figures",
          "locator": {
            "source_field": "markdown",
            "line": 85,
            "quote": "4. Churchill-Chu correlation",
            "quote_sha256": "sha256:37f8aeead120e8eb34897fb16314035dd77dc68a328e1d853d08b1acfcccbfff",
            "occurrences_in_source": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "report_body",
            "reason": "declared as a numbered list item in 'See attached figures for:' but carries no filename, no link, no platform figure name, and no bytes"
          }
        },
        {
          "asset_id": "r6511:table:error-assessment",
          "kind": "embedded_table",
          "name": "error_assessment_table",
          "in_report_section": "6. Error Assessment",
          "locator": {
            "source_field": "markdown",
            "line": 103,
            "quote": "| Criterion | Target | Achieved | Status |",
            "quote_sha256": "sha256:ff8c2b56894f0eacb4ed69b81ab27fe16e7a8f3f7713d68cf7ff0cd30b1624f5",
            "occurrences_in_source": 1
          },
          "span": {
            "first_line": 103,
            "last_line": 112
          },
          "header_row": "| Criterion | Target | Achieved | Status |",
          "data_rows": 6,
          "columns": [
            "Criterion",
            "Target",
            "Achieved",
            "Status"
          ],
          "resolution": {
            "status": "resolved",
            "scope": "embedded_in_markdown"
          },
          "note": "6 criteria rows (C1-C6) plus a relaxing note; registered as data, not judged here."
        },
        {
          "asset_id": "r6511:figure-record:fig1",
          "kind": "embedded_figure",
          "name": "cht_fig1",
          "caption": "1D composite wall analytical series resistance solution",
          "in_report_section": "record metadata (figures[]), not §4 body",
          "locator": {
            "source_field": "record",
            "path": "figures[0].name",
            "value": "cht_fig1",
            "note": "figure name does not occur in the markdown body; locator is the report record, not the markdown"
          },
          "resolution": {
            "status": "metadata_only",
            "scope": "platform_api",
            "reason": "name+caption declared in record; no figure bytes served (all probes 404)",
            "probes": {
              "/tensor/reports/6511/figures/cht_fig1": {
                "http_status": 404,
                "bytes": 29
              },
              "/tensor/reports/6511/figures/cht_fig1.png": {
                "http_status": 404,
                "bytes": 29
              },
              "/tensor/figures/cht_fig1": {
                "http_status": 404,
                "bytes": 22
              }
            }
          },
          "bytes_available": false
        },
        {
          "asset_id": "r6511:figure-record:fig2",
          "kind": "embedded_figure",
          "name": "cht_fig2",
          "caption": "Semi-infinite solid transient conduction (erf solution)",
          "in_report_section": "record metadata (figures[]), not §4 body",
          "locator": {
            "source_field": "record",
            "path": "figures[1].name",
            "value": "cht_fig2",
            "note": "figure name does not occur in the markdown body; locator is the report record, not the markdown"
          },
          "resolution": {
            "status": "metadata_only",
            "scope": "platform_api",
            "reason": "name+caption declared in record; no figure bytes served (all probes 404)",
            "probes": {}
          },
          "bytes_available": false
        }
      ],
      "claims": [],
      "claims_empty_reason": "Contract wp-6511-01 objective is register_assets=true / classify_report_type=false and its notes state 'claims 允许为空数组' together with constraints no_forced_claim_generation=true and do_not_mark_claims_as_verified=true. This工序 registers asset identity, locators and resolution state only; knowledge extraction belongs to a downstream工序, so an empty claims array is the complete result of this package, not an omission.",
      "counts": {
        "source_documents": 1,
        "assets_total": 15,
        "by_kind": {
          "report_markdown": 1,
          "software_reference": 1,
          "embedded_parameter_list": 1,
          "embedded_table": 2,
          "embedded_formula": 1,
          "absent_artifact": 1,
          "external_reference": 2,
          "figure_declaration": 4,
          "embedded_figure": 2
        },
        "by_resolution_status": {
          "resolved": 5,
          "unresolved": 7,
          "absent": 1,
          "metadata_only": 2
        },
        "figures_declared_body": 4,
        "figures_declared_record": 2,
        "figures_with_bytes": 0,
        "embedded_tables": 2,
        "embedded_parameter_lists": 1,
        "embedded_formulas": 1,
        "path_like_references_in_markdown": 0,
        "fenced_blocks": 1,
        "locators_total": 13,
        "locators_resolved": 13,
        "record_locators": 2,
        "claims": 0
      },
      "id_integrity": {
        "ids_checked": 15,
        "duplicates": [],
        "unique": true
      },
      "unresolved": [
        {
          "asset_id": "r6511:software:tensorlbm",
          "name": "TensorLBM",
          "reason": "repository name appears only in the title; the markdown names no path, commit, tag or version, so the implementing code cannot be resolved from this report"
        },
        {
          "asset_id": "r6511:absent:repro-command",
          "name": "repro_command_or_script",
          "reason": "algorithm is given as 5 prose steps; document contains exactly 1 fenced block(s) and it is a formula, no shell/pytest command, no script path, no input deck and no random seed"
        },
        {
          "asset_id": "r6511:external:shah-london",
          "name": "Shah London",
          "reason": "named correlation with no citation, edition, table/page or formula given in the report; cannot be resolved inside the report"
        },
        {
          "asset_id": "r6511:external:churchill-chu",
          "name": "Churchill Chu",
          "reason": "named correlation with no citation, edition, table/page or formula given in the report; cannot be resolved inside the report"
        },
        {
          "asset_id": "r6511:figure-body:01",
          "name": "unnamed_figure_01",
          "reason": "declared as a numbered list item in 'See attached figures for:' but carries no filename, no link, no platform figure name, and no bytes"
        },
        {
          "asset_id": "r6511:figure-body:02",
          "name": "unnamed_figure_02",
          "reason": "declared as a numbered list item in 'See attached figures for:' but carries no filename, no link, no platform figure name, and no bytes"
        },
        {
          "asset_id": "r6511:figure-body:03",
          "name": "unnamed_figure_03",
          "reason": "declared as a numbered list item in 'See attached figures for:' but carries no filename, no link, no platform figure name, and no bytes"
        },
        {
          "asset_id": "r6511:figure-body:04",
          "name": "unnamed_figure_04",
          "reason": "declared as a numbered list item in 'See attached figures for:' but carries no filename, no link, no platform figure name, and no bytes"
        },
        {
          "asset_id": "r6511:figure-record:fig1",
          "name": "cht_fig1",
          "reason": "name+caption declared in record; no figure bytes served (all probes 404)"
        },
        {
          "asset_id": "r6511:figure-record:fig2",
          "name": "cht_fig2",
          "reason": "name+caption declared in record; no figure bytes served (all probes 404)"
        }
      ],
      "observations": [
        "Report markdown is complete and self-consistent as a document: H1 title + 6 numbered sections (lines 1-112), 6 H2 and 14 H3 headings, 1 fenced block.",
        "Hash discipline: sha256 of the markdown UTF-8 bytes recomputed locally equals the contract source_hash (sha256:e27b9986b028ac9402f4e90705919fc2aea826da4c47de48224665231fc2d840), and chars 4405 equals contract chars 4405; record title and scenario_key equal the contract values.",
        "This report declares NO file-path artifacts: a scan for path-like tokens ([A-Za-z0-9_.:/-]+\\.(?:py|png|json|csv|md|ipynb|pdf|txt|dat|h5|npz)\\b) over the markdown returns 0 matches. Everything registrable in report 6511 is therefore either embedded in the markdown (2 tables, 1 bullet list, 1 formula) or declared-but-unresolvable, so no path in this manifest is asserted to exist in any repository.",
        "Figure declaration inconsistency (registered, not resolved): §4 line 81 says 'See attached figures for:' and numbers 4 figures, while the report record declares only 2 figures (cht_fig1, cht_fig2). The two sets are not mappable 1:1 from the text, so the 4 body declarations stay unresolved and the 2 record figures stay metadata_only; no merge or guess is performed.",
        "No figure bytes exist for report 6511: 5 probe paths (figures, artifacts, figures/cht_fig1, figures/cht_fig1.png, tensor/figures/cht_fig1) all returned HTTP 404.",
        "Downstream flag for 03-extraction (NOT promoted to a claim here, extraction is out of scope for this package): the §6 error table marks C1 (line 105) '| C1: Composite wall | <3% | <5% (analytical) | ✅ |' and C5 (line 109) '| C5: Flux closure | <5% | <20% (interface jump) | ✅ |' as passing although the Achieved column exceeds the Target column; likewise C2 (line 106) '| C2: erf penetration | <5% | <15% (finite domain) | ✅ |' has a 5% target against a 15% achieved value. Whether these count as passes is a claim-level question for the extraction/verification lane.",
        "Recomputation of the two unit systems in the report is out of scope (registration only): §1 gives dimensionless lu units (T_hot=1.0) in Geometry & Parameters and SI units (T_hot=350 K) in the parameter table; both are registered verbatim as-is."
      ],
      "limitations": [
        "Registration only: no claim/evidence extraction, no report-type classification, no verified marks (verification is computed by the platform gate, never by this worker).",
        "source_hash scope = UTF-8 bytes of the markdown string returned by GET /api/v1/tensor/reports/6511; the record's summary field is NOT part of the hash and was used only for cross-checks that are labelled as record-sourced.",
        "Direct psql read of tensor_reports was denied (permission denied for table tensor_reports), so the platform API is the only source channel used for the markdown.",
        "Resolution scope is limited to (a) the markdown itself, (b) the report record fields exposed by the API, (c) five HTTP probes for figure bytes, and (d) the delivery worktree. A name that cannot be resolved in these scopes is reported unresolved, never as a broken upstream artifact.",
        "The report record declares mission_id=5486 while this work package carries mission_id=null; the mismatch is recorded, not reconciled (out of scope, and reconciliation must not consume another report_id).",
        "Line numbers are 1-based indices into the stored markdown string split on '\\n'; the file has no CRLF, so they are stable for this hash only."
      ]
    }
  },
  "claims": []
}
```
