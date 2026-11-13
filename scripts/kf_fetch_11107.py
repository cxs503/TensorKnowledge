#!/usr/bin/env python3
"""Fetch report 11107 markdown from the platform API and cache it under runs/wp-11107-01/.

Never hardcodes credentials: uses TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE.
Writes: runs/wp-11107-01/report_11107.json (raw payload), runs/wp-11107-01/source_11107.md
"""
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

OUT = pathlib.Path(__file__).resolve().parents[1] / "runs" / "wp-11107-01"
OUT.mkdir(parents=True, exist_ok=True)
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
RID = "11107"


def _req(url, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def login():
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not user or not pwd:
        return None
    for path in ("/tensor/auth/login", "/auth/login", "/tensor/login"):
        try:
            d = _req(BASE + path, {"username": user, "password": pwd})
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def main():
    tok = login()
    d = _req(BASE + "/tensor/reports/" + RID, token=tok)
    rec = d.get("data", d) if isinstance(d, dict) else d
    if isinstance(rec, list):
        rec = rec[0]
    (OUT / ("report_%s.json" % RID)).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    md = rec.get("markdown") or ""
    if not md:
        print("EMPTY MARKDOWN", file=sys.stderr)
        return 2
    (OUT / ("source_%s.md" % RID)).write_text(md, encoding="utf-8")
    print("chars=%d bytes_utf8=%d lines=%d" % (len(md), len(md.encode("utf-8")),
                                               len(md.rstrip("\n").split("\n"))))
    print("sha256=" + hashlib.sha256(md.encode("utf-8")).hexdigest())
    print("record_keys=" + ",".join(sorted(rec.keys())))
    print("title=" + str(rec.get("title")))
    print("scenario_key=" + str(rec.get("scenario_key")))
    print("mission_id=" + str(rec.get("mission_id")))
    print("status=" + str(rec.get("status")))
    print("tags=" + json.dumps(rec.get("tags"), ensure_ascii=False))
    print("figures=" + json.dumps(rec.get("figures"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())