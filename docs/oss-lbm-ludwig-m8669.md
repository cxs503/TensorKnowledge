# OSS 知识落地：Ludwig（自由能型二元流体 LBM）— A 线扩展

**任务** m8669 · **目标仓** `ludwig-cf/ludwig` @ `78d83c5` · **落库** `knowledge/oss-lbm/ludwig/` · **分支** `agent/m8669`

---

## ① 案例介绍（背景 / 对象 / 参数）

Ludwig 是爱丁堡大学 EPCC「复杂流体格子 Boltzmann」代码：以 LB 解 Navier–Stokes，再叠加一个（或多个）粗粒化序参量，用**自由能**图像描述「复杂」部分（混合物、胶体、凝胶、液晶）。本任务关心其中的**二元流体/多组分（MCMP）自由能支线**，因为它与 TensorLBM 的缺口线 `GAP-LBM-MCMP-POISEUILLE`（两相通道流验收）直接相邻。

| 项 | 值 | 来源 |
|---|---|---|
| 仓库 | `ludwig-cf/ludwig` (branch master) | provenance |
| commit | `78d83c5151ff1d4c4201a96b266a08e97047cae6` | `provenance/source-snapshot` |
| 抓取方式 | `https://codeload.github.com/ludwig-cf/ludwig/tar.gz/refs/heads/master` | provenance |
| 归档 SHA-256 | `6e216ef8f4c2f5654dc11b9c6b4f3570f97cc5e277193922b48cfaf0cd72e198` | 本地计算 |
| 实现语言 | gcc 12.3.0，`-O2 -g -Wall`，`D3Q27` 模型 | 构建记录 |
| 源码规模 | 388 个 `src/*.{c,h}` 源文件（`ls src/*.c src/*.h | wc -l`） | 目录清点 |

### 元数据纠错（如实报告）

任务书把该仓描述为 *Fortran*。实测**不是**：README 明写 `written in standard ANSI C`，且全树 `*.f90/*.F90/*.f` 命中数为 0（见 `artifacts/evidence-search-transcript.txt`）。任务书另提 *gauge* 表述，实测全树 `gauge`（忽略大小写，覆盖 src/docs/tests/README）**命中 0**，Ludwig 的自由能力写成应力散度与 `phi*grad(mu)` 两种形式。两项都已作为**可证伪前提**落成 claim（负结论同样入库，见 ③）。

## ② 怎么做的（方法 / 流程 / 工具链）

1. **取源**：任务书给的缓存目录 `/root/oss-cache/` 在本机不存在（如实 insufficient → 已换路径），改用 `codeload.github.com` 拉取 master 快照 tarball（`api.github.com`/`github.com` 在该环境被限流，最终 commit SHA 经 GitHub REST API 复核）。
2. **实读源码**：对自由能目录（`free_energy.h` / `symmetric.c` / `fe_force_method.h` / `phi_force_stress.c`）、组分输运目录（`cahn_hilliard.c` / `gradient_rt.c` / `gradient_3d_27pt_fluid.c`）、初始化与统计目录（`distribution_rt.c` / `stats_sigma.c`）、测试面（`tests/unit`、`tests/regression`）逐文件定位。
3. **逐字取证**：quote **不手抄**——由 `scripts/build_package.py` 按 `文件:起止行` 切片器直接从源码取 1–3 行，JSON 里保存的就是源码字节；`--check` 可随时把已提交 JSON 与源码树逐字节复核。
4. **构建+自测（验证面）**：`make serial && make`（gcc 12.3.0，D3Q27），再跑仓内 `tests/unit: make test` 与顶层 `make test`。
5. **定量物理验证**（本包自建，用仓库自带初始化）：`2d_shear_wave`（u₀=0.04, κ=2π）在周期单相盒中按精确解 u_x = u₀ sin(ky) e^{−νk²t} 衰减；用 Ludwig 自己输出的 `[maximum ]` 速度统计序列做 ln 幅值线性拟合，得有效衰减率，与输入 `viscosity 0.00625` 的 νk² 对比，L = 8/16/32 三点看收敛。
6. **落库**：17 claims / 21 evidence / 1 provenance / 6 GAP 锚；校验器 + pytest 全绿。

## ③ 计算结果

### 3.1 知识包规模与证据分级

| 指标 | 数值 |
|---|---|
| claims | 17（任务下限 8） |
| evidence | 22（code-location 20 条逐字引文 + code-search 2 条零命中检索） |
| GAP 锚 | 6 |
| epistemic_status 分布 | contested=4，established=13 |
| 自批 | 0（全部 evidence `assessment_status=unassessed`，无 review_events） |

### 3.2 Claims 清单表

| # | claim id | 类型 | 状态 | GAP 锚 | 证据（文件:行） | 结论摘要 |
|---|---|---|---|---|---|---|
| 1 | `ludwig-free-energy-catalog` | descriptive | established | `GAP-LBM-MCMP-POISEUILLE` | `src/free_energy.h:27-29`<br>`tests/regression/d3q27/serial-spin-n01.inp:44-46` | Ludwig exposes nine concrete free-energy models (symmetric phi^4, Brazovskii, surfactant, polar, liquid cry… |
| 2 | `ludwig-fe-vtable-contract` | descriptive | established | `GAP-LBM-MCMP-FORCE-GAUGE` | `src/free_energy.h:44-46` | Every Ludwig free energy implements a virtual table whose entries are typed callbacks for free-energy densi… |
| 3 | `ludwig-ch-fd-evolution` | descriptive | established | `GAP-LBM-MCMP-POISEUILLE` | `src/cahn_hilliard.c:8-8`<br>`src/cahn_hilliard.c:13-15` | The order-parameter sector of Ludwig evolves the Cahn-Hilliard equation d_t phi + div(u phi - M grad mu) = … |
| 4 | `ludwig-ch-flux-first-order-mu` | interpretive | contested | `GAP-LBM-MCMP-MU-STENCIL` | `src/cahn_hilliard.c:281-283` | The diffusive Cahn-Hilliard flux in Ludwig is assembled from neighbouring chemical potential values as flux… |
| 5 | `ludwig-symm-phi4-density` | descriptive | established | `GAP-LBM-MCMP-POISEUILLE` | `src/symmetric.c:7-8` | Ludwig's symmetric free energy implements F[phi] = (1/2) A phi^2 + (1/4) B phi^4 + (1/2) kappa (grad phi)^2… |
| 6 | `ludwig-symm-analytic-sigma` | descriptive | established | `GAP-LBM-MCMP-SIGMA-CALIB` | `src/symmetric.c:253-255`<br>`src/symmetric.c:271-271`<br>`src/stats_sigma.c:4-6` | Ludwig computes the interfacial tension of the symmetric free energy from the analytic phi^4 result sigma =… |
| 7 | `ludwig-symm-mu-discrete` | interpretive | contested | `GAP-LBM-MCMP-MU-STENCIL` | `src/symmetric.c:314-316`<br>`src/gradient_rt.c:49-51` | The chemical potential of the symmetric free energy is evaluated as mu = a*phi + b*phi^3 - kappa*delsq(phi)… |
| 8 | `ludwig-force-methods` | descriptive | established | `GAP-LBM-MCMP-FORCE-GAUGE` | `src/fe_force_method.h:22-24`<br>`src/phi_force_stress.c:4-5` | Ludwig provides five free-energy force formulations for the hydrodynamic sector: no force, stress divergenc… |
| 9 | `ludwig-no-gauge-formulation` | negative | established | `GAP-LBM-MCMP-FORCE-GAUGE` | grep `gauge` → 0 | The string 'gauge' does not occur anywhere in the Ludwig source, documentation, tests or README (case-insen… |
| 10 | `ludwig-no-scmp-pseudopotential` | negative | established | `GAP-LBM-MCMP-SCMP` | grep `scmp|pseudopotential|pseudo-potential|shan-chen` → 0 | Ludwig contains no Shan-Chen single-component-multiphase (SCMP) pseudo-potential implementation: a case-ins… |
| 11 | `ludwig-poiseuille-init` | descriptive | established | `GAP-LBM-MCMP-POISEUILLE` | `src/distribution_rt.c:552-554`<br>`src/distribution_rt.c:582-583` | Ludwig provides a run-time initial distribution '1d_poiseuille' that sets the analytic parabolic profile u_… |
| 12 | `ludwig-shear-wave-init` | descriptive | established | `GAP-LBM-MCMP-POISEUILLE` | `src/distribution_rt.c:490-492` | Ludwig provides a run-time initial distribution '2d_shear_wave' with fixed amplitude u0 = 0.04 and wavenumb… |
| 13 | `ludwig-gradient-stencil-selection` | descriptive | established | `GAP-LBM-MCMP-MU-STENCIL` | `src/gradient_rt.c:49-51`<br>`src/gradient_3d_27pt_fluid.c:5-6` | The discrete gradient/Laplacian used by the free-energy sector is selectable at run time through the input … |
| 14 | `ludwig-spinodal-smoke-test` | interpretive | contested | `GAP-LBM-MCMP-SPINODAL` | `tests/regression/d3q27/serial-spin-n01.inp:44-46` | The only regression test that exercises the binary-fluid free-energy path in the D3Q27 build is a 10-step, … |
| 15 | `ludwig-unit-test-ch-scope` | interpretive | contested | `GAP-LBM-MCMP-SPINODAL` | `tests/unit/test_ch.c:87-89`<br>`src/cahn_hilliard.c:8-8` | The Cahn-Hilliard unit test test_ch.c only checks object construction and the mobility bookkeeping (ch->inf… |
| 16 | `ludwig-sigma-droplet-calibration` | descriptive | established | `GAP-LBM-MCMP-SIGMA-CALIB` | `src/stats_sigma.c:4-6` | Ludwig calibrates the surface tension of the symmetric free energy from a simulated droplet in 2d or 3d (st… |
| 17 | `ludwig-ansi-c-not-fortran` | descriptive | established | `GAP-LBM-MCMP-POISEUILLE` | `README.md:18-19` | Ludwig's README states that the code 'is written in standard ANSI C' and uses MPI plus a TargetDP abstracti… |

### 3.3 逐字引文抽样（完整 21 条见 evidence.json）

- `src/cahn_hilliard.c:8-8`

```c
 *     d_t phi + div (u phi - M grad mu) = 0.
```

- `src/symmetric.c:253-255`

```c
  kappa = fe->param->kappa;

  *sigma = sqrt(-8.0*kappa*a*a*a/(9.0*b*b));
```

- `src/fe_force_method.h:22-24`

```c
  FE_FORCE_METHOD_NO_FORCE,                   /* Usually no hydrodynamics */
  FE_FORCE_METHOD_STRESS_DIVERGENCE,          /* Current default */
  FE_FORCE_METHOD_PHI_GRADMU,                 /* Simple phi grad mu version */
```

- `src/distribution_rt.c:582-583`

```c
    x = 1.0*(noffset[X] + ic) - lmin[X];
    u0[X] = umax[X]*x*(ltot[X] - x)*4.0/(ltot[X]*ltot[X]);
```

### 3.4 定量物理验证（Ludwig 自身求解器，非手算）

模型：D3Q27 BGK，周期单相盒，`free_energy none`，`viscosity 0.00625`（τ = 3ν + 1/2 = 0.51875），初始场 `2d_shear_wave`；精确解 u_x(y,t) = u₀ sin(2πy/L) exp(−ν(2π/L)²t)。

| L | k = 2π/L | 实测衰减率（拟合） | 精确 νk² | 相对误差 | 拟合 R² | 步数区间 |
|---|---|---|---|---|---|---|
| 8 | 0.7854 | 4.035431e-03 | 3.855314e-03 | **+4.672%** | 0.999986 | 10–200 |
| 16 | 0.3927 | 9.744154e-04 | 9.638286e-04 | **+1.098%** | 0.999995 | 20–400 |
| 32 | 0.1963 | 2.411568e-04 | 2.409571e-04 | **+0.083%** | 0.999981 | 20–400 |

原始日志：`artifacts/runs/shear_wave_L{8,16,32}.log`（含 input 文件），结果与图由 `scripts/verify_shear_wave.py` 程序化生成：`artifacts/shear_wave_verification.json`。

![shear wave decay](../knowledge/oss-lbm/ludwig/artifacts/shear_wave_decay.png)

### 3.5 仓内测试面

- `tests/unit: make test` → **98 PASS / 0 FAIL**（含 `test_ch`、`test_fe_symmetric`、`test_fe_force_method`、`test_lb_model`、`test_field_grad`、`test_hydro`）。
- 顶层 `make test`（对存档参考日志做回归 diff）→ **FAIL**：`d3q19-short/serial-actv-s01` 相对漂移 ~1e-7（存档参考日志陈旧，非本包引入）。如实记录，不做粉饰。

### 3.6 验证输出（本次运行的原始 stdout）

```text
$ python3 validate_ludwig.py
PASS: 17 claims, 22 evidence, 1 provenance, 6 gap anchors
  claims by gap anchor:
    GAP-LBM-MCMP-POISEUILLE: 6
    GAP-LBM-MCMP-SCMP: 1
    GAP-LBM-MCMP-FORCE-GAUGE: 3
    GAP-LBM-MCMP-MU-STENCIL: 3
    GAP-LBM-MCMP-SIGMA-CALIB: 2
    GAP-LBM-MCMP-SPINODAL: 2
  claims by epistemic_status: contested=4, established=13
  locator types: code-location, code-search
  epistemic discipline: all evidence unassessed, no review events

$ pytest tests/ -q
..........                                                               [100%]
=============================== warnings summary ===============================
../../../../../../../usr/lib/python3.11/site-packages/anyio/pytest_plugin.py:14
  /usr/lib/python3.11/site-packages/anyio/pytest_plugin.py:14: PytestRemovedIn10Warning: _pytest.python.CallSpec2 has been renamed to CallSpec.
  The CallSpec2 alias will be removed in pytest 10.
  Update imports to use CallSpec instead.
  See https://docs.pytest.org/en/stable/deprecations.html#callspec2-renamed
    from _pytest.python import CallSpec2

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
10 passed, 1 warning in 0.63s
```

## ④ 结果图

左：三套网格的幅值衰减（点）与精确解（线，对数纵轴）——三点几乎重合；右：实测衰减率相对误差 vs 3% 验收带。图中误差随 k 减小而收敛，说明粗网格的 4.67% 是**离散色散**（有限 k 效应），不是实现缺陷。图为 matplotlib 程序化生成（`scripts/verify_shear_wave.py`），数据来自上表，无手描曲线。

## ⑤ 注意点（坑 / 局限 / 适用范围）

1. **缓存目录缺失**：任务书指定的 `/root/oss-cache/` 不存在；未按「读不到=insufficient」草率收工，而是经网络取同一仓同一分支快照，并把抓取 URL、归档 SHA-256、commit 全部写进 provenance（可复核）。
2. **元数据两处失真**：Fortran（实为 ANSI C）、gauge 表述（全树 0 命中）——已落成可证伪结论，避免下游继续转抄。
3. **回归面偏弱**：D3Q27 两相回归只有一个 10 步、16³ 的 `smoke test`（其头部自称），且只做数值 diff，不断言任何物理量；`test_ch.c` 只测构造与 mobility。故本包对「两相精度」类结论保守给 `contested`，不因测试绿而升级。
4. **接口通量的阶数风险**：Cahn–Hilliard 通量用两点面梯度 `M(μ_{i+1} − μ_i)`，界面处 O(h) 误差是驱动型两相通道流寄生界面流的典型来源——这是 TensorLBM 做 POISEUILLE 基准时必须先量化的量。
5. **适用范围**：所有 claims 只对上述 commit 的 master 快照成立；`gauge`/SCMP 的负结论是**检索穷尽**意义下的「本仓没有」，不是语义层面的「不可能表述成该形式」。

## ⑥ 误差判定（逐项，显式回答是否 <3%）

| 关键量 | 基准 | 误差 | 是否 <3% | 说明 |
|---|---|---|---|---|
| 剪切波衰减率 νk²（L=8） | 精确解 e^{−νk²t} | +4.672% | **否（honest FAIL）** | 离散 BGK 有限 k 色散；随 k→0 收敛 |
| 剪切波衰减率 νk²（L=16） | 精确解 e^{−νk²t} | +1.098% | 是 | 收敛区，可接受 |
| 剪切波衰减率 νk²（L=32） | 精确解 e^{−νk²t} | +0.083% | 是 | 收敛区，可接受 |

结论：`verification.summary.passes = false`——最差 +4.67%（L=8）。收敛解（L≥16）在 3% 内，L=8 明确标注不达标并给出机理（有限 k 色散）+ 收敛证据（8→16→32 误差单调下降），不掩盖。知识类结论的「基准」是可复核的源码逐字引文与仓内测试面，而非数值算例；两相 σ/ξ 的数值误差本包**未**量测（仓库只有解析式与液滴标定工具，未运行液滴算例）——按纪律声明原因，不用含糊表述。

## ⑦ GAP 锚与 TensorLBM 服务面

| GAP 锚 | 归属 | 依据 claims | 下一步 |
|---|---|---|---|
| `GAP-LBM-MCMP-POISEUILLE` | mission brief (m8669) — anchored, not self-declared | 6 条 | 在 TensorLBM 实现体积力驱动的两相通道流，用 Ludwig 的 phi^4 参数族（a,b,kappa）给出 sigma/xi 解析值，并把界面处的表观滑移与解析 Poiseuille 剖面对比。 |
| `GAP-LBM-MCMP-SCMP` | self-declared by m8669 package (adjacent to GAP-LBM-MCMP-POISEUILLE; 待平台缺口账本收养) | 1 条 | 在 TensorLBM 内以解析 Maxwell 构造/共存密度曲线作为 SCMP 自验，勿引 Ludwig 为基线。 |
| `GAP-LBM-MCMP-FORCE-GAUGE` | self-declared by m8669 package (adjacent to GAP-LBM-MCMP-POISEUILLE; 待平台缺口账本收养) | 3 条 | TensorLBM 对 stress-divergence 与 phi·∇mu 两格式在同一算例上量化差异（目标 <3%）。 |
| `GAP-LBM-MCMP-MU-STENCIL` | self-declared by m8669 package (adjacent to GAP-LBM-MCMP-POISEUILLE; 待平台缺口账本收养) | 3 条 | 固定物理参数，扫 7pt/27pt/Tomita 模板，报告 sigma 与界面剖面误差随 h 的收敛阶。 |
| `GAP-LBM-MCMP-SIGMA-CALIB` | self-declared by m8669 package (adjacent to GAP-LBM-MCMP-POISEUILLE; 待平台缺口账本收养) | 2 条 | TensorLBM 用 phi^4 参数族做 sigma 解析-实测对照，判据 3%。 |
| `GAP-LBM-MCMP-SPINODAL` | self-declared by m8669 package (adjacent to GAP-LBM-MCMP-POISEUILLE; 待平台缺口账本收养) | 2 条 | TensorLBM 组分算子加『tanh 平衡剖面拟合』与『线性生长率 vs 理论』两个定量测试。 |

`GAP-LBM-MCMP-POISEUILLE` 由任务书给定并沿用；其余 5 个为**自拟相邻锚**，在 `gaps/gap-anchors.json` 里显式写 `declared_by`（归属声明），待 TensorLBM 缺口账本收养，不暗造编号。

## ⑧ 复现命令

```bash
cd knowledge/oss-lbm/ludwig
python3 validate_ludwig.py            # 包校验：PASS
pytest tests/ -q                      # 包测试：全绿
python3 scripts/verify_shear_wave.py \
    --log artifacts/runs/shear_wave_L8.log  --L 8  --nu 0.00625 \
    --combine-with artifacts/runs/shear_wave_L16.log:16:0.00625 \
                   artifacts/runs/shear_wave_L32.log:32:0.00625
LUDWIG_SRC=<checkout> LUDWIG_COMMIT=<sha> python3 scripts/build_package.py --check  # 引文逐字节复核
```

