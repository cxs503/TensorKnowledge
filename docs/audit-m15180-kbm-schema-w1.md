# 交差审计 m15180 · KBM-SCHEMA-W1（五类知识卡 schema + 挖掘管道 v1）

**审计单**: m15246（board-audit） · **被审**: m15180（TensorKnowledge，succeeded，PR#50 merged，commit 98b78e0）
**日期**: 2026-11-11 · **审计人**: board-audit（m15246）

## ① 案例介绍

m15180 目标（任务榜第 1 轮）：五类知识卡（方法/参数/失败/基准/代码指针）JSON Schema v1 + LLM 抽取+规则核验管道 + KE API 对齐。
任务自带判据（mission goal 原文）：**schema 文档 + 管道 repro_cmd + 抽样一致率 ≥80%**（抽样依赖 KBM-CLEAN-W1 产出，未就绪先设计后补跑）。

## ② 怎么做的（审计方法）

1. 取证：读 m15180 工作树 /root/tp-agent/work/m15180、report_m15180.json、mission result（API /tensor/missions/15180）、git show 98b78e0（27 文件，2544 行）。
2. 三件套核验：run_artifacts 文件存在性、benchmark 基准裁判、repro_cmd 独立重跑。
3. 测试独立复跑：`python3 -m pytest tests/test_kbm_extract.py -q`。
4. 基准裁判：检索全部本地 DB（/root/tp-agent/*.db、work/*.db、tools/*.db）与 API 端点，查 tensor_benchmark_cases 中 anchor_slug='KBM-SCHEMA-W1'。

## ③ 计算结果（审计数字，全部程序化取得）

| 核验项 | 结果 | 证据 |
|---|---|---|
| 交付文件存在性 | 27/27 存在 | git show --stat 98b78e0 |
| pytest 独立复跑 | **30/30 passed**（0.15s） | 本审计 2026-11-11 复跑 |
| repro_cmd 独立重跑 | **6/6 verified (100.0%)，6 evidence**，卡片集合与提交版一致（仅 namespace/timestamp 差异） | /tmp/kbm_repro2 vs knowledge/kbm/demo-sample/extract |
| run_artifacts | runs/kbm/demo-sample/run_manifest.json（verification_rate=1.0）+ extract/{claims×6, evidence×6, provenance×1, INDEX.md} | 文件存在且与重跑一致 |
| 报告六段 | ①②③④⑤⑥ 齐全；④ 声明「纯文档/后端任务，无场量云图」（合理） | report_m15180.json |
| 基准裁判 | **无注册基准**：tensor_benchmark_cases 表不存在于任何本地 DB，API 无 benchmark 端点，anchor_slug='KBM-SCHEMA-W1' 无 case | 全库检索 + API 探测 |
| 报告发布 | 报告文件已入库，但 tensor_reports API 按 mission_id=15180 查询为空（未发布到 API） | GET /tensor/reports?mission_id=15180 → total=0 |
| 质量门 | server_quality_audit: gate_valid=false, gate_missing_warning=true（过程性缺口） | mission result.evidence |

## ④ 结果图

纯审计/后端任务，无场量云图；核验证据为表格+命令输出（见 ③）。

## ⑤ 注意点

- **基准裁判缺位**：tensor_benchmark_cases 无此锚点 case（表本身不在本地 DB 中）。对 schema/管道类任务，任务自带判据（schema 文档+repro_cmd+抽样一致率）为唯一裁判，本审计按此执行；「抽样一致率 ≥80%」一项**未执行**（依赖 KBM-CLEAN-W1，报告已如实声明待补跑，非虚报）。
- **无平台集成调用方**：KE API 对齐（POST /ko）停留在设计层，无 integration_callers。
- 报告未发布到 tensor_reports API（文件在库，API 查询为空）——过程性欠账，不影响功能实质。

## ⑥ 误差判定

本审计对象为 schema+管道（无数值计算），不适用 <3% 数值误差判据；关键量=测试通过率 30/30、demo 核验率 6/6，均与报告声明一致，**无虚标**。

## 判级结论

**L2（独立功能实现）**：
- 真代码 input→compute→output：`ke/kbm_extract.py`（576 行，main@534，__main__@575）+ `ke/kbm_validate.py`（89 行）+ 5 个 JSON Schema；
- 30 项单元测试独立复跑全绿；repro_cmd 可执行且输出与提交工件一致；
- **未达 L3**：无主求解器/平台集成调用方（KE 对齐仅设计）；
- **未达 L4**：无完整数值算例+误差分析（demo 为合成小样本，非基准算例）。

**裁定**：verdict 已落表（level=2，evidence 全键真实指针）→ 交差成立，m15180 消账；遗留两项过程性缺口（抽样一致率待 KBM-CLEAN-W1 补跑、报告 API 发布缺失）记入后续任务，不改变级别。
