"""Verify the wp-331-04 deliverables offline (no network needed).

Checks, in order, and prints one line per check:
  V1 envelope loads as JSON and validates against schemas/kf_result.v1.schema.json
  V2 provenance.source_hash == sha256 of the pinned source snapshot, and == contract hash
  V3 every evidence quote in the review is a verbatim substring of the source snapshot
  V4 derived metrics recomputed from the source table equal the ones written in the review
  V5 no field anywhere claims verification (honesty guard: verified/verification_status...)
  V6 verdict / acceptance self-check statements are internally consistent
Exit code 0 only if all checks pass.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs" / "wp-331-04"
OUT = ROOT / "docs" / "kf" / "wp-331-04"
CONTRACT_HASH = "sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717"

results: list[tuple[str, bool, str]] = []


def check(cid: str, ok: bool, detail: str) -> None:
    results.append((cid, ok, detail))


def main() -> int:
    src = (RUNS / "source_331.md").read_text(encoding="utf-8")
    env = json.loads((OUT / "kf_result.wp-331-04.json").read_text(encoding="utf-8"))
    review = env["outputs"]["review_report.json"]
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))

    try:
        jsonschema.validate(env, schema)
        check("V1", True, "envelope valid against kf_result.v1.schema.json")
    except jsonschema.ValidationError as exc:  # pragma: no cover
        check("V1", False, f"schema violation: {exc.message} at {list(exc.path)}")

    recomputed = "sha256:" + hashlib.sha256(src.encode("utf-8")).hexdigest()
    check("V2", recomputed == env["provenance"]["source_hash"] == CONTRACT_HASH,
          f"recomputed={recomputed[:20]}... env={env['provenance']['source_hash'][:20]}... "
          f"contract={CONTRACT_HASH[:20]}...")

    quotes = []
    for f in review["findings"]:
        quotes += [e["quote"] for e in f.get("evidence", []) if e.get("source_field") == "markdown"]
    for c in review["claim_judgements"]:
        quotes += [e["quote"] for e in c.get("evidence", []) if e.get("source_field") == "markdown"]
    missing = [q for q in quotes if q not in src]
    check("V3", not missing, f"{len(quotes)} quotes, {len(missing)} not verbatim {missing[:2]}")

    # V4 recompute derived metrics straight from the source table
    rows = {}
    lines = src.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("## ③"))
    for ln in lines[start:]:
        if ln.startswith("## ") and not ln.startswith("## ③"):
            break
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) == 4 and not set(cells[1]) <= set("- ") and cells[0].lower() != "metric":
            rows[cells[0]] = cells[1:]
    n = lambda t: float(re.search(r"-?\d+(?:\.\d+)?", t).group(0))  # noqa: E731
    d = review["derived_metrics"]
    exp_dev = abs(n(rows["Exponent"][0]) - n(rows["Exponent"][1]))
    expect = {
        "exponent_abs_deviation": round(exp_dev, 4),
        "exponent_tolerance_overshoot_factor": round(exp_dev / n(rows["Exponent"][1].split("±")[1]), 4),
        "stiffness_budget_overshoot_factor": round(n(rows["Stiffness error"][0]) / n(rows["Stiffness error"][1]), 4),
        "energy_budget_overshoot_factor": round(n(rows["Energy drift"][0]) / n(rows["Energy drift"][1]), 4),
        "beam_budget_margin_factor": round(n(rows["Stiffness error"][1]) / n(rows["Stiffness error"][2]), 2),
    }
    indent = re.search(r"max_indent=([0-9.]+)m", src).group(1)
    radius = re.search(r"R=([0-9.]+)m", src).group(1)
    expect["indent_over_R"] = round(float(indent) / float(radius), 4)
    mismatch = {k: (v, d.get(k)) for k, v in expect.items() if d.get(k) != v}
    check("V4", not mismatch, f"{len(expect)} derived metrics recomputed from source, mismatches={mismatch}")

    banned = re.compile(r'"(verified|verification_status|verification_level|is_verified|gate_confirmed)"')
    blob = json.dumps(review)
    check("V5", not banned.search(blob), "no verification-claiming field in review (honesty guard)")

    blocker_ids = [f["id"] for f in review["findings"] if f["blocking"]]
    selfcheck = review["acceptance_selfcheck"]
    ok6 = (review["verdict"] in {"pass", "needs-fix", "fail"}
           and (review["verdict"] != "pass" or not blocker_ids)
           and selfcheck["upstream_packages_completed"] is False
           and selfcheck["upstream_packages_completed"] == review["upstream"]["product_found"]
           and len(review["checks_not_run"]) >= 3)
    check("V6", ok6, f"verdict={review['verdict']} blockers={blocker_ids} "
                     f"upstream_found={review['upstream']['product_found']}")

    width = max(len(c) for c, _, _ in results)
    for cid, ok, detail in results:
        print(f"{cid:<{width}} {'PASS' if ok else 'FAIL'}  {detail}")
    print(f"\n{sum(1 for _, ok, _ in results if ok)}/{len(results)} checks passed")
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())