"""Independent verifier for wp-13946-01 (report 13946 asset manifest).

Deliberately does NOT import scripts/kf_register_13946.py: the source markdown is re-fetched from
the platform API (or, in --offline mode, read from the fetched run copy) and every locator is
re-resolved from scratch, so a bug in the builder cannot hide here.

Checks map 1:1 onto the work-package acceptance list:
  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status

Usage:
  python3 scripts/kf_verify_13946.py             # against platform API (needs env creds)
  python3 scripts/kf_verify_13946.py --offline   # against runs/wp-13946-01/report_13946.md
Output: artifacts/wp-13946-01/verification.json (mirrored to docs/wp-13946-01/)
Exit: 0 all pass, 1 any failure, 2 cannot verify (source unavailable).
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.request

REPORT_ID = "13946"
PACKAGE_ID = "wp-13946-01"
EXPECTED_HASH = "eb37b6effecdfc9396ded7a80f236173e234f2785fd984a948efba4a9b671072"
EXPECTED_CHARS = 5534
RUN_DIR = pathlib.Path("runs") / PACKAGE_ID
ART_DIR = pathlib.Path("artifacts") / PACKAGE_ID
DOC_DIR = pathlib.Path("docs") / PACKAGE_ID
MANIFEST = ART_DIR / "asset_manifest.json"
ENVELOPE = RUN_DIR / "kf_result.wp-13946-01.json"
SCHEMA_PKG = pathlib.Path("schemas/asset_manifest.wp-13946-01.schema.json")
SCHEMA_ENV = pathlib.Path("schemas/kf_result.v1.schema.json")


def _req(url, token=None, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def fetch_markdown_from_api() -> str | None:
    base = os.environ.get("TENSOR_API_BASE", "").rstrip("/")
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (base and user and pwd):
        return None
    tok = None
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = _req(base + path, payload={"username": user, "password": pwd})
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            break
    d = _req(base + "/tensor/reports/" + REPORT_ID, tok)
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    return d.get("markdown")


def verify(md: str, src_origin: str) -> dict:
    checks: dict[str, dict] = {}

    # --- valid_json
    try:
        manifest = json.loads(MANIFEST.read_text())
        envelope = json.loads(ENVELOPE.read_text())
        ok = True
        detail = "manifest + envelope parsed"
    except Exception as exc:  # noqa: BLE001
        return {"checks": {"valid_json": {"pass": False, "detail": str(exc)}}}
    checks["valid_json"] = {"pass": ok, "detail": detail}

    # --- source_hash_matches (recomputed from raw markdown bytes)
    h = hashlib.sha256(md.encode()).hexdigest()
    checks["source_hash_matches"] = {
        "pass": h == EXPECTED_HASH and manifest["source"]["hash"] == h
        and envelope["provenance"]["source_hash"] == "sha256:" + h
        and len(md) == EXPECTED_CHARS,
        "detail": {"recomputed": h, "contract": EXPECTED_HASH,
                   "manifest": manifest["source"]["hash"],
                   "envelope": envelope["provenance"]["source_hash"],
                   "chars": len(md), "chars_contract": EXPECTED_CHARS,
                   "source_origin": src_origin},
    }

    # --- schema_pass
    import jsonschema
    errs = []
    for label, inst, sp in (("manifest", manifest, SCHEMA_PKG), ("envelope", envelope, SCHEMA_ENV)):
        schema = json.loads(sp.read_text())
        try:
            jsonschema.validate(inst, schema)
        except jsonschema.ValidationError as exc:  # pragma: no cover - reported, not raised
            errs.append("%s: %s at %s" % (label, exc.message, list(exc.absolute_path)))
    checks["schema_pass"] = {"pass": not errs,
                             "detail": errs or [str(SCHEMA_PKG), str(SCHEMA_ENV)]}

    # --- no_duplicate_ids
    ids = [a["asset_id"] for a in manifest["assets"]]
    checks["no_duplicate_ids"] = {"pass": len(ids) == len(set(ids)),
                                  "detail": {"count": len(ids), "distinct": len(set(ids))}}

    # --- source_locator_resolvable (re-resolve every locator against raw markdown)
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
        problems = []
        if md[s:e] != q:
            problems.append("char_span mismatch")
        if md.count(q) != 1:
            problems.append("quote not unique (%d)" % md.count(q))
        if loc["start_line"] != md.count("\n", 0, s):
            problems.append("start_line mismatch")
        if not (0 <= s < e <= len(md)):
            problems.append("span out of range")
        if problems:
            bad.append({"asset_id": a["asset_id"], "problems": problems})
    checks["source_locator_resolvable"] = {"pass": not bad, "detail": bad or
                                           "%d/%d locators re-resolved" % (len(ids), len(ids))}

    # --- claims evidence/status
    claims = manifest.get("claims") or []
    bad_claims = [c.get("claim_id") for c in claims
                  if not (c.get("evidence") or c.get("evidence_locator") or c.get("status"))]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "pass": not bad_claims,
        "detail": {"claims": len(claims), "offending": bad_claims,
                   "note": "claims intentionally empty for 01-asset-registration"},
    }

    # --- extra guard: nothing may claim verification (structural, not keyword scan: a note is
    # allowed to *say* "not verified", so only truthy verification fields / statuses count)
    marked = []
    for a in manifest["assets"]:
        if a.get("verified") is True or a.get("status") in ("verified", "verified_by_gate"):
            marked.append(a["asset_id"])
        if a.get("resolution_check", {}).get("result") not in (None, "resolved", "unresolved", "absent", "present"):
            marked.append(a["asset_id"] + ":bad-result")
    if manifest.get("verified") is True or manifest.get("integrity", {}).get("verified_by_platform_gate"):
        marked.append("manifest")
    for c in manifest.get("claims") or []:
        if c.get("status") in ("verified", "verified_by_gate"):
            marked.append(c.get("claim_id", "?"))
    checks["no_asset_marked_verified"] = {"pass": not marked, "detail": marked or "none"}
    checks["scope_single_report"] = {
        "pass": manifest["report_id"] == REPORT_ID and envelope["report_id"] == REPORT_ID,
        "detail": {"manifest": manifest["report_id"], "envelope": envelope["report_id"]},
    }
    return {"package_id": PACKAGE_ID, "report_id": REPORT_ID, "checks": checks}


def main() -> int:
    offline = "--offline" in sys.argv
    md, origin = None, ""
    if not offline:
        md = fetch_markdown_from_api()
        origin = "platform API /tensor/reports/13946"
    if md is None:
        p = RUN_DIR / "report_13946.md"
        if not p.exists():
            print("UNABLE TO VERIFY: no API access and no local copy at %s" % p)
            return 2
        md = p.read_text()
        origin = "local fetched copy %s (API unavailable/offline)" % p
    rep = verify(md, origin)
    failed = [k for k, v in rep["checks"].items() if not v["pass"]]
    rep["all_pass"] = not failed
    rep["failed"] = failed
    ART_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(rep, ensure_ascii=False, indent=2) + "\n"
    (ART_DIR / "verification.json").write_text(txt)
    (DOC_DIR / "verification.json").write_text(txt)
    for k, v in rep["checks"].items():
        print(("PASS " if v["pass"] else "FAIL ") + k)
    print("all_pass:", rep["all_pass"], "| source:", origin)
    return 0 if rep["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())