# 四维检索索引 — TK agent 的定位面

面向 *agent 消费*的检索索引：一个知识对象要能被找到，必须同时在**四个维度**上
可寻址，缺一维就会出现「检索得到但用不了」或「用不了却检索得到」。
此处只登记索引键与查询面，**不是**算法说明；端点契约见 [`api.md`](api.md)，
后端一致性见 [`backends.md`](backends.md)。

| 维度 | 索引键 | 存储列 | 查询面 |
|---|---|---|---|
| **D1 域** | `domain` | `claims.domain` / `knowledge_base.domain` | `GET /query/by-domain?domain=&exact=`、`GET /kb/search?domain=` |
| **D2 类型** | `kind` / `ktype` | `claim·evidence·provenance·review` / `knowledge_base.ktype` | `GET /ko?kind=`、`GET /kb/search?ktype=` |
| **D3 信任** | `status` | `epistemic_status`、`review_status`、`publication_status`、`knowledge_base.status` | `GET /query/by-status?axis=&status=`、`GET /kb/search?status=` |
| **D4 溯源** | `locator` | `evidence.locator_type/locator_value/locator_quote`、`provenance` 记录 | `GET /query/chain?claim_id=`、`GET /query/claim-evidence?claim_id=` |

四维正交：域不问真假，类型不问出处，信任状态不问域，定位符不问评估结论。
把任意两维折叠成一个键（例如把 `domain` 编进 `ktype`）会让「跨域噪声」与
「已推翻结论」同时失去可过滤性 —— 这正是 D1/D3 存在的理由。

## D1 域：**必须由调用方给出**

`ke/consume.py` 的实现把域当作**过滤器**而非打分权重。实测（`tests/test_tk_agent_cases.py::
test_retrieval_dimensions_are_filters_not_weights`）：不带 `domain` 检索 `Taylor-Green`
会同时命中 `controls` 域的运维卡（其正文里也出现 Taylor-Green 字样），
加上 `domain=oss-lbm` 后噪声卡不可达。**结论：读路径不会从仓名推断域，
agent 每次检索都要显式传 `domain`**，否则跨域卡片会静默进入上下文。

```bash
curl -s "$BASE/kb/search?q=Taylor-Green&domain=oss-lbm&ktype=claim&limit=5"
curl -s "$BASE/query/by-domain?domain=lattice%20Boltzmann%20multiphase%2Fmulticomponent%20methods&exact=true"
```

## D2 类型：claim / evidence / provenance / review

四类记录不能互相冒充：claim 是可争论的陈述，evidence 是带定位符的支撑/反驳，
provenance 是「谁在何时用什么生成了它」，review 是评审事件。
`/query/chain` 一次返回 claim → evidence → source；`/query/claim-evidence`
额外返回 `dangling_evidence_refs`，**悬空引用显式可见而不是被静默丢弃**。

```bash
curl -s "$BASE/query/chain?claim_id=tkc:oss-lbm:kruger-taylor-green-decay"
```

## D3 信任：四状态不互相蕴含

`production_status` / `evidence_status` / `review_status` / `publication_status`
是四条独立轴（详见 `api.md` 与 `ke/api.py`）。检索面默认只回信任层命中的对象：
`/kb/search` 的 `status` 缺省 `active`，被推翻的卡（`status=deprecated`/`retracted`）
**从默认检索面消失**，但仍可被显式 `status=deprecated` 取回以便审计。

```bash
curl -s "$BASE/query/by-status?axis=evidence&status=established&kind=claim"
curl -s "$BASE/kb/search?q=%E8%A1%B0%E5%87%8F%E7%8E%87&status=active&ktype=claim"
```

D3 也是**精度主张的分层点**：引用值（教科书原文）、复现值（本仓运行记录）、
判据（3%）三层必须分开陈述，见 `tk-agent-cases/case-c-exactness-scope.json`。

## D4 溯源：结构化完整性 ≠ 活性

`locator` 是 `type + value + quote` 三元组（如 `code-location` +
`chapter13/matlab/vortexdecay.m:102-127` + 逐字引文）。检索能证明**结构完整**
（id 可解析、无悬空引用），不能证明**活性**（上游源码行能否在本工作树内落地）。
上游仓库未 vendor 时，活性必须记为 `WITHHELD`，不得升级为「已逐字核验」——
这条规则由 `tk-agent-cases/case-b-provenance.json` 固化，并由
`test_oss_lbm_claim_and_evidence_records_resolve` 校验。

## 不变量（机器可校验）

1. **确定性排序**：所有 `ORDER BY` 走 `Store.collate`（两后端字节序），
   否则 `:`/`-` 会让 PostgreSQL 的 locale 排序打乱 id 顺序（`backends.md`）。
2. **过滤器不是权重**：D1/D2/D3 命中即硬过滤；打分只发生在词面层
   （`ke.consume.rank`），且只在过滤后的候选集内进行。
3. **不静默丢弃**：悬空 evidence 引用、包级 provenance 与 claim 级 provenance
   分别上报（`/query/claim-evidence`、`/query/chain`）。
4. **消费可计量**：`/kb/search` 命中即写 `knowledge_injections` 并 bump
   `injected_count`，`log=false` 可关闭（脚本/回放用）。

## 与 TK agent case 的对应

| case | 主用维度 | 校验的检索性质 |
|---|---|---|
| `case-a-taylor-green` | D1 + D2 | 域过滤后 claim 唯一命中；claim 的精度主张落到 run 工件 |
| `case-b-provenance` | D4 | claim→evidence→locator 结构完整；活性 withheld；claim 级 PROV 缺口可见 |
| `case-c-exactness-scope` | D3 | 信任轴 + 精度粒度分层，引用值不得冒充分辨率无关常数 |

`tk-agent-cases/summary.json` 的 `retrieval_dimensions[]` 与上表一一对应，
`tests/test_tk_agent_cases.py::test_summary_matches_case_files` 断言四维齐全。