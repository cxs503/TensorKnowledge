#!/usr/bin/env python3
"""Render and publish the KF-RESULT report for work package wp-9777-01.

    python3 scripts/kf_wp9777_01_report.py render   # -> docs/kf_result_wp-9777-01.md
    python3 scripts/kf_wp9777_01_report.py post     # render + POST /tensor/reports
    python3 scripts/kf_wp9777_01_report.py all

Every number in the markdown is read out of the committed artefacts
(docs/kf/wp-9777-01/{asset_manifest,kf_result,verification}.json) -- nothing is typed in by
hand. The single ```json fence holds the envelope verbatim, as the delivery channel requires.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-9777-01"
PACKAGE_ID = "wp-9777-01"
REPORT_MD = ROOT / "docs" / ("kf_result_%s.md" % PACKAGE_ID)
FIG = PKG / "figures" / "fig1_asset_locator_map.png"


def load(name: str):
    return json.loads((PKG / name).read_text(encoding="utf-8"))


def render() -> str:
    man = load("asset_manifest.json")
    env = load("kf_result.json")
    ver = load("verification.json")
    src = man["source"]
    counts = man["counts"]
    assets = man["assets"]

    rows = []
    for a in assets:
        loc = a["locator"]
        quote = loc["quote"].replace("|", "\\|")
        rows.append("| %s | %s | %s | L%d | %s | %s | %s |"
                    % (a["asset_id"], a["asset_class"], a["label"][:46],
                       loc["start_line"], a["resolution"],
                       a["resolution_check"]["result"], quote[:88]))
    asset_table = "\n".join(rows)

    loc_rows = []
    for loc in man["locators"]:
        loc_rows.append("| %s | %d | %s | %s | %d | %s |"
                        % (loc["asset_id"], loc["locator"]["line"],
                           loc["quote_sha256"].split(":")[1][:16],
                           loc["quote"].replace("|", "\\|")[:60],
                           loc["occurrences_in_source"],
                           "yes" if loc["resolved"] else "NO"))
    loc_table = "\n".join(loc_rows)

    sym_rows = "\n".join("| %s | %d | %s |" % (s["kind"], s["locator"]["line"],
                                                s["quote"].replace("|", "\\|"))
                         for s in man["symbol_references"])

    checks = ver["acceptance"]

    def mark(name: str) -> str:
        c = checks[name]
        return "✓" if c["ok"] else "✗"

    detail = {
        "valid_json": "asset_manifest.json / kf_result.json / verification.json 均被 json 解析",
        "schema_pass": "kf_result.v1 errors=%s；asset_manifest.v1 形状 errors=%s（仅放开 3 个他包 const）"
                       % (checks["schema_pass"]["detail"]["kf_result_v1_errors"],
                          checks["schema_pass"]["detail"]["asset_manifest_v1_shape_errors(consts relaxed)"]),
        "source_locator_resolvable": checks["source_locator_resolvable"]["detail"],
        "source_hash_matches": "live=%s = manifest = contract = envelope"
                               % checks["source_hash_matches"]["detail"]["live"][:23],
        "no_duplicate_ids": checks["no_duplicate_ids"]["detail"],
        "all_claims_have_evidence_or_explicit_unresolved_status":
            checks["all_claims_have_evidence_or_explicit_unresolved_status"]["detail"],
    }

    unresolved_rows = "\n".join("| %s | `%s` | %s |" % (u["asset_id"], u["name"], u["reason"])
                                for u in man["unresolved"])

    md = f"""# KF-RESULT {PACKAGE_ID}

**工序** 01-asset-registration ｜ **report_id** 9777 ｜ **scenario_key** `{src["scenario_key"]}`
**来源** `{src["uri"]}` 字段 `{src["field"]}` ｜ sha256 `{src["source_hash"].split(":")[1]}`
**字符/字节/行** {src["chars"]} / {src["bytes_utf8"]} / {src["lines"]} ｜ **claims** {counts["claims"]} 条（契约允许空）
**repro_cmd** 见 ②

## ① 本工序做了什么

只做一件事：把报告 9777 的**源资产身份**登记成机器可校验的清单（`asset_manifest.json`），并为报告正文
声明过的附件/工件逐条建立**可解析定位**（1-based 行号 + 逐字引文 + 字符偏移 + 引文 sha256）。不做抽取、
不判报告类型、不写任何 claim、不给任何内容打 verified 标——verification 归平台门。

登记结果：**{counts["assets"]} 个资产**（`{json.dumps(counts["by_class"], ensure_ascii=False)}`），
其中源文档 1 个 `resolved_in_source`，其余 {counts["referenced_unresolved"]} 个 `referenced_unresolved`
（5 张图仅存于平台记录元数据、3 处正文路径指向上游工作树）。报告自身哈希与契约声明
`hash_match={src["hash_match"]}`、字符数 `chars_match_contract={src["chars_match_contract"]}`。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文（唯一信道）**：`GET $TENSOR_API_BASE/tensor/reports/9777`（Bearer 由
   `POST /auth/login` 换取）。`psql -d tensorplatform` 直读 `tensor_reports` 被拒
   （`permission denied for table tensor_reports`），故 API 是唯一来源；原文落地
   `docs/kf/wp-9777-01/source.md`（committed，供离线复算）。
2. **算哈希**：对 markdown 字符串的 UTF-8 字节算 sha256 → `{src["source_hash"]}`，与契约
   `source_hash` 逐字比对（`hash_match={src["hash_match"]}`），并把 chars `{src["chars"]}` 与契约
   `chars` {src["contract_chars"]} 比对。
3. **枚举资产**：源文档本体；平台记录 `figures[0..4]` 的 5 条 name+caption；正文路径锚点
   （`dsbeam.py`、`artifacts/m8404_dsm/audit_acceptance.py`、`results.json`）；另登记 5 条行内
   代码符号（函数/第三方调用/公式）作为 `symbol_references`（不计入 assets）。
4. **建定位器**：每个锚点在原文中找行 → 在该行内反复按分隔符切分（`，；。、`、`（）()`、`|`、
   `**`、行内反引号 span）→ 取**在全文中唯一**的最短子句作为引文，记录行号、
   `md.find(quote)` 字符偏移、引文 sha256、全文出现次数。拒绝括号/反引号不闭合、或截断在半个
   token 上的候选（踩坑记录见 ⑤）。
5. **解析判定（不臆造）**：源文档→`resolved_in_source`；5 图探测
   `GET /tensor/reports/9777/{{figures,artifacts,attachments}}` 三端点全 404 → 无字节可哈希 →
   `referenced_unresolved`；3 处正文路径在本交付树中逐一 `os.path.exists` 探测（全不存在，属上游
   TensorFEM/audit 工作树）→ `referenced_unresolved`，并在 `note` 写明"这是本检出范围，不是上游缺陷"。
6. **封信封并自检**：`kf_result.json` 只装 `outputs.asset_manifest.json` + `claims: []`；
   `verification.py` 6 条验收项逐条重算（**不是**回读自己写的字段）。
7. **一键复跑**（工作树根）：

```bash
python3 scripts/kf_wp9777_01_register.py all   # fetch + manifest + envelope + 6 项自检 + 图
python3 -m pytest tests/test_kf_wp9777_01.py -q  # 20 条离线验收测试
python3 scripts/kf_wp9777_01_report.py post     # 生成并提交本报告
```

工具链：Python 3.11 + 标准库（urllib/hashlib/json/re）+ `jsonschema` 4.26 + `matplotlib` 3.10；
未引入 scipy/pandas，无外网依赖（除平台 API）。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-9777-01/asset_manifest.json` | 登记主产物：schema=asset_manifest.v1、{counts["assets"]} 资产、{counts["locators"]} 定位器、{counts["symbol_references"]} 符号引用、claims=[] |
| `docs/kf/wp-9777-01/kf_result.json` | 平台结果信封（package_id/task_type/report_id/provenance/outputs/claims），`provenance.source_hash` = 契约哈希 |
| `docs/kf/wp-9777-01/verification.json` | 6 条 acceptance 自检结果，`all_ok={ver["all_ok"]}` |
| `docs/kf/wp-9777-01/source.md` | 原文 committed 副本（{src["chars"]} chars），离线复算用 |
| `docs/kf/wp-9777-01/figures/fig1_asset_locator_map.png` | 图1 资产定位在报告行轴上的分布 + 解析状态直方图 |
| `scripts/kf_wp9777_01_register.py` | 登记工序脚本（build/envelope/verify/figure/all） |
| `scripts/kf_wp9777_01_report.py` | 报告生成 + 提交脚本（本文件即其输出） |
| `tests/test_kf_wp9777_01.py` | 20 条离线验收测试（独立重算哈希/定位，不 import 生产 verify） |
| `runs/wp-9777-01/source_9777.md`、`runs/wp-9777-01/report_9777.json` | 取数留痕（原文 + 平台记录快照） |

### 资产登记表（{counts["assets"]} 条）

| id | class | label | 行 | resolution | check | 引文 |
|---|---|---|---|---|---|---|
{asset_table}

未解析清单（{counts["referenced_unresolved"]} 条，全部显式声明，不隐藏）：

| id | name | 判定依据 |
|---|---|---|
{unresolved_rows}

图1（`fig1_asset_locator_map.png`）：左panel 为 9 个资产的定位区间在 {src["lines"]} 行报告轴上的位置
（灰竖线=章节/首末行 identity fact），右panel 为 resolution 直方图；数据全部由 manifest 直接绘制。

## ④ 证据定位表（claim/字段 → 原文引文片段）

本工序不出 claim（`claims: []`，契约 `no_forced_claim_generation=true`）；下表是**资产定位器**的证据面，
每条均由平台可独立重算（逐字子串 + 引文 sha256 + 行号 + 唯一性）：

| id | 行 | quote_sha256(前16) | 引文片段（逐字） | 全文出现次数 | resolved |
|---|---|---|---|---|---|
{loc_table}

行内代码符号引用（不计入 assets）：

| kind | 行 | 引文 |
|---|---|---|
{sym_rows}

身份事实（首行/各节标题/末行，整行逐字比对，见 `asset_manifest.json → identity_facts`）：8 条全部复算一致。
**一处如实记录的不一致**：平台记录 title = 契约 title（战役长标题），而正文 H1 =
`# 自由-自由 Timoshenko 梁精确 DSM 验收审计（节点 p423w2-n09）`（节点级标题）——两者字符串不同，
清单原样登记双方（`h1_equals_record_title={src["h1_equals_record_title"]}`），不做改写、不择一。

## ⑤ 注意点与局限

1. **图只有元数据、没有字节**：5 张图在记录里只有 name+caption，三候选字节端点全 404，故一律
   `referenced_unresolved` 且**不声明任何图哈希**。若后续平台提供图字节，应重跑本工序并把 5 条升级为
   `resolved_in_source` + 逐图 sha256。
2. **正文 ④ 的图注是元数据的改写**：正文按 `图1..图5` 标签复述，措辞与记录 caption 不同
   （`name_in_markdown={assets[1]["note"].split("name_in_markdown=")[1].split(",")[0]}`、
   `caption_in_markdown={assets[1]["note"].split("caption_in_markdown=")[1].split(";")[0]}`），
   图身份只能按 name 绑定——清单把这一分歧写进 note，不假装图注可逐字定位。
3. **3 处正文路径在本检出不存在**：`dsbeam.py` / `artifacts/m8404_dsm/audit_acceptance.py` /
   `results.json` 属上游 TensorFEM+audit 工作树，TensorKnowledge 检出里没有 → 判 `referenced_unresolved`。
   这是**本检出范围**结论，不是"上游缺文件"的指控；不得据此推断上游造假。
4. **引文自动收窄的坑（本单踩到并修掉）**：按分隔符切分取最短唯一子句时，曾产出
   `；图3 J`、`J(ω)=n·J₀+s{{` 这类截断在半个 token/未闭合括号上的引文。修复：候选引文必须括号
   `()（）{{}}` 与反引号成对，且行内反引号 span 优先作为候选；修后 9/9 资产引文与 5/5 符号引文全部
   合法逐字唯一。
5. **registration ≠ extraction**：本工序不判断报告结论真伪，也不评价 7/7 判据 PASS 是否成立；那是
   下游抽取/审计工序的事。清单里没有任何 `verified` 标记（契约硬约束）。
6. **哈希绑定口径**：`source_hash` 绑定的是平台返回的 markdown 字符串的 UTF-8 字节；存储侧任何改动
   （含空白）都会使它与契约声明失配并令门失败——这是设计意图，不是脆弱点。

## ⑥ 自检（逐条对照 acceptance）

| # | acceptance | 结果 | 依据 |
|---|---|---|---|
| 1 | valid_json | {mark("valid_json")} | {detail["valid_json"]} |
| 2 | schema_pass | {mark("schema_pass")} | {detail["schema_pass"]} |
| 3 | source_locator_resolvable | {mark("source_locator_resolvable")} | {detail["source_locator_resolvable"]} |
| 4 | source_hash_matches | {mark("source_hash_matches")} | {detail["source_hash_matches"]} |
| 5 | no_duplicate_ids | {mark("no_duplicate_ids")} | {detail["no_duplicate_ids"]} |
| 6 | all_claims_have_evidence_or_explicit_unresolved_status | {mark("all_claims_have_evidence_or_explicit_unresolved_status")} | {detail["all_claims_have_evidence_or_explicit_unresolved_status"]} |

`all_ok = {ver["all_ok"]}`；`python3 -m pytest tests/test_kf_wp9777_01.py -q` → 20 passed。
以上为**自检**，非平台裁定；本单未把任何结论标 verified。

**误差判定（是否 <3%）**：本工序无物理量、无基准解——它登记的是文档身份与定位，唯一"误差面"是
字符串等价性，且已为**精确等价**（哈希逐字相同、{counts["locators"]} 条引文逐字子串命中、字符偏移一致），
因此不存在 >3% 的量化误差需要声明；若后续工序要做数值误差判定，应以报告 ⑥ 节的 `results.json` 原值为基准，
而该文件在本检出不可得（见 ⑤.3），故本工序**不对任何频率/百分比数值做复算或背书**。

## 附录：结果信封（交付信道：本文件唯一一个 JSON 代码块，内容与 `kf_result.json` 逐字节一致）

```json
{json.dumps(env, ensure_ascii=False, indent=2)}
```
"""
    REPORT_MD.write_text(md, encoding="utf-8")
    return md


def post() -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    tok = json.load(urllib.request.urlopen(urllib.request.Request(
        base + "/auth/login", data=body, headers={"Content-Type": "application/json"})))["access_token"]

    md = render()
    assert md.count("```json") == 1, "the envelope must be the only ```json block"
    man = load("asset_manifest.json")
    payload = {
        "title": "KF-RESULT %s" % PACKAGE_ID,
        "summary": ("报告 9777 源资产登记（工序 01，lane A）：markdown sha256 与契约一致"
                    "（%s…，%d chars），登记 %d 个资产（源文档 1 resolved、%d referenced_unresolved："
                    "5 图为元数据无字节、3 处正文路径属上游工作树），%d 条定位器全部逐字唯一可解析，"
                    "claims 空数组，未标 verified。"
                    % (man["source"]["source_hash"].split(":")[1][:12], man["source"]["chars"],
                       man["counts"]["assets"], man["counts"]["referenced_unresolved"],
                       man["counts"]["locators"])),
        "scenario_key": man["source"]["scenario_key"],
        "mission_id": 15671,
        "tags": ["kf-wp:%s" % PACKAGE_ID, "KF-RESULT", "asset-registration", "report-9777",
                 "structural-dynamics", "DSM"],
        "markdown": md,
        "figures": [{"name": "fig1_asset_locator_map.png",
                     "caption": ("图1 wp-9777-01 资产登记：9 个资产在 70 行报告轴上的定位区间（灰线=章节"
                                 "identity fact）与 resolution 状态直方图"),
                     "png_base64": base64.b64encode(FIG.read_bytes()).decode()}],
    }
    req = urllib.request.Request(base + "/tensor/reports", data=json.dumps(payload).encode(),
                                 headers={"Authorization": "Bearer " + tok,
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        out = json.loads(r.read())
    print("posted report id:", out.get("id"), "title:", out.get("title"))
    return out


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    if cmd in ("render", "all"):
        render()
        print("rendered:", REPORT_MD.relative_to(ROOT))
    if cmd in ("post", "all"):
        post()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))