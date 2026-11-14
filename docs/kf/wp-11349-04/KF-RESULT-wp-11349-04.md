# KF-RESULT wp-11349-04

工序 04 · 独立审核（red-team）· 审核对象 **wp-11349-01**（report 11349 资产登记包）
分层：API接线 | platform_governance_capability_ledger_semantics | 裁决 **needs-fix**

## ① 本工序做了什么

对 report 11349（《P266W1-N10 补记：能力台账 API 接线缺陷修复（capability_audit 路由 404）》）的 01 资产登记包
`wp-11349-01` 做独立红队复核：把它的 11 条 asset locator、计数、resolution 语义、哈希链、schema 合规与自我打戳情况逐条重算，
并用**当前时点**的线上探针对报告中的两处可核事实（21 能力矩阵、401/404 探针结论）做独立证伪尝试。
不断言任何 `verified`；裁决只按机器可重算判据出。

## ② 怎么做的（步骤/工具/关键设置）

1. **取正文**：`GET $TENSOR_API_BASE/tensor/reports/11349`（Bearer JWT），落盘 `runs/wp-11349-04/report_11349_api.json`；
   本地重算 `sha256(markdown.encode('utf-8'))`，与契约/上游 manifest 三处比对（check C01/C02/C03）。
2. **重切片**：对上游 11 条 locator 逐条执行 `md[start_char:end_char] == quote`，并统计 `md.count(quote)` 是否恰为 1；
   另按 `start_line/end_line` 重拼行区间核对覆盖（C04a/C04b/C04c）。
3. **结构/计数**：核 `in_report_section` 是否为源文档真实标题（C05）、`counts` 与 assets 明细是否自洽（C06）、id 唯一（C07）。
4. **信封与 schema**：`outputs['asset_manifest.json']` 与磁盘 manifest 逐字段比对（C08）；用仓内
   `schemas/kf_result.v1.schema.json` 校验上游信封（C09）；用上游自带的 pinned schema 校验 manifest（C10）。
5. **语义与打戳**：`referenced_unresolved` 的仓内路径可达性实测（C15）；确认无 `verified:true`/`verification_stamp`（C11）。
6. **链条**：上游自报 `artifact_sha256` 与磁盘实测比对（C12）；上游已发布报告 14789 的 title/tags/status 经平台 API 复核（C13）；
   上游落盘快照字节与平台正文重算比对（C14）。
7. **独立探针（当前时点）**：`GET /api/v1/tensor/capabilities/{audit,audit/summary,semantics}`，各有/无 token 两发，只读 GET，
   结果落 `runs/wp-11349-04/live_probe.json` 与 `probe_*_live.json`（C16）。

工具：`python3` + `jsonschema` + `curl`；脚本 `scripts/kf/verify_wp_11349_04.py`、`scripts/kf/emit_wp_11349_04.py`。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-11349-04/review_report.json` | 审核主体：18 项机器判据逐条结果、findings、live_probe、checks_not_run、独立性局限、裁决 |
| `docs/kf/wp-11349-04/kf_result.json` | KF-RESULT v1 信封（严格 schema，`provenance.source_hash` = 源 markdown 重算哈希） |
| `docs/kf/wp-11349-04/self_check.json` | 逐条 acceptance 自检 + 本信封/事件 schema 校验计数 + 产物哈希 |
| `docs/kf/wp-11349-04/KF-RESULT-wp-11349-04.md` | 本报告（唯一 json 代码块 = 上述信封字节） |
| `scripts/kf/verify_wp_11349_04.py` | 一键复算脚本（离线可跑：`--snapshot`） |
| `tests/test_kf_wp_11349_04.py` | 4 项回归：判据矩阵形状、信封/事件 schema、篡改 locator、篡改源哈希 |
| `runs/wp-11349-04/{report_11349_api.json,live_probe.json,probe_audit_live.json,probe_semantics_live.json,upstream_report_14789.json}` | 原始证据（正文快照/探针回包/上游发布记录） |

## ④ 证据定位表（claim/字段 → 原文引文片段）

| # | 被判字段/主张 | 原文引文（逐字，可在 markdown 内定位） | 独立判据 |
|---|---|---|---|
| E1 | 被审对象与缺陷面 | `backend/api/capability_audit.py` | C04b/C15：切片成立；该 .py 在 TensorKnowledge 工作树内不可达 → `referenced_unresolved` 语义正确 |
| E2 | 装配点缺失 | `**从未 include 该 router**` | C04b：quote 逐字命中且唯一 |
| E3 | 端点性质（21 能力矩阵） | `21 能力证据等级矩阵端点` | C16：当前端点 `data.total_capabilities`=21，schema_version=2.0 → 事实被佐证 |
| E4 | 探针结论（历史时点） | `**404 Not Found**` | 独立探针当前为 200（audit 与 /audit/summary）→ 该 404 只在 2026-11-10 时点成立，现在不可复现（不否定历史，但不得当作当下事实） |
| E5 | 新端点状态 | `404（新端点，分支未部署，符合预期）` | 独立探针当前 503，detail 为“工件缺失 … semantic_layers.json” → 状态已改变（路由已挂、工件未生成） |
| E6 | 接线回归测试 | `test_capability_semantics_api.py::test_routers_wired_in_main_and_route_shapes` | C04b：切片 77 字符逐字成立；测试本体属 TensorPlatform 仓，本工作树无 → 未执行（not_run） |
| E7 | 测试规模自述 | `（10 项测试全绿）` | 无法在本仓复核（not_run）；上游 01 包亦未复核 |
| E8 | 跨报告引用 | `id=11344` | 产线边界内不解引用 → `referenced_unresolved` 与边界一致 |
| E9 | 修复生效范围 | `**本分支生效**` | 上游 `resolution`/scope_statement 未把它写成线上已生效 → 语义保真 |
| E10 | 哈希链 | `source_hash` 三处（契约/上游 manifest/本次重算） | C01/C02/C14 全部一致：`sha256:e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80` |
| E11 | 上游登记结论 | 11 条 asset，`counts.assets`=11，`by_resolution`={resolved_in_source:2, referenced_unresolved:9} | C06/C07：与明细重算完全一致 |
| E12 | 上游自检声明 | `"schema_pass": "pass"`（上游 self_check.json） | **C09 fail**：上游 `kf_result.json` 违反仓内 `schemas/kf_result.v1.schema.json`（超集字段 `claims` 与 `provenance.producer/emitted_at/notes`，2 条 error）→ 自检声明过度（见 finding F-C09） |
| E13 | 上游发布记录 | `title: KF-RESULT wp-11349-01`，tags 含 `kf-wp:wp-11349-01` | C13：平台 API 复核报告 14789 status=published，title/tags 一致 |

## ⑤ 注意点与局限

1. **唯一失败项是信封 schema，不是内容保真**：17/18 判据通过；失败项 F-C09（major）为上游 `kf_result.json` 相对仓内
   `schemas/kf_result.v1.schema.json` 的 `additionalProperties:false` 多了 `claims` 与 `provenance.producer/emitted_at/notes`。
   全仓同病：`docs/kf/*/kf_result.json` 117 份中 111 份同样失败（`producer` 89 份、`emitted_at` 90 份、`claims` 83 份），
   故根因是**schema 与产线事实约定漂移**，不是 wp-11349-01 独有疏漏。建议在 schema 侧显式放行这几个人工字段（或产线统一剥离），
   并把上游 self_check 的该项改成 `not_run/unknown` 而非 `pass`——这正是本单要揭的“检查执行了但断言不足”。
2. **时点敏感**：报告的 401/404 与“分支未生效”都是 2026-11-10 的历史观察；当前端点已 200，语义端点 503。
   任何人拿本报告 ④表去当“今天该路径 404”的证据都会错。上游 01 包把 A10 标 `resolved_in_source`（只表示“表格在源文内可解析”）
   并显式声明未重放探针，这一点是**合规且诚实**的；本审核保留该判断，但补上当前时点观测。
3. **未执行项**（如实声明，不记为通过）：他仓测试 `backend/tests/test_capability_semantics_api.py` 未跑；
   2026-11-10 的 404 无法回溯重放；report 11344 未解引用（产线边界）。
4. **独立性局限**：审核者与上游生产者同属单一模型族，方法学独立性有限；因此本包把裁决尽量压在可机器重算的判据上
   （哈希/字节切片/行区间/schema/计数），主观判断只出现在严重度定级。
5. **当前时点发现的旁证缺陷（不在本工序范围，仅登记）**：`GET /api/v1/tensor/capabilities/semantics` 现在 503
   （`工件缺失: …/artifacts/capability_semantics/semantic_layers.json`），说明路由已接线但工件未生成；
   另 `audit` 载荷里 `calc.stability` 的 `reconciled_level=REAL` 与其 `action` 文本（要求降 MOCK，KB +33.33%/GM +61.54%/GZ@20° +53.27%）
   自相矛盾——属台账语义工作包，本单不裁决。
6. **无图理由**：本工序是纯文档/接口审核，输入是 1029 字符的 markdown 与 JSON 账本，不存在场量云图或收敛/比较曲线；
   图件以 ④ 表 + `runs/` 原始回包替代，故不出 png。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 依据 |
|---|---|---|
| `valid_json` | ✅ | `review_report.json`/`kf_result.json`/`self_check.json` 均解析成功 |
| `schema_pass` | ✅ | 本包 `kf_result.json` 对 `schemas/kf_result.v1.schema.json` errors=0；`review_events[0]` 对 `review-event.schema.json` errors=0 |
| `reviewer_independent` | ⚠️ partial | 判据机器可重算（哈希/切片/schema/计数），但审核者与生产者同模型族，见 ⑤.4 |
| `upstream_packages_completed` | ✅ | 审核对象 wp-11349-01 已发布为平台报告 14789（status=published，tags 含 `kf-wp:wp-11349-01`）；report 11349 无 02/03 包 |

判据自测（证明判据真在断言，而非只执行）：`python3 -m pytest tests/test_kf_wp_11349_04.py -q` → **4 passed**
（含两条篡改测试：`start_char` +1 必须让 C04b fail；源 markdown 改 1 字符必须让 C01/C02 fail）。

对**被审对象**的验收结论：`valid_json` ✅ / `schema_pass` ❌（F-C09）/ 其余内容保真项 ✅ → 裁决 **needs-fix**
（一处 `kf_result.json` 信封字段需剥离，或 schema 侧放行；内容层不需返工）。
按 honest-FAIL 纪律：本工序自身 18 项判据中 1 项 fail，不粉饰；该 fail 归被审对象而非本包产物。

## repro_cmd（一键复跑）

```bash
# 工作树根 = 仓库检出；离线（用已落盘快照）
python3 scripts/kf/verify_wp_11349_04.py --snapshot runs/wp-11349-04/report_11349_api.json   && python3 scripts/kf/emit_wp_11349_04.py && python3 scripts/kf/render_wp_11349_04_md.py   && python3 -m pytest tests/test_kf_wp_11349_04.py -q

# 在线（重取正文，platform 独立重算哈希）
TOKEN=$(curl -s -X POST "$TENSOR_API_BASE/auth/login" -H 'Content-Type: application/json' \
  -d "{\"username\":\"$TENSOR_AGENT_USER\",\"password\":\"$TENSOR_AGENT_PASS\"}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s -H "Authorization: Bearer $TOKEN" "$TENSOR_API_BASE/tensor/reports/11349" -o runs/wp-11349-04/report_11349_api.json
rm -f runs/wp-11349-04/live_probe.json   # 想在线的探针结果就重打三发 GET，或保留历史探针文件
python3 scripts/kf/verify_wp_11349_04.py --api "$TENSOR_API_BASE" --token "$TOKEN" --snapshot /dev/null \
  && python3 scripts/kf/emit_wp_11349_04.py && python3 scripts/kf/render_wp_11349_04_md.py
```

```json
{
 "package_id": "wp-11349-04",
 "task_type": "04-independent-review",
 "contract_version": "1.0",
 "report_id": "11349",
 "provenance": {
  "source_uri": "tensor://reports/11349",
  "source_field": "markdown",
  "source_hash": "sha256:e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80",
  "source_hash_matches": true,
  "title": "P266W1-N10 补记：能力台账 API 接线缺陷修复（capability_audit 路由 404）",
  "scenario_key": "platform_governance_capability_ledger_semantics",
  "chars": 1029
 },
 "outputs": {
  "review_report.json": {
   "reviewer": "agent/m19809 · red-team-reviewer (wp-11349-04)",
   "reviewed_package": "wp-11349-01",
   "reviewed_artifacts": {
    "asset_manifest.json": {
     "sha256": "0663bcdcc8460ef216096cb11a3f6a67ef9122c51883a909fa1b116e79e01c42",
     "schema": "asset_manifest.v1"
    },
    "kf_result.json": {
     "sha256": "21155502045b04b1a8fa0fd3b0427183c700e4ece1fe60fd8b86eb35a20854e6"
    },
    "published_report_id": 14789,
    "source_markdown_sha256": "sha256:e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80"
   },
   "verdict": "needs-fix",
   "checks_total": 18,
   "checks_passed": 17,
   "checks": [
    {
     "id": "C01",
     "check": "source_hash 契约一致性",
     "result": "pass",
     "detail": "recomputed=sha256:e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80 contract=sha256:e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80"
    },
    {
     "id": "C02",
     "check": "asset_manifest.source.hash 与重算一致",
     "result": "pass",
     "detail": "manifest=e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80 recomputed=sha256:e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80"
    },
    {
     "id": "C03",
     "check": "asset_manifest.source.chars/bytes 与实测一致",
     "result": "pass",
     "detail": "declared chars=1029 bytes=1657 | measured chars=1029 bytes=1657"
    },
    {
     "id": "C04a",
     "check": "locator.quote 在源 markdown 中唯一",
     "result": "pass",
     "detail": "非唯一项=[]"
    },
    {
     "id": "C04b",
     "check": "locator.char_span 切片 == quote",
     "result": "pass",
     "detail": "失配项=[]"
    },
    {
     "id": "C04c",
     "check": "locator.start_line/end_line 覆盖 quote",
     "result": "pass",
     "detail": "失配项=[]"
    },
    {
     "id": "C05",
     "check": "in_report_section 均为源文档真实标题",
     "result": "pass",
     "detail": "失配项=[] | 源标题=['P266W1-N10 补记：能力台账路由接线缺陷修复', '修复', '发现的缺陷（可复现）', '局限']"
    },
    {
     "id": "C06",
     "check": "counts 与 assets 明细自洽",
     "result": "pass",
     "detail": "declared={\"assets\": 11, \"by_class\": {\"report_document\": 1, \"source_file\": 2, \"source_symbol\": 2, \"api_endpoint\": 3, \"test_case\": 1, \"cross_report_reference\": 1, \"evidence_table\": 1}, \"by_resolution\": {\"resolved_in_source\": 2, \"referenced_unresolved\": 9}} | recomputed assets=11 by_class={'report_document': 1, 'source_file': 2, 'source_symbol': 2, 'api_endpoint': 3, 'test_case': 1, 'cross_report_reference': 1, 'evidence_table': 1} by_resolution={'resolved_in_source': 2, 'referenced_unresolved': 9}"
    },
    {
     "id": "C07",
     "check": "asset_id 唯一",
     "result": "pass",
     "detail": "ids=['A00', 'A01', 'A02', 'A03', 'A04', 'A05', 'A06', 'A07', 'A08', 'A09', 'A10']"
    },
    {
     "id": "C08",
     "check": "kf_result.outputs['asset_manifest.json'] == 磁盘 manifest",
     "result": "pass",
     "detail": "envelope keys=['asset_manifest.json']"
    },
    {
     "id": "C09",
     "check": "kf_result 通过 schemas/kf_result.v1.schema.json",
     "result": "fail",
     "detail": "errors=2 []:Additional properties are not allowed ('claims' was unexpected) ; ['provenance']:Additional properties are not allowed ('emitted_at', 'notes', 'producer' were unexpected)"
    },
    {
     "id": "C10",
     "check": "asset_manifest 通过包内 pinned schema",
     "result": "pass",
     "detail": "errors=0"
    },
    {
     "id": "C11",
     "check": "被审产物未自我打 verified 戳",
     "result": "pass",
     "detail": "manifest.integrity.verified=False verification_stamp=None"
    },
    {
     "id": "C12",
     "check": "上游自报 artifact_sha256 与磁盘实测一致",
     "result": "pass",
     "detail": "declared manifest=0663bcdcc8460ef216096cb11a3f6a67ef9122c51883a909fa1b116e79e01c42 measured=0663bcdcc8460ef216096cb11a3f6a67ef9122c51883a909fa1b116e79e01c42 | declared kf=21155502045b04b1a8fa0fd3b0427183c700e4ece1fe60fd8b86eb35a20854e6 measured=21155502045b04b1a8fa0fd3b0427183c700e4ece1fe60fd8b86eb35a20854e6"
    },
    {
     "id": "C13",
     "check": "上游 KF-RESULT 报告已发布（id/tag 自洽）",
     "result": "pass",
     "detail": "id=14789 title=KF-RESULT wp-11349-01 status=published"
    },
    {
     "id": "C14",
     "check": "上游落盘快照字节 == 平台正文重算",
     "result": "pass",
     "detail": "snapshot=docs/kf/wp-11349-01/source/report_11349.md"
    },
    {
     "id": "C15",
     "check": "referenced_unresolved 的仓内路径确实不可达",
     "result": "pass",
     "detail": "probed={\"A01\": {\"path\": \"backend/api/capability_audit.py\", \"in_worktree\": false}, \"A02\": {\"path\": \"backend/main.py\", \"in_worktree\": false}, \"A08\": {\"path\": \"test_capability_semantics_api.py\", \"in_worktree\": false}} bad=[]"
    },
    {
     "id": "C16",
     "check": "报告“21 能力”与当前端点 total_capabilities 一致",
     "result": "pass",
     "detail": "endpoint total_capabilities=21"
    }
   ],
   "findings": [
    {
     "id": "F-C09",
     "severity": "major",
     "check": "kf_result 通过 schemas/kf_result.v1.schema.json",
     "detail": "errors=2 []:Additional properties are not allowed ('claims' was unexpected) ; ['provenance']:Additional properties are not allowed ('emitted_at', 'notes', 'producer' were unexpected)"
    }
   ],
   "checks_not_run": [
    "backend/tests/test_capability_semantics_api.py 未执行：该测试属 TensorPlatform 仓，本工作树（TensorKnowledge）无此文件",
    "2026-11-10 时点线上 404 无法回溯重放：本次只观测当前时点状态（见 live_probe）",
    "未解引用 report_id=11344（产线边界：只碰 11349）"
   ],
   "live_probe": {
    "probed_at_utc": "2026-11-14T05:05:00Z",
    "base": "http://127.0.0.1:8010/api/v1",
    "audit": {
     "path": "/tensor/capabilities/audit",
     "http_no_token": 401,
     "http_with_token": 200,
     "payload_sha256_file": "runs/wp-11349-04/probe_audit_live.json",
     "payload": {
      "data": {
       "total_capabilities": 21,
       "schema_version": "2.0"
      }
     }
    },
    "audit_summary": {
     "path": "/tensor/capabilities/audit/summary",
     "http_no_token": 401,
     "http_with_token": 200
    },
    "semantics": {
     "path": "/tensor/capabilities/semantics",
     "http_no_token": 401,
     "http_with_token": 503,
     "detail": "工件缺失: /root/tensor-ecosystem/TensorPlatform/artifacts/capability_semantics/semantic_layers.json；请先运行 `python3 -m tools.capability_semantics --figures --doc`",
     "payload_sha256_file": "runs/wp-11349-04/probe_semantics_live.json"
    },
    "note": "探针只代表当前时点；报告所载 401/404 为 2026-11-10 时点状态，无法回溯重放"
   },
   "reported_facts_cross_checked": [
    {
     "fact_in_source": "21 能力证据等级矩阵",
     "source_quote": "21 能力证据等级矩阵端点",
     "independent_check": "GET /api/v1/tensor/capabilities/audit 当前返回 data.total_capabilities=21（schema_version=2.0）",
     "result": "corroborated"
    },
    {
     "fact_in_source": "带 token 探针为 404",
     "source_quote": "**404 Not Found**",
     "independent_check": "当前时点同一路径带 token 返回 200（audit 与 /audit/summary 均 200）；报告所载为 2026-11-10 时点状态，不可回溯重放",
     "result": "not_reproducible_now"
    },
    {
     "fact_in_source": "semantics 端点 404（分支未部署）",
     "source_quote": "404（新端点，分支未部署，符合预期）",
     "independent_check": "当前时点返回 503，detail=工件缺失 artifacts/capability_semantics/semantic_layers.json——路由已挂上但工件未生成",
     "result": "changed_state"
    }
   ],
   "independence_limitations": [
    "被审包与本次审核由同一模型族产出，方法学独立性有限；用可重算的机器判据（哈希/切片/schema）替代人审主观判断",
    "线上探针只代表当前时点，不能回证或否证报告所载 2026-11-10 的 404 状态"
   ]
  },
  "review_events.json": [
   {
    "id": "tkr:wp-11349-04:wp-11349-01",
    "object_ref": "wp-11349-01",
    "object_version": "asset_manifest.json@0663bcdcc8460ef216096cb11a3f6a67ef9122c51883a909fa1b116e79e01c42",
    "decision": "request-changes",
    "reviewer": {
     "id": "agent/m19809",
     "reviewer_type": "agent",
     "role": "red-team-reviewer"
    },
    "reviewed_at": "2026-11-14T05:20:00Z",
    "policy_version": "kf-result-v1/wp-11349-04",
    "rationale": "18 项机器判据 17 通过：哈希/切片/标题/计数/可达性/resolution 语义全部成立；唯一失败项为被审 kf_result.json 违反 schemas/kf_result.v1.schema.json（超集字段 claims 与 provenance.producer/emitted_at/notes），使上游 self_check 的 schema_pass=pass 成为过度声明。"
   }
  ]
 }
}
```
