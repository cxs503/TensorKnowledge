# KF-RESULT wp-14179-01

**tags**: kf-wp:wp-14179-01, 01-asset-registration, report:14179, lane:B, TensorKnowledge, draft
**package_id**: wp-14179-01 ｜ **task_type**: 01-asset-registration ｜ **report_id**: 14179
**lane**: B ｜ **repo**: TensorKnowledge ｜ **source_uri**: `tensor://reports/14179`
**source_hash**: `sha256:2352b96c50e792447e06d9d7450f16f0b34ba7ce2cbf1bf775c3402dcee59315`（本地重算 == 契约声明）｜ **chars**: 5506（UTF-8 8406 B）

---

## ① 本工序做了什么

本工作包只做 `report_id=14179`（《交差审计 m14897 H5-CALIB-REFLUX：三件套重跑通过、A_hat 0.075539(+0.72%)/RT +0.384% → verdict L5》，scenario_key=`calib_reflux_audit`）的
**资产登记**（工序 `01-asset-registration`），不做抽取、不做类型分类、不生成 claim、不标 verified：

1. **源资产身份钉死**：独立重算 `markdown` 字段的 sha256 = `2352b96c50e792447e06d9d7450f16f0b34ba7ce2cbf1bf775c3402dcee59315`，与契约 `source_hash`
   逐字节一致；`chars=5506`（python str 长度，与契约 `chars` 相同），UTF-8 字节 `8406`
   （CJK 正文两者必然不同，口径写死）。记录 title/scenario_key 与契约逐字一致。
2. **附件登记**：记录 `figures[]` 的 2 条 png 元数据（fig1_hifi_vs_reference.png、fig2_prediction_before_after.png），
   与正文 ④ 节逐字路径互相绑定（`resolution_check=record_figures_name_lookup`）。
3. **工件/代码/台账引用登记**：正文声明的代码指针、工件目录、单测、账本哈希、外部 worktree 路径共
   10 项，全部如实登记为 `referenced_unresolved`（本工作树内不存在）。
4. **正文块结构登记**：2 个 pipe 表只登记结构（表头列数/数据行数/起始行），
   **不把任何数值抽到知识对象**。
5. 合计登记资产 **27** 项：referenced_unresolved=10 ｜ resolved_in_source=17；类别分布 code_pointer=3、numeric_anchor=2、table=2、figure=2、statement=2、document=1、heading=1、vcs_reference=1、geometry_declaration=1、artifact_set=1、measurement_record=1、command=1、test_suite=1、gate_check=1、dataset_stats=1、parameter_set=1、ledger_record=1、limitation_set=1、verdict=1、deliverable_set=1、external_worktree=1。

边界遵守：只读 `GET /api/v1/tensor/reports/14179` 这一份记录，未读写任何其它 report_id；
未改写上游或其它工作包的产物；**没有任何结论被标成 verified**——verification 由平台门计算。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **契约入参**：`package_id=wp-14179-01`、`report_id=14179`、`source_field=markdown`、
   `source_hash=sha256:2352b96c50e792447e06d9d7450f16f0b34ba7ce2cbf1bf775c3402dcee59315`、`chars=5506`、`scenario_key=calib_reflux_audit`；
   六条 `acceptance` 直接落成机器检查（见 ⑥），不是人工打勾。
2. **取源**：`POST /auth/login`（凭据只从环境变量 `TENSOR_AGENT_USER`/`TENSOR_AGENT_PASS` 读取，
   不落盘、不进仓库）→ `GET /api/v1/tensor/reports/14179`（Bearer），取 `markdown` 原文；
   同记录 `title/scenario_key/mission_id/status/created_at/tags/figures` 一并登记。
3. **独立哈希**：`hashlib.sha256(markdown.encode('utf-8'))`，与契约逐字比较，不一致即 `SystemExit`
   （失败不出产物）。校验脚本另起一次网络取源重算，不复用登记脚本的内存副本。
4. **零手抄定位**：脚本内锚点表逐条要求锚字符串在原文**恰好出现一次**（命中 0 次或 >1 次立即失败），
   再由相对行偏移切出引文；每条资产登记 `start_char/end_char/start_line/end_line/quote/occurrences`。
   校验脚本反向复算 `md[start_char:end_char] == quote` 且 `md.count(quote) == 1`，并核对行偏移与字符偏移自洽。
5. **解析状态机器判定**：`resolution_check` 不是文字描述，而是可复算探针：
   `quote_is_unique_substring_of_markdown` / `record_figures_name_lookup` / `worktree_relative_path_exists`
   / `git_cat_file_in_this_worktree` / `host_absolute_path_probe_informational`。
6. **工具链**：Python 3 标准库（urllib/hashlib/json）+ `jsonschema`（envelope 按 `schemas/kf_result.v1.schema.json`
   draft 2020-12 校验，manifest 按本单 pinned schema draft-07 校验）+ matplotlib（覆盖率图）。
7. **可复跑**：见文末 `repro_cmd`；校验脚本在报告正文生成后再跑一遍，确认正文里的 json 围栏块与本单
   `kf_result.json` 完全相同。

## ③ 产出物清单

| 产物路径 | 要点 |
|---|---|
| `artifacts/wp-14179-01/asset_manifest.json` | 契约声明输出；27 项资产 + 源身份 + counts + boundary |
| `docs/kf/wp-14179-01/asset_manifest.json` | 同一份字节镜像（push gate 丢弃 artifacts/**，durable 副本落 docs/） |
| `docs/kf/wp-14179-01/kf_result.json` | 结果信封（kf_result.v1：package_id/task_type/report_id/provenance/outputs） |
| `docs/kf/wp-14179-01/locator_check.json` | 逐资产字符/行偏移与唯一性检查原始表 |
| `docs/kf/wp-14179-01/verification.json` | 独立校验的完整 check 列表（本报告 ⑥ 的唯一数据源） |
| `docs/kf/wp-14179-01/source.md` + `sha256.txt` | 取源快照与哈希台账（便于离机复核） |
| `docs/kf/wp-14179-01/figure1_asset_coverage.png` | 图1：27 项资产在原文 0–5506 字符轴上的定位覆盖率图 |
| `docs/kf/wp-14179-01/report_body.md` | 本报告正文（含唯一 json 围栏结果块） |
| `scripts/kf_wp14179_01_register.py` / `_verify.py` / `_report.py` | 登记 / 独立校验 / 渲染发布三件套 |

## ④ 证据定位表（claim/字段 → 原文逐字引文）

下表每行的引文都是**机器切出的原文子串**（完整引文见 `asset_manifest.json` 的 `locator.quote`）：

| 资产 | 类别 | 所在节 | 解析状态 | 定位 | 原文引文（逐字，截断） |
|---|---|---|---|---|---|
| A01 | `document` | # 交差审计：m14897 H5-CALIB-RE… | resolved_in_source | 全文 chars 0-5506 | `# 交差审计：m14897 H5-CALIB-REFLUX（ship-performance-platform）→ verdict **L…` |
| A02 | `heading` | # 交差审计：m14897 H5-CALIB-RE… | resolved_in_source | chars 0-72 / L1-1 | `# 交差审计：m14897 H5-CALIB-REFLUX（ship-performance-platform）→ verdict **L…` |
| A03 | `vcs_reference` | ## ① 案例介绍（审计对象与物理背景） | referenced_unresolved | chars 95-235 / L4-6 | ` ⏎ 对象 = mission **m14897**（status `succeeded`，commit `2eb994ce1`，PR *…` |
| A04 | `code_pointer` | ## ① 案例介绍（审计对象与物理背景） | referenced_unresolved | chars 237-358 / L8-9 | `物理问题：平台已有真数值高保真能力（TensorLBM 平板边界层），而 Holtrop 主链的 ⏎ 摩擦线常量 `ITTC57_A = …` |
| A05 | `numeric_anchor` | ## ① 案例介绍（审计对象与物理背景） | resolved_in_source | chars 608-727 / L17-18 | `**被标定系数**：`ITTC57_A = 0.075`（无量纲）。**消费点**：`mennen.py:ittc57_cf`， ⏎ 经 …` |
| A06 | `code_pointer` | ## ① 案例介绍（审计对象与物理背景） | referenced_unresolved | chars 419-606 / L13-15 | `**高保真源**：TensorLBM `wall_model_les.flat_plate.run_flat_plate` —— 零压梯度…` |
| A07 | `geometry_declaration` | ## ① 案例介绍（审计对象与物理背景） | resolved_in_source | chars 729-851 / L20-21 | `**验证船型**：KCS（KRISO 集装箱船），几何先过门：Cb_lib=0.6509 vs ⏎ nabla/(L·B·T)=0.650…` |
| A08 | `artifact_set` | ## ② 怎么做的（取证三件套复核，全部重跑，不信… | referenced_unresolved | chars 883-1195 / L25-28 | `1. **run_artifacts 复核**：`artifacts/m14897_calib_reflux/` 9 个工件（01_hif…` |
| A09 | `measurement_record` | ## ② 怎么做的（取证三件套复核，全部重跑，不信… | resolved_in_source | chars 1196-1435 / L29-32 | `2. **benchmark ref vs got 复核**：重跑 `python scripts/run_calib_reflux.py…` |
| A10 | `command` | ## ② 怎么做的（取证三件套复核，全部重跑，不信… | referenced_unresolved | chars 1436-1572 / L33-34 | `3. **repro_cmd 可执行**：`python scripts/run_calib_reflux.py run`（22s，PAS…` |
| A11 | `test_suite` | ## ② 怎么做的（取证三件套复核，全部重跑，不信… | referenced_unresolved | chars 1573-1690 / L35-36 | `4. **单测重跑**：`backend/tests/test_calib_reflux.py` → **17 passed**（31.6…` |
| A12 | `gate_check` | ## ② 怎么做的（取证三件套复核，全部重跑，不信… | referenced_unresolved | chars 1691-1778 / L37-38 | `5. **判级+网关自检**：按 L0–L5 功能实质判级，`maturity_gate.judge` 本地模拟复核 ⏎    （clai…` |
| A13 | `dataset_stats` | ## ③ 计算结果（程序化注入，零手抄） | resolved_in_source | chars 1802-1870 / L42-42 | `**S1 高保真证据**：站点数 238，Re_x ∈ [2.020e+07, 2.020e+08]，RANS-grade 积分边界层。` |
| A14 | `parameter_set` | ## ③ 计算结果（程序化注入，零手抄） | resolved_in_source | chars 1872-2064 / L44-46 | `**S2 标定**：A_hat=**0.075539**（ΔA/A=+0.72%），σ_A=7.239e-05（0.097%）， ⏎ 残差…` |
| A15 | `ledger_record` | ## ③ 计算结果（程序化注入，零手抄） | resolved_in_source | chars 2066-2165 / L48-49 | `**S3 回写**：账本 seq=0，entry_sha256=`6fc45dd1…`，生效快照 head_sha256=`3eeab05…` |
| A16 | `table` | ## ③ 计算结果（程序化注入，零手抄） | resolved_in_source | chars 2167-2990 / L51-62 | `**S4 回流前后对照**（KCS，同一 Holtrop 主链，仅摩擦线常量不同）： ⏎  ⏎ \| Fn \| V [kn] \| Cf be…` |
| A17 | `numeric_anchor` | ## ③ 计算结果（程序化注入，零手抄） | resolved_in_source | chars 2992-3127 / L64-65 | `**设计点（Fn=0.260, 24.00 kn）**：RT 2109.49 → 2117.58 kN（**+0.38%**）， ⏎ Pe…` |
| A18 | `figure` | ## ④ 结果图 | resolved_in_source | chars 3139-3261 / L69-70 | ``artifacts/m15056_audit_m14897/figures/fig1_hifi_vs_reference.png` ——…` |
| A19 | `figure` | ## ④ 结果图 | resolved_in_source | chars 3263-3361 / L72-73 | ``artifacts/m15056_audit_m14897/figures/fig2_prediction_before_after.p…` |
| A20 | `limitation_set` | ## ⑤ 注意点（坑 / 局限 / 适用范围） | resolved_in_source | chars 3388-4188 / L77-91 | `1. **局部量 vs 平均量**：ITTC-57 是**平均**摩阻线，平板求解器给**局部** c_f；直接相比 ⏎    会凭空造出…` |
| A21 | `table` | ## ⑥ 误差判定（逐项 vs 基准，显式回答是否… | resolved_in_source | chars 4222-4567 / L95-101 | `\| 量 \| 基准 \| 本次 \| 误差 \| <3%? \| ⏎ \|---\|---\|---\|---\|---\| ⏎ \| 高保真局部 c_f（带内均…` |
| A22 | `statement` | ## ⑥ 误差判定（逐项 vs 基准，显式回答是否… | resolved_in_source | chars 4569-4757 / L103-106 | `**结论**：高保真数值解与 ITTC-57 在带内平均偏差 +0.98%，即这条经验线在当前可达 Re ⏎ 区间已被高保真证实到 **1…` |
| A23 | `statement` | ## 判级（L0–L5 功能实质） | resolved_in_source | chars 4778-5284 / L110-118 | `- **L0 文档**：远超（有完整报告+工件）。 ⏎ - **L1 数学/单元验证**：✅ `calibrate.py` 过原点 LSQ…` |
| A24 | `verdict` | ## 判级（L0–L5 功能实质） | resolved_in_source | chars 5286-5364 / L120-121 | `**verdict = L5**（完整、集成、可复现的科研工程机制；诚实注记：高保真源为 RANS 级、 ⏎ 修正幅度小，科研价值在机制完…` |
| A25 | `deliverable_set` | ## 判级（L0–L5 功能实质） | referenced_unresolved | chars 5366-5505 / L123-125 | `**工件**：`docs/m15056_audit_m14897.md`（本审计报告）、 ⏎ `artifacts/m15056_audi…` |
| A26 | `external_worktree` | ## ⑤ 注意点（坑 / 局限 / 适用范围） | referenced_unresolved | chars 3981-4188 / L89-91 | `6. **审计侧记账**：m14897 代码在 `/root/tp-agent/work/m14897`（独立 worktree）， ⏎ …` |
| A27 | `code_pointer` | ## ② 怎么做的（取证三件套复核，全部重跑，不信… | referenced_unresolved | chars 1436-1514 / L33-33 | `3. **repro_cmd 可执行**：`python scripts/run_calib_reflux.py run`（22s，PAS…` |

## ⑤ 注意点与局限

1. **只登记、不抽取**：契约 `objective.classify_report_type=false`，`claims` 允许空数组。本单
   `claims=[]` 是合法完整结果，不为了填指标而造知识；`all_claims_have_evidence_or_explicit_unresolved_status`
   因此**空真**成立（校验脚本显式记录该口径，而非静默跳过）。
2. **10 项 `referenced_unresolved` 是真实状态**：报告引用的上游仓（ship-performance-platform / TensorLBM）
   代码、9 件工件、单测文件、`maturity_gate` 实现、三个交付物路径都不在 TensorKnowledge 工作树内；
   本工序**没有**执行 `scripts/run_calib_reflux.py`、**没有**重跑 17 个单测，因此不对其可执行性背书。
   A26 的两个宿主绝对路径在 host 上存在（探针记录在案），但绝对路径不属于 `source_uri` 可解析面，
   换机即不可复现，故仍登记为 unresolved。
3. **图只有元数据**：记录 `figures[]` 只给 name+caption，PNG 本体未下载、未入库；正文路径来自原文逐字引文。
4. **账本哈希是截断展示**（`entry_sha256`/`head_sha256` 尾随 `…`）：登记原文，不补全、不猜测。
5. **本报告不含物理量结论**：本工序是产线登记环节，图1 是资产覆盖率图（不是场量云图）——本单没有
   计算任何流场，按报告纪律声明「无场量图」的理由即为：工序不产生新的物理计算结果，唯一图件用于
   证明登记覆盖与解析状态可机器复算。
6. **本报告所有数字均由脚本从 manifest/verification 注入**，正文无手写数字；上游报告的数字仅以
   「原文引文」形式出现，未被本工序复算或背书。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 机器证据 |
|---|---|---|
| `valid_json` | ✅ PASS | json.loads round-trip OK；json.loads round-trip OK |
| `schema_pass` | ✅ PASS | envelope validates against schemas/kf_result.v1.schema.json (draft 2020-12)；manifest validates against docs/kf/wp-14179-01/asset_manifest.v1.wp-14179-01.schema.json (draft… |
| `source_locator_resolvable` | ✅ PASS | 27/27 locators: md[start:end]==quote, unique, line offsets consistent; failures=[] |
| `source_hash_matches` | ✅ PASS | live sha256=2352b96c50e792447e06d9d7450f16f0b34ba7ce2cbf1bf775c3402dcee59315 | contract=2352b96…；len(markdown)=5506 contract=5506 manifest=5506 |
| `no_duplicate_ids` | ✅ PASS | 27 asset ids, 27 distinct, format ok=True |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✅ PASS | claims=[] in manifest and envelope (contract: classify_report_type=false, no extraction) -> acc… |

补充机器检查（非 acceptance 但支撑可信度）：`nothing_marked_verified`、`boundary_respected`、
`counts_consistent`、`every_asset_has_resolution_check`、`envelope_output_is_the_manifest`、
`no_invented_information`、`mirror_byte_identical`、`report_body_single_json_block_equals_envelope`
——全部见 `verification.json`，`all_passed=True`，阻塞失败项 `[]`。

**honest 声明**：没有任何失败项被粉饰；上面 ❌ 若出现即为真实失败（本次运行无 ❌）。

---

## repro_cmd（一键复跑）

```bash
cd <TensorKnowledge worktree> && \
  python3 scripts/kf_wp14179_01_register.py && \
  python3 scripts/kf_wp14179_01_verify.py && \
  python3 scripts/kf_wp14179_01_report.py
# 依赖：环境变量 TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE；
#       pip install jsonschema matplotlib
```

## 结果信封（唯一 json 围栏块）

```json
{
  "package_id": "wp-14179-01",
  "task_type": "01-asset-registration",
  "report_id": "14179",
  "provenance": {
    "source_uri": "tensor://reports/14179",
    "source_field": "markdown",
    "source_hash": "sha256:2352b96c50e792447e06d9d7450f16f0b34ba7ce2cbf1bf775c3402dcee59315",
    "source_chars": 5506,
    "source_bytes_utf8": 8406,
    "source_title": "交差审计 m14897 H5-CALIB-REFLUX：三件套重跑通过、A_hat 0.075539(+0.72%)/RT +0.384% → verdict L5",
    "title_matches_contract": true,
    "scenario_key": "calib_reflux_audit",
    "scenario_key_matches_contract": true,
    "contract_version": "1.0",
    "lane": "B",
    "producer": "agent/m15783",
    "generator": "scripts/kf_wp14179_01_register.py",
    "verifier": "scripts/kf_wp14179_01_verify.py",
    "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/14179 (Bearer)",
    "notes": "source_hash 由 hashlib.sha256 over UTF-8 bytes of the markdown field 独立重算，与契约 source_hash 逐字节一致；合约 chars=5506 与 len(markdown) 相同。哈希相等仅为机械身份校验，本包不含任何 verified 结论——verification 由平台门计算。",
    "verification_status": "not_verified"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "blocks": {
        "pipe_tables": [
          {
            "name": "S4 回流前后对照表",
            "anchor_asset": "A16",
            "header_cells": 8,
            "data_rows": 8,
            "start_line": 52,
            "registered_as": "structure_only"
          },
          {
            "name": "误差判定表",
            "anchor_asset": "A21",
            "header_cells": 5,
            "data_rows": 5,
            "start_line": 94,
            "registered_as": "structure_only"
          }
        ],
        "fenced_code_blocks_none": true
      },
      "package_id": "wp-14179-01",
      "task_type": "01-asset-registration",
      "contract_version": "1.0",
      "report_id": "14179",
      "lane": "B",
      "generator": "scripts/kf_wp14179_01_register.py",
      "source": {
        "uri": "tensor://reports/14179",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "2352b96c50e792447e06d9d7450f16f0b34ba7ce2cbf1bf775c3402dcee59315",
        "hash_expected": "2352b96c50e792447e06d9d7450f16f0b34ba7ce2cbf1bf775c3402dcee59315",
        "hash_matches_contract": true,
        "chars": 5506,
        "chars_expected": 5506,
        "chars_matches": true,
        "chars_semantics": "契约 chars = python str 长度（码点）；UTF-8 字节数另记（CJK 正文两者不同）",
        "bytes_utf8": 8406,
        "title": "交差审计 m14897 H5-CALIB-REFLUX：三件套重跑通过、A_hat 0.075539(+0.72%)/RT +0.384% → verdict L5",
        "scenario_key": "calib_reflux_audit",
        "platform_id": 14179,
        "platform_mission_id": 15056,
        "platform_status": "published",
        "platform_created_at": "2026-11-11T16:52:08.256269+00:00",
        "platform_tags": [
          "CALIB-REFLUX",
          "高保真回流",
          "交差审计",
          "maturity_gate",
          "ship-performance-platform",
          "证据复核"
        ],
        "platform_figures": [
          "fig1_hifi_vs_reference.png",
          "fig2_prediction_before_after.png"
        ],
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/14179 (Bearer)",
        "local_copy": "runs/wp-14179-01/report_14179.md"
      },
      "counts": {
        "assets": 27,
        "by_class": {
          "document": 1,
          "heading": 1,
          "vcs_reference": 1,
          "code_pointer": 3,
          "numeric_anchor": 2,
          "geometry_declaration": 1,
          "artifact_set": 1,
          "measurement_record": 1,
          "command": 1,
          "test_suite": 1,
          "gate_check": 1,
          "dataset_stats": 1,
          "parameter_set": 1,
          "ledger_record": 1,
          "table": 2,
          "figure": 2,
          "limitation_set": 1,
          "statement": 2,
          "verdict": 1,
          "deliverable_set": 1,
          "external_worktree": 1
        },
        "by_resolution": {
          "resolved_in_source": 17,
          "referenced_unresolved": 10
        },
        "resolved_in_source": 17,
        "referenced_unresolved": 10,
        "declared_absent": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "document",
          "label": "报告 markdown 全文（源资产本体）",
          "in_report_section": "# 交差审计：m14897 H5-CALIB-REFLUX（ship-performance-platform）→ verdict **L5**",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 5506,
            "start_line": 0,
            "end_line": 125,
            "quote": "# 交差审计：m14897 H5-CALIB-REFLUX（ship-performance-platform）→ verdict **L5**\n\n## ① 案例介绍（审计对象与物理背景）\n\n对象 = mission **m14897**（status `succeeded`，commit `2eb994ce1`，PR **#935** merged）：\n「H5-CALIB-REFLUX · 高保真→经验系数回流」。本单 m15056 是**交差核验**（非重做）。\n\n物理问题：平台已有真数值高保真能力（TensorLBM 平板边界层），而 Holtrop 主链的\n摩擦线常量 `ITTC57_A = 0.075`（`backend/physics/holtrop/mennen.py:ittc57_cf`）是\n1957 年拟合的经验相关线。缺的正是**闭环**：高保真结果如何以可审计、可复算、可回滚的\n方式改写这条经验系数。\n\n**高保真源**：TensorLBM `wall_model_les.flat_plate.run_flat_plate` —— 零压梯度平板\n湍流边界层的数值解（Spalding 复合壁律 kappa=0.41/B=5.2 + Coles 尾迹 Pi=0.45，\n动量积分 dθ/dx=c_f/2 推进），每步真数值、无查表（RANS 级积分边界层，非 DNS/LES）。\n\n**被标定系数**：`ITTC57_A = 0.075`（无量纲）。**消费点**：`mennen.py:ittc57_cf`，\n经 `Holtrop1984Input.cf_line_A` 覆盖（缺省 None 保持历史数值逐位不变）。\n\n**验证船型**：KCS（KRISO 集装箱船），几何先过门：Cb_lib=0.6509 vs\nnabla/(L·B·T)=0.650499，偏差 0.062% (<2%)；L/B=7.143，B/T=2.981，nabla=52030 m³。\n\n## ② 怎么做的（取证三件套复核，全部重跑，不信报告）\n\n1. **run_artifacts 复核**：`artifacts/m14897_calib_reflux/` 9 个工件（01_hifi_plate_cf.json /\n   02_calibration.json / 03_writeback.json / 04_prediction_before_after.json+csv /\n   coefficient_store/active.json+ledger.jsonl / figures/fig1+fig2.png / manifest.json /\n   MANIFEST.sha256）全部存在且非空，sha256 逐一复算一致（`verify` 通过）。\n2. **benchmark ref vs got 复核**：重跑 `python scripts/run_calib_reflux.py run` →\n   A_hat=**0.07553932521**（ref 0.075，+0.72%），KCS 设计点 RT **2109.49→2117.58 kN**\n   （+0.384%），传递函数 dRt/dA=**0.533**，负控还原误差 **+0.00000%**（G2=4.44e-14）。\n   与报告数字逐位一致。\n3. **repro_cmd 可执行**：`python scripts/run_calib_reflux.py run`（22s，PASS，5 门全绿）+\n   `verify`（第三方复算，ok=true，父链无孤点、账本 prev 链完整、生效快照与账本末条一致）。\n4. **单测重跑**：`backend/tests/test_calib_reflux.py` → **17 passed**（31.6s），\n   断言不变量（负控还原/夹持边界/篡改必检出/消费者真读账本/同输入哈希逐位一致）。\n5. **判级+网关自检**：按 L0–L5 功能实质判级，`maturity_gate.judge` 本地模拟复核\n   （claimed L5 → 7 键全过，无缺键）。\n\n## ③ 计算结果（程序化注入，零手抄）\n\n**S1 高保真证据**：站点数 238，Re_x ∈ [2.020e+07, 2.020e+08]，RANS-grade 积分边界层。\n\n**S2 标定**：A_hat=**0.075539**（ΔA/A=+0.72%），σ_A=7.239e-05（0.097%），\n残差 RMS=1.456% / max=3.143%，物理带 [0.0700, 0.0800]，clamped=False。\n带敏感性（下界扫描）：1e7→0.075539 / 2e7→0.075539 / 5e7→0.076396，ΔA 漂移 <3%。\n\n**S3 回写**：账本 seq=0，entry_sha256=`6fc45dd1…`，生效快照 head_sha256=`3eeab056…`，\nprev 哈希链完整，可回滚（追加式，不删不盖）。\n\n**S4 回流前后对照**（KCS，同一 Holtrop 主链，仅摩擦线常量不同）：\n\n| Fn | V [kn] | Cf before | Cf after | ΔCf | RT before [kN] | RT after [kN] | ΔRT |\n|---|---|---|---|---|---|---|---|\n| 0.150 | 13.85 | 0.0014697 | 0.0014803 | +0.721% | 486.74 | 489.62 | +0.592% |\n| 0.180 | 16.62 | 0.0014377 | 0.0014480 | +0.716% | 729.57 | 733.63 | +0.556% |\n| 0.200 | 18.46 | 0.0014196 | 0.0014298 | +0.719% | 952.38 | 957.32 | +0.519% |\n| 0.220 | 20.31 | 0.0014036 | 0.0014137 | +0.720% | 1245.72 | 1251.63 | +0.474% |\n| 0.240 | 22.16 | 0.0013892 | 0.0013992 | +0.720% | 1616.99 | 1623.95 | +0.430% |\n| 0.260 | 24.00 | 0.0013761 | 0.0013860 | +0.719% | **2109.49** | **2117.58** | **+0.384%** |\n| 0.280 | 25.85 | 0.0013642 | 0.0013740 | +0.718% | 2799.39 | 2808.70 | +0.333% |\n| 0.300 | 27.70 | 0.0013532 | 0.0013630 | +0.724% | 3522.12 | 3532.72 | +0.301% |\n\n**设计点（Fn=0.260, 24.00 kn）**：RT 2109.49 → 2117.58 kN（**+0.38%**），\nPe 26047.98 → 26147.97 kW（+0.38%）。传递函数 dRt%/dA% = **0.533**（≈摩擦阻力占位比）。\n\n## ④ 结果图\n\n`artifacts/m15056_audit_m14897/figures/fig1_hifi_vs_reference.png` —— 高保真局部摩阻\nvs ITTC-57 局部线与 Prandtl-Schlichting（右=带内偏差）。\n\n`artifacts/m15056_audit_m14897/figures/fig2_prediction_before_after.png` —— 回流前后\nKCS 总阻力曲线与逐点 ΔRT。\n\n## ⑤ 注意点（坑 / 局限 / 适用范围）\n\n1. **局部量 vs 平均量**：ITTC-57 是**平均**摩阻线，平板求解器给**局部** c_f；直接相比\n   会凭空造出 ~2 倍偏差。必须用平均线的微分恒等式 `cf = A(L-2)^-2 [1-2/(ln10(L-2))]`\n   （`ittc57_local_exact`）。\n2. **前缘入口过渡段**：求解器从 Re_theta=1e4 起步，Re_x ≲ 1e7 处尾迹未充分建立；\n   标定带下界取 2e7（敏感性表 1e7/2e7/5e7 三档，ΔA 漂移 <3%）。\n3. **外推**：高保真带覆盖到 Re≈2.0e+08，KCS 26 kn 的 Re≈2.6e9 —— 差 1 个数量级；\n   A 被夹在物理带 ±0.0050 内，越界即 `clamped=True` 登记，不静默吸收。\n4. **证据等级分层**：高保真源是 RANS 级积分边界层（壁律闭包 kappa/B/Pi 取自文献，\n   未在本轮重标定），不是 DNS/LES 解析湍流。它自身与 ITTC-57 局部线平均偏差 +0.98%、\n   与 P-S 最大偏差 6.16%。\n5. **没有采用不可核证的试验表**：仓库里若干「公开模型试验表」只有 `KRISO_tank` 之类\n   标签、无逐项数字化出处（WITHHELD 级），本轮拒绝把它们当高保真锚。\n6. **审计侧记账**：m14897 代码在 `/root/tp-agent/work/m14897`（独立 worktree），\n   ECO 主 checkout 已陈旧（当前 HEAD 不含 calib_reflux）；本单把重跑工件落在\n   `/root/tp-agent/work/m15056/artifacts/m15056_audit_m14897/`，gate 以 m15056 为根可解析。\n\n## ⑥ 误差判定（逐项 vs 基准，显式回答是否 <3%）\n\n| 量 | 基准 | 本次 | 误差 | <3%? |\n|---|---|---|---|---|\n| 高保真局部 c_f（带内均值） | ITTC-57 局部线 | 数值解 | +0.98% (max 2.83%) | 是 |\n| 高保真局部 c_f（带内均值） | Prandtl-Schlichting | 数值解 | -3.50% (max 6.16%) | 否 |\n| 反解 A | 已知真值 0.075（负控合成数据） | A_hat | +0.00000% | 是 |\n| 标定残差 | 拟合线自身 | 高保真站点 | RMS 1.456% | 是 |\n| 回流后 Rt（设计点） | 回流前 Rt | after | +0.384% | 变化量本身 <3%（幅度即结论） |\n\n**结论**：高保真数值解与 ITTC-57 在带内平均偏差 +0.98%，即这条经验线在当前可达 Re\n区间已被高保真证实到 **1% 以内**；回流写回的修正是 +0.72%（ΔRt +0.38%）。这不是\n「标定出大修正」，而是**机制证明 + 一致性的量化**：若未来高保真源（LES/试验）给出\n>3% 的偏差，同一管线会把该偏差以可审计、可回滚的方式写进平台主链。\n\n## 判级（L0–L5 功能实质）\n\n- **L0 文档**：远超（有完整报告+工件）。\n- **L1 数学/单元验证**：✅ `calibrate.py` 过原点 LSQ + 负控 + 物理边界；17 单测断言不变量。\n- **L2 独立功能**：✅ `calib_reflux` 真代码（输入→计算→输出），无 placeholder。\n- **L3 系统集成**：✅ `Holtrop1984Input.cf_line_A` 接入 Holtrop 主链 `mennen.py:ittc57_cf`\n  （line 339 `Cf = ittc57_cf(Re, inp.cf_line_A)`），消费者从账本读系数。\n- **L4 基准验证**：✅ KCS 完整算例 + 误差分析（RMS 1.456%/max 3.143%）+ 可复现\n  （`repro_cmd` + `verify` 双 PASS）。\n- **L5 科研工程**：✅ 完整闭环机制（provenance/calibrate/store/predict/pipeline）+\n  外部锚（TensorLBM 数值解 + ITTC-1957 + P-S + KCS 几何门）。\n\n**verdict = L5**（完整、集成、可复现的科研工程机制；诚实注记：高保真源为 RANS 级、\n修正幅度小，科研价值在机制完备性而非大物理修正）。\n\n**工件**：`docs/m15056_audit_m14897.md`（本审计报告）、\n`artifacts/m15056_audit_m14897/`（重跑工件，gate 可解析）、\n`reports/m15056_verdict_evidence.json`（落表证据）。\n",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_covers_whole_markdown",
            "result": "resolved",
            "detail": "start_char=0, end_char=len(markdown)=5506"
          },
          "note": "整篇 markdown 即源资产；sha256 见 source.hash（与契约 source_hash 逐字节比对）"
        },
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "报告一级标题",
          "in_report_section": "# 交差审计：m14897 H5-CALIB-REFLUX（ship-performance-platform）→ verdict **L5**",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 72,
            "start_line": 0,
            "end_line": 0,
            "quote": "# 交差审计：m14897 H5-CALIB-REFLUX（ship-performance-platform）→ verdict **L5**",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_of_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char]==quote 且 quote 在全文唯一出现",
            "quote_in_source": true
          },
          "note": "标题行；与记录 title 字段同源（见 provenance.title_matches_contract）"
        },
        {
          "asset_id": "A03",
          "asset_class": "vcs_reference",
          "label": "上游 mission/commit/PR 三元组（m14897 / 2eb994ce1 / PR #935）",
          "in_report_section": "## ① 案例介绍（审计对象与物理背景）",
          "locator": {
            "method": "char_span",
            "start_char": 95,
            "end_char": 235,
            "start_line": 3,
            "end_line": 5,
            "quote": "\n对象 = mission **m14897**（status `succeeded`，commit `2eb994ce1`，PR **#935** merged）：\n「H5-CALIB-REFLUX · 高保真→经验系数回流」。本单 m15056 是**交差核验**（非重做）。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "git_cat_file_in_this_worktree",
            "object": "2eb994ce1",
            "result": "unresolved",
            "exit_code": 128,
            "detail": "对象存在于本仓对象库才算 resolved；上游仓提交号在本仓不存在"
          },
          "note": "上游仓库提交号；TensorKnowledge 对象库中不存在，本工序不推断其内容"
        },
        {
          "asset_id": "A04",
          "asset_class": "code_pointer",
          "label": "被审计消费点 mennen.py:ittc57_cf",
          "in_report_section": "## ① 案例介绍（审计对象与物理背景）",
          "locator": {
            "method": "char_span",
            "start_char": 237,
            "end_char": 358,
            "start_line": 7,
            "end_line": 8,
            "quote": "物理问题：平台已有真数值高保真能力（TensorLBM 平板边界层），而 Holtrop 主链的\n摩擦线常量 `ITTC57_A = 0.075`（`backend/physics/holtrop/mennen.py:ittc57_cf`）是",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_relative_path_exists",
            "result": "unresolved",
            "repo_declared": "ship-performance-platform",
            "paths": [
              "backend/physics/holtrop/mennen.py"
            ],
            "present": [],
            "missing": [
              "backend/physics/holtrop/mennen.py"
            ],
            "detail": "按 TensorKnowledge 工作树根判定；报告引用的上游仓不在本工作树内"
          },
          "note": "代码指针（仓库+文件+符号）；本工作树无该仓库"
        },
        {
          "asset_id": "A05",
          "asset_class": "numeric_anchor",
          "label": "被标定系数 ITTC57_A = 0.075 与其覆盖入口 Holtrop1984Input.cf_line_A",
          "in_report_section": "## ① 案例介绍（审计对象与物理背景）",
          "locator": {
            "method": "char_span",
            "start_char": 608,
            "end_char": 727,
            "start_line": 16,
            "end_line": 17,
            "quote": "**被标定系数**：`ITTC57_A = 0.075`（无量纲）。**消费点**：`mennen.py:ittc57_cf`，\n经 `Holtrop1984Input.cf_line_A` 覆盖（缺省 None 保持历史数值逐位不变）。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_of_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char]==quote 且 quote 在全文唯一出现",
            "quote_in_source": true
          },
          "note": "系数声明 + 消费入口原文；数值只登记不换算"
        },
        {
          "asset_id": "A06",
          "asset_class": "code_pointer",
          "label": "高保真源 TensorLBM wall_model_les.flat_plate.run_flat_plate",
          "in_report_section": "## ① 案例介绍（审计对象与物理背景）",
          "locator": {
            "method": "char_span",
            "start_char": 419,
            "end_char": 606,
            "start_line": 12,
            "end_line": 14,
            "quote": "**高保真源**：TensorLBM `wall_model_les.flat_plate.run_flat_plate` —— 零压梯度平板\n湍流边界层的数值解（Spalding 复合壁律 kappa=0.41/B=5.2 + Coles 尾迹 Pi=0.45，\n动量积分 dθ/dx=c_f/2 推进），每步真数值、无查表（RANS 级积分边界层，非 DNS/LES）。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_relative_path_exists",
            "result": "unresolved",
            "repo_declared": "TensorLBM",
            "paths": [
              "wall_model_les/flat_plate.py",
              "TensorLBM/wall_model_les/flat_plate.py"
            ],
            "present": [],
            "missing": [
              "wall_model_les/flat_plate.py",
              "TensorLBM/wall_model_les/flat_plate.py"
            ],
            "detail": "按 TensorKnowledge 工作树根判定；报告引用的上游仓不在本工作树内"
          },
          "note": "外部仓模块路径；报告以点路径给出，非本仓可解析地址"
        },
        {
          "asset_id": "A07",
          "asset_class": "geometry_declaration",
          "label": "KCS 几何前置门数值（Cb_lib/nabla/L/B/T 比值）",
          "in_report_section": "## ① 案例介绍（审计对象与物理背景）",
          "locator": {
            "method": "char_span",
            "start_char": 729,
            "end_char": 851,
            "start_line": 19,
            "end_line": 20,
            "quote": "**验证船型**：KCS（KRISO 集装箱船），几何先过门：Cb_lib=0.6509 vs\nnabla/(L·B·T)=0.650499，偏差 0.062% (<2%)；L/B=7.143，B/T=2.981，nabla=52030 m³。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_of_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char]==quote 且 quote 在全文唯一出现",
            "quote_in_source": true
          },
          "note": "几何门数值原文；本工序不复核"
        },
        {
          "asset_id": "A08",
          "asset_class": "artifact_set",
          "label": "上游 run_artifacts 9 工件清单（artifacts/m14897_calib_reflux/）",
          "in_report_section": "## ② 怎么做的（取证三件套复核，全部重跑，不信报告）",
          "locator": {
            "method": "char_span",
            "start_char": 883,
            "end_char": 1195,
            "start_line": 24,
            "end_line": 27,
            "quote": "1. **run_artifacts 复核**：`artifacts/m14897_calib_reflux/` 9 个工件（01_hifi_plate_cf.json /\n   02_calibration.json / 03_writeback.json / 04_prediction_before_after.json+csv /\n   coefficient_store/active.json+ledger.jsonl / figures/fig1+fig2.png / manifest.json /\n   MANIFEST.sha256）全部存在且非空，sha256 逐一复算一致（`verify` 通过）。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_relative_path_exists",
            "result": "unresolved",
            "repo_declared": "ship-performance-platform",
            "paths": [
              "artifacts/m14897_calib_reflux/"
            ],
            "present": [],
            "missing": [
              "artifacts/m14897_calib_reflux/"
            ],
            "detail": "按 TensorKnowledge 工作树根判定；报告引用的上游仓不在本工作树内"
          },
          "note": "工件目录与 9 个文件名清单；本工作树内不存在"
        },
        {
          "asset_id": "A09",
          "asset_class": "measurement_record",
          "label": "重跑实测数字块（A_hat=0.07553932521 / RT 2109.49→2117.58 kN / 传递函数 0.533 / 负控 +0.00000%）",
          "in_report_section": "## ② 怎么做的（取证三件套复核，全部重跑，不信报告）",
          "locator": {
            "method": "char_span",
            "start_char": 1196,
            "end_char": 1435,
            "start_line": 28,
            "end_line": 31,
            "quote": "2. **benchmark ref vs got 复核**：重跑 `python scripts/run_calib_reflux.py run` →\n   A_hat=**0.07553932521**（ref 0.075，+0.72%），KCS 设计点 RT **2109.49→2117.58 kN**\n   （+0.384%），传递函数 dRt/dA=**0.533**，负控还原误差 **+0.00000%**（G2=4.44e-14）。\n   与报告数字逐位一致。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_of_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char]==quote 且 quote 在全文唯一出现",
            "quote_in_source": true
          },
          "note": "上游自报实测值；只登记原文，不做独立复算（本工序无上游代码）"
        },
        {
          "asset_id": "A10",
          "asset_class": "command",
          "label": "repro_cmd 与其执行证据（run + verify）",
          "in_report_section": "## ② 怎么做的（取证三件套复核，全部重跑，不信报告）",
          "locator": {
            "method": "char_span",
            "start_char": 1436,
            "end_char": 1572,
            "start_line": 32,
            "end_line": 33,
            "quote": "3. **repro_cmd 可执行**：`python scripts/run_calib_reflux.py run`（22s，PASS，5 门全绿）+\n   `verify`（第三方复算，ok=true，父链无孤点、账本 prev 链完整、生效快照与账本末条一致）。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_relative_path_exists",
            "result": "unresolved",
            "repo_declared": "ship-performance-platform",
            "paths": [
              "scripts/run_calib_reflux.py"
            ],
            "present": [],
            "missing": [
              "scripts/run_calib_reflux.py"
            ],
            "detail": "按 TensorKnowledge 工作树根判定；报告引用的上游仓不在本工作树内"
          },
          "note": "复现命令可执行性来自上游报告；脚本本体不在本工作树，未执行"
        },
        {
          "asset_id": "A11",
          "asset_class": "test_suite",
          "label": "单测文件 backend/tests/test_calib_reflux.py 与 17 passed",
          "in_report_section": "## ② 怎么做的（取证三件套复核，全部重跑，不信报告）",
          "locator": {
            "method": "char_span",
            "start_char": 1573,
            "end_char": 1690,
            "start_line": 34,
            "end_line": 35,
            "quote": "4. **单测重跑**：`backend/tests/test_calib_reflux.py` → **17 passed**（31.6s），\n   断言不变量（负控还原/夹持边界/篡改必检出/消费者真读账本/同输入哈希逐位一致）。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_relative_path_exists",
            "result": "unresolved",
            "repo_declared": "ship-performance-platform",
            "paths": [
              "backend/tests/test_calib_reflux.py"
            ],
            "present": [],
            "missing": [
              "backend/tests/test_calib_reflux.py"
            ],
            "detail": "按 TensorKnowledge 工作树根判定；报告引用的上游仓不在本工作树内"
          },
          "note": "测试文件不在本工作树；本工序未重跑该测试（避免以未跑宣称通过）"
        },
        {
          "asset_id": "A12",
          "asset_class": "gate_check",
          "label": "maturity_gate.judge 自检（claimed L5 → 7 键全过）",
          "in_report_section": "## ② 怎么做的（取证三件套复核，全部重跑，不信报告）",
          "locator": {
            "method": "char_span",
            "start_char": 1691,
            "end_char": 1778,
            "start_line": 36,
            "end_line": 37,
            "quote": "5. **判级+网关自检**：按 L0–L5 功能实质判级，`maturity_gate.judge` 本地模拟复核\n   （claimed L5 → 7 键全过，无缺键）。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_relative_path_exists",
            "result": "unresolved",
            "repo_declared": "ship-performance-platform",
            "paths": [
              "maturity_gate.py"
            ],
            "present": [],
            "missing": [
              "maturity_gate.py"
            ],
            "detail": "按 TensorKnowledge 工作树根判定；报告引用的上游仓不在本工作树内"
          },
          "note": "网关实现体与运行结果均为上游产物；本工序只登记声明"
        },
        {
          "asset_id": "A13",
          "asset_class": "dataset_stats",
          "label": "S1 高保真证据统计（站点数 238、Re_x 区间）",
          "in_report_section": "## ③ 计算结果（程序化注入，零手抄）",
          "locator": {
            "method": "char_span",
            "start_char": 1802,
            "end_char": 1870,
            "start_line": 41,
            "end_line": 41,
            "quote": "**S1 高保真证据**：站点数 238，Re_x ∈ [2.020e+07, 2.020e+08]，RANS-grade 积分边界层。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_of_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char]==quote 且 quote 在全文唯一出现",
            "quote_in_source": true
          },
          "note": "数据集统计摘要；数据本体为 A08 工件，未在本仓"
        },
        {
          "asset_id": "A14",
          "asset_class": "parameter_set",
          "label": "S2 标定结果（A_hat、σ_A、残差 RMS/max、物理带、clamped、带敏感性）",
          "in_report_section": "## ③ 计算结果（程序化注入，零手抄）",
          "locator": {
            "method": "char_span",
            "start_char": 1872,
            "end_char": 2064,
            "start_line": 43,
            "end_line": 45,
            "quote": "**S2 标定**：A_hat=**0.075539**（ΔA/A=+0.72%），σ_A=7.239e-05（0.097%），\n残差 RMS=1.456% / max=3.143%，物理带 [0.0700, 0.0800]，clamped=False。\n带敏感性（下界扫描）：1e7→0.075539 / 2e7→0.075539 / 5e7→0.076396，ΔA 漂移 <3%。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_of_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char]==quote 且 quote 在全文唯一出现",
            "quote_in_source": true
          },
          "note": "标定参数与不确定度原文；数值仅登记"
        },
        {
          "asset_id": "A15",
          "asset_class": "ledger_record",
          "label": "S3 回写账本记录（seq=0、entry_sha256、生效快照 head_sha256）",
          "in_report_section": "## ③ 计算结果（程序化注入，零手抄）",
          "locator": {
            "method": "char_span",
            "start_char": 2066,
            "end_char": 2165,
            "start_line": 47,
            "end_line": 48,
            "quote": "**S3 回写**：账本 seq=0，entry_sha256=`6fc45dd1…`，生效快照 head_sha256=`3eeab056…`，\nprev 哈希链完整，可回滚（追加式，不删不盖）。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_of_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char]==quote 且 quote 在全文唯一出现",
            "quote_in_source": true
          },
          "note": "账本哈希为截断展示（…）；登记原文，不补全"
        },
        {
          "asset_id": "A16",
          "asset_class": "table",
          "label": "S4 回流前后对照表（表头 8 列 + 8 个 Fn 数据行）",
          "in_report_section": "## ③ 计算结果（程序化注入，零手抄）",
          "locator": {
            "method": "char_span",
            "start_char": 2167,
            "end_char": 2990,
            "start_line": 50,
            "end_line": 61,
            "quote": "**S4 回流前后对照**（KCS，同一 Holtrop 主链，仅摩擦线常量不同）：\n\n| Fn | V [kn] | Cf before | Cf after | ΔCf | RT before [kN] | RT after [kN] | ΔRT |\n|---|---|---|---|---|---|---|---|\n| 0.150 | 13.85 | 0.0014697 | 0.0014803 | +0.721% | 486.74 | 489.62 | +0.592% |\n| 0.180 | 16.62 | 0.0014377 | 0.0014480 | +0.716% | 729.57 | 733.63 | +0.556% |\n| 0.200 | 18.46 | 0.0014196 | 0.0014298 | +0.719% | 952.38 | 957.32 | +0.519% |\n| 0.220 | 20.31 | 0.0014036 | 0.0014137 | +0.720% | 1245.72 | 1251.63 | +0.474% |\n| 0.240 | 22.16 | 0.0013892 | 0.0013992 | +0.720% | 1616.99 | 1623.95 | +0.430% |\n| 0.260 | 24.00 | 0.0013761 | 0.0013860 | +0.719% | **2109.49** | **2117.58** | **+0.384%** |\n| 0.280 | 25.85 | 0.0013642 | 0.0013740 | +0.718% | 2799.39 | 2808.70 | +0.333% |\n| 0.300 | 27.70 | 0.0013532 | 0.0013630 | +0.724% | 3522.12 | 3532.72 | +0.301% |",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_of_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char]==quote 且 quote 在全文唯一出现",
            "quote_in_source": true
          },
          "note": "只登记表结构（含引文全文），不抽取数值到知识对象"
        },
        {
          "asset_id": "A17",
          "asset_class": "numeric_anchor",
          "label": "设计点结论数字（Fn=0.260 RT/Pe 变化量、传递函数 dRt%/dA%）",
          "in_report_section": "## ③ 计算结果（程序化注入，零手抄）",
          "locator": {
            "method": "char_span",
            "start_char": 2992,
            "end_char": 3127,
            "start_line": 63,
            "end_line": 64,
            "quote": "**设计点（Fn=0.260, 24.00 kn）**：RT 2109.49 → 2117.58 kN（**+0.38%**），\nPe 26047.98 → 26147.97 kW（+0.38%）。传递函数 dRt%/dA% = **0.533**（≈摩擦阻力占位比）。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_of_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char]==quote 且 quote 在全文唯一出现",
            "quote_in_source": true
          },
          "note": "设计点派生数字原文；与 A16 表格同源"
        },
        {
          "asset_id": "A18",
          "asset_class": "figure",
          "label": "图1 fig1_hifi_vs_reference.png（高保真局部摩阻 vs 参考线）",
          "in_report_section": "## ④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 3139,
            "end_char": 3261,
            "start_line": 68,
            "end_line": 69,
            "quote": "`artifacts/m15056_audit_m14897/figures/fig1_hifi_vs_reference.png` —— 高保真局部摩阻\nvs ITTC-57 局部线与 Prandtl-Schlichting（右=带内偏差）。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "record_figures_name_lookup",
            "result": "present",
            "figure_name": "fig1_hifi_vs_reference.png",
            "record_figure_names": [
              "fig1_hifi_vs_reference.png",
              "fig2_prediction_before_after.png"
            ],
            "payload_downloaded": false,
            "detail": "只按记录 figures[].name 对齐，PNG 本体未下载/未入库"
          },
          "note": "记录 figures[] 内含同名 png 元数据（name+caption），正文给出路径"
        },
        {
          "asset_id": "A19",
          "asset_class": "figure",
          "label": "图2 fig2_prediction_before_after.png（回流前后 KCS 总阻力曲线）",
          "in_report_section": "## ④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 3263,
            "end_char": 3361,
            "start_line": 71,
            "end_line": 72,
            "quote": "`artifacts/m15056_audit_m14897/figures/fig2_prediction_before_after.png` —— 回流前后\nKCS 总阻力曲线与逐点 ΔRT。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "record_figures_name_lookup",
            "result": "present",
            "figure_name": "fig2_prediction_before_after.png",
            "record_figure_names": [
              "fig1_hifi_vs_reference.png",
              "fig2_prediction_before_after.png"
            ],
            "payload_downloaded": false,
            "detail": "只按记录 figures[].name 对齐，PNG 本体未下载/未入库"
          },
          "note": "记录 figures[] 内含同名 png 元数据（name+caption），正文给出路径"
        },
        {
          "asset_id": "A20",
          "asset_class": "limitation_set",
          "label": "注意点 1–6（局部/平均恒等式、前缘过渡段、外推、证据分层、WITHHELD 拒用、审计侧记账）",
          "in_report_section": "## ⑤ 注意点（坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 3388,
            "end_char": 4188,
            "start_line": 76,
            "end_line": 90,
            "quote": "1. **局部量 vs 平均量**：ITTC-57 是**平均**摩阻线，平板求解器给**局部** c_f；直接相比\n   会凭空造出 ~2 倍偏差。必须用平均线的微分恒等式 `cf = A(L-2)^-2 [1-2/(ln10(L-2))]`\n   （`ittc57_local_exact`）。\n2. **前缘入口过渡段**：求解器从 Re_theta=1e4 起步，Re_x ≲ 1e7 处尾迹未充分建立；\n   标定带下界取 2e7（敏感性表 1e7/2e7/5e7 三档，ΔA 漂移 <3%）。\n3. **外推**：高保真带覆盖到 Re≈2.0e+08，KCS 26 kn 的 Re≈2.6e9 —— 差 1 个数量级；\n   A 被夹在物理带 ±0.0050 内，越界即 `clamped=True` 登记，不静默吸收。\n4. **证据等级分层**：高保真源是 RANS 级积分边界层（壁律闭包 kappa/B/Pi 取自文献，\n   未在本轮重标定），不是 DNS/LES 解析湍流。它自身与 ITTC-57 局部线平均偏差 +0.98%、\n   与 P-S 最大偏差 6.16%。\n5. **没有采用不可核证的试验表**：仓库里若干「公开模型试验表」只有 `KRISO_tank` 之类\n   标签、无逐项数字化出处（WITHHELD 级），本轮拒绝把它们当高保真锚。\n6. **审计侧记账**：m14897 代码在 `/root/tp-agent/work/m14897`（独立 worktree），\n   ECO 主 checkout 已陈旧（当前 HEAD 不含 calib_reflux）；本单把重跑工件落在\n   `/root/tp-agent/work/m15056/artifacts/m15056_audit_m14897/`，gate 以 m15056 为根可解析。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_of_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char]==quote 且 quote 在全文唯一出现",
            "quote_in_source": true
          },
          "note": "六条坑/局限原文；含 WITHHELD 级外部试验表被拒用的判据"
        },
        {
          "asset_id": "A21",
          "asset_class": "table",
          "label": "误差判定表（5 行，含显式 <3%? 回答）",
          "in_report_section": "## ⑥ 误差判定（逐项 vs 基准，显式回答是否 <3%）",
          "locator": {
            "method": "char_span",
            "start_char": 4222,
            "end_char": 4567,
            "start_line": 94,
            "end_line": 100,
            "quote": "| 量 | 基准 | 本次 | 误差 | <3%? |\n|---|---|---|---|---|\n| 高保真局部 c_f（带内均值） | ITTC-57 局部线 | 数值解 | +0.98% (max 2.83%) | 是 |\n| 高保真局部 c_f（带内均值） | Prandtl-Schlichting | 数值解 | -3.50% (max 6.16%) | 否 |\n| 反解 A | 已知真值 0.075（负控合成数据） | A_hat | +0.00000% | 是 |\n| 标定残差 | 拟合线自身 | 高保真站点 | RMS 1.456% | 是 |\n| 回流后 Rt（设计点） | 回流前 Rt | after | +0.384% | 变化量本身 <3%（幅度即结论） |",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_of_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char]==quote 且 quote 在全文唯一出现",
            "quote_in_source": true
          },
          "note": "上游误差表原文；本工序不复核其结论"
        },
        {
          "asset_id": "A22",
          "asset_class": "statement",
          "label": "结论段（机制证明 + 1% 以内一致性）",
          "in_report_section": "## ⑥ 误差判定（逐项 vs 基准，显式回答是否 <3%）",
          "locator": {
            "method": "char_span",
            "start_char": 4569,
            "end_char": 4757,
            "start_line": 102,
            "end_line": 105,
            "quote": "**结论**：高保真数值解与 ITTC-57 在带内平均偏差 +0.98%，即这条经验线在当前可达 Re\n区间已被高保真证实到 **1% 以内**；回流写回的修正是 +0.72%（ΔRt +0.38%）。这不是\n「标定出大修正」，而是**机制证明 + 一致性的量化**：若未来高保真源（LES/试验）给出\n>3% 的偏差，同一管线会把该偏差以可审计、可回滚的方式写进平台主链。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_of_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char]==quote 且 quote 在全文唯一出现",
            "quote_in_source": true
          },
          "note": "上游结论原文，按约束保持为未验证陈述"
        },
        {
          "asset_id": "A23",
          "asset_class": "statement",
          "label": "L0–L5 判级依据清单",
          "in_report_section": "## 判级（L0–L5 功能实质）",
          "locator": {
            "method": "char_span",
            "start_char": 4778,
            "end_char": 5284,
            "start_line": 109,
            "end_line": 117,
            "quote": "- **L0 文档**：远超（有完整报告+工件）。\n- **L1 数学/单元验证**：✅ `calibrate.py` 过原点 LSQ + 负控 + 物理边界；17 单测断言不变量。\n- **L2 独立功能**：✅ `calib_reflux` 真代码（输入→计算→输出），无 placeholder。\n- **L3 系统集成**：✅ `Holtrop1984Input.cf_line_A` 接入 Holtrop 主链 `mennen.py:ittc57_cf`\n  （line 339 `Cf = ittc57_cf(Re, inp.cf_line_A)`），消费者从账本读系数。\n- **L4 基准验证**：✅ KCS 完整算例 + 误差分析（RMS 1.456%/max 3.143%）+ 可复现\n  （`repro_cmd` + `verify` 双 PASS）。\n- **L5 科研工程**：✅ 完整闭环机制（provenance/calibrate/store/predict/pipeline）+\n  外部锚（TensorLBM 数值解 + ITTC-1957 + P-S + KCS 几何门）。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_of_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char]==quote 且 quote 在全文唯一出现",
            "quote_in_source": true
          },
          "note": "六档判级的逐条依据原文"
        },
        {
          "asset_id": "A24",
          "asset_class": "verdict",
          "label": "verdict = L5 与其诚实注记",
          "in_report_section": "## 判级（L0–L5 功能实质）",
          "locator": {
            "method": "char_span",
            "start_char": 5286,
            "end_char": 5364,
            "start_line": 119,
            "end_line": 120,
            "quote": "**verdict = L5**（完整、集成、可复现的科研工程机制；诚实注记：高保真源为 RANS 级、\n修正幅度小，科研价值在机制完备性而非大物理修正）。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_of_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char]==quote 且 quote 在全文唯一出现",
            "quote_in_source": true
          },
          "note": "上游 verdict；本工序不背书、不改写、不标 verified"
        },
        {
          "asset_id": "A25",
          "asset_class": "deliverable_set",
          "label": "本单工件三路径（docs/m15056_audit_m14897.md、artifacts 目录、reports 证据 json）",
          "in_report_section": "## 判级（L0–L5 功能实质）",
          "locator": {
            "method": "char_span",
            "start_char": 5366,
            "end_char": 5505,
            "start_line": 122,
            "end_line": 124,
            "quote": "**工件**：`docs/m15056_audit_m14897.md`（本审计报告）、\n`artifacts/m15056_audit_m14897/`（重跑工件，gate 可解析）、\n`reports/m15056_verdict_evidence.json`（落表证据）。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_relative_path_exists",
            "result": "unresolved",
            "repo_declared": "ship-performance-platform",
            "paths": [
              "docs/m15056_audit_m14897.md",
              "artifacts/m15056_audit_m14897/",
              "reports/m15056_verdict_evidence.json"
            ],
            "present": [],
            "missing": [
              "docs/m15056_audit_m14897.md",
              "artifacts/m15056_audit_m14897/",
              "reports/m15056_verdict_evidence.json"
            ],
            "detail": "按 TensorKnowledge 工作树根判定；报告引用的上游仓不在本工作树内"
          },
          "note": "相对路径；本工作树（TensorKnowledge）内不存在，属上游仓产物"
        },
        {
          "asset_id": "A26",
          "asset_class": "external_worktree",
          "label": "审计侧记账：m14897 / m15056 两个 worktree 绝对路径与 ECO 主 checkout 陈旧声明",
          "in_report_section": "## ⑤ 注意点（坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 3981,
            "end_char": 4188,
            "start_line": 88,
            "end_line": 90,
            "quote": "6. **审计侧记账**：m14897 代码在 `/root/tp-agent/work/m14897`（独立 worktree），\n   ECO 主 checkout 已陈旧（当前 HEAD 不含 calib_reflux）；本单把重跑工件落在\n   `/root/tp-agent/work/m15056/artifacts/m15056_audit_m14897/`，gate 以 m15056 为根可解析。",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "host_absolute_path_probe_informational",
            "result": "unresolved",
            "probes": [
              {
                "path": "/root/tp-agent/work/m14897",
                "exists_on_host": true
              },
              {
                "path": "/root/tp-agent/work/m15056/artifacts/m15056_audit_m14897/",
                "exists_on_host": true
              }
            ],
            "detail": "绝对路径不属于 source_uri 可解析面；host 存在性仅作信息位，换机即不可复现，故仍登记 referenced_unresolved"
          },
          "note": "宿主机绝对路径；host 探针结果仅作信息位，跨机器不可复现"
        },
        {
          "asset_id": "A27",
          "asset_class": "code_pointer",
          "label": "回流管线脚本 scripts/run_calib_reflux.py（run/verify 入口）",
          "in_report_section": "## ② 怎么做的（取证三件套复核，全部重跑，不信报告）",
          "locator": {
            "method": "char_span",
            "start_char": 1436,
            "end_char": 1514,
            "start_line": 32,
            "end_line": 32,
            "quote": "3. **repro_cmd 可执行**：`python scripts/run_calib_reflux.py run`（22s，PASS，5 门全绿）+",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_relative_path_exists",
            "result": "unresolved",
            "repo_declared": "ship-performance-platform",
            "paths": [
              "scripts/run_calib_reflux.py"
            ],
            "present": [],
            "missing": [
              "scripts/run_calib_reflux.py"
            ],
            "detail": "按 TensorKnowledge 工作树根判定；报告引用的上游仓不在本工作树内"
          },
          "note": "命令引用的脚本本体；本工作树无此文件"
        }
      ],
      "claims": [],
      "claims_note": "契约 objective.classify_report_type=false 且 notes 明确 claims 允许空数组：本工序只做资产登记与定位，不做 claim 抽取、不做类型分类、不标 verified（verification 由平台门计算）；因此 claims 为空是合法完整结果，acceptance 项 all_claims_have_evidence_or_explicit_unresolved_status 空真成立。",
      "boundary": {
        "only_report_id": "14179",
        "read_other_reports": false,
        "modified_upstream_artifacts": false,
        "marked_verified": false,
        "extraction_done": false,
        "classification_done": false
      }
    }
  },
  "claims": []
}
```
