| claim / evidence | quote (verbatim, line range) | char offsets | sha256(quote)[:16] |
|---|---|---|---|
| cls-9478-02-01<br>ev-9478-02-01 | `   - ω^{k+1} = -ω^k · (r^{k-1})^T · (r^k - r^{k-1}) / \|\|r^k - r^{k-1}\|\|²` | [1316,1388) (L34-34) | `fea4b1c6f7fb2189` |
| cls-9478-02-01<br>ev-9478-02-02 | `\| Young's modulus E \| 1.3×10⁷ \| Pa \|` | [678,714) (L16-16) | `18640f5f0f565aa8` |
| cls-9478-02-01<br>ev-9478-02-03 | `\| Frequency f [Hz] \| 3.0163 \| 3.0000 \| 0.54% \| ✅ Yes \|` | [5203,5257) (L131-131) | `95970ec4224c76ce` |
| cls-9478-02-01<br>ev-9478-02-04 | `- Frequency change from Δt=0.002 to Δt=0.001: 0.01% ≤ 3% ✓` | [3643,3701) (L93-93) | `7be985724b3b5909` |
| cls-9478-02-02<br>ev-9478-02-05 | `The Turek-Hron FSI-2 benchmark (2006) is the gold standard for validating fluid-structure interaction solvers. It involves a 2D laminar channel flow (Re≈100) past a rigid cylinder with an elastic beam attached to its trailing edge. The beam undergoes vortex-induced vibration (VIV) due to periodic vortex shedding from the cylinder.` | [136,468) (L7-7) | `90423b28024ffb0c` |
| cls-9478-02-02<br>ev-9478-02-06 | `\| C1: Frequency \| error ≤ 5% \| 0.54% \| ✅ PASS \|` | [2552,2599) (L61-61) | `4d15600c5a02c78a` |
| cls-9478-02-02<br>ev-9478-02-07 | `We implement a partitioned Dirichlet-Neumann coupling with:` | [1090,1149) (L31-31) | `d919ef0d6f057cec` |
| cls-9478-02-03<br>ev-9478-02-08 | `\| Young's modulus E \| 1.3×10⁷ \| Pa \|` | [678,714) (L16-16) | `18640f5f0f565aa8` |
| cls-9478-02-03<br>ev-9478-02-09 | `\| Frequency f [Hz] \| 3.0163 \| 3.0000 \| 0.54% \| ✅ Yes \|` | [5203,5257) (L131-131) | `95970ec4224c76ce` |
| cls-9478-02-03<br>ev-9478-02-10 | `3. **Single-mode approximation**: Only the first bending mode is considered. Higher modes may be important for some FSI problems.` | [4528,4657) (L113-113) | `c9daf04509e36f3e` |
| cls-9478-02-04<br>ev-9478-02-11 | `### Reference Values (Turek & Hron 2006)` | [855,895) (L22-22) | `de42687ff53f6521` |
| cls-9478-02-04<br>ev-9478-02-12 | `Theodorsen (1935) analytical solution for 2-DOF typical section (plunge + pitch):` | [2145,2226) (L50-50) | `908d2a3ca5ad6e8e` |
| cls-9478-02-05<br>ev-9478-02-13 | `**C7: Interface Conservation**` | [3757,3787) (L96-96) | `ef45fcaca2ca8bf4` |
| cls-9478-02-05<br>ev-9478-02-14 | `- Code: <br>- Tests:  (38 tests, all pass)<br>- Full FSI suite: 162 tests, all pass<br>- Figures: ` | [5658,5747) (L140-143) | `cafd93ff81351817` |
| cls-9478-02-06<br>ev-9478-02-15 | `## 1. Case Introduction` | [87,110) (L4-4) | `ac5670ab730f4d4e` |
| cls-9478-02-06<br>ev-9478-02-16 | `## 6. Error Assessment` | [5077,5099) (L127-127) | `0a03a738c694e464` |
| cls-9478-02-06<br>ev-9478-02-17 | `## Audit Chain` | [5643,5657) (L139-139) | `a1324df931ce8a01` |
| cls-9478-02-07<br>ev-9478-02-18 | `1. : Tip displacement and CL/CD time history<br>2. : Energy conservation verification<br>3. : Flutter analysis (U_cr vs μ, growth rate vs U)<br>4. : Time-step convergence study` | [3934,4101) (L103-106) | `ec74d5d17c0a321d` |
| cls-9478-02-07<br>ev-9478-02-19 | `- Code: <br>- Tests:  (38 tests, all pass)<br>- Full FSI suite: 162 tests, all pass<br>- Figures: ` | [5658,5747) (L140-143) | `cafd93ff81351817` |
| cls-9478-02-08<br>ev-9478-02-20 | `\| C3: CL/CD \| error ≤ 10% \| tracked \| ✅ PASS \|` | [2649,2695) (L63-63) | `6c5f47e5baab415b` |
| cls-9478-02-08<br>ev-9478-02-21 | `\| C4: Flutter \| error ≤ 8% \| <2% \| ✅ PASS \|` | [2696,2739) (L64-64) | `0032429f7eae9547` |
| cls-9478-02-08<br>ev-9478-02-22 | `\| C8: Honest FAIL \| root cause \| all pass \| ✅ PASS \|` | [2888,2940) (L68-68) | `3cf8bfd22923aa3e` |
| cls-9478-02-09<br>ev-9478-02-23 | `- Computed: A = 53.07 mm<br>- Reference: A_ref = 50.0 mm<br>- Error: 6.13% ≤ 10% ✓` | [3080,3156) (L78-80) | `004ecdaf9b1fa496` |
| cls-9478-02-09<br>ev-9478-02-24 | `- Amplitude change: 6.07% (within 10% soft tolerance)` | [3702,3755) (L94-94) | `19dccf1a0248915a` |
| cls-9478-02-10<br>ev-9478-02-25 | `\| Flutter U_cr (μ=10) \| 6.325 \| 6.325 \| <2% \| ✅ Yes \|` | [5320,5373) (L133-133) | `8fa15f714b99ae2d` |
| cls-9478-02-10<br>ev-9478-02-26 | `- For μ=10: U_cr = 6.325 (reference), numerical match within 2%` | [3255,3318) (L84-84) | `7b502b51fcd79227` |
| cls-9478-02-11<br>ev-9478-02-27 | `- Tests:  (38 tests, all pass)<br>- Full FSI suite: 162 tests, all pass` | [5667,5735) (L141-142) | `07ae070b00bfa3a2` |
| cls-9478-02-12<br>ev-9478-02-28 | `# P153W2-N03: FSI Strong Coupling — Turek-Hron FSI-2 + Flutter + Energy Conservation` | [1,85) (L2-2) | `77df46ad49dfeeb1` |
| cls-9478-02-13<br>ev-9478-02-29 | `5. **Fluid Model**: Quasi-steady vortex shedding at Strouhal frequency St=0.16, with added mass and fluid damping effects.` | [2000,2122) (L47-47) | `5f9765a8396d9c1a` |
| cls-9478-02-13<br>ev-9478-02-30 | `- Full Navier-Stokes fluid solver (TensorLBM integration)` | [4926,4983) (L122-122) | `b8a9f443d67d56a8` |
