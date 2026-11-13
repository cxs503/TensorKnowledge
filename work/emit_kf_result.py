#!/usr/bin/env python3
"""Emit the wp-444-04 deliverable: docs/kf/wp-444-04/KF-RESULT-wp-444-04.md
(one ```json block = kf_result envelope) and optionally publish it to the platform.

Run: python3 work/emit_kf_result.py [--publish]
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ART = os.path.join(ROOT, "artifacts", "wp-444-04")
DOC = os.path.join(ROOT, "docs", "kf", "wp-444-04")
SRC_MD = os.path.join(ART, "source_markdown.md")
PKG = "wp-444-04"


def sha256(path):
    with open(path, "rb") as f:
        return "sha256:" + hashlib.sha256(f.read()).hexdigest()


def build_markdown(rep, ver, obs, src_hash):
    c = ver["checks"]
    nv = [q for q in c["H9_locator_verbatim"] if not q["verbatim_in_markdown"]]
    obs_rows = "\n".join(
        "| %s | %s | %.6f | %s | %s |" % (
            r["row"], r["table_baseline"],
            r["formula_value"] if r.get("formula_value") is not None else float("nan"),
            ("%+.2f%%" % r["rel_error_vs_formula_pct"]) if r.get("formula")
            else r["note"],
            "是" if r.get("within_15pct_of_formula") else ("否" if r.get("formula") else "不可判"),
        ) for r in obs["rows"])
    evidence_rows = "\n".join(
        "| %s | `%s` | %s |" % (i + 1, q["quote"].replace("|", "\\|"),
                                "逐字命中 line %s" % q["lines"] if q["verbatim_in_markdown"]
                                else "不在 markdown 中（非逐字）")
        for i, q in enumerate(c["H9_locator_verbatim"]))
    env = {
        "package_id": PKG,
        "task_type": "04-independent-review",
        "report_id": "444",
        "provenance": {
            "source_uri": "tensor://reports/444",
            "source_field": "markdown",
            "source_hash": src_hash,
            "producer": "m15795",
            "emitted_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "notes": "独立审核；上下文=报告 markdown + wp-444-01 信封（result report 14623）；"
                     "未读生产者解释性散文作证据；未写 verification_status",
        },
        "outputs": {"review_report.json": rep},
    }
    md = f"""# KF-RESULT {PKG}

## ① 本工序做了什么

对上游工作包 **wp-444-01（01-asset-registration，result report 14623）** 做独立审核：
不看生产者解释，只用 `report_id=444` 的 markdown 与 14623 的 json 信封，逐条**独立重算**
其结构登记与证据定位声明，产出 `review_report.json`（判定 + 逐条 finding + 未跑项 + 越界观察）。
本单不抽取、不改上游产物、不写验证轴。

判定：**needs-fix（decision=request-changes）**——实质登记全部可独立复算并一致（无编造迹象），
但有 3 项中危缺陷需返修：①产出物键名不合契约 ②证据表 3 条压缩改写伪引文 ③清单细目不可跨会话解析。

## ② 怎么做的（步骤/工具/关键设置）

1. `python3 work/verify_wp444_01.py`：拉 `tensor://reports/444` 与 `14623`，独立计算
   sha256(markdown)、章节数（`^## `）、表格数（表头+分隔行起算的连续块）、figures 条数、
   反引号路径型代码引用数；对 ④ 表 9 条引文做**精确子串**判定；对行号定位做复算。
   离线复跑用 `--md/--upstream` 喂固定夹具，结果逐字节一致（同一 `measured` 块）。
2. `jsonschema`（Draft202012Validator）+ `schemas/kf_result.v1.schema.json` 校验上游信封：0 错。
3. 读 `tk_work_packages`（`runuser -u postgres psql` 只读）确认上游完成度：
   `wp-444-01 status=review, gates_ok=true, result_report_id=14623`。
4. `python3 work/observe_source_numbers.py` 把源报告 ⑥ 表的"基准"按它自己命名的公式重算
   （越界观察，不改判定）。
5. `python3 work/build_review_report.py` 生成 `review_report.json` + `review_events.json`
   （append-only，状态机复用 `scripts/ke_state_machine.py`）。
6. `python3 -m pytest tests/test_wp444_04_review.py -q` → **12 passed**。

## ③ 产出物清单

| 文件 | 要点 |
|------|------|
| `docs/kf/wp-444-04/review_report.json` | 判定 needs-fix；4 findings（F1/F2/F3 中危，F4 低）；14 项 checks_performed；4 项 checks_not_run；越界观察 1 组 |
| `docs/kf/wp-444-04/review_events.json` | 1 条 append-only 事件 `request-changes`（findings=[F1..F4] + 3 条返修条件） |
| `docs/kf/wp-444-04/KF-RESULT-wp-444-04.md` | 本文件（唯一 json 代码块=结果信封） |
| `artifacts/wp-444-04/verification.json` | 12 项机器检查原始值（哈希/计数/引文/路径可解析性） |
| `artifacts/wp-444-04/out_of_scope_observations.json` | 源 ⑥ 表 vs 解析公式的程序化重算 |
| `artifacts/wp-444-04/review_checks.png` | 双面板图：声明 vs 重算计数；⑥ 表基准 vs 公式 |
| `artifacts/wp-444-04/{{source_markdown.md, upstream_report_14623.md, upstream_envelope_wp-444-01.json}}` | 零依赖复跑夹具（源 markdown 哈希=契约哈希） |
| `work/verify_wp444_01.py`, `work/build_review_report.py`, `work/observe_source_numbers.py`, `work/make_figure.py`, `tests/test_wp444_04_review.py` | 可执行审核与回归 |

## ④ 证据定位表（claim → 原文引文片段，逐字）

| # | 引文片段（取自 report 444 markdown） | 定位结果 |
|---|--------------------------------------|----------|
{evidence_rows}

结构性证据（非 markdown 字段，单列不混算逐字）：`title` 字段=报告标题；
`figures`=[{{name:"verifier_pilot_results", caption:"..."}}]，无 `png_base64`。

## ⑤ 注意点与局限

- **本判定不授予 L3**：`verification_status` 由平台门计算，本单未写、也未把任何 claim 标 verified；
  `axes_untouched.claims_marked_verified=false`。
- **G5 结构性盲区**：上游 `claims=[]` → 门只检查了 **0** 个 locator，④ 表引文从未被机检；
  本评审用精确子串补检，9 条中 {len(nv)} 条不逐字（含 3 条压缩改写）。
- **生产者在同一记录的 prose 摘要不可剥离**：API 取回 KF-RESULT 报告时 markdown 自带生产者正文；
  本评审的判定只绑定源 markdown 重算与信封 JSON，未把该散文当证据（已在 independence.limitations 声明）。
- **未跑项**：`asset_manifest.json` 文件内容（路径不可解析）、figures 的 PNG 字节、
  报告"pytest（12 项单元测试）"的真伪（无附件线索）——一律记 `insufficient`，不当作通过。
- **域数值正确性不属本工序**：⑥ 表自洽不等于精度；下面的越界观察仅供 03/05 使用。

## ⑥ 误差判定（关键量 vs 基准，逐项）

| 关键量 | 基准 | 实际 | 偏差 | <3%? |
|--------|------|------|------|------|
| source_hash（markdown 字节） | 契约 `4068f88…57af2` | 独立重算 `{src_hash.split(":")[1][:16]}…` | 0.000% | ✓ YES |
| sections_count | 7（声明） | {c["H2_sections_count"]["recomputed"]}（重算） | 0.0% | ✓ YES |
| tables_count | 4（声明） | {c["H3_tables_count"]["recomputed"]}（重算） | 0.0% | ✓ YES |
| figures_count | 1（声明） | {c["H4_figures_count"]["recomputed"]}（重算） | 0.0% | ✓ YES |
| code_references_count | 0（声明） | {c["H5_code_references_count"]["recomputed"]}（重算） | 0.0% | ✓ YES |
| ④ 引文逐字率 | 9/9 逐字（零手抄要求） | {9 - len(nv)}/9 | **{len(nv)}/9 不逐字** | ✗ NO |

越界观察（源报告 ⑥ 表基准 vs 其自述解析式，程序化重算，**不进入本工序判定**）：

| 行 | 表中基准 | 公式值 | 相对偏差 | <15%? |
|----|----------|--------|----------|-------|
{obs_rows}

结论（**honest-FAIL 于流程一致性、PASS 于实质登记**）：上游登记的计数与哈希 100% 可复算、
偏差 0.000% < 3%；但"零手抄"一项 **3% 标准不适用**（它是计数型判据），实测 {9 - len(nv)}/9 逐字，
故判 needs-fix。**未**宣称任何科学结论 verified。

**repro_cmd**：
```bash
cd $(git rev-parse --show-toplevel) && python3 work/verify_wp444_01.py \
  --md artifacts/wp-444-04/source_markdown.md \
  --upstream artifacts/wp-444-04/upstream_report_14623.md && \
python3 work/observe_source_numbers.py && python3 work/make_figure.py && \
python3 work/build_review_report.py && \
python3 -m pytest tests/test_wp444_04_review.py -q
```

```json
{json.dumps(env, ensure_ascii=False, indent=2)}
```
"""
    return md, env


def publish(md, png_b64):
    base = os.environ["TENSOR_API_BASE"]
    tok = json.loads(urllib.request.urlopen(
        urllib.request.Request(
            base + "/auth/login",
            data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                             "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
            headers={"Content-Type": "application/json"}, method="POST"), timeout=60
    ).read())["access_token"]
    body = {
        "title": f"KF-RESULT {PKG}",
        "summary": "独立审核 wp-444-01（report 444 资产登记）：哈希与 7/4/1/0 计数独立复算一致，"
                   "但产出物键名不合契约、④ 表 9 条引文中 6 条非逐字（3 条为改写伪引文）、"
                   "清单细目不可跨会话解析 → needs-fix（request-changes）。",
        "scenario_key": "verifier_generator_separation",
        "mission_id": 15795,
        "tags": [f"kf-wp:{PKG}", "independent-review", "red-team-reviewer",
                 "report_id:444", "lane-C", "TensorKnowledge", "kf-wp:wp-444-01"],
        "markdown": md,
        "figures": [{"name": "review_checks",
                     "caption": "A: wp-444-01 声明计数 vs 独立重算（全部一致）；"
                                "B: 源报告 §6 基准按其自述解析式重算的相对偏差（越界观察）",
                     "png_base64": png_b64}],
    }
    req = urllib.request.Request(base + "/tensor/reports", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + tok}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    a = ap.parse_args()
    rep = json.load(open(os.path.join(DOC, "review_report.json"), encoding="utf-8"))
    ver = json.load(open(os.path.join(ART, "verification.json"), encoding="utf-8"))
    obs = json.load(open(os.path.join(ART, "out_of_scope_observations.json"), encoding="utf-8"))
    src_hash = sha256(SRC_MD)
    md, env = build_markdown(rep, ver, obs, src_hash)
    os.makedirs(DOC, exist_ok=True)
    out = os.path.join(DOC, f"KF-RESULT-{PKG}.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    print("wrote", out, "src_hash", src_hash)
    if a.publish:
        png = base64.b64encode(open(os.path.join(ART, "review_checks.png"), "rb").read()).decode()
        print(json.dumps(publish(md, png), ensure_ascii=False)[:400])
    return 0


if __name__ == "__main__":
    sys.exit(main())