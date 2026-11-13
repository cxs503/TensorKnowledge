# KF-RESULT wp-9582-01

工作包 `wp-9582-01` ｜ task_type `01-asset-registration` ｜ report_id `9582` ｜ lane B ｜ tag `kf-wp:wp-9582-01` ｜ 状态 draft（verification 由平台门计算，本报告不自标 verified）

## ① 本工序做了什么

对 `tensor://reports/9582` 做**资产登记**（task_type=01-asset-registration），不抽取知识、不分类、不给结论打 verified。产出一份 `asset_manifest.json`：确认 report_id 与其 markdown 的字节哈希/字符数，并把报告中声明的附件与工件逐条登记为可复核的引文定位（字符区间 + 1-based 行号 + 逐字引文 + 唯一性判定）。共登记 **22 个资产**：resolved_in_source 1 / referenced_unresolved 20 / declared_absent 1。`claims` 为空数组（契约 objective.classify_report_type=false、no_forced_claim_generation=true，空 claims 即完整结果）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文（不经记忆、不经数据库）**：`psql -d tensorplatform` 直读被行级权限拒绝（`mission denied for table tensor_reports`），改走平台 API：`POST /auth/login`（Bearer）→ `GET /tensor/reports/9582`，只取 `markdown` 字段，**按字节原样**写 `runs/wp-9582-01/source_9582.md`（不追加换行），元数据写 `source_9582_meta.json`。工具 `scripts/kf_wp9582_01_fetch.py`（stdlib only）。
2. **哈希自证**：对上述字节重算 sha256 = `cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f`，字符数 11293（UTF-8 字节数 16772）——与契约 `sha256:cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f` / 11293 逐项比对（见 manifest `source.contract` 四个布尔位）。
3. **资产抽取（程序化，不手抄）**：`scripts/kf_wp9582_01_build.py` 内以「字面 needle → 定位 → 引用行扩展」的方式登记：needle 在 markdown 中的首次出现位置取所在行，若该行在全文不唯一则上下各扩一行直至唯一（上限 8 行）；记录 `start_char/end_char`（Python str 下标）、`start_line/end_line`（1-based）、`quote`（逐字）、`unique`。图件另与报告记录 `figures[].name / png_base64` 做交叉核对。
4. **解析状态判定**（三态，不猜）：`resolved_in_source`（字节就在源内，如 markdown 本体）/ `referenced_unresolved`（引文可定位但工件字节不在报告记录内）/ `declared_absent`（报告自己声明数据不存在，如文献逐点数据 WITHHELD）。
5. **结构门**：`jsonschema` 双向校验——manifest vs 本包钉住的 `asset_manifest.schema.json`（draft-07），信封 vs 仓内规范 `schemas/kf_result.v1.schema.json`（2020-12）。
6. **自检**：6 条 acceptance 逐条机器判定，写 `selfcheck.json`（honest：不过就是不过）。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-9582-01/asset_manifest.json` | 主产物：source 身份（hash/chars/bytes/title/scenario_key + 契约比对位）+ 22 个资产 + 计数 + integrity |
| `docs/kf/wp-9582-01/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs/claims），`outputs["asset_manifest.json"]` 内嵌 manifest |
| `docs/kf/wp-9582-01/selfcheck.json` | 6 条 acceptance 的机器判定与明细（本地自检，非平台 verification） |
| `docs/kf/wp-9582-01/asset_manifest.schema.json` | 本包钉住的 manifest 结构（仓内 448 版把 package_id 写死为 `wp-448-01`，不可复用） |
| `runs/wp-9582-01/source_9582.md` | 报告 markdown 字节级副本（16772 B / 11293 chars），一切定位与哈希以它为准 |
| `runs/wp-9582-01/source_9582_meta.json` | 记录元数据（title/scenario_key/tags/figures 名单/记录字段名） |
| `docs/kf/wp-9582-01/figures/fig_asset_inventory.png` | 图1 资产清单：按类别/解析状态着色（计数直读 manifest，无手抄） |
| `docs/kf/wp-9582-01/figures/fig_locator_map.png` | 图2 定位地图：22 条 locator 在 0–11293 字符坐标上的区间（斜线=整篇文档级 locator） |

图件均由 `scripts/kf_wp9582_01_figures.py` 从 `asset_manifest.json` 实测值绘制（类别/状态计数、字符区间、唯一性计数），不含任何人工输入数字；本工序不产生物理场量，故无云图/基准对比曲线。

## ④ 证据定位表（资产/字段 → 原文引文片段）

引文一律为源 markdown 的逐字子串；`L` 列为 1-based 起始行，截断仅用于本表展示（机读版在 manifest 的 `locator.quote` 全文）。

| asset_id | class | resolution | L | 原文引文（截断展示） | 唯一性 |
|---|---|---|---|---|---|
| A01 | report_source_markdown | resolved_in_source | L1 | `# P82W2-N02 碎冰堆积体动态演化与运动学：孔隙率场、力链网络与 μ(I) 流变标定` | unique |
| A02 | figure_reference | referenced_unresolved | L158 | `**porosity_fields.png** — Porosity field phi(x,t) of one steady snapshot per scenario on the…` | unique |
| A03 | figure_reference | referenced_unresolved | L160 | `**mu_of_I_fit.png** — Measured friction coefficient against the inertial number for the thre…` | unique |
| A04 | figure_reference | referenced_unresolved | L162 | `**mu_I_residuals.png** — Residuals of the pooled element-test quadratic fit with the pre-reg…` | unique |
| A05 | figure_reference | referenced_unresolved | L164 | `**force_chain_vs_I.png** — Coordination number Z, strong-network anisotropy A_c and the shar…` | unique |
| A06 | figure_reference | referenced_unresolved | L166 | `**contact_orientation.png** — Polar distribution of contact-branch orientations folded onto …` | unique |
| A07 | figure_reference | referenced_unresolved | L168 | `**viscosity.png** — Equivalent viscosity eta = mu(I) P / gamma_dot at three confining pressu…` | unique |
| A08 | preregistration_reference | referenced_unresolved | L32 | `**工具链**：预注册 `prereg/rubble_rheology_prereg.json`（阈值先于生产扫描声明，含 Amendment 1）；扫描 `scripts/run_r…` | unique |
| A09 | code_reference | referenced_unresolved | L200 | `- 场景/后处理代码：`src/tensordem/rubble_scenarios.py`、`src/tensordem/rubble_postprocess.py`` | unique |
| A10 | code_reference | referenced_unresolved | L200 | `- 场景/后处理代码：`src/tensordem/rubble_scenarios.py`、`src/tensordem/rubble_postprocess.py`` | unique |
| A11 | code_reference | referenced_unresolved | L32 | `**工具链**：预注册 `prereg/rubble_rheology_prereg.json`（阈值先于生产扫描声明，含 Amendment 1）；扫描 `scripts/run_r…` | unique |
| A12 | code_reference | referenced_unresolved | L32 | `**工具链**：预注册 `prereg/rubble_rheology_prereg.json`（阈值先于生产扫描声明，含 Amendment 1）；扫描 `scripts/run_r…` | unique |
| A13 | data_artifact_reference | referenced_unresolved | L202 | `- 逐 run 数字：`artifacts/rubble_rheology/runs/*.json`；汇总：`artifacts/rubble_rheology/summary.jso…` | unique |
| A14 | data_artifact_reference | referenced_unresolved | L202 | `- 逐 run 数字：`artifacts/rubble_rheology/runs/*.json`；汇总：`artifacts/rubble_rheology/summary.jso…` | unique |
| A15 | code_reference | referenced_unresolved | L203 | `- 消融：`scripts/ablate_compression_kinematics.py` → `artifacts/rubble_rheology_ablation/`` | unique |
| A16 | data_artifact_reference | referenced_unresolved | L203 | `- 消融：`scripts/ablate_compression_kinematics.py` → `artifacts/rubble_rheology_ablation/`` | unique |
| A17 | test_reference | referenced_unresolved | L204 | `- 测试：`tests/test_rubble_postprocess.py`（19 项，含 4 个负控）+ `tests/test_rubble_kinematics.py`（5 项…` | unique |
| A18 | test_reference | referenced_unresolved | L204 | `- 测试：`tests/test_rubble_postprocess.py`（19 项，含 4 个负控）+ `tests/test_rubble_kinematics.py`（5 项…` | unique |
| A19 | code_reference_module | referenced_unresolved | L19 | `**后处理（`tensordem.rubble_postprocess`，与求解器解耦的纯 NumPy/SciPy 模块）**` | unique |
| A20 | code_reference_module | referenced_unresolved | L26 | `**DEM 场景（`tensordem.rubble_scenarios`，基于 `tensordem.granular2d`）**` | unique |
| A21 | code_reference_module | referenced_unresolved | L26 | `**DEM 场景（`tensordem.rubble_scenarios`，基于 `tensordem.granular2d`）**` | unique |
| A22 | literature_data_reference | declared_absent | L178 | `6. **文献锚点为量级窗**：Guimarães et al. 2022 未数字化逐点数据，逐点对比标注 WITHHELD。` | unique |

## ⑤ 注意点与局限

1. **图件像素缺失**：记录 `figures[]` 有 6 条 `name/caption`，但 `png_base64` 长度全为 0——图名与 caption 可定位，**像素字节不可解析**，故 6 张图一律 `referenced_unresolved`，不冒充已登记图片。
2. **工件跨仓**：`prereg/…`、`src/tensordem/…`、`scripts/…`、`artifacts/…`、`tests/…` 共 20 条只以路径字面量出现；报告记录无 artifact 附件字段，本工作树（TensorKnowledge）内亦不存在同名路径。是否真实存在于 TensorDEM 检出**未验证**，故记 `referenced_unresolved` 而非「存在」或「不存在」。
3. **`declared_absent` 不等于「缺失」**：Guimarães et al. 2022 逐点数据是报告自己声明未数字化（WITHHELD）；登记它是为了禁止后续工序把它当基准。
4. **A19/A20/A21 与 A09/A10 的重复口径**：模块名（`tensordem.rubble_postprocess`）与相对路径（`src/tensordem/rubble_postprocess.py`）指同一工件，但报告中出现于不同章节、不同写法，故分条登记并在 note 注明，不做合并（合并会丢章节定位）。id 仍全局唯一，满足 no_duplicate_ids。
5. **哈希口径**：`provenance.source_hash` 是 markdown 的 **UTF-8 字节** sha256（不含任何附加换行）；字符数按 Unicode 码点计（11293），与契约一致，字节数 16772 仅供对照。二者不可混用。
6. **未做（有意）**：不抽取 claims、不判定报告类型、不评估报告结论正误、不复制 A/B/C 级精度结论——这些属于 02/03 工序，越界会破坏工序边界。
7. **误差判定（本工序口径）**：本工序是元数据登记，无数值模型、无实验/解析基准可比，故「关键量误差是否 <3%」**不适用（N/A）**；可判定的只有可机检的身份量，且已全部给出实测值：哈希 = 契约哈希（逐位相等，误差 0）、字符数 = 11293（与契约 11293 相等，误差 0）、22/22 条引文可解析且唯一。报告物理结论的精度判定不在本工序范围，本报告不引用、不复述、不背书。
8. **图的口径**：本工序无物理场量，故不产云图/基准对比曲线；只画两张**由 manifest 实测数据生成**的登记图（资产清单、定位地图），图内每个数字都可回溯到 `asset_manifest.json` 字段。源报告的 6 张物理图（见注 1）字节不可得，**不重绘**——重绘等于二次创作，会污染证据链。

## ⑥ 自检：逐条对照 acceptance

| acceptance | 结果 | 明细 |
|---|---|---|
| valid_json | ✓ | {"files": ["asset_manifest.json", "kf_result.json"], "errors": []} |
| schema_pass | ✓ | {"manifest_errors": [], "envelope_errors": [], "schemas": ["asset_manifest.schema.json", "schemas/kf_result.v1.schema.json"]} |
| source_locator_resolvable | ✓ | {"locators_checked": 22, "failures": [], "rule": "char_span: md[start:end]==quote; document: start==0 and end==len(markdown); all: quote unique in markdown and start_line consistent"} |
| source_hash_matches | ✓ | {"recomputed": "sha256:cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f", "contract": "sha256:cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f", "chars": 11293, "contract_chars": 11293} |
| no_duplicate_ids | ✓ | {"n": 22, "unique": 22, "ids": ["A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", "A09", "A10", "A11", "A12", "A13", "A14", "A15", "A16", "A17", "A18", "A19", "A20", "A21", "A22"]} |
| all_claims_have_evidence_or_explicit_unresolved_status | ✓ | {"claims": 0, "violations": [], "rationale": "objective.register_assets=true, objective.classify_report_type=false -> no extraction"} |

**总结论**：6/6 acceptance 全通过（本地自检）；真实 verification 由平台门独立重算。

`repro_cmd`（一键复跑，工作树根下执行）：

```bash
python3 scripts/kf_wp9582_01_fetch.py && python3 scripts/kf_wp9582_01_build.py
```

## 结果 JSON（唯一 json 代码块，原样提交）

```json
{
  "package_id": "wp-9582-01",
  "task_type": "01-asset-registration",
  "report_id": "9582",
  "provenance": {
    "source_hash": "sha256:cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f",
    "source_field": "markdown",
    "producer": "kf-worker/m15661",
    "emitted_at": "2026-11-12T01:42:48.702841+00:00",
    "notes": "Registration only: report_id 9582 markdown pinned byte-exact and hashed locally; asset locators are char spans re-resolved against those bytes. No extraction, no verified marks."
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-9582-01",
      "task_type": "01-asset-registration",
      "report_id": "9582",
      "source": {
        "uri": "tensor://reports/9582",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f",
        "chars": 11293,
        "bytes_utf8": 16772,
        "title": "P82W2-N02 碎冰堆积体 μ(I) 流变标定：孔隙率场、力链网络与等效黏度（DEM）",
        "scenario_key": "ice_rubble_rheology_dem",
        "contract": {
          "source_hash": "sha256:cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f",
          "chars": 11293,
          "title": "P82W2-N02 碎冰堆积体 μ(I) 流变标定：孔隙率场、力链网络与等效黏度（DEM）",
          "scenario_key": "ice_rubble_rheology_dem",
          "hash_matches": true,
          "chars_match": true,
          "title_matches": true,
          "scenario_key_matches": true
        },
        "platform_figures": [
          {
            "name": "porosity_fields.png",
            "caption_chars": 280,
            "png_bytes_present": false
          },
          {
            "name": "mu_of_I_fit.png",
            "caption_chars": 295,
            "png_bytes_present": false
          },
          {
            "name": "mu_I_residuals.png",
            "caption_chars": 295,
            "png_bytes_present": false
          },
          {
            "name": "force_chain_vs_I.png",
            "caption_chars": 280,
            "png_bytes_present": false
          },
          {
            "name": "contact_orientation.png",
            "caption_chars": 236,
            "png_bytes_present": false
          },
          {
            "name": "viscosity.png",
            "caption_chars": 196,
            "png_bytes_present": false
          }
        ],
        "platform_tags": [
          "DEM",
          "rubble",
          "mu(I)",
          "force-chain",
          "porosity",
          "rheology",
          "TensorDEM",
          "P82W2-N02",
          "P82W4-N02"
        ]
      },
      "counts": {
        "assets": 22,
        "by_class": {
          "report_source_markdown": 1,
          "figure_reference": 6,
          "preregistration_reference": 1,
          "code_reference": 5,
          "data_artifact_reference": 3,
          "test_reference": 2,
          "code_reference_module": 3,
          "literature_data_reference": 1
        },
        "by_resolution": {
          "resolved_in_source": 1,
          "referenced_unresolved": 20,
          "declared_absent": 1
        },
        "resolved_in_source": 1,
        "referenced_unresolved": 20,
        "declared_absent": 1
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "report_source_markdown",
          "label": "报告源资产：markdown 全文（本工序的输入字节）",
          "in_report_section": "whole document",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "pinned byte copy re-read; sha256/len re-measured from those bytes",
            "result": "resolved"
          },
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 11293,
            "start_line": 1,
            "end_line": 207,
            "quote": "# P82W2-N02 碎冰堆积体动态演化与运动学：孔隙率场、力链网络与 μ(I) 流变标定",
            "unique": true
          },
          "note": "字节级副本 runs/wp-9582-01/source_9582.md；sha256 于该副本重算，用于 provenance.source_hash。 本副本 16772 bytes / 11293 chars。"
        },
        {
          "asset_id": "A02",
          "asset_class": "figure_reference",
          "label": "porosity_fields.png（孔隙率场云图）",
          "in_report_section": "④ 结果图",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "name in §④ bold lead-in AND record.figures[].name match AND png_base64 non-empty",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 7165,
            "end_char": 7471,
            "start_line": 158,
            "end_line": 158,
            "quote": "**porosity_fields.png** — Porosity field phi(x,t) of one steady snapshot per scenario on the required grid h = 5 d50. White dots are particle centres. The field is built from exact circle/rectangle intersections, so its area integral reproduces the global porosity to round-off (audited per run, <= 1e-12).",
            "unique": true
          },
          "note": "图名+caption 在 §④ 可定位；PNG 像素字节未随报告记录附带。 记录侧 figures[] 命中=True，png_base64 长度=0。"
        },
        {
          "asset_id": "A03",
          "asset_class": "figure_reference",
          "label": "mu_of_I_fit.png（μ–I 拟合与场景点）",
          "in_report_section": "④ 结果图",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "name in §④ bold lead-in AND record.figures[].name match AND png_base64 non-empty",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 7473,
            "end_char": 7916,
            "start_line": 160,
            "end_line": 160,
            "quote": "**mu_of_I_fit.png** — Measured friction coefficient against the inertial number for the three scenarios, one point per (scenario, imposed rate) with the seed as replicate; error bars are the standard error over seeds. Solid line: pooled element-test law; dashed: simple-shear element test alone. Pooled R^2 = 0.803, shear-only R^2 = 0.920; the channel points (mu ~ 0.07-0.10) are drag dominated and are a validation case, not calibration data.",
            "unique": true
          },
          "note": "图名+caption 在 §④ 可定位；PNG 像素字节未随报告记录附带。 记录侧 figures[] 命中=True，png_base64 长度=0。"
        },
        {
          "asset_id": "A04",
          "asset_class": "figure_reference",
          "label": "mu_I_residuals.png（主判据残差与容差带）",
          "in_report_section": "④ 结果图",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "name in §④ bold lead-in AND record.figures[].name match AND png_base64 non-empty",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 7918,
            "end_char": 8255,
            "start_line": 162,
            "end_line": 162,
            "quote": "**mu_I_residuals.png** — Residuals of the pooled element-test quadratic fit with the pre-registered residual tolerance (+-0.05). The residual standard deviation is inside the tolerance band, yet R^2 stays below 0.95 because the friction range spanned by the data is only ~0.10; the residuals are structured by solid fraction, not random.",
            "unique": true
          },
          "note": "图名+caption 在 §④ 可定位；PNG 像素字节未随报告记录附带。 记录侧 figures[] 命中=True，png_base64 长度=0。"
        },
        {
          "asset_id": "A05",
          "asset_class": "figure_reference",
          "label": "force_chain_vs_I.png（Z / A_c / 强链载荷份额 vs I）",
          "in_report_section": "④ 结果图",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "name in §④ bold lead-in AND record.figures[].name match AND png_base64 non-empty",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 8257,
            "end_char": 8564,
            "start_line": 164,
            "end_line": 164,
            "quote": "**force_chain_vs_I.png** — Coordination number Z, strong-network anisotropy A_c and the share of the load carried by the 20 % strongest contacts, per run. Z stays in the isostatic band (3-4 in 2-D) over two decades of I, while A_c grows with I: the backbone becomes more directional as the flow gets faster.",
            "unique": true
          },
          "note": "图名+caption 在 §④ 可定位；PNG 像素字节未随报告记录附带。 记录侧 figures[] 命中=True，png_base64 长度=0。"
        },
        {
          "asset_id": "A06",
          "asset_class": "figure_reference",
          "label": "contact_orientation.png（接触方向极分布）",
          "in_report_section": "④ 结果图",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "name in §④ bold lead-in AND record.figures[].name match AND png_base64 non-empty",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 8566,
            "end_char": 8832,
            "start_line": 166,
            "end_line": 166,
            "quote": "**contact_orientation.png** — Polar distribution of contact-branch orientations folded onto [0, pi): the force-weighted distribution is far more peaked than the count-weighted one, i.e. the load is carried by a minority of aligned contacts (the force-chain network).",
            "unique": true
          },
          "note": "图名+caption 在 §④ 可定位；PNG 像素字节未随报告记录附带。 记录侧 figures[] 命中=True，png_base64 长度=0。"
        },
        {
          "asset_id": "A07",
          "asset_class": "figure_reference",
          "label": "viscosity.png（等效黏度与文献窗）",
          "in_report_section": "④ 结果图",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "name in §④ bold lead-in AND record.figures[].name match AND png_base64 non-empty",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 8834,
            "end_char": 9050,
            "start_line": 168,
            "end_line": 168,
            "quote": "**viscosity.png** — Equivalent viscosity eta = mu(I) P / gamma_dot at three confining pressures with the literature acceptance window; the star is the pre-registered reference state (P = 10 kPa, gamma_dot = 0.1 1/s).",
            "unique": true
          },
          "note": "图名+caption 在 §④ 可定位；PNG 像素字节未随报告记录附带。 记录侧 figures[] 命中=True，png_base64 长度=0。"
        },
        {
          "asset_id": "A08",
          "asset_class": "preregistration_reference",
          "label": "prereg/rubble_rheology_prereg.json（预注册阈值+Amendment）",
          "in_report_section": "② 怎么做的 / 审计链",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal present in source; file bytes attached to report record? (record has no artifact field); path present in this TensorKnowledge worktree?",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 1685,
            "end_char": 1882,
            "start_line": 32,
            "end_line": 32,
            "quote": "**工具链**：预注册 `prereg/rubble_rheology_prereg.json`（阈值先于生产扫描声明，含 Amendment 1）；扫描 `scripts/run_rubble_rheology.py`（集群 20 并发，60 runs）；拟合/验收/绘图 `scripts/analyse_rubble_rheology.py`；全部数字写入 `summary.json`。",
            "unique": true
          },
          "note": "路径字面量可定位；文件本体不在报告记录内，需到 TensorDEM 检出取回。 本工作树同名路径存在=False（不在本仓即需跨仓取回）。"
        },
        {
          "asset_id": "A09",
          "asset_class": "code_reference",
          "label": "src/tensordem/rubble_scenarios.py（DEM 场景定义）",
          "in_report_section": "审计链",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal present in source; file bytes attached to report record? (record has no artifact field); path present in this TensorKnowledge worktree?",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 10777,
            "end_char": 10861,
            "start_line": 200,
            "end_line": 200,
            "quote": "- 场景/后处理代码：`src/tensordem/rubble_scenarios.py`、`src/tensordem/rubble_postprocess.py`",
            "unique": true
          },
          "note": "路径字面量可定位；文件本体不在报告记录内，需到 TensorDEM 检出取回。 本工作树同名路径存在=False（不在本仓即需跨仓取回）。"
        },
        {
          "asset_id": "A10",
          "asset_class": "code_reference",
          "label": "src/tensordem/rubble_postprocess.py（后处理模块）",
          "in_report_section": "审计链",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal present in source; file bytes attached to report record? (record has no artifact field); path present in this TensorKnowledge worktree?",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 10777,
            "end_char": 10861,
            "start_line": 200,
            "end_line": 200,
            "quote": "- 场景/后处理代码：`src/tensordem/rubble_scenarios.py`、`src/tensordem/rubble_postprocess.py`",
            "unique": true
          },
          "note": "路径字面量可定位；文件本体不在报告记录内，需到 TensorDEM 检出取回。 本工作树同名路径存在=False（不在本仓即需跨仓取回）。"
        },
        {
          "asset_id": "A11",
          "asset_class": "code_reference",
          "label": "scripts/run_rubble_rheology.py（扫描脚本）",
          "in_report_section": "审计链",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal present in source; file bytes attached to report record? (record has no artifact field); path present in this TensorKnowledge worktree?",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 1685,
            "end_char": 1882,
            "start_line": 32,
            "end_line": 32,
            "quote": "**工具链**：预注册 `prereg/rubble_rheology_prereg.json`（阈值先于生产扫描声明，含 Amendment 1）；扫描 `scripts/run_rubble_rheology.py`（集群 20 并发，60 runs）；拟合/验收/绘图 `scripts/analyse_rubble_rheology.py`；全部数字写入 `summary.json`。",
            "unique": true
          },
          "note": "路径字面量可定位；文件本体不在报告记录内，需到 TensorDEM 检出取回。 本工作树同名路径存在=False（不在本仓即需跨仓取回）。"
        },
        {
          "asset_id": "A12",
          "asset_class": "code_reference",
          "label": "scripts/analyse_rubble_rheology.py（拟合/验收/绘图脚本）",
          "in_report_section": "审计链",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal present in source; file bytes attached to report record? (record has no artifact field); path present in this TensorKnowledge worktree?",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 1685,
            "end_char": 1882,
            "start_line": 32,
            "end_line": 32,
            "quote": "**工具链**：预注册 `prereg/rubble_rheology_prereg.json`（阈值先于生产扫描声明，含 Amendment 1）；扫描 `scripts/run_rubble_rheology.py`（集群 20 并发，60 runs）；拟合/验收/绘图 `scripts/analyse_rubble_rheology.py`；全部数字写入 `summary.json`。",
            "unique": true
          },
          "note": "路径字面量可定位；文件本体不在报告记录内，需到 TensorDEM 检出取回。 本工作树同名路径存在=False（不在本仓即需跨仓取回）。"
        },
        {
          "asset_id": "A13",
          "asset_class": "data_artifact_reference",
          "label": "artifacts/rubble_rheology/runs/*.json（逐 run 数字）",
          "in_report_section": "审计链",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal present in source; file bytes attached to report record? (record has no artifact field); path present in this TensorKnowledge worktree?",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 10942,
            "end_char": 11036,
            "start_line": 202,
            "end_line": 202,
            "quote": "- 逐 run 数字：`artifacts/rubble_rheology/runs/*.json`；汇总：`artifacts/rubble_rheology/summary.json`",
            "unique": true
          },
          "note": "路径通配符可定位；逐 run 数据本体不在报告记录内。 本工作树同名路径存在=False（不在本仓即需跨仓取回）。"
        },
        {
          "asset_id": "A14",
          "asset_class": "data_artifact_reference",
          "label": "artifacts/rubble_rheology/summary.json（汇总）",
          "in_report_section": "审计链",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal present in source; file bytes attached to report record? (record has no artifact field); path present in this TensorKnowledge worktree?",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 10942,
            "end_char": 11036,
            "start_line": 202,
            "end_line": 202,
            "quote": "- 逐 run 数字：`artifacts/rubble_rheology/runs/*.json`；汇总：`artifacts/rubble_rheology/summary.json`",
            "unique": true
          },
          "note": "路径字面量可定位；汇总数据本体不在报告记录内。 本工作树同名路径存在=False（不在本仓即需跨仓取回）。"
        },
        {
          "asset_id": "A15",
          "asset_class": "code_reference",
          "label": "scripts/ablate_compression_kinematics.py（压缩运动学消融）",
          "in_report_section": "审计链",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal present in source; file bytes attached to report record? (record has no artifact field); path present in this TensorKnowledge worktree?",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 11037,
            "end_char": 11124,
            "start_line": 203,
            "end_line": 203,
            "quote": "- 消融：`scripts/ablate_compression_kinematics.py` → `artifacts/rubble_rheology_ablation/`",
            "unique": true
          },
          "note": "路径字面量可定位；文件本体不在报告记录内。 本工作树同名路径存在=False（不在本仓即需跨仓取回）。"
        },
        {
          "asset_id": "A16",
          "asset_class": "data_artifact_reference",
          "label": "artifacts/rubble_rheology_ablation/（消融输出目录）",
          "in_report_section": "审计链",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal present in source; file bytes attached to report record? (record has no artifact field); path present in this TensorKnowledge worktree?",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 11037,
            "end_char": 11124,
            "start_line": 203,
            "end_line": 203,
            "quote": "- 消融：`scripts/ablate_compression_kinematics.py` → `artifacts/rubble_rheology_ablation/`",
            "unique": true
          },
          "note": "目录路径可定位；目录内容不在报告记录内。 本工作树同名路径存在=False（不在本仓即需跨仓取回）。"
        },
        {
          "asset_id": "A17",
          "asset_class": "test_reference",
          "label": "tests/test_rubble_postprocess.py（19 项含 4 负控）",
          "in_report_section": "审计链",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal present in source; file bytes attached to report record? (record has no artifact field); path present in this TensorKnowledge worktree?",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 11125,
            "end_char": 11225,
            "start_line": 204,
            "end_line": 204,
            "quote": "- 测试：`tests/test_rubble_postprocess.py`（19 项，含 4 个负控）+ `tests/test_rubble_kinematics.py`（5 项，运动学一致性）",
            "unique": true
          },
          "note": "路径字面量可定位；测试文件本体不在报告记录内。 本工作树同名路径存在=False（不在本仓即需跨仓取回）。"
        },
        {
          "asset_id": "A18",
          "asset_class": "test_reference",
          "label": "tests/test_rubble_kinematics.py（5 项运动学一致性）",
          "in_report_section": "审计链",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal present in source; file bytes attached to report record? (record has no artifact field); path present in this TensorKnowledge worktree?",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 11125,
            "end_char": 11225,
            "start_line": 204,
            "end_line": 204,
            "quote": "- 测试：`tests/test_rubble_postprocess.py`（19 项，含 4 个负控）+ `tests/test_rubble_kinematics.py`（5 项，运动学一致性）",
            "unique": true
          },
          "note": "路径字面量可定位；测试文件本体不在报告记录内。 本工作树同名路径存在=False（不在本仓即需跨仓取回）。"
        },
        {
          "asset_id": "A19",
          "asset_class": "code_reference_module",
          "label": "tensordem.rubble_postprocess（后处理模块引用）",
          "in_report_section": "② 怎么做的",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal present in source; file bytes attached to report record? (record has no artifact field); path present in this TensorKnowledge worktree?",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 683,
            "end_char": 746,
            "start_line": 19,
            "end_line": 19,
            "quote": "**后处理（`tensordem.rubble_postprocess`，与求解器解耦的纯 NumPy/SciPy 模块）**",
            "unique": true
          },
          "note": "模块引用可定位（与 A10 的文件路径是同一工件，登记口径不同：模块名 vs 相对路径）。 本工作树同名路径存在=False（不在本仓即需跨仓取回）。"
        },
        {
          "asset_id": "A20",
          "asset_class": "code_reference_module",
          "label": "tensordem.rubble_scenarios（场景模块引用）",
          "in_report_section": "② 怎么做的",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal present in source; file bytes attached to report record? (record has no artifact field); path present in this TensorKnowledge worktree?",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 1304,
            "end_char": 1370,
            "start_line": 26,
            "end_line": 26,
            "quote": "**DEM 场景（`tensordem.rubble_scenarios`，基于 `tensordem.granular2d`）**",
            "unique": true
          },
          "note": "模块引用可定位；模块源码本体不在报告记录内。 本工作树同名路径存在=False（不在本仓即需跨仓取回）。"
        },
        {
          "asset_id": "A21",
          "asset_class": "code_reference_module",
          "label": "tensordem.granular2d（颗粒引擎基座引用）",
          "in_report_section": "② 怎么做的",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal present in source; file bytes attached to report record? (record has no artifact field); path present in this TensorKnowledge worktree?",
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 1304,
            "end_char": 1370,
            "start_line": 26,
            "end_line": 26,
            "quote": "**DEM 场景（`tensordem.rubble_scenarios`，基于 `tensordem.granular2d`）**",
            "unique": true
          },
          "note": "模块引用可定位；模块源码本体不在报告记录内。 本工作树同名路径存在=False（不在本仓即需跨仓取回）。"
        },
        {
          "asset_id": "A22",
          "asset_class": "literature_data_reference",
          "label": "Guimarães et al. 2022 逐点数据（文献锚点）",
          "in_report_section": "⑤ 注意点 / ⑥ 误差判定",
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "literal WITHHELD declaration present in source",
            "result": "absent"
          },
          "locator": {
            "method": "char_span",
            "start_char": 9642,
            "end_char": 9705,
            "start_line": 178,
            "end_line": 178,
            "quote": "6. **文献锚点为量级窗**：Guimarães et al. 2022 未数字化逐点数据，逐点对比标注 WITHHELD。",
            "unique": true
          },
          "note": "报告显式声明该数据未数字化、逐点对比 WITHHELD —— 属于「报告自己声明不存在」的资产，不得当作可用基准。"
        }
      ],
      "claims": [],
      "integrity": {
        "quote_uniqueness": {
          "total": 22,
          "unique": 22,
          "non_unique_ids": []
        },
        "hash_recomputed_locally": "sha256:cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f",
        "hash_matches_contract": true,
        "chars_match_contract": true,
        "no_duplicate_ids": true
      }
    },
    "selfcheck.json": {
      "package_id": "wp-9582-01",
      "authority": "local self-check only; the platform gate is authoritative and re-computes the hash independently",
      "checked_at": "2026-11-12T01:42:48.814558+00:00",
      "source_hash": "sha256:cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f",
      "acceptance": [
        {
          "id": "valid_json",
          "name": "all emitted JSON re-parses from disk",
          "pass": true,
          "detail": {
            "files": [
              "asset_manifest.json",
              "kf_result.json"
            ],
            "errors": []
          }
        },
        {
          "id": "schema_pass",
          "name": "asset_manifest.json vs package-pinned schema + kf_result.json vs canonical kf_result.v1",
          "pass": true,
          "detail": {
            "manifest_errors": [],
            "envelope_errors": [],
            "schemas": [
              "asset_manifest.schema.json",
              "schemas/kf_result.v1.schema.json"
            ]
          }
        },
        {
          "id": "source_locator_resolvable",
          "name": "every locator re-resolves to its verbatim quote in the pinned markdown",
          "pass": true,
          "detail": {
            "locators_checked": 22,
            "failures": [],
            "rule": "char_span: md[start:end]==quote; document: start==0 and end==len(markdown); all: quote unique in markdown and start_line consistent"
          }
        },
        {
          "id": "source_hash_matches",
          "name": "sha256 + char count of the pinned bytes equal the contract values",
          "pass": true,
          "detail": {
            "recomputed": "sha256:cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f",
            "contract": "sha256:cd99f31bff62078104eee95ff0cf1aea33f377552b7c68921986b05451ee9f5f",
            "chars": 11293,
            "contract_chars": 11293
          }
        },
        {
          "id": "no_duplicate_ids",
          "name": "asset_id values unique",
          "pass": true,
          "detail": {
            "n": 22,
            "unique": 22,
            "ids": [
              "A01",
              "A02",
              "A03",
              "A04",
              "A05",
              "A06",
              "A07",
              "A08",
              "A09",
              "A10",
              "A11",
              "A12",
              "A13",
              "A14",
              "A15",
              "A16",
              "A17",
              "A18",
              "A19",
              "A20",
              "A21",
              "A22"
            ]
          }
        },
        {
          "id": "all_claims_have_evidence_or_explicit_unresolved_status",
          "name": "claims either carry an evidence locator or an explicit status; claims=[] is the complete result for a registration-only package",
          "pass": true,
          "detail": {
            "claims": 0,
            "violations": [],
            "rationale": "objective.register_assets=true, objective.classify_report_type=false -> no extraction"
          }
        }
      ],
      "selfcheck_pass": true,
      "failed": []
    }
  },
  "claims": []
}
```
