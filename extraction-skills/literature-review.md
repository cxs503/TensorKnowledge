# Skill `xsk-literature-review` — Literature review

Report type: `literature-review` · registry entry: `registry.json` · lifecycle: `template-created`

## 1. Identification signals

`related work`, `state of the art`, `survey`, `bibliography`, citation density ≥ 5 per 1000 chars

## 2. Extraction steps

| step_id | deterministic | instruction | claim types allowed |
|---|---|---|---|
| `segment-by-citation` | yes | Split the body into citation-bearing passages; one passage yields at most one claim about the cited work. | descriptive, interpretive |
| `attribute-claims-to-cited-work` | no | Each claim names the work it is about; a claim without a resolvable citation is dropped, not guessed. | descriptive, interpretive |
| `record-agreement-and-conflict` | no | Record agreement, conflict or gap between works as separate claims; never merge or average conflicting statements. | descriptive, interpretive, hypothesis |

## 3. Evidence rules

Citations are locators: the quote must contain the citation marker or the sentence it supports. A claim about a work that the review only mentions in passing is a `mentions` relation, not `supports`.

Locators follow the evidence gate (`ke/wp_gate.py`, rules E1–E7): the declared
offsets must reproduce the quote byte-for-byte, `content_hash` must be the sha256
of the quote, and quotes shorter than 12 characters are rejected as trivial.

## 4. Typical failure modes for this report type

Treating the review's own synthesis as an original finding; attributing a claim to the wrong work; merging two works' conflicting numbers into one statement; quoting the reference list instead of the body.

## 5. Empty outcome

A review that lists titles without stating what any work found holds no reusable claim — return an empty set with that reason.

## 6. Promotion checklist

- [ ] a real report of this type ran through G1+G2+G3
- [ ] `sample_tests[]` carries report id, source hash and outcome
- [ ] independent review event recorded (reviewer ≠ skill author)
- [ ] `reuse_count` initialised before `registered`
