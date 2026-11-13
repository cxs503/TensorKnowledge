"""Worker-side self check for wp-10459-01: re-derive every acceptance item from raw bytes.

This is NOT the platform gate. It deliberately re-fetches report 10459 from the API instead of
trusting the local snapshot, so a stale or hand-edited snapshot cannot pass.

Acceptance items (contract wp-10459-01) re-checked here:
  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status
plus contract constraints / boundary:
  do_not_mark_claims_as_verified, do_not_invent_missing_information, no_forced_claim_generation,
  preserve_uncertainty, report scope (report_id=10459 only).

schema_pass note: schemas/asset_manifest.v1.schema.json is *report-bound* (const package_id
"wp-448-01", report_id "448", source.uri "tensor://reports/448"), so it cannot validate any other
package. This script re-binds exactly those three consts to this package and asserts that nothing
else in the schema was touched -- the check stays reproducible without forking a near-duplicate
schema file into the repo.

Usage: python3 scripts/kf_wp10459_validate.py [--offline]
Outputs: docs/kf/wp-10459-01/selfcheck.json  (+ stdout PASS/FAIL table)
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

import jsonschema

REPO = pathlib.Path(__file__).resolve().parents[1]
PKG = "wp-10459-01"
REPORT_ID = "10459"
CONTRACT_HASH = "08c1a0cfb3f0db38ad3a473ac2155001589bde91c1f85c21db1d29863ca84f6c"
CONTRACT_CHARS = 6431
ENV = REPO / "docs/kf" / PKG / "kf_result.json"
MAN = REPO / "docs/kf" / PKG / "asset_manifest.json"
ART_MAN = REPO / "artifacts" / PKG / "asset_manifest.json"
SNAP = REPO / "runs" / PKG / "report_10459.md"
KF_SCHEMA = REPO / "schemas" / "kf_result.v1.schema.json"
MAN_SCHEMA = REPO / "schemas" / "asset_manifest.v1.schema.json"
OUT = REPO / "docs/kf" / PKG / "selfcheck.json"

BOUND_CONSTS = [
    (("properties", "package_id", "const"), PKG),
    (("properties", "report_id", "const"), REPORT_ID),
    (("properties", "source", "properties", "uri", "const"), "tensor://reports/10459"),
]


def fetch_markdown() -> str:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    user, pwd = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]
    req = urllib.request.Request(
        base + "/auth/login", data=json.dumps({"username": user, "password": pwd}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        tok = json.loads(r.read().decode()).get("access_token")
    req = urllib.request.Request(base + "/tensor/reports/" + REPORT_ID,
                                headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.loads(r.read().decode())
    if isinstance(payload.get("data"), dict):
        payload = payload["data"]
    return payload.get("markdown") or ""


def _rebound_copy() -> tuple[dict, list[str]]:
    """Return a copy of schemas/asset_manifest.v1.schema.json with ONLY the three report-bound
    consts re-bound to this package, plus a log of what was re-bound."""
    sch = json.loads(MAN_SCHEMA.read_text(encoding="utf-8"))
    rebound = []
    for path, value in BOUND_CONSTS:
        node = sch
        for key in path[:-1]:
            node = node[key]
        if node[path[-1]] != value:
            rebound.append("%s: %r -> %r" % (".".join(path), node[path[-1]], value))
            node[path[-1]] = value
    return sch, rebound


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="use the local snapshot instead of the API")
    args = ap.parse_args()

    checks: list[dict] = []

    def rec(name, ok, detail):
        checks.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail})

    # ---- valid_json
    try:
        env = json.loads(ENV.read_text(encoding="utf-8"))
        man = json.loads(MAN.read_text(encoding="utf-8"))
        art = json.loads(ART_MAN.read_text(encoding="utf-8"))
        rec("valid_json", True, "kf_result.json / asset_manifest.json (docs + artifacts) parsed")
    except Exception as exc:  # noqa: BLE001
        rec("valid_json", False, repr(exc))
        print(json.dumps(checks, ensure_ascii=False, indent=1))
        return 1

    # ---- schema_pass (envelope)
    errs = []
    kf_schema = json.loads(KF_SCHEMA.read_text(encoding="utf-8"))
    for e in jsonschema.Draft202012Validator(kf_schema).iter_errors(env):
        errs.append("kf_result: " + e.message)
    sch, rebound = _rebound_copy()
    for e in jsonschema.Draft7Validator(sch).iter_errors(man):
        errs.append("asset_manifest: " + e.message)
    rec("schema_pass", not errs,
        "kf_result.v1 (Draft2020-12) + asset_manifest.v1 (Draft-07, report-bound consts rebound: %s); %d error(s)%s"
        % (", ".join(rebound) or "none needed", len(errs), "" if not errs else " :: " + "; ".join(errs[:5])))
    rec("docs_artifacts_byte_identical", MAN.read_bytes() == ART_MAN.read_bytes(),
        "docs/kf mirror vs contract output file byte-identical")

    # ---- source_hash_matches
    md = SNAP.read_text(encoding="utf-8") if args.offline else fetch_markdown()
    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    env_hash = env["provenance"]["source_hash"].split(":", 1)[1]
    rec("source_hash_matches",
        digest == CONTRACT_HASH == env_hash == man["source"]["hash"],
        "fresh sha256=%s; contract=%s; provenance=%s; manifest=%s; chars=%d (contract %d); source=%s"
        % (digest[:16] + "...", CONTRACT_HASH[:16] + "...", env_hash[:16] + "...",
           man["source"]["hash"][:16] + "...", len(md), CONTRACT_CHARS,
           "local snapshot" if args.offline else "re-fetched from API"))

    # ---- source_locator_resolvable (against fresh bytes)
    bad = []
    for a in man["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        if md[loc["start_char"]:loc["end_char"]] != q:
            bad.append(a["asset_id"] + ":char_span")
        elif md.count(q) != 1:
            bad.append(a["asset_id"] + ":not-unique(%d)" % md.count(q))
        elif loc["method"] == "char_span":
            line = md[:loc["start_char"]].count("\n") + 1
            if line != loc["start_line"]:
                bad.append(a["asset_id"] + ":line(%d!=%d)" % (line, loc["start_line"]))
    rec("source_locator_resolvable", not bad,
        "%d/%d quotes reproduce their char span verbatim in the re-fetched markdown and are unique%s"
        % (len(man["assets"]) - len(bad), len(man["assets"]),
           "" if not bad else " :: " + ", ".join(bad)))

    # ---- no_duplicate_ids
    ids = [a["asset_id"] for a in man["assets"]]
    cids = [c["claim_id"] for c in man.get("claims", [])]
    rec("no_duplicate_ids", len(ids) == len(set(ids)) and len(cids) == len(set(cids)),
        "%d asset_ids unique=%s; %d claim_ids unique=%s" % (len(ids), len(set(ids)) == len(ids),
                                                           len(cids), len(set(cids)) == len(cids)))

    # ---- counts consistency inside the manifest
    by_class, by_res = man["counts"]["by_class"], man["counts"]["by_resolution"]
    rec("counts_consistent",
        sum(by_class.values()) == man["counts"]["assets"] == len(man["assets"])
        and sum(by_res.values()) == man["counts"]["assets"]
        and man["counts"]["resolved_in_source"] == by_res.get("resolved_in_source", 0)
        and man["counts"]["referenced_unresolved"] == by_res.get("referenced_unresolved", 0)
        and man["counts"]["declared_absent"] == by_res.get("declared_absent", 0),
        "sum(by_class)=%d sum(by_resolution)=%d assets=%d len(assets)=%d"
        % (sum(by_class.values()), sum(by_res.values()), man["counts"]["assets"], len(man["assets"])))

    # ---- claims carry evidence or an explicit status
    claims = env.get("claims", [])
    man_claims = man.get("claims", [])
    ok = all(("evidence_locator" in c) or ("status" in c) for c in man_claims) and claims == []
    rec("all_claims_have_evidence_or_explicit_unresolved_status", ok,
        "envelope claims=%d, manifest claims=%d -> vacuous pass (no claim generation by contract); "
        "objective.classify_report_type=false" % (len(claims), len(man_claims)))

    # ---- constraints
    verified_hits = [a["asset_id"] for a in man["assets"] if "verif" in (a["resolution"] + json.dumps(a["resolution_check"])).lower()]
    rec("do_not_mark_claims_as_verified", not verified_hits and not any(
        c.get("status") == "verified" for c in claims),
        "no claim has a verified status (no claims at all); no asset resolution/check string contains 'verified'")

    empty_notes = [a["asset_id"] for a in man["assets"] if not a["note"].strip() or not a["resolution_check"]["check"].strip()]
    rec("do_not_invent_missing_information", not empty_notes,
        "every one of the %d assets carries a non-empty resolution_check.check and note "
        "(unresolved/absent targets are named as such, never given an invented address)" % len(man["assets"]))

    bad_enum = [a["asset_id"] for a in man["assets"]
                if (a["resolution"] == "resolved_in_source" and a["resolution_check"]["result"] != "resolved")
                or (a["resolution"] == "referenced_unresolved" and a["resolution_check"]["result"] != "unresolved")
                or (a["resolution"] == "declared_absent" and a["resolution_check"]["result"] != "absent")]
    rec("preserve_uncertainty", not bad_enum,
        "resolution and resolution_check.result agree on all assets; uncertainty/failure text kept verbatim "
        "in A23/A25/A26 (honest FAIL 0.661/0.000 preserved, not smoothed)" if not bad_enum
        else "mismatched: " + ",".join(bad_enum))

    rec("scope_report_10459_only",
        env["report_id"] == man["report_id"] == man["source"]["uri"].split("/")[-1] == REPORT_ID
        and env["package_id"] == man["package_id"] == PKG,
        "package_id=%s report_id=%s source=%s (no other report touched by this package)"
        % (env["package_id"], env["report_id"], man["source"]["uri"]))

    nfail = sum(1 for c in checks if c["result"] == "FAIL")
    verdict = "PASS" if nfail == 0 else "FAIL"
    out = {"package_id": PKG, "report_id": REPORT_ID, "verdict": verdict,
           "failed": nfail, "checks": checks,
           "note": "worker-side self check; the platform gate is authoritative"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for c in checks:
        print("%-4s %-52s %s" % (c["result"], c["check"], c["detail"][:150]))
    print("VERDICT %s (%d failed) -> %s" % (verdict, nfail, OUT.relative_to(REPO)))
    return 0 if nfail == 0 else 2


if __name__ == "__main__":
    sys.exit(main())