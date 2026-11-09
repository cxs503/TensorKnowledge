# TensorPlatform Integration Test — Knowledge Production Loop

**Status:** specification and fixtures ready; live dispatch is blocked pending target-environment repository eligibility check.  
**Version:** 0.1.2  
**Risk:** low

## 1. Test objective
Use the existing TensorPlatform mission system to produce one small, source-traceable Knowledge Object. Verify mission dispatch, agent execution, artifact/result return, schema validation and separation between Platform acceptance and Knowledge approval.

This first slice uses the TensorKnowledge Git repository as the artifact and review surface. It does not test a Knowledge HTTP API; no such service is implemented yet.

## 2. Canonical inputs
- Task fixture: fixtures/knowledge-task.example.json
- Illustrative result shape: fixtures/knowledge-result.example.json
- Platform mapping and current blockers: ../architecture/platform-integration.md
- Knowledge Object schema: ../schemas/knowledge-object.schema.json
- Mission result schema: ../schemas/production-result.schema.json

The result fixture is illustrative only. It contains placeholders and must never be registered or reported as a real research result.

## 3. Preflight — mandatory before dispatch
1. Inspect the target TensorPlatform deployment's active FACTORY_PROFILE.
2. Confirm TensorKnowledge is in the active project list, or in the approved fallback allowlist.
3. Confirm the worker host has the TensorKnowledge Git checkout at the path resolved by that profile.
4. Confirm the worker can create an isolated worktree and publish a branch or provide equivalent inspectable artifacts.
5. Confirm an eligible agent session can claim a mission for this repository.
6. Confirm authentication, organization scope and current Platform mission route prefix.

The current fallback REPO_WHITELIST found in TensorPlatform source does not list TensorKnowledge. A configured FACTORY_PROFILE may override the fallback. The active deployment profile is not known from source inspection, so this is a live-environment blocker until verified.

## 4. Existing mission protocol
Use the existing authenticated POST /api/v1/tensor/missions endpoint. Map package_id to task_key, render objective/scope/inputs/deliverables/evidence and acceptance criteria into goal, and set repo=TensorKnowledge and base_ref=main. For this research task, map problem_definition.problem_tree, baseline_summary and baseline_gap to Platform's research-admission fields; also supply task_class=research, difficulty and machine-checkable acceptance_criteria.

The worker lifecycle uses the existing claim, start, heartbeat and complete routes. Poll GET /api/v1/tensor/missions/{mission_id} for status and result. The complete request can return a structured result under summary.knowledge_result, with branch, head_commit and checks.

On successful work, request Platform acceptance through status=succeeded and acceptance=true. This should yield awaiting_acceptance and a Platform dev_acceptance approval record. This is not Knowledge approval.

## 5. Execution sequence
1. Complete the preflight checklist.
2. Validate all JSON fixtures and schemas.
3. Create one Platform mission using the mapping above and record its mission ID.
4. Allow an eligible agent to claim and execute it.
5. Produce one proposed Knowledge Object plus a handoff report, with at least two authoritative, attributable sources and precise locators.
6. Return the result envelope under the Platform mission summary and provide branch/commit references.
7. Inspect Platform mission detail and acceptance evidence.
8. Validate the proposed object against the Knowledge Object schema.
9. Keep the object draft/in-review; do not publish or mark it approved.
10. Record actual results in platform-test/reports/.

## 6. Acceptance criteria
- [ ] TensorKnowledge is an allowed and resolvable Platform project in the target environment.
- [ ] A unique package ID is accepted and mapped to a Platform mission ID.
- [ ] An eligible worker claims and runs the mission.
- [ ] Execution status can be queried from mission detail.
- [ ] The result contains a proposed object conforming to the Knowledge Object schema.
- [ ] At least two attributable sources are recorded with supporting locators.
- [ ] Source passages support the associated definitions/claims.
- [ ] Branch/commit or equivalent artifact references are inspectable.
- [ ] Platform acceptance state is distinct from Knowledge review state.
- [ ] Duplicate dispatch/result handling is idempotent or its limitation is documented.
- [ ] The final report marks each criterion passed, failed, blocked or not-tested with evidence.

## 7. Safety and quality constraints
- No private or sensitive data.
- No learner recruitment or human-subject data collection.
- No high-risk advice or consequential decision content.
- No fabricated citations, quotes, measurements or test results.
- No claim of truth based only on schema validation.
- Do not build a new generic scheduler, agent runtime or harness inside TensorKnowledge.
- Do not assume an endpoint, callback, webhook or MCP server exists before verifying it.

## 8. Required handoff report
Save a report under platform-test/reports/ containing:
- tested TensorPlatform commit and environment;
- active project profile and repository checkout verification (no secrets);
- endpoint mapping and authentication/organization scope;
- package ID and Platform mission ID;
- assigned agent roles;
- request, status and result evidence with sensitive values redacted;
- schema validation commands and exact outcomes;
- object IDs, branch/commit and draft status;
- Platform approval status and separate Knowledge review status;
- acceptance checklist, blockers and recommendations.

## 9. Exit decision
The test is ready to dispatch only after all preflight checks pass. It is passed only when evidence supports every mandatory acceptance criterion. If callbacks or MCP are unavailable, use polling and the existing mission protocol; those optional capabilities do not block this first test.
