# KBM-RCI-F1-ABC 第二轮报告：把「不可判定」变成「可判定的仪器」

> 任务 m15896 · 仓 TensorKnowledge · 分支 agent/m15896 · 上一轮 m15585 在本锚点 honest-FAIL。
> 本轮性质：**调研结合 + 仪器修复**。判定 = `WITHHELD`（三臂不齐，不许判成立），
> 但把「为什么不可判定」从一句托辞变成了可复算的数字。

## ① 问题设定与基准出处

owner 命题：**大量普通 Agent + 合理分解/工具/技能/治理，能否完成少量强 Agent 难以独立承担的大规模工作？**
锚点验收：A=1 强独做 / B=20 普通并行 / C=20 普通+审核+Skills，同批同契约，五指标
（单位成本 / 产量 / 抽取准确率 / 证据完整率 / 复用），prereg 先行 + 盲审。

基准（ref）出处：预注册 v1 冻结文件 `docs/rci-f1-abc/frozen/prereg.json`
（prereg_id `9e4e0bf5…18a201f`），批次 digest `82f698cf…5266900d`。
统计方法 ref：Blackwelder 1982；Farrington & Manning 1990；FDA 2016 NI 指导；
Cohen 1960 / Fleiss 1981 / Donner & Eliasziw 1992（κ）；Kish 1965（设计效应）。

**本轮不重跑三臂**，因为复核发现地面根本不成立（4 条硬事实）：

| # | 事实（可复现） | 数字 |
|---|---|---|
| F1 | 干净检出下 v1 测试红 | 修复前 **5 failed / 4 passed** → 修复后 **9 passed** |
| F2 | 冻结语料/批次/预注册不在版本控制内 | `artifacts/` 被 `.gitignore` 忽略 → 快照 0 篇入库 |
| F3 | 承诺的独立反查器不存在于主干 | `scripts/rci_f1_verify.py` 缺失（只在别的工作树） |
| F4 | B 臂身份已破 | 实测 `agent_count=1`、`mode=degraded-single-agent`、`llm_used=false` vs 设计 20 |

## ② 方法与实现（关键代码指针）

1. **语料入版本 + 逐字节校验**：`scripts/rci_f1_corpus.py`；冻结输入落
   `docs/rci-f1-abc/frozen/{batch60,prereg,tk_work_packages}.json` + `source/pilot200_sample.json`，
   快照落 `docs/rci-f1-abc/snapshot/doc_<digest>/<file>`（60 篇）。
   校验口径＝按字节重算 sha256 与批次清单比对，不符即判死。
2. **独立证据反查器**：`scripts/rci_f1_verify.py`（三关：快照可定位 / sha256 可复算 / 引文逐字落在行区间），
   回执由反查器产出；抽取器自报只用于算 `selfreport_inflation`，**不进指标**。
3. **结算器 + 臂身份审计**：`scripts/rci_f1_settle.py`（`arm_identity()` 比对回执 `agent_count/mode`
   与预注册设计，不符 → `DESCRIPTIVE_ONLY`，MO3）。
4. **可判定性仪器**：`scripts/rci_f1_power.py`（NI 把握度 / 最小可证明界 / 需样本量 / κ 自举区间 /
   聚类 deff），并内置**蒙特卡洛独立复算**（两套代码路径）。
5. **MO2 缺陷修复**：`scripts/rci_f1_metrics.py` 的 M1 在 `tokens=None` 时按 0 累加 → 改为 WITHHELD。

## ③ 参数表（本轮的「无量纲数」= 设计与统计参数）

| 参数 | 值 | 来源 |
|---|---|---|
| 批次文档数 N | 60 | 冻结 batch60 `n` |
| 分层单元 / 仓覆盖 | 12 / 15 | batch60 `observed` |
| 臂设计 | A=1 agent，B=20，C=20（C 含独立审核+Skills） | 冻结 tk_work_packages |
| 非劣效界 margin | 3pp（单侧 α=0.025） | 冻结 prereg thresholds |
| 假设参照率 p_ref | 0.90 | 设计假设（非结果数据） |
| claims/文档（lane B 实测） | 6.84（130/19） | `round2/settlement.json` |
| 设计效应假设 ρ | 0.05 / 0.2 / 0.5 | 敏感性分析 |

## ④ 对照表（ref vs got，逐项打勾/打叉）

| 判据（v1 冻结口径） | ref（阈值/设计） | got（本轮实测） | 误差/判定 |
|---|---|---|---|
| 语料完整性（60 篇 sha256） | 60/60 | **60/60**（rate=1.0） | ✅ |
| 干净检出可复算（v1 测试） | 全绿 | 修复前 5 红 → **9 passed** | ✅（有缺陷已修） |
| 臂 B 证据门（locator 反查） | 100% 可反查 | **130/130 = 1.000** | ✅ |
| 臂 B 证据完整率 M4 | lsr×coverage | **1.000**（1.000 × 1.000） | ✅（仅 B 臂，未完成批，不构成臂间比较） |
| 臂 B 产物齐备度 | 每篇 4 件 | **18/19**（B07 一篇缺 evidence/provenance/summary） | ❌ 1 篇 |
| 臂 B 自报偏差 | 0 | **0**（自报 claims_with_locator 与实测一致） | ✅ |
| 臂 B 完成度 | 60/60 | **19/60**（7/20 包） | ❌ 32% |
| 臂 B 身份 | 20 agents | **1 agent / degraded-single-agent** | ❌ 不符设计 |
| 臂 A / 臂 C 产物 | 各 60/60 | **0 / 0**（主干无产物） | ❌ 未启动（MO3） |
| M3 抽取准确率 | κ≥0.6 且人工≥30 | 无盲审回执 | WITHHELD（禁填 0） |
| M5 首周复用 | T+7d | 窗口未到 | PENDING（禁填 0） |
| **3pp 非劣效门可判定性** | 半宽 ≤ 门 | Wilson 半宽 **7.7pp** > 3pp | ❌ **不可判定** |
| n=60 的把握度（真实差 0） | ≥0.8 | **0.079** | ❌ |
| n=60 的最小可证明界 | ≤3pp | **15.3pp** | ❌ |
| 3pp 门所需 n/臂（差 0 / −2pp） | ≤60 | **1570 / 15353** | ❌ |
| κ 人工复核 30 条的半宽 | ≤0.10 | **0.258** | ❌（需 201 条） |

**显式回答「是否 <3%」**：本锚点的关键量是**比率型判据**（非劣效界与 ε），不是物理量误差，
所以「<3%」要按「CI 半宽 / 门宽」来看：n=60 时半宽 7.7pp 是门宽 3pp 的 **2.57 倍** → **不满足**。
唯一可比的连续量是**证据门反查成功率**：130/130 → 相对偏差 **0.0%（<3%）**；
以及**语料校验** 60/60 → **0.0%（<3%）**。这两项达标，判定性相关的三项（把握度/半宽/所需 n）**不达标**。

## ⑤ 敏感性 / 两个以上参数点（收敛与稳健性）

- **把握度 vs n（两个以上分辨率）**：margin 3pp、真实差 0：n=60 → 0.079；n=200 → 0.169；
  n=600 → 0.410；n=1570 → 0.800（`power.json:ni_table` + `min_demonstrable_margin`）。
- **margin 敏感性**：n=60、真实差 0：3pp → 0.079；5pp → 0.147；10pp → 0.447。
- **聚类稳健性**（实测 claims/doc=6.84）：ρ=0.05/0.2/0.5 → deff 1.29/2.17/3.92，有效 n 318/189/105，
  3pp+差 2pp 把握度 0.060/0.050/0.042（设计假设 9.2 claims/doc 时 1.41/2.64/5.10、391/209/108、0.065/0.051/0.042）
  → 换分析单元救不了 3pp。
- **解析 vs 模拟（收敛性）**：解析−模拟偏差 n=60 为 −1.6…−2.1pp，n=200 收窄到 −0.1…−0.3pp → 渐近口径成立。
- **κ 覆盖率**：Fleiss 近似 n=30 实测覆盖 **0.888**；自举 n=30 **0.923**、n=120 **0.944** → 选型改用自举。
- **仪器灵敏度（注入故障）**：篡改引文 / 篡改 sha256 / 整体错行 / 缺 evidence 文件 → 反查器分别判死
  （`tests/test_rci_f1_round2.py::test_verifier_kills_injected_faults`，4 例全过）。

## ⑥ 失败模式与工件

| 失败模式 | 观测 | 工件 |
|---|---|---|
| 语料不入版本 → 仪器不可复算 | 干净检出 5 红 | `docs/rci-f1-abc/{frozen,snapshot}`（本轮新增） |
| 自报数进指标 | B 臂 `claims_with_locator_inprocess` 自数 | `scripts/rci_f1_verify.py`（独立反查，偏差字段公示） |
| 单进程冒充 20 臂 | `agent_count=1`、`degraded-single-agent` | `scripts/rci_f1_settle.py::arm_identity`（机器门） |
| 缺计量按 0 计 → 成本失真 | M1 修复前 REAL（token 当 0） | `scripts/rci_f1_metrics.py` MO2 修复 + 回归测试 |
| 判定规则本身不可判定 | 半宽 7.7pp vs 门 3pp | `docs/rci-f1-abc/round2/{power.json,power.md}`、`METHOD-AND-PREREG-V2.md` P1–P6 |
| 臂 A/C 未执行 | 主干 0 产物 | `settlement.json:blocking`（3 条，逐臂点名） |

**复现命令**

```bash
python scripts/rci_f1_corpus.py verify
python scripts/rci_f1_verify.py --lane B
python scripts/rci_f1_settle.py
python scripts/rci_f1_power.py
python scripts/rci_f1_round2_figures.py
python -m pytest tests/test_rci_f1_abc.py tests/test_rci_f1_round2.py -q   # 23 passed
```

**图件**：`round2/figures/fig1_power_curves.png`（把握度 vs n，含 n=60 设计线）、
`fig2_kappa_precision.png`（κ 半宽 vs 人工量）、`fig3_status_matrix.png`（三臂×五指标状态）、
`fig4_laneB_evidence.png`（B 臂逐篇 claims/locator + 全批缺口）。

**未尽事项（如实申报）**：三臂仍未跑齐——A/C 无产物、B 身份不符；M3/M5 不可得；
因此本锚点判定仍是 `WITHHELD`，**没有任何臂间结论**。下一步（第三轮建议，已在 P1–P6 冻结）：
按 P3 扩批到 ≥1570 份/臂（或明示门值放宽到 ≥15pp）+ 按 P4 把人工复核提到 ≥120 条 + 按 P5 强制臂身份门，
再跑 A/B/C 三臂。