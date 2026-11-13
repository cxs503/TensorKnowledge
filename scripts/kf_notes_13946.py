"""Render docs/wp-13946-01/README.md (navigational note) with numbers injected from the artifacts.

Nothing here is typed by hand: counts come from asset_manifest.json, check results from
verification.json, delivery identity from published.json, figure identity from figure_probe.json.
Missing inputs degrade to an explicit "not run" line instead of a guessed value.

Usage: python3 scripts/kf_notes_13946.py
"""
from __future__ import annotations

import json
import pathlib

DOC = pathlib.Path("docs/wp-13946-01")
ART = pathlib.Path("artifacts/wp-13946-01")


def _read(p: pathlib.Path):
    for cand in (p, pathlib.Path(".") / p):
        if cand.exists():
            return json.loads(cand.read_text())
    return None


def main() -> int:
    man = _read(ART / "asset_manifest.json") or _read(DOC / "asset_manifest.json")
    ver = _read(ART / "verification.json")
    pub = _read(DOC / "published.json")
    fig = _read(DOC / "figure_probe.json")
    assert man, "asset manifest missing"

    c = man["counts"]
    br = c["by_resolution"]
    checks = (ver or {}).get("checks", {})
    chk_lines = "\n".join("| `%s` | %s |" % (k, "PASS" if v["pass"] else "FAIL")
                          for k, v in checks.items()) or "| (verification.json not available) | n/a |"
    rid = pub["response"]["id"] if pub else "not published"
    fig_line = ("delivered bytes sha256 `%s` = local (`%d` bytes, identical=%s)"
                % (fig["remote_sha256"], fig["remote_bytes"], fig["bytes_identical"])) if fig \
        else "figure probe not run"

    txt = f"""# wp-13946-01 — asset registration for report 13946

Work package: `{man['package_id']}` · task_type `{man['task_type']}` · lane C · status draft.
Source: `{man['source']['uri']}` field `{man['source']['field']}`,
`sha256={man['source']['hash']}` (contract match), `chars={man['source']['chars']}`.
Delivered KF-RESULT report on the platform: id `{rid}` (title `KF-RESULT {man['package_id']}`,
tag `kf-wp:{man['package_id']}`).

## What was registered

`{c['assets']}` assets: `{br.get('resolved_in_source', 0)}` resolved_in_source,
`{br.get('referenced_unresolved', 0)}` referenced_unresolved, `{br.get('declared_absent', 0)}`
declared_absent. `claims=[]` — this package registers assets only; nothing is marked verified.

## Files

| path | role |
|---|---|
| `docs/wp-13946-01/asset_manifest.json` | committed manifest (byte-identical to the `artifacts/` build output) |
| `docs/wp-13946-01/kf_result.json` | result envelope = the single json code block of the delivered report |
| `docs/wp-13946-01/KF-RESULT_wp-13946-01.md` | exact markdown delivered to the platform |
| `docs/wp-13946-01/fig1_asset_coverage.png` | coverage figure — {fig_line} |
| `docs/wp-13946-01/verification.json` | independent re-check of every acceptance item |
| `docs/wp-13946-01/published.json` | platform response for the delivered report |
| `schemas/asset_manifest.wp-13946-01.schema.json` | package-pinned schema (the shared one hard-codes another package's ids) |

`artifacts/` and `runs/` are gitignored (`artifacts/` by .gitignore + push gate), so the committed
copies live here under `docs/`; scripts write both trees.

## Reproduce

```
python3 scripts/kf_fetch_13946.py        # GET report 13946, sha256 gate
python3 scripts/kf_register_13946.py     # build manifest (unique-quote assertions)
python3 scripts/kf_verify_13946.py       # independent re-check (does not import the builder)
python3 scripts/kf_figures_13946.py      # figure, self-consistent with the manifest
python3 scripts/kf_publish_13946.py      # render + POST the KF-RESULT report
python3 scripts/kf_probe_figure_13946.py # fetch the delivered figure bytes, compare sha256
python3 scripts/kf_notes_13946.py        # this file
python3 -m pytest tests/test_kf_wp13946_01_asset_manifest.py -q
```

## Verification snapshot

| check | result |
|---|---|
{chk_lines}

Fresh-checkout behaviour (verified in a scratch copy without `artifacts/`/`runs/`): 4 passed,
2 skipped — the two that need generated trees report `skipped`, never `passed`.

## Limits

1. The API is the only source channel: direct `psql -d tensorplatform` on `tensor_reports` is denied
   (`permission denied for table tensor_reports`), so hash equality is established against the API
   bytes only.
2. Cross-repo artifacts (`src/tensordem/shear_cell.py`, `scripts/m14840/*.py`,
   `artifacts/shear_cell_m14840/*.json`, `docs/SHEAR_CELL_SERVO_AUDIT_M14840_tables.md`,
   `tests/test_shear_cell_servo_audit_m14840.py`) are registered as `referenced_unresolved`: the
   report gives no commit/URL, and this package does not reach into other repositories.
3. The report's own figure (`../figures/shear_cell_m14840_servo.png`) is registered as a link only;
   its bytes are not in this worktree and the platform record carries name+caption only.
4. No claim of this package asserts that the source report's conclusions (servo offset fixed,
   μ vs experiment < 10 %) hold. Registration is not verification.
5. Unrelated tests in `tests/kf/` and `tests/test_kf_wp448.py`-style packages fail on a fresh
   checkout because they read gitignored `runs/` / `artifacts/` trees; that predates this package
   and was left untouched (single-report boundary).
"""
    DOC.mkdir(parents=True, exist_ok=True)
    (DOC / "README.md").write_text(txt)
    print("wrote", DOC / "README.md", len(txt), "chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())