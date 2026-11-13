# wp-14214-01 — asset registration for report 14214

Work package: `wp-14214-01` · task_type `01-asset-registration` · report_id `14214` · lane B
Published result: report **14899** "KF-RESULT wp-14214-01" (tags `kf-wp:wp-14214-01`).
The worktree `report_body.md` and the published markdown are byte-identical; the
`kf_result.json` here is byte-identical to the single ```json block in that report.

## One-shot reproduction

```bash
# register assets (fetch + hash + locate + probe + emit), then verify independently
python3 scripts/kf_wp14214_01_register.py && python3 scripts/kf_wp14214_01_verify.py

# offline reproduction against the byte copy already in the package
python3 scripts/kf_wp14214_01_register.py --no-fetch && python3 scripts/kf_wp14214_01_verify.py

# deterministic emission (reproduces the published envelope's emitted_at)
KF_EMITTED_AT=2026-11-12T02:38:15+00:00 python3 scripts/kf_wp14214_01_register.py

# figures (read asset_manifest.json, no hand-typed numbers) and publish
python3 scripts/kf_wp14214_01_figures.py
python3 scripts/kf_wp14214_01_publish.py
```

## Artifacts

| file | content |
|---|---|
| `source.md` | byte copy of the registered markdown (8770 B / 6258 chars) |
| `sha256.txt` | independently recomputed digest |
| `locator_check.json` | one row per quote (line / char span / hit count / expansion rule) |
| `asset_manifest.json` | contract output: 24 assets + 6 integrity observations |
| `kf_result.json` | `kf_result.v1` envelope (schema-validated) |
| `selfcheck.json` | the 6 acceptance items + both schema validations |
| `verify.json` | 22 independent re-checks of the emitted files (all pass) |
| `report_body.md` | the published report body (six sections + one json block) |

## Boundaries respected

Only `GET /api/v1/tensor/reports/14214` was read; no other report_id was read or written.
No extraction, no classification, no claims (`claims: []`), nothing marked `verified`.
Referenced artifacts (png / tools / data / research_plan / registry) are registered as
`referenced_unresolved`: their bytes are not served by any endpoint (probe table in the report).
