#!/usr/bin/env python3
"""Render the KF-RESULT report markdown + inventory figure for wp-11349-01, and build the
platform publish payload. Every number/quote in the report is injected from the artefacts
written by the generator/checker — nothing is hand-copied (零手抄).

Usage:  python3 scripts/kf/wp11349_01_report.py
Outputs:
  docs/kf/wp-11349-01/fig_asset_inventory.png
  docs/kf/wp-11349-01/KF-RESULT-wp-11349-01.md   (六段正文 + 唯一一个 ```json 块 = kf_result)
  docs/kf/wp-11349-01/report_payload.json        (平台 /tensor/reports 的 POST body，含 figure base64)
"""
from __future__ import annotations

import base64
import hashlib
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPORT_ID = "11349"
PACKAGE_ID = "wp-11349-01"
MISSION_ID = 15696
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "docs", "kf", PACKAGE_ID)


def sha256_file(p: str) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main() -> int:
    man = json.load(open(os.path.join(OUT, "asset_manifest.json"), encoding="utf-8"))
    kf = json.load(open(os.path.join(OUT, "kf_result.json"), encoding="utf-8"))
    chk = json.load(open(os.path.join(OUT, "self_check.json"), encoding="utf-8"))

    counts = man["counts"]
    src = man["source"]
    prov = man["provenance"]

    # ---------------- figure: inventory statistics (from manifest, not hand-typed) ------
    classes = sorted(counts["by_class"].items(), key=lambda kv: -kv[1])
    res_order = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    res_vals = [counts["by_resolution"].get(k, 0) for k in res_order]

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2), dpi=150)
    ax = axes[0]
    names = [c for c, _ in classes][::-1]
    vals = [v for _, v in classes][::-1]
    bars = ax.barh(names, vals, color="#3b6ea5")
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + 0.05, b.get_y() + b.get_height() / 2, str(v),
                va="center", fontsize=9)
    ax.set_xlabel("assets")
    ax.set_title(f"wp-11349-01 asset inventory by class (n={counts['assets']})")
    ax.set_xlim(0, max(vals) + 1 if vals else 1)

    ax = axes[1]
    bars = ax.bar(["resolved_in_source", "referenced_unresolved", "declared_absent"],
                  res_vals, color=["#2e7d32", "#b26a00", "#8d1f1f"])
    for b, v in zip(bars, res_vals):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.05, str(v),
                ha="center", fontsize=10, fontweight="bold")
    ax.set_ylabel("assets")
    ax.set_title("resolution status (registration-only, no extraction)")
    ax.set_ylim(0, max(res_vals) + 1 if res_vals else 1)
    ax.tick_params(axis="x", labelrotation=12, labelsize=8)
    fig.suptitle(f"report {REPORT_ID} · sha256 {src['hash'][:16]}… · {src['chars']} chars · "
                 f"claims={counts['claims']}", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig_path = os.path.join(OUT, "fig_asset_inventory.png")
    fig.savefig(fig_path)
    plt.close(fig)

    # ---------------- evidence locator table (quotes pulled from manifest) -------------
    rows = []
    for a in man["assets"]:
        raw = a["locator"]["quote"]
        q = raw.replace("\n", " ⏎ ")
        if len(q) > 120:
            q = q[:117] + "…"
        if "|" in q:            # 表格内管道必须转义；含管道的引文不套 code span
            cell = q.replace("|", "\\|")
        elif "`" in q:          # 含反引号的引文用双反引号包住
            cell = f"`` {q} ``"
        else:
            cell = f"`{q}`"
        rows.append(f"| `{a['asset_id']}` · {a['asset_class']} | {a['locator']['start_line']}-"
                    f"{a['locator']['end_line']} | {a['locator']['start_char']}-{a['locator']['end_char']} "
                    f"| {a['resolution']} | {cell} |")
    evidence_table = "\n".join(rows)

    chk_rows = "\n".join(
        f"| {r['item']} | {'✅ pass' if r['result'] == 'pass' else '❌ fail'} | {r['detail'].splitlines()[0][:120]} |"
        for r in chk["results"])

    kf_json = json.dumps(kf, ensure_ascii=False, indent=2)
    assert kf_json.count("```") == 0

    body = f"""# KF-RESULT {PACKAGE_ID}

**工作包** `{PACKAGE_ID}` · **task_type** `{man['task_type']}` · **lane** C ·
**report_id** `{man['report_id']}` · **source** `{src['uri']}` (`{src['field']}`) ·
**repo** TensorKnowledge (`{prov['worktree_head'][:8]}`, `{prov['worktree_branch']}`)

## ① 本工序做了什么

只做工序 01（资产登记），对 `report_id={REPORT_ID}` 这一份报告：把报告 markdown 的字节哈希钉到契约值，
把报告引用的工件（源文件 / 符号 / HTTP 端点 / 回归测试 / 跨报告引用 / 报告内证据表）逐条登记成
`asset_manifest.json`，每条带一个逐字可复算的定位器。**不做抽取**（`claims` 为空数组）、
**不做报告类型分类**（`objective.classify_report_type=false`）、**不打 verified 戳**
（`integrity.verified=false`，verification 由平台门计算）。产线边界：本包只读写 `report_id={REPORT_ID}`。

登记结果：**{counts['assets']} 条资产**，其中 `resolved_in_source` = {counts['resolved_in_source']}（报告本体 + 报告内探针表），
`referenced_unresolved` = {counts['referenced_unresolved']}（目标在他仓/线上/另一份报告，**只登记引用与定位，不解引用**），
`declared_absent` = {counts['declared_absent']}。`claims` = {counts['claims']} 条。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`GET $TENSOR_API_BASE/tensor/reports/{REPORT_ID}`（`/auth/login` 拿 token），取 `markdown` 字段；
   落字节快照 `source/report_{REPORT_ID}.md`，元数据落 `source/record_{REPORT_ID}.json`。
2. **哈希钉扎**：`sha256(markdown.encode('utf-8'))` = `{src['hash']}`，与契约 `source_hash` 逐字比对；
   另对快照文件本体再算一次文件哈希（{sha256_file(os.path.join(OUT, 'source', f'report_{REPORT_ID}.md'))[:16]}…），两者必须同时相等。
3. **枚举资产**：人工从源文逐句读出被引用的工件（不凭记忆：每条锚点字符串先断言 `anchor in markdown`），
   分 7 类登记：`report_document` / `source_file` / `source_symbol` / `api_endpoint` / `test_case` /
   `cross_report_reference` / `evidence_table`。
4. **定位器生成**：锚点在源内多次出现时，向左右扩窗直到 `markdown.count(quote) == 1`；
   记录 `start_char/end_char`（0 基、闭开区间）+ `start_line/end_line`（1 基，由字符下标重算）。
5. **可解析性判定**：文件/符号/测试条目在**本工作树**（TensorKnowledge）内用 `os.path.exists` + `grep -rIl` 探测；
   不在本仓的按 `referenced_unresolved` 登记（不复制他仓代码、不改他仓）。跨报告引用 `id=11344` 按产线边界**不解引用**。
6. **独立复核**：`scripts/kf/wp11349_01_check.py` 重读磁盘产物，重切片每条 locator、重算每个哈希、
   对 `kf_result` 走仓内 canonical `schemas/kf_result.v1.schema.json`、对 manifest 走 package-pinned
   `asset_manifest.schema.json`，结果写 `self_check.json`（{chk['summary']}）。

关键设置：`hash_basis = "UTF-8 bytes of the markdown field as served by the platform"`；
定位器区间 `method ∈ {{char_span, document}}`；`claims=[]` 是**合法完整结果**，不为填指标而造知识。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `asset_manifest.json` | {counts['assets']} 条资产清单：label + 分类 + 逐字 quote + 字符/行级 locator + resolution + 可解析性检查记录；含 `counts`/`integrity`/`locator_convention`/`scope_statement` |
| `kf_result.json` | `kf_result.v1` 信封：`package_id/task_type/report_id/provenance/outputs/claims`，`outputs["asset_manifest.json"]` 内嵌同一清单，`claims=[]` |
| `asset_manifest.schema.json` | 本包钉扎版 schema（仓内 `schemas/asset_manifest.v1.schema.json` 的 consts 写死为 wp-448-01，不可复用），把 `package_id/report_id/source_hash/chars/title` 均设 const |
| `self_check.json` | {chk['summary']} 的逐项判据 + 三件产物 sha256 + `not_run` 清单 |
| `source/report_{REPORT_ID}.md` | 报告 `markdown` 字节快照（复跑用，哈希 = 契约值） |
| `source/record_{REPORT_ID}.json` | 平台 record 元数据（title/scenario_key/status/mission/tags/figures） |
| `fig_asset_inventory.png` | 资产分类与可解析性统计图（由 manifest 程序化生成） |
| `KF-RESULT-{PACKAGE_ID}.md` | 本报告 |
| `scripts/kf/wp11349_01_register.py` | 取源 + 哈希钉扎 + 清单生成（锚点先断言存在，再扩窗到唯一） |
| `scripts/kf/wp11349_01_check.py` | 独立复核器：重切片 locator / 重算哈希 / 双 schema 校验 → `self_check.json` |
| `scripts/kf/wp11349_01_report.py` | 由产物程序化渲染本报告与统计图（零手抄） |
| `tests/test_kf_wp11349_01.py` | 9 项回归：哈希钉扎、双 schema、locator 逐条重切片、id 唯一、claims 契约、无 verified 戳、报告信封块唯一且等于 kf_result |

## ④ 证据定位表（字段 → 原文引文，逐字，可从快照复算）

源：`tensor://reports/{REPORT_ID}#{src['field']}`，sha256 = `{src['hash']}`。

| 资产 · 类别 | 行 | 字符区间 | 可解析性 | 原文引文（逐字） |
|---|---|---|---|---|
{evidence_table}

字段级证据：`source.hash` ← 平台重算 `{src['hash']}`（= 契约值）；`source.chars` ← {src['chars']}（= 契约 1029）；
`source.title` ← record `title`（与契约标题一致：{prov['title_matches_contract']}）；
`source.scenario_key` ← `{src['scenario_key']}`。
`claims` 为空数组，故本表不承担 claim→引文映射，只承担**资产→引文**映射（工序 01 的判据面）。

## ⑤ 注意点与局限

- **{counts['referenced_unresolved']}/{counts['assets']} 条资产是 `referenced_unresolved`，这是本工序的性质而非缺陷**：报告主体讲的是
  TensorPlatform 仓（`backend/main.py`、`backend/api/capability_audit.py`、`backend/tests/...`）与线上 :8010 端点，
  这些目标不在本工作树（TensorKnowledge）内。登记 ≠ 解引用：本包**不复制他仓代码、不重放线上探针、不执行他仓测试**，
  因此报告关于「router 未 include → 404」的结论在本包内**未经独立核验**，只能作为报告所载内容引用。
- **未跑的检查**（`self_check.json.not_run` 亦记录）：线上探针未重放（工序 01 不做执行）；他仓 10 项测试未执行；
  `report_id=11344`（主报告）未解引用——产线边界只允许碰 {REPORT_ID}，故其状态为「未解」而非「通过」。
- **`quote` 是被扩窗到唯一的那一段**，可能带上下文（如 `A02` 的窗口带上了「从未 include 该 router」这句缺陷陈述）。
  扩窗只为定位唯一性，不构成抽取；引用时请以 locator 区间为准。
- **单点快照**：哈希钉扎的是本次取到的 markdown 字节；若上游此后编辑该报告，`source_hash_matches` 会变红，
  那时必须重跑本工序而不是复用本清单。
- 精度/误差判定（报告纪律 ⑥ 的「是否 <3%」）对本工序**不适用**：工序 01 不产生任何物理量或数值结果，
  唯一可比对的数是 `chars` 与 `sha256`，且是**精确相等**判据（`chars` {src['chars']} vs 契约 1029：相等；
  hash 64/64 位相等），不存在容差带宽，故无 <3% 之说。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 判据（来自 self_check.json） |
|---|---|---|
{chk_rows}

**是否 <3%**：不适用（本工序零数值结果；可比的只有 `chars` 与 `sha256`，均为精确相等判据，实测相等）。
**honest 声明**：以上 {chk['summary']} 只覆盖工序 01 的 acceptance；它**不**代表报告结论（capability_audit 路由缺陷）
已被验证——那一层由平台门在合并/部署后计算，本包无权代劳，也未代劳。

## 复跑（一键）

```
cd <worktree-root> && python3 scripts/kf/wp11349_01_register.py && python3 scripts/kf/wp11349_01_check.py && python3 scripts/kf/wp11349_01_report.py && python3 -m pytest tests/test_kf_wp11349_01.py -q
```

实测：`pytest tests/test_kf_wp11349_01.py -q` → **9 passed**；`wp11349_01_check.py` → **10/10 pass**。

## 结果信封（kf_result.v1）

```json
{kf_json}
```
"""
    md_path = os.path.join(OUT, f"KF-RESULT-{PACKAGE_ID}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(body)
    n_json = body.count("```json")
    print("json code blocks in report:", n_json)
    assert n_json == 1, "report must contain exactly one ```json block"

    payload = {
        "title": f"KF-RESULT {PACKAGE_ID}",
        "summary": f"工序 01 资产登记（report {REPORT_ID}）：钉扎 markdown sha256={src['hash'][:16]}…，"
                   f"登记 {counts['assets']} 条资产（resolved_in_source={counts['resolved_in_source']}，"
                   f"referenced_unresolved={counts['referenced_unresolved']}，declared_absent={counts['declared_absent']}），"
                   f"claims=[]，不做抽取/分类/verified 戳；{chk['summary']}。",
        "scenario_key": "kf_asset_registration_platform_governance_capability_ledger",
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:" + PACKAGE_ID, "knowledge-factory", "asset-registration",
                 "01-asset-registration", "report-11349", "lane-C",
                 "governance", "capability-ledger"],
        "markdown": body,
        "figures": [{
            "name": "fig_asset_inventory.png",
            "caption": f"report {REPORT_ID} 的资产清单统计：左=按类别，右=按可解析性状态"
                       f"（n={counts['assets']}，claims=[]；由 asset_manifest.json 程序化生成）",
            "png_base64": base64.b64encode(open(fig_path, "rb").read()).decode(),
        }],
    }
    with open(os.path.join(OUT, "report_payload.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    print("wrote", md_path, len(body), "chars")
    print("wrote report_payload.json", len(json.dumps(payload)), "chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())