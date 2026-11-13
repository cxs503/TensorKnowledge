#!/usr/bin/env python3
"""Record the delivery of this package to the platform (/tensor/reports) after posting.

Reads back both records from the API and writes runs/wp-11156-01/delivery.json with
machine-derived values only (no hand-typed hashes):
  * source report 11156 markdown sha256 (recomputed now, third independent check)
  * delivered KF-RESULT report id + markdown sha256
  * the single ```json block parsed back out of the delivered markdown, re-validated
    against schemas/kf_result.v1.schema.json and compared to the committed envelope.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request

import jsonschema

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PKG = os.path.join(ROOT, "docs", "kf", "wp-11156-01")
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
OUT = os.path.join(ROOT, "runs", "wp-11156-01", "delivery.json")


def get(path: str, tok: str) -> dict:
    req = urllib.request.Request(API + path, headers={"Authorization": "Bearer " + tok})
    return json.load(urllib.request.urlopen(req, timeout=60))


def main(report_id: str) -> None:
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    tok = json.load(urllib.request.urlopen(urllib.request.Request(
        API + "/auth/login", data=body,
        headers={"Content-Type": "application/json"}), timeout=30))["access_token"]

    src = get("/tensor/reports/11156", tok)
    dl = get("/tensor/reports/%s" % report_id, tok)
    md = dl["markdown"]
    blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
    schema = json.load(open(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json"), encoding="utf-8"))

    rec = {
        "package_id": "wp-11156-01",
        "source": {
            "report_id": "11156",
            "markdown_sha256": "sha256:" + hashlib.sha256(src["markdown"].encode("utf-8")).hexdigest(),
            "chars": len(src["markdown"]),
            "checked_via": "GET /api/v1/tensor/reports/11156 (3rd independent recompute)",
        },
        "delivered": {
            "report_id": str(dl["id"]),
            "title": dl.get("title"),
            "markdown_sha256": "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest(),
            "json_blocks": len(blocks),
            "figures": [f.get("name") for f in dl.get("figures") or []],
            "tags": dl.get("tags"),
        },
    }
    if len(blocks) == 1:
        env = json.loads(blocks[0])
        try:
            jsonschema.validate(env, schema)
            schema_ok = True
        except Exception as e:  # noqa: BLE001
            schema_ok = "failed: %r" % (e,)
        committed = json.load(open(os.path.join(PKG, "kf_result.json"), encoding="utf-8"))
        rec["json_block_check"] = {
            "schema_valid": schema_ok,
            "equals_committed_envelope": env == committed,
            "provenance_source_hash": env["provenance"]["source_hash"],
            "provenance_matches_source_markdown":
                env["provenance"]["source_hash"] == rec["source"]["markdown_sha256"],
            "claims": env["claims"],
        }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(rec, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    open(OUT, "a", encoding="utf-8").write("\n")
    print(json.dumps(rec, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "14794")