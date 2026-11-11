# 知识沉淀提取报告：Mission m5490（返修轮1）

**任务 ID**: m14527 (返修 m8834)  
**日期**: 2026-11-11  
**状态**: ✓ 完成（L2 独立功能级）  
**源任务**: m5490 (TensorLBM wave tank benchmark, PR #844)  
**任务键**: tk-sediment-m5490

---

## 1. 案例介绍

### 物理背景
Mission m5490 实现了 TensorLBM 的两相保守 Allen-Cahn (CAC) 相场格子 Boltzmann 波浪水池基准算例。该基准用于验证：
- 两相界面捕捉精度（相场格式）
- 波浪色散关系（Stokes 二阶解析解对标）
- 质量守恒律（液相积分质量漂移）
- 计算成本与稳定性包线

### 几何与参数
| 参数 | 值 | 说明 |
|------|-----|------|
| 网格 | D3Q19, quasi-2D (nz=3) | 准二维配置 |
| kh | {0.7, 1.5, 3.0} | 无量纲波数 |
| ε = ka | {0.02, 0.08} | 波 steepness |
| ρ_l/ρ_g | 10 | 液气密度比 |
| ν | 0.008 | 运动粘度（格子单位） |
| σ | 1e-4 | 表面张力系数 |
| 界面宽度 W | 2 cells | 相场界面厚度 |
| g | 6.5e-3 | 重力加速度（格子单位） |
| 格子单位 | dx = dt = 1, cs² = 1/3 | 标准 LBM 归一化 |

### 源任务状态
- **源分支**: agent/m5490
- **源 PR**: #844 (merged)
- **源 HEAD**: f561cd88f22522280907c208f151412238d7c6f8
- **源状态**: succeeded (honest FAIL)
- **完成时间**: 2026-11-07T14:02:39

---

## 2. 方法

### 知识提取流程

**三阶段管线**（入口脚本 `scripts/sediment_m5490_entry.py`）：

1. **构建知识条目** (`sediment_m5490_build.py`)
   - 从源仓 pinned commit 提取源码片段（git show）
   - 从 `artifacts/wave_tank/results.json` 复算所有数值（零手抄）
   - 生成 7 claims + 30 evidence + 7 provenance 记录
   - 每条 evidence 的 quote 从源文件逐字切片（content_hash = sha256）
   - jsonschema 校验（Draft 2020-12）

2. **独立验证** (`verify_sediment_m5490.py`)
   - G1 schema: 所有记录通过 schema 校验
   - G2 quote: 每条引句可在源文件 grep 复现
   - G3 index: INDEX.md 与记录一致
   - G4 draft: 无自提升（review_status=draft）
   - **121 项检查全部通过**

3. **生成运行工件** (`generate_m5490_artifacts.py`)
   - 从 pinned commit 提取 results.json 和 npz 数据
   - 生成 3 张可视化图（criteria summary, mass drift, knowledge summary）
   - 所有数字从源数据程序化注入

### 关键设置
- **零手抄纪律**: 所有数字从 `results.json` 复算，所有引句从 `git show` 切片
- **Schema 强校验**: 13 个 schema 文件（claim/evidence/provenance/review 等）
- **独立验证**: 验证脚本不导入构建脚本，完全独立重读磁盘+源仓
- **Draft 状态**: review_status=draft（fold(空 review-event 账本)），无自提升

### 工具链
- Python 3.11 + jsonschema + referencing + matplotlib + numpy
- Git (读取 pinned commit 对象)
- TensorLBM 源仓（任意包含 f561cd88 的 worktree）

---

## 3. 计算结果

### 提取的知识条目

| ID | 类型 | 核心陈述 | 关键数字 |
|----|------|----------|----------|
| tkc:tensorlbm:wave-tank-two-probe-dispersion-refuted | hypothesis (falsification) | H1 被否证：两点法相速度验证到 1% 以内 | C1b 误差 7.0%/19.0%/17.6% (kh=0.7/1.5/3.0)，远超 1% 阈值 |
| tkc:tensorlbm:wave-tank-effective-gravity-cac | causal (root_cause) | CAC 两相模型有效重力 g_eff = 0.9g | 波长偏差 -11% (89 vs 100.5 格) |
| tkc:tensorlbm:wave-tank-complex-amplitude-convention | causal (root_cause) | 复振幅时空约定弄反导致符号翻转 | 首轮 c = -0.24 (理论 0.25)，KR = 6000% |
| tkc:tensorlbm:wave-tank-cac-mass-conservation | descriptive | CAC 格式质量守恒成立 | 最差 0.37 %/周期 < 0.5 %/周期阈值 |
| tkc:tensorlbm:wave-tank-cost-criterion-record-inconsistency | descriptive | C7 headline 与机器判据不一致 | 1/8 算例超阈（pass=False），headline 称"通过" |
| tkc:tensorlbm:wave-tank-probe-protocol-bottleneck | methodological | 精度瓶颈在测量协议而非求解器场 | 空间拟合 -3.8% vs 两点法 7-19% |
| tkc:tensorlbm:wave-tank-cac-stability-envelope | causal | 稳定性/敏感性包线 | ν=0.004 发散，ν=0.008/0.012 稳定 |

### 机器判据汇总

| 判据 | 阈值 | 实测 | 通过？ |
|------|------|------|--------|
| C1_dispersion | < 1% | 6.0%/8.0%/7.5% | ✗ FAIL |
| C1b_wavemaker_phase_speed | < 1% | 7.0%/19.0%/17.6% | ✗ FAIL |
| C4_mass | < 0.5 %/周期 | 0.37 %/周期 (最差) | ✓ PASS |
| C7_cost | < 1200 s | 1 例超阈 | ✗ FAIL (整体) |

### 交付物清单

**知识条目** (`knowledge/sediment/m5490/`):
- 7 claim records (JSON)
- 30 evidence records (JSON)
- 7 provenance records (JSON)
- INDEX.md (14 KB, 完整索引)
- review-status.json (review ledger)

**运行工件** (`knowledge/sediment/m5490/`):
- fig_criteria.png (72 KB, 判据汇总图)
- fig_mass_drift.png (202 KB, 质量漂移历史)
- fig_knowledge_summary.png (43 KB, 知识提取汇总)

**实现文件** (`scripts/`):
- sediment_m5490_build.py (737 行, 构建脚本)
- sediment_m5490_figures.py (175 行, 原图表脚本)
- verify_sediment_m5490.py (199 行, 独立验证)
- generate_m5490_artifacts.py (230 行, 工件生成)
- sediment_m5490_entry.py (110 行, **入口脚本**)

---

## 4. 结果图

### 图 1: 机器判据汇总 (fig_criteria.png)
三栏柱状图展示 C1b (相速度误差)、C7 (计算成本)、C4 (质量守恒) 的实测值与阈值对比。
- C1b: 全部超阈（红色柱），阈值线 1%
- C7: 7/8 算例在阈内，1 例超阈（阈值线 20 min）
- C4: 全部在阈内（绿色柱），阈值线 0.5 %/周期

**文件**: `knowledge/sediment/m5490/fig_criteria.png` (71,844 bytes)

### 图 2: 质量漂移历史 (fig_mass_drift.png)
8 个算例的液相质量相对漂移随时间演化，红色虚线为 C4 阈值 ±0.5 %/周期。
- 所有算例漂移在阈值内
- 最差算例 kh0.7_eps0.08 漂移约 0.37 %/周期
- 质量守恒律成立

**文件**: `knowledge/sediment/m5490/fig_mass_drift.png` (202,322 bytes)

### 图 3: 知识提取汇总 (fig_knowledge_summary.png)
水平柱状图展示 4 个关键判据的通过/失败状态。
- C1_dispersion: FAIL
- C1b_wavemaker_phase_speed: FAIL
- C4_mass: PASS
- C7_cost: FAIL (整体)

**文件**: `knowledge/sediment/m5490/fig_knowledge_summary.png` (43,154 bytes)

---

## 5. 注意点

### 踩过的坑

1. **源仓路径问题**: 原脚本硬编码 `/root/tp-agent/work/m5490`，该路径已不存在。
   - **修复**: 入口脚本支持 `TENSORLBM_REPO` 环境变量，默认指向 `/root/tp-agent/work/m8492/TensorLBM`（包含 pinned commit）
   
2. **npz 文件提取**: 原 figures 脚本直接从文件系统读 npz，但源仓 worktree 未检出 artifacts。
   - **修复**: `generate_m5490_artifacts.py` 使用 `git show` 从 pinned commit 提取 npz 到内存（io.BytesIO）

3. **L0 → L2 跃迁**: 原交付仅有脚本（impl_files），无运行工件（run_artifacts）和入口（entry）。
   - **修复**: 
     - 运行入口脚本生成实际知识条目和图表
     - 创建 `sediment_m5490_entry.py` 作为统一入口
     - 生成 3 张 PNG 图作为 run_artifacts

### 局限性

1. **未实现 L3 (integration_callers)**: 未与主求解器或平台侧集成调用。本单目标为 L2，L3 留待后续。
2. **未实现 L4 (benchmark)**: 未做 ref vs got 数值对照基准测试。本单目标为 L2，L4 留待后续。
3. **Draft 状态**: 所有知识条目 review_status=draft，未经独立评审。这是 producer-only 管线的纪律要求（禁止自提升）。

### 适用范围

- 本知识包仅适用于 TensorLBM wave tank benchmark @ f561cd88
- 不推广到 3D 波浪水池、破碎波、其他造波机定律
- 不推广到船舶尺度的海况预测

---

## 6. 误差判定

### 关键量 vs 基准

| 关键量 | 计算值 | 基准值 | 误差 | 是否 < 3% |
|--------|--------|--------|------|-----------|
| C1b 相速度误差 (kh=0.7) | 7.0% | 1% 阈值 | +6.0% | **否** (超阈) |
| C1b 相速度误差 (kh=1.5) | 19.0% | 1% 阈值 | +18.0% | **否** (超阈) |
| C4 质量漂移 (最差) | 0.37 %/周期 | 0.5 %/周期 阈值 | -0.13 %/周期 | **是** (在阈内) |
| 波长偏差 (g_eff 效应) | -11% | 0% (理想) | -11% | **否** (超 15% 不可接受线) |

### 判定说明

1. **C1/C1b (色散/相速度)**: 未达 1% 阈值，误差 7-19%，远超 3% 可接受线。**HONEST FAIL**（源任务已如实申报）。
2. **C4 (质量守恒)**: 最差 0.37 %/周期 < 0.5 %/周期阈值，**PASS**。无外部实验基准，基准取机器阈值（守恒律自洽检验）。
3. **C7 (成本)**: 1/8 算例超阈，整体 **FAIL**。headline 称"通过"仅在 7 个生产算例子集意义上成立。
4. **波长偏差**: -11% 源于有效重力效应（g_eff = 0.9g），已定位根因并修复。

### 验证管线

- **Schema 校验**: 44 条记录全部通过 jsonschema (Draft 2020-12)
- **引句复现**: 30 条 evidence 的 quote 全部可在源文件 grep 复现
- **INDEX 一致性**: INDEX.md 与记录完全一致
- **Draft 纪律**: 无 review-event，无自提升

**总结**: 知识提取管线完整运行，121 项验证检查全部通过，交付 L2 级独立功能（impl_files + entry + run_artifacts）。

---

## 附录: 复现命令

```bash
# 完整管线（推荐）
cd /root/tp-agent/work/m14527
TENSORLBM_REPO=/root/tp-agent/work/m8492/TensorLBM \
  python3 scripts/sediment_m5490_entry.py

# 分步执行
TENSORLBM_REPO=/root/tp-agent/work/m8492/TensorLBM \
  python3 scripts/sediment_m5490_build.py
TENSORLBM_REPO=/root/tp-agent/work/m8492/TensorLBM \
  python3 scripts/verify_sediment_m5490.py
python3 scripts/generate_m5490_artifacts.py
```

**预期输出**: 
- `knowledge/sediment/m5490/` 下 44 个 JSON + INDEX.md + review-status.json + 3 PNG
- 验证脚本输出 `121 PASS / 0 FAIL`
- 入口脚本输出 `✓ All stages completed successfully`
