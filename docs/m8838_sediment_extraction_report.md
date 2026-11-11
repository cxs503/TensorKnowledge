# 知识沉淀提取报告：Mission m8381 — KVLCC2 MMG 操纵运动模型 HONEST-FAIL

**任务 ID**: m14529 (返修轮1, 原 m8838)  
**源任务**: m8381 (ship-performance-platform)  
**日期**: 2026-11-11  
**状态**: L2 完成 (impl + entry + run_artifacts)

---

## 1. 案例介绍

### 物理背景
KVLCC2 是 SIMMAN Workshop 基准船型（超大型油轮 VLCC），用于验证船舶操纵性数学模型。Mission m8381 目标是建立 MMG 操纵运动模型框架，将回转直径误差从 +26.6% 收敛到 ≤10%。

### 船舶参数
| 参数 | 值 | 单位 |
|------|-----|------|
| Lpp | 320.0 | m |
| B | 58.0 | m |
| T | 20.8 | m |
| Cb | 0.8098 | - |
| 排水量 | 312,622 | t |
| Dp | 9.86 | m |
| AR | 112.0 | m² |

### 模型架构
- **三自由度 MMG 模型**：纵荡(surge)、横荡(sway)、艏摇(yaw)
- **船体水动力**：基于无量纲 PMM 导数 (Yv, Yr, Nv, Nr 及高阶项)
- **螺旋桨推力**：Wageningen B-4 近似 (Kt = Kt0 + Kt_slope·J)
- **舵力**：含舵-桨干扰（Fujii 模型），关键参数：
  - 舵处推力减额: 1-tR = 0.60
  - 舵升力增量: 1+aH = 1.25
  - 舵处加速系数: κ = 0.45
  - 舵处伴流修正: ε = 0.85

### 源单结果（HONEST-FAIL）
| 参数 | 计算值 | 基准值 | 误差 |
|------|--------|--------|------|
| D/L @ δ=35° | 0.354 | 3.05 | **-88.4%** |
| 战术直径 | 113.1 m | 976.0 m | -88.4% |
| 回转角速度 | 13.85 deg/s | ~1.5 deg/s | +823% |

**结论**：模型为概念验证级别，水动力导数校准不足是主要瓶颈。

---

## 2. 方法

### 知识提取流程
1. **源定位**：从 ship-performance-platform 仓 agent/m8381 分支获取源文件
   - SHA: `97e774bcca7e49a3bf17b2500d0fc3a5bd35fbeb`
   - PR: #477 (merged)
   - 模型: qwen3.7-plus

2. **知识识别**：按过滤器命中规则提取 3 类知识
   - `falsification` — 负知识/否证（D/L 偏差 -88.4%）
   - `calibration` — 校准瓶颈（水动力导数未基于 PMM 数据校准）
   - `physical_validation` — 物理验证面（pytest 15 项测试结构）

3. **四契约结构**：
   - **claim**: 原子化知识主张，epistemic_status=draft
   - **evidence**: 逐字引句 + content_hash，从 git objects 切片
   - **provenance**: PROV-O 对齐，记录提取活动
   - **review**: 不产出（生产者不自审）

4. **校验链**：
   - jsonschema 验证（Draft 2020-12）
   - 双向交叉引用一致性
   - 逐字引句 @ SHA 复现
   - 文件 sha256 校验

### 工具链
- `build_sediment_m8381.py`: 构建脚本（入口点）
- `validate_sediment_m8381.py`: 独立验证器（4 门 46 项检查）
- `INDEX.md`: 知识包索引

---

## 3. 计算结果

### 提取的知识条目

| ID | 类型 | 核心陈述 | 证据 |
|----|------|----------|------|
| tkc:ship-m8381:turning-circle-deviation | predictive | D/L=0.354 @ δ=35°，基准 3.05，偏差 -88.4%；主导敏感参数 kappa (-2.602) | 2 evidence |
| tkc:ship-m8381:hydrodynamic-derivative-calibration | causal | 偏差主因是水动力导数（Yv=-0.50, Nv=-0.25）未基于 PMM 试验数据校准 | 2 evidence |
| tkc:ship-m8381:test-suite-coverage | methodological | pytest 5 类 15 项测试覆盖几何/运动方程/回转/敏感度/不确定度 | 1 evidence |

### 验证结果

| 门 | 检查项 | 通过 | 失败 |
|----|--------|------|------|
| G0: 源可用性 | SHA 可用 + 记录数 | 2 | 0 |
| G1: Schema | 11 条记录 jsonschema 验证 | 11 | 0 |
| G2: Quote | 5 条引句 @ SHA 复现 | 5 | 0 |
| G2: Hash | 5 条 content_hash 校验 | 5 | 0 |
| G3: Xref | 10 条交叉引用一致性 | 10 | 0 |
| G3: Index | 9 条 INDEX.md 一致性 | 9 | 0 |
| G4: Draft | 4 条草稿状态 + 无自审 | 4 | 0 |
| **总计** | | **46** | **0** |

---

## 4. 结果图

![验证结果汇总](artifacts/m8381_validation_summary.png)

**左图**: 知识包组成（3 claims / 5 evidence / 3 provenance）  
**右图**: 验证门通过情况（46/46 checks passed）

---

## 5. 注意点

### 局限与适用范围
1. **概念验证级别**：源模型 D/L 偏差 -88.4%，不可用于工程预测
2. **水动力导数未校准**：Yv, Nv 等为手工调整值，非 PMM 试验辨识
3. **需 SIMMAN 数据集**：进一步校准需依赖公开 PMM 试验数据进行系统辨识

### 知识迁移价值
- **否证价值**：明确记录了 MMG 模型在导数未校准时的典型偏差模式
- **敏感度排序**：kappa > epsilon > aH > falpha0 > tR，为后续校准提供优先级
- **测试框架**：5 类测试结构可复用于其他船型 MMG 模型验证

### 纪律遵守
- 零手抄：所有引句从 `git show <sha>:<path>` 切片
- 生产者不自审：review_status=pending，交独立席位
- SHA 一致：使用源单规格书列明的 `97e774bcca7e49a3bf17b2500d0fc3a5bd35fbeb`

---

## 6. 误差判定

| 关键量 | 计算值 | 基准值 | 误差 | 是否<3% |
|--------|--------|--------|------|---------|
| D/L @ δ=35° | 0.354 | 3.05 | -88.4% | **否** (HONEST-FAIL) |
| 测试通过率 | 86.7% (13/15) | 100% | -13.3% | **否** |

**HONEST-FAIL 声明**：源任务 m8381 明确报告回转直径精度未达 ≤10% 目标，偏差 -88.4%。本单为知识沉淀提取，不复现物理计算，忠实记录源单结论。

---

## 交付物清单

### 知识包 (knowledge/sediment/m8381/)
- `build_sediment_m8381.py` — 构建脚本（入口点）
- `validate_sediment_m8381.py` — 独立验证器
- `claim-01.json`, `claim-02.json`, `claim-03.json` — 3 条知识主张
- `evidence-01.json` ... `evidence-05.json` — 5 条证据记录
- `provenance-01.json` ... `provenance-03.json` — 3 条溯源记录
- `INDEX.md` — 知识包索引

### 运行工件 (runs/m8381-sediment/)
- `build.log` — 构建输出
- `validation.log` — 验证输出（46/46 PASS）
- `run_meta.json` — 机器可读元数据
- `README.md` — 运行说明
- `figures_validation.png` — 验证结果图

### 成熟度等级
- **L2**: ✅ impl_files (build + validate scripts)
- **L2**: ✅ entry (build_sediment_m8381.py 可执行)
- **L2**: ✅ run_artifacts (build.log + validation.log + run_meta.json)

---

**任务状态**: L2 完成  
**验收**: 46/46 验证检查通过，零手抄，生产者不自审
