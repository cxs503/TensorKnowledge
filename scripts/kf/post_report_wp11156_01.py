#!/usr/bin/env python3
"""Publish the KF-RESULT wp-11156-01 progress report to the platform (/tensor/reports).

Payload is assembled from committed artifacts only:
  markdown  <- docs/kf/wp-11156-01/KF-RESULT-wp-11156-01.md (six sections + the single json block)
  figures   <- docs/kf/wp-11156-01/asset_locator_map.png (base64)
Credentials from env (TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS); nothing is logged.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PKG = os.path.join(ROOT, "docs", "kf", "wp-11156-01")
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
PKG_ID = "wp-11156-01"

SUMMARY = (
    "wp-11156-01 (01-asset-registration) on report 11156: markdown re-fetched and sha256-pinned "
    "(4e34bdac…06d77, 4478 chars / 4489 bytes, identical to the contract hash); 21 assets registered "
    "with verbatim, uniqueness-checked locators (9 resolved in source / 4 referenced-but-unresolved / "
    "8 declared-only); 4 record-vs-markdown discrepancies logged without interpretation; claims "
    "intentionally empty and nothing marked verified. 19 offline acceptance tests pass."
)


def post() -> dict:
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(API + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    tok = json.load(urllib.request.urlopen(req, timeout=30))["access_token"]

    md = open(os.path.join(PKG, "KF-RESULT-wp-11156-01.md"), encoding="utf-8").read()
    png = base64.b64encode(open(os.path.join(PKG, "asset_locator_map.png"), "rb").read()).decode()

    payload = {
        "title": "KF-RESULT " + PKG_ID,
        "summary": SUMMARY,
        "scenario_key": "p284w3-n05-dem-auto-calibration",
        "mission_id": 15691,
        "tags": ["kf-wp:" + PKG_ID, "01-asset-registration", "report:11156",
                 "asset-manifest", "kf"],
        "markdown": md,
        "figures": [{
            "name": "asset_locator_map.png",
            "caption": "图 1：wp-11156-01 登记的 21 条资产在 report 11156 markdown（4478 字符）中的定位分布；"
                       "横轴=字符偏移，颜色=resolution（蓝=源内可定位，红=引用但本 worktree 不可解析，"
                       "橙=仅 record 声明）；斜线填充行是 record.figures 携带的图元数据（无 markdown 跨度）。"
                       "本图为流程性文档任务：报告不含场量计算，故无场量云图/解析解对比曲线，"
                       "该限制在正文 ⑤ 说明。",
            "png_base64": png,
        }],
    }
    req = urllib.request.Request(API + "/tensor/reports", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + tok})
    return json.load(urllib.request.urlopen(req, timeout=60))


if __name__ == "__main__":
    r = post()
    print(json.dumps({k: r.get(k) for k in ("id", "title", "status", "scenario_key")},
                     ensure_ascii=False))