# KF-RESULT wp-7883-01

知识产线工序 `wp-7883-01`（task_type `01-asset-registration`）对 report_id=`7883` 的资产登记结果。
**范围铁律**：只触碰 report_id=7883，不抽取、不生成知识、不标 verified（verification 由平台门计算）。

## ① 本工序做了什么

把 `tensor://reports/7883` 的 `markdown` 登记为**可回溯资产**：

* **确认身份**：字节数 11,181 B、字符数 7,585、sha256 `fc4d21ec4e30740b8596ea5b2892c877…e5fd77f5`，
  与工作包契约声明的 `sha256:fc4d21ec4e30740b…` 及 `chars: 7585` **逐位一致**（`hash_matches_contract=True`、`chars_matches_contract=True`）。
* **登记可解析资产 21 条**：章节 6、表格 6、源码文件引用 3、源文档 1、报告记录内嵌图 1、API 路由引用 1、工件文件引用 1、图片文件引用 1、记录元数据 1（其中路径/路由类引用 6 条）。
  状态分布：resolved 13 / unresolved 6 / metadata_only 2。
* **不做的**：正文抽取、claims 生成（`claims=[]`，契约允许空数组）、verified 标记、跨 report_id 的任何读写。

## ② 怎么做的（步骤 / 工具 / 关键设置）

工具链：Python 3.11 + 平台 REST（`/auth/login`、`/tensor/reports/7883`）+ `jsonschema` + matplotlib(Agg) + pytest。
一键脚本 `scripts/kf/wp_7883_01.py`（子命令 `build/result/figure/verify/all`）。

1. **取原文**：登录后 `GET /api/v1/tensor/reports/7883`，取 `markdown` 字段（不使用 psql 直连——本账号对
   `tensor_reports` 无 SELECT 权限，接口是唯一合法信道）。
2. **零手抄**：哈希/字符数/行号/引文全部由脚本从同一次取回的字节里**切**出来；`build` 前置断言哈希与字符数等于契约值，
   不等即中止（不产生"看起来成功"的产物）。
3. **解析规则**：`## ` 行 → 章节（line span = 本节到下一节前一行）；连续 `|` 行块 → 表格（数据行数 = 块行数 − 表头 − `---` 分隔行）；
   反引号内的路径/路由 token → 路径引用（出现级身份 = (path, line)，同一文件不同行不合并）；`figures[]` → 内嵌图条目。
4. **本地可解析性**：路径引用只在本交付工作树内解析（`Path.is_file()` / `glob`），查不到就记 `unresolved` + 原因，
   **绝不假设存在**（生产方 `ship-performance-platform` 不在本工作包边界内）。
5. **独立复核**：`verify` 子命令**重新取一次原文**，对 21 个 locator 逐个重解：单行 locator 要求
   `lines[n-1] == quote` 且 `quote in markdown`；区间 locator 要求 `markdown[line_start..line_end] == quote`；
   再以 `jsonschema.validate` 把信封对照仓库内 `schemas/kf_result.v1.schema.json` 校验。
6. **离线守卫**：`pytest -q tests/test_kf_wp_7883_01.py` 12 条用例（信封 schema、outputs 与落盘文件逐字节一致、
   表格引文自洽、未解析必带原因、claims 为空且无 verified、单报范围）。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-7883-01/asset_manifest.json` | 资产清单主体：21 条资产、20,404 B、sha256 `3757cbedfc50c23b…`；含逐资产 locator（行号+逐字引文）与 resolution 状态 |
| `docs/kf/wp-7883-01/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs），`23,252` B；`outputs.asset_manifest.json` 内嵌清单原文（与落盘文件解析后逐值相等） |
| `docs/kf/wp-7883-01/verification.json` | 9 项 acceptance 逐条机器判定 + 复算哈希，`all_pass=True` |
| `docs/kf/wp-7883-01/fig1_asset_coverage_map.png` | 资产覆盖图（149,666 B）：18 条有行号定位的资产在源文档上的区间条带 |
| `scripts/kf/wp_7883_01.py` | 可复跑管线：build / result / figure / verify |
| `tests/test_kf_wp_7883_01.py` | 12 条离线 pytest 守卫 |

## ④ 证据定位表（资产 → 原文定位 → 逐字引文片段）

行号为 `markdown` 按 `\n` 切分后的 1-based 行号；引文片段由脚本从原文切片生成（此处按 70 字符截断显示，完整引文见
`asset_manifest.json` 的 `locator.quote`，平台可独立重算 sha256 并做子串复核）。

| asset_id | 类型 | 定位 | 原文引文片段（逐字） |
|---|---|---|---|
| `r7883:source` | report_markdown | 字段 `markdown` | P151-N04 · EEDI/EEXI/CII 合规计算链成熟化：IMO 公式锚 + 三船型裁决面 + 减排技术折减 |
| `r7883:sec:01` | markdown_section | L3 | ## ① 案例介绍（物理背景 / 几何 / 参数表） |
| `r7883:sec:02` | markdown_section | L28 | ## ② 怎么做的（方法 / 流程 / 关键设置 / 工具链） |
| `r7883:sec:03` | markdown_section | L49 | ## ③ 计算结果（数字表） |
| `r7883:sec:04` | markdown_section | L92 | ## ④ 图 |
| `r7883:sec:05` | markdown_section | L98 | ## ⑤ 注意点（踩过的坑 / 局限 / 适用范围） |
| `r7883:sec:06` | markdown_section | L117 | ## ⑥ 误差判定（逐项列基准 + 是否 <3%） |
| `r7883:tbl:01` | markdown_table | L19–L23 | \| 船型 \| DWT \| MCR [kW] \| V_ref [kn] \| SFC_ME/AE \| Δ [t] \| DWT/Δ \| Fn \| |
| `r7883:tbl:02` | markdown_table | L53–L57 | \| 船型 \| 参考线 \| Phase2 X% \| Required \| Attained \| 裕度 \| 裁决 \| |
| `r7883:tbl:03` | markdown_table | L64–L68 | \| 船型 \| Required \| Attained(未限功率) \| 裕度 \| 裁决 \| 反解 EPL 设定点 \| |
| `r7883:tbl:04` | markdown_table | L72–L76 | \| 船型 \| 年油耗 [t] \| 年航程 [nm] \| 参考线 \| 2024 Required \| Attained \| 2024 评级 \|… |
| `r7883:tbl:05` | markdown_table | L80–L86 | \| 措施 \| 折减后 CII \| 折减率 \| 评级 \| 相对要求值 \| |
| `r7883:tbl:06` | markdown_table | L119–L130 | \| 判据 \| 内容 \| 本次数值 \| 容差 \| 结论 \| |
| `r7883:fig:01` | embedded_figure | 字段 `figures`[0] | 六幅判据图拼合（左上→右下）：(1) EEDI 参考线与散货 Phase1/2/3 要求值+三船达到值；(2) V_ref ±10% 的 E… |
| `r7883:ref:01` | api_route_reference | L30 | 工具链：Python 3.11 + FastAPI（`/api/v1/green-compliance/*`，已注册进 `backend/m… |
| `r7883:ref:02` | source_code_reference | L30 | 工具链：Python 3.11 + FastAPI（`/api/v1/green-compliance/*`，已注册进 `backend/m… |
| `r7883:ref:03` | source_code_reference | L31 | 校验 + pytest 闸门 + matplotlib（Agg）出图；`artifacts/green_compliance_m6650/r… |
| `r7883:ref:04` | artifact_file_reference | L32 | 判据 (a)–(j) 并把数字写进 `acceptance.json`（报告数字与图同源，零手抄）。 |
| `r7883:ref:05` | source_code_reference | L38 | 3. **表单一真源 + sha256**：`imo_tables.py` 集中全部 IMO 系数，逐表 canonical-JSON 哈希… |
| `r7883:ref:06` | figure_file_reference | L96 | 单幅高清 PNG 见 `artifacts/green_compliance_m6650/fig1..fig6*.png`。 |
| `r7883:meta:record` | report_metadata | 字段 `record` |  |

**未登记/未解析的显式说明**：

* unresolved 6 条：`/api/v1/green-compliance/*`(api_route_reference), `backend/main.py`(source_code_reference), `artifacts/green_compliance_m6650/run_acceptance.py`(source_code_reference), `acceptance.json`(artifact_file_reference), `imo_tables.py`(source_code_reference), `artifacts/green_compliance_m6650/fig1..fig6*.png`(figure_file_reference) ——
  原因：生产方仓库/接口不在本工作包边界内，本工作树内无对应字节，**不假设存在、不算作已登记工件**。
* `kernel.attained_intensity` / `kernel.dimension_check` / `verify()` — 报告正文引用的是**代码符号**而非文件路径，不是可解析的字节工件，故不登记（避免把符号当文件）；
* 报告 ④ 提到的 `fig1..fig6*.png` 单幅图：正文只给通配路径，无逐文件字节，登记为 1 条 glob 引用且 unresolved；

## ⑤ 注意点与局限

* **哈希只保证"未被静默改动"**：`sha256:fc4d21ec4e30740b…` 证明我读到并登记的就是平台现存的那份 markdown；
  它**不保证源报告内容正确**。源报告自身已把 IMO 表系数判为 WITHHELD（离线转录、未回读决议原文），本工序不改写这一分级。
* **内嵌图无字节可哈希**：记录的 `figures[0]` 只有 name+caption，无 `png_base64` 载荷，
  故登记为 `metadata_only`，`sha256=null`——不是漏算，是不可算。
* **平台丢弃图载荷（实测）**：发布时 `figures:[{name,caption,png_base64}]` 入库后回读只剩 `name`+`caption`，`png_base64` 被剥掉，
  因此任何"内嵌图字节可哈希"的说法都不可复核；本包内图的权威副本是仓库文件
  `docs/kf/wp-7883-01/fig1_asset_coverage_map.png`（sha256 `5934ff98fb6a3b81243867a413785df6bce6de15374b8b59f89a6610b0e8c4ca`，149,666 B），平台侧图仅作展示。
* **表格引文是跨行切片**：`markdown_table` 的 `quote` 含换行，子串复核时按原文全文匹配（不做行内规范化）；数据行数不含表头与 `---` 行。
* **manifest 不是字节级可复现**：`generated_at` 时间戳使两次构建的字节不同；语义部分（assets/locator/resolution）确定且幂等，
  复核请比对 `verification.json` 的 `manifest_sha256` 单次快照，而不是跨次比字节。
* **无抽取即无 claims**：本工序 claims 为空是契约允许的完整结果，不因"看起来空"而编造知识对象。
* **版本注记（诚实记账）**：本报告取代此前的同名报告 id=14684（该版散文 summary 把路径/路由类引用写成 5 条（实为 6 条；清单 summary.by_kind_and_status 本身正确））; id=14687（该版未实测平台是否保留 figures[].png_base64，回读发现载荷被丢弃，故补记该局限（图以仓库内 PNG 为准））。平台 `/tensor/reports/` 详情端点对 PATCH/PUT/DELETE 一律 405（已实测），无法原地更正，故以新报告发布并声明取代链；请以本报告的 json 块为准。
* **边界**：全程只读 report_id=7883；脚本 `scope_single_report_only` 检查输出中出现的 report_id 引用集合 = {'7883'}。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 判定 | 机器证据（来自 verification.json） |
|---|---|---|
| `valid_json` | PASS | json.loads OK (manifest); envelope checked under schema_pass |
| `schema_pass` | PASS | {"envelope_structurally_valid": true, "manifest_required_keys": true, "envelope": "jsonschema.validate OK against schemas/kf_result.v1.schema.json"} |
| `source_locator_resolvable` | PASS | checked 21 locators, unresolvable=[] |
| `source_hash_matches` | PASS | recomputed=fc4d21ec4e30740b8596ea5b2892c877444ab58e274d5d301638322ae5fd77f5 manifest=fc4d21ec4e30740b8596ea5b2892c877444ab58e274d5d301638322ae5fd77f5  |
| `no_duplicate_ids` | PASS | asset_ids=21 unique=21 |
| `all_claims_have_evidence_or_explicit_unresolved_status` | PASS | claims=0 violating=0 (empty array: vacuously satisfied, contract allows empty claims) |
| `do_not_mark_claims_as_verified` | PASS | no claim carries status='verified' |
| `outputs_match_declared_file` | PASS | embedded==disk:True binding_sha256_ok:True binding_bytes_ok:True |
| `scope_single_report_only` | PASS | report_id references found: ['7883'] |

补充：离线 `pytest -q tests/test_kf_wp_7883_01.py` → **12 passed**（本报告写作时实跑）。

**误差判定（本题无物理基准，逐项列可判定量）**：源字节哈希复算 = 契约值（逐位相等，偏差 0 bit）；
字符数 7585 = 契约 7585（偏差 0）；
locator 重解析 21/21 通过（失败 0）；表内引文 sha256 自洽 6/6。
**是否 <3%**：本工序全为离散精确判定（哈希/计数/子串），偏差恒为 0，**不适用 3% 阈值**；无外部实验或解析解基准，
因为登记工序不产生任何物理量——此点如实声明，不以"全 PASS"冒充"内容已被验证"。

**一键复跑**：

```
export TENSOR_API_BASE TENSOR_AGENT_USER TENSOR_AGENT_PASS   # 平台凭证
python3 scripts/kf/wp_7883_01.py all        # build -> result -> figure -> verify
python3 -m pytest -q tests/test_kf_wp_7883_01.py          # 离线守卫
```

`all` 的退出码非 0 即代表 acceptance 未全过（verify 逐条打印 detail），可直接用于门禁。

## 结果信封（kf_result.v1，平台门的机器信道）

下列 json 块即 `docs/kf/wp-7883-01/kf_result.json` 原文（唯一 json 代码块；结构与字段名未改）。

```json
{
  "package_id": "wp-7883-01",
  "task_type": "01-asset-registration",
  "report_id": "7883",
  "provenance": {
    "source_uri": "tensor://reports/7883",
    "source_field": "markdown",
    "source_hash": "sha256:fc4d21ec4e30740b8596ea5b2892c877444ab58e274d5d301638322ae5fd77f5",
    "hash_algo": "sha256",
    "hashed_bytes": "markdown encoded as utf-8",
    "source_chars": 7585,
    "source_bytes_utf8": 11181,
    "fetched_via": "GET /api/v1/tensor/reports/7883",
    "generator": "scripts/kf/wp_7883_01.py",
    "contract_version": "1.0",
    "outputs_binding": {
      "asset_manifest.json": {
        "path": "docs/kf/wp-7883-01/asset_manifest.json",
        "sha256": "3757cbedfc50c23bdffd78b8a83a444404230695491af1a191b88686f5a16a57",
        "bytes": 20404
      }
    }
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-7883-01",
      "task_type": "01-asset-registration",
      "report_id": "7883",
      "schema_note": "Envelope follows schemas/kf_result.v1.schema.json (task_type '01-asset-registration' matches the schema's '^[0-9]{2}(-[a-z0-9-]+)?$'; claims present as an empty array, which the schema allows). The asset_manifest body is self-described below.",
      "generated_at": "2026-11-12T01:30:47.766100+00:00",
      "provenance": {
        "source_uri": "tensor://reports/7883",
        "source_field": "markdown",
        "source_hash": "sha256:fc4d21ec4e30740b8596ea5b2892c877444ab58e274d5d301638322ae5fd77f5",
        "hash_algo": "sha256",
        "hashed_bytes": "markdown encoded as utf-8",
        "source_chars": 7585,
        "source_bytes_utf8": 11181,
        "contract_declared_hash": "sha256:fc4d21ec4e30740b8596ea5b2892c877444ab58e274d5d301638322ae5fd77f5",
        "contract_declared_chars": 7585,
        "hash_matches_contract": true,
        "chars_matches_contract": true,
        "report_title": "P151-N04 · EEDI/EEXI/CII 合规计算链成熟化：IMO 公式锚 + 三船型裁决面 + 减排技术折减",
        "report_title_matches_contract": true,
        "report_scenario_key": "green_compliance_eedi_eexi_cii",
        "report_mission_id": 6650,
        "report_created_at": "2026-11-08T06:50:37.355283+00:00",
        "report_tags": [
          "EEDI",
          "EEXI",
          "CII",
          "IMO",
          "MEPC.364(79)",
          "绿色航行",
          "合规裁决",
          "风助推进",
          "台账哈希链",
          "P151-N04"
        ],
        "fetched_via": "GET /api/v1/tensor/reports/7883",
        "generator": "scripts/kf/wp_7883_01.py",
        "contract_version": "1.0"
      },
      "resolution_status_vocabulary": {
        "resolved": "bytes located and hashed (source markdown, source slice, or a file inside this worktree)",
        "unresolved": "reference parsed from the report but the target is outside this package's scope",
        "metadata_only": "platform lists the asset but stores no byte payload, so no hash is claimable"
      },
      "assets": [
        {
          "asset_id": "r7883:source",
          "kind": "report_markdown",
          "uri": "tensor://reports/7883",
          "source_field": "markdown",
          "title": "P151-N04 · EEDI/EEXI/CII 合规计算链成熟化：IMO 公式锚 + 三船型裁决面 + 减排技术折减",
          "chars": 7585,
          "bytes_utf8": 11181,
          "sha256": "fc4d21ec4e30740b8596ea5b2892c877444ab58e274d5d301638322ae5fd77f5",
          "locator": {
            "scheme": "report_field",
            "field": "markdown"
          },
          "resolution": {
            "status": "resolved",
            "scope": "platform_api",
            "via": "GET /api/v1/tensor/reports/7883"
          }
        },
        {
          "asset_id": "r7883:sec:01",
          "kind": "markdown_section",
          "uri": "tensor://reports/7883#line=3",
          "heading": "① 案例介绍（物理背景 / 几何 / 参数表）",
          "line_start": 3,
          "line_end": 27,
          "n_lines": 25,
          "locator": {
            "scheme": "markdown_line",
            "line": 3,
            "quote": "## ① 案例介绍（物理背景 / 几何 / 参数表）",
            "line_start": 3,
            "line_end": 27
          },
          "resolution": {
            "status": "resolved",
            "scope": "source_markdown"
          }
        },
        {
          "asset_id": "r7883:sec:02",
          "kind": "markdown_section",
          "uri": "tensor://reports/7883#line=28",
          "heading": "② 怎么做的（方法 / 流程 / 关键设置 / 工具链）",
          "line_start": 28,
          "line_end": 48,
          "n_lines": 21,
          "locator": {
            "scheme": "markdown_line",
            "line": 28,
            "quote": "## ② 怎么做的（方法 / 流程 / 关键设置 / 工具链）",
            "line_start": 28,
            "line_end": 48
          },
          "resolution": {
            "status": "resolved",
            "scope": "source_markdown"
          }
        },
        {
          "asset_id": "r7883:sec:03",
          "kind": "markdown_section",
          "uri": "tensor://reports/7883#line=49",
          "heading": "③ 计算结果（数字表）",
          "line_start": 49,
          "line_end": 91,
          "n_lines": 43,
          "locator": {
            "scheme": "markdown_line",
            "line": 49,
            "quote": "## ③ 计算结果（数字表）",
            "line_start": 49,
            "line_end": 91
          },
          "resolution": {
            "status": "resolved",
            "scope": "source_markdown"
          }
        },
        {
          "asset_id": "r7883:sec:04",
          "kind": "markdown_section",
          "uri": "tensor://reports/7883#line=92",
          "heading": "④ 图",
          "line_start": 92,
          "line_end": 97,
          "n_lines": 6,
          "locator": {
            "scheme": "markdown_line",
            "line": 92,
            "quote": "## ④ 图",
            "line_start": 92,
            "line_end": 97
          },
          "resolution": {
            "status": "resolved",
            "scope": "source_markdown"
          }
        },
        {
          "asset_id": "r7883:sec:05",
          "kind": "markdown_section",
          "uri": "tensor://reports/7883#line=98",
          "heading": "⑤ 注意点（踩过的坑 / 局限 / 适用范围）",
          "line_start": 98,
          "line_end": 116,
          "n_lines": 19,
          "locator": {
            "scheme": "markdown_line",
            "line": 98,
            "quote": "## ⑤ 注意点（踩过的坑 / 局限 / 适用范围）",
            "line_start": 98,
            "line_end": 116
          },
          "resolution": {
            "status": "resolved",
            "scope": "source_markdown"
          }
        },
        {
          "asset_id": "r7883:sec:06",
          "kind": "markdown_section",
          "uri": "tensor://reports/7883#line=117",
          "heading": "⑥ 误差判定（逐项列基准 + 是否 <3%）",
          "line_start": 117,
          "line_end": 141,
          "n_lines": 25,
          "locator": {
            "scheme": "markdown_line",
            "line": 117,
            "quote": "## ⑥ 误差判定（逐项列基准 + 是否 <3%）",
            "line_start": 117,
            "line_end": 141
          },
          "resolution": {
            "status": "resolved",
            "scope": "source_markdown"
          }
        },
        {
          "asset_id": "r7883:tbl:01",
          "kind": "markdown_table",
          "uri": "tensor://reports/7883#line=19-23",
          "line_start": 19,
          "line_end": 23,
          "n_data_rows": 3,
          "n_columns": 8,
          "quote_sha256": "ce576d2890bb43405a6493d0d51c5aa5a2d2ae44e90c80d9365709ffef7ac0b7",
          "locator": {
            "scheme": "markdown_line_range",
            "line": 19,
            "line_start": 19,
            "line_end": 23,
            "quote": "| 船型 | DWT | MCR [kW] | V_ref [kn] | SFC_ME/AE | Δ [t] | DWT/Δ | Fn |\n|---|---|---|---|---|---|---|---|\n| Kamsarmax 型散货船 80,000 DWT | 80,000 | 9,600 | 14.5 | 165/215 | 90,507 | 0.884 | 0.159 |\n| VLCC 油轮 300,000 DWT | 300,000 | 27,000 | 15.0 | 168/215 | 332,838 | 0.901 | 0.138 |\n| Post-panamax 集装箱船 65,000 DWT | 65,000 | 22,000 | 21.0 | 170/215 | 77,531 | 0.838 | 0.221 |"
          },
          "resolution": {
            "status": "resolved",
            "scope": "source_markdown"
          }
        },
        {
          "asset_id": "r7883:tbl:02",
          "kind": "markdown_table",
          "uri": "tensor://reports/7883#line=53-57",
          "line_start": 53,
          "line_end": 57,
          "n_data_rows": 3,
          "n_columns": 7,
          "quote_sha256": "69b10f2159d1c5261774b87378043493efa4fe920b83fa4c0e5db3fbc952dee0",
          "locator": {
            "scheme": "markdown_line_range",
            "line": 53,
            "line_start": 53,
            "line_end": 57,
            "quote": "| 船型 | 参考线 | Phase2 X% | Required | Attained | 裕度 | 裁决 |\n|---|---|---|---|---|---|---|\n| bulk_80k | 4.4087 | 6.667 | 4.1147 | 3.4744 | +15.56% | **COMPLIANT** |\n| tanker_300k | 2.5888 | 20.000 | 2.0710 | 2.4959 | -20.51% | **NON_COMPLIANT** |\n| container_65k | 18.7803 | 7.812 | 17.3131 | 6.8031 | +60.71% | **COMPLIANT** |"
          },
          "resolution": {
            "status": "resolved",
            "scope": "source_markdown"
          }
        },
        {
          "asset_id": "r7883:tbl:03",
          "kind": "markdown_table",
          "uri": "tensor://reports/7883#line=64-68",
          "line_start": 64,
          "line_end": 68,
          "n_data_rows": 3,
          "n_columns": 6,
          "quote_sha256": "9249e6a2155f21f4606c5d05ad76cf207b96028b7b3ce7d854be2108ded46b31",
          "locator": {
            "scheme": "markdown_line_range",
            "line": 64,
            "line_start": 64,
            "line_end": 68,
            "quote": "| 船型 | Required | Attained(未限功率) | 裕度 | 裁决 | 反解 EPL 设定点 |\n|---|---|---|---|---|---|\n| bulk_80k | 3.5269 | 3.4744 | +1.49% | **COMPLIANT** | 无需限功率 |\n| tanker_300k | 2.0710 | 2.4959 | -20.51% | **NON_COMPLIANT** | 16,596 kW (P/P₀=0.8195) |\n| container_65k | 15.0242 | 6.8031 | +54.72% | **COMPLIANT** | 无需限功率 |"
          },
          "resolution": {
            "status": "resolved",
            "scope": "source_markdown"
          }
        },
        {
          "asset_id": "r7883:tbl:04",
          "kind": "markdown_table",
          "uri": "tensor://reports/7883#line=72-76",
          "line_start": 72,
          "line_end": 76,
          "n_data_rows": 3,
          "n_columns": 8,
          "quote_sha256": "9403e6a35b4d1a36b96cd93c8d4097a678837123e8da90785897dcb0d2520ab7",
          "locator": {
            "scheme": "markdown_line_range",
            "line": 72,
            "line_start": 72,
            "line_end": 76,
            "quote": "| 船型 | 年油耗 [t] | 年航程 [nm] | 参考线 | 2024 Required | Attained | 2024 评级 | 2026 评级 |\n|---|---|---|---|---|---|---|---|\n| bulk_80k | 7,437 | 83,520 | 4.2317 | 3.9355 | 3.4662 | **B**（0.881·req） | B（0.920） |\n| tanker_300k | 20,741 | 86,400 | 2.3926 | 2.2251 | 2.4918 | **D**（1.120·req） | D（1.170） |\n| container_65k | 17,148 | 120,960 | 8.7908 | 8.1754 | 6.7915 | **A**（0.831·req） | B（0.868） |"
          },
          "resolution": {
            "status": "resolved",
            "scope": "source_markdown"
          }
        },
        {
          "asset_id": "r7883:tbl:05",
          "kind": "markdown_table",
          "uri": "tensor://reports/7883#line=80-86",
          "line_start": 80,
          "line_end": 86,
          "n_data_rows": 5,
          "n_columns": 5,
          "quote_sha256": "9828e7187fdfcb4ce390834d909a7230543efe2aeaaf6cb1bd62e753d79e4148",
          "locator": {
            "scheme": "markdown_line_range",
            "line": 80,
            "line_start": 80,
            "line_end": 86,
            "quote": "| 措施 | 折减后 CII | 折减率 | 评级 | 相对要求值 |\n|---|---|---|---|---|\n| baseline | 3.4662 | 0.00% | **B** | 0.920 |\n| wind_4rotor_8.5ms | 3.1146 | 10.15% | **A** | 0.827 |\n| air_lubrication_5pct | 3.2929 | 5.00% | **B** | 0.874 |\n| speed_opt_0.90 | 2.8076 | 19.00% | **A** | 0.745 |\n| all_combined | 2.3966 | 30.86% | **A** | 0.636 |"
          },
          "resolution": {
            "status": "resolved",
            "scope": "source_markdown"
          }
        },
        {
          "asset_id": "r7883:tbl:06",
          "kind": "markdown_table",
          "uri": "tensor://reports/7883#line=119-130",
          "line_start": 119,
          "line_end": 130,
          "n_data_rows": 10,
          "n_columns": 5,
          "quote_sha256": "c74c5da78a0020e97c0510a340c76dc2de860e9d37369035da36c09ba13044e8",
          "locator": {
            "scheme": "markdown_line_range",
            "line": 119,
            "line_start": 119,
            "line_end": 130,
            "quote": "| 判据 | 内容 | 本次数值 | 容差 | 结论 |\n|---|---|---|---|---|\n| (a) | EEDI 基线曲线：bulk DWT=80000 vs 锚 4.41 | 基线 4.408657 vs 锚 4.41，误差 0.0304% | <2% | PASS |\n| (b) | EEDI 折减因子 Phase1/2/3 vs IMO 表 | 最差相对误差 5.56e-06% | <0.1% | PASS |\n| (c) | EEDI 量纲单测（代数核 vs SI 独立路径） | 核 vs SI 路径最差相对误差 1.31e-16 | <1e-9 | PASS |\n| (d) | EEXI 与 EEDI 一致性（未限功率） | 三船最大绝对残差 0.0e+00 | <1e-10 | PASS |\n| (e) | CII 评级边界 vs IMO dd 向量 | 9 组边界最大相对误差 0.00e+00% | <1% | PASS |\n| (f) | CII 单调性（容量↑↓ / V_ref↑↓，斜率应为 −1） | log-log 斜率 容量 -1.000000 / 航速 -1.000000 | 斜率 −1±1e-9 且严格单调 | PASS |\n| (g) | 合规裁决/评级方向性（要求收紧 → 只能变差） | EEDI 阶段轨迹与 CII 年度轨迹的裁决/评级均单调不降 | 单调不降 | PASS |\n| (h) | V_ref ±10% → EEDI ∓ 弹性 | 与名义 ∓10% 的最大偏差 1.111 pp | <2 pp | PASS |\n| (i) | IMO 表数据 sha256 可追溯 | 总哈希 18daccce16463ad7…（与金标一致=True） | 与金标一致 | PASS |\n| (j) | pytest ≥20 全绿含 ≥4 负控 | pytest 81 passed / 0 failed，负控 20 条 | ≥20 全绿含 ≥4 负控 | PASS |"
          },
          "resolution": {
            "status": "resolved",
            "scope": "source_markdown"
          }
        },
        {
          "asset_id": "r7883:fig:01",
          "kind": "embedded_figure",
          "uri": "tensor://reports/7883#figures[0]",
          "name": "green_compliance_m6650_montage.png",
          "caption": "六幅判据图拼合（左上→右下）：(1) EEDI 参考线与散货 Phase1/2/3 要求值+三船达到值；(2) V_ref ±10% 的 EEDI 弹性与解析 1/V 律；(3) CII 要求值随 Z% 收紧与 dd1..dd4 评级边界；(4) CII 随容量/航速的双对数斜率 −1.000；(5) 风助等价节能比例与复合折减；(6) VLCC 的 EEXI 随 EPL 限功率下降与二分法反解的合规设定点。",
          "bytes": null,
          "sha256": null,
          "locator": {
            "scheme": "report_field",
            "field": "figures",
            "index": 0
          },
          "resolution": {
            "status": "metadata_only",
            "scope": "platform_api",
            "has_payload": false,
            "reason": "record lists name+caption only; no png_base64 payload stored, so no byte hash is claimable"
          }
        },
        {
          "asset_id": "r7883:ref:01",
          "kind": "api_route_reference",
          "uri": "tensor://reports/7883#line=30",
          "path_reference": "/api/v1/green-compliance/*",
          "locator": {
            "scheme": "markdown_line",
            "line": 30,
            "quote": "工具链：Python 3.11 + FastAPI（`/api/v1/green-compliance/*`，已注册进 `backend/main.py`）+ pydantic 入参"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "platform_api_route",
            "reason": "HTTP route declared in the source, not a file asset; no bytes to hash in this work package"
          }
        },
        {
          "asset_id": "r7883:ref:02",
          "kind": "source_code_reference",
          "uri": "tensor://reports/7883#line=30",
          "path_reference": "backend/main.py",
          "locator": {
            "scheme": "markdown_line",
            "line": 30,
            "quote": "工具链：Python 3.11 + FastAPI（`/api/v1/green-compliance/*`，已注册进 `backend/main.py`）+ pydantic 入参"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree (producer artefact lives in another repository, outside this package's boundary)"
          }
        },
        {
          "asset_id": "r7883:ref:03",
          "kind": "source_code_reference",
          "uri": "tensor://reports/7883#line=31",
          "path_reference": "artifacts/green_compliance_m6650/run_acceptance.py",
          "locator": {
            "scheme": "markdown_line",
            "line": 31,
            "quote": "校验 + pytest 闸门 + matplotlib（Agg）出图；`artifacts/green_compliance_m6650/run_acceptance.py` 一次跑完"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree (producer artefact lives in another repository, outside this package's boundary)"
          }
        },
        {
          "asset_id": "r7883:ref:04",
          "kind": "artifact_file_reference",
          "uri": "tensor://reports/7883#line=32",
          "path_reference": "acceptance.json",
          "locator": {
            "scheme": "markdown_line",
            "line": 32,
            "quote": "判据 (a)–(j) 并把数字写进 `acceptance.json`（报告数字与图同源，零手抄）。"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree (producer artefact lives in another repository, outside this package's boundary)"
          }
        },
        {
          "asset_id": "r7883:ref:05",
          "kind": "source_code_reference",
          "uri": "tensor://reports/7883#line=38",
          "path_reference": "imo_tables.py",
          "locator": {
            "scheme": "markdown_line",
            "line": 38,
            "quote": "3. **表单一真源 + sha256**：`imo_tables.py` 集中全部 IMO 系数，逐表 canonical-JSON 哈希 + 总哈希"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree (producer artefact lives in another repository, outside this package's boundary)"
          }
        },
        {
          "asset_id": "r7883:ref:06",
          "kind": "figure_file_reference",
          "uri": "tensor://reports/7883#line=96",
          "path_reference": "artifacts/green_compliance_m6650/fig1..fig6*.png",
          "locator": {
            "scheme": "markdown_line",
            "line": 96,
            "quote": "单幅高清 PNG 见 `artifacts/green_compliance_m6650/fig1..fig6*.png`。"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "glob reference has no match in the TensorKnowledge delivery worktree"
          }
        },
        {
          "asset_id": "r7883:meta:record",
          "kind": "report_metadata",
          "uri": "tensor://reports/7883#record",
          "scenario_key": "green_compliance_eedi_eexi_cii",
          "mission_id": 6650,
          "tags": [
            "EEDI",
            "EEXI",
            "CII",
            "IMO",
            "MEPC.364(79)",
            "绿色航行",
            "合规裁决",
            "风助推进",
            "台账哈希链",
            "P151-N04"
          ],
          "created_at": "2026-11-08T06:50:37.355283+00:00",
          "status": "published",
          "locator": {
            "scheme": "report_field",
            "field": "record"
          },
          "resolution": {
            "status": "metadata_only",
            "scope": "platform_api",
            "has_payload": false,
            "reason": "platform stores these fields as record metadata; no byte payload to hash (the hashable payload of this package is the markdown field)"
          }
        }
      ],
      "claims": [],
      "claims_note": "Contract: 'claims 允许为空数组' and 03-extraction is out of scope for task_type 01-asset-registration; no knowledge object was generated (no_forced_claim_generation).",
      "summary": {
        "asset_count": 21,
        "by_kind_and_status": {
          "report_markdown/resolved": 1,
          "markdown_section/resolved": 6,
          "markdown_table/resolved": 6,
          "embedded_figure/metadata_only": 1,
          "api_route_reference/unresolved": 1,
          "source_code_reference/unresolved": 3,
          "artifact_file_reference/unresolved": 1,
          "figure_file_reference/unresolved": 1,
          "report_metadata/metadata_only": 1
        },
        "resolved": 13,
        "unresolved": 6,
        "metadata_only": 2,
        "sections": 6,
        "tables": 6,
        "figures_in_record": 1,
        "claims": 0,
        "distinct_referenced_paths": 6
      },
      "identity_granularity": "Reference assets are occurrence-level: identity is (path_reference, markdown_line), so the same file cited on different lines yields distinct asset_ids carrying their own quotes; distinct_referenced_paths is the deduplicated view.",
      "artifact_endpoint_probe": {
        "/tensor/reports/7883/artifacts": {
          "status": "http_404"
        },
        "/tensor/artifacts?report_id=7883": {
          "status": "http_404"
        }
      },
      "limitations": [
        "Registration only: no text extraction, no claim generation, no 'verified' marks (verification is platform-gated).",
        "Referenced paths are resolved strictly inside the TensorKnowledge delivery worktree; the producer tree (ship-performance-platform: backend/ + artifacts/green_compliance_m6650/) is outside this package's boundary, so those references stay unresolved by design rather than being assumed present.",
        "Report metadata 'figures' is inventoried as-is; where the record stores no payload the entry is metadata_only.",
        "markdown_table quotes are verbatim multi-line slices; n_data_rows excludes the header and '---' separator rows.",
        "Output location: docs/kf/wp-7883-01/ (not artifacts/), because .gitignore drops artifacts/** at the push gate."
      ]
    }
  },
  "claims": []
}
```
