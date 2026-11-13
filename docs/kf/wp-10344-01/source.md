# Point-particle (unresolved) two-way CFD-DEM coupling — Verification Report

## 1. Case Introduction

Point (unresolved) particles are smaller than a fluid cell: the particle surface is not resolved, the hydrodynamic force is supplied by analytic closures (Stokes/Schiller-Naumann drag, Richardson-Zaki hindrance, added-mass, pressure-gradient) and the reaction is returned to the Eulerian fluid as a momentum source via adjoint trilinear spreading.

**Governing equations:**
- Particle: `m_p du_p/dt = F_drag + F_pg + F_am + (ρ_p - ρ_f) V_p g + F_ext`
- Fluid: `ρ_f Du_f/Dt = -∇p + μ∇²u_f + f_{p→f}/(1-ε)`, `∇·u_f = 0`
- Interphase: `f_{p→f} = -Σ F_drag` (adjoint trilinear spread)

**Parameters:** ρ_p/ρ_f = 2, μ = 0.5, g = 0.5, C_A = 0.5 (sphere)

## 2. Method

- `closures.py`: pure functions for all coefficients (Stokes drag, Schiller-Naumann, RZ exponent, added-mass)
- `fluid.py`: triply periodic pseudo-spectral solver with exact viscous integrating factor, Leray projection, adjoint trilinear particle-grid transfer
- `particles.py`: vectorised Lagrangian particles with implicit added-mass integration `(m_p + C_A m_a) a = F`
- `coupling.py`: two-way loop with self-response correction, container-frame Galilean shift, momentum budget tracking
- `verification.py`: five closed-form verification faces

## 3. Results

| Gate | Criterion | Measured | Threshold | Verdict |
|---|---|---|---|---|
| Stokes terminal velocity | |U - v_t|/v_t ≤ 2% | 1.984% | 2% | **PASS** |
| Added-mass oscillation | |ω_num - ω_th|/ω_th ≤ 5% | 0.864% | 5% | **PASS** |
| Momentum exchange | |Δp_p + Δp_f|/max ≤ 1e-6 | 1.95e-14 | 1e-6 | **PASS** |
| Richardson-Zaki | |u_s - u_t εⁿ|/(u_t εⁿ) ≤ 10% | 8.681% | 10% | **PASS** |
| Pressure-gradient | |F_pg - F_analytic|/|F_analytic| ≤ 2% | 0.816% | 2% | **PASS** |

## 4. Figures

Five figures generated: stokes_terminal_velocity.png, added_mass_oscillation.png, momentum_exchange.png, richardson_zaki.png, pressure_gradient.png.

## 5. Limitations

1. Periodic box ≠ unbounded fluid; self-response correction needed (19% error without it)
2. Self-response is a steady/creeping construct; ill-conditioned when h < d
3. No particle-particle contacts modelled (fluid coupling verification only)
4. Model B (div u = 0) used; no volume-averaged momentum equation
5. No walls — wall-bounded coupling out of scope

## 6. Error Assessment

| Quantity | Reference | Error | < 3%? |
|---|---|---|---|
| Terminal velocity | Stokes v_t | 1.984% | YES |
| Added-mass frequency | √(k/(m_p+C_A m_a)) | 0.864% | YES |
| Momentum conservation | exact | 1.95e-14 | YES |
| Hindered settling | Richardson-Zaki | 8.681% | NO (within 10% gate) |
| Pressure-gradient force | analytic -V_p ∇p | 0.816% | YES |

## 7. Reproduction

```
PYTHONPATH=src pytest tests/test_point_cfd_dem.py -v   # 19 tests pass
PYTHONPATH=src python benchmarks/point_particle_cfd_dem/run.py
```
