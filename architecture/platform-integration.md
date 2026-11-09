# TensorPlatform Integration Contract

**Version:** 0.1.0  
**Status:** proposed contract for first platform test

## 1. Purpose
TensorKnowledge uses TensorPlatform as an execution provider while remaining an independently deployable knowledge system.

TensorKnowledge owns the domain task definition, knowledge schema, acceptance criteria and publication decision. TensorPlatform owns agent assignment, runtime, orchestration, workspace, execution logs and operational task state.

## 2. Integration pattern
Use an adapter boundary rather than direct dependencies on TensorPlatform internals.
- Outbound: TensorKnowledge submits a versioned work package to a Platform adapter.
- Inbound: Platform returns an acknowledgement, task identifier, status updates and a completion payload or artifact references.
- Consumption: Platform agents call the Knowledge API directly for search, object retrieval and related evidence.
- Publication: only TensorKnowledge governance may change a knowledge object's review/publication state.

The adapter should support a future executor other than TensorPlatform without changing the knowledge object model.

## 3. First-test transport
For the first test, a simple authenticated HTTP API or a manually triggered adapter is sufficient. MCP may be added as a convenient agent-facing interface, but it is not the canonical persistence or execution contract.

Suggested logical operations (names are illustrative; implementation may map them to existing Platform endpoints):

| Operation | Direction | Purpose |
|---|---|---|
| submitWorkPackage | Knowledge → Platform | Submit task, contract version, priority and deliverables |
| getExecutionStatus | Knowledge → Platform | Read queued/running/blocked/completed/failed state |
| receiveExecutionResult | Platform → Knowledge | Receive summary, proposed objects, evidence and artifact references |
| searchKnowledge | Agent/client → Knowledge | Search published or explicitly permitted draft objects |
| getKnowledgeObject | Agent/client → Knowledge | Retrieve object, version, evidence and relationships |

Do not assume these are existing TensorPlatform endpoints. The first adapter must map this logical contract to Platform's actual supported task API after the Platform team confirms it.

## 4. Work-package envelope
The submitted package must include globally unique package ID and contract version; objective, scope and exclusions; intended output object types and exact artifact paths/formats; source/evidence requirements; measurable acceptance criteria; risk class and required reviewer role; deadline/priority only when explicitly supplied; idempotency key and callback/correlation metadata.

The package schema is schemas/production-task.schema.json.

## 5. Result envelope
A completion result must include package ID and Platform task ID; execution state and completion timestamp; concise outcome summary; proposed knowledge objects, never silently approved objects; source/evidence records and artifact references; validation/test results; unresolved issues, limitations and confidence statement; agent/role attribution when available.

The result schema is schemas/production-result.schema.json.

A task may complete with blocked, partial or failed outcome. A missing source, uncertain claim or failed acceptance criterion must be reported rather than filled with invented information.

## 6. State model
Keep Platform execution state separate from Knowledge asset state.

**Execution state:** submitted, accepted, queued, running, blocked, completed, failed, cancelled.

**Knowledge review state:** draft, in-review, approved, rejected, deprecated.

**Evidence status:** established, well-supported, provisional, contested, speculative, superseded, not-assessed.

A Platform task marked completed means the execution ended. It does not mean the proposed knowledge is approved.

## 7. Identity, authorization and safety
- Use service-to-service credentials; never put secrets in repository fixtures or task payloads.
- Scope credentials to the minimum required operations and project.
- Preserve the initiating user, requesting service, assigned agent and reviewer identities where available.
- Enforce access to unpublished, sensitive or restricted knowledge at the Knowledge API.
- Do not expose private learner data, credentials, restricted source material or confidential datasets to agents unless explicitly authorized.
- Treat all agent outputs and retrieved external content as untrusted input.
- Validate schemas, file paths, size limits and allowed artifact types before ingest.
- Require human approval for high-risk or consequential knowledge.

## 8. Reliability and idempotency
- Retrying a submission with the same idempotency key must not create duplicate work packages.
- Result callbacks must be correlated to a known package and Platform task.
- Duplicate callbacks must not create duplicate knowledge versions.
- Preserve raw result payloads and validation reports for audit.
- A timeout is unknown until reconciled with Platform; do not infer failure or success.
- Keep a retry/dead-letter record for failed callbacks.

## 9. First-test acceptance criteria
1. Platform can receive a versioned package with a stable ID.
2. The adapter records the returned Platform task ID.
3. An agent can retrieve at least one Knowledge API fixture or object.
4. An agent can return a result conforming to the result schema.
5. TensorKnowledge can validate and persist the returned proposal as a draft.
6. Invalid or incomplete results are rejected with actionable validation errors.
7. Execution completion does not auto-approve the knowledge.
8. A reviewer can inspect source links, artifacts and unresolved issues.
9. A repeat submission/callback does not duplicate the task or object.
10. The test report records actual Platform behavior, not assumed endpoint support.

## 10. What Platform team must confirm
Before implementation, Platform agents must inspect the current TensorPlatform code and identify existing task submission and status APIs; supported callback/webhook or polling mechanism; agent assignment and role/capability mechanism; artifact/workspace access model; service authentication and permission model; current task state vocabulary; available logs and test environment.

They must propose a mapping from this contract to actual Platform capabilities. Do not add new generic Platform infrastructure if an equivalent capability already exists.
