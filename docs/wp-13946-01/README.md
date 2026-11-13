# wp-13946-01 — asset registration for report 13946

Work package: `wp-13946-01` · task_type `01-asset-registration` · lane C · status draft.
Source: `tensor://reports/13946` field `markdown`,
`sha256=eb37b6effecdfc9396ded7a80f236173e234f2785fd984a948efba4a9b671072` (contract match), `chars=5534`.
Delivered KF-RESULT report on the platform: id `14878` (title `KF-RESULT wp-13946-01`,
tag `kf-wp:wp-13946-01`).

## What was registered

`23` assets: `14` resolved_in_source,
`8` referenced_unresolved, `1`
declared_absent. `claims=[]` — this package registers assets only; nothing is marked verified.

## Files

| path | role |
|---|---|
| `docs/wp-13946-01/asset_manifest.json` | committed manifest (byte-identical to the `artifacts/` build output) |
| `docs/wp-13946-01/kf_result.json` | result envelope = the single json code block of the delivered report |
| `docs/wp-13946-01/KF-RESULT_wp-13946-01.md` | exact markdown delivered to the platform |
| `docs/wp-13946-01/fig1_asset_coverage.png` | coverage figure — delivered bytes sha256 `5fe3f213cfa45bee73bc2d8728753b2f6847b400bda29f0aa9d64c7426aae000` = local (`122663` bytes, identical=True) |
| `docs/wp-13946-01/verification.json` | independent re-check of every acceptance item |
| `docs/wp-13946-01/published.json` | platform response for the delivered report |
| `schemas/asset_manifest.wp-13946-01.schema.json` | package-pinned schema (the shared one hard-codes another package's ids) |

`artifacts/` and `runs/` are gitignored (`artifacts/` by .gitignore + push gate), so the committed
copies live here under `docs/`; scripts write both trees.

## Reproduce

```
python3 scripts/kf_fetch_13946.py        # GET report 13946, sha256 gate
python3 scripts/kf_register_13946.py     # build manifest (unique-quote assertions)
python3 scripts/kf_verify_13946.py       # independent re-check (does not import the builder)
python3 scripts/kf_figures_13946.py      # figure, self-consistent with the manifest
python3 scripts/kf_publish_13946.py      # render + POST the KF-RESULT report
python3 scripts/kf_probe_figure_13946.py # fetch the delivered figure bytes, compare sha256
python3 scripts/kf_notes_13946.py        # this file
python3 -m pytest tests/test_kf_wp13946_01_asset_manifest.py -q
```

## Verification snapshot

| check | result |
|---|---|
| `valid_json` | PASS |
| `source_hash_matches` | PASS |
| `schema_pass` | PASS |
| `no_duplicate_ids` | PASS |
| `source_locator_resolvable` | PASS |
| `all_claims_have_evidence_or_explicit_unresolved_status` | PASS |
| `no_asset_marked_verified` | PASS |
| `scope_single_report` | PASS |

Fresh-checkout behaviour (verified in a scratch copy without `artifacts/`/`runs/`): 4 passed,
2 skipped — the two that need generated trees report `skipped`, never `passed`.

## Limits

1. The API is the only source channel: direct `psql -d tensorplatform` on `tensor_reports` is denied
   (`permission denied for table tensor_reports`), so hash equality is established against the API
   bytes only.
2. Cross-repo artifacts (`src/tensordem/shear_cell.py`, `scripts/m14840/*.py`,
   `artifacts/shear_cell_m14840/*.json`, `docs/SHEAR_CELL_SERVO_AUDIT_M14840_tables.md`,
   `tests/test_shear_cell_servo_audit_m14840.py`) are registered as `referenced_unresolved`: the
   report gives no commit/URL, and this package does not reach into other repositories.
3. The report's own figure (`../figures/shear_cell_m14840_servo.png`) is registered as a link only;
   its bytes are not in this worktree and the platform record carries name+caption only.
4. No claim of this package asserts that the source report's conclusions (servo offset fixed,
   μ vs experiment < 10 %) hold. Registration is not verification.
5. Unrelated tests in `tests/kf/` and `tests/test_kf_wp448.py`-style packages fail on a fresh
   checkout because they read gitignored `runs/` / `artifacts/` trees; that predates this package
   and was left untouched (single-report boundary).
