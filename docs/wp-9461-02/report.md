# KF-RESULT wp-9461-02

**工序**：02-classification-parse（报告→知识产线 KBM-RCI-F1-FACTORY）
**源报告**：report_id `9461` · EEOI 与 CII 营运指标闭环验证（节点 p48w3-n09-eeoi-cii · m8189）
**source_hash**：`sha256:c839141234f9b547f153399b3e09784457d55832f3449d16c7b5b21a278a92b1`（本地重算与契约声明一致：✓）
**场景**：`green-navigation.eeoi_cii` · 语言 `zh` · 字数 10571
**判定报告类型**：`experimental-validation`（实验验证） · 选中 skill `xsk-experimental-validation` v0.1.0（template-created）

---

## ① 本工序做了什么

只做一件事：给 report 9461 打**类型/主题标签 + 结构切分**，并给出每个判定的原文逐字定位。
契约 `objective.classify_report_type=true`、`objective.register_assets=false`，notes 明确"不做抽取"，
因此本包**不产生 claims/evidence/provenance 抽取文件**，也**不给任何结论标 verified**
（verification 由平台门计算）。工序边界按 input.report_id 字面量钉死为 `9461`，未读写任何其它 report_id。

产出三个判定层：

1. **报告类型**（registry 六分型之一）+ 两个备选与被否理由 + 判定规则；
2. **主题标签** 7 条（domain / scenario / metric / method / evidence-caliber / 学科）；
3. **结构切分** 22 段（heading 层级、字符区间、行区间、段内字数），区间首尾相接覆盖全文 10571 字符。

另附一项**实测的**负面发现：skill registry 的 `identify_signals` 在本报告上完全失效（见 ⑤）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文（不许凭记忆）**：`GET $TENSOR_API_BASE/tensor/reports/9461` → `markdown` 字段，
   落盘 `runs/wp-9461-02/source_9461.md`（10571 字符），并重算 `sha256`。
   契约声明 `source_hash=sha256:c839141234f9b547f153399b3e09784457d55832f3449d16c7b5b21a278a92b1`，本地重算相等；随后又**独立二次取文**再核一次
   （两次取文同哈希、20 个定位器全部在第二次取文中逐字命中）。
2. **登记 registry 信号并如实测量**：把 `extraction-skills/registry.json` 六型的
   `identify_signals` 逐条在正文上计数（大小写不敏感子串；`citation density >= 5 per 1000 chars`
   以 `MEPC.`/`Circ.` 记号密度折算）。结果是**六型全 0 命中**（见 ⑤），
   故信号匹配**没有**被当作判定证据——这一步的作用是证明"它不可用"，而不是装作它可用。
3. **结构切分**：`^(#{1,3}) ` 正则切 heading，每段止于下一个 heading，偏移按 Python `str` 码点计；
   自检断言"段区间首尾相接且覆盖 [0, len)"。
4. **定位器（零手抄的机检落地）**：每个引文片段在原文中**必须恰好出现 1 次**，
   否则构建脚本直接以非零码退出；`start_offset/end_offset` 由 `md.index()` 求得并回切片验证，
   `content_hash` = 该片段 UTF-8 的 sha256。
5. **判定规则（先声明后判定）**：primary = "正文是否同时给出①预声明判据集②逐条对照基线的判定结论"，
   两者齐备才是 `experimental-validation`；备选按 rank 记入 `report_type_alternatives` 并写明被否理由，
   不做"只给一个字母"的黑箱输出。
6. **工具链**：Python 3.11 + `jsonschema`（schema 校验）+ `matplotlib`（仅出图）；
   模块本体零外部依赖。重计算量为"读 10.5k 字符 + 20 次子串定位"，无需提交集群。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/wp-9461-02/KF-RESULT-wp-9461-02.json` | kf_result.v1 交付载荷（`package_id/task_type/report_id/provenance/outputs`），schema 校验通过 |
| `docs/wp-9461-02/classification.json` | `outputs.classification.json` 本体：类型判定 + 7 条主题标签 + 22 段结构切分 + 12 条判定断言（含 20 个可解析定位器）+ registry 信号实测 |
| `docs/wp-9461-02/report.md` | 本报告（六段 + 唯一 json 块） |
| `runs/wp-9461-02/source_9461.md` | 平台 `markdown` 原文快照（哈希可核） |
| `runs/wp-9461-02/checks.json` | 6 项 acceptance 自检结果（逐项 ok/失败明细） |
| `runs/wp-9461-02/fig1_structure_segmentation.png` | 结构切分图（段内字符数条形，程序生成） |
| `scripts/kf_wp9461_02_classify.py` | 构建 + 自检一键脚本 |
| `scripts/kf_wp9461_02_publish.py` | 报告组装 + 递交脚本 |

**一键复跑**（工作树根执行）：

    cd <worktree-root>
    python3 scripts/kf_wp9461_02_classify.py --check
    python3 scripts/kf_wp9461_02_publish.py

（若本地无原文快照：先取 `GET $TENSOR_API_BASE/tensor/reports/9461`，把返回 JSON 的 `markdown`
字段写入 `runs/wp-9461-02/source_9461.md`，脚本会先校验哈希再继续。）

## ④ 证据定位表（claim/字段 → 原文引文片段）

偏移为源 markdown 的码点区间；`content_hash` 为引文片段 UTF-8 sha256 前 12 位（全值在 JSON 内）。

| locator | 行 | 区间 | hash | 原文引文片段（逐字） |
|---|---|---|---|---|
| e01 | L3 | chars[54:109) | 7c895a79b812… | **被测模块**：`backend/modules/green_navigation/eeoi_cii.py` |
| e03 | L88 | chars[3048:3075) | 930bc376df48… | 判据在**看结果前**已按战役 metadata 固定 |
| e04 | L89 | chars[3106:3138) | e54e323677eb… | A3 EEOI 偏差 < 15%；A4 评级与 IMO 阈值一致 |
| e05 | L236 | chars[8066:8143) | d7cf75b2f1cd… | \| A2 燃料消耗偏差 \| 数值链 vs 闭式解 F=SFOC·P·T \| 0.000e+00（+0.0000%） \| < 1% |
| e02 | L5 | chars[197:243) | 7ac60830633a… | **测试**：`tests/test_eeoi_cii_m8189.py`（24 项，全绿） |
| e17 | L61 | chars[1731:1769) | cc7903b5f479… | \| (a) 能量 \| `trapz(power_kw, time_h)` \| |
| e08 | L275 | chars[9742:9791) | ef86cac15be9… | 非整周期工况 `P(t)=20000+4000·sin(2πt/37h) kW, T=240h`： |
| e09 | L285 | chars[10081:10119) | 5181d69f8b37… | \| 321 \| 0.75 \| 4846961.4 \| 1.312e-05 \| |
| e12 | L17 | chars[476:509) | df32414c0301… | **CII/AER**（碳强度指标，MEPC.353(78) G1 |
| e14 | L79 | chars[2715:2731) | 58ccad0e5acf… | ### 2.2 工具链与可复现性 |
| e18 | L49 | chars[1533:1560) | eabc636e2c52… | 几何先验校验（平台纪律：先验 Cb/L/B 再算性能） |
| e10 | L6 | chars[244:268) | 78b4832d36cb… | **证据分级**：物理链 `REAL`；规则系数 |
| e11 | L77 | chars[2646:2680) | 9f6910358694… | `required_evidence_grade=WITHHELD` |
| e07 | L249 | chars[8766:8777) | f45a1b6ba415… | 偏离 +21.23%， |
| e06 | L250 | chars[8780:8793) | d2a095d54084… | **> 3%（不满足）** |
| e15 | L224 | chars[7793:7821) | 6574968638fd… | IMO GHG Study 4 (2020) 基准未取得 |
| e16 | L267 | chars[9482:9527) | 233998ad2cd8… | `_gn_cii_rating_status()` 仍返回 `NOT_SUPPORTED` |
| e13 | L131 | chars[4255:4289) | 39aa459642a2… | ### 3.3 年度 CII 与 A–E 评级（6 个往返航次/年） |

判定断言与定位器绑定：

| 断言 | 面 | 状态 | 定位器 | 首个定位值 |
|---|---|---|---|---|
| c01 | report_type.primary | supported | e01, e03, e04, e05 | chars[54:109) line 3 |
| c02 | report_type.secondary | supported | e01, e02, e17 | chars[54:109) line 3 |
| c03 | report_type.tertiary | supported | e08, e09 | chars[9742:9791) line 275 |
| c04 | not_literature_review | supported | e12 | chars[476:509) line 17 |
| c05 | not_technical_proposal | supported | e14 | chars[2715:2731) line 79 |
| c06 | scenario_key | supported | e12, e18 | chars[476:509) line 17 |
| c07 | evidence_grading_in_source | supported | e10, e11 | chars[244:268) line 6 |
| c08 | known_limitation:external_baseline | supported | e07, e06 | chars[8766:8777) line 249 |
| c09 | known_limitation:external_benchmark_missing | supported | e15 | chars[7793:7821) line 224 |
| c10 | known_limitation:in_repo_api_disagreement | supported | e16 | chars[9482:9527) line 267 |
| c11 | structure:rating_table | supported | e13 | chars[4255:4289) line 131 |
| c12 | uncertainty:registry_signal_blindness | unresolved | — | no locator (unresolved) |

结构切分（22 段，首尾相接覆盖全文）：

| 段 | 层级 | heading | 字数 | 偏移 |
|---|---|---|---|---|
| s01 | 1 | EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeo | 367 | 0–367 |
| s02 | 2 | 1 案例介绍 | 11 | 367–378 |
| s03 | 3 | 1.1 物理背景 | 619 | 378–997 |
| s04 | 3 | 1.2 几何与设计点（KVLCC2） | 666 | 997–1663 |
| s05 | 2 | 2 怎么做的 | 11 | 1663–1674 |
| s06 | 3 | 2.1 方法链（全部纯函数、可标量复算） | 1041 | 1674–2715 |
| s07 | 3 | 2.2 工具链与可复现性 | 312 | 2715–3027 |
| s08 | 3 | 2.3 实验设计（预声明判据） | 351 | 3027–3378 |
| s09 | 2 | 3 计算结果 | 11 | 3378–3389 |
| s10 | 3 | 3.1 航次闭环（满载基准航次） | 438 | 3389–3827 |
| s11 | 3 | 3.2 往返航次（含压载段，EEOI 的唯一完整口径） | 428 | 3827–4255 |
| s12 | 3 | 3.3 年度 CII 与 A–E 评级（6 个往返航次/年） | 707 | 4255–4962 |
| s13 | 3 | 3.4 评级边界逐点校核（ratios 由 required 反推） | 610 | 4962–5572 |
| s14 | 3 | 3.5 航速灵敏度（定进距律 P ∝ V^k） | 726 | 5572–6298 |
| s15 | 3 | 3.6 图 | 557 | 6298–6855 |
| s16 | 2 | 4 注意点（踩过的坑与局限） | 1033 | 6855–7888 |
| s17 | 2 | 5 误差判定 | 11 | 7888–7899 |
| s18 | 3 | 5.1 判据逐项 | 608 | 7899–8507 |
| s19 | 3 | 5.2 是否 < 3%？（逐项显式回答） | 508 | 8507–9015 |
| s20 | 3 | 5.3 honest 声明（未完成/不可验证部分） | 700 | 9015–9715 |
| s21 | 3 | 5.4 数值积分收敛表（对照，含混叠陷阱） | 500 | 9715–10215 |
| s22 | 2 | 6 结论 | 356 | 10215–10571 |

## ⑤ 注意点与局限

1. **类型判定是可反驳假设，不是验证**：`experimental-validation` 为 primary（置信 high），
   `algorithm-implementation`（rank 2，high）与 `scientific-computation`（rank 3，medium）作为备选保留。
   若下游 03 抽取发现正文以"算法规格/复杂度"为主，应回改 primary —— 本包把证据摊开就是为了让它可被推翻。
2. **registry 信号对中文报告盲**（实测，非推测）：六型 cardinal signal 命中数全 0，
   `software-engineering` 仅命中 incidental 的 `API`×2，`literature-review` 的引用密度 2.18 < 5.0 阈值。
   故本包**没有**用信号匹配做判定，`registry_signal_probe` 只作诊断留证。
   这是产线级缺陷（信号是英文模板）→ 记为 assertion `c12` 状态 `unresolved`，修 registry 属别的工作包。
3. **不做抽取**：`claims` 为空数组并写明理由；`asset_manifest`/`claims`/`evidence`/`provenance` 抽取文件
   一律不产出，`outputs` 只有 `classification.json`。空 claims 不等于"报告无价值"，
   而是"抽取值工序 03"。
4. **不越权定性**：源报告自己的证据分级（物理链 `REAL`、规则系数 `WITHHELD`）**原样保留**，
   本包不重判、不升级为 verified。
5. **源报告自曝的外部精度缺口照抄进分类面**：与 MEPC.353(78) 2019 油轮参考线偏离 +21.23%
   （源明写 **> 3%（不满足）**、口径 WITHHELD）；IMO GHG Study 4 (2020) 逐船基准未取得。
   故主题标签打 `validation:internal-closed-form-only`，防止下游把"与闭式解机器零偏差"读成"外部已对标"。
6. **偏移口径为码点非字节**：定位器按 Python `str` 计数；若下游按 UTF-8 字节切分，需自行转换。
   已用"切片回读 == 引文"与 `content_hash` 双保险，避免口径歧义导致假失败。
7. **无机器可读附录**：源报告只有 pipe 表，无 fenced JSON/CSV 块（`machine_readable_appendix_present=false`），
   下游若需结构化结果必须从表格解析，解析质量由工序 03/04 承担。

## ⑥ 自检：逐条对照 acceptance

| acceptance | 结果 | 证据 |
|---|---|---|
| valid_json | ✓ | `json.loads` 回读通过，46953 字节载荷 |
| schema_pass | ✓ | `jsonschema` 按 `schemas/kf_result.v1.schema.json` 校验通过（additionalProperties=false 亦通过） |
| source_locator_resolvable | ✓ | 32 个定位器：切片回读==引文、逐字在文中、content_hash 相符，失败 0 |
| source_hash_matches | ✓ | 本地重算 `sha256:c839141234f9b547f153399b3e09784457d55832f3449d16c7b5b21a278a92b1` == 契约声明 |
| no_duplicate_ids | ✓ | 断言 12 条、段 22 段，重复 0 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✓ | claims=[] （不做抽取，理由写入 `claims_note`）+ 11/12 断言带定位器，1 条显式 `unresolved`（c12，附理由） |

附加自检（契约外，防结构漂移）：`section_offsets_tile_source` ✓
—— 22 段区间首尾相接且覆盖 `[0, 10571)`。

**诚实声明（honest-FAIL 不粉饰）**：以上 6 项 acceptance 全绿，但这只覆盖"分类产物自身的一致性"。
**本工序没有、也不可能**证明报告结论的真实性：
源报告对外部基准的偏离 +21.23%（> 3%）与 GHG Study 4 基准缺失，仍如实登记为 WITHHELD，
不会因本包 acceptance 全绿而改善。`registry_signal_probe` 的六型全 0 命中同样如实留证，
未做任何"信号凑命中"的粉饰。

## 图

![fig1_structure_segmentation](fig1_structure_segmentation.png)

*图 1 报告 9461 的结构切分：22 段，段内字符数；偏移区间首尾相接覆盖全文
10571 字符（程序由 `classification.json.structure` 直接渲染）*

## registry 信号实测（诊断留证）

| report_type | 命中/信号数 | 逐条测量 |
|---|---|---|
| literature-review | 0/5 | related work=0; state of the art=0; survey=0; bibliography=0; citation density >= 5 per 1000 chars=2.18 |
| scientific-computation | 0/5 | governing equations=0; discretisation=0; convergence study=0; mesh refinement=0; timing table=0 |
| algorithm-implementation | 0/5 | pseudocode=0; complexity=0; algorithm block=0; function signature=0; O(n=0 |
| software-engineering | 1/5 | changed files=0; commit=0; interface=0; regression=0; API=2 |
| technical-proposal | 0/5 | proposal=0; design=0; roadmap=0; specification=0; plan=0 |
| experimental-validation | 0/5 | test matrix=0; facility=0; measurement uncertainty=0; validation case=0; baseline comparison=0 |

---

## 结果载荷（本报告唯一的 json 代码块；与 `docs/wp-9461-02/KF-RESULT-wp-9461-02.json` 逐字节一致）

```json
{
  "package_id": "wp-9461-02",
  "task_type": "02-classification-parse",
  "contract_version": "1.0",
  "report_id": "9461",
  "provenance": {
    "source_uri": "tensor://reports/9461",
    "source_field": "markdown",
    "source_hash": "sha256:c839141234f9b547f153399b3e09784457d55832f3449d16c7b5b21a278a92b1",
    "source_hash_matches": true,
    "title": "EEOI 与 CII 营运指标闭环验证（节点 p48w3-n09-eeoi-cii · m8189）",
    "scenario_key": "green-navigation.eeoi_cii",
    "chars": 10571
  },
  "outputs": {
    "classification.json": {
      "schema": "kf-classification/v1",
      "package_id": "wp-9461-02",
      "task_type": "02-classification-parse",
      "report_id": "9461",
      "report_type": "experimental-validation",
      "report_type_label_zh": "实验验证",
      "report_type_alternatives": [
        {
          "report_type": "algorithm-implementation",
          "rank": 2,
          "confidence": "high",
          "rejected_because": "the report validates rather than specifies an algorithm; no pseudocode/complexity analysis",
          "evidence": [
            {
              "locator_id": "e01",
              "locator_type": "char_offset",
              "value": "chars[54:109) line 3",
              "start_offset": 54,
              "end_offset": 109,
              "line": 3,
              "quote": "**被测模块**：`backend/modules/green_navigation/eeoi_cii.py`",
              "content_hash": "sha256:7c895a79b812239007e9591c066d6d68737e1a601d95ae4af1c20564d2aaa67c"
            },
            {
              "locator_id": "e02",
              "locator_type": "char_offset",
              "value": "chars[197:243) line 5",
              "start_offset": 197,
              "end_offset": 243,
              "line": 5,
              "quote": "**测试**：`tests/test_eeoi_cii_m8189.py`（24 项，全绿）",
              "content_hash": "sha256:7ac60830633aa73ec657277a0b654f591717dbd588a8dde29db534b0a7c38ea3"
            }
          ]
        },
        {
          "report_type": "scientific-computation",
          "rank": 3,
          "confidence": "medium",
          "rejected_because": "numerics are used as a check on a closed-form chain, not as the subject",
          "evidence": [
            {
              "locator_id": "e08",
              "locator_type": "char_offset",
              "value": "chars[9742:9791) line 275",
              "start_offset": 9742,
              "end_offset": 9791,
              "line": 275,
              "quote": "非整周期工况 `P(t)=20000+4000·sin(2πt/37h) kW, T=240h`：",
              "content_hash": "sha256:ef86cac15be9770241f0b8369b515637730598228f02cccbc564db5e8ac355c2"
            }
          ]
        }
      ],
      "report_type_decision_rule": {
        "primary": "argmax over (does the body state a pre-declared criterion set + per-criterion verdicts against a baseline?) — experimental-validation requires both; both present.",
        "registry_signal_match_used_as_evidence": false,
        "why_not": "all six registry types match 0 cardinal signals on this Chinese report (see registry_signal_probe); classification therefore rests on structural evidence."
      },
      "selected_skill_id": "xsk-experimental-validation",
      "selected_skill_version": "0.1.0",
      "selected_skill_lifecycle_state": "template-created",
      "language": "zh",
      "scenario_key": "green-navigation.eeoi_cii",
      "topic_labels": [
        {
          "tag": "green-navigation",
          "facet": "domain",
          "basis": [
            {
              "locator_id": "e12",
              "locator_type": "char_offset",
              "value": "chars[476:509) line 17",
              "start_offset": 476,
              "end_offset": 509,
              "line": 17,
              "quote": "**CII/AER**（碳强度指标，MEPC.353(78) G1",
              "content_hash": "sha256:df32414c0301e96cd5cf15794b56e5b455c26ae877a4e8ac408c9a7ff513027d"
            }
          ]
        },
        {
          "tag": "green-navigation.eeoi_cii",
          "facet": "scenario",
          "basis": [
            {
              "locator_id": "e12",
              "locator_type": "char_offset",
              "value": "chars[476:509) line 17",
              "start_offset": 476,
              "end_offset": 509,
              "line": 17,
              "quote": "**CII/AER**（碳强度指标，MEPC.353(78) G1",
              "content_hash": "sha256:df32414c0301e96cd5cf15794b56e5b455c26ae877a4e8ac408c9a7ff513027d"
            },
            {
              "locator_id": "e11",
              "locator_type": "char_offset",
              "value": "chars[2646:2680) line 77",
              "start_offset": 2646,
              "end_offset": 2680,
              "line": 77,
              "quote": "`required_evidence_grade=WITHHELD`",
              "content_hash": "sha256:9f6910358694b938130d1daf8b8e17acfdf3214e38ad3ee5dd755d5d6941c7d4"
            }
          ]
        },
        {
          "tag": "metric:EEOI",
          "facet": "metric",
          "basis": [
            {
              "locator_id": "e17",
              "locator_type": "char_offset",
              "value": "chars[1731:1769) line 61",
              "start_offset": 1731,
              "end_offset": 1769,
              "line": 61,
              "quote": "| (a) 能量 | `trapz(power_kw, time_h)` |",
              "content_hash": "sha256:cc7903b5f479813e15290be78e074b313903861741111c548a16d1886ec2fa9f"
            }
          ]
        },
        {
          "tag": "metric:CII-AER",
          "facet": "metric",
          "basis": [
            {
              "locator_id": "e12",
              "locator_type": "char_offset",
              "value": "chars[476:509) line 17",
              "start_offset": 476,
              "end_offset": 509,
              "line": 17,
              "quote": "**CII/AER**（碳强度指标，MEPC.353(78) G1",
              "content_hash": "sha256:df32414c0301e96cd5cf15794b56e5b455c26ae877a4e8ac408c9a7ff513027d"
            },
            {
              "locator_id": "e13",
              "locator_type": "char_offset",
              "value": "chars[4255:4289) line 131",
              "start_offset": 4255,
              "end_offset": 4289,
              "line": 131,
              "quote": "### 3.3 年度 CII 与 A–E 评级（6 个往返航次/年）",
              "content_hash": "sha256:39aa459642a2c6651b6bd890e15db7bd8e8a756b16a658322e8dc833c31ec88f"
            }
          ]
        },
        {
          "tag": "method:numerical-integration",
          "facet": "method",
          "basis": [
            {
              "locator_id": "e08",
              "locator_type": "char_offset",
              "value": "chars[9742:9791) line 275",
              "start_offset": 9742,
              "end_offset": 9791,
              "line": 275,
              "quote": "非整周期工况 `P(t)=20000+4000·sin(2πt/37h) kW, T=240h`：",
              "content_hash": "sha256:ef86cac15be9770241f0b8369b515637730598228f02cccbc564db5e8ac355c2"
            },
            {
              "locator_id": "e09",
              "locator_type": "char_offset",
              "value": "chars[10081:10119) line 285",
              "start_offset": 10081,
              "end_offset": 10119,
              "line": 285,
              "quote": "| 321 | 0.75 | 4846961.4 | 1.312e-05 |",
              "content_hash": "sha256:5181d69f8b37cbc29efb02825e531d2b69c8aaad69daa631de4573033b61e316"
            }
          ]
        },
        {
          "tag": "validation:internal-closed-form-only",
          "facet": "evidence-caliber",
          "basis": [
            {
              "locator_id": "e05",
              "locator_type": "char_offset",
              "value": "chars[8066:8143) line 236",
              "start_offset": 8066,
              "end_offset": 8143,
              "line": 236,
              "quote": "| A2 燃料消耗偏差 | 数值链 vs 闭式解 F=SFOC·P·T | 0.000e+00（+0.0000%） | < 1% | **PASS** |",
              "content_hash": "sha256:d7cf75b2f1cdaefe2d14ba0369c7c0bc0e6c11eb2b2d590d4d63bda82438f24e"
            },
            {
              "locator_id": "e15",
              "locator_type": "char_offset",
              "value": "chars[7793:7821) line 224",
              "start_offset": 7793,
              "end_offset": 7821,
              "line": 224,
              "quote": "IMO GHG Study 4 (2020) 基准未取得",
              "content_hash": "sha256:6574968638fdfa04292677828098eef02dbfa2daafbff54294d9ee1b7a6fcda5"
            },
            {
              "locator_id": "e06",
              "locator_type": "char_offset",
              "value": "chars[8780:8793) line 250",
              "start_offset": 8780,
              "end_offset": 8793,
              "line": 250,
              "quote": "**> 3%（不满足）**",
              "content_hash": "sha256:d2a095d54084363c66af892ee1e8759977eeb6efc26bb5e83b91f849e0b4825c"
            }
          ]
        },
        {
          "tag": "discipline:绿色航行",
          "facet": "ship-engineering-discipline",
          "basis": [
            {
              "locator_id": "e12",
              "locator_type": "char_offset",
              "value": "chars[476:509) line 17",
              "start_offset": 476,
              "end_offset": 509,
              "line": 17,
              "quote": "**CII/AER**（碳强度指标，MEPC.353(78) G1",
              "content_hash": "sha256:df32414c0301e96cd5cf15794b56e5b455c26ae877a4e8ac408c9a7ff513027d"
            }
          ]
        }
      ],
      "structure": {
        "segmentation_method": "regex heading split on ^(#{1,3}) to next heading; char offsets over the UTF-8-decoded markdown (Python str offsets, i.e. code points)",
        "total_chars": 10571,
        "section_count": 22,
        "sections": [
          {
            "section_id": "s01",
            "level": 1,
            "heading": "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）"
            ],
            "start_offset": 0,
            "end_offset": 367,
            "chars": 367,
            "start_line": 1,
            "end_line": 11
          },
          {
            "section_id": "s02",
            "level": 2,
            "heading": "1 案例介绍",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍"
            ],
            "start_offset": 367,
            "end_offset": 378,
            "chars": 11,
            "start_line": 11,
            "end_line": 13
          },
          {
            "section_id": "s03",
            "level": 3,
            "heading": "1.1 物理背景",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "1.1 物理背景"
            ],
            "start_offset": 378,
            "end_offset": 997,
            "chars": 619,
            "start_line": 13,
            "end_line": 32
          },
          {
            "section_id": "s04",
            "level": 3,
            "heading": "1.2 几何与设计点（KVLCC2）",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "1.1 物理背景",
              "1.2 几何与设计点（KVLCC2）"
            ],
            "start_offset": 997,
            "end_offset": 1663,
            "chars": 666,
            "start_line": 32,
            "end_line": 55
          },
          {
            "section_id": "s05",
            "level": 2,
            "heading": "2 怎么做的",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "2 怎么做的"
            ],
            "start_offset": 1663,
            "end_offset": 1674,
            "chars": 11,
            "start_line": 55,
            "end_line": 57
          },
          {
            "section_id": "s06",
            "level": 3,
            "heading": "2.1 方法链（全部纯函数、可标量复算）",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "1.1 物理背景",
              "1.2 几何与设计点（KVLCC2）",
              "2 怎么做的",
              "2.1 方法链（全部纯函数、可标量复算）"
            ],
            "start_offset": 1674,
            "end_offset": 2715,
            "chars": 1041,
            "start_line": 57,
            "end_line": 79
          },
          {
            "section_id": "s07",
            "level": 3,
            "heading": "2.2 工具链与可复现性",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "1.1 物理背景",
              "1.2 几何与设计点（KVLCC2）",
              "2 怎么做的",
              "2.1 方法链（全部纯函数、可标量复算）",
              "2.2 工具链与可复现性"
            ],
            "start_offset": 2715,
            "end_offset": 3027,
            "chars": 312,
            "start_line": 79,
            "end_line": 86
          },
          {
            "section_id": "s08",
            "level": 3,
            "heading": "2.3 实验设计（预声明判据）",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "1.1 物理背景",
              "1.2 几何与设计点（KVLCC2）",
              "2 怎么做的",
              "2.1 方法链（全部纯函数、可标量复算）",
              "2.2 工具链与可复现性",
              "2.3 实验设计（预声明判据）"
            ],
            "start_offset": 3027,
            "end_offset": 3378,
            "chars": 351,
            "start_line": 86,
            "end_line": 99
          },
          {
            "section_id": "s09",
            "level": 2,
            "heading": "3 计算结果",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "2 怎么做的",
              "3 计算结果"
            ],
            "start_offset": 3378,
            "end_offset": 3389,
            "chars": 11,
            "start_line": 99,
            "end_line": 101
          },
          {
            "section_id": "s10",
            "level": 3,
            "heading": "3.1 航次闭环（满载基准航次）",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "1.1 物理背景",
              "1.2 几何与设计点（KVLCC2）",
              "2 怎么做的",
              "2.1 方法链（全部纯函数、可标量复算）",
              "2.2 工具链与可复现性",
              "2.3 实验设计（预声明判据）",
              "3 计算结果",
              "3.1 航次闭环（满载基准航次）"
            ],
            "start_offset": 3389,
            "end_offset": 3827,
            "chars": 438,
            "start_line": 101,
            "end_line": 113
          },
          {
            "section_id": "s11",
            "level": 3,
            "heading": "3.2 往返航次（含压载段，EEOI 的唯一完整口径）",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "1.1 物理背景",
              "1.2 几何与设计点（KVLCC2）",
              "2 怎么做的",
              "2.1 方法链（全部纯函数、可标量复算）",
              "2.2 工具链与可复现性",
              "2.3 实验设计（预声明判据）",
              "3 计算结果",
              "3.1 航次闭环（满载基准航次）",
              "3.2 往返航次（含压载段，EEOI 的唯一完整口径）"
            ],
            "start_offset": 3827,
            "end_offset": 4255,
            "chars": 428,
            "start_line": 113,
            "end_line": 131
          },
          {
            "section_id": "s12",
            "level": 3,
            "heading": "3.3 年度 CII 与 A–E 评级（6 个往返航次/年）",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "1.1 物理背景",
              "1.2 几何与设计点（KVLCC2）",
              "2 怎么做的",
              "2.1 方法链（全部纯函数、可标量复算）",
              "2.2 工具链与可复现性",
              "2.3 实验设计（预声明判据）",
              "3 计算结果",
              "3.1 航次闭环（满载基准航次）",
              "3.2 往返航次（含压载段，EEOI 的唯一完整口径）",
              "3.3 年度 CII 与 A–E 评级（6 个往返航次/年）"
            ],
            "start_offset": 4255,
            "end_offset": 4962,
            "chars": 707,
            "start_line": 131,
            "end_line": 146
          },
          {
            "section_id": "s13",
            "level": 3,
            "heading": "3.4 评级边界逐点校核（ratios 由 required 反推）",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "1.1 物理背景",
              "1.2 几何与设计点（KVLCC2）",
              "2 怎么做的",
              "2.1 方法链（全部纯函数、可标量复算）",
              "2.2 工具链与可复现性",
              "2.3 实验设计（预声明判据）",
              "3 计算结果",
              "3.1 航次闭环（满载基准航次）",
              "3.2 往返航次（含压载段，EEOI 的唯一完整口径）",
              "3.3 年度 CII 与 A–E 评级（6 个往返航次/年）",
              "3.4 评级边界逐点校核（ratios 由 required 反推）"
            ],
            "start_offset": 4962,
            "end_offset": 5572,
            "chars": 610,
            "start_line": 146,
            "end_line": 164
          },
          {
            "section_id": "s14",
            "level": 3,
            "heading": "3.5 航速灵敏度（定进距律 P ∝ V^k）",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "1.1 物理背景",
              "1.2 几何与设计点（KVLCC2）",
              "2 怎么做的",
              "2.1 方法链（全部纯函数、可标量复算）",
              "2.2 工具链与可复现性",
              "2.3 实验设计（预声明判据）",
              "3 计算结果",
              "3.1 航次闭环（满载基准航次）",
              "3.2 往返航次（含压载段，EEOI 的唯一完整口径）",
              "3.3 年度 CII 与 A–E 评级（6 个往返航次/年）",
              "3.4 评级边界逐点校核（ratios 由 required 反推）",
              "3.5 航速灵敏度（定进距律 P ∝ V^k）"
            ],
            "start_offset": 5572,
            "end_offset": 6298,
            "chars": 726,
            "start_line": 164,
            "end_line": 184
          },
          {
            "section_id": "s15",
            "level": 3,
            "heading": "3.6 图",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "1.1 物理背景",
              "1.2 几何与设计点（KVLCC2）",
              "2 怎么做的",
              "2.1 方法链（全部纯函数、可标量复算）",
              "2.2 工具链与可复现性",
              "2.3 实验设计（预声明判据）",
              "3 计算结果",
              "3.1 航次闭环（满载基准航次）",
              "3.2 往返航次（含压载段，EEOI 的唯一完整口径）",
              "3.3 年度 CII 与 A–E 评级（6 个往返航次/年）",
              "3.4 评级边界逐点校核（ratios 由 required 反推）",
              "3.5 航速灵敏度（定进距律 P ∝ V^k）",
              "3.6 图"
            ],
            "start_offset": 6298,
            "end_offset": 6855,
            "chars": 557,
            "start_line": 184,
            "end_line": 205
          },
          {
            "section_id": "s16",
            "level": 2,
            "heading": "4 注意点（踩过的坑与局限）",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "2 怎么做的",
              "3 计算结果",
              "4 注意点（踩过的坑与局限）"
            ],
            "start_offset": 6855,
            "end_offset": 7888,
            "chars": 1033,
            "start_line": 205,
            "end_line": 229
          },
          {
            "section_id": "s17",
            "level": 2,
            "heading": "5 误差判定",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "2 怎么做的",
              "3 计算结果",
              "4 注意点（踩过的坑与局限）",
              "5 误差判定"
            ],
            "start_offset": 7888,
            "end_offset": 7899,
            "chars": 11,
            "start_line": 229,
            "end_line": 231
          },
          {
            "section_id": "s18",
            "level": 3,
            "heading": "5.1 判据逐项",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "1.1 物理背景",
              "1.2 几何与设计点（KVLCC2）",
              "2 怎么做的",
              "2.1 方法链（全部纯函数、可标量复算）",
              "2.2 工具链与可复现性",
              "2.3 实验设计（预声明判据）",
              "3 计算结果",
              "3.1 航次闭环（满载基准航次）",
              "3.2 往返航次（含压载段，EEOI 的唯一完整口径）",
              "3.3 年度 CII 与 A–E 评级（6 个往返航次/年）",
              "3.4 评级边界逐点校核（ratios 由 required 反推）",
              "3.5 航速灵敏度（定进距律 P ∝ V^k）",
              "3.6 图",
              "4 注意点（踩过的坑与局限）",
              "5 误差判定",
              "5.1 判据逐项"
            ],
            "start_offset": 7899,
            "end_offset": 8507,
            "chars": 608,
            "start_line": 231,
            "end_line": 243
          },
          {
            "section_id": "s19",
            "level": 3,
            "heading": "5.2 是否 < 3%？（逐项显式回答）",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "1.1 物理背景",
              "1.2 几何与设计点（KVLCC2）",
              "2 怎么做的",
              "2.1 方法链（全部纯函数、可标量复算）",
              "2.2 工具链与可复现性",
              "2.3 实验设计（预声明判据）",
              "3 计算结果",
              "3.1 航次闭环（满载基准航次）",
              "3.2 往返航次（含压载段，EEOI 的唯一完整口径）",
              "3.3 年度 CII 与 A–E 评级（6 个往返航次/年）",
              "3.4 评级边界逐点校核（ratios 由 required 反推）",
              "3.5 航速灵敏度（定进距律 P ∝ V^k）",
              "3.6 图",
              "4 注意点（踩过的坑与局限）",
              "5 误差判定",
              "5.1 判据逐项",
              "5.2 是否 < 3%？（逐项显式回答）"
            ],
            "start_offset": 8507,
            "end_offset": 9015,
            "chars": 508,
            "start_line": 243,
            "end_line": 256
          },
          {
            "section_id": "s20",
            "level": 3,
            "heading": "5.3 honest 声明（未完成/不可验证部分）",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "1.1 物理背景",
              "1.2 几何与设计点（KVLCC2）",
              "2 怎么做的",
              "2.1 方法链（全部纯函数、可标量复算）",
              "2.2 工具链与可复现性",
              "2.3 实验设计（预声明判据）",
              "3 计算结果",
              "3.1 航次闭环（满载基准航次）",
              "3.2 往返航次（含压载段，EEOI 的唯一完整口径）",
              "3.3 年度 CII 与 A–E 评级（6 个往返航次/年）",
              "3.4 评级边界逐点校核（ratios 由 required 反推）",
              "3.5 航速灵敏度（定进距律 P ∝ V^k）",
              "3.6 图",
              "4 注意点（踩过的坑与局限）",
              "5 误差判定",
              "5.1 判据逐项",
              "5.2 是否 < 3%？（逐项显式回答）",
              "5.3 honest 声明（未完成/不可验证部分）"
            ],
            "start_offset": 9015,
            "end_offset": 9715,
            "chars": 700,
            "start_line": 256,
            "end_line": 273
          },
          {
            "section_id": "s21",
            "level": 3,
            "heading": "5.4 数值积分收敛表（对照，含混叠陷阱）",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "1.1 物理背景",
              "1.2 几何与设计点（KVLCC2）",
              "2 怎么做的",
              "2.1 方法链（全部纯函数、可标量复算）",
              "2.2 工具链与可复现性",
              "2.3 实验设计（预声明判据）",
              "3 计算结果",
              "3.1 航次闭环（满载基准航次）",
              "3.2 往返航次（含压载段，EEOI 的唯一完整口径）",
              "3.3 年度 CII 与 A–E 评级（6 个往返航次/年）",
              "3.4 评级边界逐点校核（ratios 由 required 反推）",
              "3.5 航速灵敏度（定进距律 P ∝ V^k）",
              "3.6 图",
              "4 注意点（踩过的坑与局限）",
              "5 误差判定",
              "5.1 判据逐项",
              "5.2 是否 < 3%？（逐项显式回答）",
              "5.3 honest 声明（未完成/不可验证部分）",
              "5.4 数值积分收敛表（对照，含混叠陷阱）"
            ],
            "start_offset": 9715,
            "end_offset": 10215,
            "chars": 500,
            "start_line": 273,
            "end_line": 295
          },
          {
            "section_id": "s22",
            "level": 2,
            "heading": "6 结论",
            "heading_path": [
              "EEOI 与 CII 营运指标闭环验证（m8189 / 节点 p48w3-n09-eeoi-cii）",
              "1 案例介绍",
              "2 怎么做的",
              "3 计算结果",
              "4 注意点（踩过的坑与局限）",
              "5 误差判定",
              "6 结论"
            ],
            "start_offset": 10215,
            "end_offset": 10571,
            "chars": 356,
            "start_line": 295,
            "end_line": 305
          }
        ],
        "machine_readable_appendix_present": false,
        "note": "No fenced machine-readable block in the source; §3 tables are pipe tables only."
      },
      "registry_signal_probe": {
        "registry_version": "1.0",
        "method": "case-insensitive substring count of registry identify_signals in source markdown; 'citation density >= N per 1000 chars' evaluated as MEPC./Circ. token density",
        "per_type": {
          "literature-review": {
            "skill_id": "xsk-literature-review",
            "signals": [
              {
                "signal": "related work",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "state of the art",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "survey",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "bibliography",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "citation density >= 5 per 1000 chars",
                "measured": 2.18,
                "threshold": 5.0,
                "hit": false
              }
            ],
            "matched": 0
          },
          "scientific-computation": {
            "skill_id": "xsk-scientific-computation",
            "signals": [
              {
                "signal": "governing equations",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "discretisation",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "convergence study",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "mesh refinement",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "timing table",
                "measured": 0,
                "threshold": 1,
                "hit": false
              }
            ],
            "matched": 0
          },
          "algorithm-implementation": {
            "skill_id": "xsk-algorithm-implementation",
            "signals": [
              {
                "signal": "pseudocode",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "complexity",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "algorithm block",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "function signature",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "O(n",
                "measured": 0,
                "threshold": 1,
                "hit": false
              }
            ],
            "matched": 0
          },
          "software-engineering": {
            "skill_id": "xsk-software-engineering",
            "signals": [
              {
                "signal": "changed files",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "commit",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "interface",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "regression",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "API",
                "measured": 2,
                "threshold": 1,
                "hit": true
              }
            ],
            "matched": 1
          },
          "technical-proposal": {
            "skill_id": "xsk-technical-proposal",
            "signals": [
              {
                "signal": "proposal",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "design",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "roadmap",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "specification",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "plan",
                "measured": 0,
                "threshold": 1,
                "hit": false
              }
            ],
            "matched": 0
          },
          "experimental-validation": {
            "skill_id": "xsk-experimental-validation",
            "signals": [
              {
                "signal": "test matrix",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "facility",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "measurement uncertainty",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "validation case",
                "measured": 0,
                "threshold": 1,
                "hit": false
              },
              {
                "signal": "baseline comparison",
                "measured": 0,
                "threshold": 1,
                "hit": false
              }
            ],
            "matched": 0
          }
        },
        "conclusion": "All six types match 0 of their cardinal signals on this Chinese-language report; only incidental English tokens appear (software-engineering: 'API' x2; literature-review: citation density 2.18 < 5.0). Registry signal matching is therefore inconclusive here and is NOT used as the deciding evidence."
      },
      "classification_assertions": [
        {
          "assertion_id": "c01",
          "facet": "report_type.primary",
          "assertion": "Report type is experimental-validation: the report validates an existing module against pre-declared acceptance criteria and analytic/external baselines.",
          "confidence": "high",
          "status": "supported",
          "evidence": [
            {
              "locator_id": "e01",
              "locator_type": "char_offset",
              "value": "chars[54:109) line 3",
              "start_offset": 54,
              "end_offset": 109,
              "line": 3,
              "quote": "**被测模块**：`backend/modules/green_navigation/eeoi_cii.py`",
              "content_hash": "sha256:7c895a79b812239007e9591c066d6d68737e1a601d95ae4af1c20564d2aaa67c"
            },
            {
              "locator_id": "e03",
              "locator_type": "char_offset",
              "value": "chars[3048:3075) line 88",
              "start_offset": 3048,
              "end_offset": 3075,
              "line": 88,
              "quote": "判据在**看结果前**已按战役 metadata 固定",
              "content_hash": "sha256:930bc376df4888ee4542e3dbae0a67e1a69a94a39a83ce4371bb2b00e9839d23"
            },
            {
              "locator_id": "e04",
              "locator_type": "char_offset",
              "value": "chars[3106:3138) line 89",
              "start_offset": 3106,
              "end_offset": 3138,
              "line": 89,
              "quote": "A3 EEOI 偏差 < 15%；A4 评级与 IMO 阈值一致",
              "content_hash": "sha256:e54e323677ebd6929a05bd004658d2d0e9cfc54dc599ecce2ac6f4d6ace5ddc7"
            },
            {
              "locator_id": "e05",
              "locator_type": "char_offset",
              "value": "chars[8066:8143) line 236",
              "start_offset": 8066,
              "end_offset": 8143,
              "line": 236,
              "quote": "| A2 燃料消耗偏差 | 数值链 vs 闭式解 F=SFOC·P·T | 0.000e+00（+0.0000%） | < 1% | **PASS** |",
              "content_hash": "sha256:d7cf75b2f1cdaefe2d14ba0369c7c0bc0e6c11eb2b2d590d4d63bda82438f24e"
            }
          ],
          "rationale": "Object under test named (§被测模块), criteria fixed before looking at results, and per-criterion PASS/FAIL with explicit thresholds."
        },
        {
          "assertion_id": "c02",
          "facet": "report_type.secondary",
          "assertion": "Secondary type is algorithm-implementation: the object is a pure-function implementation with a 24-case regression suite quoted by path.",
          "confidence": "high",
          "status": "supported",
          "evidence": [
            {
              "locator_id": "e01",
              "locator_type": "char_offset",
              "value": "chars[54:109) line 3",
              "start_offset": 54,
              "end_offset": 109,
              "line": 3,
              "quote": "**被测模块**：`backend/modules/green_navigation/eeoi_cii.py`",
              "content_hash": "sha256:7c895a79b812239007e9591c066d6d68737e1a601d95ae4af1c20564d2aaa67c"
            },
            {
              "locator_id": "e02",
              "locator_type": "char_offset",
              "value": "chars[197:243) line 5",
              "start_offset": 197,
              "end_offset": 243,
              "line": 5,
              "quote": "**测试**：`tests/test_eeoi_cii_m8189.py`（24 项，全绿）",
              "content_hash": "sha256:7ac60830633aa73ec657277a0b654f591717dbd588a8dde29db534b0a7c38ea3"
            },
            {
              "locator_id": "e17",
              "locator_type": "char_offset",
              "value": "chars[1731:1769) line 61",
              "start_offset": 1731,
              "end_offset": 1769,
              "line": 61,
              "quote": "| (a) 能量 | `trapz(power_kw, time_h)` |",
              "content_hash": "sha256:cc7903b5f479813e15290be78e074b313903861741111c548a16d1886ec2fa9f"
            }
          ],
          "rationale": "Implementation file + test module named; method chain table lists the implemented functions and formulas without pseudocode or complexity analysis, so this stays secondary rather than primary."
        },
        {
          "assertion_id": "c03",
          "facet": "report_type.tertiary",
          "assertion": "Tertiary type is scientific-computation: it contains a numerical-integration convergence table and an aliasing counter-example.",
          "confidence": "medium",
          "status": "supported",
          "evidence": [
            {
              "locator_id": "e08",
              "locator_type": "char_offset",
              "value": "chars[9742:9791) line 275",
              "start_offset": 9742,
              "end_offset": 9791,
              "line": 275,
              "quote": "非整周期工况 `P(t)=20000+4000·sin(2πt/37h) kW, T=240h`：",
              "content_hash": "sha256:ef86cac15be9770241f0b8369b515637730598228f02cccbc564db5e8ac355c2"
            },
            {
              "locator_id": "e09",
              "locator_type": "char_offset",
              "value": "chars[10081:10119) line 285",
              "start_offset": 10081,
              "end_offset": 10119,
              "line": 285,
              "quote": "| 321 | 0.75 | 4846961.4 | 1.312e-05 |",
              "content_hash": "sha256:5181d69f8b37cbc29efb02825e531d2b69c8aaad69daa631de4573033b61e316"
            }
          ],
          "rationale": "Convergence of trapezoidal integration to O(h^2) plus a deliberately aliased case; this supports but does not carry the report, which is why it is tertiary."
        },
        {
          "assertion_id": "c04",
          "facet": "not_literature_review",
          "assertion": "literature-review is rejected: no related-work/state-of-the-art section and no bibliography; IMO documents appear as regulation identifiers, not as reviewed works.",
          "confidence": "high",
          "status": "supported",
          "evidence": [
            {
              "locator_id": "e12",
              "locator_type": "char_offset",
              "value": "chars[476:509) line 17",
              "start_offset": 476,
              "end_offset": 509,
              "line": 17,
              "quote": "**CII/AER**（碳强度指标，MEPC.353(78) G1",
              "content_hash": "sha256:df32414c0301e96cd5cf15794b56e5b455c26ae877a4e8ac408c9a7ff513027d"
            }
          ],
          "rationale": "Registry signals for literature-review measured 0 (except citation density 2.18 < 5.0)."
        },
        {
          "assertion_id": "c05",
          "facet": "not_technical_proposal",
          "assertion": "technical-proposal is rejected: the report contains no roadmap/plan/specification for future work; it reports completed runs.",
          "confidence": "medium",
          "status": "supported",
          "evidence": [
            {
              "locator_id": "e14",
              "locator_type": "char_offset",
              "value": "chars[2715:2731) line 79",
              "start_offset": 2715,
              "end_offset": 2731,
              "line": 79,
              "quote": "### 2.2 工具链与可复现性",
              "content_hash": "sha256:58ccad0e5acf13ac49291acdc2c5c4308124a9b32158b9d5295c4f52f95dd0d5"
            }
          ],
          "rationale": "§2.2 is a reproducibility record of commands already executed, not a plan."
        },
        {
          "assertion_id": "c06",
          "facet": "scenario_key",
          "assertion": "Scenario is green-navigation.eeoi_cii (IMO EEOI/CII operational carbon-intensity metrics for a KVLCC2 tanker).",
          "confidence": "high",
          "status": "supported",
          "evidence": [
            {
              "locator_id": "e12",
              "locator_type": "char_offset",
              "value": "chars[476:509) line 17",
              "start_offset": 476,
              "end_offset": 509,
              "line": 17,
              "quote": "**CII/AER**（碳强度指标，MEPC.353(78) G1",
              "content_hash": "sha256:df32414c0301e96cd5cf15794b56e5b455c26ae877a4e8ac408c9a7ff513027d"
            },
            {
              "locator_id": "e18",
              "locator_type": "char_offset",
              "value": "chars[1533:1560) line 49",
              "start_offset": 1533,
              "end_offset": 1560,
              "line": 49,
              "quote": "几何先验校验（平台纪律：先验 Cb/L/B 再算性能）",
              "content_hash": "sha256:eabc636e2c528b594dc8827a8068daeed021507153acb6ef53fa02d034d7c6e8"
            }
          ],
          "rationale": "Metrics defined per MEPC.1/Circ.684 and MEPC.353(78); geometry is KVLCC2 (tanker)."
        },
        {
          "assertion_id": "c07",
          "facet": "evidence_grading_in_source",
          "assertion": "Source itself grades its evidence: physical chain REAL, rule coefficients (C_F / reference lines / Z / d-vector) WITHHELD.",
          "confidence": "high",
          "status": "supported",
          "evidence": [
            {
              "locator_id": "e10",
              "locator_type": "char_offset",
              "value": "chars[244:268) line 6",
              "start_offset": 244,
              "end_offset": 268,
              "line": 6,
              "quote": "**证据分级**：物理链 `REAL`；规则系数",
              "content_hash": "sha256:78b4832d36cbb985b670c99bcc0f003011f202141550610f99f270f00546bad8"
            },
            {
              "locator_id": "e11",
              "locator_type": "char_offset",
              "value": "chars[2646:2680) line 77",
              "start_offset": 2646,
              "end_offset": 2680,
              "line": 77,
              "quote": "`required_evidence_grade=WITHHELD`",
              "content_hash": "sha256:9f6910358694b938130d1daf8b8e17acfdf3214e38ad3ee5dd755d5d6941c7d4"
            }
          ],
          "rationale": "Preserved as reported; this工序 does not re-verify or upgrade it."
        },
        {
          "assertion_id": "c08",
          "facet": "known_limitation:external_baseline",
          "assertion": "Against the external MEPC.353(78) 2019 tanker reference line the deviation is +21.23%, i.e. > 3% (explicitly stated as NOT satisfied, WITHHELD caliber).",
          "confidence": "high",
          "status": "supported",
          "evidence": [
            {
              "locator_id": "e07",
              "locator_type": "char_offset",
              "value": "chars[8766:8777) line 249",
              "start_offset": 8766,
              "end_offset": 8777,
              "line": 249,
              "quote": "偏离 +21.23%，",
              "content_hash": "sha256:f45a1b6ba4158767aeb7e1d53ffc2958aeaf917f66285fcdfb6d54dfe6991a8f"
            },
            {
              "locator_id": "e06",
              "locator_type": "char_offset",
              "value": "chars[8780:8793) line 250",
              "start_offset": 8780,
              "end_offset": 8793,
              "line": 250,
              "quote": "**> 3%（不满足）**",
              "content_hash": "sha256:d2a095d54084363c66af892ee1e8759977eeb6efc26bb5e83b91f849e0b4825c"
            }
          ],
          "rationale": "Recorded so downstream 03/04 does not read the internal PASS lines as external accuracy."
        },
        {
          "assertion_id": "c09",
          "facet": "known_limitation:external_benchmark_missing",
          "assertion": "The planned IMO GHG Study 4 (2020) per-ship benchmark was not obtained; the source declares that node unfinished.",
          "confidence": "high",
          "status": "supported",
          "evidence": [
            {
              "locator_id": "e15",
              "locator_type": "char_offset",
              "value": "chars[7793:7821) line 224",
              "start_offset": 7793,
              "end_offset": 7821,
              "line": 224,
              "quote": "IMO GHG Study 4 (2020) 基准未取得",
              "content_hash": "sha256:6574968638fdfa04292677828098eef02dbfa2daafbff54294d9ee1b7a6fcda5"
            }
          ],
          "rationale": "Explicit honest-FAIL statement in §4/§5.3."
        },
        {
          "assertion_id": "c10",
          "facet": "known_limitation:in_repo_api_disagreement",
          "assertion": "The in-repo API endpoint still returns NOT_SUPPORTED for CII rating status; the report does not overturn that judgement.",
          "confidence": "high",
          "status": "supported",
          "evidence": [
            {
              "locator_id": "e16",
              "locator_type": "char_offset",
              "value": "chars[9482:9527) line 267",
              "start_offset": 9482,
              "end_offset": 9527,
              "line": 267,
              "quote": "`_gn_cii_rating_status()` 仍返回 `NOT_SUPPORTED`",
              "content_hash": "sha256:233998ad2cd8f087a45adc13e20a690448eeae844f12adf66d940523b7c877c0"
            }
          ],
          "rationale": "Two calibers coexist by design: physical chain REAL vs rule transcription WITHHELD."
        },
        {
          "assertion_id": "c11",
          "facet": "structure:rating_table",
          "assertion": "Annual CII/rating results for 2023-2027 are tabulated in §3.3 (six round trips per year).",
          "confidence": "high",
          "status": "supported",
          "evidence": [
            {
              "locator_id": "e13",
              "locator_type": "char_offset",
              "value": "chars[4255:4289) line 131",
              "start_offset": 4255,
              "end_offset": 4289,
              "line": 131,
              "quote": "### 3.3 年度 CII 与 A–E 评级（6 个往返航次/年）",
              "content_hash": "sha256:39aa459642a2c6651b6bd890e15db7bd8e8a756b16a658322e8dc833c31ec88f"
            }
          ],
          "rationale": "Section segmentation anchor for downstream extraction."
        },
        {
          "assertion_id": "c12",
          "facet": "uncertainty:registry_signal_blindness",
          "assertion": "The skill registry's identify_signals cannot discriminate this report: all six types score 0 on their cardinal signals (English-only templates vs Chinese report).",
          "confidence": "high",
          "status": "unresolved",
          "evidence": [],
          "rationale": "Measured, not assumed (see outputs.classification.json.registry_signal_probe). Unresolved because it is a registry gap, not a property of this report: fixing the registry is out of scope for this work package."
        }
      ],
      "claims": [],
      "claims_note": {
        "extraction_performed": false,
        "reason": "objective.classify_report_type=true, objective.register_assets=false, contract notes '不做抽取'; claim/evidence/provenance extraction belongs to工序 03.",
        "consequence": "outputs.claims.json is intentionally absent from this package; the acceptance item 'all_claims_have_evidence_or_explicit_unresolved_status' is satisfied vacuously for claims[] and non-vacuously by classification_assertions[], where 11/12 assertions carry resolvable locators and 1 is explicitly 'unresolved'."
      },
      "provenance": {
        "source_uri": "tensor://reports/9461",
        "source_field": "markdown",
        "source_hash": "sha256:c839141234f9b547f153399b3e09784457d55832f3449d16c7b5b21a278a92b1",
        "source_hash_recomputed_locally": true,
        "title": "EEOI 与 CII 营运指标闭环验证（节点 p48w3-n09-eeoi-cii · m8189）",
        "scenario_key": "green-navigation.eeoi_cii",
        "chars": 10571
      },
      "limitations": [
        "Classification is a falsifiable hypothesis, not a verification: verification is computed by the platform gate.",
        "Topic labels are derived from the source's own wording; no external regulation text was consulted.",
        "The source's own evidence grading (REAL/WITHHELD) is preserved verbatim and not re-adjudicated.",
        "The experimental-validation skill expects 'facility' and 'measurement uncertainty' signals; neither exists in this report (the source states 未做不确定性传播). Downstream 03 must record them as absent, not invent them."
      ]
    }
  }
}
```
