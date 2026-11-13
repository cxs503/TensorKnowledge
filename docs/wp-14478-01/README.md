# wp-14478-01 — 资产登记（report 14478）

工序：`01-asset-registration`（lane B，分层 `CASE-CYLINDER-DRAG-FVM | case-cylinder-drag-fvm`）。
只登记，不抽取、不分类、不标 verified。边界：只读 `report_id=14478`，未读/写其它 report_id，未改写上游工件。

| 文件 | 是什么 | 怎么来的 |
|---|---|---|
| `source.md` | 报告 14478 的 `markdown` 逐字节副本（6156 字符 / 9430 字节 / `sha256=8fbd643e…b206b0`） | `scripts/kf_fetch_14478.py`（先校验契约哈希与字符数再落盘） |
| `source_meta.json` | 平台记录字段（title / scenario_key / mission_id=15406 / tags / figures=0） | 同上 |
| `asset_manifest.json` | 20 条资产：字符区间 + 行号 + 逐字引文 + 唯一性 + payload 状态 | `scripts/kf_register_14478.py` |
| `kf_result.wp-14478-01.json` | 平台结果信封（`package_id`/`task_type`/`report_id`/`provenance`/`outputs`/`claims`） | 同上 |
| `verification.json` | 10 项机检（在线复取 + 重算哈希 + 20 条区间回切 + 两份 schema + 边界） | `scripts/kf_verify_14478.py` |
| `asset_manifest.v1.schema.json` | manifest 结构 schema（本包自钉，report 14478 专用） | 手写并与生成器同步维护 |
| `kf_result.v1.schema.json` | 契约信封 schema，自 worktree `schemas/` 逐字节复制 | `cp schemas/kf_result.v1.schema.json` |
| `fig_locator_map.png` / `fig_payload_status.png` / `fig_acceptance_matrix.png` | 定位覆盖图 / payload 状态图 / 验收矩阵图 | `scripts/kf_figures_14478.py` |
| `KF-RESULT-wp-14478-01.md` | 交付正文（六段）+ 唯一一个 `json` 结果块 | `scripts/kf_report_14478.py` |
| `publish_roundtrip.json` | 发布回执：json 块往返一致、图端点 200 且字节 sha256 与本地一致、发布记录字段 | `scripts/kf_report_14478.py --publish` |

## 结论摘要

- 源哈希与字符数与工单契约**逐位一致**（`sha256:8fbd643e…b206b0`，6156 字符）；20/20 引文按区间回切逐字一致且全文唯一。
- payload 状态：`in_report_record` 1（原文本身）、`external_url_declared` 1（DFG 官网页 URL）、
  `external_repo_path_declared` 12（TensorFVM 仓内路径/包/符号，未取字节）、
  `declared_payload_missing` 5（`runs/`、`analysis/`、原生产物、集群 `/tmp` 输出、analyze 的 7 张图 —— 原文自述"缺/未产出"）、
  `declared_in_source_only` 1（`report` 入口的生成目标路径）。
- `claims = []`：本工序不抽取，填 claims 会伪造属于 03 工序的产物。
- **缺口未升格**：原报告是 honest-FAIL（三档网格作业排队未派发、无任何 got 数字）；本包只登记缺口，不补数值、不编造图件文件名。
- 平台图条目为 0（`figures: []`），故"平台图载荷状态"检查记为显式 vacuous PASS 并写明理由。
- 发布：报告 **14894**（title `KF-RESULT wp-14478-01`，tags 含 `kf-wp:wp-14478-01`，scenario_key `case-cylinder-drag-fvm`，mission_id=15793）；
  json 块往返逐字节相等、图端点 200、字节 sha256 与本地一致。

## 复跑

```
export TENSOR_API_BASE=http://127.0.0.1:8010/api/v1 TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=...
python3 scripts/kf_fetch_14478.py
python3 scripts/kf_register_14478.py     # 注意：会重写 emitted_at
python3 scripts/kf_verify_14478.py
python3 scripts/kf_figures_14478.py
python3 scripts/kf_report_14478.py
python3 -m pytest tests/test_kf_wp14478.py -q     # 19 passed（含 8 个负控）
python3 scripts/kf_report_14478.py --publish      # 仅在尚无交付报告时跑；已有则视为新版本
```

只读复核（不改任何产物）：`python3 -m pytest tests/test_kf_wp14478.py -q` → 19 passed，含 8 个负控
（篡改引文 / 位移区间 / 错行号 / 重复 id / 原文漂移 / 自证 verified / 异号 report_id / envelope↔manifest 不一致，另含 payload 状态非法被 schema 拒绝）。