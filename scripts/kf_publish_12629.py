"""Publish the KF-RESULT report for wp-12629-01 to the platform (report channel = the delivery channel).

Reads the generated report markdown (which already carries exactly one fenced ```json block = the
result envelope) and posts it with the locator-coverage figure attached as base64.

Credentials come from env (TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE); nothing is hardcoded.
Usage: python3 scripts/kf_publish_12629.py [--dry-run]
Output: docs/wp-12629-01/publish_receipt.json
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import sys
import urllib.request

PACKAGE_ID = "wp-12629-01"
MISSION_ID = 15751
DOC_DIR = pathlib.Path("docs") / PACKAGE_ID
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _json(url, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def login() -> str | None:
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not user or not pwd:
        return None
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = _json(BASE + path, {"username": user, "password": pwd})
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def main() -> int:
    dry = "--dry-run" in sys.argv
    md = (DOC_DIR / ("KF-RESULT-%s.md" % PACKAGE_ID)).read_text()
    ver = json.loads((DOC_DIR / "verification.json").read_text())
    if not ver.get("all_pass"):
        print("REFUSING to publish: verification.json all_pass=false")
        return 1
    png = (DOC_DIR / "fig_locator_coverage.png").read_bytes()
    payload = {
        "title": "KF-RESULT %s" % PACKAGE_ID,
        "summary": ("report 12629 资产登记：34 条资产（29 原文可解析 / 4 引用未解析 / 1 声明缺失），"
                    "sha256 与契约一致，claims=0（契约规定不抽取）；独立复核 10/10 通过"),
        "scenario_key": "dp_timedomain",
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:%s" % PACKAGE_ID, "kf-task:01-asset-registration", "lane:C", "DP", "dp_timedomain"],
        "markdown": md,
        "figures": [{
            "name": "fig_locator_coverage.png",
            "caption": ("wp-12629-01 资产 locator 覆盖图：横轴=报告 12629 markdown 字符偏移（0–1899），"
                        "每行=一条资产 locator 区间（绿=resolved_in_source，橙=referenced_unresolved，"
                        "紫=declared_absent），右 panel=asset_class 分布"),
            "png_base64": base64.b64encode(png).decode(),
        }],
    }
    if dry:
        print("dry-run: payload bytes", len(json.dumps(payload)), "figures", len(payload["figures"]))
        return 0
    tok = login()
    d = _json(BASE + "/tensor/reports", payload, tok)
    rec = {"endpoint": BASE + "/tensor/reports", "response": d,
           "markdown_bytes": len(md.encode()), "figure_png_bytes": len(png)}
    (DOC_DIR / "publish_receipt.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    print(json.dumps(rec, ensure_ascii=False)[:600])
    return 0


if __name__ == "__main__":
    sys.exit(main())