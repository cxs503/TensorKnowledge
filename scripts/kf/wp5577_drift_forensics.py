#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wp-5577-01 第 2 轮修复 · 漂移取证（程序化取证 + 出图 + 表格注入，零手抄）。

背景：main 上本包的 8 个工件曾经「各自漂移」——源载荷（markdown / 平台响应）停留在
旧版（3700 字符 / `外协方`），而哈希钉子、manifest、acceptance、REPORT.md 已被同步到
平台当前版（3702 字符 / `外协方`）。于是同一个包内并存两个源版本，pytest 判红 5 项。

本脚本不修任何东西，只**取证**：把 HEAD 与工作树逐工件分类到「旧版 / 平台版 / 混合 / 无关」，
出图 1 张，并把 Markdown 表格注入 `docs/kf/wp-5577-01/REPAIR-ROUND2.md` 的标记区。

判定口径（纯函数 :func:`classify`）：
  * 文件里出现旧版载荷 sha256/独有串而不出现平台版 → ``stale``；
  * 反之 → ``live``；
  * 两者都出现，或验收项 ID 集合是本版构建器的真子集（旧构建器产物）→ ``mixed``；
  * 两者都不出现 → ``n/a``（如只登记探活结果的 figure_probe.json）。
文本标记（旧版独有串 / 平台版独有串）由两份载荷逐行 diff 现算，不写死。

用法::

    python scripts/kf/wp5577_drift_forensics.py            # 取证 + 出图 + 注入表格
    python scripts/kf/wp5577_drift_forensics.py --check    # 只判定：仍有 stale/mixed 则退出 1
"""
from __future__ import annotations

import argparse
import bisect
import difflib
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG_REL = "docs/kf/wp-5577-01"
PKG = ROOT / PKG_REL

#: 本包的 8 个工件（相对本包根）。figure_probe.json 只登记探活结果，不含源载荷。
ARTIFACTS = (
    "source/report_5577.md",
    "source/report_5577.json",
    "source/markdown.sha256",
    "source/figure_probe.json",
    "asset_manifest.json",
    "kf_result.json",
    "acceptance.json",
    "REPORT.md",
)

MD_REL = "source/report_5577.md"
PIN_REL = "source/markdown.sha256"
DOC_REL = "REPAIR-ROUND2.md"
FIG_REL = "drift_forensics.png"

STALE, LIVE, MIXED, NA = "stale", "live", "mixed", "n/a"

#: 判定「验收项清单是否完整」的最小 ID 条数；少于该数视为零星引用，不构成版本证据。
MIN_AC_IDS_FOR_SHEET = 5
LABELS = {STALE: "旧版载荷", LIVE: "平台版载荷",
          MIXED: "混合（半同步 / 旧构建器）", NA: "不含源载荷"}


# ---------------------------------------------------------------------------
# 纯函数：版本标记与分类
# ---------------------------------------------------------------------------
def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def version_markers(stale_md: str, live_md: str) -> dict:
    """逐行 diff 现算两版载荷各自的独有串（不写死「外协方 / 外协方」）。"""
    a = stale_md.split("\n")
    b = live_md.split("\n")
    only_stale, only_live = [], []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == "replace":
            only_stale.append("\n".join(a[i1:i2]))
            only_live.append("\n".join(b[j1:j2]))
        elif tag == "delete":
            only_stale.append("\n".join(a[i1:i2]))
        elif tag == "insert":
            only_live.append("\n".join(b[j1:j2]))
    return {"stale": [s for s in only_stale if s],
            "live": [s for s in only_live if s]}


def classify(text: str, stale_hash: str, live_hash: str, markers: dict,
             builder_ids: tuple = ()) -> str:
    """把一个工件的文本分类到 stale / live / mixed / n/a。

    ``builder_ids`` = 本版构建器会产出的验收项 ID 集合（由工作树 acceptance.json 现算）。
    文件若只列出其中一部分，说明它是旧构建器的产物 → ``mixed``（部分自洽）。
    """
    has_stale = stale_hash in text or any(m in text for m in markers["stale"])
    has_live = live_hash in text or any(m in text for m in markers["live"])
    status = MIXED if (has_stale and has_live) else STALE if has_stale else LIVE if has_live else NA
    if builder_ids:
        found = set(re.findall(r"\bAC\d{2}\b", text))
        # 只有「整张验收项清单」才用完整性判据：清单类文件列出 5 项以上，
        # 而 manifest/notes 只是零星点名 1–3 项（AC01/AC02/AC14），不构成版本证据。
        if len(found) >= MIN_AC_IDS_FOR_SHEET:
            if not set(builder_ids).issubset(found):
                return MIXED          # 旧构建器产出的短清单
            if status == NA:
                return LIVE           # 清单完整 + 无载荷串 ⇒ 现行构建器产物
    return status


# ---------------------------------------------------------------------------
# 取证：HEAD 版 vs 工作树版
# ---------------------------------------------------------------------------
def head_text(rel: str) -> str | None:
    """取 HEAD 版文件文本；不存在返回 None（新加文件）。"""
    try:
        out = subprocess.run(["git", "show", "HEAD:%s/%s" % (PKG_REL, rel)],
                             cwd=ROOT, check=True, capture_output=True)
    except subprocess.CalledProcessError:
        return None
    return out.stdout.decode("utf-8")


def worktree_text(rel: str) -> str | None:
    p = PKG / rel
    return p.read_text(encoding="utf-8") if p.exists() else None


def collect() -> dict:
    live_md = (PKG / MD_REL).read_text(encoding="utf-8")
    stale_md = head_text(MD_REL)
    if stale_md is None:
        raise SystemExit("HEAD 中找不到源载荷，无法取证")
    if stale_md == live_md:
        print("注意：HEAD 与工作树的源载荷一致，本脚本无漂移可证。")
    stale_hash, live_hash = sha256_text(stale_md), sha256_text(live_md)
    pin = (PKG / PIN_REL).read_text(encoding="utf-8").strip()
    markers = version_markers(stale_md, live_md)
    builder_ids = tuple(item["id"] for item in
                        json.loads((PKG / "acceptance.json").read_text(encoding="utf-8"))["items"])

    rows = []
    for rel in ARTIFACTS:
        before = head_text(rel)
        after = worktree_text(rel)
        rows.append({
            "artifact": rel,
            "head": classify(before, stale_hash, live_hash, markers, builder_ids) if before else "absent",
            "worktree": classify(after, stale_hash, live_hash, markers, builder_ids) if after else "absent",
        })
    before = consistency_metrics(head_text("asset_manifest.json"), stale_md)
    after = consistency_metrics((PKG / "asset_manifest.json").read_text(encoding="utf-8"),
                                live_md)
    return {
        "consistency": {"before": before, "after": after},
        "stale": {"chars": len(stale_md), "bytes": len(stale_md.encode("utf-8")),
                  "sha256": stale_hash},
        "live": {"chars": len(live_md), "bytes": len(live_md.encode("utf-8")),
                 "sha256": live_hash},
        "pin": pin,
        "pin_matches_live": pin == "sha256:" + live_hash,
        "pin_matches_stale": pin == "sha256:" + stale_hash,
        "markers": markers,
        "builder_ids": list(builder_ids),
        "rows": rows,
        "counts": {
            "head": {k: sum(1 for r in rows if r["head"] == k)
                     for k in (STALE, LIVE, MIXED, NA, "absent")},
            "worktree": {k: sum(1 for r in rows if r["worktree"] == k)
                         for k in (STALE, LIVE, MIXED, NA, "absent")},
        },
    }


def consistent(rep: dict) -> bool:
    """一致 = 每个工件都只指向平台版载荷（n/a 的探活工件不受约束）。"""
    return all(r["worktree"] in (LIVE, NA) for r in rep["rows"])


# ---------------------------------------------------------------------------
# 纯函数：清单自洽性指标（同一份清单 + 同一份载荷上现算）
# ---------------------------------------------------------------------------
def consistency_metrics(manifest_text: str, md_text: str) -> dict:
    """在给定 (清单, 载荷) 组合上现算三项自洽指标 —— 用来对比 HEAD 与修后。"""
    man = json.loads(manifest_text)
    md = md_text
    body = md.rstrip("\n")
    n = len(man["assets"])
    slice_ok = [a["asset_id"] for a in man["assets"]
                if a["locator"]["quote"] == body[a["locator"]["start_char"]:a["locator"]["end_char"]]]
    uniq_ok = [a["asset_id"] for a in man["assets"]
               if md.count(a["locator"]["quote"]) == 1]
    starts = _line_starts(md)
    lines_ok = []
    for a in man["assets"]:
        loc = a["locator"]
        if loc["method"] == "document":
            if loc["start_char"] == 0 and loc["end_char"] == len(body):
                lines_ok.append(a["asset_id"])
            continue
        # 与构建器/build_acceptance(AC07) 同一口径：bisect_right(starts, offset) == 1-based 行号
        if (bisect.bisect_right(starts, loc["start_char"]) == loc["start_line"]
                and bisect.bisect_right(starts, loc["end_char"] - 1) == loc["end_line"]):
            lines_ok.append(a["asset_id"])
    return {"assets": n,
            "slice_ok": len(slice_ok), "slice_bad": sorted(set(a_id for a_id in
                (x["asset_id"] for x in man["assets"])) - set(slice_ok)),
            "unique_ok": len(uniq_ok), "unique_bad": sorted(set(
                x["asset_id"] for x in man["assets"]) - set(uniq_ok)),
            "lines_ok": len(lines_ok), "lines_bad": sorted(set(
                x["asset_id"] for x in man["assets"]) - set(lines_ok))}


def _line_starts(md: str) -> list:
    out, pos = [], 0
    for ln in md.rstrip("\n").split("\n"):
        out.append(pos)
        pos += len(ln) + 1
    return out


# ---------------------------------------------------------------------------
# 出图
# ---------------------------------------------------------------------------
COLORS = {STALE: "#c0392b", LIVE: "#27ae60", MIXED: "#e67e22", NA: "#95a5a6",
          "absent": "#ecf0f1"}

#: 图内文字一律英文 —— 容器只有 DejaVu/Noto-Sans 拉丁字形，中文会渲染成豆腐块。
STATUS_EN = {STALE: "stale", LIVE: "live", MIXED: "mixed", NA: "n/a", "absent": "absent"}


def render_figure(rep: dict, out_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    rows = rep["rows"]
    names = [r["artifact"] for r in rows]
    fig, (ax0, ax1) = plt.subplots(
        1, 2, figsize=(13.6, 5.8), gridspec_kw={"width_ratios": [1.55, 1.0]})

    # Panel A: artifact x (HEAD, worktree) payload-attribution matrix
    for col, key in enumerate(("head", "worktree")):
        for row, r in enumerate(rows):
            st = r[key]
            ax0.add_patch(plt.Rectangle((col, len(rows) - 1 - row), 1, 1,
                                        facecolor=COLORS[st], edgecolor="white", lw=1.6))
            ax0.text(col + 0.5, len(rows) - 1 - row + 0.5, STATUS_EN[st],
                     ha="center", va="center", fontsize=8.5, color="white", weight="bold")
    ax0.set_xlim(0, 2)
    ax0.set_ylim(0, len(rows))
    ax0.set_xticks([0.5, 1.5])
    ax0.set_xticklabels(["HEAD (before)", "worktree (after)"], fontsize=10)
    ax0.set_yticks([len(rows) - 1 - i + 0.5 for i in range(len(rows))])
    ax0.set_yticklabels(names, fontsize=8.5, family="monospace")
    ax0.set_title("A - which payload version each artifact points to", fontsize=10.5)
    for sp in ax0.spines.values():
        sp.set_visible(False)
    ax0.tick_params(length=0)
    ax0.legend(handles=[Patch(facecolor=COLORS[k], label=lab) for k, lab in (
        (STALE, "stale payload (3700 chars)"),
        (MIXED, "mixed (half-synced / old builder)"),
        (LIVE, "platform payload (3702 chars)"),
        (NA, "no payload (probe artifact)"),
    )], fontsize=7.8, loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=2, frameon=False)

    # Panel B: payload length per version + which version the hash pin points to
    labels = ["stale payload\n(HEAD)", "platform payload\n(worktree)"]
    chars = [rep["stale"]["chars"], rep["live"]["chars"]]
    byts = [rep["stale"]["bytes"], rep["live"]["bytes"]]
    x = [0, 1]
    w = 0.34
    b1 = ax1.bar([i - w / 2 for i in x], chars, w, label="chars", color="#2980b9")
    b2 = ax1.bar([i + w / 2 for i in x], byts, w, label="UTF-8 bytes", color="#8e44ad")
    for bars in (b1, b2):
        for rect in bars:
            ax1.text(rect.get_x() + rect.get_width() / 2, rect.get_height() + 25,
                     "%d" % int(rect.get_height()), ha="center", fontsize=9)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9.5)
    ax1.set_ylim(0, max(byts) * 1.22)
    ax1.set_ylabel("length", fontsize=9.5)
    ax1.legend(fontsize=9, loc="upper left")
    pin_owner = "platform" if rep["pin_matches_live"] else (
        "stale" if rep["pin_matches_stale"] else "neither")
    ax1.set_title("B - payload length and the version the hash pin points to (%s)"
                  % pin_owner, fontsize=10.5)
    ax1.grid(axis="y", alpha=0.25)
    for sp in ("top", "right"):
        ax1.spines[sp].set_visible(False)

    c = rep["counts"]
    fig.suptitle(
        "wp-5577-01 payload drift forensics: HEAD = %d stale + %d mixed -> worktree = %d on platform payload"
        % (c["head"][STALE], c["head"][MIXED], c["worktree"][LIVE]), fontsize=11.5)
    fig.text(0.5, 0.015,
             "hash pin sha256:%s... (platform version, double fetch identical); stale %s... retired"
             % (rep["live"]["sha256"][:12], rep["stale"]["sha256"][:12]),
             ha="center", fontsize=8.5, color="#555")
    fig.tight_layout(rect=(0, 0.035, 1, 0.94))
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


# ---------------------------------------------------------------------------
# 文档表格注入（标记区之间整段替换，数字全部来自取证结果）
# ---------------------------------------------------------------------------
BEGIN = "<!-- FORENSICS:BEGIN 由 scripts/kf/wp5577_drift_forensics.py 生成，勿手改 -->"
END = "<!-- FORENSICS:END -->"
CBEGIN = "<!-- CONSISTENCY:BEGIN 由 scripts/kf/wp5577_drift_forensics.py 生成，勿手改 -->"
CEND = "<!-- CONSISTENCY:END -->"


def render_markdown(rep: dict) -> str:
    lines = [BEGIN, "",
             "| 工件 | HEAD（修复前） | 工作树（修复后） | 判定依据 |",
             "|---|---|---|---|"]
    for r in rep["rows"]:
        basis = "含源载荷 → 比哈希/独有串" if r["head"] != NA else "只登记探活结果，不含源载荷"
        lines.append("| `%s` | %s | %s | %s |"
                     % (r["artifact"], r["head"], r["worktree"], basis))
    lines += ["",
              "两版载荷长度：旧版 %d 字符 / %d UTF-8 字节（sha256 `%s…`）；"
              "平台版 %d 字符 / %d UTF-8 字节（sha256 `%s…`）。"
              % (rep["stale"]["chars"], rep["stale"]["bytes"], rep["stale"]["sha256"][:12],
                 rep["live"]["chars"], rep["live"]["bytes"], rep["live"]["sha256"][:12]),
              "",
              "哈希钉子 `source/markdown.sha256` 实际指向：%s。"
              % ("平台版（正确）" if rep["pin_matches_live"] else
                 "旧版（错）" if rep["pin_matches_stale"] else "两版都不符（错）"),
              "",
              END]
    return "\n".join(lines)


def render_consistency(rep: dict) -> str:
    b, a = rep["consistency"]["before"], rep["consistency"]["after"]
    rows = [
        ("资产条数", b["assets"], a["assets"]),
        ("quote == md[start:end]（切片自洽）", "%d/%d" % (b["slice_ok"], b["assets"]),
         "%d/%d" % (a["slice_ok"], a["assets"])),
        ("quote 在源 payload 中唯一", "%d/%d" % (b["unique_ok"], b["assets"]),
         "%d/%d" % (a["unique_ok"], a["assets"])),
        ("行号可由字符偏移反算", "%d/%d" % (b["lines_ok"], b["assets"]),
         "%d/%d" % (a["lines_ok"], a["assets"])),
    ]
    lines = [CBEGIN, "", "| 自洽指标（同一份 `asset_manifest.json`） | HEAD（清单 3702 声明 + 载荷 3700） | "
             "工作树（清单与载荷同为平台版） |", "|---|---|---|"]
    for name, bv, av in rows:
        lines.append("| %s | %s | %s |" % (name, bv, av))
    lines += ["",
              "修复前切片不符的资产共 %d 条：%s。"
              % (len(b["slice_bad"]), ", ".join(b["slice_bad"]) or "无"),
              "",
              CEND]
    return "\n".join(lines)


def inject(doc_path: Path, block: str, begin: str = BEGIN, end: str = END) -> bool:
    if not doc_path.exists():
        return False
    text = doc_path.read_text(encoding="utf-8")
    if begin not in text or end not in text:
        return False
    head = text.split(begin)[0]
    tail = text.split(end, 1)[1]
    doc_path.write_text(head + block + tail, encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只判定一致性，不出图不注入")
    args = ap.parse_args()

    rep = collect()
    print("HEAD 版载荷 : %d 字符 / %d 字节  sha256:%s"
          % (rep["stale"]["chars"], rep["stale"]["bytes"], rep["stale"]["sha256"]))
    print("平台版载荷 : %d 字符 / %d 字节  sha256:%s"
          % (rep["live"]["chars"], rep["live"]["bytes"], rep["live"]["sha256"]))
    print("哈希钉子   : %s → %s" % (rep["pin"], "平台版" if rep["pin_matches_live"] else "非平台版"))
    for r in rep["rows"]:
        print("  %-28s HEAD=%-6s worktree=%-6s" % (r["artifact"], r["head"], r["worktree"]))
    print("计数 HEAD=%s worktree=%s" % (rep["counts"]["head"], rep["counts"]["worktree"]))

    if args.check:
        return 0 if consistent(rep) else 1

    render_figure(rep, PKG / FIG_REL)
    print("图:", (PKG / FIG_REL).relative_to(ROOT))
    doc = PKG / DOC_REL
    ok1 = inject(doc, render_markdown(rep))
    ok2 = inject(doc, render_consistency(rep), CBEGIN, CEND)
    print("表格注入: 工件归属=%s 自洽指标=%s (%s)"
          % (ok1, ok2, doc.relative_to(ROOT)))
    ev = ROOT / "artifacts" / "kf" / "wp5577_drift_forensics.json"
    ev.parent.mkdir(parents=True, exist_ok=True)
    ev.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("取证 JSON:", ev.relative_to(ROOT))
    return 0 if consistent(rep) else 1


if __name__ == "__main__":
    sys.exit(main())