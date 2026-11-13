# KBM-RCI-F1-ABC 三臂对照实验（预注册 + 批次 + 盲审 + 指标口径）

本目录：**预注册与实验设计**（先于执行落盘）。工件在 `artifacts/rci-f1-abc/`，派单记录在
`runs/rci-f1-abc/dispatch.json`，机器校验在 `tests/test_rci_f1_abc.py`。

## 一句话

同批 60 份文档（m15462 的 200 份分层试点样本里按预注册规则抽取，12 分层单元/15 仓），
唯一变量=组织方式：**A** 1 个强 Agent 整批（Qwen3.8-27B，1 包×60）；**B** 20 普通并行
（deepseek-v4-flash，免审核免 Skill，20 包×3）；**C** 20 普通 + 独立审核 + Skills（20 包×3）。
B/C 的 doc→package 映射完全相同（配对设计）。

## 工件地图

| 文件 | 是什么 |
|---|---|
| `artifacts/rci-f1-abc/batch60.json` | 批次清单（doc_id/repo/path/sha256/分层），digest 绑预注册 |
| `artifacts/rci-f1-abc/tk_work_packages.json` | 工作包台账（41 包：A 1 / B 20 / C 20），**只读**（sha256 入预注册） |
| `artifacts/rci-f1-abc/prereg.json` | 预注册：五指标/阈值/停止规则/缺失数据规则/盲审协议/分析计划 + prereg_id |
| `artifacts/rci-f1-abc/source/` | 上游 m15462 的 sample.json 与 objects.jsonl（快照 + SHA256SUMS） |
| `artifacts/rci-f1-abc/workpackage_status.json` | 执行期可变状态（mission_id/门禁/成本） |
| `artifacts/rci-f1-abc/runs/<LANE>/<pkg>.json` | 每包执行回执（门禁计数 + 成本），指标唯一输入 |
| `artifacts/rci-f1-abc/blind/` | 盲审包（pack.json / blind_key.json 封存 / human30_sheet.md / corpus 冻结快照） |
| `artifacts/rci-f1-abc/metrics.json` + `metrics.md` | 五指标×三臂结算 + 判定 |
| `artifacts/rci-f1-abc/figures/` | fig1 分层 / fig2 三臂设计 / fig3 指标可得性 |
| `runs/rci-f1-abc/dispatch.json` | 三臂派单（mission_id + goal_sha256 + 模型档） |

## 复算命令（全部确定性）

```bash
python scripts/rci_f1_batch.py build --source artifacts/rci-f1-abc/source/pilot200_sample.json \
    --out-dir artifacts/rci-f1-abc --n 60        # 重建批次 + 工作包（同 seed 同 digest）
python scripts/rci_f1_batch.py verify --out-dir artifacts/rci-f1-abc   # 14 条不变量
python scripts/rci_f1_prereg.py --out-dir artifacts/rci-f1-abc         # 预注册（指标冻结）
python scripts/rci_f1_gate.py --batch artifacts/rci-f1-abc/batch60.json --lane A \
    --package rci-f1-A-A01 --objects <objects.jsonl> \
    --corpus artifacts/rci-f1-abc/blind/corpus --out artifacts/rci-f1-abc/runs/A/rci-f1-A-A01.json
python scripts/rci_f1_blind.py prepare --dir artifacts/rci-f1-abc --objects artifacts/rci-f1-abc/objects
python scripts/rci_f1_blind.py human30 --dir artifacts/rci-f1-abc --n 30
python scripts/rci_f1_metrics.py --dir artifacts/rci-f1-abc            # 五指标 + 判定
python scripts/rci_f1_figures.py --dir artifacts/rci-f1-abc            # 图件
python -m pytest tests/test_rci_f1_abc.py -q                           # 9 项机器校验
```

## 五指标（冻结，改=新 prereg v2）

M1 单位成本（tokens/compute/agent-hours per doc + 固定权重合成指数 U）；
M2 单位时间产量（通过门禁的份数/挂钟小时）；M3 抽取准确率（盲审四字段，κ≥0.6 且人工≥30 才可结算）；
M4 证据完整率（locator 反查成功率 × claim 覆盖率，程序化反查，不采信自报）；
M5 知识复用（首周引用计数，T+7d 结算，未到=WITHHELD 禁填 0）。

判定：H1 质量非劣（−3pp 内）∧ H2 吞吐 ≥3×A ∧ H3 单位成本 ≤A → 规模生产成立；H1 不成立 → 不成立；
关键指标不可得 → WITHHELD。

## 派单状态（2026-11-12）

| 臂 | mission | 模型 | 席位 | 状态 |
|---|---|---|---|---|
| A | 15498 | Qwen3.8-27B（强档） | tp-qw38-14 | running |
| B | 15499 | deepseek-v4-flash（普通档） | tp-ds-5 | running |
| C | 15500 | deepseek-v4-flash（普通档） | tp-impl-5 | running |

B/C 按设计交 KBM-RCI-F1-FACTORY(15495) 泳道（`task_key=rci-f1-abc-lane-b/c`）；
平台无跨 mission 评论端点，交接以本仓工件（批次+工作包台账）为唯一契约来源。

## 诚实边界

- 三臂差异含**模型档位捆绑**（A 强档 vs B/C 普通档），不得单向归因于「组织方式」；
  报告并列 B vs C（切审核+Skill 的边际贡献）与 C vs A（产线 vs 单强 Agent）。
- 截止本单结算时点，三臂均在跑，五指标全部 NOT_STARTED/WITHHELD —— 不预设结论、不填占位数字。
## 第二轮（m15896）：仪器先行

第一轮 honest-FAIL 的复核结论不是「实验失败」，而是「测量仪器不存在」：
冻结语料/批次/预注册全在 `.gitignore` 忽略的 `artifacts/`（干净检出 v1 测试 5 红），
独立反查器 `rci_f1_verify.py` 只在别的工作树，B 臂实测 `agent_count=1 / degraded-single-agent` 却无人审计。

本轮把三件仪器做进主干并逐个注入故障验证：

| 仪器 | 入口 | 验证 |
|---|---|---|
| 语料入版本 + 逐字节 sha256 | `scripts/rci_f1_corpus.py verify` | 60/60；篡改 1 字节即判死 |
| 独立证据反查（禁采信自报） | `scripts/rci_f1_verify.py --lane B` | 130/130；四类注入故障各自判死 |
| 结算 + 臂身份审计 + MO2 | `scripts/rci_f1_settle.py` | agent_count 1≠20 → `DESCRIPTIVE_ONLY`；token 缺失 → M1 WITHHELD |
| 可判定性（非劣效/κ/聚类） | `scripts/rci_f1_power.py` | 恒等/单调/蒙特卡洛双路径复算 |

关键数字（`round2/power.json`）：p≈0.90、n=60/臂 时 Wilson 半宽 **7.7pp** ≫ 3pp 门，
把握度 **0.079**，最小可证明界 **15.3pp**，3pp 门需 n/臂 ≈ **1570**（真实差 0）或 **15353**（−2pp）；
κ 半宽 ≤0.10 需人工 **201** 条。判定仍 **WITHHELD**（A/C 无产物，B 身份不符）。

详见 `round2/RESEARCH.md`、`round2/METHOD-AND-PREREG-V2.md`（v2 追加条款 P1–P6）、`round2/REPORT-round2.md`。
