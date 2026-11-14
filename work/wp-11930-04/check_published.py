#!/usr/bin/env python3
"""Round-trip check of the published KF report: re-fetch it and re-parse the single JSON block."""
import json
import os
import re
import urllib.request

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
RID = "18074"


def token():
    req = urllib.request.Request(BASE + "/auth/login",
                                 data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                                                  "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
                                 method="POST")
    req.add_header("Content-Type", "application/json")
    d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    return d.get("access_token") or d.get("token") or d["data"]["access_token"]


req = urllib.request.Request(BASE + "/tensor/reports/" + RID)
req.add_header("Authorization", "Bearer " + token())
rec = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
rec = rec.get("data", rec)
md = rec["markdown"]
blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
kf = json.loads(blocks[0])
print(json.dumps({"id": rec.get("id"), "title": rec.get("title"), "tags": rec.get("tags"),
                  "json_blocks": len(blocks),
                  "package_id": kf["package_id"], "task_type": kf["task_type"],
                  "report_id": kf["report_id"],
                  "source_hash": kf["provenance"]["source_hash"],
                  "outputs": sorted(kf["outputs"]),
                  "figures": [f.get("name") for f in (rec.get("figures") or [])]},
                 ensure_ascii=False, indent=1))