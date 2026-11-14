# wp-5716-04 — 报告 5716 的独立红队复核（needs-fix）

任务要点：对报告 5716（IN10-G1 冰区航行战役验收门）做一次**可复算**的独立复核，复核方自己重算每条可重算的数字，并把「判据是否被执行」与「结论是否对口径敏感」分开判。

## 结论

- 判定 **needs-fix**，阻断项 3 条（F1、F2、F3）。
- 复算台账 22 条：PASS 4 / FAIL 8 / 恒等式不闭合 4 / 不可复算 1 / 派生 5。
- 未执行/无法执行的上游检查 5 类，登记 `NOT_RUN`/`WITHHELD`，不默认通过。

## 交付物

| 文件 | sha256(前 16) | 字节 | 作用 |
|---|---|---|---|
| `source_5716.md` | 4f9848b22b555158 | 8108 | 钉扎的快照（逐字节等于取回的 markdown，用于离线重建与哈希复核） |
| `source_5716.md.meta.json` | 4a1dc879b7f44cb0 | 598 | 取回元数据（哈希钉扎、抓取时刻、来源 URI） |
| `figures/fig_review_errors.png` | 5269e0613ea00fa0 | 246349 | 图 1：复算误差 vs 自述容差 + 台账状态矩阵 |
| `recompute.json` | a4e695faa4db3ac8 | 40754 | 复算台账：每条含公式/输入(带行号与原文)/复算值/报告值/相对差/容差/状态 |
| `review_report.json` | 61805166202230d6 | 21163 | 复核结论：判定/发现(含复现路径)/被证成主张/未执行检查/独立性限制 |
| `report.md` | ae2f08576629093f | 24626 | 复核报告正文（全部数字由 recompute.json 渲染，零手抄） |

## 复现

```bash
python3 scripts/kf/review_wp_5716_04.py --offline   # 由已提交快照重建
pytest -q tests/test_wp_5716_04_review.py           # 不变量 + 负向控制
```

来源钉扎：`sha256:4f9848b22b55515826476e1d5b2fcd15da80087a3d261d6a937a4c17cda68377`（4790 字符）。改动快照会同时打破本包所有结论与测试。

## 边界

- 只审 markdown 字节；战役工件 `artifacts/campaign_ice_nav/*` 与 `backend/*` 不在本仓库，因此 16 条门断言的执行记录、pytest 13 passed、G13 哈希台账一律未重放（`NOT_RUN`）。
- 不发布、不自称已验证：`published.json` 由平台门在合并时写入，本包状态为 `awaiting_pr_merge`。
- 与在开 PR 无重叠（含热文件声明）：除新增 `docs/kf/wp-5716-04/`、`scripts/kf/review_wp_5716_04.py`、`tests/test_wp_5716_04_review.py` 外，本 PR 只重建了一次生成物 `docs/kf/wp-459-01/envelope_conformance.json`（`scripts/kf/audit_envelope_conformance.py --write`）：该记录在 main 上已陈旧（记录的信封数与当前检出不符），使 `test_census_regenerates_byte_for_byte` 在无本包时也恒红；刷新后本包信封按 `schemas/kf_result.v1.schema.json` 判为 conforming。潜在冲突面仅此一个生成文件。
