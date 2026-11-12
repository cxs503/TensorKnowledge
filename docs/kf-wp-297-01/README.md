# wp-297-01 — report_id=297 asset registration

Lane C / task_type `01-asset-registration` / contract `1.0`. Scope: **registration only**
(the source asset identity + the artifacts the report references). No extraction, no
classification, no claim verification, no writes to any other report_id.

## Result

* source: `tensor://reports/297`, field `markdown`, 1633 chars,
  `sha256:426c49ee6920408fa082092a086ef85edf1da0d566a63dfad66dba81549cc77a` (matches the work-package contract byte for byte)
* `asset_manifest.json` — 6 referenced assets / 7 machine-resolvable locators, 3 identity claims (all `supported`, none `verified`)
* resolution status split: `unresolved` 1 · `unresolved_no_path` 1 · `unresolved_external_service` 1 · `reference_only_not_retrieved` 3
  (nothing was guessed: the geometry file has no name in the source, and `artifacts/dtmb_resistance.json` is not shipped with the report payload — `figures` is empty)
* self-checks: `checks.json` 9/9 · independent re-check: `verify_delivery.json` 15/15

## Files

| file | role |
|---|---|
| `asset_manifest.json` | **deliverable** consumed downstream (schema `kf.asset_manifest.v1`) |
| `kf_result.wp-297-01.json` | body of the single fenced json block in `docs/kf-wp-297-01.md` |
| `source_report_297.md` | byte-exact snapshot of the source markdown (offline hash re-computation) |
| `build_manifest.py` | fetch → hash → regex scan → locators → self-check (`--refresh-source` to replay) |
| `build_report.py` | renders `docs/kf-wp-297-01.md` + `/tmp/report_wp29701.json` (all numbers injected, zero hand copy) |
| `verify_delivery.py` | re-derives everything from the delivered artefacts (does not trust the builder) |
| `publish_report.py` | POSTs the report to `$TENSOR_API_BASE/tensor/reports` |
| `checks.json`, `verify_delivery.json`, `readback.json` | gate evidence (builder self-check, independent re-check, platform readback) |
| `figures/asset_locator_map.png` | reference line numbers by type + resolution status counts |

## Reproduction

```bash
python3 artifacts/kf-wp-297-01/build_manifest.py --refresh-source
python3 artifacts/kf-wp-297-01/build_report.py
python3 artifacts/kf-wp-297-01/verify_delivery.py
python3 artifacts/kf-wp-297-01/publish_report.py   # optional: re-publish
```

## Committed mirror (why there are two copies)

This repository's `.gitignore` drops `artifacts/**` (run-record area), so the working
products would not survive the branch push. `sync_mirror.py` copies the byte-identical
set into the committed path `docs/kf-wp-297-01/` and verifies `sha256(copy) == sha256(source)`
(`docs/kf-wp-297-01/mirror_manifest.json`). The mirror step is deliberately **not** part of
the report's `repro_cmd`: it does not touch the manifest or the report text, so refreshing
it cannot invalidate the published report (`docs/kf-wp-297-01.md` ↔ platform report 14572).

## Platform delivery

Report `KF-RESULT wp-297-01` published as report_id **14572** (mission 15505,
`scenario_key=dtmb5415_benchmark`, tag `kf-wp:wp-297-01`). Readback verified in
`readback.json`: markdown returned byte-identical (9923 chars), exactly one fenced
json block, embedded `provenance.source_hash` equal to the contract hash.

## Limits (honest)

* `schema_pass` could not be machine-checked: `schemas/kf_result.v1.schema.json` does not
  exist in this repository (verified by a full-tree search). The structure follows the
  contract literally (`package_id/task_type/report_id/provenance/outputs`) and a
  `contract_input_fields_present` check asserts all seven contract input fields; a real
  schema gate, if one exists platform-side, remains authoritative.
* The hash is computed over the raw `markdown` string (no newline/encoding normalisation);
  a consumer that normalises first will get a different digest.
* `artifacts/dtmb_resistance.json` and the unnamed `ASCII STL` geometry were **not**
  fetched — out of scope for this work package and out of the single-report boundary.