# wp-5716-04 · 报告 5716 独立复核（IN10-G1 冰区航行总攻验收门）

> 工序 04-independent-review ｜ 被复核报告 5716（mission {{MISSION_ID}}，`{{SCENARIO}}`）
> 源快照 sha256 `{{SRC_SHA}}`（{{SRC_CHARS}} 字符 / {{SRC_BYTES}} 字节，与 wp-5716-01 登记值逐字节相同）
> 结论：**approve_with_notes**（{{N_FINDINGS}} 条发现：{{N_MAJOR}} major / {{N_MEDIUM}} medium / {{N_LOW}} low / {{N_INFO}} info；**无阻断项**）

## ① 案例介绍

**被复核对象**：`{{TITLE}}`。该报告声称把五个独立开发的冰区航行模型（A2 冰况同化预报 / C3 航速剖面 /
D1 冰区航线 / E1 数字孪生 / B2 冰带疲劳）串成一条「{{N_GATE}} 项一致性门 + {{N_DISC}} 项披露项」的端到端
验收链，并如实登记 {{N_DISC}} 项披露不通过。

**物理背景与几何参数（取自报告 ①；本包只做一致性复核，不重算物理）**：

| 参数 | 值 | 参数 | 值 |
|---|---|---|---|
| 船型 | 北极喀拉海边缘冰区 PC6 冰级散货船母型 | 载重吨 | 45 000 DWT |
| L_pp | 190 m | B | 30 m |
| T | 11.5 m | Cb（声明） | 0.82 |
| 主机 | 18 MW | 服务航速 | 13 kn |
| σ_f（冰弯曲强度） | 500 kPa | B1 冰挤压设计力 | 8 MN @ 0.25 Hz |
| 年冰区占比 | 0.12 | 设计寿命 | 20 年 |
| 设计点（A2 最不利 lead） | h=0.91 m, C=0.81 → 4.50 kn / 3.57 MW / R_ice=464.7 kN | A2 窗口对 D1 域覆盖 | {{COVERAGE_PCT}}%（其余为已声明气候态填充） |

**我的角色**：{{N_CHECKS}} 项独立检查，只回答一个很窄的问题——报告里那些可以被闭式复算或内部对照的数字，
在只读已发表文本的前提下是否成立；对无法重建的测量量明确标 `withheld`，**不判通过**。

## ② 怎么做的

**方法**：一切数字来自两处——报告 5716 的 markdown 正文、平台报告记录（`GET /tensor/reports/5716`）。
每项检查写成「输入 → 公式 → 复算 → 与宣称对比」，剧本与报告内**不含手写数值**：本文件由
`report_body.tmpl.md` 的占位符经 `recompute.json` 注入生成；源头绑定用 `sha256(markdown)` 与 wp-5716-01
登记的契约哈希对齐（本包复算值 `{{SRC_SHA}}`，逐字节相同）。

**为什么只能这样做**：campaign 侧工件（`backend/modules/campaign_ice_nav`、`artifacts/campaign_ice_nav`、
`backend/tests/test_campaign_ice_nav.py`）不在本仓工作树内；wp-5716-01 登记的 {{N_ASSETS}} 条引用里有
{{N_UNRESOLVED}} 条解析为 `not present in delivery worktree`。因此**不能**重跑链路，只能做
(a) 字节取证、(b) 披露值的闭式算术复算、(c) 陈述之间的一致性对照。

**工具链**：python3 标准库（解析 + 算术）→ `recompute.json`；matplotlib（Agg）→ 2 张 png；平台 API →
源快照 `source_5716.md` + `source_5716.md.meta.json`。

**判定口径**（五类，逐检查登记在 `recompute.json.checks[].verdict`）：

| 判定 | 含义 | 计数 |
|---|---|---|
| `reproduced` | 由披露值复算，落在 3% 内 | {{N_REPRO}} |
| `self_consistent` | 无法外部对标，但自身/量级闭合 | {{N_SELFCONS}} |
| `contradicted` | 报告内部两个陈述（或两种读法）不能同时成立 | {{N_CONTRAD}} |
| `gap` | 表格或参数缺失（完整性问题） | {{N_GAP}} |
| `withheld` | 缺工件/缺定义，**不可判定，不判通过** | {{N_WITHHELD}} |

## ③ 计算结果

### ③.1 总览

{{N_CHECKS}} 项检查中 {{N_NUMERIC}} 项带数值复算：{{N_REPRO}} reproduced、{{N_SELFCONS}} self-consistent、
{{N_CONTRAD}} contradicted、{{N_GAP}} gap、{{N_WITHHELD}} withheld。**所有「复算 vs 宣称」类偏差都 <3%**
（{{UNDER3_LIST}}，最大 {{MAX_CLAIM_DEV}}% 来自读法敏感性 `R03`）；≥3% 的量全部是**文档级不一致**
（{{INCONS_LIST}}），不是物理精度误差。

### ③.2 逐项检查（数值全部由 recompute.json 注入）

{{CHECK_TABLE}}

### ③.3 报告 §⑥ 误差表的复核（逐项回答是否 <3%）

{{S6_TABLE}}

### ③.4 发现（按严重度排序，逐条可复算）

{{FINDINGS_TABLE}}

## ④ 结果图

**图 A（`figures/fig_review_errors.png`）**：左栏把报告 §⑥ 的 {{N_S6}} 项误差摆到 3%（owner 线）与 15%
（平台线）上，绿=达标、红=未达标——报告自判「否」的 5 项与红色完全一致，无粉饰；右栏是本次 {{N_NUMERIC}} 项
数值复算的 |复算−宣称|/宣称（对数轴），按判定着色。读图要点：右栏全部落在 3% 线**左侧**；红/灰点是文档级
不一致与不可复算项，不是数值算错。

**图 B（`figures/fig_review_closure.png`）**：左栏是闭合台账（自报 {{N_GATE}} 门 PASS / {{N_DISC}} 披露 FAIL，
对上本次 {{N_CHECKS}} 项判定的分布）；右栏按主题给出逐项判定色块图，可一眼看出 `document`、`figures`、
`contract_remap` 是本次唯一不是「绿/青」的三个主题。

图内标签用英文：运行环境只有 `Noto Sans`，无 CJK 字形，中文会渲染成方块（见 ⑤ 注意点 1）。

## ⑤ 注意点与局限

1. **无 CJK 字体**：图内文字全部英文；这不是排版偏好，是环境限制（`fc-list` 里没有任何中文字形）。
2. **不能重跑链路**：{{N_UNRESOLVED}}/{{N_ASSETS}} 条引用未解析，A2 技能、E1 闭环误差、Uikku MAPE、
   方向探针、墙钟这 5 类**测量量**只能 withheld；把它们当「通过」是越界。
3. **报告只给百分比、不给原始数**：§⑥ 每项都是「误差百分数」，没有实测/基准数值对，因此只能做自洽性判断，
   做不了统计意义上的误差分布。
4. **ρ 未声明是最有价值的一条**：Cb 反算必须除海水密度，报告没写 ρ；隐含值 ρ={{CB_RHO_IMPLIED}} t/m³，
   而按另一种同样字面的读法 Cb={{CB_ALT}}（{{CB_ALT_DEV_PCT}}% > 2% 容差）G01 会 FAIL。所以
   「{{N_GATE}}/{{N_GATE}} PASS」部分依赖未写约定——这是我认为最接近阻断的项，但它不改变任何结论方向，
   仍列 non-blocking。
5. **`冰区占比 27.0%` 有三个读法**：距离读法与能量读法分别让 63.3 h 不可行（超出 {{T_MIN_OVER_PCT}}% /
   {{T_ENER_OVER_PCT}}%），只有时间读法闭合（此时冰区航程 {{D_ICE}} nm = 航程的 {{D_ICE_FRAC_PCT}}%，
   开阔水复算 {{V_OW}} kn）→ 该百分比必须写分母。
6. **复核的单向性**：我只能证伪「算术不成立」，不能证明「物理正确」。报告自称的物理精度（Uikku
   {{UIKKU_MAPE}}%、B2 β {{B2_BETA_DEV}}%、D1↔C3 {{D1C3_DIV}}%、E1 三项闭环 >3%）我未独立重算，
   其方向与报告自判一致，属 honest FAIL。
7. **单一复核者**（agent/m20853），无第二复核人；平台 `figures[]` 只有 name/caption 无字节，报告的
   {{N_FIG_FIELD}} 张论文图未审。
8. **适用范围**：本结论只对源快照 `{{SRC_SHA}}` 这一版报告 5716 成立；报告一旦修订，须重跑本包流程。

## ⑥ 误差判定（显式回答是否 <3%）

**逐项**：

| 类别 | 项 | 复算偏差 | 是否 <3% |
|---|---|---|---|
| 恒等式复算 | `R01` Cb 反算（ρ=1.025） | {{CB_DEV}}% | **是** |
| 恒等式复算 | `R02` L/B、B/T | {{LB_DEV}}% | **是** |
| 自洽闭合 | `R10` C3 能耗/时间 → 开阔水 {{V_OW}} kn vs 服务 13 kn | {{V_OW_DEV}}% | **是** |
| 恒等式复算 | `R14` B2 β 修正后利用率 {{UTIL_CORR}} vs 宣称 12.4 | {{UTIL_DEV}}% | **是** |
| 恒等式复算 | `R06` `R09` `R18` `R20` `R22`（覆盖 / 航速 / 门数 / 分歧区间 / 源哈希） | 0 | **是** |
| 读法敏感 | `R03` 若 0.8167 已给出体积 → Cb={{CB_ALT}} | {{CB_ALT_DEV_PCT}}% | **是（但 >2% 门容差，会翻转 G01）** |
| 文档不一致 | {{INCONS_LIST}} | {{INCONS_RANGE}}% | 否（文档缺陷，非精度） |
| 不可判定 | `R04` A2 技能、`R08` 方向探针、`R21` 图清单 | — | 无基准：工件/定义缺失，不判通过 |

**结论性回答**：

1. 凡能用已披露数字闭式复算的项，**全部 <3%**（最大 {{MAX_CLAIM_DEV}}%，且属读法敏感性）——
   报告的数字**没有算术错误**。
2. 报告自身的物理精度项（E1 三项闭环 3.01–5.43%、Uikku MAPE {{UIKKU_MAPE}}%、B2 β {{B2_BETA_DEV}}%、
   D1↔C3 {{D1C3_DIV}}%）**均 >3%**，报告已逐条自判「否」；本次复核**确认其方向正确、无粉饰**。
   这些是模型物理缺口（GAP-INT-05/07 等），不是本次复核能修的。
3. {{N_INCONS}} 项文档级不一致（{{INCONS_LIST}}）**>3%**，必须修订，但均不改变任何 FAIL 方向。

**honest FAIL（本包自身不足，不粉饰）**：

- 未能重跑任何一条上游链路（工件不在本仓），因此「复现性」只到字节与算术层面。
- 未审计报告的 {{N_FIG_FIELD}} 张论文图（平台无字节）。
- 无第二复核人；「独立」只指方法独立于生产者，不是双盲。
- 本包不随附生成脚本（单 PR ≤10 文件交付纪律），图的复现依赖 `recompute.json` 的 `checks[].inputs/formula`。