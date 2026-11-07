# TensorKnowledge

**Human Knowledge, Learning & Creativity Infrastructure for the AI Era**

TensorKnowledge is an open, evolving project for rethinking what humans should learn, how knowledge should be organized, and how people can learn, investigate, and create in partnership with capable AI agents.

Its mission is to help people understand the world, exercise independent judgment, connect disciplines, and create what does not yet exist.

## Why this project exists

AI agents increasingly retrieve information, write software, analyze data, run simulations, and coordinate complex work. This changes the purpose of education. The goal should not be to memorize everything or train people only for predefined jobs. People still need strong foundations, but should increasingly learn to understand mechanisms; distinguish evidence from claims; ask worthwhile questions; connect disciplines and modalities; use agents without outsourcing judgment; evaluate results; create new knowledge and works; and reason about values and consequences.

## Project scope

1. **Knowledge framework** — a map of foundational, evidential, explanatory, systemic, creative, and civilizational knowledge.
2. **Curriculum** — learning pathways organized around questions and real-world problems.
3. **Tutorial standards** — specifications for accurate, multimodal, interactive, agent-assisted learning materials.
4. **Flagship tutorials** — exemplary learning experiences with experiments, projects, reflection, and assessment.
5. **Knowledge governance** — review, provenance, versioning, correction, and continuous improvement.
6. **Agent production workflow** — bounded work packages, independent review, evidence-based acceptance, and a future handoff to TensorPlatform.

## What TensorKnowledge is not

- Not a replacement for schools, universities, teachers, or domain experts.
- Not an encyclopedia that treats accumulated information as the final goal.
- Not an AI prompting course or a collection of tool tutorials.
- Not a claim that foundational knowledge or specialist expertise is obsolete.
- Not a system that treats agent-generated output as verified knowledge.

## Six curriculum domains

1. Cognitive foundations
2. Evidence and reality
3. Models and principles
4. Systems and interdisciplinary thinking
5. Creativity and discovery
6. Civilization and values

These domains are interconnected. Learners may enter through different questions and follow different paths.

## Relationship to the Tensor ecosystem

- **TensorPlatform** provides general agent orchestration, collaboration, execution, and governance infrastructure.
- **TensorPhysics** and domain solvers provide scientific models, computational experiments, and domain capabilities.
- **TensorKnowledge** defines the human-facing knowledge architecture, learning experiences, tutorial standards, and learning-quality criteria.

TensorKnowledge should integrate with these capabilities rather than reimplement them.

## Current stage

This repository begins as a framework-and-content project. The initial priority is to establish a coherent knowledge map, tutorial specification, quality rubric, and a small set of validated flagship tutorials before attempting a large-scale content factory or dedicated learning platform.

## Guiding principle

> Do not educate people only to know what the world already contains. Help them understand what exists, discover what is unknown, and responsibly create what could exist.

## Knowledge asset integrity

Machine-readable nodes, tutorials, and learning pathways live alongside the human-readable material. Before proposing changes, run:

```bash
python scripts/validate_knowledge_assets.py
```

The same integrity check runs in GitHub Actions for pushes to `main` and pull requests targeting `main`. A green check means local references and required metadata are structurally consistent; it does not certify factual accuracy or learning effectiveness.
