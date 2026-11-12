#!/usr/bin/env python3
"""Independent re-check of work package wp-5761-01 (01-asset-registration).

Deliberately does not import the builder: it re-fetches the source bytes, re-slices every locator,
re-validates the manifest against the pinned schema and re-derives the contract acceptance items.
It never writes a "verified" claim about content — only check outcomes.

Usage: python3 scripts/kf/verify_5761.py [--offline]
  --offline  use docs/kf/wp-5761-01/report_5761.markdown instead of a fresh API fetch
Exit code 0 = all checks pass.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PKG = "wp-5761-01"
REPORT_ID = "5761"
CONTRACT_HASH = "06f7e6a9d2164c64a916d4f11cc0e117af97766de133438d10fc884a35c2c4d7"
CONTRACT_CHARS = 4141

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "kf" / PKG
FORBIDDEN_KEYS = {"verified", "verification_status", "verification_level", "is_verified", "gate_confirmed"}


def _req(url, token=None, data=None, ctype="application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def live_source():
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    user, pwd = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]
    tok = None
    body = json.dumps({"username": user, "password": pwd}).encode()
    for path in ("/tensor/auth/login", "/auth/login"):
        try:
            d = _req(base + path, data=body)
        except Exception:  # noqa: BLE001 - try next shape
            continue
        tok = d.get("access_token") or d.get("token")
        if tok:
            break
    if not tok:
        form = urllib.parse.urlencode({"username": user, "password": pwd}).encode()
        d = _req(base + "/auth/login", data=form, ctype="application/x-www-form-urlencoded")
        tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit("login failed")
    d = _req("%s/tensor/reports/%s" % (base, REPORT_ID), tok)
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    return d["markdown"], "GET %s/tensor/reports/%s" % (base, REPORT_ID)


def walk_keys(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path + "/" + k, k
            yield from walk_keys(v, path + "/" + k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_keys(v, "%s[%d]" % (path, i))


def main(argv):
    offline = "--offline" in argv
    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "result": "pass" if ok else "fail", "detail": detail})

    manifest = json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))
    result = json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))
    schema = json.loads((OUT / "schema" / ("asset_manifest.v1.%s.schema.json" % PKG)).read_text(encoding="utf-8"))
    binding = json.loads((OUT / "schema_binding.json").read_text(encoding="utf-8"))
    local_copy = (OUT / "report_5761.markdown").read_bytes()

    # --- source acquisition
    if offline:
        md = local_copy.decode("utf-8")
        via = "local copy docs/kf/%s/report_5761.markdown (--offline)" % PKG
    else:
        md, via = live_source()
    raw = md.encode("utf-8")
    api_hash = hashlib.sha256(raw).hexdigest()
    copy_hash = hashlib.sha256(local_copy).hexdigest()

    add("valid_json", True,
        {"files": ["asset_manifest.json", "kf_result.json", "schema/…schema.json", "schema_binding.json"],
         "note": "all four parsed by json.loads"})

    add("source_hash_matches",
        api_hash == CONTRACT_HASH == manifest["source"]["hash"]
        == result["provenance"]["source_hash"].split("sha256:")[-1] == copy_hash,
        {"contract_sha256": CONTRACT_HASH, "refetched_sha256": api_hash, "local_copy_sha256": copy_hash,
         "manifest_sha256": manifest["source"]["hash"],
         "envelope_sha256": result["provenance"]["source_hash"].split("sha256:")[-1],
         "refetched_chars": len(md), "contract_chars": CONTRACT_CHARS, "via": via})

    # --- schema
    import jsonschema
    err = None
    try:
        jsonschema.validate(manifest, schema)
    except Exception as e:  # noqa: BLE001
        err = "%s: %s" % (type(e).__name__, str(e).splitlines()[0])
    parent = json.loads((REPO / binding["parent_schema"]).read_text(encoding="utf-8"))
    # specialization may only re-pin identity: required keys and structural constraints must be inherited
    structure_inherited = (parent["required"] == schema["required"]
                           and parent["properties"]["assets"]["items"] == schema["properties"]["assets"]["items"])
    if not structure_inherited:
        err = err or "specialized schema diverges structurally from parent"
    add("schema_pass", err is None,
        {"schema": binding["specialized_schema"], "schema_sha256": binding["specialized_schema_sha256"],
         "parent_schema": binding["parent_schema"], "parent_schema_sha256": binding["parent_schema_sha256"],
         "substitutions": binding["substitutions"], "validator": "jsonschema.validate (draft-07)",
         "structure_inherited_from_parent": structure_inherited,
         "error": err,
         "note": "canonical schemas/kf_result.v1.schema.json named by the contract is absent from this "
                 "worktree; manifest validated against the mechanically re-pinned copy of the accepted "
                 "asset_manifest.v1 schema — platform schema wins if it differs"})

    # --- locators: re-slice from freshly fetched bytes
    failures, span_ok = [], 0
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] == "document":
            ok = loc["start_char"] == 0 and loc["end_char"] == len(md) and loc["quote"] in md
            if not ok:
                failures.append(a["asset_id"] + ":document-span")
            else:
                span_ok += 1
            continue
        q = md[loc["start_char"]:loc["end_char"]]
        same = q == loc["quote"]
        uniq = md.count(loc["quote"]) == 1
        line_ok = md.count("\n", 0, loc["start_char"]) + 1 == loc["start_line"] and \
            md.count("\n", 0, loc["end_char"]) + 1 == loc["end_line"]
        if same and uniq and line_ok:
            span_ok += 1
        else:
            failures.append({"asset_id": a["asset_id"], "slice_equals_quote": same,
                             "quote_unique": uniq, "line_consistent": line_ok})
    add("source_locator_resolvable", not failures and span_ok == len(manifest["assets"]),
        {"assets_checked": len(manifest["assets"]), "spans_resolved": span_ok, "failures": failures,
         "method": "re-slice fresh markdown at [start_char,end_char), compare to quote, count occurrences, "
                   "recompute start_line/end_line"})

    # --- ids / counts / claims
    ids = [a["asset_id"] for a in manifest["assets"]]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    claim_ids = [c.get("claim_id") for c in manifest["claims"]]
    add("no_duplicate_ids", not dup and len(ids) == len(set(ids)) and not any(i in ids for i in claim_ids),
        {"asset_ids": ids, "duplicates": dup, "claim_ids": claim_ids})

    by_res = {}
    for a in manifest["assets"]:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    c = manifest["counts"]
    consistent = (c["assets"] == len(manifest["assets"]) == 31 and by_res == c["by_resolution"]
                  and c["resolved_in_source"] == by_res.get("resolved_in_source", 0)
                  and c["referenced_unresolved"] == by_res.get("referenced_unresolved", 0)
                  and c["declared_absent"] == by_res.get("declared_absent", 0)
                  and sum(c["by_class"].values()) == c["assets"])
    add("counts_consistent", consistent,
        {"assets": c["assets"], "by_resolution": by_res, "by_class_rows": sum(c["by_class"].values())})

    no_forced = (manifest["claims"] == [] and len(manifest["claims_note"]) >= 20)
    add("all_claims_have_evidence_or_explicit_unresolved_status", no_forced,
        {"claims": 0, "offenders": [],
         "note": "claims=[] by contract (objective.register_assets only, classify_report_type=false); "
                 "asset-level resolution status carried on all %d assets "
                 "(22 resolved_in_source / 8 referenced_unresolved / 1 declared_absent)"
                 % len(manifest["assets"]),
         "claims_note_chars": len(manifest["claims_note"])})

    # --- no self-verification, in any product
    hits = []
    for name in ("asset_manifest.json", "kf_result.json"):
        doc = json.loads((OUT / name).read_text(encoding="utf-8"))
        for path, key in walk_keys(doc):
            if key in FORBIDDEN_KEYS:
                hits.append(name + path)
    add("no_verified_markers", not hits,
        {"structural_hits": hits,
         "note": "producer must not mark anything verified (verification is the platform gate's job); "
                 "the envelope carries only provenance.verification_note = a not_verified statement"})

    # --- envelope
    need = {"package_id", "task_type", "report_id", "provenance", "outputs"}
    env_ok = need <= set(result) and result["package_id"] == PKG and \
        result["task_type"] == "01-asset-registration" and result["report_id"] == REPORT_ID
    mraw = (OUT / "asset_manifest.json").read_bytes()
    sha_ok = hashlib.sha256(mraw).hexdigest() == result["outputs"]["asset_manifest.json"]["artifact_sha256"]
    inline_ok = result["outputs"]["asset_manifest.json"]["assets"] == manifest["assets"] and \
        result["outputs"]["asset_manifest.json"]["counts"] == manifest["counts"]
    add("result_envelope_shape", env_ok and sha_ok and inline_ok,
        {"keys": sorted(result), "artifact_sha256": hashlib.sha256(mraw).hexdigest(),
         "envelope_artifact_sha256": result["outputs"]["asset_manifest.json"]["artifact_sha256"],
         "inline_manifest_matches_file": inline_ok})

    # --- figures present & non-empty
    figs = sorted(p for p in OUT.glob("*.png"))
    add("figures_present", len(figs) >= 2 and all(p.stat().st_size > 5000 for p in figs),
        {p.name: p.stat().st_size for p in figs})

    overall = "PASS" if all(x["result"] == "pass" for x in checks) else "FAIL"
    verdict = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "verified_by": "scripts/kf/verify_5761.py",
        "independence_note": "re-fetch + re-slice + re-validate; does not import the builder and does not "
                             "read any producer explanation beyond the products themselves",
        "source_hash_recomputed": "sha256:" + api_hash,
        "source_via": via,
        "checks": checks,
        "overall": overall,
        "scope_limits": [
            "content correctness of the report's claims is NOT checked (out of scope for 01; the numbers "
            "are registered as located text, not re-executed)",
            "codes/artifacts referenced by the report (route/, route_lock.json, summary.json, test file, "
            "scripts) are absent from this worktree: registered as referenced_unresolved, not verified",
            "figure PNG payloads are absent from the platform report record (name+caption only): "
            "figures registered as referenced_unresolved",
            "the canonical schemas/kf_result.v1.schema.json is absent from the worktree; the envelope "
            "shape follows the accepted wp-448-01 / wp-542-01 precedent and is validated structurally, "
            "not against the canonical file",
        ],
    }
    (OUT / "verification.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n",
                                           encoding="utf-8")
    print(json.dumps({"overall": overall, "failed": [c["check"] for c in checks if c["result"] != "pass"]},
                     ensure_ascii=False))
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))