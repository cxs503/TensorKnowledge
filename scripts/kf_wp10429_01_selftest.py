#!/usr/bin/env python3
"""Negative controls for scripts/kf_wp10429_01_verify.py.

A green verifier is worthless unless it goes red when the evidence is broken.  This
script copies the package's artifacts into a scratch directory, injects one defect at a
time, and asserts that the *specific* acceptance check (and only the intended one) flips
to FAIL.  Nothing in the working tree is modified.

Usage: python3 scripts/kf_wp10429_01_selftest.py
Outputs: runs/wp-10429-01/selftest.json (+ docs mirror); exit 0 iff every case behaves.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(".").resolve()
ART = "artifacts/wp-10429-01"
RUN = "runs/wp-10429-01"
DOC = "docs/kf/wp-10429-01"
SCHEMAS = "schemas"
SCRIPTS = "scripts"
WORKBOOK = ["asset_manifest.json", "kf_result.wp-10429-01.json", "verification.json",
            "report_10429.md", "report_10429.json", "kf_result.json"]
EXPECT = {
    # case -> acceptance key that must fail
    "tampered_quote": "source_locator_resolvable",
    "duplicate_asset_id": "no_duplicate_ids",
    "wrong_source_hash": "envelope_links",
    "missing_required_key": "schema_pass",
    "claim_without_evidence": "all_claims_have_evidence_or_explicit_unresolved_status",
    "manuscript_mismatch": "source_hash_matches",
}


def stage(tmp: pathlib.Path) -> None:
    for d in (ART, RUN, DOC, SCHEMAS, SCRIPTS):
        shutil.copytree(ROOT / d, tmp / d)
    for name, dest in (("asset_manifest.json", ART), ("kf_result.wp-10429-01.json", RUN),
                       ("asset_manifest.json", DOC), ("kf_result.json", DOC),
                       ("verification.json", DOC)):
        src = ROOT / dest / name
        if src.exists():
            (tmp / dest / name).write_bytes(src.read_bytes())


def run_verifier(tmp: pathlib.Path) -> tuple[dict, int]:
    p = subprocess.run([sys.executable, "scripts/kf_wp10429_01_verify.py", "--offline"],
                       cwd=tmp, capture_output=True, text=True)
    rep = json.loads((tmp / RUN / "verification.json").read_text())
    return rep, p.returncode


def edit_manifest(tmp: pathlib.Path, fn) -> None:
    for base in (ART, DOC):
        p = tmp / base / "asset_manifest.json"
        m = json.loads(p.read_text())
        fn(m)
        p.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    cases = {}

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        stage(tmp)
        rep, rc = run_verifier(tmp)
        cases["baseline"] = dict(expect_pass=True, all_pass=rep["all_pass"], exit=rc, failed=rep["failed"])

    mutators = {
        "tampered_quote": lambda m: m["assets"][3]["locator"].__setitem__(
            "quote", m["assets"][3]["locator"]["quote"].replace("0.41", "0.42", 1)),
        "duplicate_asset_id": lambda m: (m["assets"][5].__setitem__("asset_id", m["assets"][4]["asset_id"]),
                                         m["counts"].__setitem__("assets", len(m["assets"]))),
        "missing_required_key": lambda m: m.pop("integrity"),
        "claim_without_evidence": lambda m: m["claims"].append(dict(claim_id="c-test", text="unbacked")),
    }
    for case, mut in mutators.items():
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            stage(tmp)
            edit_manifest(tmp, mut)
            rep, rc = run_verifier(tmp)
            target = EXPECT[case]
            cases[case] = dict(expect_fail=target, targeted_check_failed=(target in rep["failed"]),
                               all_pass=rep["all_pass"], exit=rc, failed=rep["failed"],
                               ok=(target in rep["failed"] and rep["all_pass"] is False and rc == 1))

    # envelope hash tamper (leaves the manifest intact)
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        stage(tmp)
        for base, name in ((RUN, "kf_result.wp-10429-01.json"), (DOC, "kf_result.json")):
            p = tmp / base / name
            e = json.loads(p.read_text())
            e["provenance"]["source_hash"] = "sha256:" + "0" * 64
            p.write_text(json.dumps(e, ensure_ascii=False, indent=2) + "\n")
        rep, rc = run_verifier(tmp)
        cases["wrong_source_hash"] = dict(expect_fail="envelope_links",
                                          targeted_check_failed=("envelope_links" in rep["failed"]),
                                          all_pass=rep["all_pass"], exit=rc, failed=rep["failed"],
                                          ok=("envelope_links" in rep["failed"] and rc == 1))

    # manuscript tamper: one char changed in the local copy of the report
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        stage(tmp)
        p = tmp / RUN / "report_10429.md"
        p.write_text(p.read_text().replace("2.5 x 0.41 m", "2.5 x 0.42 m", 1))
        rep, rc = run_verifier(tmp)
        cases["manuscript_mismatch"] = dict(expect_fail="source_hash_matches",
                                            targeted_check_failed=("source_hash_matches" in rep["failed"]),
                                            all_pass=rep["all_pass"], exit=rc, failed=rep["failed"],
                                            ok=("source_hash_matches" in rep["failed"] and rc == 1))

    ok = cases["baseline"]["all_pass"] and all(v.get("ok") for k, v in cases.items() if k != "baseline")
    out = dict(package_id="wp-10429-01", report_id="10429",
               invocation="python3 scripts/kf_wp10429_01_selftest.py",
               n_cases=len(cases), all_ok=ok, cases=cases)
    for d in (RUN, DOC):
        (ROOT / d / "selftest.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: (v.get("ok", v.get("all_pass"))) for k, v in cases.items()}, indent=1))
    print("SELFTEST_OK" if ok else "SELFTEST_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())