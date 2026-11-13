# KF-RESULT wp-13612-01

工序 01-asset-registration ｜ report_id=13612 ｜ lane=C ｜ 状态 draft ｜ 产出物 `docs/kf/wp-13612-01/asset_manifest.json`

> 本单只做登记，不做抽取、不做分类、不给任何结论盖 verified。源报告的全部判据状态原样保留（含其 self-declared FAIL）。

## ① 本工序做了什么

1. **钉住源**：取 report 13612 的 `markdown` 字段（source_uri=`tensor://reports/13612`），对 UTF-8 字节重算 sha256 = `85bbae874e9babb342a5d216c19e00265dcc108115d6dcb53f1991af48846888`，与工作包契约 `source_hash` 逐字相等；字符数 5526（契约 `chars`=5526，相等），UTF-8 字节 9350。字节级快照落盘 `docs/kf/wp-13612-01/source/report_13612.md`，离线可复核。
2. **登记资产** 38 条（resolved_in_source 33 / referenced_unresolved 5 / declared_absent 0），每条带一个**唯一**的逐字定位符（char span + 行号区间 + 原文引文），共校验引文 46 条。
3. **探测可解析附件**：逐个 GET `/tensor/reports/13612/figures/{name}`，5 张图全部 HTTP 200 且 PNG 魔数正确，逐张记 sha256、字节数并落本地副本（不重绘、不替换）。
4. **登记未解析项**：上游工件/源码/测试路径均为仓库相对路径且摘要被截断（16/12 hex），报告内亦无 repo/branch/commit/run id，故登记为 referenced_unresolved 并写明不可核验原因。
5. **不做**：未抽取任何 claim（`claims: []`，契约明示允许）、未做报告分类、未标 verified、未改写上游或其它工作包产物。

## ② 怎么做的（步骤/工具/关键设置）

| 步骤 | 做法 | 工具/命令 |
|---|---|---|
| 取源 | `${TENSOR_API_BASE}/tensor/reports/13612`（Bearer=登录 token） | `scripts/kf_wp13612_01_asset_manifest.py --fetch` |
| 取图 | 逐名 GET figures 端点，落 `figures/*.png` + sha256/bytes/http_status | `... --fetch-figures` |
| 建清单 | 声明式资产表 → 每条引文定位（`md.find` 唯一性断言，非唯一即抛错） | `... `（默认 build） |
| 自验 | 重算哈希、逐条 span 回读、id 唯一、信封 schema、图 payload 重算 | `... --verify` |
| 测试 | pytest 16 项，只读断言（不联网、不改工作树） | `pytest tests/test_kf_wp13612_01_asset_registration.py -q` |

关键设置：

- 引文唯一性用 `md.count(quote) == 1` 硬断言——重复引文直接使构建失败，不靠人工目检。
- 定位符用**字符区间**而非行号为主（行号仅作可读辅助），因为表格行含 `|` 且中文标点密集，行内切片易错位。
- 图名↔中文图注的 5↔5 配对属**按序/语义**推断（markdown 只集体点名，未给文件名），故每张图的权威绑定是其 payload sha256，不是名字映射（见 ⑤-3）。
- 信封按 `schemas/kf_result.v1.schema.json`（draft 2020-12）校验；清单自身不新增 schema 文件、不改动上游 `schemas/` 任何文件。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 | 字节 | sha256（前 16） |
|---|---|---|---|
| `docs/kf/wp-13612-01/asset_manifest.json` | 38 条资产 + 4 条登记观察，claims=[] | 33696 | `20fd1e86be28d448` |
| `docs/kf/wp-13612-01/kf_result.json` | kf_result.v1 信封（outputs.asset_manifest.json 与磁盘清单逐字节相等） | 36202 | `a70332d0b4fda428` |
| `docs/kf/wp-13612-01/selfcheck.json` | 派生产物：verify 的逐项机器自检结果 | 889 | `3181971b9da8ee74` |
| `docs/kf/wp-13612-01/source/report_13612.md` | 源 markdown 字节级快照（离线复算用） | 9350 | `85bbae874e9babb3` |
| `docs/kf/wp-13612-01/source_meta.json` | 平台记录字段快照（title/scenario_key/tags/figures） | 1084 | `5cce1426b2590a33` |
| `docs/kf/wp-13612-01/figure_fetch.json` | 5 图 HTTP 状态 + bytes + sha256 | 2351 | `79af4c96d1ac4acc` |
| `scripts/kf_wp13612_01_asset_manifest.py` | 取源/建清单/自验三合一生成器 | 38831 | `f9846ba3cd4fb064` |
| `scripts/kf_wp13612_01_report.py` | 本报告正文合成器（数字/引文程序化注入） | 14943 | `08825145f00d8afc` |
| `scripts/kf_wp13612_01_publish.py` | 发布到平台（唯一结果信道） | 3143 | `69bd9f3588b3d41d` |
| `tests/test_kf_wp13612_01_asset_registration.py` | 16 项只读验收测试 | 7492 | `3cd18f4e42ae9f9a` |

图副本（5 个 PNG，非重绘，payload sha256 逐张可复算）：

| 图名 | 中文图注（来自 record `figures`） | http | bytes | payload sha256 |
|---|---|---|---|---|
| `fig1_parity.png` | 预测-真值一致性（测试集 vs 外推集，含误差带） | 200 | 179072 | `5d0b8be9e2674d017c6ac5274f5da5a5…` |
| `fig2_error_vs_condition.png` | 外推域相对误差随 Fr / 浪向 β 的分布 | 200 | 239751 | `d4e9729f01cdf1fd60eca3cb2f3063d0…` |
| `fig3_uncertainty.png` | 外推域 conformal 区间覆盖与各目标覆盖率 | 200 | 54742 | `98c9baa7582d71b9be1864d5d7e89886…` |
| `fig4_fields.png` | 内部场：几何输入 → 阻力密度场 → 散度残差 | 200 | 59688 | `d4f27c4246323bdf5b0b59ee97a122ac…` |
| `fig5_training.png` | 集成成员训练曲线（数据+物理损失） | 200 | 74894 | `ad044f9d1c0806b52ef3632e87c6e077…` |

## ④ 证据定位表（claim/字段 → 原文引文片段）

定位符格式：`字符区间 [start,end) ｜ 行 start_line–end_line`；引文一律逐字，由脚本对源 markdown 做 `md[start:end] == quote` 与唯一性双重复核（verify 全绿）。本工序不产出 claim，故表内为**资产 → 原文定位**而非 claim→引文。

- **A01** `report_document`（document，resolution=resolved_in_source）— 字符 [0,40) ｜ 行 1–1 ｜ 原文：
  > # 物理信息神经算子（FNO）船体阻力/耐波实时代理模型（P284W3-N09）
  核验：sha256(markdown utf8) vs contract source_hash → **resolved**
  备注：document-level locator = [0, len(markdown)); quote is the title line (unique)
- **A02** `section`（§1，resolution=resolved_in_source）— 字符 [42,52) ｜ 行 3–3 ｜ 原文：
  > ## 1. 案例介绍
  核验：heading present verbatim → **resolved**
  备注：section heading
- **A03** `section`（§2，resolution=resolved_in_source）— 字符 [1513,1521) ｜ 行 41–41 ｜ 原文：
  > ## 2. 方法
  核验：heading present verbatim → **resolved**
  备注：section heading
- **A04** `section`（§3，resolution=resolved_in_source）— 字符 [2542,2552) ｜ 行 72–72 ｜ 原文：
  > ## 3. 计算结果
  核验：heading present verbatim → **resolved**
  备注：section heading
- **A05** `section`（§4，resolution=resolved_in_source）— 字符 [4359,4368) ｜ 行 115–115 ｜ 原文：
  > ## 4. 结果图
  核验：heading present verbatim → **resolved**
  备注：section heading
- **A06** `section`（§5，resolution=resolved_in_source）— 字符 [4417,4429) ｜ 行 119–119 ｜ 原文：
  > ## 5. 注意点与局限
  核验：heading present verbatim → **resolved**
  备注：section heading
- **A07** `section`（§6，resolution=resolved_in_source）— 字符 [5097,5116) ｜ 行 136–136 ｜ 原文：
  > ## 6. 误差判定（逐项，显式回答）
  核验：heading present verbatim → **resolved**
  备注：section heading
- **A08** `artifact_path`（§1.2，resolution=referenced_unresolved）— 字符 [691,764) ｜ 行 19–19 ｜ 原文：
  > 数据集：`artifacts/p284w3_n09_fno/dataset.npz`（sha256 `a778060b577942ed`），训练域
  核验：worktree lookup of repo-relative path + digest length check → **unresolved**
  备注：path is relative to the producing repo (not named in the report); digest is a 16-hex prefix so the payload cannot be hash-pinned from this record. Not copied, not re-generated.
- **A09** `code_path`（§1.2，resolution=referenced_unresolved）— 字符 [365,424) ｜ 行 16–16 ｜ 原文：
  > | `C_T, R_T` | `backend/api/domain/resistance_holtrop.py` |
  核验：worktree lookup of repo-relative path + digest length check → **unresolved**
  备注：12-hex prefix only; no repo/commit identity in the report
- **A10** `code_path`（§1.2，resolution=referenced_unresolved）— 字符 [517,573) ｜ 行 17–17 ｜ 原文：
  > | `RAO_φ, RAO_z` | `backend/api/seakeeping_physics.py` |
  核验：worktree lookup of repo-relative path + digest length check → **unresolved**
  备注：12-hex prefix only; no repo/commit identity in the report
- **A11** `code_path`（§2.1，resolution=referenced_unresolved）— 字符 [1534,1606) ｜ 行 44–44 ｜ 原文：
  > FNO（`src/neural_operators/field_operator.py`）：lift → ×4（SpectralConv2d +
  核验：worktree lookup of repo-relative path → **unresolved**
  备注：no digest and no commit identity inside report 13612
- **A12** `test_path`（§5 item 1，resolution=referenced_unresolved）— 字符 [4575,4632) ｜ 行 124–124 ｜ 原文：
  > 回归防护：`test_input_tensor_channels_and_mask` + 数据集清单登记特征定义。
  核验：test-name lookup inside this worktree → **unresolved**
  备注：test name only: no file path, no suite/commit identity
- **A13** `table`（§1.2，resolution=resolved_in_source）— 字符 [305,346) ｜ 行 14–14 ｜ 原文：
  > | 标签 | 内核 | 方法与证据等级 | 源码 sha256（前 12 位） |
  核验：table header present verbatim → **resolved**
  备注：4 columns, 2 data rows (C_T/R_T and RAO_z/RAO_φ)
- **A14** `table`（§1.3，resolution=resolved_in_source）— 字符 [958,1011) ｜ 行 28–28 ｜ 原文：
  > | L | 60–320 m（对数均匀） | Fr | 0.08–0.40（外推 0.40–0.55） |
  核验：table row present verbatim → **resolved**
  备注：sampled ranges incl. extrapolation ranges
- **A15** `operator_input_spec`（§1.4，resolution=resolved_in_source）— 字符 [1208,1265) ｜ 行 35–35 ｜ 原文：
  > 输入场 `u(x,z)`（24 通道，网格 16×4）：逐站剖面面积比 `A(x)/(B·T)`、淹没掩膜、半宽比
  核验：spec sentence present verbatim → **resolved**
  备注：names the field channels; the remaining channels continue on the next lines
- **A16** `gate_predicate`（§1.2，resolution=resolved_in_source）— 字符 [861,893) ｜ 行 22–22 ｜ 原文：
  > `3.3e-16`（浮力守恒），Cb·L·B·T 与排水量自洽。
  核验：sentence present verbatim → **resolved**
  备注：the report's own geometry-verification evidence (∫(A/(B·T))dx = Cb); not re-run here
- **A17** `physics_constraint_spec`（§2.2，resolution=resolved_in_source）— 字符 [1932,1993) ｜ 行 55–55 ｜ 原文：
  > 3. 对称性：`RAO_φ ∝ |sin β|`（β=0/180° 恒为 0，float64 计算后残差 <1e-12）；
  核验：list item present verbatim → **resolved**
  备注：one of the four by-construction exact constraints
- **A18** `training_config`（§2.3，resolution=resolved_in_source）— 字符 [2265,2299) ｜ 行 64–64 ｜ 原文：
  > 60，**2 成员深度集成**（对数空间均值 + 成员标准差 σ）；
  核验：config sentence present verbatim → **resolved**
  备注：preceded by AdamW lr=0.006/wd=0.0001, cosine, batch 64, epochs 60
- **A19** `metric_definition`（§2.4，resolution=resolved_in_source）— 字符 [2416,2485) ｜ 行 69–69 ｜ 原文：
  > `mape_pct = mean |Δ|/max(|truth|, floor)×100`，`floor = 0.02 × 训练集中位数`
  核验：definition present verbatim → **resolved**
  备注：the report's error-yardstick declaration; every §3/§6 percentage depends on this floor
- **A20** `table`（§3.1，resolution=resolved_in_source）— 字符 [2704,2740) ｜ 行 80–80 ｜ 原文：
  > | (b) 测试集 R_T | <5% | 6.36% | FAIL |
  核验：table row present verbatim → **resolved**
  备注：criterion row carried with its FAIL verdict unchanged
- **A21** `table`（§3.1，resolution=resolved_in_source）— 字符 [2616,2652) ｜ 行 78–78 ｜ 原文：
  > | (a) 训练集 R_T | <3% | 4.49% | FAIL |
  核验：table row present verbatim → **resolved**
  备注：the only criterion naming a 3% threshold; registered so no downstream 工序 lifts it
- **A22** `table`（§3.1，resolution=resolved_in_source）— 字符 [2856,2917) ｜ 行 83–83 ｜ 原文：
  > | (d) 单点推理时延（CPU） | <10 ms | 中位 6.65 ms（p95 9.63 ms） | PASS |
  核验：table row present verbatim → **resolved**
  备注：one of the two PASS criteria (with (c), which the source itself downgrades)
- **A23** `table`（§3.2，resolution=resolved_in_source）— 字符 [3342,3433) ｜ 行 96–96 ｜ 原文：
  > | 外推集（Fr>0.4 或 β>60°） | 28.67% (28.68%) | 43191.09% (66933.87%) | 107215.54% (586642.06%) |
  核验：table row present verbatim → **resolved**
  备注：extrapolation errors of 1e4–1e5 % are the source's own numbers
- **A24** `table`（§3.3，resolution=resolved_in_source）— 字符 [3567,3640) ｜ 行 103–103 ｜ 原文：
  > | RAO_z | 18.70（55.7%） | 4553709.86（90.0%） | inf（inf=区间宽度不可度量，模型外推无信息量） |
  核验：table row present verbatim → **resolved**
  备注：records the q magnitudes that make criterion (c) a weak pass
- **A25** `table`（§3.3，resolution=resolved_in_source）— 字符 [3930,4002) ｜ 行 111–111 ｜ 原文：
  > | 1600 | 2.81e-02 / 8.01e-02 / 7.39e-02 | 13.5% | 54.5% | 55.6% | 3.44 |
  核验：table row present verbatim → **resolved**
  备注：control-experiment row (the n=640 row is the line above)
- **A26** `run_output_token`（§3.3，resolution=resolved_in_source）— 字符 [4051,4089) ｜ 行 113–113 ｜ 原文：
  > 标度 e∝n^(-0.30)；按此外推达 3.0% 需 ~233404 样本
  核验：token present verbatim → **resolved**
  备注：derived number quoted only; not recomputed by this package
- **A27** `run_output_token`（§2.3，resolution=resolved_in_source）— 字符 [2358,2395) ｜ 行 66–66 ｜ 原文：
  > 1302.0 s（本地 CPU，宿主机 load ≫ 核数，非最优算力）。
  核验：token present verbatim → **resolved**
  备注：no run id / log file referenced by the report
- **A28** `table`（§6，resolution=resolved_in_source）— 字符 [5234,5273) ｜ 行 141–141 ｜ 原文：
  > | R_T（测试集） | 同上 | <5% | 6.36% | **否** |
  核验：table row present verbatim → **resolved**
  备注：the source answers 否; this package stamps nothing as verified
- **A29** `self_declared_non_pass`（§6，resolution=resolved_in_source）— 字符 [5367,5427) ｜ 行 145–145 ｜ 原文：
  > **honest FAIL 声明**：判据 (a)(b) 的精度阈值本节点**未达成**，上述 FAIL 不做任何粉饰；
  核验：declaration present verbatim → **resolved**
  备注：carried verbatim so no downstream step lifts it to a pass
- **A30** `self_declared_non_pass`（§3.1，resolution=resolved_in_source）— 字符 [3058,3115) ｜ 行 88–88 ｜ 原文：
  > 因此 (c) 属**弱通过**：PICP 单独不足以证明外推可用，必须同时报告区间宽度（表中已列，量级 1e6）。
  核验：caveat present verbatim → **resolved**
  备注：the report downgrades its own PASS to weak; preserved
- **A31** `limitation_item`（§5 item 1，resolution=resolved_in_source）— 字符 [4431,4486) ｜ 行 121–121 ｜ 原文：
  > 1. **量纲错误（本节点踩到并修正）**：无因次频率必须是 `ω·√(L/g)`，不是 `ω/√(gL)`。
  核验：list item present verbatim → **resolved**
  备注：registered as a reusable trap; not re-verified here
- **A32** `limitation_item`（§5 item 3，resolution=resolved_in_source）— 字符 [4743,4796) ｜ 行 127–127 ｜ 原文：
  > 3. **插值极限（关键局限）**：输入为 ≥10 维无因次群，千级样本在 10 维空间里仍属稀疏——对照
  核验：list item present verbatim → **resolved**
  备注：basis of the 1e5–1e6 sample-count estimate
- **A33** `limitation_item`（§5 item 4，resolution=resolved_in_source）— 字符 [4923,4982) ｜ 行 131–131 ｜ 原文：
  > 4. **训练标签是回归/切片理论内核**（Holtrop ±5–10%；STF 2D 系数为解析近似），因此本代理的
  核验：list item present verbatim → **resolved**
  备注：no experimental benchmark was performed by the source node (its own words)
- **A34** `figure`（§4，resolution=resolved_in_source）— 字符 [4370,4415) ｜ 行 117–117 ｜ 原文：
  > 见 figures（内嵌 PNG）：parity、误差-工况、外推覆盖、内部场、训练曲线。
  核验：GET /tensor/reports/13612/figures/fig1_parity → http status + sha256(payload) → **resolved**；payload `sha256:5d0b8be9e2674d017…` (179072 B, http 200)
  备注：payload fetched and hashed by this package (binary not re-rendered); the markdown mention is the collective §4 sentence, hence the shared locator
- **A35** `figure`（§4，resolution=resolved_in_source）— 字符 [4370,4415) ｜ 行 117–117 ｜ 原文：
  > 见 figures（内嵌 PNG）：parity、误差-工况、外推覆盖、内部场、训练曲线。
  核验：GET /tensor/reports/13612/figures/fig2_error_vs_condition → http status + sha256(payload) → **resolved**；payload `sha256:d4e9729f01cdf1fd6…` (239751 B, http 200)
  备注：payload fetched and hashed by this package (binary not re-rendered); the markdown mention is the collective §4 sentence, hence the shared locator
- **A36** `figure`（§4，resolution=resolved_in_source）— 字符 [4370,4415) ｜ 行 117–117 ｜ 原文：
  > 见 figures（内嵌 PNG）：parity、误差-工况、外推覆盖、内部场、训练曲线。
  核验：GET /tensor/reports/13612/figures/fig3_uncertainty → http status + sha256(payload) → **resolved**；payload `sha256:98c9baa7582d71b9b…` (54742 B, http 200)
  备注：payload fetched and hashed by this package (binary not re-rendered); the markdown mention is the collective §4 sentence, hence the shared locator
- **A37** `figure`（§4，resolution=resolved_in_source）— 字符 [4370,4415) ｜ 行 117–117 ｜ 原文：
  > 见 figures（内嵌 PNG）：parity、误差-工况、外推覆盖、内部场、训练曲线。
  核验：GET /tensor/reports/13612/figures/fig4_fields → http status + sha256(payload) → **resolved**；payload `sha256:d4f27c4246323bdf5…` (59688 B, http 200)
  备注：payload fetched and hashed by this package (binary not re-rendered); the markdown mention is the collective §4 sentence, hence the shared locator
- **A38** `figure`（§4，resolution=resolved_in_source）— 字符 [4370,4415) ｜ 行 117–117 ｜ 原文：
  > 见 figures（内嵌 PNG）：parity、误差-工况、外推覆盖、内部场、训练曲线。
  核验：GET /tensor/reports/13612/figures/fig5_training → http status + sha256(payload) → **resolved**；payload `sha256:ad044f9d1c0806b52…` (74894 B, http 200)
  备注：payload fetched and hashed by this package (binary not re-rendered); the markdown mention is the collective §4 sentence, hence the shared locator

登记观察（未解析/风险项，原样入账）：

- **13612-o000** `digest_not_verifiable` — All upstream digests quoted in the report are truncated prefixes: dataset 16 hex (a778060b577942ed), the two kernel sources 12 hex (27ba0a9b2664 / 307afd4d2f65). None can be checked against a payload from here, so those paths are registered reference-only; this package neither re-hashes nor re-generates them.
  - assigned_status=`unresolved`；原因：digest truncated inside report 13612; full sha256 unavailable
  - 原文：> 数据集：`artifacts/p284w3_n09_fno/dataset.npz`（sha256 `a778060b577942ed`），训练域
  - 原文：> | `C_T, R_T` | `backend/api/domain/resistance_holtrop.py` |
  - 原文：> | `RAO_φ, RAO_z` | `backend/api/seakeeping_physics.py` |
- **13612-o001** `provenance_gap` — Upstream paths are repo-relative (backend/…, src/…, artifacts/…) but report 13612 names no repository, branch, commit or run id; the training wall clock has no run id either. Those paths cannot be hash-pinned to a commit from this record, so they are textual references with present_in_worktree=false (this worktree is TensorKnowledge and holds none of the five referenced paths).
  - assigned_status=`unresolved`；原因：no commit identity and no full-length digest inside report 13612
  - 原文：> FNO（`src/neural_operators/field_operator.py`）：lift → ×4（SpectralConv2d +
  - 原文：> 1302.0 s（本地 CPU，宿主机 load ≫ 核数，非最优算力）。
- **13612-o002** `figure_name_mapping` — The markdown names the figures only collectively by caption fragments, while the record `figures` field supplies fig1…fig5 file names. The 5↔5 pairing used here is by order/caption semantics; each payload was nevertheless fetched and hashed individually, so every figure asset is bound to its own sha256.
  - assigned_status=`supported`
  - 原文：> 见 figures（内嵌 PNG）：parity、误差-工况、外推覆盖、内部场、训练曲线。
- **13612-o003** `self_declared_non_pass_rows` — The source itself reports FAIL for criteria (a)(b) and calls criterion (c) a weak pass with q≈1e6-scale intervals. Statuses are registered unchanged; this package computes nothing and marks nothing verified.
  - assigned_status=`unresolved`；原因：kept exactly as the source states it (FAIL / weak pass)
  - 原文：> **honest FAIL 声明**：判据 (a)(b) 的精度阈值本节点**未达成**，上述 FAIL 不做任何粉饰；
  - 原文：> 因此 (c) 属**弱通过**：PICP 单独不足以证明外推可用，必须同时报告区间宽度（表中已列，量级 1e6）。

## ⑤ 注意点与局限

1. **摘要截断 = 不可核验**：报告只给 16/12 hex 前缀（dataset `a778060b577942ed`；内核 `27ba0a9b2664` / `307afd4d2f65`），本单**没有**去猜全量摘要、也没有重新生成工件，只把它登记为引用项。任何下游若需要核验这批上游工件，必须先去源头补全摘要或 commit id。
2. **溯源缺口**：markdown 里 `backend/…`、`src/…`、`artifacts/…` 全是仓库相对路径，但报告未写仓库名/分支/commit/run id；训练墙钟 1302.0 s 也没有 run id。故这 5 条只能在文本层面登记（present_in_worktree=false：本工作树是 TensorKnowledge，逐一 `test -e` 均为 absent，非「大概不在」）。
3. **图名映射是推断**：markdown §4 只集体点名五张图（parity、误差-工况、外推覆盖、内部场、训练曲线），文件名 `fig1_parity`…`fig5_training` 来自 record `figures` 字段；5↔5 配对按顺序+语义。为消除该不确定性，每张图都以**自身 payload sha256** 绑定，配对错位不会污染图内容证据。
4. **未做的事（诚实边界）**：未抽取 claim、未复核报告任何数字的算法正确性、未重跑训练/推理、未判断判据是否成立——这些属工序 02/03 与平台验证门，不属本单。
5. **图**：本单不产出新图（登记工序，无新计算）；源报告的 5 张图已按 sha256 登记并落本地副本，**未重绘、未拼接、未当作本单结果**。按报告纪律要求在此写明无图理由。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 机器判据 | 结果 |
|---|---|---|
| `valid_json` | `selfcheck.json:valid_json` = true | ✓ |
| `schema_pass` | `selfcheck.json:schema_pass` = true | ✓ |
| `source_locator_resolvable` | `selfcheck.json:source_locator_resolvable` = true | ✓ |
| `source_hash_matches` | `selfcheck.json:source_hash_matches_contract` = true | ✓ |
| `no_duplicate_ids` | `selfcheck.json:no_duplicate_ids` = true | ✓ |
| `all_claims_have_evidence_or_explicit_unresolved_status` | `selfcheck.json:all_claims_have_evidence_or_explicit_unresolved_status` = true | ✓ |
| 附加·引文逐字 | `selfcheck.json:all_quotes_verbatim` = true | ✓ |
| 附加·引文唯一 | `selfcheck.json:all_quotes_unique` = true | ✓ |
| 附加·图 payload 重算 | `selfcheck.json:figures_all_resolvable` = true | ✓ |
| 附加·counts 自洽 | `selfcheck.json:counts_consistent` = true | ✓ |
| 附加·claims 为空（契约允许） | `selfcheck.json:claims_empty_as_permitted` = true | ✓ |
| 附加·无 verified 标记 | `selfcheck.json:nothing_marked_verified` = true | ✓ |

`verify` 汇总：**PASS**；pytest 16 passed（只读断言）。图 payload 重算通过 5/5。

失败项：无。

### 误差判定（本工序口径，显式回答）

本单是登记工序，**不产生任何新的数值结果**（无代理预测、无与解析解/实验的比对），因此不存在「新算法 vs 基准」的误差量，也就无法也不应回答「是否<3%」。
需要说明的两点：

- 报告自带的 3% 判据是 (a) 训练集 R_T（`<3%` → 实测 4.49% → 判定 FAIL，见资产 A21）与§6 表的 `R_T（训练集） … **否**`（A28）；这两处**原样保留**，本单不改判、不重算。
- 唯一「误差类」量在本单内部是**机器自检的精确量**：源哈希逐字相等（0 位差异）、46 条引文 span 回读全等（0 处不一致）、5/5 图 payload sha256 重算相等。这些是 bit 级相等，不是统计误差。

### 复跑命令

```bash
# 全离线（快照与图副本已在树内）
python3 scripts/kf_wp13612_01_asset_manifest.py --verify \
  && python3 -m pytest tests/test_kf_wp13612_01_asset_registration.py -q \
  && python3 scripts/kf_wp13612_01_report.py
# 允许联网时重新取源/取图（哈希不变才算通过）
python3 scripts/kf_wp13612_01_asset_manifest.py --fetch --fetch-figures \
  && python3 scripts/kf_wp13612_01_asset_manifest.py --verify
```

生成时工作树 HEAD（=本单提交的父提交）：`3d43e3c` ｜ 生成器：`scripts/kf_wp13612_01_asset_manifest.py` ｜ Python 3.11.6

### result JSON（唯一一个 json 代码块，原样来自 `docs/kf/wp-13612-01/kf_result.json`）

```json
{
 "package_id": "wp-13612-01",
 "task_type": "01-asset-registration",
 "report_id": "13612",
 "provenance": {
  "source_hash": "sha256:85bbae874e9babb342a5d216c19e00265dcc108115d6dcb53f1991af48846888",
  "source_field": "markdown",
  "producer": "agent/m15765 (TensorKnowledge) · wp-13612-01",
  "emitted_at": "2026-11-12T02:33:33+00:00",
  "notes": "markdown snapshot pinned at docs/kf/wp-13612-01/source/report_13612.md; sha256 recomputed locally and equal to the contract hash"
 },
 "outputs": {
  "asset_manifest.json": {
   "schema": "asset_manifest.v1",
   "package_id": "wp-13612-01",
   "task_type": "01-asset-registration",
   "report_id": "13612",
   "lane": "C",
   "source": {
    "uri": "tensor://reports/13612",
    "field": "markdown",
    "hash_alg": "sha256",
    "hash": "85bbae874e9babb342a5d216c19e00265dcc108115d6dcb53f1991af48846888",
    "chars": 5526,
    "bytes_utf8": 9350,
    "title": "物理信息神经算子（FNO）船体阻力/耐波实时代理模型（P284W3-N09）",
    "scenario_key": "p284w3-n09-fno-surrogate",
    "snapshot": "docs/kf/wp-13612-01/source/report_13612.md",
    "platform_tags": [
     "FNO",
     "neural-operator",
     "resistance",
     "seakeeping",
     "physics-constrained",
     "conformal-uncertainty",
     "honest-FAIL",
     "TensorPlatform"
    ],
    "platform_figures": [
     {
      "name": "fig1_parity",
      "caption": "预测-真值一致性（测试集 vs 外推集，含误差带）"
     },
     {
      "name": "fig2_error_vs_condition",
      "caption": "外推域相对误差随 Fr / 浪向 β 的分布"
     },
     {
      "name": "fig3_uncertainty",
      "caption": "外推域 conformal 区间覆盖与各目标覆盖率"
     },
     {
      "name": "fig4_fields",
      "caption": "内部场：几何输入 → 阻力密度场 → 散度残差"
     },
     {
      "name": "fig5_training",
      "caption": "集成成员训练曲线（数据+物理损失）"
     }
    ]
   },
   "assets": [
    {
     "asset_id": "A01",
     "asset_class": "report_document",
     "label": "report 13612 markdown as a whole (5526 chars / 9350 UTF-8 bytes)",
     "in_report_section": "document",
     "locator": {
      "method": "document",
      "start_char": 0,
      "end_char": 40,
      "start_line": 1,
      "end_line": 1,
      "quote": "# 物理信息神经算子（FNO）船体阻力/耐波实时代理模型（P284W3-N09）",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "sha256(markdown utf8) vs contract source_hash",
      "result": "resolved"
     },
     "note": "document-level locator = [0, len(markdown)); quote is the title line (unique)"
    },
    {
     "asset_id": "A02",
     "asset_class": "section",
     "label": "§1 案例介绍 (background / data sources / parameter table / operator form)",
     "in_report_section": "§1",
     "locator": {
      "method": "char_span",
      "start_char": 42,
      "end_char": 52,
      "start_line": 3,
      "end_line": 3,
      "quote": "## 1. 案例介绍",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "heading present verbatim",
      "result": "resolved"
     },
     "note": "section heading"
    },
    {
     "asset_id": "A03",
     "asset_class": "section",
     "label": "§2 方法 (architecture / physics constraints / training / error metric)",
     "in_report_section": "§2",
     "locator": {
      "method": "char_span",
      "start_char": 1513,
      "end_char": 1521,
      "start_line": 41,
      "end_line": 41,
      "quote": "## 2. 方法",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "heading present verbatim",
      "result": "resolved"
     },
     "note": "section heading"
    },
    {
     "asset_id": "A04",
     "asset_class": "section",
     "label": "§3 计算结果 (criteria table / per-split errors / extrapolation bounds)",
     "in_report_section": "§3",
     "locator": {
      "method": "char_span",
      "start_char": 2542,
      "end_char": 2552,
      "start_line": 72,
      "end_line": 72,
      "quote": "## 3. 计算结果",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "heading present verbatim",
      "result": "resolved"
     },
     "note": "section heading"
    },
    {
     "asset_id": "A05",
     "asset_class": "section",
     "label": "§4 结果图 (collective pointer to the 5 embedded figures)",
     "in_report_section": "§4",
     "locator": {
      "method": "char_span",
      "start_char": 4359,
      "end_char": 4368,
      "start_line": 115,
      "end_line": 115,
      "quote": "## 4. 结果图",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "heading present verbatim",
      "result": "resolved"
     },
     "note": "section heading"
    },
    {
     "asset_id": "A06",
     "asset_class": "section",
     "label": "§5 注意点与局限 (5 numbered limitation items)",
     "in_report_section": "§5",
     "locator": {
      "method": "char_span",
      "start_char": 4417,
      "end_char": 4429,
      "start_line": 119,
      "end_line": 119,
      "quote": "## 5. 注意点与局限",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "heading present verbatim",
      "result": "resolved"
     },
     "note": "section heading"
    },
    {
     "asset_id": "A07",
     "asset_class": "section",
     "label": "§6 误差判定（逐项，显式回答）— criterion-vs-measured table + honest-FAIL statement",
     "in_report_section": "§6",
     "locator": {
      "method": "char_span",
      "start_char": 5097,
      "end_char": 5116,
      "start_line": 136,
      "end_line": 136,
      "quote": "## 6. 误差判定（逐项，显式回答）",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "heading present verbatim",
      "result": "resolved"
     },
     "note": "section heading"
    },
    {
     "asset_id": "A08",
     "asset_class": "artifact_path",
     "label": "dataset artifact artifacts/p284w3_n09_fno/dataset.npz (digest truncated to 16 hex)",
     "in_report_section": "§1.2",
     "locator": {
      "method": "char_span",
      "start_char": 691,
      "end_char": 764,
      "start_line": 19,
      "end_line": 19,
      "quote": "数据集：`artifacts/p284w3_n09_fno/dataset.npz`（sha256 `a778060b577942ed`），训练域",
      "unique": true
     },
     "resolution": "referenced_unresolved",
     "resolution_check": {
      "check": "worktree lookup of repo-relative path + digest length check",
      "result": "unresolved"
     },
     "note": "path is relative to the producing repo (not named in the report); digest is a 16-hex prefix so the payload cannot be hash-pinned from this record. Not copied, not re-generated."
    },
    {
     "asset_id": "A09",
     "asset_class": "code_path",
     "label": "label kernel backend/api/domain/resistance_holtrop.py (sha256 prefix 27ba0a9b2664)",
     "in_report_section": "§1.2",
     "locator": {
      "method": "char_span",
      "start_char": 365,
      "end_char": 424,
      "start_line": 16,
      "end_line": 16,
      "quote": "| `C_T, R_T` | `backend/api/domain/resistance_holtrop.py` |",
      "unique": true
     },
     "resolution": "referenced_unresolved",
     "resolution_check": {
      "check": "worktree lookup of repo-relative path + digest length check",
      "result": "unresolved"
     },
     "note": "12-hex prefix only; no repo/commit identity in the report"
    },
    {
     "asset_id": "A10",
     "asset_class": "code_path",
     "label": "label kernel backend/api/seakeeping_physics.py (sha256 prefix 307afd4d2f65)",
     "in_report_section": "§1.2",
     "locator": {
      "method": "char_span",
      "start_char": 517,
      "end_char": 573,
      "start_line": 17,
      "end_line": 17,
      "quote": "| `RAO_φ, RAO_z` | `backend/api/seakeeping_physics.py` |",
      "unique": true
     },
     "resolution": "referenced_unresolved",
     "resolution_check": {
      "check": "worktree lookup of repo-relative path + digest length check",
      "result": "unresolved"
     },
     "note": "12-hex prefix only; no repo/commit identity in the report"
    },
    {
     "asset_id": "A11",
     "asset_class": "code_path",
     "label": "FNO implementation src/neural_operators/field_operator.py",
     "in_report_section": "§2.1",
     "locator": {
      "method": "char_span",
      "start_char": 1534,
      "end_char": 1606,
      "start_line": 44,
      "end_line": 44,
      "quote": "FNO（`src/neural_operators/field_operator.py`）：lift → ×4（SpectralConv2d +",
      "unique": true
     },
     "resolution": "referenced_unresolved",
     "resolution_check": {
      "check": "worktree lookup of repo-relative path",
      "result": "unresolved"
     },
     "note": "no digest and no commit identity inside report 13612"
    },
    {
     "asset_id": "A12",
     "asset_class": "test_path",
     "label": "regression test test_input_tensor_channels_and_mask, named as the §5-1 regression guard",
     "in_report_section": "§5 item 1",
     "locator": {
      "method": "char_span",
      "start_char": 4575,
      "end_char": 4632,
      "start_line": 124,
      "end_line": 124,
      "quote": "回归防护：`test_input_tensor_channels_and_mask` + 数据集清单登记特征定义。",
      "unique": true
     },
     "resolution": "referenced_unresolved",
     "resolution_check": {
      "check": "test-name lookup inside this worktree",
      "result": "unresolved"
     },
     "note": "test name only: no file path, no suite/commit identity"
    },
    {
     "asset_id": "A13",
     "asset_class": "table",
     "label": "label-source table (kernel, method, evidence grade, source sha256 prefix per target)",
     "in_report_section": "§1.2",
     "locator": {
      "method": "char_span",
      "start_char": 305,
      "end_char": 346,
      "start_line": 14,
      "end_line": 14,
      "quote": "| 标签 | 内核 | 方法与证据等级 | 源码 sha256（前 12 位） |",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "table header present verbatim",
      "result": "resolved"
     },
     "note": "4 columns, 2 data rows (C_T/R_T and RAO_z/RAO_φ)"
    },
    {
     "asset_id": "A14",
     "asset_class": "table",
     "label": "sampling-domain parameter table (L, Fr, L/B, β, B/T, GM/B, Cb, KG/T, Cwp, λ/L)",
     "in_report_section": "§1.3",
     "locator": {
      "method": "char_span",
      "start_char": 958,
      "end_char": 1011,
      "start_line": 28,
      "end_line": 28,
      "quote": "| L | 60–320 m（对数均匀） | Fr | 0.08–0.40（外推 0.40–0.55） |",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "table row present verbatim",
      "result": "resolved"
     },
     "note": "sampled ranges incl. extrapolation ranges"
    },
    {
     "asset_id": "A15",
     "asset_class": "operator_input_spec",
     "label": "operator input field spec: u(x,z), 24 channels, 16x4 grid, 18 non-dimensional conditions",
     "in_report_section": "§1.4",
     "locator": {
      "method": "char_span",
      "start_char": 1208,
      "end_char": 1265,
      "start_line": 35,
      "end_line": 35,
      "quote": "输入场 `u(x,z)`（24 通道，网格 16×4）：逐站剖面面积比 `A(x)/(B·T)`、淹没掩膜、半宽比",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "spec sentence present verbatim",
      "result": "resolved"
     },
     "note": "names the field channels; the remaining channels continue on the next lines"
    },
    {
     "asset_id": "A16",
     "asset_class": "gate_predicate",
     "label": "geometry pre-check: buoyancy identity, max deviation 3.3e-16",
     "in_report_section": "§1.2",
     "locator": {
      "method": "char_span",
      "start_char": 861,
      "end_char": 893,
      "start_line": 22,
      "end_line": 22,
      "quote": "`3.3e-16`（浮力守恒），Cb·L·B·T 与排水量自洽。",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "sentence present verbatim",
      "result": "resolved"
     },
     "note": "the report's own geometry-verification evidence (∫(A/(B·T))dx = Cb); not re-run here"
    },
    {
     "asset_id": "A17",
     "asset_class": "physics_constraint_spec",
     "label": "hard constraint #3: RAO_φ ∝ |sin β|, exact 0 at β=0/180°, residual <1e-12",
     "in_report_section": "§2.2",
     "locator": {
      "method": "char_span",
      "start_char": 1932,
      "end_char": 1993,
      "start_line": 55,
      "end_line": 55,
      "quote": "3. 对称性：`RAO_φ ∝ |sin β|`（β=0/180° 恒为 0，float64 计算后残差 <1e-12）；",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "list item present verbatim",
      "result": "resolved"
     },
     "note": "one of the four by-construction exact constraints"
    },
    {
     "asset_id": "A18",
     "asset_class": "training_config",
     "label": "ensemble config: 2-member deep ensemble (log-space mean + member std σ)",
     "in_report_section": "§2.3",
     "locator": {
      "method": "char_span",
      "start_char": 2265,
      "end_char": 2299,
      "start_line": 64,
      "end_line": 64,
      "quote": "60，**2 成员深度集成**（对数空间均值 + 成员标准差 σ）；",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "config sentence present verbatim",
      "result": "resolved"
     },
     "note": "preceded by AdamW lr=0.006/wd=0.0001, cosine, batch 64, epochs 60"
    },
    {
     "asset_id": "A19",
     "asset_class": "metric_definition",
     "label": "MAPE definition with floor = 0.02 × training-set median, plus strict_mape_pct",
     "in_report_section": "§2.4",
     "locator": {
      "method": "char_span",
      "start_char": 2416,
      "end_char": 2485,
      "start_line": 69,
      "end_line": 69,
      "quote": "`mape_pct = mean |Δ|/max(|truth|, floor)×100`，`floor = 0.02 × 训练集中位数`",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "definition present verbatim",
      "result": "resolved"
     },
     "note": "the report's error-yardstick declaration; every §3/§6 percentage depends on this floor"
    },
    {
     "asset_id": "A20",
     "asset_class": "table",
     "label": "criteria table row (b) test-set R_T <5% → 6.36% FAIL",
     "in_report_section": "§3.1",
     "locator": {
      "method": "char_span",
      "start_char": 2704,
      "end_char": 2740,
      "start_line": 80,
      "end_line": 80,
      "quote": "| (b) 测试集 R_T | <5% | 6.36% | FAIL |",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "table row present verbatim",
      "result": "resolved"
     },
     "note": "criterion row carried with its FAIL verdict unchanged"
    },
    {
     "asset_id": "A21",
     "asset_class": "table",
     "label": "criteria table row (a) train-set R_T <3% → 4.49% FAIL",
     "in_report_section": "§3.1",
     "locator": {
      "method": "char_span",
      "start_char": 2616,
      "end_char": 2652,
      "start_line": 78,
      "end_line": 78,
      "quote": "| (a) 训练集 R_T | <3% | 4.49% | FAIL |",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "table row present verbatim",
      "result": "resolved"
     },
     "note": "the only criterion naming a 3% threshold; registered so no downstream 工序 lifts it"
    },
    {
     "asset_id": "A22",
     "asset_class": "table",
     "label": "criteria table row (d) CPU latency <10 ms → median 6.65 ms (p95 9.63 ms) PASS",
     "in_report_section": "§3.1",
     "locator": {
      "method": "char_span",
      "start_char": 2856,
      "end_char": 2917,
      "start_line": 83,
      "end_line": 83,
      "quote": "| (d) 单点推理时延（CPU） | <10 ms | 中位 6.65 ms（p95 9.63 ms） | PASS |",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "table row present verbatim",
      "result": "resolved"
     },
     "note": "one of the two PASS criteria (with (c), which the source itself downgrades)"
    },
    {
     "asset_id": "A23",
     "asset_class": "table",
     "label": "per-split error table, extrapolation row (R_T / RAO_z / RAO_φ, strict in parentheses)",
     "in_report_section": "§3.2",
     "locator": {
      "method": "char_span",
      "start_char": 3342,
      "end_char": 3433,
      "start_line": 96,
      "end_line": 96,
      "quote": "| 外推集（Fr>0.4 或 β>60°） | 28.67% (28.68%) | 43191.09% (66933.87%) | 107215.54% (586642.06%) |",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "table row present verbatim",
      "result": "resolved"
     },
     "note": "extrapolation errors of 1e4–1e5 % are the source's own numbers"
    },
    {
     "asset_id": "A24",
     "asset_class": "table",
     "label": "extrapolation-bound table, RAO_z row (q 18.70→55.7%; 4553709.86→90.0%; width inf)",
     "in_report_section": "§3.3",
     "locator": {
      "method": "char_span",
      "start_char": 3567,
      "end_char": 3640,
      "start_line": 103,
      "end_line": 103,
      "quote": "| RAO_z | 18.70（55.7%） | 4553709.86（90.0%） | inf（inf=区间宽度不可度量，模型外推无信息量） |",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "table row present verbatim",
      "result": "resolved"
     },
     "note": "records the q magnitudes that make criterion (c) a weak pass"
    },
    {
     "asset_id": "A25",
     "asset_class": "table",
     "label": "interpolation-limit control experiment, n_train=1600 row (plain MLP surrogate)",
     "in_report_section": "§3.3",
     "locator": {
      "method": "char_span",
      "start_char": 3930,
      "end_char": 4002,
      "start_line": 111,
      "end_line": 111,
      "quote": "| 1600 | 2.81e-02 / 8.01e-02 / 7.39e-02 | 13.5% | 54.5% | 55.6% | 3.44 |",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "table row present verbatim",
      "result": "resolved"
     },
     "note": "control-experiment row (the n=640 row is the line above)"
    },
    {
     "asset_id": "A26",
     "asset_class": "run_output_token",
     "label": "empirical sample-size scaling for R_T: e∝n^(-0.30), 3.0% needs ~233404 samples",
     "in_report_section": "§3.3",
     "locator": {
      "method": "char_span",
      "start_char": 4051,
      "end_char": 4089,
      "start_line": 113,
      "end_line": 113,
      "quote": "标度 e∝n^(-0.30)；按此外推达 3.0% 需 ~233404 样本",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "token present verbatim",
      "result": "resolved"
     },
     "note": "derived number quoted only; not recomputed by this package"
    },
    {
     "asset_id": "A27",
     "asset_class": "run_output_token",
     "label": "training wall clock 1302.0 s (local CPU, oversubscribed host)",
     "in_report_section": "§2.3",
     "locator": {
      "method": "char_span",
      "start_char": 2358,
      "end_char": 2395,
      "start_line": 66,
      "end_line": 66,
      "quote": "1302.0 s（本地 CPU，宿主机 load ≫ 核数，非最优算力）。",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "token present verbatim",
      "result": "resolved"
     },
     "note": "no run id / log file referenced by the report"
    },
    {
     "asset_id": "A28",
     "asset_class": "table",
     "label": "§6 error-judgement row R_T (test set): threshold <5%, measured 6.36%, answer 否",
     "in_report_section": "§6",
     "locator": {
      "method": "char_span",
      "start_char": 5234,
      "end_char": 5273,
      "start_line": 141,
      "end_line": 141,
      "quote": "| R_T（测试集） | 同上 | <5% | 6.36% | **否** |",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "table row present verbatim",
      "result": "resolved"
     },
     "note": "the source answers 否; this package stamps nothing as verified"
    },
    {
     "asset_id": "A29",
     "asset_class": "self_declared_non_pass",
     "label": "honest-FAIL declaration for criteria (a)(b)",
     "in_report_section": "§6",
     "locator": {
      "method": "char_span",
      "start_char": 5367,
      "end_char": 5427,
      "start_line": 145,
      "end_line": 145,
      "quote": "**honest FAIL 声明**：判据 (a)(b) 的精度阈值本节点**未达成**，上述 FAIL 不做任何粉饰；",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "declaration present verbatim",
      "result": "resolved"
     },
     "note": "carried verbatim so no downstream step lifts it to a pass"
    },
    {
     "asset_id": "A30",
     "asset_class": "self_declared_non_pass",
     "label": "weak-pass caveat for criterion (c): coverage 89.3% only with q≈1e6-scale intervals",
     "in_report_section": "§3.1",
     "locator": {
      "method": "char_span",
      "start_char": 3058,
      "end_char": 3115,
      "start_line": 88,
      "end_line": 88,
      "quote": "因此 (c) 属**弱通过**：PICP 单独不足以证明外推可用，必须同时报告区间宽度（表中已列，量级 1e6）。",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "caveat present verbatim",
      "result": "resolved"
     },
     "note": "the report downgrades its own PASS to weak; preserved"
    },
    {
     "asset_id": "A31",
     "asset_class": "limitation_item",
     "label": "dimensional-frequency bug (ω·√(L/g) vs ω/√(gL)) found and fixed; RAO error 100%→61%",
     "in_report_section": "§5 item 1",
     "locator": {
      "method": "char_span",
      "start_char": 4431,
      "end_char": 4486,
      "start_line": 121,
      "end_line": 121,
      "quote": "1. **量纲错误（本节点踩到并修正）**：无因次频率必须是 `ω·√(L/g)`，不是 `ω/√(gL)`。",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "list item present verbatim",
      "result": "resolved"
     },
     "note": "registered as a reusable trap; not re-verified here"
    },
    {
     "asset_id": "A32",
     "asset_class": "limitation_item",
     "label": "interpolation-limit limitation (≥10-dim input space, thousand-scale samples sparse)",
     "in_report_section": "§5 item 3",
     "locator": {
      "method": "char_span",
      "start_char": 4743,
      "end_char": 4796,
      "start_line": 127,
      "end_line": 127,
      "quote": "3. **插值极限（关键局限）**：输入为 ≥10 维无因次群，千级样本在 10 维空间里仍属稀疏——对照",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "list item present verbatim",
      "result": "resolved"
     },
     "note": "basis of the 1e5–1e6 sample-count estimate"
    },
    {
     "asset_id": "A33",
     "asset_class": "limitation_item",
     "label": "label-kernel ceiling: Holtrop ±5–10%, STF 2D coefficients analytic approximations",
     "in_report_section": "§5 item 4",
     "locator": {
      "method": "char_span",
      "start_char": 4923,
      "end_char": 4982,
      "start_line": 131,
      "end_line": 131,
      "quote": "4. **训练标签是回归/切片理论内核**（Holtrop ±5–10%；STF 2D 系数为解析近似），因此本代理的",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "list item present verbatim",
      "result": "resolved"
     },
     "note": "no experimental benchmark was performed by the source node (its own words)"
    },
    {
     "asset_id": "A34",
     "asset_class": "figure",
     "label": "figure fig1_parity — 预测-真值一致性（测试集 vs 外推集，含误差带） (record `figures` entry; markdown names it only collectively)",
     "in_report_section": "§4",
     "locator": {
      "method": "char_span",
      "start_char": 4370,
      "end_char": 4415,
      "start_line": 117,
      "end_line": 117,
      "quote": "见 figures（内嵌 PNG）：parity、误差-工况、外推覆盖、内部场、训练曲线。",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "GET /tensor/reports/13612/figures/fig1_parity → http status + sha256(payload)",
      "result": "resolved",
      "http_status": 200,
      "bytes": 179072,
      "payload_sha256": "sha256:5d0b8be9e2674d017c6ac5274f5da5a566548f0e4c0d66de755d26ee7c788c4e",
      "png_magic_ok": true,
      "local_copy": "docs/kf/wp-13612-01/figures/fig1_parity.png",
      "declared_name_from_record": "fig1_parity",
      "declared_caption_from_record": "预测-真值一致性（测试集 vs 外推集，含误差带）"
     },
     "note": "payload fetched and hashed by this package (binary not re-rendered); the markdown mention is the collective §4 sentence, hence the shared locator"
    },
    {
     "asset_id": "A35",
     "asset_class": "figure",
     "label": "figure fig2_error_vs_condition — 外推域相对误差随 Fr / 浪向 β 的分布 (record `figures` entry; markdown names it only collectively)",
     "in_report_section": "§4",
     "locator": {
      "method": "char_span",
      "start_char": 4370,
      "end_char": 4415,
      "start_line": 117,
      "end_line": 117,
      "quote": "见 figures（内嵌 PNG）：parity、误差-工况、外推覆盖、内部场、训练曲线。",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "GET /tensor/reports/13612/figures/fig2_error_vs_condition → http status + sha256(payload)",
      "result": "resolved",
      "http_status": 200,
      "bytes": 239751,
      "payload_sha256": "sha256:d4e9729f01cdf1fd60eca3cb2f3063d0c6c7403a58dce23a5e9f8d0a78b94c22",
      "png_magic_ok": true,
      "local_copy": "docs/kf/wp-13612-01/figures/fig2_error_vs_condition.png",
      "declared_name_from_record": "fig2_error_vs_condition",
      "declared_caption_from_record": "外推域相对误差随 Fr / 浪向 β 的分布"
     },
     "note": "payload fetched and hashed by this package (binary not re-rendered); the markdown mention is the collective §4 sentence, hence the shared locator"
    },
    {
     "asset_id": "A36",
     "asset_class": "figure",
     "label": "figure fig3_uncertainty — 外推域 conformal 区间覆盖与各目标覆盖率 (record `figures` entry; markdown names it only collectively)",
     "in_report_section": "§4",
     "locator": {
      "method": "char_span",
      "start_char": 4370,
      "end_char": 4415,
      "start_line": 117,
      "end_line": 117,
      "quote": "见 figures（内嵌 PNG）：parity、误差-工况、外推覆盖、内部场、训练曲线。",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "GET /tensor/reports/13612/figures/fig3_uncertainty → http status + sha256(payload)",
      "result": "resolved",
      "http_status": 200,
      "bytes": 54742,
      "payload_sha256": "sha256:98c9baa7582d71b9be1864d5d7e89886d4224bba47adea6a8717d7e5d193fc3c",
      "png_magic_ok": true,
      "local_copy": "docs/kf/wp-13612-01/figures/fig3_uncertainty.png",
      "declared_name_from_record": "fig3_uncertainty",
      "declared_caption_from_record": "外推域 conformal 区间覆盖与各目标覆盖率"
     },
     "note": "payload fetched and hashed by this package (binary not re-rendered); the markdown mention is the collective §4 sentence, hence the shared locator"
    },
    {
     "asset_id": "A37",
     "asset_class": "figure",
     "label": "figure fig4_fields — 内部场：几何输入 → 阻力密度场 → 散度残差 (record `figures` entry; markdown names it only collectively)",
     "in_report_section": "§4",
     "locator": {
      "method": "char_span",
      "start_char": 4370,
      "end_char": 4415,
      "start_line": 117,
      "end_line": 117,
      "quote": "见 figures（内嵌 PNG）：parity、误差-工况、外推覆盖、内部场、训练曲线。",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "GET /tensor/reports/13612/figures/fig4_fields → http status + sha256(payload)",
      "result": "resolved",
      "http_status": 200,
      "bytes": 59688,
      "payload_sha256": "sha256:d4f27c4246323bdf5b0b59ee97a122acc8b0d84b55ec3e3f5278310c3940f1fa",
      "png_magic_ok": true,
      "local_copy": "docs/kf/wp-13612-01/figures/fig4_fields.png",
      "declared_name_from_record": "fig4_fields",
      "declared_caption_from_record": "内部场：几何输入 → 阻力密度场 → 散度残差"
     },
     "note": "payload fetched and hashed by this package (binary not re-rendered); the markdown mention is the collective §4 sentence, hence the shared locator"
    },
    {
     "asset_id": "A38",
     "asset_class": "figure",
     "label": "figure fig5_training — 集成成员训练曲线（数据+物理损失） (record `figures` entry; markdown names it only collectively)",
     "in_report_section": "§4",
     "locator": {
      "method": "char_span",
      "start_char": 4370,
      "end_char": 4415,
      "start_line": 117,
      "end_line": 117,
      "quote": "见 figures（内嵌 PNG）：parity、误差-工况、外推覆盖、内部场、训练曲线。",
      "unique": true
     },
     "resolution": "resolved_in_source",
     "resolution_check": {
      "check": "GET /tensor/reports/13612/figures/fig5_training → http status + sha256(payload)",
      "result": "resolved",
      "http_status": 200,
      "bytes": 74894,
      "payload_sha256": "sha256:ad044f9d1c0806b52ef3632e87c6e07723bcb46682664bc23f0546506a6c7084",
      "png_magic_ok": true,
      "local_copy": "docs/kf/wp-13612-01/figures/fig5_training.png",
      "declared_name_from_record": "fig5_training",
      "declared_caption_from_record": "集成成员训练曲线（数据+物理损失）"
     },
     "note": "payload fetched and hashed by this package (binary not re-rendered); the markdown mention is the collective §4 sentence, hence the shared locator"
    }
   ],
   "observations": [
    {
     "observation_id": "13612-o000",
     "kind": "digest_not_verifiable",
     "description": "All upstream digests quoted in the report are truncated prefixes: dataset 16 hex (a778060b577942ed), the two kernel sources 12 hex (27ba0a9b2664 / 307afd4d2f65). None can be checked against a payload from here, so those paths are registered reference-only; this package neither re-hashes nor re-generates them.",
     "quotes": [
      "数据集：`artifacts/p284w3_n09_fno/dataset.npz`（sha256 `a778060b577942ed`），训练域",
      "| `C_T, R_T` | `backend/api/domain/resistance_holtrop.py` |",
      "| `RAO_φ, RAO_z` | `backend/api/seakeeping_physics.py` |"
     ],
     "assigned_status": "unresolved",
     "unresolved_reason": "digest truncated inside report 13612; full sha256 unavailable"
    },
    {
     "observation_id": "13612-o001",
     "kind": "provenance_gap",
     "description": "Upstream paths are repo-relative (backend/…, src/…, artifacts/…) but report 13612 names no repository, branch, commit or run id; the training wall clock has no run id either. Those paths cannot be hash-pinned to a commit from this record, so they are textual references with present_in_worktree=false (this worktree is TensorKnowledge and holds none of the five referenced paths).",
     "quotes": [
      "FNO（`src/neural_operators/field_operator.py`）：lift → ×4（SpectralConv2d +",
      "1302.0 s（本地 CPU，宿主机 load ≫ 核数，非最优算力）。"
     ],
     "assigned_status": "unresolved",
     "unresolved_reason": "no commit identity and no full-length digest inside report 13612"
    },
    {
     "observation_id": "13612-o002",
     "kind": "figure_name_mapping",
     "description": "The markdown names the figures only collectively by caption fragments, while the record `figures` field supplies fig1…fig5 file names. The 5↔5 pairing used here is by order/caption semantics; each payload was nevertheless fetched and hashed individually, so every figure asset is bound to its own sha256.",
     "quotes": [
      "见 figures（内嵌 PNG）：parity、误差-工况、外推覆盖、内部场、训练曲线。"
     ],
     "assigned_status": "supported",
     "note": "name↔caption pairing inferred; payload digest is the authoritative binding"
    },
    {
     "observation_id": "13612-o003",
     "kind": "self_declared_non_pass_rows",
     "description": "The source itself reports FAIL for criteria (a)(b) and calls criterion (c) a weak pass with q≈1e6-scale intervals. Statuses are registered unchanged; this package computes nothing and marks nothing verified.",
     "quotes": [
      "**honest FAIL 声明**：判据 (a)(b) 的精度阈值本节点**未达成**，上述 FAIL 不做任何粉饰；",
      "因此 (c) 属**弱通过**：PICP 单独不足以证明外推可用，必须同时报告区间宽度（表中已列，量级 1e6）。"
     ],
     "assigned_status": "unresolved",
     "unresolved_reason": "kept exactly as the source states it (FAIL / weak pass)"
    }
   ],
   "counts": {
    "assets": 38,
    "by_class": {
     "report_document": 1,
     "section": 6,
     "artifact_path": 1,
     "code_path": 3,
     "test_path": 1,
     "table": 9,
     "operator_input_spec": 1,
     "gate_predicate": 1,
     "physics_constraint_spec": 1,
     "training_config": 1,
     "metric_definition": 1,
     "run_output_token": 2,
     "self_declared_non_pass": 2,
     "limitation_item": 3,
     "figure": 5
    },
    "by_resolution": {
     "resolved_in_source": 33,
     "referenced_unresolved": 5
    },
    "resolved_in_source": 33,
    "referenced_unresolved": 5,
    "declared_absent": 0,
    "claims_registered": 0
   },
   "claims": [],
   "claims_note": "task_type 01 registers no knowledge claims; the empty array is the contract-permitted complete result (constraint no_forced_claim_generation). The report's numbers are locatable through the assets above but are NOT extracted here and NOT marked verified.",
   "integrity": {
    "hash_recomputed_locally": "sha256:85bbae874e9babb342a5d216c19e00265dcc108115d6dcb53f1991af48846888",
    "hash_matches_contract": true,
    "chars_match_contract": true,
    "quote_uniqueness": {
     "quotes_checked": 46,
     "verbatim_ok": 46,
     "unique_ok": 46,
     "spans_rechecked": true
    },
    "asset_ids_unique": true,
    "claims_registered": 0,
    "nothing_marked_verified": true,
    "envelope_schema": "schemas/kf_result.v1.schema.json"
   },
   "repro_cmd": "python3 scripts/kf_wp13612_01_asset_manifest.py && python3 scripts/kf_wp13612_01_asset_manifest.py --verify && python3 -m pytest tests/test_kf_wp13612_01_asset_registration.py -q",
   "tools": {
    "generator": "scripts/kf_wp13612_01_asset_manifest.py",
    "python": "3.11.6"
   }
  }
 },
 "claims": []
}
```
