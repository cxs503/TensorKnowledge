# KF-RESULT wp-9777-01

**工序** 01-asset-registration ｜ **report_id** 9777 ｜ **scenario_key** `structural-dynamics/dsm-beam-modal`
**来源** `tensor://reports/9777` 字段 `markdown` ｜ sha256 `d5742ce0c54743d542de8bb36d79891a0cfe8997a1b6032827fa97df251dcbe7`
**字符/字节/行** 4341 / 6651 / 70 ｜ **claims** 0 条（契约允许空）
**repro_cmd** 见 ②

## ① 本工序做了什么

只做一件事：把报告 9777 的**源资产身份**登记成机器可校验的清单（`asset_manifest.json`），并为报告正文
声明过的附件/工件逐条建立**可解析定位**（1-based 行号 + 逐字引文 + 字符偏移 + 引文 sha256）。不做抽取、
不判报告类型、不写任何 claim、不给任何内容打 verified 标——verification 归平台门。

登记结果：**9 个资产**（`{"data_artifact_reference": 1, "figure_reference": 5, "source_code_reference": 2, "source_document": 1}`），
其中源文档 1 个 `resolved_in_source`，其余 8 个 `referenced_unresolved`
（5 张图仅存于平台记录元数据、3 处正文路径指向上游工作树）。报告自身哈希与契约声明
`hash_match=True`、字符数 `chars_match_contract=True`。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文（唯一信道）**：`GET $TENSOR_API_BASE/tensor/reports/9777`（Bearer 由
   `POST /auth/login` 换取）。`psql -d tensorplatform` 直读 `tensor_reports` 被拒
   （`permission denied for table tensor_reports`），故 API 是唯一来源；原文落地
   `docs/kf/wp-9777-01/source.md`（committed，供离线复算）。
2. **算哈希**：对 markdown 字符串的 UTF-8 字节算 sha256 → `sha256:d5742ce0c54743d542de8bb36d79891a0cfe8997a1b6032827fa97df251dcbe7`，与契约
   `source_hash` 逐字比对（`hash_match=True`），并把 chars `4341` 与契约
   `chars` 4341 比对。
3. **枚举资产**：源文档本体；平台记录 `figures[0..4]` 的 5 条 name+caption；正文路径锚点
   （`dsbeam.py`、`artifacts/m8404_dsm/audit_acceptance.py`、`results.json`）；另登记 5 条行内
   代码符号（函数/第三方调用/公式）作为 `symbol_references`（不计入 assets）。
4. **建定位器**：每个锚点在原文中找行 → 在该行内反复按分隔符切分（`，；。、`、`（）()`、`|`、
   `**`、行内反引号 span）→ 取**在全文中唯一**的最短子句作为引文，记录行号、
   `md.find(quote)` 字符偏移、引文 sha256、全文出现次数。拒绝括号/反引号不闭合、或截断在半个
   token 上的候选（踩坑记录见 ⑤）。
5. **解析判定（不臆造）**：源文档→`resolved_in_source`；5 图探测
   `GET /tensor/reports/9777/{figures,artifacts,attachments}` 三端点全 404 → 无字节可哈希 →
   `referenced_unresolved`；3 处正文路径在本交付树中逐一 `os.path.exists` 探测（全不存在，属上游
   TensorFEM/audit 工作树）→ `referenced_unresolved`，并在 `note` 写明"这是本检出范围，不是上游缺陷"。
6. **封信封并自检**：`kf_result.json` 只装 `outputs.asset_manifest.json` + `claims: []`；
   `verification.py` 6 条验收项逐条重算（**不是**回读自己写的字段）。
7. **一键复跑**（工作树根）：

```bash
python3 scripts/kf_wp9777_01_register.py all   # fetch + manifest + envelope + 6 项自检 + 图
python3 -m pytest tests/test_kf_wp9777_01.py -q  # 20 条离线验收测试
python3 scripts/kf_wp9777_01_report.py post     # 生成并提交本报告
```

工具链：Python 3.11 + 标准库（urllib/hashlib/json/re）+ `jsonschema` 4.26 + `matplotlib` 3.10；
未引入 scipy/pandas，无外网依赖（除平台 API）。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-9777-01/asset_manifest.json` | 登记主产物：schema=asset_manifest.v1、9 资产、9 定位器、5 符号引用、claims=[] |
| `docs/kf/wp-9777-01/kf_result.json` | 平台结果信封（package_id/task_type/report_id/provenance/outputs/claims），`provenance.source_hash` = 契约哈希 |
| `docs/kf/wp-9777-01/verification.json` | 6 条 acceptance 自检结果，`all_ok=True` |
| `docs/kf/wp-9777-01/source.md` | 原文 committed 副本（4341 chars），离线复算用 |
| `docs/kf/wp-9777-01/figures/fig1_asset_locator_map.png` | 图1 资产定位在报告行轴上的分布 + 解析状态直方图 |
| `scripts/kf_wp9777_01_register.py` | 登记工序脚本（build/envelope/verify/figure/all） |
| `scripts/kf_wp9777_01_report.py` | 报告生成 + 提交脚本（本文件即其输出） |
| `tests/test_kf_wp9777_01.py` | 20 条离线验收测试（独立重算哈希/定位，不 import 生产 verify） |
| `runs/wp-9777-01/source_9777.md`、`runs/wp-9777-01/report_9777.json` | 取数留痕（原文 + 平台记录快照） |

### 资产登记表（9 条）

| id | class | label | 行 | resolution | check | 引文 |
|---|---|---|---|---|---|---|
| A01 | source_document | report 9777 markdown | L1 | resolved_in_source | resolved | # 自由-自由 Timoshenko 梁精确 DSM 验收审计（节点 p423w2-n09） |
| A02 | figure_reference | 图1 (fig1_spectrum.png) | L46 | referenced_unresolved | unresolved | 图1 两个极限下的精确 DSM 频谱 |
| A03 | figure_reference | 图2 (fig2_mode_shapes.png) | L46 | referenced_unresolved | unresolved | 图2 自由-自由 1–3 阶两场精确振型（w/ψ/曲率） |
| A04 | figure_reference | 图3 (fig3_wittrick_williams.png) | L46 | referenced_unresolved | unresolved | 图3 J(ω) 阶梯 vs 独立根普查（极点处阶梯不跳） |
| A05 | figure_reference | 图4 (fig4_m6117_attribution.png) | L46 | referenced_unresolved | unresolved | 图4 m6117 归因 |
| A06 | figure_reference | 图5 (fig5_random_sweep.png) | L46 | referenced_unresolved | unresolved | 图5 100 组随机样本鲁棒性 |
| A07 | source_code_reference | dsbeam.py | L19 | referenced_unresolved | unresolved | - **本单在 dsbeam.py 修三处缺陷** |
| A08 | source_code_reference | artifacts/m8404_dsm/audit_acceptance.py | L20 | referenced_unresolved | unresolved | `artifacts/m8404_dsm/audit_acceptance.py` |
| A09 | data_artifact_reference | results.json | L22 | referenced_unresolved | unresolved | 全部来自 results.json |

未解析清单（8 条，全部显式声明，不隐藏）：

| id | name | 判定依据 |
|---|---|---|
| A02 | `fig1_spectrum.png` | (1) record figure name verbatim in markdown? (2) record caption verbatim in markdown? (3) figure bytes servable at /tensor/reports/9777/{figures,artifacts,attachments}? |
| A03 | `fig2_mode_shapes.png` | (1) record figure name verbatim in markdown? (2) record caption verbatim in markdown? (3) figure bytes servable at /tensor/reports/9777/{figures,artifacts,attachments}? |
| A04 | `fig3_wittrick_williams.png` | (1) record figure name verbatim in markdown? (2) record caption verbatim in markdown? (3) figure bytes servable at /tensor/reports/9777/{figures,artifacts,attachments}? |
| A05 | `fig4_m6117_attribution.png` | (1) record figure name verbatim in markdown? (2) record caption verbatim in markdown? (3) figure bytes servable at /tensor/reports/9777/{figures,artifacts,attachments}? |
| A06 | `fig5_random_sweep.png` | (1) record figure name verbatim in markdown? (2) record caption verbatim in markdown? (3) figure bytes servable at /tensor/reports/9777/{figures,artifacts,attachments}? |
| A07 | `dsbeam.py` | path exists in the TensorKnowledge delivery worktree at 'dsbeam.py'? |
| A08 | `artifacts/m8404_dsm/audit_acceptance.py` | path exists in the TensorKnowledge delivery worktree at 'artifacts/m8404_dsm/audit_acceptance.py'? |
| A09 | `results.json` | path exists in the TensorKnowledge delivery worktree at 'results.json'? |

图1（`fig1_asset_locator_map.png`）：左panel 为 9 个资产的定位区间在 70 行报告轴上的位置
（灰竖线=章节/首末行 identity fact），右panel 为 resolution 直方图；数据全部由 manifest 直接绘制。

## ④ 证据定位表（claim/字段 → 原文引文片段）

本工序不出 claim（`claims: []`，契约 `no_forced_claim_generation=true`）；下表是**资产定位器**的证据面，
每条均由平台可独立重算（逐字子串 + 引文 sha256 + 行号 + 唯一性）：

| id | 行 | quote_sha256(前16) | 引文片段（逐字） | 全文出现次数 | resolved |
|---|---|---|---|---|---|
| A01 | 1 | 35a3f1a0f3edd8fa | # 自由-自由 Timoshenko 梁精确 DSM 验收审计（节点 p423w2-n09） | 1 | yes |
| A02 | 46 | 84e7e2f901849ca7 | 图1 两个极限下的精确 DSM 频谱 | 1 | yes |
| A03 | 46 | 13269d1dfae553de | 图2 自由-自由 1–3 阶两场精确振型（w/ψ/曲率） | 1 | yes |
| A04 | 46 | 4426b62e20bba4cd | 图3 J(ω) 阶梯 vs 独立根普查（极点处阶梯不跳） | 1 | yes |
| A05 | 46 | f97f9d61312560b8 | 图4 m6117 归因 | 1 | yes |
| A06 | 46 | 50cadbd4822d7943 | 图5 100 组随机样本鲁棒性 | 1 | yes |
| A07 | 19 | 04a0388deba446ef | - **本单在 dsbeam.py 修三处缺陷** | 1 | yes |
| A08 | 20 | dffee517b6da5e89 | `artifacts/m8404_dsm/audit_acceptance.py` | 1 | yes |
| A09 | 22 | 43ace7db9479eb14 | 全部来自 results.json | 1 | yes |

行内代码符号引用（不计入 assets）：

| kind | 行 | 引文 |
|---|---|---|
| function | 19 | `mode_shape_full` |
| third_party_call | 19 | `scipy.optimize.brentq` |
| third_party_call | 19 | 惯性容差由 1e-12‖K‖ 改为 eigvalsh 向后误差界 + J≥0 钳位 |
| formula | 16 | `K(ω)=H⁻ᵀQH⁻¹` |
| formula | 17 | `J(ω)=n·J₀+s{K}−刚体数−谱阈值伪零` |

身份事实（首行/各节标题/末行，整行逐字比对，见 `asset_manifest.json → identity_facts`）：8 条全部复算一致。
**一处如实记录的不一致**：平台记录 title = 契约 title（战役长标题），而正文 H1 =
`# 自由-自由 Timoshenko 梁精确 DSM 验收审计（节点 p423w2-n09）`（节点级标题）——两者字符串不同，
清单原样登记双方（`h1_equals_record_title=False`），不做改写、不择一。

## ⑤ 注意点与局限

1. **图只有元数据、没有字节**：5 张图在记录里只有 name+caption，三候选字节端点全 404，故一律
   `referenced_unresolved` 且**不声明任何图哈希**。若后续平台提供图字节，应重跑本工序并把 5 条升级为
   `resolved_in_source` + 逐图 sha256。
2. **正文 ④ 的图注是元数据的改写**：正文按 `图1..图5` 标签复述，措辞与记录 caption 不同
   （`name_in_markdown=False`、
   `caption_in_markdown=False`），
   图身份只能按 name 绑定——清单把这一分歧写进 note，不假装图注可逐字定位。
3. **3 处正文路径在本检出不存在**：`dsbeam.py` / `artifacts/m8404_dsm/audit_acceptance.py` /
   `results.json` 属上游 TensorFEM+audit 工作树，TensorKnowledge 检出里没有 → 判 `referenced_unresolved`。
   这是**本检出范围**结论，不是"上游缺文件"的指控；不得据此推断上游造假。
4. **引文自动收窄的坑（本单踩到并修掉）**：按分隔符切分取最短唯一子句时，曾产出
   `；图3 J`、`J(ω)=n·J₀+s{` 这类截断在半个 token/未闭合括号上的引文。修复：候选引文必须括号
   `()（）{}` 与反引号成对，且行内反引号 span 优先作为候选；修后 9/9 资产引文与 5/5 符号引文全部
   合法逐字唯一。
5. **registration ≠ extraction**：本工序不判断报告结论真伪，也不评价 7/7 判据 PASS 是否成立；那是
   下游抽取/审计工序的事。清单里没有任何 `verified` 标记（契约硬约束）。
6. **哈希绑定口径**：`source_hash` 绑定的是平台返回的 markdown 字符串的 UTF-8 字节；存储侧任何改动
   （含空白）都会使它与契约声明失配并令门失败——这是设计意图，不是脆弱点。

## ⑥ 自检（逐条对照 acceptance）

| # | acceptance | 结果 | 依据 |
|---|---|---|---|
| 1 | valid_json | ✓ | asset_manifest.json / kf_result.json / verification.json 均被 json 解析 |
| 2 | schema_pass | ✓ | kf_result.v1 errors=0；asset_manifest.v1 形状 errors=0（仅放开 3 个他包 const） |
| 3 | source_locator_resolvable | ✓ | 9 asset locators + 8 identity facts + 5 symbol locators re-resolved (verbatim substring + quote_sha256 + char offset + declared line) |
| 4 | source_hash_matches | ✓ | live=sha256:d5742ce0c54743d5 = manifest = contract = envelope |
| 5 | no_duplicate_ids | ✓ | 9 ids, duplicates=[] |
| 6 | all_claims_have_evidence_or_explicit_unresolved_status | ✓ | 0 claims (empty array is contract-legal); empty-claims reason stated: True |

`all_ok = True`；`python3 -m pytest tests/test_kf_wp9777_01.py -q` → 20 passed。
以上为**自检**，非平台裁定；本单未把任何结论标 verified。

**误差判定（是否 <3%）**：本工序无物理量、无基准解——它登记的是文档身份与定位，唯一"误差面"是
字符串等价性，且已为**精确等价**（哈希逐字相同、9 条引文逐字子串命中、字符偏移一致），
因此不存在 >3% 的量化误差需要声明；若后续工序要做数值误差判定，应以报告 ⑥ 节的 `results.json` 原值为基准，
而该文件在本检出不可得（见 ⑤.3），故本工序**不对任何频率/百分比数值做复算或背书**。

## 附录：结果信封（交付信道：本文件唯一一个 JSON 代码块，内容与 `kf_result.json` 逐字节一致）

```json
{
  "package_id": "wp-9777-01",
  "task_type": "01-asset-registration",
  "report_id": "9777",
  "provenance": {
    "source_hash": "sha256:d5742ce0c54743d542de8bb36d79891a0cfe8997a1b6032827fa97df251dcbe7",
    "source_field": "markdown",
    "producer": "kf-worker/m15671",
    "emitted_at": "2026-11-12T01:43:30.272996+00:00",
    "notes": "sha256 recomputed from GET /tensor/reports/9777 markdown UTF-8 bytes (4341 chars); equals contract source_hash sha256:d5742ce0c54743d542de8bb36d79891a0cfe8997a1b6032827fa97df251dcbe7"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "manifest_version": "1.0",
      "package_id": "wp-9777-01",
      "task_type": "01-asset-registration",
      "report_id": "9777",
      "lane": "A",
      "generated_at": "2026-11-12T01:43:29.768857+00:00",
      "producer": "kf-worker/m15671",
      "source": {
        "uri": "tensor://reports/9777",
        "report_id": "9777",
        "source_uri": "tensor://reports/9777",
        "field": "markdown",
        "source_field": "markdown",
        "hash_alg": "sha256",
        "hash": "d5742ce0c54743d542de8bb36d79891a0cfe8997a1b6032827fa97df251dcbe7",
        "source_hash": "sha256:d5742ce0c54743d542de8bb36d79891a0cfe8997a1b6032827fa97df251dcbe7",
        "contract_source_hash": "sha256:d5742ce0c54743d542de8bb36d79891a0cfe8997a1b6032827fa97df251dcbe7",
        "hash_match": true,
        "chars": 4341,
        "contract_chars": 4341,
        "chars_match_contract": true,
        "bytes_utf8": 6651,
        "lines": 70,
        "has_crlf": false,
        "has_trailing_newline": true,
        "line_counting": "logical lines = markdown.rstrip(chr(10)).split(chr(10)); 1-based",
        "fetched_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/9777",
        "title": "精确 DSM Timoshenko 梁模态验收审计：7/7 判据 PASS、dsbeam 三处缺陷修复、m6117 6.28% 归因闭环",
        "scenario_key": "structural-dynamics/dsm-beam-modal",
        "contract_title": "精确 DSM Timoshenko 梁模态验收审计：7/7 判据 PASS、dsbeam 三处缺陷修复、m6117 6.28% 归因闭环",
        "contract_scenario_key": "structural-dynamics/dsm-beam-modal",
        "title_matches_contract": true,
        "scenario_matches_contract": true,
        "h1_title_in_markdown": "# 自由-自由 Timoshenko 梁精确 DSM 验收审计（节点 p423w2-n09）",
        "h1_equals_record_title": false,
        "mission_id": 8404,
        "status": "published",
        "created_at": "2026-11-09T08:30:05.170174+00:00",
        "platform_tags": [
          "DSM",
          "Timoshenko",
          "Wittrick-Williams",
          "modal",
          "TensorFEM",
          "m6117",
          "acceptance-audit"
        ],
        "platform_figures": [
          {
            "name": "fig1_spectrum.png",
            "caption": "图1 精确 DSM 两极限：(左) 细长梁 (βL)² 与 EB 常数重合；(右) 深梁剪切+转动惯量致频率下降"
          },
          {
            "name": "fig2_mode_shapes.png",
            "caption": "图2 自由-自由 1–3 阶两场精确振型 w / ψ / 曲率（whipping 应力恢复用）"
          },
          {
            "name": "fig3_wittrick_williams.png",
            "caption": "图3 J(ω) 阶梯 vs 独立根普查零点；红点线为元素极点（J 在极点不跳）"
          },
          {
            "name": "fig4_m6117_attribution.png",
            "caption": "图4 m6117 归因：左 1–4 阶对比，右 偏差分解 +0.027 % / −5.89 % / 6.28 %"
          },
          {
            "name": "fig5_random_sweep.png",
            "caption": "图5 100 组随机样本：闭式相对差 vs 细长度；频率随 L 单调下降"
          }
        ]
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "source_document",
          "label": "report 9777 markdown",
          "in_report_section": "document",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 4341,
            "start_line": 1,
            "end_line": 70,
            "quote": "# 自由-自由 Timoshenko 梁精确 DSM 验收审计（节点 p423w2-n09）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET /tensor/reports/9777 markdown bytes -> sha256 recomputed locally",
            "result": "resolved"
          },
          "note": "Whole-document asset: 4341 chars / 6651 UTF-8 bytes / 70 lines; sha256 sha256:d5742ce0c54743d542de8bb36d79891a0cfe8997a1b6032827fa97df251dcbe7 matches the contract source_hash=True. Quote above = H1 line (locator spans the document, quote anchors its identity).",
          "name": "report_9777.md",
          "bytes_utf8": 6651,
          "sha256": "sha256:d5742ce0c54743d542de8bb36d79891a0cfe8997a1b6032827fa97df251dcbe7"
        },
        {
          "asset_id": "A02",
          "asset_class": "figure_reference",
          "label": "图1 (fig1_spectrum.png)",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 2948,
            "end_char": 2966,
            "start_line": 46,
            "end_line": 46,
            "quote": "图1 两个极限下的精确 DSM 频谱",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "(1) record figure name verbatim in markdown? (2) record caption verbatim in markdown? (3) figure bytes servable at /tensor/reports/9777/{figures,artifacts,attachments}?",
            "result": "unresolved"
          },
          "note": "Declared in the platform record metadata as name+caption and referenced in body prose by the label 图1. name_in_markdown=False, caption_in_markdown=False; the three candidate byte endpoints all return 404, so no figure bytes exist to hash -- registered as referenced_unresolved (no hash claimed).",
          "name": "fig1_spectrum.png",
          "caption_source": "record.figures[0].caption",
          "figures_endpoint_probe": {
            "/tensor/reports/9777/figures": {
              "http_status": 404,
              "bytes": 22
            },
            "/tensor/reports/9777/artifacts": {
              "http_status": 404,
              "bytes": 22
            },
            "/tensor/reports/9777/attachments": {
              "http_status": 404,
              "bytes": 22
            }
          }
        },
        {
          "asset_id": "A03",
          "asset_class": "figure_reference",
          "label": "图2 (fig2_mode_shapes.png)",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 2967,
            "end_char": 2995,
            "start_line": 46,
            "end_line": 46,
            "quote": "图2 自由-自由 1–3 阶两场精确振型（w/ψ/曲率）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "(1) record figure name verbatim in markdown? (2) record caption verbatim in markdown? (3) figure bytes servable at /tensor/reports/9777/{figures,artifacts,attachments}?",
            "result": "unresolved"
          },
          "note": "Declared in the platform record metadata as name+caption and referenced in body prose by the label 图2. name_in_markdown=False, caption_in_markdown=False; the three candidate byte endpoints all return 404, so no figure bytes exist to hash -- registered as referenced_unresolved (no hash claimed).",
          "name": "fig2_mode_shapes.png",
          "caption_source": "record.figures[1].caption",
          "figures_endpoint_probe": {
            "/tensor/reports/9777/figures": {
              "http_status": 404,
              "bytes": 22
            },
            "/tensor/reports/9777/artifacts": {
              "http_status": 404,
              "bytes": 22
            },
            "/tensor/reports/9777/attachments": {
              "http_status": 404,
              "bytes": 22
            }
          }
        },
        {
          "asset_id": "A04",
          "asset_class": "figure_reference",
          "label": "图3 (fig3_wittrick_williams.png)",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 2996,
            "end_char": 3024,
            "start_line": 46,
            "end_line": 46,
            "quote": "图3 J(ω) 阶梯 vs 独立根普查（极点处阶梯不跳）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "(1) record figure name verbatim in markdown? (2) record caption verbatim in markdown? (3) figure bytes servable at /tensor/reports/9777/{figures,artifacts,attachments}?",
            "result": "unresolved"
          },
          "note": "Declared in the platform record metadata as name+caption and referenced in body prose by the label 图3. name_in_markdown=False, caption_in_markdown=False; the three candidate byte endpoints all return 404, so no figure bytes exist to hash -- registered as referenced_unresolved (no hash claimed).",
          "name": "fig3_wittrick_williams.png",
          "caption_source": "record.figures[2].caption",
          "figures_endpoint_probe": {
            "/tensor/reports/9777/figures": {
              "http_status": 404,
              "bytes": 22
            },
            "/tensor/reports/9777/artifacts": {
              "http_status": 404,
              "bytes": 22
            },
            "/tensor/reports/9777/attachments": {
              "http_status": 404,
              "bytes": 22
            }
          }
        },
        {
          "asset_id": "A05",
          "asset_class": "figure_reference",
          "label": "图4 (fig4_m6117_attribution.png)",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 3025,
            "end_char": 3036,
            "start_line": 46,
            "end_line": 46,
            "quote": "图4 m6117 归因",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "(1) record figure name verbatim in markdown? (2) record caption verbatim in markdown? (3) figure bytes servable at /tensor/reports/9777/{figures,artifacts,attachments}?",
            "result": "unresolved"
          },
          "note": "Declared in the platform record metadata as name+caption and referenced in body prose by the label 图4. name_in_markdown=False, caption_in_markdown=False; the three candidate byte endpoints all return 404, so no figure bytes exist to hash -- registered as referenced_unresolved (no hash claimed).",
          "name": "fig4_m6117_attribution.png",
          "caption_source": "record.figures[3].caption",
          "figures_endpoint_probe": {
            "/tensor/reports/9777/figures": {
              "http_status": 404,
              "bytes": 22
            },
            "/tensor/reports/9777/artifacts": {
              "http_status": 404,
              "bytes": 22
            },
            "/tensor/reports/9777/attachments": {
              "http_status": 404,
              "bytes": 22
            }
          }
        },
        {
          "asset_id": "A06",
          "asset_class": "figure_reference",
          "label": "图5 (fig5_random_sweep.png)",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 3037,
            "end_char": 3052,
            "start_line": 46,
            "end_line": 46,
            "quote": "图5 100 组随机样本鲁棒性",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "(1) record figure name verbatim in markdown? (2) record caption verbatim in markdown? (3) figure bytes servable at /tensor/reports/9777/{figures,artifacts,attachments}?",
            "result": "unresolved"
          },
          "note": "Declared in the platform record metadata as name+caption and referenced in body prose by the label 图5. name_in_markdown=False, caption_in_markdown=False; the three candidate byte endpoints all return 404, so no figure bytes exist to hash -- registered as referenced_unresolved (no hash claimed).",
          "name": "fig5_random_sweep.png",
          "caption_source": "record.figures[4].caption",
          "figures_endpoint_probe": {
            "/tensor/reports/9777/figures": {
              "http_status": 404,
              "bytes": 22
            },
            "/tensor/reports/9777/artifacts": {
              "http_status": 404,
              "bytes": 22
            },
            "/tensor/reports/9777/attachments": {
              "http_status": 404,
              "bytes": 22
            }
          }
        },
        {
          "asset_id": "A07",
          "asset_class": "source_code_reference",
          "label": "dsbeam.py",
          "in_report_section": "② 怎么做的 / ③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 847,
            "end_char": 872,
            "start_line": 19,
            "end_line": 19,
            "quote": "- **本单在 dsbeam.py 修三处缺陷**",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path exists in the TensorKnowledge delivery worktree at 'dsbeam.py'?",
            "result": "unresolved"
          },
          "note": "Declared by the report as the artefact behind its numbers; the path belongs to the upstream TensorFEM/audit worktree and does not exist in this delivery checkout (exists_here=False). Registered as a declared reference, never as a broken upstream artefact.",
          "name": "dsbeam.py",
          "exists_in_delivery_worktree": false
        },
        {
          "asset_id": "A08",
          "asset_class": "source_code_reference",
          "label": "artifacts/m8404_dsm/audit_acceptance.py",
          "in_report_section": "② 怎么做的 / ③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 1121,
            "end_char": 1162,
            "start_line": 20,
            "end_line": 20,
            "quote": "`artifacts/m8404_dsm/audit_acceptance.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path exists in the TensorKnowledge delivery worktree at 'artifacts/m8404_dsm/audit_acceptance.py'?",
            "result": "unresolved"
          },
          "note": "Declared by the report as the artefact behind its numbers; the path belongs to the upstream TensorFEM/audit worktree and does not exist in this delivery checkout (exists_here=False). Registered as a declared reference, never as a broken upstream artefact.",
          "name": "artifacts/m8404_dsm/audit_acceptance.py",
          "exists_in_delivery_worktree": false
        },
        {
          "asset_id": "A09",
          "asset_class": "data_artifact_reference",
          "label": "results.json",
          "in_report_section": "② 怎么做的 / ③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 1220,
            "end_char": 1237,
            "start_line": 22,
            "end_line": 22,
            "quote": "全部来自 results.json",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path exists in the TensorKnowledge delivery worktree at 'results.json'?",
            "result": "unresolved"
          },
          "note": "Declared by the report as the artefact behind its numbers; the path belongs to the upstream TensorFEM/audit worktree and does not exist in this delivery checkout (exists_here=False). Registered as a declared reference, never as a broken upstream artefact.",
          "name": "results.json",
          "exists_in_delivery_worktree": false
        }
      ],
      "symbol_references": [
        {
          "symbol": "mode_shape_full",
          "kind": "function",
          "locator": {
            "source_field": "markdown",
            "line": 19
          },
          "quote": "`mode_shape_full`",
          "quote_sha256": "sha256:1015e5ecc1d92725ef09c6d4a3777ff74de43cbb3897a992cb20569b4ae976a0",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "anchor_occurrences_in_source": 1
        },
        {
          "symbol": "scipy.optimize.brentq",
          "kind": "third_party_call",
          "locator": {
            "source_field": "markdown",
            "line": 19
          },
          "quote": "`scipy.optimize.brentq`",
          "quote_sha256": "sha256:c7aa1b817d46814ddb2602c8889929ecada2ab423495ab9387d3f4d300ae8966",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "anchor_occurrences_in_source": 1
        },
        {
          "symbol": "eigvalsh",
          "kind": "third_party_call",
          "locator": {
            "source_field": "markdown",
            "line": 19
          },
          "quote": "惯性容差由 1e-12‖K‖ 改为 eigvalsh 向后误差界 + J≥0 钳位",
          "quote_sha256": "sha256:b519e8b42b1660e71618a9de21cdd1dd3e33cad330f1ea3ff4e630652d20aed1",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "anchor_occurrences_in_source": 2
        },
        {
          "symbol": "K(ω)=H⁻ᵀQH⁻¹",
          "kind": "formula",
          "locator": {
            "source_field": "markdown",
            "line": 16
          },
          "quote": "`K(ω)=H⁻ᵀQH⁻¹`",
          "quote_sha256": "sha256:e053e28dfd295e187be0d64b18083385c802542c5c7fe952cb2a1d52216da8df",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "anchor_occurrences_in_source": 1
        },
        {
          "symbol": "J(ω)=n·J₀+s{K}−刚体数−谱阈值伪零",
          "kind": "formula",
          "locator": {
            "source_field": "markdown",
            "line": 17
          },
          "quote": "`J(ω)=n·J₀+s{K}−刚体数−谱阈值伪零`",
          "quote_sha256": "sha256:c562f215521e73da7153cabef676523c4361362e091993372398e3cd0b09c136",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "anchor_occurrences_in_source": 1
        }
      ],
      "locators": [
        {
          "asset_id": "A01",
          "locator": {
            "source_field": "markdown",
            "line": 1
          },
          "quote": "# 自由-自由 Timoshenko 梁精确 DSM 验收审计（节点 p423w2-n09）",
          "quote_sha256": "sha256:35a3f1a0f3edd8fa260ea9c81f2fd9da7fc7cba3e223379fc5798c2b78fc0031",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "unique": true,
          "resolved": true
        },
        {
          "asset_id": "A02",
          "locator": {
            "source_field": "markdown",
            "line": 46
          },
          "quote": "图1 两个极限下的精确 DSM 频谱",
          "quote_sha256": "sha256:84e7e2f901849ca71d868c0007165582a7c8d7fbb64caa28f45513df2d6c8e61",
          "quote_in_source": true,
          "quote_on_declared_line": false,
          "occurrences_in_source": 1,
          "unique": true,
          "resolved": true
        },
        {
          "asset_id": "A03",
          "locator": {
            "source_field": "markdown",
            "line": 46
          },
          "quote": "图2 自由-自由 1–3 阶两场精确振型（w/ψ/曲率）",
          "quote_sha256": "sha256:13269d1dfae553de11b3208321af01767d0ae62ec330434d36719a1b8360bf41",
          "quote_in_source": true,
          "quote_on_declared_line": false,
          "occurrences_in_source": 1,
          "unique": true,
          "resolved": true
        },
        {
          "asset_id": "A04",
          "locator": {
            "source_field": "markdown",
            "line": 46
          },
          "quote": "图3 J(ω) 阶梯 vs 独立根普查（极点处阶梯不跳）",
          "quote_sha256": "sha256:4426b62e20bba4cd7d9abfa1bd347efdf821442cec21388740d8c799e19c5be7",
          "quote_in_source": true,
          "quote_on_declared_line": false,
          "occurrences_in_source": 1,
          "unique": true,
          "resolved": true
        },
        {
          "asset_id": "A05",
          "locator": {
            "source_field": "markdown",
            "line": 46
          },
          "quote": "图4 m6117 归因",
          "quote_sha256": "sha256:f97f9d61312560b81407b05a1cb067412d00cdbbb692c5c18516ea1ddca11a15",
          "quote_in_source": true,
          "quote_on_declared_line": false,
          "occurrences_in_source": 1,
          "unique": true,
          "resolved": true
        },
        {
          "asset_id": "A06",
          "locator": {
            "source_field": "markdown",
            "line": 46
          },
          "quote": "图5 100 组随机样本鲁棒性",
          "quote_sha256": "sha256:50cadbd4822d7943989322f6c792790e02f295fc5924b9ed0a5123dc5cc29b79",
          "quote_in_source": true,
          "quote_on_declared_line": false,
          "occurrences_in_source": 1,
          "unique": true,
          "resolved": true
        },
        {
          "asset_id": "A07",
          "locator": {
            "source_field": "markdown",
            "line": 19
          },
          "quote": "- **本单在 dsbeam.py 修三处缺陷**",
          "quote_sha256": "sha256:04a0388deba446ef23323646ee5e3bc451b99b934865fb96f05e0317d3062f41",
          "quote_in_source": true,
          "quote_on_declared_line": false,
          "occurrences_in_source": 1,
          "unique": true,
          "resolved": true
        },
        {
          "asset_id": "A08",
          "locator": {
            "source_field": "markdown",
            "line": 20
          },
          "quote": "`artifacts/m8404_dsm/audit_acceptance.py`",
          "quote_sha256": "sha256:dffee517b6da5e89ecee035091d323fe594cc45d950cbc3c29fc5bfaef8dc479",
          "quote_in_source": true,
          "quote_on_declared_line": false,
          "occurrences_in_source": 1,
          "unique": true,
          "resolved": true
        },
        {
          "asset_id": "A09",
          "locator": {
            "source_field": "markdown",
            "line": 22
          },
          "quote": "全部来自 results.json",
          "quote_sha256": "sha256:43ace7db9479eb147fb8d1f328444cc8f8c7f0f656b393d810d527eb10bd21de",
          "quote_in_source": true,
          "quote_on_declared_line": false,
          "occurrences_in_source": 1,
          "unique": true,
          "resolved": true
        }
      ],
      "identity_facts": [
        {
          "fact_id": "h1-title-line",
          "locator": {
            "source_field": "markdown",
            "line": 1
          },
          "quote": "# 自由-自由 Timoshenko 梁精确 DSM 验收审计（节点 p423w2-n09）",
          "quote_sha256": "sha256:35a3f1a0f3edd8fa260ea9c81f2fd9da7fc7cba3e223379fc5798c2b78fc0031",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1
        },
        {
          "fact_id": "sec1-header",
          "locator": {
            "source_field": "markdown",
            "line": 3
          },
          "quote": "## ① 案例介绍",
          "quote_sha256": "sha256:7ddf89857913efd224be5a41d7506c1c08107704d42df47f1f87b8bcc6872f42",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1
        },
        {
          "fact_id": "sec2-header",
          "locator": {
            "source_field": "markdown",
            "line": 14
          },
          "quote": "## ② 怎么做的",
          "quote_sha256": "sha256:d96e990d7dece6286c641545798575f31ab24a71d4c7eebdfaf3187fb28c82c1",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1
        },
        {
          "fact_id": "sec3-header",
          "locator": {
            "source_field": "markdown",
            "line": 22
          },
          "quote": "## ③ 计算结果（全部来自 results.json）",
          "quote_sha256": "sha256:e3300ceec1f338b3bb93a08bdb7afb47ea8d6769ca936d3f2a3a6e16df8a809d",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1
        },
        {
          "fact_id": "sec4-header",
          "locator": {
            "source_field": "markdown",
            "line": 44
          },
          "quote": "## ④ 结果图",
          "quote_sha256": "sha256:f96f5db082d6af7df301ed61dff480e611035eab736db49814b2ba4ba6067766",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1
        },
        {
          "fact_id": "sec5-header",
          "locator": {
            "source_field": "markdown",
            "line": 48
          },
          "quote": "## ⑤ 注意点",
          "quote_sha256": "sha256:fbb3949cac3b38cde89d385845282fc7fed0e116e6fbcc9f09d8fd55a7f4bd0d",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1
        },
        {
          "fact_id": "sec6-header",
          "locator": {
            "source_field": "markdown",
            "line": 57
          },
          "quote": "## ⑥ 误差判定（是否 <3%）",
          "quote_sha256": "sha256:042c5af5c3ef53c29f2e47abf95ec10fd6b4d4773bc17c73977206b343040856",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1
        },
        {
          "fact_id": "last-line",
          "locator": {
            "source_field": "markdown",
            "line": 70
          },
          "quote": "结论：DSM 自身对三个独立基准的误差 1e-13…1e-5 量级，全部 ≪3 %；m6117 的闭式锚点偏低 5.5–5.9 %，超过 3 %，且 6.28 % 恰为“FEM(+0.03 %) − 锚点(−5.89 %)”之差——债务归属明确落在闭式近似，而非有限元或网格。",
          "quote_sha256": "sha256:7cbeedd6f07d21501a9148d99177631c3ec60681058257725d39a1eaed21d265",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1
        }
      ],
      "claims": [],
      "claims_empty_reason": "Contract objective is register_assets=true / classify_report_type=false; notes say 'claims 允许为空数组' and constraints include no_forced_claim_generation=true, do_not_mark_claims_as_verified=true. This工序 registers asset identity only (report_id, markdown byte hash, declared attachments/artifacts); extraction is a downstream工序, so an empty claims array is the complete result, not an omission.",
      "counts": {
        "assets": 9,
        "by_class": {
          "data_artifact_reference": 1,
          "figure_reference": 5,
          "source_code_reference": 2,
          "source_document": 1
        },
        "by_resolution": {
          "referenced_unresolved": 8,
          "resolved_in_source": 1
        },
        "resolved_in_source": 1,
        "referenced_unresolved": 8,
        "declared_absent": 0,
        "body_references": 3,
        "figures_declared_in_record": 5,
        "figures_with_bytes": 0,
        "locators": 9,
        "locators_resolved": 9,
        "symbol_references": 5,
        "claims": 0
      },
      "id_integrity": {
        "ids_checked": 9,
        "duplicates": [],
        "unique": true
      },
      "integrity": {
        "quote_uniqueness": {
          "checked": 9,
          "all_unique": true
        },
        "hash_recomputed_locally": true,
        "hash_matches_contract": true
      },
      "unresolved": [
        {
          "asset_id": "A02",
          "name": "fig1_spectrum.png",
          "reason": "(1) record figure name verbatim in markdown? (2) record caption verbatim in markdown? (3) figure bytes servable at /tensor/reports/9777/{figures,artifacts,attachments}?"
        },
        {
          "asset_id": "A03",
          "name": "fig2_mode_shapes.png",
          "reason": "(1) record figure name verbatim in markdown? (2) record caption verbatim in markdown? (3) figure bytes servable at /tensor/reports/9777/{figures,artifacts,attachments}?"
        },
        {
          "asset_id": "A04",
          "name": "fig3_wittrick_williams.png",
          "reason": "(1) record figure name verbatim in markdown? (2) record caption verbatim in markdown? (3) figure bytes servable at /tensor/reports/9777/{figures,artifacts,attachments}?"
        },
        {
          "asset_id": "A05",
          "name": "fig4_m6117_attribution.png",
          "reason": "(1) record figure name verbatim in markdown? (2) record caption verbatim in markdown? (3) figure bytes servable at /tensor/reports/9777/{figures,artifacts,attachments}?"
        },
        {
          "asset_id": "A06",
          "name": "fig5_random_sweep.png",
          "reason": "(1) record figure name verbatim in markdown? (2) record caption verbatim in markdown? (3) figure bytes servable at /tensor/reports/9777/{figures,artifacts,attachments}?"
        },
        {
          "asset_id": "A07",
          "name": "dsbeam.py",
          "reason": "path exists in the TensorKnowledge delivery worktree at 'dsbeam.py'?"
        },
        {
          "asset_id": "A08",
          "name": "artifacts/m8404_dsm/audit_acceptance.py",
          "reason": "path exists in the TensorKnowledge delivery worktree at 'artifacts/m8404_dsm/audit_acceptance.py'?"
        },
        {
          "asset_id": "A09",
          "name": "results.json",
          "reason": "path exists in the TensorKnowledge delivery worktree at 'results.json'?"
        }
      ],
      "observations": [
        "Markdown is complete and self-consistent: H1 title, sections ①-⑥ all present, 70 lines, no CRLF, trailing newline.",
        "Contract identity triple matches: sha256 sha256:d5742ce0c54743d542de8bb36d79891a0cfe8997a1b6032827fa97df251dcbe7, chars 4341, scenario_key structural-dynamics/dsm-beam-modal.",
        "Record title and the markdown H1 title are DIFFERENT strings (record='精确 DSM Timoshenko 梁模态验收审计：7/7 判据 PASS、dsbeam 三处缺陷修复、m6117 6.28% 归因闭环', H1='# 自由-自由 Timoshenko 梁精确 DSM 验收审计（节点 p423w2-n09）'): the record carries the long campaign title, the body carries the node-scoped title. Both are registered verbatim; neither is rewritten.",
        "All 5 figures exist only as record metadata (name+caption); the body ④ section paraphrases them by label 图1..图5, so body clause != metadata caption. Figure identity is therefore name-based, and no figure bytes are servable (3/3 endpoints 404).",
        "The 3 body path references point into the upstream TensorFEM/audit worktree (artifacts/m8404_dsm/, dsbeam.py, results.json); none exists in this TensorKnowledge delivery checkout, so they stay referenced_unresolved -- reported as scope of this checkout, not as a defect upstream.",
        "source_hash scope = UTF-8 bytes of the markdown string returned by the platform API; any change to the stored markdown (even whitespace) invalidates it.",
        "Direct psql read of tensor_reports was denied (permission denied for table tensor_reports), so the API is the only source channel used."
      ]
    }
  },
  "claims": []
}
```
