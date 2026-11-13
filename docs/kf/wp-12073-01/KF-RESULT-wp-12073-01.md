# KF-RESULT wp-12073-01

- package_id: `wp-12073-01` ｜ task_type: `01-asset-registration` ｜ lane: C ｜ status: draft
- report_id: `12073` ｜ scenario_key: `cii_tracking_realtime` ｜ source: `tensor://reports/12073` (markdown)
- 源标题：实时 CII 轨迹追踪与纠偏航行优化（p161w2-arb-n01 / KVLCC2 闭环）

## ① 本工序做了什么

按 01-asset-registration 契约（「登记源资产：确认 report_id 与其 markdown 的字节哈希，列出可解析的附件/工件，
不做抽取。claims 允许为空数组。」）登记报告 12073 的源资产与随附工件。结果共 **32 个资产**
（resolved_in_source=23，referenced_unresolved=9，
declared_absent=0），其中 5 个图件取回了
png 字节并本地重算 sha256。本工序**不做知识抽取**（claims=[]，契约明确允许），**不判定报告类型**，
**未标注任何 verified**（verification 由平台门计算），**未读写任何其它 report_id**。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. `GET http://127.0.0.1:8010/api/v1/tensor/reports/12073`（Bearer=agent 用户）取 `markdown` 字段与记录元数据；只读该 id。
2. 对 markdown 按 UTF-8 原样编码重算 sha256，与契约 `sha256:362fbe90ba196e81f94aa4f6dd9d74bc5f69c729e7eb9f99a125fb9415bea850` 及
   `chars=3446` 比对：实测 chars=3446、
   bytes_utf8=5799、sha256 一致（见 ④ 表）。
3. `GET /tensor/reports/12073/figures/<name>` 逐件取回 ④ 段列出的 5 张 png，落盘并各自重算 sha256。
4. 每个工件用逐字子串定位首次出现处，计算 char 区间与起止行号（`char_span` 法），并做
   `markdown.count(quote)` 唯一性检查（31/31 唯一；非唯一项全列在
   `manifest.integrity.quote_uniqueness.non_unique`）。
5. 引用型工件（仓内模块 / 规则文件号）只登记引用位置：在工作树内 `os.path.exists` 确认，不存在即置
   `referenced_unresolved`，**不打开外部仓、不声称其内容**。
6. 产物落 `docs/kf/wp-12073-01/`：`asset_manifest.json`、`kf_result.json`（kf_result.v1 信封）、
   `verification.json`、`KF-RESULT-wp-12073-01.md`、`fig_asset_inventory.png`、`source/`（快照 + 图件字节）。
7. 关键设置：哈希前不做任何文本规范化（不 strip / 不 normalize）；哈希不一致即中止构建
   （`SystemExit`），不修补漂移字节；不复用其它报告的旧快照。

一键复跑（在工作树根执行；`--publish` 才会上报，前两步纯本地可验）：

```bash
python3 scripts/kf_wp12073_01_asset_manifest.py --fetch --build --verify
python3 scripts/kf_wp12073_01_asset_manifest.py --verify     # 只复核已提交产物
python3 scripts/kf_wp12073_01_asset_manifest.py --publish    # 上报 KF-RESULT 报告
```

工具链：Python 3.10 + 标准库（urllib / hashlib / json）+ `jsonschema`（结构门）+ matplotlib（清单图）。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-12073-01/asset_manifest.json` | 32 个资产的登记清单：类别、char 区间 / 行号、逐字引文、resolution、字节哈希 |
| `docs/kf/wp-12073-01/kf_result.json` | kf_result.v1 信封；`outputs["asset_manifest.json"]` 内嵌 manifest；`provenance.source_hash` 与契约一致 |
| `docs/kf/wp-12073-01/verification.json` | 逐条 acceptance 自检结果（机器生成，含实测值与失败明细） |
| `docs/kf/wp-12073-01/source/report_12073.md` | 源 markdown 快照（sha256 锚定，可离线复算） |
| `docs/kf/wp-12073-01/source/figures/*.png` | 5 张图件字节（自报告图件端点取回，逐一 sha256） |
| `docs/kf/wp-12073-01/fig_asset_inventory.png` | 资产类别 × resolution 的清单图（登记统计，非领域结果） |
| `docs/kf/wp-12073-01/asset_manifest.schema.json` | 本包 manifest 形状钉死（package_id / report_id 为 const），使 schema_pass 可复现 |

## ④ 证据定位表（claim / 字段 → 原文引文片段）

图件 / 表格 / 几何（char 区间为 markdown 字符偏移，quote 为该区间逐字原文）：

| id | 工件 | resolution | char 区间 | 原文引文（截断） |
|---|---|---|---|---|
| A02 | 图件 fig1_cumulative_cii_band.png | resolved_in_source | 2302–2330 | `fig1_cumulative_cii_band.png` |
| A03 | 图件 fig2_projection_deviation.png | resolved_in_source | 2356–2385 | `fig2_projection_deviation.png` |
| A04 | 图件 fig3_speed_and_disturbance.png | resolved_in_source | 2406–2436 | `fig3_speed_and_disturbance.png` |
| A05 | 图件 fig4_root_cause.png | resolved_in_source | 2451–2470 | `fig4_root_cause.png` |
| A06 | 图件 fig5_correction_sensitivity.png | resolved_in_source | 2481–2512 | `fig5_correction_sensitivity.png` |
| A13 | 判据表表头（C1–C5：量 / 数值 / 阈值 / 结论） | resolved_in_source | 1206–1231 | `\| 判据 \| 量 \| 数值 \| 阈值 \| 结论 \|` |
| A14 | 误差判定表表头（关键量 / 基准 / 误差 / <3%?） | resolved_in_source | 3028–3052 | `\| 关键量 \| 基准 \| 误差 \| <3%? \|` |
| A15 | KVLCC2 主尺度串（L_pp / B / T / Cb / Δ / dwt） | resolved_in_source | 85–155 | `L_pp 320 m / B 58 m / T 20.8 m / Cb 0.8098 / Δ 3` |

引用型工件（引文逐字，目标在包外 → unresolved）：

| id | 工件 | 原文引文 | resolution |
|---|---|---|---|
| A16 | 母型几何文件路径 | `backend/data/geometry/ships/KVLCC2_Hull.stl` | referenced_unresolved |
| A17 | 实时 CII 内核模块 | `realtime.py` | referenced_unresolved |
| A18 | 目标轨迹 / 偏差带模块 | `target.py` | referenced_unresolved |
| A19 | 预警与根因模块 | `alert.py` | referenced_unresolved |
| A20 | 纠偏优化模块 | `correction.py` | referenced_unresolved |
| A21 | 闭环仿真模块 | `simulate.py` | referenced_unresolved |
| A22 | 仓内独立实现（交叉校验基准） | `C1 与仓内独立实现（mepc.attained_cii）` | referenced_unresolved |
| A23 | 螺旋桨定律 + 附加阻力（瞬时功率） | `P = c_p·V³·(1+γ)` | resolved_in_source |
| A24 | 单位航程 CO2 排放 φ | `φ = (P·SFOC + P_aux·SFOC_aux)/V` | resolved_in_source |
| A25 | 目标质量 M_allowed(t) | `M_allowed(t)=CII_target·Capacity·D(t)` | resolved_in_source |
| A26 | λ-KKT 解析解（逐时段最优航速） | `V_i=((a_i+μ)/(2k_i))^{1/3}` | resolved_in_source |
| A27 | CII 折减系数 / 参考线规则（两件规则同处引用） | `MEPC.353(78)/338(76)` | referenced_unresolved |
| A28 | 燃料碳因子 CF 公布值来源 | `MEPC.364(79)` | referenced_unresolved |
| A29 | ETA 受限模式标签 | `mode="eta_limited"` | resolved_in_source |
| A30 | 航速受限模式标签 | `speed_limited` | resolved_in_source |
| A31 | 规则外推标记 | `z_extrapolated` | resolved_in_source |
| A32 | 方向性建议字段 | `recommendations` | resolved_in_source |

源哈希（本工序的核心断言，值均为实测）：

| 项 | 契约 | 实测 | 一致 |
|---|---|---|---|
| sha256(markdown utf-8) | `sha256:362fbe90ba196e81f94aa4f6dd9d74bc5f69c729e7eb9f99a125fb9415bea850` | `sha256:362fbe90ba196e81f94aa4f6dd9d74bc5f69c729e7eb9f99a125fb9415bea850` | 是 |
| chars | 3446 | 3446 | 是 |
| bytes_utf8 | — | 5799 | — |

图件哈希（自报告图件端点取回的 png 字节）：

| 图件 | bytes | sha256 |
|---|---|---|
| `fig1_cumulative_cii_band.png` | 61079 | `sha256:3e6edcded54851aa3cc6dd0c8b74680afc0519e75b08ae210f18b8027ada30e1` |
| `fig2_projection_deviation.png` | 83655 | `sha256:2d559898ded6eda4a541a916544ef47702bac8e7a25c7724140fb225e67d715c` |
| `fig3_speed_and_disturbance.png` | 59543 | `sha256:b5ff23fcac85030f75e952fc6e04347b32c4cdcd409d870a8f747a57ea72cf80` |
| `fig4_root_cause.png` | 32435 | `sha256:b54d83ab73784a70db0638881ffc3d7d87a9750a41d34130e57a07d4c8769401` |
| `fig5_correction_sensitivity.png` | 66230 | `sha256:f17685826598cdd7da4785f2e0f2b85a9890982825167d3c5f5cbc673db15e99` |

## ⑤ 注意点与局限

1. **claims=[] 是完整结果**：本包 objective 只有 asset registration，抽取留给下游工序；不造知识对象，
   避免为填指标而生成无据 claim。
2. **图件哈希的边界**：png 字节来自报告图件端点 `/tensor/reports/12073/figures/<name>`，与生成该图的
   进程无字节级传承关系。本单只声称「该端点在本次取回时给出这些字节、哈希如此」，不声称图是某次仿真的
   原始输出，也不对图中数值作任何判定。
3. **代码 / 模块引用一律 unresolved**：`realtime.py`、`target.py`、`alert.py`、`correction.py`、
   `simulate.py`、`backend/modules/cii_tracking`、`backend/data/geometry/ships/KVLCC2_Hull.stl` 属于
   ship-performance-platform，不在 TensorKnowledge 检出内 → 不打开外部仓、不声称其内容与报告一致。
4. **规则文件号 unresolved**：MEPC.353(78) / 338(76) / 364(79) 原文离线不可回读，仅登记引用位置；
   报告自身已对规则系数层判 WITHHELD，本单不越权升级其证据等级。
5. **唯一性不满分时如实记录**：`char_span` 引文中非唯一项列入
   `integrity.quote_uniqueness.non_unique`（本次 0 项），定位取首次出现位置，
   不做「看似唯一」的粉饰。
6. **未做（明确声明）**：报告类型分类、claim 抽取、任何数值复算、任何 verified 标注——均不在本包范围；
   本单不产生领域结论，也不对报告结论的真伪表态。
7. **图件缺失情况**：报告记录 figures[] 列 5 张图且端点可取回字节（见 ④ 表）；若某张取回失败，manifest
   会把它降为 `referenced_unresolved` 并注明原因。

## ⑥ 自检：逐条对照 acceptance

| acceptance | 判据 | 结果（`verification.json` 机器结论） |
|---|---|---|
| valid_json | manifest 与信封均可 `json.load` | ✔ pass |
| schema_pass | 信封过 `schemas/kf_result.v1.schema.json`；manifest 过本包 `asset_manifest.schema.json` | ✔ pass |
| source_locator_resolvable | 每个 locator 的 quote 逐字命中且 `md[start:end]==quote`，起止行号自洽 | ✔ pass |
| source_hash_matches | 本地重算 sha256 == 契约 source_hash（且 chars 一致） | ✔ pass |
| no_duplicate_ids | asset_id 唯一 | ✔ pass |
| all_claims_have_evidence_or_explicit_unresolved_status | claims=[] → 空真（0 条 claim）；若存在 claim 必带 evidence 或显式 status | ✔ pass |

`not_run` 表示该项未执行，**不视为通过**；失败项如实列出，不做粉饰。

## ⑦ 报告纪律六要素对照（本单为登记工序，无领域计算）

| 六要素 | 本单落点 | 说明 |
|---|---|---|
| ① 案例介绍 | ④ 表 A15「KVLCC2 主尺度串」+ §① | 只登记主尺度引文位置，不重述几何、不校验 Cb/L/B（不在本包范围） |
| ② 怎么做的 | ② 七步 + 工具链 | 取源 → 重算哈希 → 取图件字节 → 逐字定位 → 引用型工件定级 → 落产物 → 自检 |
| ③ 计算结果 | ①/④ 的计数与哈希表 | 32 个资产、23 resolved / 9 unresolved、5 张图件字节哈希（均为程序化注入，非手抄） |
| ④ 结果图 | `fig_asset_inventory.png`（随报告内嵌） | 资产类别 × resolution 的清单统计图；**非**场量云图，因本工序不产生物理场（如实声明） |
| ⑤ 注意点 | ⑤ 第 1–7 条 | 含 claims=[] 的正当性、图件哈希边界、外部仓与规则原文不可达 |
| ⑥ 误差判定 | 本表下方 | 见下 |

**误差判定（是否 <3%）**：本工序不重算任何领域量（CII、航速、排放、阻力等一概未触及），
因此**没有可对基准的物理误差**，不声称任何 <3%。唯一可判的定量断言是字节级同一性：

| 关键量 | 基准 | 误差 | <3%? |
|---|---|---|---|
| sha256(markdown utf-8) | 契约 `sha256:362fbe90ba19…` | 0（逐位相等，非百分比） | 不适用（等式判定） |
| chars | 契约 3446 | 0 字符 | 不适用（等式判定） |
| 图件 sha256（5 张） | 本次自报告图件端点取回并重算 | 0（逐位相等） | 不适用（等式判定） |

**honest 声明**：上面的「不适用」不是回避——领域精度判定（<3%）需要报告内的物理量与独立基准，
而本包按契约**不做抽取、不做复算**；把这类判定留给下游工序与平台门，比在此处造一个数字更诚实。

## 结果信封

```json
{
  "package_id": "wp-12073-01",
  "task_type": "01-asset-registration",
  "report_id": "12073",
  "provenance": {
    "source_hash": "sha256:362fbe90ba196e81f94aa4f6dd9d74bc5f69c729e7eb9f99a125fb9415bea850",
    "source_field": "markdown",
    "producer": "scripts/kf_wp12073_01_asset_manifest.py",
    "emitted_at": "2026-11-12T02:27:44.055675+00:00",
    "notes": "asset registration only: source hash pinned, 32 assets registered, claims intentionally empty (extraction is outside this package's objective)"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-12073-01",
      "task_type": "01-asset-registration",
      "report_id": "12073",
      "objective": {
        "register_assets": true,
        "classify_report_type": false
      },
      "generated_at": "2026-11-12T02:27:44.055675+00:00",
      "provenance": {
        "source_uri": "tensor://reports/12073",
        "source_field": "markdown",
        "source_hash": "sha256:362fbe90ba196e81f94aa4f6dd9d74bc5f69c729e7eb9f99a125fb9415bea850",
        "hash_alg": "sha256",
        "hashed_bytes": "markdown encoded as utf-8 (no normalization)",
        "source_chars": 3446,
        "source_bytes_utf8": 5799,
        "contract_expected_hash": "sha256:362fbe90ba196e81f94aa4f6dd9d74bc5f69c729e7eb9f99a125fb9415bea850",
        "contract_expected_chars": 3446,
        "report_title": "实时 CII 轨迹追踪与纠偏航行优化（p161w2-arb-n01 / KVLCC2 闭环）",
        "report_scenario_key": "cii_tracking_realtime",
        "report_mission_id": 10181,
        "report_status": "published",
        "report_created_at": "2026-11-10T17:28:59.350488+00:00",
        "report_created_by": 1,
        "report_tags": [
          "CII",
          "实时合规",
          "预警",
          "MPC",
          "纠偏优化",
          "绿色航行",
          "ship-performance-platform"
        ],
        "fetched_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/12073",
        "generator": "scripts/kf_wp12073_01_asset_manifest.py",
        "contract_version": "1.0"
      },
      "resolution_vocabulary": {
        "resolved_in_source": "string (or bytes) located and hashed inside the source report",
        "referenced_unresolved": "reference parsed verbatim from the report; target lies outside this package's reachable scope and is NOT hashed or inspected",
        "declared_absent": "report itself states the asset is missing/unavailable"
      },
      "structure_index": {
        "note": "headings only; offsets are character positions into markdown",
        "headings": [
          {
            "level": 1,
            "text": "实时 CII 轨迹追踪与纠偏航行优化（p161w2-arb-n01 / mission 10181）",
            "start_char": 0,
            "line": 1
          },
          {
            "level": 2,
            "text": "① 案例与物理背景",
            "start_char": 54,
            "line": 3
          },
          {
            "level": 2,
            "text": "② 方法",
            "start_char": 507,
            "line": 13
          },
          {
            "level": 2,
            "text": "③ 计算结果（程序化注入）",
            "start_char": 1188,
            "line": 25
          },
          {
            "level": 2,
            "text": "④ 图件",
            "start_char": 2291,
            "line": 52
          },
          {
            "level": 2,
            "text": "⑤ 注意点与局限",
            "start_char": 2531,
            "line": 59
          },
          {
            "level": 2,
            "text": "⑥ 误差判定（是否 <3%）",
            "start_char": 3010,
            "line": 70
          }
        ],
        "markdown_tables": 2
      },
      "assets": [
        {
          "asset_class": "report_markdown",
          "label": "报告 12073 markdown（唯一源资产，字节级锚定）",
          "in_report_section": "document",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 3446,
            "start_line": 1,
            "end_line": 82,
            "quote": "# 实时 CII 轨迹追踪与纠偏航行优化（p161w2-arb-n01 / mission 10181）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256(markdown utf-8 bytes) == contract source_hash",
            "result": "resolved"
          },
          "payload": {
            "chars": 3446,
            "bytes_utf8": 5799,
            "sha256": "sha256:362fbe90ba196e81f94aa4f6dd9d74bc5f69c729e7eb9f99a125fb9415bea850",
            "field": "markdown",
            "fetched_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/12073"
          },
          "note": "源哈希与契约一致；本工序只登记，不抽取",
          "asset_id": "A01"
        },
        {
          "asset_class": "embedded_figure",
          "label": "图件 fig1_cumulative_cii_band.png",
          "in_report_section": "④ 图件",
          "locator": {
            "method": "char_span",
            "start_char": 2302,
            "end_char": 2330,
            "start_line": 53,
            "end_line": 53,
            "quote": "fig1_cumulative_cii_band.png",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET /tensor/reports/12073/figures/fig1_cumulative_cii_band.png → png bytes",
            "result": "resolved"
          },
          "payload": {
            "name": "fig1_cumulative_cii_band.png",
            "record_caption": "累计 CII 轨迹与目标 ±3%/±5% 偏差带；基线（恒速）在风暴段冲出红带，MPC 纠偏后贴住目标线。",
            "bytes": 61079,
            "sha256": "sha256:3e6edcded54851aa3cc6dd0c8b74680afc0519e75b08ae210f18b8027ada30e1",
            "figures_field_index": 0
          },
          "note": "文件名在 ④ 段逐字出现；png 字节自报告图件端点取回并本地重算 sha256",
          "asset_id": "A02"
        },
        {
          "asset_class": "embedded_figure",
          "label": "图件 fig2_projection_deviation.png",
          "in_report_section": "④ 图件",
          "locator": {
            "method": "char_span",
            "start_char": 2356,
            "end_char": 2385,
            "start_line": 54,
            "end_line": 54,
            "quote": "fig2_projection_deviation.png",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET /tensor/reports/12073/figures/fig2_projection_deviation.png → png bytes",
            "result": "resolved"
          },
          "payload": {
            "name": "fig2_projection_deviation.png",
            "record_caption": "投影终值偏差时间历程：预警阈值（黄 3%/红 5%）与纠偏后回落的闭环证据；ETA 紧时残留偏差如实显示。",
            "bytes": 83655,
            "sha256": "sha256:2d559898ded6eda4a541a916544ef47702bac8e7a25c7724140fb225e67d715c",
            "figures_field_index": 1
          },
          "note": "文件名在 ④ 段逐字出现；png 字节自报告图件端点取回并本地重算 sha256",
          "asset_id": "A03"
        },
        {
          "asset_class": "embedded_figure",
          "label": "图件 fig3_speed_and_disturbance.png",
          "in_report_section": "④ 图件",
          "locator": {
            "method": "char_span",
            "start_char": 2406,
            "end_char": 2436,
            "start_line": 55,
            "end_line": 55,
            "quote": "fig3_speed_and_disturbance.png",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET /tensor/reports/12073/figures/fig3_speed_and_disturbance.png → png bytes",
            "result": "resolved"
          },
          "payload": {
            "name": "fig3_speed_and_disturbance.png",
            "record_caption": "上：MPC 指令/实际航速与基线航速；下：加阻因子 γ(t)。纠偏把降速集中在风暴段，ETA 窗口被用满。",
            "bytes": 59543,
            "sha256": "sha256:b5ff23fcac85030f75e952fc6e04347b32c4cdcd409d870a8f747a57ea72cf80",
            "figures_field_index": 2
          },
          "note": "文件名在 ④ 段逐字出现；png 字节自报告图件端点取回并本地重算 sha256",
          "asset_id": "A04"
        },
        {
          "asset_class": "embedded_figure",
          "label": "图件 fig4_root_cause.png",
          "in_report_section": "④ 图件",
          "locator": {
            "method": "char_span",
            "start_char": 2451,
            "end_char": 2470,
            "start_line": 56,
            "end_line": 56,
            "quote": "fig4_root_cause.png",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET /tensor/reports/12073/figures/fig4_root_cause.png → png bytes",
            "result": "resolved"
          },
          "payload": {
            "name": "fig4_root_cause.png",
            "record_caption": "根因分解（链式 vs LMDI 双方法）：加阻 30% 场景下 environment 项主导，两法分配差异显式给出。",
            "bytes": 32435,
            "sha256": "sha256:b54d83ab73784a70db0638881ffc3d7d87a9750a41d34130e57a07d4c8769401",
            "figures_field_index": 3
          },
          "note": "文件名在 ④ 段逐字出现；png 字节自报告图件端点取回并本地重算 sha256",
          "asset_id": "A05"
        },
        {
          "asset_class": "embedded_figure",
          "label": "图件 fig5_correction_sensitivity.png",
          "in_report_section": "④ 图件",
          "locator": {
            "method": "char_span",
            "start_char": 2481,
            "end_char": 2512,
            "start_line": 57,
            "end_line": 57,
            "quote": "fig5_correction_sensitivity.png",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET /tensor/reports/12073/figures/fig5_correction_sensitivity.png → png bytes",
            "result": "resolved"
          },
          "payload": {
            "name": "fig5_correction_sensitivity.png",
            "record_caption": "CII-航速灵敏度（多 γ）+ 目标线与 λ-KKT/SLSQP 求解器解位置：纠偏本质是沿 V² 律找命中目标的航速。",
            "bytes": 66230,
            "sha256": "sha256:f17685826598cdd7da4785f2e0f2b85a9890982825167d3c5f5cbc673db15e99",
            "figures_field_index": 4
          },
          "note": "文件名在 ④ 段逐字出现；png 字节自报告图件端点取回并本地重算 sha256",
          "asset_id": "A06"
        },
        {
          "asset_class": "section:case",
          "label": "① 案例与物理背景（母型 / 核算年 / 目标 CII / 物理链）",
          "in_report_section": "① 案例与物理背景",
          "locator": {
            "method": "char_span",
            "start_char": 54,
            "end_char": 66,
            "start_line": 3,
            "end_line": 3,
            "quote": "## ① 案例与物理背景",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "heading string unique in markdown",
            "result": "resolved"
          },
          "payload": null,
          "note": "标题定位点，供下游工序按段寻址；不抽取正文",
          "asset_id": "A07"
        },
        {
          "asset_class": "section:method",
          "label": "② 方法（实时内核 → 目标轨迹 → 预警根因 → 纠偏优化 → 闭环仿真）",
          "in_report_section": "② 方法",
          "locator": {
            "method": "char_span",
            "start_char": 507,
            "end_char": 514,
            "start_line": 13,
            "end_line": 13,
            "quote": "## ② 方法",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "heading string unique in markdown",
            "result": "resolved"
          },
          "payload": null,
          "note": "标题定位点，供下游工序按段寻址；不抽取正文",
          "asset_id": "A08"
        },
        {
          "asset_class": "section:results",
          "label": "③ 计算结果（C1–C5 判据表 + 闭环细节 + honest FAIL）",
          "in_report_section": "③ 计算结果（程序化注入）",
          "locator": {
            "method": "char_span",
            "start_char": 1188,
            "end_char": 1204,
            "start_line": 25,
            "end_line": 25,
            "quote": "## ③ 计算结果（程序化注入）",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "heading string unique in markdown",
            "result": "resolved"
          },
          "payload": null,
          "note": "标题定位点，供下游工序按段寻址；不抽取正文",
          "asset_id": "A09"
        },
        {
          "asset_class": "section:figures",
          "label": "④ 图件（fig1–fig5 文件名清单）",
          "in_report_section": "④ 图件",
          "locator": {
            "method": "char_span",
            "start_char": 2291,
            "end_char": 2298,
            "start_line": 52,
            "end_line": 52,
            "quote": "## ④ 图件",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "heading string unique in markdown",
            "result": "resolved"
          },
          "payload": null,
          "note": "标题定位点，供下游工序按段寻址；不抽取正文",
          "asset_id": "A10"
        },
        {
          "asset_class": "section:limits",
          "label": "⑤ 注意点与局限",
          "in_report_section": "⑤ 注意点与局限",
          "locator": {
            "method": "char_span",
            "start_char": 2531,
            "end_char": 2542,
            "start_line": 59,
            "end_line": 59,
            "quote": "## ⑤ 注意点与局限",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "heading string unique in markdown",
            "result": "resolved"
          },
          "payload": null,
          "note": "标题定位点，供下游工序按段寻址；不抽取正文",
          "asset_id": "A11"
        },
        {
          "asset_class": "section:error",
          "label": "⑥ 误差判定（是否 <3%）",
          "in_report_section": "⑥ 误差判定（是否 <3%）",
          "locator": {
            "method": "char_span",
            "start_char": 3010,
            "end_char": 3027,
            "start_line": 70,
            "end_line": 70,
            "quote": "## ⑥ 误差判定（是否 <3%）",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "heading string unique in markdown",
            "result": "resolved"
          },
          "payload": null,
          "note": "标题定位点，供下游工序按段寻址；不抽取正文",
          "asset_id": "A12"
        },
        {
          "asset_class": "table",
          "label": "判据表表头（C1–C5：量 / 数值 / 阈值 / 结论）",
          "in_report_section": "③ 计算结果（程序化注入）",
          "locator": {
            "method": "char_span",
            "start_char": 1206,
            "end_char": 1231,
            "start_line": 27,
            "end_line": 27,
            "quote": "| 判据 | 量 | 数值 | 阈值 | 结论 |",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim string located in markdown",
            "result": "resolved"
          },
          "payload": null,
          "note": "markdown 表格；本工序只登记位置，不抽取单元格内容",
          "asset_id": "A13"
        },
        {
          "asset_class": "table",
          "label": "误差判定表表头（关键量 / 基准 / 误差 / <3%?）",
          "in_report_section": "⑥ 误差判定（是否 <3%）",
          "locator": {
            "method": "char_span",
            "start_char": 3028,
            "end_char": 3052,
            "start_line": 71,
            "end_line": 71,
            "quote": "| 关键量 | 基准 | 误差 | <3%? |",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim string located in markdown",
            "result": "resolved"
          },
          "payload": null,
          "note": "markdown 表格；仅登记位置",
          "asset_id": "A14"
        },
        {
          "asset_class": "case_geometry",
          "label": "KVLCC2 主尺度串（L_pp / B / T / Cb / Δ / dwt）",
          "in_report_section": "① 案例与物理背景",
          "locator": {
            "method": "char_span",
            "start_char": 85,
            "end_char": 155,
            "start_line": 4,
            "end_line": 4,
            "quote": "L_pp 320 m / B 58 m / T 20.8 m / Cb 0.8098 / Δ 320 420 t / 300 000 dwt",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim string located in markdown",
            "result": "resolved"
          },
          "payload": null,
          "note": "母型主尺度与排水量，逐字来自 ① 段",
          "asset_id": "A15"
        },
        {
          "asset_class": "referenced_repo_artifact",
          "label": "母型几何文件路径",
          "in_report_section": "① 案例与物理背景",
          "locator": {
            "method": "char_span",
            "start_char": 165,
            "end_char": 208,
            "start_line": 5,
            "end_line": 5,
            "quote": "backend/data/geometry/ships/KVLCC2_Hull.stl",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists(worktree/backend/data/geometry/ships/KVLCC2_Hull.stl)",
            "result": "unresolved"
          },
          "payload": null,
          "note": "路径逐字出现在 ① 段；该文件属于 ship-performance-platform；TensorKnowledge 检出内不存在该路径 → 引用保持 unresolved，不声称其内容，也不打开外部仓",
          "asset_id": "A16"
        },
        {
          "asset_class": "referenced_repo_artifact",
          "label": "实时 CII 内核模块",
          "in_report_section": "② 方法",
          "locator": {
            "method": "char_span",
            "start_char": 528,
            "end_char": 539,
            "start_line": 14,
            "end_line": 14,
            "quote": "realtime.py",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists(worktree/realtime.py)",
            "result": "unresolved"
          },
          "payload": null,
          "note": "§② 第 1 条声明的实现文件；TensorKnowledge 检出内不存在该路径 → 引用保持 unresolved，不声称其内容，也不打开外部仓",
          "asset_id": "A17"
        },
        {
          "asset_class": "referenced_repo_artifact",
          "label": "目标轨迹 / 偏差带模块",
          "in_report_section": "② 方法",
          "locator": {
            "method": "char_span",
            "start_char": 645,
            "end_char": 654,
            "start_line": 16,
            "end_line": 16,
            "quote": "target.py",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists(worktree/target.py)",
            "result": "unresolved"
          },
          "payload": null,
          "note": "§② 第 2 条声明的实现文件；TensorKnowledge 检出内不存在该路径 → 引用保持 unresolved，不声称其内容，也不打开外部仓",
          "asset_id": "A18"
        },
        {
          "asset_class": "referenced_repo_artifact",
          "label": "预警与根因模块",
          "in_report_section": "② 方法",
          "locator": {
            "method": "char_span",
            "start_char": 780,
            "end_char": 788,
            "start_line": 18,
            "end_line": 18,
            "quote": "alert.py",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists(worktree/alert.py)",
            "result": "unresolved"
          },
          "payload": null,
          "note": "§② 第 3 条声明的实现文件；TensorKnowledge 检出内不存在该路径 → 引用保持 unresolved，不声称其内容，也不打开外部仓",
          "asset_id": "A19"
        },
        {
          "asset_class": "referenced_repo_artifact",
          "label": "纠偏优化模块",
          "in_report_section": "② 方法",
          "locator": {
            "method": "char_span",
            "start_char": 903,
            "end_char": 916,
            "start_line": 20,
            "end_line": 20,
            "quote": "correction.py",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists(worktree/correction.py)",
            "result": "unresolved"
          },
          "payload": null,
          "note": "§② 第 4 条声明的实现文件；TensorKnowledge 检出内不存在该路径 → 引用保持 unresolved，不声称其内容，也不打开外部仓",
          "asset_id": "A20"
        },
        {
          "asset_class": "referenced_repo_artifact",
          "label": "闭环仿真模块",
          "in_report_section": "② 方法",
          "locator": {
            "method": "char_span",
            "start_char": 1064,
            "end_char": 1075,
            "start_line": 22,
            "end_line": 22,
            "quote": "simulate.py",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists(worktree/simulate.py)",
            "result": "unresolved"
          },
          "payload": null,
          "note": "§② 第 5 条声明的实现文件；TensorKnowledge 检出内不存在该路径 → 引用保持 unresolved，不声称其内容，也不打开外部仓",
          "asset_id": "A21"
        },
        {
          "asset_class": "referenced_repo_artifact",
          "label": "仓内独立实现（交叉校验基准）",
          "in_report_section": "③ 计算结果（程序化注入）",
          "locator": {
            "method": "char_span",
            "start_char": 1325,
            "end_char": 1354,
            "start_line": 30,
            "end_line": 30,
            "quote": "C1 与仓内独立实现（mepc.attained_cii）",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists(worktree/C1)",
            "result": "unresolved"
          },
          "payload": null,
          "note": "§③ 判据表 C1 第 2 行（该模块名在报告中出现两次，故取整行唯一引文）；本工序不执行它；TensorKnowledge 检出内不存在该路径 → 引用保持 unresolved，不声称其内容，也不打开外部仓",
          "asset_id": "A22"
        },
        {
          "asset_class": "equation",
          "label": "螺旋桨定律 + 附加阻力（瞬时功率）",
          "in_report_section": "① 案例与物理背景",
          "locator": {
            "method": "char_span",
            "start_char": 369,
            "end_char": 385,
            "start_line": 10,
            "end_line": 10,
            "quote": "P = c_p·V³·(1+γ)",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim string located in markdown",
            "result": "resolved"
          },
          "payload": null,
          "note": "① 段物理链首式；仅登记引文，不做推导",
          "asset_id": "A23"
        },
        {
          "asset_class": "equation",
          "label": "单位航程 CO2 排放 φ",
          "in_report_section": "① 案例与物理背景",
          "locator": {
            "method": "char_span",
            "start_char": 402,
            "end_char": 433,
            "start_line": 10,
            "end_line": 10,
            "quote": "φ = (P·SFOC + P_aux·SFOC_aux)/V",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim string located in markdown",
            "result": "resolved"
          },
          "payload": null,
          "note": "① 段物理链第二式",
          "asset_id": "A24"
        },
        {
          "asset_class": "equation",
          "label": "目标质量 M_allowed(t)",
          "in_report_section": "② 方法",
          "locator": {
            "method": "char_span",
            "start_char": 658,
            "end_char": 695,
            "start_line": 16,
            "end_line": 16,
            "quote": "M_allowed(t)=CII_target·Capacity·D(t)",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim string located in markdown",
            "result": "resolved"
          },
          "payload": null,
          "note": "§② 第 2 条目标轨迹定义",
          "asset_id": "A25"
        },
        {
          "asset_class": "equation",
          "label": "λ-KKT 解析解（逐时段最优航速）",
          "in_report_section": "② 方法",
          "locator": {
            "method": "char_span",
            "start_char": 986,
            "end_char": 1012,
            "start_line": 21,
            "end_line": 21,
            "quote": "V_i=((a_i+μ)/(2k_i))^{1/3}",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim string located in markdown",
            "result": "resolved"
          },
          "payload": null,
          "note": "§② 第 4 条纠偏优化核心式",
          "asset_id": "A26"
        },
        {
          "asset_class": "regulatory_reference",
          "label": "CII 折减系数 / 参考线规则（两件规则同处引用）",
          "in_report_section": "⑤ 注意点与局限",
          "locator": {
            "method": "char_span",
            "start_char": 2657,
            "end_char": 2677,
            "start_line": 62,
            "end_line": 62,
            "quote": "MEPC.353(78)/338(76)",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "regulatory original text reachable offline",
            "result": "unresolved"
          },
          "payload": null,
          "note": "§⑤ 第 2 条：规则原文离线不可回读 → 报告自身对该层判 WITHHELD；文件号逐字可定位，原文不可离线回读 → 仅登记引用",
          "asset_id": "A27"
        },
        {
          "asset_class": "regulatory_reference",
          "label": "燃料碳因子 CF 公布值来源",
          "in_report_section": "⑥ 误差判定（是否 <3%）",
          "locator": {
            "method": "char_span",
            "start_char": 3182,
            "end_char": 3194,
            "start_line": 75,
            "end_line": 75,
            "quote": "MEPC.364(79)",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "regulatory original text reachable offline",
            "result": "unresolved"
          },
          "payload": null,
          "note": "§⑥ 误差表「燃料 CF」行的基准来源；文件号逐字可定位，原文不可离线回读 → 仅登记引用",
          "asset_id": "A28"
        },
        {
          "asset_class": "run_output_token",
          "label": "ETA 受限模式标签",
          "in_report_section": "③ 计算结果（程序化注入）",
          "locator": {
            "method": "char_span",
            "start_char": 2219,
            "end_char": 2237,
            "start_line": 49,
            "end_line": 49,
            "quote": "mode=\"eta_limited\"",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim string located in markdown",
            "result": "resolved"
          },
          "payload": null,
          "note": "§③ honest FAIL 段落逐字给出的模式字符串",
          "asset_id": "A29"
        },
        {
          "asset_class": "run_output_token",
          "label": "航速受限模式标签",
          "in_report_section": "③ 计算结果（程序化注入）",
          "locator": {
            "method": "char_span",
            "start_char": 2269,
            "end_char": 2282,
            "start_line": 50,
            "end_line": 50,
            "quote": "speed_limited",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim string located in markdown",
            "result": "resolved"
          },
          "payload": null,
          "note": "§③ honest FAIL 段落逐字给出的模式字符串",
          "asset_id": "A30"
        },
        {
          "asset_class": "run_output_token",
          "label": "规则外推标记",
          "in_report_section": "⑤ 注意点与局限",
          "locator": {
            "method": "char_span",
            "start_char": 2714,
            "end_char": 2728,
            "start_line": 63,
            "end_line": 63,
            "quote": "z_extrapolated",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim string located in markdown",
            "result": "resolved"
          },
          "payload": null,
          "note": "§⑤ 第 2 条：2027+ 自动标记",
          "asset_id": "A31"
        },
        {
          "asset_class": "run_output_token",
          "label": "方向性建议字段",
          "in_report_section": "⑤ 注意点与局限",
          "locator": {
            "method": "char_span",
            "start_char": 2914,
            "end_char": 2929,
            "start_line": 67,
            "end_line": 67,
            "quote": "recommendations",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim string located in markdown",
            "result": "resolved"
          },
          "payload": null,
          "note": "§⑤ 第 5 条：航线 / 纵倾 / 清洗建议字段名",
          "asset_id": "A32"
        }
      ],
      "claims": [],
      "counts": {
        "assets": 32,
        "by_class": {
          "report_markdown": 1,
          "embedded_figure": 5,
          "section:case": 1,
          "section:method": 1,
          "section:results": 1,
          "section:figures": 1,
          "section:limits": 1,
          "section:error": 1,
          "table": 2,
          "case_geometry": 1,
          "referenced_repo_artifact": 7,
          "equation": 4,
          "regulatory_reference": 2,
          "run_output_token": 4
        },
        "by_resolution": {
          "resolved_in_source": 23,
          "referenced_unresolved": 9
        },
        "resolved_in_source": 23,
        "referenced_unresolved": 9,
        "declared_absent": 0,
        "claims": 0
      },
      "integrity": {
        "quote_uniqueness": {
          "total": 31,
          "unique": 31,
          "non_unique": []
        },
        "hash_recomputed_locally": "sha256:362fbe90ba196e81f94aa4f6dd9d74bc5f69c729e7eb9f99a125fb9415bea850",
        "hash_matches_contract": true,
        "figure_bytes_hashed": 5
      }
    }
  },
  "claims": []
}
```
