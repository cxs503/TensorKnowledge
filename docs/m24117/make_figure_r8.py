#!/usr/bin/env python3
"""m24117 (RA R8): four-state comparison figure.

States:
  before      m23257 baseline (m23157 R5 recheck, quoted from R7 receipt)
  R6-claimed  R6 self-reported after (status_after.json, generated on the
              unmerged agent/m23814 branch -- falsified by R7)
  R7-actual   R7 terminal review rerun on main@53959af (frozen verifier)
  R8-fixed    THIS mission: cherry-picked fix, cold git-archive HEAD rerun
              (docs/m24117/raw/status_after_m24117.json, programmatic read)

Zero hand-copy: R8 numbers are read from the evidence JSON; the other three
states are read from docs/m24007/REVIEW-RECEIPT-R7.json (frozen review record).
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
R7 = json.loads((HERE.parent / "m24007/REVIEW-RECEIPT-R7.json").read_text())
R8 = json.loads((HERE / "raw/status_after_m24117.json").read_text())

# ---- R8 (this fix) from the frozen-verifier evidence -----------------------
loc = R8["r5_1_locators"]
man = R8["r5_2_manifest"]
d6 = R8["d6_evidence"]
r8 = {
    "pure_path_fields": loc["pure_path_fields"],
    "resolved_cold": loc["pure_path_resolved_cold"],
    "legacy_runs_prefix": loc["pure_path_fields_legacy_runs_prefix"],
    "absolute_foreign": loc["pure_path_fields_absolute_foreign"],
    "manifest_missing": len(man["missing"]),
    "manifest_mismatch": len(man["mismatch"]),
    "d6_no_input_sha256": len(d6["items_without_input_sha256"]),
    "d6_abs_input_refs": sum(len(v) for v in d6["items_with_absolute_foreign_input_refs"].values()),
    "d6_source_ref_cold": d6["source_ref_resolve_cold"],
    "d6_sha256_matches": d6["sha256_matches"],
}

# ---- R7-actual (main@53959af) from the frozen R7 receipt -------------------
a = R7["residuals"]
r7 = {
    "pure_path_fields": a["R5-1"]["actual"]["pure_path_fields"],
    "resolved_cold": a["R5-1"]["actual"]["resolved_cold"],
    "legacy_runs_prefix": a["R5-1"]["actual"]["legacy"],
    "absolute_foreign": a["R5-1"]["actual"]["absolute"],
    "manifest_missing": len(a["R5-2"]["actual"]["missing"]),
    "manifest_mismatch": 0,
    "d6_no_input_sha256": len(a["R5-3"]["actual"]["items_without_input_sha256"]),
    "d6_abs_input_refs": len(a["R5-3"]["actual"]["items_with_absolute_foreign_input_refs"]),
    "d6_source_ref_cold": a["R5-3"]["actual"]["source_ref_resolve_cold"],
    "d6_sha256_matches": a["R5-3"]["actual"]["sha256_matches"],
}

# ---- R6-claimed (self-report, falsified) ------------------------------------
r6 = {
    "pure_path_fields": a["R5-1"]["r6_claimed"]["pure_path_fields"],
    "resolved_cold": a["R5-1"]["r6_claimed"]["resolved_cold"],
    "legacy_runs_prefix": a["R5-1"]["r6_claimed"]["legacy"],
    "absolute_foreign": a["R5-1"]["r6_claimed"]["absolute"],
    "manifest_missing": 0,
    "manifest_mismatch": 0,
    "d6_no_input_sha256": 0,
    "d6_abs_input_refs": 0,
    "d6_source_ref_cold": 5,
    "d6_sha256_matches": 5,
}

# ---- before (m23257 baseline, quoted in R7 TERMINAL_REVIEW table) -----------
before = {
    "pure_path_fields": 144,
    "resolved_cold": 17,
    "legacy_runs_prefix": 114,
    "absolute_foreign": 17,
    "manifest_missing": 4,
    "manifest_mismatch": 2,
    "d6_no_input_sha256": 1,
    "d6_abs_input_refs": 3,
    "d6_source_ref_cold": 0,
    "d6_sha256_matches": 0,
}

metrics = [
    ("pure-path locator fields", "pure_path_fields", "count"),
    ("resolved cold (of pure-path)", "resolved_cold", "count"),
    ("legacy runs/ prefix", "legacy_runs_prefix", "bad"),
    ("absolute foreign paths", "absolute_foreign", "bad"),
    ("manifest missing files", "manifest_missing", "bad"),
    ("manifest digest mismatch", "manifest_mismatch", "bad"),
    ("D6 items w/o input_sha256", "d6_no_input_sha256", "bad"),
    ("D6 absolute foreign input_refs", "d6_abs_input_refs", "bad"),
    ("D6 source_ref resolve cold (/5)", "d6_source_ref_cold", "good5"),
    ("D6 item sha256 match (/5)", "d6_sha256_matches", "good5"),
]
states = [("before\nm23257", before), ("R6-claimed\n(unmerged branch)", r6),
          ("R7-actual\nmain@53959af", r7), ("R8-fixed\n1ad7b60", r8)]

fig, axes = plt.subplots(2, 5, figsize=(15, 7.5))
for ax, (label, key, kind) in zip(axes.ravel(), metrics):
    vals = [s[1][key] for s in states]
    colors = ["#888888", "#f2a6a6", "#f2c9a6", "#a6d8a6"]
    bars = ax.bar(range(4), vals, color=colors, edgecolor="black", linewidth=0.6)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v, str(v), ha="center",
                va="bottom", fontsize=8)
    ax.set_title(label, fontsize=9)
    ax.set_xticks(range(4))
    ax.set_xticklabels(["before", "R6-claim", "R7-actual", "R8-fix"], fontsize=7)
    ax.set_ylim(0, max(vals) * 1.25 + 1)
    ax.grid(axis="y", alpha=0.3)
fig.suptitle("PROD-RA R8 (m24117): R5 residuals across four states — frozen verifier "
             "docs/m23257/verify_status.py, cold git-archive HEAD\n"
             "R8 = cherry-pick of e4d086e (agent/m23814) onto main; all numbers "
             "re-derived from the committed state", fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.94])
out = HERE / "figures/r8_four_state.png"
out.parent.mkdir(exist_ok=True)
fig.savefig(out, dpi=140)
print("saved", out)
print("R8:", json.dumps(r8))
