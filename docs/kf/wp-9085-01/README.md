# wp-9085-01 — 资产登记（report 9085）

`task_type=01-asset-registration` / `lane=C` / 只碰 report 9085。

| 产物 | 说明 |
|---|---|
| `asset_manifest.json` | 源资产清单（11 条），字符区间定位 + 解析状态 + `excluded_tokens`；`claims=[]` |
| `kf_result.json` | 平台结果信封（`schemas/kf_result.v1.schema.json`），`provenance.source_hash` = 9085 markdown 字节哈希 |
| `KF-RESULT-wp-9085-01.md` | 六段报告，全文唯一 json 块即信封原文 |
| `verification.json` | 独立重放：11/11 locator、13/13 occurrence、结构检查全绿 |
| `asset_manifest.schema.derived.json` | 共享 `schemas/asset_manifest.v1.schema.json` 的派生副本（仅 3 个 identity const 变更） |
| `generator_selfcheck.json` / `report_selfcheck.json` | schema / 信封 / 报告结构自检 |
| `figures/fig_coverage.png` | 资产类别×解析状态 + 检查通过率（数据源程序化读取） |

原文副本与记录元数据在 `runs/wp-9085-01/`（`source_9085.md` 为离线复算锚点）。

平台报告：id **14718**（`title=KF-RESULT wp-9085-01`，`mission_id=15629`，
tags 含 `kf-wp:wp-9085-01`），readback 三字段 digest 全 ok。

## 复跑

```bash
python3 scripts/kf_wp9085_01_register.py   # 取原文 → 重算 sha256 → 重建清单/信封/验证
python3 scripts/kf_wp9085_01_verify.py     # 独立重放全部定位（不 import 生成器）
python3 scripts/kf_wp9085_01_report.py     # 重渲染报告 + 平台载荷
python3 -m pytest tests/test_kf_wp9085_01.py -q
```

## 已知局限（详见报告 ⑤）

- 10/11 条引用资产 `referenced_unresolved`：随报告只转移了 markdown，附件字节未交付；
  图片端点 `/tensor/reports/9085/figures/<name>` 与 `/artifacts` 均返回 404（记录在案）。
- 共享 asset_manifest schema 写死 wp-448-01 身份，本包不越界修改，改走派生 schema +
  「打到共享 schema 的错误集合 ⊆ {package_id, report_id, source/uri}」的双重证据。
- 未生成任何 claim（objective 只要求 register_assets）；未标任何 verified。