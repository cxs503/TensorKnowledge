# KF-RESULT wp-10429-01

> 工序：`01-asset-registration`（lane C，contract_version 1.0）｜report_id **10429**｜
> source_uri `tensor://reports/10429`｜source_field `markdown`｜scenario_key `fsi_lbm_strong_coupling`
> 本报告由 `scripts/kf_wp10429_01_render_report.py` 从工件直接渲染，正文数字/引文零手抄。

## ① 本工序做了什么

对 report 10429（《P153W2-N03 TensorFEM x TensorLBM strong-coupling FSI: Turek-Hron 2D-2 anchor + FSI-2 honest-FAIL + energy ledger》）做**资产登记**：确认 report_id 与其 markdown 的字节哈希一致，
把报告里可解析的资产（正文/表/代码指针/图件声明/文献集等）逐条登记成带**字符级定位器**的清单，
不做知识抽取（契约 `objective.classify_report_type=false`、notes 明确「不做抽取，claims 允许为空数组」），
不对任何结论标 verified（verification 由平台门计算）。

结果概览：登记 **22 个资产**（resolved_in_source 19 / referenced_unresolved 3 /
declared_absent 0）；markdown sha256 与契约 `source_hash` **逐位相等**；21 个 char_span 引文
全部在源文逐字命中且全篇唯一。上游报告的实质结论（Turek-Hron 2D-2 锚定 CD −11.2% / CL −19.2% / St −11.3%、
FSI-2 为 honest-FAIL、旧 fsi_turek_hron 与 fsi_flutter 被证伪）**只登记、不复核、不改判**。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`GET http://127.0.0.1:8010/api/v1/tensor/reports/10429`（Bearer 由 env 登录 `/auth/login` 取得，凭据不落盘），
   保存 `runs/wp-10429-01/report_10429.json`（原始 record）与 `report_10429.md`（markdown 本体）。
2. **对哈希**：本地重算 `sha256(markdown)` = `6e48f09bc41ac354d46463f6f91ef5b6d34a1ffa7748dcf6a3083c4f6944be1d`，与契约
   `sha256:6e48f09bc41ac354d46463f6f91ef5b6d34a1ffa7748dcf6a3083c4f6944be1d` 相等；chars 7442 与契约 7442 相等；title 与契约 title 相等。
   三者任一不等，登记脚本直接 `exit 2`（不产出半成品）。
3. **定位器生成（零手抄的关键）**：资产表里只写「锚样子串 + 行偏移」，脚本 `find_line()` 断言该锚在源文
   **恰好命中 1 行**，再由 `line_offsets()` 把行号换算成字符偏移，`quote` 由 `md[offs[s]:offs[e]+len(...)]`
   **切出**而非键入；并断言 `md.count(quote)==1`。锚或唯一性不成立即硬失败（本轮修掉了 5 处越界/重叠 span，
   见 §⑤）。
4. **解析性判定（不臆造地址）**：每个资产给 `resolution` 三态 + 机器可复算的 `resolution_check`：
   - `resolved_in_source` → 切片命中（或整篇 document 的 sha256 命中）；
   - `referenced_unresolved` → 对外部仓文件路径/符号做**工作树存在性查找**，未命中即 unresolved，且报告未给
     URL/DOI/commit，**不猜地址**；
   - 图件声明另做「平台 record.figures 名称比对」（declared 4 / matched 4）。
5. **独立复核**：`scripts/kf_wp10429_01_verify.py` **重新从 API 取全文**（不复用本地副本），
   逐条重解析定位器、用 jsonschema 校验 manifest（包内固定 schema）与信封（仓库 `schemas/kf_result.v1.schema.json`）、
   查重 ID、查 claim 证据位。验收项 6/6 通过 + 1 项附加。
6. **反证（阴性对照）**：`scripts/kf_wp10429_01_selftest.py` 在临时目录副本上逐项注入缺陷，断言**指定**验收项翻红——
   绿门不等于有效门，见 §⑥ 表。

`repro_cmd`（工作树根执行，需 env `TENSOR_API_BASE/TENSOR_AGENT_USER/TENSOR_AGENT_PASS`）：

```bash
python3 scripts/kf_wp10429_01_register.py && python3 scripts/kf_wp10429_01_verify.py   && python3 scripts/kf_wp10429_01_selftest.py && python3 scripts/kf_wp10429_01_render_report.py
```

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `artifacts/wp-10429-01/asset_manifest.json` | 契约输出；22 资产 + 定位器 + resolution_check + integrity；sha256 `845c6129a7a9259e96e7127df80d329254972491e9f355e1aacf02c523aa50bb`，28503 B |
| `docs/kf/wp-10429-01/asset_manifest.json` | 上者**逐字节**持久镜像（push gate 会丢 artifacts/、runs/） |
| `runs/wp-10429-01/kf_result.wp-10429-01.json` | kf_result.v1 信封（本报告唯一 json 块的来源） |
| `runs/wp-10429-01/verification.json` | 独立复核对账：7 项检查逐项 pass/fail 与证据字段 |
| `runs/wp-10429-01/selftest.json` | 阴性对照：7 例（基线 + 6 注入缺陷）逐例裁决 |
| `runs/wp-10429-01/report_10429.md` | 源 markdown 本地副本（7442 chars / 7448 B UTF-8） |
| `schemas/asset_manifest.v1.wp-10429-01.schema.json` | 包内固定 manifest schema（仅 const 换成本包 ID，字段集与 448 版全同） |
| `scripts/kf_wp10429_01_{register,verify,selftest,render_report,publish}.py` | 产线五件套，可一键复跑 |

## ④ 证据定位表（字段 → 原文引文片段，逐字切片）

| 资产 | 类别 | resolution | 定位（行 / 字符） | 原文引文（逐字，截断） |
|---|---|---|---|---|
| A01 | document | resolved_in_source | document | ”# P153W2-N03 — LBM x FE partitioned strong coupling (Turek-Hron 2D-2 / FSI-2) /  / **Repo** Ten…“ |
| A02 | heading | resolved_in_source | L0–0 / c0–77 | ”# P153W2-N03 — LBM x FE partitioned strong coupling (Turek-Hron 2D-2 / FSI-2)“ |
| A03 | vcs_reference | resolved_in_source | L2–2 / c79–143 | ”**Repo** TensorFEM · **branch** ′agent/m8136′ · **mission** 8136“ |
| A04 | case_geometry | resolved_in_source | L6–7 / c157–299 | ”Turek & Hron (2006) laminar channel 2.5 x 0.41 m, rigid cylinder D = 0.1 m at / (0.2, 0.2) with…“ |
| A05 | parameter_set | resolved_in_source | L8–9 / c300–441 | ”Physical parameters: rho = 1000 kg/m^3, nu = 1e-3 m^2/s, U_mean = 1.0 m/s / (Re = U_mean D / nu…“ |
| A06 | table | resolved_in_source | L13–17 / c475–764 | ”\| case \| what it isolates \| external reference \| / \|---\|---\|---\| / \| 2D-2 cylinder in …“ |
| A07 | code_pointer | referenced_unresolved | L20–22 / c779–985 | ”* **Fluid** ′src/tensorfem/lbm_channel2d.py′: D2Q9 BGK lattice Boltzmann, /   half-way bounce-b…“ |
| A08 | code_pointer | referenced_unresolved | L23–27 / c986–1332 | ”* **Structure** ′CantileverBeamFE′ / ′ModalCantileverBeam′: Euler-Bernoulli /   Hermite finite …“ |
| A09 | code_pointer | referenced_unresolved | L28–33 / c1333–1790 | ”* **Coupling** ′StrongCouplingFSI2′: Dirichlet-Neumann fixed point per time /   step, the body …“ |
| A10 | method_declaration | resolved_in_source | L34–36 / c1791–2006 | ”* **Energy ledger**: fluid kinetic energy (from the populations), structural /   kinetic + stra…“ |
| A11 | table | resolved_in_source | L42–47 / c2083–2404 | ”\| cells/D \| dt [s] \| CD \| CL amplitude \| St \| rel. error CD \| rel. error CL \| rel. erro…“ |
| A12 | validation_statement | resolved_in_source | L48–51 / c2405–2661 | ”Grid refinement (D=12 -> 20): CD changes 1.81%, / St changes 0.35% — the scheme is grid converg…“ |
| A13 | table | resolved_in_source | L55–60 / c2709–3046 | ”\| check \| result \| criterion \| / \|---\|---\|---\| / \| beam f1 vs analytic (1.875^2/(2 pi)…“ |
| A14 | table | resolved_in_source | L67–74 / c3162–3577 | ”\| quantity \| value \| note \| / \|---\|---\|---\| / \| mean sub-iterations / step \| 2.13 \| …“ |
| A15 | table | resolved_in_source | L78–87 / c3606–4443 | ”\| id \| criterion \| computed \| verdict \| / \|---\|---\|---\|---\| / \| C1 \| FSI-2 oscillat…“ |
| A16 | statement | resolved_in_source | L89–90 / c4445–4594 | ”**Verdict: C6 and C7 and C8 pass; C1, C2, C5 fail honestly; C3 and C4 are / WITHHELD. The node …“ |
| A17 | root_cause_set | resolved_in_source | L93–113 / c4631–6052 | ” / 1. **Start-up transient.** The initial condition is the parabolic profile /    everywhere, s…“ |
| A18 | statement | resolved_in_source | L116–125 / c6095–6689 | ” / * a from-scratch D2Q9 lattice-Boltzmann channel solver with bounce-back /   obstacles and mo…“ |
| A19 | falsification_statement | resolved_in_source | L109–112 / c5711–6012 | ”6. **Previously reported PASS is falsified.** ′fsi_turek_hron′ tunes /    f_vortex = 3.0 Hz and…“ |
| A20 | figure_declaration | resolved_in_source | L128–132 / c6705–6928 | ” / * ′artifacts/fsi_strong_coupling/fig_cylinder_validation.png′ / * ′artifacts/fsi_strong_coup…“ |
| A21 | reference_set | resolved_in_source | L135–143 / c6947–7441 | ” / 1. Turek, S., Hron, J. (2006). *Proposal for numerical benchmarking of FSI /    between an e…“ |
| A22 | numeric_anchor | resolved_in_source | L84–84 / c4037–4103 | ”\| C5 \| energy ledger residual (<= 5%) \| 6.693557969802016 \| FAIL \|“ |

> 引文由 `char_span` 切出，平台可对 `source_uri` 重算 sha256 并做子串二次确认；完整 quote 见 manifest。

## ⑤ 注意点与局限

1. **只登记不抽取**：`claims=[]`。上游的「CD −11.2%」「FSI-2 honest-FAIL」「旧模块应降级 MOCK」等结论**未被本工序
   验证**，也没被改写；它们在下游工序才成为知识对象候选。
2. **外部工件不可解析**：3 个 `referenced_unresolved` 指向 TensorFEM 仓的相对路径与符号
   （`src/tensorfem/lbm_channel2d.py`、`CantileverBeamFE`/`ModalCantileverBeam`、`StrongCouplingFSI2`）；
   本工作树是 TensorKnowledge，无该仓代码，报告也未给 commit/URL/DOI——**不猜地址**，如实标 unresolved。
   因此「代码 ↔ 报告数字」的可追溯链在本工序**没有闭合**，需外部仓或 commit 号补齐。
3. **`declared_absent` 为 0**：本报告没有声明缺件，图件声明 4 项在平台 record.figures 中同名存在，
   故登记为 resolved（声明可定位 + 名称比对命中），但**图件字节未做内容核验**（不做图像审读）。
4. **解析口径的边界**：`A03` 只登记到 `branch agent/m8136`，报告未给 commit sha，故「产出对应哪一版代码」
   无法由本工序锁定——这是源文的缺口，不是解析失败。
5. **span 越界已修**：首版生成时 5 处 span 越界/重叠（A04 吞了物理参数行、A07 与 A08 重叠、
   A14 多吞 1 行、A17/A18 溢出到下一节、A20 漏掉第 4 个图件）。改法不是手调数字，而是加 `end_anchor`
   语义（结束行由另一条唯一锚定位）+ 断言 `md.count(quote)==1`，重跑后全绿。
6. **不是 verified**：`provenance.verification_status = "not_verified"`，本工序不越权置位。

## ⑥ 自检：逐条对照 acceptance

| acceptance | 结果 | 证据 |
|---|---|---|
| valid_json | ✅ | manifest 28503 B + envelope 32141 B 均可解析；docs 镜像逐字节相同={'asset_manifest.json': True, 'kf_result.json': True} |
| schema_pass | ✅ | jsonschema 校验 2 个文件（0 error） |
| source_locator_resolvable | ✅ | 22 个定位器在新鲜源文上切片复算，失败 0 |
| source_hash_matches | ✅ | 重算 6e48f09bc41ac354… == 契约 6e48f09bc41ac354…；chars 7442 |
| no_duplicate_ids | ✅ | 22 个 asset_id 无重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=0（零 claim，空真） |
| envelope_links（附加自检，非契约项） | ✅ | provenance.source_hash 与契约一致；verification_status=not_verified |

**阴性对照（证明上面这些 ✅ 不是空真）**：在临时目录副本上注入单点缺陷后，"符合预期" ✅ 表示**指定检查确实翻红**、
门 exit=1（即验收项可被证伪，不是恒真印钞机）：

| 注入的缺陷 | 期望翻红的检查 | 符合预期 | 实际失败的检查项 |
|---|---|---|---|
| baseline | —（基线，期望全绿） | ✅ | — |
| tampered_quote | source_locator_resolvable | ✅ | source_locator_resolvable |
| duplicate_asset_id | no_duplicate_ids | ✅ | no_duplicate_ids |
| missing_required_key | schema_pass | ✅ | schema_pass |
| claim_without_evidence | all_claims_have_evidence_or_explicit_unresolved_status | ✅ | schema_pass, all_claims_have_evidence_or_explicit_unresolved_status |
| wrong_source_hash | envelope_links | ✅ | envelope_links |
| manuscript_mismatch | source_hash_matches | ✅ | source_hash_matches, source_locator_resolvable |

**失败项如实申报**：本轮无诚实失败项；契约 6 项全部 ✅（其中 claims 项在零 claim 下为空真，已在表中注明，
不以造 claim 的方式凑数）。未做/做不到的：外部仓工件地址（§⑤-2）、图件内容核验（§⑤-3）。

**误差判定（key quantity vs 基准）**：本工序无物理量计算，唯一的「计算 vs 基准」是
源文身份：`sha256(markdown)` 与契约值 **逐位相等（相对误差 0%）**、chars 7442 vs 7442（0%）、
标点级切片 21/21 命中（0%）。**是否 <3%：是（实为 0%）**。上游报告里的物理误差
（CD −11.2%、CL −19.2%、St −11.3%，均远超 15%/10% 容差）属**源文内容**，本工序原样登记、不背书、不改判。

**图件说明（无图理由）**：本工序是文档资产登记，不产生任何场量或对比曲线，故 `figures: []`；
可复现性由 §⑥ 的阴性对照表与 §② 的 `repro_cmd` 承担，不虚构图件。

## 唯一结果 JSON 块（kf_result.v1）

```json
{
  "package_id": "wp-10429-01",
  "task_type": "01-asset-registration",
  "report_id": "10429",
  "provenance": {
    "source_uri": "tensor://reports/10429",
    "source_field": "markdown",
    "source_hash": "sha256:6e48f09bc41ac354d46463f6f91ef5b6d34a1ffa7748dcf6a3083c4f6944be1d",
    "source_chars": 7442,
    "source_bytes_utf8": 7448,
    "source_title": "P153W2-N03 TensorFEM x TensorLBM strong-coupling FSI: Turek-Hron 2D-2 anchor + FSI-2 honest-FAIL + energy ledger",
    "scenario_key": "fsi_lbm_strong_coupling",
    "contract_version": "1.0",
    "lane": "C",
    "work_package": "wp-10429-01",
    "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/10429",
    "local_copy": "runs/wp-10429-01/report_10429.md",
    "generator": "scripts/kf_wp10429_01_register.py",
    "verifier": "scripts/kf_wp10429_01_verify.py",
    "artifact_path": "artifacts/wp-10429-01/asset_manifest.json",
    "artifact_sha256": "845c6129a7a9259e96e7127df80d329254972491e9f355e1aacf02c523aa50bb",
    "artifact_bytes": 28503,
    "verification_status": "not_verified"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-10429-01",
      "task_type": "01-asset-registration",
      "report_id": "10429",
      "source": {
        "uri": "tensor://reports/10429",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "6e48f09bc41ac354d46463f6f91ef5b6d34a1ffa7748dcf6a3083c4f6944be1d",
        "chars": 7442,
        "bytes_utf8": 7448,
        "title": "P153W2-N03 TensorFEM x TensorLBM strong-coupling FSI: Turek-Hron 2D-2 anchor + FSI-2 honest-FAIL + energy ledger",
        "scenario_key": "fsi_lbm_strong_coupling",
        "platform_id": 10429,
        "platform_mission_id": 8136,
        "platform_figures": [
          "fig_cylinder_validation",
          "fig_fsi2_history",
          "fig_energy_ledger",
          "fig_summary"
        ],
        "platform_tags": [
          "FSI",
          "Turek-Hron",
          "LBM",
          "strong-coupling",
          "Aitken",
          "energy-ledger",
          "honest-FAIL"
        ],
        "contract_hash": "sha256:6e48f09bc41ac354d46463f6f91ef5b6d34a1ffa7748dcf6a3083c4f6944be1d",
        "contract_chars": 7442,
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/10429",
        "local_copy": "runs/wp-10429-01/report_10429.md",
        "worktree": "/root/tp-agent/work/m15682"
      },
      "counts": {
        "assets": 22,
        "by_class": {
          "document": 1,
          "heading": 1,
          "vcs_reference": 1,
          "case_geometry": 1,
          "parameter_set": 1,
          "table": 5,
          "code_pointer": 3,
          "method_declaration": 1,
          "validation_statement": 1,
          "statement": 2,
          "root_cause_set": 1,
          "falsification_statement": 1,
          "figure_declaration": 1,
          "reference_set": 1,
          "numeric_anchor": 1
        },
        "by_resolution": {
          "resolved_in_source": 19,
          "referenced_unresolved": 3
        },
        "resolved_in_source": 19,
        "referenced_unresolved": 3,
        "declared_absent": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "document",
          "label": "报告正文（markdown 全文，源资产本体）",
          "in_report_section": "(document)",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "document_sha256_matches_contract",
            "result": "resolved",
            "detail": "整篇 markdown sha256 与契约 source_hash 一致"
          },
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 7442,
            "start_line": 0,
            "end_line": 144,
            "quote": "# P153W2-N03 — LBM x FE partitioned strong coupling (Turek-Hron 2D-2 / FSI-2)\n\n**Repo** TensorFEM · **branch** `agent/m8136` · **mission** 8136\n\n## 1. Case\n\nTurek & Hron (2006) laminar channel 2.5 x 0",
            "unique": true,
            "span_chars": 7442
          },
          "note": "整篇 markdown 即源资产；sha256 与 chars 见 source.hash/chars"
        },
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "报告标题行（含 P153W2-N03 编号与主题）",
          "in_report_section": "(document)",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_at_char_span",
            "result": "resolved",
            "detail": "quote 在源 markdown 中逐字命中",
            "found_at_char": 0
          },
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 77,
            "start_line": 0,
            "end_line": 0,
            "quote": "# P153W2-N03 — LBM x FE partitioned strong coupling (Turek-Hron 2D-2 / FSI-2)",
            "unique": true,
            "span_chars": 77
          },
          "note": "标题行；与平台 title 字段同源"
        },
        {
          "asset_id": "A03",
          "asset_class": "vcs_reference",
          "label": "产出来源三元组：Repo TensorFEM / branch agent/m8136 / mission 8136",
          "in_report_section": "# P153W2-N03 — LBM x FE partitioned strong coupling (Turek-Hron 2D-2 / FSI-2)",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_at_char_span",
            "result": "resolved",
            "detail": "quote 在源 markdown 中逐字命中",
            "found_at_char": 79
          },
          "locator": {
            "method": "char_span",
            "start_char": 79,
            "end_char": 143,
            "start_line": 2,
            "end_line": 2,
            "quote": "**Repo** TensorFEM · **branch** `agent/m8136` · **mission** 8136",
            "unique": true,
            "span_chars": 64
          },
          "note": "分支名可登记，但报告未给 commit sha，故无 git 对象可解析（见 resolution_check.detail）"
        },
        {
          "asset_id": "A04",
          "asset_class": "case_geometry",
          "label": "Turek-Hron 2D-2 几何与工况声明（渠道/圆柱/梁尺寸）",
          "in_report_section": "## 1. Case",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_at_char_span",
            "result": "resolved",
            "detail": "quote 在源 markdown 中逐字命中",
            "found_at_char": 157
          },
          "locator": {
            "method": "char_span",
            "start_char": 157,
            "end_char": 299,
            "start_line": 6,
            "end_line": 7,
            "quote": "Turek & Hron (2006) laminar channel 2.5 x 0.41 m, rigid cylinder D = 0.1 m at\n(0.2, 0.2) with an attached elastic beam L = 0.35 m, h = 0.02 m.",
            "unique": true,
            "span_chars": 142
          },
          "note": "几何以文字声明，未附网格文件或 STL；D/L/h 三个尺度是该 FSI 基准的定义量"
        },
        {
          "asset_id": "A05",
          "asset_class": "parameter_set",
          "label": "物理参数集（rho/nu/U_mean/Re/E/rho_s）",
          "in_report_section": "## 1. Case",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_at_char_span",
            "result": "resolved",
            "detail": "quote 在源 markdown 中逐字命中",
            "found_at_char": 300
          },
          "locator": {
            "method": "char_span",
            "start_char": 300,
            "end_char": 441,
            "start_line": 8,
            "end_line": 9,
            "quote": "Physical parameters: rho = 1000 kg/m^3, nu = 1e-3 m^2/s, U_mean = 1.0 m/s\n(Re = U_mean D / nu = 100), beam E = 5.6e6 Pa, rho_s = 1000 kg/m^3.",
            "unique": true,
            "span_chars": 141
          },
          "note": "数值原样登记，不做单位换算"
        },
        {
          "asset_id": "A06",
          "asset_class": "table",
          "label": "两个锚定算例定义表 + 外部参考量（CD/CL/St）",
          "in_report_section": "## 1. Case",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_at_char_span",
            "result": "resolved",
            "detail": "quote 在源 markdown 中逐字命中",
            "found_at_char": 475
          },
          "locator": {
            "method": "char_span",
            "start_char": 475,
            "end_char": 764,
            "start_line": 13,
            "end_line": 17,
            "quote": "| case | what it isolates | external reference |\n|---|---|---|\n| 2D-2 cylinder in channel | fluid solver (wake, drag, Strouhal) | CD = 3.22-3.24, CL amplitude ~ 1.0, St = 0.295-0.305 |\n| FSI-2 cylinder + elastic splitter plate | two-way coupling | Turek-Hron FSI-2 tables (f, A, forces) |\n",
            "unique": true,
            "span_chars": 289
          },
          "note": "外部参考以区间给出（CD=3.22-3.24, St=0.295-0.305）；参考来源见 A18 参考文献集"
        },
        {
          "asset_id": "A07",
          "asset_class": "code_pointer",
          "label": "流体求解器 src/tensorfem/lbm_channel2d.py（外部仓文件）",
          "in_report_section": "## 2. Method",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_lookup",
            "result": "unresolved",
            "detail": "候选中本工作树均不存在（外部仓 TensorFEM 产物）；报告未给 URL/DOI/commit，故不猜地址",
            "searched": [
              "src/tensorfem/lbm_channel2d.py",
              "tensorfem/lbm_channel2d.py"
            ]
          },
          "locator": {
            "method": "char_span",
            "start_char": 779,
            "end_char": 985,
            "start_line": 20,
            "end_line": 22,
            "quote": "* **Fluid** `src/tensorfem/lbm_channel2d.py`: D2Q9 BGK lattice Boltzmann,\n  half-way bounce-back walls and obstacles, momentum-exchange force, Guo\n  forcing, parabolic velocity inlet / zero-gradient outlet.",
            "unique": true,
            "span_chars": 206
          },
          "note": "TensorFEM 仓相对路径；本工作树（TensorKnowledge）内不存在该文件，无法解析到具体版本"
        },
        {
          "asset_id": "A08",
          "asset_class": "code_pointer",
          "label": "结构求解器符号 CantileverBeamFE / ModalCantileverBeam",
          "in_report_section": "## 2. Method",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_lookup",
            "result": "unresolved",
            "detail": "候选中本工作树均不存在（外部仓 TensorFEM 产物）；报告未给 URL/DOI/commit，故不猜地址",
            "searched": [
              "src/tensorfem/beam_fe.py",
              "src/tensorfem/cantilever_beam.py"
            ]
          },
          "locator": {
            "method": "char_span",
            "start_char": 986,
            "end_char": 1332,
            "start_line": 23,
            "end_line": 27,
            "quote": "* **Structure** `CantileverBeamFE` / `ModalCantileverBeam`: Euler-Bernoulli\n  Hermite finite elements with a consistent mass matrix, integrated with\n  Newmark (beta = 1/4, gamma = 1/2); the first 5 generalised modes are retained\n  because the rotational inertia of the fine mesh excites a stiff, unresolved\n  band that destabilises the interface.",
            "unique": true,
            "span_chars": 346
          },
          "note": "仅给符号名，未给文件路径或 commit；本工作树内无同名符号"
        },
        {
          "asset_id": "A09",
          "asset_class": "code_pointer",
          "label": "耦合模块符号 StrongCouplingFSI2（Aitken 动态松弛）",
          "in_report_section": "## 2. Method",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_lookup",
            "result": "unresolved",
            "detail": "候选中本工作树均不存在（外部仓 TensorFEM 产物）；报告未给 URL/DOI/commit，故不猜地址",
            "searched": [
              "src/tensorfem/strong_coupling_fsi2.py",
              "src/tensorfem/fsi_coupling2.py"
            ]
          },
          "locator": {
            "method": "char_span",
            "start_char": 1333,
            "end_char": 1790,
            "start_line": 28,
            "end_line": 33,
            "quote": "* **Coupling** `StrongCouplingFSI2`: Dirichlet-Neumann fixed point per time\n  step, the body is rasterised into a bounce-back mask, the reaction is\n  obtained from the momentum exchange of the boundary links and projected to\n  the FE nodes with the shape functions (resultant conserved by construction),\n  Aitken Delta^2 dynamic relaxation accelerates the sub-iteration and the loop\n  stops on both the displacement and the interface force residuals (1e-4).",
            "unique": true,
            "span_chars": 457
          },
          "note": "符号名 + 方法描述；实现体在外部仓，本工作树不可解析"
        },
        {
          "asset_id": "A10",
          "asset_class": "method_declaration",
          "label": "能量账本构成的五项定义",
          "in_report_section": "## 2. Method",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_at_char_span",
            "result": "resolved",
            "detail": "quote 在源 markdown 中逐字命中",
            "found_at_char": 1791
          },
          "locator": {
            "method": "char_span",
            "start_char": 1791,
            "end_char": 2006,
            "start_line": 34,
            "end_line": 36,
            "quote": "* **Energy ledger**: fluid kinetic energy (from the populations), structural\n  kinetic + strain energy, viscous dissipation from the strain-rate tensor,\n  inlet/outlet kinetic-energy flux and the interface work F.v.",
            "unique": true,
            "span_chars": 215
          },
          "note": "账本项定义原文；账本数值本体见 A13/A15"
        },
        {
          "asset_id": "A11",
          "asset_class": "table",
          "label": "流体锚定结果表（3 组 cells/D × dt，含相对误差）",
          "in_report_section": "### 3.1 Fluid anchor: Turek-Hron 2D-2 (cylinder, Re = 100)",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_at_char_span",
            "result": "resolved",
            "detail": "quote 在源 markdown 中逐字命中",
            "found_at_char": 2083
          },
          "locator": {
            "method": "char_span",
            "start_char": 2083,
            "end_char": 2404,
            "start_line": 42,
            "end_line": 47,
            "quote": "| cells/D | dt [s] | CD | CL amplitude | St | rel. error CD | rel. error CL | rel. error St |\n|---|---|---|---|---|---|---|---|\n| 12 | 8.3e-04 | 2.922 | 0.800 | 0.265 | 9.5% | 20.0% | 11.6% |\n| 20 | 5.0e-04 | 2.869 | 0.808 | 0.266 | 11.2% | 19.2% | 11.3% |\n| 12 | 4.2e-04 | 2.913 | 0.779 | 0.269 | 9.8% | 22.1% | 10.4% |\n",
            "unique": true,
            "span_chars": 321
          },
          "note": "上游自报相对误差；本工序只登记不复核（复核属下游/门）"
        },
        {
          "asset_id": "A12",
          "asset_class": "validation_statement",
          "label": "网格收敛性结论（CD 1.81% / St 0.35%）",
          "in_report_section": "### 3.1 Fluid anchor: Turek-Hron 2D-2 (cylinder, Re = 100)",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_at_char_span",
            "result": "resolved",
            "detail": "quote 在源 markdown 中逐字命中",
            "found_at_char": 2405
          },
          "locator": {
            "method": "char_span",
            "start_char": 2405,
            "end_char": 2661,
            "start_line": 48,
            "end_line": 51,
            "quote": "Grid refinement (D=12 -> 20): CD changes 1.81%,\nSt changes 0.35% — the scheme is grid converged but sits\nabout 11% below the published CD and St and 19% below the lift amplitude\n(the zero-gradient outlet reflects acoustic waves; this is the dominant bias).",
            "unique": true,
            "span_chars": 256
          },
          "note": "结论同时给出主导偏差来源（零梯度出口反射声波）"
        },
        {
          "asset_id": "A13",
          "asset_class": "table",
          "label": "结构与界面验证表（f1 / Newmark 能量漂移 / 静挠度 / 界面合力守恒）",
          "in_report_section": "### 3.2 Structure and interface verification",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_at_char_span",
            "result": "resolved",
            "detail": "quote 在源 markdown 中逐字命中",
            "found_at_char": 2709
          },
          "locator": {
            "method": "char_span",
            "start_char": 2709,
            "end_char": 3046,
            "start_line": 55,
            "end_line": 60,
            "quote": "| check | result | criterion |\n|---|---|---|\n| beam f1 vs analytic (1.875^2/(2 pi) sqrt(EI/m)/L^2) | 1.9736 vs 1.9801 Hz (0.33%) | < 3% |\n| Newmark energy drift over two periods | 2.40e-06 | < 1% |\n| static tip deflection with 8 modes (modal truncation) | 4.87e-06 | < 0.1% |\n| interface force resultant conservation | 2.30e-03 | <= 1% |",
            "unique": true,
            "span_chars": 337
          },
          "note": "4 项自检结果与其判据并列给出"
        },
        {
          "asset_id": "A14",
          "asset_class": "table",
          "label": "耦合 FSI-2 运行清单（步数/子迭代/FFT 峰/幅值/阻力/账本残差）",
          "in_report_section": "### 3.3 Coupled FSI-2 run",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_at_char_span",
            "result": "resolved",
            "detail": "quote 在源 markdown 中逐字命中",
            "found_at_char": 3162
          },
          "locator": {
            "method": "char_span",
            "start_char": 3162,
            "end_char": 3577,
            "start_line": 67,
            "end_line": 74,
            "quote": "| quantity | value | note |\n|---|---|---|\n| mean sub-iterations / step | 2.13 | all steps below tolerance (100%) |\n| median interface force residual | 0.00e+00 | >= 1e-4 target |\n| FFT peak of tip motion | 3.08 Hz | window < 1 shedding period |\n| tip amplitude | 15.6 mm | transient |\n| cylinder drag (window mean) | 56.3 x (1/2 rho U^2 D) | start-up transient |\n| energy ledger residual | 669% | transient window |",
            "unique": true,
            "span_chars": 415
          },
          "note": "运行配置（cells/D=20, u_lat=0.05, dt=2.50e-04, 1200 steps, 5 modes, zeta=2%）在表前一行"
        },
        {
          "asset_id": "A15",
          "asset_class": "table",
          "label": "验收判据表 C1-C8（computed 值与 verdict）",
          "in_report_section": "## 4. Acceptance criteria",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_at_char_span",
            "result": "resolved",
            "detail": "quote 在源 markdown 中逐字命中",
            "found_at_char": 3606
          },
          "locator": {
            "method": "char_span",
            "start_char": 3606,
            "end_char": 4443,
            "start_line": 78,
            "end_line": 87,
            "quote": "| id | criterion | computed | verdict |\n|---|---|---|---|\n| C1 | FSI-2 oscillation frequency vs reference (<= 5%) | 3.0780664123011743 | FAIL |\n| C2 | FSI-2 tip amplitude vs reference (<= 10%) | 0.015588967778231221 | FAIL |\n| C3 | mean CD / CL amplitude of the coupled case (<= 10%) | {'mean_CD': 56.28568448114494, 'amp_CL': 0.987280847455634} | WITHHELD |\n| C4 | flutter critical speed vs Theodorsen (<= 8%) | None | WITHHELD |\n| C5 | energy ledger residual (<= 5%) | 6.693557969802016 | FAIL |\n| C6 | time-step halving changes the answer by <= 3% | {'CD_change': 0.0029459622334283364, 'St_change': 0.013329719722991887, 'CL_change': 0.02633157880836767, 'max_change': 0.02633157880836767} | PASS |\n| C7 | interface force conservation error <= 1% | 0.002303900226913432 | PASS |\n| C8 | honest-FAIL root-cause analysis | None | PASS |",
            "unique": true,
            "span_chars": 837
          },
          "note": "含 FAIL/WITHHELD/PASS 三种判定；本工序不改变其状态、不标 verified"
        },
        {
          "asset_id": "A16",
          "asset_class": "statement",
          "label": "总体判定陈述（2/8 定量判据通过，honest FAIL）",
          "in_report_section": "## 4. Acceptance criteria",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_at_char_span",
            "result": "resolved",
            "detail": "quote 在源 markdown 中逐字命中",
            "found_at_char": 4445
          },
          "locator": {
            "method": "char_span",
            "start_char": 4445,
            "end_char": 4594,
            "start_line": 89,
            "end_line": 90,
            "quote": "**Verdict: C6 and C7 and C8 pass; C1, C2, C5 fail honestly; C3 and C4 are\nWITHHELD. The node is an honest FAIL overall** (2/8 quantitative criteria).",
            "unique": true,
            "span_chars": 149
          },
          "note": "判定陈述原文；数值依据见 A15"
        },
        {
          "asset_id": "A17",
          "asset_class": "root_cause_set",
          "label": "C8 根因分析 6 条（瞬态/算力/无幅值饱和/出口反射/参考转写/旧 PASS 被证伪）",
          "in_report_section": "## 5. Root causes of the FAIL (C8)",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_at_char_span",
            "result": "resolved",
            "detail": "quote 在源 markdown 中逐字命中",
            "found_at_char": 4631
          },
          "locator": {
            "method": "char_span",
            "start_char": 4631,
            "end_char": 6052,
            "start_line": 93,
            "end_line": 113,
            "quote": "\n1. **Start-up transient.** The initial condition is the parabolic profile\n   everywhere, so the splitter plate blocks an impulsive flow: the measured\n   window (0.3 s) is shorter than one shedding period and the drag decays from\n   8.8 kN to 2.8 kN without reaching a steady value.\n2. **Affordability.** A converged FSI-2 needs cells/D ~ 100 and O(10^4) steps;\n   at cells/D = 20 with u_lat = 0.05 one step costs ~70 ms with 2-3 sub-\n   iterations, i.e. ~15 min per second of physical time on one core.\n3. **No amplitude saturation.** The beam is linear (modal); the real benchmark\n   limits the amplitude through geometric nonlinearity. Without it the linear\n   model can only grow or decay.\n4. **Outlet reflections.** The zero-gradient outlet reflects acoustic waves and\n   biases CD / St low by ~11%; this affects both the anchor and the coupled run.\n5. **Reference transcription.** The FSI-2 frequency/force tables could not be\n   re-read offline, so C1/C2/C4 references are the ones already used in the\n   repository; the previous PASS on C4 is now known to be a tautology.\n6. **Previously reported PASS is falsified.** `fsi_turek_hron` tunes\n   f_vortex = 3.0 Hz and F0 = 17.5 N to the answer and reports Re = 100 while\n   the configured inflow gives Re = 30; `find_critical_flutter` returns the\n   closed form 2 sqrt(mu) that it is compared against. Those capabilities must\n   be downgraded to MOCK in the ledger.",
            "unique": true,
            "span_chars": 1421
          },
          "note": "第 6 条含对既有能力 fsi_turek_hron / fsi_flutter 的证伪结论，见 A19 单列"
        },
        {
          "asset_id": "A18",
          "asset_class": "statement",
          "label": "新增且已验证内容清单（4 项）",
          "in_report_section": "## 6. What is genuinely new and verified",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_at_char_span",
            "result": "resolved",
            "detail": "quote 在源 markdown 中逐字命中",
            "found_at_char": 6095
          },
          "locator": {
            "method": "char_span",
            "start_char": 6095,
            "end_char": 6689,
            "start_line": 116,
            "end_line": 125,
            "quote": "\n* a from-scratch D2Q9 lattice-Boltzmann channel solver with bounce-back\n  obstacles and momentum-exchange forces (validated on 2D-2 to 11%/19%/11%);\n* a modal Euler-Bernoulli FE beam verified against the analytic first\n  frequency (0.33%) and Newmark energy conservation (2.4e-6);\n* a partitioned Dirichlet-Neumann coupling with Aitken relaxation, bounce-back\n  moving body, conservative interface projection (0.23% resultant error) and a\n  real sub-iteration convergence history;\n* an energy ledger with all FSI terms, plus the finding that the two existing\n  \"verified\" FSI modules are MOCK.",
            "unique": true,
            "span_chars": 594
          },
          "note": "上游自述『verified』；本工序原样登记，不改写为平台 verified"
        },
        {
          "asset_id": "A19",
          "asset_class": "falsification_statement",
          "label": "证伪结论：fsi_turek_hron（调参+Re=30 当 100）与 fsi_flutter（2sqrt(mu) 同义反复）应降级 MOCK",
          "in_report_section": "## 5. Root causes of the FAIL (C8)",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_at_char_span",
            "result": "resolved",
            "detail": "quote 在源 markdown 中逐字命中",
            "found_at_char": 5711
          },
          "locator": {
            "method": "char_span",
            "start_char": 5711,
            "end_char": 6012,
            "start_line": 109,
            "end_line": 112,
            "quote": "6. **Previously reported PASS is falsified.** `fsi_turek_hron` tunes\n   f_vortex = 3.0 Hz and F0 = 17.5 N to the answer and reports Re = 100 while\n   the configured inflow gives Re = 30; `find_critical_flutter` returns the\n   closed form 2 sqrt(mu) that it is compared against. Those capabilities must",
            "unique": true,
            "span_chars": 301
          },
          "note": "负面结论（capability downgrade 建议）；不由本工序执行降级，仅登记"
        },
        {
          "asset_id": "A20",
          "asset_class": "figure_declaration",
          "label": "图件声明 4 项（artifacts/fsi_strong_coupling/*.png）",
          "in_report_section": "## 7. Figures",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "platform_figures_name_match",
            "result": "present",
            "detail": "declared png 声明 4 个，平台 record.figures 同名 4 个",
            "declared": [
              "fig_cylinder_validation",
              "fig_fsi2_history",
              "fig_energy_ledger",
              "fig_summary"
            ],
            "platform_figure_names": [
              "fig_cylinder_validation",
              "fig_fsi2_history",
              "fig_energy_ledger",
              "fig_summary"
            ]
          },
          "locator": {
            "method": "char_span",
            "start_char": 6705,
            "end_char": 6928,
            "start_line": 128,
            "end_line": 132,
            "quote": "\n* `artifacts/fsi_strong_coupling/fig_cylinder_validation.png`\n* `artifacts/fsi_strong_coupling/fig_fsi2_history.png`\n* `artifacts/fsi_strong_coupling/fig_energy_ledger.png`\n* `artifacts/fsi_strong_coupling/fig_summary.png`",
            "unique": true,
            "span_chars": 223
          },
          "note": "路径为 TensorFEM 仓相对路径；平台 record.figures 里 4 个同名图件已存在（名称逐一对应）"
        },
        {
          "asset_id": "A21",
          "asset_class": "reference_set",
          "label": "参考文献集 4 条（Turek-Hron 2006 / Kuettler-Wall 2008 / Guo 2002 / Newmark 1959）",
          "in_report_section": "## 8. References",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_at_char_span",
            "result": "resolved",
            "detail": "quote 在源 markdown 中逐字命中",
            "found_at_char": 6947
          },
          "locator": {
            "method": "char_span",
            "start_char": 6947,
            "end_char": 7441,
            "start_line": 135,
            "end_line": 143,
            "quote": "\n1. Turek, S., Hron, J. (2006). *Proposal for numerical benchmarking of FSI\n   between an elastic object and laminar incompressible flow.* LNCS 53, 371.\n2. Kuettler, U., Wall, W.A. (2008). *Fixed-point FSI solvers with dynamic\n   relaxation.* Comput. Mech. 42, 1.\n3. Guo, Z., Zheng, C., Shi, B. (2002). *Discrete lattice Boltzmann equation\n   for the forcing term.* Phys. Fluids 14, 2007.\n4. Newmark, N.M. (1959). *A method of computation for structural dynamics.*\n   J. Eng. Mech. Div. 85, 67.",
            "unique": true,
            "span_chars": 494
          },
          "note": "书目条目在源文内可定位；条目未给 DOI/URL，故外部全文不可由本工序解析"
        },
        {
          "asset_id": "A22",
          "asset_class": "numeric_anchor",
          "label": "关键数值锚点：账本残差 6.693557969802016（669%）触发 C5 FAIL",
          "in_report_section": "## 4. Acceptance criteria",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_at_char_span",
            "result": "resolved",
            "detail": "quote 在源 markdown 中逐字命中",
            "found_at_char": 4037
          },
          "locator": {
            "method": "char_span",
            "start_char": 4037,
            "end_char": 4103,
            "start_line": 84,
            "end_line": 84,
            "quote": "| C5 | energy ledger residual (<= 5%) | 6.693557969802016 | FAIL |",
            "unique": true,
            "span_chars": 66
          },
          "note": "单一数字锚；同一量在 A14 以 669% 形式出现（百分比与小数两处一致，仅登记不做换算校验）"
        }
      ],
      "claims": [],
      "claims_note": "工作包契约 objective.classify_report_type=false / notes『不做抽取，claims 允许为空数组』：本工序只登记资产与定位，不生成 claim；claim 抽取留给下游工序。",
      "integrity": {
        "quote_uniqueness": "全部 char_span quote 均由 build_locator 从源 markdown 按行/字符偏移切出，并逐一断言 md.count(quote)==1（见 scripts/kf_wp10429_01_register.py）",
        "zero_hand_copy": "数字/引文无手工键入，全部来自 fetched markdown 的切片",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "contract_hash_echoed": "sha256:6e48f09bc41ac354d46463f6f91ef5b6d34a1ffa7748dcf6a3083c4f6944be1d",
        "verification_status": "not_verified",
        "verification_note": "verification 由平台门计算；本文件不置 verified 标记"
      }
    }
  },
  "claims": []
}
```
