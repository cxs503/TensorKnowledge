# TensorKnowledge Architecture Decisions

**Status:** accepted baseline for v0.1.0

## TK-ADR-001 — TensorKnowledge is an independent knowledge infrastructure
**Decision:** TensorKnowledge is a standalone project and service boundary, not an internal TensorPlatform module.
**Reason:** knowledge assets, governance and services must remain reusable by other agent systems, domain projects and human-facing applications.
**Consequence:** separate repository, versioning, API, persistence and deployment lifecycle. Integration uses versioned contracts.

## TK-ADR-002 — TensorPlatform is the preferred execution provider, not a runtime dependency
**Decision:** TensorKnowledge delegates generic agent execution to TensorPlatform when available, but does not require it for knowledge retrieval, storage or governance.
**Reason:** avoid duplicating the general agent infrastructure and preserve executor portability.
**Consequence:** implement an adapter interface; do not import Platform internals into the Knowledge domain core.

## TK-ADR-003 — Knowledge objects are canonical managed assets
**Decision:** documents, datasets, code and media are artifacts or sources; a typed Knowledge Object is the canonical managed unit that describes a reusable concept, claim, theory, method, observation, result, case, skill or other knowledge asset.
**Reason:** assets need stable identity, relationships, provenance, evidence and review independent of file format.
**Consequence:** define a general-purpose object schema. Existing curriculum knowledge nodes remain compatible as a specialized learning graph and are not silently reinterpreted as the universal schema.

## TK-ADR-004 — TensorData remains the canonical data system
**Decision:** TensorKnowledge references TensorData assets and stores knowledge derived from or about them; it does not become the raw data lake.
**Reason:** preserve clear ownership between data lifecycle and epistemic/knowledge lifecycle.
**Consequence:** use stable external asset references, checksums and provenance. Avoid copying large raw datasets into the Knowledge repository.

## TK-ADR-005 — Evidence, review and execution status are distinct
**Decision:** execution completion, evidence status, review status and publication status are not interchangeable.
**Reason:** an agent can complete a task and still produce unsupported or incorrect content.
**Consequence:** every workflow and UI must display these states separately.

## TK-ADR-006 — Human learning remains a first-class application
**Decision:** existing human capability framework, curriculum, tutorials and learning pathways remain within TensorKnowledge.
**Reason:** the broader knowledge infrastructure should support both machine-useful knowledge and human understanding, judgment and creation.
**Consequence:** preserve the current curriculum domain model and connect it to general Knowledge Objects through typed relationships.
