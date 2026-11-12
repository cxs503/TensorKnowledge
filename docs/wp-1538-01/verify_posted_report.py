#!/usr/bin/env python3
"""回读已发布报告，自检交付面：标题/tags/json 块唯一性/信封可解析/source_hash 指向 1538。"""
import json
import os
import re
import urllib.request

base = os.environ["TENSOR_API_BASE"].rstrip("/")


def call(url, body=None, tok=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=120) as fh:
        return json.load(fh)


t = call(base + "/auth/login", {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]})
t = t.get("data") or t
tok = t.get("access_token") or t.get("token")
rid = json.load(open("artifacts/wp-1538-01/posted_report_ref.json"))["report_id"]
r = call(f"{base}/tensor/reports/{rid}", tok=tok)
r = r.get("data") or r
md = r["markdown"]
blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
env = json.loads(blocks[0]) if blocks else {}
print("report_id      :", r.get("id"))
print("title          :", r.get("title"))
print("mission_id     :", r.get("mission_id"))
print("tags           :", r.get("tags"))
print("markdown chars :", len(md))
print("json blocks    :", md.count("```json"))
print("envelope keys  :", sorted(env))
print("package_id     :", env.get("package_id"))
print("report_id(env) :", env.get("report_id"))
print("source_hash    :", env.get("provenance", {}).get("source_hash"))
print("claims         :", env.get("claims"))
print("outputs keys   :", list(env.get("outputs", {})))
assert r.get("title") == "KF-RESULT wp-1538-01"
assert "kf-wp:wp-1538-01" in (r.get("tags") or [])
assert md.count("```json") == 1
assert env["package_id"] == "wp-1538-01" and env["report_id"] == "1538" and env["task_type"] == "01-asset-registration"
assert env["provenance"]["source_hash"].endswith("9d7f968e4c888872eba25bfc190c3e6415e5c7a8f0f4b2733e665181e0d17c85")
assert env["outputs"]["asset_manifest.json"]["report"]["hash_match"] is True
print("SELF-CHECK OK")
