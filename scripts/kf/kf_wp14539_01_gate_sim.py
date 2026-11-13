#!/usr/bin/env python3
"""wp-14539-01 · independent re-check of the delivered envelope, from a FRESH fetch.

Deliberately does not trust the builder's own bookkeeping: it re-downloads report 14539, recomputes
sha256, and re-resolves every locator against those fresh bytes (offset + verbatim slice + line map),
then checks the envelope-level rules a platform gate would apply. Writes gate_sim.json next to the
other artifacts.

Usage: python3 scripts/kf/kf_wp14539_01_gate_sim.py
"""
from __future__ import annotations

import bisect
import hashlib
import json
import struct
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs/kf/wp-14539-01"
REPORT_ID = "14539"
CONTRACT_HASH = "d2dfc774d825389350411f5562f457cd13f44b17e3d8cf5b3c8470c80677b82b"


def _req(url, token=None, data=None, ctype="application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode() or "null")


def main():
    import os
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    creds = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                        "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    d = _req(base + "/auth/login", data=creds)
    token = d.get("access_token") or d.get("token")
    rec = _req(base + "/tensor/reports/" + REPORT_ID, token)
    if isinstance(rec.get("data"), dict):
        rec = rec["data"]
    md = rec["markdown"]
    raw = md.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()

    manifest = json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))
    result = json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))

    starts = [0]
    for i, ch in enumerate(md):
        if ch == "\n":
            starts.append(i + 1)

    def line_of(pos):
        return bisect.bisect_right(starts, pos)

    checks = {}
    checks["fresh_hash_equals_contract"] = {
        "pass": digest == CONTRACT_HASH,
        "detail": "fresh GET recomputed sha256=%s" % digest,
    }
    checks["provenance_hash_equals_fresh"] = {
        "pass": result["provenance"]["source_hash"] == "sha256:" + digest
        and manifest["source"]["hash"] == digest,
        "detail": "envelope=%s manifest=%s fresh=%s" % (
            result["provenance"]["source_hash"], manifest["source"]["hash"], digest),
    }

    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
        if loc["method"] == "document":
            if not (s == 0 and e == len(md) and q in md):
                bad.append([a["asset_id"], "document"])
            continue
        if md[s:e] != q or q not in md:
            bad.append([a["asset_id"], "slice"])
        elif (line_of(s), line_of(e - 1)) != (loc["start_line"], loc["end_line"]):
            bad.append([a["asset_id"], "line"])
    checks["all_locators_resolve_on_fresh_bytes"] = {
        "pass": not bad,
        "detail": "%d locators re-resolved against the freshly fetched markdown; failures=%s"
                  % (len(manifest["assets"]), bad),
    }

    checks["claims_empty_and_unverified"] = {
        "pass": manifest["claims"] == [] and result["claims"] == []
        and all(c.get("status") != "verified" for c in result["claims"] + manifest["claims"]),
        "detail": "manifest.claims=%d, envelope.claims=%d, no 'verified' status anywhere"
                  % (len(manifest["claims"]), len(result["claims"])),
    }
    ids = {str(result["report_id"]), str(manifest["report_id"])}
    checks["single_report_id"] = {
        "pass": ids == {REPORT_ID},
        "detail": "report ids present in the envelope: %s" % sorted(ids),
    }
    checks["envelope_matches_committed_manifest"] = {
        "pass": result["outputs"]["asset_manifest.json"] == manifest,
        "detail": "outputs['asset_manifest.json'] equals docs/kf/wp-14539-01/asset_manifest.json",
    }
    png = OUT / "figures" / "wp-14539-01_asset_locator_map.png"
    dims = None
    if png.is_file() and png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", png.read_bytes()[16:24])
        dims = [w, h]
    checks["figure_is_png"] = {
        "pass": dims is not None,
        "detail": "figure %s: PNG signature ok, %s px, %d bytes" % (
            png.name, dims, png.stat().st_size if png.is_file() else 0),
    }

    out = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "report_id": REPORT_ID,
        "fresh_sha256": digest,
        "assets": len(manifest["assets"]),
        "checks": checks,
        "all_pass": all(c["pass"] for c in checks.values()),
        "note": "independent of the builder's verify step: everything is recomputed from a new GET",
    }
    (OUT / "gate_sim.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v["pass"] for k, v in checks.items()}, ensure_ascii=False))
    print("all_pass=%s" % out["all_pass"])
    return 0 if out["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())