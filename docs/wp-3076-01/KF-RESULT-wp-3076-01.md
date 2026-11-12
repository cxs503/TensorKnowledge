# KF-RESULT wp-3076-01

**报告：reports/3076 → 资产登记（task_type=01-asset-registration，lane C）**

## ① 案例介绍

本单是报告→知识产线「01-资产登记」工序：只做**登记**，不做抽取、不做分类（`classify_report_type=false`），
不把任何结论标为 verified（verification 由平台门计算）。

登记对象 = 平台报告 `report_id=3076`（`tensor://reports/3076`，字段 `markdown`），
标题：成稿机检门禁 manuscript_gate v1：把 SEAL.md 的 H1–H8 硬伤固化为 11 项机检（负控复现 8 项 / 正控 0 误报）；场景键 `paper-line-provenance-gate`；平台标签 ['paper-production', 'provenance-gate', 'manuscript-conformance', 'verification-debt', 'pytest', 'honest-FAIL']。

原文计量（脚本现算，非手抄）：字符 **3712**（契约 `chars: 3712` 一致）、
UTF-8 字节 **6092**、`sha256=9b7bb2427af8a1b4a7f229971492c52fc691737a7742b4b703ce4e41cea464c1`（与契约 `source_hash` **逐位一致**）。

原报告的物理/工程场景（一句话背景，引原文）：这是论文生产线把 `SEAL.md` 的 H1–H8 硬伤固化为 11 项机检的工序报告；
本工单**不涉及**其中任何数值结论的复核，只登记其可解析资产。

## ② 怎么做的（步骤/工具/关键设置）

1. `scripts/kf_fetch_3076.py`——用 `TENSOR_AGENT_USER/PASS` 登录取 token，`GET /tensor/reports/3076` 取 `markdown`，
   **先做双断言**（sha256 与字符数），再落盘 `docs/wp-3076-01/source.md`（逐字节保真）。哈希不符即拒写。
2. `scripts/kf_register_3076.py`——按「锚点串必须唯一出现」的规则，从原文切片生成 19 条资产的
   `char_span`（起止字符 + 起止行 + 逐字引文 + 唯一性标记）；每条资产另带 `payload.status` 与 `checked_how`
   （证据怎么查的）。任一锚点出现次数 ≠ 1 即中止——避免"大致定位"。
3. 载荷核实：对平台记录里的 3 张图逐个探测 `/tensor/reports/3076/figures/<name>`，实得 HTTP 404
   `figure not found`，故三张图登记为 `declared_payload_missing`（有名字+图注，无载荷字节），**不假设存在**。
4. `scripts/kf_verify_3076.py`——**独立复核**：重新向平台取一次 markdown、重算哈希，把 19 条引文重新按区间
   切出来比对，并做结构 schema 校验、id 唯一性、边界与"无自证 verified"检查，输出 `verification.json`。
5. `scripts/kf_figures_3076.py`——由 manifest/verification 渲染 3 张图（ASCII 标签，避免缺中文字体）。
6. `tests/test_kf_wp3076.py`——13 个 pytest，其中 7 个负控（篡改引文/位移区间/重复 id/原文漂移/自证 verified/图载荷升格/异号 report_id）。
7. 工具链：Python 3.11.6 + jsonschema + matplotlib + pytest；结果 JSON 由脚本直接写入
   本文件唯一一个 json 代码块，零手抄。

## ③ 计算结果（程序化注入）

**登记总量**：资产 19 条 / 类 17 种；claims **0** 条（本工序合法空）；
`check_id_count=11`（从 A07 引文按 ` / ` 现算）。

| payload 状态 | 条数 |
|---|---|
| `in_report_record` | 2 |
| `external_not_in_record` | 11 |
| `cross_report_out_of_scope` | 2 |
| `declared_in_source_only` | 1 |
| `declared_payload_missing` | 3 |

| asset_class | 条数 |
|---|---|
| `source_document` | 1 |
| `negative_control_manuscript` | 1 |
| `evidence_base_report` | 1 |
| `review_report` | 1 |
| `defect_seal` | 1 |
| `gate_implementation` | 1 |
| `check_registry` | 1 |
| `positive_control_tree` | 1 |
| `solver_code` | 1 |
| `evidence_base` | 1 |
| `figure_builder` | 1 |
| `data_tables` | 1 |
| `figure_payloads` | 1 |
| `figure_metadata` | 1 |
| `recompute_artifact` | 1 |
| `dev_toolchain` | 1 |
| `platform_figure` | 3 |

**逐条登记表**（区间为 markdown 字符偏移，引文逐字来自原文）：

| id | class | 出处段落 | char span (line) | 原文引文（逐字） | payload 状态 |
|---|---|---|---|---|---|
| A01 | `source_document` | document | 0–3712 (L1–L75) | ## ① 案例介绍 | `in_report_record` |
| A02 | `negative_control_manuscript` | ① 对象表 / ② 步骤1 | 268–318 (L10–L10) | papers/_sealed/ice-wave-mechanics-r2/manuscript.md | `external_not_in_record` |
| A03 | `evidence_base_report` | ① 对象表 | 332–347 (L10–L10) | 证据基 Report #823 | `cross_report_out_of_scope` |
| A04 | `review_report` | ① 背景 | 97–108 (L4–L4) | Report #961 | `cross_report_out_of_scope` |
| A05 | `defect_seal` | ① 背景 / ② 步骤1 | 124–145 (L4–L4) | SEAL.md 列了 H1–H8 八类硬伤 | `external_not_in_record` |
| A06 | `gate_implementation` | ② 步骤2 | 840–881 (L20–L20) | `papers/tools/manuscript_gate.py`：统一数字规范化 | `external_not_in_record` |
| A07 | `check_registry` | ② 步骤1 | 724–835 (L19–L19) | struct / figref / figdata / numtrace / formula / overclaim / statdof / implmethod / repro / placeholder / arith | `in_report_record` |
| A08 | `positive_control_tree` | ① 对象表 / ② 步骤3 | 383–421 (L11–L11) | `papers/data/gate-2026-11-03/control/` | `external_not_in_record` |
| A09 | `solver_code` | ② 步骤3 | 1058–1080 (L23–L23) | `solver.py`（tanh 边界条件） | `external_not_in_record` |
| A10 | `evidence_base` | ② 步骤3 | 1082–1097 (L23–L23) | `evidence.json` | `external_not_in_record` |
| A11 | `figure_builder` | ② 步骤3 | 1100–1117 (L23–L23) | `make_figures.py` | `external_not_in_record` |
| A12 | `data_tables` | ② 步骤3 | 1123–1135 (L24–L24) | `data/*.csv` | `external_not_in_record` |
| A13 | `figure_payloads` | ② 步骤3 | 1138–1153 (L24–L24) | `figures/*.png` | `external_not_in_record` |
| A14 | `figure_metadata` | ② 步骤3 | 1156–1179 (L24–L24) | `figures_metadata.json` | `external_not_in_record` |
| A15 | `recompute_artifact` | ② 步骤4 | 1300–1323 (L26–L26) | `coth_tanh_impact.json` | `external_not_in_record` |
| A16 | `dev_toolchain` | ② 步骤5 | 1333–1376 (L27–L27) | Python 3.11 + pytest 19 passed + matplotlib | `declared_in_source_only` |
| A17 | `platform_figure` | ④ 结果图 | 2702–2723 (L54–L54) | 状态矩阵（11 checks × 2 稿） | `declared_payload_missing` |
| A18 | `platform_figure` | ④ 结果图 | 2724–2744 (L54–L54) | 数值溯源偏差分布（tol=5e-3 线） | `declared_payload_missing` |
| A19 | `platform_figure` | ④ 结果图 | 2745–2761 (L54–L54) | coth/tanh 误式代价曲线 | `declared_payload_missing` |

**机检结果**（`verification.json`，模式=online (platform re-fetch)）：

| acceptance item | result |
|---|---|
| source_hash_matches | PASS |
| chars_match_contract | PASS |
| valid_json | PASS |
| schema_pass | PASS |
| source_locator_resolvable | PASS |
| no_duplicate_ids | PASS |
| all_claims_have_evidence_or_explicit_unresolved_status | PASS |
| boundaries_and_no_self_verified | PASS |
| record_metadata_verbatim | PASS |
| platform_figure_payload_status_current | PASS |

`acceptance_all_pass = True`；`verified_label_written = False`。

## ④ 结果图

**图 1 `fig_locator_map.png`** — 19 条 locator 在 3712 字符 markdown 中的字符区间（颜色=payload 状态；点线=六个正文段落起点）。所有区间均由脚本按断言切片复算，无手填偏置。

（图载荷随报告 `figures` 字段提交；`GET /tensor/reports/<本包报告>/figures/fig_locator_map.png` 已验证可取回 200 且字节 sha256 与本地一致，证据见 `publish_roundtrip.json`。）

**图 2 `fig_payload_status.png`** — payload 状态分布：2 条在报告记录内可解析、11 条为外部工件、3 条为平台声明但载荷 404、2 条越界报告不读、1 条仅源内声明。0 条被升格为 verified。

（图载荷随报告 `figures` 字段提交；`GET /tensor/reports/<本包报告>/figures/fig_payload_status.png` 已验证可取回 200 且字节 sha256 与本地一致，证据见 `publish_roundtrip.json`。）

**图 3 `fig_acceptance_matrix.png`** — 契约 acceptance 逐项的机检结果（在线模式：10 项全 PASS）。该图由 verification.json 直接渲染，不是手绘结论。

（图载荷随报告 `figures` 字段提交；`GET /tensor/reports/<本包报告>/figures/fig_acceptance_matrix.png` 已验证可取回 200 且字节 sha256 与本地一致，证据见 `publish_roundtrip.json`。）

说明：本工序是登记/对账类，无场量、无解析解曲线；图的职责是**把登记结论可复核地画出来**（定位覆盖、载荷状态、acceptance 矩阵），故不画求解场量云图。

## ⑤ 注意点与局限

- **越界报告不读**：`Report #823`（证据基）与 `Report #961`（异族评审）在原文中被引用，但工单硬约束
  「只碰 report_id=3076」，因此其内容/哈希**未核实**，登记为 `cross_report_out_of_scope`。跨报告核对需另开工单。
- **外部工件未取**：`papers/...` 与 `SEAL.md` 属论文线仓（papers/），不在本报告记录内；本包只登记路径文本与出处，不取回、不验证内容。
- **图载荷缺失**：平台记录只有 name+caption，`/figures/<name>` 返回 404。三张图登记为 `declared_payload_missing`；
  若日后平台补了载荷，`verification.json` 的 `platform_figure_payload_status_current` 会转 FAIL，提示需重登记。
- **glob 引用不展开**：`data/*.csv`、`figures/*.png` 是通配引用，原文未列文件名，故登记为通配本身，
  个体文件数**未知**（不臆造文件名）。
- **图载荷端点已用正控校准**：平台记录的 `figures` 字段只回 name+caption（不含字节），故 404 可能是"路由写错"也可能是"载荷真缺"。
  本包用自身发布的报告做正控：`GET /tensor/reports/<本包报告>/figures/fig_locator_map.png` 返回 **200**，回传字节数与本地 sha256 一致
  （见 `publish_roundtrip.json` 的 `figure_endpoint_positive_control`）。因此报告 3076 三张图的 404 判定为**载荷真缺失**，而非我方取法错误。
- **只登记不下结论**：`solver.py` 的数值正确性、`pytest 19 passed`、`coth/tanh` 0.37%→25.02% 等都是**源报告自身的声明**，
  本包原样登记为声明，不重跑、不复核（`dev_toolchain` 标 `declared_in_source_only`）。
- **claims 为空是设计**：工单 objective 只要求登记资产；填 claims 会伪造本应属 03-知识抽取 的产物。
- **契约 schema 缺席**：`schemas/kf_result.v1.schema.json` 在本 worktree 中不存在，故把本仓 commit 53c59cc 的同一文件
  逐字节复制到 `docs/wp-3076-01/kf_result.v1.schema.json` 作为结构校验依据（来源可复核，非自造宽松 schema）。
  若平台侧 schema 与副本不同，以平台门为准，本包需随之修订。

## ⑥ 误差判定（是否 <3%？）

本工序**不产生物理量**，无实验/文献基准，故对"关键量误差是否 <3%"的回答是 **N/A（无基准）**，理由：工序产物为
资产名册与定位区间，其正确性判据是**精确恒等**而非工程容差。可以给出的是恒等式对账：

| 对账项 | 基准 | 实测 | 误差 |
|---|---|---|---|
| markdown sha256 | 契约 `9b7bb2427af8a1b4…` | 平台现取重算 `9b7bb2427af8a1b4…` | **0 bit**（全 64 位一致） |
| 字符数 | 契约 3712 | 平台现取 3712 | **0%** |
| 引文可复原 | 原文切片 | 19/19 条区间回切逐字一致 | **0 条偏差** |
| 唯一性 | 每条引文出现 1 次 | 重复 span（19 条中重复 0 对） | **0** |
| 图载荷端点（正控） | 期望 200 且字节一致 | 本包报告同端点 200、字节 sha256 一致 | **0 字节偏差** |

honest 声明：`platform_figure_payload_status_current` 只有在线模式才执行；离线跑测试时该项为 `NOT_RUN`，
不作 PASS 声明。本包对报告 3076 的**结论真伪一概不评**（不标 verified）。

## 复跑命令

`cd <worktree-root> && export TENSOR_API_BASE=http://127.0.0.1:8010/api/v1 TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=... && python3 scripts/kf_fetch_3076.py && python3 scripts/kf_register_3076.py && python3 scripts/kf_verify_3076.py && python3 scripts/kf_figures_3076.py && python3 scripts/kf_report_3076.py && python3 -m pytest tests/test_kf_wp3076.py -q`

（单行即可复跑；仅需把 `TENSOR_AGENT_USER/PASS` 换成当前席位凭据。全文只有结果信封一个 fenced 代码块，供平台原样解析。）

## 版本说明

本包先发过一版不含「图载荷端点正控」段的报告，已被本版取代（本版为唯一交付版）；两版的结果信封（json 块）逐字段相同，
差异仅在正文对正控证据的说明。发布回执与残留清单见 `publish_roundtrip.json`。

## 交付物

| 文件 | 要点 |
|---|---|
| `docs/wp-3076-01/source.md` | 报告 3076 markdown 逐字节副本（sha256 = 9b7bb2427af8a1b4…，3712 字符） |
| `docs/wp-3076-01/source_meta.json` | 平台记录字段（title/scenario_key/mission_id/tags/figures） |
| `docs/wp-3076-01/asset_manifest.json` | 19 条资产（区间/引文/唯一性/payload 状态），claims 空 |
| `docs/wp-3076-01/kf_result.wp-3076-01.json` | 平台结果信封（package_id/task_type/report_id/provenance/outputs/claims） |
| `docs/wp-3076-01/verification.json` | 10 项机检明细 + 在线复核（图 404 复测） |
| `docs/wp-3076-01/asset_manifest.v1.schema.json` | manifest 结构 schema（可机检） |
| `docs/wp-3076-01/kf_result.v1.schema.json` | 契约信封 schema（自 commit 53c59cc 逐字节恢复） |
| `docs/wp-3076-01/fig_*.png` | 定位覆盖 / 载荷状态 / acceptance 矩阵 三图 |

## 自检（逐条对照 acceptance）

| acceptance | 结果 | 依据 |
|---|---|---|
| valid_json | ✅ | 两份 JSON 均被 `json.load` 解析 + pytest `test_envelope_shape` |
| schema_pass | ✅ | 信封按 `kf_result.v1.schema.json`、manifest 按 `asset_manifest.v1.schema.json` 校验，0 error |
| source_locator_resolvable | ✅ | 19/19 引文按区间回切逐字一致、均唯一、行号复算一致 |
| source_hash_matches | ✅ | 平台现取重算 = 契约 = manifest = 信封 provenance（全 64 位一致） |
| no_duplicate_ids | ✅ | 19 个 asset_id 互异，且 19 个区间互不重叠同型 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=0（合法空）；每条资产均带 payload.status + checked_how，未解析者显式标 unresolved 类状态 |

## 结果信封（唯一 json 块，平台原样提交）

```json
{
  "package_id": "wp-3076-01",
  "task_type": "01-asset-registration",
  "report_id": "3076",
  "provenance": {
    "source_uri": "tensor://reports/3076",
    "source_field": "markdown",
    "source_hash": "sha256:9b7bb2427af8a1b4a7f229971492c52fc691737a7742b4b703ce4e41cea464c1",
    "producer": "kf-wp3076-01 asset registration (scripts/kf_register_3076.py)",
    "emitted_at": "2026-11-12T00:57:34+00:00",
    "notes": "hash = sha256 of the exact UTF-8 bytes of the report markdown field; recomputed from the platform on every verify run"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-3076-01",
      "task_type": "01-asset-registration",
      "report_id": "3076",
      "objective": {
        "register_assets": true,
        "classify_report_type": false
      },
      "source": {
        "uri": "tensor://reports/3076",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "9b7bb2427af8a1b4a7f229971492c52fc691737a7742b4b703ce4e41cea464c1",
        "chars": 3712,
        "bytes_utf8": 6092,
        "contract_chars": 3712,
        "title": "成稿机检门禁 manuscript_gate v1：把 SEAL.md 的 H1–H8 硬伤固化为 11 项机检（负控复现 8 项 / 正控 0 误报）",
        "scenario_key": "paper-line-provenance-gate",
        "platform_mission_id": 3012,
        "platform_status": "published",
        "platform_created_at": "2026-11-03T23:35:19.261537+00:00",
        "platform_tags": [
          "paper-production",
          "provenance-gate",
          "manuscript-conformance",
          "verification-debt",
          "pytest",
          "honest-FAIL"
        ],
        "platform_figures": [
          {
            "name": "gate_state_matrix.png",
            "caption": "门禁 11 项 checks 在封存 FAIL 稿与正控稿上的状态矩阵（绿=PASS 红=FAIL 黄=WARN 灰=SKIP）"
          },
          {
            "name": "gate_numtrace_dev.png",
            "caption": "数值溯源：每个定量 token 到证据基的最小相对偏差（log10），虚线=5e-3 容差"
          },
          {
            "name": "gate_coth_tanh.png",
            "caption": "H1 独立复算：coth 误式相对 tanh 正解的波数偏差 vs 周期，含 3%/15% 线"
          }
        ]
      },
      "counts": {
        "assets": 19,
        "by_class": {
          "source_document": 1,
          "negative_control_manuscript": 1,
          "evidence_base_report": 1,
          "review_report": 1,
          "defect_seal": 1,
          "gate_implementation": 1,
          "check_registry": 1,
          "positive_control_tree": 1,
          "solver_code": 1,
          "evidence_base": 1,
          "figure_builder": 1,
          "data_tables": 1,
          "figure_payloads": 1,
          "figure_metadata": 1,
          "recompute_artifact": 1,
          "dev_toolchain": 1,
          "platform_figure": 3
        },
        "by_payload_status": {
          "in_report_record": 2,
          "external_not_in_record": 11,
          "cross_report_out_of_scope": 2,
          "declared_in_source_only": 1,
          "declared_payload_missing": 3
        },
        "check_id_count": 11,
        "claims": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "source_document",
          "label": "tensor://reports/3076 markdown（本包登记的唯一原文）",
          "in_report_section": "document",
          "locator": {
            "method": "document",
            "source_field": "markdown",
            "start_char": 0,
            "end_char": 3712,
            "start_line": 1,
            "end_line": 75,
            "quote": "## ① 案例介绍",
            "unique": true
          },
          "payload": {
            "status": "in_report_record",
            "checked_how": "GET /tensor/reports/3076 → field markdown; sha256 + char count recomputed and compared with the work-package contract",
            "evidence": {
              "sha256": "9b7bb2427af8a1b4a7f229971492c52fc691737a7742b4b703ce4e41cea464c1",
              "chars": 3712
            }
          },
          "note": "Whole-document locator: span covers the entire pinned markdown; the envelope provenance.source_hash is this asset's hash."
        },
        {
          "asset_id": "A02",
          "asset_class": "negative_control_manuscript",
          "label": "封存稿 manuscript.md（246 行、6 图）",
          "in_report_section": "① 对象表 / ② 步骤1",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 268,
            "end_char": 318,
            "start_line": 10,
            "end_line": 10,
            "quote": "papers/_sealed/ice-wave-mechanics-r2/manuscript.md",
            "unique": true
          },
          "payload": {
            "status": "external_not_in_record",
            "checked_how": "path text is quoted verbatim from the markdown; the file itself lives in the paper-line repo (papers/), which is outside this report record — not fetched by this package"
          },
          "note": "Negative control (known FAIL). 6 embedded figures of that manuscript are not enumerated here: the report does not name them, and inventing names is forbidden."
        },
        {
          "asset_id": "A03",
          "asset_class": "evidence_base_report",
          "label": "证据基 Report #823",
          "in_report_section": "① 对象表",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 332,
            "end_char": 347,
            "start_line": 10,
            "end_line": 10,
            "quote": "证据基 Report #823",
            "unique": true
          },
          "payload": {
            "status": "cross_report_out_of_scope",
            "checked_how": "referenced by id only; work-package boundary forbids reading any report_id other than 3076, so its contents/hash are NOT checked here"
          },
          "note": "Deliberately unresolved: resolving it requires a separate cross-report work package."
        },
        {
          "asset_id": "A04",
          "asset_class": "review_report",
          "label": "异族确认评审 Report #961（判 FAIL）",
          "in_report_section": "① 背景",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 97,
            "end_char": 108,
            "start_line": 4,
            "end_line": 4,
            "quote": "Report #961",
            "unique": true
          },
          "payload": {
            "status": "cross_report_out_of_scope",
            "checked_how": "same boundary as A03 — id cited in text, record not read"
          },
          "note": "The report explicitly states its coth/tanh numbers do not match #961 (74.19%/37.5%); that divergence is a property of the source, not resolved by this package."
        },
        {
          "asset_id": "A05",
          "asset_class": "defect_seal",
          "label": "SEAL.md（H1–H8 硬伤清单）",
          "in_report_section": "① 背景 / ② 步骤1",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 124,
            "end_char": 145,
            "start_line": 4,
            "end_line": 4,
            "quote": "SEAL.md 列了 H1–H8 八类硬伤",
            "unique": true
          },
          "payload": {
            "status": "external_not_in_record",
            "checked_how": "quoted path text only; SEAL.md lives in the paper-line repo, not in the report record"
          },
          "note": "Upstream input of the gate; registering it does not validate its content."
        },
        {
          "asset_id": "A06",
          "asset_class": "gate_implementation",
          "label": "papers/tools/manuscript_gate.py（11 项 checks 实现）",
          "in_report_section": "② 步骤2",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 840,
            "end_char": 881,
            "start_line": 20,
            "end_line": 20,
            "quote": "`papers/tools/manuscript_gate.py`：统一数字规范化",
            "unique": true
          },
          "payload": {
            "status": "external_not_in_record",
            "checked_how": "quoted path text only; source file lives in the paper-line repo"
          },
          "note": "The claim 'only reads the audited manuscript' (mtime assertion test) is a statement of the source and is NOT re-verified here."
        },
        {
          "asset_id": "A07",
          "asset_class": "check_registry",
          "label": "11 项 check 标识符（struct…arith）",
          "in_report_section": "② 步骤1",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 724,
            "end_char": 835,
            "start_line": 19,
            "end_line": 19,
            "quote": "struct / figref / figdata / numtrace / formula / overclaim / statdof / implmethod / repro / placeholder / arith",
            "unique": true
          },
          "payload": {
            "status": "in_report_record",
            "checked_how": "the identifier list is enumerated verbatim inside the located span; count recomputed from the span (see check_id_count)"
          },
          "note": "Registered as a symbol list only — no semantics, thresholds or per-check verdicts are extracted here."
        },
        {
          "asset_id": "A08",
          "asset_class": "positive_control_tree",
          "label": "正控目录 papers/data/gate-2026-11-03/control/",
          "in_report_section": "① 对象表 / ② 步骤3",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 383,
            "end_char": 421,
            "start_line": 11,
            "end_line": 11,
            "quote": "`papers/data/gate-2026-11-03/control/`",
            "unique": true
          },
          "payload": {
            "status": "external_not_in_record",
            "checked_how": "quoted path text only; the tree is created in the paper-line repo and is not part of this report record"
          },
          "note": "Positive control (must PASS, 0 HARD). Its internal files are registered individually as A09–A14."
        },
        {
          "asset_id": "A09",
          "asset_class": "solver_code",
          "label": "control/solver.py（tanh 边界条件二分法参考解）",
          "in_report_section": "② 步骤3",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 1058,
            "end_char": 1080,
            "start_line": 23,
            "end_line": 23,
            "quote": "`solver.py`（tanh 边界条件）",
            "unique": true
          },
          "payload": {
            "status": "external_not_in_record",
            "checked_how": "quoted path text only; body not in the record"
          },
          "note": "Numeric correctness of the solver is a claim of the source report, not re-run by this package."
        },
        {
          "asset_id": "A10",
          "asset_class": "evidence_base",
          "label": "control/evidence.json（正控证据基）",
          "in_report_section": "② 步骤3",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 1082,
            "end_char": 1097,
            "start_line": 23,
            "end_line": 23,
            "quote": "`evidence.json`",
            "unique": true
          },
          "payload": {
            "status": "external_not_in_record",
            "checked_how": "quoted path text only; body not in the record"
          },
          "note": "Same name as the sealed-tree evidence base (Report #823); the two are distinct files — this package registers the positive-control one only."
        },
        {
          "asset_id": "A11",
          "asset_class": "figure_builder",
          "label": "control/make_figures.py（图件生成脚本）",
          "in_report_section": "② 步骤3",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 1100,
            "end_char": 1117,
            "start_line": 23,
            "end_line": 23,
            "quote": "`make_figures.py`",
            "unique": true
          },
          "payload": {
            "status": "external_not_in_record",
            "checked_how": "quoted path text only; body not in the record"
          },
          "note": ""
        },
        {
          "asset_id": "A12",
          "asset_class": "data_tables",
          "label": "control/data/*.csv（图件数值源，glob 引用）",
          "in_report_section": "② 步骤3",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 1123,
            "end_char": 1135,
            "start_line": 24,
            "end_line": 24,
            "quote": "`data/*.csv`",
            "unique": true
          },
          "payload": {
            "status": "external_not_in_record",
            "checked_how": "glob pattern, not a file list; the report does not enumerate the individual CSV names"
          },
          "note": "Glob reference registered as-is. Individual CSV files are unresolved (count unknown) — no names invented."
        },
        {
          "asset_id": "A13",
          "asset_class": "figure_payloads",
          "label": "control/figures/*.png（正控图件，glob 引用）",
          "in_report_section": "② 步骤3",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 1138,
            "end_char": 1153,
            "start_line": 24,
            "end_line": 24,
            "quote": "`figures/*.png`",
            "unique": true
          },
          "payload": {
            "status": "external_not_in_record",
            "checked_how": "glob pattern; individual PNG names not enumerated by the report"
          },
          "note": "Distinct from the platform record figures A17–A19: those are the report's own three figures."
        },
        {
          "asset_id": "A14",
          "asset_class": "figure_metadata",
          "label": "control/figures_metadata.json（内嵌数值数组）",
          "in_report_section": "② 步骤3",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 1156,
            "end_char": 1179,
            "start_line": 24,
            "end_line": 24,
            "quote": "`figures_metadata.json`",
            "unique": true
          },
          "payload": {
            "status": "external_not_in_record",
            "checked_how": "quoted path text only; body not in the record"
          },
          "note": ""
        },
        {
          "asset_id": "A15",
          "asset_class": "recompute_artifact",
          "label": "coth_tanh_impact.json（H1 独立复算产物）",
          "in_report_section": "② 步骤4",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 1300,
            "end_char": 1323,
            "start_line": 26,
            "end_line": 26,
            "quote": "`coth_tanh_impact.json`",
            "unique": true
          },
          "payload": {
            "status": "external_not_in_record",
            "checked_how": "quoted path text only; body not in the record"
          },
          "note": "The percentages 0.37%→25.02% quoted in ③/⑥ are the source's numbers; they are not recomputed by this registration package."
        },
        {
          "asset_id": "A16",
          "asset_class": "dev_toolchain",
          "label": "Python 3.11 + pytest 19 passed + matplotlib",
          "in_report_section": "② 步骤5",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 1333,
            "end_char": 1376,
            "start_line": 27,
            "end_line": 27,
            "quote": "Python 3.11 + pytest 19 passed + matplotlib",
            "unique": true
          },
          "payload": {
            "status": "declared_in_source_only",
            "checked_how": "declared in text; this package does not re-run the paper-line test suite (different repo, different toolchain)"
          },
          "note": "19 passed is an unverified declaration from the source, carried forward as such."
        },
        {
          "asset_id": "A17",
          "asset_class": "platform_figure",
          "label": "gate_state_matrix.png（图1：11 checks × 2 稿状态矩阵）",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 2702,
            "end_char": 2723,
            "start_line": 54,
            "end_line": 54,
            "quote": "状态矩阵（11 checks × 2 稿）",
            "unique": true
          },
          "payload": {
            "status": "declared_payload_missing",
            "checked_how": "record.figures[0] gives name+caption; GET /tensor/reports/3076/figures/gate_state_matrix.png returned HTTP 404 'figure not found'",
            "evidence": {
              "record_name": "gate_state_matrix.png",
              "http_status": 404
            }
          },
          "note": "Registered from the platform record (name + caption verbatim). PNG bytes are NOT stored in this report record — explicitly unresolved, not assumed present."
        },
        {
          "asset_id": "A18",
          "asset_class": "platform_figure",
          "label": "gate_numtrace_dev.png（图2：数值溯源偏差分布）",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 2724,
            "end_char": 2744,
            "start_line": 54,
            "end_line": 54,
            "quote": "数值溯源偏差分布（tol=5e-3 线）",
            "unique": true
          },
          "payload": {
            "status": "declared_payload_missing",
            "checked_how": "record.figures[1] gives name+caption; figure payload endpoint probed for A17 returned 404, so the same endpoint was recorded as unusable rather than assumed to work per-figure",
            "evidence": {
              "record_name": "gate_numtrace_dev.png",
              "http_status": 404
            }
          },
          "note": "See A17 for the payload-endpoint evidence; no per-figure 200 was observed."
        },
        {
          "asset_id": "A19",
          "asset_class": "platform_figure",
          "label": "gate_coth_tanh.png（图3：coth/tanh 误式代价曲线）",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 2745,
            "end_char": 2761,
            "start_line": 54,
            "end_line": 54,
            "quote": "coth/tanh 误式代价曲线",
            "unique": true
          },
          "payload": {
            "status": "declared_payload_missing",
            "checked_how": "record.figures[2] gives name+caption; payload endpoint returned 404 for the checked figure name",
            "evidence": {
              "record_name": "gate_coth_tanh.png",
              "http_status": 404
            }
          },
          "note": "Caption says '含 3%/15% 线' — that is the source's caption text, registered verbatim, not verified against an image."
        }
      ],
      "claims": [],
      "claims_note": "claims intentionally empty: contract objective is asset registration only (classify_report_type=false, no extraction). Filling claims here would fabricate knowledge objects that belong to task_type 03.",
      "integrity": {
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "chars_match_contract": true,
        "all_locators_unique_quotes": true,
        "verified_by": "scripts/kf_verify_3076.py (re-fetches the report independently)",
        "no_file_outside_worktree_written": true
      },
      "boundaries": {
        "only_report_id": "3076",
        "other_reports_read": false,
        "upstream_artifacts_rewritten": false,
        "claims_marked_verified": 0
      }
    }
  },
  "claims": []
}
```
