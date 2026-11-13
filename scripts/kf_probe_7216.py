#!/usr/bin/env python3
"""Probe platform for wp-7216-* sibling packages/reports and upstream knowledge objects."""
import json
import os
import urllib.parse
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")


def login():
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    return json.load(urllib.request.urlopen(req, timeout=60))["access_token"]


def get(path, token, params=None):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {e}"}


t = login()
for q in [
    ("/tensor/reports", {"tag": "kf-wp:wp-7216-01"}),
    ("/tensor/reports", {"q": "wp-7216"}),
    ("/tensor/work-packages", {"report_id": "7216"}),
    ("/tensor/packages", {"report_id": "7216"}),
    ("/tensor/knowledge-objects", {"report_id": "7216"}),
]:
    r = get(q[0], t, q[1])
    s = json.dumps(r, ensure_ascii=False)
    print("==", q[0], q[1], "=>", s[:700], "\n")