# Roadmap

This roadmap is a sequence of evidence-gated stages, not a promise of dates. Progress is measured by usable, reviewed learning assets rather than the number of files produced.

## Stage 0 — Establish the foundation

- [x] Define project mission and boundaries.
- [x] Establish the six-domain knowledge framework.
- [x] Define a common tutorial specification.
- [x] Define content-quality and review expectations.
- [ ] Review the framework with educators and domain specialists.
- [x] Convert the framework into reusable agent work-package contracts.
- [x] Define a reusable tutorial template and question-led learning pathways.
- [x] Define source and claim traceability requirements.

**Exit gate:** the framework is internally consistent, understandable, and reviewed for major omissions and unsupported assumptions.

## Current implementation snapshot

- The first flagship tutorial, **Scientific Thinking: From Observation to Explanation**, has an initial full draft in `flagship-tutorials/01-scientific-thinking/README.md`.
- The draft includes a pendulum investigation, model assumptions, uncertainty, agent-assisted critique, transfer exercises, and an assessment rubric.
- OpenStax references have been added for the pendulum model.
- On 2026-11-09, an agent-assisted source and structure pass checked the pendulum model and uncertainty terminology against OpenStax and NIST; the tutorial now has a more explicit reproducibility record and outcome-to-evidence map. This is not independent expert review or a learner pilot.
- Subject-matter review, learner pilot, accessibility review, and full reproducibility review remain pending. The tutorial is **not validated**.

## Capability-to-curriculum translation

- [x] Draft the human capability framework in readable and machine-readable forms.
- [x] Map seven first-cycle capabilities to existing knowledge nodes, learning pathways, and observable evidence.
- [x] Define assessment through explanation, performance, transfer, and reflection/accountability.
- [ ] Validate every mapping reference automatically and in CI.
- [ ] Review assessment validity and accessibility with educators and learners.

## Human capability framework

- [x] Draft a cross-cutting human capability architecture across understanding, inquiry, agent-era agency, and responsibility/meaning.
- [x] Publish both a readable framework and a machine-readable summary.
- [ ] Review the framework with educators, domain specialists, and learners.
- [ ] Map priority capabilities to existing knowledge nodes, pathways, and tutorial assessments.

## Current knowledge-asset implementation

- [x] Add machine-readable contracts for knowledge nodes, pathways, and tutorial metadata.
- [x] Seed 14 linked knowledge nodes spanning inquiry, causality, systems, modeling, critical thinking, and ethics.
- [x] Add two question-led pathways: scientific inquiry and systems/decisions.
- [x] Add a repository integrity validator and a GitHub Actions check for pushes and pull requests.
- [ ] Confirm the GitHub Actions check passes on the current main branch.
- [ ] Obtain independent domain and learning-design review; no review is claimed complete.

## Learning and capability development

- [x] Draft an AI-era learning methodology from field entry through contribution and stewardship.
- [x] Define a machine-readable, revisitable learning cycle.
- [x] Add an evidence-oriented capability progression rubric with L0–L5 descriptive anchors.
- [x] Add structural checks for the learning-cycle stages and rubric anchors.
- [ ] Review the methodology and rubric with educators, domain specialists, and learners.
- [ ] Pilot the cycle in more than one discipline and learner context; report actual evidence and limitations.

## Cross-disciplinary learning pilot

- [x] Define four pilot studios: scientific inquiry, engineering design, humanities research, and creative production.
- [x] Define a shared learner protocol while preserving discipline-specific evidence standards.
- [x] Define machine-readable agent work packages TK-008–TK-014 with dependencies and reviewer roles.
- [ ] Produce and independently review the four studio learning materials.
- [ ] Finalize assessment/transfer probes and ethics, privacy, and accessibility protocols.
- [ ] Run a consent-based learner pilot and publish anonymized findings, sample size, limitations, and revisions.

The pilot is currently **designed, not executed**. The work-package manifest does not imply that any agent has been assigned or that reviewers/learners have participated.

## Current production-readiness work

The repository now includes `AGENT_WORK_PACKAGES.md`, a reusable tutorial template, question-led learning pathways, and a source/claim standard. These documents prepare work for later delegation through TensorPlatform; they do not imply that the platform integration has been implemented or tested.

## Immediate next actions

1. Obtain an independent physics educator review of the first tutorial.
2. Run the pendulum activity with learners and record actual feedback and measurement issues.
3. Improve the lesson based on review evidence.
4. Only then use the revised tutorial as the production template for the next flagship lesson.

## Stage 1 — Build the knowledge map

- Define core concepts, learning outcomes, prerequisites, and cross-domain links.
- Distinguish foundational knowledge from optional specialization.
- Add multiple learning pathways for different backgrounds and goals.
- Record contested topics and unresolved design questions.

**Exit gate:** a learner can navigate from a real question to relevant concepts, tutorials, and practical investigations.

## Stage 2 — Produce flagship tutorials

Initial candidates:
1. Scientific thinking: from observation to explanation
2. Mathematics and logic as tools for understanding
3. Data, evidence, uncertainty, and causal reasoning
4. Models, systems, and emergence
5. Interdisciplinary thinking and knowledge transfer
6. Working with AI agents without surrendering judgment
7. Scientific investigation and reproducibility
8. Engineering design from idea to validated artifact
9. Creativity across art, media, and technology
10. Ethics, institutions, and civilizational futures

Each tutorial must be piloted with real learners or reviewers and revised using feedback.

**Exit gate:** at least three complete tutorials have passed content, practice, accessibility, and learning-effectiveness review.

## Stage 3 — Establish a learning experience

- Add interactive demonstrations and reproducible exercises.
- Provide learner pathways and optional depth.
- Track mastery through explanations, decisions, experiments, and artifacts.
- Make agent assistance inspectable and attributable.
- Support accessibility and low-resource learning contexts.

**Exit gate:** learners can complete a coherent learning journey and demonstrate transferable understanding.

## Stage 4 — Knowledge evolution and responsible scaling

- Create an editorial process for proposed updates.
- Use agents for drafting, cross-checking, translation, and test generation.
- Require qualified human review for substantive claims and high-impact material.
- Maintain provenance, version history, correction notices, and deprecation policies.
- Evaluate learning outcomes before scaling automated content production.

**Exit gate:** content production can scale without weakening reliability, traceability, or educational value.

## Non-goals for the initial release

- Building a full LMS before validating the learning model.
- Publishing hundreds of AI-generated lessons without review.
- Replacing specialist education with superficial generalism.
- Treating completion metrics or agent task success as proof of learning.
