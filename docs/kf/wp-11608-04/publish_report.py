#!/usr/bin/env python3
"""wp-11608-04: publish the reviewer report to the platform (mission 19821).

Builds /tmp/report_wp11608_04.json (title/summary/scenario_key/mission_id/tags/markdown/
figures[png_base64]) from the staged deliverables and POSTs it with the agent token.

Usage:
  python3 runs/wp-11608-04/publish_report.py [--dry-run]
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = "wp-11608-04"
DOCS = ROOT / "docs" / "kf" / PKG
FIG_CAPTIONS = {
    "fig1_upwind_deviation.png": "判据(a)：9 组迎风工况，报告误差列 vs 独立重算（对数轴，左）与偏差符号（右）；"
    "3 组 C=0.5 的偏差符号与精确 von Neumann 相反",
    "fig2_criterion_power.png": "判据(b)：0.1% 系数误差的 mutant 完全落在报告 ±1e-3 阈值带内（左），"
    "而独立 march 与闭式的可达一致度是 1e-15 量级、比报告表格残差低 11 个量级（右）",
    "fig3_quick_and_lw.png": "QUICK 前阶黏性：报告公式 (1-C)(1-C²)/8 与其自身符号的极限相差 5.5–25 倍，"
    "自推 (5-4C)/8 吻合到 1e-4（左）；L–W 残差黏性报告为 O(θ)、理论为 O(θ²)（右）",
    "fig4_cd2_and_grid.png": "CD2 半周期增长逐工况 vs 报告区间 1.15–1.35（7/9 低于下界，左）；"
    "网格收敛独立复现，比值 0.4994–0.5000（右）",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    md = (DOCS / f"KF-RESULT-{PKG}.md").read_text(encoding="utf-8")
    review = json.loads((DOCS / "review_report.json").read_text(encoding="utf-8"))
    figures = []
    for name, caption in FIG_CAPTIONS.items():
        raw = (DOCS / name).read_bytes()
        figures.append(
            {
                "name": name,
                "caption": caption,
                "png_base64": base64.b64encode(raw).decode("ascii"),
            }
        )
    summary = (
        "对 report 11608（TensorFVM 数值黏性/色散验证面）的独立红队审核：自实现四格式重算 6 块判据。"
        f"四条物理结论成立；但 3/6 判据表逐行数字不可复现（精确偏差小 1.7–124 倍，3 行反号）、"
        f"QUICK 前阶黏性公式被证伪（(1-C)(1-C²)/8 应为 (5-4C)/8，且大于迎风）、"
        f"CD2 增长区间仅 2/9 工况成立。disposition = {review['disposition']['verdict']}，"
        "未标任何 verified。"
    )
    payload = {
        "title": f"KF-RESULT {PKG}",
        "summary": summary,
        "scenario_key": "p73w3-n04-fvm-numerical-viscosity",
        "mission_id": 19821,
        "tags": [
            f"kf-wp:{PKG}",
            "KF-RESULT",
            "FVM",
            "numerical-viscosity",
            "independent-review",
            "red-team",
            "report-11608",
            "needs-fix",
        ],
        "markdown": md,
        "figures": figures,
    }
    tmp = Path("/tmp/report_wp11608_04.json")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"built {tmp} ({tmp.stat().st_size / 1024:.0f} KB, {len(figures)} figures)")
    if args.dry_run:
        return 0

    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps(
            {
                "username": os.environ["TENSOR_AGENT_USER"],
                "password": os.environ["TENSOR_AGENT_PASS"],
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    tok = json.load(urllib.request.urlopen(req, timeout=30))["access_token"]
    req = urllib.request.Request(
        base + "/tensor/reports",
        data=tmp.read_bytes(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok},
    )
    resp = json.load(urllib.request.urlopen(req, timeout=120))
    print(json.dumps({k: resp[k] for k in ("id", "title", "status") if k in resp}, ensure_ascii=False))
    receipt = {
        "report_id": resp.get("id"),
        "title": resp.get("title"),
        "status": resp.get("status"),
        "scenario_key": payload["scenario_key"],
        "mission_id": payload["mission_id"],
        "tags": payload["tags"],
        "figures": list(FIG_CAPTIONS),
        "note": "publish receipt only (no auth material retained)",
    }
    (DOCS / "publish.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("wrote publish receipt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())