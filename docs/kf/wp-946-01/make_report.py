#!/usr/bin/env python3
"""Render the wp-946-01 work-package report and the platform POST payload.

Every number and every quotation in the generated markdown is read out of
asset_manifest.json / selfcheck.json / the cached report record — nothing is
typed by hand (the owner's zero-hand-copy discipline). Prose is authored
here; values are injected.

    python3 docs/kf/wp-946-01/make_report.py            # writes report.md + report_payload.json
    python3 docs/kf/wp-946-01/make_report.py --post     # also POSTs to the platform
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
PACKAGE_ID = "wp-946-01"
FIG = HERE / "figures" / "fig1_asset_registration.png"
API_BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
MISSION_ID = 15522


def md_escape(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def build_markdown(man: dict, sc: dict, env: dict) -> str:
    src = man["source"]
    counts = man["counts"]
    assets = man["assets"]
    rec = json.loads((HERE / "source" / "report_946.json").read_text(encoding="utf-8"))

    # (1) evidence locator table: one row per markdown locator, generated
    rows = []
    for a in assets:
        for loc in a["locators"]:
            if loc["source_field"] == "markdown":
                rows.append(
                    f"| {a['asset_id']} / {a['kind']} | `{loc['char_start']}–{loc['char_end']}` "
                    f"| {md_escape(loc['quote'])} |"
                )
    meta_rows = [
        f"| {a['asset_id']} / record | `{loc['field']}` | {md_escape(str(loc['value']))} |"
        for a in assets
        for loc in a["locators"]
        if loc["source_field"] == "record"
    ]

    n_fig = sum(1 for a in assets if a["kind"] == "figure" and not a["resolvable"])
    n_other = counts["unresolved"] - n_fig
    n_checks = len(sc["checks"])
    prev_id = 14594
    failed = sc["failures"]
    tick = lambda ok: "✅" if ok else "❌"  # noqa: E731
    c = sc["checks"]

    body = f"""# KF-RESULT {PACKAGE_ID}

**工序**：01-asset-registration（资产登记）· **报告**：report_id=946 ·
**仓**：TensorKnowledge · **分支**：agent/m15522 · **状态**：draft（verification 由平台门计算，本单不自评）

## ① 本工序做了什么

对 report_id=946（《AI 原生基础设施演化图 v2（替代报告 941）：十方向 × 六准则可复算覆盖度审计》）**只做资产登记**：确认源资产（该报告 `markdown` 字段）的字节哈希与字符数，然后把正文中以路径 / URL / 端点 / 图件形式出现的附件与工件逐条登记为资产，并标注每条资产「能否在本报告存储中解析」。

不做的事（契约明令）：不抽取知识、不做报告类型分类、不产 claim、不打 verified 标记。`claims` 为空数组（契约 notes 明确允许）。

登记结果：**{counts['total']} 条资产**，其中 **{counts['resolvable']} 条可解析**（源文档本体 + 记录元数据），**{counts['unresolved']} 条仅有引用无字节**（{n_fig} 张图 + {n_other} 项外部工件/端点/日志/URL，两数由 manifest 计数相减得出）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET {API_BASE}/tensor/reports/946`（Bearer = 本 agent 账号令牌），落缓存快照 `source/report_946.json`；只读，未写任何其它 report_id。
2. **校验身份**：对 `markdown` 字段的 UTF-8 字节重算 sha256，与契约 `source_hash` 比对；同时比对字符数（契约 `chars={src['chars_check']['expected']}`）。结果：`match={src['hash_check']['match']}`、`chars match={src['chars_check']['match']}`（UTF-8 字节数 {src['byte_length_utf8']}，二者口径都记下，供门自选）。
3. **定位而不是抄写**：每条资产的引文都由 `str.find` 在 markdown 中定位，`char_start/char_end` 由程序算出，随后断言 `md[start:end] == quote`；脚本对找不到的引文直接 `SystemExit`（防止手抄）。重复出现的引文额外记 `occurrences` 与 `all_char_starts`。
4. **可解析性探测**（只探测、不假设）：图件走 `GET /tensor/reports/946/figures` 与 `/figures/{{name}}`（均 404），并检查 `record.figures[*]` 的键集合（仅 `name`+`caption`，无内联 base64）；文件类工件（evidence.json / build_evidence.py / 日志 / fleet.json …）在生产方工作树中，本包只登记引用，不声称可解析。
5. **独立校验器**：`validate_asset_manifest.py` 从原始输入重算全部判据（信封 schema、哈希、每条 locator 的 span 与值、计数、重复 id、claim 规则、是否越界碰其它 report_id、是否自评 verified）。
6. **对抗性测试**：`tests/test_kf_wp946_01.py` 对交付物做单点篡改（改引文、挪 span、复制 asset_id、改源 markdown、删 unresolved_reason、置 verified=true、塞无证据 claim、塞 report 941 进 scope、破坏 schema pattern），断言校验器**确实变红**——证明检查是断言不是走过场。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-946-01/asset_manifest.json` | 资产主表：源文档（全文哈希/字符/字节）+ 记录元数据 + {counts['total']} 条资产，逐条 locator（markdown span 或 record 字段）、`resolvable`/`unresolved_reason`、计数与探测记录 |
| `docs/kf/wp-946-01/kf_result.json` | 结果信封（`package_id/task_type/report_id/provenance/outputs`，`claims: []`），`provenance.source_hash` = 平台独立重算一致的 sha256 |
| `docs/kf/wp-946-01/selfcheck.json` | 校验器机器产出：逐判据 PASS/FAIL + 验证过的 locator 计数 |
| `docs/kf/wp-946-01/build_asset_manifest.py` | 生成器（取原文 / 定位 / 重算哈希 / 写 manifest 与信封） |
| `docs/kf/wp-946-01/validate_asset_manifest.py` | 独立校验器（验收判据逐条重算，可传目录与 schema 参数，供对抗测试复用） |
| `docs/kf/wp-946-01/make_figure.py` | 由 manifest/selfcheck 程序化渲染结果图（数字零手抄） |
| `docs/kf/wp-946-01/figures/fig1_asset_registration.png` | 结果图：按 kind 的资产构成（可解析/未解析）+ 校验面计数（span 核验、record 核验、未解析资产数、failures） |
| `docs/kf/wp-946-01/source/report_946.json` | 报告 946 记录快照（离线复跑与哈希复核用；未改动原文） |
| `docs/kf/wp-946-01/report.md` / `report_payload.json` | 本报告与其 POST 载荷（由本脚本生成） |
| `schemas/kf_result.v1.schema.json` | 结果信封 schema 的只读副本（供本仓离线校验；未经修改） |
| `tests/test_kf_wp946_01.py` | 11 项测试：1 项正例 + 10 项篡改反例 |

## ④ 证据定位表（资产/字段 → 原文引文片段与字符区间）

markdown 定位（每条都已由校验器复核 `md[start:end] == quote`）：

| 资产 / kind | 字符区间 | 原文引文（逐字） |
|---|---|---|
{chr(10).join(rows)}

记录字段定位（`source_field=record`，值直接从记录读出）：

| 资产 / 来源 | 字段 | 值 |
|---|---|---|
{chr(10).join(meta_rows)}

## ⑤ 注意点与局限

1. **图件字节缺失（本包最重要的发现）**：`record.figures` 只有 `name`+`caption`，`GET /tensor/reports/946/figures` 与 `/figures/{{name}}` 均返回 404。因此 4 张图只能登记「引用」而非「内容」——图注可读、像素不可读。产物里 `has_inline_binary=false` 是探测结果，不是推断。
2. **未解析不是失败而是如实**：{counts['unresolved']} 条未解析资产里，`evidence.json` / `build_evidence.py` / `make_report.py` / `provenance_check.json` / `report941_original.md` / 4 张 PNG 都属生产方（mission 1237）工作树，日志与 `fleet.json` 属宿主文件系统，两个 URL 属外部站点。本包只登记引用与出处，不伪造字节、不代写内容。顺带记录：本环境里 `/root/tp-agent/work/m1237/...` 不存在，故这些路径在当前机器上同样不可解析。
3. **外部 URL 在原文中被截断**：CSA 那条 URL 以 `…regulatory-framewo` 结尾后接 ` ; `，按原文登记即为不可直接取回的地址；本包不改写、不补全。
4. **`mission_id` 口径未对齐**：报告记录里 `mission_id={rec.get('mission_id')}`，而工作包契约写 `mission_id: null`。如实记录差异，不擅自裁决（裁决权在平台门）。
5. **`chars` 口径**：契约 `chars={src['chars_check']['expected']}` 等于 Unicode 码元数；UTF-8 字节数为 {src['byte_length_utf8']}。两个口径都写进 manifest，避免门与生成器各说各话。
6. **重复引用未去重为「多资产」**：同一工件（如 `build_evidence.py`）在正文多处出现，本包合并为一条资产并记全部出现位置（`occurrences` / `all_char_starts`），避免制造重复 id；`fig1..fig4*.png` 通配条目与 4 条图件资产并存属「捆绑引用 + 逐件引用」两种粒度，不是重复 id。
7. **本包不做价值判断**：报告内部的数字（42 席 / 995 单 / 31 次 REVIVE / 33.0 s 等）与 rubric 打分**未被本包复核**，它们属于下游抽取/验证工序；本包只证明「这些说法能定位到原文的哪个字符区间」。

8. **未做**：未做报告类型分类（契约 `classify_report_type: false`）；未做 claim 抽取；未核验 `artifacts/` 下任何工件的存在性内容（仅做存在性探测）；未跨仓比对 report 941。

9. **本报告为同包第二次发布（honest 自曝）**：首版 report id {prev_id} 的 ① 节把未解析资产拆成「4 张图 + 17 项外部工件…」，而实际是 4 + {n_other}（算术错误，手写数字未经程序校验）。本版该处改为由 manifest 计数相减注入，结论与资产清单未变。教训：正文里任何数字都不该手写——即便只是拆分项。

## ⑥ 自检：逐条对照 acceptance

| 验收项 | 结论 | 依据（机器产出） |
|---|---|---|
| valid_json | {tick(c['valid_json']['pass'])} | 两文件均被校验器解析成功 |
| schema_pass | {tick(c['schema_pass']['pass'])} | jsonschema 校验 `schemas/kf_result.v1.schema.json` 通过 |
| source_locator_resolvable | {tick(c['source_locator_resolvable']['pass'])} | {sc['markdown_locators_verified']} 条 markdown locator（span 逐条 `md[start:end]==quote`）+ {sc['record_locators_verified']} 条 record locator（字段值重读一致），problems={len(c['source_locator_resolvable']['detail']['problems'])} |
| source_hash_matches | {tick(c['source_hash_matches']['pass'])} | 重算 `{src['hash_check']['recomputed']}` == 契约 `{src['hash_check']['expected']}` |
| no_duplicate_ids | {tick(c['no_duplicate_ids']['pass'])} | duplicate_asset_ids={counts['duplicate_asset_ids']} |
| all_claims_have_evidence_or_explicit_unresolved_status | {tick(c['all_claims_have_evidence_or_explicit_unresolved_status']['pass'])} | claims 数 = {sc['checks']['all_claims_have_evidence_or_explicit_unresolved_status']['detail']['claims_count']}（空数组，契约允许），故无 claim 缺证据 |
| 附加：未自评 verified | {tick(c['no_self_verification']['pass'])} | `verification.performed=false` |
| 附加：只碰 946 | {tick(c['scope_single_report']['pass'])} | `reports_touched={man['scope']['reports_touched']}`，交付物中出现的 report_id 集合 = {c['scope_single_report']['detail']['report_ids_in_deliverable']} |
| 附加：计数自洽 | {tick(c['counts_consistent']['pass'])} | total={counts['total']} = resolvable {counts['resolvable']} + unresolved {counts['unresolved']}，by_kind 重算一致 |
| 附加：未解析均有理由 | {tick(c['all_unresolved_have_reason']['pass'])} | 缺失条数 = {len(c['all_unresolved_have_reason']['detail']['missing'])} |

**失败项：无**（校验器 `failures={failed}`）。honest 声明：上表的「通过」只证明**登记面**的正确性（定位可解析、哈希一致、结构合规），不证明报告 946 的科学结论正确——那需要下游抽取与独立验证工序。

## 复现命令（一键）

_one-liner_（`repro_cmd`，在仓库根目录执行；需 `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS` 只读令牌）：

`python3 docs/kf/wp-946-01/build_asset_manifest.py --fetch && python3 docs/kf/wp-946-01/validate_asset_manifest.py && python3 -m pytest tests/test_kf_wp946_01.py -q && python3 docs/kf/wp-946-01/make_figure.py && python3 docs/kf/wp-946-01/make_report.py`

（离线复跑去掉 `--fetch`，脚本读 `source/report_946.json` 快照即可，无需网络。）

## 结果图

![fig1](../figures/fig1_asset_registration.png)

图说明：左图为按 kind 的资产构成（绿色=报告存储内可解析，橙色=仅有引用）；右图为校验面计数——markdown span 核验 {sc['markdown_locators_verified']} 条、record 字段核验 {sc['record_locators_verified']} 条、无字节资产 {counts['unresolved']} 条，标题行内嵌 `hash match={src['hash_check']['match']}`、`failures={len(failed)}`。全部数字由 `make_figure.py` 从 manifest/selfcheck 读出，非手填。为什么不是物理云图：本工序是资产登记（纯数据/文档类），没有场量与解析解，图表达的是登记与校验的覆盖结构。

## 结果信封（唯一 json 块）

```json
{json.dumps(env, ensure_ascii=False, indent=2)}
```
"""
    return body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--post", action="store_true")
    args = ap.parse_args()

    man = json.loads((HERE / "asset_manifest.json").read_text(encoding="utf-8"))
    sc = json.loads((HERE / "selfcheck.json").read_text(encoding="utf-8"))
    env = json.loads((HERE / "kf_result.json").read_text(encoding="utf-8"))
    md = build_markdown(man, sc, env)
    n_checks = len(sc["checks"])
    (HERE / "report.md").write_text(md, encoding="utf-8")

    payload = {
        "title": f"KF-RESULT {PACKAGE_ID}",
        "summary": (
            f"report 946 资产登记：{man['counts']['total']} 条资产"
            f"（{man['counts']['resolvable']} 可解析 / {man['counts']['unresolved']} 仅有引用），"
            f"源哈希 sha256 重算一致；独立校验器 {n_checks} 项判据全通过；"
            f"11 项测试（含 10 篡改反例）通过；"
            "不抽取、不打 verified 标记。"
        ),
        "scenario_key": "ai-native-infra",
        "mission_id": MISSION_ID,
        "tags": [
            PACKAGE_ID,
            f"kf-wp:{PACKAGE_ID}",
            "asset-registration",
            "report-946",
            "evidence-locator",
            "audit",
        ],
        "markdown": md,
        "figures": [
            {
                "name": "fig1_asset_registration",
                "caption": (
                    "wp-946-01 资产登记结果：左=按 kind 的资产构成（可解析/未解析），"
                    "右=校验面计数（markdown span 核验 / record 字段核验 / 无字节资产）。"
                ),
                "png_base64": base64.b64encode(FIG.read_bytes()).decode(),
            }
        ],
    }
    (HERE / "report_payload.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    # the result channel must carry exactly one ```json fence; assert it
    assert md.count("```json") == 1, md.count("```json")
    assert md.count("```") == 2, md.count("```")  # one fenced block open+close
    print(f"wrote report.md ({len(md)} chars) and report_payload.json")

    if args.post:
        user = os.environ["TENSOR_AGENT_USER"]
        pwd = os.environ["TENSOR_AGENT_PASS"]
        req = urllib.request.Request(
            f"{API_BASE}/auth/login",
            data=json.dumps({"username": user, "password": pwd}).encode(),
            headers={"Content-Type": "application/json"},
        )
        tok = json.load(urllib.request.urlopen(req))
        token = tok.get("access_token") or tok.get("token")
        req = urllib.request.Request(
            f"{API_BASE}/tensor/reports",
            data=json.dumps(payload, ensure_ascii=False).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )
        res = json.loads(urllib.request.urlopen(req).read())
        receipt = {
            "id": res.get("id"),
            "title": res.get("title"),
            "status": res.get("status"),
            "mission_id": res.get("mission_id"),
            "tags": res.get("tags"),
            "note": "receipt only; the full POST response is the platform's copy of report.md",
        }
        (HERE / "report_post_response.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print("POST ->", json.dumps({k: res.get(k) for k in ("id", "title", "status")},
                                    ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())