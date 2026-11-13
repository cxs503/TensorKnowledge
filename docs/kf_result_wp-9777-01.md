# KF-RESULT: wp-9777-01

## 元数据

| 字段 | 值 |
|---|---|
| package_id | wp-9777-01 |
| report_id | 9777 |
| task_type | 01-asset-registration |
| title | 精确 DSM Timoshenko 梁模态验收审计：7/7 判据 PASS、dsbeam 三处缺陷修复、m6117 6.28% 归因闭环 |
| scenario_key | structural-dynamics/dsm-beam-modal |
| mission_id | 8404 |
| source_hash | sha256:d5742ce0c54743d542de8bb36d79891a0cfe8997a1b6032827fa97df251dcbe7 |
| source_chars | 4341 |
| source_lines | 70 |
| asset_count | 11 |
| figure_count | 5 |
| verification_status | not_verified |
| verification_overall | PASS |
| generated_at | 2026-11-13T10:24:06.728633+00:00 |
| producer | kf-worker/m17951 |

## 资产清单

| # | asset_id | kind | name | resolution |
|---|---|---|---|---|
| 1 | r9777:source-markdown | report_markdown | report-9777-markdown | resolved |
| 2 | r9777:figure:01 | figure | fig1_spectrum.png | unresolved |
| 3 | r9777:figure:02 | figure | fig2_mode_shapes.png | unresolved |
| 4 | r9777:figure:03 | figure | fig3_wittrick_williams.png | unresolved |
| 5 | r9777:figure:04 | figure | fig4_m6117_attribution.png | unresolved |
| 6 | r9777:figure:05 | figure | fig5_random_sweep.png | unresolved |
| 7 | r9777:ref:dsbeam.py:L19 | source_code_reference | dsbeam.py | unresolved |
| 8 | r9777:ref:artifacts_m8404_dsm_audit_acceptance.py:L20 | source_code_reference | artifacts/m8404_dsm/audit_acceptance.py | unresolved |
| 9 | r9777:ref:results.json:L20 | data_artifact_reference | results.json | unresolved |
| 10 | r9777:ref:results.json:L22 | data_artifact_reference | results.json | unresolved |
| 11 | r9777:sym:scipy_optimize_brentq:L19 | module_reference | scipy.optimize.brentq | declared_only |

## 验证结果

| # | check | result |
|---|---|---|
| 1 | valid_json | pass |
| 2 | schema_pass | pass |
| 3 | source_hash_matches | pass |
| 4 | source_locator_resolvable | pass |
| 5 | all_assets_span_within_source | pass |
| 6 | no_duplicate_ids | pass |
| 7 | all_claims_have_evidence_or_explicit_unresolved_status | pass |
| 8 | nothing_marked_verified | pass |
| 9 | artifact_hash_matches_envelope | pass |
| 10 | durable_mirror_identical | pass |
| 11 | envelope_source_hash_equals_manifest_hash | pass |
| 12 | scope_single_report | pass |

**Overall: PASS**

## 说明

本包为 **01-asset-registration** 类型，仅做资产登记与指针解析，
不做 claim 提取、不做报告类型分类、不做 verified 标记。
所有数字/哈希均由脚本从实时 markdown 程序化测量，零手抄。

### 独立性声明

markdown re-fetched by this process (fresh login), not read from the local copy only

DSM solver code/tests and figure png files are outside this worktree; this package registers pointers only and does not execute or re-validate the physics

