# KF-RESULT wp-14478-01

**报告 14478 → 资产登记（task_type=01-asset-registration，lane B，分层 CASE-CYLINDER-DRAG-FVM | case-cylinder-drag-fvm）。只登记，不抽取、不分类（`classify_report_type=false`），不把任何结论标为 verified。**

## ① 本工序做了什么

登记对象 = 平台报告 `report_id=14478`（`tensor://reports/14478`，字段 `markdown`）。标题（平台记录逐字）：`CASE-CYLINDER-DRAG-FVM: TensorFVM DFG 2D-1 cylinder drag case (per-quantity <5% verdict)`；场景键 `case-cylinder-drag-fvm`；平台 `mission_id=15406`、状态 `published`、标签 `['CASE-CYLINDER-DRAG-FVM', 'TensorFVM', 'DFG-2D-1', 'benchmark', 'drag']`、图片条目 **0** 个。

原文计量（脚本现算，非手抄）：字符 **6156**（契约 `chars: 6156` 一致）、UTF-8 字节 **9430**、`sha256=8fbd643e2e79a0fece5f9ae2fbe87a0045f268d61da54927711e260c14b206b0`（与契约 `source_hash` 逐位一致）。

本工序产出 **一份资产清单**（`asset_manifest.json`）：20 条资产，每条带字符区间 + 行号 + 逐字引文 + 唯一性标记 + payload 状态，**claims = 0 条**（本工序不抽取；填 claims 会伪造属于 03 工序的产物）。

登记到的内容类型（原文自述，非本包复算）：这是一份 **honest-FAIL** 算例报告——TensorFVM 的 DFG 2D-1 圆柱绕流（$Re_D=20$）三档网格作业递交后一直排队未派发，报告里**没有任何 got 数字**；已交付的是参考值抓取链、算例 harness、契约测试。本包只把这些工件/缺口如实登记成资产，**不补任何数值、不把缺口升级为有载荷**。

## ② 怎么做的（步骤/工具/关键设置）

1. `scripts/kf_fetch_14478.py`——用 `TENSOR_AGENT_USER/PASS` 登录取 token，`GET /tensor/reports/14478` 取 `markdown`，**先做双断言**（sha256 与字符数），相符才落盘 `docs/wp-14478-01/source.md`（逐字节保真，`newline=''`）。哈希不符即拒写。仅读 `report_id=14478`，未读任何其它 report_id。
2. `scripts/kf_register_14478.py`——按「锚点串必须在原文中唯一出现」的规则切片生成 locator：起止字符、起止行、逐字引文、`unique` 标记。20 条锚点全部 `count == 1`，任一 ≠ 1 脚本即中止（避免「大致定位」）。锚点选择避开重复出现的文件名裸串（例：`fetch_reference.py` 在原文出现 2 次，故改用带路径的完整串作锚点）。
3. payload 核实（每条资产带 `payload.status` + `checked_how`，说明证据**怎么查的**）——五种状态：`in_report_record` 1、`external_url_declared` 1、`external_repo_path_declared` 12、`declared_payload_missing` 5、`declared_in_source_only` 1。外部仓路径类（TensorFVM 仓内文件/包/符号）**不取字节、不算哈希**——它们不在本报告记录内，也不在本 worktree；原文自述「缺」的 `runs/`、`analysis/`、原生产物、集群 `/tmp` 输出一律登记为 `declared_payload_missing`，不假设存在。
4. `scripts/kf_verify_14478.py`——**独立复核**：重新向平台取一次 markdown、重算哈希，把 20 条引文按区间重新切出来逐字比对（含行号重算），再对两份 JSON 做 schema 校验、id 唯一性、claims 策略、边界与「无自证 verified」检查，输出 `verification.json`。
5. `scripts/kf_figures_14478.py`——由 manifest/verification 渲染 3 张图（ASCII 标签，本镜像无中文字体）。
6. `tests/test_kf_wp14478.py`——19 个 pytest：11 个正控（哈希/字符数/区间回切/唯一性/计数一致性/缺口未升格/两份 schema）+ 8 个负控（篡改引文、位移区间、错行号、重复 id、原文漂移、自证 verified、异号 report_id、envelope 与 manifest 不一致、非法 payload 状态）。
7. 工具链：Python 3.11 + jsonschema（Draft202012Validator）+ matplotlib + pytest；正文数字由脚本从 JSON 直接注入，零手抄。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 是什么 | 要点（机检数字） |
|---|---|---|
| `source.md` | 报告 14478 的 `markdown` 逐字节副本 | 6156 字符 / 9430 字节 / `sha256=8fbd643e2e79a0fe…` |
| `source_meta.json` | 平台记录字段（title/scenario_key/mission_id/tags/figures） | mission_id=15406、figures=0 条 |
| `asset_manifest.json` | **本工序主产物**：20 条资产清单 | 19 类、5 种 payload 状态、claims=0 |
| `kf_result.wp-14478-01.json` | 平台结果信封（package_id/task_type/report_id/provenance/outputs/claims） | provenance.source_hash 与 source.md 哈希逐位一致；outputs 内嵌同一 manifest |
| `verification.json` | 10 项机检结果 | 10/10 PASS（模式：online (platform re-fetch)） |
| `asset_manifest.v1.schema.json` / `kf_result.v1.schema.json` | 机检用 schema | 前者本包自钉（report 14478 专用），后者自 worktree `schemas/` 逐字节复制 |
| `fig_locator_map.png` | locator 覆盖图 | 20 条区间在全文字符轴上的位置 |
| `fig_payload_status.png` | payload 状态分布图 | 见 ② 步 3 的计数 |
| `fig_acceptance_matrix.png` | 验收矩阵图 | 逐条 PASS/FAIL |
| `KF-RESULT-wp-14478-01.md` | 本文件（交付正文） | 唯一一个 `json` 块 = 结果信封 |

## ④ 证据定位表（字段 → 原文逐字引文）

定位口径：`markdown` 全文坐标（0 基字符区间），引文为原文子串且在全文中**唯一**；完整未截断引文见 `asset_manifest.json`。下表引文仅作展示（长引文截断标 `…`，含换行者压平空白）。

| asset_id | 原文节 | 字符区间 | 行 | payload 状态 | 原文引文（逐字） |
|---|---|---|---|---|---|
| A01 | 全文（document locator） | 0–6156 | 1 | `in_report_record` | # CASE-CYLINDER-DRAG-FVM: DFG 2D-1 圆柱阻力算例（TensorFVM）—— honest-FAIL（计算未取回） > 状态：**honest-FAIL / fail_stage = c… |
| A02 | ① 参考值出处 | 805–915 | 24 | `external_url_declared` | https://wwwold.mathematik.tu-dortmund.de/~featflow/en/benchmarks/cfdbenchmarking/flow/dfg_benchmark1_re20.html |
| A03 | ⑥ 失败模式与工件 | 4967–4985 | 125 | `external_repo_path_declared` | featflow_re20.html |
| A04 | ⑥ 失败模式与工件 | 4990–5009 | 125 | `external_repo_path_declared` | featflow_re100.html |
| A05 | ⑥ 失败模式与工件 | 5020–5055 | 126 | `external_repo_path_declared` | `fetch_manifest.json`（URL + sha256） |
| A06 | ⑥ 失败模式与工件 | 5056–5085 | 126 | `external_repo_path_declared` | `reference.json`（解析结果 + 匹配位置） |
| A07 | ① 参考值出处 | 1418–1504 | 31 | `external_repo_path_declared` | `artifacts/case-cylinder-drag-fvm/reference/fetch_reference.py`（抓取→正则→`reference.json` |
| A08 | ② 方法与实现 | 1761–1818 | 40 | `external_repo_path_declared` | 本单新增算例级 harness `scripts/case_cylinder_drag_fvm.py`（三个入口） |
| A09 | ⑥ 失败模式与工件 | 5218–5265 | 129 | `external_repo_path_declared` | `tests/test_case_cylinder_drag_fvm.py`：合成数据契约测试 |
| A10 | ⑥ 失败模式与工件 | 5363–5425 | 131 | `external_repo_path_declared` | `artifacts/case-cylinder-drag-fvm/tools/post_report.py`：报告投递工具 |
| A11 | ⑥ 失败模式与工件 | 5435–5481 | 132 | `declared_payload_missing` | `artifacts/case-cylinder-drag-fvm/runs/`（集群结果） |
| A12 | ⑥ 失败模式与工件 | 5483–5498 | 132 | `declared_payload_missing` | `analysis/`（图件） |
| A13 | ② 方法与实现 | 1856–1903 | 42 | `declared_payload_missing` | （`result.json` / `fields.npz` / `history.json`） |
| A14 | ⑥ 失败模式与工件 | 4595–4634 | 115 | `external_repo_path_declared` | `docs/benchmarks-index.md` 记录 64×24 曾出现 |
| A15 | ② 方法与实现 | 2604–2647 | 59 | `declared_in_source_only` | --out docs/case-cylinder-drag-fvm/report.md |
| A16 | ② 方法与实现 | 1614–1668 | 36 | `external_repo_path_declared` | `tensorfvm.verification.dfg` 提供贴体网格 + SIMPLE/Rhie–Chow |
| A17 | ① 参考值出处 | 1515–1553 | 32 | `external_repo_path_declared` | `tensorfvm.verification.dfg.REFERENCE` |
| A18 | ② 方法与实现 | 2695–2777 | 65 | `declared_payload_missing` | PYTHONPATH=src python -m tensorfvm.verification.dfg --output /tmp/m15406_dfg_64x24 |
| A19 | ⑥ 失败模式与工件 | 5203–5213 | 128 | `declared_payload_missing` | 阻力分项与 7 张图 |
| A20 | ③ 参数表 | 3606–3630 | 85 | `external_repo_path_declared` | `SolverConfig.tolerance` |

原文中被引用的参考量（登记为原文内容，**本包未复核**）：`C_D` 参考值 5.57953523384、`C_L` 参考值 0.010618948146、`p_diff` 参考值 0.11752016697 Pa（三者均出自 §③ 参考值表，来源=DFG 官网页，见 A02/A03）。

## ⑤ 注意点与局限（如实）

1. **本工序不做真值判断**：资产登记只回答「报告里有哪些可解析资产、它们在哪、载荷在不在」，不评判 DFG 算例是否通过、也不评判参考值抓取链是否正确。原报告的 honest-FAIL 结论原样保留。
2. **缺口不升格**：`runs/`、`analysis/`、`result.json`/`fields.npz`/`history.json`、集群 `/tmp/m15406_dfg_*` 输出、analyze 的 7 张图在原文中明确「缺/未产出」，登记为 `declared_payload_missing`；图件名原文未给出，故**不编造文件名**（只登记计数 7）。
3. **外部工件未取字节**：TensorFVM 仓内路径/包/符号（A03–A10、A14、A16、A17、A20）在本 worktree 与本报文记录中都不存在，只登记「原文声明的路径+角色」，其 sha256、内容、是否真实实现（REAL/MOCK）均**未核实**——那属于 02/03 工序。
4. **原文自述的测试结果未重跑**：`pytest tests/test_case_cylinder_drag_fvm.py → 1 passed` 是源报告的自述（A09 的 `declared` 字段），本包未执行该测试（文件不在本 worktree），因此只记为声明，不作为本包的证据。
5. **平台图条目为 0**：平台记录 `figures` 为空数组，故无图端点可探测；`verification.json` 对此给出的是「空集 vacuous PASS + 说明」，不是「探测到 200」。
6. **边界**：只读 `report_id=14478`；未读/未写其它 report_id；未改写任何上游工件；未把任何结论标为 verified。所有写入均在本 worktree 内 `docs/wp-14478-01/`、`scripts/`、`tests/`。
7. **误差判定（必答项）**：本工序**不产生物理量**，因此不存在「相对基准 <3%」的误差判定对象——该问题在此 N/A，理由是本包只做资产登记（契约 `objective.register_assets=true`、`classify_report_type=false`）。可被判定的只有**位级一致性**：源哈希逐位相等（0 偏差）、字符数 6156=6156（0 偏差）、20/20 引文区间回切逐字相等（0 偏差）。原报告自身的物理误差判定（$C_D/C_L/p_{diff}$ vs 5% 门）因无 got 数据而为 FAIL，本包不改写该结论。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 机检细节 |
|---|---|---|
| `source_hash_matches` | ✅ PASS | {"sha256": "8fbd643e2e79a0fece5f9ae2fbe87a0045f268d61da54927711e260c14b206b0", "note": "recomputed from live platform re-fetch"} |
| `chars_match_contract` | ✅ PASS | {"chars": 6156} |
| `valid_json` | ✅ PASS | {"files": ["asset_manifest.json", "kf_result.wp-14478-01.json"], "parse": "ok"} |
| `schema_pass` | ✅ PASS | {"errors": "无", "documents": 2} |
| `source_locator_resolvable` | ✅ PASS | {"assets_checked": 20, "errors": "无"} |
| `no_duplicate_ids` | ✅ PASS | {"errors": "无"} |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✅ PASS | {"claims": 0, "errors": "无"} |
| `boundaries_and_no_self_verified` | ✅ PASS | {"errors": "无"} |
| `record_metadata_verbatim` | ✅ PASS | {"source": "live platform record", "errors": "无"} |
| `platform_figure_payload_status_current` | ✅ PASS | {"platform_figures": 0, "note": "the platform record carries no figure entries, so no figure payload can be missing; vacuous pass recorded explicitly rather th… |

契约声明的 6 项 acceptance：`valid_json`、`schema_pass`、`source_locator_resolvable`、`source_hash_matches`、`no_duplicate_ids`、`all_claims_have_evidence_or_explicit_unresolved_status` —— 全部 ✅（上表前段）。附加 4 项为 本仓追加的加固检查（字符数一致、边界与无自证 verified、记录元数据逐字一致、平台图载荷状态）。**无失败项；无 NOT_RUN 项**（本次以在线模式跑：`online (platform re-fetch)`，verified_at=2026-11-12T02:37:16+00:00）。

### honest 声明

- 没有做：任何抽取（claims=0）、任何分类、任何数值复算、任何外部仓字节取证。
- 没有做而契约也不要求的：独立评审（`review.required=false`）。
- 未把任何结论标为 verified；`verified` 由平台门计算。

## 一键复跑（repro_cmd）

```text
export TENSOR_API_BASE=http://127.0.0.1:8010/api/v1 TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=...
python3 scripts/kf_fetch_14478.py      # GET /tensor/reports/14478 → 双断言(sha256+chars) → docs/wp-14478-01/source.md
python3 scripts/kf_register_14478.py   # 锚点唯一性校验 → asset_manifest.json + kf_result.wp-14478-01.json
python3 scripts/kf_verify_14478.py     # 独立复取+重算哈希+区间回切+schema → verification.json（逐条 PASS/FAIL）
python3 scripts/kf_figures_14478.py    # 3 张图 → fig_*.png
python3 scripts/kf_report_14478.py     # 生成本报告正文（唯一 json 块）
python3 -m pytest tests/test_kf_wp14478.py -q   # 19 passed（含 8 个负控）
```

## 结果信封（唯一 json 块）

```json
{
  "package_id": "wp-14478-01",
  "task_type": "01-asset-registration",
  "report_id": "14478",
  "provenance": {
    "source_uri": "tensor://reports/14478",
    "source_field": "markdown",
    "source_hash": "sha256:8fbd643e2e79a0fece5f9ae2fbe87a0045f268d61da54927711e260c14b206b0",
    "producer": "kf-wp14478-01 asset registration (scripts/kf_register_14478.py)",
    "emitted_at": "2026-11-12T02:37:16+00:00",
    "notes": "hash = sha256 of the exact UTF-8 bytes of the report markdown field; recomputed from the platform on every verify run"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-14478-01",
      "task_type": "01-asset-registration",
      "report_id": "14478",
      "objective": {
        "register_assets": true,
        "classify_report_type": false
      },
      "source": {
        "uri": "tensor://reports/14478",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "8fbd643e2e79a0fece5f9ae2fbe87a0045f268d61da54927711e260c14b206b0",
        "chars": 6156,
        "bytes_utf8": 9430,
        "contract_chars": 6156,
        "title": "CASE-CYLINDER-DRAG-FVM: TensorFVM DFG 2D-1 cylinder drag case (per-quantity <5% verdict)",
        "scenario_key": "case-cylinder-drag-fvm",
        "platform_mission_id": 15406,
        "platform_status": "published",
        "platform_created_at": "2026-11-11T23:32:12.640144+00:00",
        "platform_tags": [
          "CASE-CYLINDER-DRAG-FVM",
          "TensorFVM",
          "DFG-2D-1",
          "benchmark",
          "drag"
        ],
        "platform_figures": []
      },
      "counts": {
        "assets": 20,
        "by_class": {
          "source_document": 1,
          "reference_authority_page": 1,
          "reference_page_archive": 2,
          "provenance_manifest": 1,
          "reference_data": 1,
          "reference_parser": 1,
          "case_harness": 1,
          "contract_test": 1,
          "report_tool": 1,
          "solver_run_output": 1,
          "analysis_output": 1,
          "native_solver_outputs": 1,
          "repo_doc": 1,
          "report_document": 1,
          "solver_code": 1,
          "reference_constant": 1,
          "cluster_job": 1,
          "figure_set": 1,
          "solver_config": 1
        },
        "by_payload_status": {
          "in_report_record": 1,
          "external_url_declared": 1,
          "external_repo_path_declared": 12,
          "declared_payload_missing": 5,
          "declared_in_source_only": 1
        },
        "reference_values_quoted": 3,
        "claims": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "source_document",
          "label": "tensor://reports/14478 markdown（本包登记的唯一原文）",
          "in_report_section": "全文（document locator）",
          "locator": {
            "method": "document",
            "source_field": "markdown",
            "start_char": 0,
            "end_char": 6156,
            "start_line": 1,
            "end_line": 145,
            "quote": "# CASE-CYLINDER-DRAG-FVM: DFG 2D-1 圆柱阻力算例（TensorFVM）—— honest-FAIL（计算未取回）\n\n> 状态：**honest-FAIL / fail_stage = compute_wait（集群排队未取回结果）**\n> 本文件在计算作业仍在集群排队时写成，不含任何未经计算的“got”数字。已交付的是可复现的\n> 算例 harness、机器解析的",
            "unique": true
          },
          "payload": {
            "status": "in_report_record",
            "checked_how": "GET /tensor/reports/14478 → field markdown; sha256 + char count recomputed and compared with the work-package contract",
            "evidence": {
              "sha256": "8fbd643e2e79a0fece5f9ae2fbe87a0045f268d61da54927711e260c14b206b0",
              "chars": 6156,
              "bytes_utf8": 9430
            }
          },
          "note": "Whole-document locator: span covers the entire pinned markdown; the envelope provenance.source_hash is this asset's hash."
        },
        {
          "asset_id": "A02",
          "asset_class": "reference_authority_page",
          "label": "Turek 组 FeatFlow DFG 2D-1 官网页（Re=20 参考值来源）",
          "in_report_section": "① 参考值出处",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 805,
            "end_char": 915,
            "start_line": 24,
            "end_line": 24,
            "quote": "https://wwwold.mathematik.tu-dortmund.de/~featflow/en/benchmarks/cfdbenchmarking/flow/dfg_benchmark1_re20.html",
            "unique": true
          },
          "payload": {
            "status": "external_url_declared",
            "checked_how": "URL quoted verbatim from the markdown; not fetched by this package (external network, and the source itself reports fetch restrictions in ‘生态摩擦’ item 4)",
            "declared": {
              "used_for": "C_D=5.57953523384 / C_L=0.010618948146 / p_diff=0.11752016697 Pa (§③ 参考值表)"
            }
          },
          "note": "Payload bytes are NOT registered here: the archived copy is A03."
        },
        {
          "asset_id": "A03",
          "asset_class": "reference_page_archive",
          "label": "归档页 featflow_re20.html（Re=20 官网页原文）",
          "in_report_section": "⑥ 失败模式与工件",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 4967,
            "end_char": 4985,
            "start_line": 125,
            "end_line": 125,
            "quote": "featflow_re20.html",
            "unique": true
          },
          "payload": {
            "status": "external_repo_path_declared",
            "checked_how": "path quoted verbatim; the file lives in the TensorFVM repo worktree (artifacts/case-cylinder-drag-fvm/reference/), which is outside this report record and this TensorKnowledge worktree — no bytes fetched or hashed by this package"
          },
          "note": "Registered as a path+role only; its sha256 is said to be recorded in fetch_manifest.json (A05), not re-derived here."
        },
        {
          "asset_id": "A04",
          "asset_class": "reference_page_archive",
          "label": "归档页 featflow_re100.html（Re=100 同族页，本算例未用其数值）",
          "in_report_section": "⑥ 失败模式与工件",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 4990,
            "end_char": 5009,
            "start_line": 125,
            "end_line": 125,
            "quote": "featflow_re100.html",
            "unique": true
          },
          "payload": {
            "status": "external_repo_path_declared",
            "checked_how": "same boundary as A03 — path quoted verbatim, bytes not fetched"
          },
          "note": "The report does not state that any Re=100 value enters the verdict; it is listed only among archived pages."
        },
        {
          "asset_id": "A05",
          "asset_class": "provenance_manifest",
          "label": "fetch_manifest.json（URL + sha256 归档清单）",
          "in_report_section": "⑥ 失败模式与工件",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 5020,
            "end_char": 5055,
            "start_line": 126,
            "end_line": 126,
            "quote": "`fetch_manifest.json`（URL + sha256）",
            "unique": true
          },
          "payload": {
            "status": "external_repo_path_declared",
            "checked_how": "path and declared content (‘URL + sha256’) quoted verbatim; file not read by this package"
          },
          "note": "The per-URL sha256 values are NOT reproduced here — reading them would require the TensorFVM worktree."
        },
        {
          "asset_id": "A06",
          "asset_class": "reference_data",
          "label": "reference.json（正则解析结果 + 匹配位置）",
          "in_report_section": "⑥ 失败模式与工件",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 5056,
            "end_char": 5085,
            "start_line": 126,
            "end_line": 126,
            "quote": "`reference.json`（解析结果 + 匹配位置）",
            "unique": true
          },
          "payload": {
            "status": "external_repo_path_declared",
            "checked_how": "path quoted verbatim; file not read by this package"
          },
          "note": "The three reference numbers are registered as quoted report text (source_document quotes in the delivery report), not from this JSON."
        },
        {
          "asset_id": "A07",
          "asset_class": "reference_parser",
          "label": "fetch_reference.py（抓取→正则→reference.json，含 drift 比对）",
          "in_report_section": "① 参考值出处",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 1418,
            "end_char": 1504,
            "start_line": 31,
            "end_line": 31,
            "quote": "`artifacts/case-cylinder-drag-fvm/reference/fetch_reference.py`（抓取→正则→`reference.json`",
            "unique": true
          },
          "payload": {
            "status": "external_repo_path_declared",
            "checked_how": "path quoted verbatim; script not executed by this package"
          },
          "note": "零手抄 mechanism claimed by the source; this package does not re-run it (out of boundary)."
        },
        {
          "asset_id": "A08",
          "asset_class": "case_harness",
          "label": "scripts/case_cylinder_drag_fvm.py（solve / analyze / report 三入口）",
          "in_report_section": "② 方法与实现",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 1761,
            "end_char": 1818,
            "start_line": 40,
            "end_line": 40,
            "quote": "本单新增算例级 harness `scripts/case_cylinder_drag_fvm.py`（三个入口）",
            "unique": true
          },
          "payload": {
            "status": "external_repo_path_declared",
            "checked_how": "path quoted verbatim; harness not executed by this package (its runs/ output is absent, A11)"
          },
          "note": "Only the declared接口面 (3 entry points) is registered; no behaviour is asserted."
        },
        {
          "asset_id": "A09",
          "asset_class": "contract_test",
          "label": "tests/test_case_cylinder_drag_fvm.py（合成数据契约测试）",
          "in_report_section": "⑥ 失败模式与工件",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 5218,
            "end_char": 5265,
            "start_line": 129,
            "end_line": 129,
            "quote": "`tests/test_case_cylinder_drag_fvm.py`：合成数据契约测试",
            "unique": true
          },
          "payload": {
            "status": "external_repo_path_declared",
            "checked_how": "path quoted verbatim; the file is not in this worktree and was not run",
            "declared": {
              "claimed_result": "pytest tests/test_case_cylinder_drag_fvm.py → 1 passed"
            }
          },
          "note": "The claim ‘1 passed’ is the source's own statement (declared_in_source_only), NOT re-executed here."
        },
        {
          "asset_id": "A10",
          "asset_class": "report_tool",
          "label": "artifacts/case-cylinder-drag-fvm/tools/post_report.py（报告投递工具）",
          "in_report_section": "⑥ 失败模式与工件",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 5363,
            "end_char": 5425,
            "start_line": 131,
            "end_line": 131,
            "quote": "`artifacts/case-cylinder-drag-fvm/tools/post_report.py`：报告投递工具",
            "unique": true
          },
          "payload": {
            "status": "external_repo_path_declared",
            "checked_how": "path quoted verbatim; file not read by this package"
          },
          "note": "No payload bytes registered."
        },
        {
          "asset_id": "A11",
          "asset_class": "solver_run_output",
          "label": "artifacts/case-cylinder-drag-fvm/runs/（集群三档网格结果）",
          "in_report_section": "⑥ 失败模式与工件",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 5435,
            "end_char": 5481,
            "start_line": 132,
            "end_line": 132,
            "quote": "`artifacts/case-cylinder-drag-fvm/runs/`（集群结果）",
            "unique": true
          },
          "payload": {
            "status": "declared_payload_missing",
            "checked_how": "the markdown itself states this path is missing (‘缺’, ‘本单未产出’); nothing to fetch, and inventing content is forbidden",
            "declared": {
              "missing_because": "§④ FAIL：三作业排队 9.6 min 未派发，本单预算内未取回任何 result.json"
            }
          },
          "note": "Unresolved by design: the deliverable is the missing-payload record, not the numbers."
        },
        {
          "asset_id": "A12",
          "asset_class": "analysis_output",
          "label": "artifacts/case-cylinder-drag-fvm/analysis/（判据/收敛/分项/图件）",
          "in_report_section": "⑥ 失败模式与工件",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 5483,
            "end_char": 5498,
            "start_line": 132,
            "end_line": 132,
            "quote": "`analysis/`（图件）",
            "unique": true
          },
          "payload": {
            "status": "declared_payload_missing",
            "checked_how": "same line as A11 declares runs/ and analysis/ both absent; not synthesised here",
            "declared": {
              "missing_because": "analysis requires runs/, which was never retrieved"
            }
          },
          "note": "Unresolved by design."
        },
        {
          "asset_id": "A13",
          "asset_class": "native_solver_outputs",
          "label": "包内原生求解产物：result.json / fields.npz / history.json",
          "in_report_section": "② 方法与实现",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 1856,
            "end_char": 1903,
            "start_line": 42,
            "end_line": 42,
            "quote": "（`result.json` / `fields.npz` / `history.json`）",
            "unique": true
          },
          "payload": {
            "status": "declared_payload_missing",
            "checked_how": "output filenames quoted verbatim as the declared native format; no instance exists (runs/ absent, A11)"
          },
          "note": "Format declaration only — zero instances registered."
        },
        {
          "asset_id": "A14",
          "asset_class": "repo_doc",
          "label": "docs/benchmarks-index.md（仓内基准索引，含 64×24 历史误差 13.36%）",
          "in_report_section": "⑥ 失败模式与工件",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 4595,
            "end_char": 4634,
            "start_line": 115,
            "end_line": 115,
            "quote": "`docs/benchmarks-index.md` 记录 64×24 曾出现",
            "unique": true
          },
          "payload": {
            "status": "external_repo_path_declared",
            "checked_how": "path quoted verbatim; the TensorFVM repo doc is not present in this worktree and was not read",
            "declared": {
              "quoted_number": "C_D 误差 ≈13.36%（源文自述的历史记录，本包未复核）"
            }
          },
          "note": "The 13.36% figure is registered as the source's own statement, not verified."
        },
        {
          "asset_id": "A15",
          "asset_class": "report_document",
          "label": "docs/case-cylinder-drag-fvm/report.md（report 入口的生成目标）",
          "in_report_section": "② 方法与实现",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 2604,
            "end_char": 2647,
            "start_line": 59,
            "end_line": 59,
            "quote": "--out docs/case-cylinder-drag-fvm/report.md",
            "unique": true
          },
          "payload": {
            "status": "declared_in_source_only",
            "checked_how": "path appears only inside the repro command block of the markdown; no bytes of it are in the record, so its existence is unconfirmed here"
          },
          "note": "Self-referential generator target of the registered report itself; not resolved by this package."
        },
        {
          "asset_id": "A16",
          "asset_class": "solver_code",
          "label": "tensorfvm.verification.dfg 包（贴体网格 + SIMPLE/Rhie–Chow + 壁面牵引/压力重构）",
          "in_report_section": "② 方法与实现",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 1614,
            "end_char": 1668,
            "start_line": 36,
            "end_line": 36,
            "quote": "`tensorfvm.verification.dfg` 提供贴体网格 + SIMPLE/Rhie–Chow",
            "unique": true
          },
          "payload": {
            "status": "external_repo_path_declared",
            "checked_how": "module path quoted verbatim; TensorFVM package not installed/checked out in this worktree — capability claims (REAL vs MOCK) are NOT assessed by this package"
          },
          "note": "Evidence-level grading of the solver is out of scope for task_type=01."
        },
        {
          "asset_id": "A17",
          "asset_class": "reference_constant",
          "label": "包内常量 tensorfvm.verification.dfg.REFERENCE（与 reference.json 漂移比对，drift=无）",
          "in_report_section": "① 参考值出处",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 1515,
            "end_char": 1553,
            "start_line": 32,
            "end_line": 32,
            "quote": "`tensorfvm.verification.dfg.REFERENCE`",
            "unique": true
          },
          "payload": {
            "status": "external_repo_path_declared",
            "checked_how": "symbol quoted verbatim; not readable in this worktree",
            "declared": {
              "drift": "无（源文自述）"
            }
          },
          "note": "‘drift = 无’ is the source's assertion; this package neither recomputes nor upgrades it."
        },
        {
          "asset_id": "A18",
          "asset_class": "cluster_job",
          "label": "集群作业三连（/tmp/m15406_dfg_*，各档独立作业）",
          "in_report_section": "② 方法与实现",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 2695,
            "end_char": 2777,
            "start_line": 65,
            "end_line": 65,
            "quote": "PYTHONPATH=src python -m tensorfvm.verification.dfg --output /tmp/m15406_dfg_64x24",
            "unique": true
          },
          "payload": {
            "status": "declared_payload_missing",
            "checked_how": "command quoted verbatim; the three /tmp outputs were never retrieved (§④) and /tmp is not part of any repo — nothing registered",
            "declared": {
              "jobs": [
                "m15406_dfg_64x24",
                "m15406_dfg_128x48",
                "m15406_dfg_256x96"
              ],
              "state_at_write": "queued"
            }
          },
          "note": "Only the 64x24 command line is the locator anchor; the other two are named in declared.jobs because each /tmp token is quoted in the source."
        },
        {
          "asset_id": "A19",
          "asset_class": "figure_set",
          "label": "analyze 生成的 7 张图（运行点/场量/收敛等）",
          "in_report_section": "⑥ 失败模式与工件",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 5203,
            "end_char": 5213,
            "start_line": 128,
            "end_line": 128,
            "quote": "阻力分项与 7 张图",
            "unique": true
          },
          "payload": {
            "status": "declared_payload_missing",
            "checked_how": "the count ‘7 张图’ is quoted verbatim; analysis/ is absent (A12) and the markdown names no figure filenames",
            "declared": {
              "figure_count": 7
            }
          },
          "note": "Individual figure names are NOT registered: the source does not name them, and inventing names is forbidden."
        },
        {
          "asset_id": "A20",
          "asset_class": "solver_config",
          "label": "包内配置项 SolverConfig.tolerance（收敛判据 1e-6）",
          "in_report_section": "③ 参数表",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 3606,
            "end_char": 3630,
            "start_line": 85,
            "end_line": 85,
            "quote": "`SolverConfig.tolerance`",
            "unique": true
          },
          "payload": {
            "status": "external_repo_path_declared",
            "checked_how": "symbol quoted verbatim; source tree not present in this worktree"
          },
          "note": "Parameter table value (1e-6) is content of the source, not re-measured."
        }
      ],
      "claims": [],
      "claims_note": "claims intentionally empty: contract objective is asset registration only (classify_report_type=false, no extraction). Filling claims here would fabricate knowledge objects that belong to task_type 03.",
      "integrity": {
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "chars_match_contract": true,
        "all_locators_unique_quotes": true,
        "verified_by": "scripts/kf_verify_14478.py (re-fetches the report independently)",
        "no_file_outside_worktree_written": true,
        "other_report_ids_touched": 0
      },
      "boundaries": {
        "only_report_id": "14478",
        "other_reports_read": false,
        "upstream_artifacts_rewritten": false,
        "claims_marked_verified": 0
      }
    }
  },
  "claims": []
}
```
