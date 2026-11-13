# KF-RESULT wp-8753-01

**工作包** `wp-8753-01`（task_type `01-asset-registration`，lane C）｜**report_id** `8753`｜
**scenario_key** `p120w2-n04`｜**源字段** `markdown`｜**交付仓** TensorKnowledge（draft）

## ① 本工序做了什么

只做一件事：把报告 `8753` 的**源资产身份**与该 markdown 中**可解析的附件/工件清单**登记下来
（register_assets=true，classify_report_type=false）。**不做抽取**：不产出知识声明、不判定报告类型、
不给任何条目打 `verified`。

- 源身份：`tensor://reports/8753`，`markdown` 字段，实测 sha256 `sha256:c0ae2fdc7da47e848f0e5eb0379429def3e68bcb299927a7f41d183e4cf07af1`
  （声明哈希一致：True；字符数 8187 vs 契约 8187，一致：True）。
- 资产清单：共 **17** 条（cross_report_reference=2, data_artifact=1, document=1, figure_collection=1, figure_declared=6, generator_script=2, module_reference=1, source_document=1, test_suite=1, vendor_reference=1）；其中在源内定位成功
  `resolved_in_source` = 1（仅源文档本身；其余都是报告"声明"的引用，
  在本交付 worktree / 平台图端点内不可解析，故记 `referenced_unresolved` = 16，
  `declared_absent` = 0）——**"取不到"不等于"不存在"**，见 §⑤。
- 每条资产都带**逐字定位器**（char span + 行号 + 原文引文 + 出现次数），可被平台独立重解析。
- claims 为空数组（契约 notes「claims 允许为空数组」+ 约束 no_forced_claim_generation=true），
  空数组理由写入 manifest 的 `claims_empty_reason`，不是遗漏。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`POST /api/v1/auth/login` 拿 Bearer token → `GET /api/v1/tensor/reports/8753`，
   取 `markdown` 字段（不读数据库、不读其它 report_id）。
2. **字节哈希**：对 `markdown.encode('utf-8')` 本地重算 sha256 与字符/字节/行数，与契约值逐项比对
   （只作比较目标，绝不回填）。
3. **结构测量**：解析 `## ` 标题行、首行、末行；实测编号章节 present=①②③④⑤⑥、
   absent=none（见 manifest `structure`）。
4. **附件/工件解析（只登记，不读内容）**：
   - 图：平台 record 的 `figures[].name` + 正文 `![name](figs/name.png)` 双向对齐，并探测
     `GET /api/v1/tensor/reports/8753/figures/<name>` 是否有字节；
   - 路径：正则扫描正文（fenced 复现块的 `backend/…`、`artifacts/…`、`cd backend` 后的 `modules/…`、
     以及散文里的反引号路径、`PROVENANCE.md` 类具名文件），按类型归类；
   - 跨报告引用：`m5745` / `m7061 v1.0.0` 等仅以标识符出现、无 `tensor://` URI 的，登记为
     `cross_report_reference` 且**不抓取**；
   - 每条引用都回溯到**权威 markdown 的逐字片段**并计算 char span/行号/出现次数，
     解析失败即 `SystemExit` 中止（不产出半份清单）。
5. **存在性探测**：每条路径在本交付 worktree 内 `Path.exists()` 实测（只探测，不读取生产仓文件）；
   平台图端点返回码如实记录。
6. **结果信封**：`kf_result.v1` 结构（package_id / task_type / report_id / provenance / outputs / claims），
   `provenance.source_hash` 直接取实测哈希。
7. **自检**：`jsonschema` 校验（kf_result 用仓内 `schemas/kf_result.v1.schema.json`；manifest 用本包
   `asset_manifest.schema.json`，因仓内 `schemas/asset_manifest.v1.schema.json` 用 `const` 死锁在 wp-448-01 上）
   + 6 条 acceptance 逐项 + `pytest` 不变量。

一键复跑：
```bash
cd <this-worktree> && python3 scripts/kf_wp8753_01_register.py all && python3 scripts/kf_wp8753_01_publish.py render && python3 -m pytest tests/test_kf_wp8753_01_asset_manifest.py -q
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-8753-01/asset_manifest.json` | 本工序主产物：源身份（sha256/chars/bytes/lines）+ 17 条带定位器的资产 + 空 claims + 计数/完整性/观测/局限 |
| `docs/kf/wp-8753-01/kf_result.json` | 结果信封（唯一交付结构），`outputs["asset_manifest.json"]` 内嵌清单，claims 空数组 |
| `docs/kf/wp-8753-01/asset_manifest.schema.json` | 本包通用（去 wp-448 const）manifest JSON Schema，供 schema_pass 机器校验 |
| `docs/kf/wp-8753-01/verification.json` | 6 条 acceptance 自检记录（含每条 detail 与 all_ok） |
| `docs/kf/wp-8753-01/figures/wp8753_01_source_locator_map.png` | 结果图：源 markdown 行剖面 + 资产锚点 + 解析状态分布 |
| `docs/kf/wp-8753-01/KF-RESULT-wp-8753-01.md` | 本报告（正文 + 唯一 json 块） |
| `runs/wp-8753-01/source_8753.md` | 取源时的 UTF-8 字节副本（离线复算哈希/引文用），sha256 同源 |
| `scripts/kf_wp8753_01_register.py` | build/schema/envelope/verify/figure 全流程，零手抄 |
| `scripts/kf_wp8753_01_publish.py` | 本报告渲染 + 发布（数字全部从产物插值） |
| `tests/test_kf_wp8753_01_asset_manifest.py` | 12 条不变量（离线 11 + 平台在线重解析 1） |

## ④ 证据定位表（字段/资产 → 原文逐字引文）

| 资产 | 类 | 标签 | 章节 | 起行 | 止行 | 出现次数 | 解析 | 原文引文（逐字，来自权威 markdown） |
|---|---|---|---|---|---|---|---|---|
| A00 | source_document | report 8753 markdown (source_field=markdown) | (whole document) | 1 | 192 | 1 | resolved | `# FuelEU Maritime 柔性机制三件套成熟化（p120w2-n04 / m7431）` |
| A01 | figure_declared | fig_a_rfnbo_closed_form.png | ④ 结果图 | 128 | 128 | 1 | unresolved | `![fig_a_rfnbo_closed_form.png](figs/fig_a_rfnbo_closed_form.png)` |
| A02 | figure_declared | fig_penalty_stack.png | ④ 结果图 | 132 | 132 | 1 | unresolved | `![fig_penalty_stack.png](figs/fig_penalty_stack.png)` |
| A03 | figure_declared | fig_ghgi_trajectory.png | ④ 结果图 | 136 | 136 | 1 | unresolved | `![fig_ghgi_trajectory.png](figs/fig_ghgi_trajectory.png)` |
| A04 | figure_declared | fig_bank_carry_cap.png | ④ 结果图 | 140 | 140 | 1 | unresolved | `![fig_bank_carry_cap.png](figs/fig_bank_carry_cap.png)` |
| A05 | figure_declared | fig_mu_and_cap_scan.png | ④ 结果图 | 144 | 144 | 1 | unresolved | `![fig_mu_and_cap_scan.png](figs/fig_mu_and_cap_scan.png)` |
| A06 | figure_declared | fig_lp_vs_enum.png | ④ 结果图 | 148 | 148 | 1 | unresolved | `![fig_lp_vs_enum.png](figs/fig_lp_vs_enum.png)` |
| A07 | module_reference | backend/modules/fueleu_maritime | FuelEU Maritime 柔性机制三件套成熟化（p120w2-n04 / m7431） | 3 | 3 | 2 | unresolved | `backend/modules/fueleu_maritime` |
| A08 | generator_script | artifacts/fueleu_maritime_m7431/run_case.py | 审计链与复现 | 179 | 179 | 1 | unresolved | `../artifacts/fueleu_maritime_m7431/run_case.py` |
| A09 | generator_script | artifacts/fueleu_maritime_m7431/gen_report.py | 审计链与复现 | 180 | 180 | 1 | unresolved | `artifacts/fueleu_maritime_m7431/gen_report.py` |
| A10 | data_artifact | artifacts/fueleu_maritime_m7431/acceptance.json | 审计链与复现 | 183 | 183 | 1 | unresolved | `artifacts/fueleu_maritime_m7431/acceptance.json` |
| A11 | figure_collection | artifacts/fueleu_maritime_m7431/figs/ | 审计链与复现 | 184 | 184 | 1 | unresolved | `artifacts/fueleu_maritime_m7431/figs/` |
| A12 | vendor_reference | backend/modules/fueleu_maritime/_m5745_ref/ | 审计链与复现 | 185 | 185 | 1 | unresolved | `backend/modules/fueleu_maritime/_m5745_ref/` |
| A13 | test_suite | backend/modules/fueleu_maritime/tests | 审计链与复现 | 178 | 178 | 1 | unresolved | `modules/fueleu_maritime/tests` |
| A14 | document | PROVENANCE.md | 审计链与复现 | 185 | 185 | 1 | unresolved | `PROVENANCE.md` |
| A15 | cross_report_reference | m5745 reference implementation (regression baseline) | ⑥ 误差判定（关键量 vs 基准，逐项回答是否 < 3%） | 164 | 164 | 1 | unresolved | `m5745 参考实现（逐字 vendor）` |
| A16 | cross_report_reference | m7061 v1.0.0 (previous version, §3.4 diff base) | ③ 计算结果 | 118 | 118 | 1 | unresolved | `与上一版（m7061, v1.0.0）的量化差异` |

源级身份事实（同一 markdown 字节内可逐字复核）：首行 `# FuelEU Maritime 柔性机制三件套成熟化（p120w2-n04 / m7431）`；
标题与契约一致：True；scenario 与契约一致：True；
平台 record 状态 `published`，tags `['FuelEU', '柔性机制', 'banking', 'borrowing', 'RFNBO', 'OPS', '线性规划', '船舶绿色航行']`。

### 结果图

![wp8753_01_source_locator_map.png](wp8753_01_source_locator_map.png)

左：报告 8753 源 markdown 的行字符剖面（8187 字符 / 192 行），
彩色竖线=各登记的资产锚点（按类着色），点线=`## ` 章节边界；右：解析状态分布（平台图字节 0/6 可得）。

## ⑤ 注意点与局限

1. **`referenced_unresolved` ≠ 不存在**：16 条 `referenced_unresolved` 的判据只是「在 TensorKnowledge 交付 worktree + 平台图端点里取不到」；
   这些路径属于生产仓（ship-performance-platform 的 `backend/modules/fueleu_maritime`、
   `artifacts/fueleu_maritime_m7431` 树），本单边界禁止触碰，因此**不声明任何字节/哈希**。
2. **图只有元数据**：6 张图在 record 元数据里有 name+caption、正文有相对链接，
   但平台图端点对全部 6 张图返回 404（见下），故登记为 metadata-only，无哈希：
- `fig_a_rfnbo_closed_form.png` → platform figure endpoint probe: HTTP 404, bytes=0, caption: 判据 (a)：RFNBO 2× 乘子的 GHGI 闭式解与能量流数值解重合（残差 ~1e-14）；虚线为 m=1 基线，可见乘子把加权平均强度整体下拉。
- `fig_penalty_stack.png` → platform figure endpoint probe: HTTP 404, bytes=0, caption: 机制叠层：3 船 2025–2035 累计罚金随机制逐层接入的变化（无柔性 8.02M → 全柔性 0 EUR）。
- `fig_ghgi_trajectory.png` → platform figure endpoint probe: HTTP 404, bytes=0, caption: 判据 (i)：各船年度 GHG 强度轨迹 vs 限值台阶；红线为 2033/2034 的乘子日落边界。
- `fig_bank_carry_cap.png` → platform figure endpoint probe: HTTP 404, bytes=0, caption: 判据 (j)：结转（banking）余额轨迹——无上限口径 vs 结转上限 0.2% 允许排放口径。
- `fig_mu_and_cap_scan.png` → platform figure endpoint probe: HTTP 404, bytes=0, caption: 判据 (h)/(c)：偿还放大 μ 的罚金单调性与预支上限 κ 的灵敏度（左/右）。
- `fig_lp_vs_enum.png` → platform figure endpoint probe: HTTP 404, bytes=0, caption: 判据 (d)：多年 LP（HiGHS）与 3 船×3 年顶点穷尽枚举的最优值对比（rel ~1e-16）。
3. **schema 口径**：仓内 `schemas/asset_manifest.v1.schema.json` 用 `const` 把 package_id/report_id/uri
   钉死在 wp-448-01，无法校验其它包；本单**不改共享 schema**（越界），改为写本包通用 schema 并在报告里明示，
   平台门仍是最终裁判。
4. **claims 为空是契约要求**，不是缺产物；本工序不做抽取，也不做类型判定。
5. **跨报告引用未解析**：`m5745`、`m7061 v1.0.0` 只有标识符、没有 URI，登记为 declared reference；
   若后续工序需要，须由平台给出可解析 URI。
6. **能力边界**：本单只登记「报告自己声明了什么、能否在源内逐字定位」，**不**判断工件是否真实生成、
   数字是否正确——那是下游工序与平台门的职责。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结论 | 证据 |
|---|---|---|
| valid_json | ✅ PASS | asset_manifest.json + kf_result.json parsed from disk (json.loads, utf-8) |
| schema_pass | ✅ PASS | asset_manifest validated against package-local generic schema; kf_result validated against schemas/kf_result.v1.schema.json |
| source_locator_resolvable | ✅ PASS | 17/17 asset locators re-resolved against the live markdown (verbatim substring + declared char span/line) |
| source_hash_matches | ✅ PASS | live=sha256:c0ae2fdc7da47e848f0e5eb0379429def3e68bcb299927a7f41d183e4cf07af1 manifest=sha256:c0ae2fdc7da47e848f0e5eb0379429def3e68bcb299927a7f41d183e4cf07af1 contract=sha256:c0ae2fdc7da47e848f0e5eb0379429def3e68bcb299927a7f41d183e4cf07af1 chars live=8187 contract=8187 |
| no_duplicate_ids | ✅ PASS | 17 ids, duplicates=[] |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ PASS | 0 claims (empty array by contract); claims_empty_reason stated: True; no claim carries status 'verified': True |

- 另外机器证明：`python3 -m pytest tests/test_kf_wp8753_01_asset_manifest.py -q` → 12 passed
  （含：envelope 过 `schemas/kf_result.v1.schema.json`、manifest 过本包 schema、离线逐字/span 复核、
  在线重取 markdown 重算哈希与全部引文、claims 空与无 `verified` 标记、资产计数自洽）。
- 生成脚本自检 `python3 scripts/kf_wp8753_01_register.py verify` → `all_ok = True`
  （verified_at 2026-11-12T01:33:19+00:00）。

**误差判定（是否 < 3%）**：本工序不产生物理量，只有可精确判等的整数/字符串事实
（sha256 等值、字符数 8187=8187、定位器 17/17 命中），
故不存在 3%/15% 相对误差口径——**N/A 而非「已达标」**。唯一的数值型不确定项是「生产仓工件内容」，
按 §⑤-1 明确标 unresolved，不做精度声明。

```json
{
  "package_id": "wp-8753-01",
  "task_type": "01-asset-registration",
  "report_id": "8753",
  "provenance": {
    "source_hash": "sha256:c0ae2fdc7da47e848f0e5eb0379429def3e68bcb299927a7f41d183e4cf07af1",
    "source_field": "markdown",
    "producer": "kf-worker/m15626",
    "emitted_at": "2026-11-12T01:33:18+00:00",
    "notes": "Report 8753 markdown registered as-is; 17 assets enumerated (1 resolved in source, 16 referenced-but-unresolved, platform figure bytes absent); claims empty by contract."
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-8753-01",
      "task_type": "01-asset-registration",
      "report_id": "8753",
      "lane": "C",
      "generated_at": "2026-11-12T01:33:18+00:00",
      "producer": "kf-worker/m15626",
      "source": {
        "report_id": "8753",
        "uri": "tensor://reports/8753",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "c0ae2fdc7da47e848f0e5eb0379429def3e68bcb299927a7f41d183e4cf07af1",
        "source_hash": "sha256:c0ae2fdc7da47e848f0e5eb0379429def3e68bcb299927a7f41d183e4cf07af1",
        "contract_source_hash": "sha256:c0ae2fdc7da47e848f0e5eb0379429def3e68bcb299927a7f41d183e4cf07af1",
        "hash_matches_contract": true,
        "chars": 8187,
        "contract_chars": 8187,
        "chars_match_contract": true,
        "bytes_utf8": 12729,
        "lines": 192,
        "has_crlf": false,
        "ends_with_newline": false,
        "title": "FuelEU 柔性机制三件套成熟化（p120w2-n04/m7431）：μ 偿还放大 + 乘子日落 + 结转上限",
        "contract_title": "FuelEU 柔性机制三件套成熟化（p120w2-n04/m7431）：μ 偿还放大 + 乘子日落 + 结转上限",
        "title_matches_contract": true,
        "scenario_key": "p120w2-n04",
        "contract_scenario_key": "p120w2-n04",
        "scenario_matches_contract": true,
        "platform_record": {
          "id": 8753,
          "status": "published",
          "stage": null,
          "mission_id": 7418,
          "created_by": 1,
          "created_at": "2026-11-08T14:35:40.424535+00:00",
          "tags": [
            "FuelEU",
            "柔性机制",
            "banking",
            "borrowing",
            "RFNBO",
            "OPS",
            "线性规划",
            "船舶绿色航行"
          ]
        },
        "platform_figures": [
          "fig_a_rfnbo_closed_form.png",
          "fig_penalty_stack.png",
          "fig_ghgi_trajectory.png",
          "fig_bank_carry_cap.png",
          "fig_mu_and_cap_scan.png",
          "fig_lp_vs_enum.png"
        ],
        "fetched_via": "GET /api/v1/tensor/reports/8753 (Bearer auth)",
        "line_counting": "logical lines = markdown.split(chr(10)); 1-based"
      },
      "structure": {
        "section_headers": [
          "## ① 案例介绍",
          "## ② 方法",
          "## ③ 计算结果",
          "## ④ 结果图",
          "## ⑤ 注意点 / 局限",
          "## ⑥ 误差判定（关键量 vs 基准，逐项回答是否 < 3%）",
          "## 审计链与复现"
        ],
        "numbered_sections_present": [
          "①",
          "②",
          "③",
          "④",
          "⑤",
          "⑥"
        ],
        "numbered_sections_absent": [],
        "first_line": "# FuelEU Maritime 柔性机制三件套成熟化（p120w2-n04 / m7431）",
        "first_line_looks_truncated": false,
        "last_line": "*Report generated by agent/m7418 for IN32-B01*"
      },
      "counts": {
        "assets": 17,
        "by_class": {
          "cross_report_reference": 2,
          "data_artifact": 1,
          "document": 1,
          "figure_collection": 1,
          "figure_declared": 6,
          "generator_script": 2,
          "module_reference": 1,
          "source_document": 1,
          "test_suite": 1,
          "vendor_reference": 1
        },
        "by_resolution": {
          "referenced_unresolved": 16,
          "resolved_in_source": 1
        },
        "resolved_in_source": 1,
        "referenced_unresolved": 16,
        "declared_absent": 0,
        "figures_declared": 6,
        "figures_with_platform_bytes": 0,
        "body_path_references": 8
      },
      "assets": [
        {
          "asset_id": "A00",
          "asset_class": "source_document",
          "label": "report 8753 markdown (source_field=markdown)",
          "in_report_section": "(whole document)",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 8187,
            "start_line": 1,
            "end_line": 192,
            "quote": "# FuelEU Maritime 柔性机制三件套成熟化（p120w2-n04 / m7431）",
            "occurrences": 1,
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "markdown fetched via GET /api/v1/tensor/reports/8753; sha256 + char count recomputed locally",
            "result": "resolved",
            "indicators": {
              "chars": 8187,
              "bytes_utf8": 12729,
              "sha256": "sha256:c0ae2fdc7da47e848f0e5eb0379429def3e68bcb299927a7f41d183e4cf07af1"
            }
          },
          "note": "Registered as the authoritative bytes for this package; platform re-computes the same hash independently."
        },
        {
          "asset_id": "A01",
          "asset_class": "figure_declared",
          "label": "fig_a_rfnbo_closed_form.png",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 5446,
            "end_char": 5510,
            "start_line": 128,
            "end_line": 128,
            "quote": "![fig_a_rfnbo_closed_form.png](figs/fig_a_rfnbo_closed_form.png)",
            "occurrences": 1,
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "figure declared in report record metadata (figures[].name) and linked in-body as figs/<name>; GET /api/v1/tensor/reports/8753/figures/fig_a_rfnbo_closed_form.png probed for bytes",
            "result": "unresolved",
            "indicators": {
              "http_status": 404,
              "bytes": 0,
              "caption": "判据 (a)：RFNBO 2× 乘子的 GHGI 闭式解与能量流数值解重合（残差 ~1e-14）；虚线为 m=1 基线，可见乘子把加权平均强度整体下拉。"
            }
          },
          "note": "Body link target (figs/fig_a_rfnbo_closed_form.png) exists only inside the producing repo; platform figure endpoint returned 404, so no bytes/hash can be asserted here — metadata + caption quoted from the source instead."
        },
        {
          "asset_id": "A02",
          "asset_class": "figure_declared",
          "label": "fig_penalty_stack.png",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 5599,
            "end_char": 5651,
            "start_line": 132,
            "end_line": 132,
            "quote": "![fig_penalty_stack.png](figs/fig_penalty_stack.png)",
            "occurrences": 1,
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "figure declared in report record metadata (figures[].name) and linked in-body as figs/<name>; GET /api/v1/tensor/reports/8753/figures/fig_penalty_stack.png probed for bytes",
            "result": "unresolved",
            "indicators": {
              "http_status": 404,
              "bytes": 0,
              "caption": "机制叠层：3 船 2025–2035 累计罚金随机制逐层接入的变化（无柔性 8.02M → 全柔性 0 EUR）。"
            }
          },
          "note": "Body link target (figs/fig_penalty_stack.png) exists only inside the producing repo; platform figure endpoint returned 404, so no bytes/hash can be asserted here — metadata + caption quoted from the source instead."
        },
        {
          "asset_id": "A03",
          "asset_class": "figure_declared",
          "label": "fig_ghgi_trajectory.png",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 5736,
            "end_char": 5792,
            "start_line": 136,
            "end_line": 136,
            "quote": "![fig_ghgi_trajectory.png](figs/fig_ghgi_trajectory.png)",
            "occurrences": 1,
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "figure declared in report record metadata (figures[].name) and linked in-body as figs/<name>; GET /api/v1/tensor/reports/8753/figures/fig_ghgi_trajectory.png probed for bytes",
            "result": "unresolved",
            "indicators": {
              "http_status": 404,
              "bytes": 0,
              "caption": "判据 (i)：各船年度 GHG 强度轨迹 vs 限值台阶；红线为 2033/2034 的乘子日落边界。"
            }
          },
          "note": "Body link target (figs/fig_ghgi_trajectory.png) exists only inside the producing repo; platform figure endpoint returned 404, so no bytes/hash can be asserted here — metadata + caption quoted from the source instead."
        },
        {
          "asset_id": "A04",
          "asset_class": "figure_declared",
          "label": "fig_bank_carry_cap.png",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 5875,
            "end_char": 5929,
            "start_line": 140,
            "end_line": 140,
            "quote": "![fig_bank_carry_cap.png](figs/fig_bank_carry_cap.png)",
            "occurrences": 1,
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "figure declared in report record metadata (figures[].name) and linked in-body as figs/<name>; GET /api/v1/tensor/reports/8753/figures/fig_bank_carry_cap.png probed for bytes",
            "result": "unresolved",
            "indicators": {
              "http_status": 404,
              "bytes": 0,
              "caption": "判据 (j)：结转（banking）余额轨迹——无上限口径 vs 结转上限 0.2% 允许排放口径。"
            }
          },
          "note": "Body link target (figs/fig_bank_carry_cap.png) exists only inside the producing repo; platform figure endpoint returned 404, so no bytes/hash can be asserted here — metadata + caption quoted from the source instead."
        },
        {
          "asset_id": "A05",
          "asset_class": "figure_declared",
          "label": "fig_mu_and_cap_scan.png",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 6005,
            "end_char": 6061,
            "start_line": 144,
            "end_line": 144,
            "quote": "![fig_mu_and_cap_scan.png](figs/fig_mu_and_cap_scan.png)",
            "occurrences": 1,
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "figure declared in report record metadata (figures[].name) and linked in-body as figs/<name>; GET /api/v1/tensor/reports/8753/figures/fig_mu_and_cap_scan.png probed for bytes",
            "result": "unresolved",
            "indicators": {
              "http_status": 404,
              "bytes": 0,
              "caption": "判据 (h)/(c)：偿还放大 μ 的罚金单调性与预支上限 κ 的灵敏度（左/右）。"
            }
          },
          "note": "Body link target (figs/fig_mu_and_cap_scan.png) exists only inside the producing repo; platform figure endpoint returned 404, so no bytes/hash can be asserted here — metadata + caption quoted from the source instead."
        },
        {
          "asset_id": "A06",
          "asset_class": "figure_declared",
          "label": "fig_lp_vs_enum.png",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 6143,
            "end_char": 6189,
            "start_line": 148,
            "end_line": 148,
            "quote": "![fig_lp_vs_enum.png](figs/fig_lp_vs_enum.png)",
            "occurrences": 1,
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "figure declared in report record metadata (figures[].name) and linked in-body as figs/<name>; GET /api/v1/tensor/reports/8753/figures/fig_lp_vs_enum.png probed for bytes",
            "result": "unresolved",
            "indicators": {
              "http_status": 404,
              "bytes": 0,
              "caption": "判据 (d)：多年 LP（HiGHS）与 3 船×3 年顶点穷尽枚举的最优值对比（rel ~1e-16）。"
            }
          },
          "note": "Body link target (figs/fig_lp_vs_enum.png) exists only inside the producing repo; platform figure endpoint returned 404, so no bytes/hash can be asserted here — metadata + caption quoted from the source instead."
        },
        {
          "asset_id": "A07",
          "asset_class": "module_reference",
          "label": "backend/modules/fueleu_maritime",
          "in_report_section": "FuelEU Maritime 柔性机制三件套成熟化（p120w2-n04 / m7431）",
          "locator": {
            "method": "char_span",
            "start_char": 58,
            "end_char": 89,
            "start_line": 3,
            "end_line": 3,
            "quote": "backend/modules/fueleu_maritime",
            "occurrences": 2,
            "unique": false
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal parsed from the report body (fenced repro block or prose); token normalised for probing (leading '../' dropped, 'backend/' prepended after 'cd backend') while the locator quote keeps the raw source text; existence probed inside the TensorKnowledge delivery worktree (m15626)",
            "result": "unresolved",
            "indicators": {
              "probed_path": "backend/modules/fueleu_maritime",
              "raw_token": "backend/modules/fueleu_maritime",
              "exists_in_worktree": false,
              "found_in": "prose"
            }
          },
          "note": "Declared by the report but absent from the TensorKnowledge worktree: it belongs to the producing repository (ship-performance-platform backend/artifacts tree), which this work package must not touch. Registered as a declared reference; payload not read, no hash claimed."
        },
        {
          "asset_id": "A08",
          "asset_class": "generator_script",
          "label": "artifacts/fueleu_maritime_m7431/run_case.py",
          "in_report_section": "审计链与复现",
          "locator": {
            "method": "char_span",
            "start_char": 7640,
            "end_char": 7686,
            "start_line": 179,
            "end_line": 179,
            "quote": "../artifacts/fueleu_maritime_m7431/run_case.py",
            "occurrences": 1,
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal parsed from the report body (fenced repro block or prose); token normalised for probing (leading '../' dropped, 'backend/' prepended after 'cd backend') while the locator quote keeps the raw source text; existence probed inside the TensorKnowledge delivery worktree (m15626)",
            "result": "unresolved",
            "indicators": {
              "probed_path": "artifacts/fueleu_maritime_m7431/run_case.py",
              "raw_token": "../artifacts/fueleu_maritime_m7431/run_case.py",
              "exists_in_worktree": false,
              "found_in": "fenced_block"
            }
          },
          "note": "Declared by the report but absent from the TensorKnowledge worktree: it belongs to the producing repository (ship-performance-platform backend/artifacts tree), which this work package must not touch. Registered as a declared reference; payload not read, no hash claimed."
        },
        {
          "asset_id": "A09",
          "asset_class": "generator_script",
          "label": "artifacts/fueleu_maritime_m7431/gen_report.py",
          "in_report_section": "审计链与复现",
          "locator": {
            "method": "char_span",
            "start_char": 7714,
            "end_char": 7759,
            "start_line": 180,
            "end_line": 180,
            "quote": "artifacts/fueleu_maritime_m7431/gen_report.py",
            "occurrences": 1,
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal parsed from the report body (fenced repro block or prose); token normalised for probing (leading '../' dropped, 'backend/' prepended after 'cd backend') while the locator quote keeps the raw source text; existence probed inside the TensorKnowledge delivery worktree (m15626)",
            "result": "unresolved",
            "indicators": {
              "probed_path": "artifacts/fueleu_maritime_m7431/gen_report.py",
              "raw_token": "artifacts/fueleu_maritime_m7431/gen_report.py",
              "exists_in_worktree": false,
              "found_in": "fenced_block"
            }
          },
          "note": "Declared by the report but absent from the TensorKnowledge worktree: it belongs to the producing repository (ship-performance-platform backend/artifacts tree), which this work package must not touch. Registered as a declared reference; payload not read, no hash claimed."
        },
        {
          "asset_id": "A10",
          "asset_class": "data_artifact",
          "label": "artifacts/fueleu_maritime_m7431/acceptance.json",
          "in_report_section": "审计链与复现",
          "locator": {
            "method": "char_span",
            "start_char": 7793,
            "end_char": 7840,
            "start_line": 183,
            "end_line": 183,
            "quote": "artifacts/fueleu_maritime_m7431/acceptance.json",
            "occurrences": 1,
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal parsed from the report body (fenced repro block or prose); token normalised for probing (leading '../' dropped, 'backend/' prepended after 'cd backend') while the locator quote keeps the raw source text; existence probed inside the TensorKnowledge delivery worktree (m15626)",
            "result": "unresolved",
            "indicators": {
              "probed_path": "artifacts/fueleu_maritime_m7431/acceptance.json",
              "raw_token": "artifacts/fueleu_maritime_m7431/acceptance.json",
              "exists_in_worktree": false,
              "found_in": "prose"
            }
          },
          "note": "Declared by the report but absent from the TensorKnowledge worktree: it belongs to the producing repository (ship-performance-platform backend/artifacts tree), which this work package must not touch. Registered as a declared reference; payload not read, no hash claimed."
        },
        {
          "asset_id": "A11",
          "asset_class": "figure_collection",
          "label": "artifacts/fueleu_maritime_m7431/figs/",
          "in_report_section": "审计链与复现",
          "locator": {
            "method": "char_span",
            "start_char": 7857,
            "end_char": 7894,
            "start_line": 184,
            "end_line": 184,
            "quote": "artifacts/fueleu_maritime_m7431/figs/",
            "occurrences": 1,
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal parsed from the report body (fenced repro block or prose); token normalised for probing (leading '../' dropped, 'backend/' prepended after 'cd backend') while the locator quote keeps the raw source text; existence probed inside the TensorKnowledge delivery worktree (m15626)",
            "result": "unresolved",
            "indicators": {
              "probed_path": "artifacts/fueleu_maritime_m7431/figs/",
              "raw_token": "artifacts/fueleu_maritime_m7431/figs/",
              "exists_in_worktree": false,
              "found_in": "prose"
            }
          },
          "note": "Declared by the report but absent from the TensorKnowledge worktree: it belongs to the producing repository (ship-performance-platform backend/artifacts tree), which this work package must not touch. Registered as a declared reference; payload not read, no hash claimed."
        },
        {
          "asset_id": "A12",
          "asset_class": "vendor_reference",
          "label": "backend/modules/fueleu_maritime/_m5745_ref/",
          "in_report_section": "审计链与复现",
          "locator": {
            "method": "char_span",
            "start_char": 7934,
            "end_char": 7977,
            "start_line": 185,
            "end_line": 185,
            "quote": "backend/modules/fueleu_maritime/_m5745_ref/",
            "occurrences": 1,
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal parsed from the report body (fenced repro block or prose); token normalised for probing (leading '../' dropped, 'backend/' prepended after 'cd backend') while the locator quote keeps the raw source text; existence probed inside the TensorKnowledge delivery worktree (m15626)",
            "result": "unresolved",
            "indicators": {
              "probed_path": "backend/modules/fueleu_maritime/_m5745_ref/",
              "raw_token": "backend/modules/fueleu_maritime/_m5745_ref/",
              "exists_in_worktree": false,
              "found_in": "prose"
            }
          },
          "note": "Declared by the report but absent from the TensorKnowledge worktree: it belongs to the producing repository (ship-performance-platform backend/artifacts tree), which this work package must not touch. Registered as a declared reference; payload not read, no hash claimed."
        },
        {
          "asset_id": "A13",
          "asset_class": "test_suite",
          "label": "backend/modules/fueleu_maritime/tests",
          "in_report_section": "审计链与复现",
          "locator": {
            "method": "char_span",
            "start_char": 7576,
            "end_char": 7605,
            "start_line": 178,
            "end_line": 178,
            "quote": "modules/fueleu_maritime/tests",
            "occurrences": 1,
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal parsed from the report body (fenced repro block or prose); token normalised for probing (leading '../' dropped, 'backend/' prepended after 'cd backend') while the locator quote keeps the raw source text; existence probed inside the TensorKnowledge delivery worktree (m15626)",
            "result": "unresolved",
            "indicators": {
              "probed_path": "backend/modules/fueleu_maritime/tests",
              "raw_token": "modules/fueleu_maritime/tests",
              "exists_in_worktree": false,
              "found_in": "fenced_block"
            }
          },
          "note": "Declared by the report but absent from the TensorKnowledge worktree: it belongs to the producing repository (ship-performance-platform backend/artifacts tree), which this work package must not touch. Registered as a declared reference; payload not read, no hash claimed."
        },
        {
          "asset_id": "A14",
          "asset_class": "document",
          "label": "PROVENANCE.md",
          "in_report_section": "审计链与复现",
          "locator": {
            "method": "char_span",
            "start_char": 7994,
            "end_char": 8007,
            "start_line": 185,
            "end_line": 185,
            "quote": "PROVENANCE.md",
            "occurrences": 1,
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path literal parsed from the report body (fenced repro block or prose); token normalised for probing (leading '../' dropped, 'backend/' prepended after 'cd backend') while the locator quote keeps the raw source text; existence probed inside the TensorKnowledge delivery worktree (m15626)",
            "result": "unresolved",
            "indicators": {
              "probed_path": "PROVENANCE.md",
              "raw_token": "PROVENANCE.md",
              "exists_in_worktree": false,
              "found_in": "prose"
            }
          },
          "note": "Declared by the report but absent from the TensorKnowledge worktree: it belongs to the producing repository (ship-performance-platform backend/artifacts tree), which this work package must not touch. Registered as a declared reference; payload not read, no hash claimed."
        },
        {
          "asset_id": "A15",
          "asset_class": "cross_report_reference",
          "label": "m5745 reference implementation (regression baseline)",
          "in_report_section": "⑥ 误差判定（关键量 vs 基准，逐项回答是否 < 3%）",
          "locator": {
            "method": "char_span",
            "start_char": 7084,
            "end_char": 7105,
            "start_line": 164,
            "end_line": 164,
            "quote": "m5745 参考实现（逐字 vendor）",
            "occurrences": 1,
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "identifier citation only; no tensor:// URI in the source to resolve against",
            "result": "unresolved"
          },
          "note": "Cross-report dependency: cited as the byte-wise vendored baseline for criterion (b). No URI is given in the source, so it is registered as declared, not fetched."
        },
        {
          "asset_id": "A16",
          "asset_class": "cross_report_reference",
          "label": "m7061 v1.0.0 (previous version, §3.4 diff base)",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 4927,
            "end_char": 4951,
            "start_line": 118,
            "end_line": 118,
            "quote": "与上一版（m7061, v1.0.0）的量化差异",
            "occurrences": 1,
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "identifier citation only; no tensor:// URI in the source to resolve against",
            "result": "unresolved"
          },
          "note": "Cross-report dependency: previous version used as the Δ baseline in §3.4; body only, not resolvable as a file from this worktree."
        }
      ],
      "claims": [],
      "claims_empty_reason": "Contract wp-8753-01 objective is register_assets=true / classify_report_type=false, notes state 'claims 允许为空数组', and constraints include no_forced_claim_generation=true + do_not_mark_claims_as_verified=true. This工序 registers source identity (report_id, markdown byte hash) and the resolvable attachment/artefact inventory; extraction is a downstream工序. An empty claims array is therefore the complete result, not an omission.",
      "id_integrity": {
        "ids_checked": 17,
        "duplicates": [],
        "unique": true
      },
      "observations": [
        "Source identity recomputed from the fetched bytes: sha256:c0ae2fdc7da47e848f0e5eb0379429def3e68bcb299927a7f41d183e4cf07af1, 8187 chars, 12729 UTF-8 bytes, 192 lines; contract hash match=True, contract char match=True.",
        "Document is a complete report: line 1 is the H1 title ('# FuelEU Maritime 柔性机制三件套成熟化（p120w2-n04 / m7431）'); numbered sections present=①②③④⑤⑥, absent=none; 7 '## ' headings in total.",
        "6 figures are declared in the platform record with captions and linked in-body as figs/<name>; GET /tensor/reports/8753/figures/<name> returned [404], so no figure bytes are available from the platform and no figure hash is claimed.",
        "8 distinct body path references were parsed; 8 of them do not exist in this delivery worktree (PROVENANCE.md, artifacts/fueleu_maritime_m7431/acceptance.json, artifacts/fueleu_maritime_m7431/figs/, artifacts/fueleu_maritime_m7431/gen_report.py …).",
        "Registered assets by class: cross_report_reference=2, data_artifact=1, document=1, figure_collection=1, figure_declared=6, generator_script=2, module_reference=1, source_document=1, test_suite=1, vendor_reference=1.",
        "No sibling work package or non-8753 report was read, quoted or modified: the only inputs are report 8753's own record and its markdown bytes."
      ],
      "limitations": [
        "Payload existence was probed only inside the TensorKnowledge worktree and the platform figure endpoint; no access to the producing repository, so 'referenced_unresolved' means 'not resolvable from here', not 'does not exist'.",
        "captions/titles are quoted from platform metadata (record.figures / title), not from the markdown body (the body's figure section carries its own one-line captions).",
        "Schema note: repo-wide schemas/asset_manifest.v1.schema.json hard-pins package_id/report_id/uri with `const` to wp-448-01 and therefore cannot validate this package; the machine check here uses the package-local generic schema written by `schema`."
      ]
    }
  },
  "claims": []
}
```

---
*Generated by kf-worker/m15626 for wp-8753-01 at 2026-11-12T01:33:27+00:00; body rendered from artefacts, zero manual transcription.*
