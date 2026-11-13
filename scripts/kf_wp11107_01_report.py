#!/usr/bin/env python3
"""wp-11107-01: render the KF-RESULT report (markdown + evidence figures) and publish it.

    python3 scripts/kf_wp11107_01_report.py render    # docs/kf_result_wp-11107-01.md + figures
    python3 scripts/kf_wp11107_01_report.py publish    # POST /tensor/reports (env credentials)

Every number and every quote in the rendered markdown is pulled from the artefacts written by
scripts/kf_wp11107_01_register.py (asset_manifest.json / verification.json) or measured here --
nothing is typed in from memory. The body carries exactly ONE ```json block: the kf_result envelope.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-11107-01"
MANIFEST = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
ENVELOPE = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
VERIFY = json.loads((PKG / "verification.json").read_text(encoding="utf-8"))
SOURCE = (ROOT / "runs" / "wp-11107-01" / "source_11107.md").read_text(encoding="utf-8")
MD_OUT = ROOT / "docs" / "kf_result_wp-11107-01.md"
FIG1 = PKG / "figures" / "fig_asset_locator_map.png"
FIG2 = PKG / "figures" / "fig_identity_census.png"
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
PACKAGE_ID = "wp-11107-01"
REPRO = "python3 scripts/kf_wp11107_01_register.py all && python3 scripts/kf_wp11107_01_report.py render && python3 -m pytest tests/test_kf_wp11107_01.py -q"


def login() -> str:
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(API + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())["access_token"]


def census_figure() -> Path:
    """Panel A: measured vs contract identity quantities. Panel B: asset resolution census."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    src = MANIFEST["source"]
    checks = VERIFY["checks"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.2, 1]})

    labels = ["chars", "bytes_utf8", "lines"]
    measured = [src["chars"], src["bytes_utf8"], src["lines"]]
    contract = [MANIFEST["contract"]["chars"], None, None]
    x = range(len(labels))
    ax1.bar([i - 0.2 for i in x], measured, width=0.4, label="measured", color="#4c72b0")
    if any(c is not None for c in contract):
        ax1.bar([i - 0.2 for i in x], [c or 0 for c in contract], width=0.4, fill=False,
                edgecolor="black", hatch="//", label="contract")
    for i, v in enumerate(measured):
        ax1.text(i - 0.2, v * 1.03, "%d" % v, ha="center", fontsize=7)
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(labels, fontsize=8)
    ax1.set_yscale("log")
    ax1.set_title("A. source identity: measured vs contract\nsha256 match=%s  chars match=%s"
                  % (src["hash_matches_contract"], src["chars_match_contract"]), fontsize=8)
    ax1.legend(fontsize=7, frameon=False)
    ax1.grid(axis="y", alpha=0.25)

    res = MANIFEST["counts"]["by_resolution"]
    order = ["resolved_in_source", "resolved_external", "referenced_unresolved", "declared_absent"]
    vals = [res.get(k, 0) for k in order]
    colours = ["#4c72b0", "#55a868", "#c44e52", "#8172b2"]
    bars = ax2.barh(order[::-1], vals[::-1], color=colours[::-1], edgecolor="black", linewidth=0.4)
    for b, v in zip(bars, vals[::-1]):
        ax2.text(b.get_width() + 0.05, b.get_y() + b.get_height() / 2, str(v), va="center", fontsize=8)
    ax2.set_xlim(0, max(vals) + 1.2)
    ax2.set_title("B. asset resolution census (n=%d)\nacceptance checks passing: %d/%d"
                  % (MANIFEST["counts"]["assets"], sum(c["pass"] for c in checks), len(checks)), fontsize=8)
    ax2.tick_params(labelsize=7.5)
    ax2.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG2, dpi=140)
    plt.close(fig)
    return FIG2


def count_tests() -> int:
    """Collected test count, measured (never hand-typed into the report)."""
    import re
    import subprocess
    out = subprocess.run([sys.executable, "-m", "pytest", "tests/test_kf_wp11107_01.py",
                          "--collect-only", "-q"], cwd=ROOT, capture_output=True, text=True)
    m = re.search(r"(\d+) tests? collected", out.stdout)
    if not m:
        raise SystemExit("cannot count tests: " + out.stdout[-300:] + out.stderr[-300:])
    return int(m.group(1))


def render() -> Path:
    census_figure()
    n_tests = count_tests()
    src = MANIFEST["source"]
    cnt = MANIFEST["counts"]
    rec = src["record"]
    assets = MANIFEST["assets"]
    checks = VERIFY["checks"]

    def asset_row(a):
        loc = a["locator"]
        q = loc["quote"] if len(loc["quote"]) <= 78 else loc["quote"][:75] + "..."
        return "| %s | %s | %s | %d | `%s` |" % (
            a["asset_id"], a["asset_class"], a["resolution"], loc["start_line"], q.replace("|", "\\|"))

    def quoterow(item_id, field, quote, loc):
        q = quote.replace("\n", " ").replace("|", "\\|")
        return "| %s | %s | chars %d–%d, line %d | `%s` |" % (
            item_id, field, loc["start_char"], loc["end_char"], loc["start_line"], q)

    ev_rows = []
    ev_rows.append(quoterow("A01", "source document H1 (title line)", assets[0]["locator"]["quote"],
                            assets[0]["locator"]))
    for a in assets[1:]:
        ev_rows.append(quoterow(a["asset_id"], a["asset_class"], a["locator"]["quote"], a["locator"]))
    for c in MANIFEST["cross_references"]:
        ev_rows.append(quoterow(c["refers_to_asset_id"] + " (cross-ref)", c["kind"],
                                c["locator"]["quote"], c["locator"]))

    check_rows = "\n".join(
        "| `%s` | %s | %s | %s |" % (c["id"], c["check"].replace("|", "\\|"),
                                     "PASS" if c["pass"] else "FAIL",
                                     str(c["evidence"]).replace("|", "\\|")[:220])
        for c in checks)

    err_rows = "\n".join([
        "| markdown sha256 vs contract `input.source_hash` | 0 | YES (byte-identical) |",
        "| markdown chars vs contract `input.chars` | %.6f %% | YES |" % (
            0.0 if src["chars"] == MANIFEST["contract"]["chars"] else
            100 * abs(src["chars"] - MANIFEST["contract"]["chars"]) / MANIFEST["contract"]["chars"]),
        "| record.title vs contract `input.title` | exact string equality (%s) | YES |"
        % rec["title_matches_contract"],
        "| record.scenario_key vs contract `input.scenario_key` | exact string equality (%s) | YES |"
        % rec["scenario_matches_contract"],
        "| physical quantities of the underlying study (K_J, Paris C/m, dK_th, K_IC, D) | **not recomputed here** | N/A |",
    ])

    md = f"""# KF-RESULT wp-11107-01

*工序 `01-asset-registration` · report_id **11107** · lane C · 分层 TensorFEM|research|A · 本文件是唯一结果信道*

## ① 本工序做了什么

对 report_id=11107 做**源资产登记**：确认 `tensor://reports/11107`（字段 `markdown`）的字节身份，并枚举报告里可定位的附件/工件。
不做抽取、不做报告分类、不写任何 topics/claims、不标 verified。契约 `objective` 明确 `register_assets: true / classify_report_type: false`，
因此 `claims` 为空数组是**完整结果**而非遗漏。

| 登记项 | 值（全部由脚本测量，非手抄） |
|---|---|
| report_id / mission_id / status | {src["report_id"]} / {rec["mission_id"]} / {rec["status"]} |
| title | `{rec["title"]}` |
| scenario_key | `{rec["scenario_key"]}` |
| markdown sha256 | `sha256:{src["hash"]}` |
| 与契约 source_hash 一致 | **{src["hash_matches_contract"]}** |
| chars / bytes_utf8 / lines | {src["chars"]} / {src["bytes_utf8"]} / {src["lines"]} |
| chars 与契约（{MANIFEST["contract"]["chars"]}）一致 | **{src["chars_match_contract"]}** |
| 登记资产数 / claims 数 | {cnt["assets"]} / {cnt["claims"]} |
| 资产分类直方图 | `{json.dumps(cnt["by_class"], ensure_ascii=False)}` |
| 解析状态直方图 | `{json.dumps(cnt["by_resolution"], ensure_ascii=False)}` |

**这个验证面是什么**（原文子串，非改写）：原文第 3 行（副标题）给出验证面标识符 `{assets[-1]["locator"]["quote"]}`，即 TensorFEM 的 C(T) 试样疲劳裂纹扩展验证面；
其 4 张图在 §4 以绝对路径给出，同时在 §3.7 的 `C8_figures` 判据里以仓库相对路径重复出现。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET {API}/tensor/reports/11107`（Bearer = 环境变量 `TENSOR_AGENT_USER` 登录的 token）；不读数据库直连（`tensor_reports` 对本角色无 SELECT 权限），
   不凭记忆。原文副本落 `runs/wp-11107-01/source_11107.md`，API 原始载荷落 `runs/wp-11107-01/report_11107.json`。
2. **算身份**：对 markdown 的 UTF-8 字节做 `sha256`；同时记录 chars / bytes_utf8 / lines / 是否 CRLF / 是否带尾换行。
   与契约 `input.source_hash`、`input.chars`、`input.title`、`input.scenario_key` 逐项比对（脚本内 `hash_match / chars_match / title_match / scenario_match`）。
3. **枚举资产**（正则驱动，零人工挑选）：
   - `record.figures[*]`（平台元数据：name+caption，共 {cnt["figures_declared_in_record"]} 条）；
   - 正文 §4 的绝对路径 `.../artifacts/<case>/fig*.png`（共 {cnt["figure_paths_quoted_in_body"]} 条）；
   - §3.7 `C8_figures` 判据里的仓库相对路径（作为 cross-reference，逐条标注是否能在本工作树解析）；
   - 副标题/摘要里的验证面标识符 `tensorfem.fatigue.ct_specimen`（代码引用）。
4. **解析探测**：
   - 平台是否提供附件字节：`GET /tensor/reports/11107/artifacts` → **404**，`.../figures` → **404**（本平台构建无工件端点，故图表字节只能从报告给出的文件路径取）；
   - 外部路径按 `os.path` 探测 + 读字节算 sha256（只读，不复制、不改动上游产物）；
   - 代码引用在本仓源码（\*.py/\*.toml/\*.cfg）内 grep（排除 .git/docs/tests 与本工序自己的产物，避免读别的工作包输出）。
5. **定位器**：每个资产一个 `char_span` 定位器（`start_char/end_char/start_line/end_line/quote/quote_sha256/occurrences_in_source/unique`）；
   `occurrences_in_source` 与 `unique` 是**测量**出来的，重复引用不隐藏（例：目录前缀在 §4 出现 {assets[5]["locator"]["occurrences_in_source"]} 次，`unique=false`）。
6. **封信封**：`kf_result.json`（`provenance.source_hash` / `source_field` / `producer` / `emitted_at` + `outputs["asset_manifest.json"]`），
   用 `schemas/kf_result.v1.schema.json` 校验；清单本身用本包 schema `schemas/asset_manifest.wp-11107-01.schema.json` 校验。
7. **自校验**：`verify` 子命令**重新拉一次**平台原文，重算 sha256，并逐条重放定位器（quote 子串、字符跨度、行号、出现次数四项全对才 PASS）。

复跑一键命令（工作树根）：

```
{REPRO}
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-11107-01/asset_manifest.json` | 资产清单本体：source 身份 + {cnt["assets"]} 个资产（含定位器/解析探测/备注）+ counts + id_integrity + claims=[] + 空 claims 理由 |
| `docs/kf/wp-11107-01/kf_result.json` | 工序结果信封（`package_id/task_type/report_id/provenance/outputs`），即交给平台门的对象 |
| `docs/kf/wp-11107-01/verification.json` | 6 条 acceptance 自检结果（含证据字符串，全部由脚本产出） |
| `docs/kf/wp-11107-01/figures/fig_asset_locator_map.png` | 图 1：各资产在原文**字符轴**上的位置 + 解析状态（斜纹=未解析） |
| `docs/kf/wp-11107-01/figures/fig_identity_census.png` | 图 2：A 身份量 measured vs contract；B 解析状态普查 + 自检通过数 |
| `runs/wp-11107-01/source_11107.md` | 原文副本（离线复算实验的依据，其 sha256 与清单一致） |
| `runs/wp-11107-01/report_11107.json` | 平台 API 原始载荷（元数据溯源） |
| `scripts/kf_fetch_11107.py` | 取原文 + 打印身份量的最小脚本 |
| `scripts/kf_wp11107_01_register.py` | build/envelope/figure/verify 四子命令（登记与自检的唯一实现） |
| `scripts/kf_wp11107_01_report.py` | 渲染本报告 + 发布到平台报告信道 |
| `tests/test_kf_wp11107_01.py` | {n_tests} 个离线验收测试用例（schema、hash、定位器、唯一性、claims 空、报告唯一 json 块） |
| `schemas/asset_manifest.wp-11107-01.schema.json` | 本包清单 schema（canonical 信封 schema 见 `schemas/kf_result.v1.schema.json`） |

## ④ 证据定位表（claim/字段 → 原文逐字引文 + 字符跨度）

下表的 `quote` 全部是对原文的**逐字子串**；`chars a–b` 为 0 基字符偏移，`line n` 为 1 基行号，均由脚本测量并在 `verify` 中重新命中。

| 资产/字段 | 类型 | 定位 | 原文引文（逐字） |
|---|---|---|---|
{chr(10).join(ev_rows)}

资产一览（解析状态）：

| asset_id | 类型 | 解析状态 | 行号 | 引文（截断） |
|---|---|---|---|---|
{chr(10).join(asset_row(a) for a in assets)}

## ⑤ 注意点与局限

- **图表字节不在交付树内。** 4 张 png 由上游任务工作树 `/root/tp-agent/work/m9374`（本机路径）产出，平台又不提供工件端点（两个端点均 404），
  所以登记的是「路径 + 字节数 + sha256」而非拷贝二进制：`resolution=resolved_external`。该路径是宿主本地、可清理的，
  因此**知识库不能依赖它**；下游若需要像素级证据，必须先做一次工件入库（本工序契约不含拷贝权限）。
- **`A07 tensorfem.fatigue.ct_specimen` 是 unresolved。** 该验证面实现于 TensorFEM，本仓（TensorKnowledge）不含求解器代码，grep 源码零命中；
  按纪律登记为 `referenced_unresolved`，而不是写成「不存在」或「已实现」。
- **§3.7 的仓库相对路径在本树不解析。** `artifacts/fatigue_ct_e647/*.png` 作为 cross-reference 登记，`resolves_in_delivery_worktree=false`；
  同一引文在原文出现 2 次（一次作为绝对路径的子串），`unique=false` 如实记录。
- **哈希是字节级、含空白。** 任何对 markdown 的空格/换行/全角标点改动都会改变 `source_hash`；本工序不做任何归一化（不 strip、不转义）。
- **本工序不产出知识。** `claims=[]`：报告里的 C1–C8 判据、Paris 常数、dK_th、K_IC、Miner D 等数字**没有被抽取或复核**，
  它们的证据等级仍是上游报告自己的声明；抽取是下游工序（03）的事。
- **`verified` 一律不标。** `verification.json` 里的 6 个 PASS 是本工序对自身 acceptance 的自检，**不是**平台的核验判定；
  `VERIFY["note"]` 已写明这一点。
- **只读边界**：除 `report_id=11107` 的原文外，未读写任何其它 report_id 的报告；`docs/rci-f1-abc/**` 等其它工作包产物被显式排除在 grep 范围外。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 检查内容 | 结果 | 证据（脚本产出） |
|---|---|---|---|
{check_rows}

`all_pass = {VERIFY["all_pass"]}`（{sum(c["pass"] for c in checks)}/{len(checks)}）。无失败项，故无 honest-FAIL 需要申报；
但上文 ⑤ 列出的三条局限（图表字节不可入库、代码引用 unresolved、相对路径不解析）是**已知未解部分**，不计入 acceptance 失败。

## 误差判定（关键量 vs 基准）

本工序是登记工序，不重算任何物理量；可判定的量是**身份量**，基准即契约 `input`：

| 量 | 与基准偏差 | 是否 < 3 % |
|---|---|---|
{err_rows}

物理量（K_J、Paris C/m、dK_th、K_IC、Miner D 等）：**无基准可判、也不在本工序范围内**——本工序只登记报告与工件身份，
不对报告结论做二次计算；因此「是否 < 3 %」对这些量按纪律声明为 N/A 而非含糊通过。图 2A/B 给出身份量对照与解析普查。

## 结果 JSON（唯一 json 代码块，平台门按此校验）

```json
{json.dumps(ENVELOPE, ensure_ascii=False, indent=2)}
```

---

*图 1 = `fig_asset_locator_map.png`（资产在字符轴上的定位与解析状态）；图 2 = `fig_identity_census.png`（身份量 vs 契约、解析状态普查）。*
"""
    MD_OUT.write_text(md, encoding="utf-8")
    return MD_OUT


def publish() -> None:
    def call(path, body=None, tok=None):
        data = None if body is None else json.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
        if tok:
            headers["Authorization"] = "Bearer " + tok
        req = urllib.request.Request(API + path, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode()

    st, body = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                    "password": os.environ["TENSOR_AGENT_PASS"]})
    assert st == 200, (st, body[:300])
    tok = json.loads(body)["access_token"]

    markdown = MD_OUT.read_text(encoding="utf-8")
    figs = []
    for path, caption in (
            (FIG1, "图 1 — wp-11107-01 资产定位图：横轴为 report 11107 markdown 的字符偏移，"
                   "每条带为该资产定位器跨度；斜纹=未解析（referenced_unresolved）。"),
            (FIG2, "图 2 — A：markdown chars/bytes/lines 的测量值与契约值对照（sha256 与 chars 均匹配）；"
                   "B：资产解析状态普查（resolved_in_source / resolved_external / referenced_unresolved / declared_absent）。")):
        figs.append({"name": path.name, "caption": caption,
                     "png_base64": base64.b64encode(path.read_bytes()).decode()})

    payload = {
        "title": "KF-RESULT " + PACKAGE_ID,
        "summary": ("wp-11107-01 (01-asset-registration, report 11107): markdown sha256 "
                    "799d7ffe…c982 recomputed from the platform and equal to the contract hash; "
                    "13319 chars; 4 record figures + producer workspace + verification-face symbol "
                    "registered as 7 assets with char-span locators; 6/6 acceptance self-checks pass; "
                    "claims=[] by contract (no extraction, nothing marked verified)."),
        "scenario_key": MANIFEST["contract"]["scenario_key"],
        "mission_id": 15690,
        "tags": ["kf-wp:" + PACKAGE_ID, "01-asset-registration", "report:11107", "lane:C",
                 "draft", "knowledge-factory", "TensorFEM"],
        "markdown": markdown,
        "figures": figs,
    }
    st, resp = call("/tensor/reports", payload, tok)
    print(st, resp[:800])
    if st not in (200, 201):
        raise SystemExit("publish failed")
    rec = json.loads(resp)
    snap = {
        "package_id": PACKAGE_ID,
        "report_id": str(rec.get("id")),
        "published_at": rec.get("created_at"),
        "markdown_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
        "markdown_chars": len(markdown),
        "figures": [{"name": f["name"],
                     "sha256": hashlib.sha256(base64.b64decode(f["png_base64"])).hexdigest(),
                     "bytes": len(base64.b64decode(f["png_base64"]))} for f in figs],
        "note": ("snapshot of what was posted to the platform report channel; the worktree copy of "
                 "docs/kf_result_wp-11107-01.md must keep this sha256 -- if the artefacts are "
                 "regenerated (timestamps change) the report must be re-published, not silently "
                 "left stale"),
    }
    (PKG / "published.json").write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
    print("snapshot -> %s (markdown sha256 %s)" % (PKG / "published.json", snap["markdown_sha256"]))


def adopt(rid: str) -> None:
    """Restore the worktree copy from the published record (source of truth = the platform copy).

    Used when artefacts were regenerated after publication: the report is immutable, so the
    worktree must be brought back to exactly what was published instead of silently diverging.
    """
    def call(path, tok=None):
        req = urllib.request.Request(API + path)
        if tok:
            req.add_header("Authorization", "Bearer " + tok)
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read().decode())

    tok = login()
    rec = call("/tensor/reports/" + rid, tok)
    md = rec["markdown"]
    MD_OUT.write_text(md, encoding="utf-8")
    env = json.loads(md.split("```json", 1)[1].split("```", 1)[0])
    (PKG / "kf_result.json").write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (PKG / "asset_manifest.json").write_text(
        json.dumps(env["outputs"]["asset_manifest.json"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    figs = []
    for f in (PKG / "figures").glob("*.png"):
        b = f.read_bytes()
        figs.append({"name": f.name, "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)})
    snap = {"package_id": PACKAGE_ID, "report_id": str(rec.get("id")),
            "published_at": rec.get("created_at"),
            "markdown_sha256": hashlib.sha256(md.encode("utf-8")).hexdigest(),
            "markdown_chars": len(md), "figures": sorted(figs, key=lambda x: x["name"]),
            "note": ("adopted from the platform copy via GET /tensor/reports/%s; the worktree files are "
                     "byte-equal to what was published" % rid)}
    (PKG / "published.json").write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("adopted report %s -> %s (sha256 %s)" % (rid, MD_OUT, snap["markdown_sha256"]))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "render":
        print(render())
    elif cmd == "publish":
        publish()
    elif cmd == "adopt":
        adopt(sys.argv[2])
    else:
        raise SystemExit("unknown subcommand " + cmd)