# P158W3-N03: TensorDEM CFD-DEM Two-Way Coupling Verification

## 1. Case Introduction

Dilute point-particle Lagrangian tracking with two-way CFD-DEM coupling.
Particle equation: m_p * du_p/dt = F_drag + F_added + F_pressure + m_p*g.
Drag: Schiller-Naumann, Added mass: C_A=0.5, Dense limit: Gidaspow/Ergun.

Parameters: d_p=1e-4m (A1-A4) / 2e-3m (A5), rho_p=2500, rho_f=1000, mu=1e-3/1e-2(A2), g=9.81.

## 2. Method

- A1: RK4 integration of Stokes relaxation, 10 checkpoints vs exponential decay
- A2: Forward Euler settling, high viscosity ensures Re<<1
- A3: Transfer function H(omega) at characteristic frequency extracts C_A
- A4: Momentum ledger per-channel accumulation, Newton's 3rd law audit
- A5: Phi sweep comparing Gidaspow with Ergun Model-A

## 3. Results

### A1: Stokes Relaxation
- tau_p = 1.6667e-03 s, Re_max = 1.0000e-02
- Max relative error = 0.886% (threshold <= 2%)
- **PASS**

### A2: Terminal Velocity
- v_t_Stokes = 8.1722e-04 m/s, v_t_num = 8.1275e-04 m/s
- Re_t = 0.0081, error = 0.547% (threshold <= 3%)
- **PASS**

### A3: Added Mass Coefficient
- C_m_recovered = 0.500000, error = 0.000% (threshold <= 5%)
- **PASS**

### A4: Momentum Conservation
- Single particle residual = 0.0000e+00
- Multi particle (20) residual = 0.0000e+00 (threshold <= 1%)
- **PASS**

### A5: Dense Limit Ergun
- phi>0.4 max error = 0.000% (threshold <= 10%)
- **PASS**

## 4. Figures

See embedded figures (5 plots).

## 5. Notes

1. Stokes relaxation requires Re<0.05 for S-N correction <1%
2. Terminal velocity needs high viscosity to ensure Re_t<<1 so S-N -> Stokes
3. Added mass extracted from transfer function at characteristic frequency
4. Momentum conservation is at machine precision level
5. Gidaspow equals Ergun in dense regime (eps<0.8)

## 6. Error Assessment

| Criterion | Measured | Threshold | Pass |
|-----------|----------|-----------|------|
| A1 | 0.886% | <=2% | Y |
| A2 | 0.547% | <=3% | Y |
| A3 | 0.000% | <=5% | Y |
| A4 | 0.0000e+00 | <=1% | Y |
| A5 | 0.000% | <=10% | Y |

**All passed: YES**