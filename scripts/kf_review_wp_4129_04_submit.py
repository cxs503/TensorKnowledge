#!/usr/bin/env python3
"""wp-4129-04: submit the KF result through the only result channel.

Publishes a report titled `KF-RESULT wp-4129-04` whose markdown is the delivered
`docs/kf/wp-4129-04.md` (six sections + exactly one ```json block, the kf_result envelope),
then reads the report back and re-checks that:
  * the json block parses and equals work/wp-4129-04/kf_result.json
  * provenance.source_hash equals sha256 of report 4129's markdown bytes
  * the tag `kf-wp:wp-4129-04` is present
"""
import base64
import hashlib
import json
import os
import pathlib
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]
WT = pathlib.Path(".")
DOC = WT / "docs/kf/wp-4129-04.md"
ENV = json.loads((WT / "work/wp-4129-04/kf_result.json").read_text(encoding="utf-8"))
PNG = (WT / "docs/kf/figures/wp-4129-04.png").read_bytes()
DOC_MD = DOC.read_text(encoding="utf-8")
SRC = (WT / "work/wp-4129-04/source/report_4129.md").read_bytes()


def call(path, body=None, token=None, method=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json"},
                                 method=method or ("POST" if data else "GET"))
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def unwrap(res):
    return res.get("data", res) if isinstance(res, dict) else res


def main(argv):
    token = (call("/auth/login", {"username": USER, "password": PASS}) or {}).get("access_token")
    assert token
    if len(argv) > 1 and argv[1] == "--verify-only":
        rid = int(argv[2])
        return verify(rid, token)
    payload = {
        "title": "KF-RESULT wp-4129-04",
        "summary": "独立审核 report 4129 / wp-4129-01：32/34 项机器复算通过，注册事实零矛盾，"
                   "查出 2 处登记精度缺陷（符号引文行号错位、引用站点少登记 1 条），verdict=needs-fix（不阻塞）。",
        "scenario_key": "benchmark-closure",
        "mission_id": 15827,
        "tags": ["kf-wp:wp-4129-04", "kf", "independent-review", "red-team", "report-4129", "wp-4129-01"],
        "markdown": DOC_MD,
        "figures": [{"name": "wp-4129-04.png",
                     "caption": "wp-4129-04 审核证据三面板：复算检查通过面 / 引用计数缺口 / 引文逐字率",
                     "png_base64": base64.b64encode(PNG).decode()}],
    }
    res = call("/tensor/reports", payload, token)
    rid = (unwrap(res) or {}).get("id")
    print("published report_id:", rid)
    return verify(rid, token)


def verify(rid, token):
    back = unwrap(call(f"/tensor/reports/{rid}", token=token))
    md = back.get("markdown", "")
    blocks = md.split("```json")
    assert len(blocks) == 2, f"expected exactly one json block, got {len(blocks) - 1}"
    env = json.loads(blocks[1].split("```")[0])
    same = env == ENV
    declared = env["provenance"]["source_hash"]
    live = "sha256:" + hashlib.sha256(SRC).hexdigest()
    print("readback title:", back.get("title"))
    print("json block == kf_result.json:", same)
    print("json block == delivered docs file:", env == json.loads(
        DOC.read_text(encoding="utf-8").split("```json")[1].split("```")[0]))
    print("source_hash match (live report 4129 bytes):", declared == live, declared)
    print("tag present:", "kf-wp:wp-4129-04" in (back.get("tags") or []))
    out = {"report_id": rid, "title": back.get("title"), "json_block_matches": same,
           "source_hash": declared, "source_hash_matches_live": declared == live,
           "tags": back.get("tags"), "status": back.get("status")}
    (WT / "work/wp-4129-04/kf_submit.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                                       encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))
    assert same and declared == live and "kf-wp:wp-4129-04" in (back.get("tags") or [])


if __name__ == "__main__":
    import sys

    main(sys.argv)