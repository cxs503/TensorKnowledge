#!/usr/bin/env python3
"""把 wp-1538-01 交付报告 POST 到平台（POST /tensor/reports），打印返回报告 id。"""
import json
import os
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
base = os.environ["TENSOR_API_BASE"].rstrip("/")


def call(url, body=None, tok=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=180) as fh:
        return json.load(fh)


t = call(base + "/auth/login", {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]})
t = t.get("data") or t
tok = t.get("access_token") or t.get("token")
payload = json.loads((HERE / "report_payload.json").read_text(encoding="utf-8"))
r = call(base + "/tensor/reports", payload, tok)
r = r.get("data") or r
print("posted report id =", r.get("id"), "| title =", r.get("title"))
Path(HERE / "posted_report_ref.json").write_text(
    json.dumps({"report_id": r.get("id"), "title": r.get("title"), "tags": r.get("tags")}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
