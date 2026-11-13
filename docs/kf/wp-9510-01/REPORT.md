# KF-RESULT wp-9510-01

**工序**：01-asset-registration（产线 lane B，源 report_id=9510）
**母任务**：mission 18538 · **锚点**：KBM-RCI-F1-FACTORY
**源**：`tensor://reports/9510` 字段 `markdown` · sha256 `sha256:cdc7db83dac16cc900d6a54d14b29f7c59e3288804041be61444d517921ee39c` · 8039 chars / 12580 bytes / 203 行
**产物**：`docs/kf/wp-9510-01/`（asset_manifest.json / kf_result.json / verification.json / source_9510.md 源副本 / figures）
**重开**：原 PR#171（m15660）于 2026-11-05 被 owner 关闭；本包从当前 main 重建（本单=m18538）

## ① 本工序做了什么

只登记、不抽取：以 report 9510 的 markdown 为唯一可信源，在进程内重算字节哈希与字符/行计数，
逐条枚举报告自己声明的附件与工件（图件、脚本、数据工件、模块路径、API 路由、外部法规文本），
并给每条资产一个可在原文逐字复算的定位符（行号 + 字符区间 + 原文整行 + 全局唯一性）。
报告类型分类、知识抽取、`verified` 标记一律不做（契约 objective.classify_report_type=false；
verification 由平台门独立重算）。`claims` 为空数组并写明理由（契约允许）。

- 登记资产总数：**26**（按类别 `{"api_endpoint_reference": 1, "code_directory": 2, "code_symbol_reference": 1, "data_artifact": 5, "external_standard_reference": 5, "figure": 5, "source_document": 1, "source_module": 5, "test_module": 1}`）
- 按解析状态：`{"referenced_unresolved": 25, "resolved_in_source": 1}`（其中 `resolved_in_source`=1，`referenced_unresolved`=25）
- 源指纹一致性：hash=一致 / chars=一致 / title=一致 / scenario=一致

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`GET /api/v1/tensor/reports/9510`（Bearer token 由 `POST /api/v1/auth/login` 取得）。
   直接 `psql -d tensorplatform -c "select markdown from tensor_reports where id=9510"` 被拒
   （`permission denied for table tensor_reports`），故唯一取数信道是认证 API；源副本落 `docs/kf/wp-9510-01/source_9510.md`。
2. **重算指纹**：`hashlib.sha256(markdown.encode('utf-8'))` → `sha256:cdc7db83dac16cc900d6a54d14b29f7c59e3288804041be61444d517921ee39c`；
   与契约 `sha256:cdc7db83dac16cc900d6a54d14b29f7c59e3288804041be61444d517921ee39c` 比对（一致），`len(markdown)`=8039 与契约 chars=8039 比对（一致）。
3. **扫描声明**（3 类正则，纯静态，不执行报告里的任何代码）：
   markdown 图链正则抓 `![](path)`；反引号令牌仅当"无空白 且 (含目录分隔符 或 已知工件后缀)"才算路径
   （模块名如 `regulatory`/`chain`/`NOT_SUPPORTED` 因此被排除，不把符号当文件）；IMO 决议号正则抓 `MEPC.x(yy)` / `MEPC.1/Circ.n`。
   按首次出现顺序去重编号 A01…A26。
4. **定位符**：行号 + `start_char/end_char`（由前序行长度累加）+ 该行原文整行 + `unique`（原文出现次数==1）。
   verify 阶段对每条定位符重算 `markdown[start:end]==quote` 与 `lines[line-1]==quote` 与子串存在性。
5. **解析判定**：路径在本交付工作树 `Path.exists` → `resolved_in_source`；否则 `referenced_unresolved`
   （报告声明但字节属于 ship-performance-platform 仓，本工作树不可达，绝不冒充已取得）。
   图件另用 `GET /tensor/reports/9510/figures/{name}` 探测平台字节，并把重算 sha256 与报告正文里声明的
   **截断 sha256 前缀**逐位对照（结果见 ④）。
6. **封装**：`kf_result.v1` 信封（package_id/task_type/report_id/provenance/outputs/claims）；
   `provenance.source_hash` 在封装阶段**重新取数重算**，与 manifest 不一致即中止（防陈旧哈希）。
7. **自检**：`jsonschema` 双 schema 校验（`schemas/kf_result.v1.schema.json` + `schemas/asset_manifest.v1.schema.json`），
   再逐条机器判 6 项 acceptance（结果见 ⑥）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-9510-01/asset_manifest.json` | 26 条资产登记；源指纹 `sha256:cdc7db83dac16cc900d6a54d14b29f7c59e3288804041be61444d517921ee39c`；每资产带行号/字符区间/原文整行/唯一性 |
| `docs/kf/wp-9510-01/kf_result.json` | 工序结果信封（本报告唯一 json 代码块的来源）；`outputs.asset_manifest.json` = 上述 manifest 全文 |
| `docs/kf/wp-9510-01/verification.json` | 6 项 acceptance 自检（`all_ok=True`） |
| `docs/kf/wp-9510-01/figures/wp-9510-01_source_locator_map.png` | 定位符分布图：行剖面 + 资产类别×解析状态直方图；sha256 `sha256:f69091c3cc4df1fbbd12d8f122b900243d78e4c07439f06a1cc5902e6551b73b` |
| `docs/kf/wp-9510-01/REPORT.md` | 本报告 |
| `docs/kf/wp-9510-01/source_9510.md` | 源 markdown 原样副本（12580 bytes，供离线复算；放 docs/ 因推送门禁滤除 runs/**） |
| `runs/wp-9510-01/report.json` | 发平台载荷（含图件 base64；运行记录，不入库） |
| `scripts/kf_wp9510_01_register_assets.py` / `scripts/kf_wp9510_01_report.py` | 可复跑流水线（build/envelope/verify/figure/report/publish） |
| `tests/test_kf_wp9510_01.py` | 离线回归测试（定位符/哈希/唯一 id/单 json 块/schema 向后兼容） |

## ④ 证据定位表（资产 → 原文整行引文，逐字可复算）

| 资产 | 类别 | 行 | 解析 | 原文整行（逐字引文，仅两处显示变换：`|`→`/` 以保证表格不被切断、超 96 字符截断加 `…`；已做显示变换的引文可在 manifest 的 locator.quote 取全文逐字本） |
|---|---|---|---|---|
| A01 | source_document | L1 | `resolved_in_source` | # P155W1-N02 绿色航行法规合规验证面成熟化：EEXI / CII / EEDI 计算链与 IMO 决议一致性 |
| A02 | code_directory | L5 | `referenced_unresolved` | **工件**：`artifacts/P155W1-N02/`（`compliance.sqlite`、`results.json`、`queries.sql`、5 张图） |
| A03 | data_artifact | L5 | `referenced_unresolved` | **工件**：`artifacts/P155W1-N02/`（`compliance.sqlite`、`results.json`、`queries.sql`、5 张图） |
| A04 | data_artifact | L5 | `referenced_unresolved` | **工件**：`artifacts/P155W1-N02/`（`compliance.sqlite`、`results.json`、`queries.sql`、5 张图） |
| A05 | data_artifact | L5 | `referenced_unresolved` | **工件**：`artifacts/P155W1-N02/`（`compliance.sqlite`、`results.json`、`queries.sql`、5 张图） |
| A06 | source_module | L6 | `referenced_unresolved` | **文档数字**：全部由 `make_report.py` 从 SQL 注入，零手抄（可 `sqlite3 < queries.sql` 逐条复算）。 |
| A07 | external_standard_reference | L12 | `referenced_unresolved` | IMO 在 MEPC.328(76) 下把"能效"从设计（EEDI）扩到在役（EEXI）与营运（CII）， |
| A08 | code_directory | L33 | `referenced_unresolved` | 1. **新建模块** `backend/modules/green_compliance/`：`regulatory`（规则系数单一转录源 + 证据分级 + |
| A09 | api_endpoint_reference | L35 | `referenced_unresolved` |    `sensitivity`（阶 4）、`api`（6 个端点，挂 `/api/v1/green-shipping/compliance/*`）。 |
| A10 | source_module | L36 | `referenced_unresolved` | 2. **接线旧端点** `backend/api/green_shipping.py`：修复两处缺陷（见 ⑤），CII 评级从 |
| A11 | external_standard_reference | L40 | `referenced_unresolved` |    * 两条独立路径互证：功率-小时路径 vs 燃油量-航程路径（后者即 EEOI，MEPC.1/Circ.684）； |
| A12 | source_module | L43 | `referenced_unresolved` |    * 三处既有实现（`green_compliance` / `green_shipping` / `green_navigation_ice.mepc`） |
| A13 | source_module | L46 | `referenced_unresolved` | 4. **工件链**：`run_compliance.py` 一次跑完全部案例 → 204 行 metric 写入 `compliance.sqlite` |
| A14 | data_artifact | L47 | `referenced_unresolved` |    → `make_report.py` 用 SQL 取数生成本报告 → `report.json` 内嵌图件 base64 发平台。 |
| A15 | external_standard_reference | L80 | `referenced_unresolved` | 评级边界（MEPC.354(78) dd 向量 (0.86, 0.94, 1.06, 1.18)，`grade = #{i : attained > dd_i·required}`）， |
| A16 | figure | L128 | `referenced_unresolved` | ![EEXI 达到值与要求值对比：遗留设计超标 82%，经济型设计需 EPL，限功率后达标](../artifacts/P155W1-N02/fig1_eexi_attained_vs_req… |
| A17 | figure | L132 | `referenced_unresolved` | ![EPL 限功率扫描：EEXI ∝ MCR′^(2/3)，交点给出达标限值（航速损失显式标注）](../artifacts/P155W1-N02/fig2_epl_path.png) |
| A18 | figure | L136 | `referenced_unresolved` | ![CII 等级带随 2023–2026 年度折减收紧；A 船由 C 降到 D，B 船稳定在 B](../artifacts/P155W1-N02/fig3_cii_rating_bands.… |
| A19 | figure | L140 | `referenced_unresolved` | ![左：EEXI 网格（弹性 +1 / −1）；右：CII 等级跳变（弹性 +1 / +2）](../artifacts/P155W1-N02/fig4_sensitivity.png) |
| A20 | figure | L144 | `referenced_unresolved` | ![EEDI 阶段时间线对比：C 船满足 Phase 2 但不满足 Phase 3（EEXI 20% < EEDI 30%）](../artifacts/P155W1-N02/fig5_eed… |
| A21 | code_symbol_reference | L157 | `referenced_unresolved` | **缺陷 D1（已修，严重）**：`api/green_shipping._gn_attained_index` 旧实现分母写 |
| A22 | test_module | L163 | `referenced_unresolved` | （本节点已在 `test_green_shipping.py` 补物理量级断言 + 独立手算断言）。 |
| A23 | external_standard_reference | L175 | `referenced_unresolved` | 2. **未取得 IMO 数值算例原文**（MEPC.333(76) 附例等），因此"与指南示例 ≤1%"判据以 |
| A24 | external_standard_reference | L191 | `referenced_unresolved` | / C_F 化学计量导出 vs MEPC.364(79) 公布值（最差燃料） / 0.248 % / 是 / REAL / |
| A25 | source_module | L202 | `referenced_unresolved` | 生成：`artifacts/P155W1-N02/make_report.py`（SQL → markdown，零手抄）； |
| A26 | data_artifact | L203 | `referenced_unresolved` | 数据：`artifacts/P155W1-N02/compliance.sqlite`（204 行 metric / 5 张图）。 |

平台图件字节探测（`GET /tensor/reports/9510/figures/{name}`）：探测 5 个名字，HTTP 200 且有字节 = 0；状态分布 `{"404": 5}`

| 图件 | HTTP | bytes | 重算 sha256（若 200） |
|---|---|---|---|
| `fig1_eexi_attained_vs_required.png` | 404 | 29 | —（无字节） |
| `fig2_epl_path.png` | 404 | 29 | —（无字节） |
| `fig3_cii_rating_bands.png` | 404 | 29 | —（无字节） |
| `fig4_sensitivity.png` | 404 | 29 | —（无字节） |
| `fig5_eedi_timeline.png` | 404 | 29 | —（无字节） |

关键定位符举例（可在 `docs/kf/wp-9510-01/source_9510.md` 上 `grep -n` 复核）：

- 源身份 L1：`# P155W1-N02 绿色航行法规合规验证面成熟化：EEXI / CII / EEDI 计算链与 IMO 决议一致性`
- 工件链声明 L5：`**工件**：`artifacts/P155W1-N02/`（`compliance.sqlite`、`results.json`、`queries.sql`、5 张图）`
- 工具链 L46：`4. **工件链**：`run_compliance.py` 一次跑完全部案例 → 204 行 metric 写入 `compliance.sqlite``

## ⑤ 注意点与局限

1. **只登记不抽取**：本工序无任何 claim/知识对象；`claims: []` 是契约允许的完整结果，不是遗漏。
2. **引用≠取得**：`compliance.sqlite` / `results.json` / `queries.sql` / `run_compliance.py` / `make_report.py` /
   5 张图 / `backend/modules/green_compliance/` 等路径属于 ship-performance-platform（节点 P155W1-N02），
   在 TensorKnowledge 交付工作树内不可达，故一律 `referenced_unresolved` 且 `existence_asserted_by_worker=false`；
   本工序不对这些字节做任何哈希声明。
3. **图件字节不可得**：5 个图件名在平台图件端点 `GET /tensor/reports/9510/figures/{name}` 上全部返回 HTTP 404，因此报告正文里的截断 sha256 前缀
   **无法**核对，图件停留 `referenced_unresolved`——这是如实记录，不是验证通过。
4. **同一文件两名**：如 A06 `make_report.py` 与 A25 `artifacts/P155W1-N02/make_report.py` 是两处不同文本引用，
   登记为两条资产并用 `same_basename_as` 互指，不做主观合并（合并会丢原文位置）。
5. **哈希口径**：sha256 作用域是平台返回 markdown 字符串的 UTF-8 字节；存储侧任何改动（含空白）都会使本 manifest 失效。
   `tensor_reports.markdown` 直读被权限拒绝，来源只能是 API。
6. **引文显示变换**：④ 表内原文整行只做两处显示变换（`|`→`/` 保表格、超 96 字符截断加 `…`），逐字全文在 `asset_manifest.json` 的 `locator.quote`；
   verify 对全文（非截断）做字符区间 + 行 + 子串三重比对。
7. **保留上游不确定性**：报告 §⑤ 自述规则系数为转录值、要求值/等级判 WITHHELD、未取得 IMO 数值算例原文；
   本工序只登记、不改写这些不确定性，也不把它们升格为结论。
8. **未做**：报告类型分类（契约关）、知识抽取（下游工序 03）、`verified` 标记（平台门职责）、读写其它 report_id。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 实测依据 |
|---|---|---|
| `valid_json` | PASS | asset_manifest.json + kf_result.json parse as JSON objects |
| `schema_pass` | PASS | {"kf_result.v1": {"schema_file": "schemas/kf_result.v1.schema.json", "error_count": 0, "errors": []}, "asset_manifest.v1": {"schema_file": "schemas/asset_manifest.v1.schema.json", "error_count": 0, "e… |
| `source_locator_resolvable` | PASS | 26/26 locators re-resolved (verbatim line + char-span identity + substring) |
| `source_hash_matches` | PASS | live=sha256:cdc7db83dac16cc900d6a54d14b29f7c59e3288804041be61444d517921ee39c manifest=sha256:cdc7db83dac16cc900d6a54d14b29f7c59e3288804041be61444d517921ee39c contract=sha256:cdc7db83dac16cc900d6a54d14… |
| `no_duplicate_ids` | PASS | 26 asset ids, duplicates=[] |
| `all_claims_have_evidence_or_explicit_unresolved_status` | PASS | 0 claims (empty allowed by contract; reason stated=True); 25 assets carry an explicit non-resolved status: A02,A03,A04,A05,A06,A07,A08,A09,A10,A11,A12,A13,A14,A15,A16,A17,A18,A19,A20,A21,A22,A23,A24,A… |

**结论**：6 项 acceptance 全部由机器判定通过（`all_ok=True`）。
"通过"仅指本工序的结构/定位/哈希/唯一性自检通过，**不代表**任何科学结论被验证；
报告中 WITHHELD 的量仍为 WITHHELD；图件与仓外工件仍为 `referenced_unresolved`。

### 一键复跑（`repro_cmd`）

在工作树根目录依次执行（需 `TENSOR_API_BASE` / `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS`）：

    python3 scripts/kf_wp9510_01_register_assets.py all
    python3 scripts/kf_wp9510_01_report.py build
    python3 -m pytest tests/test_kf_wp9510_01.py -q

（`all` 会重新取源并重算哈希；源未变时除时间戳外产物逐字节一致。`publish` 另发报告，不参与复算。）

### 结果 JSON（唯一 json 代码块，原样来自 kf_result.json）

```json
{
  "package_id": "wp-9510-01",
  "task_type": "01-asset-registration",
  "contract_version": "1.0",
  "report_id": "9510",
  "provenance": {
    "source_uri": "tensor://reports/9510",
    "source_field": "markdown",
    "source_hash": "sha256:cdc7db83dac16cc900d6a54d14b29f7c59e3288804041be61444d517921ee39c",
    "source_hash_matches": true,
    "title": "P155W1-N02 绿色航行法规合规验证面成熟化（EEXI/CII/EEDI 全链 + 两处缺陷修复）",
    "scenario_key": "green_navigation_regulatory_compliance",
    "chars": 8039
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "manifest_version": "1.0",
      "package_id": "wp-9510-01",
      "task_type": "01-asset-registration",
      "report_id": "9510",
      "lane": "B",
      "generated_at": "2026-11-13T15:10:25.993644+00:00",
      "producer": "agent/m18538",
      "source": {
        "uri": "tensor://reports/9510",
        "report_id": "9510",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "cdc7db83dac16cc900d6a54d14b29f7c59e3288804041be61444d517921ee39c",
        "hash_prefixed": "sha256:cdc7db83dac16cc900d6a54d14b29f7c59e3288804041be61444d517921ee39c",
        "chars": 8039,
        "bytes_utf8": 12580,
        "lines": 203,
        "title": "P155W1-N02 绿色航行法规合规验证面成熟化（EEXI/CII/EEDI 全链 + 两处缺陷修复）",
        "scenario_key": "green_navigation_regulatory_compliance",
        "mission_id": 8243,
        "platform_tags": [
          "EEXI",
          "CII",
          "EEDI",
          "MEPC.328(76)",
          "MEPC.354(78)",
          "缺陷修复",
          "法规合规"
        ],
        "platform_figures": [
          "fig1_eexi_attained_vs_required.png",
          "fig2_epl_path.png",
          "fig3_cii_rating_bands.png",
          "fig4_sensitivity.png",
          "fig5_eedi_timeline.png"
        ],
        "fetched_via": "GET /api/v1/tensor/reports/9510",
        "local_copy": "docs/kf/wp-9510-01/source_9510.md",
        "hash_scope": "UTF-8 bytes of the markdown string as served by the platform API",
        "contract": {
          "source_hash": "sha256:cdc7db83dac16cc900d6a54d14b29f7c59e3288804041be61444d517921ee39c",
          "chars": 8039,
          "title": "P155W1-N02 绿色航行法规合规验证面成熟化（EEXI/CII/EEDI 全链 + 两处缺陷修复）",
          "scenario_key": "green_navigation_regulatory_compliance",
          "hash_matches": true,
          "chars_matches": true,
          "title_matches": true,
          "scenario_matches": true
        }
      },
      "counts": {
        "assets": 26,
        "by_class": {
          "api_endpoint_reference": 1,
          "code_directory": 2,
          "code_symbol_reference": 1,
          "data_artifact": 5,
          "external_standard_reference": 5,
          "figure": 5,
          "source_document": 1,
          "source_module": 5,
          "test_module": 1
        },
        "by_resolution": {
          "referenced_unresolved": 25,
          "resolved_in_source": 1
        },
        "resolved_in_source": 1,
        "referenced_unresolved": 25,
        "declared_absent": 0,
        "char_spans_verified": 25
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "source_document",
          "label": "report 9510 markdown (source of truth for this package)",
          "in_report_section": "(preamble)",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 8039,
            "start_line": 1,
            "end_line": 203,
            "quote": "# P155W1-N02 绿色航行法规合规验证面成熟化：EEXI / CII / EEDI 计算链与 IMO 决议一致性",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET /tensor/reports/9510 markdown re-hashed in-process; local copy docs/kf/wp-9510-01/source_9510.md",
            "result": "resolved"
          },
          "locator_scope": "whole document: quote = H1 title line (verbatim anchor), char span covers the entire markdown",
          "note": "sha256 sha256:cdc7db83dac16cc900d6a54d14b29f7c59e3288804041be61444d517921ee39c, 8039 chars / 12580 UTF-8 bytes, 203 lines; contract hash match=True, contract chars match=True"
        },
        {
          "asset_id": "A02",
          "asset_class": "code_directory",
          "label": "artifacts/P155W1-N02/",
          "in_report_section": "(preamble)",
          "locator": {
            "method": "char_span",
            "start_char": 172,
            "end_char": 257,
            "start_line": 5,
            "end_line": 5,
            "quote": "**工件**：`artifacts/P155W1-N02/`（`compliance.sqlite`、`results.json`、`queries.sql`、5 张图）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(artifacts/P155W1-N02/)",
            "result": "unresolved"
          },
          "note": "first occurrence L5 in (preamble) (backtick_path)",
          "declared_reference_form": "backtick_path",
          "also_referenced_on_lines": [],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A03",
          "asset_class": "data_artifact",
          "label": "compliance.sqlite",
          "in_report_section": "(preamble)",
          "locator": {
            "method": "char_span",
            "start_char": 172,
            "end_char": 257,
            "start_line": 5,
            "end_line": 5,
            "quote": "**工件**：`artifacts/P155W1-N02/`（`compliance.sqlite`、`results.json`、`queries.sql`、5 张图）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(compliance.sqlite)",
            "result": "unresolved"
          },
          "note": "first occurrence L5 in (preamble) (backtick_path)",
          "declared_reference_form": "backtick_path",
          "also_referenced_on_lines": [
            46
          ],
          "existence_asserted_by_worker": false,
          "same_basename_as": [
            "A26"
          ]
        },
        {
          "asset_id": "A04",
          "asset_class": "data_artifact",
          "label": "results.json",
          "in_report_section": "(preamble)",
          "locator": {
            "method": "char_span",
            "start_char": 172,
            "end_char": 257,
            "start_line": 5,
            "end_line": 5,
            "quote": "**工件**：`artifacts/P155W1-N02/`（`compliance.sqlite`、`results.json`、`queries.sql`、5 张图）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(results.json)",
            "result": "unresolved"
          },
          "note": "first occurrence L5 in (preamble) (backtick_path)",
          "declared_reference_form": "backtick_path",
          "also_referenced_on_lines": [],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A05",
          "asset_class": "data_artifact",
          "label": "queries.sql",
          "in_report_section": "(preamble)",
          "locator": {
            "method": "char_span",
            "start_char": 172,
            "end_char": 257,
            "start_line": 5,
            "end_line": 5,
            "quote": "**工件**：`artifacts/P155W1-N02/`（`compliance.sqlite`、`results.json`、`queries.sql`、5 张图）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(queries.sql)",
            "result": "unresolved"
          },
          "note": "first occurrence L5 in (preamble) (backtick_path)",
          "declared_reference_form": "backtick_path",
          "also_referenced_on_lines": [],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A06",
          "asset_class": "source_module",
          "label": "make_report.py",
          "in_report_section": "(preamble)",
          "locator": {
            "method": "char_span",
            "start_char": 258,
            "end_char": 333,
            "start_line": 6,
            "end_line": 6,
            "quote": "**文档数字**：全部由 `make_report.py` 从 SQL 注入，零手抄（可 `sqlite3 < queries.sql` 逐条复算）。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(make_report.py)",
            "result": "unresolved"
          },
          "note": "first occurrence L6 in (preamble) (backtick_path)",
          "declared_reference_form": "backtick_path",
          "also_referenced_on_lines": [
            47
          ],
          "existence_asserted_by_worker": false,
          "same_basename_as": [
            "A25"
          ]
        },
        {
          "asset_id": "A07",
          "asset_class": "external_standard_reference",
          "label": "MEPC.328(76)",
          "in_report_section": "## ① 案例介绍（物理背景 / 几何 / 参数表）",
          "locator": {
            "method": "char_span",
            "start_char": 368,
            "end_char": 421,
            "start_line": 12,
            "end_line": 12,
            "quote": "IMO 在 MEPC.328(76) 下把\"能效\"从设计（EEDI）扩到在役（EEXI）与营运（CII），",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(MEPC.328(76))",
            "result": "unresolved"
          },
          "note": "first occurrence L12 in ## ① 案例介绍（物理背景 / 几何 / 参数表） (prose_identifier)",
          "declared_reference_form": "prose_identifier",
          "also_referenced_on_lines": [],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A08",
          "asset_class": "code_directory",
          "label": "backend/modules/green_compliance/",
          "in_report_section": "## ② 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1199,
            "end_char": 1278,
            "start_line": 33,
            "end_line": 33,
            "quote": "1. **新建模块** `backend/modules/green_compliance/`：`regulatory`（规则系数单一转录源 + 证据分级 +",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(backend/modules/green_compliance/)",
            "result": "unresolved"
          },
          "note": "first occurrence L33 in ## ② 怎么做的（方法 / 流程 / 工具链） (backtick_path)",
          "declared_reference_form": "backtick_path",
          "also_referenced_on_lines": [],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A09",
          "asset_class": "api_endpoint_reference",
          "label": "/api/v1/green-shipping/compliance/*",
          "in_report_section": "## ② 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1346,
            "end_char": 1421,
            "start_line": 35,
            "end_line": 35,
            "quote": "   `sensitivity`（阶 4）、`api`（6 个端点，挂 `/api/v1/green-shipping/compliance/*`）。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(/api/v1/green-shipping/compliance/*)",
            "result": "unresolved"
          },
          "note": "first occurrence L35 in ## ② 怎么做的（方法 / 流程 / 工具链） (backtick_path)",
          "declared_reference_form": "backtick_path",
          "also_referenced_on_lines": [],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A10",
          "asset_class": "source_module",
          "label": "backend/api/green_shipping.py",
          "in_report_section": "## ② 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1422,
            "end_char": 1486,
            "start_line": 36,
            "end_line": 36,
            "quote": "2. **接线旧端点** `backend/api/green_shipping.py`：修复两处缺陷（见 ⑤），CII 评级从",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(backend/api/green_shipping.py)",
            "result": "unresolved"
          },
          "note": "first occurrence L36 in ## ② 怎么做的（方法 / 流程 / 工具链） (backtick_path)",
          "declared_reference_form": "backtick_path",
          "also_referenced_on_lines": [],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A11",
          "asset_class": "external_standard_reference",
          "label": "MEPC.1/Circ.684",
          "in_report_section": "## ② 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1610,
            "end_char": 1670,
            "start_line": 40,
            "end_line": 40,
            "quote": "   * 两条独立路径互证：功率-小时路径 vs 燃油量-航程路径（后者即 EEOI，MEPC.1/Circ.684）；",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(MEPC.1/Circ.684)",
            "result": "unresolved"
          },
          "note": "first occurrence L40 in ## ② 怎么做的（方法 / 流程 / 工具链） (prose_identifier)",
          "declared_reference_form": "prose_identifier",
          "also_referenced_on_lines": [],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A12",
          "asset_class": "source_module",
          "label": "green_navigation_ice.mepc",
          "in_report_section": "## ② 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1765,
            "end_char": 1845,
            "start_line": 43,
            "end_line": 43,
            "quote": "   * 三处既有实现（`green_compliance` / `green_shipping` / `green_navigation_ice.mepc`）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(green_navigation_ice.mepc)",
            "result": "unresolved"
          },
          "note": "first occurrence L43 in ## ② 怎么做的（方法 / 流程 / 工具链） (backtick_path)",
          "declared_reference_form": "backtick_path",
          "also_referenced_on_lines": [],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A13",
          "asset_class": "source_module",
          "label": "run_compliance.py",
          "in_report_section": "## ② 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 1976,
            "end_char": 2053,
            "start_line": 46,
            "end_line": 46,
            "quote": "4. **工件链**：`run_compliance.py` 一次跑完全部案例 → 204 行 metric 写入 `compliance.sqlite`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(run_compliance.py)",
            "result": "unresolved"
          },
          "note": "first occurrence L46 in ## ② 怎么做的（方法 / 流程 / 工具链） (backtick_path)",
          "declared_reference_form": "backtick_path",
          "also_referenced_on_lines": [
            153
          ],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A14",
          "asset_class": "data_artifact",
          "label": "report.json",
          "in_report_section": "## ② 怎么做的（方法 / 流程 / 工具链）",
          "locator": {
            "method": "char_span",
            "start_char": 2054,
            "end_char": 2122,
            "start_line": 47,
            "end_line": 47,
            "quote": "   → `make_report.py` 用 SQL 取数生成本报告 → `report.json` 内嵌图件 base64 发平台。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(report.json)",
            "result": "unresolved"
          },
          "note": "first occurrence L47 in ## ② 怎么做的（方法 / 流程 / 工具链） (backtick_path)",
          "declared_reference_form": "backtick_path",
          "also_referenced_on_lines": [],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A15",
          "asset_class": "external_standard_reference",
          "label": "MEPC.354(78)",
          "in_report_section": "### 3.2 阶 2 — CII 年度值 + A–E 评级",
          "locator": {
            "method": "char_span",
            "start_char": 3174,
            "end_char": 3266,
            "start_line": 80,
            "end_line": 80,
            "quote": "评级边界（MEPC.354(78) dd 向量 (0.86, 0.94, 1.06, 1.18)，`grade = #{i : attained > dd_i·required}`），",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(MEPC.354(78))",
            "result": "unresolved"
          },
          "note": "first occurrence L80 in ### 3.2 阶 2 — CII 年度值 + A–E 评级 (prose_identifier)",
          "declared_reference_form": "prose_identifier",
          "also_referenced_on_lines": [],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A16",
          "asset_class": "figure",
          "label": "artifacts/P155W1-N02/fig1_eexi_attained_vs_required.png",
          "in_report_section": "### 3.5 图件",
          "locator": {
            "method": "char_span",
            "start_char": 4577,
            "end_char": 4683,
            "start_line": 128,
            "end_line": 128,
            "quote": "![EEXI 达到值与要求值对比：遗留设计超标 82%，经济型设计需 EPL，限功率后达标](../artifacts/P155W1-N02/fig1_eexi_attained_vs_required.png)",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(artifacts/P155W1-N02/fig1_eexi_attained_vs_required.png)",
            "result": "unresolved"
          },
          "note": "first occurrence L128 in ### 3.5 图件 (markdown_image); platform figure probe HTTP 404, 29 bytes -> no payload, no hash claimed",
          "declared_reference_form": "markdown_image",
          "also_referenced_on_lines": [
            130
          ],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A17",
          "asset_class": "figure",
          "label": "artifacts/P155W1-N02/fig2_epl_path.png",
          "in_report_section": "### 3.5 图件",
          "locator": {
            "method": "char_span",
            "start_char": 4818,
            "end_char": 4910,
            "start_line": 132,
            "end_line": 132,
            "quote": "![EPL 限功率扫描：EEXI ∝ MCR′^(2/3)，交点给出达标限值（航速损失显式标注）](../artifacts/P155W1-N02/fig2_epl_path.png)",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(artifacts/P155W1-N02/fig2_epl_path.png)",
            "result": "unresolved"
          },
          "note": "first occurrence L132 in ### 3.5 图件 (markdown_image); platform figure probe HTTP 404, 29 bytes -> no payload, no hash claimed",
          "declared_reference_form": "markdown_image",
          "also_referenced_on_lines": [
            134
          ],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A18",
          "asset_class": "figure",
          "label": "artifacts/P155W1-N02/fig3_cii_rating_bands.png",
          "in_report_section": "### 3.5 图件",
          "locator": {
            "method": "char_span",
            "start_char": 5031,
            "end_char": 5131,
            "start_line": 136,
            "end_line": 136,
            "quote": "![CII 等级带随 2023–2026 年度折减收紧；A 船由 C 降到 D，B 船稳定在 B](../artifacts/P155W1-N02/fig3_cii_rating_bands.png)",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(artifacts/P155W1-N02/fig3_cii_rating_bands.png)",
            "result": "unresolved"
          },
          "note": "first occurrence L136 in ### 3.5 图件 (markdown_image); platform figure probe HTTP 404, 29 bytes -> no payload, no hash claimed",
          "declared_reference_form": "markdown_image",
          "also_referenced_on_lines": [
            138
          ],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A19",
          "asset_class": "figure",
          "label": "artifacts/P155W1-N02/fig4_sensitivity.png",
          "in_report_section": "### 3.5 图件",
          "locator": {
            "method": "char_span",
            "start_char": 5260,
            "end_char": 5353,
            "start_line": 140,
            "end_line": 140,
            "quote": "![左：EEXI 网格（弹性 +1 / −1）；右：CII 等级跳变（弹性 +1 / +2）](../artifacts/P155W1-N02/fig4_sensitivity.png)",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(artifacts/P155W1-N02/fig4_sensitivity.png)",
            "result": "unresolved"
          },
          "note": "first occurrence L140 in ### 3.5 图件 (markdown_image); platform figure probe HTTP 404, 29 bytes -> no payload, no hash claimed",
          "declared_reference_form": "markdown_image",
          "also_referenced_on_lines": [
            142
          ],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A20",
          "asset_class": "figure",
          "label": "artifacts/P155W1-N02/fig5_eedi_timeline.png",
          "in_report_section": "### 3.5 图件",
          "locator": {
            "method": "char_span",
            "start_char": 5475,
            "end_char": 5586,
            "start_line": 144,
            "end_line": 144,
            "quote": "![EEDI 阶段时间线对比：C 船满足 Phase 2 但不满足 Phase 3（EEXI 20% < EEDI 30%）](../artifacts/P155W1-N02/fig5_eedi_timeline.png)",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(artifacts/P155W1-N02/fig5_eedi_timeline.png)",
            "result": "unresolved"
          },
          "note": "first occurrence L144 in ### 3.5 图件 (markdown_image); platform figure probe HTTP 404, 29 bytes -> no payload, no hash claimed",
          "declared_reference_form": "markdown_image",
          "also_referenced_on_lines": [
            146
          ],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A21",
          "asset_class": "code_symbol_reference",
          "label": "api/green_shipping._gn_attained_index",
          "in_report_section": "## ⑤ 注意点（踩坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 5949,
            "end_char": 6012,
            "start_line": 157,
            "end_line": 157,
            "quote": "**缺陷 D1（已修，严重）**：`api/green_shipping._gn_attained_index` 旧实现分母写",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(api/green_shipping._gn_attained_index)",
            "result": "unresolved"
          },
          "note": "first occurrence L157 in ## ⑤ 注意点（踩坑 / 局限 / 适用范围） (backtick_path)",
          "declared_reference_form": "backtick_path",
          "also_referenced_on_lines": [],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A22",
          "asset_class": "test_module",
          "label": "test_green_shipping.py",
          "in_report_section": "## ⑤ 注意点（踩坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 6246,
            "end_char": 6296,
            "start_line": 163,
            "end_line": 163,
            "quote": "（本节点已在 `test_green_shipping.py` 补物理量级断言 + 独立手算断言）。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(test_green_shipping.py)",
            "result": "unresolved"
          },
          "note": "first occurrence L163 in ## ⑤ 注意点（踩坑 / 局限 / 适用范围） (backtick_path)",
          "declared_reference_form": "backtick_path",
          "also_referenced_on_lines": [],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A23",
          "asset_class": "external_standard_reference",
          "label": "MEPC.333(76)",
          "in_report_section": "## ⑤ 注意点（踩坑 / 局限 / 适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 6671,
            "end_char": 6727,
            "start_line": 175,
            "end_line": 175,
            "quote": "2. **未取得 IMO 数值算例原文**（MEPC.333(76) 附例等），因此\"与指南示例 ≤1%\"判据以",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(MEPC.333(76))",
            "result": "unresolved"
          },
          "note": "first occurrence L175 in ## ⑤ 注意点（踩坑 / 局限 / 适用范围） (prose_identifier)",
          "declared_reference_form": "prose_identifier",
          "also_referenced_on_lines": [
            196
          ],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A24",
          "asset_class": "external_standard_reference",
          "label": "MEPC.364(79)",
          "in_report_section": "## ⑥ 误差判定（逐项，是否 <3%）",
          "locator": {
            "method": "char_span",
            "start_char": 7353,
            "end_char": 7414,
            "start_line": 191,
            "end_line": 191,
            "quote": "| C_F 化学计量导出 vs MEPC.364(79) 公布值（最差燃料） | 0.248 % | 是 | REAL |",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(MEPC.364(79))",
            "result": "unresolved"
          },
          "note": "first occurrence L191 in ## ⑥ 误差判定（逐项，是否 <3%） (prose_identifier)",
          "declared_reference_form": "prose_identifier",
          "also_referenced_on_lines": [],
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "A25",
          "asset_class": "source_module",
          "label": "artifacts/P155W1-N02/make_report.py",
          "in_report_section": "## ⑥ 误差判定（逐项，是否 <3%）",
          "locator": {
            "method": "char_span",
            "start_char": 7911,
            "end_char": 7972,
            "start_line": 202,
            "end_line": 202,
            "quote": "生成：`artifacts/P155W1-N02/make_report.py`（SQL → markdown，零手抄）；",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(artifacts/P155W1-N02/make_report.py)",
            "result": "unresolved"
          },
          "note": "first occurrence L202 in ## ⑥ 误差判定（逐项，是否 <3%） (backtick_path)",
          "declared_reference_form": "backtick_path",
          "also_referenced_on_lines": [],
          "existence_asserted_by_worker": false,
          "same_basename_as": [
            "A06"
          ]
        },
        {
          "asset_id": "A26",
          "asset_class": "data_artifact",
          "label": "artifacts/P155W1-N02/compliance.sqlite",
          "in_report_section": "## ⑥ 误差判定（逐项，是否 <3%）",
          "locator": {
            "method": "char_span",
            "start_char": 7973,
            "end_char": 8038,
            "start_line": 203,
            "end_line": 203,
            "quote": "数据：`artifacts/P155W1-N02/compliance.sqlite`（204 行 metric / 5 张图）。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "Path.exists(artifacts/P155W1-N02/compliance.sqlite)",
            "result": "unresolved"
          },
          "note": "first occurrence L203 in ## ⑥ 误差判定（逐项，是否 <3%） (backtick_path)",
          "declared_reference_form": "backtick_path",
          "also_referenced_on_lines": [],
          "existence_asserted_by_worker": false,
          "same_basename_as": [
            "A03"
          ]
        }
      ],
      "figure_probes": {
        "fig1_eexi_attained_vs_required.png": {
          "http_status": 404,
          "bytes": 29,
          "sha256": null,
          "caption": "EEXI 达到值与要求值对比：遗留设计超标 82%，经济型设计需 EPL，限功率后达标"
        },
        "fig2_epl_path.png": {
          "http_status": 404,
          "bytes": 29,
          "sha256": null,
          "caption": "EPL 限功率扫描：EEXI ∝ MCR′^(2/3)，交点给出达标限值（航速损失显式标注）"
        },
        "fig3_cii_rating_bands.png": {
          "http_status": 404,
          "bytes": 29,
          "sha256": null,
          "caption": "CII 等级带随 2023–2026 年度折减收紧；A 船由 C 降到 D，B 船稳定在 B"
        },
        "fig4_sensitivity.png": {
          "http_status": 404,
          "bytes": 29,
          "sha256": null,
          "caption": "左：EEXI 网格（弹性 +1 / −1）；右：CII 等级跳变（弹性 +1 / +2）"
        },
        "fig5_eedi_timeline.png": {
          "http_status": 404,
          "bytes": 29,
          "sha256": null,
          "caption": "EEDI 阶段时间线对比：C 船满足 Phase 2 但不满足 Phase 3（EEXI 20% < EEDI 30%）"
        }
      },
      "claims": [],
      "claims_empty_reason": "Contract wp-9510-01 sets objective.register_assets=true / classify_report_type=false, constraints.no_forced_claim_generation=true, and the package notes state 'claims 允许为空数组'. This工序 registers asset identity only (report_id, markdown byte hash, declared attachments/artifacts); knowledge extraction belongs to a downstream工序 (03) and is deliberately not attempted here.",
      "integrity": {
        "quote_uniqueness": {
          "quotes": 26,
          "unique_quotes": 26,
          "all_unique": true
        },
        "char_span_identity": {
          "spans_checked": 25,
          "all_match": true
        },
        "hash_recomputed_locally": "sha256:cdc7db83dac16cc900d6a54d14b29f7c59e3288804041be61444d517921ee39c",
        "hash_matches_contract": true
      },
      "id_integrity": {
        "ids_checked": 26,
        "duplicates": [],
        "unique": true
      },
      "figure_probe_summary": {
        "probed": 5,
        "http_200_with_bytes": 0,
        "http_status_histogram": {
          "404": 5
        }
      },
      "observations": [
        "Markdown is complete: H1 title on L1, sections ①-⑥ all present, 203 lines / 8039 chars; a generator/data footer closes the document.",
        "The report declares its whole artifact chain under artifacts/P155W1-N02/ (compliance.sqlite, results.json, queries.sql, make_report.py, run_compliance.py, 5 figures); those files live in ship-performance-platform and are registered here as declared references, not as verified bytes.",
        "Figure byte probes: 0/5 names returned HTTP 200 with payload, so the truncated sha256 prefixes printed in the report body can only be checked; a figure without payload stays referenced_unresolved and no hash is claimed.",
        "5 figures are declared twice: in the platform record (name+caption) and in-body as relative image links carrying truncated sha256 prefixes; those prefixes are re-checked against bytes served by GET /tensor/reports/9510/figures/{name}.",
        "IMO resolution identifiers (MEPC.x(yy) / MEPC.1/Circ.n) are registered as external standard references: they have no byte payload on this platform, so they stay referenced_unresolved by construction -- consistent with the report itself marking coefficient transcription WITHHELD."
      ],
      "limitations": [
        "Registration only: no claim extraction, no report-type classification, no verified marks (the platform gate computes verification independently).",
        "hash scope = UTF-8 bytes of the markdown field; any stored-markdown edit (even whitespace) invalidates this manifest.",
        "Direct psql read of tensor_reports is denied to this agent (permission denied for table tensor_reports), so the authenticated API is the only source channel used.",
        "Reference resolution is scoped to this delivery worktree; a path missing here is reported referenced_unresolved, never as a broken upstream artifact."
      ]
    },
    "claims.json": []
  }
}
```
