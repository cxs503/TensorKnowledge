# wp-12073-01 — 01-asset-registration for report 12073

Work package contract: `task_type=01-asset-registration`, `report_id=12073`,
`source_uri=tensor://reports/12073`, `source_field=markdown`,
`source_hash=sha256:362fbe90ba196e81f94aa4f6dd9d74bc5f69c729e7eb9f99a125fb9415bea850`,
`chars=3446`. Objective: **register assets only** — no classification, no extraction,
no verified marking.

## What is here

| file | role |
|---|---|
| `asset_manifest.json` | the deliverable: 32 registered assets with verbatim locators (char span + line span + quote), resolution status and byte hashes |
| `kf_result.json` | `kf_result.v1` envelope; the manifest is embedded under `outputs["asset_manifest.json"]`; `provenance.source_hash` is the recomputed markdown hash |
| `KF-RESULT-wp-12073-01.md` | the publishable report — six sections, evidence table, and **exactly one** ```json block (the envelope above) |
| `verification.json` | machine verdicts for the six contract acceptance items (plus one advisory figure re-hash check) |
| `asset_manifest.schema.json` | local pin of the manifest shape (`package_id` / `report_id` are `const`) so `schema_pass` is reproducible instead of asserted |
| `source/report_12073.md` | byte-exact snapshot of report 12073's `markdown` (anchor for offline re-hashing) |
| `source/report_12073.record.json` | report record metadata (title / tags / figures list / timestamps), no markdown |
| `source/figures/*.png` + `source/figure_fetch.json` | the five figure payloads retrieved from `/tensor/reports/12073/figures/<name>` and their sha256 |
| `fig_asset_inventory.png` | asset class × resolution inventory chart (registration statistic, not a domain result) |

## Reproduce

```bash
python3 scripts/kf_wp12073_01_asset_manifest.py --fetch --build --verify
python3 scripts/kf_wp12073_01_asset_manifest.py --verify      # offline re-check of committed files
python3 -m pytest tests/test_kf_wp12073_01_asset_manifest.py -q
```

`--fetch` needs `TENSOR_API_BASE`, `TENSOR_AGENT_USER`, `TENSOR_AGENT_PASS` in the
environment (credentials are never written to the tree). `--verify` without `--fetch`
works on committed files; only the figure re-hash sub-check needs the network.

## Honest limits

- `claims=[]`: the contract explicitly allows an empty array and this package's objective
  has no extraction step, so no claim was manufactured.
- Code/module paths (`realtime.py`, `simulate.py`, `backend/modules/cii_tracking`, …) and
  regulatory file numbers (MEPC.353(78)/338(76), MEPC.364(79)) are `referenced_unresolved`:
  their targets live outside this checkout / are not readable offline. Nothing about their
  content is asserted.
- Figure hashes attest to the bytes served by the report figures endpoint at fetch time;
  they do not prove provenance from the simulation that produced the figures.
## Published result

The KF-RESULT report was published through `POST /tensor/reports` (the only result
channel). The API has no `PUT`/`DELETE` for reports (both return `405`), so the
publication history is append-only:

| report id | state | note |
|---|---|---|
| 14852 | superseded | first post; identical content but without §⑦ |
| 14855 | superseded | adds §⑦ (report-discipline six-element mapping) |
| **14857** | **authoritative** | final; §⑦ included, markdown byte-equal to `KF-RESULT-wp-12073-01.md` |

`emission.json` freezes the first-emission timestamp so that `--build` is byte-idempotent:
rebuilding after publication reproduces the published markdown exactly (checked).
