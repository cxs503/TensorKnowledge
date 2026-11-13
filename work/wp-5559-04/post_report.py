#!/usr/bin/env python3
"""Publish the wp-5559-04 review report (paper-grade six-part markdown + one figure)."""
import json, os, urllib.request
tok = open("/tmp/tok.txt").read().strip()
base = os.environ["TENSOR_API_BASE"]
payload = json.load(open("/tmp/report_5559_04.json"))
req = urllib.request.Request(base + "/tensor/reports", data=json.dumps(payload).encode(),
                             headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"},
                             method="POST")
try:
    r = json.load(urllib.request.urlopen(req, timeout=120))
    print(json.dumps({k: r.get(k) for k in ("id", "title", "status", "tags")}, ensure_ascii=False))
    json.dump(r, open("work/wp-5559-04/report_create_response.json", "w"), ensure_ascii=False, indent=1)
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read()[:600].decode("utf-8", "replace"))
    raise
