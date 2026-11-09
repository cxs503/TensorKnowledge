# Competitive and Capability Analysis

Research snapshot: 2026-11-09. Qualitative desk research, not a benchmark.

## Capability matrix

Core = central capability; Partial = present but limited/variable; External = needs another service or governance process. Ratings describe public product positioning and documented workflows, not independently measured quality.

| System | Ingestion | Evidence granularity | Temporal/version handling | Human governance | Agent/API | Portability |
|---|---|---|---|---|---|---|
| Cognee | Core | Partial graph/source links | Pipeline-dependent | External | SDK/MCP | Backend-dependent |
| Graphiti | Core | Fact/edge-level | Core temporal graph | External | API | Graph export/backend |
| Mem0 | Core | Memory/fact-level | Update/forget operations | External | SDK/API | Store-dependent |
| Letta | Core | Agent memory blocks | Agent state/history | Agent/developer controls | Runtime/API | Agent state formats |
| Hindsight | Core | Observation/memory-level | Long-horizon reflection | External | SDK/API/MCP | Verify export |
| LlamaIndex | Core | Chunk/node metadata | Index refresh varies | External | Framework/API | Framework-specific |
| GraphRAG | Core | Entity/relation/community | Index rebuild lifecycle | External | Query interface | Index artifacts |
| Elicit | Core | Paper/extraction-row | Review workflow | Human screening | Product/API varies | Product export |
| PaperQA2 | Core | Passage/evidence summaries | Corpus/index cache | External | Python/CLI/tools | Local docs/answers |
| OpenAlex | Scholarly metadata | Work/entity, not claims | Dataset/API updates | Curation process | REST | Open data/API |
| Semantic Scholar | Scholarly metadata | Paper/citation | API refresh | Curation process | REST | API |
| scite | Citation context | Citation statement | Citation graph evolves | Product process | Product/API | Product-dependent |
| AI Scientist v2 | Research workflow | Experiment/report | Run artifacts | External peer review | Agent workflow | Code/artifacts |
| Robin | Research workflow | Hypothesis/experiment/result | Iterative loop | Lab-in-loop | Multi-agent | Research outputs |
| PROV-O | N/A | Entity/activity/agent | Derivation relations | N/A | RDF vocabulary | RDF |
| RO-Crate | Artifact package | Artifact/entity metadata | Identifiers/metadata | N/A | JSON-LD | Core |

## What is already relatively mature

- Agent memory extraction, retrieval and temporal context.
- Graph-based corpus indexing and semantic/hybrid retrieval.
- Scholarly paper discovery and metadata graphs.
- Literature screening and structured extraction.
- Cited question answering over scientific documents.
- Research-object and provenance standards.
- Competency and occupation taxonomies.
- Specialized autonomous research workflows.

## Hard integration and quality problems

- A stable cross-domain model that distinguishes claims, documents, datasets, methods, results and agent memories.
- Explicit claim-to-evidence links with exact locators and support/refute/qualify semantics.
- Evidence assessment separated from review authority and publication state.
- Contradiction handling that preserves competing claims and temporal validity.
- Reproducible derivation from sources, agents, tools, datasets and experiments.
- Risk-calibrated quality gates and abstention when evidence is insufficient.
- Feedback from downstream use and experiments into versioned knowledge.
- Portable export independent of one graph, vector store or agent framework.

These are candidate differentiation areas, not proof that existing products do not cover them.

## Candidate integration shortlist

| Priority | Candidate | Test question |
|---|---|---|
| P0 | PROV-O | Can each object version be traced to activities, agents and source entities? |
| P0 | RO-Crate 1.3 | Can a task package include documents, data, code, environment, people and workflow metadata? |
| P0 | PaperQA2 | Are returned passages, locators and citations correct on our corpus? |
| P0 | OpenAlex | Can DOI/title/author/work identity be resolved reliably? |
| P1 | Graphiti | Can it preserve valid-time vs observed-time and expose conflicts? |
| P1 | Cognee | Can graph extraction preserve source provenance and useful relations? |
| P1 | Elicit | What screening/extraction workflow and audit trail should be emulated? |
| P2 | Mem0 / Letta / Hindsight | Which context belongs in agent memory, and what merits promotion to governed knowledge? |
| P2 | UNESCO / ESCO / O*NET | Can external competency taxonomies map without flattening our framework? |

## Adoption due diligence

For every candidate record exact version, license, hosted/self-hosted feature split, data retention/deletion, tenant isolation, bulk export, provenance fidelity, temporal/conflict semantics, API/MCP/SDK, rate limits, operational dependencies, maintenance and benchmark results. Open source does not guarantee every hosted feature is open or commercially usable.

## Conclusion

TensorKnowledge should compete on governed knowledge lifecycle and interoperability, not graph size, connector count or another chat-over-documents UI. Build the asset/evidence/review/evolution contracts; integrate specialized discovery, memory and retrieval tools.
