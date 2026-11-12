## ① 案例介绍

**背景**：本仓是顶刊论文生产线。`papers/_sealed/ice-wave-mechanics-r2/` 是唯一一份走完成稿+评审全流程的稿件，
被异族确认评审（Report #961）判 **FAIL** 并封存，SEAL.md 列了 H1–H8 八类硬伤。复盘发现这八类**全部是
「文本 ↔ 证据基 ↔ 代码/图件」的一致性检查**，本可机检——人工评审逐轮抓、逐轮再犯，是典型**验证欠账**。

**对象（两份参照稿）**：
| 对象 | 角色 | 判据 |
|---|---|---|
| `papers/_sealed/ice-wave-mechanics-r2/manuscript.md`（246 行，6 图）+ 证据基 Report #823 | 负控（已知 FAIL） | 门禁必须复现机器可判的硬伤类 |
| `papers/data/gate-2026-11-03/control/`（本单新建） | 正控（须 PASS） | 0 HARD 失败，锁死误报 |

正控的物理场景：有限水深冰盖弯曲重力波色散式 $\omega^2=(gk+Dk^5/\rho_w)\tanh(kh)$，$D=Eh_i^3/(12(1-\nu^2))$；
参数 h=50.0 m、h_i=2.0 m、E=5.0×10⁹ Pa、ν=0.3、ρ_w=1025.0、ρ_i=917.0 kg/m³、g=9.81 m/s²、T=8.0 s。

## ② 怎么做的

1. 把 SEAL.md 的 H1–H8 逐条翻译成**可机器判定的判据**，形成 11 项 checks（HARD 拦 / SOFT 告警）：
   struct / figref / figdata / numtrace / formula / overclaim / statdof / implmethod / repro / placeholder / arith。
2. `papers/tools/manuscript_gate.py`：统一数字规范化（`1.16 × 10⁻¹³`、`1.16\times10^{-13}`、`1.16e-13` 同构；
   百分数 ↔ 分数等价；`§3.1`/`Section 4.2` 之类序数先遮蔽），每项 finding 带行号与原文片段。
   门禁**只读**被审稿（有 mtime 断言测试）。
3. 造**正控** `control/`：二分法参考实现 `solver.py`（tanh 边界条件）→ `evidence.json` → `make_figures.py`
   → `data/*.csv` + `figures/*.png` + `figures_metadata.json`（内嵌数值数组）→ `manuscript.md`（8 要素齐备、
   图在正文引用、可复现三件套齐、判据显式回答是否 <3%）。全链真算，无合成数组。
4. H1 的独立复算：同参数下把 tanh 换成 coth 重解波数，量化误式代价（`coth_tanh_impact.json`）。
5. 工具链：Python 3.11 + pytest 19 passed + matplotlib；报告数字由脚本从审计 JSON 直读注入（零手抄）。

## ③ 计算结果（程序化注入，源=审计 JSON）

| check | 严重度 | sealed r2（人工 FAIL） | control（须 PASS） | 摘要（sealed） |
|---|---|---|---|---|
| `struct` | HARD | WARN | PASS | 缺 0 个必需要素 |
| `figref` | HARD | FAIL | PASS | 6 图 / 0 路径引用 / 0 编号引用 |
| `figdata` | HARD | FAIL | PASS | 0/6 图有数据背书 |
| `numtrace` | HARD | FAIL | PASS | 检查 37 个定量 token，未溯源 1 个（证据基 237 值，tol=0.005） |
| `formula` | HARD | FAIL | PASS | 正文函数 token ['coth'] / 证据基 ['tan', 'tanh'] |
| `overclaim` | HARD | FAIL | SKIP | 证据基 WITHHELD 量名 5 个，升格命中 7 处 |
| `statdof` | HARD | FAIL | SKIP | R² 声明 2 处，缺自由度披露 2 处 |
| `implmethod` | HARD | PASS | PASS | 代码文件 1 个 / 声称方法 1 项 / 不符 0 项 |
| `repro` | HARD | FAIL | PASS | 三件套命中 0/3 |
| `placeholder` | SOFT | WARN | PASS | 占位符 2 处 |
| `arith` | HARD | FAIL | SKIP | 行级百分数复算 3 处 / JSON 三元组 0 处，不一致 3 处 |

**汇总**：sealed `verdict=FAIL`，HARD 失败 8/11；control `verdict=PASS`，HARD 失败 0/11（SKIP 3 项）。
sealed 复现的硬伤类与 SEAL.md 对照：H1→`formula`、H2→`overclaim`、H3→`figdata`（代理判据）、H4→`figref`、
H6→`repro`、H7→`statdof`、H8→`arith`（抓到 EnKF 声称 8.65% vs 同行两量复算 8.33%）；H5 在该树上不可机判，**如实不报**。

**H1 独立复算（tanh 正解 vs coth 误式）**：T=4s: 0.37%, T=6s: 1.31%, T=8s: 3.67%, T=10s: 9.60%, T=12s: 25.02%；T≥14s 时 coth 形式在 k∈(0,10] 1/m 内**无根**（二分法括号失败）——
错式不是"偏差大"，而是给出不可解的非物理分支。与 #961 记录的 74.19%/37.5% 不同（工况集不同），**不宣称一致**。

## ④ 结果图

见 figures：状态矩阵（11 checks × 2 稿）、数值溯源偏差分布（tol=5e-3 线）、coth/tanh 误式代价曲线。

## ⑤ 注意点（坑与局限）

- `numtrace` 是**存在性**判据（在证据基值域内匹配，容差 5e-3），不做"值属于该论断"的语义绑定；证据基很大时有偶然匹配风险（本例 237 值 vs 37 token，量级可控）。
- `figdata` 是合成数据的**代理**判据：有数据表背书仍可能图与数据不符，须配合人工看图。
- `overclaim` 靠量名锚定 + 希腊字母音译（α→alpha）；证据基若纯中文不写量名则退化为 SKIP。
- `arith` 只判"两量 + 一百分数"单行可复算；判据/门限类百分数（`<3%`、criterion）自动跳过，避免把门槛当结论。
- `repro` 只查三件套**存在**，不验证哈希真实性、不跑测试；`implmethod` 只查符号存在性，不验算法正确性。
- 踩坑：正则指数归一化必须先吞掉前导空白（否则 `1.16 e-13` 断号）；上标 ¹²³ 在 Latin-1（U+00B9/B2/B3）不在 U+2070 区，须单列；行级 WITHHELD 锚定会漏「量名在行内、数值在上一行」的表格行，改为量名锚定。

## ⑥ 误差判定（是否 <3%？）

| 关键量 | 基准 | 结果 | 是否 <3% |
|---|---|---|---|
| 正控归一化色散残差 | 判据 1e-12 | 7.09e-14 | **是**（低约 1.4 个数量级） |
| 正控 k vs 更紧容差解 | 独立更紧求解 | 2.48e-14 相对 | **是** |
| 门禁负控召回（vs SEAL.md 七类机器可判硬伤） | 人工评审 #961 | 7/7 复现 | **是**（H5 不可机判，已声明） |
| 门禁正控误报 | 应 0 HARD | 0/11 | **是** |
| coth 误式波数偏差（T=12 s） | tanh 正解 | 25.02% | **否**（>15% 不可接受，正是 H1 判 FAIL 的量化依据） |

honest 声明：`implmethod` 未能在封存树上复现 H5；`figdata` 只是合成数据代理判据；coth/tanh 的 74.19% 未复现（工况集不同）。
