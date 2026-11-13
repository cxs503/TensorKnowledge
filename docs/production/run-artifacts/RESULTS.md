# Production-line runner — results (generated)

Every number below is read from the JSON files in this directory;
regenerate with `python scripts/wp_line_artifacts.py`.

## Five processes (declared in code, spec: PRODUCTION-LINE-v1 §2)

| process | difficulty | parallelism | agent tier | depends on | exit gate |
|---|---|---|---|---|---|
| 01-asset-registration | low | extreme | standard | — | G1 |
| 02-classification-parse | low | high | standard | 01-asset-registration | G1 |
| 03-knowledge-extraction | medium | high | standard | 02-classification-parse | G1+G2 |
| 04-independent-review | medium | high | strong | 03-knowledge-extraction | G3 |
| 05-synthesis-research | high | low | strong | 01-asset-registration, 02-classification-parse, 03-knowledge-extraction, 04-independent-review | G1+G3 |

## Fixture matrix: reference (GATE-RULES.md) vs computed

| fixture | ref verdict | got verdict | ref rules | got rules | ref level | got level | verdict/rule/level |
|---|---|---|---|---|---|---|---|
| bad-no-evidence | FAIL_STRUCTURAL | FAIL_STRUCTURAL | S11 | S11 | L0 | L0 | ok/ok/ok |
| bad-quote-offset | FAIL_EVIDENCE | FAIL_EVIDENCE | E3, E4, E7 | E3, E4, E7 | L1 | L1 | ok/ok/ok |
| bad-self-review | FAIL_STRUCTURAL | FAIL_STRUCTURAL | S15 | S15 | L0 | L0 | ok/ok/ok |
| bad-source-hash | FAIL_EVIDENCE | FAIL_EVIDENCE | E2 | E2 | L1 | L1 | ok/ok/ok |
| bad-verified | FAIL_STRUCTURAL | FAIL_STRUCTURAL | S4, S8, S9 | S4, S8, S9 | L0 | L0 | ok/ok/ok |
| ok-basic | PASS_PROGRAMMATIC_PENDING_REVIEW | PASS_PROGRAMMATIC_PENDING_REVIEW | — | — | L2 | L2 | ok/ok/ok |
| ok-verified | PASS_PROGRAMMATIC_PENDING_REVIEW | PASS_PROGRAMMATIC_PENDING_REVIEW | — | — | L3 | L3 | ok/ok/ok |
| ok-zero-claim | PASS_PROGRAMMATIC_PENDING_REVIEW | PASS_PROGRAMMATIC_PENDING_REVIEW | — | — | L1 | L1 | ok/ok/ok |

## Benchmark metrics vs predeclared thresholds

| metric | threshold | got | pass |
|---|---|---|---|
| verdict_agreement | 1.0 | 1.0000 | yes |
| rule_agreement | 1.0 | 1.0000 | yes |
| level_agreement | 1.0 | 1.0000 | yes |
| mutation_detection | 1.0 | 1.0000 | yes |
| rule_coverage | 0.9 | 1.0000 | yes |

Rule coverage: 27/27 implemented rules reddened (uncovered: none).

## Mutation matrix (one invariant reddened at a time)

| mutant | invariant broken | expected rule | rules that fired | gate verdict | detected |
|---|---|---|---|---|---|
| m01-claim-without-evidence | every claim has evidence or unresolved | S11 | S11, S13 | FAIL_STRUCTURAL | yes |
| m02-source-hash-tampered | contract hash equals the source bytes | E2 | E2 | FAIL_EVIDENCE | yes |
| m03-locator-offset-shifted | quote sits at the declared offsets | E4 | E3, E4, E7 | FAIL_EVIDENCE | yes |
| m04-quote-bytes-tampered | quote hash matches the quote bytes | E5 | E3, E4, E5, E7 | FAIL_EVIDENCE | yes |
| m05-trivial-quote | a quote is longer than the triviality floor | E6 | E3, E4, E6, E7 | FAIL_EVIDENCE | yes |
| m06-duplicate-claim-id | record ids are unique | S6 | S13, S6 | FAIL_STRUCTURAL | yes |
| m07-invalid-json | every artefact is valid JSON | S2 | S10, S12, S13, S2 | FAIL_STRUCTURAL | yes |
| m08-producer-self-verified | producers never mark claims verified | S8 | S4, S8, S9 | FAIL_STRUCTURAL | yes |
| m09-summary-counts-inflated | summary counts match the files | S13 | S13 | FAIL_STRUCTURAL | yes |
| m10-package-carries-own-approval | 03 packages ship no review material | S15 | S15 | FAIL_STRUCTURAL | yes |
| m11-artefact-missing | declared artefacts are present | S1 | S1, S10, S12, S13, S7 | FAIL_STRUCTURAL | yes |
| m12-zero-claim-without-reason | an empty result states why | S12 | S12, S4, S5 | FAIL_STRUCTURAL | yes |
| m13-review-not-declared | review is required and independent | M1 | M1, S3 | FAIL_STRUCTURAL | yes |
| m14-report-id-mismatch | source identity agrees across files | S14 | S14 | FAIL_STRUCTURAL | yes |
| m15-provenance-emptied | summary counts match provenance | S13 | S13 | FAIL_STRUCTURAL | yes |
| m16-orphan-evidence | claim/evidence references are closed | S10 | S10, S13, S4 | FAIL_STRUCTURAL | yes |
| m17-illegal-review-transition | review events follow the state machine | M2 | M2 | PASS_PROGRAMMATIC_PENDING_REVIEW | yes |
| m18-source-unreachable | the source document is reachable | E1 | E1, E2, E3, E7, S14 | FAIL_STRUCTURAL | yes |
| m19-reviewer-prompt-copied | review prompt is not copied from the producer prompt | M4 | M4 | PASS_PROGRAMMATIC_PENDING_REVIEW | yes |
| m20-producer-explanation-in-review-context | review context excludes the producer explanation | M5 | M5 | FAIL_SEMANTIC_PREP | yes |
| m21-approval-signed-by-producer | reviewer identity differs from every producer identity | M3 | M2, M3 | PASS_PROGRAMMATIC_PENDING_REVIEW | yes |

## Line run over the fixture root

| process | packages | cleared | failed | blocked upstream |
|---|---|---|---|---|
| 01-asset-registration | 0 | 0 | 0 | 0 |
| 02-classification-parse | 0 | 0 | 0 | 0 |
| 03-knowledge-extraction | 8 | 3 | 5 | 0 |
| 04-independent-review | 0 | 0 | 0 | 0 |
| 05-synthesis-research | 0 | 0 | 0 | 0 |

base_processing_complete=False, synthesis_unblocked=False (a failing upstream package blocks 05 by design).

## 05 synthesis input over the clearing subset

| package | report | level | claims |
|---|---|---|---|
| wp-ok-basic | 9001 | L2 | 5 |
| wp-ok-verified | 9001 | L3 | 5 |

| refused package | code | detail |
|---|---|---|
| wp-ok-zero-claim | NOT_EVIDENCE_BOUND | level=L1 reason=EMPTY_PACKAGE_NO_CLAIM_TO_VERIFY |

ready=True, claims=10, duplicate candidates=5, ok-subset cleared=3.

## Process 01 — asset registration (live platform)

| report id | reachable | source hash (sha256) | chars |
|---|---|---|---|
| 15050 | True | sha256:f0e9443043caa8dc55c54c09f1151351dad03df18ca4930aa6f142621036b788 | 2703 |
| 15048 | True | sha256:c57675380b12f4ae0fe5eec450e2e4240ed15e73b5890c0f855f3f08b8e1f723 | 3098 |
| 15047 | True | sha256:4bd338c40a90c245f3fe64963a3dc1ce051b65efbacb3f865971119533c76d1e | 3716 |
| 15045 | True | sha256:60e03f194ca853f8d58a3c6075ad1e74c57b15c788adc111d3abfdb29d86c2cd | 4186 |
| 15044 | True | sha256:c0e164f64203f4b28bcf3a428625e87bffc6897761b3d45220806abce530c3c5 | 4956 |

