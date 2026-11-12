# Skill `xsk-technical-proposal` — Technical proposal / design

Report type: `technical-proposal` · registry entry: `registry.json` · lifecycle: `template-created`

## 1. Identification signals

proposal, design, roadmap, specification, plan

## 2. Extraction steps

| step_id | deterministic | instruction | claim types allowed |
|---|---|---|---|
| `extract-purpose-and-question` | no | Extract the question the document answers, verbatim where possible. A document with no question yields no research-question claim. | descriptive, interpretive |
| `extract-method-claims` | no | Extract each method step with its stated parameters; do not fill in defaults the document omits. | methodological |
| `extract-results-and-limits` | no | Extract result statements with their stated scope, and copy the limitations section verbatim into limitations[]. | descriptive, interpretive |

## 3. Evidence rules

Proposals mix intention and result. Quote the tense: a future-tense sentence yields a `hypothesis` claim, never a `descriptive` one.

Locators follow the evidence gate (`ke/wp_gate.py`, rules E1–E7): the declared
offsets must reproduce the quote byte-for-byte, `content_hash` must be the sha256
of the quote, and quotes shorter than 12 characters are rejected as trivial.

## 4. Typical failure modes for this report type

Reading a planned capability as delivered; extracting a target value as a measured value; ignoring the limitations section that bounds the result.

## 5. Empty outcome

A document that only restates goals without method or evidence holds no reusable claim.

## 6. Promotion checklist

- [ ] a real report of this type ran through G1+G2+G3
- [ ] `sample_tests[]` carries report id, source hash and outcome
- [ ] independent review event recorded (reviewer ≠ skill author)
- [ ] `reuse_count` initialised before `registered`
