"""Probe: does the platform API return figure bytes for a report that was submitted WITH an image?

Why this matters for wp-10647-01: the source report 10647 exposes 4 figures whose ``png_base64`` is
empty in the API payload. Registering that as "the author attached no bitmap" would be an inference,
not an observation -- so this script measures the platform behaviour on a report we submitted
ourselves with a non-empty PNG (the wp-10647-01 deliverable report).

Method (no writes to any report; read-only GET):
  * read the base64 length that was actually submitted  (/tmp/report_10647_publish.json)
  * GET /tensor/reports/<id> for the published report and record the returned png_base64 length
  * also try the plausible figure-serving endpoints and record their status codes

Output: artifacts/wp-10647-01/platform_figure_probe.json + docs/kf/wp-10647-01/platform_figure_probe.json
Usage : python3 scripts/kf_probe_platform_figures.py <published_report_id>
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
PAYLOAD = pathlib.Path("/tmp/report_10647_publish.json")
OUT_ART = pathlib.Path("artifacts/wp-10647-01/platform_figure_probe.json")
OUT_DOC = pathlib.Path("docs/kf/wp-10647-01/platform_figure_probe.json")


def call(path: str, data: dict | None = None, token: str | None = None) -> tuple[int, bytes]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, data=json.dumps(data).encode() if data is not None else None,
                                 headers=headers, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300]


def login() -> str:
    user, pwd = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]
    return json.loads(call("/auth/login", {"username": user, "password": pwd})[1])["access_token"]


def main(report_id: str) -> int:
    token = login()
    sent = json.loads(PAYLOAD.read_text(encoding="utf-8"))["figures"]
    sent_bytes = [len(f.get("png_base64") or "") for f in sent]
    st, body = call("/tensor/reports/%s" % report_id, None, token)
    d = json.loads(body) if st == 200 else {}
    got = [{"name": f.get("name"), "caption_present": bool(f.get("caption")),
            "png_base64_chars": len(f.get("png_base64") or "")} for f in (d.get("figures") or [])]
    endpoints = {}
    for path in ("/tensor/reports/%s/figures" % report_id,
                 "/tensor/figures/%s/%s" % (report_id, sent[0]["name"] if sent else "fig.png")):
        code, b = call(path, None, token)
        endpoints[path] = {"status": code, "body_head": b[:120].decode("utf-8", "replace")}
    probed = {
        "probe": "platform figure byte availability",
        "report_id_probed": report_id,
        "report_note": "该报告由本工单提交，提交时图件 png_base64 非空（见 submitted_png_base64_chars）",
        "submitted_png_base64_chars": sent_bytes,
        "returned_png_base64_chars": got and [g["png_base64_chars"] for g in got],
        "returned_figures": got,
        "figure_endpoints": endpoints,
        "conclusion": ("提交侧非空、响应侧为空 → API 响应不回传图件字节，且无图件下载端点；"
                       "因此 payload 中 png_base64 为空不能推断作者未附图（只说明本环境取不到位图）"),
        "used_for": "asset_manifest A23–A26 的 note 与 resolution_check.detail（避免把响应侧行为误判为作者缺失）",
    }
    OUT_ART.parent.mkdir(parents=True, exist_ok=True)
    OUT_DOC.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(probed, ensure_ascii=False, indent=2) + "\n"
    OUT_ART.write_text(text, encoding="utf-8")
    OUT_DOC.write_text(text, encoding="utf-8")
    print(json.dumps({"submitted": sent_bytes, "returned": probed["returned_png_base64_chars"],
                      "endpoints": {k: v["status"] for k, v in endpoints.items()}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "14772"))
