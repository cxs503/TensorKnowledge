#!/usr/bin/env python3
"""Worker-side self-check for wp-5716-04 (not the platform gate).

Re-derives every acceptance item from raw bytes at gate time:
  valid_json                      -> json.load on envelope + inlined block
  schema_pass                     -> jsonschema vs schemas/kf_result.v1.schema.json
  source_hash_matches             -> live re-fetch of /tensor/reports/5716, sha256 recompute
  quotes_verbatim                 -> every quote in the review is a substring of the LIVE markdown
  single_json_block               -> exactly one ```json block in docs/.../report.md, equal to envelope
  report_id_scope                 -> package/report ids match the contract, no other report touched
  do_not_mark_verified            -> no verified flag anywhere in the envelope
  upstream_packages_completed     -> reported as UNKNOWN (no platform endpoint), never PASS

Usage: python3 scripts/kf/validate_wp_5716_04.py [--offline]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

import jsonschema

PKG = "wp-5716-04"
REPORT_ID = "5716"
CONTRACT_HASH = "sha256:4f9848b22b55515826476e1d5b2fcd15da80087a3d261d6a937a4c17cda68377"
SNAP = "docs/kf/wp-5716-04/source_5716.md"
ENV = "docs/kf/wp-5716-04/kf_result.json"
REP = "docs/kf/wp-5716-04/report.md"
SCHEMA = "schemas/kf_result.v1.schema.json"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args(argv)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import review_wp_5716_04 as rv  # noqa: E402

    res: list[tuple[str, bool, str]] = []

    def chk(name: str, ok: bool, note: str) -> None:
        res.append((name, bool(ok), note))

    # raw source at gate time
    try:
        if a.offline:
            raw = open(SNAP, "rb").read()
            note = "offline snapshot"
        else:
            raw = rv.load_markdown(False)
            note = "live re-fetch"
        sha = "sha256:" + hashlib.sha256(raw).hexdigest()
        md = raw.decode("utf-8")
    except Exception as e:  # noqa: BLE001
        print("FATAL: cannot obtain source markdown:", e)
        return 2

    env = json.load(open(ENV, encoding="utf-8"))
    rep = open(REP, encoding="utf-8").read()

    chk("valid_json", isinstance(env, dict) and "outputs" in env, "envelope parsed")
    schema = json.load(open(SCHEMA, encoding="utf-8"))
    try:
        jsonschema.validate(env, schema)
        chk("schema_pass", True, "jsonschema validate -> ok")
    except jsonschema.ValidationError as e:
        chk("schema_pass", False, str(e).splitlines()[0])

    chk("source_hash_matches", env["provenance"]["source_hash"] == sha == CONTRACT_HASH,
        f"{env['provenance']['source_hash']} == recomputed {sha} ({note})")
    chk("source_field", env["provenance"]["source_field"] == "markdown",
        env["provenance"]["source_field"])

    bad = [k for k, q in rv.Q.items() if q not in md]
    chk("quotes_verbatim", not bad, f"{len(rv.Q) - len(bad)}/{len(rv.Q)} quotes located verbatim; drift={bad}")

    blocks = re.findall(r"```json\n(.*?)\n```", rep, re.S)
    ok_block = len(blocks) == 1 and json.loads(blocks[0]) == env
    chk("single_json_block", ok_block, f"{len(blocks)} json block(s), equal_to_envelope={ok_block}")

    chk("id_scope", env["package_id"] == PKG and env["report_id"] == REPORT_ID
        and env["outputs"]["review_report.json"]["report_id"] == REPORT_ID,
        f"{env['package_id']} / report {env['report_id']}")

    blob = json.dumps(env, ensure_ascii=False).lower()
    chk("do_not_mark_verified", '"verified": true' not in blob and '"status": "verified"' not in blob,
        "no verified flag; verification_status=" + str(env["outputs"]["review_report.json"].get("verification_status"))[:40])

    unknown = any("upstream_packages_completed" in u
                  for u in env["outputs"]["review_report.json"]["scope"]["unknown_not_passed"])
    chk("upstream_packages_completed", False,
        "UNKNOWN (not PASS): no platform package registry endpoint (3 candidate paths 404, tags filter ignored on /tensor/reports)"
        if unknown else "UNKNOWN: independence/exclusion note missing")

    width = max(len(n) for n, _, _ in res)
    fails = 0
    for name, ok, note in res:
        if not ok and name != "upstream_packages_completed":
            fails += 1
        flag = "PASS" if ok else ("UNKNOWN" if name == "upstream_packages_completed" else "FAIL")
        print(f"[{flag:7s}] {name.ljust(width)}  {note}")
    print(f"\n{len(res) - fails - 1} pass, {fails} fail, 1 unknown (upstream_packages_completed)")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())