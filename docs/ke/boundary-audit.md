# 领域语义边界审计（机器生成）

- 规则：知识资产数据保留领域内容 OK；核心代码硬编码领域词 NOT OK
- 知识资产目录文件：264（代码文件 42）
- 核心代码扫描文件：224
- 核心代码违规：61
- 判定：**FAIL**

## A. 核心引擎硬编码（NOT OK，须迁移）

| 文件 | 命中词 | 迁移方案 |
|---|---|---|
| ke/contract.py | lbm | 词表/算例移入 `knowledge/**` JSON 或 CLI 参数，代码只读数据 |
| ke/export.py | d2q9, lattice\-boltzmann, lbm, lbmpy, taylor\-green | 词表/算例移入 `knowledge/**` JSON 或 CLI 参数，代码只读数据 |
| ke/ingest_client.py | lbm | 词表/算例移入 `knowledge/**` JSON 或 CLI 参数，代码只读数据 |
| ke/migrate.py | lbm | 词表/算例移入 `knowledge/**` JSON 或 CLI 参数，代码只读数据 |

## B. 领域抽取/发布适配器（可接受，需参数化）

| 文件 | 命中词 | 处置 |
|---|---|---|
| ke/sediment_extract.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| ke/sediment_verify.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| ke/tk_eval_loader.py | ship | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/assets_report_figures.py | lbm | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/audit_push_filter.py | ship | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/build_extraction_fixtures.py | ship | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/kb_consume_audit.py | ship | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/kf/build_asset_manifest_5776.py | ice, lbm | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/kf/build_asset_manifest_7840.py | ship | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/kf/build_asset_manifest_wp1204_01.py | ship | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/kf/kf01_register.py | ship | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/kf/publish_5761.py | ice, ship | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/kf/render_report_7840.py | ship | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/kf/render_report_wp1204_01.py | ship | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/kf/render_result_report_5776.py | ice, lbm | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/publish_ke_migration_report.py | lbm | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/register_assets.py | lbm | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/render_sediment_sloshing_doc.py | lbm, sediment, sloshing | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/sediment_claims_m7485.py | sediment, ship | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/sediment_generate_from_oss_lbm.py | kruger, lbm, sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/sediment_generate_from_reports.py | hydrodynamic, sediment, ship | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/sediment_ke_relay.py | lbm, sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/sediment_lib.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/sediment_m5054_build.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/sediment_m5054_figures.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/sediment_m5054_report.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/sediment_m5054_source_guard.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/sediment_m5490_build.py | d3q19, lattice\ boltzmann, lbm, sediment, ship | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/sediment_m5490_entry.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/sediment_m5490_figures.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/sediment_m7485_extract.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/sediment_m7485_figure.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/sediment_sloshing_extract.py | d3q19, lattice\ boltzmann, lbm, sediment, sloshing | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/sediment_spec_m7485.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/sloshing_reference.py | lbm, sediment, sloshing | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/tk_boundary_audit.py | d2q9, d3q19, d3q27, hydrodynamic, ice, kruger, lattice\ boltzmann, lattice\-boltzmann, lbm, lbmpy, sediment, shan\-chen, ship, sloshing, taylor\-green | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/tk_stats.py | lbm, sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/validate_knowledge_assets.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/validate_ontology_v1.py | lbm | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/validate_sediment_packages.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/verify_sediment_m2400.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/verify_sediment_m5490.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/verify_sediment_m7485.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/verify_sediment_sloshing.py | lbm, sediment, sloshing | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/wp1226_publish_report.py | ship | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| scripts/wp1226_register_assets.py | ship | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| tests/test_kbm_extract.py | ship | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| tests/test_ke_api.py | d2q9, lattice\-boltzmann, lbm | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| tests/test_ke_export.py | lattice\-boltzmann, lbm, lbmpy | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| tests/test_ke_migrate.py | lattice\-boltzmann, lbm | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| tests/test_ko_v1_schema.py | d2q9, lbm | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| tests/test_sediment_ke_relay.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| tests/test_sediment_m2953.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| tests/test_sediment_m5054.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| tests/test_sediment_m7437.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| tests/test_sediment_m7485.py | sediment | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |
| tests/test_sediment_sloshing.py | lbm, sediment, sloshing | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |

## 判读口径

- `knowledge/**`、`knowledge-map/**` 的 JSON/MD 是知识资产，领域内容属数据，判 OK。
- 资产目录内若出现 `.py` 且写死领域词，判 NOT_OK（代码而非数据）。
- `ke/` 核心引擎与通用 `scripts/` 出现领域词即违规，需改为数据注入。
