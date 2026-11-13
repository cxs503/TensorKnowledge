# KF-RESULT wp-6184-01

**工作包** `wp-6184-01`（task_type=`01-asset-registration`，lane C）· **report_id** `6184` ·
**mission** 15587 · **scenario_key** `green_navigation_eexi_cii_compliance`
**报告标题** IN28-I1 EEXI/CII 合规评估引擎：MEPC 全口径实现 + 12 船型验证（算术误差 0.00%，外部基准欠账）

## ① 本工序做了什么

只做一件事：把 report `6184` 的源资产登记下来（`objective.register_assets=true`，
`classify_report_type=false`）——确认 report_id 与其 markdown 的字节哈希，列出报告内**可解析/被引用**
的附件与工件，并给每个资产一个可机器复算的原文定位符。**不做抽取**：`claims` 为空数组（契约允许的完整结果），
不把任何结论标为 verified（verification 归平台门）。

边界遵守：只读 `tensor://reports/6184`（field=markdown），未读/写任何其它 report_id，未改写上游产物。

## ② 怎么做的（步骤/工具/关键设置）

1. `GET /api/v1/auth/login`（Bearer）→ `GET /api/v1/tensor/reports/6184`，取 `markdown` 字段与
   `title`/`scenario_key`/`tags`/`figures` 记录字段。
2. 对 markdown 的 **UTF-8 字节**重算 sha256 并与契约 `input.source_hash` 比对，同时比对 `chars`、`title`、
   `scenario_key`（三项全部一致，见 ⑥）。
3. 逐个资产生成定位符：`quote` 由程序从 markdown **切片**得到（不是手敲），因此 `quote` 必为原文子串；
   `start_char/end_char` 为 Python str 偏移，`start_line/end_line` 为 1-based 逻辑行号；并校验
   `markdown.count(quote)==1`（唯一性）。
4. 资产解析状态三分：`resolved_in_source`（内容就在 markdown 里）/ `referenced_unresolved`
   （正文引用了路径或外部标准，字节在本工序不可取）/ `declared_absent`（声明缺失，本报告无需）。
5. 探测平台附件端点（`/artifacts` 与 `/figures/<png>`，结果见下方探测表，均 404 → 代码/JSON/图片资产
   只能登记为"被引用未解析"）。
6. 写 `asset_manifest.json`（本地 schema `asset_manifest.schema.json` 用 jsonschema 校验），
   再用 `verify` 独立复算（重新从平台取原文再算哈希，**不**复用 build 的中间量），结果落 `verification.json`。

**平台附件端点探测**（Bearer 直连，失败非致命，只记录不改判）：

| 端点 | 结果 |
|---|---|
| `GET /tensor/reports/6184/artifacts` | HTTP 404 |
| `GET /tensor/reports/6184/figures/in28i1_figures_1to4.png` | HTTP 404 |

一键复跑（`repro_cmd`）：

```bash
cd <worktree> && python3 scripts/kf/wp6184_register_assets.py build verify && python3 scripts/kf/wp6184_emit_result.py && python3 -m pytest tests/test_kf_wp6184_asset_manifest.py -q
```

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-6184-01/asset_manifest.json` | 10 个资产：3 个 resolved_in_source / 7 个 referenced_unresolved；claims=0；integrity 四项自检 |
| `docs/kf/wp-6184-01/asset_manifest.schema.json` | 本地钉住的 manifest 形状（`const` 泛化为 pattern，可供其它 01 工序复用） |
| `docs/kf/wp-6184-01/verification.json` | 8 项 acceptance 自检逐条 pass/FAIL 与证据串 |
| `docs/kf/wp-6184-01/source_snapshot.md` | 报告 markdown 原字节快照（sha256 与契约一致），供离线复验定位符 |
| `docs/kf/wp-6184-01/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs），即文末唯一的结果 JSON 块 |
| `scripts/kf/wp6184_register_assets.py` | build（登记）+ verify（独立复算）单文件工具 |
| `scripts/kf/wp6184_emit_result.py` | 由 manifest/verification 生成 kf_result 与本报告正文（零手抄） |
| `tests/test_kf_wp6184_asset_manifest.py` | 离线 pytest：schema、哈希、定位符、唯一 id、claims 纪律、信封单块 |

按 class 分布：{"artifact_file": 1, "code_module": 2, "code_pointer": 1, "embedded_data_table": 2, "external_dataset": 1, "external_standard": 1, "figure": 1, "source_document": 1}。

## ④ 证据定位表（资产/字段 → 原文引文片段，逐字）

| 资产 / 段 | class / resolution | 原文引文（逐字） | 偏移/行 |
|---|---|---|---|
| A01 whole document (§1–§7) | `source_document` / resolved_in_source | ## 1 案例 …（全长 2406 字符，逐字片段见 `locator.quote`） | `[0,2406)` L1–43 |
| A02 §1 案例 | `code_pointer` / referenced_unresolved | 全部写入 `fleet.py` 的 `provenance` | `[238,268)` L2–2 |
| A03 §2 怎么做的 | `code_module` / referenced_unresolved | `backend/modules/eexi_cii_compliance`：`regulatory`（参考线/削减率分档/适用门槛/Z%/dd，逐条带置信度）、`eexi`（达到值 …（全长 297 字符，逐字片段见 `locator.quote`） | `[280,577)` L4–4 |
| A04 §3 结果（首条 bullet） | `artifact_file` / referenced_unresolved | - 判据 **15/15 通过**（见 `artifacts/in28_i1/checks.json`）。 | `[586,639)` L6–6 |
| A05 §3 结果 | `embedded_data_table` / resolved_in_source | \| 船型 \| EEXI \| 要求 \| 裕度% \| AER \| 2024 评级 \| …（全长 646 字符，逐字片段见 `locator.quote`） | `[846,1492)` L9–21 |
| A06 §6 误差判定 | `embedded_data_table` / resolved_in_source | \| 量 \| 基准 \| 相对误差 \| <3%？ \| …（全长 329 字符，逐字片段见 `locator.quote`） | `[1887,2216)` L33–40 |
| A07 §4 图 | `figure` / referenced_unresolved | 四联图内嵌（figures）：EEXI attained vs required｜CII 评级矩阵 2023–2027｜AER vs 文献区间｜Holtrop n_eff vs n …（全长 93 字符，逐字片段见 `locator.quote`） | `[1632,1725)` L27–27 |
| A08 §2 怎么做的 | `code_module` / referenced_unresolved | `benchmarks`（文献区间，WITHHELD） | `[512,539)` L4–4 |
| A09 §2 怎么做的 | `external_standard` / referenced_unresolved | （达到值 MEPC.333(76)、要求值 MEPC.328(76)、EPL 反解 MEPC.335(76)） | `[366,421)` L4–4 |
| A10 §6 误差判定 | `external_dataset` / referenced_unresolved | \| 逐船 AER \| GISIS/VeriFuel 点值 \| **离线不可得** \| **无法判定（WITHHELD 欠账）** \| | `[2150,2216)` L40–40 |

表中 `|`→`\|`、换行→`<br>` 仅为 markdown 表格语法转义；**逐字偏移与未转义原文以 `asset_manifest.json`
的 `locator.quote`/`start_char`/`end_char` 为准**（那才是机器复算的定位符）。

源哈希与记录字段（均由程序注入）：`sha256:f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c` · chars 2406（契约 2406）·
bytes_utf8 3546 · lines 43 · title_match=True ·
scenario_match=True · record_status=`published` ·
platform figures 声明 1 张（`in28i1_figures_1to4.png`）。

资产清单（10 行见 manifest `assets[]`）：

| asset_id | class | label | resolution | 行 |
|---|---|---|---|---|
| A01 | `source_document` | report 6184 markdown 原文（本工作包的唯一输入） | resolved_in_source | L1–43 |
| A02 | `code_pointer` | fleet.py（12 船主尺度/载重/装机/设计点 + provenance） | referenced_unresolved | L2–2 |
| A03 | `code_module` | backend/modules/eexi_cii_compliance（引擎模块：regulatory/eexi/cii/fleet/route/benchmarks） | referenced_unresolved | L4–4 |
| A04 | `artifact_file` | artifacts/in28_i1/checks.json（15 项判据检查结果） | referenced_unresolved | L6–6 |
| A05 | `embedded_data_table` | EEXI/要求/裕度%/AER/2024 评级 11 船型数值表 | resolved_in_source | L9–21 |
| A06 | `embedded_data_table` | 误差判定表（量/基准/相对误差/<3%？，6 行） | resolved_in_source | L33–40 |
| A07 | `figure` | 四联图 in28i1_figures_1to4.png（EEXI attained vs required｜CII 评级矩阵｜AER vs 文献区间｜Holtrop n_eff） | referenced_unresolved | L27–27 |
| A08 | `code_module` | benchmarks（文献区间来源，标记 WITHHELD） | referenced_unresolved | L4–4 |
| A09 | `external_standard` | IMO 决议 MEPC.333(76) / MEPC.328(76) / MEPC.335(76)（达到值 / 要求值 / EPL 反解） | referenced_unresolved | L4–4 |
| A10 | `external_dataset` | GISIS / VeriFuel 逐船 AER 外部基准点值 | referenced_unresolved | L40–40 |

## ⑤ 注意点与局限

- **未解析资产 7 项不是失败、是缺口登记**：平台无附件端点（`/artifacts`、`/figures/<png>` 均 404），
  故 `fleet.py`、`backend/modules/eexi_cii_compliance`、`artifacts/in28_i1/checks.json`、四联图、
  `benchmarks` 区间锚、三份 MEPC 决议、GISIS/VeriFuel 基准都只能登记"报告声称存在/引用"，本工序**不为其内容背书**：

| asset_id | 资产 | 为什么不解析 |
|---|---|---|
| A02 | fleet.py（12 船主尺度/载重/装机/设计点 + provenance） | 报告正文指向的代码工件；报告未内嵌该文件内容，平台亦无随报告附件可取 → 仅登记引用，不做内容断言。 |
| A03 | backend/modules/eexi_cii_compliance（引擎模块：regulatory/eexi/cii/fleet/route/benchmarks） | 模块路径与其子模块清单为报告自述；本工序不读代码、不做实现层核验。 |
| A04 | artifacts/in28_i1/checks.json（15 项判据检查结果） | 判据 15/15 的唯一原始证据文件；报告只给路径不给内容，附件端点探测见 source.platform_attachment_probes → 不可取。 |
| A07 | 四联图 in28i1_figures_1to4.png（EEXI attained vs required｜CII 评级矩阵｜AER vs 文献区间｜Holtrop n_eff） | 报告 record.figures 声明 1 张 png（name=in28i1_figures_1to4.png），但 markdown 未内嵌 base64、平台无图字节可取 → 图资产登记为未解析，登记其声明存在。 |
| A08 | benchmarks（文献区间来源，标记 WITHHELD） | 区间锚点自身被作者标为 WITHHELD（未回读决议/文献原文），本工序照录该状态，不上调。 |
| A09 | IMO 决议 MEPC.333(76) / MEPC.328(76) / MEPC.335(76)（达到值 / 要求值 / EPL 反解） | 外部规范原文不在报告内、本工序离线不可得；仅登记报告声明的映射关系（哪条决议管哪一层）。 |
| A10 | GISIS / VeriFuel 逐船 AER 外部基准点值 | 报告显式记『离线不可得』+『无法判定（WITHHELD 欠账）』：该项被登记为缺口而非已证，保留不确定性。 |

- 本工序**不读代码、不复算 EEXI/CII**：manifest 只回答"资产在哪里、字节是否对得上"，
  报告里的 15/15 判据、0.0e+00 算术误差、AER 11/12 落区间等结论**一律未被本包验证**（claims 为空）。
- 唯一的"可解析内容资产"是两张内嵌表（A05 11 船型数值表、A06 误差判定表），它们是 markdown 子串，
  下游抽取必须重新从 A05/A06 的 char span 取数，不得引用本报告正文的数字。
- 定位符按 1-based 逻辑行 + Python str 偏移给出，源文本若被上游改写（哈希变化）则全部失效——
  这正是把 `source_hash` 钉进信封的原因。
- 图：本工序是纯登记后端任务，不产生场量/曲线，**无图**（契约要求已声明的唯一图资产 A07 以文字+定位符登记，
  其字节在平台侧 404 不可取，故不伪造替代图）。

## ⑥ 自检：逐条对照 acceptance

- [x] `valid_json` — 13241 bytes parsed
- [x] `schema_pass` — jsonschema.validate pass against asset_manifest.schema.json
- [x] `source_hash_matches` — recomputed=f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c source=platform refetch platform_match=True manifest_hash=f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c
- [x] `source_locator_resolvable` — all quotes resolve + unique
- [x] `no_duplicate_ids` — 10 ids, dupes=[]
- [x] `all_claims_have_evidence_or_explicit_unresolved_status` — claims=0 (empty=legal for 01-asset-registration); offenders=[]
- [x] `counts_consistent` — counts.assets=10 len(assets)=10
- [x] `no_verified_marks` — no claim/asset marked verified by this package

**acceptance 汇总：8/8 pass，all_pass=True**。
无失败项；若有失败按 honest-FAIL 如实登记。补充：本工序不生成 claims（`claims_all_evidenced_or_unresolved`
对空集成立），未标 verified（`no_verified_marks` pass）。

## 结果信封

```json
{
  "package_id": "wp-6184-01",
  "task_type": "01-asset-registration",
  "report_id": "6184",
  "provenance": {
    "source_hash": "sha256:f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c",
    "source_field": "markdown",
    "producer": "agent/m15587 · scripts/kf/wp6184_register_assets.py",
    "emitted_at": "2026-11-12T01:28:39.580812+00:00",
    "notes": "source_hash = sha256 of the UTF-8 bytes of GET /api/v1/tensor/reports/6184 .markdown, recomputed locally and equal to the work-package contract input.source_hash (f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c); chars 2406 = contract chars 2406. Outputs carry the registered asset manifest only; no knowledge claims are extracted by this package and nothing is marked verified."
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-6184-01",
      "task_type": "01-asset-registration",
      "report_id": "6184",
      "source": {
        "uri": "tensor://reports/6184",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c",
        "contract_hash": "f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c",
        "hash_matches_contract": true,
        "chars": 2406,
        "contract_chars": 2406,
        "chars_matches_contract": true,
        "bytes_utf8": 3546,
        "lines": 43,
        "title": "IN28-I1 EEXI/CII 合规评估引擎：MEPC 全口径实现 + 12 船型验证（算术误差 0.00%，外部基准欠账）",
        "title_matches_contract": true,
        "scenario_key": "green_navigation_eexi_cii_compliance",
        "scenario_matches_contract": true,
        "record_id": 6184,
        "record_status": "published",
        "record_tags": [
          "EEXI",
          "CII",
          "MEPC.328(76)",
          "MEPC.353(78)",
          "MEPC.354(78)",
          "green_shipping",
          "IN28-I1"
        ],
        "platform_figures": [
          {
            "name": "in28i1_figures_1to4.png",
            "caption": "四联图：EEXI attained vs required｜CII 评级矩阵 2023-2027｜AER vs 文献区间｜Holtrop n_eff vs n=3"
          }
        ],
        "fetched_via": "GET /api/v1/tensor/reports/6184 (Bearer auth)",
        "platform_attachment_probes": {
          "GET /tensor/reports/6184/artifacts": {
            "http_status": 404,
            "bytes": 22
          },
          "GET /tensor/reports/6184/figures/in28i1_figures_1to4.png": {
            "http_status": 404,
            "bytes": 29
          }
        },
        "line_counting": "1-based logical lines of markdown; char offsets are Python str indices (UTF-8 decoded)"
      },
      "counts": {
        "assets": 10,
        "by_class": {
          "artifact_file": 1,
          "code_module": 2,
          "code_pointer": 1,
          "embedded_data_table": 2,
          "external_dataset": 1,
          "external_standard": 1,
          "figure": 1,
          "source_document": 1
        },
        "by_resolution": {
          "referenced_unresolved": 7,
          "resolved_in_source": 3
        },
        "resolved_in_source": 3,
        "referenced_unresolved": 7,
        "declared_absent": 0,
        "claims": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "source_document",
          "label": "report 6184 markdown 原文（本工作包的唯一输入）",
          "in_report_section": "whole document (§1–§7)",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 2406,
            "start_line": 1,
            "end_line": 43,
            "quote": "## 1 案例\nMARPOL 附则 VI 对现有船的两条约束：**EEXI**（设计侧，75% MCR 参考工况 → g CO2/(t·nm)）与 **CII**（营运侧，年油耗/年航程 + 逐年收紧 Z% → A–E 评级）。12 只代表船覆盖任务书 10 类（Handymax/Panamax/Capesize/MR/Aframax/VLCC/Feeder/Sub-Panamax/Panamax/Post-Panamax）+ LNG + 客船，主尺度/载重/装机/设计点全部写入 `fleet.py` 的 `provenance`。\n## 2 怎么做的\n`backend/modules/eexi_cii_compliance`：`regulatory`（参考线/削减率分档/适用门槛/Z%/dd，逐条带置信度）、`eexi`（达到值 MEPC.333(76)、要求值 MEPC.328(76)、EPL 反解 MEPC.335(76)）、`cii`（G1–G4 + Z% 法定/外推/未适用三态）、`fleet`（几何三关）、`route`（Holtrop 指数 + STAWAVE-1 增阻 + 风阻，功率锚点法）、`benchmarks`（文献区间，WITHHELD）。EEXI ∝ P_ME^(2/3)，所需限功率用二分法解，不用一次方近似。\n## 3 结果\n- 判据 **15/15 通过**（见 `artifacts/in28_i1/checks.json`）。\n- 几何：12/12 过 Cb/L·B·T、DWT/Δ 包络、L/B·B/T 包络、高 Cb+高 Fn 组合检查。\n- EEXI：适用 11/12（客船无参考线 → NOT_SUPPORTED），不装 EPL 达标 **2/11**；不达标船所需 EPL 5.5–34.2% 全部可行。例：82k 散货 attained 4.219 vs required 3.486（−21.0%，需 EPL 27.4%）。\n| 船型 | EEXI | 要求 | 裕度% | AER | 2024 评级 |\n|---|---|---|---|---|---|\n| handymax_56 | 5.198 | 4.181 | -24.3 | 4.64 | C |\n| panamax_82 | 4.219 | 3.486 | -21.0 | 3.70 | C |\n| capesize_180 | 3.085 | 2.396 | -28.8 | 2.67 | D |\n| mr2_50 | 5.325 | 4.965 | -7.2 | 5.04 | A |\n| aframax_110 | 3.819 | 3.379 | -13.0 | 3.51 | A |\n| vlcc_320 | 2.397 | 2.007 | -19.4 | 2.06 | C |\n| feeder_1700teu | 16.417 | 20.161 | +18.6 | 10.95 | A |\n| subpanamax_3500teu | 18.345 | 17.707 | -3.6 | 11.86 | D |\n| panamax_4500teu | 17.632 | 17.015 | -3.6 | 11.07 | E |\n| postpanamax_8500teu | 15.723 | 13.005 | -20.9 | 9.25 | E |\n| lng_174k | 5.157 | 7.960 | +35.2 | 4.91 | A |\n\n- CII：2023→2026 评级随 Z% 收紧单调下降（如 Post-Panamax 8500TEU：E→E，比值 1.35→1.44）；LNG（C_F=2.75）全程 A。\n- 文献区间：AER 11/12 落在行业区间（区间锚点 WITHHELD）。\n\n## 4 图\n四联图内嵌（figures）：EEXI attained vs required｜CII 评级矩阵 2023–2027｜AER vs 文献区间｜Holtrop n_eff vs n=3。\n\n## 5 注意点\n系数层整体 WITHHELD（离线未回读决议原文）；箱船/气体船削减率分档置信度最低；STAWAVE-1 短波支路为线性桥接（低估短波）；营运画像（经济航速 0.86–0.93、年海上天数）是 AER 的主导输入；客船 EEXI 显式 NOT_SUPPORTED 不借邻类系数。\n\n## 6 误差判定\n| 量 | 基准 | 相对误差 | <3%？ |\n|---|---|---|---|\n| 达到 EEXI（11 船） | 独立闭式手算 | 0.0e+00 | **是** |\n| 达到 CII（12 船） | 独立闭式手算 | 0.0e+00 | **是** |\n| 要求 EEXI | 双实现互校 | 0.0e+00 | **是** |\n| 要求 CII | 双实现互校 | 0.0e+00 | **是** |\n| 年度 AER | 文献区间(±25–30%) | 11/12 落区间 | **否**（区间不构成精度） |\n| 逐船 AER | GISIS/VeriFuel 点值 | **离线不可得** | **无法判定（WITHHELD 欠账）** |\n\n## 7 发现项\n1) `backend/api/green_shipping.py` 集装箱船 EEXI 削减率未按吨位分档（一律 20%），68,600 容量处要求值偏低 12.5%。2) 客船 CII 参考线 9309·GT^−0.383 给出 required≈115 g/(GT·nm)，比游轮实测高一个数量级 → 引擎量级闸门拦为 WITHHELD 并拒发评级。\n",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim substring present at [start_char,end_char] and unique in markdown",
            "result": "resolved"
          },
          "note": "注册对象本身：source_uri=tensor://reports/6184, field=markdown。sha256 与契约 input.source_hash 逐字节一致（见 integrity），chars 与契约一致。"
        },
        {
          "asset_id": "A02",
          "asset_class": "code_pointer",
          "label": "fleet.py（12 船主尺度/载重/装机/设计点 + provenance）",
          "in_report_section": "§1 案例",
          "locator": {
            "method": "char_span",
            "start_char": 238,
            "end_char": 268,
            "start_line": 2,
            "end_line": 2,
            "quote": "全部写入 `fleet.py` 的 `provenance`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path/name literal present in markdown; asset bytes not retrievable here",
            "result": "unresolved"
          },
          "note": "报告正文指向的代码工件；报告未内嵌该文件内容，平台亦无随报告附件可取 → 仅登记引用，不做内容断言。"
        },
        {
          "asset_id": "A03",
          "asset_class": "code_module",
          "label": "backend/modules/eexi_cii_compliance（引擎模块：regulatory/eexi/cii/fleet/route/benchmarks）",
          "in_report_section": "§2 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 280,
            "end_char": 577,
            "start_line": 4,
            "end_line": 4,
            "quote": "`backend/modules/eexi_cii_compliance`：`regulatory`（参考线/削减率分档/适用门槛/Z%/dd，逐条带置信度）、`eexi`（达到值 MEPC.333(76)、要求值 MEPC.328(76)、EPL 反解 MEPC.335(76)）、`cii`（G1–G4 + Z% 法定/外推/未适用三态）、`fleet`（几何三关）、`route`（Holtrop 指数 + STAWAVE-1 增阻 + 风阻，功率锚点法）、`benchmarks`（文献区间，WITHHELD）。EEXI ∝ P_ME^(2/3)，所需限功率用二分法解，不用一次方近似。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path/name literal present in markdown; asset bytes not retrievable here",
            "result": "unresolved"
          },
          "note": "模块路径与其子模块清单为报告自述；本工序不读代码、不做实现层核验。"
        },
        {
          "asset_id": "A04",
          "asset_class": "artifact_file",
          "label": "artifacts/in28_i1/checks.json（15 项判据检查结果）",
          "in_report_section": "§3 结果（首条 bullet）",
          "locator": {
            "method": "char_span",
            "start_char": 586,
            "end_char": 639,
            "start_line": 6,
            "end_line": 6,
            "quote": "- 判据 **15/15 通过**（见 `artifacts/in28_i1/checks.json`）。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path/name literal present in markdown; asset bytes not retrievable here",
            "result": "unresolved"
          },
          "note": "判据 15/15 的唯一原始证据文件；报告只给路径不给内容，附件端点探测见 source.platform_attachment_probes → 不可取。"
        },
        {
          "asset_id": "A05",
          "asset_class": "embedded_data_table",
          "label": "EEXI/要求/裕度%/AER/2024 评级 11 船型数值表",
          "in_report_section": "§3 结果",
          "locator": {
            "method": "char_span",
            "start_char": 846,
            "end_char": 1492,
            "start_line": 9,
            "end_line": 21,
            "quote": "| 船型 | EEXI | 要求 | 裕度% | AER | 2024 评级 |\n|---|---|---|---|---|---|\n| handymax_56 | 5.198 | 4.181 | -24.3 | 4.64 | C |\n| panamax_82 | 4.219 | 3.486 | -21.0 | 3.70 | C |\n| capesize_180 | 3.085 | 2.396 | -28.8 | 2.67 | D |\n| mr2_50 | 5.325 | 4.965 | -7.2 | 5.04 | A |\n| aframax_110 | 3.819 | 3.379 | -13.0 | 3.51 | A |\n| vlcc_320 | 2.397 | 2.007 | -19.4 | 2.06 | C |\n| feeder_1700teu | 16.417 | 20.161 | +18.6 | 10.95 | A |\n| subpanamax_3500teu | 18.345 | 17.707 | -3.6 | 11.86 | D |\n| panamax_4500teu | 17.632 | 17.015 | -3.6 | 11.07 | E |\n| postpanamax_8500teu | 15.723 | 13.005 | -20.9 | 9.25 | E |\n| lng_174k | 5.157 | 7.960 | +35.2 | 4.91 | A |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim substring present at [start_char,end_char] and unique in markdown",
            "result": "resolved"
          },
          "note": "markdown 内嵌表格即数据本体（11 行船型 + 表头/分隔行）；客船缺行与正文『适用 11/12』一致，可作为下游抽取的源表。"
        },
        {
          "asset_id": "A06",
          "asset_class": "embedded_data_table",
          "label": "误差判定表（量/基准/相对误差/<3%？，6 行）",
          "in_report_section": "§6 误差判定",
          "locator": {
            "method": "char_span",
            "start_char": 1887,
            "end_char": 2216,
            "start_line": 33,
            "end_line": 40,
            "quote": "| 量 | 基准 | 相对误差 | <3%？ |\n|---|---|---|---|\n| 达到 EEXI（11 船） | 独立闭式手算 | 0.0e+00 | **是** |\n| 达到 CII（12 船） | 独立闭式手算 | 0.0e+00 | **是** |\n| 要求 EEXI | 双实现互校 | 0.0e+00 | **是** |\n| 要求 CII | 双实现互校 | 0.0e+00 | **是** |\n| 年度 AER | 文献区间(±25–30%) | 11/12 落区间 | **否**（区间不构成精度） |\n| 逐船 AER | GISIS/VeriFuel 点值 | **离线不可得** | **无法判定（WITHHELD 欠账）** |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim substring present at [start_char,end_char] and unique in markdown",
            "result": "resolved"
          },
          "note": "内嵌即本体；逐船 AER 一行显式写『离线不可得 / WITHHELD 欠账』，不确定性被保留。"
        },
        {
          "asset_id": "A07",
          "asset_class": "figure",
          "label": "四联图 in28i1_figures_1to4.png（EEXI attained vs required｜CII 评级矩阵｜AER vs 文献区间｜Holtrop n_eff）",
          "in_report_section": "§4 图",
          "locator": {
            "method": "char_span",
            "start_char": 1632,
            "end_char": 1725,
            "start_line": 27,
            "end_line": 27,
            "quote": "四联图内嵌（figures）：EEXI attained vs required｜CII 评级矩阵 2023–2027｜AER vs 文献区间｜Holtrop n_eff vs n=3。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path/name literal present in markdown; asset bytes not retrievable here",
            "result": "unresolved"
          },
          "note": "报告 record.figures 声明 1 张 png（name=in28i1_figures_1to4.png），但 markdown 未内嵌 base64、平台无图字节可取 → 图资产登记为未解析，登记其声明存在。"
        },
        {
          "asset_id": "A08",
          "asset_class": "code_module",
          "label": "benchmarks（文献区间来源，标记 WITHHELD）",
          "in_report_section": "§2 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 512,
            "end_char": 539,
            "start_line": 4,
            "end_line": 4,
            "quote": "`benchmarks`（文献区间，WITHHELD）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path/name literal present in markdown; asset bytes not retrievable here",
            "result": "unresolved"
          },
          "note": "区间锚点自身被作者标为 WITHHELD（未回读决议/文献原文），本工序照录该状态，不上调。"
        },
        {
          "asset_id": "A09",
          "asset_class": "external_standard",
          "label": "IMO 决议 MEPC.333(76) / MEPC.328(76) / MEPC.335(76)（达到值 / 要求值 / EPL 反解）",
          "in_report_section": "§2 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 366,
            "end_char": 421,
            "start_line": 4,
            "end_line": 4,
            "quote": "（达到值 MEPC.333(76)、要求值 MEPC.328(76)、EPL 反解 MEPC.335(76)）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path/name literal present in markdown; asset bytes not retrievable here",
            "result": "unresolved"
          },
          "note": "外部规范原文不在报告内、本工序离线不可得；仅登记报告声明的映射关系（哪条决议管哪一层）。"
        },
        {
          "asset_id": "A10",
          "asset_class": "external_dataset",
          "label": "GISIS / VeriFuel 逐船 AER 外部基准点值",
          "in_report_section": "§6 误差判定",
          "locator": {
            "method": "char_span",
            "start_char": 2150,
            "end_char": 2216,
            "start_line": 40,
            "end_line": 40,
            "quote": "| 逐船 AER | GISIS/VeriFuel 点值 | **离线不可得** | **无法判定（WITHHELD 欠账）** |",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path/name literal present in markdown; asset bytes not retrievable here",
            "result": "unresolved"
          },
          "note": "报告显式记『离线不可得』+『无法判定（WITHHELD 欠账）』：该项被登记为缺口而非已证，保留不确定性。"
        }
      ],
      "claims": [],
      "integrity": {
        "quote_uniqueness": true,
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "ids_unique": true,
        "claims_all_evidenced_or_unresolved": true,
        "notes": "本工序不做抽取、不生成知识 claim（objective.register_assets 为唯一目标）；claims 空数组是合法完整结果，不标任何结论为 verified。"
      }
    }
  },
  "claims": []
}
```
