#!/usr/bin/env python3
"""KF wp-12563-01 (01-asset-registration) for report_id=12563.

One-command re-run:
    python3 scripts/kf_wp12563_01_register.py

What it does (and nothing else):
  1. Logs in to the platform API, GET /tensor/reports/12563, takes the
     `markdown` field (the only source field this package may use).
  2. Recomputes sha256 over the UTF-8 bytes of that field and compares it
     with the contract-declared source_hash; also compares char count with
     the contract-declared `chars`.
  3. Registers the source asset plus every figure / code / data / table /
     block reference that is *named in the report markdown itself*.
     Every asset carries a verbatim quote whose character span and line
     span are computed from the fetched markdown (zero hand-typed offsets).
  4. Emits docs/kf/wp-12563-01/{asset_manifest.json,kf_result.json,
     locator_check.json,sha256.txt,source.md}.

No extraction, no classification, no claim generation: `claims` is an
empty array by contract (objective.classify_report_type=false).
Nothing here is marked verified; verification belongs to the platform gate.
"""
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

API_BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
USER = os.environ.get("TENSOR_AGENT_USER", "")
PASS = os.environ.get("TENSOR_AGENT_PASS", "")

PACKAGE_ID = "wp-12563-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "12563"
CONTRACT_SOURCE_HASH = "sha256:e6097b4c6c824f48a253303de23e66a9a1c16f0fdcbcf163683158e3bd5cd816"
CONTRACT_CHARS = 15874
CONTRACT_TITLE = ("P156W2-N03 · D3Q27 高阶格子恢复：死枚举审计 + 三维 Poiseuille "
                  "解析锚 + Stokes 球体阻力")
CONTRACT_SCENARIO_KEY = "lbm_d3q27_poiseuille_stokes"
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "docs", "kf", PACKAGE_ID)


def http_json(method, path, body=None, token=None):
    req = urllib.request.Request(API_BASE + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(req, data=data, timeout=60) as r:
        return json.loads(r.read().decode())


def fetch_report():
    login = http_json("POST", "/auth/login",
                      {"username": USER, "password": PASS})
    token = login["access_token"]
    return http_json("GET", "/tensor/reports/" + REPORT_ID, token=token)


def span_of(md, quote):
    """Return (start_char, end_char, start_line, end_line, occurrences) for a
    verbatim quote; raises if the quote is not found."""
    idx = md.find(quote)
    if idx < 0:
        raise ValueError("quote not found verbatim in markdown: %r" % quote[:80])
    occ = md.count(quote)
    start_line = md.count("\n", 0, idx) + 1
    end_line = md.count("\n", 0, idx + len(quote)) + 1
    return idx, idx + len(quote), start_line, end_line, occ


def main():
    rec = fetch_report()
    md = rec["markdown"]
    sha = hashlib.sha256(md.encode("utf-8")).hexdigest()
    chars = len(md)
    if "sha256:" + sha != CONTRACT_SOURCE_HASH:
        sys.exit("HASH MISMATCH: recomputed %s != contract %s"
                  % (sha, CONTRACT_SOURCE_HASH))
    if chars != CONTRACT_CHARS:
        sys.exit("CHARS MISMATCH: %d != contract %d" % (chars, CONTRACT_CHARS))
    if rec["title"] != CONTRACT_TITLE:
        sys.exit("TITLE MISMATCH: %r" % rec["title"])
    if rec["scenario_key"] != CONTRACT_SCENARIO_KEY:
        sys.exit("SCENARIO_KEY MISMATCH: %r" % rec["scenario_key"])

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "source.md"), "w", encoding="utf-8") as f:
        f.write(md)
    with open(os.path.join(OUT_DIR, "sha256.txt"), "w") as f:
        f.write(sha + "  source.md (markdown field of report 12563, utf-8)\n")

    # ---- asset definitions: (asset_id, class, label, section, quote, note)
    # Every quote must be a verbatim substring of the fetched markdown.
    A = [
        ("A01", "source_text", "report markdown (whole record)",
         "whole document",
         md,  # whole-document locator, handled specially below
         "The registered source asset itself; bytes = markdown field of the "
         "platform record, hashed in this package."),
        ("A02", "figure", "figures/p156w2_n03_poiseuille.png",
         "section 4 Figures",
         "`figures/p156w2_n03_poiseuille.png` — (left) steady velocity profiles vs the",
         "PNG bytes are not part of the report record (figures carry name+caption "
         "only); declared in markdown section 4 and in the platform figures[0] record."),
        ("A03", "figure", "figures/p156w2_n03_stokes_sphere.png",
         "section 4 Figures",
         "`figures/p156w2_n03_stokes_sphere.png` — (left) `K` vs `a/L` against the",
         "PNG bytes not in the report record; declared in markdown section 4 and "
         "platform figures[1] record."),
        ("A04", "figure", "figures/p156w2_n03_sphere_resolution.png",
         "section 4 Figures",
         "`figures/p156w2_n03_sphere_resolution.png` — drag error vs sphere",
         "PNG bytes not in the report record; declared in markdown section 4 and "
         "platform figures[2] record."),
        ("A05", "code", "src/tensorlbm/d3q27_recovery.py",
         "section 2 What was done",
         "New module `src/tensorlbm/d3q27_recovery.py`:",
         "New TensorLBM module (moment audits, D3Q27Stepper, Poiseuille/Stokes "
         "runners, viscosity gate). File lives in the TensorLBM repo, not in the "
         "report record; no artifact endpoint serves it."),
        ("A06", "code", "benchmarks/frontier/p156w2_n03_d3q27_recovery/run.py",
         "section 2 Reproduce",
         "R=benchmarks/frontier/p156w2_n03_d3q27_recovery/run.py",
         "Benchmark driver with subcommands audit/viscosity/poiseuille/sphere/"
         "stability/merge/plot; per-subcommand output file names are not "
         "individually named in the report (only the --out directory)."),
        ("A07", "code", "benchmarks/frontier/p156w2_n03_d3q27_recovery/make_report.py",
         "section 2 Reproduce",
         "python benchmarks/frontier/p156w2_n03_d3q27_recovery/make_report.py",
         "Report generator; also named in the report header line 4."),
        ("A08", "data", "artifacts/p156w2_n03_d3q27_recovery/report_data.json",
         "report header (line 4)",
         "*Generated from `artifacts/p156w2_n03_d3q27_recovery/report_data.json` by `benchmarks/frontier/p156w2_n03_d3q27_recovery/make_report.py`*",
         "Merged result data the report is generated from; not part of the report "
         "record, no artifact endpoint serves it."),
        ("A09", "data", "viscosity_gate.json",
         "section 1.1 viscosity gate",
         "the table above is emitted as `viscosity_gate.json`.",
         "Emitted artifact of the viscosity-gate run; directory implied by the "
         "Reproduce block (--out artifacts/p156w2_n03_d3q27_recovery)."),
        ("A10", "code", "unit test pinning the wall position (file not named)",
         "section 2 implementation detail 1",
         "a unit test pins the wall position.",
         "Report states a unit test exists but does not name the file; registered "
         "as declared-only with the statement as locator."),
        ("A11", "code_pointer", "TensorLBM @ 7efbcfc0808b (branch agent/m10870)",
         "report header (line 6)",
         "*Repo `TensorLBM` @ `7efbcfc0808b` (branch `agent/m10870`), torch 2.7.1 · loongarch64 · 128 cores · generated 2026-11-10T21:43:08Z*",
         "Repo identity of all code assets above; short commit prefix as printed "
         "in the report (full 40-hex sha not stated in the report)."),
        ("A12", "block", "Reproduce command block (fenced, 10 commands)",
         "section 2 Reproduce",
         "R=benchmarks/frontier/p156w2_n03_d3q27_recovery/run.py",
         "First line of the fenced reproduce block; the block also ends with the "
         "make_report.py invocation (asset A07)."),
        ("A13", "block", "Poiseuille analytic profile formula (fenced)",
         "section 1 Anchor 2",
         "u(y) = F / (2 rho nu) · y (H − y),      nu = (tau − 1/2) c_s²",
         "Fenced formula block; the exact anchor the channel runs are compared to."),
        ("A14", "table", "section 1 parameter table",
         "section 1",
         "| Parameter | Value |",
         "Case parameter table (lattice, collision, walls, precision, gaps, taus, "
         "resolutions, box factors, Reynolds targets)."),
        ("A15", "table", "section 1.1 viscosity-gate table",
         "section 1.1",
         "| tau | nu (formula) | max deviation of `nu_eff` over the boxes tested |",
         "tau vs formula nu vs max nu_eff deviation (4.268 % / 12.252 % / 83.362 %)."),
        ("A16", "table", "section 2 component table of d3q27_recovery.py",
         "section 2",
         "| Component | Purpose |",
         "Nine components of the new module (moment_audit ... run_long_stability)."),
        ("A17", "table", "section 3.1 lattice-algebra table",
         "section 3.1",
         "| Quantity | Value | Criterion |",
         "Exact lattice-algebra residuals (rank-1..rank-6) with criteria."),
        ("A18", "table", "section 3.2 third-moment table",
         "section 3.2",
         "| Form | Residual |",
         "Third-moment residuals vs truncated and full Maxwellian."),
        ("A19", "table", "section 3.3 Poiseuille anchor table",
         "section 3.3",
         "| H | tau | nu | u_max (LBM) | u_max (exact) | rel. L2 | rel. Linf | wall-force balance | steps |",
         "Five channel runs incl. the tau=3.0 viscosity-gate cross-check row."),
        ("A20", "table", "section 3.3 nu_eff normalisation table",
         "section 3.3",
         "| H | tau | nu_eff/nu − 1 | rel. L2 vs formula-nu | rel. L2 vs nu_eff |",
         "Shows error vs formula-nu grows with tau while error vs nu_eff stays small."),
        ("A21", "table", "section 3.4 resolution-study table",
         "section 3.4",
         "| D | box | a/L | Re | K (measured) | K_Hasimoto | err vs Hasimoto | err vs Stokes | momentum balance | steps |",
         "Staircase-sphere resolution study (D = 8, 12; L/D = 3; Re ~ 0.1)."),
        ("A22", "table", "section 3.4 box (confinement) study table",
         "section 3.4",
         "| a/L | K measured | K_Hasimoto | ratio |",
         "Two blockages; measured confinement ratio 0.8628 vs Hasimoto 0.8363."),
        ("A23", "table", "section 3.4 Reynolds-sweep table",
         "section 3.4",
         "| Re (achieved) | C_D | 24/Re (Stokes) | C_D Re/24 | Oseen `1+3Re/16` | err vs Stokes | err vs Oseen | err vs Schiller–Naumann |",
         "Single achieved point Re = 1.294; report marks it trend evidence only."),
        ("A24", "table", "section 6 error-judgement table",
         "section 6",
         "| Quantity | Reference | Error | < 3 %? |",
         "Per-quantity error judgement with explicit <3% answers (one NO row: "
         "sphere drag vs Hasimoto 7.592 %)."),
        ("A25", "table", "section 6.1 honest-FAIL / not-attained table",
         "section 6.1",
         "| Campaign criterion | Status | Evidence |",
         "Campaign-criterion status table incl. the two NOT MET / NOT PHYSICALLY "
         "ATTAINABLE rows."),
    ]

    assets = []
    locator_check = []
    seen_ids = set()
    for aid, cls, label, section, quote, note in A:
        if aid in seen_ids:
            sys.exit("duplicate asset_id %s" % aid)
        seen_ids.add(aid)
        if quote is md:  # whole-document source asset
            start, end = 0, len(md)
            sl, el = 1, md.count("\n") + 1
            occ = 1
            method = "document"
        else:
            start, end, sl, el, occ = span_of(md, quote)
            method = "char_span"
        assets.append({
            "asset_id": aid,
            "asset_class": cls,
            "label": label,
            "in_report_section": section,
            "locator": {
                "method": method,
                "start_char": start,
                "end_char": end,
                "start_line": sl,
                "end_line": el,
                "quote": quote if quote is not md else md[:120] + " ... [whole document, %d chars]" % len(md),
                "unique": occ == 1,
                "occurrences": occ,
            },
            "resolution": "resolved_in_source" if cls == "source_text" else "referenced_unresolved",
            "resolution_check": {
                "check": "quote is a verbatim substring of the fetched markdown; "
                         "span/line computed from that fetch" if cls != "source_text"
                         else "whole markdown field of the platform record, hashed",
                "result": "resolved" if cls == "source_text" else "unresolved",
            },
            "note": note,
        })
        locator_check.append({
            "asset_id": aid,
            "quote_head": (quote if quote is not md else md)[:100],
            "found": True,
            "occurrences": occ,
            "start_char": start,
            "end_char": end,
            "start_line": sl,
            "end_line": el,
            "unique": occ == 1,
        })

    n_resolved = sum(1 for a in assets if a["resolution"] == "resolved_in_source")
    n_unresolved = len(assets) - n_resolved
    by_class = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1

    manifest = {
        "manifest_version": "1.0",
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "contract_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": "scripts/kf_wp12563_01_register.py",
        "provenance": {
            "source_uri": "tensor://reports/12563",
            "source_field": "markdown",
            "fetched_via": "GET /api/v1/tensor/reports/12563 (Bearer)",
            "hash_algo": "sha256",
            "hashed_bytes": "markdown field encoded as utf-8",
            "source_hash": "sha256:" + sha,
            "source_hash_expected": CONTRACT_SOURCE_HASH,
            "source_hash_matches": True,
            "source_chars": chars,
            "source_bytes_utf8": len(md.encode("utf-8")),
            "chars_expected": CONTRACT_CHARS,
            "chars_matches": True,
            "chars_semantics": "contract `chars` = python str length (code points); "
                             "utf-8 byte length differs (CJK title/tags)",
            "record_identity": {
                "id": rec["id"],
                "title": rec["title"],
                "scenario_key": rec["scenario_key"],
                "mission_id": rec["mission_id"],
                "status": rec["status"],
                "created_at": rec["created_at"],
                "created_by": rec["created_by"],
                "tags": rec["tags"],
                "figure_records": len(rec["figures"]),
            },
            "title_matches_contract": rec["title"] == CONTRACT_TITLE,
            "scenario_key_matches_contract": rec["scenario_key"] == CONTRACT_SCENARIO_KEY,
        },
        "identity_granularity": "asset-level: one id per distinct reference named in "
                              "the report markdown (figure path, code path, data path, "
                              "inline table, fenced block); the source markdown itself "
                              "is one document-level asset.",
        "resolution_status_vocabulary": {
            "resolved_in_source": "asset bytes are the registered markdown itself (A01 only)",
            "referenced_unresolved": "path/quote resolved verbatim in the registered "
                                    "markdown; the file itself is not part of the report "
                                    "record and no artifact endpoint serves it",
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": {
                "resolved_in_source": n_resolved,
                "referenced_unresolved": n_unresolved,
            },
        },
        "assets": assets,
        "claims": [],
        "claims_note": "claims intentionally empty: task_type 01-asset-registration "
                        "registers source assets only (objective.classify_report_type=false, "
                        "no extraction). Nothing is marked verified; verification is "
                        "computed by the platform gate.",
        "integrity": {
            "quote_uniqueness": "each non-document quote's occurrence count recorded in "
                                "locator.occurrences; no quote is a substring of another "
                                "registered quote's span except A12/A07 sharing the "
                                "reproduce block (distinct spans)",
            "hash_recomputed_locally": True,
            "hash_matches_contract": True,
        },
    }

    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + sha,
            "source_field": "markdown",
            "producer": "agent/m15748",
            "emitted_at": manifest["generated_at"],
            "notes": "source_hash recomputed with hashlib.sha256 over the UTF-8 bytes "
                     "of the markdown field fetched from GET /api/v1/tensor/reports/12563; "
                     "matches the contract hash. Hash equality is a mechanical identity "
                     "check only - no claim in this package is marked verified.",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }

    with open(os.path.join(OUT_DIR, "asset_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(os.path.join(OUT_DIR, "kf_result.json"), "w", encoding="utf-8") as f:
        json.dump(envelope, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(os.path.join(OUT_DIR, "locator_check.json"), "w", encoding="utf-8") as f:
        json.dump({"package_id": PACKAGE_ID, "report_id": REPORT_ID,
                   "source_hash": "sha256:" + sha,
                   "locators": locator_check}, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # schema validation of the envelope (draft 2020-12)
    try:
        import jsonschema
        schema = json.load(open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "schemas", "kf_result.v1.schema.json")))
        jsonschema.validate(envelope, schema)
        print("schema validation: PASS (jsonschema, kf_result.v1.schema.json)")
    except ImportError:
        print("schema validation: SKIPPED (jsonschema not installed)")

    print("assets:", len(assets), "by_class:", by_class)
    print("sha256:", sha)
    print("chars:", chars)
    print("OK: wrote", OUT_DIR)


if __name__ == "__main__":
    main()
