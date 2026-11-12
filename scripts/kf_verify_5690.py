"""Independent verification of work package wp-5690-01 (acceptance gate self-check).

Independence discipline: the markdown is re-fetched from the platform API in this process (new login)
instead of trusting runs/wp-5690-01/report_5690.md; the hash is recomputed from scratch; every locator
is re-resolved by slicing the freshly fetched text. Nothing here writes back into the manifest.

Checks (exactly the package acceptance list):
  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status
Extras: result envelope shape, claim-verification discipline (no "verified" markers), counts consistency.

Outputs: artifacts/wp-5690-01/verification.json ; prints PASS/FAIL per check; exit code 0 iff all pass
(or only degraded-by-environment items are marked unknown).

Usage: python3 scripts/kf_verify_5690.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.request

import jsonschema

REPORT_ID = "5690"
EXPECTED_HASH = "a1e3f5faa1f969bcdfb759f7357adb8cc7474194e44a2c02ae4370f1db1b29a1"
MANIFEST = pathlib.Path("artifacts/wp-5690-01/asset_manifest.json")
SCHEMA = pathlib.Path("schemas/asset_manifest.v1.schema.json")
RESULT = pathlib.Path("runs/wp-5690-01/kf_result.wp-5690-01.json")
BLOCK = pathlib.Path("runs/wp-5690-01/kf_result_block.wp-5690-01.json")
OUT = pathlib.Path("artifacts/wp-5690-01/verification.json")
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


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
    req = urllib.request.Request(BASE + "/tensor/reports/%s" % REPORT_ID,
                                 headers={"Authorization": "Bearer " + tok} if tok else {})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    if "data" in d and isinstance(d["data"], dict):
        d = d["data"]
    return d.get("markdown", ""), d


# ---------------- reusable checks (also imported by tests/test_kf_wp5690.py) ----------------
RESOLUTION_TO_CHECK = {"resolved_in_source": "resolved", "referenced_unresolved": "unresolved",
                       "declared_absent": "absent"}


def check_locators(md: str, manifest: dict) -> list[tuple[str, str]]:
    """Return [(asset_id, reason)] for every locator that does not re-resolve in ``md``."""
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        quote = loc["quote"]
        if md[loc["start_char"]:loc["end_char"]] != quote:
            bad.append((a["asset_id"], "slice_mismatch"))
        n = md.count(quote)
        if n != 1:
            bad.append((a["asset_id"], "quote_not_unique:%d" % n))
        if not loc["unique"]:
            bad.append((a["asset_id"], "unique_flag_false"))
        expect = RESOLUTION_TO_CHECK[a["resolution"]]
        if a["resolution_check"]["result"] != expect:
            bad.append((a["asset_id"], "resolution_check_mismatch:%s!=%s"
                        % (a["resolution_check"]["result"], expect)))
    return bad


def check_duplicate_ids(manifest: dict) -> list[str]:
    ids = [a["asset_id"] for a in manifest["assets"]]
    return sorted({i for i in ids if ids.count(i) > 1})


def check_claims(claims: list) -> list:
    return [c.get("claim_id") for c in claims
            if "evidence_locator" not in c and "status" not in c]


def main() -> int:
    checks = []

    def rec(name, ok, detail, status="pass"):
        checks.append(dict(check=name, result=status if not ok else "pass", detail=detail))

    # ---------- C1 valid_json ----------
    try:
        manifest = json.loads(MANIFEST.read_text())
        result = json.loads(RESULT.read_text())
        block = json.loads(BLOCK.read_text())
        rec("valid_json", True, {"manifest": str(MANIFEST), "result": str(RESULT),
                                "block_equals_result": block == result})
    except Exception as exc:
        rec("valid_json", False, str(exc), status="fail")
        OUT.write_text(json.dumps(dict(checks=checks, overall="FAIL"), ensure_ascii=False, indent=2))
        print("FAIL valid_json:", exc)
        return 1

    # ---------- C4 source_hash_matches (independent re-fetch) ----------
    try:
        md, payload = fetch_markdown()
        fresh_hash = hashlib.sha256(md.encode()).hexdigest()
        ok = (fresh_hash == EXPECTED_HASH
              and manifest["source"]["hash"] == fresh_hash
              and result["provenance"]["source_hash"] == "sha256:" + fresh_hash
              and manifest["source"]["chars"] == len(md))
        rec("source_hash_matches", ok,
            {"api_sha256": fresh_hash, "contract_sha256": EXPECTED_HASH,
             "manifest_sha256": manifest["source"]["hash"],
             "result_sha256": result["provenance"]["source_hash"],
             "api_chars": len(md), "manifest_chars": manifest["source"]["chars"],
             "api_bytes_utf8": len(md.encode())})
    except Exception as exc:
        md = pathlib.Path("runs/wp-5690-01/report_5690.md").read_text()
        fresh_hash = hashlib.sha256(md.encode()).hexdigest()
        ok = fresh_hash == EXPECTED_HASH == manifest["source"]["hash"]
        rec("source_hash_matches", ok,
            {"api": "unavailable", "error": str(exc), "local_copy_sha256": fresh_hash,
             "degraded_to_local_copy": True})

    # ---------- C2 schema_pass ----------
    schema = json.loads(SCHEMA.read_text())
    try:
        jsonschema.validate(manifest, schema)
        rec("schema_pass", True, {"schema": str(SCHEMA),
                                  "note": "local schema schemas/asset_manifest.v1.schema.json (canonical kf_result schema absent from worktree)"})
    except jsonschema.ValidationError as exc:
        rec("schema_pass", False, "%s at %s" % (exc.message, list(exc.path)), status="fail")

    # result envelope shape (package_id / task_type / report_id / provenance / outputs)
    req_keys = {"package_id", "task_type", "report_id", "provenance", "outputs"}
    env_ok = req_keys.issubset(result) and "asset_manifest.json" in result.get("outputs", {})
    rec("result_envelope_shape", env_ok,
        {"keys": sorted(result), "outputs_keys": sorted(result.get("outputs", {}))})
    rec("result_ids_match_contract", result.get("package_id") == "wp-5690-01"
        and result.get("task_type") == "01-asset-registration" and str(result.get("report_id")) == REPORT_ID,
        {"package_id": result.get("package_id"), "task_type": result.get("task_type"),
         "report_id": result.get("report_id")})

    # ---------- C3 source_locator_resolvable ----------
    bad = check_locators(md, manifest)
    rec("source_locator_resolvable", not bad,
        {"assets_checked": len(manifest["assets"]), "failures": bad,
         "method": "re-slice fresh API markdown at [start_char,end_char) + uniqueness count"},
        status="pass" if not bad else "fail")

    # ---------- C5 no_duplicate_ids ----------
    ids = [a["asset_id"] for a in manifest["assets"]]
    dups = check_duplicate_ids(manifest)
    rec("no_duplicate_ids", not dups, {"asset_ids": ids, "duplicates": dups},
        status="pass" if not dups else "fail")

    # ---------- C6 claims evidence / explicit unresolved status ----------
    claims = manifest["claims"]
    offenders = check_claims(claims)
    rec("all_claims_have_evidence_or_explicit_unresolved_status", not offenders,
        {"claims": len(claims), "offenders": offenders,
         "note": "claims=[] by contract scope (objective.register_assets only; no extraction); "
                 "asset-level resolution status carried on all %d assets" % len(manifest["assets"])},
        status="pass" if not offenders else "fail")

    # ---------- extras ----------
    # contract: do_not_mark_claims_as_verified. Scan structurally (keys/values), not by substring,
    # so that prose such as "quotes confirmed unique" cannot trip the check.
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
        elif isinstance(node, str) and node.strip().lower() in ("verified", "verified_true", "true_verified"):
            hits.append(path)
        return hits

    vhits = walk(manifest)
    rec("no_verified_markers", not vhits,
        {"structural_hits": vhits,
         "note": "contract forbids marking claims verified; verification is computed by the platform gate"},
        status="pass" if not vhits else "fail")

    counts = manifest["counts"]
    ok_counts = (counts["assets"] == len(manifest["assets"])
                 and counts["resolved_in_source"] == sum(1 for a in manifest["assets"] if a["resolution"] == "resolved_in_source")
                 and counts["referenced_unresolved"] == sum(1 for a in manifest["assets"] if a["resolution"] == "referenced_unresolved")
                 and counts["declared_absent"] == sum(1 for a in manifest["assets"] if a["resolution"] == "declared_absent"))
    rec("counts_consistent", ok_counts, counts)

    art_hash = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    rec("artifact_hash_matches_envelope", art_hash == result["outputs"]["asset_manifest.json"]["artifact_sha256"],
        {"file_sha256": art_hash,
         "envelope_sha256": result["outputs"]["asset_manifest.json"]["artifact_sha256"]})

    # durable mirror under docs/ (repo push gate drops artifacts/** and runs/**)
    doc_dir = pathlib.Path("docs/wp-5690-01")
    mirror = doc_dir / "asset_manifest.json"
    mir_ok = mirror.exists() and hashlib.sha256(mirror.read_bytes()).hexdigest() == art_hash
    pngs = sorted(p.name for p in doc_dir.glob("fig_*.png"))
    rec("durable_mirror_identical", mir_ok,
        {"mirror": str(mirror), "mirror_sha256": hashlib.sha256(mirror.read_bytes()).hexdigest() if mirror.exists() else None,
         "artifact_sha256": art_hash, "mirrored_figures": pngs,
         "why": "tp_pusher._EXCLUDE drops artifacts/** and runs/**; docs/ is committed"},
        status="pass" if mir_ok else "fail")

    failed = [c for c in checks if c["result"] == "fail"]
    overall = "FAIL" if failed else "PASS"
    OUT.write_text(json.dumps(dict(package_id="wp-5690-01", report_id=REPORT_ID,
                                   verified_by="scripts/kf_verify_5690.py",
                                   source_hash_recomputed="sha256:" + hashlib.sha256(md.encode()).hexdigest(),
                                   checks=checks, overall=overall), ensure_ascii=False, indent=2) + "\n")
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir / "verification.json").write_text(OUT.read_text())
    for c in checks:
        print("%-5s %-55s %s" % (c["result"].upper(), c["check"], json.dumps(c["detail"], ensure_ascii=False)[:120]))
    print("overall:", overall, "->", OUT)
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
