# Review prompt — wp-79-04 (independent reviewer, red-team-reviewer role)

Prompt id: `reviewer-prompt-wp79-04`. Written independently for this package; it is
**not** a copy of the production-side prompt (`extraction-skills/prompts/producer-v1.md`)
and the 5-gram Jaccard similarity between the two is measured by
`scripts/kf_wp7904_review.py` (check `C7`) and recorded in `runs/wp-79-04/checks.json`.

## Context handed to the reviewer

* `source.md` — byte-exact copy of `report_id=79`, `markdown` field
  (`sha256:235018352a8a4f5351c48414b7ed29bd0259729f871d4ba94377551b56990ea0`).
* The upstream knowledge object named by the contract (`wp-79-01`), **if it exists**.
* Nothing else. The producer's summary / rationale / self-assessment are explicitly
  excluded (rule M5). Where the upstream object is absent, the reviewer records
  `upstream_available=false` and marks the fidelity axis `not_run` — an absent
  upstream package is never treated as a pass.

## Instructions (adversarial, falsification-first)

1. Recompute the source hash yourself; a mismatch ends the review (`source_integrity`).
2. Re-derive every numeric pair the report uses as "number traceability" evidence:
   apply the rounding criterion (artifact value rounded to the precision the report
   prints must equal the printed value) **and** both readings of the report's own
   tolerance statement (absolute percentage-point difference vs relative error).
   Report which pairs survive which reading. Do not accept a "✅" label as evidence.
3. For each declared quality criterion, ask: is there a recorded per-report outcome
   anywhere in the document? A criterion declared in the standard but with no
   recorded outcome is an evidence gap, not a pass.
4. Probe for over-claim: verdicts stated more strongly than the recorded evidence
   allows; cross-system assertions (tickets, documents) with no locator; result
   produced from an unreproducible location (absolute local paths) without a
   filename or content hash.
5. Look for inconsistent treatment: the same criterion yielding different verdicts
   across items without a stated, quotable rubric.
6. Bind every finding to a verbatim quote from `source.md` plus character offsets;
   a finding without a locator is downgraded to an open question.
7. Never write `verified` / `verification_status` / `gate_confirmed`: verification
   level is computed by the platform gate, not by the reviewer.
8. Emit: per-finding severity (blocking | major | minor | informational), the
   verdict vocabulary `pass | fail | needs-fix`, and an append-only review event
   with decision `approve | request-changes | reject`.