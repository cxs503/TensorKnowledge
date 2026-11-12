# wp-6511-01 — asset registration of report 6511

Work package: `wp-6511-01` (task_type `01-asset-registration`, lane C), report_id **6511**
`IN31-L02: TensorLBM Conjugate Heat Transfer (CHT) Validation Ladder`.

Registration only. No claim extraction, no report-type classification, no `verified` marks —
verification is computed by the platform gate.

## Result

| item | value |
|---|---|
| markdown sha256 | `sha256:e27b9986b028ac9402f4e90705919fc2aea826da4c47de48224665231fc2d840` (= contract) |
| chars / bytes / lines | 4405 / 4459 / 112 |
| assets registered | 15 (resolved 5, metadata_only 2, unresolved 7, absent 1) |
| markdown locators | 13/13 resolvable (quote is a unique substring on the declared line) |
| record locators | 2/2 (`figures[0].name`, `figures[1].name`) |
| figures with bytes | 0 (5 probe paths all HTTP 404) |
| claims | 0 — empty array + `claims_empty_reason` (contract note: claims 允许为空数组) |
| acceptance | 6/6 PASS (`runs/wp-6511-01/verify_out.json`) |

## Files

| path | role |
|---|---|
| `docs/kf/wp-6511-01/asset_manifest.json` | main deliverable (asset manifest v1 shape) |
| `docs/kf/wp-6511-01/kf_result.json` | platform result envelope = the report's single ```json block |
| `docs/kf/wp-6511-01/asset_manifest.schema.json` | package-scoped shape pin (repo `schemas/asset_manifest.v1.schema.json` hard-codes package_id=wp-448-01) |
| `docs/kf/wp-6511-01/report.md` | report body as published (platform report id 14671) |
| `docs/kf/wp-6511-01/figures/asset_inventory.png` | asset inventory figure, generated from the manifest |
| `runs/wp-6511-01/source_6511.md` | byte copy of the source markdown (single origin of every quote) |
| `runs/wp-6511-01/source_6511_record.json`, `figure_probe.json` | record snapshot, figure-endpoint probes |
| `runs/wp-6511-01/fetch_source.py`, `probe_figures.py`, `register_6511.py`, `verify_6511.py`, `make_figure.py`, `build_and_publish.py` | full pipeline |
| `runs/wp-6511-01/verify_out.json`, `publish_response.json` | self-check output, publish response |

## Reproduce

```bash
cd TensorKnowledge
python3 runs/wp-6511-01/fetch_source.py
python3 runs/wp-6511-01/probe_figures.py
python3 runs/wp-6511-01/register_6511.py
python3 runs/wp-6511-01/verify_6511.py      # exit 0 iff all 6 acceptance items pass
python3 runs/wp-6511-01/make_figure.py
python3 runs/wp-6511-01/build_and_publish.py  # optional: (re)publish the report
```

`register_6511.py` fails loudly (`exit 2`, no artifact written) if the contract hash/chars do not
match, or if any quote is not a unique substring on its declared line — it cannot emit a guessed
locator. `verify_6511.py` re-derives the source hash from a fresh `GET /tensor/reports/6511`
rather than from the local copy.

## Findings recorded, deliberately not resolved

1. **Figure declaration inconsistency**: §4 "See attached figures for:" lists 4 numbered figures with
   descriptions only (no filename/link), while the record declares 2 (`cht_fig1`, `cht_fig2`) with
   name+caption and no bytes. The two sets cannot be mapped 1:1 from the text, so the 4 body
   declarations stay `unresolved` and the 2 record figures stay `metadata_only`. No merge, no guess.
2. **No file-path artifacts at all**: a path-token scan (`.*\.(py|png|json|csv|md|ipynb|pdf|txt|dat|h5|npz)`)
   over the markdown returns 0 matches; the only fenced block is a formula, not code. Registered as one
   `absent` asset (no repro command / script / seed in the report).
3. **Downstream flag for 03-extraction** (not promoted to a claim here): the §6 table marks C1 (target
   `<3%`, achieved `<5%`), C2 (`<5%` / `<15%`) and C5 (`<5%` / `<20%`) as ✅ although the achieved value
   exceeds the target. Whether those count as passes is a claim-level judgement for the extraction /
   verification lane.