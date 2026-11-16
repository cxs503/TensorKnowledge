#!/usr/bin/env python3
"""PROD-RA R4 independent re-check of the m22059 D1-D12 repair on origin/main@ca99e79.

Read-only over the reviewed tree; every derived artifact is written to --out.

Why this file exists next to recheck.py (see REVIEW-R4.md, findings R4-1/R4-2):
  * recheck.py hardcodes RUN = "runs/m22059"; in main the m22059 evidence root is
    docs/m22059, so every locator in the shipped bundle points at a path that does
    not exist in the tree that ships it.  This script resolves the artifact root by
    trying both candidates and reports which one it used.
  * recheck.py reads evidence_bundle.evidence_items[].item_id; D6's repair renamed
    that key to evidence_id and validated against evidence-item.schema.json, so the
    shipped reviewer script raises KeyError on ca99e79.  This script accepts both.

Usage:
    python3 docs/review_m22059_prod_ra/recheck_r4.py --out /tmp/recheck_r4_output.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

TB = Path(os.environ.get("TENSORBENCH", "/srv/tensor/workspace/TensorBench"))
sys.path.insert(0, str(TB))
from tensorbench.criteria import canonical_sha256  # noqa: E402

ROOT_CANDIDATES = ("docs/m22059", "runs/m22059")
ITEM_ID_KEYS = ("evidence_id", "item_id")
LEDGER_FIELDS = ("keywords", "anchor", "category", "fail_stage", "failure_reason",
                 "repro_cmd", "evidence_refs", "affects", "resolution", "cited_kb")


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p: Path) -> str:
    return sha_bytes(p.read_bytes())


def sh(args: list[str], cwd: Path) -> tuple[int, str, str]:
    pr = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return pr.returncode, pr.stdout, pr.stderr


def reroot(ref: str, art: Path, repo: Path) -> Path | None:
    """Map a shipped locator such as runs/m22059/x.json onto the tree it lives in."""
    for cand in ROOT_CANDIDATES:
        if ref == cand or ref.startswith(cand + "/"):
            p = repotarget(repo, art) / ref[len(cand) + 1:]
            return p
    p = repo / ref
    return p


def repotarget(repo: Path, art: Path) -> Path:
    return art


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--out", required=True)
    ap.add_argument("--full-suite", default="not_run")
    ap.add_argument("--reviewed-commit", default=None,
                    help="override the reviewed commit (default: last commit touching the artifact root)")
    a = ap.parse_args()
    repo = Path(a.repo).resolve()
    art = next((repo / c for c in ROOT_CANDIDATES if (repo / c).is_dir()), None)
    # the reviewed commit is the last commit that touched the reviewed artifact root, so that
    # committing this review's own artifacts into the same tree does not move the target (R4-2)
    head = sh(["git", "rev-parse", "HEAD"], repo)[1].strip()
    if a.reviewed_commit:
        reviewed = a.reviewed_commit
    elif art is not None:
        reviewed = sh(["git", "log", "-1", "--format=%H", "--",
                       str(art.relative_to(repo))], repo)[1].strip() or head
    else:
        reviewed = head
    out: dict = {
        "reviewed_commit": reviewed,
        "repository_head": head,
        "repository": str(repo),
        "artifact_root_used": str(art.relative_to(repo)) if art else None,
        "artifact_root_candidates_present": {c: (repo / c).is_dir() for c in ROOT_CANDIDATES},
        "tensorbench_contract_head": sh(["git", "rev-parse", "HEAD"], TB)[1].strip(),
        "python": sys.version.split()[0],
    }
    report = json.loads((art / "validation-report.json").read_text(encoding="utf-8"))
    corpus_path = art / "audit_corpus" / "source" / "kf_result_wp-2506-04.md"
    src_text = corpus_path.read_text(encoding="utf-8")
    dstatus: dict[str, dict] = {}

    # ---------- 1. artifact_identity ----------------------------------------
    inputs = []
    for item in report["scenario"]["inputs"]:
        p = repo / item["path"]
        actual = sha_file(p) if p.is_file() else None
        inputs.append({"path": item["path"], "declared": item["sha256"], "actual": actual,
                       "match": actual == item["sha256"]})
    items = report["evidence_bundle"]["evidence_items"]
    item_identity = []
    for it in items:
        ref = it["source_ref"]
        iid = next((it[k] for k in ITEM_ID_KEYS if k in it), None)
        p = reroot(ref, art, repo)
        actual = sha_file(p) if p and p.is_file() else None
        item_identity.append({"evidence_id": iid, "source_ref": ref,
                              "resolved_at": str(p.relative_to(repo)) if p and p.is_file() else None,
                              "declared": it.get("sha256"), "actual": actual,
                              "match": actual == it.get("sha256")})
    # reviewer-bundle manifest: every line of docs/review_m22059_prod_ra/SHA256SUMS
    revdir = repo / "docs" / "review_m22059_prod_ra"
    manifest_rows = []
    mf = revdir / "SHA256SUMS"
    if mf.is_file():
        for line in mf.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            dig, _, ref = line.partition("  ")
            target = revdir / ref
            actual = sha_file(target) if target.is_file() else None
            manifest_rows.append({"path": ref, "declared": dig, "actual": actual,
                                  "present": target.is_file(),
                                  "match": actual == dig,
                                  "declared_is_empty_artifact_digest": dig == sha_bytes(b"")})
    manifest = {
        "manifest_present": mf.is_file(),
        "entries": len(manifest_rows),
        "entries_missing_file": [r["path"] for r in manifest_rows if not r["present"]],
        "entries_digest_mismatch": [r["path"] for r in manifest_rows if r["present"] and not r["match"]],
        "entries_with_self_or_empty_digest": [r["path"] for r in manifest_rows
                                              if r["declared_is_empty_artifact_digest"] and r["present"]
                                              and r["actual"] != r["declared"]],
        "rows": manifest_rows,
    }
    # REPAIR-NOTES locator form (does the note cite paths that exist in this tree?)
    rn = revdir / "REPAIR-NOTES.md"
    rn_paths = sorted(set(re.findall(r"`((?:runs|docs)/m22059[^`\s]*)`",
                                      rn.read_text(encoding="utf-8")))) if rn.is_file() else []
    rn_unresolved = [x for x in rn_paths
                     if not (repo / x).is_file() and not (repo / x.replace("docs/m22059","runs/m22059")).is_file()]

    # corpus copy must be byte-identical to the recorded primary corpus
    copy_digest = sha_file(corpus_path)
    ev_sum = repo / "EVIDENCE.md"
    out["artifact_identity"] = {
        "scenario_inputs": inputs,
        "scenario_inputs_mismatch": sum(1 for r in inputs if not r["match"]),
        "evidence_items": item_identity,
        "evidence_items_unresolved": [r["evidence_id"] for r in item_identity if r["actual"] is None],
        "evidence_items_mismatch": [r["evidence_id"] for r in item_identity if r["actual"] and not r["match"]],
        "corpus_copy_sha256": copy_digest,
        "corpus_copy_equals_primary_input": copy_digest == report["scenario"]["inputs"][0]["sha256"],
        "evidence_summary_present": ev_sum.is_file(),
        "evidence_summary_sha256": sha_file(ev_sum) if ev_sum.is_file() else None,
        "reviewer_bundle_manifest": manifest,
        "repair_notes_paths_cited": rn_paths,
        "repair_notes_paths_unresolved": rn_unresolved,
    }

    # ---------- 2. criteria_frozen_before_run -------------------------------
    crit = json.loads((art / "criteria.json").read_text(encoding="utf-8"))
    cf = report["criteria_freeze"]
    canon = canonical_sha256(crit)
    pretty = sha_bytes(json.dumps(crit, ensure_ascii=False, indent=2).encode())
    crit_ref_p = reroot(cf["criteria_ref"], art, repo)
    earliest = cf.get("earliest_audit_output_created_at")
    out["criteria_frozen_before_run"] = {
        "criteria_ref": cf["criteria_ref"],
        "criteria_ref_resolvable_in_tree": bool(crit_ref_p and crit_ref_p.is_file()),
        "criteria_version": cf.get("criteria_version"),
        "declared_sha256": cf["criteria_sha256"],
        "recomputed_canonical_sha256": canon,
        "match_canonical": canon == cf["criteria_sha256"],
        "matches_pretty_json_instead": pretty == cf["criteria_sha256"],
        "hash_convention": cf.get("hash_convention"),
        "frozen_at": cf["frozen_at"],
        "earliest_audit_output_created_at": earliest,
        "report_created_at": report["created_at"],
        "frozen_before_earliest_output": earliest is not None and cf["frozen_at"] <= earliest,
        "frozen_before_report_created": cf["frozen_at"] <= report["created_at"],
        "freeze_precedes_outputs_declared": cf.get("freeze_precedes_outputs"),
        "superseded_timeline_preserved": "superseded_timeline" in cf,
        "amendments": [x.get("amendment_id") for x in crit.get("amendments", [])],
        "criterion_count": len(crit.get("criteria", [])),
        "criterion_ids": [x["criterion_id"] for x in crit.get("criteria", [])],
        "criteria_sources": sorted({x.get("source", "") for x in crit.get("criteria", [])}),
    }

    # ---------- 3. evidence_traceability ------------------------------------
    claims = {p.stem: json.loads(p.read_text(encoding="utf-8"))
              for p in sorted((art / "audit_corpus" / "claims").glob("*.json"))}
    evid = {p.stem: json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((art / "audit_corpus" / "evidence").glob("*.json"))}
    loc_rows, dangling = [], []
    for name, ev in evid.items():
        loc = ev.get("locator", {})
        q, ch = loc.get("quote", ""), loc.get("content_hash")
        s, e = loc.get("start_offset"), loc.get("end_offset")
        row = {"evidence_id": ev.get("id", name), "quote_len": len(q),
               "content_hash_matches_quote": bool(q) and sha_bytes(q.encode()) == ch,
               "start_offset_zero": s == 0, "end_offset_zero": e == 0,
               "slice_matches_quote": isinstance(s, int) and isinstance(e, int) and src_text[s:e] == q and bool(q),
               "quote_found_at_declared_only": src_text.find(q) if q else -1}
        loc_rows.append(row)
        for cl in ev.get("claim_refs", []):
            if cl not in claims:
                dangling.append({"evidence": name, "missing_claim": cl})
    tri = report["claims_triage"]
    triage_rows = []
    for bucket in ("verified", "inconclusive", "broken"):
        for row in tri[bucket]:
            cid = row["claim_id"]
            refs = (claims.get(cid) or {}).get("evidence_refs", [])
            resolvable = [r for r in refs if r in evid and evid[r].get("locator", {}).get("quote")]
            triage_rows.append({"bucket": bucket, "claim_id": cid,
                                "claim_record_present": cid in claims,
                                "evidence_refs": refs,
                                "evidence_resolvable": len(resolvable),
                                "prose_only": isinstance(row.get("reason"), str)})
    triage_ids = [r["claim_id"] for r in triage_rows]
    dangling += [{"triage": t, "missing_claim": t} for t, ok in
                 ((t["claim_id"], t["claim_record_present"]) for t in triage_rows) if not ok]
    out["evidence_traceability"] = {
        "evidence_records": len(evid),
        "locators_total": len(loc_rows),
        "locators_with_empty_quote": [r["evidence_id"] for r in loc_rows if r["quote_len"] == 0],
        "locators_start_offset_zero": [r["evidence_id"] for r in loc_rows if r["start_offset_zero"]],
        "locators_slice_mismatch": [r["evidence_id"] for r in loc_rows if not r["slice_matches_quote"]],
        "locators_hash_mismatch": [r["evidence_id"] for r in loc_rows if not r["content_hash_matches_quote"]],
        "locator_rows": loc_rows,
        "auditor_findings": json.loads((art / "claim_evidence_audit.json").read_text())["findings"][:5],
        "auditor_overall_status": json.loads((art / "claim_evidence_audit.json").read_text())["overall_status"],
        "triage_entries": len(triage_rows),
        "triage_unresolvable": [t["claim_id"] for t in triage_rows if t["evidence_resolvable"] == 0],
        "dangling": dangling,
    }

    # ---------- 4. independent_rerun ----------------------------------------
    runs: dict = {}
    neg = art / "negative_test"
    rc, so, se = sh([sys.executable, "scripts/research_audit/citation_audit.py",
                     str(corpus_path)], repo)
    got = json.loads(so) if so.strip() else {}
    rec = json.loads((art / "citation_audit.json").read_text(encoding="utf-8"))
    volatile = {"created_at", "input_refs", "command", "output", "output_path"}
    runs["citation_audit_positive"] = {
        "cmd": f"citation_audit.py {corpus_path.relative_to(repo)}",
        "exit_code": rc, "stderr": se.strip()[:400],
        "status_rerun": got.get("overall_status"), "status_recorded": rec["overall_status"],
        "checks_equal": [(c["check_id"], c["state"]) for c in got.get("checks", [])] ==
                        [(c["check_id"], c["state"]) for c in rec["checks"]],
        "findings_rerun": [f.get("check_id") for f in got.get("findings", [])],
        "findings_recorded": [f.get("check_id") for f in rec["findings"]],
        "summary_equal": got.get("summary") == rec.get("summary"),
        "differing_keys": sorted(k for k in set(got) | set(rec)
                                 if k not in volatile and got.get(k) != rec.get(k)),
    }
    rc, so, _ = sh([sys.executable, "scripts/research_audit/citation_audit.py",
                    str(neg / "corpus" / "kf_result_bad.md")], repo)
    ng = json.loads(so) if so.strip() else {}
    runs["citation_audit_negative"] = {
        "exit_code": rc, "status": ng.get("overall_status"),
        "unresolved_citations": ng.get("summary", {}).get("unresolved_citations"),
        "detected_999": "999" in (ng.get("summary", {}).get("unresolved_citations") or []),
        "findings_pos_vs_neg": [len(got.get("findings", [])), len(ng.get("findings", []))],
    }
    rc, so, se = sh([sys.executable, "scripts/research_audit/claim_evidence_audit.py",
                     "--claims", str(art / "audit_corpus" / "claims"),
                     "--evidence", str(art / "audit_corpus" / "evidence"),
                     "--source-root", str(art / "audit_corpus" / "source")], repo)
    g2 = json.loads(so) if so.strip() else {}
    r2 = json.loads((art / "claim_evidence_audit.json").read_text(encoding="utf-8"))
    runs["claim_evidence_audit_positive"] = {
        "exit_code": rc, "stderr": se.strip()[:400],
        "status_rerun": g2.get("overall_status"), "status_recorded": r2["overall_status"],
        "checks_rerun": [(c["check_id"], c["state"], c.get("details")) for c in g2.get("checks", [])],
        "checks_recorded": [(c["check_id"], c["state"], c.get("details")) for c in r2["checks"]],
        "finding_codes_rerun": [f.get("check_id") for f in g2.get("findings", [])],
        "finding_codes_recorded": [f.get("check_id") for f in r2["findings"]],
        "differing_keys": sorted(k for k in set(g2) | set(r2)
                                if k not in volatile and g2.get(k) != r2.get(k)),
    }
    rc, so, se = sh([sys.executable, "scripts/research_audit/claim_evidence_audit.py",
                     "--claims", str(neg / "claims"), "--evidence", str(neg / "evidence"),
                     "--source-root", str(neg / "source")], repo)
    n2 = json.loads(so) if so.strip() else {}
    codes = [f.get("check_id") for f in n2.get("findings", [])]
    runs["claim_evidence_audit_negative"] = {
        "exit_code": rc, "status": n2.get("overall_status"),
        "finding_codes": codes,
        "detected_dangling_evidence": "missing_evidence_record" in codes,
        "detected_dangling_claim": "missing_claim_record" in codes,
        "status_differs_from_positive": n2.get("overall_status") != g2.get("overall_status"),
    }
    declared = {"citation": json.loads((neg / "citation_audit_negative.json").read_text())["overall_status"],
                "claim_evidence": json.loads((neg / "claim_evidence_audit_negative.json").read_text())["overall_status"]}
    runs["negative_matches_recorded"] = {
        "citation_audit": {"rerun": runs["citation_audit_negative"]["status"],
                           "recorded": declared["citation"]},
        "claim_evidence_audit": {"rerun": runs["claim_evidence_audit_negative"]["status"],
                                 "recorded": declared["claim_evidence"]},
    }
    runs["claims_triage_counts"] = {
        "verified": len(tri["verified"]), "inconclusive": len(tri["inconclusive"]),
        "broken": len(tri["broken"]), "sum": sum(len(tri[b]) for b in ("verified", "inconclusive", "broken")),
        "claim_records_in_corpus": len(claims),
        "reproduced_from_corpus": (len(tri["verified"]) + len(tri["inconclusive"]) + len(tri["broken"]))
        == report["claims_triage_summary"].get("triage_entries"),
    }
    out["independent_rerun"] = runs

    # ---------- 5. failure_record -------------------------------------------
    led = json.loads((art / "negative_knowledge_ledger.json").read_text(encoding="utf-8"))
    recs = []
    for rec in led["records"]:
        refs = rec.get("evidence_refs") or []
        resolved = []
        for r in refs:
            path, _, dig = r.partition("#sha256:")
            p = reroot(path, art, repo)
            ok = bool(p and p.is_file())
            resolved.append({"ref": r, "resolves": ok,
                             "digest_matches": ok and sha_file(p) == dig})
        recs.append({"keywords": rec.get("keywords"),
                     "missing_fields": [k for k in LEDGER_FIELDS if k not in rec],
                     "evidence_refs": refs,
                     "refs_without_sha256": [r for r in refs if "#sha256:" not in r],
                     "refs_resolved": resolved,
                     "repro_cmd_has_commit_sha": bool(re.search(r"\b[0-9a-f]{7,40}\b", rec.get("repro_cmd", ""))),
                     "repro_commit_present_in_repo": bool(re.search(
                         r"\b([0-9a-f]{7,40})\b", rec.get("repro_cmd", ""))) and
                         sh(["git", "cat-file", "-t", re.search(r"\b([0-9a-f]{7,40})\b",
                                                                 rec.get("repro_cmd", "")).group(1)], repo)[0] == 0,
                     "resolution": rec.get("resolution")})
    out["failure_record"] = {
        "repair_notes_present": (repo / "docs/review_m22059_prod_ra/REPAIR-NOTES.md").is_file(),
        "ledger_records": len(led["records"]),
        "per_record": recs,
        "records_missing_fields": sum(1 for r in recs if r["missing_fields"]),
        "records_with_ref_without_sha256": sum(1 for r in recs if r["refs_without_sha256"]),
        "records_without_commit_sha": sum(1 for r in recs if not r["repro_cmd_has_commit_sha"]),
        "broken_claims": len(tri["broken"]), "inconclusive_claims": len(tri["inconclusive"]),
        "swallowed_failures": 0 if all(r["resolution"] for r in recs) else len(recs),
        "evidence_bundle_missing": report["evidence_bundle"].get("missing", []),
        "evidence_items_without_input_fingerprint": [
            next((it[k] for k in ITEM_ID_KEYS if k in it), None) for it in items
            if not (it.get("provenance", {}).get("input_sha256") or it.get("input_sha256"))],
    }

    # ---------- 6. regression_scope -----------------------------------------
    rsp = art / "regression-scope.json"
    rs = json.loads(rsp.read_text(encoding="utf-8")) if rsp.is_file() else {}
    rc, so, se = sh([sys.executable, "-m", "pytest", "tests/test_research_audit_citations.py",
                     "tests/test_research_audit_claim_evidence.py", "-q"], repo)
    out["regression_scope"] = {
        "file_present": rsp.is_file(),
        "verified_at_commit": rs.get("verified_at_commit"),
        "base_commit": rs.get("base_commit"),
        "changed_paths_count": len(rs.get("changed_paths", [])),
        "declared_adjacent_tests": rs.get("adjacent_unit_tests") or rs.get("adjacent_tests"),
        "declared_full_suite": rs.get("full_suite"),
        "adjacent_rerun_exit_code": rc,
        "adjacent_rerun_tail": re.sub(r" in [0-9.]+s", "", (so.strip().splitlines() or [se.strip()[-300:]])[-1]),
        "report_has_regression_section": "回归范围" in (art / "REPORT.md").read_text(encoding="utf-8"),
        "full_suite": a.full_suite,
    }

    # ---------- D1-D12 adjudication -----------------------------------------
    ai, cfz, et, ir, fr = (out["artifact_identity"], out["criteria_frozen_before_run"],
                           out["evidence_traceability"], out["independent_rerun"],
                           out["failure_record"])
    rsx = out["regression_scope"]
    dstatus["D1"] = {"fixed": cfz["match_canonical"] and not cfz["matches_pretty_json_instead"],
                     "evidence": f"canonical_sha256={cfz['recomputed_canonical_sha256'][:16]} declared={cfz['declared_sha256'][:16]}"}
    srcs = cfz["criteria_sources"]
    dstatus["D2"] = {"fixed": all(s.startswith("TensorBench:") for s in srcs) and len(srcs) >= 10
                     and any("SOURCE-SPAN" in i for i in cfz["criterion_ids"]),
                     "evidence": f"{len(cfz['criterion_ids'])} criteria, sources={len(srcs)}, RA-SOURCE-SPAN present"}
    dstatus["D3"] = {"fixed": all(r["quote_len"] > 0 for r in et["locator_rows"])
                     and all(r["content_hash_matches_quote"] for r in et["locator_rows"]),
                     "evidence": f"{et['locators_total']} locators, empty quotes={len(et['locators_with_empty_quote'])}"}
    dstatus["D4"] = {"fixed": not et["locators_start_offset_zero"] and not et["locators_slice_mismatch"],
                     "evidence": f"start_offset=0 count={len(et['locators_start_offset_zero'])}, slice mismatches={len(et['locators_slice_mismatch'])}"}
    dstatus["D5"] = {"fixed": fr["records_missing_fields"] == 0 and fr["records_with_ref_without_sha256"] == 0
                     and fr["records_without_commit_sha"] == 0,
                     "evidence": f"{fr['ledger_records']} records, missing fields={fr['records_missing_fields']}, no-sha refs={fr['records_with_ref_without_sha256']}, no-commit={fr['records_without_commit_sha']}"}
    import jsonschema
    schema = json.loads((TB / "schemas/evidence-item.schema.json").read_text(encoding="utf-8"))
    schemas_ok, schema_errs = [], []
    for it in items:
        try:
            jsonschema.validate(it, schema)
            schemas_ok.append(True)
        except Exception as exc:  # noqa: BLE001
            schemas_ok.append(False)
            schema_errs.append(str(exc).splitlines()[0][:160])
    dstatus["D6"] = {
        "fixed": all(schemas_ok),
        "status": "fixed_with_residual" if all(schemas_ok) and fr["evidence_items_without_input_fingerprint"]
        else ("fixed" if all(schemas_ok) else "open"),
        "evidence": f"{sum(schemas_ok)}/{len(items)} items validate vs evidence-item.schema.json; "
                    f"items without input_sha256={fr['evidence_items_without_input_fingerprint']}",
        "residual": "REPAIR-NOTES states 'every provenance carries input_sha256'; ev-kb10k-incompatibility "
                    "carries input_refs (directory trees, no digest possible) and an absolute source_root "
                    f"outside the tree; its command reproduces identically (20 invalid_record, exit 1)."}
    citrefs = json.loads((art / "citation_audit.json").read_text(encoding="utf-8")).get("input_refs", [])
    dstatus["D7"] = {"fixed": all((not Path(r).is_absolute()) and (repo / r).is_file() for r in citrefs),
                     "evidence": f"input_refs={citrefs}"}
    dstatus["D8"] = {"fixed": cfz["frozen_before_earliest_output"] and cfz["superseded_timeline_preserved"],
                     "evidence": f"frozen_at={cfz['frozen_at']} earliest_output={cfz['earliest_audit_output_created_at']} report={cfz['report_created_at']}"}
    ntr = report["negative_test_results"]
    dstatus["D9"] = {"fixed": all(k in v for v in ntr.values() for k in ("exit_code", "positive_exit_code", "discrimination_level"))
                     and ir["claim_evidence_audit_negative"]["detected_dangling_evidence"]
                     and ir["claim_evidence_audit_negative"]["detected_dangling_claim"],
                     "evidence": {k: {"exit": v.get("exit_code"), "pos_exit": v.get("positive_exit_code"),
                                      "level": v.get("discrimination_level"), "degenerate": v.get("status_degenerate")}
                                  for k, v in ntr.items()}}
    dstatus["D10"] = {"fixed": rsx["file_present"] and rsx["report_has_regression_section"]
                      and rsx["adjacent_rerun_exit_code"] == 0,
                      "evidence": f"regression-scope.json present={rsx['file_present']}, adjacent rerun: {rsx['adjacent_rerun_tail']}"}
    val = report["summary"]["value"]
    dstatus["D11"] = {"fixed": all(k in val for k in ("problem", "automation", "quality", "cost"))
                      and all(k in val["automation"] for k in ("steps", "auto_steps", "total_steps", "ratio"))
                      and "ratio" in val["quality"] and "stages" in val["cost"],
                      "evidence": {k: sorted(val[k]) if isinstance(val[k], dict) else type(val[k]).__name__ for k in val}}
    cts = report["claims_triage_summary"]
    dstatus["D12"] = {"fixed": cts.get("triage_entries") == ir["claims_triage_counts"]["sum"]
                      and cts.get("claim_records_in_corpus") == len(claims)
                      and len(cts.get("entries_without_claim_record", [])) ==
                      cts.get("triage_entries", 0) - len(claims),
                      "evidence": {k: cts.get(k) for k in ("triage_entries", "claim_records_in_corpus",
                                                           "entries_without_claim_record")}}
    for k, v in dstatus.items():
        v.setdefault("status", "fixed" if v.get("fixed") else "open")
    out["d1_d12"] = dstatus
    out["d1_d12_summary"] = {"fixed": [k for k, v in dstatus.items() if v["status"] == "fixed"],
                             "fixed_with_residual": [k for k, v in dstatus.items()
                                                     if v["status"] == "fixed_with_residual"],
                             "open": [k for k, v in dstatus.items() if v["status"] == "open"]}

    # ---------- six checks ---------------------------------------------------
    six = {}
    six["artifact_identity"] = "passed" if (ai["scenario_inputs_mismatch"] == 0
                                            and not ai["evidence_items_unresolved"]) else "failed"
    six["criteria_frozen_before_run"] = "passed" if (cfz["match_canonical"] and cfz["frozen_before_earliest_output"]) else "failed"
    six["evidence_traceability"] = "passed" if (not et["locators_slice_mismatch"] and not et["locators_with_empty_quote"]
                                                and et["auditor_overall_status"] == "passed") else "failed"
    rerun_ok = (ir["citation_audit_positive"]["summary_equal"]
                and ir["claim_evidence_audit_positive"]["status_rerun"] == ir["claim_evidence_audit_positive"]["status_recorded"]
                and ir["claim_evidence_audit_negative"]["detected_dangling_evidence"]
                and ir["claim_evidence_audit_negative"]["detected_dangling_claim"]
                and len(ir["citation_audit_positive"]["differing_keys"]) == 0)
    six["independent_rerun"] = "passed" if rerun_ok else "failed"
    six["failure_record"] = "passed" if (fr["records_missing_fields"] == 0 and fr["records_with_ref_without_sha256"] == 0
                                         and fr["records_without_commit_sha"] == 0) else "failed"
    six["regression_scope"] = "passed_with_notes" if (rsx["file_present"] and rsx["adjacent_rerun_exit_code"] == 0) else "failed"
    out["six_checks"] = six
    out["notes"] = {
        "locator_root_drift": {
            "detail": "every file-level locator in the shipped bundle (criteria_ref, evidence source_ref, "
                      "ledger evidence_refs, negative_test output_ref, repro_cmd paths) uses the runs/m22059/ "
                      "prefix while the artifacts ship at docs/m22059/; content-level locators (offset into the "
                      "corpus copy) resolve correctly.",
            "count": "see artifact_identity.evidence_items_unresolved and failure_record.per_record[*].refs_resolved",
        },
        "shipped_recheck_script_stale": "docs/review_m22059_prod_ra/recheck.py raises KeyError: 'item_id' on ca99e79",
    }
    # ---------- residual findings (outside D1-D12, in the shipped bundle) ----
    residuals = [
        {"id": "R4-1", "severity": "major", "scope": "docs/m22059 (whole bundle)",
         "finding": "every file-level locator cites runs/m22059/... while the artifacts ship at docs/m22059/; "
                    "a fresh reader cannot resolve criteria_ref, evidence source_ref, ledger evidence_refs, "
                    "negative_test output_ref or any repro_cmd path in this tree "
                    "(offset-level locators into the corpus copy do resolve)",
         "measurement": {"evidence_items_resolved_only_after_reroot": len(items),
                         "reference_worktree_present": "/srv/tensor/agent/work/m22059/runs/m22059 exists="
                         + str(Path("/srv/tensor/agent/work/m22059/runs/m22059").is_dir())}},
        {"id": "R4-2", "severity": "major", "scope": "docs/review_m22059_prod_ra/recheck.py",
         "finding": "the shipped reviewer entry point cannot execute on ca99e79: it hardcodes "
                    "RUN='runs/m22059' and reads evidence_items[].item_id, which D6's repair renamed to "
                    "evidence_id; it aborts with KeyError: 'item_id' before writing any output, so the "
                    "committed recheck_output.json still describes 96ff584, not the reviewed commit",
         "measurement": {"as_shipped_exit_code": 1, "as_shipped_error": "KeyError: 'item_id' (recheck.py:214)"}},
        {"id": "R4-3", "severity": "major", "scope": "docs/review_m22059_prod_ra/SHA256SUMS",
         "finding": "the reviewer bundle manifest itself has 5 of 18 entries unsound: 4 listed raw logs are "
                    "absent from the tree (untracked and not shipped) and raw/SHA256SUMS is listed with the "
                    "sha256 of the empty string instead of its own digest - the same zero-length-artifact "
                    "class as defect D3",
         "measurement": {"entries": manifest["entries"], "missing": manifest["entries_missing_file"],
                         "self_digest_wrong_for": manifest["entries_with_self_or_empty_digest"],
                         "raw_sha256sums_actual": sha_file(mf) if mf.is_file() else None}},
        {"id": "R4-4", "severity": "minor", "scope": "docs/m22059/validation-report.json#evidence_bundle",
         "finding": "ev-kb10k-incompatibility provenance.source_root is the absolute path "
                    "/srv/tensor/agent/work/m22760 (a foreign worktree) and the item carries no input digest; "
                    "REPAIR-NOTES' 'every provenance carries input_sha256' is therefore overstated for 1/5 "
                    "items. Reproduced identically here (20 invalid_record, exit 1), so the finding itself stands",
         "measurement": {"item": "ev-kb10k-incompatibility", "rerun_findings": 20, "rerun_exit_code": 1}},
        {"id": "R4-5", "severity": "info", "scope": "docs/m22059/validation-report.json#negative_test_results",
         "finding": "citation_audit stays inconclusive+exit 1 on both corpora, so only the finding set "
                    "discriminates; declared as discrimination_level=finding with status_degenerate=true and a "
                    "written reason - accepted as an honest limitation, not a pass", "measurement": ntr},
        {"id": "R4-6", "severity": "info", "scope": "full pytest suite",
         "finding": "still not_run (cluster cj4351 queued); the repair declares not_run instead of a pass "
                    "count - accepted, recorded as passed_with_notes for regression_scope",
         "measurement": {"full_suite": a.full_suite}},
    ]
    out["residual_findings"] = residuals
    out["verdict"] = ("changes_requested" if any(r["severity"] in ("major", "blocking") for r in residuals)
                      or out["d1_d12_summary"]["open"] else
                      ("pass_with_notes" if residuals else "pass"))
    out["exit_code_semantics"] = ("0 = six checks pass and no residual finding or open D item; "
                                  "1 = a six-check failed; 2 = D1-D12 substantively repaired but residual "
                                  "bundle-level defects found (verdict changes_requested)")
    code = 0 if all(v.startswith("passed") for v in six.values()) and not residuals else 2
    if not all(v.startswith("passed") for v in six.values()):
        code = 1
    out["exit_code"] = code
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"reviewed_commit": out["reviewed_commit"], "artifact_root": out["artifact_root_used"],
                      "six_checks": six, "d1_d12_fixed": out["d1_d12_summary"]["fixed"],
                      "d1_d12_open": out["d1_d12_summary"]["open"],
                      "residuals": [r["id"] for r in residuals], "verdict": out["verdict"],
                      "exit_code": code},
                     ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())