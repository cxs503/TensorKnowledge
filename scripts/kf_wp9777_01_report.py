#!/usr/bin/env python3
"""wp-9777-01 report generator: produce the KF-RESULT markdown report from
the registered manifest and envelope.

Usage:
    python3 scripts/kf_wp9777_01_report.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ID = "9777"
PACKAGE_ID = "wp-9777-01"
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
REPORT_OUT = ROOT / "docs" / ("kf_result_%s.md" % PACKAGE_ID)


def _api_base() -> str:
    base = os.environ.get("TENSOR_API_BASE")
    if not base:
        raise SystemExit("TENSOR_API_BASE not set")
    return base.rstrip("/")


def _login() -> str:
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(_api_base() + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        tok = json.load(r).get("access_token")
    if not tok:
        raise SystemExit("login returned no access_token")
    return tok


def _get(path: str, tok: str):
    req = urllib.request.Request(_api_base() + path,
                                 headers={"Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def fetch_record() -> dict:
    tok = _login()
    st, raw = _get("/tensor/reports/%s" % REPORT_ID, tok)
    if st != 200:
        raise SystemExit("GET /tensor/reports/%s -> %s" % (REPORT_ID, st))
    return json.loads(raw)


def generate_report():
    manifest = json.loads(MANIFEST.read_text())
    envelope = json.loads(ENVELOPE.read_text())
    verification = json.loads(VERIFICATION.read_text())
    record = fetch_record()

    md_lines = []
    md_lines.append("# KF-RESULT: %s" % PACKAGE_ID)
    md_lines.append("")
    md_lines.append("## 元数据")
    md_lines.append("")
    md_lines.append("| 字段 | 值 |")
    md_lines.append("|---|---|")
    md_lines.append("| package_id | %s |" % PACKAGE_ID)
    md_lines.append("| report_id | %s |" % REPORT_ID)
    md_lines.append("| task_type | %s |" % manifest.get("task_type", ""))
    md_lines.append("| title | %s |" % record.get("title", ""))
    md_lines.append("| scenario_key | %s |" % record.get("scenario_key", ""))
    md_lines.append("| mission_id | %s |" % record.get("mission_id", ""))
    md_lines.append("| source_hash | %s |" % manifest.get("source_hash", ""))
    md_lines.append("| source_chars | %d |" % manifest.get("source_chars", 0))
    md_lines.append("| source_lines | %d |" % manifest.get("source_lines", 0))
    md_lines.append("| asset_count | %d |" % envelope.get("asset_count", 0))
    md_lines.append("| figure_count | %d |" % envelope.get("figure_count", 0))
    md_lines.append("| verification_status | %s |" % envelope.get("verification_status", ""))
    md_lines.append("| verification_overall | %s |" % verification.get("overall", ""))
    md_lines.append("| generated_at | %s |" % envelope.get("generated_at", ""))
    md_lines.append("| producer | %s |" % envelope.get("producer", ""))
    md_lines.append("")

    md_lines.append("## 资产清单")
    md_lines.append("")
    md_lines.append("| # | asset_id | kind | name | resolution |")
    md_lines.append("|---|---|---|---|---|")
    for i, a in enumerate(manifest.get("assets", []), 1):
        res_status = a.get("resolution", {}).get("status", "unknown")
        md_lines.append("| %d | %s | %s | %s | %s |" % (
            i, a.get("asset_id", ""), a.get("kind", ""),
            a.get("name", ""), res_status))
    md_lines.append("")

    md_lines.append("## 验证结果")
    md_lines.append("")
    md_lines.append("| # | check | result |")
    md_lines.append("|---|---|---|")
    for i, c in enumerate(verification.get("checks", []), 1):
        md_lines.append("| %d | %s | %s |" % (i, c.get("check", ""), c.get("result", "")))
    md_lines.append("")
    md_lines.append("**Overall: %s**" % verification.get("overall", ""))
    md_lines.append("")

    md_lines.append("## 说明")
    md_lines.append("")
    md_lines.append("本包为 **01-asset-registration** 类型，仅做资产登记与指针解析，")
    md_lines.append("不做 claim 提取、不做报告类型分类、不做 verified 标记。")
    md_lines.append("所有数字/哈希均由脚本从实时 markdown 程序化测量，零手抄。")
    md_lines.append("")
    md_lines.append("### 独立性声明")
    md_lines.append("")
    md_lines.append(verification.get("independence", {}).get("source", ""))
    md_lines.append("")
    md_lines.append(verification.get("independence", {}).get("limitation", ""))
    md_lines.append("")

    report_text = "\n".join(md_lines) + "\n"
    REPORT_OUT.write_text(report_text, encoding="utf-8")
    print("[report] written: %s (%d bytes)" % (REPORT_OUT, len(report_text)))


if __name__ == "__main__":
    generate_report()
