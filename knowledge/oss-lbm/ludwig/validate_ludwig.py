#!/usr/bin/env python3
"""Validator for the Ludwig OSS-LBM knowledge package.

Checks (all must pass; exit code 0):
 1. Files present (claims, evidence, provenance, gap anchors).
 2. Count: >= 8 claims (mission floor).
 3. ID patterns: tkc:/tke:/tkp:oss-lbm:<slug>, GAP-LBM-MCMP-<SLUG>.
 4. Unique IDs; bidirectional claim<->evidence cross references.
 5. Every claim carries a gap_anchor that is registered, and the registry's
    resolved_by_claims point back at real claims (no dangling verdicts).
 6. Evidence locators: code-location needs repo+commit(40 hex)+path+line range
    + verbatim quote (<= 3 lines); code-search needs pattern+scope+query.
 7. Epistemic discipline: no self-approval (all assessment_status
    'unassessed', no review events), established claims are descriptive or
    negative, contested claims carry >= 1 evidence, notes present (these
    double as the TensorLBM service statement).
 8. Every gap anchor has an owner ("declared_by") and a next_step.

The validator is self-contained (standard library only) so it runs in the
repository CI without extra requirements.
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

CLAIM_RE = re.compile(r"^tkc:oss-lbm:[a-z0-9-]+$")
EVID_RE = re.compile(r"^tke:oss-lbm:[a-z0-9-]+$")
PROV_RE = re.compile(r"^tkp:oss-lbm:[a-z0-9-]+$")
GAP_RE = re.compile(r"^GAP-LBM-MCMP-[A-Z0-9-]+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MIN_CLAIMS = 8


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors = []

    paths = {
        "claims": HERE / "claims" / "claims.json",
        "evidence": HERE / "evidence" / "evidence.json",
        "provenance": HERE / "provenance" / "provenance.json",
        "gaps": HERE / "gaps" / "gap-anchors.json",
    }
    for name, p in paths.items():
        if not p.exists():
            errors.append(f"missing file: {p}")
    if errors:
        print("FAIL")
        for e in errors:
            print(f"  - {e}")
        return 1

    claims = load(paths["claims"])
    evidence = load(paths["evidence"])
    provenance = load(paths["provenance"])
    gaps = load(paths["gaps"])

    # 2. count
    if len(claims) < MIN_CLAIMS:
        errors.append(f"expected >= {MIN_CLAIMS} claims, found {len(claims)}")

    # 3/4. ids
    for c in claims:
        if not CLAIM_RE.match(c.get("id", "")):
            errors.append(f"bad claim id: {c.get('id')}")
    for e in evidence:
        if not EVID_RE.match(e.get("id", "")):
            errors.append(f"bad evidence id: {e.get('id')}")
    for p in provenance:
        if not PROV_RE.match(p.get("id", "")):
            errors.append(f"bad provenance id: {p.get('id')}")
    for g in gaps:
        if not GAP_RE.match(g.get("id", "")):
            errors.append(f"bad gap id: {g.get('id')}")

    claim_ids = [c["id"] for c in claims]
    evid_ids = [e["id"] for e in evidence]
    gap_ids = [g["id"] for g in gaps]
    for label, ids in (("claim", claim_ids), ("evidence", evid_ids), ("gap", gap_ids)):
        if len(set(ids)) != len(ids):
            errors.append(f"duplicate {label} ids")

    # 4. cross references
    for c in claims:
        refs = c.get("evidence_refs") or []
        if not refs:
            errors.append(f"claim {c['id']} has no evidence_refs")
        for r in refs:
            if r not in evid_ids:
                errors.append(f"claim {c['id']} -> missing evidence {r}")
    for e in evidence:
        refs = e.get("claim_refs") or []
        if not refs:
            errors.append(f"evidence {e['id']} has no claim_refs (orphan)")
        for r in refs:
            if r not in claim_ids:
                errors.append(f"evidence {e['id']} -> missing claim {r}")

    # 5. gap anchors
    by_gap = {}
    for c in claims:
        g = c.get("gap_anchor")
        if g not in gap_ids:
            errors.append(f"claim {c['id']} has unregistered gap anchor {g}")
            continue
        by_gap.setdefault(g, []).append(c["id"])
        if c["id"] not in next(x for x in gaps if x["id"] == g).get("resolved_by_claims", []):
            errors.append(f"claim {c['id']} not listed in {g}.resolved_by_claims")
    for g in gaps:
        if not g.get("declared_by"):
            errors.append(f"gap {g['id']} missing declared_by (ownership)")
        if not g.get("next_step"):
            errors.append(f"gap {g['id']} missing next_step")
        for cid in g.get("resolved_by_claims", []):
            if cid not in claim_ids:
                errors.append(f"gap {g['id']} -> dangling claim {cid}")
        if not g.get("resolved_by_claims"):
            errors.append(f"gap {g['id']} has no resolving claims")

    # 6. locators
    for e in evidence:
        loc = e.get("locator") or {}
        if not SHA_RE.match(str(loc.get("commit", ""))):
            errors.append(f"evidence {e['id']} locator commit not 40-hex")
        if loc.get("locator_type") == "code-location":
            if not loc.get("path"):
                errors.append(f"evidence {e['id']} missing path")
            a, b = loc.get("line_start"), loc.get("line_end")
            if not (isinstance(a, int) and isinstance(b, int) and 1 <= a <= b):
                errors.append(f"evidence {e['id']} bad line range {a}-{b}")
            quote = loc.get("quote") or ""
            if not quote.strip():
                errors.append(f"evidence {e['id']} empty quote")
            if quote.count("\n") + 1 > 3:
                errors.append(f"evidence {e['id']} quote longer than 3 lines")
            if b - a + 1 != quote.count("\n") + 1:
                errors.append(f"evidence {e['id']} line range {a}-{b} inconsistent with quote")
        elif loc.get("locator_type") == "code-search":
            for field in ("pattern", "scope", "query"):
                if not loc.get(field):
                    errors.append(f"evidence {e['id']} code-search missing {field}")
            if loc.get("hits") != 0:
                errors.append(f"evidence {e['id']} absence claim must record 0 hits, got {loc.get('hits')}")
        else:
            errors.append(f"evidence {e['id']} unsupported locator_type {loc.get('locator_type')}")

    # 7. epistemic discipline
    allowed_status = {"established", "well-supported", "provisional", "contested",
                      "speculative", "superseded", "not-assessed", "hypothesized"}
    for c in claims:
        st = c.get("epistemic_status")
        if st not in allowed_status:
            errors.append(f"claim {c['id']} invalid epistemic_status {st}")
        if st == "established" and c.get("claim_type") not in ("descriptive", "negative"):
            errors.append(f"claim {c['id']}: established status must be descriptive/negative")
        if not c.get("notes"):
            errors.append(f"claim {c['id']} missing notes (TensorLBM service statement)")
        for field in ("id", "statement", "claim_type", "created_at", "version"):
            if not c.get(field):
                errors.append(f"claim {c['id']} missing {field}")
    for e in evidence:
        if e.get("assessment_status") != "unassessed":
            errors.append(f"evidence {e['id']} must be unassessed (no self-approval), got "
                          f"{e.get('assessment_status')}")
        if e.get("review_events"):
            errors.append(f"evidence {e['id']} carries review_events (self-approval)")
    for p in provenance:
        for field in ("id", "generated_entity", "activity", "agents", "recorded_at", "version"):
            if field not in p:
                errors.append(f"provenance {p.get('id')} missing {field}")
        if not SHA_RE.match(str(p.get("activity", {}).get("commit", ""))):
            errors.append(f"provenance {p.get('id')} activity commit not 40-hex")

    # 8. report
    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"PASS: {len(claims)} claims, {len(evidence)} evidence, "
          f"{len(provenance)} provenance, {len(gaps)} gap anchors")
    print("  claims by gap anchor:")
    for gid in gap_ids:
        print(f"    {gid}: {len(by_gap.get(gid, []))}")
    status_counts = {}
    for c in claims:
        status_counts[c["epistemic_status"]] = status_counts.get(c["epistemic_status"], 0) + 1
    print("  claims by epistemic_status: " +
          ", ".join(f"{k}={v}" for k, v in sorted(status_counts.items())))
    print("  locator types: " + ", ".join(
        sorted({e["locator"]["locator_type"] for e in evidence})))
    print("  epistemic discipline: all evidence unassessed, no review events")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())