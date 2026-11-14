#!/usr/bin/env python3
"""RCI-S1 registry — figures + numbers for ``docs/rci-s1-registry.md``.

Every value plotted/printed is read from the frozen artifacts; nothing is
hand-copied.  The DB-side (SQL) recomputation in ``db_extras.json`` is treated
as an *independent* second implementation, so ``fig5`` is a real parity check
(artifact-side vs SQL-side) rather than a self-comparison.

Usage::

    python3 scripts/rci_s1_report.py \
        --out audit/refs/rci-s1-registry/out \
        --figdir docs/figures/rci-s1

Prints an English numbers block (for the report) and Chinese table rows used by
the registry doc; figures are written to ``--figdir``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from ke import rci_registry as rr  # noqa: E402

TYPES = ("info", "analysis", "research", "creative")
FLAGS = ("verified", "partial", "zero_overlap", "no_numbers", "no_mission", "no_result")
CLEAN = ("kept", "repaired", "excluded")
NAVY, TEAL, SAND, RED, GREY = "#1f3b57", "#2a9d8f", "#e9c46a", "#c1442e", "#8d99ae"


def load(out):
    rows = rr.read_rows(os.path.join(out, "registry_rows.jsonl.gz")) \
        if os.path.exists(os.path.join(out, "registry_rows.jsonl.gz")) \
        else rr.read_rows(os.path.join(out, "registry_rows.jsonl"))
    summary = json.load(open(os.path.join(out, "summary.json"), encoding="utf-8"))
    sens = json.load(open(os.path.join(out, "sensitivity.json"), encoding="utf-8"))
    extras = json.load(open(os.path.join(out, "db_extras.json"), encoding="utf-8"))
    return rows, summary, sens, extras


def fig1(rows, summary, path):
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    counts = [summary["by_type"].get(t, 0) for t in TYPES]
    ax[0].bar(TYPES, counts, color=[NAVY, TEAL, SAND, RED])
    for i, v in enumerate(counts):
        ax[0].text(i, v + 60, f"{v}", ha="center", fontsize=10)
    ax[0].set_title(f"asset_type (4-way typing, n={summary['rows']})")
    ax[0].set_ylabel("reports")

    bottom = [0, 0, 0, 0]
    colours = {c: k for c, k in zip(CLEAN, (TEAL, SAND, RED))}
    for decision in CLEAN:
        vals = [sum(1 for r in rows if r["asset_type"] == t and r["clean_decision"] == decision)
                for t in TYPES]
        ax[1].bar(TYPES, vals, bottom=bottom, label=decision, color=colours[decision])
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax[1].set_title("typing x KBM-CLEAN-W1 decision")
    ax[1].legend(fontsize=9)
    ax[1].set_ylabel("reports")
    for a in ax:
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig2(rows, summary, extras, path):
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    flags = [f for f in FLAGS if summary["by_real_exec"].get(f, 0) > 0]
    vals = [summary["by_real_exec"][f] for f in flags]
    ax[0].barh(flags, vals, color=TEAL)
    for i, v in enumerate(vals):
        ax[0].text(v + 80, i, f"{v}", va="center", fontsize=9)
    ax[0].set_title("real_exec_flag (number-overlap vs mission.result)")
    ax[0].set_xlabel("reports")
    ax[0].invert_yaxis()

    ov = [float(r["real_exec_overlap"]) for r in rows if r["real_exec_overlap"] is not None]
    ax[1].hist(ov, bins=[i / 10 for i in range(11)], color=NAVY)
    st = extras["overlap_stats"]
    for key, colour in (("mean", RED), ("p50", SAND), ("p90", TEAL)):
        ax[1].axvline(float(st[key]), color=colour, lw=1.6,
                      label=f"{key}={st[key]}")
    ax[1].set_title(f"report-number overlap distribution (n={st['n']})")
    ax[1].set_xlabel("overlap = |numbers(report) & numbers(result)| / |numbers(report)|")
    ax[1].set_ylabel("reports")
    ax[1].legend(fontsize=9)
    for a in ax:
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig3(summary, sens, path):
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    hist = {int(k): v for k, v in summary["dup_cluster_size_hist"].items()}
    sizes = sorted(hist)
    ax[0].bar([str(s) for s in sizes], [hist[s] for s in sizes], color=NAVY)
    ax[0].set_yscale("log")
    ax[0].set_title(f"duplicate cluster sizes "
                    f"(clusters={summary['dup_clusters']}, reports={summary['dup_reports_in_clusters']})")
    ax[0].set_xlabel("cluster size")
    ax[0].set_ylabel("clusters (log)")
    ax[0].tick_params(axis="x", labelsize=7)

    sweep = sorted(sens["sweep"], key=lambda x: x["gate"])
    gates = [s["gate"] for s in sweep]
    ax[1].plot(gates, [s["dup_clusters"] for s in sweep], "o-", color=RED,
               label="dup clusters")
    ax[1].plot(gates, [s["pairs_accepted"] for s in sweep], "s--", color=GREY,
               label="Jaccard-accepted pairs")
    for s in sweep:
        ax[1].annotate(str(s["dup_clusters"]), (s["gate"], s["dup_clusters"]),
                       textcoords="offset points", xytext=(0, 7), fontsize=8, ha="center")
    ax[1].axvline(0.5, color=TEAL, lw=1.2, ls=":")
    ax[1].set_xlabel("exact-Jaccard gate (0.0 = LSH band only)")
    ax[1].set_ylabel("count")
    ax[1].set_title("duplicate sensitivity to the dedup gate")
    ax[1].legend(fontsize=9)
    for a in ax:
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def fig4(rows, summary, extras, path):
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    stages = ["wt_exists", "wt_artifacts", "wt_repro", "triple_ok"]
    vals = [sum(1 for r in rows if r[s]) for s in stages]
    ax[0].bar(stages, vals, color=[NAVY, GREY, SAND, TEAL])
    for i, v in enumerate(vals):
        ax[0].text(i, v + 40, f"{v}\n{v / max(1, vals[0]):.1%}", ha="center", fontsize=9)
    ax[0].set_title("artifact-triple funnel (share of wt_exists)")
    ax[0].set_ylabel("reports")
    ax[0].tick_params(axis="x", labelsize=8)

    chars = [r["md_chars"] for r in rows if r["md_chars"] > 0]
    ax[1].hist(chars, bins=[0, 500, 1000, 2000, 4000, 8000, 16000, 32000, 64000, 200000],
               color=NAVY)
    ax[1].set_xscale("log")
    ax[1].set_title(f"report body length (chars, p50={summary['md_chars_p50']}, "
                    f"total={summary['md_chars_total']})")
    ax[1].set_xlabel("markdown chars (log bins)")
    ax[1].set_ylabel("reports")
    for a in ax:
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def crosscheck_items(rows, summary, extras):
    """(label, artifact-side, SQL-side) for every independently recomputed count."""
    items = []
    st = Counter(r["mission_status"] or "<none>" for r in rows)
    for k, v in extras["mission_status"].items():
        items.append((f"mission_status:{k}", st.get(k, 0), int(v)))
    repo = Counter(r["repo"] or "<none>" for r in rows)
    for k, v in extras["by_repo"].items():
        items.append((f"repo:{k}", repo.get(k, 0), int(v)))
    tc = Counter((r["asset_type"], r["clean_decision"]) for r in rows)
    for t, c, v in extras["type_x_clean"]:
        items.append((f"type_clean:{t}/{c}", tc.get((t, c), 0), int(v)))
    tr = Counter((r["asset_type"], r["real_exec_flag"]) for r in rows)
    for t, f, v in extras["type_x_realexec"]:
        items.append((f"type_realexec:{t}/{f}", tr.get((t, f), 0), int(v)))
    dk = Counter(r["dup_kind"] for r in rows if r["dup_kind"])
    for k, v in extras["dup_kind"].items():
        items.append((f"dup_kind:{k}", dk.get(k, 0), int(v)))
    fe = Counter(c for r in rows for c in (r["failed_empty_codes"] or []))
    for k, v in extras["failed_empty_codes"].items():
        items.append((f"failed_empty:{k}", fe.get(k, 0), int(v)))
    return [i for i in items if i[1] > 0 or i[2] > 0]


def fig5(rows, summary, extras, path):
    items = crosscheck_items(rows, summary, extras)
    a = [i[1] for i in items]
    b = [i[2] for i in items]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].loglog([0.5, 5000], [0.5, 5000], "--", color=GREY, lw=1, label="exact parity y=x")
    ax[0].scatter(a, b, s=22, color=NAVY, zorder=3, label=f"{len(items)} SQL aggregates")
    ax[0].set_xlabel("artifact-side recompute (from row ledger)")
    ax[0].set_ylabel("SQL-side recompute (independent)")
    ax[0].set_title("parity of the two independent implementations")
    ax[0].legend(fontsize=8, loc="upper left")

    dev = [(x - y) / y if y else 0.0 for x, y in zip(a, b)]
    order = sorted(range(len(items)), key=lambda i: abs(dev[i]), reverse=True)
    top = order[:12]
    ax[1].barh([items[i][0] for i in top][::-1], [dev[i] for i in top][::-1], color=RED)
    ax[1].axvline(0, color="k", lw=0.8)
    ax[1].set_xlim(-0.05, 0.05)
    ax[1].set_title("largest relative deviations (|dev| ≤ 5e-2 window)")
    ax[1].set_xlabel("(artifact − SQL) / SQL")
    ax[1].tick_params(axis="y", labelsize=7)
    worst = max(abs(d) for d in dev)
    ax[1].text(0.02, 0.05, f"max |dev| = {worst:.2e}", transform=ax[1].transAxes, fontsize=9)
    for a_ in ax:
        a_.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return items, worst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="audit/refs/rci-s1-registry/out")
    ap.add_argument("--figdir", default="docs/figures/rci-s1")
    a = ap.parse_args()
    rows, summary, sens, extras = load(a.out)
    os.makedirs(a.figdir, exist_ok=True)

    # numbers first: a summary that disagrees with the ledger stops the run.
    rr.assert_summary_matches(rows, summary)

    fig1(rows, summary, os.path.join(a.figdir, "fig1_typing_clean.png"))
    fig2(rows, summary, extras, os.path.join(a.figdir, "fig2_real_exec.png"))
    fig3(summary, sens, os.path.join(a.figdir, "fig3_duplicates.png"))
    fig4(rows, summary, extras, os.path.join(a.figdir, "fig4_traceability_length.png"))
    items, worst = fig5(rows, summary, extras,
                        os.path.join(a.figdir, "fig5_crosscheck_parity.png"))

    print("== numbers (artifact-side, recomputed) ==")
    print(f"rows            = {summary['rows']}")
    print(f"snapshot        = {summary['snapshot_id']}")
    print("by_type         = " + ", ".join(f"{t}={summary['by_type'].get(t, 0)}" for t in TYPES))
    print("by_type_rule    = " + ", ".join(f"{k}={v}" for k, v in
                                          sorted(summary["by_type_rule"].items())))
    print("by_clean        = " + ", ".join(f"{k}={v}" for k, v in sorted(summary["by_clean"].items())))
    print("by_real_exec    = " + ", ".join(f"{k}={v}" for k, v in
                                          sorted(summary["by_real_exec"].items())))
    print(f"dup_clusters    = {summary['dup_clusters']}  "
          f"in_clusters={summary['dup_reports_in_clusters']}  "
          f"excess={summary['dup_excess_reports']}  "
          f"largest={max(int(k) for k in summary['dup_cluster_size_hist'])}")
    print(f"failed_empty    = {summary['failed_empty']}  codes={summary['failed_empty_codes']}")
    print(f"triple_ok       = {summary['triple_ok']}  wt_exists={summary['wt_exists']}  "
          f"with_mission={summary['with_mission']}")
    print(f"md_chars        = total={summary['md_chars_total']} p50={summary['md_chars_p50']}")
    print(f"figures         = n_total={summary['n_figures_total']} "
          f"reports_with={summary['reports_with_figures']}")
    print("sensitivity     = " + ", ".join(
        f"g={s['gate']}:clusters={s['dup_clusters']},acc={s['pairs_accepted']}"
        for s in sorted(sens["sweep"], key=lambda x: x["gate"])))
    print(f"sql_crosscheck  = {len(items)} aggregates, max|dev| = {worst:.3e}")
    print("figures written ->", a.figdir)


if __name__ == "__main__":
    main()