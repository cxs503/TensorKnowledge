# wp-5761-01 — 资产登记（report 5761）

锚点 `KBM-RCI-F1-FACTORY`｜工序 `01-asset-registration`｜lane C｜交付仓 TensorKnowledge｜status **draft**
源：`tensor://reports/5761`（`markdown`，`sha256:06f7e6a9…c4d7`，4141 字符 / 7172 字节 UTF-8）
已发布报告：平台 id **14657**，title `KF-RESULT wp-5761-01`，tag `kf-wp:wp-5761-01`

## 产物（全部落 docs/，因推送门滤掉 artifacts/**、runs/**）

| 文件 | 要点 |
|---|---|
| `report_5761.markdown` | 源报告逐字字节副本（不做换行归一）——所有 locator 的定位基准 |
| `asset_manifest.json` | **主产物**：31 条资产定位（17 类；resolved_in_source 22 / referenced_unresolved 8 / declared_absent 1）、计数、空 `claims` + 理由、integrity、4 条观测 |
| `schema/asset_manifest.v1.wp-5761-01.schema.json` | 由 `schemas/asset_manifest.v1.schema.json` 机械重钉（只改 3 处身份 pin），结构继承 |
| `schema_binding.json` | 父 schema sha256 + 逐条替换记录 |
| `kf_result.json` | 结果信封（`package_id/task_type/report_id/provenance/outputs`）——发布报告的**唯一** json 块 |
| `verification.json` | 独立复算：10 项检查，overall=PASS |
| `published_check.json` | 发布后核对（json 块 == 本地信封、源报告未被改动、figures 落库形态） |
| `fig_asset_inventory.png` / `fig_locator_map.png` | 图1 资产清单分层；图2 locator 覆盖（数字程序注入） |
| `KF-RESULT-wp-5761-01.md` | 已发布报告正文（与平台 id 14657 的 markdown 同文） |

## 一键复跑

```bash
python3 scripts/kf/build_asset_manifest_5761.py   # 取源+校验哈希+切片登记+schema+建图
python3 scripts/kf/verify_5761.py                 # 独立重拉、重切片、重校验（不 import 生成器）
python3 -m pytest tests/test_kf_wp_5761_01.py -q  # 离线回归 8 项
python3 scripts/kf/publish_5761.py                # 渲染并发布（--dry-run 只落本地 md）
python3 scripts/kf/check_published_5761.py 14657  # 发布后核对
```

`scripts/kf_fetch_5761.py` 是取源/落副本的最小工具（写 `runs/wp-5761-01/`，仅调试用）。

## 边界与局限（与报告 ⑤ 同口径）

1. 只碰 report_id=5761；发布前后都重算其 markdown 哈希，未变（`published_check.json:source_report_untouched`）。
2. 报告引用的代码与工件（`route/` 包、`route/tests/test_route_second_cut.py`、`make_route_lock.py`、
   `run_second_cut.py`、`artifacts/ice_route_second_cut/route_lock.json`、`summary.json`）**不在本工作树**，
   一律 `referenced_unresolved`，未猜路径、未臆造哈希。
3. 图1–图3 登记为 `referenced_unresolved`：源报告 `figures[]` 只有 name+caption。**发布后新证据**：
   本包自己发布的报告（14657）上载了 png_base64，但平台回读的 `figures[]` 仍只有 name+caption
   （`published_check.json: figures_payload_persisted=false`）——即图件载荷不被 `figures[]` 留存，
   属平台行为而非作者漏交；故图件字节只以 `docs/kf/wp-5761-01/*.png` 形式持久。
4. `schemas/kf_result.v1.schema.json`（契约点名）不在工作树；`schema_pass` 用重钉后的
   `asset_manifest.v1` 机器复算，形状按契约文字与 wp-448-01 / wp-542-01 先例。若平台侧 schema 不同，
   验收以平台为准，本包接受返修——主要残余风险。
5. 本工序不做分类/抽取/复算：报告原文的 64 项测试、90.21% 分支覆盖、8.620% 走廊离散误差等
   **只登记位置，不复算、不改结论强度**；也从未标 verified。