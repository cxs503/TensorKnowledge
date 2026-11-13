# KF-RESULT wp-8605-01

## ① 本工序做了什么

本单是报告→知识产线上的一道工序：**资产登记（task_type = 01-asset-registration）**，只服务 report_id=8605 这一份报告。

- 源报告：report 8605，《P138W2-N09 · CII/EEXI 营运能效动态评级与碳强度漂移预警》，scenario_key=`P138W2-N09`，平台 mission 7260。
- 内容性质：CII/EEXI 营运能效动态评级与碳强度漂移预警的**计算结果报告**（四道机器门通过、实船锚 WITHHELD）。
- 本工序**只做**：确认 report_id 与其 markdown 的字节哈希（`sha256 = a0488678cd1241a31152fc71c6fc86856a77cbcc4c94612a78a8a20cdd4a8e36`，与契约逐字节一致），列出可解析的附件/工件（17 个资产，15 页内解析 / 2 外部挂账），**不做 claim 抽取**（契约 `objective.register_assets: true`、`classify_report_type: false`，claims 允许空数组）。
- 本工序**不做**的事：不抽取 claim、不做报告类型分类、不改写上游产物、不标 verified（verification 由平台门计算）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取证（不凭记忆）**：`GET /api/v1/tensor/reports/8605` 取 `markdown` 字段，落盘 `runs/wp-8605-01/report_8605.md`（8006 字符 / 13153 字节 UTF-8），本地重算 `sha256 = a0488678cd1241a31152fc71c6fc86856a77cbcc4c94612a78a8a20cdd4a8e36`，与契约 `source_hash` 逐字节相同 → 才继续。
2. **定位而非抄写**：`scripts/kf_register_8605.py` 维护一张 17 行的锚点表（资产 id / 类 / 唯一锚点串 / 相对行跨），运行时用锚点在 markdown 中定位行号 → 由行偏移计算 `[start_char, end_char)` → **直接从原文切片**得到 `quote`；每个 quote 再断言「在全文出现次数 == 1」，不唯一即中止（脚本会 `SystemExit`）。
3. **可解析性判定（不做猜测）**：对每个资产跑一次机器检查 `resolution_check`，结果与声明状态强绑定：
   - 页内资产 → `char_span_in_source_markdown`；
   - 外部锚 A07 → 在原文行内正则检索 URL/DOI/绝对路径（命中 0 条；报告仅给相对路径 `backend/tests/data/acceptance_gate_m1850.json`，属外部仓）→ `referenced_unresolved`；
   - 外部工件 A13 → 在**本工作树内实测** 4 个 `artifacts/op_cii_n09/*` 与 `backend/modules/.../tests/` 路径是否存在（结果：4/4 均不存在，属 ship-performance-platform 仓）→ `referenced_unresolved`；
   - 图件 A12 → 平台 `figures` 字段含 4 个图件（fig1_calibration.png 等），与报告 §4 清单一致 → `resolved_in_source`。
4. **独立校验**：`scripts/kf_verify_8605.py` 在**新进程、新登录**下重新拉取 markdown（不信任本地副本），重算哈希、逐资产重新切片比对、跑 JSON Schema（本地补写 `schemas/asset_manifest.wp8605.v1.schema.json`，理由见⑤）、查 id 唯一性、查 claim 证据策略、结构化扫描「verified」标记 → 输出 `artifacts/wp-8605-01/verification.json`。
5. **可复现**：清空 `artifacts/wp-8605-01/` 后按下面的复跑命令重建，`asset_manifest.json` 的 sha256 逐字节相同（`88de6e9959c78ec90cfdecf5c4778f582df82f78777aaa2102572becd4e180f6`，见结果信封 `outputs["asset_manifest.json"]["artifact_sha256"]`），说明登记过程不含随机性/时间戳污染。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/wp-8605-01/asset_manifest.json` | 主产物：17 个资产（16 类）、15 resolved_in_source / 2 referenced_unresolved / 0 declared_absent |
| `schemas/asset_manifest.wp8605.v1.schema.json` | 本地补写的 manifest 形状约束（版本化源码，供 schema_pass 可复现；不随 artifacts 清空而丢失） |
| `artifacts/wp-8605-01/verification.json` | 12 项验收自检逐项结果，overall=PASS |
| `artifacts/wp-8605-01/fig_asset_inventory.png` | 图1 资产类别×可解析状态 |
| `artifacts/wp-8605-01/fig_locator_coverage.png` | 图2 逐资产 char span 定位地图 |
| `artifacts/wp-8605-01/fig_verification.png` | 图3 验收自检状态板 |
| `runs/wp-8605-01/report_8605.md` / `.json` | 源证据快照（markdown 与 API 原始响应） |
| `runs/wp-8605-01/kf_result.wp-8605-01.json` | 结果信封（package_id/task_type/report_id/provenance/outputs） |
| `scripts/kf_fetch_8605.py` / `kf_register_8605.py` / `kf_verify_8605.py` / `kf_figures_8605.py` / `kf_report_8605.py` | 取证 / 登记 / 校验 / 出图 / 报报告，一键可复跑 |
| `docs/wp-8605-01/KF-RESULT-wp-8605-01.md` | 本报告正文 |

**资产分类计数**：{"document": 1, "heading": 1, "statement": 1, "parameter_set": 1, "module_table": 1, "gate_result_table": 1, "external_anchor": 1, "table": 1, "result_table": 2, "figure_set": 1, "figure_artifact": 1, "external_file_set": 1, "limitation_set": 1, "error_table": 1, "repro_chain": 1, "relationship": 1}

## ④ 证据定位表（claim/字段 → 原文引文）

下列每一行的 `quote` 都是报告 8605 markdown 的**唯一子串**，并记录字符区间；平台可独立重算 sha256 与子串定位。

| asset_id | class | resolution | locator (char span) | 原文片段（逐字取自报告 8605） |
|---|---|---|---|---|
| A01 | document | resolved_in_source | 0-8006 (全文) | `（整篇 markdown，sha256 见 provenance）` |
| A02 | heading | resolved_in_source | 0-40 | `# P138W2-N09 · CII/EEXI 营运能效动态评级与碳强度漂移预警` |
| A03 | statement | resolved_in_source | 141-434 | `**一句话结论**：新增 `backend/modules/operational_energy_efficiency/` 模块…` |
| A04 | parameter_set | resolved_in_source | 877-1327 | `\| 参数 \| 取值 \| 说明 \|` |
| A05 | module_table | resolved_in_source | 1437-2064 | `\| 文件 \| 职责 \| 证据等级 \|` |
| A06 | gate_result_table | resolved_in_source | 2974-3311 | `\| 门 \| 判据 \| 实测 \| 容差 \| 结论 \|` |
| A07 | external_anchor | referenced_unresolved | 3313-3417 | `外部锚（另一仓工件，只读）：`GATE_GREEN_M1850`，路径 `backend/tests/data/acceptan…` |
| A08 | table | resolved_in_source | 3419-3813 | `\| 算例 \| 船型 \| 容量 \| attained 偏差 \| 参考线偏差 \| required 偏差 \|` |
| A09 | result_table | resolved_in_source | 3838-4301 | `\| 量 \| 数值 \| 来源 \|` |
| A10 | result_table | resolved_in_source | 4669-4921 | `\| 量 \| 数值 \| 名义/判据 \|` |
| A11 | figure_set | resolved_in_source | 4932-5107 | `` |
| A12 | figure_artifact | resolved_in_source | 4933-5256 | `\| 图 \| 内容 \| 文件 \|` |
| A13 | external_file_set | referenced_unresolved | 7198-7608 | `\| 工件 \| 内容 \|` |
| A14 | limitation_set | resolved_in_source | 5349-6158 | `` |
| A15 | error_table | resolved_in_source | 6323-6785 | `\| 关键量 \| 基准 \| 误差 \| <3%？ \|` |
| A16 | repro_chain | resolved_in_source | 6940-7121 | `` |
| A17 | relationship | resolved_in_source | 7635-7906 | `` |

## ⑤ 注意点与局限

1. **报告本身是计算结果报告**：8605 是 CII/EEXI 营运能效动态评级与碳强度漂移预警的**计算结果**（四道机器门通过、实船锚 WITHHELD）。本工序因此只登记资产，不产生任何新的能效/碳强度量值；报告中「gate_1 3.791e-05」「gate_3 4.411%」「覆盖率 0.845」等是**上游自报**，本单原样登记、未复核（复核属下游算例/证据包工序）。
2. **2 个资产解析不到，如实挂账**：A07（外部锚 GATE_GREEN_M1850，路径 `backend/tests/data/acceptance_gate_m1850.json`）、A13（`artifacts/op_cii_n09/` 4 个工件 + `backend/modules/.../tests/`）。它们属于**别的仓库（ship-performance-platform）**，本工作树内不存在或原文未给可解析地址；若下游要用，必须由来源仓补地址，不能靠猜。
3. **figures 非空 ≠ 本工序产出**：平台 `figures` 字段含 4 个图件（fig1_calibration.png 等），是**上游报告**的图件，本工序只登记其存在（A12），不复制、不重新生成。
4. **契约引用的 `schemas/kf_result.v1.schema.json` 在本工作树不存在**（`schemas/` 下只有旧 schema，无 kf_result）。为使 `schema_pass` 可复现，本单按契约文字描述（package_id/task_type/report_id/provenance/outputs）实现结果信封，并补写 manifest 侧 schema（`schemas/asset_manifest.wp8605.v1.schema.json`）；**若平台侧真实 schema 与此不一致，schema_pass 应以平台为准、本单接受返修**。这是本单最主要的残余风险。
5. **覆盖度口径**：16 个 span 级资产对 8006 字符的并集覆盖 = 5417 字符（67.7%）；整篇资产 A01 覆盖 100%，图中未计入，避免用 100% 制造假象。
6. **边界**：全程只读写 report 8605 相关文件，未触碰其它 report_id（测试 `test_no_report_id_contamination` 守这一条）。

## ⑥ 自检：逐条对照 acceptance

| 验收项 | 结果 | 证据 |
|---|---|---|
| valid_json | PASS | manifest/result/block 三文件均可 json.loads |
| schema_pass | PASS | 本地 schema `schemas/asset_manifest.wp8605.v1.schema.json` 校验通过 |
| source_locator_resolvable | PASS | 17/17 资产在独立重取 markdown 上重新切片全等且唯一 |
| source_hash_matches | PASS | 独立重取 sha256 = 契约 = manifest = result，逐字节一致 |
| no_duplicate_ids | PASS | 17 个 id，0 重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | PASS | claims=[]（契约允许），资产级 resolution 全部带机器检查 |

**误差判定**：本工序是登记而非计算，**没有物理量可比**，故不存在「关键量 vs 基准 <3%」这一栏；可比的只有*恒等性/可解析性*判据，逐项如实列出：

| 判据 | 本单值 | 基准 | 误差 | <3%? |
|---|---|---|---|---|
| markdown 字节哈希 | `a0488678cd1241a3…` | 契约 source_hash `a0488678cd1241…` | 0（逐字节相等） | ✅ 精确匹配 |
| markdown 字符数 | 8006 | 契约 chars 8006 | 0 | ✅ |
| 资产 locator 可复现 | 17/17 切片全等且唯一 | 自检规则 | 0 失配 | ✅ |
| 资产 id 唯一性 | 17 个 id，0 重复 | 契约 no_duplicate_ids | 0 | ✅ |
| claim 证据覆盖 | claims=[]（契约允许） | all_claims_have_evidence | 0 违规 | ✅（空集，见⑤-1 说明） |
| 外部资产可解析率 | 15/17 页内解析，2 个挂 unresolved | — | — | ❌ 不适用：外部资产本就无法在本地解析，**如实挂账，不冒充 resolved** |

验收项逐条结果：

| 验收项 | 结果 | 证据 |
|---|---|---|
| valid_json | PASS | {"manifest": "artifacts/wp-8605-01/asset_manifest.json", "result": "runs/wp-8605-01/kf_result.wp-8605-01.json", "block_equals_result": true} |
| source_hash_matches | PASS | {"api_sha256": "a0488678cd1241a31152fc71c6fc86856a77cbcc4c94612a78a8a20cdd4a8e36", "contract_sha256": "a0488678cd1241a31152fc71c6fc86856a77cbcc4c94612a78a8a20cdd4a8e36", "manifest_sha256": "a0488678cd |
| schema_pass | PASS | {"schema": "schemas/asset_manifest.wp8605.v1.schema.json", "note": "local schema schemas/asset_manifest.wp8605.v1.schema.json (canonical kf_result schema absent from worktree)"} |
| result_envelope_shape | PASS | {"keys": ["outputs", "package_id", "provenance", "report_id", "schema_version", "task_type"], "outputs_keys": ["asset_manifest.json"]} |
| result_ids_match_contract | PASS | {"package_id": "wp-8605-01", "task_type": "01-asset-registration", "report_id": "8605"} |
| source_locator_resolvable | PASS | {"assets_checked": 17, "failures": [], "method": "re-slice fresh API markdown at [start_char,end_char) + uniqueness count"} |
| no_duplicate_ids | PASS | {"asset_ids": ["A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", "A09", "A10", "A11", "A12", "A13", "A14", "A15", "A16", "A17"], "duplicates": []} |
| all_claims_have_evidence_or_explicit_unresolved_status | PASS | {"claims": 0, "offenders": [], "note": "claims=[] by contract scope (objective.register_assets only; no extraction); asset-level resolution status carried on all 17 assets"} |
| no_verified_markers | PASS | {"structural_hits": [], "note": "contract forbids marking claims verified; verification is computed by the platform gate"} |
| counts_consistent | PASS | {"assets": 17, "by_class": {"document": 1, "heading": 1, "statement": 1, "parameter_set": 1, "module_table": 1, "gate_result_table": 1, "external_anchor": 1, "table": 1, "result_table": 2, "figure_set |
| artifact_hash_matches_envelope | PASS | {"file_sha256": "88de6e9959c78ec90cfdecf5c4778f582df82f78777aaa2102572becd4e180f6", "envelope_sha256": "88de6e9959c78ec90cfdecf5c4778f582df82f78777aaa2102572becd4e180f6"} |
| durable_mirror_identical | PASS | {"mirror": "docs/wp-8605-01/asset_manifest.json", "mirror_sha256": "88de6e9959c78ec90cfdecf5c4778f582df82f78777aaa2102572becd4e180f6", "artifact_sha256": "88de6e9959c78ec90cfdecf5c4778f582df82f78777aa |

## 复跑命令

    python3 scripts/kf_fetch_8605.py && python3 scripts/kf_register_8605.py && python3 scripts/kf_verify_8605.py       && python3 scripts/kf_figures_8605.py && python3 -m pytest -q tests/test_kf_wp8605.py       && python3 scripts/kf_report_8605.py --no-post

（需要 `TENSOR_API_BASE` / `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS` 环境变量用于独立重取报告；无网络时 `kf_verify_8605.py` 会降级到本地副本并在 verification.json 里标注 `degraded_to_local_copy`。）

## 结果 JSON（唯一 json 代码块）

```json
{
  "schema_version": "kf_result.v1",
  "package_id": "wp-8605-01",
  "task_type": "01-asset-registration",
  "report_id": "8605",
  "provenance": {
    "source_uri": "tensor://reports/8605",
    "source_field": "markdown",
    "source_hash": "sha256:a0488678cd1241a31152fc71c6fc86856a77cbcc4c94612a78a8a20cdd4a8e36",
    "source_chars": 8006,
    "source_bytes_utf8": 13153,
    "source_title": "P138W2-N09 CII/EEXI 营运能效动态评级与碳强度漂移预警（四门过，实船锚 WITHHELD）",
    "scenario_key": "P138W2-N09",
    "contract_version": "1.0",
    "lane": "C",
    "work_package": "wp-8605-01",
    "retrieved_via": {
      "api": "http://127.0.0.1:8010/api/v1",
      "local_copy": "runs/wp-8605-01/report_8605.md"
    },
    "local_copy": "runs/wp-8605-01/report_8605.md",
    "generator": "scripts/kf_register_8605.py",
    "verifier": "scripts/kf_verify_8605.py",
    "verification_status": "not_verified"
  },
  "outputs": {
    "asset_manifest.json": {
      "artifact_path": "artifacts/wp-8605-01/asset_manifest.json",
      "artifact_sha256": "88de6e9959c78ec90cfdecf5c4778f582df82f78777aaa2102572becd4e180f6",
      "artifact_bytes": 36777,
      "schema": "asset_manifest.v1",
      "package_id": "wp-8605-01",
      "task_type": "01-asset-registration",
      "report_id": "8605",
      "source": {
        "uri": "tensor://reports/8605",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "a0488678cd1241a31152fc71c6fc86856a77cbcc4c94612a78a8a20cdd4a8e36",
        "chars": 8006,
        "bytes_utf8": 13153,
        "title": "P138W2-N09 CII/EEXI 营运能效动态评级与碳强度漂移预警（四门过，实船锚 WITHHELD）",
        "scenario_key": "P138W2-N09",
        "platform_id": 8605,
        "platform_mission_id": 7260,
        "platform_figures": [
          "fig1_calibration.png",
          "fig2_gate_deviation.png",
          "fig3_annual_rating.png",
          "fig4_weather_decomposition.png"
        ],
        "platform_tags": [
          "CII",
          "EEXI",
          "营运能效",
          "漂移预警",
          "海况修正",
          "OSSE",
          "IMO"
        ],
        "retrieved_via": {
          "api": "http://127.0.0.1:8010/api/v1",
          "local_copy": "runs/wp-8605-01/report_8605.md"
        }
      },
      "counts": {
        "assets": 17,
        "by_class": {
          "document": 1,
          "heading": 1,
          "statement": 1,
          "parameter_set": 1,
          "module_table": 1,
          "gate_result_table": 1,
          "external_anchor": 1,
          "table": 1,
          "result_table": 2,
          "figure_set": 1,
          "figure_artifact": 1,
          "external_file_set": 1,
          "limitation_set": 1,
          "error_table": 1,
          "repro_chain": 1,
          "relationship": 1
        },
        "by_resolution": {
          "resolved_in_source": 15,
          "referenced_unresolved": 2
        },
        "resolved_in_source": 15,
        "referenced_unresolved": 2,
        "declared_absent": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "document",
          "label": "报告正文（markdown 全文）",
          "in_report_section": "(document)",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 8006,
            "start_line": 0,
            "end_line": 161,
            "quote": "# P138W2-N09 · CII/EEXI 营运能效动态评级与碳强度漂移预警\n\n**节点**：P138W2-N09（战役 DAG · 物理域）｜**任务号**：7260｜**仓**：ship-performance-platform｜**分支**：`agent/m7260`\n\n**一句话结论**：新增 `backend/modules/operational_energy_efficiency/` 模块，把 「EEXI 法定合规 + 营运剖面 + 海况修正 + 年度 A–E 评级 + 年末预测/漂移预警」接成一条链；四道机器门全部通过（gate_1 3.791e-05、gate_2 1.462e-04、gate_3 4.411%、gate_4 覆盖率 0.845），但**实船油耗锚与船级社评级锚在沙箱内均 WITHHELD**，gate_3 只用 OSSE 模型形式包络替代，gate_4 只用「边界恒等 + 预测校准」替代——不冒充实船验证。\n\n---\n\n## 1 案例介绍（物理背景 / 几何 / 参数表）\n\nCII（碳强度指标）把营运碳排折算成单位运输功：\n\n    attained CII = Σ_j (FC_j · CF_j) / (Capacity · D)      [gCO₂/(dwt·nm)]\n    required CII = a · Capacity^(−c) · (1 − Z(year))\n    A–E 评级     = 与 dd₁..dd₄ × required 比较（MEPC.354(78)）\n\n与 EEXI（设计口径、静水无风、V_ref 一点）不同，CII 是**全年营运口径**：同一条船在不同海况下的油耗差异可达百分之十几，直接用水尺油耗评级会把「今年风浪大」误判成「效率变差」。因此本节点的核心不是再算一遍法规算术，而是把**天气归因**与**效率漂移**分开，并对年末评级做带区间的预测。\n\n算例母船（VLCC 量级，参数全部入档 `gate_results.json:ship`）：\n\n| 参数 | 取值 | 说明 |\n|---|---|---|\n| 船型 / 容量 | tanker / 320000 dwt | CII 的 Capacity |\n| L_pp / B / T | 320.0 / 58.0 / 20.8 m | 波浪/风阻几何 |\n| V_ref / P_ref | 15.50 kn / 22000 kW | 设计点（EEXI 用） |\n| SFC / η_D | 175 g/kWh / 0.70 | 能-碳链 |\n| 辅机 | 1500 kW | 航行辅机负荷 |\n| 燃料 | heavy_fuel_oil (CF=3.114) | MEPC.364(79) 默认值 |\n\nOSSE 真值设置（演示年，`gate_results.json:demo_truth`）：波阻律 `bridged`、模型形式偏置 ×1.10、效率漂移 6.0%/yr、报表噪声 1.5%；真值全年 CII 观测 2.3448、静水口径 2.2086、平均天气功率增量 6.17%。\n\n## 2 怎么做的（方法 / 流程 / 关键设置 / 工具链）\n\n模块 `backend/modules/operational_energy_efficiency/`（新增，附 73 个 pytest 用例）：\n\n| 文件 | 职责 | 证据等级 |\n|---|---|---|\n| `seastate.py` | 波浪增阻（复用 `api/added_resistance` 的 STAWAVE-1 单源核 + 短波桥接）、视风矢量风阻、浅水效应、集总功率增量份额 | REAL 力律 / DECLARED 系数 |\n| `profile.py` | `P₀(V)=P_ref(V/V_ref)^n`、装载率、航线海况/浪向统计、航次油耗聚合、天气归一 | REAL |\n| `eexi.py` | attained EEDI 法定链（MEPC.328(76) 形）+ 参考线 1−削减率 → 合规裁决 | attained REAL / required WITHHELD |\n| `dynamic.py` | 逐月 CII（观测/归一）、漂移分解、1 谐波季节外推 + 蒙特卡洛年末预测、分级预警 | REAL + OSSE 校准 |\n| `osse.py` | 与生产模型**函数形式不同**的真值生成器（波阻律/浪向指数/风系数/形式偏置） | 仿真真值 |\n| `gates.py` | 四道门的机器可算实现（pytest 直接断言） | — |\n| `api.py` | `POST /api/v1/operational-efficiency/{eexi-compliance,annual-rating}`、`GET /evidence` | — |\n\n关键方法点：\n\n1. **单源复用，零二次转录**：CII/dd/Z 全部委托 `modules.green_navigation_ice.mepc`；EEDI 参考线与 EEXI 削减率直接用 `api.green_shipping` 的唯一转录表；波浪增阻直接用 `api/added_resistance.stawave1` 与 `heading_factor`（m1940 已验收核）。本模块不复制任何系数——这是 gate_2「参考线与外部锚 <1%」能成立的前提。\n2. **天气归一的口径声明**：同航速口径 `FC_norm = FC_obs/(1+f_sea)`，`f_sea = (R_aw + R_wind + R_shallow)/R_calm`，`R_calm = η_D·P₀/V`（常 η_D 近似，显式声明）。等功率（固定油门）口径的航速损失不在本链内，两种口径不混用。\n3. **漂移分解**：`CII_obs` 与 `CII_norm` 各自对月份做最小二乘，`slope_obs = slope_eff + slope_weather`（一阶加减分解，声明为近似）。\n4. **年末预测**：对 `CII_norm` 线性外推 + 对逐月天气因子做 1 谐波季节拟合（避免用年内均值抹掉季节相位），剩余月份运输功按已观测月均值或用户计划；蒙特卡洛含三项不确定性：残差乘性噪声、斜率标准误、天气归因模型形式项（±30% 相对，逐次抽样为整年系统项）。\n5. **预警阈值在设计阶段固定**（未据结果回调）：`WARN_RED_P=0.5`、`WARN_AMBER_P=0.1`、`WARN_AMBER_RATIO=0.95`、`WARN_RED_RATIO=0.97`、`WARN_DRIFT_PCT=2.0`。\n\n工具链：Python 3.11 + pytest + matplotlib（图件）+ 外部锚 JSON（跨仓只读）。\n重计算（200 个 OSSE 年校准）单机 <15 s，未占用集群。\n\n## 3 计算结果（数字表，程序化注入）\n\n### 3.1 四道机器门\n\n| 门 | 判据 | 实测 | 容差 | 结论 |\n|---|---|---|---|---|\n| gate_1 | CII 与 MEPC.353(78) 式(1) 一致性 | 3.791e-05 | <1e-3 (0.1%) | PASS |\n| gate_2 | EEXI attained / 参考线 vs 外部锚 | 1.462e-04 | <1e-2 (1%) | PASS |\n| gate_3 | 海况修正后燃油 vs 真值（OSSE 最差档） | 4.411% | <10% | PASS |\n| gate_4 | 评级边界恒等 + 预测校准 | 覆盖率 0.845 / 命中 0.855 | 覆盖率∈[0.65,0.95]、命中≥0.80 | PASS |\n\n外部锚（另一仓工件，只读）：`GATE_GREEN_M1850`，路径 `backend/tests/data/acceptance_gate_m1850.json`，其自身容差 0.02。四个算例逐项偏差：\n\n| 算例 | 船型 | 容量 | attained 偏差 | 参考线偏差 | required 偏差 |\n|---|---|---|---|---|---|\n| KVLCC2_tanker | tanker | 300000 | 1.964e-05 | 8.007e-05 | 8.007e-05 |\n| Capesize_bulk | bulk_carrier | 180000 | 3.303e-05 | 1.462e-04 | 1.462e-04 |\n| PostPanamax_container | container_ship | 140000 | 1.352e-05 | 1.914e-05 | 1.914e-05 |\n| Handysize_bulk | bulk_carrier | 35000 | 3.791e-05 | 4.133e-05 | 4.133e-05 |\n\n### 3.2 演示年：动态评级与提前预警\n\n| 量 | 数值 | 来源 |\n|---|---|---|\n| required CII（2026，Z=11%） | 2.0472 | `gate_results.json:annual_rating_full_year` |\n| 参考线（2019 基线） | 2.3002 | 同上 |\n| A/B·B/C·C/D·D/E 边界 | 1.761 · 1.924 · 2.170 · 2.416 | 同上（dd=[0.86, 0.94, 1.06, 1.18]） |\n| 全年观测 CII | 2.3390 → 评级 D | 同上 |\n| 全年天气归一 CII | 2.1843 → 评级 D | 同上 |\n| 天气超额（观测/归一−1） | 7.08% | 同上 |\n| 6 月末年末预测（点） | 2.3200（真值 2.3448，误差 1.06%） | `gate_results.json:midyear_forecast` |\n| 80% 预测区间 | [2.2832, 2.3553]（覆盖真值：是） | 同上 |\n| 评级概率 | A:0.000、B:0.000、C:0.000、D:0.999、E:0.001｜点预测 D | 同上 |\n| 预警级别（6 月末） | **RED**：P(CII>required)=1.00 >= 0.5；ratio=1.133 >= 0.97 且效率漂移 +2.80%/yr | 同上 |\n| 漂移分解 | 观测 +4.09%/yr = 效率 +4.99%/yr + 天气 -0.56%/yr | `gate_results.json:drift` |\n\n逐月明细见 `artifacts/op_cii_n09/monthly_series.csv`（12 行，首月 f_sea=0.102211、末月 f_sea=0.094388）。\n\n### 3.3 预测校准（200 个 OSSE 年，前 6 月观测）\n\n| 量 | 数值 | 名义/判据 |\n|---|---|---|\n| 80% PI 覆盖率（gate_4 配置） | 0.845 | 名义 0.80 |\n| 评级命中率（gate_4 配置） | 0.855 | ≥0.80 |\n| 点预测平均相对误差（gate_4 配置） | 1.95% | — |\n| 80% PI 覆盖率（演示年配置） | 0.910 | 名义 0.80 |\n| 评级命中率（演示年配置） | 0.975 | — |\n| 点预测平均相对误差（演示年配置） | 1.07% | — |\n\n## 4 结果图\n\n| 图 | 内容 | 文件 |\n|---|---|---|\n| 图 1 | 年末 CII 预测校准：真值 vs 预测（±80% PI），200 个仿真年 | `fig1_calibration.png` |\n| 图 2 | 四道门实测偏差 vs 判据容差（对数轴）+ gate_4 覆盖率 | `fig2_gate_deviation.png` |\n| 图 3 | 年度 CII 轨迹（观测/天气归一）叠加 A–E 评级边界与 6 月末年末预测 | `fig3_annual_rating.png` |\n| 图 4 | 海况修正逐月功率增量 f_sea + 碳强度漂移分解 | `fig4_weather_decomposition.png` |\n\n（场量云图不适用：本节点是规则算术 + 量-碳链评估，无数值场求解；图件给的是校准/轨迹/分解曲线，均程序化生成，无手抄。）\n\n## 5 注意点（踩过的坑 / 局限 / 适用范围）\n\n1. **OSSE 真值里的浪向律符号写错（自查发现，已修）**：`TruthModel.heading_factor` 初版把「与顶浪夹角」算成 180°，导致真值波浪增阻被压到 1e-61 N，gate_3 一度近乎“轻松通过”，却完全没检验波阻支路。修正后 gate_3 最差档从 2.75% 变为 4.411%（真值天气份额从 4.4% 升到 5.4–12.6%）。教训：OSSE 的真值侧必须与生产侧做**同点对拍**（同一 (Hs,Tp,浪向) 输入下两侧分项应可解释）。\n2. **短波域解析核系统性偏低（已登记局限）**：短波桥接核的 Bft6 顶浪波浪增阻份额 2.77% 落在经验量级带 [5%,25%] 之外（未桥接原值 8.86%）；大船短波域需 STAWAVE-2 或模型试验表，本仓无该表 → 回归为已登记局限。\n3. **浅水效应是 DECLARED 未标定形式**（`c·(T/h)²/(1−Fr_h²)`，Fr_h≥0.85 冻结并置 critical），只作量级提示，**不参与任何判据**；要用于裁决必须先有标定数据。\n4. **天气归因的常数 η_D 近似**：`R_calm = η_D P₀/V` 忽略了附加阻力带来的 η_D 变化（ISO 15016 常 η_D 口径）。若做等功率口径的航速损失预测，需要另一条链，不能复用本链数字。\n5. **预报的天气假设**：剩余月份天气用「已观测月份的 1 谐波季节拟合」外推；跨年或异常年（如厄尔尼诺）会偏，且 PI 只覆盖 ±30% 的天气归因模型形式不确定度。\n6. **规则系数的证据等级**：参考线 a/c、Z 因子、dd 向量都是决议文本转录（离线不可回读原文），因此 required/compliance 侧继承 WITHHELD；attained 侧才是 REAL。合规结论只能用于工程筛查，不能替代法定验证。\n7. **实船锚缺失**：沙箱内没有 noon report / 船级社评级记录，gate_3/gate_4 的「与实船一致」「与船级社评级一致」按 WITHHELD 登记，用 OSSE 包络与预测校准替代——这不是实船验证，报告与返回值都带着这个标签。\n\n## 6 误差判定（关键量 vs 基准，逐项回答「是否 <3%」）\n\n| 关键量 | 基准 | 误差 | <3%？ |\n|---|---|---|---|\n| attained CII（公式一致性） | 外部锚 GATE_GREEN_M1850 四个算例 | 3.791e-05 | **是** |\n| EEXI 参考线 / required / attained | 同上 | 1.462e-04 | **是** |\n| gate_3 归一燃油（最差 OSSE 档） | OSSE 真值（形式不同） | 4.411% | **否**（>3%，但满足本节点 10% 判据） |\n| 年末 CII 点预测（200 年均值） | OSSE 真值 | 1.95% | **是** |\n| 年末 CII 点预测（演示年） | OSSE 真值 | 1.06% | **是** |\n| 漂移斜率恢复（合成序列） | 解析设定值 | <1e-6（pytest 断言） | **是** |\n| 逐月聚合 vs 年度集总 CII | MEPC.353(78) 式(1) | 1.710e-16 | **是** |\n\n**显式结论**：与**外部锚**（跨仓工件）比对的两个法规量误差量级 1e-4~1e-5（<3%）；与 **OSSE 仿真真值**比对的海况修正燃油误差 4.411%（>3%，<10%）；**实船油耗与船级社评级无法比对（WITHHELD）**，故此两项不出具「<3%」结论。\n\n## 7 复现与审计链\n\n```bash\npython3 -m pytest backend/modules/operational_energy_efficiency/tests/ -q   # 73 passed\npython3 artifacts/op_cii_n09/run_n09.py      # 生成 gate_results.json + 2 个 CSV + 4 张图\npython3 artifacts/op_cii_n09/make_report.py  # 生成本报告（数字来自上面的 JSON/CSV）\n```\n\n| 工件 | 内容 |\n|---|---|\n| `artifacts/op_cii_n09/gate_results.json` | 四道门判据数字、外部锚逐算例偏差、演示年评级/预测/预警、局限登记 |\n| `artifacts/op_cii_n09/monthly_series.csv` | 逐月 CII 金标（观测/归一/评级/f_sea） |\n| `artifacts/op_cii_n09/forecast_calibration.csv` | 200 个 OSSE 年的预测-真值-PI 明细 |\n| `artifacts/op_cii_n09/fig1..fig4*.png` | 校准 / 门偏差 / 年度轨迹 / 天气-漂移分解 |\n| `backend/modules/operational_energy_efficiency/tests/` | 73 个 pytest 用例（含四道门回归） |\n\n## 8 与既有能力的关系（不与已验证案例重复）\n\n* `modules/green_navigation_ice/mepc.py`（W5-N08）已实现 CII 法规算术与冰区 f_ice 修正——本节点**复用**它，不重写；新增的是**营运剖面驱动的动态评级 + 天气归一 + 年末预测/预警**。\n* `api/green_shipping.py` 的 `/cii` 端点明确把 A–E 评级标为 NOT_SUPPORTED——本节点用 `mepc.rate` 把评级补齐，并给出评级概率与边界恒等回归，但 required 侧证据等级仍继承 WITHHELD，不改变上游的诚实标签。\n* `api/added_resistance.py`（m1940 STAWAVE-1）作为波浪增阻单源核被复用；本节点新增的是「增阻 → 功率增量 → 燃油 → CII」的营运链与不确定性预算。\n",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "整篇 markdown 即源资产；sha256 见 source.hash"
        },
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "报告标题",
          "in_report_section": "(document)",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 40,
            "start_line": 0,
            "end_line": 0,
            "quote": "# P138W2-N09 · CII/EEXI 营运能效动态评级与碳强度漂移预警",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "标题行；与 API title 字段同源"
        },
        {
          "asset_id": "A03",
          "asset_class": "statement",
          "label": "一句话结论（四门通过 + 实船锚 WITHHELD 声明）",
          "in_report_section": "# P138W2-N09 · CII/EEXI 营运能效动态评级与碳强度漂移预警",
          "locator": {
            "method": "char_span",
            "start_char": 141,
            "end_char": 434,
            "start_line": 4,
            "end_line": 6,
            "quote": "**一句话结论**：新增 `backend/modules/operational_energy_efficiency/` 模块，把 「EEXI 法定合规 + 营运剖面 + 海况修正 + 年度 A–E 评级 + 年末预测/漂移预警」接成一条链；四道机器门全部通过（gate_1 3.791e-05、gate_2 1.462e-04、gate_3 4.411%、gate_4 覆盖率 0.845），但**实船油耗锚与船级社评级锚在沙箱内均 WITHHELD**，gate_3 只用 OSSE 模型形式包络替代，gate_4 只用「边界恒等 + 预测校准」替代——不冒充实船验证。\n\n---",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "含四道门实测数字与 WITHHELD 声明；本工序只登记不复核"
        },
        {
          "asset_id": "A04",
          "asset_class": "parameter_set",
          "label": "算例母船参数表（VLCC 量级，8 行）",
          "in_report_section": "## 1 案例介绍（物理背景 / 几何 / 参数表）",
          "locator": {
            "method": "char_span",
            "start_char": 877,
            "end_char": 1327,
            "start_line": 20,
            "end_line": 29,
            "quote": "| 参数 | 取值 | 说明 |\n|---|---|---|\n| 船型 / 容量 | tanker / 320000 dwt | CII 的 Capacity |\n| L_pp / B / T | 320.0 / 58.0 / 20.8 m | 波浪/风阻几何 |\n| V_ref / P_ref | 15.50 kn / 22000 kW | 设计点（EEXI 用） |\n| SFC / η_D | 175 g/kWh / 0.70 | 能-碳链 |\n| 辅机 | 1500 kW | 航行辅机负荷 |\n| 燃料 | heavy_fuel_oil (CF=3.114) | MEPC.364(79) 默认值 |\n\nOSSE 真值设置（演示年，`gate_results.json:demo_truth`）：波阻律 `bridged`、模型形式偏置 ×1.10、效率漂移 6.0%/yr、报表噪声 1.5%；真值全年 CII 观测 2.3448、静水口径 2.2086、平均天气功率增量 6.17%。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "表头+分隔行+8 行参数；数值仅登记不换算"
        },
        {
          "asset_id": "A05",
          "asset_class": "module_table",
          "label": "模块清单（backend/modules/operational_energy_efficiency/ 7 文件）",
          "in_report_section": "## 2 怎么做的（方法 / 流程 / 关键设置 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1437,
            "end_char": 2064,
            "start_line": 35,
            "end_line": 43,
            "quote": "| 文件 | 职责 | 证据等级 |\n|---|---|---|\n| `seastate.py` | 波浪增阻（复用 `api/added_resistance` 的 STAWAVE-1 单源核 + 短波桥接）、视风矢量风阻、浅水效应、集总功率增量份额 | REAL 力律 / DECLARED 系数 |\n| `profile.py` | `P₀(V)=P_ref(V/V_ref)^n`、装载率、航线海况/浪向统计、航次油耗聚合、天气归一 | REAL |\n| `eexi.py` | attained EEDI 法定链（MEPC.328(76) 形）+ 参考线 1−削减率 → 合规裁决 | attained REAL / required WITHHELD |\n| `dynamic.py` | 逐月 CII（观测/归一）、漂移分解、1 谐波季节外推 + 蒙特卡洛年末预测、分级预警 | REAL + OSSE 校准 |\n| `osse.py` | 与生产模型**函数形式不同**的真值生成器（波阻律/浪向指数/风系数/形式偏置） | 仿真真值 |\n| `gates.py` | 四道门的机器可算实现（pytest 直接断言） | — |\n| `api.py` | `POST /api/v1/operational-efficiency/{eexi-compliance,annual-rating}`、`GET /evidence` | — |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "7 个模块文件与证据等级原文；模块本体在外部仓（见 A13）"
        },
        {
          "asset_id": "A06",
          "asset_class": "gate_result_table",
          "label": "四道机器门结果表（4 行）",
          "in_report_section": "### 3.1 四道机器门",
          "locator": {
            "method": "char_span",
            "start_char": 2974,
            "end_char": 3311,
            "start_line": 60,
            "end_line": 65,
            "quote": "| 门 | 判据 | 实测 | 容差 | 结论 |\n|---|---|---|---|---|\n| gate_1 | CII 与 MEPC.353(78) 式(1) 一致性 | 3.791e-05 | <1e-3 (0.1%) | PASS |\n| gate_2 | EEXI attained / 参考线 vs 外部锚 | 1.462e-04 | <1e-2 (1%) | PASS |\n| gate_3 | 海况修正后燃油 vs 真值（OSSE 最差档） | 4.411% | <10% | PASS |\n| gate_4 | 评级边界恒等 + 预测校准 | 覆盖率 0.845 / 命中 0.855 | 覆盖率∈[0.65,0.95]、命中≥0.80 | PASS |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "gate_1..gate_4 实测/容差/结论原文"
        },
        {
          "asset_id": "A07",
          "asset_class": "external_anchor",
          "label": "外部锚 GATE_GREEN_M1850（跨仓只读工件）",
          "in_report_section": "### 3.1 四道机器门",
          "locator": {
            "method": "char_span",
            "start_char": 3313,
            "end_char": 3417,
            "start_line": 67,
            "end_line": 67,
            "quote": "外部锚（另一仓工件，只读）：`GATE_GREEN_M1850`，路径 `backend/tests/data/acceptance_gate_m1850.json`，其自身容差 0.02。四个算例逐项偏差：",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "address_extraction",
            "result": "unresolved",
            "addresses_found": [],
            "detail": "报告仅给出相对路径 backend/tests/data/acceptance_gate_m1850.json（无 URL/DOI/绝对路径），且该路径属外部仓，本工作树内不存在"
          },
          "note": "报告给出路径 backend/tests/data/acceptance_gate_m1850.json 与自身容差 0.02；该路径属另一仓（ship-performance-platform），本工作树内不存在，无法在平台侧解析"
        },
        {
          "asset_id": "A08",
          "asset_class": "table",
          "label": "外部锚逐算例偏差表（4 行）",
          "in_report_section": "### 3.1 四道机器门",
          "locator": {
            "method": "char_span",
            "start_char": 3419,
            "end_char": 3813,
            "start_line": 69,
            "end_line": 74,
            "quote": "| 算例 | 船型 | 容量 | attained 偏差 | 参考线偏差 | required 偏差 |\n|---|---|---|---|---|---|\n| KVLCC2_tanker | tanker | 300000 | 1.964e-05 | 8.007e-05 | 8.007e-05 |\n| Capesize_bulk | bulk_carrier | 180000 | 3.303e-05 | 1.462e-04 | 1.462e-04 |\n| PostPanamax_container | container_ship | 140000 | 1.352e-05 | 1.914e-05 | 1.914e-05 |\n| Handysize_bulk | bulk_carrier | 35000 | 3.791e-05 | 4.133e-05 | 4.133e-05 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "KVLCC2/Capesize/PostPanamax/Handysize 四算例偏差原文"
        },
        {
          "asset_id": "A09",
          "asset_class": "result_table",
          "label": "演示年动态评级与预警结果表（8 行）",
          "in_report_section": "### 3.2 演示年：动态评级与提前预警",
          "locator": {
            "method": "char_span",
            "start_char": 3838,
            "end_char": 4301,
            "start_line": 78,
            "end_line": 87,
            "quote": "| 量 | 数值 | 来源 |\n|---|---|---|\n| required CII（2026，Z=11%） | 2.0472 | `gate_results.json:annual_rating_full_year` |\n| 参考线（2019 基线） | 2.3002 | 同上 |\n| A/B·B/C·C/D·D/E 边界 | 1.761 · 1.924 · 2.170 · 2.416 | 同上（dd=[0.86, 0.94, 1.06, 1.18]） |\n| 全年观测 CII | 2.3390 → 评级 D | 同上 |\n| 全年天气归一 CII | 2.1843 → 评级 D | 同上 |\n| 天气超额（观测/归一−1） | 7.08% | 同上 |\n| 6 月末年末预测（点） | 2.3200（真值 2.3448，误差 1.06%） | `gate_results.json:midyear_forecast` |\n| 80% 预测区间 | [2.2832, 2.3553]（覆盖真值：是） | 同上 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "required CII/边界/观测/归一/预测/评级概率/预警/漂移分解原文"
        },
        {
          "asset_id": "A10",
          "asset_class": "result_table",
          "label": "预测校准结果表（200 个 OSSE 年，6 行）",
          "in_report_section": "### 3.3 预测校准（200 个 OSSE 年，前 6 月观测）",
          "locator": {
            "method": "char_span",
            "start_char": 4669,
            "end_char": 4921,
            "start_line": 96,
            "end_line": 103,
            "quote": "| 量 | 数值 | 名义/判据 |\n|---|---|---|\n| 80% PI 覆盖率（gate_4 配置） | 0.845 | 名义 0.80 |\n| 评级命中率（gate_4 配置） | 0.855 | ≥0.80 |\n| 点预测平均相对误差（gate_4 配置） | 1.95% | — |\n| 80% PI 覆盖率（演示年配置） | 0.910 | 名义 0.80 |\n| 评级命中率（演示年配置） | 0.975 | — |\n| 点预测平均相对误差（演示年配置） | 1.07% | — |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "PI 覆盖率/命中率/点预测误差（gate_4 与演示年两配置）原文"
        },
        {
          "asset_id": "A11",
          "asset_class": "figure_set",
          "label": "结果图清单（4 张，fig1..fig4）",
          "in_report_section": "## 4 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 4932,
            "end_char": 5107,
            "start_line": 106,
            "end_line": 110,
            "quote": "\n| 图 | 内容 | 文件 |\n|---|---|---|\n| 图 1 | 年末 CII 预测校准：真值 vs 预测（±80% PI），200 个仿真年 | `fig1_calibration.png` |\n| 图 2 | 四道门实测偏差 vs 判据容差（对数轴）+ gate_4 覆盖率 | `fig2_gate_deviation.png` |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "图 1-4 内容与文件名原文；图件本体在平台 figures 字段（见 A12）"
        },
        {
          "asset_id": "A12",
          "asset_class": "figure_artifact",
          "label": "平台 figures 字段（4 个内嵌图件）",
          "in_report_section": "## 4 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 4933,
            "end_char": 5256,
            "start_line": 107,
            "end_line": 112,
            "quote": "| 图 | 内容 | 文件 |\n|---|---|---|\n| 图 1 | 年末 CII 预测校准：真值 vs 预测（±80% PI），200 个仿真年 | `fig1_calibration.png` |\n| 图 2 | 四道门实测偏差 vs 判据容差（对数轴）+ gate_4 覆盖率 | `fig2_gate_deviation.png` |\n| 图 3 | 年度 CII 轨迹（观测/天气归一）叠加 A–E 评级边界与 6 月末年末预测 | `fig3_annual_rating.png` |\n| 图 4 | 海况修正逐月功率增量 f_sea + 碳强度漂移分解 | `fig4_weather_decomposition.png` |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "platform_figures_field",
            "result": "resolved",
            "platform_figures_count": 4,
            "detail": "平台 figures 字段含 4 个图件，与报告 §4 清单一致；图件在平台侧可解析"
          },
          "note": "平台 API figures 字段含 4 个图件（fig1_calibration.png 等），与报告 §4 清单一致"
        },
        {
          "asset_id": "A13",
          "asset_class": "external_file_set",
          "label": "外部仓工件（artifacts/op_cii_n09/ 与 backend/tests/）",
          "in_report_section": "## 7 复现与审计链",
          "locator": {
            "method": "char_span",
            "start_char": 7198,
            "end_char": 7608,
            "start_line": 148,
            "end_line": 154,
            "quote": "| 工件 | 内容 |\n|---|---|\n| `artifacts/op_cii_n09/gate_results.json` | 四道门判据数字、外部锚逐算例偏差、演示年评级/预测/预警、局限登记 |\n| `artifacts/op_cii_n09/monthly_series.csv` | 逐月 CII 金标（观测/归一/评级/f_sea） |\n| `artifacts/op_cii_n09/forecast_calibration.csv` | 200 个 OSSE 年的预测-真值-PI 明细 |\n| `artifacts/op_cii_n09/fig1..fig4*.png` | 校准 / 门偏差 / 年度轨迹 / 天气-漂移分解 |\n| `backend/modules/operational_energy_efficiency/tests/` | 73 个 pytest 用例（含四道门回归） |",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "artifacts/op_cii_n09/gate_results.json",
              "artifacts/op_cii_n09/monthly_series.csv",
              "artifacts/op_cii_n09/forecast_calibration.csv",
              "backend/modules/operational_energy_efficiency/tests/"
            ],
            "missing": [
              "artifacts/op_cii_n09/gate_results.json",
              "artifacts/op_cii_n09/monthly_series.csv",
              "artifacts/op_cii_n09/forecast_calibration.csv",
              "backend/modules/operational_energy_efficiency/tests/"
            ],
            "result": "unresolved",
            "detail": "全部路径在本工作树（TensorKnowledge）内均不存在，属 ship-performance-platform 仓产物"
          },
          "note": "gate_results.json/monthly_series.csv/forecast_calibration.csv/fig*.png/73 个 pytest 用例；均属 ship-performance-platform 仓，本工作树内不存在"
        },
        {
          "asset_id": "A14",
          "asset_class": "limitation_set",
          "label": "注意点与局限（7 条）",
          "in_report_section": "## 5 注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 5349,
            "end_char": 6158,
            "start_line": 117,
            "end_line": 123,
            "quote": "\n1. **OSSE 真值里的浪向律符号写错（自查发现，已修）**：`TruthModel.heading_factor` 初版把「与顶浪夹角」算成 180°，导致真值波浪增阻被压到 1e-61 N，gate_3 一度近乎“轻松通过”，却完全没检验波阻支路。修正后 gate_3 最差档从 2.75% 变为 4.411%（真值天气份额从 4.4% 升到 5.4–12.6%）。教训：OSSE 的真值侧必须与生产侧做**同点对拍**（同一 (Hs,Tp,浪向) 输入下两侧分项应可解释）。\n2. **短波域解析核系统性偏低（已登记局限）**：短波桥接核的 Bft6 顶浪波浪增阻份额 2.77% 落在经验量级带 [5%,25%] 之外（未桥接原值 8.86%）；大船短波域需 STAWAVE-2 或模型试验表，本仓无该表 → 回归为已登记局限。\n3. **浅水效应是 DECLARED 未标定形式**（`c·(T/h)²/(1−Fr_h²)`，Fr_h≥0.85 冻结并置 critical），只作量级提示，**不参与任何判据**；要用于裁决必须先有标定数据。\n4. **天气归因的常数 η_D 近似**：`R_calm = η_D P₀/V` 忽略了附加阻力带来的 η_D 变化（ISO 15016 常 η_D 口径）。若做等功率口径的航速损失预测，需要另一条链，不能复用本链数字。\n5. **预报的天气假设**：剩余月份天气用「已观测月份的 1 谐波季节拟合」外推；跨年或异常年（如厄尔尼诺）会偏，且 PI 只覆盖 ±30% 的天气归因模型形式不确定度。\n6. **规则系数的证据等级**：参考线 a/c、Z 因子、dd 向量都是决议文本转录（离线不可回读原文），因此 required/compliance 侧继承 WITHHELD；attained 侧才是 REAL。合规结论只能用于工程筛查，不能替代法定验证。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "OSSE 浪向律符号/短波域偏低/浅水 DECLARED/η_D 近似/天气假设/规则系数证据等级/实船锚缺失原文"
        },
        {
          "asset_id": "A15",
          "asset_class": "error_table",
          "label": "误差判定表（关键量 vs 基准，7 行）",
          "in_report_section": "## 6 误差判定（关键量 vs 基准，逐项回答「是否 <3%」）",
          "locator": {
            "method": "char_span",
            "start_char": 6323,
            "end_char": 6785,
            "start_line": 128,
            "end_line": 136,
            "quote": "| 关键量 | 基准 | 误差 | <3%？ |\n|---|---|---|---|\n| attained CII（公式一致性） | 外部锚 GATE_GREEN_M1850 四个算例 | 3.791e-05 | **是** |\n| EEXI 参考线 / required / attained | 同上 | 1.462e-04 | **是** |\n| gate_3 归一燃油（最差 OSSE 档） | OSSE 真值（形式不同） | 4.411% | **否**（>3%，但满足本节点 10% 判据） |\n| 年末 CII 点预测（200 年均值） | OSSE 真值 | 1.95% | **是** |\n| 年末 CII 点预测（演示年） | OSSE 真值 | 1.06% | **是** |\n| 漂移斜率恢复（合成序列） | 解析设定值 | <1e-6（pytest 断言） | **是** |\n| 逐月聚合 vs 年度集总 CII | MEPC.353(78) 式(1) | 1.710e-16 | **是** |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "7 个关键量误差与 <3% 判定原文；含显式结论（外部锚 <3%、OSSE 4.411%、实船 WITHHELD）"
        },
        {
          "asset_id": "A16",
          "asset_class": "repro_chain",
          "label": "复现与审计链（pytest/run/make 命令）",
          "in_report_section": "## 7 复现与审计链",
          "locator": {
            "method": "char_span",
            "start_char": 6940,
            "end_char": 7121,
            "start_line": 141,
            "end_line": 144,
            "quote": "\n```bash\npython3 -m pytest backend/modules/operational_energy_efficiency/tests/ -q   # 73 passed\npython3 artifacts/op_cii_n09/run_n09.py      # 生成 gate_results.json + 2 个 CSV + 4 张图",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "三条复现命令原文（73 passed / run_n09.py / make_report.py）"
        },
        {
          "asset_id": "A17",
          "asset_class": "relationship",
          "label": "与既有能力的关系（3 条，不重复已验证案例）",
          "in_report_section": "## 8 与既有能力的关系（不与已验证案例重复）",
          "locator": {
            "method": "char_span",
            "start_char": 7635,
            "end_char": 7906,
            "start_line": 157,
            "end_line": 159,
            "quote": "\n* `modules/green_navigation_ice/mepc.py`（W5-N08）已实现 CII 法规算术与冰区 f_ice 修正——本节点**复用**它，不重写；新增的是**营运剖面驱动的动态评级 + 天气归一 + 年末预测/预警**。\n* `api/green_shipping.py` 的 `/cii` 端点明确把 A–E 评级标为 NOT_SUPPORTED——本节点用 `mepc.rate` 把评级补齐，并给出评级概率与边界恒等回归，但 required 侧证据等级仍继承 WITHHELD，不改变上游的诚实标签。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "复用 mepc.py / 补齐 A-E 评级 / 复用 STAWAVE-1 原文"
        }
      ],
      "claims": [],
      "claims_note": "按工作包契约 objective.classify_report_type=false 且 notes 允许 claims 为空数组：本工序只登记资产定位，不做 claim 抽取；claim 抽取由下游工作包负责。",
      "integrity": {
        "quote_uniqueness": "all quotes confirmed unique substrings of source markdown (scripts/kf_verify_8605.py, checks.source_locator_resolvable)",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true
      }
    }
  }
}
```
