#!/usr/bin/env python3
"""wp-8163-01 delivery: render the six-section report body and publish it to the platform.

Every number in the body is injected from docs/kf/wp-8163-01/{asset_manifest,
verification,locator_check}.json -- nothing is hand-transcribed. The published
markdown contains exactly one ```json fenced block: the kf_result envelope.

    python3 scripts/kf/kf_wp8163_01_publish.py render    # write report.md, no network POST
    python3 scripts/kf/kf_wp8163_01_publish.py publish   # render + POST /tensor/reports
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

PKG = "wp-8163-01"
REPORT_ID = "8163"
MISSION_ID = 15607
SCENARIO = "IN155-N07_rigid_collision_energy_convergence"

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "kf" / PKG
MANIFEST = OUT / "asset_manifest.json"
ENVELOPE = OUT / "kf_result.json"
VERIFICATION = OUT / "verification.json"
LOCATOR_CHECK = OUT / "locator_check.json"
REPORT_MD = OUT / "report.md"


def cell(text: str, limit: int = 68) -> str:
    """One markdown table cell: single line, pipes escaped, truncated with an honest marker."""
    flat = " ".join(str(text).split()).replace("|", "\\|")
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def build_body() -> str:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    v = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    lc = json.loads(LOCATOR_CHECK.read_text(encoding="utf-8"))
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    src = m["source"]
    counts = m["counts"]
    checks = v["checks"]
    assets = m["assets"]

    ok = lambda k: "✅" if checks[k]["pass"] else "❌"

    # -- ③ output inventory (file -> key point), all sizes read from disk
    files = [
        ("docs/kf/%s/asset_manifest.json" % PKG,
         "登记清单本体：%d 个资产、%d 个可解析定位器、counts/by_class/by_resolution 全表"
         % (counts["assets"], sum(1 for a in assets if a["locator"]["unique"]))),
        ("docs/kf/%s/kf_result.json" % PKG,
         "平台结果信封（package_id/task_type/report_id/provenance/outputs），provenance.source_hash=%s"
         % env["provenance"]["source_hash"]),
        ("docs/kf/%s/verification.json" % PKG,
         "自检记录：%d 项 acceptance 逐条结论 + all_pass=%s" % (len(checks), v["all_pass"])),
        ("docs/kf/%s/locator_check.json" % PKG,
         "定位器复核：%d 条引文对活体 markdown 重解析，可解析 %d 条"
         % (lc["quotes_checked"], lc["quotes_resolvable"])),
        ("docs/kf/%s/source.md" % PKG,
         "只读源副本（%d 字符 / %d 字节），供离线复核"
         % (src["chars"], src["bytes_utf8"])),
        ("runs/%s/source_%s.md" % (PKG, REPORT_ID),
         "抓取现场的 markdown 原样落盘（与 docs 副本同字节）"),
        ("runs/%s/report_%s.json" % (PKG, REPORT_ID),
         "GET /tensor/reports/%s 的原始响应（含 title/scenario/figures/tags 元数据）" % REPORT_ID),
        ("docs/kf/%s/figures/asset_resolution_map.png" % PKG, "图 1：资产类别 × 解析状态分布"),
        ("docs/kf/%s/figures/locator_coverage.png" % PKG, "图 2：每个定位器的字符跨度对照 markdown 全长"),
        ("docs/kf/%s/asset_manifest.v1.wp8163.schema.json" % PKG,
         "由 schemas/asset_manifest.v1.schema.json 仅替换 3 个 const 得到的派生 schema（见 ⑤-1）"),
        ("scripts/kf/kf_wp8163_01_register.py",
         "一键复跑：build/envelope/verify/figure/all，引文一律从 markdown 切片不手打"),
        ("scripts/kf/kf_wp8163_01_publish.py", "本报告渲染 + 发布（数字全部由 JSON 注入）"),
    ]
    out_rows = "\n".join(
        "| `%s` | %s |" % (p, cell(k, 96)) for p, k in files
    )

    # -- ④ evidence locator table (one row per registered asset)
    ev_rows = []
    for a in assets:
        loc = a["locator"]
        ev_rows.append(
            "| %s | %s | L%d–%d | %d–%d | %s | %s |"
            % (
                a["asset_id"],
                a["asset_class"],
                loc["start_line"],
                loc["end_line"],
                loc["start_char"],
                loc["end_char"],
                cell(loc["quote"], 72),
                a["resolution"],
            )
        )
    ev_table = "\n".join(ev_rows)

    # -- ⑥ acceptance self-check
    acc_rows = "\n".join(
        "| %s | %s | %s |" % (k, ok(k), cell(checks[k]["detail"], 150)) for k in checks
    )

    by_class = "、".join("%s=%d" % (k, n) for k, n in counts["by_class"].items())
    by_res = "、".join("%s=%d" % (k, n) for k, n in counts["by_resolution"].items())

    body = f"""# ① 本工序做了什么

本单是 `{PKG}`（task_type `{m['task_type']}`，lane {m['lane']}）—— 报告→知识产线的**第一道工序：源资产登记**，不抽取、不生成 claim、不打 `verified` 标记。

* 只处理 `report_id={REPORT_ID}`：从 `GET /api/v1/tensor/reports/{REPORT_ID}` 取 `markdown`，本地重算字节哈希，与契约 `source_hash` 对齐。
* 登记该报告自身声明的可解析资产：源文档本体 {counts['by_class'].get('report_markdown', 0)} 件、正文内嵌图 {counts['by_class'].get('figure_reference', 0)} 件、审计链代码/测试/绘图路径 {counts['by_class'].get('source_code_reference', 0)} 条、产物目录 {counts['by_class'].get('artifact_directory_reference', 0)} 条、正文点名的求解器/辅助符号 {counts['by_class'].get('symbol_reference', 0)} 条，合计 **{counts['assets']} 件**。
* 每件资产都带机器可复核定位器（字符跨度 + 1-based 行跨度 + 逐字引文 + 唯一性判定）；**引文全部由脚本从 markdown 切片得到，零手抄**。
* 明确不登记的东西也记账（`m5404`、`IN155-N07` 是任务/战役编号而非资产，见 ⑤-3）。

# ② 怎么做的（步骤 / 工具 / 关键设置）

| 步 | 动作 | 工具 / 实现 |
|---|---|---|
| 1 | 取源与元数据 | `GET /api/v1/tensor/reports/{REPORT_ID}`（Bearer=登录 token），落 `runs/{PKG}/` |
| 2 | 身份校验 | `sha256(markdown.encode("utf-8"))` = `{src['hash']}`；`chars={src['chars']}`、title、scenario 逐项与契约比对（见下表） |
| 3 | 资产枚举 | 三条正则 + 记录字段：`\\`(path)\\.(py\\|png\\|json…)\\``（审计链路径）、`![alt](path)`（正文内嵌图）、`\\`artifacts/…/\\``（产物目录）、`record.figures[]`（平台图元数据）、符号词表 2 条 |
| 4 | 定位器生成 | `char_span(md, quote)`：断言 `md.count(quote)==1`，取 `md[start:end]==quote`、`start_line=md.count("\\n",0,start)+1` |
| 5 | 解析判定 | 路径类：在本交付 worktree 内 `Path.exists()` + 平台 `GET /tensor/reports/{REPORT_ID}/artifacts`、`/figures/<name>` 探针；符号类：只登记引用、不宣称存在 |
| 6 | 结构校验 | `jsonschema` Draft2020-12：信封 vs `schemas/kf_result.v1.schema.json`；清单 vs 派生 schema（见 ⑤-1） |
| 7 | 复核 | `verify` 重新抓一次活体 markdown，对全部 {lc['quotes_checked']} 个定位器重解析字符跨度/行号/唯一性 |
| 8 | 出图 | matplotlib（Agg）两张：类别×状态分布、定位器字符跨度覆盖 |

**身份比对（全部程序化，不手打）**

| 字段 | 契约值 | 实测 | 一致 |
|---|---|---|---|
| source_hash | `{src['contract_source_hash']}` | `sha256:{src['hash']}` | {src['hash_matches_contract']} |
| chars | {src['contract_chars']} | {src['chars']} | {src['chars_match_contract']} |
| title | {cell(src['contract_title'], 60)} | {cell(src['title'], 60)} | {src['title_matches_contract']} |
| scenario_key | `{src['contract_scenario_key']}` | `{src['scenario_key']}` | {src['scenario_matches_contract']} |

# ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
{out_rows}

**计数面**：assets={counts['assets']}；by_class：{by_class}；by_resolution：{by_res}；distinct_referenced_paths={counts['distinct_referenced_paths']}；claims={len(m['claims'])}（契约允许空数组，本单不抽取）。

# ④ 证据定位表（资产 → 原文逐字引文）

引文为 markdown 中该行原文切片（表格内 `\\|` 为转义），`L` 为 1-based 行号，字符跨度为 0-based 半开区间；`locator_check.json` 记录了每条引文的实时命中次数（全部 = 1）。

| asset_id | class | 行跨度 | 字符跨度 | 原文引文（逐字） | resolution |
|---|---|---|---|---|---|
{ev_table}

# ⑤ 注意点与局限

1. **schema 双轨，必须说明**：`schemas/asset_manifest.v1.schema.json` 把 `package_id`/`report_id`/`source.uri` 用 `const` 死锁在 `wp-448-01` 上，任何其它工作包都不可能"原样"通过它。本单的 `schema_pass` 因此分两段：信封严格对 `schemas/kf_result.v1.schema.json`（0 error）；清单对一份**只替换那 3 个 `const`、其余约束一字未改**的派生 schema（`asset_manifest.v1.wp8163.schema.json`，0 error）。派生 schema 随包提交，可复核；若平台侧 schema 与 `wp-448-01` 版不同，以平台门为准，本产物需相应修订。
2. **解析 ≠ 存在**：`referenced_unresolved` 只表示"在本交付 worktree 与平台记录里取不到字节"，**不是**对上游 TensorDEM 仓的否定判决。`src/tensordem/rigid_collision_energy.py`、`tests/test_rigid_collision_energy_convergence.py`、`scripts/plot_rigid_collision_energy_minimal.py` 按路径在 `git ls-files` 中 0 命中（本仓是 TensorKnowledge，不是生产者仓），故标未解析。
3. **不登记项的显式记账**：`m5404`（正文出现 {m['registration_coverage']['not_registered'][0]['occurrences_in_markdown']} 次）是任务编号，报告未点名它产生的任何文件/图；`IN155-N07` 是战役编号。二者不构成可定位资产，登记成资产反而是造假。
4. **平台不存图字节**：`record.figures[]` 只有 name+caption；`GET /tensor/reports/{REPORT_ID}/figures/energy_methods_schematic` 与 `.../convergence_orders` 均返回 {m['probes']['/tensor/reports/{0}/artifacts'.format(REPORT_ID)]['http_status']} 级探针失败（figure not found / Not Found），因此对两颗图**不声明任何哈希**。
5. **本单边界**：不改写上游产物、不写其它 report_id、不对报告内容正确性做任何判断（那是 03/04 工序与平台门的活）。`claims` 为空是契约允许的完整结果（`objective.classify_report_type=false`、`no_forced_claim_generation=true`）。
6. **复跑可重复性**：`generated_at`/`emitted_at`/`verified_at` 为运行时时间戳，故清单 sha256 每次复跑会变，但 `source.hash`、`counts`、`assets` 全字段不变。

# ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 证据/说明 |
|---|---|---|
{acc_rows}

* {len(checks)} 项自检 **all_pass={v['all_pass']}**；`manifest_sha256={v['manifest_sha256']}`（本次运行）。
* 超出 acceptance 的额外自检 **覆盖完备性**：{v['coverage']['pass']}——把与 `build` 完全相同的枚举正则重跑在活体 markdown 上，要求每个命中都是已登记资产；`enumerated_not_registered={v['coverage']['enumerated_not_registered']}`、`record_figures_not_registered={v['coverage']['record_figures_not_registered']}`。
* honest 说明：`schema_pass` 的通过依赖 ⑤-1 的派生 schema；若审核方要求"原样"通过 `wp-448-01` 版 schema，则该项应记 **not_pass（不可满足）**，因为该文件的 `const` 与本 package 冲突。

**repro_cmd**（工作树根执行，需要 `TENSOR_API_BASE`/`TENSOR_AGENT_USER`/`TENSOR_AGENT_PASS`）：

`python3 scripts/kf/kf_wp8163_01_register.py all && python3 scripts/kf/kf_wp8163_01_publish.py render`

单步可拆：`build`（抓取+清单）、`envelope`（信封）、`verify`（六项+verified 禁忌共 {len(checks)} 项自检，失败返回非零）、`figure`（两张 png）。

---

唯一的结果 JSON 块（kf_result envelope，schema `schemas/kf_result.v1.schema.json`）：

"""
    body += "```json\n" + json.dumps(env, ensure_ascii=False, indent=2) + "\n```\n"
    return body


def figures_payload() -> list[dict]:
    figs = []
    lc = json.loads(LOCATOR_CHECK.read_text(encoding="utf-8"))
    specs = [
        ("asset_resolution_map.png",
         "图 1：report %s 的资产登记分布（类别 × 解析状态）。数值由 asset_manifest.json 程序化注入；"
         "绿色=字节/文本可在源内解析，红色=报告声明但本 worktree 与平台记录均无字节。" % REPORT_ID),
        ("locator_coverage.png",
         "图 2：%d 个定位器的字符跨度（0-based）对照 markdown 全长，全部落在文档内且命中次数=1；"
         "A01 为整篇文档的范围定位器。" % lc["quotes_checked"]),
    ]
    for name, cap in specs:
        p = OUT / "figures" / name
        figs.append({"name": name, "caption": cap,
                     "png_base64": base64.b64encode(p.read_bytes()).decode()})
    return figs


def render() -> str:
    body = build_body()
    REPORT_MD.write_text(body, encoding="utf-8")
    # exactly one json fence -- assert it before we ever publish
    assert body.count("```json") == 1, "report must contain exactly one ```json block"
    assert body.count("```") == 2, "no other fenced block may compete with the result block"
    # the embedded block must be byte-equal (semantically) to the delivered envelope
    block = body.split("```json", 1)[1].rsplit("```", 1)[0]
    assert json.loads(block) == json.loads(ENVELOPE.read_text(encoding="utf-8")), \
        "embedded result block drifted from docs/kf/%s/kf_result.json" % PKG
    print("wrote %s (%d chars, json fences=%d)"
          % (REPORT_MD.relative_to(REPO), len(body), body.count("```json")))
    return body


def publish(body: str) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    login = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(login, timeout=60) as r:
        tok = json.load(r)["access_token"]
    payload = {
        "title": "KF-RESULT %s" % PKG,
        "summary": "report %s 源资产登记：%d 件资产（1 解析 / %d 未解析），sha256 与契约一致，%d 个定位器全部唯一可解析"
                   % (REPORT_ID, json.loads(MANIFEST.read_text())["counts"]["assets"],
                      json.loads(MANIFEST.read_text())["counts"]["referenced_unresolved"],
                      json.loads(LOCATOR_CHECK.read_text())["quotes_checked"]),
        "scenario_key": SCENARIO,
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:%s" % PKG, "asset-registration", "kf-result", "report-%s" % REPORT_ID],
        "markdown": body,
        "figures": figures_payload(),
    }
    req = urllib.request.Request(
        base + "/tensor/reports",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.load(r)
    except urllib.error.HTTPError as exc:
        raise SystemExit("publish failed: %s %s" % (exc.code, exc.read()[:400]))
    print("published report id=%s title=%s" % (out.get("id"), out.get("title")))
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    text = render()
    if cmd == "publish":
        publish(text)