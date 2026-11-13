#!/usr/bin/env python3
"""Build and POST the wp-5716-04 platform report (the progress-report channel).

Title/tags/scenario are taken from the work-package contract; the markdown is the
assembled report (docs/kf/wp-5716-04/report.md) verbatim, so the single ```json
block inside it is exactly docs/kf/wp-5716-04/kf_result.json. Figures are inlined
as base64 from docs/kf/wp-5716-04/figures.

Usage: python3 scripts/kf/publish_wp_5716_04.py [--dry-run]
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys

PKG = "wp-5716-04"
TITLE = f"KF-RESULT {PKG}"
SCENARIO = "ship.ice_navigation.campaign_gate"
MISSION = 15839
MD = "docs/kf/wp-5716-04/report.md"
ENV = "docs/kf/wp-5716-04/kf_result.json"
FIG = "docs/kf/wp-5716-04/figures"
PAYLOAD = "runs/wp-5716-04/report_payload.json"

FIGS = [
    ("fig_review_errors.png",
     "图1 · 审核侧重算：报告 ⑥ 表 10 个百分比项 vs 3% 验收线与 25% 预登记筛选线（对数轴）。"
     "数值由 markdown 直接解析（零手抄），红色=报告自认不达 3%，绿色=通过。"),
    ("fig_review_closure.png",
     "图2 · 时间/速度一阶闭合反演：由报告自身总量（684.1 nm、冰区 27.0%、开阔水 13 kn）"
     "反演冰段平均速度 D1=11.48 kn、C3=7.42/6.20 kn，对照报出的 4.50 kn 设计点——"
     "16 项断言中无一闭合此项，登记为门覆盖缺口 F3。"),
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    md = open(MD, encoding="utf-8").read()
    env = json.load(open(ENV, encoding="utf-8"))
    blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
    if len(blocks) != 1 or json.loads(blocks[0]) != env:
        raise SystemExit("refusing to publish: report body json block != %s" % ENV)
    figs = []
    for name, cap in FIGS:
        p = os.path.join(FIG, name)
        figs.append({"name": name, "caption": cap,
                     "png_base64": base64.b64encode(open(p, "rb").read()).decode()})
    payload = {
        "title": TITLE,
        "summary": ("wp-5716-04 独立红队审核（对象 wp-5716-01，report 5716，源哈希 "
                    "4f9848b2 逐字相符）。findings 10 条（3 high/3 medium/4 low，阻断 2），"
                    "disposition=needs-fix：报告内同一物理量双值（C3 总时长 63.3 h vs 68.2 h）、"
                    "声称 7 项披露但仅 4 个 ID 可定位；另有 7 项 reviewer 独立复算被证实自洽"
                    "（Cb 补 ρ=1.025 后 0.820075 复现、B2 β 修正 12.4 在 m=3 精确复现、D07 65.6% 自洽）。"
                    "upstream_packages_completed 因平台无包注册端点标 UNKNOWN 不冒充 PASS；"
                    "未宣称任何 verified。"),
        "scenario_key": SCENARIO,
        "mission_id": MISSION,
        "tags": ["KF-RESULT", "kf-wp:" + PKG, "IN10-G1", "independent-review",
                 "red-team", "needs-fix", "ice-navigation", "campaign-gate"],
        "markdown": md,
        "figures": figs,
    }
    os.makedirs(os.path.dirname(PAYLOAD), exist_ok=True)
    with open(PAYLOAD, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    print("payload", PAYLOAD, "md_bytes", len(md.encode()), "figs", len(figs),
          "json_block_in_body", "```json" in md)
    if a.dry_run:
        print("dry-run: not posting")
        return 0
    r = subprocess.run([sys.executable, "scripts/kf/post_report.py", PAYLOAD])
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())