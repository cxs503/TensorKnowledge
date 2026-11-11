#!/usr/bin/env python3
"""Verify the knowledge/sediment/m2400 package.

Checks (all machine-evaluable, exit code 1 on any failure):

  C1  every claim/evidence/provenance JSON validates against its schema in schemas/
  C2  every evidence locator resolves at the pinned commit: `git show <sha>:<path>`
      sliced by start_offset..end_offset equals locator.quote, and the first quoted
      line is found by a plain `grep -F` (the command is printed for the audit log)
  C3  INDEX.md is consistent with the JSON: same number of claims, every claim id,
      every primary locator and the pinned sha appear in the table
  C4  epistemic_status is `draft` everywhere, and no review-event / promoted state
      leaked into the package (producer must not self-review)

Usage:
    python scripts/verify_sediment_m2400.py [--source-repo /root/tensor-ecosystem/TensorDG]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "knowledge" / "sediment" / "m2400"
SCHEMAS = ROOT / "schemas"
SHA = "8823a47bb0f0d23a81221c8641c59af2d02fca5d"

FAILS: list[str] = []
OKS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    (OKS if ok else FAILS).append(f"{'PASS' if ok else 'FAIL'} {name}{(' :: ' + detail) if detail else ''}")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_show(repo: Path, path: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "show", f"{SHA}:{path}"],
        check=True, capture_output=True, text=True,
    ).stdout


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", default="/root/tensor-ecosystem/TensorDG")
    args = parser.parse_args(argv)
    repo = Path(args.source_repo)

    try:
        import jsonschema
        from jsonschema import Draft202012Validator
    except ImportError:  # pragma: no cover
        print("jsonschema is required", file=sys.stderr)
        return 2

    claims = sorted(OUT.glob("claim-*.json"))
    evidences = sorted(OUT.glob("evidence-*.json"))
    provenances = sorted(OUT.glob("provenance-*.json"))
    check("package-present", bool(claims) and bool(evidences) and bool(provenances),
          f"claims={len(claims)} evidence={len(evidences)} provenance={len(provenances)}")
    check("at-least-3-claim-groups", len(claims) >= 3 and len(evidences) >= 3 and len(provenances) >= 3,
          f"{len(claims)}/{len(evidences)}/{len(provenances)}")

    # ---- C1: schemas ---------------------------------------------------------
    for name, files in (("claim-record", claims), ("evidence-record", evidences),
                        ("provenance-record", provenances)):
        schema = load(SCHEMAS / f"{name}.schema.json")
        validator = Draft202012Validator(schema)
        for f in files:
            errors = sorted(validator.iter_errors(load(f)), key=lambda e: list(e.absolute_path))
            check(f"schema:{name}:{f.name}", not errors,
                  "; ".join(f"{'/'.join(map(str, e.absolute_path))}: {e.message}" for e in errors[:3]))

    # ---- C2: quotes resolve at the pinned commit ----------------------------
    claim_ids = {load(c)["id"] for c in claims}
    evidence_ids = set()
    for f in evidences:
        ev = load(f)
        evidence_ids.add(ev["id"])
        loc = ev["locator"]
        path = loc["value"].split("/", 1)[1].rsplit(":", 1)[0]
        start, end = loc["start_offset"], loc["end_offset"]
        lines = git_show(repo, path).splitlines()
        actual = "\n".join(lines[start - 1:end]).rstrip()
        check(f"quote-slice:{f.name}", actual == loc["quote"],
              f"git show {SHA[:7]}:{path} | sed -n '{start},{end}p'")
        first = loc["quote"].splitlines()[0]
        grep = subprocess.run(
            ["git", "-C", str(repo), "show", f"{SHA}:{path}"],
            check=True, capture_output=True, text=True,
        ).stdout
        hits = [i + 1 for i, line in enumerate(grep.splitlines()) if first in line]
        check(f"quote-grep:{f.name}", start in hits,
              f"grep -Fn {first[:40]!r} -> lines {hits}")
        check(f"quote-length:{f.name}", len(loc["quote"]) >= 20, f"{len(loc['quote'])} chars")
        for ref in ev["claim_refs"]:
            check(f"evidence->claim:{f.name}", ref in claim_ids, ref)

    # ---- C3: INDEX.md consistency -------------------------------------------
    index = (OUT / "INDEX.md").read_text(encoding="utf-8")
    table_rows = [ln for ln in index.splitlines() if ln.startswith("| tkc:")]
    check("index-row-count", len(table_rows) == len(claims), f"{len(table_rows)} vs {len(claims)}")
    for f in claims:
        claim = load(f)
        row = next((r for r in table_rows if claim["id"] in r), None)
        check(f"index-claim:{claim['id']}", row is not None)
        if row:
            check(f"index-sha:{claim['id']}", SHA[:7] in row)
        primaries = [load(e) for e in evidences
                     if claim["id"] in load(e)["claim_refs"]]
        check(f"claim-has-evidence:{claim['id']}", bool(primaries), f"{len(primaries)} records")
        locs = {load(e)["locator"]["value"] for e in evidences}
        if row:
            check(f"index-locator:{claim['id']}",
                  any(loc in row for loc in locs), row.split("|")[3].strip())
    for f in provenances:
        prov = load(f)
        check(f"provenance->claim:{f.name}", prov["generated_entity"]["id"] in claim_ids,
              prov["generated_entity"]["id"])
        params = prov["activity"]["parameters"]
        check(f"provenance-mission:{f.name}", params.get("mission_id") == 2400, str(params.get("mission_id")))
        check(f"provenance-task-key:{f.name}", params.get("task_key") == "tk-sediment-m2400")
        check(f"provenance-derived-from:{f.name}", "2400" in prov.get("derived_from", []))
        check(f"provenance-source-sha:{f.name}", params.get("source_sha") == SHA)

    # ---- C4: producer does not self-review ----------------------------------
    for f in claims:
        claim = load(f)
        check(f"draft-status:{f.name}", claim["epistemic_status"] == "draft", claim["epistemic_status"])
        check(f"no-promoted:{f.name}", "promoted" not in json.dumps(claim))
    check("no-review-event-files", not list(OUT.glob("review-*.json")), str(list(OUT.glob("review-*.json"))))
    check("no-review-status-field",
          not any('"review_status"' in f.read_text(encoding="utf-8") for f in claims + evidences + provenances))

    for line in OKS:
        print(line)
    for line in FAILS:
        print(line)
    print(f"\n{len(OKS)} passed, {len(FAILS)} failed")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    raise SystemExit(main())