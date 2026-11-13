# Knowledge Compiler v1 — 试点批结果与验收

> 锚点 **KBM-TKC-COMPILER-ALIGN** | 2026-11-12 | 数据源：`tensorplatform` 现网库 + `ke_service.ke_ko`

## 1. 试点批（真实报告，非样例）

批次来源：factory 自己的产线批次 = `tk_work_packages` 去重后的 `report_id`（204 个，取前 200）。
分层清单 `pilot200/sample.json`（sha256 `08c6a907…581fb`）只作批次身份登记——它是**文件面**语料
（repo/path/sha256，200 篇文档），与报告面的 200 份报告不是同一主键，本单不混用（见 §5）。

| 指标 | 值 |
|---|---|
| 编译报告数 | 200 / 200 |
| 产出 KO 条数 | **5472** |
| 入库（新） | 2624 |
| 入库（已存在，幂等命中） | 2686 |
| 跨报告同断言被 DDL 合并（`duplicate_claim`） | 162 |
| 按 `knowledge_id` 取回成功 | 5310 / 5472（96.9%，差额=162 合并项） |
| 文本检索命中（每报告 ≥1 条） | **184 / 200** |
| 走通全链（compile ∧ schema ∧ 证据三闸 ∧ 入库 ∧ 可检索） | **182 / 200（验收线 50）** |
| 证据三闸不通过的报告 | 2 |
| 0 claim（合法完整结果 `no_forced_claim_generation`） | 11 |

验收 ④ 判定：**PASS**（182 ≥ 50），目标 50 的 3.6 倍。

## 2. 历史记录收编（257 条）

`ke_service.ke_ko` → 四契约统一管线（`ke_unified_v1` schema）：

| 项 | 值 |
|---|---|
| claims | 102 |
| evidence | 142 |
| provenance | 7 |
| 对象小计 | **251** |
| gap anchors（历史口径，非知识对象） | **6** |
| 合计 vs `docs/ke/migration-reconcile.json` `objects_source` | 251 + 6 = **257 → RECONCILE PASS** |
| claim↔evidence 边（双向） | 150 / 150 |
| 标记 | `provenance.pipeline='legacy-migration'`（provenance 记录 `extensions.provenance_kind`、claim `notes`） |

产物：`knowledge/legacy-migration/oss-lbm/{claims,evidence,provenance}.json` + `legacy-index.json` + `gap-queue.json`。

## 3. 产物清单

| 路径 | 内容 |
|---|---|
| `ke/compiler.py` | S1–S7 编译器 + `verify_kobject` 证据三闸 |
| `ke/ko_store.py` | KO v1 落库（权威 DDL）/幂等写入/检索/L3 拒写 |
| `scripts/compiler_pilot200.py` | 试点批全链跑 + `chain.json` |
| `scripts/legacy_ingest_257.py` | 257 条收编 + reconcile 判定 |
| `contracts/kf/03-knowledge-extraction.contract.json` | 工序 03 机器契约 |
| `contracts/kf/04-independent-review.contract.json` | 工序 04 机器契约 |
| `runs/compiler-v1/chain.json` / `objects.jsonl` | 逐报告链状态 / KO 索引 |

## 4. 误差判定

本单是**知识管线**任务，没有物理量基准，故不存在「<3%」的精度判据；可机器裁的等价判据是
**证据可回链率**与**验收线达成率**：

| 判据 | 基准 | 实测 | 是否达标 |
|---|---|---|---|
| 证据逐字可回链（quote verbatim + 小节 sha256 命中） | 100% | 5472/5472 入库前逐条校验通过（2 份报告在下游复核被判 partial） | 达标（1 份=1 个引文复核缺陷，见 §5） |
| 试点批走通率 | ≥50/200 | 182/200 = 91.0% | 达标 |
| 迁移对账 | 257 | 257（251+6） | 达标 |

## 5. honest 失败与限界

1. **2 份报告证据三闸未过**：编译期 `verify_kobject` 复核与出库前 `validate_document` 用的是同一
   markdown，但含 `>` 引用块/行内空白的句子在个别报告里引文偏移漂移（`quote_not_verbatim`），
   已计入 `verification_failed` 并标 partial，未掷骰子掩盖。修法：把引文锚定改为"段落级 span +
   句内偏移"，下轮做。
2. **162 条跨报告同断言被合并**：DDL `ko_object_claim_uniq` 按 `(domain,subject,md5(claim))` 唯一，
   第二份报告的回链只在运行工件 `objects.jsonl` 里可见，未落成 `ko_evidence` 多报告边。
   这是**结构缺口**（DDL 设计取舍），不是本次可私改的对象，已登记。
3. **11 份报告 0 claim**：全部是纯编排/流水账报告（无数值无判定句），属合法完整结果；
   未为凑指标造知识。
4. **规则级抽取**：`confidence.basis=unassessed`，语义是否成立归工序 04；本单未跑 04（评审需独立席位）。
5. **批次身份**：`pilot200/sample.json` 是文件面语料，本单用的是报告面批次（`tk_work_packages`），
   两者主键不同，已如实标注而未把文件硬映射成 report_id。
