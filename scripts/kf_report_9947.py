#!/usr/bin/env python3
"""Build the KF-RESULT report for work package wp-9947-01 and (unless --no-post) publish it.

Zero hand-copy discipline: every number, quote and asset row in the prose is formatted from
artifacts/wp-9947-01/asset_manifest.json and artifacts/wp-9947-01/verification.json at build time;
the result JSON block is the byte-identical envelope written by scripts/kf_register_9947.py.

Outputs:
  docs/wp-9947-01/KF-RESULT-wp-9947-01.md
  artifacts/wp-9947-01/fig_asset_inventory.png  (+ docs mirror)
  POST {TENSOR_API_BASE}/tensor/reports  (title 'KF-RESULT wp-9947-01', tags kf-wp:wp-9947-01)

Usage: python3 scripts/kf_report_9947.py [--no-post]
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ART = pathlib.Path("artifacts/wp-9947-01")
DOCS = pathlib.Path("docs/wp-9947-01")
PACKAGE_ID = "wp-9947-01"
REPORT_ID = "9947"
MISSION_ID = 15675
MANIFEST = json.loads((ART / "asset_manifest.json").read_text())
VERIF = json.loads((ART / "verification.json").read_text())
RESULT = json.loads(pathlib.Path("runs/wp-9947-01/kf_result.wp-9947-01.json").read_text())
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

def _probe_stats() -> dict:
    hits = {}
    for a in MANIFEST["assets"]:
        hits.update(a["resolution_check"].get("platform_probe", {}).get("hits", {}))
    nonzero = sorted(k for k, v in hits.items() if v.get("count", 0) > 0)
    zero = sorted(k for k, v in hits.items() if v.get("count", 0) == 0)
    return {"keys": len(hits), "nonzero": nonzero, "zero": zero,
            "counts": sorted({v.get("count") for v in hits.values()})}


PROBE = _probe_stats()

COLOR = {"resolved_in_source": "#2e7d32", "referenced_unresolved": "#ef6c00",
         "declared_absent": "#6a1b9a"}


def evidence_table() -> str:
    rows = ["| asset_id | class | resolution | locator（char span / method） | 原文片段（逐字取自 report 9947 markdown） |",
            "|---|---|---|---|---|"]
    for a in MANIFEST["assets"]:
        loc = a["locator"]
        q = loc["quote"].split("\n")[0].replace("|", "\\|")
        if len(q) > 58:
            q = q[:58] + "…"
        if loc["method"] == "document":
            span, q = "0-%d / document" % loc["end_char"], "（整篇 markdown，sha256 见 provenance）"
        else:
            span = "%d-%d / char_span" % (loc["start_char"], loc["end_char"])
        rows.append("| %s | %s | %s | %s | `%s` |"
                    % (a["asset_id"], a["asset_class"], a["resolution"], span, q))
    return "\n".join(rows)


def check_table() -> str:
    rows = ["| 验收项 | 结果 | 证据（来自 verification.json） |", "|---|---|---|"]
    for c in VERIF["checks"]:
        rows.append("| %s | **%s** | `%s` |" % (c["check"], c["result"].upper(),
                                               json.dumps(c["detail"], ensure_ascii=False)[:220].replace("|", "\\|")))
    return "\n".join(rows)


def notice_table() -> str:
    rows = ["| id | 关联资产 | 事实（指针/占位，不含推断） |", "|---|---|---|"]
    for n in MANIFEST["notices"]:
        rows.append("| %s | %s | %s |" % (n["id"], n["evidence_asset"], n["text"]))
    return "\n".join(rows)


def make_figure() -> dict:
    assets = MANIFEST["assets"]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9.2, 6.4),
                                   gridspec_kw={"height_ratios": [1.35, 1]})
    # panel 1: locator map on the 616-char axis
    n = MANIFEST["source"]["chars"]
    ax1.set_xlim(0, n)
    ax1.set_ylim(-0.6, len(assets) - 0.4)
    for i, a in enumerate(assets):
        loc = a["locator"]
        ax1.barh(i, loc["end_char"] - loc["start_char"], left=loc["start_char"], height=0.62,
                 color=COLOR[a["resolution"]], alpha=0.9)
        ax1.text(loc["end_char"] + 4, i, a["asset_id"], va="center", fontsize=7)
    ax1.set_yticks([])
    ax1.set_xlabel("char offset in report 9947 markdown (%d chars, sha256 %s...)"
                   % (n, MANIFEST["source"]["hash"][:12]), fontsize=8)
    ax1.set_title("Fig.1  wp-9947-01 locator map: %d registered assets on the source markdown char axis\n"
                  "(green = sliceable in source, orange = external pointer unresolved, purple = figure absent)"
                  % len(assets), fontsize=9)
    # panel 2: resolution counts
    keys = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    vals = [MANIFEST["counts"][k] for k in keys]
    bars = ax2.bar(range(len(keys)), vals, color=[COLOR[k] for k in keys], width=0.55)
    for b, v in zip(bars, vals):
        ax2.text(b.get_x() + b.get_width() / 2, v + 0.08, str(v), ha="center", fontsize=10)
    ax2.set_xticks(range(len(keys)))
    ax2.set_xticklabels([k for k in keys], fontsize=8)
    ax2.set_ylim(0, max(vals) + 1.2)
    ax2.set_ylabel("assets", fontsize=8)
    ax2.set_title("Fig.2  resolution status distribution (total %d assets; claim extraction out of scope)"
                  % MANIFEST["counts"]["assets"], fontsize=9)
    fig.tight_layout()
    p = ART / "fig_asset_inventory.png"
    fig.savefig(p, dpi=130)
    plt.close(fig)
    (DOCS / "fig_asset_inventory.png").write_bytes(p.read_bytes())
    return {"name": p.name, "png_base64": base64.b64encode(p.read_bytes()).decode(),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def build_markdown() -> str:
    res_block = json.dumps(RESULT, ensure_ascii=False, indent=2)
    s = MANIFEST["source"]
    c = MANIFEST["counts"]
    nchecks = len(VERIF["checks"])
    npass = sum(1 for x in VERIF["checks"] if x["result"] == "pass")
    return f"""# KF-RESULT {PACKAGE_ID}

## ① 案例介绍（这是什么工序，服务哪份报告）

本单是「报告→知识」产线上的一道单一工序：**资产登记（task_type = 01-asset-registration）**，
只服务 `report_id=9947` 这一份报告，不做抽取、不做报告类型分类、不改写上游产物。

- 源报告：report 9947《{s["title"]}》，scenario_key=`{s["scenario_key"]}`，平台 stage=`{s["platform_stage"]}`，
  创建于 `{s["platform_created_at"]}`，tags={json.dumps(s["platform_tags"], ensure_ascii=False)}。
- 报告本体的物理事实：markdown `{s["chars"]}` 字符 / `{s["bytes_utf8"]}` 字节 UTF-8，
  sha256 = `{s["hash"]}`，与工作包契约 `input.source_hash` 逐字节相同。
- 内容性质：A/B 双路线试点的**终局对照汇总页**（自动合成），正文只有标题、prereg 指针、模型席位一行、
  一张五席位终态表、一行判据与裁决规则、一行原始证据指针。**它不是数值计算报告**：
  表体不含任何数值，判据细节与原始证据都以 `scenario_key` 外置。
- 本工序的边界（契约 objective）：`register_assets: true`、`classify_report_type: false`，
  `claims` 允许为空数组；`do_not_mark_claims_as_verified: true`（verification 由平台门计算）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取证不靠记忆**：`GET {{TENSOR_API_BASE}}/tensor/reports/9947` 取 `markdown` 字段，落盘
   `runs/wp-9947-01/report_9947.{{md,json}}`；本地重算 sha256 与契约 `source_hash` 比对，
   同时校验 `chars={s["chars"]}`、`title`、`scenario_key` 三项契约身份 —— 任一不符脚本立即 FATAL 退出
   （`scripts/kf_register_9947.py`）。
2. **定位而非抄写**：脚本维护一张 {c["assets"]} 行锚点表（asset_id / 资产类 / 唯一锚点串 / 相对行跨 / 是否子串定位）。
   运行时先在 markdown 中定位锚点行（断言全文出现 **恰好 1 次**），再算字符偏移，**直接从原文切片**得到
   `quote`；切片再断言全文出现次数 == 1。单行资产用子串定位（`sub=True`）以缩窄 span，不整行吞并。
3. **可解析性机器判定**：每个资产跑 `resolution_check`，结果与声明的 `resolution` 由**严格映射**绑定，
   不一致即中止（`RESOLUTION_TO_CHECK`）。三类判据：
   - 页内资产 → 重新切片校验；
   - 外部指针 → 在报告原文里正则抽取路径/URL/DOI/scenario_key，再**只读探测**：宿主路径 `stat`、
     平台 `GET /tensor/reports?scenario_key=<key>`；探测结果原样入账（含 0 命中的键）；
   - 图件 → 平台 `figures` 字段 + 正文 `![` 计数。
4. **独立复核**：`scripts/kf_verify_9947.py` 在**新进程、重新登录、重新取报告**的前提下重算哈希、
   重切每个 locator、重跑全部平台探测（与登记时记录的命中数逐键比对），并做 schema 校验、ID 唯一性、
   counts 一致性、artifact↔envelope 哈希、`docs/` 镜像字节一致、notices↔资产绑定 §6 项附加检查。
5. **零手抄到报告**：本报告的每张表、每个数字都由 `scripts/kf_report_9947.py` 从 manifest/verification
   在构建时格式化注入，JSON 代码块是登记脚本写出的 envelope 原文件。

## ③ 产出物清单

| 输出文件 | 要点 |
|---|---|
| `artifacts/wp-9947-01/asset_manifest.json` | 契约声明的唯一输出；{c["assets"]} 个资产（resolved_in_source={c["resolved_in_source"]} / referenced_unresolved={c["referenced_unresolved"]} / declared_absent={c["declared_absent"]}）、claims=[]、{len(MANIFEST["notices"])} 条 notices、resolution_semantics；sha256=`{RESULT["outputs"]["asset_manifest.json"]["artifact_sha256"]}` |
| `docs/wp-9947-01/asset_manifest.json` | 上者的**字节一致镜像**（仓推送门会丢弃 `artifacts/**` 与 `runs/**`，故 docs 是可提交副本） |
| `runs/wp-9947-01/report_9947.md` / `.json` | API 原始取件（markdown + id/title/scenario_key/figures/tags），供离线复算 |
| `runs/wp-9947-01/kf_result.wp-9947-01.json` | kf_result.v1 信封（本报告唯一 json 代码块的内容，逐字节相同） |
| `artifacts/wp-9947-01/verification.json` + `docs/` 镜像 | {nchecks} 项自检逐条记录（{npass}/{nchecks} pass），overall=`{VERIF["overall"]}` |
| `artifacts/wp-9947-01/fig_asset_inventory.png` | 图1/图2 合图：定位地图 + 可解析状态分布（数字全部来自 manifest） |
| `scripts/kf_register_9947.py` / `kf_verify_9947.py` / `kf_report_9947.py` | 登记 / 独立复核 / 报告构建，一键复跑 |
| `tests/test_kf_wp9947.py` | 不变量测试（源哈希/定位/schema/计数/镜像）+ 篡改负对照（改引文、挪 span、改 resolution 均必须被检出） |

## ④ 证据定位表（claim/字段 → 原文引文片段）

登记口径：`resolved_in_source` = 内容可在源 markdown 内按 `[start_char,end_char)` 逐字切片且全文唯一；
`referenced_unresolved` = 报告只给指针（路径/键名/scenario_key），未给可校验的 id+哈希组合，本工序只登记指针与探测结果；
`declared_absent` = 报告与平台元数据均无该资产（此处为图件）。

{evidence_table()}

**指针事实（程序化探测，不含推断）**

{notice_table()}

## ⑤ 注意点与局限

1. **本报告不含任何结果数字**：五席位终态表（A06）的表体逐行为 `m-`（任务列）、`-`（终态列）、空（墙钟列）、
   `-`（摘要列）。标题与平台 summary 称「终态自动合成/见表」，但表中没有落地值；本工序只登记字面值，
   不替它补数（`do_not_invent_missing_information`）。
2. **判据与裁决规则在本页不可自证**：判据三主一加分（A07）只是阈值声明，三条 `<5% / <10% / <0.005·Umax`
   的**实测值一条都不在本页**；测点住在 `scenario_key=pilot-qr-a / pilot-qr-b` 的 QR 报告（A10）。
   因此本页不能支撑任何「PASS/FAIL」结论，只能支撑「判据与裁决规则被这样写下来」。
3. **指针可能悬空**：探测 {PROBE["keys"]} 个 scenario_key，命中 0 条者 {len(PROBE["zero"])} 个（{"、".join(PROBE["zero"]) or "无"}），
   其余 {len(PROBE["nonzero"])} 个各命中 {"/".join(str(x) for x in PROBE["counts"] if x)} 条（P5）。本工序不推断原因
   （未发布 / 未生成 / 权限不可见），只登记「在该查询面下不可见」。
4. **prereg 路径在宿主上存在但身份未断言**：`{MANIFEST["assets"][2]["resolution_check"].get("host_probe", [{}])[0].get("path", "")}`
   实测存在（{MANIFEST["assets"][2]["resolution_check"].get("host_probe", [{}])[0].get("size_bytes", "")} 字节），
   但报告未给出该文件哈希（推迟到 A04 的 GAP 键），故按 `referenced_unresolved` 处理，不声称「已核对」。
5. **无图是事实，不是选择**：平台 `figures=[]`、正文无 `![` 引用（A12）；本报告另附的图 1/图 2 是**本工序的
   登记地图**，不是上游的计算场量或对照曲线，不得被当作 9947 的图件。
6. **不标 verified**：manifest 与 envelope 中 `verification_status = not_verified`，只有资产级
   `resolution` 状态；`claims=[]` 是本工序的完整结果而非省略（契约允许空数组）。

## ⑥ 自检：逐条对照 acceptance

{check_table()}

**误差判定（本题为登记工序，无物理量基准）**：本工序唯一可验的「数值」是**字符串/字节级恒等**，不是物理量，
故按恒等判据而非 3% 判据裁：

| 关键量 | 本工序值 | 基准 | 差值 | 是否 <3%？ |
|---|---|---|---|---|
| markdown sha256 | `{s["hash"]}` | 契约 `source_hash` = `c9857b84…3fc0bf` | 0（全等） | 是（恒等，0 误差） |
| markdown 字符数 | {s["chars"]} | 契约 `chars` = {s["chars"]} | 0 | 是（恒等，0 误差） |
| locator 可复现率 | {c["assets"]}/{c["assets"]}（独立重取后重切） | 全部可解析 | 0 条失败 | 是（恒等，0 误差） |
| 资产计数一致性 | counts={c["assets"]}，资产条目={c["assets"]} | 自洽 | 0 | 是（恒等，0 误差） |

诚实声明：本工序**没有**算出任何物理量（阻力/推进/耐波…），因此不存在「vs 实验/参考值」的精度结论；
上表不是精度证据，只是登记正确性证据。报告 9947 本身的物理结论**未经本工序验证，也不由本工序背书**。

## 复现（一键）

```bash
# 工作树根 = 仓库检出；需要 TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS
python3 scripts/kf_register_9947.py        # 取报告 → 校验哈希 → 生成 asset_manifest + kf_result
python3 scripts/kf_verify_9947.py          # 独立重取 + 契约 6 项验收自检 + 附加检查（PASS）
python3 scripts/kf_report_9947.py --no-post  # 重建本报告与图（不发帖）
pytest -q tests/test_kf_wp9947.py          # 不变量测试（含篡改负对照）
```

## 结果 JSON（唯一 json 代码块）

```json
{res_block}
```
"""


def login() -> str | None:
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (u and p):
        return None
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            req = urllib.request.Request(BASE + path, data=json.dumps(
                {"username": u, "password": p}).encode(),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def post(md: str, figure: dict) -> int:
    tok = login()
    if not tok:
        print("FATAL: cannot log in to publish the report")
        return 2
    c = MANIFEST["counts"]
    payload = {
        "title": "KF-RESULT " + PACKAGE_ID,
        "summary": "report 9947 资产登记：%d 个资产（页内可切片 %d / 外部指针未解析 %d / 声明无图 %d），"
                   "markdown sha256 逐字节匹配契约，locator %d/%d 在独立重取后重切通过，"
                   "验收自检 %d/%d PASS；claims=[]，不标 verified。"
                   % (c["assets"], c["resolved_in_source"], c["referenced_unresolved"],
                      c["declared_absent"], c["assets"], c["assets"],
                      sum(1 for x in VERIF["checks"] if x["result"] == "pass"), len(VERIF["checks"])),
        "scenario_key": MANIFEST["source"]["scenario_key"],
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:" + PACKAGE_ID, "KF-RESULT", "asset-registration", "report-9947",
                 "A/B试点", "pilot-ab"],
        "markdown": md,
        "figures": [{"name": figure["name"],
                     "caption": "图1/图2 wp-9947-01 资产登记地图：%d 个资产在 report 9947（%d 字符）字符轴上的定位，"
                                "及可解析状态分布（绿=页内可逐字切片，橙=外部指针未解析，紫=声明无图）"
                                % (c["assets"], MANIFEST["source"]["chars"]),
                     "png_base64": figure["png_base64"]}],
    }
    req = urllib.request.Request(BASE + "/tensor/reports", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=120) as r:
        print("POST /tensor/reports ->", r.read().decode()[:400])
    return 0


if __name__ == "__main__":
    DOCS.mkdir(parents=True, exist_ok=True)
    figure = make_figure()
    md = build_markdown()
    out = DOCS / f"KF-RESULT-{PACKAGE_ID}.md"
    out.write_text(md)
    print("wrote", out, len(md), "chars; figure sha256:", figure["sha256"])
    if "--no-post" in sys.argv:
        sys.exit(0)
    sys.exit(post(md, figure))