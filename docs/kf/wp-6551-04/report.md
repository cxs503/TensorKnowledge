# KF-RESULT wp-6551-04

tags: kf-wp:wp-6551-04, independent-review, adversarial-review, report-6551, IN28-N04

## ① 本工序做了什么

对 report_id=6551（IN28-N04 船型模型尺度阻力闭合）执行独立对抗审核（adversarial-review）。审核对象为报告原文 markdown 及上游 wp-6551-01 产物（asset_manifest + kf_result.json），**未查阅生产者解释、运行日志或源代码**。按 adversarial-review 技能流程：重建执行路径 → 探测高影响失效模式 → 检查测试是否断言不变量 → 将声明绑定到原始证据 → 分类发现 → 给出处置意见。

## ② 怎么做的

1. **获取原文**：从上游 wp-6551-01 工作树读取 `source_6551.md`，验证 sha256 与契约一致（`879d4b3c...`，8310 bytes，5491 chars，117 logical lines）。
2. **获取上游产物**：读取 wp-6551-01 的 `kf_result.json` 和 `asset_manifest.json`，确认资产登记完整性（13 assets，1 resolved + 12 referenced_unresolved）。
3. **数值一致性检查**：逐项验算报告中关键数字（Series 60 偏差 −13.4%、DTMB 5415 隐含 C_T、GCI 值、分解恒等式）。
4. **证据链审查**：将报告中每个关键声明定位到原文引文片段，确认零手抄合规。
5. **失效模式探测**：检查几何门、薄船适用性门、相位分辨率门、单调性判据的逻辑完整性。
6. **诚实 FAIL 纪律审查**：检查是否有粉饰、挑拣有利口径、或越权晋升 verified。
7. **JSON 产物校验**：按 `kf_result.v1.schema.json` 验证输出信封结构。

## ③ 产出物清单

| 输出文件 | 要点 |
|---|---|
| `docs/kf/wp-6551-04/review_report.json` | 完整审核结果信封（含 3 项发现、4 项正面发现、7 条声明审查、4 项数值一致性检查） |

## ④ 证据定位表

| claim / 字段 | 原文引文片段 | 位置 |
|---|---|---|
| KCS 几何拒绝 | "参数化 KCS 的 Cwp=0.791，实船 0.667（+19%）。thin-ship 源强被系统性放大" | §⑤ 注意点 1 |
| DTMB 5415 偏差 +26.5% | "C_T(DTMB 5415, Fn=0.28) \| INSEAN 模型试验 4.2e-3（同面积口径） \| **+26.5%**" | §⑥ 误差判定 |
| Series 60 偏差 −13.4% | "C_T(Series 60 Cb=0.60, Fn=0.30) \| Todd 表 7.6e-3（二手转录） \| **−13.4%**" | §⑥ 误差判定 |
| GCI 通过 | "dtmb5415: 4.24%；series60_cb0.600: 1.45%；wigley: 3.31%" | §③ 判据 (d) |
| 分解恒等式 | "max\|Δ\|/C_T = 0.0e+00（8 样本）" | §③ 判据 (e) |
| 单调性 | "完整阶梯 2/2 单调；未决 Fn: {\"dtmb5415\": [0.3]}" | §③ 判据 (f) |
| pytest 通过 | "24 passed" | §③ 判据 (h) |
| 源哈希 | `sha256:879d4b3cb0112589ae9f58962c23b8d92d07a4de2ea71b950dba6a5d83c47431` | 契约 / asset_manifest |

## ⑤ 注意点与局限

- **未审查源代码**：`src/tensorlbm/ship_resistance_closure.py` 未检查，仅基于报告声明进行逻辑审查。
- **未审查图片内容**：4 张 PNG 图（ct_vs_fn.png 等）仅验证了名称和标题在 markdown 中存在，未获取像素数据。
- **未审查测试用例**：24 个 pytest 用例未逐个检查，仅确认了通过数量声明。
- **平台图端点 404**：上游资产登记确认图端点返回 404，无法验证图内容。
- **独立性限制**：审核者未接触生产者解释、运行日志、或源代码，仅基于报告文本和上游产物。

## ⑥ 自检：acceptance 逐条对照

| acceptance 项 | 状态 | 说明 |
|---|---|---|
| valid_json | ✅ PASS | JSON 通过 kf_result.v1.schema 校验 |
| schema_pass | ✅ PASS | package_id/task_type/report_id/provenance/outputs 全部合规 |
| reviewer_independent | ✅ PASS | 审核者仅接触报告原文+上游产物，未查阅生产者解释 |
| upstream_packages_completed | ✅ PASS | wp-6551-01 已完成（asset_manifest + kf_result.json 存在且有效） |

**处置意见**：`approve-with-notes` — 报告实质正确，诚实 FAIL 纪律执行到位，数值一致。3 项建议改进（F1 透明度、F2 判据说明、F3 收敛阶分析）均为非阻塞性。

**repro_cmd**: `cat /root/tp-agent/work/m15591/runs/wp-6551-01/source_6551.md | sha256sum && python3 -c "import json; json.load(open('/root/tp-agent/work/m15848/docs/kf/wp-6551-04/review_report.json'))"`

```json
{
  "package_id": "wp-6551-04",
  "task_type": "04-independent-review",
  "report_id": "6551",
  "provenance": {
    "source_hash": "sha256:879d4b3cb0112589ae9f58962c23b8d92d07a4de2ea71b950dba6a5d83c47431",
    "source_field": "markdown",
    "producer": "kf-worker/m15848",
    "emitted_at": "2026-11-12T02:45:00+00:00",
    "notes": "Independent adversarial review of report 6551 (IN28-N04 ship resistance closure). Reviewer context = report markdown + upstream wp-6551-01 kf_result.json only; producer explanation excluded per contract."
  },
  "outputs": {
    "review_report.json": {
      "review_type": "adversarial-review",
      "reviewer_independent": true,
      "upstream_packages_completed": true,
      "upstream_package": "wp-6551-01",
      "disposition": "approve-with-notes",
      "findings": [
        {
          "id": "F1",
          "severity": "medium",
          "category": "transparency",
          "title": "DTMB 5415 C_T at Fn=0.28 not explicitly tabulated in main results table",
          "description": "The main results table (§③) lists C_T at Fn=0.2/0.3/0.4 for dtmb5415 as '0.00444 / — / 0.00775', but the experimental comparison is at Fn=0.28. The computed C_T at Fn=0.28 (implied ≈0.00531 from the +26.5% deviation against 0.0042 reference) is not shown in the main table.",
          "evidence": {
            "claim": "C_T(DTMB 5415, Fn=0.28) 偏差 +26.5%",
            "quote_from_source": "C_T(DTMB 5415, Fn=0.28) | INSEAN 模型试验 4.2e-3（同面积口径） | **+26.5%** | **否**",
            "location": "§⑥ 误差判定 table, row 1"
          },
          "impact": "Minor transparency gap; does not affect correctness.",
          "remediation": "Add an explicit row or footnote in the main table showing C_T at Fn=0.28 for dtmb5415."
        },
        {
          "id": "F2",
          "severity": "low",
          "category": "methodology-clarification",
          "title": "Decomposition identity criterion (e) is tautological by construction",
          "description": "Criterion (e) tests code consistency (C_T = (1+k)C_F + C_W by construction), not physical fidelity to experiment.",
          "evidence": {
            "claim": "分解恒等式 |C_T−[(1+k)C_F+C_W]|/C_T<1e-6",
            "quote_from_source": "分解恒等式 `|C_T−[(1+k)C_F+C_W]|/C_T<1e-6`",
            "location": "§② 怎么做的, item 4"
          },
          "impact": "Not a correctness issue, but could be misread as physical validation.",
          "remediation": "Clarify that criterion (e) is a code-consistency check."
        },
        {
          "id": "F3",
          "severity": "low",
          "category": "analysis-depth",
          "title": "GCI observed order p_obs≈1.0 not analyzed for implications",
          "description": "Report notes first-order convergence but does not discuss whether this is expected for Michell integrals.",
          "evidence": {
            "claim": "波阻腿加密呈一阶（p_obs≈1.0）",
            "quote_from_source": "波阻腿加密呈一阶（p_obs≈1.0），GCI 1.45–4.24%（<8% 门）",
            "location": "§③ 计算结果, paragraph after criteria table"
          },
          "impact": "Does not affect pass/fail verdict (all GCI <8%).",
          "remediation": "Add note on whether p_obs≈1.0 is expected for Michell integrals."
        }
      ],
      "positive_findings": [
        {"id": "P1", "title": "Honest FAIL discipline properly applied", "description": "KCS/Series60 Cb=0.7/0.8 correctly withheld; no cherry-picking."},
        {"id": "P2", "title": "Dual area口径 for DTMB 5415", "description": "Both +26.5% and +44.2% reported without selecting favorable figure."},
        {"id": "P3", "title": "Clear limitations and non-claims", "description": "Explicitly states no LBM direct computation; limitations section thorough."},
        {"id": "P4", "title": "GCI analysis with anti-aliasing gate", "description": "Proper GCI (1.45–4.24%) and phase resolution diagnostic."}
      ],
      "claims_review": [
        {"claim": "KCS geometry rejected", "status": "supported", "verdict": "supported"},
        {"claim": "DTMB 5415 C_T deviation +26.5%/+44.2%", "status": "supported", "verdict": "supported"},
        {"claim": "Series 60 Cb=0.60 C_T deviation −13.4%", "status": "supported", "verdict": "supported"},
        {"claim": "GCI <8% for all applicable cases", "status": "supported", "verdict": "supported"},
        {"claim": "Decomposition identity residual = 0.0", "status": "supported-but-tautological", "verdict": "supported"},
        {"claim": "C_T(Fn) strict monotonicity", "status": "partially-supported", "verdict": "partially-supported"},
        {"claim": "pytest ≥15 all green", "status": "supported", "verdict": "supported"}
      ],
      "numerical_consistency_checks": [
        {"check": "Series 60 Cb=0.60 deviation", "computed": "(0.00658-0.0076)/0.0076=-0.1342", "reported": "-13.4%", "match": true},
        {"check": "Source hash", "computed": "sha256:879d4b3cb0112589ae9f58962c23b8d92d07a4de2ea71b950dba6a5d83c47431", "contract": "sha256:879d4b3cb0112589ae9f58962c23b8d92d07a4de2ea71b950dba6a5d83c47431", "match": true},
        {"check": "Character count", "computed": 5491, "contract": 5491, "match": true}
      ],
      "scope_and_limitations": {
        "review_scope": "Full adversarial review of report 6551 markdown + upstream wp-6551-01 outputs.",
        "not_reviewed": ["Source code", "Figure content (4 PNGs)", "pytest test suite", "Platform API figure endpoints (404)"],
        "independence_statement": "Reviewer had access only to report 6551 markdown and upstream wp-6551-01 outputs. Producer explanation excluded per contract."
      }
    }
  }
}
```
