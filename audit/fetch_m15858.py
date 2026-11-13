#!/usr/bin/env python3
"""Fetch m15858 mission record + reports + benchmark cases for board audit."""
import json, os, urllib.request

BASE = os.environ["TENSOR_API_BASE"]
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]

def req(method, path, body=None, tok=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if tok:
        r.add_header("Authorization", "Bearer " + tok)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"_error": str(e)}

tok = req("POST", "/auth/login", {"username": USER, "password": PASS}).get("access_token", "")
print("TOKEN_LEN", len(tok))

out = {}
out["mission"] = req("GET", "/missions/15858", tok=tok)
out["reports"] = req("GET", "/tensor/reports?mission_id=15858", tok=tok)
out["bench"] = req("GET", "/tensor/benchmark-cases?anchor_slug=KBM-RCI-S2-SCHEMA", tok=tok)
with open("/root/tp-agent/work/m15887/audit/fetched_m15858.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("saved")
for k, v in out.items():
    s = json.dumps(v, ensure_ascii=False)
    print(k, "len", len(s))
