#!/usr/bin/env python3
"""wp-9582-01 figures: two plots drawn strictly from measured manifest numbers.

No number is typed in here: counts, char offsets and spans are read from
docs/kf/wp-9582-01/asset_manifest.json, so the figures cannot drift from the
artifact they illustrate.

    python3 scripts/kf_wp9582_01_figures.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "docs" / "kf" / "wp-9582-01"
FIG_DIR = PKG_DIR / "figures"
MANIFEST = PKG_DIR / "asset_manifest.json"

RES_COLOR = {"resolved_in_source": "#2f7d32", "referenced_unresolved": "#e08b00",
             "declared_absent": "#7b1fa2"}


def fig_inventory(man: dict) -> Path:
    assets = man["assets"]
    classes = sorted({a["asset_class"] for a in assets})
    res = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    fig, ax = plt.subplots(figsize=(9.2, 4.4), dpi=150)
    left = [0] * len(classes)
    for r in res:
        vals = [sum(1 for a in assets if a["asset_class"] == c and a["resolution"] == r) for c in classes]
        ax.barh(classes, vals, left=left, color=RES_COLOR[r], label=r)
        left = [acc + v for acc, v in zip(left, vals)]
    for i, tot in enumerate(left):
        ax.text(tot + 0.08, i, str(tot), va="center", fontsize=9)
    ax.set_xlabel("assets registered")
    ax.set_title("wp-9582-01 asset inventory (n=%d) by class and resolution" % man["counts"]["assets"])
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    out = FIG_DIR / "fig_asset_inventory.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def fig_locator_map(man: dict) -> Path:
    assets = man["assets"]
    total = man["source"]["chars"]
    fig, ax = plt.subplots(figsize=(9.2, 5.2), dpi=150)
    for i, a in enumerate(assets):
        loc = a["locator"]
        s, e = loc["start_char"], loc["end_char"]
        if loc["method"] == "document":
            ax.barh(i, total, left=0, height=0.7, color=RES_COLOR[a["resolution"]],
                    alpha=0.18, hatch="//", edgecolor=RES_COLOR[a["resolution"]])
        else:
            ax.barh(i, max(e - s, 1), left=s, height=0.7, color=RES_COLOR[a["resolution"]])
    ax.set_yticks(range(len(assets)))
    ax.set_yticklabels(["%s %s" % (a["asset_id"], a["asset_class"].replace("_reference", "").replace("_markdown", ""))
                        for a in assets], fontsize=7)
    ax.set_xlim(0, total)
    ax.invert_yaxis()
    ax.set_xlabel("character offset in source markdown (chars=%d, L1-L%d)" % (total, assets[0]["locator"]["end_line"]))
    ax.set_title("wp-9582-01 locator map: %d/%d quotes unique (hatched = whole-document locator)"
                 % (man["integrity"]["quote_uniqueness"]["unique"], len(assets)))
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    out = FIG_DIR / "fig_locator_map.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def captions(man: dict) -> list[dict]:
    c = man["counts"]
    return [
        {"name": "fig_asset_inventory.png",
         "caption": "图1 wp-9582-01 资产清单：%d 个登记资产按类别与可解析状态着色（绿=resolved_in_source %d，橙=referenced_unresolved %d，紫=declared_absent %d）；计数直接读 asset_manifest.json。"
                    % (c["assets"], c["resolved_in_source"], c["referenced_unresolved"], c["declared_absent"])},
        {"name": "fig_locator_map.png",
         "caption": "图2 定位地图：%d 条 locator 在源 markdown 的字符坐标（0–%d chars）上的区间，斜线填充为整篇文档级 locator（A01）；%d/%d 条引文全文唯一。"
                    % (c["assets"], man["source"]["chars"],
                       man["integrity"]["quote_uniqueness"]["unique"], c["assets"])},
    ]


def main() -> int:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    outs = [fig_inventory(man), fig_locator_map(man)]
    for p in outs:
        print("%s %d bytes" % (p.relative_to(ROOT), p.stat().st_size))
    print(json.dumps(captions(man), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())