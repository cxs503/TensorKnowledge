# Knowledge Engine — 最小闭环原型（m8620 / ke-proto）

> 状态：原型（proto）。自研薄层先行，不阻塞于选型评估（tk-ke-eval-1 未出结论；
> 若评估结论为外框，本原型作为 fallback 基线保留并明示）。
> 试点包：`platform-test/epistemic-benchmark/pilots/m8554/`（branch agent/m8554
> 的认知试点工件，owner 2026-11-09 验收通过；本分支将其收编为可复现夹具）。

## 1. 是什么

对 epistemic 记录包（claim / evidence / provenance JSON）的**最小闭环**：

```
ingest (JSON -> SQLite)  ->  查询 (6 类)  ->  一致性校验 (schema + xref 不变量)
```

设计约束：

- **薄层**：仅 Python 标准库（`sqlite3`/`json`/`argparse`）+ `jsonschema`
  （仓库既有依赖，见 `requirements-validation.txt`）。无服务、无网络、无新依赖。
- **零手抄**：每条记录原文存 `raw_json` 列，查询结果可回溯到源字节
  （`ke.queries.raw_record` 与源文件逐字节等价，有测试）。
- **不变量可检**：xref 不变量与 `pilots/m8554/validate_pilot.py` 第 2 节
  同口径（见 §4）。

## 2. 模块结构

| 文件 | 职责 |
|---|---|
| `ke/store.py` | SQLite schema + `ingest_pilot()`（幂等，单事务） |
| `ke/queries.py` | 查询类 Q1–Q6（全部按 id 排序，输出确定） |
| `ke/validate.py` | `xref_report()` / `schema_report()` / `validate_package()` |
| `ke/cli.py` | `ingest` / `query` / `validate` / `demo` 子命令 |
| `tests/test_ke_proto.py` | 15 个测试：钉死试点包查询结果 + 一致性 + 负例 |

SQLite 表：`claims` / `evidence` / `provenance`（各含 `raw_json` 原文列）+
连接表 `claim_evidence`（claim.evidence_refs 归一化）/ `evidence_claims`
（evidence.claim_refs 归一化）+ `ingest_meta`。

**有意不设外键**（连接表）：不可解析的引用必须**可入库**，否则
`xref_report` 永远检不到它们（校验器变空转）。检错机制归校验器，
与 validate_pilot.py 的 Python 侧检错同构。

## 3. 查询类（任务要求 ≥4，实现 6）

| # | 函数 | 语义 |
|---|---|---|
| Q1 | `claims_by_status(status)` | 按 claim `epistemic_status` |
| Q2 | `evidence_by_relation(relation)` | 按证据关系 supports/refutes/qualifies/contextualizes/mentions |
| Q3 | `provenance_chain(claim_id)` | 溯源链 claim → evidence → source（含 locator 引文） |
| Q4 | `claims_by_domain(domain, exact=True)` | 按 `scope.domain`（精确/子串） |
| Q5 | `evidence_for_claim(claim_id)` | 某 claim 挂载的证据（带 relation） |
| Q6 | `stats()` | 计数 + status/relation/assessment 分布 |

## 4. 一致性口径（与 validate_pilot.py 对齐）

`xref_report(conn)` 用 SQL 实现参考验证器第 2 节四条不变量：

- **I1** 每个 `claim.evidence_refs` 可解析到 evidence id
- **I2** 每个 `evidence.claim_refs` 可解析到 claim id
- **I3** 无孤儿 evidence（每条 evidence 被 ≥1 claim 引用）
- **I4** 无无证据 claim（每个 claim 被 ≥1 evidence 引用）

`schema_report()` 对 5 个 schema（claim/evidence/provenance-record、
knowledge-object、production-result）做 jsonschema 校验；
`production-result.schema.json` 的相对 `$ref`（→ knowledge-object）经
本地 `referencing.Registry` 离线解析（schema 的 `$id` 指向 GitHub，
直接校验会触发远程拉取）。

一致性证明（`tests/test_ke_proto.py`）：

1. `test_xref_invariants_match_file_recomputation`：从**原始 JSON 文件**
   独立重算四条不变量，与 DB 侧报告逐项相等；
2. `test_reference_validator_passes`：子进程跑 `validate_pilot.py` 本身，
   退出码 0（KE 口径与参考验证器同真）；
3. `test_negative_corrupted_package_detected`：注入孤儿 evidence +
   幽灵 evidence_ref，两条 xref 不变量**必须**报 FAIL（防空转）。

## 5. 运行

```bash
# 全闭环 demo（ingest -> 6 类查询 -> 校验，确定性 JSON，exit 0 = 全绿）
python -m ke.cli demo platform-test/epistemic-benchmark/pilots/m8554

# 单类查询
python -m ke.cli query <pilot> --db /tmp/ke.db --type status   --value contested
python -m ke.cli query <pilot> --db /tmp/ke.db --type relation --value refutes
python -m ke.cli query <pilot> --db /tmp/ke.db --type domain   --value "research data stewardship principles"
python -m ke.cli query <pilot> --db /tmp/ke.db --type chain    --value tkc:prov-o:wasattributedto-signature
python -m ke.cli query <pilot> --db /tmp/ke.db --type stats

# 校验（PASS/FAIL 行与 validate_pilot.py 同形）
python -m ke.cli validate <pilot> --db /tmp/ke.db

# 测试
python -m pytest tests/test_ke_proto.py -v
```

## 6. 试点包实测结果（m8554，2026-11-09 快照）

- ingest：4 claims / 8 evidence / 3 provenance，8+8 条 xref 边
- Q1：established=1（PROV-O 签名）· well-supported=1（FAIR A1 窄命题）·
  contested=1（FAIR 开放获取宽命题）· not-assessed=1（RO-Crate 投产）
- Q2：supports=2 · refutes=1 · contextualizes=3 · qualifies=1 · mentions=1
- Q4：domain "research data stewardship principles" = 2 claims
- 校验：16 schema PASS + 4 xref PASS = ALL PASS（`runs/ke-proto/demo-output.txt`）

## 7. 局限与下一步

- 单包 ingest：一次一个 pilot 目录（重 ingest 整包替换）；多包/增量 ingest 未做。
- 无推理层：只存/查/验，不做 entailment 判定或状态迁移（那是 Engine 的
  认知层，待选型评估后定）。
- 查询为 SQL 直查，无全文检索（试点规模 15 条记录，无必要）。
- 下一步候选：多包 ingest 与包间 xref、review-event 接入、
  与 production-result 信封的联动校验。
