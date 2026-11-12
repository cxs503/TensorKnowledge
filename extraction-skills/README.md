# Extraction Skill Library

Reusable extraction programs for the report-to-knowledge production line
(spec: `docs/production/PRODUCTION-LINE-v1.md` §4). One skill = one report type =
one set of machine-followable steps. A skill is **not** a prose hint: every step
is either `deterministic: true` (a program can execute it) or explicitly marked as
needing a reader, and every skill must state the signals that select it.

## Six report types (initial skeleton)

| skill_id | report type | file |
|---|---|---|
| `xsk-literature-review` | literature-review | `literature-review.md` |
| `xsk-scientific-computation` | scientific-computation | `scientific-computation.md` |
| `xsk-algorithm-implementation` | algorithm-implementation | `algorithm-implementation.md` |
| `xsk-software-engineering` | software-engineering | `software-engineering.md` |
| `xsk-technical-proposal` | technical-proposal | `technical-proposal.md` |
| `xsk-experimental-validation` | experimental-validation | `experimental-validation.md` |

## Lifecycle (enforced by `ke.wp_gate.validate_skill_registry`, rules K1–K6)

```
candidate ──► template-created ──► sample-tested ──► independent-review ──► registered ──► deprecated
             (file exists)        (≥1 passing      (recorded review       (review event id
                                   sample report)   by someone else)       + reuse counter)
```

Promotion is a machine decision, not a self-declaration:

- **identify whether one exists** — search `registry.json` by `report_type` and
  `identify_signals` before writing anything new (reuse beats invention; a second
  skill for the same type+signals is a defect).
- **no skill → create the template** — copy `_TEMPLATE.md`, state the signals,
  keep steps deterministic where possible. State = `template-created`.
- **representative sample test** — run one real report of that type through the
  full line (G1+G2+G3). Only a passing package moves the skill to
  `sample-tested`, and `sample_tests[]` must carry the report id and source hash.
  *The synthetic fixtures under `tests/fixtures/extraction/` do not count: they
  test the gate, not the skill's fitness for real reports.*
- **independent review** — a reviewer who is not the skill author records a
  review event; state = `independent-review`.
- **register** — `reuse_count` starts at 0 and is incremented by the production
  runner on each reuse; state = `registered` (requires `review_event_id`).
- **deprecate** — a registered skill that stops matching its report type (format
  drift, repeated G3 failures) is set to `deprecated` with a written reason. Never
  delete: the history of a bad extractor is negative knowledge.

## Honest current state (2026-11-12)

All six skills are at **`template-created`**: the skeletons and their
identification signals exist, but no *real* report of these types has yet been
run through the full line, so no skill is claimed as `sample-tested` or
`registered`. The lifecycle transitions themselves are exercised by
`tests/test_wp_gate.py` on copies of the registry — a test of the rules, not
evidence about a skill.

## Direction reference

CACHE-ED2: for a new document format, first generate a reusable extractor, then
execute it deterministically for every later document of that format. The skill
file is that extractor's specification; `ke/wp_gate.py` is the executor of the
checks that decide whether its output is acceptable.