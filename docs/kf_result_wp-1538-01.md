# KF-RESULT wp-1538-01

**tags**: kf-wp:wp-1538-01, 01-asset-registration, report:1538, lane:C, draft
**date**: 2026-11-12
**agent**: agent/m15528 · repo: TensorKnowledge · branch: agent/m15528
**source**: `tensor://reports/1538` (field `markdown`, sha256:9d7f968e4c888872eba25bfc190c3e6415e5c7a8f0f4b2733e665181e0d17c85)

---

## 1 本工序做了什么

`wp-1538-01` 是 **01-asset-registration**（资产登记）工序，作用域锁定 `report_id=1538` 一份报告，
目标按契约 notes：**「登记源资产：确认 report_id 与其 markdown 的字节哈希，列出可解析的附件/工件，不做抽取。claims 允许为空数组。」**

本工序交付 5 件事，全部可复跑：

1. **身份核验**：`report_id=1538` 的 markdown 字节哈希独立重算 = 契约声明值（**逐位相同**）。
2. **长度核验**：`chars=9477`（契约）vs 观测 `len(markdown)=9477`，一致；
   另记 utf-8 字节数 `13952` 与行数 `197`（契约未声明，作为补充指纹）。
3. **附件登记**：报告记录 `figures` 中 2 个 PNG 附件登记名称/caption；**二进制未下载**，
   状态如实标 `metadata_only`（不对 PNG 字节作任何断言）。
4. **工件登记**：报告 §7 工件表 9 条路径**程序化抽取**（正则解析表格行，不手打），逐条附原文引文 + 行号，
   并记录登记时点两个检出根的存在性探查结果（9/9 在其声明仓上下文中存在）。
5. **claims=[]**：本工序**不做抽取**，也不把任何结论标成 verified（verification 由平台门计算）。

**明确未做**（防止越界被误读为能力）：不抽取知识对象、不做 report_type 分类、不改写上游产物、
不修改任何其它 report_id、不修正报告正文里的任何数字或证据等级。

## 2 怎么做的（步骤 / 工具 / 关键设置）

| 步 | 动作 | 工具 / 关键设置 |
|---|---|---|
| 1 | 取源报告 | `GET $TENSOR_API_BASE/tensor/reports/1538`（Bearer=登录 token），只取 `markdown` 字段；**只读单报告** |
| 2 | psql 直连尝试 | `psql -d tensorplatform -tA -c "select markdown from tensor_reports where id=1538"` → **被拒**（`permission denied for table tensor_reports`），故全程只用 API 路径 |
| 3 | 独立重算哈希 | `hashlib.sha256(markdown.encode('utf-8')).hexdigest()`，与契约 `source_hash` 比对 |
| 4 | 离线快照 | 把 API 返回的 markdown 原样落 `runs/wp-1538-01/source_1538.md`，再 `sha256sum` 独立复算 → **与契约哈希逐位相同**（两条独立信道互证） |
| 5 | 附件抽取 | 从 record `figures[]` 取 name/caption；文件名在 markdown 中做子串定位（命中则记行号） |
| 6 | 工件抽取 | 正则 `^\|\s*`path`\s*\|\s*(.+?)\s*\|$` 只扫「## 7 工件清单」小节，遇下一个 `## ` 即停 |
| 7 | 零手抄守卫 | 每条引文/路径在写入前断言 `quote in markdown`，未命中即 fail-fast（本次 9/9 命中） |
| 8 | 存在性探查 | 对两个检出根做 `Path.exists()`（**只探存在，不读内容、不写入**）：声明仓上下文 `/root/ship-performance-platform-incoming/ship-performance-platform` 与本草稿检出 TensorKnowledge |
| 9 | 结构门 | `jsonschema.validate(envelope, kf_result.v1.schema.json)` + **反证**（故意缺 `package_id` 必须被判失败，确认 schema 不放水）。本分支树 `schemas/` 未含该 schema 文件，改用同仓兄弟检出副本（sha256 记录在 check_log） |
| 10 | 出图 | matplotlib 150 dpi，两面板：A 工件解析矩阵，B 身份核验条；**图中所有数字均从 manifest 读出**，无手打 |

工具链：Python 3.11 / urllib（仅标准库）/ jsonschema 4.26.0 / matplotlib(Agg) / hashlib。
一键复跑：见文末 `repro_cmd`（幂等，重复跑生成同构 manifest，仅 `generated_at` 时间戳变化）。

## 3 产出物清单

### 3.1 文件 → 要点（含 sha256 指纹）

| 文件 | 要点 | sha256（前 16） |
|---|---|---|
| `artifacts/wp-1538-01/asset_manifest.json` | **主产物**：完整资产清单（report 身份块 / 2 attachments / 9 artifacts / 1 external ref / claims=[] / uncertainties / provenance） | `f3a9dcf00011e4fe` |
| `artifacts/wp-1538-01/kf_result_wp-1538-01.json` | kf_result.v1 结果信封（package_id/task_type/report_id/provenance/outputs/claims） | `bb7c0751ee379fde` |
| `artifacts/wp-1538-01/build_asset_manifest.py` | 可复跑构建器（取数→核验→抽取→探查→组 manifest→结构门→写 check_log） | `53fd7ffc8d56b88c` |
| `artifacts/wp-1538-01/check_log.json` | 15 项核验记录，`all_ok=True` | — |
| `artifacts/wp-1538-01/wp1538_01_manifest_checks.png` | 结果图（见 §4） | `20c84691f59deb6c` |
| `runs/wp-1538-01/source_1538.md` | 源报告 markdown 逐字节快照（离线复算哈希用） | `9d7f968e4c888872` |
| `docs/kf_result_wp-1538-01.md` | 本报告 | — |

### 3.2 工件登记表（路径逐字来自报告 §7，行号为原文行号）

| id | declared_path（引文+行号） | 类型 | 行 | 解析状态 | 命中检出根 |
|---|---|---|---|---|---|
| 1538-art-01 | `artifacts/cii_rating_m1829/probe_cii_regime_m1829.py` (L46) | source_code | L46 | resolved_in_environment | ship_performance_platform_declared_context |
| 1538-art-02 | `artifacts/cii_rating_m1829/probe_result.json` (L189) | machine_output | L189 | resolved_in_environment | ship_performance_platform_declared_context |
| 1538-art-03 | `artifacts/cii_rating_m1829/cii_required_golden.csv` (L190) | dataset | L190 | resolved_in_environment | ship_performance_platform_declared_context |
| 1538-art-04 | `artifacts/cii_rating_m1829/patch_proposal_required_cii.diff` (L134) | patch | L134 | resolved_in_environment | ship_performance_platform_declared_context |
| 1538-art-05 | `artifacts/cii_rating_m1829/fig1_required_cii_regimes.png` (L148) | figure | L148 | resolved_in_environment | ship_performance_platform_declared_context |
| 1538-art-06 | `artifacts/cii_rating_m1829/fig2_legacy_vs_regime.png` (L151) | figure | L151 | resolved_in_environment | ship_performance_platform_declared_context |
| 1538-art-07 | `artifacts/cii_rating_m1829/pytest_summary.txt` (L194) | log | L194 | resolved_in_environment | ship_performance_platform_declared_context |
| 1538-art-08 | `backend/services/cii_required_value.py` (L49) | source_code | L49 | resolved_in_environment | ship_performance_platform_declared_context |
| 1538-art-09 | `tests/test_cii_regime_m1829.py` (L62) | source_code | L62 | resolved_in_environment | ship_performance_platform_declared_context |

### 3.3 附件登记表（record.figures）

| id | name | caption（前 60 字） | 文件名在 markdown | 二进制状态 |
|---|---|---|---|---|
| 1538-att-01 | fig1_required_cii_regimes.png | 遗留 required_cii() 的 required CII 与 Z 随年份曲线（按 regime 分区着色）：20… | 是 L148 | metadata_only |
| 1538-att-02 | fig2_legacy_vs_regime.png | A：遗留实现（实线）与本仓显式 regime 实现（虚线）对照，2023–2026 重合、<2023 虚线中止；B：16… | 是 L151 | metadata_only |

### 3.4 外部引用（不属于 §7 工件表，报告正文点名）

| id | 路径 | 引文定位 | 登记时点存在 |
|---|---|---|---|
| 1538-ext-01 | `/root/tensor-ecosystem/TensorPlatform/backend/services/green_navigation.py` | L6 | True |

## 4 证据定位表（字段 → 原文引文片段）

| 字段 | 值 / 引文（逐字，含行号） | 定位方式 |
|---|---|---|
| report.source_hash（契约 vs 观测） | sha256:9d7f968e4c888872eba25bfc190c3e6415e5c7a8f0f4b2733e665181e0d17c85 | API GET /tensor/reports/1538 → field markdown, sha256(utf-8) |
| report.chars | 9477 chars / 13952 bytes(utf-8) | 同上，len(markdown) 与 len(encode('utf-8')) |
| report.title（平台记录字段） | m1829 · CII 要求值 C1/C2「静默默认」缺陷：定位取证与显式 regime 修复 | record.title（与 markdown H1 措辞不同，见 §5 注意点 2） |
| markdown H1（用于交叉核对标题） | # m1829 · CII 要求值 C1/C2「静默默认」缺陷：定位取证 + 显式 regime 修复（补丁与金标） | markdown 第 1 行 |
| artifact 01..09 路径 | 见 §3.2 表（逐条带行号） | §7 工件清单表，逐行正则抽取 |
| attachment 01/02 文件名 | fig1_required_cii_regimes.png, fig2_legacy_vs_regime.png | record.figures[].name + markdown 子串命中 |
| claims | [] | 契约 notes「不做抽取。claims 允许为空数组」 |

代表性逐字引文（均带行号，可 `sed -n '<L>p' runs/wp-1538-01/source_1538.md` 复核）：

- 工序边界（报告自述交付项）：`本单交付 **①定位取证 ②缺陷实证 ③可直接应用的补丁（干跑验证，不改 TensorPlatform 工作树）` (L8)
- 工件清单小节标题：`## 7 工件清单` (L184)
- 报告对自身证据等级的保留：`**证据等级不升级**` (L168)
- 报告标注的未验证项（本包不越权补验）：`**无基准**（离线不可读原件）` (L179)

### 4.1 结果图

`artifacts/wp-1538-01/wp1538_01_manifest_checks.png`（150 dpi，两面板）：

- **A**：9 个报告声明工件 × 2 个检出根的存在性矩阵。可见同一批工件在其声明仓上下文中 **9/9 存在**、
  在本草稿检出（TensorKnowledge）中 **0/9 不存在** —— 这正是「资产登记必须绑定声明仓上下文」的直接图证。
- **B**：身份核验条 —— 契约 `source_hash`、API 观测 `markdown` sha256、本地快照 sha256 三者**同色（全绿）**，
  即三条独立信道给出同一哈希；旁注 chars/bytes/lines/hash_match 全部一致。

（无场量云图：本工序是资产登记/文档类工序，无任何物理场求解或数值解，故不存在可画的云图或解析解比较曲线；
上图为该工序**真正**的判定依据，不是装饰图。）

## 5 注意点与局限

1. **只 GET 了 id=1538**：单报告作用域；未读/写/覆盖任何其它 report_id，未改上游产物，未把任何结论标 verified。
2. **平台记录 title ≠ markdown H1**：record.title 无后缀，H1 含 `+（补丁与金标）`（H1 见 §4 第 4 行引文）。
   两者都如实登记、不做归一，下游若按标题对齐需注意此差异（契约 title 取的是 record.title）。
3. **附件只有元数据**：2 个 PNG 未下载，`binary_resolution=metadata_only`；因此**没有**对 PNG 字节做存在性/哈希/可解码断言。
   若后续工序需要图片本体，须另走下载通道并在 manifest 增补字节级证据。
4. **工件存在性 ≠ 内容正确性**：9 条 declared_path 在声明仓上下文里存在，仅说明**路径可解析**；
   本包不校验其内容、不校验报告 §3 里的任何数字（那是 03/04 工序与平台门的职责）。
5. **检出根是「登记时点」快照**：`resolution_probes` 记录的是本次登记时刻的存在性；仓被重建/清理后结果可能变化，
   故每条探测都写入了 `abs_path`，可重放。
6. **结构门用了兄弟副本**：本草稿树 `schemas/` 未含 `kf_result.v1.schema.json`，用同仓其它检出副本校验
   （sha256 记在 `check_log.schema_note`）；已加反证（缺 `package_id` 必须被判失败）排除 schema 过宽。
7. **psql 信道不可用**：`tensor_reports` 表对本账号 `permission denied`，故哈希核验走 API + 本地快照两信道，
   而非「API + DB」；这一点已写入 manifest 的 `report.locator.fallback_note`，不假装双库互证。
8. **claims=[] 是契约允许的完整结果**，不是漏做；本工序 task_type 明确禁止抽取。

## 6 自检（逐条对照 acceptance）

| 条件 | 结果 | 依据 |
|---|---|---|
| valid_json | ✓ | 结果 JSON 经 `json.loads` 解析；`check_log.checks[manifest_valid_json]=true` |
| schema_pass | ✓ | `jsonschema.validate` 通过 kf_result.v1；反证（缺 `package_id`）被判失败 |
| source_locator_resolvable | ✓ | `tensor://reports/1538` → `GET /api/v1/tensor/reports/1538` 200，返回 markdown 且哈希吻合 |
| source_hash_matches | ✓ | 契约 `sha256:9d7f968e4c888872eba25bfc190c3e6415e5c7a8f0f4b2733e665181e0d17c85` vs 观测逐位相同（另经本地快照 `sha256sum` 二次独立复算） |
| no_duplicate_ids | ✓ | attachment/artifact id 唯一（2/9），declared_path 无重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✓（空集成立） | `claims=[]`，契约 notes 明示允许；无悬空断言 |

机读明细（15 项，`all_ok=True`）：

| check | ok | detail |
|---|---|---|
| report_id_matches | ✓ | observed id=1538 |
| source_hash_matches | ✓ | observed=sha256:9d7f968e4c888872eba25bfc190c3e6415e5c7a8f0f4b2733e665181e0d17c85 |
| chars_matches | ✓ | observed chars=9477 (契约 9477) |
| bytes_sha256_over_utf8 | ✓ | utf-8 编码后重算一致 |
| title_matches_contract | ✓ | observed title='m1829 · CII 要求值 C1/C2「静默默认」缺陷：定位取证与显式 regime 修复' |
| scenario_key_matches_contract | ✓ | observed scenario_key='green_navigation/cii_required_value' |
| attachments_registered | ✓ | figures=2 |
| artifact_table_parsed | ✓ | rows=9 |
| artifact_locators_exact | ✓ | 9 条路径/描述均为原文逐字子串 |
| no_duplicate_ids | ✓ | attachment/artifact id 与 declared_path 均唯一 |
| external_refs_registered | ✓ | count=1 |
| local_snapshot_byte_identical | ✓ | sha256:9d7f968e4c888872eba25bfc190c3e6415e5c7a8f0f4b2733e665181e0d17c85 |
| manifest_valid_json | ✓ | /root/tp-agent/work/m15528/artifacts/wp-1538-01/asset_manifest.json |
| schema_pass | ✓ | envelope 通过 kf_result.v1.schema.json；反证（缺 package_id）被正确判失败 |
| manifest_schema_pass | ✓ | 必备键齐全=True; report.hash_match=True |

**honest 未完成项（不粉饰）**：PNG 二进制未下载验证（`not_run`）；报告 §3 的数值/证据等级未复核（工序边界外）；
工件内容未校验（只校验路径可解析）。

---

## 结果 JSON（kf_result.v1，唯一 json 块）

```json
{
  "package_id": "wp-1538-01",
  "task_type": "01-asset-registration",
  "report_id": "1538",
  "provenance": {
    "source_uri": "tensor://reports/1538",
    "source_field": "markdown",
    "source_hash": "sha256:9d7f968e4c888872eba25bfc190c3e6415e5c7a8f0f4b2733e665181e0d17c85",
    "producer": "agent/m15528 · wp-1538-01",
    "emitted_at": "2026-11-12T00:52:30+00:00",
    "notes": "01-asset-registration 只登记资产，不做抽取；claims=[] 合法。verification 由平台门计算，本包不自标 verified。",
    "asset_manifest_sha256": "f3a9dcf00011e4fe284a6d693207396656f3b4b1ac2d7bf486c5cf3383b73a06"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-1538-01",
      "task_type": "01-asset-registration",
      "report": {
        "report_id": "1538",
        "source_uri": "tensor://reports/1538",
        "source_field": "markdown",
        "title": "m1829 · CII 要求值 C1/C2「静默默认」缺陷：定位取证与显式 regime 修复",
        "scenario_key": "green_navigation/cii_required_value",
        "platform_mission_id": 1829,
        "platform_status": "published",
        "created_at": "2026-11-02T00:14:11.049862+00:00",
        "chars_declared": 9477,
        "chars_observed": 9477,
        "bytes_utf8_observed": 13952,
        "line_count_observed": 197,
        "source_hash_declared": "sha256:9d7f968e4c888872eba25bfc190c3e6415e5c7a8f0f4b2733e665181e0d17c85",
        "source_hash_observed": "sha256:9d7f968e4c888872eba25bfc190c3e6415e5c7a8f0f4b2733e665181e0d17c85",
        "hash_match": true,
        "hash_algorithm": "sha256 over markdown.encode('utf-8')",
        "locator": {
          "api": "GET http://127.0.0.1:8010/api/v1/tensor/reports/1538 (Bearer, field=markdown)",
          "fallback": "psql -d tensorplatform -tA -c \"select markdown from tensor_reports where id=1538\"",
          "fallback_note": "本次登记中 psql 直连被拒（permission denied for table tensor_reports），仅用 API 路径。"
        }
      },
      "attachments": [
        {
          "attachment_id": "1538-att-01",
          "name": "fig1_required_cii_regimes.png",
          "kind": "figure/png",
          "caption": "遗留 required_cii() 的 required CII 与 Z 随年份曲线（按 regime 分区着色）：2026 之后是无标记平线（C1），2023 之前是无标记 z=0 平线（C2）",
          "locator": {
            "record_field": "figures",
            "index": 0,
            "name": "fig1_required_cii_regimes.png"
          },
          "caption_locator": null,
          "caption_in_markdown": false,
          "name_in_markdown": true,
          "name_locator": {
            "field": "markdown",
            "line": 148
          },
          "caption_markdown_note": "报告记录的 figures[].caption 与 markdown 正文措辞不同（记录版为短摘要）；本包保留记录版原文并标注 caption_in_markdown 结果，不改写为正文措辞。",
          "binary_resolution": "metadata_only",
          "binary_resolution_note": "仅登记报告记录中的 figures 元数据；本包未下载 PNG 二进制，故不对其字节做存在性/哈希断言。"
        },
        {
          "attachment_id": "1538-att-02",
          "name": "fig2_legacy_vs_regime.png",
          "kind": "figure/png",
          "caption": "A：遗留实现（实线）与本仓显式 regime 实现（虚线）对照，2023–2026 重合、<2023 虚线中止；B：16 格独立标量复算相对残差（log 刻度，1e-15 门限）",
          "locator": {
            "record_field": "figures",
            "index": 1,
            "name": "fig2_legacy_vs_regime.png"
          },
          "caption_locator": null,
          "caption_in_markdown": false,
          "name_in_markdown": true,
          "name_locator": {
            "field": "markdown",
            "line": 151
          },
          "caption_markdown_note": "报告记录的 figures[].caption 与 markdown 正文措辞不同（记录版为短摘要）；本包保留记录版原文并标注 caption_in_markdown 结果，不改写为正文措辞。",
          "binary_resolution": "metadata_only",
          "binary_resolution_note": "仅登记报告记录中的 figures 元数据；本包未下载 PNG 二进制，故不对其字节做存在性/哈希断言。"
        }
      ],
      "artifacts": [
        {
          "artifact_id": "1538-art-01",
          "declared_path": "artifacts/cii_rating_m1829/probe_cii_regime_m1829.py",
          "declared_kind": "source_code",
          "declared_content_summary": "定位取证 + 缺陷实证 + 金标 + 补丁干跑 + 出图（可复跑）",
          "locator": {
            "section": "§7 工件清单",
            "table_row_line": 188,
            "path_line": 46,
            "quote": "| `artifacts/cii_rating_m1829/probe_cii_regime_m1829.py` | 定位取证 + 缺陷实证 + 金标 + 补丁干跑 + 出图（可复跑） |"
          },
          "resolution_probes": {
            "ship_performance_platform_declared_context": {
              "root": "/root/ship-performance-platform-incoming/ship-performance-platform",
              "abs_path": "/root/ship-performance-platform-incoming/ship-performance-platform/artifacts/cii_rating_m1829/probe_cii_regime_m1829.py",
              "exists": true
            },
            "this_worktree_TensorKnowledge_m15528": {
              "root": "/root/tp-agent/work/m15528",
              "abs_path": "/root/tp-agent/work/m15528/artifacts/cii_rating_m1829/probe_cii_regime_m1829.py",
              "exists": false
            }
          },
          "resolution_status": "resolved_in_environment",
          "resolution_note": "存在性探查仅针对登记时点可访问的检出根；「未解析」= 本包未在该根下找到，不等于该工件不存在于其生产仓。"
        },
        {
          "artifact_id": "1538-art-02",
          "declared_path": "artifacts/cii_rating_m1829/probe_result.json",
          "declared_kind": "machine_output",
          "declared_content_summary": "机器输出（/root/tensor-ecosystem/TensorPlatform/backend/services/green_navigation.py 的全量取值与判定）",
          "locator": {
            "section": "§7 工件清单",
            "table_row_line": 189,
            "path_line": 189,
            "quote": "| `artifacts/cii_rating_m1829/probe_result.json` | 机器输出（/root/tensor-ecosystem/TensorPlatform/backend/services/green_navigation.py 的全量取值与判定） |"
          },
          "resolution_probes": {
            "ship_performance_platform_declared_context": {
              "root": "/root/ship-performance-platform-incoming/ship-performance-platform",
              "abs_path": "/root/ship-performance-platform-incoming/ship-performance-platform/artifacts/cii_rating_m1829/probe_result.json",
              "exists": true
            },
            "this_worktree_TensorKnowledge_m15528": {
              "root": "/root/tp-agent/work/m15528",
              "abs_path": "/root/tp-agent/work/m15528/artifacts/cii_rating_m1829/probe_result.json",
              "exists": false
            }
          },
          "resolution_status": "resolved_in_environment",
          "resolution_note": "存在性探查仅针对登记时点可访问的检出根；「未解析」= 本包未在该根下找到，不等于该工件不存在于其生产仓。"
        },
        {
          "artifact_id": "1538-art-03",
          "declared_path": "artifacts/cii_rating_m1829/cii_required_golden.csv",
          "declared_kind": "dataset",
          "declared_content_summary": "2023–2026 金标（程序化注入，测试直接读）",
          "locator": {
            "section": "§7 工件清单",
            "table_row_line": 190,
            "path_line": 190,
            "quote": "| `artifacts/cii_rating_m1829/cii_required_golden.csv` | 2023–2026 金标（程序化注入，测试直接读） |"
          },
          "resolution_probes": {
            "ship_performance_platform_declared_context": {
              "root": "/root/ship-performance-platform-incoming/ship-performance-platform",
              "abs_path": "/root/ship-performance-platform-incoming/ship-performance-platform/artifacts/cii_rating_m1829/cii_required_golden.csv",
              "exists": true
            },
            "this_worktree_TensorKnowledge_m15528": {
              "root": "/root/tp-agent/work/m15528",
              "abs_path": "/root/tp-agent/work/m15528/artifacts/cii_rating_m1829/cii_required_golden.csv",
              "exists": false
            }
          },
          "resolution_status": "resolved_in_environment",
          "resolution_note": "存在性探查仅针对登记时点可访问的检出根；「未解析」= 本包未在该根下找到，不等于该工件不存在于其生产仓。"
        },
        {
          "artifact_id": "1538-art-04",
          "declared_path": "artifacts/cii_rating_m1829/patch_proposal_required_cii.diff",
          "declared_kind": "patch",
          "declared_content_summary": "TensorPlatform 侧补丁（未应用，字节级可应用已验证）",
          "locator": {
            "section": "§7 工件清单",
            "table_row_line": 191,
            "path_line": 134,
            "quote": "| `artifacts/cii_rating_m1829/patch_proposal_required_cii.diff` | TensorPlatform 侧补丁（未应用，字节级可应用已验证） |"
          },
          "resolution_probes": {
            "ship_performance_platform_declared_context": {
              "root": "/root/ship-performance-platform-incoming/ship-performance-platform",
              "abs_path": "/root/ship-performance-platform-incoming/ship-performance-platform/artifacts/cii_rating_m1829/patch_proposal_required_cii.diff",
              "exists": true
            },
            "this_worktree_TensorKnowledge_m15528": {
              "root": "/root/tp-agent/work/m15528",
              "abs_path": "/root/tp-agent/work/m15528/artifacts/cii_rating_m1829/patch_proposal_required_cii.diff",
              "exists": false
            }
          },
          "resolution_status": "resolved_in_environment",
          "resolution_note": "存在性探查仅针对登记时点可访问的检出根；「未解析」= 本包未在该根下找到，不等于该工件不存在于其生产仓。"
        },
        {
          "artifact_id": "1538-art-05",
          "declared_path": "artifacts/cii_rating_m1829/fig1_required_cii_regimes.png",
          "declared_kind": "figure",
          "declared_content_summary": "regime 分区曲线图",
          "locator": {
            "section": "§7 工件清单",
            "table_row_line": 192,
            "path_line": 148,
            "quote": "| `artifacts/cii_rating_m1829/fig1_required_cii_regimes.png` | regime 分区曲线图 |"
          },
          "resolution_probes": {
            "ship_performance_platform_declared_context": {
              "root": "/root/ship-performance-platform-incoming/ship-performance-platform",
              "abs_path": "/root/ship-performance-platform-incoming/ship-performance-platform/artifacts/cii_rating_m1829/fig1_required_cii_regimes.png",
              "exists": true
            },
            "this_worktree_TensorKnowledge_m15528": {
              "root": "/root/tp-agent/work/m15528",
              "abs_path": "/root/tp-agent/work/m15528/artifacts/cii_rating_m1829/fig1_required_cii_regimes.png",
              "exists": false
            }
          },
          "resolution_status": "resolved_in_environment",
          "resolution_note": "存在性探查仅针对登记时点可访问的检出根；「未解析」= 本包未在该根下找到，不等于该工件不存在于其生产仓。"
        },
        {
          "artifact_id": "1538-art-06",
          "declared_path": "artifacts/cii_rating_m1829/fig2_legacy_vs_regime.png",
          "declared_kind": "figure",
          "declared_content_summary": "遗留 vs 显式实现对照 + 残差量级",
          "locator": {
            "section": "§7 工件清单",
            "table_row_line": 193,
            "path_line": 151,
            "quote": "| `artifacts/cii_rating_m1829/fig2_legacy_vs_regime.png` | 遗留 vs 显式实现对照 + 残差量级 |"
          },
          "resolution_probes": {
            "ship_performance_platform_declared_context": {
              "root": "/root/ship-performance-platform-incoming/ship-performance-platform",
              "abs_path": "/root/ship-performance-platform-incoming/ship-performance-platform/artifacts/cii_rating_m1829/fig2_legacy_vs_regime.png",
              "exists": true
            },
            "this_worktree_TensorKnowledge_m15528": {
              "root": "/root/tp-agent/work/m15528",
              "abs_path": "/root/tp-agent/work/m15528/artifacts/cii_rating_m1829/fig2_legacy_vs_regime.png",
              "exists": false
            }
          },
          "resolution_status": "resolved_in_environment",
          "resolution_note": "存在性探查仅针对登记时点可访问的检出根；「未解析」= 本包未在该根下找到，不等于该工件不存在于其生产仓。"
        },
        {
          "artifact_id": "1538-art-07",
          "declared_path": "artifacts/cii_rating_m1829/pytest_summary.txt",
          "declared_kind": "log",
          "declared_content_summary": "测试结果",
          "locator": {
            "section": "§7 工件清单",
            "table_row_line": 194,
            "path_line": 194,
            "quote": "| `artifacts/cii_rating_m1829/pytest_summary.txt` | 测试结果 |"
          },
          "resolution_probes": {
            "ship_performance_platform_declared_context": {
              "root": "/root/ship-performance-platform-incoming/ship-performance-platform",
              "abs_path": "/root/ship-performance-platform-incoming/ship-performance-platform/artifacts/cii_rating_m1829/pytest_summary.txt",
              "exists": true
            },
            "this_worktree_TensorKnowledge_m15528": {
              "root": "/root/tp-agent/work/m15528",
              "abs_path": "/root/tp-agent/work/m15528/artifacts/cii_rating_m1829/pytest_summary.txt",
              "exists": false
            }
          },
          "resolution_status": "resolved_in_environment",
          "resolution_note": "存在性探查仅针对登记时点可访问的检出根；「未解析」= 本包未在该根下找到，不等于该工件不存在于其生产仓。"
        },
        {
          "artifact_id": "1538-art-08",
          "declared_path": "backend/services/cii_required_value.py",
          "declared_kind": "source_code",
          "declared_content_summary": "本仓规范实现（显式 regime，禁止静默默认）",
          "locator": {
            "section": "§7 工件清单",
            "table_row_line": 195,
            "path_line": 49,
            "quote": "| `backend/services/cii_required_value.py` | 本仓规范实现（显式 regime，禁止静默默认） |"
          },
          "resolution_probes": {
            "ship_performance_platform_declared_context": {
              "root": "/root/ship-performance-platform-incoming/ship-performance-platform",
              "abs_path": "/root/ship-performance-platform-incoming/ship-performance-platform/backend/services/cii_required_value.py",
              "exists": true
            },
            "this_worktree_TensorKnowledge_m15528": {
              "root": "/root/tp-agent/work/m15528",
              "abs_path": "/root/tp-agent/work/m15528/backend/services/cii_required_value.py",
              "exists": false
            }
          },
          "resolution_status": "resolved_in_environment",
          "resolution_note": "存在性探查仅针对登记时点可访问的检出根；「未解析」= 本包未在该根下找到，不等于该工件不存在于其生产仓。"
        },
        {
          "artifact_id": "1538-art-09",
          "declared_path": "tests/test_cii_regime_m1829.py",
          "declared_kind": "source_code",
          "declared_content_summary": "70 项守卫（C1/C2 正向断言 + 金标回归 + 跨仓守卫）",
          "locator": {
            "section": "§7 工件清单",
            "table_row_line": 196,
            "path_line": 62,
            "quote": "| `tests/test_cii_regime_m1829.py` | 70 项守卫（C1/C2 正向断言 + 金标回归 + 跨仓守卫） |"
          },
          "resolution_probes": {
            "ship_performance_platform_declared_context": {
              "root": "/root/ship-performance-platform-incoming/ship-performance-platform",
              "abs_path": "/root/ship-performance-platform-incoming/ship-performance-platform/tests/test_cii_regime_m1829.py",
              "exists": true
            },
            "this_worktree_TensorKnowledge_m15528": {
              "root": "/root/tp-agent/work/m15528",
              "abs_path": "/root/tp-agent/work/m15528/tests/test_cii_regime_m1829.py",
              "exists": false
            }
          },
          "resolution_status": "resolved_in_environment",
          "resolution_note": "存在性探查仅针对登记时点可访问的检出根；「未解析」= 本包未在该根下找到，不等于该工件不存在于其生产仓。"
        }
      ],
      "external_references": [
        {
          "ref_id": "1538-ext-01",
          "label": "tensorplatform_green_navigation_module",
          "abs_path": "/root/tensor-ecosystem/TensorPlatform/backend/services/green_navigation.py",
          "locator": {
            "field": "markdown",
            "line": 6,
            "quote": "`backend/services/green_navigation.py`"
          },
          "exists_at_registration": true,
          "resolution_note": "仅登记存在性；本包不读取该文件内容、不修改它。"
        }
      ],
      "source_snapshot": {
        "path": "runs/wp-1538-01/source_1538.md",
        "sha256": "sha256:9d7f968e4c888872eba25bfc190c3e6415e5c7a8f0f4b2733e665181e0d17c85",
        "byte_identical_to_api_markdown": true
      },
      "claims": [],
      "claims_note": "本工序 task_type=01-asset-registration，契约 notes 明示「不做抽取。claims 允许为空数组」；故 claims=[]（不是漏登记，也不是把结论标成 verified）。",
      "uncertainties": [
        "附件的 PNG 二进制未下载，仅登记 figures 元数据（binary_resolution=metadata_only）。",
        "工件表路径相对于其生产仓（ship-performance-platform）根；本包未在该仓做权威解析，只记录登记时点两个检出根的存在性探查结果。",
        "报告内的证据等级（如 a/c/Z 转录值的 WITHHELD）与 verification 由平台门计算，本包不复制、不改写、不升级。"
      ],
      "provenance": {
        "generated_by": "agent/m15528 · wp-1538-01",
        "generated_at": "2026-11-12T00:52:30+00:00",
        "builder": "artifacts/wp-1538-01/build_asset_manifest.py",
        "repro_cmd": "TENSOR_API_BASE=$TENSOR_API_BASE TENSOR_AGENT_USER=$TENSOR_AGENT_USER TENSOR_AGENT_PASS=$TENSOR_AGENT_PASS python3 artifacts/wp-1538-01/build_asset_manifest.py"
      }
    }
  },
  "claims": []
}
```

---

**repro_cmd**（在仓库检出根执行；幂等）：

```bash
TENSOR_API_BASE=$TENSOR_API_BASE TENSOR_AGENT_USER=$TENSOR_AGENT_USER \
TENSOR_AGENT_PASS=$TENSOR_AGENT_PASS \
python3 artifacts/wp-1538-01/build_asset_manifest.py \
 && python3 artifacts/wp-1538-01/plot_manifest_checks.py \
 && python3 artifacts/wp-1538-01/build_report.py \
 && python3 - <<'PY'
import json, hashlib
m = json.load(open('artifacts/wp-1538-01/asset_manifest.json'))
e = json.load(open('artifacts/wp-1538-01/kf_result_wp-1538-01.json'))
h = hashlib.sha256(open('runs/wp-1538-01/source_1538.md','rb').read()).hexdigest()
assert m['report']['hash_match'] is True
assert e['provenance']['source_hash'] == 'sha256:' + h, 'source_hash mismatch'
assert m['claims'] == [] and e['claims'] == []
assert e['outputs']['asset_manifest.json'] == m
print('OK  sha256=' + h)
PY
```
