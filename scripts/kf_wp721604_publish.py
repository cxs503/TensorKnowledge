#!/usr/bin/env python3
"""Publish the wp-7216-04 review report to the platform (paper-grade report discipline).

    python3 scripts/kf_wp721604_publish.py [--dry-run]

Body = docs/kf/wp-7216-04/KF-RESULT-wp-7216-04.md (the same bytes committed to the
worktree, one ```json block).  One figure is attached as base64 PNG.
Credentials come from the environment only.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
MD = REPO / "docs/kf/wp-7216-04/KF-RESULT-wp-7216-04.md"
FIG = REPO / "figures/wp-7216-04/review_map.png"
PP = "wp-7216-04"


def login() -> str:
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())["access_token"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    markdown = MD.read_text(encoding="utf-8")
    body = {
        "title": "KF-RESULT %s" % PP,
        "summary": ("独立红队审核 wp-7216-01（report 7216）：37 条规则全部在本次运行内从活原文重算，"
                    "0 失败；源哈希与契约逐字一致，40/40 定位符逐字可复现，4 条非阻塞观察"
                    "（调用式 token、document 定位符互操作、occurrence_lines 语义、39/40 "
                    "referenced_unresolved）。verdict=pass，未标 verified。"),
        "scenario_key": "knowledge-factory/independent-review",
        "mission_id": 15851,
        "tags": ["kf-wp:%s" % PP, "TensorKnowledge", "independent-review", "red-team-reviewer",
                 "wp-7216-01", "report-7216", "TensorLBM", "IN31-N12"],
        "markdown": markdown,
        "figures": [{"name": FIG.name,
                     "caption": ("上：审核规则族通过/失败（37 条规则，0 失败）。下：被审登记包 40 条资产"
                                 "定位符在报告原文上的字符跨度（虚线=章节边界）；跨仓引用多为点状窄跨度，"
                                 "段落级跨度集中在审计链 §6。"),
                     "png_base64": base64.b64encode(FIG.read_bytes()).decode()}],
    }
    if args.dry_run:
        print(json.dumps({"bytes": len(markdown), "figures": len(body["figures"]),
                          "markdown_sha256": "sha256:" + hashlib.sha256(
                              markdown.encode()).hexdigest()}, ensure_ascii=False))
        return 0
    token = login()
    req = urllib.request.Request(BASE + "/tensor/reports", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + token}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        out = json.loads(r.read().decode())
    print(json.dumps({"published_report_id": out.get("id"), "status": out.get("status"),
                      "title": out.get("title"),
                      "markdown_sha256": "sha256:" + hashlib.sha256(
                          markdown.encode()).hexdigest()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())