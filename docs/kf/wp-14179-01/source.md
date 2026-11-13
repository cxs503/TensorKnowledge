# 交差审计：m14897 H5-CALIB-REFLUX（ship-performance-platform）→ verdict **L5**

## ① 案例介绍（审计对象与物理背景）

对象 = mission **m14897**（status `succeeded`，commit `2eb994ce1`，PR **#935** merged）：
「H5-CALIB-REFLUX · 高保真→经验系数回流」。本单 m15056 是**交差核验**（非重做）。

物理问题：平台已有真数值高保真能力（TensorLBM 平板边界层），而 Holtrop 主链的
摩擦线常量 `ITTC57_A = 0.075`（`backend/physics/holtrop/mennen.py:ittc57_cf`）是
1957 年拟合的经验相关线。缺的正是**闭环**：高保真结果如何以可审计、可复算、可回滚的
方式改写这条经验系数。

**高保真源**：TensorLBM `wall_model_les.flat_plate.run_flat_plate` —— 零压梯度平板
湍流边界层的数值解（Spalding 复合壁律 kappa=0.41/B=5.2 + Coles 尾迹 Pi=0.45，
动量积分 dθ/dx=c_f/2 推进），每步真数值、无查表（RANS 级积分边界层，非 DNS/LES）。

**被标定系数**：`ITTC57_A = 0.075`（无量纲）。**消费点**：`mennen.py:ittc57_cf`，
经 `Holtrop1984Input.cf_line_A` 覆盖（缺省 None 保持历史数值逐位不变）。

**验证船型**：KCS（KRISO 集装箱船），几何先过门：Cb_lib=0.6509 vs
nabla/(L·B·T)=0.650499，偏差 0.062% (<2%)；L/B=7.143，B/T=2.981，nabla=52030 m³。

## ② 怎么做的（取证三件套复核，全部重跑，不信报告）

1. **run_artifacts 复核**：`artifacts/m14897_calib_reflux/` 9 个工件（01_hifi_plate_cf.json /
   02_calibration.json / 03_writeback.json / 04_prediction_before_after.json+csv /
   coefficient_store/active.json+ledger.jsonl / figures/fig1+fig2.png / manifest.json /
   MANIFEST.sha256）全部存在且非空，sha256 逐一复算一致（`verify` 通过）。
2. **benchmark ref vs got 复核**：重跑 `python scripts/run_calib_reflux.py run` →
   A_hat=**0.07553932521**（ref 0.075，+0.72%），KCS 设计点 RT **2109.49→2117.58 kN**
   （+0.384%），传递函数 dRt/dA=**0.533**，负控还原误差 **+0.00000%**（G2=4.44e-14）。
   与报告数字逐位一致。
3. **repro_cmd 可执行**：`python scripts/run_calib_reflux.py run`（22s，PASS，5 门全绿）+
   `verify`（第三方复算，ok=true，父链无孤点、账本 prev 链完整、生效快照与账本末条一致）。
4. **单测重跑**：`backend/tests/test_calib_reflux.py` → **17 passed**（31.6s），
   断言不变量（负控还原/夹持边界/篡改必检出/消费者真读账本/同输入哈希逐位一致）。
5. **判级+网关自检**：按 L0–L5 功能实质判级，`maturity_gate.judge` 本地模拟复核
   （claimed L5 → 7 键全过，无缺键）。

## ③ 计算结果（程序化注入，零手抄）

**S1 高保真证据**：站点数 238，Re_x ∈ [2.020e+07, 2.020e+08]，RANS-grade 积分边界层。

**S2 标定**：A_hat=**0.075539**（ΔA/A=+0.72%），σ_A=7.239e-05（0.097%），
残差 RMS=1.456% / max=3.143%，物理带 [0.0700, 0.0800]，clamped=False。
带敏感性（下界扫描）：1e7→0.075539 / 2e7→0.075539 / 5e7→0.076396，ΔA 漂移 <3%。

**S3 回写**：账本 seq=0，entry_sha256=`6fc45dd1…`，生效快照 head_sha256=`3eeab056…`，
prev 哈希链完整，可回滚（追加式，不删不盖）。

**S4 回流前后对照**（KCS，同一 Holtrop 主链，仅摩擦线常量不同）：

| Fn | V [kn] | Cf before | Cf after | ΔCf | RT before [kN] | RT after [kN] | ΔRT |
|---|---|---|---|---|---|---|---|
| 0.150 | 13.85 | 0.0014697 | 0.0014803 | +0.721% | 486.74 | 489.62 | +0.592% |
| 0.180 | 16.62 | 0.0014377 | 0.0014480 | +0.716% | 729.57 | 733.63 | +0.556% |
| 0.200 | 18.46 | 0.0014196 | 0.0014298 | +0.719% | 952.38 | 957.32 | +0.519% |
| 0.220 | 20.31 | 0.0014036 | 0.0014137 | +0.720% | 1245.72 | 1251.63 | +0.474% |
| 0.240 | 22.16 | 0.0013892 | 0.0013992 | +0.720% | 1616.99 | 1623.95 | +0.430% |
| 0.260 | 24.00 | 0.0013761 | 0.0013860 | +0.719% | **2109.49** | **2117.58** | **+0.384%** |
| 0.280 | 25.85 | 0.0013642 | 0.0013740 | +0.718% | 2799.39 | 2808.70 | +0.333% |
| 0.300 | 27.70 | 0.0013532 | 0.0013630 | +0.724% | 3522.12 | 3532.72 | +0.301% |

**设计点（Fn=0.260, 24.00 kn）**：RT 2109.49 → 2117.58 kN（**+0.38%**），
Pe 26047.98 → 26147.97 kW（+0.38%）。传递函数 dRt%/dA% = **0.533**（≈摩擦阻力占位比）。

## ④ 结果图

`artifacts/m15056_audit_m14897/figures/fig1_hifi_vs_reference.png` —— 高保真局部摩阻
vs ITTC-57 局部线与 Prandtl-Schlichting（右=带内偏差）。

`artifacts/m15056_audit_m14897/figures/fig2_prediction_before_after.png` —— 回流前后
KCS 总阻力曲线与逐点 ΔRT。

## ⑤ 注意点（坑 / 局限 / 适用范围）

1. **局部量 vs 平均量**：ITTC-57 是**平均**摩阻线，平板求解器给**局部** c_f；直接相比
   会凭空造出 ~2 倍偏差。必须用平均线的微分恒等式 `cf = A(L-2)^-2 [1-2/(ln10(L-2))]`
   （`ittc57_local_exact`）。
2. **前缘入口过渡段**：求解器从 Re_theta=1e4 起步，Re_x ≲ 1e7 处尾迹未充分建立；
   标定带下界取 2e7（敏感性表 1e7/2e7/5e7 三档，ΔA 漂移 <3%）。
3. **外推**：高保真带覆盖到 Re≈2.0e+08，KCS 26 kn 的 Re≈2.6e9 —— 差 1 个数量级；
   A 被夹在物理带 ±0.0050 内，越界即 `clamped=True` 登记，不静默吸收。
4. **证据等级分层**：高保真源是 RANS 级积分边界层（壁律闭包 kappa/B/Pi 取自文献，
   未在本轮重标定），不是 DNS/LES 解析湍流。它自身与 ITTC-57 局部线平均偏差 +0.98%、
   与 P-S 最大偏差 6.16%。
5. **没有采用不可核证的试验表**：仓库里若干「公开模型试验表」只有 `KRISO_tank` 之类
   标签、无逐项数字化出处（WITHHELD 级），本轮拒绝把它们当高保真锚。
6. **审计侧记账**：m14897 代码在 `/root/tp-agent/work/m14897`（独立 worktree），
   ECO 主 checkout 已陈旧（当前 HEAD 不含 calib_reflux）；本单把重跑工件落在
   `/root/tp-agent/work/m15056/artifacts/m15056_audit_m14897/`，gate 以 m15056 为根可解析。

## ⑥ 误差判定（逐项 vs 基准，显式回答是否 <3%）

| 量 | 基准 | 本次 | 误差 | <3%? |
|---|---|---|---|---|
| 高保真局部 c_f（带内均值） | ITTC-57 局部线 | 数值解 | +0.98% (max 2.83%) | 是 |
| 高保真局部 c_f（带内均值） | Prandtl-Schlichting | 数值解 | -3.50% (max 6.16%) | 否 |
| 反解 A | 已知真值 0.075（负控合成数据） | A_hat | +0.00000% | 是 |
| 标定残差 | 拟合线自身 | 高保真站点 | RMS 1.456% | 是 |
| 回流后 Rt（设计点） | 回流前 Rt | after | +0.384% | 变化量本身 <3%（幅度即结论） |

**结论**：高保真数值解与 ITTC-57 在带内平均偏差 +0.98%，即这条经验线在当前可达 Re
区间已被高保真证实到 **1% 以内**；回流写回的修正是 +0.72%（ΔRt +0.38%）。这不是
「标定出大修正」，而是**机制证明 + 一致性的量化**：若未来高保真源（LES/试验）给出
>3% 的偏差，同一管线会把该偏差以可审计、可回滚的方式写进平台主链。

## 判级（L0–L5 功能实质）

- **L0 文档**：远超（有完整报告+工件）。
- **L1 数学/单元验证**：✅ `calibrate.py` 过原点 LSQ + 负控 + 物理边界；17 单测断言不变量。
- **L2 独立功能**：✅ `calib_reflux` 真代码（输入→计算→输出），无 placeholder。
- **L3 系统集成**：✅ `Holtrop1984Input.cf_line_A` 接入 Holtrop 主链 `mennen.py:ittc57_cf`
  （line 339 `Cf = ittc57_cf(Re, inp.cf_line_A)`），消费者从账本读系数。
- **L4 基准验证**：✅ KCS 完整算例 + 误差分析（RMS 1.456%/max 3.143%）+ 可复现
  （`repro_cmd` + `verify` 双 PASS）。
- **L5 科研工程**：✅ 完整闭环机制（provenance/calibrate/store/predict/pipeline）+
  外部锚（TensorLBM 数值解 + ITTC-1957 + P-S + KCS 几何门）。

**verdict = L5**（完整、集成、可复现的科研工程机制；诚实注记：高保真源为 RANS 级、
修正幅度小，科研价值在机制完备性而非大物理修正）。

**工件**：`docs/m15056_audit_m14897.md`（本审计报告）、
`artifacts/m15056_audit_m14897/`（重跑工件，gate 可解析）、
`reports/m15056_verdict_evidence.json`（落表证据）。
