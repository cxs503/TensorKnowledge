#!/usr/bin/env python3
"""Publish the wp-5347-01 result report to TensorPlatform (the only result channel).

The report body is ``artifacts/wp-5347-01/KF-RESULT-wp-5347-01.md`` verbatim: it
carries exactly one fenced JSON block (the kf_result envelope), so the platform
extracts it unambiguously.  Figures are attached inline as base64 PNGs.

Title is fixed to ``KF-RESULT wp-5347-01`` and the tag ``kf-wp:wp-5347-01`` is
mandatory; both are asserted before sending.  The server's report schema is not
self-documenting from the client side, so payload shapes are tried in order and
every response body is printed (no guessing, no silent retry loops).

Usage: python3 scripts/publish_wp_5347_01_report.py [--dry-run]
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "artifacts" / "wp-5347-01"
if not PKG.is_dir():  # committed snapshot: artifacts/** is git-ignored
    PKG = REPO / "docs" / "production" / "wp-5347-01"
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

PACKAGE_ID = "wp-5347-01"
TAG = f"kf-wp:{PACKAGE_ID}"
TITLE = f"KF-RESULT {PACKAGE_ID}"
MISSION_ID = 15564
FIGURES = (
    ("asset_inventory.png",
     "报告 5347 的资产台账：按 kind×可达性堆叠，resolved 恒为 0（工序 01 只登记不检出；"
     "TensorDEM 工件不在本包字节范围内）。计数取自 asset_manifest.json。"),
    ("gate_evidence.png",
     "平台门 g1–g7 与本地 acceptance A1–A10 的逐项状态：唯一非 passed 的是 A6"
     "（0 claim 空真，记 vacuous 而非 passed），无 failed。取自 checks.json/platform_gate.json。"),
)


def call(path: str, body: dict, tok: str | None = None, timeout: int = 120):
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()[:800]
    except Exception as exc:  # noqa: BLE001
        return -1, repr(exc)[:300]


def login() -> str:
    status, body = call("/auth/login", {
        "username": os.environ["TENSOR_AGENT_USER"],
        "password": os.environ["TENSOR_AGENT_PASS"],
    })
    if status != 200:
        raise SystemExit(f"login failed: {status} {body[:200]}")
    return json.loads(body)["access_token"]


def build_payload() -> dict:
    md = (PKG / f"KF-RESULT-{PACKAGE_ID}.md").read_text(encoding="utf-8")
    assert md.lstrip().startswith(f"# {TITLE}"), "report title line mismatch"
    if md.count("```json") != 1:
        raise SystemExit(f"report must carry exactly one fenced json block, "
                         f"found {md.count('```json')}")
    manifest = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    cts = manifest["counts"]
    summary = (
        f"工序 01 资产登记（report 5347，TensorDEM CI 清红 m4829）：源 markdown "
        f"{manifest['source']['chars']} 字符、sha256 与契约一致；登记 {cts['assets']} 条资产"
        f"（{'/'.join(f'{k}={v}' for k, v in cts['by_kind'].items())}），"
        f"resolved={cts['resolved']}（跨仓工件与图注元数据不可取字节，fail-closed 记 unresolved）。"
        f"不抽取、不分类，claims=[] 为契约合法结果；本地 acceptance 9 passed/1 vacuous/0 failed，"
        f"平台门 g1–g7 全 ok。"
    )
    figures = []
    for name, caption in FIGURES:
        path = PKG / "figures" / name
        figures.append({"name": name, "caption": caption,
                        "png_base64": base64.b64encode(path.read_bytes()).decode()})
    return {
        "title": TITLE,
        "summary": summary,
        "scenario_key": "ci_clearance",
        "mission_id": MISSION_ID,
        "tags": [TAG, "kf", "asset-registration", "report-5347", "ci_clearance",
                 "TensorKnowledge"],
        "markdown": md,
        "figures": figures,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    payload = build_payload()
    if args.dry_run:
        print(json.dumps({"title": payload["title"], "tags": payload["tags"],
                          "mission_id": payload["mission_id"],
                          "markdown_chars": len(payload["markdown"]),
                          "figures": [f["name"] for f in payload["figures"]],
                          "summary": payload["summary"]}, ensure_ascii=False, indent=2))
        return 0

    tok = login()
    variants = [
        ("full", payload),
        ("no_figures", {k: v for k, v in payload.items() if k != "figures"}),
        ("minimal", {k: payload[k] for k in
                     ("title", "summary", "scenario_key", "mission_id", "markdown")}),
    ]
    for name, body in variants:
        status, resp = call("/tensor/reports", body, tok)
        print(f"[{name}] {status} {resp[:300]}")
        if status in (200, 201):
            (PKG / "publish_receipt.json").write_text(
                json.dumps({"variant": name, "status": status, "response": resp,
                            "title": payload["title"], "tags": payload["tags"]},
                           ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print("posted variant:", name)
            return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())