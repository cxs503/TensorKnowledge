**KF-RESULT wp-14351-01** · task_type=`01-asset-registration` · report_id=`14351` · lane=B
（工序输出信道：本页正文唯一一个 json 代码块即最终结果信封；正文其余部分为工序记录。）

## ① 本工序做了什么

只做一件事：为 report_id=**14351**（《GAP-FEM-3D-COHESIVE 返修轮：DCB 位移控制双缺陷修复 + 试件级 honest 部分验收》，scenario_key=`TensorFEM`，mission=15256）做**资产登记**。

- 取回该报告 markdown（`tensor://reports/14351`，字段 `markdown`），独立重算 UTF-8 字节 sha256 = `sha256:8c696991f8bef0c1f0903d2104e88a437897875c759af309c0c7710ce1260558`，与包契约声明 `sha256:8c696991f8bef0c1f0903d2104e88a437897875c759af309c0c7710ce1260558` **逐字相同**；字符数 4190 = 契约 4190。
- 登记 **22 条资产**：`resolved_in_source` 14 条（正文/表格/命令块/文档本体）、`referenced_unresolved` 8 条（外部仓库文件、图件、集群作业）、`declared_absent` 0 条。
- **不做**：报告类型分类（objective.classify_report_type=false）、知识抽取（objective 未要求；契约 notes 明示"不做抽取"）、数字复核、任何 verified 标注。
- `claims` 为**空数组**——这是契约允许的完整结果，不是缺项（见 ⑤）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取回与哈希**：`GET /api/v1/tensor/reports/14351` → `markdown` 字段，`runs/wp-14351-01/fetch_report.py` 落盘并记录 chars/bytes/sha256/figures 元数据。psql 直读被权限拒绝（`permission denied for table tensor_reports`），改用 API 是唯一可用且可复现的取数路径。
2. **标题索引**：按行扫描 ATX 标题，**跳过代码围栏内**的 `#` 行（初版误把 repro 块里 `# 单元级：all_passed True` 当标题，已修），得 8 个真实标题块。
3. **locator 生成（零手抄的关键）**：每条资产只给一个**锚串 + 相对行跨度**；脚本在原文里定位唯一命中行，然后 `quote = md[start:end]`——引文是**从原文切片**得到，而非人工重述；随后断言 `md.count(quote)==1` 且 `md[start:end]==quote`。任一断言失败脚本即中止（本包 22/22 通过）。
4. **分辨率机器检查**（不是文字声明）：
   - 外部文件类：`worktree_path_exists` → 逐路径 `Path.exists()`（本工作树=TensorKnowledge，TensorFEM 的 `src/`、`benchmarks/`、`tests/` 全不在，故 8 条标 `referenced_unresolved`）；
   - 图件类：`record_figures_and_path_check` → 比对 `figures[]` 的 name 集合（只有 `load_opening.png`、`damage_field.png`，缺 `rcurve.png`；且 figures 只有 name/caption，**无 png_base64 载荷**）；
   - 集群作业类：`cluster_artifact_lookup` → 显式判 `unresolved`（不查历史队列，避免把当前快照当历史事实）。
5. **结构校验**：manifest 对 `docs/kf/wp-14351-01/asset_manifest.schema.json`（由仓库 `schemas/asset_manifest.v1.schema.json` 换本包常量派生并钉住）过 jsonschema draft-07；结果信封对仓库原生 `schemas/kf_result.v1.schema.json` 校验。
6. **自检与出图**：`verification.json` 记 9 项 acceptance 机器判定；`asset_map.png` 的每根条 = manifest 里某条资产的 char span，颜色 = 分辨率，故图与数据不可能不同步。

## ③ 产出物清单

| 文件 | 大小 | 要点 |
|---|---|---|
| `asset_manifest.json` | 40689 B | 22 条资产的 locator/分辨率/机器检查（本工序主产物） |
| `kf_result.json` | 42976 B | 结果信封（package_id/task_type/report_id/provenance/outputs/claims=[]） |
| `verification.json` | 2519 B | 9 项 acceptance 机器自检（9 PASS / 0 FAIL） |
| `asset_manifest.schema.json` | 7966 B | 本包契约定点的 manifest schema（schema_pass 的可复现依据） |
| `asset_map.png` | 170854 B | 资产 locator 覆盖图（数据驱动，来自 manifest 本身） |
| `report.md` | 62159 B | 本报告正文（含唯一 json 结果块） |

- 附**图 1**（`asset_map.png`）：横轴=报告 markdown 字符偏移（全 4190 字符），每根条=该资产的 locator span，绿色=正文可解析、橙色=引用未解析；右侧为分辨率计数（14/8/0）。**本工序是登记类工序、无物理场量**，这张"定位覆盖图"就是本工序唯一有信息量的图；未伪造场云图。
- 结果信封（唯一 json 块）字段：`package_id`/`task_type`=`01-asset-registration`/`report_id`=`14351`/`provenance.source_hash`=`sha256:8c696991f8bef0c1f…`/`outputs["asset_manifest.json"]`（全量 manifest）/`claims`=`[]`。

## ④ 证据定位表（claim/字段 → 原文引文片段）

> 下表"引文片段"= JSON 块内该资产 `locator.quote` 的**首行摘录**（截断以 `…` 标注），完整引文与精确 char span 见 JSON；逐字校验由脚本对原文切片完成，本表不参与"是否逐字"判定。

| 资产 | 类别/标签 | 引文片段（首行摘录） |
|---|---|---|
| A01 | 报告正文（markdown 全文，本工序的哈希基准对象） | # GAP-FEM-3D-COHESIVE · 返修轮：位移控制求解器缺陷修复 + honest 部分验收（m15256） 本页是 feature-ledg… |
| A02 | DCB 算例定义（ASTM D5528 Mode I 层间断裂） | DCB（ASTM D5528 双悬臂梁，Mode I 层间断裂）用于检验 3D 内聚单元在真实三维应力状态下 能否给出可信的载荷-张开响应。几何：L=60 … |
| A03 | 几何 + 离散化 + 材料/内聚参数（L/b/h/a0、E/ν、k_n/k_s/t_n0/t_s0/G_Ic/G_IIc… | 结构化 HEX8 adherends + 零厚度 COH3D8 韧带。材料/内聚参数：E=70 GPa，ν=0.30， k_n=1e12 Pa/m，k_s=… |
| A04 | 解析基准（Williams 根部转角修正梁柔性 C + LEFM 峰值载荷闭式） | 解析基准（独立闭式）：`C = 4a³/(Ebh³) + a/(5/6·G·bh)`，含 Williams(1989) 根部转角修正 Δ； LEFM 峰值 … |
| A05 | 缺陷 A（物理错误）：加载 dof 未进 fixed_dofs → 反力恒 0 | - **缺陷 A（物理错误）**：位移控制面上被加载的 dof（x=L, z）没有进 `fixed_dofs`，落进自由集。 Newton 于是把这些 do… |
| A06 | 缺陷 B（不终止）：终步零长度步无限循环 | - **缺陷 B（不终止）**：`while delta < delta_max*(1+1e-12)` 在 `delta == delta_max` 后恒真… |
| A07 | 回归测试钉住：tests/test_cohesive3d_dcb_solver_guards.py（3 新测试）+ 修正… | 行为由 `tests/test_cohesive3d_dcb_solver_guards.py`（3 个新测试）钉住，并修正 `tests/test_coh… |
| A08 | 修复实现文件 src/tensorfem/cohesive3d_dcb.py | 复现后定位到两个**求解器缺陷**（均已在 `src/tensorfem/cohesive3d_dcb.py` 修复）： |
| A09 | 前轮基准脚本 benchmarks/cohesive3d_dcb_3d.py（及历史轮 m14987/m15001） | 1. **前轮死法定位**：m14987/m15001 的 `benchmarks/cohesive3d_dcb_3d.py` 从未产出运行工件。 |
| A10 | 单元级验证真跑：benchmarks/cohesive3d_verification.py → benchmarks/c… | 2. **单元级验证（真跑）**：`python benchmarks/cohesive3d_verification.py` → all_passed T… |
| A11 | 试件级探测真跑：benchmarks/cohesive3d_dcb_displacement_control_probe… | 3. **试件级探测（真跑）**：新增 `benchmarks/cohesive3d_dcb_displacement_control_probe.py` … |
| A12 | 全量内聚 pytest 结果：61 passed, 2 xfailed（strict=True） | 4. 全量内聚 pytest：`61 passed, 2 xfailed`（2 个 xfail 即下述开放缺陷，strict=True 不掩盖）。 |
| A13 | 试件级结果表（5 行：柔性 C×2 / 峰值非零 / 终止 / 收敛） | 试件级（`benchmarks/cohesive3d_dcb_displacement_control_probe.json`）： \| 量 \| 基准(r… |
| A14 | 单元级六项 all_passed=True 的概述陈述（数字以工件为准） | 单元级（`benchmarks/cohesive3d_verification.json`）：objectivity / patch / mode-I / … |
| A15 | 宽度分辨基准 benchmarks/cohesive3d_dcb_3d.json（quick，135.7 s，all_p… | 宽度分辨基准（`benchmarks/cohesive3d_dcb_3d.json`，quick 模式，runtime 135.7 s）： `all_pas… |
| A16 | 图件声明：docs/assets/cohesive3d-dcb-3d/{load_opening,damage_fiel… | `docs/assets/cohesive3d-dcb-3d/load_opening.png`（载荷-张开曲线）、`damage_field.png`（损… |
| A17 | 开放缺陷：试件柔性为梁理论 5.6–6.9 倍（疑似有效自由跨度 2a） | - **开放缺陷（未解决）**：修正位移控制后正常加载，FE 试件柔性是梁理论的 ~5.6–6.9 倍 （nx=24 时 5.61×；nx=50 时约 11… |
| A18 | 锚点未闭合声明（试件级 DCB 不能作验收算例；仅单元级能力可用） | - 该缺陷使**试件级** DCB 不能作为验收算例；因此 `GAP-FEM-3D-COHESIVE` **未闭合**， 仅单元级能力可用（BK 律 + C… |
| A19 | 既有适用限制：小应变运动学、无摩擦/接触/循环退化 | - 小应变运动学、无摩擦/接触/循环退化（既有限制，未变）。 |
| A20 | 集群作业 cj1024（全量 DCB，队列深度 238，未取回） | - 集群 cj1024（全量 DCB）因队列深度 238 未取回，本轮结论一律基于控制节点真跑工件。 |
| A21 | 误差判定表（4 行，逐项回答是否 <3%） | \| 关键量 \| 基准 \| 误差 \| <3%? \| \|---\|---\|---\|---\| \| 单元级 objectivity/patch/… |
| A22 | repro_cmd（4 条命令块：单元级 / 探针 / pytest） | python benchmarks/cohesive3d_verification.py # 单元级：all_passed True python benc… |

定位字段自证：`integrity.all_locators_resolvable=true`、`quote_uniqueness=true`、`no_duplicate_ids=true`，`source_hash_matches=true`。

## ⑤ 注意点与局限

1. **claims=[] 是设计而非缺项**：契约 `objective.classify_report_type=false` + notes"不做抽取" + `no_forced_claim_generation`/`do_not_mark_claims_as_verified` 共同要求不得为凑指标造 claim。报告里 3 项 honest 未达标（+460.7% / -99.8% / 0.936）保持**原文状态**，既没升格为 claim，也没标 verified——verification 由平台门计算。
2. **8 条资产是"引用未解析"**：A07, A08, A09, A10, A11, A15, A16, A20 指向外部仓库 TensorFEM 的代码/工件/图件/集群作业。本工作树只有 TensorKnowledge，按边界不复制、不臆造内容，因此这些资产**只登记"报告在哪儿引用了它"**，不登记其内容。
3. **图件载荷缺失**：平台 `figures[]` 仅返回 name/caption（无 png_base64），且 3 个声明 PNG 只匹配到 2 个（`rcurve.png` 不在 figures[]）。图件二进制不可校验——这是上游/平台侧的记录缺口，已如实登记，未补猜。
4. **不复核任何上游数字**：本工序的输出**没有**、也不该有对 +460.7%、-99.8%、0.936、61 passed/2 xfailed 等数字的独立验证；manifest 中相关字段均为 `resolved_in_source`（=能定位到原文），注意其语义是"可定位"而非"为真"。
5. **单报告边界**：全程只读写 report 14351；未接触其它 report_id（自检 `single_report_scope` PASS）。
6. **schema 是本地钉住的**：`schemas/asset_manifest.v1.schema.json` 是 wp-448-01 的专用实例（常量写死），故本包派生一份本包 schema。若平台侧存在权威 schema，以平台门为准，本包产物需按其修订。

## ⑥ 自检：逐条对照 acceptance（honest，不粉饰）

| acceptance 项 | 判定 | 依据 |
|---|---|---|
| valid_json | ✅ | json.loads(docs/kf/wp-14351-01/asset_manifest.json) 成功 |
| schema_pass | ✅ | jsonschema(draft-07) 对 docs/kf/wp-14351-01/asset_manifest.schema.json 通过；kf_result 信封对 schemas/kf_result.v1.schema.json … |
| source_locator_resolvable | ✅ | 22/22 条 locator 的 quote 与其 char span 一致（且全部 quote_unique=True） |
| source_hash_matches | ✅ | 重算 8c696991f8bef0c1f0903d2104e88a437897875c759af309c0c7710ce1260558 == 契约 sha256:8c696991f8bef0c1f0903d2104e88a437897875… |
| no_duplicate_ids | ✅ | asset_id 唯一数=22 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=[]（契约允许；不做抽取），无缺证据 claim 条目 → 条件空真；每条资产另带 resolution 或 unresolved 说明 |
| contract_chars_match | ✅ | chars 4190 == 契约 4190 |
| single_report_scope | ✅ | 仅取回/登记 report 14351；未读写任何其它 report_id |
| do_not_mark_claims_as_verified | ✅ | 结构化扫描：无任何 verified 标记对象/值；integrity.claims_marked_verified=0（claim_policy 为说明性文字，已从扫描中排除） |

**误差判定（逐项显式回答"是否 <3%"）**——本工序无物理量/实验基准，基准=包契约的哈希/字符数/结构与 schema：

| 量 | 基准 | 本工序 | 偏差 | <3%? |
|---|---|---|---|---|
| source markdown sha256 | 契约 sha256:8c696991f8bef0c1f09… | 重算 sha256:8c696991f8bef0c1f09… | 0 bit 偏差 | **是（0%）** |
| markdown 字符数 | 契约 4190 | 实测 4190 | 0 | **是（0%）** |
| locator 可解析率 | 22/22 | 22/22（quote==md[start:end] 且全文唯一） | 0 | **是（0%）** |
| schema 校验 | 0 violation | 9 PASS / 0 FAIL 自检 | 0 | **是** |

**结论**：登记正确性面上全部 0 偏差（是）；**上游报告的精度结论本工序一律未复核**（不适用 >15%/3% 判据，因为本工序不做数值计算）——若把上游自述的 +460.7% 当作待验量，则它**远未达标且本工序未给出任何反驳证据**，保持 honest-FAIL 原样。

**repro_cmd（一键复跑，工作树根=仓库检出）**

```bash
python runs/wp-14351-01/fetch_report.py          # 取回 report 14351 + 记录 sha256/chars/figures
python scripts/kf/register_14351_assets.py       # 生成 asset_manifest.json / kf_result.json / verification.json
python scripts/kf/publish_14351_report.py        # 生成 asset_map.png + report.md 并投递 KF-RESULT 报告
```

结果信封（本页唯一 json 块；串内反引号以 `\u0060` 转义，避免打断宿主代码围栏，解码后与原文逐字一致）：

```json
{
  "package_id": "wp-14351-01",
  "task_type": "01-asset-registration",
  "report_id": "14351",
  "provenance": {
    "source_hash": "sha256:8c696991f8bef0c1f0903d2104e88a437897875c759af309c0c7710ce1260558",
    "source_field": "markdown",
    "source_uri": "tensor://reports/14351",
    "producer": "scripts/kf/register_14351_assets.py",
    "emitted_at": "2026-11-12T03:05:00Z",
    "notes": "source_hash=对 markdown UTF-8 字节独立重算的 sha256（本脚本），与契约声明一致；source_field=markdown；未改动上游报告，未标注任何 verified。"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-14351-01",
      "task_type": "01-asset-registration",
      "report_id": "14351",
      "lane": "B",
      "objective": {
        "register_assets": true,
        "classify_report_type": false,
        "extraction_performed": false
      },
      "generated_at": "2026-11-12T03:05:00Z",
      "generator": "scripts/kf/register_14351_assets.py",
      "generator_inputs": {
        "report_id": "14351",
        "source_uri": "tensor://reports/14351",
        "source_field": "markdown",
        "contract_expected_sha256": "sha256:8c696991f8bef0c1f0903d2104e88a437897875c759af309c0c7710ce1260558",
        "contract_expected_chars": 4190,
        "retrieval_endpoint": "GET /api/v1/tensor/reports/14351"
      },
      "source": {
        "report_id": "14351",
        "source_uri": "tensor://reports/14351",
        "source_field": "markdown",
        "sha256": "sha256:8c696991f8bef0c1f0903d2104e88a437897875c759af309c0c7710ce1260558",
        "contract_declared_sha256": "sha256:8c696991f8bef0c1f0903d2104e88a437897875c759af309c0c7710ce1260558",
        "source_hash_matches": true,
        "chars": 4190,
        "bytes_utf8": 6370,
        "lines": 91,
        "contract_declared_chars": 4190,
        "chars_match": true,
        "hash_scope": "UTF-8 bytes of tensor_reports.markdown (report 14351)",
        "record": {
          "id": 14351,
          "title": "GAP-FEM-3D-COHESIVE 返修轮：DCB 位移控制双缺陷修复 + 试件级 honest 部分验收",
          "scenario_key": "TensorFEM",
          "mission_id": 15256,
          "status": "published",
          "created_at": "2026-11-11T21:19:49.754132+00:00",
          "tags": [
            "GAP-FEM-3D-COHESIVE",
            "cohesive",
            "DCB",
            "displacement-control",
            "honest-FAIL",
            "TensorFEM"
          ],
          "summary_sha256": "sha256:efb1846110993c9816c9396ba4a537bdcf6641e133122c7cd04822ccda61d710",
          "summary_chars": 147
        },
        "sections": [
          {
            "level": 1,
            "heading": "GAP-FEM-3D-COHESIVE · 返修轮：位移控制求解器缺陷修复 + honest 部分验收（m15256）",
            "start_line": 0,
            "heading_span": [
              0,
              61
            ],
            "char_span": [
              0,
              244
            ],
            "heading_sha256": "sha256:fe9e6261ddf263070470e271ddb295f4a81ca532709fa993064f6bac29691604"
          },
          {
            "level": 2,
            "heading": "1. 案例介绍（物理背景 / 几何 / 参数）",
            "start_line": 6,
            "heading_span": [
              244,
              270
            ],
            "char_span": [
              244,
              683
            ],
            "heading_sha256": "sha256:6ffb43d959d567f901e0ad2be6e031045ec40a34ac8df8477cc394a7586549dc"
          },
          {
            "level": 2,
            "heading": "2. 怎么做的（方法 / 流程）",
            "start_line": 15,
            "heading_span": [
              683,
              702
            ],
            "char_span": [
              683,
              1800
            ],
            "heading_sha256": "sha256:13b491e667d5d9d14b8bdbe41bb8b3f44804606f3bdd758a3f583be9b9ed0bff"
          },
          {
            "level": 2,
            "heading": "3. 计算结果（数字表，程序化提取自 JSON 工件）",
            "start_line": 34,
            "heading_span": [
              1800,
              1830
            ],
            "char_span": [
              1800,
              2881
            ],
            "heading_sha256": "sha256:824ae7980ae96173b6936ecf1908f29fbdac79d4c074378ad866a9ce02f2ae66"
          },
          {
            "level": 2,
            "heading": "4. 结果图",
            "start_line": 55,
            "heading_span": [
              2881,
              2890
            ],
            "char_span": [
              2881,
              3079
            ],
            "heading_sha256": "sha256:09f46919df4b16de04ef3b305a53e6efc1a9965fa30b678ab01dc12eedf53ecb"
          },
          {
            "level": 2,
            "heading": "5. 注意点 / 局限",
            "start_line": 61,
            "heading_span": [
              3079,
              3093
            ],
            "char_span": [
              3079,
              3485
            ],
            "heading_sha256": "sha256:1e3753d68e972c315353a714cfe53c3212b2ae5c53dffa3101045e198093220b"
          },
          {
            "level": 2,
            "heading": "6. 误差判定（逐项回答\"是否 <3%\"）",
            "start_line": 72,
            "heading_span": [
              3485,
              3509
            ],
            "char_span": [
              3485,
              3786
            ],
            "heading_sha256": "sha256:e73d61a8354a93ab92f755106727d43ec57bee13f45e106ea9fd9792ada376b1"
          },
          {
            "level": 2,
            "heading": "复现命令（repro_cmd）",
            "start_line": 81,
            "heading_span": [
              3786,
              3804
            ],
            "char_span": [
              3786,
              4190
            ],
            "heading_sha256": "sha256:01ef3f0403135d1428c4483cc7bd49220d18b82e81367933f6743002699f3262"
          }
        ]
      },
      "attachment_scan": {
        "record_figures_len": 2,
        "record_figures_keys": [
          "caption",
          "name"
        ],
        "record_figures_payload_present": false,
        "record_figures_names": [
          "load_opening.png",
          "damage_field.png"
        ],
        "markdown_image_syntax_hits": 0,
        "markdown_code_fence_hits": 2,
        "markdown_url_hits": 0,
        "markdown_path_like_hits": 18,
        "note": "扫描范围=记录 figures[] + markdown 图片语法 + 明文 URL/路径；全量登记，不过滤。"
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "source_document",
          "label": "报告正文（markdown 全文，本工序的哈希基准对象）",
          "in_report_section": "GAP-FEM-3D-COHESIVE · 返修轮：位移控制求解器缺陷修复 + honest 部分验收（m15256）",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 4190,
            "start_line": 0,
            "end_line": 90,
            "quote": "# GAP-FEM-3D-COHESIVE · 返修轮：位移控制求解器缺陷修复 + honest 部分验收（m15256）\n\n本页是 feature-ledger 锚点 \u0060GAP-FEM-3D-COHESIVE\u0060（\"3D cohesive zone 单元 + 验证算例\"）返修轮的\n证据页。**结论先行：单元级（COH3D8 + BK）能力为 REAL 且已用可复现运行工件背书；试件级（DCB\n位移控制 + 梁理论对标）**未达标**，本页如实记录失败量级与开放缺陷，不作粉饰。**\n\n## 1. 案例介绍（物理背景 / 几何 / 参数）\n\nDCB（ASTM D5528 双悬臂梁，Mode I 层间断裂）用于检验 3D 内聚单元在真实三维应力状态下\n能否给出可信的载荷-张开响应。几何：L=60 mm，b=3 mm，每臂厚 h=3 mm，初始裂纹 a0=30 mm，\n结构化 HEX8 adherends + 零厚度 COH3D8 韧带。材料/内聚参数：E=70 GPa，ν=0.30，\nk_n=1e12 Pa/m，k_s=4e11 Pa/m，t_n0=5 MPa，t_s0=3 MPa，G_Ic=300 J/m²，G_IIc=800 J/m²，BK η=2.2。\n解析基准（独立闭式）：\u0060C = 4a³/(Ebh³) + a/(5/6·G·bh)\u0060，含 Williams(1989) 根部转角修正 Δ；\nLEFM 峰值 \u0060P = b h^1.5 sqrt(G_Ic E / 6) / (a+Δ)\u0060（ASTM D5528 / Kanninen 梁理论谱系）。\n\n## 2. 怎么做的（方法 / 流程）\n\n1. **前轮死法定位**：m14987/m15001 的 \u0060benchmarks/cohesive3d_dcb_3d.py\u0060 从未产出运行工件。\n   复现后定位到两个**求解器缺陷**（均已在 \u0060src/tensorfem/cohesive3d_dcb.py\u0060 修复）：\n   - **缺陷 A（物理错误）**：位移控制面上被加载的 dof（x=L, z）没有进 \u0060fixed_dofs\u0060，落进自由集。\n     Newton 于是把这些 dof 的残差也压到 0 → 反力恒为 0 → 试件根本不张开、损伤恒 0、\n     所有峰值判据相对误差退化为 -1。\n   - **缺陷 B（不终止）**：\u0060while delta < delta_max*(1+1e-12)\u0060 在 \u0060delta == delta_max\u0060 后恒真，\n     载荷步走完后以零长度步无限循环（历史上\"DCB 跑不完\"的直接原因，控制节点上残留 24 min 僵尸进程实证）。\n   修复：加载 dof 并入约束集；终止条件改 \u0060delta_max*(1-1e-9)\u0060 + \u0060target<=delta\u0060 断路 + 步数上限。\n   行为由 \u0060tests/test_cohesive3d_dcb_solver_guards.py\u0060（3 个新测试）钉住，并修正\n   \u0060tests/test_cohesive3d_dcb.py\u0060 中记录旧（错误）契约的边界条件断言。\n2. **单元级验证（真跑）**：\u0060python benchmarks/cohesive3d_verification.py\u0060 → all_passed True\n   （element_mesh_objectivity / coupled_block_mode_i / coupled_block_mode_ii / coupled_block_mesh /\n   coupled_block_energy 全 PASS），工件 \u0060benchmarks/cohesive3d_verification.json\u0060。\n3. **试件级探测（真跑）**：新增 \u0060benchmarks/cohesive3d_dcb_displacement_control_probe.py\u0060\n   （nx=24, ny=1, nz=2，机器可判、0.3 s），用**修正后的位移控制**量测柔性并与梁理论对标。\n4. 全量内聚 pytest：\u006061 passed, 2 xfailed\u0060（2 个 xfail 即下述开放缺陷，strict=True 不掩盖）。\n\n## 3. 计算结果（数字表，程序化提取自 JSON 工件）\n\n试件级（\u0060benchmarks/cohesive3d_dcb_displacement_control_probe.json\u0060）：\n\n| 量 | 基准(ref) | 本实现(got) | 相对误差 | 判据 | 判定 |\n|---|---|---|---|---|---|\n| DCB 柔性 C [m/N]（vs Williams 根部转角梁） | 2.35674e-05 | 1.32143e-04 | +460.7% | ≤10% | **FAIL** |\n| DCB 柔性 C [m/N]（vs 无转角修正梁） | 1.91962e-05 | 1.32143e-04 | +588.4% | — | **FAIL** |\n| 峰值反力非零（缺陷 A 回归） | >0 | 0.15135 N | — | >0 | PASS |\n| 终止于 delta_max（缺陷 B 回归） | delta_max | 2.0e-05 (=目标) | 0 | 精确 | PASS |\n| 收敛 | — | converged_all=True, 40 步, 16 Newton 迭代 | — | — | PASS |\n\n单元级（\u0060benchmarks/cohesive3d_verification.json\u0060）：objectivity / patch / mode-I / mode-II /\nmesh-objectivity / energy 六项 all_passed=True（本页不重复其数字，工件为准）。\n\n宽度分辨基准（\u0060benchmarks/cohesive3d_dcb_3d.json\u0060，quick 模式，runtime 135.7 s）：\n\u0060all_passed=False\u0060；其中 \u0060compliance_bracket\u0060 的 \u0060got=0.0\u0060 是该脚本内 \u0060linear_compliance()\u0060\n仍在用\"加载 dof 自由 + 单位力\"的旧写法（修正后 prescribe 面上受力→位移恒 0），属**待迁移的陈旧助手**，\n真实可判数字以 probe 的 +460.7% 为准；\u0060peak_load_vs_lefm\u0060 got=0.0572 N vs ref=28.699 N（-99.8%）、\n\u0060energy_balance_rel\u0060=0.936、\u0060width_objectivity\u0060 got=0.719 vs ref=30.085 —— 均为同一根因（试件过柔）。\n\n## 4. 结果图\n\n\u0060docs/assets/cohesive3d-dcb-3d/load_opening.png\u0060（载荷-张开曲线）、\u0060damage_field.png\u0060（损伤场）、\n\u0060rcurve.png\u0060（R 曲线）：由 \u0060benchmarks/cohesive3d_dcb_3d.py\u0060 真跑生成，图中峰值/损伤的异常形态\n正是上述\"试件过柔\"的直观体现。平台报告内嵌同一 PNG。\n\n## 5. 注意点 / 局限\n\n- **开放缺陷（未解决）**：修正位移控制后正常加载，FE 试件柔性是梁理论的 ~5.6–6.9 倍\n  （nx=24 时 5.61×；nx=50 时约 11×），量级接近 2³，**首要怀疑有效自由跨度为 2a**\n  （韧带/夹持区定位或 adherends 与内聚面带耦合位置待核），已写入 2 个 strict-xfail 测试与\n  \u0060negative\u0060 记录；未在本轮预算内定案。\n- 该缺陷使**试件级** DCB 不能作为验收算例；因此 \u0060GAP-FEM-3D-COHESIVE\u0060 **未闭合**，\n  仅单元级能力可用（BK 律 + COH3D8 + 目标性 + patch + 双材料块）。\n- 小应变运动学、无摩擦/接触/循环退化（既有限制，未变）。\n- 集群 cj1024（全量 DCB）因队列深度 238 未取回，本轮结论一律基于控制节点真跑工件。\n\n## 6. 误差判定（逐项回答\"是否 <3%\"）\n\n| 关键量 | 基准 | 误差 | <3%? |\n|---|---|---|---|\n| 单元级 objectivity/patch/mode-I/mode-II/energy | 闭式 | ≤1e-10（工件 all_passed） | **是** |\n| DCB 柔性 vs 根部转角梁 | 2.35674e-05 m/N | +460.7% | **否** |\n| DCB 峰值载荷 vs LEFM | 28.699 N | -99.8% | **否** |\n| 能量平衡 \\|W-U-D\\|/W | 0 | 0.936 | **否** |\n\n## 复现命令（repro_cmd）\n\n\u0060\u0060\u0060bash\npython benchmarks/cohesive3d_verification.py            # 单元级：all_passed True\npython benchmarks/cohesive3d_dcb_displacement_control_probe.py   # 试件级：compliance passed=False（honest）\npython -m pytest tests/test_cohesive3d.py tests/test_cohesive3d_dcb.py \\\n    tests/test_cohesive3d_dcb_solver_guards.py tests/test_cohesive3d_dcb_verification.py -q\n# -> 61 passed, 2 xfailed\n\u0060\u0060\u0060\n",
            "quote_sha256": "sha256:8c696991f8bef0c1f0903d2104e88a437897875c759af309c0c7710ce1260558",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "source_sha256_recompute",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一，且 md[start:end]==quote（本脚本重算）。"
          },
          "note": "全文作为单一文档资产登记；quote=全文，sha256 与契约 source_hash 一致（见 integrity）。"
        },
        {
          "asset_id": "A02",
          "asset_class": "case_definition",
          "label": "DCB 算例定义（ASTM D5528 Mode I 层间断裂）",
          "in_report_section": "1. 案例介绍（物理背景 / 几何 / 参数）",
          "locator": {
            "method": "char_span",
            "start_char": 272,
            "end_char": 385,
            "start_line": 8,
            "end_line": 9,
            "quote": "DCB（ASTM D5528 双悬臂梁，Mode I 层间断裂）用于检验 3D 内聚单元在真实三维应力状态下\n能否给出可信的载荷-张开响应。几何：L=60 mm，b=3 mm，每臂厚 h=3 mm，初始裂纹 a0=30 mm，",
            "quote_sha256": "sha256:ca3770f0a009e487725d9b4a7fedbb5a7f886aa57b0def485d5992acabb9561b",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一，且 md[start:end]==quote（本脚本重算）。"
          },
          "note": "案例背景与用途，原文两句。"
        },
        {
          "asset_id": "A03",
          "asset_class": "parameter_set",
          "label": "几何 + 离散化 + 材料/内聚参数（L/b/h/a0、E/ν、k_n/k_s/t_n0/t_s0/G_Ic/G_IIc/BK η）",
          "in_report_section": "1. 案例介绍（物理背景 / 几何 / 参数）",
          "locator": {
            "method": "char_span",
            "start_char": 386,
            "end_char": 534,
            "start_line": 10,
            "end_line": 11,
            "quote": "结构化 HEX8 adherends + 零厚度 COH3D8 韧带。材料/内聚参数：E=70 GPa，ν=0.30，\nk_n=1e12 Pa/m，k_s=4e11 Pa/m，t_n0=5 MPa，t_s0=3 MPa，G_Ic=300 J/m²，G_IIc=800 J/m²，BK η=2.2。",
            "quote_sha256": "sha256:67eccbcd37dae25b55ffcbcdb5d7a30974f84734462723a8cbb975da0f1ae2a5",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一，且 md[start:end]==quote（本脚本重算）。"
          },
          "note": "参数以行内数字给出（无独立参数表）；本工序只登记定位，不抽取为参数卡。"
        },
        {
          "asset_id": "A04",
          "asset_class": "analytic_reference",
          "label": "解析基准（Williams 根部转角修正梁柔性 C + LEFM 峰值载荷闭式）",
          "in_report_section": "1. 案例介绍（物理背景 / 几何 / 参数）",
          "locator": {
            "method": "char_span",
            "start_char": 535,
            "end_char": 682,
            "start_line": 12,
            "end_line": 14,
            "quote": "解析基准（独立闭式）：\u0060C = 4a³/(Ebh³) + a/(5/6·G·bh)\u0060，含 Williams(1989) 根部转角修正 Δ；\nLEFM 峰值 \u0060P = b h^1.5 sqrt(G_Ic E / 6) / (a+Δ)\u0060（ASTM D5528 / Kanninen 梁理论谱系）。\n",
            "quote_sha256": "sha256:9fe70dcb5da3f8a88b8c2fd76d377204681905e601be2dea2f38d45a7b025291",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一，且 md[start:end]==quote（本脚本重算）。"
          },
          "note": "对标公式原文；属报告自述的外部基准谱系（ASTM D5528 / Kanninen），无可解析地址。"
        },
        {
          "asset_id": "A05",
          "asset_class": "defect_record",
          "label": "缺陷 A（物理错误）：加载 dof 未进 fixed_dofs → 反力恒 0",
          "in_report_section": "2. 怎么做的（方法 / 流程）",
          "locator": {
            "method": "char_span",
            "start_char": 842,
            "end_char": 987,
            "start_line": 19,
            "end_line": 21,
            "quote": "   - **缺陷 A（物理错误）**：位移控制面上被加载的 dof（x=L, z）没有进 \u0060fixed_dofs\u0060，落进自由集。\n     Newton 于是把这些 dof 的残差也压到 0 → 反力恒为 0 → 试件根本不张开、损伤恒 0、\n     所有峰值判据相对误差退化为 -1。",
            "quote_sha256": "sha256:3fc7109377b1beccd4d4d117e374204b7ee579c4da2b2c93e7105bee3ad2e6b7",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一，且 md[start:end]==quote（本脚本重算）。"
          },
          "note": "缺陷描述与后果链（反力/损伤/峰值判据退化）。"
        },
        {
          "asset_id": "A06",
          "asset_class": "defect_record",
          "label": "缺陷 B（不终止）：终步零长度步无限循环",
          "in_report_section": "2. 怎么做的（方法 / 流程）",
          "locator": {
            "method": "char_span",
            "start_char": 988,
            "end_char": 1208,
            "start_line": 22,
            "end_line": 24,
            "quote": "   - **缺陷 B（不终止）**：\u0060while delta < delta_max*(1+1e-12)\u0060 在 \u0060delta == delta_max\u0060 后恒真，\n     载荷步走完后以零长度步无限循环（历史上\"DCB 跑不完\"的直接原因，控制节点上残留 24 min 僵尸进程实证）。\n   修复：加载 dof 并入约束集；终止条件改 \u0060delta_max*(1-1e-9)\u0060 + \u0060target<=delta\u0060 断路 + 步数上限。",
            "quote_sha256": "sha256:e91ae2fd28bdccc43ff6b41b092f4b3472b5a5f574ba42637475c2a66bec2323",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一，且 md[start:end]==quote（本脚本重算）。"
          },
          "note": "含历史证据表述（控制节点残留 24 min 僵尸进程），本工序不复核该历史。"
        },
        {
          "asset_id": "A07",
          "asset_class": "test_reference",
          "label": "回归测试钉住：tests/test_cohesive3d_dcb_solver_guards.py（3 新测试）+ 修正 tests/test_cohesive3d_dcb.py",
          "in_report_section": "2. 怎么做的（方法 / 流程）",
          "locator": {
            "method": "char_span",
            "start_char": 1209,
            "end_char": 1327,
            "start_line": 25,
            "end_line": 26,
            "quote": "   行为由 \u0060tests/test_cohesive3d_dcb_solver_guards.py\u0060（3 个新测试）钉住，并修正\n   \u0060tests/test_cohesive3d_dcb.py\u0060 中记录旧（错误）契约的边界条件断言。",
            "quote_sha256": "sha256:e9a177be5448beb15d8b9a5dd244c89eee949580212dc02e9af2fb7f534fa1cf",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "external_path_absent_in_worktree",
            "paths": [
              "tests/test_cohesive3d_dcb_solver_guards.py",
              "tests/test_cohesive3d_dcb.py"
            ],
            "present": [],
            "missing": [
              "tests/test_cohesive3d_dcb_solver_guards.py",
              "tests/test_cohesive3d_dcb.py"
            ],
            "result": "unresolved",
            "detail": "本工作树=TensorKnowledge 检出；所列路径属外部仓库（TensorFEM）产物，按契约边界不复制、不臆造内容。"
          },
          "note": "路径属外部仓库（TensorFEM）检出；本工作树为 TensorKnowledge，按契约边界不复制内容。"
        },
        {
          "asset_id": "A08",
          "asset_class": "code_reference",
          "label": "修复实现文件 src/tensorfem/cohesive3d_dcb.py",
          "in_report_section": "2. 怎么做的（方法 / 流程）",
          "locator": {
            "method": "char_span",
            "start_char": 778,
            "end_char": 841,
            "start_line": 18,
            "end_line": 18,
            "quote": "   复现后定位到两个**求解器缺陷**（均已在 \u0060src/tensorfem/cohesive3d_dcb.py\u0060 修复）：",
            "quote_sha256": "sha256:6b7ab50ac7ee810a8bfcfda290a52517a8083b8ac5f37854503965aa90face22",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "external_path_absent_in_worktree",
            "paths": [
              "src/tensorfem/cohesive3d_dcb.py"
            ],
            "present": [],
            "missing": [
              "src/tensorfem/cohesive3d_dcb.py"
            ],
            "result": "unresolved",
            "detail": "本工作树=TensorKnowledge 检出；所列路径属外部仓库（TensorFEM）产物，按契约边界不复制、不臆造内容。"
          },
          "note": "报告声明两处缺陷均在该文件修复；本工作树无此路径，未核验代码内容。"
        },
        {
          "asset_id": "A09",
          "asset_class": "code_reference",
          "label": "前轮基准脚本 benchmarks/cohesive3d_dcb_3d.py（及历史轮 m14987/m15001）",
          "in_report_section": "2. 怎么做的（方法 / 流程）",
          "locator": {
            "method": "char_span",
            "start_char": 704,
            "end_char": 777,
            "start_line": 17,
            "end_line": 17,
            "quote": "1. **前轮死法定位**：m14987/m15001 的 \u0060benchmarks/cohesive3d_dcb_3d.py\u0060 从未产出运行工件。",
            "quote_sha256": "sha256:1a19b549a1d2b1c7d52934288c3057c8b1a07c0fd3a71c65cd4e9a242a7fe1e2",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "external_path_absent_in_worktree",
            "paths": [
              "benchmarks/cohesive3d_dcb_3d.py"
            ],
            "present": [],
            "missing": [
              "benchmarks/cohesive3d_dcb_3d.py"
            ],
            "result": "unresolved",
            "detail": "本工作树=TensorKnowledge 检出；所列路径属外部仓库（TensorFEM）产物，按契约边界不复制、不臆造内容。"
          },
          "note": "外部仓库脚本；同句给出历史轮次编号，仅登记为文本引用。"
        },
        {
          "asset_id": "A10",
          "asset_class": "run_artifact_reference",
          "label": "单元级验证真跑：benchmarks/cohesive3d_verification.py → benchmarks/cohesive3d_verification.json（all_passed True）",
          "in_report_section": "2. 怎么做的（方法 / 流程）",
          "locator": {
            "method": "char_span",
            "start_char": 1328,
            "end_char": 1586,
            "start_line": 27,
            "end_line": 29,
            "quote": "2. **单元级验证（真跑）**：\u0060python benchmarks/cohesive3d_verification.py\u0060 → all_passed True\n   （element_mesh_objectivity / coupled_block_mode_i / coupled_block_mode_ii / coupled_block_mesh /\n   coupled_block_energy 全 PASS），工件 \u0060benchmarks/cohesive3d_verification.json\u0060。",
            "quote_sha256": "sha256:657d62e6079074285bd5b56bc043716978c7303c0ed26173e30a06807a61b672",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "external_path_absent_in_worktree",
            "paths": [
              "benchmarks/cohesive3d_verification.py",
              "benchmarks/cohesive3d_verification.json"
            ],
            "present": [],
            "missing": [
              "benchmarks/cohesive3d_verification.py",
              "benchmarks/cohesive3d_verification.json"
            ],
            "result": "unresolved",
            "detail": "本工作树=TensorKnowledge 检出；所列路径属外部仓库（TensorFEM）产物，按契约边界不复制、不臆造内容。"
          },
          "note": "报告声明工件 all_passed True；工件本体不在本工作树，本工序只登记引用与自述结果。"
        },
        {
          "asset_id": "A11",
          "asset_class": "run_artifact_reference",
          "label": "试件级探测真跑：benchmarks/cohesive3d_dcb_displacement_control_probe.py（+ 同名 .json 工件，nx=24）",
          "in_report_section": "2. 怎么做的（方法 / 流程）",
          "locator": {
            "method": "char_span",
            "start_char": 1587,
            "end_char": 1724,
            "start_line": 30,
            "end_line": 31,
            "quote": "3. **试件级探测（真跑）**：新增 \u0060benchmarks/cohesive3d_dcb_displacement_control_probe.py\u0060\n   （nx=24, ny=1, nz=2，机器可判、0.3 s），用**修正后的位移控制**量测柔性并与梁理论对标。",
            "quote_sha256": "sha256:86cf915233aee3a9da91f1c394edda2cf32c6f05c947bdf29a4c0376fcb7117b",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "external_path_absent_in_worktree",
            "paths": [
              "benchmarks/cohesive3d_dcb_displacement_control_probe.py",
              "benchmarks/cohesive3d_dcb_displacement_control_probe.json"
            ],
            "present": [],
            "missing": [
              "benchmarks/cohesive3d_dcb_displacement_control_probe.py",
              "benchmarks/cohesive3d_dcb_displacement_control_probe.json"
            ],
            "result": "unresolved",
            "detail": "本工作树=TensorKnowledge 检出；所列路径属外部仓库（TensorFEM）产物，按契约边界不复制、不臆造内容。"
          },
          "note": "探针脚本与 JSON 工件均在外部仓库；报告声明 0.3 s 机器可判。"
        },
        {
          "asset_id": "A12",
          "asset_class": "test_result_statement",
          "label": "全量内聚 pytest 结果：61 passed, 2 xfailed（strict=True）",
          "in_report_section": "2. 怎么做的（方法 / 流程）",
          "locator": {
            "method": "char_span",
            "start_char": 1725,
            "end_char": 1798,
            "start_line": 32,
            "end_line": 32,
            "quote": "4. 全量内聚 pytest：\u006061 passed, 2 xfailed\u0060（2 个 xfail 即下述开放缺陷，strict=True 不掩盖）。",
            "quote_sha256": "sha256:e2e9a81034edd256123c556ada916f110f8f4dfe916cfb0bca0983a8a8a2bb8e",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一，且 md[start:end]==quote（本脚本重算）。"
          },
          "note": "文本自述的测试计数；测试本体见 A07，未在本工作树复跑。"
        },
        {
          "asset_id": "A13",
          "asset_class": "table",
          "label": "试件级结果表（5 行：柔性 C×2 / 峰值非零 / 终止 / 收敛）",
          "in_report_section": "3. 计算结果（数字表，程序化提取自 JSON 工件）",
          "locator": {
            "method": "char_span",
            "start_char": 1832,
            "end_char": 2336,
            "start_line": 36,
            "end_line": 44,
            "quote": "试件级（\u0060benchmarks/cohesive3d_dcb_displacement_control_probe.json\u0060）：\n\n| 量 | 基准(ref) | 本实现(got) | 相对误差 | 判据 | 判定 |\n|---|---|---|---|---|---|\n| DCB 柔性 C [m/N]（vs Williams 根部转角梁） | 2.35674e-05 | 1.32143e-04 | +460.7% | ≤10% | **FAIL** |\n| DCB 柔性 C [m/N]（vs 无转角修正梁） | 1.91962e-05 | 1.32143e-04 | +588.4% | — | **FAIL** |\n| 峰值反力非零（缺陷 A 回归） | >0 | 0.15135 N | — | >0 | PASS |\n| 终止于 delta_max（缺陷 B 回归） | delta_max | 2.0e-05 (=目标) | 0 | 精确 | PASS |\n| 收敛 | — | converged_all=True, 40 步, 16 Newton 迭代 | — | — | PASS |",
            "quote_sha256": "sha256:beb3f759cc7411e166a9518c41a90651c4bb807027d58868d4bd7689dcba69b8",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一，且 md[start:end]==quote（本脚本重算）。"
          },
          "note": "含 +460.7% / +588.4% 误差与两条回归判据；上游自报数字，本工序不复核、不标 verified。"
        },
        {
          "asset_id": "A14",
          "asset_class": "result_statement",
          "label": "单元级六项 all_passed=True 的概述陈述（数字以工件为准）",
          "in_report_section": "3. 计算结果（数字表，程序化提取自 JSON 工件）",
          "locator": {
            "method": "char_span",
            "start_char": 2338,
            "end_char": 2486,
            "start_line": 46,
            "end_line": 47,
            "quote": "单元级（\u0060benchmarks/cohesive3d_verification.json\u0060）：objectivity / patch / mode-I / mode-II /\nmesh-objectivity / energy 六项 all_passed=True（本页不重复其数字，工件为准）。",
            "quote_sha256": "sha256:f578cb8e731bcb93118c7f88b216005e9ac3d58cf74438036fcdd442334c47af",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一，且 md[start:end]==quote（本脚本重算）。"
          },
          "note": "报告显式声明不在正文重复单元级数字。"
        },
        {
          "asset_id": "A15",
          "asset_class": "run_artifact_reference",
          "label": "宽度分辨基准 benchmarks/cohesive3d_dcb_3d.json（quick，135.7 s，all_passed=False）及其陈旧助手说明",
          "in_report_section": "3. 计算结果（数字表，程序化提取自 JSON 工件）",
          "locator": {
            "method": "char_span",
            "start_char": 2488,
            "end_char": 2879,
            "start_line": 49,
            "end_line": 53,
            "quote": "宽度分辨基准（\u0060benchmarks/cohesive3d_dcb_3d.json\u0060，quick 模式，runtime 135.7 s）：\n\u0060all_passed=False\u0060；其中 \u0060compliance_bracket\u0060 的 \u0060got=0.0\u0060 是该脚本内 \u0060linear_compliance()\u0060\n仍在用\"加载 dof 自由 + 单位力\"的旧写法（修正后 prescribe 面上受力→位移恒 0），属**待迁移的陈旧助手**，\n真实可判数字以 probe 的 +460.7% 为准；\u0060peak_load_vs_lefm\u0060 got=0.0572 N vs ref=28.699 N（-99.8%）、\n\u0060energy_balance_rel\u0060=0.936、\u0060width_objectivity\u0060 got=0.719 vs ref=30.085 —— 均为同一根因（试件过柔）。",
            "quote_sha256": "sha256:15259badde88c27d75bf06802f913431193d816b9b617f195b709f0e42f2842d",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "external_path_absent_in_worktree",
            "paths": [
              "benchmarks/cohesive3d_dcb_3d.json"
            ],
            "present": [],
            "missing": [
              "benchmarks/cohesive3d_dcb_3d.json"
            ],
            "result": "unresolved",
            "detail": "本工作树=TensorKnowledge 检出；所列路径属外部仓库（TensorFEM）产物，按契约边界不复制、不臆造内容。"
          },
          "note": "JSON 工件在外部仓库；正文数字（+460.7% / -99.8% / 0.936 / 0.719 vs 30.085）为自述。"
        },
        {
          "asset_id": "A16",
          "asset_class": "figure_declaration",
          "label": "图件声明：docs/assets/cohesive3d-dcb-3d/{load_opening,damage_field,rcurve}.png",
          "in_report_section": "4. 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 2892,
            "end_char": 3077,
            "start_line": 57,
            "end_line": 59,
            "quote": "\u0060docs/assets/cohesive3d-dcb-3d/load_opening.png\u0060（载荷-张开曲线）、\u0060damage_field.png\u0060（损伤场）、\n\u0060rcurve.png\u0060（R 曲线）：由 \u0060benchmarks/cohesive3d_dcb_3d.py\u0060 真跑生成，图中峰值/损伤的异常形态\n正是上述\"试件过柔\"的直观体现。平台报告内嵌同一 PNG。",
            "quote_sha256": "sha256:ae6b339c04ffa55feb8152aca3401792a7a2bbe57de8479a3fc60f5179f422b3",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "record_figures_and_path_check",
            "paths": [
              "docs/assets/cohesive3d-dcb-3d/load_opening.png",
              "docs/assets/cohesive3d-dcb-3d/damage_field.png",
              "docs/assets/cohesive3d-dcb-3d/rcurve.png"
            ],
            "present": [],
            "missing": [
              "docs/assets/cohesive3d-dcb-3d/load_opening.png",
              "docs/assets/cohesive3d-dcb-3d/damage_field.png",
              "docs/assets/cohesive3d-dcb-3d/rcurve.png"
            ],
            "result": "unresolved",
            "detail": "figures[] 仅有 name/caption（无 png_base64 载荷），且 rcurve.png 不在 figures[]；docs/assets 路径不在本工作树。",
            "record_figures_names": [
              "load_opening.png",
              "damage_field.png"
            ],
            "record_figures_matched": [
              "load_opening.png",
              "damage_field.png"
            ],
            "record_figures_missing": [
              "rcurve.png"
            ]
          },
          "note": "3 个 PNG 路径：平台 figures[] 仅 2 条同名（无二进制载荷），rcurve.png 未出现在 figures[]；docs/assets/ 路径不在本工作树。"
        },
        {
          "asset_id": "A17",
          "asset_class": "open_defect_statement",
          "label": "开放缺陷：试件柔性为梁理论 5.6–6.9 倍（疑似有效自由跨度 2a）",
          "in_report_section": "5. 注意点 / 局限",
          "locator": {
            "method": "char_span",
            "start_char": 3095,
            "end_char": 3292,
            "start_line": 63,
            "end_line": 66,
            "quote": "- **开放缺陷（未解决）**：修正位移控制后正常加载，FE 试件柔性是梁理论的 ~5.6–6.9 倍\n  （nx=24 时 5.61×；nx=50 时约 11×），量级接近 2³，**首要怀疑有效自由跨度为 2a**\n  （韧带/夹持区定位或 adherends 与内聚面带耦合位置待核），已写入 2 个 strict-xfail 测试与\n  \u0060negative\u0060 记录；未在本轮预算内定案。",
            "quote_sha256": "sha256:aa00991323b5d6736570d827c4fc5024d8c222879aaa9d00ef9e379ce3f7e7c1",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一，且 md[start:end]==quote（本脚本重算）。"
          },
          "note": "报告自述未定案；含 nx=24→5.61×、nx=50→约 11× 两处量级，以及 2 个 strict-xfail 测试与 negative 记录的引用（本体未在本工作树）。"
        },
        {
          "asset_id": "A18",
          "asset_class": "negation_record_reference",
          "label": "锚点未闭合声明（试件级 DCB 不能作验收算例；仅单元级能力可用）",
          "in_report_section": "5. 注意点 / 局限",
          "locator": {
            "method": "char_span",
            "start_char": 3293,
            "end_char": 3401,
            "start_line": 67,
            "end_line": 68,
            "quote": "- 该缺陷使**试件级** DCB 不能作为验收算例；因此 \u0060GAP-FEM-3D-COHESIVE\u0060 **未闭合**，\n  仅单元级能力可用（BK 律 + COH3D8 + 目标性 + patch + 双材料块）。",
            "quote_sha256": "sha256:8c969b2750f40c55bdadf04d285233144b97885b7c81cad532405298435ec6d0",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一，且 md[start:end]==quote（本脚本重算）。"
          },
          "note": "否定性结论原文；2 个 strict-xfail 测试与 negative 记录的引用位于 A17 引文内（本工序未解析其本体）。"
        },
        {
          "asset_id": "A19",
          "asset_class": "limitation_set",
          "label": "既有适用限制：小应变运动学、无摩擦/接触/循环退化",
          "in_report_section": "5. 注意点 / 局限",
          "locator": {
            "method": "char_span",
            "start_char": 3402,
            "end_char": 3432,
            "start_line": 69,
            "end_line": 69,
            "quote": "- 小应变运动学、无摩擦/接触/循环退化（既有限制，未变）。",
            "quote_sha256": "sha256:5b4974d71033faf2ba4f787308f201fb2930c98ec279aad766b97de10ab2cd67",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一，且 md[start:end]==quote（本脚本重算）。"
          },
          "note": "报告声明为既有限制、本轮未变。"
        },
        {
          "asset_id": "A20",
          "asset_class": "external_job_reference",
          "label": "集群作业 cj1024（全量 DCB，队列深度 238，未取回）",
          "in_report_section": "5. 注意点 / 局限",
          "locator": {
            "method": "char_span",
            "start_char": 3433,
            "end_char": 3483,
            "start_line": 70,
            "end_line": 70,
            "quote": "- 集群 cj1024（全量 DCB）因队列深度 238 未取回，本轮结论一律基于控制节点真跑工件。",
            "quote_sha256": "sha256:a6f0a5e0d07fa477989b8c2142446e792a9474b759b4846872d109efe7c31192",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "cluster_artifact_lookup",
            "job_id": "cj1024",
            "result": "unresolved",
            "detail": "报告自述未取回；本工序不查询集群历史队列状态（避免把当前快照当作历史事实）。"
          },
          "note": "仅文本引用；本工序不向集群查询历史队列状态（快照≠历史事实），故工件不可解析。"
        },
        {
          "asset_id": "A21",
          "asset_class": "table",
          "label": "误差判定表（4 行，逐项回答是否 <3%）",
          "in_report_section": "6. 误差判定（逐项回答\"是否 <3%\"）",
          "locator": {
            "method": "char_span",
            "start_char": 3511,
            "end_char": 3784,
            "start_line": 74,
            "end_line": 79,
            "quote": "| 关键量 | 基准 | 误差 | <3%? |\n|---|---|---|---|\n| 单元级 objectivity/patch/mode-I/mode-II/energy | 闭式 | ≤1e-10（工件 all_passed） | **是** |\n| DCB 柔性 vs 根部转角梁 | 2.35674e-05 m/N | +460.7% | **否** |\n| DCB 峰值载荷 vs LEFM | 28.699 N | -99.8% | **否** |\n| 能量平衡 \\|W-U-D\\|/W | 0 | 0.936 | **否** |",
            "quote_sha256": "sha256:d34e65e317c0f923e6a96c52f4a6fbec2e009d28d25d82e4140b9df2114ed8d2",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一，且 md[start:end]==quote（本脚本重算）。"
          },
          "note": "上游自报：单元级 ≤1e-10 判是；柔性/峰值/能量三项判否（+460.7% / -99.8% / 0.936）。"
        },
        {
          "asset_id": "A22",
          "asset_class": "repro_command_set",
          "label": "repro_cmd（4 条命令块：单元级 / 探针 / pytest）",
          "in_report_section": "复现命令（repro_cmd）",
          "locator": {
            "method": "char_span",
            "start_char": 3814,
            "end_char": 4185,
            "start_line": 84,
            "end_line": 88,
            "quote": "python benchmarks/cohesive3d_verification.py            # 单元级：all_passed True\npython benchmarks/cohesive3d_dcb_displacement_control_probe.py   # 试件级：compliance passed=False（honest）\npython -m pytest tests/test_cohesive3d.py tests/test_cohesive3d_dcb.py \\\n    tests/test_cohesive3d_dcb_solver_guards.py tests/test_cohesive3d_dcb_verification.py -q\n# -> 61 passed, 2 xfailed",
            "quote_sha256": "sha256:6b01d9e3370b1a338f42c121a0bc27f5845897211ba007d701e707ec1935f3f6",
            "quote_unique": true,
            "matches_source": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "detail": "quote 在 markdown 中唯一，且 md[start:end]==quote（本脚本重算）。"
          },
          "note": "命令块原文；命令引用外部仓库脚本，本工作树不可直接执行。"
        }
      ],
      "counts": {
        "assets": 22,
        "by_class": {
          "source_document": 1,
          "case_definition": 1,
          "parameter_set": 1,
          "analytic_reference": 1,
          "defect_record": 2,
          "test_reference": 1,
          "code_reference": 2,
          "run_artifact_reference": 3,
          "test_result_statement": 1,
          "table": 2,
          "result_statement": 1,
          "figure_declaration": 1,
          "open_defect_statement": 1,
          "negation_record_reference": 1,
          "limitation_set": 1,
          "external_job_reference": 1,
          "repro_command_set": 1
        },
        "by_resolution": {
          "resolved_in_source": 14,
          "referenced_unresolved": 8,
          "declared_absent": 0
        }
      },
      "claims": [],
      "claim_policy": {
        "count": 0,
        "reason": "契约 objective.classify_report_type=false、notes=不做抽取；且 no_forced_claim_generation / do_not_mark_claims_as_verified 要求不得为凑指标造知识。",
        "consequence": "报告内所有结论性表述保持原文状态（含 honest-FAIL 的 3 项未达标），既未升格为 claim，也未标注 verified；verification 由平台门计算。",
        "acceptance_item_all_claims_have_evidence_or_explicit_unresolved_status": "vacuous-true：claims 为空数组（契约允许），无缺证据的 claim 条目。"
      },
      "integrity": {
        "quote_uniqueness": true,
        "hash_recomputed_locally": "sha256:8c696991f8bef0c1f0903d2104e88a437897875c759af309c0c7710ce1260558",
        "hash_matches_contract": true,
        "no_duplicate_ids": true,
        "all_locators_resolvable": true,
        "claims_marked_verified": 0
      },
      "limitations": [
        "本工序只做资产登记：不做类型分类、不做知识抽取、不复核任何数字（+460.7%/-99.8%/0.936 等均为上游自述）。",
        "8 条资产指向外部仓库（TensorFEM）文件/工件/集群作业，其内容无法在本工作树解析，故标 referenced_unresolved 而非 resolved。",
        "平台 figures[] 仅返回 name/caption、无 png_base64 载荷，图件二进制不可校验；rcurve.png 未出现在 figures[]。",
        "本工作树若无 contracts/ 下的契约文件，则 sha256/chars 契约值取自任务下发的包契约文本（见 generator_inputs）。"
      ]
    }
  },
  "claims": []
}
```
