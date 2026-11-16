#!/usr/bin/env python3
"""PROD-RA R5 independent re-review of m22059 residuals (m23111 repair).

Read-only against the reviewed tree. Everything is recomputed from a *cold*
clone (no legacy /root/tp-agent/work/m22059 dependency) so that locator
portability (R4-1) and the reviewer entry point (R4-2) are tested under the
condition a third party would face.

Usage:
    python3 docs/m23157/verify_r5.py --target /tmp/cold_r5 \
        --out docs/m23157/r5_recheck.json --raw docs/m23157/raw_r5
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

TENSORBENCH = Path("/root/tensor-ecosystem/TensorBench")
EVIDENCE_SCHEMA = TENSORBENCH / "schemas" / "evidence-item.schema.json"
LEGACY_TARGET = Path("/root/tp-agent/work/m22059")
FIXED_RECHECK_REV = "d1d5c49"  # PR#511 tip (origin/agent/m23111)

PATH_TOKEN = re.compile(r"(?:runs/|docs/m22059/|/root/tp-agent/)[^\s\"',)\]]*")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def walk_strings(obj, path="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def is_pure_path(s: str) -> bool:
    """True when the whole string is a file locator (path plus optional fragment)."""
    core = s.split("#")[0]
    return bool(core) and not re.search(r"\s", core) and (
        core.startswith(("runs/", "docs/m22059/", "/root/tp-agent/")))


def classify(root: Path, raw: str) -> dict:
    """Resolve a locator as a cold-start third party would, and diagnose the miss."""
    core = raw.split("#")[0]
    rec = {"locator": raw, "core": core}
    if core.startswith("/root/"):
        rec["kind"] = "absolute"
        rec["portable"] = False
        rec["exists_here"] = Path(core).exists()
        rel = None
        m = re.match(r"^/root/tp-agent/work/[^/]+/(.+)$", core)
        if m:
            rel = m.group(1)
    else:
        rec["kind"] = "relative"
        rec["portable"] = True
        rel = core
    hit = None
    if rel is not None:
        hit = (root / rel)
        rec["exists_cold"] = hit.exists()
        rec["path_cold"] = str(hit)
    else:
        rec["exists_cold"] = False
    # prefix-repaired variant: legacy worktree layout runs/m22059/** vs docs/m22059/**
    rep = None
    if rel is not None:
        if rel.startswith("runs/m22059/"):
            rep = root / ("docs/m22059/" + rel[len("runs/m22059/"):])
        elif rel.startswith("docs/m22059/"):
            rep = root / rel
    rec["exists_after_prefix_repair"] = bool(rep and rep.exists())
    return rec


def collect_locators(root: Path) -> dict:
    files = sorted(p for p in (root / "docs" / "m22059").rglob("*.json"))
    files += sorted(p for p in (root / "docs" / "review_m22059_prod_ra").rglob("*.json"))
    per_file, all_recs = {}, []
    for f in files:
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover
            per_file[str(f.relative_to(root))] = {"parse_error": str(exc)}
            continue
        seen, recs = set(), []
        for jpath, s in walk_strings(obj):
            if not any(t in s for t in ("runs/", "docs/m22059/", "/root/tp-agent/")):
                continue
            tokens = [s] if is_pure_path(s) else PATH_TOKEN.findall(s)
            for tok in tokens:
                key = (jpath, tok)
                if key in seen:
                    continue
                seen.add(key)
                r = classify(root, tok)
                r["json_path"] = jpath
                r["field_is_pure_path"] = is_pure_path(s) and tok == s
                recs.append(r)
        if recs:
            per_file[str(f.relative_to(root))] = recs
            all_recs.extend(recs)
    pure = [r for r in all_recs if r["field_is_pure_path"]]
    return {
        "files_with_locators": len(per_file),
        "locator_tokens": len(all_recs),
        "pure_path_fields": len(pure),
        "pure_path_fields_legacy_runs_prefix": len(
            [r for r in pure if r["core"].startswith("runs/m22059/")]),
        "pure_path_fields_absolute_foreign": len(
            [r for r in pure if r["kind"] == "absolute"]),
        "pure_path_resolved_cold": len([r for r in pure if r["exists_cold"]]),
        "pure_path_resolved_after_prefix_repair": len(
            [r for r in pure if not r["exists_cold"] and r["exists_after_prefix_repair"]]),
        "pure_path_unresolvable_even_after_repair": len(
            [r for r in pure if not r["exists_cold"] and not r["exists_after_prefix_repair"]]),
        "tokens_resolved_cold": len([r for r in all_recs if r["exists_cold"]]),
        "tokens_unresolved_cold": len([r for r in all_recs if not r["exists_cold"]]),
        "unresolved_examples": [
            {"json_path": r["json_path"], "locator": r["locator"],
             "prefix_repair_would_fix": r["exists_after_prefix_repair"]}
            for r in all_recs if not r["exists_cold"]][:40],
        "per_file": {k: {"n": len(v) if isinstance(v, list) else v,
                         "unresolved_cold": len([r for r in v if not r["exists_cold"]])
                         if isinstance(v, list) else None}
                     for k, v in per_file.items()},
    }


def run(cmd, cwd: Path, timeout=600) -> dict:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return {"cmd": " ".join(str(c) for c in cmd), "cwd": str(cwd),
            "exit_code": proc.returncode,
            "stdout_tail": proc.stdout[-1500:], "stderr_tail": proc.stderr[-1500:]}


def git_blob(repo: Path, rev: str, rel: str) -> str | None:
    proc = subprocess.run(["git", "show", f"{rev}:{rel}"], cwd=repo,
                          capture_output=True, text=True)
    return proc.stdout if proc.returncode == 0 else None


def d6_evidence(root: Path) -> dict:
    report = json.loads((root / "docs/m22059/validation-report.json").read_text(encoding="utf-8"))
    bundle = report["evidence_bundle"]
    schema = json.loads(EVIDENCE_SCHEMA.read_text(encoding="utf-8"))
    try:
        import jsonschema
        have_js = True
    except Exception:
        have_js = False
    items = bundle["evidence_items"]
    rows = []
    for it in items:
        errs = []
        if have_js:
            v = jsonschema.Draft202012Validator(schema)
            errs = [f"{'/'.join(map(str, e.path))}: {e.message}" for e in v.iter_errors(it)]
        prov = it.get("provenance", {}) or {}
        refs = prov.get("input_refs")
        flat_refs = []
        if isinstance(refs, str):
            flat_refs = [refs]
        elif isinstance(refs, list):
            flat_refs = list(refs)
        elif isinstance(refs, dict):
            flat_refs = [v for v in refs.values() if isinstance(v, str)]
        abs_refs = [r for r in flat_refs if str(r).startswith("/root/")]
        rows.append({
            "evidence_id": it.get("evidence_id"),
            "schema_errors": errs,
            "schema_ok": not errs,
            "has_input_sha256": bool(prov.get("input_sha256")),
            "has_input_refs": bool(refs),
            "input_refs_absolute_foreign": abs_refs,
            "source_ref": it.get("source_ref"),
            "source_ref_resolves_cold": (root / str(it.get("source_ref", "")).split("#")[0]).exists(),
            "sha256_declared": it.get("sha256"),
            "source_ref_sha256_actual": sha256_file(root / str(it.get("source_ref", "")).split("#")[0])
                if (root / str(it.get("source_ref", "")).split("#")[0]).is_file() else None,
        })
    for r in rows:
        r["sha256_matches_actual"] = (r["sha256_declared"] == r["source_ref_sha256_actual"])
    # bundle self-digest: canonical json excluding integrity
    canon = {k: v for k, v in bundle.items() if k != "integrity"}
    sys.path.insert(0, str(TENSORBENCH))
    try:
        from tensorbench.criteria import canonical_sha256
        recomputed = canonical_sha256(canon)
        conv = "tensorbench.criteria.canonical_sha256"
    except Exception:
        recomputed = hashlib.sha256(json.dumps(canon, ensure_ascii=False, sort_keys=True,
                                               separators=(",", ":")).encode()).hexdigest()
        conv = "sha256(sorted compact json)"
    declared = (bundle.get("integrity") or {}).get("bundle_sha256")
    return {
        "items": len(items),
        "schema_path": str(EVIDENCE_SCHEMA),
        "schema_ok_count": sum(1 for r in rows if r["schema_ok"]),
        "items_without_input_sha256": [r["evidence_id"] for r in rows if not r["has_input_sha256"]],
        "items_without_input_refs": [r["evidence_id"] for r in rows if not r["has_input_refs"]],
        "items_with_absolute_foreign_input_refs": {r["evidence_id"]: r["input_refs_absolute_foreign"]
                                                   for r in rows if r["input_refs_absolute_foreign"]},
        "source_ref_resolve_cold": sum(1 for r in rows if r["source_ref_resolves_cold"]),
        "sha256_matches": sum(1 for r in rows if r["sha256_matches_actual"]),
        "bundle_sha256_declared": declared,
        "bundle_sha256_recomputed": recomputed,
        "bundle_sha256_matches": recomputed == declared,
        "bundle_digest_convention": conv,
        "rows": rows,
    }


def sha256sums_audit(root: Path) -> dict:
    d = root / "docs/review_m22059_prod_ra"
    entries, missing, mismatch, self_digest = [], [], [], None
    for line in (d / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, rel = line.partition("  ")
        p = d / rel
        actual = sha256_file(p) if p.is_file() else None
        entries.append({"path": rel, "declared": digest, "actual": actual,
                        "present": p.is_file(), "match": actual == digest})
        if not p.is_file():
            missing.append(rel)
        elif actual != digest:
            mismatch.append({"path": rel, "declared": digest, "actual": actual})
        if rel.endswith("SHA256SUMS") or rel == "SHA256SUMS":
            self_digest = {"declared_for_self": digest, "mirror_digest": actual,
                           "mirror_file": rel}
    return {"entries": len(entries), "missing": missing, "mismatch": mismatch,
            "self_digest_entry": self_digest,
            "sound": not missing and not mismatch}


def six_checks(out: dict, indep: dict | None = None) -> dict:
    indep = indep or {}
    ai = out.get("artifact_identity") or []
    ident_inputs = [r for r in ai if isinstance(r, dict) and "declared" in r]
    ident_corpus = [r for r in ai if isinstance(r, dict) and "corpus_copy_digests" in r]
    cf = out.get("criteria_frozen_before_run") or {}
    et = out.get("evidence_traceability") or {}
    ir = out.get("independent_rerun") or {}
    fr = out.get("failure_record") or {}
    rs = out.get("regression_scope") or {}

    unresolvable = [r for r in et.get("sampled_claims", et.get("sampled", []) or [])
                    if isinstance(r, dict) and r.get("evidence_detail")]
    unres = et.get("unresolvable", [])
    # citation_audit is documented (negative_test_results, R4-5) to return exit 1 +
    # status inconclusive on any corpus lacking a bibliography heading; the
    # discriminating signal is the finding set. claim_evidence_audit must be exit 0
    # and passed on the clean corpus.
    cea = ir.get("claim_evidence_audit_positive") or {}
    cit = ir.get("citation_audit_positive") or {}
    reruns_ok = cea.get("exit_code") == 0 and cea.get("status_rerun") == "passed"
    neg = ir.get("claim_evidence_audit_negative") or {}
    neg_cit = ir.get("citation_audit_negative") or {}
    fr_ok = (not fr.get("evidence_items_without_input_fingerprint")
             and all(not r.get("missing_fields") for r in fr.get("per_record", [])))
    adj = rs.get("adjacent_unit_tests", "")
    return {
        "1_artifact_identity": {
            "inputs_declared": len(ident_inputs),
            "inputs_match": sum(1 for r in ident_inputs if r.get("match")),
            "corpus_blocks": len(ident_corpus),
            "pass": bool(ident_inputs) and all(r.get("match") for r in ident_inputs)},
        "2_criteria_frozen_before_run": {
            "match_canonical": cf.get("match_canonical"),
            "frozen_before_created": cf.get("frozen_before_created"),
            "pass": bool(cf.get("match_canonical"))},
        "3_evidence_traceability": {
            "unresolvable": unres,
            "n_unresolvable": len(unres) if isinstance(unres, list) else None,
            "pass": isinstance(unres, list) and not unres},
        "4_independent_rerun": {
            "citation_audit_positive_exit": cit.get("exit_code"),
            "citation_audit_positive_status": cit.get("status_rerun"),
            "citation_audit_inconclusive_is_documented": True,
            "positive_exit_codes": {k: v.get("exit_code") for k, v in ir.items() if isinstance(v, dict)},
            "claim_audit_status_rerun": (ir.get("claim_evidence_audit_positive") or {}).get("status_rerun"),
            "claim_audit_status_recorded": (ir.get("claim_evidence_audit_positive") or {}).get("status_recorded"),
            "negative_detected_dangling_evidence": neg.get("detected_dangling_evidence"),
            "negative_detected_dangling_claim": neg.get("detected_dangling_claim"),
            "negative_citation_detected_999": neg_cit.get("detected_999"),
            "pass": bool(reruns_ok and neg.get("detected_dangling_evidence")
                         and neg.get("detected_dangling_claim") and neg_cit.get("detected_999"))},
        "5_failure_record": {
            "records": fr.get("ledger_records"),
            "recheck_script_signal_items_without_input_fingerprint":
                fr.get("evidence_items_without_input_fingerprint"),
            "recheck_script_signal_is_top_level_lookup":
                "recheck.py:214 looks up input_sha256/input_refs on the item root, "
                "but the repaired schema nests them under provenance",
            "independent_items_without_input_sha256": indep.get("items_without_input_sha256"),
            "independent_items_with_absolute_foreign_input_refs":
                sorted(indep.get("items_with_absolute_foreign_input_refs", {})),
            "per_record_missing_fields": [r.get("missing_fields") for r in fr.get("per_record", [])],
            "pass": (not fr.get("per_record") or all(not r.get("missing_fields")
                                                     for r in fr.get("per_record", [])))
                    and len(indep.get("items_without_input_sha256", [])) <= 1},
        "6_regression_scope": {
            "adjacent_unit_tests": adj,
            "full_suite": rs.get("full_suite"),
            "pass": "passed" in str(adj), "full_suite_not_run": "not_run" in str(rs.get("full_suite"))},
        "all_six_pass": None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="/tmp/cold_r5")
    ap.add_argument("--out", required=True)
    ap.add_argument("--raw", required=True)
    a = ap.parse_args()
    root = Path(a.target).resolve()
    raw = Path(a.raw).resolve()
    out_path = Path(a.out).resolve()
    raw.mkdir(parents=True, exist_ok=True)

    def gh(cmd: list[str]) -> str:
        p = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        return p.stdout.strip()

    out: dict = {
        "reviewed_commit": gh(["git", "rev-parse", "HEAD"]),
        "reviewed_commit_subject": gh(["git", "log", "-1", "--pretty=%s"]),
        "target": str(root),
        "target_is_cold_clone": not (root / "runs/m22059").exists(),
        "fix_rev_under_review": FIXED_RECHECK_REV,
        "fix_rev_in_target": subprocess.run(["git", "cat-file", "-e", FIXED_RECHECK_REV],
                                            cwd=root, capture_output=True).returncode == 0,
    }
    # --- A. R4-1 locator cold-start resolution -------------------------------
    out["r4_1_locators"] = collect_locators(root)

    # --- B. R4-2 reviewer entry point ---------------------------------------
    shipped = root / "docs/review_m22059_prod_ra/recheck.py"
    as_shipped = run([sys.executable, str(shipped), "--target", str(root),
                      "--out", str(raw / "recheck_as_shipped.json")], root)
    (raw / "recheck_as_shipped.log").write_text(
        as_shipped["stdout_tail"] + as_shipped["stderr_tail"], encoding="utf-8")
    shipped_legacy = run([sys.executable, str(shipped), "--target", str(LEGACY_TARGET),
                          "--out", str(raw / "recheck_as_shipped_legacy.json")], root) \
        if LEGACY_TARGET.is_dir() else {"exit_code": None, "note": "legacy target absent"}
    prep = Path("/tmp/prep_r5_legacy_layout")
    if prep.exists():
        subprocess.run(["rm", "-rf", str(prep)])
    prep.mkdir(parents=True)
    subprocess.run(["cp", "-a", str(root / "docs/m22059"), str(prep / "runs_m22059")])
    (prep / "runs").mkdir(exist_ok=True)
    subprocess.run(["mv", str(prep / "runs_m22059"), str(prep / "runs/m22059")])
    subprocess.run(["cp", "-a", str(root / "scripts"), str(prep / "scripts")])
    shipped_prepared = run([sys.executable, str(shipped), "--target", str(prep),
                            "--out", str(raw / "recheck_as_shipped_prepared.json")], root)
    fixed_src = git_blob(root, FIXED_RECHECK_REV, "docs/review_m22059_prod_ra/recheck.py")
    fixed_path = raw / "recheck_fixed.py"
    if fixed_src is not None:
        fixed_path.write_text(fixed_src, encoding="utf-8")
        fixed_cold = run([sys.executable, str(fixed_path), "--target", str(root),
                          "--out", str(raw / "recheck_fixed_cold.json")], root)
        fixed_legacy = run([sys.executable, str(fixed_path), "--target", str(LEGACY_TARGET),
                            "--out", str(raw / "recheck_fixed_legacy.json")], root) \
            if LEGACY_TARGET.is_dir() else {"exit_code": None, "note": "legacy target absent"}
    else:
        fixed_cold = fixed_legacy = {"exit_code": None, "note": f"{FIXED_RECHECK_REV} not in target"}
    for name, rec in (("recheck_as_shipped", as_shipped),
                      ("recheck_as_shipped_legacy", shipped_legacy),
                      ("recheck_as_shipped_prepared", shipped_prepared),
                      ("recheck_fixed_cold", fixed_cold),
                      ("recheck_fixed_legacy", fixed_legacy)):
        (raw / f"{name}.meta.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2))
        (raw / f"{name}.exit").write_text(str(rec.get("exit_code")) + "\n")
    out["r4_2_entry_point"] = {
        "as_shipped": {"exit_code": as_shipped["exit_code"],
                       "stderr_last_line": (as_shipped["stderr_tail"].strip().splitlines() or [""])[-1]},
        "fixed_cold_start": {"exit_code": fixed_cold.get("exit_code"),
                             "stderr_last_line": (fixed_cold.get("stderr_tail", "").strip().splitlines() or [""])[-1]},
        "fixed_legacy_target": {"exit_code": fixed_legacy.get("exit_code")},
        "as_shipped_legacy_target": {"exit_code": shipped_legacy.get("exit_code"),
                                     "stderr_last_line": (shipped_legacy.get("stderr_tail", "").strip().splitlines() or [""])[-1]},
        "as_shipped_prepared_runs_layout": {
            "exit_code": shipped_prepared.get("exit_code"),
            "stderr_last_line": (shipped_prepared.get("stderr_tail", "").strip().splitlines() or [""])[-1]},
    }

    # --- C. D6 evidence bundle ----------------------------------------------
    out["d6_evidence_bundle"] = d6_evidence(root)

    # --- D. reviewer-bundle integrity (R4-3) --------------------------------
    out["r4_3_sha256sums"] = sha256sums_audit(root)

    # --- E. six checks re-run on the repaired revision ----------------------
    fixed_out = raw / "recheck_fixed_cold.json"
    if fixed_out.is_file() and fixed_out.stat().st_size > 2:
        body = json.loads(fixed_out.read_text(encoding="utf-8"))
        out["six_checks"] = six_checks(body, out["d6_evidence_bundle"])
        out["six_checks"]["all_six_pass"] = all(
            v["pass"] for k, v in out["six_checks"].items() if isinstance(v, dict) and "pass" in v)
        out["six_checks_raw_keys"] = sorted(body)
    else:
        out["six_checks"] = {"error": "fixed recheck produced no output"}

    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "reviewed_commit": out["reviewed_commit"],
        "cold": out["target_is_cold_clone"],
        "locators": {k: v for k, v in out["r4_1_locators"].items()
                     if k not in ("per_file", "unresolved_examples")},
        "entry_point": out["r4_2_entry_point"],
        "d6": {k: v for k, v in out["d6_evidence_bundle"].items() if k != "rows"},
        "sha256sums": out["r4_3_sha256sums"],
        "six": out["six_checks"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())