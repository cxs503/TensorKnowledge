# KF-RESULT wp-5347-01

## ① 本工序做了什么

工序 01（资产登记），对象=report_id `5347`（TensorDEM main CI 清红 m4829）。
只做可程序化的事：取回报告 markdown、**重算字节哈希并与契约对表**、把报告点名过的
附件/工件逐条登记为资产、标注可达性。不抽取、不分类、不改写、不给知识对象定性。
产出 `asset_manifest.json`，装在 kf_result 信封里提交。

约束遵守：每条资产带逐字定位行（`quote` + `start_offset`/`end_offset`），本节与下文所有
数字均由登记脚本从 manifest 插值，未手抄。

## ② 怎么做的（步骤/工具/关键设置）

1. `python3 scripts/fetch_report_5347.py --out artifacts/wp-5347-01/report_5347.md`
   —— 用 `$TENSOR_AGENT_USER` 登录拿 token，GET `/tensor/reports/5347`，只落 `markdown`
   字段的 UTF-8 字节；同时把记录元数据（title/tags/figures 等）存为 `.meta.json`。
2. 重算 `sha256` 与字符数，与契约 `source_hash` / `chars` 对表：
   `sha256:bdd7bb0e76c120366d71fe047057056333cf83cfef6e0a2ca1ca125082a9d2e1` / `4206 chars` —— 一致，否则脚本 exit 2 不出产物。
3. 逐字扫描 markdown：路径正则 + 裸文件名正则（`fragmentation.py` 这类漏前缀指针必须被登记），
   按文档序去重、取首次出现的整行作为 `quote`，偏移由 `rfind/find` 直接量出（非人工估计）。
4. `kind` / `reachability` **只按路径形状与元数据来源**判定（不做语义判断）；未知形状落
   `unclassified`，可达性一律 fail-closed。
5. 图的登记：报告记录 `figures` 只有 name/caption，`GET /tensor/reports/5347/figures` 返回 404
   —— 图像字节不可取回，登记为 `metadata_only`，明确不可当已归档证据。
6. 复核：`scripts/verify_wp_5347_01.py`（A1–A10，含变异测试证明每条能红）、
   `scripts/check_wp_5347_01_platform_gates.py`（复用平台 `kf/ops/knowledge_factory/gates.py`
   重放 g1–g7）、`tests/test_wp_5347_01.py`（14 条 pytest，含 7 条变异反例）。
7. 交付：`scripts/publish_wp_5347_01_report.py` 把本报告以 `KF-RESULT wp-5347-01` 为题、
   tags 含 `kf-wp:wp-5347-01`、mission_id=15564 发到平台；
   正文唯一一个 JSON 代码块即 kf_result 信封（发送前断言只有一块）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/wp-5347-01/asset_manifest.json` | 工序 01 声明输出：源哈希/字符数/标题 + 26 条资产（kind/reachability/locator） |
| `artifacts/wp-5347-01/kf_result.json` | kf_result 信封：package_id/task_type/report_id/provenance/outputs（claims=[]） |
| `artifacts/wp-5347-01/KF-RESULT-wp-5347-01.md` | 本报告（唯一一个 JSON 代码块） |
| `artifacts/wp-5347-01/checks.json` | 复核结果（每项 acceptance + 实测数字） |
| `artifacts/wp-5347-01/report_5347.md` | 源字节快照（复跑与离线复核用，哈希即 provenance） |
| `scripts/wp_5347_01_register_assets.py` | 登记器（唯一产出路径） |
| `scripts/verify_wp_5347_01.py` | 复核器（哈希/locator/ID/信封） |
| `tests/test_wp_5347_01.py` | pytest 机检 |

## ④ 证据定位表（字段 → 原文引文片段）

| 字段 | 值/判定 | 原文引文（逐字，含偏移） |
|---|---|---|
| report 标题 | TensorDEM main CI 清红（m4829）：runner 路径断言与证据账本过期 | 见 `## ① 案例介绍` 首行标题 |
| `source.source_hash` | `sha256:bdd7bb0e76c120366d71fe047057056333cf83cfef6e0a2ca1ca125082a9d2e1` | 由 markdown 字节独立重算，非引文 |
| `source.chars` | 4206 | 契约申报值 4206，实测 4206 |
| 资产 `asset-5347-001` | `/home/runner/work/<repo>/<repo>` | 见下表逐字行与偏移 |

资产逐条登记（`quote` 全文见 manifest 的 `locator.quote`，偏移已机器复核）：

| asset_id | path | kind | reachability | resolved | 所在节 |
|---|---|---|---|---|---|
| asset-5347-001 | `/home/runner/work/<repo>/<repo>` | environment_layout | environment_layout | no | ② 怎么做的 |
| asset-5347-002 | `/work/` | environment_layout | environment_layout | no | ② 怎么做的 |
| asset-5347-003 | `.../_work/<repo>/<repo>` | environment_layout | environment_layout | no | ② 怎么做的 |
| asset-5347-004 | `_work/` | environment_layout | environment_layout | no | ② 怎么做的 |
| asset-5347-005 | `docs/threefield_fragmentation_analytic_verification.md` | document | external_repo_artifact | no | ② 怎么做的 |
| asset-5347-006 | `src/tensordem/threefield/` | code | external_repo_artifact | no | ② 怎么做的 |
| asset-5347-007 | `docs/doc_evidence_ledger.json` | evidence_ledger | external_repo_artifact | no | ② 怎么做的 |
| asset-5347-008 | `artifacts/m4812_ledger_negative_controls/` | artifact | external_repo_artifact | no | ② 怎么做的 |
| asset-5347-009 | `src/tensordem/__init__.py` | code | external_repo_artifact | no | ② 怎么做的 |
| asset-5347-010 | `scripts/audit_doc_evidence.py` | script | external_repo_artifact | no | ② 怎么做的 |
| asset-5347-011 | `scripts/m4829_ci_gate_evidence.py` | script | external_repo_artifact | no | ② 怎么做的 |
| asset-5347-012 | `artifacts/m4829_ci_gate/gate_evidence.json` | artifact | external_repo_artifact | no | ② 怎么做的 |
| asset-5347-013 | `/tmp/_work/TensorDEM/TensorDEM` | ephemeral_sandbox | ephemeral_sandbox | no | ② 怎么做的 |
| asset-5347-014 | `src/tensordem` | code | external_repo_artifact | no | ③ 计算结果 |
| asset-5347-015 | `/home/runner/work/...` | environment_layout | environment_layout | no | ③ 计算结果 |
| asset-5347-016 | `.../ci_env/_work/...` | environment_layout | environment_layout | no | ③ 计算结果 |
| asset-5347-017 | `/root/tp-agent/work/m4829` | environment_layout | environment_layout | no | ③ 计算结果 |
| asset-5347-018 | `tests/test_doc_evidence_pointers.py` | test | external_repo_artifact | no | ③ 计算结果 |
| asset-5347-019 | `tests/test_dem2d_fracture_ledger.py` | test | external_repo_artifact | no | ③ 计算结果 |
| asset-5347-020 | `/tmp/_work/...` | ephemeral_sandbox | ephemeral_sandbox | no | ③ 计算结果 |
| asset-5347-021 | `/home/runner` | environment_layout | environment_layout | no | ⑤ 注意点（坑与局限） |
| asset-5347-022 | `fragmentation.py` | code | external_repo_artifact | no | ② 怎么做的 |
| asset-5347-023 | `audit_doc_evidence.py` | code | external_repo_artifact | no | ③ 计算结果 |
| asset-5347-024 | `libflexiblas.so.3` | environment_dependency | environment_dependency | no | ⑤ 注意点（坑与局限） |
| asset-5347-025 | `provenance_gate_matrix.png` | figure | metadata_only | no | figures[].name |
| asset-5347-026 | `ledger_regeneration.png` | figure | metadata_only | no | figures[].name |

按 kind 计数：

| kind | 数量 |
|---|---|
| artifact | 2 |
| code | 5 |
| document | 1 |
| environment_dependency | 1 |
| environment_layout | 8 |
| ephemeral_sandbox | 2 |
| evidence_ledger | 1 |
| figure | 2 |
| script | 2 |
| test | 2 |

按可达性计数：

| reachability | 数量 |
|---|---|
| environment_dependency | 1 |
| environment_layout | 8 |
| ephemeral_sandbox | 2 |
| external_repo_artifact | 13 |
| metadata_only | 2 |

无场量云图、无解析解/基线比较曲线：本包是纯 I/O 登记（不产生任何物理量或数值结果），
故改画两张台账图——`figures/asset_inventory.png`（按 kind×可达性的资产分布，resolved 恒为 0）
与 `figures/gate_evidence.png`（平台门 g1–g7 与本地 acceptance A1–A10 的逐项状态）。
两图均由 `scripts/wp_5347_01_figures.py` 从 `asset_manifest.json`/`checks.json`/
`platform_gate.json` 直接投影，无手抄数字。

## ⑤ 注意点与局限

- **图像字节不可得**：记录只有 name/caption，figure 端点 404；两张图登记为 `metadata_only`，
  下游若需要图像，必须回 TensorDEM 仓库工件，不能引用本包。
- **跨仓工件一律 resolved=false**：`docs/`、`scripts/`、`artifacts/`、`src/`、`tests/` 下的路径
  属于 TensorDEM（main@524821fd），不在本包 `source_uri` 字节范围内；工序 01 只登记不检出。
- **未使用本地 TensorDEM 检出做存在性校验**：本机虽有检出，但其 HEAD 未必等于 `524821fd`，
  用它“证明存在”会产生不可绑定的结论；如需校验应由上游给出 commit 级工件清单。
- **扫描只覆盖路径形状**：散文里的纯名字（如 `TensorDEM`、`ruff check`）不登记；规则写在
  manifest `registration.extraction_rule` 里，可复核、可反驳。
- **claims 为空数组是契约允许的完整结果**（objective 只要 register_assets），不是失败；
  acceptance 中 “all_claims_have_evidence_or_explicit_unresolved_status” 因此为**空真**，
  本报告如实标注为 `vacuous (0 claims)`，不得读作“已验证”。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 判定 | 依据 |
|---|---|---|
| valid_json | 通过 | `json.load` 两个产物均成功（见 checks.json） |
| schema_pass | 通过 | kf_result 过 `schemas/kf_result.v1.schema.json`（Draft 2020-12） |
| source_locator_resolvable | 通过 | 24 条字符型 locator 的 quote 均为源字节逐字子串，偏移回读一致 |
| source_hash_matches | 通过 | 契约 `sha256:bdd7bb0e76c120366d71fe047057056333cf83cfef6e0a2ca1ca125082a9d2e1` == 实测 `sha256:bdd7bb0e76c120366d71fe047057056333cf83cfef6e0a2ca1ca125082a9d2e1` |
| no_duplicate_ids | 通过 | 26 条 asset_id 唯一 |
| all_claims_have_evidence_or_explicit_unresolved_status | **空真通过（vacuous, 0 claims）** | 本工序不抽取，claims=[]，未伪造任何 claim |
| 本地 acceptance | passed=9 / vacuous=1 / failed=0 / not_run=0 | `artifacts/wp-5347-01/checks.json` |
| 平台门（复用 kf/ops/knowledge_factory/gates.py） | ok=True；结构门 ['g1_valid_json', 'g2_schema_pass', 'g3_identity'] / 证据门 ['g4_source_hash_matches', 'g4b_source_field', 'g5_source_locator_resolvable', 'g5b_all_claims_located_or_unresolved', 'g6_no_duplicate_ids', 'g7_claim_namespace']；locator_rate=None（0 claim=空真，记 None 不记 100%） | `artifacts/wp-5347-01/platform_gate.json` |

未完成项：无（本工序范围内）。局限已在 ⑤ 声明。

## repro_cmd

```bash
python3 scripts/fetch_report_5347.py --out artifacts/wp-5347-01/report_5347.md \
 && python3 scripts/wp_5347_01_register_assets.py \
 && python3 scripts/verify_wp_5347_01.py \
 && python3 scripts/check_wp_5347_01_platform_gates.py \
 && python3 scripts/wp_5347_01_register_assets.py --render-only \
 && python3 scripts/wp_5347_01_figures.py \
 && python3 -m pytest -q tests/test_wp_5347_01.py
```

## 结果信封

```json
{
  "package_id": "wp-5347-01",
  "task_type": "01-asset-registration",
  "report_id": "5347",
  "provenance": {
    "source_hash": "sha256:bdd7bb0e76c120366d71fe047057056333cf83cfef6e0a2ca1ca125082a9d2e1",
    "source_field": "markdown",
    "source_uri": "tensor://reports/5347",
    "producer": "eco_admin / mission 15564 (agent m15564)",
    "emitted_at": "2026-11-12T01:21:39+00:00",
    "notes": "工序 01 结果信封：source_hash 为 GET /tensor/reports/5347 返回 markdown 字段的 UTF-8 字节 sha256，与契约 source_hash 逐字节一致；claims 为空数组（本工序不抽取）。"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-5347-01",
      "task_type": "01-asset-registration",
      "report_id": "5347",
      "source": {
        "report_id": "5347",
        "source_uri": "tensor://reports/5347",
        "source_field": "markdown",
        "source_hash": "sha256:bdd7bb0e76c120366d71fe047057056333cf83cfef6e0a2ca1ca125082a9d2e1",
        "chars": 4206,
        "title": "TensorDEM main CI 清红（m4829）：runner 路径断言与证据账本过期",
        "scenario_key": "ci_clearance",
        "status": "published",
        "created_at": "2026-11-06T14:46:12.438974+00:00",
        "tags": [
          "CI",
          "gate",
          "provenance",
          "doc-evidence",
          "TensorDEM",
          "main-red"
        ],
        "retrieved_via": "GET TENSOR_API_BASE/tensor/reports/5347 (Bearer auth)"
      },
      "registration": {
        "objective": "register_assets",
        "producer": "eco_admin / mission 15564 (agent m15564, TensorKnowledge)",
        "generated_at": "2026-11-12T01:21:39+00:00",
        "extraction_performed": false,
        "classification_performed": false,
        "claims_extracted": 0,
        "claims_note": "契约 objective 只要求 register_assets（classify_report_type=false）；claims 为空数组是合法完整结果，未生成任何知识对象",
        "extraction_rule": {
          "path_regex": "(?:~|/)?(?:[A-Za-z0-9_.@<>${}-]+/)+[A-Za-z0-9_.@<>-]*(?:\\.[A-Za-z0-9]{1,6})?",
          "bare_file_regex": "[A-Za-z0-9_.-]+\\.(?:py|json|md|png|so\\.3)",
          "dedupe": "document order, first occurrence wins; bare filename skipped when already covered by a longer path token",
          "kind_rules": [
            [
              "docs/",
              ".json",
              "evidence_ledger"
            ],
            [
              "docs/",
              ".md",
              "document"
            ],
            [
              "scripts/",
              ".py",
              "script"
            ],
            [
              "artifacts/",
              "",
              "artifact"
            ],
            [
              "tests/",
              "",
              "test"
            ],
            [
              "src/",
              "",
              "code"
            ]
          ],
          "excluded": [
            {
              "token": "code/test/doc:TRACKED`",
              "reason": "冒号后缀=报告里的状态标签（如 code/test/doc:TRACKED），不是文件路径"
            }
          ]
        }
      },
      "assets": [
        {
          "asset_id": "asset-5347-001",
          "kind": "environment_layout",
          "path": "/home/runner/work/<repo>/<repo>",
          "reachability": "environment_layout",
          "resolved": false,
          "resolution_note": "runner 检出布局示例（目录名本身不是资产），登记以保留门禁反例上下文；resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "② 怎么做的",
            "quote": "     `/home/runner/work/<repo>/<repo>`（含 `/work/`），自托管 runner 检出在 `.../_work/<repo>/<repo>`",
            "start_offset": 673,
            "end_offset": 764,
            "quote_sha256": "sha256:b6a273051ea4c90863ea552d80802091a75b5e02a63b692534824746acb66e38"
          }
        },
        {
          "asset_id": "asset-5347-002",
          "kind": "environment_layout",
          "path": "/work/",
          "reachability": "environment_layout",
          "resolved": false,
          "resolution_note": "runner 检出布局示例（目录名本身不是资产），登记以保留门禁反例上下文；resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "② 怎么做的",
            "quote": "     `/home/runner/work/<repo>/<repo>`（含 `/work/`），自托管 runner 检出在 `.../_work/<repo>/<repo>`",
            "start_offset": 673,
            "end_offset": 764,
            "quote_sha256": "sha256:b6a273051ea4c90863ea552d80802091a75b5e02a63b692534824746acb66e38"
          }
        },
        {
          "asset_id": "asset-5347-003",
          "kind": "environment_layout",
          "path": ".../_work/<repo>/<repo>",
          "reachability": "environment_layout",
          "resolved": false,
          "resolution_note": "runner 检出布局示例（目录名本身不是资产），登记以保留门禁反例上下文；resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "② 怎么做的",
            "quote": "     `/home/runner/work/<repo>/<repo>`（含 `/work/`），自托管 runner 检出在 `.../_work/<repo>/<repo>`",
            "start_offset": 673,
            "end_offset": 764,
            "quote_sha256": "sha256:b6a273051ea4c90863ea552d80802091a75b5e02a63b692534824746acb66e38"
          }
        },
        {
          "asset_id": "asset-5347-004",
          "kind": "environment_layout",
          "path": "_work/",
          "reachability": "environment_layout",
          "resolved": false,
          "resolution_note": "runner 检出布局示例（目录名本身不是资产），登记以保留门禁反例上下文；resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "② 怎么做的",
            "quote": "     （只有 `_work/`）。同一棵干净的树，只换挂载前缀就红/绿翻转——断言测的是 runner，不是仓库。",
            "start_offset": 765,
            "end_offset": 824,
            "quote_sha256": "sha256:815e29e7344a1515d4962dcd396cd302932d7865bd8c702d2eafe47fa1b116aa"
          }
        },
        {
          "asset_id": "asset-5347-005",
          "kind": "document",
          "path": "docs/threefield_fragmentation_analytic_verification.md",
          "reachability": "external_repo_artifact",
          "resolved": false,
          "resolution_note": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "② 怎么做的",
            "quote": "   - `test_cited_source_docs_and_tests_are_tracked`：`docs/threefield_fragmentation_analytic_verification.md`",
            "start_offset": 825,
            "end_offset": 933,
            "quote_sha256": "sha256:2ea81f222e063aa1e792ea507f0b51d14cce4e2bc73800bf5132353c1eb8291d"
          }
        },
        {
          "asset_id": "asset-5347-006",
          "kind": "code",
          "path": "src/tensordem/threefield/",
          "reachability": "external_repo_artifact",
          "resolved": false,
          "resolution_note": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "② 怎么做的",
            "quote": "     把子包路径写成 `fragmentation.py`（漏 `src/tensordem/threefield/` 前缀）→ `code:MISSING`。",
            "start_offset": 934,
            "end_offset": 1016,
            "quote_sha256": "sha256:3d7944694c1de2192460858139dfe55ac6f1fea22e4bcaaf8175c34c285fb4b1"
          }
        },
        {
          "asset_id": "asset-5347-007",
          "kind": "evidence_ledger",
          "path": "docs/doc_evidence_ledger.json",
          "reachability": "external_repo_artifact",
          "resolved": false,
          "resolution_note": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "② 怎么做的",
            "quote": "   - `test_committed_ledger_is_current`：`docs/doc_evidence_ledger.json` 冻结在 145 篇/831 条，",
            "start_offset": 1017,
            "end_offset": 1105,
            "quote_sha256": "sha256:194ac62a22f5c7e2465d38cbc2e9bacf31e8bc772dc752900ccdf975f5503b5e"
          }
        },
        {
          "asset_id": "asset-5347-008",
          "kind": "artifact",
          "path": "artifacts/m4812_ledger_negative_controls/",
          "reachability": "external_repo_artifact",
          "resolved": false,
          "resolution_note": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "② 怎么做的",
            "quote": "     m4819 合并后树里已有 151 篇（本单完成后 152 篇），且 `artifacts/m4812_ledger_negative_controls/`",
            "start_offset": 1106,
            "end_offset": 1189,
            "quote_sha256": "sha256:d738e1ca8c5e28f89aee4afa9237fdc99e7aec0df23accf2407dad1746f942ed"
          }
        },
        {
          "asset_id": "asset-5347-009",
          "kind": "code",
          "path": "src/tensordem/__init__.py",
          "reachability": "external_repo_artifact",
          "resolved": false,
          "resolution_note": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "② 怎么做的",
            "quote": "   「解析后落在本树 `src/tensordem/__init__.py`」，并新增负控 `test_provenance_rejects_a_foreign_tree`",
            "start_offset": 1290,
            "end_offset": 1377,
            "quote_sha256": "sha256:58e33a240924ee43e1e5bbb28dfd448f1ea1ae6047bea224f60277b255f46061"
          }
        },
        {
          "asset_id": "asset-5347-010",
          "kind": "script",
          "path": "scripts/audit_doc_evidence.py",
          "reachability": "external_repo_artifact",
          "resolved": false,
          "resolution_note": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "② 怎么做的",
            "quote": "3. **账本重生成**：`python scripts/audit_doc_evidence.py --json docs/doc_evidence_ledger.json`，",
            "start_offset": 1441,
            "end_offset": 1530,
            "quote_sha256": "sha256:dd17dfcd8d625f6eb05108161444a1678ee045b7b1c0298876b067a4173af338"
          }
        },
        {
          "asset_id": "asset-5347-011",
          "kind": "script",
          "path": "scripts/m4829_ci_gate_evidence.py",
          "reachability": "external_repo_artifact",
          "resolved": false,
          "resolution_note": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "② 怎么做的",
            "quote": "4. **证据程序化**：`scripts/m4829_ci_gate_evidence.py` 从 `git show HEAD:docs/doc_evidence_ledger.json`",
            "start_offset": 1568,
            "end_offset": 1664,
            "quote_sha256": "sha256:5e303814f9ac342e02ec408562885b9c0ae4a2466efd4561afa3bd26fb62afde"
          }
        },
        {
          "asset_id": "asset-5347-012",
          "kind": "artifact",
          "path": "artifacts/m4829_ci_gate/gate_evidence.json",
          "reachability": "external_repo_artifact",
          "resolved": false,
          "resolution_note": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "② 怎么做的",
            "quote": "   `artifacts/m4829_ci_gate/gate_evidence.json` 与两张图（零手抄）。",
            "start_offset": 1693,
            "end_offset": 1751,
            "quote_sha256": "sha256:33f25aaa3d50638cc96c317e3a792a4f1fb5df89828101b60306665cf691d132"
          }
        },
        {
          "asset_id": "asset-5347-013",
          "kind": "ephemeral_sandbox",
          "path": "/tmp/_work/TensorDEM/TensorDEM",
          "reachability": "ephemeral_sandbox",
          "resolved": false,
          "resolution_note": "报告中的临时复现目录（/tmp/...），任务结束即消失，不构成资产；resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "② 怎么做的",
            "quote": "5. **端到端复现**：整树复制到 `/tmp/_work/TensorDEM/TensorDEM`（自托管布局同形），",
            "start_offset": 1752,
            "end_offset": 1813,
            "quote_sha256": "sha256:ef9f490e758e85f066dfb60ac02b93f76aab3ebe8b0f2c92dcb9c65fdbfb8c20"
          }
        },
        {
          "asset_id": "asset-5347-014",
          "kind": "code",
          "path": "src/tensordem",
          "reachability": "external_repo_artifact",
          "resolved": false,
          "resolution_note": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "③ 计算结果",
            "quote": "| 检出布局 | main 门禁（\"/work/\" in path） | 修复后门禁（须落在本树 src/tensordem） |",
            "start_offset": 1890,
            "end_offset": 1955,
            "quote_sha256": "sha256:876b2d72566162b8d1bfe8429a29d1627b8215fa8944a473ba8b12a0811b9356"
          }
        },
        {
          "asset_id": "asset-5347-015",
          "kind": "environment_layout",
          "path": "/home/runner/work/...",
          "reachability": "environment_layout",
          "resolved": false,
          "resolution_note": "runner 检出布局示例（目录名本身不是资产），登记以保留门禁反例上下文；resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "③ 计算结果",
            "quote": "| github-hosted (/home/runner/work/...) | PASS | PASS |",
            "start_offset": 1970,
            "end_offset": 2025,
            "quote_sha256": "sha256:ad1a0c7574cff4901f798a4b49cb502f664129c8c07a17d3247f53853eb3537b"
          }
        },
        {
          "asset_id": "asset-5347-016",
          "kind": "environment_layout",
          "path": ".../ci_env/_work/...",
          "reachability": "environment_layout",
          "resolved": false,
          "resolution_note": "runner 检出布局示例（目录名本身不是资产），登记以保留门禁反例上下文；resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "③ 计算结果",
            "quote": "| self-hosted loong64 (.../ci_env/_work/...) | FAIL | PASS |",
            "start_offset": 2026,
            "end_offset": 2086,
            "quote_sha256": "sha256:fecc33cbb1fd6a30650d00c712341744897659e95f6927fe9570518cada17fcc"
          }
        },
        {
          "asset_id": "asset-5347-017",
          "kind": "environment_layout",
          "path": "/root/tp-agent/work/m4829",
          "reachability": "environment_layout",
          "resolved": false,
          "resolution_note": "runner 检出布局示例（目录名本身不是资产），登记以保留门禁反例上下文；resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "③ 计算结果",
            "quote": "| agent worktree (/root/tp-agent/work/m4829) | PASS | PASS |",
            "start_offset": 2087,
            "end_offset": 2147,
            "quote_sha256": "sha256:60d8ce1bddf865785f321eb0467b1ef022f8433caf78d0321b5e4f42757efce3"
          }
        },
        {
          "asset_id": "asset-5347-018",
          "kind": "test",
          "path": "tests/test_doc_evidence_pointers.py",
          "reachability": "external_repo_artifact",
          "resolved": false,
          "resolution_note": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "③ 计算结果",
            "quote": "| `pytest -q tests/test_doc_evidence_pointers.py tests/test_dem2d_fracture_ledger.py` | 20 passed |",
            "start_offset": 2638,
            "end_offset": 2737,
            "quote_sha256": "sha256:b1c16f032d61f74c7279dc7a51e6ebc4dd228fcc8d3b1e7648073c9250d80f3d"
          }
        },
        {
          "asset_id": "asset-5347-019",
          "kind": "test",
          "path": "tests/test_dem2d_fracture_ledger.py",
          "reachability": "external_repo_artifact",
          "resolved": false,
          "resolution_note": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "③ 计算结果",
            "quote": "| `pytest -q tests/test_doc_evidence_pointers.py tests/test_dem2d_fracture_ledger.py` | 20 passed |",
            "start_offset": 2638,
            "end_offset": 2737,
            "quote_sha256": "sha256:b1c16f032d61f74c7279dc7a51e6ebc4dd228fcc8d3b1e7648073c9250d80f3d"
          }
        },
        {
          "asset_id": "asset-5347-020",
          "kind": "ephemeral_sandbox",
          "path": "/tmp/_work/...",
          "reachability": "ephemeral_sandbox",
          "resolved": false,
          "resolution_note": "报告中的临时复现目录（/tmp/...），任务结束即消失，不构成资产；resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "③ 计算结果",
            "quote": "| `main` 版测试文件在 `/tmp/_work/...` 布局下 | 1 failed（红项复现） |",
            "start_offset": 2805,
            "end_offset": 2860,
            "quote_sha256": "sha256:df4995805ee220120e7fe5adf65ee8270ed2f415326ad74daee4a2d2b5e79241"
          }
        },
        {
          "asset_id": "asset-5347-021",
          "kind": "environment_layout",
          "path": "/home/runner",
          "reachability": "environment_layout",
          "resolved": false,
          "resolution_note": "runner 检出布局示例（目录名本身不是资产），登记以保留门禁反例上下文；resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "⑤ 注意点（坑与局限）",
            "quote": "- **门禁不能测 runner**：依赖 `cwd`、`/home/runner`、`$GITHUB_WORKSPACE` 或目录名的断言在自托管",
            "start_offset": 3195,
            "end_offset": 3269,
            "quote_sha256": "sha256:a55d4821524071e620420739653d58d78682db5ee80d7aac5a8bbb9983fa58fd"
          }
        },
        {
          "asset_id": "asset-5347-022",
          "kind": "code",
          "path": "fragmentation.py",
          "reachability": "external_repo_artifact",
          "resolved": false,
          "resolution_note": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "② 怎么做的",
            "quote": "     把子包路径写成 `fragmentation.py`（漏 `src/tensordem/threefield/` 前缀）→ `code:MISSING`。",
            "start_offset": 934,
            "end_offset": 1016,
            "quote_sha256": "sha256:3d7944694c1de2192460858139dfe55ac6f1fea22e4bcaaf8175c34c285fb4b1"
          }
        },
        {
          "asset_id": "asset-5347-023",
          "kind": "code",
          "path": "audit_doc_evidence.py",
          "reachability": "external_repo_artifact",
          "resolved": false,
          "resolution_note": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "③ 计算结果",
            "quote": "| `audit_doc_evidence.py --check` | `ledger up to date` |",
            "start_offset": 2900,
            "end_offset": 2957,
            "quote_sha256": "sha256:7f45a00e276c87f6d228f83c27f8787c8fc274e0603f1f01a19899f1335e6ba4"
          }
        },
        {
          "asset_id": "asset-5347-024",
          "kind": "environment_dependency",
          "path": "libflexiblas.so.3",
          "reachability": "environment_dependency",
          "resolved": false,
          "resolution_note": "运行环境依赖（非报告产出），登记以保留“集群不适用”结论的上下文；resolved=false",
          "locator": {
            "locator_type": "char_span",
            "section": "⑤ 注意点（坑与局限）",
            "quote": "- **集群不适用**：外协方双节点 loong64 环境缺 `libflexiblas.so.3`/`scipy`，`pytest` 收集期即",
            "start_offset": 3448,
            "end_offset": 3522,
            "quote_sha256": "sha256:5471f57c35e9675dddb2decbd77396c6d14a00c422504b94873802f2966a799d"
          }
        },
        {
          "asset_id": "asset-5347-025",
          "kind": "figure",
          "path": "provenance_gate_matrix.png",
          "reachability": "metadata_only",
          "resolved": false,
          "resolution_note": "仅在图注元数据中出现，报告记录未携带图像字节，GET /tensor/reports/5347/figures 返回 404；resolved=false",
          "declared_caption": "溯源门禁在四种检出布局下的判定：main@524821fd 的 \"/work/\" 断言在自托管 runner(_work)与沙箱布局上假红；修复后的门禁按仓库根判定，只拒绝外部 checkout（负控）。",
          "locator": {
            "locator_type": "record_field",
            "field": "figures[].name",
            "value_sha256": "sha256:d8c986f8488b7f4930c653afed5629a5bb8ef947efba2c1e47502df50ff0f8ee"
          }
        },
        {
          "asset_id": "asset-5347-026",
          "kind": "figure",
          "path": "ledger_regeneration.png",
          "reachability": "metadata_only",
          "resolved": false,
          "resolution_note": "仅在图注元数据中出现，报告记录未携带图像字节，GET /tensor/reports/5347/figures 返回 404；resolved=false",
          "declared_caption": "证据账本逐状态计数：提交态（过期，145 篇/831 条）vs 重生成后（152 篇/879 条）；3 条被门禁滤除的产物如实降级为 MISSING+REGENERABLE。",
          "locator": {
            "locator_type": "record_field",
            "field": "figures[].name",
            "value_sha256": "sha256:4782b46172a49c1d37acc24f9e9227b7ec34ab429f76ff6e18ea0c833f1800d8"
          }
        }
      ],
      "counts": {
        "assets": 26,
        "resolved": 0,
        "unresolved": 26,
        "by_kind": {
          "artifact": 2,
          "code": 5,
          "document": 1,
          "environment_dependency": 1,
          "environment_layout": 8,
          "ephemeral_sandbox": 2,
          "evidence_ledger": 1,
          "figure": 2,
          "script": 2,
          "test": 2
        },
        "by_reachability": {
          "environment_dependency": 1,
          "environment_layout": 8,
          "ephemeral_sandbox": 2,
          "external_repo_artifact": 13,
          "metadata_only": 2
        },
        "by_section": {
          "figures[].name": 2,
          "② 怎么做的": 14,
          "③ 计算结果": 8,
          "⑤ 注意点（坑与局限）": 2
        }
      },
      "unresolved": [
        {
          "asset_id": "asset-5347-001",
          "path": "/home/runner/work/<repo>/<repo>",
          "reason": "runner 检出布局示例（目录名本身不是资产），登记以保留门禁反例上下文；resolved=false"
        },
        {
          "asset_id": "asset-5347-002",
          "path": "/work/",
          "reason": "runner 检出布局示例（目录名本身不是资产），登记以保留门禁反例上下文；resolved=false"
        },
        {
          "asset_id": "asset-5347-003",
          "path": ".../_work/<repo>/<repo>",
          "reason": "runner 检出布局示例（目录名本身不是资产），登记以保留门禁反例上下文；resolved=false"
        },
        {
          "asset_id": "asset-5347-004",
          "path": "_work/",
          "reason": "runner 检出布局示例（目录名本身不是资产），登记以保留门禁反例上下文；resolved=false"
        },
        {
          "asset_id": "asset-5347-005",
          "path": "docs/threefield_fragmentation_analytic_verification.md",
          "reason": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false"
        },
        {
          "asset_id": "asset-5347-006",
          "path": "src/tensordem/threefield/",
          "reason": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false"
        },
        {
          "asset_id": "asset-5347-007",
          "path": "docs/doc_evidence_ledger.json",
          "reason": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false"
        },
        {
          "asset_id": "asset-5347-008",
          "path": "artifacts/m4812_ledger_negative_controls/",
          "reason": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false"
        },
        {
          "asset_id": "asset-5347-009",
          "path": "src/tensordem/__init__.py",
          "reason": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false"
        },
        {
          "asset_id": "asset-5347-010",
          "path": "scripts/audit_doc_evidence.py",
          "reason": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false"
        },
        {
          "asset_id": "asset-5347-011",
          "path": "scripts/m4829_ci_gate_evidence.py",
          "reason": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false"
        },
        {
          "asset_id": "asset-5347-012",
          "path": "artifacts/m4829_ci_gate/gate_evidence.json",
          "reason": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false"
        },
        {
          "asset_id": "asset-5347-013",
          "path": "/tmp/_work/TensorDEM/TensorDEM",
          "reason": "报告中的临时复现目录（/tmp/...），任务结束即消失，不构成资产；resolved=false"
        },
        {
          "asset_id": "asset-5347-014",
          "path": "src/tensordem",
          "reason": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false"
        },
        {
          "asset_id": "asset-5347-015",
          "path": "/home/runner/work/...",
          "reason": "runner 检出布局示例（目录名本身不是资产），登记以保留门禁反例上下文；resolved=false"
        },
        {
          "asset_id": "asset-5347-016",
          "path": ".../ci_env/_work/...",
          "reason": "runner 检出布局示例（目录名本身不是资产），登记以保留门禁反例上下文；resolved=false"
        },
        {
          "asset_id": "asset-5347-017",
          "path": "/root/tp-agent/work/m4829",
          "reason": "runner 检出布局示例（目录名本身不是资产），登记以保留门禁反例上下文；resolved=false"
        },
        {
          "asset_id": "asset-5347-018",
          "path": "tests/test_doc_evidence_pointers.py",
          "reason": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false"
        },
        {
          "asset_id": "asset-5347-019",
          "path": "tests/test_dem2d_fracture_ledger.py",
          "reason": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false"
        },
        {
          "asset_id": "asset-5347-020",
          "path": "/tmp/_work/...",
          "reason": "报告中的临时复现目录（/tmp/...），任务结束即消失，不构成资产；resolved=false"
        },
        {
          "asset_id": "asset-5347-021",
          "path": "/home/runner",
          "reason": "runner 检出布局示例（目录名本身不是资产），登记以保留门禁反例上下文；resolved=false"
        },
        {
          "asset_id": "asset-5347-022",
          "path": "fragmentation.py",
          "reason": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false"
        },
        {
          "asset_id": "asset-5347-023",
          "path": "audit_doc_evidence.py",
          "reason": "工件属于 TensorDEM 仓库（main@524821fd），不在本包 source_uri 覆盖的字节内；工序 01 只登记不检出，故 resolved=false"
        },
        {
          "asset_id": "asset-5347-024",
          "path": "libflexiblas.so.3",
          "reason": "运行环境依赖（非报告产出），登记以保留“集群不适用”结论的上下文；resolved=false"
        },
        {
          "asset_id": "asset-5347-025",
          "path": "provenance_gate_matrix.png",
          "reason": "仅在图注元数据中出现，报告记录未携带图像字节，GET /tensor/reports/5347/figures 返回 404；resolved=false"
        },
        {
          "asset_id": "asset-5347-026",
          "path": "ledger_regeneration.png",
          "reason": "仅在图注元数据中出现，报告记录未携带图像字节，GET /tensor/reports/5347/figures 返回 404；resolved=false"
        }
      ],
      "notes": [
        "本包不含抽取、分类或知识判断；assets 只记录报告点名过的路径与其逐字定位行。",
        "所有资产 resolved=false：可解析的只有报告 markdown 自身字节，其 sha256 已与契约一致。",
        "报告记录的 figures 元数据只有 name/caption，图像字节不可通过 API 取回（404），因此图像资产登记为 metadata_only，不得在下游当作已归档证据。"
      ]
    }
  },
  "claims": []
}
```
