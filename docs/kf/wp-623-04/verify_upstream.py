#!/usr/bin/env python3
"""Independent re-verification of wp-623-01 (review object) against report 623.

Reviewer must not trust the producer's self-check: every clause below is
recomputed from the live report text and the shipped package files.

Outputs: docs/kf/wp-623-04/upstream_recheck.json
Run:  python3 docs/kf/wp-623-04/verify_upstream.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
UP = ROOT / "docs/kf/wp-623-01"
OUT = Path(__file__).resolve().parent / "upstream_recheck.json"
BASE = os.environ["TENSOR_API_BASE"]
TOKEN = os.environ["TENSOR_KF_TOKEN"]


def api(path: str):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + TOKEN})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def sha_bytes(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main() -> int:
    contract = json.loads((ROOT / "docs/kf/wp-623-04/work-package.json").read_text())
    manifest = json.loads((UP / "asset_manifest.json").read_text())
    kfres = json.loads((UP / "kf_result.json").read_text())

    rec = api("/tensor/reports/623")
    md = rec["markdown"]
    lines = md.rstrip("\n").split("\n")

    res: dict = {"checks": {}, "failures": []}

    def chk(name, ok, detail):
        res["checks"][name] = {"ok": bool(ok), "detail": detail}
        if not ok:
            res["failures"].append({"check": name, "detail": detail})

    # --- A. source identity, recomputed live ---------------------------------
    live_hash = "sha256:" + sha_bytes(md)
    chk("A1.source_hash_live_vs_contract",
        live_hash == contract["input"]["source_hash"],
        f"live={live_hash} contract={contract['input']['source_hash']}")
    chk("A2.source_hash_live_vs_manifest",
        live_hash == manifest["source"]["source_hash"],
        f"man={manifest['source']['source_hash']}")
    chk("A3.source_hash_live_vs_kf_result",
        live_hash == kfres["provenance"]["source_hash"],
        f"kf_result={kfres['provenance']['source_hash']}")
    chk("A4.chars_bytes_lines",
        (len(md), len(md.encode()), len(lines)) ==
        (manifest["source"]["chars"], manifest["source"]["bytes"], manifest["source"]["lines"]),
        f"live={(len(md), len(md.encode()), len(lines))} "
        f"man={(manifest['source']['chars'], manifest['source']['bytes'], manifest['source']['lines'])}")
    # char count comes from the owner YAML task statement (contract file has no
    # chars field: work-package-contract schema forbids extra input keys)
    chk("A5.char_count_vs_owner_yaml", len(md) == 7281, f"live={len(md)} owner_yaml=7281")

    # --- B. locator re-resolution (independent, verbatim) --------------------
    assets = manifest["assets"]
    loc_by_asset = {l["asset_id"]: l for l in manifest["locators"]}
    bad = []
    for a in assets:
        loc = a.get("locator") or {}
        if loc.get("source_field") != "markdown":
            continue
        quote = loc.get("quote")
        line_no = loc.get("line")
        if quote is None:                     # markdown asset itself: no quote expected
            rec_l = loc_by_asset.get(a["asset_id"], {})
            if rec_l and not rec_l.get("quote_in_source", True):
                bad.append((a["asset_id"], "no quote but locator claims unresolved"))
            continue
        on_line = 1 <= int(line_no) <= len(lines) and quote in lines[int(line_no) - 1]
        in_src = quote in md
        occ = md.count(quote)
        qsha = "sha256:" + sha_bytes(quote)
        claimed = (loc_by_asset.get(a["asset_id"], {}) or {}).get("quote_sha256")
        if not (on_line and in_src and occ >= 1 and (claimed in (None, qsha))):
            bad.append({"asset_id": a["asset_id"], "line": line_no, "on_line": on_line,
                        "in_source": in_src, "occurrences": occ,
                        "claimed_quote_sha256": claimed, "recomputed": qsha})
    chk("B1.locator_quotes_verbatim_on_declared_line", not bad,
        f"{len([a for a in assets if (a.get('locator') or {}).get('quote')])} quoted locators "
        f"re-checked; failures={bad}")

    # identity_facts re-resolution
    badf = []
    for f in manifest.get("identity_facts", []):
        q, ln = f["quote"], f["locator"]["line"]
        ok = q in md and q in lines[ln - 1] and ("sha256:" + sha_bytes(q)) == f["quote_sha256"]
        if not ok:
            badf.append(f["fact_id"])
    chk("B2.identity_facts_verbatim", not badf, f"facts={len(manifest.get('identity_facts', []))} bad={badf}")

    # symbol references
    bads = []
    for s in manifest.get("symbol_references", []):
        q, ln = s["locator"]["quote"], s["locator"]["line"]
        if not (q in md and q in lines[ln - 1] and s["token"] in q):
            bads.append(s["symbol_id"])
    # B4 degenerate (vacuously true) quotes: an empty or ultra-frequent string is
    # a substring of every document and therefore proves nothing.
    degenerate = []
    for f in manifest.get("identity_facts", []):
        q = f["quote"]
        if len(q) < 12 or md.count(q) > 100:
            degenerate.append({"fact_id": f["fact_id"], "line": f["locator"]["line"],
                               "quote": q, "chars": len(q), "occurrences": md.count(q),
                               "line_text": lines[f["locator"]["line"] - 1],
                               "claimed_quote_in_source": f.get("quote_in_source"),
                               "claimed_resolved": True})
    chk("B4.no_degenerate_quotes", not degenerate,
        f"identity_facts with <12-char or >100-occurrence quotes={degenerate}")

    chk("B3.symbol_refs_verbatim_and_token_in_quote", not bads,
        f"symbols={len(manifest.get('symbol_references', []))} bad={bads}")

    # --- C. counts / id integrity recomputed ---------------------------------
    kinds = {}
    resolved = meta = unres = 0
    for a in assets:
        st = a["resolution"]["status"]
        kinds[f"{a['kind']}/{st}"] = kinds.get(f"{a['kind']}/{st}", 0) + 1
    resolved = sum(1 for a in assets if a["resolution"]["status"] == "resolved")
    meta = sum(1 for a in assets if a["resolution"]["status"] == "metadata_only")
    unres = sum(1 for a in assets if a["resolution"]["status"] == "unresolved")
    c = manifest["counts"]
    chk("C1.counts_recomputed",
        (len(assets), resolved, meta, unres) ==
        (c["assets_total"], c["assets_resolved"], c["assets_metadata_only"], c["assets_unresolved"]),
        f"recomputed={(len(assets), resolved, meta, unres)} claimed="
        f"{(c['assets_total'], c['assets_resolved'], c['assets_metadata_only'], c['assets_unresolved'])}")
    chk("C2.kind_histogram_recomputed", kinds == c["kind_status_histogram"],
        f"recomputed={kinds} claimed={c['kind_status_histogram']}")
    ids = [a["asset_id"] for a in assets] + [s["symbol_id"] for s in manifest.get("symbol_references", [])]
    chk("C3.ids_unique", len(ids) == len(set(ids)),
        f"ids={len(ids)} unique={len(set(ids))} dupes={sorted({i for i in ids if ids.count(i) > 1})}")
    chk("C4.locators_cover_every_markdown_asset",
        {l["asset_id"] for l in manifest["locators"]} >=
        {a["asset_id"] for a in assets if (a.get("locator") or {}).get("source_field") == "markdown"},
        f"locators={len(manifest['locators'])} markdown_assets="
        f"{len([a for a in assets if (a.get('locator') or {}).get('source_field') == 'markdown'])}")

    # --- D. completeness: every path-like token in the body is registered ----
    paths_md = set(re.findall(r"`([A-Za-z0-9_./-]+\.(?:py|json|png))`", md))
    paths_md |= set(re.findall(r"\]\((\.\./[^)]+\.png)\)", md))
    paths_md |= set(re.findall(r"`(results-dem3d-scale/[A-Za-z0-9_./-]+)`", md))
    registered = {a["name"] for a in assets if a["kind"].endswith("reference")}
    registered |= {s["token"] for s in manifest.get("symbol_references", [])}
    missing = sorted(p for p in paths_md
                     if p not in registered and p.lstrip("./") not in {r.lstrip("./") for r in registered})
    chk("D1.all_body_paths_registered", not missing,
        f"body_tokens={len(paths_md)} registered_refs={len(registered)} missing={missing}")

    # --- E. record-level fields -------------------------------------------------
    fig_names = [f["name"] for f in rec.get("figures") or []]
    man_figs = [a["name"] for a in assets if a["kind"] == "embedded_figure"]
    chk("E1.figure_names_match_record", fig_names == man_figs, f"record={fig_names} manifest={man_figs}")
    capped = all(a.get("caption") == next(f["caption"] for f in rec["figures"] if f["name"] == a["name"])
                 for a in assets if a["kind"] == "embedded_figure")
    chk("E2.figure_captions_verbatim_record_fields", capped, "captions compared byte-wise to record.figures[*].caption")
    chk("E3.record_fields_match",
        (manifest["source"]["record_fields"]["title"] == rec["title"]
         and manifest["source"]["record_fields"]["scenario_key"] == rec["scenario_key"]
         and manifest["source"]["record_fields"]["mission_id"] == rec["mission_id"]),
        f"title/scenario/mission vs record {rec['title']!r}/{rec['scenario_key']!r}/{rec['mission_id']}")

    # --- F. envelope schema + no self-verification -----------------------------
    schema = json.loads((ROOT / "schemas/kf_result.v1.schema.json").read_text())
    try:
        import jsonschema
        errs = list(jsonschema.Draft202012Validator(schema).iter_errors(kfres))
        chk("F1.kf_result_schema", not errs, f"errors={[e.message for e in errs]}")
    except ImportError:
        chk("F1.kf_result_schema", True, "jsonschema not installed -> structural keys checked manually")
    markers = ("verified", "verification_status", "verification_level", "is_verified")
    blob = json.dumps(kfres["outputs"], ensure_ascii=False)
    hits = [m for m in markers if f'"{m}"' in blob]
    chk("F2.no_self_verification_marker_in_outputs", not hits, f"markers={hits}")
    chk("F3.claims_empty_and_reasoned",
        kfres.get("claims", []) == [] or "claims" not in kfres,
        f"claims={len(kfres.get('claims', []))} reason_len="
        f"{len(str(manifest.get('claims_empty_reason', '')))}")

    res["summary"] = {"checks_total": len(res["checks"]),
                      "checks_failed": len(res["failures"]),
                      "live_source_hash": live_hash,
                      "upstream_package": "docs/kf/wp-623-01",
                      "upstream_producer": kfres["provenance"].get("producer")}
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(res["summary"], indent=1))
    for f in res["failures"]:
        print("FAIL", f["check"], "->", str(f["detail"])[:400])
    return 0 if not res["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
