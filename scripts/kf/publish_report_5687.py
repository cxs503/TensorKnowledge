#!/usr/bin/env python3
"""Publish the wp-5687-01 report to the platform (title/tags/single json block per delivery contract)."""
import json
import os
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOC = REPO / "docs" / "reports" / "kf_wp_5687_01_result.md"
RESULT = REPO / "docs" / "kf" / "wp-5687-01" / "kf_result.json"
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

tpl = DOC.read_text(encoding="utf-8")
assert "@@KF_RESULT_JSON@@" in tpl, "template missing placeholder"
result_json = RESULT.read_text(encoding="utf-8").rstrip("\n")
json.loads(result_json)  # must be valid json before embedding
md = tpl.replace("@@KF_RESULT_JSON@@", "```json\n" + result_json + "\n```")
assert md.count("```json") == 1, "report must carry exactly one json block"
assert md.startswith("# KF-RESULT wp-5687-01")
# the embedded block must be byte-identical to kf_result.json
embedded = md.split("```json\n", 1)[1].rsplit("\n```", 1)[0]
assert embedded == result_json, "embedded block drifted from kf_result.json"

payload = {
    "title": "KF-RESULT wp-5687-01",
    "summary": (
        "资产登记工序完成：report 5687 源 markdown sha256 与契约一致（a4eaa764…feb3d，4236 字符/6382 字节），"
        "登记 11 个资产（1 源 resolved + 3 图 metadata_only + 7 条正文路径引用 unresolved），每条带行号逐字定位；"
        "claims 按契约留空，未标 verified；6 项验收自检全通过。"
    ),
    "scenario_key": "chronicle-metrics-in18-t2",
    "mission_id": 15574,
    "tags": ["kf-wp:wp-5687-01", "kf-result", "01-asset-registration", "report-5687", "IN18-T2", "chronicle"],
    "markdown": md,
    "figures": [],
}
resp = post(BASE + "/tensor/reports", payload, token)
print(json.dumps({"id": resp.get("id"), "title": resp.get("title"),
                  "tags": resp.get("tags"), "created_at": resp.get("created_at")},
               ensure_ascii=False, indent=2))
