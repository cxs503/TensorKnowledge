# KF-RESULT wp-12044-01

**报告（被登记源）**: report_id=12044 — 「probe figure upload (write_lease D1)」
**工作包**: `wp-12044-01` · task_type=`01-asset-registration` · lane=C · 契约版本 1.0
**工序目标**: `register_assets=true`、`classify_report_type=false`（只登记资产，不抽取知识）

## ① 本工序做了什么

对 report_id=12044 的唯一文档资产做**资产登记**：取平台 `GET /tensor/reports/12044` 的 `markdown`
字段原文字节，独立重算 sha256 并与契约 `source_hash` 比对（一致），随后在**该字节序列**上逐条解析
本报告可登记的资产定位（字符区间 + 行号 + 逐字引文），并对每条资产给出**机器校验过**的解析状态。
不做任何知识抽取，`claims` 为空数组（契约 notes 明示允许），也未对报告自述做真伪判定。

源报告本身是一条**探针记录**（title=`probe figure upload (write_lease D1)`，tags=`["probe"]`，
正文仅 57 字符一句），因此本清单只有 4 条资产：1 条整篇文档、1 条时间戳、1 条用途陈述、1 条图件声明。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`scripts/kf_wp12044_01_fetch.py` — `POST /auth/login`（凭据仅来自环境变量，不落盘）
   取 token，`GET /tensor/reports/12044`，把 `markdown` **按 UTF-8 原样字节**写入
   `docs/kf/wp-12044-01/source.md`（81 字节），同时保存整条 record 供 provenance 引用。
2. **校验哈希**：`hashlib.sha256(md.encode())` = `74cbbb52b6682ff4bb865490e1b4cce8511d023ed1a48afa19a9f2d22a0220b6`，
   与契约 `source_hash` 逐字一致（`docs/kf/wp-12044-01/sha256.txt` 记录 match=True）。
3. **定位资产**：`scripts/kf_wp12044_01_register.py` 内每条资产登记 `anchor`（逐字子串）与行偏移 `span`，
   由脚本换算成 `start_char/end_char/start_line/end_line/quote`；anchor 命中数 ≠1 或 quote 非唯一即**硬失败退出**
   （禁止手抄、禁止"差不多"）。校验结果逐条落 `docs/kf/wp-12044-01/locator_check.json`。
4. **解析状态机器校验**：文本类资产校验 `md[start:end] == quote` 且 `md.count(quote)`；
   图件资产走平台探测 `scripts/kf_wp12044_01_probe.py`（`/tensor/reports/12044/figures|assets|attachments` → 均为 **404**），
   并检查 `record.figures` 是否带 path/URL/摘要 → **不带**，故如实标 `referenced_unresolved`。
5. **结构校验**：结果信封用仓内 `schemas/kf_result.v1.schema.json`（draft 2020-12）经 `jsonschema.validate`
   实测通过，不是"看起来合规"。
6. **不改上游**：只读 report 12044，未写其它任何 report_id，未把任何结论标成 verified。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-12044-01/source.md` | 被登记 markdown 的原样字节副本（57 字符 / 81 字节） |
| `docs/kf/wp-12044-01/sha256.txt` | 本地重算 sha256 与契约值比对（match=True） |
| `docs/kf/wp-12044-01/report_12044.json` | 平台 record 原文（title/tags/mission_id/figures） |
| `docs/kf/wp-12044-01/platform_probe.json` | 图件/附件端点探测原始响应（3×404） |
| `docs/kf/wp-12044-01/locator_check.json` | 每条引文的 offset/行号/出现次数/span 一致性 |
| `docs/kf/wp-12044-01/asset_manifest.json` | 契约输出：4 条资产 + 计数 + integrity |
| `docs/kf/wp-12044-01/asset_manifest.json`（sha256） | 清单摘要 `64ee13249e12c403…` 落进结果信封与正文 json 块的 `artifact_sha256`，可离线核对 |
| `docs/kf/wp-12044-01/kf_result.json` | `kf_result.v1` 结果信封（schema 实测通过） |
| `docs/kf/wp-12044-01/report_body.md`、`docs/kf_result_wp-12044-01.md` | 本正文（含唯一一个 ```json 块） |
| `docs/kf/wp-12044-01/fig1_asset_spans.png` | 资产定位区间图（字符轴区间 + 解析状态着色），97539 字节，sha256 `e4c69f16a9017e47…`，由 `scripts/kf_wp12044_01_figure.py` 从 `asset_manifest.json` 程序化生成 |
| `scripts/kf_wp12044_01_fetch.py` / `_register.py` / `_verify.py` / `_probe.py` / `_publish.py` | 一键复跑链 |

资产表（每条引文均逐字来自正文）：

| id | class | quote（逐字） | 字符区间 | resolution |
|---|---|---|---|---|
| A01 | source_document | `probe 2026-11-10T17:22:47.930890Z — 探针：验证 figures 字段可落库。\n` | 整篇 | resolved_in_source |
| A02 | timestamp_token | `2026-11-10T17:22:47.930890Z` | 6–33 | resolved_in_source |
| A03 | intent_statement | `探针：验证 figures 字段可落库。` | 36–56 | resolved_in_source |
| A04 | figure_declaration | `figures 字段可落库` | 42–55 | referenced_unresolved |

计数：assets=4，resolved_in_source=3，
referenced_unresolved=1，declared_absent=0。

**结果图**:`docs/kf/wp-12044-01/fig1_asset_spans.png` —— 上格把 57 字符原文逐字符排在字符轴上（无 CJK 字体，中文按填充标记绘制，非乱码），下格把 4 条资产的逐字字符区间按解析状态着色。**为什么没有场量云图/对比曲线**:源报告是探针记录，正文不含任何场量、几何或数值结果，因此不存在可绘制的物理量；本图是本工序唯一可诚实产出的可视化（登记数据的结构图），不冒充计算结果。

## ④ 证据定位表（claim/字段 → 原文引文片段）

| 字段 | 值 | 原文引文（逐字） | 定位 |
|---|---|---|---|
| source.hash | `74cbbb52b6682ff4bb865490e1b4cce8511d023ed1a48afa19a9f2d22a0220b6` | 整篇正文 `probe 2026-11-10T17:22:47.930890Z — 探针：验证 figures 字段可落库。` | 整篇 0–57 |
| A02 时间戳 | `2026-11-10T17:22:47.930890Z` | `2026-11-10T17:22:47.930890Z` | char 6–33（唯一） |
| A03 用途陈述 | 探针验证 figures 字段落库 | `探针：验证 figures 字段可落库。` | char 36–56（唯一） |
| A04 图件 | `fig1_d1_linearizability.png`（caption=`probe`） | 正文仅 `figures 字段可落库`；文件名不在正文 | record.figures[0]；`/figures` 端点 404 |

零手抄声明：上表每个字符串均由脚本从 `source.md` **切片生成**（`md[start:end]`），
不是人工录入；重放 `python3 scripts/kf_wp12044_01_verify.py` 可逐条复核。

## ⑤ 注意点与局限

- **源报告是探针产物，不是科研结论**：正文仅一句"验证 figures 字段可落库"，无几何、无算例、无数值。
  本清单因此**没有参数/表格/结果资产**——这是如实反映，不是漏登。
- **图件不可解析（unresolved，不是 absent）**：`record.figures` 只带 `name`+`caption`，无 path/URL/sha256，
  且 `/tensor/reports/12044/figures` 返回 404。若下游需要图件本体，须由写租约方补齐可解析地址，本工序不得臆造。
- **`scenario_key` 为空（null）**：平台 record 未设置场景键；本工序按契约 `classify_report_type=false`
  不去猜场景，原样记录在 `source.scenario_key`。
- **quote 唯一性与字符精度**：定位按**字符**而非按行（源报告只有一行，按行会把 A02/A03/A04 的引文都撑成整篇）；
  4 条 quote 的 `md.count(quote)` 均为 1，且 `md[start:end] == quote` 逐条成立（见 `locator_check.json`）。
  A04 的引文 `figures 字段可落库` 落在 A03 引文内部——这是正文里唯一的图件指向，故 A04 借它定位，
  但解析状态仍是 unresolved（指向存在 ≠ 图件本体可解析）。
- **未做的事**：不做 claim 抽取、不做报告类型分类、不判定探针陈述真伪、不标 verified（由平台门计算）。
- **哈希一致 ≠ 内容可信**：`source_hash` 相等是机械同一性校验，只证明"登记的就是平台上那一份字节"。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| valid_json | ✅ | 全部产物以 `json.dumps` 写出；`verify` 步骤逐文件 `json.load` 通过 |
| schema_pass | ✅ | `kf_result.json` 经 `jsonschema.validate` 对 `schemas/kf_result.v1.schema.json` 通过 |
| source_locator_resolvable | ✅ | 4/4 资产 quote 唯一且 `md[start:end]==quote`（`locator_check.json`） |
| source_hash_matches | ✅ | `74cbbb52b6682ff4bb865490e1b4cce8511d023ed1a48afa19a9f2d22a0220b6` == 契约 `sha256:74cbbb52…0220b6` |
| no_duplicate_ids | ✅ | A01–A04 无重复；builder 内置重复即硬失败 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | `claims=[]`（契约允许）；A04 显式 `referenced_unresolved` |
| 边界：不改其它 report_id / 不标 verified | ✅ | 只读 12044；`verification_status=not_verified` |

无失败项（honest-FAIL 无需申报）；唯一"缺口"是 A04 图件本体的不可解析性，已显式标 unresolved 而非掩盖。

## 一键复跑

```bash
cd <worktree> && python3 scripts/kf_wp12044_01_fetch.py \
  && python3 scripts/kf_wp12044_01_probe.py \
  && python3 scripts/kf_wp12044_01_register.py \
  && python3 scripts/kf_wp12044_01_verify.py
```

## 结果信封（唯一一个 json 块）

```json
{
  "package_id": "wp-12044-01",
  "task_type": "01-asset-registration",
  "report_id": "12044",
  "provenance": {
    "source_hash": "sha256:74cbbb52b6682ff4bb865490e1b4cce8511d023ed1a48afa19a9f2d22a0220b6",
    "source_field": "markdown",
    "producer": "agent/m15737",
    "emitted_at": "2026-11-12T02:25:17Z",
    "notes": "source_uri=tensor://reports/12044; contract_version=1.0; lane=C; chars=57; bytes_utf8=81; title=probe figure upload (write_lease D1); asset_manifest_sha256=64ee13249e12c403eae71d92559ef2a08cabf2f4dda05ce26369e77c51b9a738; verification_status=not_verified (platform gate computes verification)"
  },
  "outputs": {
    "asset_manifest.json": {
      "artifact_path": "docs/kf/wp-12044-01/asset_manifest.json",
      "artifact_sha256": "64ee13249e12c403eae71d92559ef2a08cabf2f4dda05ce26369e77c51b9a738",
      "artifact_bytes": 5391,
      "schema": "asset_manifest.v1",
      "package_id": "wp-12044-01",
      "task_type": "01-asset-registration",
      "report_id": "12044",
      "source": {
        "uri": "tensor://reports/12044",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "74cbbb52b6682ff4bb865490e1b4cce8511d023ed1a48afa19a9f2d22a0220b6",
        "chars": 57,
        "bytes_utf8": 81,
        "title": "probe figure upload (write_lease D1)",
        "scenario_key": null,
        "platform_id": 12044,
        "platform_mission_id": 10115,
        "platform_tags": [
          "probe"
        ],
        "platform_figures": [
          {
            "name": "fig1_d1_linearizability.png",
            "caption": "probe"
          }
        ],
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/12044",
        "local_copy": "docs/kf/wp-12044-01/source.md"
      },
      "counts": {
        "assets": 4,
        "by_class": {
          "source_document": 1,
          "timestamp_token": 1,
          "intent_statement": 1,
          "figure_declaration": 1
        },
        "by_resolution": {
          "resolved_in_source": 3,
          "referenced_unresolved": 1
        },
        "resolved_in_source": 3,
        "referenced_unresolved": 1,
        "declared_absent": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "source_document",
          "label": "报告 markdown 正文（整篇，57 字符 / 81 字节 UTF-8，单行 + 换行）",
          "in_report_section": "(document)",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 57,
            "start_line": 0,
            "end_line": 1,
            "quote": "probe 2026-11-10T17:22:47.930890Z — 探针：验证 figures 字段可落库。\n",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim_substring_of_source_markdown",
            "result": "resolved",
            "occurrences": 1,
            "char_span_matches_quote": true
          },
          "note": "sha256 与契约 source_hash 一致（见 source.hash）；正文仅一句探针声明，无表格/公式/数值结果，故本清单不含表、参数或结果资产。"
        },
        {
          "asset_id": "A02",
          "asset_class": "timestamp_token",
          "label": "探针写入时间戳 2026-11-10T17:22:47.930890Z",
          "in_report_section": "(document)",
          "locator": {
            "method": "char_span",
            "start_char": 6,
            "end_char": 33,
            "start_line": 0,
            "end_line": 0,
            "quote": "2026-11-10T17:22:47.930890Z",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim_substring_of_source_markdown",
            "result": "resolved",
            "occurrences": 1,
            "char_span_matches_quote": true
          },
          "note": "ISO-8601 UTC 微秒级时刻，逐字取自正文；用于核验写租约 D1 的落库时刻。"
        },
        {
          "asset_id": "A03",
          "asset_class": "intent_statement",
          "label": "报告自述用途：探针验证 figures 字段可落库",
          "in_report_section": "(document)",
          "locator": {
            "method": "char_span",
            "start_char": 36,
            "end_char": 56,
            "start_line": 0,
            "end_line": 0,
            "quote": "探针：验证 figures 字段可落库。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim_substring_of_source_markdown",
            "result": "resolved",
            "occurrences": 1,
            "char_span_matches_quote": true
          },
          "note": "报告唯一实质性陈述；本工序只登记其位置，不判定该陈述真伪（不做 claim 抽取）。"
        },
        {
          "asset_id": "A04",
          "asset_class": "figure_declaration",
          "label": "图件声明 fig1_d1_linearizability.png（caption=probe，record.figures[0]）",
          "in_report_section": "(document)",
          "locator": {
            "method": "char_span",
            "start_char": 42,
            "end_char": 55,
            "start_line": 0,
            "end_line": 0,
            "quote": "figures 字段可落库",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "figure_bytes_or_path_resolvable",
            "result": "unresolved",
            "platform_figures_count": 1,
            "figure_name": "fig1_d1_linearizability.png",
            "figure_caption": "probe",
            "figure_has_url_or_path": false,
            "figures_endpoint_status": 404,
            "detail": "record.figures carries name+caption only (no path/URL/digest); GET /tensor/reports/12044/figures -> 404, so the binary cannot be resolved from the platform; the markdown names no figure file."
          },
          "note": "图件文件名/caption 只存在于平台 record.figures，正文未给出文件名、路径、URL 或摘要；figures 端点 404，二进制不可解析——如实标 unresolved，不臆造地址。"
        }
      ],
      "claims": [],
      "claims_note": "契约 objective.classify_report_type=false、notes 允许 claims 为空数组：本工序只做资产登记，不做知识抽取，也未对 A03 的陈述做真伪判定（no_forced_claim_generation）。",
      "integrity": {
        "quote_uniqueness": "每条 locator.quote 均在 source.md 中唯一出现，且 md[start:end] 逐字等于 quote（scripts/kf_wp12044_01_verify.py 复核）",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true
      }
    }
  },
  "claims": []
}
```
