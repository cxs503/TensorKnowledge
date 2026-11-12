#!/usr/bin/env python3
"""Post-publication check for wp-5761-01.

Confirms, against the live platform, that
  1. the published report carries exactly one json block and it equals docs/kf/wp-5761-01/kf_result.json;
  2. the source report (5761) markdown bytes are unchanged after our work (non-interference);
  3. which fields the platform actually persisted for figures (payload vs metadata only).

Usage: python3 scripts/kf/check_published_5761.py [published_report_id]
Exit 0 = all assertions hold.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PKG = "wp-5761-01"
OUT = REPO / "docs" / "kf" / PKG
SOURCE_ID = "5761"
CONTRACT_HASH = "06f7e6a9d2164c64a916d4f11cc0e117af97766de133438d10fc884a35c2c4d7"
BASE = os.environ["TENSOR_API_BASE"].rstrip("/")


def _req(url, token=None, data=None, ctype="application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login():
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    for path in ("/tensor/auth/login", "/auth/login"):
        try:
            d = _req(BASE + path, data=body)
        except Exception:  # noqa: BLE001
            continue
        tok = d.get("access_token") or d.get("token")
        if tok:
            return tok
    form = urllib.parse.urlencode({"username": os.environ["TENSOR_AGENT_USER"],
                                   "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    d = _req(BASE + "/auth/login", data=form, ctype="application/x-www-form-urlencoded")
    tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit("login failed")
    return tok


def get_report(rid, token):
    d = _req("%s/tensor/reports/%s" % (BASE, rid), token)
    return d.get("data", d) if isinstance(d, dict) else d


def main(argv):
    pub_id = argv[0] if argv else "14657"
    tok = login()
    pub = get_report(pub_id, tok)
    src = get_report(SOURCE_ID, tok)

    md = pub["markdown"]
    fences = md.count("```json")
    inner = [b[len("json\n"):].rstrip("\n") for b in md.split("```") if b.startswith("json\n")]
    published = json.loads(inner[0]) if inner else {}
    local = json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))
    src_hash = hashlib.sha256(src["markdown"].encode("utf-8")).hexdigest()

    checks = {
        "single_json_block": fences == 1 and len(inner) == 1,
        "block_equals_local_result": published == local,
        "title": pub.get("title") == "KF-RESULT %s" % PKG,
        "tag_present": "kf-wp:%s" % PKG in (pub.get("tags") or []),
        "source_report_untouched": src_hash == CONTRACT_HASH ==
        local["provenance"]["source_hash"].split("sha256:")[-1],
        "figures_metadata_kept": len(pub.get("figures") or []) == 2,
        "figures_payload_persisted": any((f.get("png_base64") or "") for f in (pub.get("figures") or [])),
    }
    out = {"published_report_id": pub_id, "published_title": pub.get("title"),
           "published_tags": pub.get("tags"), "source_report_id": SOURCE_ID,
           "source_hash_live": "sha256:" + src_hash, "checks": checks,
           "figure_fields": [sorted(f.keys()) for f in (pub.get("figures") or [])],
           "note": "figures_payload_persisted=false is a platform behaviour observation: png_base64 is not "
                   "retained by figures[] (the source report 5761 shows the same shape), so figure bytes are "
                   "only durable as docs/kf/%s/*.png" % PKG,
           "overall": "PASS" if all(checks[k] for k in
                                    ("single_json_block", "block_equals_local_result", "title", "tag_present",
                                     "source_report_untouched")) else "FAIL"}
    (OUT / "published_check.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out["checks"], ensure_ascii=False))
    print("overall:", out["overall"])
    return 0 if out["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))