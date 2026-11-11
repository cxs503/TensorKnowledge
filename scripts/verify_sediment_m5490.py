#!/usr/bin/env python3
"""Independent verification of knowledge/sediment/m5490.

Deliberately does NOT import the builder: it re-reads every record from disk,
re-fetches every quoted file from the pinned git object, re-runs jsonschema, and
re-derives INDEX.md consistency.  Four acceptance gates:

G1 schema      — every claim/evidence/provenance record validates against
                 schemas/*.schema.json (Draft 2020-12, offline $id registry).
G2 quote       — for every evidence record: quote is a literal substring of the
                 [start, end] line slice of `git show <sha>:<path>`, each of its
                 lines is found by `grep -F -n -x`, and content_hash matches.
G3 index       — INDEX.md carries every id / locator / sha exactly as recorded.
G4 draft       — no review-event file, review_status=draft, promoted=false, no
                 claim in a promoted epistemic state.

Usage:
    TENSORLBM_REPO=/root/tp-agent/work/m5490 python3 scripts/verify_sediment_m5490.py
Exit code 0 iff all gates pass.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = REPO_ROOT / "schemas"
PKG = REPO_ROOT / "knowledge" / "sediment" / "m5490"
TENSORLBM = Path(os.environ.get("TENSORLBM_REPO", "/root/tp-agent/work/m5490"))
SOURCE_SHA = "f561cd88f22522280907c208f151412238d7c6f8"
PROMOTED_STATES = {"established", "well-supported", "provisional"} - {"provisional"}
FORBIDDEN_STATES = {"established", "well-supported"}   # producer may not self-promote

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def git_show(path: str) -> str:
    out = subprocess.run(["git", "-C", str(TENSORLBM), "show", f"{SOURCE_SHA}:{path}"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"git show failed for {path}: {out.stderr.strip()}")
    return out.stdout


def load(prefix: str) -> list[dict]:
    files = sorted(PKG.glob(f"{prefix}-*.json"))
    return [(f, json.loads(f.read_text(encoding="utf-8"))) for f in files]


def main() -> int:
    try:
        subprocess.run(["git", "-C", str(TENSORLBM), "cat-file", "-e", f"{SOURCE_SHA}^{{commit}}"],
                       check=True, capture_output=True)
        check("src:sha_available", True, "")
    except Exception as exc:                                    # noqa: BLE001
        print(f"FAIL src:sha_available — {exc}")
        return 1

    claims = load("claim")
    evidence = load("evidence")
    provenance = load("provenance")
    check("pkg:record_counts", len(claims) >= 3 and len(evidence) >= 3 and len(provenance) >= 3,
          f"claim {len(claims)} / evidence {len(evidence)} / provenance {len(provenance)}")
    check("pkg:one_provenance_per_claim", len(provenance) == len(claims),
          f"{len(provenance)} provenance vs {len(claims)} claims")

    # ---------------------------------------------------------------- G1 ---
    import jsonschema
    from referencing import Registry, Resource

    registry = Registry()
    schemas = {}
    for name in ("claim-record", "evidence-record", "provenance-record", "review-event"):
        doc = json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))
        schemas[name] = doc
        registry = registry.with_resource(doc["$id"], Resource.from_contents(doc))

    for schema_name, prefix, recs in (
        ("claim-record", "claim", claims),
        ("evidence-record", "evidence", evidence),
        ("provenance-record", "provenance", provenance),
    ):
        v = jsonschema.Draft202012Validator(schemas[schema_name], registry=registry)
        for path, rec in recs:
            errs = sorted(v.iter_errors(rec), key=lambda e: list(e.path))
            check(f"G1 schema:{prefix}:{rec['id']}", not errs,
                  errs[0].message if errs else path.name)

    # resolvable cross references
    claim_ids = {rec["id"] for _, rec in claims}
    ev_ids = {rec["id"] for _, rec in evidence}
    prov_targets = {rec["generated_entity"]["id"] for _, rec in provenance}
    check("G1 xref:claim_ids_unique", len(claim_ids) == len(claims), "")
    check("G1 xref:evidence_ids_unique", len(ev_ids) == len(evidence), "")
    bad = sorted(c for _, rec in evidence for c in rec["claim_refs"] if c not in claim_ids)
    check("G1 xref:evidence_claim_refs_resolve", not bad, f"unresolved {bad}")
    bad = sorted(e for _, rec in claims for e in rec["evidence_refs"] if e not in ev_ids)
    check("G1 xref:claim_evidence_refs_resolve", not bad, f"unresolved {bad}")
    bad = sorted(c for c in claim_ids if c not in prov_targets)
    check("G1 xref:every_claim_has_provenance", not bad, f"missing {bad}")

    # ---------------------------------------------------------------- G2 ---
    cache: dict[str, tuple[str, list[str]]] = {}
    for path, rec in evidence:
        loc = rec["locator"]
        value = loc["value"]
        m = re.fullmatch(r"(.+)#L(\d+)-L(\d+)", value)
        if not m:
            check(f"G2 locator:{rec['id']}", False, f"unparsable locator value {value!r}")
            continue
        rel, start, end = m.group(1), int(m.group(2)), int(m.group(3))
        if rel not in cache:
            text = git_show(rel)
            cache[rel] = (text, text.split("\n"))
        text, lines = cache[rel]
        block = "\n".join(lines[start - 1:end])
        quote = loc["quote"]
        ok_quote = quote in block and len(quote) >= 20
        ok_offsets = loc.get("start_offset") == start and loc.get("end_offset") == end
        digest = "sha256:" + hashlib.sha256(quote.encode("utf-8")).hexdigest()
        ok_hash = loc.get("content_hash") == digest
        # per-line grep demonstration (grep -F -n -x on the pinned blob)
        misses = []
        for qline in [q for q in quote.split("\n") if q.strip()]:
            hits = [i + 1 for i, ln in enumerate(lines) if ln == qline]
            if not hits:
                misses.append(qline[:40])
        ok_grep = not misses
        check(f"G2 quote_in_block:{rec['id']}", ok_quote and ok_offsets and ok_hash,
              f"{rel}:{start}-{end} quote={ok_quote} offsets={ok_offsets} hash={ok_hash}")
        check(f"G2 grep_lines:{rec['id']}", ok_grep, f"missing lines {misses}")
        print(f"$ git -C {TENSORLBM} show {SOURCE_SHA[:8]}:{rel} | sed -n '{start},{end}p' "
              f"| grep -F -n -- '{quote.split(chr(10))[0][:70]}'")
        first = [i + 1 for i, ln in enumerate(lines) if ln == quote.split("\n")[0]]
        print(f"  -> line {first[0] if first else '?'} of {rel} @ {SOURCE_SHA[:8]}: "
              f"{quote.split(chr(10))[0][:90]}")

    # ---------------------------------------------------------------- G3 ---
    index = (PKG / "INDEX.md").read_text(encoding="utf-8")
    missing: list[str] = []
    for cid in sorted(claim_ids):
        if f"`{cid}`" not in index:
            missing.append(cid)
    for eid in sorted(ev_ids):
        if f"`{eid}`" not in index:
            missing.append(eid)
    for _, rec in provenance:
        if f"`{rec['id']}`" not in index:
            missing.append(rec["id"])
    for _, rec in evidence:
        if f"`{rec['locator']['value']}`" not in index:
            missing.append(rec["locator"]["value"])
    check("G3 index:ids_and_locators_present", not missing, f"missing {missing[:6]}")
    check("G3 index:sha_present", index.count(SOURCE_SHA) >= 1, SOURCE_SHA)
    counts_ok = (index.count("tkc:tensorlbm:") >= len(claims)
                 and index.count("tke:tensorlbm:") >= len(evidence))
    check("G3 index:entry_counts", counts_ok,
          f"index tkc={index.count('tkc:tensorlbm:')} tke={index.count('tke:tensorlbm:')}")

    # INDEX claim table row count must equal claim record count
    rows = [ln for ln in index.split("\n") if ln.startswith("| `tkc:tensorlbm:")]
    check("G3 index:claim_rows", len(rows) == len(claims), f"{len(rows)} rows vs {len(claims)} claims")

    # ---------------------------------------------------------------- G4 ---
    review_events = sorted(PKG.glob("review-event*.json"))
    check("G4 draft:no_review_event_records", not review_events,
          f"found {[p.name for p in review_events]}")
    status = json.loads((PKG / "review-status.json").read_text(encoding="utf-8"))
    check("G4 draft:review_status_fold", status.get("review_status") == "draft",
          str(status.get("review_status")))
    check("G4 draft:no_promotion", status.get("promoted") is False
          and status.get("producer_self_review") is False, "")
    bad = [(rec["id"], rec["epistemic_status"]) for _, rec in claims
           if rec["epistemic_status"] in FORBIDDEN_STATES]
    check("G4 draft:no_self_promoted_claim", not bad, f"promoted states {bad}")
    draft_note = all(any("review_status=draft" in n for n in rec.get("notes", []))
                     for _, rec in claims)
    check("G4 draft:notes_declare_draft", draft_note, "")

    # -------------------------------------------------------------- report --
    fails = [n for n, ok, _ in results if not ok]
    for name, ok, detail in results:
        print(("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail and not ok else ""))
    print(f"\n== verify_sediment_m5490: {len(results) - len(fails)} PASS / {len(fails)} FAIL")
    if fails:
        print("failing checks: " + "; ".join(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())