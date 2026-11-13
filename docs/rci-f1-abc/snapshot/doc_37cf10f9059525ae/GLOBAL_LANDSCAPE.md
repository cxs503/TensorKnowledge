# Global Landscape: AI-Native Knowledge Infrastructure

Research snapshot: 2026-11-09. Desk research, not an exhaustive market census.

## Executive finding

There are established projects in nearly every adjacent category: agent memory, temporal knowledge graphs, scholarly discovery, AI literature review, autonomous science, provenance, research packaging, and competency frameworks. TensorKnowledge should not rebuild these categories independently.

The plausible opportunity is a cross-domain governed knowledge lifecycle: source intake → claim/concept/method/result decomposition → evidence and provenance binding → independent review and uncertainty/conflict handling → versioned reusable assets → retrieval by people and agents → feedback from use and experiments.

This is a strategic hypothesis, not proof that no integrated competitor exists. Public research cannot inspect every private enterprise product or validate vendor claims.

## Landscape: 36 relevant systems

| # | System | Type | What it does | TensorKnowledge relevance | Primary source |
|---:|---|---|---|---|---|
| 1 | Cognee | Open-source framework | Multi-source ingestion into graph/vector/relational knowledge for agents | Evaluate as ingestion/index backend, not canonical governance | https://github.com/topoteretes/cognee |
| 2 | Graphiti | Open-source framework | Temporal knowledge graph and evolving facts | Study time-aware facts and relationship history | https://github.com/getzep/graphiti |
| 3 | Zep | Commercial product | Agent context and long-term memory | Adjacent memory service; separate from Graphiti OSS | https://www.getzep.com/ |
| 4 | Mem0 | OSS core + hosted | Extract/update/retrieve agent memories | Memory adapter, not reviewed knowledge | https://github.com/mem0ai/mem0 |
| 5 | Letta | OSS framework + hosted | Stateful agents and managed memory | Do not duplicate its agent runtime | https://github.com/letta-ai/letta |
| 6 | Hindsight | Open-source system | Retain, recall and reflect over memory | Benchmark long-horizon retrieval | https://github.com/vectorize-io/hindsight |
| 7 | Supermemory | Product/API | Memory and retrieval across app data | Evaluate portability and provenance | https://supermemory.ai/ |
| 8 | LangMem | Open-source library | Memory primitives for LangGraph | Reuse only where executor stack fits | https://github.com/langchain-ai/langmem |
| 9 | LlamaIndex | OSS framework + services | Connectors, indexing, retrieval and agents | Potential ingestion/retrieval adapter | https://github.com/run-llama/llama_index |
| 10 | Microsoft GraphRAG | OSS toolkit | Graph-based corpus indexing and retrieval | Retrieval pattern; graph extraction is not truth validation | https://github.com/microsoft/graphrag |
| 11 | Neo4j | Database platform | Property graph storage and query | Optional storage backend | https://neo4j.com/ |
| 12 | Elicit | Commercial research product | Literature search, screening, extraction, review reports | Benchmark systematic-review workflow | https://elicit.com/ |
| 13 | PaperQA2 | Open-source scientific RAG | Cited evidence retrieval over scientific documents | Candidate evidence-gathering component | https://github.com/Future-House/paper-qa |
| 14 | AI2 ScholarQA | Research system/open code | Evidence synthesis over scholarly corpora | Study large-scale scholarly QA | https://github.com/allenai/ai2-scholarqa-lib |
| 15 | Consensus | Commercial research product | Answers questions from published literature | Discovery aid, not governance layer | https://consensus.app/ |
| 16 | scite | Commercial research product | Citation context and supporting/contrasting signals | Useful evidence signal, not proof of entailment | https://scite.ai/ |
| 17 | Semantic Scholar | Scholarly search/API | Paper discovery, metadata and citation graph | Integrate for discovery and identifiers | https://www.semanticscholar.org/product/api |
| 18 | OpenAlex | Open scholarly graph/API | Works, authors, institutions, sources and topics | High-value metadata backbone | https://help.openalex.org/api/ |
| 19 | ResearchRabbit | Discovery product | Citation/network literature exploration | Source discovery workflow | https://www.researchrabbit.ai/ |
| 20 | Connected Papers | Discovery product | Graph exploration around papers | Exploration aid; not canonical store | https://www.connectedpapers.com/ |
| 21 | Litmaps | Discovery product | Citation maps and literature monitoring | Possible monitoring integration | https://www.litmaps.com/ |
| 22 | Sakana AI Scientist v2 | Research prototype | Hypotheses, experiments, analysis and paper writing | Autonomous research workflow, not knowledge governance | https://github.com/SakanaAI/AI-Scientist-v2 |
| 23 | FutureHouse Robin | Research system | Multi-agent biology hypotheses, experiments and analysis | Domain-specific knowledge-to-experiment loop | https://www.nature.com/articles/s41586-026-10652-y |
| 24 | Google AI co-scientist | Research system | Multi-agent scientific ideation and research support | Research actor; could consume governed knowledge | https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/ |
| 25 | Coscientist | Research system | LLM orchestration for chemistry research/lab automation | Domain-specialized automation | https://www.nature.com/articles/s42256-023-00709-8 |
| 26 | ChemCrow | Research prototype | Tool-augmented chemistry agent | Domain tool/knowledge integration example | https://github.com/ur-whitelab/chemcrow-public |
| 27 | W3C PROV-O | Standard | Provenance entities, activities and agents | Adopt compatible provenance model | https://www.w3.org/TR/prov-o/ |
| 28 | RO-Crate | Community specification | JSON-LD research object packaging | Portable artifact package/export target | https://www.researchobject.org/ro-crate/specification/1.3/ |
| 29 | FAIR Principles | Data principles | Findable, Accessible, Interoperable, Reusable | Stewardship checklist, not truth score | https://www.go-fair.org/fair-principles/ |
| 30 | DataCite | Metadata/DOI infrastructure | Persistent identifiers and research output metadata | Normalize dataset/software/report identifiers | https://schema.datacite.org/ |
| 31 | Schema.org | Shared vocabulary | Structured descriptions of web entities and works | Reuse common terms in exports | https://schema.org/ |
| 32 | Wikidata | Open collaborative graph | Entities, identifiers and sourced statements | Entity linking/context, not scientific authority | https://www.wikidata.org/ |
| 33 | UNESCO AI Competency Framework | International framework | 12 competencies, 4 dimensions, 3 progression levels | Baseline mapping for curriculum work | https://www.unesco.org/en/articles/ai-competency-framework-students |
| 34 | ESCO | EU taxonomy | Multilingual skills, occupations and qualifications | External taxonomy mapping | https://esco.ec.europa.eu/en |
| 35 | O*NET | US occupational system | Occupations, skills, abilities and activities | Jurisdiction-specific skills mapping | https://www.onetonline.org/ |
| 36 | Open edX | Open-source learning platform | Course delivery and assessment | Downstream learning application, not knowledge model | https://github.com/openedx/edx-platform |

## Category findings

### Agent memory and graph
Cognee, Graphiti, Mem0, Letta, Hindsight and LangMem solve different context/memory problems. Many optimize session continuity, personalization or retrieval. TensorKnowledge's invariant should instead be inspectable, sourced, versioned and governed claims/methods/results. Evaluate these as replaceable components.

### Research discovery and evidence
Elicit, PaperQA2, ScholarQA, Consensus, scite and scholarly graph APIs already cover discovery, screening, extraction, citation context and cited synthesis. Integrate their outputs while retaining source identity and exact locators. Do not start by building a competing literature search engine.

### Autonomous science
AI Scientist, Robin and co-scientist systems demonstrate progress in hypothesis generation, experiment design, analysis and writing. They are research workflows, not neutral cross-domain knowledge governance systems. The important interface is converting observations/results into traceable and reviewable assets.

### Standards and scholarly infrastructure
PROV-O, RO-Crate, FAIR, DataCite and Schema.org provide interoperability building blocks. OpenAlex, Semantic Scholar and Wikidata provide identifiers and graph context, not verified claim truth.

### Human capability and learning
UNESCO, ESCO and O*NET provide established frameworks. Map to them where useful without discarding TensorKnowledge's own AI-era capability theory.

## Limitations

This survey does not prove no integrated competitor exists; does not benchmark product accuracy; does not audit every source repository; and does not settle licensing, privacy, export or commercial suitability. Those require focused due diligence and hands-on tests.

## First technical evaluation shortlist

Start with PROV-O, RO-Crate, PaperQA2, OpenAlex, Graphiti and Cognee. Test provenance fidelity, claim/evidence links, exportability, retrieval quality and deployment cost on a small common corpus.
