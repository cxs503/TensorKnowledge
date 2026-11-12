#!/usr/bin/env python3
"""Acceptance gate for wp-1226-01 (asset registration of report 1226).

Implements the six machine-checkable acceptance keys from the contract:
  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status
plus structural invariants this package promises (unique locators, every unresolved
asset carries a reason, empty claims carry an explicit policy reason).

Writes docs/kf/wp-1226-01/acceptance.json.  Exit code 0 = all checks pass.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

WT = pathlib.Path(__file__).resolve().parent.parent
PKG = WT / "docs" / "kf" / "wp-1226-01"
SRC = WT / "work" / "wp-1226-01" / "source"
SCHEMA = WT / "schemas" / "kf_result.v1.schema.json"
CONTRACT_SOURCE_HASH = "sha256:d419206bdb3f282d2e2a1ac1f96e972af4438061815e95abba98d8c028e96717"
CONTRACT_CHARS = 6045


def _rec_get(record: dict, path: str):
    """Resolve a simple locator field path against the report record snapshot."""
    cur = record
    for part in path.replace("]", "").split("."):
        if "[" in part:
            key, idx = part.split("[")
            cur = cur[key][int(idx)]
        else:
            cur = cur[part]
    return cur


def check() -> dict:
    res: dict = {"package_id": "wp-1226-01", "checks": {}}

    # 1 valid_json ------------------------------------------------------------
    try:
        kf = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
        man = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
        res["checks"]["valid_json"] = {"ok": True, "files": ["kf_result.json", "asset_manifest.json"]}
    except Exception as e:  # noqa: BLE001
        res["checks"]["valid_json"] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        return res

    # 2 schema_pass -----------------------------------------------------------
    try:
        import jsonschema

        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        errs = sorted(jsonschema.Draft202012Validator(schema).iter_errors(kf),
                      key=lambda e: list(e.path))
        res["checks"]["schema_pass"] = {
            "ok": not errs,
            "schema": "schemas/kf_result.v1.schema.json",
            "errors": [f"{list(e.path)}: {e.message}" for e in errs],
        }
    except FileNotFoundError:
        res["checks"]["schema_pass"] = {"ok": False, "error": "schema file missing"}
    except ImportError:
        res["checks"]["schema_pass"] = {"ok": False, "error": "jsonschema not installed",
                                        "status": "not_run"}

    # 3 source_hash_matches ---------------------------------------------------
    md = (SRC / "report_1226.md").read_text(encoding="utf-8")
    md_bytes = md.encode("utf-8")
    recomputed = "sha256:" + hashlib.sha256(md_bytes).hexdigest()
    res["checks"]["source_hash_matches"] = {
        "ok": recomputed == kf["provenance"]["source_hash"] == CONTRACT_SOURCE_HASH
              and man["source"]["hash_check"]["match"],
        "contract_declared": CONTRACT_SOURCE_HASH,
        "provenance": kf["provenance"]["source_hash"],
        "recomputed_from_markdown_bytes": recomputed,
        "chars_expected": CONTRACT_CHARS,
        "chars_observed": len(md),
        "chars_match": len(md) == CONTRACT_CHARS,
    }

    # 4 source_locator_resolvable --------------------------------------------
    record = json.loads((SRC / "report_1226.json").read_text(encoding="utf-8"))
    record = record.get("data", record)
    bad, ok_n, checked = [], 0, 0
    for a in man["assets"]:
        for loc in a.get("locators", []):
            checked += 1
            field = loc.get("source_field")
            if field == "markdown":
                s, e, q = loc.get("char_start"), loc.get("char_end"), loc.get("quote")
                if not isinstance(s, int) or not isinstance(e, int) or not q:
                    bad.append({"asset_id": a["asset_id"], "why": "incomplete markdown locator"})
                elif md[s:e] != q:
                    bad.append({"asset_id": a["asset_id"], "why": "quote != markdown char span",
                                "expected": md[s:e][:80], "registered": q[:80]})
                else:
                    ok_n += 1
            elif field == "record":
                try:
                    actual = _rec_get(record, loc["field"])
                except Exception as e:  # noqa: BLE001
                    bad.append({"asset_id": a["asset_id"], "why": f"field unresolvable: {e}"})
                    continue
                if actual != loc.get("value"):
                    bad.append({"asset_id": a["asset_id"],
                                "why": f"record value mismatch at {loc['field']}",
                                "actual": actual, "registered": loc.get("value")})
                else:
                    ok_n += 1
            else:
                bad.append({"asset_id": a["asset_id"], "why": f"unknown source_field {field!r}"})
    res["checks"]["source_locator_resolvable"] = {
        "ok": not bad, "locators_checked": checked, "locators_resolved": ok_n,
        "failures": bad[:10],
    }

    # 5 no_duplicate_ids ------------------------------------------------------
    ids = [a["asset_id"] for a in man["assets"]]
    loc_keys = [(a["asset_id"], l.get("field") or (l.get("char_start"), l.get("char_end")))
                for a in man["assets"] for l in a.get("locators", [])]
    dup_ids = sorted({i for i in ids if ids.count(i) > 1})
    dup_locs = sorted({str(k) for k in loc_keys if loc_keys.count(k) > 1})
    res["checks"]["no_duplicate_ids"] = {
        "ok": not dup_ids and not dup_locs,
        "asset_id_count": len(ids),
        "duplicate_asset_ids": dup_ids,
        "duplicate_locators": dup_locs,
    }

    # 6 all_claims_have_evidence_or_explicit_unresolved_status -----------------
    claims = kf.get("claims", [])
    claim_fail = []
    for c in claims:
        has_ev = bool(c.get("evidence"))
        has_unres = bool(c.get("unresolved_reason"))
        if not (has_ev or has_unres):
            claim_fail.append(c.get("claim_id"))
        if c.get("status") == "verified":
            claim_fail.append(f"{c.get('claim_id')}: forbidden status 'verified'")
    policy_reason = (man.get("claims_policy") or {}).get("reason", "")
    res["checks"]["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": not claim_fail and (bool(claims) or bool(policy_reason)),
        "claim_count": len(claims),
        "vacuous": not claims,
        "claims_policy_reason_present": bool(policy_reason),
        "failures": claim_fail,
    }

    # extra structural invariants ---------------------------------------------
    missing_reason = [a["asset_id"] for a in man["assets"]
                      if a.get("status") == "unresolved" and not a.get("unresolved_reason")]
    res["checks"]["unresolved_assets_have_reason"] = {"ok": not missing_reason,
                                                      "missing": missing_reason}
    res["checks"]["reports_touched_single"] = {
        "ok": man["scope"]["reports_touched"] == ["1226"] and man["scope"]["report_id"] == "1226"
              and kf["report_id"] == "1226",
        "scope": man["scope"],
    }
    res["ok"] = all(v.get("ok") for v in res["checks"].values())
    res["package_id"] = kf["package_id"]
    res["summary"] = {k: v.get("ok") for k, v in res["checks"].items()}
    return res


def main() -> int:
    out = check()
    (PKG / "acceptance.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
    for k, v in out["checks"].items():
        print(f"{'PASS' if v.get('ok') else 'FAIL'}  {k}")
    print("overall:", "PASS" if out["ok"] else "FAIL")
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())