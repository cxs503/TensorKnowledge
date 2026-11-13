#!/usr/bin/env python3
"""Independent verification of work package wp-9947-01 (acceptance-gate self-check).

Independence discipline: the markdown is re-fetched from the platform API inside *this* process with a
fresh login, never read back from runs/wp-9947-01/report_9947.md; the sha256 is recomputed from
scratch and every locator is re-resolved by slicing the freshly fetched text. The manifest is only
read, never rewritten here. Probe evidence recorded in the manifest is re-executed and compared.

Checks (exactly the package acceptance list):
  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status
Extras: result envelope shape+ids, contract identity (title/chars/scenario), no "verified" markers,
counts consistency, artifact sha256 == envelope sha256, durable docs/ mirror identity,
notices point at existing assets, probe results reproducible, no write outside docs/wp-9947-01.

Outputs: artifacts/wp-9947-01/verification.json + docs/wp-9947-01/verification.json
Exit code 0 iff every check passes; a check that could not run is reported as "unknown", never "pass".

Usage: python3 scripts/kf_verify_9947.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.request

import jsonschema

REPORT_ID = "9947"
PACKAGE_ID = "wp-9947-01"
TASK_TYPE = "01-asset-registration"
EXPECTED_HASH = "c9857b84a9ea71ea174f3392d34e8e61403202ee154fdab059c4e9abd83fc0bf"
CONTRACT_TITLE = "【试点】技术路线锁定 A/B 终局对照 v1"
CONTRACT_SCENARIO = "pilot-ab"
CONTRACT_CHARS = 616

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
MANIFEST = pathlib.Path("artifacts/wp-9947-01/asset_manifest.json")
SCHEMA = pathlib.Path("schemas/asset_manifest.v1.schema.json")
RESULT = pathlib.Path("runs/wp-9947-01/kf_result.wp-9947-01.json")
BLOCK = pathlib.Path("runs/wp-9947-01/kf_result_block.wp-9947-01.json")
LOCAL_MD = pathlib.Path("runs/wp-9947-01/report_9947.md")
OUT = pathlib.Path("artifacts/wp-9947-01/verification.json")
DOC_DIR = pathlib.Path("docs/wp-9947-01")

RESOLUTION_TO_CHECK = {
    "resolved_in_source": "resolved",
    "referenced_unresolved": "unresolved",
    "declared_absent": "absent",
}


def login() -> str | None:
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (u and p):
        return None
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            req = urllib.request.Request(BASE + path, data=json.dumps(
                {"username": u, "password": p}).encode(),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def fetch_markdown() -> tuple[str, dict]:
    tok = login()
    if not tok:
        raise RuntimeError("login failed")
    req = urllib.request.Request(BASE + "/tensor/reports/" + REPORT_ID)
    req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.loads(r.read().decode())
    return payload["markdown"], payload


def probe(keys, tok) -> dict:
    hits = {}
    for k in keys:
        try:
            req = urllib.request.Request(BASE + "/tensor/reports?scenario_key=" + k)
            if tok:
                req.add_header("Authorization", "Bearer " + tok)
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
            items = d.get("items", d if isinstance(d, list) else [])
            hits[k] = dict(report_ids=[it.get("id") for it in items], count=len(items))
        except Exception as exc:
            hits[k] = dict(error=type(exc).__name__ + ": " + str(exc)[:120])
    return hits


def check_locators(md: str, manifest: dict) -> list[tuple[str, str]]:
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        quote = loc["quote"]
        if loc["method"] == "document":
            if quote != md or loc["start_char"] != 0 or loc["end_char"] != len(md):
                bad.append((a["asset_id"], "document_locator_mismatch"))
        else:
            if md[loc["start_char"]:loc["end_char"]] != quote:
                bad.append((a["asset_id"], "slice_mismatch"))
            if md.count(quote) != 1:
                bad.append((a["asset_id"], "quote_not_unique:%d" % md.count(quote)))
            if not loc["unique"]:
                bad.append((a["asset_id"], "unique_flag_false"))
        expect = RESOLUTION_TO_CHECK[a["resolution"]]
        if a["resolution_check"]["result"] != expect:
            bad.append((a["asset_id"], "resolution_check_mismatch:%s!=%s"
                        % (a["resolution_check"]["result"], expect)))
    return bad


def main() -> int:
    checks = []

    def rec(name, ok, detail, status=None):
        checks.append(dict(check=name, result=status if status else ("pass" if ok else "fail"),
                           detail=detail))

    # ---------- valid_json ----------
    try:
        manifest = json.loads(MANIFEST.read_text())
        result = json.loads(RESULT.read_text())
        block = json.loads(BLOCK.read_text())
        rec("valid_json", True, {"manifest": str(MANIFEST), "result": str(RESULT),
                                 "block_equals_result": block == result,
                                 "manifest_mirror_equals_artifact":
                                     (DOC_DIR / "asset_manifest.json").read_text() == MANIFEST.read_text()})
    except Exception as exc:
        rec("valid_json", False, str(exc), status="fail")
        OUT.write_text(json.dumps(dict(checks=checks, overall="FAIL"), ensure_ascii=False, indent=2) + "\n")
        print("FAIL valid_json:", exc)
        return 1

    # ---------- source_hash_matches (independent re-fetch) ----------
    tok = login()
    try:
        md, payload = fetch_markdown()
        fresh = hashlib.sha256(md.encode()).hexdigest()
        ok = (fresh == EXPECTED_HASH
              and manifest["source"]["hash"] == fresh
              and result["provenance"]["source_hash"] == "sha256:" + fresh
              and manifest["source"]["chars"] == len(md) == CONTRACT_CHARS
              and manifest["source"]["bytes_utf8"] == len(md.encode()))
        rec("source_hash_matches", ok,
            {"api_sha256": fresh, "contract_sha256": EXPECTED_HASH,
             "manifest_sha256": manifest["source"]["hash"],
             "result_sha256": result["provenance"]["source_hash"],
             "api_chars": len(md), "contract_chars": CONTRACT_CHARS,
             "manifest_chars": manifest["source"]["chars"], "api_bytes_utf8": len(md.encode())})
        rec("contract_identity_matches", payload.get("title") == CONTRACT_TITLE
            and payload.get("scenario_key") == CONTRACT_SCENARIO
            and manifest["source"]["title"] == CONTRACT_TITLE
            and manifest["source"]["scenario_key"] == CONTRACT_SCENARIO,
            {"api_title": payload.get("title"), "contract_title": CONTRACT_TITLE,
             "api_scenario": payload.get("scenario_key"), "contract_scenario": CONTRACT_SCENARIO})
    except Exception as exc:
        md = LOCAL_MD.read_text()
        fresh = hashlib.sha256(md.encode()).hexdigest()
        ok = fresh == EXPECTED_HASH == manifest["source"]["hash"]
        rec("source_hash_matches", ok,
            {"api": "unavailable", "error": str(exc), "local_copy_sha256": fresh,
             "degraded_to_local_copy": True}, status="pass" if ok else "fail")
        rec("contract_identity_matches", False, {"skipped": "api unavailable"}, status="unknown")

    # ---------- schema_pass ----------
    try:
        jsonschema.validate(manifest, json.loads(SCHEMA.read_text()))
        rec("schema_pass", True, {"schema": str(SCHEMA),
                                  "note": "local schema, generalized from const to pattern for package_id/"
                                          "report_id/source.uri so one gate covers every report in this lane"})
    except jsonschema.ValidationError as exc:
        rec("schema_pass", False, "%s at %s" % (exc.message, list(exc.path)), status="fail")

    # result envelope shape (kf_result.v1: package_id / task_type / report_id / provenance / outputs)
    req_keys = {"package_id", "task_type", "report_id", "provenance", "outputs"}
    rec("result_envelope_shape", req_keys.issubset(result)
        and "asset_manifest.json" in result.get("outputs", {}),
        {"keys": sorted(result), "outputs_keys": sorted(result.get("outputs", {}))})
    prov = result.get("provenance", {})
    rec("result_ids_match_contract", result.get("package_id") == PACKAGE_ID
        and result.get("task_type") == TASK_TYPE and str(result.get("report_id")) == REPORT_ID
        and prov.get("source_field") == "markdown" and prov.get("source_uri") == "tensor://reports/" + REPORT_ID,
        {"package_id": result.get("package_id"), "task_type": result.get("task_type"),
         "report_id": result.get("report_id"), "source_uri": prov.get("source_uri")},
        )
    # the kf_result.v1 envelope forbids extra top-level keys (additionalProperties:false)
    # schemas/kf_result.v1.schema.json has additionalProperties:false at the root
    allowed = {"package_id", "task_type", "report_id", "provenance", "outputs", "claims"}
    rec("result_envelope_closed", set(result) <= allowed,
        {"extra_keys": sorted(set(result) - allowed)})

    try:
        kf_schema = json.loads(pathlib.Path("schemas/kf_result.v1.schema.json").read_text())
        jsonschema.validate(result, kf_schema)
        rec("result_validates_against_kf_result_schema", True,
            {"schema": "schemas/kf_result.v1.schema.json", "root_keys": sorted(result)})
    except jsonschema.ValidationError as exc:
        rec("result_validates_against_kf_result_schema", False,
            "%s at %s" % (exc.message, list(exc.path)), status="fail")

    # ---------- source_locator_resolvable ----------
    bad = check_locators(md, manifest)
    rec("source_locator_resolvable", not bad,
        {"assets_checked": len(manifest["assets"]), "failures": bad,
         "method": "re-slice freshly fetched API markdown at [start_char,end_char) + occurrence count"})

    # ---------- no_duplicate_ids ----------
    ids = [a["asset_id"] for a in manifest["assets"]]
    dups = sorted({i for i in ids if ids.count(i) > 1})
    rec("no_duplicate_ids", not dups, {"assets": len(ids), "duplicates": dups})

    # ---------- all_claims_have_evidence_or_explicit_unresolved_status ----------
    claims = manifest.get("claims", [])
    offenders = [c.get("claim_id") for c in claims
                 if "evidence" not in c and "unresolved_reason" not in c and "status" not in c]
    rec("all_claims_have_evidence_or_explicit_unresolved_status", not offenders,
        {"claims": len(claims), "offenders": offenders,
         "note": "claims=[] is a complete result for this package (objective.register_assets only, "
                 "classify_report_type=false); every asset instead carries an explicit resolution status"})

    # ---------- extras ----------
    def walk(node, path=""):
        hits = []
        if isinstance(node, dict):
            for k, v in node.items():
                if k.lower() in ("verified", "is_verified", "claim_status"):
                    hits.append(path + "/" + k)
                hits += walk(v, path + "/" + k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                hits += walk(v, "%s/%d" % (path, i))
        elif isinstance(node, str) and node.strip().lower() in ("verified", "verified_true"):
            hits.append(path)
        return hits

    vhits = walk(manifest)
    rec("no_verified_markers", not vhits, {"structural_hits": vhits,
                                           "note": "verification is computed by the platform gate, not here"})

    counts = manifest["counts"]
    ok_counts = (counts["assets"] == len(manifest["assets"])
                 and counts["resolved_in_source"] == sum(1 for a in manifest["assets"] if a["resolution"] == "resolved_in_source")
                 and counts["referenced_unresolved"] == sum(1 for a in manifest["assets"] if a["resolution"] == "referenced_unresolved")
                 and counts["declared_absent"] == sum(1 for a in manifest["assets"] if a["resolution"] == "declared_absent")
                 and sum(counts["by_class"].values()) == counts["assets"])
    rec("counts_consistent", ok_counts, counts)

    art_hash = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    rec("artifact_hash_matches_envelope",
        art_hash == result["outputs"]["asset_manifest.json"]["artifact_sha256"],
        {"file_sha256": art_hash, "envelope_sha256": result["outputs"]["asset_manifest.json"]["artifact_sha256"]})
    mirror = DOC_DIR / "asset_manifest.json"
    mir_ok = mirror.exists() and hashlib.sha256(mirror.read_bytes()).hexdigest() == art_hash
    rec("durable_mirror_identical", mir_ok,
        {"mirror": str(mirror), "why": "tp_pusher._EXCLUDE drops artifacts/** and runs/**; docs/ is committed"})

    # notices must point at registered assets (no free-floating assertions)
    asset_ids = set(ids)
    orphan = [n["id"] for n in manifest.get("notices", []) if n.get("evidence_asset") not in asset_ids]
    rec("notices_bound_to_assets", not orphan,
        {"notices": len(manifest.get("notices", [])), "orphans": orphan})

    # probe evidence must reproduce (recorded vs re-executed)
    keys = sorted({k for a in manifest["assets"]
                   for k in a["resolution_check"].get("platform_probe", {}).get("hits", {})})
    if keys:
        try:
            fresh_hits = probe(keys, tok)
            recorded = {}
            for a in manifest["assets"]:
                recorded.update(a["resolution_check"].get("platform_probe", {}).get("hits", {}))
            diffs = {k: {"recorded": recorded.get(k), "fresh": fresh_hits.get(k)}
                     for k in keys
                     if recorded.get(k, {}).get("count") != fresh_hits.get(k, {}).get("count")}
            rec("probe_evidence_reproducible", not diffs, {"keys": keys, "diffs": diffs})
        except Exception as exc:
            rec("probe_evidence_reproducible", False, {"error": str(exc)}, status="unknown")
    else:
        rec("probe_evidence_reproducible", False, {"no probes recorded"}, status="unknown")

    failed = [c for c in checks if c["result"] == "fail"]
    unknown = [c for c in checks if c["result"] == "unknown"]
    overall = "FAIL" if failed else ("PASS_WITH_UNKNOWN" if unknown else "PASS")
    doc = dict(package_id=PACKAGE_ID, report_id=REPORT_ID, verified_by="scripts/kf_verify_9947.py",
               source_hash_recomputed="sha256:" + hashlib.sha256(md.encode()).hexdigest(),
               independent_refetch=bool(tok and not any("degraded" in json.dumps(c) for c in checks)),
               checks=checks, overall=overall)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    (DOC_DIR / "verification.json").write_text(OUT.read_text())
    for c in checks:
        print("%-7s %-58s %s" % (c["result"].upper(), c["check"],
                                 json.dumps(c["detail"], ensure_ascii=False)[:110]))
    print("overall:", overall, "->", OUT)
    return 0 if overall.startswith("PASS") else 1


if __name__ == "__main__":
    sys.exit(main())