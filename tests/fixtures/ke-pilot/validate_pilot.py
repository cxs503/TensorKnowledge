#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-off structural validation for the m8554 epistemic pilot package.
Checks: (1) every record validates against its TensorKnowledge schema;
(2) cross-reference integrity (claim_refs / evidence_refs / provenance ids);
(3) scenario invariants mirroring validate_epistemic_benchmark.py rules:
    contested  -> supports AND refutes both present, no self-approval
    insufficient -> every evidence assessment_status == insufficient, no supports relation
    scientific  -> claim has explicit scope.conditions (bounded)
Exit code 0 = all pass; prints PASS/FAIL lines to stdout."""
import json, pathlib, sys

try:
    import jsonschema
except ImportError:
    print("FAIL jsonschema not installed"); sys.exit(2)

ROOT = pathlib.Path(__file__).resolve().parent          # package root
# repo root = nearest ancestor that carries the schemas/ directory (relocatable:
# the package was moved from platform-test/.../pilots/m8554 to tests/fixtures/)
REPO = next(a for a in ROOT.parents if (a / "schemas" / "claim-record.schema.json").is_file())
SCHEMAS = REPO / "schemas"

schemas = {n: json.loads((SCHEMAS / f"{n}.schema.json").read_text())
           for n in ("claim-record", "evidence-record", "provenance-record", "knowledge-object", "production-result")}

def load(d):
    return {p.stem: json.loads(p.read_text()) for p in sorted((ROOT / d).glob("*.json"))}

claims, evidence, prov = load("claims"), load("evidence"), load("provenance")
scen = {p.stem: json.loads(p.read_text()) for p in sorted(ROOT.glob("scenario-*.json"))}

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

# 2. cross-reference integrity (key by record id field, not filename stem)
claim_ids = {c["id"] for c in claims.values()}
ev_ids = {e["id"] for e in evidence.values()}
for cid, c in claims.items():
    missing = [r for r in c.get("evidence_refs", []) if r not in ev_ids]
    check(f"xref:{cid}:evidence_refs_resolve", not missing, f"missing {missing}")
for eid, e in evidence.items():
    missing = [r for r in e.get("claim_refs", []) if r not in claim_ids]
    check(f"xref:{eid}:claim_refs_resolve", not missing, f"missing {missing}")
# every evidence is referenced by >=1 claim and vice versa
refd_ev = {r for c in claims.values() for r in c.get("evidence_refs", [])}
check("xref:all_evidence_referenced_by_claims", refd_ev == ev_ids, f"orphan evidence: {ev_ids - refd_ev}")
refd_cl = {r for e in evidence.values() for r in e.get("claim_refs", [])}
check("xref:all_claims_have_evidence", refd_cl == claim_ids, f"claims w/o evidence: {claim_ids - refd_cl}")

# 3. scenario invariants
sc = scen.get("scenario-scientific", {})
check("scenario:scientific:claim_bounded",
      bool(next(iter(claims[k] for k in claims if claims[k]["id"] == sc["claims"][0]))["scope"]["conditions"]))
sc = scen.get("scenario-contested", {})
rels = [e["relation"] for e in sc["evidence"]]
check("scenario:contested:supports_present", "supports" in rels)
check("scenario:contested:refutes_present", "refutes" in rels)
check("scenario:contested:no_self_approval",
      all(not s.get("review_events") for s in scen.values()))
contested_claim = claims["tkc-fair-requires-open-access"]
check("scenario:contested:status_is_contested", contested_claim["epistemic_status"] == "contested")
sc = scen.get("scenario-insufficient", {})
check("scenario:insufficient:all_insufficient",
      all(e["assessment_status"] == "insufficient" for e in sc["evidence"]))
check("scenario:insufficient:no_supports", "supports" not in [e["relation"] for e in sc["evidence"]])
ins_claim = claims["tkc-tkrepo-rocrate-export-production"]
check("scenario:insufficient:claim_not_assessed", ins_claim["epistemic_status"] == "not-assessed")

# 4. deliverable counts (AGENT_TASK: >=3 claims, >=6 evidence, >=1 provenance)
check(f"count:claims>=3 ({len(claims)})", len(claims) >= 3)
check(f"count:evidence>=6 ({len(evidence)})", len(evidence) >= 6)
check(f"count:provenance>=1 ({len(prov)})", len(prov) >= 1)

print(f"\n== pilot validation: {'ALL PASS' if not fails else str(len(fails)) + ' FAILURES: ' + '; '.join(fails)}")
sys.exit(1 if fails else 0)
