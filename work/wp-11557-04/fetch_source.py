#!/usr/bin/env python3
"""Fetch report 11557 markdown from the platform API and pin its sha256.

Zero-hand-copy: the source text is written verbatim to source.md; the hash is
recomputed locally from those exact bytes and compared against the contract's
declared source_hash.
"""
import hashlib
import json
import os
import pathlib
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]
DECLARED = "sha256:471f8b21be2b8a4971dd416952c6f05a3db17c9031efcc7407fc488ae78b1cb3"
OUT = pathlib.Path(__file__).resolve().parent


def req(path, data=None, token=None):
    url = BASE + path
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(url, data=body, method="POST" if body else "GET")
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode())


tok = req("/auth/login", {"username": USER, "password": PASS})
tok = tok.get("access_token") or tok.get("token")
rec = req("/tensor/reports/11557", token=tok)
if "data" in rec and isinstance(rec["data"], dict):
    rec = rec["data"]

md = rec["markdown"]
raw = md.encode("utf-8")
h = "sha256:" + hashlib.sha256(raw).hexdigest()

(OUT / "source.md").write_bytes(raw)
meta = {
    "report_id": str(rec.get("id", "11557")),
    "title": rec.get("title"),
    "scenario_key": rec.get("scenario_key"),
    "tags": rec.get("tags"),
    "status": rec.get("status"),
    "chars": len(md),
    "bytes": len(raw),
    "sha256_recomputed": h,
    "sha256_declared": DECLARED,
    "hash_match": h == DECLARED,
}
(OUT / "source_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(meta, ensure_ascii=False, indent=2))