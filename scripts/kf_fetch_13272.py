#!/usr/bin/env python3
"""wp-13272-01 · fetch report_id=13272 markdown over the TensorPlatform API and
pin its byte hash (contract: sha256:75ed781cefac9fee890f493c256dec8aea2e70795eca9d7a8bbfef1af1bcce90).

Writes the source snapshot under work/wp-13272-01/source/:
  report_13272_record.json   full API record (markdown included)
  report_13272.md            the markdown field, verbatim
  markdown.sha256            recomputed sha256 of the markdown utf-8 bytes

Exit code 1 if the recomputed hash does not equal the contract-declared hash.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
REPORT_ID = "13272"
PACKAGE_ID = "wp-13272-01"
CONTRACT_SOURCE_HASH = "sha256:75ed781cefac9fee890f493c256dec8aea2e70795eca9d7a8bbfef1af1bcce90"
CONTRACT_CHARS = 4537
CONTRACT_TITLE = "CII 规则内核三副本单源化与 regime 语义修复（m13764）"

WT = pathlib.Path(__file__).resolve().parent.parent
SRC_DIR = WT / "work" / "wp-13272-01" / "source"


def main() -> int:
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps(
            {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]}
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    tok = json.load(urllib.request.urlopen(req))["access_token"]
    req2 = urllib.request.Request(
        BASE + f"/tensor/reports/{REPORT_ID}", headers={"Authorization": "Bearer " + tok}
    )
    d = json.load(urllib.request.urlopen(req2))
    if isinstance(d, dict) and "data" in d and isinstance(d["data"], dict):
        d = d["data"]

    md = d["markdown"]
    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    recomputed = "sha256:" + digest

    SRC_DIR.mkdir(parents=True, exist_ok=True)
    (SRC_DIR / "report_13272_record.json").write_text(json.dumps(d, ensure_ascii=False, indent=1))
    (SRC_DIR / "report_13272.md").write_text(md)
    (SRC_DIR / "markdown.sha256").write_text(recomputed + "\n")

    print(f"report_id={d['id']} chars={len(md)} bytes={len(md.encode('utf-8'))}")
    print(f"recomputed={recomputed}")
    print(f"contract  ={CONTRACT_SOURCE_HASH}")
    if recomputed != CONTRACT_SOURCE_HASH:
        print("HASH MISMATCH — refusing to continue")
        return 1
    if len(md) != CONTRACT_CHARS:
        print(f"CHARS MISMATCH: observed {len(md)} != contract {CONTRACT_CHARS}")
        return 1
    if d.get("title") != CONTRACT_TITLE:
        print(f"TITLE MISMATCH: {d.get('title')!r}")
        return 1
    print("hash/chars/title all match the contract — source pinned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
