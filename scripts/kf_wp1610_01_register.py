#!/usr/bin/env python3
"""wp-1610-01 | 01-asset-registration for report_id=1610.

Read-only on the platform: fetches tensor://reports/1610 (markdown), recomputes the
sha256 of the markdown UTF-8 bytes, verifies every quoted excerpt in this package is a
verbatim substring of that markdown (zero-hand-copy discipline), and emits

    docs/kf/wp-1610-01/asset_manifest.json   asset registry (no extraction)
    docs/kf/wp-1610-01/locator_check.json    quote -> offset resolution report
    docs/kf/wp-1610-01/source.md             verbatim copy of the source markdown
    docs/kf/wp-1610-01/sha256.txt            recomputed digest

No other report_id is touched. No claim is marked verified: hash equality is a
mechanical identity check, verification status stays with the platform gate.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PWD = os.environ["TENSOR_AGENT_PASS"]
REPORT_ID = "1610"
EXPECTED = "sha256:c426979905fa50a5cd372e8e7b300ad931596c437ea1cbabb79df59c7aaa41de"
OUT = "docs/kf/wp-1610-01"  # must live under docs/: the push gate drops artifacts/**

# (locator_id, verbatim excerpt taken from the markdown, what it pins down)
QUOTES = [
    ("q01", "## 6. 复现", "report has a reproduction section"),
    ("q02", "运行环境：8 项检查，host loadavg [140.46, 109.14, 121.32]，总墙钟 51.8 s（纯 numpy，无 GPU，全部可单机复现）。",
     "stated check count and runtime environment"),
    ("q03", "落地为 `tests/test_cmaes_literature_verification.py`（15 个用例）。",
     "test file + case count"),
    ("q04", "python -m pytest tests/test_cmaes_literature_verification.py -q  # 15 passed",
     "repro command / pass count"),
    ("q05", "达标工况 9/9，最坏比值 1.800（判据 ≤3）。", "convergence acceptance statement"),
    ("q06", "全部维度最坏值 **0**", "closed-form parameter agreement statement"),
    ("q07", "复核中定位并修复的 4 处偏差（最小改动）", "defect-fix block heading (B1-B4)"),
    ("q08", "artifacts/cmaes_verification/cmaes_convergence_vs_reference.png",
     "declared artifact path 1"),
    ("q09", "artifacts/cmaes_verification/cmaes_evals_to_target.png", "declared artifact path 2"),
    ("q10", "artifacts/cmaes_verification/cmaes_achieved_precision.png", "declared artifact path 3"),
    ("q11", "多峰函数（rastrigin/ackley）在 N=10、4e4 评价内两者都停在局部极小",
     "declared limitation (multimodal not covered)"),
    ("q12", "经验协方差相对 Frobenius 误差 0.002",
     "sampling-fidelity figure in the property table"),
    ("q13", "采样协方差", "sampling-fidelity row of the error table"),
    ("q14", "修复后评价数", "B1 A/B table column"),
    ("q15", "闭式策略参数（Hansen 2016 式 49-55）", "closed-form parameter table caption"),
]

# artifact paths that the report text declares but that are NOT resolvable from the
# platform report record (they live in the producing repo, not in this record)
DECLARED_ARTIFACTS = [
    "artifacts/cmaes_verification/cmaes_convergence_vs_reference.png",
    "artifacts/cmaes_verification/cmaes_evals_to_target.png",
    "artifacts/cmaes_verification/cmaes_achieved_precision.png",
]


def post_json(url: str, payload: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def get_json(url: str, token: str) -> dict:
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    return json.loads(urllib.request.urlopen(req, timeout=120).read())


def login() -> str:
    last: Exception | None = None
    for path in ("/auth/login", "/auth/token"):
        try:
            payload = {"username": USER, "password": PWD}
            tok = post_json(BASE + path, payload).get("access_token") or post_json(
                BASE + path, payload).get("token")
        except Exception as exc:  # noqa: BLE001
            last = exc
            continue
        if tok:
            return tok
    raise SystemExit(f"login failed: {last}")


def main() -> None:
    tok = login()
    rec = get_json(f"{BASE}/tensor/reports/{REPORT_ID}", tok)
    if isinstance(rec.get("report"), dict):
        rec = rec["report"]
    md: str = rec["markdown"]

    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    hash_ok = f"sha256:{digest}" == EXPECTED

    checks = []
    for qid, quote, meaning in QUOTES:
        pos = md.find(quote)
        checks.append({
            "locator_id": qid,
            "meaning": meaning,
            "quote": quote,
            "resolvable": pos >= 0,
            "char_offset": pos if pos >= 0 else None,
            "occurrences": md.count(quote),
        })
    unresolved = [c["locator_id"] for c in checks if not c["resolvable"]]

    headings = [ln.strip() for ln in md.splitlines() if ln.startswith("#")]

    manifest = {
        "package_id": "wp-1610-01",
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "source_uri": f"tensor://reports/{REPORT_ID}",
        "source_field": "markdown",
        "source_hash": f"sha256:{digest}",
        "source_hash_expected": EXPECTED,
        "source_hash_matches": hash_ok,
        "hash_algorithm": "sha256 over UTF-8 bytes of the markdown field",
        "title": rec.get("title"),
        "scenario_key": rec.get("scenario_key"),
        "source_mission_id": rec.get("mission_id"),
        "source_status": rec.get("status"),
        "chars": len(md),
        "bytes_utf8": len(md.encode("utf-8")),
        "heading_count": len(headings),
        "headings": headings,
        "attachments": [
            {"name": f.get("name"), "caption": f.get("caption"), "origin": "record.figures"}
            for f in (rec.get("figures") or [])
            if isinstance(f, dict) and f.get("name")
        ],
        "attachments_note": "figure metadata from the report record only; PNG payloads are not downloaded or checked in this package",
        "artifacts": [
            {
                "path": p,
                "locator": "markdown §3.5 图",
                "resolvable_from_platform_record": False,
                "note": "path text is quoted verbatim from the report; the binary lives in the producing repo, not in this record",
            }
            for p in DECLARED_ARTIFACTS
        ],
        "claims": [],
        "claims_note": "claims intentionally empty: this package only registers assets; no extraction, no invented claims",
    }

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "asset_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(os.path.join(OUT, "locator_check.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "report_id": REPORT_ID,
            "source_hash": f"sha256:{digest}",
            "source_hash_matches": hash_ok,
            "quotes_checked": len(checks),
            "quotes_resolvable": len(checks) - len(unresolved),
            "unresolved": unresolved,
            "checks": checks,
        }, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(os.path.join(OUT, "source.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    with open(os.path.join(OUT, "sha256.txt"), "w", encoding="utf-8") as fh:
        fh.write(f"sha256:{digest}\n")

    print(f"report {REPORT_ID}: chars={len(md)} bytes={len(md.encode('utf-8'))}")
    print(f"sha256={digest} match={hash_ok}")
    print(f"quotes: {len(checks) - len(unresolved)}/{len(checks)} resolvable, unresolved={unresolved}")
    if not hash_ok:
        raise SystemExit("SOURCE HASH MISMATCH")
    if unresolved:
        raise SystemExit(f"UNRESOLVED LOCATORS: {unresolved}")


if __name__ == "__main__":
    main()