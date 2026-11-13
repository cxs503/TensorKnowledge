# KF-RESULT wp-9091-01

> 工作包: wp-9091-01 | 工序: 01-asset-registration | 报告: 9091
> 状态: draft | 日期: 2026-11-13

## 1. 本工序做了什么

对 report_id=9091（Mission m18172: 重开 PR#162 管到底第1轮 — matured mission deliverables）执行资产登记（01-asset-registration）。确认源报告 markdown 的字节哈希与契约一致，识别并定位报告中引用的工件，生成 asset_manifest.json。本工序不做知识抽取（classify_report_type=false），claims 为空数组。

## 2. 怎么做的（步骤/工具/关键设置）

1. **获取源报告**: 通过 TensorPlatform API 获取 report_id=9091 的 markdown 字段。
2. **哈希校验**: 本地计算 markdown 的 UTF-8 字节 SHA-256，与契约中的哈希逐位比对，确认一致。
3. **资产识别**: 扫描报告 markdown，定位引用的工件/附件。
4. **定位器计算**: 对每个资产引用，计算 char_span、行号、引用文本，并验证唯一性。
5. **清单生成**: 按 asset_manifest.v1 schema 构建 asset_manifest.json，按 kf_result.v1 schema 构建结果信封。
6. **Schema 校验**: 本地验证 JSON 结构符合 schema 要求。

关键设置：
- 源字段: `markdown`
- 哈希算法: SHA-256
- 资产分辨率: 全部标记为 `referenced_unresolved`（工件在工作树外）
- claims: 空数组（本工序不抽取知识）

## 3. 产出物清单

| 输出文件 | 要点 |
|----------|------|
| `asset_manifest.json` | 资产登记清单 |
| `kf_result.wp-9091-01.json` | 结果信封 |
| `report_9091.md` | 源报告 markdown 本地副本 |
| `verification.json` | 验证数据 |
| `checks_baseline.md` | 基线检查记录 |

## 4. 证据定位表

| Claim/字段 | 原文引文片段 | 位置 |
|------------|-------------|------|
| source_hash | 契约 source_hash 字段 | provenance |
| title | 报告标题 | 第 1 行 |
| package_id | `wp-9091-01` | 信封顶层 |
| task_type | `01-asset-registration` | 信封顶层 |

## 5. 注意点与局限

1. **工件不在工作树内**: 引用的工件位于其他仓库或平台存储，因此分辨率为 `referenced_unresolved`。这是预期行为——本工序只做登记，不跨仓拉取文件。
2. **零领域语义**: 源报告本身是平台机制（mission deliverables），不含船舶领域语义，符合 TensorPlatform 铁律。
3. **原 PR#162 已关闭**: 本工作包是对原 PR 的重开与完善，遵循小步单元原则（≤10 文件改动）。
