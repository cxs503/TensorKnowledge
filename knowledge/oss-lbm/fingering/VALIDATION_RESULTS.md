# VALIDATION_RESULTS — knowledge/oss-lbm/fingering

Agent: agent-m8691 · Branch: agent/m8691 · Date: 2026-11-09T15:19:17Z
Source: ebinan92/Fingering_dynamics @ 150a5739e320498c6ecf22ba31ab9ebc57130462 (snapshot /tmp/fing_src)

## 1. Snapshot identity and fidelity

```
$ git ls-remote https://github.com/ebinan92/Fingering_dynamics
150a5739e320498c6ecf22ba31ab9ebc57130462	HEAD
150a5739e320498c6ecf22ba31ab9ebc57130462	refs/heads/master

$ python3 - (git blob SHA-1 of every tracked text file vs GitHub tree listing)
tracked text files checked: 14, blob-SHA mismatches: 0
```

## 2. Package validator (schema · cross-refs · GAP anchors · quote hygiene · verbatim re-extraction)

```
$ python3 knowledge/oss-lbm/fingering/validate_oss_lbm_fingering.py
PASS: 12 claims, 23 evidence, 1 provenance
  epistemic status: contested=2, established=3, provisional=7
  every claim carries a gap-anchor (GAP-LBM-MCMP-POISEUILLE + free-energy anchor)
  all evidence unassessed (no self-approval)
  verbatim re-extraction against /tmp/fing_src
exit=0
```

## 3. Test suite

```
$ python3 -m pytest knowledge/oss-lbm/fingering -q
.........                                                                [100%]
9 passed in 0.80s
```

## 4. Quote re-extraction spot check (independent of the validator)

```
$ python3 - (re-extract every locator from source, compare to stored quote)
quotes re-extracted and matched verbatim: 23/23
max quote length (lines): 3
```

## 5. Claim inventory (programmatically rendered from claims.json)

```
 #  claim id                                       status       #ev  locators
 1  fing-free-energy-calibration                   established    3  lattice_boltzmann/fingering.py:40-42, lattice_boltzmann/fingering_periodic.py:37-39, lattice_boltzmann/validation.py:34-36
 2  fing-chemical-potential-sign-equivalence       established    2  lattice_boltzmann/fingering.py:148-149, lattice_boltzmann/validation.py:117-118
 3  fing-zou-he-force-corrected                    provisional    2  lattice_boltzmann/fingering.py:296-298, lattice_boltzmann/fingering.py:378-378
 4  fing-halfway-bounceback                        provisional    2  lattice_boltzmann/bounce_back.py:10-10, lattice_boltzmann/bounce_back.py:48-49
 5  fing-wetting-via-order-parameter               provisional    4  lattice_boltzmann/fingering.py:19-19, lattice_boltzmann/fingering.py:215-217, lattice_boltzmann/validation.py:71-71, lattice_boltzmann/fingering_periodic.py:18-18
 6  fing-validation-no-angle-measurement           contested      2  lattice_boltzmann/validation.py:22-22, lattice_boltzmann/validation.py:419-421
 7  fing-one-sided-initial-perturbation            established    1  lattice_boltzmann/fingering.py:106-107
 8  fing-mixed-viscosity-relaxation                provisional    1  lattice_boltzmann/fingering.py:211-212
 9  fing-mobility-fixed-relaxation                 contested      2  lattice_boltzmann/fingering.py:289-289, lattice_boltzmann/fingering.py:292-294
10  fing-guo-forcing-chemical-potential            provisional    1  lattice_boltzmann/fingering.py:201-202
11  fing-spectral-ab2-integrating-factor           provisional    2  spectrum_method/main.py:11-11, spectrum_method/main.py:58-60
12  fing-no-buoyancy-capillary-driven              provisional    1  lattice_boltzmann/fingering.py:39-39
```

## 6. Verification numbers for the three 'established' claims

```
[C1] kappa=0.75*xi*sigma=0.067500  a=-2*kappa/xi^2=-0.033750
[C1] sigma declared          = 0.045000000000000
[C1] sigma from free-energy  = 0.045000000000000   rel.err = 3.084e-16
[C1] 4*kappa/(3*xi)          = 0.045000000000000
[C1] max|mu(tanh profile)|   = 3.469e-18
[C2] simplify(mu_fingering - mu_validation) = 0
[C7] unique values of my_number           = [-1.]
[C7] perturbation range                   = [-9.994e-04, -1.758e-08]  mean = -5.018e-04
[C7] intended-symmetric mean (reference)  = -7.792e-06
```

## 7. Figure (artifact)

| file | sha256 | caption |
|---|---|---|
| `artifacts/fig1_fingering_verification.png` | `0df26a997201ee8ed421143ff7ec0302551c82917070c69e243d976da550bf52` | (a) equilibrium interface ψ=tanh(x/ξ) with μ≡0; (b) free-energy surface-tension integral reproduces declared σ (rel. error vs integration width); (c) initial perturbation as coded (one-sided) vs intended symmetric |

## 8. Honest limitations

- No numerical run of the repository solvers was performed (H×W = 380×380, MAX_T = 1000 in pure numpy; no reference/experimental target exists in the repository to compare against, so an error table would be fabricated). All claims are therefore anchored to source evidence, plus three verification surfaces that do not require the solver.
- The 'wettability validation' pathology (claim 6) is asserted from code and grep surface only: the repository ships a PNG (`wettability_validation.png`) whose content was NOT inspected (binary, no metadata); if the author measured the angle offline, the claim should be downgraded to 'not reproducible from the repository'.
- The snapshot was reconstructed from the GitHub tree/blob API listing plus cached files (14/14 blob SHAs match); a full `git clone` was not available in this environment, so directory-level metadata (e.g. file modes) is unverified.
- Commit `150a5739e...` is master HEAD as of 2026-11-09; the repository has not been pushed to since 2019-02-28, so drift risk is negligible but not zero.
