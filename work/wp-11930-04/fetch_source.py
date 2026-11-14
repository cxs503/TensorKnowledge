#!/usr/bin/env python3
"""Fetch report 11930 markdown fresh from the platform (reviewer-side, no cached producer copy).

Writes work/wp-11930-04/source_report.md and prints sha256/char/byte counts.
"""
import hashlib
import json
import os
import urllib.request

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
REPORT_ID = "11930"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source_report.md")


def token():
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps({
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        }).encode(),
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    return d.get("access_token") or d.get("token") or d["data"]["access_token"]


def main():
    req = urllib.request.Request(BASE + "/tensor/reports/" + REPORT_ID)
    req.add_header("Authorization", "Bearer " + token())
    rec = json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
    rec = rec.get("data", rec)
    md = rec["markdown"]
    b = md.encode("utf-8")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(md)
    with open(OUT + ".json", "w", encoding="utf-8") as f:
        json.dump({"id": rec.get("id"), "title": rec.get("title"),
                   "sha256": "sha256:" + hashlib.sha256(b).hexdigest(),
                   "chars": len(md), "bytes_utf8": len(b)}, f, ensure_ascii=False)
    print(json.dumps({"title": rec.get("title"),
                      "sha256": "sha256:" + hashlib.sha256(b).hexdigest(),
                      "chars": len(md), "bytes_utf8": len(b)}, ensure_ascii=False))


if __name__ == "__main__":
    main()