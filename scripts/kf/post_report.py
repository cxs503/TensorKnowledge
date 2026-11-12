#!/usr/bin/env python3
"""把工作包报告投递到平台（唯一结果信道之外的进展报告面）。

用法：python3 scripts/kf/post_report.py /tmp/kf_report_2506.json
说明：走 urllib（与 curl 等价），读 $TENSOR_API_BASE / $TENSOR_AGENT_USER / $TENSOR_AGENT_PASS。
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    payload_path = Path(sys.argv[1])
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")

    cred = json.dumps(
        {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]}
    ).encode()
    d = json.load(urllib.request.urlopen(
        urllib.request.Request(base + "/auth/login", data=cred,
                               headers={"Content-Type": "application/json"}), timeout=30))
    tok = d.get("access_token") or d.get("token")

    for k in ("title", "markdown", "mission_id", "tags", "scenario_key", "summary"):
        if k not in payload:
            raise SystemExit("payload 缺字段: " + k)
    if not any(str(t).startswith("kf-wp:") for t in payload["tags"]):
        raise SystemExit("tags 缺 kf-wp:<package_id>")

    req = urllib.request.Request(
        base + "/tensor/reports",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok},
        method="POST",
    )
    try:
        out = json.load(urllib.request.urlopen(req, timeout=180))
    except urllib.error.HTTPError as e:  # noqa: F821
        print("HTTP", e.code, e.read()[:800])
        return 1
    print(json.dumps({k: out.get(k) for k in ("id", "title", "mission_id", "status")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())