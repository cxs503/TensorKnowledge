#!/usr/bin/env python3
"""Negative control for the wp-9840-01 gate.

A gate that always says PASS is worthless. This script mutates the accepted manifest in
several ways and asserts that the *real* predicate functions imported from
scripts/kf_verify_9840.py reject every mutant, while the pristine manifest still passes.
No file on disk is modified: mutants are built in memory.
"""
import copy
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path("scripts").resolve()))
import kf_verify_9840 as gate  # noqa: E402

ART = pathlib.Path("artifacts/wp-9840-01/asset_manifest.json")
RUN_DIR = pathlib.Path("runs/wp-9840-01")


def mutants(m, md):
    out = []

    x = copy.deepcopy(m)
    x["assets"][5]["locator"]["start_char"] += 1          # shifted span -> slice mismatch
    x["assets"][5]["locator"]["end_char"] += 1
    out.append(("span_shift_by_1_char", x))

    x = copy.deepcopy(m)
    q = x["assets"][9]["locator"]["quote"]
    x["assets"][9]["locator"]["quote"] = q.replace("|", "！", 1)   # retyped/edited quote
    out.append(("quote_edited_offline", x))

    x = copy.deepcopy(m)
    x["assets"][12]["locator"]["unique"] = False          # uniqueness claim dropped
    out.append(("unique_flag_false", x))

    x = copy.deepcopy(m)
    x["assets"][-1]["asset_id"] = x["assets"][0]["asset_id"]   # duplicate id
    out.append(("duplicate_asset_id", x))

    x = copy.deepcopy(m)
    x["assets"][0]["locator"]["end_char"] -= 1             # document locator truncated
    out.append(("document_locator_truncated", x))

    x = copy.deepcopy(m)
    x["assets"][3]["locator"]["quote"] = "这句话不在原文里"    # invented quote
    out.append(("invented_quote", x))
    return out


def main() -> int:
    m = json.loads(ART.read_text())
    md = (RUN_DIR / "report_9840.md").read_text()
    if hashlib.sha256(md.encode()).hexdigest() != gate.EXPECTED_HASH:
        print("FATAL: frozen copy does not match contract hash; control is meaningless")
        return 2

    base_bad, _ = gate.check_locators(md, m)
    base_dups = gate.check_duplicate_ids(m)
    print("control: pristine manifest -> locator_failures=%d duplicate_ids=%d (expect 0/0)"
          % (len(base_bad), len(base_dups)))
    ok = not base_bad and not base_dups

    rows = []
    for name, mut in mutants(m, md):
        bad, _ = gate.check_locators(md, mut)
        dups = gate.check_duplicate_ids(mut)
        caught = bool(bad or dups)
        ok = ok and caught
        rows.append(dict(mutant=name, caught=caught, locator_failures=len(bad),
                         duplicate_ids=dups,
                         first_reason=(bad[0]["why"] if bad else ("duplicate ids: %s" % dups if dups else None))))
        print("%-28s caught=%-5s %s" % (name, caught, rows[-1]["first_reason"]))

    payload = dict(
        control="scripts/kf_9840_negative_control.py",
        pristine_locator_failures=len(base_bad), pristine_duplicate_ids=base_dups,
        mutants=rows, all_mutants_rejected=all(r["caught"] for r in rows),
        verdict="PASS" if ok else "FAIL")
    (RUN_DIR / "negative_control.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    doc = pathlib.Path("docs/wp-9840-01")
    doc.mkdir(parents=True, exist_ok=True)
    (doc / "negative_control.json").write_text((RUN_DIR / "negative_control.json").read_text())
    print("verdict:", payload["verdict"], "->", RUN_DIR / "negative_control.json")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())