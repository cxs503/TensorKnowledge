# wp-5760-01 — asset registration for report 5760

One work package, one report (`report_id=5760`, `tensor://reports/5760`, `source_field=markdown`).
Registration only: **no extraction, no claims, no "verified" marks**.

| item | value |
|---|---|
| package_id | `wp-5760-01` |
| task_type | `01-asset-registration` |
| source hash (utf-8 bytes of markdown) | `sha256:95a6ffec44f492fe4f7f39f8d6bb989d845f6a781cd5749197177b6c05308bfe` (== contract) |
| source size | 6808 chars / 10847 bytes |
| assets registered | 52 (20 `resolved_in_source`, 31 `referenced_unresolved`, 1 `declared_absent`) |
| claims | `[]` (empty array allowed by the contract notes) |
| delivered KF-RESULT report | platform report `14662`, title `KF-RESULT wp-5760-01` |

Files:

| path | what |
|---|---|
| `asset_manifest.json` | primary output: source identity, 52 assets with char-span locators, counts, integrity |
| `asset_manifest.schema.json` | package-scoped draft-07 schema used as the `schema_pass` target |
| `kf_result.json` | delivery envelope (package_id / task_type / report_id / provenance / outputs) |
| `verification.json` | this package's own 10 machine checks (not a platform verification mark) |
| `published_report.json` | publish receipt + figure round-trip check |
| `figures/asset_inventory.png` | inventory figure, generated from the manifest |
| `../../reports/kf_wp_5760_01_result.md` | the published report (template: `kf_wp_5760_01_result.template.md`) |

Reproduce (worktree root):

```bash
python3 scripts/kf/build_asset_manifest_5760.py all      # fetch + hash + inventory + verify + envelope
python3 -m pytest tests/test_kf_wp5760.py -q             # 17 offline acceptance tests
python3 scripts/kf/fig_wp5760_inventory.py               # inventory figure
python3 scripts/kf/report_wp5760.py [--post]             # compose (and publish) the KF-RESULT report
```

Boundary notes: referenced paths stay `unresolved` because they belong to the producing repository
(TensorPlatform), which is outside this work package; the report's `figures` array carries only
name+caption (no `png_base64`), so the cited figure is registered `declared_absent` rather than
re-drawn; the bash reproduction block is registered as text and deliberately not executed.