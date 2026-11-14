# ResearchAudit Adapter — TensorKnowledge Integration

**Status:** integration contract / foundation only. The ResearchAudit runtime is not yet implemented.

## 1. Critical boundary

ResearchAudit is an audit workflow over research artifacts. TensorKnowledge remains the authority for governed knowledge objects and its existing four contracts: claim, evidence, provenance and review-event. Do not create parallel claim/evidence/review schemas or copy the knowledge graph into TensorBench.

ResearchAudit should produce candidate claims and evidence links, then submit them through TensorKnowledge's existing validation and independent review lifecycle. A report-level audit finding is not automatically an approved knowledge object.

## 2. Mapping

| ResearchAudit concept | TensorKnowledge representation |
|---|---|
| Atomic statement extracted from report | schemas/claim-record.schema.json |
| Citation/source span supporting or refuting statement | schemas/evidence-record.schema.json |
| Source document, parser, extraction model and transformation | schemas/provenance-record.schema.json |
| Human/independent decision on a claim or evidence relation | schemas/review-event.schema.json |
| Extracted report/figure/table/equation files | TensorData asset reference where registered |
| Run-level audit result and metrics | TensorBench validation report |

The adapter must inspect the current schema and API implementation before coding; the table describes semantic mapping, not permission to assume all write endpoints are production-ready.

## 3. Ingestion contract

Input manifest: report asset reference and immutable version; content hash and media type; optional bibliography and source-document references; extraction configuration and parser versions; rights/access status for every source.

Extraction:
1. Parse document structure and preserve page/section/paragraph/table/figure locators.
2. Extract atomic claims without strengthening or rewriting their meaning.
3. Resolve citations to source records; preserve unresolved citations as unresolved.
4. Link claim IDs to evidence IDs with relation supports, refutes, qualifies, contextualizes or mentions.
5. Record exact source locator, quote, content hash and extraction method.
6. Create provenance for every extraction/transformation.
7. Run audit checks and emit TensorBench-compatible report.
8. Submit candidates for independent review; never self-approve.

## 4. Initial checks

- Citation reference resolution and metadata consistency.
- Claim has evidence references or is explicitly labelled hypothesis/speculation.
- Evidence locator resolves against the source snapshot.
- Evidence relation consistency: a refutes relation must not be silently counted as support.
- Contradictory evidence and superseded claims are surfaced.
- Conclusions are not broader than declared scope/conditions in the claim.
- Missing or inaccessible sources remain insufficient / inconclusive.

Citation-to-claim semantic support is model-assisted in the first version. It must cite the exact span and be evaluated against an expert-labelled holdout before being used as an approval gate.

## 5. Pilot

Use one real TensorKnowledge report with a permission-cleared bibliography. Select 100 claim-citation pairs and label them independently as support / partial or qualifying / refutation / insufficient. Keep a hidden holdout from the implementation agents.

Measure source-resolution precision, locator resolution rate, per-class precision/recall and reviewer agreement. Do not claim scientific truth verification from citation matching alone.

## 6. Non-goals

- Replacing TensorKnowledge's knowledge engine, schemas or review state machine.
- Automatically approving claims or converting generated text into governed knowledge.
- General proof checking for arbitrary mathematics.
- Plagiarism or authorship detection.
- Reproducing paywalled or restricted source content without permission.

## 7. Handoff tasks

1. Inventory existing TK ingestion, four-contract validation, provenance and review APIs.
2. Build a read-only report parser and candidate graph export.
3. Add citation/source resolver with explicit unresolved state.
4. Add evidence-locator verifier and report exporter.
5. Add labelled evaluation corpus and independent review workflow.
6. Only then add model-assisted support classification.
