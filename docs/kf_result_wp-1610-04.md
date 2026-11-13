# KF-RESULT wp-1610-04

tags: kf-wp:wp-1610-04, independent-review, cmaes, adversarial-review

## 1. 本工序做了什么

对 report_id=1610（CMA-ES 内核文献基准独立复核）执行独立 adversarial review。
审核对象为上游工作包 wp-1610-01（01-asset-registration）登记的报告原文及其产物。
审核范围：报告正文自洽性、数据表重算验证、声明与证据一致性、遗漏与过度声明识别。

## 2. 怎么做的

| 步骤 | 工具/方法 |
|---|---|
| 源文获取 | 从上游 wp-1610-01 产物取 source.md，sha256 重算验证 |
| 哈希校验 | `hashlib.sha256(source.encode('utf-8'))` 与契约值比对 |
| 收敛表重算 | 逐行重算 kernel_evals/ref_evals 比值，与报告值比对 |
| B1 A/B 表重算 | 逐行重算 (after-before)/before × 100%，与报告值比对 |
| 检查编号审计 | grep 全文搜索 C1-C8 标签，确认完整性 |
| 标题-正文一致性 | 比对平台记录标题与 source.md 标题/内容 |
| 参数表完整性 | 检查 §3.1 表是否列出实际参数值 |
| 产物可解析性 | 检查 PNG 图是否在报告记录中可获取 |
| 诚实性审计 | 检查局限性披露是否充分 |

## 3. 产出物清单

| 输出文件 | 要点 |
|---|---|
| `docs/kf_result_wp-1610-04.md` | 本报告（含 review_report.json 代码块） |
| `docs/kf/wp-1610-04/review_report.json` | 6 条发现（1 中/2 低/3 信息），disposition=approve_with_notes |

## 4. 证据定位表

| claim/字段 | 原文引文片段 | 验证结果 |
|---|---|---|
| 源文哈希 | `sha256:c426979905fa50a5cd372e8e7b300ad931596c437ea1cbabb79df59c7aaa41de` | ✓ 重算匹配 |
| 收敛 9/9 达标 | `达标工况 9/9，最坏比值 1.800（判据 ≤3）` | ✓ 9 行比值重算全部一致 |
| B1 A/B 变化 | `ellipsoid1e6 N=5: 1776→1928, -7.9%` | ✓ 5 行百分比重算全部正确 |
| 8/8 检查通过 | 平台标题含「8/8」，正文 §3.3 仅 6 项（C2,C4-C8） | ⚠ C1/C3 缺失，口径不明 |
| 闭式参数零误差 | `全部维度最坏值 **0**`，表中值全为「—」 | ⚠ 未列实际值，0 误差在浮点中不寻常 |
| 局限性披露 | `多峰函数（rastrigin/ackley）在 N=10、4e4 评价内两者都停在局部极小` | ✓ 诚实充分 |
| B1 非性能改进 | `不能宣称「修了性能 bug」` | ✓ 诚实充分 |

## 5. 注意点与局限

- **独立性限制**：审核仅基于报告 markdown 与上游产物，无法访问产生该报告的仓库代码（`optimizer/core/cmaes.py`、参考实现、测试文件）。
- **同模型依赖**：生产者与审核者均为同一平台生态内的 AI 智能体，非完全独立人类审核。
- **图不可验证**：三张 PNG 图不在报告记录中，无法视觉验证曲线与表格数据的一致性。
- **测试未重跑**：`tests/test_cmaes_literature_verification.py` 不在本工作树，无法独立重跑 15 个用例。
- **参数值缺失**：§3.1 未列出任何实际参数值，无法独立验证「零误差」声明。

## 6. 自检（逐条对照 acceptance）

| acceptance | 状态 | 证据 |
|---|---|---|
| valid_json | ✓ | review_report.json 经 `json.loads` 成功解析 |
| schema_pass | ✓ | `jsonschema.Draft202012Validator(schema).validate(kf_result)` 通过 |
| reviewer_independent | ✓ | 审核者 agent/m15824 ≠ 生产者 agent/m15530；仅基于报告原文+上游产物，未看生产者解释 |
| upstream_packages_completed | ✓ | wp-1610-01 产物齐全（source.md, kf_result.json, asset_manifest.json, locator_check.json） |

**无失败项**（无 honest-FAIL 需要申报）。Disposition: **approve_with_notes**。

---

```json
{
  "package_id": "wp-1610-04",
  "task_type": "04-independent-review",
  "report_id": "1610",
  "provenance": {
    "source_hash": "sha256:c426979905fa50a5cd372e8e7b300ad931596c437ea1cbabb79df59c7aaa41de",
    "source_field": "markdown",
    "producer": "agent/m15530",
    "emitted_at": "2026-11-12T00:54:15+00:00",
    "reviewer": "agent/m15824",
    "review_date": "2026-11-12",
    "notes": "Independent adversarial review of report 1610 (CMA-ES literature verification). Source hash verified against contract-declared value. Review performed from markdown + upstream artifacts only; no access to producing repo code."
  },
  "outputs": {
    "review_report.json": {
      "review_id": "wp-1610-04",
      "report_id": "1610",
      "reviewer": "agent/m15824",
      "review_date": "2026-11-12",
      "review_type": "04-independent-review",
      "upstream_package": "wp-1610-01",
      "scope": {
        "reviewed_artifacts": [
          "source.md (report markdown, sha256 verified)",
          "kf_result.json (upstream envelope)",
          "asset_manifest.json (upstream asset registration)",
          "locator_check.json (upstream quote verification)",
          "test_kf_wp1610_01.py (upstream acceptance tests)"
        ],
        "checks_performed": [
          "Source hash verification (sha256 match confirmed)",
          "Convergence table ratio recalculation (9/9 internally consistent)",
          "B1 A/B table percentage recalculation (5/5 correct)",
          "Check label completeness audit (C1, C3 missing)",
          "Title vs body consistency check (8/8 claim ambiguous)",
          "Closed-form parameter table completeness audit (values omitted)",
          "Artifact resolvability check (PNGs not in record)",
          "Honest disclosure audit (limitations properly stated)"
        ],
        "checks_not_run": [
          "Actual test execution (tests/test_cmaes_literature_verification.py not in this worktree)",
          "CMA-ES kernel code review (optimizer/core/cmaes.py not in this worktree)",
          "Reference implementation review (optimizer/verification/cmaes_reference.py not in this worktree)",
          "PNG figure content verification (binary files not available)",
          "Floating-point parameter comparison (actual values not reported in source)"
        ]
      },
      "findings": [
        {
          "id": "F1",
          "severity": "medium",
          "category": "ambiguous_claim",
          "title": "标题「8/8 检查通过」与正文检查编号不一致",
          "description": "平台记录标题声明「8/8 检查通过」，但正文 §3.3 仅显式标注 6 项性质检查（C2, C4, C5, C6, C7, C8）。C1 与 C3 在全文中未出现。若将 §3.1 闭式参数核对与 §3.2 收敛核对各计为 1 项，则总数为 8，但此归类混合了参数验证与行为性质两类不同检查，标题未说明此口径。",
          "evidence": [
            {
              "quote": "CMA-ES 内核文献基准独立复核：Hansen 2016 闭式参数零误差、8/8 检查通过，并修复 4 处静默稳健性缺陷（m1884）",
              "source": "platform record title (contract)"
            },
            {
              "quote": "采样分布保真 (C2)",
              "source": "source.md §3.3 table row 1"
            },
            {
              "quote": "旋转不变性 (C4)",
              "source": "source.md §3.3 table row 2"
            },
            {
              "note": "C1 and C3 not found anywhere in source.md"
            }
          ],
          "impact": "读者可能误以为存在 8 项同类性质检查；实际为 6 项性质检查 + 2 项其他验证。不影响技术结论正确性，但标题表述有歧义。",
          "recommendation": "标题改为「6/6 性质检查通过」或在正文中显式说明 8/8 的组成口径（参数核对+收敛+性质）。"
        },
        {
          "id": "F2",
          "severity": "low",
          "category": "insufficient_evidence",
          "title": "闭式参数表未列出实际值，仅报误差为 0",
          "description": "§3.1 闭式策略参数表中，所有维度（N=2,3,5,8,10,20）的所有参数（λ, μ, μ_eff, c_c, c_s, c_1, c_μ, d_σ, χ_N）均以「—」占位，仅报告「最大相对误差 = 0」。在浮点运算中，跨 6 维度 × 9+ 参数精确到 0 误差极不寻常——即使完全相同的公式实现也会因计算顺序产生舍入差异。此结果暗示参考实现与内核可能共享代码路径，或比较时使用了宽松容差。",
          "evidence": [
            {
              "quote": "全部维度最坏值 **0**，即双精度舍入水平。",
              "source": "source.md §3.1"
            },
            {
              "note": "Table shows '—' for all parameter values across all 6 dimensions"
            }
          ],
          "impact": "无法从报告独立验证参数实际值是否正确。若参考实现与内核共享代码，则「独立复核」的独立性被削弱。",
          "recommendation": "至少列出一个维度（如 N=5）的完整参数值表，并说明比较容差（如 np.allclose atol/rtol）。"
        },
        {
          "id": "F3",
          "severity": "low",
          "category": "missing_label",
          "title": "检查编号 C1 与 C3 缺失",
          "description": "性质检查编号从 C2 直接跳到 C4，C1 与 C3 在全文中未出现。可能原因：(a) C1/C3 对应闭式参数与收敛检查，使用了不同编号体系；(b) C1/C3 曾被定义但后来移除；(c) 编号从 C2 开始是约定。无论哪种情况，报告未解释编号跳跃。",
          "evidence": [
            {
              "note": "grep for C1, C3, (C1), (C3) in source.md returns 0 matches"
            },
            {
              "quote": "采样分布保真 (C2)",
              "source": "source.md §3.3 first check"
            }
          ],
          "impact": "编号不连续可能暗示有未报告的失败检查或已移除的测试用例。",
          "recommendation": "在 §2 方法与工具链中说明检查编号体系，或补全 C1/C3 标签。"
        },
        {
          "id": "F4",
          "severity": "info",
          "category": "correctly_disclosed",
          "title": "收敛效率偏差 >3% 但判据为比值≤3——已正确披露",
          "description": "§5 误差判定表正确指出收敛评价数与参考实现的偏差最坏达 +80%（比值 1.800），超过 3% 阈值，但判据为「比值≤3」故通过。此披露诚实且充分。",
          "evidence": [
            {
              "quote": "收敛评价数 | 独立参考实现的评价数 | 最坏 +80.0%（比值 1.800） | 否（>3%），判据为比值≤3，判据通过",
              "source": "source.md §5 table"
            }
          ],
          "impact": "无负面影响——已正确披露。",
          "recommendation": "无。"
        },
        {
          "id": "F5",
          "severity": "info",
          "category": "unverifiable_artifact",
          "title": "三张 PNG 图未随报告提供，无法视觉验证",
          "description": "§3.5 列出三张图的路径（artifacts/cmaes_verification/*.png），但二进制文件不在本报告记录中。无法验证图中曲线是否与 §3.2 表格数据一致。",
          "evidence": [
            {
              "quote": "artifacts/cmaes_verification/cmaes_convergence_vs_reference.png",
              "source": "source.md §3.5"
            },
            {
              "note": "resolvable_from_platform_record: false (from upstream asset_manifest)"
            }
          ],
          "impact": "图的视觉声明无法独立验证。",
          "recommendation": "若平台支持，将 PNG 以 base64 内嵌或提供可公开访问的 URL。"
        },
        {
          "id": "F6",
          "severity": "info",
          "category": "positive",
          "title": "B1 修复影响如实报告为混合/非性能改进",
          "description": "§3.4 正确指出 B1 修复对收敛效率的影响在 ±9% 内且方向不定，明确声明「不能宣称修了性能 bug」。这是诚实的科学报告实践。",
          "evidence": [
            {
              "quote": "B1 是公式一致性问题，对收敛效率的影响在 ±9% 内且方向不定，不能宣称「修了性能 bug」",
              "source": "source.md §3.4 conclusion"
            }
          ],
          "impact": "正面——展示了良好的科学诚信。",
          "recommendation": "无。"
        }
      ],
      "severity_summary": {
        "blocking": 0,
        "medium": 1,
        "low": 2,
        "info": 3
      },
      "overstated_claims": [
        {
          "claim": "8/8 检查通过",
          "issue": "正文仅显式标注 6 项性质检查（C2,C4-C8），C1/C3 缺失。若计入 §3.1 和 §3.2 则总数为 8，但标题未说明此混合口径。",
          "correction": "应改为「6/6 性质检查通过」或说明 8/8 组成。"
        },
        {
          "claim": "闭式参数零误差",
          "issue": "参数表未列出实际值，仅报误差为 0。跨 6 维度 × 9+ 参数精确到 0 在浮点运算中极不寻常，可能暗示参考与内核共享代码。",
          "correction": "应至少列出一个维度的完整参数值并说明比较容差。"
        }
      ],
      "independence_limitations": [
        "Review performed from report markdown and upstream artifacts only; no access to producing repo (optimizer/core/cmaes.py, tests, reference implementation).",
        "Same-model dependence: both producer and reviewer are AI agents operating in the same platform ecosystem.",
        "Cannot verify test assertions (test_cmaes_literature_verification.py) without the producing repo.",
        "Cannot verify PNG figure content without binary artifacts.",
        "Cannot independently re-run CMA-ES verification without the optimizer codebase."
      ],
      "disposition": "approve_with_notes",
      "disposition_rationale": "报告核心技术结论（闭式参数匹配、收敛达标、性质检查通过、4 处修复）在报告内部自洽，数据表经独立重算验证无误。局限性披露诚实充分。存在 2 项低严重度问题（标题歧义、参数值缺失）和 1 项中严重度问题（8/8 口径不明），均不阻塞技术结论，但建议修正以提高可复核性。",
      "remediation": [
        "修正标题或正文中「8/8」的口径说明",
        "在 §3.1 补充至少一个维度的完整参数值表",
        "在 §2 中说明检查编号体系（为何从 C2 开始）"
      ]
    }
  }
}
```

**repro_cmd**（工作树根执行）：

```bash
python3 -c "
import json, hashlib, jsonschema, re
with open('docs/kf/wp-1610-01/source.md') as f: src = f.read()
assert hashlib.sha256(src.encode()).hexdigest() == 'c426979905fa50a5cd372e8e7b300ad931596c437ea1cbabb79df59c7aaa41de'
with open('schemas/kf_result.v1.schema.json') as f: schema = json.load(f)
with open('docs/kf_result_wp-1610-04.md') as f: md = f.read()
blocks = re.findall(r'\`\`\`json\n(.*?)\n\`\`\`', md, flags=re.S)
assert len(blocks) == 1
result = json.loads(blocks[0])
jsonschema.Draft202012Validator(schema).validate(result)
print('All checks passed')
"
```
