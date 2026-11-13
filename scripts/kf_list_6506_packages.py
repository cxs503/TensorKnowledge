#!/usr/bin/env python3
"""Independent-review support: list KF work-package reports for report_id 6506.

Read-only queries against the platform API. Prints, for each report whose tags
mention `kf-wp:wp-6506-*`, the id/title/tags so the reviewer can establish that
upstream packages (01/02/03) exist and with what delivery status. Discovery only:
no producer explanation is fetched (titles/tags only, body excluded).

Usage:
    python3 scripts/kf_list_6506_packages.py
"""
import json
import os
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")


def _req(path, data=None, token=None):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = "Bearer " + token
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(BASE + path, data=body, headers=h,
                               method="POST" if body else "GET")
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode())


def main():
    tok = _req("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                               "password": os.environ["TENSOR_AGENT_PASS"]})
    tok = tok.get("access_token") or tok.get("token") or tok.get("data", {}).get("access_token")
    rows = _req("/tensor/reports?limit=400", token=tok)
    items = rows.get("items") if isinstance(rows, dict) else rows
    hits = []
    for it in items or []:
        tags = it.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        if any(str(t).startswith("kf-wp:wp-6506") for t in tags):
            hits.append({"id": it.get("id"), "title": it.get("title"),
                         "tags": [t for t in tags if str(t).startswith("kf-wp")]})
    hits.sort(key=lambda r: str(r["id"]))
    print(json.dumps(hits, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()