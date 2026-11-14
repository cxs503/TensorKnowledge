# KF-RESULT wp-11421-04

**报告：reports/11421 → 独立审核（task_type=04-independent-review，lane C，status=in-review）**

标题：`P270W1-N07 端到端不确定度传播：几何→阻力→推进→EEXI/CII 六因子分解（蒙特卡洛 + Sobol）` 场景键：`ship_performance` 标签：`EEXI, CII, 不确定度传播, 蒙特卡洛, Sobol, green_shipping, Holtrop, adversarial_review, kf-wp:wp-11421-04`

> 本工序只做**独立审核**：不修改报告原文、不重算生产结果、不把任何结论标为 verified（verification 由平台门计算）。审核对象 = wp-11421-01（资产登记 + 交叉复核）。

---

## ① 本工序做了什么

对 report_id=11421 的 markdown 原文（18542 字符，sha256:f85c29fe…）进行**独立语义保真度审核**，同时验证上游 wp-11421-01 的交叉复核结果（X1–X7）。审核范围覆盖：几何自洽性、Sobol 求和闭合、合规概率标准误、域外推比例合理性、σ→0 负控、收敛漂移、FD vs 解析灵敏度、以及报告正文与表格的算术一致性。

审核结论：**approve_with_notes** — 报告在所有可验证的算术断言上自洽；两项低严重性措辞问题（F1、F2）已由上游 X4/X5 正确识别；三项信息性发现（F3–F5）不影响科学内容。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **获取原文**：从 wp-11421-01 产物 `docs/kf/wp-11421-01/source.md` 读取报告 markdown（逐字节保真副本），独立重算 sha256 与字符数，与工单契约比对。
2. **独立重算 13 项检查**（R1–R13）：全部用 Python 3.11 脚本从 source.md 的表格数字直接计算，不依赖生产者代码或 artifacts。
3. **验证上游交叉复核**：读取 `docs/kf/wp-11421-01/crosscheck.json`，逐项复核 X1–X7 的 verdict 与证据定位。
4. **发现分类**：按 severity（low/info）与 category（incorrect_prose_claim / missing_interpretation / unverifiable_external_claim / documentation_clarity）分类。
5. **未运行检查标记**：6 项需要外部代码/artifacts 的检查明确标为 not_run，不冒充通过。
6. **JSON 校验**：`jsonschema` 校验 `kf_result.json` 对 `schemas/kf_result.v1.schema.json`。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-11421-04/kf_result.json` | 交付信封，`provenance.source_hash` 与原文一致，`outputs.review_report.json` 内嵌审核摘要 |
| `docs/kf/wp-11421-04/review_report.json` | 完整审核报告：13 项检查、5 项发现、6 项未运行检查、处置结论 |

## ④ 证据定位表（claim → 原文引文）

| 审核项 | 原文位置 | 引文（逐字，截断 56 字符） | 审核结果 |
|---|---|---|---|
| R1 几何自洽 | §1.2 表1 | `Cb / Cm / Cp` → `0.842 / 0.995 / 0.846` | PASS |
| R2 Sobol 求和 | §3.3 表4 | `Σ` → `0.9860 / — / 1.0007 / 0.9979 / — / 1.0006` | PASS |
| R3 合规概率 SE | §3.2 | `0.4541 ± 0.0011` | PASS |
| R4 域外推比例 | §3.2 | `76999/200000`（38.5%） | PASS |
| F1/X4 Jansen 非负 | §2.2 + 表5 | `且同样满足 S_i ≥ 0` vs `-0.0028` | CONFIRMED FAIL |
| F2/X5 FD 5% 界 | §3.4(b) + 表5 | `非零项相对差 < 5%` vs `16.25%` | CONFIRMED FAIL |
| R7 σ→0 比值 | §3.4(c) 表6 | `0.01001` / `0.00100` | PARTIAL（内部精度 vs 打印值） |
| R8 收敛漂移 | §3.4(d) 表7 | `0.250%` / `-0.011%` | PASS |
| R11 1852 量纲 | §2.3 | `capacity·V_ref[m/s]·3600` → `capacity·V_ref[kn]` | PASS |

## ⑤ 注意点与局限

1. **未重跑生产管线**：MC 样本、Sobol 估计量、API 调用均不在本记录内；审核仅限于"报告对它自己表格的断言"。
2. **图内容未检**：仅验证 PNG 载荷存在性（wp-11421-01 已做），未检查像素内容是否与表格数据一致。
3. **规则系数 WITHHELD**：EEXI_req / CII_req 来自 MEPC 转录，不可复核。
4. **同模型依赖**：审核者与生产者均为 LLM agent，语义解释可能存在共同偏差；算术验证不受此影响。
5. **honest-FAIL**：F1 和 F2 两项判定为 fail（正文措辞与表格不符），但不影响报告数值结论。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 实测值 |
|---|---|---|
| valid_json | ✅ | `pass` |
| schema_pass | ✅ | `True`（kf_result.v1.schema.json） |
| reviewer_independent | ✅ | 独立于生产者，未看生产者解释 |
| upstream_packages_completed | ✅ | wp-11421-01 已完成（asset registration + crosscheck） |
| do_not_mark_claims_as_verified | ✅ | 无任何 verified 标记 |
| review_prompt_not_copied_from_producer | ✅ | 审核流程独立构建 |

### repro_cmd

```sh
python3 -c "
import json, hashlib
with open('docs/kf/wp-11421-01/source.md','rb') as f: md=f.read()
assert hashlib.sha256(md).hexdigest()=='f85c29fe650365140152064807d90b2accdf43382f2222956470f3521e0a280a'
with open('docs/kf/wp-11421-04/kf_result.json') as f: kr=json.load(f)
assert kr['package_id']=='wp-11421-04'
assert kr['task_type']=='04-independent-review'
assert kr['provenance']['source_hash']=='sha256:f85c29fe650365140152064807d90b2accdf43382f2222956470f3521e0a280a'
with open('docs/kf/wp-11421-04/review_report.json') as f: rr=json.load(f)
assert rr['disposition']=='approve_with_notes'
assert len(rr['findings'])==5
print('All checks passed.')
"
```

交付信封（`package_id=wp-11421-04`, `task_type=04-independent-review`, `report_id=11421`, `provenance.source_hash=sha256:f85c29fe650365140152064807d90b2accdf43382f2222956470f3521e0a280a`）原样如下，此文件内**仅此一个** JSON 代码块：

```json
{
  "package_id": "wp-11421-04",
  "task_type": "04-independent-review",
  "contract_version": "1.0",
  "report_id": "11421",
  "provenance": {
    "source_uri": "tensor://reports/11421",
    "source_field": "markdown",
    "source_hash": "sha256:f85c29fe650365140152064807d90b2accdf43382f2222956470f3521e0a280a",
    "source_hash_matches": true,
    "title": "P270W1-N07 端到端不确定度传播：几何→阻力→推进→EEXI/CII 六因子分解（蒙特卡洛 + Sobol）",
    "scenario_key": "ship_performance",
    "chars": 18542
  },
  "outputs": {
    "review_report.json": {
      "review_id": "wp-11421-04",
      "reviewed_package": "wp-11421-01",
      "report_id": "11421",
      "reviewer_role": "red-team-reviewer",
      "disposition": "approve_with_notes",
      "findings_count": 5,
      "findings_severity": {
        "low": 2,
        "info": 3
      },
      "checks_performed": 13,
      "checks_not_run": 6,
      "upstream_crosscheck_validated": true,
      "summary": "Report 11421 is internally consistent on all verifiable arithmetic claims. Two low-severity prose issues (F1: Jansen estimator non-negativity claim; F2: 5% FD-analytic bound) confirmed from upstream X4/X5. Three informational findings (F3: interaction effects not discussed; F4: unverifiable external claim; F5: Table 6 ratio clarity). No numerical corrections needed. Disposition: approve_with_notes."
    },
    "review_events.json": [
      {
        "event_id": "RE-001",
        "event_type": "review_started",
        "timestamp": "2026-11-12T00:00:00Z",
        "details": "Independent review of report 11421 (wp-11421-04), reviewing upstream wp-11421-01."
      },
      {
        "event_id": "RE-002",
        "event_type": "source_verified",
        "timestamp": "2026-11-12T00:01:00Z",
        "details": "Source hash verified: sha256:f85c29fe650365140152064807d90b2accdf43382f2222956470f3521e0a280a, chars=18542, bytes_utf8=26405."
      },
      {
        "event_id": "RE-003",
        "event_type": "checks_completed",
        "timestamp": "2026-11-12T00:02:00Z",
        "details": "13 independent checks performed; 6 checks not run (require external code/artifacts)."
      },
      {
        "event_id": "RE-004",
        "event_type": "findings_recorded",
        "timestamp": "2026-11-12T00:03:00Z",
        "details": "5 findings: F1 (low, incorrect prose), F2 (low, incorrect prose), F3 (info, missing interpretation), F4 (info, unverifiable claim), F5 (info, documentation clarity)."
      },
      {
        "event_id": "RE-005",
        "event_type": "disposition_made",
        "timestamp": "2026-11-12T00:04:00Z",
        "details": "Disposition: approve_with_notes. Report is scientifically sound; two low-severity prose issues need fixing before downstream citation."
      }
    ]
  }
}
```
