#!/usr/bin/env python3
"""Fetch report 6551 from the platform API and store a byte-exact source copy.

Used by scripts/kf_wp6551_register_assets.py; kept as a separate entry point so a
reviewer can pull the raw markdown without running the registration logic.

    python3 scripts/kf_wp6551_fetch.py            # -> runs/wp-6551-01/source_6551.md
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ID = "6551"
OUT = ROOT / "runs" / ("wp-%s-01" % REPORT_ID) / ("source_%s.md" % REPORT_ID)


def main() -> int:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(base + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    tok = json.load(urllib.request.urlopen(req))["access_token"]
    req = urllib.request.Request(base + "/tensor/reports/" + REPORT_ID,
                                 headers={"Authorization": "Bearer " + tok})
    rec = json.load(urllib.request.urlopen(req))
    md = rec.get("markdown") or ""
    raw = md.encode("utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(raw)
    print(json.dumps({"report_id": REPORT_ID, "chars": len(md), "bytes_utf8": len(raw),
                      "sha256": hashlib.sha256(raw).hexdigest(),
                      "title": rec.get("title"), "scenario_key": rec.get("scenario_key"),
                      "figures": len(rec.get("figures") or []),
                      "tags": rec.get("tags"), "path": str(OUT)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())