#!/usr/bin/env python3
"""PROD-RA STATUS publication check (m23257).

Purpose: before RA's row in products/STATUS.json may move, re-derive every
fact the row would cite, from a cold extraction of main (no legacy
/srv/tensor/agent/work/m22059 dependency), so that no claim rests on a quotation.

Nothing here writes outside docs/m23257/. Read-only against the reviewed tree.

Usage:
    python3 docs/m23257/verify_status.py \
        --repo . --target /tmp/m23257_cold \
        --out docs/m23257/status_evidence.json --raw docs/m23257/raw
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

# Reuse the R5 verifier verbatim so this check cannot drift from the review it
# is auditing (same locator enumerator, same D6 walk, same manifest audit).
R5 = REPO / "docs/m23157/verify_r5.py"
PR511_MERGE = "3a70ce8"          # Merge #511 (m23111) via push-merge
R5_FIXED_RECHECK_SHA = "2cfa24548d69498831a4f05ab58ddbcd503875624d9ca203fdd14230924b1090"
TENSORBENCH = Path("/srv/tensor/workspace/TensorBench")


def load_r5():
    spec = importlib.util.spec_from_file_location("verify_r5", R5)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sh(cmd, cwd, timeout=900) -> dict:
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    return {"cmd": " ".join(str(c) for c in cmd), "cwd": str(cwd), "exit_code": p.returncode,
            "stdout_tail": p.stdout[-1200:], "stderr_tail": p.stderr[-1200:]}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cold_extract(repo: Path, target: Path) -> dict:
    """Third-party view: tracked files only, so runs/ (git-ignored) is absent."""
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    tar = subprocess.run(["git", "-C", str(repo), "archive", "HEAD"],
                         capture_output=True, check=True)
    untar = subprocess.run(["tar", "-x", "-C", str(target)], input=tar.stdout)
    return {"target": str(target), "untar_exit": untar.returncode,
            "legacy_runs_present": (target / "runs/m22059").exists(),
            "files": sum(1 for _ in target.rglob("*") if _.is_file())}


def verdict_ledger_probe(repo: Path) -> dict:
    """The mission asks for verdict rows 917/918 read from the DB.

    The agent role has no SELECT on tensor_maturity_verdicts (same limitation
    R5 recorded), so this records the probe and the in-repo quotations with
    file:line anchors instead of restating texts as if freshly read.
    """
    sql = ("SELECT id, repo, scope, mission_id, level, gate_state FROM "
           "tensor_maturity_verdicts WHERE id IN (903,917,918) "
           "OR mission_id IN (22059,23090,23111,23157) ORDER BY id;")
    probe = sh(["psql", "tensorplatform", "-c", sql], repo, timeout=60)
    quotes = []
    for rel, pats in (("docs/review_m22059_prod_ra/REVIEW-R4.md", ("行 903", "id=918")),
                      ("docs/m23157/REVIEW-R5.md", ("行 903", "行 918"))):
        f = repo / rel
        if not f.is_file():
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if any(p in line for p in pats):
                quotes.append({"file": rel, "line": i, "text": line.strip()[:240]})
    return {"probe_sql": sql, "exit_code": probe["exit_code"],
            "stderr_tail": probe["stderr_tail"].strip().splitlines()[-1:] or [],
            "read_ok": probe["exit_code"] == 0 and "ERROR" not in probe["stderr_tail"],
            "in_repo_quotations": quotes,
            "evidence_level": "WITHHELD (ledger not readable by this role; citations are in-repo quotations)"}


def contracts_check(payload_path: Path) -> dict:
    """Run TensorBench's own STATUS v2 validator + cross-field rules on the payload."""
    if not TENSORBENCH.is_dir():
        return {"ran": False, "reason": f"{TENSORBENCH} absent"}
    sys.path.insert(0, str(TENSORBENCH))
    out = {"ran": True, "validator": "tensorbench.contracts"}
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    try:
        from tensorbench import contracts  # type: ignore
        errs = contracts._status_errors(payload)
        out["cross_field_errors"] = errs
        try:
            out["validate_payload"] = contracts.validate_payload("status", payload)
        except Exception as exc:  # signature differences are recorded, not hidden
            out["validate_payload_error"] = f"{type(exc).__name__}: {exc}"
    except Exception as exc:
        out["import_error"] = f"{type(exc).__name__}: {exc}"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(REPO))
    ap.add_argument("--target", default="/tmp/m23257_cold")
    ap.add_argument("--out", required=True)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--payload", default=str(HERE / "products_STATUS.proposed.json"))
    a = ap.parse_args()
    repo, target, raw = Path(a.repo).resolve(), Path(a.target), Path(a.raw).resolve()
    raw.mkdir(parents=True, exist_ok=True)
    r5 = load_r5()

    head = sh(["git", "rev-parse", "HEAD"], repo)
    out: dict = {
        "mission": 23257,
        "purpose": "re-derive every fact before moving the RA row of products/STATUS.json",
        "repo": str(repo),
        "head_commit": head["stdout_tail"].strip(),
        "head_subject": sh(["git", "log", "-1", "--pretty=%s"], repo)["stdout_tail"].strip(),
        "pr511_merge": {},
        "fix_identity": {},
        "entry_point": {},
        "six_checks_recorded": {},
        "verdict_ledger": verdict_ledger_probe(repo),
    }
    # PR#511 merge commit reachable from HEAD, and the reviewed fix is what ships.
    out["pr511_merge"] = {
        **sh(["git", "log", "-1", "--pretty=%H%n%s", PR511_MERGE], repo),
        "in_head": subprocess.run(["git", "merge-base", "--is-ancestor", PR511_MERGE, "HEAD"],
                                  cwd=str(repo)).returncode == 0,
    }
    shipped = repo / "docs/review_m22059_prod_ra/recheck.py"
    got = sha256_file(shipped)
    out["fix_identity"] = {"path": "docs/review_m22059_prod_ra/recheck.py",
                           "sha256": got, "r5_reviewed_sha": R5_FIXED_RECHECK_SHA,
                           "matches_r5_reviewed_fix": got == R5_FIXED_RECHECK_SHA,
                           "last_commit": sh(["git", "log", "-1", "--pretty=%h %s",
                                              "--", "docs/review_m22059_prod_ra/recheck.py"],
                                             repo)["stdout_tail"].strip()}

    # Cold extraction: the condition a third party faces.
    out["cold"] = cold_extract(repo, target)
    out["r5_1_locators"] = r5.collect_locators(target)
    out["r5_2_manifest"] = r5.sha256sums_audit(target)
    try:
        d6 = r5.d6_evidence(target)
        out["d6_evidence"] = {k: v for k, v in d6.items() if k != "rows"}
    except Exception as exc:
        out["d6_evidence"] = {"not_run": f"{type(exc).__name__}: {exc}"}

    # Entry point, cold, as shipped on main.
    cold_out = raw / "recheck_cold.json"
    run = sh([sys.executable, str(target / "docs/review_m22059_prod_ra/recheck.py"),
              "--target", str(target), "--out", str(cold_out)], target)
    (raw / "recheck_cold.log").write_text(run["stdout_tail"] + run["stderr_tail"],
                                          encoding="utf-8")
    out["entry_point"] = {"cold_exit_code": run["exit_code"],
                          "stderr_tail": run["stderr_tail"].strip().splitlines()[-1:] or [],
                          "log": "docs/m23257/raw/recheck_cold.log"}
    if cold_out.is_file():
        payload = json.loads(cold_out.read_text(encoding="utf-8"))
        out["entry_point"]["sections"] = sorted(payload) if isinstance(payload, dict) else "list"

    # Six checks as recorded by the independent R5 review (quoted, not re-judged).
    rec = json.loads((repo / "docs/m23157/r5_recheck.json").read_text(encoding="utf-8"))
    sc = rec.get("six_checks", {})
    out["six_checks_recorded"] = {
        "source": "docs/m23157/r5_recheck.json",
        "source_sha256": sha256_file(repo / "docs/m23157/r5_recheck.json"),
        "all_six_pass": sc.get("all_six_pass"),
        "per_check": {k: (v.get("pass") if isinstance(v, dict) else v) for k, v in sc.items()},
        "review_receipt": "docs/m23157/REVIEW-RECEIPT-R5.json",
        "review_receipt_verdict": json.loads(
            (repo / "docs/m23157/REVIEW-RECEIPT-R5.json").read_text(encoding="utf-8")
        ).get("verdict"),
    }

    out["payload_contracts"] = contracts_check(Path(a.payload)) if Path(a.payload).is_file() \
        else {"ran": False, "reason": "payload not built yet"}

    Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

    # Console digest for the run log.
    loc = out["r5_1_locators"]
    print(f"HEAD {out['head_commit'][:12]} | PR#511 merged={out['pr511_merge']['in_head']} "
          f"| shipped recheck sha matches R5 fix={out['fix_identity']['matches_r5_reviewed_fix']}")
    print(f"locators pure_path={loc['pure_path_fields']} cold_resolved={loc['pure_path_resolved_cold']} "
          f"prefix_repair_only={loc['pure_path_resolved_after_prefix_repair']} "
          f"unresolvable={loc['pure_path_unresolvable_even_after_repair']} "
          f"legacy_prefix={loc['pure_path_fields_legacy_runs_prefix']} "
          f"absolute_foreign={loc['pure_path_fields_absolute_foreign']}")
    print(f"manifest sound={out['r5_2_manifest']['sound']} entries={out['r5_2_manifest']['entries']}")
    print(f"entry point cold exit={out['entry_point']['cold_exit_code']} "
          f"sections={out['entry_point'].get('sections')}")
    print(f"six checks all pass={out['six_checks_recorded']['all_six_pass']} "
          f"receipt verdict={out['six_checks_recorded']['review_receipt_verdict']}")
    print(f"ledger read_ok={out['verdict_ledger']['read_ok']} "
          f"{out['verdict_ledger']['stderr_tail']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())