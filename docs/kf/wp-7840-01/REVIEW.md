# Adversarial review — wp-7840-01 (report_id=7840, 01-asset-registration)

Reviewer position: self-review of my own package (independence limitation stated up front — no second agent
reviewed this). Method: re-derive every claim from the live platform source, then try to break the package.

## Scope / checks performed

| Check | How | Result |
|---|---|---|
| Source identity | re-fetch `GET /tensor/reports/7840`, recompute sha256 + char count | `eaf940b5…` = contract, 6896 chars = contract ✅ |
| Locator truth | every `locator.quote` compared to the exact line of the live markdown (`lines[n-1] == quote`) | 25/25 ✅ |
| Scanner completeness | second, independently written tokeniser over the whole body, diff vs registry | 16 tokens, 0 unregistered ✅ |
| Envelope schema | `jsonschema.validate` against `schemas/kf_result.v1.schema.json` | VALID; exactly one ```json block, byte-equal to `kf_result.json` ✅ |
| Id / count consistency | asset_id uniqueness; `counts.by_kind` re-derived from the asset list | 25 unique, counts agree ✅ |
| No overreach | no `verified` status anywhere; `claims=[]` | ✅ |

## Severity-ranked findings

**F1 — S2 (disclosed, non-blocking): 20 of 25 assets are `unresolved`.**
Registration proves the report *says* `backend/physics/acv/*.py`, `tests/test_acv_closed_chain.py`,
`artifacts/acv_in59_n09/*` exist — not that those bytes exist. The report's own tree
(`ship-performance-platform`) is outside this work package's boundary, and the platform exposes no
attachment listing (`/tensor/reports/7840/artifacts` → `http_404`, `/tensor/artifacts?report_id=7840` → `http_404`).
Downstream extraction must treat these as *citations*, not as readable sources.

**F2 — S2 (disclosed): 4 figures are `metadata_only`, `sha256=null`.**
`figures[]` stores `name`+`caption` only; `png_base64` is `""`. Any figure hash would be fabricated, so none is claimed.

**F3 — S2 (open, platform-side): figure payloads are not persisted even when submitted.**
This package's own report (id 14668) was published with a PNG; re-reading it returns
`figures[0].png_base64` length 0. Same root cause as F2: figure bytes cannot be re-verified from the
platform record, so no package can pin figure provenance from `figures[]`. Recorded, not worked around.

**F4 — S3 (found during this review, fixed before delivery): false-positive asset.**
The directory regex matched `V/` inside the inline math `V/√(gL_c)` (source L234), registering a bogus
directory asset. Fixed by requiring path segments ≥2 chars. Baseline comparison: 26 assets (1 bogus) → 25.

**F5 — S3 (found during this review, fixed before delivery): incomplete paths on L99.**
`static_equilibrium.py`, `leakage.py`, `wave_resistance.py`, `closed_chain.py` are cited bare, relative to the
``backend/physics/acv/`` directory named on the *same* line. Registering the bare name alone loses the parent.
Fixed by joining with that directory, while keeping `path_reference_literal` (verbatim) and setting
`path_reference_constructed=true` — an inferred path is never presented as a quote.

**F6 — S3 (disclosed): occurrence-level identity inflates ids.**
`tests/test_acv_closed_chain.py` appears on L101/L259/L276 → 3 asset_ids. Intentional (each carries its own
verbatim quote); dedupe view exposed as `summary.distinct_referenced_paths=13`.

**F7 — S4 (honesty note, not a defect): `all_claims_have_evidence_or_explicit_unresolved_status` is vacuous.**
`claims=[]` makes it pass trivially. It is reported as vacuous in `verification.json`, not as evidence of quality.

## Checks NOT run (marked not_run, not passed)

- claim extraction / claim–evidence binding — out of scope for task_type 01.
- existence/readability of the referenced `ship-performance-platform` files — outside the work package boundary.
- report_type classification — `objective.classify_report_type=false`.
- any numerical re-computation of the report's ACV resistance chain — other工序.

## Overstated claims

None found in the deliverables. The only `resolved` asset is the source markdown itself (bytes in hand).
No statement in the manifest or report implies the referenced code/artifacts were located.

## Disposition

**Approve with notes.** F1/F2/F3 are capability boundaries disclosed in the manifest `limitations` and the
report §⑤; F4/F5 were real defects caught by this review and fixed before delivery; F7 is a reporting honesty note.
Reproduction: `python3 scripts/kf/build_asset_manifest_7840.py build result verify && python3 -m pytest -q tests/test_kf_wp_7840_01.py`.