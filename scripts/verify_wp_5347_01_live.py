#!/usr/bin/env python3
"""Live, independent re-check of the delivered result.

What "independent" means here: nothing is read from the local artefacts except
the package identity.  The payload is extracted from the **published** report's
markdown with the platform's own extractor, the source bytes are re-fetched from
the API (not the local snapshot), and the hashes/gates are recomputed.

Writes ``artifacts/wp-5347-01/live_gate.json`` and exits 0 iff:

  L1 the published report carries exactly one fenced JSON block
  L2 that payload equals the local kf_result.json (byte-for-byte in content)
  L3 its provenance.source_hash equals sha256(live markdown of report 5347)
  L4 platform structure gate g1..g3 ok against the owning contract identity
  L5 platform evidence gate g4..g7 ok, locator_rate reported as None (0 claims)
  L6 the published tags contain ``kf-wp:wp-5347-01`` and the title is exact

Usage: python3 scripts/verify_wp_5347_01_live.py [--report-id 14642]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "artifacts" / "wp-5347-01"
if not PKG.is_dir():  # committed snapshot: artifacts/** is git-ignored
    PKG = REPO / "docs" / "production" / "wp-5347-01"
OPS = Path(os.environ.get("KF_OPS_DIR", "/root/tp-agent/kf/ops"))
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

PACKAGE_ID = "wp-5347-01"
TAG = f"kf-wp:{PACKAGE_ID}"
TITLE = f"KF-RESULT {PACKAGE_ID}"
CONTRACT = {"package_id": PACKAGE_ID, "report_id": "5347",
            "task_type": "01-asset-registration"}


def get(path: str, tok: str | None = None) -> dict:
    req = urllib.request.Request(API + path)
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-id", default="14642", help="published KF-RESULT report id")
    args = ap.parse_args(argv)

    tok = post("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                               "password": os.environ["TENSOR_AGENT_PASS"]})["access_token"]
    published = get(f"/tensor/reports/{args.report_id}", tok)
    source = get("/tensor/reports/5347", tok)
    local = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))

    sys.path.insert(0, str(OPS))
    from knowledge_factory import gates  # platform's own extractor + gates

    payload, err = gates.extract_payload(published.get("markdown", ""))
    source_md = source.get("markdown", "")
    recomputed = gates.sha256_text(source_md)

    checks = []

    def add(name, ok, **evidence):
        checks.append({"check": name, "ok": bool(ok), "evidence": evidence})

    add("L1.single_json_block", payload is not None, error=err)
    add("L2.payload_equals_local", payload == local,
        keys=sorted((payload or {}).keys()))
    add("L3.live_source_hash", (payload or {}).get("provenance", {}).get("source_hash") == recomputed,
        claimed=(payload or {}).get("provenance", {}).get("source_hash"),
        recomputed=recomputed,
        local_snapshot_sha256=gates.sha256_text(
            (PKG / "report_5347.md").read_text(encoding="utf-8")))
    struct, struct_ok = gates.structure_gate(payload, pkg=CONTRACT)
    add("L4.structure_gate", struct_ok, gates=struct)
    ev, ev_ok, stats = gates.evidence_gate(payload, source_md, expected_report_id="5347")
    add("L5.evidence_gate", ev_ok, gates=ev, stats=stats)
    tags = published.get("tags") or []
    add("L6.channel_identity", TAG in tags and published.get("title") == TITLE,
        title=published.get("title"), has_tag=TAG in tags, tags=tags)

    ok = all(c["ok"] for c in checks)
    doc = {"ok": ok, "published_report_id": args.report_id, "checks": checks,
           "live_source_chars": len(source_md),
           "note": ("0 claim 时证据门为空真：stats.locator_rate=None，"
                    "不得引用为定位率 100%")}
    (PKG / "live_gate.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
    print(json.dumps({"ok": ok, "published_report_id": args.report_id,
                      "checks": {c["check"]: c["ok"] for c in checks},
                      "live_source_chars": len(source_md), "stats": stats},
                     ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())