#!/usr/bin/env python3
"""Post-submission verification: the published KF-RESULT report must carry exactly one
json fence that is byte-identical (semantically) to kf_result.json, and its tags must
declare the work package.  Also confirms the source hash the envelope claims still
recomputes from report 1226's live markdown.
"""
import hashlib
import json
import os
import re
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
PKG = "docs/kf/wp-1226-01"


def login():
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    return d.get("access_token") or d.get("token")


def get(path, token):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    tok = login()
    # 1) source hash still recomputes from the live source report
    src = get("/tensor/reports/1226", tok)
    src = src.get("data", src)
    live = "sha256:" + hashlib.sha256(src["markdown"].encode("utf-8")).hexdigest()
    kf = json.load(open(f"{PKG}/kf_result.json", encoding="utf-8"))
    print("source live hash:", live)
    print("envelope hash  :", kf["provenance"]["source_hash"], "match:", live == kf["provenance"]["source_hash"])

    # 2) the published report round-trips
    rep = get("/tensor/reports/14603", tok)
    rep = rep.get("data", rep)
    md = rep["markdown"]
    fences = re.findall(r"```json\n(.*?)\n```", md, re.S)
    print("published title:", rep["title"], "| tags:", rep["tags"])
    print("json fences:", len(fences), "| figures:", [f.get("name") for f in (rep.get("figures") or [])])
    assert len(fences) == 1, fences
    embedded = json.loads(fences[0])
    print("embedded == kf_result.json:", embedded == kf)
    assert embedded == kf
    assert "kf-wp:wp-1226-01" in rep["tags"]
    assert rep["title"] == "KF-RESULT wp-1226-01"
    assert embedded["provenance"]["source_hash"] == live
    print("OK: published report 14603 verified")


if __name__ == "__main__":
    main()