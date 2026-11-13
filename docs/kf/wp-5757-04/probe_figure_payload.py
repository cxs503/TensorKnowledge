#!/usr/bin/env python3
"""探针：GET /api/v1/tensor/reports/<id> 回传的 figures 里是否带 png 载荷。

用于复核 review_report.json 的 F5：平台读接口对任何报告（含本单自己内嵌 png_base64
发布的报告）都只回 name+caption → 图件内容对下游不可验，与生产者无关。

用法：python3 docs/kf/wp-5757-04/probe_figure_payload.py 5757 [<本单报告 id> ...]
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request


def main(ids: list[str]) -> int:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    tok = json.load(
        urllib.request.urlopen(
            urllib.request.Request(
                base + "/auth/login",
                data=json.dumps(
                    {
                        "username": os.environ["TENSOR_AGENT_USER"],
                        "password": os.environ["TENSOR_AGENT_PASS"],
                    }
                ).encode(),
                headers={"Content-Type": "application/json"},
            )
        )
    )["access_token"]
    rc = 0
    for rid in ids:
        d = json.load(
            urllib.request.urlopen(
                urllib.request.Request(
                    f"{base}/tensor/reports/{rid}",
                    headers={"Authorization": "Bearer " + tok},
                )
            )
        )
        figs = d.get("figures") or []
        keys = sorted(figs[0].keys()) if figs else []
        has_payload = bool(figs) and all(f.get("png_base64") for f in figs)
        print(f"report {rid}: figures={len(figs)} keys={keys} png_payload={has_payload}")
        if not has_payload:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["5757"]))
