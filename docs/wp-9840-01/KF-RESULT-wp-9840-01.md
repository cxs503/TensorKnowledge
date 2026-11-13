# KF-RESULT wp-9840-01

**工作包** `wp-9840-01` · **task_type** `01-asset-registration` · **lane** C · **目标报告** `report_id=9840`（本单只触这一份）
**源** `tensor://reports/9840` · field=`markdown` · sha256=`159d4a1419890fe82d46b49037d00273376244d1f24a6503e386c6243d882524` · chars=14740 · bytes_utf8=19763
**分层标签** DG | `dg_convection_diffusion_verification` | l · **仓** TensorKnowledge（交付 status=draft）

## 1. 案例介绍（本工序在产线上的位置）

本条产线的对象是报告 9840 这一份源资产：《IN65-N04 DG 对流–扩散验证面：旋转锥 / 制造解 / 间断传播（HLLC + 正性保持 + kink 阶上界）》。它的上游是 TensorLBM 仓 IN65-N04 节点的 DG 验证面算例（旋转锥 / 制造解 / 间断传播），本工序**只做 asset registration**：确认 report_id 与其 markdown 的字节哈希、把报告内可解析的表格/声明/外部引用逐条定位成机器可复核的资产，**不做知识抽取、不做数值复核、不把任何结论标成 verified**（verification 由平台门计算）。

契约要点（原样遵守）：`objective.register_assets: true`、`classify_report_type: false`、`notes` 明确「claims 允许为空数组」。因此本工序申请的知识对象为零，产出的是证据定位器（locator）+ 解析状态（resolution），供下游抽取工序直接复用。

参数表（全部来自源 markdown，本工序不换算）：

| 项 | 值 | 出处 |
|---|---|---|
| report_id | 9840 | 契约 input.report_id，平台 `id=9840` |
| source_field | `markdown` | 契约 input.source_field |
| markdown sha256 | `159d4a1419890fe82d46b49037d00273376244d1f24a6503e386c6243d882524` | 本次独立重算（见 §6） |
| markdown 字符数 / UTF-8 字节 | 14740 / 19763 | 同上；契约 chars=14740 |
| scenario_key | `dg_convection_diffusion_verification` | 平台记录字段 |
| 平台 figures 数 | 6 | 平台记录 `figures` 字段 |
| 登记资产数 | 32 | 本清单 `counts.assets` |

## 2. 怎么做的（方法 / 流程 / 关键设置 / 工具链）

1. **取源**：`GET http://127.0.0.1:8010/api/v1/tensor/reports/9840`（Bearer 登录 token），把 markdown 与平台元数据冻结到 `runs/wp-9840-01/report_9840.md`；构建与校验都只读这一份字节，避免中途漂移。
2. **哈希先验**：先重算 sha256 与契约 `source_hash` 比对（不等即 `return 2` 硬失败），再做任何登记——哈希不过就不写产物。
3. **锚点表（33 条，5 种模式）**：每条资产声明 anchor 子串 + 解析模式：`document`（全文）/`table`（锚点行起连续 `|` 行，自动吃表头+分隔+全部数据行）/`para`（段落到空行）/`block`（锚点行 + n 行）/`section`（到下一个同级或更高级标题）。锚点必须**在文中唯一命中**，否则构建立即失败（`SystemExit`）。
4. **零手抄的引文**：quote 不是打出来的，而是 `md[start_char:end_char]` 切出来的——字符跨度、行跨度、quote 三者由同一段切片产生，故不可能出现「凭记忆重述」。构建期同时强制：quote 非空、在全文出现次数 == 1、任意两条资产不得共享同一切片（共享则必须登记 `shared_span_with`）。
5. **解析状态三分**：`resolved_in_source`（26 条）/ `referenced_unresolved`（5 条，指向 TensorLBM 仓的代码与产物，本工作树内不存在且报告未给可解析地址）/ `declared_absent`（1 条，§4「结果图」正文为空）。每条资产附 `resolution_check`（检查名 + 结果 + 证据），不留裸断言。
6. **独立校验器**：`scripts/kf_verify_9840.py` 不信任构建期的冻结副本，**重新登录、重新取 API**，用 live markdown 重算 sha256 并逐条按 `[start_char,end_char)` 重切、重算唯一性；三条哈希（契约 / live / 信封）必须同时相等。
7. **结构门**：清单按本包的 pin 死 schema `schemas/asset_manifest.wp-9840-01.schema.json` 校验；结果信封按仓内 `schemas/kf_result.v1.schema.json`（未改动）校验——该 schema `additionalProperties:false`，故信封里不放 `schema_version` 这类额外字段（与早期 448 包信封的差异见 §5）。
8. **否定对照（gate 会不会永远说 PASS？）**：`scripts/kf_9840_negative_control.py` 在内存里造 6 个变体（跨度偏移 1 字符 / 离线改引文 / unique 标志置假 / 资产 id 重复 / 全文 locator 截断 / 凭空编一句引文），断言**真实谓词函数**（从校验器 import，不是重写）逐个拒绝，且原清单 0 失败。
9. **出图**：`scripts/kf_figures_9840.py` 只读清单，画 33 条资产的文档字符轴定位图 + 解析状态/类别分布（数字全部程序化注入）。

## 3. 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/wp-9840-01/asset_manifest.json` | 主产物：33 条资产 + 源元数据 + counts + integrity（sha256 `acae6c5456e3d2fc426fd88150ddd98c7557290f90b34034304d69cc4169affd`, 52397 bytes） |
| `docs/wp-9840-01/asset_manifest.json` | 同字节入库镜像（仓推送门会丢弃 `artifacts/**`、`runs/**`，故 docs/ 存续） |
| `docs/wp-9840-01/verification.json` | 校验器逐项结果：17 pass / 0 fail / 0 not_run，overall=`PASS` |
| `docs/wp-9840-01/negative_control.json` | 6/6 变体被拒（`all_mutants_rejected=True`），原清单 0 失败 |
| `docs/wp-9840-01/fig_asset_locator_map.png` | 图 1：资产在源文档上的定位图 + 解析状态/类别分布 |
| `runs/wp-9840-01/kf_result.wp-9840-01.json` | 结果信封（与下文唯一一个 json 代码块同字节） |
| `runs/wp-9840-01/report_9840.{md,json}` | 冻结的源 markdown 与平台元数据（可复算哈希） |
| `scripts/kf_fetch_9840.py` / `kf_register_9840.py` / `kf_verify_9840.py` / `kf_9840_negative_control.py` / `kf_figures_9840.py` / `kf_report_9840.py` | 取源 / 构建 / 校验 / 否定对照 / 出图 / 发报，一键可复跑 |
| `schemas/asset_manifest.wp-9840-01.schema.json` | 本包 pin 死的清单 schema（`asset_manifest.v1.schema.json` 是 448 包专用，不可复用） |

**关键量误差判定**：本工序无物理量、无基准对标，故「是否 <3%」不适用（登记工序无实验值可比）。替代判据是门通过率：17/17 项校验 pass、0 项 fail、0 项 not_run；契约 acceptance 六条全部 PASS（§6 逐条），否定对照 6/6 被拒。这不是「精度达标」，只是「登记可复核」。

## 4. 证据定位表（每条资产 → 原文逐字引文片段）

下表 quote 列是 `md[start_char:end_char]` 切出的原文前缀（`|` 与换行已转义；⏎ 表示行边界），完整引文见清单 `assets[].locator.quote`；行号是该资产在源 markdown 中的 0 基行区间。

| 资产 | 类别 | 解析状态 | 行区间 | 原文引文（逐字，截断展示） |
|---|---|---|---|---|
| A02 | heading | resolved_in_source | 0–0 | # IN65-N04 — DG 对流–扩散验证面：旋转锥 / 制造解 / 间断传播（从零到机器可证伪） |
| A03 | metadata | resolved_in_source | 2–2 | **节点** IN65-N04 · 战役 *DG from zero to machine-falsifiable* · **仓** TensorLBM · **模块** `src/tenso… |
| A04 | problem_statement | resolved_in_source | 7–7 | ① 变系数旋转对流中 P2 误差地板 ≈2e-3；② 旋转锥收敛阶未达战役门（1.8 / 2.7）；③ 理想气体 Sod 激波位置误差 25%（honest FAIL）；④ 等温 P2 在 t… |
| A05 | criteria_table | resolved_in_source | 14–22 | \| # \| 方程 \| 区域 / 精确解 \| 判据 \| ⏎ \|---\|---\|---\|---\| ⏎ \| F1 \| $u_t+\nabla\cdot(\mathbf{a}u… |
| A06 | method_setup | resolved_in_source | 27–27 | **离散**：节点型 DG，Gauss–Lobatto 节点（面值即自由度，无需 L2 投影），弱形式 $M\dot u=\int F\varphi'-\sum_{\text{faces}}F… |
| A07 | code_declaration | resolved_in_source | 30–31 | * `hllc.py`：Toro HLLC 通量（三相波 $S_L<S_M<S_R$，恢复**接触间断**；波速估计用 PVRS 与双稀疏波估计取小者，Sod 跳跃上 $p^*=0.307$ … |
| A08 | toolchain | resolved_in_source | 33–33 | **流程**：① 参数化基准 → ② `scripts/run_dg_frontier_in65.py --case all` 产出 JSON（集群 n315/n330 loong64 9 分… |
| A09 | table | resolved_in_source | 40–70 | \| 初场 \| 阶 \| N \| L2 \| L2(kink带) \| L2(光滑区) \| 误差占比(kink带) \| 质量漂移 \| ⏎ \|---\|---\|---\|---\|… |
| A10 | table | resolved_in_source | 75–85 | \| 初场 \| 阶 \| L2 order \| kink 带 order \| 光滑区 order \| 理论 p+1 \| ⏎ \|---\|---\|---\|---\|---\|--… |
| A11 | table | resolved_in_source | 89–96 | \| 初场 \| 阶 \| L2 order \| L1 order \| 光滑理论 p+1 \| H^{3/2} 上界 \| ⏎ \|---\|---\|---\|---\|---\|---… |
| A12 | table | resolved_in_source | 100–109 | \| 阶 \| N \| L2(u) \| L2(q) \| 步数 \| ⏎ \|---\|---\|---\|---\|---\| ⏎ \| P1 \| 8 \| 0.046 \| 0.26… |
| A13 | table | resolved_in_source | 112–115 | \| 阶 \| L2(u) order \| L2(q) order \| 理论 \| 偏差 \| ⏎ \|---\|---\|---\|---\|---\| ⏎ \| P1 \| 1.983… |
| A14 | table | resolved_in_source | 119–132 | \| 通量 \| 阶 \| N \| 激波位置误差% \| 密度定位器误差% \| 激波强度误差% \| 接触宽度(格) \| 接触位置误差(格) \| L1(ρ) \| ⏎ \|---\|-… |
| A15 | table | resolved_in_source | 137–150 | \| 通量 \| 阶 \| N \| 激波位置误差% \| 激波强度误差% \| 接触宽度(格) \| L1(ρ) \| ⏎ \|---\|---\|---\|---\|---\|---\|-… |
| A16 | table | resolved_in_source | 154–164 | \| 求解器 \| t \| 激波位置 \| 位置误差% \| 激波厚度(格) \| 平台密度 ρ* \| L2/跳跃 \| ⏎ \|---\|---\|---\|---\|---\|---\… |
| A17 | numeric_anchor | resolved_in_source | 166–166 | 解析参考（等温）：$\rho^*$=0.4966，$u^*$=0.4041，激波速度 $W$=0.8137。等温 Euler 只有三条特征线，**没有接触间断**，故互裁只针对激波位置/强度/… |
| A18 | table | resolved_in_source | 171–196 | \| 限制器 \| 阶 \| N \| 周期 \| TV 比 \| 过冲% \| 欠冲% \| L1 \| ⏎ \|---\|---\|---\|---\|---\|---\|---\|---… |
| A19 | table | resolved_in_source | 201–214 | \| 限制器 \| 阶 \| N \| 幅值比 \| 相位误差(rad) \| L2 \| ⏎ \|---\|---\|---\|---\|---\|---\| ⏎ \| limited \|… |
| A20 | table | resolved_in_source | 218–223 | \| 通量 \| 阶 \| N \| 质量漂移 \| 动量漂移(÷∫ρ) \| 能量漂移 \| θ_min \| ⏎ \|---\|---\|---\|---\|---\|---\|---\|… |
| A21 | numeric_anchor | resolved_in_source | 225–225 | 旋转锥（二维、一周期）质量漂移最大值：2.81e-13。 |
| A22 | figure_section | declared_absent | 228–230 | ## 4. 结果图 ⏎  ⏎  |
| A23 | limitation_set | resolved_in_source | 231–242 | ## 5. 注意点（踩过的坑 / 局限 / 适用范围） ⏎  ⏎ 1. **周期边界的激波管是错的（本轮最大发现）**：IN70-N01 的理想气体 Sod 用长度 1 的周期管，$t=0.2… |
| A24 | table | resolved_in_source | 245–258 | \| 量 \| 实测 \| 基准 \| 阈值 \| 判定 \| ⏎ \|---\|---\|---\|---\|---\| ⏎ \| 旋转锥 P1 L2 阶（战役门 1.8） \| 1.453… |
| A25 | statement | resolved_in_source | 260–260 | **质量守恒**：Euler 周期最差质量漂移 1.13e-13、能量漂移 1.08e-13、旋转锥 2.81e-13（门 1e-10）→ **PASS**，量级为浮点舍入（1e-14…1e-… |
| A26 | unevaluated_claims | resolved_in_source | 263–266 | **“关键量是否 <3%？”逐项回答**： ⏎ * 光滑数据（高斯伴随、MMS 收敛阶、等温/理想气体激波位置）：**是**——阶偏差 0.005（<0.3），激波位置 1.82% 与 0.3… |
| A27 | verdict_summary | resolved_in_source | 269–269 | **判决汇总**：8/14 项判据通过；honest FAIL：rotating_cone_order_P1, rotating_cone_order_P2, rotating_wide_ga… |
| A28 | repro_block | resolved_in_source | 274–278 | PYTHONPATH=src python -m pytest tests/test_dg_frontier_in65.py -q     # 19 项，~25 s ⏎ PYTHONPATH=… |
| A29 | external_module | referenced_unresolved | 2–2 | **节点** IN65-N04 · 战役 *DG from zero to machine-falsifiable* · **仓** TensorLBM · **模块** `src/tenso… |
| A30 | external_test | referenced_unresolved | 233–233 | 1. **周期边界的激波管是错的（本轮最大发现）**：IN70-N01 的理想气体 Sod 用长度 1 的周期管，$t=0.2$ 时 $x=0$ 处的第二个 Riemann 问题（周期回绕）其… |
| A31 | external_script_set | referenced_unresolved | 276–276 | PYTHONPATH=src python scripts/plot_dg_frontier_in65.py                # 图 -> artifacts/IN65_N04/… |
| A32 | external_artifact | referenced_unresolved | 277–277 | PYTHONPATH=src python scripts/verdict_dg_frontier_in65.py             # -> VERDICT.json |
| A33 | compute_provenance | referenced_unresolved | 33–33 | **流程**：① 参数化基准 → ② `scripts/run_dg_frontier_in65.py --case all` 产出 JSON（集群 n315/n330 loong64 9 分… |

另：`§4 结果图` 在 markdown 中无正文（A22 (`figure_section`)），但平台 `figures` 字段有 6 条记录（fig1_convergence.png, fig2_cone_fields.png, fig3_sod.png, fig4_lbm_crosscheck.png, fig5_square_wave.png, fig6_ledgers.png）——图件字节不在本工序登记范围。

## 5. 注意点与局限

1. **不判数值真伪**：报告 §6 自报 6 项 honest FAIL（rotating_cone_order_P1/P2、rotating_wide_gaussian_order_P1/P2、rotating_hump_order_P2、sod_shock_position_2pct_all_runs）。本工序原样登记、**未复核任何一个数字**，也未把任何 PASS 项写成 verified——真伪归平台门与下游抽取/复核工序。
2. **5 条资产解析不到**：A29 (`external_module`), A30 (`external_test`), A31 (`external_script_set`), A32 (`external_artifact`), A33 (`compute_provenance`) 属 TensorLBM 仓（`src/tensorlbm/dg_verification/`、`tests/`、`scripts/`、`artifacts/`），本工作树是 TensorKnowledge，仓内无对应文件，报告也只给相对路径、无 URL/DOI/commit。按要求**不联网猜地址**，一律记 `referenced_unresolved` 并写明候选路径。
3. **§4 结果图 markdown 侧为空**：唯一 `declared_absent` 记在 markdown 事实上（该节仅标题）。图件存在于平台 `figures` 元数据（6 张），本工序不下载图件字节、不登记为已解析资产——若下游需要图件级资产，应另开工序取 `figures` 字段。
4. **共享行跨度**：A29↔A03, A33↔A08 是「同一行同时声明两件事」的必然结果（如节点元数据行既声明仓/模块路径，也声明机器门）。共享被显式记录在 `locator.shared_span_with`，校验器（`shared_span_documented`）检查对端 id 存在——不是靠沉默掩盖重复。
5. **claims 为空数组是契约行为，不是遗漏**：`objective.classify_report_type=false` + `notes` 允许空 claims。空 claims 意味着「本工序没有对报告结论做任何知识化断言」，不意味着「报告结论已被核实」。
6. **信封字段差异**：仓内 `schemas/kf_result.v1.schema.json` 顶层 `additionalProperties:false`，故信封不含 `schema_version` 等额外字段（早期 448 包信封含之，按该仓旧 schema 才合法）。若平台侧 schema 另有要求，以平台门为准，本产物须相应修订。
7. **schema_pass 的解释边界**：清单用本包 pin 的 `schemas/asset_manifest.wp-9840-01.schema.json`（因为仓内 `asset_manifest.v1.schema.json` 把 `package_id` 恒等成了 `wp-448-01`，复用即造假）。这是「本仓可复跑的结构门」，不等于平台权威 schema 通过。
8. **整篇文档不重复登记为资产**：源 markdown 由 `source.hash`（对精确字节算 sha256，平台独立重算）登记；若再把全文作为一条 document 级资产的 quote 塞进结果信封，源报告自带的代码围栏会污染信封，使「唯一一个 json 代码块」对围栏解析器产生歧义。故资产表只登记**片段**（表格/声明/外部引用），全文归属哈希而非 quote。
9. **版本说明（诚实留痕）**：本包在平台上存在三版报告 14738 → 14749 → 本版。前两版的缺陷=结果信封里的引文携带了源报告自身的 bash 代码围栏（A01 全文级资产 + A28 整节引用），使「唯一一个 json 代码块」对围栏解析器产生歧义；本版取消全文级资产、把复现段降为围栏内 5 行正文，`fence_markers=2` 成为可机检不变量。仓内定稿为 `docs/wp-9840-01/KF-RESULT-wp-9840-01.md`。
10. **单报告边界**：本单只读/写 `report_id=9840`，未触碰任何其它 report_id；`single_report_scope` 校验 manifest/envelope/URI 三处 id 一致。

## 6. 误差判定与自检（逐条对照 acceptance）

| acceptance | 结论 | 对应校验项 |
|---|---|---|
| `valid_json` | PASS | `valid_json` |
| `schema_pass` | PASS | `schema_pass_manifest, schema_pass_envelope` |
| `source_locator_resolvable` | PASS | `source_locator_resolvable` |
| `source_hash_matches` | PASS | `source_hash_matches_contract` |
| `no_duplicate_ids` | PASS | `no_duplicate_ids` |
| `all_claims_have_evidence_or_explicit_unresolved_status` | PASS | `all_claims_have_evidence_or_explicit_unresolved_status` |

补充校验（非 acceptance 但可机裁）：`source_hash_recomputed_live`、`source_chars_match_contract`、`source_field_markdown`、`quotes_are_substrings_of_source`、`no_verified_markers`、`counts_consistent`、`shared_span_documented`、`artifact_hash_matches_envelope`、`durable_mirror_identical`、`single_report_scope` —— 全部 pass（共 17 项）。

**是否 <3%？** 不适用（登记工序，无基准对标量，理由见 §3 末段）。**honest 失败项**：无（0 项 fail、0 项 not_run）。**未完成部分**：图件字节未登记（§5-3）；外部代码/产物 5 条只能记 unresolved（§5-2）。

**repro_cmd（一键复跑，工作树根执行）**：`python3 scripts/kf_fetch_9840.py && python3 scripts/kf_register_9840.py && python3 scripts/kf_verify_9840.py && python3 scripts/kf_9840_negative_control.py && python3 scripts/kf_figures_9840.py`

```json
{
  "package_id": "wp-9840-01",
  "task_type": "01-asset-registration",
  "report_id": "9840",
  "provenance": {
    "source_uri": "tensor://reports/9840",
    "source_field": "markdown",
    "source_hash": "sha256:159d4a1419890fe82d46b49037d00273376244d1f24a6503e386c6243d882524",
    "source_chars": 14740,
    "source_bytes_utf8": 19763,
    "source_title": "IN65-N04 DG 对流–扩散验证面：旋转锥 / 制造解 / 间断传播（HLLC + 正性保持 + kink 阶上界）",
    "scenario_key": "dg_convection_diffusion_verification",
    "contract_version": "1.0",
    "lane": "C",
    "work_package": "wp-9840-01",
    "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/9840",
    "local_copy": "runs/wp-9840-01/report_9840.md",
    "generator": "scripts/kf_register_9840.py",
    "verifier": "scripts/kf_verify_9840.py",
    "verification_status": "not_verified",
    "repro_cmd": "python3 scripts/kf_fetch_9840.py && python3 scripts/kf_register_9840.py && python3 scripts/kf_verify_9840.py && python3 scripts/kf_9840_negative_control.py && python3 scripts/kf_figures_9840.py"
  },
  "outputs": {
    "asset_manifest.json": {
      "artifact_path": "artifacts/wp-9840-01/asset_manifest.json",
      "artifact_sha256": "acae6c5456e3d2fc426fd88150ddd98c7557290f90b34034304d69cc4169affd",
      "artifact_bytes": 52397,
      "schema": "asset_manifest.v1",
      "package_id": "wp-9840-01",
      "task_type": "01-asset-registration",
      "report_id": "9840",
      "source": {
        "uri": "tensor://reports/9840",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "159d4a1419890fe82d46b49037d00273376244d1f24a6503e386c6243d882524",
        "chars": 14740,
        "bytes_utf8": 19763,
        "title": "IN65-N04 DG 对流–扩散验证面：旋转锥 / 制造解 / 间断传播（HLLC + 正性保持 + kink 阶上界）",
        "scenario_key": "dg_convection_diffusion_verification",
        "platform_id": 9840,
        "platform_mission_id": 8422,
        "platform_figures": [
          {
            "name": "fig1_convergence.png",
            "caption": "图 1　收敛阶：左=旋转场（锥 C0 / 丘 C1 / 高斯 C∞，P1–P3）；中=一维 kink vs 光滑；右=变系数 MMS 的 u 与 LDG 梯度 q。虚线为参考斜率。"
          },
          {
            "name": "fig2_cone_fields.png",
            "caption": "图 2　LeVeque 锥初场（左）与旋转一周期后的 P1（中）、P2（右）解（N=48）；锥面折线是 kink，L2 阶被 H^{3/2} 正则性卡住。"
          },
          {
            "name": "fig3_sod.png",
            "caption": "图 3　理想气体 Sod（t=0.2，n=400）：(a) ρ/p 的 DG vs 精确解，点线标出激波/接触位置；(b) 接触抹平宽度 vs 网格：HLLC 明显优于 Rusanov；(c) 压力梯度定位的激波位置误差 vs 2% 门。"
          },
          {
            "name": "fig4_lbm_crosscheck.png",
            "caption": "图 4　等温 Sod 三方互裁：(a) t=200 的密度剖面（已验证 D2Q9 LBM / 解析 / DG P1-HLLC）；(b) 激波位置误差与激波厚度随时间。"
          },
          {
            "name": "fig5_square_wave.png",
            "caption": "图 5　方波对流：(a) 四周期后限制/不限幅值剖面；(b) TV(u(T))/TV(u(0)) 账本；(c) 单模态耗散（幅值损失%）与色散（相位误差 rad）。"
          },
          {
            "name": "fig6_ledgers.png",
            "caption": "图 6　(a) 周期 Euler 的质量/动量/能量漂移（对数轴，红线=1e−10 门）；(b) 旋转锥中落在 kink 带内的平方误差占比。"
          }
        ],
        "platform_tags": [
          "DG",
          "TensorLBM",
          "verification",
          "HLLC",
          "Sod",
          "MMS",
          "rotating_cone",
          "limiter",
          "IN65-N04"
        ],
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/9840",
        "local_copy": "runs/wp-9840-01/report_9840.md",
        "fetch_script": "scripts/kf_fetch_9840.py"
      },
      "counts": {
        "assets": 32,
        "by_class": {
          "heading": 1,
          "metadata": 1,
          "problem_statement": 1,
          "criteria_table": 1,
          "method_setup": 1,
          "code_declaration": 1,
          "toolchain": 1,
          "table": 12,
          "numeric_anchor": 2,
          "figure_section": 1,
          "limitation_set": 1,
          "statement": 1,
          "unevaluated_claims": 1,
          "verdict_summary": 1,
          "repro_block": 1,
          "external_module": 1,
          "external_test": 1,
          "external_script_set": 1,
          "external_artifact": 1,
          "compute_provenance": 1
        },
        "by_resolution": {
          "resolved_in_source": 26,
          "declared_absent": 1,
          "referenced_unresolved": 5
        },
        "resolved_in_source": 26,
        "referenced_unresolved": 5,
        "declared_absent": 1
      },
      "assets": [
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "报告标题（H1）",
          "in_report_section": "# IN65-N04 — DG 对流–扩散验证面：旋转锥 / 制造解 / 间断传播（从零到机器可证伪）",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 51,
            "start_line": 0,
            "end_line": 0,
            "quote": "# IN65-N04 — DG 对流–扩散验证面：旋转锥 / 制造解 / 间断传播（从零到机器可证伪）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 51,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "与 API title 字段同源。"
        },
        {
          "asset_id": "A03",
          "asset_class": "metadata",
          "label": "节点/战役/仓/模块/机器门/分层声明",
          "in_report_section": "# IN65-N04 — DG 对流–扩散验证面：旋转锥 / 制造解 / 间断传播（从零到机器可证伪）",
          "locator": {
            "method": "char_span",
            "start_char": 53,
            "end_char": 307,
            "start_line": 2,
            "end_line": 2,
            "quote": "**节点** IN65-N04 · 战役 *DG from zero to machine-falsifiable* · **仓** TensorLBM · **模块** `src/tensorlbm/dg_verification/{hllc.py,frontier.py}` · **机器门** `tests/test_dg_frontier_in65.py`（19 项）· **工件** `artifacts/IN65_N04/*.json` + `VERDICT.json` + `figures/`",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 254,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "定位源仓与模块路径；模块本体见 A27/A28（本工作树内不可解析）。"
        },
        {
          "asset_id": "A04",
          "asset_class": "problem_statement",
          "label": "从上节点继承的四个未解问题（①②③④）",
          "in_report_section": "## 1. 案例介绍（物理背景 / 几何 / 参数表）",
          "locator": {
            "method": "char_span",
            "start_char": 588,
            "end_char": 694,
            "start_line": 7,
            "end_line": 7,
            "quote": "① 变系数旋转对流中 P2 误差地板 ≈2e-3；② 旋转锥收敛阶未达战役门（1.8 / 2.7）；③ 理想气体 Sod 激波位置误差 25%（honest FAIL）；④ 等温 P2 在 t=400 长期退化。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 106,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "本节点要逐条打开的四个开放问题的原文表述。"
        },
        {
          "asset_id": "A05",
          "asset_class": "criteria_table",
          "label": "模型问题与判据表 F1–F7（7 行）",
          "in_report_section": "## 1. 案例介绍（物理背景 / 几何 / 参数表）",
          "locator": {
            "method": "char_span",
            "start_char": 926,
            "end_char": 1711,
            "start_line": 14,
            "end_line": 22,
            "quote": "| # | 方程 | 区域 / 精确解 | 判据 |\n|---|---|---|---|\n| F1 | $u_t+\\nabla\\cdot(\\mathbf{a}u)=0$, $\\mathbf{a}=(0.5-y,\\,x-0.5)$ | $[0,1]^2$，LeVeque 锥 / 余弦丘 / 高斯，一周期 $t=2\\pi$ | L2 收敛阶（P1/P2/P3）+ kink 带误差占比 |\n| F2 | 一维周期对流，帐篷函数（C0）vs 高斯（C∞） | $[0,1]$，$a=1$，$t=0.5$ | 阶数分离：kink 上界 ~1.5，光滑 $p+1$ |\n| F3 | $u_t+\\mathbf{a}\\cdot\\nabla u=\\nu\\Delta u+S$，$\\mathbf{a}$ 同上 | $[0,2]^2$，$u=\\sin\\pi x\\sin\\pi y\\,e^{-t}$，$\\nu=0.05$ | $u$ 与 LDG 梯度 $q$ 的阶 vs 理论 $p+1$ |\n| F4 | 一维理想气体 Euler，$\\gamma=1.4$，Sod IC | $[0,1]$，**出流端**，$t=0.2$ | 激波位置 <2%（压力梯度定位）、强度、接触宽度 |\n| F5 | 一维等温 Euler（$p=c_s^2\\rho$，$c_s^2=1/3$，即 D2Q9 闭合） | 2000 格，$t=100\\ldots400$ | DG ⇄ 已验证 LBM ⇄ 解析 三方互裁 |\n| F6 | 一维方波对流（minmod/TVB）+ 单模态 $\\sin2\\pi x$ | $[0,1]$，$a=1$ | TVD（无新极值）+ 耗散/色散标量 |\n| F7 | 周期 Euler（Sod IC，$t=0.5$） | 200 格 | 质量/动量/能量漂移 <1e-10 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 785,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "七个算例的方程/区域/精确解/判据；数值仅登记不换算。"
        },
        {
          "asset_id": "A06",
          "asset_class": "method_setup",
          "label": "离散设置（节点型 DG / Gauss–Lobatto / SSP-RK3 / CFL / 求积）",
          "in_report_section": "## 2. 怎么做的（方法 / 流程 / 关键设置 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1748,
            "end_char": 1946,
            "start_line": 27,
            "end_line": 27,
            "quote": "**离散**：节点型 DG，Gauss–Lobatto 节点（面值即自由度，无需 L2 投影），弱形式 $M\\dot u=\\int F\\varphi'-\\sum_{\\text{faces}}F^*\\varphi$，体项用 $p+3$ 点 Gauss 求积（对 $a(x)u$ 这类 $p+1$ 次被积函数精确），时间推进 SSP-RK3（Shu–Osher），CFL 0.2–0.3，面通量可选。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 198,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "方法学声明；实现体见 A27（未解析）。"
        },
        {
          "asset_id": "A07",
          "asset_class": "code_declaration",
          "label": "新增工具声明：hllc.py（HLLC + Zhang–Shu）与 frontier.py",
          "in_report_section": "## 2. 怎么做的（方法 / 流程 / 关键设置 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1963,
            "end_char": 2366,
            "start_line": 30,
            "end_line": 31,
            "quote": "* `hllc.py`：Toro HLLC 通量（三相波 $S_L<S_M<S_R$，恢复**接触间断**；波速估计用 PVRS 与双稀疏波估计取小者，Sod 跳跃上 $p^*=0.307$ 对精确 0.3031）；等温闭合 $p=c_s^2\\rho$ 同实现（与 D2Q9 晶格一致）；`zhang_shu_limit`：Zhang–Shu 正性保持缩放限制器（$U\\leftarrow\\bar U+\\theta(U-\\bar U)$，$p(\\theta)$ 对 $\\theta$ 是凹二次型 ⇒ 二分法找最大可行 $\\theta$；单元均值精确不变 ⇒ 严格守恒）。\n* `frontier.py`：`EulerDG1D_HLLC`（**纯空间算子**，限制器只在阶段末施加；通量 hllc/rusanov 可切；边界 periodic/outflow）、`ScalarDG1D`、七个基准与量化指标。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 403,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "两条工具声明的原文；代码本体见 A27（未解析）。"
        },
        {
          "asset_id": "A08",
          "asset_class": "toolchain",
          "label": "流程①–⑤（运行→出图→判决→报告生成器）",
          "in_report_section": "## 2. 怎么做的（方法 / 流程 / 关键设置 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 2368,
            "end_char": 2642,
            "start_line": 33,
            "end_line": 33,
            "quote": "**流程**：① 参数化基准 → ② `scripts/run_dg_frontier_in65.py --case all` 产出 JSON（集群 n315/n330 loong64 9 分片，日志与 JSON 均落工件） → ③ `scripts/plot_dg_frontier_in65.py` 出图（场量重算，不抄数） → ④ `scripts/verdict_dg_frontier_in65.py` 依判据自动裁 PASS/FAIL → ⑤ `scripts/report_dg_frontier_in65.py` 程序化注入本报告。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 274,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "含集群节点 n315/n330 与 9 分片陈述，算力出处见 A31。"
        },
        {
          "asset_id": "A09",
          "asset_class": "table",
          "label": "F1 收敛数据表（锥/丘/宽高斯/窄高斯 × P1–P3，29 行数据）",
          "in_report_section": "### 3.1 旋转锥 / 光滑伴随：阶数与 kink 带误差占比（F1）",
          "locator": {
            "method": "char_span",
            "start_char": 2707,
            "end_char": 4793,
            "start_line": 40,
            "end_line": 70,
            "quote": "| 初场 | 阶 | N | L2 | L2(kink带) | L2(光滑区) | 误差占比(kink带) | 质量漂移 |\n|---|---|---|---|---|---|---|---|\n| 锥 C0 | P1 | 16 | 0.035 | 0.065 | 0.017 | 0.821 | 4.19e-14 |\n| 锥 C0 | P1 | 32 | 0.011 | 0.026 | 0.007 | 0.629 | 8.39e-14 |\n| 锥 C0 | P1 | 64 | 0.005 | 0.016 | 0.003 | 0.675 | 1.69e-13 |\n| 锥 C0 | P2 | 16 | 0.007 | 0.013 | 0.003 | 0.803 | 7.04e-14 |\n| 锥 C0 | P2 | 32 | 0.003 | 0.008 | 0.001 | 0.838 | 1.41e-13 |\n| 锥 C0 | P2 | 64 | 0.001 | 0.004 | 4.21e-04 | 0.874 | 2.81e-13 |\n| 丘 C1 | P1 | 16 | 0.018 | 0.035 | 0.007 | 0.896 | 4.23e-14 |\n| 丘 C1 | P1 | 32 | 0.004 | 0.010 | 0.003 | 0.555 | 8.56e-14 |\n| 丘 C1 | P1 | 64 | 9.89e-04 | 0.002 | 8.48e-04 | 0.308 | 1.71e-13 |\n| 丘 C1 | P2 | 16 | 0.001 | 0.003 | 2.48e-04 | 0.976 | 7.09e-14 |\n| 丘 C1 | P2 | 32 | 2.90e-04 | 7.25e-04 | 1.59e-04 | 0.736 | 1.43e-13 |\n| 丘 C1 | P2 | 64 | 6.60e-05 | 6.54e-05 | 6.60e-05 | 0.058 | 2.84e-13 |\n| 宽高斯 σ=0.1 | P1 | 16 | 0.023 | 0.045 | 0.009 | 0.871 | 4.18e-14 |\n| 宽高斯 σ=0.1 | P1 | 32 | 0.005 | 0.007 | 0.005 | 0.190 | 8.50e-14 |\n| 宽高斯 σ=0.1 | P1 | 64 | 0.002 | 0.001 | 0.002 | 0.013 | 1.70e-13 |\n| 宽高斯 σ=0.1 | P2 | 16 | 0.002 | 0.004 | 0.002 | 0.643 | 7.08e-14 |\n| 宽高斯 σ=0.1 | P2 | 32 | 0.002 | 4.37e-04 | 0.002 | 0.006 | 1.42e-13 |\n| 宽高斯 σ=0.1 | P2 | 64 | 0.002 | 1.56e-05 | 0.002 | 4.26e-06 | 2.83e-13 |\n| 窄高斯 σ=0.05 | P1 | 16 | 0.042 | 0.073 | 0.027 | 0.694 | 4.24e-14 |\n| 窄高斯 σ=0.05 | P1 | 32 | 0.016 | 0.021 | 0.015 | 0.207 | 8.42e-14 |\n| 窄高斯 σ=0.05 | P1 | 64 | 0.003 | 0.002 | 0.004 | 0.015 | 1.70e-13 |\n| 窄高斯 σ=0.05 | P1 | 96 | 0.001 | 4.00e-04 | 0.001 | 0.004 | 2.55e-13 |\n| 窄高斯 σ=0.05 | P2 | 16 | 0.007 | 0.011 | 0.005 | 0.656 | 7.20e-14 |\n| 窄高斯 σ=0.05 | P2 | 32 | 4.54e-04 | 4.04e-04 | 4.61e-04 | 0.093 | 1.42e-13 |\n| 窄高斯 σ=0.05 | P2 | 64 | 3.04e-05 | 2.57e-05 | 3.07e-05 | 0.042 | 2.84e-13 |\n| 窄高斯 σ=0.05 | P2 | 96 | 8.09e-06 | 7.04e-06 | 8.13e-06 | 0.030 | 4.25e-13 |\n| 窄高斯 σ=0.05 | P3 | 16 | 4.90e-04 | 8.97e-04 | 2.64e-04 | 0.778 | 9.94e-14 |\n| 窄高斯 σ=0.05 | P3 | 32 | 1.93e-05 | 2.51e-05 | 1.84e-05 | 0.198 | 1.98e-13 |\n| 窄高斯 σ=0.05 | P3 | 64 | 9.86e-07 | 6.46e-07 | 1.00e-06 | 0.025 | 3.97e-13 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 2086,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "原始 L2/分带误差/质量漂移；本工序只登记，不复核数值。"
        },
        {
          "asset_id": "A10",
          "asset_class": "table",
          "label": "F1 最小二乘收敛阶表（9 行）",
          "in_report_section": "### 3.1 旋转锥 / 光滑伴随：阶数与 kink 带误差占比（F1）",
          "locator": {
            "method": "char_span",
            "start_char": 4812,
            "end_char": 5302,
            "start_line": 75,
            "end_line": 85,
            "quote": "| 初场 | 阶 | L2 order | kink 带 order | 光滑区 order | 理论 p+1 |\n|---|---|---|---|---|---|\n| 锥 C0 | P1 | 1.453 | 1.027 | 1.312 | 2 |\n| 锥 C0 | P2 | 1.281 | 0.759 | 1.515 | 3 |\n| 丘 C1 | P1 | 2.084 | 1.972 | 1.474 | 2 |\n| 丘 C1 | P2 | 2.202 | 2.727 | 0.955 | 3 |\n| 宽高斯 σ=0.1 | P1 | 1.692 | 2.716 | 1.032 | 2 |\n| 宽高斯 σ=0.1 | P2 | 0.162 | 3.971 | -0.137 | 3 |\n| 窄高斯 σ=0.05 | P1 | 1.971 | 2.953 | 1.712 | 2 |\n| 窄高斯 σ=0.05 | P2 | 3.789 | 4.142 | 3.579 | 3 |\n| 窄高斯 σ=0.05 | P3 | 4.479 | 5.220 | 4.019 | 4 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 490,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "阶数与理论 p+1 并列的判读面。"
        },
        {
          "asset_id": "A11",
          "asset_class": "table",
          "label": "F2 一维 kink vs 光滑阶数表（6 行）",
          "in_report_section": "### 3.2 一维 kink vs 光滑（F2）：正则性而非格式决定阶",
          "locator": {
            "method": "char_span",
            "start_char": 5342,
            "end_char": 5682,
            "start_line": 89,
            "end_line": 96,
            "quote": "| 初场 | 阶 | L2 order | L1 order | 光滑理论 p+1 | H^{3/2} 上界 |\n|---|---|---|---|---|---|\n| kink | P1 | 1.145 | 1.506 | 2 | 1.500 |\n| kink | P2 | 1.222 | 1.653 | 3 | 1.500 |\n| kink | P3 | 1.313 | 1.708 | 4 | 1.500 |\n| smooth | P1 | 2.204 | 2.207 | 2 | 1.500 |\n| smooth | P2 | 3.032 | 3.043 | 3 | 1.500 |\n| smooth | P3 | 3.755 | 3.717 | 4 | 1.500 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 340,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "正则性决定阶的对照面（kink L2 1.145–1.313 vs smooth 2.204–3.755）。"
        },
        {
          "asset_id": "A12",
          "asset_class": "table",
          "label": "F3 制造解 L2(u)/L2(q) 表（8 行）",
          "in_report_section": "### 3.3 变系数制造解（F3）：$u$ 与 LDG 梯度 $q$ 的阶",
          "locator": {
            "method": "char_span",
            "start_char": 5724,
            "end_char": 6062,
            "start_line": 100,
            "end_line": 109,
            "quote": "| 阶 | N | L2(u) | L2(q) | 步数 |\n|---|---|---|---|---|\n| P1 | 8 | 0.046 | 0.264 | 32 |\n| P1 | 16 | 0.012 | 0.079 | 87 |\n| P1 | 32 | 0.003 | 0.022 | 266 |\n| P1 | 64 | 7.37e-04 | 0.006 | 901 |\n| P2 | 8 | 0.001 | 0.015 | 88 |\n| P2 | 16 | 1.64e-04 | 0.002 | 271 |\n| P2 | 32 | 2.07e-05 | 3.09e-04 | 920 |\n| P2 | 64 | 2.62e-06 | 4.11e-05 | 3358 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 338,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "含步数，可反推时间步设置。"
        },
        {
          "asset_id": "A13",
          "asset_class": "table",
          "label": "F3 阶与理论偏差表（P1/P2）",
          "in_report_section": "### 3.3 变系数制造解（F3）：$u$ 与 LDG 梯度 $q$ 的阶",
          "locator": {
            "method": "char_span",
            "start_char": 6065,
            "end_char": 6200,
            "start_line": 112,
            "end_line": 115,
            "quote": "| 阶 | L2(u) order | L2(q) order | 理论 | 偏差 |\n|---|---|---|---|---|\n| P1 | 1.983 | 1.823 | 2 | 0.017 |\n| P2 | 2.995 | 2.834 | 3 | 0.005 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 135,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "偏差 0.017/0.005 与 §6 判定表互指。"
        },
        {
          "asset_id": "A14",
          "asset_class": "table",
          "label": "F4 理想气体 Sod 主表（hllc/rusanov × P1/P2 × N=100–400，12 行）",
          "in_report_section": "### 3.4 理想气体 Sod（F4）：HLLC vs Rusanov，出流端",
          "locator": {
            "method": "char_span",
            "start_char": 6244,
            "end_char": 7159,
            "start_line": 119,
            "end_line": 132,
            "quote": "| 通量 | 阶 | N | 激波位置误差% | 密度定位器误差% | 激波强度误差% | 接触宽度(格) | 接触位置误差(格) | L1(ρ) |\n|---|---|---|---|---|---|---|---|---|\n| hllc | P1 | 100 | 0.849 | 1.164 | 0.315 | 7 | 0.295 | 0.008 |\n| hllc | P1 | 200 | 0.437 | 0.613 | 0.013 | 12 | 0.340 | 0.004 |\n| hllc | P1 | 400 | 0.283 | 0.345 | 0.001 | 15 | 0.065 | 0.002 |\n| hllc | P2 | 100 | 3.140 | 133.680 | 0.540 | 17 | 1.483 | 0.021 |\n| hllc | P2 | 200 | 1.823 | 2.202 | 0.083 | 36 | 1.683 | 0.014 |\n| hllc | P2 | 400 | 0.951 | 1.119 | 0.014 | 36 | 1.832 | 0.009 |\n| rusanov | P1 | 100 | 0.895 | 1.154 | 0.699 | 8 | 0.435 | 0.009 |\n| rusanov | P1 | 200 | 0.464 | 0.613 | 0.004 | 13 | 0.624 | 0.005 |\n| rusanov | P1 | 400 | 0.278 | 0.331 | 0.007 | 19 | 0.640 | 0.003 |\n| rusanov | P2 | 100 | 132.811 | 132.646 | 0.117 | 17 | 2.339 | 0.020 |\n| rusanov | P2 | 200 | 1.987 | 2.311 | 0.209 | 36 | 1.495 | 0.013 |\n| rusanov | P2 | 400 | 0.987 | 1.144 | 0.030 | 33 | 3.815 | 0.008 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 915,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "含密度定位器伪影列（rusanov P2 N=100 行 132.811%/132.646%）。"
        },
        {
          "asset_id": "A15",
          "asset_class": "table",
          "label": "F4 TVB 放宽（M=50）对照表（12 行）",
          "in_report_section": "### 3.4 理想气体 Sod（F4）：HLLC vs Rusanov，出流端",
          "locator": {
            "method": "char_span",
            "start_char": 7194,
            "end_char": 7887,
            "start_line": 137,
            "end_line": 150,
            "quote": "| 通量 | 阶 | N | 激波位置误差% | 激波强度误差% | 接触宽度(格) | L1(ρ) |\n|---|---|---|---|---|---|---|\n| hllc | P1 | 100 | 0.890 | 0.163 | 15 | 0.008 |\n| hllc | P1 | 200 | 0.448 | 0.019 | 11 | 0.004 |\n| hllc | P1 | 400 | 0.284 | 5.21e-04 | 16 | 0.002 |\n| hllc | P2 | 100 | 3.134 | 0.491 | 17 | 0.022 |\n| hllc | P2 | 200 | 1.825 | 0.187 | 36 | 0.014 |\n| hllc | P2 | 400 | 0.950 | 0.025 | 36 | 0.009 |\n| rusanov | P1 | 100 | 0.885 | 0.366 | 14 | 0.010 |\n| rusanov | P1 | 200 | 0.465 | 0.008 | 14 | 0.005 |\n| rusanov | P1 | 400 | 0.278 | 0.008 | 19 | 0.003 |\n| rusanov | P2 | 100 | 127.697 | 0.427 | 17 | 0.021 |\n| rusanov | P2 | 200 | 1.945 | 0.255 | 36 | 0.013 |\n| rusanov | P2 | 400 | 0.966 | 0.022 | 35 | 0.008 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 693,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "限制器阈值放宽前后对照；$M$ 量纲为 dx^2（见 A22-3）。"
        },
        {
          "asset_id": "A16",
          "asset_class": "table",
          "label": "F5 等温 Sod 三方互裁表（LBM/DG P1/DG P2 × t=100/200/400）",
          "in_report_section": "### 3.5 等温 Sod：DG ⇄ 已验证 LBM ⇄ 解析（F5）",
          "locator": {
            "method": "char_span",
            "start_char": 7927,
            "end_char": 8560,
            "start_line": 154,
            "end_line": 164,
            "quote": "| 求解器 | t | 激波位置 | 位置误差% | 激波厚度(格) | 平台密度 ρ* | L2/跳跃 |\n|---|---|---|---|---|---|---|\n| LBM nx=2000 | 100 | 1080.342 | 1.267 | 2.060 | 0.496 | 0.006 |\n| LBM nx=2000 | 200 | 1161.591 | 0.710 | 1.963 | 0.496 | 0.007 |\n| LBM nx=2000 | 400 | 1324.343 | 0.354 | 2.051 | 0.497 | 0.006 |\n| DG P1 | 100 | 1081.110 | 0.324 | 2.857 | 0.497 | 0.006 |\n| DG P1 | 200 | 1162.421 | 0.200 | 2.526 | 0.497 | 0.005 |\n| DG P1 | 400 | 1325.225 | 0.083 | 2.703 | 0.497 | 0.007 |\n| DG P2 | 100 | 1081.716 | 0.421 | 8.787 | 0.496 | 0.012 |\n| DG P2 | 200 | 1163.080 | 0.204 | 8.981 | 0.496 | 0.012 |\n| DG P2 | 400 | 1325.685 | 0.059 | 8.925 | 0.496 | 0.013 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 633,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "DG ⇄ LBM ⇄ 解析的三方互裁数字表。"
        },
        {
          "asset_id": "A17",
          "asset_class": "numeric_anchor",
          "label": "等温解析参考锚点（ρ*=0.4966, u*=0.4041, W=0.8137）",
          "in_report_section": "### 3.5 等温 Sod：DG ⇄ 已验证 LBM ⇄ 解析（F5）",
          "locator": {
            "method": "char_span",
            "start_char": 8562,
            "end_char": 8665,
            "start_line": 166,
            "end_line": 166,
            "quote": "解析参考（等温）：$\\rho^*$=0.4966，$u^*$=0.4041，激波速度 $W$=0.8137。等温 Euler 只有三条特征线，**没有接触间断**，故互裁只针对激波位置/强度/厚度与稀疏波。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 103,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "解析基准值；报告未给外部文献地址（自算解析解）。"
        },
        {
          "asset_id": "A18",
          "asset_class": "table",
          "label": "F6 方波 TV/过冲表（limited/unlimited × P1/P2 × N=64–256 × 周期 1/4，24 行）",
          "in_report_section": "### 3.6 方波：TVD 与耗散/色散量化（F6）",
          "locator": {
            "method": "char_span",
            "start_char": 8697,
            "end_char": 10111,
            "start_line": 171,
            "end_line": 196,
            "quote": "| 限制器 | 阶 | N | 周期 | TV 比 | 过冲% | 欠冲% | L1 |\n|---|---|---|---|---|---|---|---|\n| limited | P1 | 64 | 1 | 1.000 | 0 | 0 | 0.077 |\n| limited | P1 | 64 | 4 | 0.980 | 0 | 0 | 0.124 |\n| limited | P1 | 128 | 1 | 1.000 | 0 | 0 | 0.049 |\n| limited | P1 | 128 | 4 | 1.000 | 0 | 0 | 0.079 |\n| limited | P1 | 256 | 1 | 1.000 | 0 | 0 | 0.031 |\n| limited | P1 | 256 | 4 | 1.000 | 0 | 0 | 0.050 |\n| limited | P2 | 64 | 1 | 0.894 | 0 | 0 | 0.206 |\n| limited | P2 | 64 | 4 | 0.340 | 0 | 0 | 0.392 |\n| limited | P2 | 128 | 1 | 0.988 | 0 | 0 | 0.146 |\n| limited | P2 | 128 | 4 | 0.657 | 0 | 0 | 0.290 |\n| limited | P2 | 256 | 1 | 1.000 | 0 | 0 | 0.103 |\n| limited | P2 | 256 | 4 | 0.894 | 0 | 0 | 0.206 |\n| unlimited | P1 | 64 | 1 | 1.199 | 5.469 | 5.469 | 0.038 |\n| unlimited | P1 | 64 | 4 | 1.223 | 5.696 | 5.696 | 0.053 |\n| unlimited | P1 | 128 | 1 | 1.220 | 5.880 | 5.880 | 0.022 |\n| unlimited | P1 | 128 | 4 | 1.225 | 5.605 | 5.605 | 0.031 |\n| unlimited | P1 | 256 | 1 | 1.224 | 5.696 | 5.696 | 0.013 |\n| unlimited | P1 | 256 | 4 | 1.230 | 5.643 | 5.643 | 0.019 |\n| unlimited | P2 | 64 | 1 | 1.213 | 5.677 | 5.677 | 0.018 |\n| unlimited | P2 | 64 | 4 | 1.269 | 5.195 | 5.195 | 0.022 |\n| unlimited | P2 | 128 | 1 | 1.247 | 5.966 | 5.966 | 0.010 |\n| unlimited | P2 | 128 | 4 | 1.283 | 5.201 | 5.201 | 0.013 |\n| unlimited | P2 | 256 | 1 | 1.269 | 5.195 | 5.195 | 0.006 |\n| unlimited | P2 | 256 | 4 | 1.328 | 6.631 | 6.631 | 0.007 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 1414,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "TVD 账本原始行；过冲门 =0。"
        },
        {
          "asset_id": "A19",
          "asset_class": "table",
          "label": "F6 单模态耗散/色散表（幅值比 + 相位误差 + L2，12 行）",
          "in_report_section": "### 3.6 方波：TVD 与耗散/色散量化（F6）",
          "locator": {
            "method": "char_span",
            "start_char": 10155,
            "end_char": 10842,
            "start_line": 201,
            "end_line": 214,
            "quote": "| 限制器 | 阶 | N | 幅值比 | 相位误差(rad) | L2 |\n|---|---|---|---|---|---|\n| limited | P1 | 64 | 0.990 | -0.004 | 0.020 |\n| limited | P1 | 128 | 0.998 | -9.24e-04 | 0.007 |\n| limited | P1 | 256 | 0.999 | -2.36e-04 | 0.002 |\n| limited | P2 | 64 | 0.731 | 0.021 | 0.190 |\n| limited | P2 | 128 | 0.854 | 0.008 | 0.103 |\n| limited | P2 | 256 | 0.924 | 0.004 | 0.054 |\n| unlimited | P1 | 64 | 0.999 | -1.53e-05 | 9.09e-04 |\n| unlimited | P1 | 128 | 1.000 | -1.78e-06 | 2.20e-04 |\n| unlimited | P1 | 256 | 1.000 | -2.14e-07 | 5.42e-05 |\n| unlimited | P2 | 64 | 0.999 | -3.95e-06 | 5.68e-04 |\n| unlimited | P2 | 128 | 1.000 | -4.93e-07 | 1.42e-04 |\n| unlimited | P2 | 256 | 1.000 | -6.16e-08 | 3.55e-05 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 687,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "耗散=幅值比、色散=相位误差的标量量化面。"
        },
        {
          "asset_id": "A20",
          "asset_class": "table",
          "label": "F7 守恒性表（质量/动量/能量漂移 + θ_min，4 行）",
          "in_report_section": "### 3.7 守恒性（F7）",
          "locator": {
            "method": "char_span",
            "start_char": 10861,
            "end_char": 11189,
            "start_line": 218,
            "end_line": 223,
            "quote": "| 通量 | 阶 | N | 质量漂移 | 动量漂移(÷∫ρ) | 能量漂移 | θ_min |\n|---|---|---|---|---|---|---|\n| hllc | P1 | 200 | 1.13e-13 | 1.13e-16 | 1.07e-13 | 1.000 |\n| hllc | P2 | 200 | 3.49e-14 | 3.33e-14 | 1.32e-14 | 1.000 |\n| rusanov | P1 | 200 | 1.13e-13 | 5.33e-17 | 1.08e-13 | 0.928 |\n| rusanov | P2 | 200 | 3.63e-14 | 3.34e-14 | 1.37e-14 | 1.000 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 328,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "守恒账本；θ_min=0.928（rusanov P1）为限制器激活证据。"
        },
        {
          "asset_id": "A21",
          "asset_class": "numeric_anchor",
          "label": "旋转锥一周期质量漂移最大值 2.81e-13",
          "in_report_section": "### 3.7 守恒性（F7）",
          "locator": {
            "method": "char_span",
            "start_char": 11191,
            "end_char": 11219,
            "start_line": 225,
            "end_line": 225,
            "quote": "旋转锥（二维、一周期）质量漂移最大值：2.81e-13。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 28,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "与 A09 锥 C0 P2 N=64 行同值，可交叉核对。"
        },
        {
          "asset_id": "A22",
          "asset_class": "figure_section",
          "label": "§4 结果图（markdown 侧正文为空）",
          "in_report_section": "## 4. 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 11222,
            "end_char": 11233,
            "start_line": 228,
            "end_line": 230,
            "quote": "## 4. 结果图\n\n",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "markdown_section_body_has_content",
            "result": "absent",
            "section_lines": 3,
            "body_chars": 0,
            "platform_figures_count": 6,
            "platform_figure_names": [
              "fig1_convergence.png",
              "fig2_cone_fields.png",
              "fig3_sod.png",
              "fig4_lbm_crosscheck.png",
              "fig5_square_wave.png",
              "fig6_ledgers.png"
            ],
            "detail": "§4 标题在 markdown 中无正文；图件仅在平台 figures 元数据字段中（本工序不下载图件字节）"
          },
          "note": "markdown 该节无图件/无占位；图件实际存在于平台记录 figures 字段（6 张，见 source.platform_figures），故图件本体在本工作树内不可解析，只登记该节缺内容这一事实。"
        },
        {
          "asset_id": "A23",
          "asset_class": "limitation_set",
          "label": "注意点 8 条（含周期激波管污染、定位器陷阱、kink 基准构造）",
          "in_report_section": "## 5. 注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 11234,
            "end_char": 12713,
            "start_line": 231,
            "end_line": 242,
            "quote": "## 5. 注意点（踩过的坑 / 局限 / 适用范围）\n\n1. **周期边界的激波管是错的（本轮最大发现）**：IN70-N01 的理想气体 Sod 用长度 1 的周期管，$t=0.2$ 时 $x=0$ 处的第二个 Riemann 问题（周期回绕）其右行波已推进 0.35，与 $x=0.5$ 的波系重叠，平台区被彻底破坏（实测 $x=0.78$ 处 $p\\approx0.78$，精确 0.303）。`tests/test_dg_frontier_in65.py::test_periodic_tube_is_contaminated_reproduction` 把这个坑钉成回归测试；正式基准改用**出流端**（ghost=内部迹，通量退化为物理通量）。\n2. **定位器陷阱**：Sod 的接触面是**最大的密度跳跃**，用 $\\max|\\partial_x\\rho|$ 定位激波会把接触面当激波（上一节点 25% 的“FAIL”正是此伪影叠加上述周期污染）。压力在接触面上连续，故激波必须用 $\\max|\\partial_x p|$ 定位。\n3. **一阶限制器会把接触抹到 10+ 格**：TVB 阈值 $M=0$ 等价于全场 minmod，激波管剖面变成准一阶（接触宽度 12–40 格）。$M=50$ 只限制真间断，接触宽度与 L1 明显改善（见 3.4 对照表）；但 $M$ 的量纲是 $dx^2$，网格加密后必须重标定。\n4. **限制器不能放在 RHS 里**：SSP-RK3 的每个阶段都重新限制会破坏时间积分阶数与守恒结构；本轮把 RHS 做成纯算子，限制只作用于阶段末状态。\n5. **周期性出流不可复用同一面通量**：周期数组上“绕回面”同时扮演左右两个边界，必须分别覆写两侧边界通量（否则边界处立刻产生伪压力波——本轮第一次实现即踩此坑，表现为 7224 步小步长 + 负压）。\n6. **旋转测试的速度场在环面上不光滑（本轮第二个发现）**：$\\mathbf a=(0.5-y,\\,x-0.5)$ 是绕箱心的刚体旋转，跨 $y=0/1$ 时 $a_x$ 从 0.5 跳到 −0.5（$a_y$ 跨 $x=0/1$ 同理）。因此“$t=2\\pi$ 的精确解 = 初场”只在**数据始终留在半径 0.5 的内切圆内**时成立。IN70 的高斯伴随用 $\\sigma=0.1$、中心 (0.5,0.75)，支撑到 $r=0.55>0.5$，其 $L2$ 误差因此出现与阶数/网格无关的平台（实测 P2 阶 0.16、P1 阶 1.69，P2 在 N=16/32/64 上 L2 恒为 1.8e-3…2.3e-3）——这正是上一节点记为“P2 地板”的开放问题。本轮改用 $\\sigma=0.05$（支撑 $r\\le0.40$）后同一算子给出 P1 阶 1.97、P2 阶 3.79，说明地板是**基准构造**问题，不是离散缺陷。\n7. **适用范围**：结论限于周期/出流边界的一维 Euler 与二维标量对流–扩散；不含壁面、三维、以及耦合 DG-LBM 带（`dg_lbm.py`）。旋转锥的 kink 上界是*L2 范数*结论，L1/L∞ 更慢；等温 LBM 互裁的分辨率 2000 格、$0\\le t\\le400$（≈100 次激波穿越）。\n8. **等温体系没有接触间断**：$p=c_s^2\\rho$ 闭合下特征线只有 3 条，“密度跳跃 + 同速”是声学 Riemann 问题而非接触，写成接触会得到错误的精确解。\n\n",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 1479,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "八条踩坑/局限原文；第 7 条给出适用范围边界。"
        },
        {
          "asset_id": "A24",
          "asset_class": "table",
          "label": "§6 误差判定表（关键量 vs 基准 vs 阈值，12 行）",
          "in_report_section": "## 6. 误差判定（关键量 vs 基准，逐项回答“是否 <3%”）",
          "locator": {
            "method": "char_span",
            "start_char": 12750,
            "end_char": 13528,
            "start_line": 245,
            "end_line": 258,
            "quote": "| 量 | 实测 | 基准 | 阈值 | 判定 |\n|---|---|---|---|---|\n| 旋转锥 P1 L2 阶（战役门 1.8） | 1.453 | 1.800 | 1.800 | FAIL |\n| 旋转锥 P2 L2 阶（战役门 2.7） | 1.281 | 2.700 | 2.700 | FAIL |\n| 光滑高斯伴随 P1 L2 阶（门 1.8） | 1.971 | 1.800 | 1.800 | PASS |\n| 光滑高斯伴随 P2 L2 阶（门 2.7） | 3.789 | 2.700 | 2.700 | PASS |\n| MMS P1 阶偏差（门 <0.3） | 0.017 | p+1 | 0.300 | PASS |\n| MMS P2 阶偏差（门 <0.3） | 0.005 | p+1 | 0.300 | PASS |\n| 理想气体 Sod 最差激波位置误差（生产配置：P1 全网格 + P2 n≥200，门 2%） | 1.823 | exact Riemann | 2.000 | PASS |\n| 理想气体 Sod 严格读法（任一算例 <2%，门 2%） | 3.140 | exact Riemann | 2.000 | FAIL |\n| 等温 Sod DG-P1 最差激波位置误差（门 2%） | 0.324 | exact isothermal | 2.000 | PASS |\n| 等温 Sod LBM 最差激波位置误差（门 2%） | 1.267 | exact isothermal | 2.000 | PASS |\n| 方波限制器过冲（门 =0） | 0 | 0 | 1.00e-12 | PASS |\n| 方波 TV 比（门 ≤1） | 1.000 | 1.000 | 1.000 | PASS |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 778,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "含 6 项 honest FAIL 与 6 项 PASS 的自报判定。"
        },
        {
          "asset_id": "A25",
          "asset_class": "statement",
          "label": "质量守恒结论文本（Euler 周期 1.13e-13 / 能量 1.08e-13 / 旋转锥 2.81e-13 vs 门 1e-10）",
          "in_report_section": "## 6. 误差判定（关键量 vs 基准，逐项回答“是否 <3%”）",
          "locator": {
            "method": "char_span",
            "start_char": 13530,
            "end_char": 13643,
            "start_line": 260,
            "end_line": 260,
            "quote": "**质量守恒**：Euler 周期最差质量漂移 1.13e-13、能量漂移 1.08e-13、旋转锥 2.81e-13（门 1e-10）→ **PASS**，量级为浮点舍入（1e-14…1e-16），比门严 4 个数量级以上。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 113,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "正文复述 A20/A21 的数字，量级判读为浮点舍入。"
        },
        {
          "asset_id": "A26",
          "asset_class": "unevaluated_claims",
          "label": "「关键量是否 <3%」逐项回答（3 条）",
          "in_report_section": "## 6. 误差判定（关键量 vs 基准，逐项回答“是否 <3%”）",
          "locator": {
            "method": "char_span",
            "start_char": 13646,
            "end_char": 14040,
            "start_line": 263,
            "end_line": 266,
            "quote": "**“关键量是否 <3%？”逐项回答**：\n* 光滑数据（高斯伴随、MMS 收敛阶、等温/理想气体激波位置）：**是**——阶偏差 0.005（<0.3），激波位置 1.82% 与 0.32%（均 <2%），激波强度误差 0.16%。\n* 带 kink 的旋转锥 L2 **阶数**：**否，且不可能**——C0 初场属 $H^{3/2-\\epsilon}$，任何阶的 DG 在 L2 下都被 $O(h^{1.5})$ 卡住；实测 P1 1.45、P2 1.28，与理论上界一致（偏差<0.35），故战役门的 1.8/2.7 对**这个**基准不成立，本报告如实标 FAIL，并在光滑伴随上给出该门真正想验证的阶数（P1 1.97、P2 3.79）。\n* 余弦丘（C1，$H^{5/2-\\epsilon}$）P2 阶 2.20：介于 2.5 上界附近，同样受正则性限制，如实记 FAIL。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 394,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "含 kink 上界“否，且不可能”的否证性论述；属报告自述，本工序不判真伪。"
        },
        {
          "asset_id": "A27",
          "asset_class": "verdict_summary",
          "label": "判决汇总（8/14 通过 + 6 项 honest FAIL 列表）",
          "in_report_section": "## 6. 误差判定（关键量 vs 基准，逐项回答“是否 <3%”）",
          "locator": {
            "method": "char_span",
            "start_char": 14043,
            "end_char": 14273,
            "start_line": 269,
            "end_line": 269,
            "quote": "**判决汇总**：8/14 项判据通过；honest FAIL：rotating_cone_order_P1, rotating_cone_order_P2, rotating_wide_gaussian_order_P1, rotating_wide_gaussian_order_P2, rotating_hump_order_P2, sod_shock_position_2pct_all_runs。FAIL 项不被粉饰，且均已给出机理解释与可复现证据。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 230,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "FAIL 项名称清单；本工序只登记，不把任何项标成 verified。"
        },
        {
          "asset_id": "A28",
          "asset_class": "repro_block",
          "label": "复现命令（5 条，代码围栏内正文 + 19 项测试）",
          "in_report_section": "## 复现",
          "locator": {
            "method": "char_span",
            "start_char": 14290,
            "end_char": 14735,
            "start_line": 274,
            "end_line": 278,
            "quote": "PYTHONPATH=src python -m pytest tests/test_dg_frontier_in65.py -q     # 19 项，~25 s\nPYTHONPATH=src python scripts/run_dg_frontier_in65.py --case all      # 全套基准 -> artifacts/\nPYTHONPATH=src python scripts/plot_dg_frontier_in65.py                # 图 -> artifacts/IN65_N04/figures\nPYTHONPATH=src python scripts/verdict_dg_frontier_in65.py             # -> VERDICT.json\nPYTHONPATH=src python scripts/report_dg_frontier_in65.py --out /tmp/report.json",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_re_slice_and_uniqueness",
            "result": "resolved",
            "unique": true,
            "quote_chars": 445,
            "detail": "在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一"
          },
          "note": "定位到 bash 代码围栏内的 5 条命令（不含围栏符，避免引文里携带三反引号）；执行体在 TensorLBM 仓，本工作树不可运行。"
        },
        {
          "asset_id": "A29",
          "asset_class": "external_module",
          "label": "源模块 src/tensorlbm/dg_verification/{hllc.py,frontier.py}",
          "in_report_section": "# IN65-N04 — DG 对流–扩散验证面：旋转锥 / 制造解 / 间断传播（从零到机器可证伪）",
          "locator": {
            "method": "char_span",
            "start_char": 53,
            "end_char": 307,
            "start_line": 2,
            "end_line": 2,
            "quote": "**节点** IN65-N04 · 战役 *DG from zero to machine-falsifiable* · **仓** TensorLBM · **模块** `src/tensorlbm/dg_verification/{hllc.py,frontier.py}` · **机器门** `tests/test_dg_frontier_in65.py`（19 项）· **工件** `artifacts/IN65_N04/*.json` + `VERDICT.json` + `figures/`",
            "unique": true,
            "shared_span_with": "A03"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "referenced_path_exists_in_worktree",
            "result": "unresolved",
            "referenced_candidates": [],
            "found_in_worktree": [],
            "detail": "报告指向 TensorLBM 仓的代码/产物路径；本工作树为 TensorKnowledge，解析不到（不联网猜地址）"
          },
          "note": "属 TensorLBM 仓；本工作树（TensorKnowledge）内不存在，无 URL/commit 可解析。"
        },
        {
          "asset_id": "A30",
          "asset_class": "external_test",
          "label": "回归测试 test_periodic_tube_is_contaminated_reproduction（周期管污染钉死）",
          "in_report_section": "## 5. 注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 11263,
            "end_char": 11563,
            "start_line": 233,
            "end_line": 233,
            "quote": "1. **周期边界的激波管是错的（本轮最大发现）**：IN70-N01 的理想气体 Sod 用长度 1 的周期管，$t=0.2$ 时 $x=0$ 处的第二个 Riemann 问题（周期回绕）其右行波已推进 0.35，与 $x=0.5$ 的波系重叠，平台区被彻底破坏（实测 $x=0.78$ 处 $p\\approx0.78$，精确 0.303）。`tests/test_dg_frontier_in65.py::test_periodic_tube_is_contaminated_reproduction` 把这个坑钉成回归测试；正式基准改用**出流端**（ghost=内部迹，通量退化为物理通量）。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "referenced_path_exists_in_worktree",
            "result": "unresolved",
            "referenced_candidates": [],
            "found_in_worktree": [],
            "detail": "报告指向 TensorLBM 仓的代码/产物路径；本工作树为 TensorKnowledge，解析不到（不联网猜地址）"
          },
          "note": "属 TensorLBM 仓 tests/；本工作树不存在。整条注意点原文（A23）亦在此行内。"
        },
        {
          "asset_id": "A31",
          "asset_class": "external_script_set",
          "label": "出图脚本 scripts/plot_dg_frontier_in65.py（→ artifacts/IN65_N04/figures）",
          "in_report_section": "## 复现",
          "locator": {
            "method": "char_span",
            "start_char": 14464,
            "end_char": 14567,
            "start_line": 276,
            "end_line": 276,
            "quote": "PYTHONPATH=src python scripts/plot_dg_frontier_in65.py                # 图 -> artifacts/IN65_N04/figures",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "referenced_path_exists_in_worktree",
            "result": "unresolved",
            "referenced_candidates": [
              "scripts/plot_dg_frontier_in65.py"
            ],
            "found_in_worktree": [],
            "detail": "报告指向 TensorLBM 仓的代码/产物路径；本工作树为 TensorKnowledge，解析不到（不联网猜地址）"
          },
          "note": "TensorLBM 仓 scripts/；本工作树内不存在。"
        },
        {
          "asset_id": "A32",
          "asset_class": "external_artifact",
          "label": "判决产物 VERDICT.json（scripts/verdict_dg_frontier_in65.py 产出）",
          "in_report_section": "## 复现",
          "locator": {
            "method": "char_span",
            "start_char": 14568,
            "end_char": 14655,
            "start_line": 277,
            "end_line": 277,
            "quote": "PYTHONPATH=src python scripts/verdict_dg_frontier_in65.py             # -> VERDICT.json",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "referenced_path_exists_in_worktree",
            "result": "unresolved",
            "referenced_candidates": [
              "scripts/verdict_dg_frontier_in65.py"
            ],
            "found_in_worktree": [],
            "detail": "报告指向 TensorLBM 仓的代码/产物路径；本工作树为 TensorKnowledge，解析不到（不联网猜地址）"
          },
          "note": "TensorLBM 仓 scripts/ 与 VERDICT.json；本工作树内不存在。"
        },
        {
          "asset_id": "A33",
          "asset_class": "compute_provenance",
          "label": "算力出处：集群 n315/n330 loong64 9 分片",
          "in_report_section": "## 2. 怎么做的（方法 / 流程 / 关键设置 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 2368,
            "end_char": 2642,
            "start_line": 33,
            "end_line": 33,
            "quote": "**流程**：① 参数化基准 → ② `scripts/run_dg_frontier_in65.py --case all` 产出 JSON（集群 n315/n330 loong64 9 分片，日志与 JSON 均落工件） → ③ `scripts/plot_dg_frontier_in65.py` 出图（场量重算，不抄数） → ④ `scripts/verdict_dg_frontier_in65.py` 依判据自动裁 PASS/FAIL → ⑤ `scripts/report_dg_frontier_in65.py` 程序化注入本报告。",
            "unique": true,
            "shared_span_with": "A08"
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "referenced_path_exists_in_worktree",
            "result": "unresolved",
            "referenced_candidates": [],
            "found_in_worktree": [],
            "detail": "报告指向 TensorLBM 仓的代码/产物路径；本工作树为 TensorKnowledge，解析不到（不联网猜地址）"
          },
          "note": "仅给节点名与分片数，无作业号/日志地址，平台侧无法解析。"
        }
      ],
      "claims": [],
      "claims_note": "工作包契约 objective.classify_report_type=false、notes 允许 claims 空数组：本工序只登记资产定位，不做 claim 抽取，也不把任何结论标成 verified。",
      "integrity": {
        "quote_uniqueness": "每条 char_span 引文在冻结 markdown 中出现的次数必须为 1（构建期强制，verify 期重算）",
        "quotes_sliced_not_retyped": true,
        "document_registration": "整篇 markdown 由 source.hash（sha256 over exact bytes）登记，不重复登记为 document 级资产：全文引文会把源报告自己的代码围栏带进结果信封，使报告里唯一的 json 代码块对围栏解析器产生歧义。",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true
      }
    }
  },
  "claims": []
}
```
