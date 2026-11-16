#!/usr/bin/env python3
"""Figures for the m23257 RA STATUS publication report.

Every number is read from the evidence JSONs, never typed in by hand:
  docs/m23257/status_evidence.json   (this mission's cold re-derivation)
  docs/m23157/r5_recheck.json        (independent R5 review, quoted)
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
EV = json.loads((HERE / "status_evidence.json").read_text(encoding="utf-8"))
R5 = json.loads((HERE.parent / "m23157/r5_recheck.json").read_text(encoding="utf-8"))
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)


def fig_locators() -> Path:
    loc = EV["r5_1_locators"]
    total = loc["pure_path_fields"]
    cold = loc["pure_path_resolved_cold"]
    prefix = loc["pure_path_resolved_after_prefix_repair"]
    dead = loc["pure_path_unresolvable_even_after_repair"]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    parts = ax.barh(["file locators\n(docs/m22059 + review bundle)"],
                    [cold], color="#2e7d32", label=f"resolves cold ({cold})")
    ax.barh(["file locators\n(docs/m22059 + review bundle)"], [prefix], left=[cold],
            color="#f9a825", label=f"only after runs/->docs/ prefix rewrite ({prefix})")
    ax.barh(["file locators\n(docs/m22059 + review bundle)"], [dead], left=[cold + prefix],
            color="#c62828", label=f"unresolvable even then ({dead})")
    ax.set_xlim(0, total)
    ax.set_xlabel("count (share of %d locator fields)" % total)
    ax.set_title("R5-1 still open on main@%s: %d/%d locators resolve for a third party"
                 % (EV["head_commit"][:7], cold, total), fontsize=11)
    ax.legend(loc="lower right", fontsize=8, framealpha=0.95)
    ax.text(total * 0.505, 0.42, f"legacy runs/m22059 prefix: {loc['pure_path_fields_legacy_runs_prefix']}\n"
                                 f"absolute /srv/tensor/agent refs: {loc['pure_path_fields_absolute_foreign']}",
            ha="center", fontsize=8, bbox=dict(fc="white", ec="#999", alpha=0.9))
    ax.grid(axis="x", alpha=0.3)
    for p in parts:
        pass
    out = FIG / "ra-locator-coldstart.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def fig_entrypoints() -> Path:
    variants = {
        "as shipped (cold)": R5["r4_2_entry_point"]["as_shipped"]["exit_code"],
        "as shipped (legacy tree)": R5["r4_2_entry_point"]["as_shipped_legacy_target"]["exit_code"],
        "as shipped (prepared runs/)": R5["r4_2_entry_point"]["as_shipped_prepared_runs_layout"]["exit_code"],
        "PR#511 fix (cold)": R5["r4_2_entry_point"]["fixed_cold_start"]["exit_code"],
        "PR#511 fix (this mission, main)": EV["entry_point"]["cold_exit_code"],
    }
    names = list(variants)
    vals = [variants[k] for k in names]
    colors = ["#c62828" if v != 0 else "#2e7d32" for v in vals]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bars = ax.bar(range(len(names)), vals, color=colors)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels([n.replace(" (", "\n(") for n in names], fontsize=8)
    ax.set_ylabel("recheck.py exit code")
    ax.set_ylim(0, 1.35)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.04, str(v), ha="center", fontsize=9)
    ax.axhline(0, color="#333", lw=0.8)
    ax.set_title("Entry point: defect reproduced pre-fix, gone after PR#511 (merged %s)"
                 % EV["pr511_merge"]["stdout_tail"].splitlines()[0][:7], fontsize=11)
    ax.grid(axis="y", alpha=0.3)
    out = FIG / "ra-entrypoint-exitcodes.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def fig_status() -> Path:
    """Asserted vs reconciled for the two independent state fields."""
    rec = [p for p in json.loads((HERE / "products_STATUS.proposed.json").read_text())["products"]
           if p["id"] == "RA"][0]
    recon = json.loads((HERE / "products_STATUS.proposed.json").read_text())[
        "mission_baseline_reconciliation"]
    asserted = recon["asserted_by_mission"]
    fields = ["code_implemented", "scenario_validated"]
    asrt = [int(bool(asserted["RA_" + f])) for f in fields]
    rc = [int(bool(rec[f])) for f in fields]
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    x = np.arange(len(fields))
    ax.bar(x - 0.19, asrt, 0.36, label="asserted by mission brief", color="#5c6bc0")
    ax.bar(x + 0.19, rc, 0.36, label="supported by recomputed evidence", color="#2e7d32")
    for i, (a, r) in enumerate(zip(asrt, rc)):
        ax.text(i - 0.19, a + 0.03, "true" if a else "false", ha="center", fontsize=9)
        ax.text(i + 0.19, r + 0.03, "true" if r else "false", ha="center", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(fields)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["false", "true"])
    ax.set_ylim(0, 1.5)
    ax.legend(fontsize=8, loc="upper center", ncol=2)
    ax.set_title("RA row: one of two asserted state fields is not supported", fontsize=11)
    out = FIG / "ra-status-reconciliation.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


if __name__ == "__main__":
    for f in (fig_locators(), fig_entrypoints(), fig_status()):
        print(f.relative_to(HERE))