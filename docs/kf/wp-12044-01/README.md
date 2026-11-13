# wp-12044-01 — asset registration for report 12044

Work package: `01-asset-registration` · lane C · contract v1.0 (`contract.yaml`, verbatim copy).
Source report: `tensor://reports/12044` — "probe figure upload (write_lease D1)" (a figure-upload
probe record, `tags=["probe"]`, 57 characters of markdown; not a research result).

## Result at a glance

| item | value |
|---|---|
| markdown sha256 (recomputed locally) | `74cbbb52b6682ff4bb865490e1b4cce8511d023ed1a48afa19a9f2d22a0220b6` |
| contract `source_hash` | identical (match) |
| chars / UTF-8 bytes | 57 / 81 |
| assets registered | 4 — 3 `resolved_in_source`, 1 `referenced_unresolved`, 0 `declared_absent` |
| claims | `[]` (contract `classify_report_type=false`, `no_forced_claim_generation`) |
| verification | **not** marked by this package; the platform gate computes it |
| published report | `KF-RESULT wp-12044-01` → platform report id **14850** (`publish_receipt.json`) |

## Registered assets (character-precise, verbatim)

| id | class | quote | chars | resolution |
|---|---|---|---|---|
| A01 | source_document | whole markdown | 0–57 | resolved_in_source |
| A02 | timestamp_token | `2026-11-10T17:22:47.930890Z` | 6–33 | resolved_in_source |
| A03 | intent_statement | `探针：验证 figures 字段可落库。` | 36–56 | resolved_in_source |
| A04 | figure_declaration | `figures 字段可落库` (record.figures[0] = `fig1_d1_linearizability.png`, caption `probe`) | 42–55 | **referenced_unresolved** |

A04 is unresolved on purpose: `record.figures` carries `name` + `caption` only — no path, URL or
digest — and `GET /tensor/reports/12044/figures` answers 404 (`platform_probe.json`). The figure
binary is therefore *not* resolvable from the platform, which is recorded honestly instead of an
invented address.

## Files

| path | content |
|---|---|
| `contract.yaml` | work-package contract, verbatim |
| `source.md` | byte copy of the registered `markdown` field |
| `report_12044.json` | raw platform record (title / tags / mission_id / figures) |
| `sha256.txt` | local digest vs contract digest |
| `platform_probe.json` | raw responses of the figure/asset/attachment endpoint probes (3 × 404) |
| `locator_check.json` | per-quote offset, line, occurrence count, span↔quote equality |
| `asset_manifest.json` | **contract output** (4 assets + counts + integrity), digest pinned in the envelope |
| `kf_result.json` | `kf_result.v1` envelope, validated against `schemas/kf_result.v1.schema.json` |
| `report_body.md` | six-section report body carrying exactly one ```json block |
| `fig1_asset_spans.png`, `figures.json` | asset-span figure and its digest/caption metadata |
| `publish_receipt.json` | created report id, tags, post-publication re-fetch checks |

Manifest integrity is carried by digests rather than a second copy: `kf_result.json` records
`artifact_sha256` / `artifact_bytes` of `asset_manifest.json`, and the same digests travel inside the
single ```json block of the published report, so the shipped bytes can be checked offline.
(`artifacts/` is git-ignored in this repo, so no mirror is claimed there.)
Top-level copy of the body: `docs/kf_result_wp-12044-01.md`.

## Reproduce (one shot)

```bash
cd <worktree> && python3 scripts/kf_wp12044_01_fetch.py \
  && python3 scripts/kf_wp12044_01_probe.py \
  && python3 scripts/kf_wp12044_01_register.py \
  && python3 scripts/kf_wp12044_01_verify.py --online
```

`scripts/kf_wp12044_01_compare.py` diffs the stored markdown of the published report against the
local body. `scripts/kf_wp12044_01_publish.py --dry-run` prints the publish payload without posting;
without `--dry-run` it creates the `KF-RESULT` report and then re-fetches it to assert title, tag,
single-json-block equality with `kf_result.json`, and that report **12044 is unchanged**.

Verifier status at commit time: **31/31 checks passed** (`python3 scripts/kf_wp12044_01_verify.py --online`),
covering contract hash, platform re-fetch hash, per-asset locator verbatim+uniqueness, id uniqueness,
artifact mirror identity, `kf_result.v1` schema validation, single-json-block equality, figure digest,
publish tag/receipt, and the honesty flag (`verification_status=not_verified`).

## Superseded draft (disclosure)

A first publication, report **14847**, was created before a cosmetic fix to one row of the artifact
table (it also carried a stale `artifacts/` mirror line). `PUT /tensor/reports/{id}` answers **405**
(`scripts/kf_wp12044_01_compare.py`), so the corrected body was published as a new report, **14850**,
which is byte-identical to `report_body.md`. 14847 remains on the platform as a superseded draft of the
same package; the `kf-wp:wp-12044-01` tag is identical on both, so downstream consumers should take the
latest id recorded in `publish_receipt.json`.

## Limitations (honest)

- The source report is a probe record: no geometry, no case, no numeric result — so this manifest
  legitimately contains no parameter/table/result assets.
- `scenario_key` is `null` in the platform record; per contract no scenario is guessed.
- Hash equality is a mechanical identity check only ("the bytes registered are the bytes served");
  it says nothing about whether the probe's claim is true, which this package does not judge.
- No claim extraction, no report-type classification, no `verified` marking (platform gate owns that).