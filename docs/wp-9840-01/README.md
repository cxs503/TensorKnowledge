# wp-9840-01 — asset registration for report 9840

Work package `wp-9840-01` (`task_type=01-asset-registration`, lane C) over `tensor://reports/9840`
(IN65-N04 DG convection–diffusion verification surface). Scope: **register assets only** — no
claim extraction (`claims=[]` by contract), no numerical re-checking, nothing marked `verified`
(verification is computed by the platform gate).

Source identity (independent of this repo): `markdown`, sha256
`159d4a1419890fe82d46b49037d00273376244d1f24a6503e386c6243d882524`, 14 740 chars / 19 763 UTF-8 bytes,
title *IN65-N04 DG 对流–扩散验证面：旋转锥 / 制造解 / 间断传播（HLLC + 正性保持 + kink 阶上界）*.

## Result

| item | value |
|---|---|
| assets | 32 (26 `resolved_in_source` / 5 `referenced_unresolved` / 1 `declared_absent`) |
| claims | 0 (contract: `objective.register_assets` only, `classify_report_type=false`) |
| gate checks | 17/17 pass, overall `PASS` (`verification.json`) |
| negative control | 6/6 mutants rejected, pristine 0 failures (`negative_control.json`) |
| manifest sha256 | `acae6c5456e3d2fc426fd88150ddd98c7557290f90b34034304d69cc4169affd` |
| published report | platform `report_id=14752`, title `KF-RESULT wp-9840-01`, tag `kf-wp:wp-9840-01` |

`14738` and `14749` are earlier drafts of the same package (no update/delete API exists for platform
reports). Their defect: the envelope carried the source report's own ```` ```bash ```` fences
(full-document asset + whole-section repro quote), so the "exactly one ```json block" requirement was
ambiguous for fence parsers. The final version drops the document-level asset (the whole text is
registered by `source.hash` instead) and quotes only the 5 command lines inside the fence;
`fence_markers=2` is now a machine-checked invariant.

## Files

| file | content |
|---|---|
| `asset_manifest.json` | the deliverable: 32 assets with char/line locators, resolution status, per-asset `resolution_check` |
| `kf_result.wp-9840-01.json` | result envelope (byte-identical to the json block in the published report) |
| `verification.json` | 17 gate checks (re-runs against the live API) |
| `negative_control.json` | mutation test of the gate itself |
| `postcheck_publish.json` | post-publish check: 1 fence pair, 1 json block == envelope, tags, 6 sections |
| `source_report_9840.md` | frozen source markdown (byte-identical, hash-verified) so tests run offline |
| `fig_asset_locator_map.png` | figure 1: asset spans over the source char axis + resolution/class breakdown |
| `KF-RESULT-wp-9840-01.md` | full six-section report as published |

## Reproduce

```
python3 scripts/kf_fetch_9840.py && python3 scripts/kf_register_9840.py && \
python3 scripts/kf_verify_9840.py && python3 scripts/kf_9840_negative_control.py && \
python3 scripts/kf_figures_9840.py && python3 scripts/kf_9840_durable.py && \
python3 -m pytest tests/test_kf_9840_asset_manifest.py -q
```

`KF_DRY_RUN=1 python3 scripts/kf_report_9840.py` rebuilds the report markdown without publishing.
A clean `rm -rf artifacts/wp-9840-01 runs/wp-9840-01` + rerun reproduces the manifest byte-for-byte
(sha256 above), so the pipeline is deterministic.