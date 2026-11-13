#!/usr/bin/env python3
"""Fetch report 13980 markdown from the platform API and pin its bytes/hash.

Zero hand-copy: the markdown is pulled straight from
GET $TENSOR_API_BASE/tensor/reports/13980 and written verbatim to
artifacts/wp-13980-01/source_markdown.md, then sha256-recomputed.
"""
import hashlib
import json
import os
import sys
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]
RID = "13980"
OUT = "artifacts/wp-13980-01"


def post(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    tok = post(BASE + "/auth/login", {"username": USER, "password": PASS})
    token = tok.get("access_token") or tok.get("token")
    if not token:
        print("login failed:", list(tok)[:8], file=sys.stderr)
        return 2
    rec = get(BASE + "/tensor/reports/" + RID, token)
    os.makedirs(OUT, exist_ok=True)
    md = rec["markdown"]
    raw = md.encode("utf-8")
    with open(os.path.join(OUT, "source_markdown.md"), "wb") as f:
        f.write(raw)
    meta = {
        "report_id": str(rec.get("id", RID)),
        "title": rec.get("title"),
        "scenario_key": rec.get("scenario_key"),
        "tags": rec.get("tags"),
        "mission_id": rec.get("mission_id"),
        "chars": len(md),
        "bytes_utf8": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "figure_count": len(rec.get("figures") or []),
        "figure_names": [f.get("name") for f in (rec.get("figures") or [])],
        "record_keys": sorted(rec.keys()),
    }
    with open(os.path.join(OUT, "source_meta.json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())