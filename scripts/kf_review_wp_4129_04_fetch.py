#!/usr/bin/env python3
"""wp-4129-04 (04-independent-review): fetch report 4129 markdown independently.

Reviewer channel discipline: the only source of truth for the review is the
report markdown returned by the platform API.  Nothing produced by the
upstream worker (scripts/, docs/kf/*.md narrative) is used as evidence.

Outputs (inside worktree):
  work/wp-4129-04/source/report_4129.json    raw API response
  work/wp-4129-04/source/report_4129.md      markdown bytes (utf-8), verbatim
  work/wp-4129-04/source/markdown.sha256     sha256 of those bytes
"""
import hashlib
import json
import os
import pathlib
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]
OUT = pathlib.Path("work/wp-4129-04/source")
DECLARED = "sha256:8670fa44138a8835fac88bbc2722e7b0b8f11c9f87ce8fa728ac0971c2a0f155"
DECLARED_CHARS = 3969


def _req(path, body=None, token=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tok = _req("/auth/login", {"username": USER, "password": PASS})
    token = tok.get("access_token") or tok.get("token")
    assert token, f"no token in login response keys={list(tok)}"
    rep = _req("/tensor/reports/4129", token=token)
    (OUT / "report_4129.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    data = rep.get("data", rep)
    md = data["markdown"]
    raw = md.encode("utf-8")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    (OUT / "report_4129.md").write_bytes(raw)
    (OUT / "markdown.sha256").write_text(digest + "\n", encoding="utf-8")
    print("id:", data.get("id"))
    print("title:", data.get("title"))
    print("chars(py len):", len(md), "bytes:", len(raw))
    print("sha256:", digest)
    print("declared   :", DECLARED, "match:", digest == DECLARED)
    print("chars decl :", DECLARED_CHARS, "match:", len(md) == DECLARED_CHARS)


if __name__ == "__main__":
    main()