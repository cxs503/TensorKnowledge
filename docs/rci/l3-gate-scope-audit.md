# L3 验证单作用域审计（对抗性复核）与 v1.1 硬化

> 锚点 **KBM-RCI-S2-SCHEMA** 第 2 轮 | 2026-11-12 | 独立复核对象：v1 的 L3 晋级通道
> 证据：`runs/rci/l3_scope_audit/audit.json`（现网只读）、`tests/test_ko_v1_guard_v11.py`（36 tests）

## 发现（按严重度）

| # | 严重度 | 发现 | 证据 | 影响 |
|---|---|---|---|---|
| D1 | **critical** | v1 的票没有任何主体绑定，`verdict_by` 自由文本、`maturity_verdict_id` 无外键、写入者无核验 → "L3 唯一通道=平台验证单" 名义成立、物理不成立 | 现网 6 张 confirmed 票 `subject_sha256` 全空；一张 `maturity_verdict_id` 被复用最多 4 次 | 任何写库方都能给任意对象发 confirmed 票并晋级 L3 |
| D2 | **major** | v1 未区分「任务级 maturity 裁定」与「对象级裁定」，任务级裁定可覆盖它从未审阅的断言 | 6 条 L3 对象同 mission(15858)、同 verdict、无枚举清单 | 知识"已验证"标签可被任务级结论外溢污染 |
| D3 | **major** | v1 `content_sha256` 只排除自身字段，**包含 `verification`** → 晋级时加验证单会改变对象摘要（自指） | `scripts/validate_ko_v1.py` v1 实现；本轮 v1.1 修正 | 摘要不能用作绑定键，绑定方案在 v1 下无法落地 |
| D4 | **minor** | v1 降级（platform_verified→report_claimed）不校验 reopened 票 | `ko_object_guard()` v1 分支 | 可无票降级，审计链断点 |
| D5 | minor | `oss_inventory`/`oss_solutions`/`negative_knowledge_ledger` 对 TK 服务账号拒绝访问 | psql 实测 `permission denied` | 开源横向检索与负知识检索受限，已改用 API + 文献锚点，OSS 选型待补写 |

## 修复（v1.1，全部库内强制）

- G1 `subject_sha256`：confirmed 票必填（CHECK），晋级需与对象摘要相等（触发器）。
- G2 作用域：`source='maturity_gate'` 票必须有 `maturity_verdict_id` + `mission_id`；
  摘要不等时只认「mission 相同 + `evidence_ref.knowledge_ids` 枚举本对象」。
- G3 降级对价：必须有该对象的 `reopened` 票。
- 历史行：`NOT VALID` 约束 + 视图 `ko_l3_unbound`（6/6 标记 `legacy_ticket_without_subject_digest`）。

## 复核方法与限制

- 独立复跑：`python3 -m pytest tests/test_ko_v1_guard_v11.py tests/test_ko_v1_schema.py -q`；
  数据库面用真 PostgreSQL scratch schema 施加 v1 DDL + v1.1 迁移，正例/反例成对。
- 未跑：KE 服务端到端（服务未运行）；平台重出票（越权）；`maturity_verdicts` 表未直连（无权限），
  故「verdict 286 的具体裁定内容」未核，只核了**票与对象的绑定关系**——这一点不影响 D1/D2 结论。
- 不作为结论的部分：`R3`/六要素实测与 schema-v1 声明基线的差异（口径不同，见 methods-survey-v2 §4）。

## 处置

- 已 approve-with-notes：v1.1 硬化对**新写入**生效；现网 6 条历史 L3 保持原状并进待重核清单。
- 请求平台侧动作：按 `ko_object.content_sha256` 重出 6 张对象级票（本仓不越权改状态）。
