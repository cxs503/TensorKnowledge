#!/usr/bin/env python3
"""Independent red-team checks for wp-5760-04: audit the wp-5760-01 asset manifest.

Re-implements every check from scratch against the live source bytes; imports no
producer code. Writes a machine-readable result bundle.

Usage:
  python3 scripts/kf/review_wp5760_04_checks.py <manifest.json> <report_5760.md> <out.json>
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import sys
import urllib.request

CONTRACT_HASH = "sha256:95a6ffec44f492fe4f7f39f8d6bb989d845f6a781cd5749197177b6c05308bfe"
CONTRACT_CHARS = 6808


def fetch_report(report_id: str) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        method="POST")
    req.add_header("Content-Type", "application/json")
    tok = json.loads(urllib.request.urlopen(req, timeout=60).read())["access_token"]
    r = urllib.request.Request(base + "/tensor/reports/" + report_id)
    r.add_header("Authorization", "Bearer " + tok)
    return json.loads(urllib.request.urlopen(r, timeout=60).read())


def line_starts(md: str) -> list[int]:
    starts, off = [0], 0
    for ln in md.split("\n")[:-1]:
        off += len(ln) + 1
        starts.append(off)
    return starts


def line_of(starts: list[int], char: int) -> int:
    lo, hi = 0, len(starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if starts[mid] <= char:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


def norm_quote(q: str) -> str:
    return q[:-1] if q.endswith("…") else q


def count_tables(md: str) -> int:
    """A table = maximal run of lines whose first non-space char is '|'."""
    blocks, prev = 0, False
    for ln in md.split("\n"):
        cur = ln.lstrip().startswith("|")
        if cur and not prev:
            blocks += 1
        prev = cur
    return blocks


def count_sections(md: str) -> int:
    return len([ln for ln in md.split("\n") if re.match(r"^#{2,3} ", ln)])


def main() -> None:
    manifest_path, md_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    manifest = json.load(open(manifest_path, encoding="utf-8"))
    md_file = open(md_path, encoding="utf-8").read()
    rec = fetch_report("5760")
    md_live = rec["markdown"]
    raw = md_live.encode("utf-8")
    live_hash = "sha256:" + hashlib.sha256(raw).hexdigest()
    starts = line_starts(md_live)

    checks: list[dict] = []

    def add(cid: str, ok, claim: str, observed, blocking: bool = False):
        checks.append({"id": cid, "ok": bool(ok), "claim_audited": claim,
                       "observed": observed, "blocking": blocking})

    # C1 identity: live bytes == contract bytes == snapshot used by manifest
    add("C1.source_identity",
        live_hash == CONTRACT_HASH and len(md_live) == CONTRACT_CHARS
        and md_file == md_live,
        "source hash/chars match contract; manifest built on identical bytes",
        {"live_hash": live_hash, "contract_hash": CONTRACT_HASH,
         "live_chars": len(md_live), "live_bytes": len(raw),
         "snapshot_identical_to_live": md_file == md_live}, blocking=True)

    # C2 delivered manifest bytes == declared sha256/size
    mbytes = open(manifest_path, "rb").read()
    decl = manifest.get("outputs") or {}
    kf = json.load(open(os.path.join(os.path.dirname(manifest_path), "kf_result.json"),
                        encoding="utf-8"))
    decl_out = (kf.get("outputs") or {}).get("asset_manifest.json") or {}
    add("C2.manifest_bytes",
        hashlib.sha256(mbytes).hexdigest() == decl_out.get("sha256")
        and len(mbytes) == decl_out.get("bytes"),
        "envelope declares manifest sha256/bytes",
        {"recomputed_sha256": hashlib.sha256(mbytes).hexdigest(),
         "declared_sha256": decl_out.get("sha256"),
         "recomputed_bytes": len(mbytes), "declared_bytes": decl_out.get("bytes")},
        blocking=True)

    assets = manifest["assets"]
    ids = [a["asset_id"] for a in assets]

    # C3 id discipline
    add("C3.id_uniqueness", len(ids) == len(set(ids)) and ids == [f"A{i:02d}" for i in
                                                                range(1, len(ids) + 1)],
        "52 distinct, gapless ids",
        {"n": len(ids), "distinct": len(set(ids)), "first": ids[:3], "last": ids[-1:]},
        blocking=True)

    # C4 locator exactness: md[start:end] must equal the stored quote (modulo '…')
    bad_span, bad_line, bad_len, oob = [], [], [], []
    for a in assets:
        loc = a.get("locator") or {}
        s, e, q = loc.get("start_char"), loc.get("end_char"), loc.get("quote") or ""
        if not isinstance(s, int) or not isinstance(e, int) or not (0 <= s < e <= len(md_live)):
            oob.append(a["asset_id"])
            continue
        seg = md_live[s:e]
        if seg != q:
            if norm_quote(q) and seg.startswith(norm_quote(q)):
                if len(seg) != e - s:
                    bad_len.append(a["asset_id"])
            else:
                bad_span.append({"id": a["asset_id"], "seg": seg[:60], "quote": q[:60]})
        if loc.get("start_line") is not None and line_of(starts, s) != loc["start_line"]:
            bad_line.append({"id": a["asset_id"], "declared": loc["start_line"],
                             "actual": line_of(starts, s)})
    add("C4.locator_chars",
        not (bad_span or oob),
        "every locator quote is the verbatim md[start:end] slice",
        {"checked": len(assets), "mismatch": bad_span, "out_of_bounds": oob},
        blocking=True)
    add("C5.locator_lines", not bad_line,
        "every locator start_line equals the recomputed line of start_char",
        {"checked": len(assets), "mismatch": bad_line}, blocking=True)
    add("C6.locator_lengths", not bad_len,
        "span length end-start equals quote length (no silent truncation)",
        {"truncated_quotes": len([a for a in assets
                                  if str((a.get("locator") or {}).get("quote", "")).endswith("…")]),
         "length_mismatch": bad_len})

    # C7 counts self-consistency, recomputed from the asset array
    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    dc = manifest["counts"]
    add("C7.counts_recomputed",
        by_class == dc["by_class"] and by_res == dc["by_resolution"]
        and dc["assets"] == len(assets),
        "counts.by_class / by_resolution reproduced from the asset array",
        {"by_class": by_class, "by_resolution": by_res, "declared": dc},
        blocking=True)

    # C8 resolution honesty: resolved_in_source must have in-document bytes;
    # referenced_unresolved must never be dressed as verified
    res_bad = [a["asset_id"] for a in assets if a["asset_class"] == "source_document"
               and a["resolution"] != "resolved_in_source"]
    verified_marks = [a["asset_id"] for a in assets
                      if a.get("resolution") == "verified" or a.get("verified") is True]
    add("C8.resolution_enum",
        not res_bad and not verified_marks,
        "no asset marked verified locally; source_document resolved",
        {"source_document_bad": res_bad, "verified_marks": verified_marks,
         "claims_len": len(manifest.get("claims") or [])})

    # C9 coverage: independent recount of headings / tables / images
    indep = {"sections_h2_h3": count_sections(md_live), "tables": count_tables(md_live),
             "inline_images": len(re.findall(r"!\[[^\]]*\]\([^)]+\)", md_live))}
    add("C9.coverage_recount",
        indep["sections_h2_h3"] == by_class.get("section", 0)
        and indep["tables"] == by_class.get("table", 0)
        and indep["inline_images"] == by_class.get("figure_reference", 0),
        "section/table/image counts reproduced by an independent rule",
        {"independent": indep, "manifest": {"section": by_class.get("section"),
                                            "table": by_class.get("table"),
                                            "figure_reference": by_class.get("figure_reference")}},
        blocking=True)

    # C10 figure claim: 'figures carry name+caption but no png_base64'
    figs = rec.get("figures") or []
    fig_names = [f.get("name") for f in figs] if isinstance(figs, list) else []
    has_b64 = [f.get("name") for f in figs
               if isinstance(f, dict) and bool(f.get("png_base64"))]
    fig_assets = [a for a in assets if a["asset_class"] in ("figure_reference", "figure_metadata")]
    add("C10.figure_absence_claim",
        not has_b64,
        "platform figures[] carries no png_base64 (basis for declared_absent)",
        {"figures_entries": len(figs), "names": fig_names, "with_png_base64": has_b64,
         "figure_assets": [{"id": a["asset_id"], "class": a["asset_class"],
                            "resolution": a["resolution"]} for a in fig_assets]})

    # C11 the quote-uniqueness ledger (non_unique list) reproduced
    quotes = [norm_quote((a.get("locator") or {}).get("quote", "")) for a in assets]
    nonuniq = [assets[i]["asset_id"] for i, q in enumerate(quotes)
               if q and md_live.count(q) > 1]
    declared_nonuniq = manifest["integrity"]["quote_uniqueness"]["non_unique_assets"]
    add("C11.quote_uniqueness",
        nonuniq == declared_nonuniq
        and manifest["integrity"]["quote_uniqueness"]["unique"] == len(assets) - len(nonuniq),
        "non-unique quote ledger reproduced (occurrence-level ids, not duplicates)",
        {"recomputed_non_unique": nonuniq, "declared_non_unique": declared_nonuniq,
         "recomputed_unique": len(assets) - len(nonuniq)})

    # C12 scope: every locator belongs to report 5760's own bytes only
    add("C12.scope_single_report",
        manifest.get("report_id") == "5760"
        and str((manifest.get("source") or {}).get("uri", "")).endswith("/5760")
        and (manifest.get("source") or {}).get("hash") == live_hash.replace("sha256:", ""),
        "manifest bound to report 5760 only, source hash = live bytes",
        {"report_id": manifest.get("report_id"),
         "source_uri": (manifest.get("source") or {}).get("uri"),
         "source_hash": (manifest.get("source") or {}).get("hash") == live_hash.replace(
             "sha256:", "")})

    # C13 the report's own claim that schemas/kf_result.v1.schema.json is absent
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    schema_p = os.path.join(repo_root, "schemas", "kf_result.v1.schema.json")
    add("C13.schema_absence_claim",
        not os.path.isfile(schema_p),
        "reported limitation: 'schemas/kf_result.v1.schema.json absent in repo'",
        {"path": "schemas/kf_result.v1.schema.json", "exists": os.path.isfile(schema_p),
         "size": os.path.getsize(schema_p) if os.path.isfile(schema_p) else None})

    # C14 the 11 sampled locators printed in the producer report table re-resolve
    ko = open(os.path.join(os.path.dirname(out_path), "upstream_wp-5760-01_report_14662.md"),
              encoding="utf-8").read()
    rej, checked = [], 0
    for ln in ko.split("\n"):
        m = re.match(r"^\| (A\d\d) \| .*? \| chars (\d+)–(\d+) / lines (\d+)–(\d+) \|$", ln)
        if m:
            checked += 1
            aid, s, e, sl = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
            if not (0 <= s < e <= len(md_live)) or line_of(starts, s) != sl:
                rej.append({"id": aid, "s": s, "e": e, "declared_line": sl})
    add("C14.report_table_spans", not rej and checked >= 10,
        "the char/line locators printed in the producer report resolve on live bytes",
        {"rows_checked": checked, "rejected": rej})


    # C15 would the repo schema have caught the envelope? validates producer kf_result.json
    try:
        import jsonschema
        sch = json.load(open(schema_p, encoding="utf-8")) if os.path.isfile(schema_p) else None
        errs = None
        producer_env = os.path.join(os.path.dirname(manifest_path), "kf_result.json")
        if sch is not None and os.path.isfile(producer_env):
            try:
                jsonschema.validate(json.load(open(producer_env, encoding="utf-8")), sch)
                errs = []
            except jsonschema.ValidationError as exc:  # pragma: no cover
                errs = [str(exc.message)[:200]]
        add("C15.repo_schema_available", sch is not None and errs == [],
            "repo envelope schema exists and the producer envelope validates against it",
            {"schema_present": sch is not None, "validation_errors": errs})
    except ImportError:  # pragma: no cover
        add("C15.repo_schema_available", None, "jsonschema unavailable", "not_run")

    # C16 omission probe: every extension-bearing path token in the source must be
    # covered by the manifest's path_reference set (independent regex, different rule)
    toks = set(re.findall(r"[A-Za-z0-9_./{},\-]+\.(?:py|json|service|md|png|sql|yaml|yml|toml)",
                          md_live))
    registered = {a.get("path_reference") for a in assets if a.get("path_reference")}
    missing = sorted(t for t in toks if t not in registered)
    add("C16.no_omitted_path_tokens", not missing,
        "no extension-bearing path token in the source is left unregistered",
        {"distinct_tokens": len(toks), "missing_from_manifest": missing},
        blocking=True)

    # C17 distinct path accounting: file tokens + directory refs == declared distinct
    dirs = sorted({a.get("path_reference") for a in assets
                   if a["asset_class"] == "artifact_directory_reference"})
    add("C17.distinct_path_accounting",
        len(toks) + len(dirs) == dc.get("distinct_referenced_paths"),
        "distinct_referenced_paths reproduced as file tokens + directory refs",
        {"file_tokens": len(toks), "directory_refs": len(dirs),
         "sum": len(toks) + len(dirs),
         "declared": dc.get("distinct_referenced_paths")})

    # C18 producer's stated reason for deriving its own schema (repo v1 const)
    rep = os.path.join(repo_root, "schemas", "asset_manifest.v1.schema.json")
    const_pkg = None
    if os.path.isfile(rep):
        txt = open(rep, encoding="utf-8").read()
        m = re.search(r'"package_id":\s*\{\s*"const":\s*"([^"]+)"', txt)
        const_pkg = m.group(1) if m else None
    add("C18.repo_v1_const", const_pkg == "wp-448-01",
        "reported limitation: repo asset_manifest.v1 hardcodes package_id=wp-448-01",
        {"repo_schema_package_id_const": const_pkg})


    # C19 slice invariant: does quote == md[start_char:end_char] for every asset?
    exact, prefix_only = [], []
    for a in assets:
        loc = a.get("locator") or {}
        s_, e_ = loc.get("start_char"), loc.get("end_char")
        q = loc.get("quote") or ""
        if isinstance(s_, int) and isinstance(e_, int) and 0 <= s_ < e_ <= len(md_live):
            seg = md_live[s_:e_]
            (exact if seg == q else prefix_only).append(
                {"id": a["asset_id"], "method": loc.get("method"),
                 "span": [s_, e_], "quote_chars": len(q), "span_chars": e_ - s_}
                if seg != q else a["asset_id"])
    add("C19.quote_slice_invariant",
        not prefix_only,
        "quote equals md[start_char:end_char] for every asset (single, uniform locator rule)",
        {"exact_assets": len(exact), "non_exact": prefix_only})

    summary = {"n_checks": len(checks),
               "passed": sum(1 for c in checks if c["ok"]),
               "failed": [c["id"] for c in checks if not c["ok"]],
               "blocking_failed": [c["id"] for c in checks if not c["ok"] and c["blocking"]]}
    out = {
        "package_id": "wp-5760-04",
        "generated_at": datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0).isoformat().replace("+00:00", "+00:00"),
        "reviewed_package": "wp-5760-01",
        "reviewed_artifact": "docs/kf/wp-5760-01/asset_manifest.json",
        "reviewed_report_id": 14662,
        "source_identity": {"hash": live_hash, "chars": len(md_live), "bytes": len(raw)},
        "summary": summary,
        "checks": checks,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    for c in checks:
        if not c["ok"]:
            print("FAIL", c["id"], "->", json.dumps(c["observed"], ensure_ascii=False)[:400])


if __name__ == "__main__":
    main()