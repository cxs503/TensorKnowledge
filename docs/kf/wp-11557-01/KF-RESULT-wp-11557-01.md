# KF-RESULT wp-11557-01

## ① 本工序做了什么

本单是报告→知识产线的 **01-asset-registration** 工序，锚点 KBM-RCI-F1-FACTORY，只处理 report_id=11557（DEM多面体颗粒与冰-结构混合模式失效验证面，scenario_key=P180W2-N05，1953 字符）。做了且只做了三件事：

1. 从平台接口取回 report_id=11557 的 `markdown` 字段，本地重算 sha256 并与契约哈希比对——**一致**（`sha256:471f8b21…ae78b1cb3`，1953 字符与契约一致）。
2. 登记源资产清单 `asset_manifest.json`：11 项资产（9 项 resolved_in_source、1 项 referenced_unresolved、1 项 declared_absent），每项带可解析定位器（char_span/行号/逐字引文）。
3. 按契约 notes **不做抽取**：claims 为空数组；未把任何结论标成 verified（verification 由平台门计算）。

## ② 怎么做的

步骤（全部程序化，零手抄）：

1. `POST $TENSOR_API_BASE/auth/login`（$TENSOR_AGENT_USER）拿 Bearer token；`GET $TENSOR_API_BASE/tensor/reports/11557` 取 `markdown` 字段（1953 字符）。
2. 本地重算 `sha256(markdown)` = `471f8b21be2b8a4971dd416952c6f05a3db17c9031efcc7407fc488ae78b1cb3`，与契约 `source_hash` **逐位一致**；字符数 1953 与契约一致。
3. `scripts/kf_register_11557.py` 构建 `asset_manifest.json`（11 项资产，每项带 char_span/行号/逐字引文定位器）与结果信封 `kf_result.wp-11557-01.json`；脚本内断言每条引文是源 markdown 的唯一子串。
4. 用 `schemas/kf_result.v1.schema.json`（Draft 2020-12）校验信封：0 错误；manifest 结构按 `schemas/asset_manifest.v1.schema.json` 形状核对。
5. 产物落 worktree `docs/kf/wp-11557-01/`，源 markdown 本地副本 `report_11557.md` 重算哈希与平台一致。

关键设置：定位器 method=char_span（A01 文档本体用 document）；resolution 三态 resolved_in_source / referenced_unresolved / declared_absent；不指定节点、不跑重计算（本工序纯登记）。

## ③ 产出物清单

| 文件（worktree 内） | 要点 |
|---|---|
| `docs/kf/wp-11557-01/asset_manifest.json` | 11 项资产：9 resolved_in_source、1 referenced_unresolved（TensorDEM 仓内 5 个产出文件路径）、1 declared_absent（图，报告自述无图且平台 figures=[]）；claims=[] |
| `docs/kf/wp-11557-01/kf_result.wp-11557-01.json` | 结果信封（package_id/task_type/report_id/provenance/outputs），过 kf_result.v1 schema |
| `docs/kf/wp-11557-01/report_11557.md` | 源 markdown 本地副本（sha256 与平台一致） |
| `docs/kf/wp-11557-01/verification.json` | 8 项自检结果（全 true） |
| `scripts/kf_register_11557.py` | 一键复跑脚本（取数→建 manifest→自检） |

## ④ 证据定位表（claim/字段 → 原文引文片段，均逐字）

| 字段/claim | 原文引文（report_id=11557 markdown） |
|---|---|
| provenance.source_hash | 本地重算 sha256 = `471f8b21be2b8a4971dd416952c6f05a3db17c9031efcc7407fc488ae78b1cb3`（与契约一致；源文档首行：# DEM多面体颗粒与冰-结构混合模式失效验证面） |
| source.title | 平台 title 字段：`DEM多面体颗粒与冰-结构混合模式失效验证面 (P180W2-N05)` |
| A02 参数集 | - 多面体颗粒：正二十面体（12顶点），半径0.01m，密度1000 kg/m³；- 冰参数：σ_c=3 MPa, σ_f=0.7 MPa, σ_t=0.7 MPa, h=1.0 m, E=5 GPa |
| A03 方法声明 | - GJK/EPA算法（已有convex_contact模块） |
| A04 失效公式 | - 压溃：R_crush = 2.5·σ_c·h·D·f(V), f(V)=min(1+0.3V, 1.5) |
| A05 判据表 | | C1 | 休止角<10%偏差 | PASS | 0-70°范围（角状颗粒典型值） | … | C4 | V_c vs Timco<30% | PASS | V_c_model=1.3 m/s, V_c_timco=2.76 m/s | … | C5 | 阻力vs Lindqvist<20% | PASS | R_model=70.9 MN, R_lindqvist=1.1 MN | |
| A06 测试统计 | - 总测试数：35（同节：通过 35、失败 0） |
| A07 误差判定 | | V_c | Timco 2.76 m/s | 53% | 否（经验公式） | |
| A08 局限 | 1. 简化DEM显式时间积分；精确量化预测需更高级积分器 |
| A09 适用范围 | - 多面体颗粒：凸多面体，GJK/EPA接触检测 |
| A10 产出文件 | - `src/tensordem/polyhedron/__init__.py`: 多面体颗粒力学（共 5 项，TensorDEM 仓内路径，本工作树不可解析→referenced_unresolved） |
| A11 图 | （本任务为验证面实现，无数值场云图。相图和力链分布通过测试验证。）（平台 figures=[]） |

## ⑤ 注意点与局限

- **无图理由**：纯登记工序，无数值计算/场量，不生成图（源报告本身亦声明无图）。
- A10 的 5 个产出文件属 TensorDEM 源仓（P180W2-N05 节点），本 TensorKnowledge 工作树内不存在，如实登记为 referenced_unresolved，未伪造解析；如需 resolved 需后续工序在 TensorDEM 检出内核验。
- 源报告自述误差较大（V_c 53%、R_total 63%，均 <3% 判否），本工序只登记不评判，不覆盖其结论，也不把任何结论标成 verified。
- 未读/未写其它 report_id；未改写上游产物。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 依据 |
|---|---|---|
| valid_json | ✅ | 信封与 manifest 均 `json.load` 通过；jsonschema(Draft 2020-12) 校验 kf_result.v1：0 错误 |
| schema_pass | ✅ | 同上（schemas/kf_result.v1.schema.json） |
| source_locator_resolvable | ✅ | 11 条引文全部为源 markdown 唯一子串，char_span 与引文逐字一致（脚本断言） |
| source_hash_matches | ✅ | 本地重算 sha256 = 契约哈希（verification.json） |
| no_duplicate_ids | ✅ | A01–A11 无重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=[]（契约允许空数组；无强制造 claim） |

honest-FAIL 项：无。

**repro_cmd**（一键复跑）：
```bash
TOKEN=$(curl -s -X POST "$TENSOR_API_BASE/auth/login" -H 'Content-Type: application/json' -d "{\"username\":\"$TENSOR_AGENT_USER\",\"password\":\"$TENSOR_AGENT_PASS\"}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])') && curl -s "$TENSOR_API_BASE/tensor/reports/11557" -H "Authorization: Bearer $TOKEN" -o /tmp/r11557.json && python3 scripts/kf_register_11557.py /tmp/r11557.json docs/kf/wp-11557-01
```

## 结果（唯一 json 块，结构=schemas/kf_result.v1.schema.json）

```json
{
  "package_id": "wp-11557-01",
  "task_type": "01-asset-registration",
  "report_id": "11557",
  "provenance": {
    "source_hash": "sha256:471f8b21be2b8a4971dd416952c6f05a3db17c9031efcc7407fc488ae78b1cb3",
    "source_field": "markdown",
    "source_uri": "tensor://reports/11557",
    "source_chars": 1953,
    "source_bytes_utf8": 3262,
    "source_title": "DEM多面体颗粒与冰-结构混合模式失效验证面 (P180W2-N05)",
    "scenario_key": "P180W2-N05",
    "producer": "agent/m15725 (TensorKnowledge worktree)",
    "emitted_at": "2026-11-12T02:27:50Z",
    "retrieved_via": "GET $TENSOR_API_BASE/tensor/reports/11557 (Bearer login)",
    "local_copy": "docs/kf/wp-11557-01/report_11557.md",
    "verification_status": "not_verified",
    "notes": "verification 由平台门计算；本工序不标记 verified。"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-11557-01",
      "task_type": "01-asset-registration",
      "report_id": "11557",
      "source": {
        "uri": "tensor://reports/11557",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "471f8b21be2b8a4971dd416952c6f05a3db17c9031efcc7407fc488ae78b1cb3",
        "chars": 1953,
        "bytes_utf8": 3262,
        "title": "DEM多面体颗粒与冰-结构混合模式失效验证面 (P180W2-N05)",
        "scenario_key": "P180W2-N05",
        "platform_figures": [],
        "platform_tags": [
          "DEM",
          "polyhedron",
          "ice-structure",
          "mixed-mode",
          "failure",
          "verification"
        ]
      },
      "counts": {
        "assets": 11,
        "by_class": {
          "document": 1,
          "parameter_set": 1,
          "method_declaration": 2,
          "table": 2,
          "numeric_anchor": 1,
          "limitation_set": 1,
          "scope_statement": 1,
          "external_file_set": 1,
          "figure_slot": 1
        },
        "by_resolution": {
          "resolved_in_source": 9,
          "referenced_unresolved": 1,
          "declared_absent": 1
        },
        "resolved_in_source": 9,
        "referenced_unresolved": 1,
        "declared_absent": 1
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
            "end_char": 1953,
            "start_line": 0,
            "end_line": 80,
            "quote": "# DEM多面体颗粒与冰-结构混合模式失效验证面",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256(markdown) 本地重算并与契约哈希比对",
            "result": "resolved"
          },
          "note": "源文档本体；1953 字符 / 见 source.bytes_utf8"
        },
        {
          "asset_id": "A02",
          "asset_class": "parameter_set",
          "label": "几何与参数（多面体颗粒/冰/结构宽度）",
          "in_report_section": "## 1. 案例介绍 / ### 几何与参数",
          "locator": {
            "method": "char_span",
            "start_char": 148,
            "end_char": 188,
            "start_line": 10,
            "end_line": 10,
            "quote": "- 多面体颗粒：正二十面体（12顶点），半径0.01m，密度1000 kg/m³",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "引文为 markdown 逐字子串（脚本校验）",
            "result": "resolved"
          },
          "note": "同节还含冰参数 σ_c=3 MPa, σ_f=0.7 MPa, σ_t=0.7 MPa, h=1.0 m, E=5 GPa 与 D=10 m"
        },
        {
          "asset_id": "A03",
          "asset_class": "method_declaration",
          "label": "多面体接触检测与力模型（GJK/EPA、弹簧-阻尼、Cundall-Strack、EPSD）",
          "in_report_section": "## 2. 方法 / ### 多面体接触检测",
          "locator": {
            "method": "char_span",
            "start_char": 290,
            "end_char": 321,
            "start_line": 17,
            "end_line": 17,
            "quote": "- GJK/EPA算法（已有convex_contact模块）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "引文为 markdown 逐字子串（脚本校验）",
            "result": "resolved"
          },
          "note": "同节含法向/切向/滚动阻力公式"
        },
        {
          "asset_id": "A04",
          "asset_class": "method_declaration",
          "label": "冰失效模式公式（压溃/弯曲/劈裂 + Timco 临界速度）",
          "in_report_section": "## 2. 方法 / ### 冰失效模式",
          "locator": {
            "method": "char_span",
            "start_char": 458,
            "end_char": 512,
            "start_line": 23,
            "end_line": 23,
            "quote": "- 压溃：R_crush = 2.5·σ_c·h·D·f(V), f(V)=min(1+0.3V, 1.5)",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "引文为 markdown 逐字子串（脚本校验）",
            "result": "resolved"
          },
          "note": "同节含 R_bend/R_split 与 V_c=0.1·√(σ_f/(ρ·h)) (Timco 2001)"
        },
        {
          "asset_id": "A05",
          "asset_class": "table",
          "label": "验收判据表（C1–C9）",
          "in_report_section": "## 3. 计算结果 / ### 验收判据",
          "locator": {
            "method": "char_span",
            "start_char": 736,
            "end_char": 780,
            "start_line": 33,
            "end_line": 33,
            "quote": "| C1 | 休止角<10%偏差 | PASS | 0-70°范围（角状颗粒典型值） |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "引文为 markdown 逐字子串（脚本校验）",
            "result": "resolved"
          },
          "note": "C1–C9 九行判据，C9 为 N/A（GJK/EPA 与网格无关）"
        },
        {
          "asset_id": "A06",
          "asset_class": "numeric_anchor",
          "label": "测试统计（35/35/0）",
          "in_report_section": "## 3. 计算结果 / ### 测试统计",
          "locator": {
            "method": "char_span",
            "start_char": 1205,
            "end_char": 1214,
            "start_line": 44,
            "end_line": 44,
            "quote": "- 总测试数：35",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "引文为 markdown 逐字子串（脚本校验）",
            "result": "resolved"
          },
          "note": "同节：通过 35、失败 0"
        },
        {
          "asset_id": "A07",
          "asset_class": "table",
          "label": "误差判定表（休止角/V_c/R_total）",
          "in_report_section": "## 6. 误差判定",
          "locator": {
            "method": "char_span",
            "start_char": 1587,
            "end_char": 1627,
            "start_line": 70,
            "end_line": 70,
            "quote": "| V_c | Timco 2.76 m/s | 53% | 否（经验公式） |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "引文为 markdown 逐字子串（脚本校验）",
            "result": "resolved"
          },
          "note": "三项关键量均标注 否（<3%）；报告自述原因为简化工程公式"
        },
        {
          "asset_id": "A08",
          "asset_class": "limitation_set",
          "label": "局限（4 条）",
          "in_report_section": "## 5. 注意点 / ### 局限",
          "locator": {
            "method": "char_span",
            "start_char": 1295,
            "end_char": 1323,
            "start_line": 55,
            "end_line": 55,
            "quote": "1. 简化DEM显式时间积分；精确量化预测需更高级积分器",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "引文为 markdown 逐字子串（脚本校验）",
            "result": "resolved"
          },
          "note": "含准静态阻力公式、经验临界速度、力链各向异性简化"
        },
        {
          "asset_id": "A09",
          "asset_class": "scope_statement",
          "label": "适用范围",
          "in_report_section": "## 5. 注意点 / ### 适用范围",
          "locator": {
            "method": "char_span",
            "start_char": 1406,
            "end_char": 1430,
            "start_line": 61,
            "end_line": 61,
            "quote": "- 多面体颗粒：凸多面体，GJK/EPA接触检测",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "引文为 markdown 逐字子串（脚本校验）",
            "result": "resolved"
          },
          "note": "含冰失效工程近似与 V_c 适用条件（水平冰-垂直结构）"
        },
        {
          "asset_id": "A10",
          "asset_class": "external_file_set",
          "label": "产出文件（5 项，TensorDEM 仓内路径）",
          "in_report_section": "## 产出文件",
          "locator": {
            "method": "char_span",
            "start_char": 1723,
            "end_char": 1772,
            "start_line": 76,
            "end_line": 76,
            "quote": "- `src/tensordem/polyhedron/__init__.py`: 多面体颗粒力学",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "路径存在性检查：TensorKnowledge 工作树内不存在（本仓非源仓）",
            "result": "unresolved"
          },
          "note": "5 个路径（src/tensordem/polyhedron、src/tensordem/ice_mixed_mode、tests/test_dem_ice.py、docs/DEM_POLYHEDRON_MIXED_MODE.md、artifacts/dem_polyhedron_mixed_mode/）属 TensorDEM 源仓，本工作树不可解析；登记为 referenced_unresolved，不伪造解析"
        },
        {
          "asset_id": "A11",
          "asset_class": "figure_slot",
          "label": "结果图",
          "in_report_section": "## 4. 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 1242,
            "end_char": 1275,
            "start_line": 50,
            "end_line": 50,
            "quote": "（本任务为验证面实现，无数值场云图。相图和力链分布通过测试验证。）",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "报告显式声明无图；平台 figures 字段为空数组",
            "result": "absent"
          },
          "note": "declared_absent：源报告自述无图，非缺失"
        }
      ],
      "claims": [],
      "claims_note": "本工作包为 01-asset-registration（仅登记源资产，不做抽取）；按契约 notes，claims 为空数组。",
      "integrity": {
        "quote_uniqueness": "all quotes confirmed unique substrings of source markdown (scripts/kf_register_11557.py, checks.source_locator_resolvable)",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true
      }
    }
  },
  "claims": []
}
```
