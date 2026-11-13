# ① 本工序做了什么

本单是 `wp-8163-01`（task_type `01-asset-registration`，lane C）—— 报告→知识产线的**第一道工序：源资产登记**，不抽取、不生成 claim、不打 `verified` 标记。

* 只处理 `report_id=8163`：从 `GET /api/v1/tensor/reports/8163` 取 `markdown`，本地重算字节哈希，与契约 `source_hash` 对齐。
* 登记该报告自身声明的可解析资产：源文档本体 1 件、正文内嵌图 2 件、审计链代码/测试/绘图路径 3 条、产物目录 1 条、正文点名的求解器/辅助符号 2 条，合计 **9 件**。
* 每件资产都带机器可复核定位器（字符跨度 + 1-based 行跨度 + 逐字引文 + 唯一性判定）；**引文全部由脚本从 markdown 切片得到，零手抄**。
* 明确不登记的东西也记账（`m5404`、`IN155-N07` 是任务/战役编号而非资产，见 ⑤-3）。

# ② 怎么做的（步骤 / 工具 / 关键设置）

| 步 | 动作 | 工具 / 实现 |
|---|---|---|
| 1 | 取源与元数据 | `GET /api/v1/tensor/reports/8163`（Bearer=登录 token），落 `runs/wp-8163-01/` |
| 2 | 身份校验 | `sha256(markdown.encode("utf-8"))` = `7b48265e05e153c69347ff038be80e20a8f309fbb0563599fa21c98e22b910e7`；`chars=7785`、title、scenario 逐项与契约比对（见下表） |
| 3 | 资产枚举 | 三条正则 + 记录字段：`\`(path)\.(py\|png\|json…)\``（审计链路径）、`![alt](path)`（正文内嵌图）、`\`artifacts/…/\``（产物目录）、`record.figures[]`（平台图元数据）、符号词表 2 条 |
| 4 | 定位器生成 | `char_span(md, quote)`：断言 `md.count(quote)==1`，取 `md[start:end]==quote`、`start_line=md.count("\n",0,start)+1` |
| 5 | 解析判定 | 路径类：在本交付 worktree 内 `Path.exists()` + 平台 `GET /tensor/reports/8163/artifacts`、`/figures/<name>` 探针；符号类：只登记引用、不宣称存在 |
| 6 | 结构校验 | `jsonschema` Draft2020-12：信封 vs `schemas/kf_result.v1.schema.json`；清单 vs 派生 schema（见 ⑤-1） |
| 7 | 复核 | `verify` 重新抓一次活体 markdown，对全部 9 个定位器重解析字符跨度/行号/唯一性 |
| 8 | 出图 | matplotlib（Agg）两张：类别×状态分布、定位器字符跨度覆盖 |

**身份比对（全部程序化，不手打）**

| 字段 | 契约值 | 实测 | 一致 |
|---|---|---|---|
| source_hash | `sha256:7b48265e05e153c69347ff038be80e20a8f309fbb0563599fa21c98e22b910e7` | `sha256:7b48265e05e153c69347ff038be80e20a8f309fbb0563599fa21c98e22b910e7` | True |
| chars | 7785 | 7785 | True |
| title | Rigid Collision Energy Ledger Convergence Certification: Th… | Rigid Collision Energy Ledger Convergence Certification: Th… | True |
| scenario_key | `IN155-N07_rigid_collision_energy_convergence` | `IN155-N07_rigid_collision_energy_convergence` | True |

# ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-8163-01/asset_manifest.json` | 登记清单本体：9 个资产、9 个可解析定位器、counts/by_class/by_resolution 全表 |
| `docs/kf/wp-8163-01/kf_result.json` | 平台结果信封（package_id/task_type/report_id/provenance/outputs），provenance.source_hash=sha256:7b48265… |
| `docs/kf/wp-8163-01/verification.json` | 自检记录：7 项 acceptance 逐条结论 + all_pass=True |
| `docs/kf/wp-8163-01/locator_check.json` | 定位器复核：9 条引文对活体 markdown 重解析，可解析 9 条 |
| `docs/kf/wp-8163-01/source.md` | 只读源副本（7785 字符 / 11158 字节），供离线复核 |
| `runs/wp-8163-01/source_8163.md` | 抓取现场的 markdown 原样落盘（与 docs 副本同字节） |
| `runs/wp-8163-01/report_8163.json` | GET /tensor/reports/8163 的原始响应（含 title/scenario/figures/tags 元数据） |
| `docs/kf/wp-8163-01/figures/asset_resolution_map.png` | 图 1：资产类别 × 解析状态分布 |
| `docs/kf/wp-8163-01/figures/locator_coverage.png` | 图 2：每个定位器的字符跨度对照 markdown 全长 |
| `docs/kf/wp-8163-01/asset_manifest.v1.wp8163.schema.json` | 由 schemas/asset_manifest.v1.schema.json 仅替换 3 个 const 得到的派生 schema（见 ⑤-1） |
| `scripts/kf/kf_wp8163_01_register.py` | 一键复跑：build/envelope/verify/figure/all，引文一律从 markdown 切片不手打 |
| `scripts/kf/kf_wp8163_01_publish.py` | 本报告渲染 + 发布（数字全部由 JSON 注入） |

**计数面**：assets=9；by_class：report_markdown=1、figure_reference=2、artifact_directory_reference=1、source_code_reference=3、symbol_reference=2；by_resolution：resolved_in_source=1、referenced_unresolved=8；distinct_referenced_paths=5；claims=0（契约允许空数组，本单不抽取）。

# ④ 证据定位表（资产 → 原文逐字引文）

引文为 markdown 中该行原文切片（表格内 `\|` 为转义），`L` 为 1-based 行号，字符跨度为 0-based 半开区间；`locator_check.json` 记录了每条引文的实时命中次数（全部 = 1）。

| asset_id | class | 行跨度 | 字符跨度 | 原文引文（逐字） | resolution |
|---|---|---|---|---|---|
| A01 | report_markdown | L1–242 | 0–7785 | # Rigid Collision Energy Ledger Convergence Certification | resolved_in_source |
| A02 | figure_reference | L143–143 | 4879–4969 | ![Energy Methods Schematic](artifacts/rigid_collision_energy/energy_met… | referenced_unresolved |
| A03 | figure_reference | L149–149 | 5009–5087 | ![Convergence Orders](artifacts/rigid_collision_energy/convergence_orde… | referenced_unresolved |
| A04 | artifact_directory_reference | L234–234 | 7564–7611 | - **产物路径**: `artifacts/rigid_collision_energy/` | referenced_unresolved |
| A05 | source_code_reference | L231–231 | 7375–7428 | - **代码实现**: `src/tensordem/rigid_collision_energy.py` | referenced_unresolved |
| A06 | source_code_reference | L232–232 | 7429–7502 | - **测试用例**: `tests/test_rigid_collision_energy_convergence.py` (6/6 PAS… | referenced_unresolved |
| A07 | source_code_reference | L233–233 | 7503–7563 | - **图表生成**: `scripts/plot_rigid_collision_energy_minimal.py` | referenced_unresolved |
| A08 | symbol_reference | L42–42 | 1037–1109 | 1. **碰撞场景构建**: 使用 TensorDEM 的 IceDEM3D 引擎，构建两球对心碰撞场景。所有其他粒子冻结，仅保留两个自由球体。 | referenced_unresolved |
| A09 | symbol_reference | L53–53 | 1624–1702 | - 阻尼系数：通过 $c_n = \text{restitution\_to\_damping}(e_{target}, k_n, m_{ef… | referenced_unresolved |

# ⑤ 注意点与局限

1. **schema 双轨，必须说明**：`schemas/asset_manifest.v1.schema.json` 把 `package_id`/`report_id`/`source.uri` 用 `const` 死锁在 `wp-448-01` 上，任何其它工作包都不可能"原样"通过它。本单的 `schema_pass` 因此分两段：信封严格对 `schemas/kf_result.v1.schema.json`（0 error）；清单对一份**只替换那 3 个 `const`、其余约束一字未改**的派生 schema（`asset_manifest.v1.wp8163.schema.json`，0 error）。派生 schema 随包提交，可复核；若平台侧 schema 与 `wp-448-01` 版不同，以平台门为准，本产物需相应修订。
2. **解析 ≠ 存在**：`referenced_unresolved` 只表示"在本交付 worktree 与平台记录里取不到字节"，**不是**对上游 TensorDEM 仓的否定判决。`src/tensordem/rigid_collision_energy.py`、`tests/test_rigid_collision_energy_convergence.py`、`scripts/plot_rigid_collision_energy_minimal.py` 按路径在 `git ls-files` 中 0 命中（本仓是 TensorKnowledge，不是生产者仓），故标未解析。
3. **不登记项的显式记账**：`m5404`（正文出现 9 次）是任务编号，报告未点名它产生的任何文件/图；`IN155-N07` 是战役编号。二者不构成可定位资产，登记成资产反而是造假。
4. **平台不存图字节**：`record.figures[]` 只有 name+caption；`GET /tensor/reports/8163/figures/energy_methods_schematic` 与 `.../convergence_orders` 均返回 404 级探针失败（figure not found / Not Found），因此对两颗图**不声明任何哈希**。
5. **本单边界**：不改写上游产物、不写其它 report_id、不对报告内容正确性做任何判断（那是 03/04 工序与平台门的活）。`claims` 为空是契约允许的完整结果（`objective.classify_report_type=false`、`no_forced_claim_generation=true`）。
6. **复跑可重复性**：`generated_at`/`emitted_at`/`verified_at` 为运行时时间戳，故清单 sha256 每次复跑会变，但 `source.hash`、`counts`、`assets` 全字段不变。

# ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 证据/说明 |
|---|---|---|
| valid_json | ✅ | json.loads OK for kf_result.json and asset_manifest.json |
| schema_pass | ✅ | kf_result vs schemas/kf_result.v1.schema.json errors=0; manifest vs retargeted asset_manifest.v1 (asset_manifest.v1.wp8163.schema.json) errors=0 |
| source_locator_resolvable | ✅ | checked 9 locators against the live markdown; unresolvable=0 |
| source_hash_matches | ✅ | recomputed=7b48265e05e153c69347ff038be80e20a8f309fbb0563599fa21c98e22b910e7 declared=7b48265e05e153c69347ff038be80e20a8f309fbb0563599fa21c98e22b910e7… |
| no_duplicate_ids | ✅ | assets=9 unique=9 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=0 violating=0 (empty array satisfies the constraint per the contract note 'claims 允许为空数组') |
| do_not_mark_claims_as_verified | ✅ | no claim carries status=verified (verification is platform-gated) |

* 7 项自检 **all_pass=True**；`manifest_sha256=af5075ed242951b380f2c8a126ee24f73b7ac5383d38c6372c4e45f08ba90a66`（本次运行）。
* 超出 acceptance 的额外自检 **覆盖完备性**：True——把与 `build` 完全相同的枚举正则重跑在活体 markdown 上，要求每个命中都是已登记资产；`enumerated_not_registered=[]`、`record_figures_not_registered=[]`。
* honest 说明：`schema_pass` 的通过依赖 ⑤-1 的派生 schema；若审核方要求"原样"通过 `wp-448-01` 版 schema，则该项应记 **not_pass（不可满足）**，因为该文件的 `const` 与本 package 冲突。

**repro_cmd**（工作树根执行，需要 `TENSOR_API_BASE`/`TENSOR_AGENT_USER`/`TENSOR_AGENT_PASS`）：

`python3 scripts/kf/kf_wp8163_01_register.py all && python3 scripts/kf/kf_wp8163_01_publish.py render`

单步可拆：`build`（抓取+清单）、`envelope`（信封）、`verify`（六项+verified 禁忌共 7 项自检，失败返回非零）、`figure`（两张 png）。

---

唯一的结果 JSON 块（kf_result envelope，schema `schemas/kf_result.v1.schema.json`）：

```json
{
  "package_id": "wp-8163-01",
  "task_type": "01-asset-registration",
  "report_id": "8163",
  "provenance": {
    "source_hash": "sha256:7b48265e05e153c69347ff038be80e20a8f309fbb0563599fa21c98e22b910e7",
    "source_field": "markdown",
    "producer": "kf-worker/m15607",
    "emitted_at": "2026-11-12T01:32:55.281474+00:00",
    "notes": "sha256 over the UTF-8 bytes of GET /api/v1/tensor/reports/8163 `markdown`; recomputed locally, equals the contract source_hash sha256:7b48265e05e153c69347ff038be80e20a8f309fbb0563599fa21c98e22b910e7."
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-8163-01",
      "task_type": "01-asset-registration",
      "report_id": "8163",
      "lane": "C",
      "generated_at": "2026-11-12T01:32:55.279253+00:00",
      "producer": "kf-worker/m15607",
      "schema_note": "Shape follows schemas/asset_manifest.v1.schema.json. That file pins package_id/report_id/source.uri with `const` to wp-448-01, so it cannot validate any other package verbatim; verify regenerates a retargeted copy (asset_manifest.v1.wp8163.schema.json: only the three `const` values changed) and validates against both that copy and schemas/kf_result.v1.schema.json.",
      "source": {
        "uri": "tensor://reports/8163",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "7b48265e05e153c69347ff038be80e20a8f309fbb0563599fa21c98e22b910e7",
        "chars": 7785,
        "bytes_utf8": 11158,
        "lines": 242,
        "title": "Rigid Collision Energy Ledger Convergence Certification: Three-Method Audit and m5404 Residual Attribution",
        "scenario_key": "IN155-N07_rigid_collision_energy_convergence",
        "platform_figures": [
          {
            "name": "energy_methods_schematic",
            "caption": "三种能量核算方法的数学表述、精度等级和相互关系。方法 (i) 和 (ii-b) 在机器精度内等价，方法 (ii-a) 为一阶精度。"
          },
          {
            "name": "convergence_orders",
            "caption": "收敛阶分析四子图：(左上) 方法 (ii-a) vs (ii-b) 显示 O(dt) 收敛，斜率=1.02；(右上) 方法 (i) vs (ii-b) 在机器精度；(左下) 恢复系数随时间步收敛；(右下) 方法 (i) vs 理论显示时间离散化误差主导。"
          }
        ],
        "platform_tags": [
          "DEM",
          "energy_conservation",
          "collision",
          "convergence",
          "verification",
          "rigid_body"
        ],
        "platform_mission_id": 6820,
        "platform_status": "published",
        "fetched_via": "GET /api/v1/tensor/reports/8163",
        "contract_source_hash": "sha256:7b48265e05e153c69347ff038be80e20a8f309fbb0563599fa21c98e22b910e7",
        "contract_chars": 7785,
        "contract_title": "Rigid Collision Energy Ledger Convergence Certification: Three-Method Audit and m5404 Residual Attribution",
        "contract_scenario_key": "IN155-N07_rigid_collision_energy_convergence",
        "hash_matches_contract": true,
        "chars_match_contract": true,
        "title_matches_contract": true,
        "scenario_matches_contract": true
      },
      "counts": {
        "assets": 9,
        "by_class": {
          "report_markdown": 1,
          "figure_reference": 2,
          "artifact_directory_reference": 1,
          "source_code_reference": 3,
          "symbol_reference": 2
        },
        "by_resolution": {
          "resolved_in_source": 1,
          "referenced_unresolved": 8
        },
        "resolved_in_source": 1,
        "referenced_unresolved": 8,
        "declared_absent": 0,
        "distinct_referenced_paths": 5
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "report_markdown",
          "label": "report-8163-markdown",
          "in_report_section": "(whole document)",
          "uri": "tensor://reports/8163",
          "media_type": "text/markdown",
          "chars": 7785,
          "bytes_utf8": 11158,
          "sha256": "sha256:7b48265e05e153c69347ff038be80e20a8f309fbb0563599fa21c98e22b910e7",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 7785,
            "start_line": 1,
            "end_line": 242,
            "quote": "# Rigid Collision Energy Ledger Convergence Certification",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256(recomputed) == contract source_hash and chars == contract chars",
            "result": "resolved"
          },
          "note": "Fetched from GET /api/v1/tensor/reports/8163; byte hash over the UTF-8 encoding of the `markdown` field."
        },
        {
          "asset_id": "A02",
          "asset_class": "figure_reference",
          "label": "artifacts/rigid_collision_energy/energy_methods_schematic.png",
          "in_report_section": "### 图 1: 能量核算方法示意图",
          "uri": "tensor://reports/8163#figure:energy_methods_schematic",
          "platform_figure_name": "energy_methods_schematic",
          "platform_caption": "三种能量核算方法的数学表述、精度等级和相互关系。方法 (i) 和 (ii-b) 在机器精度内等价，方法 (ii-a) 为一阶精度。",
          "locator": {
            "method": "char_span",
            "start_char": 4879,
            "end_char": 4969,
            "start_line": 143,
            "end_line": 143,
            "quote": "![Energy Methods Schematic](artifacts/rigid_collision_energy/energy_methods_schematic.png)",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "binary path resolved in worktree (artifacts/rigid_collision_energy/energy_methods_schematic.png) and platform figure endpoint GET /api/v1/tensor/reports/8163/figures/energy_methods_schematic",
            "result": "unresolved",
            "path_in_worktree": false,
            "figure_endpoint_status": 404
          },
          "note": "Image path is quoted verbatim from the report body; the producing byte payload lives in the upstream repo, not in this record (record.figures[] carries name+caption only)."
        },
        {
          "asset_id": "A03",
          "asset_class": "figure_reference",
          "label": "artifacts/rigid_collision_energy/convergence_orders.png",
          "in_report_section": "### 图 2: 收敛阶分析",
          "uri": "tensor://reports/8163#figure:convergence_orders",
          "platform_figure_name": "convergence_orders",
          "platform_caption": "收敛阶分析四子图：(左上) 方法 (ii-a) vs (ii-b) 显示 O(dt) 收敛，斜率=1.02；(右上) 方法 (i) vs (ii-b) 在机器精度；(左下) 恢复系数随时间步收敛；(右下) 方法 (i) vs 理论显示时间离散化误差主导。",
          "locator": {
            "method": "char_span",
            "start_char": 5009,
            "end_char": 5087,
            "start_line": 149,
            "end_line": 149,
            "quote": "![Convergence Orders](artifacts/rigid_collision_energy/convergence_orders.png)",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "binary path resolved in worktree (artifacts/rigid_collision_energy/convergence_orders.png) and platform figure endpoint GET /api/v1/tensor/reports/8163/figures/convergence_orders",
            "result": "unresolved",
            "path_in_worktree": false,
            "figure_endpoint_status": 404
          },
          "note": "Image path is quoted verbatim from the report body; the producing byte payload lives in the upstream repo, not in this record (record.figures[] carries name+caption only)."
        },
        {
          "asset_id": "A04",
          "asset_class": "artifact_directory_reference",
          "label": "artifacts/rigid_collision_energy/",
          "in_report_section": "## 8. 审计链 (Audit Trail)",
          "uri": "tensor://reports/8163#path:artifacts/rigid_collision_energy/",
          "locator": {
            "method": "char_span",
            "start_char": 7564,
            "end_char": 7611,
            "start_line": 234,
            "end_line": 234,
            "quote": "- **产物路径**: `artifacts/rigid_collision_energy/`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path_exists_in_delivery_worktree(TensorKnowledge@/root/tensor) + platform artifact probe",
            "result": "unresolved",
            "path": "artifacts/rigid_collision_energy",
            "abs_exists": false
          },
          "note": "Directory named in the audit trail; the report body also embeds two png files under it (see the figure_reference assets)."
        },
        {
          "asset_id": "A05",
          "asset_class": "source_code_reference",
          "label": "src/tensordem/rigid_collision_energy.py",
          "in_report_section": "## 8. 审计链 (Audit Trail)",
          "uri": "tensor://reports/8163#path:src/tensordem/rigid_collision_energy.py",
          "locator": {
            "method": "char_span",
            "start_char": 7375,
            "end_char": 7428,
            "start_line": 231,
            "end_line": 231,
            "quote": "- **代码实现**: `src/tensordem/rigid_collision_energy.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path_exists_in_delivery_worktree(TensorKnowledge@/root/tensor) + platform artifact probe",
            "result": "unresolved",
            "path": "src/tensordem/rigid_collision_energy.py",
            "abs_exists": false
          },
          "note": "Declared in the report's audit trail; the file lives in the producing repository (TensorDEM), outside this work package's boundary."
        },
        {
          "asset_id": "A06",
          "asset_class": "source_code_reference",
          "label": "tests/test_rigid_collision_energy_convergence.py",
          "in_report_section": "## 8. 审计链 (Audit Trail)",
          "uri": "tensor://reports/8163#path:tests/test_rigid_collision_energy_convergence.py",
          "locator": {
            "method": "char_span",
            "start_char": 7429,
            "end_char": 7502,
            "start_line": 232,
            "end_line": 232,
            "quote": "- **测试用例**: `tests/test_rigid_collision_energy_convergence.py` (6/6 PASS)",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path_exists_in_delivery_worktree(TensorKnowledge@/root/tensor) + platform artifact probe",
            "result": "unresolved",
            "path": "tests/test_rigid_collision_energy_convergence.py",
            "abs_exists": false
          },
          "note": "Declared in the report's audit trail; the file lives in the producing repository (TensorDEM), outside this work package's boundary."
        },
        {
          "asset_id": "A07",
          "asset_class": "source_code_reference",
          "label": "scripts/plot_rigid_collision_energy_minimal.py",
          "in_report_section": "## 8. 审计链 (Audit Trail)",
          "uri": "tensor://reports/8163#path:scripts/plot_rigid_collision_energy_minimal.py",
          "locator": {
            "method": "char_span",
            "start_char": 7503,
            "end_char": 7563,
            "start_line": 233,
            "end_line": 233,
            "quote": "- **图表生成**: `scripts/plot_rigid_collision_energy_minimal.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path_exists_in_delivery_worktree(TensorKnowledge@/root/tensor) + platform artifact probe",
            "result": "unresolved",
            "path": "scripts/plot_rigid_collision_energy_minimal.py",
            "abs_exists": false
          },
          "note": "Declared in the report's audit trail; the file lives in the producing repository (TensorDEM), outside this work package's boundary."
        },
        {
          "asset_id": "A08",
          "asset_class": "symbol_reference",
          "label": "IceDEM3D",
          "in_report_section": "### 数值实现",
          "uri": "tensor://reports/8163#symbol:IceDEM3D",
          "locator": {
            "method": "char_span",
            "start_char": 1037,
            "end_char": 1109,
            "start_line": 42,
            "end_line": 42,
            "quote": "1. **碰撞场景构建**: 使用 TensorDEM 的 IceDEM3D 引擎，构建两球对心碰撞场景。所有其他粒子冻结，仅保留两个自由球体。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "token 'IceDEM3D' resolved to line 42 of the report prose",
            "result": "unresolved",
            "existence_asserted_by_worker": false
          },
          "note": "Symbol is named in the report prose; this work package registers the reference and does not open the TensorDEM tree to confirm it exists."
        },
        {
          "asset_id": "A09",
          "asset_class": "symbol_reference",
          "label": "restitution_to_damping",
          "in_report_section": "### 关键设置",
          "uri": "tensor://reports/8163#symbol:restitution_to_damping",
          "locator": {
            "method": "char_span",
            "start_char": 1624,
            "end_char": 1702,
            "start_line": 53,
            "end_line": 53,
            "quote": "- 阻尼系数：通过 $c_n = \\text{restitution\\_to\\_damping}(e_{target}, k_n, m_{eff})$ 计算",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "token 'restitution\\\\_to\\\\_damping' resolved to line 53 of the report prose",
            "result": "unresolved",
            "existence_asserted_by_worker": false
          },
          "note": "Symbol is named in the report prose; this work package registers the reference and does not open the TensorDEM tree to confirm it exists."
        }
      ],
      "claims": [],
      "claims_note": "Empty by contract: objective.classify_report_type=false, no extraction performed, no claim may be generated for this work package.",
      "integrity": {
        "quote_uniqueness": {
          "checked": 9,
          "unique": 9
        },
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "quotes_sliced_from_markdown_not_retyped": true
      },
      "registration_coverage": {
        "enumeration": {
          "markdown_backtick_paths_regex": "`([^`]+?\\.(?:py|png|jpg|json|csv|h5|md))`",
          "markdown_image_embeds_regex": "!\\[[^\\]]*\\]\\(([^)]+)\\)",
          "artefact_dir_regex": "`(artifacts/[^`]*/)`",
          "record_figures": "record.figures[] names",
          "symbols": [
            "IceDEM3D",
            "restitution_to_damping"
          ]
        },
        "found": {
          "markdown_backtick_paths": 3,
          "markdown_image_embeds": 2,
          "artefact_dirs": 1,
          "record_figures": 2,
          "symbols": 2
        },
        "not_registered": [
          {
            "token": "m5404",
            "occurrences_in_markdown": 9,
            "reason": "mission/task identifier referenced in the prose (sections 1, 3, 6.1); the document names no artefact or figure belonging to that run, so there is nothing locatable to register"
          },
          {
            "token": "IN155-N07",
            "occurrences_in_markdown": 1,
            "reason": "campaign/task code printed in the footer; not an asset"
          }
        ]
      },
      "probes": {
        "/tensor/reports/8163/artifacts": {
          "http_status": 404
        }
      },
      "limitations": [
        "Registration only: no extraction, no claim generation, no `verified` mark.",
        "Path references are resolved inside this TensorKnowledge worktree; the producing TensorDEM tree is outside the work package boundary, so code/test/plot references stay unresolved by design (not `absent` verdicts about TensorDEM).",
        "record.figures[] exposes name+caption only; no byte payload is served, so no hash is claimed for either figure."
      ]
    }
  }
}
```
