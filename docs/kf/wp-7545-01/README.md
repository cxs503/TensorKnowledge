# wp-7545-01 — report 7545 源资产登记（01-asset-registration）

契约：`package_id=wp-7545-01` ｜ `report_id=7545` ｜ `lane=C` ｜ `delivery.repo=TensorKnowledge` ｜ `status=draft`
源：`tensor://reports/7545`，字段 `markdown`，sha256 `84010e0091071d5971888931b9d6b73fc3bba4f217dcd17ab739979fc1c5ae60`（3583 字符 / 6333 B UTF-8）

## 产物

| 文件 | 内容 |
|---|---|
| `asset_manifest.json` | 18 个资产的台账（字符级定位器 + 解析状态 + 局限），`claims: []` |
| `kf_result.json` | 结果信封（`kf_result.v1` schema），`provenance.source_hash` = 契约哈希 |
| `verification.json` | 独立自检回执：7 项 acceptance 逐条 pass（`all_pass=true`） |
| `probe_figure_endpoint.json` | 图表端点阳性对照：证明 7545 四张图的 404 是数据缺失而非端点失效 |
| `fig1_asset_inventory.png` | 资产分类/解析状态柱状图（数据由 manifest 注入） |
| `REPORT.md` | 交付报告（六段 + 逐字证据表 + 逐条自检），已发布为平台报告 14664 |

## 登记口径（三个解析状态）

- `resolved_in_source` = 1：正文 markdown 本身的字节（重算哈希 = 契约哈希）。
- `declared_absent` = 4：平台 `figures` 元数据 4 条有 name/caption，但取值端点 404 → 无可哈希字节，不臆造摘要。
- `referenced_unresolved` = 13：`experiments.json:spec`、`run_abm.py:KNOWLEDGE_PACKS`、`dem_bpm.py`、`tools/abm`、
  `artifacts/IN59-P2/*`、`six_dim_table.json`、`three_leg.json`、`acceptance.json`、`control_arm.json`、`pytest` 命令×2 —
  均不在 TensorKnowledge 检出（worktree + git index 双查无命中），按边界不跨仓拷贝。

## 复跑

```bash
python3 scripts/kf/build_asset_manifest_7545.py build result verify   # 取源→哈希门→登记→信封→独立自检
python3 scripts/kf/report_7545_01.py render                          # 出图 + 渲染 REPORT.md
python3 scripts/kf/probe_7545_figures.py 14664                       # 图表端点阳性对照
```

## 边界声明

只读写 `report_id=7545`（另加本包自己发布的 14664 作为阳性对照）；未抽取、未生成 claim、未标 `verified`、
未改写上游或其它工作包产物。报告平台侧不可变（`/tensor/reports/{id}` 只有 GET），因此阳性对照证据以本目录独立
JSON 形式留存，不回写已发布信封——不回写是为了让已发布工件的 sha256 声明始终可复核。