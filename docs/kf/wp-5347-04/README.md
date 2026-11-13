# wp-5347-04 —— 工序 04 独立审核（report 5347 的上游 01 包）

本目录只承载 **report_id=5347** 一个工作包的审核产物；不读、不写、不覆盖其它 report_id。

## 判决

**needs-fix（request-changes）** —— 被审对象 = `wp-5347-01` 的 `asset_manifest.json`
（`artifact_sha256` 见 `review_report.json` → `review.reviewed.artifact_sha256`）。

- 26 条资产里 **25 条** locator 与报告原文**字节相等**；**1 条**（`asset-5347-024`）的 `quote`
  把原文机构名改写（`外协方` → `外协方`）却仍保留**原文切片**的 `quote_sha256`
  → 哈希与正文自相矛盾，按 G2 的 E3/E4 fail-closed 语义该包不满足证据门。
- 非阻塞 3 条：占比行不可由同表可见行复算（缺 `doc:TRACKED` 行）、图资产 404 措辞把
  路由级/资产级 404 混写、三条资产共用同一 `char_span`。

## 文件

| 文件 | 内容 |
|---|---|
| `review_report.json` | **交付物**（`kf_result.v1` 信封：`package_id/task_type/report_id/provenance/outputs`），内含 12 项检查逐条结果、4 条发现、未跑项、独立性说明、disposition |
| `review_evidence.json` | 复核原始证据（每项检查的 detail、违规条目、被审清单 sha256、原文 sha256） |
| `KF-RESULT-wp-5347-04.md` | 已发布报告正文（六段 + 唯一一个 ```json 块） |
| `publish_check.json` | 发布后回读校验（字节回读、单 json 块、内嵌 JSON == 产物、source_hash 一致） |
| `figures/review_check_matrix.png` | 12 项复核矩阵 |
| `figures/asset_locator_outcome.png` | 26 条资产按 kind×locator_type 的可定位性 |

## 一键复跑

```bash
# 1) 从平台现取 report 5347 字节，重算 12 项检查（含被审清单）
python3 work/review_wp5347_04.py --json docs/kf/wp-5347-04/review_evidence.json

# 2) 生成交付物（构建期断言：每条嵌入引文必须是原文子串）
python3 scripts/review_wp5347_04_report.py

# 3) 出图 + 发布 + 回读校验
python3 scripts/review_wp5347_04_figs.py
python3 scripts/publish_wp5347_04.py            # 加 --dry-run 只写 markdown 不发平台
```

需要环境变量 `TENSOR_API_BASE` / `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS`（脚本从环境读取，不落盘、不进 argv）。

## 边界与未做项（如实）

- 未复现 TensorDEM 仓内事实（`20 passed / 36 passed / 152 篇 879 条 / ORPHAN 0`）：本工作树没有该仓检出，一律记 `not_run`，本审核不代替 CI 结论。
- 该链当前只有 01 包，无 claims/evidence → 语义门没有对象，未生成任何知识对象，未越界代做 03。
- 未读生产者自述（`README.md` / `KF-RESULT-wp-5347-01.md` / 回执未打开），只读行为产物 `asset_manifest.json`。
- 不给任何验证状态判定；验证级别由平台门计算。