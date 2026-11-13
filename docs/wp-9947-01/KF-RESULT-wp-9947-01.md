# KF-RESULT wp-9947-01

## ① 案例介绍（这是什么工序，服务哪份报告）

本单是「报告→知识」产线上的一道单一工序：**资产登记（task_type = 01-asset-registration）**，
只服务 `report_id=9947` 这一份报告，不做抽取、不做报告类型分类、不改写上游产物。

- 源报告：report 9947《【试点】技术路线锁定 A/B 终局对照 v1》，scenario_key=`pilot-ab`，平台 stage=`S0`，
  创建于 `2026-11-09T14:30:57.100885+00:00`，tags=["A/B试点", "MethodCommitment", "盲裁"]。
- 报告本体的物理事实：markdown `616` 字符 / `855` 字节 UTF-8，
  sha256 = `c9857b84a9ea71ea174f3392d34e8e61403202ee154fdab059c4e9abd83fc0bf`，与工作包契约 `input.source_hash` 逐字节相同。
- 内容性质：A/B 双路线试点的**终局对照汇总页**（自动合成），正文只有标题、prereg 指针、模型席位一行、
  一张五席位终态表、一行判据与裁决规则、一行原始证据指针。**它不是数值计算报告**：
  表体不含任何数值，判据细节与原始证据都以 `scenario_key` 外置。
- 本工序的边界（契约 objective）：`register_assets: true`、`classify_report_type: false`，
  `claims` 允许为空数组；`do_not_mark_claims_as_verified: true`（verification 由平台门计算）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取证不靠记忆**：`GET {TENSOR_API_BASE}/tensor/reports/9947` 取 `markdown` 字段，落盘
   `runs/wp-9947-01/report_9947.{md,json}`；本地重算 sha256 与契约 `source_hash` 比对，
   同时校验 `chars=616`、`title`、`scenario_key` 三项契约身份 —— 任一不符脚本立即 FATAL 退出
   （`scripts/kf_register_9947.py`）。
2. **定位而非抄写**：脚本维护一张 12 行锚点表（asset_id / 资产类 / 唯一锚点串 / 相对行跨 / 是否子串定位）。
   运行时先在 markdown 中定位锚点行（断言全文出现 **恰好 1 次**），再算字符偏移，**直接从原文切片**得到
   `quote`；切片再断言全文出现次数 == 1。单行资产用子串定位（`sub=True`）以缩窄 span，不整行吞并。
3. **可解析性机器判定**：每个资产跑 `resolution_check`，结果与声明的 `resolution` 由**严格映射**绑定，
   不一致即中止（`RESOLUTION_TO_CHECK`）。三类判据：
   - 页内资产 → 重新切片校验；
   - 外部指针 → 在报告原文里正则抽取路径/URL/DOI/scenario_key，再**只读探测**：宿主路径 `stat`、
     平台 `GET /tensor/reports?scenario_key=<key>`；探测结果原样入账（含 0 命中的键）；
   - 图件 → 平台 `figures` 字段 + 正文 `![` 计数。
4. **独立复核**：`scripts/kf_verify_9947.py` 在**新进程、重新登录、重新取报告**的前提下重算哈希、
   重切每个 locator、重跑全部平台探测（与登记时记录的命中数逐键比对），并做 schema 校验、ID 唯一性、
   counts 一致性、artifact↔envelope 哈希、`docs/` 镜像字节一致、notices↔资产绑定 §6 项附加检查。
5. **零手抄到报告**：本报告的每张表、每个数字都由 `scripts/kf_report_9947.py` 从 manifest/verification
   在构建时格式化注入，JSON 代码块是登记脚本写出的 envelope 原文件。

## ③ 产出物清单

| 输出文件 | 要点 |
|---|---|
| `artifacts/wp-9947-01/asset_manifest.json` | 契约声明的唯一输出；12 个资产（resolved_in_source=7 / referenced_unresolved=4 / declared_absent=1）、claims=[]、5 条 notices、resolution_semantics；sha256=`6010cbac3551e3c850bbc15aaf147b3c0a17deba93d8f8879e8f09a54df8ae8a` |
| `docs/wp-9947-01/asset_manifest.json` | 上者的**字节一致镜像**（仓推送门会丢弃 `artifacts/**` 与 `runs/**`，故 docs 是可提交副本） |
| `runs/wp-9947-01/report_9947.md` / `.json` | API 原始取件（markdown + id/title/scenario_key/figures/tags），供离线复算 |
| `runs/wp-9947-01/kf_result.wp-9947-01.json` | kf_result.v1 信封（本报告唯一 json 代码块的内容，逐字节相同） |
| `artifacts/wp-9947-01/verification.json` + `docs/` 镜像 | 17 项自检逐条记录（17/17 pass），overall=`PASS` |
| `artifacts/wp-9947-01/fig_asset_inventory.png` | 图1/图2 合图：定位地图 + 可解析状态分布（数字全部来自 manifest） |
| `scripts/kf_register_9947.py` / `kf_verify_9947.py` / `kf_report_9947.py` | 登记 / 独立复核 / 报告构建，一键复跑 |
| `tests/test_kf_wp9947.py` | 不变量测试（源哈希/定位/schema/计数/镜像）+ 篡改负对照（改引文、挪 span、改 resolution 均必须被检出） |

## ④ 证据定位表（claim/字段 → 原文引文片段）

登记口径：`resolved_in_source` = 内容可在源 markdown 内按 `[start_char,end_char)` 逐字切片且全文唯一；
`referenced_unresolved` = 报告只给指针（路径/键名/scenario_key），未给可校验的 id+哈希组合，本工序只登记指针与探测结果；
`declared_absent` = 报告与平台元数据均无该资产（此处为图件）。

| asset_id | class | resolution | locator（char span / method） | 原文片段（逐字取自 report 9947 markdown） |
|---|---|---|---|---|
| A01 | document | resolved_in_source | 0-616 / document | `（整篇 markdown，sha256 见 provenance）` |
| A02 | heading | resolved_in_source | 0-39 / char_span | `## A/B 试点终局对照（2026-11-09 14:30:57 自动合成）` |
| A03 | external_file_reference | referenced_unresolved | 41-92 / char_span | `prereg：`/root/tp-agent/pilot_ab_prereg_20261109.md`` |
| A04 | evidence_pointer | referenced_unresolved | 93-134 / char_span | `sha256 在 GAP-LBM-MCMP-POISEUILLE.evidence` |
| A05 | model_roster | resolved_in_source | 143-204 / char_span | `dev 两臂同模型 qwen3.7-plus；B 审查席=deepseek-v4-flash；QR 两臂=glm-5…` |
| A06 | table_shell | resolved_in_source | 206-385 / char_span | `\| 席位 \| 任务 \| 终态 \| 墙钟 \| 摘要 \|` |
| A07 | acceptance_criteria | resolved_in_source | 387-423 / char_span | `判据三主一加分（①<5% ②<10% ③<0.005·Umax ④趋势）` |
| A08 | decision_rule | resolved_in_source | 472-512 / char_span | `裁决规则按 prereg：QR PASS 数→过程指标→双 FAIL 比根因深度` |
| A09 | deferred_decision | resolved_in_source | 513-532 / char_span | `人工终裁与推广/否决建议交 owner` |
| A10 | upstream_report_pointer | referenced_unresolved | 434-470 / char_span | `scenario_key=pilot-qr-a / pilot-qr-b` |
| A11 | upstream_report_pointer | referenced_unresolved | 534-616 / char_span | `原始证据：pilot-a/b 两臂报告（scenario_key=pilot-arm-a / pilot-arm-b…` |
| A12 | figure_slot | declared_absent | 0-616 / document | `（整篇 markdown，sha256 见 provenance）` |

**指针事实（程序化探测，不含推断）**

| id | 关联资产 | 事实（指针/占位，不含推断） |
|---|---|---|
| P1 | A06 | 五席位终态表的表体是占位符（任务列 m- / 终态列 - / 墙钟列空 / 摘要列 -），报告标题与平台 summary 所说的「终态/表」在本文中没有数值结果落地 |
| P2 | A09 | 判决与终裁均不在本文：裁决规则被指向 prereg(A03)，人工终裁被显式交 owner(A09) |
| P3 | A11 | 判据细节与原始证据均以 scenario_key 形式外置（A10/A11），本文自足性不足：不含任何 <5%/<10%/<0.005·Umax 的实测值 |
| P4 | A12 | 全文无图、平台 figures=[]：「终局对照」不含任何对照曲线或场量云图 |
| P5 | A11 | 指针探测：scenario_key pilot-arm-b 在平台 /tensor/reports 查询下命中 0 条（同批其余键各命中 1 条）；本工序只登记「在该查询面下不可见」这一事实，不推断原因是未发布、未生成还是权限不可见 |

## ⑤ 注意点与局限

1. **本报告不含任何结果数字**：五席位终态表（A06）的表体逐行为 `m-`（任务列）、`-`（终态列）、空（墙钟列）、
   `-`（摘要列）。标题与平台 summary 称「终态自动合成/见表」，但表中没有落地值；本工序只登记字面值，
   不替它补数（`do_not_invent_missing_information`）。
2. **判据与裁决规则在本页不可自证**：判据三主一加分（A07）只是阈值声明，三条 `<5% / <10% / <0.005·Umax`
   的**实测值一条都不在本页**；测点住在 `scenario_key=pilot-qr-a / pilot-qr-b` 的 QR 报告（A10）。
   因此本页不能支撑任何「PASS/FAIL」结论，只能支撑「判据与裁决规则被这样写下来」。
3. **指针可能悬空**：探测 5 个 scenario_key，命中 0 条者 1 个（pilot-arm-b），
   其余 4 个各命中 1 条（P5）。本工序不推断原因
   （未发布 / 未生成 / 权限不可见），只登记「在该查询面下不可见」。
4. **prereg 路径在宿主上存在但身份未断言**：`/root/tp-agent/pilot_ab_prereg_20261109.md`
   实测存在（2567 字节），
   但报告未给出该文件哈希（推迟到 A04 的 GAP 键），故按 `referenced_unresolved` 处理，不声称「已核对」。
5. **无图是事实，不是选择**：平台 `figures=[]`、正文无 `![` 引用（A12）；本报告另附的图 1/图 2 是**本工序的
   登记地图**，不是上游的计算场量或对照曲线，不得被当作 9947 的图件。
6. **不标 verified**：manifest 与 envelope 中 `verification_status = not_verified`，只有资产级
   `resolution` 状态；`claims=[]` 是本工序的完整结果而非省略（契约允许空数组）。

## ⑥ 自检：逐条对照 acceptance

| 验收项 | 结果 | 证据（来自 verification.json） |
|---|---|---|
| valid_json | **PASS** | `{"manifest": "artifacts/wp-9947-01/asset_manifest.json", "result": "runs/wp-9947-01/kf_result.wp-9947-01.json", "block_equals_result": true, "manifest_mirror_equals_artifact": true}` |
| source_hash_matches | **PASS** | `{"api_sha256": "c9857b84a9ea71ea174f3392d34e8e61403202ee154fdab059c4e9abd83fc0bf", "contract_sha256": "c9857b84a9ea71ea174f3392d34e8e61403202ee154fdab059c4e9abd83fc0bf", "manifest_sha256": "c9857b84a9ea71ea174f3392d34e8e` |
| contract_identity_matches | **PASS** | `{"api_title": "【试点】技术路线锁定 A/B 终局对照 v1", "contract_title": "【试点】技术路线锁定 A/B 终局对照 v1", "api_scenario": "pilot-ab", "contract_scenario": "pilot-ab"}` |
| schema_pass | **PASS** | `{"schema": "schemas/asset_manifest.v1.schema.json", "note": "local schema, generalized from const to pattern for package_id/report_id/source.uri so one gate covers every report in this lane"}` |
| result_envelope_shape | **PASS** | `{"keys": ["claims", "outputs", "package_id", "provenance", "report_id", "task_type"], "outputs_keys": ["asset_manifest.json"]}` |
| result_ids_match_contract | **PASS** | `{"package_id": "wp-9947-01", "task_type": "01-asset-registration", "report_id": "9947", "source_uri": "tensor://reports/9947"}` |
| result_envelope_closed | **PASS** | `{"extra_keys": []}` |
| result_validates_against_kf_result_schema | **PASS** | `{"schema": "schemas/kf_result.v1.schema.json", "root_keys": ["claims", "outputs", "package_id", "provenance", "report_id", "task_type"]}` |
| source_locator_resolvable | **PASS** | `{"assets_checked": 12, "failures": [], "method": "re-slice freshly fetched API markdown at [start_char,end_char) + occurrence count"}` |
| no_duplicate_ids | **PASS** | `{"assets": 12, "duplicates": []}` |
| all_claims_have_evidence_or_explicit_unresolved_status | **PASS** | `{"claims": 0, "offenders": [], "note": "claims=[] is a complete result for this package (objective.register_assets only, classify_report_type=false); every asset instead carries an explicit resolution status"}` |
| no_verified_markers | **PASS** | `{"structural_hits": [], "note": "verification is computed by the platform gate, not here"}` |
| counts_consistent | **PASS** | `{"assets": 12, "by_class": {"document": 1, "heading": 1, "external_file_reference": 1, "evidence_pointer": 1, "model_roster": 1, "table_shell": 1, "acceptance_criteria": 1, "decision_rule": 1, "deferred_decision": 1, "up` |
| artifact_hash_matches_envelope | **PASS** | `{"file_sha256": "6010cbac3551e3c850bbc15aaf147b3c0a17deba93d8f8879e8f09a54df8ae8a", "envelope_sha256": "6010cbac3551e3c850bbc15aaf147b3c0a17deba93d8f8879e8f09a54df8ae8a"}` |
| durable_mirror_identical | **PASS** | `{"mirror": "docs/wp-9947-01/asset_manifest.json", "why": "tp_pusher._EXCLUDE drops artifacts/** and runs/**; docs/ is committed"}` |
| notices_bound_to_assets | **PASS** | `{"notices": 5, "orphans": []}` |
| probe_evidence_reproducible | **PASS** | `{"keys": ["pilot-ab-review", "pilot-arm-a", "pilot-arm-b", "pilot-qr-a", "pilot-qr-b"], "diffs": {}}` |

**误差判定（本题为登记工序，无物理量基准）**：本工序唯一可验的「数值」是**字符串/字节级恒等**，不是物理量，
故按恒等判据而非 3% 判据裁：

| 关键量 | 本工序值 | 基准 | 差值 | 是否 <3%？ |
|---|---|---|---|---|
| markdown sha256 | `c9857b84a9ea71ea174f3392d34e8e61403202ee154fdab059c4e9abd83fc0bf` | 契约 `source_hash` = `c9857b84…3fc0bf` | 0（全等） | 是（恒等，0 误差） |
| markdown 字符数 | 616 | 契约 `chars` = 616 | 0 | 是（恒等，0 误差） |
| locator 可复现率 | 12/12（独立重取后重切） | 全部可解析 | 0 条失败 | 是（恒等，0 误差） |
| 资产计数一致性 | counts=12，资产条目=12 | 自洽 | 0 | 是（恒等，0 误差） |

诚实声明：本工序**没有**算出任何物理量（阻力/推进/耐波…），因此不存在「vs 实验/参考值」的精度结论；
上表不是精度证据，只是登记正确性证据。报告 9947 本身的物理结论**未经本工序验证，也不由本工序背书**。

## 复现（一键）

```bash
# 工作树根 = 仓库检出；需要 TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS
python3 scripts/kf_register_9947.py        # 取报告 → 校验哈希 → 生成 asset_manifest + kf_result
python3 scripts/kf_verify_9947.py          # 独立重取 + 契约 6 项验收自检 + 附加检查（PASS）
python3 scripts/kf_report_9947.py --no-post  # 重建本报告与图（不发帖）
pytest -q tests/test_kf_wp9947.py          # 不变量测试（含篡改负对照）
```

## 结果 JSON（唯一 json 代码块）

```json
{
  "package_id": "wp-9947-01",
  "task_type": "01-asset-registration",
  "report_id": "9947",
  "provenance": {
    "source_uri": "tensor://reports/9947",
    "source_field": "markdown",
    "source_hash": "sha256:c9857b84a9ea71ea174f3392d34e8e61403202ee154fdab059c4e9abd83fc0bf",
    "source_chars": 616,
    "source_bytes_utf8": 855,
    "source_title": "【试点】技术路线锁定 A/B 终局对照 v1",
    "scenario_key": "pilot-ab",
    "contract_version": "1.0",
    "lane": "C",
    "work_package": "wp-9947-01",
    "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/9947",
    "local_copy": "runs/wp-9947-01/report_9947.md",
    "generator": "scripts/kf_register_9947.py",
    "verifier": "scripts/kf_verify_9947.py",
    "verification_status": "not_verified"
  },
  "outputs": {
    "asset_manifest.json": {
      "artifact_path": "artifacts/wp-9947-01/asset_manifest.json",
      "artifact_sha256": "6010cbac3551e3c850bbc15aaf147b3c0a17deba93d8f8879e8f09a54df8ae8a",
      "artifact_bytes": 20269,
      "durable_mirror": "docs/wp-9947-01/asset_manifest.json",
      "schema": "asset_manifest.v1",
      "package_id": "wp-9947-01",
      "task_type": "01-asset-registration",
      "report_id": "9947",
      "source": {
        "uri": "tensor://reports/9947",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "c9857b84a9ea71ea174f3392d34e8e61403202ee154fdab059c4e9abd83fc0bf",
        "chars": 616,
        "bytes_utf8": 855,
        "title": "【试点】技术路线锁定 A/B 终局对照 v1",
        "scenario_key": "pilot-ab",
        "platform_id": 9947,
        "platform_mission_id": null,
        "platform_stage": "S0",
        "platform_status": "published",
        "platform_created_at": "2026-11-09T14:30:57.100885+00:00",
        "platform_title": "【试点】技术路线锁定 A/B 终局对照 v1",
        "platform_summary": "双臂+审查+QR 全终态自动合成；判据盲裁结果与过程指标见表；终裁交 owner。",
        "platform_figures": [],
        "platform_tags": [
          "A/B试点",
          "MethodCommitment",
          "盲裁"
        ],
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/9947",
        "local_copy": "runs/wp-9947-01/report_9947.md"
      },
      "counts": {
        "assets": 12,
        "by_class": {
          "document": 1,
          "heading": 1,
          "external_file_reference": 1,
          "evidence_pointer": 1,
          "model_roster": 1,
          "table_shell": 1,
          "acceptance_criteria": 1,
          "decision_rule": 1,
          "deferred_decision": 1,
          "upstream_report_pointer": 2,
          "figure_slot": 1
        },
        "by_resolution": {
          "resolved_in_source": 7,
          "referenced_unresolved": 4,
          "declared_absent": 1
        },
        "resolved_in_source": 7,
        "referenced_unresolved": 4,
        "declared_absent": 1
      },
      "resolution_semantics": {
        "resolved_in_source": "内容可在源 markdown 内按 [start_char,end_char) 逐字切片，且该切片在全文唯一",
        "referenced_unresolved": "报告只给指针（文件名/路径/键名/scenario_key），未给可校验的 id+哈希组合；本工序只登记指针与探测结果，不断言被指对象的内容身份/版本",
        "declared_absent": "报告与平台元数据均无该资产（此处指图件）"
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "document",
          "label": "报告正文（markdown 全文，616 字符）",
          "in_report_section": "## A/B 试点终局对照（2026-11-09 14:30:57 自动合成）",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 616,
            "start_line": 0,
            "end_line": 14,
            "quote": "## A/B 试点终局对照（2026-11-09 14:30:57 自动合成）\n\nprereg：`/root/tp-agent/pilot_ab_prereg_20261109.md`（sha256 在 GAP-LBM-MCMP-POISEUILLE.evidence，派单前冻结）。\ndev 两臂同模型 qwen3.7-plus；B 审查席=deepseek-v4-flash；QR 两臂=glm-5.2。\n\n| 席位 | 任务 | 终态 | 墙钟 | 摘要 |\n|---|---|---|---|---|\n| a-dev | m- | - |  | - |\n| a-qr | m- | - |  | - |\n| b-dev | m- | - |  | - |\n| b-review | m- | - |  | - |\n| b-qr | m- | - |  | - |\n\n判据三主一加分（①<5% ②<10% ③<0.005·Umax ④趋势）细节见各 QR 报告（scenario_key=pilot-qr-a / pilot-qr-b）；裁决规则按 prereg：QR PASS 数→过程指标→双 FAIL 比根因深度。人工终裁与推广/否决建议交 owner。\n原始证据：pilot-a/b 两臂报告（scenario_key=pilot-arm-a / pilot-arm-b）+B 审查（pilot-ab-review）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "span": [
              0,
              616
            ],
            "quote_occurrences": 1,
            "detail": "re-slice of the fetched markdown at the recorded char span; quote unique in text"
          },
          "note": "整篇 markdown 即源资产本体；sha256 见 source.hash，由平台独立重算比对"
        },
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "报告标题行（自动合成时间戳）",
          "in_report_section": "## A/B 试点终局对照（2026-11-09 14:30:57 自动合成）",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 39,
            "start_line": 0,
            "end_line": 0,
            "quote": "## A/B 试点终局对照（2026-11-09 14:30:57 自动合成）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "span": [
              0,
              39
            ],
            "quote_occurrences": 1,
            "detail": "re-slice of the fetched markdown at the recorded char span; quote unique in text"
          },
          "note": "标题行；与 API title 字段（【试点】技术路线锁定 A/B 终局对照 v1）不同名，属不同层级的标题"
        },
        {
          "asset_id": "A03",
          "asset_class": "external_file_reference",
          "label": "prereg 预注册文件路径（/root/tp-agent/pilot_ab_prereg_20261109.md）",
          "in_report_section": "## A/B 试点终局对照（2026-11-09 14:30:57 自动合成）",
          "locator": {
            "method": "char_span",
            "start_char": 41,
            "end_char": 92,
            "start_line": 2,
            "end_line": 2,
            "quote": "prereg：`/root/tp-agent/pilot_ab_prereg_20261109.md`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "external_address_probe",
            "result": "unresolved",
            "addresses_found": {
              "paths": [
                "/root/tp-agent/pilot_ab_prereg_20261109.md"
              ],
              "urls": [],
              "dois": [],
              "scenario_keys": []
            },
            "identity_binding": "none: the report gives no report_id/sha256 for the referenced object",
            "host_probe": [
              {
                "path": "/root/tp-agent/pilot_ab_prereg_20261109.md",
                "exists_on_host": true,
                "size_bytes": 2567,
                "inside_worktree": false
              }
            ],
            "detail": "路径在宿主上存在与否已实测并记录，但报告未给出该文件的哈希值（推迟到 A04 的 GAP 键），故不对其内容身份作断言"
          },
          "note": "报告给出绝对路径但未给出哈希值本身（哈希被推迟到 GAP-LBM-MCMP-POISEUILLE.evidence），本工序不据路径断言其内容身份"
        },
        {
          "asset_id": "A04",
          "asset_class": "evidence_pointer",
          "label": "GAP 证据键名 GAP-LBM-MCMP-POISEUILLE.evidence",
          "in_report_section": "## A/B 试点终局对照（2026-11-09 14:30:57 自动合成）",
          "locator": {
            "method": "char_span",
            "start_char": 93,
            "end_char": 134,
            "start_line": 2,
            "end_line": 2,
            "quote": "sha256 在 GAP-LBM-MCMP-POISEUILLE.evidence",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "external_address_probe",
            "result": "unresolved",
            "addresses_found": {
              "paths": [],
              "urls": [],
              "dois": [],
              "scenario_keys": []
            },
            "identity_binding": "none: the report gives no report_id/sha256 for the referenced object"
          },
          "note": "仅键名，无 GAP 记录 id / URL / DOI；本工序不猜测地址"
        },
        {
          "asset_id": "A05",
          "asset_class": "model_roster",
          "label": "模型席位配置（dev 双臂 / B 审查席 / QR 双臂）",
          "in_report_section": "## A/B 试点终局对照（2026-11-09 14:30:57 自动合成）",
          "locator": {
            "method": "char_span",
            "start_char": 143,
            "end_char": 204,
            "start_line": 3,
            "end_line": 3,
            "quote": "dev 两臂同模型 qwen3.7-plus；B 审查席=deepseek-v4-flash；QR 两臂=glm-5.2。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "span": [
              143,
              204
            ],
            "quote_occurrences": 1,
            "detail": "re-slice of the fetched markdown at the recorded char span; quote unique in text"
          },
          "note": "三个模型名的原文；属配置声明，不是运行日志"
        },
        {
          "asset_id": "A06",
          "asset_class": "table_shell",
          "label": "五席位终态表（表头+分隔行+5 行，表体为占位符）",
          "in_report_section": "## A/B 试点终局对照（2026-11-09 14:30:57 自动合成）",
          "locator": {
            "method": "char_span",
            "start_char": 206,
            "end_char": 385,
            "start_line": 5,
            "end_line": 11,
            "quote": "| 席位 | 任务 | 终态 | 墙钟 | 摘要 |\n|---|---|---|---|---|\n| a-dev | m- | - |  | - |\n| a-qr | m- | - |  | - |\n| b-dev | m- | - |  | - |\n| b-review | m- | - |  | - |\n| b-qr | m- | - |  | - |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "span": [
              206,
              385
            ],
            "quote_occurrences": 1,
            "detail": "re-slice of the fetched markdown at the recorded char span; quote unique in text"
          },
          "note": "登记的是表格结构与本文字面值：5 行数据的「任务」列均为 m-、「终态」列均为 -、「墙钟」列均为空、「摘要」列均为 -；表内不含任何数值结果（见 notice P1）"
        },
        {
          "asset_id": "A07",
          "asset_class": "acceptance_criteria",
          "label": "判据三主一加分（①<5% ②<10% ③<0.005·Umax ④趋势）",
          "in_report_section": "## A/B 试点终局对照（2026-11-09 14:30:57 自动合成）",
          "locator": {
            "method": "char_span",
            "start_char": 387,
            "end_char": 423,
            "start_line": 13,
            "end_line": 13,
            "quote": "判据三主一加分（①<5% ②<10% ③<0.005·Umax ④趋势）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "span": [
              387,
              423
            ],
            "quote_occurrences": 1,
            "detail": "re-slice of the fetched markdown at the recorded char span; quote unique in text"
          },
          "note": "四条判据与三条阈值以原文数字逐字登记；判据的物理定义（量纲/归一化方式）报告未在本文给出，其细节被指向各 QR 报告"
        },
        {
          "asset_id": "A08",
          "asset_class": "decision_rule",
          "label": "裁决规则（QR PASS 数→过程指标→双 FAIL 比根因深度）",
          "in_report_section": "## A/B 试点终局对照（2026-11-09 14:30:57 自动合成）",
          "locator": {
            "method": "char_span",
            "start_char": 472,
            "end_char": 512,
            "start_line": 13,
            "end_line": 13,
            "quote": "裁决规则按 prereg：QR PASS 数→过程指标→双 FAIL 比根因深度",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "span": [
              472,
              512
            ],
            "quote_occurrences": 1,
            "detail": "re-slice of the fetched markdown at the recorded char span; quote unique in text"
          },
          "note": "规则原文；规则的完整版在 A03 指向的 prereg（未解析）"
        },
        {
          "asset_id": "A09",
          "asset_class": "deferred_decision",
          "label": "人工终裁与推广/否决建议交 owner",
          "in_report_section": "## A/B 试点终局对照（2026-11-09 14:30:57 自动合成）",
          "locator": {
            "method": "char_span",
            "start_char": 513,
            "end_char": 532,
            "start_line": 13,
            "end_line": 13,
            "quote": "人工终裁与推广/否决建议交 owner",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "span": [
              513,
              532
            ],
            "quote_occurrences": 1,
            "detail": "re-slice of the fetched markdown at the recorded char span; quote unique in text"
          },
          "note": "终裁被显式推迟给 owner：本报告不含终裁结论（见 notice P2）"
        },
        {
          "asset_id": "A10",
          "asset_class": "upstream_report_pointer",
          "label": "两臂 QR 报告引用（scenario_key=pilot-qr-a / pilot-qr-b）",
          "in_report_section": "## A/B 试点终局对照（2026-11-09 14:30:57 自动合成）",
          "locator": {
            "method": "char_span",
            "start_char": 434,
            "end_char": 470,
            "start_line": 13,
            "end_line": 13,
            "quote": "scenario_key=pilot-qr-a / pilot-qr-b",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "external_address_probe",
            "result": "unresolved",
            "addresses_found": {
              "paths": [],
              "urls": [],
              "dois": [],
              "scenario_keys": [
                "pilot-qr-a"
              ],
              "probed_keys": [
                "pilot-qr-a",
                "pilot-qr-b"
              ]
            },
            "identity_binding": "none: the report gives no report_id/sha256 for the referenced object",
            "platform_probe": {
              "endpoint": "/tensor/reports?scenario_key=<key>",
              "auth": "bearer",
              "hits": {
                "pilot-qr-a": {
                  "report_ids": [
                    9942
                  ],
                  "count": 1
                },
                "pilot-qr-b": {
                  "report_ids": [
                    9940
                  ],
                  "count": 1
                }
              }
            },
            "detail": "scenario_key 在平台上可命中报告（命中 id 见 platform_probe），但本报告未写明 report_id/版本/哈希，指针→具体版本的绑定关系不由本工序断言"
          },
          "note": "只给 scenario_key，未给 report_id/版本/哈希；判据细节在彼处"
        },
        {
          "asset_id": "A11",
          "asset_class": "upstream_report_pointer",
          "label": "原始证据引用（pilot-arm-a / pilot-arm-b / pilot-ab-review）",
          "in_report_section": "## A/B 试点终局对照（2026-11-09 14:30:57 自动合成）",
          "locator": {
            "method": "char_span",
            "start_char": 534,
            "end_char": 616,
            "start_line": 14,
            "end_line": 14,
            "quote": "原始证据：pilot-a/b 两臂报告（scenario_key=pilot-arm-a / pilot-arm-b）+B 审查（pilot-ab-review）。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "external_address_probe",
            "result": "unresolved",
            "addresses_found": {
              "paths": [],
              "urls": [],
              "dois": [],
              "scenario_keys": [
                "pilot-arm-a"
              ],
              "probed_keys": [
                "pilot-arm-a",
                "pilot-arm-b",
                "pilot-ab-review"
              ]
            },
            "identity_binding": "none: the report gives no report_id/sha256 for the referenced object",
            "platform_probe": {
              "endpoint": "/tensor/reports?scenario_key=<key>",
              "auth": "bearer",
              "hits": {
                "pilot-arm-a": {
                  "report_ids": [
                    9566
                  ],
                  "count": 1
                },
                "pilot-arm-b": {
                  "report_ids": [],
                  "count": 0
                },
                "pilot-ab-review": {
                  "report_ids": [
                    9861
                  ],
                  "count": 1
                }
              }
            },
            "detail": "scenario_key 在平台上可命中报告（命中 id 见 platform_probe），但本报告未写明 report_id/版本/哈希，指针→具体版本的绑定关系不由本工序断言"
          },
          "note": "三个 scenario_key 的字面原文；报告未给出对应 report_id，身份不在此断言"
        },
        {
          "asset_id": "A12",
          "asset_class": "figure_slot",
          "label": "图件：报告无任何图件，平台 figures 字段为空",
          "in_report_section": "## A/B 试点终局对照（2026-11-09 14:30:57 自动合成）",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 616,
            "start_line": 0,
            "end_line": 14,
            "quote": "## A/B 试点终局对照（2026-11-09 14:30:57 自动合成）\n\nprereg：`/root/tp-agent/pilot_ab_prereg_20261109.md`（sha256 在 GAP-LBM-MCMP-POISEUILLE.evidence，派单前冻结）。\ndev 两臂同模型 qwen3.7-plus；B 审查席=deepseek-v4-flash；QR 两臂=glm-5.2。\n\n| 席位 | 任务 | 终态 | 墙钟 | 摘要 |\n|---|---|---|---|---|\n| a-dev | m- | - |  | - |\n| a-qr | m- | - |  | - |\n| b-dev | m- | - |  | - |\n| b-review | m- | - |  | - |\n| b-qr | m- | - |  | - |\n\n判据三主一加分（①<5% ②<10% ③<0.005·Umax ④趋势）细节见各 QR 报告（scenario_key=pilot-qr-a / pilot-qr-b）；裁决规则按 prereg：QR PASS 数→过程指标→双 FAIL 比根因深度。人工终裁与推广/否决建议交 owner。\n原始证据：pilot-a/b 两臂报告（scenario_key=pilot-arm-a / pilot-arm-b）+B 审查（pilot-ab-review）。",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "platform_figures_field+citation_scan",
            "result": "absent",
            "platform_figures_count": 0,
            "image_markdown_refs": 0,
            "detail": "平台 figures 字段为空且正文无图片引用；报告亦无「无图理由」段落，故此资产按「无图」登记"
          },
          "note": "报告全文无「图」声明、无 png/曲线引用，平台 figures=[]；本工序只登记「无图」这一事实，不代替上游生产图件"
        }
      ],
      "claims": [],
      "claims_note": "按工作包契约 objective.classify_report_type=false 且 notes 明确 claims 允许空数组：本工序只登记资产定位与可解析状态，不做 claim 抽取，也不对报告结论表态；claim 抽取归下游工序。资产级 resolution 已为每个条目显式给出。",
      "notices": [
        {
          "id": "P1",
          "scope": "A06",
          "text": "五席位终态表的表体是占位符（任务列 m- / 终态列 - / 墙钟列空 / 摘要列 -），报告标题与平台 summary 所说的「终态/表」在本文中没有数值结果落地",
          "evidence_asset": "A06"
        },
        {
          "id": "P2",
          "scope": "A08,A09",
          "text": "判决与终裁均不在本文：裁决规则被指向 prereg(A03)，人工终裁被显式交 owner(A09)",
          "evidence_asset": "A09"
        },
        {
          "id": "P3",
          "scope": "A10,A11",
          "text": "判据细节与原始证据均以 scenario_key 形式外置（A10/A11），本文自足性不足：不含任何 <5%/<10%/<0.005·Umax 的实测值",
          "evidence_asset": "A11"
        },
        {
          "id": "P4",
          "scope": "A12",
          "text": "全文无图、平台 figures=[]：「终局对照」不含任何对照曲线或场量云图",
          "evidence_asset": "A12"
        },
        {
          "id": "P5",
          "scope": "A10,A11",
          "text": "指针探测：scenario_key pilot-arm-b 在平台 /tensor/reports 查询下命中 0 条（同批其余键各命中 1 条）；本工序只登记「在该查询面下不可见」这一事实，不推断原因是未发布、未生成还是权限不可见",
          "evidence_asset": "A11",
          "probe": {
            "query": "GET /tensor/reports?scenario_key=<key>",
            "zero_hit_keys": [
              "pilot-arm-b"
            ]
          }
        }
      ],
      "integrity": {
        "quote_uniqueness": "每个 char_span 资产的 quote 都是源 markdown 的逐字切片，且全文出现次数==1（scripts/kf_verify_9947.py 在独立进程重取后重切片复核）",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true
      }
    }
  },
  "claims": []
}
```
