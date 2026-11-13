# wp-13560-01 交付说明（delivery note）

工序 01-asset-registration · report_id=13560 · lane C · 仓 TensorKnowledge · status=draft（verification 由平台门计算）

## 已发布报告（唯一结果信道）

| 项 | 值 |
|---|---|
| 平台报告 id | `14862` |
| 标题 | `KF-RESULT wp-13560-01` |
| tags | `kf-wp:wp-13560-01`, `asset-registration`, `lane-C`, `TensorKnowledge`, `report_id:13560` |
| mission_id | `15764` |
| status | `published` |
| 图件 | `wp-13560-01_asset_locator_map.png`（存取：`GET /api/v1/tensor/reports/14862/figures/<name>`）|

## 产物（本工作树）

| 文件 | sha256 |
|---|---|
| `docs/kf/wp-13560-01/asset_manifest.json` | `40318a50b6342f3974011463afb96e50811666d3779ae92bb32cb380e5c3af9b` |
| `docs/kf/wp-13560-01/kf_result.json` | `561bfae1d1ce03bd6ce41704ddbf056cb0fb0f3ca0a490fffbcf2c9041eabfaf` |
| `docs/kf/wp-13560-01/verification.json` | `fee89dc9c4186d5abacc737030d6c5f771732c41cdea58fd5ae56b8dfb91ecab` |
| `docs/kf/wp-13560-01/verification_independent.json` | `608d27b9236cfdd998e7da2ef69b20e6abb660b88799506edd7e19b1f638080c` |
| `docs/kf/wp-13560-01/report.md` | `036465781f12680a3470ede5b51ba2e2f83d9bb7bf1c1c61e6fe2b5fb930b3e3` |
| `docs/kf/wp-13560-01/figures/wp-13560-01_asset_locator_map.png` | `b62311902ef5068ac0a3bcce320bb9033eb910bc4ab8295baf7406fc4f59001e` |

## 误差判定（显式回答是否 <3%）

本工序无物理场量，可比对量是**字节与字符**级一致性，故误差按「不一致条目数」计：

| 关键量 | 基准 | 实测 | 误差 | <3%? |
|---|---|---|---|---|
| 源 markdown 字节哈希 | 契约 `sha256:b578c093…` | 平台侧独立重算 = 同一值 | 0 位差异 | **是（0%）** |
| 资产字符跨度/引文 | 原文逐字切片 | 18/18 定位器复核一致（产线 + 独立两套实现） | 0 条不一致 | **是（0%）** |
| manifest 计数 | 由资产列表重算 | `by_class`/`by_resolution` 全等 | 0 处不同 | **是（0%）** |
| 报告 json 块 | `kf_result.json` | 解析后对象全等（全文仅 1 个 json 块） | 0 处不同 | **是（0%）** |
| claims | 契约 `objective.register_assets`（不做抽取） | 0 条 | 不适用（本工序无抽取） | 是（按契约） |

自检：producer `verification.json` all_pass=True（9 项）；独立复核 `verification_independent.json` all_pass=True（11 项）。

## 一键复跑

```bash
python3 scripts/kf/kf01_register.py --preset wp-13560-01 build result verify figure report
python3 scripts/kf/kf_wp13560_01_independent_check.py   # 独立复核（零共享代码）
```

注：`report` 动作只写 `report_payload.json`，发布需显式 `POST /api/v1/tensor/reports`；本包已发布为报告 `14862`。
