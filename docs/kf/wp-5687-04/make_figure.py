#!/usr/bin/env python3
"""Render the wp-5687-04 review evidence figure from machine outputs (no hand-typed numbers)."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PKG = Path(__file__).resolve().parent
checks = json.loads((PKG / "checks.json").read_text(encoding="utf-8"))
rev = json.loads((PKG / "review_report.json").read_text(encoding="utf-8"))

GATE = {"C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "C13"}
items = checks["checks"]
locs = checks["locators"]
finds = rev["findings"]

fig = plt.figure(figsize=(15, 4.6))
gs = fig.add_gridspec(1, 3, width_ratios=[1.45, 1.15, 1.0], wspace=0.32)

# panel A: check matrix
ax = fig.add_subplot(gs[0, 0])
colors = {"pass": "#2e7d32", "fail": "#c62828", "not_run": "#9e9e9e"}
for i, c in enumerate(items):
    ax.barh(i, 1, color=colors[c["result"]], height=0.72,
            hatch="" if c["id"] in GATE else "//",
            edgecolor="black", linewidth=0.4)
    ax.text(1.05, i, f"{c['result']}", va="center", fontsize=7.5,
            color=colors[c["result"]], fontweight="bold")
ax.set_yticks(range(len(items)))
CJK = str.maketrans({"“": "'", "”": "'"})
ax.set_yticklabels([f"{c['id']} " + c["check"].translate(CJK)[:52] for c in items], fontsize=7)
ax.invert_yaxis()
ax.set_xlim(0, 1.5)
ax.set_xticks([])
ax.set_title("A  wp-5687-01 independent check matrix\n"
             f"solid = gate checks ({len(GATE)}), hatched = coverage/label checks "
             f"({len(items)-len(GATE)}); green {sum(c['result']=='pass' for c in items)} / "
             f"red {sum(c['result']=='fail' for c in items)}",
             fontsize=9, loc="left")

# panel B: locator verbatim verification
ax2 = fig.add_subplot(gs[0, 1])
ok = [l for l in locs if l["verbatim_at_line"]]
bad = [l for l in locs if not l["verbatim_at_line"]]
ax2.scatter([l["line"] for l in ok], [l["quote_chars"] for l in ok], s=95,
            c="#2e7d32", marker="o", label=f"verbatim at declared line (n={len(ok)})", zorder=3)
if bad:
    ax2.scatter([l["line"] for l in bad], [l["quote_chars"] for l in bad], s=95,
                c="#c62828", marker="x", label=f"not verbatim (n={len(bad)})", zorder=3)
for l in locs:
    ax2.annotate(l["asset_id"].split(":")[-1], (l["line"], l["quote_chars"]),
                 textcoords="offset points", xytext=(5, -10), fontsize=7)
ax2.set_xlabel("report markdown line (1-based)", fontsize=8.5)
ax2.set_ylabel("quote length (chars)", fontsize=8.5)
ax2.set_title("B  locator re-check: quote is contiguous text\n"
              "at the declared line AND in the whole markdown", fontsize=9, loc="left")
ax2.grid(alpha=0.3)
ax2.legend(fontsize=7.5, loc="upper left")
ax2.tick_params(labelsize=7.5)

# panel C: findings by severity + verdict
ax3 = fig.add_subplot(gs[0, 2])
sev = {"medium": 0, "low": 0}
for f in finds:
    sev[f["severity"]] = sev.get(f["severity"], 0) + 1
names = list(sev.keys())
vals = [sev[k] for k in names]
bars = ax3.bar(names, vals, color=["#ef6c00", "#fbc02d"][:len(names)], edgecolor="black", linewidth=0.5)
for b, v in zip(bars, vals):
    ax3.text(b.get_x() + b.get_width() / 2, v + 0.05, str(v), ha="center", fontsize=9, fontweight="bold")
ax3.set_ylim(0, max(vals) + 1.2)
ax3.set_ylabel("findings", fontsize=8.5)
ax3.set_title("C  severity and disposition", fontsize=9, loc="left")
ax3.tick_params(labelsize=8)
d = rev["decision"]
ax3.text(0.5, max(vals) * 0.55,
         f"verdict = {d['verdict'].upper()}\n"
         f"gate checks {d['gate_checks_green']}\n"
         f"blocking = {d['blocking_findings']}\n"
         f"non-blocking = {d['non_blocking_findings']}\n"
         f"(advisory, NOT a verified mark)",
         ha="center", va="center", fontsize=8.5, family="monospace",
         bbox=dict(boxstyle="round,pad=0.45", fc="#e8f5e9", ec="#2e7d32"))

fig.suptitle("wp-5687-04 independent red-team review of wp-5687-01 (01-asset-registration) - report 5687",
             fontsize=11, x=0.01, ha="left")
out = PKG / "fig1_review_evidence.png"
fig.savefig(out, dpi=170, bbox_inches="tight")
print("wrote", out, out.stat().st_size, "bytes")