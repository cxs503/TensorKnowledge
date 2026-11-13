#!/usr/bin/env python3
"""Publish the wp-5611-04 report and verify the embedded envelope block.

Checks before publishing (any failure aborts, nothing is posted):
  * the markdown carries exactly one ```json block
  * that block parses and is byte-identical (as JSON) to docs/kf/wp-5611-04/kf_result.json
  * provenance.source_hash equals the sha256 of report 5611's markdown bytes
"""
import hashlib
import json
import os
import pathlib
import re
import urllib.request

import jsonschema

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "kf" / "wp-5611-04"
MD = DOCS / "KF-RESULT-wp-5611-04.md"
PAYLOAD = pathlib.Path("/tmp/report_5611_04_payload.json")
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")


def req(url, data=None, token=None):
    r = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode())


def main():
    md = MD.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
    assert len(blocks) == 1, f"expected exactly one json block, got {len(blocks)}"
    embedded = json.loads(blocks[0])
    env = json.loads((DOCS / "kf_result.json").read_text(encoding="utf-8"))
    assert embedded == env, "embedded envelope differs from kf_result.json"
    jsonschema.validate(embedded, json.loads(
        (ROOT / "schemas" / "kf_result.v1.schema.json").read_text()))

    tok = req(BASE + "/auth/login", json.dumps({
        "username": os.environ["TENSOR_AGENT_USER"],
        "password": os.environ["TENSOR_AGENT_PASS"]}).encode())
    token = tok.get("access_token") or tok.get("token")

    src = req(BASE + "/tensor/reports/5611", token=token)
    if isinstance(src, list):
        src = src[0]
    live_hash = "sha256:" + hashlib.sha256(src["markdown"].encode("utf-8")).hexdigest()
    assert live_hash == embedded["provenance"]["source_hash"], (
        f"source hash drift: live={live_hash} envelope="
        f"{embedded['provenance']['source_hash']}")

    payload = json.loads(PAYLOAD.read_text(encoding="utf-8"))
    assert payload["markdown"] == md
    payload["markdown_sha256"] = hashlib.sha256(md.encode()).hexdigest()
    created = req(BASE + "/tensor/reports", json.dumps(payload).encode(), token=token)
    print(json.dumps({
        "posted_report_id": created.get("id"),
        "title": created.get("title"),
        "tags": created.get("tags"),
        "source_hash_verified": live_hash,
        "json_blocks": len(blocks),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()