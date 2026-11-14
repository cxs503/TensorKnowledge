# WP-12316-01: Matured Mission Deliverables — KF Pipeline Demonstration

## ① 问题与参考值出处

本包演示知识产线（KF）01-asset-registration 工序的完整交付流程：从平台报告记录中登记源资产、生成 asset_manifest.json 与 kf_result 信封、独立验证、发布回平台。

**参考值来源**：ITTC 推荐程序 7.5-02-02-01.4（自航模型试验阻力分解），以及 Tokyo 2015 研讨会 KVLCC2 基准数据。

| 量 | 参考值 | 来源 |
|---|---|---|
| C_T (Re=3.0×10⁶) | 3.82×10⁻³ | ITTC-78 经验公式 |
| C_F (Re=3.0×10⁶) | 2.96×10⁻³ | ITTC-1957 摩擦线 |
| 形状因子 (1+k) | 1.29 | KVLCC2 基准 |

## ② 方法与实现（已完成的真实部分）

本包不执行 CFD 求解，而是登记以下已存在的工件：

- `ke/store.py`：知识引擎存储层（REAL 能力，已在 ke/ 目录下）
- `ke/api.py`：知识引擎 API 层（REAL 能力）
- `scripts/kf_register_*.py` 系列：资产登记脚本（本包新增 kf_register_12316.py）
- `scripts/kf_verify_*.py` 系列：独立验证脚本（本包新增 kf_verify_12316.py）
- `scripts/kf_publish_*.py` 系列：发布脚本（本包新增 kf_publish_12316.py）
- `schemas/asset_manifest.v1.schema.json`：资产清单 schema
- `schemas/kf_result.v1.schema.json`：结果信封 schema

## ③ 参数表（无量纲数完整）

| 参数 | 值 | 单位 |
|---|---|---|
| Re | 3.0×10⁶ | — |
| Fr | 0.142 | — |
| L_pp | 230 | m |
| B | 32.2 | m |
| T | 14.5 | m |
| C_b | 0.810 | — |

## ④ 对照表（ref vs got + 逐项误差）

本包为 01-asset-registration 工序，不产生数值结果对照。对照表留空，由后续 03/04 工序填充。

## ⑤ 收敛性/参数敏感性

本包不执行计算，收敛性分析留待后续工序。

## ⑥ 失败模式与工件

本包为资产登记工序，所有工件均为登记性质（resolved_in_source / referenced_unresolved），无 declared_absent 项。

### 工件清单

| 工件 | 状态 | 说明 |
|---|---|---|
| asset_manifest.json | resolved_in_source | 本包产出，24 项资产登记 |
| kf_result.wp-12316-01.json | resolved_in_source | 结果信封 |
| verification.json | resolved_in_source | 验证结果 |
| fig1_registration_map.png | resolved_in_source | 资产登记映射图 |
| README.md | resolved_in_source | 本包说明文档 |

## 7 复现

```bash
# 1. 登记资产
python scripts/kf_register_12316.py

# 2. 独立验证（离线模式）
python scripts/kf_verify_12316.py --offline

# 3. 发布到平台
python scripts/kf_publish_12316.py

# 4. 运行测试
python -m pytest tests/test_kf_wp_12316_01.py -v
```
