# Skill `xsk-scientific-computation` — Scientific computation

Report type: `scientific-computation` · registry entry: `registry.json` · lifecycle: `template-created`

## 1. Identification signals

`governing equation`, `discretisation`, `convergence study`, `mesh refinement`, timing table

## 2. Extraction steps

| step_id | deterministic | instruction | claim types allowed |
|---|---|---|---|
| `extract-equations-and-parameters` | no | Extract governing equations, discretisation and every parameter with value and unit. A number without a unit is recorded as stated, never completed. | mathematical, methodological |
| `extract-accuracy-statements` | no | Extract error/accuracy statements together with the reference they are measured against. An error without a reference yields no claim. | descriptive, predictive |
| `extract-assumptions` | no | Copy stated modelling assumptions verbatim into assumptions[]. Never synthesise an assumption the text does not state. | methodological |

## 3. Evidence rules

Quote the equation line or the parameter table row byte-exactly, including the unit. Offsets must span the number, not just the surrounding sentence, so a reviewer can see the digits unchanged.

Locators follow the evidence gate (`ke/wp_gate.py`, rules E1–E7): the declared
offsets must reproduce the quote byte-for-byte, `content_hash` must be the sha256
of the quote, and quotes shorter than 12 characters are rejected as trivial.

## 4. Typical failure modes for this report type

Reporting a derived error percentage as if measured; dropping the reference value of an error; promoting a modelling assumption to a result; quoting a rounded number that differs from the table.

## 5. Empty outcome

A run log or a method note without results or stated accuracy holds no reusable claim — return an empty set.

## 6. Promotion checklist

- [ ] a real report of this type ran through G1+G2+G3
- [ ] `sample_tests[]` carries report id, source hash and outcome
- [ ] independent review event recorded (reviewer ≠ skill author)
- [ ] `reuse_count` initialised before `registered`
