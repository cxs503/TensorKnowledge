# m15887 交差审计：m15858（KBM-RCI-S2-SCHEMA）

verdict 落表：tensor_maturity_verdicts id=405（repo=TensorKnowledge, scope='m15858 KBM-RCI-S2-SCHEMA', level=4, verdict_by=board-audit, gate_state=pending→gate 自动裁定）。
报告：tensor_reports id=15048。

## 独立复核结论（2026-11-12）
- repro_cmd 三段重跑全过：pytest 34 passed；bench PASS（C1 1.0/1.0, C2 1.0/1.0, C3 0.0/0.0, C4 603.1 信息性）；evidence_run gate_level=4 why=[]。
- DDL 闸门探针：gate_state='confirmed' + gate_level=1 票据被 ko_ver_confirmed_shape 拒绝（L3 晋级数据库强制）。
- 工件 6 件齐（docs/rci/m15858/）；报告 15002 六段齐全。
- 基准表：tensor_benchmark_cases 该锚点 0 行（schema 任务，ref=规格条款标注，非物理基准）。
- 缺陷（已披露）：GET /ko/v1/{id}/traceability=500，旧路由 ke/api.py:293 /ko/{ko_id:path} 遮蔽新路由（ke/api.py:442 挂载）。
- 判级 L4：L2 真代码+入口+工件 ✓；L3 平台真调用（2/3 端点）✓；L4 完整算例+误差分析+可复现 ✓。

## 文件
- verdict_m15858.sql：落表 SQL（ON CONFLICT 幂等）
- fig_audit_m15858.png：ref-vs-got + case 级 match rate
- mission_15858.json / report_15002_detail.json：被审对象取证快照
