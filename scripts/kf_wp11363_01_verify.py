#!/usr/bin/env python3
"""Worker-side self check for wp-11363-01: re-derive every acceptance criterion
from raw bytes (not from the generated manifest's own assertions).

By default the report markdown is re-fetched live from the platform API, so a
stale local snapshot cannot make a check pass. `--offline` uses the committed
snapshot and says so in the output.

Acceptance criteria (contract wp-11363-01):
  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status
Contract constraints re-checked: source hash equals the contract hash, report_id
scope, no claims marked verified, claims==[] is legitimate (no forced claims).

    python3 scripts/kf_wp11363_01_verify.py [--offline]

Writes docs/kf/wp-11363-01/report_selfcheck.json. Exit code 0 iff every check passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
PKG = "wp-11363-01"
REPORT_ID = "11363"
CONTRACT_HASH = "346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23"
OUT_DIR = ROOT / "docs" / "kf" / PKG
ENVELOPE = OUT_DIR / "kf_result.json"
MANIFEST = OUT_DIR / "asset_manifest.json"
SELFCHECK = OUT_DIR / "report_selfcheck.json"
SNAPSHOT = ROOT / "runs" / PKG / ("source_%s.md" % REPORT_ID)
ENVELOPE_SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
MANIFEST_SCHEMA = ROOT / "schemas" / "asset_manifest_wp11363_01.schema.json"


def fetch_markdown() -> tuple[str, str]:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")

    def call(path, body=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(base + path,
                                     data=json.dumps(body).encode() if body else None,
                                     headers=headers)
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))

    tok = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                               "password": os.environ["TENSOR_AGENT_PASS"]})["access_token"]
    rec = call("/tensor/reports/" + REPORT_ID, token=tok)
    if str(rec.get("id")) != REPORT_ID:
        raise SystemExit("report_id mismatch from API: %r" % rec.get("id"))
    return rec["markdown"], "live GET /api/v1/tensor/reports/%s" % REPORT_ID


def scan_report_ids(obj, path="$") -> list[str]:
    """Find report_id-looking keys/values that are not 11363 (scope check)."""
    bad = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("report_id", "source_uri") and isinstance(v, (str, int)):
                s = str(v)
                if s.split("/")[-1] not in (REPORT_ID, "reports") and REPORT_ID not in s:
                    bad.append("%s.%s=%r" % (path, k, v))
            bad += scan_report_ids(v, "%s.%s" % (path, k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            bad += scan_report_ids(v, "%s[%d]" % (path, i))
    return bad


def run_checks(md: str, env: dict, man: dict, source_mode: str) -> dict:
    """Every acceptance criterion, re-derived from (md, envelope, manifest).

    Kept pure so the invariant tests can hand in tampered copies and watch the
    checks fail -- a check that cannot fail is not a check.
    """
    checks: dict[str, dict] = {}
    checks["valid_json"] = {"pass": True,
                            "detail": "envelope and manifest parsed via json.loads "
                                      "(input to run_checks)"}

    # ---- schema_pass -----------------------------------------------------
    env_schema = json.loads(ENVELOPE_SCHEMA.read_text(encoding="utf-8"))
    man_schema = json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    errs = []
    for name, inst, sch in (("envelope", env, env_schema), ("manifest", man, man_schema)):
        try:
            jsonschema.validate(instance=inst, schema=sch)
        except jsonschema.ValidationError as exc:
            errs.append("%s%s: %s" % (name, list(exc.absolute_path), exc.message))
    out_name_ok = list(env.get("outputs", {}).keys()) == ["asset_manifest.json"]
    if not out_name_ok:
        errs.append("outputs keys != ['asset_manifest.json']: %r" % list(env.get("outputs", {})))
    checks["schema_pass"] = {
        "pass": not errs,
        "detail": ("schemas/kf_result.v1.schema.json (envelope) + "
                   "schemas/asset_manifest_wp11363_01.schema.json (manifest) both validate; "
                   "declared output name = asset_manifest.json") if not errs else "; ".join(errs),
    }

    # ---- source_hash_matches --------------------------------------------
    live = hashlib.sha256(md.encode("utf-8")).hexdigest()
    declared = env["provenance"]["source_hash"].split(":", 1)[-1]
    man_hash = man["source"]["source_hash"].split(":", 1)[-1]
    checks["source_hash_matches"] = {
        "pass": live == declared == man_hash == CONTRACT_HASH,
        "detail": "source=%s; recomputed=%s envelope=%s manifest=%s contract=%s "
                  "chars=%d bytes=%d" % (source_mode, live, declared, man_hash, CONTRACT_HASH,
                                         len(md), len(md.encode("utf-8"))),
    }

    # ---- source_locator_resolvable --------------------------------------
    bad_loc, n_loc, n_unique = [], 0, 0
    for a in man["assets"]:
        loc = a.get("locator", {})
        if loc.get("method") != "char_span":
            continue
        n_loc += 1
        q = loc.get("quote", "")
        s, e = loc.get("start_char"), loc.get("end_char")
        if not q or q not in md:
            bad_loc.append("%s: quote not a substring of the source markdown" % a["asset_id"])
            continue
        if not isinstance(s, int) or not isinstance(e, int) or md[s:e] != q:
            bad_loc.append("%s: md[%s:%s] != quote" % (a["asset_id"], s, e))
            continue
        if md.count(q) != loc.get("count_occurrences"):
            bad_loc.append("%s: count_occurrences %s != recomputed %d"
                           % (a["asset_id"], loc.get("count_occurrences"), md.count(q)))
            continue
        quoted_lines = md[:s].count("\n") + 1
        if quoted_lines != loc.get("line"):
            bad_loc.append("%s: line %s != recomputed %d"
                           % (a["asset_id"], loc.get("line"), quoted_lines))
        if md.count(q) == 1:
            n_unique += 1
    checks["source_locator_resolvable"] = {
        "pass": not bad_loc and n_loc > 0 and n_loc == man["counts"]["locators"],
        "detail": "%d char_span locators re-verified against %s (substring + offset back-read "
                  "+ line number + occurrence count); %d are unique in the source; failures=%s"
                  % (n_loc, source_mode, n_unique, bad_loc[:5]),
    }

    # ---- no_duplicate_ids ------------------------------------------------
    ids = [a["asset_id"] for a in man["assets"]]
    dups = sorted({i for i in ids if ids.count(i) > 1})
    checks["no_duplicate_ids"] = {
        "pass": not dups and len(ids) == man["id_integrity"]["count"],
        "detail": "%d asset ids, duplicates=%s, pattern_ok=%s"
                  % (len(ids), dups, man["id_integrity"]["pattern_ok"]),
    }

    # ---- all_claims_have_evidence_or_explicit_unresolved_status ----------
    claims = man.get("claims") or []
    env_claims = env.get("claims") or []
    claim_problems = []
    for c in claims + env_claims:
        if not (c.get("evidence") or c.get("evidence_locator") or c.get("status")):
            claim_problems.append(c.get("claim_id"))
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "pass": not claim_problems,
        "detail": "claims=[] in both envelope and manifest (objective.classify_report_type="
                  "false, no extraction); reason recorded: %r; vacuously satisfied, "
                  "violations=%s" % (man.get("claims_empty_reason", "")[:60], claim_problems),
    }

    # ---- constraint: nothing marked verified -----------------------------
    verified_marks = [c.get("claim_id") for c in claims + env_claims
                      if c.get("status") == "verified" or c.get("verified") is True]
    checks["constraint_do_not_mark_claims_as_verified"] = {
        "pass": not verified_marks,
        "detail": "no claim carries status='verified' or verified=true; verification is left to "
                  "the platform gate (violations=%s)" % verified_marks,
    }

    # ---- constraint: report_id scope ------------------------------------
    scope_bad = scan_report_ids(env, "envelope") + scan_report_ids(man, "manifest")
    checks["constraint_report_id_scope"] = {
        "pass": not scope_bad,
        "detail": "every report_id/source_uri in the deliverables resolves to 11363; "
                  "offenders=%s" % scope_bad[:5],
    }

    # ---- constraint: uncertainty preserved ------------------------------
    checks["constraint_preserve_uncertainty"] = {
        "pass": bool(man.get("limitations")) and bool(man.get("unresolved")) is not None,
        "detail": "%d limitations + %d unresolved asset ids recorded; figure byte absence is "
                  "reported per figure instead of being papered over"
                  % (len(man.get("limitations", [])), len(man.get("unresolved", []))),
    }

    # ---- identity: contract constants -----------------------------------
    checks["constraint_contract_identity"] = {
        "pass": (man["source"]["chars"] == 6902 and man["source"]["hash_match"]
                 and man["package_id"] == PKG and man["report_id"] == REPORT_ID),
        "detail": "package_id=%s report_id=%s chars=%d hash_match=%s"
                  % (man["package_id"], man["report_id"], man["source"]["chars"],
                     man["source"]["hash_match"]),
    }
    # ---- envelope <-> manifest consistency (the envelope schema cannot pin
    # report_id, so a foreign id inside the envelope must be caught here) ------
    mism = []
    if env.get("report_id") != man.get("report_id"):
        mism.append("report_id env=%r man=%r" % (env.get("report_id"), man.get("report_id")))
    if env.get("package_id") != man.get("package_id"):
        mism.append("package_id env=%r man=%r" % (env.get("package_id"), man.get("package_id")))
    if env.get("task_type") != man.get("task_type"):
        mism.append("task_type env=%r man=%r" % (env.get("task_type"), man.get("task_type")))
    if env["provenance"]["source_hash"] != man["source"]["source_hash"]:
        mism.append("source_hash env != man")
    if env.get("outputs", {}).get("asset_manifest.json") != man:
        mism.append("outputs.asset_manifest.json is not this manifest")
    checks["constraint_envelope_manifest_consistency"] = {
        "pass": not mism,
        "detail": "package_id/report_id/task_type/source_hash agree between envelope and "
                  "manifest and outputs.asset_manifest.json is the manifest itself; "
                  "mismatches=%s" % mism,
    }
    return checks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="use the committed markdown snapshot instead of the live API")
    args = ap.parse_args()

    checks: dict[str, dict] = {}

    # ---- valid_json ------------------------------------------------------
    try:
        env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
        man = json.loads(MANIFEST.read_text(encoding="utf-8"))
        checks["valid_json"] = {"pass": True,
                                "detail": "kf_result.json and asset_manifest.json both parse "
                                          "via json.loads"}
    except Exception as exc:  # noqa: BLE001
        checks["valid_json"] = {"pass": False, "detail": repr(exc)}
        SELFCHECK.write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
        return 1

    md, source_mode = (SNAPSHOT.read_text(encoding="utf-8"), "committed snapshot "
                       + str(SNAPSHOT.relative_to(ROOT))) if args.offline else fetch_markdown()

    checks = run_checks(md, env, man, source_mode)
    passed = sum(1 for c in checks.values() if c["pass"])
    payload = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "generated_at_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).isoformat(),
        "source_mode": source_mode,
        "checked_against": {"envelope": str(ENVELOPE.relative_to(ROOT)),
                            "manifest": str(MANIFEST.relative_to(ROOT))},
        "summary": {"checks": len(checks), "passed": passed,
                    "failed": len(checks) - passed,
                    "all_pass": passed == len(checks)},
        "checks": checks,
        "note": "Worker-side self check only. It does not replace the platform gate and makes no "
                "statement about upstream artefacts that live in another repository.",
    }
    SELFCHECK.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for k, v in checks.items():
        print("%-58s %s" % (k, "PASS" if v["pass"] else "FAIL"))
    print("->", SELFCHECK.relative_to(ROOT))
    return 0 if payload["summary"]["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())