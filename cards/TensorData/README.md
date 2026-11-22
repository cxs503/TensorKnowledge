# TensorData Governance Method Cards (m27035)

知识卡挖掘·TensorData 治理与溯源规则（GLM 扩编道·短上下文纪律版 W3）。
全部卡通过 /root/tp-agent/kb_schemas/method-card.schema.json 机器校验（jsonschema draft 2020-12），同批卡 id 唯一。

## 卡清单（PR 描述·全部卡名）

| # | id | method.name | 源文件与小节 | 方程数 |
|---|----|-------------|--------------|--------|
| 1 | `tkc:tensordata:agent-provenance-actor-metadata` | Agent provenance actor-metadata attribution | docs/governance/AGENT_PROVENANCE.md §API/§Semantics/§Operational rule (L5-L48) | 4 |
| 2 | `tkc:tensordata:lifecycle-gates-rights-release` | Lifecycle gates with purpose-specific rights release | docs/governance/data-governance.md §Quality dimensions/§Lifecycle gates/§Separation of duties/§Rights and licensing manifest/§Agent production (L9-L76) | 6 |
| 3 | `tkc:tensordata:evidence-gated-migration-triage` | Evidence-gated component triage for platform migration | docs/migration/tensorplatform-inventory-initial.md §inventory rows/§Key architectural conclusions/§Next audit actions (L10-L46) | 6 |
| 4 | `tkc:tensordata:synthetic-scientific-data-provenance` | Synthetic-data labeling and scientific-data controls | docs/governance/data-governance.md §Synthetic data/§Scientific data controls (L37-L41) | 4 |

## 溯源纪律
- 每条 equations[].source 均为 具体文件路径 + 小节标题 + 行号；无出处的推断一律不写。
- 两个源文件在读取显示时头部被裁剪（AGENT_PROVENANCE.md 完整；data-governance.md 可见 L8 起；tensorplatform-inventory-initial.md 可见 L10 起），被裁剪部分（含 A/B/C/D/E 分类图例）未引用、未推断，已在卡 notes 中如实注明并降低相应置信度。
- 逐卡独立作业：读一个文件 → 当场产卡 → 落盘 commit（防长上下文超时纪律）。

生成日期: 2026-11-22
