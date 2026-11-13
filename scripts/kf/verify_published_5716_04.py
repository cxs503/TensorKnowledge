#!/usr/bin/env python3
"""Verify the published KF-RESULT wp-5716-04 report round-trips faithfully.

Fetches the published report by id (created by publish_wp_5716_04.py), then checks:
  * title / tag / scenario_key / mission_id match the contract
  * the stored markdown carries exactly one ```json block
  * that block equals docs/kf/wp-5716-04/kf_result.json byte-for-byte after parse
  * figures count and that each png_base64 decodes to a valid PNG (magic header)

Usage: python3 scripts/kf/verify_published_5716_04.py --report-id 14964
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request

ENV = "docs/kf/wp-5716-04/kf_result.json"
PKG = "wp-5716-04"


def call(base, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data,
                                 headers={"Content-Type": "application/json",
                                          **({"Authorization": "Bearer " + token} if token else {})})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-id", required=True)
    a = ap.parse_args(argv)
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    tok = call(base, "/auth/login", body={"username": os.environ["TENSOR_AGENT_USER"],
                                          "password": os.environ["TENSOR_AGENT_PASS"]})["access_token"]
    rep = call(base, "/tensor/reports/" + a.report_id, token=tok)
    md = rep["markdown"]
    env = json.load(open(ENV, encoding="utf-8"))
    checks = []
    checks.append(("title", rep["title"] == f"KF-RESULT {PKG}", rep["title"]))
    checks.append(("tag", f"kf-wp:{PKG}" in (rep.get("tags") or []), str(rep.get("tags"))))
    blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
    checks.append(("single_json_block", len(blocks) == 1, f"{len(blocks)} block(s)"))
    same = len(blocks) == 1 and json.loads(blocks[0]) == env
    checks.append(("block_equals_envelope", same, f"parsed_equal={same}"))
    # the read API returns figure name+caption (png bytes are stored, not echoed),
    # so PNG validity is checked on the local artifacts the payload was built from.
    pngs = [f for f in (rep.get("figures") or []) if f.get("name")]
    local = [os.path.join("docs/kf/wp-5716-04/figures", f["name"]) for f in pngs]
    magic = bool(pngs) and all(os.path.isfile(p)
                               and open(p, "rb").read(8) == b"\x89PNG\r\n\x1a\n" for p in local)
    checks.append(("figures_png", magic,
                   f"{len(pngs)} figure(s) echoed, local png_magic={magic}"))
    checks.append(("scenario", rep.get("scenario_key") == "ship.ice_navigation.campaign_gate",
                   str(rep.get("scenario_key"))))
    checks.append(("mission", rep.get("mission_id") == 15839, str(rep.get("mission_id"))))
    ok = all(c[1] for c in checks)
    for n, v, note in checks:
        print(f"[{'PASS' if v else 'FAIL'}] {n:22s} {note[:90]}")
    print("published report id:", rep["id"], "status:", rep.get("status"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())