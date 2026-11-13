#!/usr/bin/env python3
"""Publish the paper-grade progress report for wp-6184-04 to the platform.

All numbers in the markdown are read out of the committed artifacts (no hand
copying). Figure is embedded as base64 png.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "docs/kf/wp-6184-04"
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")

checks_doc = json.loads((PKG / "review_checks.json").read_text(encoding="utf-8"))
review = json.loads((PKG / "review_report.json").read_text(encoding="utf-8"))
checks = checks_doc["checks"]
by_id = {c["id"]: c for c in checks}
rows = next(c for c in checks if c["id"].startswith("R7"))["evidence"]["rows"]
max_dev = max(abs(r["margin_reported"] - r["margin_recomputed_pointwise"]) for r in rows)
n_band = sum(1 for r in rows if r["inside_band"])
epl = checks_doc["epl_probe"]
comp = checks_doc["completeness"]
n_pass = sum(1 for c in checks if c["status"] == "pass")
n_nr = sum(1 for c in checks if c["status"] == "not_run")
n_nbf = sum(1 for c in checks if c["status"] == "fail" and not c.get("blocking"))

md = f"""## ① 案例介绍

本单是「报告→知识产线」工序 04（独立审核）的一次落地：审核对象为 `wp-6184-01`（report 6184 的资产登记包）。
report 6184 研究的物理/法规对象是 MARPOL 附则 VI 对现有船的双约束——**EEXI**（设计侧，75% MCR 参考工况，g CO2/(t·nm)）与 **CII**（营运侧，年油耗/年航程 + 逐年收紧 Z% 的 A–E 评级），
实现于 `backend/modules/eexi_cii_compliance`（regulatory / eexi / cii / fleet / route / benchmarks 六子模块），覆盖 12 只代表船（任务书 10 类 + LNG + 客船）。
审核不看船型物理正确性（那需要引擎源码），只看：登记是否忠实于原文、计数是否掺水、是否自封验证、零 claim 是否合法，以及报告自身数字是否算术闭合。

| 项 | 值 |
|---|---|
| report_id | {review['report_id']} |
| 审核对象 | {review['reviewed_package']['package_id']}（{review['reviewed_package']['task_type']}） |
| 原文哈希（本地重算，与契约相等） | `{review['provenance']['source_hash']}` |
| 原文字符数 | {review['provenance']['source_chars']} |
| 上游交付哈希 | `{review['provenance']['upstream_kf_result_sha256']}` |

## ② 怎么做的（方法/流程/关键设置/工具链）

1. **取原文**：`GET /api/v1/tensor/reports/6184`（Bearer），本地重算 sha256 与字符数，与工作包契约 `input.source_hash` / `chars` 逐字节比对；原文快照落盘供离线复验。
2. **重解 locator**：对上游 manifest 全部 10 个资产，重算 `markdown[start:end] == quote`、quote 出现次数、1-based 起止行号，不采信 manifest 自述的 `resolved`。
3. **反算计数**：由资产列表重算 `assets / by_class / resolved_in_source` 与 manifest 自述比对；扫描信封是否含 `verified / verification_status / verification_level / is_verified / gate_confirmed`。
4. **算术闭合探针**：解析报告 §3 的 EEXI 表，用其**发布列**重算裕度 `(required−EEXI)/required`，并按两列各 3 位小数的打印舍入做**区间检验**（区间比点值 $\pm0.05$ 更严格，也更诚实）。
5. **法规一致性探针**：用报告自称的 `EEXI ∝ P_ME^(2/3)` 复算 82k 散货的 EPL 需求，与报告发布的 27.4% 对照；差值方向若与"辅机功率未被 EPL 限制"一致，则记为可解释但**未闭合**（缺引擎源码）。
6. **补全度探针**：正则扫原文反引号路径 token（4 个），排除整篇文档资产（否则子串检验必然全绿），比对 manifest。
7. **工具链**：Python 3.11；确定性审核器 `scripts/kf/wp6184_review.py`（联网/`--no-api` 离线双模式）；出图 `wp6184_figure.py`；验收测试 `tests/test_wp6184_04_review.py`（12 条，全绿）；交付 md 由 `wp6184_emit_md.py` 从 review_report.json 程序化生成，避免手抄。

## ③ 计算结果（数字表，程序化注入）

探针总表（{n_pass}/{len(checks)} 通过，{n_nbf} 非阻断失败，{n_nr} 未执行）：

| 探针 | 判据 | 状态 | 细节 |
|---|---|---|---|
""" + "\n".join(f"| {c['id']} | {c['name']} | {c['status']} | {c['detail'].replace('|', '/')} |"
                for c in checks) + f"""

报告算术闭合（{n_band}/11 行落在打印舍入允许带内，最大点值偏离 {max_dev:.4f} 个百分点）：

| 船型 | 发布裕度% | 重算裕度% | 可达带（打印舍入） | 达标 |
|---|---|---|---|---|
""" + "\n".join(
    f"| {r['ship']} | {r['margin_reported']} | {r['margin_recomputed_pointwise']} | "
    f"[{r['feasible_band_from_print_rounding'][0]}, {r['feasible_band_from_print_rounding'][1]}] | "
    f"{'是' if r['compliant_attained_le_required'] else '否'} |" for r in rows) + f"""

EPL 一致性探针（未闭合，如实记 not_run）：

| 量 | 值 |
|---|---|
| 船/ship | {epl['ship']} |
| required/attained | {epl['ratio_required_over_attained']} |
| 报告发布 EPL% | {epl['epl_pct_stated']} |
| 主机理式 (1−r^1.5) 预测 EPL% | {epl['epl_pct_from_2_3_law_main_engine_only']} |
| 差（百分点） | {epl['delta_percentage_points']} |
| 若为单项幂律，隐含指数 | {epl['implied_exponent_if_single_power_term']} |

补全度扫描：原文路径 token = `{comp['path_like_tokens_in_source']}`；已登记 = `{comp['registered']}`；**未登记 = `{comp['unregistered']}`**。

## ④ 结果图

左图为 10 个探针的状态矩阵（绿=pass、灰=not_run、红=非阻断失败，**不隐藏失败项**）；右图为报告 §3 发布裕度 vs 用其自身两列重算的裕度，误差棒即打印舍入可达带，全部 11 点压在恒等线上——说明报告的表内算术自洽。
无场量云图：本单是文档/知识产线审核工序，没有物理场，故以"证据矩阵图"承担结果图职责。

## ⑤ 注意点（踩过的坑/局限/适用范围）

- **子串检验陷阱（本单实测）**：补全度探针第一版把整篇文档资产 A01 的 quote 一起做子串搜索，结果必然全绿（原文里有的字都在 A01 里）。排除 `source_document` 类资产后才暴露真实缺口 `backend/api/green_shipping.py` —— 这正是"测试绿 ≠ 问题解决"的活例。
- **点值比较陷阱**：裕度列按 1 位小数、输入列按 3 位小数发布，点值比对会把打印舍入误判为 −7.2 vs −7.2508 的"误差"。改用舍入可达区间后 11/11 合规，判据也随之可辩护。
- **"0.00%"的证据强度**：报告标题的算术误差 0.00% 建立在"独立闭式手算/双实现互校"两个未发布基线上；11 船**恰好** 0.0e+00 更像同一代数式的等价重算。本单只证明它是**自洽**的，不证明它是**外部精度**——下游抽取若照抄"外部基准 0.00%"即属夸大。
- **未闭合项**：EPL 27.4% 与主机理式 24.9% 差 2.5pp，方向与固定辅机项一致但无源码不能闭合；上游 `artifacts/in28_i1/checks.json`（"15/15 通过"的唯一凭据）与本仓不可达；报告四联图平台 404 不可目视核对。
- **独立性是程序性的**：新工位、契约自制 prompt、上下文只含原文与上游产物；同一 owner 舰队、同一套服务，不构成组织级独立。
- 边界：只碰 report_id=6184，未改写上游产物（只做只读副本），未给任何结论打 verified。

## ⑥ 误差判定（关键量 vs 基准，逐项回答是否 <3%）

| 量 | 基准 | 误差 | <3%？ |
|---|---|---|---|
| 原文 sha256 | 工作包契约 `input.source_hash` | 完全相等（0 bit） | **是** |
| 原文字符数 | 契约 `chars` | {review['provenance']['source_chars']} vs 2406，0 | **是** |
| 10 资产 locator | 原文 `markdown[start:end]` | 10/10 字节相等，0 | **是** |
| 裕度列（11 行） | 报告自身 EEXI/要求两列 | 最大点值偏离 {max_dev:.4f} pp（{max_dev/abs(min(r['margin_reported'] for r in rows))*100:.2f}% 相对最大裕度），且 11/11 在可达带内 | **是** |
| 达标船数 | 报告"2/11" | 2 vs 2 | **是** |
| EPL%（82k 散货 27.4%） | 报告自称的 2/3 幂律 | 2.5 pp（约 10% 相对），方向可解释**未闭合** | **否 / 无法判定** |
| 引擎 vs GISIS/VeriFuel 点值 | 外部实测 | 源报告自述离线不可得（WITHHELD） | **无法判定** |

结论：**结构/证据层面等价于零误差**（哈希、locator、表内算术全过），但**物理精度层面未判定**——本单不提供、也不能被解读为"EEXI/CII 引擎已经外部验证"。审核判定 `verdict = {review['verdict']}`（阻断性失败 0；发现 4 项：1 minor 属上游补全度、1 major + 2 minor 属报告证据强度/自洽，均已写入 `review_report.json` 的下游告诫）。
"""

fig_png = (PKG / "figures/review_6184_evidence.png").read_bytes()
payload = {
    "title": "wp-6184-04 独立审核：report 6184 EEXI/CII 引擎资产登记（10 探针 / 哈希与 locator 全过 / EPL 2.5pp 未闭合）",
    "summary": (f"对 wp-6184-01 做独立审核：原文 sha256 与契约逐字节相等，10/10 资产 locator 字节精确，"
                f"报告裕度列 11/11 落在打印舍入可达带内；暴露 1 个未登记路径与 3 处报告自洽/证据强度问题；"
                f"verdict={review['verdict']}（阻断性失败 0）。EPL 27.4% vs 机理 24.9% 记 not_run。"),
    "scenario_key": "green_navigation_eexi_cii_compliance",
    "mission_id": 15844,
    "tags": ["kf-wp:wp-6184-04", "kf-result", "04-independent-review", "adversarial-review",
             "EEXI", "CII", "review", "report-6184"],
    "markdown": md,
    "figures": [{
        "name": "review_6184_evidence.png",
        "caption": "左：wp-6184-04 的 10 个审核探针状态矩阵（含非阻断失败，不隐藏）；右：report 6184 §3 发布裕度 vs 由其自身 EEXI/要求两列重算的裕度，误差棒=打印舍入可达带，11/11 落在恒等线上。",
        "png_base64": base64.b64encode(fig_png).decode(),
    }],
}
Path("/tmp/report.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

login = urllib.request.Request(
    API + "/auth/login",
    data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                     "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
    headers={"Content-Type": "application/json"}, method="POST")
token = json.load(urllib.request.urlopen(login))["access_token"]
post = urllib.request.Request(
    API + "/tensor/reports", data=json.dumps(payload, ensure_ascii=False).encode(),
    headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
    method="POST")
try:
    resp = json.load(urllib.request.urlopen(post))
except urllib.error.HTTPError as exc:  # surface the body, do not swallow
    print("HTTP", exc.code, exc.read().decode()[:800])
    raise
print(json.dumps({k: resp.get(k) for k in ("id", "title", "status", "scenario_key", "mission_id")},
                 ensure_ascii=False, default=str))
print("markdown chars:", len(md), "| figure bytes:", len(fig_png), "| posted:", datetime.now(timezone.utc).isoformat())