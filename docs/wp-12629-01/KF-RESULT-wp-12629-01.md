# KF-RESULT wp-12629-01

- package_id: `wp-12629-01` ｜ task_type: `01-asset-registration` ｜ report_id: `12629`
- tags: `kf-wp:wp-12629-01`, `kf-task:01-asset-registration`, `lane:C`, `DP`, `dp_timedomain`
- 分层: DP | dp_timedomain | s ｜ 交付仓: TensorKnowledge ｜ 状态: draft（verification 由平台门计算，本单不自判 verified）

## ① 本工序做了什么

对 report_id=12629（《P333W2-N07 动力定位时域闭环与单点失效漂移：降额因子场与解析漂移锚》，scenario_key=`dp_timedomain`）做**资产登记**：核对报告 markdown 的字节哈希与契约 `source_hash`，把报告内可解析的结构化资产（章节、参数声明、模型组件、结果条目、图表目录、局限条款、误差表、交叉引用）逐条登记为带**字符级 locator** 的资产 34 条，并显式标出无法解析项。按契约 `objective.register_assets=true / classify_report_type=false`，本工序**不做**知识抽取：`claims` 为空数组（0 条），不产生任何被标为 verified 的结论。

登记结果：`resolved_in_source` 29 条、`referenced_unresolved` 4 条、`declared_absent` 1 条。

## ② 怎么做的（步骤/工具/关键设置）

1. **取源**：`scripts/kf_fetch_12629.py` 经平台 API `GET /tensor/reports/12629` 取 `markdown` 字段，写 `runs/wp-12629-01/report_12629.{md,json}`；重算 sha256 = `6cbf559cfaec918c26cf69c0081a2a3dcdceee4f7870797b35a27af8ca7e10eb`，与契约逐字比对（chars 1899 = 契约 1899，bytes_utf8 3545）。
2. **零手抄切片**：`scripts/kf_register_12629.py` 不写死任何物理数值，切片由**结构性选择器**驱动——行号由 `## N` 标题正则解析定位，行内按 `。`/`；`/`），`/`，` 分隔符切分，再用**字段名关键字**（如 `rel_dev`、`coupled_maneuvering`、`Newman`、`RAO`、`QP`、`PD`、`RK4`）择取片段。每条 quote 落盘前校验 `md.count(quote)==1`（唯一）。
3. **不可解析项的判据**：代码指针用 `grep -rIl --exclude-dir=.git coupled_maneuvering .`（排除本包自身产物）判定代码工件是否存在；断链交叉引用用「标题列表内是否存在对应小节」判定；缺失数据集用「报告自述 + 全文无该数据表」双条件判定。
4. **交叉检查**：平台 `record.summary` 的每个数值 token 是否逐字出现在 markdown（4 个 token，全部命中=True）；`record.title`/`scenario_key` 与契约逐字相等；`record.figures` 条数与 §4 图号计数（7 vs 7，一致=True）。
5. **独立复核**：`scripts/kf_verify_12629.py` **不复用**本地已取文件，进程内重新拉取报告、重算哈希、逐条把 `start_char:end_char` 重新切开与 `quote` 比对、并检查行号、唯一性、id 连续性、schema。
6. **图与报告**：`scripts/kf_report_12629.py` 由 manifest/verification JSON 程序化生成下图与本文（表格由 manifest 切出，不手写）。

决策与偏差：无（契约路径照做）。工具链 = Python 3 + urllib（平台 API）+ jsonschema 4.26 + matplotlib 3.10；未使用集群（本工序为文本/元数据级，单机秒级，不属重计算）。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `artifacts/wp-12629-01/asset_manifest.json` | 资产登记主产物：34 条资产 + `checks` + `integrity` + `boundaries`；`claims=[]` |
| `docs/wp-12629-01/asset_manifest.json` | 同上（逐字节镜像；push 门丢弃 `artifacts/**`，故留 durable 副本） |
| `runs/wp-12629-01/kf_result.wp-12629-01.json` / `docs/wp-12629-01/kf_result.wp-12629-01.json` | 结果信封（package_id/task_type/report_id/provenance/outputs），即本文末尾唯一围栏 json 代码块 |
| `docs/wp-12629-01/verification.json` | 独立复核报告：10 项检查，全通过=True |
| `docs/wp-12629-01/fig_locator_coverage.png` | 图：资产 locator 在 1899 字符画布上的覆盖图 + asset_class 分布 |
| `scripts/kf_fetch_12629.py`、`scripts/kf_register_12629.py`、`scripts/kf_verify_12629.py`、`scripts/kf_report_12629.py` | 一键复跑链（取源 → 登记 → 复核 → 出报告） |
| `schemas/asset_manifest.wp-12629-01.schema.json` | 包级 schema（使 schema_pass 可复算而非断言） |
| `runs/wp-12629-01/report_12629.md` / `.json` | 源报告本地副本（哈希校验用，非本次新取） |

## ④ 证据定位表（字段 → 原文引文片段，逐字可定位）

quote 为 markdown 的字符区间原文（`start_char`–`end_char`），`L` 为 1-based 行号；全表由 manifest 直接切出，`unique=是` 表示该片段在原文中恰好出现一次。本表为**截断显示**（46 字符），`|`/反引号按 GFM 规则反斜杠转义、不参与语义；逐字权威副本见 `asset_manifest.json` 的 `locator.quote`。

| asset | class | 行 | 原文片段（截断 46 字符） | resolution | unique |
|---|---|---|---|---|---|
| A01 | document | L1–29 | ## 1 案例介绍 DP-2 平台供应船（L=90 m, B=20 m, T=6.5 m,… | resolved_in_source | 是 |
| A02 | heading | L1–1 | ## 1 案例介绍 | resolved_in_source | 是 |
| A03 | case_declaration | L2–2 | DP-2 平台供应船（L=90 m, B=20 m, T=6.5 m, Cb=0.75, … | resolved_in_source | 是 |
| A04 | geometry_declaration | L2–2 | 几何自校验 rel_dev=0.0000 | resolved_in_source | 是 |
| A05 | actuator_set | L2–2 | 2×尾全回转 + 2×艏侧推（总推力 120 tf） | resolved_in_source | 是 |
| A06 | environment_baseline | L2–2 | 环境基准 Hs=4.0 m / Tp=9.0 s / 流速 0.60 m/s；12 个环境… | resolved_in_source | 是 |
| A07 | companion_case | L2–2 | 附算例：110 000 t 穿梭油船（漂移锚） | resolved_in_source | 是 |
| A08 | heading | L4–4 | ## 2 怎么做的 | resolved_in_source | 是 |
| A09 | governing_equation | L5–5 | \`(M+A)v̇+Dv = τ_cmd + τ_env(v,t)\`（低速水平面三自由度） | resolved_in_source | 是 |
| A10 | code_pointer | L5–5 | 风/流系数**复用平台单一源**（\`backend.api.coupled_maneuv… | referenced_unresolved | 是 |
| A11 | model_component | L5–5 | 二阶定常漂移系数标定得使**定常值严格等于 STAWAVE-1**，慢漂用 Newman(… | resolved_in_source | 是 |
| A12 | model_component | L5–5 | 一阶波频力为声明式简化 RAO | resolved_in_source | 是 |
| A13 | model_component | L5–5 | 推力分配=加权最小能量解+逐轮饱和冻结的迭代 QP | resolved_in_source | 是 |
| A14 | model_component | L5–5 | 控制器=PD+积分抗风偏置+一阶波滤+条件积分抗饱和 | resolved_in_source | 是 |
| A15 | model_component | L5–5 | RK4 推进 | resolved_in_source | 是 |
| A16 | experiment_setup | L5–5 | 失效在 t=120 s 注入。 | resolved_in_source | 是 |
| A17 | heading | L7–7 | ## 3 计算结果 | resolved_in_source | 是 |
| A18 | result_block | L8–8 | * **12 来向能力包线**：静力均值 49.0 m/s，时域均值 39.7 m/s，*… | resolved_in_source | 是 |
| A19 | result_block | L9–9 | * **(a) 静力一致性**：PD-only 末态距解析平衡点 0.0000 m = 0… | resolved_in_source | 是 |
| A20 | result_block | L10–10 | * **(b) 包含关系**：判定域 48 点、违例 0 → PASS；边界带（0.7–1… | resolved_in_source | 是 |
| A21 | result_block | L11–11 | * **(c) 解析漂移锚**：严格二次根 \`Du=k(V−u)²\` 误差最大 0.8… | resolved_in_source | 是 |
| A22 | cross_reference | L11–11 | （气动/船体阻尼比 r 见报告表） | referenced_unresolved | 是 |
| A23 | result_block | L12–12 | * **(d) 漂移线性区**：准稳态窗 R² 最小 0.9993，字面 30–300 s… | resolved_in_source | 是 |
| A24 | cross_reference | L12–12 | （物理时间常数 τ≈4009 s，30–300 s 窗整体落在加速段内，口径偏差已在报告 … | referenced_unresolved | 是 |
| A25 | result_block | L13–13 | * **(e) 分层可证伪**：包线内 16 点全收敛、包线外 5 点全发散，混淆矩阵 {… | resolved_in_source | 是 |
| A26 | result_block | L14–14 | * **单点失效漂移事件**（V_wind=16 m/s）：稳态漂移速度 0.010 m/… | resolved_in_source | 是 |
| A27 | heading | L16–16 | ## 4 图 | resolved_in_source | 是 |
| A28 | figure_index | L17–17 | 图1 能力包线极坐标；图2 降额因子场；图3 波谱与二阶漂移力（STAWAVE-1 一致性… | resolved_in_source | 是 |
| A29 | figure_asset_set | L17–17 | 图1 能力包线极坐标；图2 降额因子场；图3 波谱与二阶漂移力（STAWAVE-1 一致性… | referenced_unresolved | 是 |
| A30 | heading | L19–19 | ## 5 注意点（局限） | resolved_in_source | 是 |
| A31 | dataset | L20–20 | 1. 一阶波频力 RAO、附加质量/阻尼分项、Newman 单系数化均为**声明式**工程… | declared_absent | 是 |
| A32 | limitation_block | L20–20 | 1. 一阶波频力 RAO、附加质量/阻尼分项、Newman 单系数化均为**声明式**工程… | resolved_in_source | 是 |
| A33 | heading | L22–22 | ## 6 误差判定（逐项，显式回答是否 <3%） | resolved_in_source | 是 |
| A34 | table | L23–29 | \| 关键量 \| 基准 \| 误差 \| <3%? \| \|---\|---\|---… | resolved_in_source | 是 |

未解析项（4 条 referenced_unresolved + 1 条 declared_absent）及其判据：

| asset | 标签 | 判据（resolution_check.check） |
|---|---|---|
| A10 | 风/流系数来源（平台单一源，代码引用） | grep -rIl 'coupled_maneuvering' 全树：命中仅 knowledge/kb10k 的 claims/evidence JSON（数据记录），无同名 .… |
| A22 | 被引“报告表”（阻尼比 r 分布） | 全文检索 '报告表' 命中 1 处；§6 误差表内无含“阻尼比/r”的数据行 |
| A24 | 被引小节 §6.4（口径偏差声明） | 全文检索 '§6.4' 命中 1 处；章节标题列表中不存在 6.4 小节 |
| A29 | 平台 record.figures 图件（7 项） | record.figures 每项仅含 name/caption，无内联图片数据、base64 或可下载 URI |
| A31 | 试验/公开 RAO 数据集 | §5 第 1 条显式声明“非试验 RAO”；全文检索无试验 RAO 数据表/文件引用 |

图：`fig_locator_coverage.png` —— 横轴为 markdown 字符偏移，每条资产所占区间着色（绿=原文可解析、橙=引用未解析、紫=声明缺失）；右panel 为 asset_class 分布。

## ⑤ 注意点与局限

1. **本工序不产出知识、不做精度判定**。所有结果数值（例如能力包线均值、降额因子、误差百分比）只作为**结果条目的原文片段**被登记，未做复算、未做四则验证，也未标 verified——那是平台门与 task_type 03/04 的职责。
2. **图件本体不可解析**：`record.figures` 7 项只有 `name`/`caption`，无内联图片数据或下载 URI，故登记为 `referenced_unresolved`；另发现文件名序号与图号错位 3 处（fig5_wave_and_drift.png: fig5↔图3, fig3_drift_anchor.png: fig3↔图4, fig4_drift_linearity.png: fig4↔图5），这是元数据缺陷、非本单可修。
3. **两处断链交叉引用**（原文自指但目标不存在）：§3(d) 指向的「§6.4」在本 markdown 无对应小节；§3(c) 指向的「报告表」（阻尼比 r 分布）在本 markdown 无该表。二者均登记为 `referenced_unresolved`，**不臆造地址、不转向其它 report_id 取证**。
4. **代码指针不可解析**：§2 引用的 `backend.api.coupled_maneuvering` 在本工作树无 `.py` 实现；命中仅 `knowledge/kb10k/{claims,evidence}/part-006.json` 的代码指针数据记录。故 `referenced_unresolved`。
5. **`declared_absent` 1 条**是报告的**自述缺失**（「非试验 RAO」），不是本工序的发现；登记它以避免下游把声明式 RAO 误当试验数据。
6. locator 是**字符级**：若 platform 侧对 markdown 做任何空白/换行规范化，`start_char` 会漂移；`quote`+行号+`source_hash` 三元组才是稳健锚。
7. 缩窄范围声明：按边界只碰 report_id=12629，未读/写其它 report_id，未改写上游工作包产物。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 判据 | 结果 |
|---|---|---|
| `valid_json` | 机器可解析 | **PASS** |
| `schema_pass` | kf_result.v1 + 包内 asset_manifest schema | **PASS** |
| `source_locator_resolvable` | 34 条 locator 全部按新取副本重解析 | **PASS** |
| `source_hash_matches` | sha256 与契约逐字节一致 | **PASS** |
| `no_duplicate_ids` | asset_id 连续且唯一 | **PASS** |
| `all_claims_have_evidence_or_explicit_unresolved_status` | claims=0（契约允许）+ 4 条未解析资产逐条带 resolution_check | **PASS** |

- 补充自检：`source_hash_matches` 由 `scripts/kf_verify_12629.py` 进程内**重新拉取**报告独立重算（非读本地副本）；`all_claims_have_evidence_or_explicit_unresolved_status` 的落法为 claims=0（契约允许）且每条非 `resolved_in_source` 资产都写了机器可读的 `resolution_check`。
- honest 说明：本条结果**未**声称任何物理量正确、**未**接受/拒绝报告结论；verification 由平台门计算。若平台侧 `kf_result` schema 与本仓副本有差异，以平台门为准（本单 schema_pass 依 `schemas/kf_result.v1.schema.json` 与包级 schema 双验，见 `verification.json`）。

复跑（工作树根执行，一键）：

```bash
python3 scripts/kf_fetch_12629.py && python3 scripts/kf_register_12629.py \
  && python3 scripts/kf_report_12629.py && python3 scripts/kf_verify_12629.py
```

```json
{
  "package_id": "wp-12629-01",
  "task_type": "01-asset-registration",
  "report_id": "12629",
  "provenance": {
    "source_uri": "tensor://reports/12629",
    "source_field": "markdown",
    "source_hash": "sha256:6cbf559cfaec918c26cf69c0081a2a3dcdceee4f7870797b35a27af8ca7e10eb",
    "producer": "TensorKnowledge scripts/kf_register_12629.py (asset registration, no extraction)",
    "emitted_at": "2026-11-12T02:30:29+00:00",
    "notes": "source_hash recomputed from the exact UTF-8 bytes of the report markdown field; quotes are runtime slices, re-resolved by scripts/kf_verify_12629.py"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-12629-01",
      "task_type": "01-asset-registration",
      "report_id": "12629",
      "objective": {
        "register_assets": true,
        "classify_report_type": false
      },
      "source": {
        "uri": "tensor://reports/12629",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "6cbf559cfaec918c26cf69c0081a2a3dcdceee4f7870797b35a27af8ca7e10eb",
        "chars": 1899,
        "bytes_utf8": 3545,
        "contract_chars": 1899,
        "lines": 29,
        "title": "P333W2-N07 动力定位时域闭环与单点失效漂移：降额因子场与解析漂移锚",
        "scenario_key": "dp_timedomain",
        "platform_mission_id": 11102,
        "platform_status": "published",
        "platform_created_at": "2026-11-10T22:13:13.450712+00:00",
        "platform_tags": [
          "DP",
          "动力定位",
          "时域仿真",
          "失效漂移",
          "能力包线",
          "P333W2-N07"
        ],
        "platform_figures": [
          {
            "name": "fig1_capability_polar.png",
            "caption": "图1 12 来向能力包线：静力/时域完好/时域失效"
          },
          {
            "name": "fig2_derating_field.png",
            "caption": "图2 降额因子场（波频储备 + 单点失效）"
          },
          {
            "name": "fig5_wave_and_drift.png",
            "caption": "图3 JONSWAP 谱、波频激励与二阶漂移力（STAWAVE-1 一致性）"
          },
          {
            "name": "fig3_drift_anchor.png",
            "caption": "图4 失效后漂移速度 vs 解析预测"
          },
          {
            "name": "fig4_drift_linearity.png",
            "caption": "图5 漂移距离-时间线性区"
          },
          {
            "name": "fig6_layers.png",
            "caption": "图6 分层可证伪"
          },
          {
            "name": "fig7_station_keeping.png",
            "caption": "图7 站桩时域历程"
          }
        ]
      },
      "counts": {
        "assets": 34,
        "by_class": {
          "document": 1,
          "heading": 6,
          "case_declaration": 1,
          "geometry_declaration": 1,
          "actuator_set": 1,
          "environment_baseline": 1,
          "companion_case": 1,
          "governing_equation": 1,
          "code_pointer": 1,
          "model_component": 5,
          "experiment_setup": 1,
          "result_block": 7,
          "cross_reference": 2,
          "figure_index": 1,
          "figure_asset_set": 1,
          "dataset": 1,
          "limitation_block": 1,
          "table": 1
        },
        "by_resolution": {
          "resolved_in_source": 29,
          "referenced_unresolved": 4,
          "declared_absent": 1
        },
        "resolved_in_source": 29,
        "referenced_unresolved": 4,
        "declared_absent": 1,
        "claims": 0
      },
      "assets": [
        {
          "asset_class": "document",
          "label": "报告正文（markdown 全文）",
          "in_report_section": "全文",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256(markdown utf-8) 与契约 source_hash 重算比对",
            "result": "resolved"
          },
          "note": "整篇 markdown 即源资产；locator method=document 覆盖 0..1899 字符；hash=6cbf559cfaec918c26cf69c0081a2a3dcdceee4f7870797b35a27af8ca7e10eb",
          "asset_id": "A01",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 1899,
            "start_line": 1,
            "end_line": 29,
            "quote": "## 1 案例介绍\nDP-2 平台供应船（L=90 m, B=20 m, T=6.5 m, Cb=0.75, Δ=8994 t，几何自校验 rel_dev=0.0000），2×尾全回转 + 2×艏侧推（总推力 120 tf）。环境基准 Hs=4.0 m / Tp=9.0 s / 流速 0.60 m/s；12 个环境来向。附算例：110 000 t 穿梭油船（漂移锚）。\n\n## 2 怎么做的\n`(M+A)v̇+Dv = τ_cmd + τ_env(v,t)`（低速水平面三自由度）；风/流系数**复用平台单一源**（`backend.api.coupled_maneuvering` 的 Blendermann/OCIMF 系数），只把相对运动学改为二维矢量；二阶定常漂移系数标定得使**定常值严格等于 STAWAVE-1**，慢漂用 Newman(1974) `C_D|η|²`（同一 JONSWAP 实现，测试钉住均值一致）；一阶波频力为声明式简化 RAO；推力分配=加权最小能量解+逐轮饱和冻结的迭代 QP；控制器=PD+积分抗风偏置+一阶波滤+条件积分抗饱和；RK4 推进；失效在 t=120 s 注入。\n\n## 3 计算结果\n* **12 来向能力包线**：静力均值 49.0 m/s，时域均值 39.7 m/s，**降额因子 δ_wave 均值 25.3%**（8 个有界来向，min 6.2%，max 46.9%）；叠加最坏单机失效后 δ_fail 均值 46.6%，失效后时域能力均值 26.4 m/s。\n* **(a) 静力一致性**：PD-only 末态距解析平衡点 0.0000 m = 0.000%·L（判据 0.5%·L，PASS）；开积分后回到设定点残差 0.041%·L。\n* **(b) 包含关系**：判定域 48 点、违例 0 → PASS；边界带（0.7–1.0·V_static）12 点中 2 点不可保持（见 §5 局限）。\n* **(c) 解析漂移锚**：严格二次根 `Du=k(V−u)²` 误差最大 0.84%，线性等效阻尼式 `F_unbal/C_eq` 误差最大 5.39%（气动/船体阻尼比 r 见报告表）。\n* **(d) 漂移线性区**：准稳态窗 R² 最小 0.9993，字面 30–300 s 窗 R² 最小 0.9584（物理时间常数 τ≈4009 s，30–300 s 窗整体落在加速段内，口径偏差已在报告 §6.4 声明）。\n* **(e) 分层可证伪**：包线内 16 点全收敛、包线外 5 点全发散，混淆矩阵 {'TP_hold': 16, 'FP_inside_not_held': 0, 'TN_diverged': 5, 'FN_outside_held': 0}，准确率 100%。\n* **单点失效漂移事件**（V_wind=16 m/s）：稳态漂移速度 0.010 m/s@45°、0.011 m/s@90°、0.009 m/s@180°；600 s 漂移距离 1.9 m、0.4 m、0.4 m。\n\n## 4 图\n图1 能力包线极坐标；图2 降额因子场；图3 波谱与二阶漂移力（STAWAVE-1 一致性）；图4 失效漂移速度 vs 两个解析预测；图5 漂移距离-时间线性区；图6 分层可证伪；图7 站桩时域历程。\n\n## 5 注意点（局限）\n1. 一阶波频力 RAO、附加质量/阻尼分项、Newman 单系数化均为**声明式**工程模型（非试验 RAO），只作趋势与量级结论；2. 分配器为迭代饱和冻结，包线是 `ALLOCATOR_BOUND`（非数学上界）；3. 顺风失控工况存在真实转首失稳（broaching），1D 解析锚算例锁定转艏自由度后比对；4. 未建模横摇/纵摇耦合、推进器响应滞后、波浪漂移阻尼。\n\n## 6 误差判定（逐项，显式回答是否 <3%）\n| 关键量 | 基准 | 误差 | <3%? |\n|---|---|---|---|\n| 二阶定常漂移力 | STAWAVE-1 | <3%（测试钉住） | 是 |\n| 稳态漂移速度 | 严格二次根 | 0.84% | 是 |\n| 稳态漂移速度 | 线性等效阻尼式 | 5.39% | 否（公式适用边界 r≪1，已给出 r 分布） |\n| 静力平衡位置 | 解析 x*=x_sp+Kp⁻¹τ | 0.000%·L | 是 |\n| 一阶波频力 / 时域能力绝对值 / 失效漂移距离 | 无公开基准 | 不声明精度 | 无基准，只作趋势结论 |",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "heading",
          "label": "章节标题 §1 案例介绍",
          "in_report_section": "§1",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "行 1 全文唯一出现",
            "result": "resolved"
          },
          "note": "一级章节标题行，供下游按节定位",
          "asset_id": "A02",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 9,
            "start_line": 1,
            "end_line": 1,
            "quote": "## 1 案例介绍",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "case_declaration",
          "label": "船型与主尺度参数（L/B/T/Cb/Δ）",
          "in_report_section": "§1",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§1 首句按“。”切分后取含“供应船”的片段；片段在全文唯一",
            "result": "resolved"
          },
          "note": "数值仅登记不换算；几何一致性判据见下一条",
          "asset_id": "A03",
          "locator": {
            "method": "char_span",
            "start_char": 10,
            "end_char": 112,
            "start_line": 2,
            "end_line": 2,
            "quote": "DP-2 平台供应船（L=90 m, B=20 m, T=6.5 m, Cb=0.75, Δ=8994 t，几何自校验 rel_dev=0.0000），2×尾全回转 + 2×艏侧推（总推力 120 tf）",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "geometry_declaration",
          "label": "几何自校验结果（rel_dev）",
          "in_report_section": "§1",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "同片段按“，”切分后取含字段名 rel_dev 的子片段",
            "result": "resolved"
          },
          "note": "船型几何自校验条款原文；是否达标不在本工序判定",
          "asset_id": "A04",
          "locator": {
            "method": "char_span",
            "start_char": 64,
            "end_char": 84,
            "start_line": 2,
            "end_line": 2,
            "quote": "几何自校验 rel_dev=0.0000",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "actuator_set",
          "label": "推进器配置（2×尾全回转 + 2×艏侧推，总推力）",
          "in_report_section": "§1",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "同片段按“），”切分后取含“侧推”的子片段",
            "result": "resolved"
          },
          "note": "执行器配置声明；推力分配器实现体见 §2 分配器条目",
          "asset_id": "A05",
          "locator": {
            "method": "char_span",
            "start_char": 86,
            "end_char": 112,
            "start_line": 2,
            "end_line": 2,
            "quote": "2×尾全回转 + 2×艏侧推（总推力 120 tf）",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "environment_baseline",
          "label": "环境基准参数（Hs/Tp/流速/来向数）",
          "in_report_section": "§1",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§1 按“。”切分后取含“环境基准”的片段",
            "result": "resolved"
          },
          "note": "环境工况声明；分布实现（JONSWAP）见 §2",
          "asset_id": "A06",
          "locator": {
            "method": "char_span",
            "start_char": 113,
            "end_char": 160,
            "start_line": 2,
            "end_line": 2,
            "quote": "环境基准 Hs=4.0 m / Tp=9.0 s / 流速 0.60 m/s；12 个环境来向",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "companion_case",
          "label": "附算例：穿梭油船漂移锚",
          "in_report_section": "§1",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§1 按“。”切分后取含“附算例”的片段",
            "result": "resolved"
          },
          "note": "附加算例声明，与主算例分属不同船型",
          "asset_id": "A07",
          "locator": {
            "method": "char_span",
            "start_char": 161,
            "end_char": 184,
            "start_line": 2,
            "end_line": 2,
            "quote": "附算例：110 000 t 穿梭油船（漂移锚）",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "heading",
          "label": "章节标题 §2 怎么做的",
          "in_report_section": "§2",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "行 4 全文唯一出现",
            "result": "resolved"
          },
          "note": "方法章节标题行",
          "asset_id": "A08",
          "locator": {
            "method": "char_span",
            "start_char": 187,
            "end_char": 196,
            "start_line": 4,
            "end_line": 4,
            "quote": "## 2 怎么做的",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "governing_equation",
          "label": "运动方程（低速水平面三自由度）",
          "in_report_section": "§2",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§2 按“；”切分后取含状态导数符号 v̇ 的片段",
            "result": "resolved"
          },
          "note": "支配方程原文；自由度声明随片段一并登记",
          "asset_id": "A09",
          "locator": {
            "method": "char_span",
            "start_char": 197,
            "end_char": 241,
            "start_line": 5,
            "end_line": 5,
            "quote": "`(M+A)v̇+Dv = τ_cmd + τ_env(v,t)`（低速水平面三自由度）",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "code_pointer",
          "label": "风/流系数来源（平台单一源，代码引用）",
          "in_report_section": "§2",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "grep -rIl 'coupled_maneuvering' 全树：命中仅 knowledge/kb10k 的 claims/evidence JSON（数据记录），无同名 .py 代码文件 → 代码工件本体不在本工作树",
            "result": "unresolved"
          },
          "note": "报告指向平台仓模块 backend.api.coupled_maneuvering；本仓只有 kb10k 代码指针记录提及该文件，代码本体不可解析，故登记为未解析、不臆造地址（kb10k 指针记录见 checks.code_pointer_target_in_worktree）",
          "asset_id": "A10",
          "locator": {
            "method": "char_span",
            "start_char": 242,
            "end_char": 330,
            "start_line": 5,
            "end_line": 5,
            "quote": "风/流系数**复用平台单一源**（`backend.api.coupled_maneuvering` 的 Blendermann/OCIMF 系数），只把相对运动学改为二维矢量",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "model_component",
          "label": "二阶定常/慢漂力模型（含标定口径）",
          "in_report_section": "§2",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§2 按“；”切分后取含 Newman 的片段",
            "result": "resolved"
          },
          "note": "标定目标与慢漂模型原文；一致性由报告自述“测试钉住”，测试工件未在本仓",
          "asset_id": "A11",
          "locator": {
            "method": "char_span",
            "start_char": 331,
            "end_char": 415,
            "start_line": 5,
            "end_line": 5,
            "quote": "二阶定常漂移系数标定得使**定常值严格等于 STAWAVE-1**，慢漂用 Newman(1974) `C_D|η|²`（同一 JONSWAP 实现，测试钉住均值一致）",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "model_component",
          "label": "一阶波频力（声明式简化 RAO）",
          "in_report_section": "§2",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§2 按“；”切分后取含 RAO 的片段",
            "result": "resolved"
          },
          "note": "声明式简化模型，非试验 RAO：精度结论只到趋势/量级（与 §5 第 1 条一致）",
          "asset_id": "A12",
          "locator": {
            "method": "char_span",
            "start_char": 416,
            "end_char": 431,
            "start_line": 5,
            "end_line": 5,
            "quote": "一阶波频力为声明式简化 RAO",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "model_component",
          "label": "推力分配（迭代 QP + 饱和冻结）",
          "in_report_section": "§2",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§2 按“；”切分后取含 QP 的片段",
            "result": "resolved"
          },
          "note": "分配器实现方式原文；其边界性质见 §5 第 2 条",
          "asset_id": "A13",
          "locator": {
            "method": "char_span",
            "start_char": 432,
            "end_char": 457,
            "start_line": 5,
            "end_line": 5,
            "quote": "推力分配=加权最小能量解+逐轮饱和冻结的迭代 QP",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "model_component",
          "label": "控制器（PD + 积分 + 波滤 + 抗饱和）",
          "in_report_section": "§2",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§2 按“；”切分后取含 PD 的片段",
            "result": "resolved"
          },
          "note": "控制器结构与波滤环节原文",
          "asset_id": "A14",
          "locator": {
            "method": "char_span",
            "start_char": 458,
            "end_char": 484,
            "start_line": 5,
            "end_line": 5,
            "quote": "控制器=PD+积分抗风偏置+一阶波滤+条件积分抗饱和",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "model_component",
          "label": "时间推进（RK4）",
          "in_report_section": "§2",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§2 按“；”切分后取含 RK4 的片段",
            "result": "resolved"
          },
          "note": "积分格式原文；步长未在该片段声明",
          "asset_id": "A15",
          "locator": {
            "method": "char_span",
            "start_char": 485,
            "end_char": 491,
            "start_line": 5,
            "end_line": 5,
            "quote": "RK4 推进",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "experiment_setup",
          "label": "单点失效注入时刻",
          "in_report_section": "§2",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§2 按“；”切分后取含“注入”的片段",
            "result": "resolved"
          },
          "note": "失效工况注入时刻原文",
          "asset_id": "A16",
          "locator": {
            "method": "char_span",
            "start_char": 492,
            "end_char": 507,
            "start_line": 5,
            "end_line": 5,
            "quote": "失效在 t=120 s 注入。",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "heading",
          "label": "章节标题 §3 计算结果",
          "in_report_section": "§3",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "行 7 全文唯一出现",
            "result": "resolved"
          },
          "note": "结果章节标题行",
          "asset_id": "A17",
          "locator": {
            "method": "char_span",
            "start_char": 509,
            "end_char": 518,
            "start_line": 7,
            "end_line": 7,
            "quote": "## 3 计算结果",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "result_block",
          "label": "能力包线条目（静力/时域均值、降额因子、失效叠加）",
          "in_report_section": "§3",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§3 第 8 行整行（项目符号行）在全文唯一",
            "result": "resolved"
          },
          "note": "整行登记：内含多个数值，仅登记不改写、不判定精度",
          "asset_id": "A18",
          "locator": {
            "method": "char_span",
            "start_char": 519,
            "end_char": 661,
            "start_line": 8,
            "end_line": 8,
            "quote": "* **12 来向能力包线**：静力均值 49.0 m/s，时域均值 39.7 m/s，**降额因子 δ_wave 均值 25.3%**（8 个有界来向，min 6.2%，max 46.9%）；叠加最坏单机失效后 δ_fail 均值 46.6%，失效后时域能力均值 26.4 m/s。",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "result_block",
          "label": "结果 (a) 静力一致性",
          "in_report_section": "§3",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§3 第 9 行整行（项目符号行）在全文唯一",
            "result": "resolved"
          },
          "note": "整行登记：内含多个数值，仅登记不改写、不判定精度",
          "asset_id": "A19",
          "locator": {
            "method": "char_span",
            "start_char": 662,
            "end_char": 752,
            "start_line": 9,
            "end_line": 9,
            "quote": "* **(a) 静力一致性**：PD-only 末态距解析平衡点 0.0000 m = 0.000%·L（判据 0.5%·L，PASS）；开积分后回到设定点残差 0.041%·L。",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "result_block",
          "label": "结果 (b) 包含关系",
          "in_report_section": "§3",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§3 第 10 行整行（项目符号行）在全文唯一",
            "result": "resolved"
          },
          "note": "整行登记：内含多个数值，仅登记不改写、不判定精度",
          "asset_id": "A20",
          "locator": {
            "method": "char_span",
            "start_char": 753,
            "end_char": 833,
            "start_line": 10,
            "end_line": 10,
            "quote": "* **(b) 包含关系**：判定域 48 点、违例 0 → PASS；边界带（0.7–1.0·V_static）12 点中 2 点不可保持（见 §5 局限）。",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "result_block",
          "label": "结果 (c) 解析漂移锚",
          "in_report_section": "§3",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§3 第 11 行整行（项目符号行）在全文唯一",
            "result": "resolved"
          },
          "note": "整行登记：内含多个数值，仅登记不改写、不判定精度",
          "asset_id": "A21",
          "locator": {
            "method": "char_span",
            "start_char": 834,
            "end_char": 931,
            "start_line": 11,
            "end_line": 11,
            "quote": "* **(c) 解析漂移锚**：严格二次根 `Du=k(V−u)²` 误差最大 0.84%，线性等效阻尼式 `F_unbal/C_eq` 误差最大 5.39%（气动/船体阻尼比 r 见报告表）。",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "cross_reference",
          "label": "被引“报告表”（阻尼比 r 分布）",
          "in_report_section": "§3 (c)",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "全文检索 '报告表' 命中 1 处；§6 误差表内无含“阻尼比/r”的数据行",
            "result": "unresolved"
          },
          "note": "所指的 r 分布表在本 markdown 中不存在：引用不可解析，未臆造转向其它来源",
          "asset_id": "A22",
          "locator": {
            "method": "char_span",
            "start_char": 913,
            "end_char": 930,
            "start_line": 11,
            "end_line": 11,
            "quote": "（气动/船体阻尼比 r 见报告表）",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "result_block",
          "label": "结果 (d) 漂移线性区",
          "in_report_section": "§3",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§3 第 12 行整行（项目符号行）在全文唯一",
            "result": "resolved"
          },
          "note": "整行登记：内含多个数值，仅登记不改写、不判定精度",
          "asset_id": "A23",
          "locator": {
            "method": "char_span",
            "start_char": 932,
            "end_char": 1046,
            "start_line": 12,
            "end_line": 12,
            "quote": "* **(d) 漂移线性区**：准稳态窗 R² 最小 0.9993，字面 30–300 s 窗 R² 最小 0.9584（物理时间常数 τ≈4009 s，30–300 s 窗整体落在加速段内，口径偏差已在报告 §6.4 声明）。",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "cross_reference",
          "label": "被引小节 §6.4（口径偏差声明）",
          "in_report_section": "§3 (d)",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "全文检索 '§6.4' 命中 1 处；章节标题列表中不存在 6.4 小节",
            "result": "unresolved"
          },
          "note": "指向的小节在本 markdown 中不存在：登记为断链引用，供 report 修订方补齐或改指",
          "asset_id": "A24",
          "locator": {
            "method": "char_span",
            "start_char": 992,
            "end_char": 1045,
            "start_line": 12,
            "end_line": 12,
            "quote": "（物理时间常数 τ≈4009 s，30–300 s 窗整体落在加速段内，口径偏差已在报告 §6.4 声明）",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "result_block",
          "label": "结果 (e) 分层可证伪混淆矩阵",
          "in_report_section": "§3",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§3 第 13 行整行（项目符号行）在全文唯一",
            "result": "resolved"
          },
          "note": "整行登记：内含多个数值，仅登记不改写、不判定精度",
          "asset_id": "A25",
          "locator": {
            "method": "char_span",
            "start_char": 1047,
            "end_char": 1181,
            "start_line": 13,
            "end_line": 13,
            "quote": "* **(e) 分层可证伪**：包线内 16 点全收敛、包线外 5 点全发散，混淆矩阵 {'TP_hold': 16, 'FP_inside_not_held': 0, 'TN_diverged': 5, 'FN_outside_held': 0}，准确率 100%。",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "result_block",
          "label": "单点失效漂移事件条目（稳态漂移速度与漂移距离）",
          "in_report_section": "§3",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§3 第 14 行整行（项目符号行）在全文唯一",
            "result": "resolved"
          },
          "note": "整行登记：内含多个数值，仅登记不改写、不判定精度",
          "asset_id": "A26",
          "locator": {
            "method": "char_span",
            "start_char": 1182,
            "end_char": 1291,
            "start_line": 14,
            "end_line": 14,
            "quote": "* **单点失效漂移事件**（V_wind=16 m/s）：稳态漂移速度 0.010 m/s@45°、0.011 m/s@90°、0.009 m/s@180°；600 s 漂移距离 1.9 m、0.4 m、0.4 m。",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "heading",
          "label": "章节标题 §4 图",
          "in_report_section": "§4",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "行 16 全文唯一出现",
            "result": "resolved"
          },
          "note": "图目录章节标题行",
          "asset_id": "A27",
          "locator": {
            "method": "char_span",
            "start_char": 1293,
            "end_char": 1299,
            "start_line": 16,
            "end_line": 16,
            "quote": "## 4 图",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "figure_index",
          "label": "图目录（图1–图7 声明）",
          "in_report_section": "§4",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§4 整行；正则 图\\d+ 计数与平台 record.figures 长度比对",
            "result": "resolved"
          },
          "note": "仅图序号与用途文字，非图件本体；图件登记见下一条",
          "asset_id": "A28",
          "locator": {
            "method": "char_span",
            "start_char": 1300,
            "end_char": 1400,
            "start_line": 17,
            "end_line": 17,
            "quote": "图1 能力包线极坐标；图2 降额因子场；图3 波谱与二阶漂移力（STAWAVE-1 一致性）；图4 失效漂移速度 vs 两个解析预测；图5 漂移距离-时间线性区；图6 分层可证伪；图7 站桩时域历程。",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "figure_asset_set",
          "label": "平台 record.figures 图件（7 项）",
          "in_report_section": "§4",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "record.figures 每项仅含 name/caption，无内联图片数据、base64 或可下载 URI",
            "result": "unresolved"
          },
          "note": "图件二进制在本报告中不可解析：文件名=fig1_capability_polar.png; fig2_derating_field.png; fig5_wave_and_drift.png; fig3_drift_anchor.png; fig4_drift_linearity.png; fig6_layers.png; fig7_station_keeping.png；同名 figN 序号与图号存在错位（见 checks.figure_name_caption_permutation）",
          "asset_id": "A29",
          "locator": {
            "method": "char_span",
            "start_char": 1300,
            "end_char": 1400,
            "start_line": 17,
            "end_line": 17,
            "quote": "图1 能力包线极坐标；图2 降额因子场；图3 波谱与二阶漂移力（STAWAVE-1 一致性）；图4 失效漂移速度 vs 两个解析预测；图5 漂移距离-时间线性区；图6 分层可证伪；图7 站桩时域历程。",
            "unique": true,
            "duplicate_quote_of": "A28"
          }
        },
        {
          "asset_class": "heading",
          "label": "章节标题 §5 注意点（局限）",
          "in_report_section": "§5",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "行 19 全文唯一出现",
            "result": "resolved"
          },
          "note": "局限章节标题行",
          "asset_id": "A30",
          "locator": {
            "method": "char_span",
            "start_char": 1402,
            "end_char": 1414,
            "start_line": 19,
            "end_line": 19,
            "quote": "## 5 注意点（局限）",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "dataset",
          "label": "试验/公开 RAO 数据集",
          "in_report_section": "§5",
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "§5 第 1 条显式声明“非试验 RAO”；全文检索无试验 RAO 数据表/文件引用",
            "result": "absent"
          },
          "note": "报告自述该数据资产不存在：登记为 declared_absent，不得由本工序补造",
          "asset_id": "A31",
          "locator": {
            "method": "char_span",
            "start_char": 1415,
            "end_char": 1481,
            "start_line": 20,
            "end_line": 20,
            "quote": "1. 一阶波频力 RAO、附加质量/阻尼分项、Newman 单系数化均为**声明式**工程模型（非试验 RAO），只作趋势与量级结论",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "limitation_block",
          "label": "局限条目（4 条，声明式模型/包线性质/broaching/未建模项）",
          "in_report_section": "§5",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§5 整行按“；”切分得 4 条",
            "result": "resolved"
          },
          "note": "局限原文：适用于下游判断结论适用范围",
          "asset_id": "A32",
          "locator": {
            "method": "char_span",
            "start_char": 1415,
            "end_char": 1602,
            "start_line": 20,
            "end_line": 20,
            "quote": "1. 一阶波频力 RAO、附加质量/阻尼分项、Newman 单系数化均为**声明式**工程模型（非试验 RAO），只作趋势与量级结论；2. 分配器为迭代饱和冻结，包线是 `ALLOCATOR_BOUND`（非数学上界）；3. 顺风失控工况存在真实转首失稳（broaching），1D 解析锚算例锁定转艏自由度后比对；4. 未建模横摇/纵摇耦合、推进器响应滞后、波浪漂移阻尼。",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "heading",
          "label": "章节标题 §6 误差判定",
          "in_report_section": "§6",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "行 22 全文唯一出现",
            "result": "resolved"
          },
          "note": "误差判定章节标题行",
          "asset_id": "A33",
          "locator": {
            "method": "char_span",
            "start_char": 1604,
            "end_char": 1628,
            "start_line": 22,
            "end_line": 22,
            "quote": "## 6 误差判定（逐项，显式回答是否 <3%）",
            "unique": true,
            "duplicate_quote_of": null
          }
        },
        {
          "asset_class": "table",
          "label": "误差判定表（表头+分隔行+5 行数据）",
          "in_report_section": "§6",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "§6 行 23–29 连续切片；逐行以 '|' 起始的行计数=7",
            "result": "resolved"
          },
          "note": "表格逐行原文登记；误差数值与其“<3%?”判定仅登记，复算/裁量属平台门",
          "asset_id": "A34",
          "locator": {
            "method": "char_span",
            "start_char": 1629,
            "end_char": 1899,
            "start_line": 23,
            "end_line": 29,
            "quote": "| 关键量 | 基准 | 误差 | <3%? |\n|---|---|---|---|\n| 二阶定常漂移力 | STAWAVE-1 | <3%（测试钉住） | 是 |\n| 稳态漂移速度 | 严格二次根 | 0.84% | 是 |\n| 稳态漂移速度 | 线性等效阻尼式 | 5.39% | 否（公式适用边界 r≪1，已给出 r 分布） |\n| 静力平衡位置 | 解析 x*=x_sp+Kp⁻¹τ | 0.000%·L | 是 |\n| 一阶波频力 / 时域能力绝对值 / 失效漂移距离 | 无公开基准 | 不声明精度 | 无基准，只作趋势结论 |",
            "unique": true,
            "duplicate_quote_of": null
          }
        }
      ],
      "claims": [],
      "claims_note": "claims intentionally empty: contract objective = asset registration only (register_assets=true, classify_report_type=false, no extraction). Emitting claims here would fabricate task_type-03 knowledge objects.",
      "checks": {
        "source_hash_matches": true,
        "chars_match_contract": true,
        "title_matches_contract": true,
        "scenario_key_matches_contract": true,
        "all_quotes_unique": true,
        "all_locators_slice_back": true,
        "record_summary_numbers_present_in_markdown": {
          "tokens": [
            "12",
            "25.3%",
            "46.6%",
            "100%"
          ],
          "present": {
            "12": true,
            "25.3%": true,
            "46.6%": true,
            "100%": true
          },
          "all_present": true
        },
        "figure_count": {
          "record_figures": 7,
          "markdown_figure_refs": 7,
          "figure_refs": [
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7"
          ],
          "consistent": true
        },
        "figure_name_caption_permutation": {
          "count": 3,
          "items": [
            {
              "name": "fig5_wave_and_drift.png",
              "name_index": 5,
              "caption_index": 3
            },
            {
              "name": "fig3_drift_anchor.png",
              "name_index": 3,
              "caption_index": 4
            },
            {
              "name": "fig4_drift_linearity.png",
              "name_index": 4,
              "caption_index": 5
            }
          ]
        },
        "code_pointer_target_in_worktree": {
          "command": "grep -rIl --exclude-dir=.git coupled_maneuvering . (this package's own outputs excluded)",
          "hits_total": [
            "./knowledge/kb10k/claims/part-006.json",
            "./knowledge/kb10k/evidence/part-006.json"
          ],
          "hits_python_code": [],
          "code_artifact_present": false,
          "reading": "hits are knowledge/kb10k claim+evidence JSON (code-pointer records naming backend/api/coupled_maneuvering.py); no .py module in this worktree"
        },
        "dangling_reference_6_4": {
          "headings": [
            "## 1 案例介绍",
            "## 2 怎么做的",
            "## 3 计算结果",
            "## 4 图",
            "## 5 注意点（局限）",
            "## 6 误差判定（逐项，显式回答是否 <3%）"
          ],
          "has_6_4_heading": false
        }
      },
      "integrity": {
        "quote_uniqueness": "every quote occurs exactly once in the markdown (checked in-script)",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "no_claim_marked_verified": true,
        "verified_by": "scripts/kf_verify_12629.py (independent re-fetch + locator re-resolution)"
      },
      "boundaries": {
        "only_report_id": "12629",
        "other_reports_read_or_written": false,
        "upstream_work_package_artifacts_rewritten": false,
        "claims_marked_verified": 0
      }
    }
  },
  "claims": []
}
```
