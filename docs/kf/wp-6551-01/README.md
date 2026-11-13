# wp-6551-01 — report 6551 asset registration

Work package `wp-6551-01` (`task_type: 01-asset-registration`, lane C) registers the source
asset of **report 6551 only** and enumerates the attachments / artefacts that report declares.
Scope is registration: no claim extraction, no report-type classification, no `verified` mark
(that verdict belongs to the platform gate).

The numeric facts (hash, char/byte counts, locator offsets, counts) live in
`asset_manifest.json` / `verification.json`; this file deliberately does not restate them, so
there is no second place for them to drift.

## Artefacts

| file | role |
|---|---|
| `asset_manifest.json` | the registration payload (`asset_manifest.v1`); every asset carries a verbatim quote, char span, line number and a resolution status + reason |
| `kf_result.json` | the result envelope submitted to the platform (`schemas/kf_result.v1.schema.json`), `outputs.asset_manifest.json` |
| `verification.json` | the 6 contract acceptance checks, machine-evaluated, plus the `not_checked` list |
| `figures/wp6551_source_locator_map.png` | source line profile with the asset anchors and the per-class counts |
| `../../runs/wp-6551-01/source_6551.md` | byte-exact copy of the markdown served by `GET /api/v1/tensor/reports/6551`; every locator can be re-derived from it offline |

## Resolution vocabulary

* `resolved_in_source` — the bytes are obtainable and were hashed here (the source markdown itself).
* `referenced_unresolved` — the report declares it but this work package cannot obtain the bytes
  (figure endpoint answers HTTP 404; TensorLBM-side paths are not in this worktree; a declared
  digest is printed truncated). Always carries `searched_scopes` + `reason`; **never** a claim of absence.
* `declared_absent` — the report itself states the artefact does not exist. Not used here.

Widening the search is a re-run, not an edit: `KF_RESOLVE_EXTRA_ROOTS=/path/to/TensorLBM`.

## Re-run

```bash
python3 scripts/kf_wp6551_fetch.py                               # fetch + byte copy (needs platform token)
python3 scripts/kf_wp6551_register_assets.py all                 # build → envelope → verify → figure
KF_OFFLINE=1 python3 scripts/kf_wp6551_register_assets.py verify  # offline re-check against runs/ copy
python3 -m pytest tests/test_kf_wp6551_registration.py -q        # regression + negative control
python3 scripts/kf_wp6551_report.py --check                      # report body ⇄ envelope consistency
```

The schema used for `schema_pass` is `schemas/asset_manifest.v1.generic.schema.json`: the
package-agnostic form of `schemas/asset_manifest.v1.schema.json` (same shape, package/report
constants relaxed to patterns), so other `01-asset-registration` packages can be gated the same way.