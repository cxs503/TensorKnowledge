#!/usr/bin/env python3
"""wp-12565-01 independent verifier.

Re-derives everything from a fresh fetch of report 12565 and the written artifacts,
using a different code path than scripts/kf_wp12565_01_register.py (slice-based span
reconstruction instead of find()-based resolution), so a bug in one path does not
silently vouch for itself.

Checks
  V1 envelope/manifest are valid JSON and the envelope validates against
     schemas/kf_result.v1.schema.json
  V2 sha256 of the freshly fetched markdown == contract hash == manifest.source.hash
  V3 every asset locator: markdown[start_char:end_char] == quote, the declared
     start/end lines contain that quote, occurrence count re-counted, `unique` consistent
  V4 every literal anchor: same reconstruction, and is_claim == False
  V5 asset ids and anchor ids unique; file copy docs/kf/wp-12565-01/source.md is
     byte-identical to the fetched markdown
  V6 claims == [] and no status marked "verified" anywhere in the envelope
  V7 scope: every URL this package contacted targets report_id 12565 only

Exit code 0 only if all checks pass. Writes docs/kf/wp-12565-01/verify_independent.json.

Usage: python3 scripts/kf_wp12565_01_verify.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-12565-01"
REPORT_ID = "12565"
CONTRACT_HASH = "sha256:a5a04a43beed973865029e9ade6c0de33a88e17a795bea13b55ef4c083571d20"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
CONTACTED: list[str] = []


def get_json(url: str, token: str | None = None):
    CONTACTED.append(url)
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login() -> str:
    CONTACTED.append(BASE + "/auth/login")
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(BASE + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())["access_token"]


def span_ok(md: str, rec: dict) -> list[str]:
    """Return a list of problems for one locator record (empty list = ok)."""
    problems = []
    q = rec["quote"]
    s, e = rec["start_char"], rec["end_char"]
    if md[s:e] != q:
        problems.append("%s: slice mismatch" % rec.get("asset_id", rec.get("locator_id")))
    mlines = md.split("\n")
    sl, el = rec["start_line"], rec["end_line"]
    if not (1 <= sl <= len(mlines)):
        problems.append("%s: start_line %d out of range" % (rec.get("asset_id"), sl))
    else:
        window = "\n".join(mlines[sl - 1:el])
        if q not in window:
            problems.append("%s: quote not inside declared line window %d-%d"
                            % (rec.get("asset_id"), sl, el))
    recount = md.count(q)
    if rec.get("occurrences") is not None and recount != rec["occurrences"]:
        problems.append("%s: occurrences %s != recounted %d"
                        % (rec.get("asset_id"), rec["occurrences"], recount))
    if "unique" in rec and rec["unique"] != (recount == 1):
        problems.append("%s: unique flag inconsistent (recount=%d)" % (rec.get("asset_id"), recount))
    return problems


def main() -> int:
    token = login()
    record = get_json(BASE + "/tensor/reports/" + REPORT_ID, token)
    if isinstance(record.get("data"), dict):
        record = record["data"]
    md = record.get("markdown") or ""
    digest = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()

    result = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
    manifest = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    checks: list[dict] = []

    # V1 schema
    import jsonschema
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    v1_problems = []
    try:
        jsonschema.validate(result, schema)
    except jsonschema.ValidationError as exc:
        v1_problems.append(str(exc).splitlines()[0])
    manifest_matches_output = result["outputs"]["asset_manifest.json"] == manifest
    checks.append({"id": "V1", "ok": not v1_problems and manifest_matches_output,
                   "detail": "envelope validates (2020-12); outputs.asset_manifest.json == "
                             "asset_manifest.json on disk" if not v1_problems else v1_problems})

    # V2 hash chain
    manifest_hash = "sha256:" + manifest["source"]["hash"]
    v2_ok = digest == CONTRACT_HASH == manifest_hash == result["provenance"]["source_hash"]
    checks.append({"id": "V2", "ok": v2_ok,
                   "detail": {"fetched": digest, "contract": CONTRACT_HASH,
                              "manifest": manifest_hash,
                              "envelope": result["provenance"]["source_hash"]}})

    # V3 asset locators
    probs = []
    for a in manifest["assets"]:
        probs += span_ok(md, {**a["locator"], "asset_id": a["asset_id"]})
    checks.append({"id": "V3", "ok": not probs,
                   "detail": "%d/%d asset locators reconstruct from the raw markdown"
                             % (len(manifest["assets"]) - len(probs), len(manifest["assets"])),
                   "problems": probs})

    # V4 anchors
    probs4 = []
    for a in manifest["literal_anchors"]:
        probs4 += span_ok(md, a)
        if a.get("is_claim") is not False:
            probs4.append("%s: is_claim must be false" % a["locator_id"])
    checks.append({"id": "V4", "ok": not probs4,
                   "detail": "%d/%d literal anchors reconstruct; none flagged as a claim"
                             % (len(manifest["literal_anchors"]) - len(probs4),
                                len(manifest["literal_anchors"])),
                   "problems": probs4})

    # V5 id uniqueness + byte copy
    aids = [a["asset_id"] for a in manifest["assets"]]
    lids = [a["locator_id"] for a in manifest["literal_anchors"]]
    copy = (PKG / "source.md").read_bytes()
    v5_ok = (len(aids) == len(set(aids))) and (len(lids) == len(set(lids))) \
        and copy == md.encode("utf-8")
    checks.append({"id": "V5", "ok": v5_ok,
                   "detail": {"asset_ids": len(aids), "distinct": len(set(aids)),
                              "anchor_ids": len(lids), "distinct_anchors": len(set(lids)),
                              "source_copy_byte_identical": copy == md.encode("utf-8")}})

    # V6 claims / verified marks
    blob = json.dumps(result, ensure_ascii=False)
    v6_ok = result.get("claims") == [] and '"verified"' not in blob
    checks.append({"id": "V6", "ok": v6_ok,
                   "detail": "claims=%r; string \"verified\" present=%s"
                             % (result.get("claims"), '"verified"' in blob)})

    # V7 scope: only report 12565 contacted
    offenders = [u for u in CONTACTED
                 if "/reports/" in u and not u.endswith("/reports/" + REPORT_ID)]
    checks.append({"id": "V7", "ok": not offenders,
                   "detail": {"contacted": CONTACTED, "offending_urls": offenders}})

    out = {"package_id": "wp-12565-01", "report_id": REPORT_ID, "source_hash": digest,
           "checks": checks, "all_pass": all(c["ok"] for c in checks)}
    (PKG / "verify_independent.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for c in checks:
        print(c["id"], "OK" if c["ok"] else "FAIL", "-", json.dumps(c["detail"],
                                                                   ensure_ascii=False)[:180])
    print("ALL_PASS:", out["all_pass"])
    return 0 if out["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())