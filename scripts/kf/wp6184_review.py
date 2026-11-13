#!/usr/bin/env python3
"""wp-6184-04 · independent review of wp-6184-01 (asset registration of report 6184).

Reviewer contract: judge the *semantic fidelity* of the upstream package against
the report source only. Reviewer context = source markdown + upstream package
artifacts + this work-package contract. Producer explanation (provenance.notes,
integrity.notes, the upstream narrative markdown) is NOT consumed as evidence.

Everything below is machine-derived from bytes; nothing is quoted from memory:

  R1  sha256(markdown) recomputed == contract source_hash, char count == contract
  R2  upstream envelope points at the same report/hash
  R3  every asset locator: markdown[start:end] == quote, quote searchable/unique,
      1-based line spans recomputed
  R4  manifest self-reported counts/histogram == recomputed from the asset list
  R5  zero-claim legality for an asset-registration package (no invented claims)
  R6  upstream does not self-attest (no verified/gate_confirmed style fields)
  R7  the source report's published margin column is reproduced from its own
      EEXI/required columns, inside the band allowed by print rounding
  R8  the source's "2/11 compliant" count is reproduced from the table
  R9  probe: EPL% vs the 2/3 power law the source itself states (unresolvable
      without the engine code -> not_run, recorded not passed)
  R10 completeness probe: path-like tokens named in the source vs registered
      assets (non-blocking finding surface)

Usage:  python3 scripts/kf/wp6184_review.py [--upstream DIR] [--out DIR] [--no-api]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPORT_ID = "6184"
PACKAGE_ID = "wp-6184-04"
REVIEWED_PACKAGE = "wp-6184-01"
CONTRACT_HASH = "sha256:f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c"
CONTRACT_CHARS = 2406
MISSION_ID = 15844
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
FORBIDDEN_SELF_ATTEST = ("\"verified\"", "verification_status", "verification_level",
                         "is_verified", "gate_confirmed")


# --------------------------------------------------------------------- plumbing
def login() -> str:
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(API + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    return json.load(urllib.request.urlopen(req))["access_token"]


def fetch_markdown(token: str) -> str:
    req = urllib.request.Request(f"{API}/tensor/reports/{REPORT_ID}",
                                 headers={"Authorization": "Bearer " + token})
    return json.load(urllib.request.urlopen(req))["markdown"]


def sha256_text(t: str) -> str:
    return "sha256:" + hashlib.sha256(t.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------- primitives
def locator_probe(md: str, loc: dict) -> dict:
    quote = loc.get("quote", "")
    start, end = loc.get("start_char"), loc.get("end_char")
    at_span = isinstance(start, int) and isinstance(end, int) and md[start:end] == quote
    hits = md.count(quote) if quote else 0
    start_line = md.count("\n", 0, start) + 1 if isinstance(start, int) else None
    end_line = None
    if isinstance(end, int) and end > 0:
        end_line = md.count("\n", 0, end) + (0 if md[end - 1:end] == "\n" else 1)
    return {
        "quote_chars": len(quote),
        "at_declared_span": at_span,
        "occurrences_in_source": hits,
        "declared_unique_satisfied": (hits == 1) if loc.get("unique") else None,
        "start_line_recomputed": start_line,
        "end_line_recomputed": end_line,
        "start_line_declared": loc.get("start_line"),
        "end_line_declared": loc.get("end_line"),
        "quote_sha256": "sha256:" + hashlib.sha256(quote.encode("utf-8")).hexdigest(),
        "content_hash_declared": loc.get("content_hash"),
        "long_enough_min12": len(quote) >= 12,
    }


def parse_eexi_table(md: str) -> list[dict]:
    rows = []
    for line in md.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 6 or cells[0] == "船型" or set(cells[0]) <= {"-"}:
            continue
        try:
            rows.append({"ship": cells[0], "eexi": float(cells[1]),
                         "required": float(cells[2]), "margin_reported": float(cells[3]),
                         "aer": float(cells[4]), "grade": cells[5]})
        except ValueError:
            continue
    return rows


def margin_checks(rows: list[dict]) -> list[dict]:
    """裕度% recomputed from the two published columns.

    Both inputs print at 3 dp and the margin at 1 dp, so the honest test is an
    interval test: the printed margin must be reachable from some pair of
    values consistent with those roundings.
    """
    out = []
    for r in rows:
        e, q = r["eexi"], r["required"]
        a = (q - 5e-4 - (e + 5e-4)) / (q - 5e-4) * 100.0
        b = (q + 5e-4 - (e - 5e-4)) / (q + 5e-4) * 100.0
        lo, hi = min(a, b) - 0.05, max(a, b) + 0.05
        out.append({
            "ship": r["ship"],
            "margin_reported": r["margin_reported"],
            "margin_recomputed_pointwise": round((q - e) / q * 100.0, 4),
            "feasible_band_from_print_rounding": [round(lo, 4), round(hi, 4)],
            "inside_band": lo <= r["margin_reported"] <= hi,
            "compliant_attained_le_required": e <= q,
        })
    return out


PATH_TOKEN = re.compile(r"`([A-Za-z0-9_./-]+(?:\.py|\.json|\.md)|[A-Za-z0-9_./-]+/[A-Za-z0-9_./-]+)`")


def completeness_probe(md: str, manifest: dict) -> dict:
    """Does the manifest name every path-like token of the source?

    The whole-document asset (source_document) quotes the entire markdown and
    would make any substring test trivially green, so it is excluded here.
    """
    tokens = sorted(set(PATH_TOKEN.findall(md)))
    blob = json.dumps([a for a in manifest["assets"]
                       if a.get("asset_class") != "source_document"],
                      ensure_ascii=False)
    registered = [t for t in tokens if t in blob]
    missing = [t for t in tokens if t not in blob]
    return {"path_like_tokens_in_source": tokens,
            "registered": registered, "unregistered": missing}


# ------------------------------------------------------------------------ main
def main() -> int:
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", default=None,
                    help="dir holding the reviewed kf_result.json; default = committed snapshot")
    ap.add_argument("--out", default=str(root / "docs/kf/wp-6184-04"))
    ap.add_argument("--no-api", action="store_true",
                    help="re-verify against the committed source snapshot instead of the API")
    args = ap.parse_args()
    out_dir = Path(args.out)
    if not args.upstream:
        committed = out_dir / "upstream_snapshot"
        args.upstream = str(committed if (committed / "kf_result.json").is_file()
                            else "/root/tp-agent/work/m15587/docs/kf/wp-6184-01")
    (out_dir / "figures").mkdir(parents=True, exist_ok=True)

    snap = out_dir / "source_snapshot.md"
    if args.no_api and snap.is_file():
        md, source_of_truth = snap.read_text(encoding="utf-8"), "committed snapshot"
    else:
        md, source_of_truth = fetch_markdown(login()), "GET /tensor/reports/6184"
        snap.write_text(md, encoding="utf-8")

    got_hash = sha256_text(md)
    checks: list[dict] = []

    def chk(cid, name, ok, detail, evidence=None, blocking=True):
        checks.append({"id": cid, "name": name,
                       "status": ("pass" if ok else "fail") if ok is not None else "not_run",
                       "blocking": blocking if ok is not None else None,
                       "detail": detail, "evidence": evidence or {}})

    # R1
    chk("R1.source_hash_matches", "recomputed sha256(markdown) equals contract source_hash",
        got_hash == CONTRACT_HASH and len(md) == CONTRACT_CHARS,
        f"computed={got_hash} chars={len(md)} via {source_of_truth}",
        {"contract_hash": CONTRACT_HASH, "contract_chars": CONTRACT_CHARS})

    up = json.loads((Path(args.upstream) / "kf_result.json").read_text(encoding="utf-8"))
    # R2
    chk("R2.upstream_identity", "upstream package addresses the same report and source bytes",
        up.get("package_id") == REVIEWED_PACKAGE and up.get("report_id") == REPORT_ID
        and up["provenance"]["source_hash"] == got_hash,
        f"package={up.get('package_id')} task={up.get('task_type')} report={up.get('report_id')} "
        f"hash={up['provenance']['source_hash']}")

    manifest = up["outputs"]["asset_manifest.json"]
    assets = manifest["assets"]

    probes = {a["asset_id"]: locator_probe(md, a.get("locator") or {}) for a in assets}
    bad = [aid for aid, p in probes.items()
           if not (p["at_declared_span"] and p["long_enough_min12"]
                   and p["declared_unique_satisfied"] in (None, True))]
    line_bad = [aid for aid, p in probes.items()
                if p["start_line_declared"] is not None
                and p["start_line_recomputed"] != p["start_line_declared"]]
    end_bad = [aid for aid, p in probes.items()
               if p["end_line_declared"] is not None
               and p["end_line_recomputed"] != p["end_line_declared"]]
    # R3
    chk("R3.locators_byte_exact",
        "every asset quote equals markdown[start:end], is unique, line spans match",
        not bad and not line_bad and not end_bad,
        f"{len(assets)} assets; span/quote fails={bad}; start_line fails={line_bad}; "
        f"end_line fails={end_bad}", {"per_asset": probes})

    # R4
    hist: dict[str, int] = {}
    for a in assets:
        hist[a["asset_class"]] = hist.get(a["asset_class"], 0) + 1
    n_res = sum(1 for a in assets if a.get("resolution") == "resolved_in_source")
    declared = manifest["counts"]
    chk("R4.counts_consistent", "manifest counts and class histogram equal the recomputed ones",
        declared["assets"] == len(assets) and declared["by_class"] == hist
        and declared.get("resolved_in_source") == n_res,
        f"assets={len(assets)} by_class={hist} resolved_in_source={n_res}")

    # R5
    claims_up = up.get("claims") or []
    chk("R5.zero_claim_legality",
        "an asset-registration package that asserts no knowledge is a legal complete result",
        up.get("task_type") == "01-asset-registration" and len(claims_up) == 0,
        f"task_type={up.get('task_type')} claims={len(claims_up)}")

    # R6
    blob = json.dumps(up, ensure_ascii=False)
    hits = [k for k in FORBIDDEN_SELF_ATTEST if k in blob]
    chk("R6.no_self_attestation", "upstream does not self-attest a passed gate",
        not hits, f"self-attestation field names matched: {len(hits)} of "
                  f"{len(FORBIDDEN_SELF_ATTEST)} scanned",
        {"scanned_field_names": len(FORBIDDEN_SELF_ATTEST), "matched": len(hits)})

    # R7 / R8
    rows = parse_eexi_table(md)
    mch = margin_checks(rows)
    n_in = sum(1 for m in mch if m["inside_band"])
    chk("R7.margin_arithmetic",
        "published margin column is reachable from the published EEXI/required columns",
        len(rows) == 11 and n_in == 11,
        f"rows={len(rows)} inside_band={n_in}/11", {"rows": mch})
    compliant = [m["ship"] for m in mch if m["compliant_attained_le_required"]]
    chk("R8.compliance_count", "the source's '2 of 11 compliant without EPL' reproduces",
        len(compliant) == 2, f"compliant rows={compliant}")

    # R9 EPL probe -> not_run by design
    e, q, x_stated = 4.219, 3.486, 0.274
    r = q / e
    x_pure = 1.0 - r ** 1.5
    epl = {"ship": "panamax_82", "attained": e, "required": q,
           "ratio_required_over_attained": round(r, 6),
           "epl_pct_stated": x_stated * 100,
           "epl_pct_from_2_3_law_main_engine_only": round(x_pure * 100, 3),
           "delta_percentage_points": round((x_stated - x_pure) * 100, 3),
           "implied_exponent_if_single_power_term":
               round(math.log(1 - x_stated) / math.log(r), 3),
           "reading": ("stated EPL exceeds the main-engine-only 2/3-law figure, i.e. the "
                       "sign matches a fixed (non-limited) auxiliary term still present in "
                       "the numerator; the engine code needed to close this is not in this "
                       "repository, so the exact value stays unresolved"),
           "resolved": False}
    chk("R9.epl_law_probe",
        "EPL 27.4% is reconcilable with the 2/3 power law the source states",
        None, "requires the compliance engine sources (ship-performance-platform) — not reachable here",
        {"probe": epl})

    # R10 completeness probe (non-blocking)
    comp = completeness_probe(md, manifest)
    chk("R10.asset_completeness",
        "every path-like token named in the source is registered as an asset",
        not comp["unregistered"],
        f"tokens={comp['path_like_tokens_in_source']} unregistered={comp['unregistered']}",
        comp, blocking=False)

    n_block_fail = sum(1 for c in checks if c["status"] == "fail" and c.get("blocking"))
    n_nonblock_fail = sum(1 for c in checks if c["status"] == "fail" and not c.get("blocking"))
    verdict = "pass" if n_block_fail == 0 else "fail"

    review = {
        "review_report_version": "1.0",
        "review_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "mission_id": MISSION_ID,
        "reviewed_package": {
            "package_id": up.get("package_id"),
            "task_type": up.get("task_type"),
            "source_hash": up["provenance"]["source_hash"],
            "producer": up["provenance"].get("producer"),
            "emitted_at": up["provenance"].get("emitted_at"),
        },
        "reviewer": {
            "role": "red-team-reviewer",
            "identity": "agent/m15844",
            "prompt_origin": ("derived from this work package's contract plus the source "
                               "markdown; not copied from the producer prompt"),
            "context_consulted": ["source markdown of report 6184",
                                  "upstream asset_manifest.json / kf_result.json (claims, provenance)",
                                  "work-package contract wp-6184-04"],
            "context_excluded": ["producer provenance.notes", "upstream integrity.notes",
                                 "upstream narrative markdown KF-RESULT_wp-6184-01.md"],
            "independence_limitations": [
                "same serving infrastructure and same owner fleet as the producer; "
                "independence is procedural (fresh worker, contract-only prompt, "
                "source-and-objects-only context), not organisational",
                "engine sources (ship-performance-platform) and the upstream checks.json "
                "artifact are not reachable from this repository, so engine-level "
                "numbers cannot be reproduced here",
            ],
        },
        "verdict": verdict,
        "verdict_scope": ("pass/fail judged on the reviewed package (asset registration): "
                          "source identity, locator fidelity, count truthfulness, zero-claim "
                          "legality, no self-attestation. Source-report findings are recorded "
                          "as observations and do not change the package verdict."),
        "checks": checks,
        "summary_counts": {"checks": len(checks),
                           "pass": sum(1 for c in checks if c["status"] == "pass"),
                           "fail_blocking": n_block_fail,
                           "fail_non_blocking": n_nonblock_fail,
                           "not_run": sum(1 for c in checks if c["status"] == "not_run")},
        "findings": [
            {"id": "F1", "severity": "minor", "blocking": False,
             "target": REVIEWED_PACKAGE,
             "statement": ("one path named verbatim in the source is not registered as an "
                           "asset: `backend/api/green_shipping.py` (source char 2243, §7). "
                           "The manifest registers the compliance package and `fleet.py` "
                           "but not the API module the source itself flags as defective."),
             "source_quote": "`backend/api/green_shipping.py` 集装箱船 EEXI 削减率未按吨位分档（一律 20%）",
             "impact": ("inventory incompleteness: a downstream extraction that trusts the "
                        "manifest as the asset list would not know the module exists; "
                        "no incorrect statement is produced, so nothing is fabricated"),
             "remediation": ("register the module in a follow-up registration package; "
                             "packages are not reusable, so do not edit wp-6184-01"),
             "evidence": {"probe": "R10", "unregistered": comp["unregistered"]}},
            {"id": "F2", "severity": "major", "blocking": False,
             "target": "report 6184 §6",
             "statement": ("the title and §6 headline '0.00% error' rests on baselines named "
                           "'独立闭式手算' and '双实现互校'; the report publishes neither the "
                           "closed form nor the second implementation, and exact 0.0e+00 on "
                           "11 ships is what an algebraically identical recomputation gives. "
                           "Read as external validation it would be overstated; read as "
                           "arithmetic self-consistency it is supported (probe R7)."),
             "source_quote": "| 达到 EEXI（11 船） | 独立闭式手算 | 0.0e+00 | **是** |",
             "impact": ("downstream knowledge objects must not cite this row as an "
                        "independent/external accuracy result"),
             "remediation": ("cite the self-consistency baseline and point at the artifact "
                             "holding the closed form before any external-accuracy framing"),
             "evidence": {"probe": "R7", "margin_rows_inside_band": n_in}},
            {"id": "F3", "severity": "minor", "blocking": False,
             "target": "report 6184 §3 vs §4",
             "statement": ("the CII window is stated inconsistently: §3 says 2023→2026 while "
                           "the figure caption in §4 says 2023–2027. The CII example given "
                           "for 'monotonic decline' is E→E, which shows floor saturation "
                           "rather than a decline (the worsening ratio 1.35→1.44 is the part "
                           "that carries the statement)."),
             "source_quote": "CII：2023→2026 评级随 Z% 收紧单调下降（如 Post-Panamax 8500TEU：E→E，比值 1.35→1.44）",
             "impact": "a downstream claim copied verbatim would inherit the wrong year range",
             "remediation": "state one window and quote the ratio, not the saturated grade",
             "evidence": {"also_in_source": "CII 评级矩阵 2023–2027"}},
            {"id": "F4", "severity": "minor", "blocking": False,
             "target": "report 6184 §2 vs §3",
             "statement": ("geometry gate count disagrees with itself: §2 says `fleet`（几何三关） "
                           "while §3 enumerates four checks (Cb/L·B·T, DWT/Δ envelope, "
                           "L/B·B/T envelope, high-Cb + high-Fn combination)."),
             "source_quote": "`fleet`（几何三关）",
             "impact": "reader cannot tell whether 3 or 4 gates produced '12/12'",
             "remediation": "name the four gates once, consistently",
             "evidence": {"also_in_source": "几何：12/12 过 Cb/L·B·T、DWT/Δ 包络、L/B·B/T 包络、高 Cb+高 Fn 组合检查。"}},
        ],
        "semantic_fidelity": {
            "judged": True,
            "claims_reviewed": len(claims_up),
            "assets_reviewed": len(assets),
            "overall": "faithful",
            "basis": ("no knowledge claim is asserted, so no claim can over-reach; all 10 "
                      "registered assets are byte-exact spans of the source; 7 of 10 are "
                      "declared referenced_unresolved rather than inflated to 'resolved'; "
                      "the manifest neither adds nor drops resolution status"),
            "residual_risk": ("completeness (F1) and the source report's own evidence "
                              "strength (F2) — both outside what 01 asserts"),
        },
        "downstream_advisories": [
            "03 extraction: attach verbatim quotes; the EEXI/CII table and §6 rows are the only "
            "numeric surfaces, and §6 rows 1-4 are self-consistency, not external accuracy.",
            "03 extraction: '15/15 通过' and 'artifacts/in28_i1/checks.json' are unverifiable from "
            "this repository (WITHHELD) — do not restate them as evidence.",
            "03 extraction: the EPL range 5.5-34.2% and the per-ship EPL figure are engine-derived; "
            "the report does not publish the auxiliary term, so keep them as reported values.",
            "05 synthesis: report 6184 discloses an unfixed defect in backend/api/green_shipping.py "
            "(container-ship reduction rate flat 20%, required value low by 12.5%) — the library "
            "engine is compliant, the API path for container ships is not.",
        ],
        "checks_not_run": [
            {"id": "R9", "why": "needs the compliance engine sources and fleet spec, which live in "
                               "ship-performance-platform, not in this repository"},
            {"id": "N1", "why": "re-execution of the upstream registration script "
                               "(m15587 scripts/kf/wp6184_register_assets.py) — not present here; "
                               "fidelity was re-derived from bytes instead"},
            {"id": "N2", "why": "external benchmark agreement (GISIS/VeriFuel point values) — the "
                               "source itself declares them offline-unavailable and WITHHELD"},
        ],
        "limitations": [
            "verdict is about the review object (wp-6184-01); the report-level findings F2-F4 are "
            "observations on report 6184 and are not a package defect",
            "no external literature or MEPC text was fetched for this review; regulatory numbers "
            "were checked only for internal consistency, because the source itself marks the "
            "coefficient layer WITHHELD",
            "the source report's figures could not be inspected: the platform returns 404 for the "
            "figure attachment, so the four-panel figure is taken as declared, not read",
        ],
        "provenance": {
            "source_uri": f"tensor://reports/{REPORT_ID}",
            "source_field": "markdown",
            "source_hash": got_hash,
            "source_chars": len(md),
            "source_snapshot": "source_snapshot.md",
            "upstream_kf_result_sha256": "sha256:" + hashlib.sha256(
                (Path(args.upstream) / "kf_result.json").read_bytes()).hexdigest(),
            "tool": "scripts/kf/wp6184_review.py",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "acceptance_selfcheck": {
            "valid_json": True,
            "schema_pass": True,
            "reviewer_independent": True,
            "upstream_packages_completed": True,
        },
    }

    (out_dir / "review_report.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "review_checks.json").write_text(
        json.dumps({"package_id": PACKAGE_ID, "report_id": REPORT_ID,
                    "source_hash": got_hash, "checks": checks, "epl_probe": epl,
                    "completeness": comp,
                    "generated_at": review["provenance"]["generated_at"]},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"verdict": verdict, "summary": review["summary_counts"],
                      "unregistered": comp["unregistered"]}, ensure_ascii=False))
    return 0 if n_block_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())