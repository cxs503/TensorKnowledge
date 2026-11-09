# TensorKnowledge

**AI-Native Knowledge Infrastructure for Humans and Agents**

TensorKnowledge is an independent knowledge infrastructure for producing, structuring, validating, governing, evolving and serving reusable knowledge assets. It supports both machine-usable knowledge and human understanding, judgment, learning and creativity.

Its central managed asset is a traceable **Knowledge Object**: a typed, versioned unit that can represent a concept, claim, theory, method, observation, model, experiment, result, case, skill or other reusable knowledge. Documents, datasets, code and media remain source artifacts or linked assets; they are not all forced into one storage format.

## Why this project exists

AI agents increasingly retrieve information, write software, analyze data, run simulations and coordinate complex work. The limiting factor is no longer only access to information. It is the ability to turn information and experience into knowledge that is traceable, assessable, reusable and capable of evolving.

TensorKnowledge aims to make that process systematic: collect sources; decompose and synthesize claims; preserve evidence and uncertainty; connect concepts, methods, data and results; review and correct outputs; and make governed knowledge available to people, agents and applications.

## Project scope

1. **Knowledge production** — bounded research, extraction, synthesis, analysis, verification and knowledge creation workflows.
2. **Knowledge assets** — typed objects, evidence, provenance, relationships, versions and links to source artifacts and datasets.
3. **Knowledge governance** — independent review, evidence status, publication gates, correction, supersession and rights management.
4. **Knowledge engine** — search, retrieval, graph traversal, context assembly and agent-facing services.
5. **Human learning and capability development** — knowledge frameworks, curricula, pathways, tutorials and assessment.
6. **Platform integration** — reusable work-package contracts and execution delegation to TensorPlatform without duplicating its agent runtime.

## What TensorKnowledge is not

- Not a second general-purpose agent runtime or orchestration platform.
- Not a raw data lake or replacement for TensorData.
- Not an uncurated mirror of the public web.
- Not an encyclopedia that treats accumulated information as the final goal.
- Not a system that treats agent-generated output, citations or schema validity as proof of truth.
- Not a replacement for domain experts, educators or accountable human decisions.

## Relationship to the Tensor ecosystem

- **TensorPlatform** provides general agent identity, runtime, orchestration, collaboration, harnesses, execution environments and platform-level governance. TensorKnowledge delegates agent execution to it when available.
- **TensorKnowledge** owns knowledge objects, evidence and provenance, knowledge-specific production workflows, domain review and approval, knowledge retrieval services, and human learning applications.
- **TensorData** owns canonical data assets and data lifecycle. TensorKnowledge references datasets and computational outputs rather than absorbing raw data.
- **TensorPhysics** and other domain projects produce domain-specific models, methods, experiments and results. Reviewed findings can become Knowledge Objects, while their original code and data remain in their owning systems.

TensorKnowledge is an independent project and service boundary. It can run alongside TensorPlatform in one operational environment, but it is not an internal Platform module and does not require Platform to serve knowledge queries. Its APIs and assets should remain usable by other agent systems.

## Global landscape research

The international landscape, capability comparison, standards mapping and strategic gap analysis are maintained in [research/global-landscape/](research/global-landscape/). Start with the [global landscape](research/global-landscape/GLOBAL_LANDSCAPE.md) and [strategic gap analysis](research/global-landscape/STRATEGIC_GAP_ANALYSIS.md).

## Architecture and integration

- [Architecture overview](architecture/README.md)
- [System architecture and deployment model](architecture/system-architecture.md)
- [TensorPlatform integration contract](architecture/platform-integration.md)
- [Architecture decisions](architecture/decisions.md)
- [First Platform integration test](platform-test/README.md)

The initial deployment should reuse the existing TensorPlatform agent runtime while keeping TensorKnowledge's API, repository, configuration and release lifecycle separate. The first integration test is a bounded knowledge-production task that returns a proposed draft object; it must not auto-approve or publish the result.

## Human capability framework

The existing human-capability architecture remains a first-class application of TensorKnowledge. It is documented in [Human Capabilities in the AI Era](curriculum/human-capabilities-ai-era.md), with a machine-readable summary in [human-capabilities-framework.json](curriculum/human-capabilities-framework.json).

The learning methodology, capability progression rubric, knowledge framework, pathways and tutorials remain in scope. They will be connected to the general Knowledge Object model rather than replaced by it.

## Machine-readable knowledge assets

Portable contracts live in the schemas directory. Start with:
- [Knowledge Object schema](schemas/knowledge-object.schema.json)
- [Production task schema](schemas/production-task.schema.json)
- [Production result schema](schemas/production-result.schema.json)
- [Existing curriculum knowledge-node schema](schemas/knowledge-node.schema.json)
- [Claim Record schema](schemas/claim-record.schema.json)
- [Evidence Record schema](schemas/evidence-record.schema.json)
- [Provenance Record schema](schemas/provenance-record.schema.json)
- [Review Event schema](schemas/review-event.schema.json)
- [Epistemic benchmark](platform-test/epistemic-benchmark/README.md)

The existing knowledge-node schema remains a specialized learning/curriculum graph. The new Knowledge Object schema is the domain-neutral asset contract.

## Validation

Before proposing changes, run:

```bash
python scripts/validate_knowledge_assets.py
```

The repository check validates local learning-asset integrity and schema-file consistency. It does not establish factual accuracy, expert approval or learning effectiveness. Integration fixtures are illustrative shapes, not evidence that TensorPlatform integration has already run.

## Guiding principle

> Do not merely collect what the world already contains. Turn information and experience into traceable knowledge, make it useful to people and agents, and keep it open to correction and further discovery.
