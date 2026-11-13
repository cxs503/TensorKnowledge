#!/usr/bin/env python3
"""Probe API routes for mission/benchmark/verdict endpoints."""
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
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"_raw": str(e)}
    except Exception as e:
        return None, {"_error": str(e)}

tok = req("POST", "/auth/login", {"username": USER, "password": PASS})[1].get("access_token", "")
print("tok", len(tok))

# openapi
st, body = req("GET", "/openapi.json")
print("openapi", st)
if st == 200:
    paths = sorted(body.get("paths", {}).keys())
    print("n_paths", len(paths))
    for p in paths:
        if any(k in p for k in ("mission", "benchmark", "verdict", "maturity", "report", "gate")):
            print(" ", p)
    json.dump(body, open("/root/tp-agent/work/m15887/audit/openapi.json", "w"))
