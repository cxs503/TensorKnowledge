"""Independent verification of the wp-12316-01 deliverable (report 12316 asset registration).

This verifier does not trust the register script: it re-fetches the report from the platform,
recomputes the markdown hash, re-slices every locator out of the markdown itself, and validates
the manifest against a pinned schema copy. Every acceptance item of the work-package contract is
mapped to one check below; anything that cannot be established is reported as not_run, never pass.

Checks (acceptance item -> check id):
  valid_json                            -> json_parses
  schema_pass                           -> schema_manifest / schema_result_envelope
  source_locator_resolvable             -> locator_slice / locator_lines / locator_unique
  source_hash_matches                   -> hash_fresh_fetch (independent API re-fetch)
  no_duplicate_ids                      -> unique_ids
  all_claims_have_evidence_or_explicit_unresolved_status -> claims_policy

Usage: python3 scripts/kf_verify_12316.py            (exit 0 = all checks pass)
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.request

REPORT_ID = "12316"
PACKAGE_ID = "wp-12316-01"
EXPECTED_HASH = "a38be5c7ec3bc9250f3d1a53fb75491d66489da695b121134a761e93bdba7f87"
SOURCE_URI = "tensor://reports/12316"

RUN_DIR = pathlib.Path("runs/wp-12316-01")
ART_DIR = pathlib.Path("artifacts/wp-12316-01")
DOC_DIR = pathlib.Path("docs/wp-12316-01")

checks = []


def check(cid: str, ok: bool, detail) -> bool:
    checks.append(dict(id=cid, ok=bool(ok), detail=detail))
    return bool(ok)


def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def fresh_markdown() -> str:
    """Independent re-fetch: the hash must not depend on our own cached copy."""
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    creds = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                        "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(base + "/auth/login", data=creds,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        token = json.load(r)["access_token"]
    req = urllib.request.Request("%s/tensor/reports/%s" % (base, REPORT_ID),
                                 headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["markdown"]


def main() -> int:
    try:
        manifest = json.loads((ART_DIR / "asset_manifest.json").read_text())
        envelope = json.loads((RUN_DIR / "kf_result.wp-12316-01.json").read_text())
        check("json_parses", True, {"manifest_keys": len(manifest), "envelope_keys": len(envelope)})
    except Exception as exc:  # noqa: BLE001
        check("json_parses", False, repr(exc))
        print(json.dumps(dict(package_id=PACKAGE_ID, checks=checks, all_pass=False), ensure_ascii=False, indent=2))
        return 1

    # ---- schema_pass
    try:
        import jsonschema
        schema = json.loads((DOC_DIR / "asset_manifest.v1.schema.json").read_text())
        pin_ok = (schema["properties"]["package_id"]["const"] == PACKAGE_ID
                  and schema["properties"]["report_id"]["const"] == REPORT_ID)
        check("schema_pinned_to_package", pin_ok,
              {"package_const": schema["properties"]["package_id"]["const"],
               "report_const": schema["properties"]["report_id"]["const"]})
        jsonschema.validate(manifest, schema)
        check("schema_manifest", True, "jsonschema validate OK against pinned asset_manifest.v1")
    except Exception as exc:  # noqa: BLE001
        check("schema_manifest", False, repr(exc))
    try:
        import jsonschema
        eschema = json.loads(pathlib.Path("schemas/kf_result.v1.schema.json").read_text())
        jsonschema.validate(envelope, eschema)
        check("schema_result_envelope", True, "jsonschema validate OK against kf_result.v1")
    except Exception as exc:  # noqa: BLE001
        check("schema_result_envelope", False, repr(exc))

    # ---- identity of the package / report
    src = manifest.get("source", {})
    check("identity", manifest.get("package_id") == PACKAGE_ID
          and manifest.get("task_type") == "01-asset-registration"
          and manifest.get("report_id") == REPORT_ID and src.get("uri") == SOURCE_URI,
          {"package_id": manifest.get("package_id"), "report_id": manifest.get("report_id"),
           "uri": src.get("uri")})

    # ---- source_hash_matches (independent re-fetch + local copy + contract pin, all three)
    md = fresh_markdown()
    h_fresh = sha256_text(md)
    h_local = sha256_text((RUN_DIR / "report_12316.md").read_text())
    prov = envelope.get("provenance", {})
    invoked = prov.get("source_hash", "")
    check("hash_fresh_fetch", h_fresh == EXPECTED_HASH == h_local == invoked.replace("sha256:", ""),
          {"fresh_api_sha256": h_fresh, "local_copy_sha256": h_local,
           "contract_sha256": EXPECTED_HASH, "envelope_source_hash": invoked,
           "chars_fresh": len(md), "chars_declared": src.get("chars")})
    check("manifest_hash_matches", src.get("hash") == h_fresh, src.get("hash"))
    check("chars_match", src.get("chars") == len(md) and src.get("bytes_utf8") == len(md.encode()),
          {"chars": src.get("chars"), "bytes_utf8": src.get("bytes_utf8"),
           "recomputed_chars": len(md), "recomputed_bytes": len(md.encode())})

    # ---- no_duplicate_ids (assets + any claims)
    assets = manifest.get("assets", [])
    ids = [a.get("asset_id") for a in assets]
    check("unique_ids", len(ids) == len(set(ids)),
          {"n_assets": len(ids), "n_unique": len(set(ids)),
           "duplicates": sorted({i for i in ids if ids.count(i) > 1})})
    check("id_pattern", all(isinstance(i, str) and len(i) == 3 and i[0] == "A" and i[1:].isdigit()
                            for i in ids), ids[:3])
    check("counts_consistent", manifest.get("counts", {}).get("assets") == len(assets),
          {"declared": manifest.get("counts", {}).get("assets"), "actual": len(assets)})

    # ---- source_locator_resolvable: re-slice every locator out of the freshly fetched markdown
    bad_slice, bad_lines, not_unique, empty, bad_doc = [], [], [], [], []
    for a in assets:
        loc = a.get("locator", {})
        s, e, q = loc.get("start_char", -1), loc.get("end_char", -1), loc.get("quote", "")
        if not q:
            empty.append(a["asset_id"])
            continue
        if loc.get("method") == "document":
            # convention: whole-document span, quote = first line (checked separately)
            if not (s == 0 and e == len(md) and q == md.split("\n")[0]
                    and loc.get("end_line") == len(md.split("\n")) - 1):
                bad_doc.append(dict(asset_id=a["asset_id"], start=s, end=e, quote=q[:40]))
            if loc.get("unique") is True and md.count(q) != 1:
                not_unique.append(dict(asset_id=a["asset_id"], occurrences=md.count(q)))
            continue
        if md[s:e] != q:
            bad_slice.append(dict(asset_id=a["asset_id"], start=s, end=e,
                                  got=md[s:e][:60], want=q[:60]))
            continue
        ls, le = loc.get("start_line"), loc.get("end_line")
        if "\n".join(md.split("\n")[ls:le + 1]) != q:
            bad_lines.append(dict(asset_id=a["asset_id"], start_line=ls, end_line=le))
        if loc.get("unique") is True and md.count(q) != 1:
            not_unique.append(dict(asset_id=a["asset_id"], occurrences=md.count(q)))
    check("locator_slice", not bad_slice, {"n_checked": len(assets), "mismatches": bad_slice[:5]})
    check("locator_document_span", not bad_doc, {"mismatches": bad_doc[:5],
                                                 "convention": "method=document → span=whole markdown, quote=first line"})
    check("locator_lines", not bad_lines, {"mismatches": bad_lines[:5]})
    check("locator_unique", not not_unique, {"mismatches": not_unique[:5]})
    check("locator_nonempty", not empty, {"empty_quotes": empty})

    # ---- resolution honesty: every claim about the outside world must carry how it was checked
    no_check = [a["asset_id"] for a in assets
                if not a.get("resolution_check", {}).get("check")
                or not a.get("resolution_check", {}).get("result")]
    check("resolution_check_present", not no_check, {"missing": no_check})
    extern = [a for a in assets if a.get("resolution") == "referenced_unresolved"]
    unresolved = [a["asset_id"] for a in extern
                  if a["resolution_check"]["result"] == "unresolved"]
    check("external_paths_accounted", True,
          {"referenced_unresolved": len(extern),
           "resolved_at_reported_path": len(extern) - len(unresolved),
           "unresolved": unresolved,
           "note": "unresolved 项如实保留，不猜地址、不补造"})
    statuses = {}
    for a in extern:
        st = a.get("payload", {}).get("status", "?")
        statuses[st] = statuses.get(st, 0) + 1
    check("external_payload_status", all(k != "?" for k in statuses), statuses)

    # ---- claims policy
    claims = manifest.get("claims", [])
    claims_ok = all(("evidence_locator" in c) or ("status" in c) for c in claims)
    check("claims_policy", claims_ok,
          {"n_claims": len(claims),
           "note": "空数组合法（register_assets only / classify_report_type=false）"})

    # ---- nothing is marked verified
    blob = json.dumps(manifest, ensure_ascii=False)
    check("no_verified_claims", '"verified"' not in blob.replace('"not_verified"', ""),
          {"verification_status": manifest.get("integrity", {}).get("verification_status")})

    all_pass = all(c["ok"] for c in checks)
    report = dict(schema="kf_verification.v1", package_id=PACKAGE_ID, report_id=REPORT_ID,
                  source_uri=SOURCE_URI, source_hash_fresh="sha256:" + h_fresh,
                  contract_hash="sha256:" + EXPECTED_HASH,
                  manifest_sha256=hashlib.sha256(
                      (ART_DIR / "asset_manifest.json").read_bytes()).hexdigest(),
                  verifier="scripts/kf_verify_12316.py",
                  generated_from="fresh API re-fetch + local manifest (no reuse of register-script state)",
                  checks=checks, all_pass=all_pass,
                  claims_allowed_empty=True,
                  acceptance=dict(
                      valid_json=next(c["ok"] for c in checks if c["id"] == "json_parses"),
                      schema_pass=all(c["ok"] for c in checks
                                      if c["id"] in ("schema_manifest", "schema_result_envelope")),
                      source_locator_resolvable=all(c["ok"] for c in checks
                                                    if c["id"].startswith("locator_")),
                      source_hash_matches=all(c["ok"] for c in checks
                                              if c["id"] in ("hash_fresh_fetch",
                                                             "manifest_hash_matches", "chars_match")),
                      no_duplicate_ids=next(c["ok"] for c in checks if c["id"] == "unique_ids"),
                      all_claims_have_evidence_or_explicit_unresolved_status=
                      next(c["ok"] for c in checks if c["id"] == "claims_policy"),
                  ))
    (RUN_DIR / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    (DOC_DIR / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(package_id=PACKAGE_ID, all_pass=all_pass,
                          acceptance=report["acceptance"],
                          failed=[c["id"] for c in checks if not c["ok"]]),
                     ensure_ascii=False, indent=2))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())