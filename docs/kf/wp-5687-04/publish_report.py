#!/usr/bin/env python3
"""Publish the wp-5687-04 review as a platform report (KF-RESULT envelope inside the markdown).

Reads report_body.md (the single ```json block is the result envelope) and fig1_review_evidence.png,
posts to POST /api/v1/tensor/reports, prints the created report id.
"""
import base64
import json
import os
import urllib.request
from pathlib import Path

PKG = Path(__file__).resolve().parent
PKG_ID = "wp-5687-04"
REPORT_ID = "5687"
MISSION_ID = 15838


def _req(url, data=None, tok=None):
    h = {"Content-Type": "application/json"}
    if tok:
        h["Authorization"] = "Bearer " + tok
    r = urllib.request.Request(url, data=data, headers=h)
    return json.load(urllib.request.urlopen(r, timeout=60))


def main() -> int:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    tok = _req(base + "/auth/login",
               json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                           "password": os.environ["TENSOR_AGENT_PASS"]}).encode())["access_token"]
    body = (PKG / "report_body.md").read_text(encoding="utf-8")
    assert body.count("```json") == 1, body.count("```json")
    env = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
    assert env["package_id"] == PKG_ID and env["report_id"] == REPORT_ID

    payload = {
        "title": f"KF-RESULT {PKG_ID}",
        "summary": (f"独立 red-team 审核 report 5687 的上游包 wp-5687-01（01-asset-registration）："
                    f"18 条机器检查，门判据 13/13 绿、blocking 0；判 pass 并记 6 条非阻塞缺陷"
                    f"（1 medium：verification.json 检查名 source_locator_resolvable 易被读成「全部解析」）。"
                    f"源哈希三方一致、7 条 locator 引文逐字命中、无 verified 断言。"),
        "scenario_key": "kf-review-wp-5687-04",
        "mission_id": MISSION_ID,
        "tags": [f"kf-wp:{PKG_ID}", "kf-review", "independent-review", "red-team",
                 "report-5687", "wp-5687-01", "IN18-T2", "TensorKnowledge"],
        "markdown": body,
        "figures": [{
            "name": "fig1_review_evidence.png",
            "caption": ("图1 复核证据三视图：A 为 18 条检查矩阵（实心=13 条门判据，斜纹=覆盖/标注项，"
                        "红=3 条非阻塞不合格项 C16/C17/C18）；B 为 7 条 locator 逐字复核（引文在声明行与全文"
                        "双重命中）；C 为缺陷分级与处置（medium 1 / low 5，blocking 0）。"),
            "png_base64": base64.b64encode(
                (PKG / "fig1_review_evidence.png").read_bytes()).decode(),
        }],
    }
    rec = _req(base + "/tensor/reports", json.dumps(payload).encode(), tok)
    rec = rec.get("report", rec)
    print("published report id:", rec.get("id"), "status:", rec.get("status"),
          "title:", rec.get("title"))
    (PKG / "publish_receipt.json").write_text(json.dumps(
        {"report_id": rec.get("id"), "title": rec.get("title"), "status": rec.get("status"),
         "scenario_key": rec.get("scenario_key"), "mission_id": rec.get("mission_id"),
         "tags": rec.get("tags")}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())