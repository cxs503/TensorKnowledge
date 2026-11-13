# KF-RESULT wp-14214-01

**tags**: kf-wp:wp-14214-01, asset-registration, report-14214, lane-B, TensorKnowledge, draft
**package_id**: wp-14214-01 ｜ **task_type**: 01-asset-registration ｜ **report_id**: 14214
**lane**: B ｜ **repo**: TensorKnowledge ｜ **source_uri**: `tensor://reports/14214` ｜ **分层**: TensorPapers|analysis|B

---

## ① 本工序做了什么

只做 `report_id=14214`（《W23 论文线：430 篇增量扫描 + 45 课题双轨重标 + research_plan 销项推进 63/73 + 成稿门四门→九门（放行2/阻断22）+ 10 单派发》）的**资产登记**（工序 `01-asset-registration`）：

1. **确认身份**：独立重算 markdown `sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9`，与契约 `source_hash` 逐字节一致；
   `chars=6258`（= python str 长度，与契约 `chars` 相同），UTF-8 字节 `8770`
   （CJK 正文两口径必然不同，此处写明口径）。
2. **登记资产 24 项**（code_file=9, code_glob=1, data_dir=1, figure_png_reference=5, inline_markdown_table=4, registry=1, report_markdown=1, research_plan_set=1, test_file=1），每项给逐字引文 + 行号 + 字符偏移 + 命中次数。
3. **登记正文内可解析块结构 4 个 pipe 表**
   （只记数据行数/表头列数/行区间，**不抽取任何数值**）；fenced 块 0 个。
4. **登记报告声明的图件 5 张**（路径 + 正文声明的 sha256_16），并与记录 `figures[]`
   （name + caption）逐图交叉绑定。
5. **算术/跨字段一致性登记 6 条**（`integrity_observations`）：状态只有 `consistent` /
   `unresolved`，**不含任何 verified 结论**。
6. **不做抽取、不分类、不产生 claim**（契约 `objective.classify_report_type: false`；`claims=[]`）。
   **没有任何结论被标成 verified**——哈希相等只是机械身份校验，verification 由平台门计算。

边界：只读 `GET /api/v1/tensor/reports/14214` 这一份记录；未读写任何其它 report_id；
未改写上游或其它工作包的产物。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **契约入参**：`package_id=wp-14214-01`、`report_id=14214`、`source_field=markdown`、
   `source_hash=sha256:edc85090…2d1af9`、`chars=6258`、`scenario_key=paper-line-w23`；
   六条 acceptance 直接落到 ⑥ 自检表。
2. **取源**：`POST /api/v1/auth/login`（凭据只从 `TENSOR_AGENT_USER`/`TENSOR_AGENT_PASS` 环境变量读，
   不落盘）→ `GET /api/v1/tensor/reports/14214`（Bearer），取 `markdown` 全文；
   同记录的 `title/scenario_key/mission_id/status/created_at/tags/figures` 一并登记为元数据。
3. **独立哈希**：`hashlib.sha256(markdown.encode('utf-8'))` 与契约 `source_hash` 逐字节比较，
   不一致即 `SystemExit`（失败不出产物）；同时核 `len(markdown)==6258`。
4. **零手抄定位**：脚本内引文种子逐条 `str.find`；种子不唯一时**按整行机械扩展**到唯一
   （`unique_quote`，`match_how` 记录扩展方式），任一未命中/不唯一即 `SystemExit`，不写 manifest。
   解析结果落 `docs/kf/wp-14214-01/locator_check.json`。
5. **表结构登记**：pipe 表由分隔行正则识别，只算 `data_rows` / `header_cells`。
6. **工件端点探测**：`/openapi.json`、`/tensor/reports/14214/artifacts`、`/tensor/reports/14214/figures`、
   `/tensor/artifacts?report_id=14214` 逐一探测（带 Bearer），见 ⑤：
   无端点提供被引用文件字节 → 这些资产 `resolution=referenced_unresolved`、`content_retrievable=false`。
7. **复跑**：`python3 scripts/kf_wp14214_01_register.py`（追加 `--no-fetch` 用包内 `source.md`
   离线复现，仅跳过联网取源与端点探测）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-14214-01/source.md` | 登记用 markdown 字节副本（8770 B / 6258 chars） |
| `docs/kf/wp-14214-01/sha256.txt` | 独立重算摘要 |
| `docs/kf/wp-14214-01/locator_check.json` | 23 条引文定位（行/字符偏移/命中次数/match_how） |
| `docs/kf/wp-14214-01/asset_manifest.json` | 契约输出 `asset_manifest.json`：24 资产 + 6 条一致性登记 |
| `docs/kf/wp-14214-01/kf_result.json` | `kf_result.v1` 信封（schema 校验 True） |
| `docs/kf/wp-14214-01/selfcheck.json` | 6 条 acceptance 机检 + 两份 schema 校验明细 |
| `docs/kf/wp-14214-01/report_body.md`、`docs/kf_result_wp-14214-01.md` | 本报告正文（同一内容两处落盘） |

资产清单（24 项）：

| asset_id | class | label | 节 | 定位行 | resolution |
|---|---|---|---|---|---|
| `A01` | report_markdown | 报告 markdown 原文（source_field=markdown） | (整篇) | 1 | resolved_in_source |
| `A02` | figure_png_reference | papers/figures/w23_window_composition.png | ④ | 73 | referenced_unresolved |
| `A03` | figure_png_reference | papers/figures/w23_track_split.png | ④ | 74 | referenced_unresolved |
| `A04` | figure_png_reference | papers/figures/w23_plan_progress.png | ④ | 75 | referenced_unresolved |
| `A05` | figure_png_reference | papers/figures/w23_draft_gate.png | ④ | 76 | referenced_unresolved |
| `A06` | figure_png_reference | papers/figures/w23_artifact_presence.png | ④ | 77 | referenced_unresolved |
| `A07` | code_glob | papers/tools/w23_*.py 面板（花括号聚合引用） | 附 | 101 | referenced_unresolved |
| `A08` | code_file | w23_extract.py | ② | 19 | referenced_unresolved |
| `A09` | code_file | w23_anchors.py | ② | 20 | referenced_unresolved |
| `A10` | code_file | w23_tracks.py | ② | 21 | referenced_unresolved |
| `A11` | code_file | w23_plan.py | ② | 22 | referenced_unresolved |
| `A12` | code_file | w23_draftgate.py | ② | 23 | referenced_unresolved |
| `A13` | code_file | w23_payloads.py | ② | 24 | referenced_unresolved |
| `A14` | code_file | w23_dispatch.py | ② | 24 | referenced_unresolved |
| `A15` | code_file | w23_planmd.py | ⑤ | 84 | referenced_unresolved |
| `A16` | code_file | w23_figures.py | ④ | 73 | referenced_unresolved |
| `A17` | test_file | test_w23_artifacts.py | 附 | 101 | referenced_unresolved |
| `A18` | data_dir | papers/data/w23-2026-11-11/ | 附 | 102 | referenced_unresolved |
| `A19` | research_plan_set | W23 新立 5 个 research_plan.md | 附 | 102 | referenced_unresolved |
| `A20` | registry | papers/registry.md | 附 | 103 | referenced_unresolved |
| `A21` | inline_markdown_table | pipe 表：指标 \| 数值 | ## ① 案例介绍（研究域与证据面） | 10 | resolved_in_source |
| `A22` | inline_markdown_table | pipe 表：指标 \| W22 \| W23 \| 变化 | ## ③ 计算结果（数字表，程序化注入） | 30 | resolved_in_source |
| `A23` | inline_markdown_table | pipe 表：task_key \| mission \| 状态 \| 模型 \| repo | ## ③ 计算结果（数字表，程序化注入） | 46 | resolved_in_source |
| `A24` | inline_markdown_table | pipe 表：关键量 \| 基准 \| 结果 \| 是否 <3% | ## ⑥ 误差判定（关键量 vs 基准） | 89 | resolved_in_source |

图件登记：

| 报告声明图件 | sha256_16（正文声明） | record.figures 绑定 |
|---|---|---|
| `papers/figures/w23_window_composition.png` | `00a0936204e0b70d` | 已绑定 |
| `papers/figures/w23_track_split.png` | `d889e66d3739a24e` | 已绑定 |
| `papers/figures/w23_plan_progress.png` | `371b8fc472428b13` | 已绑定 |
| `papers/figures/w23_draft_gate.png` | `3a48cfafc642d093` | 已绑定 |
| `papers/figures/w23_artifact_presence.png` | `4a1693ff2284f6e6` | 已绑定 |

聚合引用的机械展开：

| asset | expansion（机械展开） |
|---|---|
| `A07` | `papers/tools/w23_extract.py`<br>`papers/tools/w23_anchors.py`<br>`papers/tools/w23_plan.py`<br>`papers/tools/w23_tracks.py`<br>`papers/tools/w23_specs.py`<br>`papers/tools/w23_payloads.py`<br>`papers/tools/w23_dispatch.py`<br>`papers/tools/w23_draftgate.py`<br>`papers/tools/w23_planmd.py`<br>`papers/tools/w23_figures.py`<br>`papers/tools/w23_registry.py` |
| `A19` | `）：任务销项 = 至少产出 1 篇报告（判据达标或 honest FAIL 均算）；承接 = 重试单 goal 逐字点名前身；工件在位性按 research_plan.md 表格**列名定位**后在仓内 main 检出核验。
5. **成稿门加固**（` |

## ④ 证据定位表（字段 / 资产 → 原文逐字引文）

登记级字段全部由机器命中；下表引文即 `locator_check.json` 的内容（逐字、含行号与字符偏移）：

| locator | asset | 引文（逐字） | 行 | 字符偏移 | 命中 |
|---|---|---|---|---|---|
| L01 | `A02` | ```papers/figures/w23_window_composition.png`（sha256_16 `00a0936…`` | 73 | 3963 | 1 |
| L02 | `A03` | ```papers/figures/w23_track_split.png`（sha256_16 `d889e66d3739a2…`` | 74 | 4087 | 1 |
| L03 | `A04` | ```papers/figures/w23_plan_progress.png`（sha256_16 `371b8fc47242…`` | 75 | 4204 | 1 |
| L04 | `A05` | ```papers/figures/w23_draft_gate.png`（sha256_16 `3a48cfafc642d093``` | 76 | 4337 | 1 |
| L05 | `A06` | ```papers/figures/w23_artifact_presence.png`（sha256_16 `4a1693ff…`` | 77 | 4457 | 1 |
| L06 | `A07` | ```papers/tools/w23_{extract,anchors,plan,tracks,specs,payloads,…`` | 101 | 5774 | 1 |
| L07 | `A08` | ``**增量扫描**（`w23_extract.py`）`` | 19 | 547 | 1 |
| L08 | `A09` | ``**锚目录重建**（`w23_anchors.py`）`` | 20 | 675 | 1 |
| L09 | `A10` | ``**双轨重标**（`w23_tracks.py`）`` | 21 | 754 | 1 |
| L10 | `A11` | ``**销项收割**（`w23_plan.py`）`` | 22 | 880 | 1 |
| L11 | `A12` | ``**成稿门加固**（`w23_draftgate.py`）`` | 23 | 1018 | 1 |
| L12 | `A13` | ``**派单**（`w23_payloads.py``` | 24 | 1081 | 1 |
| L13 | `A14` | ```w23_dispatch.py`）`` | 24 | 1108 | 1 |
| L14 | `A15` | ```w23_planmd.py` 首版覆盖了`` | 84 | 5024 | 1 |
| L15 | `A16` | ```papers/tools/w23_figures.py`，输入 digest.json`` | 73 | 4039 | 1 |
| L16 | `A17` | ```test_w23_artifacts.py``` | 101 | 5884 | 1 |
| L17 | `A18` | ```papers/data/w23-2026-11-11/``` | 102 | 5913 | 1 |
| L18 | `A19` | ```papers/composite-laminate-verification/research_plan.md`` | 102 | 5948 | 1 |
| L19 | `A20` | ``registry：`papers/registry.md``` | 103 | 6209 | 1 |
| T01 | `A21` | `\| 指标 \| 数值 \|` | 10 | 395 | 1 |
| T02 | `A22` | `\| 指标 \| W22 \| W23 \| 变化 \|` | 30 | 1215 | 1 |
| T03 | `A23` | `\| task_key \| mission \| 状态 \| 模型 \| repo \|` | 46 | 1734 | 1 |
| T04 | `A24` | `\| 关键量 \| 基准 \| 结果 \| 是否 <3% \|` | 89 | 5233 | 1 |

一致性登记（`integrity_observations`）：

| obs | 类型 | 检查 | 计算值 | 结果 | 状态 |
|---|---|---|---|---|---|
| O1 | arithmetic | 窗口报告计数是否等于判词三态之和 | `{"PASS": 184, "FAIL": 138, "WITHHELD": 60, "sum": 382, "window_reports": 430, "difference": 48}` | unresolved_difference | unresolved |
| O2 | cross_field | 成稿门阻断计数：正文 vs 记录 title（/本包契约 title） | `{"body_blocked": 23, "record_title_blocked": 22, "difference": 1}` | conflict_unresolved | unresolved |
| O3 | cross_field | 「N 单派发」与派单回执表行数/唯一 task_key/mission 区间是否自洽 | `{"table_rows": 20, "distinct_task_keys": 10, "rows_with_numeric_mission": 10, "mission_range": [15092, 15101], "missions_contiguous": true, "title_stated_units": 10}` | consistent | resolved |
| O4 | arithmetic | 计划表 W22→W23→变化 三列是否逐行自洽 | `{"计划内 exp 任务": {"computed_delta": 14, "stated": "+14"}, "已销项": {"computed_delta": 12, "stated": "+12"}, "封口计划": {"computed_delta": 9, "stated": "+9"}}` | consistent | resolved |
| O5 | source_shape | 报告段结构是否包含 ①–⑥ 六段（行号由脚本扫描得到） | `{"heading_count": 8, "headings": [[1, "# W23 论文生产线研究总结：增量证据、双轨重标、research_plan 销项推进与成稿门加固"], [6, "## ① 案例介绍（研究域与证据面）"], [17, "## ② 怎么做的（方法 / 工具链）"], [26, "## ③ 计算结果（数字表，程序化注入）"], [71, "## ④ 结果图"], [79, "## ⑤ 注意点（坑与局限）"], [87, "## ⑥ 误差判定（关键量 vs 基准）"], [99, "## 附：工具与工件"]], "section_line": {"①": 6, "②": 17, "③": 26, "④": 71, "⑤": 79, "⑥": 87}, "all_six_present": true}` | complete_sections | resolved |
| O6 | cross_field | ⑥ 误差判定表的「是否 <3%」列自述到位情况 | `{"rows": 5, "column": "是否 <3%", "value_counts": {"是": 4, "不适用": 1}, "external_quantitative_error_rows": 0}` | author_declared_no_external_baseline | resolved |

## ⑤ 注意点与局限

1. **被引用工件不可取字节**：png / 脚本 / 数据目录 / research_plan / registry 只在正文里被点名，
   报告记录不携带其字节（端点探测见下表）——因此它们一律 `referenced_unresolved`：
   **只核了「路径字符串在正文里逐字存在」，没有核文件是否存在、也没核其与声明 sha256_16 是否相符**。

| 探测端点 | 结果 |
|---|---|
| `/openapi.json` | HTTP 404 |
| `/tensor/reports/14214/artifacts` | HTTP 404 |
| `/tensor/reports/14214/figures` | HTTP 404 |
| `/tensor/artifacts?report_id=14214` | HTTP 404 |

2. **O2 是真冲突，不粉饰**：正文 ③ 写「阻断 **23**」，而记录 `title`/`summary` 与本包契约 `title`
   写「阻断22」。本工序**只登记不裁决**（报告内无第三方口径可裁），状态 `unresolved`，绝不标 verified。
3. **O1 差额未归因**：184+138+60=382 ≠ 窗口 430，差 48 篇；报告未说明归属（未判/NULL 判词无声明），
   本工序不推断。
4. **人工初读假象（已由机器纠正）**：本工序首屏 `cat` 输出被终端截断，人工初读以为 markdown 缺 ① 段；
   机器解析显示第 1 行是 `# W23 论文生产线研究总结…`、第 6 行是 `## ① 案例介绍（研究域与证据面）`，
   ①–⑥ 六段齐全（O5）。故本包所有事实一律以 `str.find`/正则结果为准，不以肉眼首屏为准。
5. **不做精度判定**：本工序不产生领域量、不复算报告里的任何精度结论。报告 ⑥ 的「是否<3%」是
   报告作者给出的判据（多为恒等核/无外部基准），本工序的立场是**本工序无精度量可判**，不代填、不背书。
6. **hash 相等的含义边界**：相等只说明我读到的 markdown 与平台记录同一份（机械恒等），
   不代表内容正确，更不代表任何结论 verified。
7. **不越界**：未读其它 report_id、未改上游产物、未写任何「verified」字段。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| valid_json | ☑ PASS | asset_manifest.json / kf_result.json 均由 json.dumps 产出并被 json.load 回读 |
| schema_pass | ☑ PASS | kf_result.v1=True, asset_manifest.v1.wp-14214-01=True |
| source_locator_resolvable | ☑ PASS | 23 条 locator 全部 str.find 命中且次数==1；violations=0 |
| source_hash_matches | ☑ PASS | sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9 == 契约 sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9 |
| no_duplicate_ids | ☑ PASS | asset_id 唯一：24/24 |
| all_claims_have_evidence_or_explicit_unresolved_status | ☑ PASS | claims=[] （契约允许空数组，无强制造 claim） |
| [附加] evidence_quotes_verbatim | ☑ PASS | 7 条一致性登记引文全部可在 source_field 内逐字定位；violations=0 |

未完成/未验证的部分（如实写）：被引用工件的字节级存在性与哈希**未核**（无端点可取）；
成稿门阻断计数 22/23 的冲突**未裁决**；O1 的 48 篇差额**未归因**。这三项都超出本工序
（资产登记）的边界，已在 `asset_manifest.json` 的 `limitations` 与 `integrity_observations` 中留痕。

## ⑦ 结果 JSON（本报告唯一 json 代码块）

```json
{
  "package_id": "wp-14214-01",
  "task_type": "01-asset-registration",
  "report_id": "14214",
  "provenance": {
    "source_hash": "sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9",
    "source_field": "markdown",
    "producer": "agent/m15784",
    "emitted_at": "2026-11-12T02:38:15+00:00",
    "notes": "sha256 由本进程对 GET /api/v1/tensor/reports/14214 的 markdown 字段独立重算；与契约声明逐字节一致，chars=6258"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-14214-01",
      "task_type": "01-asset-registration",
      "report_id": "14214",
      "source": {
        "uri": "tensor://reports/14214",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9",
        "chars": 6258,
        "bytes_utf8": 8770,
        "title": "W23 论文线：430 篇增量扫描 + 45 课题双轨重标 + research_plan 销项推进 63/73 + 成稿门四门→九门（放行2/阻断22）+ 10 单派发",
        "scenario_key": "paper-line-w23",
        "mission_id": 15086,
        "status": "published",
        "created_at": "2026-11-11T18:28:58.033597+00:00",
        "created_by": 1,
        "platform_figures": [
          {
            "name": "w23_window_composition.png",
            "caption": "图1 W23 窗口 430 篇报告的判词构成与判据行（digest.json 直读，w23_figures.py 生成）"
          },
          {
            "name": "w23_track_split.png",
            "caption": "图2 45 课题双轨分布与外部锚门分级（tracks.json）"
          },
          {
            "name": "w23_plan_progress.png",
            "caption": "图3 research_plan 逐课题销项/承接/未销项（63/73 销项，33/35 封口）"
          },
          {
            "name": "w23_draft_gate.png",
            "caption": "图4 成稿门逐门热力图：九门全真才放行，2 放行/22 阻断"
          },
          {
            "name": "w23_artifact_presence.png",
            "caption": "图5 计划工件在位/缺失（48 在位 / 28 缺失，口径=main 检出）"
          }
        ],
        "platform_tags": [
          "paper-line",
          "w23",
          "dual-track",
          "research-plan",
          "draft-gate",
          "evidence-quality"
        ],
        "title_matches_contract": true,
        "scenario_key_matches_contract": true,
        "hash_matches_contract": true,
        "chars_matches_contract": true
      },
      "counts": {
        "assets": 24,
        "by_class": {
          "report_markdown": 1,
          "figure_png_reference": 5,
          "code_glob": 1,
          "code_file": 9,
          "test_file": 1,
          "data_dir": 1,
          "research_plan_set": 1,
          "registry": 1,
          "inline_markdown_table": 4
        },
        "by_resolution": {
          "resolved_in_source": 5,
          "referenced_unresolved": 19
        },
        "resolved_in_source": 5,
        "referenced_unresolved": 19,
        "declared_absent": 0,
        "inline_tables_registered": 4,
        "inline_fenced_blocks": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "report_markdown",
          "label": "报告 markdown 原文（source_field=markdown）",
          "in_report_section": "(整篇)",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 6258,
            "start_line": 1,
            "end_line": 104,
            "quote": "# W23 论文生产线研究总结：增量证据、双轨重标、research_plan 销项推进与成稿门加固",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256(utf-8 bytes) == contract.source_hash",
            "result": "resolved"
          },
          "content_retrievable": true,
          "note": "整篇 markdown 即源资产本体；locator.quote 为第 1 行（全文起点），非抽取"
        },
        {
          "asset_id": "A02",
          "asset_class": "figure_png_reference",
          "label": "papers/figures/w23_window_composition.png",
          "in_report_section": "④",
          "locator": {
            "method": "char_span",
            "start_char": 3963,
            "end_char": 4035,
            "start_line": 73,
            "end_line": 73,
            "quote": "`papers/figures/w23_window_composition.png`（sha256_16 `00a0936204e0b70d`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown 逐字子串定位（str.find，命中次数==1）",
            "result": "resolved"
          },
          "content_retrievable": false,
          "note": "正文 ④ 逐字路径 + 报告声明的前 16 位 sha256；png 字节不在报告记录内 | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供（见 artifact_endpoint_probe），故 resolution=referenced_unresolved",
          "declared_sha256_16": "00a0936204e0b70d",
          "record_figure": {
            "name": "w23_window_composition.png",
            "caption": "图1 W23 窗口 430 篇报告的判词构成与判据行（digest.json 直读，w23_figures.py 生成）"
          },
          "record_figure_bound": true
        },
        {
          "asset_id": "A03",
          "asset_class": "figure_png_reference",
          "label": "papers/figures/w23_track_split.png",
          "in_report_section": "④",
          "locator": {
            "method": "char_span",
            "start_char": 4087,
            "end_char": 4152,
            "start_line": 74,
            "end_line": 74,
            "quote": "`papers/figures/w23_track_split.png`（sha256_16 `d889e66d3739a24e`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown 逐字子串定位（str.find，命中次数==1）",
            "result": "resolved"
          },
          "content_retrievable": false,
          "note": "正文 ④ 逐字路径 + 声明 sha256_16；png 字节不在报告记录内 | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供（见 artifact_endpoint_probe），故 resolution=referenced_unresolved",
          "declared_sha256_16": "d889e66d3739a24e",
          "record_figure": {
            "name": "w23_track_split.png",
            "caption": "图2 45 课题双轨分布与外部锚门分级（tracks.json）"
          },
          "record_figure_bound": true
        },
        {
          "asset_id": "A04",
          "asset_class": "figure_png_reference",
          "label": "papers/figures/w23_plan_progress.png",
          "in_report_section": "④",
          "locator": {
            "method": "char_span",
            "start_char": 4204,
            "end_char": 4271,
            "start_line": 75,
            "end_line": 75,
            "quote": "`papers/figures/w23_plan_progress.png`（sha256_16 `371b8fc472428b13`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown 逐字子串定位（str.find，命中次数==1）",
            "result": "resolved"
          },
          "content_retrievable": false,
          "note": "正文 ④ 逐字路径 + 声明 sha256_16；png 字节不在报告记录内 | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供（见 artifact_endpoint_probe），故 resolution=referenced_unresolved",
          "declared_sha256_16": "371b8fc472428b13",
          "record_figure": {
            "name": "w23_plan_progress.png",
            "caption": "图3 research_plan 逐课题销项/承接/未销项（63/73 销项，33/35 封口）"
          },
          "record_figure_bound": true
        },
        {
          "asset_id": "A05",
          "asset_class": "figure_png_reference",
          "label": "papers/figures/w23_draft_gate.png",
          "in_report_section": "④",
          "locator": {
            "method": "char_span",
            "start_char": 4337,
            "end_char": 4401,
            "start_line": 76,
            "end_line": 76,
            "quote": "`papers/figures/w23_draft_gate.png`（sha256_16 `3a48cfafc642d093`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown 逐字子串定位（str.find，命中次数==1）",
            "result": "resolved"
          },
          "content_retrievable": false,
          "note": "正文 ④ 逐字路径 + 声明 sha256_16；png 字节不在报告记录内 | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供（见 artifact_endpoint_probe），故 resolution=referenced_unresolved",
          "declared_sha256_16": "3a48cfafc642d093",
          "record_figure": {
            "name": "w23_draft_gate.png",
            "caption": "图4 成稿门逐门热力图：九门全真才放行，2 放行/22 阻断"
          },
          "record_figure_bound": true
        },
        {
          "asset_id": "A06",
          "asset_class": "figure_png_reference",
          "label": "papers/figures/w23_artifact_presence.png",
          "in_report_section": "④",
          "locator": {
            "method": "char_span",
            "start_char": 4457,
            "end_char": 4528,
            "start_line": 77,
            "end_line": 77,
            "quote": "`papers/figures/w23_artifact_presence.png`（sha256_16 `4a1693ff2284f6e6`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown 逐字子串定位（str.find，命中次数==1）",
            "result": "resolved"
          },
          "content_retrievable": false,
          "note": "正文 ④ 逐字路径 + 声明 sha256_16；png 字节不在报告记录内 | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供（见 artifact_endpoint_probe），故 resolution=referenced_unresolved",
          "declared_sha256_16": "4a1693ff2284f6e6",
          "record_figure": {
            "name": "w23_artifact_presence.png",
            "caption": "图5 计划工件在位/缺失（48 在位 / 28 缺失，口径=main 检出）"
          },
          "record_figure_bound": true
        },
        {
          "asset_id": "A07",
          "asset_class": "code_glob",
          "label": "papers/tools/w23_*.py 面板（花括号聚合引用）",
          "in_report_section": "附",
          "locator": {
            "method": "char_span",
            "start_char": 5774,
            "end_char": 5883,
            "start_line": 101,
            "end_line": 101,
            "quote": "`papers/tools/w23_{extract,anchors,plan,tracks,specs,payloads,dispatch,draftgate,planmd,figures,registry}.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown 逐字子串定位（str.find，命中次数==1）",
            "result": "resolved"
          },
          "content_retrievable": false,
          "note": "brace-glob 逐字引文；expansion 由花括号内容机械展开（不新增名字） | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供（见 artifact_endpoint_probe），故 resolution=referenced_unresolved",
          "expansion": [
            "papers/tools/w23_extract.py",
            "papers/tools/w23_anchors.py",
            "papers/tools/w23_plan.py",
            "papers/tools/w23_tracks.py",
            "papers/tools/w23_specs.py",
            "papers/tools/w23_payloads.py",
            "papers/tools/w23_dispatch.py",
            "papers/tools/w23_draftgate.py",
            "papers/tools/w23_planmd.py",
            "papers/tools/w23_figures.py",
            "papers/tools/w23_registry.py"
          ],
          "expansion_count": 11
        },
        {
          "asset_id": "A08",
          "asset_class": "code_file",
          "label": "w23_extract.py",
          "in_report_section": "②",
          "locator": {
            "method": "char_span",
            "start_char": 547,
            "end_char": 573,
            "start_line": 19,
            "end_line": 19,
            "quote": "**增量扫描**（`w23_extract.py`）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown 逐字子串定位（str.find，命中次数==1）",
            "result": "resolved"
          },
          "content_retrievable": false,
          "note": "正文 ② 逐字点名；源码不在报告记录内 | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供（见 artifact_endpoint_probe），故 resolution=referenced_unresolved"
        },
        {
          "asset_id": "A09",
          "asset_class": "code_file",
          "label": "w23_anchors.py",
          "in_report_section": "②",
          "locator": {
            "method": "char_span",
            "start_char": 675,
            "end_char": 702,
            "start_line": 20,
            "end_line": 20,
            "quote": "**锚目录重建**（`w23_anchors.py`）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown 逐字子串定位（str.find，命中次数==1）",
            "result": "resolved"
          },
          "content_retrievable": false,
          "note": "正文 ② 逐字点名；源码不在报告记录内 | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供（见 artifact_endpoint_probe），故 resolution=referenced_unresolved"
        },
        {
          "asset_id": "A10",
          "asset_class": "code_file",
          "label": "w23_tracks.py",
          "in_report_section": "②",
          "locator": {
            "method": "char_span",
            "start_char": 754,
            "end_char": 779,
            "start_line": 21,
            "end_line": 21,
            "quote": "**双轨重标**（`w23_tracks.py`）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown 逐字子串定位（str.find，命中次数==1）",
            "result": "resolved"
          },
          "content_retrievable": false,
          "note": "正文 ② 逐字点名；源码不在报告记录内 | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供（见 artifact_endpoint_probe），故 resolution=referenced_unresolved"
        },
        {
          "asset_id": "A11",
          "asset_class": "code_file",
          "label": "w23_plan.py",
          "in_report_section": "②",
          "locator": {
            "method": "char_span",
            "start_char": 880,
            "end_char": 903,
            "start_line": 22,
            "end_line": 22,
            "quote": "**销项收割**（`w23_plan.py`）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown 逐字子串定位（str.find，命中次数==1）",
            "result": "resolved"
          },
          "content_retrievable": false,
          "note": "正文 ② 逐字点名；源码不在报告记录内 | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供（见 artifact_endpoint_probe），故 resolution=referenced_unresolved"
        },
        {
          "asset_id": "A12",
          "asset_class": "code_file",
          "label": "w23_draftgate.py",
          "in_report_section": "②",
          "locator": {
            "method": "char_span",
            "start_char": 1018,
            "end_char": 1047,
            "start_line": 23,
            "end_line": 23,
            "quote": "**成稿门加固**（`w23_draftgate.py`）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown 逐字子串定位（str.find，命中次数==1）",
            "result": "resolved"
          },
          "content_retrievable": false,
          "note": "正文 ② 逐字点名；源码不在报告记录内 | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供（见 artifact_endpoint_probe），故 resolution=referenced_unresolved"
        },
        {
          "asset_id": "A13",
          "asset_class": "code_file",
          "label": "w23_payloads.py",
          "in_report_section": "②",
          "locator": {
            "method": "char_span",
            "start_char": 1081,
            "end_char": 1105,
            "start_line": 24,
            "end_line": 24,
            "quote": "**派单**（`w23_payloads.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown 逐字子串定位（str.find，命中次数==1）",
            "result": "resolved"
          },
          "content_retrievable": false,
          "note": "正文 ② 逐字点名；源码不在报告记录内 | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供（见 artifact_endpoint_probe），故 resolution=referenced_unresolved"
        },
        {
          "asset_id": "A14",
          "asset_class": "code_file",
          "label": "w23_dispatch.py",
          "in_report_section": "②",
          "locator": {
            "method": "char_span",
            "start_char": 1108,
            "end_char": 1126,
            "start_line": 24,
            "end_line": 24,
            "quote": "`w23_dispatch.py`）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown 逐字子串定位（str.find，命中次数==1）",
            "result": "resolved"
          },
          "content_retrievable": false,
          "note": "正文 ② 逐字点名；源码不在报告记录内 | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供（见 artifact_endpoint_probe），故 resolution=referenced_unresolved"
        },
        {
          "asset_id": "A15",
          "asset_class": "code_file",
          "label": "w23_planmd.py",
          "in_report_section": "⑤",
          "locator": {
            "method": "char_span",
            "start_char": 5024,
            "end_char": 5045,
            "start_line": 84,
            "end_line": 84,
            "quote": "`w23_planmd.py` 首版覆盖了",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown 逐字子串定位（str.find，命中次数==1）",
            "result": "resolved"
          },
          "content_retrievable": false,
          "note": "正文 ⑤ 逐字点名；源码不在报告记录内 | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供（见 artifact_endpoint_probe），故 resolution=referenced_unresolved"
        },
        {
          "asset_id": "A16",
          "asset_class": "code_file",
          "label": "w23_figures.py",
          "in_report_section": "④",
          "locator": {
            "method": "char_span",
            "start_char": 4039,
            "end_char": 4083,
            "start_line": 73,
            "end_line": 73,
            "quote": "`papers/tools/w23_figures.py`，输入 digest.json",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown 逐字子串定位（str.find，命中次数==1）",
            "result": "resolved"
          },
          "content_retrievable": false,
          "note": "正文 ④ 逐字点名（4 张图共用该脚本，此处取含 digest.json 的第 1 条图注以保唯一）；源码不在报告记录内 | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供（见 artifact_endpoint_probe），故 resolution=referenced_unresolved"
        },
        {
          "asset_id": "A17",
          "asset_class": "test_file",
          "label": "test_w23_artifacts.py",
          "in_report_section": "附",
          "locator": {
            "method": "char_span",
            "start_char": 5884,
            "end_char": 5907,
            "start_line": 101,
            "end_line": 101,
            "quote": "`test_w23_artifacts.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown 逐字子串定位（str.find，命中次数==1）",
            "result": "resolved"
          },
          "content_retrievable": false,
          "note": "正文 附节逐字点名；测试源码不在报告记录内 | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供（见 artifact_endpoint_probe），故 resolution=referenced_unresolved"
        },
        {
          "asset_id": "A18",
          "asset_class": "data_dir",
          "label": "papers/data/w23-2026-11-11/",
          "in_report_section": "附",
          "locator": {
            "method": "char_span",
            "start_char": 5913,
            "end_char": 5942,
            "start_line": 102,
            "end_line": 102,
            "quote": "`papers/data/w23-2026-11-11/`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown 逐字子串定位（str.find，命中次数==1）",
            "result": "resolved"
          },
          "content_retrievable": false,
          "note": "数据目录引用；目录内容不在报告记录内 | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供（见 artifact_endpoint_probe），故 resolution=referenced_unresolved"
        },
        {
          "asset_id": "A19",
          "asset_class": "research_plan_set",
          "label": "W23 新立 5 个 research_plan.md",
          "in_report_section": "附",
          "locator": {
            "method": "char_span",
            "start_char": 5948,
            "end_char": 6004,
            "start_line": 102,
            "end_line": 102,
            "quote": "`papers/composite-laminate-verification/research_plan.md",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown 逐字子串定位（str.find，命中次数==1）",
            "result": "resolved"
          },
          "content_retrievable": false,
          "note": "同一 code span 内 5 条路径；expansion 由逗号切分机械得到 | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供（见 artifact_endpoint_probe），故 resolution=referenced_unresolved",
          "expansion": [
            "）：任务销项 = 至少产出 1 篇报告（判据达标或 honest FAIL 均算）；承接 = 重试单 goal 逐字点名前身；工件在位性按 research_plan.md 表格**列名定位**后在仓内 main 检出核验。\n5. **成稿门加固**（"
          ],
          "expansion_count": 1
        },
        {
          "asset_id": "A20",
          "asset_class": "registry",
          "label": "papers/registry.md",
          "in_report_section": "附",
          "locator": {
            "method": "char_span",
            "start_char": 6209,
            "end_char": 6238,
            "start_line": 103,
            "end_line": 103,
            "quote": "registry：`papers/registry.md`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown 逐字子串定位（str.find，命中次数==1）",
            "result": "resolved"
          },
          "content_retrievable": false,
          "note": "append-only registry 引用；文件内容不在报告记录内 | 路径/引文在 markdown 内可定位，但被引用文件的字节不随报告记录提供（见 artifact_endpoint_probe），故 resolution=referenced_unresolved"
        },
        {
          "asset_id": "A21",
          "asset_class": "inline_markdown_table",
          "label": "pipe 表：指标 | 数值",
          "in_report_section": "## ① 案例介绍（研究域与证据面）",
          "locator": {
            "method": "char_span",
            "start_char": 395,
            "end_char": 406,
            "start_line": 10,
            "end_line": 15,
            "quote": "| 指标 | 数值 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "表头行逐字定位 + 分隔行正则校验",
            "result": "resolved"
          },
          "content_retrievable": true,
          "structure": {
            "data_rows": 4,
            "header_cells": 2,
            "header_names": [
              "指标",
              "数值"
            ],
            "table_line_span": 6
          },
          "note": "只登记结构（行数/列数/表头），不抽取任何数值（契约 objective 不做抽取）"
        },
        {
          "asset_id": "A22",
          "asset_class": "inline_markdown_table",
          "label": "pipe 表：指标 | W22 | W23 | 变化",
          "in_report_section": "## ③ 计算结果（数字表，程序化注入）",
          "locator": {
            "method": "char_span",
            "start_char": 1215,
            "end_char": 1238,
            "start_line": 30,
            "end_line": 35,
            "quote": "| 指标 | W22 | W23 | 变化 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "表头行逐字定位 + 分隔行正则校验",
            "result": "resolved"
          },
          "content_retrievable": true,
          "structure": {
            "data_rows": 4,
            "header_cells": 4,
            "header_names": [
              "指标",
              "W22",
              "W23",
              "变化"
            ],
            "table_line_span": 6
          },
          "note": "只登记结构（行数/列数/表头），不抽取任何数值（契约 objective 不做抽取）"
        },
        {
          "asset_id": "A23",
          "asset_class": "inline_markdown_table",
          "label": "pipe 表：task_key | mission | 状态 | 模型 | repo",
          "in_report_section": "## ③ 计算结果（数字表，程序化注入）",
          "locator": {
            "method": "char_span",
            "start_char": 1734,
            "end_char": 1773,
            "start_line": 46,
            "end_line": 67,
            "quote": "| task_key | mission | 状态 | 模型 | repo |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "表头行逐字定位 + 分隔行正则校验",
            "result": "resolved"
          },
          "content_retrievable": true,
          "structure": {
            "data_rows": 20,
            "header_cells": 5,
            "header_names": [
              "task_key",
              "mission",
              "状态",
              "模型",
              "repo"
            ],
            "table_line_span": 22
          },
          "note": "只登记结构（行数/列数/表头），不抽取任何数值（契约 objective 不做抽取）"
        },
        {
          "asset_id": "A24",
          "asset_class": "inline_markdown_table",
          "label": "pipe 表：关键量 | 基准 | 结果 | 是否 <3%",
          "in_report_section": "## ⑥ 误差判定（关键量 vs 基准）",
          "locator": {
            "method": "char_span",
            "start_char": 5233,
            "end_char": 5259,
            "start_line": 89,
            "end_line": 95,
            "quote": "| 关键量 | 基准 | 结果 | 是否 <3% |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "表头行逐字定位 + 分隔行正则校验",
            "result": "resolved"
          },
          "content_retrievable": true,
          "structure": {
            "data_rows": 5,
            "header_cells": 4,
            "header_names": [
              "关键量",
              "基准",
              "结果",
              "是否 <3%"
            ],
            "table_line_span": 7
          },
          "note": "只登记结构（行数/列数/表头），不抽取任何数值（契约 objective 不做抽取）"
        }
      ],
      "claims": [],
      "integrity_observations": [
        {
          "obs_id": "O1",
          "kind": "arithmetic",
          "question": "窗口报告计数是否等于判词三态之和",
          "computed": {
            "PASS": 184,
            "FAIL": 138,
            "WITHHELD": 60,
            "sum": 382,
            "window_reports": 430,
            "difference": 48
          },
          "result": "unresolved_difference",
          "status": "unresolved",
          "unresolved_reason": "报告正文未说明差额归属（未判/NULL 判词未见声明），本工序不推断",
          "evidence": [
            {
              "quote": "| 指标 | 数值 |\n|---|---|\n| 窗口报告 | 430 |\n| 判词 PASS / FAIL / WITHHELD | 184 / 138 / 60 |\n| 含 `<3%` 类判据行报告 | 260 |\n| 平台累计发布 | 9401 |",
              "source_field": "markdown",
              "note": "指标表 行10-15；数字由脚本解析，未手抄"
            }
          ]
        },
        {
          "obs_id": "O2",
          "kind": "cross_field",
          "question": "成稿门阻断计数：正文 vs 记录 title（/本包契约 title）",
          "computed": {
            "body_blocked": 23,
            "record_title_blocked": 22,
            "difference": 1
          },
          "result": "conflict_unresolved",
          "status": "unresolved",
          "unresolved_reason": "正文写 23，记录 title/summary 与本包契约 title 写 22；报告内无第三方口径可裁，本工序只登记不裁决（不得标 verified）",
          "evidence": [
            {
              "quote": "- 阻断 **23**；主要阻断门计数：G5e_anchor_task_not_fail=11、G5c_artifact_ratio_ge_0.5=8、G5a_pass_report_ge1=11、G5d_fail_not_dominant=8、G5b_pass_rows_ge3=8、G4_no_draft=9、G2_plan_closed=2",
              "source_field": "markdown",
              "note": "正文 ③ 成稿门判决段"
            },
            {
              "quote": "W23 论文线：430 篇增量扫描 + 45 课题双轨重标 + research_plan 销项推进 63/73 + 成稿门四门→九门（放行2/阻断22）+ 10 单派发",
              "source_field": "record",
              "note": "记录 title（与本包契约 title 逐字相同）"
            }
          ]
        },
        {
          "obs_id": "O3",
          "kind": "cross_field",
          "question": "「N 单派发」与派单回执表行数/唯一 task_key/mission 区间是否自洽",
          "computed": {
            "table_rows": 20,
            "distinct_task_keys": 10,
            "rows_with_numeric_mission": 10,
            "mission_range": [
              15092,
              15101
            ],
            "missions_contiguous": true,
            "title_stated_units": 10
          },
          "result": "consistent",
          "status": "resolved",
          "unresolved_reason": null,
          "evidence": [
            {
              "quote": "| task_key | mission | 状态 | 模型 | repo |\n|---|---|---|---|---|\n| `paper-exp-ice-coupled-6dof-3` | None | validated-dry | deepseek-v4-flash | TensorFEM |\n| `paper-exp-ice-nav-operational-chain-4` | None | validated-dry | deepseek-v4-flash | ship-performance-platform |\n| `paper-exp-ship-hull-girder-structure-2` | None | validated-dry | deepseek-v4-flash | TensorFEM |\n| `paper-exp-undex-shock-chain-2` | None | validated-dry | deepseek-v4-flash | TensorFEM |\n| `paper-exp-green-shipping-iso19030-2` | None | validated-dry | deepseek-v4-flash | ship-performance-platform |\n| `paper-exp-composite-laminate-verification-2` | None | validated-dry | deepseek-v4-flash | TensorFEM |\n| `paper-exp-resistance-ittc-traceable-chain-2` | None | validated-dry | deepseek-v4-flash | ship-performance-platform |\n| `paper-exp-resistance-ittc-traceable-chain-3` | None | validated-dry | deepseek-v4-flash | ship-performance-platform |\n| `paper-draft-damaged-stability-flooding-td` | None | validated-dry | qwen3.6-plus | TensorPapers |\n| `paper-draft-wind-load-blendermann-weather-criterion` | None | validated-dry | deepseek-v4-flash | TensorPapers |\n| `paper-exp-ice-coupled-6dof-3` | 15092 | claimed | deepseek-v4-flash | TensorFEM |\n| `paper-exp-ice-nav-operational-chain-4` | 15093 | queued | deepseek-v4-flash | ship-performance-platform |\n| `paper-exp-ship-hull-girder-structure-2` | 15094 | queued | deepseek-v4-flash | TensorFEM |\n| `paper-exp-undex-shock-chain-2` | 15095 | queued | deepseek-v4-flash | TensorFEM |\n| `paper-exp-green-shipping-iso19030-2` | 15096 | queued | deepseek-v4-flash | ship-performance-platform |\n| `paper-exp-composite-laminate-verification-2` | 15097 | queued | deepseek-v4-flash | TensorFEM |\n| `paper-exp-resistance-ittc-traceable-chain-2` | 15098 | queued | deepseek-v4-flash | ship-performance-platform |\n| `paper-exp-resistance-ittc-traceable-chain-3` | 15099 | queued | deepseek-v4-flash | ship-performance-platform |\n| `paper-draft-damaged-stability-flooding-td` | 15100 | queued | qwen3.6-plus | TensorPapers |\n| `paper-draft-wind-load-blendermann-weather-criterion` | 15101 | queued | deepseek-v4-flash | TensorPapers |",
              "source_field": "markdown",
              "note": "派单回执 行46-67：20 行 = 同一批 10 个 task_key 的 dry-run 与落库两次快照"
            }
          ]
        },
        {
          "obs_id": "O4",
          "kind": "arithmetic",
          "question": "计划表 W22→W23→变化 三列是否逐行自洽",
          "computed": {
            "计划内 exp 任务": {
              "computed_delta": 14,
              "stated": "+14"
            },
            "已销项": {
              "computed_delta": 12,
              "stated": "+12"
            },
            "封口计划": {
              "computed_delta": 9,
              "stated": "+9"
            }
          },
          "result": "consistent",
          "status": "resolved",
          "unresolved_reason": null,
          "evidence": [
            {
              "quote": "| 指标 | W22 | W23 | 变化 |\n|---|---|---|---|\n| 计划内 exp 任务 | 59 | 73 | +14 |\n| 已销项 | 51 | 63 | +12 |\n| 封口计划 | 24 | 33 | +9 |\n| 承接 / 未销项 | — | 7 / 3 | — |",
              "source_field": "markdown",
              "note": "计划表 行30-35"
            }
          ]
        },
        {
          "obs_id": "O5",
          "kind": "source_shape",
          "question": "报告段结构是否包含 ①–⑥ 六段（行号由脚本扫描得到）",
          "computed": {
            "heading_count": 8,
            "headings": [
              [
                1,
                "# W23 论文生产线研究总结：增量证据、双轨重标、research_plan 销项推进与成稿门加固"
              ],
              [
                6,
                "## ① 案例介绍（研究域与证据面）"
              ],
              [
                17,
                "## ② 怎么做的（方法 / 工具链）"
              ],
              [
                26,
                "## ③ 计算结果（数字表，程序化注入）"
              ],
              [
                71,
                "## ④ 结果图"
              ],
              [
                79,
                "## ⑤ 注意点（坑与局限）"
              ],
              [
                87,
                "## ⑥ 误差判定（关键量 vs 基准）"
              ],
              [
                99,
                "## 附：工具与工件"
              ]
            ],
            "section_line": {
              "①": 6,
              "②": 17,
              "③": 26,
              "④": 71,
              "⑤": 79,
              "⑥": 87
            },
            "all_six_present": true
          },
          "result": "complete_sections",
          "status": "resolved",
          "unresolved_reason": null,
          "evidence": [
            {
              "quote": "## ① 案例介绍（研究域与证据面）",
              "source_field": "markdown",
              "note": "① 段标题行逐字；全部标题及行号见 computed.headings"
            }
          ]
        },
        {
          "obs_id": "O6",
          "kind": "cross_field",
          "question": "⑥ 误差判定表的「是否 <3%」列自述到位情况",
          "computed": {
            "rows": 5,
            "column": "是否 <3%",
            "value_counts": {
              "是": 4,
              "不适用": 1
            },
            "external_quantitative_error_rows": 0
          },
          "result": "author_declared_no_external_baseline",
          "status": "resolved",
          "unresolved_reason": null,
          "evidence": [
            {
              "quote": "| 关键量 | 基准 | 结果 | 是否 <3% |\n|---|---|---|---|\n| 窗口报告计数 | psql `count(*)` 直读 | 与 inventory/digest 双源一致（机检 ①②） | 是（0 误差，恒等核） |\n| 任务销项计数 | DB mission→report 关联 | 账本 partition 恒等（closed+superseded+open=tasks） | 是（0 误差） |\n| 数字 token 归属 | 锚目录 + specs | 284/284 归类，锚越界 0 | 是（0 误归） |\n| 工件在位率 | git 检出存在性 | 48 在位 / 28 缺失（口径=main 检出，非真值下界） | 不适用（无外部基准，如实声明） |\n| 图件完整性 | figures.json 登记 sha256 | 5/5 逐文件复算一致 | 是（0 误差） |",
              "source_field": "markdown",
              "note": "行89-95；本工序只登记作者自述，不复判精度、不代填结论"
            }
          ]
        }
      ],
      "artifact_endpoint_probe": {
        "base": "http://127.0.0.1:8010/api/v1",
        "probes": [
          {
            "path": "/openapi.json",
            "status": "HTTP 404"
          },
          {
            "path": "/tensor/reports/14214/artifacts",
            "status": "HTTP 404"
          },
          {
            "path": "/tensor/reports/14214/figures",
            "status": "HTTP 404"
          },
          {
            "path": "/tensor/artifacts?report_id=14214",
            "status": "HTTP 404"
          }
        ],
        "conclusion": "无端点提供被引用工件（figures/脚本/数据）的字节；故这些资产只能登记到「路径+声明哈希」层级，resolution=referenced_unresolved"
      },
      "locator_check_summary": {
        "locators": 23,
        "unresolved": 0,
        "tables_detected": 4
      },
      "integrity": {
        "quote_uniqueness": {
          "checked": 23,
          "violations": 0,
          "all_unique": true,
          "note": "每条引文在 markdown 中命中次数必须恰为 1；violations 必须为 0"
        },
        "hash_recomputed_locally": "sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9",
        "hash_matches_contract": true,
        "chars_contract": 6258,
        "chars_computed": 6258,
        "chars_matches_contract": true,
        "source_copy_sha256": "sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9",
        "claims_emitted": 0,
        "nothing_marked_verified": true,
        "observation_quotes_verbatim": {
          "checked": 7,
          "violations": 0
        },
        "kf_result_schema": {
          "path": "schemas/kf_result.v1.schema.json",
          "valid": true,
          "errors": []
        },
        "asset_manifest_schema": {
          "path": "schemas/asset_manifest.v1.wp-14214-01.schema.json",
          "valid": true,
          "errors": []
        }
      },
      "limitations": [
        "本工序只登记资产，不抽取内容、不分类、不产生 claim（契约 objective.classify_report_type=false）",
        "被引用文件（png/脚本/数据/plan/registry）的字节不可经任何端点取得，故 resolution=referenced_unresolved：只核了正文里的路径字符串，未核文件存在性与声明哈希",
        "integrity_observations 是算术/跨字段一致性登记，状态只有 consistent / unresolved，不含任何 verified 结论"
      ]
    }
  },
  "claims": []
}
```
