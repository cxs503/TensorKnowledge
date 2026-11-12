# KF-RESULT wp-4331-01

tags: kf-wp:wp-4331-01, TensorCAD, information, A

## ① 本工序做了什么

工作包 `wp-4331-01`（`01-asset-registration`）对 `report_id=4331` 执行源资产登记：
- 确认报告 markdown 的字节哈希与契约给定值一致
- 列出报告中可解析的附件/工件（figure + benchmark evidence 引用）
- 不做内容抽取（claims 为空数组）

## ② 怎么做的（步骤/工具/关键设置）

1. **登录获取 token**：`POST /api/v1/auth/login`（用户 `eco_admin`），取 `access_token`。
2. **拉取报告**：`GET /api/v1/tensor/reports/4331`，取 `markdown` 字段（2418 字符）。
3. **哈希校验**：`hashlib.sha256(markdown.encode()).hexdigest()` → `0f5fec2df3e776d0625b03ca2a1e05e4275a5f770757b18b7b83c122c8a12561`，与契约 `source_hash` 完全匹配。
4. **工件扫描**：逐段扫描 markdown，识别：
   - `figures` 字段中的 `pr77_merge_evidence.png`
   - 第③节中引用的 `benchmarks/merge77_evidence.json`
5. **生成 asset_manifest.json**：按契约结构登记源报告 + 2 个工件引用，claims 置空。
6. **生成 kf_result.json**：按 `kf_result.v1` 结构封装 provenance + outputs。

关键设置：零手抄——所有数字/引文逐字来自报告原文；不标记任何 claim 为 verified。

## ③ 产出物清单

| 输出文件 | 要点 |
|---|---|
| `docs/kf/wp-4331-01/asset_manifest.json` | 源报告登记（id=4331, hash 已验证）+ 2 个工件引用（figure + benchmark evidence）+ claims=[] |
| `docs/kf/wp-4331-01/kf_result.json` | provenance（source_hash 已验证）+ outputs（asset_manifest 路径与摘要） |

## ④ 证据定位表

| claim/字段 | 原文引文片段 | 定位 |
|---|---|---|
| source_hash | `sha256:0f5fec2df3e776d0625b03ca2a1e05e4275a5f770757b18b7b83c122c8a12561` | 契约 input.source_hash；Python hashlib 计算结果一致 |
| report title | `PR #77 治愈：agent/m3369 对 main 的三方合并（CHANGELOG 语义并集，零内容丢失）` | 报告 title 字段 / markdown 第①节标题 |
| chars=2418 | markdown 字段长度 2418 | `len(data['markdown'])` |
| figure artifact | `pr77_merge_evidence.png` | 报告 figures[0].name |
| benchmark artifact | `benchmarks/merge77_evidence.json` | markdown 第③节：「见 \`benchmarks/merge77_evidence.json\`」 |
| scenario_key | `tensorfem-pr-cure-merge` | 报告 scenario_key 字段 |

## ⑤ 注意点与局限

- **仅登记不抽取**：本工作包契约明确 `register_assets: true, classify_report_type: false`，故未做任何 claim 抽取。claims 数组为空是契约允许行为（"claims 允许为空数组"）。
- **工件状态为 referenced**：`pr77_merge_evidence.png` 和 `benchmarks/merge77_evidence.json` 仅在报告中被引用，未实际获取其二进制/内容，故 status 标为 `referenced_in_report`。
- **零手抄纪律**：所有数字（2418 字符、2 个工件、hash 值）均通过程序化读取+计算获得，无凭记忆重述。
- **不标记 verified**：契约明确 `do_not_mark_claims_as_verified: true`，本产出无任何 verified 标记。

## ⑥ 自检：逐条对照 acceptance

| 验收项 | 状态 | 说明 |
|---|---|---|
| valid_json | ✅ | asset_manifest.json 与 kf_result.json 均通过 `json.loads()` 解析 |
| schema_pass | ✅ | 结构对齐 kf_result.v1（package_id/task_type/report_id/provenance/outputs） |
| source_locator_resolvable | ✅ | report_id=4331 通过 API 成功获取，markdown 字段存在 |
| source_hash_matches | ✅ | 计算 hash `0f5fec...` 与契约给定值完全一致 |
| no_duplicate_ids | ✅ | 仅登记 1 份报告，artifact_id 无重复（art-4331-fig-01, art-4331-bench-01） |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims 为空数组（契约允许），无未解决 claim |

```json
{
  "package_id": "wp-4331-01",
  "task_type": "01-asset-registration",
  "report_id": 4331,
  "provenance": {
    "source_uri": "tensor://reports/4331",
    "source_hash": "sha256:0f5fec2df3e776d0625b03ca2a1e05e4275a5f770757b18b7b83c122c8a12561",
    "source_hash_verified": true,
    "retrieved_at": "2026-11-12T00:52:25Z",
    "retrieval_method": "GET /api/v1/tensor/reports/4331 via Bearer token (eco_admin)"
  },
  "outputs": {
    "asset_manifest.json": {
      "path": "docs/kf/wp-4331-01/asset_manifest.json",
      "artifacts_registered": 2,
      "claims_count": 0,
      "notes": "Asset registration only — no claim extraction per contract"
    }
  }
}
```

**repro_cmd**:
```bash
python3 -c "
import urllib.request, json, hashlib
tok = json.loads(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8010/api/v1/auth/login', json.dumps({'username':'eco_admin','password':'EcoTest!2026pass'}).encode(), headers={'Content-Type':'application/json'})).read())['access_token']
md = json.loads(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8010/api/v1/tensor/reports/4331', headers={'Authorization': f'Bearer {tok}'})).read())['markdown']
assert hashlib.sha256(md.encode()).hexdigest() == '0f5fec2df3e776d0625b03ca2a1e05e4275a5f770757b18b7b83c122c8a12561'
print('hash verified, chars=', len(md))
"
```
