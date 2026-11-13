# wp-9265-01 · 结果信道回环校验（发布后复核）

发布后的 KF-RESULT 报告（id=14717, title=`KF-RESULT wp-9265-01`, mission_id=15637, tags=`kf-wp:wp-9265-01`, `kf`, `01-asset-registration`, `report-9265`, `lane-B`）被重新取回，对结果 JSON 与实际源文档再做一次交叉核对，全部数字来自 `publish_receipt.json`。

| 检查 | 结果 | 实测 |
|---|---|---|
| 唯一 json 代码块 | PASS | `json_blocks_in_markdown=1` |
| 回环哈希一致 | PASS | 线上重算 `sha256:d2ab3780127bff4762a8754ada4720789eaac52fef0de8edf88369d3dea6302c` |
| 全部引文在线上源文档中可定位 | PASS | 复检 18 个 locator，未解析 0 个 |
| outputs 唯一键 = asset_manifest.json | PASS | |

图件随报告入库：`locator_map.png`。

复跑：`python3 scripts/kf_wp9265_01_report.py gate 14717`

说明：此回环只验证**信道与可定位性**（哈希/引文/结构），不构成对报告物理结论的复核。
