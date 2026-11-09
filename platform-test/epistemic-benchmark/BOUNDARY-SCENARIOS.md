# Boundary Scenarios 11–12: Design Rationale

**Scope:** two boundary scenarios added to the epistemic benchmark on top of the
existing Claim/Evidence/Provenance/Review contract
(`schemas/claim-record.schema.json`, `evidence-record.schema.json`,
`provenance-record.schema.json`, `review-event.schema.json`,
`benchmark-case.schema.json`) and its validator
(`scripts/validate_epistemic_benchmark.py`).

- **case-11 / `weak-relevance`** — 证据不足不构成支持: the evidence summary is only
  weakly related to the claim (topical overlap, no substantiation). Gold verdict:
  **unsupported**, not supported.
- **case-12 / `contested-both-sides`** — 争议保留两边: two credible (independently
  reviewed) sources hold opposing views on the same proposition. Gold verdict:
  **contested**, with both sides retained; no one-sided resolution.

## Why these two boundaries are worth testing

### 1. Weak relevance is the highest-frequency false-support failure mode

Existing case-07 (`insufficient-evidence`) covers the *general* rule "a contextual
mention is not support". The sharper boundary is when the evidence is **topically
close** to the claim — same domain vocabulary, same quantity family, same condition
space — so that a keyword/overlap-based entailment check fires. This is exactly the
failure mode of fluent knowledge extraction: the source "talks about the same thing"
without reporting the specific value, so a naive pipeline upgrades the relation to
`supports` and the claim to a supported status.

case-11 makes the trap explicit: the quote shares the claim's domain and quantity
("measured coefficients vary with operating condition") but **does not report a value
for condition Z**. The fixture therefore pins three coupled gold labels:

| Record | Field | Gold value | Forbidden |
|---|---|---|---|
| evidence | `relation` | `mentions` | `supports` |
| evidence | `assessment_status` | `insufficient` | `reviewed-supports` |
| claim | `epistemic_status` | `not-assessed` | `established` / `well-supported` / `provisional` |

Note on encoding: the claim schema intentionally has no `unsupported` status —
support is a property of the *evidence relation*, not of the claim. "Unsupported" is
therefore encoded as *absence of support*: no `supports` relation, no
`reviewed-supports` assessment, and the claim kept out of the supported-status set
(`SUPPORTED_STATUSES` in the validator). This keeps the contract unchanged while
making the verdict machine-checkable.

### 2. Symmetric credibility removes the only legitimate reason to drop a side

Existing case-05 (`contested-claim`) has **asymmetric** credibility: the refuting
side is itself `disputed`, so a resolver could legitimately down-weight it. The
boundary case-12 removes that escape hatch: **both** sources are independently
reviewed and high-confidence (`reviewed-supports` / `reviewed-refutes`). With no
credibility asymmetry, there is no principled basis for picking a side — first-come,
higher-authority, or prior-biased resolution are all the failure modes under test.
The only correct verdict is `contested` with both evidence items retained.

| Record | Field | Gold value | Forbidden |
|---|---|---|---|
| evidence A | `relation` / `assessment_status` | `supports` / `reviewed-supports` | dropped or downgraded |
| evidence B | `relation` / `assessment_status` | `refutes` / `reviewed-refutes` | dropped or downgraded |
| claim | `epistemic_status` | `contested` | any supported status, or one-sided resolution |

### 3. Gold verdicts are machine-checkable, not just documented

Each scenario's expected verdict is enforced in three layers:

1. `expected_checks` in the case envelope (human-readable expectation);
2. the fixture's own `epistemic_status` / `relation` / `assessment_status` (gold labels);
3. category invariants in `validate_epistemic_benchmark.py` (machine check).

Mutation testing (2026-11-09, this worktree) confirmed the invariants have teeth:
upgrading the case-11 claim to `well-supported`, relabeling its evidence `supports`,
resolving case-12 to `established`, dropping its refuting side, or downgrading the
refuting side to `disputed` each make the validator FAIL with a specific message,
while the unmutated 12-case set passes.

## Regression

- `python scripts/validate_epistemic_benchmark.py` → PASS: 12 benchmark cases,
  5 Draft 2020-12 schemas, cross-references and epistemic invariants valid.
- `python scripts/validate_knowledge_assets.py` → PASSED (14 nodes, 2 pathways,
  11 schemas) — unaffected, run as regression.
- All ten pre-existing cases are byte-identical to the pre-change baseline; only
  the case count (10→12), the category enum (+2), and the two new invariants
  changed.

## Scope note

As with all benchmark cases, these are **synthetic fixtures**: the quotations are
not external evidence and must never be cited as such. The validator checks
structural conformance and the pinned epistemic invariants; it does not judge
factual correctness or real claim–evidence entailment.
