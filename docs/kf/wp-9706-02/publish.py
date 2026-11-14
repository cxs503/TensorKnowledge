#!/usr/bin/env python3
"""Publish the wp-9706-02 result as a platform report.

The report body published here is exactly `KF-RESULT-wp-9706-02.md`, i.e. it
carries the single ```json result block. Figures are attached as base64 PNG.

Credentials come from the environment (``TENSOR_API_BASE``, ``TENSOR_AGENT_USER``,
``TENSOR_AGENT_PASS``); nothing is hard-coded and no token is written to disk.

Usage: python docs/kf/wp-9706-02/publish.py [--dry-run]
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

PKG = Path(__file__).resolve().parent
TITLE = "KF-RESULT wp-9706-02"
TAGS = [
    "kf-wp:wp-9706-02",
    "kf-wp",
    "kf-process:02-classification-parse",
    "report:9706",
    "scenario:dp_capability",
]
SUMMARY = (
    "报告 9706（IN145-N04 DP 能力评估）已完成工序 02 分类解析：判定 experimental-validation（置信度 "
    "medium，可反驳假设，次选 scientific-computation），选中 xsk-experimental-validation；"
    "给出 10 段结构切分与 45 条逐字原文定位（哈希重算一致），8 条判定 claim 全带 locator，"
    "4 条不一致/不可核验事项如实登记为 unresolved，未标 verified。"
)
FIGURES = [
    ("structure_segments.png", "报告 9706 结构切分：各 H2 章节字符区间长度（偏移以同一 markdown 串为基准）。"),
    ("signal_coverage.png", "六分型 identify_signals 覆盖：绿=人工判读，红=registry 英文字面扫描命中数（全 0）。"),
]


def _post(url: str, payload: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def login(base: str) -> str:
    out = _post(f"{base}/auth/login",
                {"username": os.environ["TENSOR_AGENT_USER"],
                 "password": os.environ["TENSOR_AGENT_PASS"]})
    return out["access_token"]


def main() -> int:
    dry = "--dry-run" in sys.argv
    markdown = (PKG / "KF-RESULT-wp-9706-02.md").read_text(encoding="utf-8")
    assert markdown.count("```json") == 1, "report must carry exactly one json block"

    figures = []
    for name, caption in FIGURES:
        png = PKG / "figures" / name
        figures.append({"name": name, "caption": caption,
                        "png_base64": base64.b64encode(png.read_bytes()).decode("ascii")})

    payload = {
        "title": TITLE,
        "summary": SUMMARY,
        "scenario_key": "dp_capability",
        "mission_id": 19803,
        "tags": TAGS,
        "markdown": markdown,
        "figures": figures,
    }
    if dry:
        print(json.dumps({k: (v if k != "markdown" else f"<{len(v)} chars>") for k, v in payload.items()
                          if k != "figures"}, ensure_ascii=False, indent=2))
        print(f"figures: {[f['name'] for f in figures]}")
        return 0

    base = os.environ["TENSOR_API_BASE"]
    token = login(base)
    out = _post(f"{base}/tensor/reports", payload, token)
    print(json.dumps({k: out.get(k) for k in ("id", "title", "status", "stage", "created_at")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())