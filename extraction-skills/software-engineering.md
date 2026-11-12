# Skill `xsk-software-engineering` — Software engineering change record

Report type: `software-engineering` · registry entry: `registry.json` · lifecycle: `template-created`

## 1. Identification signals

changed files, commit reference, interface/API change, regression statement

## 2. Extraction steps

| step_id | deterministic | instruction | claim types allowed |
|---|---|---|---|
| `extract-change-scope` | yes | Extract which artefacts changed (files, endpoints, schemas). A claimed change without a named artefact is not a claim. | descriptive |
| `extract-verification-evidence` | no | Extract what was actually run and its result separately from what is believed. 'Tests pass' without a command and its output is an unverified assertion. | descriptive, methodological |
| `extract-behavioural-claims` | no | A behavioural claim must name the input condition it holds under; unconditional wording for a conditional change is an over-claim. | causal, predictive, methodological |

## 3. Evidence rules

Quote the sentence naming the artefact plus the sentence describing the effect; a single sentence that says only 'fixed' is not enough for a behavioural claim.

Locators follow the evidence gate (`ke/wp_gate.py`, rules E1–E7): the declared
offsets must reproduce the quote byte-for-byte, `content_hash` must be the sha256
of the quote, and quotes shorter than 12 characters are rejected as trivial.

## 4. Typical failure modes for this report type

Turning 'the mission succeeded' into 'the capability is verified'; claiming a performance gain without the measured pair; generalising a fixture-passing change to all inputs.

## 5. Empty outcome

A pure refactor or a build-log record with no behavioural statement holds no reusable claim.

## 6. Promotion checklist

- [ ] a real report of this type ran through G1+G2+G3
- [ ] `sample_tests[]` carries report id, source hash and outcome
- [ ] independent review event recorded (reviewer ≠ skill author)
- [ ] `reuse_count` initialised before `registered`
