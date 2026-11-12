# wp-448-01 — report 448 asset registration

Work package `wp-448-01` (`01-asset-registration`, lane C) for `report_id=448`
《EX-1 水池锚定①: DTMB 5415 艏部线型优化问题规格与预注册》
(scenario_key `EX-1_tank_anchoring_dtmb5415_bow_optimization`, source markdown
sha256 `a3e7910fbcbe3624805a875ebd9a033c54036a1950cdc2885a6fc739dbcabea8`, 3233 chars).

## What was done

Registered 22 assets of report 448 with char-span locators sliced directly out of the report markdown
(no hand transcription; every quote asserted to be a unique substring):

- 16 `resolved_in_source` — locator re-resolves inside the report text
- 4 `referenced_unresolved` — A17 exact STL (164926 faces), A18 Zenodo point cloud (2250 points),
  A19 the five `docs/ex1/*` deliverables, A20 external commit `78ed109`; no address in the report and
  the files/objects do not exist in this worktree (machine-checked, see `verification.json`)
- 2 `declared_absent` — no figures in this stage (platform `figures` field is `[]`)
- `claims: []` — the contract asks for registration only (`objective.register_assets: true`,
  `classify_report_type: false`), so no claim extraction was performed and nothing is marked verified.

## Files (docs/ holds the commit-durable, byte-identical copies)

| file | what |
|---|---|
| `asset_manifest.json` | main deliverable (= `artifacts/wp-448-01/asset_manifest.json`) |
| `verification.json` | acceptance self-check results, overall PASS |
| `kf_result.wp-448-01.json` | result envelope; its single ```json block is the published report |
| `fig_asset_inventory.png` | asset classes × resolution status |
| `fig_locator_coverage.png` | char-span map of the 21 span-level assets |
| `fig_verification.png` | acceptance-check board |
| `KF-RESULT-wp-448-01.md` | the report body as published (platform report 14589) |

Shape constraint: `schemas/asset_manifest.v1.schema.json` (written locally, because the canonical
`schemas/kf_result.v1.schema.json` named by the contract is absent from this worktree).

## Why docs/ and not artifacts/

This repo's push gate (`/root/tp-agent/tp_pusher.py`, `_EXCLUDE = ^(artifacts?/|runs/|results[-/]|REPORT_GATE)`,
`_EXCLUDE2` drops `*.png` outside `docs/`) discards `artifacts/**` and `runs/**` before the branch reaches
GitHub. So the worktree keeps the artifacts at the paths referenced by the published report
(`artifacts/wp-448-01/…`, `runs/wp-448-01/…`) and `docs/wp-448-01/` carries byte-identical copies that
survive the gate; `scripts/kf_verify_448.py` check `durable_mirror_identical` (and
`tests/test_kf_wp448.py`) fail if the two copies ever diverge.

## Reproduce

    python3 scripts/kf_fetch_448.py && python3 scripts/kf_register_448.py \
      && python3 scripts/kf_verify_448.py && python3 scripts/kf_figures_448.py \
      && python3 -m pytest -q tests/test_kf_wp448.py

`asset_manifest.json` is byte-reproducible: wiping `artifacts/wp-448-01/` and rebuilding yields
sha256 `0a99a0612fc50f8deb1444ecc9566f50cc0ef4d12dc94157405e9ff686edafde` again.

## Publication note

Published report: platform id **14589**, title `KF-RESULT wp-448-01`, tag `kf-wp:wp-448-01`,
mission 15510. That report carries the 11-check snapshot; `verification.json` here additionally includes
the post-publication check `durable_mirror_identical` (12 checks), added after the commit-layout question
was resolved. The result JSON itself did not change (manifest hash identical), so the published block
remains the authoritative submission.
