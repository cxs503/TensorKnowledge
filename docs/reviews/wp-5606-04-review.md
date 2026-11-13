# wp-5606-04 独立审核（report 5606 / 上游 wp-5606-01）

处置：**request-changes**（数值层未见矛盾；反造假证据本身未被冻结）。

| 项 | 值 |
|---|---|
| 被审对象 | report_id=5606，markdown，`sha256:da0d91e5…b14edd`（5853 字符） |
| 审核者角色 | red-team-reviewer（独立上下文：仅原文 + 契约） |
| 检查项 | 18（pass 8 / fail 7 / not_run 3） |
| 发现 | major 4（F1–F4）/ minor 3（F5–F7）/ informational 2（F8–F9） |
| 结果信道 | `artifacts/wp-5606-04/KF-RESULT_wp-5606-04.md`（唯一 json 块）+ `review_report.json` |

## 四条 major

1. **F1** 被审 markdown 内无任何真实 `{{prov:<id>}}` 标注、无 prov 块 → 核心断言「块内裸数字 0」不可复核。
2. **F2** 冻结工件路径 `/root/tp-agent/work/m4976/…/capability_ledger_resolved.json` 已不存在 →
   `snapshot_hash f46ab6f3…` 不可独立复算（记 not_run，不记 pass）。
3. **F3** 声明 8 类 FAIL 码，仅 5 类有命名负例，与自身教训「没有负例的门禁等于没有门禁」冲突。
4. **F4** 图件账本只登记字节哈希，不登记图数组的 (sql, params) → 「图数组 = 一条可重跑 SQL」不可复核。

## 正面结论

表 1 百分比全部由计数精确导出（最大相对偏差 1.0e-06）；OK+OVERCLAIM+UNVERIFIED = 21 闭合；
宣称 REAL 18 被 1+2+15 完全解释 —— 未见伪造痕迹。

## 复跑

```bash
bash artifacts/wp-5606-04/run_all.sh
```

产物：`indep_check.py`（18 项复算）、`indep_check.json`、`build_report.py`、`review_report.json`、
`review_events.json`、`work-package.json`、`schema_validation.json`、
`fig_wp5606_04_ledger_consistency.png`；回归测试 `tests/test_wp_5606_04_review.py`（7 passed）。