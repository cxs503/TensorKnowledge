# wp-14351-01 · 资产登记（report_id=14351，lane B）

包契约：`task_type=01-asset-registration`，`objective.register_assets=true`，
`objective.classify_report_type=false`，`source_uri=tensor://reports/14351`（字段 `markdown`）。
投递仓：TensorKnowledge，status=draft。

## 结果（一句话）

对 report 14351 的 markdown 独立重算 sha256 = `sha256:8c696991f8bef0c1f0903d2104e88a437897875c759af309c0c7710ce1260558`
（= 契约声明值，字符数 4190 = 契约值），登记 **22 条资产**：
`resolved_in_source` 14 / `referenced_unresolved` 8 / `declared_absent` 0；`claims=[]`（契约明示不做抽取）。

KF-RESULT 结果报告已发布于平台：**report id = 14897**，`title=KF-RESULT wp-14351-01`，
`tags` 含 `kf-wp:wp-14351-01`，正文含唯一一个 json 结果块。

## 产物

| 文件 | 内容 |
|---|---|
| `asset_manifest.json` | 22 条资产：类别/标签/所在章节/locator(char span + 原文切片 quote)/分辨率/机器检查/note |
| `asset_manifest.schema.json` | 本包 schema（由 `schemas/asset_manifest.v1.schema.json` 换本包常量派生，钉住 `schema_pass`） |
| `kf_result.json` | 结果信封（`package_id`/`task_type`/`report_id`/`provenance`/`outputs`/`claims=[]`） |
| `verification.json` | 9 项 acceptance 机器自检（9 PASS / 0 FAIL） |
| `roundtrip_verification.json` | 发布后回读平台报告的 9 项复核（9 PASS / 0 FAIL） |
| `asset_map.png` | 资产 locator 覆盖图（每根条 = 一条资产的 char span，颜色 = 分辨率） |
| `report.md` / `report_payload.json` | 已发布报告正文与投递载荷（figures 的 base64 已脱敏为长度占位） |
| `published.json` | 平台返回的发布记录（id=14897） |

输入快照在 `runs/wp-14351-01/`（`report_14351.md` + `report_14351.json` + 取回脚本）。

## 复跑

```bash
python runs/wp-14351-01/fetch_report.py        # 取回 report 14351 并记录 sha256/chars/figures
python scripts/kf/register_14351_assets.py     # manifest / 信封 / 自检（哈希或 locator 断言失败即中止）
python scripts/kf/publish_14351_report.py      # 出图 + 组稿 + 投递 KF-RESULT 报告
python scripts/kf/verify_14351_published.py    # 回读平台报告复核（json 块唯一性/哈希/引文逐字）
python -m pytest tests/test_kf01_wp14351_asset_manifest.py -q   # 7 passed
```

## 边界与如实说明

- **只碰 report 14351**：未读写任何其它 report_id；未改动上游产物。
- **不做抽取**：`claims=[]` 是契约允许的完整结果（`no_forced_claim_generation`），报告里 3 项 honest 未达标
  （+460.7% / -99.8% / 0.936）保持原文状态，未升格为 claim、未标 verified。
- **8 条 `referenced_unresolved`**：A07/A08/A09/A10/A11/A15/A16/A20 指向外部仓库 TensorFEM 的代码、基准工件、
  图件与集群作业 cj1024；本工作树只有 TensorKnowledge，按边界不复制、不臆造其内容，故只登记"报告引用了它"。
- **图件载荷**：本工序上报的 197785 B PNG 经 `GET /tensor/reports/<id>` 回读时 `png_base64` 长度为 0
  （见 `roundtrip_verification.json` 的 `figures_embedded` 项）。因此 fetch 到的报告 14351 `figures[]` 只有
  name/caption **不能归因于上游没镶嵌**——更可能是读侧剥载荷。此点已在本 README 更正，报告正文 ⑤-3 的措辞
  （"上游/平台侧的记录缺口"）已兼顾两种可能，未单独归罪上游。
- **不复核上游数字**：manifest 中 `resolved_in_source` 的语义是"能在原文逐字定位"，不是"数字为真"。
- `runs/wp-14351-01/fetch_report.py` 只读环境变量取 token，不落盘任何凭据。