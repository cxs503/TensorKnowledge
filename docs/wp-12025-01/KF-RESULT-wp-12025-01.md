# KF-RESULT wp-12025-01

工序 01-asset-registration · report_id=12025 · lane C · 标题《DEM多面体颗粒接触与休止角验证》 · scenario AG29W1-N06
状态：**draft**（verification 由平台门计算；本工序不标 verified）

## ① 本工序做了什么

只做资产登记，不做抽取、不做分类、不生成 claim。具体三件事：
1. 确认源资产身份：report_id=12025，字段 `markdown`，markdown 432 字符 / 438 字节 UTF-8，
   sha256 = `6ebcceb70d4aa23bd429e13496cfa2ac2fc933c83461eef0a0c58a29321df0ed`，与工作包契约 `source_hash` 逐字节相同（本进程重新登录平台 API 取回后重算）。
2. 把这份 markdown 里**能解析的与不能解析的**资产逐条登记：共 12 条，其中
   页内可解析 6 条、外部挂账 3 条、观测缺失 3 条。
3. 给出每条资产的字符区间定位（locator），8 条 span 级定位合计覆盖原文 98.6%，其余为其补集（文档级 4 条覆盖 100%）。

## ② 怎么做的（步骤/工具/关键设置）

- 取证：Bearer 登录 `POST {base}/auth/login` → `GET {base}/tensor/reports/12025` 取 `markdown` 字段；
  落盘 `runs/wp-12025-01/report_12025.md` 与原始 payload `report_12025.json`。全程不凭记忆、不手抄。
- 哈希门：`hashlib.sha256(md)` 必须等于契约值才写产物，不等则脚本退出码 2、零产物（宁失败不污染）。
- 定位法：锚行（anchor）+ 行内子串偏移（sub）→ 以字符切片取出 quote，**quote 是切出来的，不是敲出来的**；
  断言 `md.count(quote)==1`，不唯一即中止。
- 缺失/挂账判定用机器检查而非断言：`worktree_path_exists`、`worktree_file_search`、
  `address_extraction`（只查 URL/DOI 不联网）、`markdown_image_syntax+platform_figures_field`、
  `markdown_table_and_numeric_literal_scan`、`reproduction_handle_scan`，结果写进每条 `resolution_check`。
- 验收自检：`scripts/kf_verify_12025.py` **另起进程重新登录、重新取源、重新切片**复核 6 项 acceptance
  + 4 项额外纪律；`tests/test_kf_wp12025_01.py` 用 pytest 断言不变量（哈希、切片、唯一性、计数一致性、
  信封 schema、无 verified 标记、平台往返哈希）。
- 一键复跑：`python3 scripts/kf_register_12025.py && python3 scripts/kf_verify_12025.py && python3 -m pytest tests/test_kf_wp12025_01.py -q && python3 scripts/kf_report_12025.py --no-post`

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `artifacts/wp-12025-01/asset_manifest.json` | 本工序唯一交付物；12 资产 + 定位 + 机器判定的解析状态；claims=[]（契约允许）；sha256 `6bd0e4176379143a…` |
| `docs/wp-12025-01/asset_manifest.json` | 逐字节镜像（push 门会丢弃 `artifacts/**`，docs 落地不丢） |
| `runs/wp-12025-01/kf_result.wp-12025-01.json` | 结果信封（kf_result.v1），provenance.source_hash 与契约一致 |
| `runs/wp-12025-01/report_12025.{md,json}` | 源 markdown 与 API 原始 payload（取证留痕，可离线复算哈希） |
| `docs/wp-12025-01/KF-RESULT-wp-12025-01.md` | 本报告（唯一一个 json 围栏块=结果信封） |
| `docs/wp-12025-01/fig_*.png` | 三张图（定位地图/状态分布/验收看板） |
| `scripts/kf_register_12025.py` `scripts/kf_verify_12025.py` | 生产者与独立复核者（互不复用产物） |
| `schemas/asset_manifest.v2.schema.json` | 把 v1 里写死 report_id=448 的两个 const 换成 pattern，使 schema_pass 对任意 report_id 可复现（v1 原样保留） |

## ④ 证据定位表（asset → 原文逐字切片）

| 资产 | 类别 | 解析状态 | 字符区间 | 原文引文（逐字切片） |
|---|---|---|---|---|
| A01 | document | resolved_in_source | 0–432 | `# Polyhedral Particle Contact & Repose Angle Validation  Implemented G` |
| A02 | heading | resolved_in_source | 0–55 | `# Polyhedral Particle Contact & Repose Angle Validation` |
| A03 | abstract | resolved_in_source | 57–216 | `Implemented GJK/EPA contact detection, Coulomb friction + EPSD rolling` |
| A04 | deliverables_list | resolved_in_source | 218–361 | `## Deliverables - polyhedra_repose.py (450 lines) - 42 tests passing (` |
| A05 | code_artifact | referenced_unresolved | 236–267 | `polyhedra_repose.py (450 lines)` |
| A06 | test_evidence_statement | resolved_in_source | 270–309 | `42 tests passing (14 new + 28 existing)` |
| A07 | report_document_ref | referenced_unresolved | 320–361 | `docs/polyhedra_repose_angle_validation.md` |
| A08 | verification_checklist | resolved_in_source | 363–432 | `## Verification - C2: velocity-time <5% error ✓ - C5: 42 tests ≥ 20 ✓` |
| A09 | solver_context | referenced_unresolved | 206–215 | `TensorDEM` |
| A10 | figure_assets | declared_absent | 0–432 | `# Polyhedral Particle Contact & Repose Angle Validation  Implemented G` |
| A11 | quantitative_result_table | declared_absent | 0–432 | `# Polyhedral Particle Contact & Repose Angle Validation  Implemented G` |
| A12 | reproduction_record | declared_absent | 0–432 | `# Polyhedral Particle Contact & Repose Angle Validation  Implemented G` |

每条引文都可 `md[start_char:end_char]` 复现，且全文中唯一（12/12 通过复核）。

## ⑤ 注意点与局限

- **这份报告很短（432 字符），且是"已交付"口吻的摘要**：无参数表、无实测数值、无误差表、无图、无 commit/命令/种子。
  因此 A10/A11/A12 三条 `declared_absent` 是**观测缺失**，不是作者声明——`observed_absent_note` 字段已写明这一点，下游不得引用为"作者确认无图"。
- A06「42 tests passing」与 A08「C2/C5 ✓」只在**文本层**可解析；支撑它们的测试套件、运行日志、实测值都不在报告里（A05/A07 指向 TensorDEM 仓内文件，本工作树无该检出），
  故本工序只登记声明，**不把计数当已复核事实**，也不把它们升为 claim。
- `polyhedra_repose.py`、`docs/polyhedra_repose_angle_validation.md`、`TensorDEM` 三处外部引用均无路径/URL/DOI/commit，
  属于**不可解析挂账**：要真正接入需要上游补 commit 或工件地址（这是本工序对产线的输入性反馈）。
- claims=[] 使 acceptance 项 `all_claims_have_evidence_or_explicit_unresolved_status` **空真**通过；这不是"claim 质量好"的证据，verification.json 里已显式标注。
- 本工序不触及其它 report_id；只读 report 12025。
- 局限（独立性）：生产脚本与复核脚本虽分进程、分别登录取源，但由同一智能体编写，不构成人工独立评审（契约 review.required=false）。

## ⑥ 自检：逐条对照 acceptance

| 检查 | 结果 | 说明 |
|---|---|---|
| valid_json | PASS | — |
| valid_json_envelope | PASS | — |
| source_hash_matches | PASS | — |
| schema_pass | PASS | — |
| source_locator_resolvable | PASS | — |
| no_duplicate_ids | PASS | — |
| all_claims_have_evidence_or_explicit_unresolved_status | PASS | empty claims array (task_type=01 does no extraction) => condition holds vacuously; reported as PASS not as evidence of claim quality |
| extra_result_envelope_schema | PASS | — |
| extra_block_equals_envelope | PASS | single json-fence block content must be the envelope verbatim |
| extra_no_verified_marker | PASS | producer does not label anything verified; gate computes verification |
| extra_counts_consistent | PASS | — |
| extra_kfresult_md_single_json_block | PASS | — |

**误差判定（显式回答 <3%）**：本工序无物理基准量（纯资产登记），可比的"基准"是契约哈希与源切片：
- source_hash 误差 = **0 bit**（重算 6ebcceb70d4aa23b… 与契约逐字节相同）→ **<3% 满足**；
- locator 可解析率 = 12/12 = 100%，失败 0 条 → **<3% 误差满足**；
- span 覆盖率 98.6%（其余由 4 条文档级定位补足 100%）——覆盖率不是精度指标，不参与 <3% 判定，此处列出以免误读。
结论：**没有任何一项超过 3% 的偏差**；同时如实声明：这不代表上游 report 12025 的物理结论已被验证（本工序未做数值复核，也无足够原文可复核）。

```json
{
  "package_id": "wp-12025-01",
  "task_type": "01-asset-registration",
  "report_id": "12025",
  "provenance": {
    "source_uri": "tensor://reports/12025",
    "source_field": "markdown",
    "source_hash": "sha256:6ebcceb70d4aa23bd429e13496cfa2ac2fc933c83461eef0a0c58a29321df0ed",
    "source_chars": 432,
    "source_bytes_utf8": 438,
    "source_title": "DEM多面体颗粒接触与休止角验证",
    "scenario_key": "AG29W1-N06",
    "contract_version": "1.0",
    "lane": "C",
    "work_package": "wp-12025-01",
    "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/12025",
    "local_copy": "runs/wp-12025-01/report_12025.md",
    "artifact_path": "artifacts/wp-12025-01/asset_manifest.json",
    "artifact_sha256": "6bd0e4176379143a77c8a3733c60b3cf3d79e5455afae2b43427d033f317f48e",
    "artifact_bytes": 14330,
    "durable_mirror": "docs/wp-12025-01/asset_manifest.json",
    "generator": "scripts/kf_register_12025.py",
    "verifier": "scripts/kf_verify_12025.py",
    "verification_status": "not_verified"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-12025-01",
      "task_type": "01-asset-registration",
      "report_id": "12025",
      "source": {
        "uri": "tensor://reports/12025",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "6ebcceb70d4aa23bd429e13496cfa2ac2fc933c83461eef0a0c58a29321df0ed",
        "chars": 432,
        "bytes_utf8": 438,
        "title": "DEM多面体颗粒接触与休止角验证",
        "scenario_key": "AG29W1-N06",
        "platform_id": 12025,
        "platform_mission_id": 10151,
        "platform_stage": null,
        "platform_status": "published",
        "platform_figures": [],
        "platform_tags": [
          "DEM",
          "polyhedra",
          "GJK",
          "EPA",
          "repose-angle"
        ],
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/12025",
        "local_copy": "runs/wp-12025-01/report_12025.md"
      },
      "counts": {
        "assets": 12,
        "by_class": {
          "document": 1,
          "heading": 1,
          "abstract": 1,
          "deliverables_list": 1,
          "code_artifact": 1,
          "test_evidence_statement": 1,
          "report_document_ref": 1,
          "verification_checklist": 1,
          "solver_context": 1,
          "figure_assets": 1,
          "quantitative_result_table": 1,
          "reproduction_record": 1
        },
        "by_resolution": {
          "resolved_in_source": 6,
          "referenced_unresolved": 3,
          "declared_absent": 3
        },
        "resolved_in_source": 6,
        "referenced_unresolved": 3,
        "declared_absent": 3
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "document",
          "label": "报告正文（markdown 全文，432 字符）",
          "in_report_section": "(document)",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 432,
            "start_line": 0,
            "end_line": 11,
            "quote": "# Polyhedral Particle Contact & Repose Angle Validation\n\nImplemented GJK/EPA contact detection, Coulomb friction + EPSD rolling resistance, and repose angle measurement protocol for polyhedral particles in TensorDEM.\n\n## Deliverables\n- polyhedra_repose.py (450 lines)\n- 42 tests passing (14 new + 28 existing)\n- Report: docs/polyhedra_repose_angle_validation.md\n\n## Verification\n- C2: velocity-time <5% error ✓\n- C5: 42 tests ≥ 20 ✓",
            "unique": true
          },
          "note": "整篇 markdown 即源资产；sha256 见 source.hash，与契约 source_hash 逐字节相同"
        },
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "报告标题行（英文标题）",
          "in_report_section": "# Polyhedral Particle Contact & Repose Angle Validation",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 55,
            "start_line": 0,
            "end_line": 0,
            "quote": "# Polyhedral Particle Contact & Repose Angle Validation",
            "unique": true
          },
          "note": "与 API title 字段（中文）不同语言，二者互不覆盖：title 取自 record，标题行取自 markdown"
        },
        {
          "asset_id": "A03",
          "asset_class": "abstract",
          "label": "范围声明段（实现了什么）",
          "in_report_section": "# Polyhedral Particle Contact & Repose Angle Validation",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 57,
            "end_char": 216,
            "start_line": 2,
            "end_line": 2,
            "quote": "Implemented GJK/EPA contact detection, Coulomb friction + EPSD rolling resistance, and repose angle measurement protocol for polyhedral particles in TensorDEM.",
            "unique": true
          },
          "note": "单段范围声明；不含数值结果，仅声明实现与验证对象"
        },
        {
          "asset_id": "A04",
          "asset_class": "deliverables_list",
          "label": "交付物清单（标题+3 条）",
          "in_report_section": "## Deliverables",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 218,
            "end_char": 361,
            "start_line": 4,
            "end_line": 7,
            "quote": "## Deliverables\n- polyhedra_repose.py (450 lines)\n- 42 tests passing (14 new + 28 existing)\n- Report: docs/polyhedra_repose_angle_validation.md",
            "unique": true
          },
          "note": "清单本身在页内；三条指向的实体分别登记为 A05/A06/A07"
        },
        {
          "asset_id": "A05",
          "asset_class": "code_artifact",
          "label": "polyhedra_repose.py（450 行）",
          "in_report_section": "## Deliverables",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "address_extraction+worktree_file_search",
            "addresses_found": [],
            "worktree_matches": [],
            "result": "unresolved",
            "detail": "仅在报告文本内检索 URL/DOI，并在工作树内按文件名搜索；不联网猜测地址"
          },
          "locator": {
            "method": "char_span",
            "start_char": 236,
            "end_char": 267,
            "start_line": 5,
            "end_line": 5,
            "quote": "polyhedra_repose.py (450 lines)",
            "unique": true
          },
          "note": "报告只给文件名与行数，无仓库相对路径/URL/commit，无 sha256；代码本体不可由本报告解析"
        },
        {
          "asset_id": "A06",
          "asset_class": "test_evidence_statement",
          "label": "测试计数声明（42 tests，14 new + 28 existing）",
          "in_report_section": "## Deliverables",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "文本可逐字定位；其数值支撑（测试套件/实测值）不在报告内，故不判为已复核"
          },
          "locator": {
            "method": "char_span",
            "start_char": 270,
            "end_char": 309,
            "start_line": 6,
            "end_line": 6,
            "quote": "42 tests passing (14 new + 28 existing)",
            "unique": true
          },
          "note": "声明文本在页内可逐字定位；支撑该计数的测试套件与运行日志未在报告中给出（见 A05/A12），故此处只登记声明，不把计数当作已复核事实"
        },
        {
          "asset_id": "A07",
          "asset_class": "report_document_ref",
          "label": "上游验证报告 docs/polyhedra_repose_angle_validation.md",
          "in_report_section": "## Deliverables",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "docs/polyhedra_repose_angle_validation.md"
            ],
            "missing": [
              "docs/polyhedra_repose_angle_validation.md"
            ],
            "result": "unresolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 320,
            "end_char": 361,
            "start_line": 7,
            "end_line": 7,
            "quote": "docs/polyhedra_repose_angle_validation.md",
            "unique": true
          },
          "note": "仓库相对路径；本工作树（TensorKnowledge）内不存在，属外部仓库（TensorDEM）产物，本报告未附内容"
        },
        {
          "asset_id": "A08",
          "asset_class": "verification_checklist",
          "label": "验证条目 C2/C5（两条带 ✓ 的自检项）",
          "in_report_section": "## Verification",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "文本可逐字定位；其数值支撑（测试套件/实测值）不在报告内，故不判为已复核"
          },
          "locator": {
            "method": "char_span",
            "start_char": 363,
            "end_char": 432,
            "start_line": 9,
            "end_line": 11,
            "quote": "## Verification\n- C2: velocity-time <5% error ✓\n- C5: 42 tests ≥ 20 ✓",
            "unique": true
          },
          "note": "仅两条“通过”标记，无实测值/基准值/样本量；C2 的 <5% 为判据阈值而非测量结果"
        },
        {
          "asset_id": "A09",
          "asset_class": "solver_context",
          "label": "所属求解器 TensorDEM（仓名）",
          "in_report_section": "# Polyhedral Particle Contact & Repose Angle Validation",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_checkout_search",
            "candidates": [
              "TensorDEM",
              "tensor_dem",
              "TensorDem"
            ],
            "found": [],
            "result": "unresolved",
            "detail": "本工作树内无 TensorDEM 检出；报告亦无 commit/版本可解析"
          },
          "locator": {
            "method": "char_span",
            "start_char": 206,
            "end_char": 215,
            "start_line": 2,
            "end_line": 2,
            "quote": "TensorDEM",
            "unique": true
          },
          "note": "仅出现仓名，无提交号/版本/分支；TensorDEM 检出不在本工作树内，无法解析到具体代码状态"
        },
        {
          "asset_id": "A10",
          "asset_class": "figure_assets",
          "label": "图件（场量云图/对比曲线）",
          "in_report_section": "(document)",
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "markdown_image_syntax+platform_figures_field",
            "image_syntax_hits": [],
            "platform_figures_count": 0,
            "result": "absent",
            "detail": "observed-absent：作者未作无图声明，此处只登记观测结果"
          },
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 432,
            "start_line": 0,
            "end_line": 11,
            "quote": "# Polyhedral Particle Contact & Repose Angle Validation\n\nImplemented GJK/EPA contact detection, Coulomb friction + EPSD rolling resistance, and repose angle measurement protocol for polyhedral particles in TensorDEM.\n\n## Deliverables\n- polyhedra_repose.py (450 lines)\n- 42 tests passing (14 new + 28 existing)\n- Report: docs/polyhedra_repose_angle_validation.md\n\n## Verification\n- C2: velocity-time <5% error ✓\n- C5: 42 tests ≥ 20 ✓",
            "unique": true
          },
          "note": "观测式登记：markdown 无任何图片引用，API figures 字段为空数组；报告自身未写“无图”声明，故这是 observed-absent 而非 author-declared-absent"
        },
        {
          "asset_id": "A11",
          "asset_class": "quantitative_result_table",
          "label": "定量结果表（参数表/误差表）",
          "in_report_section": "(document)",
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "markdown_table_and_numeric_literal_scan",
            "table_rows": [],
            "numeric_literals": [],
            "result": "absent",
            "detail": "observed-absent：无表格行；numeric_literals 仅含行数/测试计数/阈值，非实测结果值"
          },
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 432,
            "start_line": 0,
            "end_line": 11,
            "quote": "# Polyhedral Particle Contact & Repose Angle Validation\n\nImplemented GJK/EPA contact detection, Coulomb friction + EPSD rolling resistance, and repose angle measurement protocol for polyhedral particles in TensorDEM.\n\n## Deliverables\n- polyhedra_repose.py (450 lines)\n- 42 tests passing (14 new + 28 existing)\n- Report: docs/polyhedra_repose_angle_validation.md\n\n## Verification\n- C2: velocity-time <5% error ✓\n- C5: 42 tests ≥ 20 ✓",
            "unique": true
          },
          "note": "观测式登记：全文无 markdown 表格、无实测数值与基准数值对照；仅 A08 的两条判据阈值"
        },
        {
          "asset_id": "A12",
          "asset_class": "reproduction_record",
          "label": "复现记录（commit / 运行命令 / 运行 ID / 种子）",
          "in_report_section": "(document)",
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "reproduction_handle_scan",
            "found": {
              "git_commit": [],
              "command": [],
              "run_id": [],
              "seed": []
            },
            "result": "absent",
            "detail": "observed-absent：无 commit/命令/run id/seed 任一可复现句柄"
          },
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 432,
            "start_line": 0,
            "end_line": 11,
            "quote": "# Polyhedral Particle Contact & Repose Angle Validation\n\nImplemented GJK/EPA contact detection, Coulomb friction + EPSD rolling resistance, and repose angle measurement protocol for polyhedral particles in TensorDEM.\n\n## Deliverables\n- polyhedra_repose.py (450 lines)\n- 42 tests passing (14 new + 28 existing)\n- Report: docs/polyhedra_repose_angle_validation.md\n\n## Verification\n- C2: velocity-time <5% error ✓\n- C5: 42 tests ≥ 20 ✓",
            "unique": true
          },
          "note": "观测式登记：全文无 git commit、无命令行、无 run id、无随机种子——450 行代码与 42 个测试均无可复现句柄"
        }
      ],
      "claims": [],
      "claims_note": "按工作包契约 objective.classify_report_type=false 且 notes 允许 claims 为空数组：本工序只登记资产定位，不做 claim 抽取；claim 抽取由下游工作包负责。空数组使 acceptance 项 all_claims_have_evidence_or_explicit_unresolved_status 空真通过。",
      "observed_absent_note": "resolution=declared_absent 的三条（A10/A11/A12）是观测式登记：报告全文未作“无图/无表/无复现记录”的声明，缺失是由扫描判定，不是作者自述。",
      "integrity": {
        "quote_uniqueness": "每条 locator.quote 均为源 markdown 的唯一子串（本脚本断言，scripts/kf_verify_12025.py 独立重算复核）",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true
      }
    }
  }
}
```
