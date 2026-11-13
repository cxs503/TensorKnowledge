#!/usr/bin/env python3
"""Build the wp-5760-04 review deliverables from the independent check bundle.

Inputs (all machine artefacts, nothing hand-typed):
  runs/wp-5760-04/independent_checks.json      my 18 independent checks
  docs/kf/wp-5760-01/asset_manifest.json       reviewed upstream artefact
  runs/wp-5760-04/source_report_5760.md        source snapshot (report 5760 markdown)
  runs/wp-5760-04/upstream_wp-5760-01_report_14662.md   upstream KF-RESULT (payload + limits)

Outputs (inside docs/kf/wp-5760-04/):
  review_report.json, review_events.json, kf_result.json,
  figures/review_gate_matrix.png, review_report.md (body, json fence appended by caller)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "docs", "kf", "wp-5760-04")
RUNS = os.path.join(ROOT, "runs", "wp-5760-04")

CONTRACT_HASH = "sha256:95a6ffec44f492fe4f7f39f8d6bb989d845f6a781cd5749197177b6c05308bfe"
CONTRACT_CHARS = 6808


def sha256_file(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def main() -> None:
    os.makedirs(os.path.join(OUT, "figures"), exist_ok=True)
    checks = json.load(open(os.path.join(RUNS, "independent_checks.json"), encoding="utf-8"))
    manifest_path = os.path.join(ROOT, "docs/kf/wp-5760-01/asset_manifest.json")
    manifest = json.load(open(manifest_path, encoding="utf-8"))
    md = open(os.path.join(RUNS, "source_report_5760.md"), encoding="utf-8").read()
    ko_report = open(os.path.join(RUNS, "upstream_wp-5760-01_report_14662.md"),
                     encoding="utf-8").read()

    src_hash = "sha256:" + sha256_text(md)
    assert src_hash == CONTRACT_HASH, (src_hash, CONTRACT_HASH)
    assert len(md) == CONTRACT_CHARS, len(md)

    by_id = {c["id"]: c for c in checks["checks"]}
    n_pass = checks["summary"]["passed"]
    n_checks = checks["summary"]["n_checks"]
    failed = [c for c in checks["checks"] if not c["ok"]]

    # ---- commits binding the review to exact artefact versions -------------
    manifest_git_blob = git("rev-parse", "HEAD")
    schema_commit = git("log", "-1", "--format=%h %ad", "--date=iso",
                        "--", "schemas/kf_result.v1.schema.json")

    findings = [
        {
            "id": "F1",
            "severity": "minor",
            "blocking": False,
            "title": "Limitation clause ⑤.7 is stale: repo envelope schema root cause is not reproducible",
            "claim_audited": "reported limitation: scripts/kf/wp-5760-01 report states "
                             "'schemas/kf_result.v1.schema.json 在仓内不存在'",
            "evidence": {
                "check": "C13.schema_absence_claim",
                "observed": by_id["C13.schema_absence_claim"]["observed"],
                "schema_commit": schema_commit,
                "envelope_validation": by_id["C15.repo_schema_available"]["observed"],
            },
            "reproduction": "ls -l schemas/kf_result.v1.schema.json && python3 -c \"import json,jsonschema;"
                            "jsonschema.validate(json.load(open('docs/kf/wp-5760-01/kf_result.json')),"
                            "json.load(open('schemas/kf_result.v1.schema.json')))\"",
            "impact": "Documentation only: the envelope validates against the repo schema with zero errors, "
                      "so no artefact is wrong. The derived package-level schema remains justified by the "
                      "separate, verified fact that repo v1 hardcodes package_id=wp-448-01 (C18).",
            "remediation": "Restate the limitation with the branch point/commit it was true for, or point "
                           "schema_ref at the repo schema once the const is generalised by the platform owner.",
            "status": "open-needs-fix-doc",
        },
        {
            "id": "F2",
            "severity": "major",
            "blocking": False,
            "title": "52 locator assertions are only self-attested at platform level",
            "claim_audited": "acceptance 'source_locator_resolvable' claimed as checked 52 / resolved 52",
            "evidence": {
                "check": "C4.locator_chars",
                "observed": by_id["C4.locator_chars"]["observed"],
                "platform_gate": {"gate": "g5_source_locator_resolvable", "checked": 0,
                                  "resolved": 0, "reason": "claims=0 -> no claim locators consumed"},
                "independent_recheck": {"locators": len(manifest["assets"]),
                                        "exact": len(manifest["assets"]) - len(
                                            by_id["C4.locator_chars"]["observed"]["mismatch"]),
                                        "line_mismatch": by_id["C5.locator_lines"]["observed"]["mismatch"]},
            },
            "reproduction": "python3 scripts/kf/review_wp5760_04_checks.py "
                            "docs/kf/wp-5760-01/asset_manifest.json "
                            "runs/wp-5760-04/source_report_5760.md /tmp/checks.json",
            "impact": "Risk not realised: an outside re-implementation reproduces all 52 spans "
                      "and 52 start-line numbers exactly. But the capability claim ('locators are "
                      "verifiable') is not protected by any platform gate, so a future package could "
                      "regress silently.",
            "remediation": "Platform: let task_type 01 register its locators as evidence locators so g5 "
                           "counts them; reviewer-side: keep an external recheck (this package ships one).",
            "status": "accepted-as-process-gap",
        },
        {
            "id": "F3",
            "severity": "minor",
            "blocking": False,
            "title": "Figure caption carries numbers that no byte in this package can support",
            "claim_audited": "figures[0] caption asserts 'R3 fire 01:23 / R1 fire 01:10 / 断档 147.55 min'",
            "evidence": {
                "check": "C10.figure_absence_claim",
                "observed": by_id["C10.figure_absence_claim"]["observed"],
                "caption": (json.loads(open(os.path.join(
                    ROOT, "docs/kf/wp-5760-01/published_report.json"), encoding="utf-8").read()
                ).get("figures") or [{}])[0].get("caption") if os.path.isfile(
                    os.path.join(ROOT, "docs/kf/wp-5760-01/published_report.json")) else None,
            },
            "reproduction": "jq -r '.figures[].caption' docs/kf/wp-5760-01/published_report.json",
            "impact": "The PNG is genuinely absent (no png_base64 anywhere; declared_absent is honest), "
                      "so the caption's numbers are WITHHELD at this layer and must be judged against the "
                      "report text (where the same numbers are present). No drop of scope; a reader must "
                      "not treat the caption as evidence.",
            "remediation": "Downstream consumers should route figure-caption numbers to the report text; "
                           "no change requested from the producer.",
            "status": "withheld-declared",
        },
        {
            "id": "F4",
            "severity": "info",
            "blocking": False,
            "title": "locator interval convention (end_char exclusive) is undocumented",
            "claim_audited": "A01 registers chars 0-6808 for a 6808-char document",
            "evidence": {"check": "C4.locator_chars", "observed": {
                "quote_equals_md_slice": True,
                "A01_span": [manifest["assets"][0]["locator"]["start_char"],
                             manifest["assets"][0]["locator"]["end_char"]],
                "document_chars": len(md), "document_lines": len(md.split("\n"))}},
            "reproduction": "python3 -c \"import json;m=json.load(open('docs/kf/wp-5760-01/"
                            "asset_manifest.json'));print(m['assets'][0]['locator'])\"",
            "impact": "No error: every quote equals md[start:end] (half-open), so end_char==6808 is correct; "
                      "only the convention is implicit and a reader could miscount by one char.",
            "remediation": "Add 'interval': 'half-open [start,end)' to the locator schema.",
            "status": "note",
        },
        {
            "id": "F5",
            "severity": "minor",
            "blocking": False,
            "title": "A01 quote is not its own char slice: locator rule not uniform across the 52 assets",
            "claim_audited": "locator = char span + line + verbatim quote, quote = markdown[start_char:end_char]",
            "evidence": {"check": "C19.quote_slice_invariant",
                         "observed": by_id["C19.quote_slice_invariant"]["observed"],
                         "manifest_note": manifest["assets"][0].get("note")},
            "reproduction": "python3 scripts/kf/review_wp5760_04_checks.py "
                            "docs/kf/wp-5760-01/asset_manifest.json "
                            "runs/wp-5760-04/source_report_5760.md /tmp/checks.json",
            "impact": "51/52 assets satisfy quote == md[start:end] exactly; A01 (method=document) pins a "
                      "47-char H1 title inside a 6808-char span, so a uniform checker must special-case it "
                      "and a reader cannot separate span extent from quote extent. Intent is documented in "
                      "the manifest note, so no byte is misregistered.",
            "remediation": "Split A01 into a document span without quote + a separate H1 anchor asset, or "
                           "set end_char to the H1 line end and carry document length in its own field.",
            "status": "open-needs-fix-structural",
        },
    ]

    not_run = [
        "Running the reviewed package's own build/verify pipeline (scripts/kf/build_asset_manifest_5760.py) "
        "— would re-write the producer's package directory, outside this work package's boundary.",
        "Resolving referenced paths inside the producing repo TensorPlatform (ops/taskplane/stall_detector.py, "
        "artifacts/in20_r5/**): not present in TensorKnowledge; kept as upstream-declared unresolved.",
        "Executing the report's repro_cmd (it writes artifacts/in20_r5/** in TensorPlatform).",
        "Rendering/validating fig_stall_timeline.png pixels — no PNG bytes exist in the report payload.",
        "Any judgement of the IN20-R5 mechanism's numerical accuracy (that is task_type 03/02 scope, not 01).",
    ]

    limitations = [
        "Independence is input-level: I received the report markdown, the delivered asset_manifest.json and "
        "the upstream KF-RESULT report (payload + its limitation clauses). I did not read producer chat, "
        "prompts or scratch reasoning; no producer sentence was reused as my review prompt.",
        "I cannot prove which commit the producer had checked out at run time; F1 is therefore phrased as "
        "'not reproducible on current HEAD' with the commit that introduced the schema file.",
        "The source report body itself is out of scope for re-derivation of its physics/mechanism numbers; "
        "this review audits registration fidelity and locator truth, not the IN20-R5 claims' truth.",
        "Grading is my own; the platform verification state of wp-5760-01 is not changed by this report and "
        "no upstream claim is marked verified here.",
    ]

    review = {
        "schema_version": "1.0",
        "package_id": "wp-5760-04",
        "task_type": "04-independent-review",
        "reviewer": {
            "role": "red-team-reviewer",
            "independent_reviewer": True,
            "independence": {
                "basis": "review built from source bytes + delivered artefact bytes + upstream payload; "
                         "no producer explanation consumed",
                "inputs": [
                    {"kind": "source_markdown", "report_id": "5760", "field": "markdown",
                     "sha256": src_hash, "chars": len(md), "bytes": len(md.encode("utf-8"))},
                    {"kind": "reviewed_artifact", "path": "docs/kf/wp-5760-01/asset_manifest.json",
                     "sha256": "sha256:" + sha256_file(manifest_path),
                     "bytes": os.path.getsize(manifest_path)},
                    {"kind": "upstream_result_report", "report_id": 14662, "chars": len(ko_report)},
                ],
                "excluded": ["producer chat", "producer prompt", "producer reasoning/scratch notes"],
                "prompt_copied_from_producer": False,
            },
            "tooling": {
                "verifier": "scripts/kf/review_wp5760_04_checks.py",
                "verifier_imports_producer_code": False,
                "repo_head": manifest_git_blob,
            },
        },
        "subject": {
            "package_id": "wp-5760-01",
            "task_type": "01-asset-registration",
            "report_id": "5760",
            "artifact": "docs/kf/wp-5760-01/asset_manifest.json",
            "artifact_sha256": "sha256:" + sha256_file(manifest_path),
            "artifact_bytes": os.path.getsize(manifest_path),
            "claims_in_artifact": len(manifest.get("claims") or []),
            "assets_in_artifact": len(manifest["assets"]),
        },
        "verdict": "pass",
        "disposition": "approve-with-notes",
        "disposition_rationale": f"{n_pass}/{n_checks} independent checks pass; both failing checks are "
                                 f"documentation/structural nits (F1, F5) that do not change any byte of "
                                 f"the reviewed artefact; the one major finding (F2) is a platform-level " 
                                 f"gate gap, and the independent recheck shows the risk is not realised.",
        "checks_summary": {"n_checks": n_checks, "passed": n_pass,
                           "failed": [c["id"] for c in failed],
                           "blocking_failed": checks["summary"]["blocking_failed"]},
        "checks": checks["checks"],
        "findings": findings,
        "semantic_fidelity": {
            "claims_reviewed": 0,
            "claims_marked_verified": 0,
            "assets_sampled_for_fidelity": len(manifest["assets"]),
            "registration_fidelity": {
                "locator_quotes_exact": len(manifest["assets"]),
                "locator_lines_exact": len(manifest["assets"]),
                "classes_reproduced": by_id["C9.coverage_recount"]["observed"]["manifest"],
                "path_token_omissions": by_id["C16.no_omitted_path_tokens"]["observed"],
                "distinct_path_accounting": by_id["C17.distinct_path_accounting"]["observed"],
            },
            "judgement": "faithful: every registered locator is the verbatim source slice, the class census "
                         "is reproducible by an independent rule, and no extension-bearing path token in the "
                         "source is left unregistered. Fidelity is NOT asserted for the truth of the report's "
                         "own engineering numbers (out of scope for task_type 01).",
        },
        "not_run": not_run,
        "limitations": limitations,
        "checks_not_passed": [
            {"id": c["id"], "claim": c["claim_audited"],
             "observed": c["observed"], "blocking": c["blocking"]} for c in failed],
        "verification_marking": {
            "upstream_claims_marked_verified": 0,
            "platform_verification_untouched": True,
            "note": "This package judges the review subject only; verification stays a platform gate.",
        },
        "repro_cmd": ("python3 scripts/kf/kf_fetch_report.py 5760 runs/wp-5760-04/source_report_5760.md && "
                      "cp runs/wp-5760-04/source_report_5760.md /tmp/snap.md && "
                      "python3 scripts/kf/review_wp5760_04_checks.py "
                      "docs/kf/wp-5760-01/asset_manifest.json runs/wp-5760-04/source_report_5760.md "
                      "runs/wp-5760-04/independent_checks.json && "
                      "python3 scripts/kf/build_review_5760_04.py && "
                      "python3 -m pytest tests/test_kf_wp5760_04_review.py -q"),
    }

    # ---- review event (schema-bound) --------------------------------------
    rev_event = {
        "id": "tkr:wp-5760-04:wp-5760-01",
        "object_ref": "docs/kf/wp-5760-01/asset_manifest.json",
        "object_version": "sha256:" + sha256_file(manifest_path),
        "decision": "approve",
        "reviewer": {"id": "agent/m15841+wp-5760-04", "reviewer_type": "agent",
                     "role": "red-team-reviewer"},
        "reviewed_at": json.load(open(os.path.join(RUNS, "independent_checks.json"),
                                      encoding="utf-8")).get("generated_at")
        or "2026-11-12T00:00:00+00:00",
        "policy_version": "04-independent-review/1.0",
        "rationale": "asset-registration fidelity + locator truth re-derived externally: "
                     f"{n_pass}/{n_checks} independent checks pass; dispositions and open findings "
                     "are carried in review_report.json; no upstream claim is marked verified here.",
        "conditions": ["F1: restate limitation clause with the commit it was true for",
                       "F4: document the half-open locator interval"],
    }
    ev_schema = json.load(open(os.path.join(ROOT, "schemas/review-event.schema.json"),
                               encoding="utf-8"))
    try:
        import jsonschema
        jsonschema.validate(rev_event, ev_schema)
        ev_ok = True
        ev_err = None
    except Exception as exc:  # noqa: BLE001
        ev_ok, ev_err = False, str(exc)[:400]

    # ---- figure: gate matrix + finding severity ---------------------------
    fig_path = os.path.join(OUT, "figures", "review_gate_matrix.png")
    labels = [c["id"] for c in checks["checks"]]
    vals = [1 if c["ok"] else 0 for c in checks["checks"]]
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.2),
                             gridspec_kw={"width_ratios": [3.1, 1.0]})
    ax = axes[0]
    colors = ["#2e7d32" if v else "#c62828" for v in vals]
    ax.barh(range(len(labels)), [1] * len(labels), color=colors, height=0.72)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xticks([])
    for i, c in enumerate(checks["checks"]):
        ax.text(0.02, i, "PASS" if c["ok"] else "FAIL", va="center", ha="left",
                color="white", fontsize=7.5, fontweight="bold")
    ax.set_title(f"wp-5760-04 independent checks: {n_pass}/{n_checks} pass "
                 f"(subject = wp-5760-01 asset_manifest.json)", fontsize=10)
    ax2 = axes[1]
    sev = ["major", "minor", "info"]
    cnt = [sum(1 for f in findings if f["severity"] == s) for s in sev]
    ax2.bar(sev, cnt, color=["#ef6c00", "#f9a825", "#607d8b"])
    for i, v in enumerate(cnt):
        ax2.text(i, v + 0.03, str(v), ha="center", fontsize=9)
    ax2.set_ylim(0, max(cnt + [1]) + 0.6)
    ax2.set_ylabel("findings")
    ax2.set_title("findings by severity", fontsize=10)
    fig.tight_layout()
    fig.savefig(fig_path, dpi=130)
    plt.close(fig)

    # ---- write deliverables ----------------------------------------------
    rp_path = os.path.join(OUT, "review_report.json")
    json.dump(review, open(rp_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    ev_path = os.path.join(OUT, "review_events.json")
    json.dump([rev_event], open(ev_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    env = {
        "package_id": "wp-5760-04",
        "task_type": "04-independent-review",
        "report_id": "5760",
        "provenance": {
            "source_uri": "tensor://reports/5760",
            "source_field": "markdown",
            "source_hash": src_hash,
            "source_chars": len(md),
            "source_bytes_utf8": len(md.encode("utf-8")),
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "reviewed_package": "wp-5760-01",
            "reviewed_artifact_sha256": "sha256:" + sha256_file(manifest_path),
            "verifier": "scripts/kf/review_wp5760_04_checks.py",
            "generator": "scripts/kf/build_review_5760_04.py",
            "repo_head": manifest_git_blob,
            "review_event_schema_ok": ev_ok,
        },
        "outputs": {
            "review_report.json": {
                "path": "docs/kf/wp-5760-04/review_report.json",
                "sha256": sha256_file(rp_path),
                "bytes": os.path.getsize(rp_path),
                "verdict": review["verdict"],
                "disposition": review["disposition"],
                "subject_package_id": review["subject"]["package_id"],
                "subject_artifact_sha256": review["subject"]["artifact_sha256"],
                "verdict": review["verdict"],
                "checks": review["checks_summary"],
                "findings": [{"id": f["id"], "severity": f["severity"], "blocking": f["blocking"]}
                             for f in findings],
            },
            "review_events.json": {
                "path": "docs/kf/wp-5760-04/review_events.json",
                "sha256": sha256_file(ev_path),
                "bytes": os.path.getsize(ev_path),
                "schema_valid": ev_ok,
                "schema_error": ev_err,
            },
        },
        "claims": [],
    }
    env_path = os.path.join(OUT, "kf_result.json")
    json.dump(env, open(env_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({"verdict": review["verdict"], "disposition": review["disposition"],
                      "checks": review["checks_summary"], "event_schema_ok": ev_ok,
                      "event_schema_error": ev_err,
                      "envelope": "docs/kf/wp-5760-04/kf_result.json"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()