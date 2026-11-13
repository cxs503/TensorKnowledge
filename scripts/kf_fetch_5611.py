#!/usr/bin/env python3
"""Fetch full report record 5611 (markdown + figures + metadata) for review.

Writes the raw record as returned by the API (no normalisation) plus the
markdown bytes, then prints the identity triple the review is pinned to.
"""
import hashlib
import json
import os
import pathlib
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
OUTDIR = pathlib.Path(__file__).resolve().parents[1] / "work" / "kf-wp-5611"
REPORT_ID = "5611"


def _req(url, data=None, token=None):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    tok = _req(BASE + "/auth/login", json.dumps({
        "username": os.environ["TENSOR_AGENT_USER"],
        "password": os.environ["TENSOR_AGENT_PASS"],
    }).encode())
    token = tok.get("access_token") or tok.get("token")
    rec = _req(BASE + "/tensor/reports/" + REPORT_ID, token=token)
    if isinstance(rec, list):
        rec = rec[0]
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "record_5611.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    md = rec["markdown"]
    (OUTDIR / "source_5611.md").write_text(md, encoding="utf-8")
    print(json.dumps({
        "markdown_sha256": "sha256:" + hashlib.sha256(md.encode()).hexdigest(),
        "chars": len(md),
        "bytes_utf8": len(md.encode()),
        "figures": [f.get("name") for f in (rec.get("figures") or [])],
        "figure_count": len(rec.get("figures") or []),
        "title": rec.get("title"),
        "scenario_key": rec.get("scenario_key"),
        "status": rec.get("status"),
        "tags": rec.get("tags"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()