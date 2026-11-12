# KF-RESULT wp-946-01

**工序**：01-asset-registration（资产登记）· **报告**：report_id=946 ·
**仓**：TensorKnowledge · **分支**：agent/m15522 · **状态**：draft（verification 由平台门计算，本单不自评）

## ① 本工序做了什么

对 report_id=946（《AI 原生基础设施演化图 v2（替代报告 941）：十方向 × 六准则可复算覆盖度审计》）**只做资产登记**：确认源资产（该报告 `markdown` 字段）的字节哈希与字符数，然后把正文中以路径 / URL / 端点 / 图件形式出现的附件与工件逐条登记为资产，并标注每条资产「能否在本报告存储中解析」。

不做的事（契约明令）：不抽取知识、不做报告类型分类、不产 claim、不打 verified 标记。`claims` 为空数组（契约 notes 明确允许）。

登记结果：**22 条资产**，其中 **2 条可解析**（源文档本体 + 记录元数据），**20 条仅有引用无字节**（4 张图 + 16 项外部工件/端点/日志/URL，两数由 manifest 计数相减得出）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET http://127.0.0.1:8010/api/v1/tensor/reports/946`（Bearer = 本 agent 账号令牌），落缓存快照 `source/report_946.json`；只读，未写任何其它 report_id。
2. **校验身份**：对 `markdown` 字段的 UTF-8 字节重算 sha256，与契约 `source_hash` 比对；同时比对字符数（契约 `chars=14281`）。结果：`match=True`、`chars match=True`（UTF-8 字节数 26523，二者口径都记下，供门自选）。
3. **定位而不是抄写**：每条资产的引文都由 `str.find` 在 markdown 中定位，`char_start/char_end` 由程序算出，随后断言 `md[start:end] == quote`；脚本对找不到的引文直接 `SystemExit`（防止手抄）。重复出现的引文额外记 `occurrences` 与 `all_char_starts`。
4. **可解析性探测**（只探测、不假设）：图件走 `GET /tensor/reports/946/figures` 与 `/figures/{name}`（均 404），并检查 `record.figures[*]` 的键集合（仅 `name`+`caption`，无内联 base64）；文件类工件（evidence.json / build_evidence.py / 日志 / fleet.json …）在生产方工作树中，本包只登记引用，不声称可解析。
5. **独立校验器**：`validate_asset_manifest.py` 从原始输入重算全部判据（信封 schema、哈希、每条 locator 的 span 与值、计数、重复 id、claim 规则、是否越界碰其它 report_id、是否自评 verified）。
6. **对抗性测试**：`tests/test_kf_wp946_01.py` 对交付物做单点篡改（改引文、挪 span、复制 asset_id、改源 markdown、删 unresolved_reason、置 verified=true、塞无证据 claim、塞 report 941 进 scope、破坏 schema pattern），断言校验器**确实变红**——证明检查是断言不是走过场。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-946-01/asset_manifest.json` | 资产主表：源文档（全文哈希/字符/字节）+ 记录元数据 + 22 条资产，逐条 locator（markdown span 或 record 字段）、`resolvable`/`unresolved_reason`、计数与探测记录 |
| `docs/kf/wp-946-01/kf_result.json` | 结果信封（`package_id/task_type/report_id/provenance/outputs`，`claims: []`），`provenance.source_hash` = 平台独立重算一致的 sha256 |
| `docs/kf/wp-946-01/selfcheck.json` | 校验器机器产出：逐判据 PASS/FAIL + 验证过的 locator 计数 |
| `docs/kf/wp-946-01/build_asset_manifest.py` | 生成器（取原文 / 定位 / 重算哈希 / 写 manifest 与信封） |
| `docs/kf/wp-946-01/validate_asset_manifest.py` | 独立校验器（验收判据逐条重算，可传目录与 schema 参数，供对抗测试复用） |
| `docs/kf/wp-946-01/make_figure.py` | 由 manifest/selfcheck 程序化渲染结果图（数字零手抄） |
| `docs/kf/wp-946-01/figures/fig1_asset_registration.png` | 结果图：按 kind 的资产构成（可解析/未解析）+ 校验面计数（span 核验、record 核验、未解析资产数、failures） |
| `docs/kf/wp-946-01/source/report_946.json` | 报告 946 记录快照（离线复跑与哈希复核用；未改动原文） |
| `docs/kf/wp-946-01/report.md` / `report_payload.json` | 本报告与其 POST 载荷（由本脚本生成） |
| `schemas/kf_result.v1.schema.json` | 结果信封 schema 的只读副本（供本仓离线校验；未经修改） |
| `tests/test_kf_wp946_01.py` | 11 项测试：1 项正例 + 10 项篡改反例 |

## ④ 证据定位表（资产/字段 → 原文引文片段与字符区间）

markdown 定位（每条都已由校验器复核 `md[start:end] == quote`）：

| 资产 / kind | 字符区间 | 原文引文（逐字） |
|---|---|---|
| ast-946-01 / source_document | `0–51` | # AI 原生基础设施演化图 v2 —— 十方向 × 六准则覆盖度审计（返工重发，替代原报告 941） |
| ast-946-03 / figure | `8490–8560` | ![fig1](artifacts/ai-native-infra-v1/figures/fig1_coverage_matrix.png) |
| ast-946-03 / figure | `8395–8486` | 图 1 十方向 × 六准则覆盖度矩阵（左：逐准则 0–3 分；右：总分与强/中/弱带位）。rubric 与判据见方法节，分数由 build_evidence.py 复算，非人工填写。 |
| ast-946-04 / figure | `8645–8721` | ![fig2](artifacts/ai-native-infra-v1/figures/fig2_seat_model_decoupling.png) |
| ast-946-04 / figure | `8564–8641` | 图 2 席位身份与底层模型解耦实测（左：各席位承接任务按模型着色；右：样本规模）。来源：missions 表只读 API 视图 + fleet.json。 |
| ast-946-05 / figure | `8865–8937` | ![fig3](artifacts/ai-native-infra-v1/figures/fig3_selfheal_evidence.png) |
| ast-946-05 / figure | `8725–8861` | 图 3 自愈机制实测证据（左：autoheal 复活事件时间线，逐守护；右：fleet_supervisor 巡检间隔直方图与实测中位）。来源：/var/log/tp-fleet/autoheal.log、/var/log/tp-fleet-supervisor.log。 |
| ast-946-06 / figure | `8998–9065` | ![fig4](artifacts/ai-native-infra-v1/figures/fig4_claim_grades.png) |
| ast-946-06 / figure | `8941–8994` | 图 4 报告断言证据分级（可复算 vs 定性观察）。用于替代自评打分：可复算断言占比即本报告的稳健性下界。 |
| ast-946-07 / asset_dir | `392–421` | artifacts/ai-native-infra-v1/ |
| ast-946-08 / report_generator | `1606–1623` | build_evidence.py |
| ast-946-09 / report_generator | `1665–1679` | make_report.py |
| ast-946-10 / evidence_table | `194–207` | evidence.json |
| ast-946-11 / provenance_check | `9783–9804` | provenance_check.json |
| ast-946-12 / superseded_report_copy | `9863–9884` | report941_original.md |
| ast-946-13 / data_artifact_glob | `9678–9730` | artifacts/ai-native-infra-v1/figures/fig1..fig4*.png |
| ast-946-14 / api_endpoint | `2608–2642` | ${TENSOR_API_BASE}/tensor/missions |
| ast-946-15 / config_file | `2729–2754` | /root/tp-agent/fleet.json |
| ast-946-16 / source_code | `2896–2925` | /root/tp-agent/tp_autoheal.py |
| ast-946-17 / log_file | `2815–2845` | /var/log/tp-fleet/autoheal.log |
| ast-946-18 / log_file | `2994–3026` | /var/log/tp-fleet-supervisor.log |
| ast-946-19 / policy_document | `11681–11709` | 平台运营事件流/DISPOSITION_RULES.md |
| ast-946-20 / external_url | `11870–11978` | https://labs.cloudsecurityalliance.org/research/csa-research-note-nist-ai-agent-standards-regulatory-framewo |
| ast-946-21 / external_url | `11981–12058` | https://datatracker.ietf.org/doc/draft-daniel-ai-agent-internet-architecture/ |
| ast-946-22 / runtime_prerequisite | `14155–14177` | TENSOR_AGENT_USER/PASS |

记录字段定位（`source_field=record`，值直接从记录读出）：

| 资产 / 来源 | 字段 | 值 |
|---|---|---|
| ast-946-02 / record | `id` | 946 |
| ast-946-02 / record | `title` | AI 原生基础设施演化图 v2（替代报告 941）：十方向 × 六准则可复算覆盖度审计 |
| ast-946-02 / record | `scenario_key` | ai-native-infra |
| ast-946-02 / record | `mission_id` | 1237 |
| ast-946-02 / record | `status` | published |
| ast-946-02 / record | `created_by` | 1 |
| ast-946-02 / record | `created_at` | 2026-11-01T02:05:59.106917+00:00 |
| ast-946-02 / record | `tags` | ['AI原生基础设施', '演化图', '覆盖度矩阵', '可复算审计', '证据分级', '返工重发', '引用报告941'] |
| ast-946-03 / record | `figures[0].name` | fig1_coverage_matrix |
| ast-946-03 / record | `figures[0].caption` | 图 1 十方向 × 六准则覆盖度矩阵（左：逐准则 0–3 分；右：总分与强/中/弱带位）。rubric 与判据见方法节，分数由 build_evidence.py 复算，非人工填写。 |
| ast-946-04 / record | `figures[1].name` | fig2_seat_model_decoupling |
| ast-946-04 / record | `figures[1].caption` | 图 2 席位身份与底层模型解耦实测（左：各席位承接任务按模型着色；右：样本规模）。来源：missions 表只读 API 视图 + fleet.json。 |
| ast-946-05 / record | `figures[2].name` | fig3_selfheal_evidence |
| ast-946-05 / record | `figures[2].caption` | 图 3 自愈机制实测证据（左：autoheal 复活事件时间线，逐守护；右：fleet_supervisor 巡检间隔直方图与实测中位）。来源：/var/log/tp-fleet/autoheal.log、/var/log/tp-fleet-supervisor.log。 |
| ast-946-06 / record | `figures[3].name` | fig4_claim_grades |
| ast-946-06 / record | `figures[3].caption` | 图 4 报告断言证据分级（可复算 vs 定性观察）。用于替代自评打分：可复算断言占比即本报告的稳健性下界。 |

## ⑤ 注意点与局限

1. **图件字节缺失（本包最重要的发现）**：`record.figures` 只有 `name`+`caption`，`GET /tensor/reports/946/figures` 与 `/figures/{name}` 均返回 404。因此 4 张图只能登记「引用」而非「内容」——图注可读、像素不可读。产物里 `has_inline_binary=false` 是探测结果，不是推断。
2. **未解析不是失败而是如实**：20 条未解析资产里，`evidence.json` / `build_evidence.py` / `make_report.py` / `provenance_check.json` / `report941_original.md` / 4 张 PNG 都属生产方（mission 1237）工作树，日志与 `fleet.json` 属宿主文件系统，两个 URL 属外部站点。本包只登记引用与出处，不伪造字节、不代写内容。顺带记录：本环境里 `/root/tp-agent/work/m1237/...` 不存在，故这些路径在当前机器上同样不可解析。
3. **外部 URL 在原文中被截断**：CSA 那条 URL 以 `…regulatory-framewo` 结尾后接 ` ; `，按原文登记即为不可直接取回的地址；本包不改写、不补全。
4. **`mission_id` 口径未对齐**：报告记录里 `mission_id=1237`，而工作包契约写 `mission_id: null`。如实记录差异，不擅自裁决（裁决权在平台门）。
5. **`chars` 口径**：契约 `chars=14281` 等于 Unicode 码元数；UTF-8 字节数为 26523。两个口径都写进 manifest，避免门与生成器各说各话。
6. **重复引用未去重为「多资产」**：同一工件（如 `build_evidence.py`）在正文多处出现，本包合并为一条资产并记全部出现位置（`occurrences` / `all_char_starts`），避免制造重复 id；`fig1..fig4*.png` 通配条目与 4 条图件资产并存属「捆绑引用 + 逐件引用」两种粒度，不是重复 id。
7. **本包不做价值判断**：报告内部的数字（42 席 / 995 单 / 31 次 REVIVE / 33.0 s 等）与 rubric 打分**未被本包复核**，它们属于下游抽取/验证工序；本包只证明「这些说法能定位到原文的哪个字符区间」。

8. **未做**：未做报告类型分类（契约 `classify_report_type: false`）；未做 claim 抽取；未核验 `artifacts/` 下任何工件的存在性内容（仅做存在性探测）；未跨仓比对 report 941。

9. **本报告为同包第二次发布（honest 自曝）**：首版 report id 14594 的 ① 节把未解析资产拆成「4 张图 + 17 项外部工件…」，而实际是 4 + 16（算术错误，手写数字未经程序校验）。本版该处改为由 manifest 计数相减注入，结论与资产清单未变。教训：正文里任何数字都不该手写——即便只是拆分项。

## ⑥ 自检：逐条对照 acceptance

| 验收项 | 结论 | 依据（机器产出） |
|---|---|---|
| valid_json | ✅ | 两文件均被校验器解析成功 |
| schema_pass | ✅ | jsonschema 校验 `schemas/kf_result.v1.schema.json` 通过 |
| source_locator_resolvable | ✅ | 25 条 markdown locator（span 逐条 `md[start:end]==quote`）+ 16 条 record locator（字段值重读一致），problems=0 |
| source_hash_matches | ✅ | 重算 `sha256:3ea029afd6df49a8d3e407e42df035654b58a7555f9678d657f5fdfc1fe35552` == 契约 `sha256:3ea029afd6df49a8d3e407e42df035654b58a7555f9678d657f5fdfc1fe35552` |
| no_duplicate_ids | ✅ | duplicate_asset_ids=[] |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims 数 = 0（空数组，契约允许），故无 claim 缺证据 |
| 附加：未自评 verified | ✅ | `verification.performed=false` |
| 附加：只碰 946 | ✅ | `reports_touched=['946']`，交付物中出现的 report_id 集合 = ['946'] |
| 附加：计数自洽 | ✅ | total=22 = resolvable 2 + unresolved 20，by_kind 重算一致 |
| 附加：未解析均有理由 | ✅ | 缺失条数 = 0 |

**失败项：无**（校验器 `failures=[]`）。honest 声明：上表的「通过」只证明**登记面**的正确性（定位可解析、哈希一致、结构合规），不证明报告 946 的科学结论正确——那需要下游抽取与独立验证工序。

## 复现命令（一键）

_one-liner_（`repro_cmd`，在仓库根目录执行；需 `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS` 只读令牌）：

`python3 docs/kf/wp-946-01/build_asset_manifest.py --fetch && python3 docs/kf/wp-946-01/validate_asset_manifest.py && python3 -m pytest tests/test_kf_wp946_01.py -q && python3 docs/kf/wp-946-01/make_figure.py && python3 docs/kf/wp-946-01/make_report.py`

（离线复跑去掉 `--fetch`，脚本读 `source/report_946.json` 快照即可，无需网络。）

## 结果图

![fig1](../figures/fig1_asset_registration.png)

图说明：左图为按 kind 的资产构成（绿色=报告存储内可解析，橙色=仅有引用）；右图为校验面计数——markdown span 核验 25 条、record 字段核验 16 条、无字节资产 20 条，标题行内嵌 `hash match=True`、`failures=0`。全部数字由 `make_figure.py` 从 manifest/selfcheck 读出，非手填。为什么不是物理云图：本工序是资产登记（纯数据/文档类），没有场量与解析解，图表达的是登记与校验的覆盖结构。

## 结果信封（唯一 json 块）

```json
{
  "package_id": "wp-946-01",
  "task_type": "01-asset-registration",
  "report_id": "946",
  "provenance": {
    "source_hash": "sha256:3ea029afd6df49a8d3e407e42df035654b58a7555f9678d657f5fdfc1fe35552",
    "source_field": "markdown",
    "producer": "agent/m15522",
    "emitted_at": "2026-11-12T00:53:23+00:00",
    "notes": "source_hash recomputed from the report 946 markdown bytes fetched over the TensorPlatform API; matches the contract-declared hash"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-946-01",
      "task_type": "01-asset-registration",
      "scope": {
        "report_id": "946",
        "reports_touched": [
          "946"
        ],
        "other_reports_read_or_written": []
      },
      "source": {
        "report_id": "946",
        "source_uri": "tensor://reports/946",
        "source_field": "markdown",
        "title_in_contract": "AI 原生基础设施演化图 v2（替代报告 941）：十方向 × 六准则可复算覆盖度审计",
        "title_in_record": "AI 原生基础设施演化图 v2（替代报告 941）：十方向 × 六准则可复算覆盖度审计",
        "title_match": true,
        "scenario_key": "ai-native-infra",
        "chars": 14281,
        "byte_length_utf8": 26523,
        "sha256": "sha256:3ea029afd6df49a8d3e407e42df035654b58a7555f9678d657f5fdfc1fe35552",
        "retrieval_origin": "cache_snapshot_in_worktree",
        "hash_check": {
          "expected": "sha256:3ea029afd6df49a8d3e407e42df035654b58a7555f9678d657f5fdfc1fe35552",
          "recomputed": "sha256:3ea029afd6df49a8d3e407e42df035654b58a7555f9678d657f5fdfc1fe35552",
          "match": true
        },
        "chars_check": {
          "expected": 14281,
          "observed": 14281,
          "match": true
        }
      },
      "assets": [
        {
          "asset_id": "ast-946-01",
          "kind": "source_document",
          "role": "primary_source",
          "name": "report_946_markdown",
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 0,
              "char_end": 51,
              "quote": "# AI 原生基础设施演化图 v2 —— 十方向 × 六准则覆盖度审计（返工重发，替代原报告 941）",
              "occurrences": 1,
              "note": "first line of markdown; whole-document byte scope is content_ref"
            }
          ],
          "content_ref": {
            "source_uri": "tensor://reports/946",
            "source_field": "markdown",
            "chars": 14281,
            "byte_length_utf8": 26523,
            "sha256": "sha256:3ea029afd6df49a8d3e407e42df035654b58a7555f9678d657f5fdfc1fe35552",
            "record_snapshot": "docs/kf/wp-946-01/source/report_946.json",
            "snapshot_sha256": "sha256:118ee9eb9fa8a3d83cf09014bc964e46e4fe5de9f087a8d93555b9517aa0e001"
          },
          "resolvable": true,
          "resolution": "content_present_in_report_store",
          "status": "resolvable"
        },
        {
          "asset_id": "ast-946-02",
          "kind": "record_metadata",
          "role": "identification",
          "name": "report_946_record",
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "record",
              "field": "id",
              "value": 946
            },
            {
              "source_uri": "tensor://reports/946",
              "source_field": "record",
              "field": "title",
              "value": "AI 原生基础设施演化图 v2（替代报告 941）：十方向 × 六准则可复算覆盖度审计"
            },
            {
              "source_uri": "tensor://reports/946",
              "source_field": "record",
              "field": "scenario_key",
              "value": "ai-native-infra"
            },
            {
              "source_uri": "tensor://reports/946",
              "source_field": "record",
              "field": "mission_id",
              "value": 1237
            },
            {
              "source_uri": "tensor://reports/946",
              "source_field": "record",
              "field": "status",
              "value": "published"
            },
            {
              "source_uri": "tensor://reports/946",
              "source_field": "record",
              "field": "created_by",
              "value": 1
            },
            {
              "source_uri": "tensor://reports/946",
              "source_field": "record",
              "field": "created_at",
              "value": "2026-11-01T02:05:59.106917+00:00"
            },
            {
              "source_uri": "tensor://reports/946",
              "source_field": "record",
              "field": "tags",
              "value": [
                "AI原生基础设施",
                "演化图",
                "覆盖度矩阵",
                "可复算审计",
                "证据分级",
                "返工重发",
                "引用报告941"
              ]
            }
          ],
          "resolvable": true,
          "resolution": "api_tensor_reports_946",
          "status": "resolvable"
        },
        {
          "asset_id": "ast-946-03",
          "kind": "figure",
          "role": "referenced_figure",
          "name": "artifacts/ai-native-infra-v1/figures/fig1_coverage_matrix.png",
          "fig_no": 1,
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 8490,
              "char_end": 8560,
              "quote": "![fig1](artifacts/ai-native-infra-v1/figures/fig1_coverage_matrix.png)",
              "occurrences": 1,
              "note": "markdown image reference to the figure file"
            },
            {
              "source_uri": "tensor://reports/946",
              "source_field": "record",
              "field": "figures[0].name",
              "value": "fig1_coverage_matrix",
              "note": "declared figure identity"
            },
            {
              "source_uri": "tensor://reports/946",
              "source_field": "record",
              "field": "figures[0].caption",
              "value": "图 1 十方向 × 六准则覆盖度矩阵（左：逐准则 0–3 分；右：总分与强/中/弱带位）。rubric 与判据见方法节，分数由 build_evidence.py 复算，非人工填写。",
              "note": "caption text also appears verbatim in the markdown 1 time(s); the markdown occurrence (bold caption line in section 3.6) is where the figure is described"
            },
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 8395,
              "char_end": 8486,
              "quote": "图 1 十方向 × 六准则覆盖度矩阵（左：逐准则 0–3 分；右：总分与强/中/弱带位）。rubric 与判据见方法节，分数由 build_evidence.py 复算，非人工填写。",
              "occurrences": 1,
              "note": "caption body inside the markdown (bold markers excluded)"
            }
          ],
          "content_ref": {
            "declared_name": "fig1_coverage_matrix",
            "declared_fields": [
              "caption",
              "name"
            ],
            "has_inline_binary": false
          },
          "resolvable": false,
          "resolution": "referenced_in_markdown__no_bytes_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "the markdown embeds the figure via a repo-relative path, but report 946 carries no figure bytes: record.figures holds only name+caption and GET /tensor/reports/946/figures returns HTTP 404. Ownership of the PNG lies with the producing worktree, so registration stops at the reference."
        },
        {
          "asset_id": "ast-946-04",
          "kind": "figure",
          "role": "referenced_figure",
          "name": "artifacts/ai-native-infra-v1/figures/fig2_seat_model_decoupling.png",
          "fig_no": 2,
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 8645,
              "char_end": 8721,
              "quote": "![fig2](artifacts/ai-native-infra-v1/figures/fig2_seat_model_decoupling.png)",
              "occurrences": 1,
              "note": "markdown image reference to the figure file"
            },
            {
              "source_uri": "tensor://reports/946",
              "source_field": "record",
              "field": "figures[1].name",
              "value": "fig2_seat_model_decoupling",
              "note": "declared figure identity"
            },
            {
              "source_uri": "tensor://reports/946",
              "source_field": "record",
              "field": "figures[1].caption",
              "value": "图 2 席位身份与底层模型解耦实测（左：各席位承接任务按模型着色；右：样本规模）。来源：missions 表只读 API 视图 + fleet.json。",
              "note": "caption text also appears verbatim in the markdown 1 time(s); the markdown occurrence (bold caption line in section 3.6) is where the figure is described"
            },
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 8564,
              "char_end": 8641,
              "quote": "图 2 席位身份与底层模型解耦实测（左：各席位承接任务按模型着色；右：样本规模）。来源：missions 表只读 API 视图 + fleet.json。",
              "occurrences": 1,
              "note": "caption body inside the markdown (bold markers excluded)"
            }
          ],
          "content_ref": {
            "declared_name": "fig2_seat_model_decoupling",
            "declared_fields": [
              "caption",
              "name"
            ],
            "has_inline_binary": false
          },
          "resolvable": false,
          "resolution": "referenced_in_markdown__no_bytes_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "the markdown embeds the figure via a repo-relative path, but report 946 carries no figure bytes: record.figures holds only name+caption and GET /tensor/reports/946/figures returns HTTP 404. Ownership of the PNG lies with the producing worktree, so registration stops at the reference."
        },
        {
          "asset_id": "ast-946-05",
          "kind": "figure",
          "role": "referenced_figure",
          "name": "artifacts/ai-native-infra-v1/figures/fig3_selfheal_evidence.png",
          "fig_no": 3,
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 8865,
              "char_end": 8937,
              "quote": "![fig3](artifacts/ai-native-infra-v1/figures/fig3_selfheal_evidence.png)",
              "occurrences": 1,
              "note": "markdown image reference to the figure file"
            },
            {
              "source_uri": "tensor://reports/946",
              "source_field": "record",
              "field": "figures[2].name",
              "value": "fig3_selfheal_evidence",
              "note": "declared figure identity"
            },
            {
              "source_uri": "tensor://reports/946",
              "source_field": "record",
              "field": "figures[2].caption",
              "value": "图 3 自愈机制实测证据（左：autoheal 复活事件时间线，逐守护；右：fleet_supervisor 巡检间隔直方图与实测中位）。来源：/var/log/tp-fleet/autoheal.log、/var/log/tp-fleet-supervisor.log。",
              "note": "caption text also appears verbatim in the markdown 1 time(s); the markdown occurrence (bold caption line in section 3.6) is where the figure is described"
            },
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 8725,
              "char_end": 8861,
              "quote": "图 3 自愈机制实测证据（左：autoheal 复活事件时间线，逐守护；右：fleet_supervisor 巡检间隔直方图与实测中位）。来源：/var/log/tp-fleet/autoheal.log、/var/log/tp-fleet-supervisor.log。",
              "occurrences": 1,
              "note": "caption body inside the markdown (bold markers excluded)"
            }
          ],
          "content_ref": {
            "declared_name": "fig3_selfheal_evidence",
            "declared_fields": [
              "caption",
              "name"
            ],
            "has_inline_binary": false
          },
          "resolvable": false,
          "resolution": "referenced_in_markdown__no_bytes_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "the markdown embeds the figure via a repo-relative path, but report 946 carries no figure bytes: record.figures holds only name+caption and GET /tensor/reports/946/figures returns HTTP 404. Ownership of the PNG lies with the producing worktree, so registration stops at the reference."
        },
        {
          "asset_id": "ast-946-06",
          "kind": "figure",
          "role": "referenced_figure",
          "name": "artifacts/ai-native-infra-v1/figures/fig4_claim_grades.png",
          "fig_no": 4,
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 8998,
              "char_end": 9065,
              "quote": "![fig4](artifacts/ai-native-infra-v1/figures/fig4_claim_grades.png)",
              "occurrences": 1,
              "note": "markdown image reference to the figure file"
            },
            {
              "source_uri": "tensor://reports/946",
              "source_field": "record",
              "field": "figures[3].name",
              "value": "fig4_claim_grades",
              "note": "declared figure identity"
            },
            {
              "source_uri": "tensor://reports/946",
              "source_field": "record",
              "field": "figures[3].caption",
              "value": "图 4 报告断言证据分级（可复算 vs 定性观察）。用于替代自评打分：可复算断言占比即本报告的稳健性下界。",
              "note": "caption text also appears verbatim in the markdown 1 time(s); the markdown occurrence (bold caption line in section 3.6) is where the figure is described"
            },
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 8941,
              "char_end": 8994,
              "quote": "图 4 报告断言证据分级（可复算 vs 定性观察）。用于替代自评打分：可复算断言占比即本报告的稳健性下界。",
              "occurrences": 1,
              "note": "caption body inside the markdown (bold markers excluded)"
            }
          ],
          "content_ref": {
            "declared_name": "fig4_claim_grades",
            "declared_fields": [
              "caption",
              "name"
            ],
            "has_inline_binary": false
          },
          "resolvable": false,
          "resolution": "referenced_in_markdown__no_bytes_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "the markdown embeds the figure via a repo-relative path, but report 946 carries no figure bytes: record.figures holds only name+caption and GET /tensor/reports/946/figures returns HTTP 404. Ownership of the PNG lies with the producing worktree, so registration stops at the reference."
        },
        {
          "asset_id": "ast-946-07",
          "kind": "asset_dir",
          "role": "referenced_external_artifact",
          "name": "artifacts/ai-native-infra-v1/",
          "purpose_note": "artifact bundle root of the producing mission (evidence.json + scripts + figures)",
          "purpose_note_source": "package_author_summary__not_a_report_quote",
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 392,
              "char_end": 421,
              "quote": "artifacts/ai-native-infra-v1/",
              "occurrences": 16,
              "all_char_starts": [
                392,
                1577,
                1636,
                8498,
                8653,
                8873,
                9006,
                9387,
                9485,
                9582,
                9678,
                9754,
                9834,
                11395,
                14049,
                14107
              ],
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text but no byte-level copy is attached to report 946; the object lives in the producing mission worktree, on the host filesystem, or on an external site — registration records the reference and does not assert resolvability."
        },
        {
          "asset_id": "ast-946-08",
          "kind": "report_generator",
          "role": "referenced_external_artifact",
          "name": "build_evidence.py",
          "purpose_note": "collector that recomputes evidence.json from API/logs/config and renders figures",
          "purpose_note_source": "package_author_summary__not_a_report_quote",
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 1606,
              "char_end": 1623,
              "quote": "build_evidence.py",
              "occurrences": 7,
              "all_char_starts": [
                1606,
                2297,
                8459,
                9168,
                9514,
                11424,
                14078
              ],
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text but no byte-level copy is attached to report 946; the object lives in the producing mission worktree, on the host filesystem, or on an external site — registration records the reference and does not assert resolvability."
        },
        {
          "asset_id": "ast-946-09",
          "kind": "report_generator",
          "role": "referenced_external_artifact",
          "name": "make_report.py",
          "purpose_note": "renderer that turns evidence.json into report body + POST payload",
          "purpose_note_source": "package_author_summary__not_a_report_quote",
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 1665,
              "char_end": 1679,
              "quote": "make_report.py",
              "occurrences": 3,
              "all_char_starts": [
                1665,
                9611,
                14136
              ],
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text but no byte-level copy is attached to report 946; the object lives in the producing mission worktree, on the host filesystem, or on an external site — registration records the reference and does not assert resolvability."
        },
        {
          "asset_id": "ast-946-10",
          "kind": "evidence_table",
          "role": "referenced_external_artifact",
          "name": "evidence.json",
          "purpose_note": "single numeric source for the whole report",
          "purpose_note_source": "package_author_summary__not_a_report_quote",
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 194,
              "char_end": 207,
              "quote": "evidence.json",
              "occurrences": 6,
              "all_char_starts": [
                194,
                3580,
                9192,
                9416,
                9549,
                9631
              ],
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text but no byte-level copy is attached to report 946; the object lives in the producing mission worktree, on the host filesystem, or on an external site — registration records the reference and does not assert resolvability."
        },
        {
          "asset_id": "ast-946-11",
          "kind": "provenance_check",
          "role": "referenced_external_artifact",
          "name": "provenance_check.json",
          "purpose_note": "independent recomputation results for the three audited numbers",
          "purpose_note_source": "package_author_summary__not_a_report_quote",
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 9783,
              "char_end": 9804,
              "quote": "provenance_check.json",
              "occurrences": 1,
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text but no byte-level copy is attached to report 946; the object lives in the producing mission worktree, on the host filesystem, or on an external site — registration records the reference and does not assert resolvability."
        },
        {
          "asset_id": "ast-946-12",
          "kind": "superseded_report_copy",
          "role": "referenced_external_artifact",
          "name": "report941_original.md",
          "purpose_note": "full text of the superseded report 941, kept for diff",
          "purpose_note_source": "package_author_summary__not_a_report_quote",
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 9863,
              "char_end": 9884,
              "quote": "report941_original.md",
              "occurrences": 1,
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text but no byte-level copy is attached to report 946; the object lives in the producing mission worktree, on the host filesystem, or on an external site — registration records the reference and does not assert resolvability."
        },
        {
          "asset_id": "ast-946-13",
          "kind": "data_artifact_glob",
          "role": "referenced_external_artifact",
          "name": "artifacts/ai-native-infra-v1/figures/fig1..fig4*.png",
          "purpose_note": "the four figure binaries (see figure assets above)",
          "purpose_note_source": "package_author_summary__not_a_report_quote",
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 9678,
              "char_end": 9730,
              "quote": "artifacts/ai-native-infra-v1/figures/fig1..fig4*.png",
              "occurrences": 1,
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text but no byte-level copy is attached to report 946; the object lives in the producing mission worktree, on the host filesystem, or on an external site — registration records the reference and does not assert resolvability."
        },
        {
          "asset_id": "ast-946-14",
          "kind": "api_endpoint",
          "role": "referenced_external_artifact",
          "name": "${TENSOR_API_BASE}/tensor/missions",
          "purpose_note": "missions read-only API view, paged 200x5; source of C1/C2",
          "purpose_note_source": "package_author_summary__not_a_report_quote",
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 2608,
              "char_end": 2642,
              "quote": "${TENSOR_API_BASE}/tensor/missions",
              "occurrences": 1,
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text but no byte-level copy is attached to report 946; the object lives in the producing mission worktree, on the host filesystem, or on an external site — registration records the reference and does not assert resolvability."
        },
        {
          "asset_id": "ast-946-15",
          "kind": "config_file",
          "role": "referenced_external_artifact",
          "name": "/root/tp-agent/fleet.json",
          "purpose_note": "fleet seat configuration, 42 entries",
          "purpose_note_source": "package_author_summary__not_a_report_quote",
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 2729,
              "char_end": 2754,
              "quote": "/root/tp-agent/fleet.json",
              "occurrences": 3,
              "all_char_starts": [
                2729,
                10285,
                11148
              ],
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text but no byte-level copy is attached to report 946; the object lives in the producing mission worktree, on the host filesystem, or on an external site — registration records the reference and does not assert resolvability."
        },
        {
          "asset_id": "ast-946-16",
          "kind": "source_code",
          "role": "referenced_external_artifact",
          "name": "/root/tp-agent/tp_autoheal.py",
          "purpose_note": "CYCLE / COOLDOWN / FLAP_* constants",
          "purpose_note_source": "package_author_summary__not_a_report_quote",
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 2896,
              "char_end": 2925,
              "quote": "/root/tp-agent/tp_autoheal.py",
              "occurrences": 2,
              "all_char_starts": [
                2896,
                10758
              ],
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text but no byte-level copy is attached to report 946; the object lives in the producing mission worktree, on the host filesystem, or on an external site — registration records the reference and does not assert resolvability."
        },
        {
          "asset_id": "ast-946-17",
          "kind": "log_file",
          "role": "referenced_external_artifact",
          "name": "/var/log/tp-fleet/autoheal.log",
          "purpose_note": "REVIVE lines, source of C3/C4",
          "purpose_note_source": "package_author_summary__not_a_report_quote",
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 2815,
              "char_end": 2845,
              "quote": "/var/log/tp-fleet/autoheal.log",
              "occurrences": 4,
              "all_char_starts": [
                2815,
                8797,
                10585,
                10793
              ],
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text but no byte-level copy is attached to report 946; the object lives in the producing mission worktree, on the host filesystem, or on an external site — registration records the reference and does not assert resolvability."
        },
        {
          "asset_id": "ast-946-18",
          "kind": "log_file",
          "role": "referenced_external_artifact",
          "name": "/var/log/tp-fleet-supervisor.log",
          "purpose_note": "patrol lines, source of C5",
          "purpose_note_source": "package_author_summary__not_a_report_quote",
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 2994,
              "char_end": 3026,
              "quote": "/var/log/tp-fleet-supervisor.log",
              "occurrences": 3,
              "all_char_starts": [
                2994,
                8828,
                10979
              ],
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text but no byte-level copy is attached to report 946; the object lives in the producing mission worktree, on the host filesystem, or on an external site — registration records the reference and does not assert resolvability."
        },
        {
          "asset_id": "ast-946-19",
          "kind": "policy_document",
          "role": "referenced_external_artifact",
          "name": "平台运营事件流/DISPOSITION_RULES.md",
          "purpose_note": "human-read discipline surface, source of the qualitative claim C8",
          "purpose_note_source": "package_author_summary__not_a_report_quote",
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 11681,
              "char_end": 11709,
              "quote": "平台运营事件流/DISPOSITION_RULES.md",
              "occurrences": 1,
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text but no byte-level copy is attached to report 946; the object lives in the producing mission worktree, on the host filesystem, or on an external site — registration records the reference and does not assert resolvability."
        },
        {
          "asset_id": "ast-946-20",
          "kind": "external_url",
          "role": "referenced_external_artifact",
          "name": "https://labs.cloudsecurityalliance.org/research/csa-research-note-nist-ai-agent-standards-regulatory-framewo",
          "purpose_note": "CSA research note on NIST AI agent standards (URL appears truncated in the report)",
          "purpose_note_source": "package_author_summary__not_a_report_quote",
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 11870,
              "char_end": 11978,
              "quote": "https://labs.cloudsecurityalliance.org/research/csa-research-note-nist-ai-agent-standards-regulatory-framewo",
              "occurrences": 1,
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text but no byte-level copy is attached to report 946; the object lives in the producing mission worktree, on the host filesystem, or on an external site — registration records the reference and does not assert resolvability."
        },
        {
          "asset_id": "ast-946-21",
          "kind": "external_url",
          "role": "referenced_external_artifact",
          "name": "https://datatracker.ietf.org/doc/draft-daniel-ai-agent-internet-architecture/",
          "purpose_note": "IETF individual draft referenced for the standardization line",
          "purpose_note_source": "package_author_summary__not_a_report_quote",
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 11981,
              "char_end": 12058,
              "quote": "https://datatracker.ietf.org/doc/draft-daniel-ai-agent-internet-architecture/",
              "occurrences": 1,
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text but no byte-level copy is attached to report 946; the object lives in the producing mission worktree, on the host filesystem, or on an external site — registration records the reference and does not assert resolvability."
        },
        {
          "asset_id": "ast-946-22",
          "kind": "runtime_prerequisite",
          "role": "referenced_external_artifact",
          "name": "TENSOR_AGENT_USER/PASS",
          "purpose_note": "environment variables required by the reported repro command",
          "purpose_note_source": "package_author_summary__not_a_report_quote",
          "locators": [
            {
              "source_uri": "tensor://reports/946",
              "source_field": "markdown",
              "char_start": 14155,
              "char_end": 14177,
              "quote": "TENSOR_AGENT_USER/PASS",
              "occurrences": 1,
              "note": "markdown reference to the artifact"
            }
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown__not_present_in_report_store",
          "status": "unresolved",
          "unresolved_reason": "named inside the report text but no byte-level copy is attached to report 946; the object lives in the producing mission worktree, on the host filesystem, or on an external site — registration records the reference and does not assert resolvability."
        }
      ],
      "counts": {
        "total": 22,
        "resolvable": 2,
        "unresolved": 20,
        "by_kind": {
          "source_document": 1,
          "record_metadata": 1,
          "figure": 4,
          "asset_dir": 1,
          "report_generator": 2,
          "evidence_table": 1,
          "provenance_check": 1,
          "superseded_report_copy": 1,
          "data_artifact_glob": 1,
          "api_endpoint": 1,
          "config_file": 1,
          "source_code": 1,
          "log_file": 2,
          "policy_document": 1,
          "external_url": 2,
          "runtime_prerequisite": 1
        },
        "by_status": {
          "resolvable": 2,
          "unresolved": 20
        },
        "duplicate_asset_ids": [],
        "unresolved_without_reason": []
      },
      "extraction": {
        "performed": false,
        "reason": "contract objective is register_assets=true / classify_report_type=false; extraction and report-type classification belong to other work packages"
      },
      "claims_registered": 0,
      "claims_note": "contract note allows claims to be an empty array; this package registers assets only, so no claim objects are emitted and none can be mislabelled as verified",
      "verification": {
        "performed": false,
        "reason": "verification status is computed by the platform gate, never self-assigned"
      },
      "resolvability_probe": {
        "figure_binary_probes": [
          {
            "probe": "GET /api/v1/tensor/reports/946/figures",
            "http_status": 404,
            "observed": "{\"detail\":\"Not Found\"}"
          },
          {
            "probe": "GET /api/v1/tensor/reports/946/figures/fig1_coverage_matrix",
            "http_status": 404,
            "observed": "{\"detail\":\"figure not found\"}"
          },
          {
            "probe": "record.figures[*] key set",
            "http_status": 200,
            "observed": [
              "caption",
              "name"
            ],
            "interpretation": "name+caption only, no inline base64 payload"
          }
        ],
        "record_key_set": [
          "created_at",
          "created_by",
          "figures",
          "id",
          "markdown",
          "mission_id",
          "scenario_key",
          "stage",
          "status",
          "summary",
          "tags",
          "title"
        ],
        "producing_worktree_probe": {
          "path_checked": "/root/tp-agent/work/m1237/artifacts/ai-native-infra-v1/",
          "exists": false,
          "note": "read-only existence check only, used to explain why referenced paths cannot be resolved here; no content was read and this is outside the report store, so it is NOT evidence for any asset"
        }
      },
      "notes": [
        "report 946 record.mission_id=1237 while the package contract declares mission_id: null; recorded as observed, not reconciled by this package",
        "contract chars=14281 matches len(markdown) in Unicode code points; the UTF-8 byte length is 26523 — both are recorded so the gate can pick its own convention",
        "the CSA URL in the markdown is truncated mid-path ('...regulatory-framewo' followed by ' ; '), so that locator resolves to a non-fetchable URL as written; registered as-is, not repaired",
        "no fenced code block exists in the markdown, so no code artifact is registered from fences"
      ]
    }
  },
  "claims": []
}
```
