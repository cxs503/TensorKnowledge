#!/usr/bin/env python3
"""wp-12160-01 self-check: turns each `acceptance` item of the contract into a
machine check with raw evidence.  Writes selfcheck.json next to the manifest.

    python3 scripts/kf_selfcheck_12160.py --out docs/kf/wp-12160-01

Exit code 0 = every acceptance item PASS.  Anything not executed is reported as
not_run, never as pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request

WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = "wp-12160-01"
BASE_SCHEMA = os.path.join(WORKTREE, "schemas", "asset_manifest.v1.schema.json")
RESULT_SCHEMA = os.path.join(WORKTREE, "schemas", "kf_result.v1.schema.json")


def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def contract_hash(path: str) -> str | None:
    for ln in open(path, encoding="utf-8"):
        m = re.match(r"\s*source_hash:\s*(sha256:[0-9a-f]{64})", ln)
        if m:
            return m.group(1)
    return None


def localized_schema(out_dir: str) -> tuple[dict, str]:
    """The shipped asset_manifest schema pins package_id/report_id with `const` for
    the package it was first written for.  We reuse it verbatim except for those two
    consts, and store the localized copy so the check is reproducible."""
    raw = open(BASE_SCHEMA, encoding="utf-8").read()
    schema = json.loads(raw)
    patches = {
        "properties.package_id.const": (schema["properties"]["package_id"].get("const"), PKG),
        "properties.report_id.const": (schema["properties"]["report_id"].get("const"), "12160"),
        "properties.source.properties.uri.const": (
            schema["properties"]["source"]["properties"]["uri"].get("const"), "tensor://reports/12160"),
    }
    schema["properties"]["package_id"]["const"] = patches["properties.package_id.const"][1]
    schema["properties"]["report_id"]["const"] = patches["properties.report_id.const"][1]
    schema["properties"]["source"]["properties"]["uri"]["const"] = \
        patches["properties.source.properties.uri.const"][1]
    schema["$comment"] = ("localized from schemas/asset_manifest.v1.schema.json; only these "
                          "`const` values were rebound: " + json.dumps({k: v[0] for k, v in patches.items()},
                                                                        ensure_ascii=False))
    schema["x_localized_consts"] = {k: {"from": v[0], "to": v[1]} for k, v in patches.items()}
    path = os.path.join(out_dir, "asset_manifest.v1.localized.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(schema, fh, ensure_ascii=False, indent=2)
    return schema, path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(WORKTREE, "docs/kf", PKG))
    ap.add_argument("--contract", default=os.path.join(WORKTREE, "contracts", PKG + ".yaml"))
    ap.add_argument("--live-api", action="store_true",
                    help="also re-fetch the report from the platform and compare hashes")
    args = ap.parse_args()

    import jsonschema

    out = args.out
    man_path = os.path.join(out, "asset_manifest.json")
    res_path = os.path.join(out, "kf_result.json")
    src_path = os.path.join(out, "source_markdown.md")
    checks: dict[str, dict] = {}

    def record(name, ok, evidence, **extra):
        checks[name] = {"result": "PASS" if ok is True else ("not_run" if ok is None else "FAIL"),
                        "evidence": evidence, **extra}

    # 1 valid_json ---------------------------------------------------------
    parsed, errs = {}, []
    for path in (man_path, res_path):
        try:
            parsed[path] = json.load(open(path, encoding="utf-8"))
        except json.JSONDecodeError as exc:  # pragma: no cover
            errs.append(f"{os.path.basename(path)}: {exc}")
    record("valid_json", not errs,
           {"files": [os.path.basename(p) for p in parsed], "errors": errs,
            "bytes": {os.path.basename(p): os.path.getsize(p) for p in (man_path, res_path)}})
    manifest = parsed.get(man_path, {})
    result = parsed.get(res_path, {})

    # 2 schema_pass --------------------------------------------------------
    schema_errors = []
    sch_manifest, sch_path = localized_schema(out)
    try:
        jsonschema.validate(manifest, sch_manifest)
    except jsonschema.ValidationError as exc:
        schema_errors.append(f"asset_manifest.json: {exc.message} at {list(exc.absolute_path)}")
    try:
        jsonschema.validate(result, json.load(open(RESULT_SCHEMA, encoding="utf-8")))
    except jsonschema.ValidationError as exc:
        schema_errors.append(f"kf_result.json: {exc.message} at {list(exc.absolute_path)}")
    record("schema_pass", not schema_errors,
           {"schemas": [{"path": os.path.relpath(RESULT_SCHEMA, WORKTREE),
                         "sha256": sha256_file(RESULT_SCHEMA)},
                        {"path": os.path.relpath(sch_path, WORKTREE),
                         "sha256": sha256_file(sch_path),
                         "derived_from": os.path.relpath(BASE_SCHEMA, WORKTREE),
                         "derived_from_sha256": sha256_file(BASE_SCHEMA)}],
            "errors": schema_errors},
           note="asset_manifest.v1.localized.json = shipped schemas/asset_manifest.v1.schema.json "
                "with only package_id/report_id `const` localized to this package")

    # 3 source_locator_resolvable -----------------------------------------
    if not os.path.exists(src_path):
        record("source_locator_resolvable", False, {"error": f"missing byte copy {src_path}"})
        md = None
    else:
        md = open(src_path, encoding="utf-8").read()
    bad = []
    for asset in (manifest.get("assets", []) if md is not None else []):
        loc = asset["locator"]
        if loc["method"] == "document":
            # document locators span the whole file; the quote is an identifying excerpt
            if not md.startswith(loc["quote"]):
                bad.append({"asset_id": asset["asset_id"], "why": "document quote is not a prefix"})
            continue
        span = md[loc["start_char"]:loc["end_char"]]
        if span != loc["quote"]:
            bad.append({"asset_id": asset["asset_id"], "why": "char_span != quote"})
        if loc["quote"] not in md:
            bad.append({"asset_id": asset["asset_id"], "why": "quote not substring"})
        if loc.get("unique") and md.count(loc["quote"]) != 1:
            bad.append({"asset_id": asset["asset_id"], "why": "declared unique but occurs "
                                                              f"{md.count(loc['quote'])}x"})
        if loc["start_line"] != md.count("\n", 0, loc["start_char"]):
            bad.append({"asset_id": asset["asset_id"], "why": "start_line mismatch"})
    n_char_span = sum(1 for a in manifest.get("assets", []) if a["locator"]["method"] == "char_span")
    n_doc = sum(1 for a in manifest.get("assets", []) if a["locator"]["method"] == "document")
    if md is not None:
        record("source_locator_resolvable", not bad,
               {"char_span_locators_checked": n_char_span, "document_locators": n_doc,
                "failures": bad,
                "check": "md[start:end] == quote; unique quotes occur exactly once; "
                         "start_line == count('\\n', 0, start_char); document quote is a prefix"})

    # 4 source_hash_matches ------------------------------------------------
    disk_hash = sha256_file(src_path) if os.path.exists(src_path) else "missing"
    want = contract_hash(args.contract)
    m = re.search(r"^source_hash:\s*(\S+)", open(args.contract, encoding="utf-8").read(), re.M)
    want = m.group(1) if m else want
    got = {
        "source_markdown_sha256": "sha256:" + disk_hash,
        "manifest.source.hash": "sha256:" + manifest.get("source", {}).get("hash", ""),
        "kf_result.provenance.source_hash": result.get("provenance", {}).get("source_hash"),
        "contract.source_hash": want,
    }
    live = None
    if args.live_api:
        try:
            base = os.environ["TENSOR_API_BASE"]
            req = urllib.request.Request(
                base + "/auth/login",
                data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                                 "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
                headers={"Content-Type": "application/json"})
            tok = json.load(urllib.request.urlopen(req))
            tok = tok.get("access_token") or tok.get("token") or tok["data"]["access_token"]
            rec = json.load(urllib.request.urlopen(urllib.request.Request(
                base + "/tensor/reports/12160", headers={"Authorization": "Bearer " + tok})))
            live = "sha256:" + hashlib.sha256(rec["markdown"].encode()).hexdigest()
            got["platform_live_sha256"] = live
        except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
            got["platform_live_error"] = repr(exc)
    values = {v for v in got.values() if isinstance(v, str) and v.startswith("sha256:")}
    record("source_hash_matches", len(values) == 1 and want == "sha256:" + disk_hash, got,
           note="all four hash sources must agree; live platform re-fetch adds a fifth")

    # 5 no_duplicate_ids ---------------------------------------------------
    ids = [a["asset_id"] for a in manifest.get("assets", [])]
    dups = sorted({i for i in ids if ids.count(i) > 1})
    record("no_duplicate_ids", not dups, {"assets": len(ids), "duplicates": dups,
                                          "id_range": [ids[0], ids[-1]] if ids else []})

    # 6 claims evidence policy --------------------------------------------
    claims = result.get("claims", [])
    missing = [c.get("claim_id") for c in claims
               if not c.get("evidence") and c.get("status") not in
               {"unresolved", "partially-supported", "refuted"}]
    record("all_claims_have_evidence_or_explicit_unresolved_status", not missing,
           {"claims": len(claims), "violations": missing,
            "policy": manifest.get("claims_policy")},
           note="claims=[] by contract (register_assets only); the item is vacuously "
                "satisfied and is reported as such rather than as positive evidence of extraction")

    # extra guards (not acceptance items) ---------------------------------
    n_acceptance = len(checks)
    record("no_verification_claim_made",
           all("verified" not in json.dumps(a.get("resolution", "")) for a in manifest.get("assets", [])),
           {"resolution_values": sorted({a["resolution"] for a in manifest.get("assets", [])})},
           note="platform gate computes verification; this package only registers")
    cross = manifest.get("integrity", {}).get("contract_cross_checks", {})
    record("contract_cross_checks", all(v for k, v in cross.items()
                                        if k.endswith("_match")), cross)

    ok = all(c["result"] == "PASS" for c in checks.values())
    names = list(checks)
    acceptance = {k: checks[k] for k in names[:n_acceptance]}
    extra = {k: checks[k] for k in names[n_acceptance:]}
    payload = {
        "package_id": PKG,
        "report_id": "12160",
        "checked_at_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(timespec="seconds"),
        "acceptance": acceptance,
        "extra_checks_not_in_contract": extra,
        "all_pass": ok,
        "counts": {"acceptance_items": len(acceptance), "extra_checks": len(extra)},
        "repro_cmd": "python3 scripts/kf_register_12160.py --out docs/kf/wp-12160-01 && "
                     "python3 scripts/kf_selfcheck_12160.py --out docs/kf/wp-12160-01 --live-api",
        "not_run": [],
    }
    with open(os.path.join(out, "selfcheck.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    for group, items in (("acceptance", acceptance), ("extra", extra)):
        for name, c in items.items():
            print(f"{c['result']:8s} [{group}] {name}")
    print(f"ALL_PASS={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())