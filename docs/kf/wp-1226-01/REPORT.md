# KF-RESULT wp-1226-01

- package_id: `wp-1226-01` ｜ task_type: `01-asset-registration` ｜ report_id: `1226` ｜ lane: C ｜ repo: TensorKnowledge ｜ status: draft
- source: `tensor://reports/1226`（field=`markdown`），chars=6045，bytes=8843，sha256=`sha256:d419206bdb3f282d2e2a1ac1f96e972af4438061815e95abba98d8c028e96717`
- 工序范围：**只登记资产，不抽取 claim、不做报告类型分类、不标 verified**（按契约 objective/constraints）

## ① 本工序做了什么

对 report_id=1226（`CII 参考线（MEPC.353(78) G1）独立复核与缺陷修复（m1643）`）执行 01-asset-registration：

1. 从平台 API 取回该报告 markdown，重算字节哈希并锁定：`sha256:d419206bdb3f282d2e2a1ac1f96e972af4438061815e95abba98d8c028e96717`，8843 字节 / 6045 字符——与契约声明 `sha256:d419206bdb3f282d2e2a1ac1f96e972af4438061815e95abba98d8c028e96717` 逐字节一致（match=True）。
2. 建立资产清单：共 **22 个资产**（resolved 2 / unresolved 20），覆盖源文档本体、记录元数据、3 张声明图、报告正文中逐字出现的 17 个外部工件/符号/规范引用。
3. 为每个资产登记 **35 条 locator**（markdown 字符区间 21 条 + record 字段 14 条），全部由程序在运行时从原文计算，可逐条回解。
4. 探测资产可解析性：对图/工件尝试平台存储端点，结果见 ⑤（4/4 端点 HTTP 404）。
5. claims 按契约留空数组，并显式写明留空理由（不强制生成知识）。

## ② 怎么做的（步骤/工具/关键设置）

| 步骤 | 工具/脚本 | 关键设置 |
| --- | --- | --- |
| 取源 + 锁哈希 | `scripts/kf_fetch_1226.py`（urllib，Bearer 登录） | 以 `markdown` 字段 utf-8 编码字节做 sha256；与契约声明逐字节比对 |
| 资产登记 | `scripts/wp1226_register_assets.py`（`--offline` 可离线复跑） | 代码/工件/规范引用用**字面量针**在 markdown 内检索，找不到即 SystemExit（拒绝编造）；每条 locator 存 `char_start/char_end/quote` |
| 可解析性探测 | `scripts/wp1226_probe_assets.py` | 4 个候选端点；记录 HTTP 状态码作为证据，不重试、不猜测 |
| 验收门 | `scripts/wp1226_verify_acceptance.py` | 契约 6 项 acceptance + 2 项结构不变量；jsonschema Draft2020-12 校验信封 |
| 图 | `scripts/wp1226_render_figure.py` | matplotlib Agg，直接从 manifest 渲染，无手抄数字 |
| 单元测试 | `tests/test_wp1226_asset_manifest.py` | 7 项，含**负对照**（篡改 quote / 平移偏移必须被检出）与离线复跑逐字节一致性 |

不复用的既有件：本仓 `schemas/kf_result.v1.schema.json` 原先缺失（其它工作树已有同内容副本，md5 `0491bc4ce09a1fc2f62f015666d38935`）；本单按字节原样补齐该 schema 以便验收门可在本检出内复跑。

## ③ 产出物清单

| 文件 | 要点 |
| --- | --- |
| `docs/kf/wp-1226-01/asset_manifest.json` | 22 资产 / 35 locator / 计数与不变量 / 探测证据 / 3 条观察 |
| `docs/kf/wp-1226-01/kf_result.json` | 提交用结果信封（outputs=`asset_manifest.json`，claims=[]） |
| `docs/kf/wp-1226-01/acceptance.json` | 8 项验收检查的机器结论（全部 PASS） |
| `docs/kf/wp-1226-01/fig1_asset_resolution.png` | 资产解析状态图（本报告 ④ 后附图） |
| `scripts/kf_fetch_1226.py`、`scripts/wp1226_register_assets.py`、`scripts/wp1226_probe_assets.py`、`scripts/wp1226_verify_acceptance.py`、`scripts/wp1226_render_figure.py` | 取源/登记/探测/验收/渲染，一键复跑 |
| `tests/test_wp1226_asset_manifest.py` | 7 项 pytest（含负对照与复现性） |
| `work/wp-1226-01/source/` | 源快照：`report_1226.json`、`report_1226.md`、`probes.json`、`markdown.sha256` |

## ④ 证据定位表（字段 → 原文逐字片段）

下表的「原文片段」列全部是 report 1226 markdown 的**逐字子串**（markdown 类 locator 带字符区间，record 类 locator 带字段名）；逐条回解由 `source_locator_resolvable` 检查覆盖。

| asset_id | kind | locator | 原文片段（逐字） | status |
| --- | --- | --- | --- | --- |
| ast-1226-01 | source_document | markdown[0:46] | `# CII 参考线（IMO MEPC.353(78) G1）独立复核与缺陷修复（m1643）` | resolved |
| ast-1226-02 | record_metadata | record.id | `1226` | resolved |
| ast-1226-03 | figure | record.figures[0].name | `fig1_cii_reference_lines.png` | unresolved |
| ast-1226-04 | figure | record.figures[1].name | `fig2_relative_error.png` | unresolved |
| ast-1226-05 | figure | record.figures[2].name | `fig3_rating_general_cargo.png` | unresolved |
| ast-1226-10 | report_generator | markdown[56:97] | `tools/verify_cii_reference_lines_m1643.py` | unresolved |
| ast-1226-11 | result_data | markdown[127:178] | `artifacts/cii_m1643/cii_reference_verification.json` | unresolved |
| ast-1226-12 | figure_file | markdown[184:232] | `artifacts/cii_m1643/fig1_cii_reference_lines.png` | unresolved |
| ast-1226-13 | figure_file | markdown[235:258] | `fig2_relative_error.png` | unresolved |
| ast-1226-14 | figure_file | markdown[264:293] | `fig3_rating_general_cargo.png` | unresolved |
| ast-1226-15 | test_file | markdown[301:354] | `backend/tests/polar/test_cii_reference_lines_m1643.py` | unresolved |
| ast-1226-16 | source_code | markdown[461:490] | `backend/services/polar/cii.py` | unresolved |
| ast-1226-17 | module_reference | markdown[1288:1299] | `polar.ships` | unresolved |
| ast-1226-18 | symbol_reference | markdown[976:1005] | `constants.CII_REFERENCE_LINES` | unresolved |
| ast-1226-19 | symbol_reference | markdown[1806:1839] | `CII_REFERENCE_LINES_NOT_SUPPORTED` | unresolved |
| ast-1226-20 | symbol_reference | markdown[1599:1634] | `cii.cii_reference_line_invariants()` | unresolved |
| ast-1226-21 | symbol_reference | markdown[647:670] | `verify_cii_ship_types()` | unresolved |
| ast-1226-22 | symbol_reference | markdown[5298:5312] | `_CII_VALID_DWT` | unresolved |
| ast-1226-23 | symbol_reference | markdown[1763:1782] | `NotImplementedError` | unresolved |
| ast-1226-40 | standard_document | markdown[901:930] | `MEPC.353(78) G1 Annex Table 1` | unresolved |
| ast-1226-41 | standard_document | markdown[1126:1141] | `MEPC.353(78) G3` | unresolved |
| ast-1226-42 | standard_document | markdown[1188:1203] | `MEPC.354(78) G4` | unresolved |

## ⑤ 注意点与局限

1. **外部工件的字节不可达（20/22 未解析）**：报告正文点名的生成脚本、结果 JSON、3 张图、测试、源码与符号共 17 项，均未随报告记录附带字节副本；平台存储端点探测 4/4 返回 HTTP 404（`/tensor/reports/1226/figures/<name>`、`/tensor/reports/1226/figures`、`/tensor/artifacts/cii_m1643/cii_reference_verification.json`、`/tensor/reports/1226/attachments`）。登记停在「引用」层面，所有权仍在产出仓（ship-performance-platform）。
2. **图只有元数据**：3 张图在 record 里只声明 `name`+`caption`（无 `png_base64`），caption 均为描述性文字（≠ 文件名），故图注可登记、图内容不可审计。
3. **记录与契约的两处不一致（如实记录，不做协调）**：(a) `record.title` = `CII 参考线（MEPC.353(78) G1）独立复核与缺陷修复（m1643）`，而 markdown H1 = `CII 参考线（IMO MEPC.353(78) G1）独立复核与缺陷修复（m1643）`——H1 多一个研究机构限定词「IMO」，`title_equals_markdown_h1=False`；下游抽取应以 report_id 为主键，不要以标题相等为前提。(b) `record.mission_id` = 1643，而契约写 `mission_id: null`——按观测记录，本包不裁决。
4. **claims 为空是设计而非缺漏**：契约 notes 明确「claims 允许为空数组」，objective 只要求 `register_assets`，且 constraints 禁止 `no_forced_claim_generation`；因此本包不产出任何 claim，也不存在「verified」标记（verification 由平台门计算）。
5. **一次有界观察（不改变判定）**：对本机 `/root/ship-performance-platform` 检出按精确路径检查 7 个被引用工件，7/7 不存在；该目录不是 git 工作副本、无法与报告生成时的版本对齐，故此观察仅作提示，`resolvable=false` 的判定仍以「报告记录无字节副本 + 平台端点 404」为唯一依据。
6. **登记面向主文**：本包不解析表格数值、不复核报告内 24 个锚点或 8 类系数——那是 03/04 工序与独立复核单的职责；本单对报告的任何数字**没有**做正确性背书。
7. **装置依赖**：全部检查在本检出内离线可复跑（`--offline`），唯哈希与 404 探测需要平台在线；离线复跑与在线结果在本单中逐字节一致（`test_manifest_reproducible_from_snapshot`）。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结论 | 证据 |
| --- | --- | --- |
| valid_json | ☑ | 两个 JSON 均 `json.loads` 通过 |
| schema_pass | ☑ | `schemas/kf_result.v1.schema.json`（Draft2020-12）零错误 |
| source_locator_resolvable | ☑ | 35/35 条 locator 逐条回解成功 |
| source_hash_matches | ☑ | 重算 `sha256:d419206bdb3f282d2e2a1ac1f96e972af4438061815e95abba98d8c028e96717` = 契约声明 |
| no_duplicate_ids | ☑ | 22 个 asset_id 唯一；locator 键唯一，无重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | ☑ | claims=[] （vacuous 成立）且 `claims_policy.reason` 非空显式说明 |
| （附加）unresolved_assets_have_reason | ☑ | 20 个 unresolved 资产均带 `unresolved_reason` |
| （附加）reports_touched_single | ☑ | `reports_touched=['1226']`，未读写其它 report_id |

**honest 声明**：无失败项。但需明示两项非失败的性质——(i) 20 个资产 unresolved 是报告记录本身的缺口，不是登记遗漏；(ii) 本包不做 claim 抽取，故下游若需要知识对象须另派 03 工序。

**repro_cmd**（工作树根执行，5 条命令一键复跑）：

```bash
python3 scripts/kf_fetch_1226.py                        # 在线取源 + 锁定 sha256
python3 scripts/wp1226_probe_assets.py                  # 4 个存储端点可解析性探测
python3 scripts/wp1226_register_assets.py               # 生成 asset_manifest.json + kf_result.json
python3 scripts/wp1226_render_figure.py                 # 渲染 fig1_asset_resolution.png
python3 scripts/wp1226_verify_acceptance.py && python3 -m pytest tests/test_wp1226_asset_manifest.py -q
```

图 1：`fig1_asset_resolution.png` — 22 个资产的 locator 数与解析状态（绿=resolved 2 个：源文档与记录元数据；红=unresolved 20 个：3 图 + 17 引用），右列为 locator 的 provenance 分布。

**结果信封（契约要求的唯一 json 代码块，字段结构见 schemas/kf_result.v1.schema.json）**：

```json
{
  "package_id": "wp-1226-01",
  "task_type": "01-asset-registration",
  "report_id": "1226",
  "provenance": {
    "source_hash": "sha256:d419206bdb3f282d2e2a1ac1f96e972af4438061815e95abba98d8c028e96717",
    "source_field": "markdown",
    "producer": "agent/m15527",
    "emitted_at": "2026-11-12T00:55:56+00:00",
    "notes": "source_hash recomputed from the report-1226 markdown bytes fetched over the TensorPlatform API; equals the contract-declared hash sha256:d419206bdb3f282d2e2a1ac1f96e972af4438061815e95abba98d8c028e96717"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-1226-01",
      "task_type": "01-asset-registration",
      "scope": {
        "report_id": "1226",
        "reports_touched": [
          "1226"
        ],
        "registers_assets_only": true,
        "extracts_claims": false,
        "classifies_report_type": false,
        "writes_outside_worktree": false
      },
      "source": {
        "report_id": "1226",
        "source_uri": "tensor://reports/1226",
        "source_field": "markdown",
        "title": "CII 参考线（MEPC.353(78) G1）独立复核与缺陷修复（m1643）",
        "markdown_h1": "CII 参考线（IMO MEPC.353(78) G1）独立复核与缺陷修复（m1643）",
        "title_matches_contract": true,
        "title_equals_markdown_h1": false,
        "scenario_key": "cii_reference_lines_verification",
        "chars": 6045,
        "byte_length_utf8": 8843,
        "sha256": "sha256:d419206bdb3f282d2e2a1ac1f96e972af4438061815e95abba98d8c028e96717",
        "hash_check": {
          "expected": "sha256:d419206bdb3f282d2e2a1ac1f96e972af4438061815e95abba98d8c028e96717",
          "recomputed": "sha256:d419206bdb3f282d2e2a1ac1f96e972af4438061815e95abba98d8c028e96717",
          "match": true
        },
        "chars_check": {
          "expected": 6045,
          "observed": 6045,
          "match": true
        }
      },
      "assets": [
        {
          "asset_id": "ast-1226-01",
          "kind": "source_document",
          "role": "primary_source",
          "name": "report_1226_markdown",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 0,
              "char_end": 46,
              "quote": "# CII 参考线（IMO MEPC.353(78) G1）独立复核与缺陷修复（m1643）",
              "note": "H1 line; whole-document span recorded in content_ref"
            }
          ],
          "content_ref": {
            "source_uri": "tensor://reports/1226",
            "source_field": "markdown",
            "chars": 6045,
            "byte_length_utf8": 8843,
            "sha256": "sha256:d419206bdb3f282d2e2a1ac1f96e972af4438061815e95abba98d8c028e96717"
          },
          "resolvable": true,
          "resolution": "fetched_via_tensor_api",
          "status": "resolved"
        },
        {
          "asset_id": "ast-1226-02",
          "kind": "record_metadata",
          "role": "identification",
          "name": "report_1226_record",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "record",
              "field": "id",
              "value": 1226
            },
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "record",
              "field": "title",
              "value": "CII 参考线（MEPC.353(78) G1）独立复核与缺陷修复（m1643）"
            },
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "record",
              "field": "scenario_key",
              "value": "cii_reference_lines_verification"
            },
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "record",
              "field": "mission_id",
              "value": 1643
            },
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "record",
              "field": "status",
              "value": "published"
            },
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "record",
              "field": "created_by",
              "value": 1
            },
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "record",
              "field": "created_at",
              "value": "2026-11-01T10:05:09.946159+00:00"
            },
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "record",
              "field": "tags",
              "value": [
                "CII",
                "MEPC.353(78)",
                "绿色航行",
                "验证欠账",
                "挖掘缺陷",
                "TensorPlatform"
              ]
            }
          ],
          "values": {
            "id": 1226,
            "title": "CII 参考线（MEPC.353(78) G1）独立复核与缺陷修复（m1643）",
            "scenario_key": "cii_reference_lines_verification",
            "mission_id": 1643,
            "status": "published",
            "created_by": 1,
            "created_at": "2026-11-01T10:05:09.946159+00:00",
            "tags": [
              "CII",
              "MEPC.353(78)",
              "绿色航行",
              "验证欠账",
              "挖掘缺陷",
              "TensorPlatform"
            ]
          },
          "resolvable": true,
          "resolution": "fetched_via_tensor_api",
          "status": "resolved"
        },
        {
          "asset_id": "ast-1226-03",
          "kind": "figure",
          "role": "declared_figure",
          "name": "fig1_cii_reference_lines.png",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "record",
              "field": "figures[0].name",
              "value": "fig1_cii_reference_lines.png"
            },
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "record",
              "field": "figures[0].caption",
              "value": "G1 参考线：公布表（实线）vs 平台取值（空心圆），红色虚线为被否决的旧杂货船指数 c=-1.430"
            }
          ],
          "caption": "G1 参考线：公布表（实线）vs 平台取值（空心圆），红色虚线为被否决的旧杂货船指数 c=-1.430",
          "caption_is_descriptive": true,
          "binary_probe": {
            "path": "/tensor/reports/1226/figures/fig1_cii_reference_lines.png",
            "http_status": 404,
            "bytes": 0,
            "content_type": null
          },
          "resolvable": false,
          "resolution": "declared_in_record_only__figures_inline_payload_absent__store_probe_404",
          "status": "unresolved",
          "unresolved_reason": "record carries only name+caption (no inline bytes / no png_base64); the report store returned HTTP 404 for the figure endpoints, so the PNG bytes named by this asset cannot be fetched, hashed or compared by any downstream package"
        },
        {
          "asset_id": "ast-1226-04",
          "kind": "figure",
          "role": "declared_figure",
          "name": "fig2_relative_error.png",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "record",
              "field": "figures[1].name",
              "value": "fig2_relative_error.png"
            },
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "record",
              "field": "figures[1].caption",
              "value": "各类别指数相对误差（修复前/后，symlog 纵轴）：仅 general_cargo 修复前偏离"
            }
          ],
          "caption": "各类别指数相对误差（修复前/后，symlog 纵轴）：仅 general_cargo 修复前偏离",
          "caption_is_descriptive": true,
          "binary_probe": null,
          "resolvable": false,
          "resolution": "declared_in_record_only__figures_inline_payload_absent__store_probe_404",
          "status": "unresolved",
          "unresolved_reason": "record carries only name+caption (no inline bytes / no png_base64); the report store returned HTTP 404 for the figure endpoints, so the PNG bytes named by this asset cannot be fetched, hashed or compared by any downstream package"
        },
        {
          "asset_id": "ast-1226-05",
          "kind": "figure",
          "role": "declared_figure",
          "name": "fig3_rating_general_cargo.png",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "record",
              "field": "figures[2].name",
              "value": "fig3_rating_general_cargo.png"
            },
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "record",
              "field": "figures[2].caption",
              "value": "20 000 DWT 杂货船航次在 A-E 评级带上的落点：修复前比值 407.7（超出图轴，E），修复后 0.735（A）"
            }
          ],
          "caption": "20 000 DWT 杂货船航次在 A-E 评级带上的落点：修复前比值 407.7（超出图轴，E），修复后 0.735（A）",
          "caption_is_descriptive": true,
          "binary_probe": null,
          "resolvable": false,
          "resolution": "declared_in_record_only__figures_inline_payload_absent__store_probe_404",
          "status": "unresolved",
          "unresolved_reason": "record carries only name+caption (no inline bytes / no png_base64); the report store returned HTTP 404 for the figure endpoints, so the PNG bytes named by this asset cannot be fetched, hashed or compared by any downstream package"
        },
        {
          "asset_id": "ast-1226-10",
          "kind": "report_generator",
          "role": "referenced_external_artifact",
          "name": "tools/verify_cii_reference_lines_m1643.py",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 56,
              "char_end": 97,
              "quote": "tools/verify_cii_reference_lines_m1643.py"
            }
          ],
          "occurrence_count": 1,
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_attached_to_report_record",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text only; no byte-level copy is attached to report 1226 and the platform artifact endpoints probed here returned HTTP 404 — registration stops at the reference, ownership stays with the producing repo",
          "claim_in_text": "全部数字程序化注入，本文件由脚本产物渲染"
        },
        {
          "asset_id": "ast-1226-11",
          "kind": "result_data",
          "role": "referenced_external_artifact",
          "name": "artifacts/cii_m1643/cii_reference_verification.json",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 127,
              "char_end": 178,
              "quote": "artifacts/cii_m1643/cii_reference_verification.json"
            }
          ],
          "occurrence_count": 1,
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_attached_to_report_record",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text only; no byte-level copy is attached to report 1226 and the platform artifact endpoints probed here returned HTTP 404 — registration stops at the reference, ownership stays with the producing repo"
        },
        {
          "asset_id": "ast-1226-12",
          "kind": "figure_file",
          "role": "referenced_external_artifact",
          "name": "artifacts/cii_m1643/fig1_cii_reference_lines.png",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 184,
              "char_end": 232,
              "quote": "artifacts/cii_m1643/fig1_cii_reference_lines.png"
            }
          ],
          "occurrence_count": 1,
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_attached_to_report_record",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text only; no byte-level copy is attached to report 1226 and the platform artifact endpoints probed here returned HTTP 404 — registration stops at the reference, ownership stays with the producing repo"
        },
        {
          "asset_id": "ast-1226-13",
          "kind": "figure_file",
          "role": "referenced_external_artifact",
          "name": "fig2_relative_error.png",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 235,
              "char_end": 258,
              "quote": "fig2_relative_error.png"
            },
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 4832,
              "char_end": 4855,
              "quote": "fig2_relative_error.png"
            }
          ],
          "occurrence_count": 2,
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_attached_to_report_record",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text only; no byte-level copy is attached to report 1226 and the platform artifact endpoints probed here returned HTTP 404 — registration stops at the reference, ownership stays with the producing repo",
          "path_inferred": "artifacts/cii_m1643/fig2_relative_error.png",
          "path_inference_basis": "listed in the same 产物 enumeration directly after `artifacts/cii_m1643/fig1_cii_reference_lines.png`, so the directory is inherited from that entry; the text itself prints only the bare filename"
        },
        {
          "asset_id": "ast-1226-14",
          "kind": "figure_file",
          "role": "referenced_external_artifact",
          "name": "fig3_rating_general_cargo.png",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 264,
              "char_end": 293,
              "quote": "fig3_rating_general_cargo.png"
            },
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 4874,
              "char_end": 4903,
              "quote": "fig3_rating_general_cargo.png"
            }
          ],
          "occurrence_count": 2,
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_attached_to_report_record",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text only; no byte-level copy is attached to report 1226 and the platform artifact endpoints probed here returned HTTP 404 — registration stops at the reference, ownership stays with the producing repo",
          "path_inferred": "artifacts/cii_m1643/fig3_rating_general_cargo.png",
          "path_inference_basis": "same enumeration as fig2_relative_error.png; directory inherited"
        },
        {
          "asset_id": "ast-1226-15",
          "kind": "test_file",
          "role": "referenced_external_artifact",
          "name": "backend/tests/polar/test_cii_reference_lines_m1643.py",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 301,
              "char_end": 354,
              "quote": "backend/tests/polar/test_cii_reference_lines_m1643.py"
            }
          ],
          "occurrence_count": 1,
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_attached_to_report_record",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text only; no byte-level copy is attached to report 1226 and the platform artifact endpoints probed here returned HTTP 404 — registration stops at the reference, ownership stays with the producing repo"
        },
        {
          "asset_id": "ast-1226-16",
          "kind": "source_code",
          "role": "referenced_external_artifact",
          "name": "backend/services/polar/cii.py",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 461,
              "char_end": 490,
              "quote": "backend/services/polar/cii.py"
            }
          ],
          "occurrence_count": 1,
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_attached_to_report_record",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text only; no byte-level copy is attached to report 1226 and the platform artifact endpoints probed here returned HTTP 404 — registration stops at the reference, ownership stays with the producing repo"
        },
        {
          "asset_id": "ast-1226-17",
          "kind": "module_reference",
          "role": "referenced_external_artifact",
          "name": "polar.ships",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 1288,
              "char_end": 1299,
              "quote": "polar.ships"
            }
          ],
          "occurrence_count": 1,
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_attached_to_report_record",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text only; no byte-level copy is attached to report 1226 and the platform artifact endpoints probed here returned HTTP 404 — registration stops at the reference, ownership stays with the producing repo"
        },
        {
          "asset_id": "ast-1226-18",
          "kind": "symbol_reference",
          "role": "referenced_external_artifact",
          "name": "constants.CII_REFERENCE_LINES",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 976,
              "char_end": 1005,
              "quote": "constants.CII_REFERENCE_LINES"
            }
          ],
          "occurrence_count": 1,
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_attached_to_report_record",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text only; no byte-level copy is attached to report 1226 and the platform artifact endpoints probed here returned HTTP 404 — registration stops at the reference, ownership stays with the producing repo"
        },
        {
          "asset_id": "ast-1226-19",
          "kind": "symbol_reference",
          "role": "referenced_external_artifact",
          "name": "CII_REFERENCE_LINES_NOT_SUPPORTED",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 1806,
              "char_end": 1839,
              "quote": "CII_REFERENCE_LINES_NOT_SUPPORTED"
            }
          ],
          "occurrence_count": 1,
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_attached_to_report_record",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text only; no byte-level copy is attached to report 1226 and the platform artifact endpoints probed here returned HTTP 404 — registration stops at the reference, ownership stays with the producing repo"
        },
        {
          "asset_id": "ast-1226-20",
          "kind": "symbol_reference",
          "role": "referenced_external_artifact",
          "name": "cii.cii_reference_line_invariants()",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 1599,
              "char_end": 1634,
              "quote": "cii.cii_reference_line_invariants()"
            }
          ],
          "occurrence_count": 1,
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_attached_to_report_record",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text only; no byte-level copy is attached to report 1226 and the platform artifact endpoints probed here returned HTTP 404 — registration stops at the reference, ownership stays with the producing repo"
        },
        {
          "asset_id": "ast-1226-21",
          "kind": "symbol_reference",
          "role": "referenced_external_artifact",
          "name": "verify_cii_ship_types()",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 647,
              "char_end": 670,
              "quote": "verify_cii_ship_types()"
            }
          ],
          "occurrence_count": 1,
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_attached_to_report_record",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text only; no byte-level copy is attached to report 1226 and the platform artifact endpoints probed here returned HTTP 404 — registration stops at the reference, ownership stays with the producing repo"
        },
        {
          "asset_id": "ast-1226-22",
          "kind": "symbol_reference",
          "role": "referenced_external_artifact",
          "name": "_CII_VALID_DWT",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 5298,
              "char_end": 5312,
              "quote": "_CII_VALID_DWT"
            }
          ],
          "occurrence_count": 1,
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_attached_to_report_record",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text only; no byte-level copy is attached to report 1226 and the platform artifact endpoints probed here returned HTTP 404 — registration stops at the reference, ownership stays with the producing repo"
        },
        {
          "asset_id": "ast-1226-23",
          "kind": "symbol_reference",
          "role": "referenced_external_artifact",
          "name": "NotImplementedError",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 1763,
              "char_end": 1782,
              "quote": "NotImplementedError"
            }
          ],
          "occurrence_count": 1,
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_attached_to_report_record",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text only; no byte-level copy is attached to report 1226 and the platform artifact endpoints probed here returned HTTP 404 — registration stops at the reference, ownership stays with the producing repo"
        },
        {
          "asset_id": "ast-1226-40",
          "kind": "standard_document",
          "role": "cited_external_standard",
          "name": "MEPC.353(78) G1 Annex Table 1",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 901,
              "char_end": 930,
              "quote": "MEPC.353(78) G1 Annex Table 1"
            },
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 5704,
              "char_end": 5733,
              "quote": "MEPC.353(78) G1 Annex Table 1"
            }
          ],
          "occurrence_count": 2,
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_attached_to_report_record",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text only; no byte-level copy is attached to report 1226 and the platform artifact endpoints probed here returned HTTP 404 — registration stops at the reference, ownership stays with the producing repo"
        },
        {
          "asset_id": "ast-1226-41",
          "kind": "standard_document",
          "role": "cited_external_standard",
          "name": "MEPC.353(78) G3",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 1126,
              "char_end": 1141,
              "quote": "MEPC.353(78) G3"
            }
          ],
          "occurrence_count": 1,
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_attached_to_report_record",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text only; no byte-level copy is attached to report 1226 and the platform artifact endpoints probed here returned HTTP 404 — registration stops at the reference, ownership stays with the producing repo"
        },
        {
          "asset_id": "ast-1226-42",
          "kind": "standard_document",
          "role": "cited_external_standard",
          "name": "MEPC.354(78) G4",
          "locators": [
            {
              "source_uri": "tensor://reports/1226",
              "source_field": "markdown",
              "char_start": 1188,
              "char_end": 1203,
              "quote": "MEPC.354(78) G4"
            }
          ],
          "occurrence_count": 1,
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_attached_to_report_record",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text only; no byte-level copy is attached to report 1226 and the platform artifact endpoints probed here returned HTTP 404 — registration stops at the reference, ownership stays with the producing repo"
        }
      ],
      "asset_counts": {
        "assets_total": 22,
        "resolved": 2,
        "unresolved": 20,
        "by_kind": {
          "source_document": 1,
          "record_metadata": 1,
          "figure": 3,
          "report_generator": 1,
          "result_data": 1,
          "figure_file": 3,
          "test_file": 1,
          "source_code": 1,
          "module_reference": 1,
          "symbol_reference": 6,
          "standard_document": 3
        }
      },
      "id_uniqueness": {
        "asset_ids_unique": true,
        "asset_id_count": 22
      },
      "claims_policy": {
        "claims": [],
        "reason": "this work package is asset registration only (objective.register_assets=true, classify_report_type=false); the contract states claims may be an empty array and forbids forced claim generation, so no claim object is emitted and no text is paraphrased or marked verified"
      },
      "probes": [
        {
          "path": "/tensor/reports/1226/figures/fig1_cii_reference_lines.png",
          "http_status": 404,
          "bytes": 0,
          "content_type": null
        },
        {
          "path": "/tensor/reports/1226/figures",
          "http_status": 404,
          "bytes": 0,
          "content_type": null
        },
        {
          "path": "/tensor/artifacts/cii_m1643/cii_reference_verification.json",
          "http_status": 404,
          "bytes": 0,
          "content_type": null
        },
        {
          "path": "/tensor/reports/1226/attachments",
          "http_status": 404,
          "bytes": 0,
          "content_type": null
        }
      ],
      "observations": [
        {
          "id": "obs-title-drift",
          "observation": "record.title differs byte-wise from the markdown H1 title",
          "record_title": "CII 参考线（MEPC.353(78) G1）独立复核与缺陷修复（m1643）",
          "markdown_h1": "CII 参考线（IMO MEPC.353(78) G1）独立复核与缺陷修复（m1643）",
          "impact": "downstream extraction must key on report_id, not on title equality"
        },
        {
          "id": "obs-mission-id",
          "observation": "record.mission_id is present although the package contract declares mission_id: null",
          "record_mission_id": 1643,
          "impact": "recorded as observed only; this package does not reconcile it"
        },
        {
          "id": "obs-truncated-heading-optional",
          "observation": "markdown is a self-contained 5-section report: H1 + §1..§5 headers, no §6 self-check section",
          "section_headers": [
            "## 1. 案例介绍（物理/规范背景）",
            "## 2. 怎么做的（方法与工具链）",
            "## 3. 计算与复核结果",
            "## 4. 注意点与局限",
            "## 5. 误差判定"
          ],
          "impact": "informational; registration does not depend on section coverage"
        }
      ],
      "limitations": [
        "registration only: no claim extraction, no numeric re-verification, no report-type classification — downstream packages own those",
        "verification status is deliberately not set: the platform gate computes it",
        "all referenced artefacts live in the producing repo (ship-performance-platform) and are absent from the report store; their content was not read, hashed or trusted here",
        "figure bytes unavailable → figure content (axes/data) cannot be audited from this report record alone"
      ]
    }
  },
  "claims": []
}
```
