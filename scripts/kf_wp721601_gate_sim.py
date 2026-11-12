#!/usr/bin/env python3
"""Independent gate simulation for the published wp-7216-01 result report.

Reads the report back from the platform (it is NOT the local file), extracts the
single json code block, and re-runs every acceptance check the platform gate is
announced to run -- so a "green" here is evidence about the *published* artifact,
not about a local buffer:

  1. exactly one ```json block, parses as JSON              -> valid_json
  2. block validates against schemas/kf_result.v1.schema.json -> schema_pass
     and outputs["asset_manifest.json"] against the package pin
  3. provenance.source_hash == sha256(report 7216 markdown)  -> source_hash_matches
  4. every asset locator re-resolves on report 7216 markdown -> source_locator_resolvable
  5. asset ids / keys unique                                 -> no_duplicate_ids
  6. each claim has evidence or unresolved_reason (or the
     manifest states why claims are empty)                   -> claims item
  7. report identity: title KF-RESULT <package_id>, tags carry kf-wp:<package_id>

    python3 scripts/kf_wp721601_gate_sim.py [report_report_id]   # default 14696
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ID = "wp-7216-01"
REPORT_ID = "7216"
OUT = ROOT / "docs" / "kf" / PACKAGE_ID / "gate_sim.json"
SCHEMAS = ROOT / "schemas" / "kf_result.v1.schema.json"
MANIFEST_SCHEMA = ROOT / "docs" / "kf" / PACKAGE_ID / "asset_manifest.schema.json"


def api(path: str):
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(base + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    tok = json.load(urllib.request.urlopen(req, timeout=60))["access_token"]
    req = urllib.request.Request(base + path, headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def sha(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def main(argv) -> int:
    rid = argv[1] if len(argv) > 1 else "14696"
    rep = api("/tensor/reports/%s" % rid)
    md = rep.get("markdown") or ""
    src = api("/tensor/reports/%s" % REPORT_ID)
    src_md = src.get("markdown") or ""

    blocks = re.findall(r"(?ms)^```json\s*$(.*?)^```\s*$", md)
    res: dict = {"published_report_id": rid, "package_id": PACKAGE_ID,
                 "source_report_id": REPORT_ID, "checks": {}}
    res["checks"]["valid_json"] = {"ok": len(blocks) == 1,
                                   "detail": "json blocks found: %d" % len(blocks)}
    if len(blocks) != 1:
        OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n")
        return 1
    try:
        env = json.loads(blocks[0])
        res["checks"]["valid_json"]["parsed"] = True
    except Exception as e:
        res["checks"]["valid_json"] = {"ok": False, "detail": "parse error: %s" % e}
        OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n")
        return 1

    import jsonschema
    e_errs = [("%s: %s" % ("/".join(map(str, e.absolute_path)), e.message))
              for e in jsonschema.Draft202012Validator(json.loads(SCHEMAS.read_text())).iter_errors(env)]
    m_errs = []
    man = (env.get("outputs") or {}).get("asset_manifest.json")
    if man is not None:
        m_errs = [("%s: %s" % ("/".join(map(str, e.absolute_path)), e.message))
                  for e in jsonschema.Draft7Validator(
                      json.loads(MANIFEST_SCHEMA.read_text())).iter_errors(man)]
    res["checks"]["schema_pass"] = {"ok": not e_errs and not m_errs and man is not None,
                                    "envelope_errors": e_errs[:8], "manifest_errors": m_errs[:8]}

    live = sha(src_md.encode("utf-8"))
    res["checks"]["source_hash_matches"] = {
        "ok": live == (env.get("provenance") or {}).get("source_hash"),
        "detail": "live=%s provenance=%s" % (live, (env.get("provenance") or {}).get("source_hash"))}

    bad = []
    for a in (man or {}).get("assets", []):
        loc = a["locator"]
        q = loc["quote"]
        if loc["method"] == "document":
            good = (loc["char_start"] == 0 and loc["char_end"] == len(src_md) and q in src_md)
        else:
            good = src_md[loc["char_start"]:loc["char_end"]] == q
        good = good and sha(q.encode()) == loc["quote_sha256"]
        if not good:
            bad.append(a["asset_id"])
    n = len((man or {}).get("assets", []))
    res["checks"]["source_locator_resolvable"] = {"ok": not bad,
                                                  "detail": "%d/%d re-resolved" % (n - len(bad), n),
                                                  "failures": bad}

    ids = [a["asset_id"] for a in (man or {}).get("assets", [])]
    keys = [a["asset_key"] for a in (man or {}).get("assets", [])]
    res["checks"]["no_duplicate_ids"] = {
        "ok": len(set(ids)) == len(ids) and len(set(keys)) == len(keys),
        "detail": "%d ids, %d keys" % (len(ids), len(keys))}

    claims = env.get("claims") or []
    res["checks"]["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": all(c.get("evidence") or c.get("unresolved_reason") for c in claims)
              and bool((man or {}).get("claims_empty_reason")),
        "detail": "%d claims; empty reason present: %s"
                  % (len(claims), bool((man or {}).get("claims_empty_reason")))}

    res["checks"]["identity"] = {
        "ok": rep.get("title") == "KF-RESULT %s" % PACKAGE_ID
              and "kf-wp:%s" % PACKAGE_ID in (rep.get("tags") or []),
        "title": rep.get("title"), "tags": rep.get("tags"),
        "figures": [f.get("name") for f in (rep.get("figures") or [])]}

    res["all_ok"] = all(c["ok"] for c in res["checks"].values())
    res["note"] = ("Gate simulation on the PUBLISHED report as read back from the platform. "
                   "Not a platform verdict: it encodes my reading of the acceptance contract, "
                   "and it does not mark anything verified.")
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n")
    for k, v in res["checks"].items():
        print("[%s] %-58s %s" % ("PASS" if v["ok"] else "FAIL", k, str(v.get("detail", ""))[:100]))
    print("all_ok =", res["all_ok"], "->", OUT.relative_to(ROOT))
    return 0 if res["all_ok"] else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))