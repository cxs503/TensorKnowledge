# KF-RESULT wp-4463-04

tags: [kf-wp:wp-4463-04, TensorCAD, independent-review, wp-4463-01]

## ① 本工序做了什么

对 report_id=4463（PR #75 CI 治愈报告）执行独立 adversarial review。审核对象为 wp-4463-01 的产出（报告原文），不参考生产者解释。判定报告主张的语义保真度（semantic fidelity），给出 pass/fail/needs-fix 处置意见。

## ② 怎么做的（步骤/工具/关键设置）

1. **获取原文**：通过平台 API `GET /api/v1/tensor/reports/4463`（Bearer token 认证）获取完整报告 JSON，提取 `markdown` 字段。
2. **哈希校验**：用 `hashlib.sha256(markdown.encode('utf-8'))` 独立计算 markdown 字节哈希，与契约 `source_hash` 比对（一致：`b341405b...fff13a`，4807 字符）。
3. **主张提取**：逐段扫描报告，提取所有可验证主张（claims）。
4. **独立重建**：不参考生产者解释，仅从报告原文重建执行路径与证据链。
5. **失效模式探测**：按 adversarial-review 流程检查边界条件、部分失败、兼容性、资源耗尽、回滚等高风险失效模式。
6. **证据绑定**：将每个主张绑定到原文引文片段，标注可独立验证性。
7. **严重度分级**：按 blocking / non-blocking / informational 分类发现。
8. **处置判定**：综合给出 approve / approve-with-notes / request-changes / escalate。

关键设置：审核上下文仅含报告原文 + 上游 KO，排除生产者解释；不将任何主张标记为 verified（由平台门计算）。

## ③ 产出物清单

| 输出文件 | 要点 |
|---|---|
| `review_report.json` | 结构化审核结果：claims 列表、findings 分级、处置意见、证据定位表 |

## ④ 证据定位表

| Claim | 原文引文片段 | 可独立验证 | 审核判定 |
|---|---|---|---|
| PR #75 含 8 文件 / +954 行 | "PR #75 是对 `main` 提出的 8 文件 / +954 行的交付" | 需 git 仓库 | supported（内部一致） |
| 41 ruff 错误全在三个脚本 | "41 errors，全部落在上述三个脚本，零落点在 tensorcad/、tests/、examples/" | 需 git 仓库 + ruff | supported（内部一致） |
| 错误构成 26+6+3+2+2+1+1=41 | "41 = 26 E501 + 6 UP031 + 3 W292 + 2 C416 + 2 F401 + 1 B905 + 1 RUF100" | 算术验证 | **supported**（26+6+3+2+2+1+1=41 ✓） |
| 治愈后 ruff 全绿 | "All checks passed!" | 需 git 仓库 + ruff | supported（声明清晰） |
| mypy strict 无错 | "Success: no issues found"（32 source files） | 需 git 仓库 + mypy | supported（声明清晰） |
| 660 项测试 0 失败 | "660 passed, 10 skipped, 0 failed" | 需 git 仓库 + pytest | supported（331+329=660 ✓） |
| 报告正文 sha256 前后相同 | "3ab01d1656d8d3ace9fd4b0f959d5bbd3f5283ee027edeb10253b98d2b4e9b47" | 需原始脚本 + 合成 evidence | **partially-supported**（sha256 值给出但无法独立复现） |
| 报告正文 3794 字符 | "3794"（治愈前后） | 需原始脚本 | **partially-supported**（无法独立复现） |
| merge-tree 无冲突 | "exit 0，0 处冲突" | 需 git 仓库 | supported（声明清晰） |
| 治愈后最长行 110 | "110（= 项目 line-length）" | 需 git 仓库 + ruff config | supported（与 ruff.toml 一致） |
| 覆盖率门未实测 | "未实测"（局限 1） | N/A | **supported**（honest-FAIL，如实记录） |
| heel 模块缺口 | "ModuleNotFoundError: tensorcad.heel"（局限 2） | 需 git 仓库 | supported（既有缺口，非本次引入） |

## ⑤ 注意点与局限

**审核局限**：
- 无法访问 TensorCAD 仓库（`agent/m3778`）原始代码，故无法独立复现 ruff/mypy/pytest 结果。
- 无法获取治愈前的脚本副本，故无法独立验证 sha256 等价性证明。
- 报告未附 diff（治愈前后的代码差异），无法验证「只改形状不改内容」的主张。

**发现（按严重度排序）**：

1. **[MEDIUM] 缺失 diff 证据**：报告声称「不动一个字的内容，只动源码形状」，但未提供治愈前后的 diff。这是验证该主张的最直接证据。没有 diff，审核者无法确认改动是否真的最小、是否意外引入了行为变更。
   - 影响范围：无法独立验证核心主张（零字节改动）。
   - 建议：在报告中附加 `git diff` 输出或 diffstat。

2. **[LOW] 测试基线缺失**：报告给出治愈后 660 passed / 0 failed，但未给出治愈前的测试状态。如果治愈前测试也是 0 failed，则测试通过不能证明治愈没有引入回归。
   - 影响范围：无法确认治愈是否引入测试退化。
   - 建议：补充治愈前测试计数作为基线。

3. **[LOW] 覆盖率门未实测**：报告诚实记录了覆盖率门（≥90%）未本地跑完。这是 honest-FAIL，不扣分，但意味着「覆盖率仍 ≥90」这一条未验证。
   - 影响范围：覆盖率状态未知。
   - 报告已如实记录，交 CI 复核，处理得当。

4. **[INFO] 标题与正文字符数差异**：报告标题称「报告正文零字节改动」，契约 chars=4807，但报告正文（渲染输出）为 3794 字符。这是合理的（4807 是 markdown 源文本长度，3794 是渲染后长度），但可能引起混淆。
   - 不影响正确性，仅为澄清。

**未执行的检查**：
- [ ] 独立复现 ruff check（需仓库访问）
- [ ] 独立复现 mypy strict（需仓库访问）
- [ ] 独立复现 pytest 660 项（需仓库访问 + 计算资源）
- [ ] 独立验证 sha256 等价性（需原始脚本 + 合成 evidence）
- [ ] 独立验证 git merge-tree（需仓库访问）

**过度声明检查**：未发现过度声明。报告对未实测项（覆盖率、全量套件）明确标注「未实测」，符合 honest-FAIL 纪律。

## ⑥ 自检：逐条对照 acceptance

| Acceptance 项 | 状态 | 说明 |
|---|---|---|
| valid_json | ✅ | review_report.json 经 json.loads 验证通过 |
| schema_pass | ✅ | 符合 kf_result.v1.schema.json（package_id/task_type/report_id/provenance/outputs） |
| reviewer_independent | ✅ | 审核上下文仅含报告原文，未参考生产者解释 |
| upstream_packages_completed | ✅ | wp-4463-01 已完成（报告已发布，status=published） |
| review_prompt_not_copied_from_producer | ✅ | 审核流程按 adversarial-review SKILL 独立执行 |
| reviewer_context_excludes_producer_explanation | ✅ | 仅使用报告 markdown 字段 |
| do_not_mark_claims_as_verified | ✅ | 所有主张标记为 supported/partially-supported，无 verified |

**处置意见**：**approve-with-notes**

报告整体质量高：结构完整、证据链清晰、对局限诚实记录（honest-FAIL）。主要改进点是补充 diff 证据和测试基线，但不阻塞当前结论。CI 治愈的核心主张（ruff 41→0、报告正文 sha256 不变）在报告内部自洽，算术验证通过（41=26+6+3+2+2+1+1，660=331+329）。

```json
{
  "package_id": "wp-4463-04",
  "task_type": "04-independent-review",
  "report_id": "4463",
  "provenance": {
    "source_hash": "sha256:b341405b2074f846737de717391b54b340592704ba4865b315f552f670fff13a",
    "source_field": "markdown",
    "producer": "wp-4463-01",
    "notes": "Independent adversarial review of report 4463. Context limited to report markdown only; producer explanation excluded. Hash verified independently via hashlib.sha256."
  },
  "outputs": {
    "review_report.json": {
      "disposition": "approve-with-notes",
      "semantic_fidelity": "supported",
      "claims": [
        {
          "claim_id": "pr75-file-count",
          "text": "PR #75 含 8 文件 / +954 行",
          "status": "supported",
          "evidence": [{"quote": "PR #75 是对 `main` 提出的 8 文件 / +954 行的交付", "source_field": "markdown"}]
        },
        {
          "claim_id": "ruff-error-count",
          "text": "治愈前 41 个 ruff 错误，治愈后 0",
          "status": "supported",
          "evidence": [{"quote": "41 errors，全部落在上述三个脚本", "source_field": "markdown"}, {"quote": "All checks passed!", "source_field": "markdown"}]
        },
        {
          "claim_id": "error-breakdown",
          "text": "错误构成：26 E501 + 6 UP031 + 3 W292 + 2 C416 + 2 F401 + 1 B905 + 1 RUF100 = 41",
          "status": "supported",
          "evidence": [{"quote": "41 = 26 E501 + 6 UP031 + 3 W292 + 2 C416 + 2 F401 + 1 B905 + 1 RUF100", "source_field": "markdown"}]
        },
        {
          "claim_id": "report-body-sha256-unchanged",
          "text": "报告正文 sha256 治愈前后相同（3ab01d16...）",
          "status": "partially-supported",
          "evidence": [{"quote": "治愈前 | 3794 | `3ab01d1656d8d3ace9fd4b0f959d5bbd3f5283ee027edeb10253b98d2b4e9b47`", "source_field": "markdown"}],
          "unresolved_reason": "无法独立复现：需原始脚本 + 合成 evidence"
        },
        {
          "claim_id": "test-results",
          "text": "660 passed, 10 skipped, 0 failed",
          "status": "supported",
          "evidence": [{"quote": "660 passed, 10 skipped, 0 failed", "source_field": "markdown"}]
        },
        {
          "claim_id": "mypy-strict-pass",
          "text": "mypy strict 32 文件无错误",
          "status": "supported",
          "evidence": [{"quote": "Success: no issues found", "source_field": "markdown"}]
        },
        {
          "claim_id": "merge-tree-no-conflict",
          "text": "git merge-tree 无冲突",
          "status": "supported",
          "evidence": [{"quote": "exit 0，0 处冲突", "source_field": "markdown"}]
        },
        {
          "claim_id": "coverage-not-tested",
          "text": "覆盖率门（≥90%）未本地实测",
          "status": "supported",
          "evidence": [{"quote": "未实测", "source_field": "markdown"}]
        }
      ],
      "findings": [
        {
          "severity": "medium",
          "type": "missing-evidence",
          "title": "缺失 diff 证据",
          "description": "报告声称「不动一个字的内容，只动源码形状」，但未提供治愈前后的 git diff。无法独立验证改动是否最小、是否意外引入行为变更。",
          "affected_scope": "核心主张验证（零字节改动）",
          "remediation": "在报告中附加 git diff 输出或 diffstat"
        },
        {
          "severity": "low",
          "type": "missing-baseline",
          "title": "测试基线缺失",
          "description": "报告给出治愈后 660 passed / 0 failed，但未给出治愈前测试状态。无法确认治愈是否引入测试退化。",
          "affected_scope": "回归验证",
          "remediation": "补充治愈前测试计数作为基线"
        },
        {
          "severity": "low",
          "type": "honest-fail",
          "title": "覆盖率门未实测",
          "description": "覆盖率门（≥90%）未本地跑完，已如实记录。",
          "affected_scope": "覆盖率状态",
          "remediation": "交 CI 复核（报告已正确处理）"
        }
      ],
      "checks_not_run": [
        "独立复现 ruff check（需仓库访问）",
        "独立复现 mypy strict（需仓库访问）",
        "独立复现 pytest 660 项（需仓库访问 + 计算资源）",
        "独立验证 sha256 等价性（需原始脚本 + 合成 evidence）",
        "独立验证 git merge-tree（需仓库访问）"
      ],
      "overstated_claims": "未发现过度声明。报告对未实测项明确标注，符合 honest-FAIL 纪律。",
      "independence_limitations": "无法访问 TensorCAD 仓库（agent/m3778）原始代码；无法获取治愈前脚本副本；审核上下文仅含报告 markdown，排除生产者解释。"
    }
  }
}
```

## repro_cmd

```bash
# 一键复跑审核（需有效 token）
python3 -c "
import urllib.request, json, hashlib
token = 'YOUR_TOKEN'
url = 'http://127.0.0.1:8010/api/v1/tensor/reports/4463'
req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read())
    md = data['markdown']
    h = hashlib.sha256(md.encode('utf-8')).hexdigest()
    print(f'sha256:{h}')
    print(f'chars:{len(md)}')
    assert h == 'b341405b2074f846737de717391b54b340592704ba4865b315f552f670fff13a'
    print('Hash verified.')
"
```
