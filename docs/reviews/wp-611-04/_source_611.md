# SIR-PC2 | F07 | DEM Buoyancy & Wet Coupling Model

## 1. Case Introduction

DEM particles (ice floes) near the free surface experience buoyancy, wave forces, and wet drag. This work implements and verifies the complete wet coupling model for TensorDEM, covering 2-D circular disk and 3-D sphere geometries.

**Parameters:** R=0.5m, ρ_i=917 kg/m³, ρ_w=1025 kg/m³, g=9.81 m/s², wave A=0.1m, λ=10m, T=2.5s.

## 2. Methodology

- **Submerged fraction:** 2-D circular segment / 3-D spherical cap (analytical, vectorised)
- **Buoyancy:** Archimedes principle: F_b = ρ_w·g·V_sub
- **Wetted area:** Side + cap (2-D) / spherical cap surface (3-D)
- **Wave force:** Morison equation with Airy wave theory (deep-water decay)
- **Equilibrium:** Bisection solver for f_sub = ρ_i/ρ_w
- **Stability:** Heave restoring stiffness k_heave = ρ_w·g·V_total·|df_sub/dh| > 0

## 3. Results

| Metric | 2-D Disk | 3-D Sphere |
|--------|----------|------------|
| Buoyancy max rel error | 2.15e-16 | 2.19e-16 |
| Equilibrium h_eq (m) | -0.3378 | -0.2986 |
| f_sub at equilibrium | 0.8946 | 0.8946 |
| Heave stiffness (N/m) | 7414 | 5081 |
| Heave stable | True | True |
| GM (m) | ≈0 (neutral) | -0.115 (unstable) |

## 4. Figures

See attached figures (6 total): submerged fraction, buoyancy force, wetted area, equilibrium diagram, heave stiffness, wave force time series.

## 5. Notes

- 2-D disk GM≈0 and 3-D sphere GM<0 are known analytical results; roll stability in ice fields comes from inter-particle contacts.
- Heave (vertical) stability is the relevant criterion for DEM particles: k_heave > 0 always for floating bodies.
- Morison equation valid for D/λ < ~0.1; at D/λ=0.1 we are at the upper limit.

## 6. Error Assessment

| Quantity | Reference | Error | <3%? |
|----------|-----------|-------|------|
| Buoyancy force | Archimedes | 2.19e-16 | YES |
| Equilibrium f_sub | ρ_i/ρ_w | 7.18e-13 | YES |
| Heave stability | k>0 | k=5081 N/m | YES |

**All acceptance criteria PASS.**