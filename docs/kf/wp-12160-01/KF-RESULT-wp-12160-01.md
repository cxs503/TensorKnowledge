# KF-RESULT wp-12160-01

工作包 `wp-12160-01` · 工序 `01-asset-registration` · report_id=`12160` ·
lane C · 交付仓 TensorKnowledge（status=draft）

> 本版取代同工作包前版 report `14851`：同一 source_hash，仅将 2 条非契约自查项从 acceptance 表中分出单列（结论未变，仍全 PASS）。


## ① 本工序做了什么

只做“登记源资产”一件事，对 report `12160` 的 markdown 做三件可机器复核的事：

1. **确认源实例与其字节哈希**：从平台取回 `tensor://reports/12160` 的 `markdown` 字段，
   重算 sha256 = `e4e2c2d632af95718d0c43099594c1a41003f59610e86aa14ed82f936998b572`，与工作包契约 `source_hash` 逐字符一致
   （`hash_matches_contract = true`）；字符数
   9351 / UTF-8 字节 13468，与契约 `chars` 一致（`chars_match = true`）。
2. **列出可解析的附件/工件共 32 项**，每项给一个逐字可定位的 locator（char span + 行号 + 唯一性）：
   resolved_in_source 15 / referenced_unresolved 16 /
   declared_absent 1。
3. **不做抽取**：`claims = []`（契约 `objective.register_assets=true`、`no_forced_claim_generation=true`），
   未对报告任何结论做验证或否证——`verified` 由平台门计算，本包不写、也不暗示。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. `GET $TENSOR_API_BASE/tensor/reports/12160`（Bearer=eco_admin 登录 token）取 `markdown`；
   同时取记录元数据（title/scenario_key/tags/figures/status/mission_id）落
   `source_record.json`——报告标题与 scenario 一律来自平台记录，不由我手打。
2. 把 markdown 逐字节存成 `source_markdown.md`，重算 sha256 与契约比对（`integrity.hash_matches_contract`）。
3. 程序化枚举资产：正则抓 `路径` / `dotted 符号` / `调用` / `MEPC.*` 引用 + 结构扫描抓
   `| 表格块` 与内联 JSON 块；每个候选都用 `str.find` 在原文里取 char span、行号与出现次数，
   歧义者按行向两侧扩窗直到全文唯一（`context_expanded_lines` 记录扩了几行，绝不改写原文）。
4. 逐项做**真实解析检查**（不是断言）：路径类 → 在三个有界只读根
   （本 worktree / `ship-performance-platform` 两个本地检出）做 `os.path.exists`；
   符号类 → `grep -rFl --include=*.py`（排除本包自身脚本，防自指假阳性）；
   标准类 → 离线不可得，登记为 unresolved；规则侧系数 → 报告自述离线不可回读，登记为 declared_absent。
5. `scripts/kf_selfcheck_12160.py` 把契约 6 条 acceptance + 2 条自查项逐条机器裁决（分组输出，不混计），
   写 `selfcheck.json`；`pytest tests/test_kf_wp_12160_01.py` 6 条（含 2 条负控：改字节/移位必须 FAIL）。
6. 本 markdown 由 `scripts/kf_emit_report_12160.py` 从上述三个 JSON 渲染，表格与 JSON 块零手抄。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-12160-01/asset_manifest.json` | 登记清单本体：source 哈希/字符数 + 32 项资产（各带 locator/resolution/resolution_check）+ claims=[] + integrity |
| `docs/kf/wp-12160-01/kf_result.json` | 结果信封（kf_result.v1）：package_id/task_type/report_id/provenance/outputs，通过 `schemas/kf_result.v1.schema.json` |
| `docs/kf/wp-12160-01/selfcheck.json` | 8 条机器裁决（6 acceptance + 2 自查），全 PASS；含复跑命令 |
| `docs/kf/wp-12160-01/source_markdown.md` | 报告 markdown 的逐字节副本（sha256=`e4e2c2d632af95718d0c43099594c1a41003f59610e86aa14ed82f936998b572`），使本包可离线复核 |
| `docs/kf/wp-12160-01/source_record.json` | 平台记录元数据快照（不含 markdown），标题/scenario/figures 的唯一出处 |
| `docs/kf/wp-12160-01/asset_manifest.v1.localized.json` | 校验用 schema 本地化副本（仅 `package_id`/`report_id`/`source.uri` 三个 const 换绑，换绑清单写在 `x_localized_consts`） |
| `scripts/kf_register_12160.py` | 登记器（可 `--source-file` 离线复跑） |
| `scripts/kf_selfcheck_12160.py` | 验收自检器（`--live-api` 时额外回平台重算哈希） |
| `scripts/kf_emit_report_12160.py` | 本报告的渲染器 |
| `tests/test_kf_wp_12160_01.py` | 6 条 pytest（4 正 + 2 负控） |
| `contracts/wp-12160-01.yaml` | 工作包契约原文（供哈希与字符数交叉核对） |

## ④ 证据定位表（asset_id → 原文逐字引文；全部可在 `source_markdown.md` 定位）

| id | class | label | 节 | 行 | resolution | 原文引文（逐字，长引文截断处标 …） |
|---|---|---|---|---|---|---|
| A01 | source_instance | `tensor://reports/12160` | (document) | L0–165 | resolved_in_source | "# EEXI attained 闭合链路：Holtrop 阻力 → 推进功率 → 轴系效率 → gCO₂/(t·nm)…" |
| A02 | generator_script | `artifacts/eexi_closed_loop/run_eexi_closed_loop.py` | (preamble) | L4–4 | referenced_unresolved | "artifacts/eexi_closed_loop/run_eexi_closed_loop.py" |
| A03 | data_artifact | `artifacts/eexi_closed_loop.json` | (preamble) | L3–5 | referenced_unresolved | "生成时 HEAD `7017a6235`（提交后可能落后一代）· 生成于 2026-11-10T18:30:44+00…" |
| A04 | figure | `artifacts/eexi_closed_loop/figs/fig1_resistance_bre…` | ④ 图 | L111–111 | referenced_unresolved | "artifacts/eexi_closed_loop/figs/fig1_resistance_breakdown.p…" |
| A05 | figure | `artifacts/eexi_closed_loop/figs/fig2_efficiency_cha…` | ④ 图 | L113–113 | referenced_unresolved | "artifacts/eexi_closed_loop/figs/fig2_efficiency_chain.png" |
| A06 | figure | `artifacts/eexi_closed_loop/figs/fig3_error_budget.p…` | ④ 图 | L115–115 | referenced_unresolved | "artifacts/eexi_closed_loop/figs/fig3_error_budget.png" |
| A07 | figure | `artifacts/eexi_closed_loop/figs/fig4_eexi_levels.png` | ④ 图 | L116–116 | referenced_unresolved | "artifacts/eexi_closed_loop/figs/fig4_eexi_levels.png" |
| A08 | code_module | `physics.holtrop.mennen` | ② 怎么做的（方法 /  | L33–33 | referenced_unresolved | "physics.holtrop.mennen" |
| A09 | code_module | `modules.propeller_bemt` | ② 怎么做的（方法 /  | L34–36 | referenced_unresolved | "P_E    = R_T · V\nη_H    = (1-t)/(1-w)     （Taylor；与 module…" |
| A10 | code_function | `modules.propeller_bemt.solve_n_for_thrust` | ② 怎么做的（方法 /  | L36–36 | referenced_unresolved | "modules.propeller_bemt.solve_n_for_thrust" |
| A11 | code_module | `api.green_shipping` | ② 怎么做的（方法 /  | L37–39 | referenced_unresolved | "P_D    = P_E / (η_H·η_O·η_R·η_S)\nṁ_CO₂  = P_D · SFOC · C_F…" |
| A12 | code_function | `api.green_shipping._gn_attained_index` | ② 怎么做的（方法 /  | L53–53 | referenced_unresolved | "api.green_shipping._gn_attained_index" |
| A13 | code_function | `unit_conformance()` | ② 怎么做的（方法 /  | L54–54 | referenced_unresolved | "unit_conformance()" |
| A14 | test | `tests/test_eexi_closed_loop.py` | ② 怎么做的（方法 /  | L54–54 | referenced_unresolved | "tests/test_eexi_closed_loop.py" |
| A15 | external_standard | `MEPC.328(76)` | ① 案例介绍（物理背景  | L11–11 | referenced_unresolved | "MEPC.328(76)" |
| A16 | external_standard | `MEPC.350(78)` | ① 案例介绍（物理背景  | L11–11 | referenced_unresolved | "MEPC.350(78)" |
| A17 | upstream_commit_claim | `7017a6235` | (preamble) | L3–3 | referenced_unresolved | "7017a6235" |
| A18 | trace_identifier | `p73w3-n02-eexi-maturity` | (preamble) | L2–2 | resolved_in_source | "p73w3-n02-eexi-maturity" |
| A19 | trace_identifier | `m10589` | (preamble) | L2–2 | resolved_in_source | "m10589" |
| A20 | schema_field_key | `ships[*].provenance` | ① 案例介绍（物理背景  | L19–19 | resolved_in_source | "`ships[*].provenance`" |
| A21 | schema_field_key | `sensitivity` | ⑤ 注意点（踩过的坑 / | L136–136 | resolved_in_source | "`sensitivity`" |
| A22 | schema_field_key | `reference_input_mode` | ⑥ 误差判定（关键量 v | L165–165 | resolved_in_source | "`reference_input_mode`" |
| A23 | schema_field_key | `method_band` | ② 怎么做的（方法 /  | L52–52 | resolved_in_source | "`method_band`" |
| A24 | schema_field_key | `total_resistance_kN` | ⑤ 注意点（踩过的坑 / | L127–127 | resolved_in_source | "`total_resistance_kN`" |
| A25 | schema_field_key | `delivered_power_kW` | ⑤ 注意点（踩过的坑 / | L128–128 | resolved_in_source | "`delivered_power_kW`" |
| A26 | rule_coefficient_set | `EEDI/EEXI 参考线+削减率` | ⑤ 注意点（踩过的坑 / | L125–125 | declared_absent | "规则侧系数（参考线/削减率）离线不可回读原文" |
| A27 | embedded_json_block | `判据聚合 verdict JSON（§3.4 末）` | ③ 计算结果 | L107–107 | resolved_in_source | "{"a": {"per_ship": {"kcs_3600teu": "FAIL", "jbc_180k": "WIT…" |
| A28 | embedded_table | `① 案例介绍（物理背景 / 几何 / 参数表） · 表（3 数据行 × 18 列）` | ① 案例介绍（物理背景  | L20–24 | resolved_in_source | "几何先过 Cb·L·B·T 与 ∇ 自洽闸门，JBC 的库值 ∇ 与 Cb·L·B·T 差 2.96% 已按定义式校正…" |
| A29 | embedded_table | `3.1 链路逐段（程序化注入） · 表（3 数据行 × 18 列）` | ③ 计算结果 | L58–62 | resolved_in_source | "### 3.1 链路逐段（程序化注入）\n\n\| 船 \| 船型 \| Lpp [m] \| Cb \| V_ref…" |
| A30 | embedded_table | `3.2 参考数据审计（谁有资格当"试验值"） · 表（9 数据行 × 10 列）` | ③ 计算结果 | L68–68 | resolved_in_source | "\| 船 \| V [kn] \| R_T 参考 [kN] \| P_D 参考 [kW] \| C_W(阻力列) \|…" |
| A31 | embedded_table | `3.3 误差预算（逐段独立测量 + RSS） · 表（3 数据行 × 3 列）` | ③ 计算结果 | L93–93 | resolved_in_source | "\| 船 \| 逐段相对误差 \| 总 RSS \|" |
| A32 | embedded_table | `3.4 判据裁决表 · 表（3 数据行 × 5 列）` | ③ 计算结果 | L101–101 | resolved_in_source | "\| 船 \| (a) 阻力 vs 参考 <5% \| (b) P_D vs 试航 <8% \| (c) IMO 公式…" |

- 唯一性：`all_char_span_quotes_unique = true`；
  31 条 char_span locator 逐条复核 `md[start:end] == quote` 且 `start_line == count('\n',0,start)`。
- 本包**不对**上述任何条目做内容判定：路径类未读取文件内容、符号类未 import 执行、
  标准与规则侧系数离线文本未取得——故全部标 unresolved/absent，无一标 verified。

## ⑤ 注意点与局限

* **本包只登记不解释**：报告里所有结论（如“端到端 <5% 被否证”“1852 倍单位缺陷已修复”）都未被我复核；
  登记为资产 ≠ 认可其真实性。
* **工件不可达**：`artifacts/eexi_closed_loop*.py/.json` 与 4 张图在三个有界只读根下均不存在
  （本 worktree=知识仓、本地 ship-performance-platform 检出只有 backend/、incoming 检出无该目录）
  ⇒ 16 项 referenced_unresolved。这是**范围事实**，不是“报告造假”的判定。
* **`chars` 一致性**：契约 `chars=9351` 与实测字符数一致，UTF-8 字节为 13468（中文 3 字节，勿把字节数当字符数）。
* **schema 本地化**：随仓的 `schemas/asset_manifest.v1.schema.json` 把 `package_id`/`report_id`/`source.uri`
  写死为 wp-448-01，直接套用必失败；本地化副本只换这三个 const 并留痕。**平台侧 schema 若有异，以平台门为准**——
  这是 schema_pass 的已知薄弱点。
* **单次读取**：本包在 2026-11-12 单次读取该报告；报告若被上游改写，`source_hash_matches` 会立即变红（负控测试已证）。
* **无图**：本工序是资产登记/寄存器类任务，不产生场量或对比曲线；图形证据属上游报告（其 §④ 4 张 PNG 已登记为 A04–A07，
  字节不可达故未内嵌）。

## ⑥ 自检：逐条对照 acceptance

契约 acceptance（6 项，与契约逐条对应）：

| acceptance 项 | 结论 | selfcheck.result |
|---|---|---|
| valid_json | ✓ | PASS |
| schema_pass | ✓ | PASS |
| source_locator_resolvable | ✓ | PASS |
| source_hash_matches | ✓ | PASS |
| no_duplicate_ids | ✓ | PASS |
| all_claims_have_evidence_or_explicit_unresolved_status | ✓ | PASS |

额外自查（2 项，不属契约 acceptance，单列以免混淆）：

| 自查项 | 结论 | selfcheck.result |
|---|---|---|
| no_verification_claim_made | ✓ | PASS |
| contract_cross_checks | ✓ | PASS |

- `all_pass = true`（6+2=8 项全 PASS）；
  `not_run = []`（无未执行项）。
- 失败项：**无**。诚实声明两处口径：①`all_claims_have_evidence_or_explicit_unresolved_status`
  因 `claims=[]` 而**空真**成立——它是“没有无据主张”，不是“抽取已做”；②`schema_pass` 依赖上面说的本地化 schema。
- 负控（证明检查会响）：把 `source_markdown.md` 尾部加一个换行 ⇒ `source_hash_matches` FAIL；
  在头部插 7 字节 ⇒ char-span locator 全部错位 ⇒ `source_locator_resolvable` FAIL（pytest 两条负控覆盖）。

## repro_cmd

```bash
cd <TensorKnowledge worktree>
python3 scripts/kf_register_12160.py  --out docs/kf/wp-12160-01            # 或 --source-file <md>
python3 scripts/kf_selfcheck_12160.py --out docs/kf/wp-12160-01 --live-api # 8 条裁决
python3 -m pytest -q tests/test_kf_wp_12160_01.py                          # 6 条（含 2 负控）
python3 scripts/kf_emit_report_12160.py --out docs/kf/wp-12160-01          # 重渲染本报告
```

---

```json
{
  "package_id": "wp-12160-01",
  "task_type": "01-asset-registration",
  "report_id": "12160",
  "provenance": {
    "source_hash": "sha256:e4e2c2d632af95718d0c43099594c1a41003f59610e86aa14ed82f936998b572",
    "source_field": "markdown",
    "producer": "scripts/kf_register_12160.py",
    "notes": "fetched_from=api:http://127.0.0.1:8010/api/v1/tensor/reports/12160; chars=9351; bytes_utf8=13468; contract hash compared in integrity.hash_matches_contract"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-12160-01",
      "task_type": "01-asset-registration",
      "report_id": "12160",
      "source": {
        "uri": "tensor://reports/12160",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "e4e2c2d632af95718d0c43099594c1a41003f59610e86aa14ed82f936998b572",
        "chars": 9351,
        "bytes_utf8": 13468,
        "title": "EEXI attained 端到端闭合链路（Holtrop→P_D→η_S→gCO2/(t·nm)）成熟化：链路全闭合、端到端 <5% 被否证 + 1852 倍单位缺陷修复",
        "scenario_key": "p73w3-n02-eexi-maturity",
        "record_fields_from": "api:http://127.0.0.1:8010/api/v1/tensor/reports/12160 (record metadata, markdown excluded)",
        "record_status": "published",
        "record_mission_id": 10589,
        "record_tags": [
          "EEXI",
          "Holtrop",
          "推进效率",
          "误差传递",
          "绿色航行",
          "缺陷修复",
          "数据审计"
        ],
        "record_figures": [
          {
            "name": "fig1_resistance_breakdown.png",
            "caption": "图1 三型船 Holtrop-Mennen(1984) 总阻力分项与参考点审计（空心圆=过审计，红叉=未过审计不入判据）"
          },
          {
            "name": "fig2_efficiency_chain.png",
            "caption": "图2 推进效率分解 η_H/η_O/η_D 与公开 QPC、公开 w/t 推出的 η_H（黑短线）"
          },
          {
            "name": "fig3_error_budget.png",
            "caption": "图3 逐段相对误差与 RSS 总误差（黑横线），红虚线=5% 目标"
          },
          {
            "name": "fig4_eexi_levels.png",
            "caption": "图4a EEXI attained/参考线/要求值；图4b 单位代数回归闸门（1852 倍缺陷对照）"
          }
        ],
        "fetched_from": "api:http://127.0.0.1:8010/api/v1/tensor/reports/12160",
        "contract_hash": "sha256:e4e2c2d632af95718d0c43099594c1a41003f59610e86aa14ed82f936998b572"
      },
      "counts": {
        "assets": 32,
        "by_class": {
          "source_instance": 1,
          "generator_script": 1,
          "data_artifact": 1,
          "figure": 4,
          "code_module": 3,
          "code_function": 3,
          "test": 1,
          "external_standard": 2,
          "upstream_commit_claim": 1,
          "trace_identifier": 2,
          "schema_field_key": 6,
          "rule_coefficient_set": 1,
          "embedded_json_block": 1,
          "embedded_table": 5
        },
        "by_resolution": {
          "resolved_in_source": 15,
          "referenced_unresolved": 16,
          "declared_absent": 1
        },
        "resolved_in_source": 15,
        "referenced_unresolved": 16,
        "declared_absent": 1
      },
      "assets": [
        {
          "asset_class": "source_instance",
          "label": "tensor://reports/12160",
          "in_report_section": "(document)",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 9351,
            "start_line": 0,
            "end_line": 165,
            "quote": "# EEXI attained 闭合链路：Holtrop 阻力 → 推进功率 → 轴系效率 → gCO₂/(t·nm)\n",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256(markdown utf-8 bytes) recomputed",
            "result": "resolved"
          },
          "note": "报告本体；locator.method=document，char span 覆盖全文，quote 为全文首行（识别用摘录，不等于 span 内容）；字节哈希见 integrity.hash_recomputed_locally，与契约 source_hash 比对见 integrity.hash_matches_contract",
          "asset_id": "A01"
        },
        {
          "asset_class": "generator_script",
          "label": "artifacts/eexi_closed_loop/run_eexi_closed_loop.py",
          "in_report_section": "(preamble)",
          "locator": {
            "method": "char_span",
            "start_char": 209,
            "end_char": 259,
            "start_line": 4,
            "end_line": 4,
            "quote": "artifacts/eexi_closed_loop/run_eexi_closed_loop.py",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists over bounded roots {'/root/tp-agent/work/m15743': False, '/root/ship-performance-platform': False, '/root/ship-performance-platform-incoming/ship-performance-platform': False}",
            "present_in_roots": {
              "/root/tp-agent/work/m15743": false,
              "/root/ship-performance-platform": false,
              "/root/ship-performance-platform-incoming/ship-performance-platform": false
            },
            "probe_roots": [
              "/root/tp-agent/work/m15743",
              "/root/ship-performance-platform",
              "/root/ship-performance-platform-incoming/ship-performance-platform"
            ],
            "result": "unresolved"
          },
          "note": "报告自述的生成脚本（表内数字由它程序化注入）；本工作包不读取、不校验其内容（任务契约：只登记，不抽取）",
          "asset_id": "A02"
        },
        {
          "asset_class": "data_artifact",
          "label": "artifacts/eexi_closed_loop.json",
          "in_report_section": "(preamble)",
          "locator": {
            "method": "char_span",
            "start_char": 136,
            "end_char": 315,
            "start_line": 3,
            "end_line": 5,
            "quote": "生成时 HEAD `7017a6235`（提交后可能落后一代）· 生成于 2026-11-10T18:30:44+00:00 ·\n**本文件由 `artifacts/eexi_closed_loop/run_eexi_closed_loop.py` 从 `artifacts/eexi_closed_loop.json`\n程序化生成，表内所有数字零手抄。**",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists over bounded roots {'/root/tp-agent/work/m15743': False, '/root/ship-performance-platform': False, '/root/ship-performance-platform-incoming/ship-performance-platform': False}",
            "present_in_roots": {
              "/root/tp-agent/work/m15743": false,
              "/root/ship-performance-platform": false,
              "/root/ship-performance-platform-incoming/ship-performance-platform": false
            },
            "probe_roots": [
              "/root/tp-agent/work/m15743",
              "/root/ship-performance-platform",
              "/root/ship-performance-platform-incoming/ship-performance-platform"
            ],
            "result": "unresolved"
          },
          "note": "报告自述的数据工件：几何/工况/逐段误差/审计表/敏感度的唯一来源；本工作包不读取、不校验其内容（任务契约：只登记，不抽取）",
          "asset_id": "A03"
        },
        {
          "asset_class": "figure",
          "label": "artifacts/eexi_closed_loop/figs/fig1_resistance_breakdown.png",
          "in_report_section": "④ 图",
          "locator": {
            "method": "char_span",
            "start_char": 6583,
            "end_char": 6644,
            "start_line": 111,
            "end_line": 111,
            "quote": "artifacts/eexi_closed_loop/figs/fig1_resistance_breakdown.png",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists over bounded roots {'/root/tp-agent/work/m15743': False, '/root/ship-performance-platform': False, '/root/ship-performance-platform-incoming/ship-performance-platform': False}",
            "present_in_roots": {
              "/root/tp-agent/work/m15743": false,
              "/root/ship-performance-platform": false,
              "/root/ship-performance-platform-incoming/ship-performance-platform": false
            },
            "probe_roots": [
              "/root/tp-agent/work/m15743",
              "/root/ship-performance-platform",
              "/root/ship-performance-platform-incoming/ship-performance-platform"
            ],
            "result": "unresolved"
          },
          "note": "图1 阻力分项+参考点审计标记；本工作包不读取、不校验其内容（任务契约：只登记，不抽取）",
          "asset_id": "A04"
        },
        {
          "asset_class": "figure",
          "label": "artifacts/eexi_closed_loop/figs/fig2_efficiency_chain.png",
          "in_report_section": "④ 图",
          "locator": {
            "method": "char_span",
            "start_char": 6703,
            "end_char": 6760,
            "start_line": 113,
            "end_line": 113,
            "quote": "artifacts/eexi_closed_loop/figs/fig2_efficiency_chain.png",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists over bounded roots {'/root/tp-agent/work/m15743': False, '/root/ship-performance-platform': False, '/root/ship-performance-platform-incoming/ship-performance-platform': False}",
            "present_in_roots": {
              "/root/tp-agent/work/m15743": false,
              "/root/ship-performance-platform": false,
              "/root/ship-performance-platform-incoming/ship-performance-platform": false
            },
            "probe_roots": [
              "/root/tp-agent/work/m15743",
              "/root/ship-performance-platform",
              "/root/ship-performance-platform-incoming/ship-performance-platform"
            ],
            "result": "unresolved"
          },
          "note": "图2 推进效率分解 vs 公开 QPC；本工作包不读取、不校验其内容（任务契约：只登记，不抽取）",
          "asset_id": "A05"
        },
        {
          "asset_class": "figure",
          "label": "artifacts/eexi_closed_loop/figs/fig3_error_budget.png",
          "in_report_section": "④ 图",
          "locator": {
            "method": "char_span",
            "start_char": 6820,
            "end_char": 6873,
            "start_line": 115,
            "end_line": 115,
            "quote": "artifacts/eexi_closed_loop/figs/fig3_error_budget.png",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists over bounded roots {'/root/tp-agent/work/m15743': False, '/root/ship-performance-platform': False, '/root/ship-performance-platform-incoming/ship-performance-platform': False}",
            "present_in_roots": {
              "/root/tp-agent/work/m15743": false,
              "/root/ship-performance-platform": false,
              "/root/ship-performance-platform-incoming/ship-performance-platform": false
            },
            "probe_roots": [
              "/root/tp-agent/work/m15743",
              "/root/ship-performance-platform",
              "/root/ship-performance-platform-incoming/ship-performance-platform"
            ],
            "result": "unresolved"
          },
          "note": "图3 逐段误差+RSS vs 5% 目标线；本工作包不读取、不校验其内容（任务契约：只登记，不抽取）",
          "asset_id": "A06"
        },
        {
          "asset_class": "figure",
          "label": "artifacts/eexi_closed_loop/figs/fig4_eexi_levels.png",
          "in_report_section": "④ 图",
          "locator": {
            "method": "char_span",
            "start_char": 6906,
            "end_char": 6958,
            "start_line": 116,
            "end_line": 116,
            "quote": "artifacts/eexi_closed_loop/figs/fig4_eexi_levels.png",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists over bounded roots {'/root/tp-agent/work/m15743': False, '/root/ship-performance-platform': False, '/root/ship-performance-platform-incoming/ship-performance-platform': False}",
            "present_in_roots": {
              "/root/tp-agent/work/m15743": false,
              "/root/ship-performance-platform": false,
              "/root/ship-performance-platform-incoming/ship-performance-platform": false
            },
            "probe_roots": [
              "/root/tp-agent/work/m15743",
              "/root/ship-performance-platform",
              "/root/ship-performance-platform-incoming/ship-performance-platform"
            ],
            "result": "unresolved"
          },
          "note": "图4 EEXI 水平+单位代数回归闸门；本工作包不读取、不校验其内容（任务契约：只登记，不抽取）",
          "asset_id": "A07"
        },
        {
          "asset_class": "code_module",
          "label": "physics.holtrop.mennen",
          "in_report_section": "② 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1668,
            "end_char": 1690,
            "start_line": 33,
            "end_line": 33,
            "quote": "physics.holtrop.mennen",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "grep -rFl --include=*.py --exclude=kf_register_12160.py --exclude=kf_selfcheck_12160.py --exclude=test_kf_wp_12160_01.py 'physics.holtrop.mennen' over worktree code dirs {'tests': 0, 'scripts': 0, 'schemas': 0} (self-reference excluded)",
            "probe_result": {
              "tests": 0,
              "scripts": 0,
              "schemas": 0
            },
            "result": "unresolved"
          },
          "note": "阻力段唯一来源（Holtrop-Mennen 1984 实现）；工作包内未加载/未执行该符号，其行为既未确认也未否证",
          "asset_id": "A08"
        },
        {
          "asset_class": "code_module",
          "label": "modules.propeller_bemt",
          "in_report_section": "② 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1691,
            "end_char": 1847,
            "start_line": 34,
            "end_line": 36,
            "quote": "P_E    = R_T · V\nη_H    = (1-t)/(1-w)     （Taylor；与 modules.propeller_bemt 同源）\nη_O    ← modules.propeller_bemt.solve_n_for_thrust（BEMT 敞水，T(1-t)=R_T 闭合反解 n）",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "grep -rFl --include=*.py --exclude=kf_register_12160.py --exclude=kf_selfcheck_12160.py --exclude=test_kf_wp_12160_01.py 'modules.propeller_bemt' over worktree code dirs {'tests': 0, 'scripts': 0, 'schemas': 0} (self-reference excluded)",
            "probe_result": {
              "tests": 0,
              "scripts": 0,
              "schemas": 0
            },
            "result": "unresolved"
          },
          "note": "敞水/桨模型模块（与 η_H 的 Taylor 式同源）；工作包内未加载/未执行该符号，其行为既未确认也未否证",
          "asset_id": "A09"
        },
        {
          "asset_class": "code_function",
          "label": "modules.propeller_bemt.solve_n_for_thrust",
          "in_report_section": "② 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1779,
            "end_char": 1820,
            "start_line": 36,
            "end_line": 36,
            "quote": "modules.propeller_bemt.solve_n_for_thrust",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "grep -rFl --include=*.py --exclude=kf_register_12160.py --exclude=kf_selfcheck_12160.py --exclude=test_kf_wp_12160_01.py 'modules.propeller_bemt.solve_n_for_thrust' over worktree code dirs {'tests': 0, 'scripts': 0, 'schemas': 0} (self-reference excluded)",
            "probe_result": {
              "tests": 0,
              "scripts": 0,
              "schemas": 0
            },
            "result": "unresolved"
          },
          "note": "T(1-t)=R_T 闭合反解转速 n；工作包内未加载/未执行该符号，其行为既未确认也未否证",
          "asset_id": "A10"
        },
        {
          "asset_class": "code_module",
          "label": "api.green_shipping",
          "in_report_section": "② 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1848,
            "end_char": 2026,
            "start_line": 37,
            "end_line": 39,
            "quote": "P_D    = P_E / (η_H·η_O·η_R·η_S)\nṁ_CO₂  = P_D · SFOC · C_F                                   ← C_F 由 api.green_shipping 化学计量\nEEXI   = ṁ_CO₂ / (Capacity · V_ref)     [gCO₂/(t·nm)]",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "grep -rFl --include=*.py --exclude=kf_register_12160.py --exclude=kf_selfcheck_12160.py --exclude=test_kf_wp_12160_01.py 'api.green_shipping' over worktree code dirs {'tests': 0, 'scripts': 0, 'schemas': 0} (self-reference excluded)",
            "probe_result": {
              "tests": 0,
              "scripts": 0,
              "schemas": 0
            },
            "result": "unresolved"
          },
          "note": "SFOC→CO₂ 化学计量与 EEXI attained 指数所在模块；工作包内未加载/未执行该符号，其行为既未确认也未否证",
          "asset_id": "A11"
        },
        {
          "asset_class": "code_function",
          "label": "api.green_shipping._gn_attained_index",
          "in_report_section": "② 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 2535,
            "end_char": 2572,
            "start_line": 53,
            "end_line": 53,
            "quote": "api.green_shipping._gn_attained_index",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "grep -rFl --include=*.py --exclude=kf_register_12160.py --exclude=kf_selfcheck_12160.py --exclude=test_kf_wp_12160_01.py 'api.green_shipping._gn_attained_index' over worktree code dirs {'tests': 0, 'scripts': 0, 'schemas': 0} (self-reference excluded)",
            "probe_result": {
              "tests": 0,
              "scripts": 0,
              "schemas": 0
            },
            "result": "unresolved"
          },
          "note": "1852 倍单位缺陷的宿主函数（报告称已修复）；工作包内未加载/未执行该符号，其行为既未确认也未否证",
          "asset_id": "A12"
        },
        {
          "asset_class": "code_function",
          "label": "unit_conformance()",
          "in_report_section": "② 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 2624,
            "end_char": 2642,
            "start_line": 54,
            "end_line": 54,
            "quote": "unit_conformance()",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "grep -rFl --include=*.py --exclude=kf_register_12160.py --exclude=kf_selfcheck_12160.py --exclude=test_kf_wp_12160_01.py 'unit_conformance()' over worktree code dirs {'tests': 0, 'scripts': 0, 'schemas': 0} (self-reference excluded)",
            "probe_result": {
              "tests": 0,
              "scripts": 0,
              "schemas": 0
            },
            "result": "unresolved"
          },
          "note": "单位一致性闸门（缺陷双侧锁定之一）；工作包内未加载/未执行该符号，其行为既未确认也未否证",
          "asset_id": "A13"
        },
        {
          "asset_class": "test",
          "label": "tests/test_eexi_closed_loop.py",
          "in_report_section": "② 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 2647,
            "end_char": 2677,
            "start_line": 54,
            "end_line": 54,
            "quote": "tests/test_eexi_closed_loop.py",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists over bounded roots {'/root/tp-agent/work/m15743': False, '/root/ship-performance-platform': False, '/root/ship-performance-platform-incoming/ship-performance-platform': False}",
            "probe_result": {
              "/root/tp-agent/work/m15743": false,
              "/root/ship-performance-platform": false,
              "/root/ship-performance-platform-incoming/ship-performance-platform": false
            },
            "result": "unresolved"
          },
          "note": "缺陷回归测试（双侧锁定的另一侧）；工作包内未加载/未执行该符号，其行为既未确认也未否证",
          "asset_id": "A14"
        },
        {
          "asset_class": "external_standard",
          "label": "MEPC.328(76)",
          "in_report_section": "① 案例介绍（物理背景 / 几何 / 参数表）",
          "locator": {
            "method": "char_span",
            "start_char": 355,
            "end_char": 367,
            "start_line": 11,
            "end_line": 11,
            "quote": "MEPC.328(76)",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "standard document not part of the markdown / not available offline",
            "result": "unresolved"
          },
          "note": "EEXI 规则母文件（报告引用计算法）；离线不可回读原文，本包不据此做任何合规性陈述",
          "asset_id": "A15"
        },
        {
          "asset_class": "external_standard",
          "label": "MEPC.350(78)",
          "in_report_section": "① 案例介绍（物理背景 / 几何 / 参数表）",
          "locator": {
            "method": "char_span",
            "start_char": 371,
            "end_char": 383,
            "start_line": 11,
            "end_line": 11,
            "quote": "MEPC.350(78)",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "standard document not part of the markdown / not available offline",
            "result": "unresolved"
          },
          "note": "EEXI 计算方法修正案；离线不可回读原文，本包不据此做任何合规性陈述",
          "asset_id": "A16"
        },
        {
          "asset_class": "upstream_commit_claim",
          "label": "7017a6235",
          "in_report_section": "(preamble)",
          "locator": {
            "method": "char_span",
            "start_char": 146,
            "end_char": 155,
            "start_line": 3,
            "end_line": 3,
            "quote": "7017a6235",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "git cat-file in this worktree (TensorKnowledge) cannot prove a ship-performance-platform commit",
            "result": "unresolved"
          },
          "note": "报告声明的生成时上游 HEAD（ship-performance-platform），并自注「提交后可能落后一代」；本包无法验证该提交存在性或其内容，仅登记为声明",
          "asset_id": "A17"
        },
        {
          "asset_class": "trace_identifier",
          "label": "p73w3-n02-eexi-maturity",
          "in_report_section": "(preamble)",
          "locator": {
            "method": "char_span",
            "start_char": 65,
            "end_char": 88,
            "start_line": 2,
            "end_line": 2,
            "quote": "p73w3-n02-eexi-maturity",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "identifier declared inside the source",
            "result": "resolved"
          },
          "note": "战役节点 id，与契约 scenario_key 一致",
          "asset_id": "A18"
        },
        {
          "asset_class": "trace_identifier",
          "label": "m10589",
          "in_report_section": "(preamble)",
          "locator": {
            "method": "char_span",
            "start_char": 96,
            "end_char": 102,
            "start_line": 2,
            "end_line": 2,
            "quote": "m10589",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "identifier declared inside the source",
            "result": "resolved"
          },
          "note": "报告所属任务 id（与工作包 mission_id=15743 不同：本包是后者的产线工序）",
          "asset_id": "A19"
        },
        {
          "asset_class": "schema_field_key",
          "label": "ships[*].provenance",
          "in_report_section": "① 案例介绍（物理背景 / 几何 / 参数表）",
          "locator": {
            "method": "char_span",
            "start_char": 749,
            "end_char": 770,
            "start_line": 19,
            "end_line": 19,
            "quote": "`ships[*].provenance`",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "field key appears verbatim in markdown",
            "result": "resolved"
          },
          "note": "几何/工况逐字段出处（上游 JSON 的 provenance 数组）；键名存在于原文，键的取值语义需上游 JSON 才能核对，本包不解释",
          "asset_id": "A20"
        },
        {
          "asset_class": "schema_field_key",
          "label": "sensitivity",
          "in_report_section": "⑤ 注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 7845,
            "end_char": 7858,
            "start_line": 136,
            "end_line": 136,
            "quote": "`sensitivity`",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "field key appears verbatim in markdown",
            "result": "resolved"
          },
          "note": "容量/SFOC 一次齐次敏感度；键名存在于原文，键的取值语义需上游 JSON 才能核对，本包不解释",
          "asset_id": "A21"
        },
        {
          "asset_class": "schema_field_key",
          "label": "reference_input_mode",
          "in_report_section": "⑥ 误差判定（关键量 vs 基准，逐项显式回答\"是否<5%\"）",
          "locator": {
            "method": "char_span",
            "start_char": 9305,
            "end_char": 9327,
            "start_line": 165,
            "end_line": 165,
            "quote": "`reference_input_mode`",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "field key appears verbatim in markdown",
            "result": "resolved"
          },
          "note": "阻力改为试验/CFD 输入模式下的残差开关；键名存在于原文，键的取值语义需上游 JSON 才能核对，本包不解释",
          "asset_id": "A22"
        },
        {
          "asset_class": "schema_field_key",
          "label": "method_band",
          "in_report_section": "② 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 2485,
            "end_char": 2498,
            "start_line": 52,
            "end_line": 52,
            "quote": "`method_band`",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "field key appears verbatim in markdown",
            "result": "resolved"
          },
          "note": "误差预算里「无实测则用文献带宽」的显式标签；键名存在于原文，键的取值语义需上游 JSON 才能核对，本包不解释",
          "asset_id": "A23"
        },
        {
          "asset_class": "schema_field_key",
          "label": "total_resistance_kN",
          "in_report_section": "⑤ 注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 7394,
            "end_char": 7415,
            "start_line": 127,
            "end_line": 127,
            "quote": "`total_resistance_kN`",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "field key appears verbatim in markdown",
            "result": "resolved"
          },
          "note": "标模库阻力列字段名；键名存在于原文，键的取值语义需上游 JSON 才能核对，本包不解释",
          "asset_id": "A24"
        },
        {
          "asset_class": "schema_field_key",
          "label": "delivered_power_kW",
          "in_report_section": "⑤ 注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 7420,
            "end_char": 7440,
            "start_line": 128,
            "end_line": 128,
            "quote": "`delivered_power_kW`",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "field key appears verbatim in markdown",
            "result": "resolved"
          },
          "note": "标模库自航功率列字段名；键名存在于原文，键的取值语义需上游 JSON 才能核对，本包不解释",
          "asset_id": "A25"
        },
        {
          "asset_class": "rule_coefficient_set",
          "label": "EEDI/EEXI 参考线+削减率",
          "in_report_section": "⑤ 注意点（踩过的坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 7312,
            "end_char": 7334,
            "start_line": 125,
            "end_line": 125,
            "quote": "规则侧系数（参考线/削减率）离线不可回读原文",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "report explicitly declares offline unavailability",
            "result": "absent"
          },
          "note": "报告自述该组系数离线不可回读，证据等级 WITHHELD；本包沿用该声明，不补齐、不猜测",
          "asset_id": "A26"
        },
        {
          "asset_class": "embedded_json_block",
          "label": "判据聚合 verdict JSON（§3.4 末）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 6064,
            "end_char": 6568,
            "start_line": 107,
            "end_line": 107,
            "quote": "{\"a\": {\"per_ship\": {\"kcs_3600teu\": \"FAIL\", \"jbc_180k\": \"WITHHELD\", \"kvlcc1_300k\": \"FAIL\"}, \"all_pass\": false, \"any_fail\": true}, \"b\": {\"per_ship\": {\"kcs_3600teu\": \"FAIL\", \"jbc_180k\": \"WITHHELD\", \"kvlcc1_300k\": \"PASS\"}, \"all_pass\": false, \"any_fail\": true}, \"c\": {\"per_ship\": {\"kcs_3600teu\": \"PASS\", \"jbc_180k\": \"PASS\", \"kvlcc1_300k\": \"PASS\"}, \"all_pass\": true, \"any_fail\": false}, \"d\": {\"per_ship\": {\"kcs_3600teu\": \"FAIL\", \"jbc_180k\": \"FAIL\", \"kvlcc1_300k\": \"FAIL\"}, \"all_pass\": false, \"any_fail\": true}}",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "json.loads(quote) succeeded and keys == {a,b,c,d}",
            "result": "resolved"
          },
          "note": "可机读的裁决聚合块；本包只登记其可解析性，不重算也不改写其裁决",
          "asset_id": "A27"
        },
        {
          "asset_class": "embedded_table",
          "label": "① 案例介绍（物理背景 / 几何 / 参数表） · 表（3 数据行 × 18 列）",
          "in_report_section": "① 案例介绍（物理背景 / 几何 / 参数表）",
          "locator": {
            "method": "char_span",
            "start_char": 772,
            "end_char": 1233,
            "start_line": 20,
            "end_line": 24,
            "quote": "几何先过 Cb·L·B·T 与 ∇ 自洽闸门，JBC 的库值 ∇ 与 Cb·L·B·T 差 2.96% 已按定义式校正并登记）：\n\n| 船 | 船型 | Lpp [m] | Cb | V_ref [kn] | Fn | R_T [kN] | P_E [kW] | P_D [kW] | η_H | η_O | η_D | rpm | ṁ_CO₂ [kg/h] | EEXI att | 参考线 | required | att/req |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n| kcs_3600teu | container_ship | 230.0 | 0.6509 | 24.0 | 0.2600 | 1999.8 | 24691 | 34795 | 1.0966 | 0.6473 | 0.7096 | 95.5 | 19483 | 32.215 | 22.720 | 18.176 | 1.772 |",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 2
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "table block located by header row; pipe-row count with header+separator excluded",
            "result": "resolved"
          },
          "note": "父标题='① 案例介绍（物理背景 / 几何 / 参数表）'；| 行 5 个 ⇒ 3 数据行，18 列。本包只登记可解析性，不复述表内数字",
          "table_rows": 3,
          "parent_heading": "① 案例介绍（物理背景 / 几何 / 参数表）",
          "asset_id": "A28"
        },
        {
          "asset_class": "embedded_table",
          "label": "3.1 链路逐段（程序化注入） · 表（3 数据行 × 18 列）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 2697,
            "end_char": 3113,
            "start_line": 58,
            "end_line": 62,
            "quote": "### 3.1 链路逐段（程序化注入）\n\n| 船 | 船型 | Lpp [m] | Cb | V_ref [kn] | Fn | R_T [kN] | P_E [kW] | P_D [kW] | η_H | η_O | η_D | rpm | ṁ_CO₂ [kg/h] | EEXI att | 参考线 | required | att/req |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n| kcs_3600teu | container_ship | 230.0 | 0.6509 | 24.0 | 0.2600 | 1999.8 | 24691 | 34795 | 1.0966 | 0.6473 | 0.7096 | 95.5 | 19483 | 32.215 | 22.720 | 18.176 | 1.772 |",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 2
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "table block located by header row; pipe-row count with header+separator excluded",
            "result": "resolved"
          },
          "note": "父标题='3.1 链路逐段（程序化注入）'；| 行 5 个 ⇒ 3 数据行，18 列。本包只登记可解析性，不复述表内数字",
          "table_rows": 3,
          "parent_heading": "3.1 链路逐段（程序化注入）",
          "asset_id": "A29"
        },
        {
          "asset_class": "embedded_table",
          "label": "3.2 参考数据审计（谁有资格当\"试验值\"） · 表（9 数据行 × 10 列）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 3459,
            "end_char": 3561,
            "start_line": 68,
            "end_line": 68,
            "quote": "| 船 | V [kn] | R_T 参考 [kN] | P_D 参考 [kW] | C_W(阻力列) | C_W(功率列反演) | 反演 QPC | R1 波阻>0 | R4 量级 | R5 功率列 |",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "table block located by header row; pipe-row count with header+separator excluded",
            "result": "resolved"
          },
          "note": "父标题='3.2 参考数据审计（谁有资格当\"试验值\"）'；| 行 11 个 ⇒ 9 数据行，10 列。本包只登记可解析性，不复述表内数字",
          "table_rows": 9,
          "parent_heading": "3.2 参考数据审计（谁有资格当\"试验值\"）",
          "asset_id": "A30"
        },
        {
          "asset_class": "embedded_table",
          "label": "3.3 误差预算（逐段独立测量 + RSS） · 表（3 数据行 × 3 列）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 4998,
            "end_char": 5020,
            "start_line": 93,
            "end_line": 93,
            "quote": "| 船 | 逐段相对误差 | 总 RSS |",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "table block located by header row; pipe-row count with header+separator excluded",
            "result": "resolved"
          },
          "note": "父标题='3.3 误差预算（逐段独立测量 + RSS）'；| 行 5 个 ⇒ 3 数据行，3 列。本包只登记可解析性，不复述表内数字",
          "table_rows": 3,
          "parent_heading": "3.3 误差预算（逐段独立测量 + RSS）",
          "asset_id": "A31"
        },
        {
          "asset_class": "embedded_table",
          "label": "3.4 判据裁决表 · 表（3 数据行 × 5 列）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 5688,
            "end_char": 5770,
            "start_line": 101,
            "end_line": 101,
            "quote": "| 船 | (a) 阻力 vs 参考 <5% | (b) P_D vs 试航 <8% | (c) IMO 公式一致性 <5% | (d) 总误差 RSS <5% |",
            "unique": true,
            "occurrences_in_source": 1,
            "context_expanded_lines": 0
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "table block located by header row; pipe-row count with header+separator excluded",
            "result": "resolved"
          },
          "note": "父标题='3.4 判据裁决表'；| 行 5 个 ⇒ 3 数据行，5 列。本包只登记可解析性，不复述表内数字",
          "table_rows": 3,
          "parent_heading": "3.4 判据裁决表",
          "asset_id": "A32"
        }
      ],
      "claims": [],
      "integrity": {
        "quote_uniqueness": {
          "all_char_span_quotes_unique": true,
          "non_unique_labels": []
        },
        "hash_recomputed_locally": "e4e2c2d632af95718d0c43099594c1a41003f59610e86aa14ed82f936998b572",
        "hash_matches_contract": true,
        "no_duplicate_ids": true,
        "duplicate_ids": [],
        "contract_cross_checks": {
          "chars_recomputed": 9351,
          "chars_in_contract": "9351",
          "chars_match": true,
          "report_id_match": true,
          "scenario_key_match": true,
          "source_uri_match": true,
          "source_field_match": true
        }
      },
      "claims_policy": "claims=[] by contract (objective.register_assets=true, no extraction, no forced claim generation); no statement of the report is verified or refuted here — verification is computed by the platform gate."
    }
  },
  "claims": []
}
```
