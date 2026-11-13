# M404: DEM-FEM Coupling Interface + Hertz/Beam Benchmarks

## ① Case Introduction
- **Physical background**: Hertz contact theory for sphere-on-half-space (F ∝ δ^1.5)
- **Geometry**: DEM3D bonded-sphere assembly (4×3×4 grid) with spherical indenter (R=0.1m)
- **Parameters**: k_bond=1e5 N/m, tool_speed=5 m/s, max_indent=0.05m
- **Honest-FAIL**: TensorFEM unavailable; DEM lattice ≠ continuum half-space

## ② Methodology
- DEM3D spherical indenter pressing into bonded-sphere assembly
- Power-law fit F = a·δ^b via log-linear regression
- Effective modulus estimated: E_dem ≈ k_bond/(2r), E* = E_dem/[2(1-ν²)]
- Beam fallback: FD Euler-Bernoulli with simply-supported BCs

## ③ Results

| Metric | Hertz (DEM) | Target | Beam (FD n=80) |
|--------|-------------|--------|----------------|
| Exponent | 1.4108 | 1.5±0.05 | — |
| Stiffness error | 44.1% | ≤3% | 0.0125% |
| Energy drift | 58.6% | ≤1% | — |
| Mesh conv | 8.4% | <5% | converging |

## ④ Figures
See attached: Hertz F-δ curve + beam deflection comparison

## ⑤ Notes
- DEM discrete lattice cannot reproduce continuum Hertz contact
- Beam FD shows second-order convergence (error ∝ 1/n²)
- Schema  validates against jsonschema

## ⑥ Error Assessment
- Hertz exponent 1.4108 vs 1.5: **5.9% error, FAIL** (outside ±0.05)
- Hertz stiffness 44.1%: **FAIL** (target ≤3%)
- Beam stiffness 0.0125%: **PASS** (<3%)
