# Baseline Checks for wp-9091-01

> 工作包: wp-9091-01 | 日期: 2026-11-13

## 检查项

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | JSON 格式有效 | ✅ PASS | 所有 .json 文件可被 json.load 解析 |
| 2 | Schema 合规 | ✅ PASS | kf_result 和 asset_manifest 符合 v1 schema |
| 3 | package_id 一致 | ✅ PASS | 所有文件 package_id = wp-9091-01 |
| 4 | report_id 一致 | ✅ PASS | 所有文件 report_id = 9091 |
| 5 | task_type 有效 | ✅ PASS | 01-asset-registration 在允许枚举内 |
| 6 | 无 verified claims | ✅ PASS | claims 数组为空 |
| 7 | asset_id 唯一 | ✅ PASS | 7 个资产，7 个唯一 ID |
| 8 | 文件齐全 | ✅ PASS | 7 个预期文件全部存在 |

## 基线说明

本基线检查为离线检查，不依赖平台 API。所有检查项均为结构性验证（JSON 格式、schema 合规、字段一致性），不涉及内容真实性验证（内容真实性由平台门控负责）。

## 与平台门控的关系

- 本基线检查 = 本地预筛（pre-flight）
- 平台门控 = 独立重算 source_hash + locator 解析 + 发布审批
- 两者互补，不替代
