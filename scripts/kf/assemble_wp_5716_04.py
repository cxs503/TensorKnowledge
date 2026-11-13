#!/usr/bin/env python3
"""Assemble the wp-5716-04 deliverable: result envelope + report markdown.

Every number placed into the report comes from docs/kf/wp-5716-04/recompute.json
or from the verbatim quote table in review_wp_5716_04.py -- the assembler refuses
to run if a placeholder is left unfilled or if a substituted quote is not a verbatim
substring of the fetched markdown.

Usage: python3 scripts/kf/assemble_wp_5716_04.py [--offline]
Writes: docs/kf/wp-5716-04/kf_result.json   (machine-gate envelope)
        docs/kf/wp-5716-04/report.md        (six sections + exactly one json block)
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys

PKG = "wp-5716-04"
REPORT_ID = "5716"
SNAP = "docs/kf/wp-5716-04/source_5716.md"
RECOMP = "docs/kf/wp-5716-04/recompute.json"
REVIEW = "docs/kf/wp-5716-04/review_report.json"
TMPL = "docs/kf/wp-5716-04/report_body.tmpl.md"
OUT_ENV = "docs/kf/wp-5716-04/kf_result.json"
OUT_MD = "docs/kf/wp-5716-04/report.md"
SCENARIO = "ship.ice_navigation.campaign_gate"
MISSION = 15839


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args(argv)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import review_wp_5716_04 as rv  # noqa: E402  (reuse the quote table + tables)

    if a.offline:
        raw = open(SNAP, "rb").read()
    else:
        raw = rv.load_markdown(False)
    md = raw.decode("utf-8")
    sha = "sha256:" + hashlib.sha256(raw).hexdigest()
    if sha != rv.CONTRACT_HASH:
        raise SystemExit(f"source hash mismatch {sha}")

    rec = json.load(open(RECOMP, encoding="utf-8"))["recompute"]
    review = json.load(open(REVIEW, encoding="utf-8"))

    envelope = {
        "package_id": PKG,
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": sha,
            "source_field": "markdown",
            "producer": "m15839/agent/m15839",
            "emitted_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "notes": ("Independent red-team review of wp-5716-01. Context = report 5716 markdown "
                      "+ own arithmetic recomputation only; producer explanation excluded. "
                      "No claim is marked verified."),
        },
        "outputs": {"review_report.json": review},
    }

    sev = {}
    for f in review["findings"]:
        sev[f["severity"]] = sev.get(f["severity"], 0) + 1

    vals = {
        "sha": sha,
        "n_quotes": len(rv.Q),
        "n_findings": len(review["findings"]),
        "sev_high": sev.get("high", 0),
        "sev_med": sev.get("medium", 0),
        "sev_low": sev.get("low", 0),
        "n_blocking": len(review["blocking_findings"]),
        "n_corroborated": len(review["corroborated_claims"]),
        "cb_literal": rec["a1_cb_literal_no_density"]["cb"],
        "cb_rel_lit": rec["a1_cb_literal_no_density"]["rel_diff_pct_vs_0.82"],
        "cb_rho": rec["a2_cb_with_rho_1p025"]["cb"],
        "lb": rec["a3_geom_ratios"]["LB"],
        "bt": rec["a3_geom_ratios"]["BT"],
        "beta_b2": rec["a4_b2_beta_correction"]["beta_implied_B2"],
        "b2_12_4": rec["a4_b2_beta_correction"]["utilization_after_correction"]["SN_slope_m=3"],
        "d07_implied": rec["a7_d07_consistency"]["implied_peer_speed_kn"],
        "d1_mean": rec["a5_mean_speeds"]["D1_mean_kn_54.5h"],
        "c3_mean": rec["a5_mean_speeds"]["C3_mean_kn_63.3h"],
        "c3_mean_alt": rec["a5_mean_speeds"]["C3_mean_kn_68.2h"],
        "avg_kw": rec["a8_energy"]["avg_power_kW"],
        "avg_load": rec["a8_energy"]["avg_load_pct"],
        "kwh_nm": rec["a8_energy"]["energy_per_nm_kWh"],
        "a2_gain": rec["a13_a2_assimilation_gain_vs_ice_chart_pct"],
    }
    for k, v in rv.Q.items():
        vals["q_" + k] = v

    tmpl = open(TMPL, encoding="utf-8").read()
    body = tmpl
    for k, v in vals.items():
        body = body.replace("{{%s}}" % k, str(v))
    body = body.replace("{{ENVELOPE}}", json.dumps(envelope, ensure_ascii=False, indent=2))

    leftover = re.findall(r"\{\{[A-Za-z0-9_]+\}\}", body)
    if leftover:
        raise SystemExit("unfilled placeholders: %s" % sorted(set(leftover)))

    blocks = re.findall(r"```json\n(.*?)\n```", body, re.S)
    if len(blocks) != 1:
        raise SystemExit("report must carry exactly one json block, found %d" % len(blocks))
    if json.loads(blocks[0]) != envelope:
        raise SystemExit("inlined json block differs from envelope")

    # every quote that landed in the body must still be verbatim in the markdown
    bad = [q for q in rv.Q.values() if q not in md]
    if bad:
        raise SystemExit("quote drift: %s" % bad)

    os.makedirs(os.path.dirname(OUT_ENV), exist_ok=True)
    with open(OUT_ENV, "w", encoding="utf-8") as fh:
        json.dump(envelope, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(body)
    print("wrote", OUT_ENV, OUT_MD)
    print("envelope bytes", os.path.getsize(OUT_ENV), "report bytes", os.path.getsize(OUT_MD))
    print("scenario", SCENARIO, "mission", MISSION, "quotes", len(rv.Q))
    return 0


if __name__ == "__main__":
    sys.exit(main())