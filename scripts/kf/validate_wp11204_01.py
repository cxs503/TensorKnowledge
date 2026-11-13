#!/usr/bin/env python3
"""Independent validator for wp-11204-01.

Deliberately distrusts the local snapshot: re-fetches report 11204 from the
platform, recomputes the markdown hash, re-resolves every locator against the
fresh bytes, re-validates the manifest shape, and writes self_check.json.

Checks map 1:1 onto the contract acceptance items:
  valid_json                -> A1
  schema_pass               -> A2 (kf_result.v1 envelope + package manifest schema)
  source_locator_resolvable -> A3
  source_hash_matches       -> A4
  no_duplicate_ids          -> A5
  all_claims_have_evidence_or_explicit_unresolved_status -> A6
plus integrity invariants I1..I4 that the acceptance list does not name but the
"zero hand-copy" rule needs.
"""
import hashlib
import json
import os
import re
import sys
import urllib.request

import jsonschema

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTDIR = os.path.join(HERE, "docs", "kf", "wp-11204-01")
WORK = os.path.join(HERE, "work", "wp-11204-01")
SCHEMA_DIR = os.path.join(HERE, "schemas")
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
CONTRACT_HASH = "d22a30cc692b82f2acf6ea669fd898a330143436344e4091c4a39c06a5292f86"
CONTRACT_CHARS = 5999


def login():
    req = urllib.request.Request(
        API + "/auth/login",
        data=json.dumps({"username": os.environ.get("TENSOR_AGENT_USER", ""),
                         "password": os.environ.get("TENSOR_AGENT_PASS", "")}).encode(),
        method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    return d.get("access_token") or d.get("token")


def get_json(token, path):
    req = urllib.request.Request(API + path, method="GET")
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    checks = {}
    kf_path = os.path.join(OUTDIR, "kf_result.json")
    man_path = os.path.join(OUTDIR, "asset_manifest.json")

    # A1 valid json
    try:
        kf = json.load(open(kf_path, encoding="utf-8"))
        man = json.load(open(man_path, encoding="utf-8"))
        checks["A1_valid_json"] = {"pass": True, "detail": "both files parse as JSON"}
    except Exception as e:  # noqa: BLE001
        checks["A1_valid_json"] = {"pass": False, "detail": str(e)}
        _write(checks, None)
        return 1

    # A4 source hash vs live platform bytes (do this before trusting anything else)
    token = login()
    rec = get_json(token, "/tensor/reports/11204")
    live_md = rec["markdown"]
    live_hash = hashlib.sha256(live_md.encode("utf-8")).hexdigest()
    snapshot = open(os.path.join(WORK, "source_markdown.md"), encoding="utf-8").read()
    kf_hash = kf["provenance"]["source_hash"]
    kf_hash_norm = kf_hash.split(":", 1)[1] if kf_hash.startswith("sha256:") else kf_hash
    checks["A4_source_hash_matches"] = {
        "pass": (live_hash == CONTRACT_HASH == kf_hash_norm
                 and len(live_md) == CONTRACT_CHARS and live_md == snapshot),
        "detail": {"live_sha256": live_hash, "contract_sha256": CONTRACT_HASH,
                   "kf_provenance_sha256": kf_hash,
                   "kf_provenance_sha256_normalised": kf_hash_norm,
                   "live_chars": len(live_md), "contract_chars": CONTRACT_CHARS,
                   "local_snapshot_identical_to_live": live_md == snapshot},
    }

    # A2 schema pass
    env_schema = json.load(open(os.path.join(SCHEMA_DIR, "kf_result.v1.schema.json"), encoding="utf-8"))
    man_schema = json.load(open(os.path.join(OUTDIR, "asset_manifest.schema.json"), encoding="utf-8"))
    errs = []
    try:
        jsonschema.validate(kf, env_schema)
    except jsonschema.ValidationError as e:
        errs.append("kf_result: " + e.message)
    try:
        jsonschema.validate(man, man_schema)
    except jsonschema.ValidationError as e:
        errs.append("asset_manifest: " + e.message + " @ " + "/".join(str(p) for p in e.absolute_path))
    try:
        jsonschema.validate(kf["outputs"]["asset_manifest.json"], man_schema)
    except jsonschema.ValidationError as e:
        errs.append("outputs.asset_manifest: " + e.message)
    checks["A2_schema_pass"] = {"pass": not errs, "detail": errs or "envelope + manifest schema valid"}

    # A3 locators resolvable against LIVE bytes (record fields against LIVE record)
    bad = []
    for e in man["assets"]:
        for l in e["locators"]:
            if l["kind"] == "markdown_char_span":
                if live_md[l["start_char"]:l["end_char"]] != l["quote"]:
                    bad.append([e["asset_id"], "span_mismatch", l["quote"]])
                if live_md.count(l["quote"]) != l["occurrences"]:
                    bad.append([e["asset_id"], "occurrence_mismatch", l["quote"]])
                for sp in l["all_spans"]:
                    if live_md[sp["start_char"]:sp["end_char"]] != l["quote"]:
                        bad.append([e["asset_id"], "all_span_mismatch", sp])
                if l["start_line"] != live_md.count("\n", 0, l["start_char"]) + 1:
                    bad.append([e["asset_id"], "line_mismatch", l["quote"]])
            else:
                if not _resolve_record(rec, l["record_path"]):
                    bad.append([e["asset_id"], "record_path_missing", l["record_path"]])
    checks["A3_source_locator_resolvable"] = {
        "pass": not bad,
        "detail": {"locators_checked": sum(len(e["locators"]) for e in man["assets"]), "failures": bad},
    }

    # A5 no duplicate ids
    ids = [e["asset_id"] for e in man["assets"]]
    checks["A5_no_duplicate_ids"] = {
        "pass": len(ids) == len(set(ids)) and kf["outputs"]["asset_manifest.json"]["counts"]["assets"] == len(ids),
        "detail": {"count": len(ids), "unique": len(set(ids))},
    }

    # A6 claims discipline
    claims = kf.get("claims") or []
    ok_claims = all(("evidence" in c and c["evidence"]) or c.get("status") == "unresolved" for c in claims)
    checks["A6_claims_evidence_or_unresolved"] = {
        "pass": ok_claims and man["claims"] == claims == [],
        "detail": {"claims": len(claims),
                   "policy": "empty array is the contract-legal outcome for 01-asset-registration; "
                             "no claim is emitted, so nothing can be overstated as supported"},
    }

    # I1..I4 integrity invariants
    checks["I1_no_verified_status_anywhere"] = {
        "pass": not re.search(r'"(?:status|verification)"\s*:\s*"(?:verified|confirmed)"', json.dumps(kf, ensure_ascii=False)),
        "detail": "no asset or claim carries a verified/confirmed status (the platform gate owns verification)",
    }
    checks["I2_counts_self_consistent"] = {
        "pass": (_recount(man) == man["counts"]),
        "detail": {"recounted": _recount(man)},
    }
    fig_ok = all(e["figure_bytes"]["hash_stable_across_2_fetches"] for e in man["assets"] if "figure_bytes" in e)
    checks["I3_figure_bytes_hashed"] = {
        "pass": fig_ok and sum(1 for e in man["assets"] if "figure_bytes" in e) == 3,
        "detail": {e["asset_id"]: e["figure_bytes"]["sha256"] for e in man["assets"] if "figure_bytes" in e},
    }
    checks["I4_completeness_scanner_clean"] = {
        "pass": man["integrity"]["completeness_scanner_uncovered"] == [],
        "detail": {"tokens": man["integrity"]["completeness_scanner_tokens"]},
    }

    all_pass = all(v["pass"] for v in checks.values())
    out = {"package_id": "wp-11204-01", "report_id": "11204", "all_pass": all_pass, "checks": checks}
    with open(os.path.join(OUTDIR, "self_check.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    for k, v in checks.items():
        print(("PASS " if v["pass"] else "FAIL ") + k + ("" if v["pass"] else " :: " + str(v["detail"])[:400]))
    print("ALL_PASS=", all_pass)
    return 0 if all_pass else 9


def _write(checks, flag):
    with open(os.path.join(OUTDIR, "self_check.json"), "w", encoding="utf-8") as f:
        json.dump({"package_id": "wp-11204-01", "all_pass": False, "checks": checks}, f,
                  ensure_ascii=False, indent=1)


def _resolve_record(rec, path):
    cur = rec
    for m in re.finditer(r"([A-Za-z0-9_]+)|\[([0-9]+)\]", path.replace("record.", "")):
        key, idx = m.group(1), m.group(2)
        if key is not None:
            if not isinstance(cur, dict) or key not in cur:
                return False
            cur = cur[key]
        else:
            i = int(idx)
            if not isinstance(cur, list) or i >= len(cur):
                return False
            cur = cur[i]
    return True


def _recount(man):
    by_class, by_res = {}, {}
    for e in man["assets"]:
        by_class[e["asset_class"]] = by_class.get(e["asset_class"], 0) + 1
        by_res[e["resolution"]] = by_res.get(e["resolution"], 0) + 1
    return {
        "assets": len(man["assets"]),
        "by_class": by_class,
        "by_resolution": by_res,
        "resolved_in_source": by_res.get("resolved_in_source", 0),
        "referenced_unresolved": by_res.get("referenced_unresolved", 0),
        "declared_absent": by_res.get("declared_absent", 0),
    }


if __name__ == "__main__":
    sys.exit(main())