#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validation for the oss-lbm epistemic knowledge package.
Checks: (1) every record validates against its TensorKnowledge schema;
(2) cross-reference integrity (claim_refs / evidence_refs / provenance ids);
(3) count invariants (≥20 claims, ≥1 evidence per claim, ≥1 provenance);
(4) GAP anchor mapping (each claim notes references a GAP-LBM-* slug).
Exit code 0 = all pass; prints PASS/FAIL lines to stdout."""
import json, pathlib, sys

try:
    import jsonschema
except ImportError:
    print("FAIL jsonschema not installed"); sys.exit(2)

ROOT = pathlib.Path(__file__).resolve().parent          # knowledge/oss-lbm
# Find repo root: walk up until we find schemas/
REPO = ROOT
while not (REPO / "schemas" / "claim-record.schema.json").exists():
    REPO = REPO.parent
    if REPO == REPO.parent:
        print("FAIL: cannot find repo root with schemas/"); sys.exit(2)
SCHEMAS = REPO / "schemas"

schemas = {n: json.loads((SCHEMAS / f"{n}.schema.json").read_text())
           for n in ("claim-record", "evidence-record", "provenance-record")}

def load(d):
    return {p.stem: json.loads(p.read_text()) for p in sorted((ROOT / d).glob("*.json"))}

claims, evidence, prov = load("claims"), load("evidence"), load("provenance")

fails = []
def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail and not ok else ""))
    if not ok: fails.append(name)

# 1. schema validation
for cid, c in claims.items():
    try:
        jsonschema.validate(c, schemas["claim-record"]); check(f"schema:claim:{cid}", True)
    except jsonschema.ValidationError as e:
        check(f"schema:claim:{cid}", False, str(e.message)[:200])
for eid, e in evidence.items():
    try:
        jsonschema.validate(e, schemas["evidence-record"]); check(f"schema:evidence:{eid}", True)
    except jsonschema.ValidationError as e:
        check(f"schema:evidence:{eid}", False, str(e.message)[:200])
for pid, p in prov.items():
    try:
        jsonschema.validate(p, schemas["provenance-record"]); check(f"schema:provenance:{pid}", True)
    except jsonschema.ValidationError as e:
        check(f"schema:provenance:{pid}", False, str(e.message)[:200])

# 2. cross-reference integrity
claim_ids = {c["id"] for c in claims.values()}
ev_ids = {e["id"] for e in evidence.values()}
for cid, c in claims.items():
    missing = [r for r in c.get("evidence_refs", []) if r not in ev_ids]
    check(f"xref:{cid}:evidence_refs_resolve", not missing, f"missing {missing}")
for eid, e in evidence.items():
    missing = [r for r in e.get("claim_refs", []) if r not in claim_ids]
    check(f"xref:{eid}:claim_refs_resolve", not missing, f"missing {missing}")
# every evidence is referenced by >=1 claim
refd_ev = {r for c in claims.values() for r in c.get("evidence_refs", [])}
check("xref:all_evidence_referenced_by_claims", refd_ev == ev_ids, f"orphan evidence: {ev_ids - refd_ev}")
# every claim has >=1 evidence
check("xref:all_claims_have_evidence",
      all(len(c.get("evidence_refs", [])) >= 1 for c in claims.values()),
      "some claims have no evidence_refs")

# 3. count invariants (TASK: ≥20 claims)
check(f"count:claims>=20 ({len(claims)})", len(claims) >= 20)
check(f"count:evidence>=1_per_claim", all(len(c.get("evidence_refs", [])) >= 1 for c in claims.values()))
check(f"count:provenance>=1 ({len(prov)})", len(prov) >= 1)

# 4. GAP anchor mapping
gap_claims = [c for c in claims.values() if any("GAP-LBM" in n for n in c.get("notes", []))]
check(f"gap_anchor:mapped ({len(gap_claims)}/{len(claims)})", len(gap_claims) == len(claims),
      f"{len(claims) - len(gap_claims)} claims missing GAP anchor in notes")

# 5. epistemic status discipline (code-level = established/descriptive, not speculative)
for cid, c in claims.items():
    status = c.get("epistemic_status", "")
    check(f"epistemic:{cid}:{status}", status in ("established", "descriptive", "not-assessed"),
          f"unexpected status '{status}' for code-level claim")

# 6. scope.conditions present
for cid, c in claims.items():
    has_conds = bool(c.get("scope", {}).get("conditions"))
    check(f"scope:{cid}:conditions", has_conds, "missing scope.conditions")

print(f"\n== oss-lbm validation: {'ALL PASS' if not fails else str(len(fails)) + ' FAILURES: ' + '; '.join(fails)}")
sys.exit(1 if fails else 0)
