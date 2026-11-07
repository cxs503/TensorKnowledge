# Machine-Readable Knowledge Assets

This directory defines the portable data contracts used by TensorKnowledge. The schemas are deliberately format-first: they describe stable identifiers, relationships, provenance, and review state without prescribing a particular database or user interface.

## Contracts

- `knowledge-node.schema.json`: a concept, claim, method, model, dataset, experiment, skill, question, value, or other typed knowledge object.
- `learning-pathway.schema.json`: a question- or capability-led route through knowledge nodes and learning assets.
- `tutorial.schema.json`: tutorial metadata and its explicit links to knowledge nodes, outcomes, activities, assessment, and sources.

All schemas use JSON Schema Draft 2020-12. Assets should be valid UTF-8 JSON.

## Identity and relationships

- IDs are stable, globally namespaced strings within this repository (for example, `tk:concept:observation`).
- Renaming a title must not change an ID. Retire an ID rather than silently reusing it.
- Relationship types are explicit strings. The schema permits extension; repository validation checks that local targets exist.
- A relationship does not itself establish evidence or certainty.
- Prerequisite links should be used only when the target genuinely depends on the source. Recommended background belongs in pathway metadata, not as a hard prerequisite.

## Evidence and review are separate

Evidence status describes the state of a claim or knowledge object (for example, `well-supported` or `provisional`). Review status describes the workflow state of the asset (for example, `draft` or `approved`). Neither should be inferred from the other.

## Validation

From the repository root, run:

```bash
python scripts/validate_knowledge_assets.py
```

The validator uses only the Python standard library. It checks JSON syntax, duplicate IDs, local relationship targets, tutorial node references, and required metadata. Full JSON Schema validation can additionally be run with a Draft 2020-12 validator in CI; it is not required to run the lightweight repository integrity checks.

## Compatibility policy

- Additive optional fields are preferred for minor revisions.
- Breaking changes to required fields or field meaning require a schema version change and migration notes.
- Preserve unknown extension fields when reading and rewriting assets.
- Never silently convert evidence status, review status, units, or provenance.
- A schema-valid asset is not automatically scientifically correct or pedagogically effective; human and domain review remain necessary.
