# KF-RESULT wp-9503-01

工作包 `wp-9503-01` · 工序 `01-asset-registration` · report_id **9503** · lane B ·
source `tensor://reports/9503`（field=`markdown`）· 生成 2026-11-12T01:38:07Z ·
producer `kf-worker/m15644`

## ① 本工序做了什么

按契约只做一件事：**登记 report_id=9503 的源资产**（`objective.register_assets=true`、
`classify_report_type=false`）。具体交付：

1. 从平台 `GET /api/v1/tensor/reports/9503` 取 `markdown` 字段，落到
   `docs/kf/wp-9503-01/source_9503.md`（可入库快照；`runs/` 下另存一份运行副本），
   并对 UTF-8 字节重算 sha256 与契约 `source_hash` 逐位比对（**一致**）；
2. 在原文中定位并登记 **22 个资产**（15 类），每个资产带
   行号区间 + 字符区间 + 逐字引文（引文由程序在原文切片，非手抄），并对引文做**唯一性**校验；
3. 逐条记录"能否解析"：`resolved_in_source` 13 条、
   `referenced_unresolved` 8 条、`declared_absent` 1 条；
4. 探测报告声明的 4 张图的字节可获得性（平台 figures/artifacts 路由均 404 → 无字节，不声明图哈希）；
5. **不做抽取**：`claims` 为空数组，并在 `claims_empty_reason` 写明这是契约要求的完整结果而非遗漏；
6. **不置 verified**：任何字段都不包含 verified 标记（本工序只描述定位可解析性，验证由平台门计算）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

* 工具链：纯 Python3 标准库 + `jsonschema`（校验）+ `matplotlib`（定位图）。一键复跑脚本
  `scripts/kf_wp9503_01_register_assets.py`（子命令 fetch / build / envelope / verify / figure / result / all）。
* **零手抄机制**：资产表只写"锚点子串 + 相对行偏移"，引文在运行时由
  `"\n".join(lines[s-1:e])` 切出，随后断言 `md[start:end] == quote` 且 `md.count(quote) == 1`；
  锚点不唯一或引文不唯一 → `SystemExit`（宁可不产出，不产出半成品）。
* 会计口径：`chars` 用码点数（契约给的是 8176），`bytes_utf8` 单独记录（中文报告字节数更大），
  sha256 按**UTF-8 字节**计算 —— 与契约 `source_hash` 一致。
* 解析判定不是"看起来像"而是**探测**：本工作树对每个 `backend/**`、`artifacts/**` 地址做
  `Path.exists()`；平台侧对 `figures/<name>.png`、`figures/<name>`、`artifacts/<name>.png`
  三种 URL 形状各发一次 GET 并记录状态码。
* 报告结构（章节/行号）、图表声明、记录元数据（title/scenario_key/mission_id/tags/figures）
  全部由接口返回与原文测量得到，不写入任何未观测值。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-9503-01/asset_manifest.json` | 资产清单主体：source 对账 + 22 资产 + 7 节结构 + 图探测 + counts/integrity |
| `docs/kf/wp-9503-01/kf_result.json` | `kf_result.v1` 结果信封（唯一 json 代码块的内容来源），`outputs.asset_manifest.json` 内嵌上述清单 |
| `docs/kf/wp-9503-01/verification.json` | 9 项本地预检（6 项验收 + 契约约束项），全绿/失败逐条记录 |
| `docs/kf/wp-9503-01/figures/locator_map.png` | 定位图：22 条资产在 152 行原文上的区间条 + 右侧完整性检查面板 |
| `docs/kf/wp-9503-01/KF-RESULT-wp-9503-01.md` | 本报告（六段 + 唯一 json 块 + repro_cmd） |
| `schemas/asset_manifest.v2.schema.json` | 本次新增的**参数化**清单 schema（report-agnostic），供 `schema_pass` 可复现 |
| `docs/kf/wp-9503-01/source_9503.md` | 原文逐字快照（离线复算哈希/定位用；push 门会丢 runs/**，故另存一份） |
| `runs/wp-9503-01/record_9503.json` | 平台记录原始返回（title/scenario_key/mission_id/tags/figures） |

资产分类直方图（程序统计）：

| asset_class | 条数 |
|---|---|
| `code_reference` | 2 |
| `criteria_block` | 1 |
| `data_artifact_reference` | 2 |
| `defect_record_block` | 1 |
| `environment_declaration` | 1 |
| `evidence_grade_note` | 1 |
| `figure_reference` | 1 |
| `heading` | 1 |
| `limitation_declaration` | 1 |
| `markdown_document` | 1 |
| `provenance_declaration` | 2 |
| `repro_command` | 1 |
| `result_block` | 1 |
| `table` | 5 |
| `test_reference` | 1 |

## ④ 证据定位表（资产 → 原文引文片段）

引文一律为原文**逐字**切片（下表为截断展示，完整引文见 manifest 的 `locator.quote`；
平台可独立重算 sha256 与子串）。行号 1-based，字符区间为 `[start_char, end_char)`。

| asset_id | resolution | 行区间 | 原文引文（截断） | 所属章节 |
|---|---|---|---|---|
| A01 | resolved_in_source | 1–152 | `# EEXI attained 端到端闭合链路：Holtrop 阻力 → 推进功率 → 轴系效率 → gCO₂/(t·nm) /  / 节点 'p73w2b-n02-eexi-closed-loop' · 仓 shi …` | whole-document |
| A02 | resolved_in_source | 1–1 | `# EEXI attained 端到端闭合链路：Holtrop 阻力 → 推进功率 → 轴系效率 → gCO₂/(t·nm)` | header |
| A03 | resolved_in_source | 3–3 | `节点 'p73w2b-n02-eexi-closed-loop' · 仓 ship-performance-platform · 生成于 2026-11-09T05:49:25+00:00 ·` | header |
| A04 | referenced_unresolved | 4–4 | `commit '7017a623' · 全部数字由 'artifacts/eexi_closed_loop/run_eexi_closed_loop.py' 程序化注入（零手抄）` | header |
| A05 | resolved_in_source | 20–24 | `\| 船 \| 船型 \| DWT [t] \| Capacity [t] \| V_ref [kn] \| R_T [kN] \| P_E [kW] \| P_D [kW] \| η_O \| η_H \| η_S …` | ① 案例介绍 |
| A06 | resolved_in_source | 49–53 | `\| 船 \| G1 R_T 摩擦线偏差 [%] \| G2 能量残差 [-] \| G3 单位代数 \| EEXI att [gCO₂/(t·nm)] \| / \|---\|---\|---\|---\|---\ …` | ③ 计算结果 |
| A07 | resolved_in_source | 55–61 | `* G1（<3%）：'0.0696%' **PASS** / * G2（<1%）：独立力矩路线最大残差 '1.208e-05' **PASS**；幂等路线残差恒 0（恒等式，仅披露） / * G3 单位代数：'fin …` | ③ 计算结果 |
| A08 | resolved_in_source | 65–67 | `* 'kcs_3600teu'：P_E=25276.7 kW → P_D=37608.4 kW；2πnQ=36856.1 kW（η_S=0.98）→ P_D^torque=37608.3 kW；n=115.7 rpm …` | ③ 计算结果 |
| A09 | resolved_in_source | 71–80 | `\| V [kn] \| Holtrop R_T [kN] \| 表列 R_T [kN] \| 偏差 \| 表列 C_t·10³ \| 由 C_t 反推 R_T [kN] \| 表内不一致 \| / \|---\|- …` | ③ 计算结果 / 实验对标 |
| A10 | resolved_in_source | 82–83 | `表内 'C_t' 列与 'R_T' 列最大不一致 '20.3%'，故该表证据等级 / **WITHHELD**：只作量级参考，不用于标定、不用于 PASS 判定（见 ⑤）。` | ③ 计算结果 / 实验对标 |
| A11 | resolved_in_source | 87–91 | `\| 船 \| 基线 EEXI \| 各情形 ΔEEXI \| / \|---\|---\|---\| / \| kcs_3600teu \| 35.992 \| Cwp-3%:-1.74% / Cwp+3%:+1. …` | ③ 计算结果 / 敏感度 |
| A12 | referenced_unresolved | 95–99 | `* 'fig1_resistance.png'：三型船 R_T(V)/R_F(V) 曲线 + V_ref（点线）+ KCS 水池表散点；右图为 /   Holtrop vs 表偏差 与 表内 C_t↔R_T 自一致性 …` | ④ 结果图 |
| A13 | referenced_unresolved | 61–61 | `* G5：'artifacts/eexi_closed_loop.json'（本文件即由其生成，判据数字齐备）` | ③ 计算结果 / G5 |
| A14 | referenced_unresolved | 149–149 | `* 产物：'artifacts/eexi_closed_loop.json'、'artifacts/eexi_closed_loop/*.png'、本报告` | 审计链 |
| A15 | referenced_unresolved | 146–146 | `* 代码：'backend/modules/eexi_closed_loop/{chain.py,fleet.py,data/reference_ships.json}'、` | 审计链 |
| A16 | referenced_unresolved | 147–148 | `  'backend/api/green_shipping.py'（新增 '/eexi_closed_loop'、'/eexi_closed_loop/reference_fleet'； /   修 '_gn_att …` | 审计链 |
| A17 | referenced_unresolved | 41–41 | `   'backend/tests/test_eexi_closed_loop.py' 38 例。` | ② 怎么做的 |
| A18 | referenced_unresolved | 150–151 | `* 复现：'python backend/../artifacts/eexi_closed_loop/run_eexi_closed_loop.py'（无随机数、无网络） /   + 'cd backend && p …` | 审计链 |
| A19 | resolved_in_source | 152–152 | `* 环境：3.11.6 on Linux-6.6.52-1.7.lns23.loongarch64-loongarch64-with-glibc2.38` | 审计链 |
| A20 | resolved_in_source | 103–109 | `1. **发现并修复一个真实缺陷（1852 倍量纲错）**：'_gn_attained_index' 原实现把分母航程取 /    'V_ref[kn]×1852/3600×3600'（米/小时），得到 gCO₂/( …` | ⑤ 注意点 |
| A21 | resolved_in_source | 131–138 | `\| 关键量 \| 基准 \| 误差 \| 判据 \| 是否 <3% \| / \|---\|---\|---\|---\|---\| / \| Holtrop Cf @V_ref \| ITTC-57/78 摩擦线 …` | ⑥ 误差判定 |
| A22 | declared_absent | 140–142 | `honest 结论：G1/G2/G3(量纲)/G4/G5 全部按判据通过且可机器复现；**"与 IMO 示例船 <5%"这一项未能完成**， / 原因是离线环境无法取得 MEPC.328(76)/350(78) 原文 …` | ⑥ 误差判定 |

图声明探测（平台元数据 + 字节可用性）：

| 图 | 原文文件名 | 原文行 | record 有 caption | 字节可取 |
|---|---|---|---|---|
| fig1_resistance | fig1_resistance.png | 95 | yes | no |
| fig2_efficiency | fig2_efficiency.png | 97 | yes | no |
| fig3_eexi | fig3_eexi.png | 98 | yes | no |
| fig4_gates | fig4_gates.png | 99 | yes | no |

未解析/缺席资产的目标地址与实际探测结果（不臆造地址、不假装存在）：

| asset_id | 报告中的地址 | 类型 | exists_in_worktree |
|---|---|---|---|
| A04 | `commit:7017a623` | git_commit | n/a（非工作树地址） |
| A12 | `fig1_resistance.png` | figure_png | False |
| A13 | `artifacts/eexi_closed_loop.json` | data_json | False |
| A14 | `artifacts/eexi_closed_loop/*.png` | figure_glob | n/a（非工作树地址） |
| A15 | `backend/modules/eexi_closed_loop/chain.py` | source_code | False |
| A16 | `backend/api/green_shipping.py` | source_code | False |
| A17 | `backend/tests/test_eexi_closed_loop.py` | test_code | False |
| A18 | `artifacts/eexi_closed_loop/run_eexi_closed_loop.py` | source_code | False |
| A22 | `（无显式地址：基准本身缺席）` | external_baseline | n/a（非工作树地址） |

关键对账数字（全部由脚本测量，非记忆）：

* `source.hash` = `sha256:195c350dd486cb556f078b220cb348edf9210d4ac2631319b40658ee73428b5c` == 契约 `sha256:195c350dd486cb556f078b220cb348edf9210d4ac2631319b40658ee73428b5c`（**逐位一致**）
* `chars` = 8176 == 契约 8176；`bytes_utf8` = 11861；`lines` = 152
* 平台记录：title/scenario_key 与契约**一致**（`title_matches_contract`=True、
  `scenario_matches_contract`=True），
  status=`published`、mission_id=8233、标签 6 个
* 引文唯一性：22 条资产全部通过 `md.count(quote)==1`（document 资产按全文计）

## ⑤ 注意点与局限

1. **本工序不产生知识断言**：`claims=[]`。报告内的 35.992/3.558/2.816、0.0696%、1852 倍等数字
   在 manifest 里只以**引文**形式存在，未被换算、未被重算、未被置为 verified —— 任何下游要引用
   这些数字，必须自己回到原文（行号已给）并走自己的证据门。
2. **图字节不可得**：4 张图只有文件名（原文 L95–L99）与 record 里的 name+caption；
   `/tensor/reports/9503/figures/*`、`/artifacts/*` 均返回 404，TensorKnowledge 工作树内也无 PNG。
   因此**不声明任何图哈希**，也不声称图存在——这是 WITHHELD 式的诚实处理，不是遗漏。
3. **跨仓不可核**：`backend/**`、`artifacts/**`、commit `7017a623` 全部属 ship-performance-platform
   私有仓。本工作树逐条探测 `exists_in_worktree=false`，故整体挂 `referenced_unresolved`。
   这意味着：**报告声称的 1852 倍缺陷修复、38 例回归测试、复跑脚本，本工序一律未复核**，
   只登记其在原文中的位置。任何"已修复/已验证"的判断都需要另派一个能访问该仓的工作包。
4. **`declared_absent` 不是我判的**：A22 是报告自己写的 honest 结论（MEPC 原文离线不可得、
   仓内水池表 C_t↔R_T 自不一致 20.3%）。本工序仅登记这段自我披露的位置，不对其结论加码或减码。
5. **schema 边界**：契约引用的 `schemas/asset_manifest.*.schema.json` 在此前只有 `v1`
   实例级（`const: wp-448-01`）版本，无法用于本包。为此新增 `asset_manifest.v2`（report-agnostic
   的 pattern 版），未改动 v1（那是别的工作包的产物）。若平台侧 schema 与此不同，以平台门为准，
   本产物需按平台 schema 修订。
6. **单报告作用域**：所有输入输出路径由 `REPORT_ID=9503` 派生，脚本不含其它 report_id 常量
   （预检项 `single_report_scope`）。
7. 本报告的 `mission_id` 字段取本次派单的 15644；报告本体（report 9503）自身的 mission_id 是
   8233，两者不是同一个概念，已分别记录。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 证据（verification.json detail 截断） |
|---|---|---|
| `valid_json` | ✅ | asset_manifest.json and kf_result.json both parse |
| `schema_pass` | ✅ | envelope vs schemas/kf_result.v1.schema.json + manifest vs schemas/asset_manifest.v2.schema.json; errors=0 [] |
| `source_locator_resolvable` | ✅ | 22 locators re-checked (char-span round-trip + unique substring + line numbers agree); failures=[] |
| `source_hash_matches` | ✅ | live=sha256:195c350dd486cb556f078b220cb348edf9210d4ac2631319b40658ee73428b5c contract=sha256:195c350dd486cb556f078b220cb348edf9210 … |
| `no_duplicate_ids` | ✅ | asset ids=22 claims=0 duplicates=[] |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✅ | claims=0 (empty is the contract's complete result); violations=[] |

契约级约束附加检查：

| 检查 | 结果 | 说明 |
|---|---|---|
| `no_verified_marks` | ✅ | no 'verified' status/word appears in the manifest; resolution describes locator resolvability only |
| `record_identity_matches_contract` | ✅ | title_matches_contract=True scenario_matches_contract=True status=published mission_id=8233 |
| `single_report_scope` | ✅ | package reads/writes report_id=9503 only; all output paths are built from REPORT_ID |

**总体**：6 项验收全部通过（本地预检）。
如实说明：以上均为**本地预检**，不是平台门结论；平台会独立重算 source_hash 与子串可解析性，
且 verification 由平台计算——本报告未把任何条目标成 verified。

## repro_cmd（一键复跑）

```bash
cd <worktree-root> && python3 scripts/kf_wp9503_01_register_assets.py all
# 分步：fetch -> build -> envelope -> verify -> figure -> result
# 依赖：python3 + jsonschema + matplotlib；环境变量 TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS
# 期望：verify 全绿，source hash 与契约 195c350d…8b5c 逐位一致
```

`all` 的顺序即 fetch → build → envelope → verify → figure → result；任何一步断言失败即 `SystemExit`。

## 结果信封（唯一 json 块）

```json
{
  "package_id": "wp-9503-01",
  "task_type": "01-asset-registration",
  "report_id": "9503",
  "provenance": {
    "source_hash": "sha256:195c350dd486cb556f078b220cb348edf9210d4ac2631319b40658ee73428b5c",
    "source_field": "markdown",
    "producer": "kf-worker/m15644",
    "emitted_at": "2026-11-12T01:38:07Z",
    "notes": "source_uri=tensor://reports/9503; hash over the UTF-8 bytes of the markdown field served by GET /api/v1/tensor/reports/9503, recomputed locally at build and again against the live document at verify time (verification.json)."
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v2",
      "package_id": "wp-9503-01",
      "task_type": "01-asset-registration",
      "report_id": "9503",
      "lane": "B",
      "generated_at": "2026-11-12T01:38:07Z",
      "producer": "kf-worker/m15644",
      "objective": {
        "register_assets": true,
        "classify_report_type": false,
        "extraction_performed": false
      },
      "source": {
        "uri": "tensor://reports/9503",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "195c350dd486cb556f078b220cb348edf9210d4ac2631319b40658ee73428b5c",
        "hash_prefixed": "sha256:195c350dd486cb556f078b220cb348edf9210d4ac2631319b40658ee73428b5c",
        "contract_hash": "sha256:195c350dd486cb556f078b220cb348edf9210d4ac2631319b40658ee73428b5c",
        "hash_matches_contract": true,
        "chars": 8176,
        "contract_chars": 8176,
        "chars_match_contract": true,
        "bytes_utf8": 11861,
        "bytes_note": "byte count differs from chars because the report is CJK-heavy; the contract hashes UTF-8 bytes while chars counts code points",
        "lines": 152,
        "has_crlf": false,
        "has_trailing_newline": true,
        "line_counting": "logical lines = markdown.rstrip(chr(10)).split(chr(10)); 1-based",
        "fetched_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/9503",
        "fetched_at": "2026-11-12T01:38:06Z",
        "record_fields": {
          "title": "EEXI attained 端到端闭合链路（Holtrop→推进功率→轴系效率→gCO₂/t·nm）+ 1852 倍量纲缺陷修复",
          "scenario_key": "p73w2b-n02-eexi-closed-loop",
          "mission_id": 8233,
          "status": "published",
          "tags": [
            "EEXI",
            "绿色航行",
            "Holtrop-Mennen",
            "推进效率",
            "量纲一致性",
            "defect_fix"
          ],
          "created_at": "2026-11-09T05:51:15.514360+00:00",
          "contract_title": "EEXI attained 端到端闭合链路（Holtrop→推进功率→轴系效率→gCO₂/t·nm）+ 1852 倍量纲缺陷修复",
          "contract_scenario_key": "p73w2b-n02-eexi-closed-loop",
          "title_matches_contract": true,
          "scenario_matches_contract": true
        },
        "platform_figures": [
          {
            "name": "fig1_resistance",
            "caption": "三型船 Holtrop R_T(V) 与 R_F(V)（点线=V_ref）+ KCS 水池表散点；右图：Holtrop vs 表偏差 与 表内 C_t↔R_T 自一致性（±15% 接受带）"
          },
          {
            "name": "fig2_efficiency",
            "caption": "效率链分解 η_H/η_O/η_S/η_total 与 P_E→P_D 功率对照（柱上标注独立力矩路线 2πnQ）"
          },
          {
            "name": "fig3_eexi",
            "caption": "三型船（集箱 KCS / 散货 JBC / 油轮 KVLCC2）EEXI attained vs required 及比值"
          },
          {
            "name": "fig4_gates",
            "caption": "判据复核：G1 摩擦线偏差（3% 门禁线）与 G2 能量/推力闭合残差（1% 门禁线）"
          }
        ],
        "platform_tags": [
          "EEXI",
          "绿色航行",
          "Holtrop-Mennen",
          "推进效率",
          "量纲一致性",
          "defect_fix"
        ],
        "producer_environment": {
          "python": "3.11.6",
          "platform": "linux"
        }
      },
      "sections": [
        {
          "heading": "## ① 案例介绍（物理背景 / 几何 / 参数表）",
          "line": 6,
          "kind": "section"
        },
        {
          "heading": "## ② 怎么做的（方法 / 流程 / 工具链）",
          "line": 26,
          "kind": "section"
        },
        {
          "heading": "## ③ 计算结果",
          "line": 45,
          "kind": "section"
        },
        {
          "heading": "## ④ 结果图",
          "line": 93,
          "kind": "section"
        },
        {
          "heading": "## ⑤ 注意点（坑 / 局限 / 适用范围）",
          "line": 101,
          "kind": "section"
        },
        {
          "heading": "## ⑥ 误差判定（关键量 vs 基准，逐项）",
          "line": 129,
          "kind": "section"
        },
        {
          "heading": "## 审计链",
          "line": 144,
          "kind": "audit_chain"
        }
      ],
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "markdown_document",
          "label": "报告正文（markdown 全文，source_field=markdown）",
          "in_report_section": "whole-document",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_and_char_span_roundtrips",
            "result": "resolved"
          },
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 8176,
            "start_line": 1,
            "end_line": 152,
            "quote": "# EEXI attained 端到端闭合链路：Holtrop 阻力 → 推进功率 → 轴系效率 → gCO₂/(t·nm)\n\n节点 `p73w2b-n02-eexi-closed-loop` · 仓 ship-performance-platform · 生成于 2026-11-09T05:49:25+00:00 ·\ncommit `7017a623` · 全部数字由 `artifacts/eexi_closed_loop/run_eexi_closed_loop.py` 程序化注入（零手抄）\n\n## ① 案例介绍（物理背景 / 几何 / 参数表）\n\nEEXI（Energy Efficiency Existing Ship Index，MEPC.328(76) 修正 MEPC.350(78) 计算法）要求把\n**主机功率 → 燃油消耗 → CO₂ 排放 → 单位运输功排放** 串成一条闭合链，与要求的参考线比较。\n平台此前只有\"链的下半段\"（给定 P_ME 后算 gCO₂/(t·nm)），阻力与推进功率由外部手工填写，\n因而 attained EEXI 无法从船体几何独立复算——证据等级只能挂 WITHHELD。\n\n本节点把链路补齐为：**裸船体几何 → Holtrop-Mennen(1984) 总阻力 R_T(V_ref) → 有效功率\nP_E=R_T·V → 推进效率分解 η_H·η_O·η_S（BEMT 敞水曲线反解转速，T(1−t)=R_T 闭合）→\n主机轴功率 P_D → 燃油率 P_D·SFOC → CO₂ 率 ×C_F → EEXI_attained = CO₂/(Capacity·V_ref)**，\n并用 3 型公开标模船（集箱 KCS / 散货 JBC / 油轮 KVLCC2）给出 attained vs required 对比。\n\n几何/工况参数（逐字段证据来源见 `reference_ships.json:field_grades`；几何先过 Cb·Lpp·B·T 与 ∇ 自检）：\n\n| 船 | 船型 | DWT [t] | Capacity [t] | V_ref [kn] | R_T [kN] | P_E [kW] | P_D [kW] | η_O | η_H | η_S | η_tot | EEXI att | EEXI req | att/req |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n| kcs_3600teu | container_ship | 36000 | 25200 | 24.0 | 2047.2 | 25277 | 37608 | 0.625 | 1.097 | 0.98 | 0.672 | 35.992 | 18.176 | 1.98 |\n| jbc_180k | bulk_carrier | 180000 | 180000 | 14.5 | 1294.5 | 9656 | 17025 | 0.520 | 1.113 | 0.98 | 0.567 | 3.558 | 2.396 | 1.49 |\n| kvlcc2_300k | tanker | 300000 | 300000 | 15.5 | 1833.8 | 14622 | 24115 | 0.558 | 1.109 | 0.98 | 0.606 | 2.816 | 2.071 | 1.36 |\n\n## ② 怎么做的（方法 / 流程 / 工具链）\n\n1. **单源复用，不写第二份公式**：\n   * 阻力 `physics/holtrop/mennen.py::holtrop1984_resistance`（m2082 阻力族并一后的唯一 Holtrop 实现），\n     摩擦线校验用 `physics/holtrop/friction.py`（Schoenherr 独立线、ITTC-78 粗糙度补贴）；\n   * 敞水与船-桨配合 `modules/propeller_bemt.py::solve_n_for_thrust / select_diameter_and_pitch`\n     （BEMT 敞水曲线 + 对数二分反解 n，P/D 扫掠最大化 η_D）；\n   * EEXI 指数只由 `api/green_shipping.py::_gn_attained_index` 给，闭合链路只提供功率与碳质量，\n     两者在 API 响应里做逐位对账（`cross_source_rel_err`）。\n2. **新增模块** `backend/modules/eexi_closed_loop/`（`chain.py` 纯物理核 + `fleet.py` 批量 +\n   `data/reference_ships.json` 三型船数据与证据分级）。\n3. **API**：`POST /api/v1/green-shipping/eexi_closed_loop`（几何直算 attained EEXI）、\n   `GET /api/v1/green-shipping/eexi_closed_loop/reference_fleet`（G4 对比表）。\n4. **判据机器化**：G1 摩擦线一致性、G2 能量守恒（幂等路线 + 独立力矩路线 2πnQ）、\n   G3 单位代数（机器化简单位，不靠人眼）、G4 三型船表、G5 产物 JSON；pytest\n   `backend/tests/test_eexi_closed_loop.py` 38 例。\n5. **敏感度**：对 Cwp ±3%、LCB ±1%Lpp、SFOC ±5%、η_S∈[0.96,0.99]、D/T ±20% 扫掠，\n   量化\"假设值不确定度\"对 EEXI 的传导，区分\"判据精度\"与\"输入假设带\"。\n\n## ③ 计算结果\n\n### 判据汇总（逐船）\n\n| 船 | G1 R_T 摩擦线偏差 [%] | G2 能量残差 [-] | G3 单位代数 | EEXI att [gCO₂/(t·nm)] |\n|---|---|---|---|---|\n| kcs_3600teu | 0.0696 | 3.345e-06 | exact | 35.992 |\n| jbc_180k | 0.0593 | 3.417e-07 | exact | 3.558 |\n| kvlcc2_300k | 0.0654 | 1.208e-05 | exact | 2.816 |\n\n* G1（<3%）：`0.0696%` **PASS**\n* G2（<1%）：独立力矩路线最大残差 `1.208e-05` **PASS**；幂等路线残差恒 0（恒等式，仅披露）\n* G3 单位代数：`final_unit = g/(t·nm)`，与目标 `g/(t·nm)` 精确一致 **PASS**；\n  与绿航单源指数最大相对差 `0.0e+00` **PASS**；\n  与 IMO 示例船逐点对标：**WITHHELD**（离线不可回读 MEPC 原文，不做伪对标，见 ⑥）\n* G4：`bulk_carrier, container_ship, tanker` 三型船对比表已产出（上表 ①）\n* G5：`artifacts/eexi_closed_loop.json`（本文件即由其生成，判据数字齐备）\n\n### 效率链与碳链分解（含独立力矩路线对账）\n\n* `kcs_3600teu`：P_E=25276.7 kW → P_D=37608.4 kW；2πnQ=36856.1 kW（η_S=0.98）→ P_D^torque=37608.3 kW；n=115.7 rpm，J=0.632，K_T=0.2323，K_Q=0.03736；CO₂=21743.4 kg/h\n* `jbc_180k`：P_E=9656.0 kW → P_D=17025.1 kW；2πnQ=16684.6 kW（η_S=0.98）→ P_D^torque=17025.1 kW；n=86.0 rpm，J=0.392，K_T=0.1921，K_Q=0.02304；CO₂=9276.2 kg/h\n* `kvlcc2_300k`：P_E=14622.2 kW → P_D=24115.2 kW；2πnQ=23633.2 kW（η_S=0.98）→ P_D^torque=24115.5 kW；n=72.0 rpm，J=0.439，K_T=0.1903，K_Q=0.02381；CO₂=13080.9 kg/h\n\n### 实验对标（KCS 公开水池表，作为审计对象而非标定源）\n\n| V [kn] | Holtrop R_T [kN] | 表列 R_T [kN] | 偏差 | 表列 C_t·10³ | 由 C_t 反推 R_T [kN] | 表内不一致 |\n|---|---|---|---|---|---|---|\n| 16.0 | 702.4 | 580.0 | +21.1% | 2.15 | 697.8 | +20.3% |\n| 18.0 | 922.6 | 820.0 | +12.5% | 2.28 | 936.5 | +14.2% |\n| 20.0 | 1208.5 | 1180.0 | +2.4% | 2.52 | 1277.9 | +8.3% |\n| 22.0 | 1571.7 | 1740.0 | -9.7% | 3.05 | 1871.5 | +7.6% |\n| 24.0 | 2047.2 | 2650.0 | -22.7% | 3.80 | 2774.9 | +4.7% |\n| 25.0 | 2358.5 | 3450.0 | -31.6% | 4.50 | 3565.6 | +3.3% |\n| 26.0 | 2707.9 | 4600.0 | -41.1% | 5.60 | 4799.2 | +4.3% |\n| 27.0 | 3059.9 | 6200.0 | -50.6% | 7.20 | 6654.2 | +7.3% |\n\n表内 `C_t` 列与 `R_T` 列最大不一致 `20.3%`，故该表证据等级\n**WITHHELD**：只作量级参考，不用于标定、不用于 PASS 判定（见 ⑤）。\n\n### 敏感度（输入假设的传导，非精度声明）\n\n| 船 | 基线 EEXI | 各情形 ΔEEXI |\n|---|---|---|\n| kcs_3600teu | 35.992 | Cwp-3%:-1.74% / Cwp+3%:+1.92% / lcb-1%Lpp:-0.02% / lcb+1%Lpp:+0.12% / SFOC-5%:-4.85% / SFOC+5%:+4.85% / eta_s=0.96:+2.07% / eta_s=0.99:-1.00% / D/T-20%:+10.93% / D/T+20%:-6.88% |\n| jbc_180k | 3.558 | Cwp-3%:-1.96% / Cwp+3%:+2.27% / lcb-1%Lpp:-0.12% / lcb+1%Lpp:+0.62% / SFOC-5%:-4.80% / SFOC+5%:+4.80% / eta_s=0.96:+2.05% / eta_s=0.99:-0.99% / D/T-20%:+14.25% / D/T+20%:-9.19% |\n| kvlcc2_300k | 2.816 | Cwp-3%:-1.50% / Cwp+3%:+1.54% / lcb-1%Lpp:-0.05% / lcb+1%Lpp:+0.28% / SFOC-5%:-4.82% / SFOC+5%:+4.82% / eta_s=0.96:+2.06% / eta_s=0.99:-1.00% / D/T-20%:+13.34% / D/T+20%:-8.55% |\n\n## ④ 结果图\n\n* `fig1_resistance.png`：三型船 R_T(V)/R_F(V) 曲线 + V_ref（点线）+ KCS 水池表散点；右图为\n  Holtrop vs 表偏差 与 表内 C_t↔R_T 自一致性（±15% 接受带）。\n* `fig2_efficiency.png`：效率链分解 η_H/η_O/η_S/η_total 与 P_E→P_D 功率（柱上标注独立力矩路线 2πnQ）。\n* `fig3_eexi.png`：三型船 EEXI attained vs required 及比值。\n* `fig4_gates.png`：G1 摩擦线偏差（对数坐标，含 3% 门禁线）与 G2 能量残差（含 1% 门禁线）。\n\n## ⑤ 注意点（坑 / 局限 / 适用范围）\n\n1. **发现并修复一个真实缺陷（1852 倍量纲错）**：`_gn_attained_index` 原实现把分母航程取\n   `V_ref[kn]×1852/3600×3600`（米/小时），得到 gCO₂/(t·**m**)，与响应里声明的\n   `gCO2/(t·nm)` 差 1852 倍，而 required 按 g/(t·nm) 给出 ⇒ **任何船都被判\"合规\"**\n   （VLCC 实测：attained 0.001521、required 2.0710、ratio 0.00073）。\n   已改为海里并加解析回归测试（`TestEexiUnitDefectRegression`）；修复后 attained 2.8160、\n   ratio 1.360，与物理手算逐位一致。此为 m1895 同类缺陷（CII 用 km 当 nm）\n   在 EEXI/EEDI 达到值上的复现，属结构性回归点。\n2. **η_S 语义**：按战役判据 G2 的定义 `P_D = R_T·V/(η_H·η_O·η_S)` 实现，此处 `P_D` 物理上\n   等于进 EEXI 的主机轴功率 P_ME；螺旋桨收到功率另记 `P_D_propeller = 2πnQ`，二者由 η_S 联系。\n   \"独立力矩路线\"（P_D^prop=2πnQ，K_Q 取自 BEMT 而非由效率链除出）与效率链的差\n   `1.2e-05` 是本节点能量守恒的实质证据；但须诚实说明：两条路线共享\n   η_O/η_H 的定义（BEMT 内部满足 η0·2πnQ = T·V_a），故该残差度量的实质是**推力闭合\n   T(1−t)=R_T 的数值收敛**（二分容差 1e-5），并非两条独立物理路径的交叉验证；\n   幂等路线残差为 0 属恒等式，一并披露，不作为精度声明。\n3. **ITTC'78 粗糙度补贴与 Holtrop CA 的重叠**：ΔC_F(k_s=150 µm) 会给 R_T 加 10%~12%，\n   但它与 Holtrop 的统计相关补贴 C_A 功能重叠，叠加即重复计账。故 G1 判定只取\n   **摩擦线（Schoenherr vs ITTC-57/78 线，0.06%~0.07%）**，粗糙度情景作为披露项单列。\n4. **回归域**：JBC 的 Cb=0.858 与 Cp=0.860 略越 Holtrop 回归域上限（0.85），域门禁已如实告警；\n   该船 EEXI 精度应打折，不得当作 <3% 精度证据。\n5. **V_ref 与 P_ME 的工况一致性**：EEXI 规制取 P_ME=0.75·MCR 与 EEDI 参考航速配对；本链路按\n   \"V_ref 处的阻力功率需求\"解释 P_ME，对高速集箱船（KCS 24 kn）相当于 0.85~0.9 MCR 工况，\n   故 attained 偏保守（偏大），仅作指示性对比，不作为规范符合性结论。\n6. **参考船数据分级**：主尺度/船型系数/附体面积取公开标模（且与仓内 m547 KCS 基线逐字段断言一致），\n   SFOC/η_S/桨径比/燃料为工程典型假设（无设备实测）。各假设对 attained EEXI 的最大传导\n   （程序化取自有符号 |Δ| 最大者）：kcs_3600teu: D/T-20% → 10.9%；jbc_180k: D/T-20% → 14.3%；kvlcc2_300k: D/T-20% → 13.3%。\n\n## ⑥ 误差判定（关键量 vs 基准，逐项）\n\n| 关键量 | 基准 | 误差 | 判据 | 是否 <3% |\n|---|---|---|---|---|\n| Holtrop Cf @V_ref | ITTC-57/78 摩擦线（0.075/(log₁₀Re−2)²） | 0.0696%（R_T 级） | G1 <3% | **是** |\n| Holtrop R_T @V_ref | Schoenherr 独立摩擦线替换 | 0.0696%（Cf 级） | G1 <3% | **是** |\n| P_D 能量闭合 | 力矩路线 2πnQ/η_S = 推力闭合 T(1−t)=R_T（二分容差 1e-5） | 1.208e-05 | G2 <1% | **是** |\n| gCO₂/(t·nm) 量纲 | 单位代数（kW·g/kWh·C_F/(t·kn)） | 精确一致 | G3 | **是** |\n| EEXI attained | IMO 示例船逐点值 | 不可复核 | G3 对标 | **未判**（WITHHELD，理由：离线无 MEPC 原文） |\n| Holtrop R_T @24 kn | 仓内 KRISO_tank 表 2650 kN | -22.7% | 实验带 ±15% | **否**（且该表自身 C_t↔R_T 不一致 20.3%，基准不可信 → 不作精度声明） |\n\nhonest 结论：G1/G2/G3(量纲)/G4/G5 全部按判据通过且可机器复现；**\"与 IMO 示例船 <5%\"这一项未能完成**，\n原因是离线环境无法取得 MEPC.328(76)/350(78) 原文或可核示例船数据，按纪律挂 WITHHELD 而不编造对标值。\n\"对实验 <3%\"亦未达成，且所依据的仓内水池表自相矛盾，故如实记录为\"基准不可用\"。\n\n## 审计链\n\n* 代码：`backend/modules/eexi_closed_loop/{chain.py,fleet.py,data/reference_ships.json}`、\n  `backend/api/green_shipping.py`（新增 `/eexi_closed_loop`、`/eexi_closed_loop/reference_fleet`；\n  修 `_gn_attained_index`）、`backend/tests/test_eexi_closed_loop.py`\n* 产物：`artifacts/eexi_closed_loop.json`、`artifacts/eexi_closed_loop/*.png`、本报告\n* 复现：`python backend/../artifacts/eexi_closed_loop/run_eexi_closed_loop.py`（无随机数、无网络）\n  + `cd backend && python -m pytest tests/test_eexi_closed_loop.py -q`\n* 环境：3.11.6 on Linux-6.6.52-1.7.lns23.loongarch64-loongarch64-with-glibc2.38\n",
            "unique": true
          },
          "note": "整篇 markdown 即源资产；sha256/字符数/字节数与契约逐项对账见 source 段。"
        },
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "H1 标题行（报告标题）",
          "in_report_section": "header",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_and_char_span_roundtrips",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 62,
            "start_line": 1,
            "end_line": 1,
            "quote": "# EEXI attained 端到端闭合链路：Holtrop 阻力 → 推进功率 → 轴系效率 → gCO₂/(t·nm)",
            "unique": true
          },
          "note": "与平台 record.title 同源；记录值含括号内演绎，标题行不含。"
        },
        {
          "asset_id": "A03",
          "asset_class": "provenance_declaration",
          "label": "产物来源声明（节点键 / 仓 / 生成时间）",
          "in_report_section": "header",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_and_char_span_roundtrips",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 64,
            "end_char": 160,
            "start_line": 3,
            "end_line": 3,
            "quote": "节点 `p73w2b-n02-eexi-closed-loop` · 仓 ship-performance-platform · 生成于 2026-11-09T05:49:25+00:00 ·",
            "unique": true
          },
          "note": "声明本报告由节点 p73w2b-n02-eexi-closed-loop 在 ship-performance-platform 生成；节点键与契约 scenario_key 一致。"
        },
        {
          "asset_id": "A04",
          "asset_class": "provenance_declaration",
          "label": "版本与零手抄声明（commit 7017a623 + 生成脚本）",
          "in_report_section": "header",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "target_path_probed_in_worktree",
            "result": "unresolved",
            "target_probe": {
              "exists_in_worktree": null
            }
          },
          "locator": {
            "method": "char_span",
            "start_char": 161,
            "end_char": 250,
            "start_line": 4,
            "end_line": 4,
            "quote": "commit `7017a623` · 全部数字由 `artifacts/eexi_closed_loop/run_eexi_closed_loop.py` 程序化注入（零手抄）",
            "unique": true
          },
          "note": "commit 7017a623 属 ship-performance-platform 私有仓，本工作树（TensorKnowledge）无法解析/校验该 commit，仅登记为文本声明。",
          "target": {
            "address_as_written": "commit:7017a623",
            "kind": "git_commit",
            "ext_kind": "vcs",
            "exists_in_worktree": null,
            "reason": "address belongs to ship-performance-platform (private repo) or is an external baseline; this worktree is TensorKnowledge"
          }
        },
        {
          "asset_id": "A05",
          "asset_class": "table",
          "label": "几何/工况参数表（3 型船 × 15 列）",
          "in_report_section": "① 案例介绍",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_and_char_span_roundtrips",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 869,
            "end_char": 1467,
            "start_line": 20,
            "end_line": 24,
            "quote": "| 船 | 船型 | DWT [t] | Capacity [t] | V_ref [kn] | R_T [kN] | P_E [kW] | P_D [kW] | η_O | η_H | η_S | η_tot | EEXI att | EEXI req | att/req |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n| kcs_3600teu | container_ship | 36000 | 25200 | 24.0 | 2047.2 | 25277 | 37608 | 0.625 | 1.097 | 0.98 | 0.672 | 35.992 | 18.176 | 1.98 |\n| jbc_180k | bulk_carrier | 180000 | 180000 | 14.5 | 1294.5 | 9656 | 17025 | 0.520 | 1.113 | 0.98 | 0.567 | 3.558 | 2.396 | 1.49 |\n| kvlcc2_300k | tanker | 300000 | 300000 | 15.5 | 1833.8 | 14622 | 24115 | 0.558 | 1.109 | 0.98 | 0.606 | 2.816 | 2.071 | 1.36 |",
            "unique": true
          },
          "note": "表头+分隔行+3 行数据；数值仅登记，不换算、不重算。"
        },
        {
          "asset_id": "A06",
          "asset_class": "table",
          "label": "判据汇总表（G1/G2/G3 逐船）",
          "in_report_section": "③ 计算结果",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_and_char_span_roundtrips",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 2504,
            "end_char": 2756,
            "start_line": 49,
            "end_line": 53,
            "quote": "| 船 | G1 R_T 摩擦线偏差 [%] | G2 能量残差 [-] | G3 单位代数 | EEXI att [gCO₂/(t·nm)] |\n|---|---|---|---|---|\n| kcs_3600teu | 0.0696 | 3.345e-06 | exact | 35.992 |\n| jbc_180k | 0.0593 | 3.417e-07 | exact | 3.558 |\n| kvlcc2_300k | 0.0654 | 1.208e-05 | exact | 2.816 |",
            "unique": true
          },
          "note": "G1/G2/G3 的机器化判据数字；证据等级由平台门计算，本工序不置标。"
        },
        {
          "asset_id": "A07",
          "asset_class": "criteria_block",
          "label": "判据条目 G1–G5（含 WITHHELD 披露）",
          "in_report_section": "③ 计算结果",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_and_char_span_roundtrips",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 2758,
            "end_char": 3117,
            "start_line": 55,
            "end_line": 61,
            "quote": "* G1（<3%）：`0.0696%` **PASS**\n* G2（<1%）：独立力矩路线最大残差 `1.208e-05` **PASS**；幂等路线残差恒 0（恒等式，仅披露）\n* G3 单位代数：`final_unit = g/(t·nm)`，与目标 `g/(t·nm)` 精确一致 **PASS**；\n  与绿航单源指数最大相对差 `0.0e+00` **PASS**；\n  与 IMO 示例船逐点对标：**WITHHELD**（离线不可回读 MEPC 原文，不做伪对标，见 ⑥）\n* G4：`bulk_carrier, container_ship, tanker` 三型船对比表已产出（上表 ①）\n* G5：`artifacts/eexi_closed_loop.json`（本文件即由其生成，判据数字齐备）",
            "unique": true
          },
          "note": "G1–G5 五条判据原文，含 G3 对标项 WITHHELD 的显式披露。"
        },
        {
          "asset_id": "A08",
          "asset_class": "result_block",
          "label": "效率链与碳链分解（三型船逐项）",
          "in_report_section": "③ 计算结果",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_and_char_span_roundtrips",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3144,
            "end_char": 3607,
            "start_line": 65,
            "end_line": 67,
            "quote": "* `kcs_3600teu`：P_E=25276.7 kW → P_D=37608.4 kW；2πnQ=36856.1 kW（η_S=0.98）→ P_D^torque=37608.3 kW；n=115.7 rpm，J=0.632，K_T=0.2323，K_Q=0.03736；CO₂=21743.4 kg/h\n* `jbc_180k`：P_E=9656.0 kW → P_D=17025.1 kW；2πnQ=16684.6 kW（η_S=0.98）→ P_D^torque=17025.1 kW；n=86.0 rpm，J=0.392，K_T=0.1921，K_Q=0.02304；CO₂=9276.2 kg/h\n* `kvlcc2_300k`：P_E=14622.2 kW → P_D=24115.2 kW；2πnQ=23633.2 kW（η_S=0.98）→ P_D^torque=24115.5 kW；n=72.0 rpm，J=0.439，K_T=0.1903，K_Q=0.02381；CO₂=13080.9 kg/h",
            "unique": true
          },
          "note": "P_E→P_D、独立力矩路线 2πnQ、n/J/K_T/K_Q、CO₂ 率；数值仅登记。"
        },
        {
          "asset_id": "A09",
          "asset_class": "table",
          "label": "KCS 公开水池表对标（8 个航速点）",
          "in_report_section": "③ 计算结果 / 实验对标",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_and_char_span_roundtrips",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3642,
            "end_char": 4235,
            "start_line": 71,
            "end_line": 80,
            "quote": "| V [kn] | Holtrop R_T [kN] | 表列 R_T [kN] | 偏差 | 表列 C_t·10³ | 由 C_t 反推 R_T [kN] | 表内不一致 |\n|---|---|---|---|---|---|---|\n| 16.0 | 702.4 | 580.0 | +21.1% | 2.15 | 697.8 | +20.3% |\n| 18.0 | 922.6 | 820.0 | +12.5% | 2.28 | 936.5 | +14.2% |\n| 20.0 | 1208.5 | 1180.0 | +2.4% | 2.52 | 1277.9 | +8.3% |\n| 22.0 | 1571.7 | 1740.0 | -9.7% | 3.05 | 1871.5 | +7.6% |\n| 24.0 | 2047.2 | 2650.0 | -22.7% | 3.80 | 2774.9 | +4.7% |\n| 25.0 | 2358.5 | 3450.0 | -31.6% | 4.50 | 3565.6 | +3.3% |\n| 26.0 | 2707.9 | 4600.0 | -41.1% | 5.60 | 4799.2 | +4.3% |\n| 27.0 | 3059.9 | 6200.0 | -50.6% | 7.20 | 6654.2 | +7.3% |",
            "unique": true
          },
          "note": "审计对象表：Holtrop R_T、表列 R_T、偏差、表列 C_t 与由 C_t 反推 R_T；报告自评该表证据等级 WITHHELD。"
        },
        {
          "asset_id": "A10",
          "asset_class": "evidence_grade_note",
          "label": "水池表证据等级 WITHHELD 结论",
          "in_report_section": "③ 计算结果 / 实验对标",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_and_char_span_roundtrips",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 4237,
            "end_char": 4321,
            "start_line": 82,
            "end_line": 83,
            "quote": "表内 `C_t` 列与 `R_T` 列最大不一致 `20.3%`，故该表证据等级\n**WITHHELD**：只作量级参考，不用于标定、不用于 PASS 判定（见 ⑤）。",
            "unique": true
          },
          "note": "报告声明该表仅作量级参考、不用于标定与 PASS 判定；登记原文，不升级为结论。"
        },
        {
          "asset_id": "A11",
          "asset_class": "table",
          "label": "敏感度表（输入假设传导，非精度声明）",
          "in_report_section": "③ 计算结果 / 敏感度",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_and_char_span_roundtrips",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 4347,
            "end_char": 4995,
            "start_line": 87,
            "end_line": 91,
            "quote": "| 船 | 基线 EEXI | 各情形 ΔEEXI |\n|---|---|---|\n| kcs_3600teu | 35.992 | Cwp-3%:-1.74% / Cwp+3%:+1.92% / lcb-1%Lpp:-0.02% / lcb+1%Lpp:+0.12% / SFOC-5%:-4.85% / SFOC+5%:+4.85% / eta_s=0.96:+2.07% / eta_s=0.99:-1.00% / D/T-20%:+10.93% / D/T+20%:-6.88% |\n| jbc_180k | 3.558 | Cwp-3%:-1.96% / Cwp+3%:+2.27% / lcb-1%Lpp:-0.12% / lcb+1%Lpp:+0.62% / SFOC-5%:-4.80% / SFOC+5%:+4.80% / eta_s=0.96:+2.05% / eta_s=0.99:-0.99% / D/T-20%:+14.25% / D/T+20%:-9.19% |\n| kvlcc2_300k | 2.816 | Cwp-3%:-1.50% / Cwp+3%:+1.54% / lcb-1%Lpp:-0.05% / lcb+1%Lpp:+0.28% / SFOC-5%:-4.82% / SFOC+5%:+4.82% / eta_s=0.96:+2.06% / eta_s=0.99:-1.00% / D/T-20%:+13.34% / D/T+20%:-8.55% |",
            "unique": true
          },
          "note": "10 个情形 ×3 型船的 ΔEEXI 百分比；登记不重算。"
        },
        {
          "asset_id": "A12",
          "asset_class": "figure_reference",
          "label": "图声明 fig1_resistance / fig2_efficiency / fig3_eexi / fig4_gates",
          "in_report_section": "④ 结果图",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "target_path_probed_in_worktree",
            "result": "unresolved",
            "target_probe": {
              "exists_in_worktree": false
            }
          },
          "locator": {
            "method": "char_span",
            "start_char": 5007,
            "end_char": 5321,
            "start_line": 95,
            "end_line": 99,
            "quote": "* `fig1_resistance.png`：三型船 R_T(V)/R_F(V) 曲线 + V_ref（点线）+ KCS 水池表散点；右图为\n  Holtrop vs 表偏差 与 表内 C_t↔R_T 自一致性（±15% 接受带）。\n* `fig2_efficiency.png`：效率链分解 η_H/η_O/η_S/η_total 与 P_E→P_D 功率（柱上标注独立力矩路线 2πnQ）。\n* `fig3_eexi.png`：三型船 EEXI attained vs required 及比值。\n* `fig4_gates.png`：G1 摩擦线偏差（对数坐标，含 3% 门禁线）与 G2 能量残差（含 1% 门禁线）。",
            "unique": true
          },
          "note": "报告以文件名声明 4 张图；平台 record.figures 携带 name+caption 元数据，但 figures/artifacts 路由 404，本工作树亦无 PNG，故字节不可解析。",
          "target": {
            "address_as_written": "fig1_resistance.png",
            "kind": "figure_png",
            "ext_kind": "figure",
            "exists_in_worktree": false,
            "reason": "address belongs to ship-performance-platform (private repo) or is an external baseline; this worktree is TensorKnowledge"
          }
        },
        {
          "asset_id": "A13",
          "asset_class": "data_artifact_reference",
          "label": "产物 JSON：artifacts/eexi_closed_loop.json",
          "in_report_section": "③ 计算结果 / G5",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "target_path_probed_in_worktree",
            "result": "unresolved",
            "target_probe": {
              "exists_in_worktree": false
            }
          },
          "locator": {
            "method": "char_span",
            "start_char": 3062,
            "end_char": 3117,
            "start_line": 61,
            "end_line": 61,
            "quote": "* G5：`artifacts/eexi_closed_loop.json`（本文件即由其生成，判据数字齐备）",
            "unique": true
          },
          "note": "报告称本报告的判据数字由该 JSON 程序化注入（零手抄链上溯）；文件在 ship-performance-platform 私有仓，本工作树不可解析。",
          "target": {
            "address_as_written": "artifacts/eexi_closed_loop.json",
            "kind": "data_json",
            "ext_kind": "data",
            "exists_in_worktree": false,
            "reason": "address belongs to ship-performance-platform (private repo) or is an external baseline; this worktree is TensorKnowledge"
          }
        },
        {
          "asset_id": "A14",
          "asset_class": "data_artifact_reference",
          "label": "产物清单行：artifacts/eexi_closed_loop.json + artifacts/eexi_closed_loop/*.png + 本报告",
          "in_report_section": "审计链",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "target_path_probed_in_worktree",
            "result": "unresolved",
            "target_probe": {
              "exists_in_worktree": null
            }
          },
          "locator": {
            "method": "char_span",
            "start_char": 7864,
            "end_char": 7941,
            "start_line": 149,
            "end_line": 149,
            "quote": "* 产物：`artifacts/eexi_closed_loop.json`、`artifacts/eexi_closed_loop/*.png`、本报告",
            "unique": true
          },
          "note": "审计链的产物行；PNG 通配符无法在本工作树解析出具体文件清单。",
          "target": {
            "address_as_written": "artifacts/eexi_closed_loop/*.png",
            "kind": "figure_glob",
            "ext_kind": "figure",
            "exists_in_worktree": null,
            "reason": "address belongs to ship-performance-platform (private repo) or is an external baseline; this worktree is TensorKnowledge"
          }
        },
        {
          "asset_id": "A15",
          "asset_class": "code_reference",
          "label": "新增模块 backend/modules/eexi_closed_loop/{chain.py,fleet.py,data/reference_ships.json}",
          "in_report_section": "审计链",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "target_path_probed_in_worktree",
            "result": "unresolved",
            "target_probe": {
              "exists_in_worktree": false
            }
          },
          "locator": {
            "method": "char_span",
            "start_char": 7616,
            "end_char": 7702,
            "start_line": 146,
            "end_line": 146,
            "quote": "* 代码：`backend/modules/eexi_closed_loop/{chain.py,fleet.py,data/reference_ships.json}`、",
            "unique": true
          },
          "note": "三件套（纯物理核 chain.py / 批量 fleet.py / 三型船数据 reference_ships.json）均属 ship-performance-platform，本工作树不存在。",
          "target": {
            "address_as_written": "backend/modules/eexi_closed_loop/chain.py",
            "kind": "source_code",
            "ext_kind": "code",
            "exists_in_worktree": false,
            "reason": "address belongs to ship-performance-platform (private repo) or is an external baseline; this worktree is TensorKnowledge"
          }
        },
        {
          "asset_id": "A16",
          "asset_class": "code_reference",
          "label": "API 改动 backend/api/green_shipping.py（新增两路由 + 修 _gn_attained_index）",
          "in_report_section": "审计链",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "target_path_probed_in_worktree",
            "result": "unresolved",
            "target_probe": {
              "exists_in_worktree": false
            }
          },
          "locator": {
            "method": "char_span",
            "start_char": 7703,
            "end_char": 7863,
            "start_line": 147,
            "end_line": 148,
            "quote": "  `backend/api/green_shipping.py`（新增 `/eexi_closed_loop`、`/eexi_closed_loop/reference_fleet`；\n  修 `_gn_attained_index`）、`backend/tests/test_eexi_closed_loop.py`",
            "unique": true
          },
          "note": "含 1852 倍量纲缺陷的修复点 _gn_attained_index；本工作树不含该文件，修复本身无法在此复核。",
          "target": {
            "address_as_written": "backend/api/green_shipping.py",
            "kind": "source_code",
            "ext_kind": "code",
            "exists_in_worktree": false,
            "reason": "address belongs to ship-performance-platform (private repo) or is an external baseline; this worktree is TensorKnowledge"
          }
        },
        {
          "asset_id": "A17",
          "asset_class": "test_reference",
          "label": "回归测试 backend/tests/test_eexi_closed_loop.py（38 例）",
          "in_report_section": "② 怎么做的",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "target_path_probed_in_worktree",
            "result": "unresolved",
            "target_probe": {
              "exists_in_worktree": false
            }
          },
          "locator": {
            "method": "char_span",
            "start_char": 2315,
            "end_char": 2364,
            "start_line": 41,
            "end_line": 41,
            "quote": "   `backend/tests/test_eexi_closed_loop.py` 38 例。",
            "unique": true
          },
          "note": "报告称 38 例 pytest；用例文件不在本工作树，未运行、不置标。",
          "target": {
            "address_as_written": "backend/tests/test_eexi_closed_loop.py",
            "kind": "test_code",
            "ext_kind": "code",
            "exists_in_worktree": false,
            "reason": "address belongs to ship-performance-platform (private repo) or is an external baseline; this worktree is TensorKnowledge"
          }
        },
        {
          "asset_id": "A18",
          "asset_class": "repro_command",
          "label": "复跑命令（run_eexi_closed_loop.py + pytest）",
          "in_report_section": "审计链",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "target_path_probed_in_worktree",
            "result": "unresolved",
            "target_probe": {
              "exists_in_worktree": false
            }
          },
          "locator": {
            "method": "char_span",
            "start_char": 7942,
            "end_char": 8098,
            "start_line": 150,
            "end_line": 151,
            "quote": "* 复现：`python backend/../artifacts/eexi_closed_loop/run_eexi_closed_loop.py`（无随机数、无网络）\n  + `cd backend && python -m pytest tests/test_eexi_closed_loop.py -q`",
            "unique": true
          },
          "note": "报告声明复跑无随机数、无网络；脚本路径在本工作树不存在，未执行。",
          "target": {
            "address_as_written": "artifacts/eexi_closed_loop/run_eexi_closed_loop.py",
            "kind": "source_code",
            "ext_kind": "code",
            "exists_in_worktree": false,
            "reason": "address belongs to ship-performance-platform (private repo) or is an external baseline; this worktree is TensorKnowledge"
          }
        },
        {
          "asset_id": "A19",
          "asset_class": "environment_declaration",
          "label": "运行环境声明（3.11.6 / loongarch64 / glibc2.38）",
          "in_report_section": "审计链",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_and_char_span_roundtrips",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 8099,
            "end_char": 8175,
            "start_line": 152,
            "end_line": 152,
            "quote": "* 环境：3.11.6 on Linux-6.6.52-1.7.lns23.loongarch64-loongarch64-with-glibc2.38",
            "unique": true
          },
          "note": "环境字符串仅登记；本工序运行环境见 source.producer_environment，不做一致性断言。"
        },
        {
          "asset_id": "A20",
          "asset_class": "defect_record_block",
          "label": "1852 倍量纲缺陷记录（发现/机理/修复/回归测试）",
          "in_report_section": "⑤ 注意点",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_and_char_span_roundtrips",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 5348,
            "end_char": 5756,
            "start_line": 103,
            "end_line": 109,
            "quote": "1. **发现并修复一个真实缺陷（1852 倍量纲错）**：`_gn_attained_index` 原实现把分母航程取\n   `V_ref[kn]×1852/3600×3600`（米/小时），得到 gCO₂/(t·**m**)，与响应里声明的\n   `gCO2/(t·nm)` 差 1852 倍，而 required 按 g/(t·nm) 给出 ⇒ **任何船都被判\"合规\"**\n   （VLCC 实测：attained 0.001521、required 2.0710、ratio 0.00073）。\n   已改为海里并加解析回归测试（`TestEexiUnitDefectRegression`）；修复后 attained 2.8160、\n   ratio 1.360，与物理手算逐位一致。此为 m1895 同类缺陷（CII 用 km 当 nm）\n   在 EEXI/EEDI 达到值上的复现，属结构性回归点。",
            "unique": true
          },
          "note": "缺陷叙述块原文（原实现分母取米/小时 → gCO₂/(t·m)，与 required 的 g/(t·nm) 差 1852 倍）；本工序只登记文本位置，不复核修复。"
        },
        {
          "asset_id": "A21",
          "asset_class": "table",
          "label": "⑥ 误差判定表（关键量 vs 基准，逐项是否 <3%）",
          "in_report_section": "⑥ 误差判定",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "quote_is_unique_substring_and_char_span_roundtrips",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 6849,
            "end_char": 7423,
            "start_line": 131,
            "end_line": 138,
            "quote": "| 关键量 | 基准 | 误差 | 判据 | 是否 <3% |\n|---|---|---|---|---|\n| Holtrop Cf @V_ref | ITTC-57/78 摩擦线（0.075/(log₁₀Re−2)²） | 0.0696%（R_T 级） | G1 <3% | **是** |\n| Holtrop R_T @V_ref | Schoenherr 独立摩擦线替换 | 0.0696%（Cf 级） | G1 <3% | **是** |\n| P_D 能量闭合 | 力矩路线 2πnQ/η_S = 推力闭合 T(1−t)=R_T（二分容差 1e-5） | 1.208e-05 | G2 <1% | **是** |\n| gCO₂/(t·nm) 量纲 | 单位代数（kW·g/kWh·C_F/(t·kn)） | 精确一致 | G3 | **是** |\n| EEXI attained | IMO 示例船逐点值 | 不可复核 | G3 对标 | **未判**（WITHHELD，理由：离线无 MEPC 原文） |\n| Holtrop R_T @24 kn | 仓内 KRISO_tank 表 2650 kN | -22.7% | 实验带 ±15% | **否**（且该表自身 C_t↔R_T 不一致 20.3%，基准不可信 → 不作精度声明） |",
            "unique": true
          },
          "note": "6 行判定的原文；其中 EEXI attained vs IMO 示例船为 未判/WITHHELD、Holtrop R_T @24kn 为 否。"
        },
        {
          "asset_id": "A22",
          "asset_class": "limitation_declaration",
          "label": "honest 结论块（声明两项基准不可得：MEPC 原文缺失、水池表自相矛盾）",
          "in_report_section": "⑥ 误差判定",
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "report_declares_target_unavailable",
            "result": "absent",
            "target_probe": {
              "exists_in_worktree": null
            }
          },
          "locator": {
            "method": "char_span",
            "start_char": 7425,
            "end_char": 7606,
            "start_line": 140,
            "end_line": 142,
            "quote": "honest 结论：G1/G2/G3(量纲)/G4/G5 全部按判据通过且可机器复现；**\"与 IMO 示例船 <5%\"这一项未能完成**，\n原因是离线环境无法取得 MEPC.328(76)/350(78) 原文或可核示例船数据，按纪律挂 WITHHELD 而不编造对标值。\n\"对实验 <3%\"亦未达成，且所依据的仓内水池表自相矛盾，故如实记录为\"基准不可用\"。",
            "unique": true
          },
          "note": "报告自我声明：离线环境无法取得 MEPC.328(76)/350(78) 原文或可核示例船数据 → 对标基准缺席（报告所述，非本工序推断）。",
          "target": {
            "address_as_written": null,
            "kind": "external_baseline",
            "ext_kind": "external",
            "exists_in_worktree": null,
            "reason": "address belongs to ship-performance-platform (private repo) or is an external baseline; this worktree is TensorKnowledge"
          }
        }
      ],
      "figures": [
        {
          "name": "fig1_resistance",
          "declared_in_body_as": "fig1_resistance.png",
          "declared_body_lines": [
            95
          ],
          "caption_from_record": "三型船 Holtrop R_T(V) 与 R_F(V)（点线=V_ref）+ KCS 水池表散点；右图：Holtrop vs 表偏差 与 表内 C_t↔R_T 自一致性（±15% 接受带）",
          "has_record_metadata": true,
          "bytes_available": false,
          "byte_probes": [
            {
              "url": "<api>/tensor/reports/9503/figures/fig1_resistance.png",
              "http_status": 404,
              "bytes": 0
            },
            {
              "url": "<api>/tensor/reports/9503/figures/fig1_resistance",
              "http_status": 404,
              "bytes": 0
            },
            {
              "url": "<api>/tensor/reports/9503/artifacts/fig1_resistance.png",
              "http_status": 404,
              "bytes": 0
            }
          ]
        },
        {
          "name": "fig2_efficiency",
          "declared_in_body_as": "fig2_efficiency.png",
          "declared_body_lines": [
            97
          ],
          "caption_from_record": "效率链分解 η_H/η_O/η_S/η_total 与 P_E→P_D 功率对照（柱上标注独立力矩路线 2πnQ）",
          "has_record_metadata": true,
          "bytes_available": false,
          "byte_probes": [
            {
              "url": "<api>/tensor/reports/9503/figures/fig2_efficiency.png",
              "http_status": 404,
              "bytes": 0
            },
            {
              "url": "<api>/tensor/reports/9503/figures/fig2_efficiency",
              "http_status": 404,
              "bytes": 0
            },
            {
              "url": "<api>/tensor/reports/9503/artifacts/fig2_efficiency.png",
              "http_status": 404,
              "bytes": 0
            }
          ]
        },
        {
          "name": "fig3_eexi",
          "declared_in_body_as": "fig3_eexi.png",
          "declared_body_lines": [
            98
          ],
          "caption_from_record": "三型船（集箱 KCS / 散货 JBC / 油轮 KVLCC2）EEXI attained vs required 及比值",
          "has_record_metadata": true,
          "bytes_available": false,
          "byte_probes": [
            {
              "url": "<api>/tensor/reports/9503/figures/fig3_eexi.png",
              "http_status": 404,
              "bytes": 0
            },
            {
              "url": "<api>/tensor/reports/9503/figures/fig3_eexi",
              "http_status": 404,
              "bytes": 0
            },
            {
              "url": "<api>/tensor/reports/9503/artifacts/fig3_eexi.png",
              "http_status": 404,
              "bytes": 0
            }
          ]
        },
        {
          "name": "fig4_gates",
          "declared_in_body_as": "fig4_gates.png",
          "declared_body_lines": [
            99
          ],
          "caption_from_record": "判据复核：G1 摩擦线偏差（3% 门禁线）与 G2 能量/推力闭合残差（1% 门禁线）",
          "has_record_metadata": true,
          "bytes_available": false,
          "byte_probes": [
            {
              "url": "<api>/tensor/reports/9503/figures/fig4_gates.png",
              "http_status": 404,
              "bytes": 0
            },
            {
              "url": "<api>/tensor/reports/9503/figures/fig4_gates",
              "http_status": 404,
              "bytes": 0
            },
            {
              "url": "<api>/tensor/reports/9503/artifacts/fig4_gates.png",
              "http_status": 404,
              "bytes": 0
            }
          ]
        }
      ],
      "claims": [],
      "claims_empty_reason": "contract wp-9503-01: objective.register_assets=true / classify_report_type=false; notes say 'claims 允许为空数组' and constraints.no_forced_claim_generation=true. This package registers source identity (report_id + markdown byte hash + declared attachments/artefacts) only; extraction is a downstream工序. An empty claims array is the complete result, not an omission.",
      "counts": {
        "assets": 22,
        "by_class": {
          "code_reference": 2,
          "criteria_block": 1,
          "data_artifact_reference": 2,
          "defect_record_block": 1,
          "environment_declaration": 1,
          "evidence_grade_note": 1,
          "figure_reference": 1,
          "heading": 1,
          "limitation_declaration": 1,
          "markdown_document": 1,
          "provenance_declaration": 2,
          "repro_command": 1,
          "result_block": 1,
          "table": 5,
          "test_reference": 1
        },
        "by_resolution": {
          "declared_absent": 1,
          "referenced_unresolved": 8,
          "resolved_in_source": 13
        },
        "resolved_in_source": 13,
        "referenced_unresolved": 8,
        "declared_absent": 1,
        "figures_declared_in_record": 4,
        "figures_declared_in_body": 4,
        "figures_with_bytes_available": 0,
        "sections": 7,
        "claims": 0
      },
      "id_integrity": {
        "ids_checked": 22,
        "duplicates": [],
        "unique": true
      },
      "integrity": {
        "quote_uniqueness": {
          "checked": 22,
          "all_unique_or_document": true,
          "rule": "each non-document quote must occur exactly once in the markdown"
        },
        "chars_roundtrip": true,
        "hash_recomputed_locally": "195c350dd486cb556f078b220cb348edf9210d4ac2631319b40658ee73428b5c",
        "hash_matches_contract": true
      },
      "unresolved": [
        {
          "asset_id": "A04",
          "label": "版本与零手抄声明（commit 7017a623 + 生成脚本）",
          "reason": "target_path_probed_in_worktree"
        },
        {
          "asset_id": "A12",
          "label": "图声明 fig1_resistance / fig2_efficiency / fig3_eexi / fig4_gates",
          "reason": "target_path_probed_in_worktree"
        },
        {
          "asset_id": "A13",
          "label": "产物 JSON：artifacts/eexi_closed_loop.json",
          "reason": "target_path_probed_in_worktree"
        },
        {
          "asset_id": "A14",
          "label": "产物清单行：artifacts/eexi_closed_loop.json + artifacts/eexi_closed_loop/*.png + 本报告",
          "reason": "target_path_probed_in_worktree"
        },
        {
          "asset_id": "A15",
          "label": "新增模块 backend/modules/eexi_closed_loop/{chain.py,fleet.py,data/reference_ships.json}",
          "reason": "target_path_probed_in_worktree"
        },
        {
          "asset_id": "A16",
          "label": "API 改动 backend/api/green_shipping.py（新增两路由 + 修 _gn_attained_index）",
          "reason": "target_path_probed_in_worktree"
        },
        {
          "asset_id": "A17",
          "label": "回归测试 backend/tests/test_eexi_closed_loop.py（38 例）",
          "reason": "target_path_probed_in_worktree"
        },
        {
          "asset_id": "A18",
          "label": "复跑命令（run_eexi_closed_loop.py + pytest）",
          "reason": "target_path_probed_in_worktree"
        },
        {
          "asset_id": "A22",
          "label": "honest 结论块（声明两项基准不可得：MEPC 原文缺失、水池表自相矛盾）",
          "reason": "report_declares_target_unavailable"
        }
      ],
      "observations": [
        "markdown 8176 字符 / 11861 UTF-8 字节；与契约 chars=8176 一致，sha256 与契约逐位相同。",
        "报告结构完整：H1 + ①–⑥ 六节 + 审计链，共 7 个二级标题。",
        "4 张图仅以文件名在 ④ 结果图 声明；平台 record.figures 给 name+caption，但 figures/artifacts 路由均 404，本工作树亦无 PNG，故图字节不可解析（不声明图哈希）。",
        "所有 backend/** 与 artifacts/** 地址属 ship-performance-platform 私有仓，本工作树逐条探测 exists_in_worktree=false，登记为 referenced_unresolved。",
        "报告自评两处基准缺席：IMO 示例船逐点值（MEPC 原文离线不可得）与仓内水池表（C_t↔R_T 自不一致 20.3%）——登记为 declared_absent，不代为判定。"
      ]
    }
  },
  "claims": []
}
```
