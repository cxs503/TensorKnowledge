# OSS-LBM Knowledge Package — openLB

Source-code-driven knowledge extracted from **openLB** (openlb/openLB), the C++
lattice Boltzmann library, for TensorLBM improvement.

## Snapshot

| Item | Value |
|------|-------|
| Repo | https://github.com/openlb/openLB |
| Commit (short) | `6c3934d` |
| Commit (full) | `6c3934dea66e4c3cad66049f579e00b93effc256` |
| Commit date | 2019-12-02 |
| Cache location | `/root/openlb` (note: `/root/oss-cache/` does not exist on this host; the openLB cache lives at `/root/openlb`, same commit) |
| License | GPL-2-or-later (file headers; no LICENSE file in snapshot) |

## Scope (13 claims)

| # | Claim ID | Topic | Epistemic |
|---|----------|-------|-----------|
| 1 | `tkc:oss-lbm:openlb-gpl2-reference-only` | GPL-2 copyleft header → reference-only boundary | well-supported |
| 2 | `tkc:oss-lbm:openlb-shanchen-two-lattice` | Shan-Chen two-lattice coupling (common velocity + stencil-sum force) | well-supported |
| 3 | `tkc:oss-lbm:openlb-interaction-potential-library` | Pluggable EOS/potential library (ShanChen93/94, PengRobinson, CarnahanStarling, Krause, WeisbrodKrause, Normal, PsiEqualsRho) | well-supported |
| 4 | `tkc:oss-lbm:openlb-eos-temperature-overload` | Temperature-dependent EOS operator() overload | well-supported |
| 5 | `tkc:oss-lbm:openlb-free-energy-model` | Free-energy model, chemical-potential coupling, 9-point 1/12 stencil, 2–3 components | well-supported |
| 6 | `tkc:oss-lbm:openlb-boussinesq-coupling` | Boussinesq force + velocity copy | well-supported |
| 7 | `tkc:oss-lbm:openlb-thermal-d3q7-lattice` | D3Q7 thermal lattice | well-supported |
| 8 | `tkc:oss-lbm:openlb-validation-surface` | Validation examples with analytical references (youngLaplace, contactAngle 100°, rayleighBenard Ra=1e4/Pr=0.71) | well-supported |
| 9 | `tkc:oss-lbm:openlb-meta-descriptor` | Variadic-template descriptor with compile-time field introspection | well-supported |
| 10 | `tkc:oss-lbm:openlb-bounceback-dynamics` | Bounce-back as a Dynamics class | well-supported |
| 11 | `tkc:oss-lbm:openlb-turbulence-models` | Smagorinsky / dynamic / WALE + porous variants | well-supported |
| 12 | `tkc:oss-lbm:openlb-no-freesurface-snapshot` | **Negative result:** no free-surface module in this snapshot | provisional |
| 13 | `tkc:oss-lbm:openlb-cpu-mpi-parallel` | **Negative result:** no CUDA in this snapshot; MPI-based parallelism | provisional |

## Structure

```
openlb/
├── README.md
├── claims/claims.json          # 13 claim records (schema: claim-record.schema.json)
├── evidence/evidence.json      # 13 evidence records (schema: evidence-record.schema.json)
├── provenance/provenance.json  # 1 provenance record (schema: provenance-record.schema.json)
└── test_openlb_knowledge.py    # Pytest self-validator (incl. verbatim-quote anti-fabrication gate)
```

## Epistemic Discipline

- **No `established`**: this package is source-inspection-only (no runs, no
  benchmarks). Per the conservative rule, code-level descriptive facts are
  `well-supported`; snapshot-dependent absence claims are `provisional`.
- All evidence `assessment_status: unassessed` (draft, no self-approval).
- All locators are `code-location` with `openlb@6c3934d file:line` and a
  **verbatim** English quote of ≤3 lines.
- **Anti-fabrication gate**: `test_quotes_verbatim_in_cache` re-reads the cache
  and asserts every quote line matches the cited file:line byte-for-byte
  (skipped if the cache is absent on the host).
- Every claim carries the **GAP-LBM-INDUSTRIAL-ENG** anchor in its notes
  (industrial-grade engineering anchor). The GPL-2 contagion judgment
  (reference-only boundary) is explicit in claim 1 and enforced by
  `test_gpl_boundary_explicit`.

## Validation

```bash
pytest knowledge/oss-lbm/openlb/test_openlb_knowledge.py -v
```

Checks: file presence, ID patterns/uniqueness, bidirectional cross-references,
count ≥8, epistemic enums, no self-approval, required fields, GAP anchor on
every claim, explicit GPL reference-only judgment, locator format, quote
length ≤3, verbatim quotes against the cache, full-commit provenance linkage.

## Known Limitations

1. The snapshot (2019-12-02) **predates openLB's free-surface module** — the
   task's free-surface anchor is `insufficient` against this snapshot
   (claim 12). Re-cache a current release before any free-surface claim.
2. The snapshot has **no CUDA/GPU backend** (claim 13).
3. The snapshot bundles **no numerical run results** for the validation
   examples — the validation *surface* exists, magnitudes must be re-run.
4. The snapshot is an "unofficial mirror" without a LICENSE file; the license
   claim rests on the consistent per-file GPL-2 headers.
