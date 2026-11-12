# KF-RESULT wp-448-01

## ① 案例介绍

本单是报告→知识产线上的一道工序：**资产登记（task_type = 01-asset-registration）**，只服务 report_id=448 这一份报告。

- 源报告：report 448，《EX-1 水池锚定①: DTMB 5415 艏部线型优化问题规格与预注册》，scenario_key=`EX-1_tank_anchoring_dtmb5415_bow_optimization`，平台 mission 541。
- 内容性质：DTMB 5415 艏部线型优化的**问题规格与预注册**（不是计算结果报告）。报告自身声明本阶段无计算方法、无场量图：原文「本任务为纯文档/规格定义，无计算场量或对比曲线。图表说明:」。
- 上游几何锚点（原文）：Lpp 142.000 m / B 19.000 m / T 6.160 m / ∇ 8336.7 m³ / Cb 0.5018；设计 Fr_d = 0.28。
- 本工序**不做**的事：不抽取 claim、不做报告类型分类、不改写上游产物、不标 verified（契约 objective 仅 `register_assets: true`，claims 允许空数组）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取证（不凭记忆）**：`GET /api/v1/tensor/reports/448` 取 `markdown` 字段，落盘 `runs/wp-448-01/report_448.md`（3233 字符 / 5176 字节 UTF-8），本地重算 `sha256 = a3e7910fbcbe3624805a875ebd9a033c54036a1950cdc2885a6fc739dbcabea8`，与契约 `source_hash` 逐字节相同 → 才继续。
2. **定位而非抄写**：`scripts/kf_register_448.py` 维护一张 22 行的锚点表（资产 id / 类 / 唯一锚点串 / 相对行跨），运行时用锚点在 markdown 中定位行号 → 由行偏移计算 `[start_char, end_char)` → **直接从原文切片**得到 `quote`；每个 quote 再断言「在全文出现次数 == 1」，不唯一即中止（脚本会 `SystemExit`，历史踩坑：`**速度矩阵**:` 与 `**基线 C_T 参考值` 两条锚点各命中 2/0 次，已改为更长唯一串）。
3. **可解析性判定（不做猜测）**：对每个资产跑一次机器检查 `resolution_check`，结果与声明状态强绑定：
   - 页内资产 → `char_span_in_source_markdown`；
   - 外部交付物 A19 → 在**本工作树内实测** 5 个 `docs/ex1/*` 路径是否存在（结果：5/5 均不存在）；
   - 外部提交 A20 → 本仓 `git cat-file -e 78ed109^{commit}`（返回 128，本仓对象库无法解析）；
   - 外部数据集 A17/A18 → 在原文行内正则检索 URL/DOI/绝对路径（命中 0 条），因此登记为 `referenced_unresolved`，不编造地址；
   - 图件 A14/A15 → 平台 `figures` 字段为空数组且原文声明无图 → `declared_absent`。
4. **独立校验**：`scripts/kf_verify_448.py` 在**新进程、新登录**下重新拉取 markdown（不信任本地副本），重算哈希、逐资产重新切片比对、跑 JSON Schema（本地补写 `schemas/asset_manifest.v1.schema.json`，理由见⑤）、查 id 唯一性、查 claim 证据策略、结构化扫描「verified」标记 → 输出 `artifacts/wp-448-01/verification.json`。
5. **可复现**：清空 `artifacts/wp-448-01/` 后按下面的复跑命令重建，`asset_manifest.json` 的 sha256 逐字节相同（`0a99a0612fc50f8deb1444ecc9566f50cc0ef4d12dc94157405e9ff686edafde`，见结果信封 `outputs["asset_manifest.json"]["artifact_sha256"]`），说明登记过程不含随机性/时间戳污染。
6. **测试**：`tests/test_kf_wp448.py` 11 项，除正向断言外含 4 个**反向对照**（篡改 quote 的一个数字、平移 span、把外部资产的 resolution 谎报为 resolved、制造重复 id），证明这些检查真的会红，而不是只跑通。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/wp-448-01/asset_manifest.json` | 主产物：22 个资产（19 类）、16 resolved_in_source / 4 referenced_unresolved / 2 declared_absent，26 KB |
| `schemas/asset_manifest.v1.schema.json` | 本地补写的 manifest 形状约束（版本化源码，供 schema_pass 可复现；不随 artifacts 清空而丢失） |
| `artifacts/wp-448-01/verification.json` | 11 项验收自检逐项结果，overall=PASS |
| `artifacts/wp-448-01/fig_asset_inventory.png` | 图1 资产类别×可解析状态 |
| `artifacts/wp-448-01/fig_locator_coverage.png` | 图2 逐资产 char span 定位地图 |
| `artifacts/wp-448-01/fig_verification.png` | 图3 验收自检状态板 |
| `runs/wp-448-01/report_448.md` / `.json` | 源证据快照（markdown 与 API 原始响应） |
| `runs/wp-448-01/kf_result.wp-448-01.json` | 结果信封（package_id/task_type/report_id/provenance/outputs） |
| `scripts/kf_fetch_448.py` / `kf_register_448.py` / `kf_verify_448.py` / `kf_figures_448.py` / `kf_report_448.py` | 取证 / 登记 / 校验 / 出图 / 报报告，一键可复跑 |
| `tests/test_kf_wp448.py` | 11 项不变量测试（含 4 个反向对照） |
| `docs/wp-448-01/KF-RESULT-wp-448-01.md` | 本报告正文 |

**资产分类计数**：{"document": 1, "heading": 1, "table": 3, "geometry_declaration": 1, "statement": 1, "design_space": 1, "constraint_set": 1, "parameter_set": 1, "measurement_plan": 1, "prereg_lock": 1, "prediction": 1, "numeric_anchor": 1, "figure_declaration": 1, "figure_slot": 1, "limitation_set": 1, "external_dataset": 2, "external_file_set": 1, "vcs_reference": 1, "external_note": 1}

## ④ 证据定位表（claim/字段 → 原文引文）

下列每一行的 `quote` 都是报告 448 markdown 的**唯一子串**，并记录字符区间；平台可独立重算 sha256 与子串定位。

| asset_id | class | resolution | locator (char span) | 原文片段（逐字取自报告 448） |
|---|---|---|---|---|
| A01 | document | resolved_in_source | 0-3233 (全文) | `（整篇 markdown，sha256 见 provenance）` |
| A02 | heading | resolved_in_source | 0-30 | `# EX-1 水池锚定①: DTMB 5415 艏部线型优化` |
| A03 | table | resolved_in_source | 164-447 | `\| 参数 \| 符号 \| 值 \| 来源 \|` |
| A04 | geometry_declaration | resolved_in_source | 460-556 | `- 精确 STL: 164926 面, 7.9 MB, 15/15 门禁通过` |
| A05 | statement | resolved_in_source | 579-603 | `**目标**: min C_T(Fr=0.28)` |
| A06 | design_space | resolved_in_source | 605-697 | `**设计变量**: 8 DOF 艏部参数化 (RBF 控制点)` |
| A07 | constraint_set | resolved_in_source | 699-839 | `**约束** (可执行断言 C1-C7):` |
| A08 | parameter_set | resolved_in_source | 841-897 | `**速度矩阵**: 5 个 Fr 点 (0.14/0.21/0.28/0.35/0.41)，设计点权重 0.50` |
| A09 | measurement_plan | resolved_in_source | 910-1053 | `1. **Layer 1**: Holtrop-Mennen 经验公式批量评估 (N≥100, ±10%)` |
| A10 | prereg_lock | resolved_in_source | 1065-1188 | `- 预测改善区间: [2%, 8%] @ Fr=0.28` |
| A11 | prediction | resolved_in_source | 1621-1681 | `- 保守: ≥2% @ Fr=0.28` |
| A12 | numeric_anchor | resolved_in_source | 1122-1161 | `- 基线 C_T 参考值: 2.40e-3 (IIHR + CFDWS 均值)` |
| A13 | table | resolved_in_source | 1224-1608 | `\| 测试用例 \| 结果 \| 说明 \|` |
| A14 | figure_declaration | declared_absent | 1694-1859 | `本任务为纯文档/规格定义，无计算场量或对比曲线。图表说明:` |
| A15 | figure_slot | declared_absent | 1781-1859 | `  - 艏部参数化变形云图 (基线 vs 优化)` |
| A16 | limitation_set | resolved_in_source | 2077-2221 | `- **经验公式精度**: Holtrop-Mennen ±10%，仅用于初步筛选` |
| A17 | external_dataset | referenced_unresolved | 460-498 | `- 精确 STL: 164926 面, 7.9 MB, 15/15 门禁通过` |
| A18 | external_dataset | referenced_unresolved | 499-530 | `- 官方点云: 2250 点 (Zenodo 源), 逐点重合` |
| A19 | external_file_set | referenced_unresolved | 2874-3074 | `- docs/ex1/problem_spec.md (优化问题规格)` |
| A20 | vcs_reference | referenced_unresolved | 3076-3115 | `**Git Commit**: 78ed109 (agent/m541 分支)` |
| A21 | table | resolved_in_source | 2347-2694 | `\| 指标 \| 本任务值 \| 基准值 \| 误差 \| <3%? \|` |
| A22 | external_note | resolved_in_source | 3122-3233 | `## 图件补充 (RPT-REWORK m583)` |

## ⑤ 注意点与局限

1. **报告本身不是结果报告**：448 是问题规格+预注册。本工序因此只登记资产，不产生任何阻力/推进量值；报告中「11/11 通过」「0% 误差」是**上游自报**，本单原样登记、未复核（复核属下游算例/证据包工序）。原文 A21 表内 `| 基线 C_T (Fr=0.28) | 2.40e-3 | 2.40e-3 (IIHR+CFDWS) | 0% | ✅ |`。
2. **4 个资产解析不到，如实挂账**：A19（`docs/ex1/` 5 个交付物）、A20（外部提交 78ed109）、A17（精确 STL 164926 面）、A18（Zenodo 点云 2250 点）。它们属于**别的仓库/外部数据源**，本工作树内不存在或原文未给可解析地址；若下游要用，必须由来源仓补地址，不能靠猜。
3. **figures 为空 ≠ 报告合规**：报告尾部有治理标记「RPT-REWORK m583：本报告原无图件，经治理标记需补充」，与平台 `figures` 为空数组一致（登记为 A14/A15/A22）。补图是另一道工序，本单不代劳。
4. **契约引用的 `schemas/kf_result.v1.schema.json` 在本工作树不存在**（`schemas/` 下只有 19 个旧 schema，无 kf_result）。为使 `schema_pass` 可复现，本单按契约文字描述（package_id/task_type/report_id/provenance/outputs）实现结果信封，并补写 manifest 侧 schema；**若平台侧真实 schema 与此不一致，schema_pass 应以平台为准、本单接受返修**。这是本单最主要的残余风险。
5. **覆盖度口径**：21 个 span 级资产对 3233 字符的并集覆盖 = 2437 字符（75.4%）；整篇资产 A01 覆盖 100%，图中未计入，避免用 100% 制造假象。
6. **边界**：全程只读写 report 448 相关文件，未触碰其它 report_id（测试 `test_no_report_id_contamination` 守这一条）。

## ⑥ 误差判定

本工序是登记而非计算，**没有物理量可比**，故不存在「关键量 vs 基准 <3%」这一栏；可比的只有*恒等性/可解析性*判据，逐项如实列出：

| 判据 | 本单值 | 基准 | 误差 | <3%? |
|---|---|---|---|---|
| markdown 字节哈希 | `a3e7910fbcbe3624…` | 契约 source_hash `a3e7910fbcbe3624…` | 0（逐字节相等） | ✅ 精确匹配 |
| markdown 字符数 | 3233 | 契约 chars 3233 | 0 | ✅ |
| 资产 locator 可复现 | 22/22 切片全等且唯一 | 自检规则 | 0 失配 | ✅ |
| 资产 id 唯一性 | 22 个 id，0 重复 | 契约 no_duplicate_ids | 0 | ✅ |
| claim 证据覆盖 | claims=[]（契约允许） | all_claims_have_evidence | 0 违规 | ✅（空集，见⑤-1 说明） |
| 外部资产可解析率 | 16/22 页内解析，4 个挂 unresolved | — | — | ❌ 不适用：外部资产本就无法在本地解析，**如实挂账，不冒充 resolved** |

验收项逐条结果：

| 验收项 | 结果 | 证据 |
|---|---|---|
| valid_json | PASS | {"manifest": "artifacts/wp-448-01/asset_manifest.json", "result": "runs/wp-448-01/kf_result.wp-448-01.json", "block_equals_result": true} |
| source_hash_matches | PASS | {"api_sha256": "a3e7910fbcbe3624805a875ebd9a033c54036a1950cdc2885a6fc739dbcabea8", "contract_sha256": "a3e7910fbcbe3624805a875ebd9a033c54036a1950cdc2885a6fc739dbcabea8", "manifest_sha256": "a3e7910fbc |
| schema_pass | PASS | {"schema": "schemas/asset_manifest.v1.schema.json", "note": "local schema schemas/asset_manifest.v1.schema.json (canonical kf_result schema absent from worktree)"} |
| result_envelope_shape | PASS | {"keys": ["outputs", "package_id", "provenance", "report_id", "schema_version", "task_type"], "outputs_keys": ["asset_manifest.json"]} |
| result_ids_match_contract | PASS | {"package_id": "wp-448-01", "task_type": "01-asset-registration", "report_id": "448"} |
| source_locator_resolvable | PASS | {"assets_checked": 22, "failures": [], "method": "re-slice fresh API markdown at [start_char,end_char) + uniqueness count"} |
| no_duplicate_ids | PASS | {"asset_ids": ["A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", "A09", "A10", "A11", "A12", "A13", "A14", "A15", "A16", "A17", "A18", "A19", "A20", "A21", "A22"], "duplicates": []} |
| all_claims_have_evidence_or_explicit_unresolved_status | PASS | {"claims": 0, "offenders": [], "note": "claims=[] by contract scope (objective.register_assets only; no extraction); asset-level resolution status carried on all 22 assets"} |
| no_verified_markers | PASS | {"structural_hits": [], "note": "contract forbids marking claims verified; verification is computed by the platform gate"} |
| counts_consistent | PASS | {"assets": 22, "by_class": {"document": 1, "heading": 1, "table": 3, "geometry_declaration": 1, "statement": 1, "design_space": 1, "constraint_set": 1, "parameter_set": 1, "measurement_plan": 1, "prer |
| artifact_hash_matches_envelope | PASS | {"file_sha256": "0a99a0612fc50f8deb1444ecc9566f50cc0ef4d12dc94157405e9ff686edafde", "envelope_sha256": "0a99a0612fc50f8deb1444ecc9566f50cc0ef4d12dc94157405e9ff686edafde"} |

## 复跑命令

    python3 scripts/kf_fetch_448.py && python3 scripts/kf_register_448.py && python3 scripts/kf_verify_448.py       && python3 scripts/kf_figures_448.py && python3 -m pytest -q tests/test_kf_wp448.py       && python3 scripts/kf_report_448.py --no-post

（需要 `TENSOR_API_BASE` / `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS` 环境变量用于独立重取报告；无网络时 `kf_verify_448.py` 会降级到本地副本并在 verification.json 里标注 `degraded_to_local_copy`。）

## 结果 JSON（唯一 json 代码块）

```json
{
  "schema_version": "kf_result.v1",
  "package_id": "wp-448-01",
  "task_type": "01-asset-registration",
  "report_id": "448",
  "provenance": {
    "source_uri": "tensor://reports/448",
    "source_field": "markdown",
    "source_hash": "sha256:a3e7910fbcbe3624805a875ebd9a033c54036a1950cdc2885a6fc739dbcabea8",
    "source_chars": 3233,
    "source_bytes_utf8": 5176,
    "source_title": "EX-1 水池锚定①: DTMB 5415 艏部线型优化问题规格与预注册",
    "scenario_key": "EX-1_tank_anchoring_dtmb5415_bow_optimization",
    "contract_version": "1.0",
    "lane": "C",
    "work_package": "wp-448-01",
    "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/448",
    "local_copy": "runs/wp-448-01/report_448.md",
    "generator": "scripts/kf_register_448.py",
    "verifier": "scripts/kf_verify_448.py",
    "verification_status": "not_verified"
  },
  "outputs": {
    "asset_manifest.json": {
      "artifact_path": "artifacts/wp-448-01/asset_manifest.json",
      "artifact_sha256": "0a99a0612fc50f8deb1444ecc9566f50cc0ef4d12dc94157405e9ff686edafde",
      "artifact_bytes": 26105,
      "schema": "asset_manifest.v1",
      "package_id": "wp-448-01",
      "task_type": "01-asset-registration",
      "report_id": "448",
      "source": {
        "uri": "tensor://reports/448",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "a3e7910fbcbe3624805a875ebd9a033c54036a1950cdc2885a6fc739dbcabea8",
        "chars": 3233,
        "bytes_utf8": 5176,
        "title": "EX-1 水池锚定①: DTMB 5415 艏部线型优化问题规格与预注册",
        "scenario_key": "EX-1_tank_anchoring_dtmb5415_bow_optimization",
        "platform_id": 448,
        "platform_mission_id": 541,
        "platform_figures": [],
        "platform_tags": [
          "DTMB-5415",
          "hull-optimization",
          "preregistration",
          "tank-test",
          "CFD-Workshop",
          "resistance-reduction"
        ],
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/448",
        "local_copy": "runs/wp-448-01/report_448.md"
      },
      "counts": {
        "assets": 22,
        "by_class": {
          "document": 1,
          "heading": 1,
          "table": 3,
          "geometry_declaration": 1,
          "statement": 1,
          "design_space": 1,
          "constraint_set": 1,
          "parameter_set": 1,
          "measurement_plan": 1,
          "prereg_lock": 1,
          "prediction": 1,
          "numeric_anchor": 1,
          "figure_declaration": 1,
          "figure_slot": 1,
          "limitation_set": 1,
          "external_dataset": 2,
          "external_file_set": 1,
          "vcs_reference": 1,
          "external_note": 1
        },
        "by_resolution": {
          "resolved_in_source": 16,
          "declared_absent": 2,
          "referenced_unresolved": 4
        },
        "resolved_in_source": 16,
        "referenced_unresolved": 4,
        "declared_absent": 2
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
            "end_char": 3233,
            "start_line": 0,
            "end_line": 140,
            "quote": "# EX-1 水池锚定①: DTMB 5415 艏部线型优化\n\n## 1. 案例介绍\n\n### 物理背景\nDTMB 5415 是美国海军驱逐舰船型，国际 CFD Workshop 标准验证船型。本任务通过艏部参数化变形降低设计航速 (Fr=0.28) 下的总阻力，并通过 外协水池独立试验进行最终裁定。\n\n### 基线几何参数\n| 参数 | 符号 | 值 | 来源 |\n|------|------|----|----|\n| 垂线间长 | Lpp | 142.000 m | 官方定义 |\n| 型宽 | B | 19.000 m | 官方定义 |\n| 设计吃水 | T | 6.160 m | 官方定义 |\n| 排水体积 | ∇ | 8336.7 m³ | 官方定义 (exact) |\n| 方形系数 | Cb | 0.5018 | 验算值 |\n| 设计 Fr | Fr_d | 0.28 | CFDWS 标准 |\n| 设计航速 | V_d | 10.45 m/s | Fr=0.28 对应 |\n\n### 几何锁定状态\n- 精确 STL: 164926 面, 7.9 MB, 15/15 门禁通过\n- 官方点云: 2250 点 (Zenodo 源), 逐点重合\n- 主尺度验证: Lpp/B/T/∇ 与官方值一致\n\n## 2. 方法\n\n### 优化问题定义\n**目标**: min C_T(Fr=0.28)\n\n**设计变量**: 8 DOF 艏部参数化 (RBF 控制点)\n- x1-x3: 水线/甲板半宽变化\n- x4-x6: 球鼻艏垂向/横向/纵向位移\n- x7-x8: 甲板边线/曲率修正\n\n**约束** (可执行断言 C1-C7):\n- C1: 排水量 ±0.5%\n- C2: 主尺度 Lpp/B/T 固定\n- C3: 艉部冻结 (x/Lpp>0.35 零位移)\n- C4: 最小曲率半径 ≥0.5m\n- C5: 光体无附体\n- C6: 水密性\n- C7: 设计变量范围\n\n**速度矩阵**: 5 个 Fr 点 (0.14/0.21/0.28/0.35/0.41)，设计点权重 0.50\n\n### 三层评估方案\n1. **Layer 1**: Holtrop-Mennen 经验公式批量评估 (N≥100, ±10%)\n2. **Layer 2**: RANS CFD 抽查 (k-ω SST, N≥10, ±3%)\n3. **Layer 3**: 外协水池拖曳试验 (N=1-3+基线, ±1%)\n\n### 预注册锁定\n- 预测改善区间: [2%, 8%] @ Fr=0.28\n- 判定规则: RED/YELLOW/GREEN 三级\n- 基线 C_T 参考值: 2.40e-3 (IIHR + CFDWS 均值)\n- append-only: 水池数据到手后不可修改\n\n## 3. 计算结果\n\n### 约束断言测试 (11/11 通过)\n| 测试用例 | 结果 | 说明 |\n|---------|------|------|\n| 基线通过 | ✅ | 零位移基线满足所有约束 |\n| 排水量超差 | ✅ | +1% 触发 C1 RED |\n| 排水量范围内 | ✅ | +0.4% 通过 |\n| 艉部位移 | ✅ | 1mm 位移触发 C3 RED |\n| 变量越界 | ✅ | x1=2.0 触发 C7 RED |\n| 判定 GREEN | ✅ | 改善 5% → GREEN |\n| 判定 YELLOW (低) | ✅ | 改善 1% → YELLOW |\n| 判定 YELLOW (高) | ✅ | 改善 10% → YELLOW |\n| 判定 RED | ✅ | 阻力增加 → RED |\n| 速度矩阵权重 | ✅ | sum=1.0 |\n| 设计航速 | ✅ | V_d=10.45 m/s |\n\n### 预测改善区间\n- 保守: ≥2% @ Fr=0.28\n- 乐观: ≤8% @ Fr=0.28\n- 最可能: 4-5% (基于文献中值)\n\n## 4. 结果图\n\n本任务为纯文档/规格定义，无计算场量或对比曲线。图表说明:\n- **无图理由**: 本阶段为问题定义与预注册，尚未进行实际优化计算。待 Layer 2/3 完成后，将生成:\n  - 艏部参数化变形云图 (基线 vs 优化)\n  - C_T 改善率柱状图 (5 个 Fr 点)\n  - 阻力曲线对比 (基线 vs 优化 vs 文献)\n\n## 5. 注意点\n\n### 关键决策\n1. **设计变量选择**: 8 DOF 艏部参数化 (6-10 范围内)，聚焦球鼻艏和水线入口区域\n2. **速度矩阵**: 5 个 Fr 点含 4 个非设计点，防过拟合权重分配 (设计点 0.50)\n3. **约束严格度**: 排水量 ±0.5% (而非 ±1%)，确保水池试验可比性\n4. **预注册纪律**: append-only，水池数据到手后不可修改预测\n\n### 局限与风险\n- **经验公式精度**: Holtrop-Mennen ±10%，仅用于初步筛选\n- **CFD 不确定度**: ±3% (网格/时间/数值)，需三套网格验证\n- **水池成本**: 50-100 万 RMB，周期 2-3 个月\n- **改善预期**: 文献范围 2-8%，实际可能偏离\n\n### 适用范围\n- 仅适用于 DTMB 5415 基线 (exact 8336.7m³ 几何)\n- 艏部参数化变形 (x/Lpp ∈ [0, 0.35])\n- 模型尺度优化，实船预报作为验证\n\n## 6. 误差判定\n\n### 关键量 vs 基准\n| 指标 | 本任务值 | 基准值 | 误差 | <3%? |\n|------|---------|--------|------|------|\n| Lpp | 142.000 m | 142.000 m (官方) | 0% | ✅ |\n| B | 19.000 m | 19.000 m (官方) | 0% | ✅ |\n| T | 6.160 m | 6.160 m (官方) | 0% | ✅ |\n| ∇ | 8336.7 m³ | 8336.7 m³ (官方) | 0% | ✅ |\n| Cb | 0.5018 | 0.5018 (文献) | 0% | ✅ |\n| 基线 C_T (Fr=0.28) | 2.40e-3 | 2.40e-3 (IIHR+CFDWS) | 0% | ✅ |\n\n**说明**: 本阶段为问题定义，几何参数与官方值完全一致 (0% 误差)。基线 C_T 参考值取自公开文献 (IIHR + CFDWS 均值)，待水池试验后以实测值为准。\n\n### 约束断言验证\n- 11/11 测试通过\n- 所有约束可执行 (Python 代码)\n- 判定规则覆盖 RED/YELLOW/GREEN 三级\n\n---\n\n**交付物**:\n- docs/ex1/problem_spec.md (优化问题规格)\n- docs/ex1/prereg.md (预注册, append-only)\n- docs/ex1/evaluation_plan.md (三层评估计划)\n- docs/ex1/data_anchors.md (公开数据锚点)\n- docs/ex1/test_constraints.py (约束断言测试, 11/11 通过)\n\n**Git Commit**: 78ed109 (agent/m541 分支)\n\n---\n\n## 图件补充 (RPT-REWORK m583)\n\n> 本报告原无图件，经治理标记需补充。\n> 需补充图件：场量云图 + 比较曲线 + 误差分布。\n> 补充时间: 2026-10-30 22:41:46.0913+00。",
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
            "end_char": 30,
            "start_line": 0,
            "end_line": 0,
            "quote": "# EX-1 水池锚定①: DTMB 5415 艏部线型优化",
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
          "asset_class": "table",
          "label": "基线几何参数表（7 行）",
          "in_report_section": "### 基线几何参数",
          "locator": {
            "method": "char_span",
            "start_char": 164,
            "end_char": 447,
            "start_line": 8,
            "end_line": 16,
            "quote": "| 参数 | 符号 | 值 | 来源 |\n|------|------|----|----|\n| 垂线间长 | Lpp | 142.000 m | 官方定义 |\n| 型宽 | B | 19.000 m | 官方定义 |\n| 设计吃水 | T | 6.160 m | 官方定义 |\n| 排水体积 | ∇ | 8336.7 m³ | 官方定义 (exact) |\n| 方形系数 | Cb | 0.5018 | 验算值 |\n| 设计 Fr | Fr_d | 0.28 | CFDWS 标准 |\n| 设计航速 | V_d | 10.45 m/s | Fr=0.28 对应 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "表头+分隔行+7 行数据；数值仅登记不换算"
        },
        {
          "asset_id": "A04",
          "asset_class": "geometry_declaration",
          "label": "几何锁定状态（STL/点云/主尺度）",
          "in_report_section": "### 几何锁定状态",
          "locator": {
            "method": "char_span",
            "start_char": 460,
            "end_char": 556,
            "start_line": 19,
            "end_line": 21,
            "quote": "- 精确 STL: 164926 面, 7.9 MB, 15/15 门禁通过\n- 官方点云: 2250 点 (Zenodo 源), 逐点重合\n- 主尺度验证: Lpp/B/T/∇ 与官方值一致",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "三条声明的原文；资产本体（STL/点云文件）见 A17/A18"
        },
        {
          "asset_id": "A05",
          "asset_class": "statement",
          "label": "优化目标 min C_T(Fr=0.28)",
          "in_report_section": "### 优化问题定义",
          "locator": {
            "method": "char_span",
            "start_char": 579,
            "end_char": 603,
            "start_line": 26,
            "end_line": 26,
            "quote": "**目标**: min C_T(Fr=0.28)",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "单行目标声明"
        },
        {
          "asset_id": "A06",
          "asset_class": "design_space",
          "label": "设计变量定义（8 DOF，x1-x8）",
          "in_report_section": "### 优化问题定义",
          "locator": {
            "method": "char_span",
            "start_char": 605,
            "end_char": 697,
            "start_line": 28,
            "end_line": 31,
            "quote": "**设计变量**: 8 DOF 艏部参数化 (RBF 控制点)\n- x1-x3: 水线/甲板半宽变化\n- x4-x6: 球鼻艏垂向/横向/纵向位移\n- x7-x8: 甲板边线/曲率修正",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "含 8 DOF 声明行 + 3 条分组说明"
        },
        {
          "asset_id": "A07",
          "asset_class": "constraint_set",
          "label": "约束 C1-C7（可执行断言）",
          "in_report_section": "### 优化问题定义",
          "locator": {
            "method": "char_span",
            "start_char": 699,
            "end_char": 839,
            "start_line": 33,
            "end_line": 40,
            "quote": "**约束** (可执行断言 C1-C7):\n- C1: 排水量 ±0.5%\n- C2: 主尺度 Lpp/B/T 固定\n- C3: 艉部冻结 (x/Lpp>0.35 零位移)\n- C4: 最小曲率半径 ≥0.5m\n- C5: 光体无附体\n- C6: 水密性\n- C7: 设计变量范围",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "7 条约束原文；可执行实现体在 A19 引用的 test_constraints.py（未解析）"
        },
        {
          "asset_id": "A08",
          "asset_class": "parameter_set",
          "label": "速度矩阵（5 个 Fr 点 + 设计点权重）",
          "in_report_section": "### 优化问题定义",
          "locator": {
            "method": "char_span",
            "start_char": 841,
            "end_char": 897,
            "start_line": 42,
            "end_line": 42,
            "quote": "**速度矩阵**: 5 个 Fr 点 (0.14/0.21/0.28/0.35/0.41)，设计点权重 0.50",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "Fr 点与权重原文"
        },
        {
          "asset_id": "A09",
          "asset_class": "measurement_plan",
          "label": "三层评估方案（经验公式/CFD/水池）",
          "in_report_section": "### 三层评估方案",
          "locator": {
            "method": "char_span",
            "start_char": 910,
            "end_char": 1053,
            "start_line": 45,
            "end_line": 47,
            "quote": "1. **Layer 1**: Holtrop-Mennen 经验公式批量评估 (N≥100, ±10%)\n2. **Layer 2**: RANS CFD 抽查 (k-ω SST, N≥10, ±3%)\n3. **Layer 3**: 外协水池拖曳试验 (N=1-3+基线, ±1%)",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "各层样本量与不确定度原文"
        },
        {
          "asset_id": "A10",
          "asset_class": "prereg_lock",
          "label": "预注册锁定条目（4 条）",
          "in_report_section": "### 预注册锁定",
          "locator": {
            "method": "char_span",
            "start_char": 1065,
            "end_char": 1188,
            "start_line": 50,
            "end_line": 53,
            "quote": "- 预测改善区间: [2%, 8%] @ Fr=0.28\n- 判定规则: RED/YELLOW/GREEN 三级\n- 基线 C_T 参考值: 2.40e-3 (IIHR + CFDWS 均值)\n- append-only: 水池数据到手后不可修改",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "append-only 与判定规则原文；基线 C_T 单独登记为 A12"
        },
        {
          "asset_id": "A11",
          "asset_class": "prediction",
          "label": "预测改善区间（保守/乐观/最可能）",
          "in_report_section": "### 预测改善区间",
          "locator": {
            "method": "char_span",
            "start_char": 1621,
            "end_char": 1681,
            "start_line": 73,
            "end_line": 75,
            "quote": "- 保守: ≥2% @ Fr=0.28\n- 乐观: ≤8% @ Fr=0.28\n- 最可能: 4-5% (基于文献中值)",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "三条预测原文；属预测值非实测"
        },
        {
          "asset_id": "A12",
          "asset_class": "numeric_anchor",
          "label": "基线 C_T 参考值 2.40e-3（IIHR+CFDWS 均值）",
          "in_report_section": "### 预注册锁定",
          "locator": {
            "method": "char_span",
            "start_char": 1122,
            "end_char": 1161,
            "start_line": 52,
            "end_line": 52,
            "quote": "- 基线 C_T 参考值: 2.40e-3 (IIHR + CFDWS 均值)",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "单一数字锚点；外部出处为文献均值，报告未给可解析地址"
        },
        {
          "asset_id": "A13",
          "asset_class": "table",
          "label": "约束断言测试结果表（11 行）",
          "in_report_section": "### 约束断言测试 (11/11 通过)",
          "locator": {
            "method": "char_span",
            "start_char": 1224,
            "end_char": 1608,
            "start_line": 58,
            "end_line": 70,
            "quote": "| 测试用例 | 结果 | 说明 |\n|---------|------|------|\n| 基线通过 | ✅ | 零位移基线满足所有约束 |\n| 排水量超差 | ✅ | +1% 触发 C1 RED |\n| 排水量范围内 | ✅ | +0.4% 通过 |\n| 艉部位移 | ✅ | 1mm 位移触发 C3 RED |\n| 变量越界 | ✅ | x1=2.0 触发 C7 RED |\n| 判定 GREEN | ✅ | 改善 5% → GREEN |\n| 判定 YELLOW (低) | ✅ | 改善 1% → YELLOW |\n| 判定 YELLOW (高) | ✅ | 改善 10% → YELLOW |\n| 判定 RED | ✅ | 阻力增加 → RED |\n| 速度矩阵权重 | ✅ | sum=1.0 |\n| 设计航速 | ✅ | V_d=10.45 m/s |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "11 个用例的通过标记；测试代码本体在 A19 引用（未解析）"
        },
        {
          "asset_id": "A14",
          "asset_class": "figure_declaration",
          "label": "无图声明与待出图清单",
          "in_report_section": "## 4. 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 1694,
            "end_char": 1859,
            "start_line": 79,
            "end_line": 83,
            "quote": "本任务为纯文档/规格定义，无计算场量或对比曲线。图表说明:\n- **无图理由**: 本阶段为问题定义与预注册，尚未进行实际优化计算。待 Layer 2/3 完成后，将生成:\n  - 艏部参数化变形云图 (基线 vs 优化)\n  - C_T 改善率柱状图 (5 个 Fr 点)\n  - 阻力曲线对比 (基线 vs 优化 vs 文献)",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "platform_figures_field",
            "result": "absent",
            "platform_figures_count": 0,
            "detail": "报告声明本阶段无图，且平台 figures 字段为空"
          },
          "note": "报告声明本阶段无图；API figures 字段为空数组"
        },
        {
          "asset_id": "A15",
          "asset_class": "figure_slot",
          "label": "已声明待产图件（3 项）",
          "in_report_section": "## 4. 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 1781,
            "end_char": 1859,
            "start_line": 81,
            "end_line": 83,
            "quote": "  - 艏部参数化变形云图 (基线 vs 优化)\n  - C_T 改善率柱状图 (5 个 Fr 点)\n  - 阻力曲线对比 (基线 vs 优化 vs 文献)",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "platform_figures_field",
            "result": "absent",
            "platform_figures_count": 0,
            "detail": "报告声明本阶段无图，且平台 figures 字段为空"
          },
          "note": "计划中图件，尚未产出；不登记为现存资产"
        },
        {
          "asset_id": "A16",
          "asset_class": "limitation_set",
          "label": "局限与风险（4 条）",
          "in_report_section": "### 局限与风险",
          "locator": {
            "method": "char_span",
            "start_char": 2077,
            "end_char": 2221,
            "start_line": 94,
            "end_line": 97,
            "quote": "- **经验公式精度**: Holtrop-Mennen ±10%，仅用于初步筛选\n- **CFD 不确定度**: ±3% (网格/时间/数值)，需三套网格验证\n- **水池成本**: 50-100 万 RMB，周期 2-3 个月\n- **改善预期**: 文献范围 2-8%，实际可能偏离",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "精度/不确定度/成本/预期偏离原文"
        },
        {
          "asset_id": "A17",
          "asset_class": "external_dataset",
          "label": "精确 STL 几何（164926 面，7.9 MB）",
          "in_report_section": "### 几何锁定状态",
          "locator": {
            "method": "char_span",
            "start_char": 460,
            "end_char": 498,
            "start_line": 19,
            "end_line": 19,
            "quote": "- 精确 STL: 164926 面, 7.9 MB, 15/15 门禁通过",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "address_extraction",
            "result": "unresolved",
            "addresses_found": [],
            "detail": "仅在报告文本内检索 URL/DOI/绝对路径（不联网猜测地址）"
          },
          "note": "报告未给出可解析地址（无路径/URL/DOI），仅声明规模与门禁结果"
        },
        {
          "asset_id": "A18",
          "asset_class": "external_dataset",
          "label": "官方点云（2250 点，Zenodo 源）",
          "in_report_section": "### 几何锁定状态",
          "locator": {
            "method": "char_span",
            "start_char": 499,
            "end_char": 530,
            "start_line": 20,
            "end_line": 20,
            "quote": "- 官方点云: 2250 点 (Zenodo 源), 逐点重合",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "address_extraction",
            "result": "unresolved",
            "addresses_found": [],
            "detail": "仅在报告文本内检索 URL/DOI/绝对路径（不联网猜测地址）"
          },
          "note": "仅标注来源为 Zenodo，无 record id/DOI，无法在平台侧解析"
        },
        {
          "asset_id": "A19",
          "asset_class": "external_file_set",
          "label": "交付物清单（docs/ex1/ 5 个文件）",
          "in_report_section": "### 约束断言验证",
          "locator": {
            "method": "char_span",
            "start_char": 2874,
            "end_char": 3074,
            "start_line": 126,
            "end_line": 130,
            "quote": "- docs/ex1/problem_spec.md (优化问题规格)\n- docs/ex1/prereg.md (预注册, append-only)\n- docs/ex1/evaluation_plan.md (三层评估计划)\n- docs/ex1/data_anchors.md (公开数据锚点)\n- docs/ex1/test_constraints.py (约束断言测试, 11/11 通过)",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "docs/ex1/problem_spec.md",
              "docs/ex1/prereg.md",
              "docs/ex1/evaluation_plan.md",
              "docs/ex1/data_anchors.md",
              "docs/ex1/test_constraints.py"
            ],
            "missing": [
              "docs/ex1/problem_spec.md",
              "docs/ex1/prereg.md",
              "docs/ex1/evaluation_plan.md",
              "docs/ex1/data_anchors.md",
              "docs/ex1/test_constraints.py"
            ],
            "result": "unresolved"
          },
          "note": "仓库相对路径；本工作树（TensorKnowledge）内不存在，属外部仓库产物"
        },
        {
          "asset_id": "A20",
          "asset_class": "vcs_reference",
          "label": "Git Commit 78ed109（agent/m541 分支）",
          "in_report_section": "### 约束断言验证",
          "locator": {
            "method": "char_span",
            "start_char": 3076,
            "end_char": 3115,
            "start_line": 132,
            "end_line": 132,
            "quote": "**Git Commit**: 78ed109 (agent/m541 分支)",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "git_cat_file",
            "object": "78ed109",
            "result": "unresolved",
            "exit_code": 128
          },
          "note": "外部仓库提交号；本仓 git 对象库无法解析"
        },
        {
          "asset_id": "A21",
          "asset_class": "table",
          "label": "关键量 vs 基准误差表（6 行）",
          "in_report_section": "### 关键量 vs 基准",
          "locator": {
            "method": "char_span",
            "start_char": 2347,
            "end_char": 2694,
            "start_line": 107,
            "end_line": 114,
            "quote": "| 指标 | 本任务值 | 基准值 | 误差 | <3%? |\n|------|---------|--------|------|------|\n| Lpp | 142.000 m | 142.000 m (官方) | 0% | ✅ |\n| B | 19.000 m | 19.000 m (官方) | 0% | ✅ |\n| T | 6.160 m | 6.160 m (官方) | 0% | ✅ |\n| ∇ | 8336.7 m³ | 8336.7 m³ (官方) | 0% | ✅ |\n| Cb | 0.5018 | 0.5018 (文献) | 0% | ✅ |\n| 基线 C_T (Fr=0.28) | 2.40e-3 | 2.40e-3 (IIHR+CFDWS) | 0% | ✅ |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "上游自报 0% 误差；本工序只登记不复核"
        },
        {
          "asset_id": "A22",
          "asset_class": "external_note",
          "label": "图件补充要求（RPT-REWORK m583 治理标记）",
          "in_report_section": "### 约束断言验证",
          "locator": {
            "method": "char_span",
            "start_char": 3122,
            "end_char": 3233,
            "start_line": 136,
            "end_line": 140,
            "quote": "## 图件补充 (RPT-REWORK m583)\n\n> 本报告原无图件，经治理标记需补充。\n> 需补充图件：场量云图 + 比较曲线 + 误差分布。\n> 补充时间: 2026-10-30 22:41:46.0913+00。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "治理标记：报告曾因缺图被要求补图；标记不含图件本体"
        }
      ],
      "claims": [],
      "claims_note": "按工作包契约 objective.classify_report_type=false 且 notes 允许 claims 为空数组：本工序只登记资产定位，不做 claim 抽取；claim 抽取由下游工作包负责。",
      "integrity": {
        "quote_uniqueness": "all quotes confirmed unique substrings of source markdown (scripts/kf_verify_448.py, checks.source_locator_resolvable)",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true
      }
    }
  }
}
```
