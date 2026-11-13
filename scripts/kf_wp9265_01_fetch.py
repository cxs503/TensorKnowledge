#!/usr/bin/env python3
"""wp-9265-01 helper: fetch report 9265 markdown from the platform API.

Scope guard: touches ONLY report_id=9265.

Usage: python3 scripts/kf_wp9265_01_fetch.py
Writes: runs/wp-9265-01/report_9265.json (raw payload), runs/wp-9265-01/source_9265.md
No credentials hardcoded: env TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS.
"""
import hashlib
import json
import os
import pathlib
import urllib.request

REPORT_ID = "9265"
OUT = pathlib.Path(__file__).resolve().parents[1] / "runs" / "wp-9265-01"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _req(url, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data)
    if data:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login():
    d = _req(BASE + "/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                    "password": os.environ["TENSOR_AGENT_PASS"]})
    return d.get("access_token") or (d.get("data") or {}).get("access_token")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tok = login()
    payload = _req(BASE + "/tensor/reports/" + REPORT_ID, token=tok)
    (OUT / "report_9265.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    rec = payload.get("data", payload) if isinstance(payload, dict) else payload
    md = rec["markdown"]
    (OUT / "source_9265.md").write_text(md)
    b = md.encode("utf-8")
    print(json.dumps({"chars": len(md), "bytes": len(b),
                      "sha256": hashlib.sha256(b).hexdigest(),
                      "title": rec.get("title"), "scenario_key": rec.get("scenario_key"),
                      "figures": rec.get("figures"), "tags": rec.get("tags"),
                      "status": rec.get("status"), "mission_id": rec.get("mission_id")},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()