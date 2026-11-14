"""把 wp-9246-02 的 KF-RESULT 报告发到平台（唯一结果信道）。

用法：python3 scripts/kf/kf9246_publish.py [--dry-run]
需要 TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS。
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "production" / "wp-9246-02"

TITLE = "KF-RESULT wp-9246-02"
TAGS = ["kf-wp:wp-9246-02", "02-classification-parse", "report-9246",
        "scientific-computation", "lane-B"]
SCENARIO_KEY = "IN144-N09"
MISSION_ID = 19786


def post(path: str, payload: dict, token: str | None = None) -> dict:
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(base + path, data=json.dumps(payload).encode(),
                                 headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    markdown = (OUT / "KF-RESULT-wp-9246-02.md").read_text()
    png = OUT / "figures" / "classification_decision.png"
    payload = {
        "title": TITLE,
        "summary": ("report_id=9246 的分类解析（修订版，取代首版 18021：① 标题段级别统计改为"
                    "程序化计数，不再手写「6 个一级章」）：按 registry 六分型判定为 scientific-computation"
                    "（备选 experimental-validation 因 step-fit 不满足被排除），"
                    "22 条逐字证据、9 条判断全部证据绑定、3 条显式 unresolved；"
                    "不抽 claim、不标 verified。"),
        "scenario_key": SCENARIO_KEY,
        "mission_id": MISSION_ID,
        "tags": TAGS,
        "markdown": markdown,
        "figures": [{
            "name": "classification_decision.png",
            "caption": ("wp-9246-02 判定输入：左为 registry identify_signals × 6 类候选的命中矩阵"
                        "（hit/miss，右列为 hits/total），右为命中数与 step-fit 比例，红虚线为 R1 门槛 2。"),
            "png_base64": base64.b64encode(png.read_bytes()).decode(),
        }],
    }
    if args.dry_run:
        print(json.dumps({k: (v if k != "markdown" and k != "figures" else f"<{len(str(v))} chars>")
                          for k, v in payload.items()}, ensure_ascii=False, indent=2))
        return 0

    tok = post("/auth/login", {"username": os.environ.get("TENSOR_AGENT_USER", ""),
                               "password": os.environ.get("TENSOR_AGENT_PASS", "")})["access_token"]
    resp = post("/tensor/reports", payload, tok)
    (OUT / "publish_receipt.json").write_text(json.dumps(resp, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: resp[k] for k in ("id", "title", "status") if k in resp},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())