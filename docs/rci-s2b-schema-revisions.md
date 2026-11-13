# ko/v1 → v1.1 修订单（S2b 试点实测驱动）

> 锚点 **KBM-RCI-S2B-PILOT** | 版本 1.0.0 | 2026-11-13 | 仓 TensorKnowledge
> 依据：`docs/rci-s2b-pilot200-report.md`（200 条分层样本 + 10,071 条全样本枚举）
> 数字唯一来源：`docs/rci-s2b-pilot200/{metrics.json,full_frame_rates.json}`
> 状态：**提案 + 已量化影响面**。`schemas/` 与 `scripts/validate_ko_v1.py` 本轮**未改**（改动零字节），
> 修订以内存投影形式在 `scripts/rci_s2b_pilot.py:projected_schema()` 中实现并可回滚。

## 0. 一句话

v1.0 拿仓内真实语料一跑，**10,071 条里 0 条装得进去**（失败因：证据必须带 `report_id`）；按 R1–R6 改后 **10,065 条装得进去（99.94%）**，且 L3 通道一寸未松。所以 v1.1 要改的是「证据怎么定位」「basis 怎么说人话」，不是「验证怎么放宽」。

| 口径 | 样本 n=200 | 全样本 n=10,071 |
|---|---|---|
| strict v1.0 通过 | 0（0.00%） | 0（0.00%） |
| projected v1.1 通过 | 194（97.00%） | 10,065（99.94%） |

---

## R1 证据定位符二选一：`report_id` 或 `locator`

**现象**：仓内 10,238 条 evidence **无一条**带 TP `tensor_reports.id`，全部是 locator 型（`code-location` / 报告切片），并用 `git:<repo>@<commit>` 或外部 `url` 钉扎。v1.0 `EvidenceRef.required` 含 `report_id` ⇒ 100% 拒绝。

**证据**：`metrics.json → strict_v1.blockers.R1_evidence_locator = 200/200`；全样本 0/10,071 通过。这是**唯一的全局阻断因**。

**修订（v1.1 文本）**：

```jsonc
// $defs.EvidenceRef
"required": ["evidence_type", "artifact_ref"],
"anyOf": [ {"required": ["report_id"]}, {"required": ["locator"]} ],
"properties": {
  "report_id": {"type": ["integer", "null"], "minimum": 1},
  "locator": {
    "type": "object",
    "required": ["locator_kind", "value"],
    "properties": {
      "locator_kind": {"enum": ["code_location", "dataset", "analytic_derivation",
                                "experimental_data", "report_span", "literature"]},
      "value": {"type": "string", "minLength": 1},          // 例 pylbm@f9f5d16 analysis/x.py:14-115
      "content_sha256": {"$ref": "#/$defs/Hex64"},           // 见 R5
      "content_sha256_kind": {"enum": ["source_file", "quote_span"]},
      "quote": {"type": "string", "minLength": 15},
      "citation": {"type": "string"},
      "persistent_id": {"type": "string"}                    // git:<repo>@<sha> / url / doi
    }
  }
}
```

**影响面**：解锁全部 10,071 条对象的证据字段（前提是其余条款同时满足）；单独上 R1 时 projected 通过率 ≈ 97%（样本），剩余失败见 R3。

**不变量（防放水）**：`verification_status='report_claimed'` 仍要求**至少一条** `report_id` 型证据（投影里显式实现，见 `validate_projected()`）；`platform_verified`（L3）通道**完全不受 R1 影响** —— 仍只认平台验证单（`gate_state='confirmed'` ∧ `gate_level>=2`）且需三闸全绿。

---

## R2 `confidence.basis` 增补 `code_inspection` / `dataset_locator`

**现象**：88.05% 的对象（全样本 8,868/10,071）证据是代码位置，v1.0 八档 basis 里**没有一档**能表达「我核过源码」，只能写 `unassessed` —— 这等于把「证据在手」写成「没评估」，是向下失真。

**证据**：`metrics.json → mapping.basis_unrepresentable_v10 = 166/200 = 83.0%`（加权 88.05%，与全样本真值一致）；`review_fields` 中 `confidence.basis` 可派生率 **v1.0 = 0% → v1.1 = 83%**。

**修订（v1.1 文本）**：

```jsonc
"basis": {"enum": ["analytic_reference", "experimental_reference", "benchmark_tolerance",
                   "replicated_run", "single_run", "literature", "expert_review",
                   "unassessed",
                   "code_inspection",      // 读源码/文档定位符后的判定
                   "dataset_locator"]}     // 数据集/场文件定位符
```

**影响面**：解锁 `confidence.basis` 从 0% 到 83%（样本）/ 88.05%（总体）；它同时抬高 RQS 的 `review_derivability` 维度（样本均值 +0.15 权重项）。

**不变量**：`basis='code_inspection'` **不等于** claim 已被验证。状态仍停在 `unverified`；`basis` 描述「置信度怎么来的」，`verification_status` 描述「平台门结论」，两者不得互相替代（v1.0 已有此原则，v1.1 继承）。

---

## R3 源类型词表 → v1 `type` 的**版本化桥接表**

**现象**：语料侧 `claim_type` 词表是 `{definition, descriptive, methodological, mathematical, interpretive, predictive, hypothesis}`，与 v1 `type` 十一档**不是同一套**。硬编码在代码里的映射不可审计、无法演进；`interpretive`/`hypothesis` 在 v1 里**没有诚实落点**（本轮标 `unmapped`，不硬凑成 `capability_claim`）。

**证据**：`metrics.json → mapping.type_unmapped = 4/200`（总体 4/10,071 = 0.04%）；`projected_v1_1.blockers.R3_type_bridge = 4`。

**修订（v1.1 文本）**：不扩 `type` 词表，改为**外置桥接文件** `schemas/type-bridge.v1.json`：

```jsonc
{
  "bridge_version": "type-bridge/v1",
  "mappings": [
    {"source_vocabulary": "tkc", "source_type": "definition",     "type": "definition",      "note": "…"},
    {"source_vocabulary": "tkc", "source_type": "descriptive",     "type": "capability_claim"},
    {"source_vocabulary": "tkc", "source_type": "methodological", "type": "method_card",     "requires_payload": true},
    {"source_vocabulary": "tkc", "source_type": "mathematical",   "type": "method_card",     "requires_payload": true},
    {"source_vocabulary": "tkc", "source_type": "predictive",     "type": "benchmark_card",  "requires_payload": true},
    {"source_vocabulary": "tkc", "source_type": "interpretive",   "type": null,              "note": "无诚实落点，待定"},
    {"source_vocabulary": "tkc", "source_type": "hypothesis",     "type": null,              "note": "假说≠可证伪结论，待定"}
  ]
}
```

校验器按 `provenance.source_vocabulary` 查表；查不到 ⇒ **拒收**（不猜）。桥接文件与 schema 同版本管理，改表要 bump。

**影响面**：消除「同一条语料在不同脚本里被映射成不同类型」的隐性分叉；`unmapped` 从「静默挂 definition」变为**显式拒收 + 待定清单**（4 条进 backlog）。

**不变量**：桥接只决定 `type` 与「是否需要 payload」，**不改 payload 必填性** —— `method_card`/`benchmark_card` 仍须过各自 `*-card.schema.json`；本轮 10 个卡类对象因源记录无方法体/案例体而失败（`payload_card_body = 12` 计数含 strict 侧），这是正确行为，不得为通过率放宽。

---

## R4 `section` 与 `locator` 分工：报告证据要小节锚，非报告证据要定位符

**现象**：v1.0 要求**所有**证据都有 `section.heading`（小节锚）。但代码位置证据没有 markdown 小节，硬塞把 `locator.value` 当 heading 是伪锚点；另 `section.anchor` 有硬字符集（`^[a-z0-9\u4e00-\u9fff][a-z0-9\u4e00-\u9fff-]*$`），源定位符里的 `.py-30-31`/下划线会被拒（第一版适配器在此翻车，见报告 §⑤-4）。

**修订（v1.1 文本）**：

- `report_id` 型证据：**保留** `section.heading` 必填（这条一寸不让，报告小节锚是跨库最脆弱环节）。
- `locator` 型证据：**不要求** `section`；要求 `locator.value` + `locator.content_sha256`（R5）。
- 若两种证据都给了 `section`，`anchor` 必须匹配 `ANCHOR_RE`；`heading` 永远存原文。

**影响面**：非报告证据从「结构上不可能合规」变为「结构上可合规且可追」；样本 215 条证据中 210 条是 locator 型。

**不变量**：报告证据的锚规则不放松；`locate_section()` 的 span + `section_sha256` 校验逻辑不变。

---

## R5 外部源无文件级哈希时：摄取期对**引文切片**自算哈希

**现象**：`knowledge/oss-lbm/evidence/` 的 66 条外部仓证据有 `quote`、有 `url`/`pin`，**没有** `content_hash`。v1.0 的 `artifact_ref.sha256` 只能填文件级哈希，填不出就是空 —— 「没哈希」与「不内容寻址」被混为一谈。

**证据**：`metrics.json → evidence.gates.quote_span_hashed = 5`（样本内）；`by_facet.oss-lbm` 在只有 R1/R2/R4 时 projected 通过 0/4，加 R5 后 4/4。

**修订（v1.1 文本）**：`locator.content_sha256` 允许两类来源，用 `content_sha256_kind` 显式区分：

- `source_file`：原件字节哈希（首选，权威）；
- `quote_span`：`sha256(normalize(quote))`（退化档：钉住**引用文本**而非文件），要求 `quote` 长度 ≥ 15 且 `persistent_id`/`url` 非空。

**影响面**：解锁 oss-lbm / sediment 类外部证据的合规路径；证据闸 `content_addressed` 从 0 提到 215/215（样本）。

**不变量**：`quote_span` 档**不足以**支撑 `report_claimed`（仍需 `report_id` 型证据），也不足以支撑 L3；它只让对象在 L1 层合法、可查、可复核。

---

## R6 定位可解析性：接受外部 `@<commit>` 钉扎

**现象**：外部仓证据的 `locator.value` 形如 `pylbm@f9f5d16 analysis/equivalent_equation.py:14-115`，仓内无从 `os.path.exists` 校验；若只认「仓内文件存在」，这类证据会被判不可追溯（第一版 E-TR 因此只有 2.33%）。

**修订（v1.1 文本）**：证据可追溯三闸的第三闸定义为「**地址可解析**」，三选一即可：

1. `citation` 在仓内工作树存在（`repo_path`，最强）；
2. `artifact_ref.commit` 非空（`git:<repo>@<sha>` 钉扎）；
3. `locator.value` 内嵌 `@<7–40 位 hex>` 的外部仓 pin。

**影响面**：样本 E-TR 77.67% → 88.37%；全样本 87.67% → 88.15%（`full_frame_rates.json`）。三闸分解见 `metrics.json → evidence.gates`。

**不变量**：三闸仍是**与**关系（内容哈希 ∧ 引文 ∧ 地址可解析），任缺一即不计可追溯；不得用「有 url」冒充「有哈希」。

---

## 不采纳的修订（pilot 里出现过、明确否决）

| 候选 | 否决理由（引用数字/原则） |
|---|---|
| 放宽 `evidence` 允许空数组（救 2 条零证据 claim） | 空证据对象永远无法进 L2/L3；允许它等于允许「无据断言」入库。正确做法是把这 2 条**留在源语料**并标记待补证，不进 ko。 |
| 放宽 `section.heading` 必填（对所有证据） | 报告证据的小节锚是跨库最脆弱一环（`docs/rci/interface-spec.md §2.2`）；放松会把「锚错了」变成「不用锚」。 |
| 允许 Agent 写 `platform_verified` 以提升通过率 | owner 铁则唯一通道；v1.0 DB `CHECK` 与校验器双重拦截，任何放松即拆掉防伪晋级能力。 |
| 用 `confidence.score` 自动抬高（如 0.6→0.8）以让 RQS 好看 | RQS 是诊断量，不是目标函数；调分＝自欺，且违反「零手抄/不伪造」。 |
| 把 `interpretive`/`hypothesis` 硬映射成 `capability_claim` | 4 条记录语义不同（解读性结论 / 假说）；硬映射制造假阳性，反而污染 `capability_claim` 面。已进 backlog 待定词。 |

---

## 落地计划（下一轮 PR，未在本轮执行）

1. 改 `schemas/knowledge-object-v1.schema.json`：R1（EvidenceRef.anyOf + locator）、R2（basis enum +2）、R4（section 条件必填）、R5（content_sha256_kind）。
2. 新增 `schemas/type-bridge.v1.json` + 校验器查表（R3）。
3. 改 `scripts/validate_ko_v1.py`：`validate_document` 增 R4/R5 语义检查；`evidence_traceability` 增 R6 第三闸分支；`check_transition` **不动**。
4. 迁移：`scripts/validate_ko_v1.py --upgrade-batch` 把本轮 200 条投影结果物化为 v1.1 文档（可重放，`sample_manifest.json` 定序）。
5. 回归：`tests/test_ko_v1_schema.py` 增 v1.1 用例（含「R1 不得解锁 report_claimed」「R5 quote_span 不得支撑 L3」两条负例）。

## 未测（本轮不覆盖，勿当已验）

- 平台验证回流（L3 通道）在真实 `tensor_maturity_verdicts` 数据上的行为；
- `tensor_reports` 正文小节锚的真实解析（需 TP 侧导出，本轮 section 字段只是搬运源定位符）；
- `ko_relation` 关联网络与 L2 迁移（样本内 0 条 relations）；
- 向量/图派生索引（架构令：出现真实查询需求前不做）。
**现象**：仓内 10,107 条 evidence 索引 **无一条**带 TP `tensor_reports.id`，全部是 locator 型（`code-location` / 报告切片），并用 `git:<repo>@<commit>` 或外部 `url` 钉扎。v1.0 `EvidenceRef.required` 含 `report_id` ⇒ 100% 拒绝。
**影响面**：解锁全部 10,071 条对象的证据字段（前提是其余条款同时满足）。按 R1–R6 全量投影后样本通过 97%（194/200），剩余 6 条失败见下文 R3 与 payload 条款。**单独实施 R1 的通过率本轮未测**（投影是一次性打包的，未做逐条消融），不据此下结论。
**影响面**：非报告证据从「结构上不可能合规」变为「结构上可合规且可追」；样本 215 条证据**全部**是 locator 型（无一条 report_id 型），其中 210 条带源文件哈希、5 条靠 R5 引文切片哈希兜底。
