# Skill template — <report type>

Copy this file to `<report-type>.md`, then add the entry to `registry.json`
(`lifecycle_state: "template-created"`). Do not edit an existing skill into a
different report type: create a new skill and deprecate the old one.

## 1. Identification signals

Machine-checkable signals that route a report to this skill (keywords, required
sections, artefact kinds). Process 02 uses them; a skill with no signal cannot be
selected and therefore cannot be reused.

## 2. Extraction steps

One row per step. `deterministic: yes` means a program can execute it with no
judgement; `no` means a reader is required and the step must be reviewed.

| step_id | deterministic | instruction | claim types allowed |
|---|---|---|---|
| | | | |

## 3. Evidence rules

- Every claim carries a locator: `locator_type`, `value`, `start_offset`,
  `end_offset`, verbatim `quote`, `content_hash`.
- A number in a claim statement must appear verbatim inside the quote. Formatting
  a number yourself is inventing it.
- A claim whose evidence cannot be located goes to `unresolved.json` with a
  reason — never into `claims.json` with a guess.

## 4. Typical failure modes for this report type

List the over-claims this type invites (examples: derived complexity stated as
measured, an assumption promoted to a finding, a single dataset generalised).

## 5. Empty outcome

State concretely when this report type legitimately yields zero claims. Empty is
a legal, complete result: `extraction_summary.empty_result.is_empty = true` with a
reason of at least 20 characters.

## 6. Promotion checklist

- [ ] representative real report ran through the full line (G1+G2+G3)
- [ ] `sample_tests[]` carries that report id + source hash + outcome
- [ ] independent reviewer recorded a review event (reviewer ≠ skill author)
- [ ] `reuse_count` present before `registered`
