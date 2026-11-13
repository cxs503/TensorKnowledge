# KF-RESULT wp-12510-01

- package_id: `wp-12510-01` ｜ task_type: `01-asset-registration` ｜ report_id: `12510` ｜ lane: C ｜ repo: TensorKnowledge ｜ status: draft
- source: `tensor://reports/12510`（field=`markdown`），chars=5656，bytes=9623，sha256=`sha256:45f688344f4bc7983fc167fa84ef0fb47ad9a7a8265bcfbe8095239002da62da`
- 工序范围：**只登记资产，不抽取 claim、不做报告类型分类、不标 verified**（按契约 objective/constraints）

## ① 本工序做了什么（含案例介绍）

对 report_id=12510（`IMO IGF/G12 替代燃料安全评估框架`，scenario_key=`imo_g12_fuel_safety`，mission_id=11196）执行 01-asset-registration：

1. 从平台 API 取回该报告 markdown，重算字节哈希并锁定：`sha256:45f688344f4bc7983fc167fa84ef0fb47ad9a7a8265bcfbe8095239002da62da`，9623 字节 / 5656 字符——与契约声明逐字节一致（hash_check.match=True，chars_check.match=True）。
2. 建立资产清单：共 **8 个资产**（resolved 8 / unresolved 0），覆盖源文档本体、记录元数据、4 张声明图、代码模块与测试套件。
3. 为每个资产登记 locator（markdown 字符区间 + record 字段），全部由程序在运行时从原文计算，可逐条回解。
4. 探测资产可解析性：4 张图与代码/测试路径在本节点（m11196 工作树，只读）定位到字节/文件并复算 sha256；平台侧图下载端点不存在（3 个候选端点 HTTP 404），图字节以节点工件为准。
5. claims 按契约留空数组（objective.classify_report_type=false，不强制生成知识）。

## ② 怎么做的（步骤/工具/关键设置）

| 步骤 | 工具/脚本 | 关键设置 |
| --- | --- | --- |
| 取源 + 锁哈希 | `scripts/wp12510_register_assets.py`（urllib，Bearer 登录） | 以 `markdown` 字段 utf-8 编码字节做 sha256；与契约声明逐字节比对，不一致即 SystemExit |
| 资产登记 | 同上（`--offline` 可离线复跑） | quote 用**字面量针**在 markdown 内检索，找不到/不唯一即 SystemExit（拒绝编造）；每条 locator 存 `char_start/char_end/quote` |
| 可解析性探测 | 同上 `disk_probe()` | 只读探测节点工件目录；记录存在性/大小/sha256，不重试、不猜测 |
| 验收门 | `scripts/wp12510_verify_acceptance.py` | 契约 6 项 acceptance + 2 项结构不变量；jsonschema Draft2020-12 校验信封 |
| 图 | `scripts/wp12510_render_figure.py` | matplotlib Agg，直接从 manifest 渲染，无手抄数字 |
| 单元测试 | `tests/test_wp12510_asset_manifest.py` | 10 项 pytest，含**负对照**（篡改 quote / 复制 id 必须被检出）与离线复跑确定性 |

## ③ 产出物清单

| 文件 | 要点 |
| --- | --- |
| `docs/kf/wp-12510-01/asset_manifest.json` | 8 资产 / 15 条 locator / 计数与不变量 / 完整性声明 |
| `docs/kf/wp-12510-01/kf_result.json` | 提交用结果信封（outputs=`asset_manifest.json`，claims=[]） |
| `docs/kf/wp-12510-01/acceptance.json` | 8 项验收检查的机器结论（all_pass=true） |
| `docs/kf/wp-12510-01/fig1_asset_resolution.png` | 资产解析状态图（见下） |
| `scripts/wp12510_register_assets.py`、`scripts/wp12510_verify_acceptance.py`、`scripts/wp12510_render_figure.py` | 登记/验收/渲染，一键复跑 |
| `tests/test_wp12510_asset_manifest.py` | 10 项 pytest（含负对照与复现性） |
| `runs/wp-12510-01/` | 源快照：`report_12510_api.json`、`report_12510.md`、`markdown.sha256` |

## ④ 证据定位表（字段 → 原文逐字片段）

下表的「原文片段」列全部是 report 12510 markdown 的**逐字子串**（markdown 类 locator 带字符区间，record 类 locator 带字段名）；逐条回解由 `source_locator_resolvable` 检查覆盖。

| asset_id | kind | locator | 原文片段（逐字） | status |
| --- | --- | --- | --- | --- |
| ast-12510-01 | source_document | markdown[0:24] | `# IMO IGF/G12 替代燃料安全评估框架` | resolved |
| ast-12510-02 | record_metadata | record.id | `12510` | resolved |
| ast-12510-02 | record_metadata | record.title | `IMO IGF/G12 替代燃料安全评估框架` | resolved |
| ast-12510-02 | record_metadata | record.scenario_key | `imo_g12_fuel_safety` | resolved |
| ast-12510-02 | record_metadata | record.mission_id | `11196` | resolved |
| ast-12510-03 | figure | markdown[3511:3560] | `![fig1_fuel_properties](fig1_fuel_properties.png)` | resolved |
| ast-12510-03 | figure | record.figures[0].name | `fig1_fuel_properties.png` | resolved |
| ast-12510-04 | figure | markdown[3652:3697] | `![fig2_hazard_levels](fig2_hazard_levels.png)` | resolved |
| ast-12510-04 | figure | record.figures[1].name | `fig2_hazard_levels.png` | resolved |
| ast-12510-05 | figure | markdown[3795:3836] | `![fig3_risk_matrix](fig3_risk_matrix.png)` | resolved |
| ast-12510-05 | figure | record.figures[2].name | `fig3_risk_matrix.png` | resolved |
| ast-12510-06 | figure | markdown[3909:3958] | `![fig4_risk_comparison](fig4_risk_comparison.png)` | resolved |
| ast-12510-06 | figure | record.figures[3].name | `fig4_risk_comparison.png` | resolved |
| ast-12510-07 | source_code_module | markdown[4949:4999] | `- **代码路径**: ’backend/modules/imo_g12_fuel_safety/’` | resolved |
| ast-12510-08 | test_suite | markdown[5000:5056] | `- **测试路径**: ’backend/modules/imo_g12_fuel_safety/tests/’` | resolved |

## ⑤ 注意点与局限

1. **图字节不在平台记录内**：平台 `figures` 元数据只有 name/caption（无二进制），3 个候选下载端点均 404；图字节以本节点 m11196 工作树 `artifacts/imo_g12_fuel_safety/` 为准（sha256 已入 manifest `node_artifact`）。若该工作树被清理，图资产将退化为 referenced_unresolved。
2. **代码/测试路径为跨仓引用**：`backend/modules/imo_g12_fuel_safety/` 属 ship-performance-platform 域（m11196 工作树），本仓仅登记引用与节点验证证据，不复制代码。
3. **不标 verified**：本工序只登记与定位；任何 verification 状态由平台门计算，manifest 中无 verified 标记。
4. **零手抄**：manifest 中所有数字（chars/bytes/sha256/偏移/计数）均为运行时计算；quote 为字面量针，运行时校验唯一性。
5. **边界遵守**：只读 report_id=12510；未读/写其它 report_id；未改写上游产物。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结论 | 机器证据 |
| --- | --- | --- |
| valid_json | ✅ PASS | kf_result.json + asset_manifest.json parsed |
| schema_pass | ✅ PASS | envelope validated against kf_result.v1.schema.json |
| source_locator_resolvable | ✅ PASS | 7 markdown locators checked; bad=[] |
| source_hash_matches | ✅ PASS | recomputed=sha256:45f688344f4bc7983fc167fa84ef0fb47ad9a7a8265bcfbe8095239002da62da |
| no_duplicate_ids | ✅ PASS | asset_ids=8 unique=8; claim_ids=0 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ PASS | claims=0 (empty is legitimate per contract notes) |
| envelope_outputs_key | ✅ PASS | outputs keys=['asset_manifest.json'] |
| provenance_consistency | ✅ PASS | envelope=sha256:45f688344f4bc7983fc167fa84ef0fb47ad9a7a8265bcfbe8095239002da62da manifest=sha256:45f688344f4bc7983fc167fa84ef0fb47ad9a7a8265bcfbe8095239002da62da |

**误差判定**：本工序为登记/定位工序，无物理量计算。关键量 vs 基准逐项：源哈希 重算值=契约值（逐字节一致，误差 0，<3% ✅）；chars 重算 5656 = 契约 5656（误差 0，<3% ✅）；7 条 markdown locator 全部逐字回解成功（7/7）。无物理量基准，原因：本工序为资产登记，不涉及数值计算。

**结果图**：`fig1_asset_resolution.png`（资产解析状态，由 manifest 程序化渲染，无手抄数字；经 API `figures` 参数内嵌于本报告）。

**repro_cmd**（一键复跑）：
`python3 scripts/wp12510_register_assets.py --offline && python3 scripts/wp12510_verify_acceptance.py && python3 scripts/wp12510_render_figure.py && python3 -m pytest tests/test_wp12510_asset_manifest.py -q`

## 结果 JSON（唯一 json 块）

```json
{
  "package_id": "wp-12510-01",
  "task_type": "01-asset-registration",
  "report_id": "12510",
  "provenance": {
    "source_hash": "sha256:45f688344f4bc7983fc167fa84ef0fb47ad9a7a8265bcfbe8095239002da62da",
    "source_field": "markdown",
    "producer": "agent/m15747",
    "emitted_at": "2026-11-12T02:40:22+00:00",
    "notes": "source_hash recomputed from the report-12510 markdown bytes fetched over the TensorPlatform API; equals the contract-declared hash sha256:45f688344f4bc7983fc167fa84ef0fb47ad9a7a8265bcfbe8095239002da62da"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-12510-01",
      "task_type": "01-asset-registration",
      "scope": {
        "report_id": "12510",
        "reports_touched": [
          "12510"
        ],
        "registers_assets_only": true,
        "extracts_claims": false,
        "classifies_report_type": false,
        "writes_outside_worktree": false
      },
      "source": {
        "report_id": "12510",
        "source_uri": "tensor://reports/12510",
        "source_field": "markdown",
        "title": "IMO IGF/G12 替代燃料安全评估框架",
        "scenario_key": "imo_g12_fuel_safety",
        "chars": 5656,
        "bytes_utf8": 9623,
        "sha256": "sha256:45f688344f4bc7983fc167fa84ef0fb47ad9a7a8265bcfbe8095239002da62da",
        "hash_check": {
          "expected": "sha256:45f688344f4bc7983fc167fa84ef0fb47ad9a7a8265bcfbe8095239002da62da",
          "recomputed": "sha256:45f688344f4bc7983fc167fa84ef0fb47ad9a7a8265bcfbe8095239002da62da",
          "match": true
        },
        "chars_check": {
          "expected": 5656,
          "observed": 5656,
          "match": true
        },
        "title_check": {
          "expected": "IMO IGF/G12 替代燃料安全评估框架",
          "observed": "IMO IGF/G12 替代燃料安全评估框架",
          "match": true
        },
        "scenario_key_check": {
          "expected": "imo_g12_fuel_safety",
          "observed": "imo_g12_fuel_safety",
          "match": true
        },
        "platform_figures": [
          {
            "name": "fig1_fuel_properties",
            "caption": "四种替代燃料关键物性对比（爆炸范围/闪点/沸点/热值）"
          },
          {
            "name": "fig2_hazard_levels",
            "caption": "四种燃料危险等级雷达图（火灾爆炸/毒性/低温/腐蚀/扩散）"
          },
          {
            "name": "fig3_risk_matrix",
            "caption": "5×5 风险评估矩阵（概率×后果）"
          },
          {
            "name": "fig4_risk_comparison",
            "caption": "四种燃料风险场景分布对比"
          }
        ],
        "platform_tags": [
          "IMO",
          "IGF Code",
          "G12",
          "alternative_fuel",
          "safety",
          "LNG",
          "methanol",
          "ammonia",
          "hydrogen",
          "risk_assessment"
        ]
      },
      "assets": [
        {
          "asset_id": "ast-12510-01",
          "kind": "source_document",
          "role": "primary_source",
          "name": "report_12510_markdown",
          "locators": [
            {
              "source_uri": "tensor://reports/12510",
              "source_field": "markdown",
              "char_start": 0,
              "char_end": 24,
              "start_line": 0,
              "end_line": 0,
              "quote": "# IMO IGF/G12 替代燃料安全评估框架",
              "unique": true,
              "note": "H1 line; whole-document identity (chars/bytes/sha256) recorded in content_ref"
            }
          ],
          "content_ref": {
            "source_uri": "tensor://reports/12510",
            "source_field": "markdown",
            "chars": 5656,
            "byte_length_utf8": 9623,
            "sha256": "sha256:45f688344f4bc7983fc167fa84ef0fb47ad9a7a8265bcfbe8095239002da62da"
          },
          "resolvable": true,
          "resolution": "fetched_via_tensor_api",
          "status": "resolved"
        },
        {
          "asset_id": "ast-12510-02",
          "kind": "record_metadata",
          "role": "identification",
          "name": "report_12510_record",
          "locators": [
            {
              "source_uri": "tensor://reports/12510",
              "source_field": "record",
              "field": "id",
              "value": 12510
            },
            {
              "source_uri": "tensor://reports/12510",
              "source_field": "record",
              "field": "title",
              "value": "IMO IGF/G12 替代燃料安全评估框架"
            },
            {
              "source_uri": "tensor://reports/12510",
              "source_field": "record",
              "field": "scenario_key",
              "value": "imo_g12_fuel_safety"
            },
            {
              "source_uri": "tensor://reports/12510",
              "source_field": "record",
              "field": "mission_id",
              "value": 11196
            }
          ],
          "resolvable": true,
          "resolution": "fetched_via_tensor_api",
          "status": "resolved"
        },
        {
          "asset_id": "ast-12510-03",
          "kind": "figure",
          "role": "result_figure",
          "name": "fig1_fuel_properties.png",
          "locators": [
            {
              "source_uri": "tensor://reports/12510",
              "source_field": "markdown",
              "char_start": 3511,
              "char_end": 3560,
              "start_line": 142,
              "end_line": 142,
              "quote": "![fig1_fuel_properties](fig1_fuel_properties.png)",
              "unique": true
            },
            {
              "source_uri": "tensor://reports/12510",
              "source_field": "record",
              "field": "figures[0].name",
              "value": "fig1_fuel_properties.png"
            }
          ],
          "caption": "四种替代燃料关键物性对比（爆炸范围/闪点/沸点/热值）",
          "node_artifact": {
            "path": "/root/tp-agent/work/m11196/artifacts/imo_g12_fuel_safety/fig1_fuel_properties.png",
            "exists": true,
            "kind": "file",
            "bytes": 70788,
            "sha256": "sha256:c2b1d00f32e04fe5936edb8f6badf378e0a74798489acbd38c1b91e1442c3e7e"
          },
          "resolvable": true,
          "resolution": "referenced_in_markdown_and_record; bytes verified on node",
          "status": "resolved"
        },
        {
          "asset_id": "ast-12510-04",
          "kind": "figure",
          "role": "result_figure",
          "name": "fig2_hazard_levels.png",
          "locators": [
            {
              "source_uri": "tensor://reports/12510",
              "source_field": "markdown",
              "char_start": 3652,
              "char_end": 3697,
              "start_line": 148,
              "end_line": 148,
              "quote": "![fig2_hazard_levels](fig2_hazard_levels.png)",
              "unique": true
            },
            {
              "source_uri": "tensor://reports/12510",
              "source_field": "record",
              "field": "figures[1].name",
              "value": "fig2_hazard_levels.png"
            }
          ],
          "caption": "四种燃料危险等级雷达图（火灾爆炸/毒性/低温/腐蚀/扩散）",
          "node_artifact": {
            "path": "/root/tp-agent/work/m11196/artifacts/imo_g12_fuel_safety/fig2_hazard_levels.png",
            "exists": true,
            "kind": "file",
            "bytes": 141704,
            "sha256": "sha256:377110c0f205e3645f7782b93eb94d67a3ff3d251c9cc360756a750eb124b641"
          },
          "resolvable": true,
          "resolution": "referenced_in_markdown_and_record; bytes verified on node",
          "status": "resolved"
        },
        {
          "asset_id": "ast-12510-05",
          "kind": "figure",
          "role": "result_figure",
          "name": "fig3_risk_matrix.png",
          "locators": [
            {
              "source_uri": "tensor://reports/12510",
              "source_field": "markdown",
              "char_start": 3795,
              "char_end": 3836,
              "start_line": 154,
              "end_line": 154,
              "quote": "![fig3_risk_matrix](fig3_risk_matrix.png)",
              "unique": true
            },
            {
              "source_uri": "tensor://reports/12510",
              "source_field": "record",
              "field": "figures[2].name",
              "value": "fig3_risk_matrix.png"
            }
          ],
          "caption": "5×5 风险评估矩阵（概率×后果）",
          "node_artifact": {
            "path": "/root/tp-agent/work/m11196/artifacts/imo_g12_fuel_safety/fig3_risk_matrix.png",
            "exists": true,
            "kind": "file",
            "bytes": 63943,
            "sha256": "sha256:3bc521ebc59851c37c72d728134f9bcf24e97f5c44e918f564ec54d337167d9e"
          },
          "resolvable": true,
          "resolution": "referenced_in_markdown_and_record; bytes verified on node",
          "status": "resolved"
        },
        {
          "asset_id": "ast-12510-06",
          "kind": "figure",
          "role": "result_figure",
          "name": "fig4_risk_comparison.png",
          "locators": [
            {
              "source_uri": "tensor://reports/12510",
              "source_field": "markdown",
              "char_start": 3909,
              "char_end": 3958,
              "start_line": 160,
              "end_line": 160,
              "quote": "![fig4_risk_comparison](fig4_risk_comparison.png)",
              "unique": true
            },
            {
              "source_uri": "tensor://reports/12510",
              "source_field": "record",
              "field": "figures[3].name",
              "value": "fig4_risk_comparison.png"
            }
          ],
          "caption": "四种燃料风险场景分布对比",
          "node_artifact": {
            "path": "/root/tp-agent/work/m11196/artifacts/imo_g12_fuel_safety/fig4_risk_comparison.png",
            "exists": true,
            "kind": "file",
            "bytes": 41507,
            "sha256": "sha256:e6460c80e7401abe7245319ff778534a6cb3ef6f9ee40acd29b692f290e34cd3"
          },
          "resolvable": true,
          "resolution": "referenced_in_markdown_and_record; bytes verified on node",
          "status": "resolved"
        },
        {
          "asset_id": "ast-12510-07",
          "kind": "source_code_module",
          "role": "implementation",
          "name": "backend/modules/imo_g12_fuel_safety",
          "locators": [
            {
              "source_uri": "tensor://reports/12510",
              "source_field": "markdown",
              "char_start": 4949,
              "char_end": 4999,
              "start_line": 209,
              "end_line": 209,
              "quote": "- **代码路径**: `backend/modules/imo_g12_fuel_safety/`",
              "unique": true
            }
          ],
          "node_artifact": {
            "path": "/root/tp-agent/work/m11196/backend/modules/imo_g12_fuel_safety",
            "exists": true,
            "kind": "dir",
            "entries": [
              "__init__.py",
              "api.py",
              "compliance.py",
              "fuels.py",
              "hazards.py",
              "risk_matrix.py",
              "safety_measures.py",
              "tests"
            ],
            "entry_count": 8
          },
          "resolvable": true,
          "resolution": "referenced_in_markdown; module verified on node",
          "status": "resolved"
        },
        {
          "asset_id": "ast-12510-08",
          "kind": "test_suite",
          "role": "verification",
          "name": "backend/modules/imo_g12_fuel_safety/tests",
          "locators": [
            {
              "source_uri": "tensor://reports/12510",
              "source_field": "markdown",
              "char_start": 5000,
              "char_end": 5056,
              "start_line": 210,
              "end_line": 210,
              "quote": "- **测试路径**: `backend/modules/imo_g12_fuel_safety/tests/`",
              "unique": true
            }
          ],
          "node_artifact": {
            "path": "/root/tp-agent/work/m11196/backend/modules/imo_g12_fuel_safety/tests",
            "exists": true,
            "kind": "dir",
            "entries": [
              "conftest.py",
              "test_api.py",
              "test_compliance.py",
              "test_fuels.py",
              "test_hazards.py",
              "test_risk_matrix.py",
              "test_safety_measures.py"
            ],
            "entry_count": 7
          },
          "resolvable": true,
          "resolution": "referenced_in_markdown; suite verified on node",
          "status": "resolved"
        }
      ],
      "asset_counts": {
        "total": 8,
        "by_class": {
          "source_document": 1,
          "record_metadata": 1,
          "figure": 4,
          "source_code_module": 1,
          "test_suite": 1
        },
        "by_status": {
          "resolved": 8,
          "unresolved": 0
        }
      },
      "id_uniqueness": {
        "asset_ids_unique": true,
        "claim_ids_unique": true
      },
      "claims": [],
      "claims_policy": "empty is legitimate for this package: objective.classify_report_type=false, no extraction; claims are not force-generated",
      "integrity": {
        "quote_uniqueness": "every markdown locator quote verified at runtime as a unique verbatim substring of the fetched markdown (count==1); failure aborts the build",
        "hash_recomputed_locally": "sha256:45f688344f4bc7983fc167fa84ef0fb47ad9a7a8265bcfbe8095239002da62da",
        "hash_matches_contract": true
      }
    }
  },
  "claims": []
}
```
