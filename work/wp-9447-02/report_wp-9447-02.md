# KF-RESULT wp-9447-02

- package_id `wp-9447-02` ｜ task_type `02-classification-parse` ｜ report_id `9447` ｜ lane B ｜ 分层 TensorPlatform|research|A
- 源 `tensor://reports/9447`（field=`markdown`）：7241 字符 / 10955 字节，sha256 `a0be8122d188c0507610e1533ddb4ccbfb38f678d557ff23fe8710d52139c666`，与契约声明一致 = **是**
- 报告标题（原文逐字）：补报：冰-水拖曳力系数标定（node 18 / mission 683）——零残差是自比较，独立重判 WITHHELD
- 分类结论：primary = **`experimental-validation`**（confidence **medium**，score 3.5，lead 1.5）；runner-up `software-engineering`；subtype = evidence-audit / 证据链重建 + 重新判级（re-issue）（in_register = False，taxonomy_coverage = partial）

## ① 本工序做了什么（案例介绍）

对象是一份**补报**：`report_id=9447`，场景 `ice_drag_cd_reissue`，报告内部 mission_id = 683（补报单 m8102）。物理背景是冰颗粒/碎冰在流体中的相间拖曳力系数闭合 Cd(Re)（LBM-DEM 耦合的动量交换项），而上游节点曾以“误差 0.000000”判 done；该补报的实质是**证据链重建 + 重新判级**。

工序 02 只做三件受约束的小事：

1. **类型判定**：按 `extraction-skills/registry.json` 六分型 `identify_signals` 给分，primary = `experimental-validation`，绑定 skill `xsk-experimental-validation`（v0.1.0，lifecycle=template-created）。
2. **主题标签**：学科 ['冰区航行', '阻力']；域 `ice-hydrodynamics / LBM-DEM 相间动量交换（拖曳力系数闭合标定与证据判级）`；10 个关键词全部逐字命中原文（keywords_verified_verbatim=True）。
3. **结构切分 + 判定依据定位**：10 个标题、5 张表、1 个代码块、13 条证据定位，编号列表缺口 1 处。

**不做**：不抽取（`claims=[]`，schema 强制 maxItems=0）、不登记资产（`register_assets=false`）、不给任何结论贴 verified（`classification_status=hypothesis-draft-revocable`）。抽取属工序 03，资产属工序 01，验证级别由平台门算。

## ② 怎么做的（方法/流程/关键设置/工具链）

1. **取原文**：`GET $TENSOR_API_BASE/tensor/reports/9447`，落盘 `work/wp-9447-02/sources/9447.md`（本次 fetched_via = `platform_http:/tensor/reports/9447`）。先独立重算 sha256 与契约声明比对：sha256:a0be8122d188c0507610e1533ddb4ccbfb38f678d557ff23fe8710d52139c666 vs sha256:a0be8122d188c0507610e1533ddb4ccbfb38f678d557ff23fe8710d52139c666。
2. **零手抄定位**：脚本里只写“锚串”，锚串扩展成**整行**作为 quote，记录 `start_offset/end_offset`（Python 码点索引）+ `start_line` + `content_hash=sha256(quote)`。表格行整行成 quote，数字无法被手抄变形。
3. **定位复核**：复用平台门 `ke.wp_gate.locator_matches()` 逐字节比对（不自造规则），13/13 通过。
4. **六分型打分**（规则预声明在脚本 docstring 与 `decision_rule`）：对每类型数其 registry `identify_signals` 是否被证据支持（yes=1/partial=0.5/no=0）求和；另跑中英信号词词法计数作旁证，**不参与打分**；门槛 primary≥2.0 且 lead≥1.0，否则 `unclassified`。
5. **结构解析**：正则切标题（记 offset/行号）、数表与围栏代码块、检查编号列表连续性。
6. **schema 校验**：产物对 `schemas/classification.v1.schema.json`（Draft 2020-12，本包新写，`additionalProperties=false`）做 jsonschema 校验。
7. **边界**：只读 report 9447；不读/写其它 report_id；不改上游产物。

## ③ 产出物清单与计算结果

| 输出文件 | 要点 |
|---|---|
| `work/wp-9447-02/classification.json` | 唯一产物：六分型判定 + 主题标签 + 结构切分 + 13 条证据定位 + self_check |
| `work/wp-9447-02/sources/9447.md` | 原文逐字副本（离线复跑 + 哈希复核） |
| `work/wp-9447-02/sources/9447.meta.json` | 报告元信息（title/scenario_key/mission_id/tags） |
| `work/wp-9447-02/work-package.json` | 工作包契约（YAML 全文的 JSON 形态） |
| `work/wp-9447-02/checks.json` | 自检明细（逐条 locator 解析码、词法计数、打分） |
| `work/wp-9447-02/fig1_signal_support.png` | 图 1：六分型信号支持度与匹配构成 |
| `work/wp-9447-02/kf_result_wp-9447-02.json` | 提交用 KF-RESULT（与本报告 json 块同字节） |
| `schemas/classification.v1.schema.json` | 工序 02 产物 schema（本包新增） |
| `scripts/wp_9447_02/classify_9447.py` | 一键复跑生成器（本报告所有数字由它注入） |

### 3.1 六分型支持度（决定 primary）

| report_type | support_score | 词法命中（旁证） | 处置 |
|---|---|---|---|
| `experimental-validation` | 3.5 | 22 | supported |
| `software-engineering` | 2.0 | 5 | partial |
| `scientific-computation` | 0.5 | 1 | partial |
| `algorithm-implementation` | 0.0 | 0 | not-supported |
| `literature-review` | 0.0 | 0 | not-supported |
| `technical-proposal` | 0.0 | 0 | not-supported |

primary = `experimental-validation`（score 3.5，lead 1.5），confidence = medium，runner-up = `software-engineering`；taxonomy_coverage = partial（六分型无 audit 类，subtype 显式标注不在册）。

引用密度旁证：0.28/1000 字符（阈值 5，未达标）。

### 3.2 结构切分

| level | 标题（逐字） | start_offset | start_line |
|---|---|---|---|
| 1 | 补报：冰-水拖曳力系数标定（plan 1 / node 18 / mission 683） | 0 | 1 |
| 2 | ① 案例介绍 | 360 | 10 |
| 2 | ② 方法/流程 | 1018 | 30 |
| 2 | ③ 计算结果 | 2074 | 50 |
| 3 | 3.1 机器判级（关键结论） | 2085 | 52 |
| 3 | 3.2 独立基准 Cd(Re) | 2694 | 68 |
| 2 | ④ 结果图 | 3998 | 101 |
| 2 | ⑤ 注意点（坑 / 局限 / 适用范围） | 4682 | 112 |
| 2 | ⑥ 误差判定（逐项，显式回答是否 <3%） | 5954 | 135 |
| 2 | 产物与复现 | 6737 | 154 |

表 5 张、围栏代码块 1 个；编号缺口：[('⑤ 注意点（坑 / 局限 / 适用范围）', [7])]。

### 3.3 结果图

![fig1](fig1_signal_support.png)

图 1（`fig1_signal_support.png`）：左 = 六分型 registry 信号支持度（虚线 = 2.0 门槛，括号内为词法命中数，仅作旁证）；右 = 每类型信号匹配构成 yes/partial/no。数据全部来自 classification.json 的 report_type.support_scores 与 signal_table。

**为何没有场量云图**：工序 02 的输入是报告 markdown，本包不求解任何物理场、也不重算报告里的 Cd(Re) 数字，因此不存在“场量云图”与“对解析解/实验的曲线”可画；本包唯一的量化对象是“六分型的 registry 信号是否被原文证据支持”，已由上图给出。按纪律声明缺口而不以示意图搪塞。

## ④ 证据定位表（claim/字段 → 原文引文片段）

逐字落在 `work/wp-9447-02/sources/9447.md`；offset/行号由脚本计算。

| id | 支持的分类字段 | char_span | 行 | 原文引文（逐字） |
|---|---|---|---|---|
| E01 | subtype:evidence-audit | [220,264) | 6 | - 本报告性质：**证据链重建 + 重新判级**。原始工作树已被回收，原始工件在全盘（含 |
| E02 | experimental-validation | [6110,6168) | 140 | \| SN 闭合 Cd(Re)，Re∈[1,800] \| 实验标准阻力曲线 \| 最大 7.18 % \| **否** \| |
| E03 | experimental-validation | [780,891) | 26 | \| 参考数据（本报告独立基准） \| Clift, Grace & Weber (1978) standard drag curve (Lapple-Shepherd tabulation), smooth sphere \| |
| E04 | experimental-validation | [5063,5110) | 121 | 3. **参考数据的精度天花板**：实验标准阻力曲线表格本身有 ~1–2% 的取整/数据散布， |
| E05 | experimental-validation/scientific-computation | [5175,5237) | 124 | 4. **适用范围**：Schiller-Naumann 仅 Re ≲ 800 有效；声明的 `Re∈[1,1e5]` 覆盖 |
| E06 | subtype:evidence-audit | [2168,2251) | 56 | \| A. as_reported（记录证据结构） \| **WITHHELD** \| `R10_INDEPENDENCE` \| `SAME_SOURCE_COPY` \| |
| E07 | subtype:evidence-audit | [6405,6461) | 146 | **结论（honest）**：node 18 的 `done` 状态**不由其记录的证据支撑**——唯一记录到的 |
| E08 | software-engineering | [1465,1544) | 38 |    `/root/TensorLBM_test_waic`）执行 `git log --all --name-status -- '*ice_drag*'` |
| E09 | software-engineering | [568,643) | 16 | `pytest_test_drag_coefficient == PASS`。原结果记录 `Cd_error_vs_ITTC = 0.000000`、 |
| E10 | software-engineering | [7187,7240) | 163 | 复现：`python3 runs/m8102/ice_drag_cd/node18_reissue.py` |
| E11 | scientific-computation | [938,1016) | 28 | \| 闭合族 \| Schiller-Naumann `24/Re(1+0.15Re^0.687)`；Morrison (2013)；Newton 0.44 \| |
| E12 | structure:anomaly | [5577,5870) | 131 | 8. **与既有补报 report 9349 的关系**：9349（2026-11-09T04:12Z，0 图）以「TensorLBM DEM Schiller-Naumann 模型 vs sphere Re=100 LBM 基准」报 T1/T2 误差 2.77%/2.54%（<3%）。本报告与之不矛盾：Re=100 处 SN 对实验标准阻力曲线的误差为 2.0%，与 2.5–3% 同量级；但 9349 未覆盖 Re>800，本报告指出全 Re 覆盖不成立（79.1% @Re=1e5）。两报合并后的正确结论是「Re≲800 合格、全 Re 覆盖不成立」，而非原单声称的 0 误差。 |
| E13 | subtype:evidence-audit | [1545,1580) | 39 |    → 零命中。结论：**原始工件不可恢复**（诚实记录，不补造）。 |

全部 locator 解析码见 `work/wp-9447-02/checks.json`（E01–E13 共 13 条，非 `OK_OFFSETS` 的条数 = 0）。

## ⑤ 注意点与局限

1. **分类是假设**：`classification_status = hypothesis-draft-revocable`。六分型在中文语料下的词法信号只覆盖字面词，语义映射在 `signal_table` 里逐条挂了证据，任何人都能用一条反例 locator 推翻 primary。
2. **分型缺 audit 类型**：报告主产出是“撤销原单 REAL 判定”，六分型里没有对应类型；本包按信号把 primary 定到 `experimental-validation`，同时把 subtype 标为 in_register=false，taxonomy_coverage=partial——不把审计报告硬塞成验证报告。
3. **结构异常**：[('⑤ 注意点（坑 / 局限 / 适用范围）', [1, 2, 3, 4, 5, 6, 8, 9], [7])]，⑤ 的编号从 6 跳到 8。这是原文事实，本包只记录、不改写（不改上游产物）。
4. **不做资产核验**：报告提到原始工件全盘不可检索；本包 register_assets=false，既不确认也不否认这些工件存在（属工序 01）。
5. **不改判**：报告自身的 WITHHELD/REAL 机器判定属上游内容；本包只分类，不背书、不推翻。
6. **边界**：只碰 report 9447；没有读/写其它 report_id，因而无法做跨报告对比（跨报告属工序 05）。

## ⑥ 自检与误差判定

### 6.1 逐条 acceptance

| acceptance | 结果 | 依据 |
|---|---|---|
| `valid_json` | ✅ pass | json.dumps/loads 往返一致（ensure_ascii=False） |
| `schema_pass` | ✅ pass | jsonschema Draft2020-12 对 classification.v1.schema.json 校验通过 |
| `source_locator_resolvable` | ✅ pass | 13/13 locator 经 ke.wp_gate.locator_matches 逐字节解析通过 |
| `source_hash_matches` | ✅ pass | declared=sha256:a0be8122d188c0507610e1533ddb4ccbfb38f678d557ff23fe8710d52139c666 computed=sha256:a0be8122d188c0507610e1533ddb4ccbfb38f678d557ff23fe8710d52139c666 chars=7241（契约声明 7241） |
| `no_duplicate_ids` | ✅ pass | ids=['E01', 'E02', 'E03', 'E04', 'E05', 'E06', 'E07', 'E08', 'E09', 'E10', 'E11', 'E12', 'E13'] |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✅ pass（空真，已声明） | 本工序不做抽取：claims 恒为空数组（schema maxItems=0），“每条 claim 都有证据”为空真；未抽取不等于已核实 |

诚实说明：第 6 条为空真（本工序不抽取 claim），不粉饰为“证据已核”。

### 6.2 关键量 vs 基准，是否 <3%

| 关键量 | 基准 | 实测差异 | 是否 <3% |
|---|---|---|---|
| 源 markdown sha256 | 契约声明 `a0be8122d188c050…` | 完全一致（0 字节差异） | **是**（精确相等） |
| 源字符数 | 契约 `chars: 7241` | 7241 | **是**（精确相等） |
| locator 可解析率 | 13/13（契约要求全解析） | 13/13 通过，失败 0 条 | **是**（0.0% 失败率） |
| 关键词逐字命中率 | 10 个 | 10/10，缺 无 | **是**（0% 缺失） |
| 分类置信度 | 预声明门槛 score≥2.0 & lead≥1.0 | score 3.5，lead 1.5 | **是**（过门槛） |

**物理量的精度判据（3%）在本包不适用**：本包不产生物理量、不复算 Cd(Re)、不重跑任何算例，报告里的 Cd 误差数字只是被定位的原文内容（例如 E02 行内即含其数值），不是本包的测量结果。因此“是否 <3%”只对上述可精确判定的量作答：**全部为精确相等或 0% 失败率，均 <3%**；物理精度不作答（无基准可算），不拿上游数字冒充自己的精度。

### 6.3 repro_cmd（一键复跑）

    python3 scripts/wp_9447_02/classify_9447.py --offline

（去掉 `--offline` 则先经平台 API 重取原文并重写 `sources/9447.md`；脚本会重建 classification.json / checks.json / 图 / kf_result 与本报告 markdown。）

## KF-RESULT（唯一 json 代码块）

```json
{
  "package_id": "wp-9447-02",
  "task_type": "02-classification-parse",
  "contract_version": "1.0",
  "report_id": "9447",
  "provenance": {
    "source_uri": "tensor://reports/9447",
    "source_field": "markdown",
    "source_hash": "sha256:a0be8122d188c0507610e1533ddb4ccbfb38f678d557ff23fe8710d52139c666",
    "source_hash_matches": true,
    "title": "补报：冰-水拖曳力系数标定（node 18 / mission 683）——零残差是自比较，独立重判 WITHHELD",
    "scenario_key": "ice_drag_cd_reissue",
    "chars": 7241
  },
  "outputs": {
    "classification.json": {
      "schema": "classification.v1",
      "package_id": "wp-9447-02",
      "task_type": "02-classification-parse",
      "contract_version": "1.0",
      "report_id": "9447",
      "classification_status": "hypothesis-draft-revocable",
      "classification_scope": {
        "classify_report_type": true,
        "register_assets": false,
        "extraction_performed": false,
        "claims": []
      },
      "source": {
        "uri": "tensor://reports/9447",
        "field": "markdown",
        "declared_hash": "sha256:a0be8122d188c0507610e1533ddb4ccbfb38f678d557ff23fe8710d52139c666",
        "computed_hash": "sha256:a0be8122d188c0507610e1533ddb4ccbfb38f678d557ff23fe8710d52139c666",
        "hash_matches": true,
        "chars": 7241,
        "bytes_utf8": 10955,
        "fetched_via": "platform_http:/tensor/reports/9447",
        "title": "补报：冰-水拖曳力系数标定（node 18 / mission 683）——零残差是自比较，独立重判 WITHHELD",
        "scenario_key": "ice_drag_cd_reissue",
        "mission_id_in_report": 683
      },
      "report_type": {
        "primary": "experimental-validation",
        "confidence": "medium",
        "decision_rule": "support_score = Σ registry identify_signals 匹配度（yes=1, partial=0.5, no=0）；primary=argmax，要求 score≥2.0 且 lead≥1.0 否则 unclassified；confidence: high⇔score≥3.0 且 lead≥2.0，medium⇔score≥2.0 且 lead≥1.0；词法命中只作旁证不参与打分",
        "support_scores": {
          "experimental-validation": 3.5,
          "scientific-computation": 0.5,
          "software-engineering": 2.0,
          "literature-review": 0.0,
          "algorithm-implementation": 0.0,
          "technical-proposal": 0.0
        },
        "runner_up": "software-engineering",
        "taxonomy_coverage": "partial",
        "subtype": {
          "label": "evidence-audit / 证据链重建 + 重新判级（re-issue）",
          "in_register": false,
          "gap_note": "extraction-skills/registry.json 六分型里没有“审计/重新判级”类型；报告主产出是撤销原单 REAL 判定，按分型只能贴近 experimental-validation，故 taxonomy_coverage=partial，subtype 显式标注不在册（不硬塞进六分型）。",
          "evidence_refs": [
            "E01",
            "E06",
            "E07",
            "E13"
          ]
        },
        "alternatives": [
          {
            "report_type": "experimental-validation",
            "disposition": "supported",
            "support_score": 3.5,
            "reason": "以实验标准阻力曲线为基准做逐 Re 验证，并给出显式误差判定与适用域上限",
            "evidence_refs": [
              "E02",
              "E03",
              "E04"
            ],
            "lexical_hits": 22
          },
          {
            "report_type": "software-engineering",
            "disposition": "partial",
            "support_score": 2.0,
            "reason": "取证手段是 git 全分支检索与 pytest 判据引用，但报告不是变更记录",
            "evidence_refs": [
              "E08",
              "E09"
            ],
            "lexical_hits": 5
          },
          {
            "report_type": "scientific-computation",
            "disposition": "partial",
            "support_score": 0.5,
            "reason": "只出现闭合族公式，无控制方程/离散/收敛研究，数值部分由外部基准承载",
            "evidence_refs": [
              "E11"
            ],
            "lexical_hits": 1
          },
          {
            "report_type": "algorithm-implementation",
            "disposition": "not-supported",
            "support_score": 0.0,
            "reason": "无伪代码/复杂度/算法块",
            "evidence_refs": [],
            "lexical_hits": 0
          },
          {
            "report_type": "literature-review",
            "disposition": "not-supported",
            "support_score": 0.0,
            "reason": "仅 2 处年份引用、无综述章节，低于 citation density 阈值",
            "evidence_refs": [],
            "lexical_hits": 0
          },
          {
            "report_type": "technical-proposal",
            "disposition": "not-supported",
            "support_score": 0.0,
            "reason": "无提案/路线图/规范；标题的 plan 是战役节点编号",
            "evidence_refs": [],
            "lexical_hits": 0
          }
        ],
        "signal_table": [
          {
            "report_type": "experimental-validation",
            "signal": "baseline comparison",
            "matched": "yes",
            "evidence_refs": [
              "E02",
              "E03"
            ],
            "note": "3.2 表把闭合族逐 Re 与实验标准阻力曲线比对"
          },
          {
            "report_type": "experimental-validation",
            "signal": "validation case",
            "matched": "yes",
            "evidence_refs": [
              "E02"
            ],
            "note": "逐 Re 误差 + ⑥ 误差判定表显式回答是否 <3%"
          },
          {
            "report_type": "experimental-validation",
            "signal": "measurement uncertainty",
            "matched": "yes",
            "evidence_refs": [
              "E04"
            ],
            "note": "参考表格 ~1–2% 取整/散布给出的分辨力上限"
          },
          {
            "report_type": "experimental-validation",
            "signal": "test matrix",
            "matched": "partial",
            "evidence_refs": [],
            "note": "只有 Re 扫描网格，无多工况/实验设施矩阵"
          },
          {
            "report_type": "experimental-validation",
            "signal": "facility",
            "matched": "no",
            "evidence_refs": [],
            "note": "无实验装置；基准是文献表格，非自有测量"
          },
          {
            "report_type": "scientific-computation",
            "signal": "governing equations",
            "matched": "partial",
            "evidence_refs": [
              "E11"
            ],
            "note": "只给拖曳力式与闭合族，无控制方程推导"
          },
          {
            "report_type": "scientific-computation",
            "signal": "discretisation",
            "matched": "no",
            "evidence_refs": [],
            "note": "全文无离散格式描述"
          },
          {
            "report_type": "scientific-computation",
            "signal": "convergence study",
            "matched": "no",
            "evidence_refs": [],
            "note": "全文无收敛研究"
          },
          {
            "report_type": "scientific-computation",
            "signal": "mesh refinement",
            "matched": "no",
            "evidence_refs": [],
            "note": "全文无网格加密"
          },
          {
            "report_type": "scientific-computation",
            "signal": "timing table",
            "matched": "no",
            "evidence_refs": [],
            "note": "全文无耗时表"
          },
          {
            "report_type": "software-engineering",
            "signal": "changed files",
            "matched": "partial",
            "evidence_refs": [
              "E08"
            ],
            "note": "原节点 5 个 on_disk_changes 仅作取证对象引用，非变更记录"
          },
          {
            "report_type": "software-engineering",
            "signal": "commit",
            "matched": "yes",
            "evidence_refs": [
              "E08"
            ],
            "note": "以 git log --all 全分支检索作为取证手段"
          },
          {
            "report_type": "software-engineering",
            "signal": "regression",
            "matched": "partial",
            "evidence_refs": [
              "E09"
            ],
            "note": "引用原单 pytest 判据，本报告未复跑"
          },
          {
            "report_type": "software-engineering",
            "signal": "interface",
            "matched": "no",
            "evidence_refs": [],
            "note": "无接口变更"
          },
          {
            "report_type": "software-engineering",
            "signal": "API",
            "matched": "no",
            "evidence_refs": [],
            "note": "无 API 变更"
          },
          {
            "report_type": "literature-review",
            "signal": "related work",
            "matched": "no",
            "evidence_refs": [],
            "note": "无相关工作综述章节"
          },
          {
            "report_type": "literature-review",
            "signal": "state of the art",
            "matched": "no",
            "evidence_refs": [],
            "note": "无现状综述"
          },
          {
            "report_type": "literature-review",
            "signal": "survey",
            "matched": "no",
            "evidence_refs": [],
            "note": "无 survey"
          },
          {
            "report_type": "literature-review",
            "signal": "bibliography",
            "matched": "no",
            "evidence_refs": [],
            "note": "无参考文献表"
          },
          {
            "report_type": "literature-review",
            "signal": "citation density >= 5 per 1000 chars",
            "matched": "no",
            "evidence_refs": [],
            "note": "实测 2 处年份引用 / 7241 字符 = 0.28/1000，远低于阈值 5",
            "lexical_hits": 2
          },
          {
            "report_type": "algorithm-implementation",
            "signal": "pseudocode",
            "matched": "no",
            "evidence_refs": [],
            "note": "无伪代码"
          },
          {
            "report_type": "algorithm-implementation",
            "signal": "complexity",
            "matched": "no",
            "evidence_refs": [],
            "note": "无复杂度陈述"
          },
          {
            "report_type": "algorithm-implementation",
            "signal": "algorithm block",
            "matched": "no",
            "evidence_refs": [],
            "note": "无算法块"
          },
          {
            "report_type": "algorithm-implementation",
            "signal": "function signature",
            "matched": "no",
            "evidence_refs": [],
            "note": "无函数签名"
          },
          {
            "report_type": "algorithm-implementation",
            "signal": "O(n",
            "matched": "no",
            "evidence_refs": [],
            "note": "无 O(·) 记号"
          },
          {
            "report_type": "technical-proposal",
            "signal": "proposal",
            "matched": "no",
            "evidence_refs": [],
            "note": "标题里的 plan 指战役 plan，不构成方案书信号"
          },
          {
            "report_type": "technical-proposal",
            "signal": "design",
            "matched": "no",
            "evidence_refs": [],
            "note": "无设计章节"
          },
          {
            "report_type": "technical-proposal",
            "signal": "roadmap",
            "matched": "no",
            "evidence_refs": [],
            "note": "无路线图"
          },
          {
            "report_type": "technical-proposal",
            "signal": "specification",
            "matched": "no",
            "evidence_refs": [],
            "note": "无规范章节"
          },
          {
            "report_type": "technical-proposal",
            "signal": "plan",
            "matched": "no",
            "evidence_refs": [],
            "note": "同上：plan 是战役节点编号，不是提案"
          }
        ]
      },
      "topics": {
        "disciplines": [
          "冰区航行",
          "阻力"
        ],
        "domain": "ice-hydrodynamics / LBM-DEM 相间动量交换（拖曳力系数闭合标定与证据判级）",
        "scenario_key": "ice_drag_cd_reissue",
        "keywords": [
          "拖曳力系数",
          "冰区",
          "标准阻力曲线",
          "Schiller-Naumann",
          "Morrison",
          "Stokes",
          "WITHHELD",
          "SAME_SOURCE_COPY",
          "evidence_grade",
          "Cd(Re)"
        ],
        "keywords_verified_verbatim": true,
        "keyword_absent": []
      },
      "structure": {
        "headings": 10,
        "sections": [
          {
            "level": 1,
            "title": "补报：冰-水拖曳力系数标定（plan 1 / node 18 / mission 683）",
            "start_offset": 0,
            "start_line": 1,
            "end_offset": 360
          },
          {
            "level": 2,
            "title": "① 案例介绍",
            "start_offset": 360,
            "start_line": 10,
            "end_offset": 1018
          },
          {
            "level": 2,
            "title": "② 方法/流程",
            "start_offset": 1018,
            "start_line": 30,
            "end_offset": 2074
          },
          {
            "level": 2,
            "title": "③ 计算结果",
            "start_offset": 2074,
            "start_line": 50,
            "end_offset": 2085
          },
          {
            "level": 3,
            "title": "3.1 机器判级（关键结论）",
            "start_offset": 2085,
            "start_line": 52,
            "end_offset": 2694
          },
          {
            "level": 3,
            "title": "3.2 独立基准 Cd(Re)",
            "start_offset": 2694,
            "start_line": 68,
            "end_offset": 3998
          },
          {
            "level": 2,
            "title": "④ 结果图",
            "start_offset": 3998,
            "start_line": 101,
            "end_offset": 4682
          },
          {
            "level": 2,
            "title": "⑤ 注意点（坑 / 局限 / 适用范围）",
            "start_offset": 4682,
            "start_line": 112,
            "end_offset": 5954
          },
          {
            "level": 2,
            "title": "⑥ 误差判定（逐项，显式回答是否 <3%）",
            "start_offset": 5954,
            "start_line": 135,
            "end_offset": 6737
          },
          {
            "level": 2,
            "title": "产物与复现",
            "start_offset": 6737,
            "start_line": 154,
            "end_offset": 7241
          }
        ],
        "tables": 5,
        "fenced_code_blocks": 1,
        "ordered_list_gaps": [
          {
            "section": "⑤ 注意点（坑 / 局限 / 适用范围）",
            "observed": [
              1,
              2,
              3,
              4,
              5,
              6,
              8,
              9
            ],
            "missing": [
              7
            ]
          }
        ],
        "anomalies": [
          {
            "code": "ORDERED_LIST_SEQUENCE_GAP",
            "detail": "⑤ 注意点（坑 / 局限 / 适用范围） 观测序号 [1, 2, 3, 4, 5, 6, 8, 9]，缺 [7]",
            "evidence_refs": [
              "E12"
            ]
          }
        ]
      },
      "skill": {
        "skill_id": "xsk-experimental-validation",
        "skill_version": "0.1.0",
        "registry_version": "1.0",
        "registry_path": "extraction-skills/registry.json",
        "selection_basis": "按 decision_rule 选中的 primary report_type 对应 skill（一类型一 skill）",
        "section_match": [
          "① 案例介绍",
          "② 方法/流程",
          "③ 计算结果",
          "④ 结果图",
          "⑤ 注意点（坑 / 局限 / 适用范围）",
          "⑥ 误差判定（逐项，显式回答是否 <3%）",
          "产物与复现"
        ],
        "lifecycle_state": "template-created",
        "method_note": "该 skill 目前是 template-created（registry 自述无代表性报告通过全线），故 skill 选择是“按类型的最小可行绑定”，不是已晋升技能。"
      },
      "evidence": [
        {
          "id": "E01",
          "purpose": "报告自述性质，决定 subtype 判定",
          "supports": [
            "subtype:evidence-audit"
          ],
          "note": "anchor 扩展为整行（逐字）",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 220,
            "end_offset": 264,
            "start_line": 6,
            "end_line": 6,
            "quote": "- 本报告性质：**证据链重建 + 重新判级**。原始工作树已被回收，原始工件在全盘（含",
            "content_hash": "sha256:61417f4eb498f92fbb77adcdf5eb48bbb80f4f805f946943a56e2b3fd9b4414e",
            "char_offsets_basis": "python-str-codepoint-index"
          }
        },
        {
          "id": "E02",
          "purpose": "闭合族 vs 实验标准阻力曲线的逐 Re 误差行（baseline comparison / validation case）",
          "supports": [
            "experimental-validation"
          ],
          "note": "anchor 扩展为整行（逐字）",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 6110,
            "end_offset": 6168,
            "start_line": 140,
            "end_line": 140,
            "quote": "| SN 闭合 Cd(Re)，Re∈[1,800] | 实验标准阻力曲线 | 最大 7.18 % | **否** |",
            "content_hash": "sha256:aaf24d572d6e175b8410d0eb3eded20562e821198146955378c6ef186ea2d991",
            "char_offsets_basis": "python-str-codepoint-index"
          }
        },
        {
          "id": "E03",
          "purpose": "独立基准的文献出处声明",
          "supports": [
            "experimental-validation"
          ],
          "note": "anchor 扩展为整行（逐字）",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 780,
            "end_offset": 891,
            "start_line": 26,
            "end_line": 26,
            "quote": "| 参考数据（本报告独立基准） | Clift, Grace & Weber (1978) standard drag curve (Lapple-Shepherd tabulation), smooth sphere |",
            "content_hash": "sha256:b99ddd7530682485e107c1c1be5f192aaf9426813ce7cdcf1e6e0f79bba868ae",
            "char_offsets_basis": "python-str-codepoint-index"
          }
        },
        {
          "id": "E04",
          "purpose": "参考数据分辨率/散布讨论（measurement uncertainty 的结构类比）",
          "supports": [
            "experimental-validation"
          ],
          "note": "anchor 扩展为整行（逐字）",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 5063,
            "end_offset": 5110,
            "start_line": 121,
            "end_line": 121,
            "quote": "3. **参考数据的精度天花板**：实验标准阻力曲线表格本身有 ~1–2% 的取整/数据散布，",
            "content_hash": "sha256:5735ea6d60f1e443ef066bdd38964e0adb8ed5a5b9ba3b3276b2b4086c98644d",
            "char_offsets_basis": "python-str-codepoint-index"
          }
        },
        {
          "id": "E05",
          "purpose": "适用域限定：报告以“验证有效性范围”为组织线索",
          "supports": [
            "experimental-validation",
            "scientific-computation"
          ],
          "note": "anchor 扩展为整行（逐字）",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 5175,
            "end_offset": 5237,
            "start_line": 124,
            "end_line": 124,
            "quote": "4. **适用范围**：Schiller-Naumann 仅 Re ≲ 800 有效；声明的 `Re∈[1,1e5]` 覆盖",
            "content_hash": "sha256:333a23a60f2ef1134cfb3addde39a12fe2f13246fc1021fc8ec943e36322087d",
            "char_offsets_basis": "python-str-codepoint-index"
          }
        },
        {
          "id": "E06",
          "purpose": "机器判级表首行：报告核心是判级器的判定，不是作者结论",
          "supports": [
            "subtype:evidence-audit"
          ],
          "note": "anchor 扩展为整行（逐字）",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 2168,
            "end_offset": 2251,
            "start_line": 56,
            "end_line": 56,
            "quote": "| A. as_reported（记录证据结构） | **WITHHELD** | `R10_INDEPENDENCE` | `SAME_SOURCE_COPY` |",
            "content_hash": "sha256:9e41cc5c710b24b8241d6eaa5f8ac41d2ef9fcbaaa2d3d66bda299e57e9ccf72",
            "char_offsets_basis": "python-str-codepoint-index"
          }
        },
        {
          "id": "E07",
          "purpose": "重新判级结论段：报告主产出是撤销原单 REAL 判定",
          "supports": [
            "subtype:evidence-audit"
          ],
          "note": "anchor 扩展为整行（逐字）",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 6405,
            "end_offset": 6461,
            "start_line": 146,
            "end_line": 146,
            "quote": "**结论（honest）**：node 18 的 `done` 状态**不由其记录的证据支撑**——唯一记录到的",
            "content_hash": "sha256:cd70a7e61854bf93876775d5d72666d82428803d3684880fb78f569815bbddcf",
            "char_offsets_basis": "python-str-codepoint-index"
          }
        },
        {
          "id": "E08",
          "purpose": "变更/工件取证手段（changed files / commit 类信号）",
          "supports": [
            "software-engineering"
          ],
          "note": "anchor 扩展为整行（逐字）",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 1465,
            "end_offset": 1544,
            "start_line": 38,
            "end_line": 38,
            "quote": "   `/root/TensorLBM_test_waic`）执行 `git log --all --name-status -- '*ice_drag*'`",
            "content_hash": "sha256:bb765582d3890327ec45874cbba9e9a742ef133434802d2b775f89b72c825882",
            "char_offsets_basis": "python-str-codepoint-index"
          }
        },
        {
          "id": "E09",
          "purpose": "原单测试判据被引用为验收项（regression 类信号，本报告未复跑）",
          "supports": [
            "software-engineering"
          ],
          "note": "anchor 扩展为整行（逐字）",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 568,
            "end_offset": 643,
            "start_line": 16,
            "end_line": 16,
            "quote": "`pytest_test_drag_coefficient == PASS`。原结果记录 `Cd_error_vs_ITTC = 0.000000`、",
            "content_hash": "sha256:b90493eed58786407fed924761424dfa66668066c95f0f466c81d46137555a40",
            "char_offsets_basis": "python-str-codepoint-index"
          }
        },
        {
          "id": "E10",
          "purpose": "一键复现命令，工程性产物线索",
          "supports": [
            "software-engineering"
          ],
          "note": "anchor 扩展为整行（逐字）",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 7187,
            "end_offset": 7240,
            "start_line": 163,
            "end_line": 163,
            "quote": "复现：`python3 runs/m8102/ice_drag_cd/node18_reissue.py`",
            "content_hash": "sha256:2ef66a2055a9a884cd0328ae6ee8fb4d19f96eca82704c41ebfd300597d20546",
            "char_offsets_basis": "python-str-codepoint-index"
          }
        },
        {
          "id": "E11",
          "purpose": "闭合族数学式（无控制方程推导/离散/收敛研究）",
          "supports": [
            "scientific-computation"
          ],
          "note": "anchor 扩展为整行（逐字）",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 938,
            "end_offset": 1016,
            "start_line": 28,
            "end_line": 28,
            "quote": "| 闭合族 | Schiller-Naumann `24/Re(1+0.15Re^0.687)`；Morrison (2013)；Newton 0.44 |",
            "content_hash": "sha256:cedf866686897717640b150d3e96989272e26b3626bc60ba5b142c38288a5f57",
            "char_offsets_basis": "python-str-codepoint-index"
          }
        },
        {
          "id": "E12",
          "purpose": "⑤ 编号从 6 直接跳到 8，缺 7（结构异常）",
          "supports": [
            "structure:anomaly"
          ],
          "note": "anchor 扩展为整行（逐字）",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 5577,
            "end_offset": 5870,
            "start_line": 131,
            "end_line": 131,
            "quote": "8. **与既有补报 report 9349 的关系**：9349（2026-11-09T04:12Z，0 图）以「TensorLBM DEM Schiller-Naumann 模型 vs sphere Re=100 LBM 基准」报 T1/T2 误差 2.77%/2.54%（<3%）。本报告与之不矛盾：Re=100 处 SN 对实验标准阻力曲线的误差为 2.0%，与 2.5–3% 同量级；但 9349 未覆盖 Re>800，本报告指出全 Re 覆盖不成立（79.1% @Re=1e5）。两报合并后的正确结论是「Re≲800 合格、全 Re 覆盖不成立」，而非原单声称的 0 误差。",
            "content_hash": "sha256:7e082ae8cb126ac9a82c9a1625000643e97e1d73b5fb57550b6c2989eef36ce4",
            "char_offsets_basis": "python-str-codepoint-index"
          }
        },
        {
          "id": "E13",
          "purpose": "工件灭失的诚实声明，决定本报告的“审计/re-issue”性质",
          "supports": [
            "subtype:evidence-audit"
          ],
          "note": "anchor 扩展为整行（逐字）",
          "locator": {
            "locator_type": "char_span",
            "start_offset": 1545,
            "end_offset": 1580,
            "start_line": 39,
            "end_line": 39,
            "quote": "   → 零命中。结论：**原始工件不可恢复**（诚实记录，不补造）。",
            "content_hash": "sha256:19d170102c63b64938fc98448d21e0c3ff6aac43c0586d98cf0d90a09f46c03d",
            "char_offsets_basis": "python-str-codepoint-index"
          }
        }
      ],
      "unresolved": [
        {
          "id": "U01",
          "status": "unresolved",
          "question": "本报告是产线五工序中哪一工序的产物，或只是一次 re-issue 补报的落地形态？",
          "why": "报告未自述工序归属；契约 mission_id=null，原文 mission_id=683（补报单 m8102），二者无法互证。"
        }
      ],
      "limitations": [
        "分类是假设：六分型在中文语料下词法信号只覆盖字面词，signal_table 的语义映射由人工给出，可用 evidence 反驳。",
        "registry 无“审计/重新判级”类型，taxonomy_coverage=partial；换一套分型（含 audit）时 primary 可能改动。",
        "本包不抽取、不登记资产：报告提到的原工件/图存在性未由本包核验（属工序 01，register_assets=false）。",
        "本包只分类不改判：报告的 WITHHELD/REAL 判定属于上游内容，本包不背书也不推翻。"
      ],
      "repro": {
        "generator": "scripts/wp_9447_02/classify_9447.py",
        "command": "python3 scripts/wp_9447_02/classify_9447.py --offline",
        "offline_source": "work/wp-9447-02/sources/9447.md",
        "requires_network": false
      },
      "self_check": {
        "valid_json": {
          "result": "pass",
          "detail": "json.dumps/loads 往返一致（ensure_ascii=False）"
        },
        "source_hash_matches": {
          "result": "pass",
          "detail": "declared=sha256:a0be8122d188c0507610e1533ddb4ccbfb38f678d557ff23fe8710d52139c666 computed=sha256:a0be8122d188c0507610e1533ddb4ccbfb38f678d557ff23fe8710d52139c666 chars=7241（契约声明 7241）"
        },
        "source_locator_resolvable": {
          "result": "pass",
          "detail": "13/13 locator 经 ke.wp_gate.locator_matches 逐字节解析通过"
        },
        "no_duplicate_ids": {
          "result": "pass",
          "detail": "ids=['E01', 'E02', 'E03', 'E04', 'E05', 'E06', 'E07', 'E08', 'E09', 'E10', 'E11', 'E12', 'E13']"
        },
        "all_claims_have_evidence_or_explicit_unresolved_status": {
          "result": "vacuous-pass",
          "detail": "本工序不做抽取：claims 恒为空数组（schema maxItems=0），“每条 claim 都有证据”为空真；未抽取不等于已核实"
        },
        "schema_pass": {
          "result": "pass",
          "detail": "jsonschema Draft2020-12 对 classification.v1.schema.json 校验通过"
        }
      }
    }
  }
}
```
