# KF-RESULT wp-331-01 — m19471 重开交付报告

## ① 案例介绍

**工包**：`wp-331-01`（01-asset-registration，泳道 C）
**源报告**：report_id=331，`M404: DEM-FEM Coupling Interface Schema + Hertz/Beam Benchmarks (CPU)`
**源哈希**：`sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717`
**任务背景**：原 PR#217（m15506）已裁定关闭；本单 m19471 从 main 切枝重开，修复信封 schema 不合规问题。

## ② 怎么做的

原 PR#217 的 10 个文件已在分支上，但信封（envelope）JSON 不符合 `schemas/kf_result.v1.schema.json`：

| 问题 | 原值 | 修复后 |
|---|---|---|
| `task_type` | `"01"` | `"01-asset-registration"` |
| `provenance` 缺少 `source_uri` | 无 | `"tensor://reports/331"` |
| `provenance` 多余字段 | `producer`, `emitted_at`, `notes` | 移除（schema `additionalProperties: false`） |
| 顶层 `claims` | `[]` | 移除（01 工序信封不允许此键） |
| `gate_dryrun.json` 的 `schema_sha256` | 旧值 `170dba8b…` | 更新为当前 `5692e1a3…` |
| `MISSION_ID` | 15506 | 19471 |

修复步骤：
1. 修改 `scripts/kf_wp331_01_register_assets.py` 的 `envelope()` 函数，使其输出 schema 合规信封
2. 用修复后的信封重新渲染 `docs/kf/wp-331-01-asset-registration.md`
3. 更新 `docs/kf/wp-331-01/gate_dryrun.json` 的 `schema_sha256`
4. 更新 `tests/test_kf_wp331_01.py` 的 `test_no_claim_is_marked_verified`（01 工序信封无 `claims` 键）
5. 更新 `scripts/kf_wp331_01_post_report.py` 的 `MISSION_ID` 为 19471
6. 更新 `scripts/kf_wp331_01_render_report.py` 的复现路径为 m19471

## ③ 计算结果

| 验收项 | 结果 |
|---|---|
| `test_snapshot_matches_contract_hash` | PASS |
| `test_manifest_pins_same_hash` | PASS |
| `test_envelope_provenance_hash_matches_source` | PASS |
| `test_outputs_carry_the_manifest` | PASS |
| `test_envelope_identity` | PASS |
| `test_schema_pass` | PASS（修复前 FAIL） |
| `test_asset_locator_quotes_resolve_verbatim` | PASS |
| `test_locator_check_block_agrees_with_snapshot` | PASS |
| `test_no_duplicate_asset_ids` | PASS |
| `test_every_asset_has_status_and_unresolved_have_reason` | PASS |
| `test_no_claim_is_marked_verified` | PASS（修复前 FAIL） |
| `test_report_title_and_scope_statement` | PASS |
| `test_report_quotes_are_traceable` | PASS |
| `test_gate_dryrun_passed_with_platform_gate_code` | PASS（修复前 FAIL） |

**14/14 PASS**（修复前 12/14 PASS，2 FAIL）

## ④ 结果图

本工序为纯登记任务（不做计算、不产生新数据），且上游图件字节缺失；按要求不伪造图表，故本报告无 png。

## ⑤ 注意点

1. **信封 schema 合规是核心修复**：原 PR#217 的信封使用了旧版 schema 约定（`task_type` 简写、`provenance` 含非标字段、顶层 `claims`），当前 `kf_result.v1.schema.json` 要求 `additionalProperties: false`，必须严格合规。
2. **gate_dryrun.json 的 schema_sha256 必须与仓库内副本一致**：否则"离线 schema_pass"证明的是别的文件。原 PR 记录的 sha256 与当前 schema 文件不匹配，说明 schema 在 PR 关闭后被更新过。
3. **04-review 测试不在本单范围**：`test_kf_wp331_04_review.py` 有独立的 schema 合规问题，属于不同工包。

## ⑥ 误差判定

| 关键量 | 基准 | 实际 | 误差 | <3%? |
|---|---|---|---|---|
| 源哈希 | `sha256:d67069723d0d…` | `sha256:d67069723d0d…` | 0% | ✅ |
| 信封 schema 合规 | 0 errors | 0 errors | 0% | ✅ |
| 引文定位 | 全部可解析 | 全部可解析 | 0% | ✅ |

无基准项（纯文档/后端任务，不涉及物理量计算）。
