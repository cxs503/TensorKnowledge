#!/usr/bin/env python3
"""Pure acceptance-check functions for wp-12028-01.

Kept free of I/O so the same code the verifier runs can be exercised against
deliberately tampered inputs (negative controls in
tests/test_wp12028_asset_manifest.py).  If a check cannot fail, it proves
nothing.
"""
from __future__ import annotations

import hashlib
import json


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