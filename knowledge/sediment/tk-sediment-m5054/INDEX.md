# Sediment package: TensorSPH 3-D operators: what the analytic benchmarks actually verify (mission m5054)

* task_key: `tk-sediment-m5054` (idempotent key, do not rename)
* source: `TensorSPH` @ `82b72a15c044259d1e7c8d638e9273705fa42e7b` (mission m5054, branch `agent/m5054`, PR #338)
* producer: `ke.sediment_extract (mission m14526)` via `ke/sediment_extract.py` (spec: `knowledge/sediment/tk-sediment-m5054/spec.json`)
* epistemic status: **draft** — claims are unassessed; no review event is written here (producer must not self-review).

## Claims

| claim id | type | statement |
|---|---|---|
| `tkc:sph-m5054:kernel-quadrature-exact` | mathematical | At TensorSPH@82b72a15 the 3-D cubic-spline kernel satisfies both normalisation identities to double precision on the source lattice: sum(W*dV) = 1 with error 4.0e-15 and sum(r^2*laplacian(W)*dV) = 6 with error -1.5e-10; the discrete Laplacian at the origin equals the analytic value digit for digit. Residual error in the 3-D operators therefore cannot be blamed on the kernel. |
| `tkc:sph-m5054:mass-calibration-lattice-constant` | methodological | The lattice mass-calibration constant C is identical to all digits on every resolution of the dx ladder (dx = 0.02 -> 0.0025, spread exactly 0.0), and at h/dx = 1 the residual mass bias is -2.75e-5 on the tension side, where the Tait equation clamps it to p = 0. The bias is therefore a property of the lattice geometry, not a discretisation error that shrinks with dx: one calibration per lattice suffices. |
| `tkc:sph-m5054:laplacian-renorm-scope` | descriptive | On the operator ladder the second-moment-renormalised Laplacian is monotone in kh (relative L2 error 19.37 % -> 11.36 % -> 5.20 % -> 2.96 % for kh = 0.681, 0.511, 0.340, 0.255) while the raw Laplacian is not (5.38 % -> 4.01 % -> 11.24 % -> 13.87 %): the raw operator is twice as accurate at kh = 0.681 and only the renormalised one converges. Renormalisation is thus a fine-kh measure (kh <~ 0.34 on this lattice), not a blanket improvement. |
| `tkc:sph-m5054:shear-verdict-fail-is-a-coverage-failure` | interpretive | The 3-D unsteady-Stokes shear benchmark reports verdict 'fail' although all six of its criteria are true: the failure is missing case h1.8 in missing_cases. Its headline number (decay-rate error within 2.7 %) holds only on the finest rung (n = 24, -2.68 %); n = 12 is -12.62 %, and at n = 20 the unrenormalised operator is +11.46 % while the renormalised one is -4.18 %. Any citation of the 2.7 % figure must carry kh and the operator variant. |
| `tkc:sph-m5054:hydrostatic-headline-is-a-single-point` | interpretive | The hydrostatic-column benchmark reports verdict 'fail' with 4 of 8 criteria false. Its 2.75 % bottom-pressure error exists only for the best run (Adami wall, c0 = 20): c0 = 10 gives -4.30 %, c0 = 5 gives -8.74 %, the Tait-only wall model gives -25.23 %, and the per-layer core maximum relative error is 43.17 %. The 2.7 % figure is therefore a single bottom-load number and must not be read as per-layer pressure accuracy. |
| `tkc:sph-m5054:delivery-contract-broken-honest-fail` | interpretive | Mission m5054 is an honest partial delivery, not a closed one: at its pinned commit the README advertises the 3 %-level 3-D verification and links docs/verification_threed.md, but that file does not exist at 82b72a15 (git cat-file -e exits 128), and the committed guard test tests/test_threed_artifacts.py asserts verdict == 'pass' for the shear and hydrostatic reports while both committed reports say 'fail'. Executing that guard file against the pinned artifacts gives 2 failed / 1 passed (runs/m5054/source_guard/source_guard.json). Operator core is verified; documentation and the artifact/guard contract are not. |

## Evidence (verbatim, offsets at the pinned commit)

| evidence id | source path | lines | relation |
|---|---|---|---|
| `tke:sph-m5054:kq-kernel-integral` | `benchmarks/threed_kernel/report.json` | L12-L12 | supports |
| `tke:sph-m5054:kq-second-moment` | `benchmarks/threed_kernel/report.json` | L14-L14 | supports |
| `tke:sph-m5054:kq-laplacian-origin` | `benchmarks/threed_kernel/report.json` | L16-L16 | supports |
| `tke:sph-m5054:mc-dx-spread` | `benchmarks/threed_kernel/report.json` | L121-L125 | supports |
| `tke:sph-m5054:mc-bias-h1` | `benchmarks/threed_kernel/report.json` | L27-L27 | supports |
| `tke:sph-m5054:lap-corrected-n12` | `benchmarks/threed_kernel/report.json` | L136-L136 | supports |
| `tke:sph-m5054:lap-raw-n12` | `benchmarks/threed_kernel/report.json` | L135-L135 | supports |
| `tke:sph-m5054:lap-raw-n24` | `benchmarks/threed_kernel/report.json` | L161-L161 | supports |
| `tke:sph-m5054:lap-corrected-n32` | `benchmarks/threed_kernel/report.json` | L175-L175 | supports |
| `tke:sph-m5054:shear-verdict` | `benchmarks/threed_shear/report.json` | L1057-L1060 | supports |
| `tke:sph-m5054:shear-missing-cases` | `benchmarks/threed_shear/report.json` | L1057-L1059 | supports |
| `tke:sph-m5054:shear-decay-n24` | `benchmarks/threed_shear/report.json` | L376-L376 | supports |
| `tke:sph-m5054:shear-decay-n12` | `benchmarks/threed_shear/report.json` | L33-L33 | supports |
| `tke:sph-m5054:shear-raw-n20` | `benchmarks/threed_shear/report.json` | L1029-L1029 | supports |
| `tke:sph-m5054:hydro-bottom-best` | `benchmarks/threed_hydrostatic/report.json` | L35-L35 | supports |
| `tke:sph-m5054:hydro-bottom-tait` | `benchmarks/threed_hydrostatic/report.json` | L710-L710 | supports |
| `tke:sph-m5054:hydro-core-max` | `benchmarks/threed_hydrostatic/report.json` | L37-L37 | supports |
| `tke:sph-m5054:hydro-verdict` | `benchmarks/threed_hydrostatic/report.json` | L1425-L1426 | supports |
| `tke:sph-m5054:dc-readme-27pct` | `README.md` | L19-L19 | contextualizes |
| `tke:sph-m5054:dc-readme-missing-doc` | `README.md` | L19-L19 | refutes |
| `tke:sph-m5054:dc-guard-asserts-pass` | `tests/test_threed_artifacts.py` | L56-L59 | refutes |

## Benchmark re-derivation (ref vs got, computed by the extractor)

| row | reference | ref | got | rel. error | tolerance | within |
|---|---|---|---|---|---|---|
| `kernel-integral` | int W dV = 1 (analytic) | 1 | 1 | +4e-13% | 1e-09% | yes |
| `kernel-second-moment` | int r^2 laplacian(W) dV = 6 (analytic) | 6 | 6 | -2.5e-09% | 1e-06% | yes |
| `kernel-laplacian-origin` | -9*(1/(pi h^3))/h^2 (cubic-spline Laplacian at r=0) | -7.71571e+09 | -7.71571e+09 | -0% | 1e-09% | yes |
| `shear-decay-n24` | 2*nu*(2*pi/L)^2 (unsteady-Stokes decay rate) | 3.94784 | 3.84214 | -2.68% | 3% | yes |
| `shear-decay-n12` | 2*nu*(2*pi/L)^2 (unsteady-Stokes decay rate) | 3.94784 | 3.44962 | -12.6% | 15% | yes |
| `shear-raw-n20` | 2*nu*(2*pi/L)^2, raw Laplacian, n = 20 | 3.94784 | 4.40032 | +11.5% | 3% | **no** |
| `shear-renorm-n20` | 2*nu*(2*pi/L)^2, renormalised Laplacian, n = 20 | 3.94784 | 3.78301 | -4.18% | 3% | **no** |
| `hydro-bottom-best` | rho0*g*(H - dx/2) (hydrostatic bottom load) | 1520.55 | 1478.77 | -2.75% | 3% | yes |
| `hydro-bottom-tait` | rho0*g*(H - dx/2), Tait-only wall model (control run) | 1520.55 | 1136.93 | -25.2% | 15% | **no** |
| `hydro-core-max` | 0 (exact hydrostatic profile), core layers | 0 | 0.431741 | abs +0.4317 | 0.15 (abs) | **no** |
| `lattice-second-moment-K` | continuum second moment K = 2 (lattice value may differ) | 2 | 2.34685 | +17.3% | 15% | **no** |

Worst row: `hydro-bottom-tait` (25.2% off the reference).

## External anchors

* Monaghan 1992, Smoothed Particle Hydrodynamics, Annu. Rev. Astron. Astrophys. 30:543-574 — defines the kernel admissibility conditions (unity and second-moment normalisation) used by claims kernel-quadrature-exact and mass-calibration-lattice-constant
* Morris, Fox & Zhu 1997, Modeling low Reynolds number incompressible flows using SPH, J. Comput. Phys. 136:214-263 — source of the renormalised viscous operator family against which laplacian-renorm-scope is judged
* Randles & Libersky 1996, Smoothed Particle Hydrodynamics: some recent improvements and applications, CMAME 139:375-408 — corrected-SPH / reproducing-condition lineage behind the second-moment normalisation
* Adami, Hu & Adams 2012, A generalized wall boundary condition for smoothed particle hydrodynamics, J. Comput. Phys. 231:7057-7075 — defines the wall model whose hydrostatic bottom load is the headline of hydrostatic-headline-is-a-single-point
* Colagrossi & Landrini 2003, Numerical simulation of interfacial flows by smoothed particle hydrodynamics, J. Comput. Phys. 191:448-475 — documents the spurious pressure / odd-even mode at free surfaces that the hydrostatic per-layer table exposes

## Reproduce

```bash
python3 -m ke.sediment_extract --spec knowledge/sediment/tk-sediment-m5054/spec.json --source-repo /root/tensor-ecosystem/TensorSPH --out knowledge/sediment/tk-sediment-m5054 --run-dir docs/sediment/tk-sediment-m5054/runs/extract && python3 -m ke.sediment_verify --package knowledge/sediment/tk-sediment-m5054 --spec knowledge/sediment/tk-sediment-m5054/spec.json --source-repo /root/tensor-ecosystem/TensorSPH --run-dir docs/sediment/tk-sediment-m5054/runs/extract --report docs/sediment/tk-sediment-m5054/runs/validate/validate_report.json
```

## Limits

* The quotes pin *what the source committed*, not whether the physics is right; assessment is the job of an independent reviewer (assessment_status=unassessed).
* Numbers come from the source artifacts at the pinned commit; this package re-derives the reference values but never re-runs the SPH solver.
