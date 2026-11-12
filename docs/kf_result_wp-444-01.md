# KF-RESULT wp-444-01

## ① 本工序做了什么

源资产登记（task_type=01-asset-registration）：对 report_id=444 的 markdown 进行字节级哈希校验，解析其结构（章节/表格/图引用/代码引用），列出可识别的附件与工件，不做内容抽取（claims 留空数组）。

## ② 怎么做的

1. 通过 GET $TENSOR_API_BASE/tensor/reports/444 获取报告 markdown 字段（Bearer token 认证）
2. 对 markdown 字符串计算 sha256，与契约给定哈希 `4068f881c6722010ea3cdf78ee673068d8fb56fdc12be39db9c7b3f764457af2` 比对（结果：完全一致）
3. 逐段扫描 markdown 结构：识别 7 个章节标题、4 张表格、1 个 figures 条目、0 个代码文件引用
4. 检查 figures 数组是否含 png_base64 数据（结论：无，仅 name+caption 元数据）
5. 将登记结果写入 `artifacts/wp-444-01/asset_manifest.json`

**关键设置**：
- 哈希算法：sha256（UTF-8 编码的 markdown 字符串）
- 零手抄：所有引文逐字来自 markdown 原文
- claims 显式留空：本工序契约明确「不做抽取」

## ③ 产出物清单

| 输出文件 | 要点 |
|----------|------|
| `artifacts/wp-444-01/asset_manifest.json` | 源资产登记清单：哈希校验通过、7 章节/4 表/1 图/0 代码引用、claims=[]、2 项 unresolved |

## ④ 证据定位表

| 字段/声明 | 原文引文片段 | 位置 |
|-----------|-------------|------|
| source_hash 匹配 | sha256 计算值 = `4068f881c6722010ea3cdf78ee673068d8fb56fdc12be39db9c7b3f764457af2` | 程序计算，与契约一致 |
| 标题 | `AlphaEvolve-Style Verifier/Generator Separation: Held-Out Question Bank & Independent Verification for Ship Resistance` | API 返回 title 字段 |
| 参数表 4 行 | `ITTC-1957 / Blasius / P-S / Holtrop` | markdown section ① (lines 11-17) |
| 计算结果表 5 行 | `ITTC-1957 5/5 / Blasius 3/3 / P-S 4/4 / HM 3/3 / 合计 15/15` | markdown section ③ (lines 35-41) |
| 误差判定表 4 行 | `ITTC-1957 Cf (Re=1e8) 0.0% / Blasius Cf 0.0% / P-S Cf 0.0% / HM 1+k 0.0%` | markdown section ⑥ (lines 55-60) |
| 图引用 | `见 figures 附件：四面板图展示 ITTC-1957 摩擦线、平板边界层、逐公式通过率、逐题偏差` | markdown section ④ (line 45) |
| figures 无 PNG | figures 数组仅含 `{name, caption}` 无 `png_base64` | API 返回数据 |
| 治理升级 | `本报告经治理升级，补充六要素章节（背景/方法/结果/图件/注意点/误差判定）` | markdown 治理升级段 (line 69) |

## ⑤ 注意点与局限

- **figures 缺 PNG 数据**：报告 figures 数组只有 name+caption 元数据，无 png_base64 内嵌。原始 PNG 文件位置未知，已登记为 unresolved。
- **测试文件路径未知**：报告提及 `pytest（12 项单元测试）` 但未给出测试文件路径或仓库内位置，需后续定位。
- **治理升级段**：报告末尾有 RPT-REWORK m583 治理升级元数据，六要素章节状态标为「待补充」，但实际正文已填充完整内容——这是治理流程的残留标记，不影响内容完整性。
- **未做内容抽取**：claims 数组为空，符合本工序契约（01-asset-registration 只登记不抽取）。
- **未标 verified**：所有登记项均为「已识别」状态，验证由平台门计算。

## ⑥ 自检（acceptance 逐条）

| 验收项 | 结果 | 说明 |
|--------|------|------|
| valid_json | ✅ | asset_manifest.json 通过 json.load 验证 |
| schema_pass | ✅ | 字段结构符合契约定义（package_id/task_type/report_id/provenance/outputs） |
| source_locator_resolvable | ✅ | 所有引文可在 markdown 原文逐字定位 |
| source_hash_matches | ✅ | sha256 计算值与契约给定值完全一致 |
| no_duplicate_ids | ✅ | tbl-444-params/tbl-444-results/tbl-444-errors/tbl-444-pending/fig-444-verifier-pilot 均唯一 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=[] 显式留空，unresolved_assets 含 2 项已标注 status=unresolved |

**repro_cmd**:
```bash
cd /root/tp-agent/work/m15508
python3 -c "
import json, hashlib
manifest = json.load(open('artifacts/wp-444-01/asset_manifest.json'))
assert manifest['source_hash'] == 'sha256:4068f881c6722010ea3cdf78ee673068d8fb56fdc12be39db9c7b3f764457af2'
assert manifest['source_hash_verified'] == True
assert manifest['claims'] == []
assert len(manifest['sections']) == 7
assert len(manifest['tables']) == 4
print('ALL CHECKS PASSED')
"
```

```json
{
  "package_id": "wp-444-01",
  "task_type": "01-asset-registration",
  "report_id": "444",
  "provenance": {
    "source_uri": "tensor://reports/444",
    "source_field": "markdown",
    "source_hash": "sha256:4068f881c6722010ea3cdf78ee673068d8fb56fdc12be39db9c7b3f764457af2",
    "source_hash_verified": true,
    "retrieved_at": "2026-11-12T00:50:00Z",
    "retrieval_method": "GET tensor/reports/444 (Bearer token)"
  },
  "outputs": {
    "asset_manifest": {
      "path": "artifacts/wp-444-01/asset_manifest.json",
      "sections_count": 7,
      "tables_count": 4,
      "figures_count": 1,
      "code_references_count": 0,
      "claims_count": 0,
      "unresolved_assets_count": 2,
      "source_hash_verified": true
    }
  }
}
```
