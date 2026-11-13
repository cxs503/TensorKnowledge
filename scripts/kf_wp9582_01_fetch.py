#!/usr/bin/env python3
"""wp-9582-01: fetch report 9582 markdown from the platform API and pin its bytes.

Registration-only工序: this script does not interpret the report, it only
(a) authenticates, (b) pulls the `markdown` field, (c) measures chars/bytes/sha256
and (d) writes an untouched copy to runs/wp-9582-01/source_9582.md so that every
later step re-reads the same bytes instead of a transcript.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ID = "9582"
RUN_DIR = ROOT / "runs" / "wp-9582-01"
SOURCE_COPY = RUN_DIR / ("source_%s.md" % REPORT_ID)
META_COPY = RUN_DIR / ("source_%s_meta.json" % REPORT_ID)


def _token() -> str:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps({
        "username": os.environ["TENSOR_AGENT_USER"],
        "password": os.environ["TENSOR_AGENT_PASS"],
    }).encode()
    req = urllib.request.Request(base + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    for k in ("access_token", "token", "accessToken"):
        if k in d:
            return d[k]
    raise SystemExit("no token field in login response: %s" % sorted(d))


def main() -> int:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(base + "/tensor/reports/" + REPORT_ID,
                                 headers={"Authorization": "Bearer " + _token()})
    with urllib.request.urlopen(req, timeout=120) as r:
        rec = json.load(r)
    md = rec["markdown"]
    raw = md.encode("utf-8")
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.write_bytes(raw)          # byte-exact copy, no newline added
    meta = {
        "report_id": REPORT_ID,
        "chars": len(md),
        "bytes_utf8": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "title": rec.get("title"),
        "scenario_key": rec.get("scenario_key"),
        "tags": rec.get("tags"),
        "figures": rec.get("figures") or [],
        "record_keys": sorted(rec.keys()),
    }
    META_COPY.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: meta[k] for k in ("chars", "bytes_utf8", "sha256", "title", "scenario_key")},
                     ensure_ascii=False, indent=2))
    print("figures:", len(meta["figures"]), "record_keys:", meta["record_keys"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())