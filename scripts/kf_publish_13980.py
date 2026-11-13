#!/usr/bin/env python3
"""Publish the wp-13980-01 deliverable as a NEW platform report and verify the round trip.

Writes nothing to report 13980 (the registered source): it only creates its own report whose
markdown carries exactly one ```json block (the kf_result envelope) and whose tags carry
``kf-wp:wp-13980-01``.  After publishing it re-reads the stored report, re-extracts the block,
re-parses it and re-checks ``provenance.source_hash`` against a fresh hash of report 13980 --
i.e. the same computation the platform gate performs.
"""
from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import sys
import urllib.error
import urllib.request

PACKAGE_ID = "wp-13980-01"
MISSION_ID = 15770
TITLE = "KF-RESULT " + PACKAGE_ID
SCENARIO_KEY = "ice_resistance"
SOURCE_REPORT = "13980"
CONTRACT_HASH = "2e506d3c8285306a34dd397de133f8c48f6f02a604629adbc0c79eb81ce83ce6"
DOCS = pathlib.Path("docs/kf/wp-13980-01")
BASE = __import__("os").environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
FIGURES = [("fig1_asset_registration.png",
            "图1 wp-13980-01 资产登记覆盖：15 项资产的源文档字符区间（按 resolution 着色）与 resolution 分布；"
            "数据源=asset_manifest.json，零手抄")]


def call(path, body=None, token=None, method="POST"):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        return exc.code, {"error": exc.read().decode("utf-8", "replace")[:800]}


def login():
    import os
    st, r = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                 "password": os.environ["TENSOR_AGENT_PASS"]})
    return r.get("access_token") or r.get("token")


def call_raw(path, token):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def extract_json_block(markdown: str) -> dict:
    if markdown.count("```json") != 1:
        raise SystemExit("published markdown has %d json blocks (must be 1)" % markdown.count("```json"))
    start = markdown.find("```json") + len("```json")
    end = markdown.find("```", start)
    return json.loads(markdown[start:end])


def main() -> int:
    """No args: publish a new report. With ``--verify-only <report_id>``: only re-verify an
    already published report (so the round-trip evidence can be refreshed without spamming
    duplicate reports -- reports are append-only on this platform)."""
    verify_only = len(sys.argv) == 3 and sys.argv[1] == "--verify-only"
    md = (DOCS / ("KF-RESULT-" + PACKAGE_ID + ".md")).read_text()
    envelope = json.loads((DOCS / ("kf_result." + PACKAGE_ID + ".json")).read_text())
    assert md.count("```json") == 1 and md.count("```") == 2
    assert extract_json_block(md) == envelope
    assert envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH

    figures = [{"name": n, "caption": c,
                "png_base64": base64.b64encode((DOCS / n).read_bytes()).decode()}
               for n, c in FIGURES]

    man = json.loads((DOCS / "asset_manifest.json").read_text())
    c = man["counts"]
    payload = dict(
        title=TITLE,
        summary=("wp-13980-01 资产登记：report 13980 的 markdown 逐字节固定（sha256 %s…、%d 字符），"
                 "登记 %d 项资产（%d 源内可定位 / %d 引用未解析 / %d 声明缺失），全部 quote 唯一且偏移可复现，"
                 "claims 为空（本工序不抽取），未标注任何 verified。%s"
                 % (man["source"]["hash"][:12], man["source"]["chars"], c["assets"],
                    c["resolved_in_source"], c["referenced_unresolved"], c["declared_absent"],
                    "（本报告取代先前 report 14869 / 14880：补登记 40 工况原始工件族 A16，并把正文资产计数表述改为动态取数；asset_manifest.json 本体与 14880 逐字节相同。）"
                    if "--supersede" in " ".join(sys.argv) else "")),
        scenario_key=SCENARIO_KEY,
        mission_id=MISSION_ID,
        tags=["kf-work-package", "kf-wp:" + PACKAGE_ID, "asset-registration",
              "provenance", "report-13980"],
        markdown=md,
        figures=figures,
    )
    tok = login()
    if verify_only:
        new_id = sys.argv[2]
        print("verify-only mode, report id:", new_id)
    else:
        status, resp = call("/tensor/reports", payload, tok)
        print("POST /tensor/reports ->", status)
        if status not in (200, 201):
            print(json.dumps(resp, ensure_ascii=False)[:900])
            return 1
        new_id = resp.get("id") or (resp.get("data") or {}).get("id")
        print("published report id:", new_id)

    got_status, record = call("/tensor/reports/" + str(new_id), token=tok, method="GET")
    stored = record.get("markdown", "")
    block = extract_json_block(stored)
    _, src = call("/tensor/reports/" + SOURCE_REPORT, token=tok, method="GET")
    fresh_hash = hashlib.sha256(src["markdown"].encode()).hexdigest()
    roundtrip = dict(
        published_report_id=new_id,
        http_status=got_status,
        json_block_round_trip_equal=block == envelope,
        json_blocks_in_markdown=stored.count("```json"),
        provenance_hash_equals_fresh_source_hash=(
            block["provenance"]["source_hash"] == "sha256:" + fresh_hash),
        fresh_source_hash=fresh_hash,
        report_id_field=block["report_id"],
        package_id_field=block["package_id"],
        tags_stored=record.get("tags"),
        figures_stored=[f.get("name") for f in record.get("figures", [])],
        # the record JSON does not echo png payloads; the binary endpoint does. Hash it.
        figure_fetch=[dict(name=n, http_status=(stt := call_raw(
            "/tensor/reports/%s/figures/%s" % (new_id, n), tok)[0]),
            bytes=(len(blob) if isinstance(blob, bytes) else 0),
            sha256=(hashlib.sha256(blob).hexdigest() if isinstance(blob, bytes) else None),
            matches_local=(isinstance(blob, bytes)
                           and hashlib.sha256(blob).hexdigest()
                           == hashlib.sha256((DOCS / n).read_bytes()).hexdigest()))
            for n, blob in [(n, call_raw("/tensor/reports/%s/figures/%s" % (new_id, n), tok)[1])
                            for n in [f[0] for f in FIGURES]]],
    )
    out = pathlib.Path("runs/wp-13980-01/publish_roundtrip.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(roundtrip, ensure_ascii=False, indent=2) + "\n")
    (DOCS / "publish_roundtrip.json").write_text(
        json.dumps(roundtrip, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(roundtrip, ensure_ascii=False, indent=2))
    ok = (roundtrip["json_block_round_trip_equal"] and roundtrip["json_blocks_in_markdown"] == 1
          and roundtrip["provenance_hash_equals_fresh_source_hash"]
          and roundtrip["report_id_field"] == SOURCE_REPORT
          and "kf-wp:" + PACKAGE_ID in (record.get("tags") or [])
          and all(f["matches_local"] for f in roundtrip["figure_fetch"]))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())