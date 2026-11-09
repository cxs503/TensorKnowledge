# Claim 04: Cahn-Hilliard Chemical Potential with Three-Component Coupling

**claim_id**: CUDAPF-004
**epistemic_status**: established
**gap_anchor**: GAP-LBM-PHASEFIELD-3PH

## Statement
The chemical potential for each phase follows a three-component Cahn-Hilliard form with pairwise interfacial energy parameters lambda(i) and a three-phase coupling term involving lambdat. The chemical potential mu_i includes a double-well potential term and a gradient energy (Laplacian) term.

## Evidence
**Source**: `src/global_subroutines.f90` (chemical_potential kernel, lines ~330-345)
```fortran
mu1(x,y) = (12._fp_kind / w) * (lambda(1) * s_phi1(tx,ty) * (1._fp_kind- s_phi1(tx,ty)) * (1._fp_kind - 2._fp_kind * s_phi1(tx,ty))  &
    - 2._fp_kind * lambdat * s_phi1(tx,ty) * s_phi2(tx,ty) * (1._fp_kind - s_phi1(tx,ty) - s_phi2(tx,ty))) &
        - (3._fp_kind / 4._fp_kind) * w * lambda(1) * d2phi1(x,y)
```

**Source**: `src/device_var.f90` (lambda computation, lines ~20-25)
```fortran
real(fp_kind), constant, parameter :: lambda(3) = [(sigma(2,1) + sigma(3,1) - sigma(3,2)), &
    (sigma(2,1) + sigma(3,2) - sigma(3,1)), (sigma(3,1) + sigma(3,2) - sigma(2,1))]
real(fp_kind), constant, parameter :: lambdat = 3._fp_kind / ((1._fp_kind / lambda(1)) + (1._fp_kind / lambda(2)) + (1._fp_kind / lambda(3)))
```

## Provenance
- **repo**: AminZar69/CudaPhaseField
- **commit**: d6181e677c413bbec443570010bca60d896022b5
- **files**: `src/global_subroutines.f90`, `src/device_var.f90`

## Notes
The lambda parameters are derived from the pairwise surface tension matrix sigma(3,3). The three-phase coupling term lambdat ensures thermodynamic consistency for three-phase systems. The double-well potential phi*(1-phi)*(1-2*phi) is the derivative of phi^2*(1-phi)^2.
