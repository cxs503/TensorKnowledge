# wp-13988-01 — 01-asset-registration（report 13988）

工作包：`package_id: wp-13988-01` · `task_type: 01-asset-registration` · `lane: C`
源报告：`report_id=13988`（`tensor://reports/13988`，字段 `markdown`）
契约 `source_hash`：`sha256:79d795674f0b13f828d8933af64612a1addb30cb8a8b903f7ab136f0508442b9`（实测一致，6222 chars / 9227 bytes）

## 这一包做了什么

对**唯一一份**报告 13988 做**资产登记**（不抽取、不判定、不标 verified）：

- 29 个资产，每个带 `locator`（`char_span` + 行区间 + **逐字切片 quote**）。
- 解析分布：`resolved_in_source` 22 / `referenced_unresolved` 7 / `declared_absent` 0。
- `claims: []`——契约 `objective.classify_report_type=false` 且 notes 允许空数组；
  本包不产生任何知识断言。
- 7 条不可解析引用（9 个流水线工件文件、KCS 几何 JSON、2 个代码指针、2 个 PNG）一律
  如实标 `referenced_unresolved`，**未拼接路径当既有事实、未联网猜地址**。

## 文件

| 文件 | 作用 |
|---|---|
| `asset_manifest.json` | 主产物（`artifacts/wp-13988-01/asset_manifest.json` 的逐字节镜像） |
| `kf_result.wp-13988-01.json` | kf_result.v1 结果信封（= KF-RESULT 报告里唯一的 json 块） |
| `asset_manifest.v1.schema.json` | 由仓内 `schemas/asset_manifest.v1.schema.json` 程序化改 const 派生的包内 schema（原文件固定为 448 包） |
| `build_asset_manifest.py` | 登记器：锚点唯一性 → 逐字切片 → 解析分类 → 结构门 + 反证 → 落盘 |
| `verify_manifest.py` | 独立复核器：**重新从 API 取源**重算哈希/唯一性/切片一致性/结构门 |
| `plot_coverage.py` → `fig_manifest_coverage.png` | 覆盖图（资产 char 区间按解析类着色 + 分类计数） |
| `build_report.py` → `KF-RESULT-wp-13988-01.md` | 论文级报告渲染（数字程序化注入）+ `--post` 发布 |
| `checks.json` / `verification.json` / `posted_report.json` | 构建期自检 / 独立复核 / 发布回执 |

## 复现

```bash
cd "$(git rev-parse --show-toplevel)"
python3 scripts/kf_fetch_13988.py          # 取源 + 哈希门
python3 docs/wp-13988-01/build_asset_manifest.py
python3 docs/wp-13988-01/verify_manifest.py
python3 docs/wp-13988-01/plot_coverage.py
python3 docs/wp-13988-01/build_report.py   # 加 --post 发布到平台
```

## 自检结论

`checks.json` 11/11 pass（含 2 项反证：manifest 删 `counts`、信封缺必填键都必须被判失败）；
`verification.json` 11/11 pass（fresh source hash 相同）。acceptance 六项全通过；
`source_locator_resolvable` 29/29（quote 均唯一且在源文，char 切片逐字节相等）。

## 局限（honest）

1. 上游数字（A_hat=0.075539、ΔRT +0.384% 等）只被**定位登记**，本包不复算、不背书。
2. 上游账本哈希在报告里被**截断**（`6fc45dd1e21f8ba8…`），完整值缺失 → 下游无法仅凭报告复算链。
3. 未执行上游 `scripts/run_calib_reflux.py`（不在本工作树）；未联网核证外部数据。
4. 只碰 `report_id=13988`；未读/写其它 report_id。