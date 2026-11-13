## 1 案例介绍

本工作包 = **KBM-RCI-F1-FACTORY 产线工序 04（independent-review）**，唯一对象是 `report_id=895`
（《W7-N10 冰盖对破冰船冲击的动态响应：弹性板-流体耦合 + 船首冲击时程 + 弯曲断裂判据 + 裂纹萌生位置》）及其上游工序产物 **wp-895-01（01-asset-registration，资产登记）**。

- 报告身份：`sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39`，`chars=9459`（与契约 `source_hash`/`chars` 逐字一致，本审独立重算）。
- 上游产物：`wp-895-01` 的 `asset_manifest.json`（6 图附件 + 7 项 artifact 引用，`claims=[]`，01 工序不抽取）。
- 物理域：冰区航行 / 冰盖-船首冲击（Kirchhoff 冰板 + 势流附连质量 + 压力-面积压碎律 + 弯曲断裂判据）。
- 本包不做：不改写上游产物、不读其它 report_id、不给任何断言盖上平台确认（该判定由平台门计算）。

产出判定：**verdict = `pass`，disposition = `approve-with-notes`** ——
登记工序四轴（身份/结构/证据/附件）独立重算全部通过；源报告内容存在 1 项 major 与 1 项 minor 口径缺陷，
作为**下游 wp-895-03 抽取的 carry-forward 约束**登记（对 01 工序非阻断）。

## 2 怎么做的（方法 / 流程 / 关键设置）

1. **取源原文（字节精确）**：`GET /api/v1/tensor/reports/895` → `markdown`；`runs/wp-895-04/fetch_source.py`
   落盘快照并重算 sha256。重算值 `sha256:31f6794efa547c7d…` 与契约一致，`len=9459`。
2. **读上游包但不读解释**：只取 `wp-895-01` 的 `result.json`（`asset_manifest.json` + 信封字段）做审查对象；
   生产者 `provenance.notes`/`manifest.notes` 属 GATE-RULES M5 应剥离字段，本次读到（见 §5 局限），
   但**全部 finding 均由本审自己的程序化重算推出**，不引用其结论。
3. **四轴程序化审查（`runs/wp-895-04/audit_wp895_01.py`，一条命令出 `audit.json`）**：
   - 身份轴：sha256 / 字符数 vs 契约；
   - 结构轴：上游信封过 `schemas/kf_result.v1.schema.json`（jsonschema 4.26.0）+ 5 个自封验证字段名全文扫描 + 零 claim 合法性；
   - 证据轴：7 条 artifact `locator` 在原文中的**字节精确子串**定位（记录码点偏移）；
   - 附件轴：附件名/图注与平台 `figures` 元数据逐字节比较；附件集合 vs 原文 §3.7 图清单集合差。
4. **物理轴独立复算（红队主力）**：不读生产者代码，自己写解析式复算报告的解析锚——
   ω²=(Dκ⁴+ρ_w g)/(ρ_i h+m_a(κ))、静力 Green 函数 w(r)=−P/(2πρ_w g ℓ_c²)·kei(r/ℓ_c) 与轴对称 Hankel 求积
   （含 1/2π 逆变换因子）、点载极限 Pℓ_c²/8D、`kei` 首零点、压力-面积律 p=C·A^−0.5 + 刚体封闭解
   F_peak=K^(2/3)((3/4)MV²)^(1/3)、冲量-动量、能量账闭合、环向裂纹半径比、最小相速度 c_min。
   **工况区分**：判据 (a)/(f) 用 h=1.0 m（原文标注 ℓ_c=16.92 m），冲撞/静力用 h=1.5 m（ℓ_c=22.934 m）——
   首轮复算曾因误用 h=1.5 m 得到 ω 偏 47%，属本审自己的口径错误，已修正并保留为踩坑记录（§5）。
5. **台账与独立性**：`scripts/ke_state_machine.py` 状态机折叠 `review_events.json`（in-review→approved，
   `OK_APPROVED`）；独立性判据 = canonical id + 8 位十六进制 token 集合不交（审核者 `agent/m15817` vs
   生产者 `agent/m15521` → `distinct-identity`）。
6. **工具链**：Python 3.11 + NumPy/SciPy（`special.kei`、`integrate.quad`）+ jsonschema + matplotlib（图内嵌）。

## 3 计算结果（数字表，程序化注入零手抄）

### 3.1 关键量独立复算 vs 报告声称值（25 项）

| 量 | 本审独立复算 | 报告声称值 | 相对误差 | <3% |
|---|---|---|---|---|
| D (弯曲刚度) | 2.78159e+09 | 2.7816e+09 | 0.00024% | 是 |
| ℓ_c | 22.9338 | 22.934 | 0.00106% | 是 |
| ℓ_c(h=1.0 m) | 16.9202 | 16.92 | 0.00147% | 是 |
| 2πℓ_c (λ_c, h=1.0) | 106.313 | 106.313 | 6e-05% | 是 |
| ω(k=2π/105.0256, h=1.0) | 1.06607 | 1.06607 | 7e-05% | 是 |
| c_p = ω/k | 17.8197 | 17.8197 | 0.00022% | 是 |
| c_g = dω/dk | 26.9686 | 26.9958 | 0.1008% | 是 |
| w(0) 点载极限 Pℓ_c²/8D | 0.103051 | 0.103051 | 0.00024% | 是 |
| w(0) 高斯斑 σ=4 m（独立 Hankel 求积） | 0.0984408 | 0.098441 | 0.00021% | 是 |
| 数值 w(0) 相对本审核参考值 | 0.0984408 | 0.098225 | 0.2197% | 是 |
| 零环半径 = kei 首零点·ℓ_c | 89.778 | 89.778 | 4e-05% | 是 |
| 刚体封闭解 F_peak | 4.80032e+06 | 4.80032e+06 | 5e-05% | 是 |
| 压碎律复算 F(δ=2.730 m) | 4.72955e+06 | 4.72934e+06 | 0.0045% | 是 |
| 峰值压碎面积 A | 3.30897 | 3.309 | 0.00076% | 是 |
| 峰值压碎压强 p | 1.42931 | 1.429 | 0.02174% | 是 |
| 断裂触发瞬间 F vs δ 口径一致 | 1.55207e+06 | 1.514e+06 | 2.515% | **否** |
| ∫F dt vs M(V0−V_end) | 1.1803e+07 | 1.1779e+07 | 0.2037% | 是 |
| 能量账闭合 压碎+板+阻尼 | 8.9951 | 8.9976 | 0.02779% | 是 |
| 冰盖弹性能占释放动能 | 4.11665 | 4.12 | 0.08123% | 是 |
| 流体动能占比 | 0.872455 | 0.87 | 0.2822% | 是 |
| 环向裂纹 r/ℓ_c | 0.820188 | 0.82 | 0.02297% | 是 |
| σ1/σ_f (触发时) | 1.30714 | 1.31 | 0.2181% | 是 |
| 断裂触发时刻 t_c（首个超阈采样点） | 0.117053 | 0.2 | 41.47% | **否** |
| 最小相速度 c_min | 16.5486 | 16.55 | 0.00819% | 是 |
| V/c_min (V=40 m/s) | 2.41712 | 2.42 | 0.1192% | 是 |

- 在 **23/25** 项上本审复算与报告一致，最大相对误差 **0.2822%**（<3%，其中 6 项 <0.01%）；
- **2** 项超 1%：断裂触发瞬间 F vs δ 口径一致, 断裂触发时刻 t_c（首个超阈采样点） —— 均为**口径/采样**问题，不是算错（见 3.2）。

### 3.2 审核发现（severity 排序）

| id | 严重度 | 影响范围 | 结论 |
|---|---|---|---|
| F1 | major | source_report | t_c=0.20 s 不是求解出的穿越时刻，而是**应力场抽样栅格**（每 20 步 = 0.2 s）上的首个超阈采样点：该采样点 σ₁ 已达阈值 1.31 倍。用报告自带的压碎律 F=p(A)·A 与 C=2.6 MPa·m^0.5（F∝δ^0.5）配等速推进，σ∝√t，反解得真穿越时刻≈0.117 s，相对 0.20 s 偏 41%。报告 §5 的不确定度预算只给接触斑敏感性 ±25%，未计入抽样栅格项。⇒ 若 03 工序把 0.20 s 原样提为知识断言，属超出原文支撑的精度声明。 |
| F2 | minor | source_report | 两列数据与报告自带压碎律不同口径：以 δ=0.294 m 代入 p=C·A^−0.5、A=2δtanα·h 得 1.5521 MN，与 1.514 MN 差 2.51%；而峰值行（δ=2.730 m → 4.7296 MN vs 4.72934 MN）只差 0.00%。说明触发行更可能报的是船体推进量 ξ 而非接触穿透 δ（δ=ξ−w≈0.280 m），原文未标注两列口径。 |
| F3 | minor | upstream_package | attachments 只登记平台 figures 元数据的 6 张 PNG，而原文 §3.7 图清单有 7 行（含 impact_animation.gif）。GIF 仅以 artifacts 条目出现（locator 可定位，覆盖在并集上完整），但只读 attachments 的下游工序会漏掉该图。建议 manifest 增加 `figure_rows_in_body` 计数或把 GIF 纳入 attachments。 |
| F4 | informational | upstream_package | 图注断言的数字与正文同量但口径不同：caption 写 "wavelength error 0.001%, group velocity error 0.00%"，正文 §3.1 为 0.0011%/0.0038%（两位小数舍入后 0.00%）。图注属平台 figures 元数据而非正文，登记时未标注"数字来自图注元数据"，下游若按图注取数会得到 0.00% 的失真精度。 |
| F5 | informational | metadata | 平台记录 title 与原文 H1 有 2 字差异（H1 多了"船首"），manifest 取记录 title （契约字段）合法，但按 H1 做 join/grep 的下游会失配。建议 01 工序显式登记 h1_vs_record_title_diff 供机器检测（当前只写在自由文本 notes 里）。 |

### 3.3 结构/证据/附件轴

| id | 轴 | 检查 | 结果 |
|---|---|---|---|
| C01 | identity | sha256(markdown) == 契约 source_hash | PASS |
| C02 | identity | len(markdown) == 契约 chars=9459 | PASS |
| C03 | structural | 上游 result.json 过 kf_result.v1 schema | PASS |
| C04 | structural | 上游产物无自封验证字段（S9） | PASS |
| C05 | structural | 零 claim 合法 + outputs 与契约 output 声明一致 | PASS |
| C06 | evidence | 7 条 artifact locator 在原文逐字可定位 | PASS |
| C07 | coverage | 附件集合 vs 原文 §3.7 图清单 | NOTE(F3) |
| C08 | fidelity | 附件名/图注逐字等于平台 figures 元数据 | PASS |
| C09 | physics | 判据 (a) 色散 ω / c_p / c_g 独立复算 | PASS |
| C10 | physics | 判据 (b) 静力锚：点载极限 + 高斯斑 Hankel 求积 + kei 首零点 | PASS |
| C11 | physics | 判据 (c) 压碎律 / 刚体封闭解 / 峰值面积压强 / 冲量-动量 | PASS（F2 见触发行口径） |
| C12 | physics | 判据 (e) 能量账闭合 | PASS |
| C13 | physics | 判据 (d) 环向裂纹半径 r/ℓ_c 与 σ₁/σ_f | PASS |
| C14 | physics | 断裂触发时刻的抽样栅格伪差 | FAIL_IN_SOURCE(F1) |
| C15 | physics | 触发瞬间 F↔δ 口径一致性 | FAIL_IN_SOURCE(F2) |
| C16 | honesty | 实验对标缺口是否被显式声明未达成 | PASS（WITHHELD 明示，未粉饰） |

## 4 结果图

图 `fig_wp895_04_review.png`（三面板，全部曲线由报告自己的参数表复算）：

- **A 判据 (a) 色散**：自写 ω(κ) 曲线 + 报告解析点/数值点（h=1.0 m）。复算 ω=1.066071 rad/s，
  与报告解析值 1.066070 相对误差 **7e-05%**。
- **B 复算误差全景**：25 项相对误差（log 轴）+ 1% 判定线；红柱=超 1%（F1 抽样栅格 41.5%、F2 口径 2.51%）。
- **C 断裂触发时刻伪差（F1）**：按报告自带压碎律 F∝δ^0.5 + 等速推进 σ∝√t，阈值 0.70 MPa 的**真穿越时刻≈0.117 s**，
  而报告写的 0.20 s 是 0.2 s 应力抽样栅格的首个超阈点（该点 σ₁/σ_f=1.31）。

## 5 注意点与局限

1. **产出链未被核实（NOT_RUN）**：报告声称"全部由 `artifacts/m1138/criteria.json` 程序化产出，零手抄"，
   但 `artifacts/m1138/` 宿主在 TensorPhysics 仓 `agent/m1138`（本仓不可达）。本审复算的是**正文参数表→结论**，
   属对结论的间接独立验证，**不等于**对产出链的核实；上游 manifest 的 `resolvable=referenced_only` 亦如此标注。
2. **未跑上游测试（NOT_RUN）**：`PYTHONPATH=src python -m pytest tests/test_ice_*.py -q`（36 用例）宿主仓不可达，
   "36 用例全绿"按 NOT_RUN 处理，不算通过。
3. **实验对标仍 WITHHELD**：判据 (c)"峰值载荷 vs 实验 ≤15%"无原始传感器/模型试验数据；报告已诚实声明未达成
   ——本审确认该诚实性（原文 §4 逐字引用见 §6 表），但不能替代缺口。
4. **本审自己的踩坑（如实记录）**：首轮把判据 (a) 误用 h=1.5 m 口径，得到 ω 偏 47%、Hankel 求积漏掉 1/2π 逆变换因子（结果偏 6.28 倍）；
   修正后 6 位一致。教训：**复算前必须先从原文确认每个判据对应的工况参数**，否则"红队误报"比漏报更糟。
5. **同构审核盲区**：审核者与生产者同为平台内 AI 会话；如果双方共享同一系统性建模假设错误（附连质量/势流准静态），
   本审无法发现。F1 之所以能被抓到，是因为它由报告**自己的**压碎律与**自己的**抽样设置互推出矛盾。
6. **上下文隔离部分受损**：上游 `result.json` 内含生产者 `notes`（M5 应剥离），我在读包时看到；F5（title 漂移）
   与该 notes 所述一致，属**事后印证而非来源**，已在 `review_report.json.independence_limitations` 显式登记。
7. **不影响结论的元数据差异**：平台记录 `title` 与原文 H1 差 2 字（H1 多"船首"）；附件 6 项 = figures 元数据，
   原文 §3.7 图清单 7 行（GIF 只在 artifacts 里）——均为非阻断（F3/F5）。

## 6 误差判定（逐项显式回答"是否 <3%"）

| 关键量 | 基准 | 相对误差 | 是否 <3% |
|---|---|---|---|
| 弯曲刚度 D | 报告参数表 2.7816e9 N·m | 0.00024% | **是** |
| 特征长度 ℓ_c（h=1.5 / h=1.0） | 22.934 / 16.92 m | 0.00106% / 0.00147% | **是** |
| 角频率 ω | 1.066070 rad/s | 7e-05% | **是** |
| 相速度 c_p | 17.8197 m/s | 0.00022% | **是** |
| 群速度 c_g | 26.9958 m/s | 0.1008% | **是** |
| 静力 w(0) 高斯斑 | 0.098441 m（本审独立 Hankel 求积 0.0984408） | 0.00021% | **是** |
| 点载极限 w(0) | Pℓ_c²/8D=0.103051 m | 0.00024% | **是** |
| kei 首零点/零环半径 | 89.778 m | 4e-05% | **是** |
| 刚体封闭解 F_peak | 4.80032 MN | 5e-05% | **是** |
| 峰值压碎面积/压强 | 3.309 m² / 1.429 MPa | 0.00076% / 0.02174% | **是** |
| 冲量-动量 | 11.803 MN·s | 0.20375% | **是** |
| 能量账闭合 | 8.9976 MJ | 0.02779% | **是** |
| 环向裂纹 r/ℓ_c | 0.82 | 0.02297% | **是** |
| 最小相速度 c_min / V/c_min | 16.55 m/s / 2.42 | 0.00819% / 0.11915% | **是** |
| **断裂触发时刻 t_c** | 报告 0.20 s | **41.47%**（抽样栅格，F1） | **否** |
| **触发瞬间 F vs δ** | 报告 1.514 MN | **2.5148%**（列口径，F2） | **否** |
| 峰值载荷 vs 实验 | — | **无基准** | **无法判定（WITHHELD）** |

**显式回答**：报告的 23 项解析锚全部 <3%（最大 0.2822%），其中 Hankel 求积与报告参考值 6 位一致；
**但**断裂时刻与触发行力-穿透两处不满足——不是算错，而是"抽样栅格 / 列口径"未标注，故 t_c 不得按单值精确引用。

## 7 自检（逐条对照 acceptance，honest）

| 验收项 | 结论 | 依据 |
|---|---|---|
| `valid_json` | ✓ | `review_report.json` / `review_events.json` / `kf_result.wp-895-04.json` 均由 `json.dump` 落盘后回读通过 |
| `schema_pass` | ✓ | 信封过 `schemas/kf_result.v1.schema.json`（jsonschema Draft202012Validator）；台账过 `schemas/review-event.schema.json` |
| `reviewer_independent` | ✓ | `ke_state_machine.is_independent` → `distinct-identity`（agent/m15817 ≠ agent/m15521） |
| `upstream_packages_completed` | ✓ | wp-895-01 结果存在、过 schema、零 claim 合法、7/7 locator 可定位 |
| `review_prompt_not_copied_from_producer` | ✓ | 本单指令为 04 审核契约，未复用 01 生产 prompt（无 01 prompt 文本进入本包） |
| `reviewer_context_excludes_producer_explanation` | **△ 部分** | 上游包内含生产者 `notes`（M5 应剥离字段），我读包时看到；结论不依赖之，已登记 limitation |
| `do_not_mark_claims_as_verified` | ✓ | 三个 JSON 产物内 0 处自封验证字段名（`build_review.py` 守卫断言，命中即 abort；本表为对齐验收项而逐字引用键名，仅出现在散文里） |
| `judge_semantic_fidelity` | ✓ | 语义面=manifest 字段 vs 原文/元数据逐字一致（C06 7/7 locator、C08 图注逐字节相同）；上游 claims=[] 故无 claim 级语义 |

### 复现（一键）

```bash
cd <worktree>
python3 runs/wp-895-04/fetch_source.py        # 取 report 895 原文 + 元数据（重算 sha256）
python3 runs/wp-895-04/audit_wp895_01.py      # 四轴 + 物理轴复算 → runs/wp-895-04/audit.json
python3 runs/wp-895-04/build_review.py        # 装配 review_report/review_events/kf_result（含三道守卫）
python3 runs/wp-895-04/make_figures.py        # 三面板审核图
python3 runs/wp-895-04/publish_report.py      # 本报告本身（--dry-run 只落盘）
```

## 附：结果 JSON（本报告唯一 json 块）

```json
{
 "package_id": "wp-895-04",
 "task_type": "04-independent-review",
 "report_id": "895",
 "provenance": {
  "source_field": "markdown",
  "source_hash": "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39",
  "source_uri": "tensor://reports/895",
  "producer": "agent/m15817",
  "emitted_at": "2026-11-12T03:10:00Z",
  "notes": "Independent red-team review of wp-895-01; all numbers recomputed programmatically (audit.json); no claim is marked as platform-attested."
 },
 "outputs": {
  "review_report.json": {
   "package_id": "wp-895-04",
   "task_type": "04-independent-review",
   "report_id": "895",
   "reviewed_package": "wp-895-01",
   "reviewed_task_type": "01-asset-registration",
   "reviewer": {
    "id": "agent/m15817",
    "reviewer_type": "agent",
    "role": "red-team-reviewer"
   },
   "reviewed_at": "2026-11-12T03:10:00Z",
   "policy_version": "ke-review-v0.1",
   "provenance": {
    "source_uri": "tensor://reports/895",
    "source_field": "markdown",
    "source_hash": "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39",
    "reviewed_artifact": {
     "path": "/root/tp-agent/work/m15521/runs/wp-895-01/result.json",
     "sha256": "sha256:c25fe7cd73f7e5ae557ad7b181886ca0fe0252e844f1ee48aee77ccb78343ad0",
     "package_id": "wp-895-01",
     "producer": "agent/m15521"
    },
    "audit_tool": "runs/wp-895-04/audit_wp895_01.py",
    "audit_output": "runs/wp-895-04/audit.json",
    "producer": "agent/m15817",
    "emitted_at": "2026-11-12T03:10:00Z"
   },
   "verdict": "pass",
   "disposition": "approve-with-notes",
   "verdict_scope": "判定对象是 wp-895-01（01-asset-registration）的登记忠实性：身份/结构/证据/附件四条轴全部重算通过，零 claim 合法。F1/F2 是**源报告内容**缺陷（对 wp-895-03 抽取构成 carry-forward 约束），F3–F5 是登记侧非阻断建议；均不改变\"该登记可进入下游\"的结论。",
   "decisions_not_made": [
    "未把任何断言标成平台已确认——该判定由平台门计算，本审核只给独立复算与判断。",
    "未修改上游产物、未改写报告原文、未触碰其它 report_id。"
   ],
   "checks_performed": [
    {
     "id": "C01",
     "axis": "identity",
     "check": "sha256(markdown) == 契约 source_hash",
     "method": "hashlib 独立重算原文快照",
     "result": "PASS",
     "detail": {
      "recomputed": "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39",
      "contract": "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39"
     }
    },
    {
     "id": "C02",
     "axis": "identity",
     "check": "len(markdown) == 契约 chars=9459",
     "method": "len()",
     "result": "PASS",
     "detail": {
      "chars": 9459
     }
    },
    {
     "id": "C03",
     "axis": "structural",
     "check": "上游 result.json 过 kf_result.v1 schema",
     "method": "jsonschema Draft202012Validator",
     "result": "PASS",
     "detail": {
      "schema_errors": []
     }
    },
    {
     "id": "C04",
     "axis": "structural",
     "check": "上游产物无自封验证字段（S9）",
     "method": "5 个字段名全文扫描",
     "result": "PASS",
     "detail": {
      "scanned_self_seal_fields": 5,
      "hit_total": 0,
      "hit_fields": []
     }
    },
    {
     "id": "C05",
     "axis": "structural",
     "check": "零 claim 合法 + outputs 与契约 output 声明一致",
     "method": "字段计数 + 契约比对",
     "result": "PASS",
     "detail": {
      "claims": 0,
      "manifest_claims": 0,
      "declared_outputs": [
       "asset_manifest.json"
      ],
      "zero_claim_note_present": true
     }
    },
    {
     "id": "C06",
     "axis": "evidence",
     "check": "7 条 artifact locator 在原文逐字可定位",
     "method": "字节精确子串搜索，记录 offset",
     "result": "PASS",
     "detail": {
      "n": 7,
      "offsets": {
       "criteria.json": 3376,
       "history_elastic.csv": 8964,
       "history_fracture.csv": 8964,
       "contact_patch_sensitivity.json": 7790,
       "impact_animation.gif": 6169,
       "src/tensorphysics/ice/": 60,
       "tests/test_ice_*.py": 8770
      }
     }
    },
    {
     "id": "C07",
     "axis": "coverage",
     "check": "附件集合 vs 原文 §3.7 图清单",
     "method": "正则抽 §3.7 表格行 + 集合差",
     "result": "NOTE(F3)",
     "detail": {
      "body_figure_rows": 7,
      "attachments": [
       "fig1_dispersion.png",
       "fig2_static_hetenyi.png",
       "fig3_impact_history.png",
       "fig4_fracture_fields.png",
       "fig5_energy_ledger.png",
       "fig6_supersonic_waves.png"
      ],
      "missing_from_attachments": [
       "impact_animation.gif"
      ],
      "not_covered_at_all": []
     }
    },
    {
     "id": "C08",
     "axis": "fidelity",
     "check": "附件名/图注逐字等于平台 figures 元数据",
     "method": "逐条字节比较",
     "result": "PASS",
     "detail": {
      "all_in_record": true,
      "captions_byte_identical": true
     }
    },
    {
     "id": "C09",
     "axis": "physics",
     "check": "判据 (a) 色散 ω / c_p / c_g 独立复算",
     "method": "自写 ω²=(Dκ⁴+ρ_w g)/(ρ_i h+ρ_w/(κ tanh κH))，h=1.0 m 工况（原文标注）",
     "result": "PASS",
     "detail": {
      "ω(k=2π/105.0256, h=1.0)": {
       "recomputed": 1.0660707972969505,
       "claimed": 1.06607,
       "rel_err_pct": 7e-05
      },
      "c_p = ω/k": {
       "recomputed": 17.819739456140542,
       "claimed": 17.8197,
       "rel_err_pct": 0.00022
      },
      "c_g = dω/dk": {
       "recomputed": 26.96858802166251,
       "claimed": 26.9958,
       "rel_err_pct": 0.1008
      }
     }
    },
    {
     "id": "C10",
     "axis": "physics",
     "check": "判据 (b) 静力锚：点载极限 + 高斯斑 Hankel 求积 + kei 首零点",
     "method": "自写 1/(2π)∫p̂(κ)κdκ/(Dκ⁴+ρ_w g)、Pℓ_c²/8D、scipy kei 零点扫描",
     "result": "PASS",
     "detail": {
      "w(0) 点载极限 Pℓ_c²/8D": {
       "recomputed": 0.10305124470425633,
       "claimed": 0.103051,
       "rel_err_pct": 0.00024
      },
      "w(0) 高斯斑 σ=4 m（独立 Hankel 求积）": {
       "recomputed": 0.09844079785569107,
       "claimed": 0.098441,
       "rel_err_pct": 0.00021
      },
      "零环半径 = kei 首零点·ℓ_c": {
       "recomputed": 89.77803301385076,
       "claimed": 89.778,
       "rel_err_pct": 4e-05
      }
     }
    },
    {
     "id": "C11",
     "axis": "physics",
     "check": "判据 (c) 压碎律 / 刚体封闭解 / 峰值面积压强 / 冲量-动量",
     "method": "p=C·A^−0.5、A=2δtanα·h、F_peak=K^{2/3}((3/4)MV²)^{1/3}",
     "result": "PASS（F2 见触发行口径）",
     "detail": {
      "刚体封闭解 F_peak": {
       "recomputed": 4800322.607211074,
       "claimed": 4800320.0,
       "rel_err_pct": 5e-05
      },
      "压碎律复算 F(δ=2.730 m)": {
       "recomputed": 4729552.7883329475,
       "claimed": 4729340.0,
       "rel_err_pct": 0.0045
      },
      "峰值压碎面积 A": {
       "recomputed": 3.3089747895899344,
       "claimed": 3.309,
       "rel_err_pct": 0.00076
      },
      "峰值压碎压强 p": {
       "recomputed": 1.4293106140343423,
       "claimed": 1.429,
       "rel_err_pct": 0.02174
      },
      "∫F dt vs M(V0−V_end)": {
       "recomputed": 11803000.0,
       "claimed": 11779000.0,
       "rel_err_pct": 0.20375
      }
     }
    },
    {
     "id": "C12",
     "axis": "physics",
     "check": "判据 (e) 能量账闭合",
     "method": "压碎功+板能+阻尼 vs 释放动能",
     "result": "PASS",
     "detail": {
      "residual_pct": 0.0278,
      "claimed_total_residual": "0.027%"
     }
    },
    {
     "id": "C13",
     "axis": "physics",
     "check": "判据 (d) 环向裂纹半径 r/ℓ_c 与 σ₁/σ_f",
     "method": "18.81/ℓ_c、0.915/0.70",
     "result": "PASS",
     "detail": {
      "环向裂纹 r/ℓ_c": 0.8201883602569193,
      "σ1/σ_f (触发时)": 1.3071428571428574
     }
    },
    {
     "id": "C14",
     "axis": "physics",
     "check": "断裂触发时刻的抽样栅格伪差",
     "method": "σ∝√t 反解阈值穿越时刻",
     "result": "FAIL_IN_SOURCE(F1)",
     "detail": {
      "claimed_s": 0.2,
      "implied_s": 0.1171,
      "rel_err_pct": 41.47
     }
    },
    {
     "id": "C15",
     "axis": "physics",
     "check": "触发瞬间 F↔δ 口径一致性",
     "method": "压碎律反解 δ 与报告两列对照",
     "result": "FAIL_IN_SOURCE(F2)",
     "detail": {
      "F_from_delta_MN": 1.5521,
      "rel_err_pct": 2.5148
     }
    },
    {
     "id": "C16",
     "axis": "honesty",
     "check": "实验对标缺口是否被显式声明未达成",
     "method": "原文 §4 逐字核对",
     "result": "PASS（WITHHELD 明示，未粉饰）",
     "detail": {
      "quote_offset": 6879
     }
    }
   ],
   "checks_not_run": [
    "未访问 TensorPhysics 仓 agent/m1138 分支的 artifacts/m1138（criteria.json、history_*.csv、6 PNG、GIF 字节）：报告\"全部由 criteria.json 程序化产出，零手抄\"这一**产出链声明本身**未经核实（NOT_RUN）；本轮复算用的是正文参数表，属对结论的间接独立验证，不等价于对产出链的核实。",
    "未运行 `PYTHONPATH=src python -m pytest tests/test_ice_*.py -q`（宿主仓不可达）：\"36 用例全绿\"为 NOT_RUN，不视为通过。",
    "判据 (c) 的实验对标（≤15%）仍为 WITHHELD：本审核同样无原始传感器/模型试验数据，不能替代该缺口。",
    "未做 03 抽取语义审：上游包 claims=[]（01 工序不抽取），无语义可审；故本次\"语义忠实性\"= manifest 字段与原文/元数据的逐字一致性，已由 C06/C08 覆盖。",
    "未复核报告的物理建模假设（势流准静态、Kirchhoff 小挠度、周期域）是否适用于具体船型：超出 01 工序范围，未评估（NOT_RUN）。"
   ],
   "independence_limitations": [
    "审核者与生产者同为平台内 AI 会话（agent/m15817 vs agent/m15521），非同机构/非同模型的外部独立审；独立性由身份 token 与 canonical id 判定（scripts/ke_state_machine.is_independent），非人工评审。",
    "审核上下文包含上游 result.json 的全部字段，其中 provenance.notes / asset_manifest.notes 属生产者自述（GATE-RULES M5 要求剥离的字段）。本报告的判定不依赖 notes：F1–F4 均由 audit_wp895_01.py 对原文/元数据的程序化重算独立推出；F5 与 notes 所述一致属于事后印证，不作为其来源。",
    "复算所依据的解析式由审核者独立实现（未阅读生产者代码），若双方共享同一系统性建模错误（如附连质量假设），则本审核无法发现——这是\"同构审核\"的固有盲区。"
   ],
   "findings": [
    {
     "id": "F1",
     "severity": "major",
     "blocking_for": [
      "wp-895-03"
     ],
     "non_blocking_for": [
      "wp-895-01"
     ],
     "scope": "source_report",
     "claim_ref": "§3.4 断裂触发时刻 t_c = 0.20 s",
     "finding": "t_c=0.20 s 不是求解出的穿越时刻，而是**应力场抽样栅格**（每 20 步 = 0.2 s）上的首个超阈采样点：该采样点 σ₁ 已达阈值 1.31 倍。用报告自带的压碎律 F=p(A)·A 与 C=2.6 MPa·m^0.5（F∝δ^0.5）配等速推进，σ∝√t，反解得真穿越时刻≈0.117 s，相对 0.20 s 偏 41%。报告 §5 的不确定度预算只给接触斑敏感性 ±25%，未计入抽样栅格项。⇒ 若 03 工序把 0.20 s 原样提为知识断言，属超出原文支撑的精度声明。",
     "evidence": [
      {
       "quote": "| 断裂触发时刻 t_c | **0.20 s** |",
       "offset": 4902,
       "source_field": "markdown",
       "source_hash": "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39"
      },
      {
       "quote": "每 20 步由谱导数恢复下表面主应力场，取首个超阈时刻/位置",
       "offset": 2921,
       "source_field": "markdown",
       "source_hash": "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39"
      },
      {
       "quote": "| 下表面峰值拉应力（触发时） | 0.915 MPa（σ_1/σ_f = 1.31） |",
       "offset": 4967,
       "source_field": "markdown",
       "source_hash": "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39"
      },
      {
       "quote": "**结论：积分量（力/能量/挠度）对接触斑不敏感，局部应力峰值与裂纹时刻敏感 ⇒ 裂纹时刻应视为 ±25% 量级的不确定量**",
       "offset": 7967,
       "source_field": "markdown",
       "source_hash": "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39"
      }
     ],
     "recompute": {
      "t_c_claimed_s": 0.2,
      "t_c_implied_by_threshold_s": 0.1171,
      "rel_err_pct": 41.47,
      "formula": "t_c≈t_s*(σ_f/σ₁)^2, σ∝√t（F∝δ^0.5, δ=V·t）"
     },
     "carry_forward_constraint": "03 抽取须写为「t_c ≈ 0.12–0.20 s（受 0.2 s 应力抽样栅格限制）」，不得给单值精确断言。"
    },
    {
     "id": "F2",
     "severity": "minor",
     "blocking_for": [],
     "scope": "source_report",
     "claim_ref": "§3.4 触发时接触力 1.514 MN / 穿透 0.294 m",
     "finding": "两列数据与报告自带压碎律不同口径：以 δ=0.294 m 代入 p=C·A^−0.5、A=2δtanα·h 得 1.5521 MN，与 1.514 MN 差 2.51%；而峰值行（δ=2.730 m → 4.7296 MN vs 4.72934 MN）只差 0.00%。说明触发行更可能报的是船体推进量 ξ 而非接触穿透 δ（δ=ξ−w≈0.280 m），原文未标注两列口径。",
     "evidence": [
      {
       "quote": "| 触发时接触力 / 穿透 | 1.514 MN / 0.294 m |",
       "offset": 4930,
       "source_field": "markdown",
       "source_hash": "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39"
      },
      {
       "quote": "| 耦合仿真峰值力（船体减速 + 冰盖让压） | **4.72934 MN**（比刚体解低 1.48%，物理上的柔性效应） |",
       "offset": 4569,
       "source_field": "markdown",
       "source_hash": "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39"
      },
      {
       "quote": "| 碎冰压力-面积律 | p = C·A^(−0.5) | C = 2.6 MPa·m^0.5，p ∈ [0.1, 12] MPa | 经验压力-面积包络（Sanderson 1988 / Masterson & Frederking 1998 形式的系数） |",
       "offset": 1298,
       "source_field": "markdown",
       "source_hash": "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39"
      },
      {
       "quote": "| 最大穿透量 δ_max | 2.730 m（冰面自身下沉 0.107 m） |",
       "offset": 4674,
       "source_field": "markdown",
       "source_hash": "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39"
      }
     ],
     "recompute": {
      "F_from_delta_0.294_MN": 1.5521,
      "rel_err_pct": 2.5148,
      "delta_implied_by_F_M": 0.2798
     },
     "carry_forward_constraint": "引用该行时须注口径（ξ 或 δ）；量级不受影响。"
    },
    {
     "id": "F3",
     "severity": "minor",
     "blocking_for": [],
     "scope": "upstream_package",
     "claim_ref": "asset_manifest.attachments（6 项）",
     "finding": "attachments 只登记平台 figures 元数据的 6 张 PNG，而原文 §3.7 图清单有 7 行（含 impact_animation.gif）。GIF 仅以 artifacts 条目出现（locator 可定位，覆盖在并集上完整），但只读 attachments 的下游工序会漏掉该图。建议 manifest 增加 `figure_rows_in_body` 计数或把 GIF 纳入 attachments。",
     "evidence": [
      {
       "quote": "| `impact_animation.gif` | 冲击过程挠度/应力场动画（23 帧） |",
       "offset": 6167,
       "source_field": "markdown",
       "source_hash": "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39"
      }
     ],
     "recompute": {
      "body_figure_rows": 7,
      "attachments": 6,
      "body_figs_not_in_attachments": [
       "impact_animation.gif"
      ],
      "body_figs_not_in_artifacts_either": []
     },
     "carry_forward_constraint": "无（并集覆盖完整）。"
    },
    {
     "id": "F4",
     "severity": "informational",
     "blocking_for": [],
     "scope": "upstream_package",
     "claim_ref": "fig1_dispersion.png caption（英文图注，来自平台元数据）",
     "finding": "图注断言的数字与正文同量但口径不同：caption 写 \"wavelength error 0.001%, group velocity error 0.00%\"，正文 §3.1 为 0.0011%/0.0038%（两位小数舍入后 0.00%）。图注属平台 figures 元数据而非正文，登记时未标注\"数字来自图注元数据\"，下游若按图注取数会得到 0.00% 的失真精度。",
     "evidence": [
      {
       "quote": "| 角频率 ω（k=0.05983 1/m） | 1.066070 rad/s | 1.066088 rad/s | **0.0017%** |",
       "offset": 3491,
       "source_field": "markdown",
       "source_hash": "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39"
      },
      {
       "quote": "| 群速度 c_g（波包能量质心） | 26.9958 m/s | 26.9948 m/s | **0.0038%** |",
       "offset": 3663,
       "source_field": "markdown",
       "source_hash": "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39",
       "note": "caption 侧数字来自平台 figures 元数据（本报告 audit.json attachment_fidelity 段证明二者逐字来自元数据）"
      }
     ],
     "recompute": {
      "caption_tokens": [
       "0.001",
       "0.00"
      ]
     },
     "carry_forward_constraint": "03 取数只取正文数字，不取图注。"
    },
    {
     "id": "F5",
     "severity": "informational",
     "blocking_for": [],
     "scope": "metadata",
     "claim_ref": "title（平台记录 / asset_manifest.title）",
     "finding": "平台记录 title 与原文 H1 有 2 字差异（H1 多了\"船首\"），manifest 取记录 title （契约字段）合法，但按 H1 做 join/grep 的下游会失配。建议 01 工序显式登记 h1_vs_record_title_diff 供机器检测（当前只写在自由文本 notes 里）。",
     "evidence": [
      {
       "quote": "# W7-N10 冰盖对破冰船冲击的动态响应：弹性板-流体耦合 + 船首冲击时程 + 弯曲断裂判据 + 裂纹萌生位置",
       "offset": 0,
       "source_field": "markdown",
       "source_hash": "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39"
      }
     ],
     "recompute": {
      "h1_equals_record_title": false
     },
     "carry_forward_constraint": "无（不改变任何数值结论）。"
    }
   ],
   "overstated_claims": [
    {
     "where": "§3.4 / §4 判据 (d)",
     "as_written": "断裂触发时刻 t_c = 0.20 s",
     "why_overstated": "0.20 s 是 0.2 s 抽样栅格的第一个超阈点（σ₁/σ_f=1.31），阈值穿越本身≈0.117 s（F1）"
    },
    {
     "where": "§5 注意点 4",
     "as_written": "裂纹时刻应视为 ±25% 量级的不确定量",
     "why_overstated": "该预算只含接触斑敏感性，未含 0.2 s 应力抽样栅格（F1 显示该项量级更大）"
    }
   ],
   "source_report_numbers_recomputed": {
    "n_quantities": 25,
    "n_within_1pct": 23,
    "max_rel_err_pct_among_within_1pct": 0.28217,
    "n_fail_1pct": 2,
    "note": "除 F1/F2 两项口径问题外，报告的解析锚（色散/静力 Green 函数/刚体封闭解/能量账/裂纹半径）均可被独立解析式复算到 <0.3%，说明数字非手抄；但\"产出链由 criteria.json 程序化生成\"未被核实（见 checks_not_run）。"
   },
   "repro_cmd": "cd <worktree> && python3 runs/wp-895-04/fetch_source.py && python3 runs/wp-895-04/audit_wp895_01.py && python3 runs/wp-895-04/build_review.py",
   "artifacts": [
    "runs/wp-895-04/audit_wp895_01.py",
    "runs/wp-895-04/audit.json",
    "runs/wp-895-04/fetch_source.py",
    "runs/wp-895-04/source_report_895.md",
    "work/wp-895-04/review_report.json",
    "work/wp-895-04/review_events.json",
    "work/wp-895-04/kf_result.wp-895-04.json"
   ],
   "independence": {
    "reviewer": "agent/m15817",
    "producer_ids": [
     "agent/m15521"
    ],
    "basis": "distinct-identity",
    "rule": "scripts/ke_state_machine.is_independent：canonical id + 8 位十六进制 token 集合不交",
    "ledger_state_after_fold": "approved",
    "ledger_outcome_codes": [
     "OK_APPROVED"
    ]
   }
  },
  "review_events.json": [
   {
    "id": "tkr:wp-895-01:review-wp895-04",
    "object_ref": "package:wp-895-01",
    "object_version": "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39",
    "decision": "approve",
    "reviewer": {
     "id": "agent/m15817",
     "reviewer_type": "agent",
     "role": "red-team-reviewer"
    },
    "reviewed_at": "2026-11-12T03:10:00Z",
    "policy_version": "ke-review-v0.1",
    "rationale": "身份/结构/证据/附件四轴独立重算通过；F1/F2 属源报告内容缺陷，作为下游抽取的 carry-forward 约束登记，不阻断登记工序。",
    "findings": [
     {
      "severity": "major",
      "finding": "t_c=0.20 s 不是求解出的穿越时刻，而是**应力场抽样栅格**（每 20 步 = 0.2 s）上的首个超阈采样点：该采样点 σ₁ 已达阈值 1.31 倍。用报告自带的压碎律 F=p(A)·A 与 C=2.6 MPa·m^0.5（F∝δ^0.5）配等速推进，σ∝√t，反解得真穿越时刻≈0.117 s，相对 0.20 s 偏 41%。报告 §5 的不确定度预算只给接触斑敏感性 ±25%，未计入抽样栅格项。⇒ 若 03 工序把 0.20 s 原样提为知识断言，属超出原文支撑的精度声明。"
     },
     {
      "severity": "minor",
      "finding": "两列数据与报告自带压碎律不同口径：以 δ=0.294 m 代入 p=C·A^−0.5、A=2δtanα·h 得 1.5521 MN，与 1.514 MN 差 2.51%；而峰值行（δ=2.730 m → 4.7296 MN vs 4.72934 MN）只差 0.00%。说明触发行更可能报的是船体推进量 ξ 而非接触穿透 δ（δ=ξ−w≈0.280 m），原文未标注两列口径。"
     },
     {
      "severity": "minor",
      "finding": "attachments 只登记平台 figures 元数据的 6 张 PNG，而原文 §3.7 图清单有 7 行（含 impact_animation.gif）。GIF 仅以 artifacts 条目出现（locator 可定位，覆盖在并集上完整），但只读 attachments 的下游工序会漏掉该图。建议 manifest 增加 `figure_rows_in_body` 计数或把 GIF 纳入 attachments。"
     },
     {
      "severity": "informational",
      "finding": "图注断言的数字与正文同量但口径不同：caption 写 \"wavelength error 0.001%, group velocity error 0.00%\"，正文 §3.1 为 0.0011%/0.0038%（两位小数舍入后 0.00%）。图注属平台 figures 元数据而非正文，登记时未标注\"数字来自图注元数据\"，下游若按图注取数会得到 0.00% 的失真精度。"
     },
     {
      "severity": "informational",
      "finding": "平台记录 title 与原文 H1 有 2 字差异（H1 多了\"船首\"），manifest 取记录 title （契约字段）合法，但按 H1 做 join/grep 的下游会失配。建议 01 工序显式登记 h1_vs_record_title_diff 供机器检测（当前只写在自由文本 notes 里）。"
     }
    ],
    "conditions": [
     "wp-895-03 抽取 t_c 时必须携带 F1 的 0.12–0.20 s 区间口径"
    ]
   }
  ]
 }
}
```
