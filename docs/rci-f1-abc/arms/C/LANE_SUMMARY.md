# RCI-F1 lane C — execution summary
- anchor: `KBM-RCI-F1-ABC`  batch_digest: `82f698cf0738271cea0b6af7b59edf631e002c27aa266acda00bae7a5266900d`
- manifest: `docs/rci-f1-abc/tk_work_packages.json` (digest `a025f4452aaaa1d16a79060cf28684eaa058f46cd4195e4def1da7b6ea3784ff`)
- **execution mode: single_agent_degraded_sequential** — agent_count=1. This lane was executed by one agent working sequentially through 20 work packages; it is **not** recorded as 20-agent parallelism. Lane B's paired mapping is taken from the same dispatch spec; this worktree contains no lane B receipts, so no paired comparison is claimed.

## Results (programmatic)

| metric | value |
|---|---|
| packages | 20 |
| docs | 60 |
| receipts_ok | 20 |
| reviews_passed | 20 |
| claims | 689 |
| locators_total | 1427 |
| locators_resolved | 1427 |
| locator_rate | 1.0 |
| claims_with_stated_conditions | 49 |
| quality_total_mean | 19.634 |

- locator resolution: `1427/1427` (rate 1.0) — resolved by `scripts/rci_f1_verify.py`, not self-reported.
- independent review: 20/20 packages `pass`, findings blocking/major/minor = 0/0/0.
- claim forms: `{"quantitative": 450, "observational": 126, "normative": 46, "comparative": 46, "methodological": 7, "definitional": 1, "architectural": 13}`
- drop reasons: `{"no_assertion_cue": 643, "boilerplate": 32, "too_short": 694, "table_header_row": 178, "table_separator_row": 179, "table_row_without_metric": 120, "low_content_tokens": 67, "question_not_assertion": 5, "near_duplicate": 10, "oversized_sentence": 1}`

## Per-package table

| package | docs | claims | locators | resolved | review |
|---|---|---|---|---|---|
| rci-f1-C-C01 | 3/3 | 34 | 69 | 69 | pass |
| rci-f1-C-C02 | 3/3 | 30 | 60 | 60 | pass |
| rci-f1-C-C03 | 3/3 | 38 | 80 | 80 | pass |
| rci-f1-C-C04 | 3/3 | 22 | 46 | 46 | pass |
| rci-f1-C-C05 | 3/3 | 31 | 63 | 63 | pass |
| rci-f1-C-C06 | 3/3 | 42 | 95 | 95 | pass |
| rci-f1-C-C07 | 3/3 | 42 | 84 | 84 | pass |
| rci-f1-C-C08 | 3/3 | 31 | 62 | 62 | pass |
| rci-f1-C-C09 | 3/3 | 32 | 69 | 69 | pass |
| rci-f1-C-C10 | 3/3 | 24 | 60 | 60 | pass |
| rci-f1-C-C11 | 3/3 | 33 | 67 | 67 | pass |
| rci-f1-C-C12 | 3/3 | 28 | 56 | 56 | pass |
| rci-f1-C-C13 | 3/3 | 42 | 84 | 84 | pass |
| rci-f1-C-C14 | 3/3 | 42 | 84 | 84 | pass |
| rci-f1-C-C15 | 3/3 | 42 | 84 | 84 | pass |
| rci-f1-C-C16 | 3/3 | 31 | 64 | 64 | pass |
| rci-f1-C-C17 | 3/3 | 34 | 68 | 68 | pass |
| rci-f1-C-C18 | 3/3 | 40 | 81 | 81 | pass |
| rci-f1-C-C19 | 3/3 | 33 | 70 | 70 | pass |
| rci-f1-C-C20 | 3/3 | 38 | 81 | 81 | pass |

## Contract deviations & limitations (honest)

1. **Degraded execution mode**: single agent, sequential; `agent_count=1`, `parallel=false` in every receipt (`runs/C/<package>.json`).
2. **Extractor is deterministic rule-based** (skill `rci-f1-extraction-v1`), not an LLM: `tokens=0` in receipts; tokens_note states rule-engine only. Claim statements are normalisations of verbatim source spans (canonical substring check enforced by the reviewer).
3. **Conditions**: only source-stated condition sentences co-located in the same block are recorded; anything else leaves `stated_in_source=false`, `scope="not-stated-in-source"`. Stated-condition claims: 49/689.
4. **No scientific validation**: every KO carries `status={mission:succeeded, review:pending, scientific_validation:not_assessed, epistemic_status:draft}`; the reviewer's pass is a *semantic/evidence gate*, not a scientific verification.
5. **Not run**: lane B↔C paired comparison (no lane B artefacts in this worktree), inter-annotator agreement, and expert domain adjudication of claim content.

## ① Case introduction

Corpus of 60 frozen engineering/scientific documents drawn from 15 repositories of the Tensor ecosystem (TensorBEM, TensorBench, TensorCAD, TensorDEM, TensorDG, TensorData, TensorFEM, TensorFVM, TensorKnowledge, TensorLBM, TensorPapers, TensorPhysics, TensorPlatform, TensorSPH, ship-performance-platform); document types {"analysis": 11, "creation": 8, "information": 8, "research": 33}, evidence tiers {"A": 35, "B": 11, "C": 14}. The unit of work is a *work package* (3 documents, the same doc→package mapping as lane B, which is the paired design). No physical geometry, mesh or solver parameter set applies here: the object under test is the extraction pipeline and its evidence discipline, not a hull or a flow field.

## ② Method

1. `scripts/rci_f1_extract.py` freezes each source file into `docs/rci-f1-abc/snapshot/<doc_id>/`, re-hashing bytes against the declared sha256 prefix (60/60 match) and decoding with `newline=''` so char offsets stay byte-consistent.
2. Block parser (headings / paragraphs / list items / table rows, fenced code and HTML comments skipped) → sentence splitter (CJK + Latin, abbreviation and decimal guards) → candidate filters (length, assertion cue, boilerplate, dedup Jaccard>0.85, content tokens ≥4) → six-dimension quality scoring (integer 0–5 per dimension, rubric attached) → acceptance threshold total ≥12, cap 14/doc (≤4 table rows).
3. Every accepted claim stores an exact locator `{path, lines, span, sha256, quote}`; conditions are recorded only when a condition/limit sentence is stated in the same source block, otherwise `stated_in_source=false` / `scope="not-stated-in-source"`.
4. `scripts/rci_f1_verify.py` re-resolves every locator from the snapshot (sha256 + span slice + line range) and runs the structural/evidence gates; `scripts/rci_f1_review.py` is the independent reviewer, which sees only the snapshot, the objects JSONL and the wp manifest, and rejects non-verbatim statements, invented conditions, doc-identity mismatches, duplicates and any epistemic over-claim.

## ③ Results

| quantity | value |
|---|---|
| work packages / documents | 20 / 60 |
| claims | 689 |
| locators re-resolved | 1427/1427 |
| claims with source-stated conditions | 49 |
| quality total mean (0–30) | 19.634 (min 12, max 28) |
| receipts complete / reviews pass | 20/20 / 20/20 |
| claim forms | {"quantitative": 450, "observational": 126, "normative": 46, "comparative": 46, "methodological": 7, "definitional": 1, "architectural": 13} |
| six-dim mean | {"locatability": 4.329, "specificity": 4.393, "verifiability": 4.628, "scope_clarity": 1.284, "non_triviality": 3.688, "evidence_density": 1.311} |

## ④ Figures

- `claims_per_doc.png`: claims per document (60 bars) with the mean line.
- `gates_per_package.png`: per-package claims vs locators vs resolved locators.
- `quality_profile.png`: six-dimension quality means and quality-total histogram.

## ⑤ Traps and scope

- **CRLF offset trap**: one snapshot contains CRLF; text-mode reading would shift every span. All readers use `newline=''`.
- **Markdown pipe trap**: naive `|` removal fuses table cells into invented tokens ('dragimpulsens'), which the reviewer correctly rejected as non-verbatim; `|`→space fixed it.
- **Bullet fusion trap**: contiguous bullets without blank lines merged into one mega-sentence (up to 17 lines, 1300 chars); bullets are now their own blocks and sentences >1200 chars are dropped.
- **Heading-as-condition trap**: treating a 'hypothesis/假设' heading as a scope statement produced fake conditions; the heading fallback was removed.
- Scope: extraction/evidence discipline only — never a claim that the underlying engineering results are scientifically correct.

## Error judgement (⑥)

No physical/experimental reference value applies to this task (document-level claim extraction), so a <3% numeric tolerance is **not applicable** and is not claimed. The measurable quantities here are exact-match invariants, and they are reported exactly:

| quantity | value | criterion | within tolerance |
|---|---|---|---|
| locator reverse-resolution rate | 1427/1427 = 1.0000 | span slice + line range + sha256 exact match | yes (0 mismatches) |
| snapshot identity | 60/60 docs sha256-prefix match | declared prefix exact match | yes |
| receipts complete | 20/20 | docs_completed=3 and gates pass | yes |
| independent semantic gate | 20/20 pass | 0 blocking findings | yes |
| statement fabrication | 0/689 non-verbatim | canonical containment of quote | yes |

The residual risk is not numeric drift but **selection bias** (rule filters keep 689 of the candidate sentences and drop 1929; 14-claim cap per document), which no exact-match invariant can quantify — it needs the lane B comparison, which was not run.
