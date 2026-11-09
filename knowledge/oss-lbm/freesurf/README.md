# OSS-LBM Free-Surface Knowledge Subpackage (freesurf/)

Source-code-driven knowledge extracted from **Maarten-vd-Sande/lbm** (tier1: free-surface LBM
Python implementation, Thuerey/Körner VoF-ε family) for TensorLBM free-surface improvement.

## Source

| Item | Value |
|------|-------|
| Repo | https://github.com/Maarten-vd-Sande/lbm |
| Commit | `573a01c` (573a01c4d2e6321f3634ff271adca4ce91872e6f, 2020-08-08) |
| Cache | `/root/oss-cache/Maarten-vd-Sande_lbm` (shallow clone, depth 1) |
| Files read | `README.md`, `lbm/init.py`, `lbm/streamcollide.py`, `lbm/time_evolve.py`, `lbm/update_types.py`, `lbm/util.py`, `examples/dambreak.py`, `examples/cylinder_flow.py` |

## Scope

16 claims (≥8 required) covering:

1. **Method architecture** — D2Q9 BGK + per-cell mass ledger + bit-flag cell classification (Thuerey VoF-ε family).
2. **Core operators** — ε fill fraction, interface mass exchange (ε-weighted), surface-normal correction, cell transition criteria (fill_offset=0.003 / lonely_tresh=0.1), excess-mass redistribution (η-weighted).
3. **Mass-accounting pathologies (反例证据, status=contested)** —
   - `rho_prev = np.copy(mass)` copy bug (`lbm/time_evolve.py:18`) → ε degenerates to 1.0 (runtime-verified);
   - `cell_type & CT.GAS == 2` operator-precedence dead branch (`lbm/streamcollide.py:166`) → gas cells return 0.5 instead of 0 (exhaustively runtime-verified for 0..2047);
   - silent mass destruction when a transitioning cell has no interface neighbors (`lbm/update_types.py:94-101`).
   These are consistent with the prior inventory finding of non-conserved mass accounting (±1.5~3% over 200 steps).
4. **Solver details** — velocity limiter (|u|≤√(2/3), moment-only), first-order gravity forcing, Zou-He inlet, no-slip bounce-back, asymmetric transition reinitialization.

## Structure

```
freesurf/
├── README.md
├── claims/claims.json          # 16 claim records (schema: claim-record.schema.json)
├── evidence/evidence.json      # 16 evidence records (schema: evidence-record.schema.json)
├── provenance/provenance.json  # 1 provenance record (schema: provenance-record.schema.json)
├── validate_freesurf.py        # Self-validator (incl. verbatim quote gate)
└── tests/test_freesurf_package.py  # pytest wrapper (runs both validators + schema + verbatim)
```

## GAP Anchors

- `GAP-LBM-FREESURFACE` — free-surface method gap (method family, core operators, BCs).
- `GAP-LBM-FREESURFACE-MASS-LEDGER` — self-defined sub-anchor: mass-accounting pathologies under the
  free-surface method (attribution: free-surface method gap; pathology/counter-example evidence is
  admitted into claims with `epistemic_status: contested` and evidence noted).

## Epistemic Discipline

- Code-level descriptive facts verified by direct source inspection: `epistemic_status: established`.
- Pathology/impact claims (no verification surface in the repo — it has no tests): `epistemic_status: contested`,
  with the runtime-verification evidence noted in `notes`.
- All evidence `assessment_status: unassessed` (no self-approval); all records `draft` (no review events).
- Every claim's `notes` carries a GAP anchor + a TensorLBM service statement.

## Validation

```bash
python3 validate_freesurf.py          # subpackage validator (incl. verbatim quote gate)
python3 ../validate_oss_lbm.py        # parent package validator (must stay green)
pytest tests/ -v                     # pytest wrapper: both validators + jsonschema + verbatim
```

The verbatim gate re-reads the source cache and asserts each quote equals the located file lines
exactly (skipped with a NOTE if the cache is absent, e.g. on CI).
