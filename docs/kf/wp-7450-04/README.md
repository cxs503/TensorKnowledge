# wp-7450-04 · 04-independent-review · report_id=7450

审核对象：上游包 `wp-7450-01`（01-asset-registration）。
审核人不下结论「verified」——verification 由平台门计算；本包只给 pass / needs-fix 与证据。

**裁决：`pass`（approve-with-notes）** — 0 阻断项；27 项独立检查 26 通过 / 1 软失败。

| 文件 | 内容 |
|---|---|
| `review_report.json` | 结构化审查结论：裁决、6 条发现（含逐字引文）、27 项检查明细、not_run 清单、独立性声明 |
| `verify_wp7450_04.py` | 独立复核脚本：重取原文、重算哈希、重解 19 个定位子、重导表 1 算术、schema 校验；退出码=硬失败数 |
| `verify_output.json` | 脚本输出（每项检查 pass/detail/hard） |
| `build_review.py` | 由复核输出重建 review_report.json / 图 / 报告，并带「零手抄」断言 |
| `report.md` | 六段工序报告，唯一 ```json 块 = 结果信封 |
| `figures/fig_wp-7450-04_review_evidence.png` | 三联图：定位跨度覆盖 / 表 1 算术残差 / 检查通过矩阵 |
| 平台报告 | `published_report_id=14972`（title `KF-RESULT wp-7450-04`） |

## 发现摘要

| ID | 严重度 | 阻断 | 标题 |
|---|---|---|---|
| F1 | low | 否 | 上游 `integrity.quote_uniqueness.repeated_quotes` 为空，与 18/19 唯一计数矛盾（A18 `/cii` 原文出现 4 次） |
| F2 | medium | 否 | 报告把 api-vs-service 一致性当独立证据，但修复后二者是「别名+委托」的构造性恒等 |
| F3 | low | 否 | §⑥ 声称 4×4×4=64 格网格，markdown 只列 16 格（80 000 t） |
| F4 | low | 否 | 「164 项回归」的另一仓测试不可在本上下文运行 → not_run |
| F5 | info | 否 | §① 给 attained 链标 REAL，但报告未做 attained 计算 |
| F6 | info | 否 | 2027+ 仍返回数值，语义靠 `z_extrapolated` 标记传递 |

复跑：`python3 docs/kf/wp-7450-04/verify_wp7450_04.py && python3 docs/kf/wp-7450-04/build_review.py`

边界：本包只读写 report_id=7450 的原文与 `docs/kf/wp-7450-01/` 上游 artefact；
跨仓引用（`backend/…`、`artifacts/…`）在本工作树不存在，如实记 not_run / referenced_unresolved。