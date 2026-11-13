KF-RESULT wp-13988-01

任务 m15771 · 工作包 `wp-13988-01` · 工序 `01-asset-registration` · 报告 13988 · 状态 draft（verification 归平台门）
tags: `kf-wp:wp-13988-01` · `kf-result` · `asset-registration` · `report-13988` · `H5-CALIB-REFLUX`
> 本报告取代 `#14877`（同包前一次发布：其资产解析检查器把平台 figures[] 的同名图件误判为 absent，且 A06/A09 的候选路径列表含数学片段噪声；已修正后重发，主产物 sha256 见 ③）。


## ① 本工序做了什么

按工作包契约（`task_type=01-asset-registration`，`objective.register_assets=true`，`objective.classify_report_type=false`）对**唯一一份**报告 `report_id=13988`（标题见 ④ A02）做资产登记：

- 从平台 API 取 `markdown` 字段，独立重算 sha256，与契约 `source_hash` 逐位比对：**79d795674f0b13f828d8933af64612a1addb30cb8a8b903f7ab136f0508442b9**，chars **6222**（= 契约声明的 6222），bytes_utf8 **9227** → 一致。
- 登记 **29** 个源资产：`resolved_in_source` **22** / `referenced_unresolved` **7** / `declared_absent` **0**。每个资产带 **逐字切片** 的 `locator`（char 区间 + 行区间 + quote），不手抄。
- **不做抽取**：`claims=[]`（契约允许空数组）。本工序不产生任何知识断言，也不把任何结论标成 verified。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`scripts/kf_fetch_13988.py` 走 `GET http://127.0.0.1:8010/api/v1/tensor/reports/13988`（Bearer，env `TENSOR_AGENT_USER/PASS`，不硬编码凭据）；psql 直连本环境 `permission denied for table tensor_reports`，故只走 API。落 `runs/wp-13988-01/report_13988.json|.md`。
2. **哈希门**：`sha256(markdown.encode('utf-8'))` 与契约 `source_hash` 比对，不等即 `exit 2`（本次 MATCH）。
3. **定位法（关键设置）**：每个资产声明一个 **在全文唯一出现** 的锚点子串 + 相对行偏移 `(start, end)`；脚本用 `md.count(anchor)==1` 强制唯一（不唯一直接 `SystemExit`），再由行偏移算出 `start_char/end_char`，**quote = `md[start_char:end_char]` 切片**。因此引文逐字性由构造保证，而非人工核对。
4. **解析判定（分辨率分类）**：`resolved_in_source`＝切片自证；`referenced_unresolved`＝报告只给仓库相对路径/分支名，脚本在本工作树内逐路径 `Path.exists()` 检索（不联网、不猜地址、不臆造 DOI）；图件额外查平台 `figures[]` 是否含同名 PNG。
5. **结构门**：manifest 校验用 `docs/wp-13988-01/asset_manifest.v1.schema.json`（由仓内 `schemas/asset_manifest.v1.schema.json` 程序化改 const 派生，因原 schema 固定为 448 包）；信封校验用仓内权威 `schemas/kf_result.v1.schema.json`。两者各带反证（删必填键必须被判失败）。
6. **独立复核**：`docs/wp-13988-01/verify_manifest.py` 重新从 API 取 markdown（不复用缓存），对 29 个 quote 重算唯一性与 char 切片一致性。
7. **零领域语义**：本包全部逻辑在 `docs/wp-13988-01/` 与 `scripts/kf_fetch_13988.py` 内，不触碰平台共性代码。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `artifacts/wp-13988-01/asset_manifest.json` | 主产物：29 个资产 + locator + resolution_check；sha256 `096b1a8741db4fddfa8fb7a968053b9e65a5a10a8ea7f6907757dd545be9b30b`，37547 bytes |
| `docs/wp-13988-01/asset_manifest.json` | 主产物的**逐字节镜像**（仓推送门会丢 `artifacts/**`、`runs/**`，故留档于 `docs/`；脚本断言两者 sha256 相等） |
| `docs/wp-13988-01/kf_result.wp-13988-01.json` | kf_result.v1 结果信封（本报告 ⑦ 的单 json 块同源） |
| `docs/wp-13988-01/checks.json` | 构建期 11 项自检明细（含每次反证结果） |
| `docs/wp-13988-01/verification.json` | 独立复核 11 项，`ok=true`，记录 fresh source hash |
| `docs/wp-13988-01/build_asset_manifest.py` | 登记器（锚点唯一性 → 切片 → 分类 → 结构门 → 落盘） |
| `docs/wp-13988-01/verify_manifest.py` | 独立复核器（重新取源重算，不复用缓存） |
| `docs/wp-13988-01/plot_coverage.py` → `fig_manifest_coverage.png` | 覆盖图：29 条资产在 6222 字符源文上的区间分布（按解析类着色）+ 分类计数 |
| `scripts/kf_fetch_13988.py` | 取源+哈希门 |
| `runs/wp-13988-01/report_13988.json|.md` | API 原始载荷与字节精确 markdown |

资产分类计数：

| asset_class | 数量 |
|---|---|
| table | 6 |
| numeric_anchor | 4 |
| statement | 3 |
| code_pointer | 2 |
| external_figure | 2 |
| document | 1 |
| heading | 1 |
| run_identity | 1 |
| vcs_reference | 1 |
| statement_set | 1 |
| external_dataset | 1 |
| external_artifact_set | 1 |
| mechanism_doc | 1 |
| repro_command | 1 |
| negative_control | 1 |
| figure_declaration | 1 |
| limitation_set | 1 |

## ④ 证据定位表（字段 → 原文引文，逐字整行未截断）

- **A02** · `heading` · char `0–43` · L1 · resolved_in_source

  > # H5-CALIB-REFLUX：高保真 → 经验系数回流（sha256 溯源贯通）

- **A03** · `run_identity` · char `45–124` · L3 · resolved_in_source

  > 任务 m14897 · 分支 agent/m14897 · 判定 **PASS** · 工件 `artifacts/m14897_calib_reflux/`

- **A08** · `numeric_anchor` · char `648–822` · L13 · resolved_in_source

  > **验证船型**：KCS（KRISO 集装箱船，公开船型），几何取自 `docs/ex1/artifacts/kcs_spec_data.json`，先过几何门：Cb_lib=0.6509 vs nabla/(L·B·T)=0.650499，偏差 0.062% (<2%)；L/B=7.143，B/T=2.981，nabla=52030.0 m³。

- **A10** · `table` · char `884–1744` · L19 · resolved_in_source

  > | 步 | 做什么 | 工件 | 证据等级 |

- **A14** · `statement` · char `2107–2229` · L37 · resolved_in_source

  > **S1 高保真证据**：站点数 238，Re_x ∈ [2.020e+07, 2.020e+08]，闭包RANS-grade integral boundary layer (not DNS/LES resolved turbulence)。

- **A15** · `numeric_anchor` · char `2231–2367` · L39 · resolved_in_source

  > **S2 标定**：A_hat = **0.075539**（ΔA/A = +0.72%），σ_A = 7.239e-05（0.097%），残差 RMS = 1.456% / max = 3.143%，物理带 [0.0700, 0.0800]，clamped=False。

- **A16** · `negative_control` · char `2369–2434` · L41 · resolved_in_source

  > **S2 负控**：合成线上数据 → A 还原 0.075000，误差 **+0.00000%**（容差 0.5%）→ PASS。

- **A17** · `table` · char `2465–2663` · L45 · resolved_in_source

  > | Re_x 下界 | 站点数 | A_hat | ΔA/A | 残差 RMS |

- **A18** · `numeric_anchor` · char `2665–2754` · L51 · resolved_in_source

  > **S3 回写**：账本 seq=0，entry_sha256=`6fc45dd1e21f8ba8…`，生效快照 head_sha256=`3eeab056fd161a16…`。

- **A19** · `table` · char `2800–3647` · L55 · resolved_in_source

  > | Fn | V [kn] | Cf before | Cf after | ΔCf | RT before [kN] | RT after [kN] | ΔRT [kN] | ΔRT |

- **A20** · `numeric_anchor` · char `3649–3783` · L66 · resolved_in_source

  > **设计点（Fn=0.260, 24.00 kn）**：RT 2109.49 → 2117.58 kN（**+0.38%**），Pe 26047.98 → 26147.97 kW（+0.38%）。传递函数 dRt%/dA% = **0.533**（≈摩擦阻力占位比）。

- **A21** · `table` · char `3812–4072` · L70 · resolved_in_source

  > | ΔA/A | A | RT [kN] | ΔRT | ΔPe |

- **A26** · `table` · char `5170–5515` · L96 · resolved_in_source

  > | 量 | 基准 | 本次 | 误差 | <3%? |

- **A27** · `statement` · char `5517–5704` · L104 · resolved_in_source

  > **结论**：高保真数值解与 ITTC-57 在带内平均偏差 +0.98%，即这条经验线在当前可达 Re 区间已被高保真证实到 **1% 以内**；回流写回的修正是 +0.72%（ΔRt +0.38%）。这不是「标定出大修正」，而是**机制证明 + 一致性的量化**：若未来高保真源（LES/试验）给出 >3% 的偏差，同一管线会把该偏差以可审计、可回滚的方式写进平台主链。

- **A28** · `table` · char `5721–6125` · L108 · resolved_in_source

  > | 门 | 判据 | 结果 |

- **A29** · `statement` · char `6127–6220` · L116 · resolved_in_source

  > 溯源复算：`ok=true`（工件 9 个逐一重算 sha256，父链无孤点=True，账本 prev 链完整=True，生效快照与账本末条一致=True，预测用的是账本值=True）。


说明：上表只摘每段的首行；多行资产的完整 quote（含表体全部行）在 `asset_manifest.json` 的 `locator.quote` 里，可机械复核 `md[start:end]==quote`。全部 29 条的 quote 均为源文唯一子串（29/29 通过）。

**登记中识别出的不可解析引用（7 条，全部落 `referenced_unresolved`，不做猜测补全）**：

| 资产 | 类 | 标签 |
|---|---|---|
| A04 | vcs_reference | 工作分支 agent/m14897（无 commit sha） |
| A06 | code_pointer | 高保真源 TensorLBM wall_model_les.flat_plate.run_flat_plate |
| A07 | code_pointer | 被标定系数消费点 backend/physics/holtrop/mennen.py:ittc57_cf |
| A09 | external_dataset | KCS 几何规格文件 docs/ex1/artifacts/kcs_spec_data.json |
| A11 | external_artifact_set | 9 个 sha256 流水线工件（01_hifi_plate_cf.json … figures/*.png） |
| A23 | external_figure | fig1_hifi_vs_reference.png（高保真 c_f vs ITTC-57/P-S） |
| A24 | external_figure | fig2_prediction_before_after.png（回流前后 Rt 与逐点 ΔRT） |

## ⑤ 注意点与局限

1. **本工序不背书上游数字**。13988 报告的 A_hat=0.075539、ΔRT +0.384%、误差表「<3%?」等结论只是被**定位并登记**（A15/A19/A20/A26），其真值不在本包验证范围内；本包也不产出任何 claim（契约 `classify_report_type=false`）。
2. **哈希被截断**：报告只披露 `6fc45dd1e21f8ba8…`、`3eeab056fd161a16…` 两个前缀（A18），完整 64 位值缺失 → 下游无法仅凭报告复算账本链；这是登记到的**上游证据缺口**，不是本包缺陷。
3. **7 条引用不可解析**：9 个工件文件、KCS 几何 JSON、两个代码指针、两个 PNG 只以仓库相对路径出现；本工作树（TensorKnowledge）内均不存在，故一律判 `referenced_unresolved`，**未拼接路径当既有事实**（A11 的 note 明确标注「拼接属推断」）。
4. **图件双重身份**：两 PNG 在源文里只有路径（不可解析），但平台 `figures[]` 含同名 PNG 字节，故 `resolution_check` 记 `present` 而 `resolution` 仍为 `referenced_unresolved`——两者口径不同，已在 note 中写明，避免被读成「已解析」。
5. **schema 口径**：仓内 `schemas/asset_manifest.v1.schema.json` 的 const 写死为 `wp-448-01`；本包用程序化派生的同构副本（`docs/wp-13988-01/asset_manifest.v1.schema.json`）校验，并在文件内注明「平台侧若有 schema 以平台为准」。信封则直接对仓内权威 `kf_result.v1.schema.json` 校验。
6. **§⑤ 局限来源**：上游报告的 6 条注意点（A25）只登记原文，其中「前缘入口过渡」「外推 1 个数量级」等对下游复用该系数是关键约束，抽取工序不得丢掉。
7. **未做的事（明确声明）**：未执行上游 `scripts/run_calib_reflux.py`（不在本工作树）；未联网核证任何外部数据（Zenodo/文献）；未读/写其它 report_id。

## ⑥ 误差判定（本工序可裁量 vs 基准，显式回答是否 <3%）

本工序为**登记类**工作包，不产生物理量，故「物理量 vs 实验/文献误差」不适用；改为对**机械可裁量**给出误差，基准取工作包契约：

| 量 | 基准（契约） | 本次 | 误差 | <3%? |
|---|---|---|---|---|
| markdown sha256 | `79d795…442b9` | `79d795674f0b13f828d8933af64612a1addb30cb8a8b903f7ab136f0508442b9` | 0（逐位相等） | 是（精确相等） |
| 源字符数 | 6222 | 6222 | 0% | 是 |
| locator 逐字命中 | quote ⊂ 源文且唯一 | 29/29 | 0% | 是 |
| 重复 ID | 0 | 29 个 ID / 29 唯一 | 0 | 是 |
| 独立复核 | 全项 pass | 11/11 | 0% | 是 |

**物理精度不适用声明**：本包未产生或比较任何阻力/功率等物理量，故不回答「物理量是否 <3%」；上游报告自身的误差判定（A26，含 1 项「否」：vs Prandtl-Schlichting −3.50%）已逐字登记，可供下游审计者复核。

## ⑦ 结果（全文唯一的 kf_result.v1 JSON 代码块）

```json
{
  "package_id": "wp-13988-01",
  "task_type": "01-asset-registration",
  "report_id": "13988",
  "provenance": {
    "source_uri": "tensor://reports/13988",
    "source_field": "markdown",
    "source_hash": "sha256:79d795674f0b13f828d8933af64612a1addb30cb8a8b903f7ab136f0508442b9",
    "source_chars": 6222,
    "source_bytes_utf8": 9227,
    "source_title": "H5-CALIB-REFLUX：高保真→经验系数回流机制（sha256 溯源贯通，全链 PASS）",
    "scenario_key": "ship-performance-platform",
    "contract_version": "1.0",
    "lane": "C",
    "work_package": "wp-13988-01",
    "generator": "docs/wp-13988-01/build_asset_manifest.py",
    "verifier": "docs/wp-13988-01/verify_manifest.py",
    "verification_status": "not_verified",
    "notes": "verification 由平台门计算；本工序不自标 verified"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-13988-01",
      "task_type": "01-asset-registration",
      "report_id": "13988",
      "source": {
        "uri": "tensor://reports/13988",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "79d795674f0b13f828d8933af64612a1addb30cb8a8b903f7ab136f0508442b9",
        "chars": 6222,
        "bytes_utf8": 9227,
        "title": "H5-CALIB-REFLUX：高保真→经验系数回流机制（sha256 溯源贯通，全链 PASS）",
        "scenario_key": "ship-performance-platform",
        "platform_id": 13988,
        "platform_mission_id": 14897,
        "platform_figures": [
          "fig1_hifi_vs_reference.png",
          "fig2_prediction_before_after.png"
        ],
        "platform_tags": [
          "H5-CALIB-REFLUX",
          "calibration",
          "sha256-provenance",
          "ITTC-57",
          "KCS",
          "reflux"
        ],
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/13988 (Bearer)",
        "local_copy": "runs/wp-13988-01/report_13988.md"
      },
      "counts": {
        "assets": 29,
        "by_class": {
          "document": 1,
          "heading": 1,
          "run_identity": 1,
          "vcs_reference": 1,
          "statement_set": 1,
          "code_pointer": 2,
          "numeric_anchor": 4,
          "external_dataset": 1,
          "table": 6,
          "external_artifact_set": 1,
          "mechanism_doc": 1,
          "repro_command": 1,
          "statement": 3,
          "negative_control": 1,
          "figure_declaration": 1,
          "external_figure": 2,
          "limitation_set": 1
        },
        "by_resolution": {
          "resolved_in_source": 22,
          "referenced_unresolved": 7
        },
        "resolved_in_source": 22,
        "referenced_unresolved": 7,
        "declared_absent": 0
      },
      "sections": [
        {
          "heading": "① 案例介绍（物理背景 / 几何 / 参数）",
          "start_line": 5
        },
        {
          "heading": "② 怎么做的（方法 / 流程 / 工具链）",
          "start_line": 15
        },
        {
          "heading": "③ 计算结果（程序化注入，零手抄）",
          "start_line": 35
        },
        {
          "heading": "④ 结果图",
          "start_line": 79
        },
        {
          "heading": "⑤ 注意点（坑 / 局限 / 适用范围）",
          "start_line": 85
        },
        {
          "heading": "⑥ 误差判定（逐项 vs 基准，显式回答是否 <3%）",
          "start_line": 94
        },
        {
          "heading": "判据自检（机器可裁）",
          "start_line": 106
        }
      ],
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "document",
          "label": "报告正文（markdown 全文）",
          "in_report_section": "(document)",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 6222,
            "start_line": 0,
            "end_line": 117,
            "quote": "# H5-CALIB-REFLUX：高保真 → 经验系数回流（sha256 溯源贯通）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256_over_markdown_bytes",
            "result": "resolved",
            "detail": "sha256(markdown.encode('utf-8')) == contract source_hash; coverage = whole document"
          },
          "note": "整篇 markdown 即源资产；sha256 见 source.hash（与契约 source_hash 一致），覆盖全文字符"
        },
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "报告标题",
          "in_report_section": "(document)",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 43,
            "start_line": 0,
            "end_line": 1,
            "quote": "# H5-CALIB-REFLUX：高保真 → 经验系数回流（sha256 溯源贯通）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "一级标题；与平台 title 字段同源"
        },
        {
          "asset_id": "A03",
          "asset_class": "run_identity",
          "label": "任务身份与总判定（m14897 / agent/m14897 / PASS / 工件根）",
          "in_report_section": "(document)",
          "locator": {
            "method": "char_span",
            "start_char": 45,
            "end_char": 124,
            "start_line": 2,
            "end_line": 3,
            "quote": "任务 m14897 · 分支 agent/m14897 · 判定 **PASS** · 工件 `artifacts/m14897_calib_reflux/`",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "单行任务头；工件根路径 artifacts/m14897_calib_reflux/ 在此声明，是本报告唯一给出的工件目录"
        },
        {
          "asset_id": "A04",
          "asset_class": "vcs_reference",
          "label": "工作分支 agent/m14897（无 commit sha）",
          "in_report_section": "(document)",
          "locator": {
            "method": "char_span",
            "start_char": 45,
            "end_char": 124,
            "start_line": 2,
            "end_line": 3,
            "quote": "任务 m14897 · 分支 agent/m14897 · 判定 **PASS** · 工件 `artifacts/m14897_calib_reflux/`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "git_ref_resolution_in_this_worktree",
            "result": "unresolved",
            "detail": "本工作树 refs 中检索 agent/m14897；报告亦未给 commit sha，故不可解析到提交对象",
            "refs_scanned": 427
          },
          "note": "报告只给分支名，未给 commit 对象标识；本工作树（TensorKnowledge）无该分支，不可解析到具体提交"
        },
        {
          "asset_id": "A05",
          "asset_class": "statement_set",
          "label": "①案例介绍核心声明（问题 / 高保真源 / 被标定系数 / 验证船型）",
          "in_report_section": "① 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 153,
            "end_char": 822,
            "start_line": 6,
            "end_line": 13,
            "quote": "**问题**：平台的阻力/推进/附连水链全部以 ITTC-1957 摩擦线为唯一摩擦基准 `C_F(Re)=A/(log10Re-2)^2, A=0.075`（m2082「阻力族并一」后的唯一实现 `backend/physics/holtrop/mennen.py:ittc57_cf`）。这条线是 1957 年拟合的经验相关线，而平台已有真数值高保真能力（TensorLBM 平板边界层）。缺的正是**闭环**：高保真结果如何以可审计、可复算、可回滚的方式改写这条经验系数。\n\n**高保真源**：TensorLBM `wall_model_les.flat_plate.run_flat_plate` —— 零压梯度平板湍流边界层的数值解（Spalding 复合壁律 kappa=0.41/B=5.2 + Coles 尾迹 Pi=0.45，动量积分 dθ/dx=c_f/2 推进），每步真数值、无查表。\n\n**被标定系数**：`ITTC57_A = 0.075`（无量纲）。**消费点**：`backend/physics/holtrop/mennen.py:ittc57_cf`。\n\n**验证船型**：KCS（KRISO 集装箱船，公开船型），几何取自 `docs/ex1/artifacts/kcs_spec_data.json`，先过几何门：Cb_lib=0.6509 vs nabla/(L·B·T)=0.650499，偏差 0.062% (<2%)；L/B=7.143，B/T=2.981，nabla=52030.0 m³。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "四段声明原文（含空行）；只登记不换算。高保真源与消费点的代码指针另登记为 A06/A07"
        },
        {
          "asset_id": "A06",
          "asset_class": "code_pointer",
          "label": "高保真源 TensorLBM wall_model_les.flat_plate.run_flat_plate",
          "in_report_section": "① 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 394,
            "end_char": 556,
            "start_line": 8,
            "end_line": 9,
            "quote": "**高保真源**：TensorLBM `wall_model_les.flat_plate.run_flat_plate` —— 零压梯度平板湍流边界层的数值解（Spalding 复合壁律 kappa=0.41/B=5.2 + Coles 尾迹 Pi=0.45，动量积分 dθ/dx=c_f/2 推进），每步真数值、无查表。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "repo_relative_path_resolution_in_worktree",
            "result": "unresolved",
            "searched_count": 1,
            "searched": [
              "wall_model_les.flat_plate.run_flat_plate"
            ],
            "detail": "仅在本工作树内检索报告逐字给出的相对路径（不联网、不猜路径、不臆造地址）",
            "worktree": "/root/tp-agent/work/m15771"
          },
          "note": "跨仓代码指针（TensorLBM）；本工作树内不存在该路径，未逐行核对实现"
        },
        {
          "asset_id": "A07",
          "asset_class": "code_pointer",
          "label": "被标定系数消费点 backend/physics/holtrop/mennen.py:ittc57_cf",
          "in_report_section": "① 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 558,
            "end_char": 646,
            "start_line": 10,
            "end_line": 11,
            "quote": "**被标定系数**：`ITTC57_A = 0.075`（无量纲）。**消费点**：`backend/physics/holtrop/mennen.py:ittc57_cf`。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "repo_relative_path_resolution_in_worktree",
            "result": "unresolved",
            "searched_count": 1,
            "searched": [
              "backend/physics/holtrop/mennen.py:ittc57_cf"
            ],
            "detail": "仅在本工作树内检索报告逐字给出的相对路径（不联网、不猜路径、不臆造地址）",
            "worktree": "/root/tp-agent/work/m15771"
          },
          "note": "ship-performance-platform 仓内路径；本工作树内不存在，未核对 ittc57_cf 默认 A=0.075"
        },
        {
          "asset_id": "A08",
          "asset_class": "numeric_anchor",
          "label": "几何门数值（Cb_lib / Cb_geom / L/B / B/T / nabla）",
          "in_report_section": "① 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 648,
            "end_char": 822,
            "start_line": 12,
            "end_line": 13,
            "quote": "**验证船型**：KCS（KRISO 集装箱船，公开船型），几何取自 `docs/ex1/artifacts/kcs_spec_data.json`，先过几何门：Cb_lib=0.6509 vs nabla/(L·B·T)=0.650499，偏差 0.062% (<2%)；L/B=7.143，B/T=2.981，nabla=52030.0 m³。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "单行几何门声明：Cb 偏差 0.062% (<2%)；KCS 几何文件本体见 A09"
        },
        {
          "asset_id": "A09",
          "asset_class": "external_dataset",
          "label": "KCS 几何规格文件 docs/ex1/artifacts/kcs_spec_data.json",
          "in_report_section": "① 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 648,
            "end_char": 822,
            "start_line": 12,
            "end_line": 13,
            "quote": "**验证船型**：KCS（KRISO 集装箱船，公开船型），几何取自 `docs/ex1/artifacts/kcs_spec_data.json`，先过几何门：Cb_lib=0.6509 vs nabla/(L·B·T)=0.650499，偏差 0.062% (<2%)；L/B=7.143，B/T=2.981，nabla=52030.0 m³。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "repo_relative_path_resolution_in_worktree",
            "result": "unresolved",
            "searched_count": 1,
            "searched": [
              "docs/ex1/artifacts/kcs_spec_data.json"
            ],
            "detail": "仅在本工作树内检索报告逐字给出的相对路径（不联网、不猜路径、不臆造地址）",
            "worktree": "/root/tp-agent/work/m15771"
          },
          "note": "仓库相对路径；本工作树内不存在，几何门无法复算（只能登记上游结论）"
        },
        {
          "asset_id": "A10",
          "asset_class": "table",
          "label": "五步流水线工件登记表（S1/S2/S3/S4/S5，9 行）",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 884,
            "end_char": 1744,
            "start_line": 18,
            "end_line": 29,
            "quote": "| 步 | 做什么 | 工件 | 证据等级 |\n|---|---|---|---|\n| S1_hifi | 高保真平板边界层局部摩阻站点表（真数值解，非查表） | `01_hifi_plate_cf.json` | REAL |\n| S2_calibrate | 系数反解 + 不确定度 + 物理边界 + 负控 | `02_calibration.json` | REAL |\n| S3_writeback | 回写记录：账本 entry + 生效快照 + 三级哈希链 | `03_writeback.json` | REAL |\n| S3_active | 当前生效系数快照（消费者读取点） | `coefficient_store/active.json` | REAL |\n| S3_ledger | 追加式系数账本（prev 哈希链，可回滚） | `coefficient_store/ledger.jsonl` | REAL |\n| S4_predict | 回流前后逐点对照 + 传递函数 + 剂量响应 | `04_prediction_before_after.json` | REAL |\n| S4_table | 对照数表（before/after/Δ） | `04_prediction_before_after.csv` | REAL |\n| S5_fig_fig1_hifi_vs_reference.png | S1 高保真局部摩阻 vs ITTC-57 局部线与 Prandtl-Schlichting；右=带内偏差 | `figures/fig1_hifi_vs_reference.png` | REAL |\n| S5_fig_fig2_prediction_before_after.png | S4 回流前后 KCS 总阻力曲线与逐点 ΔRT；传递函数 dRt/dA 一并标注 | `figures/fig2_prediction_before_after.png` | REAL |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "表头+分隔+9 行；含 9 个工件文件名与上游自报证据等级 REAL（本工序不复核等级）"
        },
        {
          "asset_id": "A11",
          "asset_class": "external_artifact_set",
          "label": "9 个 sha256 流水线工件（01_hifi_plate_cf.json … figures/*.png）",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 884,
            "end_char": 1744,
            "start_line": 18,
            "end_line": 29,
            "quote": "| 步 | 做什么 | 工件 | 证据等级 |\n|---|---|---|---|\n| S1_hifi | 高保真平板边界层局部摩阻站点表（真数值解，非查表） | `01_hifi_plate_cf.json` | REAL |\n| S2_calibrate | 系数反解 + 不确定度 + 物理边界 + 负控 | `02_calibration.json` | REAL |\n| S3_writeback | 回写记录：账本 entry + 生效快照 + 三级哈希链 | `03_writeback.json` | REAL |\n| S3_active | 当前生效系数快照（消费者读取点） | `coefficient_store/active.json` | REAL |\n| S3_ledger | 追加式系数账本（prev 哈希链，可回滚） | `coefficient_store/ledger.jsonl` | REAL |\n| S4_predict | 回流前后逐点对照 + 传递函数 + 剂量响应 | `04_prediction_before_after.json` | REAL |\n| S4_table | 对照数表（before/after/Δ） | `04_prediction_before_after.csv` | REAL |\n| S5_fig_fig1_hifi_vs_reference.png | S1 高保真局部摩阻 vs ITTC-57 局部线与 Prandtl-Schlichting；右=带内偏差 | `figures/fig1_hifi_vs_reference.png` | REAL |\n| S5_fig_fig2_prediction_before_after.png | S4 回流前后 KCS 总阻力曲线与逐点 ΔRT；传递函数 dRt/dA 一并标注 | `figures/fig2_prediction_before_after.png` | REAL |",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "repo_relative_path_resolution_in_worktree",
            "result": "unresolved",
            "searched_count": 9,
            "searched": [
              "artifacts/m14897_calib_reflux/01_hifi_plate_cf.json",
              "artifacts/m14897_calib_reflux/02_calibration.json",
              "artifacts/m14897_calib_reflux/03_writeback.json",
              "artifacts/m14897_calib_reflux/04_prediction_before_after.csv",
              "artifacts/m14897_calib_reflux/04_prediction_before_after.json",
              "artifacts/m14897_calib_reflux/coefficient_store/active.json",
              "artifacts/m14897_calib_reflux/coefficient_store/ledger.jsonl",
              "artifacts/m14897_calib_reflux/figures/fig1_hifi_vs_reference.png",
              "artifacts/m14897_calib_reflux/figures/fig2_prediction_before_after.png"
            ],
            "detail": "仅在本工作树内检索报告逐字给出的相对路径（不联网、不猜路径、不臆造地址）",
            "worktree": "/root/tp-agent/work/m15771"
          },
          "note": "报告只给相对文件名，全路径需与 A03 声明的工件根拼接（拼接属推断，报告未逐字给出全路径）；本工作树内文件均不存在"
        },
        {
          "asset_id": "A12",
          "asset_class": "mechanism_doc",
          "label": "回写机制（ledger.jsonl 哈希链 / active.json 生效快照 / 回滚语义）",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1746,
            "end_char": 1941,
            "start_line": 30,
            "end_line": 31,
            "quote": "**回写机制**（本任务的核心增量）：`coefficient_store/ledger.jsonl` 追加式账本，每条 entry 带 `prev_entry_sha256` 形成哈希链；`active.json` 为生效快照、原子替换写入，其 `head_sha256` 必须等于账本末条哈希。消费者**从账本读**系数（不是重新传参）。回滚=追加一条恢复旧值的 entry，不删不盖。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "单段机制声明；consumer-reads-ledger 的实现体未随报告提供"
        },
        {
          "asset_id": "A13",
          "asset_class": "repro_command",
          "label": "一键复现命令（run / verify）",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1943,
            "end_char": 2083,
            "start_line": 32,
            "end_line": 33,
            "quote": "**一键复现**：`python scripts/run_calib_reflux.py run` → 22 s；`python scripts/run_calib_reflux.py verify` → 第三方复算（重算全部 sha256 + 父链 + 账本 + 消费一致性）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "命令指向上游仓 scripts/run_calib_reflux.py；本工作树内不存在，未执行"
        },
        {
          "asset_id": "A14",
          "asset_class": "statement",
          "label": "S1 高保真证据（站点 238，Re_x 区间，闭包类型）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 2107,
            "end_char": 2229,
            "start_line": 36,
            "end_line": 37,
            "quote": "**S1 高保真证据**：站点数 238，Re_x ∈ [2.020e+07, 2.020e+08]，闭包RANS-grade integral boundary layer (not DNS/LES resolved turbulence)。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "站点数与 Re 区间原文；站点表本体为 A11 列出的 01_hifi_plate_cf.json"
        },
        {
          "asset_id": "A15",
          "asset_class": "numeric_anchor",
          "label": "S2 标定结果（A_hat=0.075539 / σ_A / 残差 RMS / 物理带 / clamped）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 2231,
            "end_char": 2367,
            "start_line": 38,
            "end_line": 39,
            "quote": "**S2 标定**：A_hat = **0.075539**（ΔA/A = +0.72%），σ_A = 7.239e-05（0.097%），残差 RMS = 1.456% / max = 3.143%，物理带 [0.0700, 0.0800]，clamped=False。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "单一数字锚点行；数值仅登记，不复算"
        },
        {
          "asset_id": "A16",
          "asset_class": "negative_control",
          "label": "S2 负控（合成线上数据还原 A，误差 +0.00000%）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 2369,
            "end_char": 2434,
            "start_line": 40,
            "end_line": 41,
            "quote": "**S2 负控**：合成线上数据 → A 还原 0.075000，误差 **+0.00000%**（容差 0.5%）→ PASS。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "负控结论原文；合成数据与脚本未随报告提供"
        },
        {
          "asset_id": "A17",
          "asset_class": "table",
          "label": "S2 带敏感性表（Re_x 下界 1e7/2e7/5e7，3 行）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 2465,
            "end_char": 2663,
            "start_line": 44,
            "end_line": 49,
            "quote": "| Re_x 下界 | 站点数 | A_hat | ΔA/A | 残差 RMS |\n|---|---|---|---|---|\n| 1e+07 | 238 | 0.075539 | +0.72% | 1.456% |\n| 2e+07 | 238 | 0.075539 | +0.72% | 1.456% |\n| 5e+07 | 151 | 0.076396 | +1.86% | 0.611% |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "表头+分隔+3 行；5e7 档站点数降为 151、ΔA/A 变 +1.86%"
        },
        {
          "asset_id": "A18",
          "asset_class": "numeric_anchor",
          "label": "S3 回写记录（ledger seq=0，entry/head sha256 前缀）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 2665,
            "end_char": 2754,
            "start_line": 50,
            "end_line": 51,
            "quote": "**S3 回写**：账本 seq=0，entry_sha256=`6fc45dd1e21f8ba8…`，生效快照 head_sha256=`3eeab056fd161a16…`。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "哈希值在原文中被截断（6fc45dd1e21f8ba8… / 3eeab056fd161a16…），完整 64 位值未给出，下游无法独立复算链（另见 A29）"
        },
        {
          "asset_id": "A19",
          "asset_class": "table",
          "label": "S4 回流前后对照表（KCS，8 个 Fn 点）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 2800,
            "end_char": 3647,
            "start_line": 54,
            "end_line": 64,
            "quote": "| Fn | V [kn] | Cf before | Cf after | ΔCf | RT before [kN] | RT after [kN] | ΔRT [kN] | ΔRT |\n|---|---|---|---|---|---|---|---|---|\n| 0.150 | 13.85 | 0.0014697 | 0.0014803 | +0.721% | 486.74 | 489.62 | +2.88 | +0.592% |\n| 0.180 | 16.62 | 0.0014377 | 0.0014480 | +0.716% | 729.57 | 733.63 | +4.06 | +0.556% |\n| 0.200 | 18.46 | 0.0014196 | 0.0014298 | +0.719% | 952.38 | 957.32 | +4.94 | +0.519% |\n| 0.220 | 20.31 | 0.0014036 | 0.0014137 | +0.720% | 1245.72 | 1251.63 | +5.91 | +0.474% |\n| 0.240 | 22.16 | 0.0013892 | 0.0013992 | +0.720% | 1616.99 | 1623.95 | +6.96 | +0.430% |\n| 0.260 | 24.00 | 0.0013761 | 0.0013860 | +0.719% | 2109.49 | 2117.58 | +8.09 | +0.384% |\n| 0.280 | 25.85 | 0.0013642 | 0.0013740 | +0.718% | 2799.39 | 2808.70 | +9.31 | +0.333% |\n| 0.300 | 27.70 | 0.0013532 | 0.0013630 | +0.724% | 3522.12 | 3532.72 | +10.60 | +0.301% |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "表头+分隔+8 行；RT before/after 与 ΔRT 全值"
        },
        {
          "asset_id": "A20",
          "asset_class": "numeric_anchor",
          "label": "设计点结果与传递函数（RT 2109.49→2117.58 kN，dRt%/dA%=0.533）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 3649,
            "end_char": 3783,
            "start_line": 65,
            "end_line": 66,
            "quote": "**设计点（Fn=0.260, 24.00 kn）**：RT 2109.49 → 2117.58 kN（**+0.38%**），Pe 26047.98 → 26147.97 kW（+0.38%）。传递函数 dRt%/dA% = **0.533**（≈摩擦阻力占位比）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "设计点单行；Pe 26047.98→26147.97 kW 同在该行"
        },
        {
          "asset_id": "A21",
          "asset_class": "table",
          "label": "剂量-响应表（ΔA/A = ±1/3/5%，6 行）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 3812,
            "end_char": 4072,
            "start_line": 69,
            "end_line": 75,
            "quote": "| ΔA/A | A | RT [kN] | ΔRT | ΔPe |\n|---|---|---|---|---|\n| -5.0% | 0.071250 | 2053.19 | -2.669% | -2.669% |\n| -3.0% | 0.072750 | 2075.71 | -1.601% | -1.601% |\n| -1.0% | 0.074250 | 2098.23 | -0.534% | -0.534% |\n| +1.0% | 0.075750 | 2120.75 | +0.534% | +0.534% |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "表头+分隔+6 行；ΔRT 与 ΔPe 逐行等值（线性传递的体现）"
        },
        {
          "asset_id": "A22",
          "asset_class": "figure_declaration",
          "label": "④结果图两处图位声明（fig1 / fig2 路径与说明）",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 4186,
            "end_char": 4409,
            "start_line": 80,
            "end_line": 83,
            "quote": "`artifacts/m14897_calib_reflux/figures/fig1_hifi_vs_reference.png` —— 高保真局部摩阻 vs ITTC-57 局部线与 Prandtl-Schlichting（右图=带内偏差）。\n\n`artifacts/m14897_calib_reflux/figures/fig2_prediction_before_after.png` —— 回流前后 KCS 总阻力曲线与逐点 ΔRT。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "两条图位声明原文；图件字节本体见 A23/A24"
        },
        {
          "asset_id": "A23",
          "asset_class": "external_figure",
          "label": "fig1_hifi_vs_reference.png（高保真 c_f vs ITTC-57/P-S）",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 4186,
            "end_char": 4309,
            "start_line": 80,
            "end_line": 81,
            "quote": "`artifacts/m14897_calib_reflux/figures/fig1_hifi_vs_reference.png` —— 高保真局部摩阻 vs ITTC-57 局部线与 Prandtl-Schlichting（右图=带内偏差）。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform_figures_field",
            "result": "present",
            "platform_figure_name": "fig1_hifi_vs_reference.png",
            "detail": "图件字节存在于平台记录 figures[]；markdown 仅给仓库相对路径，本工作树内无该文件"
          },
          "note": "报告内为仓库相对路径；本工作树内文件不存在。平台记录 figures[0] 有同名 PNG（见 resolution_check）"
        },
        {
          "asset_id": "A24",
          "asset_class": "external_figure",
          "label": "fig2_prediction_before_after.png（回流前后 Rt 与逐点 ΔRT）",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 4311,
            "end_char": 4409,
            "start_line": 82,
            "end_line": 83,
            "quote": "`artifacts/m14897_calib_reflux/figures/fig2_prediction_before_after.png` —— 回流前后 KCS 总阻力曲线与逐点 ΔRT。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform_figures_field",
            "result": "present",
            "platform_figure_name": "fig2_prediction_before_after.png",
            "detail": "图件字节存在于平台记录 figures[]；markdown 仅给仓库相对路径，本工作树内无该文件"
          },
          "note": "同上；平台记录 figures[1] 有同名 PNG（见 resolution_check）"
        },
        {
          "asset_id": "A25",
          "asset_class": "limitation_set",
          "label": "⑤注意点（6 条：局部/平均量、前缘过渡、外推、证据分层、拒用不可核证试验表、KCS 输入简化）",
          "in_report_section": "⑤ 注意点",
          "locator": {
            "method": "char_span",
            "start_char": 4436,
            "end_char": 5136,
            "start_line": 86,
            "end_line": 92,
            "quote": "1. **局部量 vs 平均量**：ITTC-57 是 **平均** 摩阻线，平板求解器给 **局部** c_f。直接相比会凭空造出 ~2 倍偏差；必须用平均线的微分恒等式 `cf = A(L-2)^-2 [1-2/(ln10(L-2))]`（已实现为 `ittc57_local_exact`）。\n2. **前缘入口过渡段**：求解器从 Re_theta=1e4 起步，Re_x ≲ 1e7 处尾迹未充分建立。标定带下界取 2e7（敏感性表给出 1e7/2e7/5e7 三档，ΔA 漂移 <3%）。\n3. **外推**：高保真带覆盖到 Re≈2.0e+08，KCS 26 kn 的 Re≈2.6e9 —— 差 1 个数量级。因此 A 被夹在物理带 ±0.0050 内，越界即 `clamped=True` 登记，不静默吸收。\n4. **证据等级分层**：高保真源是 RANS 级积分边界层（壁律闭包 kappa/B/Pi 取自文献，未在本轮重标定），不是 DNS/LES 解析湍流。它自身与 ITTC-57 局部线平均偏差 +0.98%、与 P-S 最大偏差 6.16%。\n5. **没有采用不可核证的试验表**：仓库里若干「公开模型试验表」只有 `KRISO_tank` 之类标签、无逐项数字化出处（WITHHELD 级），本轮拒绝把它们当高保真锚——否则等于用不可核证数字污染系数账本。\n6. **KCS 输入简化**：规范文件未数字化球鼻艏横截面积，ABT=0、无附体、无艉封板；这些在 Holtrop 输出 assumptions 里逐条回报，不影响回流前后的**差值**（只影响绝对值）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "6 条局限原文；其中第 5 条是上游对 WITHHELD 级试验表的拒用声明"
        },
        {
          "asset_id": "A26",
          "asset_class": "table",
          "label": "⑥误差判定表（5 行，逐项 <3%? 列）",
          "in_report_section": "⑥ 误差判定",
          "locator": {
            "method": "char_span",
            "start_char": 5170,
            "end_char": 5515,
            "start_line": 95,
            "end_line": 102,
            "quote": "| 量 | 基准 | 本次 | 误差 | <3%? |\n|---|---|---|---|---|\n| 高保真局部 c_f（带内均值） | ITTC-57 局部线 | 数值解 | +0.98% (max 2.83%) | 是 |\n| 高保真局部 c_f（带内均值） | Prandtl-Schlichting | 数值解 | -3.50% (max 6.16%) | 否 |\n| 反解 A | 已知真值 0.075（负控合成数据） | A_hat | +0.00000% | 是 |\n| 标定残差 | 拟合线自身 | 高保真站点 | RMS 1.456% | 是 |\n| 回流后 Rt（设计点） | 回流前 Rt | after | +0.384% | 变化量本身 <3%（幅度即结论） |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "表头+分隔+5 行；含 1 行「否」（vs Prandtl-Schlichting -3.50%）——上游未粉饰"
        },
        {
          "asset_id": "A27",
          "asset_class": "statement",
          "label": "⑥结论（ITTC-57 在带内被证实到 1% 以内；写回 +0.72%）",
          "in_report_section": "⑥ 误差判定",
          "locator": {
            "method": "char_span",
            "start_char": 5517,
            "end_char": 5704,
            "start_line": 103,
            "end_line": 104,
            "quote": "**结论**：高保真数值解与 ITTC-57 在带内平均偏差 +0.98%，即这条经验线在当前可达 Re 区间已被高保真证实到 **1% 以内**；回流写回的修正是 +0.72%（ΔRt +0.38%）。这不是「标定出大修正」，而是**机制证明 + 一致性的量化**：若未来高保真源（LES/试验）给出 >3% 的偏差，同一管线会把该偏差以可审计、可回滚的方式写进平台主链。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "结论原文；属上游判断，本工序不背书也不改写"
        },
        {
          "asset_id": "A28",
          "asset_class": "table",
          "label": "判据自检门表 G1-G5（5 行，全 PASS）",
          "in_report_section": "判据自检（机器可裁）",
          "locator": {
            "method": "char_span",
            "start_char": 5721,
            "end_char": 6125,
            "start_line": 107,
            "end_line": 114,
            "quote": "| 门 | 判据 | 结果 |\n|---|---|---|\n| G1_chain_complete | 账本 prev 链与生效快照一致 | PASS |\n| G2_negative_control | 合成线上数据还原 A，误差 +0.0000% ≤ 0.5% | PASS |\n| G3_physical_bound | A_applied=0.075539 ∈ [0.06999999999999999, 0.08]，clamped=False | PASS |\n| G4_consumer_reads_ledger | S4 使用的系数取自 active.json（不是重新传参） | PASS |\n| G5_before_after_effect | 设计点 Fn=0.26: RT 2109.49 → 2117.58 kN (+0.384%)；传递函数 dRt/dA=0.533 | PASS |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "表头+分隔+5 行；上游自报 PASS，本工序只登记（verification 归平台门）"
        },
        {
          "asset_id": "A29",
          "asset_class": "statement",
          "label": "溯源复算声明（ok=true，9 工件逐一重算 sha256）",
          "in_report_section": "判据自检（机器可裁）",
          "locator": {
            "method": "char_span",
            "start_char": 6127,
            "end_char": 6220,
            "start_line": 115,
            "end_line": 116,
            "quote": "溯源复算：`ok=true`（工件 9 个逐一重算 sha256，父链无孤点=True，账本 prev 链完整=True，生效快照与账本末条一致=True，预测用的是账本值=True）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] 与登记 quote 逐字节相等"
          },
          "note": "声明复算 ok=true；但报告内仅披露 2 个被截断的哈希（A18），完整工件清单不可从报告侧复算"
        }
      ],
      "claims": [],
      "claims_note": "按工作包契约 objective.classify_report_type=false、notes 允许 claims=[]：本工序只登记源资产与定位，不做 claim 抽取与判定；claim 抽取属下游工序。任何结论都未标 verified（verification 由平台门计算）。",
      "integrity": {
        "quote_uniqueness": "all 29 quotes confirmed unique substrings of the source markdown (docs/wp-13988-01/verify_manifest.py)",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true
      }
    }
  },
  "claims": []
}
```

## ⑧ 自检：逐条对照 acceptance

| acceptance | 结果 | 证据 |
|---|---|---|
| valid_json | ✅ | `artifacts/wp-13988-01/asset_manifest.json` 可 `json.load`，37547 bytes |
| schema_pass | ✅ | 信封过 `schemas/kf_result.v1.schema.json`；manifest 过派生 schema；双反证均按预期失败 |
| source_locator_resolvable | ✅ | 29/29 quote 唯一且在源文；char 切片逐字节相等 |
| source_hash_matches | ✅ | `79d795674f0b13f828d8933af64612a1addb30cb8a8b903f7ab136f0508442b9` == 契约（构建期与复核期各算一次） |
| no_duplicate_ids | ✅ | asset_id 29/29 唯一；claims 为空 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅（空集成立） | `claims=[]`，无断言即无未证断言；`do_not_mark_claims_as_verified` 亦满足（无 verified 标记） |

构建期自检（`checks.json`，11/11 pass）：

| check | status | detail |
|---|---|---|
| source_hash_matches | pass | sha256(markdown)=79d795674f0b13f828d8933af64612a1addb30cb8a8b903f7ab136f0508442b9 contract=79d795674f0b13f828d8933af64612a1addb30cb8a8b903f7ab136f0508442b9 |
| source_chars_match_contract | pass | chars=6222 contract=6222 bytes_utf8=9227 |
| report_id_matches | pass | platform id=13988 |
| source_locator_resolvable | pass | all 29 locators are unique substrings of source markdown (failures: none) |
| no_duplicate_ids | pass | 29 asset_id, 29 unique; claims=[] so no claim_id collision possible |
| all_claims_have_evidence_or_explicit_unresolved_status | pass | claims=[] (objective.classify_report_type=false, no extraction in this work package); constraint vacuously satisfied, no claim asserted |
| valid_json | pass | manifest re-parsed from disk; 37547 bytes |
| manifest_schema_pass | pass | asset_manifest validates against docs/wp-13988-01/asset_manifest.v1.schema.json (derived local copy) |
| manifest_schema_negative_control | pass | negative control: manifest without 'counts' is rejected as expected |
| schema_pass | pass | kf_result envelope validates against schemas/kf_result.v1.schema.json (sha256=170dba8b0b5d54012490aaadc0b68647a9520ecb869e9d03f873afb99b74c076) / negative control: envelope missing required keys is rejected as expected |
| durable_mirror_identical | pass | docs/wp-13988-01/asset_manifest.json sha256 == artifacts copy sha256 (096b1a8741db4fddfa8fb7a968053b9e65a5a10a8ea7f6907757dd545be9b30b) |

独立复核（`verification.json`，重新取源）：

| check | status | detail |
|---|---|---|
| source_hash_matches | pass | fresh sha256=79d795674f0b13f828d8933af64612a1addb30cb8a8b903f7ab136f0508442b9 contract=79d795674f0b13f828d8933af64612a1addb30cb8a8b903f7ab136f0508442b9 |
| source_chars_match_contract | pass | fresh chars=6222 contract=6222 |
| valid_json | pass | artifacts/wp-13988-01/asset_manifest.json re-parsed (sha256=096b1a8741db4fddfa8fb7a968053b9e65a5a10a8ea7f6907757dd545be9b30b) |
| manifest_hash_matches_fresh_source | pass | manifest source.hash == fresh sha256 of API markdown |
| source_locator_resolvable | pass | 29 assets: quote unique=29/29, char-span exact=29/29 (offenders span=[] unique=[]) |
| no_duplicate_ids | pass | asset_id 29/29 unique, claim_id 0/0 unique |
| all_claims_have_evidence_or_explicit_unresolved_status | pass | claims=0; every claim carries evidence or an explicit status |
| referenced_unresolved_still_unresolved | pass | 4 path-referenced assets re-tested against the worktree (of 7 referenced_unresolved); offenders=none |
| schema_pass | pass | manifest validates against docs/wp-13988-01/asset_manifest.v1.schema.json / envelope validates against schemas/kf_result.v1.schema.json / negative control: schema rejects envelope missing required keys |
| envelope_source_hash_matches | pass | envelope provenance.source_hash == sha256(fresh markdown) |
| no_asset_marked_verified | pass | no asset/locator field promotes a claim to verified (offenders=none) |

## ⑨ 复现（repro_cmd）

    cd "$(git rev-parse --show-toplevel)" && \
    python3 scripts/kf_fetch_13988.py && \
    python3 docs/wp-13988-01/build_asset_manifest.py && \
    python3 docs/wp-13988-01/verify_manifest.py && \
    python3 docs/wp-13988-01/plot_coverage.py && \
    python3 docs/wp-13988-01/build_report.py --post

（env：`TENSOR_API_BASE`、`TENSOR_AGENT_USER`、`TENSOR_AGENT_PASS`；全流程无网络外部依赖，只打平台 API。）
