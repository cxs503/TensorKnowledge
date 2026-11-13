# KF-RESULT wp-13946-01

**工序**：`01-asset-registration`（lane C）｜**源**：`tensor://reports/13946`（字段 `markdown`）
**源标题**：直剪盒独立复核：压板伺服载荷偏置是控制器误差（drag→bedref），装置仍未稳态
**scenario_key**：`shear_cell_servo_audit`｜**报告**：`13946`

## ① 本工序做了什么

把 report `13946` 的 markdown 作为**唯一源**登记成资产清单：确认 report_id 与 markdown 字节哈希、
逐条定位报告中可解析的结构（表格/参数/方法/结论/图注/复现命令）与**引用了但本工作树不可解析**的工件
（跨仓代码/脚本/结果集/测试），并显式登记报告自己声明缺失的入口（μ vs 实验的实验数据集）。

- 资产数 **23**：`resolved_in_source` **14** /
  `referenced_unresolved` **8** /
  `declared_absent` **1**。
- **不抽知识**：`claims=[]`（契约 `objective.register_assets=true`、`classify_report_type=false`，
  「claims 允许为空数组」）——报告里的 F1/F2/F3 结论只作为资产 A04 原文登记，未被升级成 claim、未标 verified。
- 源哈希 `sha256:eb37b6effecdfc9396ded7a80f236173e234f2785fd984a948efba4a9b671072`，与契约一致；字符数 5534（= 契约值）。
- **未**做：附件字节校验（图件二进制）、跨仓代码解析、报告结论的独立复算（见 ⑤）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取源**：`GET $TENSOR_API_BASE/tensor/reports/13946`（`/auth/login` 取 token）→ `markdown` 字段。
   直连库 `psql -d tensorplatform -c "select markdown from tensor_reports where id=13946"` **被拒**
   （`ERROR: permission denied for table tensor_reports`），故 API 是唯一取源信道；单信道限制已记在 ⑤。
2. **哈希门控**：`scripts/kf_fetch_13946.py` 落盘前重算 `sha256(markdown)` 并断言等于契约值
   （不匹配即 `exit 2`，不落盘）。
3. **定位**：`scripts/kf_register_13946.py` 用**行区间锚**（非手抄）切片，逐条断言
   `md.count(quote)==1`（全文唯一）且 `md[start_char:end_char]==quote`（char span 与 quote 不可能漂移）；
   一行的密集引用（A16–A23）改用**精确子串锚**，避免三条资产共用同一行定位。
4. **缺失不臆造**：跨仓路径/通配目录/未给 URL 或 commit 的引用一律 `referenced_unresolved`
   并写清原因；报告显式说没有的数据集记 `declared_absent`。**没有给出任何编造地址**。
5. **schema**：`schemas/asset_manifest.v1.schema.json` 的 `package_id`/`report_id` 是别的包（`wp-448-01`/`448`）
   的 `const`，直接复用无法校验本包；做法是新增**钉住本包身份**的同构 schema
   `schemas/asset_manifest.wp-13946-01.schema.json`，不改共享文件（否则会静默放宽其它包的检查）。
6. **独立复核**：`scripts/kf_verify_13946.py` **不 import 登记器**，重新从 API 取 markdown、重算哈希、
   重新解析每个 locator，逐条映射 acceptance；结果写 `verification.json`。
7. **测试**：`tests/test_kf_wp13946_01_asset_manifest.py` 双层——离线层（committed 清单 vs 运行副本）
   + 在线层（vs 服务端字节，API 不可达时 skip 而非 pass）。
8. **出图**：`scripts/kf_figures_13946.py` 只读清单 JSON，出图时断言「按类堆叠合计 == counts.assets」
   且「按 resolution 合计 == counts.by_resolution」——图与数字不可能各说各话。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/wp-13946-01/asset_manifest.json` | 资产清单本体（schema=asset_manifest.v1） |
| `artifacts/wp-13946-01/verification.json` | 独立复核逐项结果（8 项检查） |
| `artifacts/wp-13946-01/fig1_asset_coverage.png` | 覆盖率图（数字全部来自清单 JSON） |
| `runs/wp-13946-01/report_13946.md` | 取回的源 markdown（哈希门控通过） |
| `runs/wp-13946-01/kf_result.wp-13946-01.json` | 结果信封（本报告唯一 json 块的原文） |
| `docs/wp-13946-01/asset_manifest.json` | 耐久镜像（artifacts/ 被 .gitignore/push 门丢弃） |
| `schemas/asset_manifest.wp-13946-01.schema.json` | 本包钉住的本地 schema（同名共享 schema 的 const 是别的包） |
| `scripts/kf_fetch_13946.py` | 取源+哈希门控 |
| `scripts/kf_register_13946.py` | 登记器（逐条唯一性断言，不手抄） |
| `scripts/kf_verify_13946.py` | 独立复核器（不 import 登记器） |
| `scripts/kf_figures_13946.py` | 出图（断言与清单自洽） |
| `tests/test_kf_wp13946_01_asset_manifest.py` | pytest 包装：离线+在线双重复核 |

**复现（一键）**：
```
cd <worktree> && python3 scripts/kf_fetch_13946.py && python3 scripts/kf_register_13946.py && python3 scripts/kf_verify_13946.py && python3 scripts/kf_figures_13946.py && python3 -m pytest tests/test_kf_wp13946_01_asset_manifest.py -q
```

## ④ 证据定位表（字段 → 原文引文片段）

引文均为报告 markdown 的**逐字切片**（完整 quote 与 `char_span` 见 `asset_manifest.json`；此处为显示副本，
换行画作 ` / `、超 110 字符处截断并标注 `…（截断）`，不做任何转义/改写）。

- **A01** · `document` · `resolved_in_source` · front-matter (before section 1)
  > # 直剪盒独立复核：伺服载荷偏置是可解析的控制器误差（不是"床面蠕变偏置"） /  / **锚点**：`GAP-DEM-FRICTION`（"摩擦系数 vs 实验 <10%"，仍 in_progress） / **任务* …（截断）
- **A02** · `heading` · `resolved_in_source` · front-matter (before section 1)
  > # 直剪盒独立复核：伺服载荷偏置是可解析的控制器误差（不是"床面蠕变偏置"）
- **A03** · `provenance_header` · `resolved_in_source` · front-matter (before section 1)
  > **锚点**：`GAP-DEM-FRICTION`（"摩擦系数 vs 实验 <10%"，仍 in_progress） / **任务**：m14840（verifier 席自主工时），仓库 TensorDEM，被审对象 ` …（截断）
- **A04** · `table` · `resolved_in_source` · ## 1. 结论先行（三条，全部有数字）
  > | # | 级别 | 结论 | 证据 | / |---|---|---|---| / | **F1** | 缺陷（已修） | 压板伺服在**实验室参考系**上做速度阻尼，离散稳态是 `ΔN = M_p·v_z·(1-e^ …（截断）
- **A05** · `parameter_set` · `resolved_in_source` · ## 2. 案例与装置（与 m14721 同装置，参数逐项对齐）
  > | 项 | 值 | / |---|---| / | 颗粒 | r = 5 mm，ρ = 2500 kg/m³（`ShearCellCase.density`），单分散玻璃珠，**n = 78** | / | 盒体 | 0 …（截断）
- **A06** · `procedure` · `resolved_in_source` · ## 3. 怎么做的
  > 1. **重建执行路径**：`prepare_bed` → `simulate_shear_cell`（symplectic Euler，力在 t）→ 伺服更新 → 积分 → 牵引测量。逐行核对量纲/符号/参考系。 /  …（截断）
- **A07** · `table` · `resolved_in_source` · ## 4. 计算结果
  > | 伺服模式 | σ_n = 2000 Pa | 4000 Pa | 8000 Pa | / |---|---|---|---| / | drag（m14721）相对误差 | **−30.88 %** | −3.56 % …（截断）
- **A08** · `figure_reference` · `referenced_unresolved` · ## 4. 计算结果
  > ![servo audit](../figures/shear_cell_m14840_servo.png)
- **A09** · `figure_caption` · `resolved_in_source` · ## 4. 计算结果
  > **A**：载荷保持误差（红=drag，绿=bedref，灰带 ±3%）。**B**：平均窗内 τ 的四等分均值（归一化）——三条曲线都在单调爬升，γ=1.00 也没到平台。
- **A10** · `table` · `resolved_in_source` · ### 应力保持（伺服对比）
  > | sigma_n 目标 [Pa] | drag sigma_n [Pa] | drag 相对误差 | bedref sigma_n [Pa] | bedref 相对误差 | drag mu | bedref mu |  …（截断）
- **A11** · `table` · `resolved_in_source` · ### 拖曳伺服载荷偏置的机理检验（drag 模式）
  > 稳态解 dN = M_p v_z (1-e^{-dt/tau})/dt /  / | sigma_n [Pa] | v_z [m/s] | dN 实测 [N] | dN 拖曳律预测 [N] | 相对差 | / |---| …（截断）
- **A12** · `table` · `resolved_in_source` · ### 剪切率/惯性数记账（fill_height 名义 vs 实测床高）
  > | sigma_n [Pa] | 床高 [m] | 名义 gamma_dot [1/s] | 实际 gamma_dot [1/s] | I (名义率) | I (实测率, 修正) | tau 四分之一均值 [Pa] |  …（截断）
- **A13** · `error_judgement` · `resolved_in_source` · ## 6. 误差判定（逐项，显式回答"是否 <3%"）
  > | 关键量 | 基准 | 误差 | <3% ? | / |---|---|---|---| / | σ_n 保持（bedref，2000/4000/8000 Pa） | 伺服目标值（可机器判定的精确基准） | −0.59 …（截断）
- **A14** · `repro_command` · `resolved_in_source` · ## 6. 误差判定（逐项，显式回答"是否 <3%"）
  > 复现：`PYTHONPATH=src python -m pytest tests/test_shear_cell_servo_audit_m14840.py -q` → **8 passed（5 s）**； / 证据矩 …（截断）
- **A15** · `limitation_set` · `resolved_in_source` · ## 5. 注意点（坑 / 局限 / 适用范围）
  > 1. **不要用单点 μ 作判据**：78 颗粒、压板接触数 3–10 个，μ 的块标准误 ≈ 0.04（20%），且 τ 仍漂移。要判"μ vs 实验 <10%"，先得让装置进稳态：床层 ≥ 6–8 层、颗粒数 ~10 …（截断）
- **A16** · `code_artifact` · `referenced_unresolved` · front-matter (before section 1)
  > `src/tensordem/shear_cell.py`
- **A17** · `code_artifact` · `referenced_unresolved` · ## 1. 结论先行（三条，全部有数字）
  > scripts/m14840/probe_servo_offset.py
- **A18** · `code_artifact` · `referenced_unresolved` · ## 3. 怎么做的
  > `scripts/m14840/run_matrix.py`
- **A19** · `code_artifact` · `referenced_unresolved` · ## 6. 误差判定（逐项，显式回答"是否 <3%"）
  > 图/表 `scripts/m14840/make_figures.py`
- **A20** · `derived_document` · `referenced_unresolved` · ## 4. 计算结果
  > docs/SHEAR_CELL_SERVO_AUDIT_M14840_tables.md
- **A21** · `result_dataset` · `referenced_unresolved` · ## 3. 怎么做的
  > artifacts/shear_cell_m14840/*.json
- **A22** · `test_artifact` · `referenced_unresolved` · ## 6. 误差判定（逐项，显式回答"是否 <3%"）
  > tests/test_shear_cell_servo_audit_m14840.py
- **A23** · `declared_absent` · `declared_absent` · ## 6. 误差判定（逐项，显式回答"是否 <3%"）
  > **无实验/文献数据集**（仓内无直剪实验数据；F3 未稳态）

源级定位：`tensor://reports/13946#markdown`，`len=5534`，`sha256=eb37b6effecdfc9396ded7a80f236173e234f2785fd984a948efba4a9b671072`。

## ⑤ 注意点与局限

1. **单信道取源**：`psql` 无权限，哈希一致性只能对 API 返回的字节成立；若平台存有第二份 markdown 且与
   API 不同，本单无法发现这层差异（判据仍是契约给的 sha256，已逐字节相等）。
2. **图件只登记链接，不登记字节**：A08 是报告正文的 markdown 图片链接
   `../figures/shear_cell_m14840_servo.png`，本工作树无 `figures/` 目录；平台记录里该图只有
   name+caption（`figures[0]`）而无 png 字节，故 `referenced_unresolved`，不给哈希。
3. **跨仓引用不可解析**：A16–A22（`src/tensordem/shear_cell.py`、`scripts/m14840/*.py`、
   `artifacts/shear_cell_m14840/*.json`、`docs/SHEAR_CELL_..._tables.md`、
   `tests/test_shear_cell_servo_audit_m14840.py`）都是 TensorDEM 侧相对路径，报告未给 commit/URL；
   本单**未**去别的仓解析它们，也未复跑报告声称的「8 passed」。
4. **不判定报告结论**：F1/F2/F3 是源报告的作者结论，本工序只登记其原文位置；**没有任何一条被标 verified**，
   也没有替平台门做 verification。`μ vs 实验` 一项按原文登记为「无数据集 → 不能声称」的 honest-FAIL。
5. **占位符原样保留**：A14 复现命令含 `<tag>/<mode>/<strain>` 占位符，报告未给取值，本单不实例化。
6. **本包 schema 是本地钉住的**：若平台侧 canonical schema 与本仓不同，以平台门为准，本清单需重跑而非手改。

## ⑥ 自检（逐条对照 acceptance，honest）

| acceptance | 结果 | 依据 |
|---|---|---|
| valid_json | ✔ | manifest + envelope 均可 `json.loads` |
| schema_pass | ✔ | 按 `schemas/asset_manifest.wp-13946-01.schema.json` + `schemas/kf_result.v1.schema.json` 校验，0 error |
| source_locator_resolvable | ✔ | 23/23 条 locator 在服务端字节上重新解析通过（span 相等 + 全文唯一 + start_line 相符） |
| source_hash_matches | ✔ | 重算 `eb37b6effecdfc9396ded7a80f236173e234f2785fd984a948efba4a9b671072` == 契约；manifest/envelope 同值 |
| no_duplicate_ids | ✔ | 23 个 asset_id 全互异 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✔ | `claims=[]`（空数组=契约允许的完整结果，未造 claim） |

附加自查（非契约项，跑在本单自家复核器里）：
`no_asset_marked_verified` ✔（无任何资产/claim 被标 verified）、
`scope_single_report` ✔（manifest/envelope 的 report_id 均为 `13946`，未触碰其它报告）。

**诚实说明（未完成/不可判定项，不粉饰）**：
- 图件 png 字节未校验（不可得，见 ⑤.2）；跨仓代码/结果集/测试未解析、未复跑（见 ⑤.3）。
- 本单**不**为「直剪盒伺服偏置已修」或「μ vs 实验 <10%」背书；这两条都是源报告的陈述，
  登记≠验证，verification 由平台门计算。

---

```json
{
  "package_id": "wp-13946-01",
  "task_type": "01-asset-registration",
  "report_id": "13946",
  "provenance": {
    "source_hash": "sha256:eb37b6effecdfc9396ded7a80f236173e234f2785fd984a948efba4a9b671072",
    "source_field": "markdown",
    "producer": "scripts/kf_register_13946.py (agent/m15769)",
    "emitted_at": "deterministic; see report created_at / git commit",
    "notes": "asset registration only; no extraction, no verification claim. source_hash = sha256(markdown bytes of report 13946)."
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-13946-01",
      "task_type": "01-asset-registration",
      "report_id": "13946",
      "source": {
        "uri": "tensor://reports/13946",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "eb37b6effecdfc9396ded7a80f236173e234f2785fd984a948efba4a9b671072",
        "chars": 5534,
        "bytes_utf8": 8712,
        "title": "直剪盒独立复核：压板伺服载荷偏置是控制器误差（drag→bedref），装置仍未稳态",
        "scenario_key": "shear_cell_servo_audit",
        "platform_figures": [
          {
            "name": "shear_cell_m14840_servo.png",
            "caption": "A: sigma_n 保持误差（drag vs bedref，灰带 ±3%）；B: 平均窗内 tau 四等分均值（归一化）"
          }
        ],
        "platform_tags": [
          "DEM",
          "shear_cell",
          "verification",
          "friction",
          "servo",
          "adversarial-review",
          "GAP-DEM-FRICTION"
        ]
      },
      "counts": {
        "assets": 23,
        "by_class": {
          "document": 1,
          "heading": 1,
          "provenance_header": 1,
          "table": 5,
          "parameter_set": 1,
          "procedure": 1,
          "figure_reference": 1,
          "figure_caption": 1,
          "error_judgement": 1,
          "repro_command": 1,
          "limitation_set": 1,
          "code_artifact": 4,
          "derived_document": 1,
          "result_dataset": 1,
          "test_artifact": 1,
          "declared_absent": 1
        },
        "by_resolution": {
          "resolved_in_source": 14,
          "referenced_unresolved": 8,
          "declared_absent": 1
        },
        "resolved_in_source": 14,
        "referenced_unresolved": 8,
        "declared_absent": 1
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "document",
          "label": "报告正文（markdown 全文，源资产本体）",
          "in_report_section": "front-matter (before section 1)",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 5534,
            "start_line": 0,
            "end_line": 100,
            "quote": "# 直剪盒独立复核：伺服载荷偏置是可解析的控制器误差（不是\"床面蠕变偏置\"）\n\n**锚点**：`GAP-DEM-FRICTION`（\"摩擦系数 vs 实验 <10%\"，仍 in_progress）\n**任务**：m14840（verifier 席自主工时），仓库 TensorDEM，被审对象 `src/tensordem/shear_cell.py`（m14721 合并版）\n**方法**：adversarial-review —— 读问题契约 → 独立重建执行路径 → 探高影响失效模式 → 把每条声称绑到原始证据；\n不信任测试\"跑通\"，只认不变量与可复算的数字。\n\n## 1. 结论先行（三条，全部有数字）\n\n| # | 级别 | 结论 | 证据 |\n|---|---|---|---|\n| **F1** | 缺陷（已修） | 压板伺服在**实验室参考系**上做速度阻尼，离散稳态是 `ΔN = M_p·v_z·(1-e^{-dt/τ})/dt`，即**只要压板还在跟随床面蠕变（v_z≠0），载荷必然带一个与 v_z 成正比的偏置**。m14721 把它记为\"床面致密蠕变导致的装置偏置\"，实测 `v_z = 1.49e-3 m/s`、`ΔN_实测 = 0.324 N`、拖曳律预测 `0.298 N`（差 8.2%）⇒ 是**控制器增益/离散化误差**，可解析、可修。 | `scripts/m14840/probe_servo_offset.py` 输出；表 2 |\n| **F2** | 缺陷（已修） | 报告的剪切率/惯性数用**名义 fill_height = 0.05 m**，压实后床高实测 **0.0293–0.0297 m** ⇒ γ̇ 被低估 **1.68×**（名义 1.0 s⁻¹，实际 **1.68 s⁻¹**），I 同比低估。\"准静态区 I ≲ 0.3\"的判定因此建立在错的分母上。 | 表 3；`simulate_shear_cell` 新增 `bed_height_mean / shear_rate_actual / inertial_number` |\n| **F3** | 结论不成立（honest，未修） | **装置不在稳态**：m14721 协议（γ=0.30）下 τ 在平均窗内仍有 `-2.20 … +0.84` 的相对漂移（r² = 0.03–0.31）；把剪切推到 **γ = 1.00** 后漂移仍 +0.33，τ 四分之一段均值 858→1570 Pa 单调升。⇒ 窗平均 τ 不是稳态摩擦，μ 的级间散布（0.20–0.38）主要来自非稳态 + 78 颗统计噪声，**不能宣称\"μ vs 实验 <10%\"**。已为此新增可选稳态门 `stationarity_tol`。 | 表 3、图 B |\n\n## 2. 案例与装置（与 m14721 同装置，参数逐项对齐）\n\n| 项 | 值 |\n|---|---|\n| 颗粒 | r = 5 mm，ρ = 2500 kg/m³（`ShearCellCase.density`），单分散玻璃珠，**n = 78** |\n| 盒体 | 0.080 × 0.032 × 0.050 m，侧壁 μ_wall = 0（无摩擦），底板/压板粗糙 μ = μ_p |\n| 接触 | kn = 1e5 N/m，kt = 0.5kn，e = 0.3，μ_roll = 0.05，dt = 2.5e-5 s |\n| 伺服 | M_plate = 1.0×床质量 = 0.1021 kg，τ_damp = 5e-4 s，v 限幅 0.5 m/s |\n| 协议 | 床面制备（13.7k 步，φ = 0.437，bed_top = 0.0315 m）→ 固结 → 剪切 v = 0.05 m/s，**γ = 0.30**（另有一组 γ = 1.00） |\n| 应力级 | σ_n = 2000 / 4000 / 8000 Pa（三级共用同一床面，seed = 6107） |\n\n## 3. 怎么做的\n\n1. **重建执行路径**：`prepare_bed` → `simulate_shear_cell`（symplectic Euler，力在 t）→ 伺服更新 → 积分 → 牵引测量。逐行核对量纲/符号/参考系。\n2. **把\"偏置\"做成可判伪的预测**：由伺服更新式解析出离散稳态 `ΔN = M_p·v_z·(1-e^{-dt/τ})/dt`；用 `diagnostics=True` 记录的 `vz` 做零参数检验（F1）。\n3. **修正伺服参考系**（`servo_mode=\"bedref\"`）：阻尼改为相对**压板所骑床面颗粒的平均法向速度** `v_bed`（`fn_p>0` 的颗粒），于是稳态蠕变时阻尼不耗散、`ΔN → 0`。`servo_mode=\"drag\"` 保留 m14721 的实验室系律（`ref=0`，逐位一致）作对照。\n4. **修正速率记账**：从稳态窗内的床面高度均值给 `bed_height_mean`，据此报 `shear_rate_actual` 与 `inertial_number`。\n5. **加稳态门**：`stationarity_tol` 打开时，`|drift| > tol` 的运行被有效性门拒绝（不给出 μ），把\"窗平均冒充稳态值\"堵死。\n6. **A/B 证据矩阵**：`scripts/m14840/run_matrix.py` 三级应力 × 两种伺服模式 + γ=1.00 长剪切，结果落 `artifacts/shear_cell_m14840/*.json`；图表与全部表格由 `scripts/m14840/make_figures.py` **程序化注入**（零手抄）。\n\n## 4. 计算结果\n\n表 1/2/3 见 `docs/SHEAR_CELL_SERVO_AUDIT_M14840_tables.md`（脚本生成）。要点：\n\n| 伺服模式 | σ_n = 2000 Pa | 4000 Pa | 8000 Pa |\n|---|---|---|---|\n| drag（m14721）相对误差 | **−30.88 %** | −3.56 % | −5.44 % |\n| bedref（m14840）相对误差 | **−0.59 %** | −0.21 % | −0.12 % |\n\n- 三级应力下 bedref 的载荷误差均 **< 1%**（drag 最好一级也有 3.56%，最差 30.9%）。\n- drag 模式的偏置**随窗而变、甚至变号**（γ=0.40 时为 +3.17%，γ=0.30 时为 −3.56%）——正因为它不是装置偏置而是\"跟随蠕变的瞬时载荷差 + 非稳态窗\"的合成，这与 F1 的机理一致，也与 m14721 doc §4.3 的\"系统性正偏 3~5%\"表述冲突。\n\n![servo audit](../figures/shear_cell_m14840_servo.png)\n\n**A**：载荷保持误差（红=drag，绿=bedref，灰带 ±3%）。**B**：平均窗内 τ 的四等分均值（归一化）——三条曲线都在单调爬升，γ=1.00 也没到平台。\n\n## 5. 注意点（坑 / 局限 / 适用范围）\n\n1. **不要用单点 μ 作判据**：78 颗粒、压板接触数 3–10 个，μ 的块标准误 ≈ 0.04（20%），且 τ 仍漂移。要判\"μ vs 实验 <10%\"，先得让装置进稳态：床层 ≥ 6–8 层、颗粒数 ~10³、仍用应力伺服 + `stationarity_tol` 门。\n2. **A/B 的协议口径**：本单矩阵用 `consol_time = 0.03 s`（案例默认），m14721 正文用 0.04 s；两种模式的差别是同一口径下的差分，故 F1 结论不受影响，但**绝对数值不可与 m14721 表逐格对比**。\n3. **artifacts 里的 I 列**按名义 γ̇ 记账（这正是被审计的旧约定，测试用 `rel=2e-2` 锁定该事实）；修正值 I_actual = I_nominal × 1.68 见表 3 最后一列。\n4. **`inertial_number` 的量级**：γ̇=1.68 s⁻¹、σ_n≈2–8 kPa 时 I ≈ 0.006–0.019，比 m14721 正文标注的 0.14–0.28 小两个量级——该标注按 `γ̇·2r/√(σ/ρ)` 与本文参数**不可复算**，属报告级错误（不影响代码），建议后续单按本文公式重出该行。\n5. 适用范围：I ≲ 0.3 准静态、单分散球、无黏结；`bedref` 伺服只解决**载荷保持**，不解决**稳态性**（F3 仍在）。\n\n## 6. 误差判定（逐项，显式回答\"是否 <3%\"）\n\n| 关键量 | 基准 | 误差 | <3% ? |\n|---|---|---|---|\n| σ_n 保持（bedref，2000/4000/8000 Pa） | 伺服目标值（可机器判定的精确基准） | −0.59 / −0.21 / −0.12 % | **是** |\n| σ_n 保持（drag，同上） | 同上 | −30.88 / −3.56 / −5.44 % | 否 |\n| drag 载荷偏置 vs 拖曳律预测（机理检验） | `M_p v_z (1-e^{-dt/τ})/dt`（解析） | 8.2 %（1 级）/ 表 2 全级 | 否，但足以判定机理 |\n| γ̇ 记账 | v / 实测床高 | 修正前低估 68 % | **否（修正前）**，修正后为定义式恒等 |\n| μ vs 实验 | **无实验/文献数据集**（仓内无直剪实验数据；F3 未稳态） | 不可判定 | **不能声称**（honest FAIL） |\n\n复现：`PYTHONPATH=src python -m pytest tests/test_shear_cell_servo_audit_m14840.py -q` → **8 passed（5 s）**；\n证据矩阵 `PYTHONPATH=src python scripts/m14840/run_matrix.py <tag> <mode> <strain>`；图/表 `scripts/m14840/make_figures.py`。\n\n---\n\n### 应力保持（伺服对比）\n\n| sigma_n 目标 [Pa] | drag sigma_n [Pa] | drag 相对误差 | bedref sigma_n [Pa] | bedref 相对误差 | drag mu | bedref mu |\n|---|---|---|---|---|---|---|\n| 2000 | 1382.37 | -30.88% | 1988.27 | -0.59% | 0.2734 | 0.3231 |\n| 4000 | 3857.70 | -3.56% | 3991.56 | -0.21% | 0.3121 | 0.1964 |\n| 8000 | 7564.73 | -5.44% | 7990.49 | -0.12% | 0.3768 | 0.3274 |\n\n### 拖曳伺服载荷偏置的机理检验（drag 模式）\n\n稳态解 dN = M_p v_z (1-e^{-dt/tau})/dt\n\n| sigma_n [Pa] | v_z [m/s] | dN 实测 [N] | dN 拖曳律预测 [N] | 相对差 |\n|---|---|---|---|---|\n| 2000 | -7.592e-03 | -1.5811 | -1.5115 | -4.4% |\n| 4000 | -1.557e-03 | -0.3643 | -0.3100 | -14.9% |\n| 8000 | -5.253e-03 | -1.1143 | -1.0459 | -6.1% |\n\n### 剪切率/惯性数记账（fill_height 名义 vs 实测床高）\n\n| sigma_n [Pa] | 床高 [m] | 名义 gamma_dot [1/s] | 实际 gamma_dot [1/s] | I (名义率) | I (实测率, 修正) | tau 四分之一均值 [Pa] | 窗口相对漂移 |\n|---|---|---|---|---|---|---|---|\n| 2000 | 0.0297 | 1.00 | 1.68 | 0.0112 | 0.0189 | 414, 505, 527, 758 | +0.67 |\n| 4000 | 0.0298 | 1.00 | 1.68 | 0.0079 | 0.0133 | 978, 795, 896, 673 | -0.35 |\n| 8000 | 0.0299 | 1.00 | 1.67 | 0.0056 | 0.0094 | 2008, 2031, 2377, 2859 | +0.38 |\n| 4000 (gamma=1.0) | 0.0296 | 1.00 | 1.69 | 0.0079 | 0.0134 | 858, 1084, 1282, 1569 | +0.33 |\n",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim slice of report markdown at char_span, unique in document",
            "result": "resolved"
          },
          "note": "整篇 markdown 即源资产；sha256/字符数见 source 字段，可由 scripts/kf_fetch_13946.py 复算"
        },
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "报告标题（与 API title 字段同源）",
          "in_report_section": "front-matter (before section 1)",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 38,
            "start_line": 0,
            "end_line": 0,
            "quote": "# 直剪盒独立复核：伺服载荷偏置是可解析的控制器误差（不是\"床面蠕变偏置\"）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim slice of report markdown at char_span, unique in document",
            "result": "resolved"
          },
          "note": "一级标题单行；内容与平台 title 字段一致（见 ④ 证据定位表）"
        },
        {
          "asset_id": "A03",
          "asset_class": "provenance_header",
          "label": "锚点/任务/方法三行溯源声明",
          "in_report_section": "front-matter (before section 1)",
          "locator": {
            "method": "char_span",
            "start_char": 40,
            "end_char": 284,
            "start_line": 2,
            "end_line": 5,
            "quote": "**锚点**：`GAP-DEM-FRICTION`（\"摩擦系数 vs 实验 <10%\"，仍 in_progress）\n**任务**：m14840（verifier 席自主工时），仓库 TensorDEM，被审对象 `src/tensordem/shear_cell.py`（m14721 合并版）\n**方法**：adversarial-review —— 读问题契约 → 独立重建执行路径 → 探高影响失效模式 → 把每条声称绑到原始证据；\n不信任测试\"跑通\"，只认不变量与可复算的数字。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim slice of report markdown at char_span, unique in document",
            "result": "resolved"
          },
          "note": "声明 GAP-DEM-FRICTION 锚点、m14840 任务号、被审对象仓库与文件、方法=adversarial-review"
        },
        {
          "asset_id": "A04",
          "asset_class": "table",
          "label": "结论表 F1/F2/F3（表头+分隔+3 条结论）",
          "in_report_section": "## 1. 结论先行（三条，全部有数字）",
          "locator": {
            "method": "char_span",
            "start_char": 308,
            "end_char": 1180,
            "start_line": 9,
            "end_line": 13,
            "quote": "| # | 级别 | 结论 | 证据 |\n|---|---|---|---|\n| **F1** | 缺陷（已修） | 压板伺服在**实验室参考系**上做速度阻尼，离散稳态是 `ΔN = M_p·v_z·(1-e^{-dt/τ})/dt`，即**只要压板还在跟随床面蠕变（v_z≠0），载荷必然带一个与 v_z 成正比的偏置**。m14721 把它记为\"床面致密蠕变导致的装置偏置\"，实测 `v_z = 1.49e-3 m/s`、`ΔN_实测 = 0.324 N`、拖曳律预测 `0.298 N`（差 8.2%）⇒ 是**控制器增益/离散化误差**，可解析、可修。 | `scripts/m14840/probe_servo_offset.py` 输出；表 2 |\n| **F2** | 缺陷（已修） | 报告的剪切率/惯性数用**名义 fill_height = 0.05 m**，压实后床高实测 **0.0293–0.0297 m** ⇒ γ̇ 被低估 **1.68×**（名义 1.0 s⁻¹，实际 **1.68 s⁻¹**），I 同比低估。\"准静态区 I ≲ 0.3\"的判定因此建立在错的分母上。 | 表 3；`simulate_shear_cell` 新增 `bed_height_mean / shear_rate_actual / inertial_number` |\n| **F3** | 结论不成立（honest，未修） | **装置不在稳态**：m14721 协议（γ=0.30）下 τ 在平均窗内仍有 `-2.20 … +0.84` 的相对漂移（r² = 0.03–0.31）；把剪切推到 **γ = 1.00** 后漂移仍 +0.33，τ 四分之一段均值 858→1570 Pa 单调升。⇒ 窗平均 τ 不是稳态摩擦，μ 的级间散布（0.20–0.38）主要来自非稳态 + 78 颗统计噪声，**不能宣称\"μ vs 实验 <10%\"**。已为此新增可选稳态门 `stationarity_tol`。 | 表 3、图 B |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim slice of report markdown at char_span, unique in document",
            "result": "resolved"
          },
          "note": "3 条结论级登记：F1/F2 缺陷已修、F3 结论不成立(honest 未修)；仅登记不改写、不判 verified"
        },
        {
          "asset_id": "A05",
          "asset_class": "parameter_set",
          "label": "装置与案例参数表（颗粒/盒体/接触/伺服/协议/应力级，6 行）",
          "in_report_section": "## 2. 案例与装置（与 m14721 同装置，参数逐项对齐）",
          "locator": {
            "method": "char_span",
            "start_char": 1216,
            "end_char": 1678,
            "start_line": 17,
            "end_line": 24,
            "quote": "| 项 | 值 |\n|---|---|\n| 颗粒 | r = 5 mm，ρ = 2500 kg/m³（`ShearCellCase.density`），单分散玻璃珠，**n = 78** |\n| 盒体 | 0.080 × 0.032 × 0.050 m，侧壁 μ_wall = 0（无摩擦），底板/压板粗糙 μ = μ_p |\n| 接触 | kn = 1e5 N/m，kt = 0.5kn，e = 0.3，μ_roll = 0.05，dt = 2.5e-5 s |\n| 伺服 | M_plate = 1.0×床质量 = 0.1021 kg，τ_damp = 5e-4 s，v 限幅 0.5 m/s |\n| 协议 | 床面制备（13.7k 步，φ = 0.437，bed_top = 0.0315 m）→ 固结 → 剪切 v = 0.05 m/s，**γ = 0.30**（另有一组 γ = 1.00） |\n| 应力级 | σ_n = 2000 / 4000 / 8000 Pa（三级共用同一床面，seed = 6107） |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim slice of report markdown at char_span, unique in document",
            "result": "resolved"
          },
          "note": "参数原文逐字登记（r/ρ/n/盒体尺寸/kn/kt/e/dt/M_plate/τ_damp/γ/σ_n/seed），不做换算与补全"
        },
        {
          "asset_id": "A06",
          "asset_class": "procedure",
          "label": "方法步骤清单（6 步：路径重建→解析预测→bedref 修正→速率记账→稳态门→A/B 矩阵）",
          "in_report_section": "## 3. 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1692,
            "end_char": 2419,
            "start_line": 28,
            "end_line": 33,
            "quote": "1. **重建执行路径**：`prepare_bed` → `simulate_shear_cell`（symplectic Euler，力在 t）→ 伺服更新 → 积分 → 牵引测量。逐行核对量纲/符号/参考系。\n2. **把\"偏置\"做成可判伪的预测**：由伺服更新式解析出离散稳态 `ΔN = M_p·v_z·(1-e^{-dt/τ})/dt`；用 `diagnostics=True` 记录的 `vz` 做零参数检验（F1）。\n3. **修正伺服参考系**（`servo_mode=\"bedref\"`）：阻尼改为相对**压板所骑床面颗粒的平均法向速度** `v_bed`（`fn_p>0` 的颗粒），于是稳态蠕变时阻尼不耗散、`ΔN → 0`。`servo_mode=\"drag\"` 保留 m14721 的实验室系律（`ref=0`，逐位一致）作对照。\n4. **修正速率记账**：从稳态窗内的床面高度均值给 `bed_height_mean`，据此报 `shear_rate_actual` 与 `inertial_number`。\n5. **加稳态门**：`stationarity_tol` 打开时，`|drift| > tol` 的运行被有效性门拒绝（不给出 μ），把\"窗平均冒充稳态值\"堵死。\n6. **A/B 证据矩阵**：`scripts/m14840/run_matrix.py` 三级应力 × 两种伺服模式 + γ=1.00 长剪切，结果落 `artifacts/shear_cell_m14840/*.json`；图表与全部表格由 `scripts/m14840/make_figures.py` **程序化注入**（零手抄）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim slice of report markdown at char_span, unique in document",
            "result": "resolved"
          },
          "note": "6 条方法步骤原文；步骤内引用的脚本路径分别登记为 A17-A19"
        },
        {
          "asset_id": "A07",
          "asset_class": "table",
          "label": "伺服模式相对误差对照表（drag vs bedref × 三级 σ_n）",
          "in_report_section": "## 4. 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 2501,
            "end_char": 2676,
            "start_line": 39,
            "end_line": 42,
            "quote": "| 伺服模式 | σ_n = 2000 Pa | 4000 Pa | 8000 Pa |\n|---|---|---|---|\n| drag（m14721）相对误差 | **−30.88 %** | −3.56 % | −5.44 % |\n| bedref（m14840）相对误差 | **−0.59 %** | −0.21 % | −0.12 % |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim slice of report markdown at char_span, unique in document",
            "result": "resolved"
          },
          "note": "表头+两行数据；数值仅登记，误差判定见 A13"
        },
        {
          "asset_id": "A08",
          "asset_class": "figure_reference",
          "label": "图 1 内联引用（servo audit png 相对路径）",
          "in_report_section": "## 4. 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 2886,
            "end_char": 2940,
            "start_line": 47,
            "end_line": 47,
            "quote": "![servo audit](../figures/shear_cell_m14840_servo.png)",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "referenced by relative path/env in report; not present in this worktree and no commit/URL/DOI given in the report",
            "result": "unresolved"
          },
          "note": "markdown 图片链接指向 ../figures/shear_cell_m14840_servo.png；本工作树无 figures/ 目录，二进制不可解析；平台 reports.figures 元数据声明同名图（见 source.platform_figures），但本工序只登记链接，不校验图件内容"
        },
        {
          "asset_id": "A09",
          "asset_class": "figure_caption",
          "label": "图 1 说明（A 面板载荷误差 / B 面板 τ 四等分均值）",
          "in_report_section": "## 4. 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 2942,
            "end_char": 3029,
            "start_line": 49,
            "end_line": 49,
            "quote": "**A**：载荷保持误差（红=drag，绿=bedref，灰带 ±3%）。**B**：平均窗内 τ 的四等分均值（归一化）——三条曲线都在单调爬升，γ=1.00 也没到平台。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim slice of report markdown at char_span, unique in document",
            "result": "resolved"
          },
          "note": "图注原文；与平台 figures[0].caption 语义一致"
        },
        {
          "asset_id": "A10",
          "asset_class": "table",
          "label": "表 1：应力保持逐级明细（drag/bedref σ_n 与 μ）",
          "in_report_section": "### 应力保持（伺服对比）",
          "locator": {
            "method": "char_span",
            "start_char": 4369,
            "end_char": 4704,
            "start_line": 76,
            "end_line": 80,
            "quote": "| sigma_n 目标 [Pa] | drag sigma_n [Pa] | drag 相对误差 | bedref sigma_n [Pa] | bedref 相对误差 | drag mu | bedref mu |\n|---|---|---|---|---|---|---|\n| 2000 | 1382.37 | -30.88% | 1988.27 | -0.59% | 0.2734 | 0.3231 |\n| 4000 | 3857.70 | -3.56% | 3991.56 | -0.21% | 0.3121 | 0.1964 |\n| 8000 | 7564.73 | -5.44% | 7990.49 | -0.12% | 0.3768 | 0.3274 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim slice of report markdown at char_span, unique in document",
            "result": "resolved"
          },
          "note": "表头+3 行数据；含 drag/bedref 两侧 μ 值（本工序未对 μ 做任何结论）"
        },
        {
          "asset_id": "A11",
          "asset_class": "table",
          "label": "表 2：拖曳伺服载荷偏置机理检验（v_z / ΔN 实测 / ΔN 解析预测）",
          "in_report_section": "### 拖曳伺服载荷偏置的机理检验（drag 模式）",
          "locator": {
            "method": "char_span",
            "start_char": 4734,
            "end_char": 5005,
            "start_line": 84,
            "end_line": 90,
            "quote": "稳态解 dN = M_p v_z (1-e^{-dt/tau})/dt\n\n| sigma_n [Pa] | v_z [m/s] | dN 实测 [N] | dN 拖曳律预测 [N] | 相对差 |\n|---|---|---|---|---|\n| 2000 | -7.592e-03 | -1.5811 | -1.5115 | -4.4% |\n| 4000 | -1.557e-03 | -0.3643 | -0.3100 | -14.9% |\n| 8000 | -5.253e-03 | -1.1143 | -1.0459 | -6.1% |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim slice of report markdown at char_span, unique in document",
            "result": "resolved"
          },
          "note": "含 F1 解析式原文行（稳态解 dN = M_p v_z (1-e^{-dt/tau})/dt）+ 表头 + 3 行数据"
        },
        {
          "asset_id": "A12",
          "asset_class": "table",
          "label": "表 3：剪切率/惯性数记账（名义 vs 实测床高、τ 四等分均值、窗口漂移）",
          "in_report_section": "### 剪切率/惯性数记账（fill_height 名义 vs 实测床高）",
          "locator": {
            "method": "char_span",
            "start_char": 5046,
            "end_char": 5533,
            "start_line": 94,
            "end_line": 99,
            "quote": "| sigma_n [Pa] | 床高 [m] | 名义 gamma_dot [1/s] | 实际 gamma_dot [1/s] | I (名义率) | I (实测率, 修正) | tau 四分之一均值 [Pa] | 窗口相对漂移 |\n|---|---|---|---|---|---|---|---|\n| 2000 | 0.0297 | 1.00 | 1.68 | 0.0112 | 0.0189 | 414, 505, 527, 758 | +0.67 |\n| 4000 | 0.0298 | 1.00 | 1.68 | 0.0079 | 0.0133 | 978, 795, 896, 673 | -0.35 |\n| 8000 | 0.0299 | 1.00 | 1.67 | 0.0056 | 0.0094 | 2008, 2031, 2377, 2859 | +0.38 |\n| 4000 (gamma=1.0) | 0.0296 | 1.00 | 1.69 | 0.0079 | 0.0134 | 858, 1084, 1282, 1569 | +0.33 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim slice of report markdown at char_span, unique in document",
            "result": "resolved"
          },
          "note": "含 F2/F3 的关键数字（床高 0.0296-0.0299 m、实际 γ̇ 1.67-1.69 1/s、I_actual、drift）；仅登记"
        },
        {
          "asset_id": "A13",
          "asset_class": "error_judgement",
          "label": "§6 误差判定表（含『不能声称』honest-FAIL 行）",
          "in_report_section": "## 6. 误差判定（逐项，显式回答\"是否 <3%\"）",
          "locator": {
            "method": "char_span",
            "start_char": 3703,
            "end_char": 4122,
            "start_line": 61,
            "end_line": 67,
            "quote": "| 关键量 | 基准 | 误差 | <3% ? |\n|---|---|---|---|\n| σ_n 保持（bedref，2000/4000/8000 Pa） | 伺服目标值（可机器判定的精确基准） | −0.59 / −0.21 / −0.12 % | **是** |\n| σ_n 保持（drag，同上） | 同上 | −30.88 / −3.56 / −5.44 % | 否 |\n| drag 载荷偏置 vs 拖曳律预测（机理检验） | `M_p v_z (1-e^{-dt/τ})/dt`（解析） | 8.2 %（1 级）/ 表 2 全级 | 否，但足以判定机理 |\n| γ̇ 记账 | v / 实测床高 | 修正前低估 68 % | **否（修正前）**，修正后为定义式恒等 |\n| μ vs 实验 | **无实验/文献数据集**（仓内无直剪实验数据；F3 未稳态） | 不可判定 | **不能声称**（honest FAIL） |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim slice of report markdown at char_span, unique in document",
            "result": "resolved"
          },
          "note": "5 行判定：逐项显式回答是否 <3%；末行 μ vs 实验=不可判定/不能声称"
        },
        {
          "asset_id": "A14",
          "asset_class": "repro_command",
          "label": "复现命令行（pytest 8 passed / run_matrix / make_figures）",
          "in_report_section": "## 6. 误差判定（逐项，显式回答\"是否 <3%\"）",
          "locator": {
            "method": "char_span",
            "start_char": 4124,
            "end_char": 4346,
            "start_line": 69,
            "end_line": 70,
            "quote": "复现：`PYTHONPATH=src python -m pytest tests/test_shear_cell_servo_audit_m14840.py -q` → **8 passed（5 s）**；\n证据矩阵 `PYTHONPATH=src python scripts/m14840/run_matrix.py <tag> <mode> <strain>`；图/表 `scripts/m14840/make_figures.py`。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim slice of report markdown at char_span, unique in document",
            "result": "resolved"
          },
          "note": "两条原文命令；标签 <tag>/<mode>/<strain> 为占位符，报告未给出具体取值——登记时不实例化"
        },
        {
          "asset_id": "A15",
          "asset_class": "limitation_set",
          "label": "注意点与局限（5 条：判据/协议口径/旧记账/量级/适用范围）",
          "in_report_section": "## 5. 注意点（坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 3057,
            "end_char": 3672,
            "start_line": 53,
            "end_line": 57,
            "quote": "1. **不要用单点 μ 作判据**：78 颗粒、压板接触数 3–10 个，μ 的块标准误 ≈ 0.04（20%），且 τ 仍漂移。要判\"μ vs 实验 <10%\"，先得让装置进稳态：床层 ≥ 6–8 层、颗粒数 ~10³、仍用应力伺服 + `stationarity_tol` 门。\n2. **A/B 的协议口径**：本单矩阵用 `consol_time = 0.03 s`（案例默认），m14721 正文用 0.04 s；两种模式的差别是同一口径下的差分，故 F1 结论不受影响，但**绝对数值不可与 m14721 表逐格对比**。\n3. **artifacts 里的 I 列**按名义 γ̇ 记账（这正是被审计的旧约定，测试用 `rel=2e-2` 锁定该事实）；修正值 I_actual = I_nominal × 1.68 见表 3 最后一列。\n4. **`inertial_number` 的量级**：γ̇=1.68 s⁻¹、σ_n≈2–8 kPa 时 I ≈ 0.006–0.019，比 m14721 正文标注的 0.14–0.28 小两个量级——该标注按 `γ̇·2r/√(σ/ρ)` 与本文参数**不可复算**，属报告级错误（不影响代码），建议后续单按本文公式重出该行。\n5. 适用范围：I ≲ 0.3 准静态、单分散球、无黏结；`bedref` 伺服只解决**载荷保持**，不解决**稳态性**（F3 仍在）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim slice of report markdown at char_span, unique in document",
            "result": "resolved"
          },
          "note": "5 条局限原文，preserve_uncertainty：原文措辞原样保留，不弱化也不强化"
        },
        {
          "asset_id": "A16",
          "asset_class": "code_artifact",
          "label": "被审代码 src/tensordem/shear_cell.py（m14721 合并版）",
          "in_report_section": "front-matter (before section 1)",
          "locator": {
            "method": "char_span",
            "start_char": 147,
            "end_char": 176,
            "start_line": 3,
            "end_line": 3,
            "quote": "`src/tensordem/shear_cell.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "referenced by relative path/env in report; not present in this worktree and no commit/URL/DOI given in the report",
            "result": "unresolved"
          },
          "note": "TensorDEM 仓内路径，本工作树（TensorKnowledge）无该文件，无 commit SHA/URL，故不可解析"
        },
        {
          "asset_id": "A17",
          "asset_class": "code_artifact",
          "label": "诊断脚本 scripts/m14840/probe_servo_offset.py",
          "in_report_section": "## 1. 结论先行（三条，全部有数字）",
          "locator": {
            "method": "char_span",
            "start_char": 593,
            "end_char": 629,
            "start_line": 11,
            "end_line": 11,
            "quote": "scripts/m14840/probe_servo_offset.py",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "referenced by relative path/env in report; not present in this worktree and no commit/URL/DOI given in the report",
            "result": "unresolved"
          },
          "note": "F1 证据来源脚本；跨仓相对路径，无 commit/URL，本工作树不可解析"
        },
        {
          "asset_id": "A18",
          "asset_class": "code_artifact",
          "label": "证据矩阵脚本 scripts/m14840/run_matrix.py",
          "in_report_section": "## 3. 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 2263,
            "end_char": 2293,
            "start_line": 33,
            "end_line": 33,
            "quote": "`scripts/m14840/run_matrix.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "referenced by relative path/env in report; not present in this worktree and no commit/URL/DOI given in the report",
            "result": "unresolved"
          },
          "note": "A/B 矩阵生成器；跨仓相对路径，不可解析"
        },
        {
          "asset_id": "A19",
          "asset_class": "code_artifact",
          "label": "图表生成脚本 scripts/m14840/make_figures.py",
          "in_report_section": "## 6. 误差判定（逐项，显式回答\"是否 <3%\"）",
          "locator": {
            "method": "char_span",
            "start_char": 4309,
            "end_char": 4345,
            "start_line": 70,
            "end_line": 70,
            "quote": "图/表 `scripts/m14840/make_figures.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "referenced by relative path/env in report; not present in this worktree and no commit/URL/DOI given in the report",
            "result": "unresolved"
          },
          "note": "声明图表程序化注入（零手抄）；与 A18 同行引用，跨仓不可解析"
        },
        {
          "asset_id": "A20",
          "asset_class": "derived_document",
          "label": "表 1/2/3 的脚本文档 docs/SHEAR_CELL_SERVO_AUDIT_M14840_tables.md",
          "in_report_section": "## 4. 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 2444,
            "end_char": 2488,
            "start_line": 37,
            "end_line": 37,
            "quote": "docs/SHEAR_CELL_SERVO_AUDIT_M14840_tables.md",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "referenced by relative path/env in report; not present in this worktree and no commit/URL/DOI given in the report",
            "result": "unresolved"
          },
          "note": "报告称『表 1/2/3 见』该文件；跨仓路径，本工作树不存在，不可解析"
        },
        {
          "asset_id": "A21",
          "asset_class": "result_dataset",
          "label": "证据矩阵结果集 artifacts/shear_cell_m14840/*.json",
          "in_report_section": "## 3. 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 2326,
            "end_char": 2360,
            "start_line": 33,
            "end_line": 33,
            "quote": "artifacts/shear_cell_m14840/*.json",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "referenced by relative path/env in report; not present in this worktree and no commit/URL/DOI given in the report",
            "result": "unresolved"
          },
          "note": "通配路径，未列出具体文件名/哈希；跨仓，不可解析（不臆造文件名）"
        },
        {
          "asset_id": "A22",
          "asset_class": "test_artifact",
          "label": "审计测试 tests/test_shear_cell_servo_audit_m14840.py（报告称 8 passed）",
          "in_report_section": "## 6. 误差判定（逐项，显式回答\"是否 <3%\"）",
          "locator": {
            "method": "char_span",
            "start_char": 4160,
            "end_char": 4203,
            "start_line": 69,
            "end_line": 69,
            "quote": "tests/test_shear_cell_servo_audit_m14840.py",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "referenced by relative path/env in report; not present in this worktree and no commit/URL/DOI given in the report",
            "result": "unresolved"
          },
          "note": "跨仓测试文件；报告只给『8 passed（5 s）』这一观察，本工序未复跑（无该仓检出），不作独立性判定"
        },
        {
          "asset_id": "A23",
          "asset_class": "declared_absent",
          "label": "μ vs 实验所需的实验/文献数据集",
          "in_report_section": "## 6. 误差判定（逐项，显式回答\"是否 <3%\"）",
          "locator": {
            "method": "char_span",
            "start_char": 4058,
            "end_char": 4089,
            "start_line": 67,
            "end_line": 67,
            "quote": "**无实验/文献数据集**（仓内无直剪实验数据；F3 未稳态）",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "report explicitly states the item is absent/unavailable",
            "result": "absent"
          },
          "note": "报告显式声明『无实验/文献数据集（仓内无直剪实验数据；F3 未稳态）』——按声明登记为缺失，不补造"
        }
      ],
      "claims": [],
      "claims_note": "claims 有意为空：本工序 objective.register_assets=true / classify_report_type=false，只登记资产不做抽取（契约允许空数组，禁为填指标造知识）；报告内的 F1-F3 结论原样留在 A04 等资产里，未升级为 claim。",
      "integrity": {
        "quote_uniqueness": "each quote asserted md.count(quote)==1 at build time",
        "hash_recomputed_locally": "eb37b6effecdfc9396ded7a80f236173e234f2785fd984a948efba4a9b671072",
        "hash_matches_contract": true,
        "char_count_matches_contract": true,
        "char_span_recheck": "md[start_char:end_char] == quote for every asset (asserted)",
        "verified_by_platform_gate": false
      }
    }
  },
  "claims": []
}
```
