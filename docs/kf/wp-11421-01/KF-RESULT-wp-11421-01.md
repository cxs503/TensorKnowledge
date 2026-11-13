# KF-RESULT wp-11421-01

**报告：reports/11421 → 资产登记（task_type=01-asset-registration，lane C，status=draft）**

标题：`P270W1-N07 端到端不确定度传播：几何→阻力→推进→EEXI/CII 六因子分解（蒙特卡洛 + Sobol）`　场景键：`ship_performance`　标签：`EEXI, CII, 不确定度传播, 蒙特卡洛, Sobol, green_shipping, Holtrop, defect_fix, P270W1-N07`

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
3. 图载荷实探（上述第 1 件事实），逐图记 `payload = {http_status, bytes, content_type, sha256, png_magic}`。
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
| `docs/kf/wp-11421-01/asset_manifest.json` | **主产物**：22 条资产；`resolved_in_source=11` / `referenced_unresolved=10` / `declared_absent=1`；类目 api_function=1 · artifact_path=1 · config=1 · data_table=4 · figure=6 · machine_criteria=1 · module=2 · result_field=1 · rule_reference=1 · run_config=1 · source_code=1 · test=2 |
| `docs/kf/wp-11421-01/kf_result.json` | 交付信封（17344 字符），`outputs['asset_manifest.json']` 内嵌同一份 manifest，`provenance.source_hash = sha256:f85c29fe650365140152064807d90b2accdf43382f2222956470f3521e0a280a` |
| `docs/kf/wp-11421-01/locator_check.json` | 22 条引文 → 唯一出现 22 条、区间可解析 22 条、坏项 0 |
| `docs/kf/wp-11421-01/acceptance_check.json` | 6 项验收的落值（见 §⑥），`all pass` |
| `docs/kf/wp-11421-01/crosscheck.json` | 7 项内部一致性复核：fail=2 · pass=5；findings = ['X4', 'X5'] |
| `docs/kf/wp-11421-01/source.md` / `sha256.txt` | 原文逐字节副本 + 重算摘要（`chars=18542`, `bytes_utf8=26405`） |
| `docs/kf/wp-11421-01/asset_manifest.v1.schema.json` | 本报告专属 pin schema（共享 schema 是 448 号专用 const，见 §②-5） |
| `docs/kf/wp-11421-01/fig1_asset_resolution.png` | 资产类目 × 解析状态的堆叠条形图（`sha256:f49c5102c1e92e37…`） |
| `docs/kf/wp-11421-01/fig2_locator_map.png` | 22 条定位器在 18542 字符原文轴上的投影 + 章节边界（`sha256:fb2769c289d6879b…`） |
| `docs/kf/wp-11421-01/fig3_fd_vs_analytic.png` | 两项 findings 的几何图（X5 相对差 vs 5% 界；X4 负一阶指数 ±1SE）（`sha256:c1b8583b3f55af9a…`） |
| `scripts/kf_wp11421_01_register.py` / `_crosscheck.py` / `_figures.py` / `_report.py` | 一键复跑链（见文末 `repro_cmd`） |
| `tests/test_kf_wp11421_01.py` | 27 passed（含 8 条负控） |

**六张图的载荷实探结果**（不是"报告里提到了"就算数）：

| 资产 | 字节 | sha256（前 16） | 判定 |
|---|---|---|---|
| A01 | `35000` B | `4a0a017c83479d24…` | resolved |
| A02 | `34172` B | `da364aa95995095d…` | resolved |
| A03 | `59347` B | `1c58606359663941…` | resolved |
| A04 | `42898` B | `62fe1b478b385961…` | resolved |
| A05 | `61521` B | `389eba0851bbedfd…` | resolved |
| A06 | `54685` B | `ca46f8cea7138f0e…` | resolved |

## ④ 证据定位表（字段 → 原文逐字引文片段）

定位器三要素：`start_line`（1-based 行）、`start_char–end_char`（原文**字符**区间，非字节）、`quote`（逐字）。
全部 22 条引文在 `18542` 字符原文中**各只出现 1 次**（`md.count(quote)==1`），且
`md[start_char:end_char] == quote` 逐条验过——这是 `source_locator_resolvable` 的机检口径。

| id | 类 | 报告位置 | 行 | 字符区间 | 解析 | 引文（逐字，截断 56 字符） |
|---|---|---|---|---|---|---|
| A01 | figure | §3.5 图 | 260 | `10232–10293` | resolved_in_source | ``fig1_eexi_pdf.png` ␣ EEXI 达到值 PDF + 要求值竖线 + 5–95% 带 + 合` |
| A02 | figure | §3.5 图 | 261 | `10296–10325` | resolved_in_source | ``fig2_cii_pdf.png` ␣ CII 同上 ␣` |
| A03 | figure | §3.5 图 | 262 | `10328–10391` | resolved_in_source | ``fig3_sobol_groups.png` ␣ 六因子组一阶/总效应 Sobol（EEXI、CII 双面板，` |
| A04 | figure | §3.5 图 | 263 | `10394–10439` | resolved_in_source | ``fig4_convergence.png` ␣ 样本量收敛：σ 与合规概率 vs N ␣` |
| A05 | figure | §3.5 图 | 264 | `10442–10508` | resolved_in_source | ``fig5_sigma_control.png` ␣ σ→0 负控：σ 比 vs ε（对数-对数，斜率 1 参考` |
| A06 | figure | §3.5 图 | 265 | `10511–10574` | resolved_in_source | ``fig6_sensitivity.png` ␣ 灵敏度结构：解析 δ 法 vs 有限差分 vs MC Sobo` |
| A07 | artifact_path | §preamble 工件 | 5 | `236–296` | referenced_unresolved | ``artifacts/P270W1-N07/{results.json, tables.md, fig1..fi` |
| A08 | data_table | 附录 A | 331 | `13210–13260` | referenced_unresolved | `## 附录 A · 数字表（`artifacts/P270W1-N07/tables.md` 原文）` |
| A09 | source_code | §preamble 执行脚本 | 4 | `184–228` | referenced_unresolved | `**执行脚本**：`scripts/p270w1_n07_uncertainty.py`` |
| A10 | module | §preamble 模块 | 4 | `156–183` | referenced_unresolved | ``backend/modules/green_uq/`` |
| A11 | module | §2.1 确定性链 | 74 | `2931–2982` | referenced_unresolved | `Holtrop-Mennen 唯一实现（backend/physics/holtrop）   [kN]` |
| A12 | api_function | §2.1 纪律 1 | 92 | `3681–3762` | referenced_unresolved | ``api/green_shipping` 的 `_gn_attained_index` / `_gn_attai` |
| A13 | test | §2.3 缺陷修复 | 125 | `5288–5372` | referenced_unresolved | ``test_chain.py::test_attained_index_unit_1852_fix`，相对差 <` |
| A14 | test | §2.3 缺陷修复 | 127 | `5457–5513` | referenced_unresolved | `原有 18 条 `test_green_shipping.py` 断言（只断言 `idx > 0`）全部仍通过。` |
| A15 | config | §1.3 不确定度谱 | 45 | `1767–1785` | referenced_unresolved | `出处（`spec.py` 逐条） ␣` |
| A16 | data_table | 附录 A | 333 | `13262–13289` | resolved_in_source | `# P270W1-N07 数字表（程序化生成，勿手改）` |
| A17 | data_table | §1.3 | 43 | `1713–1737` | resolved_in_source | `### 1.3 六因子不确定度谱（13 个成员）` |
| A18 | machine_criteria | §preamble 机器判据 / 附录 A 表8 | 6 | `297–373` | resolved_in_source | `**机器判据**：`artifacts/P270W1-N07/results.json → criteria`（` |
| A19 | run_config | 附录 A 表头 | 336 | `13322–13509` | resolved_in_source | `配置：{"n_mc": 200000, "n_sobol": 32768, "n_sobol_small": 3` |
| A20 | result_field | §4 注意点 5 | 285 | `11382–11450` | referenced_unresolved | ``monte_carlo.numerics.out_of_holtrop_domain`）。这是**边界外推**` |
| A21 | rule_reference | §1.2 要求值 | 41 | `1657–1711` | declared_absent | `（`WITHHELD`：系数转录自 MEPC.328(76)/MEPC.353(78)，离线不可回读原文）。` |
| A22 | data_table | §1.2 | 26 | `890–928` | resolved_in_source | `### 1.2 设计案例（Kamsarmax 散货船，80 000 dwt）` |

### 4.1 报告身份的四个独立锚点（都与契约一致）

| 字段 | 契约值 | 本工序实测 | 一致 |
|---|---|---|---|
| `report_id` | `11421` | `11421` | ✅ |
| `markdown` sha256 | `f85c29fe650365140152064807d90b2accdf43382f2222956470f3521e0a280a` | `sha256:f85c29fe650365140152064807d90b2accdf43382f2222956470f3521e0a280a` | ✅ |
| `chars` | `18542` | `18542` | ✅ |
| `title` / `scenario_key` | 见契约 | `P270W1-N07 端到端不确定度传播：几何→阻力→推…` / `ship_performance` | ✅ |

## ⑤ 注意点与局限（含 honest 失败项与未覆盖面）

1. **本工序一个数字都没有重算**：所有统计量（MC/Sobol/合规概率）与阻力/推进链的结果都在生产仓
   （`ship-performance-platform`），**不在本报告记录内**（见 A07/A09/A10/A11/A12/A15）；
   因此本包只对"报告**对它自己表格**的算术断言"做复核，不对生产结果本身背书。
2. **findings X4（severity=low）**：§2.2 声称 Jansen 估计量"同样满足 `S_i ≥ 0`"，但表5 打印了
   6 个**负**一阶指数（geom_L −0.0028、geom_B −0.0016、op_port −0.0031、
   op_speed −0.0031、eng_mcr −0.0004、op_epl −0.0004）。6 个全部落在 ±1 SE 内，
   属估计量噪声而非物理，报告结论不受影响；但这句话若被下游当"方法事实"引用就是错的
   （Jansen 的**一阶**估计量并非非负，非负的是其总效应式）。修法是改这句措辞或改成"总效应非负"。
3. **findings X5（severity=low）**：§3.4(b) 称解析与有限差分"非零项相对差 < 5%"，而表5 中
   `geom_L` 的解析值 0.0008 vs 差分值 0.00067 相对差 **16.25%**。
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
| valid_json | ✅ | `pass` |
| schema_pass | ✅ | `True` |
| source_locator_resolvable | ✅ | `True` |
| source_hash_matches | ✅ | `True` |
| no_duplicate_ids | ✅ | `True` |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | `True` |
| detail_schema_kf_result | ✅ | `pass` |
| detail_schema_asset_manifest | ✅ | `pass` |

补充自证（不属于 acceptance，但本包自己加的）：`pytest tests/test_kf_wp11421_01.py` → **27 passed**
（含 8 条负控：篡改引文即被检出、位移区间即不匹配、异号 `report_id` 即 schema 失败、重复 id 即唯一性失败、
`"status":"verified"` 即触发断言）；`crosscheck.json` 7 项 fail=2 · pass=5。

**honest-FAIL 声明**：交叉复核 X4 / X5 两项判定为 **fail**（正文断言与其自身表格不符），
本包**不修改**报告原文、不重算生产结果、不把这两项写成"已解决"——它们作为缺陷候选移交给下游工序。
除此之外本包没有其它未达标项。

## 图（平台内嵌）

1. `fig1_asset_resolution.png`：22 条资产按类目 × 解析状态堆叠——
   一眼看出"能从本记录里真的取到什么"（11 条）与"只是指针"（10 条）的比例。
2. `fig2_locator_map.png`：22 条定位器投影在 18542 字符原文轴上并叠加章节边界——
   定位覆盖全文而非仅头部，红/灰块即"原文点名但本记录拿不到"的资产。
3. `fig3_fd_vs_analytic.png`：左 = X5 逐因子"解析 vs 差分"相对差（对数轴，虚线为报告自述的 5% 界）；
   右 = X4 的 6 个负一阶指数与 ±1 SE 误差棒（竖线为 0）。

"是否 <3%" 回答：本包不产出任何物理量，无基准误差可言；可对标的是**报告内部算术**——
X1 几何闭合 0.001920 vs 报告 0.0019197（差 <5e-7）、
X2 五行 CV 全部在 4 位小数舍入内、X3 Σ 列和最大偏差 1e-4、X6 8 行（4 档 ε × 2 口径）全在 σ 打印量化内、
X7 38.4995% vs 38.5%——**均 <3%**，
唯 X4/X5 不是数值精度问题而是措辞与表格冲突（见 §⑤-2/3）。

### repro_cmd（一键复跑，需 `TENSOR_AGENT_USER/PASS`）

```sh
python3 scripts/kf_wp11421_01_register.py  && python3 scripts/kf_wp11421_01_crosscheck.py  && python3 scripts/kf_wp11421_01_figures.py  && python3 scripts/kf_wp11421_01_report.py  && python3 -m pytest tests/test_kf_wp11421_01.py -q
```

交付信封（`package_id=wp-11421-01`, `task_type=01-asset-registration`, `report_id=11421`,
`provenance.source_hash=sha256:f85c29fe650365140152064807d90b2accdf43382f2222956470f3521e0a280a`）原样如下，此文件内**仅此一个** JSON 代码块：

```json
{
  "package_id": "wp-11421-01",
  "task_type": "01-asset-registration",
  "report_id": "11421",
  "provenance": {
    "source_hash": "sha256:f85c29fe650365140152064807d90b2accdf43382f2222956470f3521e0a280a",
    "source_field": "markdown",
    "producer": "scripts/kf_wp11421_01_register.py",
    "emitted_at": "2026-11-10T13:33:14.240943+00:00",
    "notes": "asset registration only; no extraction, no claim verification; hash recomputed from the fetched markdown UTF-8 bytes"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-11421-01",
      "task_type": "01-asset-registration",
      "report_id": "11421",
      "source": {
        "uri": "tensor://reports/11421",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "f85c29fe650365140152064807d90b2accdf43382f2222956470f3521e0a280a",
        "chars": 18542,
        "bytes_utf8": 26405,
        "title": "P270W1-N07 端到端不确定度传播：几何→阻力→推进→EEXI/CII 六因子分解（蒙特卡洛 + Sobol）",
        "scenario_key": "ship_performance",
        "platform_figures": [
          "fig1_eexi_pdf.png",
          "fig2_cii_pdf.png",
          "fig3_sobol_groups.png",
          "fig4_convergence.png",
          "fig5_sigma_control.png",
          "fig6_sensitivity.png"
        ],
        "platform_tags": [
          "EEXI",
          "CII",
          "不确定度传播",
          "蒙特卡洛",
          "Sobol",
          "green_shipping",
          "Holtrop",
          "defect_fix",
          "P270W1-N07"
        ]
      },
      "counts": {
        "assets": 22,
        "by_class": {
          "figure": 6,
          "artifact_path": 1,
          "data_table": 4,
          "source_code": 1,
          "module": 2,
          "api_function": 1,
          "test": 2,
          "config": 1,
          "machine_criteria": 1,
          "run_config": 1,
          "result_field": 1,
          "rule_reference": 1
        },
        "by_resolution": {
          "resolved_in_source": 11,
          "referenced_unresolved": 10,
          "declared_absent": 1
        },
        "resolved_in_source": 11,
        "referenced_unresolved": 10,
        "declared_absent": 1
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "figure",
          "label": "fig1_eexi_pdf.png — EEXI 达到值 PDF + 要求值竖线 + 5–95% 带 + 合规概率",
          "in_report_section": "§3.5 图",
          "locator": {
            "method": "char_span",
            "start_char": 10232,
            "end_char": 10293,
            "start_line": 260,
            "end_line": 260,
            "quote": "`fig1_eexi_pdf.png` | EEXI 达到值 PDF + 要求值竖线 + 5–95% 带 + 合规概率 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "figures[] name match=True; GET figures/fig1_eexi_pdf.png -> HTTP 200, 35000 B, PNG magic=True",
            "result": "resolved"
          },
          "note": "platform record figures[0]; name matched against figures[] of the report payload",
          "payload": {
            "probe": "GET /tensor/reports/<id>/figures/<name>",
            "http_status": 200,
            "bytes": 35000,
            "content_type": "image/png",
            "sha256": "4a0a017c83479d2433feba6d555045c220a63c0fd4ff1d033bf2b3ec4dbc5806",
            "png_magic": true,
            "fetched": true
          }
        },
        {
          "asset_id": "A02",
          "asset_class": "figure",
          "label": "fig2_cii_pdf.png — CII 同上（PDF/要求值/5–95% 带/合规概率）",
          "in_report_section": "§3.5 图",
          "locator": {
            "method": "char_span",
            "start_char": 10296,
            "end_char": 10325,
            "start_line": 261,
            "end_line": 261,
            "quote": "`fig2_cii_pdf.png` | CII 同上 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "figures[] name match=True; GET figures/fig2_cii_pdf.png -> HTTP 200, 34172 B, PNG magic=True",
            "result": "resolved"
          },
          "note": "platform record figures[1]; name match",
          "payload": {
            "probe": "GET /tensor/reports/<id>/figures/<name>",
            "http_status": 200,
            "bytes": 34172,
            "content_type": "image/png",
            "sha256": "da364aa95995095d3c68240e065a64305f590eafe85e0cc795e6085592f91504",
            "png_magic": true,
            "fetched": true
          }
        },
        {
          "asset_id": "A03",
          "asset_class": "figure",
          "label": "fig3_sobol_groups.png — 六因子组一阶/总效应 Sobol（EEXI、CII 双面板，带标准误）",
          "in_report_section": "§3.5 图",
          "locator": {
            "method": "char_span",
            "start_char": 10328,
            "end_char": 10391,
            "start_line": 262,
            "end_line": 262,
            "quote": "`fig3_sobol_groups.png` | 六因子组一阶/总效应 Sobol（EEXI、CII 双面板，带标准误） |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "figures[] name match=True; GET figures/fig3_sobol_groups.png -> HTTP 200, 59347 B, PNG magic=True",
            "result": "resolved"
          },
          "note": "platform record figures[2]; name match",
          "payload": {
            "probe": "GET /tensor/reports/<id>/figures/<name>",
            "http_status": 200,
            "bytes": 59347,
            "content_type": "image/png",
            "sha256": "1c586063596639415fe4c8425f03f61133689bca8811de7b7c90c7d517c60e4d",
            "png_magic": true,
            "fetched": true
          }
        },
        {
          "asset_id": "A04",
          "asset_class": "figure",
          "label": "fig4_convergence.png — 样本量收敛：σ 与合规概率 vs N",
          "in_report_section": "§3.5 图",
          "locator": {
            "method": "char_span",
            "start_char": 10394,
            "end_char": 10439,
            "start_line": 263,
            "end_line": 263,
            "quote": "`fig4_convergence.png` | 样本量收敛：σ 与合规概率 vs N |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "figures[] name match=True; GET figures/fig4_convergence.png -> HTTP 200, 42898 B, PNG magic=True",
            "result": "resolved"
          },
          "note": "platform record figures[3]; name match",
          "payload": {
            "probe": "GET /tensor/reports/<id>/figures/<name>",
            "http_status": 200,
            "bytes": 42898,
            "content_type": "image/png",
            "sha256": "62fe1b478b38596189d7da6a929803f0b5bd7dcc5df992c21e726cecbe3cf52a",
            "png_magic": true,
            "fetched": true
          }
        },
        {
          "asset_id": "A05",
          "asset_class": "figure",
          "label": "fig5_sigma_control.png — σ→0 负控：σ 比 vs ε + 概率阶跃",
          "in_report_section": "§3.5 图",
          "locator": {
            "method": "char_span",
            "start_char": 10442,
            "end_char": 10508,
            "start_line": 264,
            "end_line": 264,
            "quote": "`fig5_sigma_control.png` | σ→0 负控：σ 比 vs ε（对数-对数，斜率 1 参考线）+ 概率阶跃 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "figures[] name match=True; GET figures/fig5_sigma_control.png -> HTTP 200, 61521 B, PNG magic=True",
            "result": "resolved"
          },
          "note": "platform record figures[4]; name match",
          "payload": {
            "probe": "GET /tensor/reports/<id>/figures/<name>",
            "http_status": 200,
            "bytes": 61521,
            "content_type": "image/png",
            "sha256": "389eba0851bbedfd2a1886f556879f47a3919faba9ab753d00c19e2f3ea217fd",
            "png_magic": true,
            "fetched": true
          }
        },
        {
          "asset_id": "A06",
          "asset_class": "figure",
          "label": "fig6_sensitivity.png — 灵敏度结构：解析 δ 法 vs 有限差分 vs MC Sobol 三对照",
          "in_report_section": "§3.5 图",
          "locator": {
            "method": "char_span",
            "start_char": 10511,
            "end_char": 10574,
            "start_line": 265,
            "end_line": 265,
            "quote": "`fig6_sensitivity.png` | 灵敏度结构：解析 δ 法 vs 有限差分 vs MC Sobol 三对照 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "figures[] name match=True; GET figures/fig6_sensitivity.png -> HTTP 200, 54685 B, PNG magic=True",
            "result": "resolved"
          },
          "note": "platform record figures[5]; name match",
          "payload": {
            "probe": "GET /tensor/reports/<id>/figures/<name>",
            "http_status": 200,
            "bytes": 54685,
            "content_type": "image/png",
            "sha256": "ca46f8cea7138f0e1c1f5ee5fd2e731cb5d39911c7e3894fc8dc763ac584ec75",
            "png_magic": true,
            "fetched": true
          }
        },
        {
          "asset_id": "A07",
          "asset_class": "artifact_path",
          "label": "artifacts/P270W1-N07/{results.json, tables.md, fig1..fig6} — 生产者工件目录",
          "in_report_section": "§preamble 工件",
          "locator": {
            "method": "char_span",
            "start_char": 236,
            "end_char": 296,
            "start_line": 5,
            "end_line": 5,
            "quote": "`artifacts/P270W1-N07/{results.json, tables.md, fig1..fig6}`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "declared path resolvable inside the report payload (markdown/figures/record)? -> no",
            "result": "unresolved"
          },
          "note": "path declared in report; the files live in ship-performance-platform (producing repo), not in this report record -> not resolvable from tensor://reports/11421"
        },
        {
          "asset_id": "A08",
          "asset_class": "data_table",
          "label": "附录 A · 数字表（声明为 artifacts/P270W1-N07/tables.md 原文）",
          "in_report_section": "附录 A",
          "locator": {
            "method": "char_span",
            "start_char": 13210,
            "end_char": 13260,
            "start_line": 331,
            "end_line": 331,
            "quote": "## 附录 A · 数字表（`artifacts/P270W1-N07/tables.md` 原文）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "byte-identity check between appendix A and external tables.md possible? -> no",
            "result": "unresolved"
          },
          "note": "appendix says it reproduces tables.md verbatim; the 8 tables ARE inline (see A16) but byte-identity with the外部 tables.md cannot be checked from this record -> unresolved"
        },
        {
          "asset_id": "A09",
          "asset_class": "source_code",
          "label": "scripts/p270w1_n07_uncertainty.py — 生成全部数字的执行脚本",
          "in_report_section": "§preamble 执行脚本",
          "locator": {
            "method": "char_span",
            "start_char": 184,
            "end_char": 228,
            "start_line": 4,
            "end_line": 4,
            "quote": "**执行脚本**：`scripts/p270w1_n07_uncertainty.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file attached/resolvable from record? -> no",
            "result": "unresolved"
          },
          "note": "code pointer into ship-performance-platform; file not attached to the report record"
        },
        {
          "asset_id": "A10",
          "asset_class": "module",
          "label": "backend/modules/green_uq/ — UQ 模块（mc/sobol/spec）",
          "in_report_section": "§preamble 模块",
          "locator": {
            "method": "char_span",
            "start_char": 156,
            "end_char": 183,
            "start_line": 4,
            "end_line": 4,
            "quote": "`backend/modules/green_uq/`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "module sources attached/resolvable from record? -> no",
            "result": "unresolved"
          },
          "note": "module pointer; source not attached to the record"
        },
        {
          "asset_id": "A11",
          "asset_class": "module",
          "label": "backend/physics/holtrop — Holtrop-Mennen 唯一实现（R_T 求解器）",
          "in_report_section": "§2.1 确定性链",
          "locator": {
            "method": "char_span",
            "start_char": 2931,
            "end_char": 2982,
            "start_line": 74,
            "end_line": 74,
            "quote": "Holtrop-Mennen 唯一实现（backend/physics/holtrop）   [kN]",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "solver source attached/resolvable from record? -> no",
            "result": "unresolved"
          },
          "note": "Holtrop implementation pointer; the regression coefficients themselves are not in the record"
        },
        {
          "asset_id": "A12",
          "asset_class": "api_function",
          "label": "api/green_shipping: _gn_attained_index / _gn_attained_cii / _PowerChain / _gn_required_*",
          "in_report_section": "§2.1 纪律 1",
          "locator": {
            "method": "char_span",
            "start_char": 3681,
            "end_char": 3762,
            "start_line": 92,
            "end_line": 92,
            "quote": "`api/green_shipping` 的 `_gn_attained_index` / `_gn_attained_cii` / `_PowerChain`，",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "function bodies attached/resolvable from record? -> no",
            "result": "unresolved"
          },
          "note": "rule-formula single source reused by this node (判据 C1 证明同输入相对差 < 1e-9); function bodies not in the record"
        },
        {
          "asset_id": "A13",
          "asset_class": "test",
          "label": "test_chain.py::test_attained_index_unit_1852_fix — 1852 量纲回归测试",
          "in_report_section": "§2.3 缺陷修复",
          "locator": {
            "method": "char_span",
            "start_char": 5288,
            "end_char": 5372,
            "start_line": 125,
            "end_line": 125,
            "quote": "`test_chain.py::test_attained_index_unit_1852_fix`，相对差 < 1e-12，旧/新比值 = 1852 ± 1e-9）。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "test file attached/resolvable from record? -> no",
            "result": "unresolved"
          },
          "note": "regression test for the 1852 factor defect; test file not in the record"
        },
        {
          "asset_id": "A14",
          "asset_class": "test",
          "label": "test_green_shipping.py — 原有 18 条断言（只断言 idx > 0）",
          "in_report_section": "§2.3 缺陷修复",
          "locator": {
            "method": "char_span",
            "start_char": 5457,
            "end_char": 5513,
            "start_line": 127,
            "end_line": 127,
            "quote": "原有 18 条 `test_green_shipping.py` 断言（只断言 `idx > 0`）全部仍通过。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "test file attached/resolvable from record? -> no",
            "result": "unresolved"
          },
          "note": "pre-existing test suite quoted by count only; file not in the record"
        },
        {
          "asset_id": "A15",
          "asset_class": "config",
          "label": "green_uq spec.py — 13 成员六因子不确定度谱 + 逐因子 provenance",
          "in_report_section": "§1.3 不确定度谱",
          "locator": {
            "method": "char_span",
            "start_char": 1767,
            "end_char": 1785,
            "start_line": 45,
            "end_line": 45,
            "quote": "出处（`spec.py` 逐条） |",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "spec.py attached/resolvable from record? -> no",
            "result": "unresolved"
          },
          "note": "the 13-member spectrum table itself is inline (see A17); the spec.py provenance strings are not"
        },
        {
          "asset_id": "A16",
          "asset_class": "data_table",
          "label": "附录 A 表1–表8 数字表（程序化生成，勿手改）",
          "in_report_section": "附录 A",
          "locator": {
            "method": "char_span",
            "start_char": 13262,
            "end_char": 13289,
            "start_line": 333,
            "end_line": 333,
            "quote": "# P270W1-N07 数字表（程序化生成，勿手改）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "table block present verbatim in markdown? -> yes",
            "result": "resolved"
          },
          "note": "8 tables rendered inline in the appendix; each row is quotable from the markdown"
        },
        {
          "asset_id": "A17",
          "asset_class": "data_table",
          "label": "§1.3 六因子不确定度谱（13 个成员，分布/1σ/作用位置）",
          "in_report_section": "§1.3",
          "locator": {
            "method": "char_span",
            "start_char": 1713,
            "end_char": 1737,
            "start_line": 43,
            "end_line": 43,
            "quote": "### 1.3 六因子不确定度谱（13 个成员）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "table present verbatim in markdown? -> yes",
            "result": "resolved"
          },
          "note": "inline Markdown table; 13 rows of (group, member, distribution, 1σ, action site)"
        },
        {
          "asset_id": "A18",
          "asset_class": "machine_criteria",
          "label": "results.json -> criteria C1–C10 与 all_pass 判据块",
          "in_report_section": "§preamble 机器判据 / 附录 A 表8",
          "locator": {
            "method": "char_span",
            "start_char": 297,
            "end_char": 373,
            "start_line": 6,
            "end_line": 6,
            "quote": "**机器判据**：`artifacts/P270W1-N07/results.json → criteria`（C1–C10，含 `all_pass`）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "criteria block present verbatim in markdown? -> yes",
            "result": "resolved"
          },
          "note": "criteria block is reproduced inline as 表8 with all_pass = True; the producer-side results.json remains referenced_unresolved (A07)"
        },
        {
          "asset_id": "A19",
          "asset_class": "run_config",
          "label": "运行配置（n_mc / n_sobol / n_anchor / n_convergence / seed / workers）",
          "in_report_section": "附录 A 表头",
          "locator": {
            "method": "char_span",
            "start_char": 13322,
            "end_char": 13509,
            "start_line": 336,
            "end_line": 336,
            "quote": "配置：{\"n_mc\": 200000, \"n_sobol\": 32768, \"n_sobol_small\": 32768, \"n_anchor\": 65536, \"n_convergence\": [10000, 30000, 100000, 300000], \"n_sigma_control\": 8000, \"seed\": 20270101, \"workers\": 24}",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "config line present verbatim in markdown? -> yes",
            "result": "resolved"
          },
          "note": "seed and sample sizes are in the markdown -> the statistical results are re-runnable if the producer script (A09) is available"
        },
        {
          "asset_id": "A20",
          "asset_class": "result_field",
          "label": "results.json.monte_carlo.numerics.out_of_holtrop_domain — Holtrop 域外推比例",
          "in_report_section": "§4 注意点 5",
          "locator": {
            "method": "char_span",
            "start_char": 11382,
            "end_char": 11450,
            "start_line": 285,
            "end_line": 285,
            "quote": "`monte_carlo.numerics.out_of_holtrop_domain`）。这是**边界外推**而非失效：`Cp` 只经",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "field value resolvable from record? -> no (field name only)",
            "result": "unresolved"
          },
          "note": "only the field name is given; the numeric share is instead quoted in §3.2 (76999/200000)"
        },
        {
          "asset_id": "A21",
          "asset_class": "rule_reference",
          "label": "MEPC.328(76) / MEPC.353(78) 规则系数原文（要求值来源）",
          "in_report_section": "§1.2 要求值",
          "locator": {
            "method": "char_span",
            "start_char": 1657,
            "end_char": 1711,
            "start_line": 41,
            "end_line": 41,
            "quote": "（`WITHHELD`：系数转录自 MEPC.328(76)/MEPC.353(78)，离线不可回读原文）。",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "rule text attached/resolvable from record? -> no (declared WITHHELD)",
            "result": "absent"
          },
          "note": "report itself declares WITHHELD: no offline copy of the rule text; consequently the required values cannot be independently recomputed from this record"
        },
        {
          "asset_id": "A22",
          "asset_class": "data_table",
          "label": "§1.2 设计案例参数表（Kamsarmax 散货船 80 000 dwt）",
          "in_report_section": "§1.2",
          "locator": {
            "method": "char_span",
            "start_char": 890,
            "end_char": 928,
            "start_line": 26,
            "end_line": 26,
            "quote": "### 1.2 设计案例（Kamsarmax 散货船，80 000 dwt）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "table present verbatim in markdown? -> yes",
            "result": "resolved"
          },
          "note": "inline parameter table (L,B,T,Cb,Cm,Cp,displacement,DWT,MCR,SFOC,C_F,efficiencies,service speed)"
        }
      ],
      "claims": [],
      "claims_note": "Empty by contract: objective.classify_report_type=false and objective.extract_claims is not declared. No claim was generated to fill a quota; no claim is marked verified.",
      "integrity": {
        "quote_uniqueness": true,
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "duplicate_asset_ids": false,
        "locators_all_resolvable": true
      },
      "limits": [
        "Registration only. No numbers were re-derived; no statistic was recomputed from the producer artifacts (they are not in this record — see A07).",
        "Figures are resolved by NAME against the platform record's figures[]; the PNG bytes were not inspected, so figure content is not attested.",
        "Required values (EEXI_req / CII_req) depend on rule coefficients the report itself marks WITHHELD (A21); they are registered as declared_absent, not as verified inputs.",
        "Appendix A claims to be tables.md verbatim; byte-identity to the外部 file cannot be checked from this record and is left unresolved (A08)."
      ]
    }
  },
  "claims": []
}
```
