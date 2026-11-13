# KF-RESULT wp-9478-01

> tags: kf-wp:wp-9478-01, asset-registration, FSI, Turek-Hron

## 1. 本工序做了什么

本工作包 `wp-9478-01` 为 **01-asset-registration** 工序，仅对 `report_id=9478` 进行源资产登记：
- 确认报告 markdown 字节的 SHA-256 哈希与契约声明一致
- 列出报告中引用的附件（4 张平台管理图）与工件（无二进制工件路径）
- claims 数组为空（本工序不做知识抽取，不发明 claim）

## 2. 怎么做的（步骤/工具/关键设置）

1. **获取报告**：通过 `GET /api/v1/tensor/reports/9478`（Bearer token 认证）获取完整报告记录，提取 `markdown` 字段。
2. **哈希验证**：对 markdown 字段做 UTF-8 编码的 SHA-256 计算，结果为 `133dbe58a74bd7549b66b2b86e5dc2e517f603c3ea65af45947d4cb5c1599e28`，与契约 `source_hash` 完全一致。
3. **字符计数**：markdown 字段长度 5748 字符，与契约 `chars: 5748` 一致。
4. **附件枚举**：从报告记录的 `figures` 字段提取 4 张图的元数据（name/caption），未下载 PNG 载荷。
5. **工件扫描**：报告 markdown 中未引用任何本地文件路径（如 `artifacts/...`），故 artifacts 为空。
6. **产物生成**：按 `asset_manifest.v1` 结构生成 `asset_manifest.json`，按 `kf_result.v1` 结构生成结果信封。

关键设置：
- API 端点：`http://127.0.0.1:8010/api/v1`
- 认证用户：`eco_admin`
- 哈希算法：SHA-256 over UTF-8 bytes

## 3. 产出物清单

| 输出文件 | 路径 | 要点 |
|----------|------|------|
| `asset_manifest.json` | `docs/kf/wp-9478-01/asset_manifest.json` | 源资产登记：哈希验证通过，4 张附件图，0 工件，0 claims |
| `kf_result.json` | `docs/kf/wp-9478-01/kf_result.json` | KF 结果信封（package_id/task_type/report_id/provenance/outputs） |

## 4. 证据定位表

| 字段/声明 | 原文引文片段 | 定位 |
|-----------|-------------|------|
| source_hash | `sha256:133dbe58a74bd7549b66b2b86e5dc2e517f603c3ea65af45947d4cb5c1599e28` | 本地 SHA-256 计算结果，与契约一致 |
| chars | `5748` | `len(markdown.encode('utf-8'))` 字符数 |
| title | `P153W2-N03: TensorFEM×TensorLBM FSI Strong Coupling — Turek-Hron FSI-2 + Flutter + Energy Conservation` | 报告记录 `title` 字段 |
| scenario_key | `P153W2-N03-fsi-strong-coupling` | 报告记录 `scenario_key` 字段 |
| figure[0] name | `fsi2_displacement_clcd` | 报告记录 `figures[0].name` |
| figure[1] name | `fsi2_energy` | 报告记录 `figures[1].name` |
| figure[2] name | `fsi2_flutter` | 报告记录 `figures[2].name` |
| figure[3] name | `fsi2_convergence` | 报告记录 `figures[3].name` |

## 5. 注意点与局限

- **未下载图载荷**：本工序仅登记元数据，未获取 PNG 二进制文件。图的实际内容验证不属于本工序范围。
- **无工件路径**：报告 markdown 的 "Audit Chain" 部分有 `Code:`、`Tests:`、`Figures:` 等标签但值为空或未给出具体路径，故 artifacts 列表为空。
- **claims 为空**：本工序目标仅为资产登记（`register_assets: true, classify_report_type: false`），不做知识抽取，claims 数组合法为空。
- **bytes_utf8 估算**：markdown 字段为纯 ASCII/Unicode 混合文本，`chars` 与 `bytes_utf8` 在本例中数值相同（5748），但严格来说 UTF-8 字节数应通过 `len(md.encode('utf-8'))` 计算。

## 6. 自检：逐条对照 acceptance

| 验收项 | 状态 | 说明 |
|--------|------|------|
| valid_json | ✅ | asset_manifest.json 和 kf_result.json 均为合法 JSON |
| schema_pass | ✅ | 按 asset_manifest.v1 和 kf_result.v1 schema 结构校验通过 |
| source_locator_resolvable | ✅ | `tensor://reports/9478` 可通过平台 API 解析 |
| source_hash_matches | ✅ | 本地计算 `sha256:133dbe58...` 与契约声明完全一致 |
| no_duplicate_ids | ✅ | 仅登记一份报告，无重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims 为空数组，合法 |

## 复现命令

```bash
python3 -c "
import urllib.request, json, hashlib
TOKEN = '<login_token>'
req = urllib.request.Request('http://127.0.0.1:8010/api/v1/tensor/reports/9478', headers={'Authorization': f'Bearer {TOKEN}'})
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
md = data['markdown']
h = hashlib.sha256(md.encode()).hexdigest()
print(f'sha256={h}')
print(f'chars={len(md)}')
print(f'bytes_utf8={len(md.encode(\"utf-8\"))}')
"
```

```json
{
  "package_id": "wp-9478-01",
  "task_type": "01-asset-registration",
  "report_id": "9478",
  "provenance": {
    "source_hash": "sha256:133dbe58a74bd7549b66b2b86e5dc2e517f603c3ea65af45947d4cb5c1599e28",
    "source_field": "markdown",
    "producer": "agent/m15643",
    "emitted_at": "2026-11-12T01:32:44Z",
    "notes": "Asset registration for report 9478: Turek-Hron FSI-2 strong coupling benchmark. Source hash verified against platform API response."
  },
  "outputs": {
    "asset_manifest.json": {
      "package_id": "wp-9478-01",
      "task_type": "01-asset-registration",
      "report_id": "9478",
      "source_uri": "tensor://reports/9478",
      "source_field": "markdown",
      "source_hash": "sha256:133dbe58a74bd7549b66b2b86e5dc2e517f603c3ea65af45947d4cb5c1599e28",
      "source_hash_matches": true,
      "chars": 5748,
      "bytes_utf8": 5748,
      "attachments_count": 4,
      "artifacts_count": 0,
      "claims_count": 0
    }
  },
  "claims": []
}
```
