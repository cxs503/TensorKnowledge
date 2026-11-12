# KF-RESULT wp-7878-01

**tags**: kf-wp:wp-7878-01, asset-registration, report-7878, lane-C, TensorKnowledge, draft
**package_id**: wp-7878-01 ｜ **task_type**: 01-asset-registration ｜ **report_id**: 7878
**lane**: C ｜ **repo**: TensorKnowledge ｜ **source_uri**: `tensor://reports/7878`

---

## ① 本工序做了什么

本工作包做且只做 `report_id=7878`（《P151-N05 完整干舷与吨位丈量验证链：ICLL 1966 修正链 + IMO Tonnage 1969（台账 STAB-FREEBOARD）》）的**资产登记**（工序 `01-asset-registration`）：

1. 确认 `report_id=7878` 与其 `markdown` 字段的字节哈希一一对应：独立重算
   `sha256:ce890ca0df1440fe3339a7eece9a31f9b0fc767eb6cb43d9991b446f42c8b1fb`，与契约声明 `source_hash` **逐字节一致**；
   `chars=7386`（= python str 长度，与契约 `chars` 相同），UTF-8 字节
   `10880`（CJK 正文两者必然不同，口径已写明）。
2. 登记可解析的**附件**：报告记录 `figures[]` 的 5 条 png 元数据
   （name + caption），并与正文 ④ 节逐字路径互相绑定。
3. 登记正文声明的**工件引用**：代码 / 测试 / 数据工件 / 台账共 11 项，
   每项给出逐字引文 + 行号 + 字符偏移。
4. 登记正文内**可解析的块结构**：5 个 pipe 表 + 1 个 fenced 文本块，
   只登记结构（数据行数 / 表头列数 / 起始行），**不抽取任何数值**。
5. **不做抽取、不分类、不产生 claim**（契约 `objective.classify_report_type: false`，
   `claims` 允许空数组）。**没有任何结论被标成 verified**——哈希相等只是机械身份校验，
   verification 由平台门计算。

边界遵守：只读 `GET /api/v1/tensor/reports/7878` 这一份记录；未读写任何其它 report_id；
未改写上游或其它工作包的产物。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **契约入参**：`package_id=wp-7878-01`、`report_id=7878`、`source_field=markdown`、
   `source_hash=sha256:ce890ca0…c8b1fb`、`chars=7386`、`title`、`scenario_key=ship_stability_freeboard_tonnage`；
   六条 `acceptance` 直接作为自检表（见 ⑥）。
2. **取源**：`POST /api/v1/auth/login`（凭据只从环境变量 `TENSOR_AGENT_USER` /
   `TENSOR_AGENT_PASS` 读取，不落盘、不进仓库）→ `GET /api/v1/tensor/reports/7878`（Bearer），
   取 `markdown` 原文；同记录 `title/scenario_key/mission_id/status/created_at/tags/figures`
   一并登记为元数据（`record_identity`）。
3. **独立哈希**：`hashlib.sha256(markdown.encode('utf-8'))`，与契约 `source_hash` 逐字比较；
   不一致则脚本 `SystemExit`（失败即不出产物）。同时记录字符数与 UTF-8 字节数。
4. **零手抄定位**：脚本内 `A[]` 引文表逐条用 `str.find` 解析；每条记录 `char_offset` /
   `line` / `occurrences`，任一引文未命中即 `SystemExit`，所以本报告的每个引文片段都是
   **机器命中**，不是人工计数。解析结果落 `docs/kf/wp-7878-01/locator_check.json`。
5. **结构登记（不抽取）**：pipe 表只算 `data_rows`（表头后连续 `|` 行数）与 `header_cells`；
   fenced 块只登记起始行与首个内容行引文。
6. **附件端点探测**：对 `/openapi.json`、`/tensor/reports/7878/artifacts`、
   `/tensor/reports/7878/figures`、`/tensor/artifacts?report_id=7878` 逐一探测（带 Bearer），
   结果见下表——没有端点提供 payload，所以图片/JSON 只能登记到"路径/元数据"层级，如实写
   `resolution.status=metadata_only / locator_resolved`、`content_retrievable=false`。

| 探测端点 | 结果 |
|---|---|
| `/openapi.json` | HTTP 404 |
| `/tensor/reports/7878/artifacts` | HTTP 404 |
| `/tensor/reports/7878/figures` | HTTP 404 |
| `/tensor/artifacts?report_id=7878` | HTTP 404 |

7. **组信封 + 机器校验**：按 `schemas/kf_result.v1.schema.json`（draft 2020-12）组
   `kf_result.v1` 信封，`Draft202012Validator.check_schema` + `jsonschema.validate` 通过才写盘；
   本报告正文的 json 块由脚本从 `kf_result.json` **原样注入**（无手抄）。
8. **一键复跑**：`python3 scripts/kf_wp7878_01_register.py`（需平台凭据环境变量），
   离线自检：`python3 -m pytest -q tests/test_kf_wp7878_01.py`。

## ③ 产出物清单

| 输出文件 | 路径 | 要点 |
|---|---|---|
| **asset_manifest.json**（契约声明输出） | `docs/kf/wp-7878-01/asset_manifest.json` | 23 个 asset（code_file=2, data_artifact=5, declared_input_glob=1, figure=5, inline_fenced_block=1, inline_markdown_table=5, ledger=1, report_markdown=1, test_file=1, tool=1）；hash 一致；locator 22/22 命中；claims=[] |
| 源文逐字节副本 | `docs/kf/wp-7878-01/source.md` | 平台取回的 markdown 原文字节（供离线子串复核） |
| 重算摘要 | `docs/kf/wp-7878-01/sha256.txt` | `sha256:ce890ca0df1440fe3339a7eece9a31f9b0fc767eb6cb43d9991b446f42c8b1fb` |
| 定位校验报告 | `docs/kf/wp-7878-01/locator_check.json` | 22 条引文全部命中，含偏移/行号/命中次数 |
| 结果信封 | `docs/kf/wp-7878-01/kf_result.json` | `kf_result.v1`，已过 `jsonschema` draft 2020-12 校验 |
| 本报告正文 | `docs/kf/wp-7878-01/report_body.md`、`docs/kf_result_wp-7878-01.md` | 六段 + 唯一一个 json 代码块 |
| 登记脚本 | `scripts/kf_wp7878_01_register.py` | 取源/哈希/22 条引文解析/清单+信封生成/正文渲染（任一失败即非零退出） |
| 离线自检测试 | `tests/test_kf_wp7878_01.py` | 复算 sha256、逐条子串、行号自洽、schema 校验、id 唯一、claims 为空 |

资产清单（`kind` → `uri`，行号指 `source.md` 的 1-based 行）：

| asset_id | kind | uri | 定位行 | 结构 | resolution |
|---|---|---|---|---|---|
| `r7878:source` | report_markdown | `tensor://reports/7878` | - | - | resolved |
| `r7878:figure:fig1` | figure | `docs/figures/p151n05/fig1_tabular_freeboard_continuity.png` | 89 | - | metadata_only |
| `r7878:figure:fig2` | figure | `docs/figures/p151n05/fig2_correction_chain.png` | 91 | - | metadata_only |
| `r7878:figure:fig3` | figure | `docs/figures/p151n05/fig3_tonnage_piecewise.png` | 93 | - | metadata_only |
| `r7878:figure:fig4` | figure | `docs/figures/p151n05/fig4_five_hull_closure.png` | 95 | - | metadata_only |
| `r7878:figure:fig5` | figure | `docs/figures/p151n05/fig5_sheer_three_cases.png` | 97 | - | metadata_only |
| `r7878:code:run_verification` | code_file | `artifacts/p151n05/run_verification.py` | 3 | - | locator_resolved |
| `r7878:glob:run_verification_json` | declared_input_glob | `artifacts/p151n05/*.json` | 4 | - | locator_resolved |
| `r7878:test:freeboard_tonnage` | test_file | `tests/test_freeboard_tonnage_p151n05.py` | 5 | - | locator_resolved |
| `r7878:code:freeboard_tonnage_api` | code_file | `backend/api/freeboard_tonnage.py` | 50 | - | locator_resolved |
| `r7878:data:icll1966_freeboard_table` | data_artifact | `backend/data/icll1966_freeboard_table.json` | 104 | - | locator_resolved |
| `r7878:tool:gen_icll1966_surrogate_table` | tool | `tools/gen_icll1966_surrogate_table.py` | 144 | - | locator_resolved |
| `r7878:data:standard_models_detailed` | data_artifact | `backend/data/standard_models_detailed.py` | 22 | - | locator_resolved |
| `r7878:data:acceptance_json` | data_artifact | `artifacts/p151n05/acceptance.json` | 147 | - | locator_resolved |
| `r7878:data:five_hull_closure_json` | data_artifact | `artifacts/p151n05/five_hull_closure.json` | 147 | - | locator_resolved |
| `r7878:data:tonnage_json` | data_artifact | `artifacts/p151n05/tonnage.json` | 147 | - | locator_resolved |
| `r7878:ledger:STAB-FREEBOARD` | ledger | `artifacts/ledger/STAB-FREEBOARD.jsonl` | 148 | - | locator_resolved |
| `r7878:table:hull_geometry` | inline_markdown_table | `in-report://7878/table/hull_geometry` | 25 | 5 行 × 18 列 | locator_resolved |
| `r7878:table:criteria` | inline_markdown_table | `in-report://7878/table/criteria` | 57 | 8 行 × 4 列 | locator_resolved |
| `r7878:table:node_continuity` | inline_markdown_table | `in-report://7878/table/node_continuity` | 70 | 4 行 × 6 列 | locator_resolved |
| `r7878:table:sheer_cases` | inline_markdown_table | `in-report://7878/table/sheer_cases` | 79 | 5 行 × 4 列 | locator_resolved |
| `r7878:table:error_judgement` | inline_markdown_table | `in-report://7878/table/error_judgement` | 128 | 9 行 × 4 列 | locator_resolved |
| `r7878:block:icll_chain_diagram` | inline_fenced_block | `in-report://7878/block/icll_chain_diagram` | 17 | - | locator_resolved |

附件（记录侧元数据，`origin=record.figures`）：

| 附件名 | 标记行 | caption（record.figures） |
|---|---|---|
| `fig1_tabular_freeboard_continuity.png` | 89 | 图1 ICLL 1966 表列干舷 f0(L)（A/B 两型）与判据 (a) 四个结点（标注实测跳变 <3e-6 相对），灰区为 1 m 网格区段。 |
| `fig2_correction_chain.png` | 91 | 图2 干舷链各项修正随 L 的分解（自相似船型族）；Reg 31 修正率分段点 L=120 m 无折角跳变（120/0.48=250）。 |
| `fig3_tonnage_piecewise.png` | 93 | 图3 GT=K1·V（右轴 K1）与 NT 的 0.30·GT 下界切换：max 函数在切换点相对跳变 0（Reg 4）。 |
| `fig4_five_hull_closure.png` | 95 | 图4 五船型 assign 最小干舷 vs 实船型干舷 D−T，及 Cb 闭合偏差对 3% 几何门的余量（最大 2.50%）。 |
| `fig5_sheer_three_cases.png` | 97 | 图5 Reg 38 舷弧修正三工况：零舷弧（+）/标准（0）/双倍舷弧（−）符号分离，且严格反对称。 |

## ④ 证据定位表

**A. 源记录身份（字段 → 值；值全部来自 API 返回与本地重算，零手抄）**

| 字段 | 值 |
|---|---|
| report_id (契约/记录) | 7878 / 7878 |
| title (记录) | P151-N05 完整干舷与吨位丈量验证链：ICLL 1966 修正链 + IMO Tonnage 1969（台账 STAB-FREEBOARD） |
| scenario_key (记录) | ship_stability_freeboard_tonnage |
| mission_id (记录) | 6651 |
| status (记录) | published |
| created_at (记录) | 2026-11-08T06:49:22.621806+00:00 |
| figure_records (记录) | 5 |
| source_field (契约) | markdown |
| source_hash (独立重算) | sha256:ce890ca0df1440fe3339a7eece9a31f9b0fc767eb6cb43d9991b446f42c8b1fb |
| source_hash (契约声明) | sha256:ce890ca0df1440fe3339a7eece9a31f9b0fc767eb6cb43d9991b446f42c8b1fb |
| hash 是否一致 | 是 |
| chars (契约 = python str 长度) | 7386 / 7386 |
| bytes_utf8 (独立计数) | 10880 |
| title / scenario_key 与契约一致 | 是 / 是 |

**B. 引文 → 原文逐字片段**（偏移/行号由 `str.find` 机械给出）

| locator_id | asset_id | 含义 | 原文逐字引文 | 行 | 字符偏移 | 命中次数 |
|---|---|---|---|---|---|---|
| L01 | `r7878:figure:fig1` | path quoted verbatim from the figure list; caption taken from record.figures | ` docs/figures/p151n05/fig1_tabular_freeboard_continuity.png ` | 89 | 4207 | 2 |
| L02 | `r7878:figure:fig2` | path quoted verbatim from the figure list; caption taken from record.figures | ` docs/figures/p151n05/fig2_correction_chain.png ` | 91 | 4320 | 2 |
| L03 | `r7878:figure:fig3` | path quoted verbatim from the figure list; caption taken from record.figures | ` docs/figures/p151n05/fig3_tonnage_piecewise.png ` | 93 | 4433 | 2 |
| L04 | `r7878:figure:fig4` | path quoted verbatim from the figure list; caption taken from record.figures | ` docs/figures/p151n05/fig4_five_hull_closure.png ` | 95 | 4543 | 2 |
| L05 | `r7878:figure:fig5` | path quoted verbatim from the figure list; caption taken from record.figures | ` docs/figures/p151n05/fig5_sheer_three_cases.png ` | 97 | 4647 | 2 |
| L06 | `r7878:code:run_verification` | producer of the report body (numbers programmatically injected) | `` `python3 artifacts/p151n05/run_verification.py` `` | 3 | 62 | 1 |
| L07 | `r7878:glob:run_verification_json` | declared input glob of run_verification.py; expanded members registered separately | `` `artifacts/p151n05/*.json` `` | 4 | 124 | 1 |
| L08 | `r7878:test:freeboard_tonnage` | test module backing the 47-passed statement (count itself not re-run here) | `` tests/test_freeboard_tonnage_p151n05.py` → **47 passed** `` | 5 | 178 | 1 |
| L09 | `r7878:code:freeboard_tonnage_api` | pure functions + FastAPI routes, registered under /api/v1/freeboard-tonnage/* | `` `backend/api/freeboard_tonnage.py`（纯函数 + FastAPI 路由，已注册 `` | 50 | 2720 | 1 |
| L10 | `r7878:data:icll1966_freeboard_table` | tabular freeboard data artifact carrying provenance.status = SURROGATE | `` `backend/data/icll1966_freeboard_table.json` `` | 104 | 4835 | 2 |
| L11 | `r7878:tool:gen_icll1966_surrogate_table` | generator of the surrogate table (reproducible by the author's claim) | `` `tools/gen_icll1966_surrogate_table.py` `` | 144 | 6781 | 1 |
| L12 | `r7878:data:standard_models_detailed` | source of the 3 public benchmark hulls (KCS/KVLCC2/JBC) | `` `backend/data/standard_models_detailed.py` `` | 22 | 682 | 1 |
| L13 | `r7878:data:acceptance_json` | criteria (a)-(h) result JSON | `` `artifacts/p151n05/acceptance.json` `` | 147 | 6963 | 1 |
| L14 | `r7878:data:five_hull_closure_json` | five-hull Cb closure result JSON | `` `five_hull_closure.json` `` | 147 | 6999 | 1 |
| L15 | `r7878:data:tonnage_json` | GT/NT piecewise result JSON | `` `tonnage.json` `` | 147 | 7024 | 1 |
| L16 | `r7878:ledger:STAB-FREEBOARD` | ledger entry key STAB-FREEBOARD (per-criterion pass flags + figure paths) | `` `artifacts/ledger/STAB-FREEBOARD.jsonl` `` | 148 | 7045 | 1 |
| L17 | `r7878:table:hull_geometry` | section 1 five-hull geometry table | ` \| 船型 \| 类型 \| ICLL 型 \| L [m] \| B [m] \| ` | 25 | 767 | 1 |
| L18 | `r7878:table:criteria` | section 3 criterion (a)-(h) table | ` \| 判据 \| 阈值 \| 实测 \| 结论 \| ` | 57 | 2979 | 1 |
| L19 | `r7878:table:node_continuity` | section 3 (a) per-node continuity table | ` \| L [m] \| f0 [mm] \| 左极限相对差 \| ` | 70 | 3600 | 1 |
| L20 | `r7878:table:sheer_cases` | section 3 (d) Reg 38 three-case table | ` \| L [m] \| 标准舷弧 [m] \| 零舷弧 [m] \| 双倍舷弧 [m] \| ` | 79 | 3927 | 1 |
| L21 | `r7878:table:error_judgement` | section 6 per-quantity error judgement table (<3%?) | ` \| 关键量 \| 基准 \| 误差 \| <3%? \| ` | 128 | 6034 | 1 |
| L22 | `r7878:block:icll_chain_diagram` | section 1 fenced text diagram of the ICLL 1966 correction chain (no language tag) | ` f0(L, type)  --Reg30-->  +ΔCb(Cb>0.68)  --Reg32--> ` | 17 | 493 | 1 |

表中每条引文都能在 `docs/kf/wp-7878-01/source.md`（sha256 `sha256:ce890ca0df1440fe3339a7eece9a31f9b0fc767eb6cb43d9991b446f42c8b1fb`）内
逐字定位；平台可用同一子串检索二次确认。

## ⑤ 注意点与局限

1. **哈希相等 ≠ 内容正确**：本单只证明「`report_id=7878` 的 `markdown` 与契约 `source_hash`
   逐字节一致」。报告里的判据数字（如结点跳变 2.75e-04%、pytest 47 passed、Cb 闭合最大
   2.50%）是上游表述，本单**原样登记、未重跑、未复核**。
2. **工件在记录内不可取**：`backend/api/freeboard_tonnage.py`、`backend/data/icll1966_freeboard_table.json`、
   `tools/gen_icll1966_surrogate_table.py`、`tests/test_freeboard_tonnage_p151n05.py`、
   `artifacts/p151n05/*.json`、`artifacts/ledger/STAB-FREEBOARD.jsonl` 等路径**逐字来自正文**，
   但文件本体在产出仓（ship-performance-platform）里，既不在本记录中，也不在本次
   TensorKnowledge 检出内（检出内无 `backend/`，`artifacts/` 下无 `p151n05/`）。因此它们的
   `resolution.status=locator_resolved`、`content_retrievable=false`——**登记的是引用，
   不是内容**。
3. **图只有元数据**：5 个 png 的 name+caption 来自记录 `figures[]`，payload 未下载、未入库；
   正文 ④ 节与"审计链"两处都逐字出现同一路径（`locator.occurrences=2`），主定位取 ④ 节。
4. **不抽取**：5 个表 + 1 个 fenced 块只登记结构（行数/列数/起始行），表内数值一条未提；
   数值级登记属于后续抽取道次（工序 03），本单不越界。
5. **上游自述的诚实边界只作指针登记**：正文 ⑤ 自称表值 `provenance.status = "SURROGATE"`、
   绝对干舷与 GT/NT 绝对值为 `WITHHELD`——本单把它登记为引用指针，**不复核其真伪**。
6. **口径**：契约 `chars=7386` 是字符数（python `str` 长度），UTF-8 字节数 10880；
   两者不可混用。
7. **版本钉死**：登记只对本次取回的字节有效；上游若改 `markdown`，哈希即失配，需重跑本单。
8. **单一报告范围**：只读 7878，未触碰其它 report_id（互不覆盖前提）。
9. **本报告无图（显式理由）**：本工序是登记/元数据类工序，产出是资产清单 + 逐字定位
   （行号/字符偏移），没有场量也没有可画曲线——强行出图只会是装饰。上游 7878 的 5 张
   png 的 payload 在本平台不可取（②.6 的四个端点探测全 404），因此既不转绘也不臆造图；
   定量证据以 ④ 定位表（偏移/行号可机器复核）与 ⑥ 自检表呈现。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| valid_json | ☑ PASS | json.dumps/json.loads round-trip of the envelope and manifest |
| schema_pass | ☑ PASS | jsonschema Draft202012Validator against schemas/kf_result.v1.schema.json |
| source_locator_resolvable | ☑ PASS | 22/22 quotes resolved verbatim (offset+line recorded) |
| source_hash_matches | ☑ PASS | sha256:ce890ca0df1440fe3339a7eece9a31f9b0fc767eb6cb43d9991b446f42c8b1fb |
| no_duplicate_ids | ☑ PASS | 23 asset_ids, 23 distinct |
| all_claims_have_evidence_or_explicit_unresolved_status | ☑ PASS | claims=[] (no extraction by contract); nothing marked verified |

附注（不粉饰）：`all_claims_have_evidence_or_explicit_unresolved_status` 在 `claims=[]` 时
为**空集真**——本单按契约不做抽取，没有为凑指标而造 claim；没有失败项需要申报。
`review.required: false`，本单未做独立评审（`independent_reviewer: false`）。

## 复现

```bash
# 1) 一键重跑（需平台凭据环境变量 TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE）
python3 scripts/kf_wp7878_01_register.py

# 2) 离线复核（不需要凭据；对已入库 source.md 复算哈希 + 逐条子串 + schema）
python3 -m pytest -q tests/test_kf_wp7878_01.py

# 3) 手工抽验平台侧哈希与引文
curl -s "$TENSOR_API_BASE/tensor/reports/7878" -H "Authorization: Bearer $TOKEN" \
  | python3 -c 'import sys,json,hashlib;m=json.load(sys.stdin)["markdown"];print("sha256:"+hashlib.sha256(m.encode()).hexdigest())'
```

## 结果信封（kf_result.v1，唯一 json 代码块）

```json
{
  "package_id": "wp-7878-01",
  "task_type": "01-asset-registration",
  "report_id": "7878",
  "provenance": {
    "source_hash": "sha256:ce890ca0df1440fe3339a7eece9a31f9b0fc767eb6cb43d9991b446f42c8b1fb",
    "source_field": "markdown",
    "producer": "agent/m15603",
    "emitted_at": "2026-11-12T01:33:29+00:00",
    "notes": "source_hash recomputed with hashlib.sha256 over the UTF-8 bytes of the markdown field fetched from GET /api/v1/tensor/reports/7878; matches the contract hash sha256:ce890ca0df1440fe3339a7eece9a31f9b0fc767eb6cb43d9991b446f42c8b1fb. Hash equality is a mechanical identity check only - no claim in this package is marked verified, verification stays with the platform gate."
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-7878-01",
      "task_type": "01-asset-registration",
      "report_id": "7878",
      "contract_version": "1.0",
      "generated_at": "2026-11-12T01:33:29+00:00",
      "generator": "scripts/kf_wp7878_01_register.py",
      "schema_note": "asset_manifest.json is the contract-declared output of this work package; the platform envelope wrapping it is validated against schemas/kf_result.v1.schema.json (draft 2020-12). Shape follows the wp-7878-01 contract keys (package_id/task_type/report_id/provenance/outputs).",
      "provenance": {
        "source_uri": "tensor://reports/7878",
        "source_field": "markdown",
        "fetched_via": "GET /api/v1/tensor/reports/7878 (Bearer)",
        "hash_algo": "sha256",
        "hashed_bytes": "markdown encoded as utf-8",
        "source_hash": "sha256:ce890ca0df1440fe3339a7eece9a31f9b0fc767eb6cb43d9991b446f42c8b1fb",
        "source_hash_expected": "sha256:ce890ca0df1440fe3339a7eece9a31f9b0fc767eb6cb43d9991b446f42c8b1fb",
        "source_hash_matches": true,
        "source_chars": 7386,
        "source_bytes_utf8": 10880,
        "chars_expected": 7386,
        "chars_matches": true,
        "chars_semantics": "contract `chars` equals the python str length (code points); the utf-8 byte length differs (CJK body)",
        "record_identity": {
          "id": 7878,
          "title": "P151-N05 完整干舷与吨位丈量验证链：ICLL 1966 修正链 + IMO Tonnage 1969（台账 STAB-FREEBOARD）",
          "scenario_key": "ship_stability_freeboard_tonnage",
          "mission_id": 6651,
          "status": "published",
          "created_at": "2026-11-08T06:49:22.621806+00:00",
          "created_by": 1,
          "tags": [
            "ICLL1966",
            "干舷",
            "load-line",
            "IMO-Tonnage-1969",
            "GT/NT",
            "舷弧修正",
            "几何前置门",
            "P151-N05",
            "STAB-FREEBOARD"
          ],
          "figure_records": 5
        },
        "title_matches_contract": true,
        "scenario_key_matches_contract": true
      },
      "identity_granularity": "asset identity is asset-level: one id per distinct registered reference (figure path, artifact path, inline table, inline block); a quote occurring on several lines is registered once with `locator.occurrences` > 1 and its primary line.",
      "resolution_status_vocabulary": {
        "resolved": "asset bytes fetched and hashed in this package (source markdown only)",
        "locator_resolved": "identity located verbatim in the registered markdown; content bytes not retrievable / not extracted by design",
        "metadata_only": "only record-side metadata (name+caption) is available; no payload",
        "unresolved": "identity could not be located - none in this package"
      },
      "assets": [
        {
          "asset_id": "r7878:source",
          "kind": "report_markdown",
          "uri": "tensor://reports/7878",
          "format": "markdown",
          "origin": "record.markdown",
          "locator": {
            "scheme": "report_field",
            "field": "markdown",
            "section": "whole record"
          },
          "resolution": {
            "status": "resolved",
            "locator_resolvable": true,
            "content_retrievable": true,
            "note": "bytes fetched from GET /api/v1/tensor/reports/7878 and hashed locally"
          },
          "content_extracted": false
        },
        {
          "asset_id": "r7878:figure:fig1",
          "kind": "figure",
          "uri": "docs/figures/p151n05/fig1_tabular_freeboard_continuity.png",
          "format": "png",
          "origin": "record.figures+markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "## ④ 结果图",
            "line": 89,
            "line_end": 89,
            "char_offset": 4207,
            "char_end": 4265,
            "occurrences": 2,
            "quote": "docs/figures/p151n05/fig1_tabular_freeboard_continuity.png"
          },
          "resolution": {
            "status": "metadata_only",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "path quoted verbatim from the figure list; caption taken from record.figures | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false
        },
        {
          "asset_id": "r7878:figure:fig2",
          "kind": "figure",
          "uri": "docs/figures/p151n05/fig2_correction_chain.png",
          "format": "png",
          "origin": "record.figures+markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "## ④ 结果图",
            "line": 91,
            "line_end": 91,
            "char_offset": 4320,
            "char_end": 4366,
            "occurrences": 2,
            "quote": "docs/figures/p151n05/fig2_correction_chain.png"
          },
          "resolution": {
            "status": "metadata_only",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "path quoted verbatim from the figure list; caption taken from record.figures | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false
        },
        {
          "asset_id": "r7878:figure:fig3",
          "kind": "figure",
          "uri": "docs/figures/p151n05/fig3_tonnage_piecewise.png",
          "format": "png",
          "origin": "record.figures+markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "## ④ 结果图",
            "line": 93,
            "line_end": 93,
            "char_offset": 4433,
            "char_end": 4480,
            "occurrences": 2,
            "quote": "docs/figures/p151n05/fig3_tonnage_piecewise.png"
          },
          "resolution": {
            "status": "metadata_only",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "path quoted verbatim from the figure list; caption taken from record.figures | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false
        },
        {
          "asset_id": "r7878:figure:fig4",
          "kind": "figure",
          "uri": "docs/figures/p151n05/fig4_five_hull_closure.png",
          "format": "png",
          "origin": "record.figures+markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "## ④ 结果图",
            "line": 95,
            "line_end": 95,
            "char_offset": 4543,
            "char_end": 4590,
            "occurrences": 2,
            "quote": "docs/figures/p151n05/fig4_five_hull_closure.png"
          },
          "resolution": {
            "status": "metadata_only",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "path quoted verbatim from the figure list; caption taken from record.figures | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false
        },
        {
          "asset_id": "r7878:figure:fig5",
          "kind": "figure",
          "uri": "docs/figures/p151n05/fig5_sheer_three_cases.png",
          "format": "png",
          "origin": "record.figures+markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "## ④ 结果图",
            "line": 97,
            "line_end": 97,
            "char_offset": 4647,
            "char_end": 4694,
            "occurrences": 2,
            "quote": "docs/figures/p151n05/fig5_sheer_three_cases.png"
          },
          "resolution": {
            "status": "metadata_only",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "path quoted verbatim from the figure list; caption taken from record.figures | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false
        },
        {
          "asset_id": "r7878:code:run_verification",
          "kind": "code_file",
          "uri": "artifacts/p151n05/run_verification.py",
          "format": "py",
          "origin": "markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "# P151-N05 完整干舷与吨位丈量验证链（ICLL 1966 + IMO Tonnage 1969）",
            "line": 3,
            "line_end": 3,
            "char_offset": 62,
            "char_end": 109,
            "occurrences": 1,
            "quote": "`python3 artifacts/p151n05/run_verification.py`"
          },
          "resolution": {
            "status": "locator_resolved",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "producer of the report body (numbers programmatically injected) | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false
        },
        {
          "asset_id": "r7878:glob:run_verification_json",
          "kind": "declared_input_glob",
          "uri": "artifacts/p151n05/*.json",
          "format": "json-glob",
          "origin": "markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "# P151-N05 完整干舷与吨位丈量验证链（ICLL 1966 + IMO Tonnage 1969）",
            "line": 4,
            "line_end": 4,
            "char_offset": 124,
            "char_end": 150,
            "occurrences": 1,
            "quote": "`artifacts/p151n05/*.json`"
          },
          "resolution": {
            "status": "locator_resolved",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "declared input glob of run_verification.py; expanded members registered separately | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false
        },
        {
          "asset_id": "r7878:test:freeboard_tonnage",
          "kind": "test_file",
          "uri": "tests/test_freeboard_tonnage_p151n05.py",
          "format": "py",
          "origin": "markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "# P151-N05 完整干舷与吨位丈量验证链（ICLL 1966 + IMO Tonnage 1969）",
            "line": 5,
            "line_end": 5,
            "char_offset": 178,
            "char_end": 234,
            "occurrences": 1,
            "quote": "tests/test_freeboard_tonnage_p151n05.py` → **47 passed**"
          },
          "resolution": {
            "status": "locator_resolved",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "test module backing the 47-passed statement (count itself not re-run here) | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false
        },
        {
          "asset_id": "r7878:code:freeboard_tonnage_api",
          "kind": "code_file",
          "uri": "backend/api/freeboard_tonnage.py",
          "format": "py",
          "origin": "markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "## ② 怎么做的（方法 / 流程 / 工具链）",
            "line": 50,
            "line_end": 50,
            "char_offset": 2720,
            "char_end": 2775,
            "occurrences": 1,
            "quote": "`backend/api/freeboard_tonnage.py`（纯函数 + FastAPI 路由，已注册"
          },
          "resolution": {
            "status": "locator_resolved",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "pure functions + FastAPI routes, registered under /api/v1/freeboard-tonnage/* | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false
        },
        {
          "asset_id": "r7878:data:icll1966_freeboard_table",
          "kind": "data_artifact",
          "uri": "backend/data/icll1966_freeboard_table.json",
          "format": "json",
          "origin": "markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "## ⑤ 注意点（坑 / 局限 / 适用范围）",
            "line": 104,
            "line_end": 104,
            "char_offset": 4835,
            "char_end": 4879,
            "occurrences": 2,
            "quote": "`backend/data/icll1966_freeboard_table.json`"
          },
          "resolution": {
            "status": "locator_resolved",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "tabular freeboard data artifact carrying provenance.status = SURROGATE | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false
        },
        {
          "asset_id": "r7878:tool:gen_icll1966_surrogate_table",
          "kind": "tool",
          "uri": "tools/gen_icll1966_surrogate_table.py",
          "format": "py",
          "origin": "markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "## 审计链",
            "line": 144,
            "line_end": 144,
            "char_offset": 6781,
            "char_end": 6820,
            "occurrences": 1,
            "quote": "`tools/gen_icll1966_surrogate_table.py`"
          },
          "resolution": {
            "status": "locator_resolved",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "generator of the surrogate table (reproducible by the author's claim) | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false
        },
        {
          "asset_id": "r7878:data:standard_models_detailed",
          "kind": "data_artifact",
          "uri": "backend/data/standard_models_detailed.py",
          "format": "py",
          "origin": "markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "## ① 案例介绍（物理背景 / 几何 / 参数表）",
            "line": 22,
            "line_end": 22,
            "char_offset": 682,
            "char_end": 724,
            "occurrences": 1,
            "quote": "`backend/data/standard_models_detailed.py`"
          },
          "resolution": {
            "status": "locator_resolved",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "source of the 3 public benchmark hulls (KCS/KVLCC2/JBC) | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false
        },
        {
          "asset_id": "r7878:data:acceptance_json",
          "kind": "data_artifact",
          "uri": "artifacts/p151n05/acceptance.json",
          "format": "json",
          "origin": "markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "## 审计链",
            "line": 147,
            "line_end": 147,
            "char_offset": 6963,
            "char_end": 6998,
            "occurrences": 1,
            "quote": "`artifacts/p151n05/acceptance.json`"
          },
          "resolution": {
            "status": "locator_resolved",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "criteria (a)-(h) result JSON | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false
        },
        {
          "asset_id": "r7878:data:five_hull_closure_json",
          "kind": "data_artifact",
          "uri": "artifacts/p151n05/five_hull_closure.json",
          "format": "json",
          "origin": "markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "## 审计链",
            "line": 147,
            "line_end": 147,
            "char_offset": 6999,
            "char_end": 7023,
            "occurrences": 1,
            "quote": "`five_hull_closure.json`"
          },
          "resolution": {
            "status": "locator_resolved",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "five-hull Cb closure result JSON | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false
        },
        {
          "asset_id": "r7878:data:tonnage_json",
          "kind": "data_artifact",
          "uri": "artifacts/p151n05/tonnage.json",
          "format": "json",
          "origin": "markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "## 审计链",
            "line": 147,
            "line_end": 147,
            "char_offset": 7024,
            "char_end": 7038,
            "occurrences": 1,
            "quote": "`tonnage.json`"
          },
          "resolution": {
            "status": "locator_resolved",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "GT/NT piecewise result JSON | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false
        },
        {
          "asset_id": "r7878:ledger:STAB-FREEBOARD",
          "kind": "ledger",
          "uri": "artifacts/ledger/STAB-FREEBOARD.jsonl",
          "format": "jsonl",
          "origin": "markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "## 审计链",
            "line": 148,
            "line_end": 148,
            "char_offset": 7045,
            "char_end": 7084,
            "occurrences": 1,
            "quote": "`artifacts/ledger/STAB-FREEBOARD.jsonl`"
          },
          "resolution": {
            "status": "locator_resolved",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "ledger entry key STAB-FREEBOARD (per-criterion pass flags + figure paths) | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false
        },
        {
          "asset_id": "r7878:table:hull_geometry",
          "kind": "inline_markdown_table",
          "uri": "in-report://7878/table/hull_geometry",
          "format": null,
          "origin": "markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "## ① 案例介绍（物理背景 / 几何 / 参数表）",
            "line": 25,
            "line_end": 25,
            "char_offset": 767,
            "char_end": 803,
            "occurrences": 1,
            "quote": "| 船型 | 类型 | ICLL 型 | L [m] | B [m] |"
          },
          "resolution": {
            "status": "locator_resolved",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "section 1 five-hull geometry table | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false,
          "structure": {
            "data_rows": 5,
            "header_cells": 18
          }
        },
        {
          "asset_id": "r7878:table:criteria",
          "kind": "inline_markdown_table",
          "uri": "in-report://7878/table/criteria",
          "format": null,
          "origin": "markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "## ③ 计算结果（判据数字，全部程序化注入）",
            "line": 57,
            "line_end": 57,
            "char_offset": 2979,
            "char_end": 3000,
            "occurrences": 1,
            "quote": "| 判据 | 阈值 | 实测 | 结论 |"
          },
          "resolution": {
            "status": "locator_resolved",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "section 3 criterion (a)-(h) table | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false,
          "structure": {
            "data_rows": 8,
            "header_cells": 4
          }
        },
        {
          "asset_id": "r7878:table:node_continuity",
          "kind": "inline_markdown_table",
          "uri": "in-report://7878/table/node_continuity",
          "format": null,
          "origin": "markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "### (a) 结点连续性逐点",
            "line": 70,
            "line_end": 70,
            "char_offset": 3600,
            "char_end": 3628,
            "occurrences": 1,
            "quote": "| L [m] | f0 [mm] | 左极限相对差 |"
          },
          "resolution": {
            "status": "locator_resolved",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "section 3 (a) per-node continuity table | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false,
          "structure": {
            "data_rows": 4,
            "header_cells": 6
          }
        },
        {
          "asset_id": "r7878:table:sheer_cases",
          "kind": "inline_markdown_table",
          "uri": "in-report://7878/table/sheer_cases",
          "format": null,
          "origin": "markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "### (d) 舷弧修正三工况（Reg 38）",
            "line": 79,
            "line_end": 79,
            "char_offset": 3927,
            "char_end": 3968,
            "occurrences": 1,
            "quote": "| L [m] | 标准舷弧 [m] | 零舷弧 [m] | 双倍舷弧 [m] |"
          },
          "resolution": {
            "status": "locator_resolved",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "section 3 (d) Reg 38 three-case table | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false,
          "structure": {
            "data_rows": 5,
            "header_cells": 4
          }
        },
        {
          "asset_id": "r7878:table:error_judgement",
          "kind": "inline_markdown_table",
          "uri": "in-report://7878/table/error_judgement",
          "format": null,
          "origin": "markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "## ⑥ 误差判定（逐项回答\"是否 <3%\"）",
            "line": 128,
            "line_end": 128,
            "char_offset": 6034,
            "char_end": 6058,
            "occurrences": 1,
            "quote": "| 关键量 | 基准 | 误差 | <3%? |"
          },
          "resolution": {
            "status": "locator_resolved",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "section 6 per-quantity error judgement table (<3%?) | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false,
          "structure": {
            "data_rows": 9,
            "header_cells": 4
          }
        },
        {
          "asset_id": "r7878:block:icll_chain_diagram",
          "kind": "inline_fenced_block",
          "uri": "in-report://7878/block/icll_chain_diagram",
          "format": null,
          "origin": "markdown",
          "locator": {
            "scheme": "markdown_line",
            "source_field": "markdown",
            "section": "## ① 案例介绍（物理背景 / 几何 / 参数表）",
            "line": 17,
            "line_end": 17,
            "char_offset": 493,
            "char_end": 543,
            "occurrences": 1,
            "quote": "f0(L, type)  --Reg30-->  +ΔCb(Cb>0.68)  --Reg32-->"
          },
          "resolution": {
            "status": "locator_resolved",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "section 1 fenced text diagram of the ICLL 1966 correction chain (no language tag) | path/quote resolved in the registered markdown; the file itself is not part of the report record and no artifact endpoint serves it (see artifact_endpoint_probe)"
          },
          "content_extracted": false
        }
      ],
      "attachments": [
        {
          "name": "fig1_tabular_freeboard_continuity.png",
          "caption": "图1 ICLL 1966 表列干舷 f0(L)（A/B 两型）与判据 (a) 四个结点（标注实测跳变 <3e-6 相对），灰区为 1 m 网格区段。",
          "origin": "record.figures",
          "markdown_locator_line": 89,
          "caption_resolvable_in_markdown": null,
          "resolution": {
            "status": "metadata_only",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "name+caption from record.figures; PNG payload not downloaded, not checked in"
          }
        },
        {
          "name": "fig2_correction_chain.png",
          "caption": "图2 干舷链各项修正随 L 的分解（自相似船型族）；Reg 31 修正率分段点 L=120 m 无折角跳变（120/0.48=250）。",
          "origin": "record.figures",
          "markdown_locator_line": 91,
          "caption_resolvable_in_markdown": null,
          "resolution": {
            "status": "metadata_only",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "name+caption from record.figures; PNG payload not downloaded, not checked in"
          }
        },
        {
          "name": "fig3_tonnage_piecewise.png",
          "caption": "图3 GT=K1·V（右轴 K1）与 NT 的 0.30·GT 下界切换：max 函数在切换点相对跳变 0（Reg 4）。",
          "origin": "record.figures",
          "markdown_locator_line": 93,
          "caption_resolvable_in_markdown": null,
          "resolution": {
            "status": "metadata_only",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "name+caption from record.figures; PNG payload not downloaded, not checked in"
          }
        },
        {
          "name": "fig4_five_hull_closure.png",
          "caption": "图4 五船型 assign 最小干舷 vs 实船型干舷 D−T，及 Cb 闭合偏差对 3% 几何门的余量（最大 2.50%）。",
          "origin": "record.figures",
          "markdown_locator_line": 95,
          "caption_resolvable_in_markdown": null,
          "resolution": {
            "status": "metadata_only",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "name+caption from record.figures; PNG payload not downloaded, not checked in"
          }
        },
        {
          "name": "fig5_sheer_three_cases.png",
          "caption": "图5 Reg 38 舷弧修正三工况：零舷弧（+）/标准（0）/双倍舷弧（−）符号分离，且严格反对称。",
          "origin": "record.figures",
          "markdown_locator_line": 97,
          "caption_resolvable_in_markdown": null,
          "resolution": {
            "status": "metadata_only",
            "locator_resolvable": true,
            "content_retrievable": false,
            "note": "name+caption from record.figures; PNG payload not downloaded, not checked in"
          }
        }
      ],
      "artifact_endpoint_probe": {
        "base": "http://127.0.0.1:8010/api/v1",
        "probes": [
          {
            "path": "/openapi.json",
            "status": "HTTP 404"
          },
          {
            "path": "/tensor/reports/7878/artifacts",
            "status": "HTTP 404"
          },
          {
            "path": "/tensor/reports/7878/figures",
            "status": "HTTP 404"
          },
          {
            "path": "/tensor/artifacts?report_id=7878",
            "status": "HTTP 404"
          }
        ],
        "conclusion": "no reachable endpoint serves figure/artifact payloads for this record; the record exposes figures as name+caption metadata only, so binary/JSON payloads cannot be registered at content level in this work package"
      },
      "claims": [],
      "claims_note": "claims intentionally empty: task_type 01-asset-registration performs no extraction and the contract allows an empty array; nothing here is marked verified",
      "summary": {
        "assets": 23,
        "assets_by_kind": {
          "report_markdown": 1,
          "figure": 5,
          "code_file": 2,
          "declared_input_glob": 1,
          "test_file": 1,
          "data_artifact": 5,
          "tool": 1,
          "ledger": 1,
          "inline_markdown_table": 5,
          "inline_fenced_block": 1
        },
        "attachments": 5,
        "locators_checked": 22,
        "locators_resolved": 22,
        "duplicate_asset_ids": [],
        "claims": 0
      },
      "limitations": [
        "single-report scope: only report_id=7878 is read; no other report_id is touched",
        "no extraction: no number/quote from the body is promoted to a claim; table and block assets are registered as structure (rows/columns) only",
        "hash equality is a mechanical identity check, not an endorsement of the report's conclusions; verification stays with the platform gate",
        "referenced artifact paths are quoted from the markdown, but the files live in the producing repository (ship-performance-platform), not in this record",
        "the upstream self-declared table provenance (SURROGATE) is registered verbatim as a pointer, not re-checked",
        "the report's own numbers (e.g. 47 passed, 2.50% Cb deviation) are not re-executed here"
      ]
    }
  },
  "claims": []
}
```
