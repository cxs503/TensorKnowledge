#!/usr/bin/env python3
"""Publish the rendered KF work-package report to the platform (mission report discipline).

Why a script and not a heredoc: `/tmp/report.json` is a *shared* path across concurrent
agents (a sibling work package overwrote it mid-flight and the POST then failed on the
`uq_reports_mission_md5` unique index). This script logs in itself and keeps the payload
in memory, so no cross-agent file can race it.

Usage:
  python3 scripts/kf/publish_report.py --package-id wp-7920-01 [--mission-id 15605] [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
USER = os.environ.get("TENSOR_AGENT_USER", "")
PASS = os.environ.get("TENSOR_AGENT_PASS", "")

SUMMARIES = {
    "wp-7920-01": (
        "report_id=7920（IN154-P4 混合推进能量管理验证）01-asset-registration："
        "源 markdown 身份 sha256=6e60d3f3…493961b（6421 字符 / 10592 B，与工作包契约逐字节一致），"
        "登记 19 个资产 = 1 源资产 + 5 条平台图元数据(metadata_only) + 13 条正文路径/模块引用(unresolved，含 2 个点号模块引用)，"
        "每条带逐字行锚（行号 + 字符区间 + 原文整行，平台可独立复算）；claims 按契约空数组、无 verified 标记。"
        "交付 kf_result.v1 信封 + asset_manifest.json + verification.json（6 项 acceptance + 5 项附加项全通过）+ 11 条不变式测试。"
    )
}


def _req(url, data=None, ctype="application/json", token=None):
    r = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        r.add_header("Content-Type", ctype)
    if token:
        r.add_header("Authorization", "Bearer " + token)
    return json.loads(urllib.request.urlopen(r, timeout=60).read().decode())


def login():
    try:
        d = _req(BASE + "/auth/login", data=json.dumps({"username": USER, "password": PASS}).encode())
    except urllib.error.HTTPError:
        d = _req(
            BASE + "/auth/login",
            data=urllib.parse.urlencode({"username": USER, "password": PASS}).encode(),
            ctype="application/x-www-form-urlencoded",
        )
    return d.get("access_token") or d.get("token")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-id", default="wp-7920-01")
    ap.add_argument("--mission-id", type=int, default=15605)
    ap.add_argument("--scenario-key", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    pkg = a.package_id
    out_dir = REPO / "docs" / "kf" / pkg
    report_path = REPO / "docs" / "reports" / ("kf_%s_result.md" % pkg.replace("-", "_"))
    md = report_path.read_text(encoding="utf-8")
    manifest = json.loads((out_dir / "asset_manifest.json").read_text(encoding="utf-8"))
    rid = manifest["report_id"]

    payload = {
        "title": "KF-RESULT " + pkg,
        "summary": SUMMARIES.get(pkg, "KF-RESULT %s" % pkg),
        "scenario_key": a.scenario_key or manifest["provenance"].get("scenario_key"),
        "mission_id": a.mission_id,
        "tags": ["kf-wp:%s" % pkg, "KF-RESULT", "asset-registration", "TensorKnowledge",
                 "report-%s" % rid],
        "markdown": md,
        "figures": [],
    }
    blob = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    print("payload: %d B, markdown md5=%s" % (len(blob), hashlib.md5(md.encode()).hexdigest()))
    if a.dry_run:
        return 0

    token = login()
    try:
        d = _req(BASE + "/tensor/reports", data=blob, token=token)
    except urllib.error.HTTPError as e:
        print("HTTP %s %s" % (e.code, e.read().decode()[:400]))
        return 1
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    receipt = {"report_id": d.get("id"), "title": d.get("title"), "mission_id": d.get("mission_id"),
               "tags": d.get("tags"), "markdown_md5": hashlib.md5(md.encode()).hexdigest(),
               "markdown_chars": len(md), "package_id": pkg}
    (out_dir / "publish_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                                                 encoding="utf-8")
    print("published report id=%s title=%s" % (receipt["report_id"], receipt["title"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())