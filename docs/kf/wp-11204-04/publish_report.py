#!/usr/bin/env python3
"""wp-11204-04 · publish the delivery report to the platform (the pipeline's report channel).

Posts `KF-RESULT-wp-11204-04.md` (which contains exactly one ```json block = kf_result.json)
plus the review figure. Credentials come from the environment only; nothing is persisted.

Usage: TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=... python docs/kf/wp-11204-04/publish_report.py
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request
from pathlib import Path

PKG = Path(__file__).resolve().parent
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
MD = PKG / "KF-RESULT-wp-11204-04.md"
FIG = PKG / "figures" / "wp-11204-04_review.png"


def post(path: str, payload: dict, token: str | None = None) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 **({"Authorization": f"Bearer {token}"} if token else {})},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> None:
    token = post("/login", {"username": os.environ["TENSOR_AGENT_USER"],
                            "password": os.environ["TENSOR_AGENT_PASS"]})["access_token"]
    md = MD.read_text(encoding="utf-8")
    assert md.count("```json") == 1
    png = base64.b64encode(FIG.read_bytes()).decode("ascii")
    body = {
        "title": "KF-RESULT wp-11204-04",
        "summary": (
            "报告 11204 独立审核（审核对象 wp-11204-01）：13 项独立检查 10 项通过、3 项报红，"
            "裁决 approve_with_notes（阻断 0）。核心数字可复算——5 项相对误差最大差 0.0028 pp，"
            "扩展 BK 解析列 7/7 复现，δ0/δf=0.009 精确复现，§⑥ 两项 >3% 为 honest-FAIL。"
            "需修：F1 弹性 J/SE(B) J 的评估载荷未声明（反解为 12.0 kN / 2.0 kN，而报告峰值 34 725 N / 7 782 N）；"
            "F2 判据总表 C1/C1b 误差符号反了。运行时断言（pytest 40 项）与图件未执行/未取到，记为 WITHHELD。"
        ),
        "scenario_key": "p273w3-n01-fem-elastoplastic-cohesive",
        "mission_id": 19783,
        "tags": ["KF-RESULT", "kf-wp:wp-11204-04", "04-independent-review", "FEM",
                 "red-team-review", "report:11204"],
        "markdown": md,
        "figures": [{
            "name": "wp-11204-04_review",
            "caption": ("独立复核图：(a) 报告 5 项相对误差的声明值 vs 重算值（最大差 0.0028 pp，"
                        "C1/C1b 符号冲突）；(b) ASTM E399 弹性 J(P) 曲线与报告两个 J 值，"
                        "反解出报告未声明的评估载荷（CT≈12.0 kN、SE(B)≈2.0 kN）。"),
            "png_base64": png,
        }],
    }
    res = post("/tensor/reports", body, token)
    print(json.dumps({k: v for k, v in res.items() if k != "markdown"},
                     ensure_ascii=False)[:1200])


if __name__ == "__main__":
    main()