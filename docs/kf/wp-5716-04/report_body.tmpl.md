## ① 本工序做了什么

目标：对 report_id=5716（IN10-G1 冰区航行全流程总攻验收门）的产出做**独立红队审核**（审核对象 wp-5716-01），只判语义保真：报告里的数量、判据、结论是否自洽、可复算、可定位。本单不改报告任何字节、不写其它 report_id、不给出 verified 标记（verification 由平台门计算）。

结论（disposition）：**needs-fix**。诚实基调可信（4 项披露项如实标不通过、外部锚点未粉饰、结构结论自认不通过），但存在 2 条阻断级事务性缺陷：同一物理量在报告内出现两个不同数值（C3 总时长 63.3 h vs 68.2 h），以及"7 项披露"与报告里实际可定位的 4 个披露 ID 不可调和。物理结论不必推翻，修复成本=编辑性订正 + 新增 1 条断言。

审核面统计：findings {{n_findings}} 条（high {{sev_high}} / medium {{sev_med}} / low {{sev_low}}），其中阻断 {{n_blocking}} 条；独立复算后**被证实自洽**的量 {{n_corroborated}} 条（列在 ④ 下半表，避免只报负面）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文并钉哈希**：`scripts/kf/fetch_report_5716.py` 走 `GET $TENSOR_API_BASE/tensor/reports/5716`，把 `markdown` 原样落盘到 `docs/kf/wp-5716-04/source_5716.md`，重算 sha256 = `{{sha}}`，与契约 source_hash 逐字相等（平台可独立重算，本单已自算一次）。
2. **零手抄机制（不是口号，是断言）**：`scripts/kf/review_wp_5716_04.py` 把审核要引用的 {{n_quotes}} 段引文登记在常量表 `Q` 里，运行时对每段做 `in markdown` 断言；任一段漂移即 `SystemExit`，不产出结果。④ 全部引文均由此断言担保。
3. **独立复算（reviewer 自己算，不采信自报）**：几何先验 Cb、B2 板格 β 修正后的 20 年利用率、D1/C3 平均航速与冰段速度反演、能量尺度、以及跨章节同量冲突扫描，全部由 Python 现算并写入 `docs/kf/wp-5716-04/recompute.json`（本报告数字全部来自该文件或引文，无手抄）。
4. **披露集合枚举**：对 markdown 做 `D0[0-9]-[A-Z0-9-]+` 正则，数出实际可定位的披露 ID。
5. **上下文隔离**：只读 `markdown` 字段（+ 仅用于溯源钉点的 id/title/tags/created_at）；**未使用**生产者的 summary/解释，**未接触**生产者代码与 `artifacts/campaign_ice_nav/*`（不在本工作树可及面）。
6. **出图**：`scripts/kf/fig_wp_5716_04.py` 从 markdown 的 ⑥ 表**直接解析**百分比行出图（数值不手抄），另从 recompute.json 出时间/速度闭合图（本机无 CJK 字体，图内标签为 reviewer 英译，已在图题声明）。
7. **自检门**：`scripts/kf/validate_wp_5716_04.py` 做 schema 校验 + 现场重取原文重算哈希 + 引文逐段复核 + 报告内 ```json 块唯一性与等价性。

一键复跑（工作树根执行，幂等；缺网可全部加 --offline 走 runs/ 快照）：

```text
python3 scripts/kf/fetch_report_5716.py --out docs/kf/wp-5716-04/source_5716.md && \
python3 scripts/kf/review_wp_5716_04.py --offline && \
python3 scripts/kf/fig_wp_5716_04.py && \
python3 scripts/kf/assemble_wp_5716_04.py --offline && \
python3 scripts/kf/validate_wp_5716_04.py && \
python3 -m pytest tests/test_wp_5716_04_review.py -q && \
python3 scripts/kf/verify_published_5716_04.py --report-id <published_id>
```

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-5716-04/review_report.json` | **契约声明的输出**：findings（含 severity/blocking/复现方法/影响/修复建议）+ corroborated_claims + checks_not_run + disposition |
| `docs/kf/wp-5716-04/recompute.json` | 全部复算中间量（输入、Cb 两口径、β 修正谱、速度/时间/能量闭合、冲突扫描、枚举计数），报告数字的唯一来源 |
| `docs/kf/wp-5716-04/figures/fig_review_errors.png` | ⑥ 表 10 个百分比项 vs 3% 验收线 / 25% 预登记筛选线（对数轴，值由 markdown 解析） |
| `docs/kf/wp-5716-04/figures/fig_review_closure.png` | 由报告总量反演的冰段平均速度 vs 报出的 4.50 kn 设计点 |
| `docs/kf/wp-5716-04/source_5716.md` (+`.meta.json`) | 原文快照与哈希钉点（provenance 可复算） |
| `scripts/kf/{fetch_report_5716,review_wp_5716_04,fig_wp_5716_04,validate_wp_5716_04}.py` | 一键复跑工具链 |
| `docs/kf/wp-5716-04/kf_result.json` | 结果信封（给机器门），与本报告唯一 json 块逐字一致 |

## ④ 证据定位表（claim/字段 → 原文引文片段，逐字）

阻断与主要缺陷：

| # | 审核判断 | 原文引文（逐字，脚本断言在文） |
|---|---|---|
| F1 | C3 总时长两处不同值 | 「{{q_c3_totals}}」 ／ 「{{q_d1_vs_c3_time}}」 |
| F2 | 声称 7 项披露、实可定位 4 个 ID | 「{{q_disclosure_count}}」 ／ 「{{q_disclosure_four}}」 |
| F3 | 16 项断言无一闭合时间/能量；D1↔C3 未对账 | 「{{q_gate_threshold}}」 ／ 「{{q_d1_route}}」 ／ 「{{q_regrid}}」 |
| F4 | 墙钟两值（50.7 s vs 约 41.5 s） | 「{{q_wallclock_2}}」 ／ 「{{q_wallclock_9}}」 |
| F5 | G01 的 Cb 公式缺密度步，字面代入自破其 2% 容差 | 「{{q_geom_cb}}」 ／ 「{{q_geom_params}}」 |
| F6 | ⑥ 漏项（GM 0.09%）与无基线技能值 | 「{{q_e1_gm}}」 ／ 「{{q_a2_line}}」 |
| F7 | 跨库 REAL 行 vs 未挂载降级条件 | 「{{q_fem_row}}」 ／ 「{{q_withheld_cond}}」 |
| F8 | 质量误差恒零未给范数 | 「{{q_a2_line}}」 |
| F9 | 测试计数无工件身份 | 「{{q_tests}}」 ／ 「{{q_artifacts}}」 |
| F10 | 门阈 8/16 且 16 项均为自洽性；外部锚全数不通过 | 「{{q_gate_threshold}}」 ／ 「{{q_d07_row}}」 ／ 「{{q_b2_beta_row}}」 |

独立复算**通过**的量（避免只报负面；也说明本次审核没有制造伪缺陷）：

| # | reviewer 复算 | 结果 | 结论 |
|---|---|---|---|
| V1 | Cb 两口径 | 字面（无密度）Cb={{cb_literal}}，相对差 {{cb_rel_lit}}%（>2% 容差，故 F5）；补 ρ=1.025 t/m³ 后 Cb={{cb_rho}} | 报出 0.82007 可复现，缺陷仅在"未声明密度步" |
| V2 | 几何比 | L/B={{lb}}、B/T={{bt}} | 与「6.333 / 2.609」一致 |
| V3 | β 修正后利用率 | β_B2≈{{beta_b2}}，按 S-N 斜率 m=3 得 {{b2_12_4}} | 与原文「12.4」一致（m=3 与方向性未在文中声明，故只列 low 提示） |
| V4 | D07 65.6% | 4.50×(1+0.656)={{d07_implied}} kn | 与"同 (h,C) 下 ≈7.45 kn"自洽 |
| V5 | 平均航速 | D1 {{d1_mean}} kn、C3(63.3h) {{c3_mean}} kn、C3(68.2h) {{c3_mean_alt}} kn | 与 13 kn 服务航速量级自洽 |
| V6 | 能量尺度 | 203388 kWh / 63.3 h = {{avg_kw}} kW（占 18 MW 的 {{avg_load}}%），{{kwh_nm}} kWh/nm | 量级合理，无独立性冲突 |
| V7 | A2 同化增益 | (0.1444−0.1145)/0.1444 = {{a2_gain}}% | 与"同化优于冰图"一致 |

## ⑤ 注意点与局限

1. **不可复跑的部分明确标 not_run（不标 pass）**：`modules.campaign_ice_nav.run_campaign` 的代码与 `artifacts/campaign_ice_nav/campaign_acceptance.json` sha256 台账都不在本工作树可及面，故 G13「台账可复算」、pytest 13 passed、上游 116 项测试、TensorFEM Q4 0.211% 均**未运行**，只登记为证据未绑定（F9/F7），不判真假。
2. **upstream_packages_completed 无法从平台 API 核验**：探测 `/tensor/reports/5716/packages`、`/tensor/work_packages?report_id=5716`、`/kf/packages?report_id=5716` 全部 404，`/tensor/reports?tags=...` 的 tags 过滤被服务端忽略（返回 total=100 与 limit 相同）。故该项在 ⑥ 标 `?`（unknown），不冒充 PASS。
3. **单审核人、无第二意见**，且审核面只有 markdown：报告引用的图（4 张在 figures 字段）本单未逐图核验数值一致性。
4. **F3 的"2.55×"是反演量不是断言错误**：由报告自身总量（684.1 nm、冰区 27.0%、开阔水 13 kn）反演冰段均速；若设计点 4.50 kn 仅代表最不利单个 lead，则反演值高于设计点属正常。报告缺逐段表，故该条只作为"门覆盖缺口"提，不作为"报告算错"。
5. **F5 的严重度按"可复算性"定，不按"结果错"定**：插入 ρ 后数值完全复现，所以这不是算错，而是断言文本不自足——但按报告自己的 2% 容差，字面代入是 FAIL，故必须写清 formula。
6. **未把任何结论标 verified**：本单只给 pass/fail/needs-fix 与证据，`verification_status` 字段显式写 `NOT_VERIFIED_BY_REVIEWER`。
7. 图内标签为英译（宿主无 CJK 字体），数值全部程序化解析，未手抄。

## ⑥ 自检：逐条对照 acceptance

| acceptance | 判定 | 依据 |
|---|---|---|
| valid_json | 是 | `docs/kf/wp-5716-04/kf_result.json` 与报告唯一 json 块均由 json.load 解析通过（validate 脚本） |
| schema_pass | 是 | 对 `schemas/kf_result.v1.schema.json` 做 jsonschema 校验通过（必填 5 字段、additionalProperties=false、source_hash 正则 `^sha256:[0-9a-f]{64}$`） |
| reviewer_independent | 是 | 上下文仅 markdown + 自算；未用 producer summary/解释；未读其它 report_id。隔离声明写入 review_report.json 的 reviewer_independence 段 |
| upstream_packages_completed | ? unknown（不冒充 PASS） | 平台无 packages 端点（3 个候选路径 404，tags 过滤被忽略）；可达的唯一上游证据是 report 5716 本体（哈希相符）。见 ⑤.2 |
| constraints.review_prompt_not_copied_from_producer | 是 | 审核提示由本单契约文本给出，未从生产者产物反向取用；findings 全部为 reviewer 自算/自定位 |
| constraints.reviewer_context_excludes_producer_explanation | 是 | 只用 `markdown` 字段；summary 字段仅在 meta.json 中留档未被引用（findings 每条引文均可在 markdown 逐字定位） |
| constraints.do_not_mark_claims_as_verified | 是 | 全报告无 verified 标记；`verification_status=NOT_VERIFIED_BY_REVIEWER`；信封不含任何 verified 字段 |
| output.review_report.json | 是 | `docs/kf/wp-5716-04/review_report.json`（信封 outputs 键名一致） |

honest-FAIL 记录（不粉饰）：`upstream_packages_completed` 无法核验 → 标 unknown；本单**未运行**被测系统、**未复核**报告 4 张图、**未获**第二审核人意见。这三项都是真实的审核盲区，不能算通过。

```json
{{ENVELOPE}}
```