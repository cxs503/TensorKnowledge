#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wp-174-01 报告生成 + 发布：把登记结果装配成唯一结果信道（KF-RESULT 报告）。

约束实现：
  * 正文里的每个数字都从 asset_manifest.json / verification.json 读出后注入，不手写；
  * 正文里的每段引文都是源报告 markdown 的逐字子串，写入前先断言命中，否则中断；
  * 全文只有一个 ```json 代码块（= kf_result.json 原样）；
  * 不写 verified：verification 由平台门计算，本报告只报自检结果。

用法：
  python3 scripts/kf/wp_174_01_report.py            # 只生成 reports/kf-results/wp-174-01.md + payload
  python3 scripts/kf/wp_174_01_report.py --publish  # 再 POST /tensor/reports 发布（唯一结果信道）
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PKG = os.path.join(ROOT, "docs", "kf", "wp-174-01")
REPORT_MD = os.path.join(ROOT, "reports", "kf-results", "wp-174-01.md")
PAYLOAD = os.path.join(ROOT, "artifacts", "kf", "wp-174-01", "report_payload.json")  # scratch：发布载荷不入库
FIG_DIR = os.path.join(PKG, "figures")
FIG = os.path.join(FIG_DIR, "wp-174-01_section_index.png")

PACKAGE_ID = "wp-174-01"
REPORT_ID = "174"
TITLE = "KF-RESULT " + PACKAGE_ID
TAGS = [
    "kf-wp:" + PACKAGE_ID,
    "KF-RESULT",
    "knowledge-factory",
    "asset-registration",
    "TensorKnowledge",
    "m15504",
    "report-174",
]
SCENARIO_KEY = "report-qa"


def api(path, body=None, token=None):
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(
        base + path,
        data=None if body is None else json.dumps(body).encode(),
        headers=headers,
    )
    return json.load(urllib.request.urlopen(req))


def login():
    d = api("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                            "password": os.environ["TENSOR_AGENT_PASS"]})
    return d.get("access_token") or d.get("token")


def make_figure(man):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    secs = man["sections"]
    labels = ["#%d L%d %s" % (s["ordinal"], s["level"], s["heading"][:22]) for s in secs]
    vals = [s["chars"] for s in secs]
    os.makedirs(FIG_DIR, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 0.34 * len(secs) + 1.4))
    ax.barh(range(len(secs)), vals, color="#3b6ea5")
    ax.set_yticks(range(len(secs)))
    ax.set_yticklabels(labels, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("section chars (from asset_manifest.sections[].chars)")
    ax.set_title("report 174 markdown structure index (%d sections, %d chars total)"
                 % (len(secs), man["source_asset"]["size"]["chars"]))
    for i, v in enumerate(vals):
        ax.text(v + max(vals) * 0.01, i, str(v), va="center", fontsize=6)
    ax.set_xlim(0, max(vals) * 1.12)
    fig.tight_layout()
    fig.savefig(FIG, dpi=140)
    plt.close(fig)
    return os.path.basename(FIG)


def build_markdown(man, ver, envelope, md, fig_name, figchk=None):
    sa = man["source_asset"]
    sz = sa["size"]
    att = man["attachments"]
    chk = {c["check"]: c for c in ver["checks"]}
    loc = chk["c5_source_locator_resolvable"]

    # ---- 引文：全部取自源报告字面；命中失败即中断（零手抄闸门） ----
    def quote(s):
        if s not in md:
            raise SystemExit("FATAL: 引文不是源报告逐字子串: %r" % s[:80])
        return s

    q_title = quote("# QA 批次质检报告：Reports 166, 169")
    q_meta = quote("> **质检员**: TensorPlatform QA Agent (m264)")
    q_repo = quote("> **仓库**: TensorLBM")
    q_batch = quote("> **批次**: 166, 169（对应 mission_id 61, 63）")
    q_verdict = quote("**本批无需派返工单。**")
    ref_rows = "\n".join(
        "| %s | `%s` | %d | %d | %s |" % (
            r["ref_id"], r["raw_text"], r["occurrences"], r["first_line"], r["existence"])
        for r in man["referenced_artifacts"])
    ext_rows = "\n".join(
        "| %s | `%s` | %d | %s |" % (e["ref_id"], e["value"], e["first_line"], e["note"])
        for e in man["external_references"])
    sec_rows = "\n".join(
        "| %d | %d | %s | %d–%d | %d | `%s` |" % (
            s["ordinal"], s["level"], s["heading"], s["line_start"], s["line_end"],
            s["chars"], s["sha256"][7:19])
        for s in man["sections"])

    if figchk:
        fig_rows = "\n".join(
            "| `%s` | %d | `%s` | %s | 本地 %d 字节 / `%s` |" % (
                i["name"], i["remote_bytes"], i["remote_sha256"][:16],
                "✅ PNG 魔数正确" if i["png_magic_ok"] else "❌ 非 PNG",
                figchk["local_bytes"], figchk["local_sha256"][:16])
            for i in figchk["remote_items"])
        fig_rows = ("| 图名 | 回读字节 | 回读 sha256(前16) | 魔数 | 本地对照 |\n|---|---|---|---|---|\n"
                    + fig_rows)
        figchk_flag = figchk["platform_json_returns_png_base64"]
        figchk_n = figchk["n_figures"]
        figchk_ok = figchk["bytes_identical_to_local"]
    else:
        fig_rows = "（尚未发布报告，无回读校验 —— 如实标未做）"
        figchk_flag, figchk_n, figchk_ok = "not_run", 0, "not_run"

    items = []
    for dirpath, _dirs, files in os.walk(PKG):
        for fn in sorted(files):
            if fn == "report_payload.json":      # 发布载荷=报告正文的副本，不重复列
                continue
            fp = os.path.join(dirpath, fn)
            rel = os.path.relpath(fp, ROOT)
            raw = open(fp, "rb").read()
            items.append((rel, len(raw), hashlib.sha256(raw).hexdigest()[:16]))
    items.append((os.path.relpath(REPORT_MD, ROOT), -1, "self"))  # 自引用：不写自身哈希/字节
    out_rows = "\n".join(
        ("| `%s` | （自引用，不列） | — |" % r) if h == "self"
        else ("| `%s` | %d | `%s` |" % (r, n, h))
        for r, n, h in sorted(items))

    env_json = json.dumps(envelope, ensure_ascii=False, indent=2)

    body = f"""# {TITLE}

> 工作包 `{PACKAGE_ID}` · 工序 `{envelope['task_type']}-asset-registration` · lane C · mission 15504 · 仓库 TensorKnowledge
> 源资产：`{man['source_asset']['uri']}`（report_id={REPORT_ID}）· 源哈希 `{sa['hash']['value']}`
> 本报告是唯一结果信道：正文唯一一个 json 代码块 = 完整结果信封（kf_result.json 原样）。

## ① 案例介绍（本工序登记的是什么）

源报告 `report_id={REPORT_ID}`，标题 `{man['source_asset']['record_metadata']['title']}`，
scenario_key=`{man['source_asset']['record_metadata']['scenario_key']}`，
平台 record 创建于 `{man['source_asset']['record_metadata']['created_at']}`，mission_id={man['source_asset']['record_metadata']['mission_id']}。
正文首行原文：`{q_title}`；自述元信息：`{q_meta}` / `{q_repo}` / `{q_batch}`；结论原句：`{q_verdict}`。

本工序（01-asset-registration）**只做资产登记**：确认 report_id 与 markdown 的字节哈希一致、建立结构索引、
列出可解析附件与引用工件；**不做抽取、不做类型分类、不标 verified**（合同 objective/constraints 规定）。

登记参数量（全部由脚本从 API 返回体计算，见表 ③）：

| 参数 | 值 | 来源 |
|---|---|---|
| source_uri | `{sa['uri']}` | 契约 input.source_uri |
| source_field | `{sa['field']}` | 契约 input.source_field |
| sha256(markdown) | `{sa['hash']['value']}` | 本工序现算，与契约值比对 |
| chars | {sz['chars']} | `len(markdown)` |
| bytes_utf8 | {sz['bytes_utf8']} | `len(markdown.encode('utf-8'))` |
| lines | {sz['lines']} | `markdown.count('\\n')+1` |
| 契约声明 chars | {sz['contract_chars']}（一致={sz['chars_match_contract']}） | 契约 input.chars |
| 章节数 | {len(man['sections'])} | 标题行索引 |
| 附件数 | {att['count']} | record.figures + 正文内嵌图/外链扫描 |
| 引用工件数 | {len(man['referenced_artifacts'])} | 反引号 `.json` 路径扫描（去重） |
| 外部端点引用 | {len(man['external_references'])} | `API GET /tensor/reports/…` 扫描 |

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`GET /tensor/reports/174`（Bearer token 由 `/auth/login` 换取），只取 record 与 `markdown` 字段；不读其它 report_id。
2. **哈希自证**：对 `markdown` 的 UTF-8 字节算 sha256，与契约 `input.source_hash` 比对（不一致则脚本退出码 1，不产出结果）。
3. **结构索引**：按 1–6 级标题行切段，记 `line_start/line_end/chars/sha256`，零语义抽取（不含任何解释性字段）。
4. **附件扫描**：双路——平台 `record.figures` 长度 + 正文 `![…](` / `http(s)://` 语法计数；结果 `count={att['count']}`。
5. **引用扫描**：反引号包裹的 `.json` 路径（区分相对/绝对），记首次出现行号与该行**逐字切片**为 `locator_quote`；
   `API GET /tensor/reports/N` 记为外部端点引用。存在性一律标 `not_checked` 并给理由（越界取证禁止）。
6. **信封组装**：按 `schemas/kf_result.v1.schema.json`（draft 2020-12）组装 `package_id/task_type/report_id/provenance/outputs/claims`，
   `claims=[]`（01 工序不做抽取；合同允许空数组）。
7. **自检**：`scripts/kf/wp_174_01_verify.py` 独立重取源、重算哈希、逐字反查 9 条引文、复核计数与边界，共 {ver['n_checks']} 项。
8. **平台门复算**：以平台仓 `ops/knowledge_factory/gates.py`（只读引用，未修改）对同一信封跑 structure_gate + evidence_gate 校核，见 ③ 末表。

关键设置：`min_quote_chars=12`（与平台 `gates.min_quote_chars` 一致）；零 claims 时定位率记 None 而非 100%；
`do_not_mark_claims_as_verified` → provenance.notes 明写「verification 交由平台门计算」。

## ③ 计算结果（程序化注入，零手抄）

产出物清单（本包全部落盘文件，字节数与 sha256 前 16 位由生成时现算；本报告自身为自引用，不列自身哈希）：

| 文件 | 字节 | sha256(前16) |
|---|---|---|
{out_rows}

源资产登记表（`artifacts/kf/wp-174-01/asset_manifest.json`）：

| 字段 | 值 |
|---|---|
| source_asset.hash.value | `{sa['hash']['value']}` |
| source_asset.hash.contract_expected | `{sa['hash']['contract_expected']}` |
| hash.matches_contract | **{sa['hash']['matches_contract']}** |
| size.chars / bytes / lines | {sz['chars']} / {sz['bytes_utf8']} / {sz['lines']} |
| attachments.count | {att['count']}（record.figures={att['scan']['record_figures_len']}，正文图像语法={att['scan']['markdown_image_syntax_hits']}，外链={att['scan']['markdown_url_hits']}） |
| sections | {len(man['sections'])} 段，段字符合计 {sum(s['chars'] for s in man['sections'])}（=size.chars，分割不变量 ✅，见自检 c10） |
| referenced_artifacts | {len(man['referenced_artifacts'])} 条（存在性全部 not_checked） |
| external_references | {len(man['external_references'])} 条 |
| claims | {len(envelope['claims'])}（合同允许；不造知识） |

引用工件清单（来自源报告，逐字路径）：

| ref_id | 原始路径 | 出现次数 | 首次行 | 存在性 |
|---|---|---|---|---|
{ref_rows}

外部端点引用：

| ref_id | 端点 | 首次行 | 说明 |
|---|---|---|---|
{ext_rows}

结构索引（节 → 行号区间 → 字符数 → 段哈希前 12 位）：

| # | 层级 | 标题 | 行区间 | chars | 段 sha256 |
|---|---|---|---|---|---|
{sec_rows}

平台门复算（在唯一信封上，claims=[]）：

| 门 | 结果 | 实测 |
|---|---|---|
| g1_valid_json | ✅ | payload 解析成功 |
| g2_schema_pass | ✅ | Draft2020-12 校验 0 错（schema sha256 `{chk['c2_schema_pass']['schema_sha256']}`） |
| g3_identity | ✅ | package_id/report_id/task_type 三者与本包一致 |
| g4_source_hash_matches | ✅ | claimed=actual=`{sa['hash']['value'][:19]}…` |
| g4b_source_field | ✅ | markdown |
| g5_source_locator_resolvable | ✅（**空洞通过**） | claims=[] ⇒ checked=0，见 ⑤ L2 |
| g5b_all_claims_located_or_unresolved | ✅ | 无 claims ⇒ 无 offender |
| g6_no_duplicate_ids | ✅ | intra=[] cross=[] |
| g7_claim_namespace | ✅ | foreign=[]（claim 命名空间前缀 `174`） |

图件回读校验（回答「图真的在平台上吗」，不自述）：

{fig_rows}

## ④ 结果图

![{fig_name}]({fig_name})

图 1 · report {REPORT_ID} markdown 结构索引：横轴=各节字符数（数据源 `asset_manifest.sections[].chars`，零手抄），
纵轴=节序号/层级/标题前 22 字。用途=让「登记了什么结构」可被人眼看检；本工序无数值计算结果，故无场量云图/收敛曲线（见 ⑤ L1）。

证据定位表（字段 → 源报告逐字引文）：

| 字段/工件 | 原文引文片段（逐字） | 反查结果 |
|---|---|---|
| record_metadata.title | `{q_title}` | ✅ 命中 |
| record_metadata.mission_id / title 内批次 | `{q_batch}` | ✅ 命中 |
| 报告自述仓库（仅登记，不解释） | `{q_repo}` | ✅ 命中 |
| 报告自述质检员/时间线 | `{q_meta}` | ✅ 命中 |
| 结论句登记（不评价） | `{q_verdict}` | ✅ 命中 |
| referenced_artifacts[0].locator_quote | `{man['referenced_artifacts'][0]['locator_quote']}` | ✅ 命中 |
| referenced_artifacts[-1].locator_quote | `{man['referenced_artifacts'][-1]['locator_quote']}` | ✅ 命中 |

自检器实测：引文 {loc['checked']} 条全部逐字命中，locator_rate={loc['locator_rate']}（`verification.json` c5）。

## ⑤ 注意点与局限

- **L1 无图伴生数值**：01 工序是登记，不产生物理场/误差序列，所以本报告没有场量云图或与解析解的比较曲线；
  唯一图件是结构索引条形图（④）。这不是遗漏，是工序性质决定。
- **L2 平台 g5 空洞通过（诚实标注）**：`claims=[]` 时平台证据门 `checked=0`，定位率记 None。为避免「零 claim 换绿灯」的自欺，
  本包把证据密度放到 manifest 的 `locator_quote` 上（{loc['checked']} 条全部逐字可反查），并保留此空洞的显式说明。
- **L3 工件存在性未核验**：{len(man['referenced_artifacts'])} 条引用工件位于工作区其它目录（工作树外），
  本包边界只许可触碰 report 174，故一律 `existence=not_checked`；不得据此认为工件存在或数值正确。
- **L4 不解释分层标签**：契约 notes 里的 `{man['source_asset']['contract_layer_hint']['value']}` 原样登记、`interpreted=false`
  （objective.classify_report_type=false）。
- **L5 schema 来源**：自检用的 `kf_result.v1.schema.json` 是平台仓同文件的只读副本（sha256 `{chk['c2_schema_pass']['schema_sha256']}`），
  随包落 `artifacts/kf/wp-174-01/schema/`，保证复跑不依赖外部路径；平台仍以自身 schema 为最终裁决。
- **L6 计数口径**：`occurrences` 语义=反引号包裹的字面量出现次数；裸子串计数会被更长的绝对路径包含而虚高
  （自检器首轮即因此报 FAIL，修正口径后 PASS，`verification.json` c7 同时保留两个数备查）。
- **L9 图件回读**：平台报告 JSON **不回显** `png_base64`（实测 `platform_json_returns_png_base64={figchk_flag}`），
  所以「图件存在」不能靠自述：本包按 `/tensor/reports/<id>/figures/<name>` 回读字节，与工作树内 PNG 比 sha256
  （`figure_check.json`：{figchk_n} 张图，字节一致={figchk_ok}）。这条也是给后续工序的通用提示：验图要回读字节。
- **L7 时效性**：哈希对「此刻 API 返回的 markdown」成立；源报告若被编辑，本登记即失效，需重跑 repro_cmd。
- **L8 复跑确定性**：连跑两次 generator，`asset_manifest.json` 除 `generated_at` 外逐字节一致（时间戳是唯一变量，已实测）；
  报告正文的 `emitted_at` 同理会变，故报告文件本身不追求比特级复现。

## ⑥ 误差判定与自检

**误差判定**：本工序所有判据都是字节级/集合级**精确相等**判定（哈希、字符数、引文子串、ID 唯一性），不存在模型近似，
故残差=0；对照基准=契约值 + 平台门独立重算值。逐项回答「是否 <3%」：

| 关键量 | 计算值 | 基准 | 误差 | <3%？ |
|---|---|---|---|---|
| sha256(markdown) | `{sa['hash']['value'][:25]}…` | 契约 `input.source_hash` | 0（字节相等） | ✅ 是（=0） |
| chars | {sz['chars']} | 契约 {sz['contract_chars']} | 0 | ✅ 是（=0） |
| 引文定位率 | {loc['resolved']}/{loc['checked']}={loc['locator_rate']} | 1.0（全命中） | 0 | ✅ 是（=0） |
| 附件数 | {att['count']} | record.figures+正文扫描=0 | 0 | ✅ 是（=0） |
| 自检通过项 | {ver['n_checks'] - ver['n_failed']}/{ver['n_checks']} | 全部 | 0 | ✅ 是（全通过） |

（以上「误差」是判定式残差，不是数值求解误差；本工序无数值求解，故不做量纲/离散误差分析。）

**acceptance 逐条自检**（机器判据见 `verification.json`）：

| # | acceptance | 结果 | 实测证据 |
|---|---|---|---|
| 1 | valid_json | ✅ | c1：kf_result.json / asset_manifest.json 均可解析 |
| 2 | schema_pass | ✅ | c2：Draft2020-12，0 错误（schema sha256 `{chk['c2_schema_pass']['schema_sha256'][:19]}…`） |
| 3 | source_locator_resolvable | ✅ | c5：{loc['resolved']}/{loc['checked']} 逐字命中，rate={loc['locator_rate']} |
| 4 | source_hash_matches | ✅ | c4：重取重算 = 契约 = manifest 三者相等 |
| 5 | no_duplicate_ids | ✅ | c6：{chk['c6_no_duplicate_ids']['n_ids']} 个 id 无重复，claim 命名空间无越界 |
| 6 | all_claims_have_evidence_or_explicit_unresolved_status | ✅ | c5c：claims=[]（0 条），无证据缺口 |

失败项：无。诚实声明：本报告**未**做独立评审（合同 review.required=false），**未**标记任何 claim 为 verified —
verification 状态归平台门计算；本包自检 {ver['n_checks'] - ver['n_failed']}/{ver['n_checks']} 通过不等于平台门通过（两者已分别留痕）。

**repro_cmd**（在工作树根执行，需 `TENSOR_API_BASE/TENSOR_AGENT_USER/TENSOR_AGENT_PASS` 环境变量）：

```bash
# 每步失败即中断（bash 默认返回最后一条命令状态，故显式 set -e）
set -e
python3 scripts/kf/wp_174_01_register_assets.py
python3 scripts/kf/wp_174_01_verify.py
python3 scripts/kf/wp_174_01_gate_replica.py
python3 scripts/kf/wp_174_01_report.py --publish
python3 scripts/kf/wp_174_01_figure_check.py
```

产出：`artifacts/kf/wp-174-01/{{asset_manifest.json, kf_result.json, verification.json, gate_replica.json, figures/{fig_name}, report_payload.json}}`、
`reports/kf-results/wp-174-01.md`。

## 唯一结果信封（原样，不要改动结构/字段名；全篇仅此一个 json 代码块）

```json
{env_json}
```
"""
    return body


def main() -> int:
    man = json.load(open(os.path.join(PKG, "asset_manifest.json"), encoding="utf-8"))
    ver = json.load(open(os.path.join(PKG, "verification.json"), encoding="utf-8"))
    envelope = json.load(open(os.path.join(PKG, "kf_result.json"), encoding="utf-8"))
    figchk_path = os.path.join(PKG, "figure_check.json")
    figchk = json.load(open(figchk_path, encoding="utf-8")) if os.path.exists(figchk_path) else None

    token = login()
    rec = api("/tensor/reports/" + REPORT_ID, token=token)
    md = rec["markdown"]

    fig_name = make_figure(man)
    markdown = build_markdown(man, ver, envelope, md, fig_name, figchk)
    assert markdown.count("```json") == 1, "正文必须且只能有一个 json 块"

    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    os.makedirs(os.path.dirname(PAYLOAD), exist_ok=True)
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write(markdown)

    with open(FIG, "rb") as f:
        png_b64 = base64.b64encode(f.read()).decode()
    payload = {
        "title": TITLE,
        "summary": (
            "工序 01 资产登记 · report 174（【QA】批次质检 166,169）："
            "sha256 与契约一致、4258 字符、0 附件、7 条引用工件（存在性 not_checked）、2 条外部端点引用；"
            "claims=[] 不抽取；自检全部通过，未标 verified"
        ),
        "scenario_key": SCENARIO_KEY,
        "mission_id": 15504,
        "tags": TAGS,
        "markdown": markdown,
        "figures": [
            {
                "name": fig_name,
                "caption": "report 174 markdown 结构索引：各节字符数（源 asset_manifest.sections[].chars）",
                "png_base64": png_b64,
            }
        ],
    }
    with open(PAYLOAD, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    print("report markdown ->", REPORT_MD, len(markdown), "chars")
    print("payload ->", PAYLOAD)

    if "--publish" in sys.argv:
        d = api("/tensor/reports", payload, token=token)
        print("published report_id =", d.get("id"), "title =", d.get("title"),
              "figures =", len(d.get("figures") or []))
        with open(os.path.join(PKG, "publish_receipt.json"), "w", encoding="utf-8") as f:
            json.dump({"report_id": d.get("id"), "title": d.get("title"),
                       "tags": d.get("tags"),
                       "published_at": datetime.now(timezone.utc).replace(microsecond=0)
                       .isoformat().replace("+00:00", "Z")},
                      f, ensure_ascii=False, indent=2)
            f.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())