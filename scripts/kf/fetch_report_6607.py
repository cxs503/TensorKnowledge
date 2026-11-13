#!/usr/bin/env python3
"""Fetch report 6607 markdown + metadata and pin its sha256 (wp-6607-04 source pinning).

Outputs (inside worktree):
  work/wp-6607-04/source/report_6607.json   raw API response
  work/wp-6607-04/source/report_6607.md     markdown bytes, verbatim
  work/wp-6607-04/source/markdown.sha256    sha256 of markdown utf-8 bytes
"""
import hashlib
import json
import os
import pathlib
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]

OUT = pathlib.Path("work/wp-6607-04/source")
DECLARED = "sha256:b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1"


def post(path, body, token=None):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
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
    rep = get("/tensor/reports/6607", token)
    (OUT / "report_6607.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    data = rep.get("data", rep)
    md = data["markdown"]
    raw = md.encode("utf-8")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    (OUT / "report_6607.md").write_bytes(raw)
    (OUT / "markdown.sha256").write_text(digest + "\n", encoding="utf-8")
    print("title:", data.get("title"))
    print("id:", data.get("id"))
    print("chars(py len):", len(md), "bytes:", len(raw))
    print("sha256:", digest)
    print("declared:", DECLARED, "MATCH" if digest == DECLARED else "MISMATCH")
    print("keys:", sorted(data.keys()))


if __name__ == "__main__":
    main()