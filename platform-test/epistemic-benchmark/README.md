# Epistemic Core Benchmark

**Purpose:** test whether an agent can produce structured, inspectable knowledge records rather than fluent but weakly supported prose.

## What is included

- `cases/case-01.json` through `case-10.json`: ten synthetic structural test scenarios.
- `../schemas/claim-record.schema.json`: atomic claims.
- `../schemas/evidence-record.schema.json`: source/locator-to-claim evidence relations.
- `../schemas/provenance-record.schema.json`: PROV-O-aligned generation lineage.
- `../schemas/review-event.schema.json`: append-only independent review decisions.
- `../schemas/benchmark-case.schema.json`: benchmark case envelope.
- `scripts/validate_epistemic_benchmark.py`: schema and cross-reference checks.

The cases are **synthetic fixtures**, not factual reference answers, source endorsements or evidence of agent capability. In particular, the example quotations are synthetic and must never be cited as external evidence.

## Ten scenarios

| Case | Scenario | Required behavior |
|---|---|---|
| 01 | Scientific claim | Scoped claim with exact evidence locator |
| 02 | Method | Separate method claim and source artifact |
| 03 | Dataset-derived result | Link data and transformation provenance |
| 04 | Capability definition | Keep external taxonomy mapping distinct from equivalence |
| 05 | Contested claim | Preserve both support and refutation evidence |
| 06 | Temporal change | Distinguish valid time from record time |
| 07 | Insufficient evidence | Do not turn a contextual mention into support |
| 08 | Counterevidence | Preserve qualifying evidence and narrow claim scope |
| 09 | Derived result | Record inputs and software in provenance |
| 10 | Review separation | Platform completion does not imply knowledge approval |

## Validation

From repository root:

```bash
python -m pip install -r requirements-validation.txt
python scripts/validate_epistemic_benchmark.py
python scripts/validate_knowledge_assets.py
```

The benchmark validator checks JSON Schema conformance and cross-record references. It does not judge whether source passages entail claims or whether a scientific statement is true.

## Agent evaluation protocol

For a real run, use the benchmark cases as task prompts, not as answers to copy. Give the agent source materials separately and require it to produce:
1. atomic Claim Records;
2. Evidence Records with source identity, exact locator and relation;
3. Provenance Records with inputs, activity, agent and tool versions;
4. no Review Event approval by the producing agent;
5. an execution report with unresolved issues and confidence rationale.

An independent reviewer should score:
- source identity correctness;
- locator existence and precision;
- claim/evidence entailment;
- counterevidence recall;
- scope and temporal correctness;
- provenance completeness;
- uncertainty calibration;
- duplicate/unsupported claim rate;
- reviewer correction effort.

Do not score output volume or prose fluency as a proxy for knowledge quality.

## Benchmark status

Version 0.1: schema/structure benchmark only. It is not yet a validated domain gold set. Before measuring agent quality, curators must add real, licensed source material and independently adjudicated gold labels for each evaluated domain.
