#!/usr/bin/env python3
"""Independent reviewer re-execution of the PROD-RA stage-3 pilot (m22059).

Read-only: every path under the reviewed tree is opened for reading only; all
derived artifacts are written into this reviewer's own worktree.

Usage:
    python3 docs/review_m22059_prod_ra/recheck.py \
        --target /root/tp-agent/work/m22059 \
        --out docs/review_m22059_prod_ra/recheck_output.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

TENSORBENCH = Path("/root/tensor-ecosystem/TensorBench")
sys.path.insert(0, str(TENSORBENCH))
from tensorbench.criteria import canonical_sha256  # noqa: E402

RUN = "runs/m22059"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(target: Path, args: list[str]) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, *args], cwd=target, capture_output=True, text=True)
    return proc.returncode, proc.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="/root/tp-agent/work/m22059")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    t = Path(a.target).resolve()
    out: dict = {"reviewed_commit": subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=t, capture_output=True, text=True).stdout.strip(),
        "target": str(t)}

    report = json.loads((t / RUN / "validation-report.json").read_text(encoding="utf-8"))

    # --- 1. artifact_identity -------------------------------------------------
    ident = []
    for item in report["scenario"]["inputs"]:
        p = t / item["path"]
        actual = sha(p) if p.is_file() else None
        ident.append({"path": item["path"], "declared": item["sha256"], "actual": actual,
                      "match": actual == item["sha256"]})
    copies = {p.name: sha(p) for p in sorted((t / RUN / "audit_corpus" / "source").iterdir())}
    corpus_prov = json.loads((t / RUN / "citation_audit.json").read_text(encoding="utf-8"))
    recorded_input = corpus_prov["input_refs"][0]
    ident.append({"corpus_copy_digests": copies,
                  "audit_recorded_input_ref": recorded_input,
                  "audit_recorded_input_ref_exists": Path(recorded_input).is_file(),
                  "audit_recorded_input_ref_under_target": recorded_input.startswith(str(t))})
    out["artifact_identity"] = ident

    # --- 2. criteria_frozen_before_run ---------------------------------------
    crit_obj = json.loads((t / RUN / "criteria.json").read_text(encoding="utf-8"))
    declared = report["criteria_freeze"]["criteria_sha256"]
    canon = canonical_sha256(crit_obj)
    pretty = hashlib.sha256(json.dumps(crit_obj, ensure_ascii=False, indent=2).encode()).hexdigest()
    out["criteria_frozen_before_run"] = {
        "criteria_ref": report["criteria_freeze"]["criteria_ref"],
        "declared_sha256": declared,
        "recomputed_canonical_sha256": canon,
        "match_canonical": canon == declared,
        "matches_pretty_json_indent2_instead": pretty == declared,
        "frozen_at": report["criteria_freeze"]["frozen_at"],
        "report_created_at": report["created_at"],
        "frozen_before_created": report["criteria_freeze"]["frozen_at"] <= report["created_at"],
        "audit_output_created_at": corpus_prov["created_at"],
        "criteria_frozen_after_audit_ran": report["criteria_freeze"]["frozen_at"] > corpus_prov["created_at"],
        "amendments": report.get("amendments"),
        "criteria_keys": sorted(crit_obj),
    }

    # --- 3. evidence_traceability (sample of the report's findings) ----------
    claims = {p.stem: json.loads(p.read_text(encoding="utf-8"))
              for p in sorted((t / RUN / "audit_corpus" / "claims").glob("*.json"))}
    evidence = {p.stem: json.loads(p.read_text(encoding="utf-8"))
                for p in sorted((t / RUN / "audit_corpus" / "evidence").glob("*.json"))}
    src_text = (t / RUN / "audit_corpus" / "source" / "kf_result_wp-2506-04.md").read_text(encoding="utf-8")
    triage = report["claims_triage"]
    sampled = []
    for bucket in ("verified", "broken"):
        for row in triage[bucket]:
            cid = row["claim_id"]
            claim = claims.get(cid)
            row_out = {"bucket": bucket, "claim_id": cid,
                       "claim_record_present": claim is not None,
                       "triage_entry_has_evidence_refs": bool(row.get("evidence_refs")),
                       "triage_entry_evidence_is_prose": isinstance(row.get("evidence"), str) or
                       isinstance(row.get("reason"), str)}
            if claim:
                refs = claim.get("evidence_refs", [])
                row_out["evidence_refs"] = refs
                det = []
                for ref in refs:
                    ev = evidence.get(ref, {})
                    quote = ev.get("locator", {}).get("quote", "")
                    chash = ev.get("locator", {}).get("content_hash")
                    offsets = (ev.get("locator", {}).get("start_offset"),
                               ev.get("locator", {}).get("end_offset"))
                    found = src_text.find(quote) if quote else -1
                    det.append({
                        "evidence_id": ref,
                        "quote_len": len(quote),
                        "quote_sha256_matches_content_hash":
                            bool(quote) and hashlib.sha256(quote.encode()).hexdigest() == chash,
                        "quote_found_in_source": found,
                        "declared_offsets": list(offsets),
                        "offset_slice_matches_quote":
                            quote != "" and src_text[offsets[0]:offsets[1]] == quote,
                    })
                row_out["evidence"] = det
                row_out["resolvable"] = any(d["quote_found_in_source"] >= 0 for d in det)
            sampled.append(row_out)
    out["evidence_traceability"] = {
        "sampled_findings": len(sampled),
        "unresolvable": [s["claim_id"] for s in sampled if s.get("resolvable") is False],
        "rows": sampled,
    }

    # --- 4. independent_rerun ------------------------------------------------
    reruns = {}
    rc, so = run(t, ["scripts/research_audit/citation_audit.py",
                     f"{RUN}/audit_corpus/source/kf_result_wp-2506-04.md"])
    got = json.loads(so)
    com = json.loads((t / RUN / "citation_audit.json").read_text(encoding="utf-8"))
    reruns["citation_audit_positive"] = {
        "cmd": f"python3 scripts/research_audit/citation_audit.py {RUN}/audit_corpus/source/kf_result_wp-2506-04.md",
        "exit_code": rc,
        "status_rerun": got["overall_status"], "status_recorded": com["overall_status"],
        "checks_rerun": [(c["check_id"], c["state"]) for c in got["checks"]],
        "checks_recorded": [(c["check_id"], c["state"]) for c in com["checks"]],
        "findings_rerun": [f["finding_id"] for f in got["findings"]],
        "findings_recorded": [f["finding_id"] for f in com["findings"]],
        "summary_equal": got["summary"] == com["summary"],
        "only_differing_keys": [k for k in com if got.get(k) != com[k]],
    }
    rc2, so2 = run(t, ["scripts/research_audit/citation_audit.py",
                       f"{RUN}/negative_test/corpus/kf_result_bad.md"])
    neg = json.loads(so2)
    reruns["citation_audit_negative"] = {
        "exit_code": rc2, "status": neg["overall_status"],
        "unresolved_citations": neg["summary"]["unresolved_citations"],
        "detected_999": "999" in neg["summary"]["unresolved_citations"],
        "status_same_as_positive_rate": neg["overall_status"] == got["overall_status"],
        "findings_count_pos_vs_neg": [len(got["findings"]), len(neg["findings"])],
    }
    rc3, so3 = run(t, ["scripts/research_audit/claim_evidence_audit.py", "--claims",
                       f"{RUN}/audit_corpus/claims", "--evidence", f"{RUN}/audit_corpus/evidence",
                       "--source-root", f"{RUN}/audit_corpus/source"])
    got3 = json.loads(so3)
    com3 = json.loads((t / RUN / "claim_evidence_audit.json").read_text(encoding="utf-8"))
    reruns["claim_evidence_audit_positive"] = {
        "exit_code": rc3, "status_rerun": got3["overall_status"], "status_recorded": com3["overall_status"],
        "checks_rerun": [(c["check_id"], c["state"], c["details"]) for c in got3["checks"]],
        "checks_recorded": [(c["check_id"], c["state"], c["details"]) for c in com3["checks"]],
        "finding_codes_rerun": [f["check_id"] for f in got3["findings"]],
        "finding_codes_recorded": [f["check_id"] for f in com3["findings"]],
    }
    rc4, so4 = run(t, ["scripts/research_audit/claim_evidence_audit.py", "--claims",
                       f"{RUN}/negative_test/claims", "--evidence", f"{RUN}/negative_test/evidence",
                       "--source-root", f"{RUN}/negative_test/source"])
    neg3 = json.loads(so4)
    reruns["claim_evidence_audit_negative"] = {
        "exit_code": rc4, "status": neg3["overall_status"],
        "finding_codes": [f["check_id"] for f in neg3["findings"]],
        "detected_dangling_evidence": "missing_evidence_record" in [f["check_id"] for f in neg3["findings"]],
        "detected_dangling_claim": "missing_claim_record" in [f["check_id"] for f in neg3["findings"]],
        "status_same_as_positive": neg3["overall_status"] == got3["overall_status"],
    }
    tri = {b: len(triage[b]) for b in ("verified", "inconclusive", "broken")}
    tri["claim_records_in_corpus"] = len(claims)
    tri["triage_ids_without_claim_record"] = [
        r["claim_id"] for b in ("verified", "inconclusive", "broken") for r in triage[b]
        if r["claim_id"] not in claims]
    reruns["claims_triage_counts"] = tri
    out["independent_rerun"] = reruns

    # --- 5. failure_record ---------------------------------------------------
    led = json.loads((t / RUN / "negative_knowledge_ledger.json").read_text(encoding="utf-8"))
    req = ["keywords", "anchor", "category", "fail_stage", "failure_reason", "repro_cmd",
           "evidence_refs", "affects", "resolution", "cited_kb"]
    recs = []
    import re as _re
    for rec in led["records"]:
        missing = [k for k in req if k not in rec]
        refs = rec.get("evidence_refs") or []
        recs.append({
            "keywords": rec.get("keywords"),
            "missing_fields": missing,
            "evidence_refs_without_sha256": [r for r in refs if "#sha256:" not in r],
            "evidence_refs_empty": not refs,
            "repro_cmd_has_commit_sha": bool(_re.search(r"\b[0-9a-f]{7,40}\b", rec.get("repro_cmd", ""))) ,
            "resolution": rec.get("resolution"),
        })
    out["failure_record"] = {
        "ledger_records": len(led["records"]),
        "per_record": recs,
        "broken_and_inconclusive_in_triage": tri["broken"] + tri["inconclusive"],
        "recorded_in_missing_or_ledger_per_claim": False,
        "evidence_bundle_missing": report["evidence_bundle"].get("missing", []),
        "evidence_items_without_input_fingerprint": [
            it["item_id"] for it in report["evidence_bundle"]["evidence_items"]
            if not it.get("input_sha256") and not it.get("input_refs")],
    }

    # --- 6. regression_scope -------------------------------------------------
    out["regression_scope"] = {
        "adjacent_unit_tests": subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_research_audit_citations.py",
             "tests/test_research_audit_claim_evidence.py", "-q"],
            cwd=t, capture_output=True, text=True).stdout.strip().splitlines()[-1],
        "changed_paths": subprocess.run(["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                                        cwd=t, capture_output=True, text=True).stdout.split(),
        "full_suite": "queued on cluster (see review report)",
    }
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: (v if not isinstance(v, (dict, list)) else "...") for k, v in out.items()},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())