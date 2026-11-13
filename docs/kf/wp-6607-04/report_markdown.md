# KF-RESULT wp-6607-04

tags: kf-wp:wp-6607-04

## 1. 本工序做了什么

独立审核（task_type=04-independent-review，lane C）：对 report_id=6607 的上游登记包 **wp-6607-01** 做红队复核。审核上下文只有两样东西：报告 6607 的 markdown 原文（本单独立登录独立拉取，字节哈希 `sha256:b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1`），以及平台已发布的上游结果信封本身（其唯一 json 块）。生产者的叙述段落、脚本、测试与工作树一律排除在证据之外。

做法是**逐条复算**而不是读一遍觉得对：把上游信封拆成 34 条可判定断言，每条都从原始字节重算一遍（定位器切片、行号、唯一性、章节归属、计数直方图、schema、scope、外加 2 条负对照证明检查不是恒真）。结果：**33/34 通过，1 失败**，登记事实（9 个定位器）无一条与原文矛盾；查出 2 条登记缺陷，全部**不阻塞**，verdict = **needs-fix**。

本工序**不做**物理核验：φ_J 是否等于 0.84、FSS 指数 ν 是否可信都不是 01 工序的验收面，本单也不把任何结论标成 verified（verification 由平台门计算）。

## 2. 怎么做的（步骤 / 工具 / 关键设置）

1. **自己取源**：独立 `POST /api/v1/auth/login` → `GET /api/v1/tensor/reports/6607`，把 markdown 按 UTF-8 落盘（`work/wp-6607-04/source/report_6607.md`）后本地重算 sha256，与契约声明相等（sha256:b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1 ✓）；7642 chars / 11166 bytes / 137 lines / 无 CRLF。直连 `psql -d tensorplatform -tA -c "select markdown from tensor_reports where id=6607"` 被拒（`ERROR:  permission denied for table tensor_reports`），API 是唯一信道。
2. **取上游 KO**：报告列表按 `scenario_key=dem-granular-jamming` 检索，命中 tensor://reports/14665（`KF-RESULT wp-6607-01`，status=`published`），只取它的 ```json 块（实测 fence 数 = 1）作为被审对象。
3. **复算检查面**（`scripts/kf/wp_6607_04_review.py`，34 条）：
   - 源身份：hash/bytes/chars/lines/CRLF、记录字段（id/title/scenario_key/status）、上游包可发现性与 tags；
   - 信封与 schema：`kf_result.v1` 校验、`asset_manifest.v1` 校验、package_id/task_type/report_id scope、provenance.source_field、claims 为空、全文无 `verified` 字样；
   - 定位器（9 个资产 × 5 面）：quote 是否原文子串；`md[start_char:end_char] == quote`；声明行号 vs 由偏移重算的行号；quote 在原文中的出现次数 = 1；偏移是否落在声明的 §N 内、且声明里的标识符 token 落在同一行；
   - 计数：assets=9、by_class 直方图、by_resolution（零值键补齐）、asset_id 唯一性、integrity 三面、A09 note 里的 29/5 是否能在原文对上；
   - 覆盖普查：正则扫全文所有被引用的文件路径（含 §8 bash 代码块内的），与登记标签做后缀匹配；
   - **负对照 2 条**：把声明偏移当 UTF-8 字节偏移去切，检验会崩（证明 char/byte 口径有别 → 通过不是恒真）；把最后一个 quote 改 3 个字符，检验在原文里搜不到。
4. **零手抄**：报告里出现的每个数字都由 `runs/wp-6607-04/review_findings.json` 程序化注入；写盘前断言 finding 的引文是原文（或上游信封）逐字子串。
5. **保留未审项**（见 §5）：9 个被登记文件在 DEM 仓里是否存在、三张图的像素、φ_J 数字的物理正确性，本单都**没有审**，不记为通过。

## 3. 产出物清单（文件名 → 要点）

| 输出文件 | 要点 |
|---|---|
| `docs/kf/wp-6607-04/review_report.json` | 交付物：verdict=`needs-fix`、blocking=`False`、34 条检查、2 条 findings、独立性声明（included/excluded/not_reviewed）、2 条 claims |
| `runs/wp-6607-04/review_findings.json` | 检查台账：逐条 upstream_claim ↔ recomputed ↔ verdict，含 coverage census 的 10 条被引路径与 9 个登记标签 |
| `docs/kf/wp-6607-04/kf_result.json` | 提交给平台的结果信封（本次报告里唯一的 json 块） |
| `docs/kf/wp-6607-04/figures/wp-6607-04.png` | 审核证据图：检查面通过/失败、`登记 9 vs 普查 10`、9/9 定位器保真 |
| `work/wp-6607-04/source/report_6607.md` | 原文快照（逐字节，sha256 与契约相等） |
| `work/wp-6607-04/upstream/report_14665.md` | 上游信封快照（被审对象） |
| `runs/wp-6607-04/asset_manifest_schema_relaxed.json` | 复算用 schema（仓库版把 const 钉死在 report 448，见 §5.3） |
| `scripts/kf/wp_6607_04_review.py` / `_emit.py` / `fetch_report_6607.py` | 复跑与出图脚本 |

## 4. 证据定位表（claim/字段 → 原文引文 + 复算值）

引文列全部是报告 6607 markdown 的逐字子串（写盘前断言）；复算值列来自 `runs/wp-6607-04/review_findings.json`。

| 检查 | 上游断言 / 检查口径（截断） | 本单复算值（截断） | 判定 |
|---|---|---|---|
| `source_hash_matches_contract` | `"sha256:b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1"` | `"sha256:b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1"` | ✓ |
| `source_hash_matches_upstream` | `"sha256:b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1"` | `"sha256:b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1"` | ✓ |
| `source_bytes` | `11166` | `11166` | ✓ |
| `source_chars` | `7642` | `7642` | ✓ |
| `record_title` | `"jamming 体积分数重锁：FIRE/CG 能量极小 + 双周期 + 有限尺寸标度（IN32-N02）"` | `"jamming 体积分数重锁：FIRE/CG 能量极小 + 双周期 + 有限尺寸标度（IN32-N02）"` | ✓ |
| `record_scenario_key` | `"dem-granular-jamming"` | `"dem-granular-jamming"` | ✓ |
| `upstream_package_discoverable` | `"report tagged kf-wp:wp-6607-01"` | `"report_id=14665 title='KF-RESULT wp-6607-01'"` | ✓ |
| `upstream_single_json_block` | `1` | `1` | ✓ |
| `kf_result_schema_pass` | `"valid per kf_result.v1"` | `true` | ✓ |
| `asset_manifest_schema_pass` | `"valid per asset_manifest.v1"` | `true` | ✓ |
| `single_report_scope` | `["6607"]` | `["6607"]` | ✓ |
| `claims_empty` | `[]` | `[]` | ✓ |
| `no_verified_marks` | `"no verified status"` | `[]` | ✓ |
| `quotes_verbatim` | `"9 quotes"` | `"all substring"` | ✓ |
| `spans_copy_exact` | `"9 char_spans"` | `"md[s:e]==quote for all"` | ✓ |
| `lines_match_offsets` | `"9 declared start_line"` | `"recomputed lines"` | ✓ |
| `quotes_unique_in_source` | `"unique=True"` | `"9 quotes count==1"` | ✓ |
| `declared_section_contains_offset` | `"9 in_report_section labels"` | `[]` | ✓ |
| `assets_total` | `9` | `9` | ✓ |
| `by_class_histogram` | `{"artifact": 1, "doc": 1, "figure": 3, "script": 3, "test": 1}` | `{"artifact": 1, "doc": 1, "figure": 3, "script": 3, "test": 1}` | ✓ |
| `by_resolution_counts` | `{"resolved_in_source": 9, "referenced_unresolved": 0, "declared_absent": 0}` | `{"resolved_in_source": 9, "referenced_unresolved": 0, "declared_absent": 0}` | ✓ |
| `asset_ids_unique` | `"A01-A09"` | `9` | ✓ |
| `integrity_flags` | `{"quote_uniqueness": true, "hash_recomputed_locally": true, "hash_matches_contra` | `{"quote_uniqueness": true, "hash_recomputed_locally": true, "hash_matches_contra` | ✓ |
| `note_numbers_trace_to_source` | `"Pytest test suite (29 cases, 5 negative controls)"` | `"29 test functions / 5 negative controls"` | ✓ |
| `body_path_reference_census` | `"9 assets registered"` | `{"distinct_cited_paths": 10, "registered": 9, "unregistered": ["src/tensordem/gr` | ✗ |
| `nc_byte_offsets_would_fail` | `"char_span is char-indexed"` | `{"assets_where_byte_slice_differs": 9}` | ✓ |
| `nc_corrupted_quote_rejected` | `"verbatim test discriminates"` | `{"corrupted_quote_in_source": false}` | ✓ |

**两条发现（引文逐字可定位）**

- **F1-unregistered-code-module-reference**（severity=`major`，blocking=`False`）：登记了 9 个资产，但原文 §2 还点名了实现层模块 `src/tensordem/granular2d/minimizer.py`；普查得 10 条被引路径 vs 9 条登记，差 1 条 = `src/tensordem/granular2d/minimizer.py`。影响：下游抽取拿不到核心求解器模块的定位器，而信封正文的措辞「解析出 9 个可定位附件/工件」读起来像穷尽。修法：登记该模块（class=script，resolution=resolved_in_source），或在 counts 里写明纳入规则。
- **F2-counting-rule-not-declared**（severity=`minor`，blocking=`False`）：「9 个」这个数没有声明计数口径（哪些类、哪些路径样式算资产），同一份原文存在多种合法数法，机器门无法独立复算该数字。修法：在 counts 里加 `inclusion_rule`。

**误差判定（关键量 vs 基准，逐项回答是否 <3%）**

| 量 | 登记/上游值 | 本单复算值 | 相对偏差 | 是否 < 3% |
|---|---|---|---|---|
| 登记资产数（9）vs 普查被引路径（10） | 9 | 10 | +11.11% | **否** |
| 定位器切片保真 `md[s:e]==quote` | 9 | 9 | +0.00% | **是** |
| 定位器落声明行 | 9 | 9 | +0.00% | **是** |
| quote 原文唯一性 | 9 | 9 | +0.00% | **是** |
| 偏移落在声明 §N 内 | 9 | 9 | +0.00% | **是** |
| envelope 内 report_id 越界（0 允许） | 0 | 0 | +0.00% | **是** |

说明：本工序没有物理基准量可对标（审核对象是登记保真度而非 φ_J 数值），因此「误差」用**登记值 vs 复算值**定义（相对偏差 =(复算−登记)/登记）；唯一超 3% 的项是资产覆盖数 9 vs 10（+11.11%，即漏登记 1 条），就是 F1，如实列为不通过项。每个量在 `review_findings.json` 里都有对应的 check_id 可追溯。

## 5. 注意点与局限

1. **审核不进入 DEM 仓**：9 个被登记文件（`benchmarks/*`、`tests/*`、`artifacts/jamming_protocol/jamming_protocol.json`、`docs/…md`、3 张 png）在本交付树里都不存在，审核只能确认「原文确实这样引用」与「上游没有断言它们存在」，不能确认它们的内容。
2. **图未审**：信封不含图片字节，三个 `figures` 端点也不在 01 工序的产物面内，图内容本单不审。
3. **schema 纪律坑**：`schemas/asset_manifest.v1.schema.json` 把 `package_id`/`report_id`/`source.uri` 用 `const` 钉死在 **report 448**（`"wp-448-01"` / `"448"`），直接拿它校验任何别的包都会失败——这是 schema 资产本身的缺陷，不是 wp-6607-01 的错。本单把这三处 const 放宽成 pattern 后再校验（`runs/wp-6607-04/asset_manifest_schema_relaxed.json`），结论：结构合法。
4. **失败面归口**：34 条检查里唯一 FAIL 是覆盖普查；上游 9 条定位器本身没有一条被证伪，所以 verdict 是 `needs-fix` 而非 `fail`，且 blocking=False（不阻塞 03/05 工序）。
5. **独立性边界**：本单能看到上游信封里的 note 文本（例如 A09 的 `29 cases / 5 negative controls`），但那是对信封自身字段的复算（数字回原文对得上），不构成采用生产者解释。
6. **计数口径敏感性**：普查正则只认带扩展名的路径 token；像 `--mu 0.5 --kt-ratio 0.5`、`monotone=True` 这类非路径记号不计入，故 10 不是「该报告引用的一切」而是「一切文件路径」。

## 6. 自检（逐条对照 acceptance）

- [✓] `valid_json`：`review_report.json` 与本报告的 json 块均为合法 JSON（emit 脚本内 `json.loads` 校验）。
- [✓] `schema_pass`：信封对 `schemas/kf_result.v1.schema.json` 校验通过（jsonschema.validate）。
- [✓] `reviewer_independent`：独立登录独立取源；上下文只含原文 + 上游信封 + 仓内 schema，生产者叙述/脚本/工作树已在 `review_report.independence.reviewer_context_excluded` 逐项列明。
- [✓] `upstream_packages_completed`：wp-6607-01 → tensor://reports/14665，title=`KF-RESULT wp-6607-01`，status=`published`，fence 数 1，信封 schema 通过。
- [✓] 约束 `do_not_mark_claims_as_verified`：全篇无 verified 标记，claims 只用 supported / partially-supported。
- [✓] 约束 `review_prompt_not_copied_from_producer`：审核判据由本单自建（34 条复算式检查 + 2 条负对照），未复用生产者脚本或自检清单。
- [!] 诚实项：唯一未通过的是覆盖普查（F1）与计数口径未声明（F2）——如实写为 `needs-fix`（不阻塞），不粉饰为 pass。

**复现**

```bash
python3 scripts/kf/fetch_report_6607.py      # 取源 + 钉哈希
python3 scripts/kf/wp_6607_04_review.py      # 34 条复算 → review_findings.json + review_report.json
python3 scripts/kf/wp_6607_04_emit.py        # 图 + 报告 + 信封，含自检断言
python3 -m pytest tests/ -q                  # 仓内回归
```

## 7. 图

- `docs/kf/wp-6607-04/figures/wp-6607-04.png`：(a) 34 条复算检查按检查面分组的通过/失败；(b) 登记资产 9 vs 普查被引路径 10 （缺口 = src/tensordem/granular2d/minimizer.py）；(c) 9 个定位器的 5 面保真（全绿）。
- 本单是审核/文档工序，没有场量可画云图；图的作用是把审核证据可视化，每个数字都从 `review_findings.json` 读出，不手抄。

```json
{
  "package_id": "wp-6607-04",
  "task_type": "04-independent-review",
  "report_id": "6607",
  "provenance": {
    "source_hash": "sha256:b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1",
    "source_field": "markdown",
    "producer": "agent/m15849",
    "emitted_at": "2026-11-12T02:45:00Z",
    "notes": "Independent review of wp-6607-01 against the report bytes; the reviewer only saw the report markdown and the published upstream envelope (json block), not the producer's explanation."
  },
  "outputs": {
    "review_report.json": {
      "package_id": "wp-6607-04",
      "task_type": "04-independent-review",
      "report_id": "6607",
      "target_package": "wp-6607-01",
      "reviewer_role": "red-team-reviewer",
      "reviewer_independent": true,
      "independence": {
        "reviewer_context_included": [
          "report 6607 markdown (verbatim, freshly fetched)",
          "upstream envelope of wp-6607-01 as published (report 14665, single json block)",
          "repo schemas (kf_result.v1, asset_manifest.v1)"
        ],
        "reviewer_context_excluded": [
          "producer prose sections 1/2/5/6 of the upstream report (only the json block is treated as the KO)",
          "producer scripts, tests and worktree of agent/m15592",
          "any producer explanation of the registration logic"
        ],
        "not_reviewed": [
          "existence or content of the 9 registered files in the DEM worktree (they live outside this repository)",
          "the three figures' pixels (no figure bytes reachable from the envelope)",
          "physical validity of the report's phi_J numbers (upstream task is registration, not verification)"
        ]
      },
      "verdict": "needs-fix",
      "verdict_scope": "registration fidelity of the upstream package against the report bytes; NOT a physics verification",
      "blocking": false,
      "summary": "34 recomputed checks, 33 pass / 1 fail; 2 finding(s), 0 blocking. All 9 registered locators reproduce exactly from the source bytes (quote == md[start:end], declared line, unique occurrence); 1 cited path(s) missing from the manifest.",
      "findings": [
        {
          "finding_id": "F1-unregistered-code-module-reference",
          "severity": "major",
          "blocking": false,
          "scope": "wp-6607-01 asset_manifest.assets",
          "evidence": {
            "unregistered_paths": [
              "src/tensordem/granular2d/minimizer.py"
            ],
            "quote": "src/tensordem/granular2d/minimizer.py",
            "source_field": "markdown",
            "quote_source": "report_markdown",
            "note": "cited in §2 as the implementation module of the static potential and both minimizers, i.e. a first-class provenance target"
          },
          "impact": "downstream extraction/linking has no locator for the core solver module; the manifest's 'parsed 9 locatable assets' reads as exhaustive",
          "remediation": "register the module reference (class=script, resolution=resolved_in_source) or state the inclusion rule explicitly (e.g. 'benchmark/doc/figure/test/artifact entries only')"
        },
        {
          "finding_id": "F2-counting-rule-not-declared",
          "severity": "minor",
          "blocking": false,
          "scope": "asset_manifest.counts",
          "evidence": {
            "upstream_quote": "解析出 9 个可定位附件/工件",
            "quote_source": "upstream_package",
            "note": "envelope prose asserts exhaustiveness without an inclusion rule; the census finds 10 distinct cited paths"
          },
          "impact": "the same source admits several legal counts, so the machine gate cannot recompute the number without guessing the rule",
          "remediation": "declare inclusion_rule in counts (classes + path patterns)"
        }
      ],
      "checks": [
        {
          "check_id": "source_hash_matches_contract",
          "upstream_assertion": "sha256:b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1",
          "assertion_origin": "upstream_package",
          "recomputed": "sha256:b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1",
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "source_hash_matches_upstream",
          "upstream_assertion": "sha256:b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1",
          "assertion_origin": "upstream_package",
          "recomputed": "sha256:b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1",
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "source_bytes",
          "upstream_assertion": 11166,
          "assertion_origin": "upstream_package",
          "recomputed": 11166,
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "source_chars",
          "upstream_assertion": 7642,
          "assertion_origin": "upstream_package",
          "recomputed": 7642,
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "source_lines_recomputed",
          "upstream_assertion": "not registered by manifest",
          "assertion_origin": "upstream_package",
          "recomputed": 137,
          "verdict": "pass",
          "notes": "informational: the manifest registers chars/bytes only; lines recomputed here to drive the locator line check"
        },
        {
          "check_id": "source_crlf_absent",
          "upstream_assertion": "utf-8/lf",
          "assertion_origin": "upstream_package",
          "recomputed": false,
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "record_id",
          "upstream_assertion": "6607",
          "assertion_origin": "upstream_package",
          "recomputed": "6607",
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "record_title",
          "upstream_assertion": "jamming 体积分数重锁：FIRE/CG 能量极小 + 双周期 + 有限尺寸标度（IN32-N02）",
          "assertion_origin": "upstream_package",
          "recomputed": "jamming 体积分数重锁：FIRE/CG 能量极小 + 双周期 + 有限尺寸标度（IN32-N02）",
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "record_scenario_key",
          "upstream_assertion": "dem-granular-jamming",
          "assertion_origin": "upstream_package",
          "recomputed": "dem-granular-jamming",
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "record_status_published",
          "upstream_assertion": "published",
          "assertion_origin": "upstream_package",
          "recomputed": "published",
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "upstream_package_discoverable",
          "upstream_assertion": "report tagged kf-wp:wp-6607-01",
          "assertion_origin": "upstream_package",
          "recomputed": "report_id=14665 title='KF-RESULT wp-6607-01'",
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "upstream_single_json_block",
          "upstream_assertion": 1,
          "assertion_origin": "upstream_package",
          "recomputed": 1,
          "verdict": "pass",
          "notes": "result channel must contain exactly one json block"
        },
        {
          "check_id": "kf_result_schema_pass",
          "upstream_assertion": "valid per kf_result.v1",
          "assertion_origin": "upstream_package",
          "recomputed": true,
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "asset_manifest_schema_pass",
          "upstream_assertion": "valid per asset_manifest.v1",
          "assertion_origin": "upstream_package",
          "recomputed": true,
          "verdict": "pass",
          "notes": " | repo schema pins package_id/report_id/uri to report 448; consts relaxed in runs/wp-6607-04/asset_manifest_schema_relaxed.json"
        },
        {
          "check_id": "envelope_package_id",
          "upstream_assertion": "wp-6607-01",
          "assertion_origin": "upstream_package",
          "recomputed": "wp-6607-01",
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "envelope_task_type",
          "upstream_assertion": "01-asset-registration",
          "assertion_origin": "upstream_package",
          "recomputed": "01-asset-registration",
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "single_report_scope",
          "upstream_assertion": [
            "6607"
          ],
          "assertion_origin": "upstream_package",
          "recomputed": [
            "6607"
          ],
          "verdict": "pass",
          "notes": "no foreign report_id inside the envelope"
        },
        {
          "check_id": "provenance_source_field",
          "upstream_assertion": "markdown",
          "assertion_origin": "upstream_package",
          "recomputed": "markdown",
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "claims_empty",
          "upstream_assertion": [],
          "assertion_origin": "upstream_package",
          "recomputed": [],
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "no_verified_marks",
          "upstream_assertion": "no verified status",
          "assertion_origin": "upstream_package",
          "recomputed": [],
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "quotes_verbatim",
          "upstream_assertion": "9 quotes",
          "assertion_origin": "upstream_package",
          "recomputed": "all substring",
          "verdict": "pass",
          "notes": "failing assets: []"
        },
        {
          "check_id": "spans_copy_exact",
          "upstream_assertion": "9 char_spans",
          "assertion_origin": "upstream_package",
          "recomputed": "md[s:e]==quote for all",
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "lines_match_offsets",
          "upstream_assertion": "9 declared start_line",
          "assertion_origin": "upstream_package",
          "recomputed": "recomputed lines",
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "quotes_unique_in_source",
          "upstream_assertion": "unique=True",
          "assertion_origin": "upstream_package",
          "recomputed": "9 quotes count==1",
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "declared_section_contains_offset",
          "upstream_assertion": "9 in_report_section labels",
          "assertion_origin": "upstream_package",
          "recomputed": [],
          "verdict": "pass",
          "notes": "mismatches: []"
        },
        {
          "check_id": "assets_total",
          "upstream_assertion": 9,
          "assertion_origin": "upstream_package",
          "recomputed": 9,
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "by_class_histogram",
          "upstream_assertion": {
            "artifact": 1,
            "doc": 1,
            "figure": 3,
            "script": 3,
            "test": 1
          },
          "assertion_origin": "upstream_package",
          "recomputed": {
            "artifact": 1,
            "doc": 1,
            "figure": 3,
            "script": 3,
            "test": 1
          },
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "by_resolution_counts",
          "upstream_assertion": {
            "resolved_in_source": 9,
            "referenced_unresolved": 0,
            "declared_absent": 0
          },
          "assertion_origin": "upstream_package",
          "recomputed": {
            "resolved_in_source": 9,
            "referenced_unresolved": 0,
            "declared_absent": 0
          },
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "asset_ids_unique",
          "upstream_assertion": "A01-A09",
          "assertion_origin": "upstream_package",
          "recomputed": 9,
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "integrity_flags",
          "upstream_assertion": {
            "quote_uniqueness": true,
            "hash_recomputed_locally": true,
            "hash_matches_contract": true
          },
          "assertion_origin": "upstream_package",
          "recomputed": {
            "quote_uniqueness": true,
            "hash_recomputed_locally": true,
            "hash_matches_contract": true
          },
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "note_numbers_trace_to_source",
          "upstream_assertion": "Pytest test suite (29 cases, 5 negative controls)",
          "assertion_origin": "upstream_package",
          "recomputed": "29 test functions / 5 negative controls",
          "verdict": "pass",
          "notes": ""
        },
        {
          "check_id": "body_path_reference_census",
          "upstream_assertion": "9 assets registered",
          "assertion_origin": "upstream_package",
          "recomputed": {
            "distinct_cited_paths": 10,
            "registered": 9,
            "unregistered": [
              "src/tensordem/granular2d/minimizer.py"
            ]
          },
          "verdict": "fail",
          "notes": "every backticked file path in the report must be registered or explicitly excluded"
        },
        {
          "check_id": "nc_byte_offsets_would_fail",
          "upstream_assertion": "char_span is char-indexed",
          "assertion_origin": "upstream_package",
          "recomputed": {
            "assets_where_byte_slice_differs": 9
          },
          "verdict": "pass",
          "notes": "negative control: interpreting the declared offsets as UTF-8 byte offsets breaks 9/9 spans, so passing the span check is informative"
        },
        {
          "check_id": "nc_corrupted_quote_rejected",
          "upstream_assertion": "verbatim test discriminates",
          "assertion_origin": "upstream_package",
          "recomputed": {
            "corrupted_quote_in_source": false
          },
          "verdict": "pass",
          "notes": "negative control: a 3-char mutation of the last quote is not found in the source"
        }
      ],
      "evidence_index": {
        "ledger": "runs/wp-6607-04/review_findings.json",
        "source_snapshot": "work/wp-6607-04/source/report_6607.md",
        "upstream_snapshot": "work/wp-6607-04/upstream/report_14665.md"
      },
      "claims_reviewed": [
        {
          "claim_id": "upstream-asset-coverage-9-complete",
          "text": "9 locatable assets were parsed out of the report",
          "status": "partially-supported",
          "evidence": [
            {
              "upstream_quote": "解析出 9 个可定位附件/工件",
              "source_field": "markdown",
              "quote_origin": "upstream_package_markdown"
            }
          ],
          "unresolved_reason": "9 registered entries reproduce, but the census finds 10 distinct cited paths; the manifest neither registers nor excludes src/tensordem/granular2d/minimizer.py"
        },
        {
          "claim_id": "upstream-locators-resolve-to-source",
          "text": "every locator quote is a verbatim substring at the declared span",
          "status": "supported",
          "evidence": [
            {
              "quote": "artifacts/jamming_protocol/jamming_protocol.json",
              "source_field": "markdown",
              "quote_origin": "report_markdown"
            },
            {
              "quote": "docs/granular2d_jamming_energy_minimization.md",
              "source_field": "markdown",
              "quote_origin": "report_markdown"
            },
            {
              "quote": "pressure_vs_phi.png",
              "source_field": "markdown",
              "quote_origin": "report_markdown"
            },
            {
              "quote": "phi_j_vs_N.png",
              "source_field": "markdown",
              "quote_origin": "report_markdown"
            },
            {
              "quote": "residual_history.png",
              "source_field": "markdown",
              "quote_origin": "report_markdown"
            },
            {
              "quote": "benchmarks/jamming_protocol_ablation.py",
              "source_field": "markdown",
              "quote_origin": "report_markdown"
            },
            {
              "quote": "benchmarks/jamming_double_periodic_verification.py",
              "source_field": "markdown",
              "quote_origin": "report_markdown"
            },
            {
              "quote": "benchmarks/jamming_protocol_report.py",
              "source_field": "markdown",
              "quote_origin": "report_markdown"
            },
            {
              "quote": "tests/test_granular2d_energy_minimization.py",
              "source_field": "markdown",
              "quote_origin": "report_markdown"
            }
          ]
        }
      ],
      "quote_policy": "every field named 'quote' is a verbatim substring of the report markdown; strings taken from the upstream envelope are stored under 'upstream_quote'/'upstream_assertion' with quote_origin/assertion_origin",
      "do_not_mark_claims_as_verified": true,
      "generated_from": "scripts/kf/wp_6607_04_review.py"
    }
  },
  "claims": [
    {
      "claim_id": "wp-6607-01-locator-fidelity",
      "text": "every locator of wp-6607-01 reproduces from the report bytes: quote == markdown[start_char:end_char], on the declared line, unique occurrence, inside the declared section",
      "status": "supported",
      "evidence": [
        {
          "quote": "artifacts/jamming_protocol/jamming_protocol.json",
          "source_field": "markdown",
          "note": "registered asset locator; re-sliced from the report bytes at the declared char_span, on the declared line, unique"
        },
        {
          "quote": "docs/granular2d_jamming_energy_minimization.md",
          "source_field": "markdown",
          "note": "registered asset locator; re-sliced from the report bytes at the declared char_span, on the declared line, unique"
        },
        {
          "quote": "benchmarks/jamming_protocol_ablation.py",
          "source_field": "markdown",
          "note": "registered asset locator; re-sliced from the report bytes at the declared char_span, on the declared line, unique"
        },
        {
          "quote": "tests/test_granular2d_energy_minimization.py",
          "source_field": "markdown",
          "note": "registered asset locator; re-sliced from the report bytes at the declared char_span, on the declared line, unique"
        },
        {
          "quote": "pressure_vs_phi.png",
          "source_field": "markdown",
          "note": "registered asset locator; re-sliced from the report bytes at the declared char_span, on the declared line, unique"
        }
      ]
    },
    {
      "claim_id": "wp-6607-01-asset-coverage-exhaustive",
      "text": "the 9 registered assets are the complete set of cited artefacts",
      "status": "partially-supported",
      "evidence": [
        {
          "quote": "`src/tensordem/granular2d/minimizer.py`",
          "source_field": "markdown",
          "note": "cited module reference absent from the manifest"
        }
      ],
      "unresolved_reason": "census finds 10 distinct cited paths vs 9 registered; the manifest states no inclusion rule"
    }
  ]
}
```
