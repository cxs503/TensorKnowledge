#!/usr/bin/env python3
"""wp-14539-01 · step 1: fetch source report 14539 verbatim + structural inventory (no extraction).

Writes (inside the worktree only):
  docs/kf/wp-14539-01/source/markdown.txt   verbatim markdown bytes (utf-8)
  docs/kf/wp-14539-01/source/record.json    record metadata subset used for registration
and prints a structural summary (headers / tables / fences / path-like tokens) so that the
asset registry is derived from the bytes, never from memory.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

REPORT_ID = "14539"
OUT = Path(__file__).resolve().parents[2] / "docs/kf/wp-14539-01/source"


def _req(url, token=None, data=None, ctype="application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login():
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    try:
        d = _req(base + "/auth/login", data=json.dumps(
            {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]}).encode())
    except urllib.error.HTTPError:
        d = _req(base + "/auth/login",
                 data=urllib.parse.urlencode({"username": os.environ["TENSOR_AGENT_USER"],
                                              "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
                 ctype="application/x-www-form-urlencoded")
    tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit("login returned no token: %s" % sorted(d))
    return base, tok


def main():
    base, tok = login()
    d = _req(base + "/tensor/reports/" + REPORT_ID, tok)
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    if str(d.get("id")) != REPORT_ID:
        raise SystemExit("report_id mismatch: %r" % d.get("id"))
    md = d["markdown"]
    raw = md.encode("utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "markdown.txt").write_bytes(raw)
    keep = {k: d.get(k) for k in ("id", "title", "scenario_key", "mission_id", "tags", "created_at", "updated_at")}
    figs = d.get("figures") or []
    keep["figures"] = [{"name": f.get("name"), "caption": f.get("caption"),
                        "png_base64_len": len(f.get("png_base64") or "")} for f in figs]
    (OUT / "record.json").write_text(json.dumps(keep, ensure_ascii=False, indent=2), encoding="utf-8")

    print("title:", d.get("title"))
    print("chars=%d bytes=%d sha256=%s" % (len(md), len(raw), hashlib.sha256(raw).hexdigest()))
    print("tags:", d.get("tags"), "| figures:", len(figs), [(f.get("name"), len(f.get("png_base64") or "")) for f in figs])
    print("\n-- headings --")
    for i, ln in enumerate(md.splitlines(), 1):
        if ln.lstrip().startswith("#") or ln.lstrip().startswith("**"):
            print(i, ln[:150])
    print("\n-- tables --")
    lines = md.splitlines()
    for i, ln in enumerate(lines, 1):
        if ln.startswith("|"):
            print(i, ln[:160])
    print("\n-- fences --")
    for i, ln in enumerate(lines, 1):
        if ln.strip().startswith("```"):
            print(i, ln[:120])
    print("\n-- path-like / inline-code tokens (unique) --")
    toks = set()
    for m in re.finditer(r"`([^`\n]+)`", md):
        t = m.group(1).strip()
        if re.search(r"\.(py|json|csv|yaml|yml|md|png|txt)$|^[\w./-]+/[\w./-]+$", t):
            toks.add(t)
    for t in sorted(toks):
        print("  ", t)
    print("\n-- api-ish tokens --")
    for t in sorted({m.group(1).strip() for m in re.finditer(r"`([^`\n]+)`", md)
                     if re.search(r"(/api/|GET |POST |:[0-9]{4})", m.group(1))}):
        print("  ", t)


if __name__ == "__main__":
    main()