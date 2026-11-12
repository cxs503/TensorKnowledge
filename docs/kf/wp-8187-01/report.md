# KF-RESULT wp-8187-01

**package_id**: wp-8187-01
**task_type**: 01-asset-registration
**report_id**: 8187
**tags**: kf-wp:wp-8187-01, lane:C, TensorDEM, research, A
**status**: draft

---

## ① 本工序做了什么

对 report_id=8187（P35-N2 湿冰颗粒团聚的毛细桥 cohesion 模型，TensorDEM）执行 **01-asset-registration** 工序：
- 确认源报告 markdown 的字节哈希与契约一致（`sha256:123060fc65159890ea043d0ce52dc0d565538b3f73043be6da2b1e82ba220789`，9206 字符 / 14982 UTF-8 字节）
- 定位并登记报告中引用的 17 个工件/附件（能力标识、源码模块、脚本、数据 JSON、测试、4 张图）
- 每个资产提供精确的字符跨度定位（char_span，0-indexed 字符 + 1-indexed 行号），引文逐字来自原文
- claims 为空数组（契约 `classify_report_type=false`，不做知识抽取）
- 平台图端点探测：4 个 figure 均 404（仅 name/caption 元数据，无字节载荷，不声称哈希）

## ② 怎么做的（步骤/工具/关键设置）

1. **获取源报告**：`GET /api/v1/tensor/reports/8187`（Bearer 登录 `$TENSOR_AGENT_USER`），取 `markdown` 字段
2. **哈希校验**：`hashlib.sha256(md.encode('utf-8')).hexdigest()` 与契约 `source_hash` 逐位比对 → **MATCH**；chars=9206 与契约一致；title/scenario_key 与契约一致
3. **工件定位**：对每个锚点 token 做 `str.find()` 子串搜索，程序化记录起始/结束字符位置、行号、出现次数（唯一性判定）；引文=token 本身，写盘前逐条复核 `md[start:end]==quote`
4. **资产分类**：capability×1、source_code×7、script×2、data×2、test×1、figure×4
5. **JSON 构建**：按 `schemas/kf_result.v1.schema.json` 信封结构组装，`outputs.asset_manifest.json` 内嵌资产清单（schema 形状对齐 `schemas/asset_manifest.v1.schema.json`）
6. **校验**：`json.loads()` 合法性；`jsonschema.validate(envelope, kf_result.v1)` 0 错误；17/17 定位可回溯；A01–A17 无重复 ID

工具链：Python 3 + urllib + hashlib + json + jsonschema（纯标准库 + jsonschema 4.26）

## ③ 产出物清单

| 输出文件 | 要点 |
|---|---|
| `docs/kf/wp-8187-01/kf_result.json` | KF 结果信封（package_id/task_type/report_id/provenance/outputs） |
| `docs/kf/wp-8187-01/asset_manifest.json` | 资产清单：17 个资产全部 resolved_in_source，claims=[] |
| `docs/kf/wp-8187-01/report.md` | 本报告（唯一 json 块=结果信封） |
| `docs/kf/wp-8187-01/verification.json` | 自检记录（acceptance 逐项，self-check only） |
| `runs/wp-8187-01/report_8187.md` | 源 markdown 本地副本（字节一致，sha256 同契约） |
| `runs/wp-8187-01/report_8187_api.json` | API 原始载荷（含 figures/tags/record 字段） |
| `scripts/kf_register_8187.py` | 一键复跑脚本（取数→校验→定位→写盘→自检） |
| `scripts/kf_report_8187.py` | 本报告构建脚本（保证 json 块与 kf_result.json 字节一致） |

资产登记摘要（capability×1、source_code×7、script×2、data×2、test×1、figure×4）：
- A01: `tensordem.wet_ice_cohesion` 能力标识 → 报告头
- A02–A04: `capillary.py` / `tensordem.liquid_bridge.solve_axisymmetric_bridge` / `liquid_bridge.py` → §2.1–2.2
- A05–A06: 参考表生成脚本 + `capillary_reference.json` → §2.2
- A07–A09: `aggregation.py` / `cohesion_cell.py` / `ice_resistance.py` → §2.3–2.4
- A10–A12: study 脚本 + `campaign.json` + `tests/test_wet_ice_cohesion.py` → §2.5/§7
- A13–A16: fig1–fig4 PNG（`artifacts/wet_ice_cohesion/`）→ §4
- A17: `src/tensordem/wet_ice_cohesion/figures.py`（make_all）→ §7

## ④ 证据定位表

| 资产 | 类别 | 定位方法 | 字符跨度 | 行号 | 原文引文片段 | 唯一 | 所在节 |
|---|---|---|---|---|---|---|---|
| A01 | capability | char_span | 117–143 | 4 | `tensordem.wet_ice_cohesion` | 是 | 报告头（标题下元信息行） |
| A02 | source_code | char_span | 887–899 | 27 | `capillary.py` | 是 | 2. 怎么做的（方法 / 流程 / 工具链） |
| A03 | source_code | char_span | 1611–1660 | 46 | `tensordem.liquid_bridge.solve_axisymmetric_bridge` | 是 | 2. 怎么做的（方法 / 流程 / 工具链） |
| A04 | source_code | char_span | 1673–1689 | 46 | `liquid_bridge.py` | 是 | 2. 怎么做的（方法 / 流程 / 工具链） |
| A05 | script | char_span | 1893–1935 | 52 | `scripts/gen_wet_ice_capillary_reference.py` | 否 | 2. 怎么做的（方法 / 流程 / 工具链） |
| A06 | data | char_span | 1945–1996 | 53 | `artifacts/wet_ice_cohesion/capillary_reference.json` | 否 | 2. 怎么做的（方法 / 流程 / 工具链） |
| A07 | source_code | char_span | 2059–2073 | 56 | `aggregation.py` | 是 | 2. 怎么做的（方法 / 流程 / 工具链） |
| A08 | source_code | char_span | 2379–2395 | 65 | `cohesion_cell.py` | 是 | 2. 怎么做的（方法 / 流程 / 工具链） |
| A09 | source_code | char_span | 2400–2417 | 65 | `ice_resistance.py` | 是 | 2. 怎么做的（方法 / 流程 / 工具链） |
| A10 | script | char_span | 2803–2836 | 78 | `scripts/wet_ice_cohesion_study.py` | 否 | 2. 怎么做的（方法 / 流程 / 工具链） |
| A11 | data | char_span | 8639–8679 | 218 | `artifacts/wet_ice_cohesion/campaign.json` | 是 | 7. 审计链 |
| A12 | test | char_span | 2878–2908 | 79 | `tests/test_wet_ice_cohesion.py` | 否 | 2. 怎么做的（方法 / 流程 / 工具链） |
| A13 | figure | char_span | 5602–5654 | 151 | `artifacts/wet_ice_cohesion/fig1_capillary_bridge.png` | 是 | 4. 结果图 |
| A14 | figure | char_span | 5762–5824 | 154 | `artifacts/wet_ice_cohesion/fig2_agglomeration_smoluchow...` | 是 | 4. 结果图 |
| A15 | figure | char_span | 5896–5945 | 156 | `artifacts/wet_ice_cohesion/fig3_cohesion_cell.png` | 是 | 4. 结果图 |
| A16 | figure | char_span | 6005–6060 | 158 | `artifacts/wet_ice_cohesion/fig4_enhancement_vs_size.png` | 是 | 4. 结果图 |
| A17 | source_code | char_span | 8690–8731 | 219 | `src/tensordem/wet_ice_cohesion/figures.py` | 是 | 7. 审计链 |

## ⑤ 注意点与局限

- **本工序不做知识抽取**：`classify_report_type=false`，claims 为空数组，不生成任何 claim
- **不验证工件内容/存在性**：被引用文件位于 TensorDEM 仓（报告头声明分支 `agent/m6796`），不在本 TensorKnowledge 工作树内；`resolution=resolved_in_source` 仅表示定位在源 markdown 中可解析，非内容验证
- **不标记 verified**：verification 由平台门独立计算；本清单不覆盖任何上游结论
- **源哈希已校验**：`sha256:123060fc65159890ea043d0ce52dc0d565538b3f73043be6da2b1e82ba220789` 与契约完全一致（本地重算）
- **零手抄**：所有数字/引文直接来自 API 返回的 markdown 字段，程序化注入
- **图端点 404**：`GET /tensor/reports/8187/figures/<name>` 对 4 张图均返回 404（29 字节错误体），与 wp-623-01 观察一致；图字节不在本工序可达范围
- **无结果图**：本工序为纯登记（无计算/无场量），不生成 png，特此声明

## ⑥ 自检（acceptance 逐条对照）

| 验收项 | 状态 | 说明 |
|---|---|---|
| valid_json | ✅ | `json.loads()` 通过（envelope + manifest） |
| schema_pass | ✅ | `jsonschema.validate` 对 kf_result.v1：0 错误 |
| source_locator_resolvable | ✅ | 17/17 资产 char_span 定位成功，`md[start:end]==quote` 逐条复核 |
| source_hash_matches | ✅ | 本地重算 `sha256:123060fc65159890ea043d0ce52dc0d565538b3f73043be6da2b1e82ba220789` = 契约值 |
| no_duplicate_ids | ✅ | A01–A17 共 17 个 ID，无重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=[]（空数组，契约允许；未造任何 claim） |

---

## 结果 JSON

```json
{
  "package_id": "wp-8187-01",
  "task_type": "01-asset-registration",
  "report_id": "8187",
  "provenance": {
    "source_hash": "sha256:123060fc65159890ea043d0ce52dc0d565538b3f73043be6da2b1e82ba220789",
    "source_field": "markdown",
    "producer": "agent/m15608",
    "emitted_at": "2026-11-12T02:12:11.439762+00:00",
    "notes": "Asset registration for report 8187 (P35-N2 wet-ice capillary-bridge cohesion, TensorDEM). Source hash recomputed from live API markdown and matches contract. 17 referenced artifacts located with verbatim char_span locators; claims=[] per contract (classify_report_type=false, no extraction). Nothing marked verified."
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-8187-01",
      "task_type": "01-asset-registration",
      "report_id": "8187",
      "source": {
        "uri": "tensor://reports/8187",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "123060fc65159890ea043d0ce52dc0d565538b3f73043be6da2b1e82ba220789",
        "chars": 9206,
        "bytes_utf8": 14982,
        "title": "P35-N2 湿冰颗粒团聚的毛细桥 cohesion 模型：解析锚 + 团聚体尺寸演化 + 冰阻力增强因子（TensorDEM）",
        "scenario_key": "wet_ice_cohesion",
        "platform_figures": [
          {
            "name": "fig1_capillary_bridge.png",
            "caption": "图1 (a) 液桥力 F/(2πγR) 随 s/R：模型（实线，calibrated）、留出集精确 Young-Laplace 解（空心圆）、任务书种子闭式（红点划线，恒 ≤ 0，即无吸引）；(b) 峰值力 parity，留出集最大误差 0.32%。"
          },
          {
            "name": "fig2_agglomeration_smoluchowski.png",
            "caption": "图2 (a) 剪切流团聚体平均尺寸 <D>/D0：DEM 粒子模型 vs Smoluchowski 正交剪切核平均场，含 dt/2 与 N×2 两条收敛算例，后半程最大偏差 5.88%；(b) 三个时刻的团簇尺寸分布 n(D,t)。"
          },
          {
            "name": "fig3_cohesion_cell.png",
            "caption": "图3 (a) 2D 拉伸池墙牵引力时程：湿（有毛细桥，c = 0.6189）vs 干（γ = 0，c = −0.0）；(b) 实测内聚力 vs 平面投影微观参考（0.5460）与 virial/Rumpf 上界（0.8576）。"
          },
          {
            "name": "fig4_enhancement_vs_size.png",
            "caption": "图4 冰阻力增强因子 F_wet/F_dry 随颗粒半径（σ_n = 1 kPa）：毛细内聚只在 Bond 数 ≲ 1（R ≲ 2.9 mm）窗口显著；cm 级碎冰体只有百分之几。标出 DEM 2D 池值与 Timco-Weeks 关系分支。"
          }
        ],
        "platform_tags": [
          "TensorDEM",
          "P35-N2",
          "wet-ice",
          "capillary-bridge",
          "cohesion",
          "Smoluchowski",
          "agglomeration",
          "ice-resistance",
          "honest-FAIL"
        ],
        "contract_source_hash": "sha256:123060fc65159890ea043d0ce52dc0d565538b3f73043be6da2b1e82ba220789",
        "hash_match": true,
        "contract_chars": 9206,
        "chars_match_contract": true,
        "title_matches_contract": true,
        "scenario_matches_contract": true,
        "fetched_via": "GET /api/v1/tensor/reports/8187",
        "record_fields": {
          "id": 8187,
          "mission_id": 6796,
          "status": "published",
          "created_at": "2026-11-08T09:16:27.307740+00:00"
        },
        "platform_figure_probes": {
          "fig1_capillary_bridge.png": {
            "http_status": 404,
            "bytes": 29
          },
          "fig2_agglomeration_smoluchowski.png": {
            "http_status": 404,
            "bytes": 29
          },
          "fig3_cohesion_cell.png": {
            "http_status": 404,
            "bytes": 29
          },
          "fig4_enhancement_vs_size.png": {
            "http_status": 404,
            "bytes": 29
          }
        },
        "line_counting": "logical lines = markdown.rstrip(chr(10)).split(chr(10)); 1-based"
      },
      "counts": {
        "assets": 17,
        "by_class": {
          "capability": 1,
          "source_code": 7,
          "script": 2,
          "data": 2,
          "test": 1,
          "figure": 4
        },
        "by_resolution": {
          "resolved_in_source": 17
        },
        "resolved_in_source": 17,
        "referenced_unresolved": 0,
        "declared_absent": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "capability",
          "label": "新增能力标识（领域目录 4 模块 + 1 study + 1 figures）",
          "in_report_section": "报告头（标题下元信息行）",
          "locator": {
            "method": "char_span",
            "start_char": 117,
            "end_char": 143,
            "start_line": 4,
            "end_line": 4,
            "quote": "tensordem.wet_ice_cohesion",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search:tensordem.wet_ice_cohesion",
            "result": "resolved"
          },
          "note": "Referenced in 报告头（标题下元信息行）; 1 occurrence(s) in report; file lives in TensorDEM (branch agent/m6796 per report header), not in this worktree; existence not asserted"
        },
        {
          "asset_id": "A02",
          "asset_class": "source_code",
          "label": "毛细桥力律模块（任务书闭式/小液桥解析锚/DEM 级闭式）",
          "in_report_section": "2. 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 887,
            "end_char": 899,
            "start_line": 27,
            "end_line": 27,
            "quote": "capillary.py",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search:capillary.py",
            "result": "resolved"
          },
          "note": "Referenced in 2. 怎么做的（方法 / 流程 / 工具链）; 1 occurrence(s) in report; file lives in TensorDEM (branch agent/m6796 per report header), not in this worktree; existence not asserted"
        },
        {
          "asset_id": "A03",
          "asset_class": "source_code",
          "label": "精确轴对称 Young–Laplace 求解器（判定基准，零重力精确自由面）",
          "in_report_section": "2. 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1611,
            "end_char": 1660,
            "start_line": 46,
            "end_line": 46,
            "quote": "tensordem.liquid_bridge.solve_axisymmetric_bridge",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search:tensordem.liquid_bridge.solve_axisymmetric_bridge",
            "result": "resolved"
          },
          "note": "Referenced in 2. 怎么做的（方法 / 流程 / 工具链）; 1 occurrence(s) in report; file lives in TensorDEM (branch agent/m6796 per report header), not in this worktree; existence not asserted"
        },
        {
          "asset_id": "A04",
          "asset_class": "source_code",
          "label": "YL 求解器文件（自带一阶积分自洽检查）",
          "in_report_section": "2. 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1673,
            "end_char": 1689,
            "start_line": 46,
            "end_line": 46,
            "quote": "liquid_bridge.py",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search:liquid_bridge.py",
            "result": "resolved"
          },
          "note": "Referenced in 2. 怎么做的（方法 / 流程 / 工具链）; 1 occurrence(s) in report; file lives in TensorDEM (branch agent/m6796 per report header), not in this worktree; existence not asserted"
        },
        {
          "asset_id": "A05",
          "asset_class": "script",
          "label": "毛细桥参考表生成脚本（R/γ/n_steps 记入 meta，可一键重算）",
          "in_report_section": "2. 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1893,
            "end_char": 1935,
            "start_line": 52,
            "end_line": 52,
            "quote": "scripts/gen_wet_ice_capillary_reference.py",
            "unique": false
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search:scripts/gen_wet_ice_capillary_reference.py",
            "result": "resolved"
          },
          "note": "Referenced in 2. 怎么做的（方法 / 流程 / 工具链）; 4 occurrence(s) in report; file lives in TensorDEM (branch agent/m6796 per report header), not in this worktree; existence not asserted"
        },
        {
          "asset_id": "A06",
          "asset_class": "data",
          "label": "毛细桥参考表 JSON（train/validate 行 + converged 标记）",
          "in_report_section": "2. 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1945,
            "end_char": 1996,
            "start_line": 53,
            "end_line": 53,
            "quote": "artifacts/wet_ice_cohesion/capillary_reference.json",
            "unique": false
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search:artifacts/wet_ice_cohesion/capillary_reference.json",
            "result": "resolved"
          },
          "note": "Referenced in 2. 怎么做的（方法 / 流程 / 工具链）; 2 occurrence(s) in report; file lives in TensorDEM (branch agent/m6796 per report header), not in this worktree; existence not asserted"
        },
        {
          "asset_id": "A07",
          "asset_class": "source_code",
          "label": "团聚粒子级模型（仿射剪切 + Lees–Edwards 镜像 + 等价球合并）",
          "in_report_section": "2. 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 2059,
            "end_char": 2073,
            "start_line": 56,
            "end_line": 56,
            "quote": "aggregation.py",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search:aggregation.py",
            "result": "resolved"
          },
          "note": "Referenced in 2. 怎么做的（方法 / 流程 / 工具链）; 1 occurrence(s) in report; file lives in TensorDEM (branch agent/m6796 per report header), not in this worktree; existence not asserted"
        },
        {
          "asset_id": "A08",
          "asset_class": "source_code",
          "label": "2D 拉伸池内聚力测量（行沉积+位置式压缩+顶墙上拉）",
          "in_report_section": "2. 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 2379,
            "end_char": 2395,
            "start_line": 65,
            "end_line": 65,
            "quote": "cohesion_cell.py",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search:cohesion_cell.py",
            "result": "resolved"
          },
          "note": "Referenced in 2. 怎么做的（方法 / 流程 / 工具链）; 1 occurrence(s) in report; file lives in TensorDEM (branch agent/m6796 per report header), not in this worktree; existence not asserted"
        },
        {
          "asset_id": "A09",
          "asset_class": "source_code",
          "label": "冰阻力增强因子 F_enh 计算",
          "in_report_section": "2. 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 2400,
            "end_char": 2417,
            "start_line": 65,
            "end_line": 65,
            "quote": "ice_resistance.py",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search:ice_resistance.py",
            "result": "resolved"
          },
          "note": "Referenced in 2. 怎么做的（方法 / 流程 / 工具链）; 1 occurrence(s) in report; file lives in TensorDEM (branch agent/m6796 per report header), not in this worktree; existence not asserted"
        },
        {
          "asset_id": "A10",
          "asset_class": "script",
          "label": "全判据 study 脚本（判据 → campaign.json + 4 张图）",
          "in_report_section": "2. 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 2803,
            "end_char": 2836,
            "start_line": 78,
            "end_line": 78,
            "quote": "scripts/wet_ice_cohesion_study.py",
            "unique": false
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search:scripts/wet_ice_cohesion_study.py",
            "result": "resolved"
          },
          "note": "Referenced in 2. 怎么做的（方法 / 流程 / 工具链）; 3 occurrence(s) in report; file lives in TensorDEM (branch agent/m6796 per report header), not in this worktree; existence not asserted"
        },
        {
          "asset_id": "A11",
          "asset_class": "data",
          "label": "全判据结果 JSON（含参考自洽最大偏差 1.22 %/1.39 % 汇总）",
          "in_report_section": "7. 审计链",
          "locator": {
            "method": "char_span",
            "start_char": 8639,
            "end_char": 8679,
            "start_line": 218,
            "end_line": 218,
            "quote": "artifacts/wet_ice_cohesion/campaign.json",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search:artifacts/wet_ice_cohesion/campaign.json",
            "result": "resolved"
          },
          "note": "Referenced in 7. 审计链; 1 occurrence(s) in report; file lives in TensorDEM (branch agent/m6796 per report header), not in this worktree; existence not asserted"
        },
        {
          "asset_id": "A12",
          "asset_class": "test",
          "label": "pytest 断言面（18 项断言，130 s）",
          "in_report_section": "2. 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 2878,
            "end_char": 2908,
            "start_line": 79,
            "end_line": 79,
            "quote": "tests/test_wet_ice_cohesion.py",
            "unique": false
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search:tests/test_wet_ice_cohesion.py",
            "result": "resolved"
          },
          "note": "Referenced in 2. 怎么做的（方法 / 流程 / 工具链）; 3 occurrence(s) in report; file lives in TensorDEM (branch agent/m6796 per report header), not in this worktree; existence not asserted"
        },
        {
          "asset_id": "A13",
          "asset_class": "figure",
          "label": "图1 液桥力律 F/(2πγR) vs s/R + 峰值力 parity（留出集最大误差 0.32 %）",
          "in_report_section": "4. 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 5602,
            "end_char": 5654,
            "start_line": 151,
            "end_line": 151,
            "quote": "artifacts/wet_ice_cohesion/fig1_capillary_bridge.png",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search:artifacts/wet_ice_cohesion/fig1_capillary_bridge.png",
            "result": "resolved"
          },
          "note": "Referenced in 4. 结果图; 1 occurrence(s) in report; file lives in TensorDEM (branch agent/m6796 per report header), not in this worktree; existence not asserted"
        },
        {
          "asset_id": "A14",
          "asset_class": "figure",
          "label": "图2 团聚体平均尺寸 ⟨D⟩/D0：DEM vs Smoluchowski + 团簇尺寸分布",
          "in_report_section": "4. 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 5762,
            "end_char": 5824,
            "start_line": 154,
            "end_line": 154,
            "quote": "artifacts/wet_ice_cohesion/fig2_agglomeration_smoluchowski.png",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search:artifacts/wet_ice_cohesion/fig2_agglomeration_smoluchowski.png",
            "result": "resolved"
          },
          "note": "Referenced in 4. 结果图; 1 occurrence(s) in report; file lives in TensorDEM (branch agent/m6796 per report header), not in this worktree; existence not asserted"
        },
        {
          "asset_id": "A15",
          "asset_class": "figure",
          "label": "图3 拉伸池墙牵引力时程（湿 vs 干）+ 实测 c vs 参考/上界",
          "in_report_section": "4. 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 5896,
            "end_char": 5945,
            "start_line": 156,
            "end_line": 156,
            "quote": "artifacts/wet_ice_cohesion/fig3_cohesion_cell.png",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search:artifacts/wet_ice_cohesion/fig3_cohesion_cell.png",
            "result": "resolved"
          },
          "note": "Referenced in 4. 结果图; 1 occurrence(s) in report; file lives in TensorDEM (branch agent/m6796 per report header), not in this worktree; existence not asserted"
        },
        {
          "asset_id": "A16",
          "asset_class": "figure",
          "label": "图4 增强因子 F_wet/F_dry 随颗粒半径（Bond 数 ≲1 窗口）",
          "in_report_section": "4. 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 6005,
            "end_char": 6060,
            "start_line": 158,
            "end_line": 158,
            "quote": "artifacts/wet_ice_cohesion/fig4_enhancement_vs_size.png",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search:artifacts/wet_ice_cohesion/fig4_enhancement_vs_size.png",
            "result": "resolved"
          },
          "note": "Referenced in 4. 结果图; 1 occurrence(s) in report; file lives in TensorDEM (branch agent/m6796 per report header), not in this worktree; existence not asserted"
        },
        {
          "asset_id": "A17",
          "asset_class": "source_code",
          "label": "图生成入口 make_all（只读 campaign.json）",
          "in_report_section": "7. 审计链",
          "locator": {
            "method": "char_span",
            "start_char": 8690,
            "end_char": 8731,
            "start_line": 219,
            "end_line": 219,
            "quote": "src/tensordem/wet_ice_cohesion/figures.py",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search:src/tensordem/wet_ice_cohesion/figures.py",
            "result": "resolved"
          },
          "note": "Referenced in 7. 审计链; 1 occurrence(s) in report; file lives in TensorDEM (branch agent/m6796 per report header), not in this worktree; existence not asserted"
        }
      ],
      "claims": [],
      "integrity": {
        "quote_uniqueness": "all_locators_verified",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true
      }
    }
  }
}
```

---

**repro_cmd**: `cd <TensorKnowledge worktree> && python3 scripts/kf_register_8187.py`（需 `$TENSOR_API_BASE/$TENSOR_AGENT_USER/$TENSOR_AGENT_PASS`；脚本重取报告、重算哈希、重建 manifest/envelope 并自检）
