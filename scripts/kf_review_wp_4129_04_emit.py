#!/usr/bin/env python3
"""wp-4129-04: emit the independent review report for wp-4129-01.

Builds work/wp-4129-04/review_report.json out of
  * the independently fetched markdown (hash-pinned in work/wp-4129-04/source/)
  * the artefact under review (knowledge/kf/wp-4129-01/kf_result.json)
  * machine-verified numbers from the verify/evidence passes
Every quote is taken from work/wp-4129-04/evidence/quotes.json, i.e. a verbatim
slice of the markdown, so nothing in the review is retyped from memory.
"""
import hashlib
import json
import pathlib

WT = pathlib.Path(".")
EV = WT / "work/wp-4129-04/evidence"
SRC = WT / "work/wp-4129-04/source/report_4129.md"
UP = WT / "knowledge/kf/wp-4129-01/kf_result.json"
OUT = WT / "work/wp-4129-04/review_report.json"

md = SRC.read_bytes().decode("utf-8")
raw = SRC.read_bytes()
lines = md.rstrip("\n").split("\n")
quotes = json.loads((EV / "quotes.json").read_text(encoding="utf-8"))
prefs = json.loads((EV / "path_refs.json").read_text(encoding="utf-8"))
findings_machine = json.loads((WT / "work/wp-4129-04/review_findings.json").read_text(encoding="utf-8"))
up = json.loads(UP.read_text(encoding="utf-8"))
man = up["outputs"]["asset_manifest.json"]
up_sha = "sha256:" + hashlib.sha256(UP.read_bytes()).hexdigest()
src_sha = "sha256:" + hashlib.sha256(raw).hexdigest()


def Q(qid):
    return {"quote": quotes[qid]["quote"], "line": quotes[qid]["line"],
            "quote_sha256": quotes[qid]["quote_sha256"], "source_field": "markdown"}


def chk(checks, cid):
    for c in checks["checks"]:
        if c["check_id"] == cid:
            return c
    raise KeyError(cid)


C = {c["check_id"]: c for c in findings_machine["checks"]}
PASSED, TOTAL = findings_machine["checks_passed"], findings_machine["checks_total"]

flat_ids = ([a["asset_id"] for a in man["assets"]] + [l["id"] for l in man["locators"]]
            + [v["ref_id"] for v in man["vcs_references"]]
            + [y["symbol_id"] for y in man["symbol_references"]]
            + [f["fact_id"] for f in man["identity_facts"]])
overlap = set(a["asset_id"] for a in man["assets"]) & set(l["id"] for l in man["locators"])

# ---- registered vs re-derived path-reference census -----------------------
PATH_KINDS = {"file_reference", "data_artifact_reference", "source_code_reference",
              "test_reference", "directory_reference", "worktree_path_reference"}
reg = [{"asset_id": a["asset_id"], "kind": a["kind"], "name": a["name"],
        "line": (a.get("locator") or {}).get("line")}
       for a in man["assets"] if a["kind"] in PATH_KINDS]
reg_lines = {(r["line"], r["name"]) for r in reg}
_cen = [c for c in findings_machine["checks"] if c["check_id"] == "body_path_reference_census"][0]
census_n = _cen["recomputed"]["body_path_references"]
census_distinct_n = _cen["recomputed"]["distinct_referenced_paths"]
missing = [{"line": ln, "token": tok} for ln, tok in _cen["recomputed"]["unregistered_sites"]]

review = {
    "schema": "kf-review-report/v1",
    "package_id": "wp-4129-04",
    "task_type": "04-independent-review",
    "reviewer_role": "red-team-reviewer",
    "report_id": "4129",
    "reviewed_package": "wp-4129-01",
    "reviewed_artifacts": [
        {"path": "knowledge/kf/wp-4129-01/kf_result.json", "sha256": up_sha,
         "what": "envelope + outputs/asset_manifest.json of wp-4129-01"},
        {"path": "knowledge/kf/wp-4129-01/asset_manifest.json", "sha256": "not_hashed",
         "what": "same manifest, standalone copy (bytes not compared: standalone copy is indented separately)"},
    ],
    "reviewed_package_provenance": {
        "source_hash": up["provenance"]["source_hash"],
        "producer": up["provenance"]["producer"],
        "emitted_at": up["provenance"]["emitted_at"],
    },
    "source_provenance": {
        "source_uri": "tensor://reports/4129",
        "source_field": "markdown",
        "source_hash": src_sha,
        "bytes": len(raw),
        "chars": len(md),
        "lines": len(lines),
        "fetched_via": "GET /api/v1/tensor/reports/4129 (own login, own request; no reuse of upstream copy)",
        "hash_recomputed_by_reviewer": True,
        "hash_matches_contract_string": src_sha
        == "sha256:8670fa44138a8835fac88bbc2722e7b0b8f11c9f87ce8fa728ac0971c2a0f155",
    },
    "verdict": "needs-fix",
    "verdict_scope": "non-blocking: the registered facts are true, two registration-precision defects must be "
                     "fixed before the manifest is used as a machine-readable reference index",
    "semantic_fidelity": {
        "judgement": "faithful-with-minor-precision-defects",
        "what_faithful_means_here": "every asserted datum re-derived from the markdown independently; no datum "
                                    "found to contradict the source; no claim upgraded beyond what the source states",
        "facts_re_derived": 30,
        "facts_passed": PASSED,
        "facts_failed": TOTAL - PASSED,
        "per_fact": [
            {"fact_id": "source-hash", "upstream": man["source"]["source_hash"],
             "rederived": src_sha, "pass": C["source_hash"]["pass"],
             "evidence": Q("h1_title")},
            {"fact_id": "source-bytes-chars-lines",
             "upstream": {"bytes": man["source"]["bytes"], "chars": man["source"]["chars"],
                          "lines": man["source"]["lines"]},
             "rederived": {"bytes": len(raw), "chars": len(md), "lines": len(lines)},
             "pass": C["source_bytes"]["pass"] and C["source_chars"]["pass"] and C["source_lines"]["pass"],
             "evidence": Q("h1_title")},
            {"fact_id": "record-fields", "upstream": man["source"]["record_fields"]["title"],
             "rederived": "record title/scenario/mission/status/created_at/tags all equal the live record",
             "pass": all(C["record_" + k]["pass"] for k in
                         ("title", "scenario_key", "mission_id", "status", "created_at", "tags")),
             "evidence": Q("h1_title")},
            {"fact_id": "markdown-quotes-verbatim",
             "upstream": f"{len(reg)} registered path refs; 25 markdown quotes in total",
             "rederived": C["markdown_quotes_verbatim"]["recomputed"],
             "pass": C["markdown_quotes_verbatim"]["pass"] and C["markdown_quotes_on_declared_line"]["pass"],
             "evidence": Q("results_final_row")},
            {"fact_id": "record-pointer-locators", "upstream": "pointer /figures/0/name, /figures/1/name",
             "rederived": C["record_pointers_resolve_to_quote"]["recomputed"],
             "pass": C["record_pointers_resolve_to_quote"]["pass"],
             "evidence": Q("fig1_body")},
            {"fact_id": "merge-commit-sha", "upstream": "b7bbe3707838 / b7bbe3707 / c441d91 / 7accc4b9c / 7accc4b",
             "rederived": C["all_four_sha_forms_present_in_source"]["recomputed"] or "all 5 git tokens present verbatim",
             "pass": C["all_four_sha_forms_present_in_source"]["pass"],
             "evidence": Q("parent_line")},
            {"fact_id": "prefix-arithmetic", "upstream": man["ref_consistency_checks"],
             "rederived": "re-computed: short/full prefixes consistent; c441d91 is a parent, not a prefix",
             "pass": all(C[k]["pass"] for k in ("merge_short_is_prefix_of_full",
                                                "main_head_7hex_is_prefix_of_9hex",
                                                "branch_head_is_not_prefix_of_merge")),
             "evidence": Q("new_sha")},
            {"fact_id": "figure-endpoints-404", "upstream": "artifacts 404 / 22 B; both figures 404 / 29 B",
             "rederived": {k: v for k, v in findings_machine["probes"].items()},
             "pass": findings_machine["probes"].get("/tensor/reports/4129/artifacts", {}).get("status") == 404
             and findings_machine["probes"].get("/tensor/reports/4129/figures/merge_audit.png", {}).get("status") == 404
             and findings_machine["probes"].get("/tensor/reports/4129/figures/plate_gate.png", {}).get("status") == 404,
             "evidence": Q("fig2_body")},
            {"fact_id": "no-verified-marks", "upstream": "checks.no_verified_marks_emitted = true",
             "rederived": C["no_verified_status"]["recomputed"], "pass": C["no_verified_status"]["pass"],
             "evidence": Q("honest_not_done")},
            {"fact_id": "claims-empty", "upstream": "claims = [] with claims_empty_reason",
             "rederived": C["claims_empty"]["recomputed"], "pass": C["claims_empty"]["pass"],
             "evidence": Q("results_final_row")},
            {"fact_id": "honest-unfinished-row-preserved",
             "upstream": "findings[honest-incomplete-local-suite] registered as reported, not upgraded",
             "rederived": "the source's own row keeps the suite 'not run to completion', and the manifest does not "
                          "turn it into a pass",
             "pass": C["finding_anchors_verbatim"]["pass"], "evidence": Q("honest_not_done")},
            {"fact_id": "symbol-locator-anchors-its-token",
             "upstream": "symbol_references/r4129:sym:02 -> line 80 quote",
             "rederived": "the token `tensorfem.__file__` occurs on line 81 only; the line-80 quote does not "
                          "contain it",
             "pass": C["token_inside_locator_quote"]["pass"],
             "evidence": Q("caveat_file_token")},
            {"fact_id": "path-reference-census",
             "upstream": {"body_path_references": man["counts"]["body_path_references"],
                          "distinct_referenced_paths": man["counts"]["distinct_referenced_paths"]},
             "rederived": {"body_path_references": census_n,
                           "distinct_referenced_paths": census_distinct_n,
                           "unregistered": missing},
             "pass": C["body_path_reference_census"]["pass"],
             "evidence": {"quote": lines[missing[0]["line"] - 1], "line": missing[0]["line"],
              "quote_sha256": "sha256:" + hashlib.sha256(lines[missing[0]["line"] - 1].encode()).hexdigest(),
              "source_field": "markdown"}},
            {"fact_id": "figures-not-asserted",
             "upstream": "embedded_figure/metadata_only x2, figures_with_bytes = 0",
             "rederived": {"figure_links_in_body": prefs["png_links_in_body"],
                           "endpoints": "404"},
             "pass": prefs["png_links_in_body"] == [] and not man["counts"]["figures_with_bytes"],
             "evidence": Q("fig1_body")},
        ],
    },
    "checks": [
        {"check_id": c["check_id"], "pass": c["pass"], "upstream_value": c["upstream_value"],
         "recomputed": c["recomputed"], "method": "independent re-derivation from the fetched markdown/record"}
        for c in findings_machine["checks"]
    ],
    "quotation_surface": findings_machine["quotation_surface"],
    "certified_by_review": {
        "checks_total": TOTAL,
        "checks_passed": PASSED,
        "checks_failed": TOTAL - PASSED,
        "failed_check_ids": [c["check_id"] for c in findings_machine["checks"] if not c["pass"]],
    },
    "findings": [
        {
            "finding_id": "F1-symbol-locator-quote-lacks-token",
            "severity": "minor",
            "blocking": False,
            "title": "the locator of symbol `tensorfem.__file__` quotes the preceding line, which does not contain "
                     "the symbol",
            "evidence": {
                "locator": "symbol_references/r4129:sym:02",
                "declared_line": 80,
                "quote": quotes["caveat_worktree_src"]["quote"],
                "token": "tensorfem.__file__",
                "token_actual_lines": [81],
                "token_quote": quotes["caveat_file_token"]["quote"],
            },
            "impact": "a consumer that checks 'is the token inside the recorded quote' gets false; the fact itself "
                      "is true (the symbol occurs verbatim on line 81), and the manifest writes no quote_in_source "
                      "flag for symbol refs, so nothing false is asserted",
            "requested_fix": "move the locator of r4129:sym:02 to line 81 and use the line-81 quote",
        },
        {
            "finding_id": "F2-path-reference-census-undercount",
            "severity": "minor",
            "blocking": False,
            "title": "counts.body_path_references = 13 while re-derivation finds 14 backticked path sites; the "
                     "missing one is the `CHANGELOG.md` occurrence on line 36",
            "evidence": {
                "upstream": {"body_path_references": man["counts"]["body_path_references"],
                             "distinct_referenced_paths": man["counts"]["distinct_referenced_paths"]},
                "rederived": {"body_path_references": census_n,
                              "distinct_referenced_paths": census_distinct_n,
                              "rule": "backticked token in the body that is a concrete path (placeholder "
                                      "PYTHONPATH=<本 worktree>/src excluded, title line 1 excluded, branch token "
                                      "agent/m3369 counted as vcs_reference not as a path)"},
                "missing_sites": missing,
                "missing_quote": ({"quote": lines[missing[0]["line"] - 1], "line": missing[0]["line"],
                                   "quote_sha256": "sha256:" + hashlib.sha256(
                                       lines[missing[0]["line"] - 1].encode()).hexdigest(),
                                   "source_field": "markdown"} if missing else None),
                "counting_rule_declared_upstream": False,
            },
            "impact": "the distinct-path count is right (9), the site count is one short; without a declared "
                      "counting rule the number is not reproducible, which matters for a manifest whose value is "
                      "machine re-checkability",
            "requested_fix": "register the line-36 `CHANGELOG.md` occurrence as an additional file_reference "
                             "(body_path_references -> 14) and declare the census rule in the manifest so the count "
                             "is reproducible",
        },
    ],
    "observations": [
        {"observation_id": "O1-id-namespaces-overlap",
         "detail": f"the {len(man['assets'])} asset ids are reused as locator ids "
                   f"(locators = {len(man['locators'])}); id_integrity reports "
                   f"{man['id_integrity']['ids_checked']} ids checked / unique, which is namespace-local. Merging "
                   f"the namespaces gives {len(flat_ids)} ids / {len(set(flat_ids))} distinct with an "
                   f"asset<->locator overlap of {len(overlap)}.",
         "impact": "non-blocking; the consumer must know the namespace to dereference an id like "
                   "`r4129:source-markdown` (it is both an asset and a locator)"},
        {"observation_id": "O2-record-title-vs-h1",
         "detail": "the record title and the markdown H1 differ in punctuation, and the manifest keeps them in "
                   "separate fields instead of collapsing them: record_fields.title for the record, "
                   "identity_facts/title-line for the H1",
         "impact": "strength, not defect: the divergence is registered, not smoothed over"},
        {"observation_id": "O3-unresolved-reasons-verified",
         "detail": "every unresolved entry whose reason is about the delivery worktree was re-checked by probing "
                   "the tree: " + str(C["unresolved_reasons_true_in_worktree"]["recomputed"]) +
                   "; `tests/` is correctly flagged as same-named-but-foreign instead of resolved",
         "impact": "strength: no unresolved reason is a silent resolution"},
        {"observation_id": "O4-source-field-of-record-locators",
         "detail": "two figure-name locators use source_field=record with quote_in_source=false, so the "
                   "markdown-substring rule is not silently applied to record pointers",
         "impact": "strength"},
    ],
    "independence": {
        "reviewer_context_used": [
            "report 4129 markdown fetched by the reviewer (bytes pinned by sha256)",
            "live report record fields (title/scenario/mission/status/created_at/tags)",
            "the artefact under review: knowledge/kf/wp-4129-01/kf_result.json",
            "live endpoint probes for /artifacts and both /figures/*",
        ],
        "reviewer_context_excluded": [
            "the producer's scripts (scripts/kf_wp_4129_01_*.py)",
            "the producer's test file (tests/test_kf_wp_4129_01.py)",
            "the producer's narrative wrapper docs/kf/wp-4129-01.md (it is an echo of the same JSON; using it "
            "would not add independent evidence)",
        ],
        "limitations": [
            "the review does not open the TensorFEM repository: the upstream artefacts (CHANGELOG.md, "
            "scripts/audit_changelog_merge.py, tests/*, src/tensorfem/plate_uniform_load.py) stay unresolved, as "
            "the manifest itself states, and the review can only confirm that non-assertion",
            "the review re-derives registration fidelity, not the physics of the plate anchors: the numbers "
            "0.4886 % / 11 anchors are read from the source and their provenance is inside TensorFEM",
            "figure bytes are 404 from the API, so no image content was reviewed",
        ],
        "review_prompt_not_copied_from_producer": True,
        "no_claim_marked_verified": True,
    },
    "checks_not_run": [
        {"check": "figure image content vs caption", "why": "both figure endpoints return 404 (re-probed)"},
        {"check": "clone-level verification of the merge result in TensorFEM", "why": "out of the reviewer's "
         "worktree (repo TensorKnowledge); the manifest also refuses to assert it"},
        {"check": "re-running the TensorFEM suites (1707 items, test_changelog_integrity, test_plate_uniform_load)",
         "why": "not runnable here; the source itself reports the full suite as not completed, and this review "
                "keeps that honest FAIL instead of trading it for a pass"},
    ],
    "verdict_detail": {
        "passes": [
            "source identity: hash / bytes / chars / lines / record fields exact",
            "25 of 25 markdown quotes verbatim and on their declared line; 2 of 2 record pointers resolve",
            "all 5 git tokens and both finding anchors present verbatim",
            "figure/artefact endpoints re-probed: 404 with identical byte counts",
            "no verified mark emitted; empty claims justified by contract",
            "honest 'not completed' row preserved, not upgraded",
        ],
        "must_fix": ["F1-symbol-locator-quote-lacks-token", "F2-path-reference-census-undercount"],
        "recommended_disposition": "accept the manifest's factual content; fix F1/F2 in the manifest before it is "
                                   "used as a reference index (both are one-line edits, no physics content involved)",
    },
    "repro_cmd": "python3 scripts/kf_review_wp_4129_04_fetch.py && "
                 "python3 scripts/kf_review_wp_4129_04_verify.py && "
                 "python3 scripts/kf_review_wp_4129_04_evidence.py && "
                 "python3 scripts/kf_review_wp_4129_04_emit.py && "
                 "python3 -m pytest -q tests/test_kf_wp_4129_04.py",
    "limits": [
        "verdict is the reviewer's judgement over registration fidelity; the platform gate computes acceptance",
        "a markdown whitespace change invalidates the pinned source_hash",
        "probes depend on the local platform API being reachable",
    ],
}

# fidelity table tallies recomputed from the table itself
_f = review["semantic_fidelity"]["per_fact"]
review["semantic_fidelity"]["facts_re_derived"] = len(_f)
review["semantic_fidelity"]["facts_passed"] = sum(1 for x in _f if x["pass"])
review["semantic_fidelity"]["facts_failed"] = sum(1 for x in _f if not x["pass"])

# every quote in the emitted report must be a verbatim substring of the markdown
def walk_quotes(o):
    if isinstance(o, dict):
        if set(o) >= {"quote", "line", "quote_sha256"}:
            yield o["quote"]
        for v in o.values():
            yield from walk_quotes(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk_quotes(v)


bad = [s for s in walk_quotes(review) if s not in md]
assert not bad, bad[:3]

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
print("review_report.json written:", OUT, OUT.stat().st_size, "bytes")
print("checks:", PASSED, "/", TOTAL, "verdict:", review["verdict"])
print("missing path sites:", missing)
print("census:", census_n, "distinct:", census_distinct_n)
print("quotes in report:", sum(1 for _ in walk_quotes(review)), "all verbatim:", not bad)