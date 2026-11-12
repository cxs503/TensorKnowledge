# wp-5776-01 — asset registration for report 5776

Work package: `wp-5776-01` · task_type `01-asset-registration` · lane C · **report_id 5776 only**
Source: `tensor://reports/5776`, field `markdown`, `sha256:49089e9b193af49f9ffcf4f35b8a82b6f4deec5da07edc8e654fc7902385c04f`, 4950 chars.

Scope: register the report's assets (figures / referenced files / body-resident blocks) with
byte-exact locators. **No extraction, no claim generation, nothing marked `verified`** — claims are
an empty array by contract, verification is computed by the platform gate.

## Artifacts

| File | What |
|---|---|
| `asset_manifest.json` | 17 assets, 9 classes, char_span locators; `claims: []`; `verification_status: not_verified` |
| `kf_result.wp-5776-01.json` | `kf_result.v1` envelope; `outputs["asset_manifest.json"]` = the manifest verbatim |
| `verification.json` | 8 acceptance checks with `all_pass` |
| `KF-RESULT-wp-5776-01.md` | delivery report (six sections) with the envelope as its single ```` ```json ```` block |
| `asset_manifest.v1_5776.schema.json` | local pinned manifest schema (consts for report/package) |
| `kf_result.v1.schema.json` | pinned copy (this worktree has no `schemas/kf_result.v1.schema.json`) |
| `fig1_asset_inventory.png`, `fig2_consistency.png` | assets by class×resolution; sweep self-consistency deviations |
| `../../runs/wp-5776-01/` | source copy + raw API payload + `consistency_check.json` (offline replay) |

## Reproduce

```bash
cd <worktree>
python3 scripts/kf/fetch_report_5776.py                        # fetch + pin sha256 (env creds only)
python3 scripts/kf/build_asset_manifest_5776.py build result   # manifest + envelope
python3 scripts/kf/consistency_check_5776.py                   # arithmetic self-consistency (NOT platform verification)
python3 scripts/kf/figures_5776.py                             # fig1/fig2
python3 scripts/kf/build_asset_manifest_5776.py verify         # independent re-fetch + 8 checks
python3 -m pytest tests/test_kf_wp5776_01.py -q                # 15 offline assertions
python3 scripts/kf/render_result_report_5776.py [--publish]    # render (and publish) the report
```

## Traps hit while building this package

1. **`psql` read of `tensor_reports` is denied** for this role (`permission denied for table
   tensor_reports`), so the source must come from `GET /tensor/reports/5776` with a bearer token;
   credentials only via env (`TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS`) — an inline password on a
   `curl` command line is blocked by the harness security policy.
2. **Locator quotes legitimately contain fenced code blocks** (a ```` ```bash ```` fence sits inside the
   audit-trail quotes). Therefore the delivery markdown's envelope cannot be extracted with
   `text.split("```json")` — it cuts inside a quote. Match the fence with real newlines on both
   sides (`\n```json\n(.*?)\n```\n`) and assert exactly one match.
3. **No artifact endpoint**: `/tensor/reports/5776/artifacts` and `/tensor/artifacts?report_id=5776`
   both return 404 and `figures[]` carries only `name`/`caption` — figure bytes are not obtainable,
   so A01–A03 are `referenced_unresolved`, never `resolved`.
4. `artifacts/` is git-ignored by the push gate, `runs/` is not — the source copy therefore lives in
   `runs/wp-5776-01/` so the offline tests keep working after a fresh clone.

## Limitations (mirrored in `asset_manifest.json:limitations`)

Registration only; figure bytes unavailable; the five audit-trail paths live in the report's own
worktree (`/root/tp-agent/work/m5068`) and are not validated here; the arithmetic consistency audit
compares the report against its **own** closed form (a self-consistency check, not an experimental
or independent-solver validation, and the agreement is dominated by 4-decimal table rounding).