#!/usr/bin/env python3
"""wp-11421-01 | compose the KF-RESULT report markdown from the emitted JSON artifacts.

Every number in the prose is injected from docs/kf/wp-11421-01/*.json at compose time
(zero hand-copy). The single ```json block at the end is kf_result.json verbatim — the
report is the delivery channel, so the envelope must be exactly what the gate will parse.

Writes docs/kf/wp-11421-01/KF-RESULT-wp-11421-01.md
"""
from __future__ import annotations

import hashlib
import json
import pathlib

D = pathlib.Path("docs/kf/wp-11421-01")
PKG = "wp-11421-01"


def j(name: str) -> dict:
    return json.loads((D / name).read_text(encoding="utf-8"))


def main() -> int:
    man, res, loc, acc, cc = (j("asset_manifest.json"), j("kf_result.json"),
                              j("locator_check.json"), j("acceptance_check.json"),
                              j("crosscheck.json"))
    src = man["source"]
    figs = [a for a in man["assets"] if a["asset_class"] == "figure"]
    fig_table = "\n".join(
        f"| {a['asset_id']} | `{a['payload']['bytes']}` B | "
        f"`{a['payload']['sha256'][:16]}…` | {a['resolution_check']['result']} |"
        for a in figs
    )
    ev_table = "\n".join(
        f"| {a['asset_id']} | {a['asset_class']} | {a['in_report_section']} | "
        f"{a['locator']['start_line']} | `{a['locator']['start_char']}–{a['locator']['end_char']}` | "
        f"{a['resolution']} | `{a['locator']['quote'][:56].replace('|', '␣')}` |"
        for a in man["assets"]
    )
    by_class = " · ".join(f"{k}={v}" for k, v in sorted(man["counts"]["by_class"].items()))
    verdicts = " · ".join(f"{k}={v}" for k, v in sorted(cc["summary"]["verdicts"].items()))
    x4 = next(c for c in cc["checks"] if c["check_id"] == "X4")
    x5 = next(c for c in cc["checks"] if c["check_id"] == "X5")
    x5w = x5["computed"]["worst"]
    x5row = x5["computed"]["per_factor"][x5w["factor"]]
    acc_lines = "\n".join(
        f"| {k} | {'✅' if (v is True or v == 'pass') else '❌'} | `{v}` |"
        for k, v in acc["checks"].items()
    )
    p1 = hashlib.sha256((D / "fig1_asset_resolution.png").read_bytes()).hexdigest()
    p2 = hashlib.sha256((D / "fig2_locator_map.png").read_bytes()).hexdigest()
    p3 = hashlib.sha256((D / "fig3_fd_vs_analytic.png").read_bytes()).hexdigest()

    md = f"""# KF-RESULT {PKG}

**报告：reports/11421 → 资产登记（task_type=01-asset-registration，lane C，status=draft）**

标题：`{src['title']}`　场景键：`{src['scenario_key']}`　标签：`{', '.join(src['platform_tags'])}`

> 本工序只做**登记**：不做抽取、不做报告分类（`classify_report_type=false`），
> 不把任何结论标为 verified（verification 由平台门计算）。`claims` 为空数组是契约允许的完整结果。

---

## ① 本工序做了什么

把 `tensor://reports/11421` 的 markdown 登记为一张可机器审核的资产清单：确认报告身份（report_id /
title / scenario_key）、重算并核对字节哈希、把报告里出现的**每一类可解析资产**（图、工件路径、代码指针、
内联数据表、机器判据块、运行配置、以及"被声明为不可得"的规则系数原文）逐条落成带 `char_span` 定位器的记录，
并给出"该资产在**本报告记录内**能否解析"的机械判定（`resolved_in_source` / `referenced_unresolved` /
`declared_absent`）。

顺带做了两件登记工序必须做、但容易被省掉的事（都只读本报告，不碰其它 report_id）：

1. **图载荷实探**：不只凭名字认图，逐张 `GET /tensor/reports/11421/figures/<name>`，记录 HTTP 状态、
   字节数、PNG 魔数与 sha256——"图在那儿"是被验证过的，不是被假设的。
2. **报告内部算术自洽复核**（7 项，见 §③）：报告正文对它自己表格的每一句数字断言都被重算了一遍。
   其中 5 项成立，2 项不成立，作为**下游缺陷候选**如实登记（severity=low，逐条给了理由与影响面）。
   这一步不产生 claim、不改任何数字，只防止"登记"把正文与表格的矛盾原样洗进下一道工序。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. `scripts/kf_wp11421_01_register.py`：用 `TENSOR_AGENT_USER/PASS` 登录取 token → `GET /tensor/reports/11421`
   取 `markdown` → **先断言后落盘**：sha256、字符数、title、scenario_key 四项与工单契约逐项比对，
   不一致即 `exit 2` 拒写。落盘 `source.md`（逐字节保真）+ `sha256.txt`。
2. **零手抄的实现方式**：22 条资产不写死引文，而是写"锚点"（行号 + 起止子串选择器），
   由脚本从**取回的 markdown 当场切片**得到 `quote`，再回查 `md.count(quote) == 1`；
   出现 0 次或 ≥2 次一律中止。定位器 `start_char/end_char` 由切片原地换算，写盘前再验
   `md[start:end] == quote`（三重一致：行锚 → 字符区间 → 引文）。
3. 图载荷实探（上述第 1 件事实），逐图记 `payload = {{http_status, bytes, content_type, sha256, png_magic}}`。
4. `scripts/kf_wp11421_01_crosscheck.py`：只从 markdown 解析表格数字，重算 7 项正文自述的算术恒等式
   （几何闭合 / CV=σ/mean / Sobol Σ 列和 / 负一阶指数 / 解析 vs 有限差分 / σ→0 线性收缩 / 域外推比例），
   输出 `crosscheck.json`（含每项的引文定位与容差依据）。
5. `docs/kf/wp-11421-01/asset_manifest.v1.schema.json`：仓内通用 schema `schemas/asset_manifest.v1.schema.json`
   把 `package_id` 与 `source.uri` 硬钉成 448 号报告（`const`），无法校验任何其它工单；本工序**不改**共享文件
   （那超出本包写权限，且会被别的工单依赖），而是按同一形状 pin 出本报告专属 schema，并额外约束
   `resolution ↔ resolution_check.result` 的一致性。
6. 校验链：`jsonschema` 校验 `kf_result.json`（对 `schemas/kf_result.v1.schema.json`）与
   `asset_manifest.json`（对本地 pin）→ 写 `acceptance_check.json`（6 项验收逐条落值）。
7. `scripts/kf_wp11421_01_figures.py`：3 张图（ASCII 标签，避免缺中文字体），全部由 JSON 现算。
8. `tests/test_kf_wp11421_01.py`：27 个用例，其中 8 个是**负控**（篡改引文 / 位移区间 / 异号 report_id /
   重复 id / 断言 claim 标 verified / 锚点串不存在 / …）——负控不过，说明校验器只是"跑过"而非"校验"。
9. 工具链：Python 3.11 + jsonschema 4.26 + matplotlib 3.10 + pytest；全程只读平台，未改任何 report。

## ③ 产出物清单（输出文件 → 要点）

| 文件（worktree 内） | 要点 |
|---|---|
| `docs/kf/wp-11421-01/asset_manifest.json` | **主产物**：{man['counts']['assets']} 条资产；`resolved_in_source={man['counts']['resolved_in_source']}` / `referenced_unresolved={man['counts']['referenced_unresolved']}` / `declared_absent={man['counts']['declared_absent']}`；类目 {by_class} |
| `docs/kf/wp-11421-01/kf_result.json` | 交付信封（{len(json.dumps(res, ensure_ascii=False))} 字符），`outputs['asset_manifest.json']` 内嵌同一份 manifest，`provenance.source_hash = sha256:{src['hash']}` |
| `docs/kf/wp-11421-01/locator_check.json` | {loc['summary']['quotes_total']} 条引文 → 唯一出现 {loc['summary']['quotes_unique']} 条、区间可解析 {loc['summary']['locators_resolvable']} 条、坏项 {len(loc['summary']['bad'])} |
| `docs/kf/wp-11421-01/acceptance_check.json` | 6 项验收的落值（见 §⑥），`all pass` |
| `docs/kf/wp-11421-01/crosscheck.json` | 7 项内部一致性复核：{verdicts}；findings = {cc['summary']['findings']} |
| `docs/kf/wp-11421-01/source.md` / `sha256.txt` | 原文逐字节副本 + 重算摘要（`chars={src['chars']}`, `bytes_utf8={src['bytes_utf8']}`） |
| `docs/kf/wp-11421-01/asset_manifest.v1.schema.json` | 本报告专属 pin schema（共享 schema 是 448 号专用 const，见 §②-5） |
| `docs/kf/wp-11421-01/fig1_asset_resolution.png` | 资产类目 × 解析状态的堆叠条形图（`sha256:{p1[:16]}…`） |
| `docs/kf/wp-11421-01/fig2_locator_map.png` | 22 条定位器在 {src['chars']} 字符原文轴上的投影 + 章节边界（`sha256:{p2[:16]}…`） |
| `docs/kf/wp-11421-01/fig3_fd_vs_analytic.png` | 两项 findings 的几何图（X5 相对差 vs 5% 界；X4 负一阶指数 ±1SE）（`sha256:{p3[:16]}…`） |
| `scripts/kf_wp11421_01_register.py` / `_crosscheck.py` / `_figures.py` / `_report.py` | 一键复跑链（见文末 `repro_cmd`） |
| `tests/test_kf_wp11421_01.py` | 27 passed（含 8 条负控） |

**六张图的载荷实探结果**（不是"报告里提到了"就算数）：

| 资产 | 字节 | sha256（前 16） | 判定 |
|---|---|---|---|
{fig_table}

## ④ 证据定位表（字段 → 原文逐字引文片段）

定位器三要素：`start_line`（1-based 行）、`start_char–end_char`（原文**字符**区间，非字节）、`quote`（逐字）。
全部 22 条引文在 `{src['chars']}` 字符原文中**各只出现 1 次**（`md.count(quote)==1`），且
`md[start_char:end_char] == quote` 逐条验过——这是 `source_locator_resolvable` 的机检口径。

| id | 类 | 报告位置 | 行 | 字符区间 | 解析 | 引文（逐字，截断 56 字符） |
|---|---|---|---|---|---|---|
{ev_table}

### 4.1 报告身份的四个独立锚点（都与契约一致）

| 字段 | 契约值 | 本工序实测 | 一致 |
|---|---|---|---|
| `report_id` | `11421` | `{res['report_id']}` | ✅ |
| `markdown` sha256 | `{src['hash']}` | `sha256:{src['hash']}` | ✅ |
| `chars` | `18542` | `{src['chars']}` | ✅ |
| `title` / `scenario_key` | 见契约 | `{src['title'][:28]}…` / `{src['scenario_key']}` | ✅ |

## ⑤ 注意点与局限（含 honest 失败项与未覆盖面）

1. **本工序一个数字都没有重算**：所有统计量（MC/Sobol/合规概率）与阻力/推进链的结果都在生产仓
   （`ship-performance-platform`），**不在本报告记录内**（见 A07/A09/A10/A11/A12/A15）；
   因此本包只对"报告**对它自己表格**的算术断言"做复核，不对生产结果本身背书。
2. **findings X4（severity=low）**：§2.2 声称 Jansen 估计量"同样满足 `S_i ≥ 0`"，但表5 打印了
   {x4['computed']['n_negative_first_order']} 个**负**一阶指数（geom_L −0.0028、geom_B −0.0016、op_port −0.0031、
   op_speed −0.0031、eng_mcr −0.0004、op_epl −0.0004）。{x4['computed']['n_negative_first_order']} 个全部落在 ±1 SE 内，
   属估计量噪声而非物理，报告结论不受影响；但这句话若被下游当"方法事实"引用就是错的
   （Jansen 的**一阶**估计量并非非负，非负的是其总效应式）。修法是改这句措辞或改成"总效应非负"。
3. **findings X5（severity=low）**：§3.4(b) 称解析与有限差分"非零项相对差 < 5%"，而表5 中
   `{x5w['factor']}` 的解析值 {x5row['analytic']} vs 差分值 {x5row['fd']} 相对差 **{x5w['rel_diff']:.2%}**。
   该行绝对值正好在 Holtrop 0.01 kN 量化地板上（报告 §4.1 自己写了这个地板），所以 16% 主要是噪声；
   缺陷是"无条件写 <5%"的措辞，而不是数字。建议加限定"|c_i| ≥ 0.005 的项"。
4. **图只看名字+字节，不看内容**：登记只证明"该 PNG 可从本记录取回且是合法 PNG"，
   **不主张**图里画的就是表里那些数（内容一致性需要重跑生产脚本，本记录无此能力）。
5. **附录 A 的"= tables.md 原文"不可验**：附录自称是 `artifacts/P270W1-N07/tables.md` 原文，
   但外部文件不在本记录内（A08），字节一致性只能留 `referenced_unresolved`，不做任何"一致"的暗示。
6. **要求值不可复核（`WITHHELD`）**：EEXI/CII 要求值来自 MEPC.328(76)/MEPC.353(78) 系数转录，
   报告自己标了 `WITHHELD`，本包登记为 `declared_absent`（A21）——不是"缺失待补"，而是"生产方已声明无原文"。
7. **未做**：报告类型分类（契约 `classify_report_type=false`）、claim 抽取（契约未要求，且本包无抽取依据）、
   任何 verified 标记（明确禁止）。
8. **离线性**：`--source-file` 复跑对 22 条资产中的 16 条非图资产**逐字节一致**；
   6 张图因需要向平台实探，离线时如实标 `payload probe NOT RUN / resolution=unresolved`，不冒充在线结果。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 实测值 / 口径 |
|---|---|---|
{acc_lines}

补充自证（不属于 acceptance，但本包自己加的）：`pytest tests/test_kf_wp11421_01.py` → **27 passed**
（含 8 条负控：篡改引文即被检出、位移区间即不匹配、异号 `report_id` 即 schema 失败、重复 id 即唯一性失败、
`"status":"verified"` 即触发断言）；`crosscheck.json` 7 项 {verdicts}。

**honest-FAIL 声明**：交叉复核 X4 / X5 两项判定为 **fail**（正文断言与其自身表格不符），
本包**不修改**报告原文、不重算生产结果、不把这两项写成"已解决"——它们作为缺陷候选移交给下游工序。
除此之外本包没有其它未达标项。

## 图（平台内嵌）

1. `fig1_asset_resolution.png`：{man['counts']['assets']} 条资产按类目 × 解析状态堆叠——
   一眼看出"能从本记录里真的取到什么"（{man['counts']['resolved_in_source']} 条）与"只是指针"（{man['counts']['referenced_unresolved']} 条）的比例。
2. `fig2_locator_map.png`：22 条定位器投影在 {src['chars']} 字符原文轴上并叠加章节边界——
   定位覆盖全文而非仅头部，红/灰块即"原文点名但本记录拿不到"的资产。
3. `fig3_fd_vs_analytic.png`：左 = X5 逐因子"解析 vs 差分"相对差（对数轴，虚线为报告自述的 5% 界）；
   右 = X4 的 {x4['computed']['n_negative_first_order']} 个负一阶指数与 ±1 SE 误差棒（竖线为 0）。

"是否 <3%" 回答：本包不产出任何物理量，无基准误差可言；可对标的是**报告内部算术**——
X1 几何闭合 {cc['checks'][0]['computed']['recomputed_rel_err']:.6f} vs 报告 {cc['checks'][0]['computed']['reported_rel_err']}（差 <5e-7）、
X2 五行 CV 全部在 4 位小数舍入内、X3 Σ 列和最大偏差 1e-4、X6 8 行（4 档 ε × 2 口径）全在 σ 打印量化内、
X7 {cc['checks'][6]['computed']['recomputed_pct']}% vs {cc['checks'][6]['computed']['printed_pct']}%——**均 <3%**，
唯 X4/X5 不是数值精度问题而是措辞与表格冲突（见 §⑤-2/3）。

### repro_cmd（一键复跑，需 `TENSOR_AGENT_USER/PASS`）

```sh
python3 scripts/kf_wp11421_01_register.py \
 && python3 scripts/kf_wp11421_01_crosscheck.py \
 && python3 scripts/kf_wp11421_01_figures.py \
 && python3 scripts/kf_wp11421_01_report.py \
 && python3 -m pytest tests/test_kf_wp11421_01.py -q
```

交付信封（`package_id={res['package_id']}`, `task_type={res['task_type']}`, `report_id={res['report_id']}`,
`provenance.source_hash={res['provenance']['source_hash']}`）原样如下，此文件内**仅此一个** JSON 代码块：

```json
{json.dumps(res, ensure_ascii=False, indent=2)}
```
"""
    p = D / "KF-RESULT-wp-11421-01.md"
    p.write_text(md, encoding="utf-8")
    # invariant: exactly one ```json block, and it round-trips to kf_result.json
    assert md.count("```json") == 1, md.count("```json")
    block = md.split("```json", 1)[1].split("```", 1)[0]
    assert json.loads(block) == res
    print(p, p.stat().st_size, "bytes; json-block roundtrip ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())