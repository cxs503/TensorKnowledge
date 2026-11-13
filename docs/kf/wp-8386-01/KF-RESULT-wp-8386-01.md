# KF-RESULT wp-8386-01

## ① 本工序做了什么

本单是"报告 → 知识产线"上的一道工序：**资产登记（task_type = 01-asset-registration）**，只服务
`report_id = 8386` 这一份报告，`lane=C`，交付仓 TensorKnowledge，状态 draft。

- 源报告：report 8386，《[m7061] FuelEU 柔性三件套：RFNBO 乘子 + 岸电 OPS 抵扣 + 存借跨年滚动（判据 a–g 全 PASS）》，`scenario_key = fueleu_flexible_multiyear`。
- 登记结果：**30 个资产**，分 23 类；按可解析性
  **22 resolved_in_source / 7 referenced_unresolved /
  1 declared_absent**。
- 源资产本体：`tensor://reports/8386` 的 `markdown` 字段，**20879 字符 /
  27959 字节 UTF-8**，本地重算 `sha256 = 4104143f4653a88fd9df9c12b93d3d05d42592aca5c835749a34f21ad85761af`，
  与契约 `source_hash` 逐字节相同。
- 本工序**不做**的事（契约 `objective` 只给了 `register_assets: true`）：不抽取 claim、不做报告类型
  分类、不改写上游产物、**不把任何结论标成 verified**（`claims = []` 是完整结果，不是缺项）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取证不凭记忆**：`scripts/kf_wp8386_01_fetch.py` 登录平台 → `GET /api/v1/tensor/reports/8386`
   → 取 `markdown` 字段落盘 `runs/wp-8386-01/report_8386.md`，同时把原始响应存
   `report_8386.json`。哈希与契约不一致时脚本直接 `SystemExit`，不产出半成品。
2. **定位而非抄写**：`scripts/kf_wp8386_01_register.py` 维护 30 行锚点表
   （asset_id / 类 / 报告小节 / **唯一锚点串**）。运行时对每个锚点在 markdown 中求出现次数，
   **必须恰好 1 次**，否则中止；`quote` 不是重敲的，而是 `md[start_char:end_char]` 的**原样切片**，
   行号由字符偏移反推。因此"零手抄"是结构保证而不是承诺。
3. **可解析性只认机器证据**，五类探针：
   - 页内资产 → `unique_substring_anchor_in_markdown`（切片相等 + 全文唯一）；
   - 上游文件/目录（`artifacts/fueleu_maritime_m7061/*`、`backend/modules/fueleu_maritime/`）
     → `worktree_path_exists:*`（本工作树实测，结果为 absent → 登记 `referenced_unresolved`，不编造路径）；
   - API 路由 → `http_probe:http://127.0.0.1:8002/api/v1/fueleu-maritime/registry`（实测返回非 2xx → unresolved）；
   - 上游提交 `7017a623` → `git_cat_file:7017a623`（本仓对象库 128 → unresolved）；
   - 原文声明"无云图" → `scan_image_references_for_fieldmap`（6 条图片引用中 0 条场量云图 → absent）。
   声明与探针必须一致：不一致时 build 直接 FATAL（`resolution_matches_probe` 检查在 verify 里再兜一次）。
4. **独立校验**：`scripts/kf_wp8386_01_register.py verify` 在**新登录、重新拉取**的 markdown 上
   逐资产重切片比对（不信任本地副本），跑 JSON Schema、id 唯一性、claim 证据策略、计数自洽、
   禁 `verified` 标记，输出 `verification.json`（overall = **PASS**）。
5. **确定性自证**：清空后重建两次 `asset_manifest.json`，字节完全相同
   （`sha256:a3c4a34652e5a428859b8662a25c6ad3bb855e7feee060789dba586f10b363e7`，manifest 内不含时间戳；时间只出现在信封 `provenance.emitted_at`）。
6. **测试**：`tests/test_kf_wp8386_01.py` 14 项，含 4 个**反向对照**（篡改 quote 的一个数字、
   平移 span 1 字符、把 absent 的 PNG 谎报成 resolved、制造重复 id），证明检查器真的会红。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-8386-01/asset_manifest.json` | 主产物：30 资产 / 23 类；22+7+1；`sha256:a3c4a34652e5a428859b8662a25c6ad3bb855e7feee060789dba586f10b363e7` |
| `docs/kf/wp-8386-01/kf_result.json` | 结果信封（package_id / task_type / report_id / provenance / outputs）；`sha256:a3526a5cfe0983f9866a7229c06039b8625a6fcaec8fd4f526490b3ea97e1a2b` |
| `docs/kf/wp-8386-01/verification.json` | 10 项验收自检逐项结果，overall = **PASS** |
| `docs/kf/wp-8386-01/figures/fig_asset_inventory.png` | 图 1 资产类别 × 可解析状态堆叠条形图 |
| `docs/kf/wp-8386-01/figures/fig_locator_coverage.png` | 图 2 逐资产字符区间定位地图（覆盖 20879 字符全文） |
| `docs/kf/wp-8386-01/figures/figures.sha256.json` | 图件 sha256（fig_asset_inventory.png=sha256:b2ce9c6dba8…, fig_locator_coverage.png=sha256:cb083de6d34…） |
| `runs/wp-8386-01/report_8386.md` / `.json` | 源证据快照（markdown 与 API 原始响应），供平台独立重算哈希 |
| `schemas/asset_manifest.v1.1.schema.json` | 本次用的形状 schema（v1 用 const 钉死 wp-448-01，故新增参数化 v1.1，旧文件未改） |
| `scripts/kf_wp8386_01_fetch.py` / `kf_wp8386_01_register.py` / `kf_wp8386_01_report.py` | 取证 / 登记+校验+出图 / 渲染+发布 |
| `tests/test_kf_wp8386_01.py` | 14 项不变量测试（含 4 个反向对照） |

**资产类别计数**：`{"document": 1, "heading": 1, "regulation_reference": 1, "parameter_table": 1, "parameter_set": 1, "clause_register": 1, "evidence_gate_statement": 1, "formula_block": 4, "numeric_anchor": 1, "solver_declaration": 1, "verification_path": 1, "criteria_table": 1, "data_table": 5, "figure_set": 1, "data_artifact_reference": 1, "source_code_reference": 1, "test_reference": 1, "api_surface": 1, "vcs_reference": 1, "repro_command_block": 1, "limitation_set": 1, "external_evidence_gap": 1, "figure_declaration_absent": 1}`

## ④ 证据定位表（asset → 原文逐字切片）

下表每个 `quote` 都是报告 8386 markdown 的**唯一子串**，区间为 `[start_char, end_char)`、
行号为反推值；平台可独立重算 sha256 与子串定位。

| asset_id | class | resolution | char span (line) | 原文片段（原样切片） |
|---|---|---|---|---|
| A01 | document | resolved_in_source | 0–20879 (L1–L485) | `# FuelEU Maritime 柔性机制三件套：RFNBO 双倍乘子 + 岸电 OPS 零排放抵扣 + 存借跨年滚动` |
| A02 | heading | resolved_in_source | 384–394 (L11–L11) | `## 1  案例介绍` |
| A03 | regulation_reference | resolved_in_source | 413–485 (L15–L15) | `FuelEU Maritime（Regulation (EU) 2023/1805）把船用能量（燃料 + 岸电）的 **Well-to-Wake` |
| A04 | parameter_table | resolved_in_source | 1123–1180 (L34–L34) | `\| 船 \| 类型 \| GT \| MCR [kW] \| 年度能量 [TJ] \| 燃料切换档（份额） \| 靠港电量 \|` |
| A05 | parameter_set | resolved_in_source | 1661–1694 (L40–L40) | `仿真窗口：2025–2035（11 年），结算粒度 = 船 × 年` |
| A06 | clause_register | resolved_in_source | 1834–1883 (L48–L48) | `\| 条款 ID \| 条款号（转录） \| 表号 \| 机制证据 \| 条款核实 \| 可进入可绑定判定 \|` |
| A07 | evidence_gate_statement | resolved_in_source | 2603–2662 (L57–L57) | `` 严格模式（`strict_legal=True`）把全部 WITHHELD 条款移出判定：乘子退回 1、OPS 按声明 `` |
| A08 | formula_block | resolved_in_source | 2902–2955 (L72–L72) | `E_eff  = Σ_k w_k·E_k        （合规能量，w=2 对 RFNBO，w=1 其它）` |
| A09 | formula_block | resolved_in_source | 3060–3110 (L80–L80) | `GI(m)  = (m·s·g_r + o·g_o + q·g_q) / (m·s + o + q)` |
| A10 | numeric_anchor | resolved_in_source | 3359–3405 (L90–L90) | `` `rate = 2400/(3.73756e6) = 6.42e-04 EUR/gCO2e` `` |
| A11 | formula_block | resolved_in_source | 3487–3570 (L97–L97) | `cb_t + bank_in_t + borrow_in_t − repay_out_t − bank_out_t − spill_t + deficit_t = 0` |
| A12 | formula_block | resolved_in_source | 3744–3769 (L102–L102) | `deficit_t = m_(t−1) − m_t` |
| A13 | solver_declaration | resolved_in_source | 4068–4105 (L109–L109) | `` （本环境无 `highspy` 包，走 SciPy 的 HiGHS 绑定） `` |
| A14 | verification_path | resolved_in_source | 4140–4171 (L113–L113) | `对小规模（3 船 × 3 年）用**顶点穷尽枚举**复核 LP` |
| A15 | criteria_table | resolved_in_source | 4671–4694 (L131–L131) | `\| 判据 \| 结果数字 \| 阈值 \| 结论 \|` |
| A16 | data_table | resolved_in_source | 5252–5354 (L143–L143) | `\| 船 \| 年 \| E_phys [MWh] \| E_eff [MWh] \| GHGI \| GI_L \| CB [1e9 gCO2e] \| RFNBO 份额 \| OPS 份额 \| 单年罚金 [EUR] \|` |
| A17 | data_table | resolved_in_source | 8092–8149 (L181–L181) | `\| 船 \| 年 \| GHGI（严格模式） \| CB [1e9 gCO2e] \| 单年罚金 [EUR] \| 判决 \|` |
| A18 | data_table | resolved_in_source | 10122–10178 (L222–L222) | `\| 配置 \| LP 状态 \| 累计罚金 [EUR] \| 相对无柔性降幅 \| 变量数 \| 等式数 \| 生效条款 \|` |
| A19 | data_table | resolved_in_source | 15881–15954 (L341–L341) | `\| 扰动 \| GWP \| 能量缩放 \| 无柔性罚金 [EUR] \| 单船柔性罚金 [EUR] \| 船队柔性罚金 [EUR] \| 平均 GHGI \|` |
| A20 | data_table | resolved_in_source | 16316–16342 (L352–L352) | `\| κ \| 硬模式状态 \| 累计罚金 [EUR] \|` |
| A21 | figure_set | referenced_unresolved | 16931–17022 (L377–L377) | `![fig_ghgie_trajectory.png](../../artifacts/fueleu_maritime_m7061/fig_ghgie_trajectory.png)` |
| A22 | data_artifact_reference | referenced_unresolved | 20653–20708 (L482–L482) | `` `artifacts/fueleu_maritime_m7061/acceptance.json`（程序化生成 `` |
| A23 | source_code_reference | referenced_unresolved | 20312–20386 (L477–L477) | `` `backend/modules/fueleu_maritime/`（clauses / energy / compliance_balance / `` |
| A24 | test_reference | referenced_unresolved | 20590–20645 (L481–L481) | `` `backend/modules/fueleu_maritime/tests/`（74 项，覆盖判据 a–g） `` |
| A25 | api_surface | referenced_unresolved | 20816–20878 (L485–L485) | `` `/api/v1/fueleu-maritime/{registry,case,compliance,portfolio}` `` |
| A26 | vcs_reference | referenced_unresolved | 161–180 (L4–L4) | `` **基线提交**：`7017a623` `` |
| A27 | repro_command_block | resolved_in_source | 19889–19940 (L460–L460) | `python3 artifacts/fueleu_maritime_m7061/run_case.py` |
| A28 | limitation_set | resolved_in_source | 20121–20166 (L468–L468) | `- Art. 23(2) 连续不合规罚金加成（NOT_SUPPORTED，累计罚金为下界）` |
| A29 | external_evidence_gap | referenced_unresolved | 19360–19436 (L442–L442) | `\| 法规限值台阶 / 罚金单价 vs EUR-Lex 原文 \| WITHHELD_EXTERNAL \| 离线无外网，无法核对原文 \| 无基准（声明） \|` |
| A30 | figure_declaration_absent | declared_absent | 16795–16822 (L373–L373) | `（本节点是 0 维法规账务模型，没有空间场量，故无云图` |

**锚点之外的机器探针明细**（29 个页内定位资产中有 8 个还需额外探针：外部路径 / HTTP / git / 内容扫描）：

| asset_id | resolution | check | result |
|---|---|---|---|
| A21 | referenced_unresolved | `worktree_path_exists:artifacts/fueleu_maritime_m7061/fig_ghgie_trajectory.png` | absent |
| A22 | referenced_unresolved | `worktree_path_exists:artifacts/fueleu_maritime_m7061/acceptance.json` | absent |
| A23 | referenced_unresolved | `worktree_path_exists:backend/modules/fueleu_maritime` | absent |
| A24 | referenced_unresolved | `worktree_path_exists:backend/modules/fueleu_maritime/tests` | absent |
| A25 | referenced_unresolved | `http_probe:http://127.0.0.1:8002/api/v1/fueleu-maritime/registry` | unresolved |
| A26 | referenced_unresolved | `git_cat_file:7017a623` | unresolved |
| A29 | referenced_unresolved | `worktree_path_exists:artifacts/fueleu_maritime_m7061/eurlex` | absent |
| A30 | declared_absent | `scan_image_references_for_fieldmap(md)` | absent |

## ⑤ 注意点与局限

1. **本工序不产生知识**：`claims = []` 由契约 `objective`（只有 `register_assets`、`classify_report_type=false`）
   决定，不是为了填指标。报告里的数值结论（判据 a–g、罚金曲线）一律**未复核**，属下游工序。
2. **"resolved_in_source" 只表示"原文里能逐字定位"，不表示内容为真**。例如 A03 的法规号
   `Regulation (EU) 2023/1805` 与 A06 的条款号都是**报告作者的转录**，原文自己标了
   `WITHHELD_EXTERNAL`（离线无 EUR-Lex 通道）；本工序原样登记，不复核、不加分、不改判。
3. **7 个 `referenced_unresolved` 是真实缺口，不是遗漏**：6 张图 PNG、`acceptance.json`、
   `backend/modules/fueleu_maritime/`、测试目录、API 路由、上游提交 `7017a623` 全部位于上游仓
   `ship-performance-platform`，本工作树（TensorKnowledge）里不存在；API 路由实测
   `http_probe` 非 2xx、`git cat_file` 返回 128 —— 我登记的是"引用了但此处不可解析"，没有替换成猜测值。
4. **A21 的存在性判定用"本工作树"口径**：Petrel 式跨仓工件登记需要跨仓路径，本单无权访问上游仓，
   因此"absent"仅代表本工作树；此局限已写进 `note`，供下游 05 工序复核。
5. **A30（无云图）是 `declared_absent`**：原文自述"0 维法规账务模型，没有空间场量"，探针扫
   6 条图片引用 0 条命中场量词。**未据此推断能力缺失**——0 维账务模型本来就不该有云图。
6. **`chars` 用 Python 字符数、`bytes_utf8` 用字节数**，中文混排下二者不同
   （20879 vs 27959）；契约 `chars: 20879`
   与字符数口径一致，若平台按字节比对会不匹配——这点已在 `source` 里显式分开记录。
7. **本单一处未改的既有缺陷**：`tests/test_kf_wp448.py` 在本工作树 13 项失败/报错，原因是它依赖
   `runs/wp-448-01/`（未随仓提交，`.gitignore` 丢弃 `artifacts/**`）——与本单无关，按"最小改动"
   原则未修，仅如实记录。

## ⑥ 自检：逐条对照 acceptance

| # | acceptance 项 | 结果 | 证据 |
|---|---|---|---|
| 1 | `valid_json` | ☑ PASS | manifest/envelope 均可 `json.loads` |
| 2 | `schema_pass` | ☑ PASS | `schemas/asset_manifest.v1.1.schema.json`；信封另过 `schemas/kf_result.v1.schema.json` |
| 3 | `source_locator_resolvable` | ☑ PASS | 重取 markdown 后 30/30 个 locator 切片相等且唯一 |
| 4 | `source_hash_matches` | ☑ PASS | `sha256:4104143f4653a88fd9df9c12b93d3d05d42592aca5c835749a34f21ad85761af` == 契约值 |
| 5 | `no_duplicate_ids` | ☑ PASS | 30 个 id 唯一（含负控测试） |
| 6 | `all_claims_have_evidence_or_explicit_unresolved_status` | ☑ PASS | `claims=[]`，check_claims 无违例 |
| + | `resolution_matches_probe`（额外自加） | ☑ PASS | 30 条声明全部由探针结果支撑 |
| + | `no_verified_marks`（额外自加） | ☑ PASS | 结构化扫描未见 verified 标记 |
| + | `counts_consistent`（额外自加） | ☑ PASS | 22+7+1 = 30 |

**无失败项**。上表 9 项全部由 `verification.json` 机器生成，未手写判断；
`overall = PASS`。**verification 本身仍由平台门复算**，本报告不代替它。

### 复跑（一键）

```bash
# 0) 依赖：python3 + jsonschema + matplotlib；环境变量 TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS
cd <worktree 根>
python3 scripts/kf_wp8386_01_fetch.py                    # 取证 + 哈希核对（不一致即退出）
python3 scripts/kf_wp8386_01_register.py all             # build + envelope + verify + figure
python3 -m pytest tests/test_kf_wp8386_01.py -q          # 14 项不变量测试
python3 scripts/kf_wp8386_01_report.py render            # 重渲染本报告
```

### ⑥ 附：结果 JSON（本报告唯一一个 json 代码块，逐字等于 `docs/kf/wp-8386-01/kf_result.json`）

```json
{
  "package_id": "wp-8386-01",
  "task_type": "01-asset-registration",
  "report_id": "8386",
  "provenance": {
    "source_hash": "sha256:4104143f4653a88fd9df9c12b93d3d05d42592aca5c835749a34f21ad85761af",
    "source_field": "markdown",
    "producer": "kf-worker/m15621",
    "emitted_at": "2026-11-12T01:33:22.971381+00:00",
    "notes": "hash recomputed from GET /api/v1/tensor/reports/8386 at build time and compared to the contract value; locators are raw markdown slices"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-8386-01",
      "task_type": "01-asset-registration",
      "report_id": "8386",
      "source": {
        "uri": "tensor://reports/8386",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "4104143f4653a88fd9df9c12b93d3d05d42592aca5c835749a34f21ad85761af",
        "chars": 20879,
        "bytes_utf8": 27959,
        "title": "[m7061] FuelEU 柔性三件套：RFNBO 乘子 + 岸电 OPS 抵扣 + 存借跨年滚动（判据 a–g 全 PASS）",
        "scenario_key": "fueleu_flexible_multiyear",
        "platform_figures": [
          "fig_ghgie_trajectory",
          "fig_energy_split",
          "fig_mechanism_stack",
          "fig_bank_ledger",
          "fig_borrow_cap",
          "fig_lp_vs_enum"
        ],
        "platform_tags": [
          "FuelEU",
          "RFNBO",
          "OPS岸电",
          "banking",
          "borrowing",
          "HiGHS",
          "线性规划",
          "碳强度",
          "绿色航行",
          "m7061"
        ],
        "title_matches_contract": true,
        "scenario_matches_contract": true,
        "chars_match_contract": true
      },
      "counts": {
        "assets": 30,
        "by_class": {
          "document": 1,
          "heading": 1,
          "regulation_reference": 1,
          "parameter_table": 1,
          "parameter_set": 1,
          "clause_register": 1,
          "evidence_gate_statement": 1,
          "formula_block": 4,
          "numeric_anchor": 1,
          "solver_declaration": 1,
          "verification_path": 1,
          "criteria_table": 1,
          "data_table": 5,
          "figure_set": 1,
          "data_artifact_reference": 1,
          "source_code_reference": 1,
          "test_reference": 1,
          "api_surface": 1,
          "vcs_reference": 1,
          "repro_command_block": 1,
          "limitation_set": 1,
          "external_evidence_gap": 1,
          "figure_declaration_absent": 1
        },
        "by_resolution": {
          "resolved_in_source": 22,
          "referenced_unresolved": 7,
          "declared_absent": 1
        },
        "resolved_in_source": 22,
        "referenced_unresolved": 7,
        "declared_absent": 1
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "document",
          "label": "报告 8386 全篇 markdown（登记对象本体）",
          "in_report_section": "全文",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 20879,
            "start_line": 1,
            "end_line": 485,
            "quote": "# FuelEU Maritime 柔性机制三件套：RFNBO 双倍乘子 + 岸电 OPS 零排放抵扣 + 存借跨年滚动",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "document_sha256_span_covers_whole_markdown",
            "result": "resolved"
          },
          "note": "locator.method=document：span=整篇 [0, len)，quote=首行标题（唯一）"
        },
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "§1 案例介绍（章节锚）",
          "in_report_section": "§1",
          "locator": {
            "method": "char_span",
            "start_char": 384,
            "end_char": 394,
            "start_line": 11,
            "end_line": 11,
            "quote": "## 1  案例介绍",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": "章节标题即可定位小节起点"
        },
        {
          "asset_id": "A03",
          "asset_class": "regulation_reference",
          "label": "FuelEU Maritime 法规出处与计罚口径（2400 EUR/t VLSFO）",
          "in_report_section": "§1.1",
          "locator": {
            "method": "char_span",
            "start_char": 413,
            "end_char": 485,
            "start_line": 15,
            "end_line": 15,
            "quote": "FuelEU Maritime（Regulation (EU) 2023/1805）把船用能量（燃料 + 岸电）的 **Well-to-Wake",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": "法规号以转录形式出现在原文，未与 EUR-Lex 核对（见 A29）"
        },
        {
          "asset_id": "A04",
          "asset_class": "parameter_table",
          "label": "三船声明输入参数表（GT / MCR / 年度能量 / 燃料切换档 / 靠港电量）",
          "in_report_section": "§1.2",
          "locator": {
            "method": "char_span",
            "start_char": 1123,
            "end_char": 1180,
            "start_line": 34,
            "end_line": 34,
            "quote": "| 船 | 类型 | GT | MCR [kW] | 年度能量 [TJ] | 燃料切换档（份额） | 靠港电量 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": "原文自注 declared（非实测），本工序只登记不评测"
        },
        {
          "asset_id": "A05",
          "asset_class": "parameter_set",
          "label": "仿真窗口与结算单元数（2025–2035 / 33 单元）",
          "in_report_section": "§1.2",
          "locator": {
            "method": "char_span",
            "start_char": 1661,
            "end_char": 1694,
            "start_line": 40,
            "end_line": 40,
            "quote": "仿真窗口：2025–2035（11 年），结算粒度 = 船 × 年",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": ""
        },
        {
          "asset_id": "A06",
          "asset_class": "clause_register",
          "label": "条款证据登记表（6 条柔性条款 × 机制证据/条款核实/可绑定判定）",
          "in_report_section": "§1.3",
          "locator": {
            "method": "char_span",
            "start_char": 1834,
            "end_char": 1883,
            "start_line": 48,
            "end_line": 48,
            "quote": "| 条款 ID | 条款号（转录） | 表号 | 机制证据 | 条款核实 | 可进入可绑定判定 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": "表内 6 条均 citation_verification=WITHHELD_EXTERNAL"
        },
        {
          "asset_id": "A07",
          "asset_class": "evidence_gate_statement",
          "label": "严格模式（strict_legal）证据闸声明与 0 可绑定判定",
          "in_report_section": "§1.3",
          "locator": {
            "method": "char_span",
            "start_char": 2603,
            "end_char": 2662,
            "start_line": 57,
            "end_line": 57,
            "quote": "严格模式（`strict_legal=True`）把全部 WITHHELD 条款移出判定：乘子退回 1、OPS 按声明",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": ""
        },
        {
          "asset_id": "A08",
          "asset_class": "formula_block",
          "label": "能量流层代数定义（E_phys / E_eff / G_eff / GHGI）",
          "in_report_section": "§2.1",
          "locator": {
            "method": "char_span",
            "start_char": 2902,
            "end_char": 2955,
            "start_line": 72,
            "end_line": 72,
            "quote": "E_eff  = Σ_k w_k·E_k        （合规能量，w=2 对 RFNBO，w=1 其它）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": "公式块；本工序不校验其正确性（属工序 03/04）"
        },
        {
          "asset_id": "A09",
          "asset_class": "formula_block",
          "label": "GHGI 闭式解与乘子导数（判据 a 的解析锚）",
          "in_report_section": "§2.1",
          "locator": {
            "method": "char_span",
            "start_char": 3060,
            "end_char": 3110,
            "start_line": 80,
            "end_line": 80,
            "quote": "GI(m)  = (m·s·g_r + o·g_o + q·g_q) / (m·s + o + q)",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": ""
        },
        {
          "asset_id": "A10",
          "asset_class": "numeric_anchor",
          "label": "罚金换算率 rate = 2400/3.73756e6 = 6.42e-04 EUR/gCO2e",
          "in_report_section": "§2.2",
          "locator": {
            "method": "char_span",
            "start_char": 3359,
            "end_char": 3405,
            "start_line": 90,
            "end_line": 90,
            "quote": "`rate = 2400/(3.73756e6) = 6.42e-04 EUR/gCO2e`",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": ""
        },
        {
          "asset_id": "A11",
          "asset_class": "formula_block",
          "label": "跨年账本闭合式（含 deficit 符号 +1）",
          "in_report_section": "§2.3",
          "locator": {
            "method": "char_span",
            "start_char": 3487,
            "end_char": 3570,
            "start_line": 97,
            "end_line": 97,
            "quote": "cb_t + bank_in_t + borrow_in_t − repay_out_t − bank_out_t − spill_t + deficit_t = 0",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": "§5 注意点 1 记录了该符号误写过的历史坑"
        },
        {
          "asset_id": "A12",
          "asset_class": "formula_block",
          "label": "纯 banking 解析解（不依赖 LP 的独立锚）",
          "in_report_section": "§2.3",
          "locator": {
            "method": "char_span",
            "start_char": 3744,
            "end_char": 3769,
            "start_line": 102,
            "end_line": 102,
            "quote": "deficit_t = m_(t−1) − m_t",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": ""
        },
        {
          "asset_id": "A13",
          "asset_class": "solver_declaration",
          "label": "求解器与其绑定路径（scipy.optimize.linprog HiGHS）",
          "in_report_section": "§2.4",
          "locator": {
            "method": "char_span",
            "start_char": 4068,
            "end_char": 4105,
            "start_line": 109,
            "end_line": 109,
            "quote": "（本环境无 `highspy` 包，走 SciPy 的 HiGHS 绑定）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": "同字符串裸写形式在 §头 与 §2.4 各出现一次，故锚点取较长唯一串"
        },
        {
          "asset_id": "A14",
          "asset_class": "verification_path",
          "label": "顶点穷尽枚举独立复核路径（numpy 仅用 linalg）",
          "in_report_section": "§2.5",
          "locator": {
            "method": "char_span",
            "start_char": 4140,
            "end_char": 4171,
            "start_line": 113,
            "end_line": 113,
            "quote": "对小规模（3 船 × 3 年）用**顶点穷尽枚举**复核 LP",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": ""
        },
        {
          "asset_id": "A15",
          "asset_class": "criteria_table",
          "label": "机器可算判据总表（a–g，全部 PASS）",
          "in_report_section": "§3.1",
          "locator": {
            "method": "char_span",
            "start_char": 4671,
            "end_char": 4694,
            "start_line": 131,
            "end_line": 131,
            "quote": "| 判据 | 结果数字 | 阈值 | 结论 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": ""
        },
        {
          "asset_id": "A16",
          "asset_class": "data_table",
          "label": "逐年逐船合规余额表（33 行 × 10 列）",
          "in_report_section": "§3.2",
          "locator": {
            "method": "char_span",
            "start_char": 5252,
            "end_char": 5354,
            "start_line": 143,
            "end_line": 143,
            "quote": "| 船 | 年 | E_phys [MWh] | E_eff [MWh] | GHGI | GI_L | CB [1e9 gCO2e] | RFNBO 份额 | OPS 份额 | 单年罚金 [EUR] |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": "33 个结算单元逐行在场"
        },
        {
          "asset_id": "A17",
          "asset_class": "data_table",
          "label": "严格模式对照表（判决恒为 WITHHELD）",
          "in_report_section": "§3.2b",
          "locator": {
            "method": "char_span",
            "start_char": 8092,
            "end_char": 8149,
            "start_line": 181,
            "end_line": 181,
            "quote": "| 船 | 年 | GHGI（严格模式） | CB [1e9 gCO2e] | 单年罚金 [EUR] | 判决 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": ""
        },
        {
          "asset_id": "A18",
          "asset_class": "data_table",
          "label": "机制阶梯表（no_flex → fleet_pool+bank+borrow）",
          "in_report_section": "§3.3",
          "locator": {
            "method": "char_span",
            "start_char": 10122,
            "end_char": 10178,
            "start_line": 222,
            "end_line": 222,
            "quote": "| 配置 | LP 状态 | 累计罚金 [EUR] | 相对无柔性降幅 | 变量数 | 等式数 | 生效条款 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": ""
        },
        {
          "asset_id": "A19",
          "asset_class": "data_table",
          "label": "灵敏度表（energy ±30% / GWP20 vs GWP100）",
          "in_report_section": "§3.5",
          "locator": {
            "method": "char_span",
            "start_char": 15881,
            "end_char": 15954,
            "start_line": 341,
            "end_line": 341,
            "quote": "| 扰动 | GWP | 能量缩放 | 无柔性罚金 [EUR] | 单船柔性罚金 [EUR] | 船队柔性罚金 [EUR] | 平均 GHGI |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": ""
        },
        {
          "asset_id": "A20",
          "asset_class": "data_table",
          "label": "κ 灵敏度与硬模式负控表",
          "in_report_section": "§3.6",
          "locator": {
            "method": "char_span",
            "start_char": 16316,
            "end_char": 16342,
            "start_line": 352,
            "end_line": 352,
            "quote": "| κ | 硬模式状态 | 累计罚金 [EUR] |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": ""
        },
        {
          "asset_id": "A21",
          "asset_class": "figure_set",
          "label": "6 张结果图（PNG，报告 §4 逐图引用）",
          "in_report_section": "§4",
          "locator": {
            "method": "char_span",
            "start_char": 16931,
            "end_char": 17022,
            "start_line": 377,
            "end_line": 377,
            "quote": "![fig_ghgie_trajectory.png](../../artifacts/fueleu_maritime_m7061/fig_ghgie_trajectory.png)",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists:artifacts/fueleu_maritime_m7061/fig_ghgie_trajectory.png",
            "result": "absent",
            "kind": "worktree_fs"
          },
          "note": "PNG 落在上游仓 ship-performance-platform 的 artifacts/ 下，本工作树不含"
        },
        {
          "asset_id": "A22",
          "asset_class": "data_artifact_reference",
          "label": "acceptance.json（判据数字与每图 sha256 的机器产物）",
          "in_report_section": "§8",
          "locator": {
            "method": "char_span",
            "start_char": 20653,
            "end_char": 20708,
            "start_line": 482,
            "end_line": 482,
            "quote": "`artifacts/fueleu_maritime_m7061/acceptance.json`（程序化生成",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists:artifacts/fueleu_maritime_m7061/acceptance.json",
            "result": "absent",
            "kind": "worktree_fs"
          },
          "note": "上游仓产物，本工作树不含"
        },
        {
          "asset_id": "A23",
          "asset_class": "source_code_reference",
          "label": "实现模块目录 backend/modules/fueleu_maritime/",
          "in_report_section": "§8",
          "locator": {
            "method": "char_span",
            "start_char": 20312,
            "end_char": 20386,
            "start_line": 477,
            "end_line": 477,
            "quote": "`backend/modules/fueleu_maritime/`（clauses / energy / compliance_balance /",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists:backend/modules/fueleu_maritime",
            "result": "absent",
            "kind": "worktree_fs"
          },
          "note": "上游仓目录，本工作树不含"
        },
        {
          "asset_id": "A24",
          "asset_class": "test_reference",
          "label": "模块测试集（74 项，覆盖判据 a–g）",
          "in_report_section": "§8",
          "locator": {
            "method": "char_span",
            "start_char": 20590,
            "end_char": 20645,
            "start_line": 481,
            "end_line": 481,
            "quote": "`backend/modules/fueleu_maritime/tests/`（74 项，覆盖判据 a–g）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists:backend/modules/fueleu_maritime/tests",
            "result": "absent",
            "kind": "worktree_fs"
          },
          "note": "上游仓目录，本工作树不含"
        },
        {
          "asset_id": "A25",
          "asset_class": "api_surface",
          "label": "HTTP 路由声明 /api/v1/fueleu-maritime/{...}",
          "in_report_section": "§8",
          "locator": {
            "method": "char_span",
            "start_char": 20816,
            "end_char": 20878,
            "start_line": 485,
            "end_line": 485,
            "quote": "`/api/v1/fueleu-maritime/{registry,case,compliance,portfolio}`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "http_probe:http://127.0.0.1:8002/api/v1/fueleu-maritime/registry",
            "result": "unresolved",
            "http_status": 404,
            "kind": "http"
          },
          "note": "实测探针见 manifest 的 resolution_check（http_status 非 2xx）"
        },
        {
          "asset_id": "A26",
          "asset_class": "vcs_reference",
          "label": "上游基线提交 7017a623",
          "in_report_section": "报告头",
          "locator": {
            "method": "char_span",
            "start_char": 161,
            "end_char": 180,
            "start_line": 4,
            "end_line": 4,
            "quote": "**基线提交**：`7017a623`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "git_cat_file:7017a623",
            "result": "unresolved",
            "git_returncode": 128,
            "kind": "git"
          },
          "note": "本仓（TensorKnowledge）对象库不含该提交，git cat-file 探针结果见 resolution_check"
        },
        {
          "asset_id": "A27",
          "asset_class": "repro_command_block",
          "label": "复跑命令块（pytest 74 项 / run_case.py / gen_report.py）",
          "in_report_section": "§7",
          "locator": {
            "method": "char_span",
            "start_char": 19889,
            "end_char": 19940,
            "start_line": 460,
            "end_line": 460,
            "quote": "python3 artifacts/fueleu_maritime_m7061/run_case.py",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": "命令块在场，但其执行依赖 A22/A23 所在上游仓（本工作树不可执行）"
        },
        {
          "asset_id": "A28",
          "asset_class": "limitation_set",
          "label": "NOT_SUPPORTED 诚实清单（Art. 23(2) 加成 / 多期偿还）",
          "in_report_section": "§7",
          "locator": {
            "method": "char_span",
            "start_char": 20121,
            "end_char": 20166,
            "start_line": 468,
            "end_line": 468,
            "quote": "- Art. 23(2) 连续不合规罚金加成（NOT_SUPPORTED，累计罚金为下界）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "unique_substring_anchor_in_markdown",
            "result": "resolved"
          },
          "note": "原文自述不支持项，本工序原样登记不改判"
        },
        {
          "asset_id": "A29",
          "asset_class": "external_evidence_gap",
          "label": "EUR-Lex 原文核对缺口（WITHHELD_EXTERNAL 行）",
          "in_report_section": "§6",
          "locator": {
            "method": "char_span",
            "start_char": 19360,
            "end_char": 19436,
            "start_line": 442,
            "end_line": 442,
            "quote": "| 法规限值台阶 / 罚金单价 vs EUR-Lex 原文 | WITHHELD_EXTERNAL | 离线无外网，无法核对原文 | 无基准（声明） |",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists:artifacts/fueleu_maritime_m7061/eurlex",
            "result": "absent",
            "kind": "worktree_fs"
          },
          "note": "离线无外网通道，登记为不可解析，不编造核对结论"
        },
        {
          "asset_id": "A30",
          "asset_class": "figure_declaration_absent",
          "label": "空间场量云图声明缺席（0 维法规账务模型）",
          "in_report_section": "§4",
          "locator": {
            "method": "char_span",
            "start_char": 16795,
            "end_char": 16822,
            "start_line": 373,
            "end_line": 373,
            "quote": "（本节点是 0 维法规账务模型，没有空间场量，故无云图",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "scan_image_references_for_fieldmap(md)",
            "result": "absent",
            "image_refs": 6,
            "fieldmap_like": [],
            "absence_word_count": 1,
            "kind": "content_scan"
          },
          "note": "原文显式声明无云图；本工序不据此推断任何缺失"
        }
      ],
      "claims": [],
      "claims_note": "objective.register_assets only; classify_report_type=false and no extraction -- an empty claims[] is the complete, honest result, not a missing one.",
      "integrity": {
        "quote_uniqueness": "each locator.quote anchored by a string occurring exactly once",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "anchors_checked": 30
      },
      "producer": "kf-worker/m15621"
    }
  },
  "claims": []
}
```
