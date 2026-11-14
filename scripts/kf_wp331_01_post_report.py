#!/usr/bin/env python3
"""把 wp-331-01 的交付报告作为 KF-RESULT 发到平台报告面。

标题 = `KF-RESULT wp-331-01`；tags 含 `kf-wp:wp-331-01`（结果信道）；markdown 取自
工作树内的报告文件（其中含唯一 ```json 结果块）。发完后回读该报告，验证
标题/tag/结果块与工作树一致——发出去的东西不是"应该对"，而是被读回来核对过。

用法：
  python3 scripts/kf_wp331_01_post_report.py --md docs/kf/wp-331-01-asset-registration.md
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request
from pathlib import Path

PACKAGE_ID = "wp-331-01"
REPORT_ID = "331"
TITLE = f"KF-RESULT {PACKAGE_ID}"
TAG = f"kf-wp:{PACKAGE_ID}"
MISSION_ID = 19471
_JSON_BLOCK = re.compile(r"```json\s*\n(.*?)```", re.S)


def _call(base, path, body=None, token=None, method=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(base + path, data=data, headers=headers,
                                method=method or ("POST" if data else "GET"))
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default="docs/kf/wp-331-01-asset-registration.md")
    a = ap.parse_args(argv)

    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    tok = _call(base, "/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                      "password": os.environ["TENSOR_AGENT_PASS"]})
    token = tok.get("access_token") or tok.get("token")

    md = Path(a.md).read_text(encoding="utf-8")
    blocks = _JSON_BLOCK.findall(md)
    if len(blocks) != 1:
        raise SystemExit(f"report md must carry exactly one json block, got {len(blocks)}")
    payload = json.loads(blocks[0])

    summary = (f"工序 01 资产登记：report {REPORT_ID} markdown 逐字节哈希对齐"
               f"（{payload['provenance']['source_hash']}），登记 4 个资产"
               "（2 resolved / 1 declared_unresolvable / 1 unresolved_candidate_found），"
               "claims 空（不做抽取）；平台门代码干跑 9/9 PASS。")

    created = _call(base, "/tensor/reports", {
        "title": TITLE,
        "summary": summary,
        "scenario_key": "dem_fem_coupling_hertz_cpu",
        "mission_id": MISSION_ID,
        "tags": [TAG, "kf", "asset-registration", "report-331", "lane-C"],
        "markdown": md,
        "figures": [],
    }, token)
    rid = created.get("id") or created.get("report_id")
    print("created report:", rid, "| title:", created.get("title"))

    back = _call(base, f"/tensor/reports/{rid}", token=token)
    same_block = _JSON_BLOCK.findall(back.get("markdown") or "")
    assert back["title"] == TITLE, back["title"]
    assert TAG in (back.get("tags") or []), back.get("tags")
    assert len(same_block) == 1 and json.loads(same_block[0]) == payload, "结果块回读不一致"
    print("readback ok: title/tag/result-block identical; report_id =", rid)
    print("tags:", back.get("tags"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())