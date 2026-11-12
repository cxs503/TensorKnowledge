# wp-3076-01 — 资产登记（report 3076）

工序：`01-asset-registration`（lane C，分层 TensorPapers | analysis）。只登记，不抽取、不分类、不标 verified。

| 文件 | 是什么 | 怎么来的 |
|---|---|---|
| `source.md` | 报告 3076 的 `markdown` 逐字节副本（3712 字符 / 6092 字节，`sha256=9b7bb242…d464c1`） | `scripts/kf_fetch_3076.py`（先校验契约哈希再落盘） |
| `source_meta.json` | 平台记录字段（title / scenario_key / mission_id=3012 / tags / 3 张图的 name+caption） | 同上 |
| `asset_manifest.json` | 19 条资产：字符区间 + 行号 + 逐字引文 + 唯一性 + payload 状态 | `scripts/kf_register_3076.py` |
| `kf_result.wp-3076-01.json` | 平台结果信封（`package_id`/`task_type`/`report_id`/`provenance`/`outputs`/`claims`） | 同上 |
| `verification.json` | 11 项机检（含在线复取、图端点 404 复测、图端点正控） | `scripts/kf_verify_3076.py` |
| `asset_manifest.v1.schema.json` | manifest 结构 schema（机检用） | 手写并与生成器同步维护 |
| `kf_result.v1.schema.json` | 契约信封 schema，本 worktree 缺该文件，故自本仓 commit `53c59cc` 逐字节恢复 | `git show 53c59cc:schemas/kf_result.v1.schema.json` |
| `publish_roundtrip.json` | 发布回执：json 块往返一致、provenance 哈希 = 现取 3076 哈希、图端点正控、被取代版本 | `scripts/kf_publish_3076.py` / `kf_check_published_3076.py` |
| `KF-RESULT-wp-3076-01.md` | 交付正文（六段）+ 唯一一个 json 结果块 | `scripts/kf_report_3076.py` |
| `fig_*.png` | 定位覆盖图 / payload 状态图 / acceptance 矩阵图 | `scripts/kf_figures_3076.py` |

## 结论摘要

- 源哈希与字符数与工单契约**逐位一致**；19/19 引文按区间回切逐字一致且唯一。
- payload 状态：`in_report_record` 2、`external_not_in_record` 11、`declared_payload_missing` 3（平台图有名字无字节，`/figures/<name>` 404）、
  `cross_report_out_of_scope` 2（Report #823 / #961，工单禁止读其它 report_id）、`declared_in_source_only` 1（`pytest 19 passed` 等声明未重跑）。
- `claims = []`：本工序不抽取，填 claims 会伪造属于 03 工序的产物。
- 图端点 404 已用正控校准：本包自己发布的报告同端点返回 200 且字节 sha256 与本地一致，故 3076 的 404 = 载荷真缺失。

## 复跑

```
export TENSOR_API_BASE=http://127.0.0.1:8010/api/v1 TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=...
python3 scripts/kf_fetch_3076.py
python3 scripts/kf_register_3076.py      # 注意：会重写 emitted_at
python3 scripts/kf_figures_3076.py
python3 scripts/kf_verify_3076.py
python3 scripts/kf_report_3076.py
python3 scripts/kf_publish_3076.py       # 只在尚无交付报告时跑；已有则用 kf_check_published_3076.py
python3 -m pytest tests/test_kf_wp3076.py -q
```

只读复核（不改任何产物）：`python3 -m pytest tests/test_kf_wp3076.py -q` —— 13 passed，含 7 个负控
（篡改引文 / 位移区间 / 重复 id / 原文漂移 / 自证 verified / 图载荷升格 / 异号 report_id）。