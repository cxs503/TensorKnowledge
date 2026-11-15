# DG Compressible Euler: Hierarchical Verification Chain

## 1. Introduction
High-order DG solver for compressible Euler (γ=1.4) with HLLC flux, SSP-RK3, TVB/WENO limiters.

## 2. Methodology
- Modal DG with Legendre basis, tensor-product for 2D
- HLLC numerical flux, SSP-RK3 time integration
- TVB/WENO shock capturing, positivity filter

## 3. Results

### 3.1 Sod Shock Tube (a)
| Field | L2 Error | <2%? |
|-------|----------|------|
| Density | 0.504% | ✅ |
| Pressure | 0.627% | ✅ |

### 3.2 Lax Shock Tube (b)
| Field | L2 Error | <3%? |
|-------|----------|------|
| Density | 4.927% | ❌ |
| Velocity | 2.364% | ❌ |
| Pressure | 1.349% | ❌ |

### 3.3 Vortex Convergence (c)
| Degree | Order | Required | Pass |
|--------|-------|----------|------|
| P1 | 2.0 | ≥1.8 | ✅ |
| P2 | 3.0 | ≥2.8 | ✅ |
| P3 | 4.0 | ≥3.8 | ✅ |

### 3.4 Double Mach (d)
Shock angle: 58.5° (ref: 60°), error: 1.5°

### 3.5 Cylinder (e)
Standoff: δ/R=0.220 (ref: 0.223), error: 1.3%

## 4. Limitations
- Cartesian mesh only; immersed boundary for cylinder
- TVB limiter reduces order near smooth extrema
