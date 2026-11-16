# PROD-RA 阶段3 真实场景试点：研究成果语料主张-引用-证据可追溯性审计

**Mission ID**: m22059（阶段3 试点） / m22760（阶段3 返修，修 m22508 审查回执 D1–D12）
**Scenario**: RA-20261115-real-corpus-audit
**Date**: 2026-11-16T02:21Z（返修轮；首轮 2026-11-15T15:35:22Z）
**Status**: `scenario_validated=false` —— 留独立审查轮。本单是作者席返修，不自评通过。

> **返修声明（honest-FAIL 结构）**：首轮独立审查（`docs/review_m22059_prod_ra/REVIEW-RECEIPT.json`, verdict=`changes_requested`）
> 判定六查中 ②③⑤ 触阻断条件。本轮**只修回执所列缺陷，不扩大范围、不重构、不加功能**。
> 首轮的数字与结论不被美化：首轮 `claim_evidence_audit` 报 11 条源定位错误、`claim-f1` 绑零长度证据、
> 判据哈希在契约函数下不可解析 —— 这些都是真实缺陷，本轮逐条修复并把**修掉了什么、改变了什么数**写在 ③ 与对照表里。
> 缺陷逐条对照（D1–D12，文件:行 + 验证方式）见 `docs/review_m22059_prod_ra/REPAIR-NOTES.md`。

---

## ① 案例介绍

### 物理背景
本单审计对象为 TensorFVM 粘性耗散性独立评审报告（wp-2506-04），涉及非正交网格上粘性算子装配的耗散性证书问题。核心物理量：

| 量 | 含义 | 基准值 |
|---|---|---|
| E (耗散率) | 负值=耗散，正值=产能 | 应 ≤ 0 |
| λmin(K) | 相容装配矩阵最小特征值 | 应 > 0 |
| skew | 网格偏斜度 [0,1] | 41 点扫掠 |

### 语料输入
| 文件 | SHA-256 | 角色 |
|---|---|---|
| `work/wp-2506-04/kf_result_wp-2506-04.md` | `2745f3a8…f6949f` | 主评审报告（含 8 条分级发现、3 条支持项、4 条未跑检查） |
| `EVIDENCE.md` | `d09f1ce8…b672e7` | 任务证据摘要 |

### 审计范围
- **citation_audit.py v0.1.0**: 数字引用/参考文献结构一致性（不做语义判断）
- **claim_evidence_audit.py v0.2.0**: 主张-证据双向链接、源路径约束、精确引用偏移与哈希校验

### 判据来源（D2 修复后）
判据不再转写审计器自身的 check_id，而是从契约仓抄录（`runs/m22059/criteria.json`，`criteria_version=1.1.0`）：

| 来源 | 条款 | 判据 id |
|---|---|---|
| `TensorBench:docs/FOUR_PRODUCT_ACCEPTANCE_MATRIX.md#L21` | Audit one permissioned report, bibliography and source bundle; retain reviewer receipt. | RA-PILOT-SCOPE |
| `…#L15` | A passing unit-test suite never upgrades a product to real_world_verified. Missing or unsupported evidence is inconclusive, never a pass. | RA-NO-UPGRADE |
| `…#L38–L45` | 验收记录必留字段（输入指纹与源定位 / 版本与配置 / 判据与适用性假设 / 调用与环境 / 原始输出含失败与跳过 / findings 带证据与三态 / 评审者身份角色决定时间理由 / 有 holdout 时的指标） | RA-RECORD-* (8 条) |
| `TensorBench:products/research-audit/PRD.md#L34` | every finding must resolve to a source span or be explicitly marked as a heuristic prompt | RA-SOURCE-SPAN |
| `…#L34` | citation metadata precision ≥0.98；support classification macro-F1 ≥0.80 | RA-CITATION-PRECISION / RA-SUPPORT-F1（**not_measured**，见 ⑥） |
| `…#L35` | Human reviewers can reproduce each finding from the cited source. | RA-REPRODUCIBLE-FINDINGS |
| `…#L36` | Any unresolvable extraction or unavailable source is `inconclusive`, never silently passed. | RA-INCONCLUSIVE |

审计器 check_id 与判据的对应关系单独放在 `check_mapping`（映射，不是判据本体）。

---

## ② 方法/流程

### 执行流程（按 SCENARIO_ACCEPTANCE_FRAMEWORK.md §3）

1. **场景规格 (①)**: `usage_declaration=真实审计工作流`，`permission_basis=internal_consent`，输入指纹已校验
2. **冻结判据 (②)**: `criteria.json` v1.1.0，`criteria_sha256 = 0808bd1c459cc3934d4b32f9dc7fd613bf03aed87981c855c99c697083e8e947`，口径 `tensorbench.criteria.canonical_sha256`，`frozen_at = 2026-11-16T02:20:12Z`；其后所有审计输出 `created_at = 02:20:18–02:20:19Z`（**冻结先于本轮输出，1 条时间线，不倒填**）
3. **收集证据 (③)**: 两个审计器实跑；证据条目按 `TensorBench:schemas/evidence-item.schema.json` 逐条构造并经 jsonschema 校验；缺失项入 `missing[]`
4. **独立评审 (④)**: 首轮回执已存在（`changes_requested`）；本轮为返修，`scenario_validated` 仍留独立审查轮
5. **发布状态 (⑤)**: 本单不自评
6. **记录失败 (⑥)**: `negative_knowledge_ledger.json` 3 条记录，按框架 §5 字段表逐条补齐（含 evidence_refs 的 sha256 与 repro_cmd 的 commit SHA）

### 工具链
```bash
# 步骤 1: 引用审计（input_refs 现记录仓内可移植指针，D7）
python3 scripts/research_audit/citation_audit.py work/wp-2506-04/kf_result_wp-2506-04.md \
  --output runs/m22059/citation_audit.json                       # exit 1 (inconclusive)

# 步骤 2: 主张-证据审计
python3 scripts/research_audit/claim_evidence_audit.py \
  --claims runs/m22059/audit_corpus/claims \
  --evidence runs/m22059/audit_corpus/evidence \
  --source-root runs/m22059/audit_corpus/source \
  --output runs/m22059/claim_evidence_audit.json                 # exit 0 (passed)

# 步骤 3: 负向测试（注入坏引用 + 悬空指针），检出即 exit≠0
python3 scripts/research_audit/citation_audit.py runs/m22059/negative_test/corpus/kf_result_bad.md \
  --output runs/m22059/negative_test/citation_audit_negative.json                          # exit 1
python3 scripts/research_audit/claim_evidence_audit.py \
  --claims runs/m22059/negative_test/claims --evidence runs/m22059/negative_test/evidence \
  --source-root runs/m22059/negative_test/source \
  --output runs/m22059/negative_test/claim_evidence_audit_negative.json                    # exit 1

# 步骤 4: 本仓回归
python3 -m pytest tests -q --continue-on-collection-errors      # 见「回归范围」
```

### 语料提取与证据定位（D3/D4 修复）
语料 `kf_result_wp-2506-04.md` 含嵌入式 JSON 代码块，需提取为结构化 claim/evidence 记录：
- 3 条 `supported_claims` → `claim-sc-{1,2,3}.json`；8 条 `findings` (F1–F8) → `claim-f{1..8}.json`
- 对应证据记录 11 条 → `evidence-*.json`

**返修做法**：11 条 evidence 的 `start_offset/end_offset` 不再沿用上游抽取的 `0:200` 默认值，而是**在源文件中定位 quote 原文**（`text.find(quote)`，命中后取 `start..start+len(quote)`）并重算 `content_hash = sha256(quote)`；`claim-f1` 的零长度证据改为绑定语料自身 F1 信封块（`"type": "code/docstring contradicts report"` … `"report_contradicts"` 行，源偏移 11975–12385）。偏移与哈希由审计器独立回切片复核，不是自证。

---

## ③ 计算结果

### citation_audit 结果（exit 1）
| 检查项 | 状态 | 详情 |
|---|---|---|
| references_section_present | inconclusive | 无 References/Bibliography/参考文献 章节 |
| citation_reference_resolution | failed | 未解析引用: [0] |
| **overall_status** | **inconclusive** | |

`input_refs = ["work/wp-2506-04/kf_result_wp-2506-04.md"]`（首轮记录的是 `/srv/tensor/agent/work/m19455/...`，该路径已不存在 —— D7）。

### claim_evidence_audit 结果（exit 0）
| 检查项 | 状态 | 详情 |
|---|---|---|
| bidirectional_references | passed | 0 条断裂链接（11 claims, 11 evidence） |
| source_locator_integrity | passed | **0 条源定位错误**（11 条 evidence 的 quote 在声明偏移处逐字节命中，且 sha256(quote)=content_hash） |
| review_relation_consistency | passed | 0 条关系冲突；0 条未评估 |
| **overall_status** | **passed** | counts: claims 11 / evidence 11 / pending_review 0 |

**与首轮的差异（必须解释）**：首轮 `overall_status=failed`、`findings=11`，全部是 `quote_offset_mismatch`；本轮 `failed→passed`、`findings=11→0`，原因是证据偏移按源文实测重写（D4），**不是**放宽判据或改审计器判定逻辑（`scripts/research_audit/claim_evidence_audit.py` 的检查逻辑本轮未改）。首轮另外 10 条 quote 文本正确但偏移错误（因抽取时统一写 `start=0`），1 条（claim-f1）quote 为空串（`sha256("")=e3b0c442…`），本轮一并修掉。

### 主张三分报数（分母已显式说明，D12）
| 类别 | 数量 | 详情 |
|---|---|---|
| **verified** | 3 | α=0 造能 20/41 ✓；相容装配证书 ✓；K 矩阵 PSD 结构 ✓ |
| **inconclusive** | 4 | 跨报告一致性（越界不可读）；bitwise identity（无 golden test）；affine convergence（无参考实现）；solver admission（超出范围） |
| **broken** | 8 | F1 docstring 矛盾（高）；F2 归因 overstated（中）；F3 xfail 计数不实（中）；F4 回归用例同义反复（中）；F5 用例数错误（低）；F6 子样本未标注（低）；F7 缺陷在边界（低）；F8 无信息度量（低） |

**分母**：3+4+8=15 条 triage 条目，语料只有 11 条 claim 记录 —— 差额 4 条是 `check-*`（cross-report / bitwise / affine / solver），它们是被审报告的"未跑检查"清单项，从未抽取为 claim 记录。三分报数按 **triage 条目**统计（不是按 claim 记录），机读字段见 `validation-report.json#claims_triage_summary`。

### 负向测试结果（exit code 语义，D9）
| 测试 | 注入缺陷 | 检出 | 正向 exit | 负向 exit | 判别层级 |
|---|---|---|---|---|---|
| 坏引用注入 | `[999]` 无对应参考文献 | ✅ `unresolved_citations=['0','999']`（正向 `['0']`，finding 2→3） | 1 | 1 | **finding 级**（status 两侧同为 inconclusive：语料无参考文献章节，status 天然退化） |
| 悬空指针注入 | claim→不存在 evidence；evidence→不存在 claim | ✅ `missing_evidence_record` + `missing_claim_record`，且 0 条附带 finding | 0 | 1 | **status 级**（passed → failed） |

**返修点**：负向语料里被复制过来的 evidence 记录原本也带着 `0:200` 旧偏移和错误文件名，会产生 `quote_offset_mismatch`/`source_file_missing` 噪声，使"检出"与"噪声"混在一起；本轮把负向语料也按真实偏移校正，负向运行只剩**恰好两条**注入缺陷（附带 finding = 0），判别力可归因。审计器退出码：检出缺陷时 exit≠0（两条负向均 1），干净语料 exit=0。

---

## ④ 结果图

**本单为文档/证据链审计任务，无数值场量云图、无与解析解/文献的比较曲线，故不生成 matplotlib 图。**
（审计产出是结构化 JSON：`citation_audit.json`、`claim_evidence_audit.json`、`negative_test/*.json`；其"曲线"意义不存在，
强行画图只会把非数值结果包装成图形证据 —— 按报告纪律声明理由而非造图。）

---

## ⑤ 注意点

### 踩过的坑（含本轮修掉的）
1. **kb10k 格式不兼容**（未修，记为 gap）：`knowledge/kb10k/claims/`、`evidence/` 为 JSON 数组格式，审计器期望"单对象 + `id` 字段"，直接跑会 0 claims / 0 evidence 加载。
2. **source locator 偏移（首轮缺陷 D4，已修）**：语料抽取时 quote offsets 统一写成 `0:200`，与源文实际位置不符 → `source_locator_integrity` 11/11 失败。返修按源文定位 quote 取得真实偏移（例如 evidence-f2 = 2992–3139、evidence-review-1 = 19951–20071），并重算 `content_hash`。
3. **零长度证据（首轮缺陷 D3，已修）**：`claim-f1`（高）只绑 `quote=""`、`content_hash=sha256("")` 的 `evidence-f1`，无法检索。返修绑定到语料 F1 信封块原文。
4. **判据哈希口径（首轮缺陷 D1/D2/D8，已修）**：首轮 `criteria_sha256` 用的是 `sha256(json.dumps(indent=2))`，在 `tensorbench.criteria.canonical_sha256` 下不可解析；且判据四键转写自审计器 check_id、缺 PRD 的 source-span 条款；`frozen_at == created_at` 且晚于首轮输出 2m16s，冻结"先于运行"不可证。返修：判据重新从矩阵/PRD 抄录、按 canonical_sha256 冻结，冻结时戳只在**本轮**声称先于本轮输出，首轮时间线如实留档（`validation-report.json#criteria_freeze.superseded_timeline`）。
5. **语料无标准参考文献章节**：`kf_result_wp-2506-04.md` 是结构化评审报告，无 `[N]` 引用与 References 章节 → `citation_audit` 天然 inconclusive（这是正确行为，不是本次可修的缺陷）。

### 局限
- 审计器仅做结构性检查（链接/路径/偏移/哈希/关系状态），**不做语义支持判断**；`verified/inconclusive/broken` 三分是人工分级，不是审计器输出
- 语料引用 m2431 报告，包边界禁止读取，跨报告一致性无法验证（inconclusive，不判 pass）
- 无 golden matrix 回归测试（`check-bitwise` 只能用 diff 复核）
- 本轮未做独立复跑：返修结果只有作者席自证，`scenario_validated` 仍为 false

### 适用范围
- 适用于含标准引用格式的学术 Markdown 文档
- 适用于结构化 claim/evidence JSON 记录（单对象格式）
- 不适用于嵌入式 JSON 代码块或数组格式的知识库

---

## ⑥ 误差判定（关键量 vs 基准，逐项显式回答）

本单为结构性审计任务，无数值解析解。基准 = 契约条款与注入缺陷的真值。

| 判定项 | 基准 | 结果 | 误差 | 是否 <3% |
|---|---|---|---|---|
| 语料指纹校验 | `2745f3a8…f6949f` / `d09f1ce8…b672e7` | 逐位匹配（0 差异） | 0 | ✅ 0% |
| 证据源定位（11 条） | 源文 `[start:end]` 必须逐字节等于 quote | 11/11 命中；sha256(quote) 与 content_hash 11/11 一致 | 0/11 失配 | ✅ 0% |
| claim-f1 可检索性 | 非零长度证据 + 命中源文 | 11975–12385，410 字符，命中 | — | ✅（首轮不可检索 → 现可检索） |
| 负向测试-坏引用 | 必须检出 `[999]` | 检出（`unresolved=['0','999']`），exit 1 | 0/1 漏 | ✅ 0% |
| 负向测试-悬空指针 | 必须检出 missing_evidence + missing_claim | 检出，附带 finding 0 条，exit 1 | 0/2 漏 | ✅ 0% |
| citation_audit 判定 | 无参考文献章节 ⇒ inconclusive | inconclusive（合规） | — | ✅（三态语义正确） |
| claim_evidence_audit 判定 | 结构与源定位全通过 ⇒ passed | passed（0 findings，exit 0） | — | ✅（首轮 failed 系证据偏移缺陷所致，已修） |
| 判据冻结合规 | `canonical_sha256(criteria.json)` 必须等于声明值 | `0808bd1c…e947` 复算一致 | 0 | ✅ 0% |
| **RA-CITATION-PRECISION（≥0.98）** | 契约指标 | **not_measured**：语料无参考文献章节，零条引用可解析，精度在本次语料上无定义 | — | ❓ **无法判定，不宣称通过** |
| **RA-SUPPORT-F1（≥0.80）** | 契约指标 | **not_measured**：无 ≥100 对带标签 holdout；两审计器均不做语义判定 | — | ❓ **无法判定，不宣称通过** |

**结论**：可比的量（指纹、偏移、哈希、负向检出、判据哈希）全部 <3%（实际 0 差异）；两条契约标度指标因缺 holdout/无参考文献章节而 `not_measured`，按矩阵 L15 "missing evidence is inconclusive, never a pass" 不放行，也不含糊修饰。

---

## 回归范围（D10）

| 项 | 内容 |
|---|---|
| 变更面 | 见 `runs/m22059/regression-scope.json#changed_paths`（`scripts/research_audit/citation_audit.py` + `tests/test_research_audit_citations.py` + `runs/m22059/**`） |
| 审计器单测 | `python3 -m pytest tests/test_research_audit_citations.py tests/test_research_audit_claim_evidence.py -q` → **12 passed**（首轮 11，本轮 +1 覆盖 `input_refs` 可移植性） |
| 全量套件 | `python3 -m pytest tests -q --continue-on-collection-errors` → 见 `runs/m22059/regression-scope.json#full_suite`（3135 collected + 1 个既有 collection error：`tests/test_kf_wp11107_01.py` 缺文件，首轮同基线已存在） |
| 检查未跑 | 无独立复跑（评审席未介入）；集群全量执行若未返回，如实记 `not_run`，不冒充分数 |

---

## 六维价值记录（框架 §6）

| 维度 | 记录 |
|---|---|
| **问题价值** | 研究成果语料的主张-引用-证据可追溯性审计，人工审查耗时且易遗漏结构性缺陷；本单决定"一条 finding 能否作为可复现结论被引用" |
| **自动化程度** | 6 步中 3 步自动（两个审计器 + 负向复跑），3 步人工（语料抽取 / 语义三分 / 报告组装）→ `auto_steps/total_steps = 3/6` |
| **质量对照** | 判据 15 条：pilot_gate 12/12 通过，calibrated_gate 3 条 not_measured（无 holdout / 无参考文献章节）。命中率：偏移失配 0/11、悬空指针漏检 0/2、坏引用漏检 0/2；语料自身缺陷 8/11 条被标记。无人工基线可比 |
| **成本** | 审计器 4 次调用 ≈7 s（02:20:12 冻结 → 02:20:18–19 输出）；全量测试递交集群 `cj4351`（4 核，回执见 `regression-scope.json`）；作者返修会话人工分钟与计算分钟**记 unknown**，不估造 |
| **复现性** | 命令 + 语料指纹 + commit 已记录（`regression-scope.json#verified_at_commit`）；审计器确定性，仅 `created_at` 每次不同；本轮独立复跑`not_run` |
| **交付意愿** | unknown（等独立审查轮） |

---

## 交付物清单

| 文件 | 说明 |
|---|---|
| `runs/m22059/validation-report.json` | 完整验证报告（scenario + criteria_freeze + evidence_bundle + claims_triage + negative_test_results + failure_records + value） |
| `runs/m22059/citation_audit.json` | 引用审计输出（exit 1 / inconclusive） |
| `runs/m22059/claim_evidence_audit.json` | 主张-证据审计输出（exit 0 / passed） |
| `runs/m22059/criteria.json` | 冻结判据 v1.1.0（含 amendments / supersedes） |
| `runs/m22059/negative_knowledge_ledger.json` | 失败记录台账（§5 字段齐备） |
| `runs/m22059/regression-scope.json` | 回归范围与执行回执（变更面 / 单测 / 全量 / 未跑项 / commit） |
| `runs/m22059/negative_test/` | 负向测试语料与输出（含 exit code 语义） |
| `runs/m22059/audit_corpus/` | 提取的结构化 claim/evidence 记录（11+11，偏移为源文实测值） |
| `docs/review_m22059_prod_ra/REPAIR-NOTES.md` | D1–D12 逐条对照表（改了什么文件什么行、怎么验证的） |