#!/usr/bin/env python3
"""wp-2506-01 图件：资产登记图（左=资产/状态/偏移，中=机读自检，右=源身份事实）。

说明：工序 01 是纯登记工序，不产生任何物理场量，因此本单没有场量云图、也没有与解析解/实验的
比较曲线（上游报告 2506 的 dissipativity-sweep.png 字节不可得，本工序不重绘）。
图中所有点均来自 asset_manifest.json / checks.json，无手填数值。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PKG = "wp-2506-01"
ART = ROOT / "artifacts" / "kf" / PKG
MIRROR = ROOT / "knowledge" / "kf" / PKG

STATUS_COLOR = {
    "resolved": "#2f7d32",
    "declared_unresolvable": "#c77700",
    "unresolved": "#b00020",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    out_dir = args.out or ART
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    man = json.loads((out_dir / "asset_manifest.json").read_text(encoding="utf-8"))
    checks = json.loads((out_dir / "checks.json").read_text(encoding="utf-8"))

    fig, axes = plt.subplots(
        1, 3, figsize=(19.5, 9.2), gridspec_kw={"width_ratios": [2.45, 1.15, 1.15]}
    )

    # ---- 左：资产登记图
    ax = axes[0]
    assets = man["assets"]
    n = len(assets)
    for i, a in enumerate(assets):
        y = n - i
        col = STATUS_COLOR[a["status"]]
        off = a.get("locator", {}).get("offset_chars")
        ax.plot([0], [y], marker="o", color=col, ms=9, zorder=3)
        label = "%s  [%s]" % (a["asset_id"].replace("asset-2506-", ""), a["kind"])
        ax.text(0.06, y, label, va="center", fontsize=8.4, family="monospace")
        ax.text(2.28, y, "%s" % (off if off is not None else "n/a"), va="center",
                ha="right", fontsize=8.4, color=col, family="monospace")
    ax.axvline(0.03, color="#999", lw=0.8)
    ax.set_xlim(-0.05, 2.35)
    ax.set_ylim(0.2, n + 0.8)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_title(
        "report 2506 asset registry — %d assets (%s), @n = char offset in markdown"
        % (n, ", ".join("%s=%d" % kv for kv in sorted(man["identity_facts"]["asset_status_distribution"].items()))),
        fontsize=10.5, loc="left",
    )
    for s, c in STATUS_COLOR.items():
        ax.plot([], [], "o", color=c, label=s)
    ax.legend(loc="lower right", fontsize=8, frameon=False)

    # ---- 中：机读自检
    ax = axes[1]
    cs = checks["checks"]
    ys = range(len(cs) - 1, -1, -1)
    for y, c in zip(ys, cs):
        col = "#2f7d32" if c["passed"] else "#b00020"
        ax.barh(y, 1, color=col, alpha=0.85, height=0.62)
        ax.text(-0.04, y, c["name"], ha="right", va="center", fontsize=8, family="monospace")
        ax.text(0.5, y, "PASS" if c["passed"] else "FAIL", ha="center", va="center",
                color="white", fontsize=8, weight="bold")
    ax.set_xlim(-1.35, 1.05)
    ax.set_ylim(-0.7, len(cs) - 0.3)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_title("acceptance self-check  all_pass=%s" % checks["all_pass"], fontsize=10.5, loc="left")

    # ---- 右：源身份事实
    src = man["source"]
    ident = man["identity_facts"]
    ax = axes[2]
    ax.axis("off")
    rows = [
        ("report_id", src["report_id"]),
        ("source_uri", src["source_uri"]),
        ("sha256 (measured)", src["source_hash"][7:23] + "…"),
        ("sha256 == contract", str(src["hash_match"])),
        ("chars (measured)", str(src["chars"])),
        ("chars (contract)", str(src["contract_chars"])),
        ("bytes utf8", str(src["bytes"])),
        ("lines", str(src["lines"])),
        ("title == contract", str(src["record_fields"]["title_matches_contract"])),
        ("title in markdown H1", str(src["record_fields"]["title_matches_markdown_h1"])),
        ("scenario_key == contract", str(src["record_fields"]["scenario_matches_contract"])),
        ("figures declared", str(ident["figures_declared"])),
        ("figure payload present", str(ident["figure_payload_present"])),
        ("mission repo", str((ident.get("mission_probe") or {}).get("mission_repo"))),
        ("claims emitted", str(man["scope"]["claims_emitted"])),
        ("verification performed", str(man["scope"]["verification_performed"])),
    ]
    ax.text(0.0, 1.0, "source identity facts", fontsize=10.5, weight="bold", va="top")
    for i, (k, v) in enumerate(rows):
        y = 0.93 - i * 0.058
        ax.text(0.0, y, k, fontsize=8.2, family="monospace", va="top")
        col = "#222"
        if k.endswith("== contract"):
            col = "#2f7d32" if v == "True" else "#b00020"
        ax.text(0.62, y, v, fontsize=8.2, family="monospace", va="top", color=col,
                weight="bold" if k in ("sha256 == contract", "chars (measured)") else "normal")
    ax.set_xlim(0, 1.35)
    ax.set_ylim(-0.05, 1.06)

    fig.suptitle(
        "KF-RESULT wp-2506-01 / 01-asset-registration / report 2506 "
        "(TensorFVM compatible viscous dissipativity) - registration work package, no field quantities",
        fontsize=11.5, x=0.01, ha="left",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    out_png = fig_dir / "wp2506_01_asset_registry.png"
    fig.savefig(out_png, dpi=150)
    print("wrote", out_png)

    if out_dir == ART:
        (MIRROR / "figures").mkdir(parents=True, exist_ok=True)
        import shutil

        shutil.copy2(out_png, MIRROR / "figures" / out_png.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())