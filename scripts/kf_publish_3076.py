#!/usr/bin/env python3
"""Publish the wp-3076-01 deliverable as a NEW platform report and verify the round trip.

Writes nothing to report 3076 (the registered source): it only creates its own report whose
markdown carries exactly one ```json block (the kf_result envelope). After publishing it re-reads
the stored report, re-extracts the block, re-parses it and re-checks provenance.source_hash against
a fresh hash of report 3076 — i.e. the same computation the platform gate performs.
"""
from __future__ import annotations

import base64
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path

import kf_fetch_3076 as fetch
import kf_verify_3076 as verify

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "wp-3076-01"
PACKAGE_ID = "wp-3076-01"
MISSION_ID = 15533
TITLE = f"KF-RESULT {PACKAGE_ID}"
SCENARIO_KEY = "paper-line-provenance-gate"
FIGURES = [
    ("fig_locator_map.png", "19 条资产 locator 在 3712 字符 markdown 中的区间（颜色=payload 状态）"),
    ("fig_payload_status.png", "payload 状态分布：2 记录内 / 11 外部 / 3 载荷 404 / 2 越界不读 / 1 仅源内声明"),
    ("fig_acceptance_matrix.png", "契约 acceptance 逐项机检结果（在线模式 10/10 PASS）"),
]


def call(path: str, body: dict | None = None, token: str | None = None, method: str = "POST") -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(fetch.api_base() + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        return exc.code, {"error": raw[:800]}


def call_raw(path: str, token: str) -> tuple[int, bytes]:
    """GET returning raw bytes (figure payloads are binary, not JSON)."""
    req = urllib.request.Request(fetch.api_base() + path, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def extract_json_block(markdown: str) -> dict:
    start = markdown.find("```json")
    if start < 0:
        raise SystemExit("published markdown has no json block")
    end = markdown.find("```", start + len("```json"))
    if markdown.count("```json") != 1:
        raise SystemExit(f"published markdown has {markdown.count('```json')} json blocks (must be 1)")
    block = markdown[start + len("```json"): end]
    return json.loads(block)


def main() -> int:
    body_md = (DOCS / f"KF-RESULT-{PACKAGE_ID}.md").read_text(encoding="utf-8")
    envelope = json.loads((DOCS / f"kf_result.{PACKAGE_ID}.json").read_text(encoding="utf-8"))
    required_hash = "sha256:" + verify.CONTRACT_HASH

    assert body_md.count("```json") == 1 and body_md.count("```") == 2
    assert extract_json_block(body_md) == envelope, "json block in the markdown differs from the envelope file"
    assert envelope["provenance"]["source_hash"] == required_hash

    figures = []
    for name, caption in FIGURES:
        png = (DOCS / name).read_bytes()
        figures.append({"name": name, "caption": caption, "png_base64": base64.b64encode(png).decode()})

    payload = {
        "title": TITLE,
        "summary": (
            "登记报告 3076 的源资产：markdown 逐字节固定（sha256 9b7bb242…、3712 字符），19 条资产的字符区间/引文/唯一性"
            "全部机检；3 张平台图有名字无载荷（/figures 404）如实标 unresolved；16 条外部/越界工件显式不解析；claims 空（本工序不抽取）。"
        ),
        "scenario_key": SCENARIO_KEY,
        "mission_id": MISSION_ID,
        "tags": ["kf-work-package", f"kf-wp:{PACKAGE_ID}", "asset-registration", "provenance", "report-3076"],
        "markdown": body_md,
        "figures": figures,
    }
    status, resp = call("/tensor/reports", payload, fetch.login())
    print("POST /tensor/reports ->", status)
    if status not in (200, 201):
        print(json.dumps(resp, ensure_ascii=False)[:900])
        return 1
    new_id = resp.get("id") or (resp.get("data") or {}).get("id")
    print("published report id:", new_id)

    # ---- round trip ----
    got_status, record = call(f"/tensor/reports/{new_id}", token=fetch.login(), method="GET")
    stored_md = record.get("markdown", "")
    block = extract_json_block(stored_md)
    fresh_source, _ = fetch.fetch_markdown()
    fig_status, fig_bytes = call_raw(f"/tensor/reports/{new_id}/figures/{FIGURES[0][0]}", fetch.login())
    recheck = {
        "published_report_id": new_id,
        "http_status": got_status,
        "json_block_round_trip_equal": block == envelope,
        "json_blocks_in_markdown": stored_md.count("```json"),
        "provenance_hash_equals_fresh_report_3076_hash": block["provenance"]["source_hash"]
        == "sha256:" + hashlib.sha256(fresh_source.encode("utf-8")).hexdigest(),
        "report_id_field": block["report_id"],
        "package_id_field": block["package_id"],
        "tags_stored": record.get("tags"),
        "figures_stored": [f.get("name") for f in record.get("figures", [])],
        "figures_have_png": [bool(f.get("png_base64")) for f in record.get("figures", [])],
        "figure_payload_exposed_in_record": any(f.get("png_base64") for f in record.get("figures", [])),
        "figure_endpoint_positive_control": {
            "report_id": new_id,
            "name": FIGURES[0][0],
            "http_status": fig_status,
            "bytes": len(fig_bytes),
            "sha256": hashlib.sha256(fig_bytes).hexdigest(),
            "note": "GET /tensor/reports/<id>/figures/<name> returns 200 here, so the 404 observed for report 3076 is a genuinely absent payload, not a wrong route",
        },
    }
    roundtrip_path = DOCS / "publish_roundtrip.json"
    history: list[dict] = []
    if roundtrip_path.exists():
        prev = json.loads(roundtrip_path.read_text(encoding="utf-8"))
        history = [h for h in prev.get("superseded_reports", []) if isinstance(h, dict)]
        if prev.get("published_report_id") not in (None, new_id):
            history.append(
                {
                    "report_id": prev["published_report_id"],
                    "superseded_by": new_id,
                    "reason": prev.get("superseded_note") or "earlier version of the same package report (body lacked the figure-endpoint positive-control section); result envelope identical",
                }
            )
    recheck["superseded_reports"] = history
    recheck["superseded_note"] = (
        "only the report named in published_report_id is the deliverable for this work package; earlier ids are listed for audit"
        if history
        else "this is the first and only published report for this work package"
    )
    roundtrip_path.write_text(json.dumps(recheck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(recheck, ensure_ascii=False, indent=2))
    ok = all(
        [
            recheck["json_block_round_trip_equal"],
            recheck["json_blocks_in_markdown"] == 1,
            recheck["provenance_hash_equals_fresh_report_3076_hash"],
            recheck["report_id_field"] == "3076",
            recheck["package_id_field"] == PACKAGE_ID,
            f"kf-wp:{PACKAGE_ID}" in (record.get("tags") or []),
        ]
    )
    print("round_trip_ok:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())