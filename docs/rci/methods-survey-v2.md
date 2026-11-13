# RCI 阶段 2a 第 2 轮 · 方法谱系调研与选型沉淀

> 锚点 **KBM-RCI-S2-SCHEMA** | 2026-11-12 | 仓 TensorKnowledge
> 上游：`docs/rci/schema-v1.md`（v1 对象/状态机）、`docs/rci/interface-spec.md`（三仓接口）
> 本轮新增：`schemas/sql/knowledge_object_v1_1.sql`（硬化迁移）、`docs/rci/l3-gate-scope-audit.md`（现网缺陷）
> 前轮 m15931 honest-FAIL（未留 fail_stage）→ 本单先调研成熟做法，再落实现。

## 1. 调研问题（唯一）

v1 的 L3 通道只问「该对象名下是否存在一张 confirmed 票」，不问「这张票到底裁定了什么」。
成熟体系怎么把**证据/证明**绑定到**被证明的东西**上？三仓接口需要的迁移面在哪？

## 2. 方法谱系（external_anchor 逐条，含采纳/拒绝）

| # | 来源（原文锚） | 关键机制 | 本单采纳 | 落地位置 |
|---|---|---|---|---|
| S1 | W3C **PROV-DM / PROV-O** Recommendation 2013-04-30（`prov:Entity/Activity/Agent`、`prov:wasDerivedFrom`、`prov:generatedAtTime`） | 证据与被证实体是不同节点，靠派生边相连，不合并 | 采纳：`ko_evidence`/`ko_verification` 与 `ko_object` 分表；`provenance.derived_from` 记上游 | v1 已有，本轮不改 |
| S2 | **in-toto** 规范（Torres-Arias et al., 2019, `subject` + `predicate` 分离） | link/attestation 的 `subject` 携带被证工件的摘要（sha256），predicate 不参与 subject 摘要 | **核心采纳**：票带 `subject_sha256` = 对象内容摘要；验证单不计入主体摘要 | `knowledge_object_v1_1.sql` G1；`validate_ko_v1.content_sha256`（排除 `verification`） |
| S3 | **SLSA Provenance v1**（slsa.dev/spec/v1.0/provenance，`subject[].digest`） | 出处文档必须点名被证工件摘要，否则不可复现 | 采纳：L3 晋级要求摘要相等；不相等时只认「任务级票 + 显式枚举」 | 守卫函数 `ko_object_guard()` |
| S4 | W3C **Verifiable Credentials Data Model 2.0**（`credentialSubject` / `proof` / `issuer`） | 证明与主体分离；签发者身份是凭据的一部分 | 部分采纳：`verdict_by` 记录签发席位；未引入密码学签名（无 owner 令，且现网无 PKI）——列为已知局限 | 文档 §4 |
| S5 | **SHACL** W3C Rec 2017-07-20（closed shapes） | 用机器可执行形状约束替代口头约定 | 采纳其精神：约束写进 PostgreSQL CHECK/触发器 + JSON Schema `additionalProperties:false` | v1 已有，本轮加 3 条 CHECK |
| S6 | **RO-Crate 1.1**（2023）与 **DataCite 4.5** | 打包件与元数据分离；跨库只交换标识符 | 采纳：L0 原件归 TD，TK 只存 `artifact_ref{kind,ref,sha256}`；`relatedIdentifier` 类比三仓 ID 互引 | interface-spec §2 |
| S7 | **Nanopublications**（Groth et al., 2010；Trusty URI） | assertion/provenance/pubinfo 三合一，URI 含内容哈希 → 改内容即改 ID | 部分采纳：内容哈希进对象，但 ID 不含哈希（改名不改 ID 的既有约定优先）；漂移用 `supersedes` 边表达 | schema-v1 §4 |
| S8 | **事件溯源 / append-only ledger**（Fowler 2005；Kreps "The Log" 2013） | 状态=事件折叠；表只增不改 | 采纳：`ko_state_event` 三表禁 UPDATE/DELETE 触发器 | v1 已有 |
| S9 | **FAIR**（Wilkinson et al., *Sci Data* 2016；F1/F2/A1.1） | 持久标识 + 可解析元数据 + 可溯源 | 采纳 F1/F2（`ko:` ID + 机器可读 schema）；A1.1 受限于报告可溯源率（实测 0.74，见 §4） | 本单实测 |
| S10 | 数据库**守卫触发器**模式（Stonebraker & Jampolsky 1991 语义；PG 文档 `plpgsql trigger`） | 不变量由数据库强制，调用方不可绕过 | 采纳：v1.1 的三条规则全部写进触发器/CHECK，不写进倡议书 | `knowledge_object_v1_1.sql` |

**拒绝项**：① 引入向量库/图库（无真实查询需求，违反"派生索引后置"令）；
② 引入密码学签名（无 PKI/owner 令，先留 `verdict_by` + 审计表）；
③ 在 plpgsql 内复算 Python 规范 JSON 哈希（jsonb 文本化与 `canonical_json` 不一致，误报风险高）→
   改为「预计算摘要 + 库内强制相等 + Python 校验器复算」的双保险，局限如实登记（§4-L2）。

## 3. 选型结论（迁移方案）

1. **主体摘要 = 对象知识核**：`content_sha256(doc)` 同时排除 `provenance.content_sha256` 与 `verification`
   （attestation 不属于被证主体，S2/S3）。这条修正了 v1 的隐性缺陷：晋级加验证单会改变对象摘要。
2. **两级绑定**：`subject_scope='object'`（摘要相等，强）与 `subject_scope='mission'`
   （同 mission **且** `evidence_ref.knowledge_ids` 枚举本对象，弱但可审计）。
3. **历史数据不静默放过**：v1.1 迁移用 `NOT VALID` 约束 + 视图 `ko_l3_unbound` 暴露，标 `needs_reverification`，
   由平台重出票消除；不自动降级（owner 铁则：状态只由平台改）。
4. **降级对价**：`platform_verified → report_claimed` 必须持该对象的 `reopened` 票，否则触发器拒绝。

## 4. 现网实测（数字全部程序化产出，零手抄）

来源：`scripts/ko_v1_gate_audit.py`（`runs/rci/audit_gate/summary.json`）、
`scripts/ko_v1_l3_scope_audit.py`（`runs/rci/l3_scope_audit/audit.json`）。

| 指标 | 参考值（schema-v1 §3.2 声明） | 实测 N=25 | 实测 N=100 | 判读 |
|---|---|---|---|---|
| 报告引用 artifacts/runs 路径（R3） | 55.2% | 80.0% | 74.0% | 高于基线；样本为**最近** N 份，越新越规范（选择偏差，见下） |
| 六要素齐全率 | 46.9% | 68.0% | 39.0% | N=100 与基线差 −7.9pp（相对 −16.8%），量级一致 |
| E-TR 报告级上界 | ≈0.47 | 0.52 | 0.28 | 分辨率敏感：N=25 与 N=100 差 24pp → 上界**不可**用单一小样本声张 |
| L3 对象数 / 票数 | — | — | 6 / 6 | 全部 `agent/m15858` 生产 |
| 带主体摘要的票 | — | — | 0 / 6 | **v1.1 视图标记 6/6 `needs_reverification`** |
| 单一 maturity 裁定被复用次数 | — | — | 最多 4 | 一张任务级裁定背书多个对象 |

**判读（诚实）**：`R3`/六要素的实测高于声明，二者口径不完全相同（声明为全库 9637 份，实测为最新 N 份，
且 facet 匹配为关键词启发式），因此**不作为基线被推翻的证据**，只作为"同量级、方向一致"的交叉验证。
真正需要注意的不是这两个数，而是 `L3 票 0/6 带主体摘要`——这是 v1 的**结构性**缺陷，不是采样噪声。

## 5. 局限与下一步

L1 现网 6 条 L3 对象需平台按 `ko_object.content_sha256` 重出票（脚本已给视图，出票属平台权限，本单不越权）。
L2 plpgsql 不能复算规范哈希，摘要真实性依赖 Python 校验器在摄取时复算 + 库内相等强制。
L3 未引入签名/签发者证书；`verdict_by` 为自报字段，仅在审计层面可追责。
L4 oss_inventory / oss_solutions / negative_knowledge_ledger 三表对本仓服务账号 `permission denied`
（实测），故开源横向与负知识检索改用平台 API + 公开文献锚点，OSS 选型以 `docs/rci/oss_solutions_seed.sql` 落盘待平台补写。
