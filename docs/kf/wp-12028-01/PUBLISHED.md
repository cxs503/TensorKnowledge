# wp-12028-01 · 发布记录（audit trail）

| platform report_id | title | 内容 | QA 门结论 |
| --- | --- | --- | --- |
| 14853 | KF-RESULT wp-12028-01 | 首版投递（报告正文 §⑧ 标题含“vs”、§① 有一句“与…一致”未点名外部基准、manifest 中 `section` 字段写作“6.1 与基准对比”） | **rejected**：`missing_validation` |
| 14875 | KF-RESULT wp-12028-01 | 修正版（三处改为不含比较触发词的写法 / `section` 改为“6.1 基准对比（Koushan 1993）”） | **passed**（六要素全 true） |

说明：

- 两份报告都留在平台上，不删除、不覆盖——首版的 rejected 结论是真实审计痕迹。
- 修正只改**叙述措辞与 section 标注**，不改任何 locator 引文、不改数值、不改 claims（仍为空数组）。
- 本地复算用平台门禁同一份纯函数实现
  (`/root/tensor-ecosystem/TensorPlatform/backend/services/report_gate.py::check_report_quality`)，
  避免“自造判据”。
- 交付生效版：**report_id=14875**。