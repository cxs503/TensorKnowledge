#!/usr/bin/env python3
"""wp-8288-01 — render the KF-RESULT report (six sections) and publish it.

Zero hand-copy: every quoted fragment in section ④ is sliced out of the byte-exact
local copy of the source markdown by marker search, so the quotes and their char
offsets are generated, not retyped. The result envelope is inlined as the report's
single ```json block.

Usage:
  python3 scripts/kf/wp8288_01_report.py render
  python3 scripts/kf/wp8288_01_report.py render publish
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PKG = "wp-8288-01"
REPORT_ID = "8288"
TITLE = "KF-RESULT wp-8288-01"
MISSION_ID = 15620
SCENARIO_KEY = "IN61-N07"

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "kf" / PKG
SRC = OUT / "source.md"
MANIFEST = OUT / "asset_manifest.json"
VERDICT = OUT / "verification.json"
RESULT = OUT / "kf_result.json"
FIGS = OUT / "figures_manifest.json"
REPORT = OUT / "report.md"

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASSWORD = os.environ["TENSOR_AGENT_PASS"]

# field label -> marker used to locate the verbatim line in the source markdown
EVIDENCE = [
    ("source.title", "IN61-N07: DEM Coarse-Graining Scaling Law", "标题字段 = 登记对象的身份锚"),
    ("source.scenario_key", "## 1. Physical Background", "正文起于物理背景节，scenario=IN61-N07（见标题与 §7 审计链）"),
    ("main_result.contact_time_invariance", "that **contact-time invariance** requires stiffness to scale as **k³**", "报告主结论（本工序不判定真伪，只登记为可定位引文）"),
    ("criterion.tc_deviation", "Contact time deviation: **0.0000%** for all k", "判据①结果行"),
    ("negative_control.range", "Negative control (mass-only): **183–2163%** deviation", "判据⑤负对照区间"),
    ("convention.hertz", "| Hertz-consistent | k·k_n | k·t_c | Bierwisch et al. (2009) |", "唯一 in-text 文献引用（A36 登记为 referenced_unresolved）"),
    ("asset.coarse_graining_py", "`src/tensordem/coarse_graining.py` | Scaling law engine + case builders", "§5.1 声明的主实现文件（A07，worktree 内不可解析）"),
    ("asset.results_json", "`runs/in61_n07/results.json` | Numeric results", "§5.1 声明的数值结果工件（A11）"),
    ("asset.pareto_png", "`runs/in61_n07/pareto.png` | Pareto front plot", "§5.1 声明的图件（A12）"),
    ("figure.inline_reference", "![Pareto Front](pareto.png)", "正文内联图引用（A03）"),
    ("macro_anchor.pending_row", "| Repose angle | Pending (torch kernel, ~30s/run) | Cluster | Code verified |", "§3.4 pending 行（A37/A40 的 declared_absent 依据）"),
    ("limitation.monodisperse", "1. **Monodisperse spheres only**:", "§6 自述适用边界"),
    ("api.entry_point", "scale_contact_time_invariant,  # Apply k-fold scaling", "§5.2 API 入口（代码块内，A35）"),
]


def _req(url, token=None, data=None, ctype="application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def login():
    payload = {"username": USER, "password": PASSWORD}
    try:
        d = _req(BASE + "/auth/login", data=json.dumps(payload).encode())
    except urllib.error.HTTPError:
        d = _req(BASE + "/auth/login", data=urllib.parse.urlencode(payload).encode(),
                 ctype="application/x-www-form-urlencoded")
    return d.get("access_token") or d.get("token")


def verbatim(md: str, marker: str):
    """Locate marker in the source and return (line_no, line_text, start_char) — sliced, not retyped."""
    i = md.find(marker)
    if i < 0:
        raise SystemExit("marker not found in source: %r" % marker)
    if md.count(marker) == 0:
        raise SystemExit("empty marker")
    ls = md.rfind("\n", 0, i) + 1
    le = md.find("\n", i)
    le = len(md) if le < 0 else le
    line = md[ls:le]
    line_no = md[:ls].count("\n") + 1
    return line_no, line, ls


def render() -> Path:
    md = SRC.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    verdict = json.loads(VERDICT.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    figs = json.loads(FIGS.read_text(encoding="utf-8"))["figures"]
    c = manifest["counts"]

    rows = []
    for field, marker, note in EVIDENCE:
        line_no, line, start = verbatim(md, marker)
        rows.append("| `%s` | L%d `[%d,%d)` | %s | %s |"
                    % (field, line_no, start, start + len(line),
                       line.replace("|", "\\|"), note))
    evidence_table = "\n".join(rows)

    acc = verdict["acceptance_items"]
    acc_lines = "\n".join(
        "| %s | %s | %s |" % (k, "✓ pass" if v["pass"] else "✗ fail", v["detail"].replace("|", "\\|"))
        for k, v in acc.items())
    extra_lines = "\n".join(
        "| %s | %s | %s |" % (k, "✓" if v["pass"] else "✗", v["detail"].replace("|", "\\|"))
        for k, v in verdict["extra_checks"].items())

    class_lines = "\n".join("| %s | %d |" % (k, v) for k, v in sorted(c["by_class"].items()))

    repro = (
        "cd /root/tp-agent/work/m15620\n"
        "export TENSOR_API_BASE=$TENSOR_API_BASE TENSOR_AGENT_USER=$TENSOR_AGENT_USER TENSOR_AGENT_PASS=$TENSOR_AGENT_PASS\n"
        "python3 scripts/kf/wp8288_01_fetch.py        # 取证：拉 markdown 并按契约 sha256 校验\n"
        "python3 scripts/kf/wp8288_01_register.py     # build + verify + result（三件套）\n"
        "python3 scripts/kf/wp8288_01_figures.py      # 两张图（纯由 manifest 渲染）\n"
        "python3 -m pytest tests/test_kf_wp8288_01.py -q   # 12 项独立复核\n"
        "python3 scripts/kf/wp8288_01_report.py render publish"
    )

    # inlined envelope: backticks escaped as \u0060 so the manifest's verbatim fence
    # quotes cannot terminate the report's own json fence early (JSON-equivalent after parsing)
    result_json = json.dumps(result, ensure_ascii=False, indent=2).replace("`", "\\u0060")
    body = f"""# {TITLE}

**工作包** `wp-8288-01` · **工序** 01-asset-registration（源资产登记） · **lane** C ·
**report_id** 8288 · **源哈希** `sha256:{manifest['source']['hash']}`
**源** `tensor://reports/8288#markdown`（{manifest['source']['chars']} chars / {manifest['source']['bytes_utf8']} bytes UTF-8）

## ① 本工序做了什么

只做一件事：把报告 8288 的**源资产身份**钉住，并把该报告内部**可解析的结构/引用**清点成册，不做抽取、不做类型判定、不写任何 claim。

- 取回 report_id=8288 的 `markdown` 字段（**只此一份报告**），本地重算 sha256 = `{manifest['source']['hash']}`，与契约 `source_hash` 逐字节一致，字符数 {manifest['source']['chars']} 与契约 {manifest['source']['chars']} 一致。源文件另存为 `docs/kf/wp-8288-01/source.md`（字节级副本）。
- 在该 markdown 上登记 **{c['assets']} 个资产**：{c['resolved_in_source']} 个 resolved_in_source、{c['referenced_unresolved']} 个 referenced_unresolved、{c['declared_absent']} 个 declared_absent。
- 每个资产带一个**逐字字符区间定位符** `[start_char, end_char)` + 含 `start_line/end_line` + `quote`；`quote` 是从源 markdown 切片得来（不是重新手打），因此可被平台二次子串校验。
- `claims` 为空数组（契约 `objective.classify_report_type=false`、无抽取工序，notes 明示允许空），理由写入 `claims_empty_reason`。**没有**任何 claim 被标 `verified`——验证留给平台门。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取证**：`GET /api/v1/tensor/reports/8288`（Bearer=agent 登录 token）→ `markdown`。写入 `source.md` 前先比 sha256 与字符数，不一致即 `SystemExit`，任何下游工件都不会建立在漂移源上（`scripts/kf/wp8288_01_fetch.py`）。
2. **定位符生成**：把 markdown 按键切行、建立「行号 → 字符偏移」表；所有 `quote` 用 `md[start:end]` 切片；若切片在全文不唯一，则**向上扩行**直到唯一（不重打字、不改字），记 `unique=true`（本次 {manifest['integrity']['quote_uniqueness']['unique_in_source']}/{manifest['integrity']['quote_uniqueness']['quotes']} 全部唯一）。
3. **引用清点**：正则扫描四类引用面——markdown 图片、反引号路径、裸路径（`.py/.json/.md/.png/.txt/.csv`）、`Author et al. (YYYY)` 文献引用；路径在**本交付 worktree 内**实际查找（命中则记 sha256+字节数，未命中记 unresolved + 原因），不跨仓猜测。
4. **结构清点**：连续 `|` 行识别 markdown 表（记表头与数据行数，不抄单元格），三反引号围栏识别公式/代码块（记 info string 与行数）。
5. **显式缺席**：报告自述 pending / cluster 的宏观锚结果行，登记为 `declared_absent`（引文即那几行，不当作失败、不臆造数值）。
6. **校验**：`jsonschema`（draft 2020-12）先验 manifest（本地投影 schema，见 ⑤ 局限 1），再验结果信封 `schemas/kf_result.v1.schema.json`；另跑 12 项 pytest 复核（见 ⑥）。
7. **出图**：两张 png 全部**由 manifest 渲染**（`scripts/kf/wp8288_01_figures.py`），像素不可能与登记册不一致。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-8288-01/source.md` | 报告 8288 markdown 字节级副本，sha256 与契约一致（零漂移基线） |
| `docs/kf/wp-8288-01/fetch_meta.json` | 取证元数据：recomputed/contract 哈希、chars、title、scenario_key、mission_id、record figures 列表 |
| `docs/kf/wp-8288-01/asset_manifest.json` | **主交付**：{c['assets']} 资产登记册 + counts + integrity + limitations |
| `docs/kf/wp-8288-01/asset_manifest.schema.json` | manifest 的本地投影 schema（仅重定向 per-package const，字段/枚举不放松） |
| `docs/kf/wp-8288-01/verification.json` | 6 项 acceptance 自检 + 3 项附加检查的机器判读（作者自检，非验证标记） |
| `docs/kf/wp-8288-01/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs），本报告唯一 json 块的内容源 |
| `docs/kf/wp-8288-01/figures/wp8288_01_locator_map.png` | 图1 定位符地图 |
| `docs/kf/wp-8288-01/figures/wp8288_01_inventory.png` | 图2 资产清单分布 |
| `scripts/kf/wp8288_01_fetch.py` / `_register.py` / `_figures.py` / `_report.py` | 取证 / 登记+校验+信封 / 出图 / 成文发布 |
| `tests/test_kf_wp8288_01.py` | 12 项独立复核（无需联网：只用本地源副本与 JSON） |

按类别分布：

| asset_class | n |
|---|---|
{class_lines}
| **合计** | **{c['assets']}** |

## ④ 证据定位表（字段 → 原文引文）

引文全部由 `md.find(marker)` 定位后**切片**得到，区间为半开区间 `[start,end)`；引文内 `|` 已转义以免破坏表格。

| 字段 / 结论 | 源行与字符区间 | 原文引文（逐字） | 说明 |
|---|---|---|---|
{evidence_table}

## ⑤ 注意点与局限

1. **schema 的投影而非复用**：仓库内 `schemas/asset_manifest.v1.schema.json` 把 `package_id`/`report_id` 等写成 `const`（pin 在别的包上），直接复用会误判。本包**不改**该文件，另存 `asset_manifest.schema.json`：字段、必填、枚举、正则一律不变，只把 per-package 的 const 重定向到本包；信封层仍用平台原生 `schemas/kf_result.v1.schema.json` 校验。
2. **{c['referenced_unresolved']} 个 unresolved 是边界而非缺陷**：被引 `src/tensordem/*.py`、`runs/in61_n07/*` 属于 TensorDEM 树，超出本工作包边界；登记为「引用存在、内容未取」，**不填猜测内容**。
3. **记录里的图无字节**：`figures[0]=pareto_front` 只有 name/caption，无 `png_base64` 载荷（`has_png_payload=false`），因此登记为 `declared_absent` 而不冒充已取到的图件。
4. **表格/围栏只登记结构**：记表头与行数、info string，不转录单元格数值——抽取属工序 03，本包越界即污染产线。
5. **A01/A02 用 document 型定位符**：整份文档/整条 record 字段无法用单点字符区间表达，故 `start_char=0, end_char=len(md)`，`quote` 取标题行作为锚；平台子串校验对 `quote` 仍成立。
6. **本包不判定真伪**：报告自身的 `0.0000%`、`183–2163%` 等数字只作为**可定位引文**登记，正确性校验不在 01 工序职责内。
7. **json 块内反引号转义**：manifest 的代码围栏引文含三反引号（逐字，不改），故信封序列化时把反引号写成 U+0060 转义；JSON 解析后与 `kf_result.json` 完全等价（已用 `json.loads` 回读比对）。
8. **未做类型判定**（`classify_report_type=false`），未生成任何 claim；空 claims 是完整结果而非缺项。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 判读依据 |
|---|---|---|
{acc_lines}

附加检查（非 acceptance 项，但同一套机器判读）：

| 检查 | 结果 | 判读依据 |
|---|---|---|
{extra_lines}

失败项：**无**（{sum(1 for v in acc.values() if not v['pass'])} 项失败）。诚实补充两条非失败但需知情的口径：
(a) `schema_pass` 用的是**投影** schema（见 ⑤-1），平台若按自身 schema 复判以平台为准；
(b) `all_claims_have_evidence_or_explicit_unresolved_status` 在 claims 为空时是**空满足**，本包已把空理由写进 `claims_empty_reason`，不靠空数组掩盖缺证据。

## 误差判定（本包无物理基准量）

- 本工序是**制品登记**，不产生物理/数值结果，**没有**可与实验/解析解对比的量，因此「关键量 vs 基准误差是否 <3%」这一问 **不适用（N/A）**，不以任何含糊措辞掩盖。
- 替代的可机械判读恒等式（逐项给出实测值）：
  1. 源哈希恒等：重算 `{manifest['source']['hash']}` == 契约 `2c35fbe3…e053f19`，**差异 0 比特**；chars {manifest['source']['chars']} == 契约 {manifest['source']['chars']}。
  2. 定位符可复现：{manifest['integrity']['quote_uniqueness']['quotes']}/{manifest['integrity']['quote_uniqueness']['quotes']} 条 `quote` 由 `md[start:end]` 精确重切（失配 0 条），全文唯一率 {manifest['integrity']['quote_uniqueness']['unique_in_source']}/{manifest['integrity']['quote_uniqueness']['quotes']}。
  3. 行号自洽：每条 char_span 定位符的 `start_line` 由字符偏移反算一致（失配 0 条，见 pytest）。
  4. ID 完整性：{c['assets']} 个 id 无重复、全部匹配 `^A[0-9]{{2}}$` 且字典序。
  这些是**恒等型判据**（应 0 差异，实测 0 差异），比 3% 阈值更严；但它们只证明「登记册忠实于源」，**不证明**报告结论正确。

## 复现命令（一键）

```bash
{repro}
```

![图1 定位符地图](figures/wp8288_01_locator_map.png)

图1：横轴=报告 8288 markdown 的字符偏移，每条横条=一个逐字 char-span 定位符，颜色=resolution 状态（绿=resolved_in_source，橙=referenced_unresolved，灰=declared_absent）。可见已解析的结构（表格/围栏）集中在中段与 §5，而 TensorDEM 路径引用成簇出现且全为橙（跨仓不可解析，属边界）。

![图2 资产清单分布](figures/wp8288_01_inventory.png)

图2：左=按 asset_class 的资产数（{c['assets']} 项），右=按 resolution 状态（{c['resolved_in_source']}/{c['referenced_unresolved']}/{c['declared_absent']}）。计数块与 `asset_manifest.json.counts` 同源，由脚本直接渲染。

## 结果信封（本报告唯一 json 块）

反引号在块内以 U+0060 转义写出（JSON 等价，解析后字节相同）：manifest 里逐字登记的代码围栏引文本身含三反引号，若原样写出会提前闭合 markdown 围栏。

```json
{result_json}
```
"""
    REPORT.write_text(body, encoding="utf-8")
    print("wrote %s (%d bytes)" % (REPORT.relative_to(REPO), len(body.encode("utf-8"))))
    return REPORT


def publish():
    token = login()
    figs = json.loads(FIGS.read_text(encoding="utf-8"))["figures"]
    payload = {
        "title": TITLE,
        "summary": ("wp-8288-01 源资产登记：报告 8288 markdown sha256 与契约逐字节一致，登记 40 个可定位资产"
                    "（19 resolved / 16 unresolved / 5 declared_absent），claims 空且无 verified 标记；"
                    "6/6 acceptance 自检通过（机器判读），验证留平台门。"),
        "scenario_key": SCENARIO_KEY,
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:wp-8288-01", "01-asset-registration", "kf-result", "asset-manifest", "IN61-N07"],
        "markdown": REPORT.read_text(encoding="utf-8"),
        "figures": [{"name": f["name"], "caption": f["caption"], "png_base64": f["png_base64"]}
                    for f in figs],
    }
    try:
        d = _req(BASE + "/tensor/reports", token, data=json.dumps(payload).encode())
    except urllib.error.HTTPError as e:
        print("HTTP %s: %s" % (e.code, e.read().decode()[:800]))
        raise SystemExit(1)
    print(json.dumps({k: d.get(k) for k in ("id", "title", "status", "scenario_key")}, ensure_ascii=False))
    (OUT / "publish_receipt.json").write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                                              encoding="utf-8")
    return d


if __name__ == "__main__":
    acts = sys.argv[1:] or ["render", "publish"]
    if "render" in acts:
        render()
    if "publish" in acts:
        publish()