# wp-11924-01 — asset registration of report 11924

Package: `wp-11924-01` · task_type `01-asset-registration` · lane C · contract_version 1.0
Source: `tensor://reports/11924` (field `markdown`)
Title: BPM 微观参数三目标联合标定的可行性判定与可辨识性审计（P270W2C-N08）
Source identity: `sha256:21d915c88bbf78f6f90384f52ce2001f1d7709306c373b159625154ab221bd73`, 13138 chars / 22299 bytes UTF-8

## Deliverables (durable copies — `artifacts/**` is dropped by the push gate)

| file | content |
|---|---|
| `KF-RESULT-wp-11924-01.md` | report body; exactly one fenced `json` block = the result envelope |
| `asset_manifest.json` | byte-identical mirror of `artifacts/wp-11924-01/asset_manifest.json` (42 assets, 22 classes) |
| `verification.json` | mirror of `artifacts/wp-11924-01/verification.json` (13 self-checks, overall PASS) |
| `fig_asset_inventory.png` / `fig_locator_coverage.png` / `fig_verification.png` | figures 1–3 |

## Scope discipline

* only report `11924` is read or written — no other report_id appears in the artifacts (checked by
  `report_scope_isolation` in the verifier);
* no claims are extracted (`claims: []` — legal by contract, `objective.classify_report_type: false`);
* nothing is marked `verified`: the envelope records `verification_status = not_verified`, verification is
  the platform gate's job;
* every `quote` in the manifest is a character slice of the source markdown, never a retyped string.

## Reproduce

```bash
python3 scripts/kf_fetch_11924.py            # GET /tensor/reports/11924 + sha256 gate
python3 scripts/kf_wp11924_01_register.py    # anchor table -> char spans -> asset_manifest.json
python3 scripts/kf_wp11924_01_verify.py      # independent re-fetch + 13 acceptance self-checks
python3 scripts/kf_wp11924_01_figures.py     # figures 1-3
python3 scripts/kf_wp11924_01_report.py      # build + publish KF-RESULT (--no-post to build only)
python3 -m pytest tests/test_kf_wp11924.py -q   # 23 invariants, 11 of them negative controls
```

Expected: `asset_manifest.json` sha256 `3d09203c46705aa4833bfbaf48c165b62498773f6d063872b4438524e272c360`
reproduced byte-for-byte; `verification.json` overall `PASS`.