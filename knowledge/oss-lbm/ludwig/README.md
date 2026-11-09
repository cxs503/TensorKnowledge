# Ludwig — OSS-LBM knowledge sub-package

Source-code knowledge extracted from **`ludwig-cf/ludwig`** (Ludwig: a lattice Boltzmann
code for complex fluids; Edinburgh Soft Matter and Statistical Physics Group / EPCC),
covering the **binary-fluid free-energy / multicomponent (MCMP) sector** relevant to the
TensorLBM gap line `GAP-LBM-MCMP-POISEUILLE` and its MCMP neighbours.

This package follows the same four-contract discipline as `knowledge/oss-lbm` (m8634/m8635):
real source reading, `repo@commit file:line` + verbatim quote evidence, conservative
`epistemic_status`, all drafts unassessed (no self-approval), in-repo validator + pytest.

## Metadata correction (honest finding)

The mission brief labels the repository as *Fortran*. It is not: the README states the code
`is written in standard ANSI C` and the tree contains no `*.f90`/`*.F90` sources
(claim `tkc:oss-lbm:ludwig-ansi-c-not-fortran`). Nothing in this package assumes Fortran.

The brief also names a *gauge* formulation. The token `gauge` does **not** occur anywhere in
`src/`, `docs/`, `tests/` or `README.md` (exhaustive case-insensitive search, 0 hits);
Ludwig's free-energy forcing is expressed as stress divergence and `phi*grad(mu)` forms
(claim `tkc:oss-lbm:ludwig-no-gauge-formulation`, gap `GAP-LBM-MCMP-FORCE-GAUGE`). This
premise is therefore recorded as **falsified for this repository**, not "transcribed".

## Layout

```
knowledge/oss-lbm/ludwig/
├── README.md                        # this file
├── claims/claims.json               # 17 claims  (tkc:oss-lbm:ludwig-*)
├── evidence/evidence.json           # 21 evidence records (19 code-location + 2 code-search)
├── provenance/provenance.json       # source snapshot + build/test record
├── gaps/gap-anchors.json            # 6 GAP anchors (1 mission-anchored + 5 adjacency, owned)
├── validate_ludwig.py               # package validator (stdlib only)
├── scripts/build_package.py         # regenerates claims/evidence by *slicing* source lines
├── scripts/verify_shear_wave.py     # quantitative LB verification (exact shear-wave decay)
├── artifacts/runs/shear_wave_L{8,16,32}.{input,log}   # raw Ludwig runs
├── artifacts/shear_wave_verification.json             # programmatic results (no hand copy)
├── artifacts/shear_wave_decay.png                     # figure (decay + error vs acceptance band)
└── tests/test_ludwig_package.py     # pytest wrapper around the validator + evidence checks
```

## Claims (17)

| id | status | gap anchor | one-line content |
|---|---|---|---|
| ludwig-free-energy-catalog | established | GAP-LBM-MCMP-POISEUILLE | 9 free-energy models + null behind one `fe_id_enum`, run-time selectable |
| ludwig-fe-vtable-contract | established | GAP-LBM-MCMP-FORCE-GAUGE | typed callback vtable (fed / mu / mu_solv / stress / molecular field) |
| ludwig-ch-fd-evolution | established | GAP-LBM-MCMP-POISEUILLE | Cahn–Hilliard `d_t phi + div(u phi − M grad mu)=0` by finite difference |
| ludwig-ch-flux-first-order-mu | contested | GAP-LBM-MCMP-MU-STENCIL | face flux `M*(mu(i+1) − mu(i))` ⇒ O(h) interface current |
| ludwig-symm-phi4-density | established | GAP-LBM-MCMP-POISEUILLE | `F = ½Aφ² + ¼Bφ⁴ + ½κ(∇φ)²` (Kendon et al. 2001) |
| ludwig-symm-analytic-sigma | established | GAP-LBM-MCMP-SIGMA-CALIB | analytic `σ = sqrt(−8κa³/9b²)`, `ξ = sqrt(−2κ/a)` |
| ludwig-symm-mu-discrete | contested | GAP-LBM-MCMP-MU-STENCIL | `mu = aφ + bφ³ − κ∇²φ` with stencil-dependent discrete Laplacian |
| ludwig-force-methods | established | GAP-LBM-MCMP-FORCE-GAUGE | 5 force formulations, stress divergence documented as default |
| ludwig-no-gauge-formulation | established (negative) | GAP-LBM-MCMP-FORCE-GAUGE | no `gauge` token in the repository |
| ludwig-no-scmp-pseudopotential | established (negative) | GAP-LBM-MCMP-SCMP | no Shan–Chen pseudo-potential / SCMP implementation |
| ludwig-poiseuille-init | established | GAP-LBM-MCMP-POISEUILLE | `1d_poiseuille` analytic parabola as *initial condition only* |
| ludwig-shear-wave-init | established | GAP-LBM-MCMP-POISEUILLE | `2d_shear_wave`, u₀=0.04, κ=2π — exact decay reference |
| ludwig-gradient-stencil-selection | established | GAP-LBM-MCMP-MU-STENCIL | run-time gradient/Laplacian stencil selection (7pt / 27pt / Tomita) |
| ludwig-spinodal-smoke-test | contested | GAP-LBM-MCMP-SPINODAL | only D3Q27 two-phase regression is a 10-step "smoke test" |
| ludwig-unit-test-ch-scope | contested | GAP-LBM-MCMP-SPINODAL | `test_ch.c` checks construction/mobility only |
| ludwig-sigma-droplet-calibration | established | GAP-LBM-MCMP-SIGMA-CALIB | droplet-based σ measurement (128 radial bins) |
| ludwig-ansi-c-not-fortran | established | GAP-LBM-MCMP-POISEUILLE | metadata correction: ANSI C, not Fortran |

`established` is used only where a verification surface exists in the repository itself
(analytic expressions, unit/regression tests, or the build+run verification recorded in
`artifacts/`). Where the *accuracy* consequence is interpretive (stencil order, absence of
physical assertions in tests) the status is deliberately `contested`.

## Gap anchors

| anchor | ownership |
|---|---|
| `GAP-LBM-MCMP-POISEUILLE` | given by the mission brief (m8669); reused, not re-defined |
| `GAP-LBM-MCMP-SCMP` | self-declared by this package, adjacency to POISEUILLE, pending adoption by the platform gap ledger |
| `GAP-LBM-MCMP-FORCE-GAUGE` | self-declared, adjacency |
| `GAP-LBM-MCMP-MU-STENCIL` | self-declared, adjacency |
| `GAP-LBM-MCMP-SIGMA-CALIB` | self-declared, adjacency |
| `GAP-LBM-MCMP-SPINODAL` | self-declared, adjacency |

Self-declared anchors carry `declared_by` explicitly (ownership statement) and a `next_step`;
they are proposals for the TensorLBM gap ledger, not silently minted IDs.

## Verification actually performed (not a transcription)

Build from the inspected snapshot (`gcc 12.3.0`, `-O2 -g -Wall`, `-D_D3Q27_`, serial):

* `make serial && make` → clean build, `src/Ludwig.exe` produced.
* `tests/unit: make test` → **98 PASS / 0 FAIL**.
* Top-level `make test` (regression diff against stored reference logs) → **FAIL** on
  `d3q19-short/serial-actv-s01` with relative drift ~1e-7 (stale reference logs in the
  snapshot); reported as-is, not hidden. See `provenance/source-snapshot.build`.
* Quantitative physics check (`scripts/verify_shear_wave.py`): the repository's own
  `2d_shear_wave` initial state decays as `u0 sin(ky) exp(−νk²t)`; measuring the decay rate
  of `max|u_x|` and comparing with `ν k²` for the input `viscosity 0.00625`:

  | L | k | measured rate | exact νk² | rel. error |
  |---|---|---|---|---|
  | 8 | 0.7854 | 4.0354e-03 | 3.8553e-03 | **+4.67%** |
  | 16 | 0.3927 | 9.7442e-04 | 9.6383e-04 | **+1.10%** |
  | 32 | 0.1963 | 2.4116e-04 | 2.4096e-04 | **+0.083%** |

  The error is a resolution (finite-k dispersion) effect of the discrete BGK operator and
  converges away as k → 0; it is *not* an implementation defect. The 3% acceptance band is
  met at L ≥ 16.

## Run the checks

```bash
python3 validate_ludwig.py                       # package integrity
python3 scripts/verify_shear_wave.py \
    --log artifacts/runs/shear_wave_L8.log  --L 8  --nu 0.00625 \
    --combine-with artifacts/runs/shear_wave_L16.log:16:0.00625 \
                   artifacts/runs/shear_wave_L32.log:32:0.00625
pytest tests/ -q                                 # validator + discipline checks
# optional, only with a local source checkout:
LUDWIG_SRC=/path/to/ludwig LUDWIG_COMMIT=<sha> python3 scripts/build_package.py --check
```

## Service to TensorLBM

1. **Model selection**: copy the run-time free-energy/vtable pattern so MCMP models are not
   compile-time coupled (needed before a two-phase `POISEUILLE` benchmark can even choose a model).
2. **Accuracy harness**: the analytic `σ(a,b,κ)` / `ξ(a,b,κ)` pair plus a droplet measurement is
   the template for a two-channel surface-tension acceptance check (criterion 3%).
3. **Interface-current risk**: the two-point face gradient of `mu` is the concrete mechanism
   behind parasitic interface currents in driven two-phase channel flow — the gap
   `GAP-LBM-MCMP-MU-STENCIL` asks for a stencil-order convergence study rather than a guess.
4. **Test discipline**: Ludwig's two-phase regression is a "smoke test" with no physical
   assertion; TensorLBM must not repeat that (quantitative assertions only).
5. **Falsified premises**: no `gauge` formulation and no SCMP pseudo-potential exist here —
   Ludwig cannot serve as a baseline for either, which changes what TensorLBM may cite it for.