# wp-5716-04 · 独立红队审核（report 5716 / 审核对象 wp-5716-01）

| 项 | 值 |
|---|---|
| package_id | `wp-5716-04` |
| task_type | `04-independent-review`（lane C） |
| report_id（唯一触碰） | `5716` |
| 审核对象 | `wp-5716-01`（IN10-G1 冰区航行全流程总攻验收门） |
| source_hash（契约=现场重算） | `sha256:4f9848b22b55515826476e1d5b2fcd15da80087a3d261d6a937a4c17cda68377` |
| 原文长度 | 4790 chars |
| disposition | **needs-fix** |
| findings | 10（high 3 / medium 3 / low 4；阻断 2：F1 C3 总时长双值、F2 披露集合 7 vs 4） |
| 独立复算后自洽 | 7 条（V1–V7，见 review_report.json `corroborated_claims`） |
| 已发布平台报告 | **14978（最终，唯一权威版本）**。历史：14964（初版，缺一键复跑块）→ 14967（补 repro，但仍引用被推送门禁滤除的 artifacts/ 路径）→ 14978（产物迁到 docs/ 后的终版）。平台无 PUT/PATCH（405），不能原地更新，故三代留痕不覆盖。 |

## 交付物

- `docs/kf/wp-5716-04/kf_result.json` — 结果信封（机器门；outputs 键名 = 契约声明的 `review_report.json`）
- `docs/kf/wp-5716-04/report.md` — 六段报告 + 唯一 ```json 块（= 信封），即平台报告的 markdown 原文
- `docs/kf/wp-5716-04/review_report.json` — 审核报告本体（findings / corroborated / checks_not_run / independence）
- `docs/kf/wp-5716-04/recompute.json` — 全部复算中间量（报告数字的唯一来源）
- `docs/kf/wp-5716-04/figures/*.png` — 2 图（⑥ 表百分比项 vs 验收线；时间/速度闭合反演）
- `docs/kf/wp-5716-04/source_5716.md(.meta.json)` — 原文快照与哈希钉点（`runs/wp-5716-04/report_payload.json` 由 publish 脚本按需再生，且 runs/ 被推送门禁滤除，不入库）
- `scripts/kf/{fetch,review,fig,assemble,validate,publish,verify}_*_5716_04 或 5716.py` — 工具链
- `tests/test_wp_5716_04_review.py` — 8 项不变量测试（含"篡改引文必须被抓到"的负控）

## 一键复跑

```bash
python3 scripts/kf/fetch_report_5716.py --out docs/kf/wp-5716-04/source_5716.md && \
python3 scripts/kf/review_wp_5716_04.py --offline && \
python3 scripts/kf/fig_wp_5716_04.py && \
python3 scripts/kf/assemble_wp_5716_04.py --offline && \
python3 scripts/kf/validate_wp_5716_04.py && \
python3 -m pytest tests/test_wp_5716_04_review.py -q && \
python3 scripts/kf/verify_published_5716_04.py --report-id 14978
```

## 边界自律

- 只读/写 `report_id=5716`；发布的是**新**报告（14967/14964），未改写 5716 任何字节。
- 未读生产者解释（summary）；findings 每条引文都由脚本断言为 markdown 逐字子串。
- 未把任何结论标 verified：`verification_status = NOT_VERIFIED_BY_REVIEWER`。
- `upstream_packages_completed` 因平台无包注册端点 → 标 **UNKNOWN**，不冒充 PASS。
## 路径纪律（踩坑留痕）

首版把产物放在 `artifacts/wp-5716-04/` 与 `runs/`，被仓库 `.gitignore`（`artifacts/`）+ 推送门禁
`scripts/audit_push_filter.py::R_RECORD ^(artifacts?/|runs/|results[-/]|REPORT_GATE)` 双重点名 →
产物不会进 GitHub，报告里引用的路径在克隆后不可达。终版把所有交付物迁到 `docs/kf/wp-5716-04/`，
仅在 `runs/` 留可再生的提交载荷。
