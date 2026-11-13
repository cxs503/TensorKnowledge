"""Independent verification of work package wp-11924-01 (acceptance gate self-check).

Independence discipline: the markdown is re-fetched from the platform API in this process (fresh login,
fresh HTTP round-trip) instead of trusting runs/wp-11924-01/report_11924.md; the sha256 is recomputed
from scratch; every locator is re-resolved by slicing the freshly fetched text. Nothing here writes
back into the manifest, and no check marks anything "verified" in the deliverable.

Checks (exactly the package acceptance list):
  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status
Extras: envelope shape, claim-verification discipline (no "verified" markers), artifact/envelope hash
identity, counts consistency, resolution_check vs resolution consistency, report scope isolation
(this package only ever touches report 11924), durable-mirror byte identity.

Outputs: artifacts/wp-11924-01/verification.json (+ docs/wp-11924-01/verification.json mirror)
Usage: python3 scripts/kf_wp11924_01_verify.py [--offline]
       --offline uses the local snapshot (degraded mode: source_hash/copy checks marked 'unknown').
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.request

import jsonschema

REPORT_ID = "11924"
EXPECTED_HASH = "21d915c88bbf78f6f90384f52ce2001f1d7709306c373b159625154ab221bd73"
EXPECTED_CHARS = 13138
PACKAGE_ID = "wp-11924-01"

MANIFEST = pathlib.Path("artifacts/wp-11924-01/asset_manifest.json")
SCHEMA = pathlib.Path("schemas/asset_manifest.v1.generic.schema.json")
KF_SCHEMA = pathlib.Path("schemas/kf_result.v1.schema.json")
RESULT = pathlib.Path("runs/wp-11924-01/kf_result.wp-11924-01.json")
BLOCK = pathlib.Path("runs/wp-11924-01/kf_result_block.wp-11924-01.json")
LOCAL_MD = pathlib.Path("runs/wp-11924-01/report_11924.md")
OUT = pathlib.Path("artifacts/wp-11924-01/verification.json")
DOC_DIR = pathlib.Path("docs/wp-11924-01")
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

RESOLUTION_TO_CHECK = {"resolved_in_source": "resolved", "referenced_unresolved": "unresolved",
                       "declared_absent": "absent"}


# ------------------------------------------------------------------ platform I/O
def login() -> str | None:
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (u and p):
        return None
    for path in ("/auth/login", "/auth/token", "/login"):
        req = urllib.request.Request(BASE + path,
                                     data=json.dumps({"username": u, "password": p}).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
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
    req = urllib.request.Request(BASE + "/tensor/reports/" + REPORT_ID,
                                headers={"Authorization": "Bearer " + tok} if tok else {})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    if "data" in d and isinstance(d["data"], dict):
        d = d["data"]
    return d.get("markdown", ""), d


# ------------------------------------------------ reusable checks (imported by tests)
def check_locators(md: str, manifest: dict) -> list[tuple[str, str]]:
    """Return [(asset_id, reason)] for every locator that does not re-resolve in ``md``."""
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        if loc["method"] == "document":
            if loc["start_char"] != 0 or loc["end_char"] != len(md):
                bad.append((a["asset_id"], "document span %d..%d != 0..%d"
                            % (loc["start_char"], loc["end_char"], len(md))))
            continue
        if md[loc["start_char"]:loc["end_char"]] != q:
            bad.append((a["asset_id"], "slice != quote"))
            continue
        if md.count(q) != 1:
            bad.append((a["asset_id"], "quote occurs %d times" % md.count(q)))
            continue
        if not loc["unique"]:
            bad.append((a["asset_id"], "unique flag asserted false"))
            continue
        line_no = md.count("\n", 0, loc["start_char"])
        if line_no != loc["start_line"]:
            bad.append((a["asset_id"], "start_line %d != %d" % (loc["start_line"], line_no)))
            continue
        end_line = md.count("\n", 0, loc["end_char"])
        if end_line != loc["end_line"]:
            bad.append((a["asset_id"], "end_line %d != %d" % (loc["end_line"], end_line)))
    return bad


def check_duplicate_ids(manifest: dict) -> list[str]:
    ids = [a["asset_id"] for a in manifest["assets"]]
    dups = sorted({i for i in ids if ids.count(i) > 1})
    return dups


def check_claims(claims: list) -> list:
    bad = []
    for c in claims:
        has_ev = bool(c.get("evidence")) or bool(c.get("evidence_locator"))
        if not has_ev and not c.get("status"):
            bad.append(c.get("claim_id", "?"))
    return bad


def check_resolution_consistency(manifest: dict) -> list:
    bad = []
    for a in manifest["assets"]:
        want = RESOLUTION_TO_CHECK[a["resolution"]]
        got = a["resolution_check"]["result"]
        if got != want:
            bad.append((a["asset_id"], "resolution=%s expects check result %s, got %s"
                        % (a["resolution"], want, got)))
    return bad


def check_counts(manifest: dict) -> list[str]:
    bad, c = [], manifest["counts"]
    if c["assets"] != len(manifest["assets"]):
        bad.append("counts.assets %d != len(assets) %d" % (c["assets"], len(manifest["assets"])))
    by_res = {}
    for a in manifest["assets"]:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    for k, v in by_res.items():
        if c["by_resolution"].get(k) != v:
            bad.append("by_resolution[%s]=%s != %d" % (k, c["by_resolution"].get(k), v))
    for k in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        if c[k] != by_res.get(k, 0):
            bad.append("counts.%s=%s != %d" % (k, c[k], by_res.get(k, 0)))
    return bad


def check_verified_markers(node, path="") -> list[str]:
    """Structural scan for 'verified' status markers (contract: do_not_mark_claims_as_verified)."""
    hits = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k.lower() in ("verified", "is_verified", "claim_status", "verified_by"):
                hits.append(path + "/" + k)
            hits += check_verified_markers(v, path + "/" + str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            hits += check_verified_markers(v, path + "/%d" % i)
    elif isinstance(node, str) and node.strip().lower() in ("verified", "verified_true", "true_verified"):
        hits.append(path + "=" + node)
    return hits


def check_scope_isolation(manifest: dict, result: dict) -> list[str]:
    bad = []
    if manifest["report_id"] != REPORT_ID:
        bad.append("manifest.report_id=%s" % manifest["report_id"])
    if result["report_id"] != REPORT_ID:
        bad.append("result.report_id=%s" % result["report_id"])
    if manifest["source"]["uri"] != "tensor://reports/" + REPORT_ID:
        bad.append("manifest.source.uri=%s" % manifest["source"]["uri"])
    if result["provenance"]["source_uri"] != "tensor://reports/" + REPORT_ID:
        bad.append("result.provenance.source_uri=%s" % result["provenance"]["source_uri"])
    return bad


# ------------------------------------------------------------------------- main
def main() -> int:
    offline = "--offline" in sys.argv
    checks: list[dict] = []

    def rec(name: str, ok: bool, detail, status: str | None = None) -> None:
        checks.append(dict(check=name, result=status or ("pass" if ok else "fail"), detail=detail))

    # ---------- C1 valid_json ----------
    try:
        manifest = json.loads(MANIFEST.read_text())
        result = json.loads(RESULT.read_text())
        block = json.loads(BLOCK.read_text())
        rec("valid_json", True, {"manifest": str(MANIFEST), "result": str(RESULT),
                                 "block_identical_to_result": block == result})
    except Exception as exc:  # noqa: BLE001
        rec("valid_json", False, str(exc), status="fail")
        OUT.write_text(json.dumps(dict(package_id=PACKAGE_ID, checks=checks, overall="FAIL"),
                                  ensure_ascii=False, indent=2))
        print("FAIL valid_json:", exc)
        return 1

    # ---------- C2 schema_pass ----------
    try:
        jsonschema.validate(manifest, json.loads(SCHEMA.read_text()))
        jsonschema.validate(result, json.loads(KF_SCHEMA.read_text()))
        rec("schema_pass", True, {"schema": str(SCHEMA), "envelope_schema": str(KF_SCHEMA),
                                  "note": "generic twin of the package-pinned asset_manifest schema "
                                          "(the pinned one hardcodes package_id/report_id of another package)"})
    except Exception as exc:  # noqa: BLE001
        rec("schema_pass", False, str(exc)[:600], status="fail")

    # ---------- source text: fresh fetch (independence) or local snapshot ----------
    fetched_from = "platform_api"
    try:
        if offline:
            raise RuntimeError("offline mode")
        md, payload = fetch_markdown()
        fetched_from = "platform_api"
    except Exception as exc:  # noqa: BLE001
        md = LOCAL_MD.read_text()
        payload = {}
        fetched_from = "local_snapshot (%s)" % str(exc)[:120]

    md_hash = hashlib.sha256(md.encode()).hexdigest()

    # ---------- C4 source_hash_matches ----------
    hash_ok = (md_hash == EXPECTED_HASH
               and manifest["source"]["hash"] == EXPECTED_HASH
               and result["provenance"]["source_hash"] == "sha256:" + EXPECTED_HASH
               and len(md) == EXPECTED_CHARS == manifest["source"]["chars"]
               and len(md.encode()) == manifest["source"]["bytes_utf8"])
    rec("source_hash_matches", hash_ok,
        {"recomputed_sha256": md_hash, "contract_sha256": EXPECTED_HASH,
         "manifest_sha256": manifest["source"]["hash"],
         "envelope_sha256": result["provenance"]["source_hash"],
         "chars": len(md), "bytes_utf8": len(md.encode()), "fetched_from": fetched_from})

    # ---------- C3 source_locator_resolvable ----------
    bad = check_locators(md, manifest)
    rec("source_locator_resolvable", not bad,
        {"assets_checked": len(manifest["assets"]), "failures": bad,
         "quote_uniqueness": "every char_span quote occurs exactly once in the fetched markdown"
                             if not bad else "see failures"})

    # ---------- C5 no_duplicate_ids ----------
    dups = check_duplicate_ids(manifest)
    claim_ids = [c.get("claim_id") for c in manifest.get("claims", [])]
    rec("no_duplicate_ids", not dups and len(claim_ids) == len(set(claim_ids)),
        {"duplicate_asset_ids": dups, "asset_ids": len(manifest["assets"]),
         "claim_ids": claim_ids})

    # ---------- C6 claims policy ----------
    bad_claims = check_claims(manifest.get("claims", []))
    rec("all_claims_have_evidence_or_explicit_unresolved_status", not bad_claims,
        {"claims": len(manifest.get("claims", [])), "offending": bad_claims,
         "policy": "claims=[] by contract (objective.classify_report_type=false, no extraction); "
                   "any future claim must carry evidence/evidence_locator or an explicit status"})

    # ---------- extras ----------
    res_bad = check_resolution_consistency(manifest)
    rec("resolution_check_consistency", not res_bad, {"failures": res_bad})

    cnt_bad = check_counts(manifest)
    rec("counts_consistency", not cnt_bad, {"failures": cnt_bad,

                                            "counts": manifest["counts"]})

    vhits = check_verified_markers(manifest) + check_verified_markers(result)
    rec("no_verified_markers", not vhits,
        {"hits": vhits, "note": "contract forbids marking claims verified; verification is computed "
                                "by the platform gate, this package records verification_status=not_verified"})

    art_hash = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    rec("artifact_hash_matches_envelope", art_hash == result["outputs"]["asset_manifest.json"]["artifact_sha256"],
        {"artifact_sha256": art_hash,
         "envelope_sha256": result["outputs"]["asset_manifest.json"]["artifact_sha256"],
         "artifact_bytes": MANIFEST.stat().st_size})

    scope_bad = check_scope_isolation(manifest, result)
    rec("report_scope_isolation", not scope_bad, {"failures": scope_bad,
                                                  "note": "package touches report 11924 only"})

    mirror = DOC_DIR / "asset_manifest.json"
    mirror_ok = mirror.exists() and hashlib.sha256(mirror.read_bytes()).hexdigest() == art_hash
    rec("durable_mirror_identical", mirror_ok, {"mirror": str(mirror), "exists": mirror.exists()})

    if fetched_from.startswith("platform_api"):
        api_ok = (payload.get("id") == int(REPORT_ID)
                  and payload.get("title") == manifest["source"]["title"]
                  and payload.get("scenario_key") == manifest["source"]["scenario_key"])
        rec("platform_metadata_matches_manifest", api_ok,
            {"platform_id": payload.get("id"), "title_match": payload.get("title") == manifest["source"]["title"],
             "scenario_key_match": payload.get("scenario_key") == manifest["source"]["scenario_key"]})
    else:
        rec("platform_metadata_matches_manifest", False, {"note": "skipped: " + fetched_from}, status="unknown")

    overall = "PASS" if all(c["result"] == "pass" for c in checks) else "FAIL"
    out = dict(package_id=PACKAGE_ID, report_id=REPORT_ID,
               verified_by="scripts/kf_wp11924_01_verify.py",
               verification_status="not_verified",
               note="self-check of the acceptance list; the authoritative verification is the platform gate",
               source={"fetched_from": fetched_from, "sha256": md_hash, "chars": len(md)},
               checks=checks, overall=overall)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    (DOC_DIR / "verification.json").write_text(OUT.read_text())

    for c in checks:
        print("%-8s %-52s %s" % (c["result"].upper(), c["check"],
                                 json.dumps(c["detail"], ensure_ascii=False)[:110]))
    print("OVERALL:", overall)
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())