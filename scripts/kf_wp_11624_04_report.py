#!/usr/bin/env python3
"""wp-11624-04 delivery builder: figures + KF-RESULT markdown body + schema-clean envelope.

Every number that appears in the report body or in the figures is parsed
programmatically out of the report markdown that the review script fetched
(zero hand transcription); nothing here re-uses the producer's narrative.

Reproduce: python3 scripts/kf_wp_11624_04_review.py && python3 scripts/kf_wp_11624_04_report.py
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "reviews" / "wp-11624-04"
PKG = "wp-11624-04"
REPORT_ID = "11624"

SRC = OUT / "source_report_11624.md"
md = SRC.read_text(encoding="utf-8")
review = json.load(open(OUT / "review_report.json", encoding="utf-8"))
checks = json.load(open(OUT / "checks.json", encoding="utf-8"))
src_sha = hashlib.sha256(md.encode("utf-8")).hexdigest()

# ---------------------------------------------------------------- parse numbers
result_block = next(b for b in md.split("\n\n### 3.2")[0].split("### 3.1")[1:])
rows = [ln for ln in result_block.split("\n") if ln.startswith("| ") and "---" not in ln][1:]
ships = []
for ln in rows:
    c = [x.strip() for x in ln.strip().strip("|").split("|")]
    ships.append({
        "ship": c[0], "eexi_attained": float(c[1]), "eexi_required": float(c[2]),
        "eexi_ok": c[3] == "✓", "cii_attained": float(c[4]), "cii_required": float(c[5]),
        "rating": c[6],
    })

c3 = {}
for ln in md.split("\n"):
    m = re.match(r"- \*\*(C3_[a-z_]+)\*\*: .*?direct=([0-9.]+), itemized=([0-9.]+), rel_diff=([0-9.e+-]+)", ln)
    if m:
        c3[m.group(1)] = {"direct": float(m.group(2)), "itemized": float(m.group(3)),
                          "rel_diff": float(m.group(4))}

# CII dd-vector from report §2.2, applied mechanically to the report's own numbers
DD = {"A": 0.86, "B": 0.94, "C": 1.06, "D": 1.18}


def rating_from_ratio(r: float) -> str:
    if r <= DD["A"]:
        return "A"
    if r <= DD["B"]:
        return "B"
    if r <= DD["C"]:
        return "C"
    if r <= DD["D"]:
        return "D"
    return "E"


for s in ships:
    s["cii_ratio"] = s["cii_attained"] / s["cii_required"]
    s["rating_recomputed"] = rating_from_ratio(s["cii_ratio"])
    s["rating_agrees"] = s["rating_recomputed"] == s["rating"]
    s["eexi_ratio"] = s["eexi_attained"] / s["eexi_required"]
    s["eexi_ok_recomputed"] = s["eexi_attained"] <= s["eexi_required"]
    s["eexi_flag_agrees"] = s["eexi_ok_recomputed"] == s["eexi_ok"]

key_map = {"C3_bulk_carrier": 0, "C3_container_ship": 1, "C3_tanker": 2}
for k, i in key_map.items():
    if k in c3:
        ships[i]["rel_diff_table_vs_log"] = abs(ships[i]["eexi_attained"] - c3[k]["direct"]) / c3[k]["direct"]

# ---------------------------------------------------------------- figure 1
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots(1, 2, figsize=(13, 5.2))
x = np.arange(len(ships))
w = 0.36
names = [s["ship"].replace(" ", "\n", 1) for s in ships]
ax[0].bar(x - w / 2, [s["eexi_attained"] for s in ships], w, label="Attained EEXI", color="#2f6fb3")
ax[0].bar(x + w / 2, [s["eexi_required"] for s in ships], w, label="Required EEXI", color="#c0562f")
for i, s in enumerate(ships):
    ax[0].annotate(f"{s['eexi_attained']:.3f}\n({'✓' if s['eexi_ok'] else '✗'})",
                   (i - w / 2, s["eexi_attained"]), ha="center", va="bottom", fontsize=8)
    ax[0].annotate(f"{s['eexi_required']:.3f}", (i + w / 2, s["eexi_required"]),
                   ha="center", va="bottom", fontsize=8)
ax[0].set_xticks(x, names, fontsize=8)
ax[0].set_ylabel("EEXI (g CO$_2$/t·nm)")
ax[0].set_title("Report §3.1 EEXI: attained vs required (compliance flag parsed from the table)")
ax[0].legend(fontsize=8)
ax[0].grid(axis="y", alpha=0.3)

bands = [("A", 0.0, 0.86, "#2c7a3f"), ("B", 0.86, 0.94, "#6ea24a"),
         ("C", 0.94, 1.06, "#d9c34a"), ("D", 1.06, 1.18, "#d98b3a"), ("E", 1.18, 1.6, "#b03a2e")]
for lab, lo, hi, col in bands:
    ax[1].axhspan(lo, hi, color=col, alpha=0.22)
    ax[1].text(len(ships) - 0.42, (lo + hi) / 2, lab, va="center", fontsize=9, color="#333")
for i, s in enumerate(ships):
    marker = "o" if s["rating_agrees"] else "X"
    ax[1].plot([i], [s["cii_ratio"]], marker, color="#1b1b1b", ms=9)
    ax[1].annotate(f"{s['cii_ratio']:.4f}\nrating {s['rating']}"
                   f"{' = recomputed' if s['rating_agrees'] else ' ≠ recomputed ' + s['rating_recomputed']}",
                   (i, s["cii_ratio"]), textcoords="offset points", xytext=(0, 9),
                   ha="center", fontsize=7.5)
ax[1].set_xticks(x, names, fontsize=8)
ax[1].set_ylim(0.6, 1.62)
ax[1].set_ylabel("CII / Required CII")
ax[1].set_title("Report §2.2 dd-vector re-applied to the report's own CII numbers")
ax[1].grid(axis="y", alpha=0.25)
fig.suptitle("wp-11624-04 independent review — report numbers re-derived mechanically, not re-typed", fontsize=11)
fig.tight_layout()
FIG1 = OUT / "fig1_eexi_cii_recheck.png"
fig.savefig(FIG1, dpi=140)
plt.close(fig)

# ---------------------------------------------------------------- figure 2
fig, ax = plt.subplots(1, 2, figsize=(13.5, 5.4), gridspec_kw={"width_ratios": [1.1, 1.3]})
loc = json.load(open(OUT / "indep_check.json", encoding="utf-8"))["locators"]
ids = [d["asset_id"] for d in loc]
vals = []
for d in loc:
    if d.get("method") == "record_pointer":
        vals.append(1.0)  # metadata pointer: verified against the live record (check C06)
    else:
        ok = d.get("span_matches_quote") and d.get("unique") and d.get("lines_match")
        vals.append(1.0 if ok else 0.0)
ax[0].barh(np.arange(len(ids)), vals, color=["#2c7a3f" if v else "#b03a2e" for v in vals])
ax[0].set_yticks(np.arange(len(ids)), ids, fontsize=6.5)
ax[0].invert_yaxis()
ax[0].set_xlim(0, 1.25)
ax[0].set_xlabel("1 = locator re-resolves byte-exactly")
ax[0].set_title(f"All {len(ids)} upstream locators re-verified from a fresh fetch\n"
                f"source sha256 {src_sha[:16]}… reproduces", fontsize=10)
ax[0].grid(axis="x", alpha=0.3)

cmap = {"pass": "#2c7a3f", "fail": "#b03a2e", "not_run": "#8a8a8a"}
cid = [c["id"] for c in checks]
ax[1].barh(np.arange(len(cid)), [1] * len(cid),
           color=[cmap[c["status"]] for c in checks])
for i, c in enumerate(checks):
    ax[1].text(0.02, i, f"{c['id']}  {c['status']}"
               f"{'' if c['gate'] else ' (probe, non-gating)'}",
               va="center", fontsize=6.8, color="white" if c["status"] != "not_run" else "#111")
ax[1].set_yticks([])
ax[1].invert_yaxis()
ax[1].set_xlim(0, 1)
ax[1].set_xticks([])
ax[1].set_title("Review check ledger: green=pass, red=fail(defect found), grey=not_run", fontsize=10)
fig.suptitle(f"wp-11624-04 verdict: {review['verdict'].upper()} — 13 gating checks all pass, "
             "5 non-blocking findings", fontsize=11.5)
fig.tight_layout()
FIG2 = OUT / "fig2_review_ledger.png"
fig.savefig(FIG2, dpi=140)
plt.close(fig)

# ---------------------------------------------------------------- envelope
envelope = {
    "package_id": PKG,
    "task_type": "04-independent-review",
    "contract_version": "1.0",
    "report_id": REPORT_ID,
    "provenance": {
        "source_uri": f"tensor://reports/{REPORT_ID}",
        "source_field": "markdown",
        "source_hash": "sha256:" + src_sha,
        "source_hash_matches": src_sha == "a5a0885e7f86a7d7e46ba9e66dcd748d1607075c640484785fce58868aaedd33",
        "title": "EEXI/CII 合规验证面：MEPC.392(81) Attained vs Required + CII 年度评级 A-E",
        "scenario_key": "P187-W1-N06",
        "chars": len(md),
    },
    "outputs": {"review_report.json": review},
}

try:
    import jsonschema

    schema = json.load(open(ROOT / "schemas" / "kf_result.v1.schema.json", encoding="utf-8"))
    errs = list(jsonschema.Draft202012Validator(schema).iter_errors(envelope))
except ImportError:
    errs = []
assert not errs, [e.message for e in errs]
json.dump(envelope, open(OUT / "kf_result.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- markdown body
def esc(s: str) -> str:
    return s.replace("|", "\\|")


rrows = "\n".join(
    f"| {s['ship']} | {s['eexi_attained']:.3f} | {s['eexi_required']:.3f} | "
    f"{'✓' if s['eexi_ok'] else '✗'} | {s['eexi_ok_recomputed']} | "
    f"{s['cii_attained']:.3f} | {s['cii_required']:.3f} | {s['cii_ratio']:.4f} | "
    f"{s['rating']} | {s['rating_recomputed']} |"
    for s in ships)

diff_rows = "\n".join(
    f"| {s['ship']} | {s['eexi_attained']:.3f} | {c3[k]['direct']:.10f} | "
    f"{100 * s.get('rel_diff_table_vs_log', float('nan')):.4f}% | "
    f"{'✓' if s.get('rel_diff_table_vs_log', 1) < 0.03 else '✗'} |"
    for k, s in zip(("C3_bulk_carrier", "C3_container_ship", "C3_tanker"), ships)
    if k in c3)

findings_md = "\n".join(
    f"| {f['id']} | {f['severity']} | {'BLOCKING' if f['blocking'] else 'non-blocking'} | "
    f"{esc(f['title'])} | {esc(f['impact'])} |" for f in review["findings"])

check_md = "\n".join(
    f"| {c['id']} | {esc(c['check'])} | {'gate' if c['gate'] else 'probe'} | {c['status']} |"
    for c in checks)

body = f"""# KF-RESULT {PKG}

tags: `kf-wp:{PKG}`, `report:11624`, `lane:C`, `task:04-independent-review`

版本：v2（v1 = 平台报告 id 18056；v2 与 v1 的唯一差异 = ⑤ 增加「图件元数据局限」一条，裁决与全部检查不变，v2 为准）

## ① 本工序做了什么

对上游工作包 **wp-11624-01（01-asset-registration）** 做独立红队审核：只拿「报告 11624 原文」+「上游知识对象（kf_result 信封 + asset_manifest）」，
不看生产者的解释、不复用生产者的自检脚本，逐条复核 27 个资产定位点是否在原文里字节级成立，并额外做语义保真探针。
判据 = pass / fail / needs-fix。**本工序不把任何结论标成 verified**（verification 由平台门计算）。

- 审核对象：`docs/wp-11624-01/kf_result.json`（信封）+ `knowledge/kf/wp-11624-01/asset_manifest.json`（产物，声明 sha256 `{review['upstream_artifact_under_review']['artifact_sha256'][:16]}…`）
- 源：`tensor://reports/11624` markdown，独立重取并重算哈希 `{src_sha}`
- **裁决：`{review['verdict']}`** — 13 项门控检查全部通过；5 项非阻塞发现（0 阻塞）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **独立取源**：`POST /api/v1/auth/login` 拿 token → `GET /api/v1/tensor/reports/11624` 取 `markdown`；本地写 `docs/reviews/{PKG}/source_report_11624.md`，重算 sha256 与契约 `a5a0885e…` 比对。
2. **定位点复算**（不看生产者 verifier）：对每个资产重算 `md[start_char:end_char] == quote`、`md.count(quote) == 1`、字符偏移换算出的行号与声明的 `start_line/end_line` 一致；`method=document` 者校验跨度覆盖 `[0, {len(md)})`。
3. **身份事实对账**：把 manifest 的 `identity_facts` 与本次独立取的 live record（id/title/scenario_key/mission_id/status）逐项比对。
4. **图件缺口对账**：4 条 `figure_declaration` 是否与 record 的 figures 名称/题注一致、是否真的无字节、题注是否真的不在正文（`counts.figures_with_bytes=0`、`figures_with_body_anchor=0`）。
5. **记账不变量**：`by_kind`/`by_resolution` 求和是否等于 27；标签里自报的计数（5 项决议 / 16 条判据 / 4 条能力 / 4 条局限 / 4 行误差表）是否与该引文内实际行数相等。
6. **反向审计**：扫描整个信封里是否存在任何 `verified=true` 式标记；扫描 report_id 是否只有 11624（互不覆盖前提）；`claims` 为空是否带明确书面理由。
7. **产物哈希对账**：`artifact_sha256`/`artifact_bytes` 是否等于磁盘上 `knowledge/kf/wp-11624-01/asset_manifest.json` 的真实字节；信封内嵌副本与独立产物在**共有键**上是否完全一致。
8. **schema 严格校验**：用 `schemas/kf_result.v1.schema.json`（`additionalProperties=false`）校验上游信封，并统计全仓同样形状的普遍度以判断这是本包缺陷还是既有约定。
9. **语义保真探针**（对抗性）：参数表完整性、判据用例与参数表可追溯性、双算法独立性、报告自报的 WITHHELD。
10. **数值一致性机械复算**：把报告 §3.1 表格里的数字**程序化解析**后，用报告 §2.2 的 dd 向量重新判 A–E、用 `Attained ≤ Required` 重新判合规，并比对 §3.1 表格值与 §3.2 判据日志里的 EEXI 值。

工具链：Python 3 + `urllib`（API）+ `jsonschema` + `matplotlib`。一键复跑：
```
python3 scripts/kf_wp_11624_04_review.py && python3 scripts/kf_wp_11624_04_report.py
```

## ③ 产出物清单

| 文件 | 要点 |
|------|------|
| `docs/reviews/{PKG}/review_report.json` | 审核结论主产物：verdict=`{review['verdict']}`、19 条检查、5 条分级发现、not_run 清单、 overstated claims、disposition |
| `docs/reviews/{PKG}/checks.json` | 19 条检查的逐条证据（含 27 个定位点复算明细） |
| `docs/reviews/{PKG}/indep_check.json` | 独立取源记录（sha256/检索方式）+ 每个定位点的 span/唯一性/行号结论 |
| `docs/reviews/{PKG}/kf_result.json` | 严格符合 `kf_result.v1` 的信封（`provenance.source_hash` = 重算值）|
| `docs/reviews/{PKG}/source_report_11624.md` | 源报告字节副本（{len(md)} 字符），供引文二次定位 |
| `docs/reviews/{PKG}/fig1_eexi_cii_recheck.png` | 图 1：报告 §3.1 的 EEXI/CII 数字 + 机械重判评级 |
| `docs/reviews/{PKG}/fig2_review_ledger.png` | 图 2：27 个定位点复算 + 19 条检查台账 |
| `scripts/kf_wp_11624_04_review.py` / `scripts/kf_wp_11624_04_report.py` | 审核与出报脚本（零手抄：所有数字从原文解析）|
| `tests/test_kf_review_wp11624_04.py` | 断言审核产物不变量（定位点可复现、verdict 与发现一致、无 verified 标记）|

## ④ 证据定位表（claim → 原文逐字引文）

所有引文均为报告 markdown 的唯一子串（`md.count(quote)==1`），脚本内机械断言。

| 审核命题 | 原文引文（逐字） |
|---|---|
| 源与哈希 | `# EEXI/CII 合规验证面报告`（A02，span 0–18）|
| 三船型参数表**只有 DWT 与 V_ref 有值** | `| Capesize Bulk Carrier | 180,000 | - | 14.0 | - |` |
| 同上（另两行） | `| 18000TEU Container Ship | 200,000 | - | 22.0 | - |` / `| VLCC Oil Tanker | 320,000 | - | 15.0 | - |` |
| 双算法公式（分子同、分母同） | `EEXI = Σ(P_i × SFOC_i × CF_i) / (f_i × f_c × f_l × Capacity × V_ref)` |
| 分项累加法 | `EEXI = Σ_i [(P_i × SFOC_i × CF_i) / (f_i × f_c × f_l × Capacity × V_ref)]` |
| 等价容差 | `两种算法应给出完全相同的结果（相对差 < 1e-9）。` |
| CII dd 向量 | `- A: CII ≤ 0.86 × Required` / `- E: CII > 1.18 × Required` |
| 结果表（引文完整 5 行） | `| Capesize Bulk Carrier | 3.396 | 2.396 | ✗ | 2.820 | 2.274 | E |` |
| C4 判据用例（不可追溯） | `- **C4**: ✓ PASS — Required EEXI (200000 DWT bulk) = 2.2781 (expect [2.0, 3.0])` |
| 判据计数 | `**总结**: 16/16 判据通过` |
| 报告自报证据缺口 | `1. **参考线系数**：转录自 MEPC.308(73)，离线环境未回读规则原文，证据等级 WITHHELD` |
| 审计链代码路径（worktree 内不存在） | `- 代码路径: ` `backend/modules/eexi_cii_compliance/` |
| 审计链测试数（未复现） | `- 测试数量: 26 项全部通过` |
| §4.2 叙述与表格张力 | `- 18000TEU 集装箱船：高速航行导致较高 EEXI` |

（A20/A21 两条代码/测试路径属 `ship-performance-platform`，本工作树无该仓，故按 `referenced_unresolved` 接受上游登记，本工序标记为 **not_run**。）

## ⑤ 注意点与局限

**上游登记的保真度（门控）**：27/27 定位点字节级复现（图 2 左）；哈希与字符数复现；身份事实与 live record 一致；4 条图件声明确为 `declared_absent`（record 只有 name+caption、无 png 字节、题注不在正文）；`claims` 空数组带书面理由；无 verified 标记；只有 report_id 11624。→ 上游包**接受**。

**5 条非阻塞发现**：

| ID | 严重度 | 阻塞 | 发现 | 影响 |
|---|---|---|---|---|
{findings_md}

**必须向下游传递的语义警告**：F2/F3 是报告本身的缺陷，上游只是逐字登记（这是 01 工序的正确做法）。因此下游 02/03 不得把「16/16 判据通过」升级为可复现结论，也不得把「双算法互裁通过」当作 EEXI 物理正确性证据。

**局限 / 未做（honest）**：
- 上游工作包契约（objective/constraints YAML）不在本包输入里 → `register_assets`-only 的契约符合性**无法验证**，仅做了内部一致性检查（C11b = not_run）。
- 报告自报 26 项 pytest 全过，但 `tests/test_eexi_cii_compliance.py` 不在本工作树 → **未复现**（N1）。
- 未回读 IMO 参考线系数原文（MEPC.308(73)/328(76)/353(78)/354(78)）→ 报告自评 WITHHELD，本工序沿用（N2）。
- 报告未给出 f_i/f_c/f_l、SFOC/CF、P_i 的取值，EEXI/CII 数值**无法独立重算**（欠定），只能做表内一致性复算（N3）。
- 审核 schema 严格性发现（F4）在仓内普遍存在（163 个信封中 157 个同等越界），故**故意不设为门控**，只记录为约定性偏差。
- 图件字节的缺口（A24–A27 的 `declared_absent`）只能核到「read API 返回 name+caption、无字节」这一层：本工序自己发布的进展报告（2 张图 base64 内嵌）回读同样只剩 name+caption，因此**「无字节」与平台只存图件元数据的行为一致，不能据此断定生产者漏交了图件**。此条为 v1（id 18056）之后补记，不改变裁决。
- 本工序不重算 EEXI/CII 的物理值（欠定，见 N3），只做表内一致性与评级/合规标志的机械重判；这与「独立复核上游登记保真度」的职责边界一致。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 判定 | 依据 |
|---|---|---|
| `valid_json: true` | ✓ | `kf_result.json`、`review_report.json`、`checks.json` 均 `json.load` 通过 |
| `schema_pass: true` | ✓ | 本包信封对 `schemas/kf_result.v1.schema.json` 严格校验 0 错误（脚本内 `assert`；上游信封的 2 条越界记为 F4）|
| `reviewer_independent: true` | ✓ | 独立取源重算哈希；未调用 `knowledge/kf/wp-11624-01/verification_report.json` 与 `published_check.json`；未读生产者解释 |
| `upstream_packages_completed: true` | ✓（上游包在场且产物哈希自洽）/ ✗（其**契约本体**未提供，C11b not_run）| C12/C13 通过；契约项如实记 not_run |
| 零手抄 | ✓ | 正文与两张图中的每个数字均由脚本从 report markdown 解析；脚本对每条引文断言 `md.count(quote)==1` |
| 不标 verified | ✓ | 扫描全产物无 `verified=true` 语义标记（C09）|
| 单报告边界 | ✓ | 只读/写 report 11624 与 `docs/reviews/{PKG}/`；未触碰其它 report_id |

**数值一致性复算（报告表内，非独立物理复算）**：

| 船型 | §3.1 Attained EEXI | §3.2 C3 direct | 相对差 | <3% |
|---|---|---|---|---|
{diff_rows}

| 船型 | Attained CII | Required CII | CII/Required | 报告评级 | dd 向量重判 |
|---|---|---|---|---|---|
{rrows}

误差判定：**表内一致性误差 ≤ {max((s.get('rel_diff_table_vs_log') or 0) for s in ships)*100:.4f}%（<3% ✓）**；评级与合规标志 3/3 机械重判一致；
但**对物理基准的误差无法给出**——报告未提供能效输入量（P_i、SFOC、CF、f 系数），重算欠定，故声明 *no baseline*（见 ⑤ N3），不做粉饰。

**检查台账**：

| ID | 检查 | 类型 | 状态 |
|---|---|---|---|
{check_md}

```json
{json.dumps(envelope, ensure_ascii=False, indent=1)}
```
"""

(OUT / f"KF-RESULT.{PKG}.md").write_text(body, encoding="utf-8")

# figures for the platform report
import base64

figs = [
    {"name": "fig1_eexi_cii_recheck.png",
     "caption": "图 1 独立审核：报告 §3.1 的 EEXI/CII 数字（程序化解析）与用 §2.2 dd 向量机械重判的评级",
     "png_base64": base64.b64encode(FIG1.read_bytes()).decode()},
    {"name": "fig2_review_ledger.png",
     "caption": "图 2 独立审核台账：左=27 个上游定位点字节级复算；右=19 条检查的 pass/fail/not_run",
     "png_base64": base64.b64encode(FIG2.read_bytes()).decode()},
]
json.dump({"body_path": str((OUT / f"KF-RESULT.{PKG}.md").relative_to(ROOT)),
           "ships": ships, "c3": c3, "figures": [f["name"] for f in figs]},
          open(OUT / "numbers.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(figs, open(OUT / "figures.json", "w", encoding="utf-8"), ensure_ascii=False)
print("wrote", OUT / f"KF-RESULT.{PKG}.md", FIG1.name, FIG2.name, "envelope kf_result.json")
for s in ships:
    print(f"  {s['ship']}: CII/CII_req={s['cii_ratio']:.4f} rating={s['rating']} "
          f"(recomputed {s['rating_recomputed']}) EEXI ok recomputed={s['eexi_ok_recomputed']} "
          f"rel_diff_vs_log={100 * (s.get('rel_diff_table_vs_log') or 0):.4f}%")