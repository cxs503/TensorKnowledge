# Verification runs — mission m8676 (Krüger OSS-LBM A-line landing)

Everything here is produced by two commands; no number in the report was typed by hand.

```bash
KRUGER_REPO=/path/to/lbm-principles-practice-code bash runs/oss-lbm-kruger-8676/run_upstream_cases.sh
python knowledge/oss-lbm/kruger/build_claims.py     # (re)build the claim package
```

| file | what it is |
|---|---|
| `run_upstream_cases.sh` | compiles + executes the upstream programs, ports chapter5, writes logs, runs the analysis |
| `kruger_bench_port.py` | line-by-line NumPy port of `chapter5/poiseuille_BB.m` and `chapter5/couette_BB.m` (MATLAB/Octave unavailable here) — a *verification surface*, not upstream code |
| `analyze_validation.py` | parses the logs only, emits `validation_summary.json` + figures |
| `validation_summary.json` | the numbers quoted in the platform report and in claim evidence |
| `kruger_bench_results.json` | full port output (profiles, τ sweep, resolution study) |
| `run_meta.json` | upstream commit, remote, commit date, toolchain, execution timestamp |
| `logs/` | raw stdout of every execution (`chapter13` ×3 resolutions, `chapter9` ×2 radii, `chapter11`, port) |
| `figures/`, `kruger_bench_profiles.png` | report figures (matplotlib, embedded into the report as base64) |
| `final_validation.log` | last full validator + pytest transcript |

## Measured headline numbers

| check | result |
|---|---|
| Taylor-Green `L2(u_x)`, NX = 32/64/128 | 7.69e-3 / 1.92e-3 / 4.79e-4 → observed order 2.00 |
| Taylor-Green `E(t)/E(0)` vs `exp(-2t/t_d)` | −1.53 % / −0.38 % / −0.10 % |
| Young-Laplace γ, droplet radii 16.32 vs 12.29 | 0.02072 vs 0.02039 → 1.61 % spread |
| IBM-LBM Poiseuille centre line (Ny = 20) | 1.642e-3 vs 1.756e-3 analytic → −6.5 % |
| chapter5 bounce-back Poiseuille, τ = ½+√(3/16) | L2 = 7.6e-16 (NY=5), 6.8e-13 (NY=15) |
| chapter5 bounce-back Poiseuille, NY = 10 / 20 | L2 = 4.0e-3 / 1.1e-3 → documented exactness **not** reproduced (claim `contested`) |
| chapter5 Couette, τ = 0.9 | L2 = 2.3e-15 |

The last two rows are the honest part: the "exact solution" statement of the upstream
source reproduces at odd channel widths only, so it is recorded as a `contested` claim
instead of being generalised.