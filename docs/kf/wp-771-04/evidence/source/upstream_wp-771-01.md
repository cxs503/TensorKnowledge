# KF-RESULT wp-771-01 — 报告 771 源资产登记

> 工序：`01-asset-registration` ｜ 报告：`771` ｜ 分支：`agent/m15518`
> 分层=DEM|dem_granular_hopper_beverloo|m ｜ 状态：draft（未做抽取、未做 verification）

## ① 本工序做了什么

只碰 `report_id=771` 这一份报告，完成「源资产登记」一件事实：确认报告与其
markdown 的字节身份（sha256 + 字符数 + UTF-8 字节数），并把报告中可解析/被引用的工件逐条登记成
带定位符的资产条目。**不做抽取、不生成 claim、不标 verified**——这三件属于下游工序与平台门。

登记结果：**10 条资产**，其中 **2 条可解析**
（源文档本体、报告记录元数据），**8 条显式 unresolved**
（3 张声明图 + 5 个正文引用的外部工件），
每条 unresolved 都带 `unresolved_reason`，不做「假装登记成功」。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET $TENSOR_API_BASE/tensor/reports/771`（Bearer=agent 登录 token），只取 `markdown` 字段；
   另落一份逐字节快照 `artifacts/kf/wp-771-01/source_771.md`，供离线复核。
2. **算身份**：对 markdown UTF-8 字节重算 `sha256`，与契约声明的哈希比对：
   `sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559` vs `sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559` → **match=True**；
   字符数 2143 vs 契约 2143 → **match=True**；
   UTF-8 字节数 3623（中文占多字节，故 ≠ 字符数）。
3. **定位符工厂**：所有 markdown 定位符由程序在原文里 `find` 出偏移（`char_start/char_end`），并做
   回读断言 `source[start:end] == quote`——**引文不可手写、不可凭记忆**，找不到直接抛错。共 6 条 markdown 定位符。
4. **附件可达性探测**（不假设）：`GET /tensor/reports/771/figures` → HTTP 404；
   逐张 `GET /tensor/reports/771/figures/<name>` → HTTP {'fig1_beverloo_qbc.png': 404, 'fig2_beverloo_linearity.png': 404, 'fig3_rate_series.png': 404}。据此把图登记为 `unresolved`（只存文件名，不伪称有字节）。
5. **结构门自检**：结果信封按 `schemas/kf_result.v1.schema.json` 用 `jsonschema` 校验；另做 8 项契约自检并落 `selfcheck.json`。
6. **离线可复现测试**：`tests/test_kf_wp771_01_asset_manifest.py` 不联网，仅凭已提交产物重放全部断言（8 项）。

工具链：Python 3.11 + `jsonschema` + `matplotlib`（图 1 由 manifest 计数程序化生成）；无外部数据依赖。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/kf/wp-771-01/asset_manifest.json` | 本工序正式交付物：source 身份块 + 10 条资产 + 计数 + 抽取/verification 显式置否 + 三条注意事项 |
| `artifacts/kf/wp-771-01/kf_result.json` | 结果信封（schemas/kf_result.v1 全字段通过），`claims: []`，`provenance.source_hash` = 重算值 |
| `artifacts/kf/wp-771-01/source_771.md` | 报告 771 markdown 逐字节快照（3623 B），供离线定位符复核 |
| `artifacts/kf/wp-771-01/selfcheck.json` | 8 项 acceptance 自检明细（accepted=true） |
| `artifacts/kf/wp-771-01/fig1_asset_inventory.png` | 图 1：按 kind 的资产登记分布（可解析/未解析堆叠），计数全部来自 manifest |
| `scripts/kf_wp771_01_register_assets.py` | 一键复跑：取原文→验哈希→建定位符→探测附件→自检→落三件产物 |
| `scripts/kf_wp771_01_emit_report.py` | 生成本报告（数字/引文全部程序化注入）+ 图 1 |
| `tests/test_kf_wp771_01_asset_manifest.py` | 8 个离线断言：schema、哈希、定位符逐字、ID 唯一、单报告范围、零抽取/零自验、图登记 |

一键复跑：

`TENSOR_API_BASE=$TENSOR_API_BASE TENSOR_AGENT_USER=$TENSOR_AGENT_USER TENSOR_AGENT_PASS=$TENSOR_AGENT_PASS python3 scripts/kf_wp771_01_register_assets.py && python3 -m pytest tests/test_kf_wp771_01_asset_manifest.py -q`

## ④ 证据定位表（claim/字段 → 原文引文，逐字）

源文件：`tensor://reports/771`，字段 `markdown`，sha256=`sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559`，chars=2143。

| asset_id | kind | name | resolvable | locator (verbatim quote / record field) |
|---|---|---|---|---|
| ast-771-01 | source_document | `report_771_markdown` | yes | md[0:43] 「# 料仓卸料(Beverloo)+休止角双案例 —— TensorDEM 跨方法吸收线」 |
| ast-771-02 | record_metadata | `report_771_record` | yes | record.id=771 |
| ast-771-10 | figure | `fig1_beverloo_qbc.png` | no | record.figures[0].name=fig1_beverloo_qbc.png |
| ast-771-11 | figure | `fig2_beverloo_linearity.png` | no | record.figures[1].name=fig2_beverloo_linearity.png |
| ast-771-12 | figure | `fig3_rate_series.png` | no | record.figures[2].name=fig3_rate_series.png |
| ast-771-20 | source_code | `src/tensordem/granular_dem.py` | no | md[482:513] 「src/tensordem/granular_dem.py」 |
| ast-771-21 | example_script | `examples/hopper_beverloo_case.py` | no | md[516:550] 「examples/hopper_beverloo_case.py」 |
| ast-771-22 | report_generator | `hopper_beverloo_report.py` | no | md[553:580] 「hopper_beverloo_report.py」 |
| ast-771-23 | data_artifact_glob | `outputs/*.json` | no | md[590:604] 「outputs/*.json」 |
| ast-771-24 | case_markdown | `CASE.md` | no | md[608:615] 「CASE.md」 |

图 1 与上表同源（manifest 计数），无手工数字。

## ⑤ 注意点与局限

- record.mission_id=813 while the package contract declares mission_id: null; recorded as observed, not reconciled by this package
- all figure captions equal their filenames, so figure content cannot be identified without the binary
- markdown says figures are embedded ('见图内嵌') and that all numbers are injected programmatically, but neither figure bytes nor outputs/*.json are attached to this report record
- **10 条里 8 条 unresolved 是事实而非瑕疵**：报告 771 的图与代码链并未随记录附字节，登记只能停在「引用存在」这一层；下游若需内容，必须回到产出仓库（TensorDEM）按路径取，不能从本 manifest 推断内容。
- **登记 ≠ 验证**：manifest 里没有任何 `verified` 标记，`verification.performed=false`，verification 由平台门计算，本工序无权也无意代填。
- **零抽取**：`extraction.performed=false`、`claims_registered=0`。报告里的 Beverloo 数值、AOR 失败结论等一个字都没进入本产物，避免把「登记」偷偷做成「抽取」。
- **schema 文件来源**：本检出原本缺 `schemas/kf_result.v1.schema.json`，为让 schema 门可执行，从同平台兄弟检出取了一份逐字节副本（sha256=`170dba8b0b5d54012490aaadc0b68647a9520ecb869e9d03f873afb99b74c076`）；若上游另有权威版本，以权威版为准，本工序不主张该文件的所有权。
- **附件探测是单次探测**：HTTP 404 只能说明「本次探测时该端点无字节返回」，不等于永久不存在；端点语义（`figures` 列表接口不存在）亦已在 manifest 里记录原样状态码。
- **范围**：仅 `report_id=771`；本工序未读、未写任何其它 report_id。

## ⑥ 自检：逐条对照 acceptance（honest）

- [x] `valid_json` — "manifest serialised with json.dumps"
- [x] `schema_pass` — "envelope validates against schemas/kf_result.v1.schema.json"
- [x] `source_locator_resolvable` — {"markdown_locators": 6, "unresolved": []}
- [x] `source_hash_matches` — {"expected": "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559", "recomputed": "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559", "ma
- [x] `no_duplicate_ids` — []
- [x] `all_claims_have_evidence_or_explicit_unresolved_status` — "zero claims registered by this package (registration only)"
- [x] `every_asset_has_locator` — "each asset carries >=1 locator"
- [x] `unresolved_assets_have_reason` — 8

- 契约五项：`valid_json` ✓ ｜ `schema_pass` ✓ ｜ `source_locator_resolvable` ✓（6 条 markdown 定位符全部逐字回读通过，record 定位符全部取自 API 返回字段）｜ `source_hash_matches` ✓（契约哈希与重算哈希逐字节一致）｜ `no_duplicate_ids` ✓（10 个 asset_id 无重复）｜ `all_claims_have_evidence_or_explicit_unresolved_status` ✓（claims 为空数组，合法完整；8 条 unresolved 资产均带原因）。
- 失败项：**无**。若按「附件必须可解析」的更高标准衡量，则 8 条 unresolved 属**未完成项**——如实登记为 unresolved，不粉饰为成功。

## ⑦ 误差判定（本工序无物理量，声明口径）

- 唯一可比对的数值量=字节身份：契约声明 `sha256:c9ba...6559` 与实际重算 `sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559` → **逐字节一致，差异 0 bit（0%）**；字符数 2143 vs 2143 → **0%**。
- 结论：**两个可比对量均 <3% 判据（实际为 0%）**；本工序不产生任何物理量（流率/休止角等），故不存在与实验或解析解的误差比较项，不在此处冒充精度结论。
- 明确不做的判定：Beverloo 硬门是否通过、AOR 是否有效——这些是报告 771 自身的 honest-FAIL 内容，本工序只登记其存在，不重算、不复述数值。

## 附：结果信封（唯一 JSON 块，本工序唯一结果信道）

```json
{
  "package_id": "wp-771-01",
  "task_type": "01-asset-registration",
  "report_id": "771",
  "provenance": {
    "source_hash": "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559",
    "source_field": "markdown",
    "producer": "agent/m15518",
    "emitted_at": "2026-11-12T00:48:41+00:00",
    "notes": "source_hash recomputed from report 771 markdown bytes fetched over the TensorPlatform API; matches the contract-declared hash"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-771-01",
      "task_type": "01-asset-registration",
      "scope": {
        "report_id": "771",
        "reports_touched": [
          "771"
        ]
      },
      "source": {
        "report_id": "771",
        "source_uri": "tensor://reports/771",
        "source_field": "markdown",
        "title": "TensorDEM：料仓卸料 Beverloo 标度复现 + 休止角（honest 部分失败）",
        "scenario_key": "dem_granular_hopper_beverloo",
        "chars": 2143,
        "byte_length_utf8": 3623,
        "sha256": "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559",
        "hash_check": {
          "expected": "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559",
          "recomputed": "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559",
          "match": true
        },
        "chars_check": {
          "expected": 2143,
          "observed": 2143,
          "match": true
        }
      },
      "assets": [
        {
          "asset_id": "ast-771-01",
          "kind": "source_document",
          "role": "primary_source",
          "name": "report_771_markdown",
          "locators": [
            {
              "source_uri": "tensor://reports/771",
              "source_field": "markdown",
              "char_start": 0,
              "char_end": 43,
              "quote": "# 料仓卸料(Beverloo)+休止角双案例 —— TensorDEM 跨方法吸收线",
              "note": "first line of markdown; whole-document span is recorded in content_ref"
            }
          ],
          "content_ref": {
            "source_uri": "tensor://reports/771",
            "source_field": "markdown",
            "chars": 2143,
            "sha256": "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559"
          },
          "resolvable": true,
          "resolution": "fetched_via_tensor_api",
          "byte_length_utf8": 3623
        },
        {
          "asset_id": "ast-771-02",
          "kind": "record_metadata",
          "role": "identification",
          "name": "report_771_record",
          "locators": [
            {
              "source_uri": "tensor://reports/771",
              "source_field": "record",
              "field": "id",
              "value": 771
            },
            {
              "source_uri": "tensor://reports/771",
              "source_field": "record",
              "field": "title",
              "value": "TensorDEM：料仓卸料 Beverloo 标度复现 + 休止角（honest 部分失败）"
            },
            {
              "source_uri": "tensor://reports/771",
              "source_field": "record",
              "field": "scenario_key",
              "value": "dem_granular_hopper_beverloo"
            }
          ],
          "values": {
            "report_id": "771",
            "title": "TensorDEM：料仓卸料 Beverloo 标度复现 + 休止角（honest 部分失败）",
            "scenario_key": "dem_granular_hopper_beverloo",
            "status": "published",
            "tags": [
              "DEM",
              "Beverloo",
              "silo discharge",
              "angle of repose",
              "verification",
              "honest-fail"
            ],
            "mission_id_observed": 813,
            "created_by": 1,
            "created_at": "2026-10-31T16:46:24.435762+00:00"
          },
          "resolvable": true,
          "resolution": "record_fields_returned_by_tensor_api"
        },
        {
          "asset_id": "ast-771-10",
          "kind": "figure",
          "role": "declared_figure",
          "name": "fig1_beverloo_qbc.png",
          "locators": [
            {
              "source_uri": "tensor://reports/771",
              "source_field": "record",
              "field": "figures[0].name",
              "value": "fig1_beverloo_qbc.png"
            }
          ],
          "caption": "fig1_beverloo_qbc.png",
          "caption_equals_name": true,
          "resolvable": false,
          "resolution": "declared_in_record_only__binary_fetch_http_404",
          "status": "unresolved",
          "unresolved_reason": "figure bytes are not retrievable from the report store; only the filename is declared, and caption duplicates the filename so it carries no independent description"
        },
        {
          "asset_id": "ast-771-11",
          "kind": "figure",
          "role": "declared_figure",
          "name": "fig2_beverloo_linearity.png",
          "locators": [
            {
              "source_uri": "tensor://reports/771",
              "source_field": "record",
              "field": "figures[1].name",
              "value": "fig2_beverloo_linearity.png"
            }
          ],
          "caption": "fig2_beverloo_linearity.png",
          "caption_equals_name": true,
          "resolvable": false,
          "resolution": "declared_in_record_only__binary_fetch_http_404",
          "status": "unresolved",
          "unresolved_reason": "figure bytes are not retrievable from the report store; only the filename is declared, and caption duplicates the filename so it carries no independent description"
        },
        {
          "asset_id": "ast-771-12",
          "kind": "figure",
          "role": "declared_figure",
          "name": "fig3_rate_series.png",
          "locators": [
            {
              "source_uri": "tensor://reports/771",
              "source_field": "record",
              "field": "figures[2].name",
              "value": "fig3_rate_series.png"
            }
          ],
          "caption": "fig3_rate_series.png",
          "caption_equals_name": true,
          "resolvable": false,
          "resolution": "declared_in_record_only__binary_fetch_http_404",
          "status": "unresolved",
          "unresolved_reason": "figure bytes are not retrievable from the report store; only the filename is declared, and caption duplicates the filename so it carries no independent description"
        },
        {
          "asset_id": "ast-771-20",
          "kind": "source_code",
          "role": "referenced_external_artifact",
          "name": "src/tensordem/granular_dem.py",
          "locators": [
            {
              "source_uri": "tensor://reports/771",
              "source_field": "markdown",
              "char_start": 482,
              "char_end": 513,
              "quote": "`src/tensordem/granular_dem.py`",
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "artifact is named inside the report text but no byte-level copy is attached to report 771; ownership lies with the producing repo, so registration stops at the reference"
        },
        {
          "asset_id": "ast-771-21",
          "kind": "example_script",
          "role": "referenced_external_artifact",
          "name": "examples/hopper_beverloo_case.py",
          "locators": [
            {
              "source_uri": "tensor://reports/771",
              "source_field": "markdown",
              "char_start": 516,
              "char_end": 550,
              "quote": "`examples/hopper_beverloo_case.py`",
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "artifact is named inside the report text but no byte-level copy is attached to report 771; ownership lies with the producing repo, so registration stops at the reference"
        },
        {
          "asset_id": "ast-771-22",
          "kind": "report_generator",
          "role": "referenced_external_artifact",
          "name": "hopper_beverloo_report.py",
          "locators": [
            {
              "source_uri": "tensor://reports/771",
              "source_field": "markdown",
              "char_start": 553,
              "char_end": 580,
              "quote": "`hopper_beverloo_report.py`",
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "artifact is named inside the report text but no byte-level copy is attached to report 771; ownership lies with the producing repo, so registration stops at the reference"
        },
        {
          "asset_id": "ast-771-23",
          "kind": "data_artifact_glob",
          "role": "referenced_external_artifact",
          "name": "outputs/*.json",
          "locators": [
            {
              "source_uri": "tensor://reports/771",
              "source_field": "markdown",
              "char_start": 590,
              "char_end": 604,
              "quote": "outputs/*.json",
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "artifact is named inside the report text but no byte-level copy is attached to report 771; ownership lies with the producing repo, so registration stops at the reference"
        },
        {
          "asset_id": "ast-771-24",
          "kind": "case_markdown",
          "role": "referenced_external_artifact",
          "name": "CASE.md",
          "locators": [
            {
              "source_uri": "tensor://reports/771",
              "source_field": "markdown",
              "char_start": 608,
              "char_end": 615,
              "quote": "CASE.md",
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "artifact is named inside the report text but no byte-level copy is attached to report 771; ownership lies with the producing repo, so registration stops at the reference"
        }
      ],
      "counts": {
        "total": 10,
        "resolvable": 2,
        "unresolved": 8,
        "by_kind": {
          "source_document": 1,
          "record_metadata": 1,
          "figure": 3,
          "source_code": 1,
          "example_script": 1,
          "report_generator": 1,
          "data_artifact_glob": 1,
          "case_markdown": 1
        },
        "duplicate_asset_ids": []
      },
      "extraction": {
        "performed": false,
        "reason": "contract objective is register_assets only (classify_report_type false); extraction belongs to a separate work package"
      },
      "claims_registered": 0,
      "verification": {
        "performed": false,
        "reason": "verification status is computed by the platform gate, never self-assigned"
      },
      "figure_probe": {
        "figures_list_called": "http://127.0.0.1:8010/api/v1/tensor/reports/771/figures",
        "figures_list_http_status": 404,
        "binary_status": {
          "fig1_beverloo_qbc.png": 404,
          "fig2_beverloo_linearity.png": 404,
          "fig3_rate_series.png": 404
        }
      },
      "notes": [
        "record.mission_id=813 while the package contract declares mission_id: null; recorded as observed, not reconciled by this package",
        "all figure captions equal their filenames, so figure content cannot be identified without the binary",
        "markdown says figures are embedded ('见图内嵌') and that all numbers are injected programmatically, but neither figure bytes nor outputs/*.json are attached to this report record"
      ]
    }
  },
  "claims": []
}
```

图 1：fig1_asset_inventory.png — 报告 771 资产登记分布（横轴=条目数，绿=可解析，灰=显式 unresolved；计数由 manifest 程序化注入，零手抄）。
