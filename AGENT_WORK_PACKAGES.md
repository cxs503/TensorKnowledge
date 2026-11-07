# Agent Work Packages and Platform Handoff

**Status:** operating specification, v0.1  
**Purpose:** define how TensorKnowledge work can be delegated to agents on TensorPlatform without turning unclear goals into large volumes of unreliable content.

## 1. Handoff principle

Do not delegate the entire knowledge system as one open-ended task. Delegate bounded work packages with explicit inputs, outputs, dependencies, evidence requirements, and acceptance tests.

The project owner retains responsibility for priorities and publication policy. Domain reviewers retain responsibility for specialist sign-off. Learners and educators provide evidence about usability and learning outcomes.

## 2. Work-package lifecycle

1. **Frame:** human/editor defines the question, intended learner, scope, and why the work matters.
2. **Decompose:** coordinator splits the work into independent packages and identifies shared dependencies.
3. **Assign:** agents receive packages matching their role and capabilities.
4. **Produce:** agents create drafts, analyses, exercises, code, or source audits in isolated branches or workspaces.
5. **Cross-review:** a different agent checks structure, traceability, consistency, and likely failure modes.
6. **Verify:** automated checks run where possible; domain-specific claims are checked against primary or authoritative sources.
7. **Human review:** qualified reviewers assess specialist correctness and consequential claims.
8. **Pilot:** learners or educators test the learning experience where appropriate.
9. **Publish:** an editor merges only work that meets its acceptance criteria.
10. **Monitor:** issues, corrections, and source changes feed the next revision.

Passing automated checks is not equivalent to expert approval or demonstrated learning.

## 3. Standard work-package contract

Every delegated task must include:

- **ID and title**
- **Objective:** one concrete outcome
- **Why it matters:** connection to the project mission
- **Audience:** intended learner or user
- **Scope:** what is included and explicitly excluded
- **Inputs:** canonical files, references, data, and dependencies
- **Deliverables:** exact paths, formats, and expected artifacts
- **Evidence requirements:** sources, calculations, tests, provenance, or learner evidence
- **Acceptance criteria:** observable pass/fail conditions
- **Risk class:** low, medium, high, or critical
- **Reviewer requirements:** role or expertise needed
- **Dependencies:** upstream packages and blocking decisions
- **Handoff report:** changes made, evidence, unresolved issues, and confidence limits

If any essential field is unknown, the agent must state the uncertainty rather than invent a value.

## 4. Agent roles

Roles are responsibilities, not claims of independent authority. One agent may perform more than one role only if independent review is still preserved.

- **Research scout:** finds candidate sources and extracts relevant claims with bibliographic details.
- **Domain analyst:** checks technical explanations, equations, assumptions, and scope.
- **Learning designer:** aligns audience, outcomes, activities, and assessment.
- **Content author:** drafts explanations and exercises from approved inputs.
- **Experiment builder:** creates reproducible procedures, datasets, notebooks, or demonstrations.
- **Adversarial reviewer:** searches for counterexamples, unsupported claims, ambiguity, and failure modes.
- **Accessibility reviewer:** checks language, structure, alternative representations, and barriers.
- **Editor/release coordinator:** checks package completeness and publication status.

No role may self-certify its own work as independently reviewed.

## 5. Risk-based review

| Risk | Examples | Minimum review |
|---|---|---|
| Low | formatting, navigation, non-substantive metadata | automated checks plus editor |
| Medium | general explanations, ordinary exercises, translations | source audit plus independent content review |
| High | specialist science, health, law, finance, safety, consequential social claims | qualified domain review; primary-source verification; explicit limitations |
| Critical | dangerous or materially harmful instructions, fabricated evidence, major misleading claims | block publication; withdraw affected content until resolved |

## 6. Acceptance gates

A package is accepted only when:
- deliverables exist at the specified paths;
- scope and audience are respected;
- substantive claims are traceable to sources or clearly labeled as hypotheses;
- calculations, code, and examples are checked;
- limitations and unresolved questions are explicit;
- acceptance criteria are demonstrated, not merely asserted;
- review status is accurate;
- no critical or blocking major defect remains.

A content package may be accepted as a **draft** while expert review or learner piloting remains pending. Its status must say so.

## 7. Parallelization rules

Good candidates for parallel work:
- independent source audits of separate topics;
- draft exercises for distinct learning outcomes;
- accessibility review of a stable draft;
- independent critique of a tutorial;
- metadata and cross-link checks.

Do not parallelize work that depends on unsettled definitions, shared file edits, or a single unresolved conceptual decision. Assign one integration owner. Avoid multiple agents writing the same canonical file concurrently.

## 8. TensorPlatform integration requirements

When the platform is ready to host this workflow, it should support:
- work-package records with versioned contracts;
- role and capability assignment;
- dependency graphs and explicit blocked states;
- isolated branches/workspaces and conflict-aware integration;
- source and artifact provenance;
- automated checks with retained logs;
- independent review assignments;
- human approval gates for high-risk content;
- status vocabulary and revision history;
- traceable links from published claims to sources and review evidence.

Do not build a dedicated TensorKnowledge execution engine if TensorPlatform can provide these generic capabilities.

## 9. First candidate work packages

| ID | Package | Output | Dependency | Review |
|---|---|---|---|---|
| TK-001 | Review the six-domain knowledge framework | gap analysis and proposed revisions | none | education / interdisciplinary |
| TK-002 | Audit Tutorial 01 physics and experiment | annotated review with corrections | Tutorial 01 draft | physics educator |
| TK-003 | Audit Tutorial 01 learning design | outcome-activity-assessment map | Tutorial 01 draft | learning designer |
| TK-004 | Pilot Tutorial 01 with learners | anonymized observations and revision proposals | stable draft and consent | educator / editor |
| TK-005 | Create reusable tutorial template | template and completion checklist | tutorial specification | editor |
| TK-006 | Develop knowledge-pathway model | pathway examples and metadata | knowledge map | learning designer |
| TK-007 | Design source/provenance metadata schema | schema and examples | taxonomy | editor / technical reviewer |

These are candidate packages, not evidence that any external agent has executed them.

### Cross-disciplinary learning pilot

The next controlled pilot is specified in [`pilots/cross-disciplinary/README.md`](pilots/cross-disciplinary/README.md), with machine-readable contracts in [`pilots/cross-disciplinary/pilot-work-packages.json`](pilots/cross-disciplinary/pilot-work-packages.json).

| ID | Package | Output | Dependency | Review |
|---|---|---|---|---|
| TK-008 | Develop scientific inquiry studio | `pilots/cross-disciplinary/studios/scientific-inquiry.md` | none | science educator / learning designer |
| TK-009 | Develop engineering design studio | `pilots/cross-disciplinary/studios/engineering-design.md` | none | engineering educator / safety reviewer |
| TK-010 | Develop humanities evidence studio | `pilots/cross-disciplinary/studios/humanities-research.md` | none | humanities specialist / source reviewer |
| TK-011 | Develop creative production studio | `pilots/cross-disciplinary/studios/creative-production.md` | none | creative practitioner / accessibility reviewer |
| TK-012 | Design common assessment and transfer probes | `pilots/cross-disciplinary/assessment-and-transfer.md` | TK-008–TK-011 | assessment specialist / independent reviewers |
| TK-013 | Prepare ethics, accessibility, and data protocol | `pilots/cross-disciplinary/participant-and-data-protocol.md` | TK-008–TK-011 | ethics/privacy / accessibility reviewers |
| TK-014 | Integrate and adversarially review pilot | `pilots/cross-disciplinary/integration-review.md` | TK-012–TK-013 | independent interdisciplinary panel |

All six packages are **proposed and unassigned**. Deliverables are targets, not existing files. Learner recruitment must not begin before the relevant review and approval gates are satisfied.

## 10. Definition of ready for platform-scale production

Begin large-scale delegation only when:
1. work-package contracts are understood and reusable;
2. acceptance criteria are testable;
3. role boundaries and review requirements are clear;
4. a canonical content template and metadata model exist;
5. the first flagship tutorial has completed at least one independent review cycle;
6. TensorPlatform can track assignments, dependencies, artifacts, reviews, and approvals.

Until then, use small controlled tasks to validate the production method.
