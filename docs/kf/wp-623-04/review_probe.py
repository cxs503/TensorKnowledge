#!/usr/bin/env python3
"""Red-team probes on wp-623-01 + upstream arithmetic re-derivation.

Complements verify_upstream.py: cross-file consistency, degenerate-quote
accounting, figure endpoint reproduction, and an independent recomputation of
the report's own headline numbers straight out of its markdown table
(no hand transcription).

Outputs: docs/kf/wp-623-04/review_probe.json
Run:  TENSOR_KF_TOKEN=... python3 docs/kf/wp-623-04/review_probe.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
UP = ROOT / "docs/kf/wp-623-01"
OUT = Path(__file__).resolve().parent / "review_probe.json"
BASE = os.environ["TENSOR_API_BASE"]
TOKEN = os.environ["TENSOR_KF_TOKEN"]


def api(path: str):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + TOKEN})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def probe(path: str):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + TOKEN})
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return {"http_status": r.status, "bytes": len(r.read())}
    except urllib.error.HTTPError as e:
        return {"http_status": e.code, "bytes": len(e.read())}


def main() -> int:
    md = api("/tensor/reports/623")["markdown"]
    lines = md.rstrip("\n").split("\n")
    manifest = json.loads((UP / "asset_manifest.json").read_text())
    kfres = json.loads((UP / "kf_result.json").read_text())
    out: dict = {"checks": {}, "findings": []}

    def chk(name, ok, detail):
        out["checks"][name] = {"ok": bool(ok), "detail": detail}

    # --- 1. cross-file consistency: embedded outputs == shipped files ---------
    same = {}
    for name, embedded in (kfres.get("outputs") or {}).items():
        p = UP / name
        same[name] = (p.is_file() and json.loads(p.read_text()) == embedded)
    chk("P1.kf_result_outputs_equal_shipped_files", all(same.values()), same)

    # --- 2. claimed occurrences_in_source are true --------------------------
    bad = []
    for l in manifest["locators"]:
        a = next((x for x in manifest["assets"] if x["asset_id"] == l["asset_id"]), None)
        q = (a or {}).get("locator", {}).get("quote")
        if q is None:
            continue
        if md.count(q) != l.get("occurrences_in_source"):
            bad.append({"asset_id": l["asset_id"], "claimed": l.get("occurrences_in_source"),
                        "recomputed": md.count(q)})
    chk("P2.occurrence_counts_true", not bad, f"mismatches={bad}")

    # --- 3. unresolved list matches the unresolved assets --------------------
    unres_assets = sorted(a["asset_id"] for a in manifest["assets"]
                          if a["resolution"]["status"] == "unresolved")
    unres_list = sorted(u["asset_id"] for u in manifest.get("unresolved", []))
    chk("P3.unresolved_list_complete", unres_assets == unres_list,
        f"assets={len(unres_assets)} list={len(unres_list)} diff="
        f"{sorted(set(unres_assets) ^ set(unres_list))}")

    # --- 4. degenerate-quote accounting -------------------------------------
    facts = manifest.get("identity_facts", [])
    vac = [f["fact_id"] for f in facts if len(f["quote"]) < 12]
    out["degenerate_quote_facts"] = {
        "identity_facts_total": len(facts), "vacuously_true": vac,
        "locators_claimed_resolved": len(manifest["locators"]),
        "non_vacuous_locators": len(manifest["locators"]) - len(vac),
    }
    chk("P4.vacuous_quote_counted_resolved", not vac, f"vacuously true identity_facts={vac}")

    # --- 5. record fields the manifest cites --------------------------------
    rec = api("/tensor/reports/623")
    fig_probe = {f["name"]: probe(f"/tensor/reports/623/figures/{f['name']}")
                 for f in rec.get("figures") or []}
    claimed = manifest["source"]["platform_attachment_probes"]["figure_probe"]
    chk("P5.figure_probe_reproduced", fig_probe == claimed, f"live={fig_probe} claimed={claimed}")

    # --- 6. independent re-derivation of the report's own table -------------
    rows = {}
    for ln in lines:
        m = re.match(r"^\| (scale_\d+k) \| ([\d,]+) \| ([\d.]+) \| (\d+) \| ([\d.]+) \| ([\d,]+) \|$", ln)
        if m:
            rows[m.group(1)] = {"n": int(m.group(2).replace(",", "")), "init_s": float(m.group(3)),
                                "steps": int(m.group(4)), "wall_s": float(m.group(5)),
                                "ms_step_reported": int(m.group(6).replace(",", ""))}
    derived = {k: {"ms_step": v["wall_s"] * 1000.0 / v["steps"],
                   "reported": v["ms_step_reported"],
                   "rel_err": abs(v["wall_s"] * 1000.0 / v["steps"] - v["ms_step_reported"]) / v["ms_step_reported"]}
               for k, v in rows.items()}
    chk("P6a.ms_per_step_arithmetic", all(d["rel_err"] < 0.005 for d in derived.values()), derived)

    base, top = rows["scale_10k"], rows["scale_100k"]
    ideal = derived["scale_10k"]["ms_step"] * top["n"] / base["n"]
    ratio = derived["scale_100k"]["ms_step"] / ideal
    chk("P6b.ratio_1p12_reproduced", abs(ratio - 1.12) < 0.01,
        f"ideal={ideal:.1f}ms actual={derived['scale_100k']['ms_step']:.1f}ms ratio={ratio:.4f} "
        f"(report text: 14,180 and 1.12)")

    # local scaling exponents: the chord ratio above is blind to non-monotonicity
    def expo(lo, hi):
        return math.log(derived[hi]["ms_step"] / derived[lo]["ms_step"]) / math.log(rows[hi]["n"] / rows[lo]["n"])
    out["scaling"] = {
        "exponent_10k_50k": round(expo("scale_10k", "scale_50k"), 3),
        "exponent_50k_100k": round(expo("scale_50k", "scale_100k"), 3),
        "chord_ratio_vs_ideal_from_10k": round(ratio, 4),
        "timed_steps_per_case": {k: rows[k]["steps"] for k in rows},
        "cost_per_particle_us": {k: round(derived[k]["ms_step"] / rows[k]["n"] * 1000, 3) for k in rows},
    }

    # --- 7. internal contradiction on reproducibility (100k) ---------------
    repro_l = [i + 1 for i, l in enumerate(lines) if "identical SHA-256 state digests" in l]
    limit_l = [i + 1 for i, l in enumerate(lines) if "not the full reproducibility verification" in l]
    out["contradiction"] = {
        "reproducibility_claim_lines": repro_l,
        "reproducibility_claim_quote": lines[repro_l[0] - 1] if repro_l else None,
        "limitation_lines": limit_l,
        "limitation_quote": lines[limit_l[0] - 1] if limit_l else None,
        "verdict_row_quote": next((l for l in lines if l.startswith("| reproducible_hash |")), None),
    }
    chk("P7.no_reproducibility_contradiction", not (repro_l and limit_l),
        f"claim@{repro_l} vs limitation@{limit_l}")

    # --- 8. dissipative settings vs exact-zero energy drift ----------------
    diss = [l for l in lines if "contact_damping=" in l]
    drift = [l for l in lines if re.match(r"^\| scale_\d+k \| 0\.00e\+00", l)]
    out["energy_metric"] = {
        "dissipative_settings_quote": diss[0] if diss else None,
        "zero_drift_rows": len(drift),
        "confirmatory_sentence": next((l for l in lines if "Zero energy drift confirms" in l), None),
    }

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"checks": {k: v["ok"] for k, v in out["checks"].items()}}, indent=1))
    print(json.dumps({k: out[k] for k in ("scaling", "contradiction")}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
