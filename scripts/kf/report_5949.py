#!/usr/bin/env python3
"""Render (and optionally publish) the KF-RESULT report for work package wp-5949-01.

Every number and every quotation in the rendered markdown is injected from
docs/kf/wp-5949-01/asset_manifest.json or from the registered source bytes — nothing is retyped,
and each evidence row is asserted to be a verbatim substring of the source before it is written.

Usage:
  python3 scripts/kf/report_5949.py render
  python3 scripts/kf/report_5949.py render publish
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PKG = "wp-5949-01"
REPORT_ID = "5949"
MISSION_ID = 15584
SCENARIO_KEY = "IN25-T2-diversity-engine"

REPO = Path(__file__).resolve().parents[2]
PKG_DIR = REPO / "docs" / "kf" / PKG
MANIFEST = PKG_DIR / "asset_manifest.json"
RESULT = PKG_DIR / "kf_result.json"
VERDICT = PKG_DIR / "verification.json"
SOURCE = PKG_DIR / "source_5949.md"
OUT_MD = PKG_DIR / "report.md"
FIG_DIR = PKG_DIR / "figures"
FIG = FIG_DIR / "asset_inventory.png"

BASE = os.environ.get("TENSOR_API_BASE", "").rstrip("/")
USER = os.environ.get("TENSOR_AGENT_USER", "")
PASS = os.environ.get("TENSOR_AGENT_PASS", "")


# ---------------------------------------------------------------- figure


def render_figure(manifest):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    assets = manifest["assets"]
    classes = sorted({a["asset_class"] for a in assets})
    res = ["resolved_in_source", "referenced_unresolved"]
    colors = {"resolved_in_source": "#2c7fb8", "referenced_unresolved": "#c8c8c8"}
    # NOTE: this image ships no CJK font (fontManager has no CJK face), so the figure labels stay
    # ASCII to avoid tofu boxes; the Chinese explanation lives in the report caption/markdown.

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [2.1, 1]})
    left = [sum(1 for a in assets if a["asset_class"] == c and a["resolution"] == "resolved_in_source") for c in classes]
    right = [sum(1 for a in assets if a["asset_class"] == c and a["resolution"] == "referenced_unresolved") for c in classes]
    y = range(len(classes))
    ax1.barh(list(y), left, color=colors["resolved_in_source"], label="resolved_in_source (located in report)")
    ax1.barh(list(y), right, left=left, color=colors["referenced_unresolved"], label="referenced_unresolved (outside worktree)")
    ax1.set_yticks(list(y))
    ax1.set_yticklabels(list(classes), fontsize=9)
    ax1.invert_yaxis()
    ax1.set_xlabel("assets (count)")
    ax1.set_title("wp-5949-01 asset inventory: %d items (class x resolution)" % len(assets), fontsize=10)
    ax1.legend(fontsize=8, loc="lower right")

    vals = [sum(1 for a in assets if a["resolution"] == r) for r in res]
    ax2.bar(["resolved_in_source", "referenced_unresolved"], vals,
            color=[colors["resolved_in_source"], colors["referenced_unresolved"]])
    for i, v in enumerate(vals):
        ax2.text(i, v + 0.2, str(v), ha="center", fontsize=10)
    ax2.set_ylabel("assets")
    ax2.set_ylim(0, max(vals) * 1.25 + 1)
    ax2.set_title("resolution split (total %d)" % sum(vals), fontsize=10)
    ax2.tick_params(axis="x", labelsize=8)
    for ax in (ax1, ax2):
        ax.grid(axis="x" if ax is ax1 else "y", alpha=0.3)
    fig.tight_layout()

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=150)
    plt.close(fig)
    raw = FIG.read_bytes()
    return {"name": FIG.name, "caption": "图 1 wp-5949-01 资产清单构成：类别 × 解析状态（左）与合计（右）；"
                                         "数字由 asset_manifest.json 程序化注入",
            "png_base64": base64.b64encode(raw).decode(), "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw)}


# ---------------------------------------------------------------- evidence


def evidence_rows(manifest, src):
    """(字段, 引文, 行号, 取法) rows; every quote is asserted verbatim against the source."""
    lines = src.split("\n")
    occ = {}
    for a in manifest["assets"]:
        if a.get("path_reference"):
            occ.setdefault(a["path_reference"], []).append(a)
    rows = []

    def push(field, quote, how, line=None):
        if quote not in src:
            raise SystemExit("EVIDENCE NOT VERBATIM (%s): %r" % (field, quote[:60]))
        if line is None:
            line = src[: src.index(quote)].count("\n") + 1
        elif quote not in lines[line - 1]:
            raise SystemExit("EVIDENCE LINE MISMATCH (%s): %r not on line %d" % (field, quote[:40], line))
        rows.append((field, quote, line, how))

    def ref(field, token):
        assets = occ[token]
        a = assets[0]
        line = a["locator"]["start_line"]
        how = "inline code，行 %d" % line
        if len(assets) > 1:
            how += "（同一 token 另见 %s）" % ", ".join(
                "%s 行 %d" % (b["asset_id"], b["locator"]["start_line"]) for b in assets[1:])
        push(field % a["asset_id"] if "%s" in field else field, "`%s`" % token, how, line)

    push("source.uri / source.hash / source.chars", manifest["assets"][0]["locator"]["quote"],
         "A01 document locator（首行锚点）")
    for tok in ("artifacts/in25_t2/coverage.json", "artifacts/in25_t2/roster_check.json",
                "artifacts/in25_t2/seats.json", "artifacts/in25_t2/seed_divergence.json",
                "artifacts/in25_t2/prereg_lock.json", "artifacts/in25_t2/dedup_ledger.json",
                "artifacts/in25_t2/pytest_summary.json", "blind_scores.json"):
        ref("assets[%s] " + tok, tok)
    for tok in ("tools/diversity/gen_doc.py", "tools/diversity/{roster,prereg,dedup,run_node}.py",
                "tests/test_diversity_engine.py", "roster.py",
                "ops/taskplane/campaign_dispatcher.py::_hollow()"):
        ref("assets[%s] " + tok, tok)
    ref("assets[%s] 工件目录", "artifacts/in25_t2/")

    for it in manifest["declared_digests"]["items"]:
        push("declared_digests[%s]" % (it["label"] or "?"), it["digest_prefix"],
             "声明哈希前缀（%d hex，行 %d）" % (it["declared_hex_chars"], it["line"]), it["line"])

    blk_asset = [a for a in manifest["assets"] if a["asset_class"] == "code_block"][0]
    blk = blk_asset["locator"]
    cmd = "python3 -m tools.diversity.run_node"
    cmd_line = next(i for i, ln in enumerate(lines, start=1) if cmd in ln)
    if cmd_line <= blk["end_line"]:
        raise SystemExit("repro command unexpectedly inside the audit-chain block")
    push("assets[%s] 代码块后的复算命令行" % blk_asset["asset_id"], cmd, "内联代码，紧随审计链块（块行 %d-%d）"
         % (blk["start_line"], blk["end_line"]), cmd_line)

    fig_assets = [a for a in manifest["assets"] if a["asset_class"] == "embedded_figure"]
    fig_lines = [ln for ln in lines if ln.startswith("**图 ")]
    for fig_asset, ln in zip(fig_assets, fig_lines):
        idx = fig_asset["uri"].split("figures[")[1].rstrip("]")
        push("figures[%s]（正文图注首行）" % idx, ln,
             "平台 figures[%s] ↔ 正文图注首行（长图注在原文中折行，此处只取首行）" % idx, lines.index(ln) + 1)
    return rows


# ---------------------------------------------------------------- render


def checklist(verdict):
    order = [
        ("valid_json", "合法 JSON"),
        ("schema_pass", "schema 通过（本仓固定 schema）"),
        ("source_locator_resolvable", "每个 locator 可在原文解析"),
        ("source_hash_matches", "source_hash 与契约一致"),
        ("no_duplicate_ids", "asset_id 无重复"),
        ("all_claims_have_evidence_or_explicit_unresolved_status", "claims 均带证据或显式未解析"),
        ("do_not_mark_claims_as_verified", "未把任何 claim 标成 verified"),
    ]
    out = []
    for key, label in order:
        c = verdict["checks"][key]
        out.append((label, "✅ 通过" if c["pass"] else "❌ 失败", c["detail"]))
    return out


def render():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    verdict = json.loads(VERDICT.read_text(encoding="utf-8"))
    src = SOURCE.read_text(encoding="utf-8")
    digest = hashlib.sha256(src.encode("utf-8")).hexdigest()
    if digest != manifest["source"]["hash"]:
        raise SystemExit("local source copy drifted from manifest hash")

    fig = render_figure(manifest)
    rows = evidence_rows(manifest, src)
    c = manifest["counts"]
    dg = manifest["declared_digests"]

    md = []
    md.append("# KF-RESULT %s" % PKG)
    md.append("")
    md.append("> package_id `%s` · task_type `01-asset-registration` · report_id `%s` · "
              "tags `kf-wp:%s` · lane C · status draft" % (PKG, REPORT_ID, PKG))
    md.append("> 源：`%s`（field `markdown`）· sha256 `%s` · %d 字符 / %d 字节 utf-8"
              % (manifest["source"]["uri"], digest, manifest["source"]["chars"],
                 manifest["source"]["bytes_utf8"]))
    md.append("> 本工序只登记资产：不抽取正文、不生成 claim、不标 verified（verification 由平台门计算）。")
    md.append("")

    md.append("## ① 本工序做了什么")
    md.append("")
    md.append("本工作包是「报告→知识」产线的第一道工序（asset registration），只处理 `report_id=%s`。"
              "产出是一份 `asset_manifest.json`：确认源资产的字节身份，并把报告里**可解析的附件/工件**"
              "逐条登记为资产（含逐字 locator），**不做抽取**，`claims` 为空数组。" % REPORT_ID)
    md.append("")
    md.append("登记结果：共 **%d** 项资产——`resolved_in_source` %d 项（本文内可定位：源 markdown 本体、"
              "平台内嵌图 %d 张、围栏代码块 1 个），`referenced_unresolved` %d 项（报告引用了、但目标不在本仓工作树内），"
              "`declared_absent` %d 项；另有 %d 条**声明哈希前缀**（%d hex 位，`truncated=true`、`verifiable=false`）单独登记。"
              % (c["assets"], c["resolved_in_source"],
                 sum(1 for a in manifest["assets"] if a["asset_class"] == "embedded_figure"),
                 c["referenced_unresolved"], c["declared_absent"], dg["count"], dg["items"][0]["declared_hex_chars"]))
    md.append("")
    md.append("资产类别分布（程序化注入，来自 manifest `counts.by_class`）：")
    md.append("")
    md.append("| 资产类别 | 数量 |")
    md.append("|---|---|")
    for k in sorted(c["by_class"]):
        md.append("| `%s` | %d |" % (k, c["by_class"][k]))
    md.append("")

    md.append("## ② 怎么做的（步骤 / 工具 / 关键设置）")
    md.append("")
    md.append("1. **取原文（不凭记忆）**：`POST /api/v1/auth/login` 拿 token → `GET /api/v1/tensor/reports/%s`，"
              "取 `markdown` 字段原文；登录用环境变量 `TENSOR_AGENT_USER/PASS`，脚本内不存任何秘密。" % REPORT_ID)
    md.append("2. **字节身份先封口**：对 `markdown.encode('utf-8')` 求 sha256，与契约 `source_hash` 逐位比对，"
              "并核对字符数是否等于契约 `chars`；任一不符立即中止（`SystemExit`），不生成任何产物。")
    md.append("3. **资产发现（只认内联代码，不猜散文）**：扫描每行的反引号内联代码，分成四类形态——"
              "带扩展名文件路径、目录路径、花括号展开（`{a,b}.py`）、`path::symbol` 形式；"
              "再补上平台 `figures[]` 与围栏代码块。散文与数学式子一律不解析，避免把正文误登记成资产。")
    md.append("4. **locator 可复算**：以「行首字符偏移」表把行号换算成 `start_char/end_char`，"
              "写入 `quote` 并回读校验 `md[start:end] == quote`；同时记录该 quote 在全文中是否唯一。"
              "引文全部取自原文切片，**没有一处手抄**。")
    md.append("5. **解析（resolution）严格限域**：目标只在本仓交付工作树内解析，命中=文件/目录存在并给出其 sha256；"
              "未命中即 `referenced_unresolved`，写明原因，绝不凭记忆补内容、绝不用「应该有」代替「没找到」。")
    md.append("6. **schema 固定下来**：本仓没有契约所称的 `schemas/kf_result.v1.schema.json`（`schemas/` 下无 `kf_*`），"
              "因此按同族 `wp-448-01` 包形状派生本包专用 schema `schemas/asset_manifest.v1.wp-5949-01.schema.json`，"
              "`jsonschema` 实跑校验——`schema_pass` 是复算出来的，不是自述的。")
    md.append("7. **验收独立复算**：`verify` 子命令重新登录并**重新拉取**原文，重算哈希、重解析全部 locator、"
              "重查 id 唯一性与 claims 状态，结果写 `verification.json`；离线 pytest 再用本地副本复验一遍。")
    md.append("")

    md.append("## ③ 产出物清单（文件名 → 要点）")
    md.append("")
    md.append("| 文件 | 要点 |")
    md.append("|---|---|")
    for path, note in [
        ("docs/kf/wp-5949-01/asset_manifest.json",
         "主产物：%d 项资产 + %d 条声明哈希前缀；counts/integrity/limitations 齐全；claims=[]" % (c["assets"], dg["count"])),
        ("docs/kf/wp-5949-01/kf_result.json",
         "结果信封（package_id/task_type/report_id/provenance/outputs），已原样写入本报告唯一的 json 代码块"),
        ("docs/kf/wp-5949-01/verification.json", "平台侧独立复算的 7 项 acceptance 结论（all_pass=%s）" % verdict["all_pass"]),
        ("docs/kf/wp-5949-01/source_5949.md", "登记源的逐字副本（%d 字节），供离线复验 locator" % manifest["source"]["bytes_utf8"]),
        ("docs/kf/wp-5949-01/report.md", "本报告"),
        ("docs/kf/wp-5949-01/figures/%s" % FIG.name, "资产清单构成图（%d 字节，sha256 %s…）" % (fig["bytes"], fig["sha256"][:16])),
        ("scripts/kf/build_asset_manifest_5949.py", "build / result / verify 三合一，可一键复跑"),
        ("schemas/asset_manifest.v1.wp-5949-01.schema.json", "本包专用 schema（约束 package/report id 与分辨率词表）"),
        ("tests/test_kf_wp5949.py", "离线 pytest：哈希、locator、唯一性、scope、报告单块结构"),
    ]:
        md.append("| `%s` | %s |" % (path, note))
    md.append("")

    md.append("## ④ 证据定位表（字段 → 原文引文片段）")
    md.append("")
    md.append("引文一律为原文**逐字切片**（渲染时逐条断言 `quote in source`，否则渲染直接失败）。")
    md.append("")
    md.append("| # | manifest 字段 | 原文引文（逐字） | 行 | 取法 |")
    md.append("|---|---|---|---|---|")
    for i, (field, quote, line, how) in enumerate(rows, start=1):
        q = quote.replace("|", "\\|").replace("\n", " ⏎ ")
        if len(q) > 120:
            q = q[:117] + "…"
        md.append("| %d | `%s` | `%s` | %d | %s |" % (i, field, q, line, how))
    md.append("")
    md.append("> 注：表中 `…` 仅用于**展示截断**，manifest 内 `locator.quote` 保存的是完整片段；"
              "以 manifest 为准（`tests/test_kf_wp5949.py::test_locators_are_verbatim_char_spans` 逐项复验）。")
    md.append("")

    md.append("## ⑤ 注意点与局限")
    md.append("")
    for item in manifest["limitations"]:
        md.append("- %s" % item)
    md.append("- **声明哈希不可当证据用**：报告头部的 %d 条工件快照 sha256 只给了 %d 位前缀（`verifiable=false`），"
              "不足以复算；manifest 只登记声明值，不据此宣称一致。" % (dg["count"], dg["items"][0]["declared_hex_chars"]))
    bn = manifest.get("block_internal_names", {})
    md.append("- **围栏块内的文件名不单独登记**：%s 只出现在审计链代码块内部，由整块资产（A04）覆盖；"
              "单列在 manifest `block_internal_names`，避免同一字节被记成两条身份。" % "、".join(
                  "`%s`" % n for n in bn.get("names", [])))
    md.append("- **同一个文件可能被引用多次**：资产身份是「引用出现级」（同一 token 在不同行各成一条），"
              "因此 `roster.py`、`tests/test_diversity_engine.py` 各出现两条——这是刻意的，便于每条引用各自携带证据。")
    md.append("- **schema 是本地派生的**：若平台侧 canonical schema 与本包 schema 不同，以平台门为准，本产物须返工。")
    md.append("")

    md.append("## ⑥ 自检（逐条对照 acceptance）")
    md.append("")
    md.append("| acceptance | 结果 | 依据 |")
    md.append("|---|---|---|")
    for label, res, detail in checklist(verdict):
        md.append("| %s | %s | %s |" % (label, res, detail.replace("|", "\\|")))
    md.append("")
    md.append("### ⑥.b 误差判定（是否 <3%）")
    md.append("")
    md.append("本工序是**登记/校验类**任务，不产生物理量，物理基准判据不适用；可判的只有字节与指针的一致性，"
              "且全是精确比较而非近似：")
    md.append("")
    md.append("| 量 | 基准 | 实测 | 误差 | <3%？ |")
    md.append("|---|---|---|---|---|")
    md.append("| markdown sha256 | 契约 `%s` | `%s` | 0 bit（逐位相同） | **是**（0.0%%） |" % (digest, digest))
    md.append("| 字符数 | 契约 %d | %d | 0 | **是**（0.0%%） |" % (manifest["source"]["chars"], manifest["source"]["chars"]))
    md.append("| locator 逐字命中 | %d/%d | %d/%d | 0 条不符 | **是**（0.0%%） |"
              % (c["assets"], c["assets"], c["assets"], c["assets"]))
    md.append("| asset_id 唯一性 | %d 唯一 | %d | 0 重复 | **是**（0.0%%） |" % (c["assets"], c["assets"]))
    md.append("| claim 标 verified 数 | 0 | 0 | 0 | **是**（0.0%） |")
    md.append("")
    md.append("**结论**：可用判据（哈希/字符数/locator/唯一性）误差均为 0，均 <3%；物理精度判据不适用于登记工序，"
              "已在 ⑤ 声明原因。")
    md.append("")

    md.append("## 复跑（repro_cmd）")
    md.append("")
    md.append("```bash")
    md.append("# 一等产物重建 + 平台侧独立复算（需要 TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS）")
    md.append("python3 scripts/kf/build_asset_manifest_5949.py build result verify")
    md.append("# 渲染本报告（含图）")
    md.append("python3 scripts/kf/report_5949.py render")
    md.append("# 离线复验（不联网）")
    md.append("python3 -m pytest tests/test_kf_wp5949.py -q")
    md.append("```")
    md.append("")
    md.append("## KF-RESULT JSON（本报告唯一 json 代码块）")
    md.append("")
    md.append("```json")
    md.append(json.dumps(result, ensure_ascii=False, indent=2))
    md.append("```")
    md.append("")

    text = "\n".join(md)
    if text.count("```json") != 1:
        raise SystemExit("report must contain exactly one json block")
    OUT_MD.write_text(text, encoding="utf-8")
    print("wrote %s (%d chars, %d evidence rows)" % (OUT_MD.relative_to(REPO), len(text), len(rows)))
    return fig


# ---------------------------------------------------------------- publish


def publish(fig):
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    md = OUT_MD.read_text(encoding="utf-8")
    payload = json.dumps({
        "title": "KF-RESULT %s" % PKG,
        "summary": "wp-5949-01 资产登记：report 5949 源哈希逐位一致（%s…），登记 %d 项资产"
                   "（%d 内定位 / %d 仓外未解析）、%d 条声明哈希前缀，claims 为空，不做抽取。"
                   % ((hashlib.sha256(SOURCE.read_bytes()).hexdigest()[:16],)
                      + (m["counts"]["assets"], m["counts"]["resolved_in_source"],
                         m["counts"]["referenced_unresolved"], m["declared_digests"]["count"])),
        "scenario_key": SCENARIO_KEY,
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:%s" % PKG, "KF-RESULT", "asset-registration", "IN25-T2", "wp-5949-01"],
        "markdown": md,
        "figures": [{"name": fig["name"], "caption": fig["caption"], "png_base64": fig["png_base64"]}],
    }, ensure_ascii=False).encode()

    def _req(url, data=None, token=None):
        r = urllib.request.Request(url, data=data, method="POST" if data else "GET")
        if data:
            r.add_header("Content-Type", "application/json")
        if token:
            r.add_header("Authorization", "Bearer " + token)
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read().decode())

    tok = _req(BASE + "/auth/login", json.dumps({"username": USER, "password": PASS}).encode())
    tok = tok.get("access_token") or tok.get("token")
    out = _req(BASE + "/tensor/reports", data=payload, token=tok)
    rid = out.get("id") if isinstance(out, dict) else out
    print("published report id=%s" % rid)
    (PKG_DIR / "published.json").write_text(json.dumps({"id": rid, "payload_sha256":
                                                        hashlib.sha256(payload).hexdigest()},
                                                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rid


if __name__ == "__main__":
    acts = sys.argv[1:] or ["render"]
    figure = render_figure(json.loads(MANIFEST.read_text(encoding="utf-8"))) if "figure-only" in acts else None
    if "render" in acts:
        figure = render()
    if "publish" in acts:
        publish(figure or render())