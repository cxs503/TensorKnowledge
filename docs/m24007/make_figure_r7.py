#!/usr/bin/env python3
"""R7 terminal-review figure: frozen-verifier metrics, before vs R6-claimed-after vs actual-after."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# before = m23257 status_evidence.json (main@3fbd3b3, pre-R6)
# claimed_after = m23814 status_after.json (agent/m23814@543881ac, never merged)
# actual_after = independent rerun of frozen verifier on main@53959af (this review)
before = {
    "pure_path_fields": 144, "cold_resolved": 17, "legacy_prefix": 114,
    "absolute_foreign": 17, "unresolvable_after_repair": 5,
    "manifest_sound": 0, "d6_input_sha256": 4, "d6_source_ref_cold": 0,
    "d6_sha256_match": 0,
}
claimed = {
    "pure_path_fields": 137, "cold_resolved": 137, "legacy_prefix": 0,
    "absolute_foreign": 0, "unresolvable_after_repair": 0,
    "manifest_sound": 1, "d6_input_sha256": 5, "d6_source_ref_cold": 5,
    "d6_sha256_match": 5,
}
actual = {
    "pure_path_fields": 139, "cold_resolved": 82, "legacy_prefix": 51,
    "absolute_foreign": 6, "unresolvable_after_repair": 2,
    "manifest_sound": 0, "d6_input_sha256": 4, "d6_source_ref_cold": 0,
    "d6_sha256_match": 0,
}

labels = [
    "pure_path\nfields", "cold\nresolved", "legacy\nruns/ prefix",
    "absolute\nforeign", "unresolvable\nafter repair",
    "manifest\nsound", "D6 with\ninput_sha256", "D6 source_ref\nresolves cold",
    "D6 sha256\nmatches",
]
x = np.arange(len(labels))
w = 0.26

fig, ax = plt.subplots(figsize=(13, 6.5))
b = ax.bar(x - w, [before[k] for k in before], w, label="before (main@3fbd3b3)", color="#c0392b")
c = ax.bar(x, [claimed[k] for k in claimed], w, label="R6 claimed after (agent/m23814@543881ac, never merged)", color="#f39c12")
a = ax.bar(x + w, [actual[k] for k in actual], w, label="actual after (main@53959af, this R7 review)", color="#27ae60")

for bars in (b, c, a):
    for r in bars:
        ax.annotate(f"{int(r.get_height())}", (r.get_x() + r.get_width()/2, r.get_height()),
                    ha="center", va="bottom", fontsize=8)

ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=8)
ax.set_ylabel("count / boolean (1=pass)")
ax.set_title("PROD-RA R7 terminal review: frozen verifier (docs/m23257/verify_status.py) metrics\n"
             "R6 self-report is FALSE for the committed state — verification ran on an unmerged branch")
ax.legend(fontsize=8, loc="upper left")
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
fig.savefig("docs/m24007/figures/r7_before_claimed_actual.png", dpi=150)
print("saved docs/m24007/figures/r7_before_claimed_actual.png")
