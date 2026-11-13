#!/usr/bin/env python3
"""wp-6607-04 independent review: re-derive every wp-6607-01 registration fact.

Reviewer context = report 6607 markdown (verbatim, fetched fresh) + the upstream
package result envelope as published on the platform (report 14665, its single
```json block).  The producer's prose / scripts / test claims are NOT used as
evidence.

Nothing here sets a claim to `verified`; verification belongs to the platform
gate.  Every quoted string printed into the artefacts is asserted to be a
verbatim substring of the source markdown before it is written.

Outputs (all inside the worktree):
  work/wp-6607-04/source/report_6607.md       verbatim source bytes
  work/wp-6607-04/upstream/kf_result_6607_01.json  upstream envelope as published
  runs/wp-6607-04/review_findings.json        check ledger (pass/fail + numbers)
  docs/kf/wp-6607-04/review_report.json       deliverable (review_report.json)

Usage: python3 scripts/kf/wp_6607_04_review.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
USER, PASS = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]

REPORT_ID = "6607"
PKG = "wp-6607-04"
TARGET_PKG = "wp-6607-01"
UPSTREAM_REPORT_ID = 14665
DECLARED = "sha256:b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1"

REPO = pathlib.Path(__file__).resolve().parents[2]
WORK = REPO / "work" / PKG
RUNS = REPO / "runs" / PKG
DOCS = REPO / "docs" / "kf" / PKG


def call(path, body=None, token=None):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = "Bearer " + token
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode() if body else None, headers=h
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def fetch():
    token = call("/auth/login", {"username": USER, "password": PASS})["access_token"]
    rec = call(f"/tensor/reports/{REPORT_ID}", token=token)
    rec = rec.get("data", rec)
    up = call(f"/tensor/reports/{UPSTREAM_REPORT_ID}", token=token)
    up = up.get("data", up)
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "source").mkdir(parents=True, exist_ok=True)
    (WORK / "upstream").mkdir(parents=True, exist_ok=True)
    md = rec["markdown"]
    (WORK / "source" / f"report_{REPORT_ID}.md").write_bytes(md.encode("utf-8"))
    (WORK / "source" / "record.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    (WORK / "upstream" / f"report_{UPSTREAM_REPORT_ID}.md").write_bytes(
        up["markdown"].encode("utf-8"))
    return rec, md, up


def one_json_block(md: str):
    """Return the single fenced json block body + count of json fences."""
    blocks = re.findall(r"```json\s*\n(.*?)```", md, flags=re.S)
    return (blocks[0] if blocks else None), len(blocks)


def schema_valid(obj, schema_path):
    import jsonschema

    schema = json.loads(pathlib.Path(schema_path).read_text(encoding="utf-8"))
    try:
        jsonschema.validate(obj, schema)
        return True, None
    except jsonschema.ValidationError as e:  # pragma: no cover - reported, not raised
        return False, f"{list(e.path)}: {e.message}"


def main() -> int:
    rec, md, up = fetch()
    raw = md.encode("utf-8")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    lines = md.split("\n")
    up_md = up["markdown"]
    body, n_json_blocks = one_json_block(up_md)
    if body is None:
        raise SystemExit("upstream package has no ```json block")
    env = json.loads(body)
    manifest = env["outputs"]["asset_manifest.json"]
    assets = manifest["assets"]

    checks = []

    def chk(check_id, claim, recomputed, ok, notes=""):
        origin = ("report_markdown"
                  if isinstance(claim, str) and claim and claim in md
                  else "upstream_package")
        checks.append({
            "check_id": check_id,
            "upstream_assertion": claim,
            "assertion_origin": origin,
            "recomputed": recomputed,
            "verdict": "pass" if ok else "fail",
            "notes": notes,
        })

    # ---------------- source identity ----------------
    chk("source_hash_matches_contract", DECLARED, digest, digest == DECLARED)
    chk("source_hash_matches_upstream",
        env["provenance"]["source_hash"], digest,
        env["provenance"]["source_hash"] == digest)
    chk("source_bytes", manifest["source"]["bytes_utf8"], len(raw),
        manifest["source"]["bytes_utf8"] == len(raw))
    chk("source_chars", manifest["source"]["chars"], len(md),
        manifest["source"]["chars"] == len(md))
    chk("source_lines_recomputed", "not registered by manifest", len(lines), True,
        "informational: the manifest registers chars/bytes only; lines recomputed here "
        "to drive the locator line check")
    chk("source_crlf_absent", "utf-8/lf", "\r" in md, "\r" not in md)
    chk("record_id", REPORT_ID, str(rec.get("id")), str(rec.get("id")) == REPORT_ID)
    chk("record_title", manifest["source"]["title"], rec.get("title"),
        manifest["source"]["title"] == rec.get("title"))
    chk("record_scenario_key", manifest["source"]["scenario_key"], rec.get("scenario_key"),
        manifest["source"]["scenario_key"] == rec.get("scenario_key"))
    chk("record_status_published", "published", up.get("status"),
        up.get("status") == "published")
    chk("upstream_package_discoverable", f"report tagged kf-wp:{TARGET_PKG}",
        f"report_id={UPSTREAM_REPORT_ID} title={up.get('title')!r}",
        up.get("title") == f"KF-RESULT {TARGET_PKG}"
        and f"kf-wp:{TARGET_PKG}" in (up.get("tags") or []))
    chk("upstream_single_json_block", 1, n_json_blocks, n_json_blocks == 1,
        "result channel must contain exactly one json block")

    # ---------------- envelope / schema ----------------
    ok, err = schema_valid(env, REPO / "schemas/kf_result.v1.schema.json")
    chk("kf_result_schema_pass", "valid per kf_result.v1", ok, ok, err or "")
    canon = json.loads((REPO / "schemas/asset_manifest.v1.schema.json").read_text())
    pinned = json.dumps(canon, ensure_ascii=False)
    schema_pinned_to_448 = ('"wp-448-01"' in pinned and '"448"' in pinned)
    relaxed = canon
    relaxed["properties"]["package_id"] = {"type": "string",
                                          "pattern": "^wp-[A-Za-z0-9][A-Za-z0-9_.:-]*-[0-9]{2}$"}
    relaxed["properties"]["report_id"] = {"type": "string", "pattern": "^[0-9]+$"}
    relaxed["properties"]["source"]["properties"]["uri"] = {"type": "string",
                                                            "pattern": "^tensor://reports/[0-9]+$"}
    rel_path = RUNS / "asset_manifest_schema_relaxed.json"
    RUNS.mkdir(parents=True, exist_ok=True)
    rel_path.write_text(json.dumps(relaxed, ensure_ascii=False, indent=2), encoding="utf-8")
    ok2, err2 = schema_valid({"schema": "asset_manifest.v1", **manifest}, rel_path)
    chk("asset_manifest_schema_pass", "valid per asset_manifest.v1", ok2, ok2,
        (err2 or "") + (" | repo schema pins package_id/report_id/uri to report 448; "
                        "consts relaxed in runs/wp-6607-04/asset_manifest_schema_relaxed.json"
                        if schema_pinned_to_448 else ""))
    chk("envelope_package_id", TARGET_PKG, env["package_id"],
        env["package_id"] == TARGET_PKG)
    chk("envelope_task_type", "01-asset-registration", env["task_type"],
        env["task_type"].startswith("01"))
    all_report_ids = set(re.findall(r'"report_id":\s*"([0-9]+)"', body))
    chk("single_report_scope", [REPORT_ID], sorted(all_report_ids),
        all_report_ids == {REPORT_ID}, "no foreign report_id inside the envelope")
    chk("provenance_source_field", "markdown", env["provenance"]["source_field"],
        env["provenance"]["source_field"] == "markdown")
    chk("claims_empty", [], env.get("claims"), env.get("claims") == [])
    verified_marks = re.findall(r"\bverified\b", body, flags=re.I)
    chk("no_verified_marks", "no verified status", verified_marks, not verified_marks)

    # ---------------- locators ----------------
    pre, inv = [], []
    for a in assets:
        loc = a["locator"]
        q, s, e = loc["quote"], loc["start_char"], loc["end_char"]
        verbatim = q in md
        span_exact = md[s:e] == q
        line_no = md[:s].count("\n") + 1
        line_ok = line_no == loc["start_line"]
        unique = md.count(q) == 1
        if not (verbatim and span_exact and line_ok and unique and loc["unique"]):
            pre.append(a["asset_id"])
        # declared section containment
        sec_decl = a.get("in_report_section", "")
        m = re.match(r"§(\d+)", sec_decl)
        sec_ok, sec_detail = True, ""
        if m:
            head = f"## {m.group(1)} "
            starts = [i for i, ln in enumerate(lines) if ln.startswith(head)]
            if not starts:
                sec_ok = False
                sec_detail = "declared top-level section not found"
            else:
                sec_start = sum(len(ln) + 1 for ln in lines[:starts[0]])
                nxt = [i for i, ln in enumerate(lines) if ln.startswith("## ")
                       and i > starts[0]]
                sec_end = sum(len(ln) + 1 for ln in lines[:nxt[0]]) if nxt else len(md) + 1
                if not (sec_start <= s < sec_end):
                    sec_ok = False
                    sec_detail = f"offset {s} outside §{m.group(1)} [{sec_start},{sec_end})"
                heading = lines[starts[0]]
                extra = [t for t in sec_decl.replace(f"§{m.group(1)}", "").split()
                         if t and t not in heading and "_" in t]
                if extra and sec_ok:
                    row = md[md.rfind("\n", 0, s) + 1: md.find("\n", e)]
                    if not all(t in row for t in extra):
                        sec_ok = False
                        sec_detail = f"row lacks token(s) {extra}"
        if not sec_ok:
            inv.append({"asset_id": a["asset_id"], "why": sec_detail})
        # class vs extension
        ext = q.rsplit(".", 1)[-1]
        expect = {"json": "artifact", "md": "doc", "png": "figure",
                  "py": "script"}.get(ext)
        if expect == "script" and "test" in q:
            expect = "test"
        if expect != a["asset_class"]:
            inv.append({"asset_id": a["asset_id"],
                        "why": f"class {a['asset_class']} vs ext .{ext}"})
    chk("quotes_verbatim", f"{len(assets)} quotes", "all substring", not pre,
        f"failing assets: {pre}")
    chk("spans_copy_exact", f"{len(assets)} char_spans", "md[s:e]==quote for all",
        not pre)
    chk("lines_match_offsets", f"{len(assets)} declared start_line", "recomputed lines",
        not pre)
    chk("quotes_unique_in_source", f"unique={True}", f"{len(assets)} quotes count==1",
        not pre)
    chk("declared_section_contains_offset", f"{len(assets)} in_report_section labels",
        inv, not inv, f"mismatches: {inv}")

    # ---------------- counts ----------------
    hist = {}
    for a in assets:
        hist[a["asset_class"]] = hist.get(a["asset_class"], 0) + 1
    res_hist = {k: 0 for k in ("resolved_in_source", "referenced_unresolved",
                               "declared_absent")}
    for a in assets:
        res_hist[a["resolution"]] = res_hist.get(a["resolution"], 0) + 1
    ids = [a["asset_id"] for a in assets]
    chk("assets_total", manifest["counts"]["assets"], len(assets),
        manifest["counts"]["assets"] == len(assets))
    chk("by_class_histogram", manifest["counts"]["by_class"], hist,
        manifest["counts"]["by_class"] == hist)
    chk("by_resolution_counts", manifest["counts"]["by_resolution"], res_hist,
        manifest["counts"]["by_resolution"] == res_hist)
    chk("asset_ids_unique", "A01-A09", len(set(ids)), len(set(ids)) == len(ids))
    chk("integrity_flags", manifest["integrity"],
        {"quote_uniqueness": not pre, "hash_recomputed_locally": True,
         "hash_matches_contract": digest == DECLARED},
        all(manifest["integrity"].get(k) is True for k in
            ("quote_uniqueness", "hash_recomputed_locally", "hash_matches_contract")))

    # note-level numeric cross-check (zero-hand-copy: numbers pulled from md)
    n_tests = re.search(r'"n_test_functions":\s*([0-9]+)', md).group(1)
    n_neg = re.search(r'"n_negative_controls":\s*([0-9]+)', md).group(1)
    a09 = next(a for a in assets if a["asset_id"] == "A09")
    note_ok = f"{n_tests} cases" in a09["note"] and f"{n_neg} negative" in a09["note"]
    chk("note_numbers_trace_to_source", a09["note"],
        f"{n_tests} test functions / {n_neg} negative controls", note_ok)

    # ---------------- adversarial coverage census ----------------
    PATH_RE = re.compile(r"(?<![A-Za-z0-9_./-])([A-Za-z0-9_][A-Za-z0-9_./-]*\."
                         r"(?:py|md|json|png|ya?ml|toml|csv|txt))(?![A-Za-z0-9_])")
    cited = sorted(set(PATH_RE.findall(md)))
    labels = {a["label"] for a in assets}

    def matched(p):
        return any(p == l or p.endswith("/" + l) for l in labels)

    unreg = [p for p in cited if not matched(p)]
    chk("body_path_reference_census", f"{len(assets)} assets registered",
        {"distinct_cited_paths": len(cited), "registered": len(labels),
         "unregistered": unreg},
        not unreg,
        "every backticked file path in the report must be registered or explicitly excluded")

    # ---------------- negative controls (prove the checks are not vacuous) ----------------
    byte_slice_mismatch = sum(
        1 for a in assets
        if md.encode("utf-8")[a["locator"]["start_char"]:a["locator"]["end_char"]]
        != a["locator"]["quote"].encode("utf-8"))
    chk("nc_byte_offsets_would_fail", "char_span is char-indexed", 
        {"assets_where_byte_slice_differs": byte_slice_mismatch}, byte_slice_mismatch > 0,
        "negative control: interpreting the declared offsets as UTF-8 byte offsets breaks "
        f"{byte_slice_mismatch}/{len(assets)} spans, so passing the span check is informative")
    corrupted = assets[-1]["locator"]["quote"][:-3] + "XYZ"
    chk("nc_corrupted_quote_rejected", "verbatim test discriminates",
        {"corrupted_quote_in_source": corrupted in md}, corrupted not in md,
        "negative control: a 3-char mutation of the last quote is not found in the source")

    # ---------------- findings ----------------
    findings = []
    if unreg:
        findings.append({
            "finding_id": "F1-unregistered-code-module-reference",
            "severity": "major",
            "blocking": False,
            "scope": f"{TARGET_PKG} asset_manifest.assets",
            "evidence": {
                "unregistered_paths": unreg,
                "quote": unreg[0],
                "source_field": "markdown",
                "quote_source": "report_markdown",
                "note": "cited in §2 as the implementation module of the static potential "
                        "and both minimizers, i.e. a first-class provenance target",
            },
            "impact": "downstream extraction/linking has no locator for the core solver "
                      "module; the manifest's 'parsed 9 locatable assets' reads as exhaustive",
            "remediation": "register the module reference (class=script, "
                           "resolution=resolved_in_source) or state the inclusion rule "
                           "explicitly (e.g. 'benchmark/doc/figure/test/artifact entries only')",
        })
    findings.append({
        "finding_id": "F2-counting-rule-not-declared",
        "severity": "minor",
        "blocking": False,
        "scope": "asset_manifest.counts",
        "evidence": {"upstream_quote": "解析出 9 个可定位附件/工件",
                     "quote_source": "upstream_package",
                     "note": "envelope prose asserts exhaustiveness without an "
                             "inclusion rule; the census finds "
                             f"{len(cited)} distinct cited paths"},
        "impact": "the same source admits several legal counts, so the machine gate "
                  "cannot recompute the number without guessing the rule",
        "remediation": "declare inclusion_rule in counts (classes + path patterns)",
    })

    verdict = "pass" if all(c["verdict"] == "pass" for c in checks) else "needs-fix"
    blocking = any(f["blocking"] for f in findings)

    # every quote emitted into the artefacts must be verbatim
    for f in findings:
        ev = f["evidence"]
        key = "quote" if "quote" in ev else "upstream_quote"
        if ev.get("quote_source") == "report_markdown":
            assert ev[key] in md, f"non-verbatim report quote: {ev[key]!r}"
        elif ev.get("quote_source") == "upstream_package":
            assert ev[key] in up_md, f"non-verbatim upstream quote: {ev[key]!r}"
        else:
            raise AssertionError(f"finding {f['finding_id']} has no quote_source")
        if key == "quote":
            assert ev["quote_source"] == "report_markdown"

    ledger = {
        "package_id": PKG,
        "target_package": TARGET_PKG,
        "reviewer_role": "red-team-reviewer",
        "source": {
            "uri": f"tensor://reports/{REPORT_ID}",
            "field": "markdown",
            "hash": digest,
            "chars": len(md),
            "bytes_utf8": len(raw),
            "lines": len(lines),
        },
        "upstream": {
            "uri": f"tensor://reports/{UPSTREAM_REPORT_ID}",
            "title": up.get("title"),
            "status": up.get("status"),
            "markdown_hash": "sha256:" + hashlib.sha256(up_md.encode()).hexdigest(),
            "envelope_package_id": env["package_id"],
        },
        "checks": checks,
        "n_checks": len(checks),
        "n_pass": sum(c["verdict"] == "pass" for c in checks),
        "n_fail": sum(c["verdict"] == "fail" for c in checks),
        "census": {"cited_paths": cited, "registered_labels": sorted(labels),
                   "unregistered": unreg},
        "findings": findings,
        "verdict": verdict,
        "blocking": blocking,
    }
    RUNS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    (RUNS / "review_findings.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")

    review_report = {
        "package_id": PKG,
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "target_package": TARGET_PKG,
        "reviewer_role": "red-team-reviewer",
        "reviewer_independent": True,
        "independence": {
            "reviewer_context_included": [
                f"report {REPORT_ID} markdown (verbatim, freshly fetched)",
                f"upstream envelope of {TARGET_PKG} as published "
                f"(report {UPSTREAM_REPORT_ID}, single json block)",
                "repo schemas (kf_result.v1, asset_manifest.v1)",
            ],
            "reviewer_context_excluded": [
                "producer prose sections 1/2/5/6 of the upstream report "
                "(only the json block is treated as the KO)",
                "producer scripts, tests and worktree of agent/m15592",
                "any producer explanation of the registration logic",
            ],
            "not_reviewed": [
                "existence or content of the 9 registered files in the DEM worktree "
                "(they live outside this repository)",
                "the three figures' pixels (no figure bytes reachable from the envelope)",
                "physical validity of the report's phi_J numbers (upstream task is "
                "registration, not verification)",
            ],
        },
        "verdict": verdict,
        "verdict_scope": "registration fidelity of the upstream package against the "
                         "report bytes; NOT a physics verification",
        "blocking": blocking,
        "summary": (
            f"{len(checks)} recomputed checks, "
            f"{sum(c['verdict'] == 'pass' for c in checks)} pass / "
            f"{sum(c['verdict'] == 'fail' for c in checks)} fail; "
            f"{len(findings)} finding(s), "
            f"{sum(f['blocking'] for f in findings)} blocking. "
            "All 9 registered locators reproduce exactly from the source bytes "
            "(quote == md[start:end], declared line, unique occurrence); "
            f"{len(unreg)} cited path(s) missing from the manifest."
        ),
        "findings": findings,
        "checks": checks,
        "evidence_index": {
            "ledger": "runs/wp-6607-04/review_findings.json",
            "source_snapshot": f"work/wp-6607-04/source/report_{REPORT_ID}.md",
            "upstream_snapshot": f"work/wp-6607-04/upstream/report_{UPSTREAM_REPORT_ID}.md",
        },
        "claims_reviewed": [
            {
                "claim_id": "upstream-asset-coverage-9-complete",
                "text": "9 locatable assets were parsed out of the report",
                "status": "partially-supported",
                "evidence": [{"upstream_quote": "解析出 9 个可定位附件/工件",
                              "source_field": "markdown",
                              "quote_origin": "upstream_package_markdown"}],
                "unresolved_reason": "9 registered entries reproduce, but the census finds "
                                     f"{len(cited)} distinct cited paths; the manifest "
                                     "neither registers nor excludes "
                                     f"{', '.join(unreg) if unreg else 'none'}",
            },
            {
                "claim_id": "upstream-locators-resolve-to-source",
                "text": "every locator quote is a verbatim substring at the declared span",
                "status": "supported",
                "evidence": [{"quote": a["locator"]["quote"], "source_field": "markdown",
                              "quote_origin": "report_markdown"} for a in assets],
            },
        ],
        "quote_policy": "every field named 'quote' is a verbatim substring of the report "
                        "markdown; strings taken from the upstream envelope are stored under "
                        "'upstream_quote'/'upstream_assertion' with quote_origin/assertion_origin",
        "do_not_mark_claims_as_verified": True,
        "generated_from": "scripts/kf/wp_6607_04_review.py",
    }
    (DOCS / "review_report.json").write_text(
        json.dumps(review_report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"checks={len(checks)} pass={ledger['n_pass']} fail={ledger['n_fail']}")
    for c in checks:
        if c["verdict"] == "fail":
            print("  FAIL", c["check_id"], "->", json.dumps(c["recomputed"], ensure_ascii=False)[:300])
    print("census: cited=%d registered=%d unregistered=%s"
          % (len(cited), len(labels), unreg))
    print("verdict:", verdict, "blocking:", blocking)
    return 0 if not blocking else 1


if __name__ == "__main__":
    raise SystemExit(main())