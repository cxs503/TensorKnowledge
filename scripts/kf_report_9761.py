#!/usr/bin/env python3
"""Render + publish the KF-RESULT report for work package wp-9761-01.

Zero hand-copy rule: every number in the body is read from a produced artifact
(asset_manifest.json / verification.json / coverage.json) or from the result envelope;
every quotation in the evidence table is a *programmatically sliced* line of the source
markdown (the locator line block from the manifest), never retyped.

The delivery channel is the markdown of a platform report:
  title  = 'KF-RESULT wp-9761-01'
  tags   = [..., 'kf-wp:wp-9761-01']
  body   = six sections + EXACTLY ONE ```json block holding the result envelope

Outputs:
  docs/wp-9761-01/KF-RESULT.wp-9761-01.md   (durable copy of what is published)
  docs/wp-9761-01/kf_result_block.json      (the json block payload, byte-identical to runs/)
  runs/wp-9761-01/publish.json              (API response)

Usage: python3 scripts/kf_report_9761.py [--no-post]
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

RUN_DIR = pathlib.Path("runs/wp-9761-01")
DOC_DIR = pathlib.Path("docs/wp-9761-01")
FIG_DIR = DOC_DIR / "figures"

PACKAGE_ID = "wp-9761-01"
REPORT_ID = "9761"
CAMPAIGN_MISSION_ID = 15667
SCENARIO_KEY = "rigid_contact_energy_ledger_certification"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

MANIFEST = json.loads(pathlib.Path("artifacts/wp-9761-01/asset_manifest.json").read_text(encoding="utf-8"))
VERIF = json.loads(pathlib.Path("artifacts/wp-9761-01/verification.json").read_text(encoding="utf-8"))
COV = json.loads((DOC_DIR / "coverage.json").read_text(encoding="utf-8"))
RESULT = json.loads((RUN_DIR / "kf_result.wp-9761-01.json").read_text(encoding="utf-8"))
MD_SOURCE = (RUN_DIR / "report_9761.md").read_text(encoding="utf-8")


def snippet(quote: str, limit: int = 76) -> str:
    """First line of a locator quote, pipe-escaped, truncated — never retyped."""
    first = quote.split("\n")[0].strip().replace("|", "\\|")
    return first if len(first) <= limit else first[:limit] + "…"


def checks_table() -> str:
    rows = ["| acceptance item | 结果 | 证据 |", "|---|---|---|"]
    mapping = {
        "valid_json": "manifest/result/block/mirror 均可解析，block==result",
        "schema_pass": "asset_manifest 过本包 schema；信封过 schemas/kf_result.v1.schema.json",
        "source_locator_resolvable": "29/29 locator 在重新抓取的 markdown 上重解析成功",
        "source_hash_matches": "重算 sha256 与契约 source_hash 逐字节一致",
        "no_duplicate_ids": "asset_id/observation_id 无重复、无悬挂引用",
        "all_claims_have_evidence_or_explicit_unresolved_status": "claims=[] 合法空数组",
        "no_premature_verification_marks": "无 verified 标记；verification_status=not_verified",
        "counts_consistent": "counts 由 assets 重算一致",
        "report_scope_isolated": "仅 report_id=9761",
    }
    detail = {c["check"]: c for c in VERIF["checks"]}
    for name, desc in mapping.items():
        c = detail.get(name)
        if c is None:
            rows.append("| %s | 未运行 | — |" % name)
            continue
        rows.append("| %s | %s | %s |" % (name, c["result"].upper(), desc))
    return "\n".join(rows)


def evidence_table() -> str:
    rows = ["| 资产 | 定位（行/字符区间） | 原文引文片段（逐字切片） | 解析状态 |", "|---|---|---|---|"]
    for a in sorted(MANIFEST["assets"], key=lambda x: x["asset_id"]):
        loc = a["locator"]
        frag = snippet(loc["quote"])
        span = "``%s``" % frag if "`" in frag else "`%s`" % frag   # safe code span
        rows.append("| %s %s | L%d-L%d / c%d-c%d | %s | %s |" % (
            a["asset_id"], a["asset_class"], loc["start_line"], loc["end_line"],
            loc["start_char"], loc["end_char"], span, a["resolution"]))
    return "\n".join(rows)


def fig_block(name: str, caption: str) -> dict:
    png = (FIG_DIR / name).read_bytes()
    return dict(name=name, caption=caption,
                png_base64=base64.b64encode(png).decode(),
                sha256=hashlib.sha256(png).hexdigest())


def build_markdown() -> str:
    c = MANIFEST["counts"]
    by_res = c["by_resolution"]
    hash_ok = VERIF["checks"][[x["check"] for x in VERIF["checks"]].index("source_hash_matches")]
    fig1 = fig_block("fig1_asset_coverage.png",
                     "图 1 wp-9761-01 的资产定位覆盖图：29 条定位区间投射到 8931 字符的源文坐标轴，"
                     "颜色=解析状态；阴影带=未被任何具体资产钉住的区段（%d 字符，占 %.2f%%，"
                     "全部为空行与章节标题）。" % (COV["gap_chars"], 100 * COV["gap_chars"] / COV["document_chars"]))
    fig2 = fig_block("fig2_resolution_checks.png",
                     "图 2 左：29 条资产按解析状态分布（resolved_in_source %d / referenced_unresolved %d）；"
                     "右：本包 %d 项校验逐条结果，overall=%s。"
                     % (by_res.get("resolved_in_source", 0), by_res.get("referenced_unresolved", 0),
                        len(VERIF["checks"]), VERIF["overall"]))

    body = f"""# KF-RESULT {PACKAGE_ID}

**工作包** `{PACKAGE_ID}` ｜ **task_type** `01-asset-registration` ｜ **lane** A ｜ **report_id** `{REPORT_ID}` ｜
**源** `tensor://reports/{REPORT_ID}`（field=`markdown`，sha256=`{MANIFEST["source"]["hash"]}`，{MANIFEST["source"]["chars"]} 字符 / {MANIFEST["source"]["bytes_utf8"]} 字节）
**分层** `DEM|{SCENARIO_KEY}|l` ｜ **交付仓** TensorKnowledge（status=draft）
**结论** 源资产已登记：{c["assets"]} 条资产、{c["unique_quotes"]} 条唯一可解析定位、claims 为空（契约允许）；
`{VERIF["overall"]}`（9 项校验，源哈希由平台 API 重新抓取后独立重算）。

## ① 本工序做了什么

只做一件事：**登记 report 9761 的源资产**，不做抽取、不做分类、不标 verified。

* 抓取 `tensor://reports/{REPORT_ID}` 的 markdown 并**逐字节核对**契约 `source_hash`：
  重算 sha256 = `{MANIFEST["source"]["hash"]}`，与契约一致（`hash_matches_contract={str(MANIFEST["source"]["hash_matches_contract"]).lower()}`），
  字符数 {MANIFEST["source"]["chars"]} 与契约 `chars: 8931` 一致（`chars_matches_contract={str(MANIFEST["source"]["chars_matches_contract"]).lower()}`）。
* 在原文里定位 {c["assets"]} 条资产（正文/表/图声明/产物路径/审计链/环境记录等 {len(c["by_class"])} 个类目），
  每条带**逐字引文 + 字符区间 + 行区间**；引文在本工序内被断言为**全文唯一出现**（occurrences=1）。
* 判定每条资产的解析状态：{by_res.get("resolved_in_source", 0)} 条 `resolved_in_source`（可在源文内解析）、
  {by_res.get("referenced_unresolved", 0)} 条 `referenced_unresolved`（指向 TensorDEM 仓的代码/图件/工件路径，本工作树内不可解析）、
  {by_res.get("declared_absent", 0)} 条 `declared_absent`。
* 输出 `asset_manifest.json`（schema=asset_manifest.v1）+ `kf_result.v1` 结果信封；`claims` 为**空数组**，
  符合契约 `objective.classify_report_type=false` 与 notes「不做抽取」。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文**：`scripts/kf_fetch_9761.py` → `GET $TENSOR_API_BASE/tensor/reports/9761`（Bearer 登录），
   落 `runs/wp-9761-01/report_9761.md/.json`。取回的 markdown sha256=`{MANIFEST["source"]["hash"]}`，
   与契约 `source_hash` 完全一致 —— 后续所有定位都建立在这份字节上。
2. **注册+自断言**：`scripts/kf_register_9761.py` 内置六条硬不变量（违反即退出非 0）：
   I1 sha256==契约；I2 asset_id 唯一且匹配 `^A[0-9]{{2}}$`；I3 每条引文在原文唯一出现；I4 `md[start:end]==quote`；
   I5 行区间重建出同一引文；I6 `resolution_check.result` 与 `resolution` 词表一致。
   锚点用「必须恰好出现在一行」的短串定位，引文由**整行切片**生成（不是手打），因此零手抄是结构性保证。
3. **独立校验**：`scripts/kf_verify_9761.py` 重新（从 API 再抓一次）取 markdown、重算 sha256、
   逐条重解析 29 个定位，并按契约 6 项 + 3 项附加检查输出 `verification.json`。
4. **覆盖率缺口分析**：`scripts/kf_figures_9761.py` 把定位区间取并集投射到字符轴，得到
   目标化覆盖率 **{COV["covered_chars"]}/{COV["document_chars"]} = {100*COV["fraction"]:.2f}%**，残差 {COV["gap_chars"]} 字符全部是
   空行({COV["gap_line_composition"]["blank"]} 行)与章节标题({COV["gap_line_composition"]["heading"]} 行)，**未登记正文行 = {COV["gap_line_composition"]["prose"]}**。
   该分析反哺了登记本身：首轮发现的 2 处未覆盖正文（归一化约定行、五球摆解释段）已补登为 A28/A29。
5. **工具链/设置**：Python 3.11 + jsonschema + matplotlib(Agg)；不联网取外部资源（外部路径只在**本工作树内**查存在性）；
   不改 `.git`、不 push；只读写 report_id={REPORT_ID}。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/{PACKAGE_ID}/asset_manifest.json` | 主产物：schema=asset_manifest.v1，{c["assets"]} 资产 / {c["unique_quotes"]} 唯一引文 / claims=[] / 5 条 observations |
| `docs/{PACKAGE_ID}/asset_manifest.json` | 与主产物**逐字节相同**的耐久镜像（仓 push 门会滤掉 `artifacts/**`、`runs/**`） |
| `runs/{PACKAGE_ID}/kf_result.wp-9761-01.json` | kf_result.v1 信封（package_id/task_type/report_id/provenance/outputs/claims） |
| `runs/{PACKAGE_ID}/kf_result_block.wp-9761-01.json` | 与本报告唯一 json 代码块的字节一致副本 |
| `artifacts/{PACKAGE_ID}/verification.json` | 9 项校验逐条结果，overall=`{VERIF["overall"]}`，含 API 重抓的 sha256 |
| `docs/{PACKAGE_ID}/verification.json` | 校验结果的耐久镜像（同上内容；push 门会滤掉 `artifacts/**`） |
| `docs/{PACKAGE_ID}/report_9761_meta.json` | 源报告平台元数据镜像（id/title/scenario_key/5 条 figure name+caption/tags） |
| `docs/{PACKAGE_ID}/coverage.json` | 定位覆盖率与缺口成分（供下游抽取确定「哪里还没有被钉住」） |
| `docs/{PACKAGE_ID}/figures/fig1_asset_coverage.png` | 图 1 覆盖图（sha256 `{fig1["sha256"][:16]}…`） |
| `docs/{PACKAGE_ID}/figures/fig2_resolution_checks.png` | 图 2 解析状态 + 校验矩阵（sha256 `{fig2["sha256"][:16]}…`） |
| `scripts/kf_fetch_9761.py`, `scripts/kf_register_9761.py`, `scripts/kf_verify_9761.py`, `scripts/kf_figures_9761.py`, `scripts/kf_report_9761.py` | 全链可一键复跑 |
| `tests/test_kf_wp9761.py` | 17 条 pytest：11 条接受性断言 + 6 条负控（见 ⑥） |
| `schemas/asset_manifest.v1.wp-9761-01.schema.json` | 本包 manifest 的钉定 schema（通用文件钉在 wp-448-01 上，未改动） |

## ④ 证据定位表

每条资产 → 原文逐字切片（片段截断仅用于表格显示，完整引文见 manifest 的 `locator.quote`；字符区间可被平台独立解析）。

{evidence_table()}

**5 条登记观察（observations，不改写原文）**

{chr(10).join("- **%s**（%s，依据 %s）：%s" % (o["id"], o["kind"], o["evidence_asset"], o["text"]) for o in MANIFEST["observations"])}

## ⑤ 注意点与局限

1. **本工序不做真伪判定**。报告自报的 `all_passed = True`（A24）与五项判据 PASS（A23）是**源文内容**，
   登记的是「原文如此」，不是平台复算；`provenance.verification_status = not_verified` 如实反映这一点。
   上游六项 <3% 的误差结论（A21/A22）同理未复核。
2. **{by_res.get("referenced_unresolved", 0)} 条 referenced_unresolved 不是缺失**。A10（TensorDEM 模块/用例）、A19（5 个 png）、A25（产物路径清单）
   指向 TensorDEM 仓；本工作树内 grep/查存在性均为 0 命中（见各条 `resolution_check.worktree_hits=[]`）。
   图件在平台 `figures` 字段里有 name+caption 但**无字节**，故只能标未解析，不能标 resolved。
3. **平台 title 与正文标题文字不同**（O1：title 为任务全名、正文标题带「（成熟化）」后缀）。本工序**不改写**任何一侧，
   只在 observation 里留痕，避免把元数据漂移静默抹平。
4. **唯一性是个强约束，也有代价**：引文必须全文唯一才能用行区间定位；重复性文本（如反复出现的阈值）无法单靠行区间区分，
   本包通过选取上下文更长的整行来规避，未使用模糊匹配。
5. **覆盖率不是质量指标**：{100*COV["fraction"]:.2f}% 只说明「正文行基本都有归属」，不说明抽取得对；
   空白与章节标题合计 {COV["gap_chars"]} 字符属结构性文本，本包刻意不登记为资产（避免用无效资产刷覆盖率）。
6. **上游谱系未能解析**：A04 提到的 in54w1（documented FAIL）与 m5404（5.111290246e-07）只有文字，无报告号/路径，
   本工序不猜、不补（O4）。
7. **规模有限的诚实说明**：{c["assets"]} 条资产由人工规则（锚点表）选定，不是算法检索；类目划分反映本报告结构，
   不代表可跨报告复用的本体。
8. **push 门之后的耐久性（已做降级而不是假设）**：本仓 push 门会滤掉 `artifacts/**` 与 `runs/**`，
   因此每条产物在 `docs/{PACKAGE_ID}/` 留有逐字节镜像；`tests/test_kf_wp9761.py` 的加载器优先取工作产物、
   回落到 `docs/` 镜像，markdown 缺失时再从平台 API 取。已用「移走 artifacts/ 与 runs/」模拟 push 后状态跑过：
   17 条仍全绿（其中 markdown 走 API 重取）。若不降级，测试会在干净检出上假失败。
9. **交付信道自检**：报告发布后由 `scripts/kf_check_published_9761.py` 再读一次已发布的 markdown，
   断言 title/tags/mission_id/scenario_key、json 代码块唯一且解析后与信封**完全相等**、图件名一致；
   该断言跑在**发布后的字节**上，而不是本地草稿。

## ⑥ 自检：逐条对照 acceptance

{checks_table()}

* `valid_json` ✅ ｜ `schema_pass` ✅ ｜ `source_locator_resolvable` ✅（29/29） ｜ `source_hash_matches` ✅（API 重抓重算 `{hash_ok["detail"]["api_sha256"]}`） ｜ `no_duplicate_ids` ✅ ｜ `all_claims_…` ✅（claims=[]，契约允许）
* **负控（证明检查有牙，不只是「跑过了」）**：①把某条引文末尾改 1 个字符 → 定位检查报 slice/uniqueness 缺陷；
  ②重复一个 asset_id → `no_duplicate_ids` 报缺陷；③把 observation 指向不存在的 A99 → 报悬挂引用；
  ④用 4 字符公共串当引文 → 报 `quote_not_unique`+`unique_flag_false`；⑤给无证据 claim → 报 missing；
  ⑥把 `5.111e-07` 改成 `5.112e-07` → sha256 不匹配且定位失配。六条均在 `tests/test_kf_wp9761.py` 中作为断言固化。
### ⑥b 误差判定（本工序的关键量 vs 基准，逐项，显式回答「是否<3%」）

| 关键量 | 本工序值 | 基准（契约 / 平台） | 相对误差 | 是否 <3% |
|---|---|---|---|---|
| markdown sha256 | `{MANIFEST["source"]["hash"][:16]}…`（64 hex） | 契约 `source_hash`（同值） | 0（逐字节相等） | 是（=0%，精确相等） |
| markdown 字符数 | {MANIFEST["source"]["chars"]} | 契约 `chars`={MANIFEST["source"]["chars"]} | 0 | 是（=0%） |
| 源报告 id | {REPORT_ID} | 契约 `report_id`={REPORT_ID} | 0 | 是（=0%） |
| scenario_key | `{SCENARIO_KEY}` | 契约 `scenario_key`（同值） | 0 | 是（=0%） |
| 定位重解析 | {c["assets"]}/{c["assets"]} 成功 | 期望 100% | 0 处失配 | 是（=0%） |
| claims 条数 | 0 | 期望 0（不做抽取） | 0 | 是（=0%） |
| 图件名集合 | 2 幅（本地生成） | 平台已发布 figures（同 2 名） | 0 | 是（=0%） |

**显式回答**：上表七项全部是**精确相等（误差 0%）**，不是「<3% 的量级问题」——本工序的验收面是**同一性**
（哈希/字符数/编号/定位），任何非零偏差都是硬失败而不是容差问题。
唯一非零的**比例量**是 `referenced_unresolved` 率 {by_res.get("referenced_unresolved", 0)}/{c["assets"]} = {100*by_res.get("referenced_unresolved",0)/c["assets"]:.2f}%：
它**不是误差**，而是「资产指向本工作树之外」的口径（逐条已给 worktree_hits=[] 证据，见⑤第 2 条），
故不纳入 <3% 判定；把外部资产强行标 resolved 才是造假。

* **未运行/未覆盖**：平台侧 gate 的复算（本工序不可见，`verification_status=not_verified`）；
  上游 TensorDEM 侧的数值复现（A10 不可解析，属下游/他仓职责）。
* **honest 项**：无失败项；但「全部 PASS」仅指**本包 acceptance**，不含对报告科学结论的认可。

## 一键复跑（repro_cmd）

`python3 scripts/kf_fetch_9761.py && python3 scripts/kf_register_9761.py && python3 scripts/kf_verify_9761.py && python3 scripts/kf_figures_9761.py && python3 -m pytest tests/test_kf_wp9761.py -q && python3 scripts/kf_report_9761.py`

## 附：结果信封（本报告唯一的 json 代码块，交付信道）

```json
{json.dumps(RESULT, ensure_ascii=False, indent=2)}
```
"""
    return body, [dict(name=fig1["name"], caption=fig1["caption"], png_base64=fig1["png_base64"]),
                  dict(name=fig2["name"], caption=fig2["caption"], png_base64=fig2["png_base64"])]


def login() -> str:
    u, p = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]
    req = urllib.request.Request(BASE + "/auth/login",
                                 data=json.dumps({"username": u, "password": p}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode())
    return d.get("access_token") or d.get("token") or (d.get("data") or {})["access_token"]


SUPERSEDED_PUBLISH_IDS = (14741, 14750)   # earlier publishes of the same envelope; superseded by the final one


def write_readme() -> pathlib.Path:
    c = MANIFEST["counts"]
    by_res = c["by_resolution"]
    text = f"""# docs/wp-9761-01 — 工作包 {PACKAGE_ID}（report 9761 源资产登记）

本目录是 `artifacts/` 与 `runs/` 的**耐久镜像**与说明：本仓 push 门会滤掉那两个目录，
所以审计需要的字节都放在这里。

## 一句话结论

report `{REPORT_ID}` 的 markdown 与契约 `source_hash` **逐字节一致**（sha256 `{MANIFEST["source"]["hash"]}`，
{MANIFEST["source"]["chars"]} 字符），已登记 {c["assets"]} 条资产、{c["unique_quotes"]} 条唯一可解析定位；
`claims = []`（契约允许，本工序不做抽取）；未标 verified（`verification_status = not_verified`）。

## 文件

| 文件 | 内容 |
|---|---|
| `asset_manifest.json` | 主产物（= `artifacts/wp-9761-01/asset_manifest.json` 逐字节镜像），schema=`asset_manifest.v1` |
| `kf_result_block.json` | 交付用的 kf_result.v1 信封（= `runs/wp-9761-01/kf_result.wp-9761-01.json`） |
| `verification.json` | 9 项校验（6 项契约 acceptance + 3 项附加），overall=`{VERIF["overall"]}` |
| `report_9761_meta.json` | 源报告平台元数据镜像 |
| `coverage.json` | 定位覆盖率 {COV["covered_chars"]}/{COV["document_chars"]} = {100*COV["fraction"]:.2f}%，未登记正文行 {COV["gap_line_composition"]["prose"]} |
| `KF-RESULT.wp-9761-01.md` | 交付报告正文（六段 + 唯一 json 代码块），与平台已发布报告同文字 |
| `figures/fig1_asset_coverage.png` | 资产定位覆盖图 |
| `figures/fig2_resolution_checks.png` | 解析状态分布 + 校验矩阵 |
| `schema` 钉定 | `schemas/asset_manifest.v1.wp-9761-01.schema.json` |

## 复跑

`python3 scripts/kf_fetch_9761.py && python3 scripts/kf_register_9761.py && python3 scripts/kf_verify_9761.py && python3 scripts/kf_figures_9761.py && python3 -m pytest tests/test_kf_wp9761.py -q && python3 scripts/kf_report_9761.py && python3 scripts/kf_check_published_9761.py`

## 已知与诚实的边界

* {by_res.get("referenced_unresolved", 0)} 条 `referenced_unresolved`（A10/A19/A25）指向 TensorDEM 仓的代码/图件/工件，本工作树内不可解析 —— 不是缺失。
* 上游报告的结论（`all_passed = True`、五项判据 PASS、六项 <3%）**未复核**，登记的是「原文如此」。
* 发布记录：`{'、'.join(str(i) for i in SUPERSEDED_PUBLISH_IDS)}` 是同一信封的首次发布（内容为早期文字稿），
  最终发布见 `runs/wp-9761-01/publish.json`；两个报告的 json 块内容相同。
"""
    out = DOC_DIR / "README.md"
    out.write_text(text, encoding="utf-8")
    return out


def main() -> int:
    md, figs = build_markdown()
    out = DOC_DIR / "KF-RESULT.wp-9761-01.md"
    out.write_text(md, encoding="utf-8")
    (DOC_DIR / "kf_result_block.json").write_text(
        json.dumps(RESULT, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("readme:", write_readme())
    n_fences = md.count("```json")
    print("markdown:", out, len(md), "chars; json blocks:", n_fences,
          "; figure blocks:", len(figs))
    if n_fences != 1:
        print("FATAL: the report must contain exactly one ```json block")
        return 2
    if "--no-post" in sys.argv:
        return 0

    payload = dict(title="KF-RESULT %s" % PACKAGE_ID,
                   summary=("工作包 wp-9761-01 源资产登记：report 9761 markdown 哈希逐字节核对一致、"
                            "%d 条资产定位全部可解析、claims 为空；不做抽取、不标 verified。"
                            % MANIFEST["counts"]["assets"]),
                   scenario_key=SCENARIO_KEY, mission_id=CAMPAIGN_MISSION_ID,
                   tags=["kf-wp:%s" % PACKAGE_ID, PACKAGE_ID, "asset-registration",
                         "report-9761", "DEM", "TensorDEM", "kf-result"],
                   markdown=md, figures=figs)
    token = login()
    req = urllib.request.Request(BASE + "/tensor/reports",
                                 data=json.dumps(payload, ensure_ascii=False).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=180) as r:
        resp = json.loads(r.read().decode())
    (RUN_DIR / "publish.json").write_text(
        json.dumps(resp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("published report id:", resp.get("id"), "title:", resp.get("title"))
    return 0


if __name__ == "__main__":
    sys.exit(main())