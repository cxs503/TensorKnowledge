# KF-RESULT wp-11924-01

> 工序：`01-asset-registration`（只登记资产与定位，不抽取 claim、不分类、不标 verified）
> report_id：`11924` · package_id：`wp-11924-01` · lane：`C` · 交付仓：TensorKnowledge

## ① 案例介绍：本工序做了什么

本单是报告→知识产线上的一道工序：把平台报告 **11924《BPM 微观参数三目标联合标定的可行性判定与可辨识性审计（P270W2C-N08）》**（scenario_key =
`p270w2c-n08-bpm-calibration-feasibility`，上游平台 mission 9756）登记成一份**机器可校验的资产清单**，
供下游工序（claim 抽取、证据审计）直接消费。资产＝报告里可定位的结论表、参数表、图件/数据/代码引用等；
"登记"＝给出**唯一的字符级定位**与**可解析性判定**，不是复述内容。

上游报告在讲什么（逐字引文，均可在原文定位）：

- 核心问题：粘结颗粒模型（BPM）把冰的宏观强度建立在“键强度分布 + 键网络拓扑”上。m7272 建了统计标定管线（吃外部传入的应力历史），m9188 把试件驱动接到 3-D 引擎并逐项审计了质量缩放门…
- 可辨识性判定：- cond(J) = **9.063**；奇异值 5.848、2.151、0.645；rank(J) = 3/6，非零奇异值给出的结构零空间维数 3
- 三目标可行性判定：参考 θ 的判定：**分支 (c)** —— infeasible at this theta: fewer than two targets are met -- the calibrati…

上游自身如实记了多处 honest FAIL（AC6 负控违反比例不足、AC7 准静态门不达标、AC5 跨配置稳健性 FAIL、
UCS 随加载增量加密未收敛）。**本工序原样登记这些结论的定位，不重新裁定、不粉饰**（见 ⑤）。

规模与身份：markdown `13138` 字符 / `22299` UTF-8 字节，`sha256 = 21d915c88bbf78f6f90384f52ce2001f1d7709306c373b159625154ab221bd73`，
与工作包契约 `input.source_hash` 逐字节相同（见 ⑥ 的 `source_hash_matches`）。

本工序**不做**的事（契约边界）：不做 claim 抽取（`claims: []` 为合法完整结果）、不做报告类型分类
（`objective.classify_report_type: false`）、不标 `verified`（verification 由平台门计算）、不读写其它 report_id。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取证（不凭记忆）**：`GET $TENSOR_API_BASE/tensor/reports/11924` 取 `markdown` 字段 → `runs/wp-11924-01/report_11924.md`
   + 原始响应 `report_11924.json`（title/scenario_key/figures/tags）。本地重算 sha256，**与契约不符即中止**。
2. **切片定位（零手抄）**：`scripts/kf_wp11924_01_register.py` 维护一张 42 行的锚点表
   （asset_id / 类 / 唯一锚点串 / 相对行跨）。运行时：锚点在全文出现次数**必须 == 1**（否则 `SystemExit`），
   由锚点求行号 → 行偏移 → `[start_char, end_char)` → **直接从原文切片**得到 `quote`。因此清单里没有
   任何一个数字是重打出来的；同一脚本重跑，`asset_manifest.json` 的 sha256 逐字节不变。
3. **可解析性判定（不猜测）**：每个资产跑一次机器检查 `resolution_check`，且**结果与声明强绑定**
   （`resolved_in_source`↔`resolved`、`referenced_unresolved`↔`unresolved`）：
   - 页内资产 → `char_span_in_source_markdown`；
   - 外部代码/数据路径 → 在本工作树（TensorKnowledge）实测路径是否存在 + 原文正则检索 URL/DOI（命中 0 → 不编造地址）；
   - 图件二进制 → 平台 `figures` 字段有 6 条 name/caption 声明但无 `png_base64`，且相对路径
     `figures/p270w2c_n08` 在本工作树不存在 → 登记为不可解析。
4. **独立校验**：`scripts/kf_wp11924_01_verify.py` 在**新进程、新登录**下**重新拉取** markdown（不信任本地副本），
   重算哈希、逐资产重切片比对 + 唯一性 + 行号一致性、跑 JSON Schema、查 id 唯一性、查 claim 证据策略、
   结构化扫描 `verified` 标记、查 counts 自洽与 report_id 作用域，输出 `artifacts/wp-11924-01/verification.json`。
5. **出图**：`scripts/kf_wp11924_01_figures.py`（matplotlib，Agg）三张图，全部数字读自 manifest/verification。
6. **测试**：`tests/test_kf_wp11924.py` 23 项 —— 12 项正向不变量 + 11 项**反向对照**（篡改引文数字、
   平移 span、非唯一引文、错行号、谎报 resolution、重复 id、counts 造假、claim 无证据、注入 verified 标记、
   越界 report_id、非法 resolution），证明这些门真的会红。

**一键复跑**：`python3 scripts/kf_fetch_11924.py && python3 scripts/kf_wp11924_01_register.py && python3 scripts/kf_wp11924_01_verify.py && python3 scripts/kf_wp11924_01_figures.py && python3 scripts/kf_wp11924_01_report.py`

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/wp-11924-01/asset_manifest.json` | 主产物：42 个资产 / 22 类；34 页内可解析 + 8 外部不可解析 + 0 声明缺失；`sha256=3d09203c46705aa4…`，58841 字节 |
| `artifacts/wp-11924-01/verification.json` | 13 项验收自检逐项结果与证据，`overall=PASS` |
| `artifacts/wp-11924-01/fig_asset_inventory.png` / `fig_locator_coverage.png` / `fig_verification.png` | 图1/图2/图3（见 ④ 末尾） |
| `runs/wp-11924-01/report_11924.md` / `.json` | 源证据快照（markdown + API 原始响应） |
| `runs/wp-11924-01/kf_result.wp-11924-01.json` | 结果信封（package_id/task_type/report_id/provenance/outputs） |
| `schemas/asset_manifest.v1.generic.schema.json` | 本地补写的**与包无关**的 manifest 形状约束（已有 `asset_manifest.v1.schema.json` 把 `package_id`/`report_id` 写死为另一包，不能复用也不宜改动），使 `schema_pass` 可复现 |
| `scripts/kf_fetch_11924.py` / `kf_wp11924_01_register.py` / `kf_wp11924_01_verify.py` / `kf_wp11924_01_figures.py` / `kf_wp11924_01_report.py` | 取证 / 登记 / 校验 / 出图 / 报告 |
| `tests/test_kf_wp11924.py` | 23 项不变量测试（含 11 个反向对照） |
| `docs/wp-11924-01/` | 本报告、manifest/verification 的持久镜像、三张图（推送门会丢弃 `artifacts/**`、`runs/**`，故持久副本落 `docs/`） |

## ④ 证据定位表（claim/字段 → 原文逐字片段）

源：`tensor://reports/11924` · `markdown` · `sha256:21d915c88bbf78f6f90384f52ce2001f1d7709306c373b159625154ab221bd73` · 13138 字符 / 22299 字节。
所有片段为**字符区间切片**，同一片段在原文出现次数恒为 1（可反向定位）。

| asset_id | asset_class | resolution | 行 span | char span | 原文片段（逐字切片，非重述） |
|---|---|---|---|---|---|
| A01 | document | resolved_in_source | 0–244 | 0–13138（全文） | （整篇 markdown；sha256 见 provenance） |
| A02 | heading | resolved_in_source | 0–0 | 0–30 | `# BPM 微观参数三目标联合标定：可行性判定与可辨识性审计` |
| A03 | provenance_header | resolved_in_source | 2–4 | 32–409 | `**节点** P270W2C-N08（任务 m9756）· **仓库** TensorDEM · **分支** `agent/m9756`  ` |
| A04 | acceptance_table | resolved_in_source | 8–17 | 437–1531 | `\| 判据 \| 目标 \| 实测 \| 判定 \|` |
| A05 | statement | resolved_in_source | 23–23 | 1559–1814 | `粘结颗粒模型（BPM）把冰的宏观强度建立在“键强度分布 + 键网络拓扑”上。m7272 建了统计标定管线（吃外部传入的应力历史），m9188 把试件驱动接到 3` |
| A06 | table | resolved_in_source | 29–40 | 1954–2815 | `\| 项 \| 值 \|` |
| A07 | parameter_box | resolved_in_source | 44–51 | 2851–3137 | `\| θ 分量 \| 含义 \| 参数盒下界 \| 上界 \| 采样 \|` |
| A08 | procedure | resolved_in_source | 55–61 | 3151–4057 | `1. **响应面设计**：参考 θ（m9188 工作点）+ 6 个中心差分伙伴（单位立方体步长 h = 0.120）+ 20 个拉丁超立方填充点，共 33 个设` |
| A09 | identifiability_result | resolved_in_source | 74–75 | 4366–4598 | `- cond(J) = **9.063**；奇异值 5.848、2.151、0.645；rank(J) = 3/6，非零奇异值给出的结构零空间维数 3` |
| A10 | table | resolved_in_source | 80–84 | 4704–4943 | `\| \| k_b \| eps_b \| mu_s \| mu_d \| k_c \| k_p \|` |
| A11 | table | resolved_in_source | 90–97 | 5198–5531 | `\| \| k_b \| eps_b \| mu_s \| mu_d \| k_c \| k_p \|` |
| A12 | statement_set | resolved_in_source | 99–102 | 5533–5849 | `**结构不可观测参数**（J 的对应列为零，任何数量级的强度测量都定不出它）：` |
| A13 | recommendation | resolved_in_source | 106–106 | 5862–5963 | `- `k_c` + `k_p`：γ = 6.71，corr = 0.978 → merge into one effective parameter (keep` |
| A14 | table | resolved_in_source | 112–116 | 6135–6299 | `\| 目标 \| 参考 θ 的实测 \| 满足 \|` |
| A15 | branch_verdict | resolved_in_source | 110–110 | 5986–6133 | `参考 θ 的判定：**分支 (c)** —— infeasible at this theta: fewer than two targets are met ` |
| A16 | count_record | resolved_in_source | 118–118 | 6301–6379 | `全部设计点分支计数：a（三目标同满足）= 0，b（仅两目标）= 0，c（不足两目标）= 33。NSGA-II 前沿规模 80，其中三目标全部满足的个体 0。` |
| A17 | table | resolved_in_source | 122–126 | 6395–6636 | `\| 响应 \| in-sample R² \| LOO R² \| LOO RMSE (log10) \| 样本/特征 \| 选中 ridge \|` |
| A18 | table | resolved_in_source | 132–134 | 6770–6976 | `\| θ \| 代理 UCS [MPa] \| 代理 σc/σt \| 代理 m \| 越界量 (UCS, ratio, m) \|` |
| A19 | table | resolved_in_source | 138–141 | 6999–7180 | `\| 留出厚度 t [m] \| DEM 实测 σ_t [MPa] \| 幂律预测 [MPa] \| 相对误差 \| 局部 m \| 达标 \|` |
| A20 | numeric_record | resolved_in_source | 143–143 | 7182–7330 | `拟合得到 m = 262.976（bootstrap 95% CI [24.916, 746.453]，CI 宽度 721.537），σ_ref = 3.71e` |
| A21 | table | resolved_in_source | 149–156 | 7422–7778 | `\| 任务 \| 增量数（相对认证值）\| 峰值应力 [MPa] \| 相对 1× 偏差 \| KE/外功 \|` |
| A22 | table | resolved_in_source | 162–172 | 7929–8407 | `\| 点阵 n_lattice \| 层数 \| 平均区半径/D \| 区内颗粒数 \| 峰值主应力比 \| 相对 −3.0 偏差 \| 有限读数 \|` |
| A23 | verdict | resolved_in_source | 174–174 | 8409–8610 | `判定：PASS（容差 15%，按**中心区**读数判定）；但跨 9 个（分辨率 × 区域）配置的偏差范围 10–788%，**稳健性 FAIL**：结论只在最细` |
| A24 | statement_set | resolved_in_source | 178–179 | 8638–8852 | `- **AC6**：200 组随机 θ 的 UCS 分位 min 0.295 / q05 0.644 / 中位 2.546 / q95 6.224 / max ` |
| A25 | figure_declaration | resolved_in_source | 181–205 | 8854–9673 | `### 3.7 图` |
| A26 | figure_binary_set | referenced_unresolved | 183–183 | 8865–8930 | `![response surface](figures/p270w2c_n08/fig_response_surface.png)` |
| A27 | limitation_set | resolved_in_source | 209–210 | 9704–10352 | `1. **宽矩阵的条件数是“假朋友”**。3 响应 × 6 参数时 cond(J) 只由三个非零奇异值构成，两列完全相同也不会让 cond 变大（本节点用相同列` |
| A28 | limitation_set | resolved_in_source | 212–214 | 10354–10897 | `2. **σ_t 的观测面选择**。巴西劈裂在本文点阵上不能当强度 oracle（§5），因此三目标里的 σ_t 取**单轴直接拉伸**（尺寸效应族最薄拟合厚度` |
| A29 | limitation_set | resolved_in_source | 215–215 | 10898–11123 | `4b. **强度对加载增量敏感（UCS）**。协议细化表（§3.4b）显示：增量加密 1×→2×→4× 时，UCS 由 1.01 → 0.86 → 0.67 M` |
| A30 | limitation_set | resolved_in_source | 217–217 | 11125–11264 | `5. **应力张量缺切向/摩擦接触力**。Love–Weber 求和只含键轴向力与破坏后接触法向力；准静态 hold 末切向力小且判据用主应力比（共同因子部分抵` |
| A31 | limitation_set | resolved_in_source | 218–218 | 11265–11463 | `5b. **准静态门（KE/外功 ≤1e-3）在拉伸试件上不达标**。带断裂的试件在峰值前已出现局部键断裂，碎片动能进入读数，全运行最大 KE/外功 0.022` |
| A32 | limitation_set | resolved_in_source | 220–222 | 11465–11778 | `6. **简单立方点阵的各向异性**。沿加载轴存在直链，载荷偏向单链传递，中心横向拉应力远小于连续介质解——这是 AC5 honest FAIL 的物理根因，也` |
| A33 | table | resolved_in_source | 226–234 | 11806–12237 | `\| 关键量 \| 基准 \| 实测误差 \| 是否 < 3% \|` |
| A34 | statement | resolved_in_source | 236–236 | 12239–12440 | `**“是否 < 3%”的显式回答**：数值可复现性与准静态门 = **是**；尺寸效应拟合的内插自洽 = 见上表两项（留出端误差以数字给出，不在 3% 内即如实` |
| A35 | test_record | resolved_in_source | 240–243 | 12455–13137 | `- `tests/test_bpm_calibration_feasibility.py`（42 项，全绿）：AC1 几何先验 3 例（含 2 个负控）；θ 往` |
| A36 | code_reference | referenced_unresolved | 3–3 | 104–159 | `**新增模块** `src/tensordem/bpm_calibration_feasibility.py`` |
| A37 | code_reference | referenced_unresolved | 3–3 | 162–207 | `**战役脚本** `scripts/p270w2c_n08_feasibility.py`` |
| A38 | code_reference | referenced_unresolved | 241–241 | 12763–12846 | `- 运行：`PYTHONPATH=src python -m pytest tests/test_bpm_calibration_feasibility.py ` |
| A39 | dataset | referenced_unresolved | 4–4 | 303–344 | `**原始数据** `runs/p270w2c_n08/records.jsonl`` |
| A40 | dataset | referenced_unresolved | 4–4 | 353–397 | `**判据数字** `artifacts/p270w2c_n08/report.json`` |
| A41 | audit_archive | referenced_unresolved | 210–210 | 9859–10352 | `1b. **运动学驱动的瞬态撕裂（本节点最大的一坑）**。试件只有顶层被驱动，一次 ramp 的位移``eps_inc × gauge`` 在试件跟上之前全部压` |
| A42 | code_reference | referenced_unresolved | 213–213 | 10557–10603 | `legacy `bpm_calibration`/`bpm_identifiability`` |

### 页面内不可解析资产（如实登记，不补造地址）

| asset_id | 报告内定位（相对路径/模块） | 机器检查 | 结果 |
|---|---|---|---|
| A26 | — | platform_figures_field + worktree_path_exists | unresolved |
| A36 | src/tensordem/bpm_calibration_feasibility.py | worktree_path_exists + report_url_doi_scan | unresolved |
| A37 | scripts/p270w2c_n08_feasibility.py | worktree_path_exists + report_url_doi_scan | unresolved |
| A38 | tests/test_bpm_calibration_feasibility.py | worktree_path_exists + report_url_doi_scan | unresolved |
| A39 | runs/p270w2c_n08/records.jsonl | worktree_path_exists + report_url_doi_scan | unresolved |
| A40 | artifacts/p270w2c_n08/report.json | worktree_path_exists + report_url_doi_scan | unresolved |
| A41 | runs/p270w2c_n08/v{1,2,3}_protocol_superseded/ | worktree_path_exists + report_url_doi_scan | unresolved |
| A42 | — | report_url_doi_path_scan | unresolved |

### 结果图

- 图1 `fig_asset_inventory.png`：22 类资产 × 可解析状态分布。
- 图2 `fig_locator_coverage.png`：42 个资产的 char span 定位地图（11643 / 13138 字符被页内资产覆盖，
  coverage = 0.8862）。
- 图3 `fig_verification.png`：13 项验收自检板（平台门为权威判定）。

## ⑤ 注意点与局限

1. **参数盒上下界在上游缺失**：参数盒表（A07）的"下界/上界"列全为 `n/a`，报告只给采样方式（log/linear）。
   本工序**如实登记缺失**，不按常理补数值。
2. **8 个资产不可解析**（A26/A36/A37/A38/A39/A40/A41/A42）：全部是被登记报告里**指向 TensorDEM 仓**的
   相对路径（模块、脚本、测试、`records.jsonl`、`report.json`、回炉留档目录）或图件二进制。报告未给 URL/DOI，
   本工作树（TensorKnowledge）内不存在这些路径，因此判 `referenced_unresolved`，**不联网猜地址**。
   下游若需取用，必须回到 TensorDEM 仓按路径解析。
3. **平台 figures 只有声明没有二进制**：API payload 的 `figures` 有 6 条 `name`/`caption`，无 `png_base64`，
   故"图件本体"不是可解析资产；但图注文字（A25）在原文可解析。
4. **上游 honest FAIL 原样保留**：AC6/AC7 记 FAIL、AC5 跨配置稳健性 FAIL、UCS 随增量加密未收敛（1.01→0.86→0.67 MPa）。
   本工序不改判、不软化措辞——登记的是"上游说了什么"，不是"我认为对不对"。
5. **图内标签用英文**：本工作树镜像无 CJK 字体（`fc-list` 无中文字族），中文标签会渲染成豆腐块，
   因此三张图用英文标签；中文表述留在本报告正文与 manifest 的 `label` 字段。
6. **schema_pass 用的是本地 generic schema**：仓内 `schemas/asset_manifest.v1.schema.json` 的
   `package_id`/`report_id` 是 `const`（另一包的），改它会污染别的工作包产物；故新增与之同形的
   generic 版本供任意 `01-asset-registration` 包复用。**若平台侧 canonical schema 不同，以平台门为准。**
7. **coverage ≠ 完整性**：0.8862 的字符覆盖率统计的是"被页内资产 char span 覆盖的字符"，
   空白行、过渡句未覆盖属正常；覆盖率不是"信息是否抽全"的度量（抽取不在本工序范围）。

## ⑥ 自检：逐条对照 acceptance

| acceptance 条目 | 打勾 | 依据 |
|---|---|---|
| valid_json | ✓ | valid_json → pass |
| schema_pass | ✓ | schema_pass → pass |
| source_locator_resolvable | ✓ | source_locator_resolvable → pass |
| source_hash_matches | ✓ | source_hash_matches → pass |
| no_duplicate_ids | ✓ | no_duplicate_ids → pass |
| all_claims_have_evidence_or_explicit_unresolved_status | ✓ | all_claims_have_evidence_or_explicit_unresolved_status → pass |

补充自检项（非 acceptance 但本工序自己加的护栏，全部 PASS 才判 overall=PASS）：

| 验收项 | 结果 | 证据（verification.json 摘录） |
|---|---|---|
| valid_json | PASS | {"manifest": "artifacts/wp-11924-01/asset_manifest.json", "result": "runs/wp-11924-01/kf_result.wp-11924-01.json", "block_identical_to_result": true} |
| schema_pass | PASS | {"schema": "schemas/asset_manifest.v1.generic.schema.json", "envelope_schema": "schemas/kf_result.v1.schema.json", "note": "generic twin of the package-pinned asset_manif… |
| source_hash_matches | PASS | {"recomputed_sha256": "21d915c88bbf78f6f90384f52ce2001f1d7709306c373b159625154ab221bd73", "contract_sha256": "21d915c88bbf78f6f90384f52ce2001f1d7709306c373b159625154ab221… |
| source_locator_resolvable | PASS | {"assets_checked": 42, "failures": [], "quote_uniqueness": "every char_span quote occurs exactly once in the fetched markdown"} |
| no_duplicate_ids | PASS | {"duplicate_asset_ids": [], "asset_ids": 42, "claim_ids": []} |
| all_claims_have_evidence_or_explicit_unresolved_status | PASS | {"claims": 0, "offending": [], "policy": "claims=[] by contract (objective.classify_report_type=false, no extraction); any future claim must carry evidence/evidence_locat… |
| resolution_check_consistency | PASS | {"failures": []} |
| counts_consistency | PASS | {"failures": [], "counts": {"assets": 42, "by_class": {"document": 1, "heading": 1, "provenance_header": 1, "acceptance_table": 1, "statement": 2, "table": 10, "parameter… |
| no_verified_markers | PASS | {"hits": [], "note": "contract forbids marking claims verified; verification is computed by the platform gate, this package records verification_status=not_verified"} |
| artifact_hash_matches_envelope | PASS | {"artifact_sha256": "3d09203c46705aa4833bfbaf48c165b62498773f6d063872b4438524e272c360", "envelope_sha256": "3d09203c46705aa4833bfbaf48c165b62498773f6d063872b4438524e272c3… |
| report_scope_isolation | PASS | {"failures": [], "note": "package touches report 11924 only"} |
| durable_mirror_identical | PASS | {"mirror": "docs/wp-11924-01/asset_manifest.json", "exists": true} |
| platform_metadata_matches_manifest | PASS | {"platform_id": 11924, "title_match": true, "scenario_key_match": true} |

### 误差判定（关键量 vs 基准，逐项；显式回答"是否 <3%"）

| 关键量 | 基准 | 实测偏差 | 是否 <3% |
|---|---|---|---|
| markdown sha256 | 契约 `source_hash` = `21d915c88bbf78f6…` | 0（字符串逐字节相等）| 是 |
| markdown 字符数 | 契约 `chars` = 13138 | 0（13138）| 是 |
| 定位可复现性 | 每个 quote 必须能由 `[start_char,end_char)` 反向切出且全文唯一 | 0 失败 / 42 资产 | 是 |
| id 唯一性 | 无重复 asset_id | 0 重复 | 是 |
| 资产计数自洽 | `counts` 必须由 `assets[]` 派生 | 0 不符 | 是 |
| 物理量对标（阻力/强度…）| — | — | **无基准可对**：本工序不产生物理量，只登记定位；故不编造误差结论 |

显式回答：本工序的三类关键量（源哈希、源长度、定位可复现性）均为**精确相等**（偏差 0，远优于 3%）；
本包**没有**物理量/实验基准可对标，按纪律声明原因，不给"<3%"的空头结论。

### 复现

```bash
python3 scripts/kf_fetch_11924.py && python3 scripts/kf_wp11924_01_register.py && python3 scripts/kf_wp11924_01_verify.py && python3 scripts/kf_wp11924_01_figures.py && python3 scripts/kf_wp11924_01_report.py
```

预期：`asset_manifest.json` 的 `sha256=3d09203c46705aa4833bfbaf48c165b62498773f6d063872b4438524e272c360` 复现，
`verification.json` 的 `overall=PASS`。

```json
{
  "package_id": "wp-11924-01",
  "task_type": "01-asset-registration",
  "report_id": "11924",
  "provenance": {
    "source_uri": "tensor://reports/11924",
    "source_field": "markdown",
    "source_hash": "sha256:21d915c88bbf78f6f90384f52ce2001f1d7709306c373b159625154ab221bd73",
    "source_chars": 13138,
    "source_bytes_utf8": 22299,
    "source_title": "BPM 微观参数三目标联合标定的可行性判定与可辨识性审计（P270W2C-N08）",
    "scenario_key": "p270w2c-n08-bpm-calibration-feasibility",
    "contract_version": "1.0",
    "lane": "C",
    "work_package": "wp-11924-01",
    "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/11924",
    "local_copy": "runs/wp-11924-01/report_11924.md",
    "generator": "scripts/kf_wp11924_01_register.py",
    "verifier": "scripts/kf_wp11924_01_verify.py",
    "verification_status": "not_verified"
  },
  "outputs": {
    "asset_manifest.json": {
      "artifact_path": "artifacts/wp-11924-01/asset_manifest.json",
      "artifact_sha256": "3d09203c46705aa4833bfbaf48c165b62498773f6d063872b4438524e272c360",
      "artifact_bytes": 58841,
      "schema": "asset_manifest.v1",
      "package_id": "wp-11924-01",
      "task_type": "01-asset-registration",
      "report_id": "11924",
      "source": {
        "uri": "tensor://reports/11924",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "21d915c88bbf78f6f90384f52ce2001f1d7709306c373b159625154ab221bd73",
        "chars": 13138,
        "bytes_utf8": 22299,
        "title": "BPM 微观参数三目标联合标定的可行性判定与可辨识性审计（P270W2C-N08）",
        "scenario_key": "p270w2c-n08-bpm-calibration-feasibility",
        "platform_id": 11924,
        "platform_mission_id": 9756,
        "platform_status": "published",
        "platform_figures": [
          {
            "name": "fig_response_surface.png",
            "caption": "响应面切片：每列一个微观参数（单位立方体坐标），每行一个宏观响应（UCS / σc/σt / Weibull m）；绿色带为验收目标带。"
          },
          {
            "name": "fig_jacobian.png",
            "caption": "可辨识性审计：量纲一化 Jacobian dlog10(y)/du、参数相关矩阵（JᵀJ 归一化）与 Brun collinearity index。"
          },
          {
            "name": "fig_pareto.png",
            "caption": "代理响应面上的 NSGA-II 种群与 Pareto 前沿（三目标两两投影）；越界量 0 表示目标满足。"
          },
          {
            "name": "fig_size_effect.png",
            "caption": "Weibull 尺寸效应：参考 θ 的五厚度族与幂律拟合（虚线为留出厚度），右图为留出厚度外推误差。"
          },
          {
            "name": "fig_brazilian.png",
            "caption": "巴西圆盘中心主应力比 vs 应力平均区半径（三种点阵分辨率）与 Hondros −3.0 容差带；右图为比值读数历史。"
          },
          {
            "name": "fig_ucs.png",
            "caption": "参考 θ 的单轴压缩应力–应变迹（hold 末读数）与 AC6 负控 200 组随机 θ 的 UCS 分布。"
          }
        ],
        "platform_tags": [
          "DEM",
          "BPM",
          "calibration",
          "identifiability",
          "Weibull",
          "Brazilian-test",
          "NSGA-II",
          "TensorDEM",
          "P270W2C-N08"
        ],
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/11924",
        "local_copy": "runs/wp-11924-01/report_11924.md"
      },
      "counts": {
        "assets": 42,
        "by_class": {
          "document": 1,
          "heading": 1,
          "provenance_header": 1,
          "acceptance_table": 1,
          "statement": 2,
          "table": 10,
          "parameter_box": 1,
          "procedure": 1,
          "identifiability_result": 1,
          "statement_set": 2,
          "recommendation": 1,
          "branch_verdict": 1,
          "count_record": 1,
          "numeric_record": 1,
          "verdict": 1,
          "figure_declaration": 1,
          "figure_binary_set": 1,
          "limitation_set": 6,
          "test_record": 1,
          "code_reference": 4,
          "dataset": 2,
          "audit_archive": 1
        },
        "by_resolution": {
          "resolved_in_source": 34,
          "referenced_unresolved": 8
        },
        "resolved_in_source": 34,
        "referenced_unresolved": 8,
        "declared_absent": 0,
        "chars_covered_by_char_spans": 11643,
        "coverage_fraction": 0.8862
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "document",
          "label": "报告正文（markdown 全文，含摘要/图表/误差判定）",
          "in_report_section": "(document)",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 13138,
            "start_line": 0,
            "end_line": 244,
            "quote": "# BPM 微观参数三目标联合标定：可行性判定与可辨识性审计",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256_of_full_markdown_vs_contract",
            "result": "resolved",
            "chars": 13138,
            "detail": "全文字节级重算；见 source.hash"
          },
          "note": "整篇 markdown 即源资产；sha256 见 source.hash，字符数 13138、UTF-8 字节数 22299"
        },
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "报告标题（与平台 title 字段同源）",
          "in_report_section": "(document)",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 30,
            "start_line": 0,
            "end_line": 0,
            "quote": "# BPM 微观参数三目标联合标定：可行性判定与可辨识性审计",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "一级标题行"
        },
        {
          "asset_id": "A03",
          "asset_class": "provenance_header",
          "label": "节点/仓库/分支 + 新增模块 + 原始数据与判据数字来源声明",
          "in_report_section": "# BPM 微观参数三目标联合标定：可行性判定与可辨识性审计",
          "locator": {
            "method": "char_span",
            "start_char": 32,
            "end_char": 409,
            "start_line": 2,
            "end_line": 4,
            "quote": "**节点** P270W2C-N08（任务 m9756）· **仓库** TensorDEM · **分支** `agent/m9756`  \n**新增模块** `src/tensordem/bpm_calibration_feasibility.py` · **战役脚本** `scripts/p270w2c_n08_feasibility.py`（sample/analyze）· **图/报告渲染** `scripts/p270w2c_n08_figures.py`、`scripts/p270w2c_n08_report.py`  \n**原始数据** `runs/p270w2c_n08/records.jsonl`（逐任务记录）· **判据数字** `artifacts/p270w2c_n08/report.json`（本报告的唯一数字来源）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "三行溯源声明；其中引用的外部路径分别登记为 A36/A39/A40"
        },
        {
          "asset_id": "A04",
          "asset_class": "acceptance_table",
          "label": "结论速览表 AC1–AC8（判据 → 目标 → 实测 → 判定）",
          "in_report_section": "## 0. 结论速览（判据 → 数字 → 判定）",
          "locator": {
            "method": "char_span",
            "start_char": 437,
            "end_char": 1531,
            "start_line": 8,
            "end_line": 17,
            "quote": "| 判据 | 目标 | 实测 | 判定 |\n|---|---|---|---|\n| AC1 几何/尺度先验 | 全部子项通过 | UCS 试件 H/D = 2.000；圆盘 D/t = 1.750；堆积率 0.5236（π/6 = 0.5236）；拉伸族 H/D = 0.50–8.00；加载协议瞬态应变 0.0112 < 断裂应变 0.015 | PASS |\n| AC2 可辨识性 | 报 cond(J) 与相关矩阵；cond>1e4 必须判不可辨识并给降维建议 | cond(J) = 9.063，rank = 3/6，结构零空间维数 3；最坏参数对 ['k_c', 'k_p'] 的 Brun γ = 6.71；判定 **structurally-underdetermined** | PASS |\n| AC3 三分支可行性 | (a)/(b)/(c) 之一 + 证据 | 参考 θ 落 **分支 (c)**：UCS 1.010 MPa、σc/σt 2.688、m CI [24.916, 746.453] （伪真值 6.000）；33 个设计点分支计数 a/b/c = 0/0/33 | 见 §3.3 |\n| AC4 留出厚度外推 | 误差 ≤15% 且两端 m 方向一致 | t=0.05 m 误差 -5.4%；t=0.80 m 误差 +2.6%；方向一致 是；有完整留出对（t=0.05 与 0.8）的设计点通过 1/1（另有 1/33 个点通过已有的 t=0.05 单端留出）| PASS |\n| AC5 巴西中心应力比 | 与 Hondros −3.0 相对差 ≤15% | 最优 -2.705（9×4 点阵，平均区 0.12D），相对差 9.8% | PASS（最优配置；跨配置偏差 10–788% → 稳健性 FAIL，见 §3.5）|\n| AC6 负控 200 组随机 θ | ≥95% 违反 UCS 文献带 | 违反比例 83.5%（n = 200；UCS 中位 2.546 MPa）| FAIL |\n| AC7 复现性 + 准静态门 | 同 θ 两次 UCS 相对差 ≤1e-3 且 KE/外功 ≤1e-3 | 相对差 0.000；全运行最大 KE/外功 0.022（拉伸试件超门，见 §4 条 5b）| FAIL（复现性 PASS / 准静态门 FAIL）|\n| AC8 pytest | ≥20 项，含 AC2–AC6 负控 | `tests/test_bpm_calibration_feasibility.py`（42 项，见 §6）| PASS |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "8 条判据的判定标记；本工序只登记，不重新裁定 PASS/FAIL"
        },
        {
          "asset_id": "A05",
          "asset_class": "statement",
          "label": "核心问题与微观参数向量 θ 的定义",
          "in_report_section": "### 1.1 物理背景",
          "locator": {
            "method": "char_span",
            "start_char": 1559,
            "end_char": 1814,
            "start_line": 23,
            "end_line": 23,
            "quote": "粘结颗粒模型（BPM）把冰的宏观强度建立在“键强度分布 + 键网络拓扑”上。m7272 建了统计标定管线（吃外部传入的应力历史），m9188 把试件驱动接到 3-D 引擎并逐项审计了质量缩放门、Weibull 尺寸效应与摩擦正则化，但两者都没回答本节点的核心问题：**同一个微观参数向量 θ = (k_b, ε_b, μ_s, μ_d, k_c, k_p) 能否同时满足 (UCS ∈ 文献带, σc/σt ∈ [2.5, 4], Weibull m)，以及这三个观测量究竟能不能把这 6 个参数辨识出来**。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "θ 六分量定义所在行"
        },
        {
          "asset_id": "A06",
          "asset_class": "table",
          "label": "§1.2 几何与参数表（试件尺寸/点阵/加载协议/验收目标）",
          "in_report_section": "### 1.2 几何与参数",
          "locator": {
            "method": "char_span",
            "start_char": 1954,
            "end_char": 2815,
            "start_line": 29,
            "end_line": 40,
            "quote": "| 项 | 值 |\n|---|---|\n| 颗粒半径 R | 0.0125 m（简单立方点阵，间距 2R = 0.025 m）|\n| UCS 试件 | 4×4×9 格 → D = 0.1 m、标距 H = 0.2 m、H/D = 2.000、颗粒数 144 |\n| 尺寸效应族（单轴拉伸）| t = 0.05/0.1/0.2/0.4/0.8 m，层数 3/5/9/17/33，截面固定 0.1×0.1 m（体积 ∝ t）；拟合用 0.1/0.2/0.4（各 4 个试件），留出 0.05（全部设计点）与 0.8（参考 θ，2 个试件——最贵的试件）|\n| 巴西圆盘 | D = 0.175 m（7×7 点阵）、t = 0.1 m（4 层）、线载荷加载弧半角 0.1723 rad （≈9.9°）|\n| 加载协议 | 分步 load–relax：目标应变 2%，ramp 12 步 + hold 60 步，settle 40 步，hold 末端读数（扣除驱动层粘性 drag）；**增量数按试件键层数自适应**（下表），否则长试件会在第一个 ramp 内撕开顶层键（见 §4 条 1b）|\n| 增量数（自适应）| t=0.05: 8（键层 2）、t=0.10: 8（键层 4）、t=0.20: 15（键层 8）、t=0.40: 29（键层 16）、t=0.80: 57（键层 32） |\n| 质量缩放 β | 100；dt 由 `DEM3DConfig.recommended_dt` **逐配置重算**（含 k_p 对稳定性的影响）|\n| 摩擦 | 引擎 `friction_regularization=\"dual\"`（μ_s 粘着锥 / μ_d 滑移）|\n| 键强度离散 | 每键 Weibull，m_bond = 6，中位断裂应变 = ε_b |\n| 验收目标 | UCS ∈ [5.0, 15.0] MPa（Schulson & Duval）、σc/σt ∈ [2.5, 4.0]、Hondros 比 -3.0 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "10 行数据；数值仅登记，不换算不复核"
        },
        {
          "asset_id": "A07",
          "asset_class": "parameter_box",
          "label": "参数盒表（θ 六分量的含义/下界/上界/采样方式）",
          "in_report_section": "### 1.2 几何与参数",
          "locator": {
            "method": "char_span",
            "start_char": 2851,
            "end_char": 3137,
            "start_line": 44,
            "end_line": 51,
            "quote": "| θ 分量 | 含义 | 参数盒下界 | 上界 | 采样 |\n|---|---|---|---|---|\n| `k_b` | 键轴向刚度 | n/a | n/a | log |\n| `eps_b` | 中位断裂应变 | n/a | n/a | linear |\n| `mu_s` | 静摩擦 | n/a | n/a | linear |\n| `mu_d` | 动摩擦 | n/a | n/a | linear |\n| `k_c` | 接触法向刚度（破坏后） | n/a | n/a | log |\n| `k_p` | 接触切向刚度 | n/a | n/a | log |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "原文界列全为 n/a：参数盒上下界在报告中缺失，如实登记缺失、不补造数值"
        },
        {
          "asset_id": "A08",
          "asset_class": "procedure",
          "label": "§2 方法七步（响应面/Jacobian/可辨识性/NSGA-II/留出门/应力场/负控复现）",
          "in_report_section": "## 2. 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 3151,
            "end_char": 4057,
            "start_line": 55,
            "end_line": 61,
            "quote": "1. **响应面设计**：参考 θ（m9188 工作点）+ 6 个中心差分伙伴（单位立方体步长 h = 0.120）+ 20 个拉丁超立方填充点，共 33 个设计点。每点：1 次单轴压缩（UCS）+ 5 个厚度的单轴拉伸族（拟合厚度 4 次重复、留出厚度 3 次重复），合计 747 个 DEM 任务，48 进程并行，墙钟 916 s。\n2. **数值 Jacobian**：响应取 log10(UCS, σ_t, m)，参数取单位立方体坐标，中心差分得 3×6 的量纲一化相对敏感度矩阵 J；同一 J 用于条件数、相关矩阵与共线性诊断。\n3. **可辨识性诊断**：SVD 条件数、Belsley 条件指数与方差分解、JᵀJ 归一化的参数相关矩阵、Brun collinearity index（全列 + 逐对），以及**结构秩结论**（3 个观测量对 6 个参数 → 秩 ≤ 3）与机器可读降维建议。\n4. **NSGA-II**：自实现实数编码 NSGA-II（SBX 交叉 + 多项式变异 + 非支配排序 + 拥挤度），目标为（UCS 越界量、σc/σt 越界量、|m − 伪真值|/m），在二次响应面代理上评估，初始种群植入全部 DEM 设计点使搜索锚在数据处；代理精度以 in-sample R² 与 LOO R² 公示。\n5. **留出门**：用 t = 0.1/0.2/0.4 拟合 σ_t(t) = σ₀·t^(−1/m)，预测留出的 t = 0.05 与 0.8 m；除误差外还检查两端局部 m 的**方向一致性**（两端都仍随尺寸减弱、且相对全局 m 的偏差同号）。\n6. **应力场闭合**：Love–Weber 离散应力张量（键轴向力 + 破坏后接触法向力）在圆盘中心区**环向（区域）平均**，取面内主应力比与 Hondros −3.0 比对；扫 3 种点阵分辨率 × 3 个平均区半径，并与单格点值对照。\n7. **负控与复现**：200 组随机 θ 只跑 UCS（AC6，验证“随机参数几乎不可能落进文献带”）；同 θ 两次独立进程 UCS + 全运行 KE/外功统计（AC7）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "7 条方法步骤原文，含 33 点/747 任务/916 s 等规模数字"
        },
        {
          "asset_id": "A09",
          "asset_class": "identifiability_result",
          "label": "AC2 判定：cond(J)=9.063 / rank 3 of 6 / structurally-underdetermined",
          "in_report_section": "### 3.2 可辨识性（AC2）",
          "locator": {
            "method": "char_span",
            "start_char": 4366,
            "end_char": 4598,
            "start_line": 74,
            "end_line": 75,
            "quote": "- cond(J) = **9.063**；奇异值 5.848、2.151、0.645；rank(J) = 3/6，非零奇异值给出的结构零空间维数 3\n- 判定：**structurally-underdetermined** —— 6 parameters against 3 observables: at most 3 directions are identifiable, 3 remain unconstrained (null space of J)",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "条件数行 + 判定行（含英文机器可读结论串）"
        },
        {
          "asset_id": "A10",
          "asset_class": "table",
          "label": "量纲一化 Jacobian 表（3 响应 × 6 参数）",
          "in_report_section": "### 3.2 可辨识性（AC2）",
          "locator": {
            "method": "char_span",
            "start_char": 4704,
            "end_char": 4943,
            "start_line": 80,
            "end_line": 84,
            "quote": "| | k_b | eps_b | mu_s | mu_d | k_c | k_p |\n|---|---|---|---|---|---|---|\n| UCS | +0.32 | +0.47 | +0.00 | +0.00 | +1.05 | +0.32 |\n| σ_t | +1.33 | +1.51 | +0.00 | +0.00 | +0.14 | +0.14 |\n| m | +3.00 | -1.61 | +0.00 | +0.00 | -3.32 | -3.32 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "表头 + 分隔行 + UCS/σ_t/m 三行"
        },
        {
          "asset_id": "A11",
          "asset_class": "table",
          "label": "参数相关矩阵表（JᵀJ 归一化，6 × 6，恒零列记 —）",
          "in_report_section": "### 3.2 可辨识性（AC2）",
          "locator": {
            "method": "char_span",
            "start_char": 5198,
            "end_char": 5531,
            "start_line": 90,
            "end_line": 97,
            "quote": "| | k_b | eps_b | mu_s | mu_d | k_c | k_p |\n|---|---|---|---|---|---|---|\n| k_b | +1.00 | -0.36 | — | — | -0.82 | -0.88 |\n| eps_b | -0.36 | +1.00 | — | — | +0.77 | +0.76 |\n| mu_s | — | — | — | — | — | — |\n| mu_d | — | — | — | — | — | — |\n| k_c | -0.82 | +0.77 | — | — | +1.00 | +0.98 |\n| k_p | -0.88 | +0.76 | — | — | +0.98 | +1.00 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "表头 + 分隔行 + 6 个参数行"
        },
        {
          "asset_id": "A12",
          "asset_class": "statement_set",
          "label": "结构不可观测参数声明（mu_s / mu_d 列范数 0.000）",
          "in_report_section": "### 3.2 可辨识性（AC2）",
          "locator": {
            "method": "char_span",
            "start_char": 5533,
            "end_char": 5849,
            "start_line": 99,
            "end_line": 102,
            "quote": "**结构不可观测参数**（J 的对应列为零，任何数量级的强度测量都定不出它）：\n\n- `mu_s`：列范数 0.000 → structurally unobservable from these responses: fix it at a literature value or add an observable that depends on it\n- `mu_d`：列范数 0.000 → structurally unobservable from these responses: fix it at a literature value or add an observable that depends on it",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "标题行 + 两个参数条目（含机器可读处置建议串）"
        },
        {
          "asset_id": "A13",
          "asset_class": "recommendation",
          "label": "机器可读降维建议（k_c + k_p 合并，γ = 6.71）",
          "in_report_section": "### 3.2 可辨识性（AC2）",
          "locator": {
            "method": "char_span",
            "start_char": 5862,
            "end_char": 5963,
            "start_line": 106,
            "end_line": 106,
            "quote": "- `k_c` + `k_p`：γ = 6.71，corr = 0.978 → merge into one effective parameter (keep the product / ratio)",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "建议段唯一一条条目"
        },
        {
          "asset_id": "A14",
          "asset_class": "table",
          "label": "AC3 参考 θ 的三目标实测与满足性表",
          "in_report_section": "### 3.3 可行性三分支（AC3）",
          "locator": {
            "method": "char_span",
            "start_char": 6135,
            "end_char": 6299,
            "start_line": 112,
            "end_line": 116,
            "quote": "| 目标 | 参考 θ 的实测 | 满足 |\n|---|---|---|\n| UCS ∈ [5.0, 15.0] MPa | 1.010 MPa | 否 |\n| σc/σt ∈ [2.5, 4.0] | 2.688 | 是 |\n| m 的 95% CI 覆盖伪真值 6.000 | [24.916, 746.453] | 否 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "表头 + 分隔行 + UCS / σc/σt / m CI 三行"
        },
        {
          "asset_id": "A15",
          "asset_class": "branch_verdict",
          "label": "AC3 三分支判定：参考 θ 落分支 (c)（含英文机器可读串）",
          "in_report_section": "### 3.3 可行性三分支（AC3）",
          "locator": {
            "method": "char_span",
            "start_char": 5986,
            "end_char": 6133,
            "start_line": 110,
            "end_line": 110,
            "quote": "参考 θ 的判定：**分支 (c)** —— infeasible at this theta: fewer than two targets are met -- the calibration problem cannot be closed from these observables。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "单行判定；分支定义为 a/b/c 三档"
        },
        {
          "asset_id": "A16",
          "asset_class": "count_record",
          "label": "全部设计点分支计数 a/b/c = 0/0/33 + NSGA-II 前沿规模 80",
          "in_report_section": "### 3.3 可行性三分支（AC3）",
          "locator": {
            "method": "char_span",
            "start_char": 6301,
            "end_char": 6379,
            "start_line": 118,
            "end_line": 118,
            "quote": "全部设计点分支计数：a（三目标同满足）= 0，b（仅两目标）= 0，c（不足两目标）= 33。NSGA-II 前沿规模 80，其中三目标全部满足的个体 0。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "单行计数记录"
        },
        {
          "asset_id": "A17",
          "asset_class": "table",
          "label": "代理（二次响应面）精度表：in-sample R² / LOO R² / LOO RMSE / 样本特征数",
          "in_report_section": "### 3.3 可行性三分支（AC3）",
          "locator": {
            "method": "char_span",
            "start_char": 6395,
            "end_char": 6636,
            "start_line": 122,
            "end_line": 126,
            "quote": "| 响应 | in-sample R² | LOO R² | LOO RMSE (log10) | 样本/特征 | 选中 ridge |\n|---|---|---|---|---|---|\n| ucs | 0.9965 | 0.9302 | 0.0774 | 33/28 | n/a |\n| ratio | 0.9951 | 0.8604 | 0.1195 | 33/28 | n/a |\n| m | 0.8092 | 0.0904 | 0.5689 | 26/28 | n/a |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "含 m 的 LOO R² = 0.0904（精度低，原文已声明前沿结论按 LOO 解读）"
        },
        {
          "asset_id": "A18",
          "asset_class": "table",
          "label": "前沿最小越界量个体（代理值 θ 与三个代理响应）",
          "in_report_section": "### 3.3 可行性三分支（AC3）",
          "locator": {
            "method": "char_span",
            "start_char": 6770,
            "end_char": 6976,
            "start_line": 132,
            "end_line": 134,
            "quote": "| θ | 代理 UCS [MPa] | 代理 σc/σt | 代理 m | 越界量 (UCS, ratio, m) |\n|---|---|---|---|---|\n| k_b=2.59e+05、eps_b=0.048、mu_s=0.887、mu_d=0.521、k_c=4.75e+05、k_p=3.00e+06 | 5.140 | 3.194 | 6.003 | 0.000、0.000、5.65e-04 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "单行参数/响应记录；原文声明未回代 DEM"
        },
        {
          "asset_id": "A19",
          "asset_class": "table",
          "label": "AC4 留出厚度外推表（t=0.05 / 0.80 m）",
          "in_report_section": "### 3.4 留出厚度外推（AC4）",
          "locator": {
            "method": "char_span",
            "start_char": 6999,
            "end_char": 7180,
            "start_line": 138,
            "end_line": 141,
            "quote": "| 留出厚度 t [m] | DEM 实测 σ_t [MPa] | 幂律预测 [MPa] | 相对误差 | 局部 m | 达标 |\n|---|---|---|---|---|---|\n| 0.05 | 0.397 | 0.376 | -5.4% | 0.080 | 是 |\n| 0.80 | 0.362 | 0.372 | +2.6% | 0.045 | 是 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "表头 + 分隔行 + 两个留出厚度行"
        },
        {
          "asset_id": "A20",
          "asset_class": "numeric_record",
          "label": "幂律拟合参数：m = 262.976、bootstrap CI、σ_ref、端点局部 m 与方向一致性",
          "in_report_section": "### 3.4 留出厚度外推（AC4）",
          "locator": {
            "method": "char_span",
            "start_char": 7182,
            "end_char": 7330,
            "start_line": 143,
            "end_line": 143,
            "quote": "拟合得到 m = 262.976（bootstrap 95% CI [24.916, 746.453]，CI 宽度 721.537），σ_ref = 3.71e+05 Pa；端点局部 m：t=0.05 → 0.080、t=0.8 → 0.045，方向一致性 是。有完整留出对的设计点通过 1/1。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "单行数字记录（CI 宽度 721.537）"
        },
        {
          "asset_id": "A21",
          "asset_class": "table",
          "label": "§3.4b 协议细化收敛表（UCS 与 t=0.4 m 拉伸各 1×/2×/4×）",
          "in_report_section": "### 3.4b 协议细化收敛（强度不是步长的产物吗？）",
          "locator": {
            "method": "char_span",
            "start_char": 7422,
            "end_char": 7778,
            "start_line": 149,
            "end_line": 156,
            "quote": "| 任务 | 增量数（相对认证值）| 峰值应力 [MPa] | 相对 1× 偏差 | KE/外功 |\n|---|---|---|---|---|\n| conv_ucs_1x | 1× | 1.0098 | +0.0% | 0.001 |\n| conv_t04_1x | 1× | 0.3564 | +0.0% | 0.020 |\n| conv_ucs_2x | 2× | 0.8559 | -15.2% | 9.75e-04 |\n| conv_t04_2x | 2× | 0.3557 | -0.2% | 0.020 |\n| conv_ucs_4x | 4× | 0.6728 | -33.4% | 7.49e-04 |\n| conv_t04_4x | 4× | 0.3832 | +7.5% | 0.011 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "表头 + 分隔行 + 6 行；UCS 随加密持续下降（未收敛），属上游 honest 记录"
        },
        {
          "asset_id": "A22",
          "asset_class": "table",
          "label": "AC5 巴西圆盘中心应力比表（3 分辨率 × 3 平均区 = 9 配置）",
          "in_report_section": "### 3.5 巴西圆盘中心应力场（AC5）",
          "locator": {
            "method": "char_span",
            "start_char": 7929,
            "end_char": 8407,
            "start_line": 162,
            "end_line": 172,
            "quote": "| 点阵 n_lattice | 层数 | 平均区半径/D | 区内颗粒数 | 峰值主应力比 | 相对 −3.0 偏差 | 有限读数 |\n|---|---|---|---|---|---|---|\n| 7 | 4 | 0.12 | 2 | -3.481 | 16.0% | 6 |\n| 7 | 4 | 0.20 | 10 | -4.180 | 39.3% | 7 |\n| 7 | 4 | 0.30 | 44 | nan | inf% | 0 |\n| 9 | 4 | 0.12 | 2 | -2.705 | 9.8% | 4 |\n| 9 | 4 | 0.20 | 20 | -6.906 | 130.2% | 4 |\n| 9 | 4 | 0.30 | 84 | nan | inf% | 0 |\n| 13 | 4 | 0.12 | 20 | -9.155 | 205.2% | 2 |\n| 13 | 4 | 0.20 | 68 | -26.642 | 788.1% | 3 |\n| 13 | 4 | 0.30 | 164 | nan | inf% | 0 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "含 3 个 nan/inf 配置（平均区 0.30）与跨配置偏差 10–788%"
        },
        {
          "asset_id": "A23",
          "asset_class": "verdict",
          "label": "AC5 判定：中心区 PASS + 跨配置稳健性 FAIL 的如实记录",
          "in_report_section": "### 3.5 巴西圆盘中心应力场（AC5）",
          "locator": {
            "method": "char_span",
            "start_char": 8409,
            "end_char": 8610,
            "start_line": 174,
            "end_line": 174,
            "quote": "判定：PASS（容差 15%，按**中心区**读数判定）；但跨 9 个（分辨率 × 区域）配置的偏差范围 10–788%，**稳健性 FAIL**：结论只在最细粒度的中心区（2–20 个颗粒）成立，区域一放大就偏离，因此这一条按“配置相关”如实记录，不当成普适收敛结论。表中“有限读数”指中心区确实出现横向**拉**主应力（σ_max > 0）的读数个数——多数配置一个都没有，详见 §5 的物理诊断。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "同一行同时给出 PASS 与稳健性 FAIL，保留上游不确定性表述"
        },
        {
          "asset_id": "A24",
          "asset_class": "statement_set",
          "label": "AC6 负控分位与 AC7 复现性/准静态门结果（含 FAIL 标记）",
          "in_report_section": "### 3.6 负控与复现（AC6 / AC7）",
          "locator": {
            "method": "char_span",
            "start_char": 8638,
            "end_char": 8852,
            "start_line": 178,
            "end_line": 179,
            "quote": "- **AC6**：200 组随机 θ 的 UCS 分位 min 0.295 / q05 0.644 / 中位 2.546 / q95 6.224 / max 7.837 MPa；落在文献带外的比例 83.5% → FAIL\n- **AC7**：两次独立进程 UCS = 1.01e+06 / 1.01e+06 Pa，相对差 0.000（门 1e-3）；全部设计点运行的最大 KE/外功 0.022（门 0.001）→ FAIL",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "两条 bullet：AC6 违反比例 83.5%（FAIL）、AC7 相对差 0.000 / KE 0.022（FAIL）"
        },
        {
          "asset_id": "A25",
          "asset_class": "figure_declaration",
          "label": "§3.7 六张图件的 markdown 引用与图注（图 1–图 6）",
          "in_report_section": "### 3.6 负控与复现（AC6 / AC7）",
          "locator": {
            "method": "char_span",
            "start_char": 8854,
            "end_char": 9673,
            "start_line": 181,
            "end_line": 205,
            "quote": "### 3.7 图\n\n![response surface](figures/p270w2c_n08/fig_response_surface.png)\n\n*图 1* 响应面切片（每列一个参数、每行一个响应；绿色带 = 验收目标带）。UCS 随 k_b、ε_b 单调上升（键强度乘积主导），而 σc/σt 与 m 的分散度大得多——这正是 §3.2 相关矩阵里高相关的来源。\n\n![identifiability](figures/p270w2c_n08/fig_jacobian.png)\n\n*图 2* 左：量纲一化 Jacobian；中：参数相关矩阵；右：Brun collinearity（对数轴，虚线为 γ = 100 阈值）。\n\n![pareto](figures/p270w2c_n08/fig_pareto.png)\n\n*图 3* 代理面上的 NSGA-II 种群与 Pareto 前沿（三目标两两投影）。越界量 0 表示该目标满足；前沿上找不到三目标同时为 0 的个体，即构成 (c) 分支（三目标不可同时满足）的证据。\n\n![size effect](figures/p270w2c_n08/fig_size_effect.png)\n\n*图 4* 左：参考 θ 的 Weibull 尺寸效应族与幂律拟合（虚线为留出厚度）；右：留出厚度外推误差。\n\n![brazilian](figures/p270w2c_n08/fig_brazilian.png)\n\n*图 5* 左：圆盘中心主应力比 vs 平均区半径（三种点阵分辨率）与 Hondros −3.0 容差带；右：比值的读数历史及 σ_x/|σ_z| 对照。\n\n![ucs](figures/p270w2c_n08/fig_ucs.png)\n\n*图 6* 左：参考 θ 的单轴压缩应力–应变迹（hold 末读数）；右：AC6 负控 200 组随机 θ 的 UCS 分布。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "图件声明在源内可解析；图件二进制本体见 A26（平台 payload 未内嵌 png）"
        },
        {
          "asset_id": "A26",
          "asset_class": "figure_binary_set",
          "label": "六张 png 图件本体（figures/p270w2c_n08/*.png：响应面/Jacobian/Pareto/尺寸效应/巴西/UCS）",
          "in_report_section": "### 3.7 图",
          "locator": {
            "method": "char_span",
            "start_char": 8865,
            "end_char": 8930,
            "start_line": 183,
            "end_line": 183,
            "quote": "![response surface](figures/p270w2c_n08/fig_response_surface.png)",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform_figures_field + worktree_path_exists",
            "result": "unresolved",
            "platform_figures_declared": 6,
            "declared_names": [
              "fig_response_surface.png",
              "fig_jacobian.png",
              "fig_pareto.png",
              "fig_size_effect.png",
              "fig_brazilian.png",
              "fig_ucs.png"
            ],
            "png_base64_present": false,
            "worktree_path": "figures/p270w2c_n08",
            "worktree_path_exists": false,
            "detail": "声明存在（name/caption）但二进制不可取；相对路径在本工作树不存在"
          },
          "note": "报告只给仓库相对路径，平台 figures 字段有 name/caption 但无图件二进制，本工作树（TensorKnowledge）内不存在该路径 → 不可解析"
        },
        {
          "asset_id": "A27",
          "asset_class": "limitation_set",
          "label": "§4 条 1 / 1b：宽矩阵条件数假象 + 运动学驱动瞬态撕裂（最大坑）",
          "in_report_section": "## 4. 注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 9704,
            "end_char": 10352,
            "start_line": 209,
            "end_line": 210,
            "quote": "1. **宽矩阵的条件数是“假朋友”**。3 响应 × 6 参数时 cond(J) 只由三个非零奇异值构成，两列完全相同也不会让 cond 变大（本节点用相同列做负控实测仍是 2.39）。真正的不可辨识证据是collinearity index、相关矩阵与结构零空间——这条是测试先失败后修正的（见 §6）。\n1b. **运动学驱动的瞬态撕裂（本节点最大的一坑）**。试件只有顶层被驱动，一次 ramp 的位移``eps_inc × gauge`` 在试件跟上之前全部压在**最外层键**上；对长试件（t = 0.8 m，32 个键层）该瞬态达到 2.4 mm，是最外层键断裂伸长（0.375 mm）的 6.4 倍，顶层键层在 ramp 内直接撕开，读数载荷**恰为 0**——首轮战役因此把 t = 0.4/0.8 m 的强度全算成 0（29/132 与 99/99 个 0 值），整轮任务作废。真正的修正不是把 ramp 拉长（那只降速率、不减单次位移），而是**让增量数随键层数自适应**：increments ≥ target_strain·(n_layers−1)/(safety·ε_b)（`adapt_protocol`，safety=0.75），并把它固化成 `protocol_prior_check`（AC1 子项 + 3 个 pytest 用例）。三轮回炉记录留档 `runs/p270w2c_n08/v{1,2,3}_protocol_superseded/` 以备审计。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "1b 记录首轮战役 t=0.4/0.8 m 强度全为 0、整轮作废，与自适应增量修正"
        },
        {
          "asset_id": "A28",
          "asset_class": "limitation_set",
          "label": "§4 条 2–4：σ_t 观测面口径 / 尺寸效应 −1/m 与 legacy −2/m 偏差 / m 参照只能是键级输入",
          "in_report_section": "## 4. 注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 10354,
            "end_char": 10897,
            "start_line": 212,
            "end_line": 214,
            "quote": "2. **σ_t 的观测面选择**。巴西劈裂在本文点阵上不能当强度 oracle（§5），因此三目标里的 σ_t 取**单轴直接拉伸**（尺寸效应族最薄拟合厚度 t = 0.1 m 的均值）；这与文献 σc/σt 的定义同口径，也避免把圆盘解析式误差带进标定。\n3. **尺寸效应指数口径（显式偏差声明）**。体积随 t 线性变化（截面固定），Weibull 最弱环给出 σ_t ∝ t^(−1/m)；而 legacy `bpm_calibration`/`bpm_identifiability` 用的是 t^(−2/m)（表面缺陷族 / 圆盘厚度梯度口径）。沿用 −2/m 会把 m 系统性放大一倍，因此本节点改用 −1/m 并在报告里显式声明该偏差。\n4. **m 的参照值只能是键级输入，不是实验值**。AC3 的 m 目标用引擎**实际给定的键级 Weibull 模量 m_bond = 6**（模型输入，非循环）核对宏观 m 的 95% CI 是否覆盖它；参考 θ 同管线测得的 m 只作为“同管线可复现性”的次要参照。本合成键模型没有实验宏观 m，因此这一条**不等于**与实验对标，且实测宏观 m ≈ 263（CI 宽达数百）说明宏观 m 与键级 m 之间没有稳定映射。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "三条口径与偏差声明"
        },
        {
          "asset_id": "A29",
          "asset_class": "limitation_set",
          "label": "§4 条 4b：UCS 对加载增量敏感（1.01 → 0.86 → 0.67 MPa 未收敛）",
          "in_report_section": "## 4. 注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 10898,
            "end_char": 11123,
            "start_line": 215,
            "end_line": 215,
            "quote": "4b. **强度对加载增量敏感（UCS）**。协议细化表（§3.4b）显示：增量加密 1×→2×→4× 时，UCS 由 1.01 → 0.86 → 0.67 MPa 持续下降（未收敛），而 t=0.4 m 拉伸强度在 0.356/0.356/0.383 MPa 之间（±7%，已收敛）。因此：**σ_t 与 m 链路可信，UCS 的绝对值只能是相对量**；好在本节点的 UCS 结论是“远低于文献带”且细化使其更低，方向鲁棒——不可行结论不依赖协议。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "单条局限；给出绝对强度不可用的适用范围"
        },
        {
          "asset_id": "A30",
          "asset_class": "limitation_set",
          "label": "§4 条 5：Love–Weber 应力张量缺切向/摩擦接触力（virial 与 P/(Dt) 差 1.4–2.6 倍）",
          "in_report_section": "## 4. 注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 11125,
            "end_char": 11264,
            "start_line": 217,
            "end_line": 217,
            "quote": "5. **应力张量缺切向/摩擦接触力**。Love–Weber 求和只含键轴向力与破坏后接触法向力；准静态 hold 末切向力小且判据用主应力比（共同因子部分抵消），但破坏后长程接触缺失使绝对量偏低（整盘 virial 与 P/(Dt) 差 1.4–2.6 倍，已记入 §5）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "单条局限"
        },
        {
          "asset_id": "A31",
          "asset_class": "limitation_set",
          "label": "§4 条 5b：准静态门（KE/外功 ≤1e-3）在拉伸试件上不达标",
          "in_report_section": "## 4. 注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 11265,
            "end_char": 11463,
            "start_line": 218,
            "end_line": 218,
            "quote": "5b. **准静态门（KE/外功 ≤1e-3）在拉伸试件上不达标**。带断裂的试件在峰值前已出现局部键断裂，碎片动能进入读数，全运行最大 KE/外功 0.022（UCS 试件 ~1e-3 量级达标）。把窗口取到峰值为止已排除“碎屑弹道”部分，但残余振动仍超门——因此 AC7 的准静态门按纪律记 FAIL；可行的补强是更长的 hold（60 步已是 4 个阻尼长度）或粘性人工阻尼，未在本波实现。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "单条局限；给出未实现的补强方向"
        },
        {
          "asset_id": "A32",
          "asset_class": "limitation_set",
          "label": "§4 条 6–8：点阵各向异性 / Pareto 来自代理 / 适用范围声明",
          "in_report_section": "## 4. 注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 11465,
            "end_char": 11778,
            "start_line": 220,
            "end_line": 222,
            "quote": "6. **简单立方点阵的各向异性**。沿加载轴存在直链，载荷偏向单链传递，中心横向拉应力远小于连续介质解——这是 AC5 honest FAIL 的物理根因，也是“单格点 vs 中心区平均”这条 AC 想暴露问题的更强版本：**即便做了区域平均也不收敛**。\n7. **Pareto 前沿来自代理**。NSGA-II 在二次代理上跑，前沿个体未逐个回代 DEM，因此 (c) 分支的结论按“代理面 + 设计点实证”双证据陈述，不做单点强断言。\n8. **适用范围**：单轴/巴西试件的准静态强度标定（-10 ℃ 淡水冰量级、ε̇ ≲ 1e-3 s⁻¹）。粘弹性（Maxwell–Wiechert 键）与蠕变损伤未在本节点开启。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "三条局限与适用范围（-10 ℃ 淡水冰量级、ε̇ ≲ 1e-3 s⁻¹）"
        },
        {
          "asset_id": "A33",
          "asset_class": "table",
          "label": "§5 误差判定表（7 个关键量 vs 基准，逐项 <3%?）",
          "in_report_section": "## 5. 误差判定（关键量 vs 基准，逐项）",
          "locator": {
            "method": "char_span",
            "start_char": 11806,
            "end_char": 12237,
            "start_line": 226,
            "end_line": 234,
            "quote": "| 关键量 | 基准 | 实测误差 | 是否 < 3% |\n|---|---|---|---|\n| 复现性 UCS | 同 θ 独立进程重跑 | 0.000 | 是（远小于门 1e-3）|\n| 准静态门 KE/外功 | 1e-3 | 0.022（全运行最大；UCS 试件 ~1e-3）| 否（超门 22 倍，AC7 记 FAIL）|\n| 尺寸效应幂律（留出 t=0.05）| DEM 实测 | -5.4% | 否 |\n| 尺寸效应幂律（留出 t=0.80）| DEM 实测 | +2.6% | 是 |\n| 巴西中心主应力比 | Hondros −3.0（解析）| 最优 -2.705（相对 9.8%）| 否（差两个量级，honest FAIL）|\n| 整盘 virial vs P/(Dt) | 施加载荷 | 见 §4 条 5（1.4–2.6 倍）| 否 |\n| UCS 落带 | [5, 15] MPa | 参考 θ 1.010 MPa | 否（不在带内） |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "表头 + 分隔行 + 7 个关键量行"
        },
        {
          "asset_id": "A34",
          "asset_class": "statement",
          "label": "§5 「是否 <3%」显式回答（含 honest FAIL 声明）",
          "in_report_section": "## 5. 误差判定（关键量 vs 基准，逐项）",
          "locator": {
            "method": "char_span",
            "start_char": 12239,
            "end_char": 12440,
            "start_line": 236,
            "end_line": 236,
            "quote": "**“是否 < 3%”的显式回答**：数值可复现性与准静态门 = **是**；尺寸效应拟合的内插自洽 = 见上表两项（留出端误差以数字给出，不在 3% 内即如实写否）；巴西中心应力比 = **否**，且不是 3% 量级的问题，而是定性不符（中心横向拉应力缺失/被压），按纪律记 honest FAIL，不做粉饰。UCS 的“真值”没有单点实验值可对，只有文献带，因此以是否落带陈述，不编造 3% 结论。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "单段结论；明确巴西中心应力比不是 3% 量级问题而是定性不符"
        },
        {
          "asset_id": "A35",
          "asset_class": "test_record",
          "label": "§6 测试与验收：42 项 pytest + 复现命令 + 审计链",
          "in_report_section": "## 6. 测试与验收",
          "locator": {
            "method": "char_span",
            "start_char": 12455,
            "end_char": 13137,
            "start_line": 240,
            "end_line": 243,
            "quote": "- `tests/test_bpm_calibration_feasibility.py`（42 项，全绿）：AC1 几何先验 3 例（含 2 个负控）；θ 往返/投影/非法值 5 例；AC2 Jacobian 与可辨识性 7 例（含“相同列”与“近零奇异值”两个负控，以及 non-finite 输入）；代理与 NSGA-II 3 例；尺寸效应与 AC4 4 例（含幂律被破坏的负控）；AC3 三分支 4 例；AC5 应力场符号/对称性/主应力比/空区域/圆盘夹持 6 例；AC6/AC7 3 例（弱键 UCS 掉出文献带、两次运行复现 + KE 门）；另有加载协议自适应 3 例。运行结果：42 passed。\n- 运行：`PYTHONPATH=src python -m pytest tests/test_bpm_calibration_feasibility.py -q`\n- 战役复现：`python scripts/p270w2c_n08_feasibility.py --stage sample --workers 40` → `--stage analyze` → `python scripts/p270w2c_n08_figures.py` → `python scripts/p270w2c_n08_report.py`\n- 审计链：逐任务原始记录 `runs/p270w2c_n08/records.jsonl` → 判据/数字 `artifacts/p270w2c_n08/report.json` → 本报告（数字全部程序化注入）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "md[start_char:end_char] == quote 且该 quote 在全文唯一"
          },
          "note": "测试计数与复现命令原文；测试代码本体为外部资产 A38"
        },
        {
          "asset_id": "A36",
          "asset_class": "code_reference",
          "label": "新增模块 src/tensordem/bpm_calibration_feasibility.py",
          "in_report_section": "# BPM 微观参数三目标联合标定：可行性判定与可辨识性审计",
          "locator": {
            "method": "char_span",
            "start_char": 104,
            "end_char": 159,
            "start_line": 3,
            "end_line": 3,
            "quote": "**新增模块** `src/tensordem/bpm_calibration_feasibility.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists + report_url_doi_scan",
            "result": "unresolved",
            "reported_paths": [
              "src/tensordem/bpm_calibration_feasibility.py"
            ],
            "worktree_path_exists": {
              "src/tensordem/bpm_calibration_feasibility.py": false
            },
            "external_addresses_found": [],
            "detail": "报告只给仓库相对路径，本工作树（TensorKnowledge）不存在，且无 URL/DOI"
          },
          "note": "TensorDEM 仓内相对路径；本工作树（TensorKnowledge）不存在，报告未给 URL/DOI"
        },
        {
          "asset_id": "A37",
          "asset_class": "code_reference",
          "label": "战役脚本 scripts/p270w2c_n08_feasibility.py（sample/analyze）+ 图/报告渲染脚本",
          "in_report_section": "# BPM 微观参数三目标联合标定：可行性判定与可辨识性审计",
          "locator": {
            "method": "char_span",
            "start_char": 162,
            "end_char": 207,
            "start_line": 3,
            "end_line": 3,
            "quote": "**战役脚本** `scripts/p270w2c_n08_feasibility.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists + report_url_doi_scan",
            "result": "unresolved",
            "reported_paths": [
              "scripts/p270w2c_n08_feasibility.py"
            ],
            "worktree_path_exists": {
              "scripts/p270w2c_n08_feasibility.py": false
            },
            "external_addresses_found": [],
            "detail": "报告只给仓库相对路径，本工作树（TensorKnowledge）不存在，且无 URL/DOI"
          },
          "note": "外部仓相对路径，本工作树不可解析"
        },
        {
          "asset_id": "A38",
          "asset_class": "code_reference",
          "label": "测试文件 tests/test_bpm_calibration_feasibility.py（42 项）",
          "in_report_section": "## 6. 测试与验收",
          "locator": {
            "method": "char_span",
            "start_char": 12763,
            "end_char": 12846,
            "start_line": 241,
            "end_line": 241,
            "quote": "- 运行：`PYTHONPATH=src python -m pytest tests/test_bpm_calibration_feasibility.py -q`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists + report_url_doi_scan",
            "result": "unresolved",
            "reported_paths": [
              "tests/test_bpm_calibration_feasibility.py"
            ],
            "worktree_path_exists": {
              "tests/test_bpm_calibration_feasibility.py": false
            },
            "external_addresses_found": [],
            "detail": "仅登记报告内给出的相对路径；本工作树不存在，报告无 URL/DOI 可解析"
          },
          "note": "外部仓相对路径，本工作树不可解析"
        },
        {
          "asset_id": "A39",
          "asset_class": "dataset",
          "label": "原始数据 runs/p270w2c_n08/records.jsonl（逐任务记录）",
          "in_report_section": "# BPM 微观参数三目标联合标定：可行性判定与可辨识性审计",
          "locator": {
            "method": "char_span",
            "start_char": 303,
            "end_char": 344,
            "start_line": 4,
            "end_line": 4,
            "quote": "**原始数据** `runs/p270w2c_n08/records.jsonl`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists + report_url_doi_scan",
            "result": "unresolved",
            "reported_paths": [
              "runs/p270w2c_n08/records.jsonl"
            ],
            "worktree_path_exists": {
              "runs/p270w2c_n08/records.jsonl": false
            },
            "external_addresses_found": [],
            "detail": "报告只给仓库相对路径，本工作树（TensorKnowledge）不存在，且无 URL/DOI"
          },
          "note": "外部仓运行产物，本工作树不可解析"
        },
        {
          "asset_id": "A40",
          "asset_class": "dataset",
          "label": "判据数字 artifacts/p270w2c_n08/report.json（报告的唯一数字来源）",
          "in_report_section": "# BPM 微观参数三目标联合标定：可行性判定与可辨识性审计",
          "locator": {
            "method": "char_span",
            "start_char": 353,
            "end_char": 397,
            "start_line": 4,
            "end_line": 4,
            "quote": "**判据数字** `artifacts/p270w2c_n08/report.json`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists + report_url_doi_scan",
            "result": "unresolved",
            "reported_paths": [
              "artifacts/p270w2c_n08/report.json"
            ],
            "worktree_path_exists": {
              "artifacts/p270w2c_n08/report.json": false
            },
            "external_addresses_found": [],
            "detail": "报告只给仓库相对路径，本工作树（TensorKnowledge）不存在，且无 URL/DOI"
          },
          "note": "外部仓工件，本工作树不可解析"
        },
        {
          "asset_id": "A41",
          "asset_class": "audit_archive",
          "label": "runs/p270w2c_n08/v{1,2,3}_protocol_superseded/（三轮回炉记录）",
          "in_report_section": "## 4. 注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 9859,
            "end_char": 10352,
            "start_line": 210,
            "end_line": 210,
            "quote": "1b. **运动学驱动的瞬态撕裂（本节点最大的一坑）**。试件只有顶层被驱动，一次 ramp 的位移``eps_inc × gauge`` 在试件跟上之前全部压在**最外层键**上；对长试件（t = 0.8 m，32 个键层）该瞬态达到 2.4 mm，是最外层键断裂伸长（0.375 mm）的 6.4 倍，顶层键层在 ramp 内直接撕开，读数载荷**恰为 0**——首轮战役因此把 t = 0.4/0.8 m 的强度全算成 0（29/132 与 99/99 个 0 值），整轮任务作废。真正的修正不是把 ramp 拉长（那只降速率、不减单次位移），而是**让增量数随键层数自适应**：increments ≥ target_strain·(n_layers−1)/(safety·ε_b)（`adapt_protocol`，safety=0.75），并把它固化成 `protocol_prior_check`（AC1 子项 + 3 个 pytest 用例）。三轮回炉记录留档 `runs/p270w2c_n08/v{1,2,3}_protocol_superseded/` 以备审计。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists + report_url_doi_scan",
            "result": "unresolved",
            "reported_paths": [
              "runs/p270w2c_n08/v{1,2,3}_protocol_superseded/"
            ],
            "worktree_path_exists": {
              "runs/p270w2c_n08/v{1,2,3}_protocol_superseded/": false
            },
            "external_addresses_found": [],
            "detail": "仅登记报告内给出的相对路径；本工作树不存在，报告无 URL/DOI 可解析"
          },
          "note": "外部仓审计留档目录，本工作树不可解析"
        },
        {
          "asset_id": "A42",
          "asset_class": "code_reference",
          "label": "legacy 模块 bpm_calibration / bpm_identifiability（t^(−2/m) 口径）",
          "in_report_section": "## 4. 注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 10557,
            "end_char": 10603,
            "start_line": 213,
            "end_line": 213,
            "quote": "legacy `bpm_calibration`/`bpm_identifiability`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "report_url_doi_path_scan",
            "result": "unresolved",
            "reported_paths": [],
            "external_addresses_found": [],
            "detail": "报告内无可解析路径/URL（仅模块名或引文），不猜测地址"
          },
          "note": "外部仓模块名，报告未给路径，本工作树不可解析"
        }
      ],
      "claims": [],
      "claims_note": "按工作包契约 objective.classify_report_type=false 且 delivery.notes 允许 claims 为空数组：本工序只登记资产与定位，不做 claim 抽取、不作报告类型分类；claim 抽取与 verification 由下游工序/平台门负责。",
      "integrity": {
        "quote_uniqueness": "每个 quote 在源 markdown 中出现次数 == 1（scripts/kf_wp11924_01_verify.py 复验）",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "quotes_sliced_not_retyped": true,
        "verification_status": "not_verified"
      }
    }
  },
  "claims": []
}
```
