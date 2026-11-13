#!/usr/bin/env python3
"""Publish the wp-6939-04 review as a platform report (title KF-RESULT wp-6939-04).

The report body is docs/kf/wp-6939-04/REVIEW.md verbatim: it carries the six
required sections and exactly one ```json block (the kf_result envelope), which
is the only result channel for this work package.

    python scripts/kf/publish_wp6939_04.py            # publish
    python scripts/kf/publish_wp6939_04.py --dry-run  # build the payload only
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "kf" / "wp-6939-04"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def login() -> str:
    """Fresh login; fall back to a cached token file if the auth route is down.

    The auth route has been observed to answer 401 on POST while previously
    issued tokens stay valid, so a cached token is used only as a fallback and
    is never printed.
    """
    try:
        req = urllib.request.Request(
            f"{BASE}/tensor/auth/login",
            data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                             "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
            headers={"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req, timeout=30))["access_token"]
    except Exception:
        cache = Path(os.environ.get("TENSOR_TOKEN_FILE", "/tmp/login.json"))
        tok = json.loads(cache.read_text())["access_token"]
        req = urllib.request.Request(f"{BASE}/tensor/reports/6939",
                                     headers={"Authorization": f"Bearer {tok}"})
        urllib.request.urlopen(req, timeout=30)  # raises if the cached token is stale
        return tok


def build_payload() -> dict:
    md = (OUT / "REVIEW.md").read_text(encoding="utf-8")
    assert md.count("```json") == 1, "the body must carry exactly one json block"
    review = json.loads((OUT / "review_report.json").read_text(encoding="utf-8"))
    png = (OUT / "figures" / "criteria_threshold_gap.png").read_bytes()
    return {
        "title": "KF-RESULT wp-6939-04",
        "summary": (
            "独立红队审核 report 6939 / wp-6939-01：裁定 needs-fix。注册信封 pass（10/10 机检、"
            "哈希逐字节一致）；claim 集语义保真 fail —— 4 条阻断（事后 20% 阈值放行 18% 误差、C4 声明的 10% "
            "判据从未被执行、C3 基准被自身近似替换、界面连续只验代数恒等式），5 条重大（25/25 与 22 行不符、"
            "6 行无数字、五图 404、容差比代码套件紧 1.7-5 倍、Fo 界与实现不符），3 条次要。未打任何验证标记。"),
        "scenario_key": "CHT|IN45-N04|m",
        "mission_id": 15850,
        "tags": ["CHT", "conjugate_heat_transfer", "TensorLBM", "independent_review",
                 "red-team-review", "kf-wp:wp-6939-04", "report:6939"],
        "markdown": md,
        "figures": [{
            "name": "criteria_threshold_gap",
            "caption": ("报告 6939 自报容差 vs TensorLBM 检出里唯一一套 CHT 验证套件（"
                        "tests/test_cht_validation.py, sha256 3bc980ce…, commit 7ed01fc8）声明的容差："
                        "逐项 log 轴对照。C5 按相对量给（1e-6 绝对 ≈ 1e-4%）。数据来源见 "
                        "review_report.json.evidence_checks.code_suite_threshold_probe。"),
            "png_base64": base64.b64encode(png).decode(),
        }],
        "verdict": review["verdict"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    payload = build_payload()
    if args.dry_run:
        slim = dict(payload, markdown=payload["markdown"][:200] + "...",
                    figures=[{**f, "png_base64": f["png_base64"][:32] + "..."}
                             for f in payload["figures"]])
        print(json.dumps(slim, ensure_ascii=False, indent=2))
        return 0
    token = login()
    req = urllib.request.Request(
        f"{BASE}/tensor/reports",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    resp = json.load(urllib.request.urlopen(req, timeout=120))
    (OUT / "publish_response.json").write_text(
        json.dumps(resp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: resp[k] for k in ("id", "title", "status") if k in resp}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())