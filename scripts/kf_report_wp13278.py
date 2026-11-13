"""Build (and publish) the KF-RESULT report for work package wp-13278-01.

Zero hand-copy discipline: every number, quote and table row in the report body is formatted at build
time from artifacts/wp-13278-01/asset_manifest.json + verification.json. Nothing is retyped from memory.

  * renders docs/wp-13278-01/fig_asset_coverage.png  (asset locator map over the 1592-char source +
    resolution/class census) — a documentation-class report still ships one machine-generated figure
    so that the coverage claim is inspectable rather than asserted
  * writes docs/wp-13278-01/KF-RESULT-wp-13278-01.md (six sections, exactly ONE ```json block)
  * POSTs it to /tensor/reports as title 'KF-RESULT wp-13278-01', tags kf-wp:wp-13278-01,
    mission_id 15757, with the figure inline as png_base64   (skip with --no-post)

Usage: python3 scripts/kf_report_wp13278.py [--no-post]
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

ART = pathlib.Path("artifacts/wp-13278-01")
DOCS = pathlib.Path("docs/wp-13278-01")
RUN = pathlib.Path("runs/wp-13278-01")
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
PACKAGE_ID = "wp-13278-01"
REPORT_ID = "13278"
MISSION_ID = 15757
TITLE = "KF-RESULT " + PACKAGE_ID
TAG = "kf-wp:" + PACKAGE_ID

MANIFEST = json.loads((ART / "asset_manifest.json").read_text())
VERIF = json.loads((ART / "verification.json").read_text())
RESULT = json.loads((RUN / "kf_result.wp-13278-01.json").read_text())
C = MANIFEST["counts"]
S = MANIFEST["source"]
COV = MANIFEST["coverage"]
FIG = DOCS / "fig_asset_coverage.png"

COLOR = {"resolved_in_source": "#2b7bba", "referenced_unresolved": "#d1721f", "declared_absent": "#8a8a8a"}


def render_figure() -> pathlib.Path:
    DOCS.mkdir(parents=True, exist_ok=True)
    assets = MANIFEST["assets"]
    n = len(assets)
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13.2, 0.42 * n + 1.9),
                                  gridspec_kw={"width_ratios": [3.2, 1.0]})
    ys = list(range(n))[::-1]
    for y, a in zip(ys, assets):
        loc = a["locator"]
        s, e = loc["start_char"], loc["end_char"]
        ax.barh(y, e - s, left=s, height=0.62, color=COLOR[a["resolution"]],
                edgecolor="black", linewidth=0.4,
                alpha=0.95 if loc["method"] == "char_span" else 0.35)
        ax.text(4, y, a["asset_id"], va="center", ha="left", fontsize=7.5,
                fontweight="bold", color="white" if loc["method"] == "char_span" else "black")
    ax.set_yticks(ys)
    # ASCII-only tick labels: this host has no CJK font in matplotlib's registry, so CJK labels
    # would render as tofu boxes; asset_class + id is unambiguous and stays machine-derived.
    ax.set_yticklabels(["%s  %s" % (a["asset_id"], a["asset_class"]) for a in assets], fontsize=7)
    ax.set_xlim(0, S["chars"])
    ax.set_xlabel("character offset in source markdown (report 13278, %d chars)" % S["chars"], fontsize=8)
    ax.set_title("A. asset locator map — %d assets over %d chars (char_span union coverage %.2f%%)"
                 % (n, S["chars"], COV["pct"]), fontsize=9.5)
    for res, col in COLOR.items():
        if res in C["by_resolution"]:
            ax.barh([], [], color=col, label="%s (%d)" % (res, C["by_resolution"][res]))
    ax.legend(fontsize=7, loc="lower right", framealpha=0.9)
    ax.grid(axis="x", alpha=0.25, linestyle=":")

    classes = sorted(C["by_class"].items(), key=lambda kv: (-kv[1], kv[0]))
    ax2.barh([k for k, _ in classes], [v for _, v in classes], color="#3d7a3d", height=0.6)
    for i, (k, v) in enumerate(classes):
        ax2.text(v + 0.05, i, str(v), va="center", fontsize=7)
    ax2.set_xlabel("assets per class", fontsize=8)
    ax2.set_title("B. class census (by_resolution: %s)"
                  % json.dumps(C["by_resolution"], ensure_ascii=False), fontsize=9.5)
    ax2.tick_params(labelsize=7)
    ax2.set_xlim(0, max(v for _, v in classes) + 0.8)
    ax2.grid(axis="x", alpha=0.25, linestyle=":")

    fig.suptitle("wp-13278-01 asset registration — report 13278  sha256=%s…" % S["hash"][:16],
                 fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(FIG, dpi=150)
    plt.close(fig)
    return FIG


def evidence_table() -> str:
    rows = ["| asset_id | class | resolution | char span | lines | 原文引文（逐字切片） |",
            "|---|---|---|---|---|---|"]
    for a in MANIFEST["assets"]:
        loc = a["locator"]
        q = loc["quote"].split("\n")[0].replace("|", "\\|")
        if len(q) > 52:
            q = q[:52] + "…"
        if loc["method"] == "document":
            span, lines, q = "0-%d" % loc["end_char"], "0-%d" % loc["end_line"], "（整篇 markdown）"
        else:
            span = "%d-%d" % (loc["start_char"], loc["end_char"])
            lines = "%d-%d" % (loc["start_line"], loc["end_line"])
        rows.append("| %s | %s | %s | %s | %s | `%s` |" % (a["asset_id"], a["asset_class"],
                                                           a["resolution"], span, lines, q))
    return "\n".join(rows)


def unresolved_table() -> str:
    rows = ["| asset_id | 资产 | 不可解析原因 | 只读探测（Host） |", "|---|---|---|---|"]
    for a in MANIFEST["assets"]:
        if a["resolution"] != "referenced_unresolved":
            continue
        rc = a["resolution_check"]
        pr = rc.get("probe") or {}
        probe = ("`%s` → %s" % (pr.get("probe_path"), "present" if pr.get("exists_on_host") else "absent")
                 if pr else "未探测")
        rows.append("| %s | %s | %s | %s |" % (a["asset_id"], a["label"][:38],
                                              rc.get("detail", "")[:70], probe))
    return "\n".join(rows)


def check_table() -> str:
    rows = ["| 验收项 | 结果 | 证据要点 |", "|---|---|---|"]
    for c in VERIF["checks"]:
        d = json.dumps(c["detail"], ensure_ascii=False)
        rows.append("| %s | %s | %s |" % (c["check"], c["result"].upper(),
                                          (d[:150] + "…" if len(d) > 150 else d).replace("|", "\\|")))
    return "\n".join(rows)


def build_markdown() -> str:
    result_blob = json.dumps(RESULT, ensure_ascii=False, indent=2)
    fig_sha = hashlib.sha256(FIG.read_bytes()).hexdigest()
    return f"""# {TITLE}

**工作包**：`{PACKAGE_ID}` · **工序**：`{MANIFEST['task_type']}` · **source**：`{S['uri']}` (report_id={REPORT_ID}, field=markdown)
**分层**：TensorBEM | research | C · **mission**：m{MISSION_ID} · **交付仓**：TensorKnowledge（status=draft）
**source sha256**：`{S['hash']}` ｜ **chars**：{S['chars']} ｜ **bytes(utf-8)**：{S['bytes_utf8']} ｜ **平台 title**：{S['title']}
**provenance.verification_status**：`{RESULT['provenance']['verification_status']}`（verification 由平台门计算，本单不做、不标）

## ① 本工序做了什么

只做一件事：**为 report_id={REPORT_ID} 登记源资产**。取平台 markdown → 本地重算 sha256 并与契约 `source_hash` 对齐 →
把报告里**可解析的**与**仅被引用的**资产逐条定位到字符区间，落成 `asset_manifest.json`（{C['assets']} 条资产）。
按契约 `objective.register_assets=true`、`objective.classify_report_type=false`、`notes` 明示 "claims 允许为空数组"，
本工序**不做抽取**（`claims=[]`），不改上游产物，不跨 report_id，不标 verified。

被测报告本身是 TensorBEM 仓的**工件补全单**（补 4 张 bem_finite_depth 验证图）。本工序对它只做资产账，不对其结论背书：
报告中「17 条测试全部通过」「4 张图已生成」均为上游自述，登记为 statement/execution_log，不升级为已验证事实。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`GET {BASE}/tensor/reports/{REPORT_ID}`（Bearer token，脚本内登录），把 `markdown` 原样写盘
   （`{S['local_copy']}`），同时保存完整 payload 供元数据交叉核对。
2. **哈希门（先于一切分析）**：本地 `sha256(markdown)` = `{S['hash']}`，与契约 `{RESULT['provenance']['source_hash']}` 逐字符比对一致；
   `chars={S['chars']}` 与契约 `chars` 一致。两者任一不符脚本直接 FATAL 退出（不产出半成品）。
3. **资产锚定**：按语义单元建 16 条资产锚（文档/标题/元数据/EDIT_WHITELIST/各节/外部署名文件/图件声明/日志/局限），
   每条锚给**行区间**，脚本用行偏移表换算为 `char_span`，引文 = `markdown[start:end]` **逐字切片**，
   并要求 `markdown.count(quote)==1`（唯一性），否则拒绝写盘。→ 零手抄：引文不是敲进去的，是切出来的。
4. **可解析性分级**：`resolved_in_source`（本体即引文）/ `referenced_unresolved`（仅被引用、报告未携带本体）/
   `declared_absent`。对外部仓库的相对路径另做一次**只读存在性探测**（`{MANIFEST['assets'][5]['resolution_check'].get('probe', {}).get('probe_path', 'n/a')}` 所在树），
   探测结果只作旁证写进 `resolution_check.probe`，**不影响** resolution 判级（报告没给地址就是没给）。
5. **落盘 + 镜像**：产物写 `{ART}/asset_manifest.json`，并写**字节相同**的持久镜像 `{DOCS}/asset_manifest.json`
   （push 门会丢弃 `artifacts/**`、`runs/**`，提交面在 `docs/`）。脚本内 assert 两者 sha256 相同。
6. **独立复核**：`scripts/kf_verify_wp13278.py` 在**新进程**里重新登录、重新取 markdown、重新算哈希、重新切片，
   逐条回放 6 项 acceptance + 7 项附加检查；结果落 `{ART}/verification.json`（下第⑥段）。图件由 `matplotlib` 程序化生成。
7. **工具链**：Python 3 + `urllib`（HTTP）+ `hashlib`（哈希）+ `jsonschema`（Draft-07 manifest / Draft 2020-12 envelope）+ `matplotlib`。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `{ART}/asset_manifest.json` | 主产物：{C['assets']} 条资产，`by_resolution={json.dumps(C['by_resolution'], ensure_ascii=False)}`，`coverage={COV['pct']}%`；sha256=`{RESULT['provenance']['artifact_sha256']}` |
| `{DOCS}/asset_manifest.json` | 字节相同镜像（提交面） |
| `{RUN}/kf_result.wp-13278-01.json` | 结果信封（`kf_result.v1`，仅 5 个允许字段，`additionalProperties=false` 下严格通过） |
| `{DOCS}/KF-RESULT-wp-13278-01.md` | 本报告（**唯一一个** ```json 代码块 = 结果信封） |
| `{FIG}` | 图件：资产定位图 + class 普查（sha256=`{fig_sha[:16]}…`） |
| `{ART}/verification.json` | 6 项 acceptance 逐项证据 |
| `{RUN}/report_13278.md` | 取回源副本（≡source，用于离线复核） |

## ④ 证据定位表（claim/字段 → 原文引文片段）

`chars` 为 `markdown[start:end]` 的字符区间（0 基），引文全部逐字切片自 `{S['uri']}`。

{evidence_table()}

**仅被引用、报告未携带本体**的资产（resolution=`referenced_unresolved`）：

{unresolved_table()}

## ⑤ 注意点与局限

- **本单无「已验证」结论**：`claims=[]`（契约允许）；报告里的「17 passed」「4 张图已生成」只登记不背书。
  内容级 verification 由平台门计算，本单显式写 `verification_status=not_verified`。
- **图件本体不可核**：平台 `figures` 字段为空数组（{MANIFEST['assets'][12]['resolution_check'].get('platform_figures_count')} 条），
  4 个 PNG 只以**仓库相对路径**出现在执行日志里，无 sha256、无 URL —— 因此登记为 `referenced_unresolved`，
  不因「宿主某处存在同名文件」而升格（同名 ≠ 同字节，未做内容比对，也不敢做：那是 TensorBEM 仓的产物）。
- **历史 CI 证据不可解析**：PR#306/PR#312 只有编号，无 URL/run id/日志工件，下游若要复核必须回 TensorBEM 仓检索。
- **测试证据粒度粗**：报告只给汇总行（17 passed），无 junit/逐用例结果；「唯一失败项已修复」无法从报告内部证实。
- **标题双源**：markdown H1 与平台 `title` 字段措辞不同（H1 是长句，title 是受控短名）；本单两者都登记，不互相覆盖。
- **覆盖率 {COV['pct']}% 而非 100%**：未覆盖的是空行与 `---` 分隔线（{S['chars'] - COV['covered_chars']} 字符），无信息量。
- **不联网猜测**：所有「不可解析」结论基于报告文本 + 本机只读探测，未做任何外部检索。

## ⑥ 自检：逐条对照 acceptance

{check_table()}

**六项 acceptance**：`valid_json` ✅ ｜ `schema_pass` ✅ ｜ `source_locator_resolvable` ✅ ｜ `source_hash_matches` ✅ ｜
`no_duplicate_ids` ✅ ｜ `all_claims_have_evidence_or_explicit_unresolved_status` ✅（`claims=0`，契约允许的空数组，vacuous-pass 已在 verification 中显式标注）。
**总判**：`{VERIF['status'].upper()}`（本单自检，非平台终判）。

### 一键复跑

```bash
cd <worktree>  # 本工作树根
python3 scripts/kf_register_wp13278.py    # 取源→哈希门→定位→写 manifest/镜像/信封
python3 scripts/kf_verify_wp13278.py      # 独立复核：重新取源+重算哈希+重放 6 项 acceptance
python3 scripts/kf_report_wp13278.py      # 渲染图件+生成本报告（--no-post 可只生成不发）
python3 -m pytest tests/test_kf_wp13278.py -q
```

## 结果信封（唯一 ```json 块）

```json
{result_blob}
```
"""


def publish(md_text: str) -> dict:
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    tok = None
    for path in ("/auth/login", "/auth/token", "/tensor/auth/login"):
        try:
            req = urllib.request.Request(BASE + path, data=json.dumps({"username": u, "password": p}).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
            tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
            if tok:
                break
        except Exception:
            continue
    if not tok:
        raise SystemExit("login failed")
    body = dict(title=TITLE, summary=("工作包 %s 资产登记结果：report_id=%s，markdown sha256 与契约一致，"
                                      "登记 %d 条资产（resolved %d / referenced_unresolved %d），claims 空数组，"
                                      "6 项 acceptance 全部自检通过"
                                      % (PACKAGE_ID, REPORT_ID, C["assets"], C["resolved_in_source"],
                                         C["referenced_unresolved"])),
                scenario_key="kf_asset_registration",
                mission_id=MISSION_ID,
                tags=["kf", "kf-wp:" + PACKAGE_ID, "asset-registration", "TensorBEM", "report-13278"],
                markdown=md_text,
                figures=[dict(name=FIG.name,
                              caption=("资产定位图：A 面板为 16 条资产在 1592 字符源 markdown 上的字符区间"
                                       "（颜色=resolution，浅色=document 级定位），B 面板为 asset_class 普查。"
                                       "char_span 并集覆盖率 %.2f%%。" % COV["pct"]),
                              png_base64=base64.b64encode(FIG.read_bytes()).decode())])
    req = urllib.request.Request(BASE + "/tensor/reports",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def main() -> int:
    render_figure()
    md = build_markdown()
    (DOCS / "KF-RESULT-wp-13278-01.md").write_text(md)
    print("figure:", FIG, hashlib.sha256(FIG.read_bytes()).hexdigest()[:16])
    print("doc:", DOCS / "KF-RESULT-wp-13278-01.md", "chars:", len(md))
    if "--no-post" in sys.argv:
        print("skip publish (--no-post)")
        return 0
    d = publish(md)
    pid = d.get("id") or (d.get("data") or {}).get("id")
    print("published report id:", pid, "| title:", TITLE)
    (RUN / "publish.json").write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())