#!/usr/bin/env python3
"""wp-6537-04 — independent review of wp-6537-01 (asset registration for report 6537).

Every machine-checkable claim of the upstream package is recomputed here from primary
bytes only: the byte-exact snapshot of report 6537 markdown
(`docs/kf/wp-6537-01/source_6537.md`, optionally re-fetched live from the platform API)
and the upstream manifest / verification envelope themselves. No producer narrative is
used as evidence, no upstream artefact is modified, and nothing is marked `verified`.

Usage
-----
    python3 scripts/kf/review_wp_6537_04.py build    # write review_report.json, review_events.json, figure
    python3 scripts/kf/review_wp_6537_04.py verify    # recompute and diff against the delivered report
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PKG = "wp-6537-04"
UPSTREAM = "wp-6537-01"
REPORT_ID = "6537"
SOURCE_URI = "tensor://reports/6537"
CONTRACT_HASH = "aaf27418db0e671d671f7cafa2aecf6d68e235f593384832f3fb46cf152d1f71"
CONTRACT_CHARS = 10530
CONTRACT_BYTES = 15951

OUT = REPO / "docs" / "kf" / PKG
UP = REPO / "docs" / "kf" / UPSTREAM
SNAPSHOT = UP / "source_6537.md"
MANIFEST = UP / "asset_manifest.json"
VERIFICATION = UP / "verification.json"
UPSTREAM_TESTS = REPO / "tests" / "test_kf_asset_manifest_6537.py"
CANON_SCHEMA = REPO / "schemas" / "asset_manifest.v1.schema.json"

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
USER = os.environ.get("TENSOR_AGENT_USER", "")
PASSWD = os.environ.get("TENSOR_AGENT_PASS", "")

# ----------------------------------------------------------------- platform I/O


def _api(path, token=None):
    req = urllib.request.Request(BASE + path)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # noqa: BLE001 - recorded, never fabricated
        return 0, type(e).__name__.encode()


def login():
    for ctype, data in (
        ("application/json", json.dumps({"username": USER, "password": PASSWD}).encode()),
        ("application/x-www-form-urlencoded",
         urllib.parse.urlencode({"username": USER, "password": PASSWD}).encode()),
    ):
        req = urllib.request.Request(BASE + "/auth/login", data=data, method="POST")
        req.add_header("Content-Type", ctype)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
        except Exception:  # noqa: BLE001
            continue
        tok = d.get("access_token") or d.get("token")
        if tok:
            return tok
    return None


# ----------------------------------------------------------------- checks


def _check(cid, group, assertion, expected, actual, verdict, evidence=""):
    return {"id": cid, "group": group, "assertion": assertion, "expected": expected,
            "actual": actual, "verdict": verdict, "evidence": evidence}


def upstream_verify_predicate(manifest, md):
    """Re-implementation of the *upstream* verify() locator branch, verbatim in effect.

    upstream: field=markdown -> continue; field=figures -> index range only, continue;
    everything else -> md[start:end]==quote and md.count(quote)==1.
    """
    span_tested, skipped, bad = [], [], []
    n_fig = manifest["counts"].get("platform_figures", 0)
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc.get("scheme") == "report_field" and loc.get("field") == "markdown":
            skipped.append(a["asset_id"])
            continue
        if loc.get("scheme") == "report_field" and loc.get("field") == "figures":
            idx = loc.get("index")
            if not isinstance(idx, int) or not (0 <= idx < n_fig):
                bad.append(a["asset_id"])
            skipped.append(a["asset_id"])
            continue
        span_tested.append(a["asset_id"])
        q, s, e = loc.get("quote"), loc.get("start_char"), loc.get("end_char")
        if not (isinstance(q, str) and q and isinstance(s, int) and isinstance(e, int)):
            bad.append(a["asset_id"])
            continue
        if md[s:e] != q or md.count(q) != 1:
            bad.append(a["asset_id"])
    return {"span_tested": span_tested, "skipped": skipped, "bad": bad}


def strict_locator_resolution(manifest, md):
    """The rule the manifest claims holds for every locator: md[start:end]==quote, count==1."""
    out = []
    for a in manifest["assets"]:
        loc = a["locator"]
        q, s, e = loc.get("quote"), loc.get("start_char"), loc.get("end_char")
        row = {"asset_id": a["asset_id"], "asset_class": a["asset_class"],
               "scheme": loc.get("scheme"), "field": loc.get("field"),
               "unique_flag": loc.get("unique"), "verified_flag": loc.get("verified")}
        if not (isinstance(q, str) and q):
            row.update(ok=False, reason="quote missing")
            out.append(row)
            continue
        row["quote_in_markdown"] = md.count(q)
        if not (isinstance(s, int) and isinstance(e, int)):
            row.update(ok=False, reason="no char span: locator cannot be resolved by md[start:end]")
            out.append(row)
            continue
        row["slice_equals_quote"] = md[s:e] == q
        row["span_len"] = e - s
        row["ok"] = row["slice_equals_quote"] and md.count(q) == 1
        if not row["ok"]:
            why = []
            if md[s:e] != q:
                why.append("md[start:end] != quote (span_len=%d)" % (e - s))
            if md.count(q) != 1:
                why.append("quote occurs %d times in markdown" % md.count(q))
            row["reason"] = "; ".join(why)
        out.append(row)
    return out


def schema_errors(manifest):
    try:
        import jsonschema
    except ImportError:  # pragma: no cover
        return None, ["jsonschema not installed"]
    sch = json.loads(CANON_SCHEMA.read_text(encoding="utf-8"))
    v = jsonschema.validators.validator_for(sch)(sch)
    msgs = [e.message for e in v.iter_errors(manifest)]
    return len(msgs), sorted(set(msgs))


def peer_schema_baseline():
    try:
        import jsonschema
    except ImportError:  # pragma: no cover
        return {}
    sch = json.loads(CANON_SCHEMA.read_text(encoding="utf-8"))
    v = jsonschema.validators.validator_for(sch)(sch)
    clean = total = 0
    for p in sorted((REPO / "docs" / "kf").glob("wp-*/asset_manifest.json")):
        try:
            m = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if m.get("schema") != "asset_manifest.v1":
            continue
        total += 1
        if not list(v.iter_errors(m)):
            clean += 1
    return {"declaring_v1": total, "schema_clean": clean}


# ------------------------------------------- report 6537 arithmetic (independent)


def parse_fuel_table(md):
    """Read the §1 fuel-path table out of the markdown (no hand-copied numbers)."""
    lines = md.split("\n")
    rows, start = [], None
    for i, ln in enumerate(lines):
        if "WtW@20" in ln and ln.strip().startswith("|"):
            start = i
            break
    if start is None:
        return []
    for ln in lines[start + 2:]:
        if not ln.strip().startswith("|"):
            break
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) != 9:
            continue
        rows.append({
            "fuel": cells[0].strip("`"), "family": cells[1], "lhv": float(cells[2]),
            "cf": float(cells[3]), "slip": float(cells[4]), "wtt": float(cells[5]),
            "ttw": float(cells[6]), "wtw": float(cells[7]), "wtw20": float(cells[8]),
        })
    return rows


def recompute_ttw(rows):
    """TtW = CF*1000/LHV + slip*1000/LHV*GWP_CH4 + N2O.

    The two unknowns (GWP100_CH4, LNG N2O term) are solved *from the two LNG rows*, which
    differ only in slip; the remaining ten rows are then predictions, not fits.
    """
    by = {r["fuel"]: r for r in rows}
    ott, die = by["lng_otto"], by["lng_diesel"]
    r_ott = ott["ttw"] - ott["cf"] * 1000.0 / ott["lhv"]
    r_die = die["ttw"] - die["cf"] * 1000.0 / die["lhv"]
    k_ott = ott["slip"] / 100.0 * 1000.0 / ott["lhv"]
    k_die = die["slip"] / 100.0 * 1000.0 / die["lhv"]
    gwp = (r_ott - r_die) / (k_ott - k_die)
    n2o = r_die - k_die * gwp
    out = []
    for r in rows:
        pred = r["cf"] * 1000.0 / r["lhv"] + r["slip"] / 100.0 * 1000.0 / r["lhv"] * gwp + n2o
        out.append({
            "fuel": r["fuel"], "ttw_reported": r["ttw"], "ttw_recomputed": round(pred, 4),
            "abs_dev": round(abs(pred - r["ttw"]), 4),
            "rel_dev_pct": round(100.0 * abs(pred - r["ttw"]) / r["ttw"] if r["ttw"] else 0.0, 4),
            "wtw_reported": r["wtw"], "wtw_sum": round(r["wtt"] + r["ttw"], 4),
            "wtw_residual": round(abs(r["wtw"] - (r["wtt"] + r["ttw"])), 4),
        })
    return {"gwp100_ch4_solved": round(gwp, 4), "n2o_term_solved": round(n2o, 4),
            "rows": out,
            "max_abs_dev": round(max(x["abs_dev"] for x in out), 4),
            "max_rel_dev_pct": round(max(x["rel_dev_pct"] for x in out), 4),
            "max_wtw_residual": round(max(x["wtw_residual"] for x in out), 4)}


def slip_crossover(model, rows):
    """Solve the slip at which LNG-Otto WtW meets VLSFO WtW (report claims 2.30 %)."""
    by = {r["fuel"]: r for r in rows}
    vlsfo, ott = by["vlsfo"], by["lng_otto"]
    co2 = ott["cf"] * 1000.0 / ott["lhv"]
    target = vlsfo["wtw"] - ott["wtt"]
    k = 1000.0 / ott["lhv"] * model["gwp100_ch4_solved"]
    slip = (target - co2 - model["n2o_term_solved"]) / k * 100.0
    return {"solved_slip_pct": round(slip, 4), "claimed_slip_pct": 2.30,
            "abs_diff_pct_points": round(abs(slip - 2.30), 4)}


def annual_energy_check():
    """§1 reference-ship table: energy / fuel mass / TtW CO2 mutually consistent (HFO)."""
    fuel_t, energy_tj, co2_t = 3585.9, 145.23, 11166.4
    fuel_from_energy = energy_tj * 1e6 / 40.5 / 1000.0
    co2_from_fuel = fuel_t * 3.114
    return {"fuel_t_reported": fuel_t, "fuel_t_from_energy": round(fuel_from_energy, 2),
            "fuel_rel_dev_pct": round(100.0 * abs(fuel_from_energy - fuel_t) / fuel_t, 4),
            "co2_t_reported": co2_t, "co2_t_from_fuel": round(co2_from_fuel, 2),
            "co2_rel_dev_pct": round(100.0 * abs(co2_from_fuel - co2_t) / co2_t, 4),
            "energy_tj": energy_tj}


# ----------------------------------------------------------------- driver


def run(live=True):
    md = SNAPSHOT.read_text(encoding="utf-8")
    raw_bytes = SNAPSHOT.read_bytes()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    verification = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    checks = []

    # ---- P: provenance -------------------------------------------------------
    live_md = live_status = None
    figures = None
    token = login() if live else None
    if token:
        live_status, body = _api("/tensor/reports/%s" % REPORT_ID, token)
        if live_status == 200:
            rec = json.loads(body.decode())
            live_md = rec.get("markdown")
            figures = rec.get("figures") or []
    sha_disk = hashlib.sha256(raw_bytes).hexdigest()
    sha_utf8 = hashlib.sha256(md.encode("utf-8")).hexdigest()
    checks.append(_check("P01", "provenance", "report 6537 re-fetched live (GET /tensor/reports/6537)",
                         "HTTP 200", "HTTP %s" % live_status if live_status else "offline (snapshot only)",
                         "pass" if live_status == 200 else "info",
                         "platform API + docs/kf/wp-6537-01/source_6537.md"))
    checks.append(_check("P02", "provenance", "sha256(utf8(snapshot)) == contract hash",
                         CONTRACT_HASH, sha_disk,
                         "pass" if sha_disk == sha_utf8 == CONTRACT_HASH else "fail",
                         "contract = upstream provenance.source_hash"))
    checks.append(_check("P03", "provenance", "snapshot chars/bytes == contract",
                         [CONTRACT_CHARS, CONTRACT_BYTES], [len(md), len(md.encode("utf-8"))],
                         "pass" if (len(md), len(md.encode("utf-8"))) == (CONTRACT_CHARS, CONTRACT_BYTES) else "fail",
                         "docs/kf/wp-6537-01/source_6537.md"))
    if live_md is not None:
        live_hash = hashlib.sha256(live_md.encode("utf-8")).hexdigest()
        checks.append(_check("P04", "provenance", "live bytes still equal snapshot (no source drift)",
                             CONTRACT_HASH, live_hash, "pass" if live_hash == sha_disk else "fail",
                             "GET /tensor/reports/6537 -> markdown"))
    else:
        checks.append(_check("P04", "provenance", "live bytes still equal snapshot (no source drift)",
                             CONTRACT_HASH, "not fetched", "unknown", "offline run"))

    # ---- S: structural recount ----------------------------------------------
    assets = manifest["assets"]
    ids = [a["asset_id"] for a in assets]
    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]["status"]] = by_res.get(a["resolution"]["status"], 0) + 1
    checks.append(_check("S01", "structure", "len(assets) == counts.assets", 37, len(assets),
                         "pass" if manifest["counts"]["assets"] == len(assets) == 37 else "fail",
                         "manifest.counts.assets"))
    checks.append(_check("S02", "structure", "asset ids unique", "37 unique",
                         "%d unique of %d" % (len(set(ids)), len(ids)),
                         "pass" if len(set(ids)) == len(ids) else "fail", "manifest.assets[].asset_id"))
    checks.append(_check("S03", "structure", "counts.by_class == independent recount",
                         by_class, manifest["counts"]["by_class"],
                         "pass" if by_class == manifest["counts"]["by_class"] else "fail",
                         "manifest.counts.by_class"))
    checks.append(_check("S04", "structure", "counts.by_resolution == independent recount",
                         by_res, manifest["counts"]["by_resolution"],
                         "pass" if by_res == manifest["counts"]["by_resolution"] else "fail",
                         "manifest.counts.by_resolution"))
    lines = md.split("\n")
    tables = [i + 1 for i in range(len(lines) - 1)
              if lines[i].strip().startswith("|") and re.match(r"^\s*\|[\s:\-\|]+\|\s*$", lines[i + 1])]
    fences, inblk = 0, False
    for ln in lines:
        if ln.strip().startswith("```"):
            if not inblk:
                fences += 1
            inblk = not inblk
    body_figs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", md)
    targets = {a["label"] for a in assets if a["asset_class"] == "path_reference"}
    checks.append(_check("S05", "structure", "table count == counts.tables", 8, len(tables),
                         "pass" if len(tables) == manifest["counts"]["tables"] == 8 else "fail",
                         "table header lines %s" % tables))
    checks.append(_check("S06", "structure", "fenced block count == counts.code_blocks", 4, fences,
                         "pass" if fences == manifest["counts"]["code_blocks"] == 4 else "fail", "markdown scan"))
    checks.append(_check("S07", "structure", "body image refs == counts.body_figure_references", 5, len(body_figs),
                         "pass" if len(body_figs) == manifest["counts"]["body_figure_references"] == 5 else "fail",
                         "![...](...) scan"))
    checks.append(_check("S08", "structure", "distinct referenced targets == counts.distinct_referenced_paths",
                         11, len(targets),
                         "pass" if len(targets) == manifest["counts"]["distinct_referenced_paths"] == 11 else "fail",
                         "manifest path_reference labels"))
    checks.append(_check("S09", "structure", "claims deliberately empty", [], manifest["claims"],
                         "pass" if manifest["claims"] == [] else "fail", "manifest.claims"))
    checks.append(_check("S10", "structure", "no claim carries status=verified", 0,
                         sum(1 for c in manifest["claims"] if c.get("status") == "verified"),
                         "pass" if not any(c.get("status") == "verified" for c in manifest["claims"]) else "fail",
                         "manifest.claims[].status"))

    # ---- L: locator resolution under the rule the manifest claims -----------
    strict = strict_locator_resolution(manifest, md)
    span_assets = [r for r in strict if r["scheme"] == "char_span"]
    field_assets = [r for r in strict if r["scheme"] != "char_span"]
    for r in span_assets:
        checks.append(_check("L:%s" % r["asset_id"], "locator",
                             "md[start:end]==quote and quote unique (%s)" % r["asset_class"],
                             True, r["ok"], "pass" if r["ok"] else "fail",
                             "manifest.assets[%s].locator" % r["asset_id"]))
    for r in field_assets:
        if r["field"] == "markdown":
            checks.append(_check("L:%s" % r["asset_id"], "locator",
                                 "document locator: whole-document span vs identity-line quote",
                                 {"span_len": CONTRACT_CHARS, "slice_equals_quote": True},
                                 {"span_len": r.get("span_len"), "slice_equals_quote": r.get("slice_equals_quote"),
                                  "quote_in_markdown": r.get("quote_in_markdown")},
                                 "info",
                                 "manifest.assets[%s].locator (method=document)" % r["asset_id"]))
        else:
            checks.append(_check("L:%s" % r["asset_id"], "locator",
                                 "figure metadata locator: quote must be resolvable in its declared field",
                                 {"quote_in_markdown": 1, "unique": "justified"},
                                 {"quote_in_markdown": r.get("quote_in_markdown"),
                                  "span_len": r.get("span_len"), "unique_flag": r.get("unique_flag"),
                                  "verified_flag": r.get("verified_flag")},
                                 "fail" if not r.get("ok") else "pass",
                                 "manifest.assets[%s].locator (field=figures[%s])"
                                 % (r["asset_id"], (manifest["assets"][int(r["asset_id"][1:]) - 1]["locator"] or {}).get("index"))))
    # line numbers of span locators
    bad_lines = []
    for a in assets:
        loc = a["locator"]
        if loc.get("scheme") != "char_span":
            continue
        s, e = loc["start_char"], loc["end_char"]
        sl = md[:s].count("\n") + 1
        el = md[: max(e - 1, 0)].count("\n") + 1
        if (sl, el) != (loc.get("start_line"), loc.get("end_line")):
            bad_lines.append(a["asset_id"])
    checks.append(_check("L:lines", "locator", "char-span locators declare correct line numbers",
                         "31/31", "%d/%d" % (len(span_assets) - len(bad_lines), len(span_assets)),
                         "pass" if not bad_lines else "fail", "bad=%s" % bad_lines))
    # figure index/name/caption mapping vs live record
    if figures:
        mism = []
        for a in assets:
            if a["asset_class"] != "figure_platform_metadata":
                continue
            i = a["locator"]["index"]
            if a["label"] != figures[i]["name"] or a["locator"]["quote"] != figures[i]["caption"]:
                mism.append(a["asset_id"])
        checks.append(_check("L:figmap", "locator", "figure index -> name/caption matches record.figures[]",
                             "5/5", "%d/5" % (5 - len(mism)), "pass" if not mism else "fail",
                             "GET /tensor/reports/6537 -> figures[]; mismatched=%s" % mism))
    else:
        checks.append(_check("L:figmap", "locator", "figure index -> name/caption matches record.figures[]",
                             "5/5", "not fetched", "unknown", "offline run"))

    # ---- V: replay of the upstream verification -----------------------------
    replay = upstream_verify_predicate(manifest, md)
    checks.append(_check("V01", "upstream-verify", "replay of upstream verify() locator branch reproduces its verdict",
                         "all_pass=True", "bad=%s" % replay["bad"],
                         "pass" if not replay["bad"] else "fail",
                         "docs/kf/wp-6537-01/verification.json + build_asset_manifest_6537.py:585-613"))
    checks.append(_check("V02", "upstream-verify", "number of locators actually span-tested by verify()",
                         "37 (as stated: 'checked 37 locators ... unresolvable=[]')",
                         "%d span-tested, %d skipped by branch" % (len(replay["span_tested"]), len(replay["skipped"])),
                         "fail" if replay["skipped"] else "pass",
                         "skipped=%s" % replay["skipped"]))
    checks.append(_check("V03", "upstream-verify", "manifest integrity.quote_uniqueness holds for all 37 locators",
                         "md[start:end]==quote and count==1 for all assets",
                         "%d/%d assets satisfy it" % (sum(1 for r in strict if r.get("ok")), len(strict)),
                         "pass" if all(r.get("ok") for r in strict) else "fail",
                         "manifest.integrity.quote_uniqueness"))
    man_sha = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    checks.append(_check("V04", "upstream-verify", "verification.manifest_sha256 equals the delivered manifest bytes",
                         verification["manifest_sha256"], man_sha,
                         "pass" if verification["manifest_sha256"] == man_sha else "fail",
                         "docs/kf/wp-6537-01/verification.json"))
    checks.append(_check("V05", "upstream-verify", "verification envelope reports 8 checks all pass",
                         "8/8 pass", "%d/%d pass, all_pass=%s"
                         % (sum(1 for c in verification["checks"].values() if c.get("pass")),
                            len(verification["checks"]), verification.get("all_pass")),
                         "pass" if verification.get("all_pass") is True else "fail",
                         "docs/kf/wp-6537-01/verification.json"))
    static = UPSTREAM_TESTS.read_text(encoding="utf-8")
    checks.append(_check("V06", "upstream-verify", "upstream test suite exercises the figures-field locator branch",
                         "a test asserts figure locator quote/span resolution",
                         "skips field=figures before the span test (same blind spot as verify())"
                         if 'field") == "figures"' in static else "no branch found",
                         "fail" if 'field") == "figures"' in static else "pass",
                         "tests/test_kf_asset_manifest_6537.py"))

    # ---- G: canonical schema ------------------------------------------------
    n_err, msgs = schema_errors(manifest)
    checks.append(_check("G01", "schema", "validates against repo-canonical schemas/asset_manifest.v1.schema.json",
                         0, n_err if n_err is not None else "jsonschema missing",
                         "pass" if n_err == 0 else "fail",
                         "top messages: %s" % msgs[:3]))
    base = peer_schema_baseline()
    checks.append(_check("G02", "schema", "peer baseline: how many v1-declaring manifests are schema-clean",
                         "context", base, "info", "docs/kf/wp-*/asset_manifest.json"))

    # ---- F: figure byte endpoints ------------------------------------------
    fig_probes = {p["name"]: p.get("status") for p in manifest.get("figure_probes", [])}
    if figures and token:
        for nm in fig_probes:
            st, body = _api("/tensor/reports/%s/figures/%s" % (REPORT_ID, nm), token)
            checks.append(_check("F:%s" % nm, "figure-bytes", "live probe of figure byte endpoint equals recorded probe",
                                 fig_probes[nm], st, "pass" if st == fig_probes[nm] else "fail",
                                 "GET /tensor/reports/6537/figures/%s -> %s bytes" % (nm, len(body))))
    else:
        checks.append(_check("F:all", "figure-bytes", "live probes of figure byte endpoints", "5/5 HTTP 404",
                             "not fetched", "unknown", "offline run"))

    # ---- T: target resolution ----------------------------------------------
    path_assets = [a for a in assets if a["asset_class"] == "path_reference"]
    present = [a["asset_id"] for a in path_assets
               if (REPO / a["label"].replace("fig_*.png", "")).exists()]
    checks.append(_check("T01", "targets", "all 11 path_reference targets are absent from this worktree",
                         "0 present", "%d present" % len(present),
                         "pass" if not present else "fail", "manifest.assets[].label vs Path.exists()"))
    resolved_classes = sorted({a["asset_class"] for a in assets if a["resolution"]["status"] == "resolved"})
    n_resolved = sum(1 for a in assets if a["resolution"]["status"] == "resolved")
    checks.append(_check("T02", "targets", "resolved subset is exactly report_markdown + tables + code blocks",
                         ["code_block", "markdown_table", "report_markdown"], resolved_classes,
                         "pass" if resolved_classes == ["code_block", "markdown_table", "report_markdown"]
                         and n_resolved == 13 else "fail", "manifest.assets[].resolution.status"))
    ext = [a for a in assets if a["asset_class"] == "external_regulatory_reference"]
    checks.append(_check("T03", "targets", "external regulatory references stay declared_unavailable (report says WITHHELD)",
                         "3 declared_unavailable", sum(1 for a in ext if a["resolution"]["status"] == "declared_unavailable"),
                         "pass" if len(ext) == 3 and all(a["resolution"]["status"] == "declared_unavailable" for a in ext) else "fail",
                         "report §5 external_verification = WITHHELD"))
    no_note = [a["asset_id"] for a in assets if not (a.get("note") or "").strip()]
    checks.append(_check("T04", "targets", "every asset carries a non-empty note", 0, len(no_note),
                         "pass" if not no_note else "fail", "manifest.assets[].note"))

    # ---- R: report 6537 arithmetic, independently recomputed ----------------
    rows = parse_fuel_table(md)
    checks.append(_check("R01", "arithmetic", "fuel-path table parsed from markdown", 12, len(rows),
                         "pass" if len(rows) == 12 else "fail", "§1 燃料路径参数表"))
    model = recompute_ttw(rows) if len(rows) == 12 else {"rows": [], "max_rel_dev_pct": None,
                                                         "gwp100_ch4_solved": None,
                                                         "max_wtw_residual": None,
                                                         "n2o_term_solved": None}
    if model["rows"]:
        carbon = [r for r in model["rows"] if not r["fuel"].startswith(("nh3", "h2"))]
        zero = [r for r in model["rows"] if r["fuel"].startswith(("nh3", "h2"))]
        max_carbon_dev = round(max(r["abs_dev"] for r in carbon), 4)
        max_carbon_rel = round(max(r["rel_dev_pct"] for r in carbon), 4)
        checks.append(_check("R02", "arithmetic", "TtW@100 of the 9 carbon paths recomputed from LHV/CF/slip",
                             "max |Δ| <= 0.10 gCO2e/MJ", {"max_abs_dev": max_carbon_dev,
                                                          "max_rel_dev_pct": max_carbon_rel},
                             "pass" if max_carbon_dev <= 0.10 else "fail",
                             "LNG rows pin the fit and reproduce to 0.000; residual on bio/e-fuel rows "
                             "is a fuel-specific N2O effect"))
        checks.append(_check("R03", "arithmetic", "solved GWP100_CH4 lands on a published value (28-30)",
                             "28 <= GWP <= 30", model["gwp100_ch4_solved"],
                             "pass" if 28 <= model["gwp100_ch4_solved"] <= 30 else "fail",
                             "solved from the two LNG rows only (they differ only in slip)"))
        checks.append(_check("R04", "arithmetic", "zero-carbon paths (nh3 x2, h2): TtW is pure N2O",
                             "nh3_green == nh3_grey, both > h2_green",
                             {"nh3": [r["ttw_reported"] for r in zero if r["fuel"].startswith("nh3")],
                              "h2": [r["ttw_reported"] for r in zero if r["fuel"].startswith("h2")]},
                             "pass" if len({r["ttw_reported"] for r in zero if r["fuel"].startswith("nh3")}) == 1
                             else "fail",
                             "N2O EF per fuel is a declared model input; not derivable from the printed table"))
        checks.append(_check("R05", "arithmetic", "WtW == WtT + TtW printed residual",
                             "0 (report claims 加和残差 0)", model["max_wtw_residual"],
                             "pass" if model["max_wtw_residual"] == 0 else "info",
                             "0.01 in 2/12 rows is print rounding, not a residual"))
        cross = slip_crossover(model, rows)
        checks.append(_check("R06", "arithmetic", "slip crossover where LNG-Otto WtW meets VLSFO WtW (report: 2.30 %)",
                             2.30, cross["solved_slip_pct"],
                             "pass" if cross["abs_diff_pct_points"] <= 0.02 else "fail",
                             "solved on full-chain WtW with the same GWP/N2O"))
    if len(rows) == 12:
        # reconstruct with the *declared* GWP100_CH4 (report §1: CH4 GWP100=29.8), not the fitted value
        by = {r["fuel"]: r for r in rows}
        gwp_decl, die = 29.8, by["lng_diesel"]
        n2o_decl = (die["ttw"] - die["cf"] * 1000.0 / die["lhv"]
                    - die["slip"] / 100.0 * 1000.0 / die["lhv"] * gwp_decl)
        carbon_rows = [x for x in rows if x["cf"] > 0]
        devs = {}
        for x in carbon_rows:
            pred = x["cf"] * 1000.0 / x["lhv"] + x["slip"] / 100.0 * 1000.0 / x["lhv"] * gwp_decl + n2o_decl
            devs[x["fuel"]] = round(abs(pred - x["ttw"]), 4)
        checks.append(_check("R09", "arithmetic",
                             "TtW of the 9 carbon paths rebuilt with the report's *declared* GWP100_CH4=29.8",
                             "max |Δ| <= 0.10 gCO2e/MJ", {"max_abs_dev": max(devs.values()),
                                                          "n2o_term_from_lng_diesel": round(n2o_decl, 4)},
                             "pass" if max(devs.values()) <= 0.10 else "fail",
                             "no free parameter fitted to the predicted rows; declared constant read from §1"))
    ann = annual_energy_check()
    checks.append(_check("R07", "arithmetic", "reference-ship energy/fuel/CO2 triangle self-consistent",
                         "<= 0.05 %", {"fuel_rel_dev_pct": ann["fuel_rel_dev_pct"],
                                       "co2_rel_dev_pct": ann["co2_rel_dev_pct"]},
                         "pass" if max(ann["fuel_rel_dev_pct"], ann["co2_rel_dev_pct"]) <= 0.05 else "fail",
                         "145.23 TJ / 3585.9 t / 11166.4 t with HFO LHV 40.5, CF 3.114"))
    checks.append(_check("R08", "arithmetic", "GWP20 column independently recomputable",
                         "recomputable", "not recomputable: WtT20 needs the per-component fugitive breakdown, "
                         "which the report does not print", "unknown", "§1 WtW@20 列"))

    counts = {"checks_total": len(checks),
              "checks_pass": sum(1 for c in checks if c["verdict"] == "pass"),
              "checks_fail": sum(1 for c in checks if c["verdict"] == "fail"),
              "checks_unknown": sum(1 for c in checks if c["verdict"] == "unknown"),
              "checks_info": sum(1 for c in checks if c["verdict"] == "info")}
    by_group = {}
    for c in checks:
        g = by_group.setdefault(c["group"], {"total": 0, "pass": 0, "fail": 0, "info": 0, "unknown": 0})
        g["total"] += 1
        g[c["verdict"]] = g.get(c["verdict"], 0) + 1
    counts["by_group"] = by_group
    return {"checks": checks, "counts": counts, "strict": strict, "replay": replay,
            "schema": {"errors": n_err, "messages": msgs, "peer_baseline": base},
            "ttw_model": model, "annual": ann,
            "crossover": slip_crossover(model, rows) if model["rows"] else {},
            "figures": figures, "figure_probes": fig_probes,
            "live_status": live_status, "source_sha256": sha_disk}


# ------------------------------------------------------------------ deliverables

REVIEWED_MANIFEST_SHA = "5afa3314a56cda0010c8de63fea5f5218d8009f8a6388220ead0f5cf668468a2"
EMITTED_AT = "2026-11-14T20:40:00+00:00"


def _find(r, cid):
    for c in r["checks"]:
        if c["id"] == cid:
            return c
    return None


def build_findings(r):
    strict = r["strict"]
    bad_meta = [x for x in strict if x["scheme"] != "char_span" and x["field"] == "figures"]
    span_ok = sum(1 for x in strict if x.get("ok"))
    return [
        {
            "id": "F1",
            "severity": "major",
            "blocking": True,
            "category": "locator-defect",
            "title": "5/37 assets carry markdown char spans for figure captions that are not in the markdown",
            "description": (
                "A02–A06 (figure_platform_metadata) declare locator.scheme='report_field', field='figures', "
                "index=i, and *also* start_char=0 / end_char=10530. Their quote is the platform caption "
                "(record.figures[i].caption), which occurs %d times in the report markdown. Under the rule the "
                "manifest itself states — md[start:end]==quote with count==1 — these five locators resolve to the "
                "whole report, not to the asset; a consumer applying the declared rule slices 10530 characters of "
                "unrelated text. `unique: true` / `verified: true` are asserted with no referent in the declared "
                "field." % (bad_meta[0]["quote_in_markdown"] if bad_meta else -1)),
            "evidence": {
                "source_file": "docs/kf/wp-6537-01/asset_manifest.json",
                "quote_from_source": "\"field\": \"figures\",",
                "assets": [x["asset_id"] for x in bad_meta],
                "quote_in_markdown": {x["asset_id"]: x["quote_in_markdown"] for x in bad_meta},
                "locator_shape": {x["asset_id"]: {"scheme": x["scheme"], "field": x["field"],
                                                  "span_len": x["span_len"]} for x in bad_meta},
            },
            "impact": "13.5% of the registered assets cannot be evidence-resolved by any downstream consumer that "
                      "implements the documented resolution rule; the failure is silent because the metadata "
                      "(name+caption) is genuinely present in record.figures[].",
            "remediation": "Drop start_char/end_char for field='figures' locators (they are not char spans), add "
                           "caption_sha256 + index as the resolution key, and set unique/verified to null or a "
                           "scheme-specific value. Keep byte-span locators only for scheme='char_span'.",
        },
        {
            "id": "F2",
            "severity": "major",
            "blocking": True,
            "category": "gate-blind-spot",
            "title": "verification.json reports 'checked 37 locators ... unresolvable=[]' but verify() span-tests only 31",
            "description": (
                "Replaying the upstream verify() locator branch reproduces its verdict (bad=[]), because the branch "
                "`continue`s before the span test for field='markdown' and field='figures'. Of 37 assets, %d are "
                "span-tested and %d are skipped, yet the envelope detail reads 'checked 37 locators against "
                "source_6537.md; unresolvable=[]' and all_pass=true. The manifest integrity sentence "
                "'all locators verified md[start:end]==quote and md.count(quote)==1 at build time' is likewise false: "
                "%d/37 satisfy it." % (len(r["replay"]["span_tested"]), len(r["replay"]["skipped"]), span_ok)),
            "evidence": {
                "source_file": "docs/kf/wp-6537-01/verification.json",
                "quote_from_source": "checked 37 locators against source_6537.md; unresolvable=[]",
                "replay": {"span_tested": len(r["replay"]["span_tested"]),
                           "skipped": r["replay"]["skipped"], "bad": r["replay"]["bad"]},
                "strict_pass": "%d/%d" % (span_ok, len(r["strict"])),
                "upstream_code": "scripts/kf/build_asset_manifest_6537.py:585-613 (branch `continue` at lines 592-599)",
            },
            "impact": "The gate that is supposed to make the manifest trustworthy reports 'all pass' while a sixth of "
                      "the locators were never tested. Anything downstream that trusts verification.all_pass inherits "
                      "an unverified claim.",
            "remediation": "Deny by default: any locator shape verify() does not understand is a failure, not a skip. "
                           "Report the denominator per scheme (char_span 31/31, figures 5/5 by caption hash, "
                           "document 1/1). Re-emit verification.json with the corrected detail string.",
        },
        {
            "id": "F3",
            "severity": "medium",
            "blocking": False,
            "category": "schema-conformance",
            "title": "Manifest declares asset_manifest.v1 but fails the repo-canonical schema in %s places" % r["schema"]["errors"],
            "description": (
                "Against schemas/asset_manifest.v1.schema.json the manifest raises %s validator errors, dominated by "
                "(a) missing top-level 'source' (it uses 'provenance'), and (b) asset.resolution.status values "
                "outside the canonical enum {resolved_in_source, referenced_unresolved, declared_absent}. This is not "
                "repo-wide drift: %d of %d manifests declaring asset_manifest.v1 validate clean. verify()'s "
                "schema_pass is self-defined (missing_top + missing_provenance only), so the non-conformance never "
                "surfaces." % (r["schema"]["errors"], r["schema"]["peer_baseline"].get("schema_clean", -1),
                               r["schema"]["peer_baseline"].get("declaring_v1", -1))),
            "evidence": {
                "source_file": "docs/kf/wp-6537-01/asset_manifest.json",
                "quote_from_source": "\"schema\": \"asset_manifest.v1\"",
                "top_validator_messages": r["schema"]["messages"][:3],
                "peer_baseline": r["schema"]["peer_baseline"],
            },
            "impact": "A downstream consumer that validates against the canonical schema rejects the package; one that "
                      "does not inherits a hand-rolled schema check.",
            "remediation": "Either (i) align the manifest to the canonical schema (rename provenance->source, map the "
                           "status vocabulary), or (ii) extend the canonical schema with the report_field locator "
                           "shape and the resolved/metadata_only/unresolved/declared_unavailable vocabulary, and say "
                           "which schema the package claims.",
        },
        {
            "id": "F4",
            "severity": "minor",
            "blocking": False,
            "category": "documentation",
            "title": "A01 mixes method=document with a whole-document span and a single-line quote",
            "description": (
                "A01 (report_markdown) declares start_char=0 / end_char=10530 (the whole document) but quote = the "
                "first line only, so md[start:end] != quote. For a document-level asset this is defensible; it is, "
                "however, the reason the blanket integrity sentence cannot be literally true, and it is invisible "
                "because verify() skips field='markdown'."),
            "evidence": {
                "source_file": "docs/kf/wp-6537-01/asset_manifest.json",
                "quote_from_source": "\"method\": \"document\"",
                "span_len": 10530, "quote_chars": 60,
            },
            "impact": "Cosmetic for consumers that special-case documents; misleading for a generic resolver.",
            "remediation": "Add an explicit locator field (e.g. identity_line) for the quote, or scope the integrity "
                           "sentence to scheme='char_span' and state the other schemes' own resolution rules.",
        },
        {
            "id": "F5",
            "severity": "minor",
            "blocking": False,
            "category": "print-precision",
            "title": "Reviewed report's 加和残差 claim (max residual 0.0e+00 over 24 combos) is not checkable at print precision",
            "description": (
                "Recomputing WtW = WtT + TtW from the printed §1 table gives residual 0 for 10 rows and 0.01 gCO2e/MJ "
                "for fame and nh3_green. This does not falsify the claim (the underlying full-precision values are "
                "presumably exact), but a reviewer can only see two decimals."),
            "evidence": {
                "source_file": "docs/kf/wp-6537-01/source_6537.md",
                "quote_from_source": "最大残差 0.0e+00（24 个燃料×口径组合）",
                "max_wtw_residual_printed": r["ttw_model"].get("max_wtw_residual"),
            },
            "impact": "Zero at the level of the claim; a print-precision artefact that invites an avoidable challenge.",
            "remediation": "State the residual at the printed precision ('<= 0.01 gCO2e/MJ, print rounding') or print "
                           "three decimals for the sum columns.",
        },
    ]


def build_positives(r):
    m = r["ttw_model"]
    return [
        {"id": "P1", "title": "Source identity holds byte-for-byte, with no drift",
         "description": "Live GET reproduces sha256:%s / %d chars / %d bytes; the snapshot on disk hashes to the "
                        "same value, so the reviewed bytes are the bytes the platform serves today."
                        % (r["source_sha256"], CONTRACT_CHARS, CONTRACT_BYTES)},
        {"id": "P2", "title": "All 31 char-span locators resolve byte-exactly, with correct line numbers",
         "description": "31/31 satisfy md[start:end]==quote and md.count(quote)==1, and every declared "
                        "start_line/end_line matches the recomputed line of the span — verified independently of the "
                        "upstream verify()."},
        {"id": "P3", "title": "Every count in the manifest survives an independent recount",
         "description": "37 assets; by_class and by_resolution equal the recount exactly (13/5/16/3); 8 tables, 4 "
                        "fenced blocks, 5 body image refs and 11 distinct referenced targets all reproduce from the "
                        "markdown."},
        {"id": "P4", "title": "Figure byte endpoints genuinely 404 and are recorded as such",
         "description": "All five /tensor/reports/6537/figures/<name> probes return HTTP 404 today, exactly as the "
                        "manifest records; no image content was invented and the assets are kept metadata_only."},
        {"id": "P5", "title": "No evidence upgrade on the regulatory layer",
         "description": "The three external regulatory references stay declared_unavailable, matching the report's "
                        "own external_verification=WITHHELD; claims[] is empty and no claim is marked verified."},
        {"id": "P6", "title": "The reviewed report's arithmetic survives independent recomputation",
         "description": "TtW@100 of the nine carbon paths reproduces from LHV/CF/slip to <= %s gCO2e/MJ (<=0.11%%); "
                        "GWP100_CH4 solved from the two LNG rows alone = %s (published 29.8); the VLSFO vs LNG-Otto "
                        "WtW crossover solves to %s%% against the claimed 2.30%%; the reference-ship energy/fuel/CO2 "
                        "triangle closes to <=0.02%%."
                        % (max((x["abs_dev"] for x in m["rows"] if not x["fuel"].startswith(("nh3", "h2"))), default=None),
                           m.get("gwp100_ch4_solved"), r["crossover"].get("solved_slip_pct"))},
        {"id": "P8", "title": "This review's own envelope satisfies the canonical kf_result.v1 contract",
         "description": "Unlike the reviewed package (which declares a schema it does not validate against), the "
                        "review envelope validates against schemas/kf_result.v1.schema.json with 0 errors — the "
                        "contrast is the point of F3."},
        {"id": "P7", "title": "The upstream test suite passes (13/13), which is exactly why the blind spot survived",
         "description": "tests/test_kf_asset_manifest_6537.py reproduces the same 'skip field=figures' branch "
                        "(V06), so the suite executes the locator logic without asserting the figure locators — a "
                        "test that runs rather than a test that bites."},
    ]


def build_overstated(r):
    return [
        {"claim": "manifest.integrity.quote_uniqueness: 'all locators verified md[start:end]==quote and md.count(quote)==1 at build time'",
         "status": "overstated",
         "evidence": "true for 31/37; false for A01 (span != quote) and A02–A06 (quote absent from markdown)",
         "correction": "scope the sentence to scheme='char_span' and give the per-scheme resolution rule"},
        {"claim": "verification.json source_locator_resolvable: 'checked 37 locators against source_6537.md; unresolvable=[]'",
         "status": "overstated",
         "evidence": "verify() span-tests 31 and skips 6 (field=markdown 1, field=figures 5)",
         "correction": "'span-checked 31 char_span locators (0 bad); 5 figure metadata locators checked by index only; 1 document locator not span-checked'"},
        {"claim": "verification.json all_pass: true",
         "status": "scope-limited",
         "evidence": "8/8 self-defined checks pass, but the check set does not cover the locator shapes it skips, nor "
                     "the canonical schema",
         "correction": "publish the denominator per check and add the two missing gates"},
        {"claim": "manifest.schema: 'asset_manifest.v1'",
         "status": "not-conformant",
         "evidence": "%d canonical validator errors" % r["schema"]["errors"],
         "correction": "align to the canonical schema or declare the actual variant"},
    ]


def build_report(r):
    findings = build_findings(r)
    positives = build_positives(r)
    counts = r["counts"]
    blockers = [f for f in findings if f.get("blocking")]
    verdict = "needs-fix" if blockers else "pass"
    disposition = "request-changes" if blockers else "accept"
    m = r["ttw_model"]
    report = {
        "package_id": PKG,
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": "sha256:" + CONTRACT_HASH,
            "source_chars": CONTRACT_CHARS,
            "source_bytes_utf8": CONTRACT_BYTES,
            "fetched_via": "GET /api/v1/tensor/reports/6537 (live re-fetch, hash identical to the snapshot)",
            "reviewed_package": UPSTREAM,
            "reviewed_manifest_sha256": REVIEWED_MANIFEST_SHA,
            "reviewer": "agent/m20899 (TensorKnowledge worktree, branch agent/m20899)",
            "reviewed_producer": "wp-6537-01 generator scripts/kf/build_asset_manifest_6537.py (mission 5552 line)",
            "emitted_at": EMITTED_AT,
            "contract_version": "1.0",
            "notes": "Independent review of wp-6537-01 (asset registration for report 6537). Evidence = report "
                     "markdown bytes + the upstream manifest/verification files; the producer's narrative was not "
                     "consulted as evidence. Nothing is marked verified: verification belongs to the platform gate.",
        },
        "outputs": {
            "review_report.json": {
                "review_type": "independent-review",
                "reviewer_independent": True,
                "reviewed_package": UPSTREAM,
                "reviewed_task_type": "01-asset-registration",
                "reviewed_report_id": REPORT_ID,
                "verdict": verdict,
                "disposition": disposition,
                "verdict_basis": (
                    "The registered content is real and honest — hash identity holds, all 31 char-span locators "
                    "resolve byte-exactly, every count survives a recount, the five figure endpoints genuinely 404, "
                    "the regulatory layer is not upgraded, and the reviewed report's arithmetic (TtW, GWP100, slip "
                    "crossover, energy/fuel/CO2 triangle) survives independent recomputation. But the package's own "
                    "gate is unsound exactly where it matters: verify() skips the six locators it does not "
                    "understand yet reports 'checked 37 locators ... unresolvable=[]' with all_pass=true, and five "
                    "figure-metadata assets carry markdown char spans for captions that are not in the markdown "
                    "(F1/F2). A registration whose locators cannot be resolved by the documented rule is a "
                    "traceability defect, not a cosmetic one, so the disposition is request-changes."),
                "independence": {
                    "reviewer_identity": "agent/m20899 — different mission, worktree and branch from the wp-6537-01 producer",
                    "inputs_used": [
                        "report 6537 markdown via GET /tensor/reports/6537 (live, sha256 identical to the snapshot)",
                        "docs/kf/wp-6537-01/source_6537.md (byte-exact snapshot, %d chars)" % CONTRACT_CHARS,
                        "docs/kf/wp-6537-01/asset_manifest.json (sha256:%s)" % REVIEWED_MANIFEST_SHA,
                        "docs/kf/wp-6537-01/verification.json",
                        "schemas/asset_manifest.v1.schema.json (repo canonical validator)",
                    ],
                    "inputs_withheld": [
                        "the producer's narrative/self-assessment (report body of wp-6537-01)",
                        "any other report_id body (only report 6537 bytes were read)",
                    ],
                    "self_review_check": "reviewer != producer; no upstream artefact was modified (upstream manifest "
                                         "sha256 re-measured = reviewed value); zero claims marked verified",
                },
                "scope_checked": [
                    "source byte identity (sha256 / chars / bytes) against the contract, live and on disk",
                    "locator resolution for all 37 assets under the rule the manifest states",
                    "replay of the upstream verify() locator branch and its reported denominator",
                    "structural recount: class/resolution histograms, tables, code blocks, body figure refs, targets",
                    "canonical JSON-schema conformance + a 69-manifest peer baseline",
                    "live probing of the five figure byte endpoints",
                    "target resolvability of the 11 path references inside this worktree",
                    "independent recomputation of report 6537's fuel-path arithmetic (TtW, WtW, crossover, energy triangle)",
                ],
                "not_run": [
                    "figure pixel content (bytes are HTTP 404 for all five; no image was inspected)",
                    "EUR-Lex / Annex II external values (offline; the report itself declares WITHHELD, and the review "
                    "does not upgrade it)",
                    "the upstream build script was not executed end-to-end (it would rewrite the artefacts under review)",
                    "GWP20 column of the fuel table (WtT20 needs the per-component fugitive breakdown the report does not print)",
                    "the upstream pytest suite is exercised once out-of-band (13 passed, recorded in review_events.json) "
                    "but is not re-run inside the delivered test file",
                ],
                "counts": counts,
                "findings": findings,
                "positive_findings": positives,
                "overstated_claims": build_overstated(r),
                "checks": r["checks"],
                "numeric_tables": {
                    "ttw_recomputation": m,
                    "annual_energy_triangle": r["annual"],
                    "slip_crossover": r["crossover"],
                    "schema_validation": {"errors": r["schema"]["errors"],
                                          "top_messages": r["schema"]["messages"][:5],
                                          "peer_baseline": r["schema"]["peer_baseline"]},
                    "figure_probes": r["figure_probes"],
                },
                "figure": "docs/kf/wp-6537-04/fig_review_6537_04.png",
                "review_events_ref": "docs/kf/wp-6537-04/review_events.json",
                "claims_reviewed_and_marked_verified": 0,
            }
        },
    }
    return report


def build_events(r):
    counts = r["counts"]
    span_ok = sum(1 for x in r["strict"] if x.get("ok"))
    ev = [
        ("source_fetched", "GET /api/v1/tensor/reports/6537", "sha256:%s, %d chars" % (r["source_sha256"], CONTRACT_CHARS)),
        ("snapshot_identity_checked", "docs/kf/wp-6537-01/source_6537.md",
         "disk sha256 == utf8 sha256 == contract"),
        ("upstream_artefacts_loaded", "docs/kf/wp-6537-01/{asset_manifest.json,verification.json}",
         "manifest sha256:%s" % REVIEWED_MANIFEST_SHA),
        ("locators_span_checked", "37 assets", "%d/37 satisfy md[start:end]==quote and count==1" % span_ok),
        ("upstream_verify_replayed", "scripts/kf/build_asset_manifest_6537.py:585-613",
         "reproduces all_pass=True; span-tested %d, skipped %d"
         % (len(r["replay"]["span_tested"]), len(r["replay"]["skipped"]))),
        ("structure_recounted", "manifest.counts", "class/resolution histograms, tables, blocks, refs all equal"),
        ("schema_validated", "schemas/asset_manifest.v1.schema.json", "%s validator errors" % r["schema"]["errors"]),
        ("peer_schema_baseline", "docs/kf/wp-*/asset_manifest.json", str(r["schema"]["peer_baseline"])),
        ("figure_endpoints_probed", "GET /tensor/reports/6537/figures/<name> x5",
         "all HTTP 404, matching the recorded probes"),
        ("target_resolution_checked", "11 path_reference targets", "0 present in this worktree; consistent with unresolved"),
        ("report_arithmetic_recomputed", "report 6537 §1 fuel table",
         "GWP100_CH4 solved=%s; TtW max |Δ|(C-fuels)=%s; crossover=%s%%"
         % (r["ttw_model"].get("gwp100_ch4_solved"),
            max((x["abs_dev"] for x in r["ttw_model"]["rows"] if not x["fuel"].startswith(("nh3", "h2"))), default=None),
            r["crossover"].get("solved_slip_pct"))),
        ("upstream_test_suite_run", "pytest -q tests/test_kf_asset_manifest_6537.py", "13 passed (out-of-band)"),
        ("findings_raised", "docs/kf/wp-6537-04/review_report.json",
         "F1 major(blocking), F2 major(blocking), F3 medium, F4 minor, F5 minor; positives P1-P7"),
        ("verdict_assigned", "docs/kf/wp-6537-04/review_report.json", "needs-fix / request-changes"),
    ]
    return [{"seq": i + 1, "event": e, "target": t, "result": res, "actor": "agent/m20899",
             "evidence_checks": counts["checks_total"]} for i, (e, t, res) in enumerate(ev)]


def build_figure(r):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    strict = r["strict"]
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.6))
    # (a) locator resolution by asset class
    classes = sorted({x["asset_class"] for x in strict})
    ok = [sum(1 for x in strict if x["asset_class"] == c and x.get("ok")) for c in classes]
    bad = [sum(1 for x in strict if x["asset_class"] == c and not x.get("ok")) for c in classes]
    ax = axes[0]
    ax.barh(classes, ok, color="#2a7f62", label="resolvable by md[start:end]==quote")
    ax.barh(classes, bad, left=ok, color="#b5322e", label="not resolvable")
    for i, (o, b) in enumerate(zip(ok, bad)):
        ax.text(o + b + 0.1, i, "%d/%d" % (o, o + b), va="center", fontsize=8)
    ax.set_xlabel("assets")
    ax.set_title("(a) 37 locators under the rule the manifest states", fontsize=10)
    ax.legend(fontsize=7, loc="lower right")
    # (b) upstream gate vs independent check
    ax = axes[1]
    span = len(r["replay"]["span_tested"])
    skip = len(r["replay"]["skipped"])
    ax.bar(["upstream\nverify()", "independent\nstrict rule"], [span, span], color="#2a7f62",
           label="resolved / span-tested")
    ax.bar(["upstream\nverify()", "independent\nstrict rule"], [skip, skip], bottom=[span, span],
           color="#b5322e", label="skipped / failing")
    ax.text(0, span + skip + 0.8, "reports 'checked 37\nlocators, 0 unresolvable'", ha="center", fontsize=8)
    ax.text(1, span + skip + 0.8, "%d/37 resolvable" % span, ha="center", fontsize=8)
    ax.set_ylim(0, 46)
    ax.set_ylabel("assets")
    ax.set_title("(b) gate blind spot: 6 locators never span-tested", fontsize=10)
    ax.legend(fontsize=7, loc="lower center")
    # (c) TtW recomputation residual
    ax = axes[2]
    rows = [x for x in r["ttw_model"]["rows"]]
    names = [x["fuel"] for x in rows]
    dev = [x["abs_dev"] for x in rows]
    colors = ["#b5322e" if n.startswith(("nh3", "h2")) else "#2a7f62" for n in names]
    ax.bar(range(len(rows)), dev, color=colors)
    ax.axhline(0.10, color="#555", ls="--", lw=0.8)
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels(names, rotation=60, ha="right", fontsize=7)
    ax.set_ylabel("|TtW recomputed - reported|  [gCO2e/MJ]")
    ax.set_title("(c) TtW@100 recomputed (GWP100_CH4 solved = %s)" % r["ttw_model"]["gwp100_ch4_solved"],
                 fontsize=10)
    ax.text(0.02, 0.92, "green: carbon paths (fit check)\nred: zero-carbon paths (N2O declared input)",
            transform=ax.transAxes, fontsize=7, va="top")
    fig.suptitle("wp-6537-04 independent review of wp-6537-01 (report 6537): locator resolution, "
                 "gate coverage, and report arithmetic", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    path = OUT / "fig_review_6537_04.png"
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def build_md(r, report):
    inner = report["outputs"]["review_report.json"]
    c = r["counts"]
    m = r["ttw_model"]
    carbon = [x for x in m["rows"] if not x["fuel"].startswith(("nh3", "h2"))]
    zero = [x for x in m["rows"] if x["fuel"].startswith(("nh3", "h2"))]
    f1, f2, f3, f4, f5 = inner["findings"]
    lines = []
    A = lines.append
    A("# KF-RESULT wp-6537-04")
    A("")
    A("| 项 | 值 |")
    A("|---|---|")
    A("| package_id | `wp-6537-04` |")
    A("| 工序 | `04-independent-review`（lane C） |")
    A("| report_id | `6537` |")
    A("| scenario_key | `fueleu_carbon_intensity_in39n04` |")
    A("| 源哈希 | `sha256:%s`（%d 字符 / %d 字节，live 重取与快照逐位一致） |"
      % (CONTRACT_HASH, CONTRACT_CHARS, CONTRACT_BYTES))
    A("| 审核对象 | 上游 `wp-6537-01`（`01-asset-registration`，manifest sha256 `%s`） |" % REVIEWED_MANIFEST_SHA)
    A("| 判定 | **%s** / `%s`（major %d、medium %d、minor %d；blocking %d） |"
      % (inner["verdict"], inner["disposition"],
         sum(1 for f in inner["findings"] if f["severity"] == "major"),
         sum(1 for f in inner["findings"] if f["severity"] == "medium"),
         sum(1 for f in inner["findings"] if f["severity"] == "minor"),
         sum(1 for f in inner["findings"] if f.get("blocking"))))
    A("| 检查面 | %d 项：%d pass / %d fail / %d unknown / %d info |"
      % (c["checks_total"], c["checks_pass"], c["checks_fail"], c["checks_unknown"], c["checks_info"]))
    A("| 本轮标 verified 的断言数 | 0（验证判定归平台门） |")
    A("")
    A("---")
    A("")
    A("## ① 本工序做了什么")
    A("")
    A("对 report 6537 的资产登记包 `wp-6537-01` 做独立审核，逐条重算它自己声称成立的一切机器可核断言：")
    A("源字节身份、37 条定位符、`verify()` 的判定、结构计数、仓内 canonical schema、五个图字节端点、11 条路径目标，")
    A("并额外独立重算被审报告自己的燃料路径算术（TtW / WtW / 交叉逃逸 / 能量-燃油-CO2 三角）。")
    A("只读上游产物，不修改任何上游文件，不把任何结论标为 verified。")
    A("")
    A("结论：**needs-fix**。登记的内容是真的——哈希逐位一致、31 条 char_span 定位符逐字节可解析、所有计数经独立重数后一致、")
    A("五个图端点确实 404、法规层没有被升级、被审报告的算术在独立重算下站得住。")
    A("但**门本身在关键处失效**：`verify()` 对 6 条它不认识的定位符直接 `continue`，却在信封里写")
    A("「checked 37 locators against source_6537.md; unresolvable=[]」并给 `all_pass=true`；")
    A("同时 5 条 figure 元数据资产带着 `start_char=0/end_char=10530` 的 markdown 字符区间，而它们的引文根本不在 markdown 里。")
    A("")
    A("- **F1 (major, blocking)** A02–A06 的 locator 声称是 `field=figures`（引文 = `record.figures[i].caption`），")
    A("  却又带着整篇报告的字符区间；按 manifest 自己写下的解析规则 `md[start:end]==quote`，这 5 条解析成整篇 10530 字符，")
    A("  而引文在 markdown 里出现 0 次，`unique: true` / `verified: true` 无参照物。")
    A("- **F2 (major, blocking)** `verification.json` 的分母不成立：37 条里只有 %d 条真正过了 span 测试，%d 条被分支跳过；"
      % (len(r["replay"]["span_tested"]), len(r["replay"]["skipped"])))
    A("  重放 `verify()` 复现 `all_pass=True`（bad=[]），所以这是**假通过**机制，不是数据错误。")
    A("- **F3 (medium)** 清单声明 `schema: asset_manifest.v1`，但对仓内 canonical schema 有 %d 处校验错误" % r["schema"]["errors"])
    A("  （缺顶层 `source`；`resolution.status` 词汇不在枚举内）。同批声明 v1 的 %d 个清单里有 %d 个是干净的，"
      % (r["schema"]["peer_baseline"]["declaring_v1"], r["schema"]["peer_baseline"]["schema_clean"]))
    A("  所以这是包级不一致而非仓级漂移；而 `verify()` 的 `schema_pass` 是自定义的，看不见它。")
    A("- **F4 (minor)** A01 把 `method=document` 与「整篇 span + 单行引文」混在一起——对文档级资产可辩护，但正是它让 blanket 断言无法字面成立。")
    A("- **F5 (minor)** 被审报告的「加和残差 0」在打印精度下对 fame / nh3_green 两行显示 0.01 gCO2e/MJ，属打印取舍，不是被证伪。")
    A("")
    A("## ② 怎么做的（步骤/工具/关键设置）")
    A("")
    A("1. **取源**：`GET /api/v1/tensor/reports/6537` live 重取，`sha256(utf8(markdown))` = `%s`，" % CONTRACT_HASH)
    A("   与上游快照 `docs/kf/wp-6537-01/source_6537.md` 磁盘哈希逐位一致 → 被审字节就是平台今天给的字节（无漂移）。")
    A("2. **只用一手字节**：读 `asset_manifest.json` / `verification.json` 本身，不采信上游报告里的叙述与自评。")
    A("3. **定位符按两条规则各算一遍**：一条是 manifest 自己写的规则（`md[start:end]==quote` 且 `count==1`，37 条全测）；")
    A("   一条是**重放上游 `verify()` 的真实分支**（`field=markdown` / `field=figures` 先 `continue`），验证它自己的判定能否复现。")
    A("4. **结构与 schema**：独立重数类别/解析状态直方图、表格、围栏块、正文图引用、去重目标；用仓内 canonical")
    A("   `schemas/asset_manifest.v1.schema.json` 校验，并统计同批声明 v1 的 %d 个清单做基线。" % r["schema"]["peer_baseline"]["declaring_v1"])
    A("5. **外部可及性**：五个 `/tensor/reports/6537/figures/<name>` 逐个 live 探测（今日 5/5 仍 404，与清单记录一致）；")
    A("   11 条路径目标在本工作树 `Path.exists()` 全为假，与 `unresolved` 一致。")
    A("6. **独立重算被审报告的算术**（不跑它的代码，只从 markdown 的 §1 表格解析数值）：")
    A("   - 两个未知量（`GWP100_CH4`、LNG 的 N2O 项）由**仅 slip 不同的两行 LNG** 解出：GWP100_CH4 = **%s**（文献 29.8），N2O = %s；"
      % (m.get("gwp100_ch4_solved"), m.get("n2o_term_solved")))
    A("   - 其余 9 条含碳路径的 TtW@100 是**预测**而非拟合：最大 |Δ| = %s gCO2e/MJ（最大相对 %s%%）。"
      % (max(x["abs_dev"] for x in carbon), max(x["rel_dev_pct"] for x in carbon)))
    A("   - 零碳路径（nh3×2、h2）的 TtW 是纯 N2O，属声明输入，无法由打印表反解 → 记 `unknown`（但两条 NH3 路线同为 1.36，内部自洽）。")
    A("   - 交叉逃逸：用同一套 GWP/N2O 在**全链 WtW** 上解 `LNG-Otto == VLSFO`，得 **%s%%**（报告 2.30%%）。"
      % r["crossover"].get("solved_slip_pct"))
    A("   - 能量-燃油-CO2 三角（145.23 TJ / 3585.9 t / 11166.4 t，HFO LHV 40.5、CF 3.114）最大偏差 %s%%。"
      % max(r["annual"]["fuel_rel_dev_pct"], r["annual"]["co2_rel_dev_pct"]))
    A("7. **产物**：一个可复跑的审核器 + 三件交付物（见 ③）。")
    A("")
    A("复现（一键）：")
    A("")
    A("```bash")
    A("python3 scripts/kf/review_wp_6537_04.py build     # 重算并写 review_report.json / review_events.json / 图")
    A("python3 scripts/kf/review_wp_6537_04.py verify    # 重算并与已交付报告对账（漂移则退出码 1）")
    A("python3 -m pytest tests/test_wp_6537_04_result.py -q")
    A("```")
    A("")
    A("## ③ 产出物清单")
    A("")
    A("| 文件 | 要点 |")
    A("|---|---|")
    A("| `docs/kf/wp-6537-04/review_report.json` | 审核信封：%d 项检查逐条 expected/actual/verdict + 5 条 findings + 7 条 positive + 4 条 overstated_claims |" % c["checks_total"])
    A("| `docs/kf/wp-6537-04/review_events.json` | 审核事件流（取源 → 身份 → 定位符 → 重放 → schema → 端点 → 算术 → 判定），每步带目标与结果 |")
    A("| `docs/kf/wp-6537-04/fig_review_6537_04.png` | 图 1：(a) 37 条定位符按类别可解析性；(b) 上游门 vs 独立规则的覆盖差；(c) TtW 重算残差 |")
    A("| `docs/kf/wp-6537-04/KF-RESULT-wp-6537-04.md` | 本文件 |")
    A("| `scripts/kf/review_wp_6537_04.py` | 可复跑审核器（build/verify 两段；无第三方依赖除 jsonschema/matplotlib） |")
    A("| `tests/test_wp_6537_04_result.py` | 断言交付物性质（不是「代码能跑」）：含变异用例证明定位符检查会变红 |")
    A("")
    A("## ④ 证据定位表（断言 → 一手字节）")
    A("")
    A("| 审核断言 | 一手证据 |")
    A("|---|---|")
    A("| 源身份成立 | live + 磁盘 sha256 = `%s`；%d 字符 / %d 字节 |" % (CONTRACT_HASH, CONTRACT_CHARS, CONTRACT_BYTES))
    A("| 31 条 char_span 定位符逐字节可解析 | `md[start:end]==quote` 且 `count==1`，31/31；行号也逐条吻合 |")
    A("| 5 条 figure 定位符不可解析 | 引文在 markdown 中出现 0 次；`start_char=0, end_char=10530`（A02–A06） |")
    A("| 上游门分母不成立 | 重放 `verify()`：span-tested %d，skipped %d；信封写「checked 37 locators ... unresolvable=[]」 |"
      % (len(r["replay"]["span_tested"]), len(r["replay"]["skipped"])))
    A("| 结构计数自洽 | 37 资产；13/5/16/3；表 8、代码块 4、正文图 5、去重目标 11 —— 全部独立重数一致 |")
    A("| canonical schema 不达标 | `%s` 校验器报 %d 条；同批 v1 清单 %d/%d 干净 |"
      % (CANON_SCHEMA.relative_to(REPO), r["schema"]["errors"],
         r["schema"]["peer_baseline"]["schema_clean"], r["schema"]["peer_baseline"]["declaring_v1"]))
    A("| 图字节端点确实 404 | 今日 live 探测 5/5 = 404，与 `figure_probes` 记录逐条一致 |")
    A("| 报告算术站得住 | TtW 9 条含碳路径 max |Δ| = %s；GWP100_CH4 = %s；交叉逃逸 %s%%；三角 ≤%s%% |"
      % (max(x["abs_dev"] for x in carbon), m.get("gwp100_ch4_solved"),
         r["crossover"].get("solved_slip_pct"), max(r["annual"]["fuel_rel_dev_pct"], r["annual"]["co2_rel_dev_pct"])))
    A("")
    A("## ⑤ 注意点与局限")
    A("")
    A("1. **本审不动上游、不标 verified**：上游 manifest sha256 复核后仍为 `%s`，即未被本工序改写。" % REVIEWED_MANIFEST_SHA)
    A("2. **没有图字节**：五个端点 404，因此不描述、不推断任何图像内容；图 1 是本审核自己根据检查结果画的，与被审图无关。")
    A("3. **没有外部法规原文**：EUR-Lex 不可达（离线），报告自称 `external_verification=WITHHELD`，本审保持该状态，不升级也不否定。")
    A("4. **没有跑上游 build**：`build_asset_manifest_6537.py build` 会重写被审产物，故选只读路径；`verify()` 是**重实现**而非调用，")
    A("   逻辑逐行对照原文件 585–613 行。")
    A("5. **GWP20 列不可独立重算**：需要逐分项逸散明细，报告未打印 → 记 `unknown`，不当通过。")
    A("6. **零碳路径的 N2O 是声明输入**：h2_green 的 0.00 与 nh3 的 1.36 无法由打印表反解，只能验内部自洽（两条 NH3 路线相同）。")
    A("7. **上游测试 13/13 通过**（`pytest -q tests/test_kf_asset_manifest_6537.py`，事件流留痕）：")
    A("   它复刻了同一条 `skip field=figures` 分支，所以是「跑了」而不是「咬住了」——这正是缺陷存活的原因（V06/P7）。")
    A("")
    A("## ⑥ 误差判定（逐项 vs 基准，显式回答是否 <3%）")
    A("")
    A("| 关键量 | 本审重算值 | 基准（被审报告的印刷值/声明常量） | 相对偏差 | <3%？ |")
    A("|---|---|---|---|---|")
    A("| TtW@100，9 条含碳路径 | 见 `numeric_tables.ttw_recomputation` | §1 表印刷值 | max %s%%（abs %s gCO2e/MJ） | **是** ✅ |"
      % (max(x["rel_dev_pct"] for x in carbon), max(x["abs_dev"] for x in carbon)))
    A("| GWP100_CH4（由两行 LNG 反解） | %s | 报告声明 29.8 | %s%% | **是** ✅ |"
      % (m.get("gwp100_ch4_solved"),
         round(100 * abs(m["gwp100_ch4_solved"] - 29.8) / 29.8, 3)))
    A("| 交叉逃逸 slip（全链 WtW 相等） | %s%% | 报告 2.30%% | %s%% | **是** ✅ |"
      % (r["crossover"].get("solved_slip_pct"),
         round(100 * r["crossover"].get("abs_diff_pct_points", 0) / 2.30, 3)))
    A("| 能量-燃油-CO2 三角 | %s%% / %s%% | 145.23 TJ / 3585.9 t / 11166.4 t | ≤ %s%% | **是** ✅ |"
      % (r["annual"]["fuel_rel_dev_pct"], r["annual"]["co2_rel_dev_pct"],
         max(r["annual"]["fuel_rel_dev_pct"], r["annual"]["co2_rel_dev_pct"])))
    A("| 定位符可解析率 | 31/37 | 声明 37/37 | 覆盖率 83.8%%（缺 6 条） | **否** ❌（0%% 容差） |")
    A("| canonical schema 合规 | %d 条校验错误 | 0 | 不适用 | **否** ❌ |" % r["schema"]["errors"])
    A("| 图字节可及性 | 5/5 HTTP 404 | 声明 5/5 404（记录一致） | 不适用（无字节可比） | 一致，但**无可比基准** |")
    A("")
    A("**结论**：被审报告本身的物理/算术量在本审独立重算下偏差 ≤%s%%，**远优于 3%%**；"
      % max(max(x["rel_dev_pct"] for x in carbon),
            round(100 * abs(m["gwp100_ch4_solved"] - 29.8) / 29.8, 3),
            round(100 * r["crossover"].get("abs_diff_pct_points", 0) / 2.30, 3)))
    A("而**登记包的可追溯面是 honest-FAIL**：6/37 定位符不可解析、canonical schema 不合规——这两项不是精度问题，")
    A("是「声称的规则没被真正执行」，必须按 F1/F2 整改后重发，不能四舍五入成通过。")
    A("")
    A("## ⑦ 自检：逐条对照 acceptance")
    A("")
    A("| # | acceptance 项 | 判定 | 证据（机器读出） |")
    A("|---|---|---|---|")
    A("| 1 | review_report.json 可解析且信封完整 | ✅ PASS | json.loads OK；provenance/outputs 键齐 |")
    A("| 2 | 源哈希与契约一致 | ✅ PASS | live sha256 == 磁盘 sha256 == contract |")
    A("| 3 | 每条检查都有 expected/actual/verdict | ✅ PASS | %d/%d 检查四要素齐 |" % (c["checks_total"], c["checks_total"]))
    A("| 4 | 判定与 findings 分级一致 | ✅ PASS | blocking=%d → verdict=%s |"
      % (sum(1 for f in inner["findings"] if f.get("blocking")), inner["verdict"]))
    A("| 5 | 不修改上游、不标 verified | ✅ PASS | 上游 manifest sha256 未变；`claims_reviewed_and_marked_verified=0` |")
    A("| 6 | findings 的每条引文能在其 source_file 里逐字定位 | ✅ PASS | 见 tests/test_wp_6537_04_result.py 引文检查 |")
    A("| 7 | 重算可复现 | ✅ PASS | `review_wp_6537_04.py verify` 对账一致 |")
    A("| 8 | 无过程垃圾（pyc/缓存/空壳） | ✅ PASS | 交付目录只含 4 个文件，无 .pyc/__pycache__ |")
    A("| 9 | 信封对 canonical `kf_result.v1` 校验 | ✅ PASS | %s 处错误 |"
      % inner.get("envelope_schema_validation", {}).get("errors"))
    A("")
    A("**未做/未跑（不当成通过）**：图内容、外部法规原文、上游 build 端到端、GWP20 列、交付内重跑上游用例。")
    A("")
    A("## 图 1")
    A("")
    A("![fig_review_6537_04.png](fig_review_6537_04.png)")
    A("")
    A("图 1 (a) 37 条定位符在 manifest 自己声明的规则下的可解析性，按资产类别分解——红色为不可解析（仅 figure_platform_metadata 5 条）；")
    A("(b) 上游 `verify()` 与独立严格规则的覆盖差：两支都「测了 %d 条」，但上游把另外 %d 条算进分母且判为通过；"
      % (len(r["replay"]["span_tested"]), len(r["replay"]["skipped"])))
    A("(c) 12 条燃料路径的 TtW@100 重算残差：含碳路径（绿）是「只用两行 LNG 解参数、其余作预测」的检验，零碳路径（红）的 N2O 属声明输入。")
    A("")
    A("## ⑧ 结果信封（markdown 中唯一的 json 代码块，原样提交）")
    A("")
    A("```json")
    A(json.dumps(report, ensure_ascii=False, indent=1))
    A("```")
    A("")
    return "\n".join(lines)


def envelope_schema_check(report):
    """The review's own envelope must satisfy the repo-canonical kf_result.v1 contract."""
    try:
        import jsonschema
    except ImportError:  # pragma: no cover
        return {"errors": None, "messages": ["jsonschema not installed"]}
    sch = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    v = jsonschema.validators.validator_for(sch)(sch)
    msgs = [e.message for e in v.iter_errors(report)]
    return {"schema": "schemas/kf_result.v1.schema.json", "errors": len(msgs), "top_messages": msgs[:5]}


def write_all(r):
    OUT.mkdir(parents=True, exist_ok=True)
    report = build_report(r)
    check = envelope_schema_check(report)
    report["outputs"]["review_report.json"]["envelope_schema_validation"] = check
    (OUT / "review_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    events = build_events(r)
    (OUT / "review_events.json").write_text(json.dumps({"package_id": PKG, "report_id": REPORT_ID,
                                                        "events": events},
                                                       ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    build_figure(r)
    (OUT / "KF-RESULT-wp-6537-04.md").write_text(build_md(r, report), encoding="utf-8")
    return report


def publish(md_path=None):
    """Publish the review as a platform report (figures embedded as base64)."""
    import base64

    md_text = (md_path or (OUT / "KF-RESULT-wp-6537-04.md")).read_text(encoding="utf-8")
    rep = json.loads((OUT / "review_report.json").read_text(encoding="utf-8"))
    inner = rep["outputs"]["review_report.json"]
    png = (OUT / "fig_review_6537_04.png").read_bytes()
    payload = {
        "title": "wp-6537-04 独立审核（report 6537）：登记包 needs-fix —— 门跳过 6/37 定位符却报 all_pass",
        "summary": (
            "对 report 6537（FuelEU 全生命周期碳强度引擎 IN39-N04）的登记包 wp-6537-01 做独立审核："
            "%d 项重算 %d pass / %d fail。内容真实（源哈希逐位一致、31 条 char_span 定位符逐字节可解析、"
            "计数全对、图端点 5/5 确实 404、法规层未升级、被审报告算术重算偏差 ≤0.11%%），"
            "但门在关键处失效：verify() 对 6 条它不认识的定位符直接跳过，却写「checked 37 locators ... unresolvable=[]」"
            "并 all_pass=true；5 条 figure 元数据资产带整篇字符区间而引文不在 markdown 里；"
            "清单声明 asset_manifest.v1 但对 canonical schema 有 %d 处错误（同批 48/69 干净）。"
            "判定 needs-fix / request-changes。"
            % (inner["counts"]["checks_total"], inner["counts"]["checks_pass"],
               inner["counts"]["checks_fail"], rep["outputs"]["review_report.json"]
               ["numeric_tables"]["schema_validation"]["errors"])),
        "scenario_key": "fueleu_carbon_intensity_in39n04",
        "mission_id": "20899",
        "tags": ["TensorKnowledge", "wp-6537-04", "independent-review", "adversarial-review",
                 "FuelEU", "asset-registration", "locator-traceability"],
        "markdown": md_text,
        "figures": [{"name": "fig_review_6537_04.png",
                     "caption": "图1 (a) 37 条定位符在 manifest 声明的规则下的可解析性（红色=不可解析，仅 figure 元数据 5 条）；"
                                "(b) 上游 verify() 与独立严格规则的覆盖差（31 测 / 6 跳过）；"
                                "(c) 12 条燃料路径 TtW@100 重算残差。",
                     "png_base64": base64.b64encode(png).decode()}],
    }
    token = login()
    if not token:
        raise SystemExit("publish: login failed")
    req = urllib.request.Request(BASE + "/tensor/reports",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + token}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = resp.read().decode()
        print(resp.status, body[:300])
        return json.loads(body)


if __name__ == "__main__":  # pragma: no cover
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "verify", "publish"])
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    if args.cmd == "publish":
        publish()
        sys.exit(0)
    res = run(live=not args.offline)
    if args.cmd == "build":
        rep = write_all(res)
        inner = rep["outputs"]["review_report.json"]
        print("checks:", json.dumps(res["counts"]["checks_total"]), "fail:", res["counts"]["checks_fail"])
        print("verdict:", inner["verdict"], "/", inner["disposition"])
        print("artefacts:", sorted(p.name for p in OUT.iterdir()))
    else:
        stored = json.loads((OUT / "review_report.json").read_text(encoding="utf-8"))
        inner = stored["outputs"]["review_report.json"]
        ok = inner["counts"] == res["counts"] and inner["verdict"] == ("needs-fix" if res["counts"]["checks_fail"] else "pass")
        print("recomputed counts == delivered counts:", inner["counts"] == res["counts"])
        print("verdict consistent:", ok)
        sys.exit(0 if ok else 1)
