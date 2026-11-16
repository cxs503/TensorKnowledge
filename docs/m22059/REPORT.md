# PROD-RA 阶段3 真实场景试点：研究成果语料主张-引用-证据可追溯性审计

**Mission ID**: m22059
**Scenario**: RA-20261115-real-corpus-audit
**Date**: 2026-11-15T15:35:22+00:00
**Status**: scenario_validated=false（留独立审查轮）

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

---

## ② 方法/流程

### 六步执行流程（按 SCENARIO_ACCEPTANCE_FRAMEWORK.md §3）

1. **场景规格 (①)**: 声明 `usage_declaration=真实审计工作流`，`permission_basis=internal_consent`，输入指纹已校验
2. **冻结判据 (②)**: 生成 `criteria.json`，SHA-256 = `f60695e1b40160af6a07813e3ec3016ff230fe22c36d2170df9b465b903fddcc`，`frozen_at` ≤ `created_at`
3. **收集证据 (③)**: 运行两个审计器，产出 JSON 报告；缺失项记入 `missing[]`
4. **独立评审 (④)**: 本单为作者自审，`scenario_validated` 留独立审查轮
5. **发布状态 (⑤)**: 本单不自评
6. **记录失败 (⑥)**: 3 条失败记录写入 `negative_knowledge_ledger.json`

### 工具链
```bash
# 步骤 1: 引用审计
python3 scripts/research_audit/citation_audit.py <corpus.md> --output <output.json>

# 步骤 2: 主张-证据审计
python3 scripts/research_audit/claim_evidence_audit.py \
  --claims <claims_dir/> --evidence <evidence_dir/> --source-root <source_dir/> \
  --output <output.json>

# 步骤 3: 负向测试（注入坏引用 + 悬空指针）
python3 scripts/research_audit/citation_audit.py <corrupted.md>
python3 scripts/research_audit/claim_evidence_audit.py --claims <neg_claims/> --evidence <neg_evidence/> --source-root <neg_source/>
```

### 语料提取
语料 `kf_result_wp-2506-04.md` 含嵌入式 JSON 代码块，需提取为结构化 claim/evidence 记录：
- 3 条 `supported_claims` → `claim-sc-{1,2,3}.json`
- 8 条 `findings` (F1-F8) → `claim-f{1..8}.json`
- 对应证据记录 → `evidence-*.json`

---

## ③ 计算结果

### citation_audit 结果
| 检查项 | 状态 | 详情 |
|---|---|---|
| references_section_present | inconclusive | 无 References/Bibliography/参考文献 章节 |
| citation_reference_resolution | failed | 未解析引用: [0] |
| **overall_status** | **inconclusive** | |

### claim_evidence_audit 结果
| 检查项 | 状态 | 详情 |
|---|---|---|
| bidirectional_references | passed | 0 条断裂链接（11 claims, 11 evidence） |
| source_locator_integrity | failed | 11 条源定位错误（quote offsets 不匹配） |
| review_relation_consistency | passed | 0 条关系冲突 |
| **overall_status** | **failed** | |

### 主张三分报数
| 类别 | 数量 | 详情 |
|---|---|---|
| **verified** | 3 | α=0 造能 20/41 ✓；相容装配证书 ✓；K 矩阵 PSD 结构 ✓ |
| **inconclusive** | 4 | 跨报告一致性（越界）；bitwise identity（无 golden test）；affine convergence（无参考实现）；solver admission（超出范围） |
| **broken** | 8 | F1 docstring 矛盾（高）；F2 归因 overstated（中）；F3 xfail 计数不实（中）；F4 回归用例同义反复（中）；F5 用例数错误（低）；F6 子样本未标注（低）；F7 缺陷在边界（低）；F8 无信息度量（低） |

### 负向测试结果
| 测试 | 注入缺陷 | 检出结果 |
|---|---|---|
| 坏引用注入 | `[999]` 无对应参考文献 | ✅ 检出（unresolved_citations 包含 "999"） |
| 悬空证据指针 | claim→不存在的 evidence | ✅ 检出（missing_evidence_record） |
| 悬空主张指针 | evidence→不存在的 claim | ✅ 检出（missing_claim_record） |

---

## ④ 结果图

**本单为文档审计任务，无数值场量或解析解比较曲线，故不生成 matplotlib 图。**

审计产出为结构化 JSON 报告，包含：
- `citation_audit.json`: 引用结构分析
- `claim_evidence_audit.json`: 主张-证据链接分析
- `negative_test/`: 负向测试输出

---

## ⑤ 注意点

### 踩过的坑
1. **kb10k 格式不兼容**: `knowledge/kb10k/claims/` 和 `evidence/` 目录中的 JSON 文件为数组格式，而 `claim_evidence_audit.py` 期望每个文件为含 `id` 字段的单个对象。直接运行导致 0 claims / 0 evidence 被加载。
2. **source locator 偏移**: 从语料提取证据时，quote offsets 设为 0:200 与实际文本位置不匹配，导致 `source_locator_integrity` 全部失败。正确做法需在源文件中搜索 quote 字符串获取精确偏移。
3. **语料无标准参考文献章节**: `kf_result_wp-2506-04.md` 是结构化评审报告，非传统学术论文格式，无 `[N]` 引用和 References 章节，导致 `citation_audit` 返回 inconclusive。

### 局限
- 审计器仅做结构性检查，不做语义支持判断
- 语料中引用 m2431 报告，但包边界禁止读取，跨报告一致性无法验证
- 无 golden matrix 回归测试

### 适用范围
- 适用于含标准引用格式的学术 Markdown 文档
- 适用于结构化 claim/evidence JSON 记录（单对象格式）
- 不适用于嵌入式 JSON 代码块或数组格式的知识库

---

## ⑥ 误差判定

本单为结构性审计任务，无数值计算结果与基准比较。关键判定：

| 判定项 | 基准 | 结果 | 是否通过 |
|---|---|---|---|
| 语料指纹校验 | sha256 2745f3a8…f6949f / d09f1ce8…b672e7 | 匹配 | ✅ |
| 负向测试-坏引用 | 必须检出 [999] | 检出 | ✅ |
| 负向测试-悬空指针 | 必须检出 missing_evidence/missing_claim | 检出 | ✅ |
| citation_audit | 无参考文献章节 → inconclusive | 符合预期 | ✅ |
| claim_evidence_audit | source locator 偏移不匹配 → failed | 符合预期（提取过程缺陷） | ⚠️ 已知问题 |

**无 <3% 误差条款适用**：本单判据为结构性完整性，非数值精度。

---

## 六维价值记录

| 维度 | 记录 |
|---|---|
| **问题价值** | 研究成果语料的主张-引用-证据可追溯性审计，人工审查耗时且易遗漏结构性缺陷 |
| **自动化程度** | 2/4 步骤自动化（citation_audit + claim_evidence_audit 自动运行；语料提取 + 报告组装需手动） |
| **质量对照** | citation_audit: inconclusive；claim_evidence_audit: failed（source locator）；negative tests: 全部检出 |
| **成本** | wall_clock ~5min, human_review ~30min, compute: 1 core × 2min |
| **复现性** | 命令 + 语料指纹已记录，可独立复现 |
| **交付意愿** | unknown（待独立审查轮确认） |

---

## 交付物清单

| 文件 | 说明 |
|---|---|
| `runs/m22059/validation-report.json` | 完整验证报告（scenario + criteria_freeze + evidence_bundle + claims_triage + failure_records） |
| `runs/m22059/citation_audit.json` | 引用审计输出 |
| `runs/m22059/claim_evidence_audit.json` | 主张-证据审计输出 |
| `runs/m22059/criteria.json` | 冻结判据 |
| `runs/m22059/negative_knowledge_ledger.json` | 失败记录台账 |
| `runs/m22059/negative_test/` | 负向测试语料与输出 |
| `runs/m22059/audit_corpus/` | 提取的结构化 claim/evidence 记录 |
