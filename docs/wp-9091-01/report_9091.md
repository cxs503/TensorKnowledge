# FSI 验证阶梯（弱耦合→强耦合）IN70-N04 — 阶段结论

# FSI verification ladder: weak → strong coupling (IN70-N04)

Status: **partial, honest**.  Rung 1 (structural participant) and rung 3
(Theodorsen flutter boundary) pass their gates.  Rung 2 (vortex-induced
vibration, Turek–Hron FSI-2, elastic trailing edge) is **not qualified**: the
fluid half fails its own gate (DFG 2D-2), so no coupled amplitude/frequency
claim is made.  Everything below quotes measured numbers; the JSON records are
in `artifacts/` and the figures in `artifacts/*.png`.

## 1. What was built (and where it lives)

| module | role |
| --- | --- |
| `src/tensorfem/fsi/beam2d.py` | two-node von Kármán beam (axial + bending, geometric stiffening, plane-strain effective modulus), consistent mass, Newmark-β + Newton equilibrium |
| `src/tensorfem/fsi/flow2d.py` | 2-D incompressible MAC solver, exact sparse-LU pressure projection, immersed-marker direct forcing (Uhlmann), body load = momentum exchange + pressure identity |
| `src/tensorfem/fsi/coupling.py` | implicit (strong) coupling driver: sub-iteration to a displacement/force gate, Aitken dynamic relaxation, closed energy ledger |
| `src/tensorfem/fsi/theodorsen.py` | closed-form `C(k)`, 2-DOF pitch–plunge p-k flutter, Wagner-indicial time-domain route, rational `C(k)` fit |
| `src/tensorfem/fsi/benchmarks.py` | DFG 2D-2, Turek–Hron FSI-2 and NACA0012 + elastic trailing-edge drivers, with the literature references embedded |
| `scripts/fsi_ladder_run.py`, `scripts/fsi_ladder_figures.py` | run records (JSON) and figures |
| `tests/test_fsi_{beam2d,flow2d,theodorsen,coupling}.py` | 22 tests (21 pass, 1 strict-xfail for a documented defect) |

The package deliberately does not touch the older rigid-carrier fixtures
(`fluid_rigid_feedback.py`, `ice_panel_fsi.py`); those remain rigid-translation
only.

## 2. Rung 1 — structural participant (PASS)

Clamped-free beam, `E = 2e11 Pa`, `ν = 0.3`, `ρ = 7800 kg/m³`,
`h = 0.05 m`, `L = 1 m`, 40 elements.

| quantity | computed | analytic | error |
| --- | --- | --- | --- |
| tip deflection, unit tip load | −1.600000e−7 m | −1.600000e−7 m (`PL³/3EI`) | < 1e−15 |
| f₁ | 40.8797 Hz | 40.8995 Hz (β₁ = 1.875104) | 0.048 % |
| f₂ | 255.4515 Hz | 256.3128 Hz (β₂ = 4.694091) | 0.34 % |
| f₃ | 711.9738 Hz | 717.6831 Hz (β₃ = 7.854757) | 0.80 % |

Plane strain switches the modulus to `E/(1−ν²)`, which changes the deflection
by exactly `1−ν² = 0.91` (asserted in
`test_plane_strain_uses_effective_modulus`); this is the idealisation used for
the Turek–Hron structure.  Newmark energy conservation without damping or load:
relative drift < 5e−3 over 400 steps.

## 3. Rung 3 — Theodorsen flutter boundary (PASS on the closed form)

`C(k) = H₁⁽²⁾(k)/(H₁⁽²⁾(k) + iH₀⁽²⁾(k))`, evaluated both through
`scipy.special.hankel2` and through the independent `J`/`Y` Bessel routines
(maximum difference 1.1e−16 over `k ∈ [1e-3, 1e2]`).  Analytic limits
reproduced: `C(1e−12) = 1.000000`, `C(1e7) = 0.50000`.

Independent anchors on `C(k)`:

* Jones (1940) two-pole approximation, documented as valid for small `k`,
  agrees within **< 3 % of `|C|` for `k ≤ 0.2`** (worst sample 2.1 %).
* The three-pole rational fit `C ≈ 1/2 + Σ c_j(ik+d_j)⁻¹` used by the
  time-domain route reproduces the exact function on `k ∈ [0.15, 1.5]` with
  **max 0.171 %, mean 0.076 %** relative error (400 log-spaced samples).

Classical section (`μ = 20`, `a = −0.2`, `x_θ = 0.2`, `r_θ = 0.5`,
`ω_h = 1`, `ω_α = 2 rad/s`, `b = 0.5 m`), p-k eigenvalue iteration:

| quantity | value |
| --- | --- |
| `U_f` | **1.1874 m/s** |
| reduced frequency `k_f = ω_f b/U_f` | 0.8654 |
| `ω_f` | 2.0553 rad/s |
| reduced velocity `U_f/(b ω_α)` | 1.1874 |
| frequency ratio `ω_f/ω_α` | 1.028 |
| damping at the boundary | −1.4e−8 (zero by construction) |
| bracket check | σ(0.6`U_f`) < 0 < σ(1.4`U_f`) |

**Cross-route check (honest FAIL on the 3 % target).**  The Wagner-indicial
time-domain integration of the same section, using the 3-pole fit (no shared
code with the p-k solve), gives

| U/U_f | 0.45 | 1.0 | 1.6 | 2.5 |
| --- | --- | --- | --- | --- |
| σ [1/s] (time domain) | −0.0336 | (0 at p-k) | −0.0183 | +0.4686 |

so the time-domain boundary lies between `1.6 U_f` and `2.5 U_f`, i.e. the two
routes disagree by **more than 60 %**, not the 3 % the node asks for.  There is
also a frequency mismatch: the time domain gives `ω ≈ 1.7–1.9 rad/s` near
`U_f` against 2.055 from p-k.  The likely causes, in order of suspicion: (i)
the Wagner/Jones indicial model loses the phase lag of `C(k)` as `k → 1` even
with the fitted poles, because the indicial form assumes a *real* transient
response while `C(k)` at `k ≈ 0.87` still carries a −9° phase; (ii) the
peak-envelope growth-rate estimator is biased by the beating of the two close
structural modes.  No external table could be consulted (offline environment),
so the flutter speed is verified against the closed form and its own analytic
limits, **not** against a published value.  This is recorded as an open item,
not as a pass.

## 4. Rung 2 — fluid half qualification (FAIL)

DFG benchmark 2D-2 (fixed cylinder, `Re = 100`, `U = 1 m/s`, `D = 0.1 m`) with
the same solver and marker machinery used by the coupled rungs,
`nx = 500`, `dt = 1e−3`, `t_end = 12 s`
(`artifacts/fsi_dfg2d2.json`, figure `artifacts/fsi_dfg2d2.png`):

| quantity | computed | reference (Turek & Hron 2006) | error |
| --- | --- | --- | --- |
| mean `C_D` | 0.623 | 3.22 | **80.7 %** |
| `C_L` amplitude | 9.59 | 0.99 | 869 % |
| Strouhal number | 0.1847 | 0.295 | 37.4 % |
| max |∇·u| (interior) | 8.0e−2 s⁻¹ | — | — |

The pressure projection itself is exact (discrete divergence < 1e−9 in the
projection unit test); the failure is localized to the **body-load
reconstruction**: the fictitious-domain pressure identity
`F = −ρ∫χ∇p dV` is spread uniformly over the marker cloud while the
constraint part is per-marker, and the resulting signal is dominated by spikes
(the `C_L` amplitude of 9.6 is non-physical by a factor of ten).  A second,
smaller defect is visible in
`test_immersed_body_is_driven_to_the_prescribed_velocity` (strict xfail): on a
non-square grid not every marker velocity is driven to the body velocity, i.e.
the diffuse body leaks.

Consequence: **no Turek–Hron FSI-2 amplitude/frequency and no trailing-edge
lock-in claim is made.**  The acceptance criteria
“`A_y` within 10 % / `f` within 5 %” and the VIV lock-in criterion are
**WITHHELD (not verified)**, and the coupled demonstration case diverged
(sub-iteration budget saturated, tip displacement → 1e33), which is consistent
with the body-load defect: a spurious load drives the structure.  Attempting
the production FSI-2 run (dx = 5 mm, t = 6 s) was abandoned after the fluid gate
failed, rather than reporting a number the solver cannot support.

## 5. Strong-coupling machinery (implemented, gate verified in principle)

`ImplicitCouplingDriver` re-runs the fluid step *and* the structural step from
the state at `tⁿ` inside every sub-iteration, so the fixed point it converges to
is the implicit coupling, not a staggered one.  It reports

* `disp_residual = ‖Δd‖_RMS / max(‖d‖_RMS, 1e−9)` against the gate (default
  1e−4), plus a relative force residual `‖F^{k+1}−F^k‖/‖F^{k+1}‖`;
* Aitken dynamic relaxation with the factor clipped to [0.02, 1];
* a closed ledger: `work` (fluid → structure, trapezoidal in the interface
  velocity), `storage` (Δstrain + Δkinetic), `dissipated` (Newmark Rayleigh
  dissipation), and `relative_residual = |work − storage − dissipated| / Σ|work|`.

Verified behaviours (tests): a quiescent start converges in ≤ 3 sub-iterations
with zero interface load; the sub-iteration count never exceeds the budget and
a non-converged step *reports* the saturated count instead of pretending to
converge; the ledger fields are finite and dissipation is non-negative; a rigid
body attaches through the same exchange.  **Not** verified: an actual
converged two-way FSI response in a shedding flow — the energy criterion
(`error < 5 %`) is therefore **WITHHELD** rather than claimed.

## 6. Known defects and limits

1. Immersed-body load reconstruction: pressure part spread uniformly, no
   surface-conforming traction; produces non-physical lift amplitude in the
   DFG case.  Root cause of the rung-2 failure.
2. Diffuse-body leakage on non-square grids (strict-xfail test).
3. Projection is fixed-coefficient, so the body constraint is only
   approximately enforced inside the body after each projection; a penalized
   (variable-coefficient) projection or a cut-cell scheme is the standard
   cure.
4. Structured beam is total-Lagrangian von Kármán: moderate rotations only, no
   shear deformation, no 3-D.
5. Wagner/Jones indicial model vs exact `C(k)` disagreement near `k ≈ 1`
   (§3); the p-k result is the qualified one.
6. All runs are single-process; `nx = 500` in 2-D is the practical ceiling on
   the shared development node under load.

## 7. Reproduce

```bash
PYTHONPATH=src pytest tests/test_fsi_beam2d.py tests/test_fsi_theodorsen.py \
    tests/test_fsi_flow2d.py tests/test_fsi_coupling.py -q
python scripts/fsi_ladder_run.py theodorsen --out artifacts/fsi_theodorsen.json
python scripts/fsi_ladder_run.py dfg --nx 500 --dt 1e-3 --t-end 12 \
    --out artifacts/fsi_dfg2d2.json
python scripts/fsi_ladder_figures.py
```

## 判定汇总（逐条回答判据）

| 判据 | 结果 | 数字 |
|---|---|---|
| Turek–Hron FSI-2 振幅 A_y 误差 <10% | **WITHHELD（未验证）** | 流体半程自身门槛未过：DFG 2D-2 平均 C_D=0.623 vs 3.22（误差 80.7%） |
| 振动频率 f 误差 <5% | **WITHHELD（未验证）** | 同上；耦合演示算例发散（子迭代饱和，tip→1e33 m），无有效耦合解 |
| Theodorsen 颤振速度 U_f 解析复现 <3% | **部分通过** | 闭式 C(k) 与 Bessel 独立实现差 1.1e-16，极限 C(0)=1/C(∞)=0.5 复现；p-k 得 U_f=1.1874 m/s, k_f=0.8654, ω_f=2.0553 rad/s；但时域 Wagner 路径边界落在 1.6U_f~2.5U_f（分歧 >60%）→ 3% 未达成（honest FAIL） |
| 子迭代残差 <1e-4 | **机制实现并验证** | 静水初值 1–3 次子迭代收敛；残差门被强制（未收敛时报告饱和次数而非伪收敛）；真实绕流耦合响应未收敛 |
| 能量守恒误差 <5% | **WITHHELD** | 能量账本（流体功/储存/耗散）已实现并逐式闭合，仅在静水算例验证；绕流算例无有效解 |

诚实声明：本节点未达成 FSI-2 振幅/频率与 VIV 锁定判据，也未达成 Theodorsen 跨方法 3% 一致；已定位的首要缺陷是浸入边界**物体载荷重构**（压力项在标记云上均匀铺开、非贴体 traction）导致 DFG 升力幅值虚高 10 倍。该结论不可被覆盖为通过。
