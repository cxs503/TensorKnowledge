#!/usr/bin/env python3
"""Publish the wp-11204-01 delivery report to TensorPlatform and verify it round-trips.

Body = docs/kf/wp-11204-01/KF-RESULT-wp-11204-01.md (contains exactly one fenced json
block = the work-package result). After POSTing, re-GET the created report and assert:
  * exactly one ```json block, parses, package_id/provenance.source_hash correct
  * the provenance hash still equals sha256(report 11204 markdown) recomputed live
  * the stored markdown is byte-identical to the local file
Prints the new report id.
"""
import base64
import hashlib
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "docs", "kf", "wp-11204-01")
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
CONTRACT_HASH = "d22a30cc692b82f2acf6ea669fd898a330143436344e4091c4a39c06a5292f86"
TITLE = "KF-RESULT wp-11204-01"


def login():
    req = urllib.request.Request(
        API + "/auth/login",
        data=json.dumps({"username": os.environ.get("TENSOR_AGENT_USER", ""),
                         "password": os.environ.get("TENSOR_AGENT_PASS", "")}).encode(),
        method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    return d.get("access_token") or d.get("token")


def main():
    tok = login()
    md = open(os.path.join(OUT, "KF-RESULT-wp-11204-01.md"), encoding="utf-8").read()
    png = open(os.path.join(OUT, "fig_asset_resolution.png"), "rb").read()
    body = {
        "title": TITLE,
        "summary": "wp-11204-01 资产登记：report 11204 源哈希与契约逐字节一致（sha256:d22a30cc…，5999 字符）；"
                   "登记 27 项资产（resolved_in_source 6 / referenced_unresolved 21 / declared_absent 0），"
                   "并首次证实该平台的记录图字节可解析（/figures/<name> 无扩展名 200，.png 404），3 张图 sha256 两次抓取一致；"
                   "自检 10 项 acceptance+不变量全 PASS；claims=[]（未抽取、未标 verified）。"
                   "rev3 为最终版：产出清单中的测试条数与局限条数改为程序化注入（rev1=14793、rev2=14795 由本版取代），JSON 结果块与 27 项资产登记内容不变。",
        "scenario_key": "p273w3-n01-fem-elastoplastic-cohesive",
        "mission_id": 15693,
        "tags": ["kf-wp:wp-11204-01", "kf-result", "01-asset-registration", "lane-C",
                 "FEM", "cohesive", "TensorPhysics"],
        "markdown": md,
        "figures": [{
            "name": "fig_asset_resolution",
            "caption": "wp-11204-01 asset inventory by class/resolution (left) and measured reachability of the five evidence channels (right)",
            "png_base64": base64.b64encode(png).decode(),
        }],
    }
    req = urllib.request.Request(API + "/tensor/reports",
                                 data=json.dumps(body, ensure_ascii=False).encode(),
                                 method="POST")
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=180) as r:
        created = json.loads(r.read().decode())
    rid = created.get("id") or (created.get("data") or {}).get("id")
    print("published report id:", rid)

    # round-trip verification against the server copy
    req2 = urllib.request.Request(API + "/tensor/reports/%s" % rid, method="GET")
    req2.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req2, timeout=60) as r:
        got = json.loads(r.read().decode())
    stored = got["markdown"]
    blocks = re.findall(r"```json\n(.*?)\n```", stored, re.S)
    assert len(blocks) == 1, "server copy must keep exactly one json block, got %d" % len(blocks)
    payload = json.loads(blocks[0])
    assert payload["package_id"] == "wp-11204-01"
    assert payload["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert stored == md, "server copy differs from local markdown"
    req3 = urllib.request.Request(API + "/tensor/reports/11204", method="GET")
    req3.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req3, timeout=60) as r:
        src = json.loads(r.read().decode())["markdown"]
    assert hashlib.sha256(src.encode("utf-8")).hexdigest() == CONTRACT_HASH
    out = {"published_report_id": rid, "title": got.get("title"), "tags": got.get("tags"),
           "mission_id": got.get("mission_id"), "markdown_chars": len(stored),
           "json_blocks": len(blocks), "figures": [f.get("name") for f in (got.get("figures") or [])],
           "provenance_hash_verified_against_source": True}
    json.dump(out, open(os.path.join(OUT, "publish_check.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())