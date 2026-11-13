# wp-11267-01 — asset registration for report 11267

KF work package `wp-11267-01` · task_type `01-asset-registration` · lane C · source
`tensor://reports/11267` (`markdown`).

**Scope**: register the source asset identity (report_id + markdown byte hash) and the
attachments/artifacts the report declares. No claim extraction, no report-type
classification, no `verified` marks, and no other `report_id` is read or written.

## Result at a glance

| item | value |
|---|---|
| source sha256 (recomputed here) | `sha256:2ca7aed6b4a376b61e38173425b70566dea93e4c0ce7695600091b9eb6de5a9f` |
| contract hash match | yes (chars 7482 = contract) |
| title / scenario_key match | yes, `p284w3-n04-fem-mpi-parallel` |
| assets registered | 23 (1 source document + 22 declared artefacts) |
| resolved with payload hash | 8 (7 PNG figures, byte-served by `GET /tensor/reports/11267/figures/<name>`) |
| declared but outside this worktree | 8 (`src/tensorphysics/fem_parallel/`, `scripts/fem_parallel_*.py`, `artifacts/fem_parallel/verification.json`, `tests/test_fem_parallel_*.py`, one test symbol) |
| declared absent by the report itself | 7 (C1/C2/C4 not measured, MPIComm backend not measured locally, cluster jobs cj308/cj313/cj314) |
| locators re-resolved verbatim | 34 |
| claims | `[]` (by contract: `classify_report_type=false`) |
| self-check | 6/6 acceptance + 3/3 integrity checks pass |

## Files

| path | content |
|---|---|
| `docs/kf/wp-11267-01/asset_manifest.json` | the package output (23 assets, locators, counts, `claims=[]`) |
| `docs/kf/wp-11267-01/kf_result.json` | result envelope, `outputs["asset_manifest.json"]` + `provenance.source_hash` |
| `docs/kf/wp-11267-01/asset_manifest.schema.json` | pinned schema for this package (so `schema_pass` is reproducible) |
| `docs/kf/wp-11267-01/verification.json` | 9 checks with metrics and verdict |
| `docs/kf/wp-11267-01/figures/asset_registration_map.png` | asset↔source-line map + self-check strip |
| `docs/kf/wp-11267-01/figure_section_tags.json` | S1..S7 section-tag → line map used by the figure |
| `docs/kf_result_wp-11267-01.md` | the KF-RESULT report (six sections + the single `json` block) |
| `runs/wp-11267-01/source_11267.md` | verbatim source snapshot used for offline re-checks |
| `runs/wp-11267-01/record_11267.json` | full platform record snapshot (title/figures/tags) |
| `scripts/kf_wp1126701_register_assets.py` | build / envelope / verify |
| `scripts/kf_wp1126701_figure_report.py` | figure / render / publish |
| `tests/test_kf_wp1126701_asset_manifest.py` | 14 offline acceptance tests |

## Published artefacts

* Platform report: **14804** — `KF-RESULT wp-11267-01`, tags `kf-wp:wp-11267-01`, mission 15695,
  scenario `p284w3-n04-fem-mpi-parallel`; its markdown is byte-identical to
  `docs/kf_result_wp-11267-01.md` and its `asset_registration_map.png` is served by
  `GET /tensor/reports/14804/figures/asset_registration_map.png` (PNG magic ok, bytes equal to the
  committed file).
* Report **14802** is an earlier publish of the same package from this worktree; its `json` block is
  identical, only the prose bullet rendering of the `declared_absent` quotes differed (escaped
  pipes). **14804 supersedes it**; the platform exposes no update/delete endpoint (PATCH/PUT → 405),
  so the duplicate stays visible.

## Reproducibility note

A fresh `python3 scripts/kf_wp1126701_register_assets.py all` re-derives every field; only the
volatile stamps (`manifest.generated_at`, `envelope.provenance.emitted_at`,
`verification.generated_at`) change. The committed `asset_manifest.json` / `kf_result.json` are
extracted from the published report 14804's `json` block, so the committed artefacts and the
platform copy are byte-consistent (asserted by `test_report_markdown_has_exactly_one_json_block_*`).

## Reproduce

```bash
export TENSOR_API_BASE=http://127.0.0.1:8010/api/v1      # login uses TENSOR_AGENT_USER/PASS
python3 scripts/kf_wp1126701_register_assets.py all      # fetch + manifest + envelope + verify
python3 scripts/kf_wp1126701_figure_report.py figure     # coverage figure
python3 scripts/kf_wp1126701_figure_report.py render     # KF-RESULT markdown (1 json block)
python3 -m pytest tests/test_kf_wp1126701_asset_manifest.py -q   # offline, no network
```

## Interpretation limits

* `declared_absent` means *the report says it is absent/unmeasured*; this package did not
  independently confirm e.g. the cluster-job queue state.
* `referenced_unresolved` means the declared path belongs to the delivery repo named in the
  report (TensorPhysics) and its payload is outside this worktree — no hash is invented.
* Asset discovery is text-driven over the markdown; an attachment not mentioned in the body
  is invisible to it (the `/artifacts` endpoint returns 404 for report 11267, so there is no
  independent artefact index to reconcile against).
* Figure names are normalised to the in-body link form `figures/<name>.png` because §4 repeats
  them bare; every literal token is still kept as its own locator quote.