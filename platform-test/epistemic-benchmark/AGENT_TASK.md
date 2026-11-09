# TensorKnowledge Epistemic Benchmark — Platform Agent Work Package

**Status:** ready for Platform preflight; do not dispatch until repository eligibility, checkout and worker publishing are verified.  
**Risk:** low  
**Target:** a small, source-grounded pilot across three epistemic scenarios.

## Objective

Test whether a TensorPlatform agent can produce reusable, structured knowledge records with claim-level evidence and reconstructable provenance. This is a production-quality experiment, not a request to implement a new database, graph engine or agent runtime.

## Required preflight

Follow `../README.md` and the repository's existing `platform-test/TENSORPLATFORM_HANDOFF.md`. Verify:
1. TensorKnowledge is permitted in the active Platform project profile.
2. The worker has a local checkout and can create/publish an isolated branch.
3. An eligible agent can claim the mission.
4. The mission API, authentication scope and result polling behavior match the deployed environment.

Stop and report if any preflight check fails. Do not bypass allowlists or target another repository.

## Pilot scenarios

Use three of the ten benchmark scenario types:
- **Scientific claim:** one bounded, low-risk factual claim with explicit domain and conditions.
- **Contested or qualifying claim:** locate at least one material source that qualifies or contradicts an initial broad formulation; preserve both sides.
- **Insufficient evidence:** include a tempting but non-entailing source mention and explain why it does not support the claim.

Use the official public specifications linked from `research/global-landscape/STANDARDS_MAPPING.md` as the initial corpus: W3C PROV-O, RO-Crate 1.3 and FAIR Principles. These are source-discovery starting points, not pre-approved conclusions. Do not fabricate quotations or claim that a source says something unless its passage has been inspected.

## Deliverables

Create a branch and commit containing:
1. At least three Claim Records conforming to `schemas/claim-record.schema.json`.
2. At least six Evidence Records conforming to `schemas/evidence-record.schema.json`, with exact locators and explicit supports/refutes/qualifies/contextualizes relations.
3. Provenance Records conforming to `schemas/provenance-record.schema.json`, recording inputs, activities, agent identity and available tool/software versions.
4. A handoff report at `platform-test/epistemic-benchmark/reports/<mission-id>.md`.
5. A machine-readable result envelope conforming to `schemas/production-result.schema.json`, or a documented exact mapping to the Platform mission result if the deployed worker contract differs.

All generated Knowledge Objects must remain `draft` or `in-review`; use conservative `evidence_status`. The producing agent must not create an approval Review Event for its own output.

## Quality requirements

- Each claim is atomic, scoped and independently assessable.
- Each evidence record identifies a real source and a precise section/page/paragraph/table/figure locator.
- Evidence relation is not inferred from citation presence.
- Counterevidence and limitations are retained.
- Distinguish valid time from recorded time when relevant.
- Provenance identifies source entities, activities, agents and software versions where available.
- Rights and quotation limits are respected; prefer concise paraphrase and short excerpts.
- Unresolved questions and confidence rationale are explicit.

## Validation

Run from repository root:

```bash
python -m pip install -r requirements-validation.txt
python scripts/validate_epistemic_benchmark.py
python scripts/validate_knowledge_assets.py
```

Record exact output. Schema validation checks structure and references; it does not establish factual truth or entailment.

## Required report fields

- TensorPlatform commit/environment and preflight evidence (no secrets);
- package ID, mission ID, agent identity/role, branch and commit;
- source bibliography and exact locators;
- claim-to-evidence mapping including contrary evidence;
- validation commands and exact outcomes;
- per-criterion pass/fail/blocked/not-tested status;
- limitations, unresolved issues and reviewer effort estimate;
- Platform mission state, separate TensorKnowledge review state and evidence status.

## Acceptance criteria

1. Three or more claim records validate.
2. Six or more evidence records validate and point to real source locators.
3. At least one claim has qualifying or refuting evidence retained.
4. At least one insufficient/contextual source is explicitly not treated as support.
5. Provenance is complete enough to reconstruct how each output was produced.
6. No self-approval; objects remain draft/in-review.
7. Independent reviewer can verify each cited locator and judge entailment.
8. Result, branch and commit are inspectable.
9. All failures and blocked checks are reported honestly.

## Stop conditions

Stop before dispatch on failed Platform preflight. During execution, stop and report if source access, exact locators or artifact publishing are unavailable. Never invent evidence to satisfy numeric deliverable counts.
