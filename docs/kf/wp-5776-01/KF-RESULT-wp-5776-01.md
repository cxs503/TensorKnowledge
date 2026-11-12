# KF-RESULT wp-5776-01

工作包 `wp-5776-01`（task_type=`01-asset-registration`，lane C）· 报告 `report_id=5776` · 标题 *Ice Floe Drift DEM-LBM Coupled Benchmark: Analytical Anchor for Two-Phase Coupling Verification* · scenario_key `IN12-S7-ice-floe-drift-dem-lbm`

> 边界声明：本工序只登记 report_id=5776 的源资产与定位符；不抽取 claim、不改写上游产物、不把任何结论标成 verified（verification 由平台门计算）。

## ① 本工序做了什么

1. 通过平台接口 `GET {base}/tensor/reports/5776` 取回 markdown（Bearer token 由 `TENSOR_AGENT_USER/PASS` 换得），本地副本落 `runs/wp-5776-01/report_5776.md`，并钉死字节指纹：`sha256:49089e9b193af49f9ffcf4f35b8a82b6f4deec5da07edc8e654fc7902385c04f`，`4950` 字符 / `4990` 字节 UTF-8。该指纹与工作包契约 `source_hash` 逐位一致（独立重算）。
2. 扫描 markdown 中全部可解析附件/工件引用，登记 **17 个资产**：analytical_expression×1、data_artifact_reference×1、document_reference×1、figure_attachment×3、inline_table×5、parameter_block×1、reproducibility_record×1、source_code_reference×3、verification_record×1。
3. 为每个资产建立 **char_span 定位符**（起止字符偏移 + 起止行号 + 逐字引文），引文由源码行区间切片得到而非重打，故 `md[start:end] == quote` 且 `md.count(quote)==1` 属构造性成立。
4. 产出 `asset_manifest.json`（登记结果主体）与 `kf_result.wp-5776-01.json`（kf_result.v1 信封），claims 为空数组——本工序 objective 只要求 `register_assets`。
5. 附带一次**自洽性算术审计**（`runs/wp-5776-01/consistency_check.json`）：从原文解析 ρ_w/ρ_i 与 9 例扫掠表，用报告**自己的**闭式重算锚点，量化表格列与闭式的相对偏差。此项明确**不是**平台验证，也不构成物理/实验对标。

## ② 怎么做的（步骤 / 工具 / 关键设置）

| 步骤 | 工具 | 关键设置 |
|---|---|---|
| 取源 + 钉指纹 | `scripts/kf/fetch_report_5776.py` | 凭据只走环境变量；零 `artifacts/**`；落 `runs/wp-5776-01/report_5776.{json,md}` |
| 资产登记 | `scripts/kf/build_asset_manifest_5776.py build` | 行区间→引文切片→字符偏移；每句 `count==1` 硬断言，重复即 `SystemExit` |
| 信封封装 | 同上 `result` | `kf_result.v1` 顶层只留 schema 允许的 6 键（`additionalProperties:false`） |
| 独立复核 | 同上 `verify` | **重新拉取** markdown 再算哈希、重解析全部 locator；输出 `verification.json` |
| 自洽审计 | `scripts/kf/consistency_check_5776.py` | 正则解析原文参数与表格，零手抄 |
| 出图 | `scripts/kf/figures_5776.py` | matplotlib Agg；图数据直接读 manifest / consistency json |
| 回归 | `tests/test_kf_wp5776_01.py` | 15 条离线断言（不联网/不连库），覆盖哈希、locator、schema、计数、审计可复算 |

关键设置：`source_field=markdown`；`hash_alg=sha256`（对 UTF-8 字节，非字符）；`verification_status=not_verified`；`claims=[]` 且写 `claims_note` 说明理由。

## ③ 产出物清单（输出文件 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-5776-01/asset_manifest.json` | 登记主体：17 资产 / 9 类 / sha256=253e4e5c2e6a05e2… |
| `docs/kf/wp-5776-01/kf_result.wp-5776-01.json` | kf_result.v1 信封，`outputs["asset_manifest.json"]` 内联 manifest；sha256=134676fb25bd23de… |
| `docs/kf/wp-5776-01/verification.json` | 校验判决：`all_pass=True`，8 项逐条明细 |
| `docs/kf/wp-5776-01/asset_manifest.v1_5776.schema.json` | 本包 pin 的 manifest schema（report/package 用 const 锁死） |
| `docs/kf/wp-5776-01/kf_result.v1.schema.json` | 本工作树缺该 schema 的 pin 副本（sha256 记在 limitations 中） |
| `docs/kf/wp-5776-01/fig1_asset_inventory.png` | 资产按类 × 解析状态的库存图 |
| `docs/kf/wp-5776-01/fig2_consistency.png` | 9 例表列 vs 闭式重算的相对偏差（对数轴，含 3% 判据线） |
| `runs/wp-5776-01/report_5776.md` / `.json` | 源副本与原始 API 载荷（复核用，可离线重放） |
| `runs/wp-5776-01/consistency_check.json` | 自洽审计明细：factor=1.067187，9 行逐例偏差 |
| `scripts/kf/{fetch,build_asset_manifest,consistency_check,figures}_5776.py` | 取源/登记/审计/出图，一键可复跑 |
| `tests/test_kf_wp5776_01.py` | 15 条离线验收断言 |

资产分类分布：analytical_expression=1，data_artifact_reference=1，document_reference=1，figure_attachment=3，inline_table=5，parameter_block=1，reproducibility_record=1，source_code_reference=3，verification_record=1；解析分布：referenced_unresolved=8，resolved_in_source=9。

## ④ 证据定位表（资产 → 原文引文片段）

引文为行区间切片，表中仅做长度截断展示（`…` 表示截断，`⏎` 表示换行）；**完整逐字引文**见 `asset_manifest.json` 的 `assets[].locator.quote`，其 `start_char/end_char/start_line/end_line` 可反查原文。

| asset_id | 类别 | 解析 | 行区间 | 原文引文片段 |
|---|---|---|---|---|
| A01 | figure_attachment | referenced_unresolved | 82 | `![Ice floe drift benchmark: ice floe drift time series](attachme …` |
| A02 | figure_attachment | referenced_unresolved | 86 | `![Ice floe drift benchmark: ice floe drift parameter sweep](atta …` |
| A03 | figure_attachment | referenced_unresolved | 90 | `![Ice floe drift benchmark: ice floe drift error distribution](a …` |
| A04 | source_code_reference | referenced_unresolved | 122 | «- `src/tensordem/ice_floe_drift.py` (13.9 KB) - Core module» |
| A05 | source_code_reference | referenced_unresolved | 123 | «- `tests/test_ice_floe_drift.py` (8.8 KB) - 21 pytest tests (all …» |
| A06 | source_code_reference | referenced_unresolved | 124 | «- `scripts/run_ice_floe_drift_benchmark.py` (8.5 KB) - Benchmark …» |
| A07 | document_reference | referenced_unresolved | 125 | «- `docs/ice_floe_drift_dem_lbm/README.md` (14.7 KB) - Documentat …» |
| A08 | data_artifact_reference | referenced_unresolved | 126 | «- `docs/ice_floe_drift_dem_lbm/ice_floe_drift_results.json` - Re …» |
| A09 | verification_record | resolved_in_source | 130-133 | «```bash ⏎ $ pytest tests/test_ice_floe_drift.py -v ⏎ =========== …» |
| A10 | reproducibility_record | resolved_in_source | 136-140 | «```bash ⏎ cd /root/tp-agent/work/m5068 ⏎ PYTHONPATH=src python3  …» |
| A11 | analytical_expression | resolved_in_source | 13-16 | «``` ⏎ U_drift = U_current · √(ρ_w/ρ_i) · √(C_D_water/C_D_ice) ⏎  …» |
| A12 | parameter_block | resolved_in_source | 7-10 | `**Geometry:** ⏎ - Ice floe: Circular cylinder, D=1m (baseline),  …` |
| A13 | inline_table | resolved_in_source | 37-40 | `\| Quantity \| Analytical \| DEM-LBM \| Error \| ⏎ \|----------\ …` |
| A14 | inline_table | resolved_in_source | 44-54 | `\| U_current [m/s] \| D [m] \| U_analytical [m/s] \| U_sim [m/s] …` |
| A15 | inline_table | resolved_in_source | 64-66 | `\| Test \| Expected \| Actual \| Result \| ⏎ \|------\|--------- …` |
| A16 | inline_table | resolved_in_source | 70-76 | `\| Force \| Value [N] \| ⏎ \|-------\|-----------\| ⏎ \| Driving …` |
| A17 | inline_table | resolved_in_source | 110-115 | `\| Metric \| Value \| Threshold \| Result \| ⏎ \|--------\|----- …` |

自洽审计关键量（全部由 `consistency_check.json` 注入）：

| 量 | 值 | 出处 |
|---|---|---|
| ρ_w / ρ_i | 1025 / 900 kg/m³ | 原文「Geometry」段解析 |
| 放大因子 √(ρ_w/ρ_i) | 1.067187 | 由上式重算 |
| 基准锚 U_anchor（U=1 m/s） | 1.0672 m/s | 重算；原文闭式写 1.0672 m/s |
| 表格 U_analytical 列最大相对偏差 | 0.0012% | 9 例逐行 |
| 表格 U_sim 列最大相对偏差 | 0.0082% | 9 例逐行 |

## ⑤ 注意点与局限

1. Registration only: no text extraction, no claim generation, no verified marks.
2. Figure assets are referenced, not materialised: the platform exposes figure name/caption but no PNG bytes and no artifact endpoint exists, so A01-A03 stay referenced_unresolved.
3. A04-A08 are the report's own audit-trail paths; they live in the report's worktree (/root/tp-agent/work/m5068), outside this delivery worktree, so their existence is not validated here.
4. Report self-reported numbers are registered as text spans, not re-derived here; the purely arithmetic consistency audit of the sweep table against the report's own closed form lives in runs/wp-5776-01/consistency_check.json (scripts/kf/consistency_check_5776.py) and is explicitly NOT a platform verification.
5. The audit-trail line `- 3 PNG figures (time series, parameter sweep, error distribution)` (line 127) is a collective restatement of A01-A03 and is deliberately not registered as a separate asset.
6. Schemas: this worktree has no schemas/kf_result.v1.schema.json, so a pinned copy (sha256=170dba8b0b5d54012490aaadc0b68647a9520ecb869e9d03f873afb99b74c076, taken from sibling worktree m15506) sits at docs/kf/wp-5776-01/kf_result.v1.schema.json and docs/kf/wp-5776-01/asset_manifest.v1_5776.schema.json pins the manifest shape; if the platform-side schema differs, the platform gate wins and this artifact must be revised.

额外观察（如实记录，不作结论）：

- 报告正文自评 `Evidence level: REAL`、`all cases < 0.01% error`，但 9 例误差列**全部打印为 0.00**，与「<0.01%」自评相比，表格分辨率不足以支撑该量级措辞；本工序只登记不做判级，此处留痕给下游评审。
- 报告 §5 自承 `The model predicts U_drift > U_current, which is unphysical for real floes`——锚点构造本身是验证用途，不能读成冰漂物理结论。
- 3 张图在 markdown 中为 `attachment:` URI，平台 `figures[]` 只有 name/caption，`/tensor/reports/5776/artifacts`、`/tensor/artifacts?report_id=5776` 均 404，故 A01-A03 只能 `referenced_unresolved`（字节不可得，绝不假设）。
- 审计轨迹中 5 个路径属报告自己的工作树（`/root/tp-agent/work/m5068`），不在本交付工作树内，其存在性与内容本工序**未**校验。

## ⑥ 自检：逐条对照 acceptance

| acceptance | 结果 | 证据 |
|---|---|---|
| `valid_json` | ✅ | `json.loads OK on docs/kf/wp-5776-01/asset_manifest.json` |
| `schema_pass` | ✅ | `validated against docs/kf/wp-5776-01/asset_manifest.v1_5776.schema.json (pinned copy of asset_manifest.v1 with …` |
| `source_locator_resolvable` | ✅ | `checked 17 char_span locators (span==quote, unique, line<->char agreement); failing=[]` |
| `source_hash_matches` | ✅ | `recomputed=49089e9b193af49f9ffcf4f35b8a82b6f4deec5da07edc8e654fc7902385c04f declared=49089e9b193af49f9ffcf4f35 …` |
| `no_duplicate_ids` | ✅ | `assets=17 unique=17 first=A01 last=A17` |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✅ | `claims=0 violating=0 (empty array is legal per contract notes: register_assets only)` |
| `kf_result_envelope_schema_pass` | ✅ | `validated docs/kf/wp-5776-01/kf_result.wp-5776-01.json against docs/kf/wp-5776-01/kf_result.v1.schema.json; er …` |
| `result_block_embedded_once_in_delivery_markdown` | ✅ | `KF-RESULT-wp-5776-01.md carries the kf_result JSON as its single fenced json block; errors=[]` |

补充自检（超出机器 acceptance 的自觉项）：

- ✅ 零手抄：所有引文经 `md[start:end]==quote` 反查；报告中的数字全部由 json 注入。
- ✅ 边界：只触 report_id=5776；`tests/test_kf_wp5776_01.py::test_work_package_does_not_reach_other_reports` 断言产物中不出现其它 wp 编号。
- ✅ 未标 verified：`provenance.verification_status = not_verified`，claims 空。
- ⚠ 未做（honest gap）：未复核 DEM-LBM 求解器是否真实存在、未复跑 21 条 pytest、未验证附件 PNG 内容——三者均需报告原工作树 m5068，超出本工作包边界。
- ⚠ 未做：`schemas/kf_result.v1.schema.json` 在本工作树缺失，本包用 pin 副本（见局限③），若平台侧 schema 有异，以平台门为准。

结论：acceptance 7 项机器检查 **全部通过**（`verification.json: all_pass=True`），无粉饰项；上述两条 ⚠ 为范围外未做项，已如实标注。

## repro_cmd（一键复跑）

```bash
cd <worktree>   # 本仓库检出根
python3 scripts/kf/fetch_report_5776.py                 # 取源 + 钉 sha256
python3 scripts/kf/build_asset_manifest_5776.py build result   # 登记 + 封装信封
python3 scripts/kf/consistency_check_5776.py            # 自洽算术审计（非平台验证）
python3 scripts/kf/figures_5776.py                      # fig1/fig2
python3 scripts/kf/build_asset_manifest_5776.py verify  # 独立复核 7 项 acceptance
python3 -m pytest tests/test_kf_wp5776_01.py -q         # 15 条离线断言
python3 scripts/kf/render_result_report_5776.py         # 重渲染本报告
```

## 结果（kf_result.v1）

```json
{
  "package_id": "wp-5776-01",
  "task_type": "01-asset-registration",
  "report_id": "5776",
  "provenance": {
    "source_hash": "sha256:49089e9b193af49f9ffcf4f35b8a82b6f4deec5da07edc8e654fc7902385c04f",
    "source_field": "markdown",
    "source_uri": "tensor://reports/5776",
    "producer": "scripts/kf/build_asset_manifest_5776.py",
    "emitted_at": "2026-11-12T01:25:03.611870+00:00",
    "notes": "asset registration for report 5776 only: 17 assets, claims=[] by contract (register_assets only), nothing marked verified; verification is platform-gated."
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-5776-01",
      "task_type": "01-asset-registration",
      "report_id": "5776",
      "provenance": {
        "source_uri": "tensor://reports/5776",
        "source_field": "markdown",
        "hash_alg": "sha256",
        "source_hash": "sha256:49089e9b193af49f9ffcf4f35b8a82b6f4deec5da07edc8e654fc7902385c04f",
        "chars": 4950,
        "bytes_utf8": 4990,
        "title": "Ice Floe Drift DEM-LBM Coupled Benchmark: Analytical Anchor for Two-Phase Coupling Verification",
        "scenario_key": "IN12-S7-ice-floe-drift-dem-lbm",
        "lane": "C",
        "contract_version": "1.0",
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/5776",
        "retrieved_at": "2026-11-12T01:25:03.610128+00:00",
        "local_copy": "runs/wp-5776-01/report_5776.md",
        "platform_figures": [
          {
            "index": 0,
            "name": "ice_floe_drift_time_series.png",
            "caption": "Ice floe drift benchmark: ice floe drift time series",
            "bytes_available": false
          },
          {
            "index": 1,
            "name": "ice_floe_drift_parameter_sweep.png",
            "caption": "Ice floe drift benchmark: ice floe drift parameter sweep",
            "bytes_available": false
          },
          {
            "index": 2,
            "name": "ice_floe_drift_error_distribution.png",
            "caption": "Ice floe drift benchmark: ice floe drift error distribution",
            "bytes_available": false
          }
        ],
        "platform_tags": [
          "DEM-LBM",
          "two-phase",
          "ice-water",
          "coupling",
          "analytical-anchor",
          "verification",
          "ice-floe-drift"
        ],
        "platform_status": "published",
        "platform_mission_id": 5068,
        "generator": "scripts/kf/build_asset_manifest_5776.py",
        "verifier": "scripts/kf/build_asset_manifest_5776.py verify",
        "verification_status": "not_verified"
      },
      "counts": {
        "assets": 17,
        "by_class": {
          "figure_attachment": 3,
          "source_code_reference": 3,
          "document_reference": 1,
          "data_artifact_reference": 1,
          "verification_record": 1,
          "reproducibility_record": 1,
          "analytical_expression": 1,
          "parameter_block": 1,
          "inline_table": 5
        },
        "by_resolution": {
          "referenced_unresolved": 8,
          "resolved_in_source": 9
        },
        "resolved_in_source": 9,
        "referenced_unresolved": 8,
        "declared_absent": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "figure_attachment",
          "label": "Figure 1 — drift time series PNG",
          "in_report_section": "## 4. Results Figures / ### Figure 1",
          "locator": {
            "method": "char_span",
            "start_char": 2418,
            "end_char": 2516,
            "start_line": 82,
            "end_line": 82,
            "quote": "![Ice floe drift benchmark: ice floe drift time series](attachment:ice_floe_drift_time_series.png)",
            "unique": true,
            "encoding": "utf-8"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "attachment_uri_materialisation",
            "result": "unresolved"
          },
          "note": "Markdown image uses an `attachment:ice_floe_drift_time_series.png` URI; the platform reports `figures[0]` with name='ice_floe_drift_time_series.png' and caption='Ice floe drift benchmark: ice floe drift time series' but exposes no PNG bytes (GET /tensor/reports/5776/artifacts and /tensor/artifacts?report_id=5776 both return 404), and no such PNG exists in this worktree — so the asset is registered by reference only, never assumed.",
          "platform_metadata": {
            "figures_index": 0,
            "name": "ice_floe_drift_time_series.png",
            "caption": "Ice floe drift benchmark: ice floe drift time series",
            "bytes_available": false
          }
        },
        {
          "asset_id": "A02",
          "asset_class": "figure_attachment",
          "label": "Figure 2 — parameter sweep PNG",
          "in_report_section": "## 4. Results Figures / ### Figure 2",
          "locator": {
            "method": "char_span",
            "start_char": 2568,
            "end_char": 2674,
            "start_line": 86,
            "end_line": 86,
            "quote": "![Ice floe drift benchmark: ice floe drift parameter sweep](attachment:ice_floe_drift_parameter_sweep.png)",
            "unique": true,
            "encoding": "utf-8"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "attachment_uri_materialisation",
            "result": "unresolved"
          },
          "note": "Markdown image uses an `attachment:ice_floe_drift_parameter_sweep.png` URI; the platform reports `figures[1]` with name='ice_floe_drift_parameter_sweep.png' and caption='Ice floe drift benchmark: ice floe drift parameter sweep' but exposes no PNG bytes (GET /tensor/reports/5776/artifacts and /tensor/artifacts?report_id=5776 both return 404), and no such PNG exists in this worktree — so the asset is registered by reference only, never assumed.",
          "platform_metadata": {
            "figures_index": 1,
            "name": "ice_floe_drift_parameter_sweep.png",
            "caption": "Ice floe drift benchmark: ice floe drift parameter sweep",
            "bytes_available": false
          }
        },
        {
          "asset_id": "A03",
          "asset_class": "figure_attachment",
          "label": "Figure 3 — error distribution PNG",
          "in_report_section": "## 4. Results Figures / ### Figure 3",
          "locator": {
            "method": "char_span",
            "start_char": 2729,
            "end_char": 2841,
            "start_line": 90,
            "end_line": 90,
            "quote": "![Ice floe drift benchmark: ice floe drift error distribution](attachment:ice_floe_drift_error_distribution.png)",
            "unique": true,
            "encoding": "utf-8"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "attachment_uri_materialisation",
            "result": "unresolved"
          },
          "note": "Markdown image uses an `attachment:ice_floe_drift_error_distribution.png` URI; the platform reports `figures[2]` with name='ice_floe_drift_error_distribution.png' and caption='Ice floe drift benchmark: ice floe drift error distribution' but exposes no PNG bytes (GET /tensor/reports/5776/artifacts and /tensor/artifacts?report_id=5776 both return 404), and no such PNG exists in this worktree — so the asset is registered by reference only, never assumed.",
          "platform_metadata": {
            "figures_index": 2,
            "name": "ice_floe_drift_error_distribution.png",
            "caption": "Ice floe drift benchmark: ice floe drift error distribution",
            "bytes_available": false
          }
        },
        {
          "asset_id": "A04",
          "asset_class": "source_code_reference",
          "label": "DEM-LBM ice-floe-drift core module",
          "in_report_section": "## 7. Audit Trail / Files created",
          "locator": {
            "method": "char_span",
            "start_char": 3833,
            "end_char": 3892,
            "start_line": 122,
            "end_line": 122,
            "quote": "- `src/tensordem/ice_floe_drift.py` (13.9 KB) - Core module",
            "unique": true,
            "encoding": "utf-8"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path_exists_in_delivery_worktree",
            "result": "unresolved"
          },
          "note": "Cited at line 122 as `src/tensordem/ice_floe_drift.py`; the path lives in the report's own worktree (/root/tp-agent/work/m5068 per the reproducibility block), not in this delivery worktree, so its existence/content is NOT validated here.",
          "path_reference": "src/tensordem/ice_floe_drift.py",
          "path_reference_scope": "report_worktree_not_delivery_worktree"
        },
        {
          "asset_id": "A05",
          "asset_class": "source_code_reference",
          "label": "Test suite for the ice-floe-drift benchmark",
          "in_report_section": "## 7. Audit Trail / Files created",
          "locator": {
            "method": "char_span",
            "start_char": 3893,
            "end_char": 3963,
            "start_line": 123,
            "end_line": 123,
            "quote": "- `tests/test_ice_floe_drift.py` (8.8 KB) - 21 pytest tests (all pass)",
            "unique": true,
            "encoding": "utf-8"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path_exists_in_delivery_worktree",
            "result": "unresolved"
          },
          "note": "Cited at line 123 as `tests/test_ice_floe_drift.py`; the path lives in the report's own worktree (/root/tp-agent/work/m5068 per the reproducibility block), not in this delivery worktree, so its existence/content is NOT validated here.",
          "path_reference": "tests/test_ice_floe_drift.py",
          "path_reference_scope": "report_worktree_not_delivery_worktree"
        },
        {
          "asset_id": "A06",
          "asset_class": "source_code_reference",
          "label": "Benchmark runner",
          "in_report_section": "## 7. Audit Trail / Files created",
          "locator": {
            "method": "char_span",
            "start_char": 3964,
            "end_char": 4035,
            "start_line": 124,
            "end_line": 124,
            "quote": "- `scripts/run_ice_floe_drift_benchmark.py` (8.5 KB) - Benchmark runner",
            "unique": true,
            "encoding": "utf-8"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path_exists_in_delivery_worktree",
            "result": "unresolved"
          },
          "note": "Cited at line 124 as `scripts/run_ice_floe_drift_benchmark.py`; the path lives in the report's own worktree (/root/tp-agent/work/m5068 per the reproducibility block), not in this delivery worktree, so its existence/content is NOT validated here.",
          "path_reference": "scripts/run_ice_floe_drift_benchmark.py",
          "path_reference_scope": "report_worktree_not_delivery_worktree"
        },
        {
          "asset_id": "A07",
          "asset_class": "document_reference",
          "label": "Case documentation README",
          "in_report_section": "## 7. Audit Trail / Files created",
          "locator": {
            "method": "char_span",
            "start_char": 4036,
            "end_char": 4103,
            "start_line": 125,
            "end_line": 125,
            "quote": "- `docs/ice_floe_drift_dem_lbm/README.md` (14.7 KB) - Documentation",
            "unique": true,
            "encoding": "utf-8"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path_exists_in_delivery_worktree",
            "result": "unresolved"
          },
          "note": "Cited at line 125 as `docs/ice_floe_drift_dem_lbm/README.md`; the path lives in the report's own worktree (/root/tp-agent/work/m5068 per the reproducibility block), not in this delivery worktree, so its existence/content is NOT validated here.",
          "path_reference": "docs/ice_floe_drift_dem_lbm/README.md",
          "path_reference_scope": "report_worktree_not_delivery_worktree"
        },
        {
          "asset_id": "A08",
          "asset_class": "data_artifact_reference",
          "label": "Benchmark results JSON",
          "in_report_section": "## 7. Audit Trail / Files created",
          "locator": {
            "method": "char_span",
            "start_char": 4104,
            "end_char": 4173,
            "start_line": 126,
            "end_line": 126,
            "quote": "- `docs/ice_floe_drift_dem_lbm/ice_floe_drift_results.json` - Results",
            "unique": true,
            "encoding": "utf-8"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path_exists_in_delivery_worktree",
            "result": "unresolved"
          },
          "note": "Cited at line 126 as `docs/ice_floe_drift_dem_lbm/ice_floe_drift_results.json`; the path lives in the report's own worktree (/root/tp-agent/work/m5068 per the reproducibility block), not in this delivery worktree, so its existence/content is NOT validated here.",
          "path_reference": "docs/ice_floe_drift_dem_lbm/ice_floe_drift_results.json",
          "path_reference_scope": "report_worktree_not_delivery_worktree"
        },
        {
          "asset_id": "A09",
          "asset_class": "verification_record",
          "label": "Test execution log (pytest)",
          "in_report_section": "## 7. Audit Trail / Test execution",
          "locator": {
            "method": "char_span",
            "start_char": 4262,
            "end_char": 4384,
            "start_line": 130,
            "end_line": 133,
            "quote": "```bash\n$ pytest tests/test_ice_floe_drift.py -v\n======================== 21 passed in 4.90s =========================\n```",
            "unique": true,
            "encoding": "utf-8"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "Body-resident block; span covers source lines 130-133 inclusive."
        },
        {
          "asset_id": "A10",
          "asset_class": "reproducibility_record",
          "label": "Reproduction command block",
          "in_report_section": "## 7. Audit Trail / Reproducibility",
          "locator": {
            "method": "char_span",
            "start_char": 4407,
            "end_char": 4575,
            "start_line": 136,
            "end_line": 140,
            "quote": "```bash\ncd /root/tp-agent/work/m5068\nPYTHONPATH=src python3 -m pytest tests/test_ice_floe_drift.py -v\nPYTHONPATH=src python3 scripts/run_ice_floe_drift_benchmark.py\n```",
            "unique": true,
            "encoding": "utf-8"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "Body-resident block; span covers source lines 136-140 inclusive."
        },
        {
          "asset_id": "A11",
          "asset_class": "analytical_expression",
          "label": "Closed-form drift-velocity anchor",
          "in_report_section": "## 1. Case Introduction / Analytical solution",
          "locator": {
            "method": "char_span",
            "start_char": 502,
            "end_char": 612,
            "start_line": 13,
            "end_line": 16,
            "quote": "```\nU_drift = U_current · √(ρ_w/ρ_i) · √(C_D_water/C_D_ice)\n        = 1.0 · √(1025/900) · 1.0 = 1.0672 m/s\n```",
            "unique": true,
            "encoding": "utf-8"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "Body-resident block; span covers source lines 13-16 inclusive."
        },
        {
          "asset_id": "A12",
          "asset_class": "parameter_block",
          "label": "Geometry and fluid parameters",
          "in_report_section": "## 1. Case Introduction / Geometry",
          "locator": {
            "method": "char_span",
            "start_char": 286,
            "end_char": 475,
            "start_line": 7,
            "end_line": 10,
            "quote": "**Geometry:**\n- Ice floe: Circular cylinder, D=1m (baseline), h=0.2m, ρ_i=900 kg/m³\n- Fluid: Water, ρ_w=1025 kg/m³, U_current=1 m/s (baseline)\n- Reynolds number: Re = 10⁶ (turbulent regime)",
            "unique": true,
            "encoding": "utf-8"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "Body-resident block; span covers source lines 7-10 inclusive."
        },
        {
          "asset_id": "A13",
          "asset_class": "inline_table",
          "label": "Baseline case result table",
          "in_report_section": "## 3. Results / Baseline Case",
          "locator": {
            "method": "char_span",
            "start_char": 1166,
            "end_char": 1338,
            "start_line": 37,
            "end_line": 40,
            "quote": "| Quantity | Analytical | DEM-LBM | Error |\n|----------|-----------|---------|-------|\n| U_drift [m/s] | 1.0672 | 1.0671 | **0.00%** |\n| Convergence | - | 195 steps | ~2s |",
            "unique": true,
            "encoding": "utf-8"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "Body-resident block; span covers source lines 37-40 inclusive."
        },
        {
          "asset_id": "A14",
          "asset_class": "inline_table",
          "label": "9-case parameter sweep table",
          "in_report_section": "## 3. Results / Parameter Sweep",
          "locator": {
            "method": "char_span",
            "start_char": 1371,
            "end_char": 1888,
            "start_line": 44,
            "end_line": 54,
            "quote": "| U_current [m/s] | D [m] | U_analytical [m/s] | U_sim [m/s] | Error [%] |\n|-----------------|-------|-------------------|-------------|-----------|\n| 0.50 | 0.50 | 0.5336 | 0.5336 | 0.00 |\n| 0.50 | 1.00 | 0.5336 | 0.5336 | 0.00 |\n| 0.50 | 2.00 | 0.5336 | 0.5336 | 0.00 |\n| 1.00 | 0.50 | 1.0672 | 1.0671 | 0.00 |\n| 1.00 | 1.00 | 1.0672 | 1.0671 | 0.00 |\n| 1.00 | 2.00 | 1.0672 | 1.0671 | 0.00 |\n| 1.50 | 0.50 | 1.6008 | 1.6007 | 0.00 |\n| 1.50 | 1.00 | 1.6008 | 1.6007 | 0.00 |\n| 1.50 | 2.00 | 1.6008 | 1.6007 | 0.00 |",
            "unique": true,
            "encoding": "utf-8"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "Body-resident block; span covers source lines 44-54 inclusive."
        },
        {
          "asset_id": "A15",
          "asset_class": "inline_table",
          "label": "Negative control table",
          "in_report_section": "## 3. Results / Negative Control",
          "locator": {
            "method": "char_span",
            "start_char": 2012,
            "end_char": 2151,
            "start_line": 64,
            "end_line": 66,
            "quote": "| Test | Expected | Actual | Result |\n|------|----------|--------|--------|\n| No fluid (pure DEM) | 0.000 m/s | 0.000000 m/s | ✅ **PASS** |",
            "unique": true,
            "encoding": "utf-8"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "Body-resident block; span covers source lines 64-66 inclusive."
        },
        {
          "asset_id": "A16",
          "asset_class": "inline_table",
          "label": "Force balance table",
          "in_report_section": "## 3. Results / Force Balance",
          "locator": {
            "method": "char_span",
            "start_char": 2172,
            "end_char": 2347,
            "start_line": 70,
            "end_line": 76,
            "quote": "| Force | Value [N] |\n|-------|-----------|\n| Driving force | 402.5166 |\n| Resistive force | 402.4764 |\n| Residual | **0.0100%** |\n| Threshold | < 1% |\n| Result | ✅ **PASS** |",
            "unique": true,
            "encoding": "utf-8"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "Body-resident block; span covers source lines 70-76 inclusive."
        },
        {
          "asset_id": "A17",
          "asset_class": "inline_table",
          "label": "Error assessment table",
          "in_report_section": "## 6. Error Assessment",
          "locator": {
            "method": "char_span",
            "start_char": 3474,
            "end_char": 3755,
            "start_line": 110,
            "end_line": 115,
            "quote": "| Metric | Value | Threshold | Result |\n|--------|-------|-----------|--------|\n| Baseline error | 0.00% | < 3% | ✅ PASS |\n| Max error (9 cases) | 0.00% | < 3% | ✅ PASS |\n| Force balance residual | 0.0100% | < 1% | ✅ PASS |\n| Negative control | 0.000000 m/s | < 10⁻⁶ m/s | ✅ PASS |",
            "unique": true,
            "encoding": "utf-8"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "Body-resident block; span covers source lines 110-115 inclusive."
        }
      ],
      "claims": [],
      "claims_note": "objective.register_assets=true / classify_report_type=false and the package notes allow an empty claims array: this lane registers assets + locators only. No claim is extracted and no claim is marked verified; claim extraction belongs to a downstream work package and verification is computed by the platform gate.",
      "integrity": {
        "quote_uniqueness": "every quote re-sliced from source lines and confirmed md.count(quote)==1, md[start:end]==quote",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "chars_match_contract": true,
        "duplicate_ids": false
      },
      "limitations": [
        "Registration only: no text extraction, no claim generation, no verified marks.",
        "Figure assets are referenced, not materialised: the platform exposes figure name/caption but no PNG bytes and no artifact endpoint exists, so A01-A03 stay referenced_unresolved.",
        "A04-A08 are the report's own audit-trail paths; they live in the report's worktree (/root/tp-agent/work/m5068), outside this delivery worktree, so their existence is not validated here.",
        "Report self-reported numbers are registered as text spans, not re-derived here; the purely arithmetic consistency audit of the sweep table against the report's own closed form lives in runs/wp-5776-01/consistency_check.json (scripts/kf/consistency_check_5776.py) and is explicitly NOT a platform verification.",
        "The audit-trail line `- 3 PNG figures (time series, parameter sweep, error distribution)` (line 127) is a collective restatement of A01-A03 and is deliberately not registered as a separate asset.",
        "Schemas: this worktree has no schemas/kf_result.v1.schema.json, so a pinned copy (sha256=170dba8b0b5d54012490aaadc0b68647a9520ecb869e9d03f873afb99b74c076, taken from sibling worktree m15506) sits at docs/kf/wp-5776-01/kf_result.v1.schema.json and docs/kf/wp-5776-01/asset_manifest.v1_5776.schema.json pins the manifest shape; if the platform-side schema differs, the platform gate wins and this artifact must be revised."
      ]
    }
  },
  "claims": []
}
```
