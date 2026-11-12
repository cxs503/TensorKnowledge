#!/usr/bin/env python3
"""Publish the wp-542-01 report to the platform (title/tags/single json block per delivery contract)."""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOC = REPO / "docs" / "reports" / "kf_wp_542_01_result.md"
BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]


def post(url, payload, token=None):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


tok = post(BASE + "/auth/login", {"username": USER, "password": PASS})
token = tok.get("access_token") or tok.get("token")

md = DOC.read_text(encoding="utf-8")
assert md.count("```json") == 1, "report must carry exactly one json block"
assert md.startswith("# KF-RESULT wp-542-01")

payload = {
    "title": "KF-RESULT wp-542-01",
    "summary": (
        "资产登记工序完成：report 542 源 markdown sha256 与契约一致（a07bad25…9b40，6599 字符），"
        "登记 51 个资产（1 源 + 3 图元数据 + 47 条正文路径引用），每条带行号逐字定位；"
        "claims 按契约留空，未标 verified；7 项验收自检全通过。"
    ),
    "scenario_key": "suboff_icebreaking",
    "mission_id": 15512,
    "tags": ["kf-wp:wp-542-01", "kf-result", "01-asset-registration", "report-542", "FEM", "DEM"],
    "markdown": md,
    "figures": [],
}
resp = post(BASE + "/tensor/reports", payload, token)
print(json.dumps({"id": resp.get("id"), "title": resp.get("title"),
                  "tags": resp.get("tags"), "created_at": resp.get("created_at")},
                 ensure_ascii=False, indent=2))