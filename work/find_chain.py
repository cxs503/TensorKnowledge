#!/usr/bin/env python3
"""Find reports whose title/tags mention a token (client-side filter; API q is ignored)."""
import json
import os
import urllib.request

BASE = os.environ["TENSOR_API_BASE"]


def _call(url, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


tok = _call(BASE + "/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                   "password": os.environ["TENSOR_AGENT_PASS"]})
tok = tok.get("access_token") or tok.get("token") or tok["data"]["access_token"]

needle = "5347"
hits = []
total = None
for off in range(0, 3000, 200):
    r = _call(BASE + "/tensor/reports?limit=200&offset=%d" % off, token=tok)
    total = r.get("total")
    items = r.get("items", [])
    if not items:
        break
    for it in items:
        blob = (str(it.get("title")) + " " + " ".join(it.get("tags") or [])).lower()
        if needle in blob:
            hits.append(it)
    if len(items) < 200:
        break
print("total reports:", total, "scanned:", off + len(items))
for it in hits:
    print(it["id"], "|", it.get("mission_id"), "|", it.get("title"), "|", it.get("tags"))