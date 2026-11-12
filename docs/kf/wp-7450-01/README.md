# wp-7450-01 · 01-asset-registration · report_id=7450

工序：资产登记（登记，不抽取；claims=0；不标 verified）。
契约：`package_id=wp-7450-01`，`source_uri=tensor://reports/7450`，`source_field=markdown`。

| 文件 | 内容 |
|---|---|
| `asset_manifest.json` | 19 项资产：source markdown ×1、内嵌图 ×2、源码/工件路径引用 ×8、表格 ×5、复现命令块 ×1、接口端点/字段 ×2 |
| `kf_result.json` | 结果信封（`schemas/kf_result.v1.schema.json`），`provenance.source_hash` = sha256(markdown utf-8) |
| `verification.json` | 9 项 acceptance 自检（全部 PASS）+ 重算哈希 |
| `report.md` | 六段工序报告（由上面三个文件程序化渲染，唯一 json 代码块 = 结果信封） |
| `figures/wp-7450-01_asset_locator_map.png` | 资产类别×解析状态 + 字符跨度覆盖图 |
| `publish_receipt.json` | 平台报告回执（发布后的 report_id 与回读校验） |

复跑：`python3 scripts/kf/kf01_register.py --preset wp-7450-01 build result verify figure report`
（会重写 asset_manifest/kf_result/verification/figures/report.md；`report_payload.json` 为发布用中间件，已被 .gitignore 之外的清理步骤删除，可随时再生。）

边界：本包只读写 report_id=7450；引用的 `backend/...`、`artifacts/...` 属 ship-performance-platform 仓，
在 TensorKnowledge 工作树内不存在 → 一律如实记 `referenced_unresolved`，不跨仓读取。
