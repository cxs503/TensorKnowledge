#!/usr/bin/env python3
"""Compose the KF-RESULT report for wp-5760-01 from machine-readable artifacts (zero hand-copied numbers).

Sources of truth:
  docs/kf/wp-5760-01/asset_manifest.json     -> counts / hash / assets / integrity
  docs/kf/wp-5760-01/verification.json       -> acceptance table
  docs/kf/wp-5760-01/kf_result.json          -> the single ```json block (inserted byte-for-byte)
  docs/kf/wp-5760-01/figures/asset_inventory.png
  a live `pytest tests/test_kf_wp5760.py -q` -> test summary line

Usage:
  python3 scripts/kf/report_wp5760.py            # write docs/reports/kf_wp_5760_01_result.md
  python3 scripts/kf/report_wp5760.py --post     # ... and publish it to the platform as a new report
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PKG_DIR = REPO / "docs" / "kf" / "wp-5760-01"
TEMPLATE = REPO / "docs" / "reports" / "kf_wp_5760_01_result.template.md"
OUT_MD = REPO / "docs" / "reports" / "kf_wp_5760_01_result.md"
PNG = PKG_DIR / "figures" / "asset_inventory.png"

PKG = "wp-5760-01"
SOURCE_REPORT_ID = "5760"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def esc(s: str, n: int = 72) -> str:
    s = s.replace("\n", "\\n").replace("|", "\\|")
    return s if len(s) <= n else s[: n - 1] + "…"


def run_pytest() -> str:
    p = subprocess.run([sys.executable, "-m", "pytest", "tests/test_kf_wp5760.py", "-q"],
                       cwd=str(REPO), capture_output=True, text=True)
    tail = [ln for ln in p.stdout.strip().split("\n") if "passed" in ln or "failed" in ln]
    return (tail[-1].strip() if tail else "pytest output unparsed: rc=%d" % p.returncode), p.returncode


def evidence_rows(assets: list) -> str:
    keep = ["A01", "A02", "A13", "A19", "A20", "A21", "A23", "A24", "A35", "A40", "A52"]
    by_id = {a["asset_id"]: a for a in assets}
    rows = []
    for aid in keep:
        a = by_id[aid]
        loc = a["locator"]
        if loc["method"] == "report_field":
            where = "figures[%d]" % loc["index"]
        else:
            where = "chars %d–%d / lines %d–%d" % (loc["start_char"], loc["end_char"],
                                                   loc["start_line"], loc["end_line"])
        rows.append("| %s | %s | `%s` | %s | %s |" % (
            aid, a["asset_class"], esc(a["label"], 40), esc(loc["quote"]), where))
    return "\n".join(rows)


def class_rows(counts: dict) -> str:
    return "\n".join("| %s | %d |" % (k, v) for k, v in sorted(counts["by_class"].items()))


def check_rows(ver: dict) -> str:
    acc = ver["acceptance"]
    order = ["valid_json", "schema_pass", "source_locator_resolvable", "source_hash_matches",
             "no_duplicate_ids", "all_claims_have_evidence_or_explicit_unresolved_status"]
    rows = []
    for k in order:
        v = acc[k]
        rows.append("| %s | %s | %s |" % (k, "✓" if v["pass"] else "✗", esc(v["detail"], 96)))
    extra = [k for k in acc if k not in order]
    for k in extra:
        v = acc[k]
        rows.append("| %s *(加固项)* | %s | %s |" % (k, "✓" if v["pass"] else "✗", esc(v["detail"], 96)))
    return "\n".join(rows)


def main(argv) -> int:
    manifest = json.loads((PKG_DIR / "asset_manifest.json").read_text(encoding="utf-8"))
    verdict = json.loads((PKG_DIR / "verification.json").read_text(encoding="utf-8"))
    result_raw = (PKG_DIR / "kf_result.json").read_bytes().decode("utf-8").rstrip("\n")
    json.loads(result_raw)  # fail fast if the envelope is not valid JSON
    counts = manifest["counts"]
    summary, rc = run_pytest()

    md = TEMPLATE.read_text(encoding="utf-8")
    subs = {
        "{{KF_RESULT_JSON}}": result_raw,
        "{{ASSETS}}": str(counts["assets"]),
        "{{CHARS}}": str(manifest["source"]["chars"]),
        "{{CONTRACT_CHARS}}": str(manifest["source"]["chars"]),
        "{{BYTES}}": str(manifest["source"]["bytes_utf8"]),
        "{{HASH}}": manifest["source"]["hash"],
        "{{RESOLVED}}": str(counts["resolved_in_source"]),
        "{{UNRESOLVED}}": str(counts["referenced_unresolved"]),
        "{{ABSENT}}": str(counts["declared_absent"]),
        "{{DISTINCT_PATHS}}": str(counts["distinct_referenced_paths"]),
        "{{CLASS_ROWS}}": class_rows(counts),
        "{{EVIDENCE_ROWS}}": evidence_rows(manifest["assets"]),
        "{{CHECKS_ROWS}}": check_rows(verdict),
        "{{QUOTE_CHECKED}}": str(manifest["integrity"]["quote_uniqueness"]["checked"]),
        "{{QUOTE_UNIQUE}}": str(manifest["integrity"]["quote_uniqueness"]["unique"]),
        "{{NONUNIQUE_IDS}}": ", ".join(manifest["integrity"]["quote_uniqueness"]["non_unique_assets"]) or "(none)",
        "{{MANIFEST_SHA}}": hashlib.sha256((PKG_DIR / "asset_manifest.json").read_bytes()).hexdigest(),
        "{{MANIFEST_BYTES}}": str((PKG_DIR / "asset_manifest.json").stat().st_size),
        "{{PYTEST}}": summary,
        "{{VERIFY_ALL}}": "true" if verdict["all_pass"] else "false",
    }
    for k, v in subs.items():
        md = md.replace(k, v)
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", md)
    if leftover:
        raise SystemExit("unsubstituted template tokens: %s" % sorted(set(leftover)))
    if md.count("```json") != 1:
        raise SystemExit("report must contain exactly one ```json block, found %d" % md.count("```json"))
    OUT_MD.write_text(md, encoding="utf-8")
    print("wrote %s (%d chars); pytest: %s (rc=%d)" % (OUT_MD.relative_to(REPO), len(md), summary, rc))

    if "--post" in argv:
        post(md, manifest, summary)
    return 0


def post(md: str, manifest: dict, summary: str) -> None:
    user = os.environ.get("TENSOR_AGENT_USER", "")
    pw = os.environ.get("TENSOR_AGENT_PASS", "")
    if not user or not pw:
        raise SystemExit("TENSOR_AGENT_USER / TENSOR_AGENT_PASS missing: cannot publish")

    def req(url, payload=None, token=None):
        data = json.dumps(payload).encode() if payload is not None else None
        r = urllib.request.Request(url, data=data, method="POST" if data else "GET")
        if data:
            r.add_header("Content-Type", "application/json")
        if token:
            r.add_header("Authorization", "Bearer " + token)
        with urllib.request.urlopen(r, timeout=120) as resp:
            return json.loads(resp.read().decode())

    tok = req(BASE + "/auth/login", {"username": user, "password": pw})["access_token"]
    fig = {
        "name": "asset_inventory.png",
        "caption": ("wp-5760-01 资产登记清单：左=按资产类别与解析状态的堆叠分布（%d 个资产）；"
                    "右=解析状态合计（resolved_in_source=%d / referenced_unresolved=%d / declared_absent=%d），"
                    "数字由 asset_manifest.json 程序化读出。" % (
                        manifest["counts"]["assets"], manifest["counts"]["resolved_in_source"],
                        manifest["counts"]["referenced_unresolved"], manifest["counts"]["declared_absent"])),
        "png_base64": base64.b64encode(PNG.read_bytes()).decode(),
    }
    payload = {
        "title": "KF-RESULT wp-5760-01",
        "summary": ("wp-5760-01 资产登记（报告 5760）：确认 report_id 与 markdown 字节哈希一致，"
                    "登记 %d 个可解析资产（%d resolved / %d unresolved / %d absent），claims 为空，不做抽取。"
                    % (manifest["counts"]["assets"], manifest["counts"]["resolved_in_source"],
                       manifest["counts"]["referenced_unresolved"], manifest["counts"]["declared_absent"]))[:500],
        "scenario_key": "IN20-R5",
        "mission_id": 15580,
        "tags": ["kf-wp:wp-5760-01", "kf-result", "asset-registration", "IN20-R5", "TensorKnowledge"],
        "markdown": md,
        "figures": [fig],
    }
    d = req(BASE + "/tensor/reports", payload, tok)
    print("published report id=%s status=%s" % (d.get("id"), d.get("status")))
    (PKG_DIR / "published_report.json").write_text(json.dumps(
        {k: v for k, v in d.items() if k not in ("markdown", "figures")}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))