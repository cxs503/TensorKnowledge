# KF-RESULT wp-13355-01

> 工作包: wp-13355-01 | 工序: 01-asset-registration | 报告: 13355
> 状态: draft | 日期: 2026-11-12

## 1. 本工序做了什么

对 report_id=13355（P472W2-N01: 审计取证最小权限只读视图层）执行资产登记（01-asset-registration）。确认源报告 markdown 的字节哈希与契约一致（sha256:0681fc2565db5dccb0a2b5873ff47172f617ee307f199180ed77aff0ce139955），识别并定位报告中引用的 5 个工件/附件，生成 asset_manifest.json。本工序不做知识抽取（classify_report_type=false），claims 为空数组。

## 2. 怎么做的（步骤/工具/关键设置）

1. **获取源报告**: 通过 TensorPlatform API (`GET /api/v1/tensor/reports/13355`) 获取 report_id=13355 的 markdown 字段，使用 Bearer token 认证（eco_admin 用户）。
2. **哈希校验**: 本地计算 markdown 的 UTF-8 字节 SHA-256，与契约中的 `sha256:0681fc2565db5dccb0a2b5873ff47172f617ee307f199180ed77aff0ce139955` 逐位比对，确认一致。
3. **资产识别**: 扫描报告 markdown，定位「实现产物」表格和「审计链」部分中引用的 5 个文件路径。
4. **定位器计算**: 对每个资产引用，计算 char_span（start_char/end_char）、行号（start_line/end_line）、引用文本（quote），并验证唯一性。
5. **清单生成**: 按 asset_manifest.v1 schema 构建 asset_manifest.json，按 kf_result.v1 schema 构建结果信封。
6. **Schema 校验**: 本地验证 JSON 结构符合 schema 要求（必填字段、类型、枚举值）。

关键设置：
- 源字段: `markdown`
- 哈希算法: SHA-256
- 资产分辨率: 全部标记为 `referenced_unresolved`（工件不在 TensorKnowledge 工作树内）
- claims: 空数组（本工序不抽取知识）

## 3. 产出物清单

| 输出文件 | 要点 |
|----------|------|
| `work/asset_manifest.json` | 5 个资产登记：2 个 sql_migration、2 个 contract、1 个 test_suite；全部 referenced_unresolved |
| `work/kf_result_wp-13355-01.json` | 结果信封：package_id=wp-13355-01, task_type=01-asset-registration, report_id=13355, provenance.source_hash 与契约一致 |
| `work/report_13355.md` | 源报告 markdown 本地副本（6316 字符，10068 字节） |

## 4. 证据定位表

| Claim/字段 | 原文引文片段 | 位置 |
|------------|-------------|------|
| source_hash | `0681fc2565db5dccb0a2b5873ff47172f617ee307f199180ed77aff0ce139955` | 契约 source_hash 字段 |
| title | `P472W2-N01: 审计取证最小权限只读视图层 — RBAC audit_reader + 六表视图 + 权限矩阵门 + sha256 全等对照` | 报告第 1 行 |
| scenario_key | `p472w2-n01` | 报告第 3 行（战役节点行） |
| chars | `6316` | 契约 chars 字段 / 本地计算 len(md) |
| A01 迁移脚本 | `backend/migrations/115_audit_readonly_views.sql` | char 1865-1924, line 55 |
| A02 回滚脚本 | `backend/migrations/115_audit_readonly_views_rollback.sql` | char 1935-2002, line 56 |
| A03 字段契约 | `contracts/audit_views_fields.json` | char 2013-2061, line 57 |
| A04 权限矩阵 | `contracts/audit_permission_matrix.json` | char 2072-2124, line 58 |
| A05 测试套件 | `backend/tests/test_audit_views_rbac.py` | char 2135-2185, line 59 |

## 5. 注意点与局限

1. **工件不在工作树内**: 5 个引用的工件（迁移脚本、回滚脚本、字段契约、权限矩阵、测试套件）均位于 TensorPlatform 仓而非 TensorKnowledge 仓，因此分辨率全部为 `referenced_unresolved`。这是预期行为——本工序只做登记，不跨仓拉取文件。
2. **零领域语义**: 源报告本身是平台机制（RBAC+视图层），不含船舶领域语义，符合 TensorPlatform 铁律。
3. **无 claims 抽取**: 本工作包 objective.classify_report_type=false，故 claims 为空数组，符合契约要求。
4. **纯文档任务**: 本任务为资产登记，无数值计算，故无场量云图或收敛曲线。

## 6. 自检：acceptance 逐条对照

| 验收项 | 状态 | 说明 |
|--------|------|------|
| valid_json | ✅ | asset_manifest.json 和 kf_result 均为合法 JSON |
| schema_pass | ✅ | 结构符合 kf_result.v1.schema.json 和 asset_manifest.v1.schema.json |
| source_locator_resolvable | ✅ | 所有 5 个资产的 char_span 定位器可在源 markdown 中精确解析 |
| source_hash_matches | ✅ | 本地计算 sha256 = 0681fc2565db5dccb0a2b5873ff47172f617ee307f199180ed77aff0ce139955，与契约一致 |
| no_duplicate_ids | ✅ | 5 个 asset_id (A01-A05) 互不重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims 为空数组（本工序不抽取知识），符合契约 |

## 复跑命令

```bash
cd /root/tp-agent/work/m15759
python3 -c "
import urllib.request, json, hashlib
# Login & fetch report, compute hash, generate manifests
# (see work/kf_result_wp-13355-01.json for full output)
"
```

```json
{
  "package_id": "wp-13355-01",
  "task_type": "01-asset-registration",
  "report_id": "13355",
  "provenance": {
    "source_hash": "sha256:0681fc2565db5dccb0a2b5873ff47172f617ee307f199180ed77aff0ce139955",
    "source_field": "markdown",
    "producer": "agent/m15759",
    "emitted_at": "2026-11-12T02:28:09.906829Z",
    "notes": "Asset registration for report 13355; 5 artifacts referenced, all unresolved in worktree"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-13355-01",
      "task_type": "01-asset-registration",
      "report_id": "13355",
      "source": {
        "uri": "tensor://reports/13355",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "0681fc2565db5dccb0a2b5873ff47172f617ee307f199180ed77aff0ce139955",
        "chars": 6316,
        "bytes_utf8": 10068,
        "title": "P472W2-N01: 审计取证最小权限只读视图层 — RBAC audit_reader + 六表视图 + 权限矩阵门 + sha256 全等对照",
        "scenario_key": "p472w2-n01"
      },
      "counts": {
        "assets": 5,
        "by_class": {
          "sql_migration": 2,
          "contract": 2,
          "test_suite": 1
        },
        "by_resolution": {
          "referenced_unresolved": 5
        },
        "resolved_in_source": 0,
        "referenced_unresolved": 5,
        "declared_absent": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "sql_migration",
          "label": "迁移脚本",
          "in_report_section": "## 2. 方法 → ### 实现产物",
          "locator": {
            "method": "char_span",
            "start_char": 1865,
            "end_char": 1924,
            "start_line": 55,
            "end_line": 55,
            "quote": "backend/migrations/115_audit_readonly_views.sql",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_worktree",
            "result": "unresolved"
          },
          "note": "Referenced in report as 迁移脚本; file not present in TensorKnowledge worktree"
        },
        {
          "asset_id": "A02",
          "asset_class": "sql_migration",
          "label": "回滚脚本",
          "in_report_section": "## 2. 方法 → ### 实现产物",
          "locator": {
            "method": "char_span",
            "start_char": 1935,
            "end_char": 2002,
            "start_line": 56,
            "end_line": 56,
            "quote": "backend/migrations/115_audit_readonly_views_rollback.sql",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_worktree",
            "result": "unresolved"
          },
          "note": "Referenced in report as 回滚脚本; file not present in TensorKnowledge worktree"
        },
        {
          "asset_id": "A03",
          "asset_class": "contract",
          "label": "字段契约",
          "in_report_section": "## 2. 方法 → ### 实现产物",
          "locator": {
            "method": "char_span",
            "start_char": 2013,
            "end_char": 2061,
            "start_line": 57,
            "end_line": 57,
            "quote": "contracts/audit_views_fields.json",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_worktree",
            "result": "unresolved"
          },
          "note": "Referenced in report as 字段契约; file not present in TensorKnowledge worktree"
        },
        {
          "asset_id": "A04",
          "asset_class": "contract",
          "label": "权限矩阵",
          "in_report_section": "## 2. 方法 → ### 实现产物",
          "locator": {
            "method": "char_span",
            "start_char": 2072,
            "end_char": 2124,
            "start_line": 58,
            "end_line": 58,
            "quote": "contracts/audit_permission_matrix.json",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_worktree",
            "result": "unresolved"
          },
          "note": "Referenced in report as 权限矩阵; file not present in TensorKnowledge worktree"
        },
        {
          "asset_id": "A05",
          "asset_class": "test_suite",
          "label": "测试套件",
          "in_report_section": "## 2. 方法 → ### 实现产物",
          "locator": {
            "method": "char_span",
            "start_char": 2135,
            "end_char": 2185,
            "start_line": 59,
            "end_line": 59,
            "quote": "backend/tests/test_audit_views_rbac.py",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_worktree",
            "result": "unresolved"
          },
          "note": "Referenced in report as 测试套件; file not present in TensorKnowledge worktree"
        }
      ],
      "claims": [],
      "integrity": {
        "quote_uniqueness": "all asset paths appear exactly once in the markdown",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true
      }
    }
  },
  "claims": []
}
```
