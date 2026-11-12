# Skill `xsk-experimental-validation` — Experimental validation

Report type: `experimental-validation` · registry entry: `registry.json` · lifecycle: `template-created`

## 1. Identification signals

test matrix, facility description, measurement uncertainty, validation case, baseline comparison

## 2. Extraction steps

| step_id | deterministic | instruction | claim types allowed |
|---|---|---|---|
| `extract-conditions` | no | Extract tested conditions (facility, configuration, ranges) as a condition list attached to every claim from that run. | descriptive |
| `extract-comparison-pairs` | no | An accuracy claim must carry measured value, reference value and how the reference was obtained. A comparison missing either side yields an unresolved claim. | descriptive, predictive |
| `extract-uncertainty` | no | Copy stated uncertainty and its coverage factor verbatim; never compute an error band the report does not state. | descriptive, mathematical |

## 3. Evidence rules

One locator per side of a comparison (measured, reference). A single quote covering both is acceptable only if both numbers are inside it.

Locators follow the evidence gate (`ke/wp_gate.py`, rules E1–E7): the declared
offsets must reproduce the quote byte-for-byte, `content_hash` must be the sha256
of the quote, and quotes shorter than 12 characters are rejected as trivial.

## 4. Typical failure modes for this report type

Reporting agreement without the reference source; quoting a deviation without its baseline; extending a validated range beyond the tested matrix.

## 5. Empty outcome

A description of a facility with no comparison holds no reusable claim.

## 6. Promotion checklist

- [ ] a real report of this type ran through G1+G2+G3
- [ ] `sample_tests[]` carries report id, source hash and outcome
- [ ] independent review event recorded (reviewer ≠ skill author)
- [ ] `reuse_count` initialised before `registered`
