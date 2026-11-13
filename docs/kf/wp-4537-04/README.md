# wp-4537-04 — independent review of wp-4537-01 (report 4537)

Reviewer seat: `reviewer-m15829-redteam` (red-team-reviewer, agent). Context = report 4537
markdown (sha256 pinned) + the upstream package `docs/kf/wp-4537-01/kf_result.json`; the
producer's own narrative is not used as evidence.

Disposition: **needs-fix** (2 blocking findings).

| file | what it is |
|---|---|
| `kf_result.json` | result envelope (schema `schemas/kf_result.v1.schema.json`): `outputs["review_report.json"]`, `outputs["review_events.json"]` |
| `review_report.json` | 14 audit checks (F1..F13), 5 reproduction probes (R1a/R1b/R2../R4), 3 findings, checks_not_run, overstated_claims, independence record |
| `review_events.json` | `ke-review-v0.1` ledger event (`request-changes`, with findings) |
| `KF-RESULT-wp-4537-04.md` | published report (six sections + the single ```json block) |
| `fig1_review_4537_04.png` | audit matrix / probe verdicts / refutation counts (all read from the JSON) |

Findings:
* `FN-4537-04-01` (medium, blocking) — `tests/test_validation_gate.py` and
  `tests/test_v1_readiness.py` are named in the report (§3) but appear in neither
  `assets[]` nor `unresolved[]`; root cause = the whole `pytest -q …` span is tokenized as
  one `command_line` inline token, so the paths inside it never reach the asset classifier.
* `FN-4537-04-02` (low) — `unresolved[]` is set-identical to `assets[status != resolved]`.
* `FN-4537-04-03` (medium, blocking) — the report's load-bearing mechanism claim
  ("`ruff format` 也不会拆语句" / "E701/E702 无法通过 `ruff format` 消解") is **refuted** by
  the same ruff 0.15.0 the report pins: `ruff format` splits `x = 1; y = 2` and
  `if True: pass` into separate lines and the E701/E702 violations drop 2 → 0.

Reproduce:

```bash
python3 scripts/kf/fetch_4537.py            # fetch + verify sha256 (TENSOR_* env needed)
python3 scripts/kf/review_4537_04.py        # audit + probes -> review_report.json / review_events.json
python3 scripts/kf/make_figure_4537_04.py   # fig1
python3 scripts/kf/publish_4537_04.py       # emit KF-RESULT md (+ --dry-run)
python3 -m pytest tests/test_kf_wp4537_04.py -q
```

Not run (declared, not assumed): GitHub check-run conclusion, in-place recomputation of
4268/616 on the TensorFEM tree, byte review of `artifacts/lint-gate-m4175/*`, claim-level
semantic fidelity (upstream `claims=[]`).
14952
