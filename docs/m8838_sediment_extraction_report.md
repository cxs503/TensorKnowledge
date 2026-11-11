# 知识沉淀提取报告：Mission m8381

**任务 ID**: m8838  
**日期**: 2026-11-10  
**状态**: 完成

---

## 1. 案例介绍

**物理背景**：KVLCC2 是 SIMMAN Workshop 基准船型（超大型油轮），用于验证船舶操纵性数学模型。Mission m8381 目标是建立高精度 MMG 模型，将回转直径误差从 +26.6% 收敛到 ≤10%。

**船舶参数**：
- Lpp = 320.0 m, B = 58.0 m, T = 20.8 m, Cb = 0.8098
- 排水量 = 312622 t, Dp = 9.86 m, AR = 112.0 m²

## 2. 方法

**知识提取流程**：
1. 从 ship-performance-platform 仓 agent/m8381 分支（sha 575ecc21）获取源文件
2. 识别 3 类知识：否证（falsification）、校准（calibration）、物理验证（physical_validation）
3. 按四契约结构提取：claim + evidence + provenance + review（review_status=pending）
4. JSON schema 校验 + 引句复现验证

## 3. 计算结果

### 提取的知识条目

| ID | 类型 | 核心陈述 | 误差/基准 |
|----|------|----------|-----------|
| tkc:ship-m8381:turning-circle-deviation | falsification | D/L=0.354 @ δ=35°，基准 3.05，偏差 -88.4% | -88.4% (远超 ≤10% 目标) |
| tkc:ship-m8381:hydrodynamic-derivative-calibration | calibration | 水动力导数校准不足为主因 | 无基准（校准未完成） |
| tkc:ship-m8381:test-suite-validation | physical_validation | pytest 15 项，13 项通过 | 86.7% 通过率 |

## 4. 结果图

本报告为知识提取任务，无数值计算结果图。

## 5. 注意点

**SHA 不一致**：任务规格书列 source_head_sha=97e774bcca，但实际 HEAD=575ecc21。按"禁止编造 sha"规则使用实际 sha。

## 6. 误差判定

| 关键量 | 计算值 | 基准值 | 误差 | 是否<3% |
|--------|--------|--------|------|---------|
| D/L @ δ=35° | 0.354 | 3.05 | -88.4% | **否** |
| 测试通过率 | 86.7% | 100% | -13.3% | **否** |

**HONEST-FAIL**：回转直径精度未达 ≤10% 目标，偏差 -88.4%。

---

**交付物**：
- knowledge/sediment/m8381/claim-*.json (3)
- knowledge/sediment/m8381/evidence-*.json (4)
- knowledge/sediment/m8381/provenance-*.json (3)
- knowledge/sediment/m8381/INDEX.md
- artifacts/m8381_validation_output.txt

**验收**：10/10 JSON 过 schema 校验，引句可复现，INDEX 一致。
