# KF-RESULT wp-10459-01

工作包 `wp-10459-01` · 工序 `01-asset-registration` · report_id **10459** · 分支 `agent/m15683` · 仓库 TensorKnowledge

## ① 本工序做了什么

把 report 10459 的**源资产登记**下来，不做抽取、不做验证：确认平台记录里 `markdown` 字段的字节内容与契约 `source_hash` 一致，再把报告中可解析的附件/工件逐条登记为资产，每条给可机器复算的定位（字符区间 + 行区间 + 逐字引文 + 唯一性）。

| 项 | 值 |
|---|---|
| report_id | 10459（本包只碰这一份） |
| source_uri | `tensor://reports/10459` |
| source_field | `markdown` |
| sha256(markdown, utf-8) | `08c1a0cfb3f0db38ad3a473ac2155001589bde91c1f85c21db1d29863ca84f6c` |
| chars / bytes_utf8 | 6431 / 9539 |
| 契约 source_hash 一致 | 是 |
| 契约 chars 一致 | 是（契约 6431） |
| 资产数 | 29（resolved_in_source 19 / referenced_unresolved 7 / declared_absent 3） |
| claims | 0（契约允许空数组：objective.classify_report_type=false，本工序不做抽取） |
| 是否标记 verified | 否（verification 由平台门计算） |

源报告主题：IN102-N03 四个 WITHHELD 工程量的双源一致性 + Sobol 敏感度 + 升级判决（波浪增阻 κ / 污损 / 风压系数 / 砰击峰值系数）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文并锁定字节**：`GET /api/v1/tensor/reports/10459`（Bearer 由 `TENSOR_AGENT_USER` 登录换得，不在脚本里写任何凭据），只取 `markdown` 字段；`sha256(md.encode('utf-8'))` 与契约 `08c1a0cf…4f6c` 比对，不一致则脚本直接退出、拒绝登记（防止基于另一份 payload 登记）。
2. **锚点定位、不是手抄**：每个资产在脚本里声明一个**锚点子串**，脚本断言它在 markdown 中**恰好出现 1 次**，再按声明的前后行偏移切出引文；随后独立复核 `md[start_char:end_char] == quote` 且 `md.count(quote)==1`，任一不成立即退出。行号由字符偏移反算（1-based）。
3. **三类解析状态，缺失就写缺失**：`resolved_in_source`（目标字节在源 markdown 内，或就是 markdown 本身）、`referenced_unresolved`（引用能定位、但目标在本 worktree / 平台记录里没有字节载荷，如外部仓代码文件、只有 name+caption 的图）、`declared_absent`（**报告自己声明**该物缺失/未做）。不发明地址、不补造内容。
4. **登记但不抽取**：`claims` 输出为空数组；没有把报告任何一句结论提升为本包结论，**未标 verified**。
5. **自检独立复算**：`scripts/kf_wp10459_validate.py` 不信任本地快照，重新从 API 取 markdown 再逐条复算验收项；manifest schema 用的是仓内 `schemas/asset_manifest.v1.schema.json`——它是 **report-bound** 的（`const` 钉死 wp-448-01/448/tensor://reports/448），自检器只重绑定这 3 个 const 并断言 schema 其余部分未改。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 大小 | 要点 |
|---|---|---|
| `artifacts/wp-10459-01/asset_manifest.json` | 45024 B | 契约声明的输出文件：29 资产 + structure_index + counts + integrity |
| `docs/kf/wp-10459-01/asset_manifest.json` | 45024 B | 同字节镜像（推送门会丢 artifacts/**，故落 docs/ 保活） |
| `docs/kf/wp-10459-01/kf_result.json` | 48629 B | `kf_result.v1` 信封（package_id/task_type/report_id/provenance/outputs） |
| `docs/kf/wp-10459-01/selfcheck.json` | 2819 B | 自检逐项结果：12/12 PASS |
| `docs/kf/wp-10459-01/fig_asset_coverage.png` | 187624 B | 图：资产定位区间覆盖图 + 类别×解析状态堆叠图 |
| `docs/reports/kf_wp_10459_01_result.md` | 本文件 | 报告正文（含唯一 json 代码块） |
| `runs/wp-10459-01/report_10459.md` | 9539 B | 平台 markdown 快照（逐字节，供复跑比对） |

### 资产登记表

| id | class | 报告位置 | 行区间 | 字符区间 | resolution | 检查要点 |
|---|---|---|---|---|---|---|
| A01 | document | document | 1–139 | 0–6431 | resolved_in_source | resolved |
| A02 | heading | title | 1–1 | 0–52 | resolved_in_source | resolved |
| A03 | statement | ① 案例介绍 | 5–7 | 81–205 | resolved_in_source | resolved |
| A04 | parameter_set | ① 案例介绍 | 9–11 | 207–340 | resolved_in_source | resolved |
| A05 | definition_table | ① 案例介绍 | 15–20 | 353–611 | resolved_in_source | resolved |
| A06 | method_spec | ② 怎么做的 | 24–27 | 639–917 | resolved_in_source | resolved |
| A07 | code_pointer | ② 怎么做的 | 26–26 | 818–853 | referenced_unresolved | unresolved |
| A08 | criterion | ② 怎么做的 | 28–29 | 918–1003 | resolved_in_source | resolved |
| A09 | numerical_setup | ② 怎么做的 | 30–32 | 1004–1143 | resolved_in_source | resolved |
| A10 | self_check | ② 怎么做的 | 33–33 | 1147–1192 | resolved_in_source | resolved |
| A11 | criterion | ② 怎么做的 | 34–35 | 1193–1268 | resolved_in_source | resolved |
| A12 | toolchain_declaration | ② 怎么做的 | 36–37 | 1269–1412 | resolved_in_source | resolved |
| A13 | code_pointer | ② 怎么做的 | 36–36 | 1302–1332 | referenced_unresolved | unresolved |
| A14 | code_pointer | ② 怎么做的 | 37–37 | 1349–1391 | referenced_unresolved | unresolved |
| A15 | result_table | ③ 计算结果 | 43–48 | 1446–2289 | resolved_in_source | resolved |
| A16 | verdict | ③ 计算结果 | 50–51 | 2291–2393 | resolved_in_source | resolved |
| A17 | result_table | ③ 计算结果 | 55–61 | 2412–2878 | resolved_in_source | resolved |
| A18 | provenance_table | ③ 计算结果 | 66–76 | 2895–4278 | resolved_in_source | resolved |
| A19 | derived_numbers | ③ 计算结果 | 79–90 | 4281–4650 | resolved_in_source | resolved |
| A20 | figure | ④ 结果图 | 94–94 | 4662–4702 | referenced_unresolved | unresolved |
| A21 | figure | ④ 结果图 | 95–95 | 4703–4760 | referenced_unresolved | unresolved |
| A22 | figure | ④ 结果图 | 96–96 | 4761–4812 | referenced_unresolved | unresolved |
| A23 | caveat_section | ⑤ 注意点 | 98–117 | 4814–5677 | resolved_in_source | resolved |
| A24 | caveat | ⑤ 注意点 | 101–101 | 4886–4919 | resolved_in_source | resolved |
| A25 | error_table | ⑥ 误差判定 | 121–131 | 5700–6132 | resolved_in_source | resolved |
| A26 | declared_absence | ⑥ 误差判定 | 137–137 | 6343–6359 | declared_absent | absent |
| A27 | declared_absence | ⑤ 注意点 | 105–105 | 5109–5149 | declared_absent | absent |
| A28 | declared_absence | ⑤ 注意点 | 114–114 | 5528–5536 | declared_absent | absent |
| A29 | metadata_field | ⑤ 注意点 | 113–113 | 5462–5492 | referenced_unresolved | unresolved |

## ④ 证据定位表（claim/字段 → 原文引文片段）

本工序不产出知识 claim（`claims=[]`），下表的每一行是一个**登记断言**：断言「原文在该位置逐字存在」。引文列为逐字前缀（超长标注截断），完整引文与字符偏移在 json 块的 `outputs.asset_manifest.json.assets[]` 里，可被平台独立复算。

| # | 登记断言（资产） | 原文引文片段（逐字） | 行 |
|---|---|---|---|
| 1 | A01 报告 markdown 全文（源资产本体） | ` # IN102-N03 四个 WITHHELD 工程量：双源一致性 × Sobol 敏感度 × 升级判决 ⏎   …(截断显示，全文见 json 块) ` | 1–139 |
| 2 | A02 报告 H1 标题行 | ` # IN102-N03 四个 WITHHELD 工程量：双源一致性 × Sobol 敏感度 × 升级判决 ` | 1–1 |
| 3 | A03 问题背景：四个工程量长期判 WITHHELD 的原因 | ` 平台能力台账里四个工程量长期判 **WITHHELD**：不是没有公式，而是只有一个来源、从未做过 ⏎ 区间一致 …(截断显示，全文见 json 块) ` | 5–7 |
| 4 | A04 参考船 KVLCC2 主尺度与工况参数 | ` 参考船 **KVLCC2**：L_pp=320.0 m, B=58.0 m, T=20.8 m, ⏎ C_b=0 …(截断显示，全文见 json 块) ` | 9–11 |
| 5 | A05 四量物理定义表（κ_aw / ΔP/P / C_X(0) / C_F） | ` \| 量 \| 定义 \| 单位 \| ⏎ \|---\|---\|---\| ⏎ \| 波浪增阻 κ_aw \ …(截断显示，全文见 json 块) ` | 15–20 |
| 6 | A06 参考资产数字化方法（EvidenceEntry 10 字段 + digest→公式→数值审计链） | `` 1. **参考资产数字化**：每个源 = `EvidenceEntry(source_id, citation, …(截断显示，全文见 json 块) `` | 24–27 |
| 7 | A07 实现文件 backend/modules/evidence_upgrade.py | ` backend/modules/evidence_upgrade.py ` | 26–26 |
| 8 | A08 双源一致性判据（重叠度 ≥ 0.7 判 CONSISTENT） | ` 2. **双源一致性**：重叠度 = \|A∩B\| / min(\|A\|,\|B\|)，≥ 0.7 判 ⏎  …(截断显示，全文见 json 块) ` | 28–29 |
| 9 | A09 Sobol 设置（Saltelli 2010 pick-freeze, n_base=512, 3584 次/量, 两套因子带） | `` 3. **Sobol 全局敏感度**：Saltelli(2010) pick-freeze，`n_base=51 …(截断显示，全文见 json 块) `` | 30–32 |
| 10 | A10 惰性因子 dummy_unused 实现自检 | `` 每个模型挂惰性因子 `dummy_unused` 作实现自检，实测 S_T=0.0000。 `` | 33–33 |
| 11 | A11 升级门判据（CONSISTENT 且 S_T>0.1 → REAL，否则维持 WITHHELD） | `` 4. **升级门**：`CONSISTENT 且 S_T(qty) > 0.1` → REAL，否则维持 ⏎   …(截断显示，全文见 json 块) `` | 34–35 |
| 12 | A12 工具链声明（纯 Python 无 numpy；pytest 35 用例；matplotlib 3.10.8 图件脚本） | `` 5. 工具链：纯 Python（无 numpy），`pytest tests/test_evidence_upg …(截断显示，全文见 json 块) `` | 36–37 |
| 13 | A13 测试文件 tests/test_evidence_upgrade.py（报告称 35 用例） | ` tests/test_evidence_upgrade.py ` | 36–36 |
| 14 | A14 图件脚本 artifacts/evidence_upgrade/make_figures.py | ` artifacts/evidence_upgrade/make_figures.py ` | 37–37 |
| 15 | A15 判据总表（4 量 × 双源值/带宽/点值差/重叠度/判决/S_T/等级） | ` \| 量 \| 源 A（值 [带]） \| 源 B（值 [带]） \| 点值相对差 \| 区间重叠度 \| 判决 …(截断显示，全文见 json 块) ` | 43–48 |
| 16 | A16 升级判决结论（2/4 通过；wave/fouling 维持 WITHHELD） | `` 升级判决：**2/4 通过** → `wind_coeff`, `slamming`； ⏎ 维持 WITHHEL …(截断显示，全文见 json 块) `` | 50–51 |
| 17 | A17 Sobol 敏感度排序表（设计工况 S_T 排序 + 惰性因子 S_T） | ` \| 量 \| 敏感度排序（S_T，设计工况） \| 惰性因子 S_T \| ⏎ \|---\|---\|--- …(截断显示，全文见 json 块) ` | 55–61 |
| 18 | A18 参考资产与审计链表（8 源：单位/有效域/带宽依据/provenance/sha256 前 16 位） | ` \| 量 \| 源 \| 单位 \| 有效域 \| 带宽依据 \| provenance \| sha256(前 …(截断显示，全文见 json 块) ` | 66–76 |
| 19 | A19 关键派生数字清单（交点 B/L=0.25、κ 17.4%、污损 8.90×、风压 6.4%、砰击 57.1%） | `` 关键派生数字（代码算出，可复算）： ⏎ * κ 两源解析交点：κ_A=κ_B ⇔ B/L=0.25（`sqrt( …(截断显示，全文见 json 块) `` | 79–90 |
| 20 | A20 图 1 双源区间与重叠度（四量） | ` * 图 1 双源区间与重叠度（四量）：源 A/源 B 带宽 + 点值 + 判决。 ` | 94–94 |
| 21 | A21 图 2 Sobol 总效应排序（设计工况，0.10 门线） | ` * 图 2 Sobol 总效应排序（设计工况），红线为被标定的量，虚线 0.10 门线；标题并列环境分布 S_T …(截断显示，全文见 json 块) ` | 95–95 |
| 22 | A22 图 3 波浪增阻 κ 随 B/L 两源曲线与解析交点 | ` * 图 3 波浪增阻 κ 随 B/L 的两源曲线与解析交点 B/L=0.25，KVLCC2 位置标注。 ` | 96–96 |
| 23 | A23 注意点全节（带宽敏感/声明带/环境稀释/模型形式/生长律/MC 噪声） | `` ## ⑤ 注意点（踩过的坑 / 局限 / 适用范围） ⏎  ⏎ * **判决对带宽敏感**：波浪量的 `band …(截断显示，全文见 json 块) `` | 98–117 |
| 24 | A24 判决对带宽敏感（band_scale_at_flip=1.1187，B/L=0.25 丰满船两源重合） | ` 1.1187，即两带同时放大到该倍数就从 INCONSISTENT ` | 101–101 |
| 25 | A25 误差判定表（8 判据 × 基准/实测/是否达标 + 升级数量） | ` \| 判据 \| 基准 / 参考 \| 实测 \| 是否达标 \| ⏎ \|---\|---\|---\|--- …(截断显示，全文见 json 块) ` | 121–131 |
| 26 | A26 外部基准数据缺失声明 | ` 无可用基准数据，故不声称 <3% ` | 137–137 |
| 27 | A27 OCIMF/Isherwood 数字化图表缺失声明 | ` OCIMF/Isherwood 数字化图表，风压的两源是两条**第一原理路线** ` | 105–105 |
| 28 | A28 污损船队统计标定未做声明 | ` 未做船队统计标定 ` | 114–114 |
| 29 | A29 报告自述的 JSON 字段 accuracy_caveat | `` `accuracy_caveat` 已显式写入报告 JSON `` | 113–113 |

## ⑤ 注意点与局限

* **登记 ≠ 验证**：`resolution` 只说明定位能否解析，`resolved_in_source` 不等于数值可信。报告里 4 个量的等级（2 REAL / 2 WITHHELD）、重叠度 0.661 与 0.000 两处 honest FAIL、S_T 数值一律**按原文登记**，本包未复核、未改判、未升格。
* **上游一处不一致已如实登记（A29）**：markdown 第 113 行自述 `accuracy_caveat` 已写入报告 JSON，但 `GET /tensor/reports/10459` 返回的顶层键为 id/title/summary/scenario_key/mission_id/stage/tags/figures/status/created_by/created_at/markdown，**无 accuracy_caveat**。本包不代写该字段，记为 `referenced_unresolved`，交上游/门处置。
* **3 个图件无字节**（A20–A22）：平台 `figures[]` 只有 name+caption，无 `png_base64`，故无字节可哈希，记为 `referenced_unresolved`；图题在 ④ 节可逐字定位。
* **3 个代码/测试/图件脚本不在本仓**（A07/A13/A14，`backend/modules/evidence_upgrade.py`、`tests/test_evidence_upgrade.py`、`artifacts/evidence_upgrade/make_figures.py`）：属船舶平台仓，本 worktree 内 `os.path.exists` 为假。报告自述「35 用例」「matplotlib 3.10.8」无法在此复核，只登记引用与其声明数。
* **A18 的 sha256 只有前 16 位**（原文如此），完整摘要不可由该表恢复；登记为截断摘要，不外推、不复原。
* **schema 局限**：仓内 `schemas/asset_manifest.v1.schema.json` 的 `const` 把 package_id/report_id/uri 钉在 wp-448-01/448 上，任何别的包都无法用它直接通过校验。本包用「只重绑定 3 个 const + 断言其余未改」的方式复用该 schema（见自检 `schema_pass` 详情），**未修改该文件**（它属上游 wp-448 产物）。若平台侧 schema 与此形态不同，以平台门为准。
* **本包不做的事**：不重算报告数字、不重建图件、不读其它 report_id、不 push、不改 .git 配置。

## ⑥ 自检（逐条对照 acceptance）

| acceptance / 约束 | 结果 | 复算依据 |
|---|---|---|
| valid\_json | PASS | kf_result.json / asset_manifest.json (docs + artifacts) parsed |
| schema\_pass | PASS | kf_result.v1 (Draft2020-12) + asset_manifest.v1 (Draft-07, report-bound consts rebound: properties.package_id.const: 'wp-448-01' -> 'wp-10459-01', properties.report_id.const: '448' -> '10459', properties.source.propertie |
| docs\_artifacts\_byte\_identical | PASS | docs/kf mirror vs contract output file byte-identical |
| source\_hash\_matches | PASS | fresh sha256=08c1a0cfb3f0db38...; contract=08c1a0cfb3f0db38...; provenance=08c1a0cfb3f0db38...; manifest=08c1a0cfb3f0db38...; chars=6431 (contract 6431); source=re-fetched from API |
| source\_locator\_resolvable | PASS | 29/29 quotes reproduce their char span verbatim in the re-fetched markdown and are unique |
| no\_duplicate\_ids | PASS | 29 asset_ids unique=True; 0 claim_ids unique=True |
| counts\_consistent | PASS | sum(by_class)=29 sum(by_resolution)=29 assets=29 len(assets)=29 |
| all\_claims\_have\_evidence\_or\_explicit\_unresolved\_status | PASS | envelope claims=0, manifest claims=0 -> vacuous pass (no claim generation by contract); objective.classify_report_type=false |
| do\_not\_mark\_claims\_as\_verified | PASS | no claim has a verified status (no claims at all); no asset resolution/check string contains 'verified' |
| do\_not\_invent\_missing\_information | PASS | every one of the 29 assets carries a non-empty resolution_check.check and note (unresolved/absent targets are named as such, never given an invented address) |
| preserve\_uncertainty | PASS | resolution and resolution_check.result agree on all assets; uncertainty/failure text kept verbatim in A23/A25/A26 (honest FAIL 0.661/0.000 preserved, not smoothed) |
| scope\_report\_10459\_only | PASS | package_id=wp-10459-01 report_id=10459 source=tensor://reports/10459 (no other report touched by this package) |

**自检结论：12/12 PASS，VERDICT PASS。** 失败项：无。

### 误差判定（关键量 vs 基准，是否 <3%）

本工序是**登记类**工序，没有物理关键量，因此**不声称任何物理量 <3%**（无基准可比，也无权代替上游判定）。可精确复算的量只有三个，均为确定性判定而非统计误差：

| 量 | 判据 | 实测 | 误差 | 是否达标 |
|---|---|---|---|---|
| sha256(markdown) | 与契约 `08c1a0cfb3f0db38…` 逐字相等 | `08c1a0cfb3f0db38…` | 0（字节级相等） | 是 |
| 定位可解析率 | 每条引文重现其字符区间且全文唯一 | 29/29 | 0 | 是 |
| counts 自洽 | Σby_class = Σby_resolution = assets | 29 / 29 / 29 | 0 | 是 |

## repro_cmd（一键复跑）

```bash
cd <worktree>   # TensorKnowledge, branch agent/m15683
python3 scripts/kf_wp10459_fetch.py            # 取 report 10459 markdown，校验 sha256 == 契约
python3 scripts/kf_wp10459_register_assets.py  # 重建 asset_manifest.json + kf_result.json
python3 scripts/kf_wp10459_validate.py         # 重新取原文，逐条复算 acceptance（期望 VERDICT PASS）
python3 scripts/kf_wp10459_figures.py          # 重建覆盖图
python3 scripts/kf_wp10459_report.py --dry-run # 只合成报告，不发布
```

环境：纯 Python 3 + `jsonschema` + `matplotlib`；凭据仅从 env `TENSOR_API_BASE` / `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS` 读取。

## 结果 JSON（唯一一个 json 代码块，平台门按此校验）

```json
{
  "package_id": "wp-10459-01",
  "task_type": "01-asset-registration",
  "report_id": "10459",
  "provenance": {
    "source_hash": "sha256:08c1a0cfb3f0db38ad3a473ac2155001589bde91c1f85c21db1d29863ca84f6c",
    "source_field": "markdown",
    "producer": "scripts/kf_wp10459_register_assets.py",
    "emitted_at": "2026-11-12T01:44:41.938448+00:00",
    "notes": "asset registration only; claims empty by contract; no verification marks"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "manifest_version": "1.0",
      "package_id": "wp-10459-01",
      "task_type": "01-asset-registration",
      "report_id": "10459",
      "objective": {
        "register_assets": true,
        "classify_report_type": false
      },
      "generated_at": "2026-11-12T01:44:41.938448+00:00",
      "source": {
        "uri": "tensor://reports/10459",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "08c1a0cfb3f0db38ad3a473ac2155001589bde91c1f85c21db1d29863ca84f6c",
        "hash_scope": "markdown encoded as utf-8",
        "chars": 6431,
        "bytes_utf8": 9539,
        "title": "IN102-N03 四个 WITHHELD 工程量的双源一致性 + Sobol 敏感度 + 升级判决（波浪增阻 κ / 污损 / 风压系数 / 砰击峰值系数）",
        "scenario_key": "ship_performance/evidence_upgrade/in102_n03",
        "mission_id": 8999,
        "status": "published",
        "created_at": "2026-11-10T06:27:25.051804+00:00",
        "platform_figures": [
          {
            "name": "fig1_source_intervals.png",
            "caption": "图 1 四个量的双源区间与重叠度（KVLCC2，阈值 0.70）：蓝=源 A，橙=源 B，黑点=点值。"
          },
          {
            "name": "fig2_sobol_total_effect.png",
            "caption": "图 2 Sobol 总效应指数排序（设计工况），红色为被标定量的因子，虚线为 0.10 门线；标题并列环境分布下的 S_T 以披露稀释效应。"
          },
          {
            "name": "fig3_wave_crossover.png",
            "caption": "图 3 波浪增阻系数两源随 B/L 的变化：STAWAVE-1 √(B/L)（±25%）与全反射动量界 1/2（±20%），解析交点 B/L=0.25，KVLCC2（0.181）处两源系统分岔。"
          }
        ],
        "platform_tags": [
          "IN102-N03",
          "evidence_grade",
          "withheld",
          "sobol",
          "dual-source",
          "wave_added_resistance",
          "fouling",
          "wind_coefficient",
          "slamming"
        ],
        "fetched_via": "GET /api/v1/tensor/reports/10459",
        "generator": "scripts/kf_wp10459_register_assets.py"
      },
      "resolution_vocabulary": {
        "resolved_in_source": "target bytes are inside the source markdown (or are the markdown itself); locator resolves to an exact slice/hash",
        "referenced_unresolved": "reference located in the markdown, but the target (file/figure bytes/JSON field) has no payload in this worktree or platform record -- nothing invented",
        "declared_absent": "the report itself declares the target to be absent/not done; registered as an explicit absence",
        "note": "resolution says nothing about truth or verification; no item here is marked verified"
      },
      "structure_index": {
        "note": "headings only, for downstream-工序 locator scaffolding; no content extracted here",
        "headings": [
          {
            "level": 1,
            "text": "IN102-N03 四个 WITHHELD 工程量：双源一致性 × Sobol 敏感度 × 升级判决",
            "line_no": 1
          },
          {
            "level": 2,
            "text": "① 案例介绍（物理背景 / 几何 / 参数）",
            "line_no": 3
          },
          {
            "level": 2,
            "text": "② 怎么做的（方法 / 流程 / 工具链）",
            "line_no": 22
          },
          {
            "level": 2,
            "text": "③ 计算结果（数字表，程序化注入）",
            "line_no": 39
          },
          {
            "level": 3,
            "text": "判据总表",
            "line_no": 41
          },
          {
            "level": 3,
            "text": "Sobol 敏感度排序",
            "line_no": 53
          },
          {
            "level": 3,
            "text": "参考资产与审计链",
            "line_no": 64
          },
          {
            "level": 2,
            "text": "④ 结果图",
            "line_no": 92
          },
          {
            "level": 2,
            "text": "⑤ 注意点（踩过的坑 / 局限 / 适用范围）",
            "line_no": 98
          },
          {
            "level": 2,
            "text": "⑥ 误差判定（vs 基准，逐项）",
            "line_no": 119
          }
        ]
      },
      "counts": {
        "assets": 29,
        "by_class": {
          "document": 1,
          "heading": 1,
          "statement": 1,
          "parameter_set": 1,
          "definition_table": 1,
          "method_spec": 1,
          "code_pointer": 3,
          "criterion": 2,
          "numerical_setup": 1,
          "self_check": 1,
          "toolchain_declaration": 1,
          "result_table": 2,
          "verdict": 1,
          "provenance_table": 1,
          "derived_numbers": 1,
          "figure": 3,
          "caveat_section": 1,
          "caveat": 1,
          "error_table": 1,
          "declared_absence": 3,
          "metadata_field": 1
        },
        "by_resolution": {
          "resolved_in_source": 19,
          "referenced_unresolved": 7,
          "declared_absent": 3
        },
        "resolved_in_source": 19,
        "referenced_unresolved": 7,
        "declared_absent": 3,
        "claims": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "document",
          "label": "报告 markdown 全文（源资产本体）",
          "in_report_section": "document",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 6431,
            "start_line": 1,
            "end_line": 139,
            "quote": "# IN102-N03 四个 WITHHELD 工程量：双源一致性 × Sobol 敏感度 × 升级判决\n\n## ① 案例介绍（物理背景 / 几何 / 参数）\n\n平台能力台账里四个工程量长期判 **WITHHELD**：不是没有公式，而是只有一个来源、从未做过\n区间一致性检验、也没量过它在总体性能响应里的权重。本节点为它们建立可复算的标定与升级\n判决，使 `WITHHELD → REAL` 有机器可裁依据。\n\n参考船 **KVLCC2**：L_pp=320.0 m, B=58.0 m, T=20.8 m,\nC_b=0.8098, V_s=7.97 m/s, Re=2.10e+09, B/L=0.1812；\n水线以上 A_F=700.0 m², A_L=2500.0 m²。\n\n四个量的物理定义：\n\n| 量 | 定义 | 单位 |\n|---|---|---|\n| 波浪增阻 κ_aw | R_AW = κ_aw·ρ g ζ_a² B，ζ_a = H_s/4 | – |\n| 污损 ΔP/P | 生长律 k_s=v·t → ΔC_F(k_s) → 功率链 100·n·f_fric·ΔC_F/C_F0 | % |\n| 风压系数 C_X(0) | F_wind,x = ½ ρ_air C_X A_F V² | – |\n| 砰击 C_F | C_F = F'/(½ ρ V²·2c)，二维楔形入水 β=30° | – |\n\n## ② 怎么做的（方法 / 流程 / 工具链）\n\n1. **参考资产数字化**：每个源 = `EvidenceEntry(source_id, citation, formula, unit,\n   validity_domain, value, band_lo, band_hi, band_basis, provenance_class)`，对规范化\n   JSON 取 `sha256`。数值全部由 `backend/modules/evidence_upgrade.py` 的代码从公式算出，\n   **无一处手抄** —— 审计链是 `digest → 公式 → 数值`（下表给出前 16 位）。\n2. **双源一致性**：重叠度 = |A∩B| / min(|A|,|B|)，≥ 0.7 判\n   CONSISTENT。用区间而非点值，避免把\"带内不同\"误判成矛盾。\n3. **Sobol 全局敏感度**：Saltelli(2010) pick-freeze，`n_base=512`，\n   每量模型求值 3584 次；输入 uniform。\n   因子带分两套并列披露：**设计工况**（过门用）与**环境分布**（把海况/风况当随机变量）。\n   每个模型挂惰性因子 `dummy_unused` 作实现自检，实测 S_T=0.0000。\n4. **升级门**：`CONSISTENT 且 S_T(qty) > 0.1` → REAL，否则维持\n   WITHHELD 并输出缺失证据清单。\n5. 工具链：纯 Python（无 numpy），`pytest tests/test_evidence_upgrade.py`（35 用例）+ 图件\n   `artifacts/evidence_upgrade/make_figures.py`（matplotlib 3.10.8）。\n\n## ③ 计算结果（数字表，程序化注入）\n\n### 判据总表\n\n| 量 | 源 A（值 [带]） | 源 B（值 [带]） | 点值相对差 | 区间重叠度 | 判决 | S_T(设计) | S_T(环境) | 等级 |\n|---|---|---|---|---|---|---|---|---|\n| `wave_add_resistance` (-) | stawave1_longwave: 0.4257 [0.3193, 0.5322] | full_reflection_momentum: 0.5 [0.4, 0.6] | 17.4% | 0.661 | **INCONSISTENT** | 0.706 | 0.209 | **WITHHELD** |\n| `fouling` (%) | townsin2003_fouling_chain: 4.142 [3.314, 4.97] | ittc78_roughness_allowance_chain: 36.87 [29.5, 44.24] | 790.2% | 0.000 | **INCONSISTENT** | 0.990 | 0.937 | **WITHHELD** |\n| `wind_coeff` (-) | bluff_body_drag_3d: 0.9 [0.792, 1.008] | flat_plate_normal_relief: 0.8424 [0.716, 0.9688] | 6.4% | 0.818 | **CONSISTENT** | 0.414 | 0.052 | **REAL** |\n| `slamming` (-) | vonkarman_momentum_analytic: 10.88 [9.577, 12.19] | momentum_numerical_timestep: 10.88 [10.77, 10.99] | 0.0% | 1.000 | **CONSISTENT** | 0.197 | 0.011 | **REAL** |\n\n升级判决：**2/4 通过** → `wind_coeff`, `slamming`；\n维持 WITHHELD：`wave_add_resistance`, `fouling`（验收线要求 ≥2，满足）。\n\n### Sobol 敏感度排序\n\n| 量 | 敏感度排序（S_T，设计工况） | 惰性因子 S_T |\n|---|---|---|\n\n| `wave_add_resistance` | kappa_aw=0.706, hs=0.291, b=0.001, rho=0.000, dummy_unused=0.000 | 0.0000 |\n| `fouling` | dP_over_P=0.990, f_fric=0.008, n_power=0.007, roughness_scatter=0.004, dummy_unused=0.000 | 0.0000 |\n| `wind_coeff` | v_wind=0.545, cx0=0.414, a_f=0.036, rho_air=0.006, dummy_unused=0.000 | 0.0000 |\n| `slamming` | v_entry=0.743, cf_slam=0.197, beta_deg=0.049, rho=0.000, dummy_unused=0.000 | 0.0000 |\n\n\n### 参考资产与审计链\n\n| 量 | 源 | 单位 | 有效域 | 带宽依据 | provenance | sha256(前 16) |\n|---|---|---|---|---|---|---|\n\n| `wave_add_resistance` | stawave1_longwave | - | lambda_p >= L_pp 的长波迎浪；R_AW = kappa*rho*g*zeta_a^2*B, zeta_a=Hs/4 | literature_spread | literature_closed_form | `b30f4651e3c00fbf` |\n| `wave_add_resistance` | full_reflection_momentum | - | lambda_p >> L_pp，深度弗劳德效应可忽略的深水长波 | declared_engineering_band | first_principles | `982788e4f2ac6db5` |\n| `fouling` | townsin2003_fouling_chain | % | ks=192.0 um @ 24 月（v=8.0 um/月 声明生长律），nt=3.0, f_fric=0.70 | declared_engineering_band | literature_closed_form | `0de72cbfc715c3b3` |\n| `fouling` | ittc78_roughness_allowance_chain | % | ks=192.0 um @ 24 月，同一 n/f_fric 链（隔离粗糙度函数差异） | declared_engineering_band | literature_closed_form | `a78539de43ff6a39` |\n| `wind_coeff` | bluff_body_drag_3d | - | psi=0 顶风，上层建筑+船体水下以上钝体外形，Re_air 1e7~1e8 | declared_engineering_band | first_principles | `9fa5d384596bcad9` |\n| `wind_coeff` | flat_plate_normal_relief | - | psi=0 顶风；把正投影面视为法向平板并做顶部泄流折减 | declared_engineering_band | first_principles | `642f72db934c1d47` |\n| `slamming` | vonkarman_momentum_analytic | - | beta=30 deg 刚性楔形、不可压、无空气垫、V 恒定 | declared_engineering_band | first_principles | `4015f3ef5ec10400` |\n| `slamming` | momentum_numerical_timestep | - | beta=30 deg，t_ref=0.05 s，dt=1e-5 s | numerical_discretisation | numerical_route | `2f40a28359cd84e3` |\n\n\n关键派生数字（代码算出，可复算）：\n* κ 两源解析交点：κ_A=κ_B ⇔ B/L=0.25（`sqrt(0.25)==0.5`，测试以 1e-12 密度钉住）；\n  KVLCC2 B/L=0.1812 ⇒ κ_A=0.4257 vs κ_B=0.5，\n  点值差 17.4%，重叠 0.661 < 0.70。\n* 污损：k_s=192.0 um；\n  Townsin 链 4.14 % vs ITTC-78 链 36.87 %\n  （比值 8.90），重叠 0.000。\n* 风压：两路 0.9000 vs 0.8424（差\n  6.4%），重叠 0.818。\n* 砰击：解析 10.8828 vs 独立数值 10.8828，\n  重叠 1.000；模型形式分歧（von Karman vs Wagner）\n  57.1% 单列披露。\n\n## ④ 结果图\n\n* 图 1 双源区间与重叠度（四量）：源 A/源 B 带宽 + 点值 + 判决。\n* 图 2 Sobol 总效应排序（设计工况），红线为被标定的量，虚线 0.10 门线；标题并列环境分布 S_T。\n* 图 3 波浪增阻 κ 随 B/L 的两源曲线与解析交点 B/L=0.25，KVLCC2 位置标注。\n\n## ⑤ 注意点（踩过的坑 / 局限 / 适用范围）\n\n* **判决对带宽敏感**：波浪量的 `band_scale_at_flip` =\n  1.1187，即两带同时放大到该倍数就从 INCONSISTENT\n  翻成 CONSISTENT；且 B/L=0.25 的丰满船两源解析重合（CONSISTENT）。故判决不是\"船型无关的\n  真理\"，而是\"KVLCC2 级细长船上的分歧\"。未以挑船型的方式让判决好看（两船型都写进测试）。\n* **带宽多为声明带**：`literature_spread` 与 `declared_engineering_band` 逐条标注；本仓没有\n  OCIMF/Isherwood 数字化图表，风压的两源是两条**第一原理路线**（钝体三维折减 / 法向平板+泄流），\n  不是文献回归表 —— 这是升级的真实弱点，报告不粉饰。\n* **环境分布下系数被淹没**：wind S_T 由 0.414（设计）降到\n  0.052（环境）；slamming 由\n  0.197 降到 0.011（env_diluted=True）。\n  含义：标定系数降低的是**系统偏差**，环境散布决定**响应出现频率**，两者不可互相替代。\n* **砰击的 REAL 只是\"算法真实+双路线可复算\"**：一致性覆盖实现（解析 vs 数值时间步进 +\n  动能功率份额不变量=1），不覆盖模型形式（π/2 差）。实测峰值一般落在两理论之间，\n  精度须试验压力/力记录，故 `accuracy_caveat` 已显式写入报告 JSON。\n* **污损生长律是声明的线性律**（v=8 μm/月，24 月），未做船队统计标定；两源共享功率链，\n  差异纯由粗糙度函数标定数据集引起 —— 这正是文献分歧，不是实现 bug。\n* Sobol MC 噪声：主因子 ±0.03、小指数 ±0.05（n_base=512，无 bootstrap），\n  故只对 0.10 门线与\"主因子 vs 惰性因子\"作强结论。\n\n## ⑥ 误差判定（vs 基准，逐项）\n\n| 判据 | 基准 / 参考 | 实测 | 是否达标 |\n|---|---|---|---|\n| 双源重叠度（波浪） | ≥0.7 | 0.661 | 否（INCONSISTENT，honest FAIL） |\n| 双源重叠度（污损） | ≥0.7 | 0.000 | 否（两 published 粗糙度函数差 8.9×） |\n| 双源重叠度（风压） | ≥0.7 | 0.818 | 是 |\n| 双源重叠度（砰击） | ≥0.7 | 1.000 | 是（verification 级） |\n| 敏感度（风压/砰击） | S_T>0.1 | 0.414 / 0.197 | 是 |\n| 惰性因子自检 | S_T≈0 | 0.0000 | 是 |\n| 解析恒等式 κ(0.25)=0.5 | 精确 | 相对误差 0（测试 1e-12） | 是 |\n| 砰击数值-解析 | 相对 <1e-6 | 实测 <1e-9 | 是 |\n| 升级数量 | ≥2 | 2 | 是 |\n\n**关键量 vs 基准误差是否 <3%？** —— 分两类如实回答：\n* **可精确复算的量**（κ=√(B/L)、κ_moment=1/2、C_F=2π/tanβ、ΔC_F、C_F0）：相对误差 0\n  （代码同一公式，测试逐位钉住），**<3% 是**，但这只证明\"命名方法自洽\"，不是对试验的精度。\n* **对照外部基准的量**（波浪增阻 vs 模型试验、砰击压力 vs 实测、污损 vs 船队数据）：\n  **无可用基准数据，故不声称 <3%**；两个量因此维持 WITHHELD，砰击/风压的 REAL 亦带\n  `accuracy_caveat`。这是本节点的诚实结论，不是遗漏。\n",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256(markdown.encode('utf-8')) recomputed locally",
            "result": "resolved"
          },
          "note": "chars=6431 / bytes_utf8=9539；哈希见 source.hash，与契约 source_hash 逐字一致。仅登记字节，不做抽取。"
        },
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "报告 H1 标题行",
          "in_report_section": "title",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 52,
            "start_line": 1,
            "end_line": 1,
            "quote": "# IN102-N03 四个 WITHHELD 工程量：双源一致性 × Sobol 敏感度 × 升级判决",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "anchor line located in markdown",
            "result": "resolved"
          },
          "note": "H1 文本与 API title 字段不同写法（API title 带“+ …（波浪增阻 κ / 污损 / 风压系数 / 砰击峰值系数）”括注）；两处均原文登记，未做统一改写。"
        },
        {
          "asset_id": "A03",
          "asset_class": "statement",
          "label": "问题背景：四个工程量长期判 WITHHELD 的原因",
          "in_report_section": "① 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 81,
            "end_char": 205,
            "start_line": 5,
            "end_line": 7,
            "quote": "平台能力台账里四个工程量长期判 **WITHHELD**：不是没有公式，而是只有一个来源、从未做过\n区间一致性检验、也没量过它在总体性能响应里的权重。本节点为它们建立可复算的标定与升级\n判决，使 `WITHHELD → REAL` 有机器可裁依据。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "anchor line located in markdown",
            "result": "resolved"
          },
          "note": "三行原文；“只有一个来源、从未做过区间一致性检验”是报告自述的缺口，不是本包结论。"
        },
        {
          "asset_id": "A04",
          "asset_class": "parameter_set",
          "label": "参考船 KVLCC2 主尺度与工况参数",
          "in_report_section": "① 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 207,
            "end_char": 340,
            "start_line": 9,
            "end_line": 11,
            "quote": "参考船 **KVLCC2**：L_pp=320.0 m, B=58.0 m, T=20.8 m,\nC_b=0.8098, V_s=7.97 m/s, Re=2.10e+09, B/L=0.1812；\n水线以上 A_F=700.0 m², A_L=2500.0 m²。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "anchor line located in markdown",
            "result": "resolved"
          },
          "note": "两行原文（L_pp/B/T/C_b/V_s/Re/B/L、A_F/A_L）。数值仅登记，不在此处复算或换算。"
        },
        {
          "asset_id": "A05",
          "asset_class": "definition_table",
          "label": "四量物理定义表（κ_aw / ΔP/P / C_X(0) / C_F）",
          "in_report_section": "① 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 353,
            "end_char": 611,
            "start_line": 15,
            "end_line": 20,
            "quote": "| 量 | 定义 | 单位 |\n|---|---|---|\n| 波浪增阻 κ_aw | R_AW = κ_aw·ρ g ζ_a² B，ζ_a = H_s/4 | – |\n| 污损 ΔP/P | 生长律 k_s=v·t → ΔC_F(k_s) → 功率链 100·n·f_fric·ΔC_F/C_F0 | % |\n| 风压系数 C_X(0) | F_wind,x = ½ ρ_air C_X A_F V² | – |\n| 砰击 C_F | C_F = F'/(½ ρ V²·2c)，二维楔形入水 β=30° | – |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "table header located + span sliced verbatim",
            "result": "resolved"
          },
          "note": "表头+分隔行+4 行公式定义；公式仅登记，本包不做实现核对。"
        },
        {
          "asset_id": "A06",
          "asset_class": "method_spec",
          "label": "参考资产数字化方法（EvidenceEntry 10 字段 + digest→公式→数值审计链）",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 639,
            "end_char": 917,
            "start_line": 24,
            "end_line": 27,
            "quote": "1. **参考资产数字化**：每个源 = `EvidenceEntry(source_id, citation, formula, unit,\n   validity_domain, value, band_lo, band_hi, band_basis, provenance_class)`，对规范化\n   JSON 取 `sha256`。数值全部由 `backend/modules/evidence_upgrade.py` 的代码从公式算出，\n   **无一处手抄** —— 审计链是 `digest → 公式 → 数值`（下表给出前 16 位）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "anchor line located in markdown",
            "result": "resolved"
          },
          "note": "四行原文；代码指针本体单列 A07。"
        },
        {
          "asset_id": "A07",
          "asset_class": "code_pointer",
          "label": "实现文件 backend/modules/evidence_upgrade.py",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 818,
            "end_char": 853,
            "start_line": 26,
            "end_line": 26,
            "quote": "backend/modules/evidence_upgrade.py",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists('backend/modules/evidence_upgrade.py') in this worktree (TensorKnowledge)",
            "result": "unresolved"
          },
          "note": "文件不属于本仓（属船舶平台仓），worktree 内不存在，故仅登记引用不登记内容；不伪造路径内容或哈希。"
        },
        {
          "asset_id": "A08",
          "asset_class": "criterion",
          "label": "双源一致性判据（重叠度 ≥ 0.7 判 CONSISTENT）",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 918,
            "end_char": 1003,
            "start_line": 28,
            "end_line": 29,
            "quote": "2. **双源一致性**：重叠度 = |A∩B| / min(|A|,|B|)，≥ 0.7 判\n   CONSISTENT。用区间而非点值，避免把\"带内不同\"误判成矛盾。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "anchor line located in markdown",
            "result": "resolved"
          },
          "note": "含重叠度定义式 |A∩B|/min(|A|,|B|) 原文；判据阈值 0.7 后续在 ③ 表与 ⑥ 表被引用。"
        },
        {
          "asset_id": "A09",
          "asset_class": "numerical_setup",
          "label": "Sobol 设置（Saltelli 2010 pick-freeze, n_base=512, 3584 次/量, 两套因子带）",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1004,
            "end_char": 1143,
            "start_line": 30,
            "end_line": 32,
            "quote": "3. **Sobol 全局敏感度**：Saltelli(2010) pick-freeze，`n_base=512`，\n   每量模型求值 3584 次；输入 uniform。\n   因子带分两套并列披露：**设计工况**（过门用）与**环境分布**（把海况/风况当随机变量）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "anchor line located in markdown",
            "result": "resolved"
          },
          "note": "三行原文；设计工况/环境分布两套因子带并列披露的说明在此。"
        },
        {
          "asset_id": "A10",
          "asset_class": "self_check",
          "label": "惰性因子 dummy_unused 实现自检",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1147,
            "end_char": 1192,
            "start_line": 33,
            "end_line": 33,
            "quote": "每个模型挂惰性因子 `dummy_unused` 作实现自检，实测 S_T=0.0000。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring located + uniqueness asserted",
            "result": "resolved"
          },
          "note": "单行原文；这是报告的实现自检声明，本包不重算其数值。"
        },
        {
          "asset_id": "A11",
          "asset_class": "criterion",
          "label": "升级门判据（CONSISTENT 且 S_T>0.1 → REAL，否则维持 WITHHELD）",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1193,
            "end_char": 1268,
            "start_line": 34,
            "end_line": 35,
            "quote": "4. **升级门**：`CONSISTENT 且 S_T(qty) > 0.1` → REAL，否则维持\n   WITHHELD 并输出缺失证据清单。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "anchor line located in markdown",
            "result": "resolved"
          },
          "note": "两行原文；升级判决的机器可裁规则。本包不执行判决，只登记判据文本。"
        },
        {
          "asset_id": "A12",
          "asset_class": "toolchain_declaration",
          "label": "工具链声明（纯 Python 无 numpy；pytest 35 用例；matplotlib 3.10.8 图件脚本）",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1269,
            "end_char": 1412,
            "start_line": 36,
            "end_line": 37,
            "quote": "5. 工具链：纯 Python（无 numpy），`pytest tests/test_evidence_upgrade.py`（35 用例）+ 图件\n   `artifacts/evidence_upgrade/make_figures.py`（matplotlib 3.10.8）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "anchor line located in markdown",
            "result": "resolved"
          },
          "note": "两行原文；两个被引用的脚本本体单列 A13/A14。"
        },
        {
          "asset_id": "A13",
          "asset_class": "code_pointer",
          "label": "测试文件 tests/test_evidence_upgrade.py（报告称 35 用例）",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1302,
            "end_char": 1332,
            "start_line": 36,
            "end_line": 36,
            "quote": "tests/test_evidence_upgrade.py",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists('tests/test_evidence_upgrade.py') in this worktree (TensorKnowledge)",
            "result": "unresolved"
          },
          "note": "worktree 内不存在该文件，35 用例数无法在此复核；按“不发明信息”原则仅登记引用与其声明数。"
        },
        {
          "asset_id": "A14",
          "asset_class": "code_pointer",
          "label": "图件脚本 artifacts/evidence_upgrade/make_figures.py",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1349,
            "end_char": 1391,
            "start_line": 37,
            "end_line": 37,
            "quote": "artifacts/evidence_upgrade/make_figures.py",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists('artifacts/evidence_upgrade/make_figures.py') in this worktree (TensorKnowledge)",
            "result": "unresolved"
          },
          "note": "worktree 内不存在；图为上游仓产物，本包不重建图件。"
        },
        {
          "asset_id": "A15",
          "asset_class": "result_table",
          "label": "判据总表（4 量 × 双源值/带宽/点值差/重叠度/判决/S_T/等级）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 1446,
            "end_char": 2289,
            "start_line": 43,
            "end_line": 48,
            "quote": "| 量 | 源 A（值 [带]） | 源 B（值 [带]） | 点值相对差 | 区间重叠度 | 判决 | S_T(设计) | S_T(环境) | 等级 |\n|---|---|---|---|---|---|---|---|---|\n| `wave_add_resistance` (-) | stawave1_longwave: 0.4257 [0.3193, 0.5322] | full_reflection_momentum: 0.5 [0.4, 0.6] | 17.4% | 0.661 | **INCONSISTENT** | 0.706 | 0.209 | **WITHHELD** |\n| `fouling` (%) | townsin2003_fouling_chain: 4.142 [3.314, 4.97] | ittc78_roughness_allowance_chain: 36.87 [29.5, 44.24] | 790.2% | 0.000 | **INCONSISTENT** | 0.990 | 0.937 | **WITHHELD** |\n| `wind_coeff` (-) | bluff_body_drag_3d: 0.9 [0.792, 1.008] | flat_plate_normal_relief: 0.8424 [0.716, 0.9688] | 6.4% | 0.818 | **CONSISTENT** | 0.414 | 0.052 | **REAL** |\n| `slamming` (-) | vonkarman_momentum_analytic: 10.88 [9.577, 12.19] | momentum_numerical_timestep: 10.88 [10.77, 10.99] | 0.0% | 1.000 | **CONSISTENT** | 0.197 | 0.011 | **REAL** |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "table header located + span sliced verbatim",
            "result": "resolved"
          },
          "note": "表头+分隔行+4 行数据（wave_add_resistance / fouling / wind_coeff / slamming）。数字仅登记，不复算、不改等级标注。"
        },
        {
          "asset_id": "A16",
          "asset_class": "verdict",
          "label": "升级判决结论（2/4 通过；wave/fouling 维持 WITHHELD）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 2291,
            "end_char": 2393,
            "start_line": 50,
            "end_line": 51,
            "quote": "升级判决：**2/4 通过** → `wind_coeff`, `slamming`；\n维持 WITHHELD：`wave_add_resistance`, `fouling`（验收线要求 ≥2，满足）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "anchor line located in markdown",
            "result": "resolved"
          },
          "note": "两行原文。这是报告作者的判决；本工序不确认、不升级、不标记 verified。"
        },
        {
          "asset_id": "A17",
          "asset_class": "result_table",
          "label": "Sobol 敏感度排序表（设计工况 S_T 排序 + 惰性因子 S_T）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 2412,
            "end_char": 2878,
            "start_line": 55,
            "end_line": 61,
            "quote": "| 量 | 敏感度排序（S_T，设计工况） | 惰性因子 S_T |\n|---|---|---|\n\n| `wave_add_resistance` | kappa_aw=0.706, hs=0.291, b=0.001, rho=0.000, dummy_unused=0.000 | 0.0000 |\n| `fouling` | dP_over_P=0.990, f_fric=0.008, n_power=0.007, roughness_scatter=0.004, dummy_unused=0.000 | 0.0000 |\n| `wind_coeff` | v_wind=0.545, cx0=0.414, a_f=0.036, rho_air=0.006, dummy_unused=0.000 | 0.0000 |\n| `slamming` | v_entry=0.743, cf_slam=0.197, beta_deg=0.049, rho=0.000, dummy_unused=0.000 | 0.0000 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "table header located + span sliced verbatim",
            "result": "resolved"
          },
          "note": "含表头/分隔行/空行/4 行排序，逐字切片（空白行保留以保真）。"
        },
        {
          "asset_id": "A18",
          "asset_class": "provenance_table",
          "label": "参考资产与审计链表（8 源：单位/有效域/带宽依据/provenance/sha256 前 16 位）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 2895,
            "end_char": 4278,
            "start_line": 66,
            "end_line": 76,
            "quote": "| 量 | 源 | 单位 | 有效域 | 带宽依据 | provenance | sha256(前 16) |\n|---|---|---|---|---|---|---|\n\n| `wave_add_resistance` | stawave1_longwave | - | lambda_p >= L_pp 的长波迎浪；R_AW = kappa*rho*g*zeta_a^2*B, zeta_a=Hs/4 | literature_spread | literature_closed_form | `b30f4651e3c00fbf` |\n| `wave_add_resistance` | full_reflection_momentum | - | lambda_p >> L_pp，深度弗劳德效应可忽略的深水长波 | declared_engineering_band | first_principles | `982788e4f2ac6db5` |\n| `fouling` | townsin2003_fouling_chain | % | ks=192.0 um @ 24 月（v=8.0 um/月 声明生长律），nt=3.0, f_fric=0.70 | declared_engineering_band | literature_closed_form | `0de72cbfc715c3b3` |\n| `fouling` | ittc78_roughness_allowance_chain | % | ks=192.0 um @ 24 月，同一 n/f_fric 链（隔离粗糙度函数差异） | declared_engineering_band | literature_closed_form | `a78539de43ff6a39` |\n| `wind_coeff` | bluff_body_drag_3d | - | psi=0 顶风，上层建筑+船体水下以上钝体外形，Re_air 1e7~1e8 | declared_engineering_band | first_principles | `9fa5d384596bcad9` |\n| `wind_coeff` | flat_plate_normal_relief | - | psi=0 顶风；把正投影面视为法向平板并做顶部泄流折减 | declared_engineering_band | first_principles | `642f72db934c1d47` |\n| `slamming` | vonkarman_momentum_analytic | - | beta=30 deg 刚性楔形、不可压、无空气垫、V 恒定 | declared_engineering_band | first_principles | `4015f3ef5ec10400` |\n| `slamming` | momentum_numerical_timestep | - | beta=30 deg，t_ref=0.05 s，dt=1e-5 s | numerical_discretisation | numerical_route | `2f40a28359cd84e3` |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "table header located + span sliced verbatim",
            "result": "resolved"
          },
          "note": "表头+分隔行+8 行源记录。sha256 仅前 16 位（报告原文如此），完整摘要不可由此表恢复——登记为截断摘要，不外推。"
        },
        {
          "asset_id": "A19",
          "asset_class": "derived_numbers",
          "label": "关键派生数字清单（交点 B/L=0.25、κ 17.4%、污损 8.90×、风压 6.4%、砰击 57.1%）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 4281,
            "end_char": 4650,
            "start_line": 79,
            "end_line": 90,
            "quote": "关键派生数字（代码算出，可复算）：\n* κ 两源解析交点：κ_A=κ_B ⇔ B/L=0.25（`sqrt(0.25)==0.5`，测试以 1e-12 密度钉住）；\n  KVLCC2 B/L=0.1812 ⇒ κ_A=0.4257 vs κ_B=0.5，\n  点值差 17.4%，重叠 0.661 < 0.70。\n* 污损：k_s=192.0 um；\n  Townsin 链 4.14 % vs ITTC-78 链 36.87 %\n  （比值 8.90），重叠 0.000。\n* 风压：两路 0.9000 vs 0.8424（差\n  6.4%），重叠 0.818。\n* 砰击：解析 10.8828 vs 独立数值 10.8828，\n  重叠 1.000；模型形式分歧（von Karman vs Wagner）\n  57.1% 单列披露。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "anchor line located + span sliced verbatim",
            "result": "resolved"
          },
          "note": "12 行原文；报告自述“代码算出，可复算”，本包只登记不复算（复算属抽取/验证工序）。"
        },
        {
          "asset_id": "A20",
          "asset_class": "figure",
          "label": "图 1 双源区间与重叠度（四量）",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 4662,
            "end_char": 4702,
            "start_line": 94,
            "end_line": 94,
            "quote": "* 图 1 双源区间与重叠度（四量）：源 A/源 B 带宽 + 点值 + 判决。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown ④ 图题定位 + API figures[0] payload inspection",
            "result": "unresolved"
          },
          "note": "平台 figures[0]=fig1_source_intervals.png 仅有 name/caption，无 png_base64 字节，故无字节可哈希；图件本体不在本 worktree。"
        },
        {
          "asset_id": "A21",
          "asset_class": "figure",
          "label": "图 2 Sobol 总效应排序（设计工况，0.10 门线）",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 4703,
            "end_char": 4760,
            "start_line": 95,
            "end_line": 95,
            "quote": "* 图 2 Sobol 总效应排序（设计工况），红线为被标定的量，虚线 0.10 门线；标题并列环境分布 S_T。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown ④ 图题定位 + API figures[1] payload inspection",
            "result": "unresolved"
          },
          "note": "平台 figures[1]=fig2_sobol_total_effect.png 仅 name/caption，无字节。"
        },
        {
          "asset_id": "A22",
          "asset_class": "figure",
          "label": "图 3 波浪增阻 κ 随 B/L 两源曲线与解析交点",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 4761,
            "end_char": 4812,
            "start_line": 96,
            "end_line": 96,
            "quote": "* 图 3 波浪增阻 κ 随 B/L 的两源曲线与解析交点 B/L=0.25，KVLCC2 位置标注。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "markdown ④ 图题定位 + API figures[2] payload inspection",
            "result": "unresolved"
          },
          "note": "平台 figures[2]=fig3_wave_crossover.png 仅 name/caption，无字节。"
        },
        {
          "asset_id": "A23",
          "asset_class": "caveat_section",
          "label": "注意点全节（带宽敏感/声明带/环境稀释/模型形式/生长律/MC 噪声）",
          "in_report_section": "⑤ 注意点",
          "locator": {
            "method": "char_span",
            "start_char": 4814,
            "end_char": 5677,
            "start_line": 98,
            "end_line": 117,
            "quote": "## ⑤ 注意点（踩过的坑 / 局限 / 适用范围）\n\n* **判决对带宽敏感**：波浪量的 `band_scale_at_flip` =\n  1.1187，即两带同时放大到该倍数就从 INCONSISTENT\n  翻成 CONSISTENT；且 B/L=0.25 的丰满船两源解析重合（CONSISTENT）。故判决不是\"船型无关的\n  真理\"，而是\"KVLCC2 级细长船上的分歧\"。未以挑船型的方式让判决好看（两船型都写进测试）。\n* **带宽多为声明带**：`literature_spread` 与 `declared_engineering_band` 逐条标注；本仓没有\n  OCIMF/Isherwood 数字化图表，风压的两源是两条**第一原理路线**（钝体三维折减 / 法向平板+泄流），\n  不是文献回归表 —— 这是升级的真实弱点，报告不粉饰。\n* **环境分布下系数被淹没**：wind S_T 由 0.414（设计）降到\n  0.052（环境）；slamming 由\n  0.197 降到 0.011（env_diluted=True）。\n  含义：标定系数降低的是**系统偏差**，环境散布决定**响应出现频率**，两者不可互相替代。\n* **砰击的 REAL 只是\"算法真实+双路线可复算\"**：一致性覆盖实现（解析 vs 数值时间步进 +\n  动能功率份额不变量=1），不覆盖模型形式（π/2 差）。实测峰值一般落在两理论之间，\n  精度须试验压力/力记录，故 `accuracy_caveat` 已显式写入报告 JSON。\n* **污损生长律是声明的线性律**（v=8 μm/月，24 月），未做船队统计标定；两源共享功率链，\n  差异纯由粗糙度函数标定数据集引起 —— 这正是文献分歧，不是实现 bug。\n* Sobol MC 噪声：主因子 ±0.03、小指数 ±0.05（n_base=512，无 bootstrap），\n  故只对 0.10 门线与\"主因子 vs 惰性因子\"作强结论。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "section heading located + span sliced verbatim",
            "result": "resolved"
          },
          "note": "整节 20 行逐字登记；含 band_scale_at_flip=1.1187 与 env_diluted=True 等不确定度披露。"
        },
        {
          "asset_id": "A24",
          "asset_class": "caveat",
          "label": "判决对带宽敏感（band_scale_at_flip=1.1187，B/L=0.25 丰满船两源重合）",
          "in_report_section": "⑤ 注意点",
          "locator": {
            "method": "char_span",
            "start_char": 4886,
            "end_char": 4919,
            "start_line": 101,
            "end_line": 101,
            "quote": "1.1187，即两带同时放大到该倍数就从 INCONSISTENT",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring located + uniqueness asserted",
            "result": "resolved"
          },
          "note": "原文跨行，此处 quote 取单行片段以保证逐字与唯一定位；完整语义见 A23 整节。"
        },
        {
          "asset_id": "A25",
          "asset_class": "error_table",
          "label": "误差判定表（8 判据 × 基准/实测/是否达标 + 升级数量）",
          "in_report_section": "⑥ 误差判定",
          "locator": {
            "method": "char_span",
            "start_char": 5700,
            "end_char": 6132,
            "start_line": 121,
            "end_line": 131,
            "quote": "| 判据 | 基准 / 参考 | 实测 | 是否达标 |\n|---|---|---|---|\n| 双源重叠度（波浪） | ≥0.7 | 0.661 | 否（INCONSISTENT，honest FAIL） |\n| 双源重叠度（污损） | ≥0.7 | 0.000 | 否（两 published 粗糙度函数差 8.9×） |\n| 双源重叠度（风压） | ≥0.7 | 0.818 | 是 |\n| 双源重叠度（砰击） | ≥0.7 | 1.000 | 是（verification 级） |\n| 敏感度（风压/砰击） | S_T>0.1 | 0.414 / 0.197 | 是 |\n| 惰性因子自检 | S_T≈0 | 0.0000 | 是 |\n| 解析恒等式 κ(0.25)=0.5 | 精确 | 相对误差 0（测试 1e-12） | 是 |\n| 砰击数值-解析 | 相对 <1e-6 | 实测 <1e-9 | 是 |\n| 升级数量 | ≥2 | 2 | 是 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "table header located + span sliced verbatim",
            "result": "resolved"
          },
          "note": "表头+分隔行+9 行（含升级数量行）；含两处 honest FAIL（0.661 / 0.000）。本包不重判这些是否达标。"
        },
        {
          "asset_id": "A26",
          "asset_class": "declared_absence",
          "label": "外部基准数据缺失声明",
          "in_report_section": "⑥ 误差判定",
          "locator": {
            "method": "char_span",
            "start_char": 6343,
            "end_char": 6359,
            "start_line": 137,
            "end_line": 137,
            "quote": "无可用基准数据，故不声称 <3%",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "search markdown for any external benchmark dataset/citation supplying residuals",
            "result": "absent"
          },
          "note": "报告显式声明无模型试验/实测/船队基准，故 <3% 不可声称；登记为 declared_absent，不补造基准。"
        },
        {
          "asset_id": "A27",
          "asset_class": "declared_absence",
          "label": "OCIMF/Isherwood 数字化图表缺失声明",
          "in_report_section": "⑤ 注意点",
          "locator": {
            "method": "char_span",
            "start_char": 5109,
            "end_char": 5149,
            "start_line": 105,
            "end_line": 105,
            "quote": "OCIMF/Isherwood 数字化图表，风压的两源是两条**第一原理路线**",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "search markdown for OCIMF/Isherwood digitised chart assets",
            "result": "absent"
          },
          "note": "原文“本仓没有 OCIMF/Isherwood 数字化图表”；风压两源实为两条第一原理路线而非文献回归表。"
        },
        {
          "asset_id": "A28",
          "asset_class": "declared_absence",
          "label": "污损船队统计标定未做声明",
          "in_report_section": "⑤ 注意点",
          "locator": {
            "method": "char_span",
            "start_char": 5528,
            "end_char": 5536,
            "start_line": 114,
            "end_line": 114,
            "quote": "未做船队统计标定",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "search markdown for fleet-statistics calibration of the fouling growth law",
            "result": "absent"
          },
          "note": "生长律为声明线性律（v=8 μm/月，24 月）；无船队统计标定数据，登记为缺失而非零。"
        },
        {
          "asset_id": "A29",
          "asset_class": "metadata_field",
          "label": "报告自述的 JSON 字段 accuracy_caveat",
          "in_report_section": "⑤ 注意点",
          "locator": {
            "method": "char_span",
            "start_char": 5462,
            "end_char": 5492,
            "start_line": 113,
            "end_line": 113,
            "quote": "`accuracy_caveat` 已显式写入报告 JSON",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "key 'accuracy_caveat' present in GET /tensor/reports/10459 payload top-level keys?",
            "result": "unresolved"
          },
          "note": "markdown 自述该字段已写入报告 JSON，但平台记录顶层键为 id/title/summary/scenario_key/mission_id/stage/tags/figures/status/created_by/created_at/markdown，无 accuracy_caveat —— 上游不一致，如实登记，不代写该字段。"
        }
      ],
      "claims": [],
      "integrity": {
        "quote_uniqueness": "every quote asserted to occur exactly once in the markdown (unique=true for all 29 assets)",
        "hash_recomputed_locally": "08c1a0cfb3f0db38ad3a473ac2155001589bde91c1f85c21db1d29863ca84f6c",
        "hash_matches_contract": true,
        "chars_matches_contract": true,
        "contract_expected_hash": "08c1a0cfb3f0db38ad3a473ac2155001589bde91c1f85c21db1d29863ca84f6c",
        "contract_expected_chars": 6431
      },
      "explicit_non_actions": [
        "no claim extraction (objective.classify_report_type=false; claims=[])",
        "no verification marking (verification computed by platform gate)",
        "no re-computation of the report's numbers; registration only",
        "no read/write of any other report_id"
      ]
    }
  },
  "claims": []
}
```
