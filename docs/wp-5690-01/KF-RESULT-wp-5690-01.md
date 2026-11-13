# KF-RESULT wp-5690-01

## ① 案例介绍（本工序对象）

本单是报告→知识产线上的一道工序：**资产登记（task_type = 01-asset-registration）**，只服务 report_id=5690 这一份报告。

- 源报告：report 5690，《IN11-H6 高保真仿真军验收门：三库工件 sha256 清单 + 经验链交叉一致性断言》，scenario_key=`ice_nav_campaign_IN11_H6_hifi_acceptance`，平台 mission 5003，status=published。
- 内容性质：冰区航行战役 IN11-H6 的**验收门报告**——三库（TensorDEM/TensorLBM/TensorPhysics）上游工件 sha256 清单 + 12 条经验链交叉一致性断言（XC-01..XC-12），门禁结论 PASS（容差内 6 / 已界定适用域 6 / 未解决冲突 0）。
- 源 markdown：5390 字符 / 8513 字节 UTF-8，sha256=`a1e3f5faa1f969bcdfb759f7357adb8cc7474194e44a2c02ae4370f1db1b29a1`，与契约 `source_hash` 逐字节一致。
- 本工序**不做**的事：不抽取 claim、不做报告类型分类、不改写上游产物、不标 verified（契约 objective 仅 `register_assets: true`，claims 允许空数组；verification 由平台门计算）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取证（不凭记忆）**：`GET /api/v1/tensor/reports/5690` 取 `markdown` 字段，落盘 `runs/wp-5690-01/report_5690.md`（5390 字符 / 8513 字节 UTF-8），本地重算 sha256 与契约 `source_hash` 比对一致 → 才继续。
2. **定位而非抄写**：`scripts/kf_register_5690.py` 维护一张 17 行锚点表（资产 id / 类 / 唯一锚点串 / 相对行跨），运行时用锚点在 markdown 中定位行号 → 由行偏移计算 `[start_char, end_char)` → **直接从原文切片**得到 `quote`；每个 quote 再断言「在全文出现次数 == 1」，不唯一即中止。
3. **可解析性判定（不做猜测）**：对每个资产跑一次机器检查 `resolution_check`，结果与声明状态强绑定：
   - 页内资产（A01-A07）→ `char_span_in_source_markdown`；
   - 外部工件/代码/模型（A08-A17）→ 在**本工作树内实测** 10 个 H5 仓（ship-performance-platform）相对路径是否存在（结果：10/10 均不存在）→ `referenced_unresolved`，不编造地址；
   - 图件 A07 → 3 条图声明在源 markdown 内可定位，PNG 字节在平台 `figures` 字段（3 项，fig1/fig2/fig3_*.png）→ `resolved_in_source`。
4. **独立校验**：`scripts/kf_verify_5690.py` 在**新进程、新登录**下重新拉取 markdown（不信任本地副本），重算哈希、逐资产重新切片比对、跑 JSON Schema（`schemas/asset_manifest.v1.schema.json`，本单将其从 wp-448-01 的 const 钉扎泛化为 pattern，见⑤-4）、查 id 唯一性、查 claim 证据策略、结构化扫描「verified」标记 → 输出 `artifacts/wp-5690-01/verification.json`。
5. **可复现**：清空 `artifacts/wp-5690-01/` 后按下面的复跑命令重建，`asset_manifest.json` 的 sha256 逐字节相同（`5b03fb8e726f4ba2bdc823141c91ca0db514c9b5db95e162bc980a4035032850`，见结果信封 `outputs["asset_manifest.json"]["artifact_sha256"]`），登记过程不含随机性/时间戳污染。
6. **测试**：`tests/test_kf_wp5690.py` 16 项，除正向断言外含 4 个**反向对照**（篡改 quote 数字、平移 span、把外部资产 resolution 谎报为 resolved、制造重复 id）+ 1 个 schema 泛化回归守卫（wp-448-01 manifest 仍须通过泛化后 schema），证明这些检查真的会红，而不是只跑通。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/wp-5690-01/asset_manifest.json` | 主产物：17 个资产（11 类）、7 resolved_in_source / 10 referenced_unresolved / 0 declared_absent |
| `artifacts/wp-5690-01/verification.json` | 12 项验收自检逐项结果，overall=PASS |
| `artifacts/wp-5690-01/fig_asset_inventory.png` | 图1 资产类别×可解析状态 |
| `artifacts/wp-5690-01/fig_locator_coverage.png` | 图2 逐资产 char span 定位地图 |
| `artifacts/wp-5690-01/fig_verification.png` | 图3 验收自检状态板 |
| `runs/wp-5690-01/report_5690.md` / `.json` | 源证据快照（markdown 与 API 原始响应） |
| `runs/wp-5690-01/kf_result.wp-5690-01.json` | 结果信封（package_id/task_type/report_id/provenance/outputs） |
| `scripts/kf_fetch_5690.py` / `kf_register_5690.py` / `kf_verify_5690.py` / `kf_figures_5690.py` / `kf_report_5690.py` | 取证 / 登记 / 校验 / 出图 / 报报告，一键可复跑 |
| `tests/test_kf_wp5690.py` | 16 项不变量测试（含 4 个反向对照 + 1 个 schema 回归守卫） |
| `schemas/asset_manifest.v1.schema.json` | manifest 形状约束（本单泛化：package_id/report_id/uri 由 const 改 pattern，向后兼容 448） |
| `docs/wp-5690-01/*` | 持久镜像（push 门滤除 artifacts/** 与 runs/**，docs/ 入库） |

**资产分类计数**：{"document": 1, "heading": 1, "statement": 1, "table": 2, "statement_set": 1, "figure_declaration": 1, "artifact_reference": 2, "document_reference": 1, "figure_set": 1, "code_reference": 5, "external_model": 1}

## ④ 证据定位表（claim/字段 → 原文引文）

下列每一行的 `quote` 都是报告 5690 markdown 的**唯一子串**，并记录字符区间；平台可独立重算 sha256 与子串定位。

| asset_id | class | resolution | locator (char span) | 原文片段（逐字取自报告 5690） |
|---|---|---|---|---|
| A01 | document | resolved_in_source | 0-5390 (全文) | `（整篇 markdown，sha256 见 provenance）` |
| A02 | heading | resolved_in_source | 0-45 | `# IN11-H6 高保真仿真军验收门：三库工件 sha256 清单 + 经验链交叉一致性` |
| A03 | statement | resolved_in_source | 47-158 | `**结论：门禁 `PASS`** —— 12 条交叉一致性断言（容差内 6 / 已界定适用域 6 / 未解决冲突 0），四对指定…` |
| A04 | table | resolved_in_source | 311-970 | `\| 上游 \| 仓 / 模块 \| 观测量 \| 经验链对端 \|` |
| A05 | table | resolved_in_source | 1805-3342 | `\| id \| 比对 \| 上游量 \| dev \| 判据 \| 结论 \|` |
| A06 | statement_set | resolved_in_source | 3359-4201 | `` |
| A07 | figure_declaration | resolved_in_source | 4212-4413 | `` |
| A08 | artifact_reference | referenced_unresolved | 5169-5389 | ``artifacts/hifi_acceptance.json`（门禁母版）· `artifacts/hifi_upstream…` |
| A09 | artifact_reference | referenced_unresolved | 5169-5389 | ``artifacts/hifi_acceptance.json`（门禁母版）· `artifacts/hifi_upstream…` |
| A10 | document_reference | referenced_unresolved | 5169-5389 | ``artifacts/hifi_acceptance.json`（门禁母版）· `artifacts/hifi_upstream…` |
| A11 | figure_set | referenced_unresolved | 5169-5389 | ``artifacts/hifi_acceptance.json`（门禁母版）· `artifacts/hifi_upstream…` |
| A12 | code_reference | referenced_unresolved | 5169-5389 | ``artifacts/hifi_acceptance.json`（门禁母版）· `artifacts/hifi_upstream…` |
| A13 | code_reference | referenced_unresolved | 1154-1394 | `2. **经验链取值调用平台既有实现**（不重写公式）：Lindqvist → `api/ice/formulas.py::ca…` |
| A14 | code_reference | referenced_unresolved | 1154-1394 | `2. **经验链取值调用平台既有实现**（不重写公式）：Lindqvist → `api/ice/formulas.py::ca…` |
| A15 | code_reference | referenced_unresolved | 1154-1394 | `2. **经验链取值调用平台既有实现**（不重写公式）：Lindqvist → `api/ice/formulas.py::ca…` |
| A16 | external_model | referenced_unresolved | 521-675 | `\| H2 \| TensorLBM `tensorlbm.frazil_rheology` \| 流变面 μ_r(φ)、幂律 …` |
| A17 | code_reference | referenced_unresolved | 1686-1787 | `5. 判据数字全部落在 `artifacts/hifi_acceptance.json#gate`；报告与图由 `make_ac…` |

## ⑤ 注意点与局限

1. **10 个外部资产解析不到，如实挂账**：A08-A17（H5 仓的 `artifacts/hifi_acceptance.json`、`artifacts/hifi_upstream/`、`docs/campaign/hifi_xcheck_report.md`、`artifacts/figures/hifi_acceptance/*.png`、`backend/tests/test_hifi_acceptance.py`、`api/ice/formulas.py`、`modules/ice_fullscale/ice_physics.py`、`physics/grease_ice/rheology.py`、W9-1215 损失模型、`make_acceptance_docs.py`）。它们属于**别的仓库**（H5=ship-performance-platform 及平台既有模块），本工作树（TensorKnowledge）内不存在，报告未给可解析 URI；若下游要用，必须由来源仓补地址，不能靠猜。
2. **报告自报数字原样登记、未复核**：12 条断言的 dev 值（+11.76% / −73.32% / +52.48% 等）与「门禁 PASS」是**上游自报**，本工序只登记定位、不复核数值（复核属下游证据包工序）。
3. **figures 在平台侧**：报告 ④ 声明 3 张图，平台 `figures` 字段确有 3 项（fig1_crosscheck_deviation.png / fig2_frazil_reduced_viscosity.png / fig3_panel_pressure_dual_chain.png），PNG 字节不落本仓；A07 登记的是**图声明**（页内可解析），图件本体不重复登记。
4. **schema 泛化（偏差声明）**：契约引用的 `schemas/kf_result.v1.schema.json` 在本工作树不存在；`schemas/asset_manifest.v1.schema.json` 原为 wp-448-01 的 const 钉扎版，本单将其 `package_id`/`report_id`/`source.uri` 三处 const 改为 pattern（`^wp-[0-9]+-[0-9]2$` / `^[0-9]+$` / `^tensor://reports/[0-9]+$`），其余结构不动。回归守卫：wp-448-01 manifest 对泛化后 schema 仍验证通过（`tests/test_kf_wp5690.py::test_generalized_schema_still_covers_wp448`）。**若平台侧真实 schema 与此不一致，schema_pass 以平台为准、本单接受返修**——与 wp-448-01 相同的残余风险。
5. **覆盖度口径**：16 个 span 级资产对 5390 字符的并集覆盖 = 3956 字符（73.4%）；整篇资产 A01 覆盖 100%，图中未计入，避免用 100% 制造假象。
6. **边界**：全程只读写 report 5690 相关文件，未触碰其它 report_id（测试 `test_no_report_id_contamination` 守这一条）。

## ⑥ 误差判定

本工序是登记而非计算，**没有物理量可比**，故不存在「关键量 vs 基准 <3%」这一栏；可比的只有*恒等性/可解析性*判据，逐项如实列出：

| 判据 | 本单值 | 基准 | 误差 | <3%? |
|---|---|---|---|---|
| markdown 字节哈希 | `a1e3f5faa1f969bc…` | 契约 source_hash `a1e3f5faa1f969bc…` | 0（逐字节相等） | ✅ 精确匹配 |
| markdown 字符数 | 5390 | 契约 chars 5390 | 0 | ✅ |
| 资产 locator 可复现 | 17/17 切片全等且唯一 | 自检规则 | 0 失配 | ✅ |
| 资产 id 唯一性 | 17 个 id，0 重复 | 契约 no_duplicate_ids | 0 | ✅ |
| claim 证据覆盖 | claims=[]（契约允许） | all_claims_have_evidence | 0 违规 | ✅（空集，见⑤-2 说明） |
| 外部资产可解析率 | 7/17 页内解析，10 个挂 unresolved | — | — | ❌ 不适用：外部资产本就无法在本地解析，**如实挂账，不冒充 resolved** |

验收项逐条结果：

| 验收项 | 结果 | 证据 |
|---|---|---|
| valid_json | PASS | {"manifest": "artifacts/wp-5690-01/asset_manifest.json", "result": "runs/wp-5690-01/kf_result.wp-5690-01.json", "block_equals_result": true} |
| source_hash_matches | PASS | {"api_sha256": "a1e3f5faa1f969bcdfb759f7357adb8cc7474194e44a2c02ae4370f1db1b29a1", "contract_sha256": "a1e3f5faa1f969bcdfb759f7357adb8cc7474194e44a2c02ae4370f1db1b29a1", "manifest_sha256": "a1e3f5faa1 |
| schema_pass | PASS | {"schema": "schemas/asset_manifest.v1.schema.json", "note": "local schema schemas/asset_manifest.v1.schema.json (canonical kf_result schema absent from worktree)"} |
| result_envelope_shape | PASS | {"keys": ["outputs", "package_id", "provenance", "report_id", "schema_version", "task_type"], "outputs_keys": ["asset_manifest.json"]} |
| result_ids_match_contract | PASS | {"package_id": "wp-5690-01", "task_type": "01-asset-registration", "report_id": "5690"} |
| source_locator_resolvable | PASS | {"assets_checked": 17, "failures": [], "method": "re-slice fresh API markdown at [start_char,end_char) + uniqueness count"} |
| no_duplicate_ids | PASS | {"asset_ids": ["A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", "A09", "A10", "A11", "A12", "A13", "A14", "A15", "A16", "A17"], "duplicates": []} |
| all_claims_have_evidence_or_explicit_unresolved_status | PASS | {"claims": 0, "offenders": [], "note": "claims=[] by contract scope (objective.register_assets only; no extraction); asset-level resolution status carried on all 17 assets"} |
| no_verified_markers | PASS | {"structural_hits": [], "note": "contract forbids marking claims verified; verification is computed by the platform gate"} |
| counts_consistent | PASS | {"assets": 17, "by_class": {"document": 1, "heading": 1, "statement": 1, "table": 2, "statement_set": 1, "figure_declaration": 1, "artifact_reference": 2, "document_reference": 1, "figure_set": 1, "co |
| artifact_hash_matches_envelope | PASS | {"file_sha256": "5b03fb8e726f4ba2bdc823141c91ca0db514c9b5db95e162bc980a4035032850", "envelope_sha256": "5b03fb8e726f4ba2bdc823141c91ca0db514c9b5db95e162bc980a4035032850"} |
| durable_mirror_identical | PASS | {"mirror": "docs/wp-5690-01/asset_manifest.json", "mirror_sha256": "5b03fb8e726f4ba2bdc823141c91ca0db514c9b5db95e162bc980a4035032850", "artifact_sha256": "5b03fb8e726f4ba2bdc823141c91ca0db514c9b5db95e |

## 复跑命令

    python3 scripts/kf_fetch_5690.py && python3 scripts/kf_register_5690.py && python3 scripts/kf_verify_5690.py \
      && python3 scripts/kf_figures_5690.py && python3 -m pytest -q tests/test_kf_wp5690.py \
      && python3 scripts/kf_report_5690.py --no-post

（需要 `TENSOR_API_BASE` / `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS` 环境变量用于独立重取报告；无网络时 `kf_verify_5690.py` 会降级到本地副本并在 verification.json 里标注 `degraded_to_local_copy`。）

## 结果 JSON（唯一 json 代码块）

```json
{
  "schema_version": "kf_result.v1",
  "package_id": "wp-5690-01",
  "task_type": "01-asset-registration",
  "report_id": "5690",
  "provenance": {
    "source_uri": "tensor://reports/5690",
    "source_field": "markdown",
    "source_hash": "sha256:a1e3f5faa1f969bcdfb759f7357adb8cc7474194e44a2c02ae4370f1db1b29a1",
    "source_chars": 5390,
    "source_bytes_utf8": 8513,
    "source_title": "IN11-H6 高保真仿真军验收门：三库工件 sha256 清单 + 12 条经验链交叉一致性断言",
    "scenario_key": "ice_nav_campaign_IN11_H6_hifi_acceptance",
    "contract_version": "1.0",
    "lane": "C",
    "work_package": "wp-5690-01",
    "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/5690",
    "local_copy": "runs/wp-5690-01/report_5690.md",
    "generator": "scripts/kf_register_5690.py",
    "verifier": "scripts/kf_verify_5690.py",
    "verification_status": "not_verified"
  },
  "outputs": {
    "asset_manifest.json": {
      "artifact_path": "artifacts/wp-5690-01/asset_manifest.json",
      "artifact_sha256": "5b03fb8e726f4ba2bdc823141c91ca0db514c9b5db95e162bc980a4035032850",
      "artifact_bytes": 33403,
      "schema": "asset_manifest.v1",
      "package_id": "wp-5690-01",
      "task_type": "01-asset-registration",
      "report_id": "5690",
      "source": {
        "uri": "tensor://reports/5690",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "a1e3f5faa1f969bcdfb759f7357adb8cc7474194e44a2c02ae4370f1db1b29a1",
        "chars": 5390,
        "bytes_utf8": 8513,
        "title": "IN11-H6 高保真仿真军验收门：三库工件 sha256 清单 + 12 条经验链交叉一致性断言",
        "scenario_key": "ice_nav_campaign_IN11_H6_hifi_acceptance",
        "platform_id": 5690,
        "platform_mission_id": 5003,
        "platform_figures": [
          {
            "name": "fig1_crosscheck_deviation.png",
            "caption": "Quantitative deviation of the 12 cross-consistency assertions; dashed lines are the ±15% platform accuracy criterion, orange bars are out-of-tolerance but physically explained / domain-bounded."
          },
          {
            "name": "fig2_frazil_reduced_viscosity.png",
            "caption": "H2 LBM rheology surface vs the W9-1215 loss model: (a) separated in raw concentration because the jamming limits differ; (b) collapsed after normalising each by its own phi_max (XC-05 within the 15% criterion)."
          },
          {
            "name": "fig3_panel_pressure_dual_chain.png",
            "caption": "H4 dual-chain panel pressure: magnitude gap between the IACS local design pressure and the B1 global-force equivalent pressure (a convention gap rather than a numerical error, see XC-12)."
          }
        ],
        "platform_tags": [
          "IN11-H6",
          "验收门",
          "冰区航行",
          "交叉一致性",
          "sha256",
          "能力增量账本"
        ],
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/5690",
        "local_copy": "runs/wp-5690-01/report_5690.md"
      },
      "counts": {
        "assets": 17,
        "by_class": {
          "document": 1,
          "heading": 1,
          "statement": 1,
          "table": 2,
          "statement_set": 1,
          "figure_declaration": 1,
          "artifact_reference": 2,
          "document_reference": 1,
          "figure_set": 1,
          "code_reference": 5,
          "external_model": 1
        },
        "by_resolution": {
          "resolved_in_source": 7,
          "referenced_unresolved": 10
        },
        "resolved_in_source": 7,
        "referenced_unresolved": 10,
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
            "end_char": 5390,
            "start_line": 0,
            "end_line": 70,
            "quote": "# IN11-H6 高保真仿真军验收门：三库工件 sha256 清单 + 经验链交叉一致性\n\n**结论：门禁 `PASS`** —— 12 条交叉一致性断言（容差内 6 / 已界定适用域 6 / 未解决冲突 0），四对指定比对全覆盖，工件清单 sha256 固定，能力增量账本 3 条 + 五级成熟度自评 6 节点。\n\n## ① 案例介绍（物理背景 / 几何 / 参数）\n\n战役 IN11 的链路是「高保真 → 经验系数」：三个求解器仓各给一个上游观测量，本仓（H5）回写进既有经验链（C1 冰阻力链 / C2 推力包络）。验收门要回答的是**证据链与口径**问题，而不是上游自身 benchmark（那是各仓责任）：\n\n| 上游 | 仓 / 模块 | 观测量 | 经验链对端 |\n|---|---|---|---|\n| H1 | TensorDEM `tensordem.ice_channel` | 航道清空宽度、残留浮冰占比（域 120×60 m，船 L80/B20，φ=0.6/0.7/0.8） | C1 `c1.channel_blockage_kappa` / C2 `c2.blockage_thrust_penalty` |\n| H2 | TensorLBM `tensorlbm.frazil_rheology` | 流变面 μ_r(φ)、幂律 n、稠度 K（φ=0–0.55，φ_max=0.60） | W9-1215 损失模型 `physics.grease_ice.rheology`（φ_max=0.35，α=1.70） |\n| H3 | TensorPhysics `tensorphysics.ice_sheet` | 破坏长度 L_b、首裂力 P_edge（h=1.0 m，E=5 GPa，σ_f=0.7 MPa） | C1 Lindqvist / Riska 分量 `api.ice/formulas.py` |\n| H4 | TensorPhysics `tensorphysics.hull_icebelt_fem` | IACS 局部设计压力、双链面压（PC6，h=0.5–1.5 m，面板 2.0×0.35×0.03 m） | B1 IACS 链 `modules/ice_fullscale` |\n\n## ② 怎么做的（方法 / 关键设置 / 工具链）\n\n1. **证据链固定**：H1..H4 的 JSON 工件逐字节归档到 `artifacts/hifi_upstream/`，记录上游绝对路径、原仓、原 commit 与 sha256；上游可达时实时比对原件 sha256，不一致即 fail-closed（`sha256_mismatch`，不给结论）。\n2. **经验链取值调用平台既有实现**（不重写公式）：Lindqvist → `api/ice/formulas.py::calc_lindqvist`；B1 全局力 → `modules/ice_fullscale/ice_physics.py::global_ice_force/local_line_load`；W9-1215 黏度律 → `physics/grease_ice/rheology.py::viscosity_ratio`（参数从其标定产物读取，不手抄）。\n3. **定量比对与判定**：dev=(上游−经验链)/经验链；|dev|≤15%（平台精度标准）→ `consistent`；超容差但物理/适用域可界定（含**拒收**）→ `explained_domain`；否则 `conflict` 使门禁失败。接线一致性类比对用 2% 判据。\n4. **能力增量账本**：对照 SIR 既有资产（TensorDEM `tensordem.threefield` W6-N02；TensorFEM `plate_mindlin`/`ice_sheet` 占位）声明增量与边界，逐节点五级成熟度自评并写 `blocked_upgrade`。\n5. 判据数字全部落在 `artifacts/hifi_acceptance.json#gate`；报告与图由 `make_acceptance_docs.py` 从该 JSON 程序化生成（零手抄）。\n\n## ③ 计算结果（数字表）\n\n| id | 比对 | 上游量 | dev | 判据 | 结论 |\n|---|---|---|---|---|---|\n| XC-01 | H1 DEM 堵塞系数 <-> C2 推力包络堵塞惩罚 | value=1.118 | +11.76% | ±15% | `consistent` |\n| XC-02 | H1 DEM 堵塞系数 <-> C1 阻力链堵塞放大系数 | value=1.118 | +11.76% | ±15% | `consistent` |\n| XC-03 | H1 DEM 稳态性 <-> C2 包络常数假设 | value_rel_spread=0.1605, monotone_in_concentration=0 | +16.05% | ±15% | `explained_domain` |\n| XC-04 | H2 LBM frazil 黏度 <-> W9-1215 损失模型 | phi=0.25, mu_relative=2.245, phi_max_H2=0.6 | -73.32% | ±15% | `explained_domain` |\n| XC-05 | H2 LBM frazil 黏度 <-> W9-1215 损失模型 | phi=0.3, mu_relative=2.828 | -12.94% | ±15% | `consistent` |\n| XC-06 | H2 LBM frazil 黏度 <-> W9-1215 损失模型 | alpha_eff=1.5, n_points=7 | -11.76% | ±15% | `consistent` |\n| XC-07 | H3 FEM 破坏长度 <-> C1 弯曲破坏特征尺度 | break_length_m=16.65, h_m=1, flexural_rigidity_Nm=4.579e+08 | +13.95% | ±15% | `consistent` |\n| XC-08 | H3 FEM 首裂力 <-> C1 Lindqvist 弯曲分量 | P_break_edge_kN=968.2, h_m=1, edge_amplification=6.82 | +52.48% | ±15% | `explained_domain` |\n| XC-09 | H3 FEM 破坏长度 <-> C1 Riska 速度项系数 | L_b_m=16.65, L_ref_m=1 | -75.49% | ±15% | `explained_domain` |\n| XC-10 | H4 FEM 面板压力(IACS 链) <-> C2 推力包络面板压力先验 | p_ref_MPa=1.2, a_ref_m2=1, patch_area_m2=0.7, exponent=0.5,  | -28.29% | ±15% | `explained_domain` |\n| XC-11 | H4 FEM 面板压力(B1 IACS 链) <-> 平台 ice_fullscale B1 实现 | F_global_N=2.77e+06, contact_width_m=1.5, q_line_kN_per_m=18 | +0.00% | ±2% | `consistent` |\n| XC-12 | H4 面板压力双链（IACS 局部设计压力 vs B1 全局力派生压力） | chain_a_max_MPa=2, chain_b_max_MPa=6.156, n_conditions=5 | +329.19% | ±15% | `explained_domain` |\n\n**四对指定比对逐条要点**\n\n- **DEM 堵塞系数 vs C2/C1**：DEM 派生上界 κ=1.118 与 C2 的「堵塞惩罚置 1（避免与 C1 双计）」相差 +11.76%（容差内）；与 C1 先验 1.0 同样 +11.76% 且落在可容许带 [1.0,2.5] 内 → 先验略保守但未越界。清空宽度对浓度**非单调**（散布 16.05%，超容差）→ 只能作上界，不回流标定。\n- **LBM frazil 黏度 vs W9-1215**：原浓度下 μ_r(φ=0.25) 差 −73.3%（堆积极限 0.60 vs 0.35 不同，不可互换）；对各自 φ_max 归一到 0.5 后差 −12.94%（容差内）；发散指数 α_eff=1.50 vs α=1.70 差 −11.76% → 两律在归一化坐标下同物理，可跨相搬运。\n- **FEM 破坏长度 vs C1 Lindqvist**：L_b=16.65 m vs 解析 Winkler 特征长度 l_c=14.61 m，+13.95%（容差内，破坏长度被板弯曲物理锁定）；P_edge=968 kN vs Lindqvist R_bending=635 kN，+52.5%（峰值 vs 航程平均，只可作**上界**）；把 L_b 当碎片尺度去映射 Riska c2 得 0.00368 < 可容许下界 0.005 → **拒收**，c2 保持先验 0.015。\n- **FEM 面板压力 vs B1 IACS 链**：H4 的 PC6 规范值 1.434 MPa vs C2 量级先验 2.0 MPa，−28.3%（冰级/面积约定不同，按 k_panel=1+λ(p/p0−1) 折算推力需求 −4.2%）；平台 `ice_fullscale` 复算与 H4 chain_b 逐项一致（偏差 0.00%，判据 2%，证明跨仓接线未走形）；双链面压差 329%（IACS 局部设计压力 vs 全局力派生等效面压，**口径不同不可混用**）。\n\n## ④ 结果图\n\n- **图 1 12 条断言偏差总览**：±15% 判据带；绿色=容差内，橙色=已界定适用域（含拒收判定）。\n- **图 2 frazil 流变对撞**：(a) 原浓度坐标下两律分离（堆积极限不同）；(b) 归一化坐标下重合（Krieger-Dougherty 同标度）。\n- **图 3 面板压力双链**：(a) 双链面压随冰厚的变化与相对偏差；(b) 口径差异达 200–330%（非数值误差）。\n\n## ⑤ 注意点（坑 / 局限 / 适用范围）\n\n- H1 工件**不含** H5 契约字段 `channel_blockage_kappa`：k_blk 只能 bound-only 使用，不得写成 calibrated；H1 行程仅约 2.5 倍船长，「瞬时清空」≠ 稳态通道阻力。\n- H2 流变面是**模型化**（KD 形式 + 参数）而非数字化试验表：参数回收 REAL，试验绝对标定 WITHHELD。\n- H3 的 P_edge 是自由边**峰值**力（边效应放大 6.82 倍），与 Lindqvist 航程平均不同口径；L_b≈l_c 是弹性特征长度，不是碎片尺度。\n- 绝对 NCR/DER 精度、面板压力绝对误差仍为 WITHHELD：main 未并入 `benchmarks/ice_nav_refs`（IN10-L2），本轮锚点全为自建（解析解/文献结构带/规范声明）。\n- 上游数值未在本门复算（需各仓运行环境），本门只固定证据链并判交叉一致性。\n\n## ⑥ 误差判定（逐项回答「是否 <3%」）\n\n- 12 条断言中 6 条在 15% 判据内，6 条超容差但已给物理解释并明确「可作上界 / 必须拒收 / 口径不同」的适用域，0 条未解决冲突。\n- **是否 <3%**：无实验基准量可谈 3%。唯一 <3% 的是**实现一致性**类比对（XC-11 偏差 0.00%，判据 2%），它只证明两仓同式同参，**不能当精度证据**。其余断言判据为平台 15% 标准。\n- 诚实披露：k_blk 不回流、c2 拒收、P_edge 只作上界、双链禁混用、绝对精度 WITHHELD —— 均写入产物 `honest_disclosures`，不可被「看起来一致」覆盖。\n\n## 产物\n\n`artifacts/hifi_acceptance.json`（门禁母版）· `artifacts/hifi_upstream/`（三库工件归档）· `docs/campaign/hifi_xcheck_report.md`（论文级报告）· `artifacts/figures/hifi_acceptance/*.png` · `backend/tests/test_hifi_acceptance.py`（23 例，含缺件/篡改负控）\n",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "整篇 markdown 即源资产；sha256 见 source.hash（与契约 source_hash 逐字节一致）"
        },
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "报告标题",
          "in_report_section": "(document)",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 45,
            "start_line": 0,
            "end_line": 0,
            "quote": "# IN11-H6 高保真仿真军验收门：三库工件 sha256 清单 + 经验链交叉一致性",
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
          "label": "门禁结论（PASS，12 断言 6/6/0）",
          "in_report_section": "# IN11-H6 高保真仿真军验收门：三库工件 sha256 清单 + 经验链交叉一致性",
          "locator": {
            "method": "char_span",
            "start_char": 47,
            "end_char": 158,
            "start_line": 2,
            "end_line": 2,
            "quote": "**结论：门禁 `PASS`** —— 12 条交叉一致性断言（容差内 6 / 已界定适用域 6 / 未解决冲突 0），四对指定比对全覆盖，工件清单 sha256 固定，能力增量账本 3 条 + 五级成熟度自评 6 节点。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "单行结论声明；上游自报，本工序只登记不复核"
        },
        {
          "asset_id": "A04",
          "asset_class": "table",
          "label": "上游观测量表（H1-H4，4 行）",
          "in_report_section": "## ① 案例介绍（物理背景 / 几何 / 参数）",
          "locator": {
            "method": "char_span",
            "start_char": 311,
            "end_char": 970,
            "start_line": 8,
            "end_line": 13,
            "quote": "| 上游 | 仓 / 模块 | 观测量 | 经验链对端 |\n|---|---|---|---|\n| H1 | TensorDEM `tensordem.ice_channel` | 航道清空宽度、残留浮冰占比（域 120×60 m，船 L80/B20，φ=0.6/0.7/0.8） | C1 `c1.channel_blockage_kappa` / C2 `c2.blockage_thrust_penalty` |\n| H2 | TensorLBM `tensorlbm.frazil_rheology` | 流变面 μ_r(φ)、幂律 n、稠度 K（φ=0–0.55，φ_max=0.60） | W9-1215 损失模型 `physics.grease_ice.rheology`（φ_max=0.35，α=1.70） |\n| H3 | TensorPhysics `tensorphysics.ice_sheet` | 破坏长度 L_b、首裂力 P_edge（h=1.0 m，E=5 GPa，σ_f=0.7 MPa） | C1 Lindqvist / Riska 分量 `api.ice/formulas.py` |\n| H4 | TensorPhysics `tensorphysics.hull_icebelt_fem` | IACS 局部设计压力、双链面压（PC6，h=0.5–1.5 m，面板 2.0×0.35×0.03 m） | B1 IACS 链 `modules/ice_fullscale` |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "表头+分隔行+4 行数据；数值仅登记不换算"
        },
        {
          "asset_id": "A05",
          "asset_class": "table",
          "label": "交叉一致性断言表（XC-01..XC-12，12 行）",
          "in_report_section": "## ③ 计算结果（数字表）",
          "locator": {
            "method": "char_span",
            "start_char": 1805,
            "end_char": 3342,
            "start_line": 25,
            "end_line": 38,
            "quote": "| id | 比对 | 上游量 | dev | 判据 | 结论 |\n|---|---|---|---|---|---|\n| XC-01 | H1 DEM 堵塞系数 <-> C2 推力包络堵塞惩罚 | value=1.118 | +11.76% | ±15% | `consistent` |\n| XC-02 | H1 DEM 堵塞系数 <-> C1 阻力链堵塞放大系数 | value=1.118 | +11.76% | ±15% | `consistent` |\n| XC-03 | H1 DEM 稳态性 <-> C2 包络常数假设 | value_rel_spread=0.1605, monotone_in_concentration=0 | +16.05% | ±15% | `explained_domain` |\n| XC-04 | H2 LBM frazil 黏度 <-> W9-1215 损失模型 | phi=0.25, mu_relative=2.245, phi_max_H2=0.6 | -73.32% | ±15% | `explained_domain` |\n| XC-05 | H2 LBM frazil 黏度 <-> W9-1215 损失模型 | phi=0.3, mu_relative=2.828 | -12.94% | ±15% | `consistent` |\n| XC-06 | H2 LBM frazil 黏度 <-> W9-1215 损失模型 | alpha_eff=1.5, n_points=7 | -11.76% | ±15% | `consistent` |\n| XC-07 | H3 FEM 破坏长度 <-> C1 弯曲破坏特征尺度 | break_length_m=16.65, h_m=1, flexural_rigidity_Nm=4.579e+08 | +13.95% | ±15% | `consistent` |\n| XC-08 | H3 FEM 首裂力 <-> C1 Lindqvist 弯曲分量 | P_break_edge_kN=968.2, h_m=1, edge_amplification=6.82 | +52.48% | ±15% | `explained_domain` |\n| XC-09 | H3 FEM 破坏长度 <-> C1 Riska 速度项系数 | L_b_m=16.65, L_ref_m=1 | -75.49% | ±15% | `explained_domain` |\n| XC-10 | H4 FEM 面板压力(IACS 链) <-> C2 推力包络面板压力先验 | p_ref_MPa=1.2, a_ref_m2=1, patch_area_m2=0.7, exponent=0.5,  | -28.29% | ±15% | `explained_domain` |\n| XC-11 | H4 FEM 面板压力(B1 IACS 链) <-> 平台 ice_fullscale B1 实现 | F_global_N=2.77e+06, contact_width_m=1.5, q_line_kN_per_m=18 | +0.00% | ±2% | `consistent` |\n| XC-12 | H4 面板压力双链（IACS 局部设计压力 vs B1 全局力派生压力） | chain_a_max_MPa=2, chain_b_max_MPa=6.156, n_conditions=5 | +329.19% | ±15% | `explained_domain` |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "12 条断言的 dev/判据/结论原文；判据 ±15%（XC-11 为 ±2%）"
        },
        {
          "asset_id": "A06",
          "asset_class": "statement_set",
          "label": "四对指定比对逐条要点（4 条）",
          "in_report_section": "## ③ 计算结果（数字表）",
          "locator": {
            "method": "char_span",
            "start_char": 3359,
            "end_char": 4201,
            "start_line": 41,
            "end_line": 45,
            "quote": "\n- **DEM 堵塞系数 vs C2/C1**：DEM 派生上界 κ=1.118 与 C2 的「堵塞惩罚置 1（避免与 C1 双计）」相差 +11.76%（容差内）；与 C1 先验 1.0 同样 +11.76% 且落在可容许带 [1.0,2.5] 内 → 先验略保守但未越界。清空宽度对浓度**非单调**（散布 16.05%，超容差）→ 只能作上界，不回流标定。\n- **LBM frazil 黏度 vs W9-1215**：原浓度下 μ_r(φ=0.25) 差 −73.3%（堆积极限 0.60 vs 0.35 不同，不可互换）；对各自 φ_max 归一到 0.5 后差 −12.94%（容差内）；发散指数 α_eff=1.50 vs α=1.70 差 −11.76% → 两律在归一化坐标下同物理，可跨相搬运。\n- **FEM 破坏长度 vs C1 Lindqvist**：L_b=16.65 m vs 解析 Winkler 特征长度 l_c=14.61 m，+13.95%（容差内，破坏长度被板弯曲物理锁定）；P_edge=968 kN vs Lindqvist R_bending=635 kN，+52.5%（峰值 vs 航程平均，只可作**上界**）；把 L_b 当碎片尺度去映射 Riska c2 得 0.00368 < 可容许下界 0.005 → **拒收**，c2 保持先验 0.015。\n- **FEM 面板压力 vs B1 IACS 链**：H4 的 PC6 规范值 1.434 MPa vs C2 量级先验 2.0 MPa，−28.3%（冰级/面积约定不同，按 k_panel=1+λ(p/p0−1) 折算推力需求 −4.2%）；平台 `ice_fullscale` 复算与 H4 chain_b 逐项一致（偏差 0.00%，判据 2%，证明跨仓接线未走形）；双链面压差 329%（IACS 局部设计压力 vs 全局力派生等效面压，**口径不同不可混用**）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "4 条要点原文；含拒收/上界/口径界定表述"
        },
        {
          "asset_id": "A07",
          "asset_class": "figure_declaration",
          "label": "结果图声明（图 1/2/3）",
          "in_report_section": "## ④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 4212,
            "end_char": 4413,
            "start_line": 48,
            "end_line": 51,
            "quote": "\n- **图 1 12 条断言偏差总览**：±15% 判据带；绿色=容差内，橙色=已界定适用域（含拒收判定）。\n- **图 2 frazil 流变对撞**：(a) 原浓度坐标下两律分离（堆积极限不同）；(b) 归一化坐标下重合（Krieger-Dougherty 同标度）。\n- **图 3 面板压力双链**：(a) 双链面压随冰厚的变化与相对偏差；(b) 口径差异达 200–330%（非数值误差）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "platform_figures_field",
            "result": "resolved",
            "platform_figures_count": 3,
            "figure_names": [
              "fig1_crosscheck_deviation.png",
              "fig2_frazil_reduced_viscosity.png",
              "fig3_panel_pressure_dual_chain.png"
            ],
            "detail": "3 条图声明在源 markdown 内可定位；PNG 字节在平台 figures 字段（3 项）"
          },
          "note": "3 条图声明原文；PNG 字节在平台 figures 字段（3 项，名称 fig1/fig2/fig3_*.png），本仓不落地"
        },
        {
          "asset_id": "A08",
          "asset_class": "artifact_reference",
          "label": "门禁母版 artifacts/hifi_acceptance.json",
          "in_report_section": "## 产物",
          "locator": {
            "method": "char_span",
            "start_char": 5169,
            "end_char": 5389,
            "start_line": 69,
            "end_line": 69,
            "quote": "`artifacts/hifi_acceptance.json`（门禁母版）· `artifacts/hifi_upstream/`（三库工件归档）· `docs/campaign/hifi_xcheck_report.md`（论文级报告）· `artifacts/figures/hifi_acceptance/*.png` · `backend/tests/test_hifi_acceptance.py`（23 例，含缺件/篡改负控）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "artifacts/hifi_acceptance.json"
            ],
            "missing": [
              "artifacts/hifi_acceptance.json"
            ],
            "result": "unresolved",
            "detail": "H5 仓（ship-performance-platform）相对路径；本工作树（TensorKnowledge）内实测不存在"
          },
          "note": "H5 仓（ship-performance-platform）相对路径；本工作树内不存在，报告未给可解析 URI"
        },
        {
          "asset_id": "A09",
          "asset_class": "artifact_reference",
          "label": "三库工件归档 artifacts/hifi_upstream/",
          "in_report_section": "## 产物",
          "locator": {
            "method": "char_span",
            "start_char": 5169,
            "end_char": 5389,
            "start_line": 69,
            "end_line": 69,
            "quote": "`artifacts/hifi_acceptance.json`（门禁母版）· `artifacts/hifi_upstream/`（三库工件归档）· `docs/campaign/hifi_xcheck_report.md`（论文级报告）· `artifacts/figures/hifi_acceptance/*.png` · `backend/tests/test_hifi_acceptance.py`（23 例，含缺件/篡改负控）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "artifacts/hifi_upstream"
            ],
            "missing": [
              "artifacts/hifi_upstream"
            ],
            "result": "unresolved",
            "detail": "H5 仓（ship-performance-platform）相对路径；本工作树（TensorKnowledge）内实测不存在"
          },
          "note": "H5 仓相对路径目录；本工作树内不存在，逐字节归档内容不可在本仓解析"
        },
        {
          "asset_id": "A10",
          "asset_class": "document_reference",
          "label": "论文级报告 docs/campaign/hifi_xcheck_report.md",
          "in_report_section": "## 产物",
          "locator": {
            "method": "char_span",
            "start_char": 5169,
            "end_char": 5389,
            "start_line": 69,
            "end_line": 69,
            "quote": "`artifacts/hifi_acceptance.json`（门禁母版）· `artifacts/hifi_upstream/`（三库工件归档）· `docs/campaign/hifi_xcheck_report.md`（论文级报告）· `artifacts/figures/hifi_acceptance/*.png` · `backend/tests/test_hifi_acceptance.py`（23 例，含缺件/篡改负控）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "docs/campaign/hifi_xcheck_report.md"
            ],
            "missing": [
              "docs/campaign/hifi_xcheck_report.md"
            ],
            "result": "unresolved",
            "detail": "H5 仓（ship-performance-platform）相对路径；本工作树（TensorKnowledge）内实测不存在"
          },
          "note": "H5 仓相对路径；本工作树内不存在"
        },
        {
          "asset_id": "A11",
          "asset_class": "figure_set",
          "label": "图件集 artifacts/figures/hifi_acceptance/*.png",
          "in_report_section": "## 产物",
          "locator": {
            "method": "char_span",
            "start_char": 5169,
            "end_char": 5389,
            "start_line": 69,
            "end_line": 69,
            "quote": "`artifacts/hifi_acceptance.json`（门禁母版）· `artifacts/hifi_upstream/`（三库工件归档）· `docs/campaign/hifi_xcheck_report.md`（论文级报告）· `artifacts/figures/hifi_acceptance/*.png` · `backend/tests/test_hifi_acceptance.py`（23 例，含缺件/篡改负控）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "artifacts/figures/hifi_acceptance"
            ],
            "missing": [
              "artifacts/figures/hifi_acceptance"
            ],
            "result": "unresolved",
            "detail": "H5 仓（ship-performance-platform）相对路径；本工作树（TensorKnowledge）内实测不存在"
          },
          "note": "H5 仓相对路径通配；本工作树内不存在（平台 figures 字段另有 3 张同名图，见 A07）"
        },
        {
          "asset_id": "A12",
          "asset_class": "code_reference",
          "label": "验收测试 backend/tests/test_hifi_acceptance.py（23 例）",
          "in_report_section": "## 产物",
          "locator": {
            "method": "char_span",
            "start_char": 5169,
            "end_char": 5389,
            "start_line": 69,
            "end_line": 69,
            "quote": "`artifacts/hifi_acceptance.json`（门禁母版）· `artifacts/hifi_upstream/`（三库工件归档）· `docs/campaign/hifi_xcheck_report.md`（论文级报告）· `artifacts/figures/hifi_acceptance/*.png` · `backend/tests/test_hifi_acceptance.py`（23 例，含缺件/篡改负控）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "backend/tests/test_hifi_acceptance.py"
            ],
            "missing": [
              "backend/tests/test_hifi_acceptance.py"
            ],
            "result": "unresolved",
            "detail": "H5 仓（ship-performance-platform）相对路径；本工作树（TensorKnowledge）内实测不存在"
          },
          "note": "H5 仓相对路径；本工作树内不存在，23 例为上游自报"
        },
        {
          "asset_id": "A13",
          "asset_class": "code_reference",
          "label": "Lindqvist 实现 api/ice/formulas.py::calc_lindqvist",
          "in_report_section": "## ② 怎么做的（方法 / 关键设置 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1154,
            "end_char": 1394,
            "start_line": 18,
            "end_line": 18,
            "quote": "2. **经验链取值调用平台既有实现**（不重写公式）：Lindqvist → `api/ice/formulas.py::calc_lindqvist`；B1 全局力 → `modules/ice_fullscale/ice_physics.py::global_ice_force/local_line_load`；W9-1215 黏度律 → `physics/grease_ice/rheology.py::viscosity_ratio`（参数从其标定产物读取，不手抄）。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "api/ice/formulas.py"
            ],
            "missing": [
              "api/ice/formulas.py"
            ],
            "result": "unresolved",
            "detail": "H5 仓（ship-performance-platform）相对路径；本工作树（TensorKnowledge）内实测不存在"
          },
          "note": "H5 仓相对路径+函数符号；本工作树内不存在（上游表 H3 行的 `api.ice/formulas.py` 为同一文件的模块记法）"
        },
        {
          "asset_id": "A14",
          "asset_class": "code_reference",
          "label": "B1 全局力 modules/ice_fullscale/ice_physics.py::global_ice_force/local_line_load",
          "in_report_section": "## ② 怎么做的（方法 / 关键设置 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1154,
            "end_char": 1394,
            "start_line": 18,
            "end_line": 18,
            "quote": "2. **经验链取值调用平台既有实现**（不重写公式）：Lindqvist → `api/ice/formulas.py::calc_lindqvist`；B1 全局力 → `modules/ice_fullscale/ice_physics.py::global_ice_force/local_line_load`；W9-1215 黏度律 → `physics/grease_ice/rheology.py::viscosity_ratio`（参数从其标定产物读取，不手抄）。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "modules/ice_fullscale/ice_physics.py"
            ],
            "missing": [
              "modules/ice_fullscale/ice_physics.py"
            ],
            "result": "unresolved",
            "detail": "H5 仓（ship-performance-platform）相对路径；本工作树（TensorKnowledge）内实测不存在"
          },
          "note": "H5 仓相对路径+函数符号；本工作树内不存在"
        },
        {
          "asset_id": "A15",
          "asset_class": "code_reference",
          "label": "W9-1215 黏度律 physics/grease_ice/rheology.py::viscosity_ratio",
          "in_report_section": "## ② 怎么做的（方法 / 关键设置 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1154,
            "end_char": 1394,
            "start_line": 18,
            "end_line": 18,
            "quote": "2. **经验链取值调用平台既有实现**（不重写公式）：Lindqvist → `api/ice/formulas.py::calc_lindqvist`；B1 全局力 → `modules/ice_fullscale/ice_physics.py::global_ice_force/local_line_load`；W9-1215 黏度律 → `physics/grease_ice/rheology.py::viscosity_ratio`（参数从其标定产物读取，不手抄）。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "physics/grease_ice/rheology.py"
            ],
            "missing": [
              "physics/grease_ice/rheology.py"
            ],
            "result": "unresolved",
            "detail": "H5 仓（ship-performance-platform）相对路径；本工作树（TensorKnowledge）内实测不存在"
          },
          "note": "H5 仓相对路径+函数符号；本工作树内不存在"
        },
        {
          "asset_id": "A16",
          "asset_class": "external_model",
          "label": "W9-1215 损失模型 physics.grease_ice.rheology（φ_max=0.35，α=1.70）",
          "in_report_section": "## ① 案例介绍（物理背景 / 几何 / 参数）",
          "locator": {
            "method": "char_span",
            "start_char": 521,
            "end_char": 675,
            "start_line": 11,
            "end_line": 11,
            "quote": "| H2 | TensorLBM `tensorlbm.frazil_rheology` | 流变面 μ_r(φ)、幂律 n、稠度 K（φ=0–0.55，φ_max=0.60） | W9-1215 损失模型 `physics.grease_ice.rheology`（φ_max=0.35，α=1.70） |",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "address_extraction+worktree_path_exists",
            "addresses_found": [],
            "paths": [
              "physics/grease_ice/rheology.py"
            ],
            "missing": [
              "physics/grease_ice/rheology.py"
            ],
            "result": "unresolved",
            "detail": "原文行内无 URL/DOI，且本工作树内无该模块"
          },
          "note": "标定产物 W9-1215 的模块记法；本工作树内无该模块，报告未给可解析 URI"
        },
        {
          "asset_id": "A17",
          "asset_class": "code_reference",
          "label": "报告生成器 make_acceptance_docs.py",
          "in_report_section": "## ② 怎么做的（方法 / 关键设置 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1686,
            "end_char": 1787,
            "start_line": 21,
            "end_line": 21,
            "quote": "5. 判据数字全部落在 `artifacts/hifi_acceptance.json#gate`；报告与图由 `make_acceptance_docs.py` 从该 JSON 程序化生成（零手抄）。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "make_acceptance_docs.py"
            ],
            "missing": [
              "make_acceptance_docs.py"
            ],
            "result": "unresolved",
            "detail": "H5 仓（ship-performance-platform）相对路径；本工作树（TensorKnowledge）内实测不存在"
          },
          "note": "H5 仓脚本；本工作树内不存在"
        }
      ],
      "claims": [],
      "claims_note": "按工作包契约 objective.classify_report_type=false 且 notes 允许 claims 为空数组：本工序只登记资产定位，不做 claim 抽取；claim 抽取由下游工作包负责。",
      "integrity": {
        "quote_uniqueness": "all quotes confirmed unique substrings of source markdown (scripts/kf_verify_5690.py, checks.source_locator_resolvable)",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true
      }
    }
  }
}
```
