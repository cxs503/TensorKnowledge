# KF-RESULT wp-5687-04

**工序**：04-independent-review（red-team-reviewer） · **审核对象**：wp-5687-01（01-asset-registration）
· **报告**：report_id=5687 · **结论**：**pass**（advisory，非 verified 标记）

## ① 本工序做了什么

对 report 5687（IN18-T2 战史官编年史与指标计算器成熟化）的上游资产登记包 **wp-5687-01** 做独立审核：
不看生产者的解释，只拿「报告 markdown 原始字节 + 上游机器产物（kf_result.json / asset_manifest.json /
verification.json）」重建执行路径，逐条重算它的每一个可机器判定的断言，再判 pass / needs-fix。

审核口径（动手前预声明，事后不可改）：verdict=pass 需（a）13 条门判据全绿且（b）零 blocking 缺陷；
blocking 仅限五类 B1–B5（源哈希不可复算 / locator 引文非逐字 / 伪造分辨率状态 / 把 claim 说成 verified /
信封 JSON-schema 非法）。覆盖度与命名类缺陷记为非阻塞项，不影响门判据结论。

实测：18 条检查 → pass 15 / fail 3 / not_run 0；
门判据 13/13 绿；缺陷 6 条（blocking 0，
medium 1，low 5）。**wp-5687-01 的核心契约成立**：
源哈希三方一致（契约/信封/manifest 均为 `sha256:a4eaa764c52e072a87f6629009b94e3a5ae97d4aab543fe851599a732fcfeb3d`），
7 条 locator 引文全部在声明行逐字命中，11 个 asset 无伪造 resolved，claims 为空且无 verified 标记。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET /api/v1/tensor/reports/5687`（Bearer 登录 token），取 `markdown` 字段并复算
   sha256 = `sha256:a4eaa764c52e072a87f6629009b94e3a5ae97d4aab543fe851599a732fcfeb3d`，与契约 source_hash 比对一致后才开工（不一致即 B1 直接拦）。
2. **锁身份**：把上游三件产物与报告原文双向快照进 `docs/kf/wp-5687-04/upstream_snapshot/`，
   记 SHA256SUMS，审核结论只对这些字节负责（本单只读报告 5687，未触碰其它 report_id）。
3. **重算而非转述**：`verify_wp5687_01.py` 独立实现 18 条检查——JSON/schema、源哈希与字符/字节数、
   平台元数据（title/scenario/mission/tags/created_at）、asset_id 去重、summary 计数复算、
   **locator 引文逐字命中（quote ⊂ 声明行 且 ⊂ 全文，1-based 行号）**、figures 元数据、分辨率状态反证
   （resolved 必须能重新算出哈希；metadata_only 必须声明无字节）、claims 诚实性、声明输出哈希、
   上游 verification.json 六条断言重放、artifact 端点 404 复核、路径覆盖枚举、distinct 路径归一、schema_note 时效。
4. **工具链**：Python 3 标准库 + `jsonschema`（按 `schemas/kf_result.v1.schema.json` 校验信封）+ pytest 8 条不变量
   + matplotlib 出图；关键设置：`--offline` 只用快照字节复跑，保证结论不依赖活库漂移。
5. **判据先于动手**：复核器内置 DECISION_RULE 常量（`declared_before_running: true`），
   门判据集合固定为 C1–C13，事后不调阈值。

```bash
# repro_cmd（一键复跑；工作树根为仓库检出，产物落 docs/kf/wp-5687-04/）
python3 docs/kf/wp-5687-04/verify_wp5687_01.py \
  - && python3 -m pytest docs/kf/wp-5687-04/test_verify_wp5687_01.py -q \
  && python3 docs/kf/wp-5687-04/make_figure.py \
  && python3 docs/kf/wp-5687-04/make_report.py
# 无网重放（仅快照字节）：python3 docs/kf/wp-5687-04/verify_wp5687_01.py --offline
```

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `review_report.json` | 本轮审核唯一结果对象：decision/checks/findings/provenance |
| `checks.json` | 18 条机器检查明细 + 7 条 locator 逐字复核 + 覆盖枚举 |
| `kf_result.json` | 工序结果信封（package_id/wp-5687-04，provenance.source_hash 锚定报告字节） |
| `verify_wp5687_01.py` | 可复跑复核器（--offline 仅用快照字节，无网可重放） |
| `test_verify_wp5687_01.py` | 8 条不变量测试（pytest） |
| `upstream_snapshot/` | 被审产物的逐字节快照 + SHA256SUMS（4 个身份哈希） |
| `fig1_review_evidence.png` | 图1 检查矩阵 / locator 逐字复核散点 / 缺陷分级 |

被审产物身份（审核只对这些字节负责）：
`asset_manifest.json` sha256:3766d86fed43dfb57fd1e16566678314182fb59c1a195e322075a6ceaa5d2e0c · `kf_result.json` sha256:77e5d6d8c97a42353959dc2eddc6d1391060cd5812476d85adf625023d5d37ff
· `verification.json` sha256:dd4f04b5331b69c4e619e7b3c89ce76d4a07ac0cb6b2fd7b7db93655e318ea7d · 报告 markdown sha256:a4eaa764c52e072a87f6629009b94e3a5ae97d4aab543fe851599a732fcfeb3d。

## ④ 证据定位表（claim / 字段 → 原文引文片段，逐字）

locator 逐字复核（行号 1-based，引文字符数为实测长度）：

| asset_id | 声明行 | 引文字符 | 逐字命中 | 引文片段 |
|---|---|---|---|---|
| r5687:ref:01 | 22 | 65 | ✓ | 「按任务书「若 T1 未并 main 则自带最小采集并声明」：本单自带 ˋto…」 |
| r5687:ref:02 | 30 | 62 | ✓ | 「2. **5 项指标**（ˋtools/chronicle/metrics.…」 |
| r5687:ref:03 | 36 | 60 | ✓ | 「3. **交叉验证**（ˋcrosscheck.pyˋ）：独立手算 SQL（…」 |
| r5687:ref:04 | 36 | 60 | ✓ | 「3. **交叉验证**（ˋcrosscheck.pyˋ）：独立手算 SQL（…」 |
| r5687:ref:05 | 40 | 80 | ✓ | 「工件 ˋartifacts/chronicle/ˋ（GLOBAL_CH…」 |
| r5687:ref:06 | 84 | 50 | ✓ | 「基准 = 独立手算 SQL（crosscheck.py，查询文本与 metr…」 |
| r5687:ref:07 | 84 | 50 | ✓ | 「基准 = 独立手算 SQL（crosscheck.py，查询文本与 metr…」 |

| claim / 字段 | 证据（原文引文或机器工件） |
|---|---|
| 源哈希三方一致（C4） | 重算 `sha256:a4eaa764c52e072a87f6629009b94e3a5ae97d4aab543fe851599a732fcfeb3d` = 契约 = 信封 = manifest `sha256` 字段 |
| 声明字符/字节可复算（C5） | manifest `source_chars`=4236、`source_bytes_utf8`=6382，与重算一致 |
| 报告元数据保真（C6） | 平台记录 mission_id=4975、created_at=2026-11-07T01:36:36.516756+00:00，manifest 全等 |
| 图元数据保真（C10） | 报告正文 `图 1：并行度曲线（M1）+ 饱和度时序（M4），1h 桶，UTC。`；manifest `{name,caption}` 与平台 figures[0] 全等（caption 取自平台记录而非 markdown，二者措辞不同，故按字段级比对） |
| 分辨率状态无伪造（C11） | 「工件 ˋartifacts/chronicle/ˋ（GLOBAL_CHRON…」（该桶仅 1 个 resolved=源 markdown，其余 10 个 unresolved/metadata_only） |
| claims 空且无 verified（C12） | manifest `claims: []`、`claims_note` 声明 01 工序不抽取；报告全文无 “verified” 字样（机器判定 False） |
| 端点探测可信（C15） | 独立重发 `/tensor/reports/5687/artifacts`、`/tensor/artifacts?report_id=5687` → 两者均 404，与 manifest `artifact_endpoint_probe` 全等 |
| 上游 verification 六条可重放（C14） | 本机重放 6 条断言（valid_json / schema_pass / source_locator_resolvable / source_hash_matches / no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status），逐条 pass 值一致，mismatches=∅ |

缺陷定位（severity / blocking / 断言 → 处置）：

| ID | severity | blocking | 被质疑的断言 | 建议处置 |
|---|---|---|---|---|
| F1 | low | 否 | manifest schema_note asserts no kf_* JSON Schema is shipped in the repository | drop the schema_note or pin it to the producing commit. |
| F2 | low | 否 | asset inventory covers every path-like reference declared in the report | register the artifact directory as one unresolved directory-level asset, or state in limitations that bundle members without declared names are out of inventory scope. |
| F3 | low | 否 | ref:05 path_reference identifies the declared file | carry the containing directory: path_reference=artifacts/chronicle/GLOBAL_CHRONICLE.md. |
| F4 | low | 否 | summary.distinct_referenced_paths=5 counts distinct referenced files | normalize by basename or record the raw-string definition explicitly (it does document occurrence-level identity, so this is a metric-label nit). |
| F5 | medium | 否 | upstream verification.json check 'source_locator_resolvable: pass (unresolvable=[])' reads as 'all references resolved' | split into locator_wellformed (pass) and targets_resolved (7 unresolved) or rename. |
| F6 | low | 否 | the report's data assets (4 tables / 6 parameter rows with SQL provenance) are neither registered nor declared out of scope | add 'data/table references are outside the 01 kind vocabulary' to limitations. |

## ⑤ 注意点与局限

- **独立性是程序性的，不是组织性的**：审核者与生产者同模型族；独立性靠「只读报告字节 + 上游机器产物、
  不看生产者解释、从零重算」保证，未做异模式交叉或多审核者一致性检验。
- **未跑项如实登记**：`tools/chronicle/*.py` 的字节级核验（不在 TensorKnowledge 交付树内，上游已按设计列
  unresolved）、报告 M1–M5 数值结论的复算（属 03/05 工序）、平台门重算（verification 由平台计算，本单不声称）、
  生产者在其它 report_id 上的写入边界（无写日志可查）。
- **本单不产生 verified**：verdict 仅供门参考；`decision.not_a_verified_mark=true`，测试
  `test_no_verified_mark_asserted` 用键名白名单机制防回归。
- **自查踩坑（如实记）**：复核器首版 C15 用数值 404 与 manifest 的字符串 `http_404` 直接比较导致假 FAIL，
  已改为规范化后比较（比对内容未变，只是口径统一）；出图时本机无 CJK 字形，图内标签改英文、中文留正文，
  避免豆腐块。
- **非阻塞结论的适用边界**：6 条缺陷都是清单覆盖与标签准确性层面，改法在 manifest/verification
  文本层即可闭环，不需要重新登记资产；因此判 pass 而非 needs-fix。
- **数据源漂移**：结论锚定 sha256:a4eaa764c52e… 这一版 markdown；报告若被编辑，C4 立即变红，
  本结论随之失效（这正是设计意图）。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 依据 |
|---|---|---|
| valid_json | ✓ | review_report.json / kf_result.json 机器解析通过（C1/C2，pytest 覆盖） |
| schema_pass | ✓ | kf_result.json 按 `schemas/kf_result.v1.schema.json` 校验通过（C3；pytest `test_envelope_conforms_to_repo_schema`） |
| reviewer_independent | ✓（有保留） | 未读生产者解释，独立重算；保留项见⑤第 1 条（同模型族） |
| upstream_packages_completed | ✓ | 上游 wp-5687-01 六条 verification 断言本机重放全一致（C14），信封 schema 合法（C3） |
| review_prompt_not_copied_from_producer | ✓ | 本单判据由 04 契约 + B1–B5 预声明规则生成，未复用生产者文本 |
| reviewer_context_excludes_producer_explanation | ✓ | 上下文仅报告 markdown + 上游三件机器产物（快照哈希可核） |
| do_not_mark_claims_as_verified | ✓ | 无 verified 断言（C12 + pytest 键名白名单） |
| 六段齐全 / repro_cmd 可复跑 | ✓ | 本报告 ①–⑥；repro_cmd 实测跑通（pytest 8 passed） |

**结论**：wp-5687-01 **pass**（门判据 13/13，
blocking 0，非阻塞 6）。
未完成/未跑部分已在⑤逐条声明，未粉饰。

```json
{
  "package_id": "wp-5687-04",
  "task_type": "04-independent-review",
  "report_id": "5687",
  "provenance": {
    "source_hash": "sha256:a4eaa764c52e072a87f6629009b94e3a5ae97d4aab543fe851599a732fcfeb3d",
    "source_field": "markdown",
    "producer": "agent/m15838 red-team reviewer",
    "emitted_at": "2026-11-12T02:53:51.162092+00:00",
    "notes": "independent review of wp-5687-01; verdict advisory, no claim marked verified"
  },
  "outputs": {
    "review_report.json": {
      "package_id": "wp-5687-04",
      "task_type": "04-independent-review",
      "contract_version": "1.0",
      "reviewed_package": "wp-5687-01",
      "reviewed_task_type": "01-asset-registration",
      "report_id": "5687",
      "reviewer_role": "red-team-reviewer",
      "independence": {
        "context_inputs": [
          "report 5687 markdown (sha256-pinned)",
          "upstream machine product: kf_result.json / asset_manifest.json / verification.json"
        ],
        "excluded": [
          "producer narrative / report_body.md / producer worktree notes"
        ],
        "producer_explanation_read": false,
        "shared_worktree_with_producer": false,
        "not_self_review": true,
        "limitation": "same model family as producer; independence is procedural (fresh recomputation from report bytes), not organisational."
      },
      "decision": {
        "verdict": "pass",
        "verdict_is_advisory": true,
        "not_a_verified_mark": true,
        "rule": {
          "verdict_pass_requires": [
            "all gate checks pass",
            "zero blocking findings (B1-B5)"
          ],
          "blocking_classes": {
            "B1": "source hash unrecomputable or divergent",
            "B2": "locator quote not contiguous verbatim substring at declared line",
            "B3": "fabricated resolution status",
            "B4": "claim presented as verified / extracted claims hidden by empty claims list",
            "B5": "JSON or schema invalidity of delivered envelope"
          },
          "declared_before_running": true
        },
        "gate_checks_green": "13/13",
        "blocking_findings": 0,
        "non_blocking_findings": 6,
        "rationale": "core contract (hash-pinned source, contiguous verbatim locators, no fabricated resolution, no verified marks, schema-valid envelope) is independently reproduced; remaining findings are inventory coverage and label-accuracy defects."
      },
      "checks": [
        {
          "id": "C1",
          "check": "asset_manifest.json parses as JSON",
          "result": "pass",
          "detail": "11 assets parsed",
          "blocking_class": null
        },
        {
          "id": "C2",
          "check": "kf_result.json parses as JSON",
          "result": "pass",
          "detail": "top keys=['outputs', 'package_id', 'provenance', 'report_id', 'task_type']",
          "blocking_class": null
        },
        {
          "id": "C3",
          "check": "kf_result.json conforms to schemas/kf_result.v1.schema.json",
          "result": "pass",
          "detail": "validated against schemas/kf_result.v1.schema.json",
          "blocking_class": null
        },
        {
          "id": "C4",
          "check": "report markdown sha256 matches contract + manifest declarations",
          "result": "pass",
          "detail": "actual=a4eaa764c52e072a87f6629009b94e3a5ae97d4aab543fe851599a732fcfeb3d contract=a4eaa764c52e072a87f6629009b94e3a5ae97d4aab543fe851599a732fcfeb3d env=a4eaa764c52e072a87f6629009b94e3a5ae97d4aab543fe851599a732fcfeb3d manifest=a4eaa764c52e072a87f6629009b94e3a5ae97d4aab543fe851599a732fcfeb3d",
          "blocking_class": null
        },
        {
          "id": "C5",
          "check": "declared chars/bytes_utf8 match recomputed size",
          "result": "pass",
          "detail": "chars=4236 bytes_utf8=6382 declared=4236/6382",
          "blocking_class": null
        },
        {
          "id": "C6",
          "check": "manifest provenance metadata equals platform report record",
          "result": "pass",
          "detail": "mission_id=4975 tags=6 created_at=2026-11-07T01:36:36.516756+00:00 report_id=5687",
          "blocking_class": null
        },
        {
          "id": "C7",
          "check": "asset ids distinct",
          "result": "pass",
          "detail": "11 ids, 11 distinct",
          "blocking_class": null
        },
        {
          "id": "C8",
          "check": "summary.asset_count/by_kind equals recomputed tally",
          "result": "pass",
          "detail": "asset_count=11 len(assets)=11 by_kind_recomputed={'report_markdown/resolved': 1, 'embedded_figure/metadata_only': 3, 'source_code_reference/unresolved': 6, 'document_reference/unresolved': 1}",
          "blocking_class": null
        },
        {
          "id": "C9",
          "check": "every markdown_line locator quote is contiguous verbatim text at declared line",
          "result": "pass",
          "detail": "checked=7 bad=[]",
          "blocking_class": null
        },
        {
          "id": "C10",
          "check": "embedded_figure assets equal platform figures[] name/caption/index",
          "result": "pass",
          "detail": "report figures=['fig1_parallelism_saturation.png', 'fig2_coverage_heatmap.png', 'fig3_bp_coverage.png'] manifest=['fig1_parallelism_saturation.png', 'fig2_coverage_heatmap.png', 'fig3_bp_coverage.png']",
          "blocking_class": null
        },
        {
          "id": "C11",
          "check": "no fabricated resolution: resolved assets re-hash, metadata_only assets claim no bytes",
          "result": "pass",
          "detail": "resolved=['r5687:source'] fabricated=[] metadata_only_without_payload=True",
          "blocking_class": null
        },
        {
          "id": "C12",
          "check": "claims list empty and no verified mark asserted",
          "result": "pass",
          "detail": "manifest claims=0 envelope claims=0 'verified' in report markdown=False",
          "blocking_class": null
        },
        {
          "id": "C13",
          "check": "declared output sha256/bytes equal the delivered manifest bytes",
          "result": "pass",
          "detail": "sha256=3766d86fed43dfb57fd1e16566678314182fb59c1a195e322075a6ceaa5d2e0c bytes=10450",
          "blocking_class": null
        },
        {
          "id": "C14",
          "check": "all 6 upstream verification.json assertions reproduce here",
          "result": "pass",
          "detail": "reproduced={'valid_json': True, 'schema_pass': True, 'source_locator_resolvable': True, 'source_hash_matches': True, 'no_duplicate_ids': True, 'all_claims_have_evidence_or_explicit_unresolved_status': True} mismatches={}",
          "blocking_class": null
        },
        {
          "id": "C15",
          "check": "artifact_endpoint_probe statuses reproduce (both 404)",
          "result": "pass",
          "detail": "live={'/tensor/reports/5687/artifacts': 404, '/tensor/artifacts?report_id=5687': 404} normalized={'/tensor/reports/5687/artifacts': 'http_404', '/tensor/artifacts?report_id=5687': 'http_404'} declared={'/tensor/reports/5687/artifacts': 'http_404', '/tensor/artifacts?report_id=5687': 'http_404'}",
          "blocking_class": null
        },
        {
          "id": "C16",
          "check": "no report-declared path silently absent from the asset inventory",
          "result": "fail",
          "detail": "path_like_tokens=['artifacts/chronicle/', 'crosscheck.py', 'tools/chronicle/collector.py', 'tools/chronicle/metrics.py'] unregistered=['artifacts/chronicle/'] declared_bundle_lines=['artifacts/chronicle/']",
          "blocking_class": null
        },
        {
          "id": "C17",
          "check": "summary.distinct_referenced_paths is basename-normalized",
          "result": "fail",
          "detail": "declared=5 raw_paths=['GLOBAL_CHRONICLE.md', 'crosscheck.py', 'metrics.py', 'tools/chronicle/collector.py', 'tools/chronicle/metrics.py'] basename_normalized=4 ['GLOBAL_CHRONICLE.md', 'collector.py', 'crosscheck.py', 'metrics.py']",
          "blocking_class": null
        },
        {
          "id": "C18",
          "check": "manifest schema_note ('no kf_* schema shipped') holds at repository HEAD",
          "result": "fail",
          "detail": "schemas/kf_*.json at HEAD=['kf_result.v1.schema.json']",
          "blocking_class": null
        }
      ],
      "locator_verification": [
        {
          "asset_id": "r5687:ref:01",
          "line": 22,
          "quote_chars": 65,
          "verbatim_at_line": true,
          "quote": "按任务书「若 T1 未并 main 则自带最小采集并声明」：本单自带 `tools/chronicle/collector.py`"
        },
        {
          "asset_id": "r5687:ref:02",
          "line": 30,
          "quote_chars": 62,
          "verbatim_at_line": true,
          "quote": "2. **5 项指标**（`tools/chronicle/metrics.py`，纯函数 + PG 装载分离，离线可测）："
        },
        {
          "asset_id": "r5687:ref:03",
          "line": 36,
          "quote_chars": 60,
          "verbatim_at_line": true,
          "quote": "3. **交叉验证**（`crosscheck.py`）：独立手算 SQL（查询文本不复用 metrics.py 构造）"
        },
        {
          "asset_id": "r5687:ref:04",
          "line": 36,
          "quote_chars": 60,
          "verbatim_at_line": true,
          "quote": "3. **交叉验证**（`crosscheck.py`）：独立手算 SQL（查询文本不复用 metrics.py 构造）"
        },
        {
          "asset_id": "r5687:ref:05",
          "line": 40,
          "quote_chars": 80,
          "verbatim_at_line": true,
          "quote": "   工件 `artifacts/chronicle/`（GLOBAL_CHRONICLE.md + 5 指标 CSV + crosscheck + 3 图）。"
        },
        {
          "asset_id": "r5687:ref:06",
          "line": 84,
          "quote_chars": 50,
          "verbatim_at_line": true,
          "quote": "基准 = 独立手算 SQL（crosscheck.py，查询文本与 metrics.py 不同源）："
        },
        {
          "asset_id": "r5687:ref:07",
          "line": 84,
          "quote_chars": 50,
          "verbatim_at_line": true,
          "quote": "基准 = 独立手算 SQL（crosscheck.py，查询文本与 metrics.py 不同源）："
        }
      ],
      "coverage_enumeration": {
        "path_like_tokens": [
          "artifacts/chronicle/",
          "crosscheck.py",
          "tools/chronicle/collector.py",
          "tools/chronicle/metrics.py"
        ],
        "unregistered": [
          "artifacts/chronicle/"
        ],
        "registered_path_references": [
          "GLOBAL_CHRONICLE.md",
          "crosscheck.py",
          "metrics.py",
          "tools/chronicle/collector.py",
          "tools/chronicle/metrics.py"
        ]
      },
      "findings": [
        {
          "id": "F1",
          "severity": "low",
          "blocking": false,
          "claim_under_review": "manifest schema_note asserts no kf_* JSON Schema is shipped in the repository",
          "evidence": {
            "quote_manifest": "No kf_result/asset_manifest JSON Schema file is shipped in this repository (schemas/ has no kf_*.json); shape follows the wp-542-01 contract keys (package_id/task_type/report_id/provenance/outputs) and is self-described below.",
            "fact": "schemas/kf_result.v1.schema.json exists at HEAD (git log -1 -- schemas/kf_result.v1.schema.json)",
            "note": "producer checkout lacks it, so the note is true for that tree but stale for HEAD; the envelope nevertheless validates against it (check C3)"
          },
          "reproduction": "python3 -c \"import json,jsonschema;jsonschema.validate(json.load(open('docs/kf/wp-5687-04/upstream_snapshot/kf_result.json')),json.load(open('schemas/kf_result.v1.schema.json')))\"",
          "remedy": "drop the schema_note or pin it to the producing commit."
        },
        {
          "id": "F2",
          "severity": "low",
          "blocking": false,
          "claim_under_review": "asset inventory covers every path-like reference declared in the report",
          "evidence": {
            "report_quote": "工件 `artifacts/chronicle/`（GLOBAL_CHRONICLE.md + 5 指标 CSV + crosscheck + 3 图）。",
            "line": 40,
            "unregistered_tokens": [
              "artifacts/chronicle/"
            ],
            "registered": [
              "GLOBAL_CHRONICLE.md",
              "crosscheck.py",
              "metrics.py",
              "tools/chronicle/collector.py",
              "tools/chronicle/metrics.py"
            ]
          },
          "reproduction": "python3 docs/kf/wp-5687-04/verify_wp5687_01.py  (check C16)",
          "remedy": "register the artifact directory as one unresolved directory-level asset, or state in limitations that bundle members without declared names are out of inventory scope."
        },
        {
          "id": "F3",
          "severity": "low",
          "blocking": false,
          "claim_under_review": "ref:05 path_reference identifies the declared file",
          "evidence": {
            "manifest": {
              "asset_id": "r5687:ref:05",
              "path_reference": "GLOBAL_CHRONICLE.md"
            },
            "report_quote": "工件 `artifacts/chronicle/`（GLOBAL_CHRONICLE.md + 5 指标 CSV + crosscheck + 3 图）。",
            "line": 40,
            "why": "the report places the file under artifacts/chronicle/; the basename alone resolves to a different (nonexistent) candidate path. Status is unresolved, so no false resolve."
          },
          "reproduction": "python3 docs/kf/wp-5687-04/verify_wp5687_01.py  (checks C9/C11)",
          "remedy": "carry the containing directory: path_reference=artifacts/chronicle/GLOBAL_CHRONICLE.md."
        },
        {
          "id": "F4",
          "severity": "low",
          "blocking": false,
          "claim_under_review": "summary.distinct_referenced_paths=5 counts distinct referenced files",
          "evidence": {
            "declared": 5,
            "basename_normalized": 4,
            "paths": [
              "GLOBAL_CHRONICLE.md",
              "crosscheck.py",
              "metrics.py",
              "tools/chronicle/collector.py",
              "tools/chronicle/metrics.py"
            ],
            "why": "tools/chronicle/metrics.py and metrics.py are the same file counted twice"
          },
          "reproduction": "python3 docs/kf/wp-5687-04/verify_wp5687_01.py  (check C17)",
          "remedy": "normalize by basename or record the raw-string definition explicitly (it does document occurrence-level identity, so this is a metric-label nit)."
        },
        {
          "id": "F5",
          "severity": "medium",
          "blocking": false,
          "claim_under_review": "upstream verification.json check 'source_locator_resolvable: pass (unresolvable=[])' reads as 'all references resolved'",
          "evidence": {
            "quote": "{\"pass\": true, \"detail\": \"checked 11 locators; unresolvable=[]\"}",
            "fact": "7 of 11 assets carry resolution.status=unresolved; the check actually measures locator well-formedness, not target resolution",
            "impact": "a downstream gate keyed on this name could record 7 unresolved references as resolved"
          },
          "reproduction": "python3 -c \"import json;m=json.load(open('docs/kf/wp-5687-04/upstream_snapshot/asset_manifest.json'));print(sum(a['resolution']['status']=='unresolved' for a in m['assets']))\"",
          "remedy": "split into locator_wellformed (pass) and targets_resolved (7 unresolved) or rename."
        },
        {
          "id": "F6",
          "severity": "low",
          "blocking": false,
          "claim_under_review": "the report's data assets (4 tables / 6 parameter rows with SQL provenance) are neither registered nor declared out of scope",
          "evidence": {
            "report_quote": "| missions 区间行 | 4642 | `-- src: select id, created_at, finished_at, status, claimed_by, repo from tensor_dev_missions where created_at <= :t_end` |",
            "why": "kind vocabulary has no data/table kind and limitations do not say data assets are excluded"
          },
          "reproduction": "python3 docs/kf/wp-5687-04/verify_wp5687_01.py  (check C16)",
          "remedy": "add 'data/table references are outside the 01 kind vocabulary' to limitations."
        }
      ],
      "checks_not_run": [
        "byte-level verification of the referenced source files (tools/chronicle/*.py) — outside this worktree, listed unresolved by the upstream package itself",
        "verification of the report's numeric claims (M1-M5, crosscheck) — those belong to the 03/05 line, not to 01-asset-registration",
        "platform-side gate recomputation (verification is platform-computed; not claimed here)",
        "producer-side write-boundary adherence across other report_ids — no access to the producer's write log; only report 5687 artefacts were inspected"
      ],
      "overstated_claims": [
        "upstream verification.json check name source_locator_resolvable (see F5)",
        "manifest schema_note about missing kf_* schema (see F1)"
      ],
      "provenance": {
        "source_uri": "tensor://reports/5687",
        "source_field": "markdown",
        "source_hash": "sha256:a4eaa764c52e072a87f6629009b94e3a5ae97d4aab543fe851599a732fcfeb3d",
        "reviewed_artifacts": {
          "kf_result.json": "sha256:77e5d6d8c97a42353959dc2eddc6d1391060cd5812476d85adf625023d5d37ff",
          "asset_manifest.json": "sha256:3766d86fed43dfb57fd1e16566678314182fb59c1a195e322075a6ceaa5d2e0c",
          "verification.json": "sha256:dd4f04b5331b69c4e619e7b3c89ce76d4a07ac0cb6b2fd7b7db93655e318ea7d",
          "upstream_worktree_package_dir": "docs/kf/wp-5687-01"
        },
        "snapshot_dir": "docs/kf/wp-5687-04/upstream_snapshot",
        "emitted_at": "2026-11-12T02:53:51.162092+00:00"
      }
    }
  }
}
```
