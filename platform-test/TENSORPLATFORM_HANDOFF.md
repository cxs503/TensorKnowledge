# TensorKnowledge → TensorPlatform Test Handoff

**Handoff status:** ready for Platform-side preflight; not yet ready for live dispatch. Source inspection baseline: TensorPlatform main at d354c78173dea9aa92948cd7e89cc15969d47fd7.  
**Requested action:** inspect the active deployment profile and enable/verify TensorKnowledge as a mission target, then run the bounded integration test.

## Why this handoff exists
TensorKnowledge now defines a provider-neutral production-task contract, a general Knowledge Object schema and a Platform result envelope. Inspection of the current TensorPlatform repository identified an existing mission API that can execute the first test. No new scheduler, worker runtime or MCP server is required for the first slice.

## Platform-side preflight work package
1. Inspect the active FACTORY_PROFILE on the target worker/API deployment.
2. Confirm whether TensorKnowledge is already configured as a project.
3. If absent, propose the smallest safe profile/allowlist change. The current source fallback REPO_WHITELIST does not include TensorKnowledge; configured profile project names replace that fallback.
4. Confirm the TensorKnowledge checkout is resolvable by the worker and can be used to create an isolated worktree.
5. Confirm an eligible resident/worker can claim a mission for this repo and publish an inspectable branch/commit.
6. Report the exact mission API prefix, authentication/organization requirements and mission status/approval behavior.
7. If all preflight checks pass, run the single low-risk task in platform-test/fixtures/knowledge-task.example.json.
8. Return the result in the shape defined by schemas/production-result.schema.json, embedded in the Platform mission summary as described in architecture/platform-integration.md.
9. Leave the proposed Knowledge Object draft/in-review. Do not publish or self-approve it.

## Known Platform mapping
- Create: POST /api/v1/tensor/missions
- Read status/result: GET /api/v1/tensor/missions/{mission_id}
- Worker protocol: /claim, /{mission_id}/start, /{mission_id}/heartbeat, /{mission_id}/complete
- Idempotency: task_key
- Platform acceptance: successful completion with acceptance=true produces awaiting_acceptance and a dev_acceptance approval request.

These routes and semantics were observed in the current repository source; verify them against the target deployment before execution.

## Handoff artifacts
- architecture/system-architecture.md
- architecture/platform-integration.md
- schemas/knowledge-object.schema.json
- schemas/production-task.schema.json
- schemas/production-result.schema.json
- platform-test/README.md
- platform-test/fixtures/knowledge-task.example.json
- platform-test/fixtures/knowledge-result.example.json

## Required report
Create a report under platform-test/reports/ with the Platform commit, active profile check, repository/worktree check, mission ID, worker identity/role, request and result evidence, validation output, approval state, acceptance checklist and blockers. Never include secrets.

## Stop conditions
Stop before dispatch if TensorKnowledge is not allowlisted, the checkout cannot be resolved, worker authorization is unclear, or artifact publication cannot be made inspectable. Report the blocker; do not bypass Platform controls or silently target another repository.
