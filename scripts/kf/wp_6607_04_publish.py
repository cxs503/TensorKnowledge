#!/usr/bin/env python3
"""Publish the wp-6607-04 review report to the platform (single result channel).

Title/tags are pinned by the work package: title == 'KF-RESULT wp-6607-04',
tags contain 'kf-wp:wp-6607-04'.  The markdown body carries exactly one ```json
block (the kf_result envelope) — verified before POST.

Usage: python3 scripts/kf/wp_6607_04_publish.py [--dry-run]
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
USER, PASS = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]
PKG = "wp-6607-04"
REPO = pathlib.Path(__file__).resolve().parents[2]
DOCS = REPO / "docs" / "kf" / PKG


def call(path, body=None, token=None):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = "Bearer " + token
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode() if body else None, headers=h)
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def main() -> int:
    dry = "--dry-run" in sys.argv
    body = (DOCS / "report_markdown.md").read_text(encoding="utf-8")
    env = json.loads((DOCS / "kf_result.json").read_text(encoding="utf-8"))
    blocks = re.findall(r"```json\s*\n(.*?)```", body, flags=re.S)
    assert len(blocks) == 1, f"exactly one json block required, got {len(blocks)}"
    assert json.loads(blocks[0]) == env, "json block must equal kf_result.json"
    assert body.startswith(f"# KF-RESULT {PKG}")

    png = (DOCS / "figures" / f"{PKG}.png").read_bytes()
    payload = {
        "title": f"KF-RESULT {PKG}",
        "summary": (
            "独立审核 wp-6607-01（report 6607 资产登记包）：独立取源重算 34 条检查，33 通过；"
            "9 个定位器全部逐字复现（char_span/行号/唯一性/章节归属），无一条被证伪；"
            "查出 2 条登记缺陷（漏登记 1 条被引模块路径、计数口径未声明），均不阻塞，"
            "verdict=needs-fix（不阻塞）。不做物理验证，不标 verified。"),
        "scenario_key": "dem-granular-jamming",
        "mission_id": 15849,
        "tags": [f"kf-wp:{PKG}", "independent-review", "red-team", "report-6607",
                 "wp-6607-01", "TensorKnowledge"],
        "markdown": body,
        "figures": [{
            "name": f"{PKG}.png",
            "caption": "wp-6607-04 审核证据：34 条复算检查按检查面分组的通过/失败；"
                       "登记资产 9 vs 普查被引路径 10（缺口=src/tensordem/granular2d/minimizer.py）；"
                       "9 个定位器的 5 面保真全部通过",
            "png_base64": base64.b64encode(png).decode(),
        }],
    }
    print("title:", payload["title"], "| markdown chars:", len(body),
          "| figure bytes:", len(png))
    if dry:
        print("dry run — not posted")
        return 0
    token = call("/auth/login", {"username": USER, "password": PASS})["access_token"]
    rep = call("/tensor/reports", payload, token=token)
    data = rep.get("data", rep)
    print("posted id:", data.get("id"), "title:", data.get("title"),
          "status:", data.get("status"), "tags:", data.get("tags"))
    receipt = {k: data.get(k) for k in ("id", "title", "status", "scenario_key",
                                        "mission_id", "tags", "created_at")}
    receipt["markdown_sha256"] = "sha256:" + hashlib.sha256(
        (data.get("markdown") or body).encode("utf-8")).hexdigest()
    receipt["figure_names"] = [f.get("name") for f in (data.get("figures") or [])]
    receipt["note"] = "slim receipt (body/figures omitted to keep the repo lean)"
    (DOCS / "published.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())