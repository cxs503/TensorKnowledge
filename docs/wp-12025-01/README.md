# wp-12025-01 — 资产登记（report 12025《DEM多面体颗粒接触与休止角验证》）

工作包 `01-asset-registration`，lane C。只登记源资产、不做抽取/分类/claim 生成，不标 verified。

## 文件

| 文件 | 说明 |
|---|---|
| `asset_manifest.json` | 交付物（`artifacts/wp-12025-01/asset_manifest.json` 的逐字节镜像） |
| `KF-RESULT-wp-12025-01.md` | 六段报告；**唯一一个 json 围栏块**=`kf_result.wp-12025-01.json` 结果信封 |
| `fig_span_map.png` | 定位地图（8 条 span 级定位在 432 字符源上的位置） |
| `fig_resolution_split.png` | 资产类别 × 解析状态构成 |
| `fig_gate_board.png` | 验收自检看板（6 项 gating + 4 项额外纪律） |

## 一键复跑

```bash
python3 scripts/kf_register_12025.py \
  && python3 scripts/kf_report_12025.py --no-post \
  && python3 scripts/kf_verify_12025.py \
  && python3 -m pytest tests/test_kf_wp12025_01.py -q
```

`kf_register_12025.py` 从平台现取 markdown（`GET /api/v1/tensor/reports/12025`），sha256 与契约
`6ebcceb70d4aa23bd429e13496cfa2ac2fc933c83461eef0a0c58a29321df0ed` 不符即中止、零产物。
`kf_verify_12025.py` 另起进程重新登录取源、重新切片复核 acceptance 6 项（结果落 `verification.json`）。

## 结论摘要（详见 KF-RESULT）

- 12 个资产：页内可解析 6 / 外部挂账 3（`polyhedra_repose.py`、`docs/polyhedra_repose_angle_validation.md`、`TensorDEM`）/ 观测缺失 3（图件、定量结果表、复现记录）。
- 原文 432 字符、无图无表无 commit：三条缺失是**观测**而非作者声明（`observed_absent_note`）。
- claims 为空（契约允许），故 claim 相关 acceptance 项为**空真**通过，`verification.json` 已标注。