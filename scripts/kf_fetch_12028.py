#!/usr/bin/env python3
"""Fetch report 12028 markdown + metadata from the platform API and pin its sha256.

Outputs (inside worktree):
  work/wp-12028-01/source/report_12028.json   raw API response
  work/wp-12028-01/source/report_12028.md     markdown bytes as stored (utf-8)
  work/wp-12028-01/source/markdown.sha256     sha256 of those markdown bytes
"""
import hashlib
import json
import os
import pathlib
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]

REPORT_ID = "12028"
DECLARED = "sha256:69846e9d0680b8a1c5db5c607b9a5bf4a0ba2e6103b1d193a6a5d5e83e0ec29f"

OUT = pathlib.Path("work/wp-12028-01/source")


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
    rep = get("/tensor/reports/" + REPORT_ID, token)
    (OUT / "report_12028.json").write_text(
        json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    data = rep.get("data", rep)
    md = data["markdown"]
    raw = md.encode("utf-8")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    (OUT / "report_12028.md").write_bytes(raw)
    (OUT / "markdown.sha256").write_text(digest + "\n", encoding="utf-8")
    print("title:", data.get("title"))
    print("id:", data.get("id"))
    print("scenario_key:", data.get("scenario_key"))
    print("chars(py len):", len(md), "bytes:", len(raw))
    print("sha256:", digest)
    print("declared source_hash:", DECLARED)
    print("hash_match:", digest == DECLARED)
    print("keys:", sorted(data.keys()))


if __name__ == "__main__":
    main()