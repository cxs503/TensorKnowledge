#!/usr/bin/env python3
"""Fetch report 12595 markdown + metadata from platform API and pin its sha256.

Outputs (inside worktree):
  work/wp-12595-01/source/report_12595.json   raw API response
  work/wp-12595-01/source/report_12595.md     markdown bytes (utf-8)
"""
import hashlib
import json
import os
import pathlib
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]

OUT = pathlib.Path("work/wp-12595-01/source")
DECLARED = "sha256:1233e5e4fece836d70b124a36a82438a1e48dbfddfc168b14f4c1f7efd7a08ce"


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
    rep = get("/tensor/reports/12595", token)
    (OUT / "report_12595.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    data = rep.get("data", rep)
    md = data["markdown"]
    raw = md.encode("utf-8")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    (OUT / "report_12595.md").write_bytes(raw)
    print("id:", data.get("id"))
    print("title:", data.get("title"))
    print("scenario_key:", data.get("scenario_key"))
    print("chars(py len):", len(md), "bytes:", len(raw))
    print("sha256:", digest)
    print("declared source_hash:", DECLARED)
    print("hash_match:", digest == DECLARED)
    print("keys:", sorted(data.keys()))


if __name__ == "__main__":
    main()
