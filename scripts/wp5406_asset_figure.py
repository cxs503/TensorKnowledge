#!/usr/bin/env python3
"""Figure for work package wp-5406-01: what the manifest actually asserts.

Panel A — reachability status per registered asset (nothing is 'retrieved');
panel B — locator type per asset (text offset locator vs record-field locator);
panel C — the source-identity cross-check: the manifest's own hash against the
hash recomputed by the platform library ``ke.wp_gate.ApiSourceResolver``.

    python scripts/wp5406_asset_figure.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "knowledge" / "assets" / "wp-5406-01"


def main() -> int:
    manifest = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    platform = json.loads((PKG / "platform_resolver_check.json").read_text(encoding="utf-8"))
    assets = manifest["attachments"]

    statuses = {}
    for a in assets:
        statuses[a["reachability"]["status"]] = statuses.get(
            a["reachability"]["status"], 0) + 1
    kinds = {}
    for a in assets:
        loc = "record_field" if (a.get("locator") or {}).get("locator_type") == "record_field" \
            else ("text_offset" if a["mentions"] else "none")
        kinds[loc] = kinds.get(loc, 0) + 1

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.6))

    ax = axes[0]
    labels = sorted(statuses)
    vals = [statuses[k] for k in labels]
    ax.barh(range(len(labels)), vals, color="#b5651d")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels([s.replace("_", " ") for s in labels], fontsize=8)
    ax.set_xlabel("assets")
    ax.set_title("A. reachability status (n=%d; retrieved bytes=0)" % len(assets), fontsize=10)
    for i, v in enumerate(vals):
        ax.text(v + 0.1, i, str(v), va="center", fontsize=8)
    ax.set_xlim(0, max(vals) + 2)

    ax = axes[1]
    lk = sorted(kinds)
    ax.bar([k.replace("_", "\n") for k in lk], [kinds[k] for k in lk],
           color=["#4a7c59", "#2f4b7c", "#777777"][: len(lk)])
    for i, k in enumerate(lk):
        ax.text(i, kinds[k] + 0.1, str(kinds[k]), ha="center", fontsize=9)
    ax.set_ylabel("assets")
    ax.set_title("B. locator type per asset", fontsize=10)
    ax.set_ylim(0, max(kinds.values()) + 2)

    ax = axes[2]
    names = ["manifest\ncomputed", "platform\nrecomputed", "contract\ndeclared"]
    values = [manifest["source"]["computed_source_hash"],
              platform["platform_sha256"],
              manifest["source"]["declared_source_hash"]]
    agree = len(set(values)) == 1
    ax.axis("off")
    ax.set_title("C. source_hash identity (report 5406 markdown)", fontsize=10)
    for i, (n, v) in enumerate(zip(names, values)):
        ax.text(0.02, 0.80 - 0.22 * i, f"{n.replace(chr(10), ' ')}: {v[:23]}…",
                fontsize=9, family="monospace")
    ax.text(0.02, 0.10,
            f"all three agree: {agree}   |   chars: manifest {manifest['source']['chars']} "
            f"= platform {platform['platform_chars']} = contract {manifest['source']['declared_chars']}\n"
            f"hash_match(manifest vs contract) = {manifest['source']['hash_match']}; "
            f"self-checks all_pass = {manifest['checks_passed']}",
            fontsize=9, color="#1a6b1a" if (agree and manifest["checks_passed"]) else "#a11")

    fig.suptitle("wp-5406-01 asset registration — what is reachable, what is only declared",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = PKG / "asset_reachability.png"
    fig.savefig(out, dpi=150)
    print("wrote", out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())