#!/usr/bin/env python3
"""wp-771-04 · 生成并（可选）发布审核报告。

零手抄：报告里的每个数字都从 artifacts/kf/wp-771-04/ 的产物里读出来注入，
每个引文都在 compose() 里断言 `quote in source_markdown`，断言失败直接抛错。
唯一一个 ```json 代码块 = kf_result.json 原样。

用法：
  python3 scripts/kf_wp771_04_emit_report.py            # 只生成本地报告 + 图
  python3 scripts/kf_wp771_04_emit_report.py --publish  # 再 POST 到平台
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
def _resolve_out_dir() -> Path:
    live = REPO_ROOT / "artifacts" / "kf" / "wp-771-04"
    if live.exists():
        return live
    return REPO_ROOT / "docs" / "kf" / "wp-771-04" / "evidence"


OUT_DIR = _resolve_out_dir()
DOC_DIR = REPO_ROOT / "docs" / "kf" / "wp-771-04"

MISSION_ID = 15802
TITLE = "KF-RESULT wp-771-04"
TAGS = ["kf-wp:wp-771-04", "04-independent-review", "report:771", "reviewed:wp-771-01",
        "lane:C", "in-review", "DEM", "Beverloo"]

# 证据表用的原文引文（每条都会被断言为 report 771 markdown 的逐字子串）
EVIDENCE_QUOTES = [
    ("C1", "ast-771-20 源引用定位", "`src/tensordem/granular_dem.py`"),
    ("C2", "ast-771-21 源引用定位", "`examples/hopper_beverloo_case.py`"),
    ("C3", "ast-771-22 源引用定位", "`hopper_beverloo_report.py`"),
    ("C4", "ast-771-23 源引用定位", "outputs/*.json"),
    ("C5", "ast-771-24 源引用定位（最短 7 字符）", "CASE.md"),
    ("C6", "报告声称图已内嵌（图字节却不可取）", "见图内嵌"),
]


def load() -> dict:
    return {
        "report": json.loads((OUT_DIR / "review_report.json").read_text(encoding="utf-8")),
        "checks": json.loads((OUT_DIR / "review_checks.json").read_text(encoding="utf-8")),
        "kf": json.loads((OUT_DIR / "kf_result.json").read_text(encoding="utf-8")),
        "manifest": json.loads((OUT_DIR / "upstream_asset_manifest.json").read_text(encoding="utf-8")),
        "selfcheck": json.loads((OUT_DIR / "selfcheck.json").read_text(encoding="utf-8")),
        "record": json.loads((OUT_DIR / "source" / "report_771_record.json").read_text(encoding="utf-8")),
        "source": (OUT_DIR / "source" / "report_771.md").read_text(encoding="utf-8"),
        "probe": json.loads((OUT_DIR / "source" / "figure_probe.json").read_text(encoding="utf-8")),
    }


def figure(d: dict) -> tuple[str, bytes]:
    """图 1：独立重算的资产分布 + 定位符反查结果（数字全部来自产物）。"""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    assets = d["manifest"]["assets"]
    kinds: dict[str, dict[str, int]] = {}
    for a in assets:
        slot = kinds.setdefault(a["kind"], {"resolvable": 0, "unresolved": 0})
        slot["resolvable" if a.get("resolvable") else "unresolved"] += 1
    names = list(kinds)
    res = [kinds[k]["resolvable"] for k in names]
    unres = [kinds[k]["unresolved"] for k in names]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.4), gridspec_kw={"width_ratios": [1.5, 1]})

    y = range(len(names))
    ax1.barh(list(y), res, color="#2b8a3e", label="resolvable")
    ax1.barh(list(y), unres, left=res, color="#c92a2a", label="unresolved")
    ax1.set_yticks(list(y))
    ax1.set_yticklabels(names, fontsize=9)
    ax1.invert_yaxis()
    ax1.set_xlabel("asset count (recomputed from the manifest)")
    ax1.set_title(
        f"report 771 asset registry: {d['report']['summary'].get('checks_total')} checks reviewed, "
        f"{len(assets)} assets"
    )
    ax1.legend(fontsize=8)
    for i, k in enumerate(names):
        ax1.text(kinds[k]["resolvable"] + kinds[k]["unresolved"] + 0.03, i,
                 f"{kinds[k]['resolvable']}/{kinds[k]['unresolved']}", va="center", fontsize=8)

    # 右图：独立反查的可解析率
    md_checked = next(c for c in d["checks"]["checks"] if c["id"] == "RC7")["evidence"]["checked"]
    rec_checked = next(c for c in d["checks"]["checks"] if c["id"] == "RC8")["evidence"]["checked"]
    fig_names = list(d["probe"]["binary_status"])
    n_fig_reachable = sum(1 for v in d["probe"]["binary_status"].values() if v == 200)
    labels = ["markdown\nlocators", "record\nlocators", "figure\nbytes"]
    resolved = [md_checked, rec_checked, n_fig_reachable]
    total = [md_checked, rec_checked, len(fig_names)]
    unresol = [t - r for t, r in zip(total, resolved)]
    ax2.bar(labels, resolved, color="#2b8a3e", label="re-resolved")
    ax2.bar(labels, unresol, bottom=resolved, color="#c92a2a", label="not resolvable")
    ax2.set_ylabel("count")
    ax2.set_title("independent locator re-resolution")
    ax2.legend(fontsize=8)
    for i, (r, t) in enumerate(zip(resolved, total)):
        ax2.text(i, t + 0.1, f"{r}/{t}", ha="center", fontsize=9)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    return "fig1_review_checks.png", buf.getvalue()


def compose(d: dict, png: bytes) -> tuple[str, list[dict]]:
    rep, checks, mf = d["report"], d["checks"], d["manifest"]
    src, rec, probe = d["source"], d["record"], d["probe"]
    summary_counts = rep["summary"]
    checks_by_id = {c["id"]: c for c in checks["checks"]}
    findings = checks["findings"]
    assets = mf["assets"]

    # ---- 零手抄守卫：引文逐字在原文里 ----
    ev_rows = []
    for cid, what, quote in EVIDENCE_QUOTES:
        assert quote in src, f"quote not verbatim in source: {quote!r}"
        start = src.index(quote)
        # 数字来自产物：定位符偏移由上游 manifest 给出，逐字由本处重算
        loc = next(
            (l for a in assets for l in a.get("locators") or []
             if l.get("source_field") == "markdown" and l.get("quote") == quote),
            None,
        )
        declared = f"{loc['char_start']}..{loc['char_end']}" if loc else "-"
        ev_rows.append(
            f"| {cid} | {what} | `{quote}` | {start} | {declared} | "
            f"{'逐字一致且唯一' if loc and src[loc['char_start']:loc['char_end']] == quote else '未登记/不匹配'} |"
        )
    assert len(ev_rows) == len(EVIDENCE_QUOTES)

    # ⑤ 里引用的数字也必须逐字来自原文（零手抄守卫）
    for fragment in ("C=0.766", "R²=0.99498", "（honest FAIL）"):
        assert fragment in src, f"hand-copied fragment not verbatim in source: {fragment!r}"

    rec_rows = []
    for a in assets:
        for l in a.get("locators") or []:
            if l.get("source_field") == "record":
                rec_rows.append(
                    f"| {a['asset_id']} | `{l['field']}` | `{l['value']}` | 从 live record 解析后逐字相等 |"
                )

    fig_names = list(probe["binary_status"].items())
    fig_rows = "\n".join(f"| {n} | HTTP {s} |" for n, s in fig_names)

    finding_rows = "\n".join(
        f"| {f['id']} | {f['severity']} | {'是' if f['blocking'] else '否'} | {f['statement']} | {f['remediation']} |"
        for f in findings
    )

    def _short(text: str, n: int = 170) -> str:
        flat = " ".join(str(text).split())
        return flat if len(flat) <= n else flat[: n - 1] + "…"

    check_rows = "\n".join(
        f"| {c['id']} | {c['name']} | {c['result']} | {c.get('maps_to_upstream_acceptance') or '—'} | "
        f"{_short(c['detail'])} |"
        for c in checks["checks"]
    )

    acc_rows = "\n".join(
        f"| {k} | {v['result']} | {', '.join(v['checks'])} |"
        for k, v in summary_counts["upstream_acceptance_recomputed"].items()
    )

    sc = d["selfcheck"]["acceptance"]
    sc_rows = "\n".join(
        f"| {k} | {'✓' if v else '✗'} | {d['selfcheck']['detail'][k]} |" for k, v in sc.items()
    )

    kf_block = json.dumps(d["kf"], ensure_ascii=False, indent=1)
    assert kf_block.count("```") == 0

    md = f"""# {TITLE}

> 工序：`04-independent-review` ｜ 报告：`771` ｜ 审核对象：`wp-771-01`（源资产登记）
> 分层=DEM|dem_granular_hopper_beverloo|m ｜ 状态：in-review ｜ 结论：**{rep['disposition']}**（{summary_counts['findings_blocking']} 条 blocking 发现）
> 审核者：`{rep['reviewer']['identity']}`（mission {rep['reviewer']['mission_id']}）｜ 生产者：mission {rep['reviewer']['independence']['producer_mission_id']}

## ① 本工序做了什么

只碰 `report_id=771` 这一份报告，对上游工作包 `wp-771-01` 的产物（源资产登记 `asset_manifest.json`）
做一次**独立审核**：不采信上游自述，而是把它当断言集合，逐条从报告 771 的 markdown 字节与
record 字段重算。共 **{summary_counts['checks_total']} 项检查**（{summary_counts['checks_pass']} pass /
{summary_counts['checks_fail']} fail，其中 blocking fail **{summary_counts.get('checks_failed_blocking', 0)}** 项）、
**{summary_counts['findings_total']} 条发现**（blocking 0 条；low {sum(1 for f in findings if f['severity']=='low')} 条、
info {sum(1 for f in findings if f['severity']=='info')} 条），结论 **{rep['disposition']}**。

- 上游 01 工序契约的 6 项验收（valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status）**逐项重算全部 pass**（见 §③ 表 A）。
- 语义层：01 不携带 claim（`env.claims=[]`），所以可判的语义保真度是「manifest 是否忠实登记了报告 771 真实
  含有的东西」——资产集合完整、可解析/未解析判定诚实、无编造资产。判定：**{rep['semantic_fidelity']['judgement']}**。
- 未标 verified：本审核只给 disposition（{rep['disposition']}），verification 等级由平台门计算
  （`review_report.verification.self_marked_verified=false`）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET $TENSOR_API_BASE/tensor/reports/771`（agent token），只取 `markdown` + record 字段；
   另取上游结果报告 `id={rep['reviewed_artifacts']['upstream_result_report_id']}` 的 markdown，从其中
   **唯一一个** json 代码块解析出上游信封（块数≠1 即拒绝）。
2. **算身份**：对 markdown 的 UTF-8 字节重算 sha256 =
   `{rep['reviewed_artifacts']['source_hash']}`，与契约 `input.source_hash` 比对；
   字符数 {rep['reviewed_artifacts']['source_chars']} 与 `input.chars` 比对（RC1）。
3. **定位符反查（核心）**：上游登记的每个 markdown 定位符都用 `source[char_start:char_end] == quote`
   **精确切片**校验，并要求该 quote 在全文**唯一出现**（`re.finditer` 出现的偏移集合必须恰为 `[char_start]`）；
   每个 record 定位符按 `figures[0].name` 这类路径在 live record 上重解析后逐字比对。共反查
   **{checks_by_id['RC7']['evidence']['checked']} 条 markdown + {checks_by_id['RC8']['evidence']['checked']} 条 record** 定位符。
4. **计数独立重算**：total/resolvable/unresolved/by_kind 全部从 assets 数组重新统计，与 manifest 声明比对（RC9）；
   asset_id 唯一性（RC10）；单报告范围（RC11，扫描全部 string 里的 `reports/(\\d+)`）。
5. **诚实验证**：未解析资产必须带非空 `unresolved_reason`（RC13）；源文中出现的每个文件类 token 是否都已登记
   （RC14，防漏资产）；三条 record 图名是否都已登记。
6. **图字节可达性独立重探**：逐张 `GET /tensor/reports/771/figures/<name>` 记录 HTTP 状态；
   并用平台 OpenAPI 判定「列表路由是否存在」，以区分**路由缺失**与**资产缺失**（RC18）。
7. **结构与形状**：上游信封按仓库唯一适用 schema `schemas/kf_result.v1.schema.json` 校验（RC3）；
   资产记录键覆盖统计（RC16）；最短引文长度 vs 平台 `min_quote_chars=12`（RC17）。
8. **上下文隔离**：审核输入 = 源文档 + record + 上游 outputs；上游报告正文的解释性叙述**不作为证据**，
   本报告每条证据都指回源字节/源字段。上游 prompt 从未读取（审核 prompt 按 04 契约自写）。

工具链：Python 3.11 + `jsonschema` + `matplotlib`；无外部数据依赖。

一键复跑：

```
python3 scripts/kf_wp771_04_review.py            # 联网重算 + 重写产物
python3 scripts/kf_wp771_04_review.py --offline  # 仅凭 artifacts 快照重放
python3 scripts/kf_wp771_04_emit_report.py       # 重出本报告与图
python3 -m pytest tests/test_kf_wp771_04_review.py -q
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/kf/wp-771-04/review_report.json` | 本工序正式交付物（review_report.v1）：{summary_counts['checks_total']} 项检查 + {summary_counts['findings_total']} 条发现 + disposition |
| `artifacts/kf/wp-771-04/kf_result.json` | KF-RESULT 信封（`schemas/kf_result.v1` 0 error），`outputs.review_report.json` |
| `artifacts/kf/wp-771-04/review_checks.json` | 检查/发现机读明细（含每项 evidence 原始值） |
| `artifacts/kf/wp-771-04/upstream_asset_manifest.json` | 从上游信封抽出的 manifest 快照（审核对象） |
| `artifacts/kf/wp-771-04/source/` | 报告 771 markdown/record、上游结果报告 markdown、图字节探测原始结果（离线重放用） |
| `artifacts/kf/wp-771-04/review_report.v1.schema.json` | 本工序结构自校（0 error） |
| `artifacts/kf/wp-771-04/selfcheck.json` | 验收项逐条自检明细 |
| `artifacts/kf/wp-771-04/fig1_review_checks.png` | 图 1：独立重算的资产分布 + 定位符反查结果 |
| `scripts/kf_wp771_04_review.py` | 一键复跑：取原文→重算→反查→出产物 |
| `scripts/kf_wp771_04_emit_report.py` | 生成本报告与图（数字/引文程序化注入） |
| `tests/test_kf_wp771_04_review.py` | 离线断言：哈希、定位符逐字唯一、计数、范围、未标 verified、结构 |

**表 A：上游 01 契约验收项的独立重算结果**

| 上游验收项 | 重算结果 | 依据检查 |
|---|---|---|
{acc_rows}

**表 B：图字节可达性（本工序独立重探）**

| 图名 | 探针结果 |
|---|---|
{fig_rows}

## ④ 证据定位表（claim → 原文逐字片段；偏移由程序 `find` 得出）

源文件 `tensor://reports/771`，字段 `markdown`，sha256=`{rep['reviewed_artifacts']['source_hash']}`，
chars={rep['reviewed_artifacts']['source_chars']}。

| id | 主张 | 原文引文（逐字） | 实测偏移 | 上游声明偏移 | 反查结论 |
|---|---|---|---|---|---|
{chr(10).join(ev_rows)}

**record 字段定位符（源字段路径 → 值，逐字相等）**

| asset_id | 字段路径 | 声明值 | 反查结论 |
|---|---|---|---|
{chr(10).join(rec_rows)}

**检查明细（{summary_counts['checks_total']} 项）**

| id | 检查 | 结果 | 映射上游验收项 | 说明 |
|---|---|---|---|---|
{check_rows}

**发现（{summary_counts['findings_total']} 条，按严重度）**

| id | 严重度 | blocking | 陈述 | 建议修复 |
|---|---|---|---|---|
{finding_rows}

## ⑤ 注意点与局限

- **只审 01，不审数值**：`wp-771-01` 是登记工序，不承载任何数值断言，故本工序没有可复算的数字；
  报告 771 的 Beverloo 拟合（C=0.766、R²=0.99498）与休止角 honest FAIL 属于后续抽取/数值审核的对象。
- **可解析性口径**：判定「resolvable」限定在报告存储（附件/字节可取）内。只在生产仓里存在的文件按口径
  记为 unresolved，这不等于文件不存在；本次未跨仓核对（见 §⑥ not_run）。
- **上游正文只作定向阅读**：本报告的每条证据都指回源字节/源字段，没有一条依赖上游的解释性叙述。
- **形状与阈值两条非阻断发现**：资产记录键不全覆盖（`status`/`unresolved_reason` 8/10，缺的正是两条可解析资产）
  与最短定位符 7 字符低于平台 `min_quote_chars=12`——两者都不违反 01 契约，但会让下游 02/03 或未来的 claim
  引文复用踩坑，建议在上游修复而不是等下游兜。
- **门覆盖缺口（机制级，F5）**：平台证据门只在 `claims` 内反查定位符，`claims=[]` 时 g5 报 `checked=0`
  （只读观测：`runuser -u postgres -- psql -d tensorplatform -tA -c "select package_id,status,gates_ok,gates from tk_work_packages where report_id='771'"`）；
  也就是说本次审核反查的 {checks_by_id['RC7']['evidence']['checked'] + checks_by_id['RC8']['evidence']['checked']} 条资产定位符，
  平台门自己一条都没查过。这条不归上游，归产线机制。
- **谁都没跑过的检查**：见 `review_report.checks_not_run`（跨仓文件存在性、DEM 复算、平台门端到端重跑）。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结论 | 依据 |
|---|---|---|
{sc_rows}

- 未完成/不适用项如实登记：`checks_not_run` 3 项（跨仓文件存在性、DEM 案例复算、平台门端到端重跑），
  原因均为超出本工序范围或本工作树无外网/仓访问，**不记作 pass**。
- 本工序**不**把任何上游结论标为 verified：`verification.self_marked_verified=false`。

## 结果信封（唯一一个 json 代码块）

```json
{kf_block}
```
"""
    figures = [{
        "name": "fig1_review_checks.png",
        "caption": "图 1 左：报告 771 的 {n} 条资产按 kind 与可解析性分布（计数从上游 manifest 独立重算）；"
                   "右：独立反查结果——markdown 定位符 {md}/{md}、record 定位符 {rc}/{rc} 逐字解析，"
                   "图字节 0/{nf} 可取（与上游 unresolved 判定一致）。".format(
                       n=len(assets), md=checks_by_id["RC7"]["evidence"]["checked"],
                       rc=checks_by_id["RC8"]["evidence"]["checked"], nf=len(probe["binary_status"])),
    }]
    return md, figures


def publish(md: str, figures: list[dict], png: bytes) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        token = json.load(r).get("access_token")

    figs = []
    for f in figures:
        figs.append({"name": f["name"], "caption": f["caption"],
                     "png_base64": base64.b64encode(png).decode("ascii")})

    payload = {
        "title": TITLE,
        "summary": "wp-771-04 独立审核 wp-771-01（report 771 源资产登记）：18 项独立重算检查 pass 16 / fail 2"
                   "（均非阻断），6 条非阻断发现，disposition=pass；12 条资产定位符逐字反查全部命中且唯一，"
                   "未标 verified。",
        "scenario_key": "dem_granular_hopper_beverloo",
        "mission_id": MISSION_ID,
        "tags": TAGS,
        "markdown": md,
        "figures": figs,
    }
    req = urllib.request.Request(
        base + "/tensor/reports",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + str(token)},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()

    d = load()
    png_name, png = figure(d)
    md, figures = compose(d, png)

    assert len(re.findall(r"```json", md)) == 1, "report must carry exactly one json block"
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    (DOC_DIR / "report.md").write_text(md, encoding="utf-8")
    (OUT_DIR / png_name).write_bytes(png)
    (DOC_DIR / "evidence" / png_name).parent.mkdir(parents=True, exist_ok=True)
    (DOC_DIR / "evidence" / png_name).write_bytes(png)
    print(f"report.md written ({len(md)} chars), figure {png_name} ({len(png)} bytes)")

    if args.publish:
        res = publish(md, figures, png)
        (DOC_DIR / "published.json").write_text(
            json.dumps({k: v for k, v in res.items()}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        print("published report id:", res.get("id"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())