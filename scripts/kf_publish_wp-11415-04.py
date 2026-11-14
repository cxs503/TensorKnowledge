#!/usr/bin/env python3
"""Publish the wp-11415-04 review report to the platform and verify the
published shape.

The markdown is the committed report (docs/kf/wp-11415-04/KF-RESULT-wp-11415-04.md),
which already carries exactly one fenced JSON block = artifacts', i.e. the
deliverable envelope; the figure is embedded as base64.

Local outputs
  docs/kf/wp-11415-04/report_published.json   API response + markdown/figure fingerprints
  runs/wp-11415-04/post_body_preview.json     POST body with the heavy fields elided

Run: python3 scripts/kf_publish_wp-11415-04.py [--dry-run] [--verify-only]
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request

import jsonschema

PACKAGE = "wp-11415-04"
MISSION_ID = 19811
DOC = pathlib.Path("docs/kf/wp-11415-04")
MD_PATH = DOC / f"KF-RESULT-{PACKAGE}.md"
FIG = DOC / "fig1_review_dashboard.png"
REC = DOC / "report_published.json"
PREVIEW = pathlib.Path("runs/wp-11415-04/post_body_preview.json")
FENCE = chr(96) * 3


def post(path: str, payload: dict, token: str | None = None) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(base + path, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode())


def get(path: str, token: str) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(base + path, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode())


def login() -> str:
    auth = post("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                "password": os.environ["TENSOR_AGENT_PASS"]})
    token = auth.get("access_token") or auth.get("token")
    if not token:
        raise SystemExit("FATAL: no token in login response")
    return token


def verify_published(token: str, rid: int) -> dict:
    pub = get(f"/tensor/reports/{rid}", token)
    md = pub["markdown"]
    blocks = re.findall(FENCE + r"json\n(.*?)\n" + FENCE, md, flags=re.S)
    schema = json.loads(pathlib.Path("schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    envelope = json.loads(blocks[0]) if blocks else {}
    try:
        jsonschema.validate(envelope, schema)
        schema_ok = True
    except jsonschema.ValidationError:
        schema_ok = False
    local = MD_PATH.read_text(encoding="utf-8")
    return {
        "published_id": pub.get("id"),
        "title_ok": pub.get("title") == f"KF-RESULT {PACKAGE}",
        "tag_ok": f"kf-wp:{PACKAGE}" in (pub.get("tags") or []),
        "tags": pub.get("tags"),
        "one_json_block": md.count(FENCE + "json") == 1,
        "envelope_schema_ok": schema_ok,
        "envelope_matches_local": json.loads(blocks[0]) == json.loads(
            re.findall(FENCE + r"json\n(.*?)\n" + FENCE, local, flags=re.S)[0]),
        "markdown_identical_to_local": md == local,
        "markdown_chars": len(md),
        "figures": [f.get("name") for f in (pub.get("figures") or [])],
    }


def main() -> int:
    dry = "--dry-run" in sys.argv
    if "--verify-only" in sys.argv:
        checks = verify_published(login(), json.loads(REC.read_text())["published_response"]["id"])
        print(json.dumps(checks, ensure_ascii=False, indent=2))
        return 0 if all(v for k, v in checks.items() if isinstance(v, bool)) else 5

    md = MD_PATH.read_text(encoding="utf-8")
    assert md.count(FENCE + "json") == 1, "report must carry exactly one fenced json block"
    result = json.loads((DOC / "kf_result.json").read_text(encoding="utf-8"))
    assert json.loads(re.findall(FENCE + r"json\n(.*?)\n" + FENCE, md, flags=re.S)[0]) == result
    review = result["outputs"]["review_report.json"]
    disp = review["disposition"]

    png = FIG.read_bytes()
    payload = {
        "title": f"KF-RESULT {PACKAGE}",
        "summary": (
            f"报告 11415 的 01 工序产物 wp-11415-01 独立红队审核：源 sha256 与契约一致"
            f"（{result['provenance']['chars']} 字符），28/28 定位码逐字节命中，"
            f"{review['check_summary']['total']} 项检查 {review['check_summary']['pass']} 过 "
            f"{review['check_summary']['fail']} 不过；判定 {disp['verdict']}（{disp['disposition']}），"
            f"产线 {disp['pipeline_verdict']}：上游 run 产物未提交导致验证器不可复跑（F1）、"
            f"信封 schema 违规属产线范围口径分歧（F2）。未把任何结论标为 verified。"
        ),
        "scenario_key": result["provenance"]["scenario_key"],
        "mission_id": MISSION_ID,
        "tags": [f"kf-wp:{PACKAGE}", "independent-review", "red-team", "knowledge-factory",
                 "IMO", "weather-criterion", f"report:{result['report_id']}", "m19811"],
        "markdown": md,
        "figures": [{
            "name": FIG.name,
            "caption": (
                "wp-11415-04 审核仪表盘：(A) C1–C10 检查矩阵，8 过 2 不过；(B) 被审包 wp-11415-01 的 "
                f"{len(result['outputs']['review_report.json']['checks'])} 项检查所覆盖的资产类别分布；"
                "(C) 产线级 kf_result.v1 合规率（40 包中 39 包违规，含被审包）；"
                "(D) 被审报告源表自身算术残差（lw2=1.5·lw1、b/a 重算、C5 跨列），仅剩 4 位小数舍入。"
                "全部数值由 runs/wp-11415-04/*.json 程序化注入。"
            ),
            "png_base64": base64.b64encode(png).decode(),
        }],
    }
    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    PREVIEW.write_text(json.dumps({**payload,
                                   "markdown": f"<{len(md)} chars>",
                                   "figures": [{**payload["figures"][0],
                                                "png_base64": f"<{len(payload['figures'][0]['png_base64'])} b64 chars>"}]},
                                  ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if dry:
        print(f"dry-run: markdown {len(md)} chars, figure {len(png)} bytes (not published)")
        return 0

    token = login()
    res = post("/tensor/reports", payload, token)
    rec = {
        "published_response": res,
        "published_markdown_chars": len(md),
        "published_markdown_sha256": "sha256:" + hashlib.sha256(md.encode()).hexdigest(),
        "figure_bytes": len(png),
        "figure_sha256": "sha256:" + hashlib.sha256(png).hexdigest(),
        "title": payload["title"],
        "tags": payload["tags"],
        "mission_id": MISSION_ID,
    }
    REC.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("published:", json.dumps(res, ensure_ascii=False)[:300])
    checks = verify_published(token, res["id"])
    rec["post_publish_verification"] = checks
    REC.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("post-publish verification:", json.dumps(checks, ensure_ascii=False)[:500])
    return 0 if all(v for k, v in checks.items() if isinstance(v, bool)) else 5


if __name__ == "__main__":
    sys.exit(main())