# GAP anchors — OSS-LBM ingestion line (TensorKnowledge)

This file is the **registry** for the gap anchors used by the claims in
`knowledge/oss-lbm/kruger/`.  A GAP anchor names a *missing capability* (a gap) that a
claim's evidence is supposed to close, and states who owns closing it.  The validator
(`validate_kruger.py`) refuses any claim whose `notes` do not name an anchor that appears
in this file.

Format: `GAP-<DOMAIN>-<TOPIC>` — owner — what the gap is — how this package touches it.

---

## GAP-LBM-BENCH-METHODOLOGY

**Owner** — TensorKnowledge / OSS-LBM ingestion line (mission m8676).  Registry entry
created 2026-11-09; the anchor is claimed by the `knowledge/oss-lbm/**` line, i.e. the
OSS-code knowledge base, *not* by the solver repositories.

**Gap.** TensorLBM has no written, executable methodology for turning *published
benchmark case spectra* into acceptance criteria.  Concretely, the platform can run LBM
kernels but cannot answer, with evidence: which canonical case (Poiseuille / Couette /
Taylor-Green / droplet Laplace pressure / cylinder cross-flow) constrains which error
term; what the reference (analytic) quantity is for each; what boundary-condition
dialect the reference assumes (half-way bounce-back vs wet node; wall plane at y=0 or at
the node centre); and what the acceptable deviation is at each resolution.  Without that
methodology, "LBM solver X is accurate" stays an assertion, not a measurement.

**Standard case spectrum this anchor covers** (the four independently usable references
present in the Krüger accompanying code, plus the interface case):

| Case | Reference quantity | Case code in this repo |
|---|---|---|
| Plane Poiseuille (pressure- or force-driven) | parabolic profile, `u_max = gradP H^2/(8 nu)` | `chapter5/poiseuille_BB.m`, `chapter5/poiseuille_wetnode.m`, `chapter6/force_poiseuille_BB.m` |
| Plane Couette (moving wall) | linear profile `u = u_wall y/H` | `chapter5/couette_BB.m`, `chapter5/couette_wetnode.m` |
| Taylor-Green vortex decay | `exp(-t/t_d)`, `t_d = 1/(nu (kx^2+ky^2))` | `chapter13/python3/vortexdecay.py` (+ cpu/openmp/mpi/gpu) |
| Droplet Laplace pressure (Young-Laplace) | `dp = gamma / r`, gamma invariant in r | `chapter9/shanchen.cpp` |
| Cylinder cross-flow (Kármán) | `St`, `Cd`, `Cl` at fixed `Re`, `D`, blockage | `chapter8/cylinder.cpp` |

**What this package contributes.** 16 claims with verbatim, line-pinned quotations from
`lbm-principles-practice/code@6e2c592`, plus four executed verification runs
(`runs/oss-lbm-kruger-8676/`): the Taylor-Green case reaching measured second-order
convergence (observed order 2.00), Young-Laplace consistency of 1.61 % between two droplet
radii, an IBM-LBM Poiseuille centre-line deviation of −6.5 % at 20 nodes across the
channel, and a machine-precision reproduction of the chapter-5 bounce-back Poiseuille and
Couette solutions at the documented magic relaxation time — **but only for part of the
tested channel widths**, which is recorded as an explicitly `contested` claim rather than
smoothed over.

**Downstream use.** The case/quantity/deviation triple above is what a TensorLBM acceptance
gate needs; the numbers in `runs/oss-lbm-kruger-8676/validation_summary.json` are the first
measured baselines for it.  Closing the gap requires the gate itself (a TensorLBM-side
benchmark harness) — out of scope for this ingestion mission and left explicitly open.

---

## Related anchors (not claimed here, listed for navigability)

* `GAP-LBM-BOUNDARY-PRECISION` — wall-condition accuracy ladder (interpolated
  bounce-back family, wet-node family, magic parameter).  Partly informed by claims
  `kruger-trt-magic-parameter`, `kruger-couette-wetnode-family`,
  `kruger-poiseuille-bb-exactness-scope`; ownership stays with the solver line.
* `GAP-KE-EVIDENCE-GRADING` — how evidence grades (REAL/MOCK/STUB/WITHHELD) map onto
  knowledge records.  Untouched here; this package deliberately stays `unassessed`.