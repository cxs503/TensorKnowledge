# TensorPlatform Integration Contract

**Version:** 0.1.1  
**Status:** proposed adapter contract, mapped against TensorPlatform main at commit d354c78173dea9aa92948cd7e89cc15969d47fd7 (inspected 2026-11-09)

## 1. Purpose and ownership

TensorKnowledge uses TensorPlatform as an execution provider while remaining an independently deployable knowledge system.

TensorKnowledge owns the domain task definition, knowledge schema, evidence requirements, review and publication decision. TensorPlatform owns agent identity/runtime, mission dispatch and execution state, workspaces, execution logs and its own acceptance workflow.

## 2. Verified current Platform integration surface

Repository inspection identified the existing mission protocol in TensorPlatform:

- Mission creation: POST /api/v1/tensor/missions, implemented by backend/api/tensor_missions.py.
- Mission list/detail: GET /api/v1/tensor/missions and GET /api/v1/tensor/missions/{mission_id}.
- Worker claim: POST /api/v1/tensor/missions/claim.
- Worker lifecycle: POST /api/v1/tensor/missions/{mission_id}/start, /heartbeat and /complete.
- Mission status and result are persisted in tensor_dev_missions; the detail response includes result and any associated approval record.
- Successful completion with acceptance=true transitions to awaiting_acceptance and creates a Platform dev_acceptance approval request. This is Platform task acceptance, not TensorKnowledge knowledge approval.
- MissionCreate supports task_key for idempotency, repo, base_ref, runner, model, worker_role, difficulty, task_class, problem_tree, baseline_summary, baseline_gap and acceptance_criteria.

These are existing Platform routes and fields, not new endpoints proposed by TensorKnowledge. Route prefix and authentication must still be verified against the target deployment before the first live request.

## 3. Important current blocker: TensorKnowledge repository eligibility

The current fallback REPO_WHITELIST in backend/api/tensor_missions.py does not include TensorKnowledge. A configured FACTORY_PROFILE replaces that fallback with its project_names. In either case, the requested repository must also resolve to a local Git checkout for the worker.

Before dispatch, the Platform operator must confirm:
1. TensorKnowledge is included in the active FACTORY_PROFILE project list, or in the approved fallback allowlist.
2. The worker host has a valid local checkout at the path resolved by the active profile.
3. The configured agent runner can create an isolated worktree and push/publish a branch or otherwise return artifacts.
4. The selected worker session is eligible to claim the mission.

Do not assume the production FACTORY_PROFILE or worker filesystem from repository source alone. The active deployment configuration is not visible in this repository inspection.

## 4. First-test mapping: Knowledge Production Task → Platform Mission

The first test uses the existing mission API rather than inventing a new Platform API.

| TensorKnowledge field | Platform mission field / handling |
|---|---|
| package_id | Embedded in goal and mapped to task_key |
| objective + why_it_matters | goal |
| scope.included / scope.excluded | Explicitly rendered into goal |
| inputs | Rendered as source/input instructions in goal |
| deliverables | Rendered as exact expected artifacts in goal |
| evidence_requirements | Rendered into goal |
| acceptance_criteria | acceptance_criteria list and goal |
| risk_class | Used by Knowledge policy; not a native MissionCreate field |
| execution_profile.task_class / difficulty | Platform task_class / difficulty |
| execution_profile.budget | Platform budget, subject to Platform caps |
| execution_profile.preferred_role | Hint only; map to an allowed Platform worker_role only if the configured role vocabulary supports it; otherwise leave unpinned |
| required_reviewer_role | Include in goal; Platform worker_role is a separate, constrained runtime role |
| idempotency_key | task_key (within the authenticated organization) |
| target repository | repo=TensorKnowledge, configured outside the portable task schema |
| target base | base_ref=main for the initial test |
| retry/execution limits | Platform budget and runner fields |

For a research-class mission, provide the Platform admission gate fields: task_class=research, difficulty, at least three problem_tree elements, baseline_summary, baseline_gap and machine-checkable acceptance_criteria. Do not use engineering exemption to bypass research admission.

## 5. Completion and result mapping

The Platform worker completes through its existing /complete route. The request model includes status, acceptance, summary, branch, head_commit, checks, report_id and fail_stage.

For the first test:
- Include the structured TensorKnowledge result envelope under summary.knowledge_result.
- Include headline, changed_files and a quality_gate record in summary where applicable.
- Include machine-checkable checks in the Platform checks field.
- Return the artifact branch and head commit where available.
- Use status=succeeded and acceptance=true when requesting the Platform's normal acceptance review. This results in awaiting_acceptance, not immediate success publication.
- TensorKnowledge then validates the embedded knowledge object and keeps it draft/in-review until its own knowledge review gate is passed.

If the Platform acceptance workflow is unavailable in the target environment, report that limitation and do not silently equate task completion with knowledge approval.

## 6. Status separation

**Platform mission state** is controlled by TensorPlatform (for example queued, claimed, running, awaiting_acceptance, succeeded, failed, stopped).

**TensorKnowledge review state** is controlled by TensorKnowledge (draft, in-review, approved, rejected, deprecated).

**Knowledge evidence status** is controlled by evidence assessment (established, well-supported, provisional, contested, speculative, superseded, not-assessed).

A Platform mission marked succeeded or awaiting_acceptance does not imply an approved Knowledge Object.

## 7. No callback or MCP assumption

The current integration plan uses authenticated HTTP mission creation plus status/detail polling or the existing Platform UI. The Platform repository's architecture RFC states that a native MCP server was not present in the inspected backend at that time. Do not assume a Knowledge-specific webhook, callback or MCP tool exists.

A future adapter may add callbacks or MCP when implemented and tested. They are not prerequisites for the first repository-level integration test.

## 8. Knowledge consumption path

Platform agents can consume knowledge in the first test by reading the versioned schema, source fixtures and approved repository assets from the TensorKnowledge checkout. A dedicated Knowledge HTTP API is not yet implemented; therefore the first test must not claim to have tested API-based retrieval.

A later service increment may expose authenticated object search and retrieval independently of Platform. That API should be designed from actual client requirements, not invented as a prerequisite to the first agent task.

## 9. Security and reliability

- Use the Platform's existing authentication and organization scoping.
- Never place credentials in task payloads, Git fixtures or reports.
- Preserve package ID, Platform mission ID, organization, agent identity, branch and commit.
- Use task_key for idempotent creation; a reused key with a different mission body may conflict.
- Poll mission detail after dispatch; reconcile timeouts before retrying.
- Treat agent output and retrieved external content as untrusted.
- Validate schema, file paths, size limits and artifact references before ingest.
- Require human review for high-risk or consequential knowledge.

## 10. First-test acceptance criteria

1. TensorKnowledge is an allowed and resolvable Platform project in the target environment.
2. An authenticated owner can create a mission with the mapped fields.
3. The response returns a mission ID and queued status.
4. An eligible worker claims and runs the mission.
5. The worker returns a structured result envelope and a branch/commit or equivalent artifact reference.
6. The mission detail endpoint exposes the result and current Platform approval state.
7. The result and proposed object validate against TensorKnowledge schemas.
8. The Knowledge Object remains draft/in-review after Platform completion.
9. A Platform acceptance decision and a Knowledge review decision are recorded as distinct events.
10. Duplicate task submission and result retrieval do not create duplicate knowledge versions.

## 11. Platform implementation request if blocked

If TensorKnowledge is absent from the active project profile or cannot be resolved by the worker, the Platform team must make the smallest configuration/allowlist change and verify worktree creation. Do not build a new task scheduler or agent runtime in TensorKnowledge.
