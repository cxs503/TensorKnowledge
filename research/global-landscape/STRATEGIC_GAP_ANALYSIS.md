# TensorKnowledge Strategic Gap Analysis

Research snapshot: 2026-11-09. Strategic hypotheses derived from public desk research; require hands-on validation.

## 1. Positioning

TensorKnowledge should be an **AI-native, interoperable and governed knowledge infrastructure** that turns information, data and experience into traceable, assessable, reusable and evolving knowledge assets for people and agents.

It should not be another agent memory product, graph database, literature search/chat-with-PDF product, autonomous scientist, public-web mirror or generic LMS.

Its plausible value is the knowledge asset lifecycle connecting specialized producers, data systems, research agents, domain tools, reviewers and downstream users. This is a hypothesis, not a proven moat; the survey has not ruled out private integrated competitors.

## 2. Build / integrate / defer

### Build
- Canonical Knowledge Object and version model.
- Atomic claim and evidence model with exact locators and support/refute/qualify relations.
- Knowledge-specific governance separate from Platform acceptance.
- Conflict and temporal evolution without silent overwrites.
- Production task contract for bounded knowledge work.
- PROV-O and RO-Crate interoperability.
- Retrieval contract that returns object version, evidence, status and provenance.
- Human learning/capability application linked to reusable objects.

### Integrate
- Scholarly discovery: OpenAlex, Semantic Scholar, Crossref.
- Scientific evidence retrieval: PaperQA2; benchmark Elicit workflow.
- Graph ingestion/retrieval: Cognee, Graphiti, GraphRAG as replaceable backends.
- Agent memory: Mem0, Letta, Hindsight, LangMem; keep memory distinct from governed knowledge.
- Artifact packaging: RO-Crate.
- Provenance vocabulary: PROV-O.
- Skills taxonomy mapping: UNESCO, ESCO, O*NET.

### Defer
- Proprietary graph or vector database.
- Full literature search engine or public-web crawler.
- New agent runtime, scheduler or harness.
- Fully autonomous approval/publication.
- Large UI before APIs and model are tested.
- Dozens of connectors before one end-to-end benchmark succeeds.

## 3. Differentiating lifecycle

Sources / data / experiments / agent outputs
→ intake and identity resolution
→ claims, concepts, methods and results
→ evidence, locators and provenance
→ quality assessment and human review
→ versioned governed Knowledge Objects
→ retrieval for people, agents and applications
→ use, experiment, decision and teaching
→ feedback, correction and new data
→ knowledge evolution.

This loop is real only when transitions have machine-checkable artifacts and observable outcomes. A document describing the loop is not implementation evidence.

## 4. Gaps in current v0.1 baseline

The current README and architecture correctly separate TensorPlatform, TensorKnowledge and TensorData and define Knowledge Objects as canonical assets. However, the current Knowledge Object schema remains coarse:

1. sources combine source identity and free-text supports; no atomic claim-to-passage relation.
2. no first-class claims/evidence records.
3. provenance is extensible but not constrained to a PROV-O-compatible contract.
4. no valid-time vs recorded-time semantics.
5. review stores one decision rather than append-only independent events.
6. conflict relations are free-form.
7. rights/license metadata are incomplete.
8. no explicit external identifier namespace/value model.
9. no RO-Crate export profile or round-trip test.
10. no quality benchmark corpus or evaluator protocol.

Do not expand the core schema indiscriminately. Define modular Evidence, Provenance and Review Event records, then reference them from Knowledge Object.

## 5. Roadmap

### Stage 0 — landscape and baseline
Keep this research under version control; validate references, licenses and current repo state. No broad feature build yet.

### Stage 1 — epistemic contracts
Define claim, evidence, provenance and review-event schemas; add support/refute/qualify/contextualize relations; temporal fields where relevant; create 8–12 fixtures spanning scientific claims, methods, dataset-derived results, capability definitions and contested claims.

### Stage 2 — interoperability proof
Export one research task as RO-Crate 1.3; map provenance to PROV-O; resolve DOI/OpenAlex/ORCID identifiers; run round-trip tests and document lossiness.

### Stage 3 — production and quality benchmark
Use PaperQA2 or equivalent to gather evidence; let TensorPlatform agents produce draft objects; compare with human-curated gold claims/evidence. Measure source correctness, locator accuracy, entailment, counterevidence recall, duplicate rate, uncertainty calibration and reviewer correction effort. Keep results draft/in-review.

### Stage 4 — knowledge engine
Benchmark lexical, vector and graph retrieval over approved objects. Compare Cognee/Graphiti with a simple relational + search baseline. Every result must carry object ID/version, evidence status and provenance.

### Stage 5 — applications
Connect human-capability curriculum and tutorials; connect TensorPhysics and other domain projects; support external agent systems, not only TensorPlatform; build workbench on real service operations.

## 6. Quality metrics

| Metric | Evaluation |
|---|---|
| Source identity | DOI/title/author match |
| Locator accuracy | Verify page/section/table/passage exists |
| Claim-evidence entailment | Blind human reviewer labels |
| Counterevidence recall | Compare against curated contrary evidence |
| Provenance completeness | Required-field and graph validation |
| Temporal correctness | Synthetic fact-change tests |
| Conflict preservation | Contradiction fixtures |
| Calibration | Reliability bins/Brier score where appropriate |
| Reuse success | Blind downstream task using the object |
| Reviewer effort | Expert time and correction sampling |
| Evolution traceability | Version lineage audit |
| Portability | RO-Crate/JSON-LD round-trip |

Do not optimize only for object volume or answer fluency.

## 7. Decision gates

- Gate A: source → claim → evidence passes manual entailment review.
- Gate B: provenance identifies source, activity, agent/tool and generated version.
- Gate C: contested/superseded claims remain preserved.
- Gate D: RO-Crate export/import preserves required metadata.
- Gate E: independent agent retrieves and correctly reuses an approved object.
- Gate F: benchmark reduces expert review effort without reducing correctness.

## Final recommendation

Proceed with a narrow evidence-first vertical slice. Build epistemic contracts and benchmark before graph infrastructure, broad connectors or large UI. Success is not document volume or agent count: it is whether another person or agent can inspect, trust at a stated level, reuse, challenge and improve each knowledge asset.
