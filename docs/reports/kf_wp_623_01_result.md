# KF-RESULT wp-623-01

**工作包**: `wp-623-01` · **task_type**: `01-asset-registration` · **report_id**: `623` · **lane**: `C` · **delivery**: TensorKnowledge (draft)
**源**: `tensor://reports/623` 字段 `markdown` · **哈希口径**: UTF-8 字节 · `sha256:b513d521df6b393c365a587d49bc06f2482396a01228ed72f53d9e7132d86dcf`

## ① 本工序做了什么

对 report 623《DEM3D Large-Scale Particle Benchmark: 10k-100k Wall-Clock Scaling Study》执行**资产登记**（工序 01）：只确认源资产身份、清点可解析的附件/工件，**不做抽取、不做报告类型判定、不标 verified**。

1. **源资产身份确认**：`markdown` = 7324 B / 7281 字符 / 151 行，sha256 = `sha256:b513d521df6b393c365a587d49bc06f2482396a01228ed72f53d9e7132d86dcf`，与工作包契约 `source_hash` **逐字节一致**（契约 chars=7281 亦一致）。
2. **登记资产 16 项** = 1 源 markdown + 2 报告记录内嵌图元数据 + 13 条正文路径引用（11 个不同路径，同一路径在不同行各算一次）；另登记 3 条符号级引用（模块入口 / 上游报告号）。
3. **每条资产带可解析定位**：markdown 行号 + 该行逐字引文 + 引文 sha256，共 17 个定位点，全部在**实时拉取的 markdown** 上重解析通过（17/17）。
4. **解析状态三分**：`resolved` 1（源 markdown，已在工作树落本地副本）、`metadata_only` 2（图只有 name/caption，平台不供字节，不假装有哈希）、`unresolved` 13（正文声明的 TensorDEM 工件，**在工作树内不存在**，如实标未解析，不声称上游缺失）。
5. `claims` 保持**空数组**：契约 `no_forced_claim_generation: true` 且本工序 objective 仅 `register_assets=true`，抽取属下游工序（理由已写进清单 `claims_empty_reason`）。

资产状态分布：

| kind / status | 数量 |
|---|---|
| `data_artifact_reference/unresolved` | 1 |
| `embedded_figure/metadata_only` | 2 |
| `figure_reference/unresolved` | 4 |
| `report_markdown/resolved` | 1 |
| `source_code_reference/unresolved` | 8 |
| `report_markdown/resolved` | 1 |
| **合计** | **16** |

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`POST /api/v1/auth/login`（`$TENSOR_AGENT_USER`）→ `GET /api/v1/tensor/reports/623`，取 `markdown` 原字段，落本地副本 `runs/wp-623-01/source_623.md`。本机 `psql -d tensorplatform -c "select markdown from tensor_reports where id=623"` 被拒（`permission denied for table tensor_reports`），故 **API 是唯一取源通道**（如实记录，不掩饰）。
2. **定身份**：对 `markdown` 的 UTF-8 字节做 sha256，与契约 `source_hash`、契约 `chars=7281` 双向比对；不等即 `SystemExit` 中止，不产出半成品清单。同时比对 `title` / `scenario_key`：`scenario_key` 逐字相同；`title` 在记录里用 U+2013 EN DASH（`10k–100k`）、契约用 ASCII 连字符（`10k-100k`），**做单字符 dash 归一后相同**——这一点如实标注，不当作逐字相同。
3. **扫描引用**（三条正则，全部只读原文、零猜测）：
   - markdown 图片 `![alt](path)` → `figure_reference`；
   - 反引号内容中"像路径"者（有目录段或已知工件后缀）→ 按扩展名归类（`.py`→源码、`.json`→数据工件、`.png`→图、`.md`→文档）；
   - 裸路径 + 可选 `../` 前缀（同上归类）。负向断言排除"路径的子串碎片"（如 `results-dem3d-` 被切成 `dem3d-`），首版踩到 1 例假阳性后修正。
4. **符号级引用**：反引号内的点分模块名（`tensordem.dem3d.IceDEM3D` 等）与 `**Upstream**` 行的 `m<编号>` 单独登记为 `module_reference` / `upstream_report_reference`，状态 `declared_only`——本工序不开 TensorDEM 仓，不声称这些入口存在。
5. **附件解析尝试**（结果写进清单，不猜）：`GET /tensor/reports/623/figures/<name>` 两图均 HTTP 404（`figure "not found"`）；`/tensor/reports/623/artifacts`、`/tensor/artifacts?report_id=623`、`/tensor/reports/623/figures`、`/tensor/reports/623/attachments` 均 HTTP 404。故图只能 `metadata_only`。
6. **解析范围**：工件只在**交付工作树**（TensorKnowledge）内查找；命中则记字节数 + sha256（`resolved`），未命中记 `unresolved` + 同 basename 命中列表（供后人定位），**绝不跨仓臆测存在性**。
7. **信封与自校验**：`kf_result.json` 的 `provenance.source_hash` 由**重新拉取的实时字节**重算，与清单声明不一致则拒绝产出；`verification.json` 用 `jsonschema` Draft 2020-12 校验 `schemas/kf_result.v1.schema.json`（平台下发 schema 的仓内副本，sha256 `170dba8b0b5d54012490aaadc0b68647a9520ecb869e9d03f873afb99b74c076`），并**再次**对实时 markdown 重解析全部 17 个定位点。
8. **关键设置**：纯标准库（urllib/hashlib/json/re）+ `jsonschema` 做 schema 门 + matplotlib 出图；脚本幂等，`all` 一条命令重建全部产物。

一键复跑（工作树根执行）：

```bash
python3 scripts/kf_wp62301_register_assets.py all && python3 scripts/kf_wp62301_render_report.py
```

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-623-01/asset_manifest.json` | 主产物：16 资产 + 3 符号引用 + 17 定位点 + provenance + 空 claims；27723 B，`sha256:9ad919d486844d675a40c67e208154c4f7396ef76b47c0196a9ee9306e94bd28` |
| `docs/kf/wp-623-01/kf_result.json` | 交付信封（package_id/task_type/report_id/provenance/outputs）：`outputs.asset_manifest.json` 内嵌同一清单，`source_hash` 实时重算绑定；31515 B，`sha256:c8b8443a20cad6c92adfbd81fa754b81895ad308d3af45a651febf37ecea25b5` |
| `docs/kf/wp-623-01/verification.json` | 自校验报告：6 项 acceptance 全 True（`all_ok: true`）；1268 B，`sha256:672889147a2db6b587d4756e060e60d6e91b4f12ee483852cb353a96a4f289dc` |
| `docs/kf/wp-623-01/figures/wp62301_source_locator_map.png` | 定位图：左=逐行字符数曲线 + 各类引用锚点行 + 章节线；右=资产 kind/status 直方图（207337 B） |
| `runs/wp-623-01/source_623.md` | 源 markdown 本地副本，`sha256:b513d521df6b393c365a587d49bc06f2482396a01228ed72f53d9e7132d86dcf` |
| `scripts/kf_wp62301_register_assets.py` | 可复跑构建器（build / envelope / verify / figure / all） |
| `scripts/kf_wp62301_render_report.py` | 报告渲染器（本报告全部数字由脚本注入，零手抄） |

## ④ 证据定位表（asset/字段 → 原文逐字引文）

定位方案：`source_field=markdown` 用 1 基行号，校验时 **`lines[line-1] == quote` 且 `quote in markdown` 且 `sha256(quote)` 与清单一致**；图元数据用 `source_field=record` 的 JSON pointer。下表由脚本从清单回读生成。

源身份（identity_facts，全文级锚点）：

| fact | 定位 | 原文逐字 |
|---|---|---|
| `title-line` | L1 | `# DEM3D Large-Scale Particle Benchmark: 10k–100k Wall-Clock Scaling Study` |
| `scenario-line` | L3 | `**Mission**: SIR-PC2\|V02 \| **ID**: m705 \| **Layer**: L2_validation` |
| `sec1-header` | L9 | `## 1. Case Introduction` |
| `audit-chain-header` | L141 | `## Audit Chain` |
| `closing-note` | L150 | `` |

资产 / 符号定位（引文=路径 token 或整行，均为原文逐字子串）：

| asset_id | kind | 解析状态 | 定位 | 原文引文（逐字） |
|---|---|---|---|---|
| `r623:source-markdown` | report_markdown | resolved | L1 | `整字段 sha256（151 行）；L1=# DEM3D Large-Scale Particle Benchmark: 10k–100k…` |
| `r623:figure:01` | embedded_figure | metadata_only | `figures` record | name=`dem3d_scale_benchmark` (record 只有 name/caption, 无字节) |
| `r623:figure:02` | embedded_figure | metadata_only | `figures` record | name=`dem3d_energy_drift` (record 只有 name/caption, 无字节) |
| `r623:ref:01` | source_code_reference | unresolved | L52 | `scripts/benchmark_dem3d_scale.py` |
| `r623:ref:02` | source_code_reference | unresolved | L53 | `scripts/plot_dem3d_scale_benchmark.py` |
| `r623:ref:03` | source_code_reference | unresolved | L53 | `scripts/plot_dem3d_energy_drift.py` |
| `r623:ref:04` | source_code_reference | unresolved | L54 | `tests/test_dem3d_scale_benchmark.py` |
| `r623:ref:05` | figure_reference | unresolved | L98 | `../artifacts/dem3d_scale_benchmark.png` |
| `r623:ref:06` | figure_reference | unresolved | L103 | `../artifacts/dem3d_energy_drift.png` |
| `r623:ref:07` | source_code_reference | unresolved | L144 | `src/tensordem/dem3d.py` |
| `r623:ref:08` | source_code_reference | unresolved | L144 | `src/tensordem/dem3d_energy.py` |
| `r623:ref:09` | source_code_reference | unresolved | L145 | `scripts/benchmark_dem3d_scale.py` |
| `r623:ref:10` | source_code_reference | unresolved | L146 | `tests/test_dem3d_scale_benchmark.py` |
| `r623:ref:11` | data_artifact_reference | unresolved | L147 | `results-dem3d-scale/scaling_report.json` |
| `r623:ref:12` | figure_reference | unresolved | L147 | `artifacts/dem3d_scale_benchmark.png` |
| `r623:ref:13` | figure_reference | unresolved | L147 | `artifacts/dem3d_energy_drift.png` |
| `r623:sym:01` | module_reference | declared_only | L51 | `tensordem.dem3d.IceDEM3D` |
| `r623:sym:02` | module_reference | declared_only | L51 | `tensordem.dem3d_energy.EnergyAuditedIceDEM3D` |
| `r623:sym:03` | upstream_report_reference | declared_only | L143 | `m670` |

图元数据（`source_field=record`）：`/figures/0/name` = `dem3d_scale_benchmark`，`/figures/1/name` = `dem3d_energy_drift`；两者 caption 见清单 `assets[].caption`。

## ⑤ 注意点与局限

1. **只登记，不判定**：无 claim 抽取、无报告类型分类、无 verified 标记；verification 由平台门独立重算，本工序的 `verification.json` 只是自检。
2. **13 个正文引用的工件（+ 2 图）全部 unresolved，这是"范围"而不是"结论"**：它们是 TensorDEM 侧产物（`src/tensordem/dem3d.py`、`scripts/benchmark_dem3d_scale.py`、`tests/test_dem3d_scale_benchmark.py`、`results-dem3d-scale/scaling_report.json`、`artifacts/*.png`），不在交付工作树内。清单显式写 `existence_asserted_by_worker: false`，避免被下游误读为"上游缺文件"。要判定这些工件真伪需 TensorDEM 仓的独立解析工序。
3. **两图无字节**：报告记录只给 name/caption，`GET .../figures/<name>`、`.../artifacts`、`.../attachments` 全 404，故只登记元数据，不给 sha256——不伪造哈希。
4. **title 的 dash 差异**：记录用 U+2013，契约用 ASCII `-`；已按单字符归一判定"相同"，并在清单里同时保留两串原文，供门自行裁量（若门要求逐字相等，此处会如实判为不一致）。
5. **哈希口径**：`markdown` 字符串的 UTF-8 字节；平台侧任何改动（含空白）都会让 `source_hash` 失配。本地副本与实时字节当前一致（7324 B）。
6. **本工序无量纲物理量**：不产生场量云图，也没有解析解/文献基线可比；因此图 = 文档结构/定位图（图 1），误差判定只对"恒等量"（哈希、字符数、定位解析率）给出，见⑥。这一条是数据性质决定的，不是漏做。
7. **未做的事**（如实列出）：未在 TensorDEM 仓复算报告里的 1.12× 缩放比与 0 能量漂移；未下载/校验两张 PNG 内容；未做报告类型分类（契约 `classify_report_type: false`）。

## ⑥ 自检（逐条对照 acceptance）

| 结果 | acceptance 项 | 证据 |
|---|---|---|
| ✅ PASS | valid_json | asset_manifest.json + kf_result.json parsed |
| ✅ PASS | schema_pass | kf_result.v1 schema: 0 errors |
| ✅ PASS | source_locator_resolvable | 17/17 markdown locators re-resolved (line + verbatim + quote_sha256) |
| ✅ PASS | source_hash_matches | live=sha256:b513d521df6b393c365a587d49bc06f2482396a01228ed72f53d9e7132d86dcf manifest=sha256:b513d521df6b393c365a587d49bc06f2482396a01228ed72f53d9e713 |
| ✅ PASS | no_duplicate_ids | 16 ids, duplicates=[] |
| ✅ PASS | all_claims_have_evidence_or_explicit_unresolved_status | 0 claims; empty-claims reason stated: True |

**误差判定**（本工序的"关键量"是恒等量，逐项给出）：

| 量 | 实测 | 基准/契约 | 误差 | 是否 < 3%？ |
|---|---|---|---|---|
| markdown sha256 (UTF-8) | `b513d521df6b393c…` | 契约 `source_hash`=b513d521df6b393c… | 0（逐字节相同） | **是** |
| markdown chars | 7281 | 契约 chars=7281 | 0% | **是** |
| markdown bytes / lines | 7324 B / 151 行 | 无契约基线 | n/a | 不适用（登记量，非误差量） |
| markdown 定位点可解析 | 17/17 | 全部可解析 | 0% | **是** |
| 源资产可解析 | 1/1 | 源 markdown 1/1 可解析 | 0% | **是** |
| 工件（非源）字节可解析 | 0/15 | 无基线（工件在 TensorDEM 仓；2 图仅元数据） | 不可判定 | 不适用（见⑤） |

回答：**是**——sha256、字符数、定位解析率三项均为精确比对，误差 0%（< 3%）；"工件可解析数"无基准可比（工件属 TensorDEM 仓），不做误差判定也不含糊其辞。

图 1（`figures/wp62301_source_locator_map.png`）：左图为 report 623 markdown 的逐行字符数曲线，竖线为每类正文引用在原文中的行号锚点，点线标出 H1/§1/§3/§5/Audit Chain 章节位置；右图为资产 kind/status 直方图。用途=让"登记了哪些、锚在哪一行、有多少解析不了"一眼可核，替代本工序不存在的物理场量云图。

## 附：结果 JSON（全文唯一 fenced json 代码块，与 `docs/kf/wp-623-01/kf_result.json` 逐字节相同）

```json
{
  "package_id": "wp-623-01",
  "task_type": "01-asset-registration",
  "report_id": "623",
  "provenance": {
    "source_hash": "sha256:b513d521df6b393c365a587d49bc06f2482396a01228ed72f53d9e7132d86dcf",
    "source_field": "markdown",
    "producer": "kf-worker/m15515",
    "emitted_at": "2026-11-12T00:52:47.243855+00:00",
    "notes": "hash recomputed from GET /api/v1/tensor/reports/623 markdown (UTF-8 bytes); matches contract source_hash sha256:b513d521df6b393c365a587d49bc06f2482396a01228ed72f53d9e7132d86dcf"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-623-01",
      "task_type": "01-asset-registration",
      "report_id": "623",
      "lane": "C",
      "generated_at": "2026-11-12T00:52:46.793963+00:00",
      "producer": "kf-worker/m15515",
      "source": {
        "report_id": "623",
        "source_uri": "tensor://reports/623",
        "source_field": "markdown",
        "source_hash": "sha256:b513d521df6b393c365a587d49bc06f2482396a01228ed72f53d9e7132d86dcf",
        "contract_source_hash": "sha256:b513d521df6b393c365a587d49bc06f2482396a01228ed72f53d9e7132d86dcf",
        "hash_algo": "sha256",
        "hash_match": true,
        "chars": 7281,
        "contract_chars": 7281,
        "chars_match_contract": true,
        "bytes": 7324,
        "lines": 151,
        "has_crlf": false,
        "has_trailing_newline": true,
        "line_counting": "logical lines = markdown.rstrip(chr(10)).split(chr(10)); 1-based",
        "fetched_via": "GET /api/v1/tensor/reports/623",
        "record_fields": {
          "title": "DEM3D Large-Scale Particle Benchmark: 10k-100k Wall-Clock Scaling Study",
          "scenario_key": "SIR-PC2|V02",
          "mission_id": 705,
          "status": "published",
          "created_at": "2026-10-31T04:56:19.855455+00:00",
          "tags": [
            "DEM",
            "scaling",
            "benchmark",
            "ice-navigation",
            "L2_validation"
          ],
          "contract_title": "DEM3D Large-Scale Particle Benchmark: 10k-100k Wall-Clock Scaling Study",
          "contract_scenario_key": "SIR-PC2|V02",
          "title_matches_contract": true,
          "scenario_matches_contract": true
        },
        "platform_attachment_probes": {
          "GET /tensor/reports/623/artifacts": "not_probed_here",
          "figure_probe": {
            "dem3d_scale_benchmark": {
              "http_status": 404,
              "bytes": 29
            },
            "dem3d_energy_drift": {
              "http_status": 404,
              "bytes": 29
            }
          }
        }
      },
      "assets": [
        {
          "asset_id": "r623:source-markdown",
          "kind": "report_markdown",
          "name": "report-623-markdown",
          "locator": {
            "source_field": "markdown",
            "line": 1
          },
          "source_uri": "tensor://reports/623",
          "media_type": "text/markdown",
          "bytes": 7324,
          "chars": 7281,
          "lines": 151,
          "sha256": "sha256:b513d521df6b393c365a587d49bc06f2482396a01228ed72f53d9e7132d86dcf",
          "hash_scope": "UTF-8 bytes of the markdown field as served by GET /api/v1/tensor/reports/623",
          "local_copy": "runs/wp-623-01/source_623.md",
          "resolution": {
            "status": "resolved",
            "scope": "platform_api",
            "via": "GET /tensor/reports/623"
          },
          "hash_matches_contract": true,
          "chars_matches_contract": true
        },
        {
          "asset_id": "r623:figure:01",
          "kind": "embedded_figure",
          "name": "dem3d_scale_benchmark",
          "caption": "Log-log plot of per-step wall-clock time vs. particle count. Measured scaling closely follows ideal O(N) linear scaling. 100k ratio vs ideal: 1.12x.",
          "locator": {
            "source_field": "record",
            "pointer": "/figures/0/name",
            "quote": "dem3d_scale_benchmark"
          },
          "resolution": {
            "status": "metadata_only",
            "scope": "platform_api",
            "via": "GET /tensor/reports/623/figures/dem3d_scale_benchmark",
            "http_status": 404,
            "reason": "record exposes name/caption only; no byte payload was returned, so no hash is claimed"
          }
        },
        {
          "asset_id": "r623:figure:02",
          "kind": "embedded_figure",
          "name": "dem3d_energy_drift",
          "caption": "Energy drift per step across all three scales. All cases show zero drift within machine precision.",
          "locator": {
            "source_field": "record",
            "pointer": "/figures/1/name",
            "quote": "dem3d_energy_drift"
          },
          "resolution": {
            "status": "metadata_only",
            "scope": "platform_api",
            "via": "GET /tensor/reports/623/figures/dem3d_energy_drift",
            "http_status": 404,
            "reason": "record exposes name/caption only; no byte payload was returned, so no hash is claimed"
          }
        },
        {
          "asset_id": "r623:ref:01",
          "kind": "source_code_reference",
          "name": "scripts/benchmark_dem3d_scale.py",
          "reference_form": "backticked_path",
          "locator": {
            "source_field": "markdown",
            "line": 52,
            "quote": "- **Benchmark script**: `scripts/benchmark_dem3d_scale.py`"
          },
          "quote_token": "scripts/benchmark_dem3d_scale.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r623:ref:02",
          "kind": "source_code_reference",
          "name": "scripts/plot_dem3d_scale_benchmark.py",
          "reference_form": "backticked_path",
          "locator": {
            "source_field": "markdown",
            "line": 53,
            "quote": "- **Visualization**: `scripts/plot_dem3d_scale_benchmark.py`, `scripts/plot_dem3d_energy_drift.py`"
          },
          "quote_token": "scripts/plot_dem3d_scale_benchmark.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r623:ref:03",
          "kind": "source_code_reference",
          "name": "scripts/plot_dem3d_energy_drift.py",
          "reference_form": "backticked_path",
          "locator": {
            "source_field": "markdown",
            "line": 53,
            "quote": "- **Visualization**: `scripts/plot_dem3d_scale_benchmark.py`, `scripts/plot_dem3d_energy_drift.py`"
          },
          "quote_token": "scripts/plot_dem3d_energy_drift.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r623:ref:04",
          "kind": "source_code_reference",
          "name": "tests/test_dem3d_scale_benchmark.py",
          "reference_form": "backticked_path",
          "locator": {
            "source_field": "markdown",
            "line": 54,
            "quote": "- **Tests**: `tests/test_dem3d_scale_benchmark.py` (7 acceptance tests)"
          },
          "quote_token": "tests/test_dem3d_scale_benchmark.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r623:ref:05",
          "kind": "figure_reference",
          "name": "../artifacts/dem3d_scale_benchmark.png",
          "reference_form": "markdown_image_link",
          "locator": {
            "source_field": "markdown",
            "line": 98,
            "quote": "![DEM3D Scale Benchmark](../artifacts/dem3d_scale_benchmark.png)"
          },
          "quote_token": "../artifacts/dem3d_scale_benchmark.png",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r623:ref:06",
          "kind": "figure_reference",
          "name": "../artifacts/dem3d_energy_drift.png",
          "reference_form": "markdown_image_link",
          "locator": {
            "source_field": "markdown",
            "line": 103,
            "quote": "![DEM3D Energy Drift](../artifacts/dem3d_energy_drift.png)"
          },
          "quote_token": "../artifacts/dem3d_energy_drift.png",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r623:ref:07",
          "kind": "source_code_reference",
          "name": "src/tensordem/dem3d.py",
          "reference_form": "backticked_path",
          "locator": {
            "source_field": "markdown",
            "line": 144,
            "quote": "- **Solver**: `src/tensordem/dem3d.py` (IceDEM3D), `src/tensordem/dem3d_energy.py` (EnergyAuditedIceDEM3D)"
          },
          "quote_token": "src/tensordem/dem3d.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r623:ref:08",
          "kind": "source_code_reference",
          "name": "src/tensordem/dem3d_energy.py",
          "reference_form": "backticked_path",
          "locator": {
            "source_field": "markdown",
            "line": 144,
            "quote": "- **Solver**: `src/tensordem/dem3d.py` (IceDEM3D), `src/tensordem/dem3d_energy.py` (EnergyAuditedIceDEM3D)"
          },
          "quote_token": "src/tensordem/dem3d_energy.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r623:ref:09",
          "kind": "source_code_reference",
          "name": "scripts/benchmark_dem3d_scale.py",
          "reference_form": "backticked_path",
          "locator": {
            "source_field": "markdown",
            "line": 145,
            "quote": "- **Benchmark**: `scripts/benchmark_dem3d_scale.py`"
          },
          "quote_token": "scripts/benchmark_dem3d_scale.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r623:ref:10",
          "kind": "source_code_reference",
          "name": "tests/test_dem3d_scale_benchmark.py",
          "reference_form": "backticked_path",
          "locator": {
            "source_field": "markdown",
            "line": 146,
            "quote": "- **Tests**: `tests/test_dem3d_scale_benchmark.py` (7/7 PASS)"
          },
          "quote_token": "tests/test_dem3d_scale_benchmark.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r623:ref:11",
          "kind": "data_artifact_reference",
          "name": "results-dem3d-scale/scaling_report.json",
          "reference_form": "backticked_path",
          "locator": {
            "source_field": "markdown",
            "line": 147,
            "quote": "- **Artifacts**: `results-dem3d-scale/scaling_report.json`, `artifacts/dem3d_scale_benchmark.png`, `artifacts/dem3d_energy_drift.png`"
          },
          "quote_token": "results-dem3d-scale/scaling_report.json",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r623:ref:12",
          "kind": "figure_reference",
          "name": "artifacts/dem3d_scale_benchmark.png",
          "reference_form": "backticked_path",
          "locator": {
            "source_field": "markdown",
            "line": 147,
            "quote": "- **Artifacts**: `results-dem3d-scale/scaling_report.json`, `artifacts/dem3d_scale_benchmark.png`, `artifacts/dem3d_energy_drift.png`"
          },
          "quote_token": "artifacts/dem3d_scale_benchmark.png",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r623:ref:13",
          "kind": "figure_reference",
          "name": "artifacts/dem3d_energy_drift.png",
          "reference_form": "backticked_path",
          "locator": {
            "source_field": "markdown",
            "line": 147,
            "quote": "- **Artifacts**: `results-dem3d-scale/scaling_report.json`, `artifacts/dem3d_scale_benchmark.png`, `artifacts/dem3d_energy_drift.png`"
          },
          "quote_token": "artifacts/dem3d_energy_drift.png",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        }
      ],
      "symbol_references": [
        {
          "symbol_id": "r623:sym:01",
          "kind": "module_reference",
          "token": "tensordem.dem3d.IceDEM3D",
          "locator": {
            "source_field": "markdown",
            "line": 51,
            "quote": "- **Solver**: `tensordem.dem3d.IceDEM3D` + `tensordem.dem3d_energy.EnergyAuditedIceDEM3D`"
          },
          "resolution": {
            "status": "declared_only",
            "reason": "named in the report prose; this工序 registers the reference, it does not open TensorDEM"
          },
          "existence_asserted_by_worker": false
        },
        {
          "symbol_id": "r623:sym:02",
          "kind": "module_reference",
          "token": "tensordem.dem3d_energy.EnergyAuditedIceDEM3D",
          "locator": {
            "source_field": "markdown",
            "line": 51,
            "quote": "- **Solver**: `tensordem.dem3d.IceDEM3D` + `tensordem.dem3d_energy.EnergyAuditedIceDEM3D`"
          },
          "resolution": {
            "status": "declared_only",
            "reason": "named in the report prose; this工序 registers the reference, it does not open TensorDEM"
          },
          "existence_asserted_by_worker": false
        },
        {
          "symbol_id": "r623:sym:03",
          "kind": "upstream_report_reference",
          "token": "m670",
          "locator": {
            "source_field": "markdown",
            "line": 143,
            "quote": "- **Upstream**: m670 (friction/rolling resistance model) — interface compatible"
          },
          "resolution": {
            "status": "declared_only",
            "reason": "named in the report prose; this工序 registers the reference, it does not open TensorDEM"
          },
          "existence_asserted_by_worker": false
        }
      ],
      "locators": [
        {
          "asset_id": "r623:source-markdown",
          "locator": {
            "source_field": "markdown",
            "line": 1
          },
          "quote_sha256": "sha256:6537d09ae4754eec2618a4f9256725f55ce35f3ccf9c9a91db145014113eb379",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "asset_id": "r623:ref:01",
          "locator": {
            "source_field": "markdown",
            "line": 52
          },
          "quote_sha256": "sha256:2d823ee79d0a72a81c74dcb4344d5407f47cbc128672aa493898c397d333812e",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "asset_id": "r623:ref:02",
          "locator": {
            "source_field": "markdown",
            "line": 53
          },
          "quote_sha256": "sha256:a5fe44df7911ea403ef85de11e4d1d919b3b314a6360244dbaf2130ce51b1764",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "asset_id": "r623:ref:03",
          "locator": {
            "source_field": "markdown",
            "line": 53
          },
          "quote_sha256": "sha256:a5fe44df7911ea403ef85de11e4d1d919b3b314a6360244dbaf2130ce51b1764",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "asset_id": "r623:ref:04",
          "locator": {
            "source_field": "markdown",
            "line": 54
          },
          "quote_sha256": "sha256:74d6ce40b0ae676bb807525f158ccb978c176ac9250bb789b2c9508064f45111",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "asset_id": "r623:ref:05",
          "locator": {
            "source_field": "markdown",
            "line": 98
          },
          "quote_sha256": "sha256:82a2771e0e8a809b9fc00d7d8258cd12fdfff73393e662e71a6582147ff6a67d",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "asset_id": "r623:ref:06",
          "locator": {
            "source_field": "markdown",
            "line": 103
          },
          "quote_sha256": "sha256:4f2d2c03d99fa7fc997c9acb1d8001f9b93e68a69b584670b0c5219cf0e413b0",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "asset_id": "r623:ref:07",
          "locator": {
            "source_field": "markdown",
            "line": 144
          },
          "quote_sha256": "sha256:bc30fc31045901322df7050cfd9ea5bc5266c686ef7c6c11dfada297b7e94596",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "asset_id": "r623:ref:08",
          "locator": {
            "source_field": "markdown",
            "line": 144
          },
          "quote_sha256": "sha256:bc30fc31045901322df7050cfd9ea5bc5266c686ef7c6c11dfada297b7e94596",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "asset_id": "r623:ref:09",
          "locator": {
            "source_field": "markdown",
            "line": 145
          },
          "quote_sha256": "sha256:af5ac5cb0b63aa748687c0157f66e1288ecd70c0278b18c4a25d6b7cf37c271b",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "asset_id": "r623:ref:10",
          "locator": {
            "source_field": "markdown",
            "line": 146
          },
          "quote_sha256": "sha256:a33deb42da0f17f393c523d652274f3c6f05762f45f3747b56b8a17dce8bb48f",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "asset_id": "r623:ref:11",
          "locator": {
            "source_field": "markdown",
            "line": 147
          },
          "quote_sha256": "sha256:70b5815c0012e4031c3ab832d0fd7d3fdb44facc3bef715d0da83079bba428aa",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "asset_id": "r623:ref:12",
          "locator": {
            "source_field": "markdown",
            "line": 147
          },
          "quote_sha256": "sha256:70b5815c0012e4031c3ab832d0fd7d3fdb44facc3bef715d0da83079bba428aa",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "asset_id": "r623:ref:13",
          "locator": {
            "source_field": "markdown",
            "line": 147
          },
          "quote_sha256": "sha256:70b5815c0012e4031c3ab832d0fd7d3fdb44facc3bef715d0da83079bba428aa",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "asset_id": "r623:sym:01",
          "locator": {
            "source_field": "markdown",
            "line": 51
          },
          "quote_sha256": "sha256:8dd3cfab5b0eee502e014ae1990daca4a4fdc42cc2c39932ebde23a7dd6f69d0",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "asset_id": "r623:sym:02",
          "locator": {
            "source_field": "markdown",
            "line": 51
          },
          "quote_sha256": "sha256:8dd3cfab5b0eee502e014ae1990daca4a4fdc42cc2c39932ebde23a7dd6f69d0",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "asset_id": "r623:sym:03",
          "locator": {
            "source_field": "markdown",
            "line": 143
          },
          "quote_sha256": "sha256:671f111c6072a965f6362bd066aa607cb73dd630014a2e1300f29d2f26903a9f",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        }
      ],
      "identity_facts": [
        {
          "fact_id": "title-line",
          "locator": {
            "source_field": "markdown",
            "line": 1
          },
          "quote": "# DEM3D Large-Scale Particle Benchmark: 10k–100k Wall-Clock Scaling Study",
          "quote_sha256": "sha256:6537d09ae4754eec2618a4f9256725f55ce35f3ccf9c9a91db145014113eb379",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1
        },
        {
          "fact_id": "scenario-line",
          "locator": {
            "source_field": "markdown",
            "line": 3
          },
          "quote": "**Mission**: SIR-PC2|V02 | **ID**: m705 | **Layer**: L2_validation  ",
          "quote_sha256": "sha256:40dbabdce718bdc90bc7497e50624cf2a9645e9671b5993567df1e41e801b6c0",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1
        },
        {
          "fact_id": "sec1-header",
          "locator": {
            "source_field": "markdown",
            "line": 9
          },
          "quote": "## 1. Case Introduction",
          "quote_sha256": "sha256:ac5670ab730f4d4e0a5515c3bec2d6230c3e1bc2df9006cfd06b12c985a4bd8f",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1
        },
        {
          "fact_id": "audit-chain-header",
          "locator": {
            "source_field": "markdown",
            "line": 141
          },
          "quote": "## Audit Chain",
          "quote_sha256": "sha256:a1324df931ce8a0175a1885d886f1dfd88b7ee84c952a1881c255df47523cf1e",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1
        },
        {
          "fact_id": "closing-note",
          "locator": {
            "source_field": "markdown",
            "line": 150
          },
          "quote": "",
          "quote_sha256": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 7282
        }
      ],
      "claims": [],
      "claims_empty_reason": "Contract wp-623-01 objective is register_assets=true / classify_report_type=false, and notes state 'claims 允许为空数组' plus constraints no_forced_claim_generation=true. This工序 registers asset identity only (report_id, markdown byte hash, declared attachments/artifacts); extraction is a downstream工序, so an empty claims array is the complete result, not an omission.",
      "counts": {
        "source_documents": 1,
        "figures_declared_in_record": 2,
        "figures_with_bytes": 0,
        "body_references": 13,
        "distinct_referenced_paths": 11,
        "assets_total": 16,
        "assets_resolved": 1,
        "assets_metadata_only": 2,
        "assets_unresolved": 13,
        "locators": 17,
        "locators_resolved": 17,
        "symbol_references": 3,
        "claims": 0,
        "kind_status_histogram": {
          "data_artifact_reference/unresolved": 1,
          "embedded_figure/metadata_only": 2,
          "figure_reference/unresolved": 4,
          "report_markdown/resolved": 1,
          "source_code_reference/unresolved": 8
        }
      },
      "id_integrity": {
        "ids_checked": 16,
        "duplicates": [],
        "unique": true
      },
      "unresolved": [
        {
          "asset_id": "r623:ref:01",
          "name": "scripts/benchmark_dem3d_scale.py",
          "reason": "path not present in delivery worktree TensorKnowledge"
        },
        {
          "asset_id": "r623:ref:02",
          "name": "scripts/plot_dem3d_scale_benchmark.py",
          "reason": "path not present in delivery worktree TensorKnowledge"
        },
        {
          "asset_id": "r623:ref:03",
          "name": "scripts/plot_dem3d_energy_drift.py",
          "reason": "path not present in delivery worktree TensorKnowledge"
        },
        {
          "asset_id": "r623:ref:04",
          "name": "tests/test_dem3d_scale_benchmark.py",
          "reason": "path not present in delivery worktree TensorKnowledge"
        },
        {
          "asset_id": "r623:ref:05",
          "name": "../artifacts/dem3d_scale_benchmark.png",
          "reason": "path not present in delivery worktree TensorKnowledge"
        },
        {
          "asset_id": "r623:ref:06",
          "name": "../artifacts/dem3d_energy_drift.png",
          "reason": "path not present in delivery worktree TensorKnowledge"
        },
        {
          "asset_id": "r623:ref:07",
          "name": "src/tensordem/dem3d.py",
          "reason": "path not present in delivery worktree TensorKnowledge"
        },
        {
          "asset_id": "r623:ref:08",
          "name": "src/tensordem/dem3d_energy.py",
          "reason": "path not present in delivery worktree TensorKnowledge"
        },
        {
          "asset_id": "r623:ref:09",
          "name": "scripts/benchmark_dem3d_scale.py",
          "reason": "path not present in delivery worktree TensorKnowledge"
        },
        {
          "asset_id": "r623:ref:10",
          "name": "tests/test_dem3d_scale_benchmark.py",
          "reason": "path not present in delivery worktree TensorKnowledge"
        },
        {
          "asset_id": "r623:ref:11",
          "name": "results-dem3d-scale/scaling_report.json",
          "reason": "path not present in delivery worktree TensorKnowledge"
        },
        {
          "asset_id": "r623:ref:12",
          "name": "artifacts/dem3d_scale_benchmark.png",
          "reason": "path not present in delivery worktree TensorKnowledge"
        },
        {
          "asset_id": "r623:ref:13",
          "name": "artifacts/dem3d_energy_drift.png",
          "reason": "path not present in delivery worktree TensorKnowledge"
        }
      ],
      "observations": [
        "Report markdown is complete and self-consistent: first line is the H1 title, sections 1-6 + Audit Chain all present (151 lines).",
        "The 2 figures are declared in the record metadata (name+caption) and referenced in-body as relative links ../artifacts/<name>.png; the platform serves no figure bytes for this report, so they stay metadata_only (no hash claimed).",
        "All body path references point at TensorDEM artefacts (src/tensordem/*.py, scripts/*, tests/*, results-dem3d-scale/*, artifacts/*.png) which do not exist in the TensorKnowledge delivery worktree; they are registered as declared references with existence_asserted_by_worker=false."
      ],
      "limitations": [
        "Registration only: no claim/evidence extraction, no report-type classification, no verified marks (verification is computed by the platform gate).",
        "source_hash scope = UTF-8 bytes of the markdown string returned by the platform API; any change to the stored markdown (even whitespace) invalidates it.",
        "Direct psql read of tensor_reports was denied (permission denied for table tensor_reports), so the API is the only source channel used.",
        "Reference resolution is limited to the delivery worktree; a missing path here is reported as unresolved, never as a broken upstream artefact."
      ]
    }
  },
  "claims": []
}
```
