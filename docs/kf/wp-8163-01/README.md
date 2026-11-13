# wp-8163-01 — source asset registration for report 8163

Work package: `wp-8163-01`, task_type `01-asset-registration`, lane C, report_id **8163**.
Scope: register the report's own source asset and every attachment / artefact / symbol the
report declares. **No extraction, no claim generation, no `verified` marks** — verification is
computed by the platform gate, not asserted here.

## Artefacts

| file | what it is |
|---|---|
| `asset_manifest.json` | the manifest: 9 assets, per-asset locators (char span + 1-based line span + verbatim quote + uniqueness), counts, probes, limitations |
| `kf_result.json` | the delivery envelope (`package_id`/`task_type`/`report_id`/`provenance`/`outputs`) — this exact object is the single `json` block of the published report |
| `verification.json` | self-check: the 6 contract acceptance items plus `do_not_mark_claims_as_verified`, each with a pass flag and a measured detail string; `coverage` records the enumeration-completeness cross-check |
| `locator_check.json` | every quote re-resolved against a freshly fetched markdown (occurrence count, char span, line) |
| `source.md` | committed read-only copy of the source markdown (7 785 chars / 11 158 bytes) |
| `asset_manifest.v1.wp8163.schema.json` | derived schema: `schemas/asset_manifest.v1.schema.json` with **only** its three `const`s retargeted (see below) |
| `report.md` | the six-section delivery report as published (contains exactly one ```json block) |
| `figures/asset_resolution_map.png` | asset class × resolution status |
| `figures/locator_coverage.png` | every locator's char span against the markdown length |

## Reproduce

```bash
export TENSOR_API_BASE=... TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=...
python3 scripts/kf/kf_wp8163_01_register.py all   # build + envelope + verify + figures
python3 scripts/kf/kf_wp8163_01_publish.py render # re-render report.md from the JSON
pytest -q tests/test_kf_wp8163_01.py              # 8 offline checks, no network
```

Order matters: `register.py all` refreshes the envelope timestamps, so `report.md` must be
re-rendered afterwards or the embedded block no longer equals `kf_result.json` (the test says so).

## Known limitation (deliberate, documented, not hidden)

`schemas/asset_manifest.v1.schema.json` pins `package_id`, `report_id` and `source.uri` with
`const` to `wp-448-01`, so no other work package can validate against it verbatim. `verify`
therefore validates the manifest against `asset_manifest.v1.wp8163.schema.json` — the shipped
schema with only those three `const` values replaced — and validates the envelope strictly
against `schemas/kf_result.v1.schema.json`. If the platform gate uses a differently-pinned
schema, the gate wins and this manifest must be revised.

References to files in the producing repository (`src/tensordem/…`, `tests/…`, `scripts/plot_…`)
are `referenced_unresolved`: they are not in this TensorKnowledge worktree and the platform
serves no payload for them. That is *not* a verdict that those files do not exist upstream.