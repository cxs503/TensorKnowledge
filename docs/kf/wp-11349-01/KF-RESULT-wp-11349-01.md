# KF-RESULT wp-11349-01

**工作包** `wp-11349-01` · **task_type** `01-asset-registration` · **lane** C ·
**report_id** `11349` · **source** `tensor://reports/11349` (`markdown`) ·
**repo** TensorKnowledge (`a7fdcb80`, `agent/m15696`)

## ① 本工序做了什么

只做工序 01（资产登记），对 `report_id=11349` 这一份报告：把报告 markdown 的字节哈希钉到契约值，
把报告引用的工件（源文件 / 符号 / HTTP 端点 / 回归测试 / 跨报告引用 / 报告内证据表）逐条登记成
`asset_manifest.json`，每条带一个逐字可复算的定位器。**不做抽取**（`claims` 为空数组）、
**不做报告类型分类**（`objective.classify_report_type=false`）、**不打 verified 戳**
（`integrity.verified=false`，verification 由平台门计算）。产线边界：本包只读写 `report_id=11349`。

登记结果：**11 条资产**，其中 `resolved_in_source` = 2（报告本体 + 报告内探针表），
`referenced_unresolved` = 9（目标在他仓/线上/另一份报告，**只登记引用与定位，不解引用**），
`declared_absent` = 0。`claims` = 0 条。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`GET $TENSOR_API_BASE/tensor/reports/11349`（`/auth/login` 拿 token），取 `markdown` 字段；
   落字节快照 `source/report_11349.md`，元数据落 `source/record_11349.json`。
2. **哈希钉扎**：`sha256(markdown.encode('utf-8'))` = `e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80`，与契约 `source_hash` 逐字比对；
   另对快照文件本体再算一次文件哈希（e1dbc9395d11c8d9…），两者必须同时相等。
3. **枚举资产**：人工从源文逐句读出被引用的工件（不凭记忆：每条锚点字符串先断言 `anchor in markdown`），
   分 7 类登记：`report_document` / `source_file` / `source_symbol` / `api_endpoint` / `test_case` /
   `cross_report_reference` / `evidence_table`。
4. **定位器生成**：锚点在源内多次出现时，向左右扩窗直到 `markdown.count(quote) == 1`；
   记录 `start_char/end_char`（0 基、闭开区间）+ `start_line/end_line`（1 基，由字符下标重算）。
5. **可解析性判定**：文件/符号/测试条目在**本工作树**（TensorKnowledge）内用 `os.path.exists` + `grep -rIl` 探测；
   不在本仓的按 `referenced_unresolved` 登记（不复制他仓代码、不改他仓）。跨报告引用 `id=11344` 按产线边界**不解引用**。
6. **独立复核**：`scripts/kf/wp11349_01_check.py` 重读磁盘产物，重切片每条 locator、重算每个哈希、
   对 `kf_result` 走仓内 canonical `schemas/kf_result.v1.schema.json`、对 manifest 走 package-pinned
   `asset_manifest.schema.json`，结果写 `self_check.json`（10/10 项通过）。

关键设置：`hash_basis = "UTF-8 bytes of the markdown field as served by the platform"`；
定位器区间 `method ∈ {char_span, document}`；`claims=[]` 是**合法完整结果**，不为填指标而造知识。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `asset_manifest.json` | 11 条资产清单：label + 分类 + 逐字 quote + 字符/行级 locator + resolution + 可解析性检查记录；含 `counts`/`integrity`/`locator_convention`/`scope_statement` |
| `kf_result.json` | `kf_result.v1` 信封：`package_id/task_type/report_id/provenance/outputs/claims`，`outputs["asset_manifest.json"]` 内嵌同一清单，`claims=[]` |
| `asset_manifest.schema.json` | 本包钉扎版 schema（仓内 `schemas/asset_manifest.v1.schema.json` 的 consts 写死为 wp-448-01，不可复用），把 `package_id/report_id/source_hash/chars/title` 均设 const |
| `self_check.json` | 10/10 项通过 的逐项判据 + 三件产物 sha256 + `not_run` 清单 |
| `source/report_11349.md` | 报告 `markdown` 字节快照（复跑用，哈希 = 契约值） |
| `source/record_11349.json` | 平台 record 元数据（title/scenario_key/status/mission/tags/figures） |
| `fig_asset_inventory.png` | 资产分类与可解析性统计图（由 manifest 程序化生成） |
| `KF-RESULT-wp-11349-01.md` | 本报告 |
| `scripts/kf/wp11349_01_register.py` | 取源 + 哈希钉扎 + 清单生成（锚点先断言存在，再扩窗到唯一） |
| `scripts/kf/wp11349_01_check.py` | 独立复核器：重切片 locator / 重算哈希 / 双 schema 校验 → `self_check.json` |
| `scripts/kf/wp11349_01_report.py` | 由产物程序化渲染本报告与统计图（零手抄） |
| `tests/test_kf_wp11349_01.py` | 9 项回归：哈希钉扎、双 schema、locator 逐条重切片、id 唯一、claims 契约、无 verified 戳、报告信封块唯一且等于 kf_result |

## ④ 证据定位表（字段 → 原文引文，逐字，可从快照复算）

源：`tensor://reports/11349#markdown`，sha256 = `e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80`。

| 资产 · 类别 | 行 | 字符区间 | 可解析性 | 原文引文（逐字） |
|---|---|---|---|---|
| `A00` · report_document | 1-32 | 0-1029 | resolved_in_source | `# P266W1-N10 补记：能力台账路由接线缺陷修复` |
| `A01` · source_file | 5-5 | 46-77 | referenced_unresolved | `backend/api/capability_audit.py` |
| `A02` · source_file | 6-6 | 155-196 | referenced_unresolved | `` `backend/main.py` **从未 include 该 router** `` |
| `A03` · source_symbol | 23-23 | 661-688 | referenced_unresolved | `api.capability_audit.router` |
| `A04` · source_symbol | 23-23 | 698-729 | referenced_unresolved | `api.capability_semantics.router` |
| `A05` · api_endpoint | 5-5 | 93-125 | referenced_unresolved | `` `GET /tensor/capabilities/audit` `` |
| `A06` · api_endpoint | 6-6 | 129-143 | referenced_unresolved | `/audit/summary` |
| `A07` · api_endpoint | 15-15 | 420-457 | referenced_unresolved | `/api/v1/tensor/capabilities/semantics` |
| `A08` · test_case | 26-26 | 805-882 | referenced_unresolved | `test_capability_semantics_api.py::test_routers_wired_in_main_and_route_shapes` |
| `A09` · cross_report_reference | 32-32 | 1011-1019 | referenced_unresolved | `id=11344` |
| `A10` · evidence_table | 11-15 | 245-491 | resolved_in_source | \| 请求 \| 结果 \| ⏎ \|---\|---\| ⏎ \| `GET /api/v1/tensor/capabilities/audit`（无 token） \| 401（auth 中间件先于路由） \| ⏎ \| `GET /api/v1/t… |

字段级证据：`source.hash` ← 平台重算 `e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80`（= 契约值）；`source.chars` ← 1029（= 契约 1029）；
`source.title` ← record `title`（与契约标题一致：True）；
`source.scenario_key` ← `platform_governance_capability_ledger_semantics`。
`claims` 为空数组，故本表不承担 claim→引文映射，只承担**资产→引文**映射（工序 01 的判据面）。

## ⑤ 注意点与局限

- **9/11 条资产是 `referenced_unresolved`，这是本工序的性质而非缺陷**：报告主体讲的是
  TensorPlatform 仓（`backend/main.py`、`backend/api/capability_audit.py`、`backend/tests/...`）与线上 :8010 端点，
  这些目标不在本工作树（TensorKnowledge）内。登记 ≠ 解引用：本包**不复制他仓代码、不重放线上探针、不执行他仓测试**，
  因此报告关于「router 未 include → 404」的结论在本包内**未经独立核验**，只能作为报告所载内容引用。
- **未跑的检查**（`self_check.json.not_run` 亦记录）：线上探针未重放（工序 01 不做执行）；他仓 10 项测试未执行；
  `report_id=11344`（主报告）未解引用——产线边界只允许碰 11349，故其状态为「未解」而非「通过」。
- **`quote` 是被扩窗到唯一的那一段**，可能带上下文（如 `A02` 的窗口带上了「从未 include 该 router」这句缺陷陈述）。
  扩窗只为定位唯一性，不构成抽取；引用时请以 locator 区间为准。
- **单点快照**：哈希钉扎的是本次取到的 markdown 字节；若上游此后编辑该报告，`source_hash_matches` 会变红，
  那时必须重跑本工序而不是复用本清单。
- 精度/误差判定（报告纪律 ⑥ 的「是否 <3%」）对本工序**不适用**：工序 01 不产生任何物理量或数值结果，
  唯一可比对的数是 `chars` 与 `sha256`，且是**精确相等**判据（`chars` 1029 vs 契约 1029：相等；
  hash 64/64 位相等），不存在容差带宽，故无 <3% 之说。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 判据（来自 self_check.json） |
|---|---|---|
| valid_json | ✅ pass | asset_manifest.json + kf_result.json 均被 json 解析成功 |
| source_hash_matches | ✅ pass | recomputed(utf-8)=e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80 · snapshot_file=e1dbc9395d11c8d953075 |
| schema_pass | ✅ pass | kf_result 通过 schemas/kf_result.v1.schema.json | manifest 通过 package-pinned asset_manifest.v1 (wp-11349-01) |
| source_locator_resolvable | ✅ pass | 11 条 locator 全部重切片校验 |
| no_duplicate_ids | ✅ pass | 11 条 asset_id 唯一（A00..A10），counts.assets=11 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ pass | claims=0 条（契约允许为空数组；本包 objective.classify_report_type=false，故为 0 条，本条为空真通过） |
| envelope_matches_on_disk_manifest | ✅ pass | kf_result.outputs['asset_manifest.json'] 与磁盘 asset_manifest.json 逐字段相同 |
| report_identity_matches_contract | ✅ pass | report_id=11349 package_id=wp-11349-01 task_type=01-asset-registration |
| no_verified_stamp | ✅ pass | 全树扫描 verified=true / verification_stamp：无命中（integrity.verified=false，verification 交平台门计算） |
| contract_chars_match | ✅ pass | chars=1029 vs 契约 1029 |

**是否 <3%**：不适用（本工序零数值结果；可比的只有 `chars` 与 `sha256`，均为精确相等判据，实测相等）。
**honest 声明**：以上 10/10 项通过 只覆盖工序 01 的 acceptance；它**不**代表报告结论（capability_audit 路由缺陷）
已被验证——那一层由平台门在合并/部署后计算，本包无权代劳，也未代劳。

## 复跑（一键）

```
cd <worktree-root> && python3 scripts/kf/wp11349_01_register.py && python3 scripts/kf/wp11349_01_check.py && python3 scripts/kf/wp11349_01_report.py && python3 -m pytest tests/test_kf_wp11349_01.py -q
```

实测：`pytest tests/test_kf_wp11349_01.py -q` → **9 passed**；`wp11349_01_check.py` → **10/10 pass**。

## 结果信封（kf_result.v1）

```json
{
  "package_id": "wp-11349-01",
  "task_type": "01-asset-registration",
  "report_id": "11349",
  "provenance": {
    "source_hash": "sha256:e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80",
    "source_field": "markdown",
    "source_uri": "tensor://reports/11349",
    "producer": "agent/m15696 (TensorKnowledge) · package wp-11349-01",
    "emitted_at": "2026-11-12T01:50:38+00:00",
    "notes": "01-asset-registration: hash-pinned inventory of report 11349; claims intentionally empty; no extraction, no report_type classification, no verification stamp"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "manifest_version": "1.0",
      "package_id": "wp-11349-01",
      "task_type": "01-asset-registration",
      "report_id": "11349",
      "objective": {
        "register_assets": true,
        "classify_report_type": false
      },
      "generated_at": "2026-11-12T01:50:38+00:00",
      "source": {
        "uri": "tensor://reports/11349",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80",
        "chars": 1029,
        "bytes_utf8": 1657,
        "lines": 32,
        "title": "P266W1-N10 补记：能力台账 API 接线缺陷修复（capability_audit 路由 404）",
        "record_title": "P266W1-N10 补记：能力台账 API 接线缺陷修复（capability_audit 路由 404）",
        "scenario_key": "platform_governance_capability_ledger_semantics",
        "record_scenario_key": "platform_governance_capability_ledger_semantics",
        "record_status": "published",
        "record_mission_id": 9561,
        "record_created_at": "2026-11-10T13:05:50.625915+00:00",
        "record_tags": [
          "API接线",
          "能力台账",
          "缺陷修复",
          "探针方法学"
        ],
        "platform_figures": [
          {
            "name": "fig2_tier_coverage_and_misuse.png",
            "caption": "图（沿用主报告）：误用治理修复前后对照"
          }
        ],
        "fetched_via": "byte snapshot (docs/kf/wp-11349-01/source/report_11349.md)"
      },
      "provenance": {
        "source_uri": "tensor://reports/11349",
        "source_field": "markdown",
        "source_hash": "sha256:e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80",
        "contract_source_hash": "sha256:e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80",
        "source_hash_matches_contract": true,
        "contract_chars": 1029,
        "contract_title": "P266W1-N10 补记：能力台账 API 接线缺陷修复（capability_audit 路由 404）",
        "title_matches_contract": true,
        "hashed_bytes": "markdown encoded as utf-8",
        "worktree_repo": "TensorKnowledge",
        "worktree_head": "a7fdcb80233a5ec32def8c02027c1702c81342a4",
        "worktree_branch": "agent/m15696",
        "generator": "scripts/kf/wp11349_01_register.py",
        "contract_version": "1.0"
      },
      "resolution_vocabulary": {
        "resolved_in_source": "字节/引文在报告 markdown 内逐字定位（本包唯一可自证的一类）",
        "referenced_unresolved": "报告引用的目标在本包作用域外（他仓文件/线上端点/跨报告），只登记定位，不解引用、不判真伪",
        "declared_absent": "报告声明存在的产物在源内不存在（本报告无此情形，故计数为 0）"
      },
      "locator_convention": {
        "char_span": "start_char/end_char 为 UTF-8 解码后 markdown 字符串的字符下标，md[start_char:end_char] == quote 逐字成立",
        "document": "method=document 的条目（仅 A00 本体）跨越整篇 [0, len)；其 quote 取首行标题，字节完整性由 sha256 而非切片保证",
        "widening": "若锚点字符串在源内多次出现，则向左右扩窗直到 quote 唯一；因此 quote 可能含有锚点之外的上下文语境，只作定位用，不构成抽取",
        "line_numbers": "start_line/end_line 为 1 基行号，由字符下标重算"
      },
      "structure_index": {
        "note": "仅标题行与字符偏移，作为下游工序的定位脚手架；不抽取任何内容",
        "headings": [
          {
            "level": 1,
            "text": "P266W1-N10 补记：能力台账路由接线缺陷修复",
            "line_no": 1
          },
          {
            "level": 2,
            "text": "发现的缺陷（可复现）",
            "line_no": 3
          },
          {
            "level": 2,
            "text": "修复",
            "line_no": 20
          },
          {
            "level": 2,
            "text": "局限",
            "line_no": 29
          }
        ]
      },
      "counts": {
        "assets": 11,
        "by_class": {
          "report_document": 1,
          "source_file": 2,
          "source_symbol": 2,
          "api_endpoint": 3,
          "test_case": 1,
          "cross_report_reference": 1,
          "evidence_table": 1
        },
        "by_resolution": {
          "resolved_in_source": 2,
          "referenced_unresolved": 9
        },
        "resolved_in_source": 2,
        "referenced_unresolved": 9,
        "declared_absent": 0,
        "claims": 0
      },
      "assets": [
        {
          "asset_id": "A00",
          "asset_class": "report_document",
          "kind": "report_document",
          "label": "报告正文 markdown（11349，来源资产本体）",
          "in_report_section": "P266W1-N10 补记：能力台账路由接线缺陷修复",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 1029,
            "start_line": 1,
            "end_line": 32,
            "quote": "# P266W1-N10 补记：能力台账路由接线缺陷修复",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256(utf-8 bytes) == contract source_hash",
            "result": "resolved"
          },
          "note": "字节哈希已钉扎；本条为本工序的被登记对象本体。",
          "quote_verbatim_in_markdown": true
        },
        {
          "asset_id": "A01",
          "asset_class": "source_file",
          "kind": "source_file_under_review",
          "label": "backend/api/capability_audit.py（缺陷所在的 21 能力证据等级矩阵端点模块）",
          "in_report_section": "发现的缺陷（可复现）",
          "locator": {
            "method": "char_span",
            "start_char": 46,
            "end_char": 77,
            "start_line": 5,
            "end_line": 5,
            "quote": "backend/api/capability_audit.py",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists(worktree/rel) + grep -rIl rel in TensorKnowledge@a7fdcb80 (grep hits=6, exists=False)",
            "result": "unresolved"
          },
          "note": "属 TensorPlatform 仓，不在本工作树（TensorKnowledge）内 → 本包只登记引用与定位，不解引用、不复制代码。",
          "quote_verbatim_in_markdown": true
        },
        {
          "asset_id": "A02",
          "asset_class": "source_file",
          "kind": "source_file_under_review",
          "label": "backend/main.py（未 include router 的装配点）",
          "in_report_section": "发现的缺陷（可复现）",
          "locator": {
            "method": "char_span",
            "start_char": 155,
            "end_char": 196,
            "start_line": 6,
            "end_line": 6,
            "quote": "`backend/main.py` **从未 include 该 router**",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists(worktree/rel) + grep -rIl rel in TensorKnowledge@a7fdcb80 (grep hits=0, exists=False)",
            "result": "unresolved"
          },
          "note": "同上。quote 因唯一性扩窗而带上了报告对它的缺陷陈述（未 include）；该陈述属报告结论，本包只登记位置，不重算、不判真伪。",
          "quote_verbatim_in_markdown": true
        },
        {
          "asset_id": "A03",
          "asset_class": "source_symbol",
          "kind": "router_symbol",
          "label": "api.capability_audit.router（待挂载的 APIRouter 对象）",
          "in_report_section": "修复",
          "locator": {
            "method": "char_span",
            "start_char": 661,
            "end_char": 688,
            "start_line": 23,
            "end_line": 23,
            "quote": "api.capability_audit.router",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists(worktree/rel) + grep -rIl rel in TensorKnowledge@a7fdcb80 (grep hits=0, exists=False)",
            "result": "unresolved"
          },
          "note": "符号级引用；所在模块在 TensorPlatform 仓。",
          "quote_verbatim_in_markdown": true
        },
        {
          "asset_id": "A04",
          "asset_class": "source_symbol",
          "kind": "router_symbol",
          "label": "api.capability_semantics.router（本次并列新建的 router）",
          "in_report_section": "修复",
          "locator": {
            "method": "char_span",
            "start_char": 698,
            "end_char": 729,
            "start_line": 23,
            "end_line": 23,
            "quote": "api.capability_semantics.router",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists(worktree/rel) + grep -rIl rel in TensorKnowledge@a7fdcb80 (grep hits=0, exists=False)",
            "result": "unresolved"
          },
          "note": "符号级引用；所在模块在 TensorPlatform 仓。",
          "quote_verbatim_in_markdown": true
        },
        {
          "asset_id": "A05",
          "asset_class": "api_endpoint",
          "kind": "http_endpoint",
          "label": "GET /tensor/capabilities/audit（21 能力证据矩阵端点，缺陷路径）",
          "in_report_section": "发现的缺陷（可复现）",
          "locator": {
            "method": "char_span",
            "start_char": 93,
            "end_char": 125,
            "start_line": 5,
            "end_line": 5,
            "quote": "`GET /tensor/capabilities/audit`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists(worktree/rel) + grep -rIl rel in TensorKnowledge@a7fdcb80 (grep hits=4, exists=False)",
            "result": "unresolved"
          },
          "note": "线上 :8010 的服务端点，非本仓文件资产；本工序不做执行/重放探针。",
          "quote_verbatim_in_markdown": true
        },
        {
          "asset_id": "A06",
          "asset_class": "api_endpoint",
          "kind": "http_endpoint",
          "label": "/audit/summary（同一 router 的汇总子路径）",
          "in_report_section": "发现的缺陷（可复现）",
          "locator": {
            "method": "char_span",
            "start_char": 129,
            "end_char": 143,
            "start_line": 6,
            "end_line": 6,
            "quote": "/audit/summary",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists(worktree/rel) + grep -rIl rel in TensorKnowledge@a7fdcb80 (grep hits=4, exists=False)",
            "result": "unresolved"
          },
          "note": "与 A05 同 router 的另一端点；仅引用登记。",
          "quote_verbatim_in_markdown": true
        },
        {
          "asset_id": "A07",
          "asset_class": "api_endpoint",
          "kind": "http_endpoint",
          "label": "GET /api/v1/tensor/capabilities/semantics（新端点，分支未部署）",
          "in_report_section": "发现的缺陷（可复现）",
          "locator": {
            "method": "char_span",
            "start_char": 420,
            "end_char": 457,
            "start_line": 15,
            "end_line": 15,
            "quote": "/api/v1/tensor/capabilities/semantics",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists(worktree/rel) + grep -rIl rel in TensorKnowledge@a7fdcb80 (grep hits=4, exists=False)",
            "result": "unresolved"
          },
          "note": "报告记录其带 token 探针结果为 404；本包不重放。",
          "quote_verbatim_in_markdown": true
        },
        {
          "asset_id": "A08",
          "asset_class": "test_case",
          "kind": "regression_test",
          "label": "backend/tests/test_capability_semantics_api.py::test_routers_wired_in_main_and_route_shapes（源码级接线回归）",
          "in_report_section": "修复",
          "locator": {
            "method": "char_span",
            "start_char": 805,
            "end_char": 882,
            "start_line": 26,
            "end_line": 26,
            "quote": "test_capability_semantics_api.py::test_routers_wired_in_main_and_route_shapes",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists(worktree/rel) + grep -rIl rel in TensorKnowledge@a7fdcb80 (grep hits=4, exists=False)",
            "result": "unresolved"
          },
          "note": "测试文件在 TensorPlatform 仓；本仓无法执行该测试，故只登记不判绿。",
          "quote_verbatim_in_markdown": true
        },
        {
          "asset_id": "A09",
          "asset_class": "cross_report_reference",
          "kind": "report_cross_reference",
          "label": "主报告 id=11344（本补记不改变其判据数字）",
          "in_report_section": "局限",
          "locator": {
            "method": "char_span",
            "start_char": 1011,
            "end_char": 1019,
            "start_line": 32,
            "end_line": 32,
            "quote": "id=11344",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists(worktree/rel) + grep -rIl rel in TensorKnowledge@a7fdcb80 (grep hits=0, exists=False)",
            "result": "unresolved"
          },
          "note": "跨报告引用。按产线边界（只碰 report_id=11349）本包**不解引用** 11344，故其存在性与内容状态为未解，不可判 verified。",
          "quote_verbatim_in_markdown": true
        },
        {
          "asset_id": "A10",
          "asset_class": "evidence_table",
          "kind": "in_report_probe_table",
          "label": "复现探针表（带 JWT 打 :8010，2026-11-10，三行请求/结果）",
          "in_report_section": "发现的缺陷（可复现）",
          "locator": {
            "method": "char_span",
            "start_char": 245,
            "end_char": 491,
            "start_line": 11,
            "end_line": 15,
            "quote": "| 请求 | 结果 |\n|---|---|\n| `GET /api/v1/tensor/capabilities/audit`（无 token） | 401（auth 中间件先于路由） |\n| `GET /api/v1/tensor/capabilities/audit`（带 token） | **404 Not Found** |\n| `GET /api/v1/tensor/capabilities/semantics`（带 token） | 404（新端点，分支未部署，符合预期） |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "os.path.exists(worktree/rel) + grep -rIl rel in TensorKnowledge@a7fdcb80 (grep hits=0, exists=False)",
            "result": "present"
          },
          "note": "表格在报告 markdown 内逐字可解析；作为下游工序的定位脚手架登记，不复制数字结论。",
          "quote_verbatim_in_markdown": true
        }
      ],
      "claims": [],
      "integrity": {
        "quote_uniqueness": "每条 locator.quote 在源 markdown 中出现恰好 1 次（A00 为标题行）",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "verification_stamp": null,
        "verified": false
      },
      "scope_statement": {
        "did": [
          "读取 report 11349 的 markdown 并重算 sha256",
          "枚举报告引用的文件/符号/端点/测试/跨报告引用/证据表并给出 verbatim locator",
          "输出 asset_manifest.json + kf_result.v1 信封"
        ],
        "did_not": [
          "抽取知识对象（claims 为空数组）",
          "做报告类型分类（objective.classify_report_type=false）",
          "重放线上探针 / 执行他仓测试",
          "解引用 report 11344（产线边界：只碰 11349）",
          "打 verified 戳（verification 由平台门计算）"
        ]
      }
    }
  },
  "claims": []
}
```
