# wp-9706-01 — platform-gate cross-check (round trip)

Purpose: do not assume the submission channel works. The **platform's own gate module**
(`/root/tp-agent/kf/ops/knowledge_factory/gates.py`, `extract_payload` + `structure_gate` + `evidence_gate`)
was run against the **markdown stored in the platform** for the published result report, not against the local file.

## Identities

| item | value |
|---|---|
| work package | `wp-9706-01` |
| source report | `9706` (`tensor://reports/9706`, field `markdown`) |
| source sha256 | `7d0e024b8630cd3390f5efc0c3f5abfb467e85a869c78126bbb210a1a2d13534` (12546 chars / 20505 bytes) |
| published result report | platform report id `14782`, title `KF-RESULT wp-9706-01`, tag `kf-wp:wp-9706-01` |
| earlier draft (same body, stale summary) | report id `14778` |

## Result — 9/9 sub-gates pass on the stored markdown

| gate | result |
|---|---|
| g1_valid_json | True |
| g2_schema_pass (`schemas/kf_result.v1.schema.json`, Draft 2020-12) | True |
| g3_identity (package_id / report_id / task_type stage) | True |
| g4_source_hash_matches (claimed vs platform sha256 of source markdown) | True |
| g4b_source_field | True |
| g5_source_locator_resolvable (0 claims -> 0 locators) | True |
| g5b_all_claims_located_or_unresolved | True |
| g6_no_duplicate_ids | True |
| g7_claim_namespace | True |

`stats = {"n_claims": 0, "locators_checked": 0, "locators_resolved": 0, "locator_rate": null}`
— zero claims is a legitimate complete result for `01-asset-registration` (the gate records `null`, not 100%).

## Why backticks are escaped inside the embedded JSON

`extract_payload` uses the **non-greedy** pattern `re.compile(r"```json\s*\n(.*?)```", re.S)`. Two registered
assets are fenced code blocks (A09 flow diagram, A28 repro commands) whose **verbatim** quotes contain ```.
Serialising the envelope with literal backticks therefore truncated the payload and made it undecodable
(reproduced during development: the block closed at the first ``` inside a quote string).
The report embeds the envelope with backticks escaped as `\u0060` — legal JSON, semantically identical after
`json.loads`, and the block then contains no ``` at all. This is checked on every run by
`scripts/kf_report_9706.py` (gate-style extraction + equality with the envelope file) and by
`tests/test_kf_wp_9706_01.py::test_report_has_exactly_one_decodable_json_block`.

## Independence limitation

This cross-check imports a module that lives **outside** the worktree, so it is not part of the reproducible
chain (`scripts/kf_run_9706.sh`). The in-repo verifier mirrors the same extraction regex and the same identity /
hash predicates, which is what the committed acceptance record rests on. If the platform gate changes, the
in-repo mirror must be updated with it.
