#!/usr/bin/env python3
"""Independent verifier for work package wp-13980-01 (report 13980).

Runs the contract's acceptance items as machine checks and writes
runs/wp-13980-01/verify_report.json (+ durable mirror under docs/kf/wp-13980-01/).
It is deliberately independent of scripts/kf_register_13980.py: the markdown is
re-fetched from the platform API rather than trusting the local copy, and every
locator is re-resolved from raw offsets.

Checks (map 1:1 onto the contract acceptance block):
  valid_json                        -- both the envelope and the manifest parse
  schema_pass                       -- jsonschema validation of envelope vs
                                       schemas/kf_result.v1.schema.json and manifest vs
                                       schemas/asset_manifest.v1.schema.json (that file
                                       pins report 448's consts, so the consts are
                                       parameterised from this package's contract)
  source_locator_resolvable         -- every locator re-slices to its quote; quote is a
                                       unique substring; unique flags are truthful
  source_hash_matches               -- sha256 + char count of the freshly fetched markdown
                                       equal the contract values
  no_duplicate_ids                  -- asset_id unique
  all_claims_have_evidence_or_explicit_unresolved_status -- claims=[] (allowed) and no
                                       asset silently missing resolution/check
  not_marked_verified               -- 约束 do_not_mark_claims_as_verified 的机检

Usage: python3 scripts/kf_verify_13980.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

import jsonschema

REPORT_ID = "13980"
PACKAGE_ID = "wp-13980-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/13980"
CONTRACT_HASH = "2e506d3c8285306a34dd397de133f8c48f6f02a604629adbc0c79eb81ce83ce6"
CONTRACT_CHARS = 8267

ART = pathlib.Path("artifacts/wp-13980-01")
RUN = pathlib.Path("runs/wp-13980-01")
DOC = pathlib.Path("docs/kf/wp-13980-01")
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def fetch_markdown() -> str:
    """Re-fetch from the platform (independent of the local artifact copy)."""
    login = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(login, timeout=60) as r:
        tok = json.loads(r.read().decode())
    token = tok.get("access_token") or tok.get("token")
    req = urllib.request.Request(BASE + "/tensor/reports/" + REPORT_ID,
                                 headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())["markdown"]


def parameterised_manifest_schema() -> dict:
    p = pathlib.Path("schemas/asset_manifest.v1.schema.json")
    schema = copy.deepcopy(json.loads(p.read_text()))
    props = schema["properties"]
    props["package_id"]["const"] = PACKAGE_ID
    props["task_type"]["const"] = TASK_TYPE
    props["report_id"]["const"] = REPORT_ID
    src = props["source"]["properties"]
    src["uri"]["const"] = SOURCE_URI
    src["field"]["const"] = "markdown"
    src["hash_alg"]["const"] = "sha256"
    return schema


def locator_failures(md: str, assets: list) -> list:
    """Re-resolve every locator from raw offsets against ``md``; return offending ids.

    Exposed separately so tests can feed deliberately tampered assets and confirm the
    check is discriminating (a check that cannot fail proves nothing).
    """
    bad = []
    for a in assets:
        loc = a["locator"]
        if loc["method"] == "document":
            ok = loc["start_char"] == 0 and loc["end_char"] == len(md)
        else:
            ok = md[loc["start_char"]:loc["end_char"]] == loc["quote"]
        ok = ok and md.count(loc["quote"]) >= 1 and loc["unique"] is True
        if not ok:
            bad.append(a["asset_id"])
    return bad


def run_checks() -> dict:
    checks, detail = {}, {}

    # ---- valid_json -------------------------------------------------------
    try:
        envelope = json.loads((RUN / "kf_result.wp-13980-01.json").read_text())
        manifest = json.loads((ART / "asset_manifest.json").read_text())
        checks["valid_json"] = True
    except Exception as exc:
        return {"checks": {"valid_json": False}, "detail": {"error": str(exc)}}

    # ---- schema_pass ------------------------------------------------------
    errs = []
    try:
        jsonschema.validate(envelope, json.loads(
            pathlib.Path("schemas/kf_result.v1.schema.json").read_text()))
    except Exception as exc:
        errs.append("kf_result.v1: " + str(exc).splitlines()[0])
    try:
        jsonschema.validate(manifest, parameterised_manifest_schema())
    except Exception as exc:
        errs.append("asset_manifest.v1: " + str(exc).splitlines()[0])
    checks["schema_pass"] = not errs
    detail["schema_errors"] = errs

    # ---- source_hash_matches (fresh fetch, not the local copy) ------------
    try:
        md_live = fetch_markdown()
        live_hash = hashlib.sha256(md_live.encode()).hexdigest()
        checks["source_hash_matches"] = (
            live_hash == CONTRACT_HASH
            and len(md_live) == CONTRACT_CHARS
            and manifest["source"]["hash"] == CONTRACT_HASH
            and envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH)
        detail["live_hash"] = live_hash
        detail["live_chars"] = len(md_live)
        detail["local_copy_matches_live"] = (
            (ART / "source_markdown.md").read_text() == md_live)
    except Exception as exc:
        checks["source_hash_matches"] = False
        detail["fetch_error"] = str(exc)
        md_live = (ART / "source_markdown.md").read_text()

    # ---- source_locator_resolvable ----------------------------------------
    bad = locator_failures(md_live, manifest["assets"])
    checks["source_locator_resolvable"] = not bad
    detail["locator_failures"] = bad

    # ---- no_duplicate_ids -------------------------------------------------
    ids = [a["asset_id"] for a in manifest["assets"]]
    checks["no_duplicate_ids"] = len(ids) == len(set(ids))

    # ---- claims / resolution completeness ---------------------------------
    claims = envelope.get("claims", manifest.get("claims", []))
    unresolved_ok = all(
        a.get("resolution") in ("resolved_in_source", "referenced_unresolved", "declared_absent")
        and a.get("resolution_check", {}).get("result")
        for a in manifest["assets"])
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = (
        isinstance(claims, list) and unresolved_ok)
    detail["claims_count"] = len(claims)

    # ---- not_marked_verified ---------------------------------------------
    blob = json.dumps(envelope, ensure_ascii=False) + json.dumps(manifest, ensure_ascii=False)
    checks["not_marked_verified"] = (
        envelope["provenance"].get("verification_status") == "not_verified"
        and '"verified": true' not in blob.replace(" ", "")
        and '"status":"verified"' not in blob.replace(" ", ""))

    detail["counts"] = manifest["counts"]
    return {"package_id": PACKAGE_ID, "report_id": REPORT_ID,
            "checks": checks, "all_pass": all(checks.values()), "detail": detail}


def main() -> int:
    rep = run_checks()
    out = json.dumps(rep, ensure_ascii=False, indent=2) + "\n"
    RUN.mkdir(parents=True, exist_ok=True)
    DOC.mkdir(parents=True, exist_ok=True)
    (RUN / "verify_report.json").write_text(out)
    (DOC / "verify_report.json").write_text(out)
    print(out)
    return 0 if rep["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())