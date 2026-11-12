# KBM-RCI-F1-ABC 预注册：三臂对照实验设计与批次锚（执行前落盘）

> 任务 15496 · 仓 TensorKnowledge · 生成于 2026-11-12T00:44:04.899146+00:00 ·
> 批次 digest `82f698cf0738271cea0b6af7b59edf631e002c27aa266acda00bae7a5266900d` · prereg_id `9e4e0bf551c63599548c2f9d9ef19b562c1eed0bdbeab5a614ac75a8d18a201f` ·
> 本报告**先于任何臂执行**发布，作为预注册时间戳锚（指标/阈值自此冻结，事后改动须 v2 重锚）。

## ① 案例介绍（背景/对象/参数表）

owner 战略命题：**大量普通 Agent + 合理任务分解/工具/技能/质量治理，能否完成少量强 Agent 难以独立承担的大规模工作？**
本单把它落成一次可预注册、可机器裁定的对照实验：同一批 60 份文档、同一工作包契约、唯一变量=组织方式。

| 参数 | 取值 |
|---|---|
| 批次规模 | **60 份**（来自 m15462 的 200 份分层试点样本，同源上游） |
| 分层键 | content_type × tier（12 单元，Hamilton 最大余数法分配，每单元 ≥1 席） |
| 实抽覆盖 | 单元 12/12，仓 15/15 |
| 层内选样 | sha256(seed\|repo\|path) 升序 + 仓轮转（与路径长度/时间/大小无关，确定性） |
| 分层分配 | analysis|A 5；analysis|B 3；creation|A 3；creation|B 2；research|A 24；research|B 4；research|C 5；information|C 3；analysis|C 3；creation|C 3；information|A 3；information|B 2 |
| 三臂 | A=1 强 Agent 整批（60 份，1 包）；B=20 普通并行（无审核无 Skill，20×3）；C=20 普通+独立审核+Skills（20×3） |
| 工作包总数 | 41（A 1 + B 20 + C 20） |
| 配对设计 | B 与 C 的 doc→package 映射**完全相同**（降低批次噪声，可做配对差分） |
| 模型档位 | A=`strong (Qwen3.8-27B)`；B/C=`ordinary (deepseek-v4-flash)` |

**诚实声明（混淆变量）**：三臂在「模型档位/审核/技能」上是**捆绑**差异（组织方式含配置），
因此不得把臂间差异单向归因于「组织方式单一因子」；报告将并列 B vs C（同模型档，切出审核+Skill 的边际贡献）
与 C vs A（整体产线 vs 单强 Agent）两组对照。

## ② 怎么做的（方法/流程/工具链）

1. **批次构建**（`scripts/rci_f1_batch.py`）：读 m15462 `pilot200/sample.json`（sha256 已入库 `artifacts/rci-f1-abc/source/`），
   按 S1-S4 规则抽 60 份，输出 `batch60.json`（含每篇 sha256 与 digest）。
2. **工作包台账**（同脚本）：A 1×60、B/C 各 20×3（配对），写 `tk_work_packages.json`，
   `verify` 子命令机器校验 14 条不变量（覆盖/配对/digest 一致，全绿）。
3. **预注册**（`scripts/rci_f1_prereg.py`）：五指标定义 + 阈值 + 停止规则 + 缺失数据规则 + 盲审协议 + 分析计划
   全部冻结，prereg_id=sha256(canonical 内容)，绑定批次 digest 与批次文件 sha256。
4. **盲审协议**（`scripts/rci_f1_blind.py`）：sample_id=sha256(seed\|ko_id)[:12]，抹除 lane/package/model，
   结构级去标识检查（禁字段 + 正则），封存 `blind_key.json`（sha256 入预注册）；
   人工≥30 条分层复核表 `human30_sheet.md`；κ<0.6 → M3 降级 WITHHELD。
5. **指标计算**（`scripts/rci_f1_metrics.py`）：只读工件，MI/MO 规则内建，缺数据一律 WITHHELD 不填 0。
6. **派单**（`scripts/rci_f1_dispatch.py`）：A 臂本单直接派发（钉强档 `strong (Qwen3.8-27B)`，
   goal 内联 60 条清单，goal_sha256 落盘）；B/C 交 KBM-RCI-F1-FACTORY 泳道（`task_key=rci-f1-abc-lane-b/c`）。

## ③ 计算结果（预注册时的机器事实，非实验结果）

| 项 | 值 |
|---|---|
| batch_digest | `82f698cf0738271cea0b6af7b59edf631e002c27aa266acda00bae7a5266900d` |
| prereg_id | `9e4e0bf551c63599548c2f9d9ef19b562c1eed0bdbeab5a614ac75a8d18a201f` |
| 工作包数 | 41（lane A/B/C = 1/20/20） |
| 文档槽位 | 每臂 60（三臂共 180 槽位） |
| 不变量检查 | 14/14 PASS（`rci_f1_batch.py verify`） |
| 盲审管线试运行 | 用 m15462 的 278 个 KO 做仪器试运行：278 item 去标识、快照 60/60 sha 校验、零泄漏、人工表 30 席（`artifacts/rci-f1-abc/pilot/`） |

## ④ 结果图

图1 = 批次分层分配 vs 实抽 + 仓覆盖；图2 = 三臂组织设计对照（agent 数/包数/文档槽位）。
实验数据图（成本/产量/准确率/证据完整率）待三臂结算后于 final 报告给出。

## ⑤ 注意点（坑与局限）

- **无臂间质量对照的先行读取**：预注册后只看进度/成本流水，不看臂间质量明细（防中途调阈值）。
- **模型档捆绑**：见①诚实声明；A 臂强档优势不能当组织方式效应。
- **B/C 落地的现实风险**：FACTORY 泳道若未及时接手，B/C 单会以单 Agent 降级执行——回执 `agent_count`
  会暴露这一点，届时按 MO3 记 WITHHELD 或降级判定，不粉饰。
- **M5 首周复用**当时点未到（T+7d），预注册即写死「未到=WITHHELD，禁填 0」。

## ⑥ 误差判定（可判定性）

本单是设计单，尚未产生实验数值，因此不存在「关键量误差 <3%」的对照——**如实声明**：
本阶段可判定的只有机器事实（digest/不变量/去标识/覆盖），逐项已在上表给出且可复算；
实验指标误差判定在三臂结算后按预注册阈值（3pp 非劣、3× 吞吐、单位成本 ≤A）执行，
届时逐项列出并显式回答是否达标。允许失败不允许伪造：不达标即写不达标。

**偏差与理由**：任务书要求「批次定义写入 tk_work_packages（lane=A/B/C）」。平台无 tk_work_packages 表，
本单以实现为工件台账 `artifacts/rci-f1-abc/tk_work_packages.json`（含契约版本、门禁、成本槽位），
与 FACTORY(15495) 的建表口径对齐（package_id/report_id→doc_ids/task_type/status/mission_id/skill_id/lane/gates/cost）。
