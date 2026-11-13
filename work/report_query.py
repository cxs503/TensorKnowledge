#!/usr/bin/env python3
"""Small helper: list/search tensor reports; creds from env only."""
import json
import os
import sys
import urllib.parse
import urllib.request

BASE = os.environ["TENSOR_API_BASE"]


def _call(url, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


tok = _call(BASE + "/auth/login",
            {"username": os.environ["TENSOR_AGENT_USER"],
             "password": os.environ["TENSOR_AGENT_PASS"]})
tok = tok.get("access_token") or tok.get("token") or tok["data"]["access_token"]

mode = sys.argv[1]
if mode == "search":
    kw = sys.argv[2]
    r = _call(BASE + "/tensor/reports?limit=200&q=" + urllib.parse.quote(kw), token=tok)
elif mode == "get":
    r = _call(BASE + "/tensor/reports/" + sys.argv[2], token=tok)
elif mode == "missions":
    r = _call(BASE + "/tensor/reports?limit=200&mission_id=" + sys.argv[2], token=tok)
else:
    r = _call(BASE + "/" + mode, token=tok)

if isinstance(r, dict) and "items" in r:
    for it in r["items"]:
        print(it.get("id"), "|", it.get("mission_id"), "|", it.get("title"), "|", it.get("tags"))
    print("total", r.get("total"), "keys", list(r))
else:
    print(json.dumps(r, ensure_ascii=False)[:2000])