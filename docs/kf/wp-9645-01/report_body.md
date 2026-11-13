# KF-RESULT wp-9645-01

**工序** 01-asset-registration ｜ **report_id** 9645 ｜ **契约** contract_version 1.0 ｜ **lane** B ｜ **status** draft

| 项 | 值 |
|---|---|
| 源资产 URI | `tensor://reports/9645`（field=`markdown`） |
| 源 sha256（本工序重算） | `a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00` |
| 源 sha256（契约声明） | `a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00` |
| 一致 | ✓ |
| 字符数 / UTF-8 字节 / 行数 | 11824 / 15967 / 196 |
| 报告标题（平台记录） | IN101-N09 ISO 19906 冰压设计分项系数目标可靠度反标定（成熟化） |
| scenario_key | `ice_partial_factors_target_inverse` |
| 平台 mission_id / status | 8350 / published |
| 注册资产数 | 46（resolved 27 / unresolved 18 / absent 1） |
| claims | 0 条（`claims: []`，契约允许；本工序不做抽取） |
| 输出文件名 | `asset_manifest.json` |

## ① 本工序做了什么

按合同 `objective.register_assets=true`、`objective.classify_report_type=false`，对 report_id=9645 的 markdown 做**资产登记**：

1. 取回 `tensor://reports/9645` 的 `markdown` 字段，本地重算 sha256 并核对契约声明值 `a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00` 与字符数 11824。
2. 把该 markdown 内的可解析材料登记为 46 条资产：文档本体与章节锚点、机器判据表与判据汇总行、输入参数表、表 1–表 8、⑥ 误差判定表与结论段、6 张图（markdown 图片声明）、结果 JSON / 求解器模块 / 脚本 / 复现命令等代码与数据引用、ISO 19906 Annex A 表格（报告自述缺失）与出处等级标记、JCSS/ISO 2394 劈分约定、产出仓与前序节点、3 个数值锚点、设计格式原文。
3. 每条资产给出**逐字字符区间 locator**（`start_char/end_char/start_line/end_line/quote/quote_sha256`），并对每个 quote 断言「是源文本的唯一子串且 `md[start:end]==quote`」。
4. **未做**：知识抽取、结论判定、report_type 分类、任何 `verified` 标记；`claims` 为空数组。

## ② 怎么做的（步骤 / 工具 / 关键设置）

| 步骤 | 做法 | 产物 / 证据 |
|---|---|---|
| 取源 | `GET $TENSOR_API_BASE/tensor/reports/9645`（Bearer 登录 token），只读该 report_id | `source.md`（源副本）+ `sha256.txt` |
| 校验 | `hashlib.sha256(markdown.encode('utf-8'))` 对比契约哈希；字符数对比 11824；`source.title_matches_contract` / `scenario_key_matches_contract` 位记录 | `asset_manifest.json` → `source.*` |
| 定位 | 每条资产先给一个**唯一锚串**，程序断言 `md.count(anchor)==1`，再按 `token / line / table / para / document` 五种方式扩成区段，quote 一律取 `md[start:end]` 切片（**不手抄**） | `assets[].locator` |
| 解析状态 | 三档：`resolved_in_source`（引用与字节都在包内）/ `referenced_unresolved`（引用可定位、目标字节不在包内）/ `declared_absent`（报告自述不在工作树） | `assets[].resolution` + `resolution_check` |
| 覆盖检查 | 扫全部 inline-code token 与 markdown 图片，逐个判定是否落在某资产字符区间内；否则必须显式豁免并给理由 | `coverage.*` |
| 结构校验 | 信封 `jsonschema.validate(kf_result, schemas/kf_result.v1.schema.json)`；清单 `jsonschema.validate(manifest, docs/kf/wp-9645-01/asset_manifest.schema.json)` | `locator_check.json` |
| 自检 | `verify` 模式离线重跑 6 项 acceptance + 4 项附加检查，输出 `locator_check.json` | `report_body.md`（本文件） |

工具链：Python 3 标准库（`hashlib`/`json`/`urllib`）+ `jsonschema` + `matplotlib`；脚本 `scripts/kf/wp_9645_01_register.py`（`build`/`verify`/`figure`/`report` 四模式）。

**一键复跑**（工作树根）：

```
python3 scripts/kf/wp_9645_01_register.py build && \
python3 scripts/kf/wp_9645_01_register.py verify && \
python3 scripts/kf/wp_9645_01_register.py figure && \
python3 scripts/kf/wp_9645_01_register.py report
```

离线复检（无需网络，仅用仓内 `source.md`）：

```
python3 scripts/kf/wp_9645_01_register.py verify
python3 -m pytest tests/test_wp_9645_01_assets.py -q
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-9645-01/asset_manifest.json` | 资产清单主体：source 元信息 + 46 条资产 + counts + coverage + integrity + platform_probe；`claims` 空 |
| `docs/kf/wp-9645-01/kf_result.json` | 结果信封（package_id / task_type / report_id / provenance / outputs / claims），`outputs.asset_manifest.json` 内嵌清单全文 |
| `docs/kf/wp-9645-01/source.md` | 报告 markdown 逐字节副本（所有 locator 的解析底本） |
| `docs/kf/wp-9645-01/sha256.txt` | sha256 / field / chars / bytes / report_id 一行事实 |
| `docs/kf/wp-9645-01/locator_check.json` | 离线自检记录：6 项 acceptance + 4 项附加检查逐项 pass/fail 与证据串 |
| `docs/kf/wp-9645-01/asset_manifest.schema.json` | 本包清单形状约束（可机器裁的 `schema_pass`，`asset_manifest.v1` 的 pattern 版） |
| `docs/kf/wp-9645-01/asset_coverage.png` | 覆盖图：按解析状态的资产计数 + 按资产类别计数（见 ④ 图说明） |

按资产类别分布：

| asset_class | 数量 |
|---|---|
| `table` | 9 |
| `section_heading` | 8 |
| `code_reference` | 6 |
| `figure_reference` | 6 |
| `numeric_anchor` | 3 |
| `criterion_summary` | 1 |
| `data_artifact_reference` | 1 |
| `design_format` | 1 |
| `external_standard_reference` | 1 |
| `external_standard_table` | 1 |
| `machine_criteria_table` | 1 |
| `parameter_table` | 1 |
| `prior_node_reference` | 1 |
| `provenance_flag` | 1 |
| `record_field_reference` | 1 |
| `repo_reference` | 1 |
| `report_markdown` | 1 |
| `repro_command` | 1 |
| `statement` | 1 |

## ④ 证据定位表（claim / 字段 → 原文引文片段）

**图说明（本工序唯一图件 `asset_coverage.png`）**：本工序是登记型（无物理场、无数值求解），因此没有场量云图与解析解/基线比较曲线可画；图件改为**登记覆盖图**——左栏按解析状态计数（resolved_in_source 27 / referenced_unresolved 18 / declared_absent 1），右栏按资产类别计数，标题行给出源 sha256 前 12 位与自检 10/10 结果。图中每个数字都直接取自 `asset_manifest.json` 的 `counts`（程序化注入，非手抄）。

本工序无 claim（`claims: []`），下表是**字段级**证据定位：`asset_id → 原文逐字片段`，全部可由 `md[start:end]==quote` 机械复算。

| asset_id | asset_class | resolution | 行 | 字符区间 | 原文片段（逐字切片） |
|---|---|---|---|---|---|
| A01 | `report_markdown` | resolved_in_source | L1–L196 | 0–11824 | `# IN101-N09 — ISO 19906 ice-pressure partial-factor back-calibration at beta_T =…` |
| A02 | `section_heading` | resolved_in_source | L1–L1 | 0–147 | `# IN101-N09 — ISO 19906 ice-pressure partial-factor back-calibration at beta_T =…` |
| A03 | `section_heading` | resolved_in_source | L15–L15 | 652–673 | `## ① 案例介绍（物理背景 / 参数表）` |
| A04 | `section_heading` | resolved_in_source | L34–L34 | 1486–1510 | `## ② 怎么做的（方法 / 流程 / 工具链）` |
| A05 | `section_heading` | resolved_in_source | L47–L47 | 3009–3018 | `## ③ 计算结果` |
| A06 | `section_heading` | resolved_in_source | L139–L139 | 7553–7561 | `## ④ 结果图` |
| A07 | `section_heading` | resolved_in_source | L165–L165 | 9265–9288 | `## ⑤ 注意点（坑 / 局限 / 适用范围）` |
| A08 | `section_heading` | resolved_in_source | L174–L174 | 10598–10629 | `## ⑥ 误差判定（逐项 vs 基准，显式回答是否 <3 %）` |
| A09 | `section_heading` | resolved_in_source | L190–L190 | 11379–11385 | `## 审计链` |
| A10 | `machine_criteria_table` | resolved_in_source | L5–L11 | 400–633 | `` \| 机器判据 \| 结果 \| ⏎ \|---\|---\| ⏎ \| `a_form_vs_simulation` \| PASS \| ⏎ \| `b_inverse_sol… `` |
| A11 | `criterion_summary` | resolved_in_source | L13–L13 | 635–650 | `**判据汇总** 5/5 通过` |
| A12 | `parameter_table` | resolved_in_source | L19–L32 | 946–1484 | `\| 参数 \| 取值 \| 说明 \| ⏎ \|---\|---\|---\| ⏎ \| $p_0$ \| 2.500 MPa \| 参考面积处冰压中值 \| ⏎ \| $ex$ \| …` |
| A13 | `table` | resolved_in_source | L49–L64 | 3020–3495 | `**表 1 反问题解** ⏎  ⏎ \| 量 \| 值 \| ⏎ \|---\|---\| ⏎ \| $\gamma_f^*$ \| **1.437056** \| ⏎ \| $\…` |
| A14 | `table` | resolved_in_source | L66–L74 | 3497–3926 | `**表 2 FORM 的四条独立验证（判据 a）** ⏎  ⏎ \| 方法 \| $\beta$ \| $P_f$ \| 与 FORM 相对误差 \| 1σ 区间覆盖 F…` |
| A15 | `table` | resolved_in_source | L76–L83 | 3928–4245 | `**表 3 β 敏感性（判据 c）：包络定理解析导数 vs 中心差分** ⏎  ⏎ \| 导数 \| 解析（伴随）\| 中心差分 \| 相对误差 \| ⏎ \|---\|--…` |
| A16 | `table` | resolved_in_source | L85–L98 | 4247–5648 | `**表 4 与 ISO 19906 表格分项系数偏差（判据 d）** ⏎  ⏎ \| 表格对（$\gamma_F\times\gamma_M$）\| 表格值 \| $…` |
| A17 | `table` | resolved_in_source | L100–L109 | 5650–6455 | `**表 5 不保守算例（偏差 >15 % 且 $\kappa_{table}<\kappa^*$）** ⏎  ⏎ \| 表格对 \| $\kappa$ 缺口 \| 达…` |
| A18 | `table` | resolved_in_source | L111–L116 | 6457–6710 | `**表 6 负控（判据 e）：忽略 p–A 负相关** ⏎  ⏎ \| 模型 \| $\kappa^*$ \| $\gamma_f^*$ \| $\psi^*$ \| $…` |
| A19 | `table` | resolved_in_source | L120–L127 | 6858–7242 | `**表 7 $\beta_T$ 敏感性** ⏎  ⏎ \| $\beta_T$ \| $P_{f,T}$ \| $\gamma_f^*$ \| $\psi^*$ \| $…` |
| A20 | `table` | resolved_in_source | L129–L137 | 7244–7551 | `**表 8 模型参数敏感性 $\partial\beta/\partial\theta$（在 $\kappa^*$ 处，中心差分）** ⏎  ⏎ \| 参数 \| …` |
| A21 | `table` | resolved_in_source | L176–L186 | 10631–11194 | `\| 关键量 \| 基准 \| 误差 \| <3 % ? \| ⏎ \|---\|---\|---\|---\| ⏎ \| FORM $\beta$ \| 闭式解析 $\beta_{l…` |
| A22 | `statement` | resolved_in_source | L188–L188 | 11196–11377 | `**结论**：FORM 与解析值、重要性抽样的一致性远优于 3 %（均为 1e-2 % 量级）；反问题残差 1e-11；伴随导数与有限差分一致到 1e-7；唯一…` |
| A23 | `figure_reference` | referenced_unresolved | L143–L143 | 7741–7827 | `![fig1](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig1_pa_join…` |
| A24 | `figure_reference` | referenced_unresolved | L147–L147 | 8015–8106 | `![fig2](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig2_beta_vs…` |
| A25 | `figure_reference` | referenced_unresolved | L151–L151 | 8321–8405 | `![fig3](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig3_newton.…` |
| A26 | `figure_reference` | referenced_unresolved | L155–L155 | 8587–8679 | `![fig4](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig4_iso_dev…` |
| A27 | `figure_reference` | referenced_unresolved | L159–L159 | 8913–9007 | `![fig5](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig5_negativ…` |
| A28 | `figure_reference` | referenced_unresolved | L163–L163 | 9174–9263 | `![fig6](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig6_sensiti…` |
| A29 | `data_artifact_reference` | referenced_unresolved | L192–L192 | 11398–11480 | `/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/in101_n09_results.js…` |
| A30 | `record_field_reference` | referenced_unresolved | L193–L193 | 11520–11561 | `` `machine_criteria` 5 条，`criteria_summary` `` |
| A31 | `code_reference` | referenced_unresolved | L3–L3 | 179–214 | `` `tensorphysics.ice_partial_factors` `` |
| A32 | `code_reference` | referenced_unresolved | L194–L194 | 11630–11668 | `` `tensorphysics.structural.reliability` `` |
| A33 | `code_reference` | referenced_unresolved | L194–L194 | 11693–11733 | `` `tensorphysics.structural.distributions` `` |
| A34 | `code_reference` | referenced_unresolved | L36–L36 | 1529–1546 | `` `p_area_joint.py` `` |
| A35 | `code_reference` | referenced_unresolved | L37–L37 | 2009–2040 | `` `target_reliability_inverse.py` `` |
| A36 | `code_reference` | referenced_unresolved | L192–L192 | 11495–11511 | `` `run_study()` 直出 `` |
| A37 | `repro_command` | referenced_unresolved | L195–L195 | 11747–11822 | `PYTHONPATH=src python3 benchmarks/iso19906_partial_factors/run_in101_n09.py` |
| A38 | `external_standard_table` | declared_absent | L171–L171 | 10185–10211 | `ISO 19906 Annex A 正文不在工作树内` |
| A39 | `provenance_flag` | resolved_in_source | L171–L171 | 10228–10284 | `` `source_tier=secondary`, `primary_source_verified=False` `` |
| A40 | `external_standard_reference` | referenced_unresolved | L41–L41 | 2254–2299 | `JCSS/ISO 2394 设计值劈分（荷载分项系数 = FORM 设计点作用/特征作用）` |
| A41 | `repo_reference` | referenced_unresolved | L3–L3 | 149–169 | `**仓库** TensorPhysics` |
| A42 | `prior_node_reference` | referenced_unresolved | L3–L3 | 337–348 | `IN13-W3-N10` |
| A43 | `numeric_anchor` | resolved_in_source | L55–L55 | 3114–3160 | `\| $\kappa^*=\gamma_f^*\psi^*$ \| **1.431318** \|` |
| A44 | `numeric_anchor` | resolved_in_source | L58–L58 | 3223–3255 | `\| 达到的 $\beta$ \| 4.000000000000 \|` |
| A45 | `numeric_anchor` | resolved_in_source | L118–L118 | 6712–6856 | `$\Delta\gamma_f^*$ = +28.90 %，$\Delta\kappa^*$ = +21.63 %；把偏大的 $\kappa$ 用到**物理**…` |
| A46 | `design_format` | resolved_in_source | L3–L3 | 226–278 | `` `gamma_f * F_k <= R_k / psi,  kappa = gamma_f * psi` `` |

未能解析（`referenced_unresolved` / `declared_absent`）的条目及原因：

| asset_id | asset_class | resolution | 原因（实测） |
|---|---|---|---|
| A23 | `figure_reference` | referenced_unresolved | record_entry_found=True payload_in_record=False local_copy_in_worktree=False |
| A24 | `figure_reference` | referenced_unresolved | record_entry_found=True payload_in_record=False local_copy_in_worktree=False |
| A25 | `figure_reference` | referenced_unresolved | record_entry_found=True payload_in_record=False local_copy_in_worktree=False |
| A26 | `figure_reference` | referenced_unresolved | record_entry_found=True payload_in_record=False local_copy_in_worktree=False |
| A27 | `figure_reference` | referenced_unresolved | record_entry_found=True payload_in_record=False local_copy_in_worktree=False |
| A28 | `figure_reference` | referenced_unresolved | record_entry_found=True payload_in_record=False local_copy_in_worktree=False |
| A29 | `data_artifact_reference` | referenced_unresolved | target path is outside this worktree; not fetched (scope: report 9645 only) |
| A30 | `record_field_reference` | referenced_unresolved | field names quoted from the report's own restatement; source JSON not fetched |
| A31 | `code_reference` | referenced_unresolved | local probe src/tensorphysics=False (producing repo is TensorPhysics, this checkout is TensorKnowledge) |
| A32 | `code_reference` | referenced_unresolved | local probe src/tensorphysics=False (producing repo is TensorPhysics, this checkout is TensorKnowledge) |
| A33 | `code_reference` | referenced_unresolved | local probe src/tensorphysics=False (producing repo is TensorPhysics, this checkout is TensorKnowledge) |
| A34 | `code_reference` | referenced_unresolved | local probe benchmarks/iso19906_partial_factors=False |
| A35 | `code_reference` | referenced_unresolved | local probe benchmarks/iso19906_partial_factors=False |
| A36 | `code_reference` | referenced_unresolved | reference registered at its mention; target bytes out of this package's scope |
| A37 | `repro_command` | referenced_unresolved | local probe benchmarks/iso19906_partial_factors=False |
| A38 | `external_standard_table` | declared_absent | declaration quoted verbatim at locator; not supplemented by this package |
| A40 | `external_standard_reference` | referenced_unresolved | standard text is not in the worktree; no primary copy taken |
| A41 | `repo_reference` | referenced_unresolved | reference registered at its mention; target bytes out of this package's scope |
| A42 | `prior_node_reference` | referenced_unresolved | reference registered at its mention; target bytes out of this package's scope |

## ⑤ 注意点与局限

1. **6 张图只有引用、没有字节**。报告 markdown 用绝对路径（`/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig*.png`）引用图，指向产出任务 8350 的工作树；平台记录 `figures[]` 只存 name+caption、无 png 载荷（`platform_figures_payload_present=false`，实测）。故 6 条图资产全部 `referenced_unresolved`：登记位置与文件名，不声称持有图件、不对图内容作任何断言。按边界也未跨任务取件。
2. **结果 JSON 与求解器代码不在本包范围内**。`in101_n09_results.json`、`tensorphysics.*`、`p_area_joint.py`、`target_reliability_inverse.py`、复现命令均属 TensorPhysics 仓/产出任务 8350；本检出为 TensorKnowledge，`src/tensorphysics` 与 `benchmarks/iso19906_partial_factors` 实测不存在（`source.local_availability`），因此这些条目是引用登记，不是可解析资产。
3. **ISO 19906 Annex A.2/A.3 表格值本工序不持有、不补录**。报告自述「ISO 19906 Annex A 正文不在工作树内」且标记 `source_tier=secondary`, `primary_source_verified=False`；表 4/表 5 中的表格分项系数只能从报告转述登记，无法回溯到规范正文。这是本报告最大的外部证据缺口，下游若要用表 4/表 5 的偏差结论，必须自行取得规范正文。
4. **哈希一致 ≠ 内容正确**。`source_hash_matches` 只证明我读到的字节与契约声明同源；本工序没有任何判据复核 β、κ*、偏差等数值是否算对，也不把任何结论标成 `verified`（verification 归平台门）。
5. **会计口径（会计而非评价）**：`resolved_in_source` 计 27 条、`referenced_unresolved` 18 条、`declared_absent` 1 条；前者是「引文可逐字解析」，不等于「结论成立」。
6. **清单 schema 是本地约束**。`schemas/kf_result.v1.schema.json` 在仓内存在并按它校验信封；清单侧无仓内 canonical schema（`schemas/asset_manifest.v1.schema.json` 是 wp-448-01 的 const 版，package_id/report_id 写死为 448），故本包补 `docs/kf/wp-9645-01/asset_manifest.schema.json`（同形状、const 改 pattern）。**若平台侧 schema 与此不符，以平台为准、本包接受返修。**

## ⑥ 自检：逐条对照 acceptance

| 结果 | acceptance 项 | 证据 |
|---|---|---|
| ✓ | valid_json | asset_manifest.json + kf_result.json 均解析成功（strict JSON，无尾逗号/注释） |
| ✓ | schema_pass | envelope vs schemas/kf_result.v1.schema.json (sha256 170dba8b0b5d5401...); manifest vs docs/kf/wp-9645-01/asset_manifest.schema.json (sha256 ea9c9d39c391befc...) |
| ✓ | source_locator_resolvable | 逐个重解析 46 个 locator（char_span 用 md[start:end]==quote 且全文字符串计数=1；document 用 hash+长度+首行前缀），不可解析=[] |
| ✓ | source_hash_matches | 本地重算 sha256=a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00；契约=a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00；信封=sha256:a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00；字符数=11824 |
| ✓ | no_duplicate_ids | 46 个 asset_id，重复=[]，outputs 键=['asset_manifest.json'] |
| ✓ | all_claims_have_evidence_or_explicit_unresolved_status | claims=0（task_type 01 的空数组是完整结果）；缺证据/缺状态的条数=0 |
| ✓ | reference_coverage | 未归类 inline code token=[]；未登记 markdown 图片=[] |
| ✓ | manifest_integrity_flags | {"quote_uniqueness": true, "hash_recomputed_locally": true, "hash_matches_contract": true, "locator_span_equality": true, "asset_ids_unique": true} |
| ✓ | no_verification_marks | claims 为空；结果内无 claim 级 verification 标记（verification 由平台门计算） |
| ✓ | contract_metadata_matches | title 与契约一致=True；scenario_key 与契约一致=True |

附加检查（非 acceptance，但本包断言）：`reference_coverage`、`manifest_integrity_flags`、`no_verification_marks`、`contract_metadata_matches` 全绿；全部 10 项见 `locator_check.json` 的 `all_pass` 字段（当前 `all_pass=True`）。

**未跑/未验的项（如实声明）**：报告的数值结论（β=4.0 精度、κ 唯一性、ISO 表格偏差、负控）**未**在本工序复核——不属本工序接口；报告 markdown 引用的 6 张图件与结果 JSON **未**取回，故对图与 JSON 的内容未作任何验证。

```json
{
  "package_id": "wp-9645-01",
  "task_type": "01-asset-registration",
  "report_id": "9645",
  "provenance": {
    "source_hash": "sha256:a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00",
    "source_field": "markdown",
    "producer": "agent/m15663",
    "emitted_at": "2026-11-12T01:44:22.943496+00:00",
    "notes": "source_hash 由本工序对 GET http://127.0.0.1:8010/api/v1/tensor/reports/9645 返回的 markdown 取 UTF-8 字节重算，与契约声明值一致；哈希相等是机械恒等检查，不构成对报告内容正确性的判定，任何结论都未被标为 verified（verification 归平台门）。"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-9645-01",
      "task_type": "01-asset-registration",
      "contract_version": "1.0",
      "report_id": "9645",
      "generated_at": "2026-11-12T01:44:22.940498+00:00",
      "generator": "scripts/kf/wp_9645_01_register.py",
      "source": {
        "uri": "tensor://reports/9645",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00",
        "hash_expected_from_contract": "a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00",
        "hash_matches_contract": true,
        "hashed_bytes": "markdown field encoded as UTF-8",
        "chars": 11824,
        "chars_expected_from_contract": 11824,
        "bytes_utf8": 15967,
        "lines": 196,
        "title": "IN101-N09 ISO 19906 冰压设计分项系数目标可靠度反标定（成熟化）",
        "title_matches_contract": true,
        "scenario_key": "ice_partial_factors_target_inverse",
        "scenario_key_matches_contract": true,
        "platform_report_id": 9645,
        "platform_mission_id": 8350,
        "platform_status": "published",
        "platform_tags": [
          "IN101-N09",
          "ISO19906",
          "partial-factors",
          "FORM",
          "importance-sampling",
          "negative-control",
          "ice"
        ],
        "platform_figures": [
          "fig1_pa_joint.png",
          "fig2_beta_vs_kappa.png",
          "fig3_newton.png",
          "fig4_iso_deviations.png",
          "fig5_negative_control.png",
          "fig6_sensitivity.png"
        ],
        "platform_figures_payload_present": false,
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/9645",
        "local_copy": "docs/kf/wp-9645-01/source.md",
        "local_availability": {
          "benchmarks/iso19906_partial_factors": false,
          "src/tensorphysics": false,
          "solver_module_ice_partial_factors": false
        }
      },
      "objective": {
        "register_assets": true,
        "classify_report_type": false,
        "extraction_performed": false,
        "claims_generated": false
      },
      "counts": {
        "assets": 46,
        "by_class": {
          "report_markdown": 1,
          "section_heading": 8,
          "machine_criteria_table": 1,
          "criterion_summary": 1,
          "parameter_table": 1,
          "table": 9,
          "statement": 1,
          "figure_reference": 6,
          "data_artifact_reference": 1,
          "record_field_reference": 1,
          "code_reference": 6,
          "repro_command": 1,
          "external_standard_table": 1,
          "provenance_flag": 1,
          "external_standard_reference": 1,
          "repo_reference": 1,
          "prior_node_reference": 1,
          "numeric_anchor": 3,
          "design_format": 1
        },
        "by_resolution": {
          "resolved_in_source": 27,
          "referenced_unresolved": 18,
          "declared_absent": 1
        },
        "resolved_in_source": 27,
        "referenced_unresolved": 18,
        "declared_absent": 1,
        "markdown_images": 6,
        "markdown_images_registered": 6,
        "inline_code_tokens": 25,
        "inline_code_tokens_covered_or_exempt": 25
      },
      "resolution_vocabulary": {
        "resolved_in_source": "引用与字节都在本包范围内：quote 是源 markdown 的唯一逐字切片",
        "referenced_unresolved": "引用在原文中可定位，但目标字节不在本包范围（跨仓 / 跨任务 / 未取件），登记而不解析",
        "declared_absent": "报告自述该材料不在工作树内，本工序不补录、不推断"
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "report_markdown",
          "label": "报告正文（markdown 全文，注册的唯一源资产）",
          "in_report_section": "(document)",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 11824,
            "start_line": 1,
            "end_line": 196,
            "quote": "# IN101-N09 — ISO 19906 ice-pressure partial-factor back-calibration at beta_T = 4.0 (mature: target-reliability inverse, FORM/IS/MC cross-checked)",
            "unique": true,
            "quote_sha256": "3bf5a31633ccf69996cd2b094e4bf0b07db41d4eaed6b4002975be08d683a4aa"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "present"
          },
          "note": "源资产本体：sha256 见 source.hash；本清单所有 locator 的字符偏移均相对此文本。"
        },
        {
          "asset_id": "A02",
          "asset_class": "section_heading",
          "label": "一级标题行（含仓库 / 模块 / 设计格式 / 目标 beta / 前序节点元信息）",
          "in_report_section": "(document)",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 147,
            "start_line": 1,
            "end_line": 1,
            "quote": "# IN101-N09 — ISO 19906 ice-pressure partial-factor back-calibration at beta_T = 4.0 (mature: target-reliability inverse, FORM/IS/MC cross-checked)",
            "unique": true,
            "quote_sha256": "3bf5a31633ccf69996cd2b094e4bf0b07db41d4eaed6b4002975be08d683a4aa"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "标题行本身是元信息载体（TensorPhysics、tensorphysics.ice_partial_factors、beta_T=4.00、IN13-W3-N10）。"
        },
        {
          "asset_id": "A03",
          "asset_class": "section_heading",
          "label": "§① 案例介绍（物理背景 / 参数表）",
          "in_report_section": "①",
          "locator": {
            "method": "char_span",
            "start_char": 652,
            "end_char": 673,
            "start_line": 15,
            "end_line": 15,
            "quote": "## ① 案例介绍（物理背景 / 参数表）",
            "unique": true,
            "quote_sha256": "36a26967e12d847614510e47819c2d9e0d047109603f5103fcd3fe73da5c0a70"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "章节定位锚点。"
        },
        {
          "asset_id": "A04",
          "asset_class": "section_heading",
          "label": "§② 怎么做的（方法 / 流程 / 工具链）",
          "in_report_section": "②",
          "locator": {
            "method": "char_span",
            "start_char": 1486,
            "end_char": 1510,
            "start_line": 34,
            "end_line": 34,
            "quote": "## ② 怎么做的（方法 / 流程 / 工具链）",
            "unique": true,
            "quote_sha256": "8212001779678628cf0a139365a79343a8bf2172e157ae032abbd77b7c998d64"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "章节定位锚点。"
        },
        {
          "asset_id": "A05",
          "asset_class": "section_heading",
          "label": "§③ 计算结果",
          "in_report_section": "③",
          "locator": {
            "method": "char_span",
            "start_char": 3009,
            "end_char": 3018,
            "start_line": 47,
            "end_line": 47,
            "quote": "## ③ 计算结果",
            "unique": true,
            "quote_sha256": "725f569a39ae4b79e0c3d7f6f2747c2eb79f7fba7690c5cf38e8112f68cdf1c7"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "章节定位锚点。"
        },
        {
          "asset_id": "A06",
          "asset_class": "section_heading",
          "label": "§④ 结果图",
          "in_report_section": "④",
          "locator": {
            "method": "char_span",
            "start_char": 7553,
            "end_char": 7561,
            "start_line": 139,
            "end_line": 139,
            "quote": "## ④ 结果图",
            "unique": true,
            "quote_sha256": "f96f5db082d6af7df301ed61dff480e611035eab736db49814b2ba4ba6067766"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "章节定位锚点。"
        },
        {
          "asset_id": "A07",
          "asset_class": "section_heading",
          "label": "§⑤ 注意点（坑 / 局限 / 适用范围）",
          "in_report_section": "⑤",
          "locator": {
            "method": "char_span",
            "start_char": 9265,
            "end_char": 9288,
            "start_line": 165,
            "end_line": 165,
            "quote": "## ⑤ 注意点（坑 / 局限 / 适用范围）",
            "unique": true,
            "quote_sha256": "9a72c263336542c4dfcf2b4dfc5fefa0f7a4e947dd7485cb6106ec643ab828a4"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "章节定位锚点。"
        },
        {
          "asset_id": "A08",
          "asset_class": "section_heading",
          "label": "§⑥ 误差判定（逐项 vs 基准，显式回答是否 <3 %）",
          "in_report_section": "⑥",
          "locator": {
            "method": "char_span",
            "start_char": 10598,
            "end_char": 10629,
            "start_line": 174,
            "end_line": 174,
            "quote": "## ⑥ 误差判定（逐项 vs 基准，显式回答是否 <3 %）",
            "unique": true,
            "quote_sha256": "6beca3b0a84d1fba646616cdd900b7425dee81b8ed5cc598166099e1080bd34e"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "章节定位锚点。"
        },
        {
          "asset_id": "A09",
          "asset_class": "section_heading",
          "label": "审计链（结果 JSON / 机器判据 / 求解器 / 复现命令）",
          "in_report_section": "审计链",
          "locator": {
            "method": "char_span",
            "start_char": 11379,
            "end_char": 11385,
            "start_line": 190,
            "end_line": 190,
            "quote": "## 审计链",
            "unique": true,
            "quote_sha256": "3a9b5efde46d8c79af4c6849e20f71b773bec17d9da34923afcd7ee002c48297"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "章节定位锚点。"
        },
        {
          "asset_id": "A10",
          "asset_class": "machine_criteria_table",
          "label": "机器判据表（a–e 五条判据及 PASS 结果）",
          "in_report_section": "标题后",
          "locator": {
            "method": "char_span",
            "start_char": 400,
            "end_char": 633,
            "start_line": 5,
            "end_line": 11,
            "quote": "| 机器判据 | 结果 |\n|---|---|\n| `a_form_vs_simulation` | PASS |\n| `b_inverse_solved_unique` | PASS |\n| `c_beta_sensitivity_vs_finite_difference` | PASS |\n| `d_iso_table_deviation_map` | PASS |\n| `e_negative_control_pa_correlation` | PASS |",
            "unique": true,
            "quote_sha256": "c2423e763e49eff201d03a35b502bada0383668e0355a67405b8cc4ed807910e"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "判据名与 PASS 结果逐字可定位；本工序不改写判据结论。"
        },
        {
          "asset_id": "A11",
          "asset_class": "criterion_summary",
          "label": "判据汇总行（5/5 通过）",
          "in_report_section": "标题后",
          "locator": {
            "method": "char_span",
            "start_char": 635,
            "end_char": 650,
            "start_line": 13,
            "end_line": 13,
            "quote": "**判据汇总** 5/5 通过",
            "unique": true,
            "quote_sha256": "7a00af3138ccb4c325d6184c80b0ff8d498b79870f0f2cbdd28245cde0c97279"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "汇总陈述，注册以固定原文位置；不据此打 verified 标。"
        },
        {
          "asset_id": "A12",
          "asset_class": "parameter_table",
          "label": "输入参数表（p0 / ex / A0 / CoV / F_k / R_k / rho_ln p,ln A / sigma_ln F）",
          "in_report_section": "①",
          "locator": {
            "method": "char_span",
            "start_char": 946,
            "end_char": 1484,
            "start_line": 19,
            "end_line": 32,
            "quote": "| 参数 | 取值 | 说明 |\n|---|---|---|\n| $p_0$ | 2.500 MPa | 参考面积处冰压中值 |\n| $ex$ | 0.400 | ISO 压力–面积指数 |\n| $A_0$ / $A_{med}$ | 5.00 / 5.00 m² | 参考面积 / 年极值接触面积中值 |\n| CoV($A$) | 0.350 | 年极值接触面积对数正态变异系数 |\n| CoV($\\varepsilon_p$) | 0.150 | 压力规律认知不确定性（中值归一）|\n| CoV($k_F$) | 0.100 | 载荷模型不确定性 |\n| CoV($R$) | 0.120 | 构件抗力变异系数 |\n| 特征冰力 $F_k$ | 23.517 MN | 100 年超越（年超越概率 1e-2）|\n| 特征抗力 $R_k$ | 33.660 MN | 5 % 分位 |\n| $\\rho_{\\ln p,\\ln A}$ | -0.6737 | 由指数与面积散度解析给出 |\n| $\\sigma_{\\ln F}$ | 0.2717 | 计入负相关 |\n| $\\sigma_{\\ln F}$（$\\rho$=0 对照）| 0.4077 | 同一对边缘分布，忽略相关 |",
            "unique": true,
            "quote_sha256": "48ffa7a30711fa3c43d3f45814ed623ec3ae0ecd4c40e715a3a867b59abd6029"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "参数名与取值逐字可定位；本工序不做提取、不做量纲复核。"
        },
        {
          "asset_id": "A13",
          "asset_class": "table",
          "label": "表 1 反问题解（gamma_f* / psi* / kappa* / F* / R* / 达到 beta / 迭代数 / 条件数 / 方向余弦）",
          "in_report_section": "③",
          "locator": {
            "method": "char_span",
            "start_char": 3020,
            "end_char": 3495,
            "start_line": 49,
            "end_line": 64,
            "quote": "**表 1 反问题解**\n\n| 量 | 值 |\n|---|---|\n| $\\gamma_f^*$ | **1.437056** |\n| $\\psi^*$ | **0.996007** |\n| $\\kappa^*=\\gamma_f^*\\psi^*$ | **1.431318** |\n| $F^*$ (设计点冰力) | 33.7950 MN |\n| $R^*$ (设计点抗力) | 33.7950 MN |\n| 达到的 $\\beta$ | 4.000000000000 |\n| $|\\beta-\\beta_T|$ | 0.00e+00 |\n| Newton 迭代数（三初值） | [7, 5, 5] |\n| $\\gamma_f^*$ 三初值极差 | 7.88e-11 |\n| Jacobian 条件数 | 4.791 |\n| $\\kappa$ 单变量二分解（独立复核）| 1.431318 ($\\beta$=4.000000000) |\n| 设计点方向余弦 $\\alpha$ | [0.3361, -0.0915, 0.8464, -0.4028] |",
            "unique": true,
            "quote_sha256": "a48a9a3889c1b043aa6db53443a94124252e71b20e31fca15829f05f190f9e0a"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "反问题解表。"
        },
        {
          "asset_id": "A14",
          "asset_class": "table",
          "label": "表 2 FORM 的四条独立验证（判据 a）",
          "in_report_section": "③",
          "locator": {
            "method": "char_span",
            "start_char": 3497,
            "end_char": 3926,
            "start_line": 66,
            "end_line": 74,
            "quote": "**表 2 FORM 的四条独立验证（判据 a）**\n\n| 方法 | $\\beta$ | $P_f$ | 与 FORM 相对误差 | 1σ 区间覆盖 FORM |\n|---|---|---|---|---|\n| FORM | 4.000000 | 3.1671e-05 | — | — |\n| 闭式 $\\beta_{ln}$（解析）| 4.000000 | — | 6.46e-09 | — |\n| 设计点重要性抽样 | 3.997451 | 3.2014e-05 | -6.372e-04 | 否（1σ 带仅 ±4.5e-03，比 FORM 收敛容差还窄） |\n| 粗 Monte Carlo | 3.976286 | 3.5000e-05 | -5.929e-03 | 否（95 % 带：True，区间 [3.94, 4.019]） |\n| 粗 MC + 抗力解析积分 | 4.002966 | 3.1277e-05 | +7.416e-04 | 是 |",
            "unique": true,
            "quote_sha256": "2c0f67bca76070e601976d81eddd3e3cfaa4eaa2a093f3e4782acfeff79c254e"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "FORM vs 解析 / 重要性抽样 / 粗 MC / Rao–Blackwell 四条验证面。"
        },
        {
          "asset_id": "A15",
          "asset_class": "table",
          "label": "表 3 beta 敏感性（判据 c）：伴随解析导数 vs 中心差分",
          "in_report_section": "③",
          "locator": {
            "method": "char_span",
            "start_char": 3928,
            "end_char": 4245,
            "start_line": 76,
            "end_line": 83,
            "quote": "**表 3 β 敏感性（判据 c）：包络定理解析导数 vs 中心差分**\n\n| 导数 | 解析（伴随）| 中心差分 | 相对误差 |\n|---|---|---|---|\n| $\\partial\\beta/\\partial\\kappa$ | 2.353844 | 2.353845 | -3.33e-07 |\n| $\\partial\\beta/\\partial\\gamma_f$ | 2.344445 | 2.344446 | -3.33e-07 |\n| $\\partial\\beta/\\partial\\psi$ | 3.382607 | 3.382608 | -3.33e-07 |\n| 最大相对误差 | | | 3.33e-07 |",
            "unique": true,
            "quote_sha256": "b8b01962a9ed22de9a0d11e6d55922c321e38140d3a0725a692d52ed9f4e14fd"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "伴随导数 vs 有限差分对照表。"
        },
        {
          "asset_id": "A16",
          "asset_class": "table",
          "label": "表 4 与 ISO 19906 表格分项系数偏差（判据 d，10 对）",
          "in_report_section": "③",
          "locator": {
            "method": "char_span",
            "start_char": 4247,
            "end_char": 5648,
            "start_line": 85,
            "end_line": 98,
            "quote": "**表 4 与 ISO 19906 表格分项系数偏差（判据 d）**\n\n| 表格对（$\\gamma_F\\times\\gamma_M$）| 表格值 | $\\kappa_{table}$ | $\\Delta\\gamma_f$ | $\\Delta\\psi$ | $\\Delta\\kappa$ | 判定 | 按表设计的 $\\beta$ |\n|---|---|---|---|---|---|---|---|\n| ice_action_extreme x steel_plate_yielding | (1.35, 1.10) | 1.4850 | -6.06 % | +10.44 % | +3.75 % | 带内/偏保守 | 4.1240 |\n| ice_action_extreme x steel_plate_buckling | (1.35, 1.15) | 1.5525 | -6.06 % | +15.46 % | +8.47 % | 超差/偏保守 | 4.2738 |\n| ice_action_extreme x steel_weld_connection | (1.35, 1.25) | 1.6875 | -6.06 % | +25.50 % | +17.90 % | 超差/偏保守 | 4.5547 |\n| ice_action_abnormal x steel_plate_yielding | (1.10, 1.10) | 1.2100 | -23.45 % | +10.44 % | -15.46 % | 超差/不保守 | 3.4341 |\n| ice_action_abnormal x steel_plate_buckling | (1.10, 1.15) | 1.2650 | -23.45 % | +15.46 % | -11.62 % | 超差/不保守 | 3.5838 |\n| ice_action_abnormal x steel_weld_connection | (1.10, 1.25) | 1.3750 | -23.45 % | +25.50 % | -3.93 % | 超差/不保守 | 3.8648 |\n| ice_action_frequent x steel_plate_yielding | (1.00, 1.10) | 1.1000 | -30.41 % | +10.44 % | -23.15 % | 超差/不保守 | 3.1130 |\n| ice_action_frequent x steel_plate_buckling | (1.00, 1.15) | 1.1500 | -30.41 % | +15.46 % | -19.65 % | 超差/不保守 | 3.2627 |\n| ice_action_frequent x steel_weld_connection | (1.00, 1.25) | 1.2500 | -30.41 % | +25.50 % | -12.67 % | 超差/不保守 | 3.5436 |\n| repo_anchor gamma_ice x gamma_m | (1.25, 1.15) | 1.4375 | -13.02 % | +15.46 % | +0.43 % | 超差/偏保守 | 4.0145 |",
            "unique": true,
            "quote_sha256": "562c22341a5849ad42cba883cbf3e7e2087b2e820d98a638f2d48764ff5c4146"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "表格分项系数对逐行偏差表。"
        },
        {
          "asset_id": "A17",
          "asset_class": "table",
          "label": "表 5 不保守算例（偏差 >15 % 且 kappa_table<kappa*）",
          "in_report_section": "③",
          "locator": {
            "method": "char_span",
            "start_char": 5650,
            "end_char": 6455,
            "start_line": 100,
            "end_line": 109,
            "quote": "**表 5 不保守算例（偏差 >15 % 且 $\\kappa_{table}<\\kappa^*$）**\n\n| 表格对 | $\\kappa$ 缺口 | 达到的 $\\beta$ | $\\Delta\\beta$ | $P_f/P_{f,T}$ | 按表所需 $R_k$ / 标定所需 $R_k$ |\n|---|---|---|---|---|---|\n| ice_action_abnormal x steel_plate_yielding | +15.46 % | 3.4341 | 0.5659 | 9.39× | 28.455 / 33.660 MN |\n| ice_action_abnormal x steel_plate_buckling | +11.62 % | 3.5838 | 0.4162 | 5.35× | 29.749 / 33.660 MN |\n| ice_action_abnormal x steel_weld_connection | +3.93 % | 3.8648 | 0.1352 | 1.76× | 32.336 / 33.660 MN |\n| ice_action_frequent x steel_plate_yielding | +23.15 % | 3.1130 | 0.8870 | 29.24× | 25.869 / 33.660 MN |\n| ice_action_frequent x steel_plate_buckling | +19.65 % | 3.2627 | 0.7373 | 17.42× | 27.044 / 33.660 MN |\n| ice_action_frequent x steel_weld_connection | +12.67 % | 3.5436 | 0.4564 | 6.23× | 29.396 / 33.660 MN |",
            "unique": true,
            "quote_sha256": "c6e4a778b0e64a8c267d0a00605083f7d35810a529a73736b95810445f29e697"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "不保守算例的 beta / delta beta / P_f 倍数 / R_k 需求表。"
        },
        {
          "asset_id": "A18",
          "asset_class": "table",
          "label": "表 6 负控（判据 e）：忽略 p–A 负相关",
          "in_report_section": "③",
          "locator": {
            "method": "char_span",
            "start_char": 6457,
            "end_char": 6710,
            "start_line": 111,
            "end_line": 116,
            "quote": "**表 6 负控（判据 e）：忽略 p–A 负相关**\n\n| 模型 | $\\kappa^*$ | $\\gamma_f^*$ | $\\psi^*$ | $\\sigma_{\\ln F}$ |\n|---|---|---|---|---|\n| 计入 $\\rho_{\\ln p,\\ln A}$=-0.6737 | 1.431318 | 1.437056 | 0.996007 | 0.2717 |\n| 忽略相关（$\\rho$=0）| 1.740922 | 1.852433 | 0.939803 | 0.4077 |",
            "unique": true,
            "quote_sha256": "e647fe262305eb9ef3b5d6d84060a30d4192c7f775ab4d4144500b4e740f8684"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "负控对照表。"
        },
        {
          "asset_id": "A19",
          "asset_class": "table",
          "label": "表 7 beta_T 敏感性",
          "in_report_section": "③",
          "locator": {
            "method": "char_span",
            "start_char": 6858,
            "end_char": 7242,
            "start_line": 120,
            "end_line": 127,
            "quote": "**表 7 $\\beta_T$ 敏感性**\n\n| $\\beta_T$ | $P_{f,T}$ | $\\gamma_f^*$ | $\\psi^*$ | $\\kappa^*$ | $\\mathrm{d}\\gamma_f/\\mathrm{d}\\beta_T$ |\n|---|---|---|---|---|---|\n| 3.30 | 4.834e-04 | 1.20749 | 0.96298 | 1.16279 | — |\n| 3.80 | 7.235e-05 | 1.36734 | 0.98646 | 1.34882 | 0.3280 |\n| 4.00 | 3.167e-05 | 1.43706 | 0.99601 | 1.43132 | 0.3620 |\n| 4.30 | 8.540e-06 | 1.54835 | 1.01050 | 1.56462 | — |",
            "unique": true,
            "quote_sha256": "7593215b50faf2c626b0c5f1f40074974989e5c8233e82fd89986985a3631c49"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "目标可靠度敏感性表。"
        },
        {
          "asset_id": "A20",
          "asset_class": "table",
          "label": "表 8 模型参数敏感性 d beta / d theta（在 kappa* 处，中心差分）",
          "in_report_section": "③",
          "locator": {
            "method": "char_span",
            "start_char": 7244,
            "end_char": 7551,
            "start_line": 129,
            "end_line": 137,
            "quote": "**表 8 模型参数敏感性 $\\partial\\beta/\\partial\\theta$（在 $\\kappa^*$ 处，中心差分）**\n\n| 参数 | 名义值 | $\\partial\\beta/\\partial\\theta$ |\n|---|---|---|\n| exponent | 0.4000 | +1.1474 |\n| a_cov | 0.3500 | -1.8573 |\n| pressure_model_cov | 0.1500 | -2.4270 |\n| load_model_cov | 0.1000 | -1.6383 |\n| resistance_cov | 0.1200 | +0.1134 |",
            "unique": true,
            "quote_sha256": "11c31ad7b1a4f1279b9059a719bded51f29c0f54170b23e5d4c19304b20653ba"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "模型参数敏感性表。"
        },
        {
          "asset_id": "A21",
          "asset_class": "table",
          "label": "⑥ 误差判定表（关键量 / 基准 / 误差 / 是否 <3 %）",
          "in_report_section": "⑥",
          "locator": {
            "method": "char_span",
            "start_char": 10631,
            "end_char": 11194,
            "start_line": 176,
            "end_line": 186,
            "quote": "| 关键量 | 基准 | 误差 | <3 % ? |\n|---|---|---|---|\n| FORM $\\beta$ | 闭式解析 $\\beta_{ln}$ | 6.46e-09 | 是 |\n| FORM $\\beta$ | 设计点重要性抽样 | 6.37e-04 | 是 |\n| 反问题残差 $|\\beta(\\gamma^*) - \\beta_T|$ | 目标 4.0 | 0.00e+00 | 是（阈值 1e-3） |\n| 伴随 $\\partial\\beta/\\partial\\kappa$ | 中心差分 | -3.33e-07 | 是 |\n| 伴随 $\\partial\\beta/\\partial\\gamma_f$ | 中心差分 | -3.33e-07 | 是 |\n| 伴随 $\\partial\\beta/\\partial\\psi$ | 中心差分 | -3.33e-07 | 是 |\n| $\\kappa^*$（Newton）| $\\kappa^*$（二分）| 2.31e-11 | 是 |\n| 粗 MC $\\beta$ | FORM | 5.93e-03 | 是 |\n| 与 ISO A.2×A.3（极值+屈服）$\\kappa$ 偏差 | 表格 1.485 | +0.0375 | 否（表格值高于标定值，偏保守侧） |",
            "unique": true,
            "quote_sha256": "32cba0a8aac678a97e272167109172c0d1b3563b5ba051d16bae0ac46d1ac720"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "误差判定逐项表。"
        },
        {
          "asset_id": "A22",
          "asset_class": "statement",
          "label": "⑥ 结论段（FORM 与解析值 / IS 一致性、反问题残差、伴随导数、粗 MC 噪声说明）",
          "in_report_section": "⑥",
          "locator": {
            "method": "char_span",
            "start_char": 11196,
            "end_char": 11377,
            "start_line": 188,
            "end_line": 188,
            "quote": "**结论**：FORM 与解析值、重要性抽样的一致性远优于 3 %（均为 1e-2 % 量级）；反问题残差 1e-11；伴随导数与有限差分一致到 1e-7；唯一未达 3 % 量级的对照是**粗 MC 的统计噪声**（1σ 约 8 %，Rao–Blackwell 化后约 6 %，两者 95 % 带均覆盖 FORM），属采样误差而非模型误差，已在表 2 如实列出。",
            "unique": true,
            "quote_sha256": "0983f6889d4a658192da24b214c06be1f7cdd6862886050a6a639129632b79a2"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "结论陈述，注册以固定原文位置；是否成立由平台门裁定，本工序不打 verified 标。"
        },
        {
          "asset_id": "A23",
          "asset_class": "figure_reference",
          "label": "图 1 联合 p–A 状态（fig1_pa_joint.png）",
          "in_report_section": "④",
          "locator": {
            "method": "char_span",
            "start_char": 7741,
            "end_char": 7827,
            "start_line": 143,
            "end_line": 143,
            "quote": "![fig1](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig1_pa_joint.png)",
            "unique": true,
            "quote_sha256": "773a2a33b8c8a41e5cae200dbb073ebd6efa23088d46042459f452ba8957af6e"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "record.figures[] entry with matching filename + png payload present?",
            "result": "unresolved",
            "detail": "record_entry_found=True payload_in_record=False local_copy_in_worktree=False",
            "record_figure": "fig1_pa_joint.png"
          },
          "note": "markdown 内为绝对路径（指向产出任务 8350 的工作树），PNG 字节不在本仓、也不在报告记录 figures[] 的载荷内，故登记引用、未解析字节。 报告记录 figures[] 以 name+caption 登记该图，但整份记录任一 figure 都不含 png 载荷（payload_present=False）。"
        },
        {
          "asset_id": "A24",
          "asset_class": "figure_reference",
          "label": "图 2 beta vs kappa（fig2_beta_vs_kappa.png）",
          "in_report_section": "④",
          "locator": {
            "method": "char_span",
            "start_char": 8015,
            "end_char": 8106,
            "start_line": 147,
            "end_line": 147,
            "quote": "![fig2](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig2_beta_vs_kappa.png)",
            "unique": true,
            "quote_sha256": "f7de44cb6ae2852174c8fbaccda8b70fb2ab7fefb56f6de6ea3bdb6fec8b9b93"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "record.figures[] entry with matching filename + png payload present?",
            "result": "unresolved",
            "detail": "record_entry_found=True payload_in_record=False local_copy_in_worktree=False",
            "record_figure": "fig2_beta_vs_kappa.png"
          },
          "note": "同上：仅登记引用，未取字节。 报告记录 figures[] 以 name+caption 登记该图，但整份记录任一 figure 都不含 png 载荷（payload_present=False）。"
        },
        {
          "asset_id": "A25",
          "asset_class": "figure_reference",
          "label": "图 3 Newton 收敛与劈分曲线（fig3_newton.png）",
          "in_report_section": "④",
          "locator": {
            "method": "char_span",
            "start_char": 8321,
            "end_char": 8405,
            "start_line": 151,
            "end_line": 151,
            "quote": "![fig3](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig3_newton.png)",
            "unique": true,
            "quote_sha256": "520f27ddc2383516f0d8cd855172f5a44c032d647d79149b0a0913b93a25ec9b"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "record.figures[] entry with matching filename + png payload present?",
            "result": "unresolved",
            "detail": "record_entry_found=True payload_in_record=False local_copy_in_worktree=False",
            "record_figure": "fig3_newton.png"
          },
          "note": "同上：仅登记引用，未取字节。 报告记录 figures[] 以 name+caption 登记该图，但整份记录任一 figure 都不含 png 载荷（payload_present=False）。"
        },
        {
          "asset_id": "A26",
          "asset_class": "figure_reference",
          "label": "图 4 与 ISO 表格分项系数逐项偏差图（fig4_iso_deviations.png）",
          "in_report_section": "④",
          "locator": {
            "method": "char_span",
            "start_char": 8587,
            "end_char": 8679,
            "start_line": 155,
            "end_line": 155,
            "quote": "![fig4](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig4_iso_deviations.png)",
            "unique": true,
            "quote_sha256": "43fb0de9c7a6f18c7630dd9ba857b77781762f724fbfb74ac9736060334f3e76"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "record.figures[] entry with matching filename + png payload present?",
            "result": "unresolved",
            "detail": "record_entry_found=True payload_in_record=False local_copy_in_worktree=False",
            "record_figure": "fig4_iso_deviations.png"
          },
          "note": "同上：仅登记引用，未取字节。 报告记录 figures[] 以 name+caption 登记该图，但整份记录任一 figure 都不含 png 载荷（payload_present=False）。"
        },
        {
          "asset_id": "A27",
          "asset_class": "figure_reference",
          "label": "图 5 负控（fig5_negative_control.png）",
          "in_report_section": "④",
          "locator": {
            "method": "char_span",
            "start_char": 8913,
            "end_char": 9007,
            "start_line": 159,
            "end_line": 159,
            "quote": "![fig5](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig5_negative_control.png)",
            "unique": true,
            "quote_sha256": "a424a9db6c7a6e89ebb3fb6082fec3cf6147aa04a485946b6d35e58e4d12163d"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "record.figures[] entry with matching filename + png payload present?",
            "result": "unresolved",
            "detail": "record_entry_found=True payload_in_record=False local_copy_in_worktree=False",
            "record_figure": "fig5_negative_control.png"
          },
          "note": "同上：仅登记引用，未取字节。 报告记录 figures[] 以 name+caption 登记该图，但整份记录任一 figure 都不含 png 载荷（payload_present=False）。"
        },
        {
          "asset_id": "A28",
          "asset_class": "figure_reference",
          "label": "图 6 灵敏度（fig6_sensitivity.png）",
          "in_report_section": "④",
          "locator": {
            "method": "char_span",
            "start_char": 9174,
            "end_char": 9263,
            "start_line": 163,
            "end_line": 163,
            "quote": "![fig6](/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/fig6_sensitivity.png)",
            "unique": true,
            "quote_sha256": "93c94f185537d60f86fa1e728dc8fafa7f68f0ce3f0e9b21d8c8a0b37b742a5e"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "record.figures[] entry with matching filename + png payload present?",
            "result": "unresolved",
            "detail": "record_entry_found=True payload_in_record=False local_copy_in_worktree=False",
            "record_figure": "fig6_sensitivity.png"
          },
          "note": "同上：仅登记引用，未取字节。 报告记录 figures[] 以 name+caption 登记该图，但整份记录任一 figure 都不含 png 载荷（payload_present=False）。"
        },
        {
          "asset_id": "A29",
          "asset_class": "data_artifact_reference",
          "label": "结果 JSON：in101_n09_results.json（报告全部数字的唯一来源）",
          "in_report_section": "审计链",
          "locator": {
            "method": "char_span",
            "start_char": 11398,
            "end_char": 11480,
            "start_line": 192,
            "end_line": 192,
            "quote": "/root/tp-agent/work/m8350/artifacts/iso19906_target_inverse/in101_n09_results.json",
            "unique": true,
            "quote_sha256": "4eba00b21ccbb7c3b19d39857d4177e92227fe637615f41b6e29a26e8d53d295"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "reference parsed from markdown; target bytes present in this package's scope?",
            "result": "unresolved",
            "detail": "target path is outside this worktree; not fetched (scope: report 9645 only)"
          },
          "note": "绝对路径位于产出任务 8350 的工作树内，不在本仓检出范围内；按边界未跨任务取件，也未解析其内容。"
        },
        {
          "asset_id": "A30",
          "asset_class": "record_field_reference",
          "label": "结果 JSON 判据字段 machine_criteria / criteria_summary",
          "in_report_section": "审计链",
          "locator": {
            "method": "char_span",
            "start_char": 11520,
            "end_char": 11561,
            "start_line": 193,
            "end_line": 193,
            "quote": "`machine_criteria` 5 条，`criteria_summary`",
            "unique": true,
            "quote_sha256": "acf2ac72cf233803145ea0f0edf628637b4c6a5438b9e77c5cd1ba5974a0b9e3"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "reference parsed from markdown; target bytes present in this package's scope?",
            "result": "unresolved",
            "detail": "field names quoted from the report's own restatement; source JSON not fetched"
          },
          "note": "字段名与其值取自报告转述；原 JSON 未取件，故字段值的机器可读副本属未解析。"
        },
        {
          "asset_id": "A31",
          "asset_class": "code_reference",
          "label": "冰区分项系数模块 tensorphysics.ice_partial_factors",
          "in_report_section": "标题 / ②",
          "locator": {
            "method": "char_span",
            "start_char": 179,
            "end_char": 214,
            "start_line": 3,
            "end_line": 3,
            "quote": "`tensorphysics.ice_partial_factors`",
            "unique": true,
            "quote_sha256": "911933d86f96c2baa403e9f959324a07dc5df1f7ee4531f0ef4e4c9c7ee6ed33"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "reference parsed from markdown; target bytes present in this package's scope?",
            "result": "unresolved",
            "detail": "local probe src/tensorphysics=False (producing repo is TensorPhysics, this checkout is TensorKnowledge)"
          },
          "note": "属 TensorPhysics 仓；本检出为 TensorKnowledge，本地无该模块（见 source.local_availability 实测探针）。"
        },
        {
          "asset_id": "A32",
          "asset_class": "code_reference",
          "label": "求解器 tensorphysics.structural.reliability（FORM/HL-RF、SORM、IS、MC）",
          "in_report_section": "审计链",
          "locator": {
            "method": "char_span",
            "start_char": 11630,
            "end_char": 11668,
            "start_line": 194,
            "end_line": 194,
            "quote": "`tensorphysics.structural.reliability`",
            "unique": true,
            "quote_sha256": "87190b604eca6ab620eb41e225fa8d9019a34ed812b5a02ba9041caf839185ea"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "reference parsed from markdown; target bytes present in this package's scope?",
            "result": "unresolved",
            "detail": "local probe src/tensorphysics=False (producing repo is TensorPhysics, this checkout is TensorKnowledge)"
          },
          "note": "同上：跨仓引用，本检出不可解析。"
        },
        {
          "asset_id": "A33",
          "asset_class": "code_reference",
          "label": "分布 / Nataf 模块 tensorphysics.structural.distributions",
          "in_report_section": "审计链",
          "locator": {
            "method": "char_span",
            "start_char": 11693,
            "end_char": 11733,
            "start_line": 194,
            "end_line": 194,
            "quote": "`tensorphysics.structural.distributions`",
            "unique": true,
            "quote_sha256": "3a666262bbd1a76cd5d77a1a190a88212eaf0d46d19ce43d96b1adfa3f21ea94"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "reference parsed from markdown; target bytes present in this package's scope?",
            "result": "unresolved",
            "detail": "local probe src/tensorphysics=False (producing repo is TensorPhysics, this checkout is TensorKnowledge)"
          },
          "note": "同上：跨仓引用，本检出不可解析。"
        },
        {
          "asset_id": "A34",
          "asset_class": "code_reference",
          "label": "脚本 p_area_joint.py（联合 p–A 状态）",
          "in_report_section": "②",
          "locator": {
            "method": "char_span",
            "start_char": 1529,
            "end_char": 1546,
            "start_line": 36,
            "end_line": 36,
            "quote": "`p_area_joint.py`",
            "unique": true,
            "quote_sha256": "7c2bcb282b0dd6e76809b0f9144189f2bb94056c92c8ef70ebd1cae8c32c28fa"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "reference parsed from markdown; target bytes present in this package's scope?",
            "result": "unresolved",
            "detail": "local probe benchmarks/iso19906_partial_factors=False"
          },
          "note": "文件不在本检出（benchmarks/ 下无 iso19906 目录，见 source.local_availability 实测探针）。"
        },
        {
          "asset_id": "A35",
          "asset_class": "code_reference",
          "label": "脚本 target_reliability_inverse.py（两方程两未知量反问题）",
          "in_report_section": "②",
          "locator": {
            "method": "char_span",
            "start_char": 2009,
            "end_char": 2040,
            "start_line": 37,
            "end_line": 37,
            "quote": "`target_reliability_inverse.py`",
            "unique": true,
            "quote_sha256": "a6f5bbb55f68f27106e9c7fe94801edbfecb67e6cff9deab988ec526d96873a2"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "reference parsed from markdown; target bytes present in this package's scope?",
            "result": "unresolved",
            "detail": "local probe benchmarks/iso19906_partial_factors=False"
          },
          "note": "同上：文件不在本检出。"
        },
        {
          "asset_id": "A36",
          "asset_class": "code_reference",
          "label": "入口函数 run_study()（结果 JSON 直出）",
          "in_report_section": "审计链",
          "locator": {
            "method": "char_span",
            "start_char": 11495,
            "end_char": 11511,
            "start_line": 192,
            "end_line": 192,
            "quote": "`run_study()` 直出",
            "unique": true,
            "quote_sha256": "50c4b9bac1b4ecd23cd7c5475e7bdf1003bc0de4149788236c084a2812c941b5"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "reference parsed from markdown; target bytes present in this package's scope?",
            "result": "unresolved",
            "detail": "reference registered at its mention; target bytes out of this package's scope"
          },
          "note": "函数定义不在本检出；只登记调用点。"
        },
        {
          "asset_id": "A37",
          "asset_class": "repro_command",
          "label": "复现命令 PYTHONPATH=src python3 benchmarks/iso19906_partial_factors/run_in101_n09.py",
          "in_report_section": "审计链",
          "locator": {
            "method": "char_span",
            "start_char": 11747,
            "end_char": 11822,
            "start_line": 195,
            "end_line": 195,
            "quote": "PYTHONPATH=src python3 benchmarks/iso19906_partial_factors/run_in101_n09.py",
            "unique": true,
            "quote_sha256": "d53dc8676c61f7a30f45a6c23d551ff49f373739b412d86272e7765ea481863a"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "reference parsed from markdown; target bytes present in this package's scope?",
            "result": "unresolved",
            "detail": "local probe benchmarks/iso19906_partial_factors=False"
          },
          "note": "命令原文登记；本检出不具备该 benchmark 与依赖模块，故本次未执行（不声称可复现）。"
        },
        {
          "asset_id": "A38",
          "asset_class": "external_standard_table",
          "label": "ISO 19906 Annex A.2 × A.3 分项系数表（9 对）",
          "in_report_section": "⑤/⑥",
          "locator": {
            "method": "char_span",
            "start_char": 10185,
            "end_char": 10211,
            "start_line": 171,
            "end_line": 171,
            "quote": "ISO 19906 Annex A 正文不在工作树内",
            "unique": true,
            "quote_sha256": "9760901888b50a9ced8bf0a9c987e09536e58c724bcf6143bce2d6e516b08762"
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "report body declares the material unavailable in the work tree",
            "result": "absent",
            "detail": "declaration quoted verbatim at locator; not supplemented by this package"
          },
          "note": "报告自述该正文不在工作树内，且 A.2/A.3 为二次文献转录（见 source_tier 资产）；本工序不补录、不推断表格值。"
        },
        {
          "asset_id": "A39",
          "asset_class": "provenance_flag",
          "label": "出处等级标记 source_tier=secondary, primary_source_verified=False",
          "in_report_section": "⑤",
          "locator": {
            "method": "char_span",
            "start_char": 10228,
            "end_char": 10284,
            "start_line": 171,
            "end_line": 171,
            "quote": "`source_tier=secondary`, `primary_source_verified=False`",
            "unique": true,
            "quote_sha256": "ebe6ea628ac66db90c5b383459132c6a5e918583bc8c5c28698b2f9b627e853e"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "出处等级标记本身在原文中可逐字定位；它声明所引 ISO 表为二次来源，故由该表得出的裁决为 conditional。"
        },
        {
          "asset_id": "A40",
          "asset_class": "external_standard_reference",
          "label": "JCSS/ISO 2394 设计值劈分约定",
          "in_report_section": "②/⑤",
          "locator": {
            "method": "char_span",
            "start_char": 2254,
            "end_char": 2299,
            "start_line": 41,
            "end_line": 41,
            "quote": "JCSS/ISO 2394 设计值劈分（荷载分项系数 = FORM 设计点作用/特征作用）",
            "unique": true,
            "quote_sha256": "659e60881ebf3a1065941f39fa1e164d90a25c5d5daab2b45e3680d37be280d7"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "reference parsed from markdown; target bytes present in this package's scope?",
            "result": "unresolved",
            "detail": "standard text is not in the worktree; no primary copy taken"
          },
          "note": "规范条文本身不在工作树内，仅登记报告对该约定的引用位置；劈分约定未被本工序核验。"
        },
        {
          "asset_id": "A41",
          "asset_class": "repo_reference",
          "label": "产出仓 TensorPhysics",
          "in_report_section": "标题",
          "locator": {
            "method": "char_span",
            "start_char": 149,
            "end_char": 169,
            "start_line": 3,
            "end_line": 3,
            "quote": "**仓库** TensorPhysics",
            "unique": true,
            "quote_sha256": "b3b8e01f7f52801a3028be4c4e2e58da0e0c1b6ab778b14d329bda157e5009e2"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "reference parsed from markdown; target bytes present in this package's scope?",
            "result": "unresolved",
            "detail": "reference registered at its mention; target bytes out of this package's scope"
          },
          "note": "跨仓：本检出为 TensorKnowledge，未取 TensorPhysics 代码。"
        },
        {
          "asset_id": "A42",
          "asset_class": "prior_node_reference",
          "label": "前序节点 IN13-W3-N10（plate-stress 极限状态、单参数反问题）",
          "in_report_section": "标题",
          "locator": {
            "method": "char_span",
            "start_char": 337,
            "end_char": 348,
            "start_line": 3,
            "end_line": 3,
            "quote": "IN13-W3-N10",
            "unique": true,
            "quote_sha256": "59a9ed8aa6c67d00a3b049673bb7d49911502c94412022d61dff9971752f9264"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "reference parsed from markdown; target bytes present in this package's scope?",
            "result": "unresolved",
            "detail": "reference registered at its mention; target bytes out of this package's scope"
          },
          "note": "前序节点产物未在本包范围内，仅登记引用。"
        },
        {
          "asset_id": "A43",
          "asset_class": "numeric_anchor",
          "label": "锚点 kappa* = 1.431318（表 1 行）",
          "in_report_section": "③",
          "locator": {
            "method": "char_span",
            "start_char": 3114,
            "end_char": 3160,
            "start_line": 55,
            "end_line": 55,
            "quote": "| $\\kappa^*=\\gamma_f^*\\psi^*$ | **1.431318** |",
            "unique": true,
            "quote_sha256": "49ffc1f2e72cf46f9279b68d907561540df5e6de860204f832d5fb4a2cbd6266"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "数值锚点：为下游工序提供逐字可解析的定位，不构成对数值正确性的判定。"
        },
        {
          "asset_id": "A44",
          "asset_class": "numeric_anchor",
          "label": "锚点 达到的 beta = 4.000000000000（表 1 行）",
          "in_report_section": "③",
          "locator": {
            "method": "char_span",
            "start_char": 3223,
            "end_char": 3255,
            "start_line": 58,
            "end_line": 58,
            "quote": "| 达到的 $\\beta$ | 4.000000000000 |",
            "unique": true,
            "quote_sha256": "bbf78706461d46dd93953a49a284ee1489e560157bff7fefc6d3010c0bb7602d"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "同上：仅定位。"
        },
        {
          "asset_id": "A45",
          "asset_class": "numeric_anchor",
          "label": "锚点 负控 delta gamma_f = +28.90 %（表 6 后陈述）",
          "in_report_section": "③",
          "locator": {
            "method": "char_span",
            "start_char": 6712,
            "end_char": 6856,
            "start_line": 118,
            "end_line": 118,
            "quote": "$\\Delta\\gamma_f^*$ = +28.90 %，$\\Delta\\kappa^*$ = +21.63 %；把偏大的 $\\kappa$ 用到**物理**模型上会得到 $\\beta$ = 4.6597（过度设计 +0.6597）。判据阈值 5 %，实际 +28.90 % → 检出。",
            "unique": true,
            "quote_sha256": "b3cdab136b2927cb0c5a65547f73b9d911496f6863a2b5865493e913d0d16f9e"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "同上：仅定位。"
        },
        {
          "asset_id": "A46",
          "asset_class": "design_format",
          "label": "设计格式 gamma_f * F_k <= R_k / psi, kappa = gamma_f * psi",
          "in_report_section": "标题",
          "locator": {
            "method": "char_span",
            "start_char": 226,
            "end_char": 278,
            "start_line": 3,
            "end_line": 3,
            "quote": "`gamma_f * F_k <= R_k / psi,  kappa = gamma_f * psi`",
            "unique": true,
            "quote_sha256": "854242e6ff94137b8545de791b5b542698ef08c725625dd640707e29c86195fa"
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote is a unique verbatim slice of source markdown; md[start:end]==quote",
            "result": "resolved"
          },
          "note": "设计格式原文（含双空格），供下游工序逐字引用。"
        }
      ],
      "claims": [],
      "claims_note": "契约 notes 允许空 claims 数组：本工序只登记资产，不做抽取；未生成任何知识对象，也未把任何结论标为 verified。",
      "coverage": {
        "unregistered_inline_code_tokens": [],
        "unregistered_markdown_images": [],
        "exempt_tokens": {
          "a_form_vs_simulation": "criterion id inside the machine-criteria table asset (A10)",
          "b_inverse_solved_unique": "criterion id inside the machine-criteria table asset (A10)",
          "c_beta_sensitivity_vs_finite_difference": "criterion id inside the machine-criteria table asset (A10)",
          "d_iso_table_deviation_map": "criterion id inside the machine-criteria table asset (A10)",
          "e_negative_control_pa_correlation": "criterion id inside the machine-criteria table asset (A10)",
          "rho0": "symbol name used in prose; no independent material to register",
          "matplotlib": "third-party library name; report pins no version, so nothing to hash or resolve",
          "tensorphysics.structural": "package prefix of two already-registered module assets",
          "criterion_interpretation": "JSON field name of the results record; no independent material",
          "conditional": "verdict label produced by the producer; not an asset"
        },
        "note": "inline code token / markdown 图片必须落在某个 asset 的字符区间内，或在此显式豁免并给出理由。"
      },
      "integrity": {
        "quote_uniqueness": true,
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "locator_span_equality": true,
        "asset_ids_unique": true
      },
      "platform_probe": {
        "/tensor/reports/9645/artifacts": {
          "status": "http_404"
        },
        "/tensor/artifacts?report_id=9645": {
          "status": "http_404"
        }
      }
    }
  },
  "claims": []
}
```
