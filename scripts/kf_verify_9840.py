#!/usr/bin/env python3
"""wp-9840-01 acceptance gate — re-runs every acceptance item against live source.

Independence: the verifier does NOT trust the builder's frozen copy. It re-authenticates,
re-fetches tensor/reports/9840, recomputes sha256 over the live markdown, and re-slices every
char-span locator out of the live text. Anything that cannot be re-derived is reported
not-run/fail rather than assumed passed.

Checks (acceptance item -> check id):
  valid_json                                   -> valid_json
  schema_pass                                  -> schema_pass_manifest + schema_pass_envelope
  source_locator_resolvable                    -> source_locator_resolvable
  source_hash_matches                          -> source_hash_matches_contract + source_hash_recomputed_live
  no_duplicate_ids                             -> no_duplicate_ids
  all_claims_have_evidence_or_explicit_status  -> all_claims_have_evidence_or_explicit_unresolved_status
  (constraint) do_not_mark_claims_as_verified  -> no_verified_markers
  (extras)                                     -> counts_consistent, shared_span_documented,
                                                  artifact_hash_matches_envelope, durable_mirror_identical,
                                                  single_report_scope
"""
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

import jsonschema

PACKAGE_ID = "wp-9840-01"
REPORT_ID = "9840"
EXPECTED_HASH = "159d4a1419890fe82d46b49037d00273376244d1f24a6503e386c6243d882524"
EXPECTED_CHARS = 14740
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
USER = os.environ.get("TENSOR_AGENT_USER", "")
PASS = os.environ.get("TENSOR_AGENT_PASS", "")

RUN_DIR = pathlib.Path("runs/wp-9840-01")
ART = pathlib.Path("artifacts/wp-9840-01/asset_manifest.json")
DOC_DIR = pathlib.Path("docs/wp-9840-01")
RESULT = RUN_DIR / ("kf_result.%s.json" % PACKAGE_ID)
OUT = RUN_DIR / "verification.json"

checks = []


def rec(cid, ok, detail, status=None):
    checks.append(dict(check=cid, result=status or ("pass" if ok else "fail"), detail=detail))


def api(path, data=None, token=None):
    req = urllib.request.Request(BASE + path)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, body, timeout=60) as r:
        return json.loads(r.read().decode())


def check_locators(md, manifest):
    """Return (failures, shared_spans). A locator resolves iff the live markdown slice at
    [start_char,end_char) is byte-equal to the recorded quote and that quote occurs exactly once."""
    bad, shared = [], []
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] == "document":
            if loc["start_char"] != 0 or loc["end_char"] != len(md) or loc["quote"] != md:
                bad.append({"asset": a["asset_id"], "why": "document locator is not the whole live markdown"})
            continue
        sliced = md[loc["start_char"]:loc["end_char"]]
        if sliced != loc["quote"]:
            bad.append({"asset": a["asset_id"], "why": "re-slice != quote",
                        "expected_head": loc["quote"][:40], "got_head": sliced[:40]})
        elif md.count(loc["quote"]) != 1:
            bad.append({"asset": a["asset_id"], "why": "quote not unique in live markdown",
                        "count": md.count(loc["quote"])})
        elif loc["unique"] is not True:
            bad.append({"asset": a["asset_id"], "why": "locator.unique flag is not true"})
        elif loc.get("shared_span_with"):
            shared.append({"asset": a["asset_id"], "shared_with": loc["shared_span_with"]})
    return bad, shared


def check_duplicate_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    return sorted({i for i in ids if ids.count(i) > 1})


def main() -> int:
    # ---------- C1 valid_json ----------
    try:
        manifest = json.loads(ART.read_text())
        result = json.loads(RESULT.read_text())
        rec("valid_json", True, {"manifest": str(ART), "result": str(RESULT)})
    except Exception as exc:  # noqa: BLE001
        rec("valid_json", False, {"error": str(exc)})
        OUT.write_text(json.dumps({"checks": checks}, ensure_ascii=False, indent=2))
        return 1

    # ---------- C2 schema_pass ----------
    msch = json.loads(pathlib.Path("schemas/asset_manifest.wp-9840-01.schema.json").read_text())
    try:
        jsonschema.validate(manifest, msch)
        rec("schema_pass_manifest", True, {"schema": "schemas/asset_manifest.wp-9840-01.schema.json",
                                           "assets_validated": len(manifest["assets"])})
    except jsonschema.ValidationError as exc:
        rec("schema_pass_manifest", False, {"error": exc.message, "path": list(exc.path)})
    ksch = json.loads(pathlib.Path("schemas/kf_result.v1.schema.json").read_text())
    try:
        jsonschema.validate(result, ksch)
        rec("schema_pass_envelope", True, {"schema": "schemas/kf_result.v1.schema.json",
                                          "top_level_keys": sorted(result),
                                          "note": "repo schema unmodified; schema_version removed to satisfy additionalProperties=false"})
    except jsonschema.ValidationError as exc:
        rec("schema_pass_envelope", False, {"error": exc.message, "path": list(exc.path)})

    # ---------- C3 source_hash_matches (live re-fetch, independent of frozen copy) ----------
    try:
        tok = api("/auth/login", {"username": USER, "password": PASS})["access_token"]
        payload = api("/tensor/reports/" + REPORT_ID, token=tok)
        md = payload["markdown"]
        live_hash = hashlib.sha256(md.encode()).hexdigest()
        rec("source_hash_recomputed_live", live_hash == manifest["source"]["hash"],
            {"live_sha256": "sha256:" + live_hash, "manifest_sha256": "sha256:" + manifest["source"]["hash"],
             "live_chars": len(md), "bytes_utf8": len(md.encode())})
        rec("source_hash_matches_contract", live_hash == EXPECTED_HASH == result["provenance"]["source_hash"].split(":", 1)[1],
            {"contract": "sha256:" + EXPECTED_HASH, "live": "sha256:" + live_hash,
             "envelope": result["provenance"]["source_hash"]})
        rec("source_chars_match_contract", len(md) == EXPECTED_CHARS == manifest["source"]["chars"],
            {"contract": EXPECTED_CHARS, "live": len(md), "manifest": manifest["source"]["chars"]})
        rec("source_field_markdown", payload.get("markdown") is not None and manifest["source"]["field"] == "markdown",
            {"field": manifest["source"]["field"], "platform_id": payload.get("id")})
    except Exception as exc:  # noqa: BLE001
        rec("source_hash_recomputed_live", False, {"error": "live re-fetch failed: %s" % exc}, status="not_run")
        md = None

    # ---------- C4 source_locator_resolvable (re-slice at [start,end) on LIVE markdown) ----------
    if md is not None:
        bad, shared = check_locators(md, manifest)
        rec("source_locator_resolvable", not bad,
            {"assets_checked": len(manifest["assets"]),
             "char_spans_re_sliced": sum(1 for a in manifest["assets"] if a["locator"]["method"] == "char_span"),
             "failures": bad, "shared_spans": shared,
             "method": "fresh API markdown re-sliced at [start_char,end_char); equality + uniqueness recomputed"},
            status="pass" if not bad else "fail")
        rec("quotes_are_substrings_of_source", all(a["locator"]["quote"] in md for a in manifest["assets"]),
            {"assets": len(manifest["assets"])})
    else:
        rec("source_locator_resolvable", False, {"reason": "no live markdown"}, status="not_run")

    # ---------- C5 no_duplicate_ids ----------
    dups = check_duplicate_ids(manifest)
    rec("no_duplicate_ids", not dups,
        {"assets": len(manifest["assets"]), "duplicates": dups},
        status="pass" if not dups else "fail")

    # ---------- C6 claims evidence / explicit unresolved status ----------
    claims = manifest["claims"]
    offenders = [c for c in claims if not c.get("evidence_locator") and not c.get("status")]
    rec("all_claims_have_evidence_or_explicit_unresolved_status", not offenders,
        {"claims": len(claims), "offenders": offenders,
         "note": "claims=[] by contract scope (objective.register_assets only, classify_report_type=false, "
                 "no extraction); every asset still carries an explicit resolution status "
                 "(%d resolved_in_source / %d referenced_unresolved / %d declared_absent)"
                 % (manifest["counts"]["resolved_in_source"], manifest["counts"]["referenced_unresolved"],
                    manifest["counts"]["declared_absent"])},
        status="pass" if not offenders else "fail")

    # ---------- constraint: do_not_mark_claims_as_verified (structural scan) ----------
    def walk(node, path=""):
        hits = []
        if isinstance(node, dict):
            for k, v in node.items():
                if k.lower() in ("verified", "is_verified", "claim_status", "verification_status"):
                    if not (k == "verification_status" and str(v) == "not_verified"):
                        hits.append(path + "/" + k)
                hits += walk(v, path + "/" + k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                hits += walk(v, "%s/%d" % (path, i))
        elif isinstance(node, str) and node.strip().lower() in ("verified", "verified_true", "true_verified"):
            hits.append(path)
        return hits

    vhits = walk(manifest)
    rec("no_verified_markers", not vhits,
        {"structural_hits": vhits,
         "envelope_verification_status": result["provenance"].get("verification_status"),
         "note": "contract forbids marking claims verified; verification is computed by the platform gate"},
        status="pass" if not vhits else "fail")

    # ---------- extras ----------
    c = manifest["counts"]
    ok_counts = (c["assets"] == len(manifest["assets"])
                 and c["resolved_in_source"] == sum(1 for a in manifest["assets"] if a["resolution"] == "resolved_in_source")
                 and c["referenced_unresolved"] == sum(1 for a in manifest["assets"] if a["resolution"] == "referenced_unresolved")
                 and c["declared_absent"] == sum(1 for a in manifest["assets"] if a["resolution"] == "declared_absent")
                 and sum(c["by_class"].values()) == len(manifest["assets"])
                 and sum(c["by_resolution"].values()) == len(manifest["assets"]))
    rec("counts_consistent", ok_counts, c, status="pass" if ok_counts else "fail")

    idset = {a["asset_id"] for a in manifest["assets"]}
    shared_bad = [{"asset": a["asset_id"], "shared_with": a["locator"]["shared_span_with"]}
                  for a in manifest["assets"]
                  if a["locator"].get("shared_span_with") and a["locator"]["shared_span_with"] not in idset]
    rec("shared_span_documented", not shared_bad, {"violations": shared_bad,
                                                  "sharing": [{"asset": a["asset_id"], "with": a["locator"]["shared_span_with"]}
                                                              for a in manifest["assets"] if a["locator"].get("shared_span_with")]},
        status="pass" if not shared_bad else "fail")

    art_hash = hashlib.sha256(ART.read_bytes()).hexdigest()
    rec("artifact_hash_matches_envelope", art_hash == result["outputs"]["asset_manifest.json"]["artifact_sha256"],
        {"file_sha256": art_hash, "envelope_sha256": result["outputs"]["asset_manifest.json"]["artifact_sha256"]},
        status="pass" if art_hash == result["outputs"]["asset_manifest.json"]["artifact_sha256"] else "fail")

    mirror = DOC_DIR / "asset_manifest.json"
    mir_ok = mirror.exists() and hashlib.sha256(mirror.read_bytes()).hexdigest() == art_hash
    rec("durable_mirror_identical", mir_ok,
        {"mirror": str(mirror),
         "mirror_sha256": hashlib.sha256(mirror.read_bytes()).hexdigest() if mirror.exists() else None,
         "artifact_sha256": art_hash,
         "why": "tp_pusher._EXCLUDE drops artifacts/** and runs/**; docs/ is committed"},
        status="pass" if mir_ok else "fail")

    scope_ok = (manifest["report_id"] == result["report_id"] == REPORT_ID
                and manifest["source"]["uri"] == "tensor://reports/" + REPORT_ID
                and "reports/" + REPORT_ID in result["provenance"]["source_uri"])
    rec("single_report_scope", scope_ok,
        {"report_id": manifest["report_id"], "source_uri": manifest["source"]["uri"],
         "other_report_ids_touched": []},
        status="pass" if scope_ok else "fail")

    failed = [x for x in checks if x["result"] == "fail"]
    notrun = [x for x in checks if x["result"] == "not_run"]
    overall = "FAIL" if failed else ("NOT_RUN" if notrun else "PASS")
    OUT.write_text(json.dumps(dict(
        package_id=PACKAGE_ID, report_id=REPORT_ID,
        verified_by="scripts/kf_verify_9840.py",
        source_hash_recomputed_live="sha256:" + hashlib.sha256(md.encode()).hexdigest() if md else None,
        acceptance={k: [x["result"] for x in checks if x["check"].startswith(k)][0]
                    if any(x["check"].startswith(k) for x in checks) else "not_run"
                    for k in ("valid_json", "schema_pass", "source_locator_resolvable", "source_hash",
                              "no_duplicate_ids", "all_claims_have_evidence_or_explicit_unresolved_status")},
        checks=checks, overall=overall), ensure_ascii=False, indent=2) + "\n")
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    (DOC_DIR / "verification.json").write_text(OUT.read_text())
    for x in checks:
        print("%-8s %-52s %s" % (x["result"].upper(), x["check"],
                                 json.dumps(x["detail"], ensure_ascii=False)[:110]))
    print("overall:", overall, "->", OUT)
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())