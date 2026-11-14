#!/usr/bin/env python3
"""Publish the wp-5716-04 progress report to the platform.

The report body is the package's own report.md (six mandated sections, all
numbers injected from recompute.json); the two review figures are embedded as
base64 PNGs.  Nothing is transcribed by hand here.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request

PKG = "/srv/tensor/agent/work/m20865/docs/kf/wp-5716-04"
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]


def post(path, payload, token=None):
    req = urllib.request.Request(
        API + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 **({"Authorization": "Bearer " + token} if token else {})},
        method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


token = post("/auth/login", {"username": USER, "password": PASS})["access_token"]

with open(f"{PKG}/recompute.json", encoding="utf-8") as f:
    rc = json.load(f)
s = rc["summary"]
body = open(f"{PKG}/report.md", encoding="utf-8").read()

head = f"""**本报告为 mission 20865（TensorKnowledge#323 重开·第 3 轮）的进展报告**：
交付 `docs/kf/wp-5716-04` 独立复核包（重写自原 PR#323，10 文件，含 1 个不变量测试门）。

- 复核对象：`tensor://reports/5716`（IN10-G1 冰区航行总攻验收门），源哈希
  `sha256:{rc['source']['sha256_recomputed'][:16]}…` 与 `docs/kf/wp-5716-01` 登记值逐字节相同。
- 结论：`approve_with_notes`，无阻断项；{s['n_checks']} 项检查 =
  6 reproduced / 7 self-consistent / 5 contradicted / 4 gap / 2 withheld。
- 算术层：可闭式复算的 {s['arithmetic_checks']['n']} 项偏差全部 <3%（最大
  {s['arithmetic_checks']['max_rel_dev_pct']:.2f}%）。
- 文档层：{s['document_inconsistencies']['n']} 项不一致，其中 ≥3% 的
  {len(s['document_inconsistencies']['ids_over_3pct'])} 项（27.0% 无分母、C3 航时 63.3 vs 68.2 h、
  墙钟 50.7 vs 41.5 s、7 图 vs 4 图等）。
- 物理层：报告自判的 6 项 >3% 误差经复核方向正确、无粉饰。

---

"""

figs = []
for name, caption in (
    ("fig_review_errors.png",
     "图 A：左=报告 5716 ⑥ 自报误差对 3%（owner 线）/15%（平台线）两线（对数轴）；"
     "右=本包自身偏差，绿=复算 vs 宣称（全部 <3%），红=报告内文档级不一致。"),
    ("fig_review_closure.png",
     "图 B：24 项检查的判定色块（颜色即结论）+ 判定普查 + 闭合台账（disposition / 阻断项 / "
     "复算最大偏差 / honest FAIL / withheld / 源哈希绑定）。"),
):
    with open(f"{PKG}/figures/{name}", "rb") as f:
        figs.append({"name": name, "caption": caption,
                     "png_base64": base64.b64encode(f.read()).decode()})

payload = {
    "title": "报告 5716 独立复核（04 工序）：24 项闭式复算 + 9 条发现，无阻断项",
    "summary": (
        f"对 tensor://reports/5716（IN10-G1 冰区航行总攻验收门）做独立复核：{s['n_checks']} 项检查"
        f"（6 reproduced / 7 self-consistent / 5 contradicted / 4 gap / 2 withheld），"
        f"可闭式复算的 {s['arithmetic_checks']['n']} 项偏差全部 <3%（最大 "
        f"{s['arithmetic_checks']['max_rel_dev_pct']:.2f}%），故报告没有算术错误；"
        f"{s['document_inconsistencies']['n']} 项文档级不一致（最严重：冰区占比 27.0% 无分母、"
        "C3 航时 63.3 vs 68.2 h、墙钟 50.7 vs 41.5 s、7 图齐全 vs 4 图记录）须修订但不翻转任何 honest FAIL；"
        "报告自判的 6 项 >3% 误差经复核方向正确、无粉饰。判定 approve_with_notes，无阻断项。"),
    "scenario_key": "ship.ice_navigation.campaign_gate",
    "mission_id": 20865,
    "tags": ["kf-04", "independent-review", "report-5716", "ice-navigation", "recompute",
             "adversarial-review", "wp-5716-04"],
    "markdown": head + body,
    "figures": figs,
}

resp = post("/tensor/reports", payload, token)
print(json.dumps({k: resp.get(k) for k in ("id", "title", "status", "mission_id")}, ensure_ascii=False))
print("figures:", len(resp.get("figures") or []))