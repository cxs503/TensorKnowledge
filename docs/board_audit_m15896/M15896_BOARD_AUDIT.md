> 交差审计（非重做）。被审交付：`6a4037bdfc96` @ 分支 `agent/m15896`（尚未并入 main）
> 审计工作树 `m15923`；本页与 `docs/board_audit_m15896/*.json` 全部程序化生成。

**裁定：L2（board-audit）** —— 仪器层真实可复现；锚点实验未成立，L3/L4 均有硬阻断。

## 1. 被审对象与基准出处

- 锚点 `KBM-RCI-F1-ABC`：A=1 强独做 / B=20 普通并行 / C=20 普通+审核+Skills，同批同契约，五指标（单位成本/产量/抽取准确率/证据完整率/复用），prereg 先行 + 盲审。
- 任务目标判据原文：`【RCI-F1｜A=1强独做/B=20普通并行/C=20普通+审核+Skills 同批同契约；五指标：单位成本/产量/抽取准确率/证据完整率/复用；prereg先行+盲审】`
- 预注册出处：`docs/rci-f1-abc/frozen/prereg.json`（prereg_id `9e4e0bf5…`，batch_digest `82f698cf…`）；同 digest 的 `docs/rci-f1-abc/PREREG.md` 已在父 commit `3d43e3c` 中（in_base=True）→ 先行性有历史见证。
- **注册裁判**：`tensor_benchmark_cases` 中 `anchor_slug='KBM-RCI-F1-ABC'` → **0 行**（全表 25 行；`repo ILIKE '%Knowledge%'` 亦 0 行）。无机器容差可查，故以**预注册阈值**作 ref，并如实记裁判缺口。

## 2. 三件套取证

| 项 | 结论 | 证据 |
|---|---|---|
| run_artifacts | 存在且入库 | 抽检清单 18 项，缺失 0、未入库 0；入库计数 frozen=4 / snapshot=60 / round2=18 |
| benchmark ref vs got | 有表，且多项越门 | 见 §3：共 18 项判据，PASS 5 / FAIL 9 / WITHHELD-PENDING 2 |
| repro_cmd | 可执行（干净检出） | 23 passed；重跑后工件 sha256 稳定=True、逐叶差异 0/324 |

## 3. ref vs got 逐项对照（基准判据是唯一裁判）

| 判据 | ref | got（本轮实测） | 判定 |
|---|---|---|---|
| 语料完整性 60 篇 sha256 | 60/60（prereg batch n=60） | 60/60 rate=1.00 | PASS |
| 证据门 locator 可反查率 | 100% | 130/130=1.000 | PASS（仅 B 臂） |
| 自报偏差 selfreport_inflation | 0 | 0 | PASS（仅 B 臂） |
| 臂 B 完成度 | 60/60 | 19/60 = 31.7% | FAIL |
| 臂 B 产物齐备度 | 每篇 4 件 | 18/19 | FAIL |
| 臂 B 身份（agent_count=20 普通 Agent） | 20 / 非 degraded | [1] / ['degraded-single-agent'] / identity_match=False | FAIL |
| 臂 A 产物 | 60/60 | 0 篇 | FAIL（未启动） |
| 臂 C 产物 | 60/60 | 0 篇 | FAIL（未启动） |
| M3 抽取准确率 κ≥0.6 且人工≥30 | κ≥0.6 且人工≥30 条 | WITHHELD:None | WITHHELD |
| M5 首周复用 T+7d | T+7d 窗口内复用率>0 | PENDING:None | PENDING |
| 3pp 非劣效门可判定性（半宽≤3pp） | ≤0.030 | 0.0774（7.7pp） | FAIL |
| n=60 把握度（真实差 0） | ≥0.80 | 0.0789 | FAIL |
| n=60 最小可证明界 | ≤0.03 | 0.1534 | FAIL |
| 3pp 门所需 n/臂（差 0 / −2pp） | ≤60 | 1570 / 15353 | FAIL |
| κ 人工 30 条半宽 | ≤0.10 | 0.2584 | FAIL |
| 注册基准行 tensor_benchmark_cases(anchor) | ≥1 行机器可裁 | 0 行 | FAIL |
| 报告六段齐全 | 6/6 | 6/6 | PASS |
| 可复现（干净检出重跑） | 全绿 + 工件逐叶一致 | 23 passed；差异叶=0/324 | PASS |

**显式回答「是否<3%」**：连续量有两项在 3% 内 —— 语料校验 60/60（相对偏差 0.0%）、证据门反查 130/130（0.0%）。但锚点关键量是**3pp 非劣效门的可判定性**：n=60 的 Wilson 半宽 7.7pp 是门宽 3pp 的 **2.58 倍**（超门 158%），**不满足**。

## 4. 方法与独立复算

- 干净检出：`git -C /root/tp-agent/work/m15896 archive 6a4037b | tar -x -C <tmp>`，不读工作树脏状态。
- 基线重建：父 commit `3d43e3c` 干净检出跑 v1 测试 → **5 failed / 4 passed**，与交付自称「5 红 4 绿」逐数吻合（F1 反核通过）。
- 缺陷根因：父 commit 内 frozen/=0 文件、snapshot/=0 文件、`scripts/rci_f1_verify.py` 存在=False → 「仪器不存在」是真事实而非托辞。
- Wilson 半宽独立复算（p=0.90, n=60, z=1.96）：0.0774 vs 工件 0.0774（Δ0.0000）。
- 确定性：power.py 重跑与原 `power.json` **逐叶 0 差异**（MC 种子固定 20261112），settle 同；事后工件 sha256 未变=True。
- 判级规则（机器判）：L1=True L2=True L3=False L4=False。
  - L1 通过：23 测试全绿；Wilson 半宽独立复算 0.0774 vs 工件 0.0774（Δ0.0000）
  - L2 通过：4 个真实仪器（corpus/verify/settle/power）输入→计算→输出，干净检出重跑工件 sha256 不变、逐叶差异 0
  - L3 阻断：scripts/ 与 tests/ 之外无调用者（repo=0, ci=0, platform=0）
  - L4 阻断：注册基准行 0 条；三臂不齐（A=0 篇、C=0 篇、B identity_match=False）→ 五指标无臂间数据

## 5. 独立复核发现的偏差（adversarial findings）

| id | 级别 | 类型 | 事实 | 影响 |
|---|---|---|---|---|
| F-1 | minor | report-number vs artifact | {"fleiss_n30": {"report": 0.888, "artifact": 0.8962, "abs_delta": 0.0082}, "boot_n120": {"report": 0.944, "artifact": 0.9396, "abs_delta": 0.0044}} | 定性结论（近似法 n=30 under-cover）不变；但「判据数字零手抄」在这两个数上不成立 |
| F-2 | blocking-for-L4 | referee absent | tensor_benchmark_cases anchor_slug='KBM-RCI-F1-ABC' → 0 行（全表 25 行，TensorKnowledge 域 0 行） | 无注册基准行 → 五指标即便齐也无机器容差可裁；L4 不可授予 |
| F-3 | blocking-for-anchor | arms not executed | settlement.lanes: A docs=0, C docs=0, B docs=19/60；identity.B agent_count=[1] mode=[degraded-single-agent] identity_match=false | 臂间比较零数据；WITHHELD 是唯一诚实结论 |
| F-4 | major | lane B data are not agent data | arms/B/.../provenance.json: extractor='rule-based, deterministic, no-LLM', llm_used=false, tokens=null, _exec_metrics wall_seconds=0.028/3 篇 | 数字度量的是反查器+确定性抽取器，不是 20 个普通 Agent；报告以身份门自认不可用于 H1–H3（诚实），但不得据此评 L4 |
| F-5 | minor | prereg provenance (check passed) | frozen/prereg.json 首入库于本轮 6a4037b；父 commit 3d43e3c 的 PREREG.md 已含同一 batch_digest 82f698cf… 与 prereg_id 9e4e0bf5…（in_base=True） | 判据（3pp 非劣效 / κ≥0.6）确为事前冻结，非事后补写 |
| F-6 | minor | artifacts gitignored (root cause, fixed) | 父 commit 内 frozen/=0、snapshot/=0、verify 脚本存在=False；.gitignore 第 5 行 artifacts/ | 本轮已修（入库 frozen=4、snapshot=60、round2=18）；本审计据此刻意落 docs/ 而非 artifacts/ |
| F-7 | blocking-for-level | acceptance vs attainment | decided_by=eco_admin；实测 5 项 PASS / 9 项 FAIL / 2 项 WITHHELD-PENDING | 接受=交付验收（工件齐、可复现）≠ 锚点达成；级别按功能实质 L2 |

无「虚标高级」情形：交付报告自报 WITHHELD，未声称臂间结论；本轮 L2 比 accepted=true 更严。

## 6. 范围与局限

- 臂 B 回执由 no-LLM 确定性抽取器产出（`llm_used=false`），M2/M4 实测值只描述仪器，不描述「20 个普通 Agent」；报告已用身份门（identity_match=false）自认不可用，本审计采纳。
- 报告 ⑤ 两处 κ 覆盖率与 `power.json` 有 0.004–0.008 偏差（F-1），属转写误差，不改结论。
- 本审计不重跑任何臂（A/C 无产物、B 无 LLM 调用，无从重跑），只核验仪器与判据。
- `tensor_benchmark_cases` 缺该锚点行是台账缺口而非交付缺陷，但它使 L4 在机器口径上不可能成立。
- 图件说明：本单为**核验/台账类**任务，不含新的场量或曲线数据；判定性曲线数据已在被审工件 `round2/figures/fig1_power_curves.png` 内，审计侧以数值表（§3）为准，故不另生成图。

## 7. 处置

L2 落表；gate 记 confirmed（仪器层确认真实），**不作锚点消账**：锚点 `KBM-RCI-F1-ABC` 仍为 WITHHELD，待第三轮按 prereg P3–P5 扩批至 ≥1570 份/臂、人工复核 ≥120 条、强制臂身份门后重裁。
