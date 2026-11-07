# TensorPlatform Handoff: Cross-Disciplinary Learning Pilot

**Status:** ready as a task specification; not yet imported, assigned, or executed in TensorPlatform.  
**Source of truth:** [pilot design](README.md) and [machine-readable package manifest](pilot-work-packages.json).

## Objective

Develop a reviewable set of four discipline-specific learning studios that test the TensorKnowledge learning methodology. Preserve disciplinary standards; do not produce generic AI-written lessons that merely share headings.

## Required operating model

- Use the existing TensorKnowledge work-package contract in `AGENT_WORK_PACKAGES.md`.
- Treat `pilot-work-packages.json` as the authoritative package IDs, dependencies, risk classes, deliverable paths, acceptance criteria, and reviewer roles.
- Create isolated workspaces/branches for TK-008 through TK-011. Assign separate authoring agents where possible.
- Assign cross-review to agents that did not author the relevant studio.
- Start TK-012 and TK-013 only after the four studio drafts exist; these two packages may proceed in parallel.
- Start TK-014 only after TK-012 and TK-013 have reviewable outputs.
- Keep one integration owner responsible for consistency and conflict resolution.

## Package execution sequence

```text
TK-008 Scientific inquiry ─────┐
TK-009 Engineering design ─────┤
TK-010 Humanities research ────┼──> TK-012 Assessment and transfer ──┐
TK-011 Creative production ────┘                                      ├──> TK-014 Integration review
TK-008..011 ───────────────────────> TK-013 Ethics/accessibility/data ─┘
```

## Mandatory constraints

1. Do not recruit learners, collect learner data, or claim a pilot has run.
2. Do not claim expert review, assessment validity, or learning effectiveness without named, qualified reviewers and recorded evidence.
3. Use primary/authoritative sources for substantive claims; preserve URLs, bibliographic details, access dates where relevant, and license/rights information.
4. Do not invent historical quotations, scientific measurements, engineering test results, learner feedback, or creative provenance.
5. Label generated, simulated, supplied, and observed data distinctly.
6. Keep discipline-specific evidence criteria. The common learning cycle is a shared scaffold, not a claim that scientific, humanities, engineering, and creative work use identical truth criteria.
7. Record AI assistance and independent verification. Agent output is not learner evidence.
8. Make safety, accessibility, privacy, consent, and copyright blockers explicit.
9. If reviewer expertise or a required source cannot be secured, mark the package blocked or draft; do not self-certify.
10. Report acceptance criteria one by one with links to evidence. A green structural check is not subject-matter approval.

## Required handoff report per package

- package ID and status;
- branch/commit and exact deliverable paths;
- agents and roles (including cross-reviewer);
- sources and provenance;
- acceptance-criteria checklist with evidence links;
- automated checks and their exact results;
- domain review status and reviewer qualifications;
- unresolved issues, confidence limits, and dependencies;
- recommended next action.

## Integration and release gate

TK-014 must produce an integration report that:
- compares the four studios against the common tutorial specification;
- identifies inconsistencies and discipline-specific differences that must remain;
- checks the transfer probes and learner protocol;
- lists all safety, source, accessibility, privacy, and rights blockers;
- recommends **ready for human review**, **revise**, or **blocked**.

It must not publish the materials as validated tutorials. Publication and any learner pilot require explicit human approval and completion of the applicable review/consent gates.

## Definition of done for this handoff

This handoff is complete when all seven packages have evidence-backed status reports and their outputs are integrated or explicitly blocked. It is not complete merely because agents have generated files or tests pass.
