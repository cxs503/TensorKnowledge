#!/usr/bin/env python3
import sys
"""Fetch report 11621 markdown + metadata from platform API and pin its sha256.

Outputs (inside worktree):
  runs/wp-11621-01/report_11621.json   raw API response
  runs/wp-11621-01/report_11621.md     markdown payload
"""
import hashlib
import json
import os
import pathlib
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]

OUT = pathlib.Path("runs/wp-11621-01")


def post(path, body, token=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def get(path, token):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tok = post("/auth/login", {"username": USER, "password": PASS})
    token = tok.get("access_token") or tok.get("token")
    assert token, f"no token in login response keys={list(tok)}"
    rep = get("/tensor/reports/11621", token)
    (OUT / "report_11621.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    data = rep.get("data", rep)
    md = data["markdown"]
    raw = md.encode("utf-8")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    (OUT / "report_11621.md").write_bytes(raw)
    (OUT / "markdown.sha256").write_text(digest + "\n", encoding="utf-8")
    print("title:", data.get("title"))
    print("id:", data.get("id"))
    print("chars(py len):", len(md), "bytes:", len(raw))
    print("sha256:", digest)
    print("declared source_hash: sha256:89a6a0828d4feddbc1c1ee81e80cc7c844ea234c01c2efeec215fcd7ed54dafb")
    print("keys:", sorted(data.keys()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
