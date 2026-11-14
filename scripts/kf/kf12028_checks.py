#!/usr/bin/env python3
"""Acceptance self-check for wp-12028-01 (worker side, NOT the platform gate).

Two layers
  * pure functions (top half): no I/O, so the very code the verifier runs can be
    exercised against deliberately tampered inputs -- negative controls in
    tests/test_wp12028_asset_manifest.py.  If a check cannot fail, it proves nothing.
  * main() (bottom half): re-derives every acceptance item from raw bytes and
    writes docs/kf/wp-12028-01/acceptance.json.

Default mode re-fetches the markdown and the 4 figure payloads from the platform,
so a stale snapshot cannot pass; --offline compares the committed snapshot with
the committed manifest instead and labels those checks as offline.

Usage: python3 scripts/kf/kf12028_checks.py [--offline]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

import jsonschema

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kf12028_register_assets import fetch_figure  # noqa: E402  (single fetch implementation)
from register_assets_lib import fetch_report, get_token  # noqa: E402

PKG = "wp-12028-01"
REPORT_ID = "12028"
CONTRACT_HASH = "sha256:69846e9d0680b8a1c5db5c607b9a5bf4a0ba2e6103b1d193a6a5d5e83e0ec29f"
CONTRACT_CHARS = 8377
ENV_PATH = Path("docs/kf/wp-12028-01/kf_result.json")
MAN_PATH = Path("docs/kf/wp-12028-01/asset_manifest.json")
ACC_PATH = Path("docs/kf/wp-12028-01/acceptance.json")
SCHEMA_PATH = Path("schemas/kf_result.v1.schema.json")
SNAP = Path("work/wp-12028-01/source/report_12028.json")


def sha256_of_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_report(md: str, env: dict, man: dict) -> dict:
    recomputed = sha256_of_text(md)
    prov = (env or {}).get("provenance", {})
    return {
        "recomputed": recomputed,
        "provenance_source_hash": prov.get("source_hash"),
        "manifest_sha256": (man or {}).get("source", {}).get("sha256"),
        "chars": len(md),
        "matches_provenance": recomputed == prov.get("source_hash"),
        "matches_manifest": recomputed == (man or {}).get("source", {}).get("sha256"),
    }


def locator_failures(man: dict, md: str, rec: dict) -> list[dict]:
    """Every markdown locator must satisfy md[start:end] == quote and quote in md;
    every record locator must equal the value actually served by the API."""
    bad = []
    for asset in (man or {}).get("assets", []):
        for loc in asset.get("locators", []):
            field = loc.get("source_field")
            if field == "markdown":
                q = loc.get("quote", "")
                s, e = loc.get("char_start"), loc.get("char_end")
                if not isinstance(s, int) or not isinstance(e, int):
                    bad.append({"asset": asset.get("asset_id"), "why": "missing span"})
                elif md[s:e] != q:
                    bad.append({"asset": asset.get("asset_id"), "why": "span/quote mismatch"})
                elif q not in md:
                    bad.append({"asset": asset.get("asset_id"), "why": "quote absent"})
                elif e - s != len(q):
                    bad.append({"asset": asset.get("asset_id"), "why": "span length"})
            elif field == "record":
                f = loc.get("field", "")
                if f.startswith("figures[].name"):
                    vals = [x.get("name") for x in (rec.get("figures") or [])]
                else:
                    vals = rec.get(f)
                if vals != loc.get("value"):
                    bad.append({"asset": asset.get("asset_id"), "field": f,
                                "why": "record value mismatch"})
            else:
                bad.append({"asset": asset.get("asset_id"), "why": "unknown source_field"})
    for obs in (man or {}).get("observations", []):
        for loc in obs.get("evidence", []):
            q = loc.get("quote", "")
            if md[loc.get("char_start", 0):loc.get("char_end", 0)] != q or q not in md:
                bad.append({"observation": obs.get("id"), "why": "evidence not resolvable"})
    return bad


def duplicate_report(man: dict, env: dict) -> dict:
    aids = [x.get("asset_id") for x in (man or {}).get("assets", [])]
    oids = [x.get("id") for x in (man or {}).get("observations", [])]
    cids = [c.get("claim_id") for c in ((env or {}).get("claims") or [])]
    return {
        "asset_ids": len(aids), "asset_ids_unique": len(aids) == len(set(aids)),
        "observation_ids": len(oids), "observation_ids_unique": len(oids) == len(set(oids)),
        "claim_ids": len(cids), "claim_ids_unique": len(cids) == len(set(cids)),
        "all_unique": (len(aids) == len(set(aids)) and len(oids) == len(set(oids))
                       and len(cids) == len(set(cids))),
    }


def claim_defects(claims: list[dict] | None) -> list[dict]:
    out = []
    for c in claims or []:
        if not (c.get("evidence") or c.get("status")):
            out.append({"claim_id": c.get("claim_id"), "why": "no evidence and no status"})
        if c.get("status") in ("verified", "confirmed"):
            out.append({"claim_id": c.get("claim_id"),
                        "why": "worker must not set a verified status"})
    return out


def _truthy_flag(node, key: str) -> bool:
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key and v:
                return True
            if _truthy_flag(v, key):
                return True
    elif isinstance(node, list):
        return any(_truthy_flag(x, key) for x in node)
    return False


def structural_invariants(man: dict) -> dict:
    assets = (man or {}).get("assets", [])
    counts = (man or {}).get("asset_counts", {})
    by_res: dict[str, int] = {}
    for x in assets:
        by_res[x.get("status")] = by_res.get(x.get("status"), 0) + 1
    scope = (man or {}).get("scope", {})
    return {
        "counts_match_assets": counts.get("assets_total") == len(assets),
        "resolved_count_matches": counts.get("resolved") == by_res.get("resolved", 0),
        "unresolved_count_matches": counts.get("unresolved") == by_res.get("unresolved", 0),
        "unresolved_have_reason": all(x.get("unresolved_reason") for x in assets
                                      if x.get("status") == "unresolved"),
        "scope_no_claim_extraction": scope.get("extracts_claims") is False,
        "scope_no_classification": scope.get("classifies_report_type") is False,
        "scope_no_verified_flag": scope.get("marks_verified") is False,
        "no_asset_marked_verified": not any(x.get("status") == "verified" for x in assets),
        "no_truthy_verified_flag": not _truthy_flag(man, "verified"),
        "claims_policy_reason_present": bool((man or {}).get("claims_policy", {}).get("reason")),
    }


def all_pass(invariants: dict) -> bool:
    return all(v is True for v in invariants.values())


def dumps(node) -> str:
    return json.dumps(node, ensure_ascii=False)


def figure_fingerprint_defects(man: dict, store: dict) -> list[dict]:
    """Every registered figure fingerprint must equal the one in `store`
    (live platform bytes, or the committed snapshot in offline mode)."""
    bad = []
    for a in (man or {}).get("assets", []):
        if a.get("kind") != "figure_reference":
            continue
        name = a["name"].rsplit("/", 1)[-1]
        want = a.get("resolved_bytes") or {}
        got = (store or {}).get(name) or {}
        if not got:
            bad.append({"figure": name, "why": "no payload in store/snapshot"})
            continue
        for k in ("sha256", "bytes", "width_px", "height_px"):
            if want.get(k) != got.get(k):
                bad.append({"figure": name, "field": k, "manifest": want.get(k),
                            "store": got.get(k)})
        if got.get("http_status") not in (200, None):
            bad.append({"figure": name, "why": "store returned HTTP %s" % got.get("http_status")})
    return bad


def check(checks: list, name: str, ok: bool, detail, mode: str = "offline") -> None:
    checks.append({"check": name, "status": "PASS" if ok else "FAIL",
                   "mode": mode, "detail": detail})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="compare against the committed snapshot instead of the platform")
    a = ap.parse_args()

    checks: list[dict] = []

    # ---- valid_json ------------------------------------------------------
    try:
        env = json.loads(ENV_PATH.read_text(encoding="utf-8"))
        man = json.loads(MAN_PATH.read_text(encoding="utf-8"))
        valid, detail = True, {"envelope": str(ENV_PATH), "manifest": str(MAN_PATH)}
    except Exception as e:  # noqa: BLE001
        env, man, valid, detail = {}, {}, False, repr(e)
    check(checks, "valid_json", valid, detail)

    # ---- schema_pass -----------------------------------------------------
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(env, schema)
        ok, err = True, None
    except jsonschema.ValidationError as e:  # pragma: no cover
        ok, err = False, str(e.message)
    check(checks, "schema_pass", ok, {"schema": str(SCHEMA_PATH), "error": err,
                                      "envelope_keys": sorted(env.keys())})

    # ---- contract alignment + single-report hard lock --------------------
    scope = man.get("scope", {})
    alignment = {
        "package_id": env.get("package_id") == PKG,
        "task_type": env.get("task_type") == "01-asset-registration",
        "report_id": env.get("report_id") == REPORT_ID,
        "manifest_package_id": man.get("package_id") == PKG,
        "manifest_report_id": scope.get("report_id") == REPORT_ID,
        "reports_touched_is_single_12028": scope.get("reports_touched") == [REPORT_ID],
        "declared_output_present": "asset_manifest.json" in (env.get("outputs") or {}),
    }
    check(checks, "contract_alignment", all(alignment.values()), alignment)

    # ---- source_hash_matches --------------------------------------------
    rec = fetch_report(REPORT_ID, record_file=(SNAP if a.offline else None))
    md = rec["markdown"]
    h = hash_report(md, env, man)
    hash_ok = (h["matches_provenance"] and h["matches_manifest"]
               and h["recomputed"] == CONTRACT_HASH and h["chars"] == CONTRACT_CHARS)
    check(checks, "source_hash_matches", hash_ok, {
        **h,
        "recomputed_from": rec.get("_retrieved_via"),
        "contract_declared": CONTRACT_HASH,
        "chars_expected": CONTRACT_CHARS,
        "bytes_utf8": len(md.encode("utf-8")),
    }, mode="offline-snapshot" if a.offline else "online")

    # ---- source_locator_resolvable --------------------------------------
    bad = locator_failures(man, md, rec)
    n_loc = sum(len(x.get("locators", [])) for x in man.get("assets", []))
    n_obs = sum(len(o.get("evidence", [])) for o in man.get("observations", []))
    check(checks, "source_locator_resolvable", not bad and n_loc > 0 and n_obs > 0,
          {"asset_locators_checked": n_loc, "observation_evidence_checked": n_obs,
           "failures": bad})

    # ---- no_duplicate_ids ------------------------------------------------
    dup = duplicate_report(man, env)
    check(checks, "no_duplicate_ids", dup["all_unique"], dup)

    # ---- claims: evidence or explicit unresolved status ------------------
    claims = (env.get("outputs") or {}).get("claims.json") or []
    defects = claim_defects(claims)
    check(checks, "all_claims_have_evidence_or_explicit_unresolved_status", not defects, {
        "claims": len(claims),
        "envelope_carries_claims": "claims" in env,
        "empty_claims_allowed_by_contract_notes": True,
        "reason_recorded": bool(man.get("claims_policy", {}).get("reason")),
        "defects": defects,
    })

    # ---- structural invariants ------------------------------------------
    inv = structural_invariants(man)
    check(checks, "structural_invariants", all_pass(inv), inv)

    # ---- figure payload fingerprints (live bytes when online) -----------
    snap = json.loads(SNAP.read_text(encoding="utf-8")) if SNAP.exists() else {}
    if a.offline:
        store, mode = snap.get("figure_fingerprints") or {}, "offline-snapshot"
    else:
        token = get_token()
        if not token:
            store, mode = {}, "offline-snapshot"
            a.offline = True
        else:
            store = {name: fetch_figure(name, token, (snap.get("figure_fingerprints") or {}).get(name))
                     for name in (snap.get("figure_fingerprints") or {})}
            mode = "online"
    fig_bad = figure_fingerprint_defects(man, store)
    check(checks, "figure_payloads_live_sha256", not fig_bad,
          {"mode": mode, "figures_checked": len(store),
           "sha256": {k: (v or {}).get("sha256") for k, v in store.items()},
           "defects": fig_bad}, mode=mode)

    ok = all(c["status"] == "PASS" for c in checks)
    payload = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "verified_by": "worker self-check (NOT the platform gate; status stays draft)",
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "mode": "offline" if a.offline else "online",
        "summary": {"total": len(checks),
                    "pass": sum(c["status"] == "PASS" for c in checks),
                    "fail": sum(c["status"] == "FAIL" for c in checks), "all_pass": ok},
        "checks": checks,
    }
    ACC_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for c in checks:
        print("%-4s %-55s %s" % (c["status"], c["check"], c["mode"]))
        if c["status"] == "FAIL":
            print("     detail:", dumps(c["detail"])[:700])
    print("all_pass:", ok, "->", ACC_PATH)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
