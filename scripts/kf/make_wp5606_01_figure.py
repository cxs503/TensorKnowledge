#!/usr/bin/env python3
"""Figure for wp-5606-01: attachment inventory + acceptance status.

Both panels are driven by runs/wp-5606-01/asset_manifest.json — no hand-typed
numbers.  A registration work package produces no field data, so the figure is a
machine-derived status chart (declaration vs. resoluble bytes), not a contour.

Output: runs/wp-5606-01/fig_acceptance.png (+ sha256 printed to stdout)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "runs" / "wp-5606-01"

m = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
items = m["attachments"]["items"]
comp = m["attachments"]["composition"]
checks = m["acceptance_selfcheck"]

kinds = list(comp.keys())
locator_ok = [sum(1 for a in items if a["kind"] == k and a["locator"]["resolvable"]) for k in kinds]
declared = [comp[k] for k in kinds]
byte_ok = [sum(1 for a in items if a["kind"] == k and a["resolvable"]) for k in kinds]

fig, (ax1, ax2) = plt.subplots(
    1, 2, figsize=(13.5, 5.2), gridspec_kw={"width_ratios": [1.05, 1.0]}
)

y = range(len(kinds))
ax1.barh([i + 0.19 for i in y], declared, height=0.36, color="#4C78A8",
         label="declared in report (registration entries)")
ax1.barh([i - 0.19 for i in y], locator_ok, height=0.36, color="#54A24B",
         label="verbatim locator resolves in source")
ax1.barh([i - 0.19 for i in y], byte_ok, height=0.36, color="#E45756",
         label="file bytes obtainable in this package")
ax1.set_yticks(list(y))
ax1.set_yticklabels([k.replace("_", " ") for k in kinds], fontsize=9)
ax1.set_xlabel("entries", fontsize=9)
ax1.set_title(
    f"A. Asset inventory: {m['attachments']['count']} entries, "
    f"{sum(locator_ok)}/{sum(declared)} locators resolved, {sum(byte_ok)} byte-resolvable",
    fontsize=10, loc="left",
)
ax1.legend(fontsize=7.5, loc="lower right")
ax1.grid(axis="x", alpha=0.3)
for i, v in enumerate(declared):
    ax1.text(v + 0.08, i + 0.19, str(v), va="center", fontsize=8)

order = [
    "valid_json",
    "schema_pass",
    "source_hash_matches",
    "source_locator_resolvable",
    "no_duplicate_ids",
    "all_claims_have_evidence_or_explicit_unresolved_status",
]
labels = [o.replace("_", "\n") for o in order]
vals = [1 if checks[o] else 0 for o in order]
ax2.barh(range(len(order))[::-1], [1] * len(order),
         color=["#54A24B" if v else "#E45756" for v in vals], height=0.62)
ax2.set_yticks(range(len(order))[::-1])
ax2.set_yticklabels(labels, fontsize=7.5)
ax2.set_xlim(0, 1.35)
ax2.set_xticks([])
ax2.set_title("B. Acceptance self-check (green = pass; PASS is a mechanical check, "
              "not platform verification)", fontsize=10, loc="left")
for i, v in zip(range(len(order))[::-1], vals):
    ax2.text(1.02, i, "PASS" if v else "FAIL", va="center", fontsize=8.5,
             color="#2E7D32" if v else "#B71C1C", fontweight="bold")
ax2.axvline(1.0, color="k", lw=0.6, alpha=0.4)
for s in ("top", "right", "bottom"):
    ax2.spines[s].set_visible(False)

src = m["source_asset"]
fig.suptitle(
    f"wp-5606-01 · report {m['report_id']} asset registration · "
    f"markdown {src['size']['chars']} chars / {src['size']['bytes_utf8']} B · "
    f"sha256 {src['hash']['value'][7:19]}… == contract ({src['hash']['matches_contract']})",
    fontsize=9.5, x=0.01, ha="left",
)
fig.tight_layout(rect=(0, 0, 1, 0.94))
out = PKG / "fig_acceptance.png"
fig.savefig(out, dpi=160)
print(out, "sha256:" + hashlib.sha256(out.read_bytes()).hexdigest())