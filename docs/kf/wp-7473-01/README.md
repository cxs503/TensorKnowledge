# wp-7473-01 — report 7473 asset registration (lane C)

Work package: `01-asset-registration`, `report_id=7473` only. No extraction, no claim generation,
no `verified` marks (verification is computed by the platform gate).

## Deliverables

| file | what it is |
|---|---|
| `asset_manifest.json` | the registered assets (38 entries, claims = 0) |
| `kf_result.json` | the delivery envelope; byte-identical to the single ```json block in the published report |
| `source_markdown.md` | byte-identical snapshot of `tensor://reports/7473` markdown (sha256 `c3b3d095…d0f6b`, 5942 chars / 8934 bytes) |
| `verification.json` | 7 acceptance checks re-run independently of the build step |
| `asset_manifest_7473.schema.json` | local JSON Schema pinning the manifest shape (platform schema wins on disagreement) |
| `report_gate_check.json` | platform `POST /platform-governance/report-gate/check` receipt for the published report |
| `fig_asset_resolution.png` | report figure 1, plotted straight from `asset_manifest.json` |

## Locator schemes (important for auditors)

* `markdown_line` — `line` (1-based), whole-line `quote`, `start_char`/`end_char` into the markdown, and
  `unique` = whether that quote occurs exactly once in the document. `quote` is sliced from the source
  bytes, never retyped, and `verify` re-checks `markdown[start:end] == quote` and `lines[line-1] == quote`.
* `markdown_document` — the whole markdown; used for the single `source_document` asset.
* `report_field` — a field of the report *record* rather than the markdown. Used only for the two
  `platform_figure_record` assets; their `quote` is rendered from `figures[i].name` + `figures[i].caption`
  (caption text is verbatim from the record) and is deliberately **not** claimed to be a markdown substring.

## Resolution vocabulary

* `resolved_in_source` — located and hashed: source markdown, an in-source table header, or a file inside
  this delivery worktree.
* `referenced_unresolved` — named by the report, target bytes not reachable from this work package.
  Everything under `src/ tests/ benchmarks/ artifacts/` belongs to **TensorLBM**, not to this
  TensorKnowledge worktree; TensorKnowledge's own same-named directories are never used to "resolve" them.
* `declared_absent` — the report itself states the asset does not exist (quoted verbatim).

`referenced_unresolved` is a scope statement, not a finding of absence: an auditor who needs file-level
evidence for the TensorLBM paths must check them out in the TensorLBM repository.

## Reproduce

```bash
cd <worktree>
python3 scripts/kf/build_asset_manifest_7473.py build verify result   # needs TENSOR_API_BASE/_USER/_PASS
python3 scripts/kf/plot_7473_manifest.py
python3 -m pytest -q tests/test_kf_wp_7473_01.py                       # offline; live case skips without creds
```

Read-only re-check of the committed artifacts (no platform needed):

```bash
python3 -m pytest -q tests/test_kf_wp_7473_01.py
```