# Claim 08: Double Precision Default with Single-Precision Warning

**claim_id**: CUDAPF-008
**epistemic_status**: established
**gap_anchor**: GAP-LBM-PHASEFIELD-3PH

## Statement
The solver defaults to double precision (kind(0.0d0)). Single precision is available but the README explicitly warns against it for quantitative results, noting "a gradual drift (a slow decrease in phi3_min, small unphysical wobble in total mass conservation) as rounding error accumulates."

## Evidence
**Source**: `src/precision_m.f90` (lines 1-6)
```fortran
module precision_m
    integer, parameter :: singlePrecision = kind(0.0)
    integer, parameter :: doublePrecision = kind(0.0d0)
    !integer, parameter :: fp_kind = singlePrecision
    integer, parameter :: fp_kind = doublePrecision
end module precision_m
```

**Source**: `README.md` (Precision section)
```
**Double precision is the default** and is recommended for any run whose results you intend to trust or report.
**Single precision** runs faster and uses half the memory, but it comes at a real cost to numerical stability:
over long runs it shows a gradual drift (a slow decrease in `phi3_min`, small unphysical wobble in total mass
conservation) as rounding error accumulates timestep over timestep.
```

## Provenance
- **repo**: AminZar69/CudaPhaseField
- **commit**: d6181e677c413bbec443570010bca60d896022b5
- **files**: `src/precision_m.f90`, `README.md`

## Notes
This is a notable self-documented limitation: the author explicitly acknowledges mass conservation drift in single precision. For any benchmarking or validation work, double precision should be used. The precision is controlled by a single toggle in precision_m.f90.
