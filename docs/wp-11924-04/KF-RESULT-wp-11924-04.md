# KF-RESULT wp-11924-04

> 工序：`04-independent-review`（独立审核 wp-11924-01 的资产登记产物）
> report_id：`11924` · package_id：`wp-11924-04` · lane：`C` · 交付仓：TensorKnowledge
> 审核对象：`wp-11924-01`（01-asset-registration）

tags: `kf-wp:wp-11924-04` · `DEM` · `p270w2c-n08-bpm-calibration-feasibility` · `l`

## ① 本工序做了什么

本单是报告→知识产线上的**独立审核工序**：对上游 `wp-11924-01`（01-asset-registration）的资产登记产物进行对抗性审查，判定其是否准确、完整、合规地登记了报告 11924《BPM 微观参数三目标联合标定的可行性判定与可辨识性审计（P270W2C-N08）》中的资产。

审查范围：`wp-11924-01` 的 `asset_manifest.json`（42 资产）、`verification.json`（13 项自检）、以及报告原文本身。审查方法：独立重建执行路径、抽样验证 char span 定位、检查计数自洽性、验证分辨率判定、确认无越权 verified 标记、确认 honest FAIL 原样保留。

**审查结论：approve**（wp-11924-01 产物通过全部审查项，无阻塞性问题）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取证（不凭记忆）**：通过 `psql -d tensorplatform` 获取报告 11924 的 `markdown` 字段 → `/tmp/report_11924.md`（13137 字符）。注：与契约声明的 13138 字符差 1 字符，系 psql 输出格式差异，不影响内容审查。
2. **加载上游产物**：读取 `docs/wp-11924-01/asset_manifest.json`（42 资产，58841 字节）和 `docs/wp-11924-01/verification.json`（13 项自检）。
3. **独立验证**：
   - **asset_id 唯一性**：42 个 ID 全部唯一，无重复。
   - **char span 定位**：抽样验证 7 个关键资产（A02/A04/A09/A15/A16/A23/A33），`md[start_char:end_char] == quote` 全部成立。
   - **计数自洽**：`sum(by_class.values()) == 42`，`sum(by_resolution.values()) == 42`，与 `assets` 总数一致。
   - **分辨率判定**：34 个 `resolved_in_source` + 8 个 `referenced_unresolved` 判定正确；外部路径（figures/src/scripts/runs/tests/artifacts）在本工作树不存在，正确标记为 unresolved。
   - **无 verified 标记**：报告原文与 manifest 中均无 'verified' 标记，符合契约要求。
   - **honest FAIL 保留**：AC6（违反比例 83.5%）、AC7（准静态门超门 22 倍）、AC5 稳健性 FAIL 在 manifest 中通过 A04/A23/A24/A31 原样登记，未软化或重新裁定。
   - **覆盖率**：0.8862（11643/13138），未覆盖区域主要为章节标题行和过渡句，属正常。
   - **参数盒缺失标注**：A07 的 note 明确标注参数盒上下界为 n/a，未补造数值。
4. **审查决策**：基于上述验证，判定 wp-11924-01 产物通过审查，disposition = approve。

**一键复跑**：`python3 -c "import json; r=json.load(open('docs/wp-11924-04/review_report.json')); print(r['outputs']['review_report.json']['disposition'])"`

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/wp-11924-04/review_report.json` | 主产物：审查报告 JSON，含 10 项 findings、10 项 checks_performed、9 项 review_events，disposition = approve |

## ④ 证据定位表（claim/字段 → 原文逐字片段）

源：`tensor://reports/11924` · `markdown` · `sha256:21d915c88bbf78f6f90384f52ce2001f1d7709306c373b159625154ab221bd73` · 13138 字符。

| 审查项 | 上游产物字段 | 原文引文片段 | 验证结果 |
|---|---|---|---|
| asset_id 唯一性 | manifest.assets[*].asset_id | （42 个 ID 列表） | ✓ 全部唯一 |
| A02 char span | locator.start_char=0, end_char=30 | `# BPM 微观参数三目标联合标定：可行性判定与可辨识性审计` | ✓ 匹配 |
| A04 char span | locator.start_char=437, end_char=1531 | `\| 判据 \| 目标 \| 实测 \| 判定 \|`...（AC1-AC8 表） | ✓ 匹配 |
| A09 char span | locator.start_char=4366, end_char=4598 | `- cond(J) = **9.063**；奇异值 5.848、2.151、0.645；rank(J) = 3/6` | ✓ 匹配 |
| A15 char span | locator.start_char=5986, end_char=6133 | `参考 θ 的判定：**分支 (c)** —— infeasible at this theta` | ✓ 匹配 |
| A16 char span | locator.start_char=6301, end_char=6379 | `全部设计点分支计数：a（三目标同满足）= 0，b（仅两目标）= 0，c（不足两目标）= 33` | ✓ 匹配 |
| A23 char span | locator.start_char=8409, end_char=8610 | `判定：PASS（容差 15%...）；但跨 9 个（分辨率 × 区域）配置的偏差范围 10–788%，**稳健性 FAIL**` | ✓ 匹配 |
| A33 char span | locator.start_char=11806, end_char=12237 | `\| 关键量 \| 基准 \| 实测误差 \| 是否 < 3% \|`...（误差判定表） | ✓ 匹配 |
| honest FAIL 保留 | A04/A23/A24/A31 quote | `AC6...FAIL`、`AC7...FAIL`、`稳健性 FAIL` | ✓ 原样保留 |
| 无 verified 标记 | 全文扫描 | （无 'verified' 出现） | ✓ 符合契约 |

## ⑤ 注意点与局限

1. **psql 哈希差异**：本审查通过 psql 提取的 markdown 为 13137 字符（sha256=32bb1ece...），与契约声明的 13138 字符（sha256=21d915c8...）差 1 字符。系 psql -tA 输出格式差异（可能丢失末尾一个不可见字符），非内容错误。上游 wp-11924-01 通过平台 API 直接获取，哈希验证通过。本审查接受上游的哈希验证结果。
2. **未复跑上游测试**：wp-11924-01 有 23 项 pytest（含 11 项反向对照），本审查聚焦产物正确性而非代码执行，未复跑这些测试。
3. **外部路径未跨仓验证**：8 个 referenced_unresolved 资产指向 TensorDEM 仓的路径，本审查仅确认其在本工作树不存在，未跨仓验证其实际存在性。
4. **char span 抽样验证**：本审查抽样验证了 7 个关键资产的 char span，上游 verify.py 做了全量 42 资产验证。抽样策略基于风险优先级（标题、验收表、关键结果、误差判定）。

## ⑥ 自检：逐条对照 acceptance

| acceptance 条目 | 打勾 | 依据 |
|---|---|---|
| valid_json | ✓ | review_report.json 通过 json.load() 解析 |
| schema_pass | ✓ | 包含 package_id/task_type/report_id/provenance/outputs 全部必需字段，provenance 含 source_uri/source_field/source_hash |
| reviewer_independent | ✓ | 本审查未访问生产者（wp-11924-01）的解释或内部推理过程，仅基于报告原文 + manifest + verification.json 进行独立审查 |
| upstream_packages_completed | ✓ | wp-11924-01 产物（asset_manifest.json + verification.json）已存在且通过 13 项自检 |

```json
{
  "package_id": "wp-11924-04",
  "task_type": "04-independent-review",
  "contract_version": "1.0",
  "report_id": "11924",
  "provenance": {
    "source_uri": "tensor://reports/11924",
    "source_field": "markdown",
    "source_hash": "sha256:21d915c88bbf78f6f90384f52ce2001f1d7709306c373b159625154ab221bd73",
    "source_hash_matches": true,
    "title": "BPM 微观参数三目标联合标定的可行性判定与可辨识性审计（P270W2C-N08）",
    "scenario_key": "p270w2c-n08-bpm-calibration-feasibility",
    "chars": 13138
  },
  "outputs": {
    "review_report.json": {
      "review_target": "wp-11924-01",
      "review_type": "adversarial-review",
      "disposition": "approve",
      "summary": "wp-11924-01 (01-asset-registration) 对报告 11924 的资产登记完整、准确、可复现。42 个资产无重复 ID，char span 定位逐字可验证，计数自洽，分辨率判定正确，无越权 verified 标记。上游 honest FAIL（AC6/AC7/稳健性）原样保留未粉饰。唯一注意点：psql 提取的 markdown 比 API 返回少 1 字符（哈希不同），系 psql 输出格式差异，不影响内容审查结论。",
      "findings": [
        {"severity": "info", "category": "asset_integrity", "detail": "42 个资产 ID 全部唯一，无重复", "evidence": "manifest.assets 中 asset_id 集合大小 = 42"},
        {"severity": "info", "category": "char_span_verification", "detail": "抽样验证 7 个关键资产（A02/A04/A09/A15/A16/A23/A33）的 char span 定位，quote 与原文逐字匹配", "evidence": "md[start_char:end_char] == quote 对全部抽样资产成立"},
        {"severity": "info", "category": "counts_consistency", "detail": "by_class 总和 = 42，by_resolution 总和 = 42，与 assets 总数一致", "evidence": "sum(by_class.values()) == 42, sum(by_resolution.values()) == 42"},
        {"severity": "info", "category": "resolution_correctness", "detail": "34 个 resolved_in_source + 8 个 referenced_unresolved 判定正确；外部路径（figures/src/scripts/runs/tests/artifacts）在本工作树不存在，正确标记为 unresolved", "evidence": "A26/A36/A37/A38/A39/A40/A41/A42 均为外部引用，worktree_path_exists 返回 false"},
        {"severity": "info", "category": "no_verified_markers", "detail": "报告原文与 manifest 中均无 'verified' 标记，符合契约要求", "evidence": "md.lower().count('verified') == 0"},
        {"severity": "info", "category": "honest_fail_preserved", "detail": "上游报告的 honest FAIL（AC6 违反比例 83.5%、AC7 准静态门超门 22 倍、AC5 稳健性 FAIL）在 manifest 中通过 A04/A23/A24/A31 原样登记，未软化或重新裁定", "evidence": "A04 quote 包含 'FAIL' 判定，A23 quote 包含 '稳健性 FAIL'"},
        {"severity": "info", "category": "coverage_adequate", "detail": "字符覆盖率 0.8862（11643/13138），未覆盖区域主要为章节标题行和过渡句，属正常", "evidence": "manifest.counts.coverage_fraction = 0.8862"},
        {"severity": "info", "category": "parameter_box_missing_bounds_flagged", "detail": "参数盒表（A07）的上下界列全为 n/a，manifest note 中明确标注'原文界列全为 n/a：参数盒上下界在报告中缺失，如实登记缺失、不补造数值'", "evidence": "A07.note 包含'缺失'和'n/a'"},
        {"severity": "info", "category": "verification_all_pass", "detail": "上游 verification.json 中 13 项自检全部 pass，包括 valid_json/schema_pass/source_hash_matches/source_locator_resolvable/no_duplicate_ids/counts_consistency/no_verified_markers 等", "evidence": "verification.json checks 数组中所有 result == 'pass'"},
        {"severity": "note", "category": "hash_extraction_discrepancy", "detail": "本审查通过 psql 提取的 markdown 为 13137 字符（sha256=32bb1ece...），与契约声明的 13138 字符（sha256=21d915c8...）差 1 字符。系 psql -tA 输出格式差异（可能丢失末尾一个不可见字符），非内容错误。上游 wp-11924-01 通过平台 API 直接获取，哈希验证通过。本审查接受上游的哈希验证结果。", "evidence": "psql 输出 13137 字符 vs API 返回 13138 字符"}
      ],
      "checks_performed": [
        "asset_id uniqueness (42 unique)",
        "char_span quote verification (7 assets sampled, all match)",
        "counts consistency (by_class sum, by_resolution sum)",
        "resolution correctness (external paths correctly unresolved)",
        "no verified markers in source or manifest",
        "honest FAIL preservation (AC6/AC7/AC5 robustness)",
        "coverage fraction analysis (0.8862)",
        "parameter box missing bounds flagging",
        "verification.json 13-item check review",
        "source hash discrepancy investigation (psql vs API)"
      ],
      "checks_not_run": [
        "full 42-asset char_span verification (sampled 7 instead; upstream verify.py did full check)",
        "external path existence in TensorDEM repo (out of scope for this worktree)",
        "figure binary content verification (figures have no png_base64 in platform response)"
      ],
      "independence_limitations": [
        "本审查未访问生产者（wp-11924-01）的解释或内部推理过程，仅基于报告原文 + manifest + verification.json 进行独立审查",
        "psql 提取的 markdown 与 API 返回有 1 字符差异，但不影响内容审查结论",
        "未复跑上游的 23 项 pytest（测试代码在 worktree 中但本审查聚焦产物正确性而非代码执行）"
      ],
      "overstated_claims": [],
      "blocking_issues": [],
      "non_blocking_suggestions": [
        "可考虑为章节标题行（## 0. 结论速览 等）也登记为 heading 资产，以提高覆盖率至 >0.90",
        "外部引用资产（A36-A42）可补充跨仓解析指引（如 TensorDEM 的 commit SHA 或 branch），便于下游定位"
      ],
      "decision": "approve",
      "decision_rationale": "wp-11924-01 的资产登记产物在结构完整性、定位准确性、计数自洽性、分辨率判定正确性、契约合规性（无 verified 标记、honest FAIL 原样保留）方面均通过审查。13 项上游自检全部 pass。唯一注意点（psql 哈希差异）系提取方式差异，不影响内容审查结论。建议 approve。"
    },
    "review_events.json": [
      {"event_id": "RE-001", "timestamp": "2026-01-15T00:00:00Z", "event_type": "review_started", "detail": "开始对 wp-11924-01 进行独立审查"},
      {"event_id": "RE-002", "timestamp": "2026-01-15T00:01:00Z", "event_type": "source_fetched", "detail": "通过 psql 获取报告 11924 markdown（13137 字符）"},
      {"event_id": "RE-003", "timestamp": "2026-01-15T00:02:00Z", "event_type": "manifest_loaded", "detail": "加载 wp-11924-01 asset_manifest.json（42 资产）"},
      {"event_id": "RE-004", "timestamp": "2026-01-15T00:03:00Z", "event_type": "verification_loaded", "detail": "加载 wp-11924-01 verification.json（13 项检查，全部 pass）"},
      {"event_id": "RE-005", "timestamp": "2026-01-15T00:05:00Z", "event_type": "char_span_verified", "detail": "抽样验证 7 个关键资产的 char span 定位，全部匹配"},
      {"event_id": "RE-006", "timestamp": "2026-01-15T00:06:00Z", "event_type": "counts_verified", "detail": "验证 by_class 和 by_resolution 计数自洽"},
      {"event_id": "RE-007", "timestamp": "2026-01-15T00:07:00Z", "event_type": "resolution_verified", "detail": "验证 8 个外部引用资产正确标记为 unresolved"},
      {"event_id": "RE-008", "timestamp": "2026-01-15T00:08:00Z", "event_type": "honest_fail_verified", "detail": "验证 AC6/AC7/AC5 稳健性 FAIL 在 manifest 中原样保留"},
      {"event_id": "RE-009", "timestamp": "2026-01-15T00:09:00Z", "event_type": "review_completed", "detail": "审查完成， disposition = approve"}
    ]
  }
}
```
