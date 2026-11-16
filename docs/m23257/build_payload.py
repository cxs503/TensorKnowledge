#!/usr/bin/env python3
"""Build the RA-line patch for products/STATUS.json v2 (m23257).

The canonical file lives in the TensorBench repository
(`TensorBench/products/STATUS.json`, sha256 recorded below). This workspace is a
TensorKnowledge checkout, so the file cannot be edited here; the deliverable is
a byte-faithful *proposed* successor built from the canonical file by touching
only the RA row, plus a reconciliation block. `apply_status_patch.py` performs
the same transformation in place in the owning checkout.

Every value written here is taken from docs/m23257/status_evidence.json, which
is recomputed by verify_status.py from a cold extraction of main.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CANONICAL = Path("/root/tensor-ecosystem/TensorBench/products/STATUS.json")
EVIDENCE = HERE / "status_evidence.json"

HEAD = "3fbd3b35c02dd9457fbd46a1905384972883ec8e"
PR511_MERGE = "3a70ce80b74a885ede35a8d3d369f1648527ff50"
R5_REVIEWED_MAIN = "cbd754bbeb8bb386ac61068a762aa6a47bb7a26f"
CRITERIA_SHA = "c12873d308294508116dc623ff162f125b49ce251d3f3d86099e81421052d74a"
VALIDATION_REPORT_SHA = "466f22995fd85dc718a257fc8abeeda5a956a7269f1a48f0c0cea94e933d7bd7"
R5_RECEIPT_SHA = "6c29270dc6961df7ec6bcf8ae3dce162ff0d96962617bc18005bccad6bc8932b"

RA_ROW = {
    "id": "RA",
    "name": "Research Audit",
    "repository": "cxs503/TensorKnowledge",
    "code_implemented": True,
    "scenario_validated": False,
    "acceptance_evidence": {
        "scenario_id": "PROD-RA-m22059",
        "validation_report_ref":
            f"cxs503/TensorKnowledge@{HEAD}:docs/m22059/validation-report.json",
        "review_receipt_ref":
            f"cxs503/TensorKnowledge@{HEAD}:docs/m23157/REVIEW-RECEIPT-R5.json",
        "criteria_sha256": CRITERIA_SHA,
        "reviewed_commit": PR511_MERGE,
        "verdict": "changes_requested",
        "maturity_verdict_ref":
            "tensorplatform:tensor_maturity_verdicts#id=903 (m22059 D1-D12), "
            "#id=918 (R4 residuals); R5 row written by "
            "docs/m23157/verdict_insert_r5.sql (id not readable by this role)",
    },
    "implemented_evidence": [
        "audit engine ships on main@3fbd3b3: docs/review_m22059_prod_ra/recheck.py "
        f"sha256 2cfa24548d69498831a4f05ab58ddbcd503875624d9ca203fdd14230924b1090 = the exact "
        "file PR#511 (d1d5c49) was reviewed on and that was merged as 3a70ce8",
        "entry point exits 0 on a cold extraction of main (tracked files only, no legacy "
        "runs/m22059 tree) and emits all six check sections",
        "markdown citation audit, claim-evidence provenance, negative corpus "
        "(9/9/9 injections detected), failure ledger (3 records) and regression-scope "
        "declaration all execute inside the repository",
        "authorship-side validation report retained at docs/m22059/validation-report.json "
        f"(sha256 {VALIDATION_REPORT_SHA}, criteria sha256 {CRITERIA_SHA})",
        "independent review rounds R4 (docs/review_m22059_prod_ra/REVIEW-R4.md) and R5 "
        f"(docs/m23157/) executed; R5 receipt sha256 {R5_RECEIPT_SHA}",
    ],
    "not_implemented_or_unverified": [
        "R5-1 (blocking, unfixed at main@3fbd3b3): 114 of 144 file locators still point at "
        "the legacy runs/m22059/ layout and 17 are absolute /root/tp-agent refs; only 17/144 "
        "resolve in a cold checkout (11.8%), so a third party cannot reproduce each finding "
        "from the cited source inside the repository",
        "R5-2 (major, unfixed): reviewer bundle manifest unsound - 4 of 18 SHA256SUMS entries "
        "have no file and 1 mismatch (self-digest)",
        "R5-3 (minor, unfixed): 3 of 5 evidence items carry absolute foreign input_refs and "
        "ev-kb10k-incompatibility has no provenance.input_sha256",
        "No expert-labelled holdout or per-class precision/recall for the audit engine; "
        "validation is contract-level (reproducibility/portability), not accuracy against a "
        "labelled gold set",
        "Accepted limitation carried from R4-5: citation_audit reports inconclusive + exit 1 "
        "when the corpus directory is absent",
    ],
    "next_gate":
        "Repair the R5-1/R5-2/R5-3 residuals (relocatable in-repo locators, sound manifest, "
        "complete provenance fingerprints) and obtain one further independent review whose "
        "verdict is pass; scenario_validated may only be set in the same change that cites "
        "that pass verdict, because contracts._status_errors rejects true against "
        "verdict=changes_requested.",
    "baseline_note":
        "code_implemented flipped false->true: the audit engine is now in its owning "
        "repository and runs cold. scenario_validated deliberately left false despite the "
        "mission brief asking for true - see mission_baseline_reconciliation. reviewed_commit "
        "is the PR#511 merge 3a70ce8 as the mission specified; the R5 receipt under review "
        "actually reviewed main@cbd754b plus the standalone fix d1d5c49, which is why both "
        "shas are named here.",
}


def build() -> dict:
    ev = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    loc = ev["r5_1_locators"]
    payload = json.loads(CANONICAL.read_text(encoding="utf-8"))
    payload["as_of"] = "2026-11-16"
    payload["products"] = [RA_ROW if p.get("id") == "RA" else p for p in payload["products"]]
    idx = payload.setdefault("evidence_index", {})
    idx.update({
        "products/STATUS.json (canonical source of this patch)":
            "TensorBench@cxs503 sha256 "
            + hashlib.sha256(CANONICAL.read_bytes()).hexdigest(),
        "docs/m22059/validation-report.json": VALIDATION_REPORT_SHA,
        "docs/m22059/criteria.json": CRITERIA_SHA,
        "docs/m23157/REVIEW-RECEIPT-R5.json": R5_RECEIPT_SHA,
        "docs/m23257/status_evidence.json":
            "recomputed evidence bundle for this publication (verify_status.py)",
        "docs/m23257/status_evidence.json#r5_1_locators":
            f"{loc['pure_path_resolved_cold']}/{loc['pure_path_fields']} locators resolve cold",
    })
    payload["mission_baseline_reconciliation"] = {
        "asserted_by_mission": {
            "RA_code_implemented": True,
            "RA_scenario_validated": True,
            "RA_acceptance_evidence.reviewed_commit": "PR#511 merge commit",
            "RA_acceptance_evidence.verdict": "implied pass (brief says R5 review green, "
                                              "m23157 accepted=true)",
            "RA_acceptance_evidence.maturity_verdict_ref": "rows 917/918",
        },
        "reconciled": {
            "RA_code_implemented": True,
            "RA_scenario_validated": False,
            "RA_acceptance_evidence.reviewed_commit": PR511_MERGE,
            "RA_acceptance_evidence.verdict": "changes_requested",
            "RA_acceptance_evidence.maturity_verdict_ref":
                "id=903 and id=918 cited by the reviews; m23157 row via "
                "docs/m23157/verdict_insert_r5.sql",
        },
        "reason":
            "Two part of the brief reconcile, one does not. (1) code_implemented=true is "
            "confirmed and now recorded: main ships the reviewed recheck.py byte-for-byte "
            "(sha256 2cfa2454...), PR#511 is an ancestor of main@3fbd3b3, and the entry point "
            "exits 0 on a cold extraction. (2) 'six checks pass' and 'PR#511 merged' are also "
            "confirmed. (3) scenario_validated=true is not supportable. The R5 receipt that "
            "this brief calls green records verdict=changes_requested, "
            "scenario_validated=false, and two unfixed residuals that this mission "
            "re-measured on main@3fbd3b3: 127 of 144 file locators still do not resolve in a "
            "cold checkout (114 legacy runs/m22059 prefixes, 17 absolute /root/tp-agent refs) "
            "and the reviewer manifest is still unsound (4 missing + 1 mismatch of 18). "
            "Independently, TensorBench/tensorbench/contracts.py::_status_errors rejects "
            "scenario_validated=true whenever acceptance_evidence.verdict != 'pass', so "
            "writing true here would fail the canonical validator and would launder a "
            "changes_requested verdict into an acceptance. The brief's 'm23157 accepted=true' "
            "is best read as the m23157 mission being accepted as a delivery (its "
            "changes_requested verdict is the accepted output), not as the RA scenario passing "
            "acceptance; conflating the two is the substantive defect this publication "
            "refuses to encode. Rows 917/918 could not be read back (this role has no SELECT "
            "on tensor_maturity_verdicts - see status_evidence.json#verdict_ledger); the "
            "shipped reviews cite id=903 (D1-D12) and id=918 (R4 residuals), and no in-repo "
            "citation of a row 917 was found, so the brief's '917' is left unreconciled "
            "rather than silently plausible.",
    }
    return payload


def main() -> int:
    payload = build()
    out = HERE / "products_STATUS.proposed.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(REPO)} "
          f"sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")
    ra = [p for p in payload["products"] if p["id"] == "RA"][0]
    print(f"RA code_implemented={ra['code_implemented']} "
          f"scenario_validated={ra['scenario_validated']} "
          f"verdict={ra['acceptance_evidence']['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())