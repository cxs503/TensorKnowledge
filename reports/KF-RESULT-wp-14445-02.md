# KF-RESULT wp-14445-02

**package_id**: wp-14445-02
**task_type**: 02-classification-parse
**report_id**: 14445
**tags**: kf-wp:wp-14445-02, kf-stage:02, lane:B, GAP-PP-5, classification
**status**: draft

---

## ① 本工序做了什么

**对象（案例介绍）**：report_id=14445，标题 `GAP-PP-5 可微路径设备口径：文档化 CPU 基线 + tensor-tau 梯度回归 A/B（m15359）`，scenario_key=`gap_pp5_cpu_baseline`，源 `tensor://reports/14445` 的 `markdown` 字段共 8040 字符 / 9541 bytes。该报告本身是"GAP-PP-5 可微路径设备口径（CPU 基线 + tensor-tau 梯度回归 A/B）"的一轮计算报告（双层结构：①–⑥ 中文正题 + 英文附录 §1–§7）。

本工序只做 **02-classification-parse**：

- 取源并**独立重算**字节哈希 → `sha256:0fad2f03c7cceceba726538a60a0c9e206b0a932e9d53e10f5e32388da25c85b`，与契约 `source_hash` 逐位一致，`chars`=8040（契约 8040）；
- 按 `extraction-skills/registry.json` 的六分型给出**可反驳**分类假设：primary=`scientific-computation`，secondary=`software-engineering`，confidence=`medium`；六类逐类给出"为何不作为 primary"的裁决（③.3）；
- 选中 skill：`xsk-scientific-computation`（次要 `xsk-software-engineering`）；
- 结构切分：19 个标题全部按字符偏移落位，覆盖整篇（首节 start_char=0，末节 end_char=8039 = len−1）；
- 7 个主题标签，每标签绑定一条逐字 locator；
- **不做**抽取、不登记资产、不标 verified：`claims_extracted=False`、`assets_registered=False`、`marked_verified=False`、`other_reports_touched=False`。

## ② 怎么做的（步骤/工具/关键设置）

1. **取源**：`GET $TENSOR_API_BASE/tensor/reports/14445`（Bearer 登录令牌），只读 `markdown` 字段；原文逐字节副本落 `docs/wp-14445-02/source/14445.markdown`，供离线复算 locator（`sha256sum` 复核 = `0fad2f03c7cceceba726538a60a0c9e206b0a932e9d53e10f5e32388da25c85b`）。
2. **哈希门**：`hashlib.sha256(md.encode("utf-8"))` 与契约常量比对，不等即 `SystemExit`——不允许在错源上分类。
3. **零手抄定位**：脚本只声明**短锚串**，quote 一律 `md[start:end]` 运行时切片，记录 `start_char/end_char/start_line/end_line/quote_sha256/occurrences`；锚串非唯一即构建失败（唯一性=可解析性）。
4. **信号扫描**：对 registry 每个 skill 的 `identify_signals` 做**词边界**、大小写不敏感计数（不用裸子串：否则 `plan` 命中 `control plane`，凭空造出 technical-proposal 证据）；开放式匹配器（如 `O(n`）按字面计。
5. **语义映射与反向证据**：registry 短语与报告用词不一致时（报告写 `Wall-clock / throughput table`，registry 写 `timing table`）登记为 `semantic_signal_map`（标 strength），并另记 `absent_signal_evidence`——**信号真不满足就写不满足**，不把沉默当支持。
6. **结构切分**：行首标题正则（`#{1,3}`）+ ①–⑥ 标记；每节记 `start_char/chars/kind`，并断言相邻节无缝、覆盖全文。
7. **渲染**：本页所有数字、字符跨度、引文由 `scripts/kf/wp14445_02_emit_report.py` 从 `classification.json` / `kf_result_wp-14445-02.json` 注入（零手抄）；`figures/` 图由 matplotlib 从同一产物生成。
8. **机检**：`pytest tests/test_wp14445_02_classification.py`（21 项）。

工具链：Python 3 + 标准库（urllib/hashlib/json/re）+ jsonschema + matplotlib。**参数表**：本工序无数值参数（不是物理算例）——唯一"参数"是分型阈值口径（字面 vs 语义），已在 ③.2/③.3 与 `report_type.signal_policy` 明示。

## ③ 产出物清单（含结果图）

### ③.1 交付文件

| 输出文件 | 要点 |
|---|---|
| `docs/wp-14445-02/classification.json` | 分型判定（primary/secondary/confidence/五类替代裁决）+ 19 节结构切分 + 7 主题标签 + 26 条 locator + 3 条 parse note |
| `kf_result_wp-14445-02.json` | kf_result.v1 信封；本页 JSON 块与之**字节一致**（测试断言） |
| `docs/wp-14445-02/source/14445.markdown` | 源报告逐字节副本（9541 bytes），离线复核 locator |
| `figures/wp-14445-02/fig_wp-14445-02_classification.png` | 图：结构切分 + 六分型信号证据（双面板） |
| `reports/KF-RESULT-wp-14445-02.md` | 本页 |
| `scripts/kf/wp14445_02_classify.py` / `scripts/kf/wp14445_02_emit_report.py` | 分类器 / 渲染器（一键复跑） |
| `tests/test_wp14445_02_classification.py` | 机器门 21 项：schema、哈希、locator 逐字可解析、ID 唯一、结构无缝、无悬空引用、单 json 块 |

### ③.2 六分型信号扫描结果（字面口径，词边界计数）

| report_type | 命中 | 命中的 signal |
|---|---|---|
| literature-review | 0/5 | — |
| scientific-computation | 0/5 | — |
| algorithm-implementation | 0/5 | — |
| software-engineering | 2/5 | commit×2, regression×2 |
| technical-proposal | 0/5 | — |
| experimental-validation | 0/5 | — |

字面口径领先者 = `software-engineering`。本工序 primary **不是**按字面计数选的（规则与证伪条件见 `report_type.decision_rule` / `signal_policy.falsifier`），差异如实留在产物里。

### ③.3 语义映射 / 反向证据 / 逐类裁决

**语义映射（只登记经得起反驳的映射，逐条带 strength）**

| id | report_type | registry signal | locator | 强度 | 原文引文 |
|---|---|---|---|---|---|
| S1 | scientific-computation | timing table | L1 | strong | `Wall-clock / throughput table` |
| S2 | software-engineering | regression | L4 | strong | `live regression` |
| S3 | software-engineering | commit | L6 | strong | `TensorLBM commit` |
| S4 | experimental-validation | test matrix | L9 | strong | `9 configurations` |
| S5 | experimental-validation | validation case | L3 | partial | `shear-wave decay anchor` |
| S6 | experimental-validation | baseline comparison | L8 | partial | `ref vs got` |

**反向证据（信号确实不满足）**

| id | report_type | registry signal | locator | 原文引文（逐字） |
|---|---|---|---|---|
| A1 | scientific-computation | convergence study | L10 | `Tau-mode convergence curve figure omitted` |

**六类逐类裁决（为什么不是别的类）**

| report_type | 支撑 locator | 为何不作为 primary |
|---|---|---|
| software-engineering | L4, L6, L7, L5 | commit/regression/pytest-A/B evidence is present and would make this the primary under a literal-signal or count rule, but it covers §7 plus one paragraph of §2 — the deliverable itself is the timing matrix |
| experimental-validation | L3, L8, L9 | test-matrix / validation-case / baseline-comparison wording is present, but two of the registry's experimental-validation signals are unsatisfied ('facility': none; 'measurement uncertainty': no budget, only a metric-comparability caveat about the RSS figure, locator T4) and the validation target is an analytic anchor for the solver, not measured data |
| algorithm-implementation | — | no pseudocode/complexity/algorithm block; the code is an example CLI, not the subject |
| literature-review | — | three citations for anchors, no survey structure, nothing synthesised from the literature |
| technical-proposal | — | it reports work already executed (A/B done, tables filled), it does not propose future work |

### ③.4 结果图

![fig_wp-14445-02_classification.png](../figures/wp-14445-02/fig_wp-14445-02_classification.png)

左：源报告结构切分（19 个标题、按字符偏移落位；蓝=①–⑥ 中文正题、紫=附录标题、绿=英文 §1–§7）；右：六分型 identify_signals 命中（红=registry 字面命中、绿=语义映射命中），primary 判定为 scientific-computation。

## ④ 证据定位表（claim/字段 → 原文引文片段）

全部 quote 为运行时切片（`quote_sha256` 逐条留存），`start_char` 可直接在 `docs/wp-14445-02/source/14445.markdown` 上复算；测试对 26 条逐条断言 `source[start:end] == quote` 且 sha256 相符、行号与偏移一致。

| locator | 用途 | 字符跨度 | 行 | 原文引文片段（逐字） |
|---|---|---|---|---|
| L1 | type | 5286–5315 | 89 | `Wall-clock / throughput table` |
| L2 | type | 5997–6017 | 102 | `Sensitivity: 3 grids` |
| L3 | type | 4770–4793 | 76 | `shear-wave decay anchor` |
| L4 | type | 3542–3557 | 50 | `live regression` |
| L5 | type | 7910–7934 | 113 | `Fix belongs in TensorLBM` |
| L6 | type | 3379–3395 | 49 | `TensorLBM commit` |
| L7 | type | 7995–8038 | 113 | `upstream test that is currently red on main` |
| L8 | type | 4194–4204 | 63 | `ref vs got` |
| L9 | type | 6061–6077 | 102 | `9 configurations` |
| L10 | type | 6798–6839 | 107 | `Tau-mode convergence curve figure omitted` |
| L12 | type | 1803–1810 | 23 | `不是 CUDA` |
| T1 | topic | 154–184 | 2 | `examples/differentiable_lbm.py` |
| T2 | topic | 185–195 | 2 | `--mode tau` |
| T3 | topic | 559–567 | 7 | `autograd` |
| T4 | topic | 1797–1802 | 23 | `VmHWM` |
| T5 | topic | 1258–1263 | 14 | `MLUPS` |
| T6 | topic | 6301–6340 | 105 | `Cluster leg not completed in this round` |
| T7 | topic | 6639–6669 | 106 | `GPU node was added to the pool` |
| D1 | parse-note | 1394–1403 | 15 | `<0.01% 量级` |
| D2 | parse-note | 2041–2053 | 28 | `三参数点均 <0.01%` |
| D3 | parse-note | 4897–4939 | 79 | `\| 0.6 \| 0.03333333 \| 0.03496079 \| 4.8824 \|` |
| D4 | parse-note | 1688–1710 | 21 | `来自控制面宿主（loongarch64 架构` |
| D5 | parse-note | 6565–6604 | 105 | `come from the control-plane x86_64 host` |
| D6 | parse-note | 204–218 | 2 | `墙钟/吞吐/峰值RSS 矩阵` |
| D7 | parse-note | 5286–5326 | 89 | `Wall-clock / throughput table (variant B` |
| D8 | parse-note | 2126–2134 | 34 | `程序化生成的表格` |

### ④.1 结构切分（19 节，覆盖 8040 字符）

| # | kind | start_char | chars | 标题 |
|---|---|---|---|---|
| 1 | contract_section_zh | 0 | 449 | ## ① 案例介绍 |
| 2 | contract_section_zh | 449 | 472 | ## ② 怎么做的 |
| 3 | contract_section_zh | 921 | 486 | ## ③ 计算结果 |
| 4 | contract_section_zh | 1407 | 140 | ## ④ 结果图 |
| 5 | contract_section_zh | 1547 | 314 | ## ⑤ 注意点 / 局限 |
| 6 | contract_section_zh | 1861 | 260 | ## ⑥ 误差判定（是否 <3%） |
| 7 | appendix | 2121 | 15 | # 附录：程序化生成的表格 |
| 8 | appendix | 2136 | 228 | # GAP-PP-5 · differentiable path device line: documented CPU |
| 9 | appendix_section_en | 2364 | 707 | ## 1 Problem setting & baseline provenance |
| 10 | appendix_section_en | 3071 | 866 | ## 2 Method & implementation |
| 11 | appendix_section_en | 3937 | 252 | ## 3 Parameters |
| 12 | appendix_section_en | 4189 | 16 | ## 4 ref vs got |
| 13 | appendix_section_en | 4205 | 305 | ### 4.1 tau recovery end-to-end (ref = tau* = 0.9, exact by  |
| 14 | appendix_section_en | 4510 | 252 | ### 4.2 gradient vs central finite difference (fp64) |
| 15 | appendix_section_en | 4762 | 258 | ### 4.3 shear-wave decay anchor (analytic nu = (tau-0.5)/3), |
| 16 | appendix_section_en | 5020 | 261 | ### 4.4 upstream regression test A/B (`pytest tests/test_aut |
| 17 | appendix_section_en | 5281 | 981 | ## 5 Wall-clock / throughput table (variant B = intended dif |
| 18 | appendix_section_en | 6262 | 1227 | ## 6 Failure modes / scope / repro |
| 19 | appendix_section_en | 7489 | 551 | ## 7 Findings handed back to TensorLBM (cross-repo, not fixe |

### ④.2 解析备注（记录，不裁决）

- **N1**（internal_discrepancy_observed）：front matter ③/⑥ state the shear-wave anchor errors as <0.01% while the appendix §4.3 table for the same three tau points tops out at 4.8824%; the two readings are not reconcilable from the text alone；定位 D1/D2/D3；处置：reported, not adjudicated (stage 02 does not extract or grade claims)
- **N2**（internal_discrepancy_observed）：front matter ⑤ places the numbers on a loongarch64 control-plane host while appendix §6 says they come from the x86_64 control-plane host; §2 lists loongarch64 as the device；定位 D4/D5；处置：reported, not adjudicated; device identification is genuinely uncertain
- **N3**（structural_duplication_risk）：the front matter summarises the appendix: the deliverable described in ① is re-presented as the appendix timing table, and the appendix is introduced as programmatically generated — the same result therefore appears twice in one document, so a stage-03 extractor must deduplicate by value+context or it will double-count；定位 D6/D7/D8；处置：reported as a downstream risk; this stage extracts nothing

## ⑤ 注意点与局限

- **分类是可反驳假设，不是事实**：primary 依赖"报告想交付什么"的实质判断，而 registry 字面命中给出的是另一类（③.2 表 + falsifier）。若平台 02 政策是"纯字面信号"，本单 primary 应改判——错误在分类器，不在原文。
- **两条原文内部不一致已记录未裁决**（N1：正题写 `<0.01%` 与附录 §4.3 表最大 4.8824% 无法用文本自洽；N2：宿主架构 loongarch64 与 x86_64 两说）。本工序不做抽取与裁定，按 `preserve_uncertainty` 原样保留。
- **N3 结构重复呈现**（正题① ↔ 附录 §5 同一交付物；附录自述"程序化生成的表格"）：若 03 不按 value+context 去重，会重复计数。
- **踩坑（共享 /tmp）**：发布载荷原用 `/tmp/report.json`，该路径全机共享，本轮观察到被另一 lane 的载荷占用/覆盖；本单改用 `/tmp/report_wp-14445-02.json` 并在发布前逐字段核对 `title/tags/markdown 首行`。本单**未访问平台侧任何其它 report_id 的报告记录**，也未读写其它工作包的产物；`/tmp` 里撞见的其它 lane 载荷既未使用也未修改（我既不引用其内容，也不覆盖其路径）。
- **独立性局限**：本单 `review.required=false`、`independent_reviewer=false`，我是**生产者**，所有自检是自证；真正独立性来自平台门与 04 审核。
- **本工序不产出知识**：`source_hash_matches=true` 只是哈希事实，不是知识验证；产物内无 claim、无 `verified` 标记。

## ⑥ 自检（逐条对照 acceptance）/ 误差判定 / 复跑

| # | acceptance | 结果 | 依据（可机器复现） |
|---|---|---|---|
| 1 | valid_json | **PASS** | `json.load` 成功；`jsonschema.validate(envelope, kf_result.v1)` 通过（`test_envelope_validates_against_kf_result_schema`） |
| 2 | schema_pass | **PASS** | 信封 required 四字段齐全、`additionalProperties:false`；`outputs` 只含 `classification.json` 且为对象 |
| 3 | source_locator_resolvable | **PASS** | 26/26 条 locator 按 `start_char:end_char` 逐字复现 + `quote_sha256` 相符 + 行号与偏移自洽（2 个测试逐条断言） |
| 4 | source_hash_matches | **PASS** | 独立重算 `sha256:0fad2f03c7cceceba726538a60a0c9e206b0a932e9d53e10f5e32388da25c85b` == 契约 == `provenance.source_hash`；`sha256sum` 对落盘副本复算一致 |
| 5 | no_duplicate_ids | **PASS** | locator_id(26) / note_id(3) / tag(7) / 节索引 域内全唯一；`counts` 与实体逐项相符 |
| 6 | all_claims_have_evidence_or_explicit_unresolved_status | **PASS（N/A 已说明）** | 本工序不产 claim；所有判断项均带 locator；无法自洽的两处显式标 `internal_discrepancy_observed` + `unresolved` 处置，不粉饰 |

**附加机检（超出 acceptance 的自我挑战）**：结构无缝覆盖全文（`a.end_char+1 == b.start_char`，末节到 `len−1`）；产物内 `L*/T*/D*` 引用无悬空；语义映射不含无文本支持的类（literature-review / algorithm-implementation / technical-proposal）；字面命中不得由裸子串造成（`plan`/`plane` 陷阱回归测试）；报告唯一 json 块 == 信封文件字节；报告表格里的每个字符跨度都能在产物中找到。

**误差判定（关键量 vs 基准，是否 <3%）**：本工序**无数值计算**，故无"对物理/解析基准的误差"可列——这是文档结构工序，按 owner 规定写明理由而非含糊。可机检替代指标（全部为计数，无插值）：locator 逐字可解析率 = 26/26 = **100%**；源哈希一致性 = **1/1**；ID 重复 = **0**；悬空引用 = **0**；结构覆盖 = **8040/8040 字符**。分类本身**无真值基准**，故不宣称任何"分类正确率"百分比（honest：不可算）。

**未跑的检查（如实标 unknown/not_run）**：平台侧哈希与 locator 二次确认（由平台门算，本单未跑）；03 抽取阶段的实际去重行为（下游）；分类正确性的外部标注（不存在）。

**repro_cmd（一键复跑）**

```
cd <worktree> && python3 scripts/kf/wp14445_02_classify.py \
  --source-file docs/wp-14445-02/source/14445.markdown \
  && python3 scripts/kf/wp14445_02_emit_report.py \
  && python3 -m pytest tests/test_wp14445_02_classification.py -q
```

（在线复核：去掉 `--source-file`，脚本重新从平台取源并重算哈希。）

---

## 结果 JSON（唯一 json 块）

```json
{
  "package_id": "wp-14445-02",
  "task_type": "02-classification-parse",
  "contract_version": "1.0",
  "report_id": "14445",
  "provenance": {
    "source_uri": "tensor://reports/14445",
    "source_field": "markdown",
    "source_hash": "sha256:0fad2f03c7cceceba726538a60a0c9e206b0a932e9d53e10f5e32388da25c85b",
    "source_hash_matches": true,
    "title": "GAP-PP-5 可微路径设备口径：文档化 CPU 基线 + tensor-tau 梯度回归 A/B（m15359）",
    "scenario_key": "gap_pp5_cpu_baseline",
    "chars": 8040
  },
  "outputs": {
    "classification.json": {
      "schema": "classification.v1",
      "package_id": "wp-14445-02",
      "task_type": "02-classification-parse",
      "contract_version": "1.0",
      "report_id": "14445",
      "source": {
        "uri": "tensor://reports/14445",
        "field": "markdown",
        "title": "GAP-PP-5 可微路径设备口径：文档化 CPU 基线 + tensor-tau 梯度回归 A/B（m15359）",
        "scenario_key": "gap_pp5_cpu_baseline",
        "hash_alg": "sha256",
        "hash": "0fad2f03c7cceceba726538a60a0c9e206b0a932e9d53e10f5e32388da25c85b",
        "hash_with_prefix": "sha256:0fad2f03c7cceceba726538a60a0c9e206b0a932e9d53e10f5e32388da25c85b",
        "chars": 8040,
        "bytes_utf8": 9541,
        "declared_chars": 8040,
        "recomputed_independently": true,
        "matches_contract": true
      },
      "taxonomy": {
        "source": "extraction-skills/registry.json",
        "report_types": [
          "literature-review",
          "scientific-computation",
          "algorithm-implementation",
          "software-engineering",
          "technical-proposal",
          "experimental-validation"
        ],
        "note": "six-type taxonomy is read from the registry at build time; no local vocabulary"
      },
      "report_type": {
        "primary": "scientific-computation",
        "secondary": [
          "software-engineering"
        ],
        "confidence": "medium",
        "confidence_rationale": "three of the six types have real textual support (timing table; commit+regression; test matrix/validation case), so the choice of a single primary is a judgement about what the report IS, not a count. The spine of the document is the device baseline matrix (front matter ① -> appendix §5) plus analytic verification (L3, L8); the defect A/B is written up as a finding handed back (L5). Hence scientific-computation primary, software-engineering secondary, confidence medium not high",
        "decision_rule": "primary = the type of the artifact the round set out to deliver; secondary = types carried by substantial sections. Signal counts are NOT the decision rule and are reported separately so the choice stays falsifiable",
        "alternatives_considered": [
          {
            "report_type": "software-engineering",
            "supporting_locator_ids": [
              "L4",
              "L6",
              "L7",
              "L5"
            ],
            "why_not_primary": "commit/regression/pytest-A/B evidence is present and would make this the primary under a literal-signal or count rule, but it covers §7 plus one paragraph of §2 — the deliverable itself is the timing matrix"
          },
          {
            "report_type": "experimental-validation",
            "supporting_locator_ids": [
              "L3",
              "L8",
              "L9"
            ],
            "why_not_primary": "test-matrix / validation-case / baseline-comparison wording is present, but two of the registry's experimental-validation signals are unsatisfied ('facility': none; 'measurement uncertainty': no budget, only a metric-comparability caveat about the RSS figure, locator T4) and the validation target is an analytic anchor for the solver, not measured data"
          },
          {
            "report_type": "algorithm-implementation",
            "supporting_locator_ids": [],
            "why_not_primary": "no pseudocode/complexity/algorithm block; the code is an example CLI, not the subject"
          },
          {
            "report_type": "literature-review",
            "supporting_locator_ids": [],
            "why_not_primary": "three citations for anchors, no survey structure, nothing synthesised from the literature"
          },
          {
            "report_type": "technical-proposal",
            "supporting_locator_ids": [],
            "why_not_primary": "it reports work already executed (A/B done, tables filled), it does not propose future work"
          }
        ],
        "signal_policy": {
          "literal_scan_leader": "software-engineering",
          "literal_matched_counts": {
            "literature-review": 0,
            "scientific-computation": 0,
            "algorithm-implementation": 0,
            "software-engineering": 2,
            "technical-proposal": 0,
            "experimental-validation": 0
          },
          "rule_applied": "primary is a substantive reading of what the round delivered; the literal registry scan is reported verbatim next to it, including its disagreement",
          "falsifier": "if the stage-02 policy were literal-signal-only, 'software-engineering' would be primary and this classification wrong; the registry phrase list also has no phrase for the report's own words ('Wall-clock / throughput table')"
        },
        "unclassified_is_legal": true
      },
      "skills": {
        "selected_skill_id": "xsk-scientific-computation",
        "secondary_skill_ids": [
          "xsk-software-engineering"
        ],
        "selection_rule": "skill whose report_type equals report_type.primary; secondary skill recorded for the software-engineering findings section"
      },
      "signals": {
        "scan_rule": "word-boundary (not raw substring) case-insensitive count of each registry identify_signals phrase over the whole markdown; open matchers such as 'O(n' are counted literally",
        "per_skill": [
          {
            "skill_id": "xsk-literature-review",
            "report_type": "literature-review",
            "signals": [
              {
                "signal": "related work",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "state of the art",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "survey",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "bibliography",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "citation density >= 5 per 1000 chars",
                "literal_occurrences": 0,
                "matched": false
              }
            ],
            "signals_matched": 0,
            "signals_total": 5
          },
          {
            "skill_id": "xsk-scientific-computation",
            "report_type": "scientific-computation",
            "signals": [
              {
                "signal": "governing equations",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "discretisation",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "convergence study",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "mesh refinement",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "timing table",
                "literal_occurrences": 0,
                "matched": false
              }
            ],
            "signals_matched": 0,
            "signals_total": 5
          },
          {
            "skill_id": "xsk-algorithm-implementation",
            "report_type": "algorithm-implementation",
            "signals": [
              {
                "signal": "pseudocode",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "complexity",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "algorithm block",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "function signature",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "O(n",
                "literal_occurrences": 0,
                "matched": false
              }
            ],
            "signals_matched": 0,
            "signals_total": 5
          },
          {
            "skill_id": "xsk-software-engineering",
            "report_type": "software-engineering",
            "signals": [
              {
                "signal": "changed files",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "commit",
                "literal_occurrences": 2,
                "matched": true
              },
              {
                "signal": "interface",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "regression",
                "literal_occurrences": 2,
                "matched": true
              },
              {
                "signal": "API",
                "literal_occurrences": 0,
                "matched": false
              }
            ],
            "signals_matched": 2,
            "signals_total": 5
          },
          {
            "skill_id": "xsk-technical-proposal",
            "report_type": "technical-proposal",
            "signals": [
              {
                "signal": "proposal",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "design",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "roadmap",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "specification",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "plan",
                "literal_occurrences": 0,
                "matched": false
              }
            ],
            "signals_matched": 0,
            "signals_total": 5
          },
          {
            "skill_id": "xsk-experimental-validation",
            "report_type": "experimental-validation",
            "signals": [
              {
                "signal": "test matrix",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "facility",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "measurement uncertainty",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "validation case",
                "literal_occurrences": 0,
                "matched": false
              },
              {
                "signal": "baseline comparison",
                "literal_occurrences": 0,
                "matched": false
              }
            ],
            "signals_matched": 0,
            "signals_total": 5
          }
        ],
        "semantic_signal_map": [
          {
            "map_id": "S1",
            "report_type": "scientific-computation",
            "registry_signal": "timing table",
            "locator_id": "L1",
            "strength": "strong",
            "quote": "Wall-clock / throughput table",
            "note": "registry phrase mapped onto a report feature stated in different words"
          },
          {
            "map_id": "S2",
            "report_type": "software-engineering",
            "registry_signal": "regression",
            "locator_id": "L4",
            "strength": "strong",
            "quote": "live regression",
            "note": "registry phrase mapped onto a report feature stated in different words"
          },
          {
            "map_id": "S3",
            "report_type": "software-engineering",
            "registry_signal": "commit",
            "locator_id": "L6",
            "strength": "strong",
            "quote": "TensorLBM commit",
            "note": "registry phrase mapped onto a report feature stated in different words"
          },
          {
            "map_id": "S4",
            "report_type": "experimental-validation",
            "registry_signal": "test matrix",
            "locator_id": "L9",
            "strength": "strong",
            "quote": "9 configurations",
            "note": "registry phrase mapped onto a report feature stated in different words"
          },
          {
            "map_id": "S5",
            "report_type": "experimental-validation",
            "registry_signal": "validation case",
            "locator_id": "L3",
            "strength": "partial",
            "quote": "shear-wave decay anchor",
            "note": "registry phrase mapped onto a report feature stated in different words"
          },
          {
            "map_id": "S6",
            "report_type": "experimental-validation",
            "registry_signal": "baseline comparison",
            "locator_id": "L8",
            "strength": "partial",
            "quote": "ref vs got",
            "note": "registry phrase mapped onto a report feature stated in different words"
          }
        ],
        "absent_signal_evidence": [
          {
            "map_id": "A1",
            "report_type": "scientific-computation",
            "registry_signal": "convergence study",
            "locator_id": "L10",
            "satisfied": false,
            "quote": "Tau-mode convergence curve figure omitted",
            "note": "the report has no convergence study: the tau convergence curve is explicitly reported as omitted"
          }
        ]
      },
      "evidence_for_classification": [
        {
          "method": "char_span",
          "start_char": 5286,
          "end_char": 5315,
          "start_line": 89,
          "end_line": 89,
          "quote": "Wall-clock / throughput table",
          "quote_sha256": "999ec4f85f0e046eeaa8ee92a9326fde919fd3db90363e936b153419038ea764",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "L1"
        },
        {
          "method": "char_span",
          "start_char": 5997,
          "end_char": 6017,
          "start_line": 102,
          "end_line": 102,
          "quote": "Sensitivity: 3 grids",
          "quote_sha256": "28c57fa40eb9e240c20d3d41aab527fa90ab57c46f91a93b8d36f60f4b448e57",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "L2"
        },
        {
          "method": "char_span",
          "start_char": 4770,
          "end_char": 4793,
          "start_line": 76,
          "end_line": 76,
          "quote": "shear-wave decay anchor",
          "quote_sha256": "1769e2c974b5e72fbdbbf675ae79efb70c5c572fa83c3e3e121868727fa12cc2",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "L3"
        },
        {
          "method": "char_span",
          "start_char": 3542,
          "end_char": 3557,
          "start_line": 50,
          "end_line": 50,
          "quote": "live regression",
          "quote_sha256": "e4b1344f3043a9a944d6925f9b32e7edd8def36eec85abe8f08e8ba823015582",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "L4"
        },
        {
          "method": "char_span",
          "start_char": 7910,
          "end_char": 7934,
          "start_line": 113,
          "end_line": 113,
          "quote": "Fix belongs in TensorLBM",
          "quote_sha256": "2c2d97e1973d6462a8d26aae5a377083a0449524ba7c18425527d3bee3dbd0ed",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "L5"
        },
        {
          "method": "char_span",
          "start_char": 3379,
          "end_char": 3395,
          "start_line": 49,
          "end_line": 49,
          "quote": "TensorLBM commit",
          "quote_sha256": "15c6910c03e91ffd2109c957e25960a641ffdd27a8a9235f82eccd067975b5f5",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "L6"
        },
        {
          "method": "char_span",
          "start_char": 7995,
          "end_char": 8038,
          "start_line": 113,
          "end_line": 113,
          "quote": "upstream test that is currently red on main",
          "quote_sha256": "d118440ef0c4f3febe3671ba7dc694b303eea0f1abec427154c5962fa399f3ac",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "L7"
        },
        {
          "method": "char_span",
          "start_char": 4194,
          "end_char": 4204,
          "start_line": 63,
          "end_line": 63,
          "quote": "ref vs got",
          "quote_sha256": "a55fe5a9d1f45986a94c0297ed854f04021e4786c735b58f3bf158a4bce7228e",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "L8"
        },
        {
          "method": "char_span",
          "start_char": 6061,
          "end_char": 6077,
          "start_line": 102,
          "end_line": 102,
          "quote": "9 configurations",
          "quote_sha256": "67a2827ee7570ef5da306bd92f439e33b678015976c5743a8107448ddb202954",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "L9"
        },
        {
          "method": "char_span",
          "start_char": 6798,
          "end_char": 6839,
          "start_line": 107,
          "end_line": 107,
          "quote": "Tau-mode convergence curve figure omitted",
          "quote_sha256": "b28b1b59e6ebbae62cae9542f4594965fb2c10843362529f2c7bd7228c41ed9f",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "L10"
        },
        {
          "method": "char_span",
          "start_char": 1803,
          "end_char": 1810,
          "start_line": 23,
          "end_line": 23,
          "quote": "不是 CUDA",
          "quote_sha256": "415e01488dc8d6e32868380f099e80399823f9a1685d5e00a1361d00126d0fe1",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "L12"
        }
      ],
      "topic_tags": [
        {
          "tag": "differentiable-lbm",
          "locator_id": "T1"
        },
        {
          "tag": "autograd-gradient-check",
          "locator_id": "T3"
        },
        {
          "tag": "cpu-device-baseline",
          "locator_id": "T4"
        },
        {
          "tag": "wall-clock-throughput",
          "locator_id": "T5"
        },
        {
          "tag": "tau-mode-inverse-problem",
          "locator_id": "T2"
        },
        {
          "tag": "cluster-leg-incomplete",
          "locator_id": "T6"
        },
        {
          "tag": "gpu-node-not-pooled",
          "locator_id": "T7"
        }
      ],
      "topic_locators": [
        {
          "method": "char_span",
          "start_char": 154,
          "end_char": 184,
          "start_line": 2,
          "end_line": 2,
          "quote": "examples/differentiable_lbm.py",
          "quote_sha256": "3a374cf59228e9998a6ff028ff99302b6b212d58f3d25a028609e3160a6ab8c1",
          "resolvable": true,
          "occurrences": 2,
          "unique_in_source": false,
          "locator_id": "T1"
        },
        {
          "method": "char_span",
          "start_char": 185,
          "end_char": 195,
          "start_line": 2,
          "end_line": 2,
          "quote": "--mode tau",
          "quote_sha256": "03ece7dd69925579faf80cc90343e228d99bf0eab78a3b9bcf0822e0d2b9ce2b",
          "resolvable": true,
          "occurrences": 3,
          "unique_in_source": false,
          "locator_id": "T2"
        },
        {
          "method": "char_span",
          "start_char": 559,
          "end_char": 567,
          "start_line": 7,
          "end_line": 7,
          "quote": "autograd",
          "quote_sha256": "78b1457554800d3953e9fa932334f43aa5f9322cf0b332e3656620d569732d46",
          "resolvable": true,
          "occurrences": 7,
          "unique_in_source": false,
          "locator_id": "T3"
        },
        {
          "method": "char_span",
          "start_char": 1797,
          "end_char": 1802,
          "start_line": 23,
          "end_line": 23,
          "quote": "VmHWM",
          "quote_sha256": "a919f1aa10e386a1522e39ae9101c3935c86bb8e2d5f94c31d0aca2c752dbb23",
          "resolvable": true,
          "occurrences": 2,
          "unique_in_source": false,
          "locator_id": "T4"
        },
        {
          "method": "char_span",
          "start_char": 1258,
          "end_char": 1263,
          "start_line": 14,
          "end_line": 14,
          "quote": "MLUPS",
          "quote_sha256": "37ca682bb63854e9fad846bb8598a194d955a7dd118a80d433f883841b3ddbb3",
          "resolvable": true,
          "occurrences": 6,
          "unique_in_source": false,
          "locator_id": "T5"
        },
        {
          "method": "char_span",
          "start_char": 6301,
          "end_char": 6340,
          "start_line": 105,
          "end_line": 105,
          "quote": "Cluster leg not completed in this round",
          "quote_sha256": "e3441cb736d116d8422f01ed5e60d93ee2080565a55fa0467b0e25a9c36d190b",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "T6"
        },
        {
          "method": "char_span",
          "start_char": 6639,
          "end_char": 6669,
          "start_line": 106,
          "end_line": 106,
          "quote": "GPU node was added to the pool",
          "quote_sha256": "4d2c03685bac03c69e0c74c0378dcf8cf6251ae1b9a63c1bee7578dacf17bd45",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "T7"
        }
      ],
      "structure": {
        "headings_found": 19,
        "by_kind": {
          "contract_section_zh": 6,
          "appendix": 2,
          "appendix_section_en": 11
        },
        "sections": [
          {
            "index": 1,
            "kind": "contract_section_zh",
            "level": 2,
            "start_char": 0,
            "start_line": 1,
            "title": "## ① 案例介绍",
            "end_char": 448,
            "chars": 449
          },
          {
            "index": 2,
            "kind": "contract_section_zh",
            "level": 2,
            "start_char": 449,
            "start_line": 6,
            "title": "## ② 怎么做的",
            "end_char": 920,
            "chars": 472
          },
          {
            "index": 3,
            "kind": "contract_section_zh",
            "level": 2,
            "start_char": 921,
            "start_line": 10,
            "title": "## ③ 计算结果",
            "end_char": 1406,
            "chars": 486
          },
          {
            "index": 4,
            "kind": "contract_section_zh",
            "level": 2,
            "start_char": 1407,
            "start_line": 17,
            "title": "## ④ 结果图",
            "end_char": 1546,
            "chars": 140
          },
          {
            "index": 5,
            "kind": "contract_section_zh",
            "level": 2,
            "start_char": 1547,
            "start_line": 20,
            "title": "## ⑤ 注意点 / 局限",
            "end_char": 1860,
            "chars": 314
          },
          {
            "index": 6,
            "kind": "contract_section_zh",
            "level": 2,
            "start_char": 1861,
            "start_line": 25,
            "title": "## ⑥ 误差判定（是否 <3%）",
            "end_char": 2120,
            "chars": 260
          },
          {
            "index": 7,
            "kind": "appendix",
            "level": 1,
            "start_char": 2121,
            "start_line": 34,
            "title": "# 附录：程序化生成的表格",
            "end_char": 2135,
            "chars": 15
          },
          {
            "index": 8,
            "kind": "appendix",
            "level": 1,
            "start_char": 2136,
            "start_line": 36,
            "title": "# GAP-PP-5 · differentiable path device line: documented CPU baseline a",
            "end_char": 2363,
            "chars": 228
          },
          {
            "index": 9,
            "kind": "appendix_section_en",
            "level": 2,
            "start_char": 2364,
            "start_line": 41,
            "title": "## 1 Problem setting & baseline provenance",
            "end_char": 3070,
            "chars": 707
          },
          {
            "index": 10,
            "kind": "appendix_section_en",
            "level": 2,
            "start_char": 3071,
            "start_line": 46,
            "title": "## 2 Method & implementation",
            "end_char": 3936,
            "chars": 866
          },
          {
            "index": 11,
            "kind": "appendix_section_en",
            "level": 2,
            "start_char": 3937,
            "start_line": 52,
            "title": "## 3 Parameters",
            "end_char": 4188,
            "chars": 252
          },
          {
            "index": 12,
            "kind": "appendix_section_en",
            "level": 2,
            "start_char": 4189,
            "start_line": 63,
            "title": "## 4 ref vs got",
            "end_char": 4204,
            "chars": 16
          },
          {
            "index": 13,
            "kind": "appendix_section_en",
            "level": 3,
            "start_char": 4205,
            "start_line": 64,
            "title": "### 4.1 tau recovery end-to-end (ref = tau* = 0.9, exact by construction)",
            "end_char": 4509,
            "chars": 305
          },
          {
            "index": 14,
            "kind": "appendix_section_en",
            "level": 3,
            "start_char": 4510,
            "start_line": 70,
            "title": "### 4.2 gradient vs central finite difference (fp64)",
            "end_char": 4761,
            "chars": 252
          },
          {
            "index": 15,
            "kind": "appendix_section_en",
            "level": 3,
            "start_char": 4762,
            "start_line": 76,
            "title": "### 4.3 shear-wave decay anchor (analytic nu = (tau-0.5)/3), fp64",
            "end_char": 5019,
            "chars": 258
          },
          {
            "index": 16,
            "kind": "appendix_section_en",
            "level": 3,
            "start_char": 5020,
            "start_line": 83,
            "title": "### 4.4 upstream regression test A/B (`pytest tests/test_autograd.py -k collide_step_gradients`)",
            "end_char": 5280,
            "chars": 261
          },
          {
            "index": 17,
            "kind": "appendix_section_en",
            "level": 2,
            "start_char": 5281,
            "start_line": 89,
            "title": "## 5 Wall-clock / throughput table (variant B = intended differentiable path, median of reps)",
            "end_char": 6261,
            "chars": 981
          },
          {
            "index": 18,
            "kind": "appendix_section_en",
            "level": 2,
            "start_char": 6262,
            "start_line": 104,
            "title": "## 6 Failure modes / scope / repro",
            "end_char": 7488,
            "chars": 1227
          },
          {
            "index": 19,
            "kind": "appendix_section_en",
            "level": 2,
            "start_char": 7489,
            "start_line": 111,
            "title": "## 7 Findings handed back to TensorLBM (cross-repo, not fixed here)",
            "end_char": 8039,
            "chars": 551
          }
        ],
        "language_layout": "bilingual: ①-⑥ Chinese front matter, then '# 附录' English appendix §1-§7",
        "note": "segmentation is purely structural (heading regex + ①-⑥ markers); no semantic rewrite"
      },
      "parse_notes": [
        {
          "note_id": "N1",
          "kind": "internal_discrepancy_observed",
          "summary": "front matter ③/⑥ state the shear-wave anchor errors as <0.01% while the appendix §4.3 table for the same three tau points tops out at 4.8824%; the two readings are not reconcilable from the text alone",
          "locator_ids": [
            "D1",
            "D2",
            "D3"
          ],
          "disposition": "reported, not adjudicated (stage 02 does not extract or grade claims)"
        },
        {
          "note_id": "N2",
          "kind": "internal_discrepancy_observed",
          "summary": "front matter ⑤ places the numbers on a loongarch64 control-plane host while appendix §6 says they come from the x86_64 control-plane host; §2 lists loongarch64 as the device",
          "locator_ids": [
            "D4",
            "D5"
          ],
          "disposition": "reported, not adjudicated; device identification is genuinely uncertain"
        },
        {
          "note_id": "N3",
          "kind": "structural_duplication_risk",
          "summary": "the front matter summarises the appendix: the deliverable described in ① is re-presented as the appendix timing table, and the appendix is introduced as programmatically generated — the same result therefore appears twice in one document, so a stage-03 extractor must deduplicate by value+context or it will double-count",
          "locator_ids": [
            "D6",
            "D7",
            "D8"
          ],
          "disposition": "reported as a downstream risk; this stage extracts nothing"
        }
      ],
      "parse_note_locators": [
        {
          "method": "char_span",
          "start_char": 1394,
          "end_char": 1403,
          "start_line": 15,
          "end_line": 15,
          "quote": "<0.01% 量级",
          "quote_sha256": "c489359422dd837d7226da881532dd32fac922808b0233c4e634f59004e90c2d",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "D1"
        },
        {
          "method": "char_span",
          "start_char": 2041,
          "end_char": 2053,
          "start_line": 28,
          "end_line": 28,
          "quote": "三参数点均 <0.01%",
          "quote_sha256": "0e8aac3b15b0d08d1d5365266494ce993fec5b2e64913f55d0fabfd608c1562d",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "D2"
        },
        {
          "method": "char_span",
          "start_char": 4897,
          "end_char": 4939,
          "start_line": 79,
          "end_line": 79,
          "quote": "| 0.6 | 0.03333333 | 0.03496079 | 4.8824 |",
          "quote_sha256": "df85175ad14be64f4eb0bfc5cb0cfd485b0ccd56ec2e83e276a83b01e3045a9f",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "D3"
        },
        {
          "method": "char_span",
          "start_char": 1688,
          "end_char": 1710,
          "start_line": 21,
          "end_line": 21,
          "quote": "来自控制面宿主（loongarch64 架构",
          "quote_sha256": "1fbf9140712a9a834dd2bd5376eff19d2b24606e0a0ed18abdabfbe2ae8fc7ac",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "D4"
        },
        {
          "method": "char_span",
          "start_char": 6565,
          "end_char": 6604,
          "start_line": 105,
          "end_line": 105,
          "quote": "come from the control-plane x86_64 host",
          "quote_sha256": "68d9974babc26e74f66ef3cc831373223f630b5d830693ad334de24a2b0493bf",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "D5"
        },
        {
          "method": "char_span",
          "start_char": 204,
          "end_char": 218,
          "start_line": 2,
          "end_line": 2,
          "quote": "墙钟/吞吐/峰值RSS 矩阵",
          "quote_sha256": "dc2daa1ddbdbe228ab8c9cc2ebc9c7aea37cdbf8999c9dcd025edeeec6829c74",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "D6"
        },
        {
          "method": "char_span",
          "start_char": 5286,
          "end_char": 5326,
          "start_line": 89,
          "end_line": 89,
          "quote": "Wall-clock / throughput table (variant B",
          "quote_sha256": "d8bb95e4d54b0471a52c3d5e53957c81922dc4302b3b17010ed0668c396ed805",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "D7"
        },
        {
          "method": "char_span",
          "start_char": 2126,
          "end_char": 2134,
          "start_line": 34,
          "end_line": 34,
          "quote": "程序化生成的表格",
          "quote_sha256": "744b2700a5c076acbd0b98580637b094a38d5f05a5e3cdb437abfc03089c088e",
          "resolvable": true,
          "occurrences": 1,
          "unique_in_source": true,
          "locator_id": "D8"
        }
      ],
      "uncertainty": {
        "preserved": true,
        "items": [
          "report_type is a refutable hypothesis (primary + alternative recorded)",
          "registry signals are literal-string matchers; a semantic match the phrase list does not cover is not counted",
          "the two internal discrepancies are flagged, never resolved by this stage"
        ]
      },
      "non_actions": {
        "claims_extracted": false,
        "assets_registered": false,
        "marked_verified": false,
        "other_reports_touched": false,
        "note": "objective.classify_report_type=true, register_assets=false; verification is the platform's gate"
      },
      "counts": {
        "sections": 19,
        "type_evidence_locators": 11,
        "topic_tags": 7,
        "parse_notes": 3,
        "parse_note_locators": 8
      }
    }
  }
}
```
