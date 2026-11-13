# KF-RESULT wp-9656-01

**工作包** `wp-9656-01` ｜ **task_type** `01-asset-registration` ｜ **lane** B ｜ **report_id** `9656`
**源** `tensor://reports/9656#markdown` ｜ **source_hash** `sha256:04416e71c0f6dcef356dc57cd48a267661ac42aa46418879e4a4f7ed32918619`（与契约一致：true）
**产出** `asset_manifest.json`（27 条资产） ｜ **claims** 0（契约允许为空：本工序只做登记，不做抽取）

## ① 本工序做了什么

把 `report_id=9656` 的 markdown 登记为产线的**源资产**，并把它自己声明的附件/工件列成可解析清单；不做任何抽取、不改写上游、不标 verified。

1. **身份核对**：取 `GET /api/v1/tensor/reports/9656`，对 `markdown` 字段的 UTF-8 字节重算 sha256，得 `sha256:04416e71c0f6dcef356dc57cd48a267661ac42aa46418879e4a4f7ed32918619`，与契约 `source_hash` 逐字符相等；字符数 `12470` 亦与契约 `12470` 相等（标题/场景键同样比对，见 ④）。
2. **资产枚举**（三层，共 27 条）：
   - 源资产 1 条：`r9656:source-markdown`（20150 bytes / 12470 chars / 289 行，`resolved`）；
   - 报告记录内声明的图 4 条：`fig1_excitation.png` … `fig4_fatigue.png`，记录里只有 name+caption、`png_base64` 为空 → `metadata_only`，**没有字节可哈希，故不编造 sha256**；
   - 正文路径引用 22 条（去重后 15 个不同路径）：`artifacts/ice_shaft_vibration/*.json`、`criteria.json`、`case_results.json`、`model_ledger.json`、四张图、`backend/…` 三个脚本/用例、`backend/modules/ice_shaft_vibration/` 目录 → 均为 `unresolved`（指向**产出仓** ship-performance-platform 的工件，本工作树无该检出，如实记未解析）。
3. **结构清点**（仍属登记，非抽取）：markdown 表 8 张（共 77 行）、一级节 7 个，逐条带行号与逐字表头/标题引文。
4. **未做的事**：零 claim（`claims: []`）、零 verified 标记、跨仓读零次。

## ② 怎么做的（步骤 / 工具 / 关键设置）

### 2.1 流程

```
login → GET /tensor/reports/9656（校验 id 必须是 9656，越界即 abort）
      → 缓存源到 runs/wp-9656-01/source_9656.md（后续离网可复算）
      → sha256(UTF-8 markdown) 与契约常量比对（不等即 SystemExit，绝不写半张清单）
      → 正则扫描三层引用 → 每条算 char 跨度/行号/逐字引文 → 去重（跨度包含关系）
      → 每条路径做两路解析探测：本工作树（含 sha256）/ 外部检出探针（只读）
      → 图：记录级 name+caption+png_base64 长度 → metadata_only 判定
      → 表/节清单 → manifest → envelope(kf_result) → verify(6 项) → figure
```

### 2.2 关键设置

- **哈希口径**：`sha256` over `markdown.encode("utf-8")`（20150 bytes）；`hash_scope` 字段写死该口径，避免下游把「文件字节」与「API 返回值字节」混淆。
- **两种哈希用途分离**：`provenance.source_hash` = 源报告哈希（平台独立重算，本单必须一致）；清单文件的 sha256 另记 `asset_manifest.digest.json`，不塞进自身（自引用哈希不可计算）。
- **定位器口径**：`char_span` 用 `md[start_char:end_char] == quote` 硬校验；同时存 `line_quote`（整行逐字）与 `line_occurrences`（该行在全文出现次数），短路径串重复时标 `unique=false` 而不是假装唯一。
- **唯一性诚实**：`unique` 在全部资产上用同一定义（该字符串在 markdown 原文中出现次数 == 1），实测 6/27 条唯一；其余 21 条因「同一路径既在正文又在产物表」「图名包含在路径里」而重复出现，故标 `unique=false` —— 不是定位缺陷，位置由 `start_line` + `char_span` 唯一确定；4 张图另有 `record_unique=true`（`figures[]` 内每个名字只出现一次）。
- **不猜测**：平台工件端点 `/tensor/reports/9656/artifacts`、`/tensor/artifacts?report_id=9656` 均 404（实测，记入 `platform_probes`），故附件解析只靠正文自述。

### 2.3 一键复跑（repro_cmd）

```bash
# 全流程（需要 TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS）
for c in build envelope verify figure; do python3 scripts/kf/wp9656_01_register.py $c; done
python3 scripts/kf/wp9656_01_report.py render
# 离网不变量自检（不需要 token）
pytest tests/test_kf_wp9656_01.py -q
```

`verify` 会**重新**取一次源、重算哈希、并把全部 42 个定位器重新落在最新 markdown 上（不是复用 build 的结果）。

## ③ 产出物清单

| 文件（worktree 内） | 字节 | sha256（前 16） | 要点 |
|---|---|---|---|
| `asset_manifest.json` | 33928 | `3507a6e3b5db5980` | 登记清单：源资产 + 图 + 22 条正文路径引用 + 表/节清单 |
| `kf_result.json` | 39173 | `3f01823c74d6e55d` | 结果信封（本报告唯一 json 代码块的内容） |
| `verification.json` | 2293 | `c7c1390733b40c07` | acceptance 六项自检 + 定位器计数 |
| `figures/wp9656_01_source_locator_map.png` | 215896 | `648f0d20398db558` | 定位器分布图（行剖面 + kind/status 直方图） |
| `KF-RESULT-wp-9656-01.md` | 51200 | `747cf1f1e7845970` | 本报告正文（自引用，写入后才生成） |

资产按 kind/status 分布（27 条）：

| kind/status | 数量 |
|---|---|
| `data_artifact_reference/unresolved` | 6 |
| `directory_reference/unresolved` | 1 |
| `embedded_figure/metadata_only` | 4 |
| `figure_reference/unresolved` | 8 |
| `report_markdown/resolved` | 1 |
| `source_code_reference/unresolved` | 7 |

## ④ 证据定位表（结论/字段 → 原文逐字引文）

| 字段 / 结论 | 原文行 | 逐字引文片段 | 说明 |
|---|---|---|---|
| 标题（`source.title`，与契约一致：true） | L1 | `# 冰区推进轴系横向振动与轴承载荷模型（IN101-N05）` | markdown 首行即标题，与报告的 `title` 字段一致 |
| 数字全为程序化注入（非手抄） | L5 | ``全部数字由 `backend/scripts/build_ice_shaft_vibration_report.py` 从 `artifacts/ice_shaft_vibration/*.json` 程序化注入，零手抄。`` | 报告自述注入链，支撑「零手抄」 |
| 图 1 引用（`r9656:ref:07`） | L187 | `![fig1](artifacts/ice_shaft_vibration/fig1_excitation.png)` | markdown 图片引用 → `figure_reference`，本工作树不存在 |
| 图 4 引用（`r9656:ref:10`） | L199 | `![fig4](artifacts/ice_shaft_vibration/fig4_fatigue.png)` | 同上，图 2/3 结构相同（L191/L195） |
| 上游结论（仅登记其存在，不采信） | L120 | ``全部判据 all_pass = **True**。机器可读判据：`artifacts/ice_shaft_vibration/criteria.json`；全量结果：`artifacts/ice_shaft_vibration/case_r …`` | 记录原话，本工序不转写为 claim、不标 verified |
| 表 1（六条判据表，`r9656:table:02`） | L111 | `\| # \| 判据 \| 结果 \| 判据值 \| 门槛 \| 判定 \|` | 表清单 8 张之一，此处只登记表头/行数 |
| 表 2（载荷与寿命量级） | L124 | `\| 量 \| 数值 \|` | 供下游 03 工序抽取的量级表 |
| 表 3（误差判定表，逐项「是否<3%」） | L239 | `\| 关键量 \| 基准（独立路线/解析） \| 相对误差 \| 是否 <3% \| 说明 \|` | 报告自带误差判定表，登记为可解析工件 |
| 产物表首行（`criteria.json`） | L280 | ``\| 判据（机器可读） \| `artifacts/ice_shaft_vibration/criteria.json` \|`` | 引用存在但工作树内不可解析（跨仓） |
| 复核命令（上游） | L273 | `pytest tests/test_ice_shaft_vibration.py -v          # 28 passed` | 上游复跑口令，登记不执行 |
| 误差判定收束段 | L254 | `**逐项回答**：` | 逐项回答的段落入口 |
| WITHHELD 声明 | L266 | `- **绝对载荷/寿命无试验基准** → 记 WITHHELD，不做「已对标」声明。` | 上游诚实声明，本工序原样保留不确定性 |
| `source_hash` / `chars` | 全文 | （不可引文，逐字节度量） | `sha256(UTF-8 bytes)=sha256:04416e71c0f6dcef356dc57cd48a267661ac42aa46418879e4a4f7ed32918619`，chars=12470；由 `verify` 与平台门各自独立重算 |

> 表中每条引文都由脚本在执行期从 markdown 直接切片并断言 `quote in source`；引文重复出现时以行号（L 列）唯一确定位置。

## ⑤ 注意点与局限

1. **22 条引用全部 `unresolved` 是设计而不是缺陷**：它们指向产出仓 `ship-performance-platform` 的 `artifacts/`、`backend/`，TensorKnowledge 工作树里没有那次检出（外部只读探针亦报 absent）。跨仓读会破坏「只碰本单报告」的边界，故如实记未解析，等下游按 `tensor://` URI 取。
2. **4 张图 `metadata_only`**：`figures[]` 只有 name+caption，`png_base64` 为空 → 无字节、无哈希。本单**不**用 caption 去猜图内容。
3. **`unique=false` 的语义**：21 条资产引文在全文中出现多次（同一路径既在正文、又在产物表/图名里）。定位靠 `start_line`+`char_span`，不靠「引文唯一」；图另有记录级唯一性 `record_unique`。
4. **命名空间**：资产 id 一律 `r9656:` 前缀，与该报告绑定；不写 `verified`、不写 `claim`，避免下游误当已核验知识。
5. **未覆盖**：不做 report_type 分类（契约 `classify_report_type: false`）；不解析表内数值（03 工序职责）；不核对上游自称的用例通过数（见 L273 引文）是否真通过（跨仓、非本单职权）。
6. **自检独立性有限**：`verify` 由产出脚本自己执行（会重新取源重算，但共用解析代码），最终裁决以平台门独立重算的 `source_hash`/子串为准 —— 本单不自称「已通过平台门」。

## ⑥ 自检：acceptance 逐条

| 验收项 | 结论 | 依据 |
|---|---|---|
| `valid_json` | ✓ PASS | both asset_manifest.json and kf_result.json parse |
| `schema_pass` | ✓ PASS | asset_manifest vs schemas/asset_manifest.v1.wp9656-01.schema.json; kf_result vs schemas/kf_result.v1.schema.json |
| `source_locator_resolvable` | ✓ PASS | 42 locators re-checked against live markdown (27 assets, 8 tables, 7 sections) |
| `source_hash_matches` | ✓ PASS | live=sha256:04416e71c0f6dcef356dc57cd48a267661ac42aa46418879e4a4f7ed32918619 contract=sha256:04416e71c0f6dcef356dc57cd48a267661ac42aa46418879e4a4f7ed32918619 chars=12470 (contract 12470) |
| `no_duplicate_ids` | ✓ PASS | 27 asset ids, duplicates=none |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✓ PASS | 0 claims (empty by contract: objective.register_assets only, no extraction); unbacked=none |

- 定位器实测：42 个检查点（27 资产 + 8 表 + 7 节），解析成功 42 个 → 全绿；`locators_resolved == locators_checked`（42 == 42）。
- 计数自洽：assets_total 27 = resolved 1 + metadata_only 4 + unresolved 22。
- **误差判定（是否 <3%）**：本工作包是**登记类**工序，产出不含物理量预测，因此不存在「计算值 vs 实验/解析基准」的误差判定 —— 无基准不是遗漏，而是任务性质（`objective.register_assets`）。可机器裁决的等价量是**身份一致性**：`source_hash` 相对契约误差 = 0（逐字符相等），字符数误差 = 0（12470 vs 12470），定位器解析失败数 = 0 → **<3% ✓（此处为精确相等）**。
- 上游报告自带的误差判定表中存在结论为 `否（>3%）` 的行（L249：`\| $N_{cycles}$ \| 解析波形+同一 S-N/Miner 管线（手算周期集） \| 4.5326% \| **否** \| 误差来自雨流子循环与波形差异 \|`）；另有 L266 的 WITHHELD 声明。两处**原样登记、不代为判定**，不抹成通过 —— 本单只保证「引文可在原文逐字定位」。
- 数字来源纪律：本报告正文数字全部由脚本从 JSON 工件或源 markdown 注入，上游数值（如上面 L249 的误差）一律以引文形式出现，不由本单手抄转述。

## 附：result JSON（本报告唯一的 json 代码块，机器门按此校验）

```json
{
  "package_id": "wp-9656-01",
  "task_type": "01-asset-registration",
  "report_id": "9656",
  "provenance": {
    "source_uri": "tensor://reports/9656",
    "source_field": "markdown",
    "source_hash": "sha256:04416e71c0f6dcef356dc57cd48a267661ac42aa46418879e4a4f7ed32918619",
    "hash_algo": "sha256",
    "hash_scope": "UTF-8 bytes of the markdown field as served by GET /api/v1/tensor/reports/9656",
    "source_chars": 12470,
    "source_bytes_utf8": 20150,
    "source_lines": 289,
    "fetched_via": "GET /api/v1/tensor/reports/9656",
    "producer": "kf-worker/m15664",
    "emitted_at": "2026-11-12T01:44:55.011459+00:00",
    "contract_version": "1.0",
    "notes": "source_hash recomputed from the live markdown bytes and equals the contract value sha256:04416e71c0f6dcef356dc57cd48a267661ac42aa46418879e4a4f7ed32918619"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-9656-01",
      "task_type": "01-asset-registration",
      "report_id": "9656",
      "lane": "B",
      "generated_at": "2026-11-12T01:44:54.452867+00:00",
      "producer": "kf-worker/m15664",
      "contract_version": "1.0",
      "schema_ref": "schemas/asset_manifest.v1.wp9656-01.schema.json",
      "source": {
        "uri": "tensor://reports/9656",
        "source_field": "markdown",
        "hash_alg": "sha256",
        "source_hash": "sha256:04416e71c0f6dcef356dc57cd48a267661ac42aa46418879e4a4f7ed32918619",
        "hash_scope": "sha256 over UTF-8 bytes of the markdown field",
        "chars": 12470,
        "bytes_utf8": 20150,
        "lines": 289,
        "title": "IN101-N05 冰区推进轴系横向振动与轴承载荷：六条判据全通过（REAL）",
        "scenario_key": "ice_shaft_vibration",
        "report_mission_id": 8346,
        "report_status": "published",
        "report_stage": null,
        "platform_tags": [
          "IN101-N05",
          "ice",
          "shafting",
          "lateral-vibration",
          "bearing-load",
          "fatigue",
          "REAL"
        ],
        "contract_source_hash": "sha256:04416e71c0f6dcef356dc57cd48a267661ac42aa46418879e4a4f7ed32918619",
        "contract_chars": 12470,
        "contract_title": "IN101-N05 冰区推进轴系横向振动与轴承载荷：六条判据全通过（REAL）",
        "contract_scenario_key": "ice_shaft_vibration",
        "hash_matches_contract": true,
        "chars_matches_contract": true,
        "title_matches_contract": true,
        "scenario_matches_contract": true
      },
      "assets": [
        {
          "asset_id": "r9656:source-markdown",
          "kind": "report_markdown",
          "name": "report-9656-markdown",
          "source_uri": "tensor://reports/9656",
          "media_type": "text/markdown",
          "bytes": 20150,
          "chars": 12470,
          "lines": 289,
          "sha256": "sha256:04416e71c0f6dcef356dc57cd48a267661ac42aa46418879e4a4f7ed32918619",
          "hash_scope": "UTF-8 bytes of the `markdown` field as served by GET /api/v1/tensor/reports/9656",
          "local_copy": "runs/wp-9656-01/source_9656.md",
          "locator": {
            "method": "document",
            "source_field": "markdown",
            "start_char": 0,
            "end_char": 30,
            "start_line": 1,
            "end_line": 289,
            "quote": "# 冰区推进轴系横向振动与轴承载荷模型（IN101-N05）",
            "unique": true,
            "doc_chars": 12470,
            "doc_bytes_utf8": 20150,
            "doc_lines": 289
          },
          "resolution": {
            "status": "resolved",
            "scope": "platform_api",
            "via": "GET /tensor/reports/9656"
          }
        },
        {
          "asset_id": "r9656:figure:01",
          "kind": "embedded_figure",
          "name": "fig1_excitation.png",
          "caption": "IN101-N05 图 1",
          "bytes": null,
          "sha256": null,
          "locator": {
            "method": "record_pointer",
            "source_field": "record",
            "pointer": "/figures/0/name",
            "quote": "fig1_excitation.png",
            "unique": false,
            "record_unique": true,
            "markdown_name_occurrences": 2,
            "markdown_image_line": 187
          },
          "resolution": {
            "status": "metadata_only",
            "scope": "platform_api",
            "via": "GET /tensor/reports/9656 figures[0]",
            "has_payload": false,
            "reason": "record lists name+caption only; png_base64 is empty, so no image bytes exist to hash or resolve in this record"
          }
        },
        {
          "asset_id": "r9656:figure:02",
          "kind": "embedded_figure",
          "name": "fig2_shaft_modes.png",
          "caption": "IN101-N05 图 2",
          "bytes": null,
          "sha256": null,
          "locator": {
            "method": "record_pointer",
            "source_field": "record",
            "pointer": "/figures/1/name",
            "quote": "fig2_shaft_modes.png",
            "unique": false,
            "record_unique": true,
            "markdown_name_occurrences": 2,
            "markdown_image_line": 191
          },
          "resolution": {
            "status": "metadata_only",
            "scope": "platform_api",
            "via": "GET /tensor/reports/9656 figures[1]",
            "has_payload": false,
            "reason": "record lists name+caption only; png_base64 is empty, so no image bytes exist to hash or resolve in this record"
          }
        },
        {
          "asset_id": "r9656:figure:03",
          "kind": "embedded_figure",
          "name": "fig3_bearing_load.png",
          "caption": "IN101-N05 图 3",
          "bytes": null,
          "sha256": null,
          "locator": {
            "method": "record_pointer",
            "source_field": "record",
            "pointer": "/figures/2/name",
            "quote": "fig3_bearing_load.png",
            "unique": false,
            "record_unique": true,
            "markdown_name_occurrences": 2,
            "markdown_image_line": 195
          },
          "resolution": {
            "status": "metadata_only",
            "scope": "platform_api",
            "via": "GET /tensor/reports/9656 figures[2]",
            "has_payload": false,
            "reason": "record lists name+caption only; png_base64 is empty, so no image bytes exist to hash or resolve in this record"
          }
        },
        {
          "asset_id": "r9656:figure:04",
          "kind": "embedded_figure",
          "name": "fig4_fatigue.png",
          "caption": "IN101-N05 图 4",
          "bytes": null,
          "sha256": null,
          "locator": {
            "method": "record_pointer",
            "source_field": "record",
            "pointer": "/figures/3/name",
            "quote": "fig4_fatigue.png",
            "unique": false,
            "record_unique": true,
            "markdown_name_occurrences": 2,
            "markdown_image_line": 199
          },
          "resolution": {
            "status": "metadata_only",
            "scope": "platform_api",
            "via": "GET /tensor/reports/9656 figures[3]",
            "has_payload": false,
            "reason": "record lists name+caption only; png_base64 is empty, so no image bytes exist to hash or resolve in this record"
          }
        },
        {
          "asset_id": "r9656:ref:01",
          "kind": "source_code_reference",
          "path_reference": "backend/scripts/build_ice_shaft_vibration_report.py",
          "via": "backticked_ref",
          "markdown_alt": null,
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 150,
            "end_char": 201,
            "start_line": 5,
            "end_line": 5,
            "quote": "backend/scripts/build_ice_shaft_vibration_report.py",
            "unique": true,
            "line_quote": "> 全部数字由 `backend/scripts/build_ice_shaft_vibration_report.py` 从 `artifacts/ice_shaft_vibration/*.json` 程序化注入，零手抄。",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:02",
          "kind": "data_artifact_reference",
          "path_reference": "artifacts/ice_shaft_vibration/*.json",
          "via": "backticked_ref",
          "markdown_alt": null,
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 206,
            "end_char": 242,
            "start_line": 5,
            "end_line": 5,
            "quote": "artifacts/ice_shaft_vibration/*.json",
            "unique": true,
            "line_quote": "> 全部数字由 `backend/scripts/build_ice_shaft_vibration_report.py` 从 `artifacts/ice_shaft_vibration/*.json` 程序化注入，零手抄。",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:03",
          "kind": "source_code_reference",
          "path_reference": "backend/scripts/run_ice_shaft_vibration_case.py",
          "via": "backticked_ref",
          "markdown_alt": null,
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 4129,
            "end_char": 4176,
            "start_line": 104,
            "end_line": 104,
            "quote": "backend/scripts/run_ice_shaft_vibration_case.py",
            "unique": true,
            "line_quote": "工具链：Python/NumPy/SciPy（特征值、求根、优化）+ Matplotlib；算例脚本 `backend/scripts/run_ice_shaft_vibration_case.py`，用例 `backend/tests/test_ice_shaft_vibration.py`。",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:04",
          "kind": "source_code_reference",
          "path_reference": "backend/tests/test_ice_shaft_vibration.py",
          "via": "backticked_ref",
          "markdown_alt": null,
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 4182,
            "end_char": 4223,
            "start_line": 104,
            "end_line": 104,
            "quote": "backend/tests/test_ice_shaft_vibration.py",
            "unique": false,
            "line_quote": "工具链：Python/NumPy/SciPy（特征值、求根、优化）+ Matplotlib；算例脚本 `backend/scripts/run_ice_shaft_vibration_case.py`，用例 `backend/tests/test_ice_shaft_vibration.py`。",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:05",
          "kind": "data_artifact_reference",
          "path_reference": "artifacts/ice_shaft_vibration/criteria.json",
          "via": "backticked_ref",
          "markdown_alt": null,
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 5006,
            "end_char": 5049,
            "start_line": 120,
            "end_line": 120,
            "quote": "artifacts/ice_shaft_vibration/criteria.json",
            "unique": false,
            "line_quote": "全部判据 all_pass = **True**。机器可读判据：`artifacts/ice_shaft_vibration/criteria.json`；全量结果：`artifacts/ice_shaft_vibration/case_results.json`。",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:06",
          "kind": "data_artifact_reference",
          "path_reference": "artifacts/ice_shaft_vibration/case_results.json",
          "via": "backticked_ref",
          "markdown_alt": null,
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 5057,
            "end_char": 5104,
            "start_line": 120,
            "end_line": 120,
            "quote": "artifacts/ice_shaft_vibration/case_results.json",
            "unique": false,
            "line_quote": "全部判据 all_pass = **True**。机器可读判据：`artifacts/ice_shaft_vibration/criteria.json`；全量结果：`artifacts/ice_shaft_vibration/case_results.json`。",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:07",
          "kind": "figure_reference",
          "path_reference": "artifacts/ice_shaft_vibration/fig1_excitation.png",
          "via": "markdown_image",
          "markdown_alt": "fig1",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 7466,
            "end_char": 7515,
            "start_line": 187,
            "end_line": 187,
            "quote": "artifacts/ice_shaft_vibration/fig1_excitation.png",
            "unique": false,
            "line_quote": "![fig1](artifacts/ice_shaft_vibration/fig1_excitation.png)",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:08",
          "kind": "figure_reference",
          "path_reference": "artifacts/ice_shaft_vibration/fig2_shaft_modes.png",
          "via": "markdown_image",
          "markdown_alt": "fig2",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 7657,
            "end_char": 7707,
            "start_line": 191,
            "end_line": 191,
            "quote": "artifacts/ice_shaft_vibration/fig2_shaft_modes.png",
            "unique": false,
            "line_quote": "![fig2](artifacts/ice_shaft_vibration/fig2_shaft_modes.png)",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:09",
          "kind": "figure_reference",
          "path_reference": "artifacts/ice_shaft_vibration/fig3_bearing_load.png",
          "via": "markdown_image",
          "markdown_alt": "fig3",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 7898,
            "end_char": 7949,
            "start_line": 195,
            "end_line": 195,
            "quote": "artifacts/ice_shaft_vibration/fig3_bearing_load.png",
            "unique": false,
            "line_quote": "![fig3](artifacts/ice_shaft_vibration/fig3_bearing_load.png)",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:10",
          "kind": "figure_reference",
          "path_reference": "artifacts/ice_shaft_vibration/fig4_fatigue.png",
          "via": "markdown_image",
          "markdown_alt": "fig4",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 8106,
            "end_char": 8152,
            "start_line": 199,
            "end_line": 199,
            "quote": "artifacts/ice_shaft_vibration/fig4_fatigue.png",
            "unique": false,
            "line_quote": "![fig4](artifacts/ice_shaft_vibration/fig4_fatigue.png)",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:11",
          "kind": "source_code_reference",
          "path_reference": "tests/test_ice_shaft_vibration.py",
          "via": "bare_ref",
          "markdown_alt": null,
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 11692,
            "end_char": 11725,
            "start_line": 273,
            "end_line": 273,
            "quote": "tests/test_ice_shaft_vibration.py",
            "unique": false,
            "line_quote": "pytest tests/test_ice_shaft_vibration.py -v          # 28 passed",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:12",
          "kind": "source_code_reference",
          "path_reference": "scripts/run_ice_shaft_vibration_case.py",
          "via": "bare_ref",
          "markdown_alt": null,
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 11757,
            "end_char": 11796,
            "start_line": 274,
            "end_line": 274,
            "quote": "scripts/run_ice_shaft_vibration_case.py",
            "unique": false,
            "line_quote": "python scripts/run_ice_shaft_vibration_case.py       # 重算 artifacts（~1 min）",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:13",
          "kind": "source_code_reference",
          "path_reference": "scripts/build_ice_shaft_vibration_report.py",
          "via": "bare_ref",
          "markdown_alt": null,
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 11833,
            "end_char": 11876,
            "start_line": 275,
            "end_line": 275,
            "quote": "scripts/build_ice_shaft_vibration_report.py",
            "unique": false,
            "line_quote": "python scripts/build_ice_shaft_vibration_report.py   # 重建本报告（数字全注入）",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:14",
          "kind": "data_artifact_reference",
          "path_reference": "artifacts/ice_shaft_vibration/criteria.json",
          "via": "backticked_ref",
          "markdown_alt": null,
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 11935,
            "end_char": 11978,
            "start_line": 280,
            "end_line": 280,
            "quote": "artifacts/ice_shaft_vibration/criteria.json",
            "unique": false,
            "line_quote": "| 判据（机器可读） | `artifacts/ice_shaft_vibration/criteria.json` |",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:15",
          "kind": "data_artifact_reference",
          "path_reference": "artifacts/ice_shaft_vibration/case_results.json",
          "via": "backticked_ref",
          "markdown_alt": null,
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 11992,
            "end_char": 12039,
            "start_line": 281,
            "end_line": 281,
            "quote": "artifacts/ice_shaft_vibration/case_results.json",
            "unique": false,
            "line_quote": "| 全量结果 | `artifacts/ice_shaft_vibration/case_results.json` |",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:16",
          "kind": "data_artifact_reference",
          "path_reference": "artifacts/ice_shaft_vibration/model_ledger.json",
          "via": "backticked_ref",
          "markdown_alt": null,
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 12070,
            "end_char": 12117,
            "start_line": 282,
            "end_line": 282,
            "quote": "artifacts/ice_shaft_vibration/model_ledger.json",
            "unique": true,
            "line_quote": "| 模型台账（几何/材料/阻尼/S-N/来源） | `artifacts/ice_shaft_vibration/model_ledger.json` |",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:17",
          "kind": "figure_reference",
          "path_reference": "artifacts/ice_shaft_vibration/fig1_excitation.png",
          "via": "backticked_ref",
          "markdown_alt": null,
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 12130,
            "end_char": 12179,
            "start_line": 283,
            "end_line": 283,
            "quote": "artifacts/ice_shaft_vibration/fig1_excitation.png",
            "unique": false,
            "line_quote": "| 图 1 | `artifacts/ice_shaft_vibration/fig1_excitation.png` |",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:18",
          "kind": "figure_reference",
          "path_reference": "artifacts/ice_shaft_vibration/fig2_shaft_modes.png",
          "via": "backticked_ref",
          "markdown_alt": null,
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 12192,
            "end_char": 12242,
            "start_line": 284,
            "end_line": 284,
            "quote": "artifacts/ice_shaft_vibration/fig2_shaft_modes.png",
            "unique": false,
            "line_quote": "| 图 2 | `artifacts/ice_shaft_vibration/fig2_shaft_modes.png` |",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:19",
          "kind": "figure_reference",
          "path_reference": "artifacts/ice_shaft_vibration/fig3_bearing_load.png",
          "via": "backticked_ref",
          "markdown_alt": null,
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 12255,
            "end_char": 12306,
            "start_line": 285,
            "end_line": 285,
            "quote": "artifacts/ice_shaft_vibration/fig3_bearing_load.png",
            "unique": false,
            "line_quote": "| 图 3 | `artifacts/ice_shaft_vibration/fig3_bearing_load.png` |",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:20",
          "kind": "figure_reference",
          "path_reference": "artifacts/ice_shaft_vibration/fig4_fatigue.png",
          "via": "backticked_ref",
          "markdown_alt": null,
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 12319,
            "end_char": 12365,
            "start_line": 286,
            "end_line": 286,
            "quote": "artifacts/ice_shaft_vibration/fig4_fatigue.png",
            "unique": false,
            "line_quote": "| 图 4 | `artifacts/ice_shaft_vibration/fig4_fatigue.png` |",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:21",
          "kind": "directory_reference",
          "path_reference": "backend/modules/ice_shaft_vibration/",
          "via": "backticked_dir",
          "markdown_alt": null,
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 12377,
            "end_char": 12413,
            "start_line": 287,
            "end_line": 287,
            "quote": "backend/modules/ice_shaft_vibration/",
            "unique": true,
            "line_quote": "| 模块 | `backend/modules/ice_shaft_vibration/` |",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "directory not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        },
        {
          "asset_id": "r9656:ref:22",
          "kind": "source_code_reference",
          "path_reference": "backend/tests/test_ice_shaft_vibration.py",
          "via": "backticked_ref",
          "markdown_alt": null,
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 12425,
            "end_char": 12466,
            "start_line": 288,
            "end_line": 288,
            "quote": "backend/tests/test_ice_shaft_vibration.py",
            "unique": false,
            "line_quote": "| 用例 | `backend/tests/test_ice_shaft_vibration.py` |",
            "line_occurrences": 1
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree",
            "external_probe": [
              {
                "root": "/root/ship-performance-platform",
                "status": "absent"
              }
            ]
          }
        }
      ],
      "tables": [
        {
          "table_id": "r9656:table:01",
          "line_start": 26,
          "line_end": 51,
          "rows": 24,
          "cols": 4,
          "header_quote": "| 参数 | 符号 | 取值 | 单位 |",
          "header_unique": true,
          "start_char": 803
        },
        {
          "table_id": "r9656:table:02",
          "line_start": 111,
          "line_end": 118,
          "rows": 6,
          "cols": 6,
          "header_quote": "| # | 判据 | 结果 | 判据值 | 门槛 | 判定 |",
          "header_unique": true,
          "start_char": 4268
        },
        {
          "table_id": "r9656:table:03",
          "line_start": 124,
          "line_end": 133,
          "rows": 8,
          "cols": 2,
          "header_quote": "| 量 | 数值 |",
          "header_unique": true,
          "start_char": 5131
        },
        {
          "table_id": "r9656:table:04",
          "line_start": 139,
          "line_end": 145,
          "rows": 5,
          "cols": 4,
          "header_quote": "| 模态阶数 | 谐波阶数 | 手算峰值 [N] | 与时域数值的相对差 |",
          "header_unique": true,
          "start_char": 5728
        },
        {
          "table_id": "r9656:table:05",
          "line_start": 151,
          "line_end": 158,
          "rows": 6,
          "cols": 3,
          "header_quote": "| 路线 | $f_1$ [Hz] | 与 FEM 相对差 |",
          "header_unique": true,
          "start_char": 6033
        },
        {
          "table_id": "r9656:table:06",
          "line_start": 168,
          "line_end": 176,
          "rows": 7,
          "cols": 5,
          "header_quote": "| $\\sigma_f$ [MPa] | 艉轴承峰值 [N] | 艏轴承峰值 [N] | 寿命 $N_{cycles}$ | 寿命 [h] |",
          "header_unique": true,
          "start_char": 6677
        },
        {
          "table_id": "r9656:table:07",
          "line_start": 239,
          "line_end": 252,
          "rows": 12,
          "cols": 5,
          "header_quote": "| 关键量 | 基准（独立路线/解析） | 相对误差 | 是否 <3% | 说明 |",
          "header_unique": true,
          "start_char": 10221
        },
        {
          "table_id": "r9656:table:08",
          "line_start": 278,
          "line_end": 288,
          "rows": 9,
          "cols": 2,
          "header_quote": "| 产物 | 路径 |",
          "header_unique": true,
          "start_char": 11899
        }
      ],
      "sections": [
        {
          "line_heading": "## ① 案例介绍",
          "quote": "① 案例介绍",
          "unique": true
        },
        {
          "line_heading": "## ② 怎么做（方法 / 流程 / 关键设置）",
          "quote": "② 怎么做（方法 / 流程 / 关键设置）",
          "unique": true
        },
        {
          "line_heading": "## ③ 计算结果",
          "quote": "③ 计算结果",
          "unique": true
        },
        {
          "line_heading": "## ④ 结果图",
          "quote": "④ 结果图",
          "unique": true
        },
        {
          "line_heading": "## ⑤ 注意点（踩坑 / 局限 / 适用范围）",
          "quote": "⑤ 注意点（踩坑 / 局限 / 适用范围）",
          "unique": true
        },
        {
          "line_heading": "## ⑥ 误差判定（关键量 vs 基准，逐项回答「是否<3%」）",
          "quote": "⑥ 误差判定（关键量 vs 基准，逐项回答「是否<3%」）",
          "unique": true
        },
        {
          "line_heading": "## 附：复核方式",
          "quote": "附：复核方式",
          "unique": true
        }
      ],
      "claims": [],
      "claims_empty_reason": "contract objective is register_assets only (classify_report_type=false, no extraction); emitting zero claims is the complete, non-invented result for task_type 01",
      "counts": {
        "assets_total": 27,
        "assets_resolved": 1,
        "assets_metadata_only": 4,
        "assets_unresolved": 22,
        "body_references": 22,
        "distinct_referenced_paths": 15,
        "declared_figures_in_record": 4,
        "figures_with_bytes": 0,
        "tables": 8,
        "table_rows": 77,
        "sections": 7,
        "claims": 0,
        "kind_status_histogram": {
          "report_markdown/resolved": 1,
          "embedded_figure/metadata_only": 4,
          "source_code_reference/unresolved": 7,
          "data_artifact_reference/unresolved": 6,
          "figure_reference/unresolved": 8,
          "directory_reference/unresolved": 1
        }
      },
      "distinct_referenced_paths": [
        "artifacts/ice_shaft_vibration/*.json",
        "artifacts/ice_shaft_vibration/case_results.json",
        "artifacts/ice_shaft_vibration/criteria.json",
        "artifacts/ice_shaft_vibration/fig1_excitation.png",
        "artifacts/ice_shaft_vibration/fig2_shaft_modes.png",
        "artifacts/ice_shaft_vibration/fig3_bearing_load.png",
        "artifacts/ice_shaft_vibration/fig4_fatigue.png",
        "artifacts/ice_shaft_vibration/model_ledger.json",
        "backend/modules/ice_shaft_vibration/",
        "backend/scripts/build_ice_shaft_vibration_report.py",
        "backend/scripts/run_ice_shaft_vibration_case.py",
        "backend/tests/test_ice_shaft_vibration.py",
        "scripts/build_ice_shaft_vibration_report.py",
        "scripts/run_ice_shaft_vibration_case.py",
        "tests/test_ice_shaft_vibration.py"
      ],
      "platform_probes": {
        "/tensor/reports/9656/artifacts": {
          "status": "http_404"
        },
        "/tensor/artifacts?report_id=9656": {
          "status": "http_404"
        }
      },
      "observations": [
        "All 22 body path references point at artifacts/ and backend/ of the producing repository (ship-performance-platform), which is not a checkout in this TensorKnowledge worktree -- hence unresolved here, by design, not a defect.",
        "The report record carries 4 figures by name+caption only (png_base64 empty); image bytes are therefore not hashable from the record.",
        "Locator quotes are exact character slices of the served markdown; the full line is stored alongside as line_quote for human re-checking."
      ],
      "limitations": [
        "Registration only: no claim is extracted, classified, or marked verified.",
        "Artifact existence is asserted by the report text; this package does not confirm the referenced files exist upstream (no cross-repo read).",
        "Uniqueness of a quote is a property of this document only; short path strings that recur are flagged with unique=false and line_occurrences>1."
      ],
      "integrity": {
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "locators_checked": 42,
        "locators_resolved": 42,
        "quote_uniqueness": "6/27 asset quotes occur exactly once in the markdown; 21 recur (flagged unique=false; positional locators stay unambiguous via start_line/char_span). 4 assets are additionally unique at record level.",
        "duplicate_asset_ids": 0
      }
    },
    "asset_manifest.digest.json": {
      "path": "docs/kf/wp-9656-01/asset_manifest.json",
      "sha256": "sha256:3507a6e3b5db5980e36de7ef751843557b293db6ea48f9b3a1d8bddc5674df86",
      "bytes": 33928,
      "asset_count": 27,
      "claims": 0
    }
  },
  "claims": []
}
```
