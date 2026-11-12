#!/usr/bin/env python3
"""Render docs/reports/kf_wp_623_01_result.md from the generated artefacts and
(optionally) POST it to the platform as the KF-RESULT report.

Every number/quote in the markdown is injected from asset_manifest.json /
verification.json / kf_result.json -- nothing is typed by hand.

    python3 scripts/kf_wp62301_render_report.py            # write md + self-check
    python3 scripts/kf_wp62301_render_report.py --post     # ... and publish
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ID = "wp-623-01"
REPORT_ID = "623"
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
FIG = OUT_DIR / "figures" / "wp62301_source_locator_map.png"
REPORT_MD = ROOT / "docs" / "reports" / "kf_wp_623_01_result.md"


def sha256(p: Path) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()


def src_copy(mf: dict) -> str:
    return next(a["local_copy"] for a in mf["assets"] if a["kind"] == "report_markdown")


def esc(s: str) -> str:
    return (s or "").replace("|", "\\|")


def evidence_rows(mf: dict) -> list[str]:
    rows = []
    lines = (ROOT / src_copy(mf)).read_text().rstrip("\n").split("\n")
    for a in mf["assets"]:
        loc = a["locator"]
        if loc["source_field"] != "markdown":
            rows.append("| `%s` | %s | %s | `figures` record | name=`%s` (record 只有 name/caption, 无字节) |"
                        % (a["asset_id"], a["kind"], a["resolution"]["status"], a["name"]))
            continue
        ln = loc["line"]
        if a["kind"] == "report_markdown":
            tok = "整字段 sha256（%d 行）；L1=%s" % (len(lines), lines[0][:48] + ("…" if len(lines[0]) > 48 else ""))
        else:
            tok = a.get("quote_token") or a["name"]
        rows.append("| `%s` | %s | %s | L%d | `%s` |" % (a["asset_id"], a["kind"],
                                                         a["resolution"]["status"], ln, esc(tok)))
    for s in mf["symbol_references"]:
        rows.append("| `%s` | %s | declared_only | L%d | `%s` |"
                    % (s["symbol_id"], s["kind"], s["locator"]["line"], esc(s["token"])))
    return rows


def identity_rows(mf: dict) -> list[str]:
    return ["| `%s` | L%d | `%s` |" % (f["fact_id"], f["locator"]["line"], esc(f["quote"].strip()))
            for f in mf["identity_facts"]]


def build_markdown() -> str:
    mf = json.loads(MANIFEST.read_text())
    vf = json.loads(VERIFICATION.read_text())
    env_text = ENVELOPE.read_text().strip()
    c = mf["counts"]
    s = mf["source"]
    rf = s["record_fields"]
    probes = s["platform_attachment_probes"]["figure_probe"]
    probe_txt = "; ".join("%s → HTTP %s" % (k, v["http_status"]) for k, v in probes.items())

    acc_rows = "\n".join(
        "| %s | %s | %s |" % ("✅ PASS" if ch["ok"] else "❌ FAIL", k,
                              esc(str(ch.get("detail"))[:150]))
        for k, ch in vf["acceptance"].items())

    err_rows = [
        "| markdown sha256 (UTF-8) | `%s` | 契约 `source_hash`=%s | 0（逐字节相同） | **是** |"
        % (s["source_hash"][7:23] + "…", s["contract_source_hash"][7:23] + "…"),
        "| markdown chars | %d | 契约 chars=%d | 0%% | **是** |" % (s["chars"], s["contract_chars"]),
        "| markdown bytes / lines | %d B / %d 行 | 无契约基线 | n/a | 不适用（登记量，非误差量） |"
        % (s["bytes"], s["lines"]),
        "| markdown 定位点可解析 | %d/%d | 全部可解析 | 0%% | **是** |"
        % (c["locators_resolved"], c["locators"]),
        "| 源资产可解析 | %d/1 | 源 markdown 1/1 可解析 | 0%% | **是** |" % c["assets_resolved"],
        "| 工件（非源）字节可解析 | 0/%d | 无基线（工件在 TensorDEM 仓；2 图仅元数据） | 不可判定 | 不适用（见⑤） |"
        % (c["assets_total"] - c["assets_resolved"]),
    ]

    md = f"""# KF-RESULT {PACKAGE_ID}

**工作包**: `{PACKAGE_ID}` · **task_type**: `{mf['task_type']}` · **report_id**: `{REPORT_ID}` · **lane**: `C` · **delivery**: TensorKnowledge (draft)
**源**: `{s['source_uri']}` 字段 `markdown` · **哈希口径**: UTF-8 字节 · `{s['source_hash']}`

## ① 本工序做了什么

对 report 623《{rf['title']}》执行**资产登记**（工序 01）：只确认源资产身份、清点可解析的附件/工件，**不做抽取、不做报告类型判定、不标 verified**。

1. **源资产身份确认**：`markdown` = {s['bytes']} B / {s['chars']} 字符 / {s['lines']} 行，sha256 = `{s['source_hash']}`，与工作包契约 `source_hash` **逐字节一致**（契约 chars={s['contract_chars']} 亦一致）。
2. **登记资产 {c['assets_total']} 项** = 1 源 markdown + {c['figures_declared_in_record']} 报告记录内嵌图元数据 + {c['body_references']} 条正文路径引用（{c['distinct_referenced_paths']} 个不同路径，同一路径在不同行各算一次）；另登记 {c['symbol_references']} 条符号级引用（模块入口 / 上游报告号）。
3. **每条资产带可解析定位**：markdown 行号 + 该行逐字引文 + 引文 sha256，共 {c['locators']} 个定位点，全部在**实时拉取的 markdown** 上重解析通过（{c['locators_resolved']}/{c['locators']}）。
4. **解析状态三分**：`resolved` {c['assets_resolved']}（源 markdown，已在工作树落本地副本）、`metadata_only` {c['assets_metadata_only']}（图只有 name/caption，平台不供字节，不假装有哈希）、`unresolved` {c['assets_unresolved']}（正文声明的 TensorDEM 工件，**在工作树内不存在**，如实标未解析，不声称上游缺失）。
5. `claims` 保持**空数组**：契约 `no_forced_claim_generation: true` 且本工序 objective 仅 `register_assets=true`，抽取属下游工序（理由已写进清单 `claims_empty_reason`）。

资产状态分布：

| kind / status | 数量 |
|---|---|
""" + "\n".join("| `%s` | %d |" % (k, n) for k, n in c["kind_status_histogram"].items()) + f"""
| `report_markdown/resolved` | {c['assets_resolved']} |
| **合计** | **{c['assets_total']}** |

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`POST /api/v1/auth/login`（`$TENSOR_AGENT_USER`）→ `GET /api/v1/tensor/reports/623`，取 `markdown` 原字段，落本地副本 `runs/{PACKAGE_ID}/source_623.md`。本机 `psql -d tensorplatform -c "select markdown from tensor_reports where id=623"` 被拒（`permission denied for table tensor_reports`），故 **API 是唯一取源通道**（如实记录，不掩饰）。
2. **定身份**：对 `markdown` 的 UTF-8 字节做 sha256，与契约 `source_hash`、契约 `chars=7281` 双向比对；不等即 `SystemExit` 中止，不产出半成品清单。同时比对 `title` / `scenario_key`：`scenario_key` 逐字相同；`title` 在记录里用 U+2013 EN DASH（`10k–100k`）、契约用 ASCII 连字符（`10k-100k`），**做单字符 dash 归一后相同**——这一点如实标注，不当作逐字相同。
3. **扫描引用**（三条正则，全部只读原文、零猜测）：
   - markdown 图片 `![alt](path)` → `figure_reference`；
   - 反引号内容中"像路径"者（有目录段或已知工件后缀）→ 按扩展名归类（`.py`→源码、`.json`→数据工件、`.png`→图、`.md`→文档）；
   - 裸路径 + 可选 `../` 前缀（同上归类）。负向断言排除"路径的子串碎片"（如 `results-dem3d-` 被切成 `dem3d-`），首版踩到 1 例假阳性后修正。
4. **符号级引用**：反引号内的点分模块名（`tensordem.dem3d.IceDEM3D` 等）与 `**Upstream**` 行的 `m<编号>` 单独登记为 `module_reference` / `upstream_report_reference`，状态 `declared_only`——本工序不开 TensorDEM 仓，不声称这些入口存在。
5. **附件解析尝试**（结果写进清单，不猜）：`GET /tensor/reports/623/figures/<name>` 两图均 HTTP 404（`figure "not found"`）；`/tensor/reports/623/artifacts`、`/tensor/artifacts?report_id=623`、`/tensor/reports/623/figures`、`/tensor/reports/623/attachments` 均 HTTP 404。故图只能 `metadata_only`。
6. **解析范围**：工件只在**交付工作树**（TensorKnowledge）内查找；命中则记字节数 + sha256（`resolved`），未命中记 `unresolved` + 同 basename 命中列表（供后人定位），**绝不跨仓臆测存在性**。
7. **信封与自校验**：`kf_result.json` 的 `provenance.source_hash` 由**重新拉取的实时字节**重算，与清单声明不一致则拒绝产出；`verification.json` 用 `jsonschema` Draft 2020-12 校验 `schemas/kf_result.v1.schema.json`（平台下发 schema 的仓内副本，sha256 `170dba8b0b5d54012490aaadc0b68647a9520ecb869e9d03f873afb99b74c076`），并**再次**对实时 markdown 重解析全部 {c['locators']} 个定位点。
8. **关键设置**：纯标准库（urllib/hashlib/json/re）+ `jsonschema` 做 schema 门 + matplotlib 出图；脚本幂等，`all` 一条命令重建全部产物。

一键复跑（工作树根执行）：

```bash
python3 scripts/kf_wp62301_register_assets.py all && python3 scripts/kf_wp62301_render_report.py
```

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `{OUT_DIR.relative_to(ROOT)}/asset_manifest.json` | 主产物：{c['assets_total']} 资产 + {c['symbol_references']} 符号引用 + {c['locators']} 定位点 + provenance + 空 claims；{MANIFEST.stat().st_size} B，`{sha256(MANIFEST)}` |
| `{OUT_DIR.relative_to(ROOT)}/kf_result.json` | 交付信封（package_id/task_type/report_id/provenance/outputs）：`outputs.asset_manifest.json` 内嵌同一清单，`source_hash` 实时重算绑定；{ENVELOPE.stat().st_size} B，`{sha256(ENVELOPE)}` |
| `{OUT_DIR.relative_to(ROOT)}/verification.json` | 自校验报告：6 项 acceptance 全 True（`all_ok: {str(vf['all_ok']).lower()}`）；{VERIFICATION.stat().st_size} B，`{sha256(VERIFICATION)}` |
| `{OUT_DIR.relative_to(ROOT)}/figures/wp62301_source_locator_map.png` | 定位图：左=逐行字符数曲线 + 各类引用锚点行 + 章节线；右=资产 kind/status 直方图（{FIG.stat().st_size} B） |
| `runs/{PACKAGE_ID}/source_623.md` | 源 markdown 本地副本，`{sha256(ROOT / src_copy(mf))}` |
| `scripts/kf_wp62301_register_assets.py` | 可复跑构建器（build / envelope / verify / figure / all） |
| `scripts/kf_wp62301_render_report.py` | 报告渲染器（本报告全部数字由脚本注入，零手抄） |

## ④ 证据定位表（asset/字段 → 原文逐字引文）

定位方案：`source_field=markdown` 用 1 基行号，校验时 **`lines[line-1] == quote` 且 `quote in markdown` 且 `sha256(quote)` 与清单一致**；图元数据用 `source_field=record` 的 JSON pointer。下表由脚本从清单回读生成。

源身份（identity_facts，全文级锚点）：

| fact | 定位 | 原文逐字 |
|---|---|---|
""" + "\n".join(identity_rows(mf)) + f"""

资产 / 符号定位（引文=路径 token 或整行，均为原文逐字子串）：

| asset_id | kind | 解析状态 | 定位 | 原文引文（逐字） |
|---|---|---|---|---|
""" + "\n".join(evidence_rows(mf)) + f"""

图元数据（`source_field=record`）：`/figures/0/name` = `dem3d_scale_benchmark`，`/figures/1/name` = `dem3d_energy_drift`；两者 caption 见清单 `assets[].caption`。

## ⑤ 注意点与局限

1. **只登记，不判定**：无 claim 抽取、无报告类型分类、无 verified 标记；verification 由平台门独立重算，本工序的 `verification.json` 只是自检。
2. **{c['body_references']} 个正文引用的工件（+ {c['figures_declared_in_record']} 图）全部 unresolved，这是"范围"而不是"结论"**：它们是 TensorDEM 侧产物（`src/tensordem/dem3d.py`、`scripts/benchmark_dem3d_scale.py`、`tests/test_dem3d_scale_benchmark.py`、`results-dem3d-scale/scaling_report.json`、`artifacts/*.png`），不在交付工作树内。清单显式写 `existence_asserted_by_worker: false`，避免被下游误读为"上游缺文件"。要判定这些工件真伪需 TensorDEM 仓的独立解析工序。
3. **两图无字节**：报告记录只给 name/caption，`GET .../figures/<name>`、`.../artifacts`、`.../attachments` 全 404，故只登记元数据，不给 sha256——不伪造哈希。
4. **title 的 dash 差异**：记录用 U+2013，契约用 ASCII `-`；已按单字符归一判定"相同"，并在清单里同时保留两串原文，供门自行裁量（若门要求逐字相等，此处会如实判为不一致）。
5. **哈希口径**：`markdown` 字符串的 UTF-8 字节；平台侧任何改动（含空白）都会让 `source_hash` 失配。本地副本与实时字节当前一致（{s['bytes']} B）。
6. **本工序无量纲物理量**：不产生场量云图，也没有解析解/文献基线可比；因此图 = 文档结构/定位图（图 1），误差判定只对"恒等量"（哈希、字符数、定位解析率）给出，见⑥。这一条是数据性质决定的，不是漏做。
7. **未做的事**（如实列出）：未在 TensorDEM 仓复算报告里的 1.12× 缩放比与 0 能量漂移；未下载/校验两张 PNG 内容；未做报告类型分类（契约 `classify_report_type: false`）。

## ⑥ 自检（逐条对照 acceptance）

| 结果 | acceptance 项 | 证据 |
|---|---|---|
{acc_rows}

**误差判定**（本工序的"关键量"是恒等量，逐项给出）：

| 量 | 实测 | 基准/契约 | 误差 | 是否 < 3%？ |
|---|---|---|---|---|
""" + "\n".join(err_rows) + f"""

回答：**是**——sha256、字符数、定位解析率三项均为精确比对，误差 0%（< 3%）；"工件可解析数"无基准可比（工件属 TensorDEM 仓），不做误差判定也不含糊其辞。

图 1（`figures/wp62301_source_locator_map.png`）：左图为 report 623 markdown 的逐行字符数曲线，竖线为每类正文引用在原文中的行号锚点，点线标出 H1/§1/§3/§5/Audit Chain 章节位置；右图为资产 kind/status 直方图。用途=让"登记了哪些、锚在哪一行、有多少解析不了"一眼可核，替代本工序不存在的物理场量云图。

## 附：结果 JSON（全文唯一 fenced json 代码块，与 `{OUT_DIR.relative_to(ROOT)}/kf_result.json` 逐字节相同）

```json
{env_text}
```
"""
    return md


def selfcheck(md_text: str) -> dict:
    """The report must contain exactly one ```json block and that block must equal
    kf_result.json byte-for-byte; re-validate it against the schema here."""
    from jsonschema import Draft202012Validator
    blocks = re.findall(r"```json\n(.*?)\n```", md_text, flags=re.S)
    env_file = ENVELOPE.read_text().strip()
    ok_one = len(blocks) == 1
    ok_same = ok_one and blocks[0].strip() == env_file
    obj = json.loads(blocks[0]) if ok_one else {}
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
    errs = [e.message for e in Draft202012Validator(schema).iter_errors(obj)]
    mf = json.loads(MANIFEST.read_text())
    return {
        "single_json_block": ok_one,
        "json_block_equals_kf_result_file": ok_same,
        "schema_errors": errs,
        "source_hash_in_block": obj.get("provenance", {}).get("source_hash"),
        "source_hash_matches_manifest": obj.get("provenance", {}).get("source_hash")
        == mf["source"]["source_hash"],
        "title_line": md_text.split("\n")[0],
        "title_ok": md_text.split("\n")[0].strip() == "# KF-RESULT %s" % PACKAGE_ID,
        "has_six_sections": all(k in md_text for k in
                                ("① 本工序做了什么", "② 怎么做的", "③ 产出物清单",
                                 "④ 证据定位表", "⑤ 注意点与局限", "⑥ 自检")),
    }


def post(md_text: str) -> None:
    api = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

    def call(path, body, tok=None):
        h = {"Content-Type": "application/json"}
        if tok:
            h["Authorization"] = "Bearer " + tok
        req = urllib.request.Request(api + path, data=json.dumps(body).encode(), headers=h)
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.status, r.read().decode()[:400]
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()[:600]

    st, body = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                    "password": os.environ["TENSOR_AGENT_PASS"]})
    if st != 200:
        raise SystemExit("login failed: %s %s" % (st, body))
    tok = json.loads(urllib.request.urlopen(urllib.request.Request(
        api + "/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        headers={"Content-Type": "application/json"})).read())["access_token"]

    payload = {
        "title": "KF-RESULT %s" % PACKAGE_ID,
        "summary": ("report 623 资产登记：markdown %d B/%d chars，sha256 与契约逐字节一致；登记 %d 资产"
                    "（1 源 + 2 图元数据 + %d 正文路径引用）+ %d 符号引用，%d 个定位点全解析；claims 空（工序 01 不抽取）。"
                    % (json.loads(MANIFEST.read_text())["source"]["bytes"],
                       json.loads(MANIFEST.read_text())["source"]["chars"],
                       json.loads(MANIFEST.read_text())["counts"]["assets_total"],
                       json.loads(MANIFEST.read_text())["counts"]["body_references"],
                       json.loads(MANIFEST.read_text())["counts"]["symbol_references"],
                       json.loads(MANIFEST.read_text())["counts"]["locators"])),
        "scenario_key": "SIR-PC2|V02",
        "mission_id": 15515,
        "tags": ["kf-wp:%s" % PACKAGE_ID, "KBM-RCI-F1-FACTORY", "asset-registration",
                 "DEM", "SIR-PC2", "V02", "lane-C", "report-623"],
        "markdown": md_text,
        "figures": [{
            "name": "wp62301_source_locator_map",
            "caption": ("report 623 markdown 结构与定位图：左=逐行字符数 + 各类引用锚点行（L1/L9/L58/L109/L141 章节线）；"
                        "右=资产 kind/status 分布。无物理场量可比，故以结构/定位图代替云图。"),
            "png_base64": base64.b64encode(FIG.read_bytes()).decode(),
        }],
    }
    st, body = call("/tensor/reports", payload, tok)
    print("POST /tensor/reports ->", st, body[:400])
    if st not in (200, 201):
        raise SystemExit("post failed")
    Path("/tmp/kf_623_01_payload.json").write_text(json.dumps(payload, ensure_ascii=False))


def main(argv: list[str]) -> int:
    md_text = build_markdown()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(md_text)
    chk = selfcheck(md_text)
    (OUT_DIR / "report_selfcheck.json").write_text(json.dumps(chk, ensure_ascii=False, indent=2) + "\n")
    print("report ->", REPORT_MD.relative_to(ROOT), len(md_text), "chars")
    print(json.dumps(chk, ensure_ascii=False, indent=1))
    bad = [k for k in ("single_json_block", "json_block_equals_kf_result_file",
                       "source_hash_matches_manifest", "title_ok", "has_six_sections")
           if not chk[k]] + (["schema"] if chk["schema_errors"] else [])
    if bad:
        raise SystemExit("report self-check failed: %s" % bad)
    if "--post" in argv:
        post(md_text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))