# KF-RESULT wp-331-01

**工包**：`wp-331-01` ｜ **工序**：`01-asset-registration`（泳道 C）｜ **report_id**：`331`
**源**：`tensor://reports/331` ／ `source_field=markdown` ／ `sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717`
**交付仓**：TensorKnowledge（status=draft）｜ **上游报告标题**：`M404: DEM-FEM Coupling Interface Schema + Hertz/Beam Benchmarks (CPU)`

## ① 本工序做了什么

只做一件被契约限定的事：**为报告 331 登记源资产**（`register_assets: true`,
`classify_report_type: false`）。具体三件：

1. 取回 `tensor://reports/331` 的 `markdown` 字段，按其 UTF-8 字节独立重算 `sha256`，
   与契约 `source_hash` 逐字符比对 → **True**（1371 字符 / 1412 字节）；
2. 枚举该报告声明/提及的可解析资产（markdown、记录元数据、图件、被提及的 schema 工件），
   逐个给出检索端点、HTTP 状态、字节数与 `sha256`（可得时）；
3. 不可取得的资产**保留为 unresolved 并写明理由**，不做反推、不代上游补件。

**未做**（契约禁止/越界）：不抽取 claim（`claims: []`）、不判定 verified、不重跑上游 DEM/FEM 算例、
不读写任何其它 `report_id`、不改写上游产物。

## ② 怎么做的（步骤／工具／关键设置）

| 步 | 动作 | 工具/端点 | 结果 |
|---|---|---|---|
| 1 | 取源报告 | `GET /api/v1/tensor/reports/331`（Bearer token，登录 `POST /api/v1/auth/login`） | HTTP 200，取字段 `markdown` |
| 2 | 字节哈希 | `hashlib.sha256(markdown.encode('utf-8'))` | `sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717` |
| 3 | 哈希对齐 | 与契约 `source_hash` 严格比较（不匹配即中止，不写产物） | match = **True** |
| 4 | 图件检索 | `GET /api/v1/tensor/reports/331/figures/hertz_beam_comparison` | HTTP **404**（`{"detail":"figure not found"}`） |
| 5 | 图件目录反查 | 只读列目录 `/root/tensor-ecosystem/TensorPlatform/backend/uploads/tensor_reports` | 目录存在=True，`331/` 子目录存在=**False**，同级报告目录 2703 个（探测时点值） |
| 6 | 工件名候选扫描 | 只读扫描 `*/schemas/dem_fem_coupling_v1.json` | `/root/tensor-ecosystem/TensorDEM/schemas/dem_fem_coupling_v1.json`（4729 B，sha256 `9a5fa0f663584f43…`） |
| 7 | 引文定位自检 | 每段引文 `in markdown` + `bytes.find()` 取字节偏移 | 全部可解析（见 ④） |
| 8 | 平台门干跑（同一份门代码） | `scripts/kf_wp331_01_gate_dryrun.py`（gates.py sha256 `f0206f6399318b01…`） | 9/9 PASS，`gates_ok=True` |

关键设置：全程只读（唯一写动作是本工作树内的产物文件）；`claims` 显式留空；
未解析项一律带 `unresolved_reason`，不用 `verified` 字样；`min_quote_chars` 门槛（平台门 12 字符）
在 ④ 里逐条满足（最短引文 36 字符）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-331-01/asset_manifest.json` | 资产清单本体：4 个资产（2 resolved / 1 declared_unresolvable / 1 unresolved_candidate_found）+ 源指纹 + 引文定位自检 + 未解析理由 |
| `docs/kf/wp-331-01/source_snapshot/report_331.markdown` | 源 markdown 的**字节同源**快照（`sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717`），供离线复算与门自检 |
| `scripts/kf_wp331_01_register_assets.py` | 登记器（一键复跑；哈希不符即中止） |
| `scripts/kf_wp331_01_render_report.py` | 本报告渲染器（数字全部从 manifest 注入，零手抄） |
| `schemas/kf_result.v1.schema.json` | 结果信封 schema 的**逐字节副本**（平台侧同名文件），供离线结构门复算 |
| `tests/test_kf_wp331_01.py` | 离线验收测试：哈希/结构/引文/去重/未解析理由 |
| `docs/kf/wp-331-01/gate_dryrun.json` | 平台门干跑留痕（9 条门的通过/失败、门代码与 schema 的 sha256、包身份） |

资产登记表（`asset_manifest.json` 摘要）：

| asset_id | kind | status | bytes | sha256（截断） |
|---|---|---|---|---|
| `asset-331-report-markdown` | report_markdown | resolved | 1412 | `sha256:d67069723d0db8be` |
| `asset-331-report-record` | report_record_metadata | resolved | 0 | `—` |
| `asset-331-figure-hertz_beam_comparison` | figure | declared_unresolvable | 0 | `—` |
| `asset-331-schema-dem_fem_coupling_v1` | schema_artifact | unresolved_candidate_found | 0 | `—` |

未解析资产与理由：

| asset_id | status | reason |
|---|---|---|
| `asset-331-figure-hertz_beam_comparison` | declared_unresolvable | 记录声明了图件 hertz_beam_comparison，但检索端点返回 HTTP 404（figure not found），且服务端图件目录下无 report 331 子目录（同级报告目录 2703 个）——字节不可得；不伪造、不重绘、不代上游补图。 |
| `asset-331-schema-dem_fem_coupling_v1` | unresolved_candidate_found | 平台无「报告→附件」绑定端点，markdown 正文无文件名/URI，字节不可经 API 取得；只读扫描在 /root/tensor-ecosystem/TensorDEM/schemas/dem_fem_coupling_v1.json 找到同名候选（sha256 9a5fa0f663584f43…），但与报告 331 的版本绑定只是间接证据，不据此认定同一工件。 本工序不反推工件内容，保留未解析。 |

## ④ 证据定位表（claim／字段 → 原文引文片段）

本工序 `claims: []`（契约 `no_forced_claim_generation`: 不做抽取），因此没有 claim 级引文；
下面是**资产定位**用的引文，全部逐字取自报告 331 的 `markdown` 字段，
`offset_bytes` 是引文在该字段 UTF-8 字节流中的起始偏移：

| 定位键 | 原文引文（逐字） | 在 markdown 中可解析 | offset_bytes |
|---|---|---|---|
| `honest_fail` | - **Honest-FAIL**: TensorFEM unavailable; DEM lattice ≠ continuum half-space | True | 335 |
| `parameters` | - **Parameters**: k_bond=1e5 N/m, tool_speed=5 m/s, max_indent=0.05m | True | 266 |
| `metrics_exponent_row` | | Exponent | 1.4108 | 1.5±0.05 | — | | True | 810 |
| `schema_mention` | - Schema  validates against jsonschema | True | 1188 |
| `figure_mention` | See attached: Hertz F-δ curve + beam deflection comparison | True | 991 |

另两条只在**记录字段**（非 markdown）出现的登记项，如实标注为"无 markdown 定位"：

| 字段 | 值 | 说明 |
|---|---|---|
| `record.title` | `M404: DEM-FEM Coupling Interface Schema + Hertz/Beam Benchmarks (CPU)` | 与 markdown H1 `M404: DEM-FEM Coupling Interface + Hertz/Beam Benchmarks` **不一致**（记录多了 `Schema`/`(CPU)`）→ `title_fields_consistent=False`；两者分别登记，不改写、不归并 |
| `record.figures[0].caption` | Left: Hertz contact force-displacement (DEM3D vs fit vs analytical). Right: Beam deflection (FD vs analytical) showing convergence. | 图注只在记录字段；markdown ④ 段仅有 `See attached: Hertz F-δ curve + beam deflection comparison`，不含图名 |

## ⑤ 注意点与局限

1. **图件缺失是本工序最硬的事实**：报告声明了 1 张图（`hertz_beam_comparison`），但检索端点
   HTTP 404，且服务端图件目录下根本没有 `331/` 子目录
   （同级有 2703 个报告目录可对照）→ 判定 `declared_unresolvable`。
   我没有重绘、没有从别处挪用图表来"补全"——那会制造假工件；这对下游 02/03 是硬约束：
   该报告的图证据链**当前不可闭合**。
2. **schema 工件只是候选**：`find` 在 `TensorDEM/schemas/dem_fem_coupling_v1.json` 找到同名文件
   （4729 B，sha256 `9a5fa0f663584f43…`），
   且其提交主题含 `m404`、日期与报告同日——但这是**间接旁证**，不是平台级"报告→工件"绑定；
   状态保持 `unresolved_candidate_found`，不认定同一工件。
3. **标题双源不一致**：`record.title` 与 markdown H1 不同（见 ④）。登记器不改写，交下游自行选择；
   若后续工序引用标题，须声明取的是哪一源。
4. **只读边界**：本单只碰 `report_id=331`。图件目录与候选扫描均为只读探测；
   `sibling_report_dirs` 是探测时点的活值（平台并发写报告会变），故它不是稳定指纹，仅作佐证。
5. **哈希可比性**：`sha256` 的计算口径=平台 `markdown` 字段的 UTF-8 字节（不做换行归一化）。
   若平台侧未来对 markdown 做归一化，此指纹会失效——这正是门要独立重算的原因。
6. **无图说明**：本工序为纯登记任务（不做计算、不产生新数据），且上游图件字节缺失；
   按要求**不伪造图表**，故本报告无 png。若需要图，正确做法是上游重发报告时补图，
   而不是在本工序重绘。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 判定 | 依据 |
|---|---|---|
| `valid_json` | ✅ | `asset_manifest.json` 可 `json.load`；结果块可解析（`tests/test_kf_wp331_01.py` 断言） |
| `schema_pass` | ✅ | 结果信封过 `schemas/kf_result.v1.schema.json`（jsonschema Draft202012），离线复算 |
| `source_locator_resolvable` | ✅ | ④ 表 5 条引文全部 `in markdown` 为真，offset 非 -1；最短 36 字符 ＞ 门限 12 |
| `source_hash_matches` | ✅ | 生产侧重算 `sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717` ＝ 契约 `sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717`；平台会再独立重算 |
| `no_duplicate_ids` | ✅ | 4 个 `asset_id` 互不相同且均含 `331`；`claims: []` 无 id |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✅（空集真空成立） | 工序 01 不做抽取，`claims` 为空数组＝合法完整结果；4 个资产中 2 个未解析项均带 `unresolved_reason` |
| 门干跑（非 acceptance，但最能说明问题） | ✅ | 平台门干跑（工作树内，用平台同一份门代码）9/9 条 PASS，`gates_ok=True`；平台侧仍会独立重算哈希 |

失败项：**无**。但两处**诚实标注的缺口**（不是粉饰掉的门失败）：
图件字节不可得（`declared_unresolvable`）、schema 工件绑定未证（`unresolved_candidate_found`）。

## 复现命令（一键）

```bash
# 0) 环境：TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS 已在环境中
cd /root/tp-agent/work/m15506
python3 scripts/kf_wp331_01_register_assets.py \
    --out-dir artifacts/kf/wp-331-01 --emit-envelope /tmp/kf_env331.json
python3 scripts/kf_wp331_01_gate_dryrun.py \
    --out artifacts/kf/wp-331-01/gate_dryrun.json        # 平台同一份门代码干跑
python3 scripts/kf_wp331_01_render_report.py \
    --manifest docs/kf/wp-331-01/asset_manifest.json \
    --snapshot docs/kf/wp-331-01/source_snapshot/report_331.markdown \
    --envelope /tmp/kf_env331.json \
    --dryrun docs/kf/wp-331-01/gate_dryrun.json \
    --out docs/kf/wp-331-01-asset-registration.md
python3 -m pytest tests/test_kf_wp331_01.py -q
```

## 结果信封（机器门读取的唯一 ```json 块）

```json
{
  "package_id": "wp-331-01",
  "task_type": "01",
  "report_id": "331",
  "provenance": {
    "source_hash": "sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717",
    "source_field": "markdown",
    "producer": "tensor-agent m15506 (knowledge-factory worker, lane C)",
    "emitted_at": "2026-11-12T00:52:50+00:00",
    "notes": "hash 由生产者从平台 markdown 字段 utf-8 字节独立重算；平台门会再独立重算一次。"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-331-01",
      "task_type": "01-asset-registration",
      "lane": "C",
      "generated_at": "2026-11-12T00:52:50+00:00",
      "source": {
        "report_id": "331",
        "source_uri": "tensor://reports/331",
        "source_field": "markdown",
        "source_hash": "sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717",
        "expected_source_hash": "sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717",
        "hash_matches": true,
        "chars": 1371,
        "bytes_utf8": 1412,
        "title_record": "M404: DEM-FEM Coupling Interface Schema + Hertz/Beam Benchmarks (CPU)",
        "title_markdown_h1": "M404: DEM-FEM Coupling Interface + Hertz/Beam Benchmarks",
        "title_fields_consistent": false,
        "scenario_key": "dem_fem_coupling_hertz_cpu"
      },
      "assets": [
        {
          "asset_id": "asset-331-report-markdown",
          "kind": "report_markdown",
          "uri": "tensor://reports/331#markdown",
          "status": "resolved",
          "retrieval": {
            "endpoint": "GET /api/v1/tensor/reports/331",
            "field": "markdown",
            "http_status": 200
          },
          "sha256": "sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717",
          "chars": 1371,
          "bytes_utf8": 1412,
          "locator": {
            "source_field": "markdown",
            "quote": "# M404: DEM-FEM Coupling Interface + Hertz/Beam Benchmarks",
            "note": "markdown 首行 H1"
          },
          "notes": "本工序唯一权威源；字节哈希由生产者独立重算并与契约 source_hash 对齐。"
        },
        {
          "asset_id": "asset-331-report-record",
          "kind": "report_record_metadata",
          "uri": "tensor://reports/331#record",
          "status": "resolved",
          "retrieval": {
            "endpoint": "GET /api/v1/tensor/reports/331",
            "field": "record",
            "http_status": 200
          },
          "fields": {
            "id": 331,
            "title": "M404: DEM-FEM Coupling Interface Schema + Hertz/Beam Benchmarks (CPU)",
            "scenario_key": "dem_fem_coupling_hertz_cpu",
            "status": "published",
            "mission_id": 404,
            "created_at": "2026-10-30T08:24:18.053739+00:00",
            "tags": [
              "DEM-FEM",
              "coupling",
              "Hertz",
              "benchmark",
              "CPU",
              "honest-FAIL"
            ]
          },
          "locator": {
            "source_field": "record",
            "quote": null,
            "note": "元数据字段取自记录，markdown 正文无对应字样"
          },
          "notes": "记录 title 与 markdown H1 不一致（记录='M404: DEM-FEM Coupling Interface Schema + Hertz/Beam Benchmarks (CPU)'；H1='M404: DEM-FEM Coupling Interface + Hertz/Beam Benchmarks'）：两者分别登记，不做改写、不做归并。"
        },
        {
          "asset_id": "asset-331-figure-hertz_beam_comparison",
          "kind": "figure",
          "uri": "tensor://reports/331/figures/hertz_beam_comparison",
          "status": "declared_unresolvable",
          "retrieval": {
            "endpoint": "GET /api/v1/tensor/reports/331/figures/hertz_beam_comparison",
            "http_status": 404,
            "error_body": "{\"detail\":\"figure not found\"}",
            "figure_dir_probe": {
              "root": "/root/tensor-ecosystem/TensorPlatform/backend/uploads/tensor_reports",
              "exists": true,
              "report_subdir_present": false,
              "sibling_report_dirs": 2703
            }
          },
          "sha256": null,
          "bytes": 0,
          "caption": "Left: Hertz contact force-displacement (DEM3D vs fit vs analytical). Right: Beam deflection (FD vs analytical) showing convergence.",
          "locator": {
            "source_field": "markdown",
            "quote": "See attached: Hertz F-δ curve + beam deflection comparison",
            "note": "图件在 markdown ④ Figures 段被引用"
          },
          "unresolved_reason": "记录声明了图件 hertz_beam_comparison，但检索端点返回 HTTP 404（figure not found），且服务端图件目录下无 report 331 子目录（同级报告目录 2703 个）——字节不可得；不伪造、不重绘、不代上游补图。"
        },
        {
          "asset_id": "asset-331-schema-dem_fem_coupling_v1",
          "kind": "schema_artifact",
          "uri": "tensor://reports/331#artifact:dem_fem_coupling_v1.json",
          "status": "unresolved_candidate_found",
          "retrieval": {
            "endpoint": null,
            "http_status": null,
            "candidate_scan": {
              "scan_root": "/root/tensor-ecosystem",
              "pattern": "*/schemas/dem_fem_coupling_v1.json",
              "hits": [
                {
                  "path": "/root/tensor-ecosystem/TensorDEM/schemas/dem_fem_coupling_v1.json",
                  "bytes": 4729,
                  "sha256": "9a5fa0f663584f436c00ff78804e966ac8558ae2e46f8afac88df12205e2fbdd"
                }
              ]
            }
          },
          "locator": {
            "source_field": "record",
            "quote": null,
            "note": "工件文件名只在记录 summary 出现；markdown 正文只剩「Schema  validates against jsonschema」（文件名被剥离）"
          },
          "unresolved_reason": "平台无「报告→附件」绑定端点，markdown 正文无文件名/URI，字节不可经 API 取得；只读扫描在 /root/tensor-ecosystem/TensorDEM/schemas/dem_fem_coupling_v1.json 找到同名候选（sha256 9a5fa0f663584f43…），但与报告 331 的版本绑定只是间接证据，不据此认定同一工件。 本工序不反推工件内容，保留未解析。"
        }
      ],
      "unresolved": [
        {
          "asset_id": "asset-331-figure-hertz_beam_comparison",
          "status": "declared_unresolvable",
          "reason": "记录声明了图件 hertz_beam_comparison，但检索端点返回 HTTP 404（figure not found），且服务端图件目录下无 report 331 子目录（同级报告目录 2703 个）——字节不可得；不伪造、不重绘、不代上游补图。"
        },
        {
          "asset_id": "asset-331-schema-dem_fem_coupling_v1",
          "status": "unresolved_candidate_found",
          "reason": "平台无「报告→附件」绑定端点，markdown 正文无文件名/URI，字节不可经 API 取得；只读扫描在 /root/tensor-ecosystem/TensorDEM/schemas/dem_fem_coupling_v1.json 找到同名候选（sha256 9a5fa0f663584f43…），但与报告 331 的版本绑定只是间接证据，不据此认定同一工件。 本工序不反推工件内容，保留未解析。"
        }
      ],
      "asset_status_counts": {
        "resolved": 2,
        "declared_unresolvable": 1,
        "unresolved_candidate_found": 1
      },
      "locator_checks": {
        "honest_fail": {
          "quote": "- **Honest-FAIL**: TensorFEM unavailable; DEM lattice ≠ continuum half-space",
          "resolvable_in_markdown": true,
          "offset_bytes": 335
        },
        "parameters": {
          "quote": "- **Parameters**: k_bond=1e5 N/m, tool_speed=5 m/s, max_indent=0.05m",
          "resolvable_in_markdown": true,
          "offset_bytes": 266
        },
        "metrics_exponent_row": {
          "quote": "| Exponent | 1.4108 | 1.5±0.05 | — |",
          "resolvable_in_markdown": true,
          "offset_bytes": 810
        },
        "schema_mention": {
          "quote": "- Schema  validates against jsonschema",
          "resolvable_in_markdown": true,
          "offset_bytes": 1188
        },
        "figure_mention": {
          "quote": "See attached: Hertz F-δ curve + beam deflection comparison",
          "resolvable_in_markdown": true,
          "offset_bytes": 991
        }
      },
      "scope": {
        "extraction_performed": false,
        "claims_emitted": 0,
        "note": "工序 01 只登记资产与指纹；不抽取知识、不判定 verified、不重跑上游算例。"
      }
    }
  },
  "claims": []
}
```
