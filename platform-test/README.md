# TensorPlatform Integration Test — Knowledge Production Loop

**Status:** test specification ready for Platform capability mapping; not yet executed.  
**Version:** 0.1.0  
**Risk:** low

## 1. Test objective
Use the TensorPlatform agent runtime to produce one small, source-traceable knowledge object from supplied, stable references. Verify task submission, execution tracking, artifact/result return, schema validation, draft persistence and human review separation.

This is an integration test, not a test of scientific discovery or production-scale throughput.

## 2. Test package
The canonical request fixture is fixtures/knowledge-task.example.json. The expected result shape is fixtures/knowledge-result.example.json.

Suggested topic: a basic, low-risk concept with authoritative, openly accessible sources. The Platform team may use another low-risk topic if source access is easier, but must preserve the acceptance criteria and report the chosen sources.

## 3. Execution sequence
1. Inspect TensorPlatform's current task APIs, agent assignment, workspace and callback/polling support.
2. Map the logical operations in architecture/platform-integration.md to existing capabilities.
3. Validate the task fixture against schemas/production-task.schema.json.
4. Submit the task through the Platform adapter and record the Platform task ID.
5. Assign one research agent and one independent reviewer if current Platform capabilities permit. If not, report the limitation; do not describe self-review as independent.
6. Agent returns a result matching schemas/production-result.schema.json, with at least one proposed Knowledge Object.
7. Validate every proposed object against schemas/knowledge-object.schema.json.
8. Persist the proposal as draft or in-review; do not set approved.
9. Retrieve the object through the Knowledge API or a documented repository-level test adapter.
10. Submit an integration report with actual request/response evidence, logs, limitations and next steps.

## 4. Acceptance criteria
- [ ] A unique package ID is accepted by TensorPlatform.
- [ ] A Platform task ID is returned and correlated to the package.
- [ ] Execution status can be queried or received.
- [ ] Agent can access the required input references.
- [ ] Result payload conforms to the result schema.
- [ ] At least one proposed object conforms to the Knowledge Object schema.
- [ ] Sources are attributable and support the stated claim; source excerpts/locators are recorded where possible.
- [ ] Execution completion does not automatically approve or publish the object.
- [ ] Duplicate submission/result delivery is handled idempotently or the limitation is documented.
- [ ] A final report distinguishes passed, failed, blocked and not-tested criteria.

## 5. Safety and quality constraints
- No private or sensitive data.
- No external learner recruitment or human-subject data collection.
- No high-risk advice or consequential decision content.
- No fabricated citations, quotes, measurements or test results.
- No claim of scientific truth based only on schema validation.
- Do not build a new generic scheduler, agent runtime or harness inside TensorKnowledge.
- Do not assume an endpoint exists before inspecting TensorPlatform.

## 6. Required Platform handoff report
Save a report under platform-test/reports/ containing:
- tested TensorPlatform commit and environment;
- endpoint/adapter mapping and authentication method (never include secrets);
- package ID and Platform task ID;
- assigned agent roles;
- request, status and result evidence with sensitive values redacted;
- schema validation commands and exact outcomes;
- object IDs and draft status;
- acceptance checklist with evidence links;
- blockers, deviations and recommendations.

## 7. Exit decision
The test is ready when Platform confirms a feasible mapping to current capabilities and can run the package in a controlled environment.

The test is passed only when evidence supports every mandatory acceptance criterion. If the platform lacks a callback, use polling or a documented manual result handoff for this first test and record the limitation; do not block the architecture test on optional automation.
