#!/usr/bin/env python3
"""Render the kf_result schema-conformance figure from the scan artifact.

Input is the JSON emitted by ``scripts/kf/schema_conformance_scan.py`` — no
number in the figure is typed by hand, so the figure cannot drift from the
measurement.

Left panel : valid vs. invalid envelope counts, baseline schema vs. current.
Right panel: the remaining drift categories (grouped schema errors that the
             additive fix deliberately does NOT paper over).

Usage:
    python3 scripts/kf/plot_schema_conformance.py \
        --report docs/kf/wp-459-01/schema_conformance.json \
        --out docs/kf/wp-459-01/figures/fig_wp459_01_schema_conformance.png
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SHORT = {
    "required:<root>": "missing required\ntop-level key",
    "additionalProperties:<root>": "unknown top-level key",
    "additionalProperties:provenance": "unknown provenance key",
    "additionalProperties:outputs": "unknown outputs key",
    "enum:task_type": "task_type not in enum",
    "pattern:package_id": "package_id pattern",
    "type:provenance": "provenance field type",
    "required:provenance": "missing provenance key",
    "additionalProperties:outputs/asset_manifest.json": "manifest shape",
}


def label(finding: dict) -> str:
    key = f"{finding['validator']}:{finding['path']}"
    return SHORT.get(key, key)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--top", type=int, default=6)
    args = ap.parse_args(argv)

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    base, cur = report["baseline"], report["current"]

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.6), gridspec_kw={"width_ratios": [1, 1.5]})

    ax = axes[0]
    groups = ["baseline schema\n(pre-fix)", "current schema\n(additive fix)"]
    valid = [base["envelopes_valid"], cur["envelopes_valid"]]
    invalid = [base["envelopes_invalid"], cur["envelopes_invalid"]]
    bars_v = ax.bar(groups, valid, color="#2c6fbb", label="valid")
    bars_i = ax.bar(groups, invalid, bottom=valid, color="#b4453b", label="invalid")
    for bars, values, offsets in ((bars_v, valid, [0, 0]), (bars_i, invalid, valid)):
        for rect, value, base_value in zip(bars, values, offsets):
            ax.text(
                rect.get_x() + rect.get_width() / 2,
                base_value + value / 2,
                f"{value}",
                ha="center",
                va="center",
                color="white",
                fontsize=11,
                fontweight="bold",
            )
    ax.set_ylabel("kf_result envelopes")
    ax.set_title(
        f"envelope conformance: {base['envelopes_valid']}/{base['envelopes_scanned']} → "
        f"{cur['envelopes_valid']}/{cur['envelopes_scanned']} valid\n"
        f"additive-only = {report['delta']['additive_only']} "
        f"(regressions = {len(report['delta']['regressions'])})",
        fontsize=10,
    )
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1]
    findings = cur["findings"][: args.top]
    names = [label(f) for f in findings]
    counts = [f["count"] for f in findings]
    ypos = range(len(names))
    ax.barh([*ypos], counts, color="#e08a1e")
    for y, value in zip(ypos, counts):
        ax.text(value + 0.3, y, str(value), va="center", fontsize=9)
    ax.set_yticks([*ypos])
    ax.set_yticklabels(names, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("envelopes affected (remaining, not fixed here)")
    ax.set_title(
        f"residual drift categories: {cur['finding_count']} groups / "
        f"{cur['envelopes_invalid']} invalid envelopes",
        fontsize=10,
    )
    ax.grid(axis="x", alpha=0.25)

    fig.suptitle(
        "kf_result.v1 contract drift: schema vs. 426 candidate envelopes in-tree "
        "(docs/kf, runs, work)",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())