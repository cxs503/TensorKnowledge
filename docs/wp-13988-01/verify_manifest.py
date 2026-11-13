"""Independent verifier for artifacts/wp-13988-01/asset_manifest.json.

Re-fetches report 13988 from the platform API (no reliance on the cached copy),
then re-checks every acceptance item of the work package against that fresh
markdown:

  1. source_hash_matches          sha256(fresh markdown) == contract source_hash
  2. source_locator_resolvable    every quote is a unique substring AND
                                  md[start_char:end_char] == quote (fresh offsets)
  3. no_duplicate_ids             asset_id (and claim_id) uniqueness
  4. all_claims_have_evidence_or_explicit_unresolved_status
  5. valid_json / schema_pass     manifest + envelope validate; negative control fails
  6. no_asset_marked_verified     nothing was promoted to verified by this package

Writes docs/wp-13988-01/verification.json. Exit 0 iff every check passes.
Usage: python3 docs/wp-13988-01/verify_manifest.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.request

REPORT_ID = "13988"
PACKAGE_ID = "wp-13988-01"
CONTRACT_SOURCE_HASH = "79d795674f0b13f828d8933af64612a1addb30cb8a8b903f7ab136f0508442b9"
CONTRACT_CHARS = 6222
WT = pathlib.Path(".").resolve()
MANIFEST = WT / "artifacts" / PACKAGE_ID / "asset_manifest.json"
ENVELOPE = WT / "docs" / PACKAGE_ID / ("kf_result.%s.json" % PACKAGE_ID)
LOCAL_SCHEMA = WT / "docs" / PACKAGE_ID / "asset_manifest.v1.schema.json"
KF_SCHEMA = WT / "schemas" / "kf_result.v1.schema.json"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _req(url, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login():
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = _req(BASE + path, {"username": user, "password": pwd})
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def main() -> int:
    results = []

    def add(name, ok, detail):
        results.append(dict(check=name, status="pass" if ok else "fail", detail=detail))
        return ok

    tok = login()
    payload = _req("%s/tensor/reports/%s" % (BASE, REPORT_ID), token=tok)
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    md = payload["markdown"]
    fresh_hash = hashlib.sha256(md.encode()).hexdigest()

    add("source_hash_matches", fresh_hash == CONTRACT_SOURCE_HASH,
        "fresh sha256=%s contract=%s" % (fresh_hash, CONTRACT_SOURCE_HASH))
    add("source_chars_match_contract", len(md) == CONTRACT_CHARS,
        "fresh chars=%d contract=%d" % (len(md), CONTRACT_CHARS))

    man = json.loads(MANIFEST.read_text())
    add("valid_json", man.get("schema") == "asset_manifest.v1",
        "%s re-parsed (sha256=%s)" % (MANIFEST.relative_to(WT),
                                      hashlib.sha256(MANIFEST.read_bytes()).hexdigest()))
    add("manifest_hash_matches_fresh_source", man["source"]["hash"] == fresh_hash,
        "manifest source.hash == fresh sha256 of API markdown")

    # ---- locator resolution against the FRESH markdown ---------------------
    bad_span, bad_unique, bad_count = [], [], []
    for a in man["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        if md.count(q) != 1:
            bad_unique.append(a["asset_id"])
        if loc["method"] == "char_span":
            if md[loc["start_char"]:loc["end_char"]] != q:
                bad_span.append(a["asset_id"])
            if md.count(q) < 1:
                bad_count.append(a["asset_id"])
        else:
            if loc["start_char"] != 0 or loc["end_char"] != len(md):
                bad_span.append(a["asset_id"] + "(document span)")
    add("source_locator_resolvable", not (bad_span or bad_unique),
        "%d assets: quote unique=%d/%d, char-span exact=%d/%d (offenders span=%s unique=%s)"
        % (len(man["assets"]), len(man["assets"]) - len(bad_unique), len(man["assets"]),
           len(man["assets"]) - len(bad_span), len(man["assets"]), bad_span, bad_unique))

    ids = [a["asset_id"] for a in man["assets"]]
    cids = [c["claim_id"] for c in man.get("claims", [])]
    add("no_duplicate_ids", len(ids) == len(set(ids)) and len(cids) == len(set(cids)),
        "asset_id %d/%d unique, claim_id %d/%d unique" % (len(set(ids)), len(ids),
                                                          len(set(cids)), len(cids)))

    unresolved = [c for c in man.get("claims", [])
                  if not c.get("evidence") and c.get("status") not in
                  ("unresolved", "partially-supported", "refuted", "supported")]
    add("all_claims_have_evidence_or_explicit_unresolved_status", not unresolved,
        "claims=%d; every claim carries evidence or an explicit status" % len(man.get("claims", [])))

    # ---- resolution claims must be true NOW (no stale / invented resolution)
    wrong = []
    for a in man["assets"]:
        if a["resolution"] == "referenced_unresolved":
            seg = a["resolution_check"]
            if seg.get("check") == "repo_relative_path_resolution_in_worktree":
                if any((WT / p).exists() for p in seg.get("searched", [])):
                    wrong.append(a["asset_id"])
    npath = sum(1 for a in man["assets"]
                if a["resolution_check"].get("check") == "repo_relative_path_resolution_in_worktree")
    add("referenced_unresolved_still_unresolved", not wrong,
        "%d path-referenced assets re-tested against the worktree (of %d referenced_unresolved); "
        "offenders=%s" % (npath, sum(1 for a in man["assets"]
                                     if a["resolution"] == "referenced_unresolved"),
                          wrong or "none"))

    # ---- schema gates -------------------------------------------------------
    import jsonschema
    env = json.loads(ENVELOPE.read_text())
    try:
        jsonschema.validate(man, json.loads(LOCAL_SCHEMA.read_text()))
        man_ok, man_d = True, "manifest validates against %s" % LOCAL_SCHEMA.relative_to(WT)
    except Exception as exc:
        man_ok, man_d = False, "manifest schema violation: %s" % exc
    kf = json.loads(KF_SCHEMA.read_text())
    try:
        jsonschema.validate(env, kf)
        env_ok, env_d = True, "envelope validates against %s" % KF_SCHEMA.relative_to(WT)
    except Exception as exc:
        env_ok, env_d = False, "envelope schema violation: %s" % exc
    try:
        jsonschema.validate({"package_id": PACKAGE_ID}, kf)
        neg_ok, neg_d = False, "negative control did NOT fail"
    except Exception:
        neg_ok, neg_d = True, "negative control: schema rejects envelope missing required keys"
    add("schema_pass", man_ok and env_ok and neg_ok, " | ".join([man_d, env_d, neg_d]))
    add("envelope_source_hash_matches", env["provenance"]["source_hash"] == "sha256:" + fresh_hash,
        "envelope provenance.source_hash == sha256(fresh markdown)")

    marked = [a["asset_id"] for a in man["assets"]
              if "verified" in json.dumps(a, ensure_ascii=False).lower()]
    add("no_asset_marked_verified", not marked,
        "no asset/locator field promotes a claim to verified (offenders=%s)" % (marked or "none"))

    ok = all(r["status"] == "pass" for r in results)
    out = dict(package_id=PACKAGE_ID, report_id=REPORT_ID, ok=ok,
               fresh_source_hash="sha256:" + fresh_hash,
               manifest_sha256=hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
               envelope_sha256=hashlib.sha256(ENVELOPE.read_bytes()).hexdigest(),
               verified_at_note="就地复算，非平台门；平台门结论以平台为准",
               checks=results)
    (WT / "docs" / PACKAGE_ID / "verification.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    for r in results:
        print("[%s] %-52s %s" % (r["status"], r["check"], r["detail"][:120]))
    print("ok =", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())