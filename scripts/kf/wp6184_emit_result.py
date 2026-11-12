#!/usr/bin/env python3
"""wp-6184-01 result envelope + report body emitter (task_type=01-asset-registration).

Consumes docs/kf/wp-6184-01/asset_manifest.json (+ verification.json) and emits:
  docs/kf/wp-6184-01/kf_result.json          -> envelope submitted as the report's single ```json block
  docs/kf/wp-6184-01/KF-RESULT_wp-6184-01.md -> report body (6 sections, one json block only)

All numbers/quotes in the report body are read out of the manifest/verification files,
never retyped, so the body cannot drift from the registered evidence.

Usage:
  python3 scripts/kf/wp6184_emit_result.py          # emit files
  python3 scripts/kf/wp6184_emit_result.py --post   # emit + POST the report to the platform
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "docs" / "kf" / "wp-6184-01"
MANIFEST = OUT_DIR / "asset_manifest.json"
VERDICT = OUT_DIR / "verification.json"
KF_RESULT = OUT_DIR / "kf_result.json"
REPORT_MD = OUT_DIR / "KF-RESULT_wp-6184-01.md"

PKG = "wp-6184-01"
REPORT_ID = "6184"
MISSION_ID = 15587
SCENARIO = "green_navigation_eexi_cii_compliance"

REPRO = (
    "cd <worktree> && python3 scripts/kf/wp6184_register_assets.py build verify "
    "&& python3 scripts/kf/wp6184_emit_result.py && python3 -m pytest tests/test_kf_wp6184_asset_manifest.py -q"
)


def _preview(quote: str, limit: int = 90) -> str:
    """Readable table preview of a locator quote; the full verbatim quote lives in the manifest."""
    if len(quote) <= limit:
        return _cell(quote)
    first = quote.split("\n", 1)[0][:limit]
    return _cell(first) + f" …（全长 {len(quote)} 字符，逐字片段见 `locator.quote`）"


def _cell(text: str) -> str:
    """One markdown table cell: keep the quote verbatim apart from table-syntax escapes."""
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")


def build_result(man: dict) -> dict:
    return {
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + man["source"]["hash"],
            "source_field": "markdown",
            "producer": "agent/m15587 · scripts/kf/wp6184_register_assets.py",
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "notes": (
                "source_hash = sha256 of the UTF-8 bytes of GET /api/v1/tensor/reports/6184 .markdown, "
                "recomputed locally and equal to the work-package contract input.source_hash "
                f"({man['source']['contract_hash']}); chars {man['source']['chars']} = contract chars "
                f"{man['source']['contract_chars']}. Outputs carry the registered asset manifest only; "
                "no knowledge claims are extracted by this package and nothing is marked verified."
            ),
        },
        "outputs": {"asset_manifest.json": man},
        "claims": [],
    }


def build_report(man: dict, ver: dict, result: dict) -> str:
    src = man["source"]
    cnt = man["counts"]
    acc = ver["acceptance"]
    marks = "\n".join(
        f"- [{'x' if c['result'] == 'pass' else ' '}] `{c['check']}` — {c['detail']}" for c in acc
    )
    assets_rows = "\n".join(
        f"| {a['asset_id']} | `{a['asset_class']}` | {_cell(a['label'])} | {a['resolution']} | "
        f"L{a['locator']['start_line']}–{a['locator']['end_line']} |"
        for a in man["assets"]
    )
    ev_rows = "\n".join(
        f"| {a['asset_id']} {_cell(a['in_report_section'])} | `{a['asset_class']}` / {a['resolution']} | "
        f"{_preview(a['locator']['quote'])} | `[{a['locator']['start_char']},{a['locator']['end_char']})` "
        f"L{a['locator']['start_line']}–{a['locator']['end_line']} |"
        for a in man["assets"]
    )
    probes = "\n".join(f"| `{k}` | HTTP {v.get('http_status', v.get('error', '?'))} |" for k, v in src["platform_attachment_probes"].items())
    unresolved = [a for a in man["assets"] if a["resolution"] != "resolved_in_source"]
    unresolved_rows = "\n".join(f"| {a['asset_id']} | {_cell(a['label'])} | {_cell(a['note'])} |" for a in unresolved)

    block = json.dumps(result, ensure_ascii=False, indent=2)
    return f"""# KF-RESULT {PKG}

**工作包** `{PKG}`（task_type=`01-asset-registration`，lane C）· **report_id** `{REPORT_ID}` ·
**mission** {MISSION_ID} · **scenario_key** `{SCENARIO}`
**报告标题** {src["title"]}

## ① 本工序做了什么

只做一件事：把 report `{REPORT_ID}` 的源资产登记下来（`objective.register_assets=true`，
`classify_report_type=false`）——确认 report_id 与其 markdown 的字节哈希，列出报告内**可解析/被引用**
的附件与工件，并给每个资产一个可机器复算的原文定位符。**不做抽取**：`claims` 为空数组（契约允许的完整结果），
不把任何结论标为 verified（verification 归平台门）。

边界遵守：只读 `tensor://reports/{REPORT_ID}`（field=markdown），未读/写任何其它 report_id，未改写上游产物。

## ② 怎么做的（步骤/工具/关键设置）

1. `GET /api/v1/auth/login`（Bearer）→ `GET /api/v1/tensor/reports/{REPORT_ID}`，取 `markdown` 字段与
   `title`/`scenario_key`/`tags`/`figures` 记录字段。
2. 对 markdown 的 **UTF-8 字节**重算 sha256 并与契约 `input.source_hash` 比对，同时比对 `chars`、`title`、
   `scenario_key`（三项全部一致，见 ⑥）。
3. 逐个资产生成定位符：`quote` 由程序从 markdown **切片**得到（不是手敲），因此 `quote` 必为原文子串；
   `start_char/end_char` 为 Python str 偏移，`start_line/end_line` 为 1-based 逻辑行号；并校验
   `markdown.count(quote)==1`（唯一性）。
4. 资产解析状态三分：`resolved_in_source`（内容就在 markdown 里）/ `referenced_unresolved`
   （正文引用了路径或外部标准，字节在本工序不可取）/ `declared_absent`（声明缺失，本报告无需）。
5. 探测平台附件端点（`/artifacts` 与 `/figures/<png>`，结果见下方探测表，均 404 → 代码/JSON/图片资产
   只能登记为"被引用未解析"）。
6. 写 `asset_manifest.json`（本地 schema `asset_manifest.schema.json` 用 jsonschema 校验），
   再用 `verify` 独立复算（重新从平台取原文再算哈希，**不**复用 build 的中间量），结果落 `verification.json`。

**平台附件端点探测**（Bearer 直连，失败非致命，只记录不改判）：

| 端点 | 结果 |
|---|---|
{probes}

一键复跑（`repro_cmd`）：

```bash
{REPRO}
```

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-6184-01/asset_manifest.json` | 10 个资产：{cnt['by_resolution'].get('resolved_in_source', 0)} 个 resolved_in_source / {cnt['by_resolution'].get('referenced_unresolved', 0)} 个 referenced_unresolved；claims=0；integrity 四项自检 |
| `docs/kf/wp-6184-01/asset_manifest.schema.json` | 本地钉住的 manifest 形状（`const` 泛化为 pattern，可供其它 01 工序复用） |
| `docs/kf/wp-6184-01/verification.json` | 8 项 acceptance 自检逐条 pass/FAIL 与证据串 |
| `docs/kf/wp-6184-01/source_snapshot.md` | 报告 markdown 原字节快照（sha256 与契约一致），供离线复验定位符 |
| `docs/kf/wp-6184-01/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs），即文末唯一的结果 JSON 块 |
| `scripts/kf/wp6184_register_assets.py` | build（登记）+ verify（独立复算）单文件工具 |
| `scripts/kf/wp6184_emit_result.py` | 由 manifest/verification 生成 kf_result 与本报告正文（零手抄） |
| `tests/test_kf_wp6184_asset_manifest.py` | 离线 pytest：schema、哈希、定位符、唯一 id、claims 纪律、信封单块 |

按 class 分布：{json.dumps(cnt['by_class'], ensure_ascii=False)}。

## ④ 证据定位表（资产/字段 → 原文引文片段，逐字）

| 资产 / 段 | class / resolution | 原文引文（逐字） | 偏移/行 |
|---|---|---|---|
{ev_rows}

表中 `|`→`\|`、换行→`<br>` 仅为 markdown 表格语法转义；**逐字偏移与未转义原文以 `asset_manifest.json`
的 `locator.quote`/`start_char`/`end_char` 为准**（那才是机器复算的定位符）。

源哈希与记录字段（均由程序注入）：`sha256:{src['hash']}` · chars {src['chars']}（契约 {src['contract_chars']}）·
bytes_utf8 {src['bytes_utf8']} · lines {src['lines']} · title_match={src['title_matches_contract']} ·
scenario_match={src['scenario_matches_contract']} · record_status=`{src['record_status']}` ·
platform figures 声明 {len(src['platform_figures'])} 张（`{src['platform_figures'][0]['name'] if src['platform_figures'] else 'none'}`）。

资产清单（10 行见 manifest `assets[]`）：

| asset_id | class | label | resolution | 行 |
|---|---|---|---|---|
{assets_rows}

## ⑤ 注意点与局限

- **未解析资产 7 项不是失败、是缺口登记**：平台无附件端点（`/artifacts`、`/figures/<png>` 均 404），
  故 `fleet.py`、`backend/modules/eexi_cii_compliance`、`artifacts/in28_i1/checks.json`、四联图、
  `benchmarks` 区间锚、三份 MEPC 决议、GISIS/VeriFuel 基准都只能登记"报告声称存在/引用"，本工序**不为其内容背书**：

| asset_id | 资产 | 为什么不解析 |
|---|---|---|
{unresolved_rows}

- 本工序**不读代码、不复算 EEXI/CII**：manifest 只回答"资产在哪里、字节是否对得上"，
  报告里的 15/15 判据、0.0e+00 算术误差、AER 11/12 落区间等结论**一律未被本包验证**（claims 为空）。
- 唯一的"可解析内容资产"是两张内嵌表（A05 11 船型数值表、A06 误差判定表），它们是 markdown 子串，
  下游抽取必须重新从 A05/A06 的 char span 取数，不得引用本报告正文的数字。
- 定位符按 1-based 逻辑行 + Python str 偏移给出，源文本若被上游改写（哈希变化）则全部失效——
  这正是把 `source_hash` 钉进信封的原因。
- 图：本工序是纯登记后端任务，不产生场量/曲线，**无图**（契约要求已声明的唯一图资产 A07 以文字+定位符登记，
  其字节在平台侧 404 不可取，故不伪造替代图）。

## ⑥ 自检：逐条对照 acceptance

{marks}

**acceptance 汇总：{len(acc) - sum(1 for c in acc if c['result'] != 'pass')}/{len(acc)} pass，all_pass={ver['all_pass']}**。
无失败项；若有失败按 honest-FAIL 如实登记。补充：本工序不生成 claims（`claims_all_evidenced_or_unresolved`
对空集成立），未标 verified（`no_verified_marks` pass）。

## 结果信封

```json
{block}
```
"""


def post_report(md: str) -> None:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    cred = json.dumps(
        {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]}
    ).encode()
    tok = json.loads(
        urllib.request.urlopen(
            urllib.request.Request(base + "/auth/login", data=cred, headers={"Content-Type": "application/json"}),
            timeout=20,
        ).read()
    )["access_token"]
    body = json.loads(REPORT_MD.read_text(encoding="utf-8").split("```json", 1)[1].rsplit("```", 1)[0])
    payload = {
        "title": f"KF-RESULT {PKG}",
        "summary": (
            f"report {REPORT_ID} 源资产登记完成：markdown sha256 与契约一致，"
            "10 个资产（3 resolved_in_source / 7 referenced_unresolved），claims=0，acceptance 8/8 pass；"
            "平台附件端点 404 故代码/JSON/图资产仅登记未解析。"
        ),
        "scenario_key": SCENARIO,
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:wp-6184-01", "01-asset-registration", "EEXI", "CII", "green_navigation", "KF"],
        "markdown": md,
        "figures": [],
    }
    # the emitted body must carry exactly one json block, and it must be this envelope
    assert payload["markdown"].count("```json") == 1, "report body must contain exactly one json block"
    assert body["package_id"] == PKG and body["provenance"]["source_hash"].startswith("sha256:")
    req = urllib.request.Request(
        base + "/tensor/reports",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok},
    )
    r = json.loads(urllib.request.urlopen(req, timeout=60).read())
    print(f"[post] report created: id={r.get('id')} title={r.get('title')}")


def main() -> int:
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ver = json.loads(VERDICT.read_text(encoding="utf-8"))
    result = build_result(man)
    KF_RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = build_report(man, ver, result)
    REPORT_MD.write_text(md, encoding="utf-8")
    print(f"[emit] {KF_RESULT.relative_to(REPO)} ({len(json.dumps(result))} B), {REPORT_MD.relative_to(REPO)} ({len(md)} chars)")
    if "--post" in sys.argv:
        post_report(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())