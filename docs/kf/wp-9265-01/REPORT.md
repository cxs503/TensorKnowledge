# KF-RESULT wp-9265-01

**工序** 01-asset-registration ｜ **report_id** 9265 ｜ **lane** B ｜ **producer** kf-worker/m15637
**源** `tensor://reports/9265`（`markdown`）｜ **source_hash** `sha256:d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c`（本机重算，与契约逐字相同）
**交付** `docs/kf/wp-9265-01/asset_manifest.json`（外包一层 `kf_result.v1` 信封）

## ① 本工序做了什么

只做一件事：为 report 9265 登记**源资产身份**并盘点它声明过的附件/工件。**不做抽取、不做分类、不判定真伪**
（契约 `objective.register_assets=true`、`objective.classify_report_type=false`、
`constraints.no_forced_claim_generation=true`、`constraints.do_not_mark_claims_as_verified=true`）。
据此 `claims` 为空数组——这是完整结果而非遗漏（理由原文见 `asset_manifest.json → claims_empty_reason`）。

产出规模（全部实测，非人工填写）：assets=14 (resolved_in_source=1, referenced_unresolved=12, declared_absent=1)；locator 共 **18** 个（资产 14 + 身份事实 4），
字符 / 字节 / 行数 = **9599 / 15943 / 235**，逐字唯一命中率 100%（`max_occurrences=1`）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`GET /api/v1/tensor/reports/9265`（token 由 `/auth/login` 用环境变量换取，脚本零硬编码凭据），
   落 `runs/wp-9265-01/report_9265.json` 与 `source_9265.md`。
2. **独立重算身份**：对 `markdown` 的 UTF-8 字节做 sha256 并与契约 `source_hash` 比对；同时比对
   `chars`、`title`、`scenario_key`。四项全中（见 ④），说明源串既未换行归一化也未重排。
3. **盘点声明物**：逐条从正文提取——5 张记录图（`record.figures` 仅 name+caption）、
   `artifacts/dp_capability/` 目录、`criteria.json` 判据账本、`capability_payload.json`、
   两个落库模块、测试文件、出图脚本，外加报告自陈"没有"的 DNV 对标数据集。
4. **逐字定位**：`locator` 一律由 `str.find` 在源串上切出（不手抄），记录
   `start_char/end_char/start_line/end_line/quote/unique`；引文不存在或不唯一则脚本 `SystemExit`，不出半成品。
5. **解析状态判定（三分类，证据驱动）**：
   - `resolved_in_source`：源资产本体（markdown 字节）——本工作树确实持有其内容；
   - `referenced_unresolved`：图字节与 ship-performance-platform 内路径——**本工作树不持有**。
     实测平台 `GET /tensor/reports/9265/figures`、`/artifacts` 均 **404**、`record.figures[]` 无
     `png_base64` ⇒ 不为任何图片声明哈希；
   - `declared_absent`：DNV 已发表 PSV 包线数值数据集——报告原文自陈"没有可引用"。
6. **信封 + 双 schema 校验**：manifest 包进 `kf_result.v1` 信封；信封按 `schemas/kf_result.v1.schema.json`
   校验，manifest 按**本包重钉 const 的投影 schema** 校验（仓库内 `asset_manifest.v1.schema.json`
   把 `package_id/report_id` 钉死为 wp-448-01/448，故新增投影而非改上游；形状/枚举未变）。
7. **出图**：`locator_map.png` 把 18 个 locator 的 `start_char/end_char` 画在源文档字符轴上
   （坐标全部读自 manifest，无一手抄数字）。
8. **独立验收测试**：`tests/test_kf_wp9265_01_manifest.py` 不经构建脚本内部函数，直接读已发布
   JSON 并从平台重取 markdown 复算哈希/逐字/行号/唯一性（9 项全绿）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-9265-01/asset_manifest.json` | 源身份（hash/chars/title/scenario）+ 14 个资产逐字 locator + 4 条身份事实 + counts/id_integrity/integrity |
| `docs/kf/wp-9265-01/kf_result.json` | `kf_result.v1` 信封：`provenance.source_hash=sha256:d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c`、`outputs.asset_manifest.json`=上述 manifest、`claims=[]` |
| `docs/kf/wp-9265-01/verification.json` | 6 项 acceptance 实测结果 + 18 行 locator 复检明细 + `not_checked` 清单 |
| `docs/kf/wp-9265-01/asset_manifest.wp-9265-01.schema.json` | 本包重钉 const 的投影 schema（让 `schema_pass` 可复跑而非口头断言） |
| `docs/kf/wp-9265-01/figures/locator_map.png` | 资产定位图：18 个 locator 的字符轴位置 + 行号标注；`png_sha256=9bb0081355e047ad308dae23ade5e5d7964905c7baea50008f8b348b38ffe133`（110718 bytes） |
| `docs/kf/wp-9265-01/figures/locator_map.json` | 图元数据（caption / 数据来源 / 哈希），保证图可溯源 |
| `docs/kf/wp-9265-01/REPORT.md` | 本报告（`scripts/kf_wp9265_01_report.py md` 渲染，数字全注入） |
| `scripts/kf_wp9265_01_register.py` | build / envelope / verify / figure / all 五子命令，幂等 |
| `scripts/kf_wp9265_01_report.py` | md / post 两子命令（渲染 + 发布），数字从产物读取 |
| `scripts/kf_wp9265_01_fetch.py` | 取源并打印身份三元组 |
| `tests/test_kf_wp9265_01_manifest.py` | 9 项独立验收测试（含边界与范围守卫） |

## ④ 证据定位表（字段/claim → 原文引文片段，逐字可定位）

身份四项（对照契约）：

| 字段 | 契约值 | 实测值 | 一致 |
|---|---|---|---|
| `source_hash` | `sha256:d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c` | `sha256:d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c` | ✅ |
| `chars` | 9599 | 9599 | ✅ |
| `title` | DP 系统能力评估：推力分配 QP × 环境力平衡 × 操作包线图（IN144-N05 / m7890） | DP 系统能力评估：推力分配 QP × 环境力平衡 × 操作包线图（IN144-N05 / m7890） | ✅ |
| `scenario_key` | `dp_capability_assessment` | `dp_capability_assessment` | ✅ |
| `bytes_utf8` / `lines` | — | 15943 / 235 | 实测 |

资产 → 原文（每条 quote 均为源串中**唯一**子串，构建脚本 + 独立测试双重核验）：

| asset_id | class | label | § | resolution | check | quote (verbatim, 1-based line) |
|---|---|---|---|---|---|---|
| A01 | source_document | `report 9265 markdown (source asset itself)` | whole document | resolved_in_source | resolved | L1: # 动力定位 (DP) 系统能力评估：推力分配 QP × 环境力平衡 × 操作包线图 |
| A02 | figure_declared | `capability_polar.png` | ③3.5 图 / record.figures[0] | referenced_unresolved | unresolved | L154: - `capability_polar.png` — 极坐标操作包线图（5 条等电流曲线 + 最坏失效虚线） |
| A03 | figure_declared | `failure_degradation.png` | ③3.5 图 / record.figures[1] | referenced_unresolved | unresolved | L155: - `failure_degradation.png` — 单件失效降级柱状图（30% 判据线） |
| A04 | figure_declared | `load_models.png` | ③3.5 图 / record.figures[2] | referenced_unresolved | unresolved | L156: - `load_models.png` — 风/流/波浪漂移力系数随来向变化 |
| A05 | figure_declared | `balance.png` | ③3.5 图 / record.figures[3] | referenced_unresolved | unresolved | L157: - `balance.png` — 10 个工况点平衡残差（对数轴）+ 峰值利用率 |
| A06 | figure_declared | `degradation_sensitivity.png` | ③3.5 图 / record.figures[4] | referenced_unresolved | unresolved | L158: - `degradation_sensitivity.png` — 降级随有义波高变化（23%→36%） |
| A07 | artifact_directory | `artifacts/dp_capability/` | document header (产物行) | referenced_unresolved | unresolved | L6: **产物** `artifacts/dp_capability/`（JSON + 5 张 PNG + 判据账本 `criteria.json`） |
| A08 | data_artifact_reference | `criteria.json` | document header (产物行) + ③3.1 | referenced_unresolved | unresolved | L6: 判据账本 `criteria.json` |
| A09 | data_artifact_reference | `capability_payload.json` | ③3.1 表格 | referenced_unresolved | unresolved | L91: 见表 `capability_payload.json` |
| A10 | source_code_reference | `backend/physics/dp_core.py` | document header (落库模块行) | referenced_unresolved | unresolved | L4: `backend/physics/dp_core.py`（物理/数值内核） |
| A11 | source_code_reference | `backend/api/dynamic_positioning.py` | document header (落库模块行) | referenced_unresolved | unresolved | L4: `backend/api/dynamic_positioning.py`（FastAPI 端点） |
| A12 | test_reference | `tests/test_dp_capability.py` | document header (验证行) | referenced_unresolved | unresolved | L5: `tests/test_dp_capability.py`（40 项 pytest，22 s 全绿） |
| A13 | script_reference | `scripts/dp_capability_artifacts_m7890.py` | ①案例介绍 / 复现 | referenced_unresolved | unresolved | L16: `scripts/dp_capability_artifacts_m7890.py` |
| A14 | benchmark_dataset_absent | `DNV 已发表 PSV 包线数值数据集` | ④与 DNV 规范的对照 | declared_absent | absent | L162: 仓库内没有可引用的 DNV 已发表包线数值数据集 |

身份事实（文档头与复现块）：

| fact_id | § | line | quote |
|---|---|---|---|
| title-h1 | ①H1 标题 | L1 | `# 动力定位 (DP) 系统能力评估：推力分配 QP × 环境力平衡 × 操作包线图` |
| campaign-line | 文档头 战役节点行 | L3 | `**战役节点** IN144-N05` |
| module-line | 文档头 落库模块行 | L4 | `**落库模块**` |
| repro-block | 复现代码块 | L230 | `python3 -m pytest tests/test_dp_capability.py -q` |

## ⑤ 注意点与局限

1. **未做抽取是刻意的**：`claims=[]` 且 `claims_empty_reason` 写明契约依据——不得为填指标造知识。
2. **图片零哈希**：5 张图只有 name+caption；平台 figure/artifact 端点 404、工作树亦无同名文件，
   故一律 `referenced_unresolved`，**不声明任何图片 sha256**（拒绝"看起来已验证"的假证据）。
3. **外部仓不可达**：`backend/physics/dp_core.py` 等 7 条路径属 ship-performance-platform，不在本工作树
   （TensorKnowledge）；本次只登记"报告声明了它"，**不主张其存在或正确**。判定证据=6 个候选相对路径逐一
   存在性探测（原文见各资产 `resolution_check.check`）。
4. **不主张报告结论为真**：平衡残差、包线风速、降级百分比等全部**未复算**；报告自身 §⑥ 也把
   风/流/波浪漂移系数与包线绝对值列为 **WITHHELD（无基准）**。本工序零 `verified` 标记。
5. **schema 重钉是本包局部行为**：只新增本包投影文件，未改写上游 schema（互不覆盖）。
6. **边界**：只读写 `report_id=9265` 及其本包产物（`scope_guard.report_ids_touched=["9265"]`），
   无跨包读写，未改上游/下游工作包产物。

## ⑥ 自检（逐条对照 acceptance）

| acceptance item | 结果 | 依据（实测数字） |
|---|---|---|
| `valid_json` | PASS | asset_manifest.json and kf_result.json both parse as JSON objects |
| `schema_pass` | PASS | assets_manifest validated against re-pinned per-package schema; kf_result validated against schemas/kf_result.v1.schema.json; errors=none |
| `source_locator_resolvable` | PASS | 18/18 locators resolved (verbatim substring + char span + line number + uniqueness) |
| `source_hash_matches` | PASS | recomputed sha256:d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c vs contract sha256:d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c |
| `no_duplicate_ids` | PASS | 14 asset ids, duplicates=none |
| `all_claims_have_evidence_or_explicit_unresolved_status` | PASS | claims=0 (empty by contract: no_forced_claim_generation=true, classify_report_type=false); no unbacked claim present |

**误差判定（本工序可量化基准）**：源身份四项（hash / chars / title / scenario_key）与契约**精确相等**
（相对误差 **0%**，是否 <3%：**是**，且是零容差相等而非落在容差内）；locator 逐字唯一命中
**18/18**（0 例失配）。本工序不产生物理量，故无物理误差可判；报告内物理数字真伪留给下游
抽取/复核工序（本单在 `verification.json → not_checked` 显式列出）。
`acceptance` **6/6 PASS**，无 honest-FAIL 项。

**未核项（unknown / not_run，不写作 pass）**：外部仓工件存在性与内容、5 张图字节、
报告数值真伪、"40 项 pytest / 22 s 全绿"自述。

**一键复跑**：

```bash
python3 scripts/kf_wp9265_01_register.py all && python3 -m pytest tests/test_kf_wp9265_01_manifest.py -q
```

## 结果 JSON（本报告唯一 json 代码块，原样提交）

```json
{
  "package_id": "wp-9265-01",
  "task_type": "01-asset-registration",
  "report_id": "9265",
  "provenance": {
    "source_hash": "sha256:d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c",
    "source_field": "markdown",
    "producer": "kf-worker/m15637",
    "emitted_at": "2026-11-12T01:36:13Z",
    "notes": "source_hash = sha256 of the markdown bytes returned by GET /api/v1/tensor/reports/9265 (utf-8, no normalisation)."
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-9265-01",
      "task_type": "01-asset-registration",
      "report_id": "9265",
      "lane": "B",
      "generated_at": "2026-11-12T01:36:13Z",
      "producer": "kf-worker/m15637",
      "scope_guard": {
        "report_ids_touched": [
          "9265"
        ],
        "writes_outside_package_dir": [],
        "extraction_performed": false,
        "claims_verified": false,
        "note": "Registration only (objective.register_assets=true, objective.classify_report_type=false). No upstream/downstream artefact edited."
      },
      "source": {
        "uri": "tensor://reports/9265",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c",
        "contract_hash": "sha256:d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c",
        "hash_match": true,
        "chars": 9599,
        "contract_chars": 9599,
        "chars_match": true,
        "bytes_utf8": 15943,
        "lines": 235,
        "has_crlf": false,
        "has_trailing_newline": false,
        "title": "DP 系统能力评估：推力分配 QP × 环境力平衡 × 操作包线图（IN144-N05 / m7890）",
        "contract_title": "DP 系统能力评估：推力分配 QP × 环境力平衡 × 操作包线图（IN144-N05 / m7890）",
        "title_match": true,
        "scenario_key": "dp_capability_assessment",
        "contract_scenario_key": "dp_capability_assessment",
        "scenario_match": true,
        "record_status": "published",
        "record_stage": null,
        "record_mission_id": 7890,
        "record_created_at": "2026-11-09T03:36:35.342100+00:00",
        "record_created_by": 1,
        "platform_tags": [
          "DP",
          "dynamic-positioning",
          "thrust-allocation",
          "QP",
          "capability-plot",
          "DNV-ST-0111",
          "environmental-loads",
          "DP2-redundancy",
          "IN144-N05"
        ],
        "platform_figures": [
          {
            "name": "capability_polar.png",
            "caption": "图1 DP 操作包线极坐标图：等电流族（0~2 m/s）最大可持续风速 vs 环境来向，Hs 3 m，可用推力 0.6",
            "has_png_base64": false,
            "caption_in_markdown": false
          },
          {
            "name": "failure_degradation.png",
            "caption": "图2 单推力器失效后的能力降级（DP-2 最坏单点失效），30% 判据线",
            "has_png_base64": false,
            "caption_in_markdown": false
          },
          {
            "name": "load_models.png",
            "caption": "图3 环境载荷模型：风/流纵向与横向系数、不同海况的波浪平均漂移力随来向变化",
            "has_png_base64": false,
            "caption_in_markdown": false
          },
          {
            "name": "balance.png",
            "caption": "图4 10 个工况点的 3-DOF 平衡残差（对数轴）与 QP 分配峰值利用率",
            "has_png_base64": false,
            "caption_in_markdown": false
          },
          {
            "name": "degradation_sensitivity.png",
            "caption": "图5 DP-2 降级随有义波高变化：最坏艏向 23.0%（Hs1.5）→36.3%（Hs3.0）",
            "has_png_base64": false,
            "caption_in_markdown": false
          }
        ],
        "platform_figure_probes": {
          "/tensor/reports/9265/figures": {
            "http_status": 404,
            "bytes": 0,
            "error": "HTTPError"
          },
          "/tensor/reports/9265/artifacts": {
            "http_status": 404,
            "bytes": 0,
            "error": "HTTPError"
          }
        },
        "fetched_via": "GET /api/v1/tensor/reports/9265",
        "line_counting": "logical lines from markdown.split(chr(10)); 1-based"
      },
      "counts": {
        "assets": 14,
        "by_class": {
          "artifact_directory": 1,
          "benchmark_dataset_absent": 1,
          "data_artifact_reference": 2,
          "figure_declared": 5,
          "script_reference": 1,
          "source_code_reference": 2,
          "source_document": 1,
          "test_reference": 1
        },
        "by_resolution": {
          "declared_absent": 1,
          "referenced_unresolved": 12,
          "resolved_in_source": 1
        },
        "resolved_in_source": 1,
        "referenced_unresolved": 12,
        "declared_absent": 1,
        "figures_declared_in_record": 5,
        "locators": 18,
        "identity_facts": 4,
        "claims": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "source_document",
          "label": "report 9265 markdown (source asset itself)",
          "in_report_section": "whole document",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256(markdown utf-8) == contract source_hash and chars == 9599",
            "result": "resolved"
          },
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 9599,
            "start_line": 1,
            "end_line": 235,
            "quote": "# 动力定位 (DP) 系统能力评估：推力分配 QP × 环境力平衡 × 操作包线图",
            "unique": true
          },
          "note": "Source of truth for every other locator in this manifest; fetched via GET /api/v1/tensor/reports/9265."
        },
        {
          "asset_id": "A02",
          "asset_class": "figure_declared",
          "label": "capability_polar.png",
          "in_report_section": "③3.5 图 / record.figures[0]",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform figure bytes probe (/tensor/reports/9265/figures -> 404, /artifacts -> 404) + worktree file probe over 6 relative paths -> []",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 6062,
            "end_char": 6116,
            "start_line": 154,
            "end_line": 154,
            "quote": "- `capability_polar.png` — 极坐标操作包线图（5 条等电流曲线 + 最坏失效虚线）",
            "unique": true
          },
          "note": "Declared in record metadata (name+caption) and in §3.5; no figure bytes served by the platform for this report, and no such file in the TensorKnowledge worktree. record.caption=\"图1 DP 操作包线极坐标图：等电流族（0~2 m/s）最大可持续风速 vs 环境来向，Hs 3 m，可用推力 0.6\""
        },
        {
          "asset_id": "A03",
          "asset_class": "figure_declared",
          "label": "failure_degradation.png",
          "in_report_section": "③3.5 图 / record.figures[1]",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform figure bytes probe (/tensor/reports/9265/figures -> 404, /artifacts -> 404) + worktree file probe over 6 relative paths -> []",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 6117,
            "end_char": 6165,
            "start_line": 155,
            "end_line": 155,
            "quote": "- `failure_degradation.png` — 单件失效降级柱状图（30% 判据线）",
            "unique": true
          },
          "note": "Declared in record metadata (name+caption) and in §3.5; bytes not available. record.caption=\"图2 单推力器失效后的能力降级（DP-2 最坏单点失效），30% 判据线\""
        },
        {
          "asset_id": "A04",
          "asset_class": "figure_declared",
          "label": "load_models.png",
          "in_report_section": "③3.5 图 / record.figures[2]",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform figure bytes probe (/tensor/reports/9265/figures -> 404, /artifacts -> 404) + worktree file probe over 6 relative paths -> []",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 6166,
            "end_char": 6204,
            "start_line": 156,
            "end_line": 156,
            "quote": "- `load_models.png` — 风/流/波浪漂移力系数随来向变化",
            "unique": true
          },
          "note": "Declared in record metadata (name+caption) and in §3.5; bytes not available. record.caption=\"图3 环境载荷模型：风/流纵向与横向系数、不同海况的波浪平均漂移力随来向变化\""
        },
        {
          "asset_id": "A05",
          "asset_class": "figure_declared",
          "label": "balance.png",
          "in_report_section": "③3.5 图 / record.figures[3]",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform figure bytes probe (/tensor/reports/9265/figures -> 404, /artifacts -> 404) + worktree file probe over 6 relative paths -> []",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 6205,
            "end_char": 6246,
            "start_line": 157,
            "end_line": 157,
            "quote": "- `balance.png` — 10 个工况点平衡残差（对数轴）+ 峰值利用率",
            "unique": true
          },
          "note": "Declared in record metadata (name+caption) and in §3.5; bytes not available. record.caption=\"图4 10 个工况点的 3-DOF 平衡残差（对数轴）与 QP 分配峰值利用率\""
        },
        {
          "asset_id": "A06",
          "asset_class": "figure_declared",
          "label": "degradation_sensitivity.png",
          "in_report_section": "③3.5 图 / record.figures[4]",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform figure bytes probe (/tensor/reports/9265/figures -> 404, /artifacts -> 404) + worktree file probe over 6 relative paths -> []",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 6247,
            "end_char": 6299,
            "start_line": 158,
            "end_line": 158,
            "quote": "- `degradation_sensitivity.png` — 降级随有义波高变化（23%→36%）",
            "unique": true
          },
          "note": "Declared in record metadata (name+caption) and in §3.5; bytes not available. record.caption=\"图5 DP-2 降级随有义波高变化：最坏艏向 23.0%（Hs1.5）→36.3%（Hs3.0）\""
        },
        {
          "asset_id": "A07",
          "asset_class": "artifact_directory",
          "label": "artifacts/dp_capability/",
          "in_report_section": "document header (产物行)",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file exists inside this TensorKnowledge worktree at any of [\"artifacts/dp_capability/\", \"artifacts/artifacts/dp_capability/\", \"docs/artifacts/dp_capability/\", \"scripts/artifacts/dp_capability/\", \"tests/artifacts/dp_capability/\", \"ship-performance-platform/artifacts/dp_capability/\"]",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 273,
            "end_char": 345,
            "start_line": 6,
            "end_line": 6,
            "quote": "**产物** `artifacts/dp_capability/`（JSON + 5 张 PNG + 判据账本 `criteria.json`）",
            "unique": true
          },
          "note": "Output directory of the upstream mission m7890, located in repo ship-performance-platform; not present in this TensorKnowledge delivery worktree."
        },
        {
          "asset_id": "A08",
          "asset_class": "data_artifact_reference",
          "label": "criteria.json",
          "in_report_section": "document header (产物行) + ③3.1",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file exists inside this TensorKnowledge worktree at any of [\"criteria.json\", \"artifacts/criteria.json\", \"docs/criteria.json\", \"scripts/criteria.json\", \"tests/criteria.json\", \"ship-performance-platform/criteria.json\"]",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 324,
            "end_char": 344,
            "start_line": 6,
            "end_line": 6,
            "quote": "判据账本 `criteria.json`",
            "unique": true
          },
          "note": "Criteria ledger (c2/c3 keys quoted in §3.1 and §④); referenced, content not shipped here."
        },
        {
          "asset_id": "A09",
          "asset_class": "data_artifact_reference",
          "label": "capability_payload.json",
          "in_report_section": "③3.1 表格",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file exists inside this TensorKnowledge worktree at any of [\"capability_payload.json\", \"artifacts/capability_payload.json\", \"docs/capability_payload.json\", \"scripts/capability_payload.json\", \"tests/capability_payload.json\", \"ship-performance-platform/capability_payload.json\"]",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3578,
            "end_char": 3606,
            "start_line": 91,
            "end_line": 91,
            "quote": "见表 `capability_payload.json`",
            "unique": true
          },
          "note": "Per-case 3-DOF load table referenced instead of being inlined in the report table."
        },
        {
          "asset_id": "A10",
          "asset_class": "source_code_reference",
          "label": "backend/physics/dp_core.py",
          "in_report_section": "document header (落库模块行)",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file exists inside this TensorKnowledge worktree at any of [\"backend/physics/dp_core.py\", \"artifacts/backend/physics/dp_core.py\", \"docs/backend/physics/dp_core.py\", \"scripts/backend/physics/dp_core.py\", \"tests/backend/physics/dp_core.py\", \"ship-performance-platform/backend/physics/dp_core.py\"]",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 128,
            "end_char": 165,
            "start_line": 4,
            "end_line": 4,
            "quote": "`backend/physics/dp_core.py`（物理/数值内核）",
            "unique": true
          },
          "note": "Numeric/physics kernel (L1-L4) in ship-performance-platform; not in this worktree."
        },
        {
          "asset_id": "A11",
          "asset_class": "source_code_reference",
          "label": "backend/api/dynamic_positioning.py",
          "in_report_section": "document header (落库模块行)",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file exists inside this TensorKnowledge worktree at any of [\"backend/api/dynamic_positioning.py\", \"artifacts/backend/api/dynamic_positioning.py\", \"docs/backend/api/dynamic_positioning.py\", \"scripts/backend/api/dynamic_positioning.py\", \"tests/backend/api/dynamic_positioning.py\", \"ship-performance-platform/backend/api/dynamic_positioning.py\"]",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 166,
            "end_char": 214,
            "start_line": 4,
            "end_line": 4,
            "quote": "`backend/api/dynamic_positioning.py`（FastAPI 端点）",
            "unique": true
          },
          "note": "FastAPI endpoint module in ship-performance-platform; not in this worktree."
        },
        {
          "asset_id": "A12",
          "asset_class": "test_reference",
          "label": "tests/test_dp_capability.py",
          "in_report_section": "document header (验证行)",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file exists inside this TensorKnowledge worktree at any of [\"tests/test_dp_capability.py\", \"artifacts/tests/test_dp_capability.py\", \"docs/tests/test_dp_capability.py\", \"scripts/tests/test_dp_capability.py\", \"tests/tests/test_dp_capability.py\", \"ship-performance-platform/tests/test_dp_capability.py\"]",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 222,
            "end_char": 272,
            "start_line": 5,
            "end_line": 5,
            "quote": "`tests/test_dp_capability.py`（40 项 pytest，22 s 全绿）",
            "unique": true
          },
          "note": "Test suite claimed 40 passed / 22 s; that claim is NOT reproduced here (registration only)."
        },
        {
          "asset_id": "A13",
          "asset_class": "script_reference",
          "label": "scripts/dp_capability_artifacts_m7890.py",
          "in_report_section": "①案例介绍 / 复现",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file exists inside this TensorKnowledge worktree at any of [\"scripts/dp_capability_artifacts_m7890.py\", \"artifacts/scripts/dp_capability_artifacts_m7890.py\", \"docs/scripts/dp_capability_artifacts_m7890.py\", \"scripts/scripts/dp_capability_artifacts_m7890.py\", \"tests/scripts/dp_capability_artifacts_m7890.py\", \"ship-performance-platform/scripts/dp_capability_artifacts_m7890.py\"]",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 531,
            "end_char": 573,
            "start_line": 16,
            "end_line": 16,
            "quote": "`scripts/dp_capability_artifacts_m7890.py`",
            "unique": true
          },
          "note": "Generating script for the report's tables/figures; not in this worktree."
        },
        {
          "asset_id": "A14",
          "asset_class": "benchmark_dataset_absent",
          "label": "DNV 已发表 PSV 包线数值数据集",
          "in_report_section": "④与 DNV 规范的对照",
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "report body states the dataset is not available (grep of the verbatim sentence)",
            "result": "absent"
          },
          "locator": {
            "method": "char_span",
            "start_char": 6323,
            "end_char": 6347,
            "start_line": 162,
            "end_line": 162,
            "quote": "仓库内没有可引用的 DNV 已发表包线数值数据集",
            "unique": true
          },
          "note": "Explicitly declared absent by the report itself -> numerical layer of §④ is WITHHELD."
        }
      ],
      "identity_facts": [
        {
          "fact_id": "title-h1",
          "in_report_section": "①H1 标题",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 42,
            "start_line": 1,
            "end_line": 1,
            "quote": "# 动力定位 (DP) 系统能力评估：推力分配 QP × 环境力平衡 × 操作包线图",
            "unique": true
          },
          "quote_sha256": "218892ffd566bb4b7e1f54b9965c391cd07fe2a15f41f5e4b8839b3c4e898be7"
        },
        {
          "fact_id": "campaign-line",
          "in_report_section": "文档头 战役节点行",
          "locator": {
            "method": "char_span",
            "start_char": 44,
            "end_char": 62,
            "start_line": 3,
            "end_line": 3,
            "quote": "**战役节点** IN144-N05",
            "unique": true
          },
          "quote_sha256": "5861ddde1a71471cc77e9ac3d6752f99b744a7feca302bd7c8393ad591ae598c"
        },
        {
          "fact_id": "module-line",
          "in_report_section": "文档头 落库模块行",
          "locator": {
            "method": "char_span",
            "start_char": 119,
            "end_char": 127,
            "start_line": 4,
            "end_line": 4,
            "quote": "**落库模块**",
            "unique": true
          },
          "quote_sha256": "077835b834d9076c1023d090d4dd3b15b8ef3e4f8beadccb9d685cddd3926f91"
        },
        {
          "fact_id": "repro-block",
          "in_report_section": "复现代码块",
          "locator": {
            "method": "char_span",
            "start_char": 9214,
            "end_char": 9262,
            "start_line": 230,
            "end_line": 230,
            "quote": "python3 -m pytest tests/test_dp_capability.py -q",
            "unique": true
          },
          "quote_sha256": "52f13f9f5f5d5f39bf678dd6b3e6ffc5dddc152c54b2cd2b3991cd54cfac4769"
        }
      ],
      "claims": [],
      "claims_empty_reason": "Contract wp-9265-01 sets objective.register_assets=true, objective.classify_report_type=false, constraints.no_forced_claim_generation=true and notes 'claims 允许为空数组'. This 工序 registers asset identity (report_id + markdown byte hash + declared attachments/artifacts) only; extraction is a downstream 工序. An empty claims array is therefore the complete result, not an omission.",
      "id_integrity": {
        "ids_checked": 14,
        "duplicates": [],
        "unique": true
      },
      "integrity": {
        "quote_uniqueness": {
          "all_unique": true,
          "occurrences": {
            "A01": 1,
            "A02": 1,
            "A03": 1,
            "A04": 1,
            "A05": 1,
            "A06": 1,
            "A07": 1,
            "A08": 1,
            "A09": 1,
            "A10": 1,
            "A11": 1,
            "A12": 1,
            "A13": 1,
            "A14": 1
          },
          "locators_checked": 18,
          "max_occurrences": 1
        },
        "hash_recomputed_locally": "sha256:d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c",
        "hash_matches_contract": true,
        "chars_match_contract": true
      },
      "unresolved": [
        {
          "asset_id": "A02",
          "label": "capability_polar.png",
          "reason": "platform figure bytes probe (/tensor/reports/9265/figures -> 404, /artifacts -> 404) + worktree file probe over 6 relative paths -> []"
        },
        {
          "asset_id": "A03",
          "label": "failure_degradation.png",
          "reason": "platform figure bytes probe (/tensor/reports/9265/figures -> 404, /artifacts -> 404) + worktree file probe over 6 relative paths -> []"
        },
        {
          "asset_id": "A04",
          "label": "load_models.png",
          "reason": "platform figure bytes probe (/tensor/reports/9265/figures -> 404, /artifacts -> 404) + worktree file probe over 6 relative paths -> []"
        },
        {
          "asset_id": "A05",
          "label": "balance.png",
          "reason": "platform figure bytes probe (/tensor/reports/9265/figures -> 404, /artifacts -> 404) + worktree file probe over 6 relative paths -> []"
        },
        {
          "asset_id": "A06",
          "label": "degradation_sensitivity.png",
          "reason": "platform figure bytes probe (/tensor/reports/9265/figures -> 404, /artifacts -> 404) + worktree file probe over 6 relative paths -> []"
        },
        {
          "asset_id": "A07",
          "label": "artifacts/dp_capability/",
          "reason": "file exists inside this TensorKnowledge worktree at any of [\"artifacts/dp_capability/\", \"artifacts/artifacts/dp_capability/\", \"docs/artifacts/dp_capability/\", \"scripts/artifacts/dp_capability/\", \"tests/artifacts/dp_capability/\", \"ship-performance-platform/artifacts/dp_capability/\"]"
        },
        {
          "asset_id": "A08",
          "label": "criteria.json",
          "reason": "file exists inside this TensorKnowledge worktree at any of [\"criteria.json\", \"artifacts/criteria.json\", \"docs/criteria.json\", \"scripts/criteria.json\", \"tests/criteria.json\", \"ship-performance-platform/criteria.json\"]"
        },
        {
          "asset_id": "A09",
          "label": "capability_payload.json",
          "reason": "file exists inside this TensorKnowledge worktree at any of [\"capability_payload.json\", \"artifacts/capability_payload.json\", \"docs/capability_payload.json\", \"scripts/capability_payload.json\", \"tests/capability_payload.json\", \"ship-performance-platform/capability_payload.json\"]"
        },
        {
          "asset_id": "A10",
          "label": "backend/physics/dp_core.py",
          "reason": "file exists inside this TensorKnowledge worktree at any of [\"backend/physics/dp_core.py\", \"artifacts/backend/physics/dp_core.py\", \"docs/backend/physics/dp_core.py\", \"scripts/backend/physics/dp_core.py\", \"tests/backend/physics/dp_core.py\", \"ship-performance-platform/backend/physics/dp_core.py\"]"
        },
        {
          "asset_id": "A11",
          "label": "backend/api/dynamic_positioning.py",
          "reason": "file exists inside this TensorKnowledge worktree at any of [\"backend/api/dynamic_positioning.py\", \"artifacts/backend/api/dynamic_positioning.py\", \"docs/backend/api/dynamic_positioning.py\", \"scripts/backend/api/dynamic_positioning.py\", \"tests/backend/api/dynamic_positioning.py\", \"ship-performance-platform/backend/api/dynamic_positioning.py\"]"
        },
        {
          "asset_id": "A12",
          "label": "tests/test_dp_capability.py",
          "reason": "file exists inside this TensorKnowledge worktree at any of [\"tests/test_dp_capability.py\", \"artifacts/tests/test_dp_capability.py\", \"docs/tests/test_dp_capability.py\", \"scripts/tests/test_dp_capability.py\", \"tests/tests/test_dp_capability.py\", \"ship-performance-platform/tests/test_dp_capability.py\"]"
        },
        {
          "asset_id": "A13",
          "label": "scripts/dp_capability_artifacts_m7890.py",
          "reason": "file exists inside this TensorKnowledge worktree at any of [\"scripts/dp_capability_artifacts_m7890.py\", \"artifacts/scripts/dp_capability_artifacts_m7890.py\", \"docs/scripts/dp_capability_artifacts_m7890.py\", \"scripts/scripts/dp_capability_artifacts_m7890.py\", \"tests/scripts/dp_capability_artifacts_m7890.py\", \"ship-performance-platform/scripts/dp_capability_artifacts_m7890.py\"]"
        }
      ],
      "observations": [
        "Markdown identity verified independently of the contract: recomputed sha256 == contract source_hash, chars == 9599, title and scenario_key match the contract strings.",
        "The 5 record figures carry name+caption only (no png_base64), the platform exposes no figure bytes, and no such files exist in this worktree -> referenced_unresolved (no hash is claimed for any image).",
        "All code/data/test references point into repo ship-performance-platform, which is not part of this worktree -> registered as declared references, existence not asserted.",
        "One asset is declared_absent by the report itself (DNV published PSV envelope dataset), which is why §④ of the report keeps the numerical layer WITHHELD."
      ]
    }
  },
  "claims": []
}
```
