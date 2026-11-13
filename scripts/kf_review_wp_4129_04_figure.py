#!/usr/bin/env python3
"""wp-4129-04 figure: the audit evidence of the independent review, drawn from the JSON.

Panels (all numbers read from work/wp-4129-04/*.json, nothing retyped):
  (a) 34 machine checks: pass / fail, grouped by the collection they audit;
  (b) registered vs re-derived reference counts (body sites 13 vs 14, distinct 9 vs 9);
  (c) quotation surface: markdown quotes checked / on their declared line, record locators,
      and the one token that sits outside its locator quote (finding F1).
"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

WT = pathlib.Path(".")
RV = json.loads((WT / "work/wp-4129-04/review_report.json").read_text(encoding="utf-8"))
FIND = json.loads((WT / "work/wp-4129-04/review_findings.json").read_text(encoding="utf-8"))
OUT = WT / "docs/kf/figures/wp-4129-04.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

groups = [
    ("source identity", ("source_hash", "source_bytes", "source_chars", "source_lines", "source_crlf",
                         "provenance_hash_eq_contract", "contract_fields_match_record")),
    ("record fields", tuple(c["check_id"] for c in FIND["checks"] if c["check_id"].startswith("record_"))),
    ("locators", ("markdown_quotes_verbatim", "markdown_quotes_on_declared_line",
                  "record_pointers_resolve_to_quote", "token_inside_locator_quote", "locators_count",
                  "locators_resolved_count")),
    ("counts / ids", ("kind_status_histogram", "assets_total", "id_uniqueness_per_namespace",
                      "id_integrity_scope_matches_claim", "body_path_reference_census",
                      "unresolved_reasons_true_in_worktree")),
    ("honesty", ("no_verified_status", "claims_empty", "single_report_scope",
                 "finding_anchors_verbatim")),
    ("git / prefix", ("merge_short_is_prefix_of_full", "main_head_7hex_is_prefix_of_9hex",
                      "branch_head_is_not_prefix_of_merge", "all_four_sha_forms_present_in_source")),
    ("live probes", ("artifacts_probe_404",)),
]
by_id = {c["check_id"]: c["pass"] for c in FIND["checks"]}
names, npass, nfail = [], [], []
for g, ids in groups:
    ids = [i for i in ids if i in by_id]
    names.append(g)
    npass.append(sum(1 for i in ids if by_id[i]))
    nfail.append(sum(1 for i in ids if not by_id[i]))
uncovered = set(by_id) - {i for _, ids in groups for i in ids}
assert not uncovered, uncovered

fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.2))
ax = axes[0]
y = range(len(names))
ax.barh(list(y), npass, color="#2c7fb8", label="pass")
ax.barh(list(y), nfail, left=npass, color="#d94801", label="fail")
ax.set_yticks(list(y))
ax.set_yticklabels(names, fontsize=9)
for i, (p, f) in enumerate(zip(npass, nfail)):
    ax.text(p + f + 0.1, i, f"{p}/{p + f}", va="center", fontsize=8)
ax.set_xlabel("machine checks")
ax.set_title(f"(a) wp-4129-01 re-derivation: {FIND['checks_passed']}/{FIND['checks_total']} pass", fontsize=10)
ax.legend(fontsize=8, loc="lower right")
ax.set_xlim(0, max(p + f for p, f in zip(npass, nfail)) + 2.0)

ax = axes[1]
reg = RV["findings"][1]["evidence"]["upstream"]
red = RV["findings"][1]["evidence"]["rederived"]
labels = ["body_path_references", "distinct_referenced_paths"]
x = range(len(labels))
ax.bar([i - 0.18 for i in x], [reg[k] for k in labels], width=0.36, color="#7f7f7f",
       label="registered (wp-4129-01)")
ax.bar([i + 0.18 for i in x], [red[k] for k in labels], width=0.36, color="#2c7fb8",
       label="re-derived (this review)")
for i, k in enumerate(labels):
    ax.text(i - 0.18, reg[k] + 0.2, str(reg[k]), ha="center", fontsize=9)
    ax.text(i + 0.18, red[k] + 0.2, str(red[k]), ha="center", fontsize=9)
ax.set_xticks(list(x))
ax.set_xticklabels([l.replace("_", "\n") for l in labels], fontsize=9)
ax.set_ylim(0, max(reg.values()) * 1.35)
ax.set_ylabel("count")
miss = RV["findings"][1]["evidence"]["missing_sites"]
ax.set_title(f"(b) reference census: gap = unregistered site at line {miss[0]['line']}", fontsize=10)
ax.legend(fontsize=8)

ax = axes[2]
qs = RV["quotation_surface"]
bars = [("markdown quotes\nchecked", qs["markdown_quotes"], "#2c7fb8"),
        ("…on declared\nline", qs["markdown_quotes_on_declared_line"], "#41ab5d"),
        ("record locators\nresolved", qs["record_locators"], "#41ab5d"),
        ("token outside\nits quote", len(FIND["defects"]["token_outside_quote"]), "#d94801"),
        ("quotes not\nverbatim", len(FIND["defects"]["quote_not_verbatim"]), "#d94801")]
ax.bar([b[0] for b in bars], [b[1] for b in bars], color=[b[2] for b in bars])
for i, b in enumerate(bars):
    ax.text(i, b[1] + 0.3, str(b[1]), ha="center", fontsize=9)
ax.set_ylabel("count")
ax.set_ylim(0, max(b[1] for b in bars) * 1.25)
ax.tick_params(axis="x", labelsize=8)
ax.set_title("(c) quotation surface: verbatim by construction", fontsize=10)
fig.suptitle("wp-4129-04 independent review of wp-4129-01 (report 4129): every registered fact re-derived",
             fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.94))
fig.savefig(OUT, dpi=130)
print("wrote", OUT, OUT.stat().st_size, "bytes")
print("groups:", {n: (p, f) for n, p, f in zip(names, npass, nfail)})