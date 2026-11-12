# KF-RESULT wp-8510-01

**tags**: `kf-wp:wp-8510-01`, `asset-registration`, `green_navigation_eexi_units`

---

## ① 本工序做了什么

本工作包执行 **01-asset-registration**（源资产登记）工序，对 report_id=8510 进行资产登记：

- 确认 report_id=8510 存在且可访问
- 获取 markdown 字段并计算 sha256 哈希
- 验证哈希与契约声明一致：`sha256:89c40d5daaece7b52882a5d137706680a8132e886aa8922092461a8d15208ad7`
- 解析报告结构：9 个章节、7 张表格、1 张图、7 处代码引用
- 登记 5 项未解决资产（unresolved_assets）
- **不做知识抽取**：claims 数组为空，由后续工作包（如 02-claim-extraction）填充

---

## ② 怎么做的（步骤/工具/关键设置）

### 步骤

1. **获取报告**：通过平台 API `GET /tensor/reports/8510` 获取完整报告 payload
2. **哈希验证**：对 markdown 字段计算 sha256，与契约声明的 `89c40d5daaece7b52882a5d137706680a8132e886aa8922092461a8d15208ad7` 比对
3. **结构解析**：
   - 按 `## ` 标记切分章节
   - 识别表格（`|---|` 模式）
   - 识别图片引用（`![...](...)` 模式）
   - 识别代码文件引用（`backend/`、`tools/`、`artifacts/` 路径）
4. **资产登记**：按 wp-446-01 模板生成 asset_manifest.json
5. **结果封装**：按 kf_result.v1.schema.json 生成结果信封

### 工具

- Python 3 + urllib.request（API 访问）
- hashlib.sha256（哈希计算）
- json（序列化/反序列化）

### 关键设置

- API 端点：`$TENSOR_API_BASE/tensor/reports/8510`
- 认证：Bearer token（通过 `/auth/login` 获取）
- 哈希算法：sha256（UTF-8 编码）

---

## ③ 产出物清单

| 输出文件 | 路径 | 要点 |
|---|---|---|
| asset_manifest.json | `docs/wp-8510-01_asset_manifest.json` | 完整资产登记：9 章节、7 表格、1 图、7 代码引用、5 未解决资产 |
| kf_result.json | `runs/wp-8510-01/kf_result.json` | 结果信封（schema v1 合规） |
| report_8510.md | `runs/wp-8510-01/report_8510.md` | 原始 markdown（10454 字符） |
| report_8510.json | `runs/wp-8510-01/report_8510.json` | 原始 API payload |

---

## ④ 证据定位表

| 字段/声明 | 原文引文片段 | 位置 |
|---|---|---|
| report_id | `8510` | API payload `id` 字段 |
| title | `P248-N07 绿色航行 EEXI 达到值量纲缺陷修复与单位账本门成熟化（缺陷因子 1852，修后误差 5.1e-14%）` | API payload `title` 字段 |
| scenario_key | `green_navigation_eexi_units` | API payload `scenario_key` 字段 |
| source_hash | `sha256:89c40d5daaece7b52882a5d137706680a8132e886aa8922092461a8d15208ad7` | 契约声明 + 独立计算验证 |
| source_length_chars | `10454` | markdown 字段长度 |
| report_status | `published` | API payload `status` 字段 |
| report_created_at | `2026-11-08T12:21:20.965413+00:00` | API payload `created_at` 字段 |
| report_tags | `['EEXI', 'EEDI', '量纲账本', 'green_navigation', 'P248-N07', 'defect_fix', 'unit_ledger']` | API payload `tags` 字段 |
| sections[0].heading | `1 案例介绍（物理背景 / 参数 / 量纲）` | markdown line 12 |
| tables[0].id | `tbl-8510-params` | markdown section 1.3 |
| figures[0].name | `eexi_units_before_after` | markdown section 4 |
| code_references[0].file | `backend/api/green_shipping.py` | markdown section 5 |
| unresolved_assets[0].id | `ua-8510-fig-png` | 图 PNG 未内嵌 |

---

## ⑤ 注意点与局限

1. **零手抄纪律**：所有数字/引文均从 API payload 和 markdown 原文逐字提取，未凭记忆重述
2. **不做知识抽取**：本工序仅登记资产，不提取 claims；claims 数组为空是合法的（见契约 `no_forced_claim_generation: true`）
3. **未解决资产**：
   - 图 PNG 未内嵌（仅有元数据引用）
   - gate_numbers.json 位于 artifacts/ 但未在工作树内
   - 2 处遗留重复服务未在本节点修复
   - 1 处相邻缺陷（virtual_data_models.py:20）与本节点无关
   - 规则系数层仍为 WITHHELD（未回读 IMO 原文）
4. **哈希验证**：独立计算 sha256 与契约声明一致，平台可独立重算做二次确认
5. **不标记 verified**：按契约约束 `do_not_mark_claims_as_verified: true`，所有声明保持原始状态

---

## ⑥ 自检（逐条对照 acceptance）

| 验收项 | 结果 | 说明 |
|---|---|---|
| valid_json | ✅ | asset_manifest.json 和 kf_result.json 均为合法 JSON |
| schema_pass | ✅ | kf_result.json 符合 kf_result.v1.schema.json（package_id/task_type/report_id/provenance/outputs 必填字段齐全） |
| source_locator_resolvable | ✅ | 所有引文均可在 markdown 原文中定位（行号/章节/文件路径） |
| source_hash_matches | ✅ | 独立计算 sha256=89c40d5daaece7b52882a5d137706680a8132e886aa8922092461a8d15208ad7，与契约声明一致 |
| no_duplicate_ids | ✅ | 所有 id 字段（tbl-8510-*, fig-8510-*, code-8510-*, ua-8510-*）均唯一 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims 为空数组（合法）；unresolved_assets 均有 explicit status="unresolved" |

**honest-FAIL 声明**：无失败项。所有验收条件均满足。

---

## 复现命令

```bash
cd /root/tp-agent/work/m15623
python3 scripts/kf_fetch_8510.py
# 输出：runs/wp-8510-01/report_8510.md 和 report_8510.json
# 验证：sha256(markdown) == 89c40d5daaece7b52882a5d137706680a8132e886aa8922092461a8d15208ad7
```

---

```json
{
  "package_id": "wp-8510-01",
  "task_type": "01-asset-registration",
  "report_id": "8510",
  "provenance": {
    "source_hash": "sha256:89c40d5daaece7b52882a5d137706680a8132e886aa8922092461a8d15208ad7",
    "source_field": "markdown",
    "producer": "agent-wp-8510-01",
    "emitted_at": "2026-11-12T01:30:00Z",
    "notes": "Source report fetched via platform API /tensor/reports/8510; sha256 verified against contract expectation."
  },
  "outputs": {
    "asset_manifest.json": {
      "package_id": "wp-8510-01",
      "task_type": "01-asset-registration",
      "report_id": 8510,
      "source_uri": "tensor://reports/8510",
      "source_hash": "sha256:89c40d5daaece7b52882a5d137706680a8132e886aa8922092461a8d15208ad7",
      "source_hash_verified": true,
      "source_field": "markdown",
      "source_length_chars": 10454,
      "title": "P248-N07 绿色航行 EEXI 达到值量纲缺陷修复与单位账本门成熟化（缺陷因子 1852，修后误差 5.1e-14%）",
      "scenario_key": "green_navigation_eexi_units",
      "report_status": "published",
      "report_created_at": "2026-11-08T12:21:20.965413+00:00",
      "report_tags": ["EEXI", "EEDI", "量纲账本", "green_navigation", "P248-N07", "defect_fix", "unit_ledger"],
      "sections_count": 9,
      "tables_count": 7,
      "figures_count": 1,
      "code_references_count": 7,
      "unresolved_assets_count": 5,
      "claims_count": 0,
      "claims_note": "本工作包为 01-asset-registration（源资产登记），不做抽取。claims 留空，由后续工作包填充。"
    }
  },
  "claims": []
}
```
