# KF-RESULT wp-7554-01

**工作包** `wp-7554-01` ｜ **工序** `01-asset-registration` ｜ **report_id** `7554`
**源** `tensor://reports/7554` `markdown` ｜ **source_hash** `sha256:d64a8ba8abe00714e3d7f8067ebfcbc30509ef0e858e1c697231b62d1eda7921`（本地重算，与契约一致）
**标题（源报告）** plan 143（ABM）终态后的自主提案：6 条从未做过的任务书（判据真空清偿 + 两条空白学科面）
**scenario_key / mission_id（源报告）** `abm` / `6357`
**产出** `docs/kf/wp-7554-01/`（asset_manifest.json / kf_result.json / verification.json / source_snapshot.md / figures）

---

## ① 本工序做了什么

只做一件事：**登记 report_id=7554 的源资产**。具体为

1. 从平台取回该报告 `markdown` 字段（`GET /tensor/reports/7554`），**重新计算**其 UTF-8 字节
   的 sha256 与字符数，并与工作包契约给的 `source_hash` / `chars` 对账：
   `5015` 字符 / `9203` 字节 / `sha256:d64a8ba8abe00714e3d7f8067ebfcbc30509ef0e858e1c697231b62d1eda7921`，与契约值一致（hash_matches_contract=True）。
2. 在 markdown 内**按字面解析**出可登记的对象（平台图、产物路径、代码脚本、数据表、上游报告引用、
   报告自述不存在的对象），逐条给出**字符级定位**，并标注解析状态。
3. **不做抽取**：`claims` 为 `[]`（工序契约 `objective.classify_report_type=false`，01 工序的
   零 claim 是合法完整结果，不为填指标造知识）。
4. **不判定 verified**：本工序只产出 worker 侧自检（`verification.json`），
   `verification` 由平台门计算，任何字段都没有被标成 verified。

登记结果：**12 个资产 = 1 个 resolved_in_source（报告自身 markdown）+ 10 个
referenced_unresolved（字节不在本包范围内：平台只存图元数据、跨报告、外部表、仓内不存在的产物路径）
+ 1 个 declared_absent（报告自行声明不存在）。**

- 按状态：`{"resolved_in_source": 1, "referenced_unresolved": 10, "declared_absent": 1}`
- 按类：`{"report_markdown": 1, "artifact_file": 2, "code_artifact": 1, "embedded_figure": 2, "field_contour": 1, "data_source": 2, "upstream_report": 3}`

## ② 怎么做的（步骤 / 工具 / 关键设置）

工具：`scripts/kf/register_source_assets.py`（本单新增，**通用**：report_id / source_hash /
discovery plan 全部来自参数，脚本内无任何 report 常量），配置 `docs/kf/wp-7554-01/discovery_plan.json`；
独立复核：`tests/test_kf_wp_7554_01.py`（**不 import 生成器**，自己重算 hash/切片/行号/schema，
防止"生成器的 bug 替自己作证"）。

关键设计（防止"手抄"与"幻觉定位"的结构性做法）：

1. **引文=程序切片，不是重敲**。discovery plan 里每条资产只给一个 `anchor` 字符串，
   脚本要求该 anchor 在 markdown 中**恰好出现 1 次**（否则直接 abort）；
   写入 manifest 的 `quote` 是 `markdown[start:end]` 的**切片**，因此"quote 是源子串"
   由构造保证，`start_line/end_line` 由换行计数导出。
2. **定位可回读**：自检把 `quote` 再与 `markdown[start_char:end_char]` 比对（round-trip），
   而不是只检查"串在不在"。
3. **状态词汇表显式**：`resolution_vocabulary` 写清 resolved/unresolved/absent 三种判据；
   凡"报告提了但字节不在本包范围内"一律 `referenced_unresolved` 并写明未解析的原因，
   **不猜、不补、不把间接证据当直接证据**。
4. **schema 双校验**：`kf_result.json` 对 `schemas/kf_result.v1.schema.json`（仓库内 canonical 信封）
   校验；`asset_manifest.json` 对**由 `schemas/asset_manifest.v1.schema.json` 在 build 时
   重绑 const（package_id/report_id/source uri）派生**的 `asset_manifest.schema.pkg.json` 校验，
   派生文件落盘可复查，canonical 形状不变。
5. **源字节留底**：`source_snapshot.md`（sha256 `d64a8ba8abe00714e3d7f8067ebfcbc30509ef0e858e1c697231b62d1eda7921`）使全部定位在离线状态下可复算。

复跑（一键）：

```text
export TENSOR_API_BASE=http://127.0.0.1:8010/api/v1
python3 scripts/kf/register_source_assets.py \
  --package-id wp-7554-01 --report-id 7554 \
  --expected-hash d64a8ba8abe00714e3d7f8067ebfcbc30509ef0e858e1c697231b62d1eda7921 --expected-chars 5015 \
  --spec docs/kf/wp-7554-01/discovery_plan.json \
  --out-dir docs/kf/wp-7554-01 build verify
```

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-7554-01/asset_manifest.json` | 主产物。12 资产 / 1 resolved / 10 unresolved / 1 absent；`claims: []`；每条资产含 method+char/line span+逐字 quote+uniqueness+resolution+resolution_check，`integrity.hash_matches_contract=True`；sha256 `6d9c92014780f553cff40605fbc41798182a981cbff1618cbfe928104556fdf1` |
| `docs/kf/wp-7554-01/kf_result.json` | 结果信封（`package_id/task_type/report_id/provenance/outputs/claims`），`outputs["asset_manifest.json"]` 内嵌 manifest 全文；`provenance.source_hash=sha256:d64a8ba8abe00714e3d7f8067ebfcbc30509ef0e858e1c697231b62d1eda7921`；本文件即下文唯一的 JSON 代码块 |
| `docs/kf/wp-7554-01/verification.json` | worker 侧自检 10 项（见 ⑥）逐条 PASS/FAIL + 失败清单 + "非平台门"声明 |
| `docs/kf/wp-7554-01/source_snapshot.md` | 取回源 markdown 原字节留底（sha256 `d64a8ba8abe00714e3d7f8067ebfcbc30509ef0e858e1c697231b62d1eda7921`） |
| `docs/kf/wp-7554-01/discovery_plan.json` | 12 条资产的 anchor/状态/理由配置（可读、可重跑、可 diff） |
| `docs/kf/wp-7554-01/asset_manifest.schema.pkg.json` | build 时由 canonical schema 重绑 const 派生的包级 schema（schema_pass 的判据） |
| `docs/kf/wp-7554-01/figures/manifest_resolution.png` | 图 1：资产类 × 解析状态计数（数据源=manifest 自身，程序化注入） |
| `scripts/kf/register_source_assets.py` | 通用登记器（build+verify），report_id 参数化，无硬编码常量 |
| `tests/test_kf_wp_7554_01.py` | 独立复核 12 项 pytest（不 import 生成器）：hash/切片回读/行号/schema/单 JSON 块/无 verified 标记/`claims=[]`，含平台在线复算 hash 的用例 |
| `scripts/kf/render_kf_result_report.py` | 本报告渲染/发布器（表格、图、JSON 块全部从产物读取，零手抄） |

## ④ 证据定位表（claim/字段 → 原文引文片段）

下表每行 = manifest 中一条资产。`char span / line span` 为源 markdown 的**字符偏移与 1-based 行号**，
"原文引文"列为 `markdown[start_char:end_char]` 的程序切片，可直接回读。

| asset_id | label | resolution | class | quote unique | char span / line span | 原文引文（逐字切片） |
|---|---|---|---|---|---|---|
| A01 | Report 7554 markdown itself (contract source) | `resolved_in_source` | report_markdown | unique | 0-38 / L1-1 | `# plan 143（ABM）全节点终态后的自主提案：6 条从未做过的任务书` |
| A02 | artifacts/p143_w1/prop-6357.json (6 proposal task-sheets) | `referenced_unresolved` | artifact_file | unique | 123-167 / L4-4 | 「`artifacts/p143_w1/prop-6357.json`（6 条完整任务书）」 |
| A03 | fig_data.json (source numbers behind figures 1-2) | `referenced_unresolved` | artifact_file | unique | 177-197 / L4-4 | 「`fig_data.json`（图数据）」 |
| A04 | gen_figs.py (figure data-extraction / plotting script) | `referenced_unresolved` | code_artifact | unique | 199-221 / L4-4 | 「`gen_figs.py`（取数/绘图脚本）」 |
| A05 | fig1_frontier_coverage.png (plan-143 node states + discipline coverage heatmap) | `referenced_unresolved` | embedded_figure | unique | 3181-3216 / L77-77 | `![fig1](fig:fig1_frontier_coverage)` |
| A06 | fig2_gap_ledger.png (attainment ratio of the six indebtedness items, log axis) | `referenced_unresolved` | embedded_figure | unique | 3217-3245 / L78-78 | `![fig2](fig:fig2_gap_ledger)` |
| A07 | field-quantity contour (contradiction/pressure fields) for this report | `declared_absent` | field_contour | unique | 3582-3590 / L90-90 | `图里没有场量云图` |
| A08 | campaign_nodes (plan_id=143) node-state table, read by SQL | `referenced_unresolved` | data_source | unique | 1219-1258 / L27-27 | 「`campaign_nodes(plan_id=143)` 状态 SQL 直读」 |
| A09 | tensor_guide_tracker KPI snapshot (success_rate/lineage_coverage/kb_samples/...) | `referenced_unresolved` | data_source | unique | 1026-1058 / L22-22 | 「`tensor_guide_tracker` 最新 KPI 快照」 |
| A10 | report m6334 (P1: SC-LBM droplet entry, Laplace/added-mass criteria) | `referenced_unresolved` | upstream_report | unique | 494-503 / L13-13 | `P1（m6334）` |
| A11 | report m6335 (P2: TensorDEM bonded-particle ice fracture, UCS/ν/Weibull criteria) | `referenced_unresolved` | upstream_report | unique | 650-659 / L15-15 | `P2（m6335）` |
| A12 | report m6330 (A3: run-manifest back-filler, limitation 5) | `referenced_unresolved` | upstream_report | unique | 790-799 / L17-17 | `A3（m6330）` |

说明：`quote unique = unique` 表示该引文在源 markdown 中**只出现 1 次**（自检口径），
因此定位无歧义；`declared_absent` 行的引文是报告**自述不存在**的原句，不是资产本体。

## ⑤ 注意点与局限

1. **本单不产生任何物理量**：01 工序只登记源资产，没有仿真、没有抽取、没有误差计算；
   "关键量 vs 解析/实验基准 <3%" 在本工序**不适用**，理由是被比较的量根本不存在（见 ⑥ 表末行）。
2. **10/12 条资产是 unresolved，这是实测而非遗漏**。逐个原因：
   - 平台图 2 张：报告读接口（`GET /tensor/reports/7554`）对 `figures[]` **只返回 `{name, caption}`**，
     无任何 payload 字段（`/tensor/reports/{id}/figures` 与 `/figure/0` 均 404）→ 本包拿不到图片字节，
     因此无法哈希、无法内嵌；**这不等于"平台没存字节"**（存储层未证，见 ⑤-5 的对照实验）。
     登记为 `referenced_unresolved` 是"字节不在本包可读范围"的准确表述；
   - `artifacts/p143_w1/prop-6357.json` / `fig_data.json` / `gen_figs.py`：报告点名，但**本 worktree 内
     `find` 全仓无此文件**（且 `artifacts/` 被 `.gitignore` 与推送门滤除，见 `docs/ops/filter-audit.md`）；
   - `campaign_nodes(plan_id=143)` / `tensor_guide_tracker`：上游数据库状态，属后续核验任务，本工序不查；
   - m6334 / m6335 / m6330：跨报告引用，**包边界禁止读写 report_id≠7554**，故只登记引用、不取正文。
3. **边界自律**：本单未读、未写、未覆盖任何其它 report_id；未改写上游工作包产物；
   `finish`/报告里也没有把任何结论标成 verified。
4. **定位口径的一个已知弱点**：`char_span` 绑定的是**当前这一版** markdown。若上游编辑该报告
   （平台重算 hash 会变），本清单的偏移随之失效 —— 这正是 `source_hash` 前置校验的意义：
   hash 不匹配时不得使用旧偏移，必须重跑 build。
5. **一处自己抓到并已勘误的过度断言（诚实记录）**：本包 v1（平台 report 14688，标题相同）把上述
   图资产写成"平台 `png_base64` 为空 → 无字节可哈希"，暗含了"平台未存字节"的**存储层断言**——
   读接口不暴露 payload，既不能证实也不能证伪该断言。v2 起改为"读路径只暴露 name/caption"。
   **对照实验**（顺手做了）：本包自己给平台投递了一张 65,141 字节的 PNG（`figures[].png_base64`），
   回读时仍只暴露 `{name, caption}` → 说明该读路径**普遍**不返回图字节，与"这份报告有没有画图"无关。
   因此 A05/A06 的 `referenced_unresolved` 是读路径限制所致，不是源报告缺图。此后同标题报告以编号更大者为准。
6. **A01 的 `document` 定位（自检发现并已修的一处真缺陷）**：最初把整篇资产写成
   `method=document` 且 `char span=(0, len(md))`，但 `quote` 只能取首个标题行 —— 于是
   `md[start:end] != quote`，**round-trip 不成立**（独立测试抓到）。修正为：`char span`=标题行区间
   （可回读），"覆盖整篇"这一主张改由 `covers_document=true` + `document_chars=<n>` 两个显式字段
   承载。同类缺陷还抓到一处：契约哈希比对标志曾只存在于内存、落盘为 `null`，现由 build 直接计算并
   持久化（`hash_matches_contract=true`），并由独立测试断言其在**文件里**为 true。

## ⑥ 自检：逐条对照 acceptance（honest）

| acceptance 项 | 结果 | 依据（自检明细） |
|---|---|---|
| `valid_json` | ✅ | 4 个 JSON 产物均 `json.loads` 通过（asset_manifest / kf_result / verification / schema.pkg） |
| `schema_pass` | ✅ | kf_result vs `schemas/kf_result.v1.schema.json`；manifest vs build 时派生的包级 schema（jsonschema 4.26.0） |
| `source_locator_resolvable` | ✅ | 12/12 quote 是源子串；12/12 char span 回读等于 quote（round-trip） |
| `source_hash_matches` | ✅ | 本地重算 `sha256:d64a8ba8abe00714e3d7f8067ebfcbc30509ef0e858e1c697231b62d1eda7921` == 契约值；字符数 5015 == 契约 5015 |
| `no_duplicate_ids` | ✅ | 12 个 asset_id，去重后仍 12 |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✅ | `claims=[]`：01 工序零 claim 是合法完整结果（契约 `no_forced_claim_generation`） |

自检明细（`verification.json` 原样）：

| check | result | detail |
|---|---|---|
| source_hash_matches_contract | ✅ PASS | recomputed=d64a8ba8abe00714e3d7f8067ebfcbc30509ef0e858e1c697231b62d1eda7921 contract=d64a8ba8abe00714e3d7f8067ebfcbc3050 |
| source_chars_matches_contract | ✅ PASS | actual=5015 contract=5015 |
| source_locator_resolvable | ✅ PASS | non-substring quotes: [] |
| quote_uniqueness | ✅ PASS | non-unique quotes: [] |
| locator_char_span_roundtrip | ✅ PASS | span!=quote: [] |
| no_duplicate_ids | ✅ PASS | n=12 unique=12 |
| counts_consistent | ✅ PASS | assets=12 by_resolution={'resolved_in_source': 1, 'referenced_unresolved': 10, 'declared_absent': 1} |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ PASS | claims=0 (zero claims is a legal complete result for 01) |
| kf_result_schema_pass | ✅ PASS | schemas/kf_result.v1.schema.json |
| manifest_schema_pass | ✅ PASS | derived from schemas/asset_manifest.v1.schema.json |

**误差判定（显式回答是否 <3%）**：本工序的可判定量全部是**离散/精确量**（sha256 相等、字符数相等、
quote 子串/唯一性、id 去重、schema 通过），实测偏差均为 **0**，即 0% < 3% ✅。
唯一例外是"平台图字节"这一项：它不是"误差超标"，而是**根本取不到字节**（`png_base64` 为空），
故如实登记为 `referenced_unresolved` 而不是 0 误差通过——不把"没有证据"写成"误差为 0"。
**未被本单验证的事项**（不得读作 PASS）：上游三条欠账量值（R²=0.25 / UCS 54.8% / ν 8.4%）
在源报告中的真实性、两张图的像素内容、m6334/m6335/m6330 的正文结论——这些属其它工作包或平台门的职责。

---

## 结果信封（唯一 JSON 代码块）

```json
{
  "package_id": "wp-7554-01",
  "task_type": "01-asset-registration",
  "report_id": "7554",
  "provenance": {
    "source_uri": "tensor://reports/7554",
    "source_field": "markdown",
    "source_hash": "sha256:d64a8ba8abe00714e3d7f8067ebfcbc30509ef0e858e1c697231b62d1eda7921",
    "hash_algo": "sha256",
    "hashed_bytes": "markdown encoded as utf-8",
    "source_chars": 5015,
    "source_bytes_utf8": 9203,
    "fetched_via": "GET /tensor/reports/7554",
    "generator": "scripts/kf/register_source_assets.py",
    "contract_version": "1.0",
    "emitted_at": "2026-11-12T01:33:35.083069+00:00",
    "notes": "Hashes and locator spans are recomputed at build time from the fetched markdown; no quote was retyped by hand."
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "manifest_version": "1.0",
      "package_id": "wp-7554-01",
      "task_type": "01-asset-registration",
      "report_id": "7554",
      "generated_at": "2026-11-12T01:33:35.081202+00:00",
      "generator": "scripts/kf/register_source_assets.py",
      "contract_version": "1.0",
      "source": {
        "uri": "tensor://reports/7554",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "d64a8ba8abe00714e3d7f8067ebfcbc30509ef0e858e1c697231b62d1eda7921",
        "chars": 5015,
        "bytes_utf8": 9203,
        "title": "plan 143（ABM）终态后的自主提案：6 条从未做过的任务书（判据真空清偿 + 两条空白学科面）",
        "scenario_key": "abm",
        "platform_figures": [
          {
            "name": "fig1_frontier_coverage.png",
            "caption": "图1 (a) plan 143 节点状态 SQL 直读；(b) 学科面 × 三源覆盖计数热图（关键词自动归类）",
            "fields_exposed_by_read_api": [
              "caption",
              "name"
            ],
            "payload_field_present": false
          },
          {
            "name": "fig2_gap_ledger.png",
            "caption": "图2 六条提案所清偿既有欠账的达标度（量值由 tensor_reports 正则抽取，log 轴）",
            "fields_exposed_by_read_api": [
              "caption",
              "name"
            ],
            "payload_field_present": false
          }
        ],
        "platform_tags": [
          "ABM",
          "proposal",
          "plan143",
          "autonomy",
          "TensorLBM",
          "TensorDEM",
          "statistical-power"
        ],
        "platform_report_meta": {
          "id": 7554,
          "mission_id": 6357,
          "created_at": "2026-11-07T22:31:06.293806+00:00",
          "status": "published"
        }
      },
      "resolution_vocabulary": {
        "resolved_in_source": "bytes located inside this report's own markdown and re-sliced from it",
        "referenced_unresolved": "reference parsed from the markdown, but the target bytes are outside this package's scope (other report / other repo / platform stores metadata only)",
        "declared_absent": "the report itself declares the asset does not exist (no bytes were ever produced)"
      },
      "counts": {
        "assets": 12,
        "by_class": {
          "report_markdown": 1,
          "artifact_file": 2,
          "code_artifact": 1,
          "embedded_figure": 2,
          "field_contour": 1,
          "data_source": 2,
          "upstream_report": 3
        },
        "by_resolution": {
          "resolved_in_source": 1,
          "referenced_unresolved": 10,
          "declared_absent": 1
        },
        "resolved_in_source": 1,
        "referenced_unresolved": 10,
        "declared_absent": 1
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "report_markdown",
          "label": "Report 7554 markdown itself (contract source)",
          "in_report_section": "title / ① 案例介绍",
          "kind": "report_markdown",
          "uri": "tensor://reports/7554",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 38,
            "start_line": 1,
            "end_line": 1,
            "quote": "# plan 143（ABM）全节点终态后的自主提案：6 条从未做过的任务书",
            "unique": true,
            "covers_document": true,
            "document_chars": 5015
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256(markdown utf-8) == contract source_hash",
            "result": "resolved"
          },
          "note": "Whole-document asset; end_char = len(markdown). Bytes re-hashed locally at build time."
        },
        {
          "asset_id": "A02",
          "asset_class": "artifact_file",
          "label": "artifacts/p143_w1/prop-6357.json (6 proposal task-sheets)",
          "in_report_section": "preamble 产物行",
          "kind": "json_artifact",
          "uri": "artifact://p143_w1/prop-6357.json",
          "locator": {
            "method": "char_span",
            "start_char": 123,
            "end_char": 167,
            "start_line": 4,
            "end_line": 4,
            "quote": "`artifacts/p143_w1/prop-6357.json`（6 条完整任务书）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path exists in this worktree (glob artifacts/p143_w1/prop-6357.json)",
            "result": "unresolved"
          },
          "note": "Path is named in the report but no such file is present in this worktree (artifacts/ is gitignored and only holds oss-lbm-kruger). Not fetched: out of this package's scope. Not a claim that the file never existed.",
          "present_in_worktree": false
        },
        {
          "asset_id": "A03",
          "asset_class": "artifact_file",
          "label": "fig_data.json (source numbers behind figures 1-2)",
          "in_report_section": "preamble 产物行; ③ 欠账账本",
          "kind": "json_artifact",
          "uri": "artifact://p143_w1/fig_data.json",
          "locator": {
            "method": "char_span",
            "start_char": 177,
            "end_char": 197,
            "start_line": 4,
            "end_line": 4,
            "quote": "`fig_data.json`（图数据）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path exists in this worktree (glob **/fig_data.json)",
            "result": "unresolved"
          },
          "note": "Cited as the single source of the figure numbers; absent from this worktree, so this package cannot independently re-derive the plotted values. No attempt to reconstruct them (no-invention constraint).",
          "present_in_worktree": false
        },
        {
          "asset_id": "A04",
          "asset_class": "code_artifact",
          "label": "gen_figs.py (figure data-extraction / plotting script)",
          "in_report_section": "preamble 产物行",
          "kind": "source_code",
          "uri": "artifact://p143_w1/gen_figs.py",
          "locator": {
            "method": "char_span",
            "start_char": 199,
            "end_char": 221,
            "start_line": 4,
            "end_line": 4,
            "quote": "`gen_figs.py`（取数/绘图脚本）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path exists in this worktree (glob **/gen_figs.py)",
            "result": "unresolved"
          },
          "note": "Referenced without a directory prefix, so its location is ambiguous in the source; not resolvable from this worktree.",
          "present_in_worktree": false
        },
        {
          "asset_id": "A05",
          "asset_class": "embedded_figure",
          "label": "fig1_frontier_coverage.png (plan-143 node states + discipline coverage heatmap)",
          "in_report_section": "③ 计算结果 / ④ 结果图 图 1",
          "kind": "platform_figure",
          "uri": "tensor://reports/7554#figures[0]",
          "locator": {
            "method": "char_span",
            "start_char": 3181,
            "end_char": 3216,
            "start_line": 77,
            "end_line": 77,
            "quote": "![fig1](fig:fig1_frontier_coverage)",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "read API (GET /tensor/reports/7554) exposes a figure payload field",
            "result": "unresolved"
          },
          "note": "The report read API returns only {name, caption} for figures[0] — no payload field — so no image bytes can be hashed or embedded here. Whether bytes are stored server-side is NOT determined by this package (control: this package submitted a 65,141-byte PNG and the read-back still exposed only name/caption). Not a claim that the figure does not exist.",
          "present_in_worktree": false
        },
        {
          "asset_id": "A06",
          "asset_class": "embedded_figure",
          "label": "fig2_gap_ledger.png (attainment ratio of the six indebtedness items, log axis)",
          "in_report_section": "③ 计算结果 / ④ 结果图 图 2",
          "kind": "platform_figure",
          "uri": "tensor://reports/7554#figures[1]",
          "locator": {
            "method": "char_span",
            "start_char": 3217,
            "end_char": 3245,
            "start_line": 78,
            "end_line": 78,
            "quote": "![fig2](fig:fig2_gap_ledger)",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "read API (GET /tensor/reports/7554) exposes a figure payload field",
            "result": "unresolved"
          },
          "note": "The report read API returns only {name, caption} for figures[1] — no payload field — so no image bytes can be hashed or embedded here. Whether bytes are stored server-side is NOT determined by this package (control: this package submitted a 65,141-byte PNG and the read-back still exposed only name/caption). Not a claim that the figure does not exist.",
          "present_in_worktree": false
        },
        {
          "asset_id": "A07",
          "asset_class": "field_contour",
          "label": "field-quantity contour (contradiction/pressure fields) for this report",
          "in_report_section": "⑤ 注意点 1",
          "kind": "absent_by_declaration",
          "uri": "tensor://reports/7554#absent:field_contour",
          "locator": {
            "method": "char_span",
            "start_char": 3582,
            "end_char": 3590,
            "start_line": 90,
            "end_line": 90,
            "quote": "图里没有场量云图",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "report self-declares that no field was solved, hence no contour exists",
            "result": "absent"
          },
          "note": "Registered as an explicit absence so that downstream tasks do not hunt for a contour that was never produced. Reason given by the report: this is a proposal-only report with no simulated field."
        },
        {
          "asset_id": "A08",
          "asset_class": "data_source",
          "label": "campaign_nodes (plan_id=143) node-state table, read by SQL",
          "in_report_section": "② 怎么做的 1. 情报归集",
          "kind": "database_table",
          "uri": "db://tensorplatform/campaign_nodes?plan_id=143",
          "locator": {
            "method": "char_span",
            "start_char": 1219,
            "end_char": 1258,
            "start_line": 27,
            "end_line": 27,
            "quote": "`campaign_nodes(plan_id=143)` 状态 SQL 直读",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "table content re-read and compared inside this package",
            "result": "unresolved"
          },
          "note": "Upstream database state, not an attachment of the report; re-reading it would be a later verification task, not asset registration. Not queried here (out of scope).",
          "present_in_worktree": false
        },
        {
          "asset_id": "A09",
          "asset_class": "data_source",
          "label": "tensor_guide_tracker KPI snapshot (success_rate/lineage_coverage/kb_samples/...)",
          "in_report_section": "① 案例介绍 参数/主体",
          "kind": "database_table",
          "uri": "db://tensorplatform/tensor_guide_tracker",
          "locator": {
            "method": "char_span",
            "start_char": 1026,
            "end_char": 1058,
            "start_line": 22,
            "end_line": 22,
            "quote": "`tensor_guide_tracker` 最新 KPI 快照",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "KPI numbers re-read from the tracker inside this package",
            "result": "unresolved"
          },
          "note": "The snapshot is point-in-time ('最新'), so the values quoted in the source cannot be re-resolved exactly later even by a reader with DB access. Baseline drift is expected.",
          "present_in_worktree": false
        },
        {
          "asset_id": "A10",
          "asset_class": "upstream_report",
          "label": "report m6334 (P1: SC-LBM droplet entry, Laplace/added-mass criteria)",
          "in_report_section": "① 案例介绍 / ⑤ 注意点",
          "kind": "report_reference",
          "uri": "tensor://reports/mission:6334",
          "locator": {
            "method": "char_span",
            "start_char": 494,
            "end_char": 503,
            "start_line": 13,
            "end_line": 13,
            "quote": "P1（m6334）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "report 6334 markdown read inside this package",
            "result": "unresolved"
          },
          "note": "Cross-report reference. Deliberately NOT fetched: the package boundary forbids touching any report_id other than 7554.",
          "present_in_worktree": false
        },
        {
          "asset_id": "A11",
          "asset_class": "upstream_report",
          "label": "report m6335 (P2: TensorDEM bonded-particle ice fracture, UCS/ν/Weibull criteria)",
          "in_report_section": "① 案例介绍 / ⑤ 注意点",
          "kind": "report_reference",
          "uri": "tensor://reports/mission:6335",
          "locator": {
            "method": "char_span",
            "start_char": 650,
            "end_char": 659,
            "start_line": 15,
            "end_line": 15,
            "quote": "P2（m6335）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "report 6335 markdown read inside this package",
            "result": "unresolved"
          },
          "note": "Same boundary rule as A10: reference recorded, bytes not read here.",
          "present_in_worktree": false
        },
        {
          "asset_id": "A12",
          "asset_class": "upstream_report",
          "label": "report m6330 (A3: run-manifest back-filler, limitation 5)",
          "in_report_section": "① 案例介绍 / ⑤ 注意点 3",
          "kind": "report_reference",
          "uri": "tensor://reports/mission:6330",
          "locator": {
            "method": "char_span",
            "start_char": 790,
            "end_char": 799,
            "start_line": 17,
            "end_line": 17,
            "quote": "A3（m6330）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "report 6330 markdown read inside this package",
            "result": "unresolved"
          },
          "note": "Same boundary rule as A10/A11; the report quotes A3's limitation 5, which this package does not re-verify.",
          "present_in_worktree": false
        }
      ],
      "claims": [],
      "integrity": {
        "quote_uniqueness": "checked",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true
      }
    }
  },
  "claims": []
}
```
