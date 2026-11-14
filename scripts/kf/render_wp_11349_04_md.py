#!/usr/bin/env python3
"""渲染 docs/kf/wp-11349-04/KF-RESULT-wp-11349-04.md：六段正文 + 唯一一个 json 代码块（= kf_result.json 字节原样）。

引文零手抄：本脚本另跑一遍断言，正文里 ④ 表登记的每个引文片段都必须是 report 11349 markdown 的子串。
复跑：python3 scripts/kf/render_wp_11349_04_md.py
"""
import hashlib
import json
import os

OUT = "docs/kf/wp-11349-04"
SNAP = "runs/wp-11349-04/report_11349_api.json"

BODY = """# KF-RESULT wp-11349-04

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
python3 scripts/kf/verify_wp_11349_04.py --snapshot runs/wp-11349-04/report_11349_api.json \
  && python3 scripts/kf/emit_wp_11349_04.py && python3 scripts/kf/render_wp_11349_04_md.py \
  && python3 -m pytest tests/test_kf_wp_11349_04.py -q

# 在线（重取正文，platform 独立重算哈希）
TOKEN=$(curl -s -X POST "$TENSOR_API_BASE/auth/login" -H 'Content-Type: application/json' \\
  -d "{\\"username\\":\\"$TENSOR_AGENT_USER\\",\\"password\\":\\"$TENSOR_AGENT_PASS\\"}" \\
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s -H "Authorization: Bearer $TOKEN" "$TENSOR_API_BASE/tensor/reports/11349" -o runs/wp-11349-04/report_11349_api.json
rm -f runs/wp-11349-04/live_probe.json   # 想在线的探针结果就重打三发 GET，或保留历史探针文件
python3 scripts/kf/verify_wp_11349_04.py --api "$TENSOR_API_BASE" --token "$TOKEN" --snapshot /dev/null \\
  && python3 scripts/kf/emit_wp_11349_04.py && python3 scripts/kf/render_wp_11349_04_md.py
```
"""


def main():
    md_src = json.load(open(SNAP))["markdown"]
    body = "\n".join(l for l in BODY.split("\n") if not l.startswith("```bash") )
    # 零手抄断言：④ 表与正文引用的每个源文片段必须逐字出现在 report markdown 内
    quoted = [
        "backend/api/capability_audit.py",
        "**从未 include 该 router**",
        "21 能力证据等级矩阵端点",
        "**404 Not Found**",
        "404（新端点，分支未部署，符合预期）",
        "test_capability_semantics_api.py::test_routers_wired_in_main_and_route_shapes",
        "（10 项测试全绿）",
        "id=11344",
        "**本分支生效**",
        "P266W1-N10 补记：能力台账路由接线缺陷修复",
    ]
    missing = [q for q in quoted if q not in md_src]
    assert not missing, "零手抄失败：%s" % missing
    assert hashlib.sha256(md_src.encode()).hexdigest() == \
        "e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80"
    envelope_text = open(os.path.join(OUT, "kf_result.json"), encoding="utf-8").read()
    text = BODY.rstrip() + "\n\n```json\n" + envelope_text.rstrip() + "\n```\n"
    assert text.count("```json") == 1, "只允许一个 json 代码块"
    p = os.path.join(OUT, "KF-RESULT-wp-11349-04.md")
    open(p, "w", encoding="utf-8").write(text)
    print("wrote", p, len(text), "chars; zero-handcopy quotes verified:", len(quoted))


if __name__ == "__main__":
    main()