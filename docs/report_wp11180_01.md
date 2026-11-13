# KF-RESULT wp-11180-01

tags: kf-wp:wp-11180-01, asset-registration, eexi, green_shipping, p74-n02

## 1. 本工序做了什么

工作包 `wp-11180-01`（工序 `01-asset-registration`）对报告 `report_id=11180`（标题：EEXI Attained 闭合链路精度传递验证 (P74-N02)）进行源资产登记。确认报告 markdown 的字节哈希与契约一致，识别并定位报告中引用的 4 个附件/工件，生成 `asset_manifest.json` 与 `kf_result` 信封。本工序不做知识抽取（`classify_report_type=false`），`claims` 为空数组。

## 2. 怎么做的（步骤/工具/关键设置）

1. **获取报告原文**：通过平台 API `GET /api/v1/tensor/reports/11180`（Bearer token 认证）获取 `markdown` 字段，共 490 字符 / 670 字节 UTF-8。
2. **哈希校验**：本地计算 `sha256(markdown.encode('utf-8'))`，结果为 `9adfdac400ff0e205a17c20a761625acca0acf0e55f9ff477bf2c1c5c8bf3292`，与契约 `source_hash` 完全一致。
3. **资产识别**：在报告「产物」段落（char 252–451）中识别 4 个引用资产：
   - A01: `backend/api/green_shipping.py::_gn_eexi_from_physics()`（实现）
   - A02: `backend/tests/test_eexi_chain_p74n02.py`（测试）
   - A03: `artifacts/eexi_verification.json`（验证工件）
   - A04: `docs/eexi_verification_report_p74n02.md`（报告）
4. **定位记录**：对每个资产记录 `char_span` 定位（start_char/end_char/start_line/end_line/quote），验证 quote 在原文中唯一出现。
5. **分辨率判定**：4 个资产均为 `referenced_unresolved`（引用存在但文件不在本工作树内，无法验证存在性）。
6. **产物生成**：按 `asset_manifest.v1` schema 生成 `asset_manifest.json`，按 `kf_result.v1` schema 生成结果信封。

**工具链**：Python 3 (stdlib `json`, `hashlib`, `urllib`)，无外部依赖。
**关键设置**：UTF-8 编码，sha256 哈希，char_span 定位法。

## 3. 产出物清单

| 输出文件 | 要点 |
|---|---|
| `artifacts/asset_manifest_wp11180_01.json` | 4 个资产登记，含 char_span 定位、分辨率判定、完整性校验 |
| `artifacts/kf_result_wp11180_01.json` | KF 结果信封，含 provenance（source_hash 匹配）、outputs（asset_manifest）、空 claims |

## 4. 证据定位表

| claim/字段 | 原文引文片段 | 位置 |
|---|---|---|
| source_hash | `sha256:9adfdac400ff0e205a17c20a761625acca0acf0e55f9ff477bf2c1c5c8bf3292` | 本地计算，与契约一致 |
| A01 quote | `backend/api/green_shipping.py::_gn_eexi_from_physics()` | char 264–318, line 16 |
| A02 quote | `backend/tests/test_eexi_chain_p74n02.py` | char 325–364, line 17 |
| A03 quote | `artifacts/eexi_verification.json` | char 371–403, line 18 |
| A04 quote | `docs/eexi_verification_report_p74n02.md` | char 410–449, line 19 |
| 三船对标误差 | `12.1% / 7.0% / 1.0% (均 <15%)` | char 113–143, line 10 |
| 能力结论 | `EEXI attained 能力: WITHHELD → REAL` | char 452–490, line 22 |

## 5. 注意点与局限

- **资产分辨率**：4 个资产均为 `referenced_unresolved`——它们在报告中被引用，但文件路径属于 `ship-performance-platform` 或其他仓库，不在本 TensorKnowledge 工作树内。要升级为 `resolved_in_source` 需在对应仓库中验证文件存在。
- **零 claims**：本工序目标为资产登记（`classify_report_type=false`），不抽取知识主张，故 claims 为空数组。这是契约允许的合法状态。
- **无图**：本任务为文档/后端资产登记工序，无数值计算输出，故无场量云图或比较曲线。
- **哈希一致性**：source_hash 经本地重算与契约完全匹配，平台门将独立二次确认。

## 6. 自检：acceptance 逐项对照

| 验收项 | 状态 | 说明 |
|---|---|---|
| `valid_json` | ✅ | asset_manifest.json 与 kf_result.json 均通过 `json.load()` 解析 |
| `schema_pass` | ✅ | 字段名/类型/必填项符合 `asset_manifest.v1` 与 `kf_result.v1` schema |
| `source_locator_resolvable` | ✅ | 4 个资产的 char_span 定位均在原文范围内，quote 唯一可查 |
| `source_hash_matches` | ✅ | 本地计算 `sha256:9adfdac4...3292` = 契约值 |
| `no_duplicate_ids` | ✅ | asset_id 为 A01–A04，无重复 |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✅ | claims 为空数组（合法），无未处理主张 |

**结论**：全部 acceptance 项通过，无 honest-FAIL。

## 复跑命令

```bash
cd /root/tp-agent/work/m15692
python3 scripts/kf_register_11180.py
```

（脚本将重新从 API 拉取报告、校验哈希、生成 asset_manifest 与 kf_result）

```json
{
  "package_id": "wp-11180-01",
  "task_type": "01-asset-registration",
  "report_id": "11180",
  "provenance": {
    "source_hash": "sha256:9adfdac400ff0e205a17c20a761625acca0acf0e55f9ff477bf2c1c5c8bf3292",
    "source_field": "markdown",
    "producer": "agent/m15692",
    "emitted_at": "2026-11-12T01:52:00+00:00",
    "notes": "Asset registration for EEXI attained verification report. 4 assets identified in 产物 section, all referenced_unresolved (external to this worktree)."
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-11180-01",
      "task_type": "01-asset-registration",
      "report_id": "11180",
      "source": {
        "uri": "tensor://reports/11180",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "9adfdac400ff0e205a17c20a761625acca0acf0e55f9ff477bf2c1c5c8bf3292",
        "chars": 490,
        "bytes_utf8": 670,
        "title": "EEXI Attained 闭合链路精度传递验证 (P74-N02)",
        "scenario_key": "green_shipping_eexi_chain"
      },
      "counts": {
        "assets": 4,
        "by_class": {
          "implementation": 1,
          "test": 1,
          "verification_artifact": 1,
          "report": 1
        },
        "by_resolution": {
          "referenced_unresolved": 4
        },
        "resolved_in_source": 0,
        "referenced_unresolved": 4,
        "declared_absent": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "implementation",
          "label": "EEXI attained 计算实现",
          "in_report_section": "产物",
          "locator": {
            "method": "char_span",
            "start_char": 264,
            "end_char": 318,
            "start_line": 16,
            "end_line": 16,
            "quote": "backend/api/green_shipping.py::_gn_eexi_from_physics()",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_worktree",
            "result": "unresolved"
          },
          "note": "EEXI attained 物理计算链路实现函数"
        },
        {
          "asset_id": "A02",
          "asset_class": "test",
          "label": "EEXI 闭合链路测试",
          "in_report_section": "产物",
          "locator": {
            "method": "char_span",
            "start_char": 325,
            "end_char": 364,
            "start_line": 17,
            "end_line": 17,
            "quote": "backend/tests/test_eexi_chain_p74n02.py",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_worktree",
            "result": "unresolved"
          },
          "note": "EEXI 端到端链路验证测试"
        },
        {
          "asset_id": "A03",
          "asset_class": "verification_artifact",
          "label": "EEXI 验证数据",
          "in_report_section": "产物",
          "locator": {
            "method": "char_span",
            "start_char": 371,
            "end_char": 403,
            "start_line": 18,
            "end_line": 18,
            "quote": "artifacts/eexi_verification.json",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_worktree",
            "result": "unresolved"
          },
          "note": "EEXI 验证结果 JSON 工件"
        },
        {
          "asset_id": "A04",
          "asset_class": "report",
          "label": "EEXI 验证报告",
          "in_report_section": "产物",
          "locator": {
            "method": "char_span",
            "start_char": 410,
            "end_char": 449,
            "start_line": 19,
            "end_line": 19,
            "quote": "docs/eexi_verification_report_p74n02.md",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "file_exists_in_worktree",
            "result": "unresolved"
          },
          "note": "EEXI 验证详细报告文档"
        }
      ],
      "claims": [],
      "integrity": {
        "quote_uniqueness": "all_unique",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true
      }
    }
  },
  "claims": []
}
```
