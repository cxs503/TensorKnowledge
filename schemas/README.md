# Machine-Readable Knowledge Assets

This directory defines portable data contracts used by TensorKnowledge. The schemas describe stable identifiers, relationships, provenance, evidence and review state without prescribing a particular database or user interface.

## Contracts

### General knowledge infrastructure
- knowledge-object.schema.json: the domain-neutral, canonical Knowledge Object. It can represent concepts, claims, observations, theories, models, methods, procedures, skills, experiments, results, cases and other reusable knowledge assets.
- production-task.schema.json: the bounded work package submitted to an execution provider such as TensorPlatform.
- production-result.schema.json: the execution result envelope, including proposed objects, evidence, artifacts, checks and unresolved issues.

### Human learning application
- knowledge-node.schema.json: a specialized node for the existing human-capability and curriculum knowledge graph.
- learning-pathway.schema.json: a question- or capability-led route through knowledge nodes and learning assets.
- tutorial.schema.json: tutorial metadata and explicit links to knowledge nodes, outcomes, activities, assessment and sources.

All schemas use JSON Schema Draft 2020-12. Assets should be valid UTF-8 JSON.

## Identity and relationships

- General Knowledge Object IDs use the tko:<domain>:<slug> namespace.
- Existing curriculum IDs continue to use the tk: namespace. Do not silently rename or reinterpret existing IDs.
- Renaming a title must not change an ID. Retire an ID rather than silently reusing it.
- Relationship types are explicit strings. A relationship does not itself establish evidence or certainty.
- Prerequisite links should be used only when the target genuinely depends on the source. Recommended background belongs in pathway metadata, not as a hard prerequisite.

## Source and data references

A source record should identify the source type, citation, URL or persistent identifier where available, exact locator, access date and the claim or content it supports. Check reuse and licensing terms before copying source content.

TensorKnowledge should normally reference canonical datasets and large artifacts owned by TensorData or domain projects. Use data_references and artifact_references with stable asset IDs, URIs and checksums where available. Do not copy large raw datasets into Knowledge Objects.

## Evidence, execution and review are separate

- Execution state describes what happened to a delegated task.
- Evidence status describes how well a claim or object is supported.
- Review status describes the workflow decision on an asset.
- Publication status describes who may access the asset.

A completed Platform task does not imply approved knowledge. A schema-valid object does not imply factual accuracy.

## Validation

From the repository root, run:

```bash
python scripts/validate_knowledge_assets.py
```

The validator uses the Python standard library. It checks learning-asset consistency, JSON syntax and schema-file conventions. Full JSON Schema validation can additionally be run with a Draft 2020-12 validator; it is not required for the lightweight repository integrity check.

## Compatibility policy

- Additive optional fields are preferred for minor revisions.
- Breaking changes to required fields or field meaning require a schema version change and migration notes.
- Preserve unknown extension fields when reading and rewriting assets.
- Never silently convert evidence status, review status, units or provenance.
- A schema-valid asset is not automatically scientifically correct or pedagogically effective; human and domain review remain necessary.
