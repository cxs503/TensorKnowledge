# wp-12629-01 — report 12629 asset registration (task_type 01-asset-registration)

Contract: `package_id: wp-12629-01`, `report_id: 12629`, `source_field: markdown`,
`source_hash: sha256:6cbf559cfaec918c26cf69c0081a2a3dcdceee4f7870797b35a27af8ca7e10eb`, chars 1899.
Lane C, delivery repo TensorKnowledge, status `draft`. Register assets only — **no extraction**
(`classify_report_type=false`), therefore `claims` is an empty array and nothing is marked verified.

## Deliverables

| file | content |
|---|---|
| `asset_manifest.json` | 34 assets with char-level locators (29 resolved_in_source / 4 referenced_unresolved / 1 declared_absent), `checks`, `integrity`, `boundaries` |
| `kf_result.wp-12629-01.json` | result envelope = the single fenced json block of the report |
| `KF-RESULT-wp-12629-01.md` | report body (six sections + that one json block) |
| `verification.json` | independent re-fetch + locator re-resolution + schema pass (10/10) |
| `publish_receipt.json` | platform publish roundtrip (report id 14874): markdown byte-identical, json block equals envelope |
| `fig_locator_coverage.png` | assets drawn on the 1899-char markdown canvas + asset_class histogram |

## Reproduce (from the worktree root)

```bash
python3 scripts/kf_fetch_12629.py && python3 scripts/kf_register_12629.py \
  && python3 scripts/kf_verify_12629.py \
  && python3 scripts/kf_report_12629.py && python3 scripts/kf_verify_12629.py
```

Order matters: `kf_report_12629.py` embeds the checks from `verification.json`, so verify → report →
verify. The last verify is authoritative; it re-fetches report 12629 from the API in-process instead of
reusing `runs/wp-12629-01/report_12629.md`, so a stale local copy cannot make the gate pass.

Publishing (`python3 scripts/kf_publish_12629.py`) refuses to run unless `verification.json` has
`all_pass: true`.

## Determinism (checked on a clean clone)

The chain was re-run in a fresh `git clone` of this commit: `asset_manifest.json` came out
byte-identical to the committed one, and the only differing field in the result envelope is
`provenance.emitted_at` (a wall-clock stamp). Locators therefore do not depend on machine state, PYTHONHASHSEED
or directory layout.

## Known unresolved items (recorded, not repaired)

`A10` code pointer `backend.api.coupled_maneuvering` (no `.py` in this worktree) · `A22` dangling
"报告表" (damping-ratio r distribution) · `A24` dangling "§6.4" · `A29` 7 figure binaries not
retrievable from the API · `A31` experimental RAO dataset declared absent by the report itself.
Also noted: 3 figure filename↔caption index permutations in `record.figures`.
