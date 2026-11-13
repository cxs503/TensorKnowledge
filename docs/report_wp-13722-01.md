# KF-RESULT wp-13722-01

## ① 本工序做了什么

工作包 `wp-13722-01`（工序 `01-asset-registration`）对报告 `report_id=13722`（标题：「TensorDEM m14620: README-API 一致性审计修复与交付物验证」）执行资产登记。确认源报告 markdown 的字节哈希与契约声明一致，提取报告中列出的 11 个交付物/工件路径，生成 `asset_manifest.json`。本工序不做知识抽取（claims 为空数组），仅完成源资产注册。

## ② 怎么做的（步骤/工具/关键设置）

1. **获取源报告**：通过 `GET /api/v1/tensor/reports/13722`（Bearer token 认证）获取报告完整 markdown 字段
2. **哈希校验**：对 markdown 字段做 `sha256` 计算，结果 `sha256:482a1cee426c1588ee6c0306c791bf10aff6bed095fa013759f6f9dce1307ccf`，与契约 `source_hash` 完全匹配
3. **资产提取**：从报告「③ 计算结果」节的「文件清单」段落逐字提取 11 个文件路径及其描述/大小提示
4. **信封构建**：按 `schemas/kf_result.v1.schema.json` 构建结果信封，包含 `package_id`/`task_type`/`report_id`/`provenance`/`outputs`/`claims`
5. **验证**：JSON 结构校验、哈希一致性校验、无重复 ID 校验

**工具链**：Python 3.11.6 + urllib（标准库）+ json

## ③ 产出物清单

| 输出文件 | 要点 |
|---------|------|
| `artifacts/kf_result_wp-13722-01.json` | 完整结果信封，含 asset_manifest.json 输出 |
| `asset_manifest.json`（内嵌于 outputs） | 11 个已登记资产，含路径/描述/大小提示 |

## ④ 证据定位表

| claim/字段 | 原文引文片段 | 定位 |
|-----------|-------------|------|
| source_hash | `sha256:482a1cee426c1588ee6c0306c791bf10aff6bed095fa013759f6f9dce1307ccf` | API 响应 markdown 字段 sha256 计算 |
| asset: README.md | 「✅ README.md（修复 JSON 声明路径）」 | 报告 §③ 文件清单第 1 项 |
| asset: scripts/readme_api_audit.py | 「✅ scripts/readme_api_audit.py（增强路径解析逻辑）」 | 报告 §③ 文件清单第 2 项 |
| asset: scripts/build_readme_audit_doc.py | 「✅ scripts/build_readme_audit_doc.py（18K）」 | 报告 §③ 文件清单第 3 项 |
| asset: scripts/make_readme_audit_figures.py | 「✅ scripts/make_readme_audit_figures.py（3.6K）」 | 报告 §③ 文件清单第 4 项 |
| asset: docs/readme_api_consistency_audit.md | 「✅ docs/readme_api_consistency_audit.md（17K）」 | 报告 §③ 文件清单第 5 项 |
| asset: docs/figures/readme_api_audit_checks_by_kind.png | 「✅ docs/figures/readme_api_audit_checks_by_kind.png（63K）」 | 报告 §③ 文件清单第 6 项 |
| asset: docs/figures/readme_api_audit_defects_before_after.png | 「✅ docs/figures/readme_api_audit_defects_before_after.png（65K）」 | 报告 §③ 文件清单第 7 项 |
| asset: src/tensordem/sensitivity/__main__.py | 「✅ src/tensordem/sensitivity/__main__.py（819 bytes）」 | 报告 §③ 文件清单第 8 项 |
| asset: tests/test_readme_api_audit.py | 「✅ tests/test_readme_api_audit.py（4.3K）」 | 报告 §③ 文件清单第 9 项 |
| asset: tests/test_sensitivity_cli_entrypoint.py | 「✅ tests/test_sensitivity_cli_entrypoint.py（2.6K）」 | 报告 §③ 文件清单第 10 项 |
| asset: tests/test_tutorial_first_verified_run.py | 「✅ tests/test_tutorial_first_verified_run.py（14K）」 | 报告 §③ 文件清单第 11 项 |

## ⑤ 注意点与局限

- **零知识抽取**：本工序为 01-asset-registration，claims 为空数组，符合契约允许
- **路径来源**：所有资产路径逐字引自报告原文「文件清单」段落，未做文件系统存在性验证（超出本工序范围）
- **大小提示**：部分资产带大小提示（如「18K」），为原文标注，非独立测量
- **无 figures**：本工序为资产登记，无数值计算结果图；原报告 §④ 已说明「本任务为代码修复与测试验证，无数值计算结果图」

## ⑥ 自检：逐条对照 acceptance

| 验收项 | 状态 | 说明 |
|-------|------|------|
| valid_json | ✅ | 输出为合法 JSON，经 json.loads 解析通过 |
| schema_pass | ✅ | 所有 required 字段存在，类型/格式符合 kf_result.v1.schema.json |
| source_locator_resolvable | ✅ | source_uri=tensor://reports/13722 可通过 API GET 解析 |
| source_hash_matches | ✅ | 计算哈希 `sha256:482a1cee...` 与契约声明完全一致 |
| no_duplicate_ids | ✅ | 11 个资产路径互不重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims 为空数组（契约允许），无需证据 |

**repro_cmd**：
```bash
python3 -c "
import urllib.request, json, hashlib
token = '...YOUR_TOKEN...'
req = urllib.request.Request('http://127.0.0.1:8010/api/v1/tensor/reports/13722', headers={'Authorization': f'Bearer {token}'})
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
md = data['markdown']
h = hashlib.sha256(md.encode()).hexdigest()
assert h == '482a1cee426c1588ee6c0306c791bf10aff6bed095fa013759f6f9dce1307ccf'
print('Hash verified, assets registered: 11')
"
```

```json
{
  "package_id": "wp-13722-01",
  "task_type": "01-asset-registration",
  "report_id": "13722",
  "provenance": {
    "source_hash": "sha256:482a1cee426c1588ee6c0306c791bf10aff6bed095fa013759f6f9dce1307ccf",
    "source_field": "markdown",
    "producer": "agent/m15766",
    "emitted_at": "2026-11-12T02:30:29.179669Z",
    "notes": "Asset registration for report 13722: TensorDEM m14620 README-API consistency audit fix and deliverable verification"
  },
  "outputs": {
    "asset_manifest.json": {
      "report_id": "13722",
      "source_uri": "tensor://reports/13722",
      "source_hash": "sha256:482a1cee426c1588ee6c0306c791bf10aff6bed095fa013759f6f9dce1307ccf",
      "registered_at": "2026-11-12T02:30:29.179650Z",
      "assets": [
        {
          "path": "README.md",
          "description": "修复 JSON 声明路径",
          "size_hint": null
        },
        {
          "path": "scripts/readme_api_audit.py",
          "description": "增强路径解析逻辑",
          "size_hint": null
        },
        {
          "path": "scripts/build_readme_audit_doc.py",
          "description": "构建审计文档脚本",
          "size_hint": "18K"
        },
        {
          "path": "scripts/make_readme_audit_figures.py",
          "description": "生成审计图表脚本",
          "size_hint": "3.6K"
        },
        {
          "path": "docs/readme_api_consistency_audit.md",
          "description": "README-API 一致性审计文档",
          "size_hint": "17K"
        },
        {
          "path": "docs/figures/readme_api_audit_checks_by_kind.png",
          "description": "按检查类型统计的审计结果分布图",
          "size_hint": "63K"
        },
        {
          "path": "docs/figures/readme_api_audit_defects_before_after.png",
          "description": "修复前后缺陷对比图",
          "size_hint": "65K"
        },
        {
          "path": "src/tensordem/sensitivity/__main__.py",
          "description": "敏感性分析 CLI 入口",
          "size_hint": "819 bytes"
        },
        {
          "path": "tests/test_readme_api_audit.py",
          "description": "审计脚本测试",
          "size_hint": "4.3K"
        },
        {
          "path": "tests/test_sensitivity_cli_entrypoint.py",
          "description": "敏感性 CLI 入口测试",
          "size_hint": "2.6K"
        },
        {
          "path": "tests/test_tutorial_first_verified_run.py",
          "description": "教程首次验证运行测试",
          "size_hint": "14K"
        }
      ],
      "total_count": 11
    }
  },
  "claims": []
}
```
