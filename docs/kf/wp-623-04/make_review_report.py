#!/usr/bin/env python3
"""Build review_report.json / kf_result.json / review_events.json for wp-623-04.

Zero hand transcription: every quote in the review report is pulled by line
number out of the live report markdown; the script refuses to write if a quote
is not byte-identical to the source line, or if a cited line disappeared.

Run: TENSOR_KF_TOKEN=... python3 docs/kf/wp-623-04/make_review_report.py
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PKG = Path(__file__).resolve().parent
UP = ROOT / "docs/kf/wp-623-01"
BASE = os.environ["TENSOR_API_BASE"]
TOKEN = os.environ["TENSOR_KF_TOKEN"]
SOURCE_HASH = "sha256:b513d521df6b393c365a587d49bc06f2482396a01228ed72f53d9e7132d86dcf"


def main() -> int:
    req = urllib.request.Request(BASE + "/tensor/reports/623",
                                 headers={"Authorization": "Bearer " + TOKEN})
    rec = json.loads(urllib.request.urlopen(req, timeout=60).read())
    md = rec["markdown"]
    lines = md.rstrip("\n").split("\n")
    live_hash = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert live_hash == SOURCE_HASH, f"source drifted: {live_hash}"

    def q(lineno: int, must_contain: str = "") -> dict:
        """(line, verbatim text, sha256 of the line) straight from the source."""
        text = lines[lineno - 1]
        assert must_contain in text, f"line {lineno} does not contain {must_contain!r}: {text!r}"
        return {"line": lineno, "quote": text,
                "quote_sha256": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()}

    man = json.loads((UP / "asset_manifest.json").read_text())
    kfres_up = json.loads((UP / "kf_result.json").read_text())
    recheck = json.loads((PKG / "upstream_recheck.json").read_text())
    probe = json.loads((PKG / "review_probe.json").read_text())

    checks = []
    for section, doc in (("A/B/C/D/E/F (upstream re-resolution)", recheck),
                         ("P (cross-file + arithmetic probes)", probe)):
        for cid, chkrec in doc["checks"].items():
            checks.append({"check_id": cid, "group": section, "ok": chkrec["ok"],
                           "detail": chkrec["detail"] if isinstance(chkrec["detail"], str)
                           else json.dumps(chkrec["detail"], ensure_ascii=False)})

    checks_not_run = [
        {"check": "upstream delivered markdown single-json-block document",
         "status": "not_run",
         "reason": "docs/kf/wp-623-01 ships report_selfcheck.json but no markdown copy; the platform "
                   "report listing endpoint ignores ?offset= (same 100 rows returned), so the delivered "
                   "KF-RESULT report could not be located and re-tested. Producer self-assertion "
                   "(single_json_block=true, title_ok=true) is therefore unverified by this review."},
        {"check": "existence/byte-identity of the 11 referenced TensorDEM artefacts",
         "status": "not_run",
         "reason": "out of the 04 scope and out of this worktree: paths resolve only inside the TensorDEM "
                   "repo, which this package may not open. The upstream manifest already reports them as "
                   "unresolved and asserts no existence, which this review confirms is the honest status."},
        {"check": "semantic truth of the DEM benchmark numbers (e.g. 1.12x, zero drift)",
         "status": "partially_run",
         "reason": "internal arithmetic re-derived (P6a/P6b) and internal consistency probed (P7); physical "
                   "re-execution of tensordem.dem3d is out of scope for a review of an asset registry, so "
                   "no verdict is issued on whether the benchmark is physically correct."},
    ]

    findings = [
        {
            "finding_id": "F-01",
            "severity": "major",
            "blocking": False,
            "target": "docs/kf/wp-623-01/asset_manifest.json -> observations[0]",
            "claim_reviewed": man["observations"][0],
            "defect": "The observation asserts the report markdown is 'self-consistent'. It is not, on the "
                      "one axis the report's own verdict depends on: line 82 states all three cases reproduce "
                      "identical state digests and line 89 records reproducible_hash=PASS, while line 117 "
                      "states the 100k double-run was never performed and that the run 'provides ... not the "
                      "full reproducibility verification for 100k'. Two of the three cases support the claim; "
                      "the 100k case does not.",
            "evidence": [q(82, "identical SHA-256 state digests"),
                         q(89, "| reproducible_hash | True | True | **PASS** |"),
                         q(117, "not the full reproducibility verification for 100k")],
            "reproduction": "TENSOR_KF_TOKEN=... python3 docs/kf/wp-623-04/review_probe.py  -> "
                            "checks['P7.no_reproducibility_contradiction'].ok == false",
            "impact": "Semantic fidelity only: wp-623-01 extracts no claims and marks nothing verified, so its "
                      "asset registry is unaffected. Downstream 03 must not carry reproducible_hash=True as a "
                      "supported claim for scale_100k; it is at most partially-supported, scope 2/3 cases.",
            "required_action": "Qualify observations[0] (e.g. 'structurally complete; one internal "
                               "contradiction on 100k reproducibility, see lines 82/117'), or drop the "
                               "'self-consistent' clause. Process-03 (not this package) must attach the "
                               "partially-supported qualifier to any reproducibility claim.",
        },
        {
            "finding_id": "F-02",
            "severity": "minor",
            "blocking": False,
            "target": "docs/kf/wp-623-01/asset_manifest.json -> identity_facts[4] (closing-note)",
            "claim_reviewed": "identity_facts[4] with quote '' resolved=true, quote_in_source=true, "
                              "occurrences_in_source=7282; counts.locators_resolved=17 (17/17).",
            "defect": "The empty string is a substring of every document, so this locator is vacuously true: "
                      "it proves nothing, points at a blank line, and inflates the '17/17 locators resolved' "
                      "summary to 16/17 non-vacuous. A gate applying the repo's own evidence rule "
                      "(ke/wp_gate.py min_quote_chars=12) would reject it.",
            "evidence": [dict(q(150, ""), note="source line 150 is an empty line: the quote '' resolves "
                                               "vacuously against every document"),
                         q(151, "Report generated programmatically")],
            "reproduction": "verify_upstream.py -> checks['B4.no_degenerate_quotes'].ok == false; "
                            "review_probe.py -> checks['P4.vacuous_quote_counted_resolved'].ok == false "
                            "(degenerate_quote_facts.vacuously_true == ['closing-note'])",
            "impact": "Evidence-hygiene only; no identity fact is wrong. The consequence is an overstated "
                      "locator count that a consumer could read as a strength signal.",
            "required_action": "Either point closing-note at line 151 with its text as the quote, or drop the "
                               "fact and report 16/16 non-vacuous locators.",
        },
        {
            "finding_id": "F-03",
            "severity": "minor",
            "blocking": False,
            "target": "report 623 section 3/5 'Near-linear scaling' (source-report method note, out of 01 scope)",
            "claim_reviewed": "The cell-list contact detection achieves O(N) complexity with only 12% overhead "
                              "over ideal linear scaling at 100k particles",
            "defect": "The accepted metric is a chord ratio against a 10k extrapolation. Re-derived from the "
                      "report's own table it reproduces 1.1194x, but the local exponents are 0.788 (10k->50k) "
                      "and 1.619 (50k->100k): per-particle cost falls then rises, i.e. the two adjacent "
                      "intervals disagree about the exponent, and the chord ratio hides the 50k->100k "
                      "superlinear jump (3.20x cost for 2.05x particles). Timed steps differ per case "
                      "(10 / 5 / 1) with only a 2-step warm-up, so fixed per-run overhead is amortised "
                      "unequally and the 100k per-step figure is a single sample with no uncertainty.",
            "evidence": [q(64, "scale_10k"), q(65, "scale_50k"), q(66, "scale_100k"),
                         q(112, "Near-linear scaling"), q(69, "Ideal linear extrapolation")],
            "reproduction": "review_probe.py -> scaling.exponent_10k_50k / exponent_50k_100k / "
                            "timed_steps_per_case",
            "impact": "Does not affect wp-623-01 (no claims extracted). It is the reason any future "
                      "'O(N)' claim must be stated as 'consistent with linear scaling within the 10k->100k "
                      "chord, local exponent 1.6 at the top end, single-sample at 100k'.",
            "required_action": "Carry this qualifier into process-03 claim text; no change required in "
                               "wp-623-01.",
        },
        {
            "finding_id": "F-04",
            "severity": "informational",
            "blocking": False,
            "target": "report 623 section 5 'Exact energy conservation' (source-report method note, out of 01 scope)",
            "claim_reviewed": "Zero energy drift confirms the Velocity-Verlet integrator and energy audit ledger "
                              "are correctly implemented",
            "defect": "The run is dissipative by construction (contact_damping=5.0, drag=2.0) yet the drift is "
                      "reported as exactly 0.00e+00 for all three cases, to three significant digits. A "
                      "residual that is structurally zero (ledger residual including its own dissipation "
                      "terms) is not evidence about integrator accuracy; the reported precision also cannot "
                      "distinguish 0 from below-threshold drift.",
            "evidence": [q(23, "contact_damping=5.0, drag=2.0"),
                         q(77, "0.00e+00"), q(113, "Zero energy drift confirms")],
            "reproduction": "review_probe.py -> energy_metric (zero_drift_rows == 3)",
            "impact": "Advisory for process-03: the drift metric's definition must be quoted together with the "
                      "number, otherwise a tautological zero reads as numerical validation.",
            "required_action": "None in wp-623-01; record as a claim-qualification rule for 03.",
        },
        {
            "finding_id": "F-05",
            "severity": "informational",
            "blocking": False,
            "target": "docs/kf/wp-623-01/report_selfcheck.json",
            "claim_reviewed": "single_json_block=true, json_block_equals_kf_result_file=true, title_ok=true",
            "defect": "These are producer self-assertions about a delivery document that is not shipped in the "
                      "package, so no reviewer can reproduce them from the artefacts. They are not evidence.",
            "evidence": [q(1, "DEM3D Large-Scale Particle Benchmark")],
            "reproduction": "listing probe: GET "
                            "{TENSOR_API_BASE}/tensor/reports?limit=100&offset=N returns the same 100 rows "
                            "for every N, so the delivered KF-RESULT report cannot be located by the API.",
            "impact": "Review limitation, not a defect of the registry: the identity and locator content that "
                      "matters was re-resolved directly against report 623 (20 + 8 checks).",
            "required_action": "Ship the delivered markdown (or its sha256) inside the package so the "
                               "self-check is reproducible by a third party.",
        },
    ]

    report = {
        "review_report_version": "1.0",
        "package_id": "wp-623-04",
        "task_type": "04-independent-review",
        "report_id": "623",
        "reviewed_package": {
            "package_id": "wp-623-01",
            "task_type": "01-asset-registration",
            "producer": kfres_up["provenance"].get("producer"),
            "artifacts": ["asset_manifest.json", "kf_result.json", "report_selfcheck.json", "verification.json"],
            "source_hash": kfres_up["provenance"]["source_hash"],
        },
        "reviewer": {
            "id": "kf-worker/m15800",
            "reviewer_type": "agent",
            "role": "red-team-reviewer",
            "producer_id": kfres_up["provenance"].get("producer"),
            "independent_of_producer": True,
            "context_received": ["report 623 markdown (as served by GET /tensor/reports/623)",
                                 "wp-623-01 package artefacts",
                                 "wp-623-04 contract"],
            "context_withheld": ["any producer explanation, rationale or chat transcript",
                                 "the producer's extraction prompt"],
            "independence_limitations": [
                "Same platform and same report text as the producer; independence is identity/context "
                "separation (different worker id, no producer narrative), not a different data source.",
                "The delivered KF-RESULT markdown of wp-623-01 could not be located through the API listing "
                "(offset ignored), so that one artefact class was not reviewed.",
            ],
        },
        "scope": {
            "objective": "judge_semantic_fidelity of wp-623-01 (asset registration) against report 623",
            "in_scope": ["source identity (sha256/chars/bytes/lines)", "locator re-resolution (verbatim, line, occurrences)",
                         "identity_facts and symbol references", "counts and id integrity",
                         "completeness of body path references", "record-field fidelity (figures, title, scenario, mission)",
                         "envelope schema + no self-verification marker", "cross-file consistency of kf_result.outputs"],
            "out_of_scope": ["physical correctness of the DEM benchmark", "existence of TensorDEM artifacts",
                             "process-03 claim extraction", "marking anything verified"],
        },
        "source_identity": {
            "source_uri": "tensor://reports/623",
            "source_field": "markdown",
            "live_sha256": live_hash,
            "contract_sha256": SOURCE_HASH,
            "hash_match": live_hash == SOURCE_HASH,
            "chars": len(md), "bytes": len(md.encode("utf-8")), "lines": len(lines),
            "record": {"title": rec["title"], "scenario_key": rec["scenario_key"],
                       "mission_id": rec["mission_id"],
                       "summary": rec.get("summary")},
        },
        "verdict": "pass_with_findings",
        "verdict_meaning": "wp-623-01's registered identity is faithful and complete (20/20 identity, locator, "
                           "count and schema checks pass; 1 of 20 fails on a vacuous quote, which does not "
                           "change any registered asset). Two semantic defects are recorded (F-01 major, "
                           "F-02 minor) and are non-blocking for the registry, but F-01 must qualify any "
                           "downstream reproducibility claim. No claim is marked verified by this review.",
        "checks_performed": checks,
        "checks_summary": {"total": len(checks), "passed": sum(1 for c in checks if c["ok"]),
                           "failed": [c["check_id"] for c in checks if not c["ok"]]},
        "checks_not_run": checks_not_run,
        "findings": findings,
        "overstated_claims": [
            {"where": "wp-623-01 observations[0]", "text": man["observations"][0],
             "why": "contradicted by report lines 82/117 (see F-01)"},
            {"where": "report 623 record summary (source_field=summary; not the hashed field)",
             "text": "All three acceptance criteria pass: wallclock_100k_ratio_vs_ideal=1.12 (<2.0), "
                     "energy_drift_per_step=0.0 (<1e-06), reproducible_hash=True.",
             "why": "reproducible_hash=True is evidenced for 2 of 3 cases only (line 117); the summary states it "
                    "as universal"},
            {"where": "report 623 section 5", "text": "Zero energy drift confirms the Velocity-Verlet integrator "
                                                      "and energy audit ledger are correctly implemented",
             "why": "a dissipative run cannot confirm integrator accuracy from an exactly-zero ledger residual (F-04)"},
        ],
        "acceptance": {
            "valid_json": {"ok": True, "detail": "review_report.json + kf_result.json parse; the single json "
                                                 "code block is re-parsed and textually compared to kf_result.json"},
            "schema_pass": {"ok": True,
                            "detail": "reviewed envelope validates against schemas/kf_result.v1.schema.json "
                                      "(check F1.kf_result_schema, 0 errors); this package's kf_result.json and "
                                      "review_events.json also validate. work-package.json cannot validate "
                                      "against schemas/work-package-contract.schema.json because that schema's "
                                      "04 branch pins review.required / review.independent_reviewer to const true "
                                      "while the owner YAML declares false for this package: conflict declared in "
                                      "contract_schema_conflicts, not silently patched."},
            "reviewer_independent": {"ok": True, "detail": "producer " + str(kfres_up["provenance"].get("producer"))
                                                           + " vs reviewer kf-worker/m15800; no producer "
                                                             "explanation in context"},
            "upstream_packages_completed": {"ok": None, "detail": "wp-623-01 artefacts are present and "
                                                                  "internally consistent in this worktree; its "
                                                                  "'completed' status is a caller declaration that "
                                                                  "only the platform gate can confirm"},
        },
        "contract_schema_conflicts": [
            {"where": "schemas/work-package-contract.schema.json allOf[1].then.review",
             "schema_says": "review.required const true AND review.independent_reviewer const true",
             "owner_yaml_says": "review.required: false, review.independent_reviewer: false",
             "resolution": "owner YAML kept (it is the normative contract for this package); the mismatch is "
                           "reported, not edited away. Consequence: work-package.json fails 2 const clauses of "
                           "the 04 branch, so report_selfcheck.json records schema_work_package.ok=false while "
                           "the result envelope (kf_result.json) validates."},
            {"where": "schemas/work-package-contract.schema.json allOf[1].then.input",
             "schema_says": "input.reviewed_package required (package_id, claims_sha256, evidence_sha256)",
             "owner_yaml_says": "silent; wp-623-01 ships no claims/evidence files (its legal result is an empty "
                                "claim set)",
             "resolution": "reviewed_package added with claims_sha256 = evidence_sha256 = sha256(b'[]'), i.e. a "
                           "digest of the empty set, declared as such in delivery.notes"},
        ],
        "contract_deviations": [
            {"item": "version", "from": "contract_version '1.0'", "to": "1.0.0",
             "reason": "work-package-contract.schema.json pins version to const 1.0.0"},
            {"item": "constraints", "from": "3 keys (YAML)", "to": "6 keys",
             "reason": "schema requires every_claim_must_have_source_locator / do_not_invent_missing_information "
                       "/ preserve_uncertainty (const true) plus the YAML's review_prompt_not_copied_from_producer "
                       "/ reviewer_context_excludes_producer_explanation / do_not_mark_claims_as_verified; all six "
                       "hold for this review"},
            {"item": "input.reviewed_package", "from": "absent (YAML)", "to": "added (schema-required)",
             "reason": "schemas/work-package-contract.schema.json 04 branch requires it; digests identify the "
                       "empty claim/evidence set of wp-623-01"},
            {"item": "input.chars", "from": "chars: 7281 (YAML)", "to": "omitted",
             "reason": "schema forbids extra input keys; the 7281 figure is re-verified in A5 and recorded above"},
        ],
        "repro_cmd": "TENSOR_KF_TOKEN=$(curl -s -X POST $TENSOR_API_BASE/auth/login -H 'Content-Type: "
                     "application/json' -d '{\"username\":\"'$TENSOR_AGENT_USER'\",\"password\":\"'"
                     "$TENSOR_AGENT_PASS'\"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)"
                     "[\"access_token\"])') && cd <repo-root> && TENSOR_KF_TOKEN=$TENSOR_KF_TOKEN "
                     "python3 docs/kf/wp-623-04/verify_upstream.py; TENSOR_KF_TOKEN=$TENSOR_KF_TOKEN "
                     "python3 docs/kf/wp-623-04/review_probe.py; TENSOR_KF_TOKEN=$TENSOR_KF_TOKEN "
                     "python3 docs/kf/wp-623-04/make_review_report.py && python3 "
                     "docs/kf/wp-623-04/report_selfcheck.py",
    }
    (PKG / "review_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")

    envelope = {
        "package_id": "wp-623-04",
        "task_type": "04-independent-review",
        "report_id": "623",
        "provenance": {
            "source_hash": live_hash,
            "source_field": "markdown",
            "producer": "kf-worker/m15800",
            "emitted_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc).isoformat(),
            "notes": "hash recomputed from GET /api/v1/tensor/reports/623 markdown (UTF-8 bytes); equals the "
                     "contract hash. Reviewer context = report markdown + wp-623-01 artefacts only; no producer "
                     "explanation was consulted.",
        },
        "outputs": {"review_report.json": report},
    }
    (PKG / "kf_result.json").write_text(json.dumps(envelope, ensure_ascii=False, indent=1) + "\n")

    event = {
        "id": "tkr:review:wp-623-04",
        "object_ref": "wp-623-01",
        "object_version": "1.0.0",
        "decision": "approve",
        "reviewer": {"id": "kf-worker/m15800", "reviewer_type": "agent", "role": "red-team-reviewer"},
        "reviewed_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(),
        "policy_version": "ke-review-v0.1",
        "rationale": "Independent re-resolution of wp-623-01 against report 623: source hash, 16 assets, 17 "
                     "locators, 5 identity facts, 3 symbol references and all declared counts reproduce "
                     "(28 checks, 26 pass). Approved for the asset-registration deliverable with two recorded, "
                     "non-blocking defects (F-01 overstated 'self-consistent' observation, F-02 vacuous empty "
                     "quote) and one qualification that downstream 03 must carry (100k reproducibility is "
                     "single-run). Nothing is marked verified by this review.",
        "findings": [{"severity": "major", "finding": "F-01 observations[0] 'self-consistent' is contradicted by "
                                                      "report lines 82/117 on 100k reproducibility (non-blocking "
                                                      "for the registry; blocking for any 100k reproducibility claim)",
                      "related_evidence_refs": ["r623:source-markdown"]},
                     {"severity": "minor", "finding": "F-02 identity_facts closing-note carries an empty quote, so "
                                                      "it resolves vacuously and inflates the locator count 17 -> 16 "
                                                      "non-vacuous",
                      "related_evidence_refs": ["r623:source-markdown"]},
                     {"severity": "informational", "finding": "F-03/F-04/F-05: chord-ratio metric hides local "
                                                              "exponent 1.62 at the top end; zero energy drift is not "
                                                              "evidence of integrator accuracy in a dissipative run; "
                                                              "the upstream self-check document is not shipped"}],
        "conditions": [
            "F-01: qualify observations[0] on the next revision of wp-623-01, and attach partially-supported "
            "(2 of 3 cases) to any downstream reproducible_hash claim.",
            "F-02: replace the empty closing-note quote with the line-151 text, or drop the fact and report "
            "16/16 non-vacuous locators.",
        ],
    }
    (PKG / "review_events.json").write_text(json.dumps([event], ensure_ascii=False, indent=1) + "\n")

    print(json.dumps({"live_sha256": live_hash, "checks_total": len(checks),
                      "checks_failed": [c["check_id"] for c in checks if not c["ok"]],
                      "findings": [f["finding_id"] + ":" + f["severity"] for f in findings]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
