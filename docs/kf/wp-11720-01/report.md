# KF-RESULT wp-11720-01

tags: kf-wp:wp-11720-01, FVM, DEM, two-phase, ice-floe, coupling, verification, ice-channel

## ① 本工序做了什么

工作包 `wp-11720-01`（工序 `01-asset-registration`）对报告 `report_id=11720`（标题：「FVM-DEM 碎冰场两相耦合成熟化验证：从单相水流到水流+浮冰双向耦合」）执行资产登记。确认源 markdown 字节哈希与契约一致，列出报告中可解析的附件/工件（4 张 figure 元数据、3 张表格），不做知识抽取（claims 为空数组）。

## ② 怎么做的（步骤/工具/关键设置）

1. **获取报告**：通过 `GET /api/v1/tensor/reports/11720`（Bearer token 认证）获取报告完整记录，提取 `markdown` 字段。
2. **哈希校验**：对 markdown 字段 UTF-8 编码字节计算 SHA-256，结果为 `sha256:d9d8b0a44cbd18c56e6d78706aa550c1d6e0d6649af816aa4a43d25d32791a59`，与契约 `source_hash` 完全一致。
3. **结构扫描**：正则扫描 markdown 标题（19 个 heading）、表格（3 张）、代码块（0 个）、文件引用（0 个）。
4. **figure 元数据登记**：从报告 record 的 `figures` 数组提取 4 张图的 name+caption，标记为 metadata-only（无 PNG payload）。
5. **表格定位**：以 line_span 方式记录 3 张表格在 markdown 中的行号范围。
6. **产物生成**：输出 `asset_manifest.json`（完整资产清单）和 `kf_result.json`（平台结果信封）。

## ③ 产出物清单

| 输出文件 | 要点 |
|---------|------|
| `docs/kf/wp-11720-01/asset_manifest.json` | 完整资产清单：4 figures（metadata-only）、3 tables（line_span 定位）、0 code blocks、0 file references；claims=[] |
| `docs/kf/wp-11720-01/kf_result.json` | 平台结果信封：package_id/task_type/report_id/provenance/outputs 五字段，source_hash 与契约一致 |

## ④ 证据定位表

| claim/字段 | 原文引文片段 | 定位 |
|-----------|------------|------|
| source_hash | `sha256:d9d8b0a44cbd18c56e6d78706aa550c1d6e0d6649af816aa4a43d25d32791a59` | 契约 contract.source_hash |
| title | `FVM-DEM 碎冰场两相耦合成熟化验证：从单相水流到水流+浮冰双向耦合` | report.title |
| scenario_key | `p348w2-n10-fvm-dem-ice-coupling` | report.scenario_key |
| chars | `2674` | len(markdown) |
| figure C1 | `C1_single_floe_drift` | report.figures[0].name |
| figure C3 | `C3_newton_third_law` | report.figures[1].name |
| figure C4 | `C4_multi_floe` | report.figures[2].name |
| figure C5 | `C5_grid_convergence` | report.figures[3].name |
| table T1 | `| 参数 | 值 | 单位 |` (line 10) | markdown §①/几何与参数 |
| table T2 | `| u_∞ (m/s) | v_drift (m/s) |` (line 43) | markdown §③/C1 |
| table T3 | `| 判据 | 关键量 | 误差 |` (line 96) | markdown §⑥ |

## ⑤ 注意点与局限

1. **仅登记不抽取**：本工序为 01-asset-registration，不做知识抽取，claims 为空数组（契约允许）。
2. **Figure 无 PNG payload**：报告 record 的 figures 数组仅含 name+caption，无 PNG 字节，故 figure 登记为 metadata-only。
3. **无外部文件引用**：报告 markdown 中未出现任何代码路径或工件路径引用，file_references 为空。
4. **表格以行号定位**：表格使用 line_span 定位，未对表格内容做独立字节哈希。
5. **verification 由平台门计算**：本工序不标记任何 claim 为 verified。

## ⑥ 自检：逐条对照 acceptance

| acceptance 条件 | 结果 | 说明 |
|----------------|------|------|
| valid_json | ✅ PASS | asset_manifest.json 和 kf_result.json 均为合法 JSON |
| schema_pass | ✅ PASS | kf_result.json 包含全部 required 字段（package_id/task_type/report_id/provenance/outputs），provenance 含 source_hash 和 source_field |
| source_locator_resolvable | ✅ PASS | source_uri=tensor://reports/11720 可通过 GET /api/v1/tensor/reports/11720 解析 |
| source_hash_matches | ✅ PASS | 本地计算 sha256=d9d8b0a44cbd18c56e6d78706aa550c1d6e0d6649af816aa4a43d25d32791a59，与契约一致 |
| no_duplicate_ids | ✅ PASS | asset_manifest 中 asset_id 无重复（T1/T2/T3 + 4 figures 各有唯一标识） |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ PASS | claims 为空数组（契约允许），无需证据 |

**全部 acceptance 条件通过。**

## 复现命令

```bash
# 1. 获取报告并验证哈希
python3 -c "
import urllib.request, json, hashlib
token = 'YOUR_TOKEN'
req = urllib.request.Request('http://127.0.0.1:8010/api/v1/tensor/reports/11720', headers={'Authorization': f'Bearer {token}'})
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
md = data['markdown']
h = hashlib.sha256(md.encode()).hexdigest()
assert h == 'd9d8b0a44cbd18c56e6d78706aa550c1d6e0d6649af816aa4a43d25d32791a59', f'Hash mismatch: {h}'
print('Hash verified:', h)
"

# 2. 验证 JSON 合法性
python3 -c "import json; json.load(open('docs/kf/wp-11720-01/asset_manifest.json')); json.load(open('docs/kf/wp-11720-01/kf_result.json')); print('JSON valid')"
```

```json
{
  "package_id": "wp-11720-01",
  "task_type": "01-asset-registration",
  "report_id": "11720",
  "provenance": {
    "source_hash": "sha256:d9d8b0a44cbd18c56e6d78706aa550c1d6e0d6649af816aa4a43d25d32791a59",
    "source_field": "markdown",
    "producer": "agent/m15729",
    "emitted_at": "2026-11-12T02:30:00+00:00",
    "notes": "Asset registration for report 11720: FVM-DEM ice-channel two-phase coupling verification. Hash verified against contract source_hash. 4 figures (metadata-only), 3 tables, 0 code blocks, 0 file references registered."
  },
  "outputs": {
    "asset_manifest.json": {
      "package_id": "wp-11720-01",
      "task_type": "01-asset-registration",
      "report_id": "11720",
      "source_hash_matches": true,
      "assets_registered": {
        "figures": 4,
        "tables": 3,
        "code_blocks": 0,
        "file_references": 0
      },
      "claims_count": 0,
      "path": "docs/kf/wp-11720-01/asset_manifest.json"
    }
  },
  "claims": []
}
```
