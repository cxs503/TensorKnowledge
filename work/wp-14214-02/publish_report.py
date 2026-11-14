#!/usr/bin/env python3
"""Publish the wp-14214-02 delivery report to the platform (POST /api/v1/tensor/reports).

The delivery channel of a KF work package is a report whose markdown carries exactly one
JSON block = `work/wp-14214-02/kf_result.json`. This script publishes that report with the
diagnostic figure embedded as png_base64. It never writes to report 14214 itself.

Credentials are read from TENSOR_AGENT_USER / TENSOR_AGENT_PASS and never printed.

Run: python3 work/wp-14214-02/publish_report.py
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

WP = Path(__file__).resolve().parent
REPO = WP.parents[1]
MD = REPO / "docs" / "kf_result_wp-14214-02.md"
PNG = WP / "figures" / "wp14214_02_signal_profile.png"
RECEIPT = WP / "publish_receipt.json"
SUPERSEDES = os.environ.get("SUPERSEDES_REPORT_ID", "").strip()

TITLE = "KF-RESULT wp-14214-02"
SCENARIO_KEY = "paper-line-w23"
MISSION_ID = 19805
TAGS = [
    "kf-wp:wp-14214-02",
    "02-classification-parse",
    "report-14214",
    "lane-B",
    "TensorKnowledge",
    "draft",
]


def main() -> int:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    markdown = MD.read_text(encoding="utf-8")
    if markdown.count("```json") != 1:
        print(f"refusing to publish: {markdown.count('```json')} json blocks (must be exactly 1)",
              file=sys.stderr)
        return 1
    figures = []
    if PNG.exists():
        figures.append({
            "name": PNG.name,
            "caption": "图1 report 14214 六分型信号命中剖面（左，registry 英文信号 vs 本地中文代理）"
                       "与 level-2 节长度剖面（右）；由 work/wp-14214-02/wp_14214_02_classify.py 生成",
            "png_base64": base64.b64encode(PNG.read_bytes()).decode(),
        })
    payload = {
        "title": TITLE,
        "summary": "report 14214 分类解析（工序 02）：sha256 恒等核通过，结构切分 8 节/4 表/5 图，"
                   "六分型机械打分判定 technical-proposal（confidence=medium，唯一 registry 命中 "
                   "`plan`×18 中仅 4 次独立出现），20 条逐字 locator 全部可解析，claims=[]、3 项 unresolved 挂账、无 verified。",
        "scenario_key": SCENARIO_KEY,
        "mission_id": MISSION_ID,
        "tags": TAGS,
        "markdown": markdown,
        "figures": figures,
    }

    def post(url: str, body: dict, token: str | None = None) -> dict:
        req = urllib.request.Request(url, method="POST", data=json.dumps(body).encode())
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", "Bearer " + token)
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())

    login = post(base + "/auth/login", {
        "username": os.environ["TENSOR_AGENT_USER"],
        "password": os.environ["TENSOR_AGENT_PASS"],
    })
    token = login.get("access_token") or login.get("token")
    created = post(base + "/tensor/reports", payload, token)
    rec = created.get("data", created)
    receipt = {
        "title": TITLE,
        "report_id": rec.get("id"),
        "status": rec.get("status"),
        "scenario_key": SCENARIO_KEY,
        "mission_id": MISSION_ID,
        "markdown_chars": len(markdown),
        "json_blocks": markdown.count("```json"),
        "figures": [f["name"] for f in figures],
        "tags": TAGS,
        "supersedes_report_ids": [int(x) for x in SUPERSEDES.split(",") if x.strip().isdigit()] or None,
        "response_keys": sorted(rec.keys()),
    }
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())