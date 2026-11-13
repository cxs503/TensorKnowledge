#!/usr/bin/env python3
"""wp-13272-01 · acceptance gate for the 01-asset-registration package.

Checks (contract acceptance + structural invariants):
  1. valid_json                          both JSON outputs parse
  2. schema_pass                         envelope validates against schemas/kf_result.v1.schema.json
  3. source_locator_resolvable           every markdown locator quote is a verbatim substring at
                                         the recorded char span; every record locator field exists
  4. source_hash_matches                 recomputed sha256(markdown utf-8) == contract hash
  5. no_duplicate_ids                    asset_id unique; locator keys unique per asset
  6. all_claims_have_evidence_or_explicit_unresolved_status
                                         claims=[] (vacuous) + claims_policy.reason non-empty
  7. (extra) unresolved_assets_have_reason
  8. (extra) reports_touched_single      only report 13272 touched

Writes docs/kf/wp-13272-01/acceptance.json. Exit 1 on any FAIL.
"""
from __future__ import annotations

import json
import pathlib

import jsonschema

WT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = WT / "docs" / "kf" / "wp-13272-01"
SRC_DIR = WT / "work" / "wp-13272-01" / "source"
SCHEMA = WT / "schemas" / "kf_result.v1.schema.json"

CONTRACT_HASH = "sha256:75ed781cefac9fee890f493c256dec8aea2e70795eca9d7a8bbfef1af1bcce90"
CONTRACT_CHARS = 4537
REPORT_ID = "13272"


def main() -> int:
    checks: list[dict] = []

    def add(name: str, ok: bool, evidence: str) -> None:
        checks.append({"check": name, "pass": bool(ok), "evidence": evidence})

    md = (SRC_DIR / "report_13272.md").read_text()
    record = json.loads((SRC_DIR / "report_13272_record.json").read_text())

    # 1. valid_json
    try:
        manifest = json.loads((OUT_DIR / "asset_manifest.json").read_text())
        envelope = json.loads((OUT_DIR / "kf_result.json").read_text())
        add("valid_json", True, "asset_manifest.json and kf_result.json both json.loads OK")
    except Exception as e:  # noqa: BLE001
        add("valid_json", False, repr(e))
        (OUT_DIR / "acceptance.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    # 2. schema_pass
    schema = json.loads(SCHEMA.read_text())
    try:
        jsonschema.validate(envelope, schema, format_checker=jsonschema.FormatChecker())
        add("schema_pass", True, "jsonschema Draft2020-12: 0 errors on kf_result.json")
    except jsonschema.ValidationError as e:
        add("schema_pass", False, f"ValidationError: {e.message} at {list(e.absolute_path)}")

    # 3. source_locator_resolvable
    bad = []
    n_md = n_rec = 0
    for a in manifest["assets"]:
        for loc in a["locators"]:
            if loc.get("source_field") == "markdown":
                n_md += 1
                seg = md[loc["char_start"]:loc["char_end"]]
                if seg != loc["quote"] or md.find(loc["quote"]) != loc["char_start"]:
                    bad.append((a["asset_id"], loc["quote"][:40]))
            elif loc.get("source_field") == "record":
                n_rec += 1
                field = loc["field"]
                cur = record
                for part in field.split("."):
                    if part.endswith("]"):
                        base, idx = part.split("[")
                        cur = cur[base][int(idx[:-1])]
                    else:
                        cur = cur[part]
                if cur != loc["value"]:
                    bad.append((a["asset_id"], field))
    add(
        "source_locator_resolvable",
        not bad,
        f"{n_md} markdown locators + {n_rec} record locators all re-resolved; failures={bad[:5]}",
    )

    # 4. source_hash_matches
    import hashlib

    recomputed = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    add(
        "source_hash_matches",
        recomputed == CONTRACT_HASH == envelope["provenance"]["source_hash"],
        f"recomputed={recomputed} contract={CONTRACT_HASH} envelope={envelope['provenance']['source_hash']}",
    )

    # 5. no_duplicate_ids
    ids = [a["asset_id"] for a in manifest["assets"]]
    dup = len(ids) != len(set(ids))
    add("no_duplicate_ids", not dup, f"{len(ids)} asset_ids, unique={len(set(ids))}")

    # 6. claims
    claims = envelope.get("claims", [])
    reason = manifest.get("claims_policy", {}).get("reason", "")
    ok6 = all(
        (c.get("status") in ("supported", "partially-supported", "refuted") and c.get("evidence"))
        or (c.get("status") == "unresolved" and c.get("unresolved_reason"))
        for c in claims
    ) and bool(reason)
    add(
        "all_claims_have_evidence_or_explicit_unresolved_status",
        ok6,
        f"claims={len(claims)} (vacuous pass); claims_policy.reason non-empty={bool(reason)}",
    )

    # 7. unresolved assets carry a reason
    missing = [a["asset_id"] for a in manifest["assets"]
               if a["status"] == "unresolved" and not a.get("unresolved_reason")]
    add("unresolved_assets_have_reason", not missing, f"missing={missing[:5]}")

    # 8. single report touched
    add(
        "reports_touched_single",
        manifest["scope"]["reports_touched"] == [REPORT_ID],
        f"reports_touched={manifest['scope']['reports_touched']}",
    )

    # extra: chars check
    add(
        "chars_match_contract",
        manifest["source"]["chars"] == CONTRACT_CHARS,
        f"observed={manifest['source']['chars']} contract={CONTRACT_CHARS}",
    )

    (OUT_DIR / "acceptance.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2))
    failed = [c for c in checks if not c["pass"]]
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["check"] + "  " + c["evidence"])
    print(f"TOTAL {len(checks) - len(failed)}/{len(checks)} pass")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
