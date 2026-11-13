#!/usr/bin/env python3
"""Build work/wp-4776-04/review_report.json for package wp-4776-04.

Design rule: every quote used in the review is asserted to be a verbatim substring of
the report markdown, and every upstream locator is re-derived here from the markdown
(not copied from the upstream manifest).  If any assertion fails the build aborts.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "source_4776.md")
UP = os.path.join(HERE, "upstream", "asset_manifest_wp-4776-01.json")
OUT = os.path.join(HERE, "review_report.json")

SOURCE_HASH = "sha256:03d3239696a36958c408df0ac3fd21d506a39cce4277b7f918134591d00d3882"

md = open(SRC, encoding="utf-8").read()
assert "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest() == SOURCE_HASH, "source hash drift"
manifest = json.load(open(UP, encoding="utf-8"))


def q(text: str) -> str:
    """Verbatim quote guard: the string must occur exactly once in the report."""
    n = md.count(text)
    assert n == 1, f"quote occurrence {n} != 1: {text!r}"
    return text


def qat(text: str, line: int) -> str:
    """Verbatim quote guard anchored to the asserted source line (1-based)."""
    lines = md.split("\n")
    assert text in lines[line - 1], f"quote not on line {line}: {text!r}"
    return q(text)


# --- quotes (all machine-guarded) -------------------------------------------------
Q_H1 = qat("# PR #185 CI cure: one ruff build for the debt ratchet", 1)
Q_SYMPTOM = q("`test (3.12)` = failure on branch `agent/m4156` (head `3910110`), 4 failed / 1764 passed:")
Q_EMPTY = q("All four failures report *empty* collection")
Q_FAILID = q("FAILED tests/test_lint_gate.py::test_collect_reports_rule_ledger_and_unformatted_set")
Q_LEDGER = q("The debt ledger `docs/lint-baseline.json` is **ruff-version specific**")
Q_CIPIN = qat("| `.github/workflows/ci.yml`, lint job | `pip install \"ruff==0.15.0\"` | 0.15.0 |", 25)
Q_DEVPIN = qat("| `pyproject.toml`, `dev` extra | `ruff>=0.6` | **0.17.3** (resolved by pip) |", 26)
Q_MECH = q("expectations of those fixtures no longer hold and the collection came back empty.")
Q_INFER = q("inferred from ruff's own release notes")
Q_RULE59 = q("59 -> 413 in 0.16, re-based in 0.17")
Q_LIBOK = q("The library code was never involved - `pytest` was green apart from these four.")
Q_REPRO = q("Reproduced locally (ruff 0.15.0, the pin): `tests/test_lint_gate.py` 15/15 passed on the")
Q_FIX4 = q("## Fix (4 files)")
Q_PINDEV = q("`pyproject.toml` - `dev` extra now pins `ruff==0.15.0` (same build as the lint job),")
Q_REGTEST = q("This is the regression test for the incident - it is red on the")
Q_SKIPGUARD = q("ruff is not the frozen build, instead of failing with")
Q_NOSOLVER = q("No solver code, no other test, no unrelated file touched.")
Q_GATE0 = qat("| gate green on the real tree | `python scripts/lint_gate.py --check` | exit **0**, `check 4271 -> 4271`, `unformatted 624 -> 624`, **0 new debt** |", 61)
Q_GATE2 = q("| gate refuses drift | same with a `ruff 0.17.3` shim on `PATH` | exit **2**,")
Q_T18 = qat("| tests after fix | `pytest tests/test_lint_gate.py -q` | **18 passed** |", 63)
Q_T1F = qat("| regression test is red pre-fix | `ruff>=0.6` restored in `pyproject.toml` | **1 failed** (`dev extra declares ['ruff>=0.6'] but the CI lint job pins ruff==0.15.0`), 17 passed |", 64)
Q_T14 = qat("| drift guard | tests with a `ruff 0.17.3` shim on `PATH` | 14 passed, **4 skipped** with the pin/re-freeze reason |", 65)
Q_FIGCTX = q("Evidence logs and the figure live in `runs/pr185-cure/`:")
Q_FIGREF = q("![evidence](fig:pr185-cure-evidence.png)")
Q_LOGS = q("`gate-pinned.log` (exit 0), `gate-drifted.log` (exit 2), `lint-report.json`")
Q_CAVEAT = q("The 0.17.3 mechanism could not be executed locally")

# --- independent re-derivation of the upstream inventory --------------------------
rows, ok = [], 0
for a in manifest["asset_inventory"]:
    loc = a["locator"]
    span = md[loc["char_start"]:loc["char_end"]]
    exact = span == loc["quote"]
    occ = len(re.findall(re.escape(loc["quote"]), md))
    line = md.count("\n", 0, loc["char_start"]) + 1
    good = exact and occ == loc["occurrences"] and line == loc["line"]
    ok += good
    rows.append({"asset_id": a["asset_id"], "kind": a["kind"], "path": a["declared_path"],
                 "span_exact": exact, "occurrences": occ, "line": line, "ok": good})
assert ok == 13, f"locator re-derivation failed: {ok}/13"

paths_in_md = sorted({m.group(1) for m in re.finditer(
    r"[`\s(]((?:[A-Za-z0-9_.\-]+/)*[A-Za-z0-9_.\-]+\.(?:py|toml|json|yml|md|log|png))[`\s),.]", md)})
registered_full = {a["declared_path"] for a in manifest["asset_inventory"]}
registered_base = {os.path.basename(x) for x in registered_full}
unregistered = [p for p in paths_in_md if p not in registered_full and os.path.basename(p) not in registered_base]

review = {
    "reviewer_role": "red-team-reviewer",
    "reviewed_package": "wp-4776-01",
    "reviewed_task_type": "01-asset-registration",
    "reviewed_report_id": "4776",
    "reviewed_source_hash": SOURCE_HASH,
    "verdict": "pass",
    "line_level_verdict": "needs-fix",
    "verdict_scope_note": (
        "verdict judges the object under review, wp-4776-01 (asset registration): its 13 locators "
        "re-derive exactly and its reachability bookkeeping is honest. line_level_verdict judges the "
        "source report 4776 the line is built on: its evidence payloads are unretrievable and one "
        "causal claim is contradicted by the declared repository's own records (R1, R2)."
    ),
    "judge_semantic_fidelity": True,
    "semantic_fidelity": {
        "outcome": "pass",
        "numbers_fabricated": False,
        "summary": (
            "13/13 registered locators re-derive bit-exactly from the source markdown (character "
            "spans, sha256 of each quote, occurrence counts, line numbers) and all 13 path tokens in "
            "the report are registered, so the registration neither invents nor drops a file asset. "
            "The report's internal arithmetic is fully consistent (4+1764=1768 failed/passed in CI; "
            "15 pre-fix tests + 3 new = 18; 14 passed + 4 skipped = 18; 1 failed + 17 passed = 18). "
            "Nothing is marked verified and the claim set is legitimately empty for task type 01. "
            "Three medium findings are recorded against the upstream report, none against the "
            "registration: 0/7 evidence payloads are retrievable (R1), the stated ruff mechanism "
            "predicts more findings rather than an empty collection and is contradicted by the "
            "declared repo's own 0.17.3 record (R2), and the six referenced repo paths resolve "
            "nowhere in the audit environment (R6)."
        ),
        "severity_counts": {"high": 0, "medium": 3, "low": 3},
    },
    "scope_reviewed": {
        "source": "tensor://reports/4776 markdown, 4869 chars, ascii-only, sha256 matched the contract",
        "upstream_artifact": "wp-4776-01 outputs['asset_manifest.json'] (structured artifact only; no producer prose read)",
        "reviewed_repo_state": (
            "TensorFEM mirrors at /root/tensor-ecosystem/TensorFEM (HEAD 916604b7, 502 refs) and "
            "/opt/mm-verify/TensorFEM; 14 ecosystem repos under /root/tensor-ecosystem"
        ),
        "read_only": True,
        "host_probes": ["GET /tensor/reports/4776", "GET /tensor/reports/4776/figures",
                        "GET /tensor/reports/4776/figures/pr185-cure-evidence.png",
                        "GET /tensor/reports/4776/attachments"],
    },
    "checks_run": [
        {"check": "C1_source_identity", "result": "pass",
         "detail": "sha256 03d3239696…d00d3882 == contract; 4869 chars / 4869 bytes; ascii_only"},
        {"check": "C2_locator_fidelity", "result": "pass",
         "detail": "13/13 assets: span exact, content_hash exact, occurrence count exact, line exact"},
        {"check": "C3_completeness", "result": "pass",
         "detail": f"13 path tokens in the markdown, all 13 registered; unregistered={unregistered}"},
        {"check": "C4_internal_arithmetic", "result": "pass",
         "detail": "9 numeric invariants re-computed from the text, all consistent"},
        {"check": "C5_reachability", "result": "fail",
         "detail": "figures listing 404, figure bytes 404, attachments 404; only the record route is 200"},
        {"check": "C6_review_quotes_verbatim", "result": "pass",
         "detail": "every quote carried by this review is a verbatim substring of the markdown"},
        {"check": "C7_review_discipline", "result": "pass",
         "detail": "no claim marked verified; verdict consistent with findings"},
    ],
    "findings": [
        {
            "id": "R1",
            "severity": "medium",
            "blocking": False,
            "blocking_for_downstream": True,
            "type": "evidence payloads not retrievable",
            "location": "report 4776 figures[] + §Evidence (`runs/pr185-cure/`)",
            "report_quote": [Q_FIGCTX, Q_LOGS, Q_FIGREF],
            "reviewer_measurement": {
                "GET /tensor/reports/4776": 200,
                "GET /tensor/reports/4776/figures": 404,
                "GET /tensor/reports/4776/figures/pr185-cure-evidence.png": 404,
                "GET /tensor/reports/4776/attachments": 404,
                "payloads_declared": 7,
                "payloads_resolvable_from_report_store": 0,
            },
            "impact": (
                "0 of 7 declared evidence payloads (1 figure + 6 logs/payloads) can be fetched from the "
                "report store, and the markdown carries no inline bytes, so no downstream package can "
                "hash, parse or re-run against the artifacts behind the verification table "
                "(18 passed / exit 0 / exit 2 / 0 new debt). The figure is additionally referenced "
                "inline as fig:pr185-cure-evidence.png, which renders broken."
            ),
            "upstream_handling": (
                "wp-4776-01 recorded this honestly (A01 reachability=metadata_only_in_record, A02-A07 "
                "declared_only_not_resolvable_in_report_store) - it is a defect of the report, not of "
                "the registration."
            ),
            "recommendation": "Republish 4776 with the figure bytes and the six payloads attached, or delete the inline fig: reference and label the verification table as prose-only.",
        },
        {
            "id": "R2",
            "severity": "medium",
            "blocking": False,
            "blocking_for_downstream": True,
            "type": "causal claim stated as fact, contradicted by the declared repo's own record",
            "location": "report 4776 §Root cause vs TensorFEM docs/lint-gate-determinism.md:16",
            "report_quote": [Q_MECH, Q_INFER, Q_RULE59, Q_EMPTY],
            "reviewer_measurement": {
                "same_repo_record": "TensorFEM docs/lint-gate-determinism.md:16 - `c5168e47` with ruff 0.17.3 = failure (1228 errors)",
                "same_repo_record_2": "TensorFEM pyproject.toml:75 - 'ruff 0.17.4 widened the defaults with the I/UP/RUF/C4/PL families'",
                "prediction_of_stated_mechanism": "a widened default rule set yields MORE findings, not an empty collection",
                "empty_collection_explained_by_report": "stated as a consequence of the widening; the report itself concedes the rule-level detail is inferred",
                "rule_count_59_to_413_verified": False,
            },
            "impact": (
                "A downstream knowledge extraction that turns 'ruff 0.16 widened the default set from 59 "
                "to 413 rules, therefore the fixtures collected nothing' into knowledge would encode a "
                "causal claim that (a) is not measured, and (b) runs against the declared repo's own "
                "recorded behaviour for the same tool version (1228 errors, not zero). The report's "
                "remedy is unaffected - pinning one build and refusing cross-version comparison is "
                "robust to the mechanism - but the explanation must not travel as fact."
            ),
            "recommendation": "Downgrade §Root cause to 'observed: empty parse under 0.17.3; mechanism unconfirmed', and name the untested alternative (JSON output/parse-key or config-rejection change) next to the rule-set-widening hypothesis.",
        },
        {
            "id": "R6",
            "severity": "medium",
            "blocking": False,
            "blocking_for_downstream": True,
            "type": "declared repo paths do not resolve in the audit environment",
            "location": "report 4776 A08-A13 referenced_repo_path assets",
            "report_quote": [Q_SYMPTOM, Q_PINDEV],
            "reviewer_measurement": {
                "repos_searched": "/root/tensor-ecosystem/* (14 repos) + /opt/mm-verify/* mirrors",
                "scripts/lint_gate.py_found": False,
                "docs/lint-baseline.json_found": False,
                "runs/pr185-cure_found": False,
                "branch_agent_m4156_in_TensorFEM": False,
                "TensorFEM_refs_scanned": 502,
                "TensorSPH_refs_scanned": 260,
                "TensorFEM_git_log_all_path_scripts_lint_gate_py": "no commits",
                "TensorFEM_git_log_all_path_docs_lint-baseline_json": "no commits",
                "TensorFEM_HEAD_lint_toolchain_instead": [
                    "scripts/lint_scope.sh (change-scoped gate)",
                    ".github/workflows/ci.yml: lint over lint-scope.txt",
                    "pyproject.toml [tool.ruff.lint] explicit select pin",
                    "docs/lint-gate-determinism.md",
                    "dev extra = ruff>=0.15,<0.16 (range, not ==0.15.0)",
                ],
            },
            "impact": (
                "The report's file inventory (a whole-tree ratchet in scripts/lint_gate.py with a "
                "docs/lint-baseline.json ledger) does not match the declared repository's live lint "
                "toolchain (change-scoped scripts/lint_scope.sh + explicit rule-set pin), and the "
                "described fix is not in any visible history. This is NOT evidence of fabrication: the "
                "report says the work lives on the unmerged branch agent/m4156, and this audit "
                "environment holds main-only snapshots with pruned agent refs. It does mean the six "
                "repo-path assets are unverifiable here, which the upstream manifest's reachability "
                "string (declared_only_not_resolvable_in_report_store) understates."
            ),
            "recommendation": "Until the branch is resolvable, packages 03/05 must treat A08-A12 as WITHHELD (not supported) and keep the quote-level locators as the only binding; register the branch/commit as a provenance handle so resolvability can be retried.",
        },
        {
            "id": "R3",
            "severity": "low",
            "blocking": False,
            "type": "coverage gap in asset kinds",
            "location": "wp-4776-01 asset_inventory (kinds: figure | evidence_artifact | referenced_repo_path)",
            "report_quote": [Q_SYMPTOM],
            "reviewer_measurement": {
                "repo_refs_in_markdown": ["agent/m4156", "3910110"],
                "repo_refs_registered": 0,
                "registered_kinds": ["figure", "evidence_artifact", "referenced_repo_path"],
            },
            "impact": "The only handles that could resolve the unmerged fix (branch agent/m4156, head 3910110) have no slot in the inventory, so the asset set can never point at a retrievable commit.",
            "recommendation": "Add a repo_ref kind (branch/sha) and register both handles.",
        },
        {
            "id": "R4",
            "severity": "low",
            "blocking": False,
            "type": "disclosed discrepancy not surfaced where the gate reads it",
            "location": "wp-4776-01 asset_manifest.json source.* vs unresolved/registration_problems",
            "report_quote": [Q_H1],
            "reviewer_measurement": {
                "platform_record_title": "PR #185 CI cure: one pinned ruff build for the lint debt ratchet",
                "markdown_h1": "# PR #185 CI cure: one ruff build for the debt ratchet",
                "upstream_flag": "source.title_equals_markdown_h1 = false",
                "listed_in_unresolved_or_registration_problems": False,
            },
            "impact": "The title drift is correctly measured but parked in a boolean; a downstream title-binding step that reads only registration_problems/unresolved will see a clean manifest and may bind the wrong title.",
            "recommendation": "Also list the title mismatch under unresolved, with both strings.",
        },
        {
            "id": "R5",
            "severity": "low",
            "blocking": False,
            "type": "coverage trade-off in the upstream fix",
            "location": "report 4776 §Fix item 3 (skip guard)",
            "report_quote": [Q_SKIPGUARD],
            "reviewer_measurement": {
                "tests_skipped_on_drift": 4,
                "tests_passed_on_drift": 14,
                "event_that_triggers_skip": "any ruff build != 0.15.0",
            },
            "impact": "The regression suite goes quiet exactly on the event it guards against (a ruff bump): 4 real-binary end-to-end tests skip instead of failing, so a future genuine breakage on a re-frozen build must be caught by the pin-consistency test alone.",
            "recommendation": "Keep the skip, but add one non-skipping assertion that collection is non-empty under any ruff, so 'collected nothing' can never be silent.",
        },
    ],
    "supported_claims": [
        {"claim": "source hash and length match the contract", "quote": Q_SYMPTOM,
         "reviewer": "sha256 03d32396…d00d3882, 4869 chars, ascii-only"},
        {"claim": "13 registered assets all anchor to a verbatim span", "quote": Q_LEDGER,
         "reviewer": "13/13 spans exact at the declared char offsets; sha256(quote) matches each declared content_hash"},
        {"claim": "occurrence counts are unique-or-correct (figure token occurs twice, once per reference)", "quote": Q_FIGREF,
         "reviewer": "A01 occurrences 2 = 1 bullet + 1 inline fig reference; A02-A13 each occur once"},
        {"claim": "no path token in the report is left unregistered", "quote": Q_FIX4,
         "reviewer": "13 distinct path tokens in the markdown, 13 registered (3 x pyproject.toml / test_lint_gate.py / lint_gate.py repeats)"},
        {"claim": "the four CI failures were enumerated one by one", "quote": Q_FAILID,
         "reviewer": "4 FAILED lines in the symptom block vs the headline '4 failed'"},
        {"claim": "the post-fix suite grew by exactly three tests", "quote": Q_REGTEST,
         "reviewer": "15 pre-fix (report) + 3 named new tests = 18 post-fix (report) - consistent"},
        {"claim": "the drift-guard run partitions the same 18 tests", "quote": Q_T14,
         "reviewer": "14 passed + 4 skipped = 18"},
        {"claim": "the pre-fix regression run partitions the same 18 tests", "quote": Q_T1F,
         "reviewer": "1 failed + 17 passed = 18"},
        {"claim": "gate green means unchanged counts and zero new debt", "quote": Q_GATE0,
         "reviewer": "4271 -> 4271 and 624 -> 624 are self-consistent with '0 new debt' (re-derived, not re-run)"},
        {"claim": "upstream did not mark anything verified and extracted no claims", "quote": Q_NOSOLVER,
         "reviewer": "asset_manifest.json has claims_registration.claims = [] and no verification field; task type 01 owns no claims"},
        {"claim": "reachability status of the figure is accurate", "quote": Q_FIGCTX,
         "reviewer": "record.figures carries name+caption only; figure bytes route 404 (independently probed)"},
    ],
    "checks_not_run": [
        {"check": "re-run lint gate: exit 0 / exit 2 contract", "status": "not_run",
         "reason": "requires scripts/lint_gate.py; absent from every accessible checkout (R6). ruff 0.15.0 is installed locally but the gate script and tests are not."},
        {"check": "pytest tests/test_lint_gate.py -q -> 18 passed / 14+4 skipped", "status": "not_run",
         "reason": "same missing file; the drift-guard run additionally needs a ruff 0.17.3 shim, and no 0.17.3/0.17.4 build is installable here (the report notes there is no loong64 wheel for that build)."},
        {"check": "diff audit of the 4 touched files / 'no solver code touched'", "status": "not_run",
         "reason": "the fix lives on branch agent/m4156, which has no ref in the 502-ref TensorFEM mirror; main's history contains no commit for scripts/lint_gate.py."},
        {"check": "re-count the debt ledger (4271 findings / 624 unformatted)", "status": "not_run",
         "reason": "docs/lint-baseline.json is not present in any accessible checkout."},
        {"check": "ruff 0.16 default-set 59 -> 413", "status": "not_run",
         "reason": "no network access to ruff release notes and no 0.16 build available; the report itself labels this as inferred (R2)."},
        {"check": "inspect the evidence figure image", "status": "not_run",
         "reason": "figure bytes return 404 from the report store; only the 272-char caption exists."},
    ],
    "independence_limitations": [
        "Only the structured artifact of wp-4776-01 was opened (outputs['asset_manifest.json']); its narrative sections were not read, so no producer explanation influenced the findings.",
        "Nothing outside report_id 4776 was read or written; no other report_id was touched.",
        "Repo evidence comes from main-only mirrors with pruned agent refs, so 'not found' is reported as unresolvable (WITHHELD), never as fabrication.",
        "The report's own measurements (18 passed, exit 0, exit 2) could not be re-executed because the gate script is absent; they are verified only for internal consistency.",
    ],
    "reproduction": {
        "one_key": "python3 verify_review.py  (writes checks.json; --offline uses the local source snapshot)",
        "commands": [
            "python3 -c \"import json,urllib.request,os;\"  # see verify_review.py::login for the token flow",
            "python3 verify_review.py",
            "python3 build_review.py",
            "git -C /root/tensor-ecosystem/TensorFEM log --all --oneline -- 'scripts/lint_gate.py'",
            "git -C /root/tensor-ecosystem/TensorFEM for-each-ref --format='%(refname)' | wc -l",
            "grep -n '0.17.3' /root/tensor-ecosystem/TensorFEM/docs/lint-gate-determinism.md",
            "grep -n '0.17.4 widened the defaults' /root/tensor-ecosystem/TensorFEM/pyproject.toml",
        ],
    },
    "disposition": (
        "approve wp-4776-01 with notes (pass): registration is faithful, complete on file assets and "
        "honest about unresolved payloads. Escalate R1 and R2 to the report owner before package 03 "
        "extracts knowledge, and mark A08-A12 WITHHELD until agent/m4156 is resolvable (R6)."
    ),
}

json.dump(review, open(OUT, "w"), ensure_ascii=False, indent=1)
print("wrote", OUT)
print("locator re-derivation:", f"{ok}/13")
print("unregistered paths:", unregistered)
print("findings:", [(f["id"], f["severity"], f["blocking"]) for f in review["findings"]])