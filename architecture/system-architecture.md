# TensorKnowledge System Architecture

**Version:** 0.1.0  
**Status:** proposed architecture baseline

## 1. Product definition
TensorKnowledge is an AI-native knowledge infrastructure for producing, structuring, validating, governing, evolving and serving reusable knowledge assets for people, agents and applications.

Its primary product is not a document repository or a standalone agent platform. Its durable output is a governed collection of traceable knowledge objects and linked artifacts. Its software provides the lifecycle and services required to create and use those assets.

The existing human-capability framework, curriculum, learning pathways and tutorials remain first-class TensorKnowledge applications. They are not the entire scope of the knowledge infrastructure.

## Epistemic record model

The Knowledge Object is the canonical aggregate and stable entry point, but high-value epistemic components are separate versioned records:

- **Claim Record**: an atomic proposition with scope, modality, temporal validity and epistemic status.
- **Evidence Record**: a source plus exact locator and an explicit relation to one or more claims (supports, refutes, qualifies, contextualizes, mentions or derived-from).
- **Provenance Record**: PROV-O-aligned entities, activities, agents, inputs and software/tool versions.
- **Review Event**: append-only decision and rationale under a versioned review policy.

Knowledge Objects reference these records by stable IDs. Evidence assessment, review decision, publication visibility and Platform mission state remain independent dimensions. Provenance describes derivation; it does not establish truth. JSON Schema validation establishes structural conformance only.

## 2. Core principles
1. Knowledge object first: a document may contain knowledge, but the canonical managed unit is a typed, addressable knowledge object.
2. Evidence before authority: source, evidence status, review status and publication status are separate fields.
3. Keep original artifacts: preserve source documents, datasets, code, simulations and media in their appropriate systems; knowledge objects link to them.
4. Domain-neutral core: the core model supports science, engineering, humanities, education and creative production without imposing one discipline's evidence standard on all others.
5. Platform reuse: delegate generic agent execution to TensorPlatform when available; do not clone its runtime, harness, scheduler or agent registry.
6. Independent deployability: TensorKnowledge remains useful through its own API and repository even if TensorPlatform is unavailable or replaced.
7. Human accountability: high-risk or consequential knowledge requires qualified review and explicit approval.
8. Reversible evolution: preserve provenance, version history, supersession and correction paths.

## 3. Logical architecture

### 3.1 Knowledge Production
Owns knowledge-specific workflows, not generic agent execution: define a research or synthesis objective; decompose it into bounded work packages; specify sources, deliverables, evidence requirements and acceptance criteria; request execution from an external agent provider; collect outputs and route them through review.

### 3.2 Knowledge Repository
Owns canonical knowledge assets: typed knowledge objects and their versions; source and evidence records; relationships and domain taxonomies; links to TensorData datasets and external artifacts; lifecycle and publication state.

The repository may use relational, document, graph, object or vector storage internally. The public contract must not depend on a particular database.

### 3.3 Knowledge Governance
Owns domain-specific quality and release policy: provenance completeness; evidence assessment and uncertainty; contradiction and duplicate detection; independent review and approval; rights, privacy, safety and sensitivity checks; correction, deprecation and supersession.

A structurally valid object is not necessarily true, useful or approved.

### 3.4 Knowledge Engine
Provides reusable knowledge services: lexical and semantic retrieval; graph and relationship traversal; context assembly with provenance; query and recommendation; object and artifact resolution; API and MCP-facing access.

Inference or generated summaries must retain links to the underlying objects and evidence. A generated answer is not automatically a new approved knowledge object.

### 3.5 Knowledge Applications
Applications consume the core services: research and domain knowledge workspaces; learning pathways, tutorials and capability development; agent-facing knowledge retrieval and skills; cross-domain discovery and synthesis; decision support and knowledge-enabled workflows.

A workbench is a client of the services, not the source of truth.

## 4. System boundaries and ownership

| Capability or asset | Owner | Notes |
|---|---|---|
| Agent identity, runtime and orchestration | TensorPlatform | Generic infrastructure |
| Harness, tools and execution workspace | TensorPlatform | Reuse existing platform capability |
| Generic task execution state and logs | TensorPlatform | Knowledge stores domain links and acceptance outcomes |
| Knowledge work-package definition | TensorKnowledge | Domain-specific objective and acceptance |
| Knowledge objects and relationships | TensorKnowledge | Canonical knowledge record |
| Evidence, provenance and review decisions | TensorKnowledge | Domain-specific epistemic governance |
| Search and retrieval over knowledge assets | TensorKnowledge | May use shared infrastructure |
| Raw datasets and data lifecycle | TensorData | Knowledge stores references and derived knowledge |
| Scientific solver outputs | Domain project / TensorData | Link rather than copy by default |
| Curriculum, tutorials and learning assessment | TensorKnowledge | Existing project assets remain in scope |

## 5. Relationship and call direction
The integration is bidirectional but responsibilities remain asymmetric:
- TensorKnowledge delegates execution to TensorPlatform.
- TensorPlatform agents and other clients consume knowledge services from TensorKnowledge.
- Agents return proposed artifacts and evidence; TensorKnowledge validates and governs them.
- Domain projects contribute source data and findings; TensorKnowledge converts reviewed findings into reusable knowledge assets.

TensorKnowledge must not require TensorPlatform to answer a knowledge query. The query path is directly to the Knowledge API. Only work requiring agent execution needs the platform delegation path.

## 6. Deployment model

### Profile A — integrated development (recommended first)
Run TensorKnowledge services alongside the existing TensorPlatform deployment, preferably on the same development host if resources permit. Keep separate processes, configuration, storage namespace and release lifecycle. Reuse Platform agents for production tasks. This is one operational environment, not one monolithic application.

### Profile B — independent services
Deploy TensorKnowledge API, repository and search services independently. TensorPlatform connects through authenticated APIs. This supports independent scaling, maintenance and use by other agent platforms.

### Profile C — standalone / alternate executor
Run the Knowledge Repository and Knowledge Engine without TensorPlatform. Knowledge assets remain accessible; production tasks can be performed manually or delegated to another compatible execution provider.

## 7. Minimum viable service decomposition
The first implementation should not begin with many microservices. Start with a modular application and stable boundaries:
1. Knowledge API: object CRUD, versioning, search and task intake.
2. Knowledge store: canonical object and provenance persistence.
3. Workflow adapter: submit work packages to TensorPlatform and receive results.
4. Governance module: validation, review state and publication gates.

Search indexing, graph storage, vector databases and independent scaling can be added when measured requirements justify them.

## 8. First end-to-end test
1. TensorKnowledge defines a low-risk research task and acceptance criteria.
2. TensorKnowledge submits the task to TensorPlatform.
3. TensorPlatform assigns an agent and returns a platform task identifier.
4. The agent produces a structured draft object, source list and handoff report.
5. TensorPlatform reports completion and artifact references.
6. TensorKnowledge validates the payload and stores it as draft / in-review.
7. A reviewer can inspect provenance and approve or reject it.
8. A client can retrieve the object through the Knowledge API.

The test must not claim that agent output is verified knowledge. Publication is a separate, human-governed action.

## 9. Non-goals for v0.1
- Rebuilding a general-purpose agent runtime.
- Requiring a graph database, vector database or specific cloud vendor.
- Ingesting and copying the full public web.
- Automatically promoting agent output to approved knowledge.
- Treating every data file, document or generated answer as a knowledge object.
- Building a large end-user UI before the object and integration contracts are tested.
