# KF-RESULT wp-11267-04

**工作包** `wp-11267-04` · task_type `04-independent-review` · lane C · report_id **11267**
**审核对象** `wp-11267-01`（01-asset-registration）
**源** `tensor://reports/11267` field `markdown` · sha256 `sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f` · 7482 chars / 11574 bytes / 201 lines（现场重取，独立重算一致）
**处置** `needs-fix` — 语义保真 pass；两处元数据 needs-fix（非阻断）

## ① 本工序做了什么

对上游资产登记包 `wp-11267-01` 做独立红队审核：**不看生产者的解释，只用报告原文 + 上游机器产物**重新算一遍。
判的是**语义保真**——登记集是否与报告原文逐字一致、是否有幻觉/漏登记、是否越界（多报告、写 verified）。
不重算报告里的物理量，也不改写上游任何文件。

结论一句话：**登记内容可核、无伪造；缺陷只在信封 schema 版本漂移与探针文案两处元数据上。**
独立复核 15 项：pass 13 · needs-fix 2 · FAIL 0。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **现场重取原文**：`GET /tensor/reports/11267`（Bearer），markdown 落地 `runs/wp-11267-04/source_11267.md`；
   独立重算 sha256 = `sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f`，与契约声明一致（`hash_match=True`）。
2. **自写复算器** `docs/kf/wp-11267-04/review_wp-11267-04.py`：资产发现、locator 判定、计数复核、图 payload 重取、schema 双版本校验全部由审核员重新实现，不复用生产者代码。
3. **locator 逐字符复核**：57 条 locator，逐条判 `quote ∈ markdown`、`markdown[start:end] == quote`、行号由 offset 重算、`quote_sha256` 重算。
4. **独立发现集**：图片链接 / 反引号路径 token / `python -m` 入口 / `cjNNN` 作业号 / `test_*` 符号五类规则，得 15 个候选，与登记集求差 → 漏登记 0 条；反向查“原文中不存在”的资产 → 0 条。
5. **declared_absent 保真**：7 条逐条做句级判定（引文本身或所在行须含 not measured/queued/未测量等缺失语），并反向检查判据表 3 行 `not measured` 是否漏登记 → 漏 0 行。
6. **图 payload 重取**：7 张图从 `/tensor/reports/11267/figures/<name>` 现场取字节，比对 `bytes` 与 `sha256`，校验 PNG magic —— 全部一致（`all_match=True`）。
7. **schema 双版本**：用生成时在册版本（commit `548f89e`）与当前 `schemas/kf_result.v1.schema.json` 分别校验上游信封；manifest 另按本包 pinned schema 校验。
8. **外部时序核对**：查 `cj308/cj313/cj314` 集群队列终态（`run_cluster ps`），核对报告“仍为 queued”的时效性。
9. **工具链**：python 3.11 · jsonschema 4.26 · matplotlib 3.10；全部结论落 `runs/wp-11267-04/independent_recompute.json`。

## ③ 产出物清单（输出文件 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-11267-04/kf_result.json` | 结果信封（过当前 KF-RESULT v1 schema）：outputs 含 review_report.json / review_events.json |
| `docs/kf/wp-11267-04/review_report.json` | 审核报告：15 项复核 + 6 条发现（含 severity/证据/复现/整改）+ 未跑项 + 过度声称项 + 处置 |
| `docs/kf/wp-11267-04/review_events.json` | 审核事件账本 7 条（重取→复核→外部探针→发现→处置→verified 写入 0 条） |
| `docs/kf/wp-11267-04/review_wp-11267-04.py` | 独立复算器（可一键复跑） |
| `runs/wp-11267-04/independent_recompute.json` | 逐项 metric 原始记录（每个判定带 verbatim 证据） |
| `runs/wp-11267-04/source_11267.md` / `record_11267.json` | 原文快照与平台记录快照（复算基准） |
| `docs/kf/wp-11267-04/fig1_review_matrix.png` | 图 1：复核项判定矩阵 + 登记计数分布 |

## ④ 证据定位表（claim/字段 → 原文引文）

每条引文由构建脚本 `quote()` 现场断言“逐字存在于原文”后才写入，行号由字符偏移重算。

- **源身份 hash** — pass — 原文 `# MPI 域分解并行有限元基础设施（p284w3-n04-fem-mpi-parallel）` (L1)
- **7 张图存在且被正文引用** — pass — 原文 `![强扩展](figures/strong_scaling.png)` (L128)
- **图引用清单完整性（7 链接 + 7 裸名 = 14）** — pass — 原文 `![场量](figures/fields.png)` (L134)
- **declared_absent: C1 未测量** — pass — 原文 `| C1_strong_efficiency | not measured | 0.600000 | P=16 | FAIL (未测量) |` (L124)
- **declared_absent: C2 未测量** — pass — 原文 `| C2_weak_ratio | not measured | 1.500000 | P=32 | FAIL (未测量) |` (L125)
- **declared_absent: C4 未测量** — pass — 原文 `| C4_comm_fraction | not measured | 0.300000 | P=16 | FAIL (未测量) |` (L126)
- **declared_absent: MPIComm 未本机实测** — pass — 原文 `自动探测，但**未在本机实测**（如实声明，不作为本节点证据）。` (L162)
- **declared_absent: cj308/cj313/cj314 排队** — pass — 原文 `` 在报告定稿时仍为 `queued` `` (L169)
- **对照：C6 已测量（不应登记为缺失）** — pass — 原文 `| C6_load_balance | 0.110812 | 0.100000 | P=4 | FAIL |` (L123)
- **F3 时效性（报告自述集群未到位）** — 见 F3 — 原文 `集群算力未到位（未完成部分，如实申报）` (L168)
- **F4 locator 过窄（缺失语义在句中）** — 见 F4 — 原文 `（cj308 全量判据、cj313 P=1/2 点、cj314 P=4/8 点）` (L169)
- **复现入口** — 契约要求的一键复跑 — 原文 `python -m tensorphysics.fem_parallel.verification --n-dofs 1000000 --n-per-rank 100000` (L195)

## ⑤ 注意点与局限

1. **两处 needs-fix 都不碰事实内容**：F1（信封 schema 版本漂移）与 F2（探针文案矛盾）是元数据层缺陷；
   manifest 的 23 资产 / 34 locator / 7 图 payload 全部可复算通过。
2. **F3 是时效性风险而非上游缺陷**：报告定稿时三个作业确为 queued（引文见上表），但审核时刻
   `cj308/cj313/cj314` 均已 `succeeded/rc=0`。登记忠实于原文，但下游若把“无 P=16/P=32 数据”当永久结论就错了。
3. **审核口径差异**（F5）：`distinct_referenced_paths=15` 在审核员口径下为 11（是否计入模块点分名/目录 token/glob），
   图片类派生计数 7/14 则逐项复现 —— 定义差异，非错误。
4. **A00 文档型 locator**（F6）：span 覆盖全文而 quote 仅为标题行，需靠 `method=document` 区分；其 `all_locators[0]` 为 0–47 精确对齐。
5. **不复算物理量**：本工序以报告原文为事实基准，不重算 S(P)/E(P)/rel L2；数字可信度归 05 综述与平台门。
   因此本报告不对“扩展性是否成立”作任何断言。
6. **隔离性局限（如实申报）**：生产者结论文档 `docs/kf_result_wp-11267-01.md` 的前 60 行在独立复算前被同目录浏览命令落屏；
   本报告所有判定与数字均由复算器重算，未引用其自检结论，但审核上下文并非完全隔离。
7. **可复现边界**：复核基线为仓库工作树快照（HEAD `445efce0fb14`）；生产者运行时环境不可重建；
   集群状态是查询时刻快照。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 依据 |
|---|---|---|
| valid_json | ✅ | `review_report.json` / `review_events.json` / `kf_result.json` 均可 `json.loads` |
| schema_pass | ✅ | 信封过 `schemas/kf_result.v1.schema.json`（draft 2020-12，`additionalProperties=false`）；构建时即校验，失败会抛错 |
| reviewer_independent | ✅（有披露） | 独立复算器自写；未复用生产者代码/结论；隔离性局限见⑤.6 |
| upstream_packages_completed | ✅ | wp-11267-01 四件产物齐备且 hash 固化（见 review_report.json `reviewed_artifacts`） |
| review_prompt_not_copied_from_producer | ✅ | 审核判据由本包自定 15 项，非摘抄生产者自检项 |
| reviewer_context_excludes_producer_explanation | ✅（有披露） | 判定不采用其叙述；但存在⑤.6 所述邻近可见，如实记录 |
| do_not_mark_claims_as_verified | ✅ | 全库 `verified` 标记写入 0 条（review_events E7） |

**honest-FAIL 声明**：无 FAIL 项；2 项 needs-fix 归上游元数据（F1/F2），1 项 attention 归下游（F3），均未粉饰。

## 复现

```bash
cd <worktree-root>
export TENSOR_API_BASE=http://127.0.0.1:8010/api/v1
python3 docs/kf/wp-11267-04/review_wp-11267-04.py   # 独立复算 → runs/wp-11267-04/independent_recompute.json
python3 docs/kf/wp-11267-04/build_review.py         # 生成 review_report/events/kf_result/图/本报告
```

## 发现汇总

| ID | 严重度 | 标题 | 阻断 |
|---|---|---|---|
| F1 | medium | 上游信封 kf_result.json 不符合当前 KF-RESULT v1 schema（顶层多出 claims；provenance 缺 source_uri） | 否 |
| F2 | low | worktree_probe 的 reason 文本与 result 自相矛盾（14/23 资产写成 “path exists …” 却 result=unresolved），并泄漏生产者绝对工作树路径 | 否 |
| F3 | medium | cj308/cj313/cj314 登记为 declared_absent 与报告原文一致，但集群现状已 succeeded —— 下游不得把“无扩展点数据”当作永久结论 | 否 |
| F4 | low | cluster_job 资产的 locator 只有裸作业号，“缺失”语义仅由所在句承载 | 否 |
| F5 | info | 派生计数 distinct_referenced_paths=15 未能被审核口径复现（审核员口径 11） | 否 |
| F6 | info | A00 文档型 locator 的 span 覆盖全文而 quote 只是标题行（span≠quote） | 否 |

## 复核项汇总

| 检查 | 名称 | 判定 |
|---|---|---|
| K1-source-identity | 源身份：manifest/契约/独立重算三方 hash 与字符数一致 | **pass** |
| K2-locator-verbatim | locator 逐字符可定位（quote∈原文 / md[s:e]==quote / 行号重算一致） | **pass** |
| K3-counts-selfconsistent | counts 与实际数组逐项自洽（总数/按类/按可解性/id 唯一） | **pass** |
| K4-discovery-recall | 审核员独立发现集无漏登记 | **pass** |
| K4b-no-phantom-assets | 无“原文中不存在”的幻觉资产（每条 locator quote 均在原文） | **pass** |
| K5-declared-absent-fidelity | declared_absent 每条都是原文自述缺失（句级），且判据表未测量行无遗漏 | **pass** |
| K6-figure-payload | 7 张图现场重取，字节数与 sha256 与登记一致（非占位/非错误体） | **pass** |
| K7-scope-boundary | claims=[] 合规、全库无 verified 判定、只碰本报告 | **pass** |
| K8-envelope-schema-dual | 信封 schema：按生成时在册版本 vs 按当前版本分别判定 | **needs-fix** |
| K9-manifest-schema | asset_manifest.json 过本包 pinned schema | **pass** |
| K10-derived-counts | 派生计数（图链接/图引用/独立路径数）复核 | **pass** |
| K11-worktree-probe-wording | worktree_probe 的 reason 文本与 result 不自相矛盾、无绝对路径泄漏 | **needs-fix** |
| K13-section-attribution | in_report_section 与 locator 实际所在节段一致 | **pass** |
| K14-occurrence-count | occurrence_count == len(all_locators)，且总 locator 数可复核 | **pass** |
| K15-caption-fidelity | 图题逐字等于记录元数据 caption（非记忆重述） | **pass** |

```json
{
 "package_id": "wp-11267-04",
 "task_type": "04-independent-review",
 "contract_version": "1.0",
 "report_id": "11267",
 "provenance": {
  "source_uri": "tensor://reports/11267",
  "source_field": "markdown",
  "source_hash": "sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f",
  "source_hash_matches": true,
  "title": "TensorPhysics: MPI 域分解并行 FEM 基础设施与强/弱扩展验证 (p284w3-n04)",
  "scenario_key": "p284w3-n04-fem-mpi-parallel",
  "chars": 7482
 },
 "outputs": {
  "review_report.json": {
   "review_report_version": "1.0",
   "review_id": "wp-11267-04",
   "reviewer_role": "red-team-reviewer",
   "report_id": "11267",
   "package_reviewed": "wp-11267-01",
   "review_object_contract": {
    "package_id": "wp-11267-01",
    "task_type": "01-asset-registration",
    "contract_version": "1.0",
    "lane": "C"
   },
   "reviewed_artifacts": [
    {
     "path": "docs/kf/wp-11267-01/asset_manifest.json",
     "sha256": "sha256:cd50467970c5ce7b9b34d33062324627175e86807d32cd6b669a88ac9a0aff15"
    },
    {
     "path": "docs/kf/wp-11267-01/kf_result.json",
     "sha256": "sha256:7f0ce0f357ba6f8919cbea28ce13365b9213da33405be57050657c1c96c68bd8"
    },
    {
     "path": "docs/kf/wp-11267-01/verification.json",
     "sha256": "sha256:1dd3324a52ceb4cb76007fe59b388b5dca77293347c47ea6d48a9e56b7e309fb"
    },
    {
     "path": "docs/kf/wp-11267-01/asset_manifest.schema.json",
     "sha256": "sha256:3f83ea495de915593ebaa4602cb3327cc4726b55cc5d06ad657a6180837dabcd"
    }
   ],
   "source": {
    "uri": "tensor://reports/11267",
    "field": "markdown",
    "recomputed_sha256": "sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f",
    "contract_declared_sha256": "sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f",
    "hash_match": true,
    "chars": 7482,
    "bytes_utf8": 11574,
    "lines": 201,
    "fetched_via": "GET /tensor/reports/11267（现场重取，非磁盘副本）"
   },
   "verdict": "needs-fix",
   "verdict_reason": "语义保真无缺陷：23 资产 / 34 locator 全逐字可定位（0 span 错、0 行号错、0 幻觉、0 漏登记），7 张图 payload 现场重取字节级一致，源 hash 三方一致，claims=[] 合规且无 verified 标记。判 needs-fix 只因两处机器可检的元数据缺陷（F1 信封 schema 版本漂移、F2 探针文案矛盾），均不影响 manifest 的事实内容，与 F3 的时效性风险一并交下游注意。",
   "verdict_scope": {
    "semantic_fidelity": "pass",
    "artifact_integrity": "pass",
    "envelope_schema_current": "fail (F1)",
    "probe_semantics": "needs-fix (F2)",
    "downstream_freshness": "attention (F3)"
   },
   "contract_checks": {
    "valid_json": true,
    "schema_pass": true,
    "reviewer_independent": true,
    "upstream_packages_completed": true,
    "notes": "schema_pass 指本审核包 review_report.json/kf_result.json 通过 schemas/kf_result.v1.schema.json；上游信封对当前 schema 的符合性另见 F1（不改写上游产物，只记录）。"
   },
   "independence": {
    "reviewer_is_not_producer": true,
    "producer": "kf-worker/m15695",
    "reviewer_worktree": "/root/tp-agent/work/m19785",
    "repo_head": "445efce0fb14750df98a995d4c0667c7519b55ee",
    "independent_recomputation": "自写复算器 docs/kf/wp-11267-04/review_wp-11267-04.py，资产发现规则、locator 判定、计数复核、图 payload 重取均由审核员重新实现，未复用生产者代码",
    "context_used": [
     "报告原文 markdown（API 现场重取）",
     "上游机器产物 asset_manifest.json / kf_result.json / 其 pinned schema",
     "上游自检 verification.json（仅用于交叉比对，不作判定依据）"
    ],
    "context_exclusions": [
     "未采用生产者的解释性叙述作为判定依据",
     "未读取或写入任何其它 report_id"
    ],
    "limitations": [
     "生产者结论文档 docs/kf_result_wp-11267-01.md 的前 60 行在进入独立复算前被同目录浏览命令落屏（邻近可见，非有意取证）；本报告全部判定与数字由复算器对原文/产物重新计算，未引用其自检结论，但严格意义上审核上下文并非完全隔离。",
     "复核基线是仓库工作树快照（HEAD），未对生产者运行时做历史重建；生产者进程环境不可复现。",
     "集群作业状态为查询时刻快照（见 F3），非报告定稿时刻的状态。"
    ]
   },
   "scope_performed": [
    "源身份：markdown 字节哈希、字符数、标题、scenario_key 三方（契约/manifest/现场重取）比对",
    "locator 逐字符复核：23 个资产级 locator + 34 个 all_locators，共 57 条，逐条 quote∈原文、md[s:e]==quote、行号重算、quote_sha256 重算",
    "独立资产发现：图片链接 / 反引号路径 token / python -m 入口 / cjNNN 作业号 / test_* 符号五类规则，比对登记集（召回）与幻觉（精确率）",
    "declared_absent 保真：7 条逐条判“原文自述缺失”并做句级判定，反向检查判据表 not measured 行是否漏登记",
    "图 payload：7 张图从 /tensor/reports/11267/figures/<name> 现场重取，字节数与 sha256 与登记比对，校验 PNG magic",
    "计数自洽：total / by_resolution / by_class / id 唯一 / occurrence_count==len(all_locators) / 派生计数",
    "节段归属：in_report_section 与 locator 所在最近标题逐条比对",
    "图题保真：manifest 图题与记录元数据 caption 逐字比对",
    "信封与 manifest schema：按生成时在册版本（548f89e）与当前版本分别校验",
    "工序边界：claims=[] 、verified 标记扫描、跨 report_id 引用扫描",
    "外部时序核对：cj308/cj313/cj314 集群队列状态查询"
   ],
   "checks": [
    {
     "id": "K1-source-identity",
     "name": "源身份：manifest/契约/独立重算三方 hash 与字符数一致",
     "verdict": "pass",
     "detail": {
      "manifest_hash": "sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f",
      "recomputed": "sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f",
      "contract_hash": "sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f",
      "chars": {
       "manifest": 7482,
       "recomputed": 7482
      },
      "bytes_utf8": {
       "manifest": 11574,
       "recomputed": 11574
      },
      "title_match": true,
      "scenario_match": true
     },
     "evidence": [
      {
       "quote": "# MPI 域分解并行有限元基础设施（p284w3-n04-fem-mpi-parallel）",
       "start_char": 0,
       "start_line": 1
      }
     ]
    },
    {
     "id": "K2-locator-verbatim",
     "name": "locator 逐字符可定位（quote∈原文 / md[s:e]==quote / 行号重算一致）",
     "verdict": "pass",
     "detail": {
      "locators_checked": 57,
      "bad": 0,
      "quote_not_in_markdown": 0,
      "span_mismatch": 0,
      "line_mismatch": 0,
      "document_method_spans": 1,
      "examples": []
     },
     "evidence": [
      {
       "quote": "# MPI 域分解并行有限元基础设施（p284w3-n04-fem-mpi-parallel）",
       "start_char": 0,
       "start_line": 1
      }
     ]
    },
    {
     "id": "K3-counts-selfconsistent",
     "name": "counts 与实际数组逐项自洽（总数/按类/按可解性/id 唯一）",
     "verdict": "pass",
     "detail": {
      "declared": {
       "assets": 23,
       "by_class": {
        "cluster_job": 3,
        "code_module_path": 1,
        "code_script": 3,
        "data_artifact": 1,
        "declared_measurement_gap": 4,
        "figure_artifact": 7,
        "run_command": 1,
        "source_document": 1,
        "test_suite": 1,
        "test_symbol": 1
       },
       "by_resolution": {
        "declared_absent": 7,
        "referenced_unresolved": 8,
        "resolved_in_source": 8
       },
       "resolved_in_source": 8,
       "referenced_unresolved": 8,
       "declared_absent": 7,
       "body_image_links": 7,
       "figure_references_total": 14,
       "distinct_referenced_paths": 15,
       "claims": 0
      },
      "actual_total": 23,
      "actual_by_resolution": {
       "resolved_in_source": 8,
       "referenced_unresolved": 8,
       "declared_absent": 7
      },
      "actual_by_class": {
       "source_document": 1,
       "code_module_path": 1,
       "run_command": 1,
       "data_artifact": 1,
       "code_script": 3,
       "declared_measurement_gap": 4,
       "figure_artifact": 7,
       "cluster_job": 3,
       "test_symbol": 1,
       "test_suite": 1
      },
      "id_unique": true,
      "name_unique": true
     },
     "evidence": []
    },
    {
     "id": "K4-discovery-recall",
     "name": "审核员独立发现集无漏登记",
     "verdict": "pass",
     "detail": {
      "discovered_keys": 15,
      "missed": 0,
      "missed_items": []
     },
     "evidence": []
    },
    {
     "id": "K4b-no-phantom-assets",
     "name": "无“原文中不存在”的幻觉资产（每条 locator quote 均在原文）",
     "verdict": "pass",
     "detail": {
      "phantom": []
     },
     "evidence": []
    },
    {
     "id": "K5-declared-absent-fidelity",
     "name": "declared_absent 每条都是原文自述缺失（句级），且判据表未测量行无遗漏",
     "verdict": "pass",
     "detail": {
      "declared_absent": 7,
      "bad": [],
      "locator_narrower_than_sentence": [
       {
        "asset_id": "A16",
        "name": "cj308",
        "quote": "cj308",
        "line": 169,
        "line_text": "（cj308 全量判据、cj313 P=1/2 点、cj314 P=4/8 点）在报告定稿时仍为 `queued`"
       },
       {
        "asset_id": "A17",
        "name": "cj313",
        "quote": "cj313",
        "line": 169,
        "line_text": "（cj308 全量判据、cj313 P=1/2 点、cj314 P=4/8 点）在报告定稿时仍为 `queued`"
       },
       {
        "asset_id": "A18",
        "name": "cj314",
        "quote": "cj314",
        "line": 169,
        "line_text": "（cj308 全量判据、cj313 P=1/2 点、cj314 P=4/8 点）在报告定稿时仍为 `queued`"
       }
      ],
      "unmeasured_rows_in_report": 3,
      "unregistered_unmeasured_rows": []
     },
     "evidence": [
      {
       "quote": "| C1_strong_efficiency | not measured | 0.600000 | P=16 | FAIL (未测量) |",
       "start_char": 4472,
       "start_line": 124
      },
      {
       "quote": "| C2_weak_ratio | not measured | 1.500000 | P=32 | FAIL (未测量) |",
       "start_char": 4543,
       "start_line": 125
      },
      {
       "quote": "| C4_comm_fraction | not measured | 0.300000 | P=16 | FAIL (未测量) |",
       "start_char": 4607,
       "start_line": 126
      },
      {
       "quote": "   自动探测，但**未在本机实测**（如实声明，不作为本节点证据）。",
       "start_char": 6086,
       "start_line": 162
      },
      {
       "quote": "cj308",
       "start_char": 6405,
       "start_line": 169
      },
      {
       "quote": "cj313",
       "start_char": 6416,
       "start_line": 169
      },
      {
       "quote": "cj314",
       "start_char": 6430,
       "start_line": 169
      }
     ]
    },
    {
     "id": "K6-figure-payload",
     "name": "7 张图现场重取，字节数与 sha256 与登记一致（非占位/非错误体）",
     "verdict": "pass",
     "detail": {
      "figures": 7,
      "all_match": true,
      "declared_figure_assets": [
       "strong_scaling.png",
       "weak_scaling.png",
       "communication.png",
       "iterations.png",
       "accuracy.png",
       "load_balance.png",
       "fields.png"
      ],
      "artifact_endpoint_probe": {
       "path": "/tensor/reports/11267/artifacts",
       "http_status": 404,
       "bytes": 22,
       "body_head": "{\"detail\":\"Not Found\"}"
      }
     },
     "evidence": []
    },
    {
     "id": "K7-scope-boundary",
     "name": "claims=[] 合规、全库无 verified 判定、只碰本报告",
     "verdict": "pass",
     "detail": {
      "claims": [],
      "claims_empty_reason_len": 435,
      "verified_token_in_reason": false,
      "other_report_ids_seen": []
     },
     "evidence": []
    },
    {
     "id": "K8-envelope-schema-dual",
     "name": "信封 schema：按生成时在册版本 vs 按当前版本分别判定",
     "verdict": "needs-fix",
     "detail": {
      "emission_schema_commit": "548f89e",
      "emission_schema_errors": null,
      "current_schema_errors": {
       "message": "Additional properties are not allowed ('claims' was unexpected)",
       "path": []
      },
      "top_level_keys": [
       "claims",
       "outputs",
       "package_id",
       "provenance",
       "report_id",
       "task_type"
      ],
      "provenance_keys": [
       "emitted_at",
       "notes",
       "producer",
       "source_field",
       "source_hash"
      ]
     },
     "evidence": []
    },
    {
     "id": "K9-manifest-schema",
     "name": "asset_manifest.json 过本包 pinned schema",
     "verdict": "pass",
     "detail": {
      "pinned_schema": "docs/kf/wp-11267-01/asset_manifest.schema.json",
      "errors": null
     },
     "evidence": []
    },
    {
     "id": "K10-derived-counts",
     "name": "派生计数（图链接/图引用/独立路径数）复核",
     "verdict": "pass",
     "detail": {
      "manifest_body_image_links": 7,
      "recomputed_image_links": 7,
      "manifest_figure_references_total": 14,
      "recomputed_bare_png_mentions": 14,
      "manifest_distinct_referenced_paths": 15,
      "recomputed_backticked_paths": 10
     },
     "evidence": []
    },
    {
     "id": "K11-worktree-probe-wording",
     "name": "worktree_probe 的 reason 文本与 result 不自相矛盾、无绝对路径泄漏",
     "verdict": "needs-fix",
     "detail": {
      "contradictory_entries": 14,
      "sample": [
       [
        "A05",
        "C1_strong_efficiency",
        "path exists in TensorKnowledge worktree: C1_strong_efficiency"
       ],
       [
        "A06",
        "C2_weak_ratio",
        "path exists in TensorKnowledge worktree: C2_weak_ratio"
       ],
       [
        "A07",
        "C4_comm_fraction",
        "path exists in TensorKnowledge worktree: C4_comm_fraction"
       ]
      ],
      "absolute_path_entries": 14
     },
     "evidence": []
    },
    {
     "id": "K13-section-attribution",
     "name": "in_report_section 与 locator 实际所在节段一致",
     "verdict": "pass",
     "detail": {
      "assets_checked": 22,
      "mismatch": []
     },
     "evidence": []
    },
    {
     "id": "K14-occurrence-count",
     "name": "occurrence_count == len(all_locators)，且总 locator 数可复核",
     "verdict": "pass",
     "detail": {
      "total_locators": 34,
      "mismatch": []
     },
     "evidence": []
    },
    {
     "id": "K15-caption-fidelity",
     "name": "图题逐字等于记录元数据 caption（非记忆重述）",
     "verdict": "pass",
     "detail": {
      "record_figures": 7,
      "mismatch": []
     },
     "evidence": []
    }
   ],
   "findings": [
    {
     "id": "F1",
     "severity": "medium",
     "likelihood": "certain (machine-detectable)",
     "blocking": false,
     "title": "上游信封 kf_result.json 不符合当前 KF-RESULT v1 schema（顶层多出 claims；provenance 缺 source_uri）",
     "evidence": {
      "emission_schema_commit": "548f89e (2026-11-12 09:21 +0800)",
      "emission_schema_verdict": "pass",
      "current_schema_error": {
       "message": "Additional properties are not allowed ('claims' was unexpected)",
       "path": []
      },
      "top_level_keys": [
       "claims",
       "outputs",
       "package_id",
       "provenance",
       "report_id",
       "task_type"
      ],
      "provenance_keys": [
       "emitted_at",
       "notes",
       "producer",
       "source_field",
       "source_hash"
      ],
      "provenance_source_hash_recomputed": "sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f"
     },
     "analysis": "上游产物生成时（2026-11-12T01:54Z）在册 schema（commit 548f89e）允许顶层 claims 与 provenance 扩展字段，故生产者的 schema_pass 自检在当时为真；2026-11-13（ef809cd）schema 收紧为 provenance required=[source_uri, source_field, source_hash] 且 additionalProperties=false，上游信封随即不再通过。仓库内 117 份 kf_result.json 只有 18 份符合当前 schema —— 属系统性版本漂移，非本包独有缺陷。",
     "remediation": "重发信封：把 claims 移入 outputs 或删除，provenance 增补 source_uri=tensor://reports/11267；或由平台提供 schema 版本别名（v1.0 冻结版）。",
     "affected_scope": "wp-11267-01 的 kf_result.json（下游 02/03 工序若用当前 schema 校验会被拒）"
    },
    {
     "id": "F2",
     "severity": "low",
     "likelihood": "certain (计数)",
     "blocking": false,
     "title": "worktree_probe 的 reason 文本与 result 自相矛盾（14/23 资产写成 “path exists …” 却 result=unresolved），并泄漏生产者绝对工作树路径",
     "evidence": {
      "contradictory_entries": 14,
      "absolute_path_entries": 14,
      "sample": [
       [
        "A05",
        "C1_strong_efficiency",
        "path exists in TensorKnowledge worktree: C1_strong_efficiency"
       ],
       [
        "A06",
        "C2_weak_ratio",
        "path exists in TensorKnowledge worktree: C2_weak_ratio"
       ],
       [
        "A07",
        "C4_comm_fraction",
        "path exists in TensorKnowledge worktree: C4_comm_fraction"
       ]
      ]
     },
     "analysis": "探针模板把 check 文案固定为 “path exists in <repo> worktree: <name>”，而实际 result 由存在性判定得出；两者拼接后对不存在的路径也宣称 exists，读者只能靠 result 字段判读。同时 path 指向 /root/tp-agent/work/m15695/…（生产者临时工作树，已不可达），降低可复现性。",
     "remediation": "check 文案改为条件式（exists/missing 由 result 决定），路径字段改为仓库相对路径或工作树标识（producer=…）。",
     "affected_scope": "manifest 中 14 个资产的 resolution_check.worktree_probe（不含已 resolved 的 9 个）"
    },
    {
     "id": "F3",
     "severity": "medium",
     "likelihood": "certain (集群查询)",
     "blocking": false,
     "title": "cj308/cj313/cj314 登记为 declared_absent 与报告原文一致，但集群现状已 succeeded —— 下游不得把“无扩展点数据”当作永久结论",
     "evidence": {
      "report_quote": "`` （cj308 全量判据、cj313 P=1/2 点、cj314 P=4/8 点）在报告定稿时仍为 `queued` `` (L169)",
      "queue_probe": {
       "cj308": "succeeded node=n315 rc=0 submitted=11-10 11:40 age=3974.1min",
       "cj313": "succeeded node=n315 rc=0 submitted=11-10 11:53 age=3972.1min",
       "cj314": "succeeded node=n330 rc=0 submitted=11-10 11:53 age=3971.1min"
      },
      "probe_tool": "run_cluster(action=ps, job_id=cj30x)"
     },
     "analysis": "登记口径要求“登记报告声明为空”，上游据此把三个作业记为 declared_absent —— 对报告原文是忠实的（报告定稿时确为 queued）；但三个作业现均为 succeeded/rc=0，说明 P=16/P=32 扩展点数据已可获取。这不是上游的缺陷，是时效性风险：若 03 抽取把“集群算力未到位”写成 claim，或 05 综述据此判“扩展性不可验证”，就会把一个已消失的阻塞当作事实。",
     "remediation": "不要求 01 返工；建议平台对 declared_absent 附 freshness_checked_at，或在补测工序用 cj308/313/314 工件刷新扩展点数字。",
     "affected_scope": "下游 03（claim 抽取）/05（综述）对扩展性结论的表述"
    },
    {
     "id": "F4",
     "severity": "low",
     "likelihood": "certain",
     "blocking": false,
     "title": "cluster_job 资产的 locator 只有裸作业号，“缺失”语义仅由所在句承载",
     "evidence": {
      "locator_quote": "`cj308` (L169)",
      "sentence": "`向 外协方双节点集群递交的三个作业` (L168)",
      "line": 169
     },
     "analysis": "locator.quote=`cj308` 逐字可定位（K2 通过），但单看引文无法自证 declared_absent；语义要靠 note 与上下文句。对“零手抄”不构成违规（引文逐字），但对“证据自足”是弱化。",
     "remediation": "把 locator 扩到所在句（char span 覆盖整句），或在 resolution_check 里记录句级 quote。",
     "affected_scope": "A16/A17/A18"
    },
    {
     "id": "F5",
     "severity": "info",
     "likelihood": "n/a",
     "blocking": false,
     "title": "派生计数 distinct_referenced_paths=15 未能被审核口径复现（审核员口径 11）",
     "evidence": {
      "manifest_distinct_referenced_paths": 15,
      "reviewer_backticked_paths": 10,
      "reproduced": {
       "body_image_links": "7/7",
       "figure_references_total": "14/14"
      }
     },
     "analysis": "图片类派生计数（7 图链接、14 处图引用）逐项复现；路径去重数因口径不同（是否计入模块点分名、目录 token、glob 形式）差 4，属定义差异，非错误。",
     "remediation": "在 method_notes 中写明该计数的口径；不影响产物可用性。",
     "affected_scope": "manifest.counts"
    },
    {
     "id": "F6",
     "severity": "info",
     "likelihood": "certain",
     "blocking": false,
     "title": "A00 文档型 locator 的 span 覆盖全文而 quote 只是标题行（span≠quote）",
     "evidence": {
      "span": [
       0,
       7482
      ],
      "quote_len": 47,
      "all_locators_entry_exact": true,
      "detail": 1
     },
     "analysis": "method=document 的 locator 用全文 span 表示“登记的是整份文档”，identity 引文另置；其 all_locators[0] 的 0–47 精确对齐标题行。按逐字符口径（md[s:e]==quote）该条不成立，需靠 method 字段区分，审核时已单列，不计为缺陷。",
     "remediation": "可选：method=document 时把 quote 设为整篇正文，或增设 identity_quote 字段。",
     "affected_scope": "A00"
    }
   ],
   "observations": [
    {
     "id": "O1-criteria-coverage",
     "text": "判据 C1–C6 中只有 3 个（未测量的 C1/C2/C4）被登记为资产；C3/C5/C6 已测量出数值，未作资产登记",
     "criteria_in_report": [
      "C1_strong_efficiency",
      "C2_weak_ratio",
      "C3_parallel_vs_serial_l2",
      "C4_comm_fraction",
      "C5_iteration_reduction",
      "C6_load_balance"
     ],
     "criteria_keys": [
      "C1",
      "C2",
      "C3",
      "C4",
      "C5",
      "C6"
     ],
     "registered_as_asset": [
      "C1",
      "C2",
      "C4",
      "MPIComm"
     ],
     "criteria_not_registered": [
      "C3",
      "C5",
      "C6"
     ],
     "scope_declared_by_producer": [
      "claim extraction (claims == [])"
     ]
    }
   ],
   "checks_not_run": [
    {
     "check": "复跑上游 tensorphysics.fem_parallel.verification 流水线",
     "status": "not_run",
     "reason": "审核对象是资产登记而非报告结论；且 P=16/P=32 需集群资源，属补测工序范围"
    },
    {
     "check": "报告性能数字（S(P)/E(P)/iters/rel L2）的可信度重算",
     "status": "not_run",
     "reason": "本工序判语义保真：报告原文是登记的事实基准，不重算其物理量；数字重算归 05 综述/平台门"
    },
    {
     "check": "cj308/cj313/cj314 工件（fetch）内容核验",
     "status": "not_run",
     "reason": "只查了队列终态（succeeded），未取回工件，故不对扩展点数值作任何断言"
    },
    {
     "check": "生产者运行时刻的可信时间戳/签名",
     "status": "not_run",
     "reason": "工作树内无签名设施，仅有产物自身 generated_at 字段"
    }
   ],
   "overstated_claims": [
    {
     "claim": "上游 verification.json C2_schema_pass=pass / 生产者叙述“draft-2020-12 校验 schemas/kf_result.v1.schema.json”",
     "status": "true at emission, false under current schema",
     "evidence": "F1：当前 schema additionalProperties=false 且 provenance 必需 source_uri"
    },
    {
     "claim": "上游自检 9/9 checks pass 且 acceptance 6/6",
     "status": "partially reproduced",
     "evidence": "审核员 15 项独立复核 13 pass / 2 needs-fix / 0 fail；上游自检未覆盖探针文案自相矛盾（F2）与派生计数口径（F5）"
    },
    {
     "claim": "报告⑤.9“集群算力未到位，P=16/P=32 没有任何集群数据”",
     "status": "stale (report-time true, now false)",
     "evidence": "F3：cj308/cj313/cj314 均 succeeded"
    }
   ],
   "disposition": {
    "decision": "needs-fix（非阻断：manifest 事实内容可用；阻断项仅信封 schema 与探针文案两处元数据）",
    "required_fixes": [
     "F1 重发信封（顶层 claims 移入 outputs；provenance 补 source_uri）",
     "F2 探针 check 文案条件化 + 路径改仓库相对"
    ],
    "advisory": [
     "F3 下游 03/05 不得把“无扩展点数据”写成事实；建议补测工序用 cj308/313/314 工件刷新",
     "F4 locator 扩到句级",
     "F5 记录派生计数口径",
     "F6 document 型 locator 口径写清"
    ],
    "escalation": "无需升级"
   },
   "reviewer_repro_cmd": "python3 docs/kf/wp-11267-04/review_wp-11267-04.py && python3 docs/kf/wp-11267-04/build_review.py",
   "generated_at": "2026-11-14T03:55:32+00:00",
   "repo_head": "445efce0fb14750df98a995d4c0667c7519b55ee"
  },
  "review_events.json": [
   {
    "event_id": "E1",
    "at": "2026-11-14T03:55:32+00:00",
    "actor": "kf-worker/m19785",
    "action": "review_started",
    "object": "wp-11267-01",
    "detail": {
     "source_hash_recomputed": "sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f",
     "hash_match": true
    }
   },
   {
    "event_id": "E2",
    "at": "2026-11-14T03:55:32+00:00",
    "actor": "kf-worker/m19785",
    "action": "source_refetched",
    "detail": {
     "via": "GET /tensor/reports/11267",
     "chars": 7482,
     "bytes_utf8": 11574
    }
   },
   {
    "event_id": "E3",
    "at": "2026-11-14T03:55:32+00:00",
    "actor": "kf-worker/m19785",
    "action": "checks_executed",
    "detail": {
     "checks": 15,
     "pass": 13,
     "needs_fix": 2,
     "fail": 0
    }
   },
   {
    "event_id": "E4",
    "at": "2026-11-14T03:55:32+00:00",
    "actor": "kf-worker/m19785",
    "action": "external_probe",
    "detail": {
     "cluster_jobs": [
      "cj308",
      "cj313",
      "cj314"
     ],
     "observed": "succeeded/rc=0"
    }
   },
   {
    "event_id": "E5",
    "at": "2026-11-14T03:55:32+00:00",
    "actor": "kf-worker/m19785",
    "action": "findings_raised",
    "detail": {
     "finding_ids": [
      "F1",
      "F2",
      "F3",
      "F4",
      "F5",
      "F6"
     ],
     "severities": {
      "F1": "medium",
      "F2": "low",
      "F3": "medium",
      "F4": "low",
      "F5": "info",
      "F6": "info"
     }
    }
   },
   {
    "event_id": "E6",
    "at": "2026-11-14T03:55:32+00:00",
    "actor": "kf-worker/m19785",
    "action": "disposition_set",
    "detail": {
     "verdict": "needs-fix",
     "blocking_items": []
    }
   },
   {
    "event_id": "E7",
    "at": "2026-11-14T03:55:32+00:00",
    "actor": "kf-worker/m19785",
    "action": "verified_flags_written",
    "detail": {
     "count": 0,
     "reason": "verification 由平台门计算，本工序不写 verified"
    }
   }
  ]
 }
}
```
