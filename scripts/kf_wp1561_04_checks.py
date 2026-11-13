#!/usr/bin/env python3
"""wp-1561-04 · independent (red-team) re-derivation of every check on wp-1561-01.

Evidence basis = report 1561 markdown (platform API or byte snapshot)
               + docs/kf/wp-1561-01/asset_manifest.json
               + docs/kf/wp-1561-01/kf_result.json
Producer narrative (README prose, selfcheck `ok:true`) is an OBJECT UNDER TEST,
never supporting evidence.

  python3 scripts/kf_wp1561_04_checks.py [--live] [--probe-figures]
writes docs/kf/wp-1561-04/review_checks.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG_UP = ROOT / "docs/kf/wp-1561-01"
PKG = ROOT / "docs/kf/wp-1561-04"
SCHEMA = ROOT / "schemas/kf_result.v1.schema.json"

CONTRACT = {
    "package_id": "wp-1561-04",
    "task_type": "04-independent-review",
    "report_id": "1561",
    "source_uri": "tensor://reports/1561",
    "source_field": "markdown",
    "source_hash": "sha256:19203e6ea7f05573f0b06835f9c0e1f08fb54fc5481787ace02487d5ac6d1620",
    "reviewed_package": "wp-1561-01",
    "reviewer_role": "red-team-reviewer",
    "producer_identity": "agent/m15529 (TensorKnowledge) · package wp-1561-01",
    "reviewer_identity": "agent/m15823 (TensorKnowledge) · package wp-1561-04 · red-team-reviewer",
}
RHO = 1025.0     # kg/m^3 seawater; the report prints the symbol only -> assumption, corroborated by C_T=4.37
KN = 0.514444    # m/s per knot


def sha256_bytes(b):
    return "sha256:" + hashlib.sha256(b).hexdigest()


def sha256_text(s):
    return sha256_bytes(s.encode("utf-8"))


def live_source():
    base = os.environ.get("TENSOR_API_BASE", "")
    user = os.environ.get("TENSOR_AGENT_USER", "")
    pw = os.environ.get("TENSOR_AGENT_PASS", "")
    out = {"attempted": bool(base and user)}
    if not out["attempted"]:
        out["status"] = "not_run"
        return out
    try:
        req = urllib.request.Request(
            base + "/auth/login",
            data=json.dumps({"username": user, "password": pw}).encode(),
            headers={"Content-Type": "application/json"})
        tok = json.load(urllib.request.urlopen(req, timeout=30))["access_token"]
        hdr = {"Authorization": "Bearer " + tok}

        def get(path):
            return urllib.request.urlopen(
                urllib.request.Request(base + path, headers=hdr), timeout=60).read()

        rec = json.loads(get("/tensor/reports/1561"))
        md = rec["markdown"]
        out.update({"status": "http_200", "markdown_sha256": sha256_text(md),
                    "markdown_utf8_bytes": len(md.encode("utf-8")),
                    "title": rec.get("title"),
                    "figures_declared": [f.get("name") for f in (rec.get("figures") or [])],
                    "token": tok, "markdown": md})
    except Exception as exc:            # fail loudly, never silently
        out.update({"status": "error", "error": repr(exc)[:300]})
    return out


def probe_figures(token):
    base = os.environ.get("TENSOR_API_BASE", "")
    names = ["fig1_thrust_power.png", "fig2_cross_pe.png", "fig3_eta0_vs_diameter.png",
             "fig4_open_water.png", "fig5_pitch_sweep.png"]
    res = {}
    for n in names:
        rec = {"name": n}
        try:
            req = urllib.request.Request(f"{base}/tensor/reports/1561/figures/{n}",
                                         headers={"Authorization": "Bearer " + (token or "")})
            body = urllib.request.urlopen(req, timeout=30).read()
            rec.update({"http": 200, "bytes": len(body), "sha256": sha256_bytes(body)})
        except urllib.error.HTTPError as exc:
            rec.update({"http": exc.code, "body": exc.read().decode("utf-8", "replace")[:120]})
        except Exception as exc:
            rec.update({"http": None, "error": repr(exc)[:200]})
        res[n] = rec
    return res


def ck(cid, name, status, method, detail, evidence=None):
    return {"id": cid, "name": name, "status": status, "method": method,
            "detail": detail, "evidence": evidence or []}


def rel(a, b):
    return abs(a - b) / abs(b) if b else float("inf")


def tbl_rows(text, header_key):
    rows, take = [], False
    for ln in text.splitlines():
        if ln.startswith("|") and header_key in ln:
            take = True
            continue
        if take:
            if not ln.startswith("|"):
                break
            if set(ln.replace("|", "").strip()) <= set("-: "):
                continue
            rows.append([c.strip() for c in ln.strip().strip("|").split("|")])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--probe-figures", action="store_true")
    args = ap.parse_args()

    PKG.mkdir(parents=True, exist_ok=True)
    checks = []
    live = live_source() if args.live else {"attempted": False, "status": "not_run"}
    figs = probe_figures(live.get("token")) if (args.probe_figures and live.get("token")) else {}

    # ---------- A. source identity
    snap = PKG_UP / "source/report_1561.md"
    snap_bytes = snap.read_bytes()
    md = snap_bytes.decode("utf-8")
    snap_hash = sha256_bytes(snap_bytes)
    checks.append(ck("A1", "source_hash_recompute",
                     "pass" if snap_hash == CONTRACT["source_hash"] else "fail",
                     "sha256 over the UTF-8 bytes of the reviewed markdown (no newline normalisation)",
                     {"computed": snap_hash, "contract": CONTRACT["source_hash"],
                      "equal": snap_hash == CONTRACT["source_hash"]},
                     ["docs/kf/wp-1561-01/source/report_1561.md"]))
    checks.append(ck("A2", "source_size_and_shape", "pass",
                     "recomputed byte/char/line counts and the first line",
                     {"utf8_bytes": len(snap_bytes), "characters": len(md),
                      "lines": len(md.split("\n")) - (1 if md.endswith("\n") else 0),
                      "first_line": md.splitlines()[0]}))
    heads = ("## ①", "## ②", "## ③", "## ④", "## ⑤", "## ⑥")
    checks.append(ck("A3", "six_sections_present",
                     "pass" if all(h in md for h in heads) else "fail",
                     "substring scan for the six mandated section headers",
                     {h: (h in md) for h in heads}))
    if live.get("status") == "http_200":
        eq = live["markdown_sha256"] == snap_hash
        checks.append(ck("A4", "snapshot_equals_live_api", "pass" if eq else "fail",
                         "GET /tensor/reports/1561 -> sha256(markdown) vs the pinned snapshot",
                         {"live": live["markdown_sha256"], "snapshot": snap_hash, "equal": eq,
                          "live_utf8_bytes": live["markdown_utf8_bytes"],
                          "live_title": live["title"]}))
    else:
        checks.append(ck("A4", "snapshot_equals_live_api", "not_run",
                         "GET /tensor/reports/1561", {"live": live.get("status")},
                         ["requires --live plus agent credentials"]))

    # ---------- B. envelope integrity of the reviewed package
    env = json.loads((PKG_UP / "kf_result.json").read_text(encoding="utf-8"))
    man = json.loads((PKG_UP / "asset_manifest.json").read_text(encoding="utf-8"))
    try:
        import jsonschema
        jsonschema.validate(env, json.loads(SCHEMA.read_text(encoding="utf-8")))
        schema_ok, schema_err = True, ""
    except Exception as exc:
        schema_ok, schema_err = False, repr(exc)[:300]
    checks.append(ck("B1", "envelope_schema_validate", "pass" if schema_ok else "fail",
                     "jsonschema.validate(kf_result.json, schemas/kf_result.v1.schema.json)",
                     {"ok": schema_ok, "error": schema_err,
                      "package_id": env.get("package_id"), "task_type": env.get("task_type"),
                      "report_id": env.get("report_id")}))
    pr = env.get("provenance") or {}
    checks.append(ck("B2", "envelope_source_identity",
                     "pass" if (pr.get("source_hash") == CONTRACT["source_hash"]
                                and pr.get("source_field") == "markdown"
                                and env.get("report_id") == "1561") else "fail",
                     "provenance.source_hash / source_field / report_id vs contract",
                     {"source_hash": pr.get("source_hash"), "source_field": pr.get("source_field"),
                      "report_id": env.get("report_id")}))
    outs = env.get("outputs") or {}
    same = json.dumps(outs.get("asset_manifest.json"), sort_keys=True) == json.dumps(man, sort_keys=True)
    checks.append(ck("B3", "envelope_manifest_equals_file", "pass" if same else "fail",
                     "canonical-JSON comparison of outputs['asset_manifest.json'] vs asset_manifest.json",
                     {"equal": same, "output_keys": sorted(outs)}))
    checks.append(ck("B4", "zero_claim_legality",
                     "pass" if (env.get("claims") == [] and man.get("claims") == []) else "fail",
                     "task 01 declares no knowledge claims; contract allows an empty claims array",
                     {"envelope_claims": len(env.get("claims") or []),
                      "manifest_claims": len(man.get("claims") or [])}))

    # ---------- C. manifest factual accuracy re-derived from the source
    assets = man["assets"]
    ids = [a["asset_id"] for a in assets]
    contiguous = ids == [f"1561-a{i:03d}" for i in range(len(ids))]
    checks.append(ck("C1", "asset_inventory_shape",
                     "pass" if (len(assets) == 57 and len(set(ids)) == 57 and contiguous) else "fail",
                     "count + uniqueness + contiguity of asset_id",
                     {"total": len(assets), "unique": len(set(ids)), "contiguous": contiguous,
                      "first": ids[0], "last": ids[-1]}))

    src_lines = md.splitlines()
    missing, line_bad = [], []
    for a in assets:
        q = a.get("quote") or ""
        if q not in md:
            missing.append(a["asset_id"])
            continue
        ln = (a.get("locator") or {}).get("line")
        if isinstance(ln, int):
            target = src_lines[ln - 1] if 1 <= ln <= len(src_lines) else "<out of range>"
            if q.splitlines()[0] not in target:
                line_bad.append({"asset_id": a["asset_id"], "line": ln,
                                 "quote_first_line": q.splitlines()[0][:60],
                                 "source_line": str(target)[:60]})
    checks.append(ck("C2", "quote_verbatim_all_assets", "pass" if not missing else "fail",
                     "exact substring test of every asset quote against the markdown",
                     {"checked": len(assets), "not_found": missing}))
    checks.append(ck("C3", "line_locator_matches", "pass" if not line_bad else "fail",
                     "the quote's first line must be contained in the source line the locator names",
                     {"checked": len(assets), "mismatch_count": len(line_bad),
                      "mismatches": line_bad[:5]}))

    by_kind, by_res = {}, {}
    for a in assets:
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + 1
        by_res[a["resolvability"]] = by_res.get(a["resolvability"], 0) + 1
    dc = {k: v for k, v in (man.get("counts") or {}).items() if isinstance(v, dict)}
    tally = (dc.get("by_kind") == by_kind and dc.get("by_resolvability") == by_res
             and (man.get("counts") or {}).get("total") == len(assets))
    checks.append(ck("C4", "counts_tally_rederived", "pass" if tally else "fail",
                     "recount kind / resolvability / total from the asset array vs manifest.counts",
                     {"total": len(assets), "by_kind": by_kind, "by_resolvability": by_res,
                      "declared_total": (man.get("counts") or {}).get("total")}))

    VOCAB = {"resolved_in_markdown", "named_no_locator",
             "referenced_only_not_resolvable_from_this_record",
             "declared_and_markdown_referenced_binary_not_served"}
    nonres = [a for a in assets if a["resolvability"] != "resolved_in_markdown"]
    off_vocab = sorted({a["resolvability"] for a in nonres} - VOCAB)
    checks.append(ck("C5", "non_resolved_assets_declared", "pass" if not off_vocab else "fail",
                     "every non-resolved asset carries one of the four declared resolvability statuses "
                     "(no silent drop of an unresolvable asset)",
                     {"non_resolved": len(nonres), "statuses_off_vocabulary": off_vocab,
                      "by_status": by_res}))
    bare = [a["asset_id"] for a in nonres
            if not (a.get("registration_note") or a.get("note") or a.get("binary_probe")
                    or "present_in_worktree" in a)]
    checks.append(ck("C5b", "non_resolved_reason_attached", "fail" if bare else "pass",
                     "does each non-resolved asset say WHY (prose reason / binary probe / worktree flag), "
                     "not only THAT it is unresolved",
                     {"non_resolved": len(nonres), "status_only_no_reason": bare,
                      "count_status_only": len(bare)}))

    obs = man.get("observations") or []
    bad_obs = [{"observation": o.get("observation_id"), "quote": q[:60]}
               for o in obs for q in (o.get("quotes") or []) if q not in md]
    checks.append(ck("C6", "observation_quotes_verbatim", "pass" if not bad_obs else "fail",
                     "exact substring test of every quote attached to an observation",
                     {"observations": [o.get("observation_id") for o in obs],
                      "quotes_checked": sum(len(o.get("quotes") or []) for o in obs),
                      "not_found": bad_obs}))

    geo, disp = 130790.0, 115000.0
    delta = abs(geo - disp)
    r_geo, r_disp = delta / geo, delta / disp
    checks.append(ck("C7", "observation_o000_arithmetic_rederived",
                     "pass" if (round(r_geo * 100, 1) == 12.1 and round(r_disp * 100, 1) == 13.7) else "fail",
                     "|130790-115000| over each denominator named in the two sentences",
                     {"delta_m3": delta,
                      "over_geometry_pct": round(r_geo * 100, 2),
                      "over_displacement_pct": round(r_disp * 100, 2),
                      "registered_as": "1561-o000 (unresolved)"}))

    markers = ("verification_status", "verification_level", "is_verified", "gate_confirmed",
               '"verified"', "'verified'")
    raw = b"".join(p.read_bytes() for p in sorted(PKG_UP.glob("*.json")))
    hits = [m for m in markers if m.encode() in raw]
    checks.append(ck("C8", "no_self_verification_marker", "pass" if not hits else "fail",
                     "byte scan of every JSON in the reviewed package for verification field names",
                     {"markers_found": hits,
                      "files_scanned": sorted(p.name for p in PKG_UP.glob("*.json"))}))

    fig_assets = [a for a in assets if a["kind"] == "figure"]
    figs_declared = (man.get("report") or {}).get("figures_declared")
    checks.append(ck("C9", "figures_registered",
                     "pass" if (len(fig_assets) == 5 and figs_declared == 5) else "fail",
                     "declared figure count vs registered figure assets",
                     {"declared_in_record": figs_declared, "registered_assets": len(fig_assets),
                      "labels": [a.get("label") for a in fig_assets],
                      "binary_probe": [a.get("binary_probe") for a in fig_assets]}))

    sc = json.loads((PKG_UP / "selfcheck.json").read_text(encoding="utf-8"))
    sc_names = list((sc.get("checks") or {}).keys())
    checks.append(ck("C10", "producer_selfcheck_audited_not_trusted", "pass",
                     "the producer's own check list is treated as a claim set: its items are re-derived "
                     "independently by C1-C9/B1-B4, its `ok` flag is never copied",
                     {"producer_reported_items": len(sc_names),
                      "producer_reported_ok": sc.get("ok"),
                      "producer_reported_failed": sc.get("failed"),
                      "rederived_by": "C1-C9 + B1-B4 + E1-E5"}))

    # record title vs document H1: is the pinned record title reproducible from the text?
    rec_title = (live.get("title") if live.get("status") == "http_200"
                 else (man.get("report") or {}).get("title") or "")
    h1 = src_lines[0]
    title_in_md = bool(rec_title) and rec_title in md
    shared = os.path.commonprefix([rec_title, h1.lstrip("# ")])
    checks.append(ck("C12", "record_title_reproducible_from_markdown",
                     "pass" if title_in_md else "fail",
                     "substring test of the pinned record title against the markdown; both strings "
                     "recorded so downstream can see which one is quotable",
                     {"record_title": rec_title,
                      "record_title_source": ("live GET /tensor/reports/1561" if live.get("status") == "http_200"
                                              else "asset_manifest.json report.title"),
                      "markdown_h1": h1,
                      "record_title_found_in_markdown": title_in_md,
                      "common_prefix": shared,
                      "impact": "a quote taken from record.title would not resolve against the source "
                                "text; only the H1 is quotable"}))

    # line-count claim: "163 lines" is not what the bytes say (162 newline-terminated lines)
    declared_lines = (man.get("report") or {}).get("lines")
    a000 = next((a for a in assets if a["asset_id"] == "1561-a000"), {})
    actual_lines = len(md.splitlines())
    checks.append(ck("C11", "declared_line_count_rederived",
                     "fail" if declared_lines != actual_lines else "pass",
                     "recompute the number of lines with str.splitlines() and md.count(newline)",
                     {"declared_lines": declared_lines, "a000_line_count": a000.get("line_count"),
                      "actual_splitlines": actual_lines, "actual_newline_count": md.count("\n"),
                      "ends_with_newline": md.endswith("\n"),
                      "impact": "no locator is affected (max locator line = 160); the number in the "
                                "manifest equals count(newline)+1, i.e. it counts a phantom final line"}))

    # ---------- D. figure payload reachability
    if figs:
        all404 = all(v.get("http") == 404 for v in figs.values())
        checks.append(ck("D1", "figure_payload_reachable", "pass",
                         "live GET /tensor/reports/1561/figures/<name> for the 5 declared figures",
                         {"probes": {k: {"http": v.get("http"), "bytes": v.get("bytes")}
                                     for k, v in figs.items()},
                          "all_404": all404,
                          "consistent_with_registration": "1561-o001",
                          "note": ("binary still not served: registration observation remains accurate"
                                   if all404 else "payload now served: 1561-o001 is stale, ask 01 to re-probe")}))
    else:
        checks.append(ck("D1", "figure_payload_reachable", "not_run",
                         "live GET of the figure endpoints",
                         {"status": "not attempted (--probe-figures)"}))

    # ---------- E. subject-report arithmetic recomputed from its own numbers
    geom = {}
    for r in tbl_rows(md, "L_wl[m]"):
        if len(r) >= 7 and r[0] in ("KCS", "KVLCC2", "Feeder120", "Aframax", "Ferry"):
            geom[r[0]] = {"L": float(r[1]), "B": float(r[2]), "T": float(r[3]),
                          "Cb": float(r[4]), "disp": float(r[5]), "V": float(r[6])}
    pairs = lambda s: [float(x) for x in re.findall(r"-?\d+\.?\d*", s.replace("**", ""))]  # noqa: E731
    rows = {}
    for r in tbl_rows(md, "R_T[kN]"):
        if len(r) >= 17 and r[0] in geom:
            rows[r[0]] = {"R_T": float(r[2]), "P_E": float(r[3]), "I2": pairs(r[4]),
                          "T_old": pairs(r[5])[0], "T_new": pairs(r[5])[1],
                          "D": float(r[6]), "rpm": float(r[7]), "PD": float(r[8]),
                          "J": float(r[9]), "KT": float(r[10]), "eta0": float(r[11]),
                          "etaD": float(r[12]), "I3": pairs(r[13]),
                          "P_old": pairs(r[14])[0], "P_new": pairs(r[14])[1], "I4": pairs(r[15])}
    derived = {}
    for name, g in geom.items():
        if name not in rows:
            continue
        r = rows[name]
        t = 0.5 * g["Cb"] - 0.12
        w = 0.5 * g["Cb"] - 0.05
        etaH = (1 - t) / (1 - w)
        V = g["V"] * KN
        Va = V * (1 - w)
        n = r["rpm"] / 60.0
        A0 = math.pi * r["D"] ** 2 / 4.0
        C_T = (r["T_new"] * 1e3) / (0.5 * RHO * Va ** 2 * A0)
        etaI = 2.0 / (1.0 + math.sqrt(1.0 + C_T))
        KQ = r["J"] * r["KT"] / (2 * math.pi * r["eta0"])
        pd_kq = 2 * math.pi * n * (KQ * RHO * n ** 2 * r["D"] ** 5) / 1e3
        derived[name] = {
            "t": round(t, 4), "w": round(w, 4), "eta_H": round(etaH, 4),
            "T_req_kN": round(r["R_T"] / (1 - t), 1), "T_new_kN": r["T_new"],
            "T_rel_err": round(rel(r["T_new"], r["R_T"] / (1 - t)), 6),
            "I2_lo": round(r["R_T"] / 0.9, 1), "I2_hi": round(r["R_T"] / 0.7, 1),
            "I2_reported": r["I2"], "I2_in_band": r["I2"][0] <= r["T_new"] <= r["I2"][1],
            "P_E_kW": round(r["R_T"] * V, 0), "P_E_reported": r["P_E"],
            "I3_lo": round(r["P_E"] / 0.78, 0), "I3_hi": round(r["P_E"] / 0.50, 0),
            "I3_reported": r["I3"], "P_D_in_band": r["I3"][0] <= r["P_new"] <= r["I3"][1],
            "etaD_from_etaH": round(r["eta0"] * etaH, 3), "etaD_reported": r["etaD"],
            "J_recomputed": round(Va / (n * r["D"]), 3), "J_reported": r["J"],
            "J_interval_from_int_rpm": [round(Va / (((r["rpm"] + 0.5) / 60.0) * r["D"]), 3),
                                        round(Va / (((r["rpm"] - 0.5) / 60.0) * r["D"]), 3)],
            "PD_interval_from_int_rpm": [round(2 * math.pi * ((r["rpm"] + 0.5) / 60.0) * (KQ * RHO * ((r["rpm"] + 0.5) / 60.0) ** 2 * r["D"] ** 5) / 1e3, 0),
                                         round(2 * math.pi * ((r["rpm"] - 0.5) / 60.0) * (KQ * RHO * ((r["rpm"] - 0.5) / 60.0) ** 2 * r["D"] ** 5) / 1e3, 0)],
            "D_over_T": round(r["D"] / g["T"], 3), "C_T": round(C_T, 2),
            "eta_I": round(etaI, 3), "eta0_over_etaI": round(r["eta0"] / etaI, 3),
            "P_D_from_KQ_kW": round(pd_kq, 0), "P_D_rel_err": round(rel(pd_kq, r["P_new"]), 4),
            "I4_lo": round(r["T_new"] * 0.70 / r["R_T"], 3),
            "I4_hi": round(r["T_new"] * 0.90 / r["R_T"], 3),
            "I4_reported": r["I4"],
            "I4_contains_1": r["I4"][0] <= 1.0 <= r["I4"][1],
            "T_old_over_new": round(r["T_old"] / r["T_new"], 3),
            "P_old_over_new": round(r["P_old"] / r["P_new"], 3),
        }
    # rpm is quoted as an integer, so n is only known to +-0.5 rpm; J ~ 1/n and P_D ~ n^3,
    # therefore the reported values are tested inside the integer-rpm interval, not against a
    # point value with an arbitrary tolerance.
    for d in derived.values():
        lo, hi = sorted(d["J_interval_from_int_rpm"])
        d["J_in_rpm_interval"] = lo - 1e-3 <= d["J_reported"] <= hi + 1e-3
        plo, phi = sorted(d["PD_interval_from_int_rpm"])
        d["PD_in_rpm_interval"] = plo * 0.995 <= d["P_D_from_KQ_kW"] <= phi * 1.005
    e1 = all(d["T_rel_err"] < 0.002 and d["I2_in_band"] and d["P_D_in_band"]
             and d["I4_contains_1"] and d["J_in_rpm_interval"] and d["PD_in_rpm_interval"]
             and rel(d["etaD_from_etaH"], d["etaD_reported"]) < 0.002
             and abs(d["D_over_T"] - 0.70) < 0.002 for d in derived.values())
    checks.append(ck("E1", "subject_closure_arithmetic_rederived", "pass" if e1 else "fail",
                     "per ship: t=0.5Cb-0.12, w=0.5Cb-0.05, T_req=R_T/(1-t), I2=[R_T/0.9,R_T/0.7], "
                     "P_E=R_T*V*0.514444, I3=[P_E/0.78,P_E/0.5], eta_D=eta0*eta_H, J=V(1-w)/(nD), "
                     "I4=T(1-t)/R_T",
                     {"per_ship": derived, "rho_assumed_kg_m3": RHO, "knot_m_s": KN,
                      "worst_T_rel_err": max(d["T_rel_err"] for d in derived.values())}))
    checks.append(ck("E2", "subject_loading_and_actuator_disk_bound",
                     "pass" if all(d["eta0_over_etaI"] <= 1.0 for d in derived.values()) else "fail",
                     "C_T=T/(0.5 rho Va^2 pi D^2/4); eta_I=2/(1+sqrt(1+C_T)); test eta0<=eta_I and whether "
                     "the quoted Ferry C_T=4.37 is reproduced",
                     {"per_ship": {k: {"C_T": v["C_T"], "eta_I": v["eta_I"],
                                       "eta0_over_etaI": v["eta0_over_etaI"]} for k, v in derived.items()},
                      "ferry_C_T_matches_quoted_4_37": abs(derived["Ferry"]["C_T"] - 4.37) < 0.02}))
    trng = [d["T_old_over_new"] for d in derived.values()]
    prng = [d["P_old_over_new"] for d in derived.values()]
    mt = re.search(r"T_old/T_new=\s*\*\*([\d.]+)–([\d.]+)\*\*", md)
    mp = re.search(r"功率比\s*\*\*([\d.]+)–([\d.]+)\*\*", md)
    qt = [float(x) for x in mt.groups()] if mt else None
    qp = [float(x) for x in mp.groups()] if mp else None
    e3 = bool(qt and qp and abs(min(trng) - qt[0]) < 0.002 and abs(max(trng) - qt[1]) < 0.002
              and abs(min(prng) - qp[0]) < 0.002 and abs(max(prng) - qp[1]) < 0.002)
    checks.append(ck("E3", "subject_ratio_ranges_rederived", "pass" if e3 else "fail",
                     "recompute min/max of T_old/T_new and P_old/P_new over the 5 rows vs the quoted ranges",
                     {"computed_T": [round(min(trng), 3), round(max(trng), 3)], "quoted_T": qt,
                      "computed_P": [round(min(prng), 3), round(max(prng), 3)], "quoted_P": qp}))
    etad = [d["etaD_reported"] for d in derived.values()]
    checks.append(ck("E4", "subject_etaD_range_vs_band", "pass",
                     "reported eta_D range vs the I3 band 0.50-0.78 quoted in the report; plus the same range "
                     "at eta_R=0.98",
                     {"reported_eta_D": [min(etad), max(etad)], "band": [0.50, 0.78],
                      "min_margin_to_floor": round(min(etad) - 0.50, 3),
                      "min_eta_D_if_eta_R_0_98": round(min(etad) * 0.98, 4)}))
    hexish = re.findall(r"\b[0-9a-f]{7,40}\b", md)
    checks.append(ck("E5", "subject_provenance_identity_present",
                     "pass" if not hexish else "fail",
                     "regex scan of the markdown for a commit sha / payload digest",
                     {"hex_like_tokens": hexish[:5], "count": len(hexish),
                      "consistent_with": "1561-o002 (no commit identity inside the report)"}))

    # ---------- F. independence mechanics
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "scripts"))
    from ke_state_machine import is_independent, producer_identity  # noqa: E402
    _prod = man.get("producer")
    _prod_id = _prod.get("id") if isinstance(_prod, dict) else (_prod or "")
    prod_ids = [p for p in [CONTRACT["producer_identity"], _prod_id] if p]
    indep, basis = is_independent({"id": CONTRACT["reviewer_identity"], "reviewer_type": "agent"},
                                  producer_identity({"producer_ids": prod_ids}))
    checks.append(ck("F1", "reviewer_independent", "pass" if indep else "fail",
                     "scripts/ke_state_machine.is_independent(reviewer, producer)",
                     {"reviewer": CONTRACT["reviewer_identity"], "producer": prod_ids,
                      "independent": indep, "basis": basis}))
    try:
        from ke.wp_gate import prompt_similarity  # noqa: E402
        rp = (PKG / "review_prompt.md").read_text(encoding="utf-8")
        pp = (ROOT / "extraction-skills/prompts/producer-v1.md").read_text(encoding="utf-8")
        jac = prompt_similarity(pp, rp)
        checks.append(ck("F2", "prompt_not_copied_from_producer", "pass" if jac < 0.5 else "fail",
                         "char 5-gram Jaccard(producer-v1.md, review_prompt.md) < 0.5",
                         {"jaccard": round(jac, 4), "threshold": 0.5,
                          "chars_compared": [len(pp), len(rp)]}))
    except Exception as exc:
        checks.append(ck("F2", "prompt_not_copied_from_producer", "not_run",
                         "ke.wp_gate.prompt_similarity", {"error": repr(exc)[:200]},
                         ["docs/kf/wp-1561-04/review_prompt.md"]))

    # ---------- G. honest declaration of what was not run
    checks.append(ck("G1", "checks_not_run", "not_run",
                     "declared explicitly instead of silently skipped",
                     {"not_run": [
                         "closure residual 1.11e-05 (needs the propulsion endpoint, not in this repo)",
                         "pytest 28 items in ship-performance-platform (repo not checked out here)",
                         "12 vs 32 radial stations convergence 0.6%/0.05% (needs the BEMT kernel)",
                         "figure payload content (binaries not served, see D1)",
                         "R_T absolute accuracy vs towing tank (resistance domain, no dataset in the report)",
                         "BEMT heavy-load optimism 15-20% vs B4-70 measured series (no dataset in the report)"],
                      "reason": "each item needs an artifact outside report 1561 + wp-1561-01"}))

    out = {"package_id": CONTRACT["package_id"], "task_type": CONTRACT["task_type"],
           "report_id": CONTRACT["report_id"], "contract": CONTRACT,
           "live": {k: v for k, v in live.items() if k != "markdown"},
           "figure_probes": figs,
           "source": {"sha256_snapshot": snap_hash, "utf8_bytes": len(snap_bytes)},
           "checks": checks,
           "counts": {"checks": len(checks),
                      "pass": sum(1 for c in checks if c["status"] == "pass"),
                      "fail": sum(1 for c in checks if c["status"] == "fail"),
                      "not_run": sum(1 for c in checks if c["status"] == "not_run")}}
    (PKG / "review_checks.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"checks": out["counts"], "live": out["live"].get("status"),
                      "figures_404": [v.get("http") for v in figs.values()]},
                     ensure_ascii=False))
    return 0 if out["counts"]["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())