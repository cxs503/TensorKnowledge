# KF-RESULT wp-8398-01

工序 `wp-8398-01`（task_type=`01-asset-registration`，lane C）｜report_id `8398`｜源哈希 `sha256:e2b867451792017e0af5346b70c7a4eb5f764917490c9ac6fc66c14435da6706`

## ① 本工序做了什么

按契约对报告 8398 做**源资产登记**（不做抽取、不做分类、不标注 verified）：

1. 从平台取回 report_id=8398 的 `markdown` 字段，落盘为字节副本（`runs/wp-8398-01/source_8398.md`，7514 bytes / 4290 chars），本地重算 sha256 与契约声明值比对：**一致**。
2. 逐条登记报告正文与 record 中声明的代码/脚本/文档/工件/图/符号引用，共 **32** 项，每项带可复算定位（字符区间 + 行号 + 逐字引文 + 引文 sha256 + 出现次数）。
3. 逐项做存在性探测并如实记录结论：`declared_only=22，metadata_only=4，resolved=1，unresolved=5`。
4. 产出 `asset_manifest.json`、`kf_result.json`（信封）、`verification.json`（自检）与一张资产清单图。

## ② 怎么做的（步骤 / 工具 / 关键设置）

| 步骤 | 命令 | 说明 |
|---|---|---|
| 取源 | `python3 scripts/kf_wp8398_01_register.py fetch` | GET `/api/v1/tensor/reports/8398`，只读 report_id=8398 一个报告；markdown 原文按 UTF-8 字节落盘 |
| 登记 | `... build` | 声明表驱动扫描；定位器为**在取回字节上实测**的字符区间/行号/逐字引文，不手抄任何数字 |
| 信封 | `... envelope` | `provenance.source_hash` = 本地重算值（非契约抄写） |
| 自检 | `... verify` | 重新联网取一份 markdown，对每条 markdown 定位器复核 slice/字符 sha256/出现次数/行号；6 项 acceptance 逐条机判 |
| 出图 | `... figure` | matplotlib，资产锚点行位 + 类别计数 |

关键设置：仅用标准库（`verify` 用 jsonschema、`figure` 用 matplotlib）；任何定位失败 `SystemExit` 中止，不产出半份 manifest。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-8398-01/asset_manifest.json` | 源身份 + 32 项资产 + 计数 + 空 claims + integrity |
| `docs/kf/wp-8398-01/kf_result.json` | 平台信封：package_id/task_type/report_id/provenance/outputs/claims |
| `docs/kf/wp-8398-01/verification.json` | 6 项 acceptance 自检结果（`all_ok=True`） |
| `docs/kf/wp-8398-01/figures/fig_asset_inventory.png` | 资产锚点行位图 + 类别计数（matplotlib, 150 dpi） |
| `runs/wp-8398-01/source_8398.md` | 源 markdown 字节副本（7514 bytes） |
| `scripts/kf_wp8398_01_register.py` | 本工序全部步骤的可重跑实现 |
| `schemas/asset_manifest_kf.v1.schema.json` | 01 工序 manifest 的通用（非 const 硬编码）schema |

## ④ 证据定位表（claim/字段 → 原文引文片段）

引文均为取回 markdown 的**逐字切片**（`verify` 已复核 slice 与 sha256）。资产集合 = 报告声明物，非知识主张：本工序 claims 为空数组（契约 `classify_report_type=false`）。

| 资产 ID | 类别 | 行 | 原文引文（逐字） | 解析状态 |
|---|---|---|---|---|
| `r8398:source-markdown` | report_markdown | 1 | `# P121W5-N11 成熟化单：DEM 接触物理模块（温度键合 + 润滑耦合 + 力链统计）集成验证与 API 稳定化` | resolved |
| `r8398:mod:contact_physics` | python_package | 21 | `tensordem.contact_physics` | declared_only |
| `r8398:file:bond` | python_module_file | 21 | `bond.py` | declared_only |
| `r8398:file:lubrication` | python_module_file | 21 | `lubrication.py` | declared_only |
| `r8398:file:statistics` | python_module_file | 21 | `statistics.py` | declared_only |
| `r8398:file:march` | python_module_file | 21 | `march.py` | declared_only |
| `r8398:mod:ice_bond_viscoelastic` | upstream_module | 7 | `tensordem.ice_bond_viscoelastic` | declared_only |
| `r8398:func:ice_resistance` | upstream_function | 7 | `tensordem.wet_ice_cohesion.ice_resistance` | declared_only |
| `r8398:mod:ridge_dem` | upstream_module | 8 | `tensordem.ridge_dem` | declared_only |
| `r8398:mod:ice_rubble_microstructure` | upstream_module | 8 | `tensordem.ice_rubble_microstructure` | declared_only |
| `r8398:mod:interface_thermal` | upstream_module | 9 | `tensordem.interface_thermal` | declared_only |
| `r8398:sym:OperatingPoint` | symbol | 11 | `OperatingPoint` | declared_only |
| `r8398:sym:ContactPhysicsMarch` | symbol | 22 | `ContactPhysicsMarch` | declared_only |
| `r8398:sym:standalone_reference` | symbol | 22 | `standalone_reference` | declared_only |
| `r8398:sym:RidgeContactStatistics` | symbol | 72 | `RidgeContactStatistics` | declared_only |
| `r8398:func:within_strength_fit` | symbol | 70 | `within_strength_fit()` | declared_only |
| `r8398:script:freeze_api` | script | 21 | `scripts/freeze_contact_physics_api.py` | declared_only |
| `r8398:script:regression_gate` | script | 24 | `scripts/contact_physics_regression_gate.py` | declared_only |
| `r8398:script:build_doc` | script | 25 | `scripts/build_contact_physics_doc.py` | declared_only |
| `r8398:doc:contact_physics_module` | doc | 25 | `docs/contact_physics_module.md` | declared_only |
| `r8398:example:contact_physics_demo` | example | 25 | `examples/contact_physics_demo.py` | declared_only |
| `r8398:test:integration` | test | 89 | `tests/test_contact_physics_integration.py` | declared_only |
| `r8398:artifact:integration_report` | artifact | 89 | `artifacts/contact_physics/integration_report.json` | unresolved |
| `r8398:artifact:api_baseline` | artifact | 89 | `api_baseline.json` | unresolved |
| `r8398:artifact:regression_gate_json` | artifact | 89 | `regression_gate.json` | unresolved |
| `r8398:artifact:performance_pytest` | artifact | 89 | `performance_pytest.json` | unresolved |
| `r8398:anchor:git_c2e8461e4a50` | provenance_anchor | 21 | `c2e8461e4a50` | declared_only |
| `r8398:suite:pytest_n02_n05_n08` | declared_test_suite | 24 | `9 个 pytest 文件` | unresolved |
| `r8398:figure:01` | figure | 0 | `fig_coupling_history.png` | metadata_only |
| `r8398:figure:02` | figure | 0 | `fig_bond_response.png` | metadata_only |
| `r8398:figure:03` | figure | 0 | `fig_parity.png` | metadata_only |
| `r8398:figure:04` | figure | 0 | `fig_statistics.png` | metadata_only |

源身份字段证据：

| 字段 | 值 | 依据 |
|---|---|---|
| `report_id` | 8398 | `GET /tensor/reports/8398` 返回 id 字段 |
| `sha256(markdown)` | `sha256:e2b867451792017e0af5346b70c7a4eb5f764917490c9ac6fc66c14435da6706` | 本地对字节副本重算，与契约 `sha256:e2b867451792017e0af5346b70c7a4eb5f764917490c9ac6fc66c14435da6706` 一致 |
| `chars` | 4290 | `len(markdown)`，契约声明 4290，一致 |
| `title` | P121W5-N11 DEM 接触物理模块成熟化：温度键合+润滑耦合+力链统计集成验证与 API 稳定化 | record.title（契约声明值 一致） |
| `scenario_key` | ice_navigation | record.scenario_key（契约声明 ice_navigation，一致） |
| 报告自述 git rev | `c2e8461e4a50` | 原文含该串（是）；本工序不打开该 rev |

## ⑤ 注意点与局限

1. **只登记、不验证内容**：本工序不断言任何数值结论正确；`status` 一律不是 verified，verification 由平台门独立重算。manifest 中 `claims` 为空数组是**按契约的完整结果**，不是缺省。
2. **32 项资产中只有 1 项在本工序可真正解析**（源 markdown）；22 为 `declared_only`（仅在本仓之外的存在性探测中可见：外部检出路径 / 本地 import spec / grep / git 对象，均非报告 pin 的 rev，故一律不报字节哈希）、4 为 `metadata_only`（图只有 name/caption）、5 为 `unresolved`：`r8398:artifact:integration_report`、`r8398:artifact:api_baseline`、`r8398:artifact:regression_gate_json`、`r8398:artifact:performance_pytest`、`r8398:suite:pytest_n02_n05_n08`。
3. **上游工件未做字节校验**：报告涉及的求解器/脚本/工件属于上游仓，检出目录 `/root/tp-agent/work/m14461`（rev `fb41e9de`）不是报告 pin 的 `c2e8461e4a50`，故只报“存在”不报哈希；任何一致性主张留待上游 owner。
4. **图是记录元数据**：4 张图的名称/图注来自 `record.figures`（正文 ④ 只写“见附图”、未给文件名）；figure 端点返回载荷 0/4 张，既无图字节可哈希，下游也无法从该端点复现图
5. **`api_baseline.json` / `regression_gate.json` / `performance_pytest.json` 无路径前缀**：原文以裸文件名出现，实际落盘目录需上游仓确认，本工序不猜路径。
6. 报告正文的表格与数字（如 0.0e+00、-8.08%、150 用例）**未登记为 claim**：按契约本工序不做抽取，防越权复述；它们只作为“报告存在这些声明”的事实留在原文。
7. **审计链工件不可取回是这条产线的真实缺口**：报告 ④ 声称的总表/签名基线/回归门/性能样本（`artifacts/contact_physics/*.json`、`api_baseline.json` 等）在本工序两个探测根下都取不到（`artifacts/` 被 `.gitignore` 排除，只有少数文件被强制入库），下游证据审计工序若需要这些字节，须回上游仓运行机取证，否则只能拿到“报告声称有”这一层。

### 误差判定（数值面）

本工序无数值模型输出，可比对量只有源身份量与定位器，逐项列出（判据面而非物理精度面）：

| 关键量 | 基准 | 误差 | 是否 < 3% |
|---|---|---|---|
| markdown sha256 | 契约声明 `sha256:e2b867451792017e0af5346b70c7a4eb5f764917490c9ac6fc66c14435da6706` | 0（逐位相同） | 是（0% < 3%） |
| markdown 字符数 4290 | 契约声明 4290 | 0 | 是（0% < 3%） |
| 定位器可解析率 28/28 | 全部可解析 | 0 | 是（0% < 3%） |

**无物理/实验基准可比的声明**：本工序不产出物理量，故不存在“计算值 vs 实验值”的误差项；报告 8398 自身的数值主张（如 0.0e+00、-8.08%）属上游工序，本工序未复核也未复述。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| `valid_json` | ✓ | asset_manifest.json + kf_result.json parsed |
| `schema_pass` | ✓ | 0 schema error(s) |
| `source_locator_resolvable` | ✓ | 28/28 markdown locators re-resolved on live bytes (char span + verbatim quote + sha256 + line) |
| `source_hash_matches` | ✓ | live=sha256:e2b867451792017e0af5346b70c7a4eb5f764917490c9ac6fc66c14435da6706 manifest=sha256:e2b867451792017e0af5346b70c7a4eb5f764917490c9ac6fc66c14435da6706 contract=sha256:e2b867451792017e0af5346b70c7a4eb5f764917490c9ac6fc66c14435da6706 |
| `no_duplicate_ids` | ✓ | 32 ids, duplicates=[] |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✓ | 0 claims; empty-claims reason stated: True |

`all_ok = True`；无失败项（若有会如实列出，不粉饰）。

## 复跑命令

```bash
cd <worktree>  # TensorKnowledge worktree for m15622
python3 scripts/kf_wp8398_01_register.py all   # fetch+build+envelope+verify+figure+report
```

## KF-RESULT JSON

```json
{
  "package_id": "wp-8398-01",
  "task_type": "01-asset-registration",
  "report_id": "8398",
  "provenance": {
    "source_hash": "sha256:e2b867451792017e0af5346b70c7a4eb5f764917490c9ac6fc66c14435da6706",
    "source_field": "markdown",
    "source_uri": "tensor://reports/8398",
    "producer": "kf-worker/m15622",
    "emitted_at": "2026-11-12T01:34:07.484856+00:00",
    "notes": "source_hash recomputed from the fetched markdown bytes (sha256 over UTF-8), not copied from the contract; registration only, no claim marked verified"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-8398-01",
      "task_type": "01-asset-registration",
      "report_id": "8398",
      "lane": "C",
      "generated_at": "2026-11-12T01:34:07.471458+00:00",
      "producer": "kf-worker/m15622",
      "source": {
        "report_id": "8398",
        "source_uri": "tensor://reports/8398",
        "source_field": "markdown",
        "source_hash": "sha256:e2b867451792017e0af5346b70c7a4eb5f764917490c9ac6fc66c14435da6706",
        "contract_source_hash": "sha256:e2b867451792017e0af5346b70c7a4eb5f764917490c9ac6fc66c14435da6706",
        "hash_match": true,
        "hash_algo": "sha256",
        "chars": 4290,
        "contract_chars": 4290,
        "chars_match_contract": true,
        "bytes": 7514,
        "lines": 90,
        "has_crlf": false,
        "has_trailing_newline": true,
        "line_counting": "1-based; lines = markdown.split(chr(10))",
        "hash_scope": "UTF-8 bytes of the markdown field as served by GET /api/v1/tensor/reports/8398",
        "local_copy": "runs/wp-8398-01/source_8398.md",
        "record_local_copy": "runs/wp-8398-01/record_8398.json",
        "fetched_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/8398",
        "record_fields": {
          "title": "P121W5-N11 DEM 接触物理模块成熟化：温度键合+润滑耦合+力链统计集成验证与 API 稳定化",
          "scenario_key": "ice_navigation",
          "mission_id": 7053,
          "status": "published",
          "created_at": "2026-11-08T11:29:46.020210+00:00",
          "tags": [
            "DEM",
            "contact-physics",
            "lubrication",
            "ice-bond",
            "P121W5-N11",
            "integration",
            "maturation"
          ],
          "figures": 4,
          "contract_title": "P121W5-N11 DEM 接触物理模块成熟化：温度键合+润滑耦合+力链统计集成验证与 API 稳定化",
          "title_matches_contract": true,
          "contract_scenario_key": "ice_navigation",
          "scenario_matches_contract": true,
          "contract_reported_git_rev": "c2e8461e4a50",
          "reported_git_rev_in_markdown": true
        },
        "upstream_probe": {
          "probe_root": "/root/tp-agent/work/m14461",
          "probe_root_exists": true,
          "probe_rev": "fb41e9de"
        }
      },
      "assets": [
        {
          "asset_id": "r8398:source-markdown",
          "asset_class": "report_markdown",
          "label": "report-8398-markdown",
          "token": "document",
          "locator": {
            "source_field": "markdown",
            "method": "document",
            "start_char": 0,
            "end_char": 4290,
            "start_line": 1,
            "end_line": 90,
            "quote": "# P121W5-N11 成熟化单：DEM 接触物理模块（温度键合 + 润滑耦合 + 力链统计）集成验证与 API 稳定化",
            "quote_sha256": "6ab93f2dc7681e0fe0a90762e991c354dee58e1db5d84d199780268ecf733a30",
            "unique": true,
            "occurrences": 1,
            "context": "# P121W5-N11 成熟化单：DEM 接触物理模块（温度键合 + 润滑耦合 + 力链统计）集成验证与 API 稳定化"
          },
          "resolution": {
            "status": "resolved",
            "scope": "platform_api",
            "checks": [
              {
                "check": "GET /tensor/reports/8398",
                "result": "200"
              },
              {
                "check": "sha256(utf8 markdown bytes)",
                "result": "e2b867451792017e0af5346b70c7a4eb5f764917490c9ac6fc66c14435da6706"
              }
            ],
            "reason": "whole markdown field, byte-exact local copy kept in the run dir"
          },
          "note": "quote = first line (heading); the asset itself is the whole document span"
        },
        {
          "asset_id": "r8398:mod:contact_physics",
          "asset_class": "python_package",
          "label": "tensordem.contact_physics",
          "token": "tensordem.contact_physics",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 1063,
            "end_char": 1088,
            "start_line": 21,
            "end_line": 21,
            "quote": "tensordem.contact_physics",
            "quote_sha256": "559b1ec62149e5bb6dba5a76e5e17326b201934a717d927604ad8435e1293ca2",
            "unique": true,
            "occurrences": 1,
            "context": "1. **API 稳定化（判据 b）**：新增 `tensordem.contact_physics` 子包（`bond.py` / `lubrication.py` / `statistics.py` / `march.py`），每个能力一个对象一个方法签名；上游三个节点模块**零改动**，其公开签名与文件哈希被 `scripts/freeze_contact_physics_api.py` 冻结为基线（基线 rev `c2e8461e4a50`），逐模块字节比对 → 签名变更 0 个。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "upstream python package",
            "checks": [
              {
                "check": "python_import_spec",
                "result": "present",
                "module": "tensordem.contact_physics",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/contact_physics/__init__.py",
                "origin_scope_note": "resolved through PYTHONPATH pointing at a foreign tenant worktree; this is a presence signal, not evidence about the report's pinned rev"
              },
              {
                "check": "origin_inside_foreign_checkout",
                "result": "yes",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/contact_physics/__init__.py"
              }
            ],
            "reason": "module resolves on the local python path via a foreign checkout; the report's pinned rev is not opened, so no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:file:bond",
          "asset_class": "python_module_file",
          "label": "bond.py",
          "token": "bond.py",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 1094,
            "end_char": 1101,
            "start_line": 21,
            "end_line": 21,
            "quote": "bond.py",
            "quote_sha256": "747e86a2730aeaf59b1c14ceb92abdedaa8d7fcff0bd664f7ccd84e632ee45cf",
            "unique": true,
            "occurrences": 1,
            "context": "1. **API 稳定化（判据 b）**：新增 `tensordem.contact_physics` 子包（`bond.py` / `lubrication.py` / `statistics.py` / `march.py`），每个能力一个对象一个方法签名；上游三个节点模块**零改动**，其公开签名与文件哈希被 `scripts/freeze_contact_physics_api.py` 冻结为基线（基线 rev `c2e8461e4a50`），逐模块字节比对 → 签名变更 0 个。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "upstream python package",
            "checks": [
              {
                "check": "python_import_spec",
                "result": "present",
                "module": "tensordem.contact_physics.bond",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/contact_physics/bond.py",
                "origin_scope_note": "resolved through PYTHONPATH pointing at a foreign tenant worktree; this is a presence signal, not evidence about the report's pinned rev"
              },
              {
                "check": "origin_inside_foreign_checkout",
                "result": "yes",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/contact_physics/bond.py"
              }
            ],
            "reason": "module resolves on the local python path via a foreign checkout; the report's pinned rev is not opened, so no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:file:lubrication",
          "asset_class": "python_module_file",
          "label": "lubrication.py",
          "token": "lubrication.py",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 1106,
            "end_char": 1120,
            "start_line": 21,
            "end_line": 21,
            "quote": "lubrication.py",
            "quote_sha256": "ec705f6f74c388a6379d48f0d9237669aa9259266f0335aa8e078d91d9ef28ca",
            "unique": true,
            "occurrences": 1,
            "context": "1. **API 稳定化（判据 b）**：新增 `tensordem.contact_physics` 子包（`bond.py` / `lubrication.py` / `statistics.py` / `march.py`），每个能力一个对象一个方法签名；上游三个节点模块**零改动**，其公开签名与文件哈希被 `scripts/freeze_contact_physics_api.py` 冻结为基线（基线 rev `c2e8461e4a50`），逐模块字节比对 → 签名变更 0 个。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "upstream python package",
            "checks": [
              {
                "check": "python_import_spec",
                "result": "present",
                "module": "tensordem.contact_physics.lubrication",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/contact_physics/lubrication.py",
                "origin_scope_note": "resolved through PYTHONPATH pointing at a foreign tenant worktree; this is a presence signal, not evidence about the report's pinned rev"
              },
              {
                "check": "origin_inside_foreign_checkout",
                "result": "yes",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/contact_physics/lubrication.py"
              }
            ],
            "reason": "module resolves on the local python path via a foreign checkout; the report's pinned rev is not opened, so no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:file:statistics",
          "asset_class": "python_module_file",
          "label": "statistics.py",
          "token": "statistics.py",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 1125,
            "end_char": 1138,
            "start_line": 21,
            "end_line": 21,
            "quote": "statistics.py",
            "quote_sha256": "a7db2722825dc26c364446fddcc0ffd9512a190558cf2b56cdc094746606e0b9",
            "unique": true,
            "occurrences": 1,
            "context": "1. **API 稳定化（判据 b）**：新增 `tensordem.contact_physics` 子包（`bond.py` / `lubrication.py` / `statistics.py` / `march.py`），每个能力一个对象一个方法签名；上游三个节点模块**零改动**，其公开签名与文件哈希被 `scripts/freeze_contact_physics_api.py` 冻结为基线（基线 rev `c2e8461e4a50`），逐模块字节比对 → 签名变更 0 个。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "upstream python package",
            "checks": [
              {
                "check": "python_import_spec",
                "result": "present",
                "module": "tensordem.contact_physics.statistics",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/contact_physics/statistics.py",
                "origin_scope_note": "resolved through PYTHONPATH pointing at a foreign tenant worktree; this is a presence signal, not evidence about the report's pinned rev"
              },
              {
                "check": "origin_inside_foreign_checkout",
                "result": "yes",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/contact_physics/statistics.py"
              }
            ],
            "reason": "module resolves on the local python path via a foreign checkout; the report's pinned rev is not opened, so no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:file:march",
          "asset_class": "python_module_file",
          "label": "march.py",
          "token": "march.py",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 1143,
            "end_char": 1151,
            "start_line": 21,
            "end_line": 21,
            "quote": "march.py",
            "quote_sha256": "730d3a7021489a47240a2f07e064dcc2565d141765281186f80635d0964a5292",
            "unique": true,
            "occurrences": 1,
            "context": "1. **API 稳定化（判据 b）**：新增 `tensordem.contact_physics` 子包（`bond.py` / `lubrication.py` / `statistics.py` / `march.py`），每个能力一个对象一个方法签名；上游三个节点模块**零改动**，其公开签名与文件哈希被 `scripts/freeze_contact_physics_api.py` 冻结为基线（基线 rev `c2e8461e4a50`），逐模块字节比对 → 签名变更 0 个。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "upstream python package",
            "checks": [
              {
                "check": "python_import_spec",
                "result": "present",
                "module": "tensordem.contact_physics.march",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/contact_physics/march.py",
                "origin_scope_note": "resolved through PYTHONPATH pointing at a foreign tenant worktree; this is a presence signal, not evidence about the report's pinned rev"
              },
              {
                "check": "origin_inside_foreign_checkout",
                "result": "yes",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/contact_physics/march.py"
              }
            ],
            "reason": "module resolves on the local python path via a foreign checkout; the report's pinned rev is not opened, so no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:mod:ice_bond_viscoelastic",
          "asset_class": "upstream_module",
          "label": "tensordem.ice_bond_viscoelastic",
          "token": "tensordem.ice_bond_viscoelastic",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 169,
            "end_char": 200,
            "start_line": 7,
            "end_line": 7,
            "quote": "tensordem.ice_bond_viscoelastic",
            "quote_sha256": "0e0a6ab181e13bd07605805703289ef67c8d5bec8cc5ea83b90f225b214f120c",
            "unique": true,
            "occurrences": 1,
            "context": "* **P121W5-N02｜温度相关键合模型**：`tensordem.ice_bond_viscoelastic` 的 Maxwell-Wiechert（Prony 级数）键合律 + Kachanov 蠕变损伤钟，温度依赖取 `tensordem.wet_ice_cohesion.ice_resistance` 的 Timco & Weeks (2010) 卤水体积/强度关系。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "upstream python package",
            "checks": [
              {
                "check": "python_import_spec",
                "result": "present",
                "module": "tensordem.ice_bond_viscoelastic",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/ice_bond_viscoelastic.py",
                "origin_scope_note": "resolved through PYTHONPATH pointing at a foreign tenant worktree; this is a presence signal, not evidence about the report's pinned rev"
              },
              {
                "check": "origin_inside_foreign_checkout",
                "result": "yes",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/ice_bond_viscoelastic.py"
              }
            ],
            "reason": "module resolves on the local python path via a foreign checkout; the report's pinned rev is not opened, so no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:func:ice_resistance",
          "asset_class": "upstream_function",
          "label": "tensordem.wet_ice_cohesion.ice_resistance",
          "token": "tensordem.wet_ice_cohesion.ice_resistance",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 258,
            "end_char": 299,
            "start_line": 7,
            "end_line": 7,
            "quote": "tensordem.wet_ice_cohesion.ice_resistance",
            "quote_sha256": "062719dd6f09bf5a01463c3e62e24f15b1a2f9864b27dc52544c5401316e0bc0",
            "unique": true,
            "occurrences": 1,
            "context": "* **P121W5-N02｜温度相关键合模型**：`tensordem.ice_bond_viscoelastic` 的 Maxwell-Wiechert（Prony 级数）键合律 + Kachanov 蠕变损伤钟，温度依赖取 `tensordem.wet_ice_cohesion.ice_resistance` 的 Timco & Weeks (2010) 卤水体积/强度关系。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "upstream python package",
            "checks": [
              {
                "check": "python_import_spec",
                "result": "present",
                "module": "tensordem.wet_ice_cohesion",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/wet_ice_cohesion/__init__.py",
                "origin_scope_note": "resolved through PYTHONPATH pointing at a foreign tenant worktree; this is a presence signal, not evidence about the report's pinned rev"
              },
              {
                "check": "origin_inside_foreign_checkout",
                "result": "yes",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/wet_ice_cohesion/__init__.py"
              }
            ],
            "reason": "module resolves on the local python path via a foreign checkout; the report's pinned rev is not opened, so no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:mod:ridge_dem",
          "asset_class": "upstream_module",
          "label": "tensordem.ridge_dem",
          "token": "tensordem.ridge_dem",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 365,
            "end_char": 384,
            "start_line": 8,
            "end_line": 8,
            "quote": "tensordem.ridge_dem",
            "quote_sha256": "cf136ce42d1062432edd0854ded9d7037c55774de51fa1a22a02418fe60e736e",
            "unique": true,
            "occurrences": 1,
            "context": "* **P121W5-N05｜冰脊形态与接触网络统计**：`tensordem.ridge_dem` 的确定性冻结键合三角点阵冰脊 + `tensordem.ice_rubble_microstructure` 的配位数/力链分布估计。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "upstream python package",
            "checks": [
              {
                "check": "python_import_spec",
                "result": "present",
                "module": "tensordem.ridge_dem",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/ridge_dem.py",
                "origin_scope_note": "resolved through PYTHONPATH pointing at a foreign tenant worktree; this is a presence signal, not evidence about the report's pinned rev"
              },
              {
                "check": "origin_inside_foreign_checkout",
                "result": "yes",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/ridge_dem.py"
              }
            ],
            "reason": "module resolves on the local python path via a foreign checkout; the report's pinned rev is not opened, so no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:mod:ice_rubble_microstructure",
          "asset_class": "upstream_module",
          "label": "tensordem.ice_rubble_microstructure",
          "token": "tensordem.ice_rubble_microstructure",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 404,
            "end_char": 439,
            "start_line": 8,
            "end_line": 8,
            "quote": "tensordem.ice_rubble_microstructure",
            "quote_sha256": "763c048ac97899e4b272b877daeedf4531017148bab7b6cbdc41c8584c1be71f",
            "unique": true,
            "occurrences": 1,
            "context": "* **P121W5-N05｜冰脊形态与接触网络统计**：`tensordem.ridge_dem` 的确定性冻结键合三角点阵冰脊 + `tensordem.ice_rubble_microstructure` 的配位数/力链分布估计。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "upstream python package",
            "checks": [
              {
                "check": "python_import_spec",
                "result": "present",
                "module": "tensordem.ice_rubble_microstructure",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/ice_rubble_microstructure.py",
                "origin_scope_note": "resolved through PYTHONPATH pointing at a foreign tenant worktree; this is a presence signal, not evidence about the report's pinned rev"
              },
              {
                "check": "origin_inside_foreign_checkout",
                "result": "yes",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/ice_rubble_microstructure.py"
              }
            ],
            "reason": "module resolves on the local python path via a foreign checkout; the report's pinned rev is not opened, so no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:mod:interface_thermal",
          "asset_class": "upstream_module",
          "label": "tensordem.interface_thermal",
          "token": "tensordem.interface_thermal",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 482,
            "end_char": 509,
            "start_line": 9,
            "end_line": 9,
            "quote": "tensordem.interface_thermal",
            "quote_sha256": "d3873ae54d506776212c01096f6c50a3511b38189ad275a8de89ced8977c77b9",
            "unique": true,
            "occurrences": 1,
            "context": "* **P121W5-N08｜润滑-接触双向耦合**：`tensordem.interface_thermal` 的熔化分数摩擦律 mu(T)、Blok 热分配、Stefan 潜热开关与 Newton 求解的耦合推进器。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "upstream python package",
            "checks": [
              {
                "check": "python_import_spec",
                "result": "present",
                "module": "tensordem.interface_thermal",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/interface_thermal/__init__.py",
                "origin_scope_note": "resolved through PYTHONPATH pointing at a foreign tenant worktree; this is a presence signal, not evidence about the report's pinned rev"
              },
              {
                "check": "origin_inside_foreign_checkout",
                "result": "yes",
                "origin": "/root/tp-agent/work/m14461/src/tensordem/interface_thermal/__init__.py"
              }
            ],
            "reason": "module resolves on the local python path via a foreign checkout; the report's pinned rev is not opened, so no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:sym:OperatingPoint",
          "asset_class": "symbol",
          "label": "OperatingPoint",
          "token": "OperatingPoint",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 572,
            "end_char": 586,
            "start_line": 11,
            "end_line": 11,
            "quote": "OperatingPoint",
            "quote_sha256": "b134dcdd05e33d268fdd5ce4569bf7c92c9e03d8b1ae391144d00883ed750bbe",
            "unique": true,
            "occurrences": 1,
            "context": "共享工况（`OperatingPoint`）：滑移接触冰-钢，法向力 5e+04 N，名义接触压力 4.69e+08 Pa，冷态摩擦系数 mu_cold = 0.1；键合束 64 根，参考力 F_ref = 1000 N，损伤时间 t_ref = 60 s，Kachanov 指数 m = 3，盐度 5 ppt。三个物理区间："
          },
          "resolution": {
            "status": "declared_only",
            "scope": "foreign checkout grep",
            "checks": [
              {
                "check": "foreign_grep",
                "result": "present",
                "pattern": "OperatingPoint",
                "files": [
                  "examples/contact_physics_demo.py",
                  "scripts/post_contact_physics_report.py",
                  "src/tensordem/contact_physics/__init__.py"
                ],
                "authoritative": false
              }
            ],
            "reason": "probe performed in a foreign checkout (/root/tp-agent/work/m14461) that is neither this repo nor the rev pinned by the report; existence only, no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:sym:ContactPhysicsMarch",
          "asset_class": "symbol",
          "label": "ContactPhysicsMarch",
          "token": "ContactPhysicsMarch",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 1305,
            "end_char": 1324,
            "start_line": 22,
            "end_line": 22,
            "quote": "ContactPhysicsMarch",
            "quote_sha256": "dcd2c4245c295192b080242934cfefed6629ad9ba9c7b87517e5e56e6696dc18",
            "unique": true,
            "occurrences": 1,
            "context": "2. **集成测试（判据 a）**：`ContactPhysicsMarch` 在一个循环里按固定顺序推进 N08 → N02（用 N08 给出的界面温度）→ N05（统计采样）。测试里另写一份**只用库函数**的组合驱动（`standalone_reference`）作为参照，逐量比对 20 个历史序列。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "foreign checkout grep",
            "checks": [
              {
                "check": "foreign_grep",
                "result": "present",
                "pattern": "ContactPhysicsMarch",
                "files": [
                  "benchmarks/contact_physics_integration.py",
                  "examples/contact_physics_demo.py",
                  "scripts/post_contact_physics_report.py"
                ],
                "authoritative": false
              }
            ],
            "reason": "probe performed in a foreign checkout (/root/tp-agent/work/m14461) that is neither this repo nor the rev pinned by the report; existence only, no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:sym:standalone_reference",
          "asset_class": "symbol",
          "label": "standalone_reference",
          "token": "standalone_reference",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 1399,
            "end_char": 1419,
            "start_line": 22,
            "end_line": 22,
            "quote": "standalone_reference",
            "quote_sha256": "d6a06a2a0e2536066b2a643ad4b31dae9fe9c468a118e3a549f6b0c6ed770b0c",
            "unique": true,
            "occurrences": 1,
            "context": "2. **集成测试（判据 a）**：`ContactPhysicsMarch` 在一个循环里按固定顺序推进 N08 → N02（用 N08 给出的界面温度）→ N05（统计采样）。测试里另写一份**只用库函数**的组合驱动（`standalone_reference`）作为参照，逐量比对 20 个历史序列。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "foreign checkout grep",
            "checks": [
              {
                "check": "foreign_grep",
                "result": "present",
                "pattern": "standalone_reference",
                "files": [
                  "benchmarks/contact_physics_integration.py",
                  "scripts/post_contact_physics_report.py",
                  "tests/test_contact_physics_integration.py"
                ],
                "authoritative": false
              }
            ],
            "reason": "probe performed in a foreign checkout (/root/tp-agent/work/m14461) that is neither this repo nor the rev pinned by the report; existence only, no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:sym:RidgeContactStatistics",
          "asset_class": "symbol",
          "label": "RidgeContactStatistics",
          "token": "RidgeContactStatistics",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 3423,
            "end_char": 3445,
            "start_line": 72,
            "end_line": 72,
            "quote": "RidgeContactStatistics",
            "quote_sha256": "d9f7869eada00adbbb21422359a1987ecb2c7d8f40ae4d5d027d5f7c6ab3992a",
            "unique": true,
            "occurrences": 1,
            "context": "5. **统计是单次实现**：`RidgeContactStatistics` 采样一条给定种子点阵，不是脊龙骨折算分布；多实现集合是后续项。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "foreign checkout grep",
            "checks": [
              {
                "check": "foreign_grep",
                "result": "present",
                "pattern": "RidgeContactStatistics",
                "files": [
                  "benchmarks/contact_physics_integration.py",
                  "examples/contact_physics_demo.py",
                  "scripts/post_contact_physics_report.py"
                ],
                "authoritative": false
              }
            ],
            "reason": "probe performed in a foreign checkout (/root/tp-agent/work/m14461) that is neither this repo nor the rev pinned by the report; existence only, no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:func:within_strength_fit",
          "asset_class": "symbol",
          "label": "within_strength_fit()",
          "token": "within_strength_fit()",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 3344,
            "end_char": 3365,
            "start_line": 70,
            "end_line": 70,
            "quote": "within_strength_fit()",
            "quote_sha256": "94057449d55e82d7e6243605f8b55917f9bd9b626c71720e3ca781d85c8f9a60",
            "unique": true,
            "occurrences": 1,
            "context": "3. **T ≥ 0 处 strength_factor = 0 是极限不是拟合**：熔化界面没有固相键合；卤水体积关系在 5 ppt 下约 -0.72 degC 已触及 0.29 孔隙极限而返回值 0，-2 degC 以上已属拟合带外（`within_strength_fit()` 显式报告）。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "foreign checkout grep",
            "checks": [
              {
                "check": "foreign_grep",
                "result": "present",
                "pattern": "within_strength_fit",
                "files": [
                  "scripts/post_contact_physics_report.py",
                  "src/tensordem/contact_physics/bond.py",
                  "tests/test_contact_physics_integration.py"
                ],
                "authoritative": false
              }
            ],
            "reason": "probe performed in a foreign checkout (/root/tp-agent/work/m14461) that is neither this repo nor the rev pinned by the report; existence only, no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:script:freeze_api",
          "asset_class": "script",
          "label": "scripts/freeze_contact_physics_api.py",
          "token": "scripts/freeze_contact_physics_api.py",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 1198,
            "end_char": 1235,
            "start_line": 21,
            "end_line": 21,
            "quote": "scripts/freeze_contact_physics_api.py",
            "quote_sha256": "1b35d3915a405e9f8f8c5de859f3db3983c4f8409c04be44a29197eb7fc305d6",
            "unique": true,
            "occurrences": 1,
            "context": "1. **API 稳定化（判据 b）**：新增 `tensordem.contact_physics` 子包（`bond.py` / `lubrication.py` / `statistics.py` / `march.py`），每个能力一个对象一个方法签名；上游三个节点模块**零改动**，其公开签名与文件哈希被 `scripts/freeze_contact_physics_api.py` 冻结为基线（基线 rev `c2e8461e4a50`），逐模块字节比对 → 签名变更 0 个。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "foreign checkout",
            "checks": [
              {
                "check": "tensorknowledge_worktree_path",
                "result": "absent",
                "path": "scripts/freeze_contact_physics_api.py"
              },
              {
                "check": "foreign_checkout_path",
                "result": "present",
                "path": "/root/tp-agent/work/m14461/scripts/freeze_contact_physics_api.py",
                "authoritative": false
              }
            ],
            "reason": "probe performed in a foreign checkout (/root/tp-agent/work/m14461) that is neither this repo nor the rev pinned by the report; existence only, no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:script:regression_gate",
          "asset_class": "script",
          "label": "scripts/contact_physics_regression_gate.py",
          "token": "scripts/contact_physics_regression_gate.py",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 1611,
            "end_char": 1653,
            "start_line": 24,
            "end_line": 24,
            "quote": "scripts/contact_physics_regression_gate.py",
            "quote_sha256": "6ece26350db143c1d78eb00282693c07721357ab4f1dbc53a5028810d0e75f4f",
            "unique": true,
            "occurrences": 1,
            "context": "4. **回归门（判据 d）**：N02/N05/N08 的 9 个 pytest 文件分节点独立进程执行，`scripts/contact_physics_regression_gate.py` 落盘。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "foreign checkout",
            "checks": [
              {
                "check": "tensorknowledge_worktree_path",
                "result": "absent",
                "path": "scripts/contact_physics_regression_gate.py"
              },
              {
                "check": "foreign_checkout_path",
                "result": "present",
                "path": "/root/tp-agent/work/m14461/scripts/contact_physics_regression_gate.py",
                "authoritative": false
              }
            ],
            "reason": "probe performed in a foreign checkout (/root/tp-agent/work/m14461) that is neither this repo nor the rev pinned by the report; existence only, no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:script:build_doc",
          "asset_class": "script",
          "label": "scripts/build_contact_physics_doc.py",
          "token": "scripts/build_contact_physics_doc.py",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 1774,
            "end_char": 1810,
            "start_line": 25,
            "end_line": 25,
            "quote": "scripts/build_contact_physics_doc.py",
            "quote_sha256": "fd8f30216eafdc6f27c66172ab8b8a1843f48e9e61ceb16a21a6bbb242016ab5",
            "unique": true,
            "occurrences": 1,
            "context": "5. **文档（判据 e）**：`docs/contact_physics_module.md` 覆盖全部 6 个公开 API；`examples/contact_physics_demo.py` 可独立运行；文档中的验收表由 `scripts/build_contact_physics_doc.py` 从工件程序化注入，杜绝手抄漂移。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "foreign checkout",
            "checks": [
              {
                "check": "tensorknowledge_worktree_path",
                "result": "absent",
                "path": "scripts/build_contact_physics_doc.py"
              },
              {
                "check": "foreign_checkout_path",
                "result": "present",
                "path": "/root/tp-agent/work/m14461/scripts/build_contact_physics_doc.py",
                "authoritative": false
              }
            ],
            "reason": "probe performed in a foreign checkout (/root/tp-agent/work/m14461) that is neither this repo nor the rev pinned by the report; existence only, no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:doc:contact_physics_module",
          "asset_class": "doc",
          "label": "docs/contact_physics_module.md",
          "token": "docs/contact_physics_module.md",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 1676,
            "end_char": 1706,
            "start_line": 25,
            "end_line": 25,
            "quote": "docs/contact_physics_module.md",
            "quote_sha256": "8a62761e6b564c9fcfed897ac87c550a415fdf9881b0cacf2694897be3e5f683",
            "unique": false,
            "occurrences": 2,
            "context": "5. **文档（判据 e）**：`docs/contact_physics_module.md` 覆盖全部 6 个公开 API；`examples/contact_physics_demo.py` 可独立运行；文档中的验收表由 `scripts/build_contact_physics_doc.py` 从工件程序化注入，杜绝手抄漂移。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "foreign checkout",
            "checks": [
              {
                "check": "tensorknowledge_worktree_path",
                "result": "absent",
                "path": "docs/contact_physics_module.md"
              },
              {
                "check": "foreign_checkout_path",
                "result": "present",
                "path": "/root/tp-agent/work/m14461/docs/contact_physics_module.md",
                "authoritative": false
              }
            ],
            "reason": "probe performed in a foreign checkout (/root/tp-agent/work/m14461) that is neither this repo nor the rev pinned by the report; existence only, no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:example:contact_physics_demo",
          "asset_class": "example",
          "label": "examples/contact_physics_demo.py",
          "token": "examples/contact_physics_demo.py",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 1724,
            "end_char": 1756,
            "start_line": 25,
            "end_line": 25,
            "quote": "examples/contact_physics_demo.py",
            "quote_sha256": "82cd9c4efe3e5f8fbf7043b692852d8318760428b65b799a29a039dfb3ba6f53",
            "unique": true,
            "occurrences": 1,
            "context": "5. **文档（判据 e）**：`docs/contact_physics_module.md` 覆盖全部 6 个公开 API；`examples/contact_physics_demo.py` 可独立运行；文档中的验收表由 `scripts/build_contact_physics_doc.py` 从工件程序化注入，杜绝手抄漂移。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "foreign checkout",
            "checks": [
              {
                "check": "tensorknowledge_worktree_path",
                "result": "absent",
                "path": "examples/contact_physics_demo.py"
              },
              {
                "check": "foreign_checkout_path",
                "result": "present",
                "path": "/root/tp-agent/work/m14461/examples/contact_physics_demo.py",
                "authoritative": false
              }
            ],
            "reason": "probe performed in a foreign checkout (/root/tp-agent/work/m14461) that is neither this repo nor the rev pinned by the report; existence only, no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:test:integration",
          "asset_class": "test",
          "label": "tests/test_contact_physics_integration.py",
          "token": "tests/test_contact_physics_integration.py",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 4180,
            "end_char": 4221,
            "start_line": 89,
            "end_line": 89,
            "quote": "tests/test_contact_physics_integration.py",
            "quote_sha256": "9aa4bcc8c671285daf4b2059bc0445900fb4704324e8ed4e7673a5a79780d161",
            "unique": true,
            "occurrences": 1,
            "context": "审计链：`artifacts/contact_physics/integration_report.json`（总表）、`api_baseline.json`（签名基线）、`regression_gate.json`（回归门）、`performance_pytest.json`（性能原始样本）、`docs/contact_physics_module.md`（文档）、`tests/test_contact_physics_integration.py`（判据可执行形式）。生成时间 2026-11-08T11:24:36.627023+00:00，git `c2e8461e4a50`。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "foreign checkout",
            "checks": [
              {
                "check": "tensorknowledge_worktree_path",
                "result": "absent",
                "path": "tests/test_contact_physics_integration.py"
              },
              {
                "check": "foreign_checkout_path",
                "result": "present",
                "path": "/root/tp-agent/work/m14461/tests/test_contact_physics_integration.py",
                "authoritative": false
              }
            ],
            "reason": "probe performed in a foreign checkout (/root/tp-agent/work/m14461) that is neither this repo nor the rev pinned by the report; existence only, no byte hash is claimed"
          }
        },
        {
          "asset_id": "r8398:artifact:integration_report",
          "asset_class": "artifact",
          "label": "artifacts/contact_physics/integration_report.json",
          "token": "artifacts/contact_physics/integration_report.json",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 3999,
            "end_char": 4048,
            "start_line": 89,
            "end_line": 89,
            "quote": "artifacts/contact_physics/integration_report.json",
            "quote_sha256": "c64d56a7892c4635be394875769fd762d8e41944d4a5a9e83221961ec3f86c1f",
            "unique": true,
            "occurrences": 1,
            "context": "审计链：`artifacts/contact_physics/integration_report.json`（总表）、`api_baseline.json`（签名基线）、`regression_gate.json`（回归门）、`performance_pytest.json`（性能原始样本）、`docs/contact_physics_module.md`（文档）、`tests/test_contact_physics_integration.py`（判据可执行形式）。生成时间 2026-11-08T11:24:36.627023+00:00，git `c2e8461e4a50`。"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "both probe roots",
            "checks": [
              {
                "check": "tensorknowledge_worktree_path",
                "result": "absent",
                "path": "artifacts/contact_physics/integration_report.json"
              },
              {
                "check": "foreign_checkout_path",
                "result": "absent",
                "path": "/root/tp-agent/work/m14461/artifacts/contact_physics/integration_report.json",
                "authoritative": false
              }
            ],
            "reason": "path found under neither probe root"
          }
        },
        {
          "asset_id": "r8398:artifact:api_baseline",
          "asset_class": "artifact",
          "label": "api_baseline.json",
          "token": "api_baseline.json",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 4055,
            "end_char": 4072,
            "start_line": 89,
            "end_line": 89,
            "quote": "api_baseline.json",
            "quote_sha256": "7b0e37b7a4515f1e8de5161db3aa06752a542f4f27368f42c7ad04198d1fdcca",
            "unique": true,
            "occurrences": 1,
            "context": "审计链：`artifacts/contact_physics/integration_report.json`（总表）、`api_baseline.json`（签名基线）、`regression_gate.json`（回归门）、`performance_pytest.json`（性能原始样本）、`docs/contact_physics_module.md`（文档）、`tests/test_contact_physics_integration.py`（判据可执行形式）。生成时间 2026-11-08T11:24:36.627023+00:00，git `c2e8461e4a50`。"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "foreign checkout glob",
            "checks": [
              {
                "check": "foreign_rglob_name",
                "result": "absent",
                "name": "api_baseline.json",
                "files": [],
                "authoritative": false
              }
            ],
            "reason": "filename not found in the probe checkout"
          }
        },
        {
          "asset_id": "r8398:artifact:regression_gate_json",
          "asset_class": "artifact",
          "label": "regression_gate.json",
          "token": "regression_gate.json",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 4081,
            "end_char": 4101,
            "start_line": 89,
            "end_line": 89,
            "quote": "regression_gate.json",
            "quote_sha256": "4659dda8f3b5c2e64e3e5428535916b65a16f4c550744199c488eed303eb2658",
            "unique": true,
            "occurrences": 1,
            "context": "审计链：`artifacts/contact_physics/integration_report.json`（总表）、`api_baseline.json`（签名基线）、`regression_gate.json`（回归门）、`performance_pytest.json`（性能原始样本）、`docs/contact_physics_module.md`（文档）、`tests/test_contact_physics_integration.py`（判据可执行形式）。生成时间 2026-11-08T11:24:36.627023+00:00，git `c2e8461e4a50`。"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "foreign checkout glob",
            "checks": [
              {
                "check": "foreign_rglob_name",
                "result": "absent",
                "name": "regression_gate.json",
                "files": [],
                "authoritative": false
              }
            ],
            "reason": "filename not found in the probe checkout"
          }
        },
        {
          "asset_id": "r8398:artifact:performance_pytest",
          "asset_class": "artifact",
          "label": "performance_pytest.json",
          "token": "performance_pytest.json",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 4109,
            "end_char": 4132,
            "start_line": 89,
            "end_line": 89,
            "quote": "performance_pytest.json",
            "quote_sha256": "dff86de9bc7910a8f3b3b87a657705611f0221bd47309459712d2fdfcf4028e1",
            "unique": true,
            "occurrences": 1,
            "context": "审计链：`artifacts/contact_physics/integration_report.json`（总表）、`api_baseline.json`（签名基线）、`regression_gate.json`（回归门）、`performance_pytest.json`（性能原始样本）、`docs/contact_physics_module.md`（文档）、`tests/test_contact_physics_integration.py`（判据可执行形式）。生成时间 2026-11-08T11:24:36.627023+00:00，git `c2e8461e4a50`。"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "foreign checkout glob",
            "checks": [
              {
                "check": "foreign_rglob_name",
                "result": "absent",
                "name": "performance_pytest.json",
                "files": [],
                "authoritative": false
              }
            ],
            "reason": "filename not found in the probe checkout"
          }
        },
        {
          "asset_id": "r8398:anchor:git_c2e8461e4a50",
          "asset_class": "provenance_anchor",
          "label": "c2e8461e4a50",
          "token": "c2e8461e4a50",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 1251,
            "end_char": 1263,
            "start_line": 21,
            "end_line": 21,
            "quote": "c2e8461e4a50",
            "quote_sha256": "8616efb2ce503b674bff4be1e895f99fe7f9b2e38c87f0d2f45d438e09c0b64e",
            "unique": false,
            "occurrences": 2,
            "context": "1. **API 稳定化（判据 b）**：新增 `tensordem.contact_physics` 子包（`bond.py` / `lubrication.py` / `statistics.py` / `march.py`），每个能力一个对象一个方法签名；上游三个节点模块**零改动**，其公开签名与文件哈希被 `scripts/freeze_contact_physics_api.py` 冻结为基线（基线 rev `c2e8461e4a50`），逐模块字节比对 → 签名变更 0 个。"
          },
          "resolution": {
            "status": "declared_only",
            "scope": "foreign checkout git object",
            "checks": [
              {
                "check": "foreign_git_rev",
                "result": "present",
                "rev": "c2e8461e4a50",
                "authoritative": false
              }
            ],
            "reason": "the rev named in the report exists as an object in the probe checkout, which says nothing about the report's artefacts"
          }
        },
        {
          "asset_id": "r8398:suite:pytest_n02_n05_n08",
          "asset_class": "declared_test_suite",
          "label": "9 个 pytest 文件",
          "token": "9 个 pytest 文件",
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "start_char": 1587,
            "end_char": 1600,
            "start_line": 24,
            "end_line": 24,
            "quote": "9 个 pytest 文件",
            "quote_sha256": "32653f6ae357d7d937da9aa571e00b1fa12426d84f8fbd07e159f66993f30b3e",
            "unique": true,
            "occurrences": 1,
            "context": "4. **回归门（判据 d）**：N02/N05/N08 的 9 个 pytest 文件分节点独立进程执行，`scripts/contact_physics_regression_gate.py` 落盘。"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "not probed",
            "checks": [
              {
                "check": "probe_target",
                "result": "not_derivable",
                "detail": "the report declares a count/plural without names"
              }
            ],
            "reason": "declared as an unnamed plural ('9 pytest 文件'); the report gives no filenames, so nothing is locatable and nothing is invented"
          }
        },
        {
          "asset_id": "r8398:figure:01",
          "asset_class": "figure",
          "label": "fig_coupling_history.png",
          "token": "fig_coupling_history.png",
          "locator": {
            "source_field": "record",
            "method": "record_pointer",
            "start_char": 0,
            "end_char": 1,
            "start_line": 1,
            "end_line": 1,
            "quote": "fig_coupling_history.png",
            "quote_sha256": "496df77d945eb801b9cf4fc0cad5f343fb92076e90282a80902cf31487a68f5b",
            "unique": true,
            "occurrences": 1,
            "context": "figures[0].name"
          },
          "resolution": {
            "status": "metadata_only",
            "scope": "platform_api",
            "checks": [
              {
                "check": "GET /tensor/reports/8398/figures/fig_coupling_history.png",
                "result": "http_404",
                "bytes": 29
              }
            ],
            "reason": "record exposes name/caption only; no figure bytes were returned, so no hash is claimed"
          },
          "note": "Interface temperature, friction coefficient and melt-film thickness of the three integrated regimes (N08 two-way coupling driven inside one contact-physics march)."
        },
        {
          "asset_id": "r8398:figure:02",
          "asset_class": "figure",
          "label": "fig_bond_response.png",
          "token": "fig_bond_response.png",
          "locator": {
            "source_field": "record",
            "method": "record_pointer",
            "start_char": 0,
            "end_char": 1,
            "start_line": 1,
            "end_line": 1,
            "quote": "fig_bond_response.png",
            "quote_sha256": "64106ea1f2b4bd0f0d762589546f060a63dc7e097a0a81992c657e0fcd265199",
            "unique": true,
            "occurrences": 1,
            "context": "figures[1].name"
          },
          "resolution": {
            "status": "metadata_only",
            "scope": "platform_api",
            "checks": [
              {
                "check": "GET /tensor/reports/8398/figures/fig_bond_response.png",
                "result": "http_404",
                "bytes": 29
              }
            ],
            "reason": "record exposes name/caption only; no figure bytes were returned, so no hash is claimed"
          },
          "note": "Bond force versus strain and the Kachanov damage of the bond bundle; the melting regime saturates within one step because F_ref -> 0 at the melting point."
        },
        {
          "asset_id": "r8398:figure:03",
          "asset_class": "figure",
          "label": "fig_parity.png",
          "token": "fig_parity.png",
          "locator": {
            "source_field": "record",
            "method": "record_pointer",
            "start_char": 0,
            "end_char": 1,
            "start_line": 1,
            "end_line": 1,
            "quote": "fig_parity.png",
            "quote_sha256": "56513659661fee2aae6ae8be524595d583a1c744e063392aab7b114fe9a59514",
            "unique": true,
            "occurrences": 1,
            "context": "figures[2].name"
          },
          "resolution": {
            "status": "metadata_only",
            "scope": "platform_api",
            "checks": [
              {
                "check": "GET /tensor/reports/8398/figures/fig_parity.png",
                "result": "http_404",
                "bytes": 29
              }
            ],
            "reason": "record exposes name/caption only; no figure bytes were returned, so no hash is claimed"
          },
          "note": "Per-quantity maximum relative error between the integrated march and the three standalone drivers (all identical to round-off, far below the 1e-10 acceptance line)."
        },
        {
          "asset_id": "r8398:figure:04",
          "asset_class": "figure",
          "label": "fig_statistics.png",
          "token": "fig_statistics.png",
          "locator": {
            "source_field": "record",
            "method": "record_pointer",
            "start_char": 0,
            "end_char": 1,
            "start_line": 1,
            "end_line": 1,
            "quote": "fig_statistics.png",
            "quote_sha256": "458055cbdcf8b2dbab106d3f9087edda2991a7174d6e231bcbcfaab8072ca149",
            "unique": true,
            "occurrences": 1,
            "context": "figures[3].name"
          },
          "resolution": {
            "status": "metadata_only",
            "scope": "platform_api",
            "checks": [
              {
                "check": "GET /tensor/reports/8398/figures/fig_statistics.png",
                "result": "http_404",
                "bytes": 29
              }
            ],
            "reason": "record exposes name/caption only; no figure bytes were returned, so no hash is claimed"
          },
          "note": "Ridge morphology and contact-force-network statistics sampled at the operating point (criterion for N05)."
        }
      ],
      "counts": {
        "assets": 32,
        "by_class": {
          "artifact": 4,
          "declared_test_suite": 1,
          "doc": 1,
          "example": 1,
          "figure": 4,
          "provenance_anchor": 1,
          "python_module_file": 4,
          "python_package": 1,
          "report_markdown": 1,
          "script": 3,
          "symbol": 5,
          "test": 1,
          "upstream_function": 1,
          "upstream_module": 4
        },
        "by_resolution": {
          "declared_only": 22,
          "metadata_only": 4,
          "resolved": 1,
          "unresolved": 5
        },
        "markdown_locators": 28,
        "explicitly_unresolved": 5,
        "declared_only": 22,
        "metadata_only": 4
      },
      "claims": [],
      "claims_note": "task_type=01 and objective.classify_report_type=false: this package registers source assets only and performs no claim extraction, so the claim list is intentionally empty rather than filled with unreviewed restatements.",
      "integrity": {
        "hash_recomputed_locally": true,
        "hash_algorithm": "sha256",
        "verified_logic": "no asset is marked verified; verification is computed by the platform gate, which re-hashes the markdown and re-resolves every locator",
        "quotes_are_measured": "every locator quote is a slice of the fetched markdown bytes"
      }
    }
  },
  "claims": []
}
```

