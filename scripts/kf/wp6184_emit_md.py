#!/usr/bin/env python3
"""Emit the wp-6184-04 delivery: kf_result envelope + KF-RESULT markdown.

The markdown carries exactly one ```json block (the envelope), because the
platform treats that block as the single result channel.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "docs/kf/wp-6184-04"
PACKAGE_ID = "wp-6184-04"
REPORT_ID = "6184"

review = json.loads((PKG / "review_report.json").read_text(encoding="utf-8"))
upstream_sha = review["provenance"]["upstream_kf_result_sha256"]
checks = {c["id"]: c for c in review["checks"]}

envelope = {
    "package_id": PACKAGE_ID,
    "task_type": "04-independent-review",
    "report_id": REPORT_ID,
    "provenance": {
        "source_hash": review["provenance"]["source_hash"],
        "source_field": "markdown",
        "producer": "agent/m15844 · scripts/kf/wp6184_review.py",
        "emitted_at": datetime.now(timezone.utc).isoformat(),
        "notes": ("reviewer context = source markdown of report 6184 + upstream wp-6184-01 "
                  "package artifacts + this work-package contract; producer narrative excluded. "
                  f"Upstream kf_result.json sha256={upstream_sha}. "
                  "Verdict applies to the reviewed package; source-report findings are "
                  "observations, listed separately."),
    },
    "outputs": {"review_report.json": review},
}

body_json = json.dumps(envelope, ensure_ascii=False, indent=2)
(PKG / "kf_result.json").write_text(body_json, encoding="utf-8")
envelope_sha = "sha256:" + hashlib.sha256(body_json.encode("utf-8")).hexdigest()

rows = "\n".join(
    f"| {c['id']} | {c['name']} | {c['status']} | {c['detail']} |" for c in review["checks"])
findings = "\n".join(
    f"| {f['id']} | {f['severity']} | {'yes' if f['blocking'] else 'no'} | {f['target']} | "
    f"{f['statement'].replace('|', '/')} |" for f in review["findings"])
loc = checks["R3.locators_byte_exact"]
margin = checks["R7.margin_arithmetic"]

md = f"""# KF-RESULT {PACKAGE_ID}

**工序** 04 独立审核（red-team） · **报告** report_id=6184 · **审核对象** `wp-6184-01`（01-asset-registration）
**结论** `verdict = {review['verdict']}`（阻断性失败 {review['summary_counts']['fail_blocking']} 项；非阻断失败 {review['summary_counts']['fail_non_blocking']} 项；未执行 {review['summary_counts']['not_run']} 项）

## ① 本工序做了什么

对上游 `wp-6184-01`（report 6184 的资产登记包）做独立审核：不采信生产者叙述，只用**报告原文 2406 字符**与**上游产物字节**重算一遍，判其登记是否忠实、计数是否掺水、是否自封验证、零 claim 是否合法；顺带用报告自己的数字做算术闭合探针，把过强的证据表述标出来供下游 03 抽取时不被传染。共 10 个探针，8 过 1 未执行 1 非阻断失败。

## ② 怎么做的（步骤/工具/关键设置）

1. `GET /api/v1/tensor/reports/6184`（Bearer）取 `markdown`，本地重算 `sha256` 得 `{review['provenance']['source_hash']}`，与工作包契约 `input.source_hash` 逐字节相等，字符数 {review['provenance']['source_chars']} 与契约 2406 相等（探针 R1）。原文快照落盘 `source_snapshot.md`，使离线可复验。
2. 遍历上游 manifest 的 10 个资产，对每个 locator 重算 `markdown[start_char:end_char] == quote`、quote 在原文中的出现次数、以及 1-based 行号（R3）。
3. 用资产列表反算 `counts.assets / by_class / resolved_in_source`，与 manifest 自述比对（R4）；扫描上游信封是否出现自封验证字段（R6）。
4. 从原文表格解析 EEXI/要求/裕度三列，用**发布列**重算裕度，并按两列各自 3 位小数打印的舍入包络做**区间检验**（不是点值比对，避免把打印舍入当误差）（R7）；数出"不装 EPL 达标"的船数（R8）。
5. 探针 R9：报告自称 `EEXI ∝ P_ME^(2/3)`，用它复算 82k 散货的 EPL 27.4% —— 主机理式给 24.9%，差 2.5 个百分点，方向与"辅机项未被限功率"一致，但要闭合必须有引擎源码，故记 **not_run**，不记通过。
6. 探针 R10（补全度）：扫原文中所有反引号路径 token（4 个），排除整篇文档资产后比对 manifest，暴露 1 个未登记路径 → 发现项 F1。
7. 工具链：Python 3.11 + `scripts/kf/wp6184_review.py`（确定性，可 `--no-api` 离线复跑）、`scripts/kf/wp6184_figure.py`（证据图）、`pytest`。审核 prompt 由本工作包契约+原文自拟，未复制生产 prompt；上下文不含生产者 `provenance.notes` / `integrity.notes` / 上游叙述 MD。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `review_report.json` | 审核结论信封内容：10 探针状态 + 4 项发现（F1 minor / F2 major / F3-F4 minor）+ 语义忠实判定 + 下游告诫 + not_run 清单 |
| `review_report.schema.json` | 本包自带 schema（仓内无 review_report 统一 schema，供 `schema_pass` 机器可判） |
| `kf_result.json` | kf_result.v1 交付信封，`outputs["review_report.json"]` 即上表首项，本文件 sha256={envelope_sha} |
| `source_snapshot.md` | 报告 6184 原文逐字节快照（sha256 与契约相等），离线复验用 |
| `upstream_snapshot/kf_result.json` | 上游 `wp-6184-01` 交付只读副本（sha256={upstream_sha}），未改写 |
| `review_checks.json` | 10 探针原始结果 + 11 行裕度区间 + EPL 探针 + 补全度扫描 |
| `figures/review_6184_evidence.png` | 左：探针状态矩阵（含非阻断失败，不隐藏）；右：报告发布裕度 vs 重算值（恒等线+舍入带） |
| `scripts/kf/wp6184_review.py` / `wp6184_figure.py` / `tests/test_wp6184_04_review.py` | 审核器 / 出图 / 12 条验收测试 |

## ④ 证据定位表（claim → 原文逐字片段）

| 判定 | 原文引文（逐字，可 `str.find` 定位） |
|---|---|
| 上游 source_hash 正确 | `sha256:f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c` 本地重算相等，2406 字符相等 |
| 10/10 资产 locator 字节精确 | 逐资产 `md[start:end] == quote` 全为真；行号 `1..43` 全部复现（R3 明细见 `review_checks.json`） |
| 零 claim 合法 | `claims: []` 且 `task_type=01-asset-registration`；01 的职责是登记不是抽取 |
| 内容不含自封验证 | 扫描 `verified / verification_status / verification_level / is_verified / gate_confirmed` 命中 0（R6） |
| F1 未登记资产 | `` `backend/api/green_shipping.py` 集装箱船 EEXI 削减率未按吨位分档（一律 20%） `` |
| F2 证据强度 | `| 达到 EEXI（11 船） | 独立闭式手算 | 0.0e+00 | **是** |` |
| F3 年份窗口自相矛盾 | `CII：2023→2026 评级随 Z% 收紧单调下降（如 Post-Panamax 8500TEU：E→E，比值 1.35→1.44）` 对比 §4 `CII 评级矩阵 2023–2027` |
| F4 几何关数自相矛盾 | `` `fleet`（几何三关） `` 对比 §3 `几何：12/12 过 Cb/L·B·T、DWT/Δ 包络、L/B·B/T 包络、高 Cb+高 Fn 组合检查。` |
| R7 算术闭合 | 11/11 行的发布裕度落在 `EEXI`/`要求` 两列打印舍入可达区间内（最大偏离 −7.2508 vs 发布 −7.2，band [−7.3216,−7.1799]） |
| R8 达标数 | `不装 EPL 达标 **2/11**` ↔ 表内仅 `feeder_1700teu`(16.417≤20.161)、`lng_174k`(5.157≤7.960) 达标 |
| R9 未闭合 | `例：82k 散货 attained 4.219 vs required 3.486（−21.0%，需 EPL 27.4%）` 与 `EEXI ∝ P_ME^(2/3)`：主机理式 24.9% |

## ⑤ 注意点与局限

- **审核对象与观察对象分离**：verdict 只判 `wp-6184-01`（登记是否忠实合法）。F2/F3/F4 是**报告本身**的证据强度/自洽问题，不改上游包 verdict，但下游 03 不得把 §6 前四行当作"独立/外部精度验证"来引用（`下游告诫` 已写入 review_report）。
- **F2 是本单最该被看见的一条**：标题与 §6 的 `0.00%` 建立在"独立闭式手算/双实现互校"两个未发布基线上；11 船**恰好** 0.0e+00 更像同一代数式的等价重算（R7 证明它至少是自洽的），而不是外部精度。若下游成稿照抄"外部基准 0.00%"，会把自洽说成验证。
- **不可闭合项已如实记 not_run**：R9 需引擎源码（在 ship-performance-platform，本仓不可达）；上游 `artifacts/in28_i1/checks.json`（`15/15 通过` 的唯一凭据）同样不可达 → 本单**不复制**该结论。
- **报告图不可读**：平台 `/tensor/reports/6184/figures/in28i1_figures_1to4.png` 返回 404，四联图只能按声明处理，未目视核对。
- 独立性是**程序性**的：新工位、契约自制 prompt、上下文只含原文与上游产物；但同一 owner 舰队、同一套服务，非组织级独立，已在 `reviewer.independence_limitations` 写明。
- 边界遵守：只碰 report_id=6184；未改写上游产物（只做只读副本）；未给任何结论打 verified（结论由平台门计算）。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 依据 |
|---|---|---|
| `valid_json` | ✅ | `review_report.json` / `kf_result.json` 均 `json.loads` 通过；测试 `test_review_report_is_valid_json` |
| `schema_pass` | ✅ | 经本包 `review_report.schema.json` 校验通过（`test_review_report_schema_pass`） |
| `reviewer_independent` | ✅ | 审核 prompt 契约自拟未复制生产 prompt；上下文排除生产者叙述；identity=agent/m15844 ≠ 上游 producer=agent/m15587 |
| `upstream_packages_completed` | ✅ | 上游 `wp-6184-01` 产物齐全（kf_result/asset_manifest/asset_manifest.schema/source_snapshot/verification），source_hash 与契约一致，10 资产 locator 全可解析 |
| `constraints.review_prompt_not_copied_from_producer` | ✅ | 审核器 prompt 为探针清单（见 ②），与生产抽取 prompt 无共享文本 |
| `constraints.reviewer_context_excludes_producer_explanation` | ✅ | `reviewer.context_excluded` 列明排除三项，判定只用原文与产物字节 |
| `constraints.do_not_mark_claims_as_verified` | ✅ | 全文无自封验证类字段名（`test_no_self_attestation_fields_anywhere`）；verdict 用 pass/fail |
| `objective.judge_semantic_fidelity` | ✅ | `semantic_fidelity.overall = faithful`，含 basis 与 residual_risk（0 claim、10 资产、7/10 保守标 unresolved） |

**honest-FAIL 项（不粉饰）**：`R9.epl_law_probe` = not_run（缺引擎源码，27.4% 与主机理式 24.9% 的 2.5pp 差**未闭合**）；`N2` 外部基准确认未做（源报告自述离线不可得，`WITHHELD`）。这两条使本单**不能**支持"引擎精度已外部验证"的任何说法。

## 复跑

```bash
# 一键复跑（工作树根 = TensorKnowledge 检出）
python3 scripts/kf/wp6184_review.py            # 联网取原文并重算全部探针 → review_report.json
python3 scripts/kf/wp6184_review.py --no-api   # 只对提交的 source_snapshot.md 离线复验
python3 scripts/kf/wp6184_figure.py            # 证据图
python3 -m pytest tests/test_wp6184_04_review.py -q   # 12 passed
```

## 结果信封（唯一 json 块）

```json
{body_json}
```
"""
out = PKG / "KF-RESULT-wp-6184-04.md"
out.write_text(md, encoding="utf-8")
print(out, len(md), "chars; envelope", envelope_sha)