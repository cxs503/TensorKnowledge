# CII 规则内核三副本单源化与 regime 语义修复（m13764）

**锚点**：NEW（`KPI-QC-RECHECK` 已合并功能独立复核的子项；建议新条目
`DEF-CII-SINGLE-SOURCE`，见文末）
**证据等级**：数值层 REAL（纯代数，可独立标量复算）；法规系数层 WITHHELD（离线未回读规则原文；
本次不动系数，仅修语义与副本一致性）

## ① 案例介绍（问题背景）

IMO 碳强度规则（MEPC.353(78) 参考线 / MEPC.338(76) 年度折减率 Z / MEPC.354(78) 评级）
在本仓存在 **三份独立实现**：

| 代号 | 位置 | Z 表口径 | 角色 |
|---|---|---|---|
| A | `backend/services/cii_required_value.py` | 分数 | 权威口径（显式 regime，m1829 建） |
| B | `backend/api/green_shipping.py` | 分数 | 主 API 副本 |
| C | `backend/modules/green_navigation_ice/mepc.py` | 百分比 | 冰区链副本 |

复核靶子：**同一年份的 CII 要求值，三处是否给同一个数、同一套语义？**
（同一规则三副本 = 单源纪律的直接违反对象，且三处都不是错值报错型，而是静默默认型。）

## ② 怎么做的（方法）

1. 写机器对账工具 `tools/cii_consistency_scan.py`：对 (年份 2019–2030) × 三实现，
   逐点取 (z, required_value, regime, extrapolated, 异常)，判定是否一致，输出 JSON 基线。
2. 先跑基线（`artifacts/cii_consistency_scan_before.json`）→ **12/12 年份不一致**。
3. 定位根因（两条，均为静默默认）：
   - **C1（真缺陷，仅 C）**：`mepc.z_factor` 用 `Z_FACTORS.get(year, 11.0)` 一次性兜底，
     `year<2023` 也套 11% 折减 → 规则尚未生效的年份给出"要求值"，比 2019 参考线**低 11.0%**
     （bulk carrier / 80000 DWT：3.7662 vs 4.2317 gCO2/(dwt·nm)）；
   - **C2（仅 B/C）**：`year>2026` 静默沿用 11%，返回体无外推标记，下游无法区分
     "法规确定值"与"外推值"。
4. 修复（最小改动，语义层单源化）：
   - `mepc.py`：Z 表由 A 派生（`Z_FACTORS = 100·A.CII_Z_FACTOR`），新增
     `z_regime() / z_extrapolated() / required_cii_meta()`；`z_factor()` 对 <2023 返回 0.0
     （= 参考线口径，且 regime 可判）；2023–2026 数值逐位不变；
   - `green_shipping.py`：`_gn_required_cii()` 委派 A 的 `required_cii()`，保留原键
     （`z_factor` 仍为分数），新增 `regime / z_extrapolated / required_value_is_reference / regime_note`；
   - `green_navigation_ice/api.py`：`compliance` 与 `model_audit` 回显 regime 标记与
     `dd_vector_basis`（dd 向量为通用单档，未做船型×容量档转录 → 机器可见的局限声明）；
   - **不动**任何法规系数（a/c、Z 表值、dd 值），不据此提高证据等级。

## ③ 计算结果（程序化注入，`artifacts/cii_consistency_scan_*.json`）

bulk carrier, Capacity = 80000 DWT：

| year | regime | z（分数） | 修复前 B | 修复前 C | 修复后 A=B=C | 一致性 |
|---|---|---|---|---|---|---|
| 2019–2022 | not_yet_applicable | 0.00 | 4.2317 (无标记) | **3.7662 (−11.0%)** | 4.2317 | 前 ✗ / 后 ✓ |
| 2023 | determined | 0.05 | 4.0201 | 4.0201 | 4.0201 | 前 ✗(regime 缺) / 后 ✓ |
| 2024 | determined | 0.07 | 3.9355 | 3.9355 | 3.9355 | 同上 |
| 2025 | determined | 0.09 | 3.8508 | 3.8508 | 3.8508 | 同上 |
| 2026 | determined | 0.11 | 3.7662 | 3.7662 | 3.7662 | 同上 |
| 2027–2030 | extrapolated | 0.11 | 3.7662 (无标记) | 3.7662 (无标记) | 3.7662 (`z_extrapolated=True`) | 前 ✗ / 后 ✓ |

对账结论：修复前 `divergent_years = 12/12`，修复后 `0/12`
（`artifacts/cii_consistency_scan_before.json` / `_after.json`）。

## ④ 结果图

`artifacts/m13764_cii_consistency.png`：左右两栏为修复前/后三实现的 required CII–year 曲线，
灰色带 = 规则未适用年份（2019–2022）。修复前 C 曲线在灰带内整体低于 A/B 11.0%（缺陷可见）；
修复后三线完全重合。

## ⑤ 注意点 / 局限

- **未动的部分**：法规系数（a/c、Z 表、dd 向量）均为离线转录，证据等级仍 WITHHELD；
  本次修复**不改变**任何系数的可信度，只消除"同一规则三个答案"与"静默默认"。
- **评级（A–E）机制已验，法规值未验**：`dd_vector` 只有一档通用值 (0.86, 0.94, 1.06, 1.18)，
  未做 MEPC.354(78) G4 的船型×容量档转录。因此只断言分区完备/单调/端点归属（机制层），
  不断言逐船型评级正确；`DD_VECTOR_BASIS` 与 `/reference`、`model_audit` 均显式回显该局限。
  `green_shipping` 的 L4 层仍保持 NOT_SUPPORTED，未因本次修复被提升（不制造假能力）。
- **行为变更（向后兼容性）**：`mepc.required_cii(ref, 2019)` 由 3.7662 变为 4.2317（修正值）；
  2023–2026 逐位不变，故 pathway / monte_carlo / pipeline 现有链路（年份 ≥2023）数值不受影响
  （冰区模块 47 条测试、green_shipping 37 条测试全绿）。
- 2027+ 仍返回 11%（工程保守取最后已通过值），但现在**必须**带 `z_extrapolated=True`，
  调用方不能"只看数字"当合规结论。

## ⑥ 误差判定

| 关键量 | 基准 | 修复前误差 | 修复后误差 | <3%? |
|---|---|---|---|---|
| 2019–2022 要求值（C 实现） | 2019 参考线 `a·Cap^(−c)` = 4.2317 | **−11.00%** | 0.00%（逐位相等） | 前否 / **后是** |
| 三实现 z 值（2019–2030，12 年 × 4 船型 × 3 容量） | A 单源 | 不一致（B/C 缺 regime，C 4 年错值） | 相对差 ≤1e-15 | **后是** |
| 三实现 required_value（同上网格） | A 单源 | 同上 | 相对差 ≤1e-15 | **后是** |
| 评级机制（边界分区/单调/端点） | 解析定义 dd_i·req | — | 153 条断言全通过 | 不适用（机制层） |

## 复现

```bash
python3 tools/cii_consistency_scan.py --out artifacts/cii_consistency_scan_after.json
python3 -m pytest tests/test_cii_single_source_consistency.py -q          # 153 passed
python3 -m pytest backend/modules/green_navigation_ice/tests -q           # 47 passed
python3 -m pytest backend/tests/test_green_shipping.py \
                 backend/tests/test_green_efficiency_m1895.py -q          # 37 passed
python3 -m pytest tests/test_cii_regime_m1829.py -q                       # 70 passed
```

## 建议新总账条目

- `slug=DEF-CII-SINGLE-SOURCE`，域：绿色航行（`ship-performance-platform`）
- 验收：三实现 (2019–2035 × {bulk,tanker,container,gas} × {15k,80k,200k}) 的
  z/required_value/regime 逐点相对差 ≤1e-12 且 `divergent_years == 0`（本单已达：
  12/12 → 0/12，153 条回归断言）；
- 后续增量（未做）：MEPC.354(78) G4 船型×容量档 dd 向量转录 → 才能把
  `green_shipping` L4 评级从 NOT_SUPPORTED 提升。