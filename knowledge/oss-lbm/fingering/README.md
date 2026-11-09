# OSS-LBM · Fingering_dynamics sub-package

Source-code knowledge extraction for **`ebinan92/Fingering_dynamics`** — a two-phase
free-energy lattice-Boltzmann solver with Zou–He open boundaries, half-way bounce-back and
wall-order-parameter wetting, plus a companion pseudo-spectral solver for viscous fingering.

| Field | Value |
|---|---|
| Repository | `ebinan92/Fingering_dynamics` (public, default branch `master`) |
| Commit | `150a5739e320498c6ecf22ba31ab9ebc57130462` (master HEAD via `git ls-remote`, 2026-11-09; last push 2019-02-28) |
| Snapshot fidelity | all 14 tracked text files verified byte-for-byte against the GitHub blob SHA-1s of the API tree listing (`/tmp/fing_manifest.json`), 0 mismatches |
| Claims | 12 (`established` 3, `provisional` 7, `contested` 2) |
| Evidence | 23 verbatim code quotations, each ≤ 3 lines, `repo@commit path:line` locator |
| Provenance | 1 record (activity = extraction, agent = `agent-m8691`) |
| Anchor | every claim carries a `gap-anchor:` condition — free-energy phase-field anchor (κ = 0.75ξσ, a = −2κ/ξ², σ = 4κ/(3ξ)) + adjacent **GAP-LBM-MCMP-POISEUILLE** |
| Status | **draft** — all evidence `assessment_status: unassessed`, no self-approval |

## What the repository is

```
lattice_boltzmann/
  fingering.py              Poiseuille/fingering between top & bottom wall (free-energy LBM, wetting psi_wall=-1.0)
  fingering_periodic.py     same, periodic in the transverse direction (psi_wall=-0.5)
  fingering_periodic_gpu.py GPU (cupy) variant of the above
  bounce_back.py            half-way bounce-back for rectangular obstacles (f and g pairs)
  create_block.py           obstacle geometry helpers
  validation.py             droplet-on-wall run ("wettability validation", psi_wall=0.0)
spectrum_method/
  main.py                   non-reactive viscous fingering by pseudo-spectral method (Tan & Homsy reference)
  main_3phase.py            three-phase precipitation viscous fingering
```

## Claim list

| # | Claim id | Status | Where |
|---|---|---|---|
| 1 | `fing-free-energy-calibration` | established | fingering.py:40-42 (+ periodic:37-39, validation:34-36) |
| 2 | `fing-chemical-potential-sign-equivalence` | established | fingering.py:148-149 vs validation.py:117-118 |
| 3 | `fing-zou-he-force-corrected` | provisional | fingering.py:296-298, 378 |
| 4 | `fing-halfway-bounceback` | provisional | bounce_back.py:10, 48-49 |
| 5 | `fing-wetting-via-order-parameter` | provisional | fingering.py:19, 215-217; validation.py:71; periodic:18 |
| 6 | `fing-validation-no-angle-measurement` | **contested** | validation.py:22, 419-421 |
| 7 | `fing-one-sided-initial-perturbation` | established | fingering.py:106-107 |
| 8 | `fing-mixed-viscosity-relaxation` | provisional | fingering.py:211-212 |
| 9 | `fing-mobility-fixed-relaxation` | **contested** | fingering.py:289, 292-294 |
| 10 | `fing-guo-forcing-chemical-potential` | provisional | fingering.py:201-202 |
| 11 | `fing-spectral-ab2-integrating-factor` | provisional | spectrum_method/main.py:11, 58-60 |
| 12 | `fing-no-buoyancy-capillary-driven` | provisional | fingering.py:39 (+ repo-wide negative search) |

Full statements, GAP anchors and TensorLBM service notes: `claims/claims.json`.

### Epistemic policy applied here

`established` is used only for claims that have a **validation surface beyond source reading**
executed in this package:

1. calibration triple — numeric free-energy integral reproduces σ = 4κ/(3ξ) to < 1e-4 relative
   error and μ(tanh profile) ≡ 0 to < 1e-12;
2. chemical-potential spellings — sympy identity check;
3. one-sided seed — numpy reproduction of `np.random.randint(0, 1, ...)` ≡ 0.

Everything that rests on reading only (boundary conditions, wetting encoding, forcing, spectral
scheme) stays `provisional`; the two **pathologies** are `contested` because the contradiction is
between the repository's *claim* and its *code*, not a settled physical dispute:
* the "wettability validation" script never measures a contact angle (`Theta = np.pi/4` is dead code);
* the order-parameter set relaxes with a fixed τ while momentum relaxes with a spatially varying `mix_tau`,
  undocumented.

## Reproduce

```bash
# extract (regenerates all three JSON files from a source snapshot; quotes are pulled by line number)
python3 tools/build_claims.py --src /tmp/fing_src --commit 150a5739e320498c6ecf22ba31ab9ebc57130462

# validate (schema + cross-refs + GAP anchors + quote hygiene + verbatim re-extraction)
python3 validate_oss_lbm_fingering.py            # exits 0 / 1

# tests
python3 -m pytest knowledge/oss-lbm/fingering -q # 9 passed
```

Without a snapshot the verbatim layer degrades gracefully (structure is still checked); with
`FINGERING_SRC=<dir>` or `/tmp/fing_src` present every quote is re-extracted and compared.

## How this serves TensorLBM

* **Free-energy multiphase core**: the three calibration relations and the (1 − 1/(2τ)) Guo-type
  chemical-potential-gradient force are directly reusable; TensorLBM's current scope is single-phase.
* **Multiphase pressure boundaries**: force-corrected Zou–He inlet/outlet (`psi_x*mu/6` terms) is a
  ready reference implementation; TensorLBM only has the single-phase variant.
* **Wetting fallback**: a single wall order-parameter value is the cheapest wettability knob — with the
  explicit caveat that this repository provides **no ψ_wall → θ calibration**, so TensorLBM must add a
  contact-angle extractor and an error table (< 3 %) before claiming wettability validation.
* **Cross-validation reference**: the pseudo-spectral solver gives an independent (FFT/AB2) solution of
  the same fingering physics at negligible cost — usable as a reference curve for the LBM case.
* **Anti-patterns to avoid**: one-sided random seeding (non-zero mean perturbs the growth rate) and
  "validation by eyeballing a colour map".