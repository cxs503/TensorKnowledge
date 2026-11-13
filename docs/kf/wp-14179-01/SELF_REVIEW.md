# SELF_REVIEW — wp-14179-01 (adversarial self-check)

**Independence limitation (stated up front)**: the reviewer and the producer are the same agent
in the same worktree. This is *not* an independent review; the contract sets
`review.required: false` and `verification` is computed by the platform gate. What follows is a
deliberate attempt to break my own deliverable, with the same evidence standard demanded of a
third party.

**Reviewed artifacts**: commit `340c7a9` (+ template-only follow-up) — `artifacts/wp-14179-01/asset_manifest.json`,
`docs/kf/wp-14179-01/*` (mirror, envelope, locator check, verification, source snapshot, report body,
published record), `scripts/kf_wp14179_01_{register,verify,report}.py`, `tests/test_kf_wp14179_01.py`,
published report **14892**.

## Probe list (what was attacked)

| # | Attack | Result |
|---|---|---|
| 1 | Re-fetch the source by a second network call and re-hash (does the register script's in-memory copy lie?) | `scripts/kf_wp14179_01_verify.py` fetches the markdown fresh and recomputes sha256 = `2352b96c…59315` = contract = manifest = envelope. PASS |
| 2 | Off-by-one / mis-sliced quotes (`md[start:end] == quote`, line offsets self-consistent) | 27/27 PASS, recomputed twice (register + verify + pytest) |
| 3 | Anchor that is not unique (silent capture of the wrong occurrence) | anchors are required to hit exactly once, else the register script aborts; two anchors were in fact rejected at build time (`2 hits` for the repro_cmd anchor) and fixed by narrowing, not by loosening the check |
| 4 | Duplicate / reused asset ids, counts drifting from the asset list | 27 ids, all distinct, `counts.by_resolution/by_class` recomputed from the list. PASS |
| 5 | Fabricated information (numbers typed by hand, quotes paraphrased, "verified" stamped) | claims=[]; `verification_status=not_verified`; every quote is a machine-sliced substring; the two row/column counts of the registered tables are computed from the quotes, and the one hand-typed count found during self-review (the "10 × referenced_unresolved" token in report §⑤) was replaced by a template injection — the re-render is byte-identical to the published body, so no re-publish was needed |
| 6 | False resolution status for assets that are not actually retrievable | figures are `resolved_in_source` **because** `record.figures[].name` matches, and the check records `payload_downloaded=false`; all 10 external repo paths are `referenced_unresolved` even where the host path exists (A26 probe recorded as informational only) |
| 7 | Artifact-fetch endpoints overlooked (could the PNG/JSON payloads be resolved after all?) | probed with Bearer: `/openapi.json`, `/tensor/reports/14179/artifacts`, `/tensor/reports/14179/figures`, `/tensor/artifacts?report_id=14179` → **all 404**. So metadata-only resolution is the platform's ceiling, not a shortcut I took |
| 8 | Envelope not equal to the manifest it claims to output | `outputs["asset_manifest.json"]` is JSON-equal to the artifact; envelope validates against `schemas/kf_result.v1.schema.json` (draft 2020-12), manifest against the pinned draft-07 schema |
| 9 | Report body smuggling a second JSON block or a rewritten envelope | exactly one fenced `json` block, JSON-equal to `kf_result.json`; published copy re-fetched from the platform is byte-identical (`published.json.roundtrip_identical=true`) |
| 10 | Boundary leakage (touching other report_ids or upstream artifacts) | only `GET /tensor/reports/14179` was read; the only write was the creation of my own result report 14892; no upstream file was modified |

## Findings (severity ranked)

1. **MEDIUM — figures are metadata-level only.** `A18/A19` are registered `resolved_in_source`
   with `resolution_check.result=present`, which a downstream consumer could misread as "PNG
   retrievable". Mitigation: the check payload states `payload_downloaded=false`, this review and
   report §⑤ item 3 state it again, and probe #7 shows no endpoint serves the payload.
2. **LOW — table data intentionally not extracted** (`A16` S4 table, `A21` error table: structure
   only, `data_rows`/`header_cells`). A downstream extraction package must re-derive values from the
   quotes; this package must not be read as a data source.
3. **LOW — upstream claims are not verified here.** `scripts/run_calib_reflux.py` was **not** run and
   `backend/tests/test_calib_reflux.py` (17 tests) was **not** re-run — both belong to
   ship-performance-platform, absent from this worktree. Nothing in this package asserts they pass.
4. **LOW — pinned schema is local.** `asset_manifest.v1.wp-14179-01.schema.json` is my own pinning of
   the shape used; if the platform-side manifest schema is stricter, the platform gate wins and this
   artifact must be revised.
5. **INFORMATIONAL — host probes are non-portable.** `A26` records that the two absolute paths exist
   on *this* host; that fact is recorded as an information bit only, never as resolution.

## Checks not run (marked not_run, not "passed")

- live `scripts/run_calib_reflux.py run` / `verify` (upstream repo absent) — not_run
- `backend/tests/test_calib_reflux.py` 17 tests (upstream repo absent) — not_run
- PNG payload download / visual inspection of the upstream figures — not_run (no endpoint, probe #7)
- independent (third-party) review — not_run (contract: review.required=false)

## Overstated claims?

None found in the deliverable: no claim objects, no `verified` status, `verification_status=not_verified`,
and the report states plainly that the upstream numbers are quoted, not recomputed.

## Disposition

**approve with notes** — blocking checks all pass (`verification.json.all_passed=true`, `pytest 9 passed`);
findings 1–5 are documentation-level risks already disclosed in the manifest checks and report §⑤.
The next worker on this report (extraction package) should treat A08/A11/A12/A25 as reachable-only-
upstream, and treat A16/A21 as structure-only.