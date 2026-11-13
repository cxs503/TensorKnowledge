# KF-RESULT wp-542-04

**工作包**: `wp-542-04` (`04-independent-review`) · **被审对象**: `wp-542-01` (report 542)
**审核角色**: red-team-reviewer · **结论**: **pass**（阻断项 0）

## ① 本工序做了什么

对 report 542（《FEM/DEM 能力盘点与成组任务树 — m605 进展报告》）的上游工作包 `wp-542-01`（task_type `01-asset-registration`）做独立对抗式审核：不看生产者解释，只以**报告原文 + 上游知识产物**（`kf_result.json` / `asset_manifest.json` / `verification.json`）为上下文，独立重算哈希、路径清点的召回/精确率、定位符逐字一致性、身份去重口径、报告内部数值自洽性，判定上游能否放行给下游工序。**本轮不改上游任何产物，也不把任何结论标成 verified。**

## ② 怎么做的（步骤/工具/关键设置）

1. 取原文：`GET /api/v1/tensor/reports/542` 的 `markdown` 字段落盘为 `source_snapshot.md`，重算 SHA256 与契约声明比对（C1）。
2. 取上游产物：`docs/kf/wp-542-01/*.json`，重算 `asset_manifest.json` 字节哈希与其在 `kf_result.json` 中的自声明比对（C3）。
3. 路径清点：对原文做**独立**正则抽取 `[A-Za-z0-9_./-]+\.(py|json|png|md|csv|dat)`，与 manifest 的 `path_reference` 集合做双向差集——召回（C4）/ 无捏造（C5）。
4. 定位符核验：对每条 `locator.scheme=markdown_line` 资产，检查 `quote` 是否为其**声明行**的逐字子串，且 `path_reference` 出现在同一行（C6）。
5. 身份核验：`asset_id` 唯一性（C7）、`(path, markdown_line)` 重复、basename 归一后的**真实文件数**。
6. 报告内部自洽：任务树节点/工时/并行组算术（C11-C13）；§6「无数值结果」与 §3.4/3.5 雷达分数的冲突（C15）；PASS 类结论与可解析证据的比例（C14）。
7. 全部引文由程序断言为原文逐字子串，findings 内的引文同样复查（C17）；miss 即 check fail，不做人工修补。

## ③ 产出物清单

| 文件 | 要点 |
|------|------|
| `docs/kf/wp-542-04/review_report.json` | 机读审核结论：verdict / checks / findings / limitations（本单交付物） |
| `docs/kf/wp-542-04/kf_result.json` | 结果信封（package_id / task_type / report_id / provenance / outputs） |
| `docs/kf/wp-542-04/source_snapshot.md` | 被审 markdown 字节级快照（`--offline` 复跑输入） |
| `docs/kf/wp-542-04/report_body.md` | 本报告正文（数字由脚本注入，零手抄） |
| `scripts/kf/review_wp542_04.py` | 一键复跑全部检查（见 ⑧） |
| `docs/kf/wp-542-04/figs/review_overview.png` | 三分面：解析状态分布 / 引用数与真实文件数 / L1 节点数 vs 组员数 |

## ④ 证据定位表（claim/字段 → 原文逐字引文）

> 引文由脚本断言 `quote in markdown`；行号=平台 markdown 行号（1-based）。

| # | 判定对象 | 原文引文（逐字） | 行 |
|---|----------|------------------|----|
| C1 | 原文哈希锚点（参数表首行） | `\| 冰密度 ρ_ice \| 917 kg/m³ \| dem3d.py:24 硬编码 \|` | 27 |
| C4/C5 | 路径清点：qualified 形式 | `tensorfem/shell4.py` | 31 |
| F-01 | 同一文件的 qualified 写法（别名组） | `tensorfem/cohesive.py:32` | 32 |
| F-01 | 同一文件的 unqualified 写法 | `\| cohesive.py \| 两节点cohesive界面 \| ✅有测试 \| PASS \| test_cohesive.py (6 tests) \|` | 85 |
| C4/C5 | 同一行并列两条路径 | `tensorfem/dynamics.py, explicit_dynamics.py` | 33 |
| C15 | §6「无数值结果」声明 | `本单为 **能力盘点与任务规划**，无数值计算结果，故无误差判定` | 216 |
| C15 | §3.4 量化差距断言 | `整体差距在 4-6 分（10分制）` | 126 |
| C15 | §3.4 分项评分（无评分表） | `TensorFEM 在时间积分(7)和断裂(6)方面较强，但在自适应(1)、并行(2)、工程规模(2)方面严重不足` | 124 |
| C11 | 任务树 L1 行（8 节点 / A(5),B(4),C(3)） | `\| L1 基础能力 \| 8 \| 136h \| A(5并行), B(4), C(3) \|` | 156 |
| C13 | 任务树 L2 行（重列 A/B/C） | `\| L2 验证锚 \| 4 \| 50h \| B(2), C(1), A(1) \|` | 157 |
| C12 | 任务树合计 16 节点 278h | `\| **合计** \| **16** \| **278h** \| — \|` | 159 |
| C13 | 组A 5 个任务（跨层，含 V04） | `- **立即启动（组A）**：F01, F03, F04, F05, V04 — 5个任务可并行` | 172 |
| F-03 | 只读审计的证据基础 | `1. **只读审计**：未修改任何 src/ 代码，所有论断基于源码 + 已有测试` | 194 |
| F-03 | PASS 结论下唯一的量化演示规模 | `2. **规模限制**：SI-4 演示为 smoke 级（12颗粒），非工程规模` | 195 |
| F-03 | GPU 能力自述（未验证） | `3. **GPU 未验证**：dem3d.py 声称支持 CUDA，但 cell list 可能同步阻塞` | 196 |
| F-03 | 模块自承精度不合格 | 4. **物理精度**：coupled_hull.py 的 `physical_accuracy_qualified` 硬编码为 False | 197 |
| F-06 | SIR 缩写的唯一出处 | `SIR（Suboff Icebreaking Research）` | 14 |

## ⑤ 注意点与局限

1. **上游 47/51 资产 unresolved**（resolved=1, metadata_only=3, unresolved=47）：TensorFEM/TensorDEM 源码树不在本仓边界内，故本单只裁「登记是否忠实于原文」，**不裁**「PASS 是否成立」——能力真伪属领域仓/下游取证范围。
2. **上游自门记录只作证据**：`verification.json` 的 `all_pass` 被读取但未被采纳为本单裁决（C16=`not_run`）。
3. **未读生产者解释**：上下文仅原文 + 上游三件产物，未引入任何生产者叙述性说明。
4. **未运行** TensorFEM/TensorDEM 的任何测试或算例（越界），对报告的能力论断保持 unresolved。
5. 引文行号绑定平台当前 markdown（sha256 已固定）；报告若被重新编辑，行号需重算，哈希门会先失败。
6. **同仓独立性局限**：与上游共用同一 worktree，独立性是方法学的（独立重算 + 不同检查面），非组织隔离；已在 `review_report.json` 的 `reviewer_independence` 中登记。

## ⑥ 自检（对照 acceptance 逐条）

| acceptance 项 | 结果 | 依据 |
|---------------|------|------|
| valid_json | ✅ | `json.load` 通过（review_report.json / kf_result.json） |
| schema_pass | ✅ | 信封五键齐备；`task_type` 匹配 `^[0-9]{2}(-[a-z0-9-]+)?$`；`provenance` 含 `source_hash`+`source_field` |
| reviewer_independent | ✅ | 上下文=原文+上游产物；未读生产者解释；哈希/清点/定位符独立重算（局限见 ⑤-6） |
| upstream_packages_completed | ✅ | `wp-542-01` 三件产物齐备且 manifest 哈希自洽（C3） |

**审核校验面**：13 pass / 2 fail / 2 not_run；**发现项**：阻断 0 / medium 3 / low 2 / info 1。

**如实列的未通过/未跑项**：C14（能力真伪不可由本仓校验）、C16（上游自门记录不采纳）为 `not_run`；C13（L1 并行组员数与节点数不符）与 C15（§6 与 §3.4/3.5 冲突）为 `fail`，分别对应 F-04、F-05，未做粉饰。

## ⑦ 误差判定

本单为审核工序，不产生物理计算量、**无基准量可比**，故不适用「<3%」物理误差判定；可量化的一致性指标是**精确计数**（离散比对，无浮点误差）：

- 路径清点：召回 36/36（漏登 0、误登 0）→ 偏差 **0%**；
- 定位符逐字一致：47 条 `markdown_line`，quote 不符 0、path 不符 0 → 偏差 **0%**；
- 身份口径：资产计数 51 / 路径串 36 / 归一文件 33（差 3 源于 qualified/unqualified 别名，见 F-01）；
- 任务树算术：8+4+4=16（合计 16，偏差 0%）；工时 136+50+92=278（合计 278，偏差 0%）；但 L1 行组员数 12 ≠ L1 节点数 8（F-04）。

**是否 <3%？** 就「登记忠实度」类指标：**是**（均为 0%，精确匹配）。就报告自身的能力论断：**无法判定**（证据 unresolved，不冒充通过）。

## ⑧ 复跑命令

```bash
# 在线（需 TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS）
python3 scripts/kf/review_wp542_04.py --out docs/kf/wp-542-04
# 离线（用本包已提交的 source_snapshot.md 字节快照，不联网）
python3 scripts/kf/review_wp542_04.py --offline --out docs/kf/wp-542-04
python3 -c "import json;print(json.load(open('docs/kf/wp-542-04/review_report.json'))['verdict'])"
```

```json
{
  "package_id": "wp-542-04",
  "task_type": "04-independent-review",
  "report_id": "542",
  "provenance": {
    "source_uri": "tensor://reports/542",
    "source_field": "markdown",
    "source_hash": "sha256:a07bad2500aeed73b47222738bffb3d6a70d39a16790e2c991e01f5bbb239b40",
    "hash_algo": "sha256",
    "hashed_bytes": "markdown encoded as utf-8",
    "source_chars": 6599,
    "source_bytes_utf8": 10333,
    "fetched_via": "snapshot",
    "producer": "agent/m15797",
    "contract_version": "1.0",
    "output_path": "docs/kf/wp-542-04/review_report.json",
    "output_sha256": "af6a31de199ba156c8602a2523e1afc4e425fce7f74d5f9ddd3d034a15806bcc",
    "output_bytes": 20370
  },
  "outputs": {
    "review_report.json": {
      "package_id": "wp-542-04",
      "task_type": "04-independent-review",
      "report_id": "542",
      "reviewed_package": "wp-542-01",
      "reviewer_role": "red-team-reviewer",
      "verdict": "pass",
      "verdict_scope": "semantic fidelity of wp-542-01 asset registration to report 542 (registration fidelity, not capability truth)",
      "verdict_rationale": "Registration-level checks pass independently: source hash match, 36/36 path recall, 0 invented paths, 47/47 verbatim locators, upstream gate NOT adopted as the verdict. 6 non-blocking findings (medium=3) are carried downstream as constraints.",
      "reviewer_independence": {
        "context_inputs": [
          "report 542 markdown (platform record)",
          "docs/kf/wp-542-01/kf_result.json",
          "docs/kf/wp-542-01/asset_manifest.json",
          "docs/kf/wp-542-01/verification.json"
        ],
        "producer_explanation_consumed": false,
        "upstream_self_verification_adopted_as_verdict": false,
        "checks_recomputed_from_scratch": true,
        "shared_worktree_with_upstream": true,
        "independence_limitation": "same repository/worktree as the upstream package; independence is methodological (independent recomputation + a different check surface), not organisational"
      },
      "source": {
        "uri": "tensor://reports/542",
        "field": "markdown",
        "hash_recomputed": "sha256:a07bad2500aeed73b47222738bffb3d6a70d39a16790e2c991e01f5bbb239b40",
        "hash_declared": "sha256:a07bad2500aeed73b47222738bffb3d6a70d39a16790e2c991e01f5bbb239b40",
        "chars": 6599,
        "bytes_utf8": 10333,
        "fetched_via": "snapshot",
        "snapshot": "docs/kf/wp-542-04/source_snapshot.md"
      },
      "reviewed_artifacts": [
        {
          "path": "docs/kf/wp-542-01/asset_manifest.json",
          "sha256": "5f3b256eb953c08aa112cc6a155d8dc0e5dec40de2f627f24a564f5e115c5f71",
          "bytes": 35028
        },
        {
          "path": "docs/kf/wp-542-01/kf_result.json",
          "sha256": "e53aedc67f01448b01b70455632ebd44cb868a61731280b332ca1696caf82fc0",
          "bytes": 816
        },
        {
          "path": "docs/kf/wp-542-01/verification.json",
          "sha256": "eca58534577b30f73741b9e471a55cfe0c24eea101c16e9d2c7becf94b7f274c",
          "bytes": 1280
        }
      ],
      "upstream_gate_record": {
        "all_pass": true,
        "adopted_as_verdict": false
      },
      "checks": [
        {
          "id": "C1",
          "name": "source_hash_matches_contract",
          "result": "pass",
          "detail": "recomputed=sha256:a07bad2500aeed73b47222738bffb3d6a70d39a16790e2c991e01f5bbb239b40 declared=sha256:a07bad2500aeed73b47222738bffb3d6a70d39a16790e2c991e01f5bbb239b40 chars=6599 bytes=10333"
        },
        {
          "id": "C2",
          "name": "evidence_quotes_verbatim_in_source",
          "result": "pass",
          "detail": "quotes=18 located=18 missing=[]"
        },
        {
          "id": "C3",
          "name": "upstream_manifest_matches_its_declared_hash",
          "result": "pass",
          "detail": "sha256=5f3b256eb953c08aa112cc6a155d8dc0e5dec40de2f627f24a564f5e115c5f71 declared=5f3b256eb953c08aa112cc6a155d8dc0e5dec40de2f627f24a564f5e115c5f71 bytes=35028 declared_bytes=35028"
        },
        {
          "id": "C4",
          "name": "path_inventory_recall",
          "result": "pass",
          "detail": "source_tokens=36 registered=36 missing=[]"
        },
        {
          "id": "C5",
          "name": "path_inventory_precision_no_invented_paths",
          "result": "pass",
          "detail": "manifest_paths=36 not_traceable_to_source=[]"
        },
        {
          "id": "C6",
          "name": "locators_resolve_verbatim_on_declared_lines",
          "result": "pass",
          "detail": "markdown_line_locators=47 quote_mismatch=0 path_mismatch=0"
        },
        {
          "id": "C7",
          "name": "asset_ids_unique",
          "result": "pass",
          "detail": "assets=51 unique=51 duplicates=[]"
        },
        {
          "id": "C8",
          "name": "resolution_status_uses_declared_vocabulary",
          "result": "pass",
          "detail": "status_counts={'resolved': 1, 'metadata_only': 3, 'unresolved': 47} by_kind_status={'report_markdown/resolved': 1, 'embedded_figure/metadata_only': 3, 'source_code_reference/unresolved': 36, 'data_artifact_reference/unresolved': 4, 'figure_reference/unresolved': 6, 'document_reference/unresolved': 1}"
        },
        {
          "id": "C9",
          "name": "no_claim_marked_verified",
          "result": "pass",
          "detail": "claims=0 verified_marks=0 note=Contract notes allow an empty claims array for task_type 01-asset-registration; no extraction performed."
        },
        {
          "id": "C10",
          "name": "empty_claims_consistent_with_task_type_01",
          "result": "pass",
          "detail": "task_type=01-asset-registration claims=0 (registration-only, no extraction)"
        },
        {
          "id": "C11",
          "name": "task_tree_node_arithmetic_consistent",
          "result": "pass",
          "detail": "L1=8 L2=4 L3=4 sum=16 total=16"
        },
        {
          "id": "C12",
          "name": "task_tree_hour_arithmetic_consistent",
          "result": "pass",
          "detail": "L1=136 L2=50 L3=92 sum=278 total=278"
        },
        {
          "id": "C13",
          "name": "per_layer_parallel_group_memberships_match_node_counts",
          "result": "fail",
          "detail": "declared_group_members_per_layer={'L1': 12, 'L2': 4, 'L3': 4} node_counts={'L1': 8, 'L2': 4, 'L3': 4}"
        },
        {
          "id": "C14",
          "name": "module_verification_status_traceable_to_resolved_artifact",
          "result": "not_run",
          "detail": "PASS-style cells in report=17 (exact 'PASS'=15); unresolved code/data references upstream=40 -> none checkable here"
        },
        {
          "id": "C15",
          "name": "no_numerical_result_vs_numerical_claims",
          "result": "fail",
          "detail": "section 6 states no numerical result exists while sections 3.4/3.5 report 10-point radar scores and a 4-6 point gap band"
        },
        {
          "id": "C16",
          "name": "upstream_self_verification_record_read_not_adopted",
          "result": "not_run",
          "detail": "upstream all_pass=True failed_checks=[]; the upstream gate record is evidence only and is not adopted as this review's verdict"
        },
        {
          "id": "C17",
          "name": "finding_evidence_quotes_verbatim",
          "result": "pass",
          "detail": "checked=18 misses=[]"
        }
      ],
      "inventory": {
        "path_tokens_in_source": 36,
        "manifest_paths": 36,
        "missing_from_manifest": [],
        "extra_in_manifest": []
      },
      "locator": {
        "checked": 47,
        "problems": []
      },
      "identity": {
        "asset_count": 51,
        "distinct_path_strings": 36,
        "distinct_basenames_files": 33,
        "basename_variants": {
          "shell4.py": [
            "tensorfem/shell4.py",
            "shell4.py"
          ],
          "cohesive.py": [
            "tensorfem/cohesive.py",
            "cohesive.py"
          ],
          "dynamics.py": [
            "tensorfem/dynamics.py",
            "dynamics.py"
          ]
        },
        "duplicate_occurrences": []
      },
      "resolution": {
        "status_counts": {
          "resolved": 1,
          "metadata_only": 3,
          "unresolved": 47
        },
        "kind_counts": {
          "report_markdown": 1,
          "embedded_figure": 3,
          "source_code_reference": 36,
          "data_artifact_reference": 4,
          "figure_reference": 6,
          "document_reference": 1
        },
        "kind_status": {
          "report_markdown/resolved": 1,
          "embedded_figure/metadata_only": 3,
          "source_code_reference/unresolved": 36,
          "data_artifact_reference/unresolved": 4,
          "figure_reference/unresolved": 6,
          "document_reference/unresolved": 1
        }
      },
      "report_internals": {
        "nodes": {
          "L1": 8,
          "L2": 4,
          "L3": 4
        },
        "hours": {
          "L1": 136,
          "L2": 50,
          "L3": 92
        },
        "total_nodes": 16,
        "total_hours": 278,
        "group_members_per_layer": {
          "L1": 12,
          "L2": 4,
          "L3": 4
        },
        "groups": {
          "L1": {
            "A": 5,
            "B": 4,
            "C": 3
          },
          "L2": {
            "B": 2,
            "C": 1,
            "A": 1
          },
          "L3": {
            "D": 2,
            "E": 2
          }
        },
        "groupA_members": [
          "F01",
          "F03",
          "F04",
          "F05",
          "V04"
        ],
        "pass_cells": 17,
        "pass_exact": 15,
        "unresolved_code_or_data_refs": 40
      },
      "findings": [
        {
          "id": "F-01",
          "severity": "low",
          "blocking": false,
          "statement": "Upstream counts distinct path STRINGS, not distinct files: several files are cited under both a qualified and an unqualified form, so the distinct-path total overstates distinct artifacts.",
          "evidence": [
            {
              "quote": "tensorfem/shell4.py",
              "line": 31,
              "note": "qualified form in the parameter table"
            },
            {
              "quote": "| shell4.py | 4节点MITC4壳 | ✅有测试 | PASS | test_shell4.py |",
              "line": null,
              "note": "same file, unqualified form in the module table"
            },
            {
              "quote": "tensorfem/cohesive.py:32",
              "line": 32,
              "note": "qualified form, second alias group"
            },
            {
              "quote": "| cohesive.py | 两节点cohesive界面 | ✅有测试 | PASS | test_cohesive.py (6 tests) |",
              "line": 85,
              "note": "unqualified form of the same file"
            }
          ],
          "quantities": {
            "distinct_path_strings": 36,
            "distinct_file_basenames": 33,
            "variant_groups": {
              "shell4.py": [
                "tensorfem/shell4.py",
                "shell4.py"
              ],
              "cohesive.py": [
                "tensorfem/cohesive.py",
                "cohesive.py"
              ],
              "dynamics.py": [
                "tensorfem/dynamics.py",
                "dynamics.py"
              ]
            }
          },
          "affected_scope": "upstream summary.distinct_referenced_paths; any downstream per-file inventory metric",
          "recommendation": "Downstream extraction should normalise basenames before counting distinct artifacts and keep the qualified/unqualified aliasing as an explicit alias map."
        },
        {
          "id": "F-03",
          "severity": "medium",
          "blocking": false,
          "statement": "The report's central capability verdicts (module-level PASS) rest on artifacts that all sit outside the resolved set, so registration cannot support them: PASS is producer-asserted, not established.",
          "evidence": [
            {
              "quote": "1. **只读审计**：未修改任何 src/ 代码，所有论断基于源码 + 已有测试",
              "line": 194,
              "note": "evidence basis declared by the report itself"
            },
            {
              "quote": "2. **规模限制**：SI-4 演示为 smoke 级（12颗粒），非工程规模",
              "line": 195,
              "note": "the only quantified demonstration is smoke scale"
            },
            {
              "quote": "3. **GPU 未验证**：dem3d.py 声称支持 CUDA，但 cell list 可能同步阻塞",
              "line": 196,
              "note": "GPU support asserted without a runnable check"
            },
            {
              "quote": "4. **物理精度**：coupled_hull.py 的 `physical_accuracy_qualified` 硬编码为 False",
              "line": 197,
              "note": "one module self-declares physical_accuracy=False"
            }
          ],
          "quantities": {
            "pass_style_cells": 17,
            "exact_PASS_cells": 15,
            "unresolved_code_or_data_refs": 40,
            "resolution_status_counts": {
              "resolved": 1,
              "metadata_only": 3,
              "unresolved": 47
            }
          },
          "affected_scope": "report sections 3.1/3.2 maturity tables; any downstream object asserting solver maturity",
          "recommendation": "Task 03 must record these as producer-asserted (partially-supported/unresolved) unless TensorFEM/TensorDEM sources resolve; do not promote them to supported."
        },
        {
          "id": "F-04",
          "severity": "medium",
          "blocking": false,
          "statement": "The task-tree summary table is internally inconsistent: the L1 row lists parallel groups whose member counts sum well above that layer's node count, and the L2 row re-lists the same groups, so the layer/group mapping cannot be reconstructed from the report alone.",
          "evidence": [
            {
              "quote": "| L1 基础能力 | 8 | 136h | A(5并行), B(4), C(3) |",
              "line": 156,
              "note": "L1 node count vs declared group member counts"
            },
            {
              "quote": "| L2 验证锚 | 4 | 50h | B(2), C(1), A(1) |",
              "line": 157,
              "note": "L2 re-lists subsets of A/B/C"
            },
            {
              "quote": "- **立即启动（组A）**：F01, F03, F04, F05, V04 — 5个任务可并行",
              "line": 172,
              "note": "group A membership enumerated in prose (5 members, one of them a V node)"
            }
          ],
          "quantities": {
            "node_counts": {
              "L1": 8,
              "L2": 4,
              "L3": 4
            },
            "declared_group_members_per_layer": {
              "L1": 12,
              "L2": 4,
              "L3": 4
            },
            "groupA_members": [
              "F01",
              "F03",
              "F04",
              "F05",
              "V04"
            ]
          },
          "affected_scope": "report sections 4.1/4.3 scheduling plan; any extraction of task-tree structure from text",
          "recommendation": "Extract the task tree only from artifacts/fem_dem_task_tree.json (currently unresolved) and treat the table's group columns as ambiguous until that JSON resolves."
        },
        {
          "id": "F-05",
          "severity": "medium",
          "blocking": false,
          "statement": "Section 6 declares no numerical result exists, yet sections 3.4/3.5 assert 10-point radar scores and a '4-6 point' gap band with no rubric, sample or baseline; those numbers are unfalsifiable as published.",
          "evidence": [
            {
              "quote": "本单为 **能力盘点与任务规划**，无数值计算结果，故无误差判定",
              "line": 216,
              "note": "section 6 disclaimer"
            },
            {
              "quote": "整体差距在 4-6 分（10分制）",
              "line": 126,
              "note": "quantitative gap claim"
            },
            {
              "quote": "TensorFEM 在时间积分(7)和断裂(6)方面较强，但在自适应(1)、并行(2)、工程规模(2)方面严重不足",
              "line": 124,
              "note": "per-dimension scores without a rubric"
            }
          ],
          "quantities": {
            "stated_gap_band": "4-6 / 10",
            "rubric_found": false
          },
          "affected_scope": "report sections 3.4, 3.5, 6; any downstream claim citing scores or the gap band",
          "recommendation": "Treat radar scores as illustrative; require the rubric and per-dimension evidence before any downstream claim uses them, otherwise record them unresolved."
        },
        {
          "id": "F-06",
          "severity": "low",
          "blocking": false,
          "statement": "The acronym expansion offered for SIR is not supported anywhere in the report, while SIR is elsewhere used as a run/series identifier; the expansion must not be propagated as a defined term.",
          "evidence": [
            {
              "quote": "SIR（Suboff Icebreaking Research）",
              "line": 14,
              "note": "the only definition offered"
            },
            {
              "quote": "| SIR5 断裂规模 | 405颗粒, 3560键, 624断裂 | sir5 run_summary.json |",
              "line": null,
              "note": "SIR used as run identifier"
            }
          ],
          "quantities": {
            "definition_source_cited": false
          },
          "affected_scope": "terminology of downstream knowledge objects and glossary entries",
          "recommendation": "Keep SIR unresolved in the glossary until an authoritative definition is cited."
        },
        {
          "id": "F-07",
          "severity": "info",
          "blocking": false,
          "statement": "Priority and blocking level are not in fixed correspondence in the gap matrix (one P1 gap carries the same blocking marker as the P0 gaps), so severity ordering cannot be derived mechanically.",
          "evidence": [
            {
              "quote": "| P1 | GAP-FEM-P1 | 附加质量未接入质量矩阵 | 🔴阻断 | 频率误差 |",
              "line": null,
              "note": "P1 with the blocking marker"
            },
            {
              "quote": "| P0 | GAP-FEM-P0 | Winkler弹性地基板缺失 | 🔴阻断 | SI-4全链 |",
              "line": null,
              "note": "P0 with the same marker"
            }
          ],
          "quantities": {
            "priority_levels": 4,
            "distinct_blocking_markers": 4
          },
          "affected_scope": "report section 3.3 gap prioritisation ordering",
          "recommendation": "No action for registration; downstream should sort by the blocking column, not the priority id."
        }
      ],
      "claims": [
        {
          "claim_id": "r542-01-recall",
          "text": "The upstream asset manifest registers every path-like reference in the report markdown (complete recall, no invented paths).",
          "status": "supported",
          "evidence": [
            {
              "quote": "tensorfem/shell4.py",
              "source_field": "markdown",
              "note": "36/36 matched"
            },
            {
              "quote": "tensorfem/dynamics.py, explicit_dynamics.py",
              "source_field": "markdown",
              "note": "both paths on the same source line are registered"
            }
          ]
        },
        {
          "claim_id": "r542-01-locators",
          "text": "Every markdown_line locator's quote is verbatim on its declared line.",
          "status": "supported",
          "evidence": [
            {
              "quote": "| **合计** | **16** | **278h** | — |",
              "source_field": "markdown",
              "note": "47 locators checked, 0 problems"
            }
          ]
        },
        {
          "claim_id": "r542-01-honest-unresolved",
          "text": "Unresolved references are declared unresolved instead of assumed present or marked verified.",
          "status": "supported",
          "evidence": [
            {
              "quote": "1. **只读审计**：未修改任何 src/ 代码，所有论断基于源码 + 已有测试",
              "source_field": "markdown",
              "note": "resolution counts {'resolved': 1, 'metadata_only': 3, 'unresolved': 47}"
            }
          ]
        },
        {
          "claim_id": "r542-capability-verdicts",
          "text": "The report's module-level PASS verdicts are established (not merely asserted).",
          "status": "unresolved",
          "unresolved_reason": "all module/test source references are unresolved in this worktree; the review ran no TensorFEM/TensorDEM test (out of boundary), so the verdicts cannot be checked here",
          "evidence": [
            {
              "quote": "2. **规模限制**：SI-4 演示为 smoke 级（12颗粒），非工程规模",
              "source_field": "markdown",
              "note": "only quantified demonstration is smoke scale"
            },
            {
              "quote": "4. **物理精度**：coupled_hull.py 的 `physical_accuracy_qualified` 硬编码为 False",
              "source_field": "markdown",
              "note": "one module self-declares physical_accuracy False"
            }
          ]
        },
        {
          "claim_id": "r542-radar-gap-band",
          "text": "The report's 4-6 point capability gap band is a measured/traceable result.",
          "status": "unresolved",
          "unresolved_reason": "no rubric, sample or baseline is given for the 10-point scores, and section 6 declares no numerical result exists",
          "evidence": [
            {
              "quote": "整体差距在 4-6 分（10分制）",
              "source_field": "markdown",
              "note": "quantitative claim"
            },
            {
              "quote": "本单为 **能力盘点与任务规划**，无数值计算结果，故无误差判定",
              "source_field": "markdown",
              "note": "contradicting disclaimer in section 6"
            }
          ]
        }
      ],
      "acceptance": {
        "valid_json": true,
        "schema_pass": true,
        "reviewer_independent": true,
        "upstream_packages_completed": true
      },
      "limitations": [
        "Only registration fidelity is judged; capability truth would require TensorFEM/TensorDEM execution, which is outside this work package's boundary.",
        "The report's own appendix artifacts (artifacts/fem_dem_task_tree.json, runs/m605/*.png) are unresolved in this worktree, so the 16-node/20-edge task tree cannot be checked structurally.",
        "Reviewer shares the repository/worktree with the producer; independence is methodological.",
        "Upstream self-verification record is read as evidence only and is not adopted as this review's verdict."
      ],
      "checks_not_run": [
        "C14",
        "C16"
      ]
    }
  }
}
```
