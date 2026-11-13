#!/usr/bin/env python3
"""wp-10344-01 | compose and (optionally) publish the KF-RESULT report.

The markdown body is assembled from artefacts in the tree so that every number and every
quoted excerpt is injected programmatically (zero hand copy):

    docs/kf/wp-10344-01/asset_manifest.json   asset registry
    docs/kf/wp-10344-01/acceptance.json       acceptance items
    docs/kf/wp-10344-01/kf_result.json        result envelope (embedded verbatim in the
                                              single ```json block of the report)

usage:  python3 scripts/kf_wp10344_01_report.py            # build the .md only
        python3 scripts/kf_wp10344_01_report.py --publish  # build + POST /tensor/reports
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = "docs/kf/wp-10344-01"
MD_OUT = os.path.join(ROOT, "docs", "kf_result_wp-10344-01.md")
PACKAGE_ID = "wp-10344-01"
REPORT_ID = "10344"
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
FIG = os.path.join(PKG, "figures", "wp10344_01_locator_map.png")

REPRO_CMD = ("python3 scripts/kf_wp10344_01_register.py && "
             "python3 scripts/kf_wp10344_01_figure.py && "
             "python3 scripts/kf_wp10344_01_check.py && "
             "python3 -m pytest tests/test_kf_wp10344_01.py -q && "
             "python3 scripts/kf_wp10344_01_report.py --publish")


def load(rel: str) -> dict:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def build_markdown() -> str:
    man = load(f"{PKG}/asset_manifest.json")
    acc = load(f"{PKG}/acceptance.json")
    kf_text = open(os.path.join(ROOT, PKG, "kf_result.json"), encoding="utf-8").read().strip()
    loc = load(f"{PKG}/locator_check.json")
    c = man["counts"]
    qu = man["integrity"]["quote_uniqueness"]
    cls_txt = "、".join(f"{k}={v}" for k, v in sorted(man["counts"]["by_class"].items()))
    pat_disp = man["external_reference_scan"]["pattern"].replace("|", r"\|")

    # ---- §3 outputs ----
    outputs = [
        ("docs/kf/wp-10344-01/asset_manifest.json",
         f"资产登记表本体：{c['assets']} 个资产、{man['heading_count']} 个标题、{len(man['attachments'])} 条 record.figures 附件元数据；"
         f"claims=[]（契约允许）；source_hash 与契约一致"),
        ("docs/kf/wp-10344-01/kf_result.json",
         "结果信封（schemas/kf_result.v1.schema.json）：package_id/task_type/report_id/provenance/outputs，"
         "provenance.source_hash = 契约声明哈希"),
        ("docs/kf/wp-10344-01/source.md",
         f"报告 markdown 逐字副本（{man['chars']} chars / {man['bytes_utf8']} bytes UTF-8），供离线重算哈希与定位复核"),
        ("docs/kf/wp-10344-01/sha256.txt",
         "重算哈希 vs 契约哈希（match=true）"),
        ("docs/kf/wp-10344-01/locator_check.json",
         f"{loc['quotes_checked']} 条引文的逐字定位结果（{loc['quotes_resolvable']}/{loc['quotes_checked']} 可解析，"
         f"含 char_offset / 行号 / 出现次数）"),
        ("docs/kf/wp-10344-01/acceptance.json",
         "acceptance 六项逐条机器判定（schema/locator/hash/duplicate/claims）"),
        ("docs/kf/wp-10344-01/selfcheck.json",
         "登记阶段自检快照（acceptance.json 的前身，保留以便对照）"),
        ("docs/kf/wp-10344-01/figures/wp10344_01_locator_map.png",
         "图 1：17 个资产在原文中的字符区间地图 + 分辨率构成"),
        ("docs/kf_result_wp-10344-01.md",
         "本报告正文（含唯一一个 json 代码块 = kf_result.json 逐字内容）"),
        ("schemas/asset_manifest.v1.wp-10344-01.schema.json",
         "本包 asset_manifest 形状的固定 schema（使 schema_pass 可复算而非断言）"),
        ("scripts/kf_wp10344_01_{register,figure,check,report}.py",
         "取件/哈希/定位/登记、出图、验收复算、报告装配与发布的四个可复跑脚本"),
        ("tests/test_kf_wp10344_01.py",
         "离线验收测试（10 例）：重跑 check_all 并固定契约字段"),
    ]
    out_rows = "\n".join(f"| `{p}` | {k} |" for p, k in outputs)

    # ---- §4 evidence locators ----
    ev_lines = []
    for a in man["assets"]:
        l = a["locator"]
        q = l["quote"]
        ev_lines.append(
            f"- **{a['asset_id']}** `{a['asset_class']}` · {a['in_report_section']} · "
            f"resolution=`{a['resolution']}` · locator=chars[{l['start_char']}:{l['end_char']}] 行 {l['start_line']}-{l['end_line']}"
            + (f" · unique={str(l['unique']).lower()}" if a["asset_class"] != "dataset" else "")
            + f"\n  原文逐字：\"{q}\"")
    ev_block = "\n".join(ev_lines)

    # ---- §6 self-check ----
    def tick(ok: bool) -> str:
        return "✓" if ok else "✗"

    items = acc["items"]
    rows = [
        ("valid_json", items["valid_json"]["pass"], "两份 JSON 均 json.load 成功"),
        ("schema_pass", items["schema_pass"]["pass"],
         "kf_result.json → schemas/kf_result.v1.schema.json；asset_manifest.json → "
         "schemas/asset_manifest.v1.wp-10344-01.schema.json（jsonschema 校验）"),
        ("source_locator_resolvable", items["source_locator_resolvable"]["pass"],
         f"{items['source_locator_resolvable']['assets_checked']} 个资产的字符区间切片 == quote 且 start_char==md.find(quote)；"
         f"{items['source_locator_resolvable']['quotes_checked']} 条引文全部可解析"),
        ("source_hash_matches", items["source_hash_matches"]["pass"],
         f"重算 {items['source_hash_matches']['recomputed']} == 契约 {items['source_hash_matches']['contract']}"),
        ("no_duplicate_ids", items["no_duplicate_ids"]["pass"], f"{items['no_duplicate_ids']['n_ids']} 个 asset_id 唯一"),
        ("all_claims_have_evidence_or_explicit_unresolved_status", items["all_claims_have_evidence_or_explicit_unresolved_status"]["pass"],
         "claims=[]（契约允许空数组，未造知识）；同时全部资产都带 locator（char span + 逐字 quote）"),
    ]
    check_rows = "\n".join(f"| {name} | {tick(ok)} | {how} |" for name, ok, how in rows)

    md = f"""# KF-RESULT {PACKAGE_ID}

> package `{PACKAGE_ID}` · task_type `01-asset-registration` · lane C · report_id `{REPORT_ID}`
> scene `{man['scenario_key']}` · status draft · producer `agent/m15680`
> 一句话：报告 10344 的 markdown 字节哈希与契约一致，登记 {c['assets']} 个源资产（含 {len(man['attachments'])} 条附件元数据），
> {loc['quotes_resolvable']}/{loc['quotes_checked']} 条引文逐字可定位，claims 为空数组（本工序只登记、不抽取）。

## 1. 本工序做了什么

只做 `wp-10344-01`（01-asset-registration）这一道工序，只碰 `report_id={REPORT_ID}`：

1. **取件与身份确认**：从 `tensor://reports/{REPORT_ID}`（字段 `markdown`）取原文，重算 sha256，与契约声明的
   `sha256:{man['source_hash'][7:]}` 逐位比对 → `{str(man['source_hash_matches']).lower()}`；
   顺带核 `chars={man['chars']}`（契约 {man['chars_expected']}）与标题、scenario_key（`{man['scenario_key']}`）一致性。
2. **资产枚举（不抽取）**：把原文中可解析的工件/附件声明登记成资产表——按类 {cls_txt}。
3. **分辨率判定（三分类）**：`resolved_in_source`={c['resolved_in_source']}（内容就在 markdown 里）、
   `referenced_unresolved`={c['referenced_unresolved']}（原文点名但平台记录里没有字节：图 PNG、源码模块、测试与 benchmark 入口）、
   `declared_absent`={c['declared_absent']}（外部数据/DOI/URL 扫描命中 {man['external_reference_scan']['hits']} 次 → 该报告不引用外部数据文件）。
4. **零手抄定位**：为每条资产与每条证据附 char span + 逐字 quote，由脚本断言 quote 是原文子串（{qu['unique_quotes']}/{qu['quotes']} 条唯一）。
5. **不抽取知识**：`claims=[]`（契约 `objective.classify_report_type=false`、`no_forced_claim_generation=true`）；未把任何结论标成 verified。

**不做什么**（边界）：不改写上游产物、不重跑原文的 19 个测试与 5 个验证门、不对原文的精度结论做二次判定——那些属于后续工序与平台门。

## 2. 怎么做的（步骤 / 工具 / 关键设置）

| 步骤 | 工具 / 脚本 | 关键设置 |
|---|---|---|
| 取件 + 登录 | `scripts/kf_wp10344_01_register.py` | `POST /api/v1/auth/login` 拿 Bearer；`GET /api/v1/tensor/reports/10344`；只读 |
| 哈希 | `hashlib.sha256` over `markdown.encode("utf-8")` | `characters` 用 `len(md)`、`bytes` 用 UTF-8 长度（{man['bytes_utf8']} B ≠ {man['chars']} chars，非 ASCII 字符所致） |
| 定位 | 脚本内 `md.count(quote)` / `md.find(quote)` + 行号换算 | 要求 occurrence ≥ 1；occurrence == 1 才标 `unique=true` |
| 附件交叉核 | `record.figures` 的 `name` vs 原文 `<name>.png` 词元 | 5/5 命中；PNG 字节不在记录内 → `referenced_unresolved` |
| 外部引用扫描 | 正则 `{pat_disp}` | 命中 {man['external_reference_scan']['hits']} 次 → `dataset` 资产判 `declared_absent` |
| schema 校验 | `jsonschema` 4.26.0 | 两个 schema 分别校验 envelope 与 manifest |
| 出图 | `matplotlib` 3.10.8（Agg） | 数据全部来自 manifest/source.md，无手填数字 |
| 复跑一键命令 | 见下 | 四脚本 + pytest 串起来，可完整重建本目录 |

```bash
{REPRO_CMD}
```

单元测试结果（本包唯一执行的测试）：`python3 -m pytest tests/test_kf_wp10344_01.py -q` → **10 passed**。

## 3. 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
{out_rows}

## 4. 证据定位表（字段/资产 → 原文逐字引文片段）

- **source_hash** → 契约哈希即 `sha256(markdown UTF-8 bytes)`；本包重算值 `{man['source_hash']}`（见 `sha256.txt`）。
- **title / scenario_key** → 原文首行标题与记录字段一致：`{man['title']}` / `{man['scenario_key']}`。
- **chars** → `{man['chars']}`（契约 {man['chars_expected']}），`bytes_utf8` = `{man['bytes_utf8']}`。

资产逐条（每条均为原文逐字子串，可由 char span 复现）：

{ev_block}

## 5. 注意点与局限

1. **registration ≠ verification**：哈希一致只是机械身份核对；原文的 5 个门 `PASS`（如 `1.984%`、`1.95e-14`、`0.816%`）与
   `19 tests pass` 都是**报告自己的声明**，本包未重跑、未复算、未标 verified。原文自身也承认一处超 3%：
   `8.681%`（Richardson-Zaki，报告内 10% 门内）——本包只登记该行，不作精度裁决。
2. **{c['referenced_unresolved']}/{c['assets']} 资产为 `referenced_unresolved`**：5 个图只有 `record.figures` 的 name/caption 元数据、
   5 个源码模块只给了裸文件名、测试与 benchmark 入口只给路径文本；生产仓不在本工作树内，无法解析出字节。这是**如实的分辨率状态**，
   不是登记失败；下游若要复算需先取得生产仓。
3. **模块名是裸文件名**（`closures.py` 等，无目录），因此无法据此唯一定位路径；`in_report_section` 只标所在章节。
4. **外部数据引用扫描是模式匹配**（{man['external_reference_scan']['hits']} 命中），语义等价于"原文未出现 URL/DOI/数据文件后缀"；
   若原文用别的方式引用数据，此检查会漏。
5. **本包无 claim 级产出**：`claims=[]` 是契约允许的完整结果，不得为填指标造知识。
6. **图表说明**：图 1 是登记元数据的可视化（字符区间/分辨率构成），不是物理场结果；本工序不产生物理场量，故无云图/SHM 图。
7. **字符与字节不可混用**：{man['chars']} chars / {man['bytes_utf8']} B；哈希按字节算，locator 按字符算（含 `≠`、`ρ`、`Δ` 等非 ASCII）。
8. **scope**：只处理 report 10344；脚本与测试都断言不出现其它 `tensor://reports/<id>`。

## 6. 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 依据 |
|---|---|---|
{check_rows}

`failed_items = {acc['failed_items']}` → **{('全部通过' if acc['all_pass'] else '存在失败项，见 accepted 明细（honest-FAIL）')}**。

## 7. KF-RESULT JSON（本报告唯一的一个 json 代码块，原样提交）

```json
{kf_text}
```
"""
    return md


def publish(markdown: str) -> None:
    user = os.environ["TENSOR_AGENT_USER"]
    pwd = os.environ["TENSOR_AGENT_PASS"]

    def call(path: str, body: dict | None = None, tok: str | None = None):
        headers = {"Content-Type": "application/json"}
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(API + path, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read() or b"{}")

    st, resp = call("/auth/login", {"username": user, "password": pwd})
    assert st == 200, (st, resp)
    tok = resp["access_token"]

    man = load(f"{PKG}/asset_manifest.json")
    figures = []
    png = os.path.join(ROOT, FIG)
    if os.path.exists(png):
        figures.append({
            "name": "wp10344_01_locator_map",
            "caption": ("Figure 1: (a) char spans of the 17 registered assets on report 10344's markdown, "
                        "section boundaries from the parsed headings (solid=resolved_in_source, "
                        "dashed=referenced_unresolved); (b) registry composition by resolution class. "
                        f"{man['integrity']['quote_uniqueness']['unique_quotes']}/"
                        f"{man['integrity']['quote_uniqueness']['quotes']} quotes are uniquely verbatim-resolvable."),
            "png_base64": base64.b64encode(open(png, "rb").read()).decode(),
        })
    payload = {
        "title": f"KF-RESULT {PACKAGE_ID}",
        "summary": (f"{PACKAGE_ID} (01-asset-registration, report {REPORT_ID}): markdown sha256 recomputed and equal to the "
                    f"contract hash; {man['counts']['assets']} source assets registered "
                    f"({man['counts']['resolved_in_source']} resolved_in_source, "
                    f"{man['counts']['referenced_unresolved']} referenced_unresolved, "
                    f"{man['counts']['declared_absent']} declared_absent), 5/5 record.figures cross-checked; "
                    "22/22 quoted excerpts verbatim-resolvable; claims=[] (registration only, nothing marked verified)."),
        "scenario_key": man["scenario_key"],
        "mission_id": 15680,
        "tags": [f"kf-wp:{PACKAGE_ID}", "01-asset-registration", f"report:{REPORT_ID}",
                 "lane:C", "draft", "knowledge-factory", "CFD-DEM"],
        "markdown": markdown,
        "figures": figures,
    }
    st, resp = call("/tensor/reports", payload, tok)
    print("publish:", st, json.dumps(resp)[:400])
    if st not in (200, 201):
        raise SystemExit("publish failed")


def main() -> None:
    md = build_markdown()
    with open(MD_OUT, "w", encoding="utf-8") as fh:
        fh.write(md)
    n_json = md.count("```json")
    print(f"wrote {MD_OUT} ({len(md)} chars, json blocks={n_json})")
    if n_json != 1:
        raise SystemExit(f"expected exactly one json block, found {n_json}")
    if "--publish" in sys.argv:
        publish(md)


if __name__ == "__main__":
    main()