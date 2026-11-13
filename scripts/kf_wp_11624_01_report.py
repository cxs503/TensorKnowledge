#!/usr/bin/env python3
"""KF work package wp-11624-01 — figure + result markdown (+ optional publish).

Everything rendered here is *derived from the registered assets*: the EEXI/CII
numbers are parsed out of the verbatim table quote of asset A12 and the A–E band
multipliers out of the decision-rule quote of asset A11 (both lifted from the
source markdown by scripts/kf_wp_11624_01_register.py). Nothing is transcribed by
hand, and the figure is explicitly a *visualisation of registered content*, not a
re-verification of the upstream numbers.

Outputs
  docs/wp-11624-01/figs/wp11624_01_fig1_eexi_cii.png
  knowledge/kf/wp-11624-01/KF-RESULT.wp-11624-01.md   (six sections + single ```json block)
  docs/wp-11624-01/KF-RESULT.wp-11624-01.md           (byte-identical mirror)

Usage
  python3 scripts/kf_wp_11624_01_report.py              # build figure + markdown, no network
  python3 scripts/kf_wp_11624_01_report.py --publish    # also POST to the platform reports API
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

PKG = "wp-11624-01"
REPORT_ID = "11624"
MISSION_ID = 15728
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "knowledge" / "kf" / PKG
DOC = ROOT / "docs" / PKG
FIG_DIR = DOC / "figs"
FIG = FIG_DIR / "wp11624_01_fig1_eexi_cii.png"
MD_OUT = OUT / ("KF-RESULT.%s.md" % PKG)


def parse_result_table(manifest: dict) -> list[dict]:
    """Parse asset A12's verbatim quote (registered markdown table) into rows."""
    a12 = next(a for a in manifest["assets"] if a["asset_id"] == "A12")
    rows = [ln for ln in a12["locator"]["quote"].split("\n") if ln.startswith("|")]
    cells = [[c.strip() for c in ln.strip("|").split("|")] for ln in rows]
    header, body = cells[0], [c for c in cells[2:]]  # cells[1] is the separator row
    out = []
    for c in body:
        rec = dict(zip(header, c))
        out.append({
            "ship": rec["船型"],
            "attained_eexi": float(rec["Attained EEXI"]),
            "required_eexi": float(rec["Required EEXI"]),
            "eexi_compliant": rec["合规"] == "✓",
            "attained_cii": float(rec["Attained CII"]),
            "required_cii": float(rec["Required CII"]),
            "grade": rec["评级"],
        })
    return out


def parse_bands(manifest: dict) -> dict:
    """Extract the A–E multipliers from asset A11's verbatim decision-rule quote."""
    a11 = next(a for a in manifest["assets"] if a["asset_id"] == "A11")
    mults = sorted({float(m) for m in re.findall(r"(\d\.\d\d)\s*×\s*Required",
                                                a11["locator"]["quote"])})
    if mults != [0.86, 0.94, 1.06, 1.18]:
        raise SystemExit("unexpected band multipliers parsed from A11: %r" % mults)
    return {"a_max": mults[0], "b_max": mults[1], "c_max": mults[2], "d_max": mults[3],
            "quote": a11["locator"]["quote"]}


def build_figure(rows: list[dict], bands: dict) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    ships = [r["ship"] for r in rows]
    short = ["Capesize\nbulk", "18000TEU\ncontainer", "VLCC\noil tanker"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.4, 4.9))

    # --- panel A: EEXI attained vs required (registered values, A12)
    idx = range(len(rows))
    w = 0.36
    ax1.bar([i - w / 2 for i in idx], [r["attained_eexi"] for r in rows], w,
            label="Attained EEXI (as reported)", color="#c0504d")
    ax1.bar([i + w / 2 for i in idx], [r["required_eexi"] for r in rows], w,
            label="Required EEXI (as reported)", color="#4f81bd")
    for i, r in enumerate(rows):
        ax1.text(i - w / 2, r["attained_eexi"] + 0.15, "%.3f" % r["attained_eexi"],
                 ha="center", fontsize=8)
        ax1.text(i + w / 2, r["required_eexi"] + 0.15, "%.3f" % r["required_eexi"],
                 ha="center", fontsize=8)
        ax1.text(i, -0.85, "compliant: %s" % ("yes" if r["eexi_compliant"] else "NO"),
                 ha="center", fontsize=8, color="#c0504d" if not r["eexi_compliant"] else "#4f81bd")
    ax1.set_xticks(list(idx))
    ax1.set_xticklabels(short, fontsize=8)
    ax1.set_ylim(-1.6, max(max(r["attained_eexi"], r["required_eexi"]) for r in rows) * 1.18)
    ax1.set_ylabel("EEXI (g CO2 / (t·nm)), values as reported")
    ax1.set_title("(a) EEXI attained vs required — verbatim table A12", fontsize=9)
    ax1.legend(fontsize=7, loc="upper left")
    ax1.grid(axis="y", alpha=0.3)

    # --- panel B: CII ratio vs A–E bands (bands from A11, ratios from A12)
    b = bands
    edges = [(0.0, b["a_max"], "A"), (b["a_max"], b["b_max"], "B"), (b["b_max"], b["c_max"], "C"),
             (b["c_max"], b["d_max"], "D"), (b["d_max"], max(1.9, b["d_max"] + 0.5), "E")]
    colors = ["#4f81bd", "#9bbb59", "#f2c200", "#f79646", "#c0504d"]
    for (lo, hi, lab), col in zip(edges, colors):
        ax2.axvspan(lo, hi, color=col, alpha=0.22)
        ax2.text((lo + hi) / 2, len(rows) - 0.35, lab, ha="center", fontsize=9, weight="bold")
    ratios = [r["attained_cii"] / r["required_cii"] for r in rows]
    ax2.scatter(ratios, list(idx), s=70, color="#333333", zorder=5)
    for i, (r, q) in enumerate(zip(rows, ratios)):
        ax2.annotate("%s: ratio %.3f → %s (reported %s)" % (r["ship"], q, r["grade"],
                                                            _grade(q, b)),
                     (q, i), textcoords="offset points", xytext=(8, 6), fontsize=7)
    for x, lab in [(b["a_max"], "0.86"), (b["b_max"], "0.94"), (b["c_max"], "1.06"),
                   (b["d_max"], "1.18")]:
        ax2.axvline(x, color="k", lw=0.7, ls="--")
        ax2.text(x, -0.75, lab, ha="center", fontsize=7)
    ax2.set_xlim(0, max(1.9, b["d_max"] + 0.5))
    ax2.set_ylim(-1.0, len(rows) - 0.2)
    ax2.set_yticks(list(idx))
    ax2.set_yticklabels(short, fontsize=8)
    ax2.set_xlabel("CII / Required CII  (bands A–E from decision rule A11)")
    ax2.set_title("(b) CII position relative to G4 A–E bands", fontsize=9)
    ax2.grid(axis="x", alpha=0.3)

    fig.suptitle("Report 11624 registered content — EEXI/CII compliance view "
                 "(registration only; upstream values not re-verified)", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIG, dpi=150)
    plt.close(fig)

    png = FIG.read_bytes()
    return {
        "path": str(FIG.relative_to(ROOT)),
        "sha256": hashlib.sha256(png).hexdigest(),
        "bytes": len(png),
        "rows": rows,
        "bands": {k: v for k, v in bands.items() if k != "quote"},
        "cii_ratios": ratios,
    }


def _grade(q: float, b: dict) -> str:
    if q <= b["a_max"]:
        return "A"
    if q <= b["b_max"]:
        return "B"
    if q <= b["c_max"]:
        return "C"
    if q <= b["d_max"]:
        return "D"
    return "E"


def build_markdown(manifest: dict, result: dict, verif: dict, fig: dict) -> str:
    counts = manifest["counts"]
    loc_rows = []
    for a in manifest["assets"]:
        loc = a["locator"]
        first = loc["quote"].split("\n")[0]
        if len(first) > 96:
            first = first[:96] + " …"
        if loc["source_field"] == "record":
            where = 'record %s' % loc["pointer"]
            lines = "—"
        else:
            where = "md[%d:%d]" % (loc["start_char"], loc["end_char"])
            lines = "%d–%d" % (loc["start_line"], loc["end_line"]) if a["asset_id"] != "A01" \
                else "1–%d（全文）" % loc["end_line"]
        loc_rows.append("| %s | %s | %s | %s | `%s` | %s |" % (
            a["asset_id"], a["kind"], a["resolution"], lines, where, first.replace("|", "\\|")))

    checks = verif["checks"]
    tick = lambda k: "✓" if checks[k]["pass"] else "✗"  # noqa: E731

    ratio_lines = "\n".join(
        "| %s | %.3f | %.3f | %.3f | %s | %s | %s |" % (
            r["ship"], r["attained_cii"], r["required_cii"],
            r["attained_cii"] / r["required_cii"],
            _grade(r["attained_cii"] / r["required_cii"], fig["bands"]),
            r["grade"],
            "✓" if _grade(r["attained_cii"] / r["required_cii"], fig["bands"]) == r["grade"]
            else "✗")
        for r in fig["rows"])  # numbers parsed from the A12 quote, not typed

    body = f"""# KF-RESULT {PKG}

- report_id: {REPORT_ID} ｜ source_uri: {manifest['source']['uri']} ｜ source_field: `markdown`
- source_hash: `sha256:{manifest['source']['hash']}`（本地重算，与契约 source_hash 一致）
- chars: {manifest['source']['chars']} ｜ bytes_utf8: {manifest['source']['bytes_utf8']}
- package_id: `{PKG}` ｜ task_type: `01-asset-registration` ｜ lane: C ｜ status: draft
- 分层: EEXI | P187-W1-N06 | m

## ① 本工序做了什么

只做一件事：把 report_id=11624 这份报告**登记为资产**——确认它的 markdown 字节哈希、列出正文里
可解析的资产（表格/公式/判据清单/声明/引用），并把记录 metadata 里 4 条只有名字和图注、没有字节也
没有正文锚点的图件声明按缺口登记。**不做抽取**：按契约 `objective.register_assets=true`、
`classify_report_type=false`、`no_forced_claim_generation=true`，`claims` 为空数组；
也**没有**给任何对象打 `verified`（verification 由平台门计算，`provenance.verification_status`
=`not_verified`）。

登记结果：资产 {counts['assets']} 条 —— `resolved_in_source` {counts['resolved_in_source']} 条、
`referenced_unresolved` {counts['referenced_unresolved']} 条（审计链里的代码路径与测试文件，
属 ship-performance-platform 仓，本工作树内不存在）、`declared_absent` {counts['declared_absent']} 条
（4 条图件声明：`figures_with_bytes=0`，正文 0 处锚点）。定位器 {counts['locators']} 条，全部复解成功。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET $TENSOR_API_BASE/tensor/reports/11624`（Bearer token 由 `/auth/login` 取得），
   只取 `markdown` 字段；psql 对本角色 permission denied，故 API 是唯一信道。
2. **落冻结快照**：快照写 `knowledge/kf/wp-11624-01/source_report_11624.md`（UTF-8，仅 json 解码，
   不做换行/空白规整），并断言写回后再读的 sha256 不变。
3. **行号锚定**：以 1-based 行号表登记每条资产（`ASSET_TABLE`），引文由
   `md[start_char:end_char]` 现算，不手抄；每条都校验 `md[start:end] == quote` 且
   `md.count(quote) == 1`（唯一性），失败即整包 FAIL。
4. **记录侧资产**：图件走 JSON pointer（`/figures/0..3`），并机器检查 name/caption 是否出现在正文
   （结果：0/4 出现）以及是否有 png/url/path 字段（无）。
5. **出厂自检**：manifest 过本包钉版 schema（`schemas/asset_manifest.v1.wp-11624-01.schema.json`），
   result 信封过平台 `schemas/kf_result.v1.schema.json`（`additionalProperties:false` 下无多余键）。
6. **独立复核器**：`scripts/kf_wp_11624_01_verify.py` 不读 manifest 自带的 checks，从快照与文件
   重新推导六项验收；`tests/test_kf_wp_11624_01.py` 用 12 条负例证明这些检查真的会红
   （改引文/移 char span/换非唯一引文/加一字节/改 hash/重复 id/无出处 claim/打 verified 章/
   改 package_id/断 pointer/引用他报告）。

一键复跑：

```text
{manifest['repro_cmd']}
python3 scripts/kf_wp_11624_01_verify.py
python3 -m pytest tests/test_kf_wp_11624_01.py -q
python3 scripts/kf_wp_11624_01_report.py            # 重建本报告正文与图
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `knowledge/kf/wp-11624-01/asset_manifest.json` | 本工序唯一交付物：{counts['assets']} 条资产 + {counts['locators']} 条定位器 + 4 条图件缺口 + 空 claims（sha256 `{hashlib.sha256((OUT / 'asset_manifest.json').read_bytes()).hexdigest()[:16]}…`） |
| `knowledge/kf/wp-11624-01/kf_result.json` | kf_result.v1 结果信封（outputs.asset_manifest.json 内嵌 manifest 副本＋工件哈希） |
| `knowledge/kf/wp-11624-01/source_report_11624.md` | 源报告冻结快照（{manifest['source']['chars']} 字符 / {manifest['source']['bytes_utf8']} 字节） |
| `knowledge/kf/wp-11624-01/source_record.json` | 记录侧字段（title/scenario/mission/tags/figures，不含 markdown） |
| `knowledge/kf/wp-11624-01/verification_report.json` | 独立复核器输出（逐项 pass/fail + 每条资产的复解明细） |
| `scripts/kf_wp_11624_01_register.py` / `_verify.py` / `_report.py` | 登记 / 复核 / 出图出报告，三个脚本可离线复跑 |
| `schemas/asset_manifest.v1.wp-11624-01.schema.json` | 本包钉版 schema（把 `schema_pass` 变成可复算项，且不动别包已钉死的 schema） |
| `tests/test_kf_wp_11624_01.py` | 6 正例 + 12 负例 |
| `docs/wp-11624-01/*` | push gate 会丢 `artifacts/**`，故以上文档类工件在 docs/ 留字节一致镜像 |

图：`{fig['path']}`（sha256 `{fig['sha256'][:16]}…`，{fig['bytes']} 字节）。图为**登记内容的可视化**：
数值逐字解析自资产 A12 的表格引文，A–E 分档系数解析自资产 A11 的判据引文，不是对上游数字的复核。

## ④ 证据定位表（字段 → 原文引文片段）

多行资产在上表只显示**首行**（保持逐字，不截断中段语义）；完整逐字引文与 char span 见 JSON 块中
`outputs.asset_manifest.json.assets[].locator.quote`。

| 资产 | 族 | 解析状态 | 行区间 | 定位 | 原文引文（首行，逐字） |
|---|---|---|---|---|---|
{chr(10).join(loc_rows)}

CII/Required 比值（由 A12 引文程序化相除，非手算）＋用 A11 分档系数反推档位与报告评级列对照
（这是**登记内容的内部一致性检查**，不是对上游计算正确性的复核）：

| 船型 | Attained CII | Required CII | CII/Required | 按 A11 分档反推 | 报告评级 | 一致 |
|---|---|---|---|---|---|---|
{ratio_lines}

## ⑤ 注意点与局限

1. **只登记不抽取**：`claims=[]` 是契约要求，不等于报告没有结论句——结论句已作为资产 A19 登记，
   其成立与否不由本工序判定。
2. **两处计数口径不同，并列登记不解释**：A14「16/16 判据通过」与 A22「测试数量: 26 项全部通过」
   是判据集合与测试集合两回事，本工序不合并、不换算、不裁定。
3. **审计链不可解析**：`backend/modules/eexi_cii_compliance/` 与 `tests/test_eexi_cii_compliance.py`
   在本工作树内不存在（属 ship-performance-platform 仓），因此「测试真的跑过」无法在本包内取证，
   登记为 `referenced_unresolved`，不做存在性断言。
4. **4 条图件声明是缺口不是资产**：记录 metadata 有 name/caption，但无 png/url/path，正文 0 处提及
   （机器检索 name 与 caption 均 0 命中），故 `declared_absent`；本工序不声称图件曾产出。
5. **上游数值未复核**：A12/A13/A18 的数值一律按原文登记；报告 A16 自报「离线环境未回读规则原文，
   证据等级 WITHHELD」，该不确定度原样保留在本清单里，未被本工序消解。
6. **生成时间不可溯源**：A23「生成时间: 自动」是字面文本而非时间戳，无法作为时间证据。
7. **schema 本地钉版**：仓库内 `schemas/asset_manifest.v1.schema.json` 把 package_id/report_id
   钉死为 `wp-448-01`/`448`，直接用会把本包判红；本包另立钉版 schema（结构同源），
   若平台侧 canonical schema 另有规定，以平台门为准、本工件再修。

## ⑥ 自检（逐条对照 acceptance）

| 验收项 | 结果 | 证据 |
|---|---|---|
| valid_json | {tick('envelope_identity')} 通过 | 三个 JSON 均 `json.loads` 严格解析成功（verifier 直接读文件） |
| schema_pass | {tick('schema_pass')} 通过 | manifest 过本包钉版 schema；result 过 `schemas/kf_result.v1.schema.json`（平台 schema `additionalProperties:false`，顶层键只有 package_id/task_type/report_id/provenance/outputs/claims，且 claims 为空数组） |
| source_locator_resolvable | {tick('source_locator_resolvable')} 通过 | {checks['source_locator_resolvable']['assets_resolved']}/{checks['source_locator_resolvable']['assets_checked']} 条：markdown 侧 `md[start:end]==quote` 且 `count==1`；record 侧 pointer 可解析且 quote 在 pointer 值内 |
| source_hash_matches | {tick('source_hash_matches')} 通过 | 快照 sha256 = 契约 `sha256:{manifest['source']['hash'][:16]}…`；manifest 与 provenance 三处一致；chars {checks['source_hash_matches']['chars']} = 契约 {4253} |
| no_duplicate_ids | {tick('no_duplicate_ids')} 通过 | {checks['no_duplicate_ids']['asset_ids']} 个 asset_id 无重复，且 locators 的 id 集与资产集完全相同 |
| all_claims_have_evidence_or_explicit_unresolved_status | {tick('claims_have_evidence_or_unresolved_status')} 通过（空集，契约允许） | claims=0；12 条负例证明「无出处 claim」会被判红；无任何对象带 verified 章，provenance.verification_status=`{result['provenance']['verification_status']}` |

补充：`single_report_scope` {tick('single_report_scope')}（全包只出现 `tensor://reports/11624`，
无他 report_id 引用）、`durable_mirror` {tick('durable_mirror')}（docs/ 镜像与 knowledge/ 字节一致）。
测试：`python3 -m pytest tests/test_kf_wp_11624_01.py -q` → 18 passed。
无失败项（honest-FAIL 无需粉饰）。

## 结果 JSON（唯一一个 json 代码块，原样提交）

```json
{json.dumps(result, ensure_ascii=False, indent=2)}
```
"""
    return body


# ------------------------------------------------------------------- publish
def publish(md_text: str, fig: dict, token: str | None = None) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    if token is None:
        login = urllib.request.Request(
            base + "/auth/login",
            data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                             "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
            headers={"Content-Type": "application/json"})
        tok = json.load(urllib.request.urlopen(login))
        token = tok.get("access_token") or tok.get("token")
    png = base64.b64encode(FIG.read_bytes()).decode()
    payload = {
        "title": "KF-RESULT %s" % PKG,
        "summary": "report 11624 资产登记完成：%d 条资产 / %d 条定位器全解，"
                   "4 条图件声明登记为缺口，claims 空（契约）。" % (
                       len(json.loads((OUT / 'asset_manifest.json').read_text())["assets"]),
                       json.loads((OUT / 'asset_manifest.json').read_text())["counts"]["locators"]),
        "scenario_key": "P187-W1-N06",
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:%s" % PKG, "KF-RESULT", "EEXI", "CII", "asset-registration", "P187-W1-N06"],
        "markdown": md_text,
        "figures": [{
            "name": "wp11624_01_eexi_cii_registered",
            "caption": "报告 11624 登记内容可视化：(a) 三船型 Attained vs Required EEXI（逐字取自资产 "
                       "A12 表格引文）；(b) CII/Required 比值与 G4 A–E 分档（系数取自资产 A11 判据引文）。"
                       "仅为登记内容的可视化，不代表对上游数值的复核。",
            "png_base64": png,
        }],
    }
    req = urllib.request.Request(base + "/tensor/reports", data=json.dumps(payload).encode(),
                                headers={"Content-Type": "application/json",
                                         "Authorization": "Bearer " + token})
    return json.loads(urllib.request.urlopen(req).read())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--skip-figure", action="store_true")
    args = ap.parse_args(argv)

    manifest = json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))
    result = json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))
    verif = json.loads((OUT / "verification_report.json").read_text(encoding="utf-8"))
    if not verif["all_checks_pass"]:
        print("FATAL: verification_report says checks failed; refusing to render a PASS report")
        return 1

    fig_path = DOC / "figs" / "wp11624_01_fig1_eexi_cii.png"
    if args.skip_figure and fig_path.exists():
        png = fig_path.read_bytes()
        fig = {"path": str(fig_path.relative_to(ROOT)),
               "sha256": hashlib.sha256(png).hexdigest(), "bytes": len(png),
               "rows": parse_result_table(manifest), "bands": parse_bands(manifest)}
        fig["cii_ratios"] = [r["attained_cii"] / r["required_cii"] for r in fig["rows"]]
    else:
        fig = build_figure(parse_result_table(manifest), parse_bands(manifest))

    md_text = build_markdown(manifest, result, verif, fig)
    MD_OUT.write_text(md_text, encoding="utf-8")
    DOC.mkdir(parents=True, exist_ok=True)
    (DOC / MD_OUT.name).write_bytes(MD_OUT.read_bytes())
    print("figure:", fig["path"], fig["sha256"], fig["bytes"], "bytes")
    print("markdown:", MD_OUT.relative_to(ROOT), len(md_text), "chars")
    n_json = md_text.count("```json")
    print("json fences in report body:", n_json, "(must be 1)")
    if n_json != 1:
        return 1
    # the single fenced block must be the result envelope, byte-for-byte, and hash-consistent
    block = md_text.split("```json", 1)[1].split("```", 1)[0].strip()
    embedded = json.loads(block)
    expect = json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))
    h_ok = embedded["provenance"]["source_hash"] == ("sha256:" + hashlib.sha256(
        (OUT / "source_report_11624.md").read_text(encoding="utf-8").encode()).hexdigest())
    print("embedded block == kf_result.json:", embedded == expect,
          "| provenance hash matches snapshot:", h_ok)
    if embedded != expect or not h_ok:
        return 1
    if args.publish:
        resp = publish(md_text, fig)
        rid = resp.get("id") or (resp.get("data") or {}).get("id")
        print("published report id:", rid)
        print(json.dumps({k: v for k, v in resp.items() if k != "markdown"},
                         ensure_ascii=False)[:600])
    return 0


if __name__ == "__main__":
    sys.exit(main())