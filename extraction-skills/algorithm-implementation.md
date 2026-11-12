# Skill `xsk-algorithm-implementation` — Algorithm implementation

Report type: `algorithm-implementation` · registry entry: `registry.json` · lifecycle: `template-created`

## 1. Identification signals

pseudocode block, complexity statement, function signature, `O(` in a results section

## 2. Extraction steps

| step_id | deterministic | instruction | claim types allowed |
|---|---|---|---|
| `extract-procedure` | no | Extract the procedure in the source's order. A step the text leaves implicit stays implicit and is listed as a gap. | methodological, mathematical |
| `extract-complexity-claims` | no | Complexity and termination statements are claims only when the source states them; do not derive them from the pseudocode. | mathematical, predictive |
| `locate-code-artefacts` | yes | Reference code locations by path and symbol when named. Missing code is recorded as unresolved, never reconstructed. | descriptive |

## 3. Evidence rules

Procedures are quoted as contiguous lines with offsets; a reworded step is a paraphrase and must be marked `manual-paraphrase`, not `direct-quotation`.

Locators follow the evidence gate (`ke/wp_gate.py`, rules E1–E7): the declared
offsets must reproduce the quote byte-for-byte, `content_hash` must be the sha256
of the quote, and quotes shorter than 12 characters are rejected as trivial.

## 4. Typical failure modes for this report type

Deriving complexity from pseudocode and presenting it as the source's claim; completing a procedure with an obvious-but-absent step; citing a file the report does not name.

## 5. Empty outcome

A pseudocode sketch with no stated property (correctness, complexity, application) holds no reusable claim.

## 6. Promotion checklist

- [ ] a real report of this type ran through G1+G2+G3
- [ ] `sample_tests[]` carries report id, source hash and outcome
- [ ] independent review event recorded (reviewer ≠ skill author)
- [ ] `reuse_count` initialised before `registered`
