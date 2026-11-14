#!/usr/bin/env python3
"""Independent read-back verification for the wp-14214-02 delivery.

Re-fetches the published delivery report and the source report from the platform and
checks, without trusting anything local except the files themselves:
  * published markdown is byte-identical to docs/kf_result_wp-14214-02.md
  * it carries exactly one JSON block, equal to work/wp-14214-02/kf_result.json
  * figure and tags survived the round-trip
  * source report 14214 markdown sha256 is still the contract value (nothing was overwritten)

Run: python3 work/wp-14214-02/verify_readback.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path

WP = Path(__file__).resolve().parent
REPO = WP.parents[1]
MD = REPO / "docs" / "kf_result_wp-14214-02.md"
KF = WP / "kf_result.json"
RECEIPT = WP / "publish_receipt.json"
OUT = WP / "readback_verification.json"
SOURCE_HASH = "edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9"


def main() -> int:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")

    def post(url, body, token=None):
        req = urllib.request.Request(url, method="POST", data=json.dumps(body).encode())
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", "Bearer " + token)
        return json.loads(urllib.request.urlopen(req, timeout=60).read())

    def get(url, token):
        req = urllib.request.Request(url)
        req.add_header("Authorization", "Bearer " + token)
        return json.loads(urllib.request.urlopen(req, timeout=60).read())

    token = post(base + "/auth/login", {
        "username": os.environ["TENSOR_AGENT_USER"],
        "password": os.environ["TENSOR_AGENT_PASS"],
    })["access_token"]

    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    pub = get(f"{base}/tensor/reports/{receipt['report_id']}", token)
    pub = pub.get("data", pub)
    src = get(f"{base}/tensor/reports/14214", token)
    src = src.get("data", src)

    local_md = MD.read_text(encoding="utf-8")
    kf = json.loads(KF.read_text(encoding="utf-8"))
    blocks = re.findall(r"```json\n(.*?)\n```", pub["markdown"], re.S)

    result = {
        "package_id": "wp-14214-02",
        "delivery_report_id": pub.get("id"),
        "delivery_title": pub.get("title"),
        "delivery_status": pub.get("status"),
        "checks": {
            "published_markdown_byte_identical": {
                "pass": pub["markdown"] == local_md,
                "chars": len(pub["markdown"]),
            },
            "single_json_block": {"pass": len(blocks) == 1, "count": len(blocks)},
            "payload_equals_kf_result": {
                "pass": bool(blocks) and json.loads(blocks[0]) == kf,
            },
            "figure_present": {
                "pass": "wp14214_02_signal_profile.png" in [f.get("name") for f in pub.get("figures", [])],
                "figures": [f.get("name") for f in pub.get("figures", [])],
            },
            "tag_kf_wp_present": {
                "pass": "kf-wp:wp-14214-02" in pub.get("tags", []),
                "tags": pub.get("tags", []),
            },
            "source_report_14214_unmodified": {
                "pass": hashlib.sha256(src["markdown"].encode("utf-8")).hexdigest() == SOURCE_HASH,
                "sha256": hashlib.sha256(src["markdown"].encode("utf-8")).hexdigest(),
            },
            "scope_single_report": {
                "pass": kf["report_id"] == "14214",
                "report_id": kf["report_id"],
            },
        },
    }
    result["all_pass"] = all(c["pass"] for c in result["checks"].values())
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["checks"], ensure_ascii=False, indent=2))
    print("ALL PASS" if result["all_pass"] else "FAILED CHECKS PRESENT")
    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())