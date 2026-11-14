#!/usr/bin/env python3
"""Measure and plot the KF-RESULT v1 envelope schema repair (wp-459-01).

Two panels, both fed from committed bytes (no hand-copied numbers):

  (a) how many of the committed envelopes each schema revision accepts
      — rev 1.0 (the over-narrow overwrite) vs rev 1.1 (the repair);
  (b) why rev 1.0 rejected them, as a cause census.

The rev 1.0 blob is read out of git history (``BASELINE_REV``), so the "before"
numbers stay reproducible after the repair is merged: the commit precedes the
repair by construction and lives in the permanent history.

Usage
-----
    python3 scripts/kf/fig_wp459_01_envelope_conformance.py           # plot + print numbers
    python3 scripts/kf/fig_wp459_01_envelope_conformance.py --json    # numbers only
"""

from __future__ import annotations

import collections
import glob
import json
import os
import subprocess
import sys

import jsonschema

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCHEMA_REL = "schemas/kf_result.v1.schema.json"
BASELINE_REV = "d2ecb95"  # tip of main immediately before the rev 1.1 repair
FIG_REL = "docs/kf/wp-459-01/figures/fig_wp459_01_envelope_conformance.png"
CENSUS_REL = "docs/kf/wp-459-01/envelope_conformance.json"


def committed_envelopes() -> list[tuple[str, dict]]:
    out = []
    for path in sorted(
        set(glob.glob(os.path.join(ROOT, "**", "kf_result*.json"), recursive=True))
    ):
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        if isinstance(doc, dict) and "provenance" in doc and "outputs" in doc:
            out.append((os.path.relpath(path, ROOT).replace(os.sep, "/"), doc))
    return out


def baseline_schema() -> dict:
    blob = subprocess.run(
        ["git", "-C", ROOT, "show", f"{BASELINE_REV}:{SCHEMA_REL}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return json.loads(blob)


def rejection_causes(validator, envelopes) -> collections.Counter:
    causes: collections.Counter = collections.Counter()
    for _, doc in envelopes:
        errors = list(validator.iter_errors(doc))
        if not errors:
            continue
        seen = set()
        for err in errors:
            path = list(err.path)
            where = ".".join(str(p) for p in path)
            if err.validator == "additionalProperties":
                seen.add(f"extra keys in {where or 'top level'}")
            elif err.validator == "required":
                seen.add(f"missing required in {where or 'top level'}")
            elif err.validator in ("pattern", "enum", "type"):
                seen.add(f"{where or 'top'} {err.validator}")
            else:
                seen.add(f"{where or 'top'} {err.validator}")
        causes.update(seen)
    return causes


def measure() -> dict:
    envelopes = committed_envelopes()
    before = jsonschema.Draft202012Validator(baseline_schema())
    with open(os.path.join(ROOT, SCHEMA_REL), encoding="utf-8") as fh:
        after = jsonschema.Draft202012Validator(json.load(fh))

    def accepted(validator) -> int:
        return sum(1 for _, doc in envelopes if not list(validator.iter_errors(doc)))

    with open(os.path.join(ROOT, CENSUS_REL), encoding="utf-8") as fh:
        census = json.load(fh)

    causes = rejection_causes(before, envelopes)
    # group the long tail so the chart stays readable
    grouped = {
        "provenance extra keys\n(producer/emitted_at/notes/lane…)": causes.get(
            "extra keys in provenance", 0
        ),
        "top-level extra keys\n(claims/contract_version/…)*": causes.get(
            "extra keys in top level", 0
        ),
        "provenance missing\nrequired key (source_uri)": causes.get(
            "missing required in provenance", 0
        ),
        "task_type only\nfull names (short code 01)": causes.get("task_type enum", 0),
        "outputs key\nwhitelist": causes.get("extra keys in outputs", 0),
        "other (type/enum/pattern)": sum(
            v
            for k, v in causes.items()
            if k.startswith(("outputs.", "report_id", "task_type", "package_id"))
        ),
    }
    return {
        "envelopes": len(envelopes),
        "accepted_rev1_0": accepted(before),
        "accepted_rev1_1": accepted(after),
        "ratio_rev1_0": round(accepted(before) / len(envelopes), 4),
        "ratio_rev1_1": round(accepted(after) / len(envelopes), 4),
        "baseline_rev": BASELINE_REV,
        "rejection_causes_rev1_0": grouped,
        "residual": census["residual_allowlist"],
    }


def plot(stats: dict) -> str:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.4, 4.8))

    labels = [
        "rev 1.0\n(overwrite: additionalProperties=false,\nprovenance 7-key whitelist)",
        "rev 1.1\n(repair: envelope semantics restored)",
    ]
    accepted = [stats["accepted_rev1_0"], stats["accepted_rev1_1"]]
    rejected = [stats["envelopes"] - a for a in accepted]
    colors_acc = ["#c0392b", "#1e8449"]
    ax1.bar(labels, accepted, color=colors_acc, width=0.55, label="accepted")
    ax1.bar(
        labels,
        rejected,
        bottom=accepted,
        color="#d5d8dc",
        width=0.55,
        hatch="//",
        edgecolor="#7f8c8d",
        label="rejected",
    )
    for i, (a, r) in enumerate(zip(accepted, rejected)):
        ax1.text(
            i, a / 2, f"{a}", ha="center", va="center", color="white", fontweight="bold"
        )
        ax1.text(
            i,
            a + r / 2,
            f"{r}",
            ha="center",
            va="center",
            color="#2c3e50",
            fontweight="bold",
        )
        ax1.text(
            i,
            stats["envelopes"] * 1.03,
            f"{a / stats['envelopes']:.1%} accepted",
            ha="center",
            va="bottom",
            fontsize=10,
        )
    ax1.set_ylim(0, stats["envelopes"] * 1.12)
    ax1.set_ylabel(f"committed kf_result envelopes (n={stats['envelopes']})")
    ax1.set_title("(a) envelope conformance, measured on committed bytes")
    ax1.legend(loc="lower right", frameon=True)
    ax1.grid(axis="y", alpha=0.3)

    causes = stats["rejection_causes_rev1_0"]
    names = list(causes)
    values = [causes[k] for k in names]
    bars = ax2.barh(names, values, color="#c0392b", alpha=0.85, height=0.6)
    for bar, value in zip(bars, values):
        ax2.text(
            value + 2,
            bar.get_y() + bar.get_height() / 2,
            str(value),
            va="center",
            fontsize=10,
        )
    ax2.invert_yaxis()
    ax2.set_xlabel("envelopes flagged (one envelope can hit several causes)")
    ax2.set_title("(b) why rev 1.0 rejected them")
    ax2.grid(axis="x", alpha=0.3)
    ax2.text(
        0.98,
        0.02,
        f"baseline blob: git {BASELINE_REV}:{SCHEMA_REL}",
        transform=ax2.transAxes,
        ha="right",
        va="bottom",
        fontsize=8,
        color="#566573",
    )

    fig.suptitle(
        "KF-RESULT v1 schema repair (wp-459-01): the schema must describe the artifact family",
        fontsize=12.5,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = os.path.join(ROOT, FIG_REL)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


def main(argv: list[str]) -> int:
    stats = measure()
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    if "--json" not in argv:
        print(f"wrote {FIG_REL}", file=sys.stderr)
        plot(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
