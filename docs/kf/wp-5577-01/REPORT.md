# KF-RESULT wp-5577-01

- package_id: `wp-5577-01` ｜ task_type: `01-asset-registration` ｜ report_id: `5577` ｜ lane: C ｜ repo: TensorKnowledge ｜ status: draft
- source: `tensor://reports/5577`（field=`markdown`），chars=3702，bytes=5707，sha256=`sha256:60575cfe91ed23757639b1060ce931c746236989cb3ba8734a4a8280582b7de8`
- 工序范围：**只登记资产，不抽取 claim、不做报告类型分类、不标 verified**（按契约 objective/constraints）

## ① 本工序做了什么

对 report_id=5577（`BP 示范工程报告：Agent 科研生产闭环端到端实证（IN12-P8 / m4936）`）执行 01-asset-registration：

1. 从平台 API 取回该报告记录，重算 `markdown` 字段 utf-8 字节哈希并锁定：`sha256:60575cfe91ed23757639b1060ce931c746236989cb3ba8734a4a8280582b7de8`，5707 字节 / 3702 字符——与契约声明 `sha256:60575cfe91ed23757639b1060ce931c746236989cb3ba8734a4a8280582b7de8` 逐字节一致（match=True），chars 契约 3702 = 实测 3702。
2. 建立资产清单：共 **21 个资产**（resolved 2 / unresolved 19），覆盖源文档本体、记录元数据、3 张声明图、以及报告正文中逐字出现的 16 个工件/端点/标准/文献/任务引用。
3. 为每个资产登记 locator（markdown 字符区间 17 条 + record 字段 9 条），全部由脚本在运行时从原文计算，可逐条回解。
4. claims 按契约留空数组，并显式写明留空理由（`no_forced_claim_generation`；本包 objective 仅 `register_assets`）。

## ② 怎么做的（步骤/工具/关键设置）

| 步骤 | 工具/脚本 | 关键设置 |
| --- | --- | --- |
| 取源 + 锁哈希 | `scripts/wp5577_register_assets.py`（urllib，Bearer 登录） | 以 `markdown` 字段 utf-8 编码字节做 sha256（不做换行归一）；与契约声明逐字节比对，不符即 SystemExit |
| 资产登记 | 同上（`--offline` 可离线复跑） | 工件/端点/标准/文献引用用**字面量针**在 markdown 内检索，找不到即 SystemExit（拒绝编造 locator）；每条 locator 存 `char_start/char_end/quote` |
| 验收门 | 同上（`verify_acceptance`） | 契约 6 项 acceptance + 2 项结构不变量；jsonschema Draft2020-12 校验信封 |
| 图 | `scripts/wp5577_render_figure.py` | matplotlib Agg，直接从 manifest 渲染，无手抄数字 |
| 单元测试 | `tests/test_wp5577_asset_manifest.py` | 12 项，含**负对照**（篡改 quote / 平移偏移必须被检出；缺失针必须被拒）与离线复跑逐字节一致性 |

不复用的既有件：本检出原先缺 `schemas/kf_result.v1.schema.json`（其它工作树已有同内容副本，md5 `0491bc4ce09a1fc2f62f015666d38935`）；本单按字节原样补齐该 schema 以便验收门可在本检出内复跑。

## ③ 产出物清单

| 文件 | 要点 |
| --- | --- |
| `docs/kf/wp-5577-01/asset_manifest.json` | 21 资产 / 26 locator / 计数与不变量 / claims 政策 |
| `docs/kf/wp-5577-01/kf_result.json` | 提交用结果信封（outputs=`asset_manifest.json`，claims=[]） |
| `docs/kf/wp-5577-01/acceptance.json` | 8 项验收检查的机器结论（全部 PASS） |
| `docs/kf/wp-5577-01/fig1_asset_resolution.png` | 资产解析状态图（本报告 ④ 后附图） |
| `docs/kf/wp-5577-01/source/` | 源快照：`report_5577.json`（API 记录）、`report_5577.md`、`markdown.sha256` |
| `scripts/wp5577_register_assets.py`、`scripts/wp5577_render_figure.py`、`scripts/wp5577_build_report.py` | 登记/渲染/组报，一键复跑 |
| `tests/test_wp5577_asset_manifest.py` | 12 项 pytest（含负对照与复现性） |
| `schemas/kf_result.v1.schema.json` | 结果信封 schema（与其它工作树副本 md5 一致） |

## ④ 证据定位表（asset → 原文逐字片段）

下表的「原文片段」列全部是 report 5577 markdown 的**逐字子串**（markdown 类 locator 带字符区间，record 类 locator 带字段名）；逐条回解由 `source_locator_resolvable` 检查覆盖（17/17 条 markdown locator 回解成功）。

| asset_id | kind | status | 原文片段（逐字） |
| --- | --- | --- | --- |
| ast-5577-01 | source_document | resolved | `## ① 案例介绍` |
| ast-5577-02 | record_metadata | resolved | `5577` |
| ast-5577-03 | figure | unresolved | `fig1_resistance_spectrum.png` |
| ast-5577-04 | figure | unresolved | `fig2_deviation_spectrum.png` |
| ast-5577-05 | figure | unresolved | `fig3_evidence_chain.png` |
| ast-5577-06 | declared_artifact | unresolved | `python -m bp_demo.run` |
| ast-5577-07 | declared_artifact | unresolved | `/api/v1/calculations/resistance` |
| ast-5577-08 | declared_artifact | unresolved | `cluster_exec.py nodes` |
| ast-5577-09 | declared_artifact | unresolved | `physics/holtrop` |
| ast-5577-10 | declared_artifact | unresolved | `tests/test_resistance_ittc78.py` |
| ast-5577-11 | declared_artifact | unresolved | `artifacts/bp_demo/sha256_index.json` |
| ast-5577-12 | declared_artifact | unresolved | `/calculations/resistance` |
| ast-5577-13 | declared_artifact | unresolved | `/resistance/predict` |
| ast-5577-14 | declared_artifact | unresolved | `http://127.0.0.1:8002` |
| ast-5577-15 | standard_reference | unresolved | `ITTC-57` |
| ast-5577-16 | standard_reference | unresolved | `ITTC-1978` |
| ast-5577-17 | literature_reference | unresolved | `Holtrop & Mennen (1982)` |
| ast-5577-18 | literature_reference | unresolved | `Holtrop (1984)` |
| ast-5577-19 | benchmark_reference | unresolved | `KVLCC2` |
| ast-5577-20 | mission_reference | unresolved | `m2082` |
| ast-5577-21 | gate_reference | unresolved | `report_gate` |

图 1：`fig1_asset_resolution.png` — 21 个资产的解析状态（绿=resolved 2 个：源文档与记录元数据；红=unresolved 19 个：3 图 + 16 个声明引用）与 kind 分布。

## ⑤ 注意点与局限

1. **19 个资产 unresolved 是报告记录本身的缺口，不是登记遗漏**：3 张图在 record 里只有 `name`+`caption`（无 `png_base64`），图内容不可审计；16 个工件/端点/标准/文献引用只以名字出现在正文，其字节副本在产出仓（ship-performance-platform）或平台侧，不在本报告记录内。
2. **登记面向主文**：本包不解析表格数值、不复核报告内任何数字的正确性——那是 03/04 工序与独立复核单的职责；本单对报告 5577 的任何数字**没有**做正确性背书。
3. **claims 为空是设计而非缺漏**：契约 objective 仅 `register_assets`（`classify_report_type=false`），constraints 禁止强制生成 claim；因此本包不产出任何 claim，也不存在「verified」标记（verification 由平台门计算）。
4. **装置依赖**：全部检查在本检出内离线可复跑（`--offline`，源快照在 `docs/kf/wp-5577-01/source/`）；在线模式经 API 重取，两种模式在本单中逐字节一致（`test_offline_rerun_byte_identical`）。
5. **schema 补齐**：本检出原先缺 `schemas/kf_result.v1.schema.json`，按其它工作树同内容副本（md5 `0491bc4ce09a1fc2f62f015666d38935`）字节原样补齐，未改任何字段。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结论 |
| --- | --- |
| valid_json | ☑ |
| schema_pass | ☑ |
| source_hash_matches | ☑ |
| source_locator_resolvable | ☑ |
| no_duplicate_ids | ☑ |
| all_claims_have_evidence_or_explicit_unresolved_status | ☑ |
| unresolved_assets_have_reason | ☑ |
| reports_touched_single | ☑ |

**honest 声明**：无失败项。需明示一项非失败的性质——19 个 unresolved 资产是源记录缺字节副本所致（见 ⑤.1），下游 02/03 工序若需图内容或工件字节，须另走平台存储端点或产出仓。

**repro_cmd**（工作树根执行，一键复跑）：

```bash
python3 scripts/wp5577_register_assets.py --offline   # 离线复跑：manifest + 信封 + acceptance（在线去掉 --offline）
python3 scripts/wp5577_render_figure.py               # 渲染 fig1_asset_resolution.png
python3 scripts/wp5577_build_report.py                # 组装本报告（唯一 json 块=结果信封）
python3 -m pytest tests/test_wp5577_asset_manifest.py -q   # 12 项测试（含负对照）
```

**结果信封（契约要求的唯一 json 代码块，字段结构见 schemas/kf_result.v1.schema.json）**：

```json
{
  "package_id": "wp-5577-01",
  "task_type": "01-asset-registration",
  "report_id": "5577",
  "provenance": {
    "source_hash": "sha256:60575cfe91ed23757639b1060ce931c746236989cb3ba8734a4a8280582b7de8",
    "source_field": "markdown",
    "producer": "agent/m15568",
    "emitted_at": "2026-11-12T01:44:36+00:00",
    "notes": "source_hash recomputed from the report-5577 markdown bytes fetched over the TensorPlatform API; equals the contract-declared hash sha256:60575cfe91ed23757639b1060ce931c746236989cb3ba8734a4a8280582b7de8"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-5577-01",
      "task_type": "01-asset-registration",
      "generated_by": "scripts/wp5577_register_assets.py",
      "scope": {
        "report_id": "5577",
        "reports_touched": [
          "5577"
        ],
        "registers_assets_only": true,
        "extracts_claims": false,
        "classifies_report_type": false,
        "writes_outside_worktree": false
      },
      "source": {
        "report_id": "5577",
        "source_uri": "tensor://reports/5577",
        "source_field": "markdown",
        "title": "BP 示范工程报告：Agent 科研生产闭环端到端实证（IN12-P8 / m4936）",
        "title_matches_contract": true,
        "scenario_key": "campaign/bp-demo-in12p8",
        "scenario_key_matches_contract": true,
        "mission_id": 4936,
        "status": "published",
        "tags": [
          "BP示范工程",
          "科研闭环",
          "阻力",
          "Holtrop-Mennen",
          "report_gate",
          "honest-fail"
        ],
        "chars": 3702,
        "byte_length_utf8": 5707,
        "sha256": "sha256:60575cfe91ed23757639b1060ce931c746236989cb3ba8734a4a8280582b7de8",
        "hash_check": {
          "expected": "sha256:60575cfe91ed23757639b1060ce931c746236989cb3ba8734a4a8280582b7de8",
          "recomputed": "sha256:60575cfe91ed23757639b1060ce931c746236989cb3ba8734a4a8280582b7de8",
          "match": true
        },
        "chars_check": {
          "expected": 3702,
          "observed": 3702,
          "match": true
        },
        "figures_entries": 3
      },
      "asset_counts": {
        "total": 21,
        "resolved": 2,
        "unresolved": 19,
        "by_status": {
          "resolved": 2,
          "unresolved": 19
        }
      },
      "claims_policy": {
        "claims": [],
        "reason": "contract objective is register_assets only (classify_report_type=false); constraints forbid forced claim generation, so claims is an empty array by design — no knowledge objects are minted in this work package"
      },
      "assets": [
        {
          "asset_id": "ast-5577-01",
          "kind": "source_document",
          "role": "primary_source",
          "name": "report_5577_markdown",
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "markdown",
              "char_start": 0,
              "char_end": 9,
              "quote": "## ① 案例介绍",
              "note": "first line (no H1 in this report); whole-document span in content_ref"
            }
          ],
          "content_ref": {
            "source_uri": "tensor://reports/5577",
            "source_field": "markdown",
            "chars": 3702,
            "byte_length_utf8": 5707,
            "sha256": "sha256:60575cfe91ed23757639b1060ce931c746236989cb3ba8734a4a8280582b7de8"
          },
          "resolvable": true,
          "resolution": "fetched_via_tensor_api",
          "status": "resolved"
        },
        {
          "asset_id": "ast-5577-02",
          "kind": "record_metadata",
          "role": "identification",
          "name": "report_5577_record",
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "record",
              "field": "id",
              "value": 5577
            },
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "record",
              "field": "title",
              "value": "BP 示范工程报告：Agent 科研生产闭环端到端实证（IN12-P8 / m4936）"
            },
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "record",
              "field": "scenario_key",
              "value": "campaign/bp-demo-in12p8"
            },
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "record",
              "field": "mission_id",
              "value": 4936
            },
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "record",
              "field": "status",
              "value": "published"
            },
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "record",
              "field": "tags",
              "value": [
                "BP示范工程",
                "科研闭环",
                "阻力",
                "Holtrop-Mennen",
                "report_gate",
                "honest-fail"
              ]
            }
          ],
          "resolvable": true,
          "resolution": "fetched_via_tensor_api",
          "status": "resolved"
        },
        {
          "asset_id": "ast-5577-03",
          "kind": "figure",
          "role": "declared_figure",
          "name": "fig1_resistance_spectrum.png",
          "declared_metadata": {
            "caption": "图 1 KCS 总阻力—航速谱：引擎实测 vs Holtrop-Mennen 主链同参数复算 vs 仓内 m2082 基准点"
          },
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "record",
              "field": "figures[0].name",
              "value": "fig1_resistance_spectrum.png"
            }
          ],
          "payload": {
            "present": false,
            "bytes": 0,
            "sha256": null
          },
          "resolvable": false,
          "status": "unresolved",
          "unresolved_reason": "record.figures carries name+caption only (no png_base64); no byte payload in the report record, so the image content cannot be audited from this source"
        },
        {
          "asset_id": "ast-5577-04",
          "kind": "figure",
          "role": "declared_figure",
          "name": "fig2_deviation_spectrum.png",
          "declared_metadata": {
            "caption": "图 2 偏差谱：逐航速点相对偏差与四项验证判据偏差，绿带为 ±3%"
          },
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "record",
              "field": "figures[1].name",
              "value": "fig2_deviation_spectrum.png"
            }
          ],
          "payload": {
            "present": false,
            "bytes": 0,
            "sha256": null
          },
          "resolvable": false,
          "status": "unresolved",
          "unresolved_reason": "record.figures carries name+caption only (no png_base64); no byte payload in the report record, so the image content cannot be audited from this source"
        },
        {
          "asset_id": "ast-5577-05",
          "kind": "figure",
          "role": "declared_figure",
          "name": "fig3_evidence_chain.png",
          "declared_metadata": {
            "caption": "图 3 证据链：任务组织→引擎调用→算力管理→独立验证 四阶段机读状态与耗时"
          },
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "record",
              "field": "figures[2].name",
              "value": "fig3_evidence_chain.png"
            }
          ],
          "payload": {
            "present": false,
            "bytes": 0,
            "sha256": null
          },
          "resolvable": false,
          "status": "unresolved",
          "unresolved_reason": "record.figures carries name+caption only (no png_base64); no byte payload in the report record, so the image content cannot be audited from this source"
        },
        {
          "asset_id": "ast-5577-06",
          "kind": "declared_artifact",
          "role": "repro_command",
          "name": "python -m bp_demo.run",
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "markdown",
              "char_start": 528,
              "char_end": 549,
              "quote": "python -m bp_demo.run",
              "note": "one-command four-stage closed-loop rerun"
            }
          ],
          "payload": {
            "present": false,
            "bytes": null,
            "sha256": null
          },
          "resolvable": false,
          "status": "unresolved",
          "unresolved_reason": "referenced by name in the report markdown; the referenced object lives in the producing repo (ship-performance-platform) or on the platform, not in this report record"
        },
        {
          "asset_id": "ast-5577-07",
          "kind": "declared_artifact",
          "role": "engine_endpoint",
          "name": "/api/v1/calculations/resistance",
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "markdown",
              "char_start": 673,
              "char_end": 704,
              "quote": "/api/v1/calculations/resistance",
              "note": "engine endpoint called 8 times (5 speeds + 2 negative controls + 1 deterministic re-call)"
            }
          ],
          "payload": {
            "present": false,
            "bytes": null,
            "sha256": null
          },
          "resolvable": false,
          "status": "unresolved",
          "unresolved_reason": "referenced by name in the report markdown; the referenced object lives in the producing repo (ship-performance-platform) or on the platform, not in this report record"
        },
        {
          "asset_id": "ast-5577-08",
          "kind": "declared_artifact",
          "role": "cluster_probe_command",
          "name": "cluster_exec.py nodes",
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "markdown",
              "char_start": 773,
              "char_end": 794,
              "quote": "cluster_exec.py nodes",
              "note": "702 dual-node loong64 liveness probe"
            }
          ],
          "payload": {
            "present": false,
            "bytes": null,
            "sha256": null
          },
          "resolvable": false,
          "status": "unresolved",
          "unresolved_reason": "referenced by name in the report markdown; the referenced object lives in the producing repo (ship-performance-platform) or on the platform, not in this report record"
        },
        {
          "asset_id": "ast-5577-09",
          "kind": "declared_artifact",
          "role": "physics_module",
          "name": "physics/holtrop",
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "markdown",
              "char_start": 1015,
              "char_end": 1030,
              "quote": "physics/holtrop",
              "note": "single physics source for residual wave-making resistance"
            }
          ],
          "payload": {
            "present": false,
            "bytes": null,
            "sha256": null
          },
          "resolvable": false,
          "status": "unresolved",
          "unresolved_reason": "referenced by name in the report markdown; the referenced object lives in the producing repo (ship-performance-platform) or on the platform, not in this report record"
        },
        {
          "asset_id": "ast-5577-10",
          "kind": "declared_artifact",
          "role": "test_file",
          "name": "tests/test_resistance_ittc78.py",
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "markdown",
              "char_start": 2524,
              "char_end": 2555,
              "quote": "tests/test_resistance_ittc78.py",
              "note": "legacy test file; collection fixed this round (41 passed / 3 skipped)"
            }
          ],
          "payload": {
            "present": false,
            "bytes": null,
            "sha256": null
          },
          "resolvable": false,
          "status": "unresolved",
          "unresolved_reason": "referenced by name in the report markdown; the referenced object lives in the producing repo (ship-performance-platform) or on the platform, not in this report record"
        },
        {
          "asset_id": "ast-5577-11",
          "kind": "declared_artifact",
          "role": "artifact_index",
          "name": "artifacts/bp_demo/sha256_index.json",
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "markdown",
              "char_start": 2271,
              "char_end": 2306,
              "quote": "artifacts/bp_demo/sha256_index.json",
              "note": "sha256 index of the 3 PNGs"
            }
          ],
          "payload": {
            "present": false,
            "bytes": null,
            "sha256": null
          },
          "resolvable": false,
          "status": "unresolved",
          "unresolved_reason": "referenced by name in the report markdown; the referenced object lives in the producing repo (ship-performance-platform) or on the platform, not in this report record"
        },
        {
          "asset_id": "ast-5577-12",
          "kind": "declared_artifact",
          "role": "legacy_endpoint",
          "name": "/calculations/resistance",
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "markdown",
              "char_start": 680,
              "char_end": 704,
              "quote": "/calculations/resistance",
              "note": "legacy mock endpoint (pre-fix)"
            }
          ],
          "payload": {
            "present": false,
            "bytes": null,
            "sha256": null
          },
          "resolvable": false,
          "status": "unresolved",
          "unresolved_reason": "referenced by name in the report markdown; the referenced object lives in the producing repo (ship-performance-platform) or on the platform, not in this report record"
        },
        {
          "asset_id": "ast-5577-13",
          "kind": "declared_artifact",
          "role": "mainchain_endpoint",
          "name": "/resistance/predict",
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "markdown",
              "char_start": 2370,
              "char_end": 2389,
              "quote": "/resistance/predict",
              "note": "Holtrop main-chain endpoint"
            }
          ],
          "payload": {
            "present": false,
            "bytes": null,
            "sha256": null
          },
          "resolvable": false,
          "status": "unresolved",
          "unresolved_reason": "referenced by name in the report markdown; the referenced object lives in the producing repo (ship-performance-platform) or on the platform, not in this report record"
        },
        {
          "asset_id": "ast-5577-14",
          "kind": "declared_artifact",
          "role": "deployed_instance",
          "name": "http://127.0.0.1:8002",
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "markdown",
              "char_start": 1891,
              "char_end": 1912,
              "quote": "http://127.0.0.1:8002",
              "note": "resident old-build instance (deployment drift)"
            }
          ],
          "payload": {
            "present": false,
            "bytes": null,
            "sha256": null
          },
          "resolvable": false,
          "status": "unresolved",
          "unresolved_reason": "referenced by name in the report markdown; the referenced object lives in the producing repo (ship-performance-platform) or on the platform, not in this report record"
        },
        {
          "asset_id": "ast-5577-15",
          "kind": "standard_reference",
          "role": "friction_standard",
          "name": "ITTC-57",
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "markdown",
              "char_start": 838,
              "char_end": 845,
              "quote": "ITTC-57",
              "note": "friction coefficient closed-form standard"
            }
          ],
          "payload": {
            "present": false,
            "bytes": null,
            "sha256": null
          },
          "resolvable": false,
          "status": "unresolved",
          "unresolved_reason": "referenced by name in the report markdown; the referenced object lives in the producing repo (ship-performance-platform) or on the platform, not in this report record"
        },
        {
          "asset_id": "ast-5577-16",
          "kind": "standard_reference",
          "role": "roughness_standard",
          "name": "ITTC-1978",
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "markdown",
              "char_start": 1973,
              "char_end": 1982,
              "quote": "ITTC-1978",
              "note": "roughness allowance standard"
            }
          ],
          "payload": {
            "present": false,
            "bytes": null,
            "sha256": null
          },
          "resolvable": false,
          "status": "unresolved",
          "unresolved_reason": "referenced by name in the report markdown; the referenced object lives in the producing repo (ship-performance-platform) or on the platform, not in this report record"
        },
        {
          "asset_id": "ast-5577-17",
          "kind": "literature_reference",
          "role": "wave_making_regression",
          "name": "Holtrop & Mennen (1982)",
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "markdown",
              "char_start": 107,
              "char_end": 130,
              "quote": "Holtrop & Mennen (1982)",
              "note": "wave-making resistance regression source"
            }
          ],
          "payload": {
            "present": false,
            "bytes": null,
            "sha256": null
          },
          "resolvable": false,
          "status": "unresolved",
          "unresolved_reason": "referenced by name in the report markdown; the referenced object lives in the producing repo (ship-performance-platform) or on the platform, not in this report record"
        },
        {
          "asset_id": "ast-5577-18",
          "kind": "literature_reference",
          "role": "wave_making_regression",
          "name": "Holtrop (1984)",
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "markdown",
              "char_start": 133,
              "char_end": 147,
              "quote": "Holtrop (1984)",
              "note": "wave-making resistance regression source"
            }
          ],
          "payload": {
            "present": false,
            "bytes": null,
            "sha256": null
          },
          "resolvable": false,
          "status": "unresolved",
          "unresolved_reason": "referenced by name in the report markdown; the referenced object lives in the producing repo (ship-performance-platform) or on the platform, not in this report record"
        },
        {
          "asset_id": "ast-5577-19",
          "kind": "benchmark_reference",
          "role": "benchmark_ship",
          "name": "KVLCC2",
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "markdown",
              "char_start": 865,
              "char_end": 871,
              "quote": "KVLCC2",
              "note": "full-scale literature anchor (HONEST-FAIL item V4)"
            }
          ],
          "payload": {
            "present": false,
            "bytes": null,
            "sha256": null
          },
          "resolvable": false,
          "status": "unresolved",
          "unresolved_reason": "referenced by name in the report markdown; the referenced object lives in the producing repo (ship-performance-platform) or on the platform, not in this report record"
        },
        {
          "asset_id": "ast-5577-20",
          "kind": "mission_reference",
          "role": "upstream_mission",
          "name": "m2082",
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "markdown",
              "char_start": 2408,
              "char_end": 2413,
              "quote": "m2082",
              "note": "mission that merged the two resistance chains"
            }
          ],
          "payload": {
            "present": false,
            "bytes": null,
            "sha256": null
          },
          "resolvable": false,
          "status": "unresolved",
          "unresolved_reason": "referenced by name in the report markdown; the referenced object lives in the producing repo (ship-performance-platform) or on the platform, not in this report record"
        },
        {
          "asset_id": "ast-5577-21",
          "kind": "gate_reference",
          "role": "report_gate",
          "name": "report_gate",
          "locators": [
            {
              "source_uri": "tensor://reports/5577",
              "source_field": "markdown",
              "char_start": 910,
              "char_end": 921,
              "quote": "report_gate",
              "note": "six-element report gate (8/8)"
            }
          ],
          "payload": {
            "present": false,
            "bytes": null,
            "sha256": null
          },
          "resolvable": false,
          "status": "unresolved",
          "unresolved_reason": "referenced by name in the report markdown; the referenced object lives in the producing repo (ship-performance-platform) or on the platform, not in this report record"
        }
      ]
    }
  },
  "claims": []
}
```
