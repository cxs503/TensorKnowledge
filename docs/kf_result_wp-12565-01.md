# KF-RESULT wp-12565-01

**tags**: `kf-wp:wp-12565-01`, `01-asset-registration`, `report:12565`, `lane:C`, `draft`, `knowledge-factory`
**package_id**: `wp-12565-01` ｜ **task_type**: `01-asset-registration` ｜ **report_id**: `12565` ｜ **lane**: `C`
**source_uri**: `tensor://reports/12565` ｜ **source_field**: `markdown` ｜ **repo**: TensorKnowledge ｜ **status**: draft

---

## ① 本工序做了什么

本工作包做且只做 `report_id=12565`（《P156W2-N03 报告勘误：球阻归一化口径（nu_formula vs nu_eff）》，scenario_key=`lbm_d3q27_poiseuille_stokes`）的**资产登记**（工序 `01-asset-registration`）：

1. **确认 report_id 与其 markdown 的字节哈希一一对应**：独立重算 `sha256:a5a04a43beed973865029e9ade6c0de33a88e17a795bea13b55ef4c083571d20`，
   与契约声明 `sha256:a5a04a43beed973865029e9ade6c0de33a88e17a795bea13b55ef4c083571d20` **逐字节相等**；`chars=648`（= python `str` 长度，与契约 `chars=648` 相同），
   UTF-8 字节 `1086`（CJK 正文两者必然不同，口径已写明），共 `12` 行。
2. **登记源资产本体**：`markdown` 原件按字节落盘（`docs/kf/wp-12565-01/source.md`，`1086` 字节，
   与平台返回逐字节相同——独立校验器 V5 复核），并登记记录侧元数据（title / scenario_key / mission_id /
   status / created_at / tags / figures）。
3. **列出可解析的附件/工件引用**：8 个资产，逐个给出**逐字引文 + 字符跨度 + 行跨度 + 出现次数**：
   `resolved_in_source` 4 个、`referenced_unresolved` 4 个、`declared_absent` 0 个。
4. **登记正文中的数值字面量位置**（`literal_anchors`，18 条）：只记位置与出现次数，
   `is_claim=false`，**不解释、不比较、不构成 claim**——供下游工序零手抄取用。
5. **不做抽取、不分类、不产生 claim**（契约 `objective.classify_report_type=false`、`no_forced_claim_generation=true`；
   `claims` 允许空数组）。**没有任何结论被标成 verified**：哈希相等只是机械身份校验，verification 由平台门计算。

**边界遵守**：只读 `GET /api/v1/tensor/reports/12565` 这一份记录；正文提到的上游
`report id 12563` **故意未取**（本包不得读写其它 report_id），按 `referenced_unresolved` 登记；
未改写上游或其它工作包产物（独立校验器 V7 逐条列出本包访问过的 URL）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **契约入参**：`package_id`、`report_id=12565`、`source_field=markdown`、契约 `source_hash`、`chars=648`、
   `title`、`scenario_key`；六条 `acceptance` 直接作为自检表（见 ⑥），另有独立校验器 7 条（不共用代码路径）。
2. **取源**：`POST /api/v1/auth/login`（凭据只从环境变量 `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS` 读，
   不落盘、不进仓库）→ `GET /api/v1/tensor/reports/12565`（Bearer）取 `markdown`；
   同记录元数据一并登记。
3. **零手抄定位**：脚本内 `ASSETS[]` / `ANCHORS[]` 引文表为**声明值**，用 `str.find` 逐条解析；
   **任一引文未命中即 `SystemExit`，不出半张清单**（本轮 A09 引文未命中被硬拦下，见 ⑤）。
   每条落 `char_span`（start/end）、`line` 跨度、`occurrences`、`unique`。
4. **哈希闸门**：`hashlib.sha256(markdown.encode('utf-8'))` 与契约 `source_hash` 比较，且 `len(str)` 与契约 `chars` 比较；
   任一不符即 `SystemExit`。
5. **schema 双验**：信封按 `schemas/kf_result.v1.schema.json`（JSON-Schema 2020-12）校验；
   清单按 `schemas/asset_manifest.v1.schema.json` 校验，因其 `package_id`/`report_id`/`source.uri` 为 448 包的 `const`，
   校验时**只把这三个 const 重钉到本包**（其余结构与判据不变，脚本内注明），使 `schema_pass` 是可复现检查而非断言。
6. **附件端点探测**（带 Bearer，逐条记录状态码）：

| 探测端点 | 结果 |
|---|---|
| `/api/v1/openapi.json` | HTTP 404 |
| `/api/v1/tensor/reports/12565/artifacts` | HTTP 404 |
| `/api/v1/tensor/reports/12565/figures` | HTTP 404 |
| `/api/v1/tensor/artifacts?report_id=12565` | HTTP 404 |

7. **独立校验器**（`scripts/kf_wp12565_01_verify.py`，**不 import 登记脚本**，改用切片重建 `markdown[start:end] == quote`
   的另一条代码路径）：7 条检查全部通过，见 ⑥ 第二张表。
8. **报告正文的 json 块由脚本从 `kf_result.json` 原样注入**（f-string 拼装 + `json.dumps`，无手抄）；本文件只有这一个 fenced json 块。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-12565-01/asset_manifest.json` | 契约输出 `asset_manifest.json`：8 资产 / 18 字面量锚点 / `claims=[]` / counts·integrity·limitations |
| `docs/kf/wp-12565-01/kf_result.json` | `kf_result.v1` 信封（`package_id`/`task_type`/`report_id`/`provenance`/`outputs`，2020-12 校验通过），`outputs.asset_manifest.json` 与上表逐字段相同 |
| `docs/kf/wp-12565-01/source.md` | 报告 `markdown` 原件字节副本（1086 字节） |
| `docs/kf/wp-12565-01/sha256.txt` | 本地重算摘要 `sha256:a5a04a43beed973865029e9ade6c0de33a88e17a795bea13b55ef4c083571d20` |
| `docs/kf/wp-12565-01/locator_check.json` | 每条资产/锚点的跨度、行号、出现次数 |
| `docs/kf/wp-12565-01/verification.json` | 六条 acceptance 的机器判定（`all_pass=True`） |
| `docs/kf/wp-12565-01/verify_independent.json` | 独立校验器 7 条结果（`all_pass=True`） |
| `docs/kf/wp-12565-01/figures/locator_map.png` | 图 1：648 字符轴上的资产跨度与锚点位置 + 按类别的登记结果计数 |
| `scripts/kf_wp12565_01_register.py` / `_verify.py` / `_figure.py` / `_report.py` | 一键复跑链（登记 → 独立校验 → 出图 → 组报告+发布） |

## ④ 证据定位表（claim/字段 → 原文引文片段）

**A. 资产与逐字定位**（`locator.quote` 为原文逐字片段，`start/end` 为 python `str` 字符偏移，1-based 行号）

| asset_id | asset_class | 标签 | 行跨度 | 字符跨度 | 原文引文 | resolution |
|---|---|---|---|---|---|---|
| A01 | source_document | report 12565 markdown (whole document) | L1–L1 | 0–37 | `# P156W2-N03 报告勘误（对应 report id 12563）` | resolved_in_source |
| A02 | upstream_report_reference | upstream report 12563 (the report this errata corrects) | L1–L1 | 17–37 | `（对应 report id 12563）` | referenced_unresolved |
| A03 | data_artifact_reference | artifacts/sphere_resolution.json (declared artifact holding both K values) | L7–L7 | 273–305 | `artifacts/sphere_resolution.json` | referenced_unresolved |
| A04 | data_field_reference | declared JSON fields k_measured / k_measured_effective_nu inside A03 | L7–L7 | 305–343 | `（k_measured / k_measured_effective_nu）` | referenced_unresolved |
| A05 | inline_markdown_table | the two-row corrigendum table (量 / 摘要行写的 / 正文·工件 / 差异原因) | L5–L5 | 90–121 | `\| 量 \| 摘要行写的 \| 正文/工件（准） \| 差异原因 \|` | resolved_in_source |
| A06 | data_field_reference | formula-viscosity normalisation (tau-1/2)/3 | L7–L7 | 200–211 | `(tau-1/2)/3` | resolved_in_source |
| A07 | data_field_reference | lattice-BGK effective-viscosity normalisation (nu_eff) | L7–L7 | 228–249 | `格子 BGK 有效黏性 nu_eff 归一` | resolved_in_source |
| A08 | analytic_reference | Hasimoto drag correlation (benchmark reference curve) | L7–L7 | 142–162 | `球阻 vs Hasimoto（D=12）` | referenced_unresolved |

**B. 数值字面量锚点（只记位置，`is_claim=false`）**

| id | 原文逐字 | 起始字符 | 行跨度 | 该处原意（照抄语义，不解释） |
|---|---|---|---|---|
| L01 | `8.3 %` | 165 | 7–7 | summary-line value, D=12 (as reported in the abstract line) |
| L02 | `7.59 %` | 175 | 7–7 | body/artifact value, D=12 (preferred normalisation) |
| L03 | `8.32 %` | 186 | 7–7 | D=12 error recomputed with the formula viscosity |
| L04 | `K=1.6775` | 216 | 7–7 | K with formula viscosity (tau-1/2)/3 |
| L05 | `K=1.6909` | 250 | 7–7 | K with lattice-BGK effective viscosity |
| L06 | `10.2 %` | 360 | 8–8 | summary-line value, D=8 (as reported in the abstract line) |
| L07 | `10.22 %` | 369 | 8–8 | body value, D=8 |
| L08 | `2.33 %` | 431 | 10–10 | 1/D -> 0 intercept of a two-point linear extrapolation |
| L09 | `0.8628` | 525 | 10–10 | measured K ratio for the two blockage ratios a/L=1/6 and 1/8 |
| L10 | `0.8363` | 544 | 10–10 | Hasimoto K ratio for the same two blockage ratios |
| L11 | `a/L=1/6` | 503 | 10–10 | first blockage ratio |
| L12 | `1.112 %` | 577 | 12–12 | Poiseuille error, first entry |
| L13 | `0.278 %` | 585 | 12–12 | Poiseuille error, second entry |
| L14 | `0.070 %` | 593 | 12–12 | Poiseuille error, third entry |
| L15 | `阶 2.00` | 601 | 12–12 | observed Poiseuille convergence order |
| L16 | `4e-9` | 615 | 12–12 | wall force balance residual |
| L17 | `1e5 步` | 624 | 12–12 | stability run length in steps |
| L18 | `3e-16` | 634 | 12–12 | third-moment residual |

**C. 身份事实（机器比对，非人工计数）**

| 事实 | 出处 | 值 | 说明 |
|---|---|---|---|
| source_hash 相等 | `hashlib.sha256(markdown)` vs 契约 | `sha256:a5a04a43beed973865029e9ade6c0de33a88e17a795bea13b55ef4c083571d20` | `hash_matches_contract=true` |
| chars 相等 | `len(markdown)` vs 契约 `chars` | `648` vs `648` | `chars_match_contract=true` |
| title 相等 | `record.title` vs 契约 `title` | `P156W2-N03 报告勘误：球阻归一化口径（nu_formula vs nu_eff）` | `title_matches_contract=true` |
| scenario_key 相等 | `record.scenario_key` vs 契约 | `lbm_d3q27_poiseuille_stokes` | `scenario_matches_contract=true` |
| 记录无附件 | `len(record.figures)` | `0` | 该记录未声明任何图，故无附件元数据可登记 |
| 记录状态 | `record.status` / `created_at` | `published` / `2026-11-10T21:44:49.735945+00:00` | mission_id=`10870` |

**D. 登记过程中机器发现的身份观察（不改原文，只如实登记）**

| 观察 | 检查 | 结果 | 说明 |
|---|---|---|---|
| the contract title mentions nu_formula, the markdown body never does | `"nu_formula" in markdown` | false | the body names the formula-viscosity normalisation by its expression (tau-1/2)/3, so the title's token cannot be located as markdown text; it is registered via source.title only |
| the markdown H1 states the corrected report id, not the errata's title | `markdown.split(chr(10))[0]` | "# P156W2-N03 报告勘误（对应 report id 12563）" | locator anchor for A01; the record title lives in the title field, not in H1 |
| figure list is empty for this record | `len(record.figures)` | 0 | the record declares no figures, so no attachment metadata can be registered |

## ⑤ 注意点与局限

1. **标题里的 `nu_formula` 在正文中不存在**：契约/记录 `title` 为「…（nu_formula vs nu_eff）」，但 markdown H1 只写
   「报告勘误（对应 report id 12563）」，正文用表达式 `(tau-1/2)/3` 指代公式黏性归一。该 token **无法作为 markdown 文本定位**，
   故只经 `source.title` 登记（表中 A06/A07），不假装它在正文里。
2. **上游 report 12563 未取，是非能力缺失而是边界遵守**：本包被限定只碰 `12565`，因此勘误所指的“准值”所在的
   正文与工件（`artifacts/sphere_resolution.json`）**在本包内不可读**；两处差异（8.3 % vs 7.59 %、10.2 % vs 10.22 %）
   只登记为字面量位置，**未做值层面复核**，需要上游包的工序去核。
3. **`referenced_unresolved` 4 项是真的解析不到**：工件端点
   `/tensor/reports/12565/artifacts`、`/figures`、`/tensor/artifacts?report_id=` 全为 HTTP 404（见 ② 表），
   记录 `figures` 为空，故工件只到定位符层级，**不声称内容可校验**。
4. **Hasimoto 只有名字**：markdown 无年份/版次/DOI，`analytic_reference` 只能 `referenced_unresolved`——
   不能凭空补文献标识（`do_not_invent_missing_information`）。
5. **数值字面量的边界**：`literal_anchors` 只登记“原文在哪、出现几次”，不判定其对错；把 `7.59 %` 认作正确值属于
   抽取/判定工序，不在本包。
6. **图 1 的标签只有 ASCII**：本机 matplotlib 唯一可用字体为 `Noto Sans`（无 CJK 覆盖），CJK 标注会显示为方块，
   故图内用 asset_id + asset_class 标注；CJK 引文以逐字形式存在于 `asset_manifest.json`（可核对）。
7. **过程中被自己的闸门拦下过一次**：初版把 A09 引文 `（nu_formula vs nu_eff）` 当作正文片段，登记脚本直接
   `SystemExit`（未出半张清单）——它只存在于 `title`，不在 markdown；改成 `identity_observations` 登记（见 ⑤.1）。
   另初版 A01 用 `method=document` 但 `quote` 只是标题行，独立校验器 V3 切片重建失败（7/8），
   改为精确 `char_span` + 另列 `document_scope` 后 8/8 通过。
8. **本包不产生任何关于物理结论的断言**：报告内容（球阻归一化口径、外推截距等）的科学正确性不在本工序判定范围内。

## ⑥ 误差判定

本工序唯一的外部基准是契约声明的身份量，逐项列出：

| 基准量 | 契约值 | 本包实测 | 误差 | 是否 <3 % |
|---|---|---|---|---|
| `sha256(markdown)` | `sha256:a5a04a43beed973865029e9ade6c0de33a88e17a795bea13b55ef4c083571d20` | `sha256:a5a04a43beed973865029e9ade6c0de33a88e17a795bea13b55ef4c083571d20` | 0（逐字节相等） | 是（0 %） |
| `chars`（`str` 长度） | `648` | `648` | 0 | 是（0 %） |
| `title` / `scenario_key` | 见 ④-C | 见 ④-C | 0 | 是（0 %） |
| 资产定位符可解析率 | 全部可解析 | 8/8 资产 + 18/18 锚点 | 0 | 是（0 %） |

**显式回答**：本工序的可比基准量误差为 **0 %，< 3 % ✓**。报告正文中的物理量（如 `7.59 %`、`2.33 %`）本包**未复算**，
其误差判定属于上游/下游工序，此处**不声明**——避免把“定位符解析成功”误读成“数值被验证”。

## ⑥′ 自检：逐条对照 acceptance

**契约 6 条（`docs/kf/wp-12565-01/verification.json`）**

| acceptance 项 | 判定 | 证据 |
|---|---|---|
| `valid_json` | ✓ | manifest + envelope round-trip through json.dumps/json.loads |
| `schema_pass` | ✓ | envelope vs schemas/kf_result.v1.schema.json (2020-12) and manifest vs schemas/asset_manifest.v1.schema.json with package/report consts re-pinned |
| `source_locator_resolvable` | ✓ | 8/8 asset quotes + 18/18 anchor quotes resolve verbatim (char span, line span, occurrence count recorded) |
| `source_hash_matches` | ✓ | sha256:a5a04a43beed973865029e9ade6c0de33a88e17a795bea13b55ef4c083571d20 |
| `no_duplicate_ids` | ✓ | 8 asset ids, 8 distinct |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✓ | claims=[] by contract (no extraction); every non-empty asset carries a locator + explicit resolution; nothing marked verified |

**独立校验器 7 条（`docs/kf/wp-12565-01/verify_independent.json`，另一条代码路径）**

| id | 判定 | 证据 |
|---|---|---|
| V1 | ✓ | "envelope validates (2020-12); outputs.asset_manifest.json == asset_manifest.json on disk" |
| V2 | ✓ | {"fetched": "sha256:a5a04a43beed973865029e9ade6c0de33a88e17a795bea13b55ef4c083571d20", "contract": "sha256:a5a04a43beed973865029e9ade6c0de33a88e17a795 |
| V3 | ✓ | "8/8 asset locators reconstruct from the raw markdown" |
| V4 | ✓ | "18/18 literal anchors reconstruct; none flagged as a claim" |
| V5 | ✓ | {"asset_ids": 8, "distinct": 8, "anchor_ids": 18, "distinct_anchors": 18, "source_copy_byte_identical": true} |
| V6 | ✓ | "claims=[]; string \"verified\" present=False" |
| V7 | ✓ | {"contacted": ["http://127.0.0.1:8010/api/v1/auth/login", "http://127.0.0.1:8010/api/v1/tensor/reports/12565"], "offending_urls": []} |

**honest-FAIL 声明**：无失败项，全部 ✓。但如实登记三项“未做”：①未读上游 report 12563（边界，非缺陷）；
②未取任何工件内容（端点 404，`referenced_unresolved` 如实标注）；③未做任何数值复核与 claim 生成（契约要求）。

## ⑦ 图 1 说明（figures）

**图 1** `figures/locator_map.png`：上图为 648 字符 markdown 轴上的资产跨度（条）与 18 个字面量锚点位置（竖线），
颜色区分 `resolved_in_source` / `referenced_unresolved`；下图为按资产类别的登记结果计数（由 `asset_manifest.json` 直接读取，非手抄）。

## 复跑（repro_cmd）

```bash
cd "$(git rev-parse --show-toplevel)" && python3 scripts/kf_wp12565_01_register.py && python3 scripts/kf_wp12565_01_verify.py && python3 scripts/kf_wp12565_01_figure.py && python3 scripts/kf_wp12565_01_report.py body
```

（`publish` 子命令需要 `TENSOR_AGENT_USER`/`TENSOR_AGENT_PASS`/`TENSOR_API_BASE`；若离线可用 `--no-fetch`
读 `docs/kf/wp-12565-01/source.md`，仍在本地复算哈希比对契约值。）

---

## 结果信封（kf_result.v1，本报告唯一 json 块，由脚本从 `docs/kf/wp-12565-01/kf_result.json` 原样注入）

```json
{
  "package_id": "wp-12565-01",
  "task_type": "01-asset-registration",
  "report_id": "12565",
  "provenance": {
    "source_hash": "sha256:a5a04a43beed973865029e9ade6c0de33a88e17a795bea13b55ef4c083571d20",
    "source_field": "markdown",
    "producer": "agent/m15749",
    "emitted_at": "2026-11-12T02:30:41+00:00",
    "notes": "sha256 recomputed with hashlib over the UTF-8 bytes of the markdown field fetched from GET /api/v1/tensor/reports/12565; identical to the contract source_hash. Identity check only - no claim is marked verified."
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-12565-01",
      "task_type": "01-asset-registration",
      "report_id": "12565",
      "lane": "C",
      "contract_version": "1.0",
      "generated_at": "2026-11-12T02:30:41+00:00",
      "producer": "agent/m15749",
      "source": {
        "uri": "tensor://reports/12565",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "a5a04a43beed973865029e9ade6c0de33a88e17a795bea13b55ef4c083571d20",
        "hash_with_prefix": "sha256:a5a04a43beed973865029e9ade6c0de33a88e17a795bea13b55ef4c083571d20",
        "contract_hash": "sha256:a5a04a43beed973865029e9ade6c0de33a88e17a795bea13b55ef4c083571d20",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "chars": 648,
        "contract_chars": 648,
        "chars_match_contract": true,
        "bytes_utf8": 1086,
        "lines": 12,
        "title": "P156W2-N03 报告勘误：球阻归一化口径（nu_formula vs nu_eff）",
        "scenario_key": "lbm_d3q27_poiseuille_stokes",
        "contract_title": "P156W2-N03 报告勘误：球阻归一化口径（nu_formula vs nu_eff）",
        "contract_scenario_key": "lbm_d3q27_poiseuille_stokes",
        "title_matches_contract": true,
        "scenario_matches_contract": true,
        "platform_figures": [],
        "platform_tags": [
          "D3Q27",
          "corrigendum",
          "TensorLBM"
        ],
        "platform_mission_id": 10870,
        "platform_status": "published",
        "platform_created_at": "2026-11-10T21:44:49.735945+00:00",
        "summary_field_len_chars": 102,
        "line_counting": "1-based over markdown.rstrip('\\n').split('\\n'); char spans are python str offsets over the same unicode string"
      },
      "counts": {
        "assets": 8,
        "by_class": {
          "source_document": 1,
          "upstream_report_reference": 1,
          "data_artifact_reference": 1,
          "data_field_reference": 3,
          "inline_markdown_table": 1,
          "analytic_reference": 1
        },
        "by_resolution": {
          "resolved_in_source": 4,
          "referenced_unresolved": 4
        },
        "resolved_in_source": 4,
        "referenced_unresolved": 4,
        "declared_absent": 0,
        "literal_anchors": 18
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "source_document",
          "label": "report 12565 markdown (whole document)",
          "in_report_section": "whole document",
          "uri": "tensor://reports/12565",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 0,
            "end_char": 37,
            "start_line": 1,
            "end_line": 1,
            "quote": "# P156W2-N03 报告勘误（对应 report id 12563）",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256 over the UTF-8 bytes of record.markdown == contract source_hash",
            "result": "resolved"
          },
          "note": "bytes fetched via GET /api/v1/tensor/reports/12565, hashed locally; the document is the registration target itself, so it resolves to itself",
          "document_scope": {
            "start_char": 0,
            "end_char": 648,
            "start_line": 1,
            "end_line": 12,
            "chars": 648,
            "bytes_utf8": 1086
          }
        },
        {
          "asset_id": "A02",
          "asset_class": "upstream_report_reference",
          "label": "upstream report 12563 (the report this errata corrects)",
          "in_report_section": "H1 title",
          "uri": "tensor://reports/12563",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 17,
            "end_char": 37,
            "start_line": 1,
            "end_line": 1,
            "quote": "（对应 report id 12563）",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "record fetch of report 12563 deliberately not performed (package scope boundary)",
            "result": "unresolved"
          },
          "note": "the id is quoted verbatim, but this package is restricted to report_id=12565 and must not read other report_ids, so its body/artifacts stay unverified here"
        },
        {
          "asset_id": "A03",
          "asset_class": "data_artifact_reference",
          "label": "artifacts/sphere_resolution.json (declared artifact holding both K values)",
          "in_report_section": "corrigendum table",
          "uri": "artifacts/sphere_resolution.json",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 273,
            "end_char": 305,
            "start_line": 7,
            "end_line": 7,
            "quote": "artifacts/sphere_resolution.json",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "artifact endpoints probed for report 12565; no payload served (see artifact_probe)",
            "result": "unresolved"
          },
          "note": "path is quoted verbatim; the file is an artifact of the upstream report, not part of this record, and no reachable endpoint serves it"
        },
        {
          "asset_id": "A04",
          "asset_class": "data_field_reference",
          "label": "declared JSON fields k_measured / k_measured_effective_nu inside A03",
          "in_report_section": "corrigendum table",
          "uri": "artifacts/sphere_resolution.json#k_measured,k_measured_effective_nu",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 305,
            "end_char": 343,
            "start_line": 7,
            "end_line": 7,
            "quote": "（k_measured / k_measured_effective_nu）",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "field names are quoted verbatim; the enclosing artifact A03 does not resolve",
            "result": "unresolved"
          },
          "note": "the two normalisation variants the errata distinguishes live in these two fields; field names are registered, values are not extracted"
        },
        {
          "asset_id": "A05",
          "asset_class": "inline_markdown_table",
          "label": "the two-row corrigendum table (量 / 摘要行写的 / 正文·工件 / 差异原因)",
          "in_report_section": "corrigendum table",
          "uri": "tensor://reports/12565#table-1",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 90,
            "end_char": 121,
            "start_line": 5,
            "end_line": 5,
            "quote": "| 量 | 摘要行写的 | 正文/工件（准） | 差异原因 |",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "table structure parsed from the markdown (header cells + contiguous pipe rows)",
            "result": "resolved"
          },
          "note": "structure registered only (header_cells / data_rows); cell values are not extracted",
          "structure": {
            "header_cells": 4,
            "data_rows": 2,
            "table_end_line": 8
          }
        },
        {
          "asset_id": "A06",
          "asset_class": "data_field_reference",
          "label": "formula-viscosity normalisation (tau-1/2)/3",
          "in_report_section": "corrigendum table",
          "uri": "tensor://reports/12565#nu_formula",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 200,
            "end_char": 211,
            "start_line": 7,
            "end_line": 7,
            "quote": "(tau-1/2)/3",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "normalisation expression quoted verbatim",
            "result": "resolved"
          },
          "note": "the errata names this normalisation as the source of the 8.32 % variant; the expression is registered as written, its definition(s) are not re-derived here"
        },
        {
          "asset_id": "A07",
          "asset_class": "data_field_reference",
          "label": "lattice-BGK effective-viscosity normalisation (nu_eff)",
          "in_report_section": "corrigendum table",
          "uri": "tensor://reports/12565#nu_eff",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 228,
            "end_char": 249,
            "start_line": 7,
            "end_line": 7,
            "quote": "格子 BGK 有效黏性 nu_eff 归一",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "normalisation phrase quoted verbatim",
            "result": "resolved"
          },
          "note": "the body-preferred normalisation; registered as a named quantity, not recomputed here"
        },
        {
          "asset_id": "A08",
          "asset_class": "analytic_reference",
          "label": "Hasimoto drag correlation (benchmark reference curve)",
          "in_report_section": "corrigendum table",
          "uri": "tensor://reports/12565#hasimoto",
          "locator": {
            "method": "char_span",
            "source_field": "markdown",
            "start_char": 142,
            "end_char": 162,
            "start_line": 7,
            "end_line": 7,
            "quote": "球阻 vs Hasimoto（D=12）",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "bibliographic identifier (DOI/edition/year) present in the registered markdown",
            "result": "unresolved"
          },
          "note": "the reference is cited by name only - no year, edition or DOI appears in the markdown, so the exact correlation cannot be resolved to a source"
        }
      ],
      "literal_anchors": [
        {
          "locator_id": "L01",
          "kind": "number_literal",
          "quote": "8.3 %",
          "meaning_as_written": "summary-line value, D=12 (as reported in the abstract line)",
          "source_field": "markdown",
          "start_char": 165,
          "end_char": 170,
          "start_line": 7,
          "end_line": 7,
          "occurrences": 1,
          "unique": true,
          "resolvable": true,
          "is_claim": false
        },
        {
          "locator_id": "L02",
          "kind": "number_literal",
          "quote": "7.59 %",
          "meaning_as_written": "body/artifact value, D=12 (preferred normalisation)",
          "source_field": "markdown",
          "start_char": 175,
          "end_char": 181,
          "start_line": 7,
          "end_line": 7,
          "occurrences": 2,
          "unique": false,
          "resolvable": true,
          "is_claim": false
        },
        {
          "locator_id": "L03",
          "kind": "number_literal",
          "quote": "8.32 %",
          "meaning_as_written": "D=12 error recomputed with the formula viscosity",
          "source_field": "markdown",
          "start_char": 186,
          "end_char": 192,
          "start_line": 7,
          "end_line": 7,
          "occurrences": 1,
          "unique": true,
          "resolvable": true,
          "is_claim": false
        },
        {
          "locator_id": "L04",
          "kind": "number_literal",
          "quote": "K=1.6775",
          "meaning_as_written": "K with formula viscosity (tau-1/2)/3",
          "source_field": "markdown",
          "start_char": 216,
          "end_char": 224,
          "start_line": 7,
          "end_line": 7,
          "occurrences": 1,
          "unique": true,
          "resolvable": true,
          "is_claim": false
        },
        {
          "locator_id": "L05",
          "kind": "number_literal",
          "quote": "K=1.6909",
          "meaning_as_written": "K with lattice-BGK effective viscosity",
          "source_field": "markdown",
          "start_char": 250,
          "end_char": 258,
          "start_line": 7,
          "end_line": 7,
          "occurrences": 1,
          "unique": true,
          "resolvable": true,
          "is_claim": false
        },
        {
          "locator_id": "L06",
          "kind": "number_literal",
          "quote": "10.2 %",
          "meaning_as_written": "summary-line value, D=8 (as reported in the abstract line)",
          "source_field": "markdown",
          "start_char": 360,
          "end_char": 366,
          "start_line": 8,
          "end_line": 8,
          "occurrences": 1,
          "unique": true,
          "resolvable": true,
          "is_claim": false
        },
        {
          "locator_id": "L07",
          "kind": "number_literal",
          "quote": "10.22 %",
          "meaning_as_written": "body value, D=8",
          "source_field": "markdown",
          "start_char": 369,
          "end_char": 376,
          "start_line": 8,
          "end_line": 8,
          "occurrences": 1,
          "unique": true,
          "resolvable": true,
          "is_claim": false
        },
        {
          "locator_id": "L08",
          "kind": "number_literal",
          "quote": "2.33 %",
          "meaning_as_written": "1/D -> 0 intercept of a two-point linear extrapolation",
          "source_field": "markdown",
          "start_char": 431,
          "end_char": 437,
          "start_line": 10,
          "end_line": 10,
          "occurrences": 1,
          "unique": true,
          "resolvable": true,
          "is_claim": false
        },
        {
          "locator_id": "L09",
          "kind": "number_literal",
          "quote": "0.8628",
          "meaning_as_written": "measured K ratio for the two blockage ratios a/L=1/6 and 1/8",
          "source_field": "markdown",
          "start_char": 525,
          "end_char": 531,
          "start_line": 10,
          "end_line": 10,
          "occurrences": 1,
          "unique": true,
          "resolvable": true,
          "is_claim": false
        },
        {
          "locator_id": "L10",
          "kind": "number_literal",
          "quote": "0.8363",
          "meaning_as_written": "Hasimoto K ratio for the same two blockage ratios",
          "source_field": "markdown",
          "start_char": 544,
          "end_char": 550,
          "start_line": 10,
          "end_line": 10,
          "occurrences": 1,
          "unique": true,
          "resolvable": true,
          "is_claim": false
        },
        {
          "locator_id": "L11",
          "kind": "number_literal",
          "quote": "a/L=1/6",
          "meaning_as_written": "first blockage ratio",
          "source_field": "markdown",
          "start_char": 503,
          "end_char": 510,
          "start_line": 10,
          "end_line": 10,
          "occurrences": 1,
          "unique": true,
          "resolvable": true,
          "is_claim": false
        },
        {
          "locator_id": "L12",
          "kind": "number_literal",
          "quote": "1.112 %",
          "meaning_as_written": "Poiseuille error, first entry",
          "source_field": "markdown",
          "start_char": 577,
          "end_char": 584,
          "start_line": 12,
          "end_line": 12,
          "occurrences": 1,
          "unique": true,
          "resolvable": true,
          "is_claim": false
        },
        {
          "locator_id": "L13",
          "kind": "number_literal",
          "quote": "0.278 %",
          "meaning_as_written": "Poiseuille error, second entry",
          "source_field": "markdown",
          "start_char": 585,
          "end_char": 592,
          "start_line": 12,
          "end_line": 12,
          "occurrences": 1,
          "unique": true,
          "resolvable": true,
          "is_claim": false
        },
        {
          "locator_id": "L14",
          "kind": "number_literal",
          "quote": "0.070 %",
          "meaning_as_written": "Poiseuille error, third entry",
          "source_field": "markdown",
          "start_char": 593,
          "end_char": 600,
          "start_line": 12,
          "end_line": 12,
          "occurrences": 1,
          "unique": true,
          "resolvable": true,
          "is_claim": false
        },
        {
          "locator_id": "L15",
          "kind": "number_literal",
          "quote": "阶 2.00",
          "meaning_as_written": "observed Poiseuille convergence order",
          "source_field": "markdown",
          "start_char": 601,
          "end_char": 607,
          "start_line": 12,
          "end_line": 12,
          "occurrences": 1,
          "unique": true,
          "resolvable": true,
          "is_claim": false
        },
        {
          "locator_id": "L16",
          "kind": "number_literal",
          "quote": "4e-9",
          "meaning_as_written": "wall force balance residual",
          "source_field": "markdown",
          "start_char": 615,
          "end_char": 619,
          "start_line": 12,
          "end_line": 12,
          "occurrences": 1,
          "unique": true,
          "resolvable": true,
          "is_claim": false
        },
        {
          "locator_id": "L17",
          "kind": "number_literal",
          "quote": "1e5 步",
          "meaning_as_written": "stability run length in steps",
          "source_field": "markdown",
          "start_char": 624,
          "end_char": 629,
          "start_line": 12,
          "end_line": 12,
          "occurrences": 1,
          "unique": true,
          "resolvable": true,
          "is_claim": false
        },
        {
          "locator_id": "L18",
          "kind": "number_literal",
          "quote": "3e-16",
          "meaning_as_written": "third-moment residual",
          "source_field": "markdown",
          "start_char": 634,
          "end_char": 639,
          "start_line": 12,
          "end_line": 12,
          "occurrences": 1,
          "unique": true,
          "resolvable": true,
          "is_claim": false
        }
      ],
      "artifact_probe": {
        "probes": [
          {
            "url": "http://127.0.0.1:8010/api/v1/openapi.json",
            "http_status": 404
          },
          {
            "url": "http://127.0.0.1:8010/api/v1/tensor/reports/12565/artifacts",
            "http_status": 404
          },
          {
            "url": "http://127.0.0.1:8010/api/v1/tensor/reports/12565/figures",
            "http_status": 404
          },
          {
            "url": "http://127.0.0.1:8010/api/v1/tensor/artifacts?report_id=12565",
            "http_status": 404
          }
        ],
        "conclusion": "no reachable endpoint serves payloads for this record; declared artifact paths therefore stop at locator level (referenced_unresolved), never at content level"
      },
      "identity_observations": [
        {
          "observation": "the contract title mentions nu_formula, the markdown body never does",
          "check": "\"nu_formula\" in markdown",
          "result": false,
          "in_record_title": true,
          "note": "the body names the formula-viscosity normalisation by its expression (tau-1/2)/3, so the title's token cannot be located as markdown text; it is registered via source.title only"
        },
        {
          "observation": "the markdown H1 states the corrected report id, not the errata's title",
          "check": "markdown.split(chr(10))[0]",
          "result": "# P156W2-N03 报告勘误（对应 report id 12563）",
          "note": "locator anchor for A01; the record title lives in the title field, not in H1"
        },
        {
          "observation": "figure list is empty for this record",
          "check": "len(record.figures)",
          "result": 0,
          "note": "the record declares no figures, so no attachment metadata can be registered"
        }
      ],
      "claims": [],
      "claims_empty_reason": "objective.register_assets=true / classify_report_type=false and constraint no_forced_claim_generation=true: this工序 registers asset identity and locators only. Extraction and claim formation belong to downstream工序, so an empty claims array is the complete result, not an omission. Nothing here is marked verified; verification is computed by the platform gate.",
      "integrity": {
        "quote_uniqueness": {
          "assets_quoted": 8,
          "anchors_quoted": 18,
          "non_unique_quotes": [],
          "all_unique": true
        },
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "duplicate_asset_ids": [],
        "ids_unique": true
      },
      "limitations": [
        "single-report scope: only report_id=12565 is read; report 12563 (named in the markdown) and its artifacts are outside this package's boundary and stay unresolved",
        "no extraction: no number is interpreted, compared or promoted to a claim; literal anchors record positions only",
        "hash equality is a mechanical identity check, not an endorsement of the errata's numbers; verification stays with the platform gate",
        "the corrected values (e.g. the 7.59 % variant) live in the upstream artifact JSON, which this package cannot read, so no value-level cross-check is made here",
        "Hasimoto is cited by name only; no year/edition/DOI appears in the markdown"
      ]
    }
  },
  "claims": []
}
```
