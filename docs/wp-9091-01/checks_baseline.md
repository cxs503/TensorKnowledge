# Repo-wide test baseline (context for wp-9091-01 self-checks)

The work package's own acceptance evidence is `verification.json` + `tests/test_kf_wp9091_01_asset_manifest.py`
(8 invariants, all passing). This note records the *surrounding* suite state, so that "8 passed" cannot be
mistaken for "the whole repo is green".

## Commands and raw results (worktree `/root/tp-agent/work/m15630`, branch `agent/m15630`)

```
$ python3 -m pytest tests -q
12 failed, 356 passed, 3 skipped, 1 xfailed, 6 warnings, 22 errors in 93.36s

$ python3 -m pytest tests -q 2>&1 | grep -E "^(FAILED|ERROR)" | ... | uniq -c
     11 ERROR   tests/test_kf_wp448.py
     11 ERROR   tests/test_wp766_01_asset_registration.py
      4 FAILED  tests/test_ke_migrate.py
      1 FAILED  tests/test_kf_wp448.py
      5 FAILED  tests/test_rci_f1_abc.py
      2 FAILED  tests/test_sediment_ke_relay.py
```

## Baseline: are these mine?

No. The same five files were re-run on an untouched `HEAD` extract
(`git archive HEAD | tar -x -C /tmp/base_wp9091`):

```
$ python3 -m pytest tests/test_kf_wp448.py tests/test_wp766_01_asset_registration.py \
      tests/test_ke_migrate.py tests/test_rci_f1_abc.py tests/test_sediment_ke_relay.py -q
12 failed, 13 passed, 4 warnings, 22 errors in 5.09s
```

Identical counts (12 failed / 22 errors) → pre-existing. This package only **adds** files
(`docs/wp-9091-01/`, `scripts/kf_*wp9091*`, `scripts/kf_fetch_report.py`,
`schemas/asset_manifest.v1.generic.schema.json`, `tests/test_kf_wp9091_01_asset_manifest.py`,
`runs/wp-9091-01/`) and does not edit existing code, tests, or the v1 schema — which is why the
wp-448-01 schema regression is asserted explicitly (`schema_pass.regression_v1`, and test I7).

`tests/test_kf_wp9091_01_asset_manifest.py`: **8 passed** in this worktree and in a docs-only clean
checkout (`/tmp/cleanck_wp9091`, `scripts/kf_verify_wp9091_01.py` → `all_pass: True` there as well) —
i.e. the package self-verifies without `runs/` or `artifacts/`, both of which the push filter strips.

## Why this file exists instead of an update to the platform report

The platform report for this package is `14704` (`KF-RESULT wp-9091-01`), published before the repo-wide
run. `PUT`/`PATCH /tensor/reports/14704` both answer `405 Method Not Allowed`, so correcting it in place
is impossible, and re-publishing would create a second `KF-RESULT` report for the same package_id
(ambiguity for the gate). The baseline therefore lives here, next to the artifacts, and is referenced
from `README.md`. It does not change any registration result.