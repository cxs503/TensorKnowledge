#!/usr/bin/env python3
"""Fetch report 7545 markdown from the Tensor platform API and verify its sha256.

Env: TENSOR_API_BASE (default http://127.0.0.1:8010), TENSOR_AGENT_USER, TENSOR_AGENT_PASS
Output: work/kf_wp7545/report_7545.json  (raw API record) and report_7545.md (markdown bytes)
"""
import hashlib
import json
import os
import sys
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010").rstrip("/")
USER = os.environ.get("TENSOR_AGENT_USER", "")
PASS = os.environ.get("TENSOR_AGENT_PASS", "")
EXPECT = "sha256:84010e0091071d5971888931b9d6b73fc3bba4f217dcd17ab739979fc1c5ae60"

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "work", "kf_wp7545")


def _post(path, payload, token=None):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(BASE + path, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _get(path, token):
    req = urllib.request.Request(BASE + path, method="GET")
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    os.makedirs(OUT, exist_ok=True)
    tok = None
    for body in ({"username": USER, "password": PASS}, {"grant_type": "password", "username": USER, "password": PASS}):
        try:
            d = _post("/auth/login", body)
            tok = d.get("access_token") or d.get("token")
            if tok:
                break
        except Exception as e:  # noqa: BLE001
            print("login attempt failed:", e, file=sys.stderr)
    if not tok:
        print("LOGIN_FAILED", file=sys.stderr)
        return 2

    rec = _get("/tensor/reports/7545", tok)
    md = rec.get("markdown")
    if md is None and isinstance(rec.get("data"), dict):
        rec = rec["data"]
        md = rec.get("markdown")
    if md is None:
        print("NO_MARKDOWN_FIELD keys=%s" % list(rec)[:20], file=sys.stderr)
        return 3

    raw = md.encode("utf-8")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    with open(os.path.join(OUT, "report_7545.json"), "w") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "report_7545.md"), "wb") as f:
        f.write(raw)
    print(json.dumps({"chars": len(md), "bytes": len(raw), "sha256": digest,
                      "matches_contract": digest == EXPECT}, ensure_ascii=False))
    return 0 if digest == EXPECT else 4


if __name__ == "__main__":
    sys.exit(main())