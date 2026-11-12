# KF-RESULT wp-6506-01

tags: kf-wp:wp-6506-01, asset-registration, report-6506, P34-N7

## ① 本工序做了什么

本工作包 `wp-6506-01`（工序 `01-asset-registration`）对报告 `report_id=6506` 执行源资产登记：
- 确认报告 ID 与其 markdown 字段的字节哈希（`sha256:195447357f5099ba51d2931c4daff233b23098fee7bdf8f53a1569b060f4877c`），与契约给定 `source_hash` 一致。
- 从报告 markdown 正文中逐字定位并登记 17 个可解析附件/工件（脚本 7、数据 2、测试 2、源码 3、图 4），每个工件均附 `source_locator` 指向原文位置。
- 不做知识抽取，`claims` 为空数组，符合 `01-asset-registration` 契约。

## ② 怎么做的（步骤/工具/关键设置）

1. **获取报告原文**：通过 `POST $TENSOR_API_BASE/auth/login` 获取 Bearer token，再 `GET $TENSOR_API_BASE/tensor/reports/6506` 取 `markdown` 字段（10846 字符）。
2. **哈希校验**：对 markdown 字符串做 UTF-8 编码后 `sha256` 计算，结果 `sha256:195447357f5099ba51d2931c4daff233b23098fee7bdf8f53a1569b060f4877c` 与契约 `source_hash` 逐字节一致。
3. **工件识别**：通读报告 markdown，从「附录：复算入口」表、正文 3.1/3.3/3.4/3.5 节、④ 结果图段、⑤ 注意点段中逐字提取所有被引用的文件路径，去重后登记为 17 个 artifact。
4. **JSON 校验**：用 Python `json.load()` 验证 `asset_manifest.json` 与 `kf_result.json` 均为合法 JSON；检查无重复 `artifact_id`、所有 artifact 均有 `source_locator`。
5. **Schema 对照**：按 `schemas/kf_result.v1.schema.json` 逐项核对 `package_id`/`task_type`/`report_id`/`provenance`/`outputs`/`claims` 字段类型与约束。

关键设置：零手抄——所有 `source_locator` 值均直接引用报告 markdown 原文中的章节名/表名/段落描述，不凭记忆重述。

## ③ 产出物清单

| 输出文件 | 要点 |
|---|---|
| `artifacts/wp-6506-01/asset_manifest.json` | 17 个工件登记，每个含 artifact_id/name/path/type/description/source_locator；claims=[] |
| `artifacts/wp-6506-01/kf_result.json` | kf_result.v1 信封：package_id=wp-6506-01, task_type=01-asset-registration, report_id=6506, provenance.source_hash 已校验, outputs 含 asset_manifest.json 摘要 |

## ④ 证据定位表（claim/字段 → 原文引文片段）

| 字段 | 原文引文片段 | 定位 |
|---|---|---|
| report_id | 契约给定 `report_id: '6506'` | 工作包契约 input 节 |
| source_hash | `sha256:195447357f5099ba51d2931c4daff233b23098fee7bdf8f53a1569b060f4877c` | 契约 input.source_hash；API 返回 markdown 重算一致 |
| title | `P34-N7 报告归属门与判据变异门成熟化：403 归属阻断 + PNG 魔数门 + 全台账 KPI（PAPER-TRACE kill rate 97.8%）` | 契约 input.title；API 返回 report.title 一致 |
| chars | `10846` | 契约 input.chars；API 返回 markdown len() 一致 |
| artifact art-6506-001 | `artifacts/m5496/make_report_payload.py` | 报告正文「附录：复算入口」表第一行 |
| artifact art-6506-002 | `artifacts/m5496/make_figures.py` | 报告正文「附录：复算入口」表第六行 |
| artifact art-6506-003 | `artifacts/m5496/criteria_mutation_ledger.json` | 报告正文「附录：复算入口」表第三行 |
| artifact art-6506-004 | `artifacts/m5496/probe_kill.py` | 报告正文 3.4 节及「附录：复算入口」表第五行 |
| artifact art-6506-005 | `artifacts/m5496/test_runs.json` | 报告正文 3.5 节 C5 判据引用 |
| artifact art-6506-006 | `tools/audit/domain_leak_scan.py` | 报告正文 3.5 节 C12 判据及「附录：复算入口」表第七行 |
| artifact art-6506-007 | `tools/audit/criteria_mutation.py` | 报告正文「附录：复算入口」表第三行 |
| artifact art-6506-008 | `tools/audit/paper_gate_mutation_audit.py` | 报告正文「附录：复算入口」表第四行 |
| artifact art-6506-009 | `tests/test_report_ownership.py` | 报告正文 ⑤ 注意点第 5 条及「附录：复算入口」表第一行 |
| artifact art-6506-010 | `tests/test_criteria_mutation.py` | 报告正文「附录：复算入口」表第二行 |
| artifact art-6506-011 | `backend/services/report_ownership.py` | 报告正文 ⑤ 注意点第 3/4 条及「附录：复算入口」表第七行 |
| artifact art-6506-012 | `backend/api/tensor_reports.py` | 报告正文「附录：复算入口」表第七行 |
| artifact art-6506-013 | `tools/report_payload.py` | 报告正文「附录：复算入口」表第七行 |
| artifact art-6506-014 | `artifacts/m5496/fig1_killrate_by_gate.png` | 报告正文 ④ 结果图第一段 |
| artifact art-6506-015 | `artifacts/m5496/fig2_m1_monotonic.png` | 报告正文 ④ 结果图第二段 |
| artifact art-6506-016 | `artifacts/m5496/fig3_paper_trace_ast.png` | 报告正文 ④ 结果图第三段 |
| artifact art-6506-017 | `artifacts/m5496/fig4_criteria_heatmap.png` | 报告正文 ④ 结果图第四段 |

## ⑤ 注意点与局限

1. **仅登记不抽取**：本工序为 `01-asset-registration`，只确认源资产哈希与列出可解析工件，不做知识抽取（claims 为空）。
2. **工件路径未验证存在性**：所有 artifact path 均从报告 markdown 原文中提取，但未在本地工作树中验证这些文件实际存在（它们属于上游仓 `TensorPlatform` 的 `agent/m5496` 分支）。
3. **零手抄纪律**：所有 source_locator 值均逐字来自报告 markdown 原文，未凭记忆重述任何数字或描述。
4. **无图产出**：本工序为纯资产登记任务，不涉及计算/仿真/可视化，故无结果图。

## ⑥ 自检：逐条对照 acceptance 打勾/叉

| 验收项 | 状态 | 说明 |
|---|---|---|
| valid_json | ✅ | `asset_manifest.json` 与 `kf_result.json` 均通过 `json.load()` 解析 |
| schema_pass | ✅ | kf_result 含全部 required 字段（package_id/task_type/report_id/provenance/outputs），类型与 pattern 均符合 v1 schema |
| source_locator_resolvable | ✅ | 17 个 artifact 的 source_locator 均指向报告 markdown 中可定位的章节/表/段落 |
| source_hash_matches | ✅ | 本地重算 `sha256:195447357f5099ba51d2931c4daff233b23098fee7bdf8f53a1569b060f4877c` 与契约一致 |
| no_duplicate_ids | ✅ | 17 个 artifact_id 全部唯一（art-6506-001 至 art-6506-017） |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims 为空数组，符合 01-asset-registration 契约（允许为空） |

**repro_cmd**: `python3 -c "import json; json.load(open('artifacts/wp-6506-01/asset_manifest.json')); json.load(open('artifacts/wp-6506-01/kf_result.json')); print('OK')"`

```json
{
  "package_id": "wp-6506-01",
  "task_type": "01-asset-registration",
  "report_id": "6506",
  "provenance": {
    "source_hash": "sha256:195447357f5099ba51d2931c4daff233b23098fee7bdf8f53a1569b060f4877c",
    "source_field": "markdown",
    "producer": "tp-agent",
    "emitted_at": "2026-11-12T01:26:04Z",
    "notes": "Asset registration for report 6506 (P34-N7). Source hash verified against platform API response. 17 artifacts identified from report markdown text. Claims array is empty per 01-asset-registration contract."
  },
  "outputs": {
    "asset_manifest.json": {
      "report_id": "6506",
      "source_uri": "tensor://reports/6506",
      "source_field": "markdown",
      "source_hash": "sha256:195447357f5099ba51d2931c4daff233b23098fee7bdf8f53a1569b060f4877c",
      "title": "P34-N7 报告归属门与判据变异门成熟化：403 归属阻断 + PNG 魔数门 + 全台账 KPI（PAPER-TRACE kill rate 97.8%）",
      "scenario_key": "P34-N7",
      "chars": 10846,
      "artifact_count": 17,
      "claim_count": 0,
      "artifact_types": {
        "script": 7,
        "data": 2,
        "test": 2,
        "source": 3,
        "figure": 4
      }
    }
  },
  "claims": []
}
```
