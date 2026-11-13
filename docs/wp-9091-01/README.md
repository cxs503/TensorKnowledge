# wp-9091-01 — asset registration for report 9091

Work package: `wp-9091-01` · task_type `01-asset-registration` · lane C · report_id `9091`
Source: `tensor://reports/9091` field `markdown`
sha256 `89c2a8f978e2915cb079337441118458e78017bcb4a177c38d8c8a00cc8c6f17` · 10060 chars / 10955 bytes UTF-8

Scope: register the report's assets only — confirm identity + hash, list the parsable
attachments/artifacts with verbatim unique locators, classify each as
`resolved_in_source` / `referenced_unresolved` / `declared_absent`. No knowledge extraction
(`claims` is deliberately empty), no re-computation of the report's numbers, nothing marked
`verified` (the platform gate owns verification).

## Files

| path | what |
|---|---|
| `asset_manifest.json` | the registered manifest (29 assets, empty claims, integrity block) — byte-identical to `artifacts/wp-9091-01/asset_manifest.json` |
| `report_9091.md` | archived copy of the source markdown (survives the push filter, so the hash + locators stay checkable offline) |
| `kf_result.wp-9091-01.json` | `kf_result.v1` result envelope (identical JSON is embedded in `KF-RESULT-wp9091-01.md` as the single fenced json block) |
| `verification.json` | self-check record: 8 independent checks + acceptance mapping, `verification_status = not_verified` |
| `fig_asset_inventory.png` | figure 1: asset classes / resolution split / locator coverage on the report line axis |
| `KF-RESULT-wp9091-01.md` | the deliverable report (six sections, evidence table, self-check); published on the platform as report `14704` |
| `checks_baseline.md` | repo-wide pytest baseline (12 failed / 22 errors at HEAD, reproduced on an untouched `git archive` extract → pre-existing, not caused by this package) |

## Reproduce

```bash
python3 scripts/kf_fetch_report.py 9091 89c2a8f978e2915cb079337441118458e78017bcb4a177c38d8c8a00cc8c6f17
python3 scripts/kf_register_wp9091_01.py
python3 scripts/kf_verify_wp9091_01.py
python3 -m pytest tests/test_kf_wp9091_01_asset_manifest.py -q
python3 scripts/kf_figures_wp9091_01.py
python3 scripts/kf_report_wp9091_01.py            # add --publish to POST the platform report
```

Offline (no platform access): the first line may be replaced by
`mkdir -p runs/wp-9091-01 && cp docs/wp-9091-01/report_9091.md runs/wp-9091-01/` plus the payload
json; `python3 scripts/kf_verify_wp9091_01.py` alone already re-checks the archived copies.

## Result at a glance

* assets 29 — resolved_in_source 24 / referenced_unresolved 4 / declared_absent 1
* unresolved by construction: `src/tensorfem/fsi/*.py` + `scripts/fsi_ladder_*.py` (TensorFEM repo, not this
  worktree), `artifacts/fsi_dfg2d2.{json,png}` / `artifacts/fsi_theodorsen.json` / `artifacts/*.png`
  (stripped by the push filter), platform `figures` (3 name+caption, no binary)
* declared_absent: the external flutter reference table — the report states it was unobtainable offline and
  the whole markdown contains no URL/DOI
* every locator satisfies `md[start_char:end_char] == quote` and `md.count(quote) == 1`