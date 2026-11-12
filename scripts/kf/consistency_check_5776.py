#!/usr/bin/env python3
"""Arithmetic consistency audit for report 5776 (NOT a platform verification).

What this does — and only this:
  * parses the density pair (rho_w, rho_i) and the 9-case sweep table out of the
    report markdown (no retyping),
  * recomputes U_anchor = U_current * sqrt(rho_w/rho_i) from the report's OWN
    closed form (which asserts sqrt(C_D_water/C_D_ice) = 1.0),
  * reports the relative deviation of the table's U_analytical and U_sim columns
    from that recomputation.

It deliberately does NOT judge physical validity, does NOT compare against
experiment, and does NOT set any claim to `verified` — verification is the
platform gate's job.

Usage: python3 scripts/kf/consistency_check_5776.py
Output: runs/wp-5776-01/consistency_check.json
"""
from __future__ import annotations

import json
import math
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
MD = REPO / "runs" / "wp-5776-01" / "report_5776.md"
OUT = REPO / "runs" / "wp-5776-01" / "consistency_check.json"

EXPECTED_HASH_PREFIX = "49089e9b"


def parse_params(md: str):
    rho_w = float(re.search(r"ρ_w=([0-9.]+) kg/m³", md).group(1))
    rho_i = float(re.search(r"ρ_i=([0-9.]+) kg/m³", md).group(1))
    # closed form: U_drift = U_current * sqrt(rho_w/rho_i) * sqrt(CD_w/CD_i), CD ratio taken as 1.0
    ratio = 1.0 if "· 1.0 = 1.0672 m/s" in md else None
    if ratio is None:
        raise SystemExit("closed-form block layout changed: cannot pin the CD-ratio factor")
    return rho_w, rho_i, ratio


ROW_RE = re.compile(r"^\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|$")


def parse_sweep(md: str):
    rows = []
    for line in md.split("\n"):
        m = ROW_RE.match(line.strip())
        if m:
            u, d, u_ana, u_sim, err = (float(g) for g in m.groups())
            rows.append({"U_current": u, "D": d, "U_analytical_table": u_ana,
                         "U_sim_table": u_sim, "error_pct_table": err})
    return rows


def main():
    raw = MD.read_bytes()
    import hashlib
    h = hashlib.sha256(raw).hexdigest()
    if not h.startswith(EXPECTED_HASH_PREFIX):
        raise SystemExit("report copy hash %s does not match the pinned source" % h)
    md = raw.decode("utf-8")
    rho_w, rho_i, cd_ratio = parse_params(md)
    rows = parse_sweep(md)
    if len(rows) != 9:
        raise SystemExit("expected 9 sweep rows, parsed %d" % len(rows))

    factor = math.sqrt(rho_w / rho_i) * cd_ratio
    max_dev_ana = 0.0
    max_dev_sim = 0.0
    for r in rows:
        r["U_anchor_recomputed"] = r["U_current"] * factor
        r["dev_analytical_rel"] = abs(r["U_analytical_table"] - r["U_anchor_recomputed"]) / r["U_anchor_recomputed"]
        r["dev_sim_rel"] = abs(r["U_sim_table"] - r["U_anchor_recomputed"]) / r["U_anchor_recomputed"]
        max_dev_ana = max(max_dev_ana, r["dev_analytical_rel"])
        max_dev_sim = max(max_dev_sim, r["dev_sim_rel"])

    baseline_anchor = 1.0 * factor
    out = {
        "report_id": "5776",
        "source_sha256": h,
        "scope": "arithmetic consistency of the report's own numbers against its own closed form; NOT platform verification, NOT physical validation",
        "inputs_parsed_from_source": {"rho_w": rho_w, "rho_i": rho_i, "cd_ratio_factor": cd_ratio,
                                      "sweep_rows": len(rows)},
        "closed_form": "U_anchor = U_current * sqrt(rho_w/rho_i) * sqrt(C_D_water/C_D_ice), CD ratio = 1.0",
        "factor": factor,
        "baseline_U_anchor_recomputed_m_s": baseline_anchor,
        "rows": rows,
        "summary": {
            "max_rel_dev_analytical_column": max_dev_ana,
            "max_rel_dev_sim_column": max_dev_sim,
            "max_rel_dev_analytical_pct": 100 * max_dev_ana,
            "max_rel_dev_sim_pct": 100 * max_dev_sim,
            "threshold_pct": 3.0,
            "analytical_column_within_3pct": 100 * max_dev_ana < 3.0,
            "sim_column_within_3pct": 100 * max_dev_sim < 3.0,
        },
        "caveats": [
            "The comparison target is the report's own closed form, i.e. a self-consistency check — agreement does not corroborate against experiment or an independent solver.",
            "The report's own discussion flags U_drift > U_current as unphysical for real floes (intentional verification construction); this audit neither confirms nor refutes that remark.",
            "Deviations are dominated by the 4-decimal rounding of the printed table, so 1e-5-level agreement is expected, not evidence of solver accuracy.",
        ],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT.relative_to(REPO)), "factor": round(factor, 6),
                      "baseline_anchor": round(baseline_anchor, 4),
                      "max_dev_analytical_pct": 100 * max_dev_ana,
                      "max_dev_sim_pct": 100 * max_dev_sim}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())