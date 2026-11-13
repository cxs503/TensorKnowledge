# Work Package wp-9091-01

> Mission m18172 · 重开 PR#162 管到底第1轮 · matured mission deliverables
> 工序: 01-asset-registration · 报告: 9091

## 概述

本工作包对 report_id=9091 执行资产登记工序（01-asset-registration），是 KBM-RCI-F1-FACTORY 知识产线的第一道工序。

## 文件清单

| 文件 | 说明 |
|------|------|
| `KF-RESULT-wp9091-01.md` | 工序结果报告（人类可读） |
| `kf_result.wp-9091-01.json` | 工序结果信封（机器可校验） |
| `asset_manifest.json` | 资产登记清单 |
| `report_9091.md` | 源报告 markdown 本地副本 |
| `verification.json` | 验证数据（hash/locator 校验） |
| `checks_baseline.md` | 基线检查记录 |

## Schema 合规

- `kf_result.wp-9091-01.json` → `schemas/kf_result.v1.schema.json`
- `asset_manifest.json` → `schemas/asset_manifest.v1.schema.json`

## 验证

```bash
pytest tests/test_kf_wp9091_01.py -v
```
