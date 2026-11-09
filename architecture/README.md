# TensorKnowledge Architecture

**Status:** architecture baseline, v0.1.0

## Canonical documents
- [System architecture](system-architecture.md) — product boundary, logical components, deployment profiles and data ownership.
- [TensorPlatform integration](platform-integration.md) — execution delegation, callbacks, identity, permissions and operational boundaries.
- [Architecture decisions](decisions.md) — decisions that remain stable unless explicitly revised.
- [Platform test handoff](../platform-test/TENSORPLATFORM_HANDOFF.md) — preflight requirements and the exact request to the Platform team.

## Architectural statement
TensorKnowledge is an independent knowledge infrastructure and asset system. TensorPlatform is the preferred general-purpose agent execution and orchestration provider. TensorKnowledge may delegate knowledge-production work to TensorPlatform, while agents and applications running on TensorPlatform may consume TensorKnowledge services directly.

The systems are independently versioned and deployable. They communicate through documented, versioned contracts. TensorKnowledge does not implement a second general-purpose agent runtime.

## Scope boundary
TensorKnowledge owns knowledge-domain semantics and lifecycle: knowledge objects, relationships, evidence, provenance, review and versioning; knowledge-production workflows and domain-specific acceptance gates; knowledge search, retrieval, composition and publishing; learning frameworks, curricula, tutorials and human capability development.

TensorPlatform owns generic agent operations: agent identity and runtime; orchestration, scheduling, collaboration and workspaces; harnesses, tools and execution environments; generic task state, operational logs and platform-level governance.

TensorData owns canonical data storage and data services. TensorKnowledge references data assets rather than absorbing raw datasets or replacing data governance.

## Readiness rule
A design document is not an implemented service. Interfaces in this baseline are contracts for a first integration test. The first platform test should use a bounded, low-risk knowledge task and a draft knowledge object, with human review required before publication.
